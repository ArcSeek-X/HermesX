-- 仅用于尚无这两个字段的旧 SQLite 用户库，停服务、备份后执行一次。
-- 新数据库由 schema.sql 直接创建；本脚本不会由应用自动执行。
-- 两条 ALTER 在同一事务中，失败时不应保留部分升级。
BEGIN IMMEDIATE;
ALTER TABLE hrs_system_user ADD COLUMN enterprise_id BIGINT CHECK(enterprise_id > 0);
ALTER TABLE hrs_system_user ADD COLUMN organization_id BIGINT CHECK(organization_id > 0);
COMMIT;
