-- 第五课（JOIN 篇）：多表关联查询
-- 适用：MySQL 8.x / InnoDB
-- 依赖第三课脚本创建的 mysql_course 数据库和业务表；order_items、employees 表由本脚本创建。

USE mysql_course;

CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT NOT NULL AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_oi_order_product (order_id, product_id),
    CONSTRAINT fk_oi_order FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_oi_product FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE = InnoDB;

INSERT IGNORE INTO order_items (order_id, product_id, quantity, price)
VALUES (1, 1, 2, 199.00),
       (1, 2, 1, 59.90),
       (2, 3, 1, 1299.00);

CREATE TABLE IF NOT EXISTS employees (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    manager_id BIGINT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_emp_name (name),
    CONSTRAINT fk_emp_manager FOREIGN KEY (manager_id) REFERENCES employees(id)
) ENGINE = InnoDB;

INSERT IGNORE INTO employees (name, manager_id)
VALUES ('张伟', NULL),
       ('李娜', 1),
       ('王强', 1),
       ('赵敏', 2);

-- 四、INNER JOIN：只保留匹配数据
SELECT u.id AS user_id, u.nickname, o.order_no, o.status
FROM users AS u
INNER JOIN orders AS o ON o.user_id = u.id;

-- 五、LEFT JOIN：保留左表全部行
SELECT u.id AS user_id, u.nickname, o.order_no
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id;

-- 五.1 查询没有订单的用户
SELECT u.id, u.nickname
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
WHERE o.id IS NULL;

-- 六、多表 JOIN：订单明细（order_items 关联 orders 和 products）
SELECT o.order_no, p.name, oi.quantity
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.id
JOIN products AS p ON p.id = oi.product_id;

-- 七、自连接：员工与上级
SELECT e.name AS employee, m.name AS manager
FROM employees AS e
LEFT JOIN employees AS m ON m.id = e.manager_id;

-- 八、聚合 + JOIN：每个用户订单数
SELECT u.id, u.nickname, COUNT(o.id) AS order_count
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
GROUP BY u.id, u.nickname;

-- 八、聚合 + JOIN：每个用户已支付金额
SELECT u.id, u.nickname,
       COALESCE(SUM(o.total_amount), 0) AS paid_amount
FROM users AS u
LEFT JOIN orders AS o
    ON o.user_id = u.id
   AND o.status = 'paid'
GROUP BY u.id, u.nickname;
