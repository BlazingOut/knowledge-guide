# 第3课:Dockerfile 与镜像构建

> 这一课从一个真实场景开始：把一套 Python 写的外卖系统部署到云服务器。系统里有 API、MySQL 和 Redis。我们先拆清楚它由哪些部分组成、为什么要拆成多个容器，再回到 Dockerfile，把其中的 Python 应用构建成镜像。
>
> 目标：能分清云服务器镜像、Docker 基础镜像、官方服务镜像和应用镜像；能解释容器里的服务端/客户端角色；能写出可复现、体积合理、以非 root 用户运行的 Dockerfile；能解释构建上下文、镜像层、缓存和多阶段构建。
>
> 本课只构建 app 镜像。多容器之间的网络、Compose 编排和端口映射分别在第 5、6 课展开。

命令示例中 `#` 后面的文字是注释，实际执行时不输入。

## 1. 场景：把外卖系统部署到云服务器

### 1.1 系统由哪些部分组成

假设我们要部署一个外卖系统。它至少包含三部分：

```text
用户/浏览器
    -> takeout-api（Python 写的 HTTP 服务）
        -> MySQL：订单、用户、菜单等业务数据
        -> Redis：缓存、会话、订单队列
```

| 部分 | 职责 | 运行形态 |
|---|---|---|
| `takeout-api` | 提供下单、查菜单、查订单等 HTTP 接口 | Python 进程，监听 8000 |
| MySQL | 保存订单、用户、菜单等需要长期保留的数据 | 数据库服务，监听 3306 |
| Redis | 缓存菜单、保存会话、暂存订单消息 | 缓存服务，监听 6379 |

这里的"客户端 / 服务端"是**运行时角色**：

```text
服务端：监听端口，等待别人来请求
    例如 redis-server、mysqld、takeout-api 的 HTTP 服务

客户端：主动发起连接，发送请求
    例如浏览器、redis-cli、Python 的 redis/pymysql 客户端
```

`takeout-api` 同时扮演两种角色：

```text
对用户：它是服务端，监听 8000，等待 HTTP 请求
对 MySQL/Redis：它是客户端，主动连接 3306/6379
```

所以"客户端镜像 / 服务端镜像"不是 Docker 的正式分类，而是按运行时角色起的名字。一个镜像里可以同时包含客户端和服务端程序，具体跑哪一个由启动命令决定。

### 1.2 先分清四种"镜像"

部署时最容易混的是"镜像"这个词。它至少可能指四种东西：

| 说法 | 实际含义 | 例子 | 和 Dockerfile 的关系 |
|---|---|---|---|
| 云服务器镜像 | 云厂商提供的操作系统模板，用来创建一台虚拟机 | Ubuntu 22.04、Debian 12 | 不写 Dockerfile，选镜像创建服务器 |
| Docker 基础镜像 | `FROM` 后面的构建起点 | `python:3.12-slim`、`ubuntu:24.04` | Dockerfile 从这里开始 |
| 官方服务镜像 | 官方已经打包好的服务端软件 | `redis:7`、`mysql:8` | 通常不写 Dockerfile，直接运行 |
| 应用镜像 | 你自己构建的业务镜像 | `takeout-api:1.0` | 本课要写的 Dockerfile |

部署到云服务器时，层次是这样：

```text
云服务器（用 Ubuntu 22.04 镜像创建的一台虚拟机）
    └── 安装 Docker Engine
         ├── takeout-api 容器（应用镜像，自己构建）
         ├── redis 容器（官方服务镜像 redis:7）
         └── mysql 容器（官方服务镜像 mysql:8）
```

云服务器镜像负责"造一台机器"；Docker 镜像负责"在这台机器上跑什么服务"。两者不是同一层概念。

同一个 Docker 镜像也可以按不同命令运行成客户端或服务端。例如 `redis:7` 默认启动 `redis-server`：

```bash
docker run -d --name redis redis:7
# 默认命令是 redis-server，容器扮演 Redis 服务端
```

但覆盖命令后，同一个镜像可以启动 `redis-cli`：

```bash
docker run --rm redis:7 redis-cli --version
# 这次运行的是 redis-cli，容器扮演客户端
```

如果想让一个独立的客户端容器连接另一个 Redis 容器，两个容器需要加入同一个 Docker 网络，具体在第 5 课展开。

所以不要把镜像分成"客户端镜像"和"服务端镜像"；更准确的说法是：**这个容器这次运行的是客户端进程还是服务端进程**。

### 1.3 为什么要拆成多个容器

一个常见的想法是：把 Python、MySQL、Redis 全装进一个镜像，部署时只跑一个容器。这样做不是不行，但不适合正式系统：

```text
一个容器装所有东西
    -> 镜像很大，构建和拉取都慢
    -> MySQL/Redis 升级要重建整个应用镜像
    -> 数据持久化、备份、扩容都更麻烦
    -> 一个进程出问题，整个容器都受影响
    -> 无法单独扩容 API，只能连数据库一起复制
```

更常见的做法是**一个容器负责一个主要服务**：

| 容器 | 职责 | 镜像来源 | 对外端口 | 数据 |
|---|---|---|---|---|
| `takeout-api` | 业务 API | 自己构建 `takeout-api:1.0` | 8000 对公网 | 无状态，数据在 MySQL/Redis |
| `mysql` | 业务数据 | 官方 `mysql:8` | 3306 只在内网 | volume 持久化 |
| `redis` | 缓存/会话/队列 | 官方 `redis:7` | 6379 只在内网 | 可选 volume |

部署时的安全边界：

```text
公网只开放：
    22      （SSH，限制来源 IP）
    80/443 或 8000（API）

不开放：
    3306（MySQL）
    6379（Redis）
```

MySQL 和 Redis 只需要被 app 容器访问，不需要暴露到公网。它们之间的连接靠 Docker 网络和服务名，具体机制在第 5 课，编排在第 6 课。

## 2. 环境是什么

### 2.1 应用环境

在 Docker 语境里，"环境"不是"一整套操作系统"，而是应用运行所需的东西：

```text
基础系统用户态
    + 语言运行时（Python、Node、JDK……）
    + 依赖库（pip 包、系统库……）
    + 应用代码
    + 配置和环境变量
    + 启动命令
```

容器共享宿主机内核，不带完整操作系统。所以镜像可以理解成"一台已经装好运行时、依赖和代码的电脑模板"；容器是用这个模板启动起来的实例。

以外卖系统的 app 为例：

```text
takeout-api 镜像
├── 基础镜像 python:3.12-slim
│   ├── Linux 用户态（不是完整内核）
│   └── Python 3.12 + pip
├── pip 安装的依赖（redis、pymysql、orjson……）
├── 你的代码 app.py
├── 环境变量 APP_ENV、PORT、REDIS_HOST、MYSQL_HOST
└── 启动命令 CMD ["python", "app.py"]
```

`python:3.12-slim` 是**基础镜像**，它已经提供了 Linux 用户态和 Python，所以 Dockerfile 不需要再写"安装 Python"。

真实外卖系统会在 `requirements.txt` 里放 Python 客户端库：

```text
redis        # 连接 Redis 的客户端库
pymysql      # 连接 MySQL 的客户端库
```

注意：`redis` 这个 pip 包是**客户端库**，不是 Redis 服务器；`pymysql` 是 MySQL 客户端库，不是 MySQL 服务器。

### 2.2 服务环境

MySQL 和 Redis 也有自己的"环境"，但它们通常不需要你写 Dockerfile：

```text
redis:7 镜像
├── redis-server 可执行文件
├── 默认配置
└── 启动命令 redis-server

mysql:8 镜像
├── mysqld 可执行文件
├── 初始化脚本
├── 数据目录 /var/lib/mysql
└── 启动命令 mysqld
```

官方镜像已经把这些装好了。你只需要：

```text
用 image: redis:7 运行 Redis 容器
用 image: mysql:8 运行 MySQL 容器
给 MySQL 配环境变量（root 密码、数据库名）
给 MySQL 挂 volume 保存 /var/lib/mysql
```

只有需要改配置、加插件、定制初始化脚本时，才基于官方镜像写 Dockerfile，例如：

```dockerfile
FROM redis:7
COPY redis.conf /usr/local/etc/redis/redis.conf
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
```

### 2.3 镜像、容器和运行环境

| 概念 | 是什么 | 生命周期 |
|---|---|---|
| 云服务器 | 一台虚拟机，提供 CPU、内存、磁盘、网络 | 长期运行 |
| Docker 镜像 | 应用和依赖的只读模板 | 构建后长期保存 |
| Docker 容器 | 镜像启动后的运行实例 | 可创建、停止、删除 |
| 运行环境 | 容器启动时注入的配置，如环境变量、挂载、网络 | 随容器变化 |

"环境"不等于"云服务器"。云服务器是宿主，Docker 镜像把应用环境打包，容器是实际运行的进程。

## 3. 从 app 镜像开始

### 3.1 为什么先构建 app 镜像

Redis 和 MySQL 用官方镜像，只有 `takeout-api` 是你自己的代码，需要自己构建。所以这一课先写 app 的 Dockerfile。

### 3.2 示例应用

`code/docker/03-minimal-app.py` 是一个简化版外卖 API：

```text
GET /         返回服务信息（服务名、环境、JSON 库）
GET /orders   返回一条示例订单
GET /health   返回 {"status": "ok"}
```

它现在用假数据，不连接 MySQL/Redis；真实系统会把订单写进 MySQL、把缓存放进 Redis。打包方式是一样的，本课先把镜像构建讲清楚。

核心代码（省略导入和 `to_json` 辅助函数，完整代码见 `code/docker/03-minimal-app.py`）：

```python
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            payload = {"status": "ok"}
        elif self.path == "/orders":
            payload = {
                "orders": [
                    {"id": 1, "status": "created", "amount": 38.5},
                ]
            }
        elif self.path == "/":
            payload = {
                "service": "takeout-api",
                "env": APP_ENV,
                "json": "orjson" if orjson is not None else "stdlib",
            }
        else:
            self.send_error(404, "Not Found")
            return

        body = to_json(payload)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
```

### 3.3 第一个 Dockerfile

`code/docker/03-app.Dockerfile`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY 03-minimal-app.py app.py

ENV APP_ENV=dev \
    PORT=8000

EXPOSE 8000

CMD ["python", "app.py"]
```

这个版本先不安装第三方依赖，只验证"基础镜像 + 代码 + 启动命令"这条最小链路。

### 3.4 逐条解释

| 指令 | 作用 | 本课示例中的含义 |
|---|---|---|
| `FROM python:3.12-slim` | 指定基础镜像 | 从官方 Python 3.12 slim 版本开始，提供 Linux 用户态和 Python |
| `WORKDIR /app` | 设置**容器内**工作目录 | 后续 `COPY`、`RUN`、`CMD` 默认在容器里的 `/app` 下执行 |
| `COPY 03-minimal-app.py app.py` | 从构建上下文复制文件 | 把上下文里的文件复制成镜像里的 `/app/app.py` |
| `ENV APP_ENV=dev PORT=8000` | 设置运行环境变量 | 镜像运行时默认值，`docker run -e` 可以覆盖 |
| `EXPOSE 8000` | 声明容器计划监听的端口 | 只是元数据，不负责监听，也不发布端口 |
| `CMD ["python", "app.py"]` | 默认启动命令 | 容器启动时执行 `python app.py`，可被 `docker run` 参数覆盖 |

`EXPOSE`、程序监听和 `-p` 是三件不同的事：

```text
程序 bind/listen 8000   -> 真正开始监听 8000
EXPOSE 8000             -> 声明"这个容器计划监听 8000"，不负责监听
docker run -p 8000:8000 -> 把宿主机 8000 映射到容器 8000
```

端口映射的机制在第 5 课，本课为了验证 HTTP 服务会临时用一次 `-p`。

### 3.5 构建与运行

从仓库根目录构建：

```bash
docker build -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
# -f 指定 Dockerfile；-t 起名；最后一个参数是构建上下文
```

最后一个参数 `code/docker` 是**宿主机上的构建上下文**，不是 Dockerfile 路径，也不是容器里的 `/app`。它告诉 Docker：把宿主机上的 `code/docker` 目录打包发给 daemon，Dockerfile 里的 `COPY` 从这里面找文件。

运行：

```bash
docker run --rm -p 8000:8000 takeout-api:1
# --rm：容器退出后自动删除
# -p 8000:8000：把本机 8000 映射到容器 8000
```

另开一个终端验证：

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/orders
curl http://127.0.0.1:8000/health
```

预期输出：

```text
{"service":"takeout-api","env":"dev","json":"stdlib"}
{"orders":[{"id":1,"status":"created","amount":38.5}]}
{"status":"ok"}
```

Windows PowerShell 里 `curl` 可能是 `Invoke-WebRequest` 的别名；如果参数行为不一致，改用 `curl.exe` 或 `Invoke-RestMethod`。

验证完按 `Ctrl+C` 停止这个前台容器，再进行下一节，避免 8000 端口被占用。

## 4. Dockerfile 指令详解

### 4.1 FROM：基础镜像

```dockerfile
FROM python:3.12-slim
```

- 每个 Dockerfile 通常以 `FROM` 开头；只有 `ARG` 可以出现在 `FROM` 之前；
- 尽量固定版本，不要依赖 `latest`；
- Python 场景常用 `python:3.12-slim`；`alpine` 更小，但使用 musl libc，某些二进制 wheel 不兼容；
- 基础镜像决定了大部分体积和攻击面，选官方、维护活跃的镜像。

### 4.2 RUN：构建时执行命令

真实外卖系统会在构建时安装客户端依赖：

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

真实项目的 `requirements.txt` 会长这样；本课的可运行示例文件只保留 `orjson`：

```text
redis
pymysql
orjson
```

- `RUN` 在构建阶段执行，结果写入镜像层；
- 每条 `RUN` 都会产生一层，尽量把相关的安装和清理放在同一条命令里；
- 安装系统包时清理缓存：

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```

- `RUN cd /app` 不会改变后续指令的工作目录，要改目录用 `WORKDIR`。

本课的可运行示例只安装 `orjson`；`redis` 和 `pymysql` 是真实外卖系统会加的客户端库，不改变 Dockerfile 的写法。

`RUN` 只负责构建时准备环境，**不是启动应用**。启动应用用 `CMD` 或 `ENTRYPOINT`，下一节展开。

### 4.3 COPY 与 ADD

```dockerfile
COPY 03-minimal-app.py app.py
```

- `COPY` 从构建上下文复制文件或目录；
- `COPY --chown=app:app ...` 可以在复制时修改属主；
- `ADD` 比 `COPY` 多了从 URL 下载、自动解压 tar 的能力；
- 日常优先用 `COPY`，行为更可预测。

### 4.4 WORKDIR：工作目录

```dockerfile
WORKDIR /app
```

- 设置后续指令的工作目录；
- 目录不存在会自动创建；
- 比 `RUN cd /app` 可靠，因为 `RUN` 的目录变化不会延续。

这里的 `/app` 是**镜像/容器内的路径**，不是 Windows 的 `C:\app`。构建时 Docker 会在镜像里创建 `/app`；运行容器后，`docker exec ... pwd` 看到的就是这个目录。

不要把这几类路径混在一起：

| 路径 | 在哪 | 谁用 |
|---|---|---|
| `code/docker` | 宿主机 | `docker build` 的构建上下文 |
| `code/docker/03-app.Dockerfile` | 宿主机 | 构建说明书 |
| `/app` | 容器内 | 容器里的进程和 `WORKDIR` |
| `/app/app.py` | 容器内 | `COPY` 复制进去的文件 |

宿主机上的 `code/docker` 不会被"变成"容器里的 `/app`；它只是构建时提供给 Docker 的原料目录。容器里的 `/app` 是镜像里的另一个文件系统视图。第 2 课 3.8 节用 `docker exec ... pwd` 和 `ls /` 观察过这个区别。

### 4.5 ENV 与 ARG

```dockerfile
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION \
    REDIS_HOST=redis \
    MYSQL_HOST=mysql
```

| 指令 | 生效范围 | 是否留在最终镜像 | 典型用途 |
|---|---|---|---|
| `ARG` | 构建阶段 | 默认不保留 | 版本号、镜像源 |
| `ENV` | 构建和运行阶段 | 保留在镜像配置里 | 应用默认配置 |

`REDIS_HOST=redis`、`MYSQL_HOST=mysql` 是容器网络里的服务名，具体解析在第 5、6 课。这里只先建立"配置通过环境变量传入"的概念。

注意：

- `ARG` 和 `ENV` 都不适合存放密钥；它们可能出现在镜像历史、`docker inspect` 或构建日志里；
- 数据库密码应在运行时通过环境变量、`--env-file` 或 secrets 注入；
- 不要把密码写进 Dockerfile。

### 4.6 EXPOSE：声明端口

```dockerfile
EXPOSE 8000
```

- 只是声明"这个容器计划监听 8000"，并写入镜像元数据；
- **不会让程序开始监听端口**；真正监听由应用代码里的 `bind` / `listen` 决定；
- 不会自动发布到宿主机；真正发布端口要在 `docker run` 时用 `-p`，或用 `-P` 随机映射所有 `EXPOSE` 的端口。

本课示例应用里真正负责监听的是这一行：

```python
server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
# PORT 默认是 8000；这行代码才会让进程监听 8000
```

如果程序实际监听 9000，但 Dockerfile 写 `EXPOSE 8000`，`EXPOSE` 只是一条错误的声明，不会改变程序行为。

| 谁负责 | 作用 |
|---|---|
| 应用代码 | 真正 `bind` / `listen` 端口 |
| `EXPOSE` | 声明计划监听的端口，写进镜像元数据 |
| `-p` | 建立宿主机端口到容器端口的映射 |

`docker inspect` 里的 `ExposedPorts` 也只是这条声明，不代表进程真的在监听。

### 4.7 CMD 与 ENTRYPOINT

先把 `RUN` 和 `CMD` 的区别收成一张表：

| | `RUN` | `CMD` |
|---|---|---|
| 执行时机 | `docker build` 构建镜像时 | `docker run` 启动容器时 |
| 执行次数 | 每次构建执行一次，命中缓存可跳过 | 每次启动容器执行一次 |
| 结果 | 写入镜像层，改变镜像内容 | 只写元数据，指定默认命令 |
| 是否成为最终容器的进程 | 不会，构建容器执行完就结束 | 通常会成为容器的主进程 |
| 如何改变 | 改 Dockerfile 后重新构建，或 `--no-cache` | `docker run image <command>` 覆盖 |
| 典型用途 | `pip install`、`apt install`、编译、生成文件 | 启动 API、启动服务 |

一句话：

```text
RUN 是装修时把设备装进房子
CMD 是入住时按下启动开关
```

```dockerfile
CMD ["python", "app.py"]
```

`CMD` 提供默认命令，`docker run` 后面的参数会覆盖它：

```bash
docker run --rm takeout-api:1 python -c "print('override CMD')"
# 容器执行 python -c ...，而不是 python app.py
```

`ENTRYPOINT` 把可执行程序固定下来，`CMD` 变成默认参数：

```dockerfile
ENTRYPOINT ["python"]
CMD ["app.py"]
```

```bash
# 假设用上面的 ENTRYPOINT 写法构建了镜像 takeout-api:entry
docker run --rm takeout-api:entry -c "print('args appended')"
# 等价于 python -c "print('args appended')"
```

| | `CMD` | `ENTRYPOINT` |
|---|---|---|
| 作用 | 默认命令 | 固定入口 |
| `docker run` 参数 | 覆盖整个 CMD | 追加为参数 |
| 覆盖方式 | 直接传新命令 | `--entrypoint` |
| 典型场景 | 允许使用者换命令 | 镜像就是一个专用工具 |

优先使用 exec 形式 `["python", "app.py"]`，让进程直接接收信号；shell 形式 `python app.py` 会经过 `/bin/sh -c`，信号处理可能不符合预期。

### 4.8 USER：非 root 运行

```dockerfile
RUN groupadd --system app \
    && useradd --system --gid app --no-create-home app

USER app
```

- 容器默认以 root 运行；生产镜像应尽量使用非 root；
- 创建专用用户，只给运行应用所需的最小权限；
- `COPY --chown=app:app` 让应用文件属于该用户；
- 非 root 用户不能绑定 1024 以下端口，所以应用监听 8000、8080 等高位端口。

如果精简镜像里没有 `groupadd` / `useradd`，可以直接用数值 UID：

```dockerfile
RUN chown -R 10001:10001 /app
COPY --chown=10001:10001 app.py /app/app.py
USER 10001
```

### 4.9 HEALTHCHECK：健康检查

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"
```

- 容器启动后，Docker 每隔 `interval` 执行一次检查；
- 连续失败 `retries` 次后，状态变成 `unhealthy`；
- `start-period` 给应用启动留时间；
- 健康检查本身不会自动重启容器；重启策略或编排系统才会根据状态处理。

查看状态：

```bash
docker inspect --format "{{.State.Health.Status}}" 容器名
```

### 4.10 指令速查表

| 指令 | 作用 | 常见注意点 |
|---|---|---|
| `FROM` | 基础镜像 | 固定版本，优先官方 slim 镜像 |
| `RUN` | 构建时执行命令 | 合并安装与清理，减少层和缓存 |
| `COPY` | 从上下文复制文件 | 路径相对于构建上下文 |
| `ADD` | 复制 + 下载/解压 | 日常优先 `COPY` |
| `WORKDIR` | 设置工作目录 | 不要用 `RUN cd` 代替 |
| `ENV` | 运行环境变量 | 会保留在镜像中，不放密钥 |
| `ARG` | 构建参数 | 构建时有效，默认不保留 |
| `EXPOSE` | 声明计划监听的端口 | 不负责监听，也不发布端口 |
| `CMD` | 默认命令 | 可被 `docker run` 参数覆盖 |
| `ENTRYPOINT` | 固定入口 | 参数追加，可用 `--entrypoint` 覆盖 |
| `USER` | 运行用户 | 生产镜像建议非 root |
| `HEALTHCHECK` | 健康检查 | 只改状态，不自动重启 |

## 5. 构建上下文与 .dockerignore

### 5.1 构建上下文

`docker build` 会把一个目录发给 daemon，这个目录叫**构建上下文**。`COPY` / `ADD` 只能从这个目录里取文件。

```text
docker build -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
                                                                  ^^^^^^^^^
                                                                  构建上下文
```

| 参数 | 在哪个位置 | 含义 |
|---|---|---|
| `-f code/docker/03-app.Dockerfile` | 宿主机 | Dockerfile 的路径，相对于当前 shell |
| `-t takeout-api:1` | 镜像仓库 | 给构建出的镜像起名并打 tag |
| `code/docker` | 宿主机 | 构建上下文，`COPY` / `ADD` 的源路径相对于它 |

一句话：`-f` 找的是**宿主机上的 Dockerfile**，最后一个参数找的是**宿主机上的上下文目录**，两者都不是容器里的 `/app`。

因为上下文是 `code/docker`，Dockerfile 里写：

```dockerfile
COPY 03-minimal-app.py app.py
```

而不是 `COPY code/docker/03-minimal-app.py app.py`。

如果先进入 `code/docker` 再构建：

```bash
cd code/docker
docker build -f 03-app.Dockerfile -t takeout-api:1 .
```

`.` 表示当前目录就是构建上下文。

### 5.2 .dockerignore

构建上下文会整体发给 daemon。如果里面有 `.git`、`__pycache__`、日志、测试数据，构建会变慢，还可能把不该进镜像的文件带进去。

在 `code/docker/` 下创建 `.dockerignore`：

```text
__pycache__/
*.pyc
.git/
.env
```

规则：

- `.dockerignore` 放在构建上下文根目录；
- 语法类似 `.gitignore`；
- 被忽略的文件不会被 `COPY . .` 复制，也不参与缓存校验；
- 不要把 Dockerfile 本身排除掉。

## 6. 构建缓存

### 6.1 镜像层与缓存

每条会改变文件系统的指令都会产生一层：

```text
FROM python:3.12-slim       -> 基础层
WORKDIR /app                -> 元数据层
COPY 03-minimal-app.py .    -> 文件层
ENV APP_ENV=dev             -> 元数据层
CMD ["python", "app.py"]    -> 元数据层
```

Docker 会缓存每一层。下一次构建时，如果某条指令和它的输入没有变化，就复用缓存。

缓存是否命中，取决于：

- 上一条指令的缓存是否还在；
- 指令字符串是否完全一样；
- `COPY` / `ADD` 的源文件内容是否变化。

一旦某一层失效，它后面的所有层都要重新构建。

### 6.2 让缓存为你工作

第一次构建：

```bash
docker build -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
```

不改文件再构建一次，大部分步骤会显示 `CACHED`。

修改 `03-minimal-app.py` 后再构建，`COPY` 层失效，后面的层重新执行。用下面的命令看每一步：

```bash
docker build --progress=plain -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
```

强制不用缓存：

```bash
docker build --no-cache -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
```

真实外卖系统的常见顺序：

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

先把不常变的依赖清单复制进去并安装，再复制经常变的业务代码。这样改业务代码不会让依赖安装层失效。

## 7. 多阶段构建与非 root

### 7.1 为什么需要多阶段

如果在一张镜像里同时做"构建"和"运行"，最终镜像会带上编译器、包管理器缓存、测试工具，体积大、攻击面也大。

多阶段构建把过程拆成两个阶段：

```text
builder 阶段：安装构建工具、构建依赖、产出 wheel
    -> 只把需要的产物复制到 runtime 阶段
runtime 阶段：只保留运行应用需要的东西
```

最终镜像不包含 builder 阶段的工具和中间文件。

### 7.2 多阶段 Dockerfile

`code/docker/03-app-hardened.Dockerfile`：

```dockerfile
FROM python:3.12 AS builder

WORKDIR /build
COPY 03-requirements.txt requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

RUN groupadd --system app \
    && useradd --system --gid app --no-create-home app

COPY --chown=app:app 03-minimal-app.py app.py

ENV APP_ENV=prod \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

CMD ["python", "app.py"]
```

拆开看：

| 部分 | 作用 |
|---|---|
| `FROM python:3.12 AS builder` | 第一阶段，命名为 `builder`，负责构建依赖 |
| `RUN pip wheel ...` | 把依赖构建成 wheel，放在 `/wheels` |
| `FROM python:3.12-slim` | 第二阶段，最终镜像的起点 |
| `COPY --from=builder /wheels /wheels` | 只从 builder 复制产物 |
| `RUN pip install ... && rm -rf /wheels` | 安装 wheel 后删掉 wheel，减小体积 |
| `USER app` | 最终容器以非 root 运行 |

本例用 `orjson` 作为第三方依赖：builder 阶段把它构建成 wheel，runtime 阶段只安装 wheel。单阶段镜像没有安装它，所以 `/` 返回 `"json":"stdlib"`；多阶段镜像会返回 `"json":"orjson"`。

### 7.3 非 root 用户

为什么不用 root：

- 容器里的 root 虽然受命名空间限制，但一旦挂载了宿主机目录或暴露了内核漏洞，影响更大；
- 生产环境通常要求容器以非 root 运行；
- 非 root 用户能运行的命令更少，攻击面更小。

验证：

```bash
docker run --rm takeout-api:2 python -c "import os; print(os.getuid(), os.getgid())"
# 输出非 0 的 uid/gid，说明 USER app 生效
```

### 7.4 验证最终镜像

构建多阶段镜像：

```bash
docker build -f code/docker/03-app-hardened.Dockerfile -t takeout-api:2 code/docker
```

比较体积：

```bash
docker images takeout-api
```

注意：本例的 `takeout-api:1` 没有第三方依赖，`takeout-api:2` 多装了 `orjson`，所以 `:2` 不一定比 `:1` 小。多阶段构建的收益要和"把构建工具、编译器和依赖缓存也留在最终镜像"的单阶段版本比较；真实项目里 builder 会安装编译工具，差异才明显。

查看构建历史：

```bash
docker history takeout-api:2
```

## 8. 运行课程代码

### 8.1 构建单阶段镜像

```bash
docker build -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
```

### 8.2 运行并验证接口

```bash
docker run --rm -p 8000:8000 takeout-api:1
# 前台运行；保持这个终端，另开一个终端执行 curl
```

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/orders
curl http://127.0.0.1:8000/health
```

预期：

```text
{"service":"takeout-api","env":"dev","json":"stdlib"}
{"orders":[{"id":1,"status":"created","amount":38.5}]}
{"status":"ok"}
```

### 8.3 观察 CMD 被覆盖

```bash
docker run --rm takeout-api:1 python -c "print('override CMD')"
# docker run 后面的命令覆盖 Dockerfile 里的 CMD
```

### 8.4 构建多阶段镜像并验证非 root

```bash
docker build -f code/docker/03-app-hardened.Dockerfile -t takeout-api:2 code/docker
# 多阶段构建：builder 产出 wheel，runtime 只装 wheel

docker run --rm takeout-api:2 python -c "import os; print(os.getuid(), os.getgid())"
# 输出非 0 uid/gid，说明 USER app 生效

docker run -d --name takeout-health -p 8000:8000 takeout-api:2
# 后台运行，等待健康检查

sleep 10
docker ps
# STATUS 里应出现 (healthy)

docker inspect --format "{{.State.Health.Status}}" takeout-health
# 输出 healthy

docker rm -f takeout-health
# 清理练习容器
```

### 8.5 观察缓存

```bash
docker build -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
# 第二次构建，大部分步骤显示 CACHED

# 修改 03-minimal-app.py 里的任意一行后，再执行：
docker build --progress=plain -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
# COPY 层失效，后面的层重新执行
```

## 9. 常见错误

### 9.1 `COPY failed: file not found in build context`

```text
COPY failed: file not found in build context or excluded by .dockerignore
```

原因通常是 `COPY` 的路径写成了相对仓库根目录，但构建上下文是 `code/docker`。`COPY` 的源路径相对于构建上下文，不是相对于当前 shell。

### 9.2 改了代码但构建没有变化

可能命中了缓存，或者改的文件不在 `COPY` 范围内。用 `--progress=plain` 看每一步是否 `CACHED`；必要时 `--no-cache`。

### 9.3 `COPY . .` 导致缓存频繁失效

`COPY . .` 会把所有文件都纳入缓存校验，日志、测试数据、临时文件一变就失效。用 `.dockerignore` 排除无关文件，或者只复制需要的文件。

### 9.4 容器启动后立刻退出

```bash
docker ps -a
docker logs 容器名
```

常见原因：

- `CMD` 执行的进程很快结束；
- 启动命令写错，路径不对；
- 应用缺少环境变量或依赖，启动时报错。

容器的主进程退出，容器就退出；这不是 Docker 故障。

### 9.5 `permission denied`

非 root 用户对文件或目录没有写权限。检查：

```text
COPY 时是否用了 --chown=app:app
应用是否需要写目录；需要时提前创建并 chown
是否监听了 1024 以下的端口
```

### 9.6 `EXPOSE` 了端口但本机访问不到

`EXPOSE` 只是声明，既不会让程序监听，也不会发布端口。运行时仍需要 `-p`：

```bash
docker run -p 8000:8000 takeout-api:1
```

端口映射的排查在第 5 课。

### 9.7 把密钥写进 `ENV` 或 `ARG`

```dockerfile
ENV DB_PASSWORD=secret      # 错误：会留在镜像配置里
ARG DB_PASSWORD=secret      # 错误：可能出现在构建历史和日志里
```

密码不要进镜像。运行时用环境变量、`--env-file` 或 Docker secrets；构建期需要密钥时用 BuildKit secret 挂载，本课程不展开。

### 9.8 app 容器连不上 MySQL/Redis

如果应用里写：

```text
MYSQL_HOST=127.0.0.1
REDIS_HOST=127.0.0.1
```

在 app 容器里，`127.0.0.1` 指的是 app 容器自己，不是 MySQL/Redis 容器。正确做法是使用 Compose 网络里的服务名：

```text
MYSQL_HOST=mysql
REDIS_HOST=redis
```

具体网络机制在第 5 课，编排在第 6 课。

## 10. 课后作业

在外卖系统 app 的基础上完成：

1. 增加 `GET /version` 接口，返回 `{"version": "..."}`；
2. 用 `ARG APP_VERSION` 在构建时传入版本号，并让 `/version` 返回它；
3. 用两个不同的 `--build-arg APP_VERSION` 构建两个镜像，分别运行并验证返回值；
4. 把 `COPY 03-minimal-app.py app.py` 改成 `COPY . .`，观察第二次构建的缓存变化；
5. 添加 `.dockerignore` 排除 `__pycache__/`、`*.pyc`、`.env`，再构建一次，说明缓存为什么更稳定；
6. 回答：为什么 app 镜像只安装 `redis`、`pymysql` 这些客户端库，而不安装 `redis-server`、`mysqld`？

要求：

- `/version` 在单阶段和多阶段镜像里都能返回正确版本；
- 构建日志里能看到 `--build-arg` 生效；
- 能解释 `ARG` 与 `ENV` 的生效范围差异；
- 不把任何密钥写进 Dockerfile。

## 11. 验收问题 / 过关清单

达到下面的程度，就可以进入下一课：

```text
能区分云服务器镜像、Docker 基础镜像、官方服务镜像和应用镜像
能说明客户端/服务端是运行时角色，不是镜像类型
能把外卖系统拆成 app、mysql、redis 三个容器，并说明各自职责
能解释为什么不在 app 镜像里安装 Redis/MySQL 服务器
能写一个包含 FROM、WORKDIR、COPY、ENV、EXPOSE、CMD 的 Dockerfile
能用 docker build -f ... -t ... 构建镜像
能解释构建上下文和 COPY 路径的关系
能解释 CMD 和 ENTRYPOINT 的区别
能解释 ARG 和 ENV 的生效范围，知道为什么不能放密钥
能解释 EXPOSE 和 -p 的区别
能用 .dockerignore 控制构建上下文
能解释构建缓存什么时候失效，并用 --progress=plain 观察
能写出多阶段 Dockerfile，把构建工具留在 builder
能用 USER 和 COPY --chown 让容器以非 root 运行
能配置 HEALTHCHECK 并用 docker inspect 查看健康状态
能排查 COPY 找不到文件、容器启动即退出、permission denied
```

## 12. 面试高频考点

### 12.1 云服务器镜像和 Docker 镜像有什么区别？

> 云服务器镜像是云厂商提供的操作系统模板，用来创建一台虚拟机；Docker 镜像把应用和依赖打包在一起，运行在云服务器的 Docker Engine 里。前者是"机器模板"，后者是"应用包"，不是同一层概念。

### 12.2 为什么 Redis/MySQL 不装进 app 镜像？

> Redis/MySQL 是独立服务，应该各自运行在官方镜像的容器里；app 镜像只安装客户端库（如 `redis`、`pymysql`），通过 Docker 网络连接服务名。这样升级、扩容、数据持久化和故障隔离都更简单，镜像也更小。

### 12.3 一个镜像能同时是客户端和服务端吗？

> 可以。客户端/服务端是运行时角色，不是镜像类型。比如 `redis:7` 默认启动 `redis-server`，是服务端；覆盖命令运行 `redis-cli` 时，就是客户端。app 容器对用户是 HTTP 服务端，对 Redis/MySQL 又是客户端。

### 12.4 一个 Dockerfile 从构建到运行经历了什么？

> `docker build` 把构建上下文发给 Docker daemon，按 Dockerfile 逐条执行指令，每条指令产生一个镜像层，最后给镜像打 tag。`docker run` 用镜像创建容器，在只读层上加一个可写层，再启动 `CMD` 或 `ENTRYPOINT` 指定的进程。

### 12.5 `CMD` 和 `ENTRYPOINT` 有什么区别？

> `CMD` 是默认命令，`docker run` 后面的参数会覆盖它；`ENTRYPOINT` 是固定入口，`docker run` 后面的参数会追加为它的参数。需要镜像像专用工具一样使用时用 `ENTRYPOINT`，需要允许使用者替换命令时用 `CMD`。两者都推荐 exec 形式，便于正确接收信号。

### 12.6 `COPY` 和 `ADD` 有什么区别？

> `COPY` 只从构建上下文复制文件或目录；`ADD` 还支持从 URL 下载和自动解压 tar。`ADD` 的隐式行为容易让构建结果不直观，所以日常优先用 `COPY`。

### 12.7 Docker 构建缓存什么时候失效？

> 缓存按层复用。某条指令的字符串、父层缓存或 `COPY`/`ADD` 的源文件内容发生变化，这一层就失效，后面的层也要重建。优化方式是先把不常变的依赖安装放在前面，把经常变的源码复制放在后面，并用 `.dockerignore` 排除无关文件。

### 12.8 多阶段构建解决什么问题？

> 多阶段构建把编译、安装依赖等构建过程放在 builder 阶段，只把运行所需的产物复制到最终阶段。这样最终镜像不包含编译器、包管理器缓存和构建工具，体积更小、攻击面更小。常见写法是 `COPY --from=builder`。

### 12.9 为什么容器里不建议用 root？

> 容器默认以 root 运行，一旦应用被突破，攻击者在内核漏洞、挂载目录等场景下可能获得更大权限。生产镜像应创建专用用户，用 `USER` 切换，用 `COPY --chown` 设置文件属主，并尽量使用只读文件系统和最小权限。

### 12.10 `EXPOSE` 和 `-p` 有什么区别？

> `EXPOSE` 只是声明容器打算监听的端口，写入镜像元数据；它不会让程序开始监听，也不会发布到宿主机。真正监听由应用代码的 `bind` / `listen` 决定；`-p` 才是在运行时建立宿主机端口到容器端口的映射。只写 `EXPOSE` 时，宿主机仍然访问不到容器服务。

### 12.11 怎样减小镜像体积？

> 选择合适的基础镜像（slim、distroless），使用多阶段构建，只复制运行所需文件，合并 `RUN` 并在同一层清理包管理器缓存，使用 `.dockerignore` 排除无关文件，避免把 `.git`、测试数据和构建工具带进最终镜像。不要为了小而无条件用 alpine，Python 的二进制 wheel 可能有 musl 兼容问题。

### 12.12 `RUN` 和 `CMD` 有什么区别？

> `RUN` 在 `docker build` 时执行，结果写入镜像层，用来安装依赖、编译、生成文件；它不会成为最终容器的进程。`CMD` 在容器启动时执行，只指定默认命令，可以被 `docker run` 后面的参数覆盖，通常会成为容器的主进程。一句话：`RUN` 准备镜像，`CMD` 启动容器。

## 13. 下一课预告

下一课解决"容器删了数据怎么办"：

```text
容器的可写层是什么，删除容器后数据去哪了？
volume 和 bind mount 有什么区别？
MySQL 容器为什么必须挂载 /var/lib/mysql？
挂载后权限不对、文件属主变化怎么处理？
怎样备份和恢复容器里的数据？
```
