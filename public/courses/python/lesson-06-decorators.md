# 第六课：装饰器

第五课提到 `@contextmanager` 本身是一个装饰器。本课专门讲装饰器：Python 生态里最常见的语言机制之一。`@dataclass`（第三课用过）、FastAPI 的路由注册、pytest 的 fixture，都是装饰器。理解装饰器的前提是先接受一个事实：函数也是对象，可以像普通值一样传递。

本课的重点是弄清楚装饰器到底做了什么，而不是记住各种花哨写法。读完本课，你应该能看懂任何 `@something` 形式的代码在干什么。

## 学习目标

完成本课后，你应当能够：

- 解释"函数是对象"以及函数可以作为参数和返回值；
- 写出装饰器的固定模板，并解释 `@` 语法糖；
- 使用 `functools.wraps` 保留函数的元信息；
- 编写带参数的装饰器（装饰器工厂）；
- 编写带内部状态的装饰器；
- 在实际库和框架中识别装饰器。

## 1. 函数是对象

### 1.1 函数可以赋值、传参和返回

函数定义之后，它的名字就是一个普通变量，值是可调用对象：

```python
def double(value: int) -> int:
    return value * 2


f = double
print(f(3))        # 6
print(f.__name__)  # double
```

函数可以放进列表、作为参数传给另一个函数，也可以作为返回值：

```python
def apply(func, value):
    return func(value)


print(apply(double, 4))  # 8
```

"函数可以作为参数和返回值"是装饰器成立的前提。

### 1.2 函数的元信息：`__name__`、`__doc__` 等

函数对象除了"能被调用"，还自带一组描述自身的属性，统称元信息。最常用的是 `__name__` 和 `__doc__`：

| 属性 | 值是什么 | 谁在使用 |
| --- | --- | --- |
| `__name__` | 函数的名字（字符串） | 日志、调试、堆栈跟踪 |
| `__doc__` | 函数开头的文档字符串（docstring） | `help()`、IDE 补全提示、自动生成文档 |
| `__module__` | 函数定义所在的模块名 | 调试、序列化 |
| `__annotations__` | 参数和返回值的类型标注 | IDE、静态检查器 |

`__doc__` 不需要单独赋值：写在 `def` 下面第一行的字符串字面量就是它。所以可以这样读取：

```python
def add_record(records, content, kind):
    """向记录列表添加一条生活记录。"""  # 这一行字符串就是 add_record.__doc__
    ...


print(add_record.__name__)  # add_record —— 函数的名字
print(add_record.__doc__)   # 向记录列表添加一条生活记录。 —— 函数开头的文档字符串
```

调试工具、文档工具和框架依赖这些信息：日志要打函数名，IDE 要把 docstring 显示在补全提示里。装饰器如果不加处理，会把这些信息弄丢，这是后面 `functools.wraps` 存在的原因。

## 2. 装饰器的固定模板

### 2.1 模板长什么样

装饰器是"接收一个函数、返回一个新函数"的函数。虽然装饰器的用途千差万别，但写法都来自同一个固定模板：

```python
def decorator(func):
    def wrapper(*args, **kwargs):
        # 调用原函数之前：额外的行为
        result = func(*args, **kwargs)
        # 调用原函数之后：额外的行为
        return result

    return wrapper
```

逐层拆解这个模板：

- 外层 `decorator(func)`：接收被装饰的原函数，例如 `add_record`；
- `wrapper(*args, **kwargs)`：返回给调用者的新函数。`*args, **kwargs` 让它能接收任意参数并原样转发给原函数；
- 调用前 / 调用后：装饰器要增加的横切行为写在这两个位置——打印日志、统计耗时、校验权限、失败重试；
- `return wrapper`：把新函数交出去。调用者看到的名字仍然是原函数名，实际执行的是 `wrapper`。

### 2.2 为什么必须是两层函数

两层嵌套不是风格偏好，而是由 `@` 的执行方式决定的。`@announce` 等价于 `double = announce(double)`：装饰器在**函数定义时**被调用一次，参数是"函数本身"，不是调用参数。调用参数要等调用发生时才有，所以"接收调用参数"这件事只能由另一层函数来做。

如果试图把两层合成一层，让外层同时接收函数和调用参数：

```python
def announce(func, *args, **kwargs):   # 错误：把两个时刻的参数混在一起
    print("函数开始执行")
    return func(*args, **kwargs)
```

`@announce` 执行时发生的是 `announce(double)`：此刻 `*args, **kwargs` 是空的（调用还没有发生），于是 `func(*args, **kwargs)` 变成 `double()`——在定义阶段就调用 `double` 且没传 `value`，模块一加载就抛 `TypeError`。即使被装饰的函数没有参数，`double = announce(double)` 也会把 `double` 绑成调用的**返回值**（一个普通值），`double` 不再是函数，之后 `double(3)` 会报"对象不可调用"。

所以内外两层的分工必须分开：

```text
外层（定义时执行一次）  接收原函数，返回新函数
内层（每次调用执行）    接收调用参数，做调用前后的行为，再转调原函数
```

### 2.3 内层函数的名字不是固定的

`wrapper` 只是惯例命名，不是关键字。固定的是**结构和位置**：外层接收原函数并返回新函数，内层接收调用参数。内层叫 `wrapped`、`inner`、`call_original` 效果完全一样：

```python
def decorator(func):
    def inner(*args, **kwargs):   # 名字换成 inner，行为不变
        return func(*args, **kwargs)

    return inner
```

代码库里 `wrapper`（"包装"）最常见，看到它就能想到这个模板，但不要以为它是语法要求。

### 2.4 模板本身什么也不做

上面的模板没有填入任何额外行为，只是把参数和返回值原样转发，等价于没有装饰。**具体装饰器 = 模板 + 在"调用前后"的位置填入具体行为。** 例如在调用前打印一句话（对比 2.2 那个混用两个时刻的错误写法）：

```python
def announce(func):
    def wrapper(*args, **kwargs):
        print("函数开始执行")
        return func(*args, **kwargs)

    return wrapper
```

先记住模板的形状，第 4 节开始往里填日志等常用行为。在填行为之前，还有一个问题要先解决：怎么把这个包装"挂"到目标函数上。这就是第 3 节 `@` 的作用。

## 3. `@` 语法糖：`@` 是什么

把装饰器挂到一个函数上有两种等价写法。不写 `@`，手动包装：

```python
def double(value: int) -> int:
    return value * 2

double = announce(double)

print(double(3))
```

用 `@`，把包装写在函数定义的上方：

```python
@announce
def double(value: int) -> int:
    return value * 2

print(double(3))
```

两种写法完全等价。**`@announce` 的意思是：这个函数定义好之后，用 `announce` 包装它，再把结果绑回原来的名字。**

一个容易混淆的细节是执行时机：`@` 在**函数定义时**执行。模块加载到 `@announce` 这一行时，`announce(double)` 就已经调用并完成了包装；之后每次调用 `double`，执行的都是 `wrapper`，`announce` 本身只被调用一次。所以装饰器外层适合放"定义时只需准备一次"的逻辑，而 wrapper 里放"每次调用都要做"的逻辑。

以后看到 `@something`，读法就是："`something` 包装了下面这个函数"。

### 3.1 多个装饰器：自下而上应用，自外而内执行

一个函数可以同时挂多个装饰器：

```python
@log_call
@measure
def add(a, b):
    return a + b
```

等价于 `add = log_call(measure(add))`。两条规则：

- **定义时自下而上应用**：靠 `def` 最近的装饰器先包装，成为最内层；
- **调用时自外而内执行**：外层装饰器先进入、最后退出，原函数在最内层最后执行。

```text
log_call 进入（最外层先进入）
    measure 进入
        add 执行
    measure 退出
log_call 退出（最外层最后退出）
```

## 4. 具体的常用装饰器

### 4.1 日志装饰器 `log_call`

现在按模板填写日志行为：调用前打印参数，调用后打印返回值。

```python
def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}，参数：{args} {kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} 返回：{result}")
        return result

    return wrapper
```

应用它：

```python
@log_call
def add_record(records, content, kind):
    record = LifeRecord(content, kind)
    records.append(record)
    return record
```

```python
records = []
add_record(records, "整理笔记", "learning")
```

输出会多出两行日志。`add_record` 原本的代码一行没改，只是被 `log_call` 包了一层——这就是装饰器的价值：不动原函数，给多个函数统一加行为。给 `find_record`、`save_records` 也加上 `@log_call`，它们就都有了日志。

接下来写装饰器时会遇到三个实际问题，第 5、6、7 节分别处理：如何保住函数的名字（`functools.wraps`）、如何给装饰器传参数（装饰器工厂）、如何让装饰器记住历史（有状态装饰器）。

## 5. `functools.wraps`：保住函数的名字

运行 4.1 的示例后，如果打印 `add_record.__name__`，会得到 `"wrapper"` 而不是 `"add_record"`：

```python
print(add_record.__name__)  # wrapper，不是 add_record
```

原因：`@log_call` 把 `add_record` 这个名字绑到了 wrapper 上，而 wrapper 自己的 `__name__` 是 `"wrapper"`。第 1.2 节说过，日志、文档工具和框架都依赖 `__name__`、`__doc__` 这些元信息，丢了会影响调试和文档。

`functools` 是 Python 标准库中提供高阶函数工具的模块（`wraps`、`partial`、`lru_cache` 都来自它），这是本课程第一次用到它。`functools.wraps(func)` 会把原函数的 `__name__`、`__doc__` 等信息复制到 wrapper 上：

```python
from functools import wraps


def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}，参数：{args} {kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} 返回：{result}")
        return result

    return wrapper
```

这样 `add_record.__name__` 仍然是 `"add_record"`。调试、堆栈跟踪和文档工具都依赖这些信息，所以自己写装饰器时，固定模板里默认加上 `@wraps(func)`。

## 6. 带参数的装饰器（装饰器工厂）

`@log_call` 本身不接受参数。如果装饰器需要参数（例如一个标签），需要再包一层。外面那层接收参数并返回真正的装饰器，因此这种写法叫装饰器工厂：

```python
def log_elapsed(label: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"开始：{label}")
            result = func(*args, **kwargs)
            print(f"结束：{label}")
            return result

        return wrapper

    return decorator
```

```python
@log_elapsed("查找记录")
def find_record(records, content):
    for record in records:
        if record.content == content:
            return record
    return None
```

执行顺序是：`log_elapsed("查找记录")` 先被调用，返回 `decorator`；然后 `@decorator` 把原函数包装成 wrapper。以后看到 `@something("参数")` 的写法，就是装饰器工厂。

## 7. 有状态的装饰器

wrapper 可以引用定义在外层函数作用域中的变量，这些变量会在多次调用之间保持。下面的装饰器统计函数被调用了几次：

```python
def count_calls(func):
    calls = 0

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal calls
        calls += 1
        print(f"{func.__name__} 被调用 {calls} 次")
        return func(*args, **kwargs)

    return wrapper
```

```python
@count_calls
def double(value: int) -> int:
    return value * 2


double(2)
double(3)
```

`calls` 在 `count_calls` 的作用域里，`wrapper` 每次调用都会读写它。**`nonlocal` 表示"修改的不是本地变量，而是外层函数的变量"**。这种由 wrapper 长期持有的数据叫**闭包状态**，可以实现计数器、缓存、限流等需要记住历史的行为。

## 8. 装饰器的常见用途

- **日志**：记录谁调用了哪个函数、参数是什么（本课的 `log_call`）；
- **计时**：统计一段逻辑的耗时，配合第五课的计时器；
- **重试**：调用失败（例如网络请求、模型调用）时自动重试若干次；
- **权限检查**：调用前校验身份或权限，不满足则拒绝；
- **缓存**：用参数作为键缓存结果，避免重复计算；
- **路由注册**：把函数注册到框架的路由表（FastAPI 的 `@app.get`）。

其中"重试"在 AI 应用里很常见：调用 LLM 接口可能偶发超时或限流，给调用加上"失败后重试 N 次"的装饰器，可以显著提高稳定性。这也是本课作业的一部分。

## 9. 在实际库和框架中识别装饰器

前几课已经见过装饰器，只是当时没有点破：

- `@dataclass`（第三课）：装饰器读取字段，自动生成构造方法等方法；
- `@contextmanager`（第五课）：装饰器把生成器函数变成上下文管理器；
- FastAPI 的 `@app.get("/")`：装饰器把函数注册到路由表，并附加请求处理信息；
- pytest 的 `@pytest.fixture`：装饰器标记测试准备函数；
- 其他框架中的 `@login_required`、`@cache` 等：装饰器实现横切关注点。

识别方法：看到 `@` 开头、定义在函数或类上一行的写法，就是装饰器。它不改变函数原有的逻辑，而是在函数外面套了一层行为。理解了装饰器，这些框架用法就不再是"魔法"。

## 10. 运行课程代码

```bash
python code/python/lesson_06_decorators.py
```

上半部分会运行 `log_call`、`functools.wraps` 和装饰器工厂的完整示例。注意代码文件里的 `log_call` 已经带上了 `@wraps`（第 5 节的内容），文档第 4 节先展示未加 `wraps` 的版本，是为了先暴露"名字丢失"这个问题。下半部分作业包含 TODO，但默认不会调用 `homework()`，因此课程示例仍然可以直接运行。

## 11. 课后作业：提醒服务的装饰器

作业代码在同一个 Python 文件的下半部分，场景沿用第四课的提醒清单，不要求重新实现上面的生活记录。

需要完成：

1. 完成 `count_calls` 装饰器：统计函数被调用的次数，每次调用后打印"函数名 被调用 N 次"，并使用 `functools.wraps` 保留函数信息；
2. 完成 `retry(max_times)` 装饰器工厂：调用原函数，成功则返回结果；抛出异常则重试，最多 `max_times` 次；最后一次仍然失败时把异常继续抛出；使用 `functools.wraps`；
3. 在 `homework()` 中用 `count_calls` 包装 `add_reminder` 并调用三次，观察打印输出；
4. 用 `@retry(3)` 装饰一个"前两次抛出异常、第三次成功"的函数并调用，观察它最终成功；
5. 打印被装饰函数的 `__name__`，确认没有被装饰器改写。

## 12. 验收问题

1. 为什么说函数是对象？函数作为参数和返回值意味着什么？
2. 装饰器的固定模板有哪几个部分？`*args, **kwargs` 起什么作用？
3. `@log_call` 和 `add_record = log_call(add_record)` 是什么关系？`@` 在什么时候执行？
4. `functools.wraps` 解决了什么问题？
5. 装饰器工厂和普通装饰器有什么区别？`@log_elapsed("查找记录")` 的执行顺序是什么？
6. 有状态的装饰器中，`nonlocal` 起什么作用？
7. 在前面已经学过的课程中，哪些地方已经使用过装饰器？
