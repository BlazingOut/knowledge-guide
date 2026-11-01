"""LangGraph 第十课：并行、Send 与子图。

四个演示（全部离线可跑，不需要 API Key）：
- 演示 A：为什么需要并行——静态 fan-out（两个独立工具串行 1.0s vs 并行 0.5s）；
- 演示 B：Send 动态 fan-out + Map-Reduce——批量查多个城市天气，同一 super-step 并行；
- 演示 C：子图——把 ReAct Agent 作为子图嵌入外层图，验证状态隔离；
- 演示 D：并发写同一字段——无 reducer 报 InvalidUpdateError，有 reducer 才合并。

运行：
    python code/langgraph/langgraph_lesson10.py
"""

import operator
import time
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Send


# ---------- 演示 A：为什么需要并行（静态 fan-out） ----------


def slow_weather(city: str) -> str:
    """慢工具：查天气（模拟 0.5s）。"""
    time.sleep(0.5)
    return f"{city}：晴，22℃"


def slow_air(city: str) -> str:
    """慢工具：查空气（模拟 0.5s）。"""
    time.sleep(0.5)
    return f"{city}：空气优"


def build_serial_graph():
    """串行：两个独立查询一个接一个（1.0s）。"""

    class S(TypedDict):
        city: str
        weather: str
        air: str

    def w(state):
        state.update(weather=slow_weather(state["city"]))
        print(f"[w] 天气完成（0.5s 后）")
        return {"weather": state["weather"]}

    def a(state):
        state.update(air=slow_air(state["city"]))
        print(f"[a] 空气完成（0.5s 后）")
        return {"air": state["air"]}

    g = StateGraph(S)
    g.add_node("w", w)
    g.add_node("a", a)
    g.add_edge(START, "w")
    g.add_edge("w", "a")
    g.add_edge("a", END)
    return g.compile()


def build_parallel_graph():
    """并行：两个独立节点从 START 各走一条边（0.5s）。"""

    class S(TypedDict):
        city: str
        weather: str
        air: str

    def w(state):
        time.sleep(0.5)
        print(f"[w] 天气完成")
        return {"weather": f"{state['city']}：晴，22℃"}

    def a(state):
        time.sleep(0.5)
        print(f"[a] 空气完成")
        return {"air": f"{state['city']}：空气优"}

    def merge(state):
        return {}

    g = StateGraph(S)
    g.add_node("w", w)
    g.add_node("a", a)
    g.add_node("merge", merge)
    g.add_edge(START, "w")     # fan-out：两条普通边
    g.add_edge(START, "a")
    g.add_edge("w", "merge")   # fan-in：都汇到 merge
    g.add_edge("a", "merge")
    g.add_edge("merge", END)
    return g.compile()


def demo_parallel():
    """演示 A：两个独立查询，串行 vs 静态并行。"""
    print("--- 演示 A：为什么需要并行 ---")
    t0 = time.perf_counter()
    build_serial_graph().invoke({"city": "上海", "weather": "", "air": ""})
    print(f"串行（w 完再 a）：耗时 {time.perf_counter()-t0:.1f}s")
    print()
    t0 = time.perf_counter()
    build_parallel_graph().invoke({"city": "上海", "weather": "", "air": ""})
    print(f"并行（w、a 同一 super-step）：耗时 {time.perf_counter()-t0:.1f}s")
    print("结论：两个独立任务，串行白白等两次，并行只等最慢的那个")


# ---------- 演示 B：Send 动态 fan-out + Map-Reduce（批量记录处理管线） ----------


class TaskState(TypedDict):
    docs: list                                # 输入：[(doc_id, 原始文本)]，数量由数据决定
    processed: Annotated[list, operator.add]  # fan-in 合并：每条的处理结果追加
    report: str


def model_node(state: TaskState) -> dict:
    """模型节点：确认任务（脚本化），真正的分发交给编排。"""
    print(f"[model] 收到 {len(state['docs'])} 条记录，准备逐条处理")
    return {}


def route_fan_out(state: TaskState) -> list:
    """条件边返回 Send 列表：每条记录一个独立任务（数量由数据决定）。"""
    return [Send("process", {"doc_id": did, "text": text}) for did, text in state["docs"]]


def process_node(state: TaskState) -> dict:
    """处理管线节点（每条记录一个实例，同一 super-step 并行）。

    内部模拟三步管线：清洗 → 分类 → 打标。这是"一个节点被实例化多次、
    每条记录独立走完整个管线"——不是"一个函数被调多次"，工具并行
    （ToolNode 多个 tool_calls）做不到这一步。
    """
    time.sleep(0.3)
    text = state["text"].strip()                        # ① 清洗：去空白
    cat = "运动" if "跑" in text else "其他"             # ② 分类：规则判断
    tag = "#健康" if cat == "运动" else "#日常"          # ③ 打标
    result = f"{state['doc_id']}（{cat}{tag}）：{text}"
    print(f"[process] {state['doc_id']} 处理完成：{result}")
    return {"processed": [result]}


def summarize(state: TaskState) -> dict:
    """fan-in：所有任务完成后才执行，reducer 已把每条结果合并进 state。"""
    print(f"[summarize] 合并 {len(state['processed'])} 条处理结果")
    return {"report": "；".join(state["processed"])}


def build_send_graph():
    g = StateGraph(TaskState)
    g.add_node("model", model_node)
    g.add_node("process", process_node)
    g.add_node("summarize", summarize)
    g.add_edge(START, "model")
    g.add_conditional_edges("model", route_fan_out)   # ← Send 从这里返回
    g.add_edge("process", "summarize")                 # fan-in 普通边
    g.add_edge("summarize", END)
    return g.compile()


def demo_send():
    """演示 B：Send 动态 fan-out + reducer fan-in（Map-Reduce 数据管线）。"""
    print("--- 演示 B：Send 批量处理记录（Map-Reduce） ---")
    app = build_send_graph()
    docs = [
        ("d1", "  跑步 30 分钟  "),
        ("d2", "  晚饭少油少盐  "),
        ("d3", "  睡前不喝咖啡  "),
    ]
    t0 = time.perf_counter()
    final = app.invoke({"docs": docs, "processed": [], "report": ""})
    print(f"3 条记录各走 0.3s 的处理管线，总耗时 {time.perf_counter()-t0:.1f}s（串行会 0.9s）")
    print("最终汇总：", final["report"])
    print("（process 节点被同一 super-step 并行执行 3 次——每条记录走完整管线；")
    print("  注意这不能用工具并行代替：模型没法把'清洗→分类→打标'管线塞进一个 tool_calls）")


# ---------- 演示 C：子图（ReAct Agent 嵌入外层图） ----------


@tool
def calculate(expression: str) -> str:
    """计算一个四则运算表达式，如 "1+1"。"""
    return str(eval(expression, {"__builtins__": {}}, {}))


def build_react_subgraph():
    """子图：完整 ReAct Agent（脚本化模型 + 工具），State 是 MessagesState。"""

    def call_model_fake(state: MessagesState) -> dict:
        last = state["messages"][-1]
        if isinstance(last, ToolMessage):
            return {"messages": [AIMessage(content=f"最终答案：{last.content}")]}
        return {"messages": [AIMessage(
            content="我来计算。",
            tool_calls=[{"name": "calculate", "args": {"expression": "1+1"}, "id": "t1"}])]}

    def route(state):
        return "tools" if state["messages"][-1].tool_calls else END

    g = StateGraph(MessagesState)
    g.add_node("model", call_model_fake)
    g.add_node("tools", ToolNode([calculate]))
    g.add_edge(START, "model")
    g.add_conditional_edges("model", route)
    g.add_edge("tools", "model")
    return g.compile()   # 编译后的图 = 子图


class OuterState(MessagesState):
    request: str    # 外层自己的字段，子图 State 里没有
    reply: str


def router_node(state: OuterState) -> dict:
    """外层路由：把 request 转成子图的输入消息。"""
    print(f"[router] 外层字段 request={state['request']!r}（子图节点访问不到它）")
    return {"messages": [HumanMessage(content=state["request"])]}


def outer_end(state: OuterState) -> dict:
    print(f"[outer_end] 外层看到子图回填的最后一条消息：{state['messages'][-1].content!r}")
    print(f"[outer_end] 外层字段 reply={state['reply']!r} 没被子图碰过")
    return {}


def demo_subgraph():
    """演示 C：子图作为普通节点，共享 messages、隔离其余字段。"""
    print("--- 演示 C：子图（ReAct Agent 嵌入外层图） ---")
    outer = StateGraph(OuterState)
    outer.add_node("router", router_node)
    outer.add_node("agent", build_react_subgraph())   # ← 子图当节点
    outer.add_node("outer_end", outer_end)
    outer.add_edge(START, "router")
    outer.add_edge("router", "agent")
    outer.add_edge("agent", "outer_end")
    outer.add_edge("outer_end", END)
    app = outer.compile()

    result = app.invoke({"messages": [], "request": "1+1 等于几？", "reply": ""})
    print()
    print("外层最终字段：", list(result.keys()))
    print("messages 条数：", len(result["messages"]), "（子图内部完整调用链回填到外层）")
    print("结论：子图只消费/更新自己 State 定义的字段（messages）；外层其他字段子图碰不到")


# ---------- 演示 D：并发写同一字段 ----------


def demo_concurrent_write():
    """演示 D：两个并行节点同时写同一字段——无 reducer 报错，有 reducer 合并。"""
    print("--- 演示 D：并发更新同一字段 ---")

    # D1：无 reducer（LastValue），两个并行节点都写 count
    class S1(TypedDict):
        count: int

    def a(state):
        time.sleep(0.3)
        print("[a] 写 count=1")
        return {"count": 1}

    def b(state):
        time.sleep(0.1)
        print("[b] 写 count=2")
        return {"count": 2}

    def end1(state):
        return {}

    g1 = StateGraph(S1)
    g1.add_node("a", a)
    g1.add_node("b", b)
    g1.add_node("end", end1)
    g1.add_edge(START, "a")
    g1.add_edge(START, "b")
    g1.add_edge("a", "end")
    g1.add_edge("b", "end")
    try:
        g1.compile().invoke({"count": 0})
        print("count：？？？")
    except Exception as exc:
        print(f"count（无 reducer）：图失败 -> {type(exc).__name__}: {str(exc).splitlines()[0]}")

    # D2：有 reducer（Annotated[list, operator.add]），两份都合并
    class S2(TypedDict):
        logs: Annotated[list, operator.add]

    def a2(state):
        time.sleep(0.3)
        return {"logs": ["a"]}

    def b2(state):
        time.sleep(0.1)
        return {"logs": ["b"]}

    def end2(state):
        print(f"logs（有 reducer）：{state['logs']}（两份都在，顺序不定）")
        return {}

    g2 = StateGraph(S2)
    g2.add_node("a", a2)
    g2.add_node("b", b2)
    g2.add_node("end", end2)
    g2.add_edge(START, "a")
    g2.add_edge(START, "b")
    g2.add_edge("a", "end")
    g2.add_edge("b", "end")
    g2.compile().invoke({"logs": []})

    print("结论：并发节点写同一字段必须配 reducer（第 2 课的 Annotated），否则直接报错，不是'后写覆盖'")


def main():
    demo_parallel()
    print()
    demo_send()
    print()
    demo_subgraph()
    print()
    demo_concurrent_write()


# ===== 课后作业 =====


def build_send_graph_v2(docs: list):
    """作业 1：可指定记录列表的 Send Map-Reduce。

    把演示 B 的 route_fan_out 改成从 state 读取 docs（数量可变），
    每条记录走完整处理管线（清洗 → 分类 → 打标）。
    验证：docs=[("d1", "  跑步 30 分钟  "), ..., 5 条]（每条 0.3s 管线）
    总耗时 ≈ 0.3s（并行），report 汇总 5 条处理结果。
    """
    # TODO：实现这个函数（参考 build_send_graph，记录列表可变）
    pass


def build_outer_with_rag_subgraph():
    """作业 2：把第 9 课的 Agentic RAG 图作为子图嵌入外层图。

    外层加一个 router 节点：查询含知识库词才进 RAG 子图，否则直接问候。
    验证外层字段隔离：外层 State 定义 RAG 子图没有的字段，子图不碰它。
    （第 9 课代码 langgraph_lesson09.py 里的 build_agentic_rag_graph 可直接当子图，
     但它的 State 是 RAGState，外层需要包含 RAGState 的全部字段才能驱动它。）
    """
    # TODO：实现这个函数
    pass


def demo_concurrent_field():
    """作业 3：并发写同一字段的验证。

    写两个并行节点，同时 overwrite 一个 int 字段（无 reducer），
    观察 InvalidUpdateError；改成 Annotated[list, operator.add] 观察合并。
    把观察结果写成一段话（运行哪个图、看到什么异常、怎么修）。
    """
    # TODO：实现这个函数（参考演示 D，自己再跑一遍并写出观察）
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    app = build_send_graph_v2([
        ("d1", "  跑步 30 分钟  "),
        ("d2", "  睡前不喝咖啡  "),
        ("d3", "  晚饭少油少盐  "),
        ("d4", "  骑车 10 公里  "),
        ("d5", "  午休 20 分钟  "),
    ])
    final = app.invoke({"docs": [
        ("d1", "  跑步 30 分钟  "),
        ("d2", "  睡前不喝咖啡  "),
        ("d3", "  晚饭少油少盐  "),
        ("d4", "  骑车 10 公里  "),
        ("d5", "  午休 20 分钟  "),
    ], "processed": [], "report": ""})
    assert len(final["processed"]) == 5, final["processed"]
    print("作业 1 通过：5 条记录并行走处理管线，report =", final["report"])

    outer = build_outer_with_rag_subgraph()
    result = outer.invoke({
        "query": "我晚上老是睡不着怎么办",
        "rewritten": "我晚上老是睡不着怎么办",
        "needs_retrieval": False, "hits": [], "best_score": 0.0,
        "attempts": 0, "quality_ok": False, "answer": "", "tag": "outer-only",
    })
    assert result["tag"] == "outer-only", result
    print("作业 2 通过：RAG 子图嵌入外层图，外层字段 tag 未被子图修改")

    demo_concurrent_field()
    print("作业 3 通过：见上面的观察文字")


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
