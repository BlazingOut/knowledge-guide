# 第7课:综合练习：把外卖系统装进 Docker

> 前面六课分别讲了镜像、容器、隔离、Dockerfile、数据卷、端口网络和 Compose。这一课把它们串起来：从一份 FastAPI 代码开始，构建 app 镜像，再用 Compose 启动 app + Redis + MySQL，验证下单、查询和持久化。
>
> 学完这一课，你应该能独立把一套多服务应用装进 Docker，并解释每一步为什么这样做。

命令示例中 `#` 后面的文字是注释，实际执行时不输入。

## 1. 目标和范围

这一课完成一件完整的事：

```text
FastAPI 代码（07-main.py）
    -> 多阶段 Dockerfile（07-app.Dockerfile）
    -> app 镜像
    -> Compose（07-compose.yaml）
    -> app + redis + mysql 三个容器
    -> 验证下单、查询、重启后数据仍在
```

目标架构：

```text
用户
    -> 宿主机 8000
    -> app 容器（FastAPI，监听 8000）
        ├── 写订单、查订单 -> mysql 容器（3306）
        └── 订单计数       -> redis 容器（6379）
```

涉及的文件：

```text
code/docker/
├── 07-main.py            FastAPI 应用
├── 07-requirements.txt   依赖
├── 07-app.Dockerfile     app 的多阶段 Dockerfile
├── 07-compose.yaml       三个服务的编排
└── 04-init.sql           MySQL 初始化脚本（复用第 4 课）
```

## 2. 应用代码：FastAPI 连接 MySQL/Redis

`code/docker/07-main.py` 是一个真正连接数据库和缓存的 FastAPI 应用。

### 2.1 接口

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/` | 返回服务信息和依赖地址 |
| GET | `/health` | 健康检查 |
| POST | `/orders` | 创建订单：写 MySQL，Redis 计数 |
| GET | `/orders` | 查询最近 10 条订单 |
| GET | `/orders/count` | 查看 Redis 里的订单计数 |

### 2.2 配置通过环境变量传入

```python
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "example")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "takeout")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
```

这些值在 Compose 里会指向 service 名 `mysql` 和 `redis`。

### 2.3 创建订单

```python
@app.post("/orders")
def create_order(order: OrderIn) -> dict:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO orders (user_id, amount) VALUES (%s, %s)",
            (order.user_id, order.amount),
        )
        order_id = cur.lastrowid
    conn.close()

    get_redis().incr("orders:count")
    return {"id": order_id, "user_id": order.user_id, "amount": order.amount}
```

- `pymysql` 是 MySQL 客户端库，负责连接和 SQL；
- `redis` 是 Redis 客户端库，负责读写缓存；
- 应用只安装客户端库，不安装 MySQL/Redis 服务器。

### 2.4 启动前等待依赖

```python
def wait_for_deps(retries: int = 30) -> None:
    for _ in range(retries):
        try:
            get_db().close()
            get_redis().ping()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("依赖未就绪")
```

容器启动时，MySQL 可能还在初始化。这个循环会重试 30 秒；配合 Compose 的 healthcheck 和 `depends_on`，能避免一启动就连接失败。

## 3. Dockerfile：多阶段 + 非 root

`code/docker/07-app.Dockerfile`：

```dockerfile
FROM python:3.12 AS builder

WORKDIR /build
COPY 07-requirements.txt requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

RUN groupadd --system app \
    && useradd --system --gid app --no-create-home app

COPY --chown=app:app 07-main.py app.py

ENV APP_ENV=prod \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

CMD ["python", "app.py"]
```

对应前面几课：

| 内容 | 来自哪一课 |
|---|---|
| 多阶段构建、builder 只装依赖 | 第 3 课 |
| 非 root 用户、`COPY --chown` | 第 3 课 |
| `HEALTHCHECK` | 第 3 课 |
| 只 `EXPOSE`，不 `-p` | 第 3、5 课 |

`CMD ["python", "app.py"]` 里的 `app.py` 最终调用：

```python
uvicorn.run(app, host="0.0.0.0", port=PORT)
```

`0.0.0.0` 保证 app 能被 Docker 网络和端口映射访问；只监听容器内 `127.0.0.1` 会连不进去。

## 4. Compose：app + redis + mysql

`code/docker/07-compose.yaml`：

```yaml
services:
  app:
    build:
      context: .
      dockerfile: 07-app.Dockerfile
    ports:
      - "8000:8000"
    environment:
      MYSQL_HOST: mysql
      MYSQL_PORT: 3306
      MYSQL_USER: root
      MYSQL_PASSWORD: example
      MYSQL_DATABASE: takeout
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      redis:
        condition: service_healthy
      mysql:
        condition: service_healthy

  redis:
    image: redis:7
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: example
      MYSQL_DATABASE: takeout
    volumes:
      - mysql-data:/var/lib/mysql
      - ./04-init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-pexample"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 20s

volumes:
  redis-data:
  mysql-data:
```

关键点：

- `app` 用 `build` 构建镜像；`redis`、`mysql` 用官方 `image`；
- 只有 `app` 发布 `8000`；Redis/MySQL 不发布；
- app 里的 `MYSQL_HOST=mysql`、`REDIS_HOST=redis` 是 service 名，由 Compose DNS 解析；
- `depends_on` 用 `condition: service_healthy`，等 Redis/MySQL 健康后才启动 app；
- `mysql-data`、`redis-data` 是 named volume，`down` 不会删数据；
- `04-init.sql` 在 MySQL 第一次初始化时建库建表。

## 5. 启动与验证

从仓库根目录启动：

```bash
docker compose -f code/docker/07-compose.yaml up -d --build
# -d 后台运行；--build 先构建 app 镜像
```

查看状态：

```bash
docker compose -f code/docker/07-compose.yaml ps
```

等 MySQL 初始化完成，看日志：

```bash
docker compose -f code/docker/07-compose.yaml logs -f mysql
# Ctrl+C 退出
```

验证接口：

```bash
curl.exe http://127.0.0.1:8000/
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/orders
```

创建一单：

```bash
curl.exe -X POST http://127.0.0.1:8000/orders -H "Content-Type: application/json" -d '{"user_id":1,"amount":38.5}'
```

预期返回：

```text
{"id":1,"user_id":1,"amount":38.5}
```

查询订单和计数：

```bash
curl.exe http://127.0.0.1:8000/orders
curl.exe http://127.0.0.1:8000/orders/count
```

Windows PowerShell 里如果 `curl.exe` 行为不符合预期，可以用：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/orders -ContentType 'application/json' -Body '{"user_id":1,"amount":38.5}'
Invoke-RestMethod http://127.0.0.1:8000/orders
Invoke-RestMethod http://127.0.0.1:8000/orders/count
```

## 6. 验证数据持久化

停掉并删除容器，但保留数据卷：

```bash
docker compose -f code/docker/07-compose.yaml down
# 删除容器和网络，保留 redis-data、mysql-data
```

重新启动：

```bash
docker compose -f code/docker/07-compose.yaml up -d
# 不需要 --build；镜像已经构建过
```

再查：

```bash
curl.exe http://127.0.0.1:8000/orders
curl.exe http://127.0.0.1:8000/orders/count
```

订单和计数应该还在，因为数据在 named volume 里。

如果确实要清空数据重新初始化：

```bash
docker compose -f code/docker/07-compose.yaml down -v
# 删除 redis-data、mysql-data；下次 up 会重新初始化
```

## 7. 常见故障排查

### 7.1 app 启动后立刻退出

```bash
docker compose -f code/docker/07-compose.yaml ps
docker compose -f code/docker/07-compose.yaml logs app
```

常见原因：

- MySQL/Redis 没就绪，`wait_for_deps` 超时退出；
- 环境变量写错，app 连不上；
- 端口被占用。

### 7.2 MySQL 还在初始化时 app 就连了

`depends_on: condition: service_healthy` 会等 MySQL 健康；app 里还有 30 秒重试。两者叠加，基本能避免。

### 7.3 app 里写 `127.0.0.1` 连不上

app 容器里的 `127.0.0.1` 是 app 自己。必须用：

```text
MYSQL_HOST=mysql
REDIS_HOST=redis
```

### 7.4 初始化 SQL 没有执行

`mysql-data` 已经有数据时，`04-init.sql` 不会重复执行。需要新 volume，或 `down -v`（会丢数据）。

### 7.5 端口 8000 被占用

```text
Bind for 0.0.0.0:8000 failed: port is already allocated
```

找旧容器或占用进程，换端口，例如 `- "8080:8000"`。

### 7.6 `permission denied`

非 root 用户写目录失败。检查 `COPY --chown`、目录属主；数据库数据用 named volume，不用 bind mount。

## 8. 完整练习清单

```bash
# 1. 构建并启动整套环境
docker compose -f code/docker/07-compose.yaml up -d --build

# 2. 查看状态
docker compose -f code/docker/07-compose.yaml ps

# 3. 看 MySQL 初始化日志
docker compose -f code/docker/07-compose.yaml logs -f mysql

# 4. 验证接口
curl.exe http://127.0.0.1:8000/
curl.exe http://127.0.0.1:8000/health

# 5. 创建订单
curl.exe -X POST http://127.0.0.1:8000/orders -H "Content-Type: application/json" -d '{"user_id":1,"amount":38.5}'

# 6. 查询订单和计数
curl.exe http://127.0.0.1:8000/orders
curl.exe http://127.0.0.1:8000/orders/count

# 7. 进容器确认 service 名可解析
docker compose -f code/docker/07-compose.yaml exec app python -c "import socket; print(socket.gethostbyname('mysql'), socket.gethostbyname('redis'))"

# 8. 停掉并保留数据
docker compose -f code/docker/07-compose.yaml down

# 9. 重新启动，验证数据还在
docker compose -f code/docker/07-compose.yaml up -d
curl.exe http://127.0.0.1:8000/orders
curl.exe http://127.0.0.1:8000/orders/count

# 10. 清理（确认后）
docker compose -f code/docker/07-compose.yaml down -v
```

## 9. 课后作业

1. 增加 `GET /orders/{order_id}`，按 ID 查询一条订单；不存在的 ID 返回 404；
2. 给 app 增加 `env_file`，把 `MYSQL_PASSWORD` 移到 `.env` 文件里，验证 `.env` 不提交到仓库；
3. 给 app 的 Compose 增加 healthcheck，并在 `docker compose ps` 里观察健康状态；
4. 增加一个 `adminer` 服务（`profiles: ["tools"]`），用 `--profile tools` 启动并访问 MySQL；
5. 回答：`depends_on` 和 `wait_for_deps` 分别解决了什么问题？为什么两个都要？

要求：

- 能解释每一步用了第几课的知识；
- 能复现"下单 -> 重启 -> 数据还在"；
- 不把密码写进镜像或提交到仓库。

## 10. 验收问题 / 过关清单

达到下面的程度，就可以进入下一课：

```text
能画出用户 -> app -> MySQL/Redis 的完整链路
能解释 app 为什么只安装客户端库，不安装服务器
能说明多阶段构建和 builder/runtime 的分工
能读懂 07-compose.yaml 的 build、image、ports、environment、volumes、depends_on、healthcheck
能解释 service 名就是容器网络里的 DNS 名
能用 docker compose up/down/ps/logs/exec 操作整套环境
能验证下单后 MySQL 有订单、Redis 计数增加
能验证 down 后数据仍在、down -v 后数据清空
能排查 app 启动即退出、127.0.0.1 连不上、初始化 SQL 不执行、端口占用
```

## 11. 面试高频考点

### 11.1 一套多服务应用怎么装进 Docker？

> 先把每个服务拆成独立容器：app 用自己写的 Dockerfile 构建，Redis/MySQL 用官方镜像。再用 Compose 描述 service、端口、环境变量、数据卷和依赖。app 通过 service 名访问 Redis/MySQL，数据库数据挂 named volume，只对外暴露 app 端口。

### 11.2 为什么 app 镜像要装 `redis`、`pymysql`，但不装 Redis/MySQL 服务器？

> `redis` 和 `pymysql` 是 Python 客户端库，让 app 能连接 Redis/MySQL；Redis/MySQL 服务器是独立服务，应该各自跑官方镜像。这样升级、扩容、数据持久化和故障隔离都更简单。

### 11.3 `depends_on` 和应用里的重试分别解决什么？

> `depends_on: service_healthy` 让 Compose 等依赖容器健康后再启动 app；应用里的 `wait_for_deps` 处理启动竞态，即使依赖临时不可用也能重试。前者管启动顺序，后者管应用自身的健壮性，两者互补。

### 11.4 怎样验证数据持久化？

> 向 MySQL 写一条订单、向 Redis 计数，然后 `docker compose down` 再 `up -d`，数据仍然存在，说明数据在 named volume 里；`down -v` 会删除 volume，数据丢失。

### 11.5 容器起不来按什么顺序排查？

> 先 `docker compose ps` 看状态，再 `docker compose logs 服务名` 看日志，然后检查环境变量、service 名、端口和健康检查，最后用 `docker compose exec 服务 sh` 进容器验证网络和配置。

## 12. 下一课预告

下一课进入生产化与排障：

```text
镜像怎么进入生产环境，tag 策略怎么定？
CI 怎么构建和推送镜像？
镜像扫描、非 root、只读文件系统怎么做？
资源限制、重启策略、日志怎么配？
Nginx 反向代理和线上排障怎么做？
```
