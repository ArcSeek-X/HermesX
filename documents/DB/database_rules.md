# HermesX 数据库与建表规范

更新时间：2026-11-24。

本文是 HermesX 数据库命名、表结构和数据边界的规范。当前使用 SQLite，后续按服务逐步迁移 MySQL。表名已确认采用前缀式，例如 `hrs_system_user`；不是含点号的字面表名。

> **SQL 执行状态**：system 正式 SQL 包含冻结基线 BASELINE_20261123 及组织升级段 ORGANIZATION_20261124，Java 已关闭启动初始化并移除旧分段读取，正式 SQL 不进入业务 JAR。独立手动工具和执行历史已实现，本机 data/hrs_system.db 已初始化并导入组织验证数据，生产部署仍待安排，见 [SQL 管理与数据库升级方案](sql_management_and_execution_plan.md)。

## 1. 适用范围与执行原则

- 【强制】所有新建的应用业务表遵循本文，包括用户、组织、字典、关联、业务日志等表，必须具有 `delete_flag`、`enterprise_id`、`organization_id` 三个字段。
- 【强制】本规范不要求修改 SQLite 自行维护的内部表，例如 `sqlite_sequence`。视图不是数据表，不机械增加可写字段，但对外查询仍遵循数据范围与删除规则。
- 【强制】独立升级工具的技术历史表（例如 `hrs_system_schema_history`）不是业务表，不添加逻辑删除或企业组织归属字段；按独立工具协议维护，不通过业务 CRUD 修改。此例外不适用于业务日志、关联表或其他应用业务表。
- 【强制】旧表改造使用明确的迁移脚本，不能修改初始化脚本后就声称旧库已升级。项目尚未上线，直接面向目标结构设计，不为旧字段长期维护双列或双写。
- 【强制】修改现有表前核对实际版本、已有数据及所有调用方。真实配置、用户数据和运行数据库不随源码提交，不因整理目录而移动或清空。
- 【强制】本文是目标约定，不代表存量 Python 表已经合规。本规范不批量改存量表；system 三表正式 SQL 已收敛为当前基线并通过内存验证，不表示真实业务库已经部署，当前状态见第10节。

## 2. 每个服务拥有独立数据库

| 服务／工程 | SQLite 文件名 | 后续 MySQL 数据库名 | 主要数据 |
| --- | --- | --- | --- |
| Python | `stock_analysis.db` | 接入时单独确定，不与 Java analysis 混用 | Python 自己拥有的分析执行、报告等数据；存量业务移交另行安排 |
| `hrs-system-service` | `hrs_system.db` | `hrs_system` | 用户资料、组织、角色权限、菜单、字典、业务设置 |
| `hrs-auth-service` | `hrs_auth.db` | `hrs_auth` | 账号凭据、认证与会话；后续实现 |
| `hrs-analysis-service` | `hrs_analysis.db` | `hrs_analysis` | 自选股、研究偏好、分析任务归属；后续实现 |

【强制】服务只能直接读写自己的库，访问其他服务的数据通过接口。不能用跨库 SQL、SQLite ATTACH 或共享 Entity/Mapper 绕过服务边界。跨服务通过稳定 ID 关联，不建立跨库外键。

同一个 MySQL 实例可以承载多个服务数据库，但应分别分配受限账号。独立数据库不意味着必须每个服务安装一个 MySQL 容器。

当前 system 用户案例暂存密码哈希和账号状态是已记录的阶段性安排；正式接入 auth 时，必须移交凭据和账号状态的唯一写入责任，不允许两边同时写。见[用户管理案例](../engineering/java_user_management_case.md)。

## 3. SQLite 文件具体放在哪里

### 3.1 仓库本地开发目录

【强制】本地开发数据库统一位于**仓库根目录的 `data/`**，不放在 Java 源码、resources、target、python/ 或各服务工程目录内：

```text
HermesX/
├── data/
│   ├── stock_analysis.db       # Python 已有数据库，保留原位置
│   ├── hrs_system.db           # system 实际启用后创建
│   ├── hrs_auth.db             # 未来启用 auth 时创建
│   └── hrs_analysis.db         # 未来启用 Java analysis 时创建
├── hrs-system-service/
├── hrs-auth-service/
├── hrs-analysis-service/
└── python/
```

本机当前仓库位置对应的绝对路径：

| 数据库 | 本机路径 |
| --- | --- |
| Python | `/Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/data/stock_analysis.db` |
| system | `/Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/data/hrs_system.db` |
| auth（规划） | `/Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/data/hrs_auth.db` |
| Java analysis（规划） | `/Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/data/hrs_analysis.db` |

以上绝对路径是本机定位说明，不得写死进 Java/Python 源码、共享构建文件或部署配置。尚未实现的服务不预先创建空数据库；本规范也不会自动创建文件。

system 在仓库根用 Bash 启动时配置：

```bash
mkdir -p data
export HRS_SYSTEM_DB_URL="jdbc:sqlite:$(pwd)/data/hrs_system.db"
```

`HRS_SYSTEM_DB_URL` 当前为必填配置。Java 已关闭启动建表或升级，使用业务接口前须手动准备匹配结构。SQLite 驱动仍可能创建空文件，不能以文件存在或服务启动成功判断建库完成。工具和具体操作见[运行教程](../engineering/java_user_management_case.md)。父目录需预先建立，启动还需要管理凭据。从其他工作目录启动时必须传入正确的绝对路径，不能误用当时的 `pwd`。

### 3.2 容器、桌面和测试

- 【强制】数据库是运行数据。容器使用外部持久化卷，桌面安装版使用操作系统提供的应用数据目录，再传入绝对路径；不写入安装包、JAR 或资源目录。容器内路径与桌面具体目录在对应接入阶段确定，不照搬开发机路径。
- 【强制】测试使用隔离临时库，不能使用真实的 `data/hrs_system.db` 或 Python 数据库。需要多个连接时不要未经验证使用普通 `:memory:`，其数据可能按连接隔离。
- 【强制】`data/`、数据库文件、SQLite 的 `-wal`、`-shm`、`-journal` 附属文件及备份不入 Git，不作为构建产物分发。schema、迁移 SQL 和不含真实数据的测试夹具可以入库。

## 4. 命名规则

### 4.1 表名、库名、字段名

【强制】表名统一为：

```text
hrs_<服务简称>_<业务名>
```

| 服务 | 表名示例 |
| --- | --- |
| system | `hrs_system_user`、`hrs_system_organization`、`hrs_system_user_role` |
| auth | `hrs_auth_account`、`hrs_auth_session` |
| Java analysis | `hrs_analysis_watchlist`、`hrs_analysis_task_ownership` |

服务简称为 `system`、`auth`、`analysis`，不拼接 `-service`。Python 新建业务表也遵循 `hrs_<已明确的服务简称>_<业务名>`；在其服务简称正式确认前，不擅自使用 Java analysis 的简称，存量表不因此直接重命名。

- 全部采用小写英文与下划线；业务名使用清晰、统一的单数名词或名词组合，不使用中文、空格、连字符或点号，不以 `tbl_` 等方式重复表示“表”。
- 库名与文件名分开：SQLite 文件 `hrs_system.db`；MySQL 库 `hrs_system`；表名仍是 `hrs_system_user`。
- `hrs_system.hrs_system_user` 在 MySQL 中表示“库.表”，不是表名的一部分。SQLite 的点号表示 main/temp/已附加库的限定名，不能把 `hrs_system.user` 当普通单表名称使用。
- 字段使用 `snake_case`，Java 属性使用 `camelCase`，通过 MyBatis 映射对应。

### 4.2 索引与约束命名

| 对象 | 命名规则 | 示例 |
| --- | --- | --- |
| 普通索引 | `idx_<表名>_<用途或列名>` | `idx_hrs_system_user_scope` |
| 唯一索引 | `uk_<表名>_<业务键>` | `uk_hrs_system_user_username` |
| 显式 CHECK 约束 | `ck_<表名>_<规则>` | `ck_hrs_system_user_delete_flag` |

名称应清楚且控制长度，便于迁移 MySQL。SQLite 内联 UNIQUE 生成的自动索引无需手工改名；有明确迁移需求时再显式命名。避免 SQLite 中不同表手工索引重名。

## 5. 每张业务表的必备字段

### 5.1 三个强制字段

| 数据库字段 | Java 属性 | 类型与默认值 | 语义与写入规则 |
| --- | --- | --- | --- |
| `delete_flag` | `deleteFlag` | SQLite 可用 TINYINT/INTEGER；MySQL TINYINT；NOT NULL DEFAULT 0；仅允许0/1 | 0未删除、1已删除；由服务端删除/恢复用例维护，不作为普通表单可编辑字段 |
| `enterprise_id` | `enterpriseId` | BIGINT；当前允许NULL，无虚构默认企业ID；非空时为正整数 | 所属企业，不自动等同于已经实现租户隔离 |
| `organization_id` | `organizationId` | BIGINT；当前允许NULL，无虚构默认组织ID；非空时为正整数 | 所属组织，与部门ID分开；不能用 `dept_id` 代替 |

【强制】“必须包含”表示每张业务表都必须建这三列，不意味着当前所有行都必须有企业与组织归属。当前没有完整组织、租户体系，允许NULL表示未分配；禁止用0、-1或硬编码某企业作为兜底。将来要求归属必填的业务，应先确定可信上下文、修复旧NULL数据，再迁移为 NOT NULL，不静默替换默认值。

【强制】普通查询、分页总数、更新、删除及批量操作统一检查 `delete_flag = 0`。软删除更新删除标志及更新审计字段，保留数据。查看已删除数据、恢复、最终清理必须有明确独立的授权语义；不写默认物理 DELETE 代替业务删除。测试夹具清理不属于业务删除接口。

### 5.1.1 组织主数据表的主键特例（代码、SQL及本机独立库已落实）

`hrs_system_organization`采用`organization_id`作为唯一主键，删除原`id`列；SQLite声明为`organization_id INTEGER PRIMARY KEY AUTOINCREMENT`，Java/接口字段为`organizationId`。本表该列表示组织节点身份，非空且唯一，不再作为可空、可重复的所属组织归属列，也不另设scopeOrganizationId。父子关系由`parent_id`引用该主键，所属企业仍用`enterprise_id`。

上节普通业务表organization_id的可空归属规则不适用于组织主数据表本身。用户/菜单等表的id与organization_id不因此自动改名或改语义；用户dept_id的目标关联应指向组织表organization_id，并同步校验组织存在、未删除及所属企业，不沿用已取消的部门组织归属比较。

此项已落实到Java Entity/DTO/VO、Mapper和正式SQL的ORGANIZATION_20261124段，已使用临时SQLite验证，并于2026-11-24由手动工具初始化本机data/hrs_system.db。若旧数据存在，应将旧id身份保留为新organization_id，不将旧的可重复组织归属值直接当成主键。实施遵循既有手动执行与历史冻结规则，详见[组织管理方案](../product/系统设置/system_org_management.md#sec-3)。

### 5.2 主键与审计字段

| 字段 | 规则 |
| --- | --- |
| `id`（默认）或明确批准的业务主键名 | 普通表默认id；组织主数据表按5.1.1使用organization_id且不再有id。Java Long，SQLite INTEGER PRIMARY KEY AUTOINCREMENT，MySQL BIGINT AUTO_INCREMENT；仅本表内唯一 |
| `create_by` | 创建人，建议 VARCHAR(64)，服务端可信身份或明确的系统任务身份生成 |
| `update_by` | 更新人，建议 VARCHAR(64)，随更新与软删除维护 |
| `create_time` | 创建时间，服务端生成，统一UTC |
| `update_time` | 更新时间，由所有更新 SQL 或统一持久化机制维护，不能依赖前端提交 |

【强制】新增表默认包含主键和上述审计字段；新表明确声明审计字段的可空策略，不接受客户端指定内部审计值。旧版用户表审计列可空的安排已在新建库基线中收敛，不允许因此匿名写入。

当前 system 新基线的三张业务表均将创建人、更新人和审计时间声明为非空；Java Mapper 写入操作者，SQLite 默认生成创建及初始更新时间。

实体可以包含这些内部字段，但对外 VO 采用白名单，不默认返回删除标记和密码哈希。不要让所有 DTO 继承包含审计和删除标志的万能 BaseEntity，造成可修改字段失控。

## 6. 数据范围、唯一性和索引

- 当前用户管理仅向配置的管理身份开放，`enterpriseId` 和 `organizationId` 可以由该管理员维护，只是元数据。用户dept_id非空时已校验组织存在且未删除、所属企业一致；尚无企业主数据校验，也没有实现普通用户跨企业隔离；接口文档必须如实说明。
- 后续实现多租户时，企业身份来自认证后的可信上下文。请求中的ID只能作为待授权目标，不可直接决定操作者的权限范围。读取、计数、修改、删除及关联查询都需覆盖数据范围，而不只是给列表加筛选项。
- `enterprise_id` 与 `organization_id` 不是同一个概念；组织主数据表organization_id为主键，其他普通业务表按所属组织语义使用。允许同一企业拥有多个组织。新增组织关联表后验证组织属于目标企业，不擅自认为任意两组正整数都存在关联。
- 唯一性按业务定义，不能机械在所有表套统一组合。当前用户 `username` 全表唯一，包含已删除账号；本规范不把它悄悄改成企业内唯一。
- 如果未来支持企业内唯一，必须明确NULL企业的处理规则。SQLite 与 MySQL 的普通唯一约束都不能简单用可空列自动保证“未分配企业也唯一”。
- 不简单使用 `(业务键, delete_flag)` 来实现“删除后可无限复用”：同一业务键已有一条删除记录时，再删除另一条可能冲突。允许复用需要单独设计并验证跨数据库方案。
- 索引按真实查询建立。常按企业、组织查询时可评估 `(enterprise_id, organization_id, delete_flag, id)` 等复合索引；只有组织条件的查询未必能有效利用该索引，需用执行计划验证。不要给每个低基数字段机械建立独立索引。
- 不建立跨服务外键。同服务外键应有真实父表，SQLite 使用时确保各连接启用外键检查；无父表时不能声称存在性已经保证。

## 7. SQLite 类型与建表模板

SQLite 并不自动强制 VARCHAR(n) 的长度；日期也没有独立存储类型。因此参数校验之外，应使用适当 CHECK 约束补充规则，具体行为参考 [SQLite 类型文档](https://www.sqlite.org/datatype3.html)。

| 业务类型 | SQLite 约定 | MySQL 迁移方向 |
| --- | --- | --- |
| 主键 | INTEGER PRIMARY KEY AUTOINCREMENT | BIGINT AUTO_INCREMENT |
| 企业、组织等ID | BIGINT + 正整数规则，Java Long | BIGINT，与Java有符号Long范围一致 |
| 状态、删除标志 | INTEGER或TINYINT + CHECK枚举范围 | TINYINT + 受目标版本支持的约束 |
| 短文本 | VARCHAR(n) + 必要长度CHECK | VARCHAR(n)，显式确定字符集、排序规则 |
| 时间 | 当前用户案例为UTC的 YYYY-MM-DD HH:MM:SS 文本，以DATETIME声明 | DATETIME，并由应用保证UTC；需要毫秒时单独统一精度 |
| 金额 | 优先用整数最小单位并说明币种与精度，或经验证的十进制定点方案 | DECIMAL(p,s)；不能把SQLite DECIMAL声明误认为精确定点存储 |
| 大文本 | TEXT，明确大小上限 | TEXT或按容量选择具体类型 |

以下为通用业务表模板，**不是本次已经创建的新表**。它示范必备字段、长度检查及较严格的ID存储检查；不要求现有用户表未经迁移直接替换DDL：

```sql
CREATE TABLE IF NOT EXISTS hrs_system_example (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 64),
    enterprise_id BIGINT CHECK(
        enterprise_id IS NULL OR (typeof(enterprise_id) = 'integer' AND enterprise_id > 0)
    ),
    organization_id BIGINT CHECK(
        organization_id IS NULL OR (typeof(organization_id) = 'integer' AND organization_id > 0)
    ),
    delete_flag TINYINT NOT NULL DEFAULT 0 CHECK(delete_flag IN (0, 1)),
    create_by VARCHAR(64) NOT NULL CHECK(length(create_by) BETWEEN 1 AND 64),
    update_by VARCHAR(64) NOT NULL CHECK(length(update_by) BETWEEN 1 AND 64),
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

`typeof` 是SQLite特定函数，迁移MySQL时由严格数值类型和校验承担，不原样复制。MyBatis SQL 用 `#{参数}` 绑定，不通过 `${参数}` 拼入用户输入；排序列等动态标识符必须使用服务端白名单。

## 8. 初始化、升级、备份和回滚

- 【强制】每个 Java 服务在其根目录下的 `sql/` 维护唯一正式 SQL：`hrs-system-service/sql/hrs-system-service.sql`、`hrs-auth-service/sql/hrs-auth-service.sql`、`hrs-analysis-service/sql/hrs-analysis-service.sql`。固定名称不加分支或日期后缀，分支与发布历史由 Git 管理；不在 resources 维护正式副本，不扫描目录批量执行。
- 【执行约定】建库与升级由人手动运行独立工具，Java 启动不执行正式 SQL，不维护版本列表。工具读取唯一文件，负责检查、备份、事务、完成验证和执行历史；不是每次启动都必须升级，也不要求人手工截取版本。
- 【执行约定】统一入口允许反复运行，已完成变更校验摘要后跳过，待完成变更按依赖执行，冲突或未知结构报错。`CREATE TABLE IF NOT EXISTS` 不会修正已有表，SQLite 条件改表由工具衔接；不忽略错误来实现所谓幂等。
- 【执行约定】先核对实际数据再建立正确基线。已执行并记录的段冻结，后续向同一文件追加变更。旧结构若有需保留数据，先备份和专门转换，不为旧入口长期保留 Java 执行器或双份 SQL。
- 【当前实现】system SQL 包含 `BASELINE_20261123` 与 `ORGANIZATION_20261124`，覆盖用户、组织及目标菜单结构。`spring.sql.init.mode=never`，旧 Java 分段读取已移除；Maven 仅将正式 SQL 复制到测试 classpath，业务 JAR 不含建表 SQL。测试在临时 SQLite 显式初始化；独立工具和技术历史表已实现，临时库测试通过；本机data/hrs_system.db已由手动工具执行2段并导入组织验证数据，生产部署仍未执行。
- **Java 启动不再因旧分段缺失失败，也不负责准备业务表。** 新基线可在空库或同结构下重复执行，不能升级未知旧结构；不要截取旧 V2/V3；使用独立工具先plan，再按目标状态apply/create或adopt-baseline，不能以Java启动代替升级。
- auth/analysis 的 SQL 当前仅注释占位，不创建数据库。Java测试直接复用正式基线，旧历史结构和菜单替换夹具已删除。Python 的既有初始化链路不随本次 system 方案一并改造。
- 每个变更说明前置状态、影响字段、数据保留、验证、恢复及停写要求。事务边界由工具控制，不能在新正式段内嵌独立 BEGIN/COMMIT。工具落地、Java 自动执行移除和运行教程更新须一起验收。
- SQLite 不支持所有 MySQL ALTER 语法。复杂改表可能需要建新表、复制校验、重建索引再切换，不能丢失约束、删除标记、审计字段及主键。
- 备份优先使用数据库一致性备份机制；若选择文件复制，先停止写入并正确处理WAL/SHM等状态。不能在运行中只复制一个 .db 就认为备份完整。
- 迁移前后核对行数、主键、关键业务值、NULL、归属与删除状态；用真实SQLite验证脚本，并覆盖重启读取。恢复备份前先确认迁移后的新增数据如何处理，不直接覆盖。
- SQLite单写者特性和锁等待要纳入并发验证。当前连接池最大1、busy_timeout=5000毫秒是用户案例的设置，不是所有未来服务必须照抄的容量规则。

完整设计、实际命令、变更注释协议和验收矩阵见 [SQL 管理与数据库升级方案](sql_management_and_execution_plan.md)。工具只支持SQLite；MySQL另行实现，不把SQLite脚本直接用于MySQL。

## 9. 后续迁移 MySQL 的验收要求

按服务逐个迁移，不把三个库合成一个全服务可写库。迁移至少完成：

1. 确认目标MySQL版本、驱动和框架组合，使用该版本实际支持的DDL与约束，明确utf8mb4、排序规则、严格模式和UTC时间约定。
2. 为每个服务建库和受限账号；连接地址与凭据从配置传入，更新 `.env.example`，不硬编码开发机环境。
3. 转换主键、时间、长度、类型和约束；SQLite的PRAGMA、typeof、INSERT RETURNING等不能盲目复制，MyBatis XML按实际数据库调整。
4. 比较账号大小写、尾部空格、NULL、唯一键及软删除后的重名行为。当前SQLite账号比较区分大小写，MySQL排序规则不能未经验证就改变该契约。
5. 用脱敏副本验证导入，保持ID、企业组织归属、密码哈希、审计时间和删除标志，检查导入后主键分配。迁移密码哈希，不还原明文密码。
6. 在MySQL上运行CRUD、筛选分页、事务回滚、约束、并发和权限测试；不能只用SQLite测试通过替代目标库验证。
7. 切换时保持唯一写入方，记录增量与回滚方式，不默认两库同时写。切换确认后停用旧SQLite写入口，保留合规备份。

## 10. 当前实现与规范的差异

| 项目 | 当前状态与处理 |
| --- | --- |
| system 用户表 | 新基线含delete_flag、enterprise_id、organization_id；后两列可空，dept_id及归属非空时用typeof与正数CHECK限制；审计字段非空，账号全表唯一，逻辑删除后仍不复用 |
| system 运行库 | 仓库根data/hrs_system.db已由手动工具初始化，通过HRS_SYSTEM_DB_URL指定；SQL不随Java启动执行 |
| system 组织主键目标 | 组织表organization_id为唯一主键，已移除id及原组织归属语义；SQL、Java、用户dept_id引用和同企业校验已同步，本机独立库已执行 |
| system 部门/菜单 | 新基线已包含三字段、审计列及目标菜单menu_业务列和module/group/page，内存SQLite验证通过；未删除菜单标识及page路由以部分索引唯一。本机system库已初始化并导入37条组织验证数据，用户和菜单仍为空，菜单导入待安排；执行工具已实现，Java启动初始化已关闭，测试直接使用正式基线，不再用另一份菜单DDL替换。用户dept_id由Java校验真实部门及归属 |
| system 企业与租户身份 | 仍无企业主数据和完整租户身份体系；普通业务表enterprise_id、organization_id为归属元数据，组织主数据表的目标organization_id按5.1.1为主键；不声称完成多租户权限 |
| auth、Java analysis | 尚为骨架，不提前建库建表 |
| Python 存量表 | stock_analysis.db中现有表未统一改名或补齐三字段；后续必须先盘点真实数据与调用方，再按业务移交和迁移计划收敛，不能把这份文档当成改造完成证明 |

## 11. 建表与改表审查清单

- [ ] 确认表的唯一所属服务，SQLite目录与配置地址正确，没有读写其他服务库。
- [ ] 表名为hrs_服务简称_业务名，字段小写下划线，Java属性和XML映射一致。
- [ ] 每张业务表包含delete_flag、enterprise_id、organization_id，并明确NULL、取值和审计策略。
- [ ] 普通读写、列表总数、批量及关联路径正确处理逻辑删除和数据范围。
- [ ] 业务唯一性、大小写、NULL、删除后复用规则明确，索引与真实查询匹配。
- [ ] DTO、Entity、VO不混用，不从客户端信任审计人或租户身份，不泄露凭据。
- [ ] 新库DDL与旧库迁移都经过真实数据库验证，旧数据与删除状态得到保留。
- [ ] 配置示例、专题文档、变更日志和测试同步；不提交实际数据库、备份或密钥。

关联文档：[SQL管理与数据库升级方案](sql_management_and_execution_plan.md)、[整体架构](../engineering/engineering_architecture.md)、[Java工程规范](../engineering/java_engineering_architecture.md)、[用户管理案例](../engineering/java_user_management_case.md)、[Nacos与独立数据库运行说明](../engineering/java_nacos_discovery.md)。

技术参考：[SQLite数据类型](https://www.sqlite.org/datatype3.html)、[SQLite库名与对象名解析](https://www.sqlite.org/lang_naming.html)。本规范暂无英文对应版，本次不新增平行翻译文档。

部门和菜单字段、树规则、V4初始化及已有用户关联收口见[部门与菜单案例](../engineering/java_organization_menu_management_case.md)。
