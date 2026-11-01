"""LangGraph 第七课：interrupt：让图停下来等人确认。

审批流程演示：准备邮件 → interrupt 暂停问外部 → 外部确认后恢复发送。
需要 checkpointer（第 6 课），因为"暂停在哪、怎么恢复"要持久化。

运行：
    python code/langgraph/langgraph_lesson07.py
"""

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class MailState(TypedDict):
    recipient: str  # 收件人
    subject: str    # 邮件主题
    status: str     # 状态：pending 待审批 / approved 已批准 / rejected 已拒绝 / sent 已发送
    mail_id: str    # 邮件唯一编号


def node_prepare(state: MailState) -> dict:
    """节点 1：准备邮件草稿，进入待审批状态。"""
    mail_id = f"mail-{state['recipient']}"
    print(f"[prepare] 草稿就绪：给 {state['recipient']} 发「{state['subject']}」，编号 {mail_id}")
    return {"status": "pending", "mail_id": mail_id}


def node_approve(state: MailState):
    """节点 2：调用 interrupt 暂停，把审批请求抛给外部。

    恢复执行时，interrupt() 的返回值就是外部通过 Command(resume=...) 传回的值。
    """
    decision = interrupt({
        "question": f"是否发送邮件给 {state['recipient']}？",
        "mail_id": state["mail_id"],
    })
    if decision == "confirmed":
        print(f"[approve] 外部确认（{decision!r}），继续发送")
        return {"status": "approved"}
    print(f"[approve] 外部未确认（{decision!r}），取消发送")
    return {"status": "rejected"}


def route_after_approve(state: MailState) -> str:
    """条件边：只有批准才进入发送节点，否则直接结束。"""
    return "send" if state["status"] == "approved" else END


def node_send(state: MailState) -> dict:
    """节点 3：只有 approved 才会走到这里。"""
    print(f"[send] 发送邮件 {state['mail_id']} 给 {state['recipient']}")
    return {"status": "sent"}


def build_mail_graph():
    graph = StateGraph(MailState)
    graph.add_node("prepare", node_prepare)
    graph.add_node("approve", node_approve)
    graph.add_node("send", node_send)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "approve")
    graph.add_conditional_edges("approve", route_after_approve)
    graph.add_edge("send", END)
    return graph.compile(checkpointer=MemorySaver())


def cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def demo_approve_flow():
    """演示 A：完整审批——暂停 → 外部确认 → 恢复 → 发送。"""
    print("--- 演示 A：审批通过 ---")
    app = build_mail_graph()
    result = app.invoke(
        {"recipient": "小明", "subject": "明天开会", "status": "", "mail_id": ""},
        config=cfg("mail-1"),
    )
    intr = result["__interrupt__"][0]
    print("暂停。抛给外部的问题：", intr.value)
    final = app.invoke(Command(resume="confirmed"), config=cfg("mail-1"))
    print("最终 state：", dict(final))


def demo_reject_flow():
    """演示 B：审批拒绝——走 rejected 分支，不发送。"""
    print("--- 演示 B：审批拒绝 ---")
    app = build_mail_graph()
    app.invoke(
        {"recipient": "小红", "subject": "报销单", "status": "", "mail_id": ""},
        config=cfg("mail-2"),
    )
    final = app.invoke(Command(resume="cancel"), config=cfg("mail-2"))
    print("最终 state：", dict(final))


def demo_get_state():
    """演示 C：暂停后查看图停在哪里。"""
    print("--- 演示 C：暂停后查看断点状态 ---")
    app = build_mail_graph()
    app.invoke(
        {"recipient": "小李", "subject": "周报", "status": "", "mail_id": ""},
        config=cfg("mail-3"),
    )
    state = app.get_state(cfg("mail-3"))
    print("下一步节点（next）：", state.next)
    print("当前 values：", dict(state.values))


def main():
    demo_approve_flow()
    print()
    demo_reject_flow()
    print()
    demo_get_state()


# ===== 课后作业：给"删除生活记录"加审批 =====


class DeleteState(TypedDict):
    # TODO：定义状态字段——record_id（要删除的记录 id）、status（已删除 / 已取消）
    pass


def node_confirm(state):
    """作业：调用 interrupt 请求用户确认删除，根据返回值决定状态。

    提示：interrupt({"question": ...})；返回 "yes" 时 status="已删除"，否则 "已取消"。
    """
    # TODO：实现这个函数
    pass


def node_do_delete(state) -> dict:
    """节点：执行删除（只有确认后才会走到这里）。"""
    return {"status": "已删除"}


def build_homework_graph():
    # TODO：组装删除审批图：START → confirm →(条件边)→ do_delete 或 END
    # 注意：interrupt 需要 checkpointer，记得 compile(checkpointer=MemorySaver())
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    app = build_homework_graph()
    app.invoke({"record_id": "rec-1", "status": ""}, config=cfg("del-1"))
    final = app.invoke(Command(resume="yes"), config=cfg("del-1"))
    assert final["status"] == "已删除", final
    app2 = build_homework_graph()
    app2.invoke({"record_id": "rec-2", "status": ""}, config=cfg("del-2"))
    final2 = app2.invoke(Command(resume="no"), config=cfg("del-2"))
    assert final2["status"] == "已取消", final2
    print("作业通过：确认后删除、拒绝后取消")


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
