# 第5课:Redis Key 设计、过期时间与连接池

> 这一课学习 Redis 数据的生命周期和访问入口。
>
> 目标是能够设计清晰的 Key，给临时数据设置合理的过期时间，并理解 Python 客户端为什么需要复用连接。

## 一、这一课要解决什么问题

Redis 中的数据最终都要通过 Key 找到：

```text
Key 设计混乱
    -> 不知道数据属于哪个模块
    -> 容易覆盖其他数据
    -> 出问题时难以排查
```

Redis 中的临时数据还需要明确生命周期：

```text
写入缓存或会话
    -> 设置过期时间
    -> 到期后不再正常读取
```

本课回答四个问题：

1. Redis Key 应该怎样命名？
2. 哪些数据应该设置过期时间？
3. `TTL` 的返回值如何理解？
4. 应用为什么要复用 Redis 客户端和连接池？

---

## 二、Key 命名

### 1. Key 是数据的地址

Redis 不通过表名和列名查找数据，而是通过 Key：

```redis
SET user:1001:name "Alice"
GET user:1001:name
```

可以把 Key 看成数据的地址：

```text
user:1001:name
├── user：业务对象
├── 1001：对象编号
└── name：字段或用途
```

Redis 不强制 Key 使用某种格式，但项目应该统一约定。常见的命名方式是用冒号分隔不同层级：

```text
app:user:1001:profile
app:session:abc123
app:article:42:detail
app:task:9001:status
```

### 2. Key 命名需要表达什么

一个好的 Key 通常能够看出：

- 属于哪个应用或业务；
- 保存哪类对象；
- 对应哪个用户或资源；
- 保存的是什么用途；
- 是否需要版本或环境区分。

例如：

```text
life:user:1001:profile
life:agent:task:9001:status
life:cache:article:42
```

不建议使用含义不清的公共 Key：

```text
data
info
status
temp
```

不同模块使用这些 Key 时很容易互相覆盖。

### 3. Key 中是否放环境

如果开发、测试和生产共用同一个 Redis 实例，建议在 Key 中区分环境：

```text
life:dev:user:1001:profile
life:test:user:1001:profile
life:prod:user:1001:profile
```

更常见的做法是让不同环境使用不同 Redis 实例或逻辑数据库，但环境前缀仍然可以作为额外保护。

真实项目中需要先确认已有约定，不要随意给现有 Key 改名。Key 名称的变化会影响读取、删除、监控和数据迁移。

---

## 三、过期时间

### 1. 临时数据应该自动失效

缓存、验证码和短期任务状态通常不应该永久保存：

```redis
SET verification-code:1001 "572913" EX 300
```

这条命令表示：

```text
保存验证码
有效期 300 秒
到期后 Redis 不再返回这个 Key
```

其他常见的临时数据包括：

- 查询缓存；
- 登录会话；
- 密码重置令牌；
- 限流计数；
- 幂等请求记录；
- Agent 临时执行状态。

过期时间不是“清理工作”的替代品。业务仍然需要考虑数据量、内存和长期存储。

### 2. 查看 TTL

```redis
SET course:temporary "hello" EX 60
TTL course:temporary
```

`TTL` 返回值的含义：

```text
正数：剩余秒数
-1：Key 存在，但没有过期时间
-2：Key 不存在
```

例如：

```redis
SET course:permanent "hello"
TTL course:permanent
```

结果通常是：

```text
(integer) -1
```

如果一个本来应该短期存在的 Key 返回 `-1`，通常说明写入代码忘记设置过期时间。

### 3. 设置、修改和删除过期时间

写入时设置过期时间：

```redis
SET session:abc "user:1001" EX 3600
```

单独设置过期时间：

```redis
EXPIRE session:abc 3600
```

修改过期时间：

```redis
EXPIRE session:abc 7200
```

删除过期时间：

```redis
PERSIST session:abc
```

一般更推荐在写入时直接设置过期时间：

```redis
SET cache:article:42 "..." EX 300
```

这样可以避免 `SET` 成功后、`EXPIRE` 执行前程序中断，导致数据意外变成永久 Key。

### 4. 过期时间应该设置多久

没有适用于所有业务的固定值，需要结合数据变化频率和可接受的陈旧程度：

```text
验证码：几分钟
文章详情缓存：几分钟到几十分钟
登录会话：几十分钟到几小时
短期 Agent 状态：根据任务最长执行时间
```

过期时间太短，会导致频繁未命中和重复查询；过期时间太长，数据可能过时或占用更多内存。缓存课程会继续讨论如何选择和更新过期时间。

### 5. Key 过期不代表精确到点删除

业务上可以把过期理解为“过期后不可正常使用”，但不要把它理解为 Redis 在某个精确时刻立刻完成物理删除。

Redis 会通过过期检查机制清理数据。对应用来说，重要的是：

- 不应该继续使用已经过期的业务数据；
- 不应该依赖过期删除动作触发核心业务；
- 需要定期执行的任务不能只依赖 TTL。

---

## 四、Python 中使用连接池

### 1. 为什么不应该每次请求都新建客户端

Redis 是一个网络服务。每次请求都新建连接，流程会变成：

```text
HTTP 请求到达
    -> 创建 Redis 客户端
    -> 建立 TCP 连接
    -> 执行命令
    -> 关闭连接
```

请求量增加后，连接建立和关闭本身会产生额外开销，也可能快速消耗 Redis 的连接数。

更常见的方式是复用一个客户端：

```text
应用进程
    -> Redis 客户端
        -> 连接池
            -> Redis 连接
```

客户端从连接池中获取连接，命令执行完成后归还连接。

### 2. 使用 `redis.Redis` 创建客户端

`redis.Redis(...)` 是创建客户端对象的构造函数，参数说明连接的是哪台 Redis：

```python
import redis


client = redis.Redis(
    host="127.0.0.1",        # Redis Server 的主机
    port=6379,               # Redis Server 的端口
    db=0,                    # 逻辑数据库编号
    decode_responses=True,   # 返回的字符串直接解码成 Python str
)
```

`redis.Redis` 内部会使用连接池。创建对象时不会立刻建立连接，真正建立连接发生在第一次执行命令时，连接从池中取出。

应用通常创建一个可复用的客户端，而不是在每个函数中重新创建。`from_url` 是 `redis.Redis` 的类方法，不需要先创建实例就能调用，它把 `redis://主机:端口/数据库编号` 形式的地址解析成连接参数：

```python
redis_client = redis.Redis.from_url(
    "redis://127.0.0.1:6379/0",   # redis://主机:端口/数据库编号
    decode_responses=True,
)
```

直接传参数和传 URL 两种写法等价，按团队习惯选择一种即可。

### 3. 显式配置连接池

`ConnectionPool` 是专门负责存放和管理连接的类。上一节直接用 `redis.Redis(...)` 时，客户端内部已经自动创建了一个默认连接池；需要限制连接数量时，可以显式创建连接池并交给客户端：

```python
import redis


pool = redis.ConnectionPool.from_url(      # 创建一个连接池对象
    "redis://127.0.0.1:6379/0",
    max_connections=10,                    # 池中最多同时存在 10 条连接
    decode_responses=True,
)
client = redis.Redis(connection_pool=pool) # 把连接池交给客户端使用
```

`max_connections=10` 表示这个客户端最多使用 10 个连接。超过上限后的行为取决于客户端实现：默认可能直接报错，也可以配置成排队等待，具体在后续 Web 课程中展开。

连接池大小不是越大越好：

- 太小，业务请求可能等待或失败；
- 太大，Redis 和应用都需要管理更多连接；
- 应用实例增加后，总连接数也会增加。

连接池大小要结合应用实例数、请求并发和 Redis 处理能力设置。

### 4. 连接超时

连接 Redis 时应该设置合理的超时时间：

```python
client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    socket_connect_timeout=2,   # 建立连接最多等待 2 秒
    socket_timeout=2,           # 单次 Redis 操作最多等待 2 秒
    decode_responses=True,
)
```

这里先区分两个概念：

```text
socket_connect_timeout：建立连接最多等待多久
socket_timeout：一次 Redis 操作最多等待多久
```

超时不是越短越好。太短可能把正常的短暂延迟误判为失败，太长又会让 HTTP 请求长时间卡住。实际值需要结合接口的超时预算。

---

## 五、Python 示例

本课代码放在：

```text
code/redis/05-key-expiry-pool.py
```

示例会演示 Key 前缀、TTL 和连接池：

```python
import redis


def main() -> None:
    prefix = "course:lesson03:"            # 统一的 Key 前缀，便于识别和清理

    pool = redis.ConnectionPool.from_url(  # 创建连接池，最多 5 条连接
        "redis://127.0.0.1:6379/0",
        max_connections=5,
        decode_responses=True,
    )
    client = redis.Redis(                  # 创建客户端，使用上面的连接池
        connection_pool=pool,
        socket_connect_timeout=2,
        socket_timeout=2,
    )

    permanent_key = prefix + "permanent"   # 用前缀拼接出完整 Key
    temporary_key = prefix + "temporary"

    client.set(permanent_key, "no expiry")           # 写入，不设置过期时间
    client.set(temporary_key, "expires soon", ex=30) # 写入，30 秒后过期

    print("Permanent TTL:", client.ttl(permanent_key))   # ttl() 返回剩余秒数
    print("Temporary TTL:", client.ttl(temporary_key))
    print("Temporary value:", client.get(temporary_key))

    client.delete(permanent_key, temporary_key)          # 一次删除多个 Key


if __name__ == "__main__":
    main()
```

本课用到的客户端方法：

| 方法 | 含义 | 参数说明 |
|---|---|---|
| `client.set(key, value, ex=秒数)` | 写入字符串值 | 传 `ex` 时同时设置过期时间 |
| `client.get(key)` | 读取值 | Key 不存在时返回 `None` |
| `client.ttl(key)` | 返回剩余秒数 | 对应命令行的 `TTL` |
| `client.delete(key, ...)` | 删除一个或多个 Key | 可以传多个 Key |

运行：

```bash
python -m pip install redis
python code/redis/05-key-expiry-pool.py
```

代码中的永久 Key 只是为了观察 `TTL=-1` 的情况，实际业务中不要给临时数据省略过期时间。

---

## 六、常见错误

### 1. Key 没有业务前缀

```redis
SET status "running"
```

这种 Key 很容易和其他模块冲突。建议至少包含业务和对象：

```redis
SET life:agent:task:9001:status "running"
```

### 2. 先 `SET`，忘记 `EXPIRE`

```python
client.set("session:abc", "user:1001")
```

如果会话应该自动过期，这段代码是不完整的：

```python
client.set("session:abc", "user:1001", ex=3600)
```

### 3. 把 `TTL=-1` 当成异常

`-1` 表示 Key 存在但没有过期时间，不代表 Redis 连接失败。应该先确认这个 Key 是否本来就设计为永久存在。

### 4. 以为连接池越大越好

连接池过大可能让所有应用实例一起占满 Redis 连接。连接池要看总实例数量：

```text
总连接数 ≈ 应用实例数 × 每个实例的连接池上限
```

### 5. 在函数中频繁创建客户端

```python
def read_value(key: str):
    client = redis.Redis(...)   # 错误示例：每次调用都新建客户端，连接池无法复用
    return client.get(key)
```

应用通常应该在进程或应用生命周期内复用客户端。具体初始化和关闭时机，可以在 FastAPI 的生命周期中统一管理。

---

## 七、面试回答模板

### 题目：Redis Key 应该如何设计？

> 通常使用统一的业务前缀和冒号分隔层级，例如 `app:user:1001:profile`。Key 应该表达业务、对象、编号和用途，避免使用 `data`、`info` 这类容易冲突的名字。多环境或多模块共用实例时，还要考虑环境和命名空间隔离。

### 题目：为什么缓存要设置过期时间？

> 过期时间可以限制数据生命周期，避免缓存、会话、验证码和临时任务状态永久占用内存，也能让旧数据最终失效。具体时间要结合数据更新频率、允许的陈旧时间和重建成本决定。

### 题目：`TTL` 返回 `-1` 和 `-2` 分别是什么意思？

> `-1` 表示 Key 存在但没有设置过期时间，`-2` 表示 Key 不存在。排查临时数据没有过期时，先确认是忘记设置 TTL，还是 Key 已经不存在。

### 题目：Redis 连接池解决什么问题？

> Redis 是网络服务，连接池可以复用已经建立的连接，减少每个请求重复建立 TCP 连接的开销，同时限制应用的并发连接数。连接池不是越大越好，需要结合应用实例数量、请求并发和 Redis 的承载能力设置。

---

## 八、这一课学到什么程度可以继续

达到下面的程度，就可以进入下一课：

```text
能为 Redis Key 设计统一的业务前缀
能解释对象、用户、任务和环境信息如何放入 Key
能使用 EXPIRE、TTL、SET EX 和 PERSIST
能区分 TTL 的正数、-1 和 -2
能为临时数据选择合理的生命周期
能解释为什么应用需要复用 Redis 客户端
能说出 redis.Redis、redis.Redis.from_url 和 ConnectionPool 各自的作用
能说明连接池大小与应用实例数量的关系
能设置基础的连接和操作超时
能运行 code/redis/05-key-expiry-pool.py
```

下一课将学习 Cache Aside，重点回答：

```text
为什么查询要先查缓存？
缓存未命中时如何查询数据库并回填？
数据库更新后什么时候删除缓存？
```
