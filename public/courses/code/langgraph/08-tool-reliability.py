"""LangGraph 第八课：工具调用的可靠性与防护。

工具在生产里会怎么坏、怎么防护，六个演示对应六道防线（全部离线可跑，
用脚本化模型，不需要 API Key）：
- 演示 A：幻觉参数——args_schema 校验兜底 + 错误文本回给模型，模型自我修正；
- 演示 B：枚举约束——docstring 的取值说明不是约束，Literal 才是；
- 演示 C：结果异常——截断与结构化返回；
- 演示 D：幂等——唯一请求号去重，重复调用不产生第二次副作用；
- 演示 E：超时——异步工具可真正取消，同步工具只能放弃等待（线程杀不死）；
- 演示 F：可观测性——日志包装器记录每次调用的入参、出参、耗时。

运行：
    python code/langgraph/langgraph_lesson08.py
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


# ---------- 1. 工具定义（沿用第 4/5 课的 calculate，新增带副作用的生活记录工具） ----------


@tool
def calculate(expression: str) -> str:
    """计算一个四则运算表达式，如 "1+1"、"2*3+4"。"""
    if not all(c in "0123456789 +-*/()." for c in expression):
        raise ValueError("表达式包含不允许的字符")
    return str(eval(expression, {"__builtins__": {}}, {}))


@tool
def update_record(record_id: str, action: Literal["create", "update", "delete"], amount: float = 0.0) -> str:
    """更新生活记录。record_id 是记录的唯一编号；action 用 Literal 做枚举约束（只允许 create/update/delete）。"""
    return f"record {record_id} {action} done"


def simple_update(record_id: str, action: str, amount: float = 0.0) -> str:
    """更新生活记录。action 取值 create/update/delete（只是 docstring 里的说明，不是约束）。"""
    return f"record {record_id} {action} done"


RECORD_STORE: dict = {}  # 模拟生活记录存储（演示 D 幂等用）
EXECUTED_KEYS: set = set()  # 已执行过的幂等键


@tool
def update_record_idem(record_id: str, amount: float, idempotency_key: str) -> str:
    """幂等更新生活记录：同一 idempotency_key 只真正执行一次。

    idempotency_key（幂等键）由调用方生成并随每次重试保持不变——
    模型/用户/网络重试时带同一个键，第二次调用直接忽略，不产生重复副作用。
    """
    if idempotency_key in EXECUTED_KEYS:
        return f"重复请求已忽略（键 {idempotency_key} 之前已执行）"
    EXECUTED_KEYS.add(idempotency_key)
    RECORD_STORE[record_id] = amount  # ← 真正写存储的动作只发生一次
    return f"record {record_id} 已更新为 {amount}"


# ---------- 演示 A：幻觉参数——校验兜底 + 错误回喂给模型，模型自我修正 ----------


def call_model_fake(state: MessagesState) -> dict:
    """脚本化模型：第一次编造错误参数名（actionx），收到校验错误后自我修正。"""
    last = state["messages"][-1]
    if isinstance(last, ToolMessage):
        if "Field required" in last.content:
            # 模型读懂了错误文本（缺 action 字段）→ 修正参数重试
            return {"messages": [AIMessage(
                content="参数写错了，修正后重试。",
                tool_calls=[{"name": "update_record", "args": {"record_id": "r1", "action": "create"}, "id": "c2"}])]}
        return {"messages": [AIMessage(content=f"更新成功：{last.content}")]}
    # 第一次：编造一个不存在的参数名 actionx（幻觉参数）
    return {"messages": [AIMessage(
        content="我来更新记录。",
        tool_calls=[{"name": "update_record", "args": {"record_id": "r1", "actionx": "create"}, "id": "c1"}])]}


def route_after_model(state: MessagesState) -> str:
    """条件边：还有工具调用就去工具节点，否则结束。"""
    return "tools" if state["messages"][-1].tool_calls else END


def demo_hallucination():
    """演示 A：模型编造参数 → 校验拦截 → 错误回给模型 → 模型修正重试。"""
    print("--- 演示 A：幻觉参数的自我修正循环 ---")
    graph = StateGraph(MessagesState)
    graph.add_node("model", call_model_fake)
    graph.add_node("tools", ToolNode([update_record], handle_tool_errors=lambda e: f"工具执行失败：{e}"))
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route_after_model)
    graph.add_edge("tools", "model")
    app = graph.compile()
    result = app.invoke({"messages": [HumanMessage(content="创建一条生活记录 r1")]})
    for m in result["messages"]:
        calls = m.tool_calls[0]["name"] if getattr(m, "tool_calls", None) else ""
        print(f"  {type(m).__name__}: {m.content!r} {calls}")
    print("最终回答：", result["messages"][-1].content)

    print()
    print("校验错误文本长这样（回给模型的就是它）：")
    try:
        update_record.invoke({"record_id": "r1", "actionx": "create"})
    except Exception as exc:
        print("  ValidationError：", str(exc).splitlines()[0])
        print("  ", str(exc).splitlines()[1], "<- 缺这个字段，模型靠它定位错误")


# ---------- 演示 B：枚举约束——docstring 不是约束，Literal 才是 ----------


def demo_enum_constraint():
    """演示 B：同样传 action='fly'，普通 str 直接执行，Literal 被校验拦截。"""
    print("--- 演示 B：枚举约束（docstring vs Literal） ---")
    plain_schema = tool(simple_update).args_schema.model_json_schema()
    literal_schema = update_record.args_schema.model_json_schema()
    print("普通 str 的 action 约束：", plain_schema["properties"]["action"])
    print("Literal 的 action 约束：", literal_schema["properties"]["action"])
    print()
    print("传 action='fly'：")
    print("  普通 str ->", simple_update(record_id="r1", action="fly"), "（docstring 说了也不拦）")
    try:
        update_record.invoke({"record_id": "r1", "action": "fly"})
    except Exception as exc:
        print("  Literal ->", type(exc).__name__, "| 文本：", str(exc).splitlines()[2].strip())


# ---------- 演示 C：结果异常——截断与结构化返回 ----------


def demo_result_handling():
    """演示 C：工具结果太大就截断（并告诉模型截断了）；尽量返回结构化数据。"""
    print("--- 演示 C：结果异常的处理 ---")
    big_result = "x" * 10000  # 模拟一个 1 万字符的巨型结果
    max_len = 200
    truncated = big_result[:max_len] + f"…（已截断，原文 {len(big_result)} 字符）"
    print(f"截断：原长 {len(big_result)} -> 返回 {len(truncated)} 字符，末尾注明截断")

    structured = json.dumps(
        {"city": "上海", "temp": 22, "weather": "晴", "humidity": 0.45},
        ensure_ascii=False,
    )
    print("结构化返回（JSON）：", structured)
    print("自由文本 vs 结构化：模型解析 JSON 字段，比从散文里抠数字可靠")


# ---------- 演示 D：幂等——唯一请求号去重 ----------


def demo_idempotency():
    """演示 D：同一幂等键第二次调用被去重，存储只被写一次。"""
    print("--- 演示 D：幂等（唯一请求号去重） ---")
    key = "req-abc"
    print("第 1 次调用：", update_record_idem.invoke({"record_id": "rec-1", "amount": 100.0, "idempotency_key": key}))
    print("第 2 次调用（同键重试，如模型/网络重试）：",
          update_record_idem.invoke({"record_id": "rec-1", "amount": 100.0, "idempotency_key": key}))
    print("存储内容：", RECORD_STORE, "（只被真正写入一次）")
    print("注意：幂等键必须由调用方生成并随重试保持不变；工具内部用时间戳/随机数当键会每次不同，去重失效")


# ---------- 演示 E：超时——异步可取消，同步只能放弃等待 ----------


@tool
async def slow_weather(city: str) -> str:
    """查询天气。模拟慢服务：固定睡 5 秒才返回。"""
    await asyncio.sleep(5)
    return f"{city}：晴，22℃"


async def demo_timeout_async():
    """异步工具：asyncio.wait_for 超时后协程被真正取消（不会残留后台执行）。"""
    print("--- 演示 E1：异步工具超时（可真正取消） ---")
    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(slow_weather.ainvoke({"city": "上海"}), timeout=1.0)
    except asyncio.TimeoutError:
        print(f"等 1 秒超时 -> asyncio.TimeoutError，协程被取消（耗时 {time.perf_counter() - t0:.1f}s）")
    await asyncio.sleep(0.3)
    print("再等 0.3 秒确认：没有后台残留执行")


def demo_timeout_sync():
    """同步工具：线程池 + future.result(timeout)——调用方放弃等待，但线程杀不死。"""
    print("--- 演示 E2：同步工具超时（线程杀不死，只能放弃等待） ---")

    @tool
    def slow_sync(city: str) -> str:
        """查询天气。模拟慢服务。"""
        time.sleep(5)
        return f"{city}：晴"

    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(slow_sync.invoke, {"city": "北京"})
        t0 = time.perf_counter()
        try:
            fut.result(timeout=1.0)
        except FutureTimeoutError:
            print(f"等 1 秒超时 -> TimeoutError（调用方放弃等待，耗时 {time.perf_counter() - t0:.1f}s）")
    print("但后台线程仍在跑（线程无法杀死）——所以超时后别假设'没执行'，重试必须带幂等键（第 5 节）")


# ---------- 演示 F：可观测性——日志包装器 ----------


def logged(fn):
    """给工具函数加日志的装饰器：记录入参、出参、耗时、状态。

    用 functools.wraps 保留原函数签名和 docstring，@tool 生成的 schema 不受影响。
    异常照常抛出（交给 ToolNode 的 handle_tool_errors），日志先记一笔。
    """
    import functools

    @functools.wraps(fn)
    def wrapped(**kwargs):
        t0 = time.perf_counter()
        try:
            out = fn(**kwargs)
            status = "ok"
        except Exception as exc:
            out, status = str(exc), "error"
        dt = (time.perf_counter() - t0) * 1000
        print(f"[tool-log] {fn.__name__} 入参={kwargs} 状态={status} 出参={str(out)[:60]!r} 耗时={dt:.1f}ms")
        return out

    return wrapped


@tool
@logged
def log_weather(city: str) -> str:
    """查询指定城市的天气。服务偶发不可用（模拟外部依赖故障）。"""
    if city == "北京":
        raise ConnectionError("天气服务暂时不可用")
    return f"{city}：晴，22℃"


def demo_observability():
    """演示 F：日志包装器 + 一次完整调用链的日志复盘。"""
    print("--- 演示 F：可观测性（日志包装器） ---")
    print("单次调用（成功与失败各一次）：")
    log_weather.invoke({"city": "上海"})
    try:
        log_weather.invoke({"city": "北京"})
    except ConnectionError:
        pass  # 异常冒泡，由上层（ToolNode）决定回给模型还是让图失败

    print()
    print("完整调用链复盘（模拟一次 ReAct 多轮调用的日志）:")
    chain = [
        ("calculate", {"expression": "1+1"}, "ok", "2", 12.3),
        ("update_record", {"record_id": "r1", "actionx": "create"}, "error", "Field required", 0.4),
        ("update_record", {"record_id": "r1", "action": "create"}, "ok", "record r1 create done", 3.1),
    ]
    for name, args, status, out, ms in chain:
        print(f"  [tool-log] {name} 入参={args} 状态={status} 出参={out!r} 耗时={ms:.1f}ms")
    print("复盘看什么：哪一步状态=error（幻觉参数命中校验）；哪一步耗时异常（>100ms 要查外部依赖）")


# ---------- 主入口 ----------


def main():
    demo_hallucination()
    print()
    demo_enum_constraint()
    print()
    demo_result_handling()
    print()
    demo_idempotency()
    print()
    asyncio.run(demo_timeout_async())  # 异步工具演示需要事件循环
    print()
    demo_timeout_sync()
    print()
    demo_observability()


# ===== 课后作业：超时包装器 + 幂等工具 + 日志复盘 =====


async def search_with_timeout(city: str, timeout: float = 1.0) -> str:
    """作业 1：异步工具的通用超时包装器——超时返回错误文本，而不是抛异常。

    提示：用 asyncio.wait_for(慢工具的 ainvoke({...}), timeout=timeout)，
    捕获 asyncio.TimeoutError 后返回 "工具超时：..."。
    这样超时错误可以像普通工具错误一样回给模型，让模型决定重试还是放弃。
    """
    # TODO：实现这个函数
    pass


def add_reminder(reminder_text: str, idempotency_key: str) -> str:
    """作业 2：幂等工具——同一条提醒（同 idempotency_key）只添加一次。

    用模块级 REMINDERS 列表保存提醒；同一个键重复调用时返回
    "重复请求已忽略"而不是再加一条。
    """
    # TODO：实现这个函数（参考演示 D 的 update_record_idem）
    pass


def review_tool_logs(logs: list) -> str:
    """作业 3：日志复盘——给定一次工具调用链的日志，指出问题。

    logs 是 (工具名, 状态, 耗时ms) 三元组列表。返回一段复盘文字：
    至少指出 ① 哪次调用失败、为什么；② 哪次调用耗时异常。
    示例日志：logs = [("search_weather", "ok", 120), ("update_record", "error", 0.3)]
    """
    # TODO：实现这个函数
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    # 作业 1：超时包装器
    result = asyncio.run(search_with_timeout("上海", timeout=0.2))
    assert result.startswith("工具超时"), result
    print("作业 1 通过：超时返回错误文本 ->", result)

    # 作业 2：幂等
    REMINDERS.clear()
    print("第 1 次：", add_reminder("跑步 30 分钟", "key-1"))
    print("第 2 次：", add_reminder("跑步 30 分钟", "key-1"))
    assert REMINDERS == ["跑步 30 分钟"], REMINDERS
    print("作业 2 通过：同键第二次调用未产生重复提醒 ->", REMINDERS)

    # 作业 3：日志复盘
    review = review_tool_logs([("search_weather", "ok", 120), ("update_record", "error", 0.3)])
    assert "error" in review and "120" in review, review
    print("作业 3 通过：复盘 ->", review)


REMINDERS: list = []  # 作业 2 用的提醒存储


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
