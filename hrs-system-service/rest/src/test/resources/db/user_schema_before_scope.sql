-- 参考 scaffold 的 sys_user，保留字段含义和长度；SQLite 不支持 MySQL COMMENT/ON UPDATE。
CREATE TABLE IF NOT EXISTS hrs_system_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 用户ID，SQLite 必须用 INTEGER 才能作为自增主键
    username VARCHAR(64) NOT NULL UNIQUE CHECK(length(username) BETWEEN 1 AND 64), -- 登录账号，删除后仍保留唯一性
    password VARCHAR(128) NOT NULL CHECK(length(password) <= 128), -- BCrypt哈希，不存明文
    nickname VARCHAR(64) NOT NULL CHECK(length(nickname) BETWEEN 1 AND 64), -- 用户昵称
    phone VARCHAR(32) CHECK(length(phone) <= 32), -- 电话
    email VARCHAR(128) CHECK(length(email) <= 128), -- 邮箱
    dept_id BIGINT CHECK(dept_id > 0), -- 部门ID，本案例未实现部门表，不声明虚假的外键
    status TINYINT NOT NULL DEFAULT 1 CHECK(status IN (0,1)), -- 正常1，停用0（暂不关联登录）
    last_login_time DATETIME, -- 最近登录时间，无登录功能所以保持NULL
    deleted TINYINT NOT NULL DEFAULT 0 CHECK(deleted IN (0,1)), -- 逻辑删除
    create_by VARCHAR(64) CHECK(length(create_by) <= 64), -- 创建人，由认证上下文提供
    update_by VARCHAR(64) CHECK(length(update_by) <= 64), -- 更新人
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- UTC时间，SQLite以文本表示
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP -- 由更新SQL显式维护
);
CREATE INDEX IF NOT EXISTS idx_hrs_system_user_dept ON hrs_system_user(dept_id);
CREATE INDEX IF NOT EXISTS idx_hrs_system_user_status ON hrs_system_user(status);
