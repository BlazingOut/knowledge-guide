"""LangGraph 第一课：Agent 框架定位与第一个 StateGraph。

课程示例（build_graph）在上半部分，可直接运行；
课后作业（build_homework_graph）在下半部分，完成后再运行。

运行：
    python code/langgraph/langgraph_lesson01.py
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    """节点之间共享的状态。

    本课中每个字段都是"最后一次写入的值覆盖旧值"，
    字段的合并（覆盖/追加、reducer）语义在第 2 课展开。
    """

    user_message: str  # 用户的输入
    echo_count: int  # 已经处理过的节点数
    reply: str  # 生成的回复


def node_receive(state: State) -> dict:
    """节点 1：接收用户消息，把处理次数 +1。

    节点是普通 Python 函数：输入 State，返回要更新的字段组成的 dict。
    只返回自己需要更新的字段，其余字段原样保留。
    """
    print(f"[node_receive] 输入 state: {state}")
    return {"echo_count": state["echo_count"] + 1}


def node_reply(state: State) -> dict:
    """节点 2：根据用户消息生成回复。"""
    print(f"[node_reply] 输入 state: {state}")
    return {"reply": f"收到你的消息：{state['user_message']}（第 {state['echo_count']} 次处理）"}


def build_graph():
    """课程示例：双节点链 START -> receive -> reply -> END。"""
    graph = StateGraph(State)
    graph.add_node("receive", node_receive)
    graph.add_node("reply", node_reply)
    graph.add_edge(START, "receive")
    graph.add_edge("receive", "reply")
    graph.add_edge("reply", END)
    return graph.compile()


def main():
    app = build_graph()
    result = app.invoke(
        {"user_message": "帮我安排明天的会议", "echo_count": 0, "reply": ""}
    )
    print("最终 state：", result)


# ===== 课后作业：给图增加第三个节点 =====


def node_finish(state: State) -> dict:
    """作业：读取 state["reply"]，返回加 [完成] 前缀的新 reply，并让 echo_count 再 +1。

    提示：返回值形如 {"reply": ..., "echo_count": ...}。
    """
    # TODO：实现这个函数
    return {"reply": state["reply"], "echo_count": state["echo_count"]}  # 占位，未实现


def build_homework_graph():
    """作业：在 reply 节点和 END 之间插入 finish 节点。

    执行路径应为 START -> receive -> reply -> finish -> END。
    """
    graph = StateGraph(State)
    graph.add_node("receive", node_receive)
    graph.add_node("reply", node_reply)
    graph.add_node("finish", node_finish)
    graph.add_edge(START, "receive")
    graph.add_edge("receive", "reply")
    # TODO：补上 finish 的两条边（reply -> finish、finish -> END）
    return graph.compile()


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    app = build_homework_graph()
    result = app.invoke(
        {"user_message": "提醒我买牛奶", "echo_count": 0, "reply": ""}
    )
    assert result["reply"].startswith("[完成]"), result["reply"]
    assert result["echo_count"] == 2, result["echo_count"]
    print("作业通过：", result)


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
