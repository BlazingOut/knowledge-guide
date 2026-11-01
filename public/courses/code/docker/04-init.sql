-- 第 4 课：MySQL 初始化脚本
-- 这个文件通过 bind mount 挂到容器的 /docker-entrypoint-initdb.d/ 下。
-- 只有当 MySQL 数据目录为空（第一次初始化）时，这个脚本才会执行。

CREATE DATABASE IF NOT EXISTS takeout;
USE takeout;

CREATE TABLE IF NOT EXISTS orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO orders (user_id, amount, status)
VALUES (1, 38.50, 'created');
