# -*- coding: utf-8 -*-
"""第 8 课机制实测：ValidationError 的形态、handle_tool_errors 回传文本。"""
import json
from langchain_core.tools import tool, StructuredTool
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage

@tool
def update_record(record_id: str, action: str, amount: float = 0.0) -> str:
    """更新生活记录。record_id 是记录的唯一编号；action 取值 create/update/delete。"""
    return f"record {record_id} {action} done"

print("=== 1. args_schema 校验失败：ValidationError 长什么样 ===")
try:
    update_record.invoke({"record_id": "r1", "actionx": "create"})  # 参数名写错
except Exception as e:
    print("异常类型:", type(e).__name__)
    print("str(e) 前 300 字:\n", str(e)[:300])

try:
    update_record.invoke({"record_id": "r1", "action": "fly"})  # 取值超范围
except Exception as e:
    print("\n取值超范围异常类型:", type(e).__name__)
    print("str(e) 前 300 字:\n", str(e)[:300])

print("\n=== 2. handle_tool_errors 把错误文本包进 ToolMessage ===")
tools_node = ToolNode([update_record], handle_tool_errors=lambda e: f"工具执行失败：{e}")
msg = AIMessage(content="", tool_calls=[{"name": "update_record", "args": {"record_id": "r1", "actionx": "create"}, "id": "c1"}])
result = tools_node.invoke({"messages": [HumanMessage(content="hi"), msg]})
tm = result["messages"][-1]
print("ToolMessage type:", type(tm).__name__)
print("ToolMessage.content:", repr(tm.content)[:300])

print("\n=== 3. 默认（不配 handle_tool_errors）行为 ===")
tools_node2 = ToolNode([update_record])
try:
    tools_node2.invoke({"messages": [HumanMessage(content="hi"), msg]})
except Exception as e:
    print("默认行为: 抛异常", type(e).__name__, "| str:", str(e)[:120])
