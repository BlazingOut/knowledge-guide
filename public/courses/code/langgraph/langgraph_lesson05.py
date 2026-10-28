"""LangGraph 第五课：ReAct：把工具接进循环（tool calling 核心）。

工具的定义、注册与执行见第 4 课；本课把工具组装成 ReAct 图，后半部分
收拢"图的执行方式"（invoke / stream / config）。

代码结构（谁调用谁）：
- 第 1 部分：定义工具（第 4 课讲过，直接使用）；
- 第 2 部分：**真实模型节点**（make_real_call_model）——真实链路里
  "模型节点调用模型、返回 AIMessage"的完整代码；需要安装 langchain-openai
  并设置 OPENAI_API_KEY 才能真跑；
- 第 3 部分：**离线替身**（call_model_fake）——它和真实模型节点是
  **同一个接口**（输入 state → 输出 {"messages": [AIMessage]}），没有 Key 时
  顶替真实模型，让你离线也能看到图的运行（演示 A/B/D/E 离线可跑）；
- 第 4 部分：组装 ReAct 图（工具进图的第 2 步 + 条件边）；
- 演示 C 把替身换成真实模型节点，缺 Key / 缺依赖时打印原因跳过，不崩溃。

运行：
    python code/langgraph/langgraph_lesson05.py
"""

import os

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


# ---------- 1. 定义工具（第 4 课讲过定义，这里直接使用） ----------


@tool
def calculate(expression: str) -> str:
    """计算一个四则运算表达式，如 "1+1"、"2*3+4"。只允许数字和 + - * / ( ) . 空格。"""
    if not all(c in "0123456789 +-*/()." for c in expression):
        raise ValueError("表达式包含不允许的字符")
    return str(eval(expression, {"__builtins__": {}}, {}))


@tool
def search_weather(city: str) -> str:
    """查询指定城市的天气。服务偶发不可用时会抛错（模拟外部依赖故障）。"""
    if city == "北京":
        raise ConnectionError("天气服务暂时不可用")
    return f"{city}：晴，22℃"


TOOLS = [calculate, search_weather]  # 白名单：只允许调这两个


# ---------- 2. 真实模型节点：真实链路里"谁调用谁"的完整代码 ----------


def make_real_call_model(tools):
    """创建真实模型节点（开发期调用一次，得到节点函数）。

    ① 创建模型对象 → ② bind_tools 挂工具（第 4 课第 1 步）→ ③ 返回模型节点。
    返回的节点函数签名和 call_model_fake 完全一样（输入 state，输出消息更新），
    所以换模型不用改图。
    """
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY，跳过真实链路演示")
    llm = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=os.environ.get("OPENAI_BASE_URL"),   # 可选：指向兼容端点
        api_key=api_key,
    )
    llm_with_tools = llm.bind_tools(tools)   # ② 第 4 课第 1 步：说明书挂到模型

    def call_model(state: MessagesState) -> dict:
        """模型节点：调用【模型】（不是工具），返回 AIMessage 追加进消息历史。

        模型只会返回 tool_calls 声明（"我要调 calculate，参数是 {...}"），
        真正执行工具函数的是 ToolNode（第 4 课）。
        """
        response = llm_with_tools.invoke(state["messages"])   # ← 调用的是模型
        return {"messages": [response]}

    return call_model


# ---------- 3. 离线替身：脚本化模型（没有 Key 时顶替真实模型，接口相同） ----------


def call_model_fake(state: MessagesState) -> dict:
    """离线替身：和真实模型节点同一个接口（state → {"messages": [AIMessage]}）。

    它模拟真实模型的三种典型行为，让你没有 Key 也能看到图的运行：
    - 工具报错 → 换个参数重试（模型的自我修正，演示 A）；
    - 拿到工具结果 → 继续调下一个工具（多轮，演示 B）；
    - 拿到全部结果 → 给出最终回答。
    有 Key 时把 build_react_graph(call_model_fake, TOOLS) 换成
    build_react_graph(make_real_call_model(TOOLS), TOOLS)，图的其余部分不用动。
    """
    last = state["messages"][-1]

    if isinstance(last, ToolMessage):
        # 刚拿到工具结果
        if "不可用" in last.content:
            # 情况 1：工具报错 → 换个参数重试（模型自我修正）
            return {"messages": [AIMessage(
                content="天气服务不可用，换个城市再查。",
                tool_calls=[{"name": "search_weather", "args": {"city": "上海"}, "id": "t2"}])]}
        if "上海" in last.content:
            # 情况 2：拿到结果 → 给出最终回答
            return {"messages": [AIMessage(content=f"查询结果：{last.content}")]}
        if last.content == "2":
            # 情况 3：第一轮结果 → 继续调下一个工具（多轮）
            return {"messages": [AIMessage(
                content="第一轮是 2，再算一轮。",
                tool_calls=[{"name": "calculate", "args": {"expression": "2+3"}, "id": "t3"}])]}
        if last.content == "5":
            return {"messages": [AIMessage(content="两轮计算完成，最终结果：2 和 5")]}
        return {"messages": [AIMessage(content=f"结果：{last.content}")]}

    # 第一次调用：根据用户请求决定先调哪个工具
    if "计算" in last.content or "1+1" in last.content:
        return {"messages": [AIMessage(
            content="我来计算。",
            tool_calls=[{"name": "calculate", "args": {"expression": "1+1"}, "id": "t1"}])]}
    return {"messages": [AIMessage(
        content="我来查天气。",
        tool_calls=[{"name": "search_weather", "args": {"city": "北京"}, "id": "t1"}])]}


# ---------- 4. 组装 ReAct 图（工具进图的第 2 步 + 条件边） ----------


def route_after_model(state: MessagesState) -> str:
    """条件边：最后一条 AIMessage 带工具调用 → 去工具节点；否则结束。

    这就是手写循环里的 while 判断条件。
    """
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END


def build_react_graph(call_model, tools):
    """ReAct 图：model →(有工具调用?)→ tools → 回到 model；否则 END。

    第 2 步：ToolNode 进图（第 4 课）——工具函数的真正执行者注册成图的节点。
    图结构和模型无关：换 call_model（替身 / 真实模型）不用改图。
    工具异常默认会让图失败（新版行为）；这里显式配置为把错误文本
    包成 ToolMessage 回给模型，让模型有机会自我修正。
    """
    graph = StateGraph(MessagesState)
    graph.add_node("model", call_model)
    graph.add_node(
        "tools",
        ToolNode(tools, handle_tool_errors=lambda e: f"工具执行失败：{e}"),
    )
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route_after_model)
    graph.add_edge("tools", "model")
    return graph.compile()


# ---------- 演示（A/B/D/E 用离线替身；C 用真实模型） ----------


def _print_messages(messages):
    for m in messages:
        name = type(m).__name__
        calls = m.tool_calls[0]["name"] if getattr(m, "tool_calls", None) else ""
        print(f"  {name}: {m.content!r} {calls}")


def demo_error_recovery():
    """演示 A：工具报错 → 模型自我修正（真实模型也会这样做）。"""
    print("--- 演示 A：天气服务报错后模型换城市重试（离线替身） ---")
    app = build_react_graph(call_model_fake, TOOLS)
    result = app.invoke({"messages": [HumanMessage(content="北京今天天气怎么样？")]})
    _print_messages(result["messages"])
    print("最终回答：", result["messages"][-1].content)


def demo_multi_round():
    """演示 B：连续多轮工具调用（计算器 ×2 → 总结）。"""
    print("--- 演示 B：连续两轮工具调用（离线替身） ---")
    app = build_react_graph(call_model_fake, TOOLS)
    result = app.invoke({"messages": [HumanMessage(content="1+1 和 2+3 各是多少？")]})
    _print_messages(result["messages"])
    print("最终回答：", result["messages"][-1].content)


def demo_real_llm():
    """演示 C：真实模型调用（把替身换成真实模型节点，需 API Key）。"""
    print("--- 演示 C：真实模型调用 ---")
    app = build_react_graph(make_real_call_model(TOOLS), TOOLS)
    result = app.invoke({"messages": [HumanMessage(content="北京天气怎么样？另外 2+3 等于几？")]})
    _print_messages(result["messages"])
    print("最终回答：", result["messages"][-1].content)


def demo_execution():
    """执行方式：stream 逐 super-step 观察 + recursion_limit 防失控。"""
    print("--- 演示 D：stream 逐 super-step 观察（离线替身） ---")
    app = build_react_graph(call_model_fake, TOOLS)
    for chunk in app.stream({"messages": [HumanMessage(content="1+1 是几？")]}, stream_mode="updates"):
        for node, update in chunk.items():
            last = update.get("messages", [None])[-1]
            print(f"  super-step 节点={node}: {type(last).__name__}({getattr(last, 'content', '')!r})")

    print()
    print("--- 演示 E：recursion_limit 防失控 ---")

    def greedy(state: MessagesState) -> dict:
        return {"messages": [AIMessage(
            content="再算一次",
            tool_calls=[{"name": "calculate", "args": {"expression": "1+1"}, "id": "g1"}])]}

    g = StateGraph(MessagesState)
    g.add_node("model", greedy)
    g.add_node("tools", ToolNode(TOOLS, handle_tool_errors=lambda e: f"工具执行失败：{e}"))
    g.add_edge(START, "model")
    g.add_conditional_edges("model", route_after_model)
    g.add_edge("tools", "model")
    app2 = g.compile()
    try:
        app2.invoke({"messages": [HumanMessage(content="开始")]}, config={"recursion_limit": 3})
    except Exception as exc:
        print(f"recursion_limit=3 -> {type(exc).__name__}: {str(exc).splitlines()[0]}")


def main():
    demo_error_recovery()
    print()
    demo_multi_round()
    print()
    try:
        demo_real_llm()
    except (ImportError, RuntimeError) as exc:
        print(f"跳过演示 C：{exc}")
        print("（安装 langchain-openai 并设置 OPENAI_API_KEY 后即可真调用）")
    print()
    demo_execution()


# ===== 课后作业：给 ReAct 循环加"最多 3 轮"防失控 =====


class ReActState(MessagesState):
    # TODO：加一个 step_count 字段（int，覆盖语义），统计模型被调了几轮
    pass


def call_model_greedy(state: ReActState) -> dict:
    """一个"永远想调工具"的脚本化模型：每次都返回工具调用，模拟失控模型。"""
    return {"messages": [AIMessage(
        content="我再算一次。",
        tool_calls=[{"name": "calculate", "args": {"expression": "1+1"}, "id": f"greedy{state['step_count']}"}])]}


def call_model_with_limit(state: ReActState) -> dict:
    """作业：调用模型，并把本轮计数 +1。

    提示：返回 {"messages": [模型输出], "step_count": state["step_count"] + 1}
    """
    # TODO：实现这个函数
    pass


def route_with_limit(state: ReActState) -> str:
    """作业：还有工具调用、且轮数 < 3 → 去 tools；否则 END。

    提示：先取最后一条消息判断 tool_calls，再检查 state["step_count"]
    """
    # TODO：实现这个函数
    pass


def build_homework_graph():
    # TODO：用 ReActState 组装 model / tools 节点与条件边（仿照 build_react_graph）
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    app = build_homework_graph()
    result = app.invoke({"messages": [HumanMessage(content="开始")], "step_count": 0})
    assert result["step_count"] == 3, f"step_count = {result['step_count']}，应在第 3 轮强制结束"
    print("作业通过：第 3 轮后强制结束，step_count =", result["step_count"])


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
