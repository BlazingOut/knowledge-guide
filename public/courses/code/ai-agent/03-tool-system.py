"""第三课示例：工具注册、调用链路、失败回填、超时包装与幂等键。"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field


# ===== 课程示例：工具注册表与调用链路 =====


@dataclass
class Decision:
    """模型一步的结构化输出，与第二课相同。"""

    kind: str
    text: str = ""
    tool_name: str = ""
    tool_args: dict[str, str] = field(default_factory=dict)


@dataclass
class ToolSpec:
    """一个工具的注册信息。模型只看得到 name 与 description，其余给运行时用。"""

    name: str
    description: str
    func: object
    required: tuple[str, ...] = ()
    value_rules: dict[str, tuple[str, ...]] = field(default_factory=dict)
    permission: str = ""      # 空字符串表示无需权限
    side_effects: bool = False
    timeout_s: float = 3.0


@dataclass
class LifeStore:
    records: dict[str, list[str]] = field(default_factory=dict)
    plans: list[str] = field(default_factory=list)


STORE = LifeStore()


def search_records(kind: str) -> str:
    items = STORE.records.get(kind, [])
    return f"查询结果：{items}"


def add_plan(title: str) -> str:
    STORE.plans.append(title)
    return f"已添加计划：{title}"


def search_preferences() -> str:
    return "偏好：提醒方式=推送，主题=简洁"


def delete_records(kind: str) -> str:
    STORE.records.pop(kind, None)
    return f"已删除 {kind} 记录"


def buggy_tool() -> str:
    raise ValueError("数据库连接断开")


def slow_search(seconds: str) -> str:
    time.sleep(float(seconds))
    return "慢查询结果"


# 注册表一：含糊描述——模型只能靠描述选工具
VAGUE_REGISTRY: dict[str, ToolSpec] = {
    "search_records": ToolSpec(
        name="search_records",
        description="查询记录",
        func=search_records,
        required=("kind",),
        value_rules={"kind": ("health", "study")},
    ),
    "search_preferences": ToolSpec(
        name="search_preferences",
        description="查询信息",
        func=search_preferences,
    ),
}

# 注册表二：清晰描述——何时用、何时不用都写明
CLEAR_REGISTRY: dict[str, ToolSpec] = {
    "search_records": ToolSpec(
        name="search_records",
        description="查询运动记录，例如跑步、健身的条数与明细；不查询用户偏好。",
        func=search_records,
        required=("kind",),
        value_rules={"kind": ("health", "study")},
    ),
    "search_preferences": ToolSpec(
        name="search_preferences",
        description="查询用户偏好设置，例如提醒方式与主题；不查询运动记录。",
        func=search_preferences,
    ),
}

# 注册表三：在清晰版之上补充写工具、权限工具、异常与慢工具，用于演示失败
DEMO_REGISTRY: dict[str, ToolSpec] = {
    **CLEAR_REGISTRY,
    "add_plan": ToolSpec(
        name="add_plan",
        description="新增一条生活计划，标题控制在 20 字内。",
        func=add_plan,
        required=("title",),
        side_effects=True,
    ),
    "delete_records": ToolSpec(
        name="delete_records",
        description="删除某类记录，仅管理员可用。",
        func=delete_records,
        required=("kind",),
        permission="admin",
        side_effects=True,
    ),
    "buggy_tool": ToolSpec(
        name="buggy_tool",
        description="演示执行异常的工具。",
        func=buggy_tool,
    ),
    "slow_search": ToolSpec(
        name="slow_search",
        description="一个执行很慢的查询，用于演示超时。",
        func=slow_search,
        required=("seconds",),
        timeout_s=0.5,
    ),
}


def validate_args(spec: ToolSpec, args: dict[str, str]) -> str | None:
    """参数校验：返回失败原因，通过时返回 None。"""
    for key in spec.required:
        if not args.get(key, "").strip():
            return f"缺少必填参数 {key}"
    for key, allowed in spec.value_rules.items():
        value = args.get(key, "")
        if value and value not in allowed:
            return f"参数 {key}={value!r} 不在允许范围 {allowed}"
    return None


def execute_tool(
    registry: dict[str, ToolSpec],
    name: str,
    args: dict[str, str],
    user_role: str = "member",
    strict: bool = False,
) -> str:
    """一次工具调用的完整链路，返回写回上下文的观察。

    顺序：存在性 -> 参数校验 -> 权限 -> 执行（带超时）-> 包装成观察。
    strict=True 时执行异常向上抛出（快速失败）；默认回填观察。
    """
    spec = registry.get(name)
    if spec is None:
        return f"未知工具：{name}"
    problem = validate_args(spec, args)
    if problem is not None:
        return f"参数校验失败：{problem}"
    if spec.permission and user_role != spec.permission:
        return f"权限不足：{name} 需要 {spec.permission} 权限，当前角色 {user_role}"
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(spec.func, **args)
        result = future.result(timeout=spec.timeout_s)
    except FutureTimeoutError:
        return (
            f"工具超时：{name} 超过 {spec.timeout_s} 秒未返回，"
            "本次未拿到结果（副作用可能已发生）"
        )
    except Exception as exc:  # 执行异常：默认回填，strict 时快速失败
        if strict:
            raise
        return f"工具执行失败：{type(exc).__name__}: {exc}"
    finally:
        pool.shutdown(wait=False)  # 不等后台线程；超时只是不再等待
    return str(result)


class KeywordLLM:
    """假模型：只在工具描述里找关键词来选工具。

    真实模型靠语义理解 description，机制相同——它看不到函数源码，
    描述就是全部依据。这里用关键词匹配把这件事做成可观察的。
    """

    def __init__(self, goal_keyword: str, args: dict[str, str]) -> None:
        self.goal_keyword = goal_keyword
        self.args = args

    def choose(self, registry: dict[str, ToolSpec]) -> Decision:
        for spec in registry.values():
            if self.goal_keyword in spec.description:
                return Decision(
                    kind="tool", tool_name=spec.name, tool_args=dict(self.args)
                )
        return Decision(
            kind="final",
            text=f"没有适合“{self.goal_keyword}”的工具，需要用户补充信息",
        )


_PROCESSED: dict[str, str] = {}


def add_plan_idem(title: str, request_id: str) -> str:
    """带幂等键的写入：同一 request_id 只执行一次。

    幂等键来自请求本身（模型输出或客户端生成），重试时不变。
    """
    if request_id in _PROCESSED:
        return f"重复请求（{request_id}），不重复执行；已有计划：{_PROCESSED[request_id]}"
    _PROCESSED[request_id] = title
    STORE.plans.append(title)
    return f"已添加计划：{title}（请求号 {request_id}）"


def main() -> None:
    global STORE
    STORE = LifeStore(records={"health": ["周一慢跑"]})

    print("路径 A：同一目标，两份注册表——描述决定选工具")
    llm = KeywordLLM("运动", {"kind": "health"})
    print("含糊描述 ->", llm.choose(VAGUE_REGISTRY))
    decision = llm.choose(CLEAR_REGISTRY)
    print("清晰描述 ->", decision)
    if decision.kind == "tool":
        print(
            "观察：",
            execute_tool(CLEAR_REGISTRY, decision.tool_name, decision.tool_args),
        )
    print()

    STORE = LifeStore(records={"health": ["周一慢跑"]})
    print("路径 B：失败也是观察（strict=False），以及一次快速失败")
    print("取值非法 ->", execute_tool(DEMO_REGISTRY, "search_records", {"kind": "运动"}))
    print("缺少参数 ->", execute_tool(DEMO_REGISTRY, "add_plan", {}))
    print("权限不足 ->", execute_tool(DEMO_REGISTRY, "delete_records", {"kind": "health"}))
    print("执行异常 ->", execute_tool(DEMO_REGISTRY, "buggy_tool", {}))
    try:
        execute_tool(DEMO_REGISTRY, "buggy_tool", {}, strict=True)
    except ValueError as exc:
        print("快速失败 -> 异常向上抛出，交给人处理：", exc)
    print("当前计划（应仍为空）：", STORE.plans)
    print()

    print("路径 C：超时包装")
    print("超时观察 ->", execute_tool(DEMO_REGISTRY, "slow_search", {"seconds": "2"}))
    print("（后台线程还会收尾一会儿，说明：超时只是不再等待，不是强杀）")
    print()

    STORE = LifeStore(records={"health": ["周一慢跑"]})
    _PROCESSED.clear()
    print("路径 D：幂等键——重试不重做")
    print("第一次 ->", add_plan_idem("今晚跑步", "req-001"))
    print("重试同一请求号 ->", add_plan_idem("今晚跑步", "req-001"))
    print("新请求号 ->", add_plan_idem("周三游泳", "req-002"))
    print("当前计划（应只有两条）：", STORE.plans)


# ===== 课后作业：学习资料工具链 =====

STUDY_PLANS: list[str] = []
STUDY_PROCESSED: dict[str, str] = {}


def search_notes(topic: str) -> str:
    return f"笔记摘要：{topic} 尚未掌握间隔重复"


def buggy_notes(topic: str) -> str:
    raise RuntimeError("笔记服务暂时不可用")


def add_review(title: str) -> str:
    STUDY_PLANS.append(title)
    return f"已加入复习：{title}"


STUDY_REGISTRY: dict[str, ToolSpec] = {
    "search_notes": ToolSpec(
        name="search_notes",
        description="查询学习笔记的掌握情况；不写入任何数据。",
        func=search_notes,
        required=("topic",),
    ),
    "add_review": ToolSpec(
        name="add_review",
        description="把一个知识点加入复习计划；request_id 由调用方生成，用于幂等。",
        func=add_review,
        required=("title", "request_id"),
        side_effects=True,
    ),
    "buggy_notes": ToolSpec(
        name="buggy_notes",
        description="演示执行异常的笔记工具。",
        func=buggy_notes,
        required=("topic",),
    ),
}


def execute_study_tool(name: str, args: dict[str, str]) -> str:
    """学习资料场景的调用链路。要求见课程文档第 10 节。

    链路：存在性 -> 参数校验 -> 幂等检查 -> 执行 -> 异常回填。
    注意：request_id 是链路层字段，执行 add_review 前要先取出，
    不要原样传给函数本身。
    """
    # TODO 作业：按上面五步完成本函数
    raise NotImplementedError("请完成 execute_study_tool")


def homework() -> None:
    for name, args in [
        ("search_notes", {"topic": ""}),
        ("add_review", {"title": "间隔重复 20 分钟", "request_id": "req-001"}),
        ("add_review", {"title": "间隔重复 20 分钟", "request_id": "req-001"}),
        ("add_review", {"title": "费曼技巧", "request_id": "req-002"}),
        ("buggy_notes", {"topic": "记忆曲线"}),
    ]:
        print(f"{name} {args} -> {execute_study_tool(name, args)}")
    print("复习列表（应只有两条）：", STUDY_PLANS)


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
