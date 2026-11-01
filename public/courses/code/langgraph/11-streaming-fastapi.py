"""LangGraph 第十一课：流式输出与 FastAPI 集成。

五个演示：
- 演示 A：stream_mode="values" vs "updates" 的输出差异；
- 演示 B：stream_mode="messages" 的消息事件流（含节点元数据）；
- 演示 C：stream_mode="custom" 自定义事件（get_stream_writer）；
- 演示 D：FastAPI SSE 接口（真实代码，需要 pip install fastapi uvicorn；
  缺依赖时打印原因跳过——离线也能跑 A/B/C/E）；
- 演示 E：客户端断开与资源清理（协程取消时 finally 善后）。

全部模型节点用脚本化替身，不需要 API Key。

运行：
    python code/langgraph/langgraph_lesson11.py
"""

import asyncio
import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


# ---------- 共用的 ReAct 图（离线替身模型 + 计算器工具） ----------


@tool
def calculate(expression: str) -> str:
    """计算一个四则运算表达式，如 "1+1"。"""
    return str(eval(expression, {"__builtins__": {}}, {}))


def call_model_fake(state: MessagesState) -> dict:
    """脚本化模型：先发起工具调用，拿到结果后给最终答案。"""
    last = state["messages"][-1]
    if isinstance(last, ToolMessage):
        return {"messages": [AIMessage(content=f"最终答案：{last.content}")]}
    return {"messages": [AIMessage(
        content="我来计算。",
        tool_calls=[{"name": "calculate", "args": {"expression": "1+1"}, "id": "t1"}])]}


def route_after_model(state: MessagesState) -> str:
    return "tools" if getattr(state["messages"][-1], "tool_calls", None) else END


def build_react_graph():
    g = StateGraph(MessagesState)
    g.add_node("model", call_model_fake)
    g.add_node("tools", ToolNode([calculate]))
    g.add_edge(START, "model")
    g.add_conditional_edges("model", route_after_model)
    g.add_edge("tools", "model")
    return g.compile()


IN = {"messages": [HumanMessage(content="1+1 是几？")]}


# ---------- 演示 A：values vs updates ----------


def demo_stream_modes():
    """演示 A：values 给完整 state，updates 只给节点更新。"""
    print("--- 演示 A：stream_mode=values vs updates ---")
    app = build_react_graph()

    print("values（每个 super-step 后的完整 state，4 个 chunk）：")
    for i, chunk in enumerate(app.stream(IN, stream_mode="values")):
        last = chunk["messages"][-1]
        print(f"  chunk{i}: {type(last).__name__} {last.content!r}")

    print("updates（每个 super-step 的节点更新，3 个 chunk）：")
    for i, chunk in enumerate(app.stream(IN, stream_mode="updates")):
        print(f"  chunk{i}: {list(chunk.keys())} <- 只有产生更新的节点")


# ---------- 演示 B：messages 事件流 ----------


def demo_messages_stream():
    """演示 B：messages 模式的事件流——(消息, 元数据) 元组。"""
    print("--- 演示 B：stream_mode=messages（消息事件流） ---")
    app = build_react_graph()
    for i, (msg, metadata) in enumerate(app.stream(IN, stream_mode="messages")):
        print(f"  事件{i}: {type(msg).__name__} content={msg.content!r} node={metadata.get('langgraph_node')}")
    print("说明：真实 LLM 下这里会是 token 增量（AIMessageChunk 一条条蹦出来）；")
    print("脚本化替身一次给整条消息。事件顺序：AIMessage → ToolMessage → AIMessage。")


# ---------- 演示 C：custom 自定义事件 ----------


def demo_custom_stream():
    """演示 C：custom 模式——节点里用 get_stream_writer 写自定义事件。"""
    print("--- 演示 C：stream_mode=custom（get_stream_writer） ---")

    from typing import TypedDict

    class S(TypedDict):
        x: int

    def node_a(state):
        writer = get_stream_writer()          # 在节点里拿写入器
        writer({"stage": "a_start", "x": state["x"]})
        writer({"stage": "a_progress", "pct": 50})
        return {"x": state["x"] + 1}

    def node_b(state):
        get_stream_writer()({"stage": "b_done", "x": state["x"]})
        return {}

    g = StateGraph(S)
    g.add_node("a", node_a)
    g.add_node("b", node_b)
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    app = g.compile()

    for chunk in app.stream({"x": 0}, stream_mode="custom"):
        print("  ", chunk)
    print("用途：进度上报（写文件 30%/70%）、阶段通知——前端不用解析消息结构，只收自定义 JSON")


# ---------- 演示 D：FastAPI SSE 接口（真实代码，缺依赖跳过） ----------


def build_sse_app():
    """FastAPI SSE 接口：把 astream 的 messages 事件流转成 text/event-stream。

    需要：pip install fastapi uvicorn
    启动：uvicorn langgraph_lesson11:sse_app --reload（模块内已导出的 sse_app）
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse

    app = FastAPI()
    react_app = build_react_graph()

    @app.post("/chat")
    async def chat(request: Request):
        body = await request.json()
        question = body.get("message", "")

        async def gen():
            # astream 惰性生成：边跑图边产出事件
            async for msg, metadata in react_app.astream(
                {"messages": [HumanMessage(content=question)]},
                stream_mode="messages",
            ):
                # SSE 格式：data: JSON\n\n；客户端断开时这里抛 CancelledError
                payload = {
                    "type": type(msg).__name__,
                    "content": msg.content,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


def demo_sse():
    """演示 D：SSE 接口（需要 fastapi）。缺依赖时打印原因跳过。"""
    print("--- 演示 D：FastAPI SSE 接口 ---")
    try:
        sse_app = build_sse_app()
    except ImportError as exc:
        print(f"跳过演示 D：{exc}")
        print("（pip install fastapi uvicorn 后即可启动：uvicorn langgraph_lesson11:sse_app）")
        return
    print("SSE 接口已构建：POST /chat，media_type=text/event-stream")
    print("启动：uvicorn langgraph_lesson11:sse_app --reload")

    # 不真起服务器，离线演示 SSE 事件文本长什么样：
    async def show_sse_text():
        print("离线演示 SSE 事件格式（和接口产出一致）：")
        async for msg, metadata in build_react_graph().astream(IN, stream_mode="messages"):
            payload = {"type": type(msg).__name__, "content": msg.content}
            print(f"  data: {json.dumps(payload, ensure_ascii=False)}")
        print("  data: [DONE]")

    asyncio.run(show_sse_text())


# ---------- 演示 E：客户端断开与资源清理 ----------


def demo_disconnect_cleanup():
    """演示 E：协程取消时，生成器的 except CancelledError/finally 必须善后。"""
    print("--- 演示 E：客户端断开（任务取消）与资源清理 ---")

    async def sse_generator():
        """模拟 SSE 生成器：客户端断开 -> 任务被取消，CancelledError 抛进来。"""
        resource = {"opened": True}
        try:
            for i in range(5):
                await asyncio.sleep(0.2)
                yield f"data: {{'chunk': {i}}}\n\n"
        except asyncio.CancelledError:
            # 客户端断开：消费生成器的任务被取消，异常在这里被捕获
            resource["opened"] = False
            print("  [cleanup] 客户端断开，资源已清理（数据库连接归还/文件关闭）")
            raise  # 重新抛出，让框架正常结束
        finally:
            resource["opened"] = False

    async def client():
        """模拟前端：消费生成器，收 2 条后任务被取消（= 客户端断开）。"""
        gen = sse_generator()

        async def consumer():
            count = 0
            async for chunk in gen:
                print("  收到：", chunk.strip())
                count += 1
                if count >= 2:
                    await asyncio.sleep(1.0)   # 前端停止消费，然后断开

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.6)               # 等消费者收 2 条
        task.cancel()                          # 客户端断开 -> 取消任务 -> 取消生成器
        try:
            await task
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(0.2)               # 给生成器的 finally 一点时间

    asyncio.run(client())
    print("结论：SSE 生成器必须 try/except CancelledError + finally——断开时清理资源，而不是让连接挂着")


def main():
    demo_stream_modes()
    print()
    demo_messages_stream()
    print()
    demo_custom_stream()
    print()
    demo_sse()
    print()
    demo_disconnect_cleanup()


# ===== 课后作业 =====


async def stream_updates_vs_messages():
    """作业 1：自己观察 updates 和 messages 的输出差异，写一段对比。

    提示：对同一个图分别 stream_mode="updates" 和 "messages"，
    打印每个 chunk 的"结构"（dict 键名 / 消息类型），观察：
    - updates 一个 super-step 一个 dict（{节点: 更新}）；
    - messages 是消息级事件（(消息, 元数据)），super-step 内部可能多条。
    返回一段结论文字。
    """
    # TODO：实现这个函数
    pass


def build_sse_for_weather():
    """作业 2：给"多工具 Agent"加 SSE 接口。

    在第 5 课 langgraph_lesson05.py 的 ReAct 图基础上，写一个 FastAPI SSE 接口：
    POST /chat 流式返回消息事件（含工具调用事件）。缺 fastapi 时打印原因。
    """
    # TODO：实现这个函数（参考 build_sse_app）
    pass


async def long_task_with_timeout():
    """作业 3：长任务的超时与取消。

    用 asyncio.wait_for 给一个模拟的"慢 Agent 流"设 1 秒超时；
    超时抛 TimeoutError/CancelledError，finally 里打印"资源已清理"。
    观察：超时后生成器被取消，但清理代码执行了。
    """
    # TODO：实现这个函数
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    import asyncio as _aio

    conclusion = _aio.run(stream_updates_vs_messages())
    assert "super-step" in conclusion and "messages" in conclusion
    print("作业 1 通过：", conclusion)

    try:
        build_sse_for_weather()
    except ImportError as exc:
        print("作业 2：缺 fastapi 跳过（", exc, "）")
    else:
        print("作业 2 通过：SSE 接口已构建")

    _aio.run(long_task_with_timeout())
    print("作业 3 通过：超时后清理代码执行")


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
