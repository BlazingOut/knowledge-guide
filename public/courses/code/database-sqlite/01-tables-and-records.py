import sqlite3
from pathlib import Path

DATABASE = Path(__file__).parent / "01-tables-and-records.sqlite3"

with sqlite3.connect(DATABASE) as connection:
    connection.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL)")
    if connection.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        connection.execute("INSERT INTO books (title, author) VALUES (?, ?)", ("小王子", "圣埃克苏佩里"))
        connection.execute("INSERT INTO books (title, author) VALUES (?, ?)", ("置身事内", "兰小欢"))
    for row in connection.execute("SELECT id, title, author FROM books ORDER BY id").fetchall():
        print(row)


# TODO 作业 1：再插入一本书，只填写 title 和 author。
with sqlite3.connect(DATABASE) as connection:
  connection.execute("INSERT INTO books (title, author) VALUES ( ?, ?)", ("三体", "刘慈欣"))
# TODO 作业 2：把查询语句改为只查询 title 和 author 两列。
  rows = connection.execute("SELECT title, author FROM books ORDER BY id").fetchall()
# TODO 作业 3：把查询结果打印成容易阅读的文字。
  for row in rows:
    print(row)
# TODO 作业 4：再运行一次程序，观察初始数据不会重复插入。
"""
不会重复插入
"""
    
