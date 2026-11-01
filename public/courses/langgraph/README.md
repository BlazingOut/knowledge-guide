# LangGraph 应用开发

目标：面向 AI Agent 开发岗秋招，在阶段 9 手写 Agent 执行循环的基础上，系统掌握 LangGraph 的图执行模型与核心机制，学完后能用"节点、边、状态"解释和设计任何 Agent 应用，并能回答 LangGraph 相关的全部高频面试题。示例优先使用通用场景（多工具助手、带审批的写邮件 Agent、检索问答等），第 4、5、6、11 课和综合项目与 Life Manager 的 `runtime/tool_loop.py`、`agents`、`tools` 对照阅读。

本课程共十三课，原则是**理论先行、实践在后、机制先行、背诵在后**：第 1 至第 3 课建立图的执行模型（节点、边、状态、路由）；第 4 课把工具单独讲透（定义、注册、执行），第 5 课用图组装 ReAct Agent，并在后半部分收拢"图的执行方式"（invoke / stream / config 与事件流）；第 6、7 课深入 LangGraph 区别于其他框架的核心能力（checkpointer 持久化、interrupt 人工介入）；第 8 至第 10 课处理 Agent 工程的真实问题（工具可靠性、Agentic RAG、并行与多 Agent）；第 11、12 课讲集成与评估；第 13 课框架选型与综合复盘。每课都标注"面试考点"，但讲解从机制讲起，不直接给背诵结论。

## 前置知识

- 完成阶段 9：理解 token 与上下文、消息格式、采样参数、结构化输出、tool calling、Embedding、向量检索、RAG、执行循环；**必须**已手写过一个工具调用循环（阶段 9 练习），并阅读过 Life Manager 的 `runtime/tool_loop.py`。
- Python 工程基础：类型标注、`async`/`await`、异常处理、`pytest`。
- 第 11 课额外要求：完成 FastAPI 第 9、10 课（异步接口与流式响应）。
- 会创建 Python 虚拟环境并安装第三方包（阶段 0、1 已覆盖）。

## 课程结构

### 第 1 课：Agent 框架定位与第一个 StateGraph

目标：理解为什么需要 Agent 框架，LangGraph 在整个生态中的定位，跑通第一个图。

内容：手写循环的三个问题——状态散乱在函数参数和返回值里、分支与循环逻辑混在一起、执行过程不可恢复不可观测；Agent 框架解决什么、不解决什么；LangGraph 与 LangChain、AutoGen、CrewAI 的定位差异（本课只做概览，选型对比在第 13 课展开）；StateGraph 的最小构成：`Node`、`Edge`、`State`、`START`、`END`；`compile` 与 `invoke` 的生命周期。

实践：安装 `langgraph`，写一个双节点链式图（两个普通函数节点依次执行），观察 `invoke` 返回的完整 state。

面试考点：为什么用 Agent 框架而不是手写循环；LangGraph 和 LangChain 是什么关系；节点、边、状态分别是什么。

### 第 2 课：State、Channel 与 Reducer

目标：深入理解图的"共享状态"机制，能解释字段合并语义，这是后面所有课程的基础。

内容：State 是图的核心，是节点之间唯一的通信方式；`TypedDict` 声明状态；`Annotated` 与 reducer——为什么需要 reducer、内置的 `operator.add`、自定义 reducer（去重、合并、取最新）；channel 的两种基本语义（保存单值 vs 追加累积）；节点只返回部分状态时如何合并进图状态；并发节点同时更新同一字段的行为；共享状态与副作用的关系（节点应尽量纯函数）。

实践：写一个 append 字段和一个 overwrite 字段，跑多个节点观察合并行为；写一个自定义 reducer（如去重后追加）并验证。

面试考点：reducer 是什么、为什么需要；append 和 overwrite 的区别；两个节点并发更新同一字段会发生什么；为什么节点被建议写成纯函数。

### 第 3 课：节点、普通边与条件边

目标：掌握图的路由机制：节点如何被调度、分支如何产生、循环如何终止。

内容：节点是普通 Python 函数（输入 state 子集 → 输出 state 子集）；普通边表示固定顺序；条件边与路由函数（返回下一个节点名或 `END`）；图的执行是"一次状态更新 = 一个 super-step"，条件边决定下一步；循环与终止条件；`Command` 的引入（节点同时返回状态更新和下一个跳转目标）；与手写 `while` 循环对照：图如何表达同样的逻辑。

实践：实现"循环处理直到满足条件"的图（如计数器累加到阈值），打印每次 super-step 的状态变化；用路由函数实现 if-else 分支。

面试考点：条件边如何决定下一步；图如何实现循环和终止；节点之间靠什么传数据；一次 `invoke` 内部发生了哪几次状态更新。

### 第 4 课：工具：定义、注册与执行

目标：把"工具"讲透——它是什么、`@tool` 怎么从函数生成 StructuredTool、两个"加入"环节、消息数据流与权限边界，为第 5 课组装 ReAct 打基础。

内容：工具的定义与边界（带"说明书"和"校验器"的外部能力接口；工具是无状态函数，不直接读写 State）；StructuredTool 的组成（name / description / args_schema / func）；`@tool` 的机制——从函数签名与 docstring 生成 args_schema（`inspect.signature` + pydantic 校验器，类型标注与 docstring 的作用）；三种定义方式（`@tool` / `@tool("名", ...)` / `StructuredTool.from_function`）；args_schema 与 pydantic 校验（调用前校验、`ValidationError`）；两个"加入"环节——`bind_tools`（把 schema 给模型）vs `ToolNode`（进图执行）；消息数据流 `AIMessage.tool_calls → ToolNode → ToolMessage(tool_call_id)`；权限边界（白名单 + 参数校验）。

实践：用 `@tool` 定义 2~3 个工具（计算器、天气等），观察生成的 name / description / JSON Schema；手动 `invoke` 验证合法参数与缺参数的校验失败；用一个带 `tool_calls` 的 `AIMessage` 直接驱动 `ToolNode`，观察 `ToolMessage` 的产生（无需真实模型）。

面试考点：工具是什么、`@tool` 怎么生成 schema（docstring 和类型标注的作用）；`bind_tools` 和 `ToolNode` 各自解决什么；工具为什么不直接改 State；权限边界的实现。

### 第 5 课：ReAct：把工具接进循环

目标：把第 4 课的工具组装成 ReAct Agent 图，逐行对照手写循环；并在本课后半部分收拢"图怎么被调用"的执行机制。

内容：工具的定义、注册与执行见第 4 课，本课只做组装；ReAct 图的标准形态：LLM 节点 → 条件边判断"需要工具吗" → `ToolNode` 或 `END`；`route_after_model` 的写法（读最后一条消息的 `tool_calls`）；工具异常时模型如何自我修正（`handle_tool_errors` 配置）；图与模型解耦（换 call_model 不改图）；把结果追加进 messages 的 reducer 写法；与手写循环逐行对照，列出图和循环各自的优缺点。后半部分：图的执行方式——invoke 的输入输出与执行语义（输入初始 state → 按路径走 super-step → 返回最终 state）、四种执行方式（invoke / ainvoke / stream / astream）、config 机制（recursion_limit 防失控、thread_id 预告，第 6 课展开）、stream 事件与 super-step 的对应（stream_mode 详解在第 11 课）。

实践：用第 4 课的工具组装 ReAct Agent（脚本化模型离线跑通 + 真实模型调用）；故意让一个工具抛异常，观察模型修正行为；与手写循环对照列出优缺点；用 stream 观察 ReAct 图的每个 super-step（AIMessage → ToolMessage → AIMessage 逐步出现）；用 recursion_limit 掐断失控模型，与作业的 MAX_STEPS 对照（框架硬限制 vs 业务软限制）。

面试考点：ReAct 循环的图表达；route 条件边 = while 条件；工具异常如何回给模型（结合第 4 课的 ToolNode）；为什么工具结果要追加进消息历史而不是覆盖；invoke / stream / ainvoke / astream 的区别；config 里有什么（recursion_limit 防失控、thread_id 会话）。

### 第 6 课：Checkpointer 与持久化（durable execution）

目标：深入理解 LangGraph 的差异化能力——状态持久化与断点续跑，学会用它实现会话记忆和故障恢复。

内容：checkpointer 是什么、存了什么（每个 super-step 之后的状态快照 + 中断点）；checkpointer 类型与存储位置（`MemorySaver`、`SqliteSaver`、`PostgresSaver`）和序列化；`thread_id` 与会话隔离；同一 `thread_id` 下续跑如何从上次 checkpoint 继续；进程崩溃后恢复执行（durable execution 的卖点）；checkpoint 的边界——只存图状态，不存外部资源状态（数据库写入、已发请求无法回滚）。

实践：用 `SqliteSaver` 运行 ReAct Agent，模拟进程崩溃后用同一 `thread_id` 从断点恢复；开两个不同 `thread_id` 验证会话隔离；观察 sqlite 文件里的 checkpoint 内容。

面试考点：checkpoint 存的是什么；`thread_id` 有什么用；进程挂了如何恢复；checkpointer 和数据库存业务数据是什么关系；为什么说"状态持久化"是 LangGraph 区别于手写循环的关键。

### 第 7 课：Human-in-the-loop 与 interrupt

目标：掌握人工介入的机制：图暂停、审批、恢复执行，并处理超时与取消。

内容：为什么需要人工介入（工具执行前审批、高成本操作确认、安全边界）；`interrupt()` 的原理——执行到中断点抛特殊异常暂停图、序列化当前状态、恢复时从断点继续；`interrupt_before`/`interrupt_after` 断点；用 `Command(resume=...)` 或传入同一状态恢复；超时与用户取消（不恢复该 `thread_id` 即可放弃）；与后端接口配合的异步审批流程。

实践：实现"发送邮件前人工确认"流程——第一次 `invoke` 暂停并返回 `interrupt` 信息，用户确认后带 `Command(resume="confirmed")` 恢复；实现超时后放弃（不续跑并清理 checkpoint）。

面试考点：`interrupt` 和普通 `sleep`/`wait` 的区别；恢复执行时状态如何保留；人工审批在工程上如何实现（与 API 的配合）；中断期间外部副作用如何处理。

### 第 8 课：工具调用的可靠性与防护

目标：处理 Agent 工具调用在生产中的真实问题：幻觉参数、格式错误、重复调用、超时、幂等。

内容：工具 schema 设计（清晰描述、参数校验、枚举约束）；模型编造参数的识别与重试策略；工具结果过大或格式异常的处理（截断、结构化返回）；重复调用的幂等设计（唯一请求号、去重）；工具超时与中断（工具执行时长限制）；工具执行的可观测性（每次调用的入参、出参、耗时记录）；权限模型（白名单、敏感操作二次确认）。

实践：给工具加超时包装器；设计一个幂等工具（重复执行不产生副作用，如"更新生活记录"用唯一 ID 去重）；记录一次完整工具调用链的日志并复盘。

面试考点：工具调用失败怎么办；如何防止模型乱调工具或编造参数；工具幂等为什么重要、怎么设计；工具执行超时如何处置。

### 第 9 课：Agentic RAG：检索作为工具

目标：把阶段 9 的传统 RAG 升级为"检索即工具"的 Agentic RAG，理解检索决策与重检索。

内容：传统 RAG 的流程与问题（固定一次检索、查询质量依赖 embedding、无法自我修正）；检索工具化——把向量检索封装成工具让模型按需调用；查询改写与路由（先改写查询再检索、判断是否需要检索）；Agentic RAG 的图形态：判断节点 → 检索节点 → 质量判断节点 → 重检索或生成；何时值得用 Agentic RAG（多一步模型调用，成本与收益权衡）。

实践：把阶段 9 的检索流程改造成图：先判断是否需要检索 → 检索 → 判断结果是否足够 → 不足则改写查询重检索，足够则生成回答；与固定流程 RAG 对比一次结果。

面试考点：Agentic RAG 和普通 RAG 的区别；如何减少幻觉；检索结果不够好怎么办；为什么检索要变成工具而不是固定流程。

### 第 10 课：并行、Send 与子图

目标：掌握并行执行与图组合：fan-out/fan-in、Map-Reduce、子图，理解状态作用域与并发注意事项。

内容：为什么需要并行（多个独立工具、多个子任务）；`Send` API 与动态 fan-out（向同一节点批量发送任务）；Map-Reduce 模式与 reducer 合并结果；子图——嵌套图、子图内外的状态隔离、子图作为普通节点使用；并发节点的注意事项（共享字段合并、外部资源并发访问、限流）；并行不等于更好（成本、限流、调试复杂度）。

实践：用 `Send` 并行调用多个工具再合并结果（如批量查询多个城市的天气再汇总）；把一个完整 Agent 作为子图组合进上层图，验证状态隔离。

面试考点：`Send` 和普通边调用的区别；子图状态如何与外层隔离；什么时候适合并行/多 Agent、什么时候不该用。

### 第 11 课：流式输出与 FastAPI 集成

目标：理解图的事件流机制，把 Agent 跑进 FastAPI 的 SSE/WebSocket 接口。

内容：`stream`/`astream` 的 `stream_mode`（`values`、`updates`、`messages`、`custom` 的区别与各自用途；第 5 课已介绍基础事件结构）；消息事件的结构（增量 token、工具调用事件）与事件出现的顺序；异步节点与异步工具（`async` 节点在什么情况下值得写）；与前端 SSE/WebSocket 的对接方式；客户端断开与资源清理；长任务的超时与取消（结合第 6 课的 checkpoint 续跑）。

实践：写一个 FastAPI SSE 接口，流式返回 Agent 的增量 token 和工具调用事件；测试客户端中途断开后服务端资源正确清理；用 `stream_mode="updates"` 对比 `"messages"` 的输出差异。

面试考点：`stream_mode` 各值的区别；如何把 Agent 跑在后端并流式推给前端；长 Agent 任务超时了怎么办；流式场景下 checkpoint 的作用。

### 第 12 课：Agent 的评估与回归

目标：建立 Agent 评估体系：单元级、轨迹级、LLM-as-judge，用固定评测集防止回归。

内容：Agent 评估什么（最终答案正确性、工具选择是否合理、成本、延迟、安全性）；评测集设计（复用阶段 9 的 10~20 个固定样例，补充边界与对抗用例）；断言方式（规则断言 vs LLM-as-judge，各自优缺点）；轨迹级评估——比较整条工具调用序列而不是只看最终答案；修改前回归对比（改提示词、加工具后跑同一评测集）；量化指标（成功率、平均 token、平均耗时）。

实践：为第 5 课的 ReAct Agent 写评测脚本：跑评测集、统计成功率/工具调用正确率/token 成本；修改一次提示词后跑回归并对比结果，写一份对比记录。

面试考点：Agent 怎么测试；LLM-as-judge 的优缺点；如何防止改一个工具导致整体行为回归；评测样例怎么选。

### 第 13 课：框架选型与综合复盘

目标：能回答"为什么选 LangGraph"的选型题，把全课串成"一个生产 Agent 的完整生命周期"。

内容：框架对比矩阵——LangGraph vs LangChain Agent vs AutoGen vs CrewAI vs 自研循环，从状态管理、持久化、人工介入、流式、可观测性、调试难度、生态与学习成本逐项对比；LangGraph 的边界与坑（学习曲线陡、版本变化快、过度抽象风险）；多 Agent 编排模式（orchestrator-worker、pipeline、层级结构）各自适用场景；完整复盘：从用户消息 → 路由 → 工具调用 → 记忆 → 人工审批 → 流式返回的完整链路，梳理每步的故障与排查手段。

实践：写一份选型笔记：给定需求（如 Life Manager 的日程助手）对比至少三个方案并给出结论；模拟面试问答（"为什么用 LangGraph""什么时候不该用多 Agent"）。

面试考点：为什么用 LangGraph 而不是自研循环；LangGraph vs AutoGen/CrewAI 怎么选；什么时候不该用多 Agent；LangGraph 的局限性。

## 综合练习

用 LangGraph 完整重写 Life Manager 的最小 Agent：工具调用（ReAct 图）+ 会话记忆（`SqliteSaver` checkpoint）+ 人工审批（`interrupt`，写邮件/删除类操作需确认）+ 流式输出（FastAPI SSE）+ 固定评测集回归。产出：可运行的图代码（`code/langgraph/`）、全链路状态变化图（SVG）、一次真实执行的排查笔记（日志 → 定位 → 修复）。

## 阶段验收

学习者应能够：

1. 用"节点、边、状态"解释任意一个 LangGraph Agent 的执行过程，并画出其状态变化。
2. 解释 reducer 合并语义、channel 的两种基本行为，以及并发节点更新同一字段的后果。
3. 独立实现带条件路由与终止条件的循环图，说明一次 `invoke` 内部发生了哪几次状态更新。
4. 能定义工具、解释 `@tool` 从签名生成 schema 的机制，区分 `bind_tools` 与 `ToolNode`，说明 `tool_calls → ToolMessage` 的数据流。
5. 用图实现 ReAct Agent，能对照手写循环说明各自优缺点；能说清 invoke / stream / ainvoke / astream 的差别，用 config 控制 `recursion_limit` 防失控，解释 stream 事件与 super-step 的关系。
6. 解释 checkpoint 存了什么、`thread_id` 如何隔离会话、进程崩溃如何恢复。
7. 实现"暂停 → 审批 → 恢复"的人工介入流程，说明 `interrupt` 与普通等待的区别。
8. 为工具设计 schema、超时、幂等与权限防护，处理工具调用失败与幻觉参数。
9. 实现 Agentic RAG 并说明它与固定流程 RAG 的取舍。
10. 用 `Send` 实现并行 fan-out 与结果合并，解释子图的状态隔离。
11. 把 Agent 接入 FastAPI 的 SSE 接口并处理客户端断开与超时。
12. 用固定评测集 + 规则断言/LLM-as-judge 评估 Agent 并做回归对比。
13. 从状态管理、持久化、调试难度等维度对比 LangGraph 与自研循环、AutoGen、CrewAI，给出选型结论。

## 课程编写约束

- **理论先行、实践在后**：先讲清机制再动手；每个引入的 API（`StateGraph`、reducer、`@tool`、`ToolNode`、checkpointer、`interrupt`、`Send`、`stream_mode`）都要说明它是什么、解决什么问题、输入输出与副作用；值得展开的机制单独成课，不一笔带过。
- 每课只引入少量新概念，先运行观察，再讲解原理；同一知识点不在多课重复展开（工具机制在第 4 课，第 5 课只组装不重讲；stream 机制在第 5 课后半部分入门，第 11 课只讲后端集成）。
- 每课明确标注"面试考点"，但讲解从机制讲起，不直接给背诵结论。
- 在必要处使用 SVG 示意图（状态合并语义、ReAct 循环、checkpoint 快照与恢复、interrupt 暂停恢复、事件流顺序），放在本目录 `assets/` 下，以 `![说明](./assets/xxx.svg)` 引用，沿用本仓库已有风格。
- 实践代码与课后作业放在同一 Python 文件，统一放 `code/langgraph/`，命名 `langgraph_lessonNN.py`；每课作业遵循"关键概念、运行命令、自己的解释、一个错误案例、验收结果"的学习记录惯例。
- 模型调用沿用阶段 9 的兼容 OpenAI 接口方式，不引入新的云服务依赖；可观测性以自建日志为主，LangSmith 不作为本课程的必选依赖。
- 示例优先使用通用场景；第 4、5、6、11 课与综合项目必须与 Life Manager 的 `runtime/tool_loop.py`、`agents`、`tools` 对照阅读，其余课程不强关联项目。
- 必须先完成阶段 9 的手写工具调用循环再开始本课程；课程中的对照练习都以该循环为参照物。
