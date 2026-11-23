-- V4 新增部门和菜单：只做幂等建表，不修改用户表或删除已有数据。
-- 当前显式列入Spring初始化资源；不是自动扫描所有迁移脚本。
CREATE TABLE IF NOT EXISTS hrs_system_organization (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 部门节点主键，对应用户表dept_id
    parent_id BIGINT NOT NULL DEFAULT 0 CHECK(parent_id>=0 AND parent_id<>id), -- 根节点使用0
    ancestors VARCHAR(500) NOT NULL DEFAULT '' CHECK(length(ancestors)<=500), -- 祖先ID逗号路径，由业务层维护
    dept_name VARCHAR(100) NOT NULL CHECK(length(trim(dept_name)) BETWEEN 1 AND 100),
    leader VARCHAR(64) CHECK(length(leader)<=64),
    phone VARCHAR(32) CHECK(length(phone)<=32),
    email VARCHAR(128) CHECK(length(email)<=128),
    sort INT NOT NULL DEFAULT 0 CHECK(sort>=0),
    status TINYINT NOT NULL DEFAULT 1 CHECK(status IN (0,1)),
    enterprise_id BIGINT CHECK(enterprise_id IS NULL OR (typeof(enterprise_id)='integer' AND enterprise_id>0)),
    organization_id BIGINT CHECK(organization_id IS NULL OR (typeof(organization_id)='integer' AND organization_id>0)),
    delete_flag TINYINT NOT NULL DEFAULT 0 CHECK(delete_flag IN (0,1)),
    create_by VARCHAR(64) NOT NULL CHECK(length(create_by) BETWEEN 1 AND 64),
    update_by VARCHAR(64) NOT NULL CHECK(length(update_by) BETWEEN 1 AND 64),
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_hrs_system_organization_parent ON hrs_system_organization(parent_id,delete_flag);
CREATE INDEX IF NOT EXISTS idx_hrs_system_organization_scope ON hrs_system_organization(enterprise_id,organization_id,delete_flag,sort,id);

CREATE TABLE IF NOT EXISTS hrs_system_menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 与参考项目不同：由数据库分配，不使用MAX(id)+1
    parent_id BIGINT NOT NULL DEFAULT 0 CHECK(parent_id>=0 AND parent_id<>id),
    menu_name VARCHAR(100) NOT NULL CHECK(length(trim(menu_name)) BETWEEN 1 AND 100),
    menu_type VARCHAR(16) NOT NULL CHECK(menu_type IN ('dir','menu','btn')),
    icon VARCHAR(64) CHECK(length(icon)<=64),
    path VARCHAR(200) CHECK(length(path)<=200),
    component VARCHAR(200) CHECK(length(component)<=200),
    permission VARCHAR(128) CHECK(length(permission)<=128),
    sort INT NOT NULL DEFAULT 0 CHECK(sort>=0),
    visible TINYINT NOT NULL DEFAULT 1 CHECK(visible IN (0,1)),
    status TINYINT NOT NULL DEFAULT 1 CHECK(status IN (0,1)),
    enterprise_id BIGINT CHECK(enterprise_id IS NULL OR (typeof(enterprise_id)='integer' AND enterprise_id>0)),
    organization_id BIGINT CHECK(organization_id IS NULL OR (typeof(organization_id)='integer' AND organization_id>0)),
    delete_flag TINYINT NOT NULL DEFAULT 0 CHECK(delete_flag IN (0,1)),
    create_by VARCHAR(64) NOT NULL CHECK(length(create_by) BETWEEN 1 AND 64),
    update_by VARCHAR(64) NOT NULL CHECK(length(update_by) BETWEEN 1 AND 64),
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_hrs_system_menu_parent ON hrs_system_menu(parent_id,delete_flag);
CREATE INDEX IF NOT EXISTS idx_hrs_system_menu_scope ON hrs_system_menu(enterprise_id,organization_id,delete_flag,sort,id);
CREATE INDEX IF NOT EXISTS idx_hrs_system_menu_permission ON hrs_system_menu(permission,delete_flag);
