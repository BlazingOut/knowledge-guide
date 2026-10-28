-- 第五课（聚合、子查询与 CTE 篇）：聚合、子查询与 CTE
-- 适用：MySQL 8.x / InnoDB
-- 依赖第三课脚本创建的 mysql_course 数据库和业务表；多表关联示例见 05-join.sql。

USE mysql_course;

SELECT COUNT(*) AS order_count,
       SUM(total_amount) AS total_amount
FROM orders;

SELECT COUNT(*) AS all_rows,
       COUNT(phone) AS rows_with_phone,
       COUNT(DISTINCT phone) AS distinct_phones
FROM users;

SELECT status, COUNT(*) AS order_count
FROM orders
GROUP BY status;

SELECT user_id, status, COUNT(*) AS order_count
FROM orders
GROUP BY user_id, status;

SELECT user_id, COUNT(*) AS order_count
FROM orders
WHERE status = 'paid'
GROUP BY user_id
HAVING COUNT(*) >= 3;

SELECT id, order_no, total_amount
FROM orders
WHERE total_amount > (SELECT AVG(total_amount) FROM orders);

SELECT id, nickname
FROM users
WHERE id IN (SELECT user_id FROM orders);

SELECT u.id, u.nickname
FROM users AS u
WHERE EXISTS (
    SELECT 1 FROM orders AS o WHERE o.user_id = u.id
);

SELECT u.id, u.nickname
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1 FROM orders AS o WHERE o.user_id = u.id
);

WITH paid_orders AS (
    SELECT user_id, total_amount
    FROM orders
    WHERE status = 'paid'
)
SELECT user_id, SUM(total_amount) AS paid_amount
FROM paid_orders
GROUP BY user_id;
