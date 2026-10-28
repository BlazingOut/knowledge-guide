import sqlite3
from pathlib import Path


DATABASE = Path(__file__).parent / "database_lesson04.sqlite3"


with sqlite3.connect(DATABASE) as connection:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS people ("
        "id INTEGER PRIMARY KEY, "
        "name TEXT NOT NULL, "
        "age INTEGER)"
    )

    # 只在表还是空的时候放入两行，避免重复运行时主键冲突。
    if connection.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 0:
        connection.execute(
            "INSERT INTO people (id, name, age) VALUES (?, ?, ?)",
            (1, "小明", 25),
        )
        connection.execute(
            "INSERT INTO people (id, name, age) VALUES (?, ?, ?)",
            (2, "小红", 24),
        )

    # 列定义的六个位置：序号、列名、类型、是否非空、默认值、是否主键。
    columns = connection.execute("PRAGMA table_info(people)").fetchall()
    print("增加列之前或列已存在时的结构：")
    for column in columns:
        print(column)

    # column[1] 是列名。列已经加过时不能再次 ADD COLUMN。
    names = [column[1] for column in columns]
    if "nickname" not in names:
        connection.execute("ALTER TABLE people ADD COLUMN nickname TEXT")

    print("原有行的 nickname：")
    rows = connection.execute(
        "SELECT id, name, nickname FROM people ORDER BY id"
    ).fetchall()
    for row in rows:
        print(row)

    connection.execute(
        "UPDATE people SET nickname = ? WHERE id = ?",
        ("明明", 1),
    )

    print("填写一名用户的 nickname 之后：")
    rows = connection.execute(
        "SELECT id, name, nickname FROM people ORDER BY id"
    ).fetchall()
    for row in rows:
        print(row)

    print("增加列之后的结构：")
    for column in connection.execute("PRAGMA table_info(people)"):
        print(column)


# ====================
# 课后作业
# ====================

# TODO 作业 1：给 people 增加 city 列，类型是 TEXT。
# 先用 PRAGMA table_info 判断列名里是否已经有 city，没有再执行 ALTER TABLE。

# TODO 作业 2：查询 id、name、city。
# 用长注释说明：加列前已经存在的两行，city 为什么是 None。

# TODO 作业 3：用 UPDATE 给其中一行写下城市，再查询。
# 确认没有写城市的那一行仍然是 None，而不是空字符串。

# TODO 作业 4：从 PRAGMA table_info(people) 的结果里选一行。
# 用长注释按六个位置说明：序号、列名、类型、是否非空、默认值、是否主键。
