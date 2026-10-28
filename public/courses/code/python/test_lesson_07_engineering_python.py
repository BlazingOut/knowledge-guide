"""第七课测试：pytest 单元测试、fixture、集成测试和 mock。

运行：python -m pytest code/python/test_lesson_07_engineering_python.py
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lesson_07_engineering_python import (
    LifeRecord,
    add_record,
    find_records,
    load_records,
    main,
    save_records,
)


# ===== 单元测试：不接触文件系统 =====

def test_add_record_appends() -> None:
    records: list[LifeRecord] = []
    record = add_record(records, LifeRecord("跑步", "health"))
    assert record in records
    assert len(records) == 1


def test_add_record_rejects_duplicate() -> None:
    records = [LifeRecord("跑步", "health")]
    with pytest.raises(ValueError):
        add_record(records, LifeRecord("跑步", "health"))


def test_life_record_validation() -> None:
    with pytest.raises(ValueError):
        LifeRecord("  ", "health")
    with pytest.raises(ValueError):
        LifeRecord("跑步", "")


# ===== fixture：准备数据并注入配置 =====

@pytest.fixture
def records_file(tmp_path, monkeypatch):
    """把记录存储指向临时文件，并注入环境变量；测试结束后自动清理。"""
    path = tmp_path / "records.json"
    save_records(
        path,
        [
            LifeRecord("读书", "learning", completed=True),
            LifeRecord("跑步", "health"),
        ],
    )
    monkeypatch.setenv("LIFE_RECORDS_PATH", str(path))
    return path


def test_load_records_roundtrip(records_file) -> None:
    """集成测试：写入的文件能原样读回来。"""
    records = load_records(records_file)
    assert len(records) == 2
    assert records[0].content == "读书"
    assert records[0].completed is True


# ===== 集成测试：走完整 CLI 流程 =====

def test_main_add_then_list(records_file, capsys) -> None:
    assert main(["add", "写代码", "--kind", "work"]) == 0
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "写代码" in out
    assert "[work]" in out


def test_main_list_filters_by_kind(records_file, capsys) -> None:
    main(["list", "--kind", "health"])
    out = capsys.readouterr().out
    assert "跑步" in out
    assert "读书" not in out


# ===== mock：替换外部依赖 =====

def test_main_add_uses_save_records(records_file) -> None:
    """mock 示例：用 patch 替换 save_records，验证 main 调用了它，
    同时证明测试不依赖真正写文件。"""
    with patch("lesson_07_engineering_python.save_records") as fake_save:
        code = main(["add", "整理笔记", "--kind", "learning"])
    assert code == 0
    fake_save.assert_called_once()


# ===== 课后作业：为功能补充测试 =====
# 完成下面的 TODO 测试，并删除 @pytest.mark.skip 所在行后全部通过。

@pytest.mark.skip(reason="课后作业：完成 TODO 后移除本行")
def test_find_records_limits() -> None:
    """请完成：构造 3 条记录，find_records(limit=2) 只返回前 2 条。"""
    raise NotImplementedError


@pytest.mark.skip(reason="课后作业：完成 TODO 后移除本行")
def test_main_list_handles_empty_file(tmp_path, monkeypatch, capsys) -> None:
    """请完成：存储文件不存在时，list 命令应正常返回 0，且输出为空。"""
    raise NotImplementedError


@pytest.mark.skip(reason="课后作业：完成 TODO 后移除本行")
def test_add_record_stores_stripped_content() -> None:
    """请完成：LifeRecord 会清理首尾空白，验证 add_record 存的是清理后的内容。"""
    raise NotImplementedError
