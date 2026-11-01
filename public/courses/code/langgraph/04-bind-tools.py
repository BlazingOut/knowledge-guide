"""LangGraph 第四课：工具：定义、注册与执行。

演示 A / B / C 离线可跑（观察 @tool、校验、ToolNode 行为）；
演示 D 是"真实完整链路"——展示工具从定义到被调用的全部真实代码：
@tool 定义 → bind_tools 挂模型 → 模型节点 → ToolNode 进图 → 完整 ReAct 图。
演示 D 需要安装 langchain-openai 并设置 OPENAI_API_KEY（可选 OPENAI_BASE_URL
指向兼容端点、OPENAI_MODEL）；缺 Key / 缺依赖时打印原因并跳过，不崩溃。

运行：
    python code/langgraph/langgraph_lesson04.py
"""

import json
import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool, tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


# ---------- 1. 定义工具（@tool 生成 StructuredTool） ----------


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


# ---------- 2. 环节一（开发期，写一次）：bind_tools 把说明书挂到模型 ----------

llm_with_tools = None  # 模块级：绑定了工具的模型，模型节点用它


def make_llm_with_tools():
    """创建真实模型并挂上工具说明书。

    需要先安装 langchain-openai（它支持 base_url 指向兼容端点）。
    环境变量：OPENAI_API_KEY（必填）、OPENAI_BASE_URL（可选）、OPENAI_MODEL（可选）。
    """
    global llm_with_tools
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY，跳过真实链路演示")
    llm = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=api_key,
    )
    # ← 环节一：把工具列表挂到模型上，模型由此"知道"有哪些工具、参数长什么样
    llm_with_tools = llm.bind_tools(TOOLS)
    return llm_with_tools


# ---------- 3. 模型节点：调用模型（不是调用工具） ----------


def call_model(state: MessagesState) -> dict:
    """模型节点：调用绑定了工具的模型，把返回的 AIMessage 追加进消息历史。

    注意：这一行调用的是【模型】，不是工具。模型只会返回
    tool_calls 声明（"我要调 calculate，参数是 {...}"），不会执行任何工具函数。
    """
    response = llm_with_tools.invoke(state["messages"])  # ← 调用模型
    return {"messages": [response]}


# ---------- 4. 环节二（开发期，写一次）：ToolNode 进图 + 完整 ReAct 组装 ----------


def route_after_model(state: MessagesState) -> str:
    """条件边：最后一条消息带工具调用 → 去工具节点；否则结束。"""
    last = state["messages"][-1]
    return "tools" if last.tool_calls else END


def build_react_graph():
    """组装完整 ReAct 图：模型节点 + 工具节点 + 条件边。

    ← 环节二：ToolNode(TOOLS) 生成"工具执行节点"，注册进图。
    图执行到 tools 节点时，ToolNode 读 tool_calls、按 name 找到工具、
    调用 calculate.invoke(...)——这才是工具函数的真正执行者。
    """
    graph = StateGraph(MessagesState)
    graph.add_node("model", call_model)                                   # 模型节点
    graph.add_node("tools", ToolNode(TOOLS, handle_tool_errors=lambda e: f"工具执行失败：{e}"))  # 工具节点（环节二）
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route_after_model)
    graph.add_edge("tools", "model")                                      # 执行完回模型，形成循环
    return graph.compile()


# ---------- 演示 A / B / C：离线可跑，观察工具本身的机制 ----------


def demo_tool_anatomy():
    """演示 A：@tool 把一个普通函数变成了什么。"""
    print("--- 演示 A：@tool 生成了什么 ---")
    t = calculate
    print("类型：", type(t).__module__ + "." + type(t).__name__)
    print("name：", t.name)
    print("description：", t.description)
    print("args_schema：", t.args_schema.__name__)
    print("JSON Schema（给模型看的参数说明书）：")
    print(json.dumps(t.args_schema.model_json_schema(), ensure_ascii=False, indent=2))


def demo_invoke_validation():
    """演示 B：invoke 的数据流——先校验，再调用，再包装。"""
    print("--- 演示 B：invoke 的校验 ---")
    print("合法参数：", calculate.invoke({"expression": "1+1"}))
    try:
        calculate.invoke({"expressionx": "1+1"})  # 参数名不对，校验不通过
    except Exception as exc:
        print("参数不对 ->", type(exc).__name__)


def demo_toolnode_drive():
    """演示 C：用带 tool_calls 的 AIMessage 驱动单节点图里的 ToolNode（无需真实模型）。

    这一步就是运行期"工具节点"在做的事：读 tool_calls → 按 name 执行 →
    包成 ToolMessage（靠 tool_call_id 与模型发起的调用一一对应）。
    """
    print("--- 演示 C：ToolNode 执行（工具节点的运行期行为） ---")
    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    app = graph.compile()
    result = app.invoke({
        "messages": [AIMessage(content="", tool_calls=[
            {"name": "calculate", "args": {"expression": "1+1"}, "id": "x1"},
            {"name": "search_weather", "args": {"city": "上海"}, "id": "x2"},
        ])]
    })
    for m in result["messages"]:
        print(f"  {type(m).__name__}: content={m.content!r} tool_call_id={getattr(m, 'tool_call_id', None)}")


# ---------- 演示 D：真实完整链路（需要 API Key） ----------


def demo_real_flow():
    """演示 D：真实链路——完整展示"什么调用了什么"。

    1. 开发期：make_llm_with_tools()（环节一，bind_tools）+ build_react_graph()（环节二，ToolNode 进图）；
    2. 运行期：模型节点调用模型 → 模型返回 tool_calls → 条件边路由 →
       ToolNode 执行工具 → ToolMessage 回填 → 模型再答。
    """
    print("--- 演示 D：真实完整链路（需 OPENAI_API_KEY） ---")
    make_llm_with_tools()          # 环节一：bind_tools，把说明书挂到模型
    app = build_react_graph()      # 环节二 + 组装完整图
    result = app.invoke({"messages": [HumanMessage(content="北京天气怎么样？另外 1+1 等于几？")]})
    for m in result["messages"]:
        name = type(m).__name__
        calls = m.tool_calls[0]["name"] if getattr(m, "tool_calls", None) else ""
        print(f"  {name}: {m.content!r} {calls}")
    print("最终回答：", result["messages"][-1].content)


def main():
    demo_tool_anatomy()
    print()
    demo_invoke_validation()
    print()
    demo_toolnode_drive()
    print()
    try:
        demo_real_flow()
    except (ImportError, RuntimeError) as exc:
        print(f"跳过演示 D：{exc}")
        print("（安装 langchain-openai 并设置 OPENAI_API_KEY 后即可真调用）")


# ===== 课后作业：定义两个新工具并观察 schema =====


def reverse_text(text: str) -> str:
    """作业：定义工具——把字符串反转后返回。

    提示：返回 text[::-1]；补全类型标注（参数 str，返回 str）。
    """
    # TODO：实现这个函数
    pass


def count_reminders(reminders: list) -> int:
    """作业：定义工具——返回生活记录里待办的数量。

    提示：返回 len(reminders)；观察 list 参数在 schema 里的表现。
    """
    # TODO：实现这个函数
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    t1 = tool(reverse_text)  # 等价于给 reverse_text 加 @tool
    t2 = tool(count_reminders)
    print("reverse_text：", t1.name, "|", t1.description)
    print("count_reminders 参数 schema：", t2.args_schema.model_json_schema())
    assert t1.invoke({"text": "跑步"}) == "步跑", t1.invoke({"text": "跑步"})
    assert t2.invoke({"reminders": ["跑步", "读书"]}) == 2, t2.invoke({"reminders": ["跑步", "读书"]})
    manual = StructuredTool.from_function(
        func=reverse_text, name="reverse_text_manual", description="反转字符串（手动构建）"
    )
    print("手动构建与 @tool 生成的是同一类型：", type(manual) is type(t1))
    print("作业通过")


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
