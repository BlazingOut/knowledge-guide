# 第四课：数据类型和表结构

第 3 课的 `UPDATE` 改的是某一格里的值，表仍然是原来的那些列。这一课改的是表本身有哪些列：每一列准备放什么类型的数据，以及一张已经有行的表怎样再增加一列。

**学习目标：**

1. 能说明 `INTEGER`、`TEXT`、`REAL` 各自表示什么，并写出对应的 SQL 字面量；
2. 能用 `ALTER TABLE ... ADD COLUMN` 给已有的表增加一列，并知道原有行在新列上是什么；
3. 能读懂 `PRAGMA table_info` 返回的每一项；
4. 能在 Python 里执行上面两句 SQL，并重复运行程序时不因为列已经存在而中断。

## 1. 数据类型

`CREATE TABLE` 里每一列都要写两样东西：列名，以及这一列的数据类型。本课使用 SQLite 里最常见的三种：

```sql
id INTEGER
name TEXT
age INTEGER
```

| 类型        | 准备存放的数据 | SQL 里怎么写一个值 |
| --------- | ------- | ----------- |
| `INTEGER` | 整数      | `25`，不加引号   |
| `TEXT`    | 文字      | `'小明'`，用单引号 |
| `REAL`    | 带小数的数   | `19.9`，不加引号 |

插入一行时，值和类型按这个写法对应：

```sql
INSERT INTO people (id, name, age)
VALUES (1, '小明', 25);
```

`1` 和 `25` 是整数。`'小明'` 是文字。如果某一列是价格，类型写成 `REAL`，值就写成 `19.9`。这里的引号是 SQL 的写法，不是 Python 的字符串规则。整句 SQL 放进 Python 的双引号字符串时，文字外面仍然是单引号。

类型写在列上，是在声明这一列打算放哪一类数据。SQLite 对这个声明比较宽松：把整数 `123` 插进 `TEXT` 列，插入通常仍会成功，这一格被存成文字 `'123'`。MySQL 往往会拒绝明显对不上的值，或者按自己的规则转换。所以表结构里写了 `TEXT`，不等于别的类型一定写不进去。后面如果看到同一种插入在另一种数据库里结果不同，先确认类型检查是不是一样严。

`NULL` 不是这三种类型里的一个值。它表示这个位置没有值。下一节给旧行增加的新列，就会出现 `NULL`。怎样用 `IS NULL` 把它查出来，放到第 6 课。

## 2. 增加一列

表已经创建并且里面有行之后，列不是只能停在建表时的那几列。增加一列使用 `ALTER TABLE`：

```sql
ALTER TABLE people
ADD COLUMN nickname TEXT
```

`ALTER TABLE people` 指出要改的是 `people` 这张表。`ADD COLUMN` 是这次做的修改：增加列。后面的 `nickname TEXT` 与建表时的一列相同，先是列名，再是类型。

这条语句执行前，表里可以已经有这样两行：

```text
id  name  age
1   小明  25
2   小红  24
```

执行后再查询 `nickname`，这两行仍然在，新列是空的：

```text
id  name  age  nickname
1   小明  25
2   小红  24
```

命令行里空着的那一格，在 Python 里读出来是 `None`，在数据库里是 `NULL`：加列的时候这两行并没有昵称可写。之后插入的新行可以带上昵称，也可以继续不写。已经存在的某一行，要用第 3 课的 `UPDATE` 把昵称填进去，加列本身不会帮你填。

同一列不能加第二次。再执行一遍上面的 `ALTER TABLE`，SQLite 会报 `duplicate column name: nickname`。程序如果要重复运行，应先查看列定义，发现 `nickname` 已经存在就跳过这句。查看的方法是下一节的 `PRAGMA table_info`。

本课只用 `ADD COLUMN`。不在这里改某一列已经声明的类型，也不删除列。那些语句要么 SQLite 的写法和增加列不同，要么要重建整张表，等确实需要时再学。

## 3. 查看列定义

SQLite 用 `PRAGMA table_info` 查看一张表现在有哪些列。`PRAGMA` 是 SQLite 自己的命令，用来查看或调整数据库的状态；`table_info` 是其中用来看列定义的一项。括号里是表名：

```sql
PRAGMA table_info(people)
```

增加 `nickname` 之后，结果是四行，每行描述一列：

```text
0|id|INTEGER|0||1
1|name|TEXT|1||0
2|age|INTEGER|0||0
3|nickname|TEXT|0||0
```

竖线分开的六个位置是固定的：

| 位置    | 含义                         | 以 `name` 那一行为例         |
| ----- | -------------------------- | ---------------------- |
| 第 1 个 | 列的序号，从 0 开始                | `1`，表示第二列              |
| 第 2 个 | 列名                         | `name`                 |
| 第 3 个 | 数据类型                       | `TEXT`                 |
| 第 4 个 | 是否要求非空，`1` 表示是，`0` 表示可以没有值 | `1`，因为建表时写了 `NOT NULL` |
| 第 5 个 | 默认值；没有默认值时这里是空的            | 空                      |
| 第 6 个 | 是否是主键，`1` 表示是              | `0`                    |

对照 `id` 那一行：序号是 `0`，类型是 `INTEGER`，最后一个数字是 `1`，所以它是主键。`nickname` 是最后加进去的，序号是 `3`，类型是 `TEXT`，非空和主键两个标志都是 `0`，也没有默认值。因此旧行在这一列上是 `NULL`，而不是自动写成空字符串。

Python 里每一行就是一个有六个元素的元组，顺序和上表相同。打印出来如果只看到一串括号，就按这六个位置逐个读，而不是把它当成普通的数据行。

## 4. 在 Python 中执行

`ALTER TABLE` 和 `PRAGMA` 都是交给数据库的语句。Python 一侧仍然是第 1 课的 `connection.execute`，它没有一个叫 `alter` 的方法：

```python
connection.execute("ALTER TABLE people ADD COLUMN nickname TEXT")
columns = connection.execute("PRAGMA table_info(people)").fetchall()
```

第一句执行完没有查询结果，所以不必 `fetchall()`。第二句的结果是列定义，每一列一个元组，要用 `fetchall()` 取出来。

新列上的 `NULL` 在参数里写成 Python 的 `None`。例如新插入一个人、但还不写昵称：

```python
connection.execute(
    "INSERT INTO people (id, name, age, nickname) VALUES (?, ?, ?, ?)",
    (3, "小李", 30, None),
)
```

最后一个参数 `None` 进到 `nickname`，表里这一格就是 `NULL`。不要写成空字符串 `""`：那是长度为 0 的文字，和“没有值”不是同一种数据。

练习程序会多次运行。加列前先看 `table_info`，列名里已经有 `nickname` 就不再执行 `ALTER TABLE`：

```python
names = [column[1] for column in columns]
if "nickname" not in names:
    connection.execute("ALTER TABLE people ADD COLUMN nickname TEXT")
```

`column[1]` 就是上一节表格里的第 2 个位置：列名。这里用列名判断，是因为序号会随列的多少变化，列名才是这列的身份。

## 5. 练习

练习文件：`code/database-sqlite/database_lesson04.py`。它使用单独的 `database_lesson04.sqlite3`，不改前三课的书籍数据。

运行：

```bash
python code/database-sqlite/database_lesson04.py
```

示例会创建 `people`，插入小明和小红，打印当时的列定义，在缺少 `nickname` 时加上这一列，再查出这两行的昵称。第一次运行时两个昵称都是 `None`。示例接着把小明的昵称改成“明明”，再次查询。然后重新打印列定义，这时应能看到序号为 `3` 的 `nickname`。

文件后半是作业，需要自己完成：

1. 再增加一列 `city`，类型是 `TEXT`。加上之前先判断这列是否已经存在。
2. 查询 `id`、`name`、`city`，写出旧的两行在 `city` 上为什么是 `None`。
3. 用 `UPDATE` 给其中一行写下城市，再查询确认另一行仍然没有城市。
4. 在长注释里读 `PRAGMA table_info(people)` 的一行，按六个位置说明它是哪一列、什么类型、是不是非空、有没有默认值、是不是主键。

这一课的作业不要求制造约束错误，也不使用 `UNIQUE`。那些是第 5 课的练习。
