# 第九课：异步接口与模型调用

## 本课范围

前一阶段已经学习了 Python 协程、`asyncio`、`await` 和阻塞 I/O。本课把这些能力放进 FastAPI，完成一个最小的聊天接口：

```text
HTTP 请求
  -> FastAPI 异步路由
  -> 异步模型客户端
  -> 等待模型响应
  -> 返回结构化结果
```

本课使用本地模拟模型客户端，不需要真实 API Key，也不发起外部网络请求。

本课暂不展开：

- SSE 和流式响应；
- 真实模型 SDK 的完整参数；
- 对话历史、上下文窗口和 Token 计费；
- 重试、限流、熔断和消息队列；
- 异步数据库驱动。

流式响应放在下一课，生产化治理在后续阶段展开。

## 学习目标

完成本课后，你应当能够：

- 区分同步路由和异步路由；
- 在异步路由中使用 `await` 等待模型 I/O；
- 解释为什么 `async def` 不会自动消除阻塞；
- 为模型调用设置超时；
- 将上游超时和上游失败转换成合理的 HTTP 状态码；
- 说明为什么本地模拟客户端可以用于学习和测试，但不能代表真实模型服务。

## 1. 为什么模型调用适合异步

模型调用通常是网络 I/O：

```text
发送请求
  -> 等待模型排队和生成
  -> 接收响应
```

等待期间，当前请求没有 CPU 密集型工作可做。如果使用异步 HTTP 客户端，事件循环可以处理其他请求。

异步主要解决等待期间的任务切换，不保证模型服务本身更快，也不能解决模型服务排队、限流或计算资源不足。

## 2. 同步路由和异步路由

同步路由：

```python
@app.post("/chat")
def chat(payload: ChatInput):
    answer = client.complete(payload.message)
    return {"answer": answer}
```

异步路由：

```python
@app.post("/chat")
async def chat(payload: ChatInput):
    answer = await client.complete(payload.message)
    return {"answer": answer}
```

异步版本的关键不是把 `def` 改成 `async def`，而是被等待的模型客户端也提供异步操作：

```python
answer = await client.complete(payload.message)
```

如果 `client.complete()` 内部执行的是同步阻塞网络请求，即使外层函数是 `async def`，也仍然可能阻塞事件循环。

## 3. 模拟异步模型客户端

示例代码使用一个本地客户端：

```python
class FakeModelClient:
    async def complete(self, message: str, delay: float = 0.2) -> str:
        await asyncio.sleep(delay)
        return f"模型收到：{message}"
```

这是一个教学替身：

- `async def complete` 模拟异步 SDK 方法；
- `asyncio.sleep` 模拟等待模型响应；
- 不需要网络和密钥；
- 返回值固定，便于观察接口行为。

真实 SDK 的参数通常更多。本课只保留“输入消息、等待响应、返回文本”这条主线。

## 4. 使用异步路由调用模型

接口定义：

```python
@app.post("/chat", response_model=ChatOutput)
async def chat(
    payload: ChatInput,
    delay: Annotated[float, Query(ge=0, le=5)] = 0.2,
):
    ...
```

请求体：

```json
{
  "message": "你好"
}
```

查询参数 `delay` 只是为了观察超时行为，真实模型服务中不应让客户端任意控制服务端等待时间。

路由中的核心调用：

```python
answer = await model_client.complete(payload.message, delay)
```

执行过程：

```text
接收请求
  -> 校验 ChatInput
  -> 调用异步模型客户端
  -> await 等待模型结果
  -> 生成 ChatOutput
  -> 返回 JSON
```

## 5. 为模型调用设置超时

上游服务不能无限等待。示例使用：

```python
async with asyncio.timeout(2):
    answer = await model_client.complete(payload.message, delay)
```

含义是：最多等待 2 秒。如果模型客户端没有及时完成，当前操作会被取消并抛出 `TimeoutError`。

超时处理：

```python
except TimeoutError:
    raise HTTPException(
        status_code=504,
        detail="模型服务超时",
    )
```

`504 Gateway Timeout` 表示当前服务作为网关等待上游服务时超时。

超时不是无限重试的理由。重试策略要结合请求是否幂等、模型服务限流和整体请求预算，在生产化课程中展开。

## 6. 处理上游错误

模拟客户端在收到 `fail` 时抛出 `RuntimeError`：

```python
if message == "fail":
    raise RuntimeError("模拟的模型服务失败")
```

接口层将其转换为：

```python
except RuntimeError:
    raise HTTPException(
        status_code=502,
        detail="模型服务暂时不可用",
    )
```

`502 Bad Gateway` 表示当前服务从上游获得了无效响应或上游调用失败。

真实项目中不应把所有异常都简单转换成 `502`。需要根据上游 SDK 的错误信息区分超时、认证失败、限流、参数错误和服务端故障。

## 7. 课程示例代码

示例文件：

```text
code/fastapi/lesson09_async.py
```

示例只有一个接口：

```text
POST /chat?delay=0.2
```

成功响应：

```json
{
  "answer": "模型收到：你好"
}
```

特殊输入：

- `message = "fail"`：返回 `502`；
- `delay > 2`：返回 `504`；
- `delay < 0` 或 `delay > 5`：返回参数校验错误。

## 8. 运行课程代码

安装依赖：

```bash
pip install fastapi uvicorn
```

启动服务：

```bash
cd code/fastapi
python -m uvicorn lesson09_async:app --reload --port 8008
```

打开：

```text
http://127.0.0.1:8008/docs
```

也可以使用请求：

```bash
curl -X POST "http://127.0.0.1:8008/chat?delay=0.2" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"你好\"}"
```

观察超时：

```bash
curl -X POST "http://127.0.0.1:8008/chat?delay=3" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"等待测试\"}"
```

观察上游错误：

```bash
curl -X POST "http://127.0.0.1:8008/chat" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"fail\"}"
```

## 9. 课后作业

### 作业一：增加响应耗时

在响应中增加一个固定格式的 `model` 字段，例如：

```json
{
  "answer": "模型收到：你好",
  "model": "fake-model"
}
```

要求同时修改 Pydantic 响应模型和返回值。

### 作业二：增加消息长度限制

在 `ChatInput` 中限制 `message` 不能为空，并限制最大长度。使用 `/docs` 发送非法请求，观察 `422`。

### 作业三：观察阻塞调用

把 `await asyncio.sleep(delay)` 临时改成 `time.sleep(delay)`，再恢复原代码。说明为什么函数仍然是 `async def`，但事件循环会被阻塞。

## 10. 验收问题

1. 为什么模型调用适合放在异步路由中？
2. `async def` 和 `await` 分别表示什么？
3. 为什么把同步函数改成 `async def` 不一定就变成非阻塞？
4. `asyncio.timeout()` 解决什么问题？
5. 为什么上游超时通常返回 `504`？
6. 为什么上游调用失败可以映射为 `502`？
7. 为什么示例使用模拟模型客户端？
8. 客户端可控的 `delay` 参数为什么不适合直接出现在真实接口中？
9. 超时后是否应该无条件重试？
10. 本课为什么不实现流式响应？

## 11. 面试高频考点

### 11.1 FastAPI 中什么时候使用 `async def`？

当路由内部包含异步 I/O，并且调用的客户端提供异步接口时，可以使用 `async def`。如果内部调用长时间运行的同步阻塞函数，单纯把路由改成异步函数不能解决阻塞问题。

### 11.2 异步调用模型时为什么必须设置超时？

模型服务可能排队、限流、网络异常或长时间无响应。没有超时，请求会长期占用连接和任务资源，最终影响服务吞吐。超时还应该和取消、重试、日志及监控一起设计。

### 11.3 为什么要在 API 层转换上游异常？

上游 SDK 的异常类型不应该直接暴露给 API 调用方。API 层需要把内部异常转换为稳定的 HTTP 状态码和错误结构，同时记录足够的服务端日志。

### 11.4 异步是否等于并行？

不是。异步通常是在一个事件循环中利用 I/O 等待时间交替运行多个任务；并行是多个执行资源同时运行。异步不能自动加速 CPU 密集型计算。
