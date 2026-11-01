"""第三课示例与作业：类、数据建模和类型标注。"""

from __future__ import annotations

from dataclasses import dataclass, field


# ===== 课程示例：生活记录 =====

@dataclass
class LifeRecord:
    content: str
    kind: str = "other"
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


def find_by_kind(records: list[LifeRecord], kind: str) -> LifeRecord | None:
    for record in records:
        if record.kind == kind:
            return record
    return None


def main() -> None:
    records = [
        LifeRecord(" 跑步 ", " HEALTH "),
        LifeRecord("读书", "learning", completed=True),
    ]
    for record in records:
        print(record.summary())
    print("找到 health：", find_by_kind(records, "health"))
    print("找到 shopping：", find_by_kind(records, "shopping"))


# ===== 课后作业：阅读清单 =====

@dataclass
class Book:
    title: str
    author: str
    finished: bool = False

    def __post_init__(self) -> None:
        # TODO：清理 title 和 author，并拒绝空标题。
        pass


@dataclass
class ReadingList:
    name: str
    books: list[Book] = field(default_factory=list)

    def add(self, book: Book) -> None:
        # TODO：如果已有相同标题的书，抛出 ValueError。
        # TODO：否则把 book 加入 books。
        pass

    def find(self, title: str) -> Book | None:
        # TODO：清理 title，找到后返回 Book，找不到返回 None。
        return None


def homework() -> None:
    """完成 TODO 后取消注释并运行。"""
    reading = ReadingList("今年想读")
    backup = ReadingList("备用清单")
    book = Book(" 人类简史 ", " 尤瓦尔·赫拉利 ")

    # TODO：把 book 加入 reading，并打印 reading.find("人类简史")。
    # TODO：尝试添加同标题书籍并捕获 ValueError。
    # TODO：向 backup 添加另一本书，证明两个列表互不影响。
    print(reading, backup)


if __name__ == "__main__":
    main()
