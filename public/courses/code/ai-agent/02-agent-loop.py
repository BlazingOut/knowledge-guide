"""第二课示例：最大步数受限的 Agent Loop。"""

from __future__ import annotations

from dataclasses import dataclass, field


# ===== 课程示例：生活管家最小循环 =====


@dataclass
class Decision:
    """模型一步的结构化输出。kind 为 final 或 tool。"""

    kind: str
    text: str = ""
    tool_name: str = ""
    tool_args: dict[str, str] = field(default_factory=dict)


@dataclass
class LifeStore:
    records: dict[str, list[str]] = field(default_factory=dict)
    plans: list[str] = field(default_factory=list)


def search_records(kind: str) -> str:
    items = STORE.records.get(kind, [])
    return f"查询结果：{items}"


def add_plan(title: str) -> str:
    STORE.plans.append(title)
    return f"已添加计划：{title}"


STORE = LifeStore(records={"health": ["周一慢跑"]})
TOOLS = {"search_records": search_records, "add_plan": add_plan}


class ScriptLLM:
    """按观察是否出现过，吐出下一步决策。不执行工具。"""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def decide(self, messages: list[dict[str, str]]) -> Decision:
        contents = " ".join(item["content"] for item in messages)
        if self.mode == "loop":
            if "已添加计划" in contents:
                return Decision(kind="final", text="已经补上今晚跑步。")
            if "查询结果" in contents:
                return Decision(
                    kind="tool",
                    tool_name="add_plan",
                    tool_args={"title": "今晚跑步"},
                )
            return Decision(
                kind="tool",
                tool_name="search_records",
                tool_args={"kind": "health"},
            )
        return Decision(
            kind="tool",
            tool_name="search_records",
            tool_args={"kind": "health"},
        )


def run_loop(
    goal: str,
    llm: ScriptLLM,
    tools: dict[str, object],
    max_steps: int = 6,
) -> str:
    """运行 Agent Loop，返回最终回复。

    每轮：decide → 最终则停止 / 工具则执行并追加观察。
    达到 max_steps 仍无 final 时返回说明字符串。
    """
    messages = [
        {"role": "system", "content": "你是生活管家，按观察决定下一步。"},
        {"role": "user", "content": goal},
    ]
    for step in range(1, max_steps + 1):
        print(f"-- 第 {step} 步，messages={len(messages)} --")
        decision = llm.decide(messages)
        if decision.kind == "final":
            print("最终回复：", decision.text)
            return decision.text
        print("调用工具：", decision.tool_name, decision.tool_args)
        func = tools.get(decision.tool_name)
        if func is None:
            observation = f"未知工具：{decision.tool_name}"
        else:
            observation = func(**decision.tool_args)
        print("观察：", observation)
        messages.append({"role": "tool", "content": observation})
    return "已达最大步数，停止循环"


def main() -> None:
    global STORE
    STORE = LifeStore(records={"health": ["周一慢跑"]})
    print("路径 A：查询后写入")
    print(
        "结果：",
        run_loop("先查运动再决定是否加今晚跑步", ScriptLLM("loop"), TOOLS),
    )
    print("当前计划：", STORE.plans)
    print()
    STORE = LifeStore(records={"health": ["周一慢跑"]})
    print("路径 B：反复查询，命中最大步数")
    print("结果：", run_loop("一直查", ScriptLLM("repeat"), TOOLS, max_steps=3))
    print("当前计划：", STORE.plans)


# ===== 课后作业：学习资料循环 =====


def search_notes(topic: str) -> str:
    return f"笔记摘要：{topic} 尚未掌握间隔重复"


def add_review(title: str) -> str:
    return f"已加入复习：{title}"


class StudyScriptLLM:
    def decide(self, messages: list[dict[str, str]]) -> Decision:
        contents = " ".join(item["content"] for item in messages)
        if "已加入复习" in contents:
            return Decision(kind="final", text="复习计划已写好。")
        if "笔记摘要" in contents:
            return Decision(
                kind="tool",
                tool_name="add_review",
                tool_args={"title": "间隔重复 20 分钟"},
            )
        return Decision(
            kind="tool",
            tool_name="search_notes",
            tool_args={"topic": "记忆方法"},
        )


def run_study_loop(
    goal: str,
    llm: StudyScriptLLM,
    tools: dict[str, object],
    max_steps: int = 6,
) -> str:
    """学习资料场景下的 Loop。要求见课程文档第 7 节。"""
    # TODO 作业：完成循环（初始化 messages、decide、执行工具、追加观察、max_steps）
    raise NotImplementedError("请完成 run_study_loop")


def homework() -> None:
    tools = {"search_notes": search_notes, "add_review": add_review}
    reply = run_study_loop(
        "先找没掌握的概念，再生成一条复习计划",
        StudyScriptLLM(),
        tools,
    )
    print("作业最终回复：", reply)


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
