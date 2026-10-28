# 第一课：异常与错误处理

异常处理是工程 Python 的基础。程序不仅要处理“正常输入”，还要处理文件不存在、参数错误、外部服务失败和业务规则不允许等情况。异常机制决定了错误如何被表示、传播、转换和最终处理。

本课会围绕一个生活记录模块展开，先观察异常如何产生，再学习如何在合适的边界处理它们。

## 1. 什么是异常

异常（exception）是程序运行过程中对“当前操作无法正常完成”的一种结构化表示。它不是普通返回值，也不是一条打印出来的错误文字。异常对象包含异常类型和错误信息，解释器会沿着当前调用链寻找能够处理它的代码。

例如：

```python
def divide(total: float, count: int) -> float:
    return total / count

divide(10, 0)
```

执行时会产生 `ZeroDivisionError`。如果没有处理代码，程序会停止，并打印 traceback。

## 2. 异常类型和 traceback

Python 的异常是对象，通常属于 `BaseException` 的子类。业务代码一般捕获 `Exception` 或更具体的异常，不应随意捕获 `BaseException`，因为后者还包含系统退出和键盘中断等控制信号。

常见异常：

| 异常 | 常见原因 |
| --- | --- |
| `ValueError` | 类型可以接受，但值不合法 |
| `TypeError` | 操作对象类型不合适 |
| `KeyError` | 字典中不存在指定键 |
| `IndexError` | 序列下标越界 |
| `FileNotFoundError` | 文件路径不存在 |
| `ZeroDivisionError` | 除数为零 |

traceback 是异常发生时的调用路径报告。它通常从调用者一路显示到真正抛出异常的位置；阅读时先找到最后一行的异常类型和消息，再向上查看哪一行代码调用了出错函数。

## 3. 异常如何传播

```python
def parse_count(text: str) -> int:
    return int(text)

def load_limit(text: str) -> int:
    return parse_count(text)

load_limit("many")
```

`int("many")` 产生 `ValueError`。`parse_count` 没有处理，所以异常返回到 `load_limit`；`load_limit` 也没有处理，于是继续返回到最外层。异常会沿调用栈向上寻找处理者。

```text
parse_count
    ↑ 未处理
load_limit
    ↑ 未处理
程序入口
    ↑ 最终显示 traceback
```

异常传播不是“自动重试”，也不是“自动返回 None”。如果一直没有处理者，当前程序执行会终止。

## 4. `try` 和 `except`

捕获异常的基本形式：

```python
try:
    count = int(user_input)
except ValueError:
    count = 0
```

`try` 中的代码出现指定异常时，跳转到对应的 `except`；没有异常时不会执行该 `except`。应尽量捕获具体类型：

```python
try:
    record = records[index]
except IndexError:
    print("记录不存在")
```

不要这样写：

```python
try:
    do_something()
except Exception:
    pass
```

这会隐藏真正的 bug，让程序看似继续运行但状态已经不正确。

### 4.1 多种异常使用同一个处理逻辑

如果多种异常需要相同处理，可以把异常类型写成元组：

```python
try:
    count = int(user_input)
except (TypeError, ValueError):
    print("数量必须是整数")
```

这表示 `TypeError` 或 `ValueError` 都进入同一个处理分支。括号中的内容是异常类组成的元组，不要写成 `except TypeError or ValueError`。

这种写法适合两种底层错误在当前层具有相同含义的情况。例如，传入对象类型不合适，或字符串内容不能转换，都可以统一转换为“输入必须是整数”。

### 4.2 多种异常分别处理

如果不同异常需要不同动作，就写多个 `except`：

```python
try:
    with open(path, encoding="utf-8") as file:
        content = file.read()
except FileNotFoundError:
    print("文件不存在")
except PermissionError:
    print("没有权限读取文件")
```

Python 会从上到下检查 `except`，使用第一个匹配的分支。

### 4.3 使用异常继承关系统一处理

有些异常属于同一个父类：

```text
LookupError
├── IndexError
└── KeyError
```

因此可以统一捕获：

```python
try:
    content = records[index]["content"]
except LookupError:
    print("查找记录失败")
```

如果既需要特殊处理子类，又需要处理其他父类异常，具体异常必须写在前面：

```python
try:
    with open(path, encoding="utf-8") as file:
        content = file.read()
except FileNotFoundError:
    print("可以创建默认文件")
except OSError as error:
    print(f"其他文件错误：{error}")
```

`FileNotFoundError` 是 `OSError` 的子类。如果先写 `except OSError`，后面的 `FileNotFoundError` 就永远不会被执行。

### 4.4 捕获异常对象

使用 `as` 可以<mark>读取异常对象</mark>：

```python
try:
    count = int(user_input)
except (TypeError, ValueError) as error:
    print(f"转换失败：{error}")
```

异常对象通常用于记录日志或补充上下文；面向用户时，应根据业务提供清晰提示，而不是无条件暴露底层错误文字。

## 6. `else` 和 `finally`

`else` 只在 `try` 中没有异常时执行：

```python
try:
    value = parse_value(text)
except ValueError:
    value = None
else:
    print("解析成功")
```

`finally` 无论是否发生异常都会执行，适合释放资源或执行必须完成的清理：

```python
handle = None
try:
    handle = open("record.txt", encoding="utf-8")
    content = handle.read()
finally:
    if handle is not None:
        handle.close()
```

后续文件课程会介绍 `with`，它通常能更清晰地完成同类资源管理。

## 7. 什么时候处理异常

异常应该在“能够做出正确决定”的边界处理。

```text
底层函数：发现错误并抛出有意义的异常
        ↓
业务层：决定是否转换成业务错误
        ↓
入口/API：决定如何向用户展示错误
```

例如，底层解析函数可以抛出 `ValueError`；命令行入口可以把它转换成提示文字；API 层可以转换成 HTTP 错误。底层函数不应该为了打印而吞掉异常，因为它不知道调用者想如何处理。

## 8. 自定义异常和异常边界

当调用者需要区分业务错误时，可以定义自定义异常：

```python
class InvalidRecordError(ValueError):
    """记录内容不符合业务规则。"""

def validate_content(content: str) -> None:
    if not content.strip():
        raise InvalidRecordError("记录内容不能为空")
```

自定义异常不是为了让错误名字更复杂，而是让调用者能够精确捕获：

```python
try:
    validate_content(user_input)
except InvalidRecordError as error:
    print(f"输入无效：{error}")
```

继承 `ValueError` 表示它仍然属于“值不合法”这一大类；调用者既可以捕获具体的 `InvalidRecordError`，也可以捕获更宽泛的 `ValueError`。

### 8.1 空的异常类有什么作用

下面的类体只有 `pass`：

```python
class InvalidRecordError(ValueError):
    pass
```

它看起来没有内容，但这个类定义本身创建了一个新的异常类型。可以把它理解为给一类错误起了一个 Python 可以识别的名字：

```text
ValueError
└── InvalidRecordError
```

`pass` 表示这个类暂时没有增加额外方法或属性。它自动继承 `ValueError` 的行为，因此可以创建、抛出和捕获。

定义异常类和产生异常是两个动作：

```python
class InvalidRecordError(ValueError):
    pass

error = InvalidRecordError("记录内容不能为空")
raise error
```

实际代码通常直接写成：

```python
raise InvalidRecordError("记录内容不能为空")
```

括号中的文字是异常消息，可以在捕获后通过 `str(error)` 读取。

### 8.2 自定义异常如何被调用

异常类通常不是像普通函数一样由调用者直接调用，而是在错误发生时由底层函数抛出，再由上层捕获：

```python
class InvalidRecordError(ValueError):
    pass

def validate_content(content: str) -> None:
    if not content.strip():
        raise InvalidRecordError("记录内容不能为空")

try:
    validate_content("   ")
except InvalidRecordError as error:
    print(f"输入错误：{error}")
```

执行过程是：

```text
validate_content("   ")
        ↓
创建 InvalidRecordError("记录内容不能为空")
        ↓ raise
跳出 validate_content
        ↓
except InvalidRecordError 捕获
        ↓
打印输入错误
```

如果没有匹配的 `except`，异常会沿调用链继续向上传播；最终仍无人处理时，程序会终止并显示 traceback。

`RecordNotFoundError` 的使用方式相同：底层可以把 `IndexError` 转换成它，上层通过 `except RecordNotFoundError` 处理。

### 8.3 为什么不直接使用普通异常

如果所有错误都使用 `ValueError`，调用者无法仅凭异常类型区分不同业务问题。使用自定义类型后可以精确处理：

```python
try:
    process_record(record)
except InvalidRecordError:
    show_input_error()
except RecordNotFoundError:
    show_not_found_error()
```

所以空异常类的价值不是提供新的算法，而是提供稳定的分类标签和调用边界。

## 9. 重新抛出和异常链

如果当前层只能补充上下文，不能真正解决错误，可以使用 `raise` 继续抛出：

```python
try:
    value = int(text)
except ValueError:
    raise ValueError("年龄字段必须是整数")
```

更好的写法通常保留原始原因：

```python
try:
    value = int(text)
except ValueError as error:
    raise ValueError("年龄字段必须是整数") from error
```

`from error` 会<mark>建立异常链</mark>。traceback 会同时显示“当前层的解释”和“原始异常”，便于定位真正原因。

## 10. 设计异常处理时的常见错误

### 捕获过宽

`except Exception` 会把很多本来应该暴露的编程错误一起捕获。除非你在明确的最外层边界记录日志并返回统一错误，否则应捕获具体异常。

### 只打印不处理

```python
try:
    save_record(record)
except OSError as error:
    print(error)
```

打印后程序可能继续使用一个并未保存成功的状态。应该根据业务决定返回失败、重试、转换异常或终止。

### 把异常当作正常分支滥用

异常适合表示异常情况，不应把所有正常查询结果都设计成异常。

## 11. 运行课程代码

完整示例：

```bash
python code/python/lesson_01_exceptions.py
```

## 12. 课后作业

作业和课程示例放在同一个文件中：`code/python/lesson_01_exceptions.py`。文件上半部分是可以直接运行的课程示例，下半部分从 `# ===== 课后作业：书签收藏 =====` 开始，是需要自己完成的练习。

作业要求：

1. 定义并使用 `InvalidBookmarkError` 和 `DuplicateBookmarkError`；
2. 实现 `add_bookmark`：标题不能为空，URL 必须使用 `http://` 或 `https://`，且不能重复；
3. 实现 `open_bookmark`：按标题返回 URL，找不到时抛出查找类异常；
4. 在 `homework()` 中自行组织成功、重复、无效和找不到四种调用，并使用合适的 `try/except/else` 处理；
5. 注意保存到列表中的标题和 URL 应去掉首尾空白。

运行：

```bash
python code/python/lesson_01_exceptions.py
```

## 13. 验收问题

1. 异常和普通返回值有什么区别？
2. 异常没有在当前函数处理时会发生什么？
3. 为什么应该优先捕获具体异常？
4. `else` 和 `finally` 分别什么时候执行？
5. 自定义异常解决了什么问题？
6. `raise ... from error` 为什么有价值？
