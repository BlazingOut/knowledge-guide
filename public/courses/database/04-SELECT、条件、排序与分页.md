# 第4课:SELECT、条件、排序与分页

> 前两课解决了表和字段的设计（表结构、数据类型、约束）。这一课学习最常用的数据库操作：从表中准确地找到想要的数据。
>
> 本课完整可执行示例见 `code/database/03-select-filter-sort-page.sql`。理论文档只保留用于解释概念的关键 SQL 片段。

## 一、这一课要解决什么问题

查询通常不是把整张表打印出来，而是：

```text
选择需要的列
    -> 筛选符合条件的记录
    -> 处理 NULL 和边界值
    -> 按业务要求排序
    -> 返回指定范围的数据
```

本课主要学习 `SELECT`、`WHERE`、`ORDER BY`、`LIMIT`、`OFFSET`，以及 `NULL`、三值逻辑、稳定排序和分页。

## 二、SELECT 的基本结构

### 1. SELECT 语句
`SELECT` 的完整常用形式，方括号都是可选项：

```sql
SELECT [DISTINCT] 列1 [AS 别名], 列2, ...
FROM 表名 [AS 别名]
[WHERE 条件]
[ORDER BY 列 [ASC | DESC], ...]
[LIMIT 行数 [OFFSET 跳过行数]];
```

| 部分 | 含义 |
|---|---|
| `SELECT` | 要返回的列，用 `*` 表示所有列 |
| `FROM` | 数据来源，先 `USE` 选定数据库或写 `库名.表名` |
| `WHERE` / `ORDER BY` / `LIMIT` | 可选：筛选、排序、限量，分别在第 3、5、6 节展开 |

最小形式只保留 `SELECT` 和 `FROM`：

```sql
SELECT email, nickname
FROM users;
```

临时查看可以使用 `SELECT *`，但稳定的业务查询应明确列出字段，避免传输不需要的数据，也避免表结构变化意外影响接口。

列别名和计算列：`AS` 给结果列起名，用于展示，也可被 `ORDER BY` 引用。

```sql
SELECT id AS user_id, nickname AS display_name
FROM users;

SELECT name, price, price * 0.9 AS discounted_price
FROM products;
```



表别名：`FROM users AS u`，起别名后 SELECT 里用 `别名.列` 引用，为多表查询做准备。

```sql
SELECT u.id, u.email
FROM users AS u;
```

`DISTINCT` 去除结果中的重复组合，但不应该用来掩盖 JOIN 条件错误：

```sql
SELECT DISTINCT status
FROM orders;
```

### 2. 条件分支

`CASE` 是条件表达式：从上到下判断分支，返回第一个条件为真的结果，用来生成结果列。结构模板：

```sql
CASE WHEN 条件1 THEN 结果1
     WHEN 条件2 THEN 结果2
     ...
     ELSE 默认结果 END
```

| 部分 | 含义 |
|---|---|
| `WHEN 条件 THEN 结果` | 一个分支：条件成立时返回对应结果 |
| `ELSE 默认结果` | 所有 WHEN 都不成立时返回的值，可选 |
| `END` | 结束 CASE 表达式，必须写 |

行为：从上到下依次判断，命中第一个为真的 WHEN 就返回，后面的分支不再判断；都不成立时返回 `ELSE`，没有 `ELSE` 则返回 NULL。整个 CASE 作为 SELECT 的一列，通常配 `AS` 起别名：

```sql
SELECT
    name,
    CASE WHEN stock = 0 THEN '无货'
         WHEN stock < 10 THEN '库存较低'
         ELSE '库存正常' END AS stock_label
FROM products;
```

### 3. COALESCE 兜底函数

`COALESCE` 解决“NULL 不能直接展示”的问题。业务表里很多字段允许为空，例如 `users.phone` 可以为 NULL；查询结果直接显示 NULL 既不友好，也常让前端难以处理。`COALESCE` 是 NULL 兜底函数：`COALESCE(值1, 值2, ...)` 从左到右返回第一个非 NULL 的值，全部为 NULL 时返回 NULL。

| 项目 | 说明 |
|---|---|
| 参数 | 两个及以上值：字段、常量或表达式 |
| 返回值 | 第一个非 NULL 的参数 |
| 常见用途 | 把 NULL 换成展示用默认值，或多个字段间兜底 |

```sql
SELECT nickname, COALESCE(phone, '未填写') AS phone_display
FROM users;
```

它作用在结果列：phone 有值时显示 phone，为 NULL 时显示“未填写”，只改变查询结果的展示值，不修改数据库里的数据。参数可以接多个，依次兜底，例如联系方式按优先级取 `COALESCE(mobile, phone, email, '无')`。

和 `IS NULL` 的分工：`IS NULL` 用于条件判断（这一行要不要），`COALESCE` 用于取值展示（这一列显示什么）。

## 三、WHERE：筛选记录

```sql
SELECT 列1, 列2, ...
FROM 表名
WHERE 条件;
```

`WHERE` 逐行过滤，条件为真的行才进入结果。常用条件语法：

| 语法 | 含义 | 示例 |
|---|---|---|
| `=`、`<>`、`!=`、`>`、`>=`、`<`、`<=` | 数值/字符串比较 | `status = 'paid'`、`total_amount >= 100` |
| `AND`、`OR`、`NOT` | 逻辑组合 | `status = 'paid' AND total_amount >= 100` |
| `列 IN (值1, 值2, ...)` | 属于一组候选值 | `status IN ('paid', 'shipped', 'completed')` |
| `列 BETWEEN a AND b` | 闭区间 | `price BETWEEN 50 AND 200` |
| `列 LIKE '模式'` | 模糊匹配；`%` 任意长度，`_` 一个字符 | `nickname LIKE 'Alice%'` |
| `列 IS NULL` / `列 IS NOT NULL` | 判断空值 | `phone IS NULL` |

注意三点：

- `AND` 优先级高于 `OR`，复杂条件要显式加括号，例如 `WHERE (status = 'paid' OR status = 'shipped') AND total_amount >= 100;`
- 时间范围用左闭右开：`created_at >= '2026-01-01 00:00:00' AND created_at < '2026-01-02 00:00:00'`，不要用 `23:59:59` 作为一天结束。
- 前置 `%` 的 `LIKE` 难以利用普通 B+ 树索引，具体在索引课程中讨论。

把上表每种条件写成完整语句，对照样例表执行：

```sql
-- 比较 + AND
SELECT id, order_no, total_amount
FROM orders
WHERE status = 'paid'
  AND total_amount >= 100;

-- OR 加括号
SELECT id, order_no, status, total_amount
FROM orders
WHERE (status = 'paid' OR status = 'shipped')
  AND total_amount >= 100;

-- IN
SELECT id, order_no, status
FROM orders
WHERE status IN ('paid', 'shipped', 'completed');

-- BETWEEN
SELECT id, name, price
FROM products
WHERE price BETWEEN 50 AND 200;

-- LIKE
SELECT id, nickname
FROM users
WHERE nickname LIKE 'Alice%';

-- IS NULL
SELECT id, email
FROM users
WHERE phone IS NULL;
```

## 四、NULL 和三值逻辑

### 1. NULL 不是"可比较的值"

```text
NULL：没有值、未知或不适用
''：空字符串
0：数值零
```

NULL 和空字符串、零都不是一回事。**NULL 表示"未知"**：它参与比较时既不等于任何值，也不等于 NULL 自己。`1 = NULL` 的结果不是 TRUE、也不是 FALSE，而是第三种状态 **UNKNOWN**：

```text
TRUE / FALSE / UNKNOWN（三值逻辑）
WHERE 只保留结果为 TRUE 的行，FALSE 和 UNKNOWN 都会被过滤
```

所以 `WHERE phone = NULL` 对每一行的判断结果都是 UNKNOWN，查出来永远是空结果。**判断空值必须写 `IS NULL` / `IS NOT NULL`**：

```sql
-- 正确：查没有手机号的用户
SELECT id, nickname, phone
FROM users
WHERE phone IS NULL;

-- 正确：查填了手机号的用户
SELECT id, nickname, phone
FROM users
WHERE phone IS NOT NULL;
```

对比错误写法：

```sql
-- 错误：= NULL 对每行都是 UNKNOWN，返回空结果
SELECT id, nickname, phone
FROM users
WHERE phone = NULL;
```

如果只是想把 NULL 在结果里显示成默认值（而不是过滤行），用第二节的 `COALESCE`——判断和取值是两件事。

### 2. `NOT IN` 遇到 NULL 的陷阱

```sql
WHERE id NOT IN (1, 2, NULL)
```

它等价于 `id <> 1 AND id <> 2 AND id <> NULL`。`id <> NULL` 的结果是 UNKNOWN，AND 只要有一个 UNKNOWN 就得不到 TRUE，所以**这条查询永远返回空结果**，而且不报错。

正确做法是让候选集合里不含 NULL，或改用 `NOT EXISTS`（子查询语法在第 6 课展开）：

```sql
-- 正确：先剔除 NULL 候选再 NOT IN
SELECT id, nickname
FROM users
WHERE id NOT IN (
    SELECT user_id FROM orders WHERE user_id IS NOT NULL
);

-- 正确：NOT EXISTS 判断"不存在"，天然不受 NULL 影响
SELECT id, nickname
FROM users
WHERE NOT EXISTS (
    SELECT 1 FROM orders WHERE orders.user_id = users.id
);
```

两条语句都能查"没有下过订单的用户"；写 `WHERE ... NOT IN (子查询)` 时，要先确认子查询不会返回 NULL。

## 五、ORDER BY：明确结果顺序

没有 `ORDER BY` 时，SQL 只保证返回满足条件的记录，不保证顺序。需要排序时必须明确写出：

```sql
SELECT id, order_no, created_at
FROM orders
ORDER BY created_at DESC, id DESC;
```

写法是 `ORDER BY 列 [ASC | DESC], ...`：`ASC` 升序（默认），`DESC` 降序；多个字段用逗号分隔，依次作为次级排序键。

多字段排序很重要。如果多个订单的创建时间相同，增加唯一的 `id` 可以让顺序稳定，减少分页时重复或漏数据。NULL 的排序位置可能受数据库版本和排序规则影响，需要在目标环境验证。

## 六、LIMIT、OFFSET 与分页

### 1. 写法

`LIMIT 行数 [OFFSET 跳过行数]`：`LIMIT` 限最多返回多少行，可选的 `OFFSET` 表示先跳过多少行。

```sql
SELECT id, order_no, created_at
FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 20;
```

`LIMIT 20 OFFSET 20` 表示跳过前 20 条再取 20 条。

### 2. 普通分页为什么深了会慢

普通分页适合数据量不大、页码不深的场景。页码很深时，例如 `LIMIT 20 OFFSET 200000`，数据库要**先按排序找到第 200000 行，再取 20 行**：

```text
LIMIT 20 OFFSET 200000
    -> 按 ORDER BY 定位起点
    -> 跳过前 200000 行（这些行也要被扫描）
    -> 取 20 行返回
```

即使索引能加速定位，**被跳过的 20 万行仍然要被数据库读一遍再丢弃**，所以 `OFFSET` 越大成本越高。深分页慢的本质：**被跳过的行也要被扫描**。

### 3. 键集分页（大数据量）

分页必须有明确且稳定的排序，排序字段组合最好唯一。键集分页不用 OFFSET，以上一页最后一个排序键为游标，用 WHERE 直接定位下一页的起点：

```sql
SELECT id, order_no, created_at
FROM orders
WHERE id > 100
ORDER BY id ASC
LIMIT 20;
```

时间倒序时通常把时间和 ID 一起作为游标：

```sql
WHERE created_at < '2026-10-18 12:00:00'
   OR (created_at = '2026-10-18 12:00:00' AND id < 100)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

键集分页的代价：只能**顺序翻页**（客户端要跳到第 100 页做不到）；排序键必须唯一，否则会漏行或重复。

### 4. 两种方案的对比

| 方案 | 写法 | 优点 | 缺点 |
|---|---|---|---|
| OFFSET 分页 | `LIMIT n OFFSET m` | 简单，可跳页 | 深页慢（要扫描并丢弃前 m 行） |
| 键集分页 | `WHERE 排序键 > 游标 ORDER BY 排序键 LIMIT n` | 深页不慢（索引直接定位起点） | 只能顺序翻页，排序键要唯一 |

面试一句话：**深分页慢的本质是"被跳过的行也要被扫描"；键集分页把"跳过"变成"定位"，所以深页不慢，代价是不能跳页。**

深分页和键集分页的索引代价会在执行计划课程中详细验证。

## 七、SQL 的书写顺序与逻辑执行顺序

常见书写顺序：

```text
SELECT -> FROM -> WHERE -> GROUP BY -> HAVING -> ORDER BY -> LIMIT
```

理解查询时可以按逻辑顺序思考：

```text
FROM：确定数据来源
WHERE：过滤原始行
GROUP BY：分组
HAVING：过滤分组结果
SELECT：生成返回列
ORDER BY：排序
LIMIT：截取结果
```

这解释了为什么 WHERE 通常不能使用 SELECT 别名，也解释了为什么聚合结果应使用 HAVING 过滤。聚合和 HAVING 会在第 6 课深入。

## 八、常见错误

- 没有 `ORDER BY` 却假设结果有顺序；
- 使用 `= NULL`，而不是 `IS NULL`；
- OR 条件没有加括号；
- 用 `23:59:59` 表示一天结束；
- 分页没有稳定排序；
- 用 `SELECT *` 作为长期接口查询；
- 用 `DISTINCT` 掩盖 JOIN 问题。

## 九、面试回答模板

### 题目：为什么没有 ORDER BY 就不能保证查询顺序？

> SQL 只保证返回满足条件的记录，不保证未指定的顺序。数据库可能根据表扫描、索引和执行计划选择不同的访问方式。需要稳定顺序时必须显式写 ORDER BY，分页时还要补充唯一字段保证顺序稳定。

### 题目：为什么不能使用 `= NULL`？

> NULL 表示未知或没有值，不是普通可比较值。参与普通比较时结果通常是 UNKNOWN，而不是 TRUE，所以 `column = NULL` 无法筛选 NULL，应该使用 `IS NULL` 或 `IS NOT NULL`。

### 题目：深分页为什么慢？怎么优化？

> `LIMIT offset, count` 执行时要先按排序找到第 offset 行，再取 count 行——被跳过的 offset 行也要被数据库扫描并丢弃，所以 offset 越大成本越高。优化常用键集分页：以上一页最后一个排序键为游标，用 `WHERE 排序键 > 游标 ORDER BY 排序键 ASC LIMIT n` 取下一页，索引直接定位起点，深页也不慢；代价是不能跳页，且排序键要唯一。

## 十、这一课学到什么程度可以继续

```text
能写出明确字段的 SELECT
能组合 WHERE、AND、OR、IN、BETWEEN 和 LIKE
能正确判断 NULL，并解释三值逻辑
能使用 CASE 和 COALESCE 生成结果
能使用 ORDER BY 实现稳定排序
能使用 LIMIT 和 OFFSET 实现基础分页
能解释深分页和键集分页的区别
能说出 SQL 的书写顺序和逻辑执行顺序
```

下一课将学习 `INSERT`、`UPDATE`、`DELETE` 与数据修改，重点回答：

```text
如何安全地写入数据？
唯一键冲突时怎么办？
如何使用条件更新避免错误修改？
如何通过影响行数判断业务操作是否成功？
```
