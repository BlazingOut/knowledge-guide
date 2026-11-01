# 第8课:MySQL 8 高级查询语法

> 前一课学习了聚合、JOIN、子查询和 CTE。这一课继续处理更复杂的查询：合并结果集、组内排名、每组 Top N、最近一条记录和累计统计。
>
> 本课完整可执行示例见 `code/database/06-advanced-query.sql`。理论文档只保留解释语义的关键 SQL 片段。

## 一、这一课要解决什么问题

普通 `GROUP BY` 会把一组数据压缩成一行，但很多业务查询既想保留明细，又想在明细旁边看到组内统计：

```text
每个用户最近的一笔订单
每个分类销量最高的前三个商品
订单按用户排名
每个用户的累计消费
两组结构相同的数据合并
```

这一课主要学习：

```text
UNION / UNION ALL：合并多个查询结果
窗口函数：在保留明细的同时进行组内计算
CTE：组织多步骤复杂查询
```

## 二、UNION 和 UNION ALL

### 1. 合并结果集

`UNION` 可以把两个查询的结果上下合并：

```sql
SELECT id, email
FROM users
WHERE id <= 10

UNION

SELECT id, email
FROM users
WHERE email LIKE '%example.com';
```

参与合并的查询需要满足：

- 返回的列数相同；
- 对应位置的类型能够兼容；
- 列的含义最好一致。

结果列名通常以第一个查询的列名为准。

### 2. UNION 和 UNION ALL 的区别

```text
UNION：合并后去重
UNION ALL：合并后保留重复行
```

如果业务不要求去重，优先使用 `UNION ALL`：

```sql
SELECT id, email FROM users WHERE id <= 10
UNION ALL
SELECT id, email FROM users WHERE id > 10;
```

`UNION` 为了去重，可能需要额外排序或临时处理。不要习惯性使用 `UNION`，先确认重复记录是否真的需要消除。

### 3. ORDER BY 放在哪里

如果要对合并后的最终结果排序，通常把 `ORDER BY` 放在最后：

```sql
SELECT id, email FROM users WHERE id <= 10
UNION ALL
SELECT id, email FROM users WHERE id > 10
ORDER BY id;
```

单个分支中的排序通常不能替代最终结果排序。`LIMIT` 放在分支内部和放在最后，语义也不同，写之前要明确是“每个分支截取”还是“合并后截取”。

## 三、窗口函数是什么

### 1. GROUP BY 和窗口函数的区别

`GROUP BY` 会把多行压缩成一行：

```sql
SELECT user_id, SUM(total_amount) AS total_amount
FROM orders
GROUP BY user_id;
```

窗口函数则在保留原始行的同时，增加计算结果：

```sql
SELECT
    id,
    user_id,
    total_amount,
    SUM(total_amount) OVER (PARTITION BY user_id) AS user_total
FROM orders;
```

结果中每笔订单仍然存在，同时每笔订单旁边都有该用户的订单总额。

```text
GROUP BY：多行 -> 一行
窗口函数：保留明细 + 增加组内计算列
```

### 2. 窗口函数的基本结构

```sql
函数名(...) OVER (
    PARTITION BY 分组字段
    ORDER BY 排序字段
)
```

```text
PARTITION BY：把数据分成多个窗口，不会压缩结果
ORDER BY：规定窗口内的顺序
```

窗口函数的 `ORDER BY` 和整个查询最后的 `ORDER BY` 不是一回事：前者决定计算顺序，后者决定最终输出顺序。

## 四、排名函数

### 1. ROW_NUMBER

为每个用户的订单按时间倒序编号：

```sql
SELECT
    id,
    user_id,
    order_no,
    created_at,
    ROW_NUMBER() OVER (
        PARTITION BY user_id
        ORDER BY created_at DESC, id DESC
    ) AS row_num
FROM orders;
```

每个用户都会从 1 开始编号。`id` 作为第二排序条件，可以在创建时间相同时保证顺序稳定。

### 2. RANK 和 DENSE_RANK

```sql
SELECT
    id,
    user_id,
    total_amount,
    RANK() OVER (
        PARTITION BY user_id
        ORDER BY total_amount DESC
    ) AS amount_rank,
    DENSE_RANK() OVER (
        PARTITION BY user_id
        ORDER BY total_amount DESC
    ) AS dense_amount_rank
FROM orders;
```

三种函数的区别：

```text
ROW_NUMBER：每行唯一编号，不考虑并列
RANK：并列时排名相同，后续排名会跳号
DENSE_RANK：并列时排名相同，后续排名不跳号
```

例如金额排名为 `100、100、90`：

```text
ROW_NUMBER：1、2、3
RANK：      1、1、3
DENSE_RANK：1、1、2
```

应该根据业务到底需要“前 N 行”还是“前 N 个名次”来选择。

## 五、每组 Top N 和最近一条记录

窗口函数不能直接在同一层 `WHERE` 中使用别名过滤，因此通常需要 CTE 或派生表：

```sql
WITH ranked_orders AS (
    SELECT
        o.*,
        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY created_at DESC, id DESC
        ) AS rn
    FROM orders AS o
)
SELECT *
FROM ranked_orders
WHERE rn = 1;
```

这就是“每个用户最近一笔订单”的典型写法：

```text
先给每个用户的订单排名
    -> 再保留排名为 1 的记录
```

每个用户最近三笔订单：

```sql
WITH ranked_orders AS (
    SELECT
        o.*,
        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY created_at DESC, id DESC
        ) AS rn
    FROM orders AS o
)
SELECT *
FROM ranked_orders
WHERE rn <= 3;
```

## 六、累计统计和窗口范围

按用户的订单时间计算累计金额：

```sql
SELECT
    id,
    user_id,
    created_at,
    total_amount,
    SUM(total_amount) OVER (
        PARTITION BY user_id
        ORDER BY created_at, id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total
FROM orders;
```

窗口范围表示当前行参与计算的区间：

```text
UNBOUNDED PRECEDING：从当前分组第一行开始
CURRENT ROW：直到当前行
```

对于存在相同排序值的场景，明确使用 `ROWS` 并补充唯一排序键，通常更容易得到稳定、可解释的结果。

## 七、CTE 与窗口函数组合

CTE 适合把复杂查询拆成有名字的步骤：

```sql
WITH user_order_stats AS (
    SELECT
        user_id,
        COUNT(*) AS order_count,
        SUM(total_amount) AS total_amount
    FROM orders
    GROUP BY user_id
), ranked_users AS (
    SELECT
        user_id,
        order_count,
        total_amount,
        RANK() OVER (ORDER BY total_amount DESC) AS amount_rank
    FROM user_order_stats
)
SELECT u.nickname, r.order_count, r.total_amount, r.amount_rank
FROM ranked_users AS r
JOIN users AS u ON u.id = r.user_id
ORDER BY r.amount_rank;
```

每个 CTE 都可以理解为一个命名的中间结果，但它不是永久表。CTE 主要改善可读性，是否带来性能提升要结合执行计划验证。

## 八、视图、存储过程和触发器：只作了解

### 1. 视图

视图可以保存一个查询定义：

```sql
CREATE VIEW paid_order_summary AS
SELECT user_id, SUM(total_amount) AS paid_amount
FROM orders
WHERE status = 'paid'
GROUP BY user_id;
```

之后可以像查询表一样查询：

```sql
SELECT * FROM paid_order_summary;
```

视图通常保存的是查询逻辑，不等于自动保存一份独立数据。它适合封装稳定查询和简化权限，但复杂视图仍可能有性能和维护问题。

### 2. 存储过程和触发器

存储过程把一组数据库操作封装在数据库中，触发器则在数据变更时自动执行逻辑。它们在旧系统中可能比较常见，但需要谨慎使用：

- 行为不容易从应用代码中看出来；
- 调试和测试链路更复杂；
- 触发器可能产生隐式的级联影响；
- 业务逻辑分散在应用和数据库两处。

本课程只要求能读懂这些对象，不把它们作为 MySQL 业务开发主线。

## 九、常见错误

### 1. UNION 两边列数或含义不一致

即使类型能够转换，列的业务含义不一致也会产生难以理解的结果。合并前先确认每个位置表达同一类数据。

### 2. 把窗口函数当成 GROUP BY

窗口函数不会自动减少行数。如果只需要每组一行，应使用聚合；如果需要保留明细，应使用窗口函数。

### 3. 用 RANK 解决前 N 行问题

并列值会使 `RANK` 返回超过 N 行。需要严格取 N 行时使用 `ROW_NUMBER`，需要保留并列名次时才使用 `RANK` 或 `DENSE_RANK`。

### 4. 窗口排序不稳定

只按可能重复的时间或金额排序，结果可能不稳定。补充主键等唯一字段作为排序条件。

### 5. 认为 CTE 一定更快

CTE 首要价值是组织复杂 SQL。真正性能要看数据量、索引、优化器和 `EXPLAIN`。

## 十、面试回答模板

### 题目：窗口函数和 GROUP BY 有什么区别？

> GROUP BY 会把多行聚合成每组一行；窗口函数在保留原始明细行的同时，增加组内统计或排名结果。需要每组一行时使用 GROUP BY，需要“明细加统计”或每组排名时使用窗口函数。

### 题目：如何查询每个用户最近一笔订单？

> 可以先使用 `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC, id DESC)` 为每个用户的订单排名，再在外层查询中过滤 `row_number = 1`。使用时间加主键作为排序条件，可以保证时间相同时顺序稳定。

### 题目：ROW_NUMBER、RANK 和 DENSE_RANK 有什么区别？

> ROW_NUMBER 为每一行生成唯一编号；RANK 允许并列且后续排名跳号；DENSE_RANK 允许并列但后续排名不跳号。取严格前 N 行通常用 ROW_NUMBER，按名次保留并列数据时使用 RANK 或 DENSE_RANK。

## 十一、这一课学到什么程度可以继续

```text
能区分 UNION 和 UNION ALL
能解释 GROUP BY 和窗口函数的区别
能使用 ROW_NUMBER、RANK、DENSE_RANK
能查询每组最近一条和每组 Top N
能写累计统计
能使用 CTE 组织多步骤查询
能说明视图、存储过程和触发器的基本用途与风险
```

下一课将进入 MySQL 的核心：InnoDB 索引与索引设计。
