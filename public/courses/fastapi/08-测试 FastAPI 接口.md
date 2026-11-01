# 第8课:测试 FastAPI 接口

## 本课范围

前几课通过 `/docs` 手动验证接口。本课开始使用自动化测试，验证接口的外部行为：

```text
测试客户端
  -> HTTP 请求
  -> FastAPI 路由
  -> 依赖
  -> SQLite
  -> HTTP 响应
```

本课不展开：

- 完整测试理论和测试驱动开发；
- 大规模 mock 体系；
- 认证系统测试；
- 异步测试框架的完整用法；
- CI/CD 配置。

重点是理解 `TestClient`、依赖覆盖、临时数据库和 API 到 SQLite 的集成测试。

## 学习目标

完成本课后，你应当能够：

- 使用 `TestClient` 发起测试请求；
- 断言状态码、响应 JSON 和错误结果；
- 使用 pytest fixture 准备测试客户端；
- 通过 `app.dependency_overrides` 替换数据库依赖；
- 为测试使用独立 SQLite 数据库；
- 区分接口测试、单元测试和手工访问 `/docs`。

## 1. 为什么需要接口测试

手工测试适合快速观察，但每次修改后都要重复点击，容易遗漏边界情况。接口测试把请求和预期结果写成代码：

```python
response = client.post(
    "/items",
    json={"content": "学习接口测试"},
)

assert response.status_code == 201
```

之后可以反复运行同一组检查。

本课测试接口的外部行为，不直接测试路由函数内部的局部变量。这样测试更接近调用方实际看到的结果。

## 2. `TestClient`

```python
from fastapi.testclient import TestClient


client = TestClient(app)
response = client.get("/items")
```

`TestClient` 是 FastAPI 提供的测试客户端，底层使用 Starlette 的测试能力。它让测试代码可以用类似 HTTP 客户端的方式访问应用，但请求在测试进程内完成，不需要启动 Uvicorn。

本课用到的操作：

```python
client.get(path, params=None)
client.post(path, json=None)
```

- `path`：接口路径；
- `params`：查询参数字典；
- `json`：要序列化为 JSON 请求体的 Python 对象；
- 返回值：响应对象；
- 常用属性：`status_code`、`json()`、`text`。

示例：

```python
response = client.get("/items", params={"limit": 10})
assert response.status_code == 200
assert isinstance(response.json(), list)
```

## 3. 测试不同结果

### 3.1 成功响应

```python
response = client.post(
    "/items",
    json={"content": "学习接口测试"},
)

assert response.status_code == 201
assert response.json()["content"] == "学习接口测试"
```

### 3.2 自动校验错误

`limit` 要求至少为 1：

```python
response = client.get("/items?limit=0")

assert response.status_code == 422
```

这里测试的是请求参数进入路由前的 FastAPI/Pydantic 校验。

### 3.3 资源不存在

```python
response = client.get("/items/999")

assert response.status_code == 404
assert response.json()["detail"] == "事项不存在"
```

测试不只是验证“返回了错误”，还应该确认错误状态码和响应结构符合接口约定。

## 4. 使用 fixture 准备客户端

测试中经常需要重复创建客户端和准备资源。pytest 的 fixture 可以集中管理：

```python
@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
```

测试函数声明需要它：

```python
def test_list_items(client: TestClient) -> None:
    response = client.get("/items")
    assert response.status_code == 200
```

fixture 中 `yield` 前的代码负责准备，`yield` 后的代码负责清理。

## 5. 使用依赖覆盖替换测试数据库

如果测试直接使用课程代码中的 `study.sqlite3`，测试会污染学习数据，而且测试之间可能互相影响。FastAPI 支持用 `app.dependency_overrides` 替换依赖：

```python
def override_get_connection():
    yield from create_test_connection(test_database)


app.dependency_overrides[get_connection] = override_get_connection
```

替换关系是：

```text
正常运行：get_connection -> study.sqlite3
测试运行：override_get_connection -> 临时 test.sqlite3
```

测试结束后要清除覆盖：

```python
app.dependency_overrides.clear()
```

否则后续测试可能继续使用测试依赖，导致测试之间产生隐藏状态。

## 6. 临时 SQLite 数据库

pytest 的 `tmp_path` fixture 会提供一个临时目录：

```python
def client(tmp_path: Path):
    test_database = tmp_path / "test.sqlite3"
```

测试数据库具有几个优点：

- 不修改课程示例数据库；
- 每个测试运行可以获得新的文件；
- 测试结束后临时目录可以被清理；
- 可以验证真实 SQL、事务和接口之间的连接。

这类测试不是只测一个 Python 函数，而是从 HTTP 请求走到 SQLite，因此可以称为接口集成测试。

## 7. 课程示例代码

示例文件：

```text
code/fastapi/08-testing.py
```

示例包含：

- `GET /items`；
- `POST /items`；
- `GET /items/{item_id}`；
- 正常创建和查询测试；
- `422` 参数校验测试；
- `404` 资源不存在测试；
- 临时 SQLite 数据库；
- `dependency_overrides` 数据库依赖覆盖。

## 8. 安装和运行测试

安装依赖：

```bash
pip install fastapi uvicorn pytest httpx
```

在仓库根目录执行：

```bash
pytest code/fastapi/08-testing.py -q
```

如果只想手工访问示例服务：

```bash
cd code/fastapi
python code/fastapi/08-testing.py
```

然后打开：

```text
http://127.0.0.1:8007/docs
```

## 9. 课后作业

### 作业一：测试分页结果

先创建两条事项，再使用 `GET /items?limit=1`：

- 断言状态码为 `200`；
- 断言返回列表长度为 `1`；
- 说明分页参数是在路由前由 FastAPI 校验的。

### 作业二：测试请求体校验

发送以下请求：

```json
{}
```

断言返回 `422`，并观察错误响应中的字段位置。

### 作业三：测试数据库隔离

在一个测试中创建事项，在另一个测试中查询相同 ID，确认两个测试不会共享数据。

## 10. 验收问题

1. `TestClient` 是否需要先启动 Uvicorn？
2. 为什么接口测试应该断言状态码和响应结构？
3. `app.dependency_overrides` 解决了什么问题？
4. 为什么测试不应该直接使用课程运行时的 SQLite 文件？
5. fixture 中的 `yield` 前后分别适合做什么？
6. 为什么测试结束后要清除依赖覆盖？
7. `422` 和 `404` 分别说明了什么？
8. 当前测试为什么属于接口集成测试？
9. 如何测试一个需要认证依赖的接口？
10. 如果测试之间互相影响，应该优先检查哪些共享状态？

## 11. 面试高频考点

### 11.1 为什么要覆盖依赖？

依赖覆盖可以在不修改路由代码的情况下替换数据库、认证或外部服务。测试可以使用隔离的临时资源，生产代码仍然使用真实依赖。

### 11.2 单元测试和接口测试有什么区别？

单元测试通常验证一个函数或一个类的局部行为，可以隔离外部依赖。接口测试从 HTTP 请求开始，验证路由、参数校验、依赖、业务和存储之间的协作。

### 11.3 为什么测试要使用独立数据库？

真实数据库可以验证 SQL 和事务，但如果直接使用开发数据库，测试会污染数据，也会依赖运行顺序。临时数据库同时保留真实 SQLite 行为和测试隔离。

### 11.4 为什么不能只测试 `200`？

API 的错误行为也是接口契约的一部分。参数错误、资源不存在和业务失败如果没有测试，重构时很容易意外改变状态码或错误结构。
