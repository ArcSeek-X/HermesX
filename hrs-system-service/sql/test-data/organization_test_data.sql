-- 组织管理开发验证数据，仅在明确选定的 system 开发库上手动执行。
-- 先运行 scripts/db/manual_db_upgrade.py 完成正式结构初始化，再执行本文件。
-- 这是独立测试数据文件，不是正式升级文件；升级工具、Java启动都不会自动执行它。
-- 12个未删除根组织、36个未删除节点、1个已删除节点，最多4层。
-- 名称、负责人、电话及example.com邮箱均为演示；性质/类型及企业归属留NULL。
-- 主键由数据库分配，父级和ancestors按真实主键派生，不手工指定ID。
-- 同一测试编码已存在（含已删除）时跳过，不覆盖编辑、不复活删除记录；禁止用于生产初始化。
-- 若已手动修改测试编码/父子关系，应先核对测试集，不以重跑恢复原始值。
-- create_by固定标记仅用于识别手动导入的测试集，不创建登录账号或权限关系。
BEGIN IMMEDIATE;

-- 第一层：根组织；最后一条为逻辑删除验证记录。
WITH seed(code, name, short_name, sort, status, delete_flag) AS (VALUES
    ('DEMO-ORG-HQ', '验证科技集团', '验证总部', 1, 1, 0),
    ('DEMO-ORG-EAST', '验证华东分部', '华东', 2, 1, 0),
    ('DEMO-ORG-SOUTH', '验证华南分部', '华南', 3, 1, 0),
    ('DEMO-ORG-NORTH', '验证华北分部', '华北', 4, 1, 0),
    ('DEMO-ORG-WEST', '验证西部分部', '西部', 5, 1, 0),
    ('DEMO-ORG-CENTRAL', '验证华中分部', '华中', 6, 1, 0),
    ('DEMO-ORG-NORTHEAST', '验证东北分部', '东北', 7, 1, 0),
    ('DEMO-ORG-MARKET', '验证市场事业部', '市场', 8, 1, 0),
    ('DEMO-ORG-DATA', '验证数据事业部', '数据', 9, 1, 0),
    ('DEMO-ORG-SUPPORT', '验证支持中心', '支持', 10, 1, 0),
    ('DEMO-ORG-TRAINING', '验证培训中心', '培训', 11, 1, 0),
    ('DEMO-ORG-DISABLED', '验证停用机构', '停用机构', 12, 0, 0),
    ('DEMO-ORG-DELETED', '验证已删除组织（不应显示）', '已删除', 13, 1, 1)
)
INSERT INTO hrs_system_organization
    (parent_id, ancestors, organization_name, organization_short_name, organization_code,
     organization_email, organization_phone, organization_leader, organization_nature, organization_type,
     remark, sort, status, enterprise_id, delete_flag, create_by, update_by)
SELECT 0, '', seed.name, seed.short_name, seed.code,
       lower(seed.code) || '@example.com', '010-00000000', '测试负责人', NULL, NULL,
       '组织管理开发验证数据；非真实组织。', seed.sort, seed.status, NULL, seed.delete_flag,
       'seed.organization-management', 'seed.organization-management'
FROM seed
WHERE NOT EXISTS (SELECT 1 FROM hrs_system_organization existing WHERE existing.organization_code=seed.code);

-- 第2层：按已插入的上级编码关联真实主键。
WITH seed(code, parent_code, name, short_name, sort, status) AS (VALUES
    ('DEMO-ORG-HQ-RND', 'DEMO-ORG-HQ', '验证研发中心', '研发', 1, 1),
    ('DEMO-ORG-HQ-PRODUCT', 'DEMO-ORG-HQ', '验证产品中心', '产品', 2, 1),
    ('DEMO-ORG-HQ-OPS', 'DEMO-ORG-HQ', '验证运营中心', '运营', 3, 1),
    ('DEMO-ORG-HQ-ARCHIVE', 'DEMO-ORG-HQ', '验证停用归档部', '归档', 4, 0),
    ('DEMO-ORG-EAST-SH', 'DEMO-ORG-EAST', '验证上海研发中心', '上海研发', 1, 1),
    ('DEMO-ORG-EAST-HZ', 'DEMO-ORG-EAST', '验证杭州运营中心', '杭州运营', 2, 1),
    ('DEMO-ORG-SOUTH-SZ', 'DEMO-ORG-SOUTH', '验证深圳研发中心', '深圳研发', 1, 1),
    ('DEMO-ORG-SOUTH-GZ', 'DEMO-ORG-SOUTH', '验证广州服务中心', '广州服务', 2, 1),
    ('DEMO-ORG-NORTH-BJ', 'DEMO-ORG-NORTH', '验证北京研发组', '北京研发', 1, 1),
    ('DEMO-ORG-NORTH-TJ', 'DEMO-ORG-NORTH', '验证天津停用办公室', '天津办公室', 2, 0),
    ('DEMO-ORG-WEST-CD', 'DEMO-ORG-WEST', '验证成都业务组', '成都', 1, 1),
    ('DEMO-ORG-DATA-QUALITY', 'DEMO-ORG-DATA', '验证停用数据质量组', '数据质量', 1, 0),
    ('DEMO-ORG-DATA-MODEL', 'DEMO-ORG-DATA', '验证模型管理组', '模型', 2, 1),
    ('DEMO-ORG-TRAINING-NEW', 'DEMO-ORG-TRAINING', '验证入职培训组', '入职培训', 1, 1)
)
INSERT INTO hrs_system_organization
    (parent_id, ancestors, organization_name, organization_short_name, organization_code,
     organization_email, organization_phone, organization_leader, organization_nature, organization_type,
     remark, sort, status, enterprise_id, delete_flag, create_by, update_by)
SELECT parent.organization_id,
       CASE WHEN parent.ancestors='' THEN CAST(parent.organization_id AS TEXT)
            ELSE parent.ancestors || ',' || parent.organization_id END,
       seed.name, seed.short_name, seed.code,
       lower(seed.code) || '@example.com', '010-00000000', '测试负责人', NULL, NULL,
       '组织管理开发验证数据；非真实组织。', seed.sort, seed.status, parent.enterprise_id, 0,
       'seed.organization-management', 'seed.organization-management'
FROM seed
JOIN hrs_system_organization parent ON parent.organization_code=seed.parent_code
    AND parent.create_by='seed.organization-management' AND parent.delete_flag=0
WHERE NOT EXISTS (SELECT 1 FROM hrs_system_organization existing WHERE existing.organization_code=seed.code);

-- 第3层：按已插入的上级编码关联真实主键。
WITH seed(code, parent_code, name, short_name, sort, status) AS (VALUES
    ('DEMO-ORG-HQ-RND-DATA', 'DEMO-ORG-HQ-RND', '验证数据分析部', '数据分析', 1, 1),
    ('DEMO-ORG-HQ-RND-PLATFORM', 'DEMO-ORG-HQ-RND', '验证平台工程部', '平台工程', 2, 1),
    ('DEMO-ORG-HQ-PRODUCT-DESIGN', 'DEMO-ORG-HQ-PRODUCT', '验证用户体验组', '用户体验', 1, 1),
    ('DEMO-ORG-HQ-PRODUCT-PLAN', 'DEMO-ORG-HQ-PRODUCT', '验证产品规划组', '产品规划', 2, 1),
    ('DEMO-ORG-HQ-OPS-SERVICE', 'DEMO-ORG-HQ-OPS', '验证客户服务组', '客户服务', 1, 1),
    ('DEMO-ORG-HQ-OPS-CONTENT', 'DEMO-ORG-HQ-OPS', '验证内容运营组', '内容运营', 2, 1),
    ('DEMO-ORG-HQ-ARCHIVE-ACTIVE', 'DEMO-ORG-HQ-ARCHIVE', '验证归档维护组（启用）', '归档维护', 1, 1)
)
INSERT INTO hrs_system_organization
    (parent_id, ancestors, organization_name, organization_short_name, organization_code,
     organization_email, organization_phone, organization_leader, organization_nature, organization_type,
     remark, sort, status, enterprise_id, delete_flag, create_by, update_by)
SELECT parent.organization_id,
       CASE WHEN parent.ancestors='' THEN CAST(parent.organization_id AS TEXT)
            ELSE parent.ancestors || ',' || parent.organization_id END,
       seed.name, seed.short_name, seed.code,
       lower(seed.code) || '@example.com', '010-00000000', '测试负责人', NULL, NULL,
       '组织管理开发验证数据；非真实组织。', seed.sort, seed.status, parent.enterprise_id, 0,
       'seed.organization-management', 'seed.organization-management'
FROM seed
JOIN hrs_system_organization parent ON parent.organization_code=seed.parent_code
    AND parent.create_by='seed.organization-management' AND parent.delete_flag=0
WHERE NOT EXISTS (SELECT 1 FROM hrs_system_organization existing WHERE existing.organization_code=seed.code);

-- 第4层：按已插入的上级编码关联真实主键。
WITH seed(code, parent_code, name, short_name, sort, status) AS (VALUES
    ('DEMO-ORG-HQ-RND-DATA-MARKET', 'DEMO-ORG-HQ-RND-DATA', '验证行情分析组', '行情分析', 1, 1),
    ('DEMO-ORG-HQ-RND-DATA-LABEL', 'DEMO-ORG-HQ-RND-DATA', '验证数据标注组', '数据标注', 2, 1),
    ('DEMO-ORG-HQ-RND-PLATFORM-API', 'DEMO-ORG-HQ-RND-PLATFORM', '验证接口工程组', '接口工程', 1, 1)
)
INSERT INTO hrs_system_organization
    (parent_id, ancestors, organization_name, organization_short_name, organization_code,
     organization_email, organization_phone, organization_leader, organization_nature, organization_type,
     remark, sort, status, enterprise_id, delete_flag, create_by, update_by)
SELECT parent.organization_id,
       CASE WHEN parent.ancestors='' THEN CAST(parent.organization_id AS TEXT)
            ELSE parent.ancestors || ',' || parent.organization_id END,
       seed.name, seed.short_name, seed.code,
       lower(seed.code) || '@example.com', '010-00000000', '测试负责人', NULL, NULL,
       '组织管理开发验证数据；非真实组织。', seed.sort, seed.status, parent.enterprise_id, 0,
       'seed.organization-management', 'seed.organization-management'
FROM seed
JOIN hrs_system_organization parent ON parent.organization_code=seed.parent_code
    AND parent.create_by='seed.organization-management' AND parent.delete_flag=0
WHERE NOT EXISTS (SELECT 1 FROM hrs_system_organization existing WHERE existing.organization_code=seed.code);

COMMIT;
