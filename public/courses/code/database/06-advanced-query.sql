-- 第六课：MySQL 8 高级查询语法
-- 适用：MySQL 8.x / InnoDB
-- 默认使用第三课脚本创建的 mysql_course 数据库和业务表。

USE mysql_course;

SELECT id, email FROM users WHERE id <= 10
UNION ALL
SELECT id, email FROM users WHERE id > 10
ORDER BY id;

SELECT id, user_id, order_no, created_at,
       ROW_NUMBER() OVER (
           PARTITION BY user_id
           ORDER BY created_at DESC, id DESC
       ) AS row_num
FROM orders;

SELECT id, user_id, total_amount,
       RANK() OVER (
           PARTITION BY user_id ORDER BY total_amount DESC
       ) AS amount_rank,
       DENSE_RANK() OVER (
           PARTITION BY user_id ORDER BY total_amount DESC
       ) AS dense_amount_rank
FROM orders;

WITH ranked_orders AS (
    SELECT o.*,
           ROW_NUMBER() OVER (
               PARTITION BY user_id
               ORDER BY created_at DESC, id DESC
           ) AS rn
    FROM orders AS o
)
SELECT *
FROM ranked_orders
WHERE rn <= 3;

SELECT id, user_id, created_at, total_amount,
       SUM(total_amount) OVER (
           PARTITION BY user_id
           ORDER BY created_at, id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_total
FROM orders;

WITH user_order_stats AS (
    SELECT user_id, COUNT(*) AS order_count,
           SUM(total_amount) AS total_amount
    FROM orders
    GROUP BY user_id
), ranked_users AS (
    SELECT user_id, order_count, total_amount,
           RANK() OVER (ORDER BY total_amount DESC) AS amount_rank
    FROM user_order_stats
)
SELECT u.nickname, r.order_count, r.total_amount, r.amount_rank
FROM ranked_users AS r
JOIN users AS u ON u.id = r.user_id
ORDER BY r.amount_rank;
