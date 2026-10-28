# 第八课：SQLite 特有语法与内部结构

> MySQL 课程已经覆盖了通用的插入、更新和唯一约束。本课只学习 SQLite 中值得单独理解的能力：`rowid`、`INTEGER PRIMARY KEY`、`AUTOINCREMENT`、UPSERT、`RETURNING`、`WITHOUT ROWID`，以及 SQLite 常见的日期、JSON 和全文搜索扩展。
>
> 完整可运行代码见 `code/database-sqlite/database_lesson08.py`。

## 一、这一课要解决什么问题

SQLite 有一些实现和语法值得单独记住：

```text
为什么 INTEGER PRIMARY KEY 可以直接使用 rowid？
AUTOINCREMENT 是不是所有自增主键都需要？
SQLite 如何写 UPSERT 和 RETURNING？
SQLite 的日期时间、JSON 和全文搜索为什么需要特殊理解？
```

这些能力是 SQLite 的特色，不能直接把 MySQL 的自增、日期类型和扩展行为照搬过来。

## 二、rowid 和 INTEGER PRIMARY KEY

普通 SQLite 表通常是 rowid 表。即使没有显式定义主键，SQLite 也会为每行维护一个整数 `rowid`：

```sql
SELECT rowid, name
FROM products;
```

如果定义：

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
```

这里的 `id` 会成为 rowid 的别名：

```text
id、rowid、_rowid_ 通常指向同一个内部行编号
```

这不是所有整数类型声明都成立。必须是 SQLite 特殊形式的 `INTEGER PRIMARY KEY`，而不是类似 MySQL 的任意整数主键写法。

### 1. 为什么这很重要

`INTEGER PRIMARY KEY`：

- 不需要额外维护一棵独立的整数主键索引；
- 插入时可以省略 ID，由 SQLite 生成；
- 查询主键时直接访问 rowid；
- 是 SQLite 中最常见的轻量主键设计。

但 rowid 只是内部行标识，不应该自动当作业务订单号、时间顺序或安全不可猜测的公开 ID。

## 三、AUTOINCREMENT 的真实含义

可以这样定义：

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
```

`AUTOINCREMENT` 的主要保证是：已经使用过的较大 rowid 不会因为对应记录被删除而再次使用。它并不让插入更快，反而需要额外维护 `sqlite_sequence` 表。

通常的选择是：

```text
只需要唯一整数主键：INTEGER PRIMARY KEY
必须避免复用历史 rowid：再考虑 AUTOINCREMENT
```

不要因为“自增”三个字就默认使用 `AUTOINCREMENT`。大多数本地业务表只需要 `INTEGER PRIMARY KEY`。

## 四、SQLite 的 UPSERT

SQLite 支持基于唯一约束的冲突处理：

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO settings (key, value)
VALUES ('theme', 'dark')
ON CONFLICT(key) DO UPDATE SET
    value = excluded.value;
```

这里的 `excluded.value` 表示本次尝试插入、但因为冲突而被排除的值。

如果冲突时直接忽略：

```sql
INSERT INTO settings (key, value)
VALUES ('theme', 'light')
ON CONFLICT(key) DO NOTHING;
```

UPSERT 的前提是存在主键或唯一约束。没有明确的冲突目标，数据库不知道“已经存在”应该依据哪个字段判断。

## 五、RETURNING

SQLite 支持在写入语句后返回受影响的记录：

```sql
INSERT INTO settings (key, value)
VALUES ('language', 'zh-CN')
RETURNING rowid, key, value;
```

更新后返回结果：

```sql
UPDATE settings
SET value = 'en-US'
WHERE key = 'language'
RETURNING key, value;
```

删除前或删除后需要知道具体记录时，也可以使用：

```sql
DELETE FROM settings
WHERE key = 'language'
RETURNING key, value;
```

使用 Python `sqlite3` 时，可以像读取普通查询一样读取结果：

```python
row = connection.execute(
    """
    INSERT INTO settings (key, value)
    VALUES (?, ?)
    RETURNING rowid, key, value
    """,
    ("timezone", "UTC"),
).fetchone()
```

要确认目标 SQLite 版本支持 `RETURNING`。如果项目需要兼容旧版本，应使用插入后读取 ID 或其他兼容方案，并做好并发边界设计。

## 六、WITHOUT ROWID

默认的普通表通常是 rowid 表。对于合适的联合主键表，可以使用：

```sql
CREATE TABLE user_tenants (
    user_id INTEGER NOT NULL,
    tenant_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (user_id, tenant_id)
) WITHOUT ROWID;
```

`WITHOUT ROWID` 表不维护隐含的 rowid，而是直接按照主键组织。它可能适合：

- 联合主键本身就是主要访问方式；
- 不需要额外整数 rowid；
- 希望避免重复存储主键结构。

它也有约束和使用差异，不能因为名字特殊就默认更快。需要使用时，应通过实际数据和查询计划验证。

## 七、SQLite 的日期时间

SQLite 没有 MySQL 那种独立的 `DATETIME` 存储类型。日期时间通常以以下形式之一保存：

```text
TEXT：例如 2026-10-18 16:00:00
INTEGER：例如 Unix 时间戳
REAL：儒略日数
```

如果使用文本，推荐统一使用可按字典序比较的格式：

```sql
INSERT INTO events (created_at)
VALUES ('2026-10-18 16:00:00');
```

SQLite 提供日期时间函数，但它们主要是函数处理，不代表字段拥有 MySQL `DATETIME` 那样的严格类型保证。应用必须统一时区、精度和格式。

## 八、JSON1 扩展

SQLite 可以通过 JSON1 扩展处理 JSON 文本：

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    data TEXT NOT NULL
);

INSERT INTO documents (data)
VALUES ('{"name":"Alice","role":"admin"}');

SELECT json_extract(data, '$.name') AS name
FROM documents;
```

这里的 `data` 本质上仍然是文本，JSON 函数负责解析它。需要注意：

- JSON 是否可用取决于 SQLite 构建和版本；
- JSON 字段不会自动拥有关系型字段的约束；
- 高频筛选字段通常适合拆成普通列；
- JSON 适合结构变化较大、访问频率较低的扩展数据。

不要把 JSON 当成逃避表结构设计的方式。需要唯一性、范围查询和强约束时，普通字段通常更清晰。

## 九、FTS5 全文搜索

普通 `LIKE '%关键词%'` 适合小数据量的简单匹配，但不适合复杂全文搜索。SQLite 可以使用 FTS5：

```sql
CREATE VIRTUAL TABLE notes_fts
USING fts5(title, body);

INSERT INTO notes_fts (title, body)
VALUES ('SQLite', 'SQLite is a file database');

SELECT title, body
FROM notes_fts
WHERE notes_fts MATCH 'SQLite';
```

FTS5 是虚拟表和扩展能力，是否可用取决于 SQLite 构建。它适合关键词搜索、分词和全文索引场景，但不等同于普通表上的 `LIKE`，中文分词效果还需要结合具体 tokenizer 和外部搜索方案评估。

## 十、常见错误

- 把所有整数主键都当成 rowid 别名；
- 为了自增就无条件使用 `AUTOINCREMENT`；
- 没有唯一约束却使用 UPSERT；
- 不确认 SQLite 版本就使用 `RETURNING`；
- 把 SQLite 的日期文本当成严格的日期类型；
- 把 JSON 文本当成自动受约束的结构化字段；
- 把 FTS5 当成普通 `LIKE` 的简单替换；
- 没有验证编译选项就假设 JSON1 或 FTS5 一定可用。

## 十一、面试回答模板

### 题目：SQLite 的 rowid 是什么？

> 普通 SQLite 表通常有一个隐含的整数 rowid，用于标识行。如果表定义为 `INTEGER PRIMARY KEY`，这个字段会成为 rowid 的别名。它适合做内部整数主键，但不应该自动当成业务编号或安全的公开 ID。

### 题目：AUTOINCREMENT 有什么作用？

> 它主要保证已经使用过的较大 rowid 不会因为记录删除而再次使用。它会增加额外维护成本，不是普通自增主键的默认必需品。只需要唯一整数主键时，通常使用 `INTEGER PRIMARY KEY` 就够了。

### 题目：SQLite 如何实现 UPSERT？

> 先为业务冲突字段建立主键或唯一约束，再使用 `INSERT ... ON CONFLICT(...) DO UPDATE` 或 `DO NOTHING`。冲突目标必须明确，否则数据库无法判断哪种重复应该触发更新。

## 十二、这一课学到什么程度可以继续

```text
能解释 rowid 和 INTEGER PRIMARY KEY 的关系
能说明 AUTOINCREMENT 的作用和代价
能使用 ON CONFLICT 实现 UPSERT
能使用 RETURNING 读取写操作结果
知道 WITHOUT ROWID 适合什么类型的表
能说明 SQLite 日期时间的常见保存方式
知道 JSON1 和 FTS5 是扩展能力，需确认版本和构建支持
```

下一课将学习 SQLite 备份、恢复与完整性检查。
