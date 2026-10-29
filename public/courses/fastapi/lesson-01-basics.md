# 第1课：FastAPI 从零入门

这是 Life Manager 项目的配套学习笔记。课程会从网络和 Web 基础开始，再逐步进入 FastAPI、数据库和 Agent 接口。

## 学习方式

每一课包含：

1. 要理解的概念
2. 当前项目中的对应代码
3. 可以运行的最小示例
4. 动手练习

学习时优先运行示例、修改代码、观察结果，再回头阅读解释。

代码中的 `TODO 作业` 注释标出了需要自己完成的小任务。作业只使用当前课程已经介绍过的知识。


## 0. 先看懂 Python 基础语法

练习文件不是一段神秘配置，而是一个普通的 Python 文件。可以按下面顺序阅读：

```python
from fastapi import FastAPI
```

`from ... import ...` 是导入语法。它从 `fastapi` 这个已安装的 Python 包中取出 `FastAPI` 类，之后才能使用它。

```python
app = FastAPI(title="FastAPI 学习练习")
```

`app` 是变量名，`=` 表示把右边创建出来的对象保存到左边。`FastAPI(...)` 是调用一个类，创建 FastAPI 应用对象。`title=...` 是传给它的一个命名参数。

```python
def health_check():
    return {"status": "ok"}
```

- `def` 用来定义函数。
- `health_check` 是函数名。
- `()` 表示这个函数暂时不接收参数。
- 冒号 `:` 表示函数内容从下一行开始。
- 缩进的代码属于这个函数。
- `return` 把结果交还给调用者。
- `{ "status": "ok" }` 是 Python 字典，由键和值组成。

函数定义只是“写好了以后要做什么”，定义时不会自动执行。FastAPI 路由注册后，收到匹配的请求时才会调用它。

```python
name: str = "朋友"
```

这是一个带类型标注和默认值的参数：`name` 是参数名，`str` 表示字符串，`"朋友"` 表示调用时没有提供 name 就使用这个默认值。

```python
if name == "myy":
    message = "你好，朋友"
else:
    message = f"你好，{name}"
```

`if` 根据条件决定执行哪一段。`==` 是比较两个值是否相等；`=` 是赋值，二者不要混淆。`f"...{name}"` 是格式化字符串，会把变量值放进文字中。

## 0.1 装饰器到底做什么

```python
@app.get("/health")
def health_check():
    return {"status": "ok"}
```

`@` 开头的这一行是 Python 装饰器。可以先把它理解成“给紧接着定义的函数登记一项额外用途”。

FastAPI 的 `app.get("/health")` 登记的用途是：

```text
收到 GET /health
  -> 调用 health_check()
  -> 把 return 的字典变成 JSON 响应
```

所以 `health_check` 这个名字不是 URL 的一部分；URL 由装饰器中的 `"/health"` 决定。

## 1. 客户端和服务器

- React 前端是客户端，负责展示页面并发起请求。
- FastAPI 后端是服务器，负责接收请求、执行 Python 代码并返回结果。
- Uvicorn 负责让 FastAPI 应用真正运行在网络上。

一次请求的基本过程：

```text
React 前端
  -> 发出 HTTP 请求
Uvicorn
  -> 把请求交给 FastAPI
FastAPI
  -> 根据方法和路径找到路由
Python 函数
  -> 执行业务逻辑
FastAPI
  -> 返回状态码和 JSON
React 前端
  -> 显示结果
```

## 2. URL 的组成

示例：

```text
http://localhost:8000/api/sessions/abc123/messages
```

- `http`：通信协议
- `localhost`：当前电脑
- `8000`：端口
- `/api`：API 的统一前缀
- `/sessions`：资源类型
- `abc123`：某个具体会话
- `/messages`：会话下的消息资源

## 3. 什么是路由

路由是“请求如何分发到 Python 函数”的规则。

```python
@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

含义：收到 `GET /api/health` 时，执行 `health_check()`。

`@app.get(...)` 是 Python 装饰器语法，也是 FastAPI 注册路由的方式。

函数名只是 Python 内部名称，不决定 URL：

```python
@app.get("/api/sessions")
def list_all_conversations():
    return []
```

这个接口仍然是 `GET /api/sessions`。

## 4. GET 和 POST

- `GET`：读取数据，例如 `GET /api/sessions`
- `POST`：提交数据或创建资源，例如 `POST /api/sessions`

可以先记忆为：`GET` 是拿东西，`POST` 是交东西或创建东西。

## 5. 路径参数

```python
@app.get("/api/sessions/{session_id}/messages")
def session_messages(session_id: str):
    ...
```

访问 `/api/sessions/sess_123/messages` 时，FastAPI 会把 `sess_123` 传给 `session_id`。

## 6. 请求体和 Pydantic

前端可以发送 JSON：

```json
{
  "text": "帮我记录买咖啡",
  "model": "gpt-5.5"
}
```

后端用 Pydantic 定义结构：

```python
from pydantic import BaseModel

class RequestInput(BaseModel):
    text: str
    model: str | None = None
```

FastAPI 会自动解析 JSON、校验类型，并生成 `RequestInput` 对象。

## 7. 响应和状态码

后端返回的 Python 字典会自动变成 JSON。

常见状态码：

- `200`：成功
- `201`：创建成功
- `404`：找不到资源
- `422`：请求数据格式不符合要求
- `500`：服务器内部错误

## 8. Uvicorn

启动命令：

```bash
cd fastapi
python -m uvicorn lesson01_basic_api:app --reload
```

- `python`：使用 Python 解释器
- `-m uvicorn`：把已安装的 Uvicorn 模块作为程序运行
- `lesson01_basic_api:app`：加载当前 `code/fastapi/lesson01_basic_api.py` 中的 `app`
- `--reload`：代码修改后自动重启，适合开发和学习

Uvicorn 是 ASGI 服务器。当前只需要理解：FastAPI 定义请求如何处理，Uvicorn 负责让 FastAPI 在网络上运行。

## 当前练习

练习文件：`code/fastapi/lesson01_basic_api.py`

启动后访问：

```text
http://127.0.0.1:8000/hello
http://127.0.0.1:8000/hello?name=小明
http://127.0.0.1:8000/docs
```

动手修改 `/hello` 接口的返回内容，刷新浏览器观察变化。

课后作业：

1. 增加一个 `/goodbye` 接口。
2. 让 `/goodbye?name=小明` 返回包含名字的告别语句。
3. 为接口增加一个整数查询参数，并观察传入文字时的 `422` 错误。

完成后可以把修改后的代码或遇到的错误发给我，我会按照“提示优先”的方式帮助你检查。
