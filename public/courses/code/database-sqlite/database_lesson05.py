import sqlite3
from pathlib import Path

DATABASE = Path(__file__).parent / "database_lesson05.sqlite3"

with sqlite3.connect(DATABASE) as connection:
    # 课程示例：创建带约束的表
    connection.execute("CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE)")
    connection.execute("INSERT OR IGNORE INTO people (id, name, email) VALUES (?, ?, ?)", (1, "小明", "xiaoming@example.com"))

    # 课程示例：捕获约束错误
    try:
        connection.execute("INSERT INTO people (id, name, email) VALUES (?, ?, ?)", (2, None, "another@example.com"))
    except sqlite3.IntegrityError as error:
        print(f"NOT NULL 约束错误：{error}")

    try:
        connection.execute("INSERT INTO people (id, name, email) VALUES (?, ?, ?)", (3, "小红", "xiaoming@example.com"))
    except sqlite3.IntegrityError as error:
        print(f"UNIQUE 约束错误：{error}")

# ====================
# 课后作业
# ====================

# TODO 作业 1：尝试插入一个重复的 id，观察 PRIMARY KEY 错误。
# TODO 作业 2：尝试插入 name 为 None 的记录，观察 NOT NULL 错误。
# TODO 作业 3：尝试插入重复的 email，观察 UNIQUE 错误。
# TODO 作业 4：用长注释解释三个约束分别解决什么问题。
# 作业答案：
#
#
