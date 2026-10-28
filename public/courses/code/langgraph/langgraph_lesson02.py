"""LangGraph 第二课：State、Channel 与 Reducer。

课程示例（build_graph）在上半部分，可直接运行；
课后作业（build_homework_graph）在下半部分，完成后再运行。

运行：
    python code/langgraph/langgraph_lesson02.py
"""

from operator import add
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    # records 是"追加"字段：节点返回的列表会拼接到已有列表之后
    records: Annotated[list, add]
    # step_count 是"覆盖"字段：后写覆盖先写
    step_count: int
    # summary 同样是覆盖字段，由最后一个节点写入
    summary: str


def node_collect(state: State) -> dict:
    """节点 1：采集一条原始生活记录（追加到 records）。"""
    record = {"id": 1, "text": "早上跑步 5 公里", "clean": False}
    print(f"[node_collect] 追加：{record}")
    return {"records": [record], "step_count": state["step_count"] + 1}


def node_clean(state: State) -> dict:
    """节点 2：清洗后追加一条（records 会累积两条）。"""
    cleaned = {"id": 1, "text": "运动：跑步 5 公里", "clean": True}
    print(f"[node_clean] 追加：{cleaned}")
    return {"records": [cleaned]}


def node_summarize(state: State) -> dict:
    """节点 3：汇总已有记录，覆盖写入 summary。"""
    summary = f"今天共有 {len(state['records'])} 条记录，已处理 {state['step_count']} 步"
    print(f"[node_summarize] 覆盖写入 summary：{summary}")
    return {"summary": summary}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("collect", node_collect)
    graph.add_node("clean", node_clean)
    graph.add_node("summarize", node_summarize)
    graph.add_edge(START, "collect")
    graph.add_edge("collect", "clean")
    graph.add_edge("clean", "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()


def demo_concurrent_write():
    """同一 super-step 内两个节点写同一字段：普通字段报错，reducer 字段合并。"""

    def write_step_a(state: State) -> dict:
        return {"step_count": 1}

    def write_step_b(state: State) -> dict:
        return {"step_count": 2}

    graph = StateGraph(State)
    graph.add_node("a", write_step_a)
    graph.add_node("b", write_step_b)
    graph.add_edge(START, "a")
    graph.add_edge(START, "b")
    graph.add_edge("a", END)
    graph.add_edge("b", END)
    try:
        graph.compile().invoke({"records": [], "step_count": 0, "summary": ""})
    except Exception as exc:
        print(f"[普通字段] 两个节点同时写 step_count -> {type(exc).__name__}: {exc}")

    def append_a(state: State) -> dict:
        return {"records": [{"id": "a"}]}

    def append_b(state: State) -> dict:
        return {"records": [{"id": "b"}]}

    graph2 = StateGraph(State)
    graph2.add_node("a", append_a)
    graph2.add_node("b", append_b)
    graph2.add_edge(START, "a")
    graph2.add_edge(START, "b")
    graph2.add_edge("a", END)
    graph2.add_edge("b", END)
    result = graph2.compile().invoke({"records": [], "step_count": 0, "summary": ""})
    print(f"[reducer 字段] 两个节点同时追加 records -> {result['records']}")


def demo_add_messages():
    """add_messages 的三种行为：新 id 追加、同 id 替换、RemoveMessage 删除。"""
    merged = add_messages(
        [HumanMessage(content="你好", id="1")],
        [AIMessage(content="你好！", id="2")],
    )
    print("[add_messages] 新 id 追加：", [(type(m).__name__, m.content) for m in merged])

    replaced = add_messages(
        [HumanMessage(content="你好", id="1")],
        [HumanMessage(content="你好（修改后）", id="1")],
    )
    print("[add_messages] 同 id 替换：", [(m.content, m.id) for m in replaced])

    removed = add_messages(
        [HumanMessage(content="a", id="1"), AIMessage(content="b", id="2")],
        [RemoveMessage(id="1")],
    )
    print("[add_messages] RemoveMessage 删除：", [(m.content, m.id) for m in removed])


def main():
    app = build_graph()
    result = app.invoke({"records": [], "step_count": 0, "summary": ""})
    print("最终 state：", result)
    print()
    demo_concurrent_write()
    print()
    demo_add_messages()


# ===== 课后作业：自定义去重 reducer =====


def dedup_append(current: list, update: list) -> list:
    """作业：按 id 去重后追加。

    返回一个新列表：先复制 current，再把 update 中 id 尚未出现过的条目加进去。
    不要原地修改 current。
    """
    # TODO：实现这个函数
    return current + update  # 占位：未去重


class HomeworkState(TypedDict):
    records: Annotated[list, dedup_append]


def homework_node_a(state: HomeworkState) -> dict:
    return {"records": [{"id": 1, "text": "跑步"}, {"id": 2, "text": "读书"}]}


def homework_node_b(state: HomeworkState) -> dict:
    return {"records": [{"id": 2, "text": "读书（重复）"}]}


def build_homework_graph():
    graph = StateGraph(HomeworkState)
    graph.add_node("a", homework_node_a)
    graph.add_node("b", homework_node_b)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)
    return graph.compile()


def homework():
    app = build_homework_graph()
    result = app.invoke({"records": []})
    ids = [r["id"] for r in result["records"]]
    assert ids == [1, 2], f"去重失败：{result['records']}"
    print("作业通过：", result)


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
