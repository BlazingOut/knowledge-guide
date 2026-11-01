"""第七课示例与作业：工程 Python——日志、配置、命令行和测试。

本文件是生活记录命令行应用：把第二课（文件存储）、第三课（数据模型）、
第四课（入口结构）和本课（日志、配置、命令行）串成一个可运行的小程序。
配套测试在 test_lesson_07_engineering_python.py。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_RECORDS_PATH = Path("/tmp/life-manager/records.json")


# ===== 数据模型（第三课） =====

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


# ===== 存储（第二课） =====

def save_records(path: Path, records: list[LifeRecord]) -> None:
    """把生活记录保存为格式化的 UTF-8 JSON 文件。"""
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
    logger.info("已保存 %d 条记录到 %s", len(records), path)


def load_records(path: Path) -> list[LifeRecord]:
    """读取生活记录 JSON 文件；文件不存在时返回空列表。"""
    if not path.exists():
        logger.warning("记录文件不存在：%s，按空列表处理", path)
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
    logger.info("已读取 %d 条记录", len(records))
    return records


# ===== 业务（第三课） =====

def add_record(records: list[LifeRecord], record: LifeRecord) -> LifeRecord:
    """添加记录；相同内容的记录只允许存在一条。"""
    if any(item.content == record.content for item in records):
        raise ValueError(f"记录已经存在：{record.content}")
    records.append(record)
    logger.info("已添加记录：%s", record.summary())
    return record


def find_records(
    records: list[LifeRecord],
    kind: str | None = None,
    limit: int = 20,
) -> list[LifeRecord]:
    """按类型过滤并限制条数；kind 为 None 时不过滤。"""
    matched = records if kind is None else [r for r in records if r.kind == kind]
    return matched[:limit]


# ===== 配置（环境变量） =====

def records_path_from_env() -> Path:
    """记录文件路径来自环境变量，未设置时使用默认路径。"""
    return Path(os.environ.get("LIFE_RECORDS_PATH", str(DEFAULT_RECORDS_PATH)))


def log_level_from_env() -> str:
    """日志级别来自环境变量，未设置时默认 INFO。"""
    return os.environ.get("LOG_LEVEL", "INFO").upper()


def setup_logging(level: str) -> None:
    """配置根日志器的级别和输出格式。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("日志级别：%s", level)


# ===== 命令行入口（第四课 + 本课） =====

def build_parser() -> argparse.ArgumentParser:
    """构造带子命令的命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="life-records",
        description="生活记录命令行应用",
    )
    parser.add_argument("--version", action="version", version="life-records 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="添加一条记录")
    add_parser.add_argument("content", help="记录内容")
    add_parser.add_argument("--kind", default="other", help="记录类型")
    add_parser.add_argument("--done", action="store_true", help="标记为已完成")

    list_parser = sub.add_parser("list", help="列出记录")
    list_parser.add_argument("--kind", default=None, help="只显示指定类型")
    list_parser.add_argument("--limit", type=int, default=20, help="最多显示条数")
    return parser


def main(argv: list[str] | None = None) -> int:
    """程序入口：解析参数、读取配置、分发到子命令，返回退出码。"""
    args = build_parser().parse_args(argv)
    setup_logging(log_level_from_env())
    path = records_path_from_env()
    logger.info("命令：%s，存储路径：%s", args.command, path)

    if args.command == "add":
        records = load_records(path)
        record = add_record(records, LifeRecord(args.content, args.kind, args.done))
        save_records(path, records)
        print("已添加：", record.summary())
        return 0

    if args.command == "list":
        records = find_records(load_records(path), kind=args.kind, limit=args.limit)
        for record in records:
            print(record.summary())
        logger.info("共显示 %d 条", len(records))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
