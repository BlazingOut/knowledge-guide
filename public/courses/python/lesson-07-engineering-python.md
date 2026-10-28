# 第七课：工程 Python——日志、配置、命令行和测试

前六课把生活记录从"字典 → 类 → 模块 → 语言工具"一步步搭了起来。本课是阶段 1 的收尾：把数据模型、存储、命令行拼成一个**可运行、可测试**的命令行应用，并补上工程化的四个零件——日志、配置、命令行入口、测试。本课不引入新的语法，而是回答一个问题：**代码怎么变成程序**。

写脚本和写程序是两回事。脚本用 `print` 排查问题、把路径写死在代码里、靠 `input()` 交互；程序要能交付给别人用：日志可以分级开关、配置不写死、参数通过命令行传入、改了代码有测试兜底。本课把这四件事逐个讲清楚。

**学习目标：**

1. 能说出 `print` 和 `logging` 的区别，配置日志级别和输出格式；
2. 能通过环境变量注入配置（存储路径、日志级别），并解释配置为什么不能写死在代码里；
3. 能用 `argparse` 写出带子命令的命令行程序，理解入口 `main()` 和退出码；
4. 能用 pytest 写单元测试和集成测试，用 fixture 准备和清理数据；
5. 能解释 mock 的作用，用 `unittest.mock.patch` 替换外部依赖；
6. 能读懂 traceback、会用 `breakpoint()`，并解释"最小复现"的意义；
7. 能说出重构的原则，以及为什么"测试是重构的安全网"。

## 1. 一个脚本是怎么长成程序的

先对比脚本和程序的差别：

| | 脚本 | 程序 |
| --- | --- | --- |
| 排查问题 | `print` 到处打 | 日志：有级别、有时间、可开关 |
| 路径和参数 | 写死在代码里 | 环境变量配置 + 命令行参数 |
| 交互方式 | `input()` 一问一答 | 参数一次传齐，可被脚本调用 |
| 改动风险 | 改一处怕坏一处 | 测试兜底，跑一遍就知道 |

本课的生活记录应用就是"程序"的形态：`add`/`list` 两个子命令、存储路径来自环境变量、日志按级别输出、配套 pytest 测试。它同时是前六课所有知识的落点。

## 2. 日志：从 `print` 到 `logging`

### 2.1 `print` 的问题

排查问题最原始的方式是到处 `print`。它有三个明显的缺点：

- **没有级别**：调试信息和错误信息混在一起，无法只保留重要的；
- **不能整体开关**：上线时要删掉或注释掉所有 `print`；
- **没有时间**：看不出问题发生在什么时候，也就看不出先后顺序。

`logging` 标准库解决这三件事。

### 2.2 日志级别

`logging` 把日志按严重程度分成五级：

| 级别 | 什么时候用 |
| --- | --- |
| `DEBUG` | 调试细节，正常运行时不希望看到 |
| `INFO` | 常规流程：命令、读写、保存了多少条 |
| `WARNING` | 有问题但程序还能继续（如文件不存在按空处理） |
| `ERROR` | 操作失败，需要人处理 |
| `CRITICAL` | 程序无法继续，即将退出 |

设置级别后，**低于该级别的日志不会被输出**。开发时调到 `DEBUG`，运行时调 `INFO` 或 `WARNING`，不用改代码。

### 2.3 `basicConfig` 和输出格式

```python
def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
```

运行程序后，日志长这样——时间、级别、来源、消息都有：

```text
2026-10-22 17:23:09,150 INFO __main__: 日志级别：INFO
2026-10-22 17:23:09,150 WARNING __main__: 记录文件不存在：\tmp\life-manager\records.json，按空列表处理
2026-10-22 17:23:09,151 INFO __main__: 已保存 1 条记录到 \tmp\life-manager\records.json
```

注意日志消息和用户看到的结果是分开的：日志走 stderr，`print` 的结果走 stdout。日志是给"运行和维护程序的人"看的，`print` 的结果是给"使用程序的人"看的。

### 2.4 模块级 logger

模块里用 `logging.getLogger(__name__)` 取 logger，名字会带上模块路径：

```python
logger = logging.getLogger(__name__)
logger.info("已保存 %d 条记录到 %s", len(records), path)
```

`%(name)s` 会显示 `lesson_07_engineering_python`，多模块项目里一眼能看出日志来自哪个文件。消息用 `%d`、`%s` 占位而不是 f-string，是日志的推荐写法：只有这条日志真正要输出时才做字符串拼接，性能更好。

## 3. 配置：环境变量和默认值

### 3.1 为什么配置不能写死

记录文件存到哪、日志级别调到哪，这些是**运行环境**决定的，不是代码逻辑决定的。写死在代码里的坏处：换一台机器就要改代码、重发版本；不小心把本机路径提交到仓库，还会影响别人。

### 3.2 `os.environ.get` 加默认值

```python
def records_path_from_env() -> Path:
    return Path(os.environ.get("LIFE_RECORDS_PATH", "/tmp/life-manager/records.json"))


def log_level_from_env() -> str:
    return os.environ.get("LOG_LEVEL", "INFO").upper()
```

`os.environ.get(name, default)` 在环境变量没设置时返回默认值。这样程序**没有配置也能跑**（用默认值），需要改变时不用动代码：

```powershell
$env:LIFE_RECORDS_PATH = "D:\life\records.json"
$env:LOG_LEVEL = "DEBUG"
python code/python/lesson_07_engineering_python.py list
```

配置规则：**代码决定"怎么处理"，环境变量决定"处理谁、在哪里、多详细"**。存储路径、日志级别、服务地址这类值都应该来自配置。

## 4. 命令行参数和程序入口

### 4.1 `argparse` 基本用法

`argparse` 是标准库的命令行解析工具。生活记录应用有两个子命令：`add` 和 `list`：

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="life-records", description="生活记录命令行应用")
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="添加一条记录")
    add_parser.add_argument("content", help="记录内容")          # 位置参数
    add_parser.add_argument("--kind", default="other", help="记录类型")  # 可选参数
    add_parser.add_argument("--done", action="store_true", help="标记为已完成")
    return parser
```

- **位置参数** `content`：必须按顺序给；
- **可选参数** `--kind`、`--done`：带名字给，`--done` 是开关（有就是 `True`）；
- 子命令让一个程序像有多个入口：`add` 和 `list` 各自有自己的参数。

使用效果：

```bash
python code/python/lesson_07_engineering_python.py add "跑步" --kind health
python code/python/lesson_07_engineering_python.py list --kind learning
python code/python/lesson_07_engineering_python.py --help
```

参数解析错误或 `--help` 时，argparse 会自动打印提示并退出，不需要手写。

### 4.2 `main()` 和退出码

第四课讲过 `__name__ == "__main__"`。工程化的入口还要多做两件事——接收参数、返回退出码：

```python
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- `main(argv)` 接收参数列表，让测试可以**直接调用 main 而不真的打开命令行**（本课测试就是这么做的）；
- 返回 `int` 退出码：`0` 表示成功，非 `0` 表示失败，这样程序可以被别的脚本调用、由调用方判断成功与否；
- `raise SystemExit(main())` 把退出码交给操作系统。

## 5. 测试：pytest

### 5.1 为什么需要测试

程序会不断修改：加功能、修 bug、重构。每一次修改都可能弄坏已有的功能，**测试就是防止"改坏了不知道"**。写好测试后，改完代码跑一遍，绿了才放心——这比"自己点一遍"可靠得多。

### 5.2 单元测试：不接触文件系统

pytest 的约定：文件名以 `test_` 开头，测试函数名以 `test_` 开头，断言用 `assert`：

```python
def test_add_record_rejects_duplicate() -> None:
    records = [LifeRecord("跑步", "health")]
    with pytest.raises(ValueError):
        add_record(records, LifeRecord("跑步", "health"))
```

上面的测试不读写任何文件，只验证 `add_record` 的业务规则——这是单元测试：测一个函数、一类规则，快且隔离。`pytest.raises(ValueError)` 断言"调用时抛出了 `ValueError`"。

### 5.3 fixture：准备和清理

测试需要数据：临时文件、环境变量、初始记录。pytest 的 fixture 负责准备，测试结束后自动清理：

```python
@pytest.fixture
def records_file(tmp_path, monkeypatch):
    """把记录存储指向临时文件，并注入环境变量；测试结束后自动清理。"""
    path = tmp_path / "records.json"
    save_records(path, [LifeRecord("读书", "learning", completed=True), LifeRecord("跑步", "health")])
    monkeypatch.setenv("LIFE_RECORDS_PATH", str(path))
    return path
```

- `tmp_path`：pytest 内置 fixture，提供每个测试独立的临时目录；
- `monkeypatch.setenv`：设置环境变量，测试结束自动还原；
- 自定义 fixture 把"准备临时存储"这一套逻辑抽出来，多个测试共用。

测试函数只要在参数里写上 fixture 名，pytest 就会自动传入：

```python
def test_load_records_roundtrip(records_file) -> None:
    records = load_records(records_file)
    assert len(records) == 2
```

### 5.4 单元测试 vs 集成测试

| | 单元测试 | 集成测试 |
| --- | --- | --- |
| 测什么 | 单个函数、单条规则 | 多个部分协作（如完整 CLI 流程） |
| 依赖 | 不碰文件、网络 | 用真实文件、真实调用链 |
| 速度/稳定性 | 快、稳定 | 慢一点、更接近真实 |

生活记录应用的集成测试直接调用 `main(["add", "写代码"])`，走完"解析参数 → 读文件 → 加记录 → 写文件 → 打印"的全流程，再检查输出：

```python
def test_main_add_then_list(records_file, capsys) -> None:
    assert main(["add", "写代码", "--kind", "work"]) == 0
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "写代码" in out
```

`capsys` 是 pytest 内置 fixture，用来捕获程序打印到屏幕的内容。

### 5.5 mock：替换外部依赖

集成测试会真的读写文件。有些依赖（外部 API、网络、数据库）在测试时不应该真的发生——这时用 mock 把它替换掉。`unittest.mock.patch` 可以临时替换模块里的函数：

```python
from unittest.mock import patch

def test_main_add_uses_save_records(records_file) -> None:
    """用 patch 替换 save_records，验证 main 调用了它，但不真正写文件。"""
    with patch("lesson_07_engineering_python.save_records") as fake_save:
        code = main(["add", "整理笔记", "--kind", "learning"])
    assert code == 0
    fake_save.assert_called_once()
```

`patch("模块.函数名")` 在 `with` 块内用假对象替换真实函数，块结束时自动还原。`fake_save.assert_called_once()` 验证"main 确实调用了保存"。**mock 的适用边界**：替换"外部世界的副作用"（网络、磁盘、时间），而不是替换自己的业务逻辑——把业务逻辑也 mock 掉，测试就失去意义了。

### 5.6 运行 pytest

```bash
python -m pytest code/python/test_lesson_07_engineering_python.py -q
```

`-q` 只显示摘要。全部通过时输出 `7 passed, 3 skipped`（3 个跳过的是课后作业，见第 10 节）。

## 6. 排错：traceback、断点、最小复现

### 6.1 读懂 traceback

traceback 的读法在第一课讲过：**从下往上读**。最下面是异常类型和消息，往上每一段是"谁调用了谁"。程序报错时先看最下面的异常类型（`ValueError` 还是 `TypeError`），再沿调用链找到真正出问题的那一行。

### 6.2 断点：`breakpoint()`

在可疑位置放 `breakpoint()`，运行到那里会进入 `pdb` 交互调试器：

```python
def add_record(records, record):
    breakpoint()   # 运行到这里暂停，进入 pdb
    ...
```

常用命令：`n`（执行下一行）、`p 变量名`（打印变量）、`c`（继续运行）、`q`（退出）。`breakpoint()` 在生产代码里不要保留，它是调试工具。

### 6.3 最小复现

"程序崩了"时，第一步不是猜，而是**把问题缩小到最小复现**：去掉无关参数、无关分支，直到能用几行代码稳定地重现同一个错误。最小复现有两个作用：

- 缩小了排查范围，错误原因更容易暴露；
- **最小复现本身就是测试的雏形**——把它写成 `test_` 函数，修好之后它就成了回归测试，防止问题再出现。

## 7. 代码质量和重构

### 7.1 好代码的原则

生活记录应用里的函数各有单一职责：

| 函数 | 职责 |
| --- | --- |
| `LifeRecord` | 数据模型和校验 |
| `load_records` / `save_records` | 存储 |
| `add_record` / `find_records` | 业务规则 |
| `build_parser` / `main` | 入口和分发 |
| `records_path_from_env` / `log_level_from_env` | 配置 |

每个函数只做一件事，名字说清楚它做什么。**判断标准：给函数起名字时，如果名字里要出现"和"，多半职责不单一。**

### 7.2 重构：不改行为地调整结构

重构是在**不改变程序行为**的前提下调整代码结构：提取重复代码、拆开过长的函数、换掉难懂的名字。因为行为不变，所以重构前后测试应该都是绿的——**测试就是重构的安全网**：没有测试，谁也不敢动代码；有了测试，重构完跑一遍就知道有没有改坏。

## 8. 真实场景：把前六课串成一个应用

本课的代码文件 `code/python/lesson_07_engineering_python.py` 就是一个完整的命令行生活记录应用，前六课的内容都在里面：

```text
第二课 文件与 JSON        save_records / load_records
第三课 类与类型标注        LifeRecord
第四课 入口结构            main() / __name__ == "__main__"
第五课 语言工具            存储和业务函数的复用
第六课 装饰器              （pytest 的 @pytest.fixture 就是装饰器）
本课   日志、配置、命令行    logging / 环境变量 / argparse
```

加上配套的 `test_lesson_07_engineering_python.py`，这就是阶段 1 的产出：**一个可运行、可测试的命令行小程序**。运行一次完整的添加和查看：

```bash
python code/python/lesson_07_engineering_python.py add "跑步" --kind health
python code/python/lesson_07_engineering_python.py add "读书" --kind learning --done
python code/python/lesson_07_engineering_python.py list
```

结果会先打印日志，再打印用户可见的记录：

```text
已添加： [health] 跑步（未完成）
已添加： [learning] 读书（已完成）
[health] 跑步（未完成）
[learning] 读书（已完成）
```

## 9. 运行课程代码

首次运行测试前安装 pytest：

```bash
python -m pip install pytest
```

运行命令行应用：

```bash
python code/python/lesson_07_engineering_python.py add "跑步" --kind health
python code/python/lesson_07_engineering_python.py list
python code/python/lesson_07_engineering_python.py --help
```

运行测试：

```bash
python -m pytest code/python/test_lesson_07_engineering_python.py -q
```

预期输出 `7 passed, 3 skipped`——示例测试全部通过，3 个课后作业测试默认跳过，不影响演示。

## 10. 课后作业：为功能补充测试

作业在测试文件 `code/python/test_lesson_07_engineering_python.py` 的下半部分，是三个被 `@pytest.mark.skip` 跳过的测试函数。完成 TODO 并删除 `@pytest.mark.skip` 所在行后，它们应该全部通过。

作业要求：

1. 完成 `test_find_records_limits`：构造 3 条记录，验证 `find_records(limit=2)` 只返回前 2 条；
2. 完成 `test_main_list_handles_empty_file`：存储文件不存在时，`list` 命令应返回 `0`，且输出为空；
3. 完成 `test_add_record_stores_stripped_content`：`LifeRecord` 会清理首尾空白，验证 `add_record` 存储的是清理后的内容；
4. 全部完成后运行测试，预期输出 `10 passed`，并用自己的话解释每个测试测的是哪条规则。

## 11. 验收问题

1. `print` 和 `logging` 的区别是什么？日志的五个级别分别什么时候用？
2. 配置为什么要通过环境变量注入？`os.environ.get(name, default)` 里的默认值起什么作用？
3. `argparse` 的位置参数、可选参数和子命令分别解决什么问题？
4. `main()` 为什么要接收参数并返回退出码？
5. 单元测试和集成测试的区别是什么？各举本课的一个例子。
6. fixture 解决什么问题？`tmp_path`、`monkeypatch`、`capsys` 分别做什么？
7. mock 的适用边界是什么？什么时候不该用 mock？
8. traceback 应该从哪边开始读？最小复现为什么是测试的雏形？
9. 为什么说"测试是重构的安全网"？

## 12. 面试高频考点

- 日志级别怎么选、为什么不直接用 `print`、日志和用户输出的区别。
- 配置管理：环境变量注入 + 默认值，"配置不写死在代码里"的原因。
- 命令行程序：argparse 参数类型、子命令、退出码的意义、`main(argv)` 为什么可测试。
- pytest：`test_` 约定、`assert`、`pytest.raises`、fixture（`tmp_path`、`monkeypatch`、`capsys`）、单元 vs 集成。
- mock：`unittest.mock.patch` 的用法和适用边界（替换外部副作用，不替换业务逻辑）。
- 排错流程：traceback 阅读、`breakpoint()`、最小复现；重构与测试的关系。
