-- 第八课：EXPLAIN、慢查询与查询优化
-- 适用：MySQL 8.x / InnoDB
-- 默认使用第三课脚本创建的 mysql_course 数据库和业务表。

USE mysql_course;

EXPLAIN
SELECT id, order_no, created_at
FROM orders
WHERE user_id = 1
  AND status = 'paid'
ORDER BY created_at DESC
LIMIT 20;

EXPLAIN
SELECT id, order_no
FROM orders
WHERE id = 1;

EXPLAIN
SELECT id, order_no
FROM orders
WHERE status = 'paid';

EXPLAIN
SELECT id, order_no
FROM orders
WHERE created_at >= '2026-01-01'
  AND created_at < '2027-01-01';

-- 对照观察：对索引列使用函数。
EXPLAIN
SELECT id, order_no
FROM orders
WHERE YEAR(created_at) = 2026;

EXPLAIN
SELECT id, order_no
FROM orders
WHERE created_at >= '2026-01-01'
  AND created_at < '2027-01-01';

-- MySQL 8 会实际执行下面的查询，并展示实际运行信息。
-- EXPLAIN ANALYZE
-- SELECT id, order_no
-- FROM orders
-- WHERE user_id = 1;

SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- 需要权限，且会影响实例；只在专门的测试环境中按需执行。
-- SET GLOBAL long_query_time = 1;

-- 大 OFFSET 与键集分页对照。
EXPLAIN
SELECT id, order_no
FROM orders
ORDER BY id
LIMIT 1000000, 20;

EXPLAIN
SELECT id, order_no
FROM orders
WHERE id > 1000000
ORDER BY id
LIMIT 20;
