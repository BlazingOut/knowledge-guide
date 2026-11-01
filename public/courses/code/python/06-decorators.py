"""第六课示例与作业：装饰器。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps


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


def log_call(func):
    """装饰器示例：调用前打印参数，调用后打印返回值。"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}，参数：{args} {kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} 返回：{result}")
        return result

    return wrapper


@log_call
def add_record(records: list[LifeRecord], content: str, kind: str) -> LifeRecord:
    record = LifeRecord(content, kind)
    records.append(record)
    return record


def log_elapsed(label: str):
    """装饰器工厂示例：带标签，调用前打印开始，调用后打印结束。"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"开始：{label}")
            result = func(*args, **kwargs)
            print(f"结束：{label}")
            return result

        return wrapper

    return decorator


@log_elapsed("查找记录")
def find_record(records: list[LifeRecord], content: str) -> LifeRecord | None:
    for record in records:
        if record.content == content:
            return record
    return None


def main() -> None:
    print("== 函数是对象：赋值和 __name__ ==")
    f = add_record
    print("f 的名字：", f.__name__)

    print("== 装饰器：日志 ==")
    records: list[LifeRecord] = []
    add_record(records, "整理笔记", "learning")
    print("当前记录数：", len(records))

    print("== functools.wraps 保留函数名 ==")
    print("add_record.__name__：", add_record.__name__)

    print("== 装饰器工厂 ==")
    print("查找结果：", find_record(records, "整理笔记"))
    print("未找到：", find_record(records, "不存在的记录"))


# ===== 课后作业：提醒服务的装饰器 =====
# 场景沿用第四课的提醒清单，不要求重复实现上面的生活记录示例。

@dataclass
class Reminder:
    title: str
    done: bool = False

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("提醒标题不能为空")


def count_calls(func):
    """请完成：统计函数调用次数的装饰器。"""
    # TODO：在 wrapper 外层维护一个计数器（使用 nonlocal）。
    # TODO：每次调用后打印 f"{func.__name__} 被调用 {n} 次"。
    # TODO：使用 functools.wraps 保留原函数信息。
    raise NotImplementedError


def retry(max_times: int = 3):
    """请完成：调用失败时重试的装饰器工厂。"""
    # TODO：返回一个装饰器，包装函数。
    # TODO：调用原函数，成功则返回结果；抛出异常则重试，最多 max_times 次。
    # TODO：最后一次仍然失败时，把异常继续抛出。
    # TODO：使用 functools.wraps 保留原函数信息。
    raise NotImplementedError


def add_reminder(reminders: list[Reminder], title: str) -> Reminder:
    reminder = Reminder(title)
    reminders.append(reminder)
    return reminder


def homework() -> None:
    """完成 TODO 后取消注释并运行。"""
    reminders: list[Reminder] = []

    # TODO：用 counted_add = count_calls(add_reminder) 包装 add_reminder，
    #       调用三次，观察打印输出。
    # TODO：定义一个"前两次抛出异常、第三次成功"的函数，
    #       用 @retry(3) 装饰它并调用，观察它最终成功。
    # TODO：打印被装饰函数的 __name__，确认没有被改写。
    print("请完成第六课作业")


if __name__ == "__main__":
    main()
