-- 第十二课：undo log、redo log 与 binlog
-- 适用：MySQL 8.x
-- 说明：以下主要是只读检查和时序注释，不直接模拟异常重启。

USE mysql_course;

-- 查看 binlog 和相关配置。
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
SHOW VARIABLES LIKE 'log_bin_basename';
SHOW VARIABLES LIKE 'innodb_log%';

-- 查看当前 binlog 状态。
SHOW BINARY LOG STATUS;
-- 某些 MySQL 版本或兼容环境可使用：
-- SHOW MASTER STATUS;

-- undo log / rollback 的可观察示例。
START TRANSACTION;

UPDATE products
SET stock = stock + 1
WHERE id = 1;

-- 回滚后，修改不应成为已提交业务数据。
ROLLBACK;

-- redo log、binlog 和数据页刷盘的关系是内部时序，不能通过普通 SQL
-- 安全地模拟异常掉电。可以用下面的时序复习：
-- 1. 修改内存数据页。
-- 2. redo log 进入 prepare。
-- 3. binlog 写入。
-- 4. redo log 标记 commit。
-- 5. 数据页后续异步刷盘。

-- 时间点恢复的概念流程：
-- 1. 恢复最近一次全量备份。
-- 2. 找到备份之后的 binlog 起点。
-- 3. 按顺序回放到目标时间点。

-- 不要直接删除 binlog 文件。清理前必须确认备份和复制已经不再需要这些日志。
