# FastAPI 课程大纲

目标：从 HTTP 基础开始，逐步理解 Life Manager 的 FastAPI 后端接口。

前置知识：基本 Python 语法、函数、字典、类型标注；数据库部分暂时只在数据库课程完成后接入。

## 课程顺序

### 第 1 课：HTTP、URL、路由和 Uvicorn

目标：理解客户端、服务器、请求、响应、端口和路由；能够启动 FastAPI 应用。

状态：已完成，见 [lesson-01-basics.md](./lesson-01-basics.md)。

### 第 2 课：查询参数、路径参数和请求体

目标：区分三种输入位置，并能从 URL 或 JSON 读取数据。

状态：已完成，见 [lesson-02-inputs.md](./lesson-02-inputs.md)。

### 第 3 课：Pydantic 输入模型和响应模型

目标：理解数据校验、默认值、字段限制和 `response_model`。

状态：已完成，见 [lesson-03-models.md](./lesson-03-models.md)。

### 第 4 课：错误处理和状态码

目标：区分自动校验错误、资源不存在和业务规则错误。

状态：已完成，见 [lesson-04-errors.md](./lesson-04-errors.md)。

### 第 5 课：FastAPI 与 SQLite

前置条件：完成数据库课程第 1 至第 3 课。

目标：把接口、SQL 和数据库连接起来，理解当前项目的 Store 层。

状态：已编写，见 [lesson-05-sqlite.md](./lesson-05-sqlite.md)。

### 第 6 课：依赖注入 `Depends`

目标：理解共享数据库连接、认证信息和公共参数为什么适合使用依赖注入。

已编写：[lesson-06-dependencies.md](./lesson-06-dependencies.md)。

### 第 7 课：路由拆分和项目结构

目标：把当前单文件 API 拆分为路由、模型、服务和配置模块。

已编写：[lesson-07-project-structure.md](./lesson-07-project-structure.md)，示例应用在 `code/fastapi/lesson07_app/`。

### 第 8 课：测试 FastAPI 接口

目标：使用 TestClient 测试正常请求、校验错误和资源不存在等情况。

已编写：[lesson-08-testing.md](./lesson-08-testing.md)。

### 第 9 课：异步接口与模型调用

前置条件：完成 Python 进阶第 8 课，理解协程、`async`、`await` 和阻塞 I/O。

目标：理解 FastAPI 异步路由，使用异步客户端调用模拟模型服务，并处理超时和上游错误。

范围：只讲异步接口和非流式模型调用；不在本课展开真实模型 SDK、流式响应、重试和消息队列。

已编写：[lesson-09-async-model-calls.md](./lesson-09-async-model-calls.md)。

### 第 10 课：流式响应与聊天接口

目标：使用 `StreamingResponse` 或 SSE 返回逐步生成的结果，理解事件格式、异常、客户端断开和资源清理。

已编写：[lesson-10-streaming.md](./lesson-10-streaming.md)。

## 进入下一课的标准

完成当前课作业，并能用自己的话解释接口的请求方法、路径、输入、返回值和错误状态。
