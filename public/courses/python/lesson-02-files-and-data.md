# 第二课：文件、路径和数据转换

第一课的记录保存在列表里，程序结束后数据就消失了。本课学习如何把数据保存到文件，并在下次运行时读回来。

本课不把“文件读写”当成一个需要记住的命令，而是逐个理解 Python 提供的对象、方法、参数和返回值：`pathlib.Path` 表示路径，文件对象负责读写，`json` 负责在文本和 Python 数据之间转换。

## 学习目标

完成本课后，你应当能够：

- 说明 `pathlib` 模块和 `Path` 类分别是什么；
- 使用 `Path` 创建路径、查询路径状态和组合子路径；
- 使用文件对象读写指定编码的文本；
- 解释 `json.dumps`、`json.loads`、`json.dump` 和 `json.load` 的区别；
- 处理文件不存在、JSON 格式错误和数据结构错误；
- 把文件读写放在独立函数中，而不是散落在业务代码里。

## 1. `pathlib` 模块和 `Path` 类

### 1.1 模块和类

`pathlib` 是 Python 标准库中的路径处理模块，不需要额外安装。它提供了面向对象的路径操作。

```python
from pathlib import Path
```

- `pathlib`：模块名；
- `Path`：模块中的类；
- `Path(...)`：创建一个表示路径的对象。

路径对象不是文件内容，也不是已经打开的文件。它只是告诉程序“某个文件或目录在哪里”。

```python
path = Path("data/records.json")
print(type(path))  # <class 'pathlib.PosixPath'> 或 WindowsPath
print(path)        # data/records.json
```

在 macOS/Linux 上通常是 `PosixPath`，在 Windows 上通常是 `WindowsPath`。代码使用 `Path`，就不需要自己判断路径分隔符。

### 1.2 `Path` 的输入和输出

`Path` 可以接收字符串、已有的路径对象或其他实现路径协议的对象，返回一个新的 `Path` 对象：

```python
Path("data")
Path("data") / "records.json"
Path.cwd()
Path.home()
```

| 写法 | 输入 | 返回值 | 含义 |
| --- | --- | --- | --- |
| `Path("data")` | 路径字符串 | `Path` | 创建相对路径 |
| `Path.cwd()` | 无 | `Path` | 当前工作目录 |
| `Path.home()` | 无 | `Path` | 当前用户目录 |
| `path / "file.txt"` | 路径对象和名称 | `Path` | 组合子路径 |

当前工作目录是“执行 Python 命令时所在的目录”，不一定是 Python 文件所在的目录：

```python
from pathlib import Path

print(Path.cwd())
print(Path("data/records.json"))
```

执行命令时所在位置不同，`Path("data/records.json")` 代表的实际位置也可能不同。这是相对路径最常见的陷阱。

### 1.3 使用 `/` 组合路径

不要使用字符串拼接路径：

```python
# 不推荐：依赖斜杠，容易产生重复或缺少分隔符
path = "data/" + "records.json"
```

使用 `Path` 的 `/` 运算符：

```python
data_dir = Path("data")
record_path = data_dir / "records.json"
```

这里的 `/` 不是做数学除法，而是 `Path` 定义的运算。输入是一个 `Path` 和一个路径片段，输出是新的 `Path`；原来的 `data_dir` 不会被修改。

还可以连续组合：

```python
project_dir = Path("life-manager")
record_path = project_dir / "data" / "records.json"
```

### 1.4 查询路径状态

以下方法都返回布尔值，不会创建文件或目录：

```python
path.exists()    # 路径是否存在
path.is_file()   # 是否存在且是普通文件
path.is_dir()    # 是否存在且是目录
```

例如：

```python
path = Path("data/records.json")

if not path.exists():
    print("文件还没有创建")
elif not path.is_file():
    print("这个路径不是普通文件")
```

这几个方法通常返回 `False`，而不是在路径不存在时抛出异常。因此它们适合做“是否初始化”的判断。

### 1.5 读取路径信息

```python
path = Path("data/records.json")

print(path.name)       # records.json
print(path.stem)       # records
print(path.suffix)     # .json
print(path.parent)     # data
print(path.parts)      # ('data', 'records.json')
```

这些属性返回路径的一部分：

| 属性 | 返回值 | 示例 |
| --- | --- | --- |
| `name` | 文件名字符串 | `records.json` |
| `stem` | 不含扩展名的名称 | `records` |
| `suffix` | 最后一个扩展名 | `.json` |
| `parent` | 父目录 `Path` | `data` |
| `parts` | 路径片段元组 | `("data", "records.json")` |

### 1.6 创建目录

`mkdir` 创建目录。它的几个常用参数是：

```python
path.mkdir(parents=True, exist_ok=True)
```

- `parents=False`：默认值；父目录不存在时失败；
- `parents=True`：父目录不存在时一并创建；
- `exist_ok=False`：默认值；目录已存在时抛出 `FileExistsError`；
- `exist_ok=True`：目录已存在时不报错。

保存文件前通常这样确保父目录存在：

```python
record_path = Path("data/life/records.json")
record_path.parent.mkdir(parents=True, exist_ok=True)
```

注意：`mkdir` 创建的是目录，不是文件；它不会自动创建 `records.json`。

## 2. 文件对象和 `with`

### 2.1 `Path.open` 的输入和输出

```python
path = Path("notes.txt")
file = path.open("r", encoding="utf-8")
```

`Path.open` 的常用参数：

| 参数 | 作用 |
| --- | --- |
| `mode="r"` | 读取文本，文件必须存在 |
| `mode="w"` | 写入文本，不存在则创建，存在则覆盖 |
| `mode="a"` | 追加文本，不存在则创建 |
| `encoding="utf-8"` | 指定文本编码 |
| `newline` | 控制换行转换，初学阶段通常使用默认值 |

返回值是文件对象。文件对象提供 `read`、`readline`、`readlines`、`write` 和 `close` 等方法。

### 2.2 为什么要使用 `with`

直接打开文件后，必须保证最终调用 `close()`：

```python
file = path.open("r", encoding="utf-8")
try:
    text = file.read()
finally:
    file.close()
```

`with` 把这个资源释放过程写得更清楚：

```python
with path.open("r", encoding="utf-8") as file:
    text = file.read()
```

进入 `with` 时得到文件对象，离开代码块时自动关闭文件，即使代码块中抛出异常也会执行清理。`as file` 得到的是文件对象，不是字符串路径。

### 2.3 读取文本

文件对象的 `read` 返回字符串：

```python
with Path("notes.txt").open("r", encoding="utf-8") as file:
    content = file.read()

print(type(content))  # str
```

读取方法的差别：

- `read()`：读取剩余全部内容，返回 `str`；
- `readline()`：读取一行，返回 `str`；
- `readlines()`：读取所有行，返回 `list[str]`；
- 直接 `for line in file`：逐行读取，适合较大文件。

`Path` 也提供简写方法：

```python
content = Path("notes.txt").read_text(encoding="utf-8")
```

它返回文本字符串，并在内部负责打开和关闭文件。需要控制模式或逐行处理时，使用 `open` 更明确。

### 2.4 写入文本

文件对象的 `write` 接收字符串，返回实际写入的字符数：

```python
with Path("notes.txt").open("w", encoding="utf-8") as file:
    count = file.write("今天跑步\n")

print(count)
```

`write` 不会自动添加换行。`mode="w"` 会覆盖原文件，所以保存重要数据时必须清楚自己是否允许覆盖。

简写形式：

```python
Path("notes.txt").write_text("今天跑步\n", encoding="utf-8")
```

它返回写入的字符数。

## 3. `json` 模块：文本和 Python 数据的转换

### 3.1 JSON 是什么

JSON 是一种文本格式，可以表达：对象、数组、字符串、数字、布尔值和 `null`。

```json
[
  {"content": "跑步", "kind": "health"}
]
```

JSON 文本不是 Python 列表本身。它需要经过解析才能变成 Python 对象。

### 3.2 `json.dumps`：Python 对象转字符串

```python
import json

records = [{"content": "跑步", "kind": "health"}]
text = json.dumps(records, ensure_ascii=False, indent=2)
```

`json.dumps` 的输入是可被 JSON 表达的 Python 对象，返回值是 `str`：

```python
print(type(text))  # str
print(text)
```

常用参数：

- `ensure_ascii=False`：保留中文，而不是转换成 `\u` 形式；
- `indent=2`：使用 2 格缩进，方便阅读和查看 Git diff；
- `sort_keys=True`：按键排序，适合需要稳定输出的场景。

不是所有 Python 对象都能直接转换：`Path`、自定义类和大多数日期对象需要先转换为字符串或字典。

### 3.3 `json.loads`：字符串转 Python 对象

```python
text = '[{"content": "跑步", "kind": "health"}]'
records = json.loads(text)

print(type(records))       # list
print(type(records[0]))    # dict
```

`json.loads` 的输入是 JSON 字符串，返回对应的 Python 对象。格式不合法时抛出 `json.JSONDecodeError`：

```python
try:
    json.loads("不是 JSON")
except json.JSONDecodeError as error:
    print(f"解析失败：{error}")
```

### 3.4 `dump`/`load`：直接和文件对象配合

`dumps` 和 `loads` 中的 `s` 表示 string，它们处理字符串；`dump` 和 `load` 直接处理文件对象：

```python
with Path("records.json").open("w", encoding="utf-8") as file:
    json.dump(records, file, ensure_ascii=False, indent=2)

with Path("records.json").open("r", encoding="utf-8") as file:
    records = json.load(file)
```

四个函数的区别：

| 函数 | 输入 | 输出 | 用途 |
| --- | --- | --- | --- |
| `dumps` | Python 对象 | JSON 字符串 | 对象转文本 |
| `loads` | JSON 字符串 | Python 对象 | 文本转对象 |
| `dump` | Python 对象和文件对象 | `None` | 对象直接写文件 |
| `load` | 文件对象 | Python 对象 | 文件直接读对象 |

## 4. 把文件读写封装成存储函数

业务代码不应该到处出现 `open` 和 `json.loads`。可以先设计两个函数：

```python
import json
from pathlib import Path


def save_records(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_records(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"记录文件不是有效 JSON：{path}") from error

    if not isinstance(raw, list):
        raise ValueError("记录文件的顶层结构必须是数组")

    records: list[dict[str, str]] = []
    for position, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"第 {position} 条记录必须是对象")
        content = item.get("content")
        kind = item.get("kind")
        if not isinstance(content, str) or not isinstance(kind, str):
            raise ValueError(f"第 {position} 条记录缺少有效 content 或 kind")
        records.append({"content": content, "kind": kind})
    return records
```

这里有三个边界：

1. 文件不存在：第一次运行时可以视为“还没有记录”，返回空列表；
2. JSON 无法解析：文件已经存在，但内容损坏，应转换为清晰的 `ValueError`；
3. JSON 可以解析但结构不符合约定：仍然需要校验，不能直接把未知数据交给业务层。

## 5. 运行实验

运行配套代码：

```bash
python code/python/lesson_02_files_and_data.py
```

然后检查示例创建的 JSON 文件。观察：

1. 父目录不存在时，`mkdir(parents=True, exist_ok=True)` 如何创建目录；
2. 文件中的中文是否保持可读；
3. JSON 数组对应 Python 的 `list`，JSON 对象对应 Python 的 `dict`；
4. 再次运行时，程序是否能读取之前保存的记录。

可以手工把 JSON 改成下面几种内容，再运行 `load_records` 观察区别：

```text
不是 JSON
```

```json
{"content": "只有一个对象"}
```

```json
[{"content": 123, "kind": "health"}]
```

## 6. 课后练习

作业代码位于 `code/python/lesson_02_files_and_data.py` 的下半部分，场景改为“学习资料收藏”，不要求重复实现上面的生活记录存储。

1. 实现 `save_resource(path, resource)`：校验 `title` 和 `url`，创建父目录，并将一个字典保存为 JSON 对象；
2. 实现 `load_resource(path)`：处理文件不存在、无效 JSON、顶层类型错误和字段类型错误；
3. 实现 `append_learning_log(path, message)`：使用追加模式向 UTF-8 文本文件写入一行；
4. 在 `homework()` 中保存并读取一条学习资料，追加两条学习日志并读取日志；
5. 观察 `FileNotFoundError`、`InvalidResourceError` 和由 `JSONDecodeError` 转换来的 `ValueError` 的区别；
6. 说明 `read_text`/`write_text` 与 `open`/`close` 的关系，以及为什么 `json.loads` 不能直接接收 `Path`。

## 7. 验收问题

1. `Path("data") / "records.json"` 的输入和输出分别是什么？
2. `exists()`、`is_file()` 和 `is_dir()` 的区别是什么？
3. `mkdir(parents=True, exist_ok=True)` 中两个参数分别解决什么问题？
4. 为什么推荐使用 `with path.open(...) as file`？
5. `dumps`、`loads`、`dump` 和 `load` 的区别是什么？
6. 文件不存在、JSON 格式错误和字段格式错误为什么应该区分处理？
7. `save_records` 为什么应该负责创建父目录，而不是要求调用者提前手工创建？
