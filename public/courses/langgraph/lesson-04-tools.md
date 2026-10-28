不是简单地直接添加，而是修改一下“加入的两个环节”这一部分，说明如果想要加入的话，需要有两步：
第一步干嘛干嘛。
第二步干嘛干嘛。
如果其中某一步失败了会怎么样，这个列表也要列进去。# 第四课：工具：定义、注册与执行

前三课学完了图的零件：节点、状态、边。第 5 课要组装 ReAct Agent 时，"工具"会是图里最常出现的东西，但它的分量值得单独一课——工具不是"一个函数"这么简单：它要自动生成给模型看的参数说明书（schema）、在调用前做校验、在执行后变成消息。本课把工具讲透：它是什么、`@tool` 怎么工作、两个"加入"环节的区别、消息数据流和权限边界。

范围：本课只讲工具的**正常形态**。ReAct 循环的组装在第 5 课；工具在生产里"会怎么坏、怎么防护"（幻觉参数、幂等、超时）在第 8 课；多工具并行执行在第 10 课。

前置：完成第 1~3 课（图执行模型）；理解 tool calling 的消息格式——`AIMessage` 能带 `tool_calls`、工具结果回填成 `ToolMessage`。

**学习目标：**

1. 能用一句话定义工具，说出 StructuredTool 的四件套；
2. 能解释 `@tool` 从函数签名生成 `args_schema` 的机制（docstring 和类型标注的作用）；
3. 能说清加入工具的两步（`bind_tools` / `ToolNode`）各自做什么，缺一步会怎样；
4. 能画出 `tool_calls → ToolMessage` 的数据流，解释 `tool_call_id` 的作用；
5. 能实现权限边界：白名单 + 参数校验。

## 1. 工具的定义与边界

一句话定义：**工具是 Agent 可以调用、自带"说明书"和"校验器"的外部能力接口**。

- "说明书"：name、description、参数 schema——给模型看，模型据此决定调不调、怎么调；
- "校验器"：调用前先检查参数，不合法就不执行底层函数；
- "外部能力"：查天气、算数、写文件、调 API……任何普通函数能做的事。

工具和普通函数的区别就在这三样：普通函数只有代码，工具在代码外面套了一层"模型可见的元数据 + 调用前的校验"。模型的 tool calling 之所以能工作，靠的就是这一层。

**关键边界：工具是无状态函数，不直接读写 State。** 它接收参数、返回内容（字符串），不接触消息历史，也不知道"这是第几轮对话"；要不要把结果写进状态、写哪个字段，由**节点**决定（第 5 课）。工具就像乐高块，节点是拼装的人。

本课用两个工具做贯穿示例（第 5 课组装 ReAct 也会用它们）：`calculate`（计算器，纯函数）和 `search_weather`（查天气，模拟外部依赖会偶发报错）。

## 2. StructuredTool 的四件套与 @tool 机制

`@tool` 把一个普通函数变成的是一个 `StructuredTool` 对象，它有四件套：

| 组成部分 | 内容 | 从哪来 |
| --- | --- | --- |
| `name` | 工具名，模型用它发起调用 | 函数名（可覆盖） |
| `description` | 工具干什么、什么时候用 | docstring（可覆盖） |
| `args_schema` | 参数校验模型（pydantic） | 函数签名自动生成 |
| `func` | 底层函数本身 | 原函数 |

机制分三步（以 `langchain-core` 1.6.x 源码为据）：

1. **装饰器分派**：`@tool`（无参）把函数本身传进来，`@tool(...)`（带参）返回一个再包函数的 `_partial`，殊途同归到同一个工厂；
2. **选实现**：默认 `infer_schema=True`，走 `StructuredTool.from_function`；
3. **填四件套**：`name = name or func.__name__`、`description = description or func.__doc__`，而 `args_schema = create_schema_from_function(name, func)`——它用 `inspect.signature(func)` 拿函数签名和类型标注，交给 **pydantic v2 的 `create_model`** 动态生成一个校验模型（1.6.x 源码最后一行就是 `create_model(name, **fields)`），过滤掉 `self`/`cls`、`config` 等运行时注入参数，剩下的字段就是参数模型。

所以 **docstring 和类型标注不是可选项**：description 和参数类型/必填全部来自它们。没有 docstring，模型就不知道工具是干什么的；没有类型标注，schema 就无法推断参数该填什么。

实测（运行演示 A）：`calculate` 的 JSON Schema 长这样——正是 `bind_tools` 最终给模型看的东西：

```json
{
  "description": "计算一个四则运算表达式，如 \"1+1\"...",
  "properties": { "expression": { "title": "Expression", "type": "string" } },
  "required": ["expression"],
  "type": "object"
}
```

## 3. 三种定义方式

定义工具有三条路，生成的都是同一类对象（`StructuredTool`），区别只是"元数据从哪里来"。三条路都要先导入：

```python
from langchain_core.tools import StructuredTool, tool
```

**方式一：`@tool`（最常用）**——名字 = 函数名、描述 = docstring、参数 schema = 签名自动生成：

```python
@tool
def calculate(expression: str) -> str:
    """计算一个四则运算表达式，如 "1+1"。"""
    return str(eval(expression, {"__builtins__": {}}, {}))
```

**方式二：`@tool("改名", parse_docstring=True)`**——覆盖工具名，并让 docstring 里的 `Args:` 段成为每个参数的描述（Google 风格 docstring）：

```python
@tool("计算器", parse_docstring=True)
def calc(expression: str) -> str:
    """计算表达式。

    Args:
        expression: 四则运算表达式，如 "1+1"。
    """
    return str(eval(expression, {"__builtins__": {}}, {}))
```

**方式三：`StructuredTool.from_function(...)`（全手动）**——名字、描述、schema 全部显式传，适合运行时动态构造工具（比如从配置生成）：

```python
def _reverse(text: str) -> str:
    return text[::-1]

reverse_tool = StructuredTool.from_function(
    func=_reverse,
    name="reverse_text",
    description="把字符串反转后返回",
)
```

三种方式对比（小结）：

| 写法 | 效果 |
| --- | --- |
| `@tool` | 最常用：名字=函数名、描述=docstring、schema=签名自动生成 |
| `@tool("改名", parse_docstring=True)` | 覆盖名字；从 docstring 的 `Args:` 段提取每个参数的描述 |
| `StructuredTool.from_function(func, name=, description=, args_schema=)` | 全手动，适合运行时动态构造工具 |

## 4. args_schema 与校验

`args_schema` 是一个 pydantic 模型（BaseModel 子类），`invoke` 时的数据流是：

```text
tool.invoke({"expression": "1+1"})
  → args_schema 先校验（参数名、类型、必填）
  → 校验失败：ValidationError，底层函数根本不会执行
  → 校验通过：调用底层函数
  → 返回值包装成工具结果（默认作为 ToolMessage 的 content）
```

运行演示 B 能看到：合法的 `{"expression": "1+1"}` 返回 `"2"`；参数名写错（`expressionx`）直接抛 `ValidationError`——**错误在调用函数之前就被拦下了**，这是校验器的价值：模型偶尔会编造参数，校验层兜底，而不是让 Python 在函数内部炸出各种奇怪的错误。

## 5. 加入工具：两步，缺一不可（本课核心）

先回答最容易卡住的问题：**工具函数到底是谁在调用？** 答案是——运行期**不是模型在调**，而是图里的 `ToolNode` 在调。模型只做一件事：返回一段"我要调用 calculate，参数是 {...}"的**声明**（`tool_calls`）；真正执行你的函数的是工具节点。

**把工具加进 Agent 需要两步，缺一不可**（都发生在开发期，各写一行代码）：

- **第 1 步 `bind_tools`（发起端）**：把工具的"说明书"挂到模型上——让模型知道有工具、会发起调用；
- **第 2 步 `ToolNode`（执行端）**：把工具执行节点注册进图——让图能执行模型发起的调用。

```python
# 第 1 步：bind_tools，把工具的"说明书"挂到模型上（开发期，你写一次）
llm_with_tools = llm.bind_tools(tools)

# 第 2 步：ToolNode 进图（开发期，你写一次）
from langgraph.prebuilt import ToolNode   # ToolNode 是库自带的预建节点，不用自己写
graph.add_node("tools", ToolNode(tools))
```

为什么是"两步"而不是一步：模型是"发起者"，图是"执行者"，两端必须配套。5.1、5.2 分别讲两步怎么操作，5.3 看运行期完整链条，5.4 列出"缺一步会怎样"（都实测过——**都不崩溃，都是静默失效**）。

### 5.1 第 1 步：`bind_tools`——工具怎么进"模型"

`bind_tools(tools)` 把工具列表挂到**模型对象**上，改的是模型，不改图。完整的顺序是：**先创建模型对象，再往上挂工具，最后在模型节点里调用**：

```python
from langchain_openai import ChatOpenAI   # 需要先 pip install langchain-openai

# ① 创建模型对象。ChatOpenAI 是模型封装类，走 OpenAI 兼容接口，
#    base_url 可指向任何兼容端点（密钥只从环境变量读，不写进代码）
llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    base_url=os.environ.get("OPENAI_BASE_URL"),   # 可选：指向兼容端点
    api_key=os.environ.get("OPENAI_API_KEY"),     # 必填
)

# ② 把工具挂到模型上（bind_tools）。模型还是那个模型，
#    只是多带了一层"工具说明书"——它知道有哪些工具、参数长什么样
llm_with_tools = llm.bind_tools(tools)

# ③ 模型节点里调用"带工具的模型"
def call_model(state):
    response = llm_with_tools.invoke(state["messages"])   # ← 这行调用的是模型，不是工具
    return {"messages": [response]}
```

三个要点：`llm_with_tools.invoke(messages)` 的输入输出和 `llm.invoke(messages)` 完全一样，唯一区别是返回时**可能带 `tool_calls`**；`bind_tools` 只改模型不改图，图里没出现任何工具信息；工具列表就是白名单——只把允许的工具传进去。

作用：模型拿到工具的 JSON Schema（第 2 节那个），生成 `tool_calls` 时参数会遵守它。不调用 `bind_tools`，模型根本不知道有工具存在，永远不会发起调用。

### 5.2 第 2 步：`ToolNode`——工具怎么进"图"

**`ToolNode` 不是你自己写的**——它是 `langgraph.prebuilt` 里现成的"预建节点"，从库导入即可：

```python
from langgraph.prebuilt import ToolNode   # 库自带，不用自己写实现

tool_node = ToolNode(tools, handle_tool_errors=lambda e: f"工具执行失败：{e}")
graph.add_node("tools", tool_node)    # 注册成图的节点
graph.add_edge("tools", "model")      # 执行完回到模型（第 5 课组装时加上）
```

它内部做三件事（不需要你操心，但要知道）：读最后一条 `AIMessage` 的 `tool_calls` → 按 name 找到工具对象 → 调用它的 `invoke`，把结果包成 `ToolMessage` 回填。你只需要构造它（传入工具列表）再注册进图。`handle_tool_errors` 参数控制工具抛异常时怎么办（把错误回给模型 vs 让图失败，第 5 课展开）。

作用：图执行到 `tools` 节点时，`ToolNode` 就是上面说的"真正执行者"。不注册 `ToolNode`，模型发起了 `tool_calls` 也无人执行。

### 5.3 运行期：谁调用谁（完整链路）

```text
开发期（你各写一行，各发生一次）：
  llm_with_tools = llm.bind_tools(tools)     # 第 1 步：说明书挂到模型
  graph.add_node("tools", ToolNode(tools))   # 第 2 步：执行节点注册进图

运行期（图执行时自动发生）：
  模型节点   llm_with_tools.invoke(messages)
             → 返回 AIMessage(tool_calls=[{name: "calculate", args: {...}, id: ...}])
  图调度     条件边看到有 tool_calls → 路由到 tools 节点（第 5 课）
  工具节点   ToolNode 按 name 找到 calculate → 调用 calculate.invoke({...})
             → 结果包成 ToolMessage 追加回 messages
  模型节点   再次调用模型，看到工具结果，给出最终回答（第 5 课）
```

**核心澄清**：模型"说"要调工具（生成 `tool_calls`），ToolNode 才"真的调"了工具（执行 `calculate.invoke`）。**这两个动作的执行者不是同一个**——分不清这一点，就分不清两步。

### 5.4 缺一步会怎样（实测）：两步都是"静默失效"

| 缺哪一步 | 现象（实测） | 怎么发现 |
| --- | --- | --- |
| 缺第 1 步 `bind_tools` | 模型不知道有工具，**从不发起调用**：图正常跑完、Agent 直接"回答"，但工具一次都没执行过——messages 里没有任何 `ToolMessage` | 看返回的消息里有没有 `ToolMessage` |
| 缺第 2 步 `ToolNode` | 模型发起了 `tool_calls`，但条件边路由到不存在的 `tools`：**编译不报错**，运行期只打印一条警告（`wrote to unknown channel branch:to:tools, ignoring it`），图停在半路、**没有最终回答** | 有工具调用，但对应位置没有 `ToolMessage`；翻日志找那条警告 |

**两种都不崩溃——这是最危险的地方**：缺第 1 步让你的 Agent 悄悄退化成"没有工具的问答机"；缺第 2 步让它"想调工具却执行不了"。这也呼应第 3 课那个坑：**条件边指向不存在的节点不会报错**——缺第 2 步就是它的活例子。

两步对比（小结）：

| | 第 1 步 `bind_tools(tools)` | 第 2 步 `ToolNode(tools)` |
| --- | --- | --- |
| 作用 | 把工具**说明书**挂到模型上 | 把工具**执行逻辑**挂进图 |
| 谁消费 | 模型：据此生成 `tool_calls` | 图：按名字匹配并执行工具 |
| 位置 | 模型节点调用模型之前 | 作为图里的一个节点 |
| 开发期还是运行期 | 开发期，你写一次 | 开发期，你写一次 |

一句话：**第 1 步回答"工具怎么进模型"，第 2 步回答"工具怎么进图"**。两步都要有，Agent 才能"模型发起调用 → 图执行工具"；缺一步的后果见 5.4。

**白名单**就是在这两步上实现的：只把允许调用的工具传进 `bind_tools` 和 `ToolNode` 的列表，Agent 就永远调不到列表之外的工具。

## 6. 消息数据流

一次工具调用的完整消息链：

```text
模型返回：AIMessage(tool_calls=[{name, args, id}])
   ↓
ToolNode 按 name 匹配工具，执行
   ↓
追加回 messages：ToolMessage(tool_call_id=id, content=结果)
```

运行演示 C 能看到一条 `AIMessage` 带两个 `tool_calls` 时，`ToolNode` 会各执行一次并返回两个 `ToolMessage`——**靠 `tool_call_id` 和模型发起的调用一一对应**，不会混淆。多工具并行时（第 10 课）这个 id 对应关系就是唯一的分辨手段。

工具结果以 `ToolMessage` 追加进 messages（`add_messages` reducer，第 2 课），同 id 的消息会被替换——这也是工具调用链能完整保留、模型下一轮能看到全部上下文的原因。

## 7. 权限边界

三层防护，从外到内：

1. **白名单**：`bind_tools` 和 `ToolNode` 只注册允许的工具（第 5 节）；
2. **参数校验**：`args_schema` 的类型和取值约束（第 4 节），`calculate` 里的字符白名单是自定义校验的示例；
3. **敏感操作人工确认**：写邮件、删除这类高风险工具，执行前要人确认——第 7 课的 `interrupt` 就是干这个的。

## 8. 运行课程代码

```bash
cd c:\0work\project\ai_application_development_study
python code/langgraph/langgraph_lesson04.py
```

依次打印：`@tool` 生成的四件套与 JSON Schema（演示 A）、invoke 的校验行为（演示 B）、`ToolNode` 执行两个工具调用的消息链（演示 C）、**真实完整链路**（演示 D：bind_tools 挂模型 → 模型节点 → ToolNode 进图 → 完整 ReAct 图；需 `OPENAI_API_KEY`，缺 Key 时打印原因跳过）。

## 9. 课后作业

作业和课程示例在同一个文件中：`code/langgraph/langgraph_lesson04.py`，从 `# ===== 课后作业 =====` 开始。

1. 实现 `reverse_text`（字符串反转）和 `count_reminders`（统计待办数量），补全 docstring 和类型标注；
2. 运行 `homework()`（完成后取消 `__main__` 注释）：用 `tool(reverse_text)` 包装它们，打印 name / description / args_schema，观察**字符串参数和 list 参数在 schema 里的差异**；
3. 验证 `reverse_text.invoke({"text": "跑步"})` 返回 `"步跑"`、`count_reminders.invoke({"reminders": [...]})` 返回数量；
4. 用 `StructuredTool.from_function` 手动构建一个工具，确认它与 `@tool` 生成的是同一类型；
5. 思考题：把 `count_reminders` 的 docstring 删掉再运行，`description` 会变成什么？这说明了什么？

## 10. 验收问题

1. 一句话定义工具？StructuredTool 的四件套是什么、各自从哪来？
2. `@tool` 是怎么从函数签名生成 `args_schema` 的？docstring 和类型标注为什么不是可选项？
3. `bind_tools` 和 `ToolNode` 各自解决什么？少了哪个会怎样？**运行期真正执行工具函数的是谁？**
4. 一次工具调用的消息数据流是什么？`tool_call_id` 有什么用？
5. 工具为什么不直接读写 State？
6. 权限边界的三层防护是什么？

## 11. 面试高频考点

- 工具是什么：自带"说明书（name/description/schema）+ 校验器"的外部能力接口。
- `@tool` 机制：函数签名 → pydantic 校验器 → `args_schema`；docstring 即 description。
- `bind_tools` vs `ToolNode`：给模型看 schema vs 进图执行——"工具怎么进模型"和"工具怎么进图"是两件事；**模型只生成 `tool_calls` 声明，真正执行工具函数的是 `ToolNode`**。
- 工具是无状态函数，不直接碰 State；写状态是节点的职责。
- 白名单 + 参数校验 + 敏感操作人工确认（第 7 课）的三层防护。
