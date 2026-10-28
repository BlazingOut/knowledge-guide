# Redis 基础与连接

> 这一课是 Redis 正式课程的起点。
>
> 目标不是马上记住很多命令，而是先理解：Redis 是什么类型的服务，应用如何找到并连接 Redis，以及 Redis 和 SQLite、MySQL 分别适合做什么。

## 一、这一课要解决什么问题

如果只把 Redis 当成一组命令，很容易形成这样的印象：

```text
执行 SET
    -> 得到一个值
```

但在真实应用中，Redis 命令前后还有服务启动、网络连接和数据生命周期：

```text
应用启动
    -> 找到 Redis 服务
    -> 建立客户端连接
    -> 发送命令
    -> Redis 在内存中读取或修改数据
    -> 返回结果
```

因此，这一课先回答六个基础问题：

1. Redis 是数据库、缓存，还是消息队列？
2. Redis 和 SQLite、MySQL 有什么区别？
3. Redis Server 和 Redis 客户端分别做什么？
4. 应用怎样找到并连接 Redis？
5. Redis 中最基本的数据读写是什么样的？
6. 为什么 Redis 中的数据可能会自动消失？

后面的数据结构、缓存模式、分布式锁和异步任务，都建立在这些概念之上。

---

## 二、Redis 是什么

### 1. Redis 是独立运行的服务

Redis 通常不是应用目录中的一个数据库文件，而是一个独立运行的服务：

```text
FastAPI 应用
    |
    | 网络连接
    v
Redis Server
    |
    ├── 内存中的 Key-Value 数据
    ├── 过期时间
    └── 可选的持久化文件
```

Redis Server 负责：

- 监听一个网络端口；
- 接收客户端连接；
- 解析客户端发送的命令；
- 在内存数据中读取或修改值；
- 检查命令和账号权限；
- 返回结果或错误；
- 根据配置执行过期和持久化操作。

应用不是直接打开 Redis 的内部数据文件，而是通过 Redis 协议访问服务。

Redis 常见的本地连接配置可以写成：

```text
redis://127.0.0.1:6379/0
```

它可以拆成：

```text
协议：redis
主机：127.0.0.1
端口：6379
数据库编号：0
```

`6379` 是 Redis 常见的默认端口，但端口不是永远固定的，实际项目应以服务配置为准。

### 2. Redis 不只是缓存

Redis 经常被称为“缓存”，这是它最常见的用途之一，但不是它唯一的用途：

```text
Redis
├── 缓存查询结果
├── 保存短期会话
├── 记录计数器
├── 实现排行榜
├── 保存限流状态
├── 记录幂等请求
└── 支持简单的任务队列
```

Redis 的共同特点是：

- 数据主要放在内存中；
- 读写速度通常很快；
- 通过网络服务被多个应用实例访问；
- 支持字符串、哈希、列表、集合等数据结构；
- 可以为数据设置过期时间；
- 可以选择是否将数据持久化到磁盘。

但“速度快”不等于“所有数据都应该放 Redis”。用户账户、订单和长期业务事实通常仍然需要由关系型数据库保存。Redis 更适合保存可以快速访问、短期存在或能够重新计算的数据。

---

## 三、Redis 和 SQLite、MySQL 的区别

### 1. SQLite 更像一个文件

使用 SQLite 时，应用通常直接打开一个数据库文件：

```text
应用进程
    -> 打开 app.db
    -> 读取和修改文件
```

SQLite 适合：

- 本地工具；
- 单机应用；
- 测试和小型项目；
- 不需要单独部署数据库服务的场景。

### 2. MySQL 是关系型数据库服务器

MySQL 的结构通常是：

```text
Web 应用 A ─┐
            ├── 网络连接 ──> MySQL Server
Web 应用 B ─┘                  ├── 数据库
                               ├── 表
                               └── 数据文件
```

MySQL 适合保存结构化的长期业务数据，例如：

- 用户；
- 商品；
- 订单；
- 账单；
- 关系复杂、需要查询和事务的数据。

MySQL 重点提供：

- 表和列；
- 主键、唯一约束和外键；
- SQL 查询；
- 事务；
- 索引；
- 多用户并发访问。

### 3. Redis 更像一个共享的高速状态服务

Redis 的结构更像这样：

```text
Web 应用 A ─┐
Web 应用 B ─┼──> Redis Server
Worker     ─┘       ├── key: value
                    ├── key: hash
                    └── key: list
```

Redis 不以关系型表和 SQL 为核心，而是围绕 Key 和数据结构工作：

```text
Key                         Value
user:1001:session           {"logged_in": true}
article:42                  {"title": "...", "view_count": 10}
rate_limit:user:1001        7
```

Redis 适合：

- 查询结果缓存；
- 短期会话；
- 计数器；
- 排行榜；
- 限流状态；
- 幂等请求记录；
- 异步任务状态。

### 4. 三者不是简单的替代关系

一个实际应用可能同时使用三者：

```text
FastAPI
    ├── MySQL：保存用户、订单等长期事实
    ├── Redis：保存缓存、会话和任务状态
    └── SQLite：本地开发或小型单机数据
```

例如，用户资料的真实来源可以是 MySQL：

```text
请求用户资料
    -> 先查询 Redis
    -> Redis 有数据：直接返回
    -> Redis 没有数据：查询 MySQL
    -> 将结果写入 Redis
    -> 返回结果
```

这里 Redis 是访问加速层，MySQL 才是长期数据来源。后续课程会详细讨论这种 Cache Aside 模式。

可以先使用下面的方式区分它们：

| 组件 | 主要数据模型 | 常见职责 | 数据是否适合长期保存 |
|---|---|---|---|
| SQLite | 表、行、列、SQL | 本地和单机关系型数据 | 可以 |
| MySQL | 表、行、列、SQL | 共享业务数据、事务和复杂查询 | 可以 |
| Redis | Key 和多种数据结构 | 缓存、状态、计数和任务 | 取决于持久化和业务设计 |

不要把“Redis 很快”理解成“Redis 一定比 MySQL 更适合保存业务数据”。数据模型、事务需求、恢复要求和查询方式都要一起考虑。

---

## 四、启动 Redis 服务

### 1. 服务和客户端是两个程序

使用 Redis 时通常涉及两个角色：

```text
redis-server：启动 Redis 服务
redis-cli：连接 Redis 并发送命令
```

可以把它们理解为：

```text
redis-cli       -> 提出请求
redis-server    -> 接收、执行、返回结果
```

如果 Redis Server 没有启动，单独执行客户端不会凭空产生数据库服务。

### 2. 用 Docker 启动本地 Redis

如果本机已经安装 Docker，可以使用一个专门的练习容器：

```bash
docker run --name redis-course -p 6379:6379 -d redis:7
```

参数含义：

```text
--name redis-course：容器名称
-p 6379:6379：把本机 6379 映射到容器 6379
-d：后台运行
redis:7：使用 Redis 7 镜像
```

这条命令启动了一个隔离的 Redis 环境：容器内部真的运行着 `redis-server` 进程，监听 6379 端口。隔离、镜像和容器的详细机制在 Docker 课程中展开，本课先会用它即可。

查看容器是否正在运行：

```bash
docker ps
```

查看容器日志：

```bash
docker logs redis-course
```

停止容器：

```bash
docker stop redis-course
```

重新启动已经停止的容器：

```bash
docker start redis-course
```

删除练习容器：

```bash
docker rm redis-course
```

删除容器前要确认它只是本课的练习环境。不要对包含重要数据的容器直接执行删除操作。

### 3. 不使用 Docker 时

也可以直接安装 Redis 兼容服务，并让它监听本机端口。不同操作系统的安装方式不同，本课程不要求死记安装命令。关键是确认三件事：

```text
服务是否启动
服务监听哪个主机和端口
客户端是否能够连接
```

Windows 学习环境可以使用 Docker Desktop，或者使用一个能够提供 Redis 服务的本地开发环境。只要最终能够通过 `redis-cli` 或 Python 客户端访问 `127.0.0.1:6379`，后续练习的连接方式基本一致。

### 4. 确认端口是否被占用

如果启动 Redis 时提示端口已经被使用，可能是：

- 已经有一个 Redis 实例在运行；
- 其他程序占用了 6379；
- Docker 容器重复映射了同一个端口。

先确认是否已有容器：

```bash
docker ps -a
```

如果 Redis 服务使用了其他本机端口，例如 6380：

```bash
docker run --name redis-course-6380 -p 6380:6379 -d redis:7
```

此时客户端连接本机的 `6380`，但容器内部仍然使用 `6379`：

```text
本机 127.0.0.1:6380
    -> 容器内 Redis Server:6379
```

端口映射的两侧不一定相同。应用连接的是本机暴露出来的端口。

---

## 五、使用 redis-cli 连接

### 1. 建立本地连接

连接前需要有一个 `redis-cli` 程序。如果你手动安装了 Redis 并把命令加入 PATH，可以直接执行：

```bash
redis-cli -h 127.0.0.1 -p 6379
```

参数含义：

```text
-h：Redis Server 的主机
-p：Redis Server 的端口
```

如果你是用 Docker 启动的 Redis（本课推荐方式），Windows 本机通常没有 `redis-cli` 程序——它只在容器里面。此时进入容器执行：

```bash
docker exec -it redis-course redis-cli
```

参数含义：

```text
docker exec：在运行中的容器里执行命令
-it：交互式模式（保持输入并分配终端）
redis-course：容器名
redis-cli：在容器内启动的命令行客户端
```

进入后同样会看到提示符：

```text
127.0.0.1:6379>
```

之后的命令（PING、SET、GET、TTL 等）在容器内外完全一样。若容器没有在运行，`docker exec` 会报错，先用 `docker ps` 确认 `redis-course` 正在运行。

连接成功后，通常会看到 Redis 命令提示符：

```text
127.0.0.1:6379>
```

### 2. 先执行 PING

连接后先执行：

```redis
PING
```

正常结果：

```text
PONG
```

`PONG` 说明客户端已经连到了一个能够响应命令的 Redis 服务。它不能单独证明：

- 账号拥有所有权限；
- 业务 Key 存在；
- Redis 一定有持久化配置；
- 网络链路在高负载下仍然稳定。

它只是最基本的连通性检查。

### 3. 查看服务信息

可以使用：

```redis
INFO server
```

查看 Redis 版本和运行信息。也可以查看服务是否正在处理请求：

```redis
INFO stats
```

初学阶段不需要记住 `INFO` 返回的所有字段。先关注：

- Redis 版本；
- 运行时间；
- 当前连接数；
- 命令处理数量；
- 内存使用情况。

### 4. 查看当前数据库编号

Redis 默认提供多个逻辑数据库，连接地址最后的 `/0` 表示默认使用编号为 `0` 的逻辑数据库。

在命令行中可以查看当前数据库中的 Key 数量：

```redis
DBSIZE
```

切换逻辑数据库：

```redis
SELECT 1
```

切换后执行 `DBSIZE`，看到的是数据库 `1` 中的 Key 数量。

初学阶段可以把逻辑数据库理解成同一个 Redis 服务中的不同命名空间，但不要把它当成 MySQL 中完整独立的数据库。真实项目更常通过 Key 前缀区分业务，例如：

```text
life:user:1001
life:session:abc
life:task:9001
```

不要在共享环境中随意执行：

```redis
FLUSHDB
```

它会删除当前逻辑数据库中的所有 Key。下面的命令会删除整个 Redis 实例中的所有逻辑数据库：

```redis
FLUSHALL
```

这两个命令都是破坏性操作，本课不要求执行。

---

## 六、第一次读写数据

### 1. SET 和 GET

Redis 最基础的操作是保存和读取一个字符串值：

```redis
SET greeting "hello redis"
GET greeting
```

结果：

```text
OK
"hello redis"
```

这里可以先建立一个简单模型：

```text
Key：greeting
Value：hello redis
```

Redis 的 Key 区分大小写：

```redis
SET user:name "Alice"
GET user:name
GET User:Name
```

第二个 `GET` 查找的是另一个 Key。

### 2. 判断 Key 是否存在

```redis
EXISTS greeting
```

返回 `1` 表示存在，返回 `0` 表示不存在。

查看 Key 的数据类型：

```redis
TYPE greeting
```

当前结果应该是：

```text
string
```

删除一个 Key：

```redis
DEL greeting
```

再次读取：

```redis
GET greeting
```

结果是：

```text
(nil)
```

`(nil)` 表示这个 Key 当前不存在，不是字符串 `"nil"`。

### 3. Key 命名

Redis 不要求 Key 必须使用某种格式，但业务代码需要建立自己的规则。常见方式是用冒号分隔命名空间：

```text
user:1001
user:1001:profile
session:abc123
article:42
```

命名时至少要考虑：

- 这个 Key 属于哪个业务；
- 它代表哪类对象；
- 是否包含用户或资源编号；
- 是否需要版本；
- 是否可能与其他模块冲突；
- 后续是否方便批量排查。

例如，不建议多个模块都使用含义不清的 Key：

```text
data
info
status
```

更清晰的方式是：

```text
life:user:1001:profile
life:agent:task:9001
life:rate-limit:user:1001
```

Key 设计会直接影响缓存失效、排查问题和多服务共用 Redis 的安全边界，后续课程会继续展开。

---

## 七、过期时间和数据生命周期

### 1. 为 Key 设置过期时间

Redis 可以让一个 Key 在指定时间后自动失效：

```redis
SET verification-code:1001 "572913"
EXPIRE verification-code:1001 300
```

这里的 `300` 是秒数，表示 300 秒后过期。

查看剩余时间：

```redis
TTL verification-code:1001
```

可能得到：

```text
(integer) 287
```

TTL 会随着时间减少。继续读取：

```redis
GET verification-code:1001
```

在过期后会得到：

```text
(nil)
```

### 2. 在写入时同时设置过期时间

更常见的写法是在 `SET` 时一起设置：

```redis
SET login:session:abc123 "user:1001" EX 3600
```

这表示写入值，并让它在 3600 秒后过期。

这样做比先 `SET` 再 `EXPIRE` 更不容易出现中间步骤失败导致 Key 没有过期时间的问题。后续学习缓存时，通常优先使用这种方式。

### 3. TTL 的特殊返回值

`TTL` 可能返回几种不同结果：

```text
正数：剩余秒数
-1：Key 存在，但没有设置过期时间
-2：Key 不存在
```

例如：

```redis
SET permanent-key "value"
TTL permanent-key
```

结果通常是：

```text
(integer) -1
```

这说明 Key 存在，但不会自动过期。

如果一个本来应该短期存在的 Key 返回 `-1`，就要检查写入代码是否忘记设置过期时间。临时状态没有过期时间，可能最终变成长期占用内存的数据。

### 4. 删除过期时间

可以使用 `PERSIST` 删除过期时间：

```redis
SET temporary-key "value" EX 60
PERSIST temporary-key
TTL temporary-key
```

删除过期时间后，TTL 通常会变成 `-1`。

本课只要求理解操作含义，不建议在业务代码中随意删除 Key 的过期时间。数据应该有明确的生命周期。

---

## 八、使用 Python 连接 Redis

### 1. 安装客户端库

Python 中常用的 Redis 客户端包名是 `redis`：

```bash
python -m pip install redis
```

如果项目使用虚拟环境，先激活项目对应的环境，再执行安装。确认安装成功：

```bash
python -c "import redis; print(redis.__version__)"
```

这里的 `redis` 包是 Python 客户端，不是 Redis Server 本身。安装 Python 包不会自动启动 Redis 服务。

### 2. 建立同步连接

创建一个最小脚本：

```python
import redis


client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
)

print(client.ping())
```

正常运行结果：

```text
True
```

配置含义：

```text
host：Redis Server 所在主机
port：Redis Server 监听的端口
db：使用的逻辑数据库编号
decode_responses：让返回的字符串直接解码为 Python str
```

如果不设置 `decode_responses=True`，有些字符串结果会以 `bytes` 返回：

```python
value = client.get("greeting")
print(value)
```

可能看到：

```text
b'hello redis'
```

设置后更适合入门：

```python
client.set("greeting", "hello redis")
print(client.get("greeting"))
```

结果：

```text
hello redis
```

### 3. Python 中完成读写和过期

```python
import redis


client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
)

client.set("course:greeting", "hello redis", ex=60)

print(client.exists("course:greeting"))
print(client.get("course:greeting"))
print(client.ttl("course:greeting"))

client.delete("course:greeting")
print(client.get("course:greeting"))
```

这里对应命令行中的：

```text
SET ... EX 60
EXISTS
GET
TTL
DEL
```

Python 客户端只是把程序中的方法调用转换成 Redis 能理解的命令。Redis 的数据模型和过期行为并不会因为使用 Python 而改变。

### 4. 连接检查和异常处理

实际应用中，连接 Redis 可能失败：

- Redis 服务没有启动；
- host 写错；
- port 写错；
- Docker 端口没有映射；
- 网络不可达；
- Redis 要求认证但客户端没有提供密码；
- 连接超时。

可以先写一个环境检查脚本：

```python
import redis
from redis.exceptions import RedisError


client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
    socket_connect_timeout=2,
)

try:
    client.ping()
except RedisError as error:
    print(f"Redis connection failed: {error}")
else:
    print("Redis is available")
```

`socket_connect_timeout` 只表示建立连接时最多等待多久。它不是所有 Redis 操作的完整超时策略，后续学习接口超时和分布式调用时还需要进一步配置。

不要在业务代码中捕获异常后什么都不做：

```python
try:
    client.get("key")
except Exception:
    pass
```

这样会把 Redis 不可用隐藏起来，最终表现为接口数据不完整或行为异常。至少应该记录错误，并根据业务决定返回错误、降级到数据库，还是暂时跳过缓存。

### 5. 连接池的初步认识

Python Redis 客户端通常会复用连接，而不是每次调用 `get` 或 `set` 都重新建立一个 TCP 连接。存放和分发这些连接的组件，就是连接池。

可以把连接池想象成一排固定的办公工位：

```text
应用进程
    -> Redis 客户端连接池（一排固定的工位）
        ├── 连接 1（工位 A）
        ├── 连接 2（工位 B）
        └── 连接 3（工位 C）
```

```text
连接 ≈ 工位：提前布置好——到 Redis 的 TCP 通道已建立、认证已完成，长期存在
请求 ≈ 员工：临时来办事，找一个空工位坐下，办完就走
```

一个请求访问 Redis 的过程是：

```text
请求到达
    -> 从连接池借一条空闲连接
    -> 在这条连接上发送命令、接收结果
    -> 把连接归还给连接池，留给下一个请求
```

借和还都由客户端自动完成，业务代码通常感知不到。

这里要澄清一个常见误解：以为请求会像队列一样排在连接池里，等池子有空位再把请求“放进去”。实际不是这样。连接池里放的是连接，不是请求：连接是长期住户，请求是流动的过客。请求从不进入连接池，它只是短暂借用一条连接。

只有当所有工位都被占满时，请求才会真正开始等待：要么排队等其他请求归还连接，要么等待超时后直接报错，具体行为取决于客户端的配置。

顺便理解为什么复用值得：新建一条连接并不便宜，要先完成 TCP 握手和认证才能发送第一条命令，相当于临时搭一个新工位。复用就是直接坐到已经布置好的工位上，跳过这些准备步骤。

初学阶段可以创建一个客户端实例并在应用中复用：

```python
import redis


redis_client = redis.Redis.from_url(
    "redis://127.0.0.1:6379/0",
    decode_responses=True,
)
```

不要在每个函数调用中反复创建新的客户端对象，也不要在每个请求中手动启动和关闭 Redis Server。服务的生命周期和业务请求的生命周期是两件事。

连接池的容量（`max_connections`）、池满后的等待与超时、健康检查和 FastAPI 生命周期，会在后续课程结合 Web 接口展开。

---

## 九、一个完整的入门练习

### 1. 准备 Redis 服务

如果使用 Docker：

```bash
docker run --name redis-course -p 6379:6379 -d redis:7
```

如果使用 Docker，先进入容器内的命令行：

```bash
docker exec -it redis-course redis-cli
```

（如果在 Windows 上单独安装了 redis-cli，也可以直接执行 `redis-cli -h 127.0.0.1 -p 6379`。）

### 2. 依次执行基础命令

```redis
PING

SET course:user:1001 "Alice" EX 300
GET course:user:1001
EXISTS course:user:1001
TYPE course:user:1001
TTL course:user:1001

DEL course:user:1001
GET course:user:1001
```

观察并记录：

```text
PING 返回什么？
SET 成功时返回什么？
GET 的值是什么？
TYPE 返回什么？
TTL 是否接近 300？
DEL 后 GET 返回什么？
```

### 3. 使用 Python 重复一次

创建 `redis_lesson01.py`：

```python
import redis


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=2,
    )

    print("Redis available:", client.ping())

    key = "course:lesson01:user:1001"
    client.set(key, "Alice", ex=60)

    print("Exists:", client.exists(key))
    print("Type:", client.type(key))
    print("Value:", client.get(key))
    print("TTL:", client.ttl(key))

    client.delete(key)
    print("After delete:", client.get(key))


if __name__ == "__main__":
    main()
```

运行：

```bash
python redis_lesson01.py
```

这个练习至少验证了：

- Python 能够连接 Redis；
- Redis 能够保存字符串值；
- Key 可以设置过期时间；
- Python 能够读取类型、值和 TTL；
- 删除后读取不到原来的 Key。

### 4. 增加一个自动过期观察

把过期时间改成 5 秒：

```python
client.set(key, "Alice", ex=5)
```

连续运行下面的代码，观察 TTL 变化：

```python
for _ in range(7):
    print(client.ttl(key), client.get(key))
```

如果希望看到时间自然变化，可以在循环中增加等待：

```python
import time


for _ in range(7):
    print(client.ttl(key), client.get(key))
    time.sleep(1)
```

这里要注意：过期时间到达后，Redis 不保证在某个精确的 CPU 时刻立刻删除 Key。对使用者来说，过期 Key 不应该再被正常读取；具体清理时机由 Redis 的过期处理机制决定。

---

## 十、常见错误

### 1. `Connection refused`

错误可能类似：

```text
Error 10061 connecting to 127.0.0.1:6379.
No connection could be made because the target machine actively refused it.
```

常见原因：

- Redis Server 没有启动；
- Docker 容器已经停止；
- 连接端口写错；
- 容器端口没有映射到本机；
- Redis 监听的不是 `127.0.0.1`。

排查顺序：

```text
确认 Redis Server 是否运行
    -> 确认监听端口
    -> 确认 Docker 端口映射
    -> 用 redis-cli 执行 PING
    -> 再检查 Python 配置
```

如果使用 Docker：

```bash
docker ps
docker logs redis-course
```

### 2. 把 Python 包安装当成启动 Redis

执行：

```bash
python -m pip install redis
```

只会安装 Python 客户端库，不会启动 Redis Server。两者分别是：

```text
Redis Server：真正保存和处理数据的服务
redis：Python 用来连接 Redis 的客户端包
```

### 3. 连接了错误的端口

例如容器这样启动：

```bash
docker run --name redis-course -p 6380:6379 -d redis:7
```

那么 Python 应该连接：

```python
redis.Redis(host="127.0.0.1", port=6380)
```

不是 `6379`。容器内部端口和本机暴露端口要分开看。

### 4. 以为 `GET` 返回的 `(nil)` 是字符串

下面的结果：

```redis
GET missing-key
```

```text
(nil)
```

表示 Key 不存在。Python 中通常对应 `None`：

```python
value = client.get("missing-key")
assert value is None
```

不要把它和字符串 `"nil"`、空字符串 `""` 或数字 `0` 混淆。业务代码需要根据不同情况决定如何处理。

### 5. 忘记设置过期时间

如果写入短期状态时只执行：

```redis
SET verification-code:1001 "572913"
```

那么它默认没有过期时间：

```redis
TTL verification-code:1001
```

结果通常是：

```text
(integer) -1
```

验证码、临时会话、缓存和任务锁通常都需要明确生命周期。写入时建议直接使用：

```redis
SET verification-code:1001 "572913" EX 300
```

### 6. 在共享 Redis 中执行 `FLUSHDB`

`FLUSHDB` 会清空当前逻辑数据库，可能删除其他程序正在使用的数据。`FLUSHALL` 影响范围更大。

练习时也不要只因为“当前是本地环境”就养成无确认清空的习惯。清理数据前应该：

```text
确认 Redis 实例
    -> 确认逻辑数据库
    -> 确认 Key 前缀
    -> 优先删除自己的练习 Key
```

### 7. 把 Redis 当成永不丢数据的数据库

Redis 的数据主要位于内存中，即使开启了 RDB 或 AOF，也要根据配置和故障类型考虑可能的数据丢失。缓存、临时状态和可以重建的数据比较适合放 Redis。

如果数据是用户订单、账单或其他不可重新计算的业务事实，不能只因为 Redis 访问速度快就把关系型数据库移除。数据的持久化、备份、事务和恢复要求必须先明确。

### 8. 每次操作都创建新的客户端

下面这种写法不适合作为长期的服务代码：

```python
def get_value(key: str):
    client = redis.Redis(host="127.0.0.1", port=6379)
    return client.get(key)
```

它会让客户端和连接池的生命周期难以管理。应用通常应该创建一个可复用的客户端，在应用启动时初始化，在应用关闭时按框架生命周期处理资源。

---

## 十一、面试回答模板

### 题目：Redis 是什么？

> Redis 是一个独立运行的内存数据服务，使用 Key 和多种数据结构保存数据，并通过网络协议向客户端提供读写能力。它常用于缓存、会话、计数、限流、排行榜和异步任务状态，也支持设置过期时间以及可选的持久化。它不是所有业务数据的替代品，长期业务事实通常仍然由关系型数据库保存。

### 题目：Redis 和 MySQL 有什么区别？

> MySQL 是关系型数据库，核心是表、SQL、事务、约束和复杂查询，适合保存结构化的长期业务数据。Redis 核心是 Key 和多种内存数据结构，访问速度快，适合缓存、短期状态、计数和任务控制。实际应用中通常让 MySQL 保存事实数据，让 Redis 作为访问加速和状态管理组件，两者不是简单的替代关系。

### 题目：Redis 为什么快？

> Redis 的数据主要在内存中，避免了每次访问都从磁盘读取；它使用简单高效的数据结构和事件驱动的网络处理模型，常见的单 Key 操作开销较低。不过网络延迟、数据结构选择、Key 大小、命令复杂度和实例负载仍然会影响实际性能，不能只用“内存数据库”解释所有性能问题。

### 题目：Redis 的数据会不会丢？

> Redis 的数据主要在内存中，是否丢失取决于数据是否设置过期、是否开启 RDB 或 AOF、持久化配置、故障类型以及恢复策略。缓存和可重建数据可以接受一定程度的数据丢失，但订单、账单等长期业务事实不能只依赖 Redis。选择 Redis 存储数据前，要先明确数据的持久化和恢复要求。

### 题目：TTL 返回 `-1` 和 `-2` 分别是什么意思？

> `-1` 表示 Key 存在但没有设置过期时间，`-2` 表示 Key 不存在。排查临时状态或缓存没有按预期过期时，可以先通过 `TTL` 区分这两种情况。

### 题目：为什么要使用连接池？

> Redis 是网络服务，频繁建立和关闭 TCP 连接会产生握手、认证等额外开销。连接池预先保留一批可复用的连接：请求需要访问 Redis 时先从池中借出一条连接，用完归还，而不是每次都重新建立连接；池的容量同时也限制了应用同时占用的连接数。它不是越大越好，容量需要结合请求并发、Redis 处理能力和应用实例数量设置。

---

## 十二、这一课学到什么程度可以继续

达到下面的程度，就可以进入下一课：

```text
能说清 Redis Server 和 Python 客户端的区别
能解释 Redis 与 SQLite、MySQL 的职责差异
能启动本地 Redis 服务，并通过 docker exec 或本机 redis-cli 执行 PING
能拆解一个 Redis 连接地址
能使用 SET、GET、EXISTS、TYPE 和 DEL
能使用 EXPIRE、TTL 和 SET EX 设置数据生命周期
能用 Python redis 客户端完成连接和读写
能区分 Key 不存在、空字符串和没有过期时间
能排查连接拒绝、端口错误和客户端未安装
知道不应在共享环境中随意执行 FLUSHDB 或 FLUSHALL
```

下一课将继续学习 Redis 的常见数据结构，重点回答：

```text
String、Hash、List、Set 和 Sorted Set 分别适合什么场景？
为什么 Redis 的数据结构不是关系型表？
如何使用 Hash 保存对象？
如何使用 List 表示队列？
什么时候应该使用 Set 或 Sorted Set？
```
