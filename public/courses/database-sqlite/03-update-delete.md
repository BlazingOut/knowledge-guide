# 第3课：修改和删除记录

## 1. 使用 `UPDATE`

```sql
UPDATE books
SET author = ?
WHERE title = ?
```

- `UPDATE books`：要修改 `books` 表。
- `SET author = ?`：把 `author` 列改成新值。
- `WHERE title = ?`：只修改符合条件的行。

## 2. 使用 `DELETE`

```sql
DELETE FROM books
WHERE title = ?
```

这会删除符合条件的记录。`DELETE` 后面不需要写列名，只需要指定表和条件。

## 3. 为什么 `WHERE` 很重要

```sql
UPDATE books SET author = ?
```

没有 `WHERE` 时，所有书的作者都会被修改。

```sql
DELETE FROM books
```

没有 `WHERE` 时，整张表的记录都会被删除。因此修改和删除前，应先确认条件能准确找到目标记录。

## 4. 当前练习

练习文件：`code/database-sqlite/03-update-delete.py`

运行：

```bash
python code/database-sqlite/03-update-delete.py
```

这个练习会使用第一课创建的数据库。示例中的删除语句默认被注释，避免重复运行时反复删除数据。代码中的课后作业区域有 4 个编号的 `TODO`，开放题答案直接写成长注释。
