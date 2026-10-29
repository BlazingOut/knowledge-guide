# 第二课：条件查询和排序

## 1. 使用 `WHERE` 筛选记录

```sql
SELECT title, author
FROM books
WHERE author = ?
```

`WHERE` 会筛选记录，只保留符合条件的行。这里的条件是作者等于某个值。

Python 代码通过第二个参数传入真实作者：

```python
connection.execute(
    "SELECT title, author FROM books WHERE author = ?",
    ("刘慈欣",),
)
```

这里虽然只有一个 `?`，但第二个参数仍然要传一个“参数序列”。元组正好表示一组参数：

```python
("刘慈欣",)       # 只有一个元素的元组
["刘慈欣"]         # 列表也可以作为参数序列
```

结尾的逗号不可省略。`("刘慈欣")` 只是一个加了括号的字符串，不是元组。`execute` 会按照位置，把参数序列中的第一个值绑定到第一个 `?`。

## 2. 使用 `ORDER BY` 排序

```sql
SELECT id, title, author
FROM books
ORDER BY id DESC
```

- `ORDER BY id`：按照 `id` 排序。
- `ASC`：升序，从小到大；默认值。
- `DESC`：降序，从大到小。

`ORDER BY` 后面不要求一定是整数列。它后面通常接列名，也可以是文字、数字、小数或日期文字等可以比较的值：

```sql
ORDER BY title ASC       -- 按文字排序
ORDER BY id DESC         -- 按整数排序
ORDER BY price ASC       -- 按小数排序
```

如果日期统一使用类似 `2026-08-30` 的格式，日期文字也可以按时间顺序排列。

占位符用于“值”，不能直接替代列名：

```python
# 正确：值使用占位符
"WHERE author = ?"

# 不能这样动态选择排序列
"ORDER BY ?"
```

如果允许用户选择排序字段，应该从程序预先准备好的列名列表中选择，而不是把用户输入直接拼进 SQL。

`WHERE` 决定“哪些记录被保留”，`ORDER BY` 决定“保留的记录如何排列”。它们可以一起使用。

## 3. Python 中的查询结果

```python
connection.row_factory = sqlite3.Row
```

设置后，每一行可以通过列名读取：

```python
row["title"]
row["author"]
```

这样比只使用 `row[0]`、`row[1]` 更容易理解。

## 4. 当前练习

练习文件：`code/database-sqlite/database_lesson02.py`

运行：

```bash
python code/database-sqlite/database_lesson02.py
```

这个练习使用第一课创建的 `database_lesson01.sqlite3`。如果还没有运行第一课，请先运行：

```bash
python code/database-sqlite/database_lesson01.py
```

代码中的“课后作业”区域已经用 `TODO 作业 1` 到 `TODO 作业 4` 标出。开放题答案直接写在代码注释中，较长的答案使用连续的 `#` 注释。
