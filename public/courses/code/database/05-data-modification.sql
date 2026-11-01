-- 第四课：INSERT、UPDATE、DELETE 与数据修改
-- 适用：MySQL 8.x / InnoDB
-- 依赖第三课脚本创建的 mysql_course 数据库和业务表；脚本自带建表与数据重置，可独立运行、可重复执行。

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
    deleted_at DATETIME NULL,
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

-- 重置业务数据，保证脚本可重复执行；先运行第三课脚本再运行本脚本也不会冲突
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE orders;
TRUNCATE TABLE products;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO users (email, nickname, phone)
VALUES ('alice@example.com', 'Alice', '13800000001');

INSERT INTO users (email, nickname)
VALUES ('bob@example.com', 'Bob');

INSERT INTO products (name, price, stock)
VALUES ('Keyboard', 199.00, 10),
       ('Mouse', 59.90, 50),
       ('Monitor', 1299.00, 8);

SELECT LAST_INSERT_ID();

-- 唯一键冲突：重复执行时观察 Duplicate entry 错误。
-- INSERT INTO users (email, nickname)
-- VALUES ('alice@example.com', 'Alice 2');

INSERT IGNORE INTO users (email, nickname)
VALUES ('alice@example.com', 'Alice 2');

INSERT INTO products (id, name, price, stock)
VALUES (1, 'Keyboard', 199.00, 20)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    price = VALUES(price),
    stock = VALUES(stock);

SELECT id, email, nickname, phone FROM users WHERE id = 1;

UPDATE users
SET nickname = 'Alice Chen', phone = '13800000002'
WHERE id = 1;

UPDATE products
SET stock = stock - 1
WHERE id = 1 AND stock > 0;

SELECT id, name, stock FROM products WHERE id = 1;

INSERT INTO orders (user_id, order_no, total_amount)
VALUES (1, 'ORD-003', 199.00);

UPDATE orders
SET status = 'paid'
WHERE order_no = 'ORD-003' AND status = 'pending';

UPDATE users
SET deleted_at = CURRENT_TIMESTAMP
WHERE id = 1 AND deleted_at IS NULL;

SELECT id, email, deleted_at FROM users WHERE deleted_at IS NULL;

START TRANSACTION;

UPDATE products
SET stock = stock - 1
WHERE id = 2 AND stock > 0;

-- 应用检查影响行数后，成功执行 COMMIT，失败执行 ROLLBACK。
INSERT INTO orders (user_id, order_no, total_amount)
VALUES (2, 'ORD-TX-001', 59.90);

COMMIT;

-- 仅本地实验使用，确认数据不再需要后再手动执行。
-- DELETE FROM orders WHERE order_no = 'ORD-003';
-- DROP DATABASE mysql_course;
