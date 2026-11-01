"""LangGraph 第三课：节点、普通边与条件边。

课程示例（build_graph）在上半部分，可直接运行；
课后作业（build_homework_graph）在下半部分，完成后再运行。

运行：
    python code/langgraph/langgraph_lesson03.py
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class State(TypedDict):
    # todo 是待办列表，process 节点每轮取第一条并删除（覆盖写）
    todo: list
    # processed 记录已处理的待办（追加）
    processed: Annotated[list, add]
    # round_count 记录循环轮数（覆盖写）
    round_count: int
    # summary 由汇总节点覆盖写入
    summary: str


def node_process(state: State) -> dict:
    """处理一条待办：取第一条，从 todo 移除，加入 processed。"""
    item = state["todo"][0]
    print(f"[process] 处理待办：{item}")
    return {
        "todo": state["todo"][1:],
        "processed": [item],
        "round_count": state["round_count"] + 1,
    }


def route_todo(state: State) -> str:
    """条件边路由函数：还有待办就继续处理，否则去汇总。"""
    if state["todo"]:
        return "process"
    return "summarize"


def node_summarize(state: State) -> dict:
    summary = f"共处理 {len(state['processed'])} 条待办，循环 {state['round_count']} 轮"
    print(f"[summarize] {summary}")
    return {"summary": summary}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("process", node_process)
    graph.add_node("summarize", node_summarize)
    graph.add_edge(START, "process")
    graph.add_conditional_edges("process", route_todo)
    graph.add_edge("summarize", END)
    return graph.compile()


def demo_command():
    """Command：下一步取决于节点内部的局部结果（异常），路由函数读不到。"""

    class ParseState(TypedDict):
        user_input: str  # 用户输入
        todo: list       # 解析出的待办
        errors: list     # 解析失败的记录
        result: str      # 最终结果

    def parse_todo(text: str) -> dict:
        """解析文本为待办；不包含"待办"二字就抛异常。"""
        if "待办" not in text:
            raise ValueError("未找到待办内容")
        return {"text": text}

    def node_parse(state: ParseState):
        try:
            item = parse_todo(state["user_input"])
        except ValueError as exc:
            print(f"[parse] 解析失败：{exc}")
            return Command(
                update={"errors": [str(exc)], "result": "请重新输入，格式：待办：xxx"},
                goto="retry",
            )
        print(f"[parse] 解析成功：{item}")
        return Command(update={"todo": [item], "result": "已解析"}, goto="finish")

    def node_retry(state: ParseState) -> dict:
        return {}

    def node_finish(state: ParseState) -> dict:
        return {}

    graph = StateGraph(ParseState)
    graph.add_node("parse", node_parse)
    graph.add_node("retry", node_retry)
    graph.add_node("finish", node_finish)
    graph.add_edge(START, "parse")
    graph.add_edge("retry", END)
    graph.add_edge("finish", END)
    ok = graph.compile().invoke({"user_input": "待办：写周报", "todo": [], "errors": [], "result": ""})
    print("[Command] 成功路径：", ok["result"], ok["todo"])
    bad = graph.compile().invoke({"user_input": "帮我看看天气", "todo": [], "errors": [], "result": ""})
    print("[Command] 失败路径：", bad["result"], bad["errors"])


def main():
    app = build_graph()
    result = app.invoke(
        {"todo": ["跑步", "读书", "写周报"], "processed": [], "round_count": 0, "summary": ""}
    )
    print("最终 state：", result)
    print()
    demo_command()


# ===== 课后作业：重试循环 =====


class RetryState(TypedDict):
    attempt_count: int  # 已尝试次数（覆盖）
    success: bool       # 本次是否成功（覆盖）
    result: str         # 最终结果（覆盖）


def node_attempt(state: RetryState) -> dict:
    """模拟一次处理：前两次失败，第三次成功。"""
    attempt = state["attempt_count"] + 1
    if attempt < 3:
        return {"attempt_count": attempt, "success": False}
    return {"attempt_count": attempt, "success": True}


def node_finish(state: RetryState) -> dict:
    return {"result": f"第 {state['attempt_count']} 次尝试成功"}


def route_retry(state: RetryState) -> str:
    """作业：补全路由函数。

    要求：success 为 True 时返回 "finish"，否则返回 "attempt"。
    """
    # TODO：实现这个函数
    return "finish"  # 占位：永远去 finish


def build_homework_graph():
    graph = StateGraph(RetryState)
    graph.add_node("attempt", node_attempt)
    graph.add_node("finish", node_finish)
    graph.add_edge(START, "attempt")
    # TODO：补上 attempt 的条件边（route_retry）和 finish -> END 的普通边
    return graph.compile()


def homework():
    app = build_homework_graph()
    result = app.invoke({"attempt_count": 0, "success": False, "result": ""})
    assert result["attempt_count"] == 3, result["attempt_count"]
    assert result["success"] is True, result["success"]
    assert result["result"], result["result"]
    print("作业通过：", result)


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
