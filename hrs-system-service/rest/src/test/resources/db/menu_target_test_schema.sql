-- 仅供自动化测试：模拟Java Mapper要求的目标列，不是正式建表/升级脚本。
-- 只在测试自己创建的临时SQLite中执行，不连接或创建data/hrs_system.db。
DROP TABLE IF EXISTS hrs_system_menu;
CREATE TABLE hrs_system_menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_parent_id BIGINT NOT NULL DEFAULT 0,
    menu_code VARCHAR(128) NOT NULL,
    menu_name VARCHAR(100) NOT NULL,
    menu_description VARCHAR(500) NOT NULL DEFAULT '',
    menu_type VARCHAR(16) NOT NULL CHECK(menu_type IN ('module','group','page')),
    menu_route_path VARCHAR(200), menu_page_path VARCHAR(200),
    menu_icon VARCHAR(64), menu_badge VARCHAR(64),
    menu_position VARCHAR(16) NOT NULL DEFAULT 'content',
    menu_expanded INT NOT NULL DEFAULT 0 CHECK(menu_expanded IN (0,1)),
    menu_visible INT NOT NULL DEFAULT 1 CHECK(menu_visible IN (0,1)),
    menu_sort INT NOT NULL DEFAULT 0,
    menu_status INT NOT NULL DEFAULT 1 CHECK(menu_status IN (0,1)),
    menu_permission VARCHAR(128), menu_auth VARCHAR(16), menu_exact INT,
    enterprise_id BIGINT, organization_id BIGINT,
    delete_flag INT NOT NULL DEFAULT 0,
    create_by VARCHAR(64) NOT NULL, update_by VARCHAR(64) NOT NULL,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX test_menu_code ON hrs_system_menu(menu_code) WHERE delete_flag=0;
CREATE UNIQUE INDEX test_menu_page_route ON hrs_system_menu(menu_route_path) WHERE delete_flag=0 AND menu_type='page';
