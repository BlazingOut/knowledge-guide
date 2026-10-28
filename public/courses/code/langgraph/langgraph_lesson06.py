"""LangGraph 第六课：Checkpointer 与持久化（durable execution）。

演示 A（MemorySaver）：会话记忆与线程隔离，无需额外安装；
演示 B（SqliteSaver）：进程重启后从断点恢复，需要安装 langgraph-checkpoint-sqlite
    （langgraph-checkpoint 4.x 起 sqlite 支持被拆成独立包）。

运行：
    python code/langgraph/langgraph_lesson06.py
"""

import os
import sqlite3

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

DB_FILE = os.path.join(os.path.dirname(__file__), "lesson06_checkpoints.db")


@tool
def search_weather(city: str) -> str:
    """查询指定城市的天气。服务偶发不可用时会抛错。"""
    if city == "北京":
        raise ConnectionError("天气服务暂时不可用")
    return f"{city}：晴，22℃"


TOOLS = [search_weather]


def call_model(state: MessagesState) -> dict:
    """脚本化模型：能"记住"历史里的天气结果——记忆来自消息历史本身。"""
    last = state["messages"][-1]

    if isinstance(last, ToolMessage):
        if "不可用" in last.content:
            return {"messages": [AIMessage(
                content="天气服务不可用，换个城市再查。",
                tool_calls=[{"name": "search_weather", "args": {"city": "上海"}, "id": "t2"}])]}
        return {"messages": [AIMessage(content=f"查询结果：{last.content}")]}

    if isinstance(last, HumanMessage):
        if "刚才" in last.content:
            # 从历史里找上一次的天气结果——只有消息历史还在，这一步才做得到
            for m in reversed(state["messages"][:-1]):
                if isinstance(m, ToolMessage) and "上海" in m.content:
                    return {"messages": [AIMessage(content=f"刚才查到的是：{m.content}（来自历史记忆）")]}
            return {"messages": [AIMessage(content="历史里没有天气记录。")]}
        return {"messages": [AIMessage(
            content="我来查天气。",
            tool_calls=[{"name": "search_weather", "args": {"city": "北京"}, "id": "t1"}])]}

    return {"messages": [AIMessage(content="好的。")]}


def route_after_model(state: MessagesState) -> str:
    """条件边：还有工具调用就去 tools，否则结束（同第 5 课）。"""
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END


def build_react_graph(call_model, tools, checkpointer):
    """ReAct 图 + checkpointer：invoke 时多传一个 config 即可区分会话。"""
    graph = StateGraph(MessagesState)
    graph.add_node("model", call_model)
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=lambda e: f"工具执行失败：{e}"))
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route_after_model)
    graph.add_edge("tools", "model")
    return graph.compile(checkpointer=checkpointer)


def cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def demo_memory_session():
    """演示 A：MemorySaver——同一线程的会话记忆 + 线程间隔离。"""
    print("--- 演示 A：会话记忆与线程隔离（MemorySaver） ---")
    app = build_react_graph(call_model, TOOLS, MemorySaver())

    r1 = app.invoke({"messages": [HumanMessage(content="北京今天天气怎么样？")]}, config=cfg("user-1"))
    print("user-1 第一轮：", r1["messages"][-1].content, "（历史", len(r1["messages"]), "条）")

    r2 = app.invoke({"messages": [HumanMessage(content="刚才查的上海天气如何？")]}, config=cfg("user-1"))
    print("user-1 第二轮：", r2["messages"][-1].content, "（历史", len(r2["messages"]), "条）")

    r3 = app.invoke({"messages": [HumanMessage(content="北京天气怎么样？")]}, config=cfg("user-2"))
    print("user-2 第一轮：", r3["messages"][-1].content, "（历史", len(r3["messages"]), "条，与 user-1 完全隔离）")


def demo_crash_resume():
    """演示 B：SqliteSaver——进程重启后，用同一 thread_id 从断点恢复。"""
    print("--- 演示 B：崩溃恢复（SqliteSaver 文件持久化） ---")
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    # "进程 1"：跑完一轮后"退出"（with 结束 = 连接关闭，等价进程结束）
    with SqliteSaver.from_conn_string(DB_FILE) as saver:
        app1 = build_react_graph(call_model, TOOLS, saver)
        r1 = app1.invoke({"messages": [HumanMessage(content="北京今天天气怎么样？")]}, config=cfg("user-3"))
        print("进程 1：", r1["messages"][-1].content, "（历史", len(r1["messages"]), "条，已写入 DB）")

    # "进程 2"：同一个 DB 文件重建全新图实例（等价进程重启）
    with SqliteSaver.from_conn_string(DB_FILE) as saver:
        app2 = build_react_graph(call_model, TOOLS, saver)
        r2 = app2.invoke({"messages": [HumanMessage(content="刚才查的上海天气如何？")]}, config=cfg("user-3"))
        print("进程 2 恢复：", r2["messages"][-1].content)
        print("进程 2 看到完整历史", len(r2["messages"]), "条（消息来自 DB，不是内存）")

    # 观察 DB 内容
    conn = sqlite3.connect(DB_FILE)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    rows = conn.execute("SELECT thread_id, count(*) FROM checkpoints GROUP BY thread_id").fetchall()
    conn.close()
    print("DB 文件：", DB_FILE)
    print("DB 表：", tables, "；checkpoints 行数（按线程）：", rows)


def main():
    demo_memory_session()
    print()
    demo_crash_resume()


# ===== 课后作业：会话封装与清除 =====


def chat(app, thread_id: str, text: str):
    """作业：封装一次对话调用。

    提示：app.invoke({"messages": [HumanMessage(content=text)]}, config=cfg(thread_id))
    """
    # TODO：实现这个函数，返回最终回答字符串
    pass


def homework():
    # TODO：
    # 1. 用 MemorySaver 建一个 app；
    # 2. 线程 a 问"北京天气怎么样？"，线程 b 问"北京天气怎么样？"，线程 a 再问"刚才查的上海天气如何？"；
    # 3. 用 chat() 断言：线程 a 的消息数不受线程 b 影响，且能答出"上海"；
    # 4. 用 checkpointer.delete_thread("a") 清除线程 a 的会话，再问"刚才…"，应回答"历史里没有天气记录。"
    pass


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
