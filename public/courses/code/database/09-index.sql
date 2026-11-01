-- 第七课：InnoDB 索引与索引设计
-- 适用：MySQL 8.x / InnoDB
-- 默认使用第三课脚本创建的 mysql_course 数据库和业务表。

USE mysql_course;

CREATE INDEX idx_users_email
ON users(email);

CREATE INDEX idx_users_email_nickname
ON users(email, nickname);

CREATE INDEX idx_orders_user_status_time
ON orders(user_id, status, created_at);

SELECT email, nickname
FROM users
WHERE email = 'alice@example.com';

SELECT id, order_no, created_at
FROM orders
WHERE user_id = 1
  AND status = 'paid'
ORDER BY created_at DESC
LIMIT 20;

SELECT id, order_no, created_at
FROM orders
WHERE status = 'paid';

SELECT id, order_no, created_at
FROM orders
WHERE created_at >= '2026-01-01'
  AND created_at < '2027-01-01';

-- 对照观察：对索引列使用函数。
SELECT id, order_no
FROM orders
WHERE YEAR(created_at) = 2026;

-- 与上面的查询语义相同，但更容易利用时间列的有序性。
SELECT id, order_no
FROM orders
WHERE created_at >= '2026-01-01'
  AND created_at < '2027-01-01';

-- 查看表上的索引。
SHOW INDEX FROM users;
SHOW INDEX FROM orders;

-- 练习结束后，可按需删除本课创建的索引。
-- DROP INDEX idx_users_email ON users;
-- DROP INDEX idx_users_email_nickname ON users;
-- DROP INDEX idx_orders_user_status_time ON orders;
