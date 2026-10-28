# 第三课：Pydantic 校验和响应模型

## 1. 输入模型是接口契约

Pydantic 模型用 Python 类描述请求体应该长什么样：

```python
class LifeItemInput(BaseModel):
    content: str
    kind: str = "inbox"
```

它同时完成两件事：

- 把 JSON 变成属性清晰的 Python 对象
- 检查数据是否符合接口要求

## 2. 用 Field 增加限制

```python
class LifeItemInput(BaseModel):
    content: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=1, ge=1, le=5)
```

- `min_length`：字符串最短长度
- `max_length`：字符串最长长度
- `ge`：大于或等于
- `le`：小于或等于

如果请求不符合限制，FastAPI 会返回 `422`，并说明哪个字段出了问题。

## 3. Field 常用参数

`Field` 的参数是 Pydantic 预先定义的，不是任意自创的。常用参数可以按用途记忆：

| 用途 | 参数 | 示例 |
| --- | --- | --- |
| 字符串长度 | `min_length`, `max_length` | `Field(min_length=1, max_length=100)` |
| 数字范围 | `gt`, `ge`, `lt`, `le` | `Field(ge=1, le=5)` |
| 默认值 | `default` | `Field(default=1)` |
| 文档说明 | `description`, `title` | `Field(description="优先级")` |
| 示例值 | `examples` | `Field(examples=["买咖啡"])` |
| 正则限制 | `pattern` | `Field(pattern=r"^[A-Z]+$")` |

数字范围参数的含义：

- `gt`：大于
- `ge`：大于或等于
- `lt`：小于
- `le`：小于或等于

完整参数列表会随 Pydantic 版本变化，最可靠的查看方式是阅读当前环境中的帮助：

```python
from pydantic import Field
import inspect

print(inspect.signature(Field))
```

也可以查看官方文档中的 `Field` 参考。学习阶段不需要背完整列表，遇到具体需求时再查参数即可。

## 4. 输入模型和输出模型可以不同

输入数据和返回数据的用途不同，通常不应该共用一个模型：

```python
class LifeItemOutput(BaseModel):
    id: int
    content: str
    kind: str
    priority: int
```

创建时用户不需要提供 `id`，但返回时服务器可以生成并返回 `id`。

## 5. response_model

```python
@app.post("/life-items", response_model=LifeItemOutput)
def create_life_item(item: LifeItemInput):
    ...
```

`response_model` 告诉 FastAPI：这个接口的响应应该符合 `LifeItemOutput`。示例函数中故意返回了 `internal_note`，但它不会出现在最终响应里，因为输出模型没有这个字段。

## 6. 当前练习

练习文件：`code/fastapi/lesson03_pydantic_models.py`

启动：

```bash
cd fastapi
python -m uvicorn lesson03_pydantic_models:app --reload --port 8002
```

打开 `http://127.0.0.1:8002/docs`，调用 `POST /life-items`。

可以先使用：

```json
{
  "content": "买咖啡",
  "kind": "shopping",
  "priority": 3
}
```

再尝试：

1. 删除 `content`。
2. 把 `priority` 改成 `10`。
3. 把 `content` 改成空字符串。
4. 在请求中增加 `unknown_field`，观察它是否出现在响应中。
