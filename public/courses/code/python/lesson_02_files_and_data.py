"""第二课示例与作业：文件、路径和数据转换。"""

import json
from pathlib import Path


# ===== 课程示例：生活记录 JSON 存储 =====

def save_records(path: Path, records: list[dict[str, str]]) -> None:
    """将生活记录保存为格式化的 UTF-8 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_records(path: Path) -> list[dict[str, str]]:
    """读取并校验生活记录；文件不存在时返回空列表。"""
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


def main() -> None:
    path = Path("/tmp/life-manager-records.json")
    records = [
        {"content": "晚上跑步", "kind": "health"},
        {"content": "读书", "kind": "learning"},
    ]
    save_records(path, records)
    print("保存位置：", path)
    print("读取结果：", load_records(path))


# ===== 课后作业：学习资料收藏 =====
# 这个场景使用字典和文本文件，不要求重复实现上面的生活记录存储。

class InvalidResourceError(ValueError):
    """学习资料的数据不符合要求。"""


def save_resource(path: Path, resource: dict[str, str]) -> None:
    """请完成：将一条资料保存成 JSON 文件。"""
    # TODO：title 和 url 必须是非空字符串，否则抛出 InvalidResourceError。
    # TODO：创建父目录，以 UTF-8 和缩进 2 格写入一个 JSON 对象。
    raise NotImplementedError


def load_resource(path: Path) -> dict[str, str]:
    """请完成：读取一条资料并校验其结构。"""
    # TODO：文件不存在时抛出 FileNotFoundError，不要返回 None。
    # TODO：把 JSONDecodeError 转换成 ValueError，并使用 raise ... from error。
    # TODO：顶层必须是 dict，且 title、url 必须是字符串；否则抛出 InvalidResourceError。
    raise NotImplementedError


def append_learning_log(path: Path, message: str) -> None:
    """请完成：向学习日志追加一行文字。"""
    # TODO：创建父目录，使用追加模式和 UTF-8 编码写入 message + "\n"。
    raise NotImplementedError


def homework() -> None:
    """请完成后再取消注释下面的调用，观察不同异常。"""
    resource_path = Path("/tmp/life-manager-learning/python.json")
    log_path = Path("/tmp/life-manager-learning/progress.log")
    resource = {"title": "Python pathlib", "url": "https://docs.python.org/3/library/pathlib.html"}

    # TODO：保存并读取 resource，打印读取结果。
    # TODO：追加两条学习日志，再读取日志文件并打印内容。
    # TODO：分别处理 FileNotFoundError、InvalidResourceError 和 ValueError。
    print("请完成第二课作业")


if __name__ == "__main__":
    main()
