# 第三课：类、数据建模和类型标注

第二课中的记录使用字典表示。字典适合快速组织数据，但字段名称是字符串，任何代码都可以随意修改它，数据规则也没有集中定义的位置。本课学习如何使用类和 `dataclass` 表达领域对象，并用类型标注说明函数的输入和输出。

本课的重点不是把所有代码都改成类，而是理解什么时候需要一个有明确结构和行为的数据对象，以及类型标注到底能做什么、不能做什么。

## 学习目标

完成本课后，你应当能够：

- 区分类、实例、属性和方法；
- 使用构造方法创建对象并维护对象状态；
- 解释组合和继承的区别，并优先选择合适的关系；
- 使用 `dataclass` 减少数据类的样板代码；
- 使用 `Enum` 表示有限的分类值；
- 为变量、参数、返回值和集合添加类型标注；
- 说明类型标注不会自动完成运行时校验。

## 1. 类和实例

### 1.1 类是什么

类是创建对象的定义。它可以描述对象有哪些数据，以及对象能够执行哪些操作。

```python
class LifeRecord:
    pass


record = LifeRecord()
print(type(record))
```

`class LifeRecord` 创建类，`LifeRecord()` 创建实例。类是结构定义，`record` 是根据这个定义创建出的具体对象。可以创建多个互相独立的实例。

### 1.2 `__init__` 和 `self`

通常在 `__init__` 中初始化对象属性：

```python
class LifeRecord:
    def __init__(self, content: str, kind: str):
        self.content = content
        self.kind = kind


record = LifeRecord("跑步", "health")
print(record.content)
```

`__init__` 接收创建实例时的参数，通常返回 `None`。`self` 表示当前实例；`self.content` 是当前对象的属性。调用 `record.describe()` 时，Python 会自动把 `record` 作为 `self` 传入。

### 1.3 方法和对象状态

方法是定义在类中的函数，可以读取或修改实例状态：

```python
class Counter:
    def __init__(self):
        self.value = 0

    def increase(self, amount: int = 1) -> None:
        self.value += amount


counter = Counter()
counter.increase()
counter.increase(2)
print(counter.value)  # 3
```

把数据和相关行为放在一起，比让外部代码到处修改字典字段更容易维护。

## 2. 数据校验和对象边界

类可以在创建对象时执行规则检查：

```python
class LifeRecord:
    def __init__(self, content: str, kind: str):
        content = content.strip()
        kind = kind.strip().lower()
        if not content:
            raise ValueError("记录内容不能为空")
        if not kind:
            raise ValueError("记录类型不能为空")
        self.content = content
        self.kind = kind
```

成功创建的对象就满足最基本的约束。注意：Python 不会因为属性写了 `str` 标注，就自动阻止后续代码执行 `record.content = 123`。类型标注和运行时校验是两件事。

## 3. 组合和继承

组合表示“一个对象拥有另一个对象”：

```python
class User:
    def __init__(self, name: str):
        self.name = name


class LifeManager:
    def __init__(self, owner: User):
        self.owner = owner
```

继承表示“某类是一种更具体的另一类”：

```python
class Notification:
    def send(self, message: str) -> str:
        raise NotImplementedError


class EmailNotification(Notification):
    def send(self, message: str) -> str:
        return f"email: {message}"
```

继承适合稳定的“是一种”关系；如果只是需要调用另一个对象的功能，优先考虑组合，不要为了复用几行代码就创建继承层次。

## 4. `dataclass`

### 4.1 基本用法

如果一个类主要保存数据，手写 `__init__`、`__repr__` 和比较逻辑会产生样板代码。`dataclass` 可以根据字段定义自动生成常用方法：

```python
from dataclasses import dataclass


@dataclass
class LifeRecord:
    content: str
    kind: str


record = LifeRecord(content="跑步", kind="health")
print(record)
```

`@dataclass` 会读取字段，并生成构造方法。字段标注同时说明构造参数的预期类型。

### 4.2 默认值和可变字段

有默认值的字段通常放在没有默认值的字段后面：

```python
@dataclass
class LifeRecord:
    content: str
    kind: str = "other"
    completed: bool = False
```

不要把列表直接作为默认值，因为不同实例可能共享同一个列表。使用 `field(default_factory=list)`：

```python
from dataclasses import dataclass, field


@dataclass
class Note:
    text: str
    tags: list[str] = field(default_factory=list)
```

`default_factory=list` 会在每次创建实例时调用 `list()`，得到独立列表。

### 4.3 `__post_init__` 和 `frozen`

`__post_init__` 会在 dataclass 自动生成的 `__init__` 完成后执行，适合清理和校验字段：

```python
@dataclass
class LifeRecord:
    content: str
    kind: str

    def __post_init__(self) -> None:
        self.content = self.content.strip()
        self.kind = self.kind.strip().lower()
        if not self.content:
            raise ValueError("记录内容不能为空")
```

`@dataclass(frozen=True)` 会禁止创建后直接修改字段，适合表示不可变值对象：

```python
@dataclass(frozen=True)
class Coordinate:
    latitude: float
    longitude: float
```

## 5. `Enum` 表示有限选项

如果 `kind` 只能是几个固定值，普通字符串容易出现拼写错误。可以使用 `Enum`：

```python
from enum import Enum


class RecordKind(str, Enum):
    HEALTH = "health"
    LEARNING = "learning"
    SHOPPING = "shopping"


kind = RecordKind.HEALTH
print(kind.value)  # health
```

`RecordKind.HEALTH` 是枚举成员，`.value` 是对应的字符串值。枚举成员和普通字符串仍然是不同概念。

## 6. 类型标注

### 6.1 参数、返回值和集合

```python
@dataclass
class LifeRecord:
    content: str
    kind: str


def summarize(record: LifeRecord) -> str:
    return f"[{record.kind}] {record.content}"


records: list[LifeRecord] = []
records.append(LifeRecord("跑步", "health"))
```

`record: LifeRecord` 表示参数预期是 `LifeRecord`，`-> str` 表示函数预期返回字符串，`list[LifeRecord]` 表示列表元素预期是该类型。

### 6.2 可选值

一个值可能不存在时，要把这种情况表达出来：

```python
def find_by_kind(records: list[LifeRecord], kind: str) -> LifeRecord | None:
    for record in records:
        if record.kind == kind:
            return record
    return None
```

返回值是 `LifeRecord | None`，调用者必须考虑找不到的情况。

### 6.3 类型标注不会自动校验

类型标注主要服务于阅读、IDE、静态检查器和重构工具。需要运行时校验时，要使用 `isinstance`、构造函数中的检查、`__post_init__` 或专门的数据校验库。

## 7. 运行课程代码

```bash
python code/python/lesson_03_classes_data_modeling.py
```

上半部分会创建并打印生活记录。下半部分作业包含 TODO，但默认不会被调用，因此课程示例仍然可以直接运行。

## 8. 课后作业：阅读清单

作业代码在同一个 Python 文件的下半部分，场景改为阅读清单，不要求重新实现上面的 `LifeRecord`。

需要完成：

1. 使用 `@dataclass` 完成 `Book`，字段为 `title: str`、`author: str`、`finished: bool`；
2. 在 `__post_init__` 中清理标题和作者，并拒绝空标题；
3. 完成 `ReadingList.add(book)`，拒绝相同标题的重复书籍；
4. 完成 `ReadingList.find(title)`，找到时返回 `Book`，找不到时返回 `None`；
5. 为 `ReadingList.books` 使用 `field(default_factory=list)`，确保不同阅读清单不会共享同一个列表；
6. 在 `homework()` 中创建两个阅读清单，证明它们的书籍互不影响。

## 9. 验收问题

1. 类和实例有什么区别？`self` 指向什么？
2. 为什么对象的校验逻辑可以放在 `__init__` 或 `__post_init__`？
3. 组合和继承分别表示什么关系？为什么通常优先考虑组合？
4. `field(default_factory=list)` 解决了什么问题？
5. `Enum` 的成员和它的 `.value` 有什么区别？
6. 类型标注能否阻止错误类型在运行时传入函数？如果不能，谁负责校验？
7. 为什么 `find` 的返回类型应该写成 `Book | None`？

