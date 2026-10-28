# 第五课：约束

第 4 课给列规定了类型。类型只说明这一格大致放什么，并不阻止两行使用同一个编号，也不阻止姓名这个位置空着。约束是写在表结构上的另一类规则：插入或修改违反规则时，数据库拒绝这一次写入，原来的行保持不变。

本课观察三种规则：主键、非空、唯一。外键要涉及两张表，放到多表那一课。查询空值的写法放到第 6 课；这里会插入 `NULL`，只为了看约束让不让它留下。

**学习目标：**

1. 能说出主键、`NOT NULL`、`UNIQUE` 各自拒绝什么样的行；
2. 能从 `sqlite3.IntegrityError` 的消息里看出是哪一种约束、哪一列没有通过；
3. 能说明 `NULL` 在 `UNIQUE` 列上可以出现多次，在主键和 `NOT NULL` 列上不行；
4. 能区分“让错误抛出来”和 `INSERT OR IGNORE` 把这次插入丢掉。

## 1. 规则写在表上

本课的表是：

```sql
CREATE TABLE people (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE
)
```

`PRIMARY KEY`、`NOT NULL`、`UNIQUE` 都写在列的类型后面。它们在建表时生效，不是插入时临时加上的条件。先放入一行合法数据：

```sql
INSERT INTO people (id, name, email)
VALUES (1, '小明', 'xiaoming@example.com')
```

后面每一节都在这行已经存在的前提下，再插入一行，看数据库拒绝什么。拒绝发生在 SQLite 执行语句的时候。Python 的 `execute` 没有先检查邮箱是否重复；检查失败后，SQLite 让这句 `execute` 抛出异常。

## 2. 主键

`id INTEGER PRIMARY KEY` 表示 `id` 用来区分每一行。表里已经有 `id` 为 `1` 的小明，再插入另一个 `id` 也是 `1` 的人：

```python
connection.execute(
    "INSERT INTO people (id, name, email) VALUES (?, ?, ?)",
    (1, "另一个", "a@example.com"),
)
```

SQLite 抛出 `sqlite3.IntegrityError`，消息是：

```text
UNIQUE constraint failed: people.id
```

`IntegrityError` 是完整性约束错误，也就是这行不符合表上的规则。消息里的 `people.id` 指出是 `people` 表的 `id` 列。SQLite 在这里说的是 `UNIQUE constraint`，因为主键首先要求这一列的值不重复；它没有另外写一句“主键错误”。看到列名是主键那一列，就可以判断这是主键冲突。

冲突的这一行不会留下。再查询 `people`，仍然只有原来的小明，不会出现姓名是“另一个”的人。

主键同时还不允许 `NULL`。本课的 `id` 是 `INTEGER PRIMARY KEY`，插入时不写 `id`，SQLite 会自己补一个还没有用过的整数。这是第 1 课已经见过的行为。所以正常插入既不会撞上已有编号，也不会把主键留空。要观察主键错误，就明确再写一次已经存在的 `id`。

## 3. 非空

`name TEXT NOT NULL` 表示 `name` 这一列必须有值。Python 里没有值写成 `None`，到 SQLite 里就是 `NULL`：

```python
connection.execute(
    "INSERT INTO people (id, name, email) VALUES (?, ?, ?)",
    (2, None, "b@example.com"),
)
```

错误消息是：

```text
NOT NULL constraint failed: people.name
```

这次点名的是 `NOT NULL`，列是 `people.name`。编号 `2` 并没有和已有主键重复，邮箱也是新的；被拒绝只是因为姓名这个位置没有值。空字符串 `""` 不是 `NULL`，它是一段长度为 0 的文字，`NOT NULL` 不会拒绝它。本课要观察的是 `None`，不要用空字符串代替。

`email` 这一列没有写 `NOT NULL`，所以邮箱可以暂时没有。下面两行都能够插入：

```python
(4, "小刚", None)
(5, "小丽", None)
```

两个邮箱都是 `NULL`，这不是非空约束的范围。下一节会看到，唯一约束也不把这两个 `NULL` 当成重复。

## 4. 唯一

`email TEXT UNIQUE` 表示有内容的邮箱不能重复。小明已经使用 `xiaoming@example.com`，再给小红写入同一个邮箱：

```python
connection.execute(
    "INSERT INTO people (id, name, email) VALUES (?, ?, ?)",
    (3, "小红", "xiaoming@example.com"),
)
```

错误消息是：

```text
UNIQUE constraint failed: people.email
```

它和主键冲突的消息是同一种句式。区别只在列名：`people.id` 是主键那一列，`people.email` 是另外加了 `UNIQUE` 的列。主键只能有一个，用来指出“哪一行”；`UNIQUE` 可以加在别的列上，用来表示“这一列的业务值也不能重复”。人的编号和人的邮箱是两件不同的事，所以分成两种约束。

`UNIQUE` 允许多个 `NULL`。小刚和小丽的邮箱都是 `None`，两次插入都成功。可以把它理解成：唯一约束只比较已经写下的值；没有值就没有一个可以判定为重复的邮箱。因此“邮箱可空，但写下的邮箱不能重复”正好是 `TEXT UNIQUE`，不要再给它加 `NOT NULL`。如果邮箱也必须填写，才在类型后面同时写上 `NOT NULL` 和 `UNIQUE`。

`UPDATE` 同样受这些规则约束。把小刚的邮箱改成小明已经使用的地址，也会得到 `people.email` 上的 `UNIQUE constraint failed`。本课的练习先看插入，修改只是同一套规则作用到已有的行。

## 5. 错误抛出和忽略这次插入

约束失败时，默认结果是语句中断，Python 收到 `IntegrityError`。调用方可以记录这个错误，也可以告诉使用者邮箱已经被注册。捕获它的写法和别的异常相同：

```python
try:
    connection.execute(
        "INSERT INTO people (id, name, email) VALUES (?, ?, ?)",
        (3, "小红", "xiaoming@example.com"),
    )
except sqlite3.IntegrityError as error:
    print(error)
```

`try` 里面只放可能违反约束的那一次 `execute`。`except` 只接 `sqlite3.IntegrityError`。表名写错、SQL 少了括号，属于语句本身写错，不会进这个分支。

有时重复执行脚本，只是想保证某一行存在，并不想因为那一行已经在表里就让程序停下来。SQLite 可以在插入语句里声明“违反约束就跳过这次插入”：

```python
cursor = connection.execute(
    "INSERT OR IGNORE INTO people (id, name, email) VALUES (?, ?, ?)",
    (1, "不会写入", "nope@example.com"),
)
print(cursor.rowcount)
```

`id` 为 `1` 的人已经存在，所以这次插入被忽略。`rowcount` 是 `0`，表示没有新行。原来那一行的姓名仍然是“小明”，不会被改成“不会写入”。`OR IGNORE` 只决定这次插入写不写进去，它不是 `UPDATE`。

练习里的示例要让你看见错误消息，所以使用普通 `INSERT`，并用 `try` 接住。示例开头放入小明时使用 `INSERT OR IGNORE`，是为了这个程序可以重复运行：第二次再放同一个 `id`，忽略即可，不必删库。作业里要观察的失败，不要写成 `OR IGNORE`，否则异常不会出现，消息也看不到。

## 6. 练习

练习文件：`code/database-sqlite/database_lesson05.py`。数据库是单独的 `database_lesson05.sqlite3`。

运行：

```bash
python code/database-sqlite/database_lesson05.py
```

示例先创建 `people` 并放入小明，再做两次会被拒绝的插入：姓名为 `None`，以及邮箱与小明相同。输出里应有两行错误，分别包含 `people.name` 上的 `NOT NULL constraint failed` 和 `people.email` 上的 `UNIQUE constraint failed`。

作业在文件后半，自己完成：

1. 再插入一个 `id` 为 `1` 的人，捕获 `IntegrityError`，确认消息里是 `people.id`。
2. 再插入一次姓名为 `None` 的行，确认消息里是 `NOT NULL` 和 `people.name`。
3. 再插入一次与小明相同的邮箱，确认消息里是 `UNIQUE` 和 `people.email`。
4. 用长注释回答：为什么两个邮箱都是 `NULL` 可以同时留下，两个相同的邮箱地址不行；主键和 `UNIQUE` 的错误消息都写着 `UNIQUE constraint failed` 时，怎样从列名判断是哪一种约束。
