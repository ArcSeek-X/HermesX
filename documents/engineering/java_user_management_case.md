# Java 用户管理学习案例（SQLite）

本案例把 `scaffold-master-main` 的用户 CRUD 思路放入 HermesX 的 `hrs-system-service`，只实现服务端。阅读顺序是 **DTO → Controller → Service 接口 → ServiceImpl → UserMapper / XML → Entity → VO**。本文中的路径均相对于仓库根。

统一响应见 [common与响应规范](java_common_response_design.md)：正文中的VO、数组、分页结果均位于resultData内，删除返回200及true，CSRF token位于resultData.token。

## 1. 本次实现的边界

- 实现新增、单条详情、分页筛选、完整修改资料、逻辑删除；表名为 `hrs_system_user`。
- 沿用参考项目的账号唯一、密码哈希、审计字段、正常/停用状态及软删除语义，不复制参考项目默认密码。
- 不移植角色、岗位及完整授权管理。部门功能已在[部门与菜单案例](java_organization_menu_management_case.md)实现；用户的deptId非空时必须引用未删除的真实部门，且企业/组织归属必须与部门一致。enterpriseId、organizationId仍是可空元数据，不等同于租户认证。传入roleIds等不支持字段返回400。
- 本案例没有登录、注册、重置密码、账号停用撤销会话、导出、操作日志系统。`status` 当前只影响资料与筛选，不影响认证。
- **阶段性架构例外**：为保留参考表字段并独立演示用户 CRUD，system 暂存账号、BCrypt 密码哈希及状态。将来接入 auth 时，应将凭据和账号状态移交 auth，通过稳定用户 ID 关联，停止 system 的凭据写入；不能把两个服务同时写用户凭据作为最终架构。
- API 使用外部配置的管理身份进行 HTTP Basic 认证，该身份与表内用户相互独立。表内第一个用户不是内置管理员，不设置 `id=1` 特例。创建用户不会使其获得 API 管理权限。
- auth、analysis 仍是骨架，Python、Web、Electron 不切换到 Java。

## 2. 文件在哪里，各做什么

| 文件（相对于 `hrs-system-service/`） | 大白话职责 |
| --- | --- |
| `pojo/src/main/java/hermesx/system/dto/CreateUserDTO.java` | 描述新增允许填的字段，通过注解约束必填和长度；不收审计人 |
| `pojo/src/main/java/hermesx/system/dto/UpdateUserDTO.java` | 描述可修改资料，不允许改账号与密码 |
| `pojo/src/main/java/hermesx/system/entity/UserEntity.java` | 数据库一行的完整模型，含密码密文，仅供内部使用 |
| `pojo/src/main/java/hermesx/system/vo/UserVO.java` | 返回给调用方的数据白名单，没有密码 |
| `../hrs-common/src/main/java/hermesx/common/vo/PageVO.java` | 分页结果的公共结构，含 rows、total、page、pageSize |
| `../hrs-common/src/main/java/hermesx/common/rest/RestResult.java` | 全部JSON成功/失败统一响应，替代原ErrorVO |
| `rest/src/main/java/hermesx/system/SystemApplication.java` | Spring Boot 服务启动入口 |
| `rest/src/main/java/hermesx/system/controller/UserController.java` | HTTP 方法、路径、参数及响应状态；不写 SQL |
| `rest/src/main/java/hermesx/system/service/IUserService.java` | 业务契约，调用方只需要知道能做什么 |
| `rest/src/main/java/hermesx/system/service/impl/UserServiceImpl.java` | 权限、密码哈希、规则、事务和模型转换 |
| `rest/src/main/java/hermesx/system/dao/UserMapper.java` | 数据访问接口，声明方法与参数，不决定操作者权限 |
| `rest/src/main/resources/mapper/UserMapper.xml` | 编写 SQL、参数绑定和 Entity 构造映射，namespace 对应接口全名 |
| `rest/src/main/java/hermesx/system/security/CurrentUser.java` | 检查管理身份，从认证上下文获取可信审计人 |
| `rest/src/main/java/hermesx/system/config/SecurityConfig.java` | 装配管理身份、BCrypt 和 HTTP 安全过滤链 |
| `rest/src/main/java/hermesx/system/config/DatabaseConfig.java` | 把 SQLite 唯一键冲突通过 MyBatis 会话转换成通用重复键异常 |
| `rest/src/main/java/hermesx/system/exception/GlobalExceptionHandler.java` | 业务异常到 HTTP 错误的转换，避免返回 SQL 或密码 |
| `rest/src/main/resources/application.properties` | 外部配置入口、连接池和建表脚本设置 |
| `rest/src/main/resources/db/schema.sql` | 建表和索引，首次启动创建，后续启动不清空数据 |
| `rest/src/test/java/hermesx/system/UserApiIntegrationTest.java` | 使用真实 SQLite 临时文件贯穿 API、业务和持久化 |

这里使用 Java 17 的 `record` 表示数据类型：它生成构造方法和字段访问方法，例如 `data.nickname()`；没有 Lombok，也不需要手写大量 getter/setter。DTO 不负责处理业务，Entity 不负责执行 SQL。为避免意外记录密码，含密码的类型重写了 `toString()`。

本例采用 **MyBatis Mapper + XML**。`UserMapper` 仍放 `dao/` 数据访问层；MyBatis 创建接口的代理实现，通过方法名查找 XML 中同名的 SQL，不需要手写 MapperImpl。原来的 `UserDao` 已移除，不额外套转发 DAO 或 Repository。

XML 的 `namespace="hermesx.system.dao.UserMapper"` 对应 Java 接口全名，`id="find"` 等对应方法名，`#{id}` 等对应 `@Param` 参数名，并由 MyBatis 转成预编译绑定。Entity 使用不可变 record，因此通过 `<constructor>` 显式映射每个列名和参数类型，空的 dept_id 不会被误转成0。

列表和总数共用 `<sql id="filters">`，减少筛选条件漂移。SQLite 的 INSERT RETURNING 返回结果集，按 [MyBatis 官方约定](https://mybatis.org/mybatis-3/sqlmap-xml.html)写成带 `affectData="true"`、`flushCache="true"` 和 `useCache="false"` 的 `<select>`，不是普通只读查询。集成测试验证它参加 Spring 事务并能回滚。

MyBatis Spring Boot Starter 3.0.5 适配本例 Spring Boot 3.5；运行配置明确指定 `classpath:mapper/UserMapper.xml`。测试仍使用 JdbcTemplate 独立检查数据库实际内容，不代表业务里保留了第二套数据访问实现。将来换数据库时调整驱动、DDL 和 XML 方言，不承诺仅改 URL 即可迁移。

## 3. 一次新增如何经过各层

1. 安全过滤链先认证管理身份，并验证写请求的 CSRF token。
2. Controller 将 JSON 转成 `CreateUserDTO`，执行格式校验，调用 `IUserService.create`。
3. Spring 注入的实际对象是 `UserServiceImpl`：它再次守住业务权限，取得真实管理人，检查密码 UTF-8 字节上限，用 BCrypt 生成哈希。
4. Service 开启本地事务，调用 UserMapper，MyBatis 执行 XML 中使用 `#{参数}` 绑定的 SQL，执行 INSERT，再用 SQLite `RETURNING id` 获取该次插入的主键。
5. Mapper 查询得到 `UserEntity`；Service 显式转换成不含密码的 `UserVO`。
6. Controller 返回 `201 Created`，并设置新资源的 Location。

事务的意义是：一个业务操作需要多条本地 SQL 时，要么一起成功，要么一起回滚。数据库的 UNIQUE 约束是账号不重复的最终保障，不能只在 Java 里“先查一下”，因为并发请求可能同时通过查询。

查询默认排除 `delete_flag=1`。删除只更新标记，不物理删除数据。账号唯一约束覆盖已删除记录，因此删除后也不能重复使用同名账号，沿用参考表的唯一键含义。

## 4. 字段与 SQLite 适配

参考来源：`vibe-template/scaffold-master-main/scaffold-system/sql/V1__init_schema.sql` 中的 `sys_user`，以及 `SystemManagementService` 的用户创建、修改与软删除逻辑。参考项目文件仅用于阅读，未修改。

| 字段 | 中文含义 | 参考 MySQL 类型 | 本例 SQLite 声明 / 处理 |
| --- | --- | --- | --- |
| id | 用户 ID | BIGINT 自增 | INTEGER PRIMARY KEY AUTOINCREMENT，Java Long |
| username | 登录账号 | VARCHAR(64) | VARCHAR(64)，非空唯一，保留大小写，精确区分 |
| password | 密码密文 | VARCHAR(128) | VARCHAR(128)，只存 BCrypt 哈希，响应不返回 |
| nickname | 用户昵称 | VARCHAR(64) | VARCHAR(64)，非空 |
| phone | 联系电话 | VARCHAR(32) | 同名同长度声明，可空，不强制某一国家手机号格式 |
| email | 邮箱 | VARCHAR(128) | 同名同长度声明，可空，输入校验邮箱格式 |
| dept_id | 部门 ID | BIGINT | BIGINT，可空正整数；非空时验证真实部门存在、未删除和归属一致 |
| enterprise_id | 所属企业 ID | 参考 Newsee 的 BIGINT(18) | BIGINT，可空正整数，对应 Java enterpriseId |
| organization_id | 所属组织 ID | 参考 Newsee 的 BIGINT(18) | BIGINT，可空正整数，对应 Java organizationId |
| status | 用户状态 | TINYINT | TINYINT + CHECK，1正常、0停用；新增缺省1 |
| last_login_time | 最近登录时间 | DATETIME | DATETIME，可空，本例不更新 |
| delete_flag | 删除标记 | TINYINT | TINYINT + CHECK，缺省0，删除置1 |
| create_by / update_by | 创建人 / 更新人 | VARCHAR(64) | 保留声明，值取认证上下文 |
| create_time / update_time | 创建 / 更新时间 | DATETIME | UTC文本，格式 YYYY-MM-DD HH:MM:SS，更新时显式赋 CURRENT_TIMESTAMP |

SQLite 不像 MySQL 一样自动强制 VARCHAR 长度，所以 DTO 校验之外，DDL 也增加 CHECK。SQLite 不支持 MySQL 的 COMMENT、ENGINE 和 ON UPDATE 子句，中文解释使用 SQL 注释。时间、主键和唯一索引是迁移数据库时需要重点复核的差异。

`schema.sql` 用于当前初始建表，`CREATE TABLE IF NOT EXISTS` 不会自动升级未来变化的旧表。本次新增企业和组织字段提供 `rest/src/main/resources/db/migration/V2__add_user_enterprise_organization.sql` 作为显式升级脚本，仅用于两个字段均不存在的旧 SQLite 表，应用不会自动执行它。旧数据的新增字段保持 NULL，不自动猜填归属。

使用旧库时，先停止 Java 服务并备份数据库，再检查 `PRAGMA table_info(hrs_system_user);`。确认两个字段都不存在后，从仓库根执行下列命令，路径由自己提供：

```bash
read -r -p '旧SQLite文件的绝对路径: ' USER_DB_FILE
# .bail on 保证遇到错误立即退出；两条 ALTER 位于一个事务，失败不会只升级一半。
sqlite3 -bail "$USER_DB_FILE" < hrs-system-service/rest/src/main/resources/db/migration/V2__add_user_enterprise_organization.sql
```

删除标志统一为数据库 `delete_flag`、Java Entity 的 `deleteFlag`；值为0表示正常、1表示已删除，仍不暴露在前端 VO 中。若旧表仍叫 `deleted`，停止服务、备份后，再执行一次重命名脚本（原有删除状态会保留）：

```bash
sqlite3 -bail "$USER_DB_FILE" < hrs-system-service/rest/src/main/resources/db/migration/V3__rename_user_delete_flag.sql
```

V2 用于增加企业和组织字段，V3 用于重命名删除标志，分别检查对应字段后执行；两步都需要时按 V2 → V3 执行。新数据库由配置中的schema.sql和显式V4脚本初始化，无需手动运行V2/V3；已有对应目标字段时不要重复执行。若只有一个字段存在，应先排查数据库版本，不能盲目重跑脚本。脚本保留原用户、密码哈希和审计数据。后续字段变更也需明确的迁移，不要仅覆盖 CREATE TABLE 文件。

Nacos 可选接入、独立数据库规划和注册验证见 [Nacos 接入说明](java_nacos_discovery.md)。

## 5. 启动服务

需要 JDK 17。以下命令从仓库根运行，使用独立 SQLite 文件，父目录先创建：

```bash
./mvnw -pl hrs-system-service/rest -am verify
mkdir -p data
export HRS_SYSTEM_DB_URL="jdbc:sqlite:$(pwd)/data/hrs_system.db"
read -r -p '管理账号: ' HRS_SYSTEM_ADMIN_USERNAME
export HRS_SYSTEM_ADMIN_USERNAME
read -r -s -p '管理密码（12至72个UTF-8字节）: ' HRS_SYSTEM_ADMIN_PASSWORD
printf '\n'
export HRS_SYSTEM_ADMIN_PASSWORD
java -jar hrs-system-service/rest/target/hrs-system-service-rest-0.1.0-SNAPSHOT.jar
```

Java 不自动读取根 `.env`，上述变量必须导出到 Java 进程。数据库路径由 `HRS_SYSTEM_DB_URL` 必填配置，建议绝对路径，不能复用 Python 的数据库文件。未提供管理账号、密码或数据库 URL 时启动失败，不创建默认管理账号。配置也已列入根 `.env.example`。

`HRS_SYSTEM_BIND_ADDRESS` 缺省为 `127.0.0.1`；`HRS_SYSTEM_PORT` 缺省为 `0`，操作系统选择可用端口，查看启动日志中的端口后使用。需要固定开发端口时自行 export。以下请求中，先将 `BASE_URL` 设成该实际地址；不把示例开发接口直接暴露到公网。远程访问 Basic 认证须使用 HTTPS。

## 6. 接口与调用示例

| 方法与路径 | 输入 | 成功结果 |
| --- | --- | --- |
| GET `/api/system/users/csrf` | Basic 管理认证 | token、headerName、parameterName，并设置保存 token 的会话 Cookie |
| POST `/api/system/users` | username、password、nickname；可选 phone、email、deptId、enterpriseId、organizationId、status | 201 + RestResult(UserVO) + Location |
| GET `/api/system/users/{id}` | 正整数 ID | 200 + RestResult(UserVO) |
| GET `/api/system/users` | keyword、status、deptId、enterpriseId、organizationId、page、pageSize | 200 + RestResult(PageVO) |
| PUT `/api/system/users/{id}` | nickname、status 必填；phone、email、deptId、enterpriseId、organizationId 可空 | 200 + RestResult(更新后UserVO) |
| DELETE `/api/system/users/{id}` | 正整数 ID | 200 + RestResult(true) |

PUT 表示完整更新可编辑资料：省略可选 phone/email/deptId/enterpriseId/organizationId 会清空它们。username、password、roleIds 等不属于修改输入，发送未知字段返回400。账号不可改，密码不通过资料修改接口变更。

分页从1开始，pageSize默认20，上限100；keyword 对账号或昵称做字面子串查询，status、deptId、enterpriseId、organizationId 精确筛选，按ID倒序。它不是 SQL 表达式，`%` 也不是通配符。

以下使用 Bash、curl 和 Python3。另开终端时需重新提供管理环境变量。将 BASE_URL 填为启动日志显示的本机 URL：

```bash
read -r -p '服务URL: ' BASE_URL
COOKIE_FILE=$(mktemp)
fetch_csrf() {
CSRF_JSON=$(curl --fail --silent --show-error -u "$HRS_SYSTEM_ADMIN_USERNAME:$HRS_SYSTEM_ADMIN_PASSWORD" \
  -c "$COOKIE_FILE" "$BASE_URL/api/system/users/csrf")
CSRF_TOKEN=$(printf '%s' "$CSRF_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["resultData"]["token"])')
}
fetch_csrf

# 教学示例数据；这里的密码属于新建的表内用户，不是管理接口的密码。
curl --fail-with-body -u "$HRS_SYSTEM_ADMIN_USERNAME:$HRS_SYSTEM_ADMIN_PASSWORD" \
  -b "$COOKIE_FILE" -H "X-CSRF-TOKEN: $CSRF_TOKEN" -H 'Content-Type: application/json' \
  -d '{"username":"learner","password":"Learning-only-2026","nickname":"学习用户","status":1,"enterpriseId":100,"organizationId":2001}' \
  "$BASE_URL/api/system/users"

curl --fail-with-body -u "$HRS_SYSTEM_ADMIN_USERNAME:$HRS_SYSTEM_ADMIN_PASSWORD" \
  "$BASE_URL/api/system/users?page=1&pageSize=20&keyword=learner"

# 先从新增响应取 id，再填入下面提示，不假定第一个用户的 ID 一定是1。
read -r -p '用户ID: ' USER_ID
fetch_csrf
curl --fail-with-body -u "$HRS_SYSTEM_ADMIN_USERNAME:$HRS_SYSTEM_ADMIN_PASSWORD" \
  -X PUT -b "$COOKIE_FILE" -H "X-CSRF-TOKEN: $CSRF_TOKEN" -H 'Content-Type: application/json' \
  -d '{"nickname":"修改后的昵称","status":0,"email":"learner@example.com","enterpriseId":100,"organizationId":2001}' \
  "$BASE_URL/api/system/users/$USER_ID"

fetch_csrf
curl --fail-with-body -u "$HRS_SYSTEM_ADMIN_USERNAME:$HRS_SYSTEM_ADMIN_PASSWORD" \
  -X DELETE -b "$COOKIE_FILE" -H "X-CSRF-TOKEN: $CSRF_TOKEN" "$BASE_URL/api/system/users/$USER_ID"
rm "$COOKIE_FILE"
```

每次请求都需要 Basic 凭据；Cookie 只用于 CSRF token，不代表已登录。写接口同时携带 CSRF token 和对应 Cookie。认证流程会轮换 token，所以每次写操作前都通过 fetch_csrf 获取新的 token；重启服务后也需重新获取。

常见错误：400参数错误、401认证失败、403权限/CSRF失败、404资源不存在、409业务冲突、503数据库失败；全部返回RestResult。CSRF在认证前拒绝时返回403/CSRF_INVALID，401保留认证挑战响应头。

## 7. 验证、限制与回滚

集成测试使用独立临时 SQLite 文件，不连接本地真实用户库，覆盖 CRUD、软删除、密码哈希和响应脱敏、重复账号、筛选分页、输入校验、SQL特殊字符、认证、权限与 CSRF。本机已通过根 `./mvnw verify`（10个模块、9组集成场景）及打包后真实进程启动、真实 token/Cookie 请求、重启持久化、更新和软删除检查；尚未验证 Windows 与远端部署。

部门和菜单后续实现及规则收口见[部门与菜单案例](java_organization_menu_management_case.md)。本案例不是完整认证和组织权限系统；新增归属字段是管理员维护的元数据，不能作为可信租户上下文。当前账号仍全表唯一，未改成企业内唯一。管理身份拥有本表全部数据的管理权限，没有普通用户自助资料接口。尚无其他服务调用，不为远程包编写无用实现。本次不执行前端构建，也不迁移现有 Python 用户和历史数据。

本次加字段后若只回退代码，SQLite 中新增的可空列可以保留，避免删列损坏数据；需要精确恢复表结构时，使用升级前备份并核对升级后的新增数据。回滚整个案例时停止 Java 进程，撤回 system 实现与构建配置即可；保留配置指定的 SQLite 文件，不删除用户数据。升级前的数据备份和正式 auth 数据移交需要另行设计。

设计依据：[Java 工程架构](java_engineering_architecture.md)。技术行为参考 [Spring Boot 数据初始化](https://docs.spring.io/spring-boot/how-to/data-initialization.html)、[SQLite 类型说明](https://www.sqlite.org/datatype3.html)、[Spring Security Basic 认证](https://docs.spring.io/spring-security/reference/servlet/authentication/passwords/basic.html)。本学习文档没有英文对应版，本次未新增双语副本。

**2026-11-19 行为更新**：新增部门表后，用户新增/修改不再允许任意不存在的deptId；旧孤立引用需明确改为NULL或实际部门。V4创建新表不自动修正这些旧值，也不改变已有用户的密码或删除状态。
