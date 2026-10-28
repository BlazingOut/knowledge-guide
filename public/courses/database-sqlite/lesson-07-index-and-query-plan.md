# 第七课：SQLite 的索引与查询计划

> MySQL 正式课程已经讲过 B+ 树、聚簇索引、回表、覆盖索引和 `EXPLAIN`。本课不重复 InnoDB 的内部结构，而是学习 SQLite 如何创建索引，以及如何用 `EXPLAIN QUERY PLAN` 观察 SQLite 实际选择了什么访问方式。
>
> 完整可运行代码见 `code/database-sqlite/database_lesson07.py`。

## 一、这一课要解决什么问题

对于 SQLite 查询，不能只凭 SQL 文字判断它是否高效。需要回答：

```text
SQLite 是扫描整张表，还是使用了索引？
联合索引的列顺序是否匹配查询？
查询只需要索引中的字段时，能否避免读取表记录？
EXPLAIN QUERY PLAN 的 SCAN、SEARCH 分别表示什么？
```

SQLite 的重点工具是：

```sql
EXPLAIN QUERY PLAN
```

它和 MySQL 的 `EXPLAIN` 不是同一种输出格式。不要把 MySQL 的 `type`、`key`、`rows` 字段直接套到 SQLite。

## 二、创建索引

准备好 `products` 表后，为分类创建索引：

```sql
CREATE INDEX idx_products_category
ON products(category);
```

查询计划：

```sql
EXPLAIN QUERY PLAN
SELECT id, name, price
FROM products
WHERE category = '办公';
```

可能看到类似结果：

```text
SEARCH products USING INDEX idx_products_category (category=?)
```

这里的重点是 `USING INDEX`，说明 SQLite 选择了这棵索引。具体输出文本可能随 SQLite 版本和索引名称变化。

删除索引：

```sql
DROP INDEX idx_products_category;
```

删除前应确认没有其他查询依赖它。索引是数据库对象，删除后不会删除表中的数据，但可能改变查询性能。

## 三、SCAN 和 SEARCH

### 1. SCAN：扫描

如果没有合适索引，计划可能类似：

```text
SCAN products
```

可以把它理解为 SQLite 需要逐步检查表中的记录。小表扫描不一定是问题，数据量很大或查询频繁时才需要重点关注。

### 2. SEARCH：定位范围

使用索引后，可能看到：

```text
SEARCH products USING INDEX idx_products_category (category=?)
```

这表示 SQLite 根据条件在索引中定位满足条件的范围，而不是无条件检查整张表。

不要把 `SCAN` 简单等同于“错误”，也不要把 `SEARCH` 简单等同于“必然更快”。优化器还要考虑表大小、返回行数、索引成本和实际数据分布。

## 四、覆盖索引

建立联合索引：

```sql
CREATE INDEX idx_products_category_name
ON products(category, name);
```

查询只返回索引中已经存在的字段：

```sql
EXPLAIN QUERY PLAN
SELECT category, name
FROM products
WHERE category = '办公';
```

可能看到：

```text
SEARCH products USING COVERING INDEX idx_products_category_name (category=?)
```

`USING COVERING INDEX` 表示查询所需字段可以直接从索引取得，不必再读取表记录。

这里沿用“覆盖索引”的通用概念，但不要把它解释成 InnoDB 的二级索引回表模型。SQLite 没有 MySQL InnoDB 那套聚簇索引、二级索引和回表实现，具体数据组织方式不同。

覆盖索引仍然有代价：索引更宽，占用更多空间，并增加写入维护成本。只有高频、合适的查询才值得专门设计覆盖索引。

## 五、联合索引的列顺序

为订单表建立联合索引：

```sql
CREATE INDEX idx_orders_user_status
ON orders(user_id, status);
```

适合观察的查询：

```sql
EXPLAIN QUERY PLAN
SELECT id, order_no
FROM orders
WHERE user_id = 1
  AND status = 'paid';
```

再观察只使用第二列的查询：

```sql
EXPLAIN QUERY PLAN
SELECT id, order_no
FROM orders
WHERE status = 'paid';
```

第二条查询是否使用索引、使用到什么程度，必须以 SQLite 的实际计划为准。课程中的重点不是机械背诵 MySQL 的最左前缀结论，而是学会通过 `EXPLAIN QUERY PLAN` 验证 SQLite 的行为。

联合索引设计仍应从实际查询出发：

```text
哪些字段经常一起出现在 WHERE？
是否需要 ORDER BY？
返回字段是否可以被索引覆盖？
写入和更新频率是否很高？
```

## 六、查询条件和索引

对索引列使用函数，可能使优化器难以直接利用索引：

```sql
WHERE lower(name) = 'keyboard'
```

是否能使用表达式索引、是否应该改写查询，要结合 SQLite 版本和索引定义验证。不要只根据 MySQL 经验判断。

前置通配符同样可能难以利用普通索引：

```sql
WHERE name LIKE '%键'
```

而确定前缀的模式更容易形成可搜索范围：

```sql
WHERE name LIKE '键%'
```

实际是否使用索引，仍然通过 `EXPLAIN QUERY PLAN` 确认。

## 七、Python 中读取查询计划

`sqlite3` 可以像执行普通查询一样读取计划：

```python
plan_rows = connection.execute(
    """
    EXPLAIN QUERY PLAN
    SELECT id, name
    FROM products
    WHERE category = ?
    """,
    ("办公",),
).fetchall()

for row in plan_rows:
    print(tuple(row))
```

SQLite 的计划行通常包含类似字段：

```text
(id, parent, notused, detail)
```

最值得先看的通常是 `detail`：

```text
SCAN products
SEARCH products USING INDEX ...
SEARCH products USING COVERING INDEX ...
```

不要把 `EXPLAIN QUERY PLAN` 的输出当作跨版本稳定的机器接口。自动化测试可以检查关键行为，但不要过度依赖完整文本完全一致。

## 八、统计信息和 ANALYZE

SQLite 优化器会根据表和索引的统计信息选择计划。数据分布发生变化后，可以考虑更新统计信息：

```sql
ANALYZE;
```

`ANALYZE` 会读取数据分布并保存统计结果，帮助优化器做选择。它不是“强制所有查询使用索引”，也不是执行一次就能永久解决性能问题。

在验证计划时，要考虑：

- 当前数据库是否有足够测试数据；
- 测试数据分布是否接近真实数据；
- 索引是否刚刚创建；
- 是否执行过 `ANALYZE`；
- 查询返回结果是否很大。

## 九、SQLite 查询计划和 MySQL EXPLAIN 的区别

两者都用于观察访问计划，但关注方式不同：

| 对比 | SQLite | MySQL |
|---|---|---|
| 常用命令 | `EXPLAIN QUERY PLAN` | `EXPLAIN` |
| 典型输出 | `SCAN`、`SEARCH`、`USING INDEX` | `type`、`key`、`rows`、`Extra` |
| 课程重点 | 是否扫描、是否搜索、是否覆盖 | 访问类型、索引、估计行数、额外操作 |
| 引擎模型 | SQLite 文件数据库 | MySQL InnoDB 服务器引擎 |

在 SQLite 中，不需要重新讲聚簇索引和回表；在 MySQL 中，也不能用 SQLite 的 `SCAN`、`SEARCH` 输出代替 InnoDB 的执行计划分析。

## 十、常见错误

### 1. 只要看到 SCAN 就认为查询一定有问题

小表全表扫描可能比使用索引更便宜。要结合数据量和实际耗时判断。

### 2. 只要创建索引就认为查询一定使用

优化器可能认为全表扫描成本更低。必须查看 `EXPLAIN QUERY PLAN`。

### 3. 把 SQLite 当成 InnoDB 分析

SQLite 没有 MySQL InnoDB 的聚簇索引、二级索引和回表模型。可以讨论索引覆盖，但不能照搬底层结构解释。

### 4. 用一条小表测试推断大表性能

小数据集上的计划和真实数据分布可能不同。查询性能需要接近真实规模的数据验证。

### 5. 索引过多

每棵索引都要占用空间并增加写入维护成本。应根据真实查询和计划创建索引。

## 十一、面试回答模板

### 题目：SQLite 如何判断查询有没有使用索引？

> 使用 `EXPLAIN QUERY PLAN` 查看计划，重点观察 detail 中是否出现 `USING INDEX`、`USING COVERING INDEX`，以及是否只是 `SCAN`。但小表扫描不一定是问题，最终还要结合数据量和实际耗时判断。

### 题目：SQLite 的 SCAN 和 SEARCH 有什么区别？

> SCAN 表示计划需要扫描数据，SEARCH 表示根据条件在表或索引中查找目标范围。它们是查询计划中的访问描述，不应该脱离数据量、返回行数和索引成本简单判断优劣。

### 题目：SQLite 和 MySQL 的索引分析一样吗？

> 目标都是观察查询访问路径，但工具和底层模型不同。SQLite 常用 `EXPLAIN QUERY PLAN`，重点看 SCAN、SEARCH 和索引覆盖；MySQL 常用 `EXPLAIN`，重点看 type、key、rows 和 Extra。不能把 InnoDB 的聚簇索引和回表模型直接套到 SQLite。

## 十二、这一课学到什么程度可以继续

```text
能使用 CREATE INDEX 和 DROP INDEX
能使用 EXPLAIN QUERY PLAN
能解释 SCAN、SEARCH 和 USING INDEX
能识别 USING COVERING INDEX
能根据真实查询初步设计 SQLite 联合索引
知道 SQLite 不应套用 InnoDB 聚簇索引和回表模型
知道数据规模、统计信息和版本会影响查询计划
```

下一课将学习 SQLite 特有语法与内部结构，包括 `rowid`、`INTEGER PRIMARY KEY`、UPSERT 和 `RETURNING`。
