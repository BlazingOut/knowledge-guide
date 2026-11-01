# 第2课:Redis 常见数据结构

> 这一课只学习 Redis 最常用的五种数据结构。
>
> 目标不是背完所有命令，而是看到一个业务需求时，能够先判断应该使用哪种结构。

## 一、这一课要解决什么问题

Redis 不只保存一段字符串。除了 String，它还提供 Hash、List、Set 和 Sorted Set：

```text
String       一个值
Hash         一组字段和值
List         有顺序的元素集合
Set          不重复的元素集合
Sorted Set   带分数、可排序的元素集合
```

本课回答三个问题：

1. 五种数据结构分别保存什么样的数据？
2. 每种结构最常见的使用场景是什么？
3. 为什么不能把 Redis 数据结构直接当成 MySQL 表？

和 MySQL 先建表、再写数据不同，Redis 的结构不需要预先定义：向一个不存在的 Key 写入时，Redis 会自动创建对应类型。这个特点后面会反复用到。

这个机制也带来了一个代价：**Redis 不会校验 Key 名**。写错 Key 名不会被发现——写入会悄悄创建一个新 Key，读取会得到 nil。MySQL 写错表名会直接报错，Redis 不会。所以 Key 的命名规范要靠应用自己保证，这是后面课程反复强调 Key 前缀的原因，实际项目还会把 Key 名集中定义成常量，避免手写拼错。

前置内容：已经能够启动 Redis，并使用 Python 客户端完成 `PING`、`SET` 和 `GET`。

本课命令示例中，`#` 后面的文字是注释，用来解释这一行命令的含义和参数。在 redis-cli 中练习时，只需要输入命令本身。

---

## 二、String：保存一个值

String 是最简单、最常见的数据类型。它可以保存文本、数字或序列化后的 JSON：

```redis
SET user:1001:name "Alice"   # 写入一个字符串值
GET user:1001:name           # 读取这个 Key 的值
```

常见用途：

- 缓存一个查询结果；
- 保存短期标记；
- 保存计数器；
- 保存序列化后的简单对象。

数字字符串可以使用自增命令。`INCR` 是 increment（自增）的缩写，`INCRBY` 是 increment by（按指定数值自增）的缩写：

```redis
SET article:42:views 0        # 写入计数器初始值
INCR article:42:views         # 数值自增 1：浏览量变成 1
INCRBY article:42:views 5     # 一次自增指定数值：浏览量变成 6
GET article:42:views          # 读取当前计数
```

这里的值在 Redis 中仍然是 String，只是 Redis 为它提供了数字运算命令。

| 命令 | 含义 | 参数说明 |
|---|---|---|
| `SET key value` | 写入字符串值 | 可以加 `EX 秒数` 同时设置过期时间 |
| `GET key` | 读取值 | Key 不存在时返回 nil |
| `INCR key` | 数值自增 1 | 值必须是整数形式的字符串，否则报错 |
| `INCRBY key increment` | 数值增加指定数值 | `increment` 可以为负数 |

另外，`INCR` 是原子操作：自增在 Redis 内部一次完成，多个请求同时执行也不会互相覆盖。如果用“先 GET、加 1、再 SET”三步实现计数，并发时会丢失更新。计数器应该使用 `INCR` 系列命令，而不是在应用里手动加减。

适合使用 String 的问题通常是：

```text
我只需要根据一个 Key 取回一个整体的值
```

如果经常只修改对象中的一个字段，就不一定适合把整个对象序列化成一个 String。此时可以考虑 Hash。

---

## 三、Hash：保存对象的多个字段

Hash 可以保存一个对象的多个字段：

```redis
HSET user:1001 name "Alice" city "Beijing" level "3"   # 一次设置多个字段和值
HGET user:1001 name                                    # 读取一个字段
HGETALL user:1001                                      # 读取所有字段和值
```

可以把它理解成：

```text
Key：user:1001
    name  -> Alice
    city  -> Beijing
    level -> 3
```

常见命令：

| 命令 | 含义 | 参数说明 |
|---|---|---|
| `HSET key field value` | 设置字段的值 | `field value` 可以写多对，一次设置多个字段 |
| `HGET key field` | 读取一个字段的值 | 字段不存在时返回 nil |
| `HMGET key field` | 一次读取多个字段 | 可以传多个字段名 |
| `HGETALL key` | 读取所有字段和值 | 字段很多时返回结果较大，慎用 |
| `HEXISTS key field` | 判断字段是否存在 | 返回 1（存在）或 0（不存在） |
| `HDEL key field` | 删除字段 | 可以一次删除多个字段 |

Hash 适合保存对象的短期状态，例如：

```text
agent:task:9001
    status      -> running
    retry_count -> 1
    worker      -> worker-a
```

Hash 不是关系型表。它没有 MySQL 表中的主键约束、外键和 SQL 查询能力。字段之间的业务规则仍然需要由应用或其他数据库保证。

---

## 四、List：保存有顺序的元素

List 是有顺序的字符串集合，可以从左侧或右侧插入和取出：

```redis
LPUSH task:list "task-1"    # 从左侧（头部）插入元素
RPUSH task:list "task-2"    # 从右侧（尾部）插入元素
LRANGE task:list 0 -1       # 按索引范围读取元素：0 到 -1 表示全部
```

结果类似：

```text
task-1
task-2
```

你可能注意到，这里没有"先创建列表"的步骤。Redis 的列表不需要预先定义：`LPUSH` 或 `RPUSH` 时如果 Key 不存在，会自动创建一个空列表再插入；如果 Key 已经存在但不是列表类型，会返回 `WRONGTYPE` 错误。同样，列表元素被全部弹出后，这个 Key 会自动消失。

常见命令：

| 命令 | 含义 | 参数说明 |
|---|---|---|
| `LPUSH key value` | 从左侧（头部）插入元素 | 可以一次插入多个 |
| `RPUSH key value` | 从右侧（尾部）插入元素 | 可以一次插入多个 |
| `LPOP key` | 从左侧取出一个元素 | 取出即删除，并返回该元素 |
| `RPOP key` | 从右侧取出一个元素 | 取出即删除，并返回该元素 |
| `LLEN key` | 返回列表长度 | — |
| `LRANGE key start stop` | 按索引范围读取元素 | 索引从 0 开始，`-1` 表示最后一个元素 |

List 常见用途：

- 简单任务队列；
- 最近访问记录；
- 有顺序的短期消息。

需要注意，List 只表示一组有顺序的元素。它本身不自动解决：

- 消息是否已经处理；
- 消费失败后如何重试；
- 多个消费者如何协调；
- 消息是否重复。

这些问题会在异步任务课程中继续学习。

---

## 五、Set：保存不重复的元素

Set 中的元素不重复，并且不强调顺序：

```redis
SADD user:1001:tags "python"   # 添加成员
SADD user:1001:tags "redis"
SADD user:1001:tags "python"   # 重复添加会被忽略，不会产生第二个 "python"
SMEMBERS user:1001:tags        # 返回全部成员
```

常见命令：

| 命令 | 含义 | 参数说明 |
|---|---|---|
| `SADD key member` | 添加成员 | 可以一次添加多个，重复成员被忽略 |
| `SISMEMBER key member` | 判断成员是否存在 | 返回 1（是成员）或 0（不是） |
| `SMEMBERS key` | 返回全部成员 | 顺序不保证 |
| `SREM key member` | 删除成员 | 可以一次删除多个 |
| `SCARD key` | 返回成员数量 | — |
| `SINTER key1 key2` | 求多个集合的交集 | 可以传两个以上的 Key |

Set 适合：

- 标签；
- 去重后的 ID 集合；
- 判断某个成员是否属于一组；
- 简单的交集、并集和差集。

例如，找出同时属于两个集合的用户：

```redis
SINTER group:python group:redis   # 返回同时在两个集合中的成员
```

如果业务要求“按时间排序”或“按分数排序”，Set 就不够用了，可以考虑 Sorted Set。

---

## 六、Sorted Set：带分数的有序集合

Sorted Set 中每个元素都有一个分数，Redis 根据分数提供排序结果：

```redis
ZADD leaderboard 98 "user:1001"      # 添加成员，并给它设置分数
ZADD leaderboard 85 "user:1002"
ZADD leaderboard 91 "user:1003"
ZRANGE leaderboard 0 -1 WITHSCORES   # 按分数从低到高返回全部成员，WITHSCORES 表示连分数一起返回
```

常见用途：

- 排行榜；
- 按时间排序的任务；
- 优先级队列；
- 延迟任务的到期时间。

常见命令：

| 命令 | 含义 | 参数说明 |
|---|---|---|
| `ZADD key score member` | 添加成员并设置分数 | 分数是排序依据，重复添加会更新分数 |
| `ZINCRBY key increment member` | 给成员的分数加上增量 | `increment` 可以为负数 |
| `ZRANK key member` | 查询升序排名（分数从低到高） | 排名从 0 开始 |
| `ZREVRANK key member` | 查询降序排名（分数从高到低） | 排名从 0 开始 |
| `ZREVRANGE key start stop` | 按分数从高到低返回成员 | 加 `WITHSCORES` 连分数一起返回 |
| `ZREM key member` | 删除成员 | 可以一次删除多个 |

`ZRANGE` 默认按分数从低到高排列，`ZREVRANGE` 按分数从高到低排列。

Sorted Set 的分数是排序依据，不一定代表业务中的“分数”。例如可以使用 Unix 时间戳作为分数：

```redis
ZADD tasks:scheduled 1792300800 "task:9001"   # 用到期时间戳作为分数
```

这样可以取出最早到期的任务。具体如何实现可靠的延迟任务，还需要处理并发、重复消费和失败重试，不能只靠 `ZADD` 完成。

---

## 七、如何选择数据结构

可以先用下面的问题判断：

```text
只需要保存一个整体的值？
    -> String

需要保存一个对象的多个字段？
    -> Hash

需要按插入顺序保存元素？
    -> List

需要去重和判断成员是否存在？
    -> Set

需要按照分数或时间排序？
    -> Sorted Set
```

简单对比：

| 数据结构 | 主要特点 | 常见场景 |
|---|---|---|
| String | 一个整体的值 | 缓存、标记、计数器 |
| Hash | 多个字段和值 | 用户状态、任务状态 |
| List | 有顺序、可从两端操作 | 简单队列、最近记录 |
| Set | 元素不重复 | 标签、成员集合、去重 |
| Sorted Set | 元素带分数并可排序 | 排行榜、定时任务 |

选择结构时，不要只看“哪种命令更快”，还要看：

- 数据如何读取；
- 数据是否需要去重；
- 是否需要排序；
- 是否需要单独修改字段；
- 是否需要设置过期时间；
- 后续是否需要删除或批量更新。

---

## 八、Python 示例

本课代码放在：

```text
code/redis/02-data-structures.py
```

示例会使用一个统一的 Key 前缀，运行结束后删除练习数据：

```python
import redis


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )

    prefix = "course:lesson02:"

    client.set(prefix + "message", "hello")
    print("String:", client.get(prefix + "message"))

    client.hset(
        prefix + "user:1001",
        mapping={"name": "Alice", "level": "3"},
    )
    print("Hash:", client.hgetall(prefix + "user:1001"))

    client.rpush(prefix + "tasks", "task-1", "task-2")
    print("List:", client.lrange(prefix + "tasks", 0, -1))

    client.sadd(prefix + "tags", "python", "redis", "python")
    print("Set:", sorted(client.smembers(prefix + "tags")))

    client.zadd(
        prefix + "leaderboard",
        {"user:1001": 98, "user:1002": 85},
    )
    print(
        "Sorted Set:",
        client.zrevrange(prefix + "leaderboard", 0, -1, withscores=True),
    )

    for key in client.scan_iter(match=prefix + "*"):
        client.delete(key)


if __name__ == "__main__":
    main()
```

运行前确认 Redis 已启动，并安装 Python 客户端：

```bash
python -m pip install redis
python code/redis/02-data-structures.py
```

代码只演示数据结构的基本读写，不包含缓存失效、任务确认和并发控制。

---

## 九、常见错误

### 1. 把 Hash 当成 Python 字典直接存入

Redis 不会自动理解 Python 字典。可以使用 Hash：

```python
client.hset("user:1001", mapping={"name": "Alice", "level": "3"})
```

也可以把字典序列化后保存成 String，但读取时需要自己反序列化：

```text
Hash：可以单独读取和修改字段
String JSON：整体读取和写入
```

根据访问方式选择，不要混用后又忘记数据格式。

### 2. 以为 List 自动就是可靠消息队列

List 能保存有顺序的元素，但不会自动记录“哪个消费者已经成功处理”。如果消费者取出任务后崩溃，任务可能丢失。可靠的消息处理还需要确认、重试和幂等设计。

### 3. 以为 Set 有固定顺序

Set 只保证成员不重复，不应该依赖 `SMEMBERS` 返回的顺序。如果业务需要顺序，请使用 List 或 Sorted Set。

### 4. 把 Sorted Set 的分数当成完整业务字段

Sorted Set 只有一个用于排序的 score。若一个排行榜还需要昵称、头像等信息，通常需要另外保存对象数据，或让 Sorted Set 只保存排序关系。

### 5. 练习 Key 没有清理

本课代码使用 `course:lesson02:` 前缀，并在结束时删除练习 Key。真实项目也应该设计清晰的命名空间，避免不同模块互相覆盖数据。

---

## 十、面试回答模板

### 题目：Redis 常见数据结构有哪些？

> 常见的有 String、Hash、List、Set 和 Sorted Set。String 适合缓存和计数，Hash 适合保存对象的多个字段，List 适合有顺序的数据和简单队列，Set 适合去重和成员判断，Sorted Set 适合排行榜、按分数或时间排序的场景。

### 题目：String 和 Hash 怎么选择？

> 如果对象通常整体读取和整体覆盖，可以序列化后使用 String；如果需要频繁单独读取或修改对象中的字段，可以使用 Hash。选择时要结合访问方式、数据格式和过期策略，而不是只看存储形式。

### 题目：List 能不能实现消息队列？

> List 可以实现简单的生产者和消费者队列，但它本身不完整解决消息确认、失败重试、重复消费和死信问题。对可靠性要求更高的任务，需要使用更合适的消息模型，并在业务层保证幂等。

---

## 十一、这一课学到什么程度可以继续

达到下面的程度，就可以进入下一课：

```text
能说出 String、Hash、List、Set 和 Sorted Set 的特点
能说出每种结构常见命令的含义和参数
能根据“整体值、对象字段、顺序、去重、排序”选择结构
能使用 Hash 保存和读取对象字段
能使用 List 保存有顺序的元素
能使用 Set 完成去重和成员判断
能使用 Sorted Set 保存分数并查询排名
知道 List 不自动提供可靠消息处理
知道 Set 不保证顺序
能运行 code/redis/02-data-structures.py 并清理练习数据
```

下一课将学习 Redis 的原理，重点回答：

```text
Redis 为什么快？
单线程为什么能处理那么多请求？
List、Set、Sorted Set 的底层分别是怎么实现的？
底层结构对使用选择有什么影响？
```
