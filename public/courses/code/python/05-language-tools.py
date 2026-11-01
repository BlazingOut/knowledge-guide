"""第五课示例与作业：迭代器、生成器、上下文管理器。"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# ===== 课程示例：生活记录 =====

@dataclass
class LifeRecord:
    content: str
    kind: str
    completed: bool = False

    def __post_init__(self) -> None:
        self.content = self.content.strip()
        self.kind = self.kind.strip().lower()
        if not self.content:
            raise ValueError("记录内容不能为空")
        if not self.kind:
            raise ValueError("记录类型不能为空")

    def summary(self) -> str:
        state = "已完成" if self.completed else "未完成"
        return f"[{self.kind}] {self.content}（{state}）"


def save_records(path: Path, records: list[LifeRecord]) -> None:
    """将生活记录保存为格式化的 UTF-8 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = [
        {
            "content": record.content,
            "kind": record.kind,
            "completed": record.completed,
        }
        for record in records
    ]
    with path.open("w", encoding="utf-8") as file:
        json.dump(raw, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_records(path: Path) -> list[LifeRecord]:
    """读取生活记录 JSON 文件，返回 LifeRecord 列表。"""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    if not isinstance(raw, list):
        raise ValueError("记录文件的顶层结构必须是数组")
    records: list[LifeRecord] = []
    for position, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"第 {position} 条记录必须是对象")
        records.append(
            LifeRecord(item["content"], item["kind"], item.get("completed", False))
        )
    return records


def iter_records(path: Path) -> Iterator[LifeRecord]:
    """生成器示例：逐条读取记录，按需产出，不一次性构造完整列表。

    调用 iter_records(path) 时函数体不会立即执行，只有 for 循环或 next()
    索取下一条时，才会执行到下一个 yield。
    """
    for record in load_records(path):
        yield record


class RecordIter:
    """自定义迭代器示例：实现 __iter__ 和 __next__。"""

    def __init__(self, records: list[LifeRecord]) -> None:
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


class RecordBox:
    """自定义可迭代对象示例：实现 __iter__，每次遍历都返回新的迭代器。"""

    def __init__(self, records: list[LifeRecord] | None = None) -> None:
        self._records = list(records or [])

    def add(self, record: LifeRecord) -> None:
        self._records.append(record)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        # 每次返回一个新迭代器，所以同一个 box 可以反复遍历。
        return iter(self._records)


class Timer:
    """上下文管理器示例：进入时记录开始时间，退出时打印耗时。"""

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        elapsed = time.perf_counter() - self.start
        print(f"耗时：{elapsed:.3f} 秒")
        # 返回 False（不吞掉异常），让异常继续向外传播。
        return False


@contextmanager
def timer_alternative():
    """使用 @contextmanager 的等价写法：yield 前后分别是进入和退出逻辑。"""
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"耗时：{time.perf_counter() - start:.3f} 秒")


def main() -> None:
    path = Path("/tmp/life-manager-records/records.json")
    save_records(
        path,
        [
            LifeRecord("读书", "learning", completed=True),
            LifeRecord("跑步", "health"),
            LifeRecord("写代码", "work"),
        ],
    )

    print("== 迭代器：iter 和 next ==")
    records = load_records(path)
    iterator = iter(records)
    print(next(iterator).summary())
    print(next(iterator).summary())

    print("== 迭代器：取完抛出 StopIteration ==")
    small = [LifeRecord("买菜", "shopping")]
    it = iter(small)
    print(next(it).summary())
    try:
        next(it)
    except StopIteration:
        print("StopIteration：迭代器已取完")

    print("== 自定义迭代器 ==")
    for record in RecordIter(records):
        print(record.summary())

    print("== 自定义可迭代对象 ==")
    box = RecordBox(records)
    print("第一遍：", [record.content for record in box])
    print("第二遍：", [record.content for record in box])

    print("== 生成器：逐条读取记录 ==")
    for record in iter_records(path):
        print(record.summary())

    print("== 生成器：按需消费，可以提前停止 ==")
    count = 0
    for record in iter_records(path):
        if count >= 2:
            break
        print(record.summary())
        count += 1

    print("== 生成器：只能迭代一次 ==")
    once = iter_records(path)
    print("第一次：", [record.content for record in once])
    print("第二次：", [record.content for record in once])

    print("== 上下文管理器：计时 ==")
    with Timer():
        time.sleep(0.05)

    print("== 上下文管理器：@contextmanager 写法 ==")
    with timer_alternative():
        time.sleep(0.02)


# ===== 课后作业：学习日志 =====
# 这个场景使用文本日志文件，不要求重复实现上面的生活记录。


class StudyTimer:
    """请完成：记录学习耗时的上下文管理器。"""

    def __init__(self, label: str, log: list[tuple[str, float]]) -> None:
        # TODO：保存 label 和 log 列表，供 __exit__ 使用。
        pass

    def __enter__(self) -> "StudyTimer":
        # TODO：记录开始时间（time.perf_counter()），返回 self。
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # TODO：计算耗时（秒，保留三位小数），追加 (label, seconds) 到 log。
        # TODO：返回 False，不吞掉异常。
        raise NotImplementedError


def iter_log_lines(path: Path) -> Iterator[str]:
    """请完成：逐条读取学习日志文件的生成器。"""
    # TODO：用 with 打开 UTF-8 文本文件并逐行读取。
    # TODO：去掉每行首尾空白，跳过空行，产出其余每一行。
    # TODO：文件不存在时抛出 FileNotFoundError，让调用者知道问题。
    raise NotImplementedError


def homework() -> None:
    """完成 TODO 后取消注释并运行。"""
    path = Path("/tmp/life-manager-learning/log.txt")

    # TODO：用 path.write_text 写入两行日志（其中一行是空行）。
    # TODO：用 iter_log_lines(path) 打印逐条读取的日志。
    # TODO：用一个生成器对象连续 for 循环两次，观察第二次为什么没有输出。
    # TODO：用 StudyTimer 记录一次"作业用时"，time.sleep(0.02)，再打印 log 列表。
    print("请完成第五课作业")


if __name__ == "__main__":
    main()
