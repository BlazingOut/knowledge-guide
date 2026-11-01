# 第5课:INSERT、UPDATE、DELETE 与数据修改

> 前三课解决了数据库对象、表结构和查询。这一课开始真正操作数据：如何插入记录、修改记录和删除记录，以及如何避免一条写错的 SQL 修改整张表。
>
> 本课的完整可执行 SQL 已拆到 `code/database/04-data-modification.sql`。课文保留关键片段用于解释概念，运行练习时请以代码文件为准。
>
> 本课只讲单条写语句的语法和边界；查询语法已在第 4 课学过，聚合、事务与锁分别在 5、9~11 课展开。

## 一、这一课要解决什么问题

数据库写操作的危险，通常不在于语法太难，而在于目标范围不明确：

```text
INSERT：插入了重复数据，或者漏掉了必填字段
UPDATE：WHERE 条件写错，修改了不该修改的记录
DELETE：忘记 WHERE，删除了整张表的数据
```

实际开发中，数据修改应该形成一个稳定的习惯：

```text
先确认目标数据
    -> 编写带条件的写操作
    -> 检查影响行数
    -> 必要时放入事务
    -> 确认无误后提交
```

**学习目标：**

1. 能写出带明确字段列表的单条和多条 `INSERT`，并说清省略字段与显式 `NULL` 的区别；
2. 能处理唯一键冲突，说清 `INSERT IGNORE` 与 `ON DUPLICATE KEY UPDATE` 的适用场景和风险；
3. 能用带 `WHERE` 的 `UPDATE` / `DELETE` 修改数据，并用条件更新实现基础的库存扣减；
4. 能通过影响行数判断条件操作是否成功，并说清 `LAST_INSERT_ID()` 的用途；
5. 能区分硬删除和软删除，说清各自的代价；
6. 能把相互依赖的写操作放进合理的事务边界。

---

## 二、使用配套代码

本课不在理论文档中重复准备数据库和练习表。完整的建库、建表、初始化数据以及可执行操作，统一放在：

`code/database/04-data-modification.sql`

执行代码前，请确认使用的是专门的本地练习数据库。代码文件中的初始化数据不适合在已经存在业务数据的环境中直接重复执行。

理论文档从已有的 `users`、`products` 和 `orders` 表开始讲解数据修改语法：

```sql
SELECT * FROM users;
SELECT * FROM products;
SELECT * FROM orders;
```

---

## 三、INSERT：插入数据

`INSERT` 的常用写法：

```sql
INSERT INTO 表名 (字段1, 字段2, ...)
VALUES (值1, 值2, ...);
```

| 部分 | 含义 | 说明 |
|---|---|---|
| `表名` | 写入哪张表 | 先 `USE` 选定数据库，或写 `库名.表名` |
| `字段列表` | 本次写入哪些列 | 可以只列一部分字段 |
| `VALUES` | 和字段一一对应的值 | 数量、顺序必须和字段列表一致 |

**省略的字段**由数据库处理：有默认值用默认值，自增列自动生成编号，允许 `NULL` 则存 `NULL`。这和“显式写入 `NULL`”不是一回事，第 3 小节展开。

### 1. 插入一条记录

最推荐的写法是明确列出要写入的字段：

```sql
INSERT INTO users (email, nickname, phone)
VALUES ('alice@example.com', 'Alice', '13800000001');
```

因为 `id` 有 `AUTO_INCREMENT`，`created_at` 有默认值，所以可以省略它们。


### 2. 为什么要明确列名

不推荐这样写：

```sql
INSERT INTO users
VALUES (1, 'alice@example.com', 'Alice', NULL, NOW());
```

这种写法依赖字段的当前顺序。一旦表增加、删除或调整字段，就可能：

- 字段和值数量不匹配；
- 值写入错误的字段；
- 迁移脚本在不同环境表现不同。

推荐：

```sql
INSERT INTO users (email, nickname)
VALUES ('bob@example.com', 'Bob');
```

只列出本次确实要写入的字段，让默认值和自增字段由数据库处理。

### 3. 显式写入默认值和 `NULL`

省略字段和显式写入 `NULL` 不是一回事：

```sql
-- 省略 status，使用默认值 pending
INSERT INTO orders (user_id, order_no, total_amount)
VALUES (1, 'ORD-001', 99.00);
```

如果显式写入 `NULL`：

```sql
INSERT INTO orders (user_id, order_no, status, total_amount)
VALUES (1, 'ORD-002', NULL, 88.00);
```

由于 `status` 定义为 `NOT NULL`，这条语句通常会失败。

如果一个字段允许 `NULL`：

```sql
INSERT INTO users (email, nickname, phone)
VALUES ('carol@example.com', 'Carol', NULL);
```

这表示手机号目前没有值，不等于手机号是空字符串。

### 4. 一次插入多条记录

```sql
INSERT INTO products (name, price, stock)
VALUES
    ('Keyboard', 199.00, 10),
    ('Mouse', 59.90, 50),
    ('Monitor', 1299.00, 8);
```

批量插入通常比逐条发送多次 SQL 更高效，因为可以减少网络往返和语句解析开销。

但批量也不是越大越好。批次过大可能导致：

- 单条请求占用过多内存；
- 锁持有时间变长；
- 失败后重试成本更高；
- 事务日志增长过快。

生产环境通常会根据数据量和接口耗时选择合适的批次大小，并在事务中分批处理。

### 5. 获取新插入的主键

应用插入用户后，通常需要知道数据库生成的 `id`，例如创建订单时使用这个用户 ID。

在 MySQL 客户端中可以查看最近一次自增值：

```sql
SELECT LAST_INSERT_ID();
```

`LAST_INSERT_ID()` 的解析：

| 项目 | 说明 |
|---|---|
| 返回内容 | 当前会话最近一次 `AUTO_INCREMENT` 生成的值 |
| 参数 | 无参数 |
| 作用范围 | 会话级：只反映当前连接自己的插入，其他连接互不影响 |
| 用途 | 拿到数据库刚生成的自增主键，例如创建订单时使用这个用户 ID |

应用驱动通常会直接提供 `insertId` 或类似字段，原理和 `LAST_INSERT_ID()` 相同。不要通过“再次查询最大 ID”获取刚插入的记录：

```sql
-- 不可靠
SELECT MAX(id) FROM users;
```

并发插入时，最大 ID 可能属于另一个请求。

---

## 四、UPDATE：修改数据

`UPDATE` 的常用写法：

```sql
UPDATE 表名
SET 列1 = 值1, 列2 = 值2, ...
WHERE 条件;
```

| 部分 | 含义 | 说明 |
|---|---|---|
| `SET` | 要修改的列和值 | 可同时修改多个列；值可以是常量、表达式或另一列 |
| `WHERE` | 限定修改哪些行 | **省略 WHERE 会修改整张表** |

`SET` 的值可以是表达式，例如 `stock = stock - 1`：让数据库基于当前值计算，而不是应用先读再写（第 2、3 小节展开）。

### 1. 修改一条记录

```sql
UPDATE users
SET nickname = 'Alice Chen',
    phone = '13800000002'
WHERE id = 1;
```

执行前先确认目标：

```sql
SELECT id, email, nickname, phone
FROM users
WHERE id = 1;
```

执行后再检查：

```sql
SELECT id, email, nickname, phone
FROM users
WHERE id = 1;
```

### 2. 使用表达式更新

库存扣减不应由应用先读取数值，再把计算后的结果写回：

```text
应用读取 stock=10
应用计算 10-1=9
应用写入 stock=9
```

多个请求同时执行时，可能互相覆盖。更安全的基础写法是让数据库执行计算：

```sql
UPDATE products
SET stock = stock - 1
WHERE id = 1;
```

但这仍然允许库存减成负数，下一节会加入条件。

### 3. 条件更新

只允许库存大于 0 时扣减：

```sql
UPDATE products
SET stock = stock - 1
WHERE id = 1
  AND stock > 0;
```

执行后检查影响行数：

```text
影响行数 = 1：扣减成功
影响行数 = 0：商品不存在，或者库存已经不足
```

应用可以根据影响行数决定返回“购买成功”还是“库存不足”。这里的语句已经体现了一个重要原则：

```text
把必须同时成立的条件放进同一条 UPDATE
```

在并发场景下，这比“先 SELECT，再由应用判断，再 UPDATE”更可靠。完整的事务隔离和锁机制会在后续课程中展开。

### 4. 避免无条件 UPDATE

下面的语句会修改整张表：

```sql
UPDATE users
SET nickname = 'Unknown';
```

除非你明确就是要批量修改全部记录，否则不要执行。安全流程是：

```sql
SELECT COUNT(*)
FROM users
WHERE id BETWEEN 100 AND 200;

UPDATE users
SET nickname = 'New Name'
WHERE id BETWEEN 100 AND 200;
```

`COUNT(*)` 返回满足条件的行数（聚合语法在第 6 课展开），但实际执行前还要检查条件是否覆盖了预期数据，不能只看这一个数字。

### 5. 更新时的 NULL 处理

清空可空字段时，可以显式写 `NULL`：

```sql
UPDATE users
SET phone = NULL
WHERE id = 1;
```

如果字段是 `NOT NULL`，这条语句会失败。不要用空字符串代替 NULL，除非业务明确规定空字符串就是有效状态。

---

## 五、DELETE：删除数据

`DELETE` 的常用写法：

```sql
DELETE FROM 表名
WHERE 条件;
```

| 部分 | 含义 | 说明 |
|---|---|---|
| `表名` | 从哪张表删除 | 删除的是记录，表结构保留 |
| `WHERE` | 限定删除哪些行 | **省略 WHERE 会清空整张表** |

删除的是数据行，不是表本身；`DROP TABLE` 才会删除表结构，第 2 小节展开对比。

### 1. 删除指定记录

```sql
DELETE FROM users
WHERE id = 1;
```

删除前应该先查询同样的条件：

```sql
SELECT *
FROM users
WHERE id = 1;
```

尤其要注意外键关系。如果用户仍然被订单引用，`ON DELETE RESTRICT` 可能阻止删除。

### 2. DELETE 没有 WHERE 的风险

```sql
DELETE FROM users;
```

这会删除表中的所有记录，但不会删除表结构。它和 `DROP TABLE` 不同：

```text
DELETE FROM users：删除记录，表还在
DROP TABLE users：删除表和表结构
DROP DATABASE mysql_course：删除数据库及其中对象
```

三者都可能造成严重数据损失。生产环境执行前必须确认目标库、目标表和条件，并准备恢复方案。

### 3. 分批删除

大表删除大量数据时，不建议一次执行一个极大的删除事务：

```sql
DELETE FROM orders
WHERE created_at < '2020-01-01';
```

这种操作可能持有锁很久、产生大量 undo 和 redo，并影响线上查询。可以根据主键分批：

```sql
DELETE FROM orders
WHERE id >= 1
  AND id < 10001
  AND created_at < '2020-01-01';
```

然后继续处理下一批。批次大小要结合表规模、索引和线上负载测试，不能机械固定。

### 4. 软删除

很多业务不直接删除记录，而是增加删除标记：

```sql
ALTER TABLE users
ADD COLUMN deleted_at DATETIME NULL;
```

软删除：

```sql
UPDATE users
SET deleted_at = CURRENT_TIMESTAMP
WHERE id = 1
  AND deleted_at IS NULL;
```

查询未删除记录：

```sql
SELECT *
FROM users
WHERE deleted_at IS NULL;
```

软删除的优点：

- 便于恢复；
- 保留历史记录；
- 避免立即破坏关联数据。

代价是：

- 每次查询都要记得过滤；
- 数据会持续占用空间；
- 唯一约束设计更复杂；
- 大表需要归档。

软删除不是“永远不删除”，通常还需要定期归档或物理清理策略。

---

## 六、影响行数到底表示什么

应用执行 `UPDATE` 或 `DELETE` 后，通常会收到影响行数。它是判断业务操作结果的重要依据，但必须理解它的语义。

例如：

```sql
UPDATE products
SET stock = stock - 1
WHERE id = 1
  AND stock > 0;
```

通常可以这样判断：

```text
影响行数为 1：有一行满足条件并完成更新
影响行数为 0：没有满足条件的行，或值没有实际变化（取决于驱动配置）
```

严格判断时，要结合数据库驱动对“匹配行数”和“实际改变行数”的返回方式。对于库存扣减这种表达式更新，成功时通常确实发生了值变化，因此影响行数判断比较直观。

版本号乐观锁也依赖同样的思想（假设 `accounts` 表有 `balance` 余额和 `version` 版本号两列）：

```sql
UPDATE accounts
SET balance = 90,
    version = version + 1
WHERE id = 1
  AND version = 7;
```

```text
影响行数 = 1：版本匹配，更新成功
影响行数 = 0：版本已经变化，需要重新读取或提示冲突
```

后续课程会把它和乐观锁、并发更新结合起来。

---

## 七、唯一键冲突

假设 `users.email` 有唯一约束：

```sql
UNIQUE KEY uk_users_email (email)
```

再次插入相同邮箱：

```sql
INSERT INTO users (email, nickname)
VALUES ('alice@example.com', 'Alice 2');
```

MySQL 会返回类似错误：

```text
Duplicate entry 'alice@example.com' for key 'uk_users_email'
```

这不是数据库故障，而是数据库在执行唯一性规则。应用应该根据业务决定：

```text
注册：提示邮箱已存在
导入：记录冲突并继续处理其他数据
同步：更新已存在记录
幂等请求：把重复请求视为已经完成
```

### 1. `INSERT IGNORE`

在 `INSERT` 后加 `IGNORE`，语法与普通插入一致：

```sql
INSERT IGNORE INTO users (email, nickname)
VALUES ('alice@example.com', 'Alice 2');
```

遇到某些可忽略的错误（例如重复唯一键）时，MySQL 将错误转为警告，语句继续执行；重复唯一键时通常不会插入新记录。

这里要区分两个层次：**唯一键约束定义“不许重复”的规则，`INSERT IGNORE` 只决定违反规则时的处理方式**——它不改变约束，重复的行依然不会插入，只是把“报错中止整条语句”换成“跳过这一行、继续执行”。典型场景是批量导入：1 万行里混了几条重复，普通 `INSERT` 会整体失败，`INSERT IGNORE` 跳过重复行、其余照常导入。

但 `INSERT IGNORE` 可能掩盖其他数据问题，例如非法值被调整或警告被忽略。不要在不了解副作用的情况下把所有批量导入都改成 `INSERT IGNORE`。

### 2. `ON DUPLICATE KEY UPDATE`

需要“存在则更新，不存在则插入”时，可以在 `INSERT` 后面追加冲突处理分支：

```sql
INSERT INTO 表名 (字段列表)
VALUES (值列表)
ON DUPLICATE KEY UPDATE
    列1 = 值1, 列2 = 值2, ...;
```

完整例子：

```sql
INSERT INTO products (id, name, price, stock)
VALUES (1, 'Keyboard', 199.00, 20)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    price = VALUES(price),
    stock = VALUES(stock);
```

| 部分 | 含义 | 说明 |
|---|---|---|
| `ON DUPLICATE KEY UPDATE` | 插入遇到唯一键冲突时改走更新 | 主键或任意唯一键冲突都会进入更新分支 |
| `VALUES(列名)` | 引用“本次 INSERT 语句为该列提供的值” | 只在这个更新分支里使用 |

这类语句适合配置同步、缓存表刷新等场景。需要注意：主键或其他唯一键冲突都可能进入更新分支，设计时要明确哪一个唯一约束代表业务身份。

MySQL 8.0.20 起官方推荐用别名写法取代 `VALUES()`（后者已标记废弃，8.x 仍可用）：

```sql
INSERT INTO products (id, name, price, stock) AS new
VALUES (1, 'Keyboard', 199.00, 20)
ON DUPLICATE KEY UPDATE
    name = new.name,
    price = new.price,
    stock = new.stock;
```

正式项目应结合目标版本文档和测试验证。

### 3. 不要把冲突处理和业务幂等混为一谈

数据库唯一约束可以防止重复数据，但不自动解决整个业务请求的幂等问题。

例如支付请求重复到达时，除了给支付单号加唯一约束，还要考虑：

- 重复请求是否返回第一次的结果；
- 扣款是否只执行一次；
- 网络超时后客户端如何重试；
- 订单状态如何流转。

唯一约束是幂等设计的一部分，不是全部。

---

## 八、事务中执行数据修改

如果一个业务包含多条相互依赖的写操作，应考虑放在同一个事务中。事务由三个语句控制：

| 语句 | 含义 |
|---|---|
| `START TRANSACTION` | 开启一个事务，之后的操作一起生效或一起回滚 |
| `COMMIT` | 提交：确认事务内的所有修改生效 |
| `ROLLBACK` | 回滚：作废事务内的所有修改 |

示例：

```sql
START TRANSACTION;

UPDATE products
SET stock = stock - 1
WHERE id = 1
  AND stock > 0;

-- 应用检查影响行数
-- 如果扣减失败，则回滚

INSERT INTO orders (user_id, order_no, total_amount)
VALUES (1, 'ORD-003', 199.00);

COMMIT;
```

如果库存不足：

```sql
ROLLBACK;
```

这样订单插入和库存扣减不会只成功一半。

但仅写出 `START TRANSACTION` 还不够，应用还需要保证：

- 所有相关 SQL 使用同一个数据库连接；
- 成功路径一定提交；
- 异常路径一定回滚；
- 连接归还连接池前没有遗留事务；
- 事务中不执行长时间网络请求。

事务和并发锁会在第 9 至第 13 课详细学习，这里先建立“相关写操作要有清晰边界”的习惯。

---

## 九、完整练习

本课的完整练习顺序已经放入 `code/database/04-data-modification.sql`，包括：

```text
插入用户和商品
    -> 查看自增 ID
    -> 处理唯一键冲突
    -> 使用条件更新扣减库存
    -> 创建订单并更新状态
    -> 执行软删除
    -> 在事务中组合库存扣减和订单创建
```

阅读理论时只需要关注每一步为什么这样写；需要实际运行时再打开代码文件。

---

## 十、常见错误自查清单

- 插入不写字段列表：表结构一变，语句就可能失败或把值写错字段。插入时明确列名。
- `UPDATE` 或 `DELETE` 忘记 `WHERE`：会修改或删除整张表。执行前先用同样条件的 `SELECT` 确认目标，必要时放进事务。
- 先 `SELECT` 再由应用计算并 `UPDATE`：并发下两个请求会互相覆盖。让数据库执行条件更新。
- 用 `MAX(id)` 获取刚插入的记录：并发时可能拿到别人的 ID。用 `LAST_INSERT_ID()` 或驱动的 `insertId`。
- 用 `INSERT IGNORE` 掩盖所有错误：数据问题会变成警告。批量导入要记录冲突和警告。
- 只看 SQL 执行成功、不检查影响行数：条件更新影响行数为 0 时业务并没有完成。库存、订单状态和版本号更新都要检查影响行数。

---

## 十一、验收问题

1. 插入时明确字段列表和不写字段列表有什么区别？
2. 省略字段、显式写 `NULL`、显式写默认值，三者各会发生什么？
3. 唯一键冲突有哪些处理方式？`INSERT IGNORE` 的风险是什么？
4. `ON DUPLICATE KEY UPDATE` 在什么情况下进入更新分支？`VALUES(列)` 表示什么？
5. 如何避免库存扣成负数？影响行数 0 和 1 各代表什么？
6. 为什么不能用 `MAX(id)` 获取刚插入的记录？`LAST_INSERT_ID()` 返回的是什么？
7. `DELETE FROM users` 和 `DROP TABLE users` 有什么区别？
8. 软删除有什么优缺点？查询时要注意什么？
9. 为什么相互依赖的写操作要放进事务？事务里要注意什么？

---

## 十二、面试回答模板

### 题目：为什么 INSERT 时要明确写字段名？

> 明确字段列表可以避免依赖表的物理字段顺序，也能让默认值和自增字段由数据库处理。表结构变化后，不写字段列表的语句可能出现数量不匹配或数据写入错误，所以业务 SQL 通常应该明确列出字段。

### 题目：如何避免库存扣成负数？

> 可以使用带条件的原子更新：`UPDATE products SET stock = stock - 1 WHERE id = ? AND stock > 0`，然后根据影响行数判断扣减是否成功。相比先查询库存、再由应用计算并更新，这种方式把检查和修改放在同一条 SQL 中。高并发场景还要结合事务和锁进一步分析。

### 题目：唯一键冲突时怎么处理？

> 先根据业务语义决定：注册场景通常提示已存在，导入场景可以记录冲突并继续，同步场景可以使用更新，幂等请求则需要返回已有结果。数据库层通过唯一约束防止重复，应用层捕获冲突并决定业务响应，不能简单地用 `INSERT IGNORE` 掩盖所有错误。

### 题目：软删除有什么优缺点？

> 软删除通过 `deleted_at` 等字段标记记录，能够保留历史并便于恢复，也能减少直接删除对关联数据的破坏。缺点是每次查询都要过滤，唯一约束和数据归档更复杂，数据也会持续占用空间。它适合需要审计或恢复的业务，但仍应配合长期归档和清理策略。

---

## 十三、这一课学到什么程度可以继续

```text
能使用明确字段列表插入单条和多条记录
能理解默认值、自增 ID 和显式 NULL 的区别
能处理唯一键冲突，并知道 INSERT IGNORE 的风险
能写带 WHERE 的 UPDATE 和 DELETE
能使用条件更新实现基础的库存扣减
能通过影响行数判断条件操作是否成功
能区分硬删除和软删除
能把相关写操作放进合理的事务边界
能说出 UPDATE、DELETE 忘记 WHERE 的风险
```

下一课将学习聚合、JOIN、子查询与 CTE，重点回答：

```text
COUNT(*) 和 COUNT(列) 为什么结果不同？
INNER JOIN 和 LEFT JOIN 有什么区别？
ON 和 WHERE 有什么区别？
EXISTS 适合什么场景？
```
