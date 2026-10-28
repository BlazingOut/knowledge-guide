# 第一课：数据库、表和记录

这条课程线用于补充 FastAPI 练习所需要的数据库知识。示例使用 SQLite，因为它不需要单独启动数据库服务器，并且当前 Life Manager 项目也使用 SQLite。


这一课的重点是 SQL 语法，不是 Python 语法。

## 1. 数据库是什么

数据库是一个负责长期保存和组织数据的软件系统。程序退出后，数据库中的数据仍然存在。

当前项目中的数据库文件包括：

```text
data/lifestyle.sqlite3
data/memory_index.sqlite3
data/domains/*.sqlite3
```

`.sqlite3` 文件就是 SQLite 数据库的保存文件。

## 2. 表、行和列

可以把数据库表先理解成一张结构化表格：

| id | content | kind |
| --- | --- | --- |
| 1 | 买咖啡 | shopping |
| 2 | 给妈妈打电话 | life |

- 表（table）：一类数据的集合，例如 `items`
- 行（row / record）：一条具体数据
- 列（column）：数据的一个属性
- 主键（primary key）：唯一标识一行数据的列，通常叫 `id`

## 3. SQL 是什么

SQL（结构化查询语言）是交给数据库执行的语言。Python 负责打开数据库、把语句送进去、取回结果；语句里面要做什么，由 SQL 描述。后面的 `CREATE`、`INSERT`、`SELECT` 都是 SQL，不是 Python 的关键字。

它和 Python 不是同一类语言，主要有四个特点。

**第一，SQL 声明要什么结果，不写获得结果的步骤。** 用 Python 从一批书里取出书名，得自己写循环：

```python
titles = []
for book in books:
    titles.append(book["title"])
```

同一件事用 SQL 写成：

```sql
SELECT title
FROM books
```

这里没有“从第一本走到最后一本”。你只说明两件事：结果里要 `title` 这一列，数据来自 `books` 这张表。先读哪一行、要不要用索引，由数据库决定。所以 SQL 不能按 Python 的习惯理解成“程序会从上往下逐行处理我的列表”。

**第二，一条语句处理的是一整张表，结果通常仍是一张表。** `SELECT title FROM books` 得到的不是一个字符串，而是零行、一行或很多行，每一行都有 `title` 这一列。就算只查出一本书，那也是“只有一行的表”，不是一个单独的 Python 变量。第 8 节里 `fetchall()` 返回多行，就是这个特点落到 Python 里的样子。

插入、修改、删除也是按表来的，不是先取出一个对象再改它的属性。本课的 `INSERT` 是往表里增加行。后面写到不带条件的修改和删除时，作用范围同样是整张表，而不是“当前这一行”；那一课会专门看漏写条件的后果。

**第三，句式是固定的，关键字和数据要分开。** `SELECT` 必须写在 `FROM` 前面。写成 `FROM books SELECT title` 不是换一种风格，而是语法错误。关键字的大小写不改变含义，`select` 和 `SELECT` 相同；本课把关键字写成大写，只是为了和表名、列名分开，容易读。

表里的文字用单引号，数字不加引号：

```sql
INSERT INTO books (title, author)
VALUES ('小王子', '圣埃克苏佩里')
```

`'小王子'` 是要存进表里的文字。`SELECT` 外面不加引号，它才是命令。在 Python 里，整句 SQL 经常放在双引号字符串中，SQL 内部的文字仍然用单引号，两层引号各管各的。

**第四，一种语句只做一类事。** 本课和后面几课用到的语句可以先分成三组：

```text
CREATE          定义表的结构，不负责写入某一行
INSERT、UPDATE、DELETE   增加、修改、删除行
SELECT          只读出结果，不改表里的数据
```

查询两次，表里的行还是那些行。要把新书放进去，必须再写 `INSERT`，不能靠 `SELECT` 顺便写入。Python 可以在一个函数里又查列表又 `append`；SQL 把这两件事分成不同的语句。

因此 SQL 不是用来替代 Python 的完整编程语言。循环、函数、业务上的先后步骤仍然写在 Python 里。SQL 负责把“对表做什么”说清楚。条件筛选、排序和一次修改哪些行，从第 2 课继续；这一课先会读上面这几种句子。

常见语句和它们的作用：

```text
CREATE  创建表
INSERT  插入数据
SELECT  查询数据
UPDATE  更新数据
DELETE  删除数据
```

## 4. Python 如何使用 SQLite

Python 通过标准库里的 `sqlite3` 模块操作 SQLite：

```python
import sqlite3
from pathlib import Path

DATABASE = Path(__file__).parent / "database_lesson01.sqlite3"

with sqlite3.connect(DATABASE) as connection:
    ...
```

- `import sqlite3`：导入 Python 自带的 SQLite 工具库。
- `Path(...)`：表示数据库文件的位置。
- `sqlite3.connect(DATABASE)`：连接数据库文件。如果文件不存在，SQLite 会创建它。
- `as connection`：把连接对象命名为 `connection`，后面用它执行 SQL。
- `with`：自动管理连接和事务。代码正常结束时提交修改，出现异常时回滚。

执行 SQL 的基本形式是：

```python
connection.execute("这里写 SQL")
```

`connection` 是 Python 对象，`execute` 是它提供的方法；括号里的字符串才是 SQL 语句。也就是说，Python 负责调用数据库，SQL 负责告诉数据库要做什么。

## 5. 逐句理解第一个 SQL 表

练习中的建表语句是：

```sql
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL
)
```

- `CREATE TABLE`：创建一张表。
- `IF NOT EXISTS`：如果这张表已经存在，就不要重复创建，也不要报错。
- `books`：表名。
- `id`、`title`、`author`：列名。
- `INTEGER`、`TEXT`：列的数据类型，分别表示整数和文字。
- `PRIMARY KEY`：主键，每一行的唯一标识。
- `AUTOINCREMENT`：插入新行时，`id` 自动递增。
- `NOT NULL`：这一列不允许为空。

## 6. 插入数据

```sql
INSERT INTO books (title, author)
VALUES (?, ?)
```

- `INSERT INTO books`：向 `books` 表插入数据。
- `(title, author)`：说明要填写哪些列。
- `VALUES`：后面跟着要写入的值。
- `?`：占位符，由 Python 单独传入真实值。

例如传入 `("小王子", "圣埃克苏佩里")`，数据库就会新增一行。`id` 不需要填写，因为它会自动生成。

## 6.1 `?` 占位符是什么

在下面这条 SQL 中：

```python
sql = "INSERT INTO books (title, author) VALUES (?, ?)"
values = ("小王子", "圣埃克苏佩里")
connection.execute(sql, values)
```

第一个 `?` 代表 `title` 的值，第二个 `?` 代表 `author` 的值。Python 会按照位置依次填入：

```text
第 1 个 ? <- "小王子"
第 2 个 ? <- "圣埃克苏佩里"
```

每个需要动态传入的值都要有一个占位符，所以两个值需要两个 `?`：

```python
"VALUES (?, ?)"       # 两个值
"VALUES (?)"          # 一个值
```

占位符不是 SQL 中固定代表某个具体内容的符号，而是执行时才填入的安全位置。不要把用户输入直接拼接进 SQL：

```python
# 不推荐：直接拼接文字
sql = f"SELECT * FROM books WHERE title = '{title}'"

# 推荐：使用占位符
sql = "SELECT * FROM books WHERE title = ?"
connection.execute(sql, (title,))
```

这样做可以避免 SQL 注入，也让数据库驱动正确处理字符串中的引号等特殊字符。

注意单个值的写法：

```python
(title,)
```

结尾的逗号很重要。`(title)` 只是加了括号，仍然是一个普通值；`(title,)` 才是只包含一个元素的元组。

## 6.2 一次插入多条数据

如果有多本书，可以使用 `executemany` 重复执行同一条 SQL：

```python
books = [
    ("百年孤独", "加西亚·马尔克斯"),
    ("活着", "余华"),
    ("额尔古纳河右岸", "迟子建"),
]

connection.executemany(
    "INSERT INTO books (title, author) VALUES (?, ?)",
    books,
)
```

这里 SQL 只写一遍，`books` 中的每个元组执行一次：

```text
第 1 次：第 1 个元组填入两个 ?
第 2 次：第 2 个元组填入两个 ?
第 3 次：第 3 个元组填入两个 ?
```

也可以写成一条 SQL 中的多组值：

```sql
INSERT INTO books (title, author)
VALUES (?, ?), (?, ?), (?, ?)
```

这种写法需要六个值，因此需要六个 `?`。学习和实际项目中，使用 `executemany` 往往更清楚。

它和 Python 的 `format` 有相似之处：都是把值放入某些位置。但 `?` 不是字符串格式化语法，不应该使用 `format` 或 f-string 替代，因为占位符由数据库驱动安全处理动态值。

## 7. 查询数据

```sql
SELECT id, title, author
FROM books
ORDER BY id
```

- `SELECT`：选择要读取的列。
- `FROM books`：从 `books` 表读取。
- `ORDER BY id`：按照 `id` 排序。
- `SELECT *`：表示选择全部列，但实际项目中通常明确写列名更清楚。

## 8. Python 如何拿到查询结果

```python
rows = connection.execute(sql).fetchall()
```

- `execute`：让数据库执行 SQL。
- `fetchall()`：取出全部查询结果。
- `fetchone()`：只取出一条结果。

数据库中的查询结果不是自动的 Python 字典，而通常是一行一行的结果。当前练习打印出来的 `(1, '小王子', '圣埃克苏佩里')` 就是一行记录。

## 9. 第一个练习

练习文件：`code/database-sqlite/database_lesson01.py`

运行：

```bash
python code/database-sqlite/database_lesson01.py
```

它会在 `code/database-sqlite/` 中创建 `database_lesson01.sqlite3`，创建 `books` 表，插入两条记录并查询出来。

跟着示例做：

1. 运行文件，观察输出。

课后作业：

1. 再插入一本你喜欢的书，只填写已经讲过的 `title` 和 `author`。
2. 修改 `SELECT` 语句，只查询 `title` 和 `author` 两列。
3. 把查询结果中的一行打印成更容易阅读的文字，例如：`书名：小王子，作者：圣埃克苏佩里`。
4. 再运行一次程序，观察为什么不会重复插入初始的两本书。

本课暂时不要求增加列、使用 `WHERE` 或使用 `ORDER BY`。这些会在后续课程中先讲清楚，再作为对应课程的作业。

完成作业后，可以把代码或运行结果发给我。我会先检查你的思路和错误，再给提示，不会直接跳过你的思考过程。
