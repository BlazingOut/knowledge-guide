# 第五课：迭代器、生成器、上下文管理器

Python 课程从"怎么把数据放进文件"讲到"怎么把代码拆成模块"。本课解决另一个工程问题：**数据怎么按需取出来，资源怎么安全地用完就还**。假设生活记录文件里有十万条记录，直接全部读进内存既浪费又没有必要；再假设一段代码获取了锁、连接或文件句柄，一旦忘了释放，程序就会出错。本课的两个机制分别解决这两类问题：迭代器和生成器负责"按需生产数据"，上下文管理器负责"进入和退出必须成对"的资源。

本课先用代码观察迭代和生成的机制，再讲上下文管理器，最后回到真实场景：为什么框架代码里到处是 `with` 和 `yield`。装饰器会在第六课单独讲，本课只在必要时提前点一句。

**学习目标：**

1. 能区分可迭代对象、迭代器和生成器，说出 `iter()`、`next()`、`StopIteration` 各自的作用；
2. 能写出实现 `__iter__` 的自定义可迭代对象，并解释它和迭代器"能不能反复遍历"的区别；
3. 能用 `yield` 写出生成器，并解释惰性求值带来的内存和提前停止的好处；
4. 能写出自定义上下文管理器，并解释 `__exit__` 的返回值如何决定异常的去向；
5. 能说出 `@contextmanager` 什么时候适合用；
6. 能在实际库和框架中认出这三种机制。

## 1. 为什么需要"按需取数据"

先看一个具体的业务问题。生活记录的 JSON 文件里可能有几千条记录，但你今天的任务是"打印前两条看看格式对不对"。最直接的做法是：

```python
records = load_records(path)   # 把全部记录读进内存
print(records[0])
print(records[1])
```

问题在于：`load_records` 必须把**全部**记录一次性构造出来，哪怕你只用到前两条。如果文件有十万条、每条都带类型标注的对象，这一下就占掉了大量内存；如果调用方只想在找到第一条符合条件的数据后就停止，后面的几万条都是白读。

"按需取数据"把这两个动作拆开：**生产方一次只产出一条，消费方要一条取一条**。这就是迭代器和生成器解决的核心问题。

```text
一次性取完：       生产方 ──► 完整列表 ──► 消费方挑着用（其余浪费）
按需取数据：       生产方 ──► 要一条给一条 ──► 消费方想停就停
```

## 2. 可迭代对象和迭代器

### 2.1 `for` 循环背后发生了什么

可以这样遍历记录：

```python
records = [LifeRecord("跑步", "health"), LifeRecord("读书", "learning")]
for record in records:
    print(record.summary())
```

`for` 循环并不是 Python 语言内置的特殊魔法。它做的事情可以拆开来看：

```python
iterator = iter(records)
print(next(iterator).summary())   # [health] 跑步（未完成）
print(next(iterator).summary())   # [learning] 读书（未完成）
```

`iter(records)` 从列表取得一个迭代器对象，`next(iterator)` 每次取出下一条。取完所有元素后，再次调用 `next()` 会抛出 `StopIteration`，`for` 循环就是捕获到这个结束信号后正常退出的：

```text
iter(records) ──► 迭代器对象
next(it)      ──► 第一条记录
next(it)      ──► 第二条记录
next(it)      ──► 抛 StopIteration，for 循环结束
```

`StopIteration` 不是错误，而是"没有更多元素"的结束信号。它由 `for` 循环自动处理，业务代码一般不需要手动捕获。

### 2.2 可迭代对象和迭代器的区别

这两个词经常被混用，但它们在协议层面有明确分工：

| | 可迭代对象（iterable） | 迭代器（iterator） |
| --- | --- | --- |
| 是什么 | 可以被 `iter()` 转换的对象 | `iter()` 返回的"指针"对象 |
| 例子 | 列表、元组、字典、字符串、文件 | `iter(records)` 的返回值 |
| 作用 | 提供数据来源 | 逐个取出元素 |
| 遍历次数 | 可以反复遍历 | 只能走一遍 |

迭代器本身通常也可以被 `iter()` 转换，返回值是它自己：

```python
iterator = iter(records)
print(iterator is iter(iterator))  # True
```

**记忆的关键：迭代器是一个只能向前、只能一次的指针；可迭代对象是能反复产生新迭代器的容器。**

字典、文件这些常见对象也都是可迭代的：

```python
for key, value in record.items():
    print(key, value)

for line in file:    # 文件对象是迭代器，逐行读取大文件不占用全部内存
    print(line)
```

### 2.3 自定义迭代器：`RecordIter`

实现 `__iter__` 和 `__next__` 的类就是一个迭代器。下面这个类按顺序取出记录列表里的元素：

```python
class RecordIter:
    def __init__(self, records: list[LifeRecord]):
        self.records = records
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self) -> LifeRecord:
        if self.index >= len(self.records):
            raise StopIteration
        record = self.records[self.index]
        self.index += 1
        return record
```

`__next__` 每次返回一条记录，并把下标前进一位；取完时抛出 `StopIteration`。`__iter__` 返回 `self`，因为迭代器本身就是自己的迭代器——这也是它"只能走一遍"的原因：`index` 只有一份，走完就没了。

### 2.4 自定义可迭代对象：`RecordBox`

实际业务里更常见的是"可迭代的容器"：一个保存记录的类，调用方可以 `for record in box` 遍历它，而且可以**反复遍历**。实现方式是写 `__iter__`，每次调用都返回一个**新的**迭代器：

```python
class RecordBox:
    """自定义可迭代对象：实现 __iter__ 后就能放进 for 循环。"""

    def __init__(self, records: list[LifeRecord] | None = None) -> None:
        self._records = list(records or [])

    def add(self, record: LifeRecord) -> None:
        self._records.append(record)

    def __iter__(self):
        # 每次返回一个新迭代器，所以同一个 box 可以反复遍历。
        return iter(self._records)
```

```python
box = RecordBox(records)

for record in box:        # 第一遍：正常输出
    print(record.summary())
for record in box:        # 第二遍：仍然有内容
    print(record.summary())
```

运行结果：同一 `box` 遍历两遍都有内容。把 `RecordIter` 和 `RecordBox` 放在一起对比，就能看清"迭代器"和"可迭代对象"的本质差别：

| | `RecordIter` | `RecordBox` |
| --- | --- | --- |
| `__iter__` 返回 | `self`（自己） | 新的迭代器 |
| 能遍历几次 | 一次 | 多次 |
| 本质 | 迭代器 | 可迭代对象 |

这也解释了 2.2 里"迭代器也是可迭代对象"的说法：迭代器为了能用 `for`，实现了 `__iter__` 并返回 self，代价是遍历变成一次性；容器每次生成新迭代器，才能反复遍历。**判断一个对象是迭代器还是可迭代对象，就看它的 `__iter__` 返回的是不是自己。**

## 3. 生成器

### 3.1 `yield` 让函数变成生成器

手写迭代器类的场景其实很少，因为生成器能做到同样的事，代码却短得多。包含 `yield` 的函数是生成器函数，调用它不会执行函数体，而是返回一个生成器对象：

```python
def unfinished(records: list[LifeRecord]):
    for record in records:
        if not record.completed:
            yield record
```

```python
gen = unfinished(records)   # 函数体还没有执行
print(next(gen).summary())  # 执行到第一个 yield，暂停并交出记录
```

每次 `next()`（或 `for` 循环）让函数体运行到下一个 `yield`，暂停并把值交出来；下一次 `next()` 从暂停的位置继续。**函数体里的代码（包括开头的准备工作）在第一次 `next()` 时才执行，而不是在调用生成器函数时执行。** 这个细节在后面"逐条读取记录"和作业的思考题里都会用到。

### 3.2 生成器就是迭代器

生成器对象本身就是迭代器，可以用 `next()` 和 `for` 循环，也可以转换成列表：

```python
print([record.content for record in unfinished(records)])
```

`for` 循环结束时，生成器同样通过 `StopIteration` 退出。生成器和手写迭代器类达到的效果相同，但代码短得多，是实际代码中"按需产出数据"的首选写法。

### 3.3 惰性求值

生成器是"按需计算"的：不会一次性构造完整的结果列表，而是每次产出一条。这带来两个实际好处：

- **内存占用低**：处理大量数据时，不需要把所有结果同时放在内存里；
- **可以提前停止**：调用方 `break` 之后，生成器不会再继续生成剩余部分。

```python
count = 0
for record in iter_records(path):
    if count >= 2:
        break
    print(record.summary())
    count += 1
```

`break` 之后，后面的记录不会被生成。换成返回列表的普通函数，这做不到：列表在返回之前就已经全部构造好了。

### 3.4 生成器只能迭代一次

一个生成器对象从头到尾只能被消费一遍：

```python
once = iter_records(path)
print("第一次：", [record.content for record in once])  # 有内容
print("第二次：", [record.content for record in once])  # 空列表
```

第一遍 `for` 循环结束后，生成器已经到达末尾。需要再次遍历时，要重新调用生成器函数，得到一个新的生成器对象。对比 2.4 的 `RecordBox`：容器每次 `__iter__` 都返回新迭代器，所以可以反复遍历；生成器自己就是迭代器，只能走一遍。

### 3.5 生成器表达式

和列表推导式类似的写法是生成器表达式，它返回生成器而不是列表：

```python
gen = (record for record in records if not record.completed)
```

列表推导式 `[...]` 立刻构造完整列表；生成器表达式 `(...)` 惰性产出。数据量小且需要反复使用结果时用列表推导式更直观；数据量大或只需要遍历一遍时，生成器更合适。

## 4. 逐条读取记录：把前几课的知识接起来

把第二课的 JSON 读取和第三课的 `LifeRecord` 结合起来，就得到逐条读取记录的生成器（代码文件 `code/python/lesson_05_language_tools.py` 的完整示例）：

```python
def iter_records(path: Path) -> Iterator[LifeRecord]:
    """逐条读取记录，按需产出，不一次性构造完整列表。"""
    for record in load_records(path):
        yield record
```

运行程序，输出会是逐条打印的记录：

```text
== 生成器：逐条读取记录 ==
[learning] 读书（已完成）
[health] 跑步（未完成）
[work] 写代码（未完成）
```

这个函数把"生产数据"和"消费数据"解耦：生产方（生成器）不知道消费方需要多少，消费方（`for` 循环）不需要一次性拥有全部数据。调用方只关心前两条时，拿到第二条之后就可以 `break`，剩下的记录不会被构造。

注意 `iter_records(path)` 的返回类型标注是 `Iterator[LifeRecord]` 而不是 `list[LifeRecord]`——类型标注如实反映了"这是一个按需产出记录的可迭代对象"。如果调用方需要完整列表，可以显式 `list(iter_records(path))`，这比写一个返回列表的函数更灵活：由调用方决定要多少。

## 5. 上下文管理器

### 5.1 `with` 在做什么

第二课已经用过 `with`：

```python
with path.open("r", encoding="utf-8") as file:
    records = json.load(file)
```

`with` 的含义是：进入时执行一些准备逻辑，退出时执行清理逻辑。打开文件后无论正常结束还是中途抛出异常，文件都会被关闭。**资源管理的痛点是"获取和释放必须成对出现"，`with` 把这对操作固定在一处，不会忘记释放。**

### 5.2 自定义上下文管理器：`__enter__` 和 `__exit__`

实现 `__enter__` 和 `__exit__` 的类可以在 `with` 中使用。下面是一个计时器：

```python
class Timer:
    """进入时记录开始时间，退出时打印耗时。"""

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        elapsed = time.perf_counter() - self.start
        print(f"耗时：{elapsed:.3f} 秒")
        return False
```

```python
with Timer():
    time.sleep(0.05)
```

- `__enter__` 在进入 `with` 块时执行，返回值绑定到 `as` 后面的变量；没有 `as` 时返回值被忽略；
- `__exit__` 在离开 `with` 块时执行，**无论块内是否抛出异常**。

### 5.3 `__exit__` 的参数和返回值：异常去哪了

`__exit__` 接收三个参数：异常类型、异常对象和 traceback。块内没有异常时，这三个值都是 `None`：

```python
def __exit__(self, exc_type, exc_value, traceback) -> None:
    print("exc_type:", exc_type)
    print("exc_value:", exc_value)
```

返回值决定异常如何处理，这是上下文管理器最容易被忽略的细节：

```text
__exit__ 返回 False（或 None）──► 不吞异常，异常继续向外传播
__exit__ 返回 True            ──► 本层处理完毕，调用者看不到异常
```

```python
with Timer():           # __exit__ 返回 False
    do_something()      # 块内抛出异常 → 异常继续向上传播，调用者能捕获
```

除非有明确理由（例如重试逻辑在 `__exit__` 内部已经完成），不要返回 `True`。吞掉异常会让调用者以为操作成功，而实际可能并没有。

### 5.4 `@contextmanager` 简化写法

如果上下文管理器只有进入和退出两段逻辑，可以用 `contextlib.contextmanager` 写成生成器形式：

```python
from contextlib import contextmanager


@contextmanager
def timer():
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"耗时：{time.perf_counter() - start:.3f} 秒")
```

`yield` 之前的部分相当于 `__enter__`，之后的部分相当于 `__exit__`。`finally` 保证即使块内抛出异常，退出逻辑仍然执行：

```python
with timer():
    time.sleep(0.02)
```

这里有个值得注意的细节：**`@contextmanager` 本身就是一个装饰器，它把生成器函数变成了上下文管理器。** 装饰器是下一课的主题，先记住这个例子即可。

### 5.5 什么时候需要自定义上下文管理器

当"进入时的准备"和"退出时的清理"必须成对出现时，就适合用上下文管理器固定这对操作。常见场景：

- 获取和释放锁（线程锁、分布式锁）；
- 打开和关闭连接、文件、会话；
- 记录一段操作的耗时（计时器）；
- 临时修改某个状态，结束后恢复。

如果只是打开和关闭资源，优先使用标准库或第三方库已经提供的上下文管理器（例如 `with open(...)`、`with requests.Session() as session`），不要重复实现。

## 6. 真实场景：框架里为什么到处是 `with` 和 `yield`

用过 Web 框架的人几乎每天写 `with`，用 `yield` 的代码也越来越多。这些不是炫技，而是本课两个机制在工程里的标准用法：

```text
with open(path)            ──► 文件自动关闭
with requests.Session()    ──► 会话用完自动释放
with redis_client.lock()   ──► 分布式锁自动释放
for line in file           ──► 文件对象是迭代器，逐行读大文件不占内存
```

后续课程里还有两个直接继承本课的写法：

- pytest 的 fixture 用 `yield` 分隔"准备"和"清理"（第七课工程 Python 展开）；
- FastAPI 的依赖注入支持 `yield` 形式的资源清理（FastAPI 课程展开）。

**阅读库文档时，看到 `with` 是上下文管理器，看到函数里有 `yield` 是生成器，看到能放进 `for` 循环的都是可迭代对象。** 理解这三个机制后，框架代码里很多"魔法"其实是这三个基础工具的组合。装饰器是下一个要认识的机制，第六课专门讲它。

## 7. 运行课程代码

```bash
python code/python/lesson_05_language_tools.py
```

会依次演示：`iter`/`next` 逐个取记录、取完抛出 `StopIteration`、自定义迭代器 `RecordIter`、自定义可迭代对象 `RecordBox`（反复遍历两遍）、生成器逐条读取记录、提前停止、生成器只能迭代一次（第二次输出为空）、计时器上下文管理器和 `@contextmanager` 写法。上半部分示例默认运行；下半部分作业包含 TODO，默认不会调用 `homework()`。

## 8. 课后作业：学习日志

作业和课程示例在同一个文件中：`code/python/lesson_05_language_tools.py`。上半部分可以直接运行；下半部分从 `# ===== 课后作业：学习日志 =====` 开始，场景改为学习日志文件，不要求重新实现上面的生活记录。

作业要求：

1. 完成 `StudyTimer` 上下文管理器：进入时记录开始时间，退出时把 `(label, seconds)` 追加到传入的 log 列表，并返回 `False` 不吞掉异常；
2. 完成 `iter_log_lines(path)` 生成器：逐行读取 UTF-8 文本文件，去掉行首尾空白、跳过空行，文件不存在时抛出 `FileNotFoundError`；
3. 在 `homework()` 中写入两行日志（其中一行是空行），用 `iter_log_lines` 逐条打印；
4. 用一个生成器对象连续 `for` 循环两次，观察第二次为什么没有输出——对比 `RecordBox` 为什么能遍历两遍；
5. 用 `StudyTimer` 记录一次作业用时，打印 log 列表；
6. 思考并在验收时回答：调用 `iter_log_lines(path)` 时，如果文件不存在，`FileNotFoundError` 是**立刻**抛出，还是要等到第一次 `for`/`next()` 才抛出？为什么？这和你预期的有什么区别？

## 9. 验收问题

1. 可迭代对象和迭代器有什么区别？`iter()` 返回什么？
2. `next()` 取完所有元素后会发生什么？`for` 循环是如何正常结束的？
3. `RecordIter` 和 `RecordBox` 的 `__iter__` 分别返回什么？为什么一个只能遍历一次、一个可以反复遍历？
4. 生成器函数和普通函数有什么区别？调用生成器函数时会发生什么？
5. 为什么逐条读取记录时生成器有用？`for` 循环中途 `break` 之后会发生什么？
6. `with` 语句的 `__enter__` 和 `__exit__` 分别在什么时候执行？
7. `__exit__` 返回 `True` 和返回 `False` 有什么区别？
8. `@contextmanager` 的 `yield` 之前和之后分别对应什么？

## 10. 面试高频考点

- 可迭代对象、迭代器、生成器三者的区别，以及 `iter()`、`next()`、`StopIteration` 的作用。
- 迭代器"只能向前、只能一次"，可迭代对象"每次 `__iter__` 返回新迭代器"——用 `RecordIter`/`RecordBox` 的对比说明。
- 生成器的惰性求值：什么时候省内存、为什么可以提前停止、为什么只能迭代一次。
- 上下文管理器协议（`__enter__`/`__exit__`）和 `__exit__` 返回值对异常传播的影响；`@contextmanager` 什么时候用。
- 框架中 `with`（资源清理）和 `yield`（准备/清理分离）的常见位置。
