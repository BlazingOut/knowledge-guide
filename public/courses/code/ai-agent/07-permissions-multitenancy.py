"""第七课示例：RBAC 权限、多租户三层隔离、配额与审计。"""

from __future__ import annotations

from dataclasses import dataclass, field


# ===== 课程示例：权限模型与多租户隔离 =====


@dataclass
class User:
    name: str
    tenant: str
    roles: tuple[str, ...]


@dataclass
class ToolSpec:
    """工具注册。permission 是需要的最小角色；tenant_scoped 是否按租户隔离。"""

    name: str
    description: str
    func: object
    required: tuple[str, ...] = ()
    value_rules: dict[str, tuple[str, ...]] = field(default_factory=dict)
    permission: str = ""            # 空 = 登录即可
    confirm_required: bool = False  # 危险操作，需要人工确认（完整审批在第 9 课）


@dataclass
class AuditRecord:
    seq: int
    tenant: str
    user: str
    role: str
    tool: str
    args: dict[str, str]
    result: str
    allowed: bool


class AuditLog:
    """审计日志：谁在何时（这里用序号代替时间）调用了哪个工具、结果如何。"""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []
        self._seq = 0

    def record(
        self,
        user: User,
        tool: str,
        args: dict[str, str],
        result: str,
        allowed: bool,
    ) -> None:
        self._seq += 1
        self.records.append(
            AuditRecord(
                self._seq, user.tenant, user.name, ",".join(user.roles),
                tool, dict(args), result, allowed,
            )
        )

    def dump(self) -> None:
        for rec in self.records:
            print(
                f"  #{rec.seq} 租户={rec.tenant} 用户={rec.user} 角色={rec.role} "
                f"工具={rec.tool} 参数={rec.args} 结果={rec.result[:20]} 放行={rec.allowed}"
            )


@dataclass
class TenantStore:
    records: dict[str, list[str]] = field(default_factory=dict)
    memory: dict[str, list[str]] = field(default_factory=dict)
    quota: dict[str, dict] = field(default_factory=dict)  # tenant -> {"calls", "limit"}


STORE = TenantStore()


def new_world() -> TenantStore:
    return TenantStore(
        records={"A": ["周一慢跑"], "B": ["周三游泳"]},
        memory={"A": ["用户偏爱晨跑"], "B": ["用户偏爱夜跑"]},
        quota={"A": {"calls": 0, "limit": 2}, "B": {"calls": 0, "limit": 10}},
    )


ACTIVE_TENANT = "A"  # 运行时从会话上下文注入，不由模型或请求参数提供


def set_active_tenant(tenant: str) -> None:
    global ACTIVE_TENANT
    ACTIVE_TENANT = tenant


def search_records(kind: str) -> str:
    items = STORE.records[ACTIVE_TENANT].copy()
    return f"查询结果（租户 {ACTIVE_TENANT}）：{items}"


def add_plan(title: str) -> str:
    STORE.records[ACTIVE_TENANT].append(title)
    return f"已添加计划（租户 {ACTIVE_TENANT}）：{title}"


def delete_records(kind: str) -> str:
    STORE.records[ACTIVE_TENANT] = []
    return f"已删除（租户 {ACTIVE_TENANT}）的 {kind} 记录"


REGISTRY: dict[str, ToolSpec] = {
    "search_records": ToolSpec(
        name="search_records",
        description="查询本租户的运动记录；kind 只能是 health 或 study。",
        func=search_records,
        required=("kind",),
        value_rules={"kind": ("health", "study")},
    ),
    "add_plan": ToolSpec(
        name="add_plan",
        description="给本租户新增一条生活计划。",
        func=add_plan,
        required=("title",),
        permission="member",
    ),
    "delete_records": ToolSpec(
        name="delete_records",
        description="清空本租户的某类记录，仅管理员可用，且需要人工确认。",
        func=delete_records,
        required=("kind",),
        permission="admin",
        confirm_required=True,
    ),
}


def validate_args(spec: ToolSpec, args: dict[str, str]) -> str | None:
    for key in spec.required:
        if not args.get(key, "").strip():
            return f"缺少必填参数 {key}"
    for key, allowed in spec.value_rules.items():
        value = args.get(key, "")
        if value and value not in allowed:
            return f"参数 {key}={value!r} 不在允许范围 {allowed}"
    return None


def execute(
    registry: dict[str, ToolSpec],
    user: User,
    name: str,
    args: dict[str, str],
    audit: AuditLog,
) -> str:
    """完整调用链路：存在 -> 校验 -> RBAC -> 租户 -> 配额 -> 确认 -> 执行 -> 审计。

    返回写回上下文的观察。每一步被拦都会写一条审计记录（allowed=False）。
    """
    spec = registry.get(name)
    if spec is None:
        audit.record(user, name, args, f"未知工具：{name}", False)
        return f"未知工具：{name}"
    problem = validate_args(spec, args)
    if problem is not None:
        audit.record(user, name, args, f"参数校验失败：{problem}", False)
        return f"参数校验失败：{problem}"
    if spec.permission and spec.permission not in user.roles:
        audit.record(user, name, args, f"权限不足：需要 {spec.permission}", False)
        return f"权限不足：{name} 需要 {spec.permission} 角色，当前角色 {user.roles}"
    # 租户 ID 由会话注入：参数里的 tenant 与当前会话租户不一致 = 伪造
    if "tenant" in args and args["tenant"] != user.tenant:
        audit.record(user, name, args, f"租户不符：{args['tenant']} != {user.tenant}", False)
        return f"租户不符：请求中的租户 {args['tenant']} 与当前会话租户 {user.tenant} 不一致，拒绝执行"
    quota = STORE.quota[user.tenant]
    if quota["calls"] >= quota["limit"]:
        audit.record(user, name, args, f"配额不足：已达上限 {quota['limit']}", False)
        return f"配额不足：租户 {user.tenant} 调用次数已达上限 {quota['limit']}"
    quota["calls"] += 1
    if spec.confirm_required:
        audit.record(user, name, args, "需要人工确认，未执行", False)
        return f"需要人工确认：{name} 是危险操作，未执行（完整审批流在第 9 课）"
    set_active_tenant(user.tenant)
    try:
        result = spec.func(**args)
    except Exception as exc:
        result = f"工具执行失败：{type(exc).__name__}: {exc}"
    audit.record(user, name, args, result, True)
    return result


def recall_memory(tenant: str, keyword: str) -> str:
    """记忆层隔离：只在本租户分区召回，命中他租户的候选一律拒绝。"""
    own = [fact for fact in STORE.memory[tenant] if keyword in fact]
    other = [
        t for t, facts in STORE.memory.items()
        if t != tenant for fact in facts if keyword in fact
    ]
    if other:
        return f"拒绝跨租户召回：关键词 {keyword} 命中租户 {other} 的记忆（严禁跨租户召回）"
    return f"本租户记忆：{own}"


def main() -> None:
    global STORE

    alice = User(name="alice", tenant="A", roles=("member",))
    admin = User(name="bob", tenant="A", roles=("member", "admin"))

    print("路径 A：RBAC——角色决定能调哪个工具")
    STORE = new_world()
    audit = AuditLog()
    print("alice 调 delete_records ->", execute(REGISTRY, alice, "delete_records", {"kind": "health"}, audit))
    print("admin 调 delete_records ->", execute(REGISTRY, admin, "delete_records", {"kind": "health"}, audit))
    print()

    print("路径 B：多租户三层隔离——数据、记忆、伪造租户")
    STORE = new_world()
    audit = AuditLog()
    print("alice(A) 查记录 ->", execute(REGISTRY, alice, "search_records", {"kind": "health"}, audit))
    print(
        "参数里带 tenant=B ->",
        execute(REGISTRY, alice, "search_records", {"kind": "health", "tenant": "B"}, audit),
    )
    print("A 召回「晨跑」 ->", recall_memory("A", "晨跑"))
    print("A 召回「夜跑」 ->", recall_memory("A", "夜跑"))
    print()

    print("路径 C：资源层隔离——租户配额")
    STORE = new_world()
    audit = AuditLog()
    print("第 1 次 ->", execute(REGISTRY, alice, "search_records", {"kind": "health"}, audit))
    print("第 2 次 ->", execute(REGISTRY, alice, "search_records", {"kind": "health"}, audit))
    print("第 3 次 ->", execute(REGISTRY, alice, "search_records", {"kind": "health"}, audit))
    print()

    print("路径 D：对抗输入——恶意参数被闸门③拦下，并留下审计")
    STORE = new_world()
    audit = AuditLog()
    payload = {"kind": "health' OR '1'='1"}
    print("注入 payload ->", execute(REGISTRY, alice, "search_records", payload, audit))
    print()

    print("审计日志（含被拦记录）：")
    audit.dump()
    print("字段清单：序号 / 租户 / 用户 / 角色 / 工具 / 参数 / 结果 / 是否放行")


# ===== 课后作业：学习资料工具的权限与租户 =====

STUDY_PLANS: list[str] = []


def search_notes(topic: str) -> str:
    return f"笔记摘要（租户 {ACTIVE_TENANT}）：{topic} 尚未掌握间隔重复"


def add_review(title: str) -> str:
    STUDY_PLANS.append(title)
    return f"已加入复习：{title}"


def delete_notes(topic: str) -> str:
    return f"已删除笔记：{topic}"


STUDY_REGISTRY: dict[str, ToolSpec] = {
    "search_notes": ToolSpec(
        name="search_notes",
        description="查询本租户的学习笔记。",
        func=search_notes,
        required=("topic",),
        permission="member",
    ),
    "add_review": ToolSpec(
        name="add_review",
        description="把知识点加入复习计划。",
        func=add_review,
        required=("title", "request_id"),
        permission="member",
    ),
    "delete_notes": ToolSpec(
        name="delete_notes",
        description="删除本租户的笔记，仅管理员可用且需要确认。",
        func=delete_notes,
        required=("topic",),
        permission="admin",
        confirm_required=True,
    ),
}


def run_guarded(
    user: User,
    name: str,
    args: dict[str, str],
    audit: AuditLog,
) -> str:
    """TODO 作业：学习资料场景的完整调用链路，要求见课程文档第 12 节。

    链路顺序：存在性 -> 参数校验 -> RBAC -> 租户一致 -> 配额 -> 二次确认 -> 执行 -> 审计。
    复用 execute 的检查逻辑即可，但需要满足：
    1. add_review 的 request_id 是链路层字段，执行前取出，不传给函数本身；
    2. 被拦的每一步都要写审计记录（allowed=False）。
    提示：可以把 execute 里的检查顺序复制过来，把 REGISTRY 换成 STUDY_REGISTRY。
    """
    raise NotImplementedError("请完成 run_guarded")


def homework() -> None:
    alice = User(name="alice", tenant="A", roles=("member",))
    admin = User(name="bob", tenant="A", roles=("member", "admin"))
    audit = AuditLog()
    calls = [
        (alice, "search_notes", {"topic": "记忆方法"}),
        (alice, "add_review", {"title": "间隔重复 20 分钟", "request_id": "req-001"}),
        (alice, "delete_notes", {"topic": "记忆方法"}),        # member -> 权限不足
        (admin, "delete_notes", {"topic": "记忆方法"}),        # admin -> 需要确认
        (alice, "search_notes", {"topic": "记忆方法", "tenant": "B"}),  # 伪造租户 -> 拒绝
    ]
    for user, name, args in calls:
        print(f"{user.name}({user.roles}) {name} -> {run_guarded(user, name, args, audit)}")
    print("复习列表：", STUDY_PLANS)
    print("审计记录：")
    audit.dump()


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
