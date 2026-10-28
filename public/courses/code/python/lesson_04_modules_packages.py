"""第四课示例与作业：模块、包与项目结构。"""

from __future__ import annotations

from dataclasses import dataclass, field


# ===== 课程示例：模块中的提醒模型和服务 =====

@dataclass
class Reminder:
    title: str
    done: bool = False

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("提醒标题不能为空")


def add_reminder(reminders: list[Reminder], reminder: Reminder) -> None:
    if any(item.title == reminder.title for item in reminders):
        raise ValueError(f"提醒已经存在：{reminder.title}")
    reminders.append(reminder)


def find_reminder(reminders: list[Reminder], title: str) -> Reminder | None:
    title = title.strip()
    for reminder in reminders:
        if reminder.title == title:
            return reminder
    return None


def main() -> None:
    reminders: list[Reminder] = []
    add_reminder(reminders, Reminder(" 提交学习记录 "))
    add_reminder(reminders, Reminder("阅读 Python 文档", done=True))
    print("提醒列表：", reminders)
    print("查找结果：", find_reminder(reminders, "提交学习记录"))
    print("未找到：", find_reminder(reminders, "不存在的提醒"))


# ===== 课后作业：提醒清单 =====

@dataclass
class ReminderList:
    name: str
    reminders: list[Reminder] = field(default_factory=list)

    def add(self, reminder: Reminder) -> None:
        # TODO：拒绝相同标题的提醒，否则加入 reminders。
        pass

    def find(self, title: str) -> Reminder | None:
        # TODO：清理 title，找到后返回 Reminder，找不到返回 None。
        return None


def format_reminders(reminders: list[Reminder]) -> str:
    """请完成：每条提醒输出一行，完成项标记为 [x]。"""
    # TODO：未完成使用 [ ]，完成使用 [x]，格式示例：[ ] 阅读文档
    raise NotImplementedError


def homework() -> None:
    first = ReminderList("今天")
    second = ReminderList("以后")

    # TODO：向 first 添加两条提醒，向 second 添加一条不同的提醒。
    # TODO：打印 format_reminders(first.reminders)。
    # TODO：查找存在和不存在的提醒。
    # TODO：尝试添加重复标题，并捕获 ValueError。
    # TODO：证明 first 和 second 的 reminders 是两个不同的列表。
    print(first, second)


if __name__ == "__main__":
    main()
