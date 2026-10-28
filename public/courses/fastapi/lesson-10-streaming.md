# 第十课：流式响应与聊天接口

## 本课范围

第九课的接口要等模型调用完成后，才一次性返回完整 JSON。本课改为逐段返回结果：

```text
客户端发起请求
  -> 服务端产生第一段内容
  -> 立即发送
  -> 服务端继续产生内容
  -> 发送下一段
  -> 发送结束事件
```

本课使用本地模拟模型，不需要真实 API Key。

本课暂不展开：

- 真实模型 SDK 的流式参数；
- WebSocket；
- 前端流式渲染；
- 对话历史和上下文管理；
- 断点续传和消息持久化；
- 生产环境代理、负载均衡和连接数治理。

## 学习目标

完成本课后，你应当能够：

- 解释普通 JSON 响应和流式响应的区别；
- 使用异步生成器逐段产生内容；
- 使用 `StreamingResponse` 返回流；
- 读懂基本 SSE 数据格式；
- 发送结束事件；
- 处理客户端断开和协程取消；
- 说明流式响应为什么不能简单套用普通 JSON 测试方式。

## 1. 普通响应和流式响应

普通接口通常是：

```text
请求
  -> 等待完整结果
  -> 一次返回 JSON
```

例如：

```json
{
  "answer": "完整的模型回答"
}
```

流式接口则是：

```text
请求
  -> 返回第一段
  -> 返回第二段
  -> 返回第三段
  -> 返回结束标记
```

流式响应的价值是降低用户感知到的首字节等待时间。它不会让模型生成总耗时一定变短，只是让已经生成的内容更早到达客户端。

## 2. 异步生成器

普通生成器使用 `yield` 逐个产生值：

```python
def numbers():
    yield 1
    yield 2
```

异步生成器使用 `async def` 和 `yield`：

```python
async def fake_model_stream(message: str):
    await asyncio.sleep(0.2)
    yield f"收到：{message}"
```

异步生成器可以在每次产生内容前等待异步 I/O。调用方使用 `async for` 消费：

```python
async for part in fake_model_stream("你好"):
    print(part)
```

本课用异步生成器模拟模型逐步生成文本。

## 3. SSE 数据格式

示例使用 Server-Sent Events 的基本文本格式：

```text
data: 第一段

data: 第二段

event: done
data: [DONE]

```

每个事件使用空行分隔。常用字段：

- `data:`：事件携带的数据；
- `event:`：事件名称；
- 空行：表示一个事件结束。

本课只使用文本片段，不处理复杂 JSON。真实应用通常会把片段、消息 ID、错误和结束状态编码成 JSON。

## 4. `StreamingResponse`

示例路由：

```python
@app.post("/chat/stream")
async def chat_stream(payload: ChatInput):
    return StreamingResponse(
        event_stream(payload.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
```

教学用签名：

```python
StreamingResponse(
    content: AsyncIterable[str],
    media_type: str | None = None,
    headers: Mapping[str, str] | None = None,
)
```

- `content`：同步或异步的字符串迭代器；
- `media_type`：响应内容类型；
- `headers`：额外响应头；
- 返回值：一个流式 HTTP 响应对象。

`text/event-stream` 告诉客户端这是 SSE 风格的事件流。`Cache-Control: no-cache` 用于避免中间缓存延迟或合并事件。

## 5. 结束事件和资源清理

示例在正常结束时发送：

```text
event: done
data: [DONE]

```

客户端不能只依赖连接关闭来判断业务是否完成。明确的结束事件可以让客户端区分：

- 正常完成；
- 中途错误；
- 网络断开；
- 服务端取消。

客户端主动断开时，服务端的异步生成器可能收到 `asyncio.CancelledError`。如果生成器持有模型连接、文件或临时资源，应在 `finally` 中清理：

```python
async def stream():
    resource = await acquire()
    try:
        async for part in generate(resource):
            yield part
    finally:
        await release(resource)
```

本课示例没有需要关闭的外部资源，但保留取消处理，让学生看到断连是流式接口必须考虑的生命周期事件。

## 6. 课程示例代码

示例文件：

```text
code/fastapi/lesson10_streaming.py
```

接口：

```text
POST /chat/stream
```

请求体：

```json
{
  "message": "你好"
}
```

响应会分成多个事件：

```text
data: 你说的是：你好

data: 。这是

data: 一条流式

data: 响应。

event: done
data: [DONE]

```

## 7. 运行课程代码

安装依赖：

```bash
pip install fastapi uvicorn
```

启动服务：

```bash
cd code/fastapi
python -m uvicorn lesson10_streaming:app --reload --port 8009
```

使用 `/docs` 可以发送请求，但 Swagger 页面不一定直观展示逐段到达的过程。也可以使用支持流式读取的客户端：

```bash
curl -N -X POST "http://127.0.0.1:8009/chat/stream" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"你好\"}"
```

`-N` 用于关闭 curl 的输出缓冲，便于观察事件逐段打印。

## 8. 课后作业

### 作业一：增加错误事件

当输入内容为空或等于 `fail` 时，发送：

```text
event: error
data: {"message":"生成失败"}

```

要求错误事件后不要再发送正常的 `done` 事件。

### 作业二：改为 JSON 数据

把每个 `data:` 内容改成 JSON 字符串：

```json
{
  "delta": "一段文本",
  "index": 0
}
```

要求客户端仍然能够区分片段顺序和结束事件。

### 作业三：观察客户端断开

使用命令行客户端发起请求后提前终止连接，思考服务端为什么需要处理取消，以及真实模型调用中哪些资源需要清理。

## 9. 验收问题

1. 普通 JSON 响应和流式响应的主要区别是什么？
2. 为什么流式响应可以改善用户感知的等待时间？
3. 异步生成器和普通生成器有什么区别？
4. `StreamingResponse` 的 `content` 参数需要什么类型的对象？
5. `text/event-stream` 表示什么？
6. SSE 事件为什么使用空行分隔？
7. 为什么要发送明确的结束事件？
8. 客户端断开时服务端可能收到什么取消信号？
9. 流式响应中哪些资源需要在 `finally` 中清理？
10. 为什么普通的 `response.json()` 不适合直接验证流式响应？

## 10. 面试高频考点

### 10.1 流式响应解决什么问题？

流式响应让服务端已经生成的内容尽早发送给客户端，降低首段内容的等待时间。它不等于降低模型总生成耗时，也不等于提高模型计算速度。

### 10.2 SSE 和 WebSocket 有什么区别？

SSE 通常是服务端向客户端单向推送，基于 HTTP 文本事件流；WebSocket 建立双向长连接，客户端和服务端都可以主动发送消息。本课的聊天输出只需要服务端持续返回内容，因此 SSE 更简单。

### 10.3 为什么流式接口要处理取消？

用户关闭页面、切换会话或网络中断时，服务端可能不再需要继续生成。如果不处理取消，模型请求、连接和计算资源可能继续占用。实际项目需要把取消信号传递到下游，并在 `finally` 中释放资源。

### 10.4 流式接口如何传递错误？

如果响应头已经发送，服务端通常不能再像普通接口一样修改 HTTP 状态码。因此流式协议需要定义错误事件和结束状态，让客户端在事件层面识别失败。
