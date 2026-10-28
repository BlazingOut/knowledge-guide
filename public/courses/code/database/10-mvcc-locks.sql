-- 第十课：MVCC、快照读、当前读与锁
-- 适用：MySQL 8.x / InnoDB
-- 说明：并发实验需要两个独立的 MySQL 会话和可测试的 accounts 表。

USE mysql_course;

-- 会话 A：修改但不提交。
-- START TRANSACTION;
-- UPDATE accounts SET balance = 50 WHERE id = 1;

-- 会话 B：普通快照读，观察是否读取 A 未提交的版本。
-- START TRANSACTION;
-- SELECT balance FROM accounts WHERE id = 1;

-- 会话 A 提交后，会话 B 再次普通读取，观察隔离级别和读取视图的影响。
-- COMMIT;
-- SELECT balance FROM accounts WHERE id = 1;
-- ROLLBACK;

-- 会话 A：持有当前读的排他锁。
-- START TRANSACTION;
-- SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;

-- 会话 B：尝试修改同一行，观察锁等待。
-- START TRANSACTION;
-- UPDATE accounts SET balance = balance - 10 WHERE id = 1;

-- 会话 A 结束后，会话 B 才能继续。
-- COMMIT;
-- COMMIT;

-- 共享锁示例。
-- START TRANSACTION;
-- SELECT balance FROM accounts WHERE id = 1 FOR SHARE;
-- ROLLBACK;

-- 查看当前连接和等待信息。
SHOW PROCESSLIST;

-- MySQL 8 锁信息；不同版本字段可能不同。
SELECT *
FROM performance_schema.data_locks;

SELECT *
FROM performance_schema.data_lock_waits;

-- 范围当前读示例。实际锁范围取决于索引、数据和隔离级别。
-- START TRANSACTION;
-- SELECT * FROM products WHERE stock BETWEEN 10 AND 20 FOR UPDATE;
-- ROLLBACK;
