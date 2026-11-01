-- 第三课：SELECT、条件、排序与分页
-- 适用：MySQL 8.x / InnoDB
-- 本脚本自包含：先建库、建表并写入样例数据，再执行本课查询示例；可重复运行。

CREATE DATABASE IF NOT EXISTS mysql_course
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;
USE mysql_course;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    nickname VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_email (email)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS products (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT chk_products_price CHECK (price >= 0),
    CONSTRAINT chk_products_stock CHECK (stock >= 0)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS orders (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    order_no VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(12, 2) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_orders_order_no (order_no),
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT chk_orders_amount CHECK (total_amount >= 0)
) ENGINE = InnoDB;

-- 重置业务数据，保证脚本可重复执行
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE orders;
TRUNCATE TABLE products;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO users (email, nickname, phone)
VALUES ('alice@example.com', 'Alice', '13800000001'),
       ('bob@example.com', 'Bob', NULL),
       ('carol@example.com', 'Carol', '13800000003');

INSERT INTO products (name, price, stock)
VALUES ('Keyboard', 199.00, 10),
       ('Mouse', 59.90, 50),
       ('Monitor', 1299.00, 8);

INSERT INTO orders (user_id, order_no, status, total_amount, created_at)
VALUES (1, 'ORD-001', 'paid',      199.00, '2026-10-10 09:00:00'),
       (2, 'ORD-002', 'shipped',    59.90, '2026-10-11 10:00:00'),
       (1, 'ORD-003', 'completed', 1299.00,'2026-10-12 11:00:00'),
       (2, 'ORD-004', 'paid',      199.00, '2026-10-13 09:30:00'),
       (1, 'ORD-005', 'shipped',    59.90, '2026-10-14 10:30:00'),
       (2, 'ORD-006', 'paid',      1299.00,'2026-10-15 11:30:00'),
       (1, 'ORD-007', 'completed', 199.00, '2026-10-16 12:00:00'),
       (2, 'ORD-008', 'paid',       59.90, '2026-10-18 12:00:00');

-- 以下查询与课文各节对应 -----------------------------------------

-- 二、SELECT 基本结构
SELECT id, email, nickname FROM users;
SELECT id AS user_id, nickname AS display_name FROM users;
SELECT name, price, price * 0.9 AS discounted_price FROM products;
SELECT u.id, u.email FROM users AS u;
SELECT DISTINCT status FROM orders;

-- 三、WHERE 筛选
SELECT id, order_no, total_amount
FROM orders
WHERE status = 'paid' AND total_amount >= 100;

SELECT id, order_no, status, total_amount
FROM orders
WHERE (status = 'paid' OR status = 'shipped')
  AND total_amount >= 100;

SELECT id, order_no, status
FROM orders
WHERE status IN ('paid', 'shipped', 'completed');

SELECT id, name, price
FROM products
WHERE price BETWEEN 50 AND 200;

SELECT id, nickname
FROM users
WHERE nickname LIKE 'Alice%';

SELECT name,
       CASE WHEN stock = 0 THEN '无货'
            WHEN stock < 10 THEN '库存较低'
            ELSE '库存正常' END AS stock_label
FROM products;

-- 四、NULL 与三值逻辑
SELECT id, email FROM users WHERE phone IS NULL;
SELECT nickname, COALESCE(phone, '未填写') AS phone_display FROM users;

-- 五、ORDER BY 稳定排序
SELECT id, order_no, created_at
FROM orders
ORDER BY created_at DESC, id DESC;

-- 六、LIMIT / OFFSET 分页
SELECT id, order_no, created_at
FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 3 OFFSET 3;

-- 键集分页：以上一页最后一个 id=3 为游标
SELECT id, order_no, created_at
FROM orders
WHERE id > 3
ORDER BY id ASC
LIMIT 3;

-- 时间倒序游标：以上一页最后一行为锚点（id=6，created_at=2026-10-15 11:30:00）
SELECT id, order_no, created_at
FROM orders
WHERE created_at < '2026-10-15 11:30:00'
   OR (created_at = '2026-10-15 11:30:00' AND id < 6)
ORDER BY created_at DESC, id DESC
LIMIT 3;
