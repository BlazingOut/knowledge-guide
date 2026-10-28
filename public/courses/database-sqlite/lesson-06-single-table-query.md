# 第六课：单表查询补全

## 本课范围

前几课已经学习了 `SELECT`、`WHERE`、排序以及基本的插入、修改和删除。本课继续只查询一张表，把单表筛选中最常用的条件补齐：

```text
IN
BETWEEN
LIKE
IS NULL
DISTINCT
AND / OR / NOT
LIMIT / OFFSET
```

本课不讲：

- 多表 `JOIN`；
- 聚合函数、`GROUP BY` 和 `HAVING`；
- 子查询；
- 事务和连接生命周期；
- 索引和执行计划。

这些内容放在后续课程。

## 学习目标

完成本课后，你应当能够：

- 使用 `IN`、`BETWEEN` 和 `LIKE` 表达常见筛选；
- 使用 `IS NULL` 正确查询空值；
- 解释 `NULL` 不能使用 `= NULL` 判断的原因；
- 使用 `DISTINCT` 去除重复结果；
- 用括号明确 `AND` 和 `OR` 的逻辑关系；
- 使用 `LIMIT` 和 `OFFSET` 实现最基本的分页；
- 在 Python `sqlite3` 中为占位符传递参数。

## 1. 练习表

本课使用 `products` 表：

```sql
CREATE TABLE products (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price INTEGER NOT NULL,
  stock INTEGER,
  description TEXT
)
```

其中 `stock` 和 `description` 允许为 `NULL`，用于观察空值查询。

示例数据：

| id | name | category | price | stock | description |
| --- | --- | --- | ---: | ---: | --- |
| 1 | 键盘 | 办公 | 199 | 20 | 机械键盘 |
| 2 | 鼠标 | 办公 | 99 | 0 | 无线鼠标 |
| 3 | 显示器 | 办公 | 1299 | 8 | 27 英寸显示器 |
| 4 | 水杯 | 生活 | 59 | 30 | `NULL` |
| 5 | 背包 | 生活 | 299 | 5 | 通勤背包 |
| 6 | 耳机 | 数码 | 499 | `NULL` | 降噪耳机 |

## 2. `IN`：匹配多个候选值

如果要查询办公或数码分类，可以写多个 `OR`：

```sql
WHERE category = '办公' OR category = '数码'
```

也可以写成：

```sql
SELECT id, name, category
FROM products
WHERE category IN ('办公', '数码')
ORDER BY id
```

`IN` 表示一个值是否属于给定候选集合。Python 中仍然使用占位符：

```python
connection.execute(
    """
    SELECT id, name
    FROM products
    WHERE category IN (?, ?)
    """,
    ("办公", "数码"),
)
```

每个 `?` 对应一个参数。不能把 Python 列表直接作为一个参数期待 SQLite 自动展开：

```python
# 不要这样写
connection.execute(
    "SELECT * FROM products WHERE category IN (?)",
    (["办公", "数码"],),
)
```

如果候选数量是动态的，需要根据数量生成对应数量的 `?`，但仍然要把值作为参数传递。

## 3. `BETWEEN`：匹配闭区间

查询价格在 100 到 500 之间的商品：

```sql
SELECT name, price
FROM products
WHERE price BETWEEN 100 AND 500
ORDER BY price
```

`BETWEEN a AND b` 包含两端：

```text
a <= value AND value <= b
```

所以 `price = 100` 和 `price = 500` 都会匹配。

Python 写法：

```python
connection.execute(
    """
    SELECT name, price
    FROM products
    WHERE price BETWEEN ? AND ?
    """,
    (100, 500),
)
```

如果业务需要排除边界，应明确写成：

```sql
WHERE price > 100 AND price < 500
```

不要默认把 `BETWEEN` 理解成开区间。

## 4. `LIKE`：匹配文本模式

查询名称中包含“器”的商品：

```sql
SELECT name
FROM products
WHERE name LIKE '%器%'
```

通配符：

| 写法 | 含义 |
| --- | --- |
| `%` | 任意长度的字符序列，包括空字符串 |
| `_` | 任意一个字符 |

示例：

```sql
WHERE name LIKE '耳%'
```

表示以“耳”开头。

```sql
WHERE name LIKE '%器'
```

表示以“器”结尾。

Python 中把模式作为参数：

```python
connection.execute(
    "SELECT name FROM products WHERE name LIKE ?",
    ("%器%",),
)
```

不要通过字符串拼接把用户输入直接放进 SQL。参数化可以防止输入改变 SQL 结构。

## 5. `NULL` 和 `IS NULL`

`NULL` 表示缺失或未知，不等同于空字符串，也不等同于数字 `0`：

```text
NULL     没有值或未知
''       长度为 0 的字符串
0        数字零
```

错误写法：

```sql
WHERE stock = NULL
```

正确写法：

```sql
SELECT name, stock
FROM products
WHERE stock IS NULL
```

查询已经记录库存的商品：

```sql
WHERE stock IS NOT NULL
```

原因是普通比较遇到 `NULL` 会得到未知结果，而不是普通的真或假。判断空值必须使用 `IS NULL` 或 `IS NOT NULL`。

## 6. `DISTINCT`：去除重复结果

查询商品分类：

```sql
SELECT category
FROM products
ORDER BY category
```

同一个分类会出现多次。只想看有哪些不同分类，可以使用：

```sql
SELECT DISTINCT category
FROM products
ORDER BY category
```

`DISTINCT` 作用于 `SELECT` 结果中的整行组合：

```sql
SELECT DISTINCT category, stock
FROM products
```

这里去重的单位是 `(category, stock)` 组合，不是只对 `category` 单独去重。

如果选择了 `id`：

```sql
SELECT DISTINCT id, category
FROM products
```

由于 `id` 本身不同，通常不会达到预期的分类去重效果。

## 7. `AND`、`OR` 和括号

查询办公或生活分类，并且价格低于 500：

```sql
WHERE (category = '办公' OR category = '生活')
  AND price < 500
```

括号表示先计算分类条件，再与价格条件组合。

如果省略括号：

```sql
WHERE category = '办公'
   OR category = '生活' AND price < 500
```

SQL 通常先处理 `AND`，再处理 `OR`，这等价于：

```sql
WHERE category = '办公'
   OR (category = '生活' AND price < 500)
```

这会让所有办公商品都匹配，即使价格不低于 500。

工程代码中，即使自己记得优先级，也建议在混合 `AND` 和 `OR` 时使用括号。括号表达的是业务意图，也能减少维护者误读。

`NOT` 可以否定条件：

```sql
WHERE NOT category = '办公'
```

实际项目中如果条件复杂，优先写成更直接的正向条件，例如：

```sql
WHERE category IN ('生活', '数码')
```

## 8. `LIMIT` 和 `OFFSET`

只取前两条：

```sql
SELECT id, name
FROM products
ORDER BY id
LIMIT 2
```

跳过前两条，再取两条：

```sql
SELECT id, name
FROM products
ORDER BY id
LIMIT 2 OFFSET 2
```

分页必须配合稳定的 `ORDER BY`。没有排序时，数据库不保证每次返回的顺序，分页结果可能发生变化。

Python 中使用参数：

```python
connection.execute(
    """
    SELECT id, name
    FROM products
    ORDER BY id
    LIMIT ? OFFSET ?
    """,
    (2, 2),
)
```

`LIMIT` 和 `OFFSET` 的值应该经过输入校验。分页参数过大可能造成不必要的查询和响应。

## 9. 查询逻辑顺序

SQL 的书写顺序和理解顺序不是完全一样。单表查询可以先用下面的逻辑顺序理解：

```text
FROM
  -> WHERE
  -> SELECT
  -> DISTINCT
  -> ORDER BY
  -> LIMIT / OFFSET
```

例如：

```sql
SELECT DISTINCT category
FROM products
WHERE price < 500
ORDER BY category
LIMIT 2
```

可以理解为：

1. 从 `products` 取数据；
2. 筛选价格小于 500 的行；
3. 只保留 `category`；
4. 去掉重复分类；
5. 排序；
6. 取前两条。

这是理解查询的模型，不代表 SQLite 内部一定严格按这个物理步骤执行。优化器可能选择不同的执行计划；执行计划留到索引课程讨论。

## 10. 课程代码和运行

练习文件：

```text
code/database-sqlite/database_lesson06.py
```

运行：

```bash
python code/database-sqlite/database_lesson06.py
```

程序会创建独立的 `database_lesson06.sqlite3`，每次运行先重建 `products` 表，因此示例结果不会受到上次运行的影响。

代码中依次演示：

1. `IN` 查询多个分类；
2. `BETWEEN` 查询价格范围；
3. `LIKE` 查询文本模式；
4. `IS NULL` 查询缺失库存；
5. `DISTINCT` 查询不同分类；
6. 括号、`LIMIT` 和 `OFFSET`。

## 11. 课后作业

在 `homework()` 中完成以下查询，使用同一个 `products` 表：

1. 查询分类为“办公”或“生活”，且库存大于 0 的商品；
2. 查询价格不在 100 到 500 之间的商品；
3. 查询名称以“鼠”或“耳”开头的商品；
4. 查询 `description` 不为空的商品；
5. 查询不同的 `category` 和 `stock` 组合；
6. 实现第 2 页，每页 2 条记录，按 `id` 升序排列。

每个查询都要打印标题和结果，并说明：

- 使用了哪个条件；
- 是否包含边界；
- `NULL` 是如何判断的；
- 是否依赖稳定排序。

## 12. 验收问题

1. `IN` 和多个 `OR` 有什么关系？
2. `BETWEEN` 是否包含两端？
3. `%` 和 `_` 在 `LIKE` 中分别代表什么？
4. 为什么 `stock = NULL` 查不到空值？
5. `NULL`、空字符串和 `0` 有什么区别？
6. `DISTINCT` 对多列查询时按什么去重？
7. 混合使用 `AND` 和 `OR` 时为什么建议加括号？
8. 为什么分页必须配合 `ORDER BY`？
9. `LIMIT 2 OFFSET 4` 表示什么？
10. SQL 的逻辑查询顺序是什么？

## 13. 面试高频考点

### 13.1 `WHERE column = NULL` 为什么不正确？

`NULL` 表示未知或缺失，普通比较不会得到普通的真值。判断空值必须使用 `IS NULL`，判断非空使用 `IS NOT NULL`。

### 13.2 `BETWEEN` 是否包含边界？

包含。`value BETWEEN a AND b` 等价于 `value >= a AND value <= b`。如果业务需要开区间，需要显式使用 `>` 和 `<`。

### 13.3 `AND` 和 `OR` 混合时如何避免逻辑错误？

使用括号明确业务分组。`AND` 通常优先于 `OR`，省略括号可能导致一部分条件只作用于 `OR` 的一侧。

### 13.4 分页为什么需要排序？

关系型表本身没有天然的返回顺序。没有稳定的 `ORDER BY`，数据库可以用不同顺序返回行，导致不同页之间重复或遗漏数据。

### 13.5 为什么 `DISTINCT` 不能代替业务去重？

`DISTINCT` 只对当前查询结果的列组合去重。它不修改表中的数据，也不保证业务上某个字段唯一；需要数据唯一性时，应考虑 `UNIQUE` 约束。
