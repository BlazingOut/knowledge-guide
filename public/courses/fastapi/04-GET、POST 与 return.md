# 第4课:GET、POST 与 return

## 1. 地址不决定请求方法

同一个地址可以定义不同方法：

```python
@app.get("/notes")
def list_notes():
    return {"action": "读取笔记"}

@app.post("/notes")
def create_note():
    return {"action": "创建笔记"}
```

真正区分它们的是 HTTP 请求中的 method：

```text
GET  /notes
POST /notes
```

## 2. 浏览器地址栏通常发送 GET

直接访问：

```text
http://127.0.0.1:8002/notes
```

浏览器地址栏会发出 `GET` 请求。因此它只能调用 `@app.get` 路由，不能通过地址栏直接调用需要 JSON 请求体的 `@app.post` 路由。

POST 可以通过 FastAPI `/docs` 的 `Try it out`、前端 `fetch`、表单或其他 API 工具发送。

## 3. return 的区别

GET 和 POST 都可以返回字符串、字典、列表或 Pydantic 模型。FastAPI 会把返回值转换为 HTTP 响应，通常是 JSON。

区别主要不在 Python 的 `return` 写法，而在接口语义：GET 通常返回被读取的数据，POST 通常返回新创建的数据或操作结果。

创建资源时也常用 `201 Created`：

```python
from fastapi import status

@app.post("/notes", status_code=status.HTTP_201_CREATED)
def create_note():
    return {"id": 1, "content": "买咖啡"}
```

## 错误处理与 HTTP 状态码

## 1. 为什么需要错误处理

用户请求不一定总是正确，例如：

- 请求的生活事项不存在
- 提交的数据不符合业务规则
- 请求体缺少字段或类型错误

后端应该返回清晰的状态码和错误信息，而不是让程序直接崩溃。

## 2. 使用 HTTPException

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="生活事项不存在")
```

`raise` 会中断当前函数。FastAPI 会捕获这个异常，并返回类似的 JSON：

```json
{
  "detail": "生活事项不存在"
}
```

## 3. 三类常见错误

### 404：资源不存在

例如请求 `/life-items/99`，但 ID 为 99 的事项不存在。

### 400：请求违反业务规则

请求格式可能是正确的，但内容不符合业务要求，例如名称不能是空字符串。

### 422：请求数据无法通过自动校验

例如路径参数要求整数，却请求 `/life-items/abc`，或者请求体缺少必填字段。这个错误通常由 FastAPI 和 Pydantic 自动返回。

## 4. `status` 常量

下面两种写法效果相同：

```python
raise HTTPException(status_code=404, detail="不存在")
```

```python
from fastapi import status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="不存在",
)
```

数字写法更短，`status.HTTP_404_NOT_FOUND` 可读性更好。

## 5. 当前练习

练习文件：`code/fastapi/04-errors.py`

启动：

```bash
cd fastapi
python code/fastapi/04-errors.py
```

打开 `http://127.0.0.1:8003/docs`，尝试：

1. 请求 `GET /life-items/1`，观察成功响应。
2. 请求 `GET /life-items/99`，观察 `404`。
3. 请求 `GET /life-items/abc`，观察 `422`。
4. 请求 `POST /life-items/1/rename`，分别提交正常名称和空名称。
5. 删除请求体中的 `name`，观察自动校验错误。
