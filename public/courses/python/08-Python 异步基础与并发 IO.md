# 第8课:Python 异步基础与并发 IO

## 1. 本课目标

完成本课后，你应当能够：

- 区分同步、异步、并发和并行；
- 解释阻塞操作为什么会拖慢同一个事件循环中的其他任务；
- 读写包含 `async def`、`await` 和 `asyncio.run()` 的 Python 代码；
- 使用 `asyncio.create_task()` 和 `asyncio.gather()` 并发等待多个 I/O 操作；
- 处理异步任务的异常、超时、取消和资源清理；
- 理解 Python 协程、后台任务和消息队列不是同一个概念。

本课是进入 FastAPI 异步接口、模型调用和 Redis 异步任务之前的基础课。重点是建立运行模型，不是学习完整的并发编程或操作系统 I/O 实现。

## 2. 为什么需要异步

先看一个同步程序：

```python
import time


def fetch(name: str, delay: float) -> str:
    print(f"{name} started")
    time.sleep(delay)
    print(f"{name} finished")
    return name


start = time.perf_counter()
fetch("A", 2)
fetch("B", 1)
elapsed = time.perf_counter() - start

print(f"elapsed: {elapsed:.1f}s")
```

程序会先等待 A 完成，再开始 B。总耗时大约是 3 秒。

这里的 `time.sleep()` 模拟网络请求、模型调用或文件操作中的等待。真实程序等待的可能是：

- HTTP 服务返回响应；
- 数据库查询完成；
- 模型服务生成结果；
- 文件读写完成。

如果程序在等待期间没有其他工作可做，同步代码比较直接。但当一个服务同时处理许多 I/O 请求时，让一个任务独占执行权并等待，可能会浪费处理能力。

异步编程的核心思想是：

> 当前任务等待 I/O 时，主动把执行权交给其他可以继续运行的任务。

## 3. 同步、异步、并发和并行

这几个词需要分开理解。

### 3.1 同步

同步代码按照调用顺序执行。调用方需要等待当前操作完成后，才能继续下一步。

```text
开始任务 A -> 等待 A -> 完成 A
             开始任务 B -> 等待 B -> 完成 B
```

### 3.2 异步

异步代码允许任务在等待 I/O 时暂停，把执行机会交给其他任务。

异步并不表示操作一定更快，而是减少等待期间的空转。

很多人第一次学异步时会卡在一个问题：**“协程都暂停了，它等待的那个操作为什么还能完成？”** 答案在于，发起等待和完成操作是两件不同的事。

一个异步协程调用 `await asyncio.sleep(1)` 时，它实际上只是**向操作系统内核提交了一个请求**：“请帮我等待 1 秒”。提交之后，这个协程就暂停了，不再执行任何代码。后面的事，由内核负责：

```text
协程:  提交"请等待 1 秒"的请求 -> 暂停（此时协程什么都不做）
内核:  继续计时，1 秒后把这个操作标记为"已完成"
事件循环:  发现操作完成了，才去恢复那个协程
```

所以“操作完成”发生在**内核里**，而不是**协程本身**里被做出来的。协程暂停的这段时间，它只是干等着；真正在推进的是内核。一旦内核把结果准备好了，事件循环再让协程从 `await` 的下一行继续，这时协程读到的只是内核已经准备好的结果——一次读回而已。

这就是为什么“暂停”不等于“失败”，也为什么协程可以安心地把控制权交出去：**它知道完成这件事的并不是自己，而是内核**。`time.sleep()` 之所以会阻塞事件循环，正是因为普通函数被 `time.sleep()` 卡住时，它没有先向内核提交一个“由内核去等”的请求，而是自己占着执行权什么都不做地等——这背后意味着内核没有任何可以独立推进的等待任务，事件循环无事可做。

### 3.3 并发

并发表示多个任务在同一段时间内交替推进。单线程事件循环也可以实现并发：

```text
任务 A: 开始 -> 等待网络 ---------> 继续
任务 B:        开始 -> 等待网络 -> 继续
```

依然要强调：图中 A 在 `等待网络` 的那段横线上暂停时，**不是 A 自己在完成网络等待，而是内核在替它完成**。A 只是把请求交给内核后让出了执行权，B 才能在 `开始 -> 等待网络` 之间插入运行。当内核把 A 的网络结果准备好后，事件循环再把 A 从暂停处叫醒。所以“交替推进”的前提，是每个任务暂停期间都有人（内核）在背后推进它的等待。

### 3.4 并行

并行表示多个任务在同一时刻使用不同的执行资源运行，例如多个 CPU 核心或多个进程。

异步 I/O 主要解决等待问题，不会自动让 CPU 密集型计算变快。计算大量图像、训练模型或执行复杂算法时，应该根据场景考虑多进程、专用计算库或任务队列。

到这里，我们已经知道异步并发想解决什么问题：

```text
任务 A 开始等待 I/O
    -> 暂停 A
    -> 运行任务 B
    -> B 也等待 I/O
    -> 哪个任务先完成，就恢复哪个任务
```

但要实现这件事，程序还需要两个具体机制：

1. 需要一种能够“运行一段时间后暂停，之后再继续”的任务；
2. 需要一个执行器，负责在这些任务之间切换，并在等待结束后恢复任务。

Python 中，第一种任务通常由**协程**表示，第二种执行器就是前面提到的**事件循环**。接下来先看协程如何写，再回头观察事件循环如何调度它。

## 4. 协程和 `async def`

### 4.1 用 `async def` 定义可暂停的函数

普通函数从第一行开始执行，直到返回结果或抛出异常。它在执行过程中不会因为等待 I/O 而主动把控制权交给其他任务。为了表达“这个函数内部可能会暂停，并把控制权交还给事件循环”，Python 提供了 `async def`：

使用 `async def` 可以定义协程函数：

```python
import asyncio


async def greet(name: str) -> str:
    await asyncio.sleep(1)
    return f"hello, {name}"
```

这里的 `greet` 仍然是一个函数，但它的执行方式和普通函数不同。函数体中的 `await asyncio.sleep(1)` 表示：等待这一秒期间，当前任务可以暂停，事件循环可以去运行其他任务。

需要注意，**定义协程函数**和**运行协程函数**是两件事。调用协程函数时，不会直接得到字符串结果：

```python
result = greet("Alice")
print(result)
```

这里的 `result` 是一个**协程对象**。它表示一次尚未完成的异步计算，而不是 `greet` 最终返回的字符串。此时，`greet` 的函数体还没有按照预期执行完成。

要让事件循环真正运行这个协程，需要在另一个协程中使用 `await` 等待它：

```python
async def main() -> None:
    result = await greet("Alice")
    print(result)


asyncio.run(main())
```

这段代码体现了几个对象之间的关系：

```text
async def greet(...)  -> 定义协程函数
greet("Alice")        -> 得到协程对象
await greet("Alice")  -> 等待协程完成并取得返回值
asyncio.run(main())   -> 启动事件循环，运行最外层协程
```

`asyncio.run()` 为一个异步程序创建并运行事件循环，等待 `main()` 完成后退出。它通常适合作为异步脚本的入口。前面的同步程序可以直接从第一行开始执行，而这个异步程序需要先由 `asyncio.run()` 启动事件循环，事件循环才有机会驱动 `main()` 和它等待的其他协程。

### 4.2 `await` 的作用

`await` 可以理解为：

> 等待一个可等待对象的结果；等待期间，当前协程暂停，事件循环可以运行其他任务。

因此，`await` 不是简单地把程序“卡住”。它只暂停当前协程，并把执行机会交还给事件循环。只有被等待的操作真正完成后，当前协程才会从 `await` 的下一行继续执行。

`await` 只能出现在 `async def` 函数内部：

```python好的，我发现我前面关于协程这部分听不太懂的一个原因是，在前面的异步那里可能没有讲清楚：关于 IO 这些操作是来自于内核，而不是当前的这个协程做的。所以我一直都在想，为什么它都被暂停了还能完成
async def main() -> None:
    value = await greet("Alice")
    print(value)
```

不能在普通函数中直接使用：

```python
def main():
    value = await greet("Alice")  # SyntaxError
```

## 5. 事件循环的直观模型

事件循环负责检查哪些异步任务可以继续运行，并在任务等待 I/O 时切换到其他任务。

可以把它简化为下面的过程：

```text
事件循环开始
    -> 运行任务 A，A 等待网络
    -> 运行任务 B，B 等待数据库
    -> 检查 A 是否完成
    -> 检查 B 是否完成
    -> 哪个任务的等待结束，就恢复哪个任务
事件循环结束
```

这种切换是协作式的。任务只有在执行 `await` 等待异步操作时，才有机会把执行权交还给事件循环。

因此，下面的代码虽然使用了 `async def`，仍然会阻塞事件循环：

```python
import time


async def bad_task() -> None:
    time.sleep(3)
```

`time.sleep()` 不会把执行权交还给事件循环。执行它时，同一个事件循环中的其他任务也无法继续。

异步代码中应该优先使用对应的异步等待：

```python
import asyncio


async def good_task() -> None:
    await asyncio.sleep(3)
```

## 6. 连续等待和并发等待

下面是连续等待：

```python
import asyncio


async def fetch(name: str, delay: float) -> str:
    print(f"{name} started")
    await asyncio.sleep(delay)
    print(f"{name} finished")
    return name


async def sequential() -> None:
    first = await fetch("A", 2)
    second = await fetch("B", 1)
    print(first, second)


asyncio.run(sequential())
```

总耗时大约是 3 秒，因为 B 要等 A 完成后才开始。

可以使用 `asyncio.gather()` 同时等待多个协程：

```python
async def concurrent() -> None:
    results = await asyncio.gather(
        fetch("A", 2),
        fetch("B", 1),
    )
    print(results)


asyncio.run(concurrent())
```

两个任务会同时开始等待，总耗时大约是 2 秒，也就是最长任务的耗时。

`gather()` 适合多个相互独立的操作，例如：

- 同时请求多个服务；
- 同时查询多个互不依赖的数据源；
- 同时获取多个模型工具的结果。

如果后一个操作依赖前一个操作的结果，就不能为了追求并发而强行使用 `gather()`。

## 7. 创建任务

`asyncio.create_task()` 会把协程安排到当前事件循环中运行，并返回一个任务对象：

```python
async def main() -> None:
    task_a = asyncio.create_task(fetch("A", 2))
    task_b = asyncio.create_task(fetch("B", 1))

    result_a = await task_a
    result_b = await task_b
    print(result_a, result_b)


asyncio.run(main())
```

创建任务后要记得等待它，或者保存任务对象以便之后检查结果。不要创建任务后丢弃引用，否则可能无法正确处理任务的异常和清理。

对于简单的“同时等待多个结果”，`asyncio.gather()` 通常更容易阅读。需要单独取消、检查或管理任务时，再使用 `create_task()`。

### 7.1 为什么创建了任务，还要再等待一次

初学时常有一个困惑：`create_task()` 明明已经让任务启动了，为什么后面还要 `await task` 再等一次？是不是重复了？

不是。关键在于：**「启动」和「等待」是两个不同主体的动作**。

- **启动**：把协程交给事件循环，让它开始运行。执行者是 `create_task()` 和它背后的事件循环。任务一旦创建，就已经在独立运行了；
- **等待**：当前协程（外侧函数）自己挂起，直到被等待的对象完成。执行者是**包含 `await` 的外侧协程**，而不是那个被等待的任务自己。

所以“为什么已经启动了还要再等”的答案是：**被启动的是任务，在等待的是外侧函数自己**——两者不是同一个主体。如果不等待，外侧函数会先结束，任务可能来不及完成，异常也无处处理。

| 写法 | 谁启动 | 谁等待 | 时序 |
| --- | --- | --- | --- |
| `await fetch("A", 2)` | 事件循环在 `await` 那一刻开始驱动 `fetch` | 外侧协程挂起等它完成 | 启动和等待几乎同时发生，看起来像一体 |
| `task = create_task(fetch("A", 2))` | `create_task()` 时就已经启动 | 外侧协程之后才 `await task` 等它完成 | 启动和等待分离，中间可以干别的 |

> 一句话总结：`await X` = 外侧协程挂起，等 **X** 完成；而 X 是否已经在跑、何时开始跑，取决于 X 是怎么来的——直接 `await` 协程对象时由事件循环当场驱动，`await` 一个 `Task` 时它早在 `create_task()` 时就开始运行了。

## 8. 异常处理

异步任务中的异常仍然应该被明确处理：

```python
async def fail() -> str:
    await asyncio.sleep(0.1)
    raise RuntimeError("upstream failed")


async def main() -> None:
    try:
        await fail()
    except RuntimeError as exc:
        print(f"handled: {exc}")


asyncio.run(main())
```

使用 `gather()` 时，可以通过 `return_exceptions=True` 把异常作为结果收集：

```python
async def main() -> None:
    results = await asyncio.gather(
        fetch("A", 1),
        fail(),
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            print(f"failed: {result}")
        else:
            print(f"succeeded: {result}")


asyncio.run(main())
```

是否允许部分成功，需要由业务决定。比如同时查询多个推荐服务时可以接受部分结果；保存一组必须完整的数据时，部分成功可能就应该让整个操作失败。

## 9. 超时和取消

网络服务和模型调用不能无限等待。可以使用 `asyncio.timeout()` 设置超时。

先解释 `async with` 这个写法。`with` 语句用于**上下文管理器**：进入时初始化、退出时清理，即使中间抛异常也会执行清理（比如 `with open(...)` 保证文件关闭）。`async with` 是它的异步版本，区别是进入和退出时**可以 `await` 异步操作**。这里的 `asyncio.timeout(1)` 就是一个异步上下文管理器，可以把它理解为一个**定时闹钟**：

- 进入 `async with` 时，启动一个 1 秒的闹钟；
- 代码块内的操作在 1 秒内完成：退出时取消闹钟，正常返回；
- 1 秒后仍未完成：闹钟触发，正在等待的操作被**取消**，并在退出 `async with` 时抛出 `TimeoutError`。

所以 `async with asyncio.timeout(1):` 的意思是：**这段代码最多等 1 秒，超时就把正在等待的操作取消，并抛出 `TimeoutError` 结束**。

```python
import asyncio


async def slow_operation() -> str:
    await asyncio.sleep(5)
    return "done"


async def main() -> None:
    try:
        async with asyncio.timeout(1):
            result = await slow_operation()
            print(result)
    except TimeoutError:
        print("operation timed out")


asyncio.run(main())
```

上面的示例中，如果 `slow_operation()` 在 1 秒内完成，程序正常打印结果；如果超时，`async with` 退出时抛出 `TimeoutError`，被 `except` 捕获。

注意一点：超时**不是**“干等 1 秒然后继续”，而是把正在等待的操作**取消**了——这跟后面“任务取消”是同一套机制。所以超时发生后一定要处理 `TimeoutError`，否则程序会直接报错退出。

`asyncio.timeout()` 与 `asyncio.wait_for()` 效果等价，只是写法不同：

| 写法 | 特点 |
| --- | --- |
| `async with asyncio.timeout(1):` | 可以包裹多行代码、多个 `await`，代码块边界清晰；Python 3.11+ |
| `result = await asyncio.wait_for(coro, timeout=1)` | 只包裹单个协程；写法更紧凑；较早版本也可用 |

如果项目需要兼容较早的 Python 版本，也可以使用 `asyncio.wait_for()`：

```python
async def main() -> None:
    try:
        result = await asyncio.wait_for(slow_operation(), timeout=1)
        print(result)
    except asyncio.TimeoutError:
        print("operation timed out")
```

任务也可以被主动取消：

```python
async def main() -> None:
    task = asyncio.create_task(slow_operation())
    await asyncio.sleep(0.1)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("task cancelled")


asyncio.run(main())
```

被取消的协程应该在 `finally` 中释放资源：

```python
async def request_resource() -> None:
    resource = await acquire_resource()
    try:
        await use_resource(resource)
    finally:
        await release_resource(resource)
```

这里的 `acquire_resource`、`use_resource` 和 `release_resource` 只是示意函数。真实项目中的连接、文件、锁和临时状态都需要考虑异常和取消路径。

## 10. 处理阻塞调用

异步函数中可能需要调用暂时没有异步版本的旧代码。例如某个库只有同步接口：

```python
def blocking_read() -> str:
    import time

    time.sleep(2)
    return "data"
```

直接在异步函数中调用会阻塞事件循环：

```python
async def bad_read() -> str:
    return blocking_read()
```

可以使用 `asyncio.to_thread()` 把阻塞调用放到线程中：

```python
async def read_without_blocking_loop() -> str:
    return await asyncio.to_thread(blocking_read)
```

这并不意味着 CPU 密集型任务会因此自动变快。`to_thread()` 主要用于避免同步 I/O 阻塞事件循环，例如旧的文件库或同步客户端。CPU 密集型任务通常应该考虑多进程或专门的计算方案。

## 11. Python 协程不等于后台任务

这几个概念经常被混淆：

### Python 异步协程

解决的是单个进程内的 I/O 等待和任务切换：

```text
一个进程 -> 一个事件循环 -> 多个协程任务
```

### 后台任务

解决的是请求不必等待某个工作完成：

```text
HTTP 请求 -> 创建任务 -> 立即返回
后台程序 -> 执行任务
```

### 消息队列

解决的是任务的投递、持久化、确认、重试和消费者解耦：

```text
生产者 -> 消息队列 -> 消费者
```

协程不会自动提供可靠投递和失败重试，消息队列也不一定需要使用协程。后续 Redis 课程会单独学习后台任务、消息队列和消费幂等。

## 12. 常见错误

### 错误一：忘记等待协程

```python
result = fetch("A", 1)
print(result)
```

这只会得到协程对象。需要在异步函数中使用 `await result`，或把它交给 `asyncio.run()`。

### 错误二：连续 `await` 却以为是并发

```python
await fetch("A", 2)
await fetch("B", 1)
```

这是顺序执行。需要使用 `gather()` 或先创建任务，才能让两个独立操作同时等待。

### 错误三：在异步代码中使用阻塞调用

```python
async def bad():
    time.sleep(5)
```

`async def` 不会自动把函数中的所有代码变成非阻塞代码。

### 错误四：把异步用于 CPU 密集型计算

异步主要优化等待 I/O 的时间，不会让复杂计算自动使用多个 CPU 核心。

### 错误五：忽略任务异常和取消

创建后台任务后不保存、不等待、不处理异常，可能造成错误丢失、资源未释放或任务状态不明确。

## 13. 本课练习

### 练习一：比较顺序等待和并发等待

使用 `asyncio.sleep()` 模拟三个独立的网络请求：

- 请求 A 等待 2 秒；
- 请求 B 等待 1 秒；
- 请求 C 等待 3 秒。

分别实现：

1. 顺序调用三个请求；
2. 使用 `asyncio.gather()` 并发等待三个请求。

记录两种实现的总耗时，并解释为什么不同。

### 练习二：处理失败和超时

为其中一个模拟请求增加失败逻辑，为另一个请求设置超时。要求：

- 能区分成功结果和异常结果；
- 超时后不会无限等待；
- 程序结束前能够清理创建的任务。

### 练习三：识别阻塞调用

编写两个异步任务：

- 一个使用 `asyncio.sleep()`；
- 一个使用 `time.sleep()`。

观察它们对其他任务的影响，再使用 `asyncio.to_thread()` 改写阻塞调用，比较执行顺序。

## 14. 验收标准

完成本课后，应当能够用自己的话回答：

1. 同步、异步、并发和并行有什么区别？
2. 为什么调用协程函数不会立即得到最终结果？
3. `await` 等待期间发生了什么？
4. 为什么连续两个 `await` 不等于并发？
5. `asyncio.gather()` 适合什么场景？
6. 为什么 `time.sleep()` 会阻塞事件循环？
7. `asyncio.to_thread()` 解决什么问题？它为什么不是 CPU 并行方案？
8. 任务超时或取消后，为什么仍然需要执行资源清理？
9. Python 协程和消息队列分别解决什么问题？

代码验收：

- 能运行一个使用 `asyncio.run()` 启动的异步脚本；
- 能使用 `gather()` 并发等待多个独立的 I/O 模拟任务；
- 能处理至少一个失败任务和一个超时任务；
- 能在取消或异常时通过 `finally` 释放资源；
- 能指出代码中可能阻塞事件循环的同步调用。

## 15. 与后续课程的衔接

- FastAPI：学习同步路由和异步路由的选择、异步模型调用、超时和流式响应；
- 数据库：理解同步 SQLite、异步数据库驱动和连接生命周期的区别，不因为使用异步路由就强行改造所有 SQL；
- Redis：学习连接池、后台任务、消息队列、失败重试和消费幂等；
- 生产化：学习超时、取消、限流、重试、日志和任务监控。
