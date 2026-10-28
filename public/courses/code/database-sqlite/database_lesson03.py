import sqlite3
from pathlib import Path


DATABASE = Path(__file__).parent / "database_lesson01.sqlite3"


with sqlite3.connect(DATABASE) as connection:
    connection.row_factory = sqlite3.Row

    # ====================
    # 课程示例 1：修改一条记录
    # ====================
    connection.execute(
        "UPDATE books SET author = ? WHERE title = ?",
        ("刘慈欣", "三体"),
    )

    # ====================
    # 课程示例 2：删除一条记录
    # ====================
    # 这条语句暂时注释掉，避免每次运行都删除数据。
    # connection.execute("DELETE FROM books WHERE title = ?", ("三体",))

    rows = connection.execute(
        "SELECT id, title, author FROM books ORDER BY id"
    ).fetchall()

    print("当前书籍：")
    for row in rows:
        print(f"编号：{row['id']}，书名：{row['title']}，作者：{row['author']}")


# ====================
# 课后作业
# ====================

# TODO 作业 1：把“小王子”的作者修改为你指定的文字。
# 提示：UPDATE books SET ... WHERE title = ?
with sqlite3.connect(DATABASE) as connection:
    connection.execute("UPDATE books SET author = ? WHERE title = ?", ("MYY", "小王子"))

# TODO 作业 2：查询修改后的“小王子”，确认 UPDATE 生效。
    rows = connection.execute("SELECT author FROM books WHERE title = ?", ("小王子",))
    for row in rows:
        print(row[0])
# TODO 作业 3：删除“置身事内”，先确认 DELETE 语句中的 WHERE 条件。
# 提示：完成后再次运行 SELECT，确认它不再出现。
    connection.execute("DELETE FROM books WHERE title = ?", ("置身事内", ))

# TODO 作业 4：用长注释解释为什么 UPDATE 和 DELETE 通常必须写 WHERE。
# 作业答案：
# 因为更新和删除需要明确操作对象是哪些具体条目，否则会删除和更新所有的行

