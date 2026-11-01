# 第5课:FastAPI 连接 SQLite

## 1. FastAPI 和数据库的分工

FastAPI 负责接收请求和返回响应，SQLite 负责保存数据：

```text
POST /items
  -> FastAPI 解析请求体
  -> Python 执行 INSERT
  -> SQLite 保存记录
  -> FastAPI 返回新记录
```

## 2. 创建表

```python
connection.execute(
    "CREATE TABLE IF NOT EXISTS items ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "content TEXT NOT NULL)"
)
```

`IF NOT EXISTS` 表示表已经存在时不重复创建。

## 3. 查询和插入

查询使用 `SELECT`：

```python
rows = connection.execute(
    "SELECT id, content FROM items ORDER BY id"
).fetchall()
```

插入使用 `INSERT`：

```python
connection.execute(
    "INSERT INTO items (content) VALUES (?)",
    (item.content,),
)
```

`?` 是 SQL 占位符。用户输入应该作为第二个参数传入，不能直接拼接到 SQL 字符串中，这样更安全。

## 4. `with sqlite3.connect(...)`

```python
with sqlite3.connect(DATABASE) as connection:
    ...
```

这种写法会管理连接和事务：代码正常结束时提交修改，出现异常时回滚。离开 `with` 代码块后连接也会关闭。

当前项目的 `SQLiteStore` 也使用 `sqlite3.connect`，但它把连接保存在 Store 对象中，负责更多表和会话逻辑。

## 5. 当前练习

练习文件：`code/fastapi/05-sqlite.py`

启动：

```bash
cd fastapi
python code/fastapi/05-sqlite.py
```

打开 `http://127.0.0.1:8004/docs`，按顺序：

1. 用 `POST /items` 创建几条事项。
2. 用 `GET /items` 查询全部事项。
3. 用 `GET /items/{item_id}` 查询某一条事项。
4. 查询不存在的 ID，观察 `404`。
5. 查看练习目录中新生成的 `study.sqlite3` 文件。
