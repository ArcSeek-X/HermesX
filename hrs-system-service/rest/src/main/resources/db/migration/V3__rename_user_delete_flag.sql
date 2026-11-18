-- 仅用于仍有 deleted 字段的旧用户表，停止服务并备份后执行一次。
-- 新库已使用 delete_flag；不得重复执行。本脚本不改变原有0/1值。
BEGIN IMMEDIATE;
ALTER TABLE hrs_system_user RENAME COLUMN deleted TO delete_flag;
COMMIT;
