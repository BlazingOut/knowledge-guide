# 第七课：interrupt：让图停下来等人确认

前六课学会的是"让 Agent 全自动跑"：节点、工具、状态、持久化。但生产中不是所有操作都该全自动——发邮件、删记录这类**不可逆副作用**，最好在动手前让真人确认一下。本课讲 LangGraph 为此提供的机制 `interrupt`：执行到节点内部停下来，把"要不要继续"抛给外部，等人拍板后再从断点恢复。

范围：本课只讲 `interrupt()`（节点内部的审批点）与恢复；编译期断点 `interrupt_before`/`interrupt_after`（在节点**之前/之后**固定位置暂停）存在，但本课不展开，面试提到时知道区别即可。超时与取消在第 4.4 节讲，工具可靠性是下一课的事。

前置：第 6 课（checkpoint——`interrupt` 必须配合 checkpointer 才能"记住暂停在哪"）；第 3 课（条件边，本课的拒绝分支用到；`Command` 在第 3 课已见过）。

**学习目标：**

1. 能一句话说清 `interrupt` 是什么，为什么必须配 checkpointer；
2. 能画出审批流程：第一次 `invoke` 暂停 → 外部拿到问题 → `Command(resume=...)` 恢复；
3. 能解释"恢复时节点从头重跑、`interrupt()` 直接返回 resume 值"这个机制；
4. 能实现拒绝分支（条件边）和超时放弃（不续跑该线程）；
5. 能说出 `interrupt` 与 `sleep`/普通等待的本质区别。

## 1. 背景：全自动 Agent 的风险

一个全自动的 Agent 会把"用户消息 → 调工具 → 返回结果"一路跑完。遇到**副作用不可逆**的工具时，全自动就有风险：邮件发出去了不能撤回、生活记录删了不能还原。第 4 课的权限边界第三层叫"敏感操作人工确认"——本课就是这一层的实现机制。

需求很明确：图执行到"发邮件"之前，**暂停**，把"要发这封邮件，同意吗？"抛给外部（人），拿到答案后再决定继续发还是取消。暂停不是报错，也不是等待几秒，而是"执行到一半挂起，等一个外部决定"。下一节看 LangGraph 用什么表达这个"暂停"。

## 2. interrupt 是什么：节点里的"询问点"

LangGraph 提供的暂停函数叫 `interrupt(value)`，本课第一个新概念，当场定义：

- **`interrupt(value)`**：只能在**节点内部**调用的函数。执行到这一行，图**暂停**；`value`（一个任意值，通常是个问题描述）被抛给外部调用者；之后恢复执行时，这个函数**返回**外部传回的值。

一句话类比：`interrupt()` 像函数里的"询问点"——跑到这里，把问题递给函数外面的人，然后挂起；外面的人把答案递回来，函数从询问点继续往下走。

讲"暂停"离不开一个词：**断点**——图暂停的位置。`interrupt()` 的断点在**节点内部**那一行；编译期还有 `interrupt_before`/`interrupt_after`，断点在节点**之前/之后**（本课不展开，知道区别即可）。

边界要分清（三条都影响后面的使用）：

- `interrupt` **必须配合 checkpointer**（第 6 课）。暂停在哪、暂停时的状态是什么，都要落盘才能恢复；没配 checkpointer 直接报错。
- `interrupt` 只在**节点内部**有效，不能在工具里调（工具是无状态函数，第 4 课）。
- 一个节点可以多次调用 `interrupt`（多次审批），但本课只讲单次审批。

## 3. 机制：暂停、恢复与重跑

`interrupt` 的机制用一个例子讲透。以"发邮件前确认"为例，图长这样（节点 2 内部有 `interrupt()`）：

```text
第一次 invoke（thread=t1）：
  START → prepare ──→ approve ──(interrupt 暂停)──→ [返回给外部：中断信息]

外部看到问题，决定"同意"，恢复：
  approve（从 interrupt() 返回 'confirmed'）──→ send ──→ END
```

**暂停时发生什么**（演示 A 的输出佐证）：

1. `prepare` 执行完，状态更新落盘；
2. `approve` 执行到 `interrupt()` 这一行，图暂停——`value` 被放进 **invoke 的返回值**，外部从那里拿到问题。返回值的这个字段叫 **`__interrupt__`**：第一次 `invoke` 后，`result["__interrupt__"][0].value` 就是要问的问题（第 4.2 节演示怎么取）；
3. 暂停的位置（断点在 `approve` 内部）连同状态一起记进 checkpoint——第 4.3 节用 `get_state` 能查出来。

**恢复时发生什么**（这是 `interrupt` 和普通等待最不同的地方）：再次 `invoke` 时，不再传"新消息"，而是传 `Command(resume=...)`——本课第二个新概念，就地定义：

- **`Command(resume=value)`**：恢复执行时作为 `invoke` 的**输入**传入的对象（第 3 课见过 `Command(update=, goto=)`，本课用的是它的另一个用途）。`resume` 参数的值就是 `interrupt()` 恢复后返回的东西。

恢复时，`approve` 节点**从头重新执行**，但 `interrupt()` 这一行不再暂停，而是直接返回 `"confirmed"`，节点继续往下走（`status="approved"` → 条件边 → `send`）。观察演示 A 的输出：`[approve] 外部确认` 是在恢复后才打印的——节点函数被重新调用了。

**这个"重跑"带来一个必须记住的细节**：`interrupt()` 之前的代码会执行两次（暂停前一次、恢复后一次）。如果那段代码有副作用（写文件、发请求），恢复时会重复执行——第 5 节常见错误的第一条。

**为什么能"记住"暂停点？** 因为 checkpoint（第 6 课）：暂停时图状态和断点位置都落盘了，恢复 = 从最近 checkpoint 继续，未执行完的节点重跑。

机制到此讲完，第 4 节把这些机制落到代码上。

## 4. 实践用法：邮件审批流程

课程代码 `code/langgraph/langgraph_lesson07.py`。组装分三步：审批节点、条件边、编译。

### 4.1 审批流程代码

**节点 2（审批点）**——`interrupt()` 的值就是问题，返回值就是答案。注意 `value` 可以是**任意值**：本课用一个 dict 描述问题（比字符串能带更多结构化信息）；真实工程里还会往 `value` 里放**选项列表**，供外部界面渲染成审批按钮（见 4.2）：

```python
def node_approve(state: MailState):
    decision = interrupt({
        "question": f"是否发送邮件给 {state['recipient']}？",
        "mail_id": state["mail_id"],
    })
    if decision == "confirmed":
        return {"status": "approved"}
    return {"status": "rejected"}
```

**条件边（拒绝分支）**——只有批准才走到发送节点，否则直接结束（第 3 课的条件边，这里就是它的实际用途）：

```python
def route_after_approve(state: MailState) -> str:
    return "send" if state["status"] == "approved" else END
```

**编译**——`interrupt` 的前提是 checkpointer，这里把第 6 课的 `MemorySaver` 配进去：

```python
app = graph.compile(checkpointer=MemorySaver())
```

### 4.2 完整调用：暂停 → 确认 → 恢复

演示 A 的两次 `invoke` 就是完整审批流。第一次 `invoke` 结束于暂停点，返回值里带着中断信息（第 3 节提过的 `__interrupt__`，这里第一次取它）：

```python
# 第一次：图暂停在审批点，拿到要问的问题
result = app.invoke({"recipient": "小明", "subject": "明天开会", "status": "", "mail_id": ""},
                    config={"configurable": {"thread_id": "mail-1"}})
question = result["__interrupt__"][0].value   # {'question': '是否发送邮件给 小明？', ...}
```

外部（人）确认后，恢复执行——用第 3 节定义过的 `Command(resume="confirmed")` 作为**输入**，并传**同一个 `thread_id`**（第 6 课：断点按线程存，换线程就找不到暂停点）：

```python
# 外部（人）确认后：恢复执行
final = app.invoke(Command(resume="confirmed"),
                   config={"configurable": {"thread_id": "mail-1"}})
# final["status"] == "sent"
```

强调一点：`Command(resume=...)` 是 `invoke` 的**输入**，不是 config——这是最容易搞混的地方（第 5 节常见错误第二条）。

**带选项的审批：选项从哪来**——你可能会想："真实产品里 Agent 会给我好几个选项（批准/拒绝）"。那些选项**不是框架自动生成的**，而是开发者放进 `value` 里的。把选项列表加进中断信息：

```python
decision = interrupt({
    "question": f"是否发送邮件给 {state['recipient']}？",
    "options": ["confirmed", "cancel"],   # 外部界面渲染成两个按钮
    "mail_id": state["mail_id"],
})
```

外部拿到 `value` 后把它渲染成带按钮的审批卡片；用户点了哪个，就把哪个作为 `Command(resume=选项值)` 传回，`interrupt()` 返回的就是它（运行验证过）：

```text
外部拿到的 payload： {'question': '是否发送邮件给 小明？', 'options': ['confirmed', 'cancel'], ...}
渲染成按钮： ['[confirmed]', '[cancel]']
用户点 confirmed → Command(resume="confirmed") → interrupt() 返回 "confirmed" → status="approved"
```

所以 `interrupt` 的职责只有一个：**把 `value` 原样抛出去、把 `resume` 原样收回来**。抛什么、收什么、怎么展示，都由开发者在上层产品里设计。

### 4.3 暂停后查看断点

暂停后想确认"图停在哪"，用 `get_state`——本课第三个新概念，就地定义：

- **`app.get_state(config)`**：查询某个线程当前的图状态。返回对象的 `.next` 字段是"下一步要执行的节点"——**暂停时显示的就是断点所在节点**。

运行演示 C 能看到：第一次 `invoke` 暂停后，`get_state(cfg("mail-3")).next` 显示 `('approve',)`，图确实停在 `approve` 节点内部。

### 4.4 超时与取消

外部一直不恢复，这个线程的图就一直挂着（状态在 checkpoint 里，不占资源）。要放弃：**不恢复该线程**即可；要清理：`checkpointer.delete_thread(thread_id)`（第 6 课学过）把断点状态清掉。

## 5. 常见错误

1. **忘了配 checkpointer**：`interrupt` 直接报错——暂停在哪要落盘才能恢复，没有 checkpointer 就"记不住"断点。
2. **恢复时把 `Command(resume=...)` 当成新输入**：`invoke({"新消息"}, config=...)` 不会把答案递给 `interrupt()`，图行为不对；必须用 `Command(resume=答案)` 作为输入。
3. **换了 `thread_id` 恢复**：断点按线程存，换线程就找不到原来的暂停点了。
4. **在 `interrupt()` 之前写了副作用代码**：节点重跑时这段代码执行两次（见第 3 节），副作用会重复——副作用代码放在 `interrupt()` 之后，或保证幂等（第 8 课）。
5. **把 `interrupt` 当等待**：它不是"睡 3 秒再继续"，而是"挂起等外部决定"——状态、断点都持久化了，恢复靠 `Command(resume=...)`。

## 6. 运行课程代码

```bash
cd c:\0work\project\ai_application_development_study
python code/langgraph/langgraph_lesson07.py
```

依次打印：演示 A（审批通过：暂停 → 确认 → 发送）、演示 B（审批拒绝：不发送）、演示 C（暂停后 `get_state` 显示断点在 `approve`）。

## 7. 课后作业

作业和课程示例在同一个文件中：`code/langgraph/langgraph_lesson07.py`，从 `# ===== 课后作业 =====` 开始。

给"删除生活记录"加审批（迁移自邮件审批，组合了 interrupt + 条件边两个要点）：

1. 补全 `DeleteState`：定义 `record_id`（要删除的记录 id）和 `status`（已删除 / 已取消）；
2. 完成 `node_confirm`：调用 `interrupt({"question": ...})`，返回值是 `"yes"` 时 `status="已删除"`，否则 `"已取消"`；
3. 在 `build_homework_graph()` 里组装图：`START → confirm →(条件边)→ do_delete 或 END`，**记得 `compile(checkpointer=MemorySaver())`**；
4. 运行 `homework()`（完成后取消 `__main__` 注释）：线程 del-1 恢复 `"yes"` → 状态"已删除"；线程 del-2 恢复 `"no"` → 状态"已取消"；
5. 思考题：为什么 `node_confirm` 里的 `interrupt()` 之前不能放"真的删除"的代码？如果放了会发生什么？（答案在第 5 节第 4 条）

## 8. 验收问题 / 过关清单

能回答：

1. `interrupt(value)` 是什么？为什么必须配 checkpointer？
2. 审批流程的两次 `invoke` 各做了什么？恢复时 `Command(resume=...)` 的值去了哪里？
3. 恢复时节点是怎么继续的？"`interrupt()` 之前的代码执行两次"意味着什么？
4. 拒绝分支怎么实现？超时/取消怎么处理？
5. `interrupt` 和 `sleep` 的本质区别是什么？

## 9. 面试高频考点

答案分机制和口述模板两层，面试时按模板说：

**Q1：`interrupt` 和普通 `sleep`/等待有什么区别？**
机制：`sleep` 只是时间流逝，程序继续往下走；`interrupt` 是图**挂起**，状态和断点都通过 checkpoint 持久化，恢复靠外部显式传回 `Command(resume=...)`，可以"想停多久停多久、由人决定而不是由定时器决定"。
口述模板："`interrupt` 是 durable 的暂停——暂停位置和状态都落盘了，外部确认后从断点恢复继续；`sleep` 只是阻塞等待，没有'断点'这个概念。"

**Q2：恢复执行时节点内部发生了什么？**
口述模板："恢复时，暂停的节点函数从头重新执行，`interrupt()` 这一行不再暂停而是直接返回 `Command(resume=...)` 传回的值，代码从那里继续。所以 `interrupt()` 之前的代码会执行两次，有副作用的代码不能放在它前面。"

**Q3：为什么 `interrupt` 必须配合 checkpointer？**
口述模板："因为要'记住暂停在哪'——断点位置和暂停时的状态都要持久化，恢复时从最近 checkpoint 继续。没有 checkpointer，图就不知道从哪里继续。"

**Q4：审批（human-in-the-loop）在工程上怎么和 API 配合？**
口述模板："第一次请求跑图，图在 `interrupt()` 处暂停，把要审批的内容放进返回值；后端把内容展示给用户；用户确认后，后端带着 `Command(resume=确认结果)` 和同一个 `thread_id` 再调一次图，从断点恢复。取消就是不恢复，或 `delete_thread` 清理。"

**Q5：中断期间的副作用怎么处理？**
口述模板："`interrupt()` 之前和之后都可能执行副作用——之前会因节点重跑执行两次，之后是恢复后才执行。要么把副作用放在 `interrupt()` 之后，要么让副作用幂等（第 8 课）。"

## 下一课预告

第 8 课《工具调用的可靠性与防护》：`interrupt` 解决了"敏感操作要人确认"，下一课解决工具在生产里"会怎么坏、怎么防护"——幻觉参数、重复调用、超时、幂等。
