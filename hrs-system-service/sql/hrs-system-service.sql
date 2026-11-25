-- HermesX system 服务正式 SQL；所属服务：hrs-system-service；当前方言：SQLite。
-- @service hrs-system-service
-- @dialect sqlite
-- 用途：尚未上线、无历史数据时的初始建库基线，不再保留 INIT/V2/V3/V4 历史升级段。
-- 本文件只定义表和索引，不创建默认账号，不导入菜单，不清理或覆盖业务数据。
-- 相同结构下可重复执行；IF NOT EXISTS 不会检查或修正已有表、索引的定义。
-- 已有旧结构的数据库不能依靠重跑本基线升级；后续由独立手动工具预检并执行增量变更。
-- Java 已关闭启动初始化，不读取或选择本文件的版本段；使用业务接口前须手动准备匹配结构。
-- 不在 SQL 内控制 BEGIN/COMMIT；后续由独立工具统一负责备份、事务、检查和执行历史。
-- 数据库开发位置：仓库根 data/hrs_system.db；实际绝对路径由执行者与运行配置指定。
-- 字段规范见 documents/DB/database_rules.md；执行方案见 documents/DB/sql_management_and_execution_plan.md。

-- BEGIN BASELINE_20261123
-- @upgrade {"description":"初始化用户、部门及统一菜单表","kind":"baseline","requires":[],"verify":[]}

-- 一、部门表。组织树与用户的 dept_id 关联，父节点、祖先路径和归属一致性由 Service 校验。
-- organization_id 是归属元数据，不等同于本表 id，也不能代替用户所属部门 dept_id。
CREATE TABLE IF NOT EXISTS hrs_system_organization (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 主键，由 SQLite 分配；Java 使用 Long
    parent_id BIGINT NOT NULL DEFAULT 0 -- 父部门主键；0 表示根，禁止指向自身
        CHECK(typeof(parent_id) = 'integer' AND parent_id >= 0 AND parent_id <> id),
    ancestors VARCHAR(500) NOT NULL DEFAULT '' CHECK(length(ancestors) <= 500), -- 祖先 ID 逗号路径，由 Service 计算
    dept_name VARCHAR(100) NOT NULL CHECK(length(dept_name) BETWEEN 1 AND 100 AND length(trim(dept_name)) > 0), -- 部门名称
    leader VARCHAR(64) CHECK(length(leader) <= 64), -- 负责人，可空
    phone VARCHAR(32) CHECK(length(phone) <= 32), -- 联系电话，可空
    email VARCHAR(128) CHECK(length(email) <= 128), -- 邮箱，可空；格式由 DTO 校验
    sort INT NOT NULL DEFAULT 0 CHECK(typeof(sort) = 'integer' AND sort >= 0), -- 同级排序，越小越靠前
    status TINYINT NOT NULL DEFAULT 1 CHECK(status IN (0, 1)), -- 1 启用，0 禁用
    enterprise_id BIGINT CHECK(enterprise_id IS NULL OR (typeof(enterprise_id) = 'integer' AND enterprise_id > 0)), -- 所属企业，可空
    organization_id BIGINT CHECK(organization_id IS NULL OR (typeof(organization_id) = 'integer' AND organization_id > 0)), -- 所属组织，可空
    delete_flag TINYINT NOT NULL DEFAULT 0 CHECK(delete_flag IN (0, 1)), -- 0 正常，1 逻辑删除
    create_by VARCHAR(64) NOT NULL CHECK(length(create_by) BETWEEN 1 AND 64 AND length(trim(create_by)) > 0), -- 创建人，由服务端可信身份提供
    update_by VARCHAR(64) NOT NULL CHECK(length(update_by) BETWEEN 1 AND 64 AND length(trim(update_by)) > 0), -- 更新人，更新及删除时维护
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 创建时间，SQLite 保存 UTC 文本
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP -- 更新时间，由更新 SQL 显式维护
);

CREATE INDEX IF NOT EXISTS idx_hrs_system_organization_parent
    ON hrs_system_organization(parent_id, delete_flag);
CREATE INDEX IF NOT EXISTS idx_hrs_system_organization_scope
    ON hrs_system_organization(enterprise_id, organization_id, delete_flag, sort, id);

-- 二、用户表。当前 system 学习案例暂存密码哈希；正式认证接入后按方案移交 auth。
-- 用户与部门的存在性、未删除状态及企业组织归属由 Service 校验，不在此新增外键或触发器。
CREATE TABLE IF NOT EXISTS hrs_system_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 用户主键；不等同于跨服务全局身份
    username VARCHAR(64) NOT NULL CHECK(length(username) BETWEEN 1 AND 64 AND length(trim(username)) > 0), -- 登录账号；区分大小写
    password VARCHAR(128) NOT NULL CHECK(length(password) BETWEEN 1 AND 128), -- BCrypt 密码哈希，禁止存明文
    nickname VARCHAR(64) NOT NULL CHECK(length(nickname) BETWEEN 1 AND 64 AND length(trim(nickname)) > 0), -- 用户昵称
    phone VARCHAR(32) CHECK(length(phone) <= 32), -- 电话，可空
    email VARCHAR(128) CHECK(length(email) <= 128), -- 邮箱，可空；格式由 DTO 校验
    dept_id BIGINT CHECK(dept_id IS NULL OR (typeof(dept_id) = 'integer' AND dept_id > 0)), -- 所属部门，关联本库部门主键
    enterprise_id BIGINT CHECK(enterprise_id IS NULL OR (typeof(enterprise_id) = 'integer' AND enterprise_id > 0)), -- 所属企业，可空
    organization_id BIGINT CHECK(organization_id IS NULL OR (typeof(organization_id) = 'integer' AND organization_id > 0)), -- 所属组织，可空
    status TINYINT NOT NULL DEFAULT 1 CHECK(status IN (0, 1)), -- 1 正常，0 停用；当前不关联登录认证
    last_login_time DATETIME, -- 最近登录 UTC 时间；当前尚无登录功能，保持 NULL
    delete_flag TINYINT NOT NULL DEFAULT 0 CHECK(delete_flag IN (0, 1)), -- 0 正常，1 逻辑删除
    create_by VARCHAR(64) NOT NULL CHECK(length(create_by) BETWEEN 1 AND 64 AND length(trim(create_by)) > 0), -- 创建人，由服务端提供
    update_by VARCHAR(64) NOT NULL CHECK(length(update_by) BETWEEN 1 AND 64 AND length(trim(update_by)) > 0), -- 更新人，由服务端提供
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 创建 UTC 时间
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP -- 更新 UTC 时间，由更新 SQL 显式维护
);

-- 账号全表唯一：逻辑删除后仍保留账号，不能据此注册同名新用户。
CREATE UNIQUE INDEX IF NOT EXISTS uk_hrs_system_user_username
    ON hrs_system_user(username);
CREATE INDEX IF NOT EXISTS idx_hrs_system_user_dept
    ON hrs_system_user(dept_id, delete_flag);
CREATE INDEX IF NOT EXISTS idx_hrs_system_user_status
    ON hrs_system_user(status, delete_flag);

-- 三、菜单表。module、group、page 使用同一种结构，通过 menu_type 区分。
-- 除 id、归属、删除及审计字段外，业务字段均使用 menu_ 前缀，对应 Java 的 menuXxx 属性。
CREATE TABLE IF NOT EXISTS hrs_system_menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 数字主键；menu_code 不是主键
    menu_parent_id BIGINT NOT NULL DEFAULT 0 -- 父菜单主键；module 为根，使用 0
        CHECK(typeof(menu_parent_id) = 'integer' AND menu_parent_id >= 0 AND menu_parent_id <> id),
    menu_code VARCHAR(128) NOT NULL CHECK(length(menu_code) BETWEEN 1 AND 128 AND length(trim(menu_code)) > 0), -- 稳定业务标识，例如 stock、kline
    menu_name VARCHAR(100) NOT NULL CHECK(length(menu_name) BETWEEN 1 AND 100 AND length(trim(menu_name)) > 0), -- 菜单名称或前端国际化键
    menu_description VARCHAR(500) NOT NULL DEFAULT '' CHECK(length(menu_description) <= 500), -- 描述或国际化键
    menu_type VARCHAR(16) NOT NULL CHECK(menu_type IN ('module', 'group', 'page')), -- 模块、分组、页面
    menu_route_path VARCHAR(200) CHECK(length(menu_route_path) <= 200), -- page 保存完整站内路径；不拼接 menu_code
    menu_page_path VARCHAR(200) CHECK(length(menu_page_path) <= 200), -- 前端页面标识，例如 pages/Stock/StockKLinePage/StockKLinePage
    menu_icon VARCHAR(64) CHECK(length(menu_icon) <= 64), -- 图标名称，不保存组件代码
    menu_badge VARCHAR(64) CHECK(length(menu_badge) <= 64), -- 角标文字，可空
    menu_position VARCHAR(16) NOT NULL DEFAULT 'content' CHECK(menu_position IN ('header', 'content', 'footer')), -- 展示区域
    menu_expanded TINYINT NOT NULL DEFAULT 0 CHECK(menu_expanded IN (0, 1)), -- 是否默认展开，JSON 为 Boolean
    menu_visible TINYINT NOT NULL DEFAULT 1 CHECK(menu_visible IN (0, 1)), -- 只控制前端显示；父级隐藏时后代入口也隐藏
    menu_sort INT NOT NULL DEFAULT 0 CHECK(typeof(menu_sort) = 'integer' AND menu_sort >= 0), -- 同级排序，越小越靠前
    menu_status TINYINT NOT NULL DEFAULT 1 CHECK(menu_status IN (0, 1)), -- 是否启用；Java 导航查询排除禁用节点及其子树
    menu_permission VARCHAR(128) CHECK(length(menu_permission) <= 128), -- 权限标识预留，尚未实现角色菜单授权
    menu_auth VARCHAR(16) CHECK(menu_auth IN ('public', 'protected')), -- 对应 JSON 的 auth，可空，不表示后端已完成授权
    menu_exact TINYINT CHECK(menu_exact IN (0, 1)), -- 对应 JSON 的 exact，可空；前端路径精确匹配元数据
    enterprise_id BIGINT CHECK(enterprise_id IS NULL OR (typeof(enterprise_id) = 'integer' AND enterprise_id > 0)), -- 所属企业，可空
    organization_id BIGINT CHECK(organization_id IS NULL OR (typeof(organization_id) = 'integer' AND organization_id > 0)), -- 所属组织，可空
    delete_flag TINYINT NOT NULL DEFAULT 0 CHECK(delete_flag IN (0, 1)), -- 0 正常，1 逻辑删除
    create_by VARCHAR(64) NOT NULL CHECK(length(create_by) BETWEEN 1 AND 64 AND length(trim(create_by)) > 0), -- 创建人，由服务端提供
    update_by VARCHAR(64) NOT NULL CHECK(length(update_by) BETWEEN 1 AND 64 AND length(trim(update_by)) > 0), -- 更新人，由服务端提供
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 创建 UTC 时间
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 更新 UTC 时间，由更新 SQL 显式维护
    -- module 必须位于根；group/page 必须有父节点。父节点存在性、类型、循环及归属由 Service 校验。
    CONSTRAINT ck_hrs_system_menu_root_type CHECK(
        (menu_type = 'module' AND menu_parent_id = 0)
        OR (menu_type IN ('group', 'page') AND menu_parent_id > 0)
    ),
    -- page 必须能定位站内路由与页面；group 的可选路径仅为元数据，不参与 page 路由拼接。
    CONSTRAINT ck_hrs_system_menu_page_target CHECK(
        menu_type <> 'page' OR (
            menu_route_path IS NOT NULL
            AND substr(menu_route_path, 1, 1) = '/'
            AND substr(menu_route_path, 1, 2) <> '//'
            AND menu_page_path IS NOT NULL
            AND substr(menu_page_path, 1, 6) = 'pages/'
            AND length(menu_page_path) > 6
        )
    )
);

-- 与当前 Service 保持一致：未删除菜单的 menu_code 全局唯一，page 的完整路由全局唯一。
-- 禁用记录仍参与唯一性；逻辑删除后可复用，允许保留多条已删除历史记录。
-- SQLite 使用部分唯一索引；迁移 MySQL 时需重设计，不能原样复制 WHERE 索引语法。
CREATE UNIQUE INDEX IF NOT EXISTS uk_hrs_system_menu_code
    ON hrs_system_menu(menu_code) WHERE delete_flag = 0;
CREATE UNIQUE INDEX IF NOT EXISTS uk_hrs_system_menu_page_route
    ON hrs_system_menu(menu_route_path) WHERE delete_flag = 0 AND menu_type = 'page';
CREATE INDEX IF NOT EXISTS idx_hrs_system_menu_parent
    ON hrs_system_menu(menu_parent_id, delete_flag);
CREATE INDEX IF NOT EXISTS idx_hrs_system_menu_scope
    ON hrs_system_menu(enterprise_id, organization_id, delete_flag, menu_sort, id);

-- END BASELINE_20261123

-- 后续真实结构或数据变更追加到此处；基线实际执行并登记后，不再改写已执行内容。
-- 手动工具：scripts/db/manual_db_upgrade.py；执行历史由工具维护，Java 不调用它。
-- 本文件已验证不代表真实库已部署；首次执行须先 plan，再明确指定 apply/create。

-- BEGIN ORGANIZATION_20261124
-- @upgrade {"description":"组织主键、业务字段及企业关联规则升级","kind":"migration","requires":["BASELINE_20261123"],"verify":["SELECT COUNT(*) = 0 FROM hrs_system_organization child LEFT JOIN hrs_system_organization parent ON child.parent_id=parent.organization_id WHERE child.parent_id<>0 AND (parent.organization_id IS NULL OR child.enterprise_id IS NOT parent.enterprise_id)"]}
-- 保留旧id数值，保证父链和用户dept_id的身份不变；旧组织归属列不再沿用。
CREATE TABLE hrs_system_organization_next (
    organization_id INTEGER PRIMARY KEY AUTOINCREMENT CHECK(organization_id > 0),
    parent_id BIGINT NOT NULL DEFAULT 0 CHECK(typeof(parent_id) = 'integer' AND parent_id >= 0 AND parent_id <> organization_id),
    ancestors VARCHAR(500) NOT NULL DEFAULT '' CHECK(length(ancestors) <= 500),
    organization_name VARCHAR(100) NOT NULL CHECK(length(organization_name) BETWEEN 1 AND 100 AND length(trim(organization_name)) > 0),
    organization_short_name VARCHAR(64) CHECK(length(organization_short_name) <= 64),
    organization_code VARCHAR(64) CHECK(length(organization_code) <= 64),
    organization_email VARCHAR(128) CHECK(length(organization_email) <= 128),
    organization_phone VARCHAR(32) CHECK(length(organization_phone) <= 32),
    organization_leader VARCHAR(64) CHECK(length(organization_leader) <= 64),
    organization_nature VARCHAR(32) CHECK(length(organization_nature) <= 32),
    organization_type VARCHAR(32) CHECK(length(organization_type) <= 32),
    remark VARCHAR(500) CHECK(length(remark) <= 500),
    sort INT NOT NULL DEFAULT 0 CHECK(typeof(sort) = 'integer' AND sort >= 0),
    status TINYINT NOT NULL DEFAULT 1 CHECK(status IN (0, 1)),
    enterprise_id BIGINT CHECK(enterprise_id IS NULL OR (typeof(enterprise_id) = 'integer' AND enterprise_id > 0)),
    delete_flag TINYINT NOT NULL DEFAULT 0 CHECK(delete_flag IN (0, 1)),
    create_by VARCHAR(64) NOT NULL CHECK(length(create_by) BETWEEN 1 AND 64 AND length(trim(create_by)) > 0),
    update_by VARCHAR(64) NOT NULL CHECK(length(update_by) BETWEEN 1 AND 64 AND length(trim(update_by)) > 0),
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO hrs_system_organization_next
    (organization_id,parent_id,ancestors,organization_name,organization_email,organization_phone,organization_leader,sort,status,enterprise_id,delete_flag,create_by,update_by,create_time,update_time)
SELECT id,parent_id,ancestors,dept_name,email,phone,leader,sort,status,enterprise_id,delete_flag,create_by,update_by,create_time,update_time FROM hrs_system_organization;
DROP TABLE hrs_system_organization;
ALTER TABLE hrs_system_organization_next RENAME TO hrs_system_organization;
CREATE INDEX idx_hrs_system_organization_parent ON hrs_system_organization(parent_id,delete_flag);
CREATE INDEX idx_hrs_system_organization_enterprise ON hrs_system_organization(enterprise_id,delete_flag,sort,organization_id);
-- END ORGANIZATION_20261124
