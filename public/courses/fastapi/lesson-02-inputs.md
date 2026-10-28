# 第二课：查询参数、路径参数和请求体

一个接口接收的数据，常见有三种位置。

## 1. 查询参数

查询参数写在 URL 的 `?` 后面，多个参数使用`&` 并列：

```text
/search?keyword=coffee&limit=5
```

对应代码：

```python
@app.get("/search")
def search(keyword: str, limit: int = 10):
    ...
```

`keyword` 是必填参数，`limit` 有默认值 10。查询参数适合搜索条件、筛选条件、分页设置等。

## 2. 路径参数

路径参数是 URL 路径的一部分：

```text
/users/42
```

对应代码：

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    ...
```

路径参数通常表示“我要操作哪个具体资源”，例如用户 ID、会话 ID 或记录 ID。

## 3. 请求体

请求体通常用于 `POST`，内容以 JSON 发送：

```json
{
  "content": "买咖啡",
  "category": "购物"
}
```

对应代码：

```python
class NoteInput(BaseModel):
    content: str
    category: str = "未分类"

@app.post("/notes")
def create_note(note: NoteInput):
    ...
```

请求体适合创建或更新对象，因为它可以携带结构更复杂的数据。

## 4. 三者对比

| 类型 | 示例 | 常见用途 |
| --- | --- | --- |
| 查询参数 | `/search?keyword=coffee` | 搜索、筛选、分页 |
| 路径参数 | `/users/42` | 指定具体资源 |
| 请求体 | `{"content": "买咖啡"}` | 创建或更新数据 |

## 5. 当前练习

练习文件：`code/fastapi/lesson02_input_sources.py`

启动：

```bash
cd fastapi
python -m uvicorn lesson02_input_sources:app --reload --port 8001
```

浏览器可以直接访问：

```text
http://127.0.0.1:8001/search?keyword=coffee&limit=5
http://127.0.0.1:8001/users/42
```

`POST /notes` 需要发送 JSON，可以在 `http://127.0.0.1:8001/docs` 中点击接口，再点击 `Try it out`。

练习：

1. 给 `/search` 增加一个 `category` 查询参数。
2. 把 `/users/{user_id}` 的返回值增加一段用户说明。
3. 给 `NoteInput` 增加一个 `important: bool = False` 字段。

## 6. 参数类型和自动转换

URL 本身只能传输文字，所以查询参数和路径参数最初都是字符串：

```text
/users/42
```

其中 `42` 刚到服务器时可以理解为文本。FastAPI 会根据函数参数的类型标注进行转换和校验：

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    ...
```

这里 FastAPI 会尝试把 `"42"` 转成整数 `42`。如果访问 `/users/abc`，转换失败，FastAPI 会返回 `422`，不会把错误的值传给函数。

如果写成：

```python
@app.get("/users/{user_id}")
def get_user(user_id: str):
    ...
```

那么 `42` 会作为字符串 `"42"` 传入。

请求体中的 JSON 可以表达数字、布尔值和字符串等类型，但 Pydantic 仍会根据模型定义进行校验。
