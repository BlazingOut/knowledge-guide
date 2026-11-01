# SQLite 专题

这条课程线建立在 MySQL 正式课程之上，不再重复讲一遍通用 SQL。MySQL 课程已经覆盖数据库对象、数据类型、约束、增删改查、聚合、JOIN、子查询、窗口函数、索引、执行计划、事务、MVCC、锁、日志和线上排查。

本课程只学习 SQLite 特有的实现和使用方式：数据库文件模型、Python `sqlite3`、动态类型、外键开关、单写者事务模型、WAL、SQLite 查询计划、`rowid`、SQLite 特有语法、备份恢复和适用边界。

SQLite 是真实在用的数据库：数据保存为一个文件，由使用它的程序直接打开，不需要单独启动数据库服务器。浏览器、手机应用、桌面软件、嵌入式程序、测试环境和本仓库的 Life Manager 都可能使用这种方式。

## 课程定位

```text
MySQL 正式课程：学习通用 SQL 和服务器数据库核心原理
    -> SQLite 专题：学习 SQLite 与服务器数据库不同的行为和实现
```

本课程不把 SQLite 的结论推广到 MySQL，也不把 MySQL 的 InnoDB 模型机械套到 SQLite：

```text
SQLite：文件数据库、单写者、WAL、sqlite3 API
MySQL：独立服务器、InnoDB、行锁、MVCC、redo/binlog
```

## 旧版资料说明

原有第 1 至第 5 课笔记仍然保留在本目录，作为早期的 SQLite/SQL 入门资料继续可用：

- [第 1 课：数据库、表和记录](./01-tables-and-records.md)
- [第 2 课：条件查询和排序](./02-filtering-sorting.md)
- [第 3 课：修改和删除记录](./03-update-delete.md)
- [第 4 课：表结构、数据类型和表结构修改](./04-schema.md)
- [第 5 课：约束和数据完整性](./05-constraints.md)

对应代码在 `code/database-sqlite/`。它们属于早期入门资料，不再作为完成 MySQL 后的正式学习顺序。后续新增或修改的专题课统一放在本目录，不要再复制到 `courses/后端基础/database/`。

## 前置知识

默认已经完成 MySQL 正式课程前 8 课，能够读写基础 SQL，理解表、约束、事务、JOIN、聚合和子查询。

还需要：

- 能运行 Python 文件；
- 知道函数、异常和基本文件路径；
- 了解 MySQL 是独立数据库服务器；
- 能阅读简单的 SQL 和 Python 代码。

本课程不从 `CREATE TABLE`、`SELECT`、`JOIN` 等通用语法重新开始。需要用到时只回顾 SQLite 与 MySQL 的行为差异。

## 课程顺序

### 第 1 课：SQLite 文件数据库模型

目标：理解 SQLite 与 MySQL Server 的部署和存储差异，知道 SQLite 适合什么场景。

内容：数据库就是一个文件；文件路径和权限；应用进程直接打开数据库；多个进程访问同一个文件；SQLite 不需要独立服务；数据库文件中可以保存表、索引和元数据；SQLite 适合本地、嵌入式、桌面、移动端、测试和小型单机服务；多实例共享写入和高并发写入的边界。

实践：用 Python 创建数据库文件，查看文件生成位置；用两个连接打开同一个文件，观察它们访问的是同一份数据。

面试考点：SQLite 和 MySQL 的核心差异；为什么 Web 多实例共享业务通常使用 MySQL；SQLite 文件应该如何部署和保护。

### 第 2 课：Python `sqlite3` 连接与查询

目标：能够在 Python 中正确打开 SQLite、执行参数化 SQL、读取结果并关闭连接。

内容：`sqlite3.connect`；连接和游标；`execute`、`executemany`；`fetchone`、`fetchall`；`row_factory`；`?` 占位符；Python 类型与 SQLite 类型转换；连接生命周期；上下文管理；异常处理；`sqlite3.IntegrityError`；为什么不能把参数拼接到 SQL 字符串。

实践：使用 Python 完成一次参数化查询、批量插入和异常处理，并确认连接关闭后没有遗留未提交事务。

面试考点：Python 如何连接 SQLite；参数化查询解决什么问题；游标、连接和事务分别负责什么。

### 第 3 课：SQLite 类型系统与 STRICT 表

目标：理解 SQLite 的动态类型和 type affinity，不把 MySQL 的严格字段类型直接套到 SQLite。

内容：SQLite 的 `NULL`、`INTEGER`、`REAL`、`TEXT`、`BLOB` 五种存储类别；声明类型与实际存储类型；type affinity；数字和字符串的转换；布尔值通常使用 `0` 和 `1`；日期时间通常使用文本、整数或实数保存；SQLite 与 MySQL `INT`、`VARCHAR`、`DATETIME` 的差异；`STRICT` 表；动态类型的灵活性和数据质量风险。

实践：向普通表和 `STRICT` 表写入不同类型的值，使用 `typeof()` 比较实际存储类型，并观察 Python 读取结果。

面试考点：SQLite 为什么是动态类型；type affinity 是什么；SQLite 如何保存日期时间；什么时候使用 `STRICT` 表。

### 第 4 课：SQLite 约束与外键开关

目标：掌握 SQLite 约束的实际行为，尤其是外键默认不一定启用的问题。

内容：主键、`NOT NULL`、`UNIQUE`、`CHECK` 的 SQLite 行为；`PRAGMA foreign_keys = ON`；外键约束是连接级别设置；为什么建了外键却没有生效；`ON DELETE CASCADE`；Python 创建连接后如何主动开启外键；如何用测试确认约束真的生效。

实践：在两个独立连接中分别检查和设置 `foreign_keys`，尝试插入不存在的父记录，比较开启和未开启时的结果。

面试考点：SQLite 外键为什么可能不生效；`PRAGMA foreign_keys` 的作用范围；如何保证应用创建的每个连接都开启外键。

### 第 5 课：SQLite 事务和单写者模型

目标：理解 SQLite 文件级并发的特点，能够排查 `database is locked`。

内容：`BEGIN`、`COMMIT`、`ROLLBACK`；自动提交；`BEGIN DEFERRED`、`BEGIN IMMEDIATE`、`BEGIN EXCLUSIVE`；SQLite 通常只有一个写入者；多个读者的并发；写事务等待；`busy_timeout`；Python 连接超时；如何缩短写事务；为什么不能把 SQLite 的并发模型理解成 InnoDB 行锁。

实践：用两个 Python 连接制造写入等待，观察锁错误和超时；比较不同 `BEGIN` 模式的行为。

面试考点：SQLite 是否支持并发；为什么出现 `database is locked`；SQLite 和 MySQL 行锁模型有什么区别；如何减少写锁冲突。

### 第 6 课：WAL 与 SQLite 读写并发

目标：理解 WAL 如何改善 SQLite 的读写并发，以及它没有解决什么问题。

内容：rollback journal；WAL 的基本工作方式；`PRAGMA journal_mode = WAL`；读者读取旧快照、写者追加 WAL；WAL 仍然只有一个写入者；WAL 和 `-wal`、`-shm` 文件；长读事务导致 WAL 增长；checkpoint；多进程访问的注意事项；WAL 不等于高并发写入，也不等于 MySQL 的 MVCC 和行锁。

实践：在两个连接中比较默认 journal 模式和 WAL 模式下的读写行为，观察 WAL 文件和 checkpoint 的影响。

面试考点：WAL 解决什么问题；WAL 为什么仍然只有一个写入者；长事务为什么会使 WAL 文件变大。

### 第 7 课：SQLite 的索引与查询计划

目标：使用 SQLite 的工具判断查询是否扫描全表、是否使用索引或覆盖索引。

内容：`CREATE INDEX`；联合索引列顺序；`EXPLAIN QUERY PLAN`；`SCAN`；`SEARCH`；`USING INDEX`；`USING COVERING INDEX`；SQLite 查询计划和 MySQL `EXPLAIN` 的差异；SQLite 不使用 InnoDB 聚簇索引、回表模型；统计信息对计划的影响；只从 SQLite 输出理解访问路径，不重复讲 B+ 树和 InnoDB 索引结构。

实践：对同一条查询分别查看无索引、普通索引和覆盖索引计划，比较 `SCAN`、`SEARCH` 和 `USING COVERING INDEX`。

面试考点：如何查看 SQLite 是否使用索引；`SCAN` 和 `SEARCH` 的区别；SQLite 的 `EXPLAIN QUERY PLAN` 与 MySQL `EXPLAIN` 有什么不同。

### 第 8 课：SQLite 特有语法与内部结构

目标：掌握 MySQL 课程没有重点覆盖的 SQLite 特有能力。

内容：`INSERT OR IGNORE`；`INSERT ... ON CONFLICT`；UPSERT；`RETURNING`；`rowid`；`INTEGER PRIMARY KEY` 与 rowid 的关系；`AUTOINCREMENT` 的真实含义和代价；`WITHOUT ROWID`；SQLite 日期函数；JSON1 扩展；FTS5 全文搜索；这些扩展的版本和编译选项限制。

实践：分别使用 UPSERT、`RETURNING` 和 `rowid` 完成小型数据操作，比较 `INTEGER PRIMARY KEY` 与 `AUTOINCREMENT` 的行为。

面试考点：SQLite 的 `rowid` 是什么；`INTEGER PRIMARY KEY` 为什么特殊；`AUTOINCREMENT` 解决什么问题又带来什么代价；SQLite 如何做全文搜索。

### 第 9 课：SQLite 备份、恢复与完整性检查

目标：能够设计 SQLite 文件的安全备份和恢复流程，而不是简单复制正在使用的文件。

内容：直接复制数据库文件的风险；WAL 模式下的备份注意事项；`VACUUM INTO`；Python Online Backup API；`PRAGMA integrity_check`；`PRAGMA quick_check`；恢复时替换数据库文件；备份文件可恢复性验证；SQLite 没有 MySQL binlog 和主从复制；文件备份与应用停机窗口。

实践：生成数据库备份，执行完整性检查，在临时路径恢复并验证表和数据；比较正常关闭、WAL 模式和正在写入时的备份注意事项。

面试考点：SQLite 如何备份；为什么不能无条件直接复制数据库文件；如何检查数据库文件是否损坏；SQLite 为什么没有 MySQL 的 binlog 主从恢复体系。

### 第 10 课：SQLite 的真实使用边界

目标：能够判断项目应该继续使用 SQLite，还是迁移到 MySQL/PostgreSQL。

内容：浏览器、桌面、移动端、嵌入式和本地缓存；单机工具和测试数据库；小型 Web 服务；多进程、多实例和共享文件系统风险；并发写入、备份、权限和监控；什么时候 SQLite 足够；什么时候需要服务器数据库；从 SQLite 迁移时的数据类型、SQL 方言、并发模型、连接方式和备份策略差异；阅读 Life Manager 的 SQLite 存储模块。

实践：分析一个本地应用和一个多实例 Web 服务，分别说明继续使用 SQLite 或迁移到 MySQL/PostgreSQL 的理由。

面试考点：SQLite 适合什么场景；SQLite 为什么不适合高并发写入；什么时候应该从 SQLite 迁移到服务器数据库。

## 阶段验收

完成本专题后，应当能够：

1. 说明 SQLite 文件数据库和 MySQL Server 的部署差异。
2. 在 Python 中正确使用 `sqlite3` 连接、参数化查询、事务和异常处理。
3. 解释 SQLite 的五种存储类别、type affinity 和 `STRICT` 表。
4. 说明为什么必须显式开启 `PRAGMA foreign_keys = ON`。
5. 解释 SQLite 的单写者模型、锁等待、事务模式和 `busy_timeout`。
6. 解释 WAL 改善了什么、没有解决什么，以及长读事务的影响。
7. 使用 `EXPLAIN QUERY PLAN` 判断 `SCAN`、`SEARCH` 和覆盖索引。
8. 读懂 `rowid`、`INTEGER PRIMARY KEY`、UPSERT、`RETURNING` 等 SQLite 特有能力。
9. 完成 SQLite 数据库的备份、完整性检查和恢复验证。
10. 判断一个项目继续使用 SQLite 还是迁移到 MySQL/PostgreSQL。

## 编写约束

- 不重复编写 MySQL 课程已经覆盖的通用 SQL 入门内容；只在说明 SQLite 差异时使用必要 SQL。
- 每条结论明确是 SQLite 特有行为，不能把 SQLite 的单写者、WAL 或动态类型推广到 MySQL。
- 理论课文放在 `courses/后端基础/database-sqlite/`，完整脚本和 Python 实验放在 `code/database-sqlite/`。
- 课文中的完整示例拆到代码文件，理论文档只保留理解概念所需的关键片段。
- SQLite 的默认行为、编译选项和版本差异要明确说明，不能把某个环境的结果说成永远如此。
- 涉及数据库文件、WAL、备份和恢复时，优先使用临时练习库，避免对真实业务文件执行破坏性操作。
- 旧版第 1 至第 5 课保留为历史资料；后续专题课不再从零讲 SQL。
- 下一课具体编写顺序等用户指定。
