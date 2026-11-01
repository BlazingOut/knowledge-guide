-- 第十三课（线上排查篇）：从现象到证据的排查示例
-- 适用：MySQL 8.x
-- 说明：本文件以只读检查和排查思路为主，不直接执行备份、恢复、切换或删除操作。

USE mysql_course;

-- 连接和线程状态。
SHOW FULL PROCESSLIST;
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Threads_running';
SHOW GLOBAL VARIABLES LIKE 'max_connections';

-- InnoDB 状态和锁排查。
SHOW ENGINE INNODB STATUS;

SELECT *
FROM performance_schema.data_locks;

SELECT *
FROM performance_schema.data_lock_waits;

-- 慢查询和执行计划检查。
SHOW GLOBAL VARIABLES LIKE 'slow_query_log';
SHOW GLOBAL VARIABLES LIKE 'long_query_time';

EXPLAIN
SELECT id, order_no, created_at
FROM orders
WHERE user_id = 1
  AND status = 'paid'
ORDER BY created_at DESC
LIMIT 20;

-- binlog 和复制相关配置。具体字段会随 MySQL 版本和复制方式变化。
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
SHOW VARIABLES LIKE 'log_bin_basename';
SHOW BINARY LOG STATUS;

-- 某些环境可以查看复制状态；没有配置复制时可能返回空结果或报权限错误。
-- SHOW REPLICA STATUS;
-- 旧版本兼容语法：
-- SHOW SLAVE STATUS;

-- 时间点恢复是运维流程，不在本地 SQL 中直接执行：
-- 1. 恢复最近一次全量备份。
-- 2. 找到备份之后的 binlog。
-- 3. 回放到目标时间点并验证数据。

-- 不要直接执行以下高风险操作：
-- KILL <thread_id>;
-- RESET BINARY LOGS;
-- DROP DATABASE mysql_course;
