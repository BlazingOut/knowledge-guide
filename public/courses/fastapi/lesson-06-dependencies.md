# 第六课：依赖注入 `Depends` 与资源生命周期

## 本课范围

第五课中，每个路由都自己打开 SQLite 连接。本课只围绕一个问题展开：

> 如何让 FastAPI 在调用路由前准备好依赖，并在请求结束后释放资源？

本课使用一个最小的 `items` API，重点观察：

```text
请求
  -> FastAPI 调用依赖
  -> 路由使用依赖结果
  -> 请求结束
  -> 清理 yield 依赖提供的资源
```

本课暂不展开完整认证系统、Store 分层、异步数据库、ORM 和测试。认证、路由拆分和 TestClient 会在后续课程中分别学习。

## 学习目标

完成本课后，你应当能够：

- 解释 `Depends` 的作用和执行过程；
- 用依赖复用查询参数；
- 使用 `yield` 依赖管理数据库连接；
- 区分连接关闭和事务提交；
- 说明同一请求内的依赖复用与跨请求资源隔离；
- 判断哪些公共逻辑适合提取为依赖。

## 1. 什么是依赖注入

普通函数由调用者准备参数：

```python
def list_items(limit: int):
    ...


list_items(10)
```

FastAPI 中，路由可以声明自己需要什么：

```python
@app.get("/items")
def list_items(
    limit: Annotated[int, Depends(get_limit)],
):
    ...
```

`Depends(get_limit)` 不是在模块加载时直接调用 `get_limit()`。请求到达后，FastAPI 会：

1. 找到 `get_limit`；
2. 解析它的参数；
3. 调用它；
4. 把返回值传给 `list_items`；
5. 再执行路由函数。

教学用签名：

```python
Depends(dependency: Callable[..., Any] | None = None)
```

`dependency` 是依赖函数，通常是普通函数或异步函数。`Depends` 返回的是由 FastAPI 解析的依赖声明，不是依赖函数的结果。

## 2. 用依赖复用查询参数

示例代码中使用一个最小的分页参数依赖：

```python
def get_limit(
    limit: int = Query(default=10, ge=1, le=100),
) -> int:
    return limit
```

路由只声明需要一个经过校验的 `limit`：

```python
@app.get("/items")
def list_items(
    limit: Annotated[int, Depends(get_limit)],
):
    ...
```

`Query` 中本课使用的参数：

- `default`：查询参数缺失时的默认值；
- `ge`：数值必须大于或等于指定值；
- `le`：数值必须小于或等于指定值。

访问：

```text
GET /items?limit=20
```

FastAPI 会先读取并校验 `limit`，再调用 `get_limit`，最后把结果传给路由。

依赖的价值不在于少写几行代码，而在于把“参数读取和校验”从路由业务中分离出来。后续多个接口需要相同规则时，可以复用同一个依赖。

## 3. 使用 `yield` 管理数据库连接

第五课中，路由可以自己管理连接：

```python
@app.get("/items")
def list_items():
    connection = sqlite3.connect(DATABASE)
    try:
        ...
    finally:
        connection.close()
```

当多个路由都需要数据库时，可以把资源管理提取成依赖：

```python
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
```

路由声明需要连接：

```python
@app.get("/items")
def list_items(
    limit: Annotated[int, Depends(get_limit)],
    connection: Annotated[
        sqlite3.Connection,
        Depends(get_connection),
    ],
):
    rows = connection.execute(
        "SELECT id, content FROM items ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]
```

### `yield` 依赖的执行过程

```text
请求开始
  -> 创建 SQLite 连接
  -> yield 连接给路由
  -> 路由执行查询
  -> 路由返回或抛出异常
  -> 执行 finally
  -> 关闭连接
```

`yield` 前的代码负责准备资源，`yield` 提供资源，`finally` 负责清理资源。

需要区分：

- `connection.close()`：关闭连接；
- `connection.commit()`：提交当前事务；
- `connection.rollback()`：回滚当前事务；
- `finally`：无论路由成功还是失败，都执行清理。

写操作必须在返回成功响应前明确提交：

```python
cursor = connection.execute(
    "INSERT INTO items (content) VALUES (?)",
    (item.content,),
)
connection.commit()
return {"id": cursor.lastrowid, "content": item.content}
```

不要把关闭连接当成提交事务。第五课中的 `with sqlite3.connect(...)` 主要管理事务提交和回滚，不能把它当成自动关闭连接的依据。

## 4. 依赖的作用范围

同一个请求中，FastAPI 默认会缓存同一个依赖的结果。这个机制用于避免同一请求中重复准备相同资源。

它不表示连接会跨请求共享：

```text
请求 A -> 连接 A -> 请求结束后关闭
请求 B -> 连接 B -> 请求结束后关闭
```

不要把 SQLite 连接放在全局变量中供所有请求使用。全局连接会混淆资源生命周期，并可能带来线程归属、并发访问和异常恢复问题。

## 5. 课程示例代码

示例文件：

```text
code/fastapi/lesson06_dependencies.py
```

示例只保留两个依赖：

| 依赖 | 作用 |
| --- | --- |
| `get_limit` | 读取并校验一个公共查询参数 |
| `get_connection` | 创建并清理当前请求的 SQLite 连接 |

示例接口：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/items` | 使用依赖连接查询事项 |
| `POST` | `/items` | 使用依赖连接创建事项 |

这里没有加入认证、Store 和复杂分页模型，因为它们不是本课的核心。完整的依赖组合和模块拆分会在后续课程中出现。

## 6. 运行课程代码

安装依赖：

```bash
pip install fastapi uvicorn
```

启动服务：

```bash
cd code/fastapi
python -m uvicorn lesson06_dependencies:app --reload --port 8005
```

打开：

```text
http://127.0.0.1:8005/docs
```

按以下顺序观察：

1. 使用 `GET /items` 查询事项；
2. 修改 `limit`，观察查询参数如何通过依赖传入；
3. 使用 `POST /items` 创建事项；
4. 再使用 `GET /items` 查询新记录；
5. 在 `get_connection` 的 `finally` 中临时加入打印，观察请求结束后的清理时机。

## 7. 课后作业

### 作业一：增加查询偏移量

新增一个 `get_offset` 依赖，从查询参数读取 `offset`：

- 默认值为 `0`；
- 不能小于 `0`；
- `GET /items` 同时使用 `limit` 和 `offset`；
- 使用 SQL 的 `LIMIT ? OFFSET ?`。

### 作业二：观察异常路径的清理

在 `GET /items` 中临时抛出一个异常，并在 `get_connection` 的 `finally` 中打印日志。确认路由异常后仍然会执行清理逻辑。

### 作业三：增加请求头依赖

新增一个简单的请求头依赖，用于读取 `X-Study-User`。本作业只要求观察依赖注入，不要求实现完整认证和授权。

## 8. 验收问题

1. `Depends(get_connection)` 和直接调用 `get_connection()` 有什么区别？
2. FastAPI 在调用路由函数前会做哪些依赖处理？
3. 为什么数据库连接适合使用 `yield` 依赖？
4. `yield` 前、`yield` 后和 `finally` 分别适合做什么？
5. 为什么写操作必须明确 `commit()`？
6. `close()` 和 `commit()` 的职责有什么区别？
7. 同一个依赖会不会跨请求共享结果？
8. 路由抛出异常时，`yield` 依赖的 `finally` 是否还会执行？
9. 为什么不应该把 SQLite 连接作为全局变量？
10. 哪些公共逻辑适合提取成 FastAPI 依赖？

## 9. 面试高频考点

### 9.1 `Depends` 解决了什么问题？

`Depends` 让路由声明自己需要的公共能力，FastAPI 根据依赖关系解析参数、调用依赖并把结果传入路由。它可以复用参数校验、数据库连接、认证信息和配置读取等逻辑。

本课只用参数和数据库连接作为示例，认证依赖会在后续课程中展开。

### 9.2 `yield` 依赖如何管理资源？

需要说清楚执行顺序：

```text
进入请求
  -> 执行 yield 前代码
  -> 提供资源
  -> 执行路由
  -> 执行清理代码
```

数据库连接应该在准备阶段创建，在 `finally` 中关闭。事务提交应该在写操作成功后明确执行。

### 9.3 为什么不直接使用全局数据库连接？

全局连接会让资源生命周期和请求生命周期脱钩，也可能带来线程归属、并发访问和异常恢复问题。按请求获取并释放连接更容易解释和管理；连接池则应该由专门的连接池组件管理。

### 9.4 依赖注入和消息队列有什么区别？

依赖注入解决的是当前请求中的对象和公共逻辑如何准备；消息队列解决的是任务如何在请求之外投递、持久化、确认和重试。两者属于不同层次，不能互相替代。
