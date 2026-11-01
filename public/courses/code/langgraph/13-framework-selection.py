"""LangGraph 第十三课：框架选型与综合复盘。

综合复盘演示：把全课机制串成一个"带审批的最小生活管家 Agent"——
ReAct 循环（第 5 课）+ checkpointer（第 6 课）+ interrupt 审批（第 7 课）
+ 工具与权限（第 4、8 课）+ 流式输出（第 11 课）。

三条链路（全部离线可跑，脚本化模型）：
- 链路 A：低危工具（计算）——全程自动，无审批；
- 链路 B：高危工具（写生活记录）——interrupt 暂停 → 确认 → 执行；
- 链路 C：高危工具被拒绝——不执行，approved=False。

运行：
    python code/langgraph/langgraph_lesson13.py
"""

from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt


# ---------- 1. 工具：低危计算器 + 高危生活记录（第 4、8 课） ----------


@tool
def calculate(expression: str) -> str:
    """计算一个四则运算表达式，如 "1+1"。"""
    return str(eval(expression, {"__builtins__": {}}, {}))


@tool
def add_reminder(text: str) -> str:
    """添加生活记录（高危：写库，需要人工确认）。"""
    return f"已记录：{text}"


HIGH_RISK = {"add_reminder"}   # 高危工具白名单（第 8 课权限模型：白名单 + 审批）


# ---------- 2. 图：model →(有工具?)→ permission →(approved?)→ tools → model ----------


class AgentState(MessagesState):
    approved: bool   # 审批结果（第 7 课 interrupt 的产出）


def call_model(state: AgentState) -> dict:
    """模型节点（脚本化）：按用户意图发起工具调用。"""
    last = state["messages"][-1]
    if isinstance(last, ToolMessage):
        return {"messages": [AIMessage(content=f"完成：{last.content}")]}
    q = last.content
    if "跑步" in q:
        return {"messages": [AIMessage(content="我来记录。", tool_calls=[
            {"name": "add_reminder", "args": {"text": "跑步 30 分钟"}, "id": "t1"}])]}
    if "1+1" in q:
        return {"messages": [AIMessage(content="我来算。", tool_calls=[
            {"name": "calculate", "args": {"expression": "1+1"}, "id": "t1"}])]}
    return {"messages": [AIMessage(content="你好！我是生活管家。")]}


def route_after_model(state: AgentState) -> str:
    """条件边：还有工具调用 → 先过审批节点；否则结束（第 3、5 课）。"""
    return "permission" if getattr(state["messages"][-1], "tool_calls", None) else END


def check_permission(state: AgentState) -> dict:
    """审批节点：高危工具暂停等人确认；低危工具直接放行（第 7 课）。"""
    names = [c["name"] for c in state["messages"][-1].tool_calls]
    if any(n in HIGH_RISK for n in names):
        decision = interrupt({
            "question": f"要执行高危工具 {names}，同意吗？",
            "options": ["yes", "no"],   # 外部界面渲染成按钮（第 7 课 4.2）
        })
        return {"approved": decision == "yes"}
    return {"approved": True}


def route_permission(state: AgentState) -> str:
    """条件边：批准才执行工具，拒绝直接结束（第 3 课）。"""
    return "tools" if state["approved"] else END


def build_full_agent():
    """组装完整 Agent（第 5 课形态 + 审批节点 + checkpointer）。"""
    g = StateGraph(AgentState)
    g.add_node("model", call_model)
    g.add_node("permission", check_permission)
    g.add_node("tools", ToolNode([calculate, add_reminder], handle_tool_errors=lambda e: f"工具执行失败：{e}"))
    g.add_edge(START, "model")
    g.add_conditional_edges("model", route_after_model)
    g.add_conditional_edges("permission", route_permission)
    g.add_edge("tools", "model")
    return g.compile(checkpointer=MemorySaver())   # 第 6 课：interrupt 必须配 checkpointer


def cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _step_label(chunk) -> str:
    """把 updates chunk 变成 '节点(产出)' 的短标签，用于流式打印。"""
    out = []
    for node, update in chunk.items():
        last = update.get("messages", [None])[-1]
        out.append(f"{node}({type(last).__name__ if last else list(update.keys())})")
    return " → ".join(out)


def demo_auto_flow():
    """链路 A：低危工具（计算），全程自动，流式看到每个 super-step。"""
    print("--- 链路 A：低危工具（1+1），全程无审批 ---")
    app = build_full_agent()
    for chunk in app.stream(
        {"messages": [HumanMessage(content="1+1 是几？")], "approved": False},
        config=cfg("t-a"), stream_mode="updates",
    ):
        print("  super-step:", _step_label(chunk))
    print("  -> 四个 super-step：model 发起 → permission 放行 → tools 执行 → model 总结；无需人工")


def demo_approve_flow():
    """链路 B：高危工具（写生活记录），interrupt 暂停 → 确认 → 执行。"""
    print("--- 链路 B：高危工具（记录跑步），暂停 → 确认 → 执行 ---")
    app = build_full_agent()
    result = app.invoke(
        {"messages": [HumanMessage(content="帮我记录跑步 30 分钟")], "approved": False},
        config=cfg("t-b"),
    )
    payload = result["__interrupt__"][0].value
    print("  暂停。抛给外部：", payload)
    final = app.invoke(Command(resume="yes"), config=cfg("t-b"))
    print("  恢复后最终消息：", final["messages"][-1].content)
    print("  -> 全程串起：工具（第 4 课）→ ReAct（第 5 课）→ checkpoint（第 6 课）→ interrupt 审批（第 7 课）")


def demo_reject_flow():
    """链路 C：高危工具被拒绝 → 不执行。"""
    print("--- 链路 C：高危工具被拒绝 → 不执行 ---")
    app = build_full_agent()
    app.invoke(
        {"messages": [HumanMessage(content="帮我记录跑步 30 分钟")], "approved": False},
        config=cfg("t-c"),
    )
    final = app.invoke(Command(resume="no"), config=cfg("t-c"))
    print("  拒绝后最终消息：", final["messages"][-1].content)
    print("  approved:", final["approved"], "（工具没执行）")


def main():
    demo_auto_flow()
    print()
    demo_approve_flow()
    print()
    demo_reject_flow()
    print()
    print("=== 选型对比矩阵（见文档第 2 节）===")
    print("LangGraph vs LangChain Agent vs AutoGen vs CrewAI vs 自研循环")
    print("对比维度：状态管理 / 持久化 / 人工介入 / 流式 / 可观测性 / 调试难度 / 生态与学习成本")


# ===== 课后作业：选型笔记 + 模拟面试 =====


def selection_note(requirement: dict) -> str:
    """作业 1：给定需求，写一份选型笔记（对比至少三个方案，给出结论）。

    requirement 是一个 dict，例如：
    {"name": "Life Manager 日程助手", "needs": ["多工具调用", "会话记忆", "敏感操作审批", "流式返回"]}

    返回一段 200~300 字的选型结论文字，必须包含：
    - 至少三个候选方案（如 LangGraph / 自研循环 / AutoGen / CrewAI）；
    - 每个方案的"合/不合"理由（对应 requirement 的 needs）；
    - 最终结论一句话。
    """
    # TODO：实现这个函数（参考文档第 2 节对比矩阵和第 6 节决策框架）
    pass


def interview_qa(topic: str) -> str:
    """作业 2：模拟面试问答——按 topic 输出"机制 + 口述模板"。

    topic 取值："为什么用 LangGraph" / "什么时候不该用多 Agent" /
              "LangGraph 的局限性"。
    返回两段文字：第一段机制（2~3 句），第二段口述模板（面试直接说）。
    """
    # TODO：实现这个函数（参考文档第 11 节面试考点的模板结构）
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    note = selection_note({"name": "Life Manager 日程助手", "needs": ["多工具调用", "会话记忆", "敏感操作审批", "流式返回"]})
    assert "LangGraph" in note and ("自研" in note or "AutoGen" in note or "CrewAI" in note), note
    print("作业 1 通过：选型笔记 ->", note)

    for topic in ["为什么用 LangGraph", "什么时候不该用多 Agent", "LangGraph 的局限性"]:
        answer = interview_qa(topic)
        assert "口述模板" in answer and len(answer) > 100
        print(f"作业 2 [{topic}] ->", answer[:80], "...")


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
