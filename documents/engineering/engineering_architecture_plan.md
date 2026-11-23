# <a id="engineering-architecture-plan"></a>HermesX 工程架构实施计划

> 📝 **方案简述**：把全仓、Java 和 Python 架构方案落实为可独立验收和回滚的代码批次，先完成等价的 Python 目录迁移，再接入 Java 和网页、桌面共用的业务链路。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-18

## 目录

- [一、实施边界与批次总览](#sec-1)
- [二、P0：建立迁移基线](#sec-2)
- [三、P1：迁移 Python 工程目录](#sec-3)
- [四、P2：建立 Java 骨架，业务实现后置](#sec-4)
- [五、P3：打通分析任务与报告](#sec-5)
- [六、P4：切换网页、桌面与部署入口](#sec-6)
- [七、P5：按业务能力移交数据](#sec-7)
- [八、交付与最终验收](#sec-8)
- [九、本期执行记录](#sec-9)

<a id="sec-1"></a>

## 一、实施边界与批次总览

**2026-11-24 SQL 执行状态更新**：SQLite 继续过渡，每服务固定同名 SQL；基线已收敛，Java 已关闭启动初始化并移除分段读取，正式 SQL 只复制到测试 classpath。独立手动工具和执行历史已实现并在临时库验证，正式部署仍待安排；执行约定及MySQL后续工作按 [SQL 管理与数据库升级方案](../DB/sql_management_and_execution_plan.md)的 DB-0～DB-5 批次执行，下文早期收拢记录仅描述当时阶段，当前实现与验收以上述状态及最新记录为准。

**2026-11-18 范围更新**：原 P2“仅骨架”的初始交付已完成。现按用户新的明确授权，额外实现 system 的 SQLite 用户管理学习案例；不表示 P2 完整认证及 P3–P5 已获执行授权。案例的接口、字段、阶段性凭据归属例外和运行方法见 [用户管理案例](java_user_management_case.md)。

实施依据为 [整体工程架构](engineering_architecture.md)、[Java 工程架构](java_engineering_architecture.md) 和 [Python 工程架构](python_engineering_architecture.md)。本文定义施工顺序与验收门槛，各层的编码规则由子方案维护。Java 业务实现和Java/Python 多服务部署不在本期范围。

【强制】**本期最高优先级是调整仓库目录和工程边界。按 P0 → P1 → P2 骨架的顺序执行，骨架验收后停止。** P2 的 Java 实现以及 P3–P5 仅作为后续规划，等另行安排；本期不接入 Java 服务，不切换现有入口。

| 批次 | 本期安排 | 交付与验收 |
| --- | --- | --- |
| P0 | 优先完成 | 记录命令、路径、契约与数据位置，明确存量失败和阻断项。 |
| P1 | P0 后完成 | Python 工程完整位于 `python/`，调整后的入口能完成原有功能，数据和配置读写通过验收。 |
| P2 | 只建工程骨架 | 根目录 Maven 构建文件及源码、资源、测试目录到位；不编写 Java 源码，不接入 Java 运行链路。 |
| P3–P5 | 后续安排 | 保留分析接入、网页与桌面切换及数据移交计划，本期不执行。 |

【强制】P1 只做目录迁移及配套路径修正，不改 Python 包名、分析算法、选源行为、用户 API 和数据库结构。不在这一批引入 Java、重构 Python 五层或清理旧模块。真实 `.env`、数据库、报告和日志留在原有运行位置；用已有配置或经验证的默认路径解析它们。

【强制】项目尚未上线，按目标目录直接迁移。旧内部路径和开发命令可以调整，相关调用方同批改到新位置；不为旧位置新增兼容脚本、双份实现或过渡开关。仍有真实职责的入口（如承担根目录启动编排的 `start.sh`）保留并更新。修改范围由目标结构和实际调用链决定。

【强制】本期只交付迁移后的 Python 工程和不含新增 Java 实现的 Java 骨架。三个 Java 服务（`hrs-auth-service`、`hrs-system-service`、`hrs-analysis-service`）加一个 Python 服务是后续部署目标；每个 Java 服务分为 pojo/rest 两个 Maven 子模块，后续也不默认引入独立网关、消息中间件或分析 Worker。

<a id="sec-2"></a>

## 二、P0：建立迁移基线

1. 记录执行时的 Git HEAD、工作区状态、使用的平台和 Python 环境。盘点从仓库根启动的 CLI、API、定时任务、Bot、Web 静态资源、Docker 及桌面安装包；记录入口、工作目录、资源和运行数据位置。
2. 执行 `python scripts/check_architecture.py --check`、`./scripts/ci_gate.sh`；如果门禁提前退出，单独执行 `python -m pytest -m "not network"` 取得独立测试结果。记录 CLI `--dry-run`、本地健康接口和静态资源检查结果，使用临时数据目录或脱敏副本。
3. 当前架构检查已报出 `src/application/system/system_dict_service.py` 对国家数据源、具体仓储和 `src.storage` 的三处存量依赖。实施时复核；若仍阻断门禁，单开修复批次，用应用端口与 bootstrap 装配收口，并覆盖国家字典读取、同步和失败行为。修复通过后再合入 P1，不修改基线掩盖问题。
4. 建立关键契约对照表：分析提交、进度、历史与报告、设置读取、自选股、登录 Cookie；记录现有路径、状态码和前端依赖字段。部署、桌面流程加上旧数据库打开和重新启动后的数据读取检查。
5. 记录离线测试收集的用例及数量、架构扫描覆盖的文件数，以及关键 CI 构建或打包检查的触发路径。按本地、容器和桌面分别记录 Python 实际读取及写入的配置文件与数据库位置。只保留路径和结果，不记录真实凭据。

**完成标准与回滚**：提交可复查的基线结果和路径清单；P0 不改运行配置。若有独立的字典修复，单独保留其验证与回滚边界。

<a id="sec-3"></a>

## 三、P1：迁移 Python 工程目录

将 `main.py`、`server.py`、`webui.py`、`src/`、`api/`、`data_provider/`、`bot/`、`strategies/`、`templates/`、`tests/` 及 Python 的依赖和工具配置移至 `python/`。移动后仍从 Python 工程位置解析 `from src…` 等现有导入。按以下清单逐项核对改动：

| 改动面 | 重点文件与动作 |
| --- | --- |
| 开发入口 | 根 `start.sh` 负责启动编排，Python 子进程使用正确工程目录。直接运行 Python 的命令更新到开发指引，不在根目录保留旧 `main.py` 或 `requirements.txt` 的转发副本。 |
| 资源和运行数据 | 分别定位 Git 仓库根、Python 工程根和运行数据路径。核对 `api/app.py` 的 `HRS_STATIC_DIR` 与根 `dist-web/`、内置策略与模板，以及配置读取、设置保存和数据库默认路径。位置解析不依赖碰巧正确的进程工作目录。 |
| 测试与架构守卫 | 更新 `scripts/ci_gate.sh`、`scripts/test.sh` 和 `tests/support/paths.py` 的调用方：访问 `.github/`、`docker/`、`scripts/` 用仓库根；查找 Python 源码和资源用 Python 工程根。架构检查从 Git 根显式指定 `--root python --baseline scripts/architecture_baseline.json`，基线里的路径继续相对扫描根。对比迁移前后的测试收集和扫描文件数，逐项解释差异；扫描不到文件不得视为通过。 |
| 容器与流水线 | 更新 `docker/Dockerfile` 的依赖和源码复制路径、Compose 数据挂载及入口；核对 CI 路径过滤、pip 缓存、每日分析、网络检查和镜像发布引用。 |
| 桌面与辅助工具 | 更新 Windows/macOS 的后端和桌面打包脚本、开发启动分支与股票索引脚本。核对 PyInstaller 入口、内置策略资源、Electron 静态产物及安装包路径；此时 Electron 仍只启动原 Python 后端。 |

**验收**：对比 P0 的离线测试、CLI、API 和静态资源结果；用临时配置执行定时任务验证，检查 Docker 镜像和桌面包能启动并读取原位置的数据。Windows/macOS 安装验证分别记录；平台缺口不视为通过。更新现有使用命令和双语对应说明。

- **数据与设置往返**：用脱敏的旧数据库和配置副本验证能看到已有记录；在设置界面保存一项非敏感设置后核对写入目标，重启后重新读取。检查 `python/` 或其他错误位置没有被悄悄新建空数据库或配置文件。
- **干净检出**：至少从一个无现成虚拟环境、无前端产物和桌面打包缓存的检出运行文档中的安装和启动命令。核对 CI 中迁移后的 Python 路径能触发相应打包检查；同时核对只改无关文档不会误触发专用检查。

**回滚**：整批恢复文件位置和引用改动，不做数据库逆迁移。若回滚需要还原用户数据，说明 P1 已超出预定范围，应在合入前拆分。

<a id="sec-4"></a>

## 四、P2：建立 Java 骨架，业务实现后置

**本期只建骨架，现已按三服务方案调整。** 根 POM 为 `hermesx-parent`，聚合三个服务；服务 POM 分别聚合 pojo/rest。每个 rest 仅依赖本服务 pojo，暂时构建普通 JAR，不配置启动类、Spring Boot、数据库或认证依赖。使用 JDK 17 编译目标与根 Maven Wrapper。空目录以 `.gitkeep` 保留，`application.yml` 仅含骨架说明注释。

```text
HermesX/
├── pom.xml / mvnw / mvnw.cmd / .mvn/wrapper/
├── hrs-auth-service/              # hermesx.auth
│   ├── pom.xml
│   ├── pojo/pom.xml
│   ├── pojo/src/main/java/hermesx/auth/{base,entity,dto,vo}/
│   ├── pojo/src/test/{java/hermesx/auth,resources}/
│   ├── rest/pom.xml
│   ├── rest/src/main/java/hermesx/auth/
│   │   ├── controller/
│   │   ├── service/impl/
│   │   ├── service/remote/dto/
│   │   ├── dao/、config/、security/、exception/
│   │   └── interceptor/、utils/
│   ├── rest/src/main/resources/{application.yml,mapper/}
│   └── rest/src/test/{java/hermesx/auth,resources}/
├── hrs-system-service/            # 同样的 pojo/rest 结构，包名 hermesx.system
└── hrs-analysis-service/          # 同样的 pojo/rest 结构，包名 hermesx.analysis
```

**本期验收与回滚**：`./mvnw verify` 验证全部 11 个 Maven 模块（含后续新增common）；原P2骨架验收只包含三个rest→本服务pojo的依赖；后续common和system案例另按末尾记录验收，不把骨架期的“无Java实现”套用于当前状态。原根源码目录的用户空文件 `test.java` 原样移到 auth/rest 的对应包，保持未跟踪状态。未改 Python、Web、桌面、Docker 和发布入口，不要求 Java 能启动。回滚仅撤回 Java 构建与目录调整并原样恢复用户文件，P1 Python 迁移和本地数据不变。

**后续实施（待另行安排）**：

1. 在既有骨架上配置各服务启动类 `hermesx.auth.AuthApplication`、`hermesx.system.SystemApplication`、`hermesx.analysis.AnalysisApplication`、健康检查、运行参数和 Java 构建门禁。实现前记录兼容的 JDK、Spring Boot、持久化方案与桌面运行时选择；新增配置同步更新脱敏的 `.env.example` 与文档。
2. 按 `hermesx.auth` 和 `hermesx.system` 实现账号、登录、退出、会话、最小角色授权和数据范围。先实现分析链路所需的用户管理与权限；完整部门、菜单和字典后台分批补齐。注册角色由服务配置和策略决定；请求不赋予自己权限。
3. 对照 [用户、角色与菜单授权方案](../authority/backend/user_role.md)，确定账号与后台用户的同一标识、账号状态的唯一写入方、初始化管理员方式、Cookie 兼容策略和停用后的会话撤销。持久层只管理 Java 业务数据。

**后续验收**：`./mvnw verify`（Windows 使用 `mvnw.cmd verify`）通过；覆盖注册和默认角色、登录退出、重复账号、管理员停用后现有会话失效、普通用户无权执行管理操作。此时仍可独立启动 Python，暂不切换现有网页或桌面流量。

**后续回滚**：撤回新启用的 Java 服务与流量配置。保留该阶段产生的 Java 数据，按明确的数据恢复方案处理；不清除 Python 用户配置。

<a id="sec-5"></a>

## 五、P3：打通分析任务与报告

1. 定义 Java 到 Python 的内部契约：提交、查询状态和读取报告，以及测试矩阵需要的列表与删除。明确任务 ID、提交幂等键、错误码、超时和进度字段。Python 通过认证后的内部接口复用现有执行逻辑，不复制分析流水线。
2. 在 `hrs-analysis-service` 的 `hermesx.analysis` 包内按 `controller/`、`service/impl/`、`dao/`、`service/remote/` 落地，数据类型放该服务的 pojo 模块。Java 从登录上下文确定当前用户，保存任务归属；Python 保存分析执行状态与报告。Java 的 `PythonAnalysisClient` 处理协议、超时和错误映射；查报告、删报告和获取进度都先由 Java 校验数据范围。
3. 推荐先落下归属记录及待提交状态，再在数据库事务外调用 Python。提交超时后用同一请求标识查询受理结果；只有 Python 能依据稳定的幂等标识识别并返回已有任务时才允许自动重试。若尚不支持安全重放，明确显示待确认并提供对账路径。未归属的旧报告不默认加入所有用户可见范围。

**验收**：用真实 Java 与 Python 测试接口，覆盖「登录 → 提交 → 进度 → 报告」；用户 A 不能枚举、读取、删除或订阅用户 B 的任务。覆盖认证失效、Python 不可用、远端已受理但响应超时、同一请求重放与旧历史归属。区分已持久化报告和进程内进度，记录 Python 重启后的行为。

**回滚**：关闭新分析入口，保留任务归属记录和已生成的 Python 报告；对进行中的任务按 ID 核对后再恢复流量，避免重提。

<a id="sec-6"></a>

## 六、P4：切换网页、桌面与部署入口

- **Web**：在 `apps/hrs-web/src/api/` 收口 Java API 地址、认证和错误处理；保持页面与协议一致。核对登录状态、Cookie、轮询和现有流式端点。尚未迁移的界面能力由 Java 提供明确的兼容调用或暂缓切换；不公开绕过授权的 Python 内部入口。
- **服务器**：更新 `docker/`，提供 Java 对外入口及 Python 内部地址；确定静态资源托管和服务就绪检查。按部署模式明确调度责任，避免默认同时启动两套定时分析。更新 CI 的 Java、Python、Web 路径过滤及镜像构建。
- **桌面**：`apps/hrs-desktop/` 复用 Web 构建产物，安装包携带所需 Java 运行时和 Python 后端。在本机启动时配置服务地址、数据目录和内部认证，等待三个 Java 服务与一个 Python 服务就绪；验证启动失败、端口占用和退出后的进程清理。服务器连接模式若实现，使用同一对外 API，不启动本地分析进程。

**验收**：Web 执行 `npm ci`、`npm test`、`npm run lint`、`npm run build`；验收 Docker 四服务联动及 Windows、macOS 目标安装包。浏览器与桌面用同样的 API 完成登录、分析、报告链路；涉及界面变化时，在 PR 中提供截图。正式切换前确认核心旧功能、存量数据和退出/升级路径已有验证证据。

**回滚**：各运行形态分别保留上一版部署配置或安装包。切换前标记哪些数据已在新系统写入；回到旧入口时保持单一写入方，先核对是否需要导回切换期间新增数据。

<a id="sec-7"></a>

## 七、P5：按业务能力移交数据

按小批次实现 `system` 的组织、角色、菜单、字典和业务设置，以及 `analysis` 的最近搜索、自选股分组和研究偏好。可先用最近搜索验证迁移办法，再处理有关联数据和定时任务依赖的自选股。投组台账与计算、预警执行、模型与数据源运行配置、Bot 和通知首期仍在 Python。

每个功能执行同一套切换流程：

1. 列出 Web、桌面、CLI、每日任务和 Bot 的读写入口，明确现有数据归属及新表的唯一写入方。
2. 用脱敏副本验证迁移、用户映射、去重和数据条数/关键字段核对；对无归属记录单独处理。重复执行迁移不得重复导入。
3. 停止旧写入，完成迁移和校验后启用 Java 写入。旧入口需要保留时，只读或转到新所有方。定时分析需要自选股时，经接口读取或随任务传入。
4. 验证两端的查询、权限和修改，核对旧入口调用方已迁离再退役；记录切换点、迁移前后的数据校验以及回滚所需的备份或增量导出。

**回滚**：未切换写入前可直接回到旧入口。已切换时先停止新写入，核对切换后增量并按已演练的方案导回或恢复，再启用旧写入，避免两边并行修改。

<a id="sec-8"></a>

## 八、交付与最终验收

**本期收尾条件**：P0 的基线已记录，P1 的 Python 搬迁通过等价验收，P2 骨架已建且没有新增 Java 实现及运行入口变更。以下其余条目用于长期架构的最终验收，不要求在本期完成。

- [ ] Python 目录迁移可独立审查和回退，旧 CLI、API、定时分析、Bot、Docker 及原桌面包行为有验收证据。
- [ ] Java 的分包、依赖、命名及事务边界符合子方案，跨语言调用有鉴别身份、对象授权和故障测试。
- [ ] 网页和桌面使用相同业务接口；桌面单机仍可启动本机后端，服务器保护内部 Python API。
- [ ] 每个已迁功能有唯一写入方、可重复核对的数据迁移记录和回滚演练；存量数据和密钥未随源码进入版本管理。
- [ ] 对用户可见的 CLI、API、部署和打包变化更新相关指南及 `documents/CHANGELOG.md`；双语未同步时说明原因。

每批交付记录实际改动、执行命令与结果、尚未覆盖的平台或联网场景，以及回滚位置。缺少阻断验收证据的批次不视为完成。各阶段实际完成情况以下方执行记录为准。

<a id="sec-9"></a>

## 九、本期执行记录

- **P0 基线**：以 `4cf604dc` 的干净源码为基线，在 macOS ARM64、Python 3.11.15 上收集 5,994 个离线用例（4 个联网用例排除）。离线基线 5,986 通过、8 失败：5 项依赖未纳入版本控制的 `.env.example`，3 项分时测试替身未接受现有的 `fast` 参数。原架构门禁另报国家字典的三条跨层引用。字典改由装配层注入原仓储和数据源，数据库结构、API 和字典行为不变。
- **P1 路径切换**：从仓库根安装 `python/requirements.txt`、启动 `python/main.py`；从 `python/` 运行 Python 测试。容器内部仍以 `/app` 为运行目录；Electron 开发入口使用 `python/main.py`，安装包继续使用冻结的 Python 后端。定时任务、依赖缓存、路径过滤和打包脚本已切换。拟入库的配置仅为脱敏的 `.env.example`，已有真实配置与 SQLite 数据未随源码移动。
- **P1 Python 与容器验证**：门禁全部通过，5,996 个离线用例通过、4 个联网用例排除。使用干净源码副本和新虚拟环境安装依赖，从仓库根和 Python 工程根分别启动 API，验证静态资源、已有 SQLite 数据及设置保存后重启可读。Docker 镜像完成构建，容器内首页、健康检查、模板和 SQLite 文件均可用。CLI 的 AAPL dry-run 已执行，外部行情未成功返回，未验证完整联网分析。
- **P1 客户端验收缺口**：Web 构建通过，ESLint 与基线均报 54 个错误和 7 个警告，本轮 Web 测试有 14 项失败，尚不能判全绿。Electron 单元测试通过 49 项；macOS 冻结后端通过启动、依赖导入、策略和资源检查，完整 DMG 在 Electron 下载时中断；Windows 安装和远端 Actions 尚未验证。
- **P2 三服务骨架（2026-11-18）**：根聚合工程下建立 auth、system、analysis 三个服务及各自 pojo/rest，`./mvnw verify` 的 10 个模块全部通过。rest 仅依赖本服务 pojo，未新增 Java 实现、启动类、数据库或应用框架依赖。原用户空文件 `test.java` 原样迁入 auth/rest；包目录用 `.gitkeep` 保留，配置仅含说明注释。已验证 POM 继承、模块依赖、路径、文档锚点与嵌套 target 忽略规则；未进行 Java 运行、Windows Wrapper 或四服务集成验证，因为本期尚无这些运行能力。

- **system 用户管理案例（2026-11-18）**：在 pojo/rest 分层下实现用户 CRUD、SQLite 建表、BCrypt、独立配置管理身份和 CSRF 保护；未接入 auth、Python 或客户端。根 Maven verify 的全部10个模块通过，5组真实SQLite集成场景通过；可执行JAR真实HTTP认证、CSRF、CRUD与重启持久化检查通过。未执行 Windows、远端部署或前端联调。凭据字段暂存 system 的阶段性例外见案例文档。

- **system Mapper 调整（2026-11-18）**：按用户要求，以 MyBatis UserMapper + XML 替换原 JdbcTemplate UserDao；保留 SQLite 表与 HTTP 契约，补充 INSERT RETURNING 回滚验证。`./mvnw clean verify` 全部10个模块及6组集成测试通过，可执行JAR真实HTTP与重启持久化检查通过。

- **用户企业与组织字段（2026-11-18）**：新增 enterprise_id、organization_id，并贯通 DTO/Entity/VO、Mapper XML 和列表精确筛选，字段可空且有值时必须为正整数；提供旧 SQLite 显式升级脚本，不自动修改本机数据，不将归属字段宣称为租户隔离。全部10个Maven模块和9项测试通过，包含旧表保留数据升级；可执行JAR验证新增归属落库、重启读取及原CRUD通过。

- **system Nacos 接入（2026-11-18）**：仅 system/rest 引入服务注册与发现，默认关闭以支持离线开发，开启时要求配置地址与专用命名空间；保留独立 SQLite 数据库。本机已有Nacos2.5.4下注册、通过发现地址访问API及退出注销验证通过，全部10个Maven模块和12项测试通过。具体版本约束、启动方式与验证见 [Nacos 接入说明](java_nacos_discovery.md)。

- **system 配置格式统一（2026-11-18）**：将 system 的 application.yml 转为 application.properties，21项配置及环境变量默认值保持一致；auth/analysis 骨架暂不调整。

- **部门与菜单服务端（2026-11-19）**：参考scaffold在system实现Organization/Menu的DTO、Entity、VO、Controller、Service接口/实现及Mapper/XML；通过显式V4幂等初始化新增hrs_system_organization、hrs_system_menu。补齐循环检查、树筛选祖先保留、部门移动子孙路径原子更新、菜单类型与删除规则、用户部门关联校验；auth/Python/客户端不变。全部10个Maven模块和22项测试通过，并通过临时SQLite下可执行JAR真实HTTP、CSRF、重启持久化和软删除检查。说明见[部门与菜单案例](java_organization_menu_management_case.md)。

- **common与统一响应（2026-11-19）**：新增普通hrs-common JAR，迁移PageVO并替换ErrorVO；system用户/部门/菜单/CSRF、业务异常、安全过滤器及错误分发统一为RestResult。删除由204改200/true，CSRF读取resultData.token。方案见[统一响应](java_common_response_design.md)，不改数据库和Python接口。

- **统一响应验收**：干净构建全部11个Maven模块通过，common 3项测试与system 27项测试共30项通过；真实可执行JAR验证成功/删除/分页/树/CSRF及400/401/403/404/405/406/415/500统一JSON，保留Basic认证挑战。未改真实数据库和客户端，Windows及跨服务业务调用未验证。

- **当前交付边界（2026-11-23）**：用户统一响应、部门与用户关联、菜单Java及可选Nacos配置分批入库；正式业务数据库、目标菜单结构部署与数据导入暂缓。前端最新隐藏祖先/状态职责规则、用户级授权及真实身份转发联调仍待实施。历史验证记录不等同于本轮重新在线验收。auth/test.java为迁移保留的零字节用户占位文件，最终以独立chore提交记录，不包含auth实现。

- **SQL维护入口收拢（2026-11-23）**：每个Java服务的sql/目录统一维护同名.sql文件；system将INIT/V2/V3/V4收拢为版本分段，构建复制入JAR，启动仍只选INIT/V4。移除旧正式SQL路径并同步测试和文档，不执行业务库迁移，也不引入自动版本记录。

- **SQL新库基线整理（2026-11-23）**：按先修改SQL文件的要求，将system正式文件收敛为BASELINE_20261123，移除INIT/V2/V3/V4，三表结构与Mapper列对齐，补齐约束和索引。内存SQLite3.43.2完成47项映射/约束检查及重复执行验证；没有创建真实业务库。Java仍引用旧分段，因此本轮不宣称Maven/启动链路通过，后续按DB批次同步工具、配置和测试。

- **Java启动与SQL执行解耦（2026-11-24）**：system生产配置改为spring.sql.init.mode=never，移除SqlScriptConfig/VersionedSqlResource与旧分段测试。正式SQL只复制到测试classpath，业务JAR不含SQL；CRUD测试使用正式基线，移除菜单替换DDL。根./mvnw -o clean verify的11模块、40测试通过；打包JAR在隔离临时库连续启动两次并通过Basic查询，结构和业务数据未变化。独立手动工具及真实数据库部署仍未实施，回退本次只涉及代码、配置和文档，无真实数据库需回滚。

- **SQLite手动升级工具（2026-11-24）**：新增scripts/db/manual_db_upgrade.py及标准库unittest临时库测试；SQL使用@service、@dialect和逐段@upgrade JSON声明，工具按历史与规范结构选择待办，不在Java维护版本列表。支持plan、apply/create、adopt-baseline、SHA-256摘要、独立技术历史表、写锁复查、一致性备份和整批回滚；Java仍关闭初始化。工具测试接入ci_gate.sh deterministic。实际业务库、MySQL和自动部署未操作。

- **手动工具验收（2026-11-24）**：Python3.9和3.11下各28项真实SQLite测试通过，覆盖事务回滚、WAL快照、无历史库接管与两进程竞争；根Maven11模块40测试通过。工具创建临时库后，打包Java真实HTTP完成Basic/CSRF用户及菜单新增和导航，工具重跑无待办，结构及历史未被Java改写。未操作实际数据库，MySQL、Windows、Docker与远端Actions未验证。

- **提交前并发修正（2026-11-24）**：加压复查发现，普通文件描述符探测可能释放同进程SQLite写锁；数据库读取改为SQLite接口，补备份连接不释放写锁的回归。最新工具29项测试通过，30轮双进程验证通过；未修改实际业务库。
