import sqlite3
from pathlib import Path


DATABASE = Path(__file__).parent / "01-tables-and-records.sqlite3"


with sqlite3.connect(DATABASE) as connection:
    connection.row_factory = sqlite3.Row

    # ====================
    # 课程示例 1：使用 WHERE 筛选作者
    # ====================
    rows = connection.execute(
        "SELECT title, author FROM books WHERE author = ?",
        ("刘慈欣",),
    ).fetchall()

    print("刘慈欣的书：")
    for row in rows:
        print(f"书名：{row['title']}，作者：{row['author']}")

    # ====================
    # 课程示例 2：使用 ORDER BY 排序
    # ====================
    rows = connection.execute(
        "SELECT id, title, author FROM books ORDER BY id DESC"
    ).fetchall()

    print("\n按照 id 从大到小：")
    for row in rows:
        print(dict(row))


# ====================
# 课后作业
# ====================

# TODO 作业 1：查询作者是“余华”的书。
# 提示：把上面的作者条件改成“余华”。
with sqlite3.connect(DATABASE) as connection:
    rows = connection.execute(
            "SELECT title FROM books WHERE author = ?",
            ("余华",),
        ).fetchall()
    for row in rows:
        print(row[0])
# TODO 作业 2：查询所有书，但只显示 title 和 author。
    rows = connection.execute("SELECT title, author FROM books")
    for row in rows:
        print(f"书名：{row[0]}, 作者：{row[1]}")
# TODO 作业 3：使用 ORDER BY，让书名按照 id 从小到大排列。
    rows = connection.execute("SELECT title, author FROM books ORDER BY id")
    for row in rows:
        print(f"书名：{row[0]}, 作者：{row[1]}")
# TODO 作业 4：用自己的话解释 WHERE 和 ORDER BY 的区别。
# 作业答案可以直接写成下面这样的长注释：
#
# 我的答案：
# WHERE 用来筛选符合条件的行，决定哪些记录会被查询出来。
# ORDER BY 用来排列已经查询出来的记录，决定它们显示的顺序。
