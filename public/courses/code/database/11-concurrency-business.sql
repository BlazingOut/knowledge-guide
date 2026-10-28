-- 第十一课：业务并发控制：下单、库存与账户
-- 适用：MySQL 8.x / InnoDB
-- 说明：并发实验需要两个独立 MySQL 会话和业务练习表。

USE mysql_course;

-- 方案一：条件更新扣库存。
START TRANSACTION;

UPDATE products
SET stock = stock - 1
WHERE id = 1
  AND stock > 0;

-- 应用检查影响行数：1 表示成功，0 表示库存不足或商品不存在。
-- 确认成功后创建订单。
INSERT INTO orders (user_id, order_no, status, total_amount)
VALUES (1, 'ORD-CONDITION-001', 'pending', 199.00);

COMMIT;

-- 方案二：悲观锁。需要在事务中先读取最新库存。
-- START TRANSACTION;
-- SELECT stock FROM products WHERE id = 1 FOR UPDATE;
-- UPDATE products SET stock = stock - 1 WHERE id = 1;
-- INSERT INTO orders (user_id, order_no, status, total_amount)
-- VALUES (1, 'ORD-LOCK-001', 'pending', 199.00);
-- COMMIT;

-- 方案三：乐观锁。先为练习表增加版本号，再使用旧版本更新。
-- ALTER TABLE products ADD COLUMN version BIGINT NOT NULL DEFAULT 0;
-- UPDATE products
-- SET stock = stock - 1, version = version + 1
-- WHERE id = 1 AND version = 0 AND stock > 0;

-- 账户条件扣款。
-- START TRANSACTION;
-- UPDATE accounts
-- SET balance = balance - 100
-- WHERE id = 1 AND balance >= 100;
-- INSERT INTO account_transactions (account_id, amount, type)
-- VALUES (1, 100, 'debit');
-- COMMIT;

-- 幂等请求表。
-- CREATE TABLE order_requests (
--     id BIGINT NOT NULL AUTO_INCREMENT,
--     request_id VARCHAR(64) NOT NULL,
--     order_id BIGINT NULL,
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     PRIMARY KEY (id),
--     UNIQUE KEY uk_order_requests_request_id (request_id)
-- ) ENGINE = InnoDB;
