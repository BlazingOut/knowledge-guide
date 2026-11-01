-- 第九课：事务、ACID 与隔离级别
-- 适用：MySQL 8.x / InnoDB
-- 说明：并发实验需要打开两个独立的 MySQL 会话。

USE mysql_course;

SELECT @@autocommit;
SELECT @@transaction_isolation;

-- 基础事务示例。accounts 表需要在专门的练习环境中准备。
-- START TRANSACTION;
-- UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- UPDATE accounts SET balance = balance + 100 WHERE id = 2;
-- COMMIT;

-- 保存点示例。
-- START TRANSACTION;
-- UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- SAVEPOINT after_debit;
-- ROLLBACK TO SAVEPOINT after_debit;
-- COMMIT;

-- 设置当前会话隔离级别，影响后续事务。
-- SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 会话 A：修改但不提交。
-- START TRANSACTION;
-- UPDATE accounts SET balance = 50 WHERE id = 1;

-- 会话 B：普通读取，观察是否能读到 A 未提交的值。
-- START TRANSACTION;
-- SELECT balance FROM accounts WHERE id = 1;

-- 会话 A：结束修改。
-- COMMIT;

-- 会话 B：结束实验事务。
-- COMMIT;

-- 只在确认无副作用的测试环境中观察 DDL 与事务行为。
-- START TRANSACTION;
-- ALTER TABLE users ADD COLUMN transaction_demo_remark VARCHAR(255);
-- ROLLBACK;
