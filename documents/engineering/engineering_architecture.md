# <a id="engineering-architecture"></a>HermesX 整体工程架构

> 📝 **方案简述**：确定 HermesX 的全仓目录、Java 与 Python 分工、网页与桌面端协作、工程资产归属及交付验收标准。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-18

## 目录

- [一、设计目标与功能归属](#sec-1)
- [二、目标工程目录](#sec-2)
- [三、Java 分层与文件命名](#sec-3)
- [四、Java 与 Python 的数据和接口边界](#sec-4)
- [五、迁移顺序与验收](#sec-5)
- [六、前端、部署与仓库资产规范](#sec-6)

<a id="sec-1"></a>

## 一、设计目标与功能归属

目前网页与桌面端仍使用 Python 后端，其工程位于 `python/`。仓库根目录已有聚合三个 Java 服务的 Maven 工程骨架，各服务分为 pojo 与 rest；system 已有独立 SQLite 用户管理案例及菜单 Java 接口；菜单目标数据库和初始化数据暂缓，其他服务仍为骨架。后续目标是在现有分析能力上接入 Java 业务 API，让网页和桌面共享权限规则与接口，同时保留桌面本机运行方式。Java/Python 多服务部署尚未实施。

后续部署目标是 **三个 Java 服务和一个 Python 分析服务**。`hrs-auth-service`、`hrs-system-service`、`hrs-analysis-service` 各自独立运行，每个服务包含 pojo 数据模块和 rest 运行模块；根 POM 统一聚合构建。system 已提供独立的用户 CRUD 与配置管理身份保护；完整服务部署与 auth 认证接入另行安排。

| 子方案 | 维护范围 |
| --- | --- |
| [Java 工程架构](java_engineering_architecture.md) | Java 目录、业务模块、分层、文件命名及调用 Python 的规则。 |
| [Python 工程架构](python_engineering_architecture.md) | Python 当前与目标目录、五层职责、文件命名、数据源和存储规则。 |

| 模块或服务 | 负责内容 |
| --- | --- |
| Java · `hrs-auth-service` | 注册、登录、退出、凭据、账号启停和会话撤销。 |
| Java · `hrs-system-service` | 用户后台管理、组织部门、角色权限、数据范围、菜单、数据字典和业务设置。 |
| Java · `hrs-analysis-service` | 自选股、分组、最近搜索、研究偏好、分析任务归属和访问授权。 |
| Python · `python/` | 行情、指标、新闻情报、个股分析、大盘复盘、回测、选股、决策信号、报告、Agent，以及模型和数据源的运行配置。投组台账与计算、预警执行、定时任务、机器人和通知首期继续复用现有 Python 实现。 |

【强制】网页与桌面共用同一套 Java 业务 API 和 Python 分析接口。后续网页版由服务器运行三个 Java 服务和一个 Python 服务；桌面单机版需统一管理本机这四个服务的启动、就绪和退出，具体编排留待接入阶段验证。当前 Web 与桌面仍运行现有 Python 链路；后续浏览器与 Electron 经 Java 业务接口访问，Java 按需调用 Python。单机与服务器各自保存数据；需要共享账号和数据时，桌面需连接同一服务器。

<a id="sec-2"></a>

## 二、目标工程目录

```text
HermesX/
├── pom.xml                        # Java 构建入口
├── hrs-common/                    # 菜单依赖的公共响应与结果码JAR，不是独立服务
├── mvnw / mvnw.cmd
├── .mvn/wrapper/
├── hrs-auth-service/              # hermesx.auth，认证服务
│   ├── pom.xml                    # 聚合 pojo 与 rest
│   ├── pojo/                      # pom.xml、src/main/java/hermesx/auth/{base,entity,dto,vo}
│   └── rest/                      # pom.xml、src/{main,test}，控制器、服务、DAO、远程调用
├── hrs-system-service/            # hermesx.system，系统管理服务
│   ├── pom.xml
│   ├── pojo/
│   └── rest/
├── hrs-analysis-service/          # hermesx.analysis，股票研究业务服务
│   ├── pom.xml
│   ├── pojo/
│   └── rest/
├── python/
│   ├── .python-version / pyproject.toml / setup.cfg / requirements.txt
│   ├── main.py / server.py / webui.py
│   ├── api/
│   ├── src/                       # 保留现有 Python 分层及其包结构
│   ├── data_provider/
│   ├── bot/
│   ├── strategies/
│   ├── templates/
│   └── tests/
├── apps/
│   ├── hrs-web/                   # 网页与桌面复用界面
│   │   ├── package.json / package-lock.json
│   │   ├── src/                   # api、router、pages、components、stores、locales
│   │   └── public/ / tests/ / e2e/
│   └── hrs-desktop/               # Electron、安装和更新
│       ├── package.json / package-lock.json
│       ├── main.js / preload.js
│       └── renderer/ / scripts/ / tests/
├── docker/                        # 镜像、Compose 和容器启动
├── scripts/                       # 验证、构建、打包和辅助工具
├── .github/                       # CI、定时任务和发布
├── .conventions/                  # 现有通用、前端编码约定
├── docs/                          # 使用、配置和部署指南
├── documents/
│   ├── engineering/              # 整体工程、Java、Python 三份方案
│   ├── framework/                # 既有架构决策、实施基准和迁移记录
│   ├── authority/ / product/
│   └── CHANGELOG.md
├── AGENTS.md / CLAUDE.md           # 仓库协作规则及兼容软链接
├── start.sh                        # 保留根目录开发启动入口
├── .env.example                    # 脱敏配置示例，实施时校验忽略规则
└── README.md / LICENSE
```

- 【强制】三个服务的基础包分别是 `hermesx.auth`、`hermesx.system`、`hermesx.analysis`，源码位于各自 pojo/rest 的 `src/main/java/`，测试包对应源码。后续启动类分别为 `AuthApplication`、`SystemApplication`、`AnalysisApplication`，当前未实现。
- 【强制】包名只组织代码，构建产物由 Maven artifactId 决定。例如 auth 的两个产物为 `hrs-auth-service-pojo-<version>.jar` 与 `hrs-auth-service-rest-<version>.jar`，各自在对应子模块的 `target/` 内。auth/analysis 的 rest 仍是普通骨架 JAR；system/rest 已构建为 Spring Boot 可执行 JAR。
- 【强制】根 POM 仅聚合构建，根目录不再保留 Java `src/`；Python 位于 `python/`。配置、数据库、日志、报告与构建产物不作为源码入库。

<a id="sec-3"></a>

## 三、Java 分层与文件命名

【强制】每个服务采用按层平铺结构，层内按业务文件名分类，不再嵌套 auth/system/research 业务包。调用方向为 `Controller → Service 接口 → ServiceImpl → DAO`；跨服务由 ServiceImpl 调用 `service/remote/` 中的 Client，不访问对方实现或数据库。

| 所属模块和目录 | 文件示例 | 职责 |
| --- | --- | --- |
| pojo · `base/`、`entity/` | `BaseEntity.java`、`WatchlistEntity.java` | 必要基础类型及本服务持久化数据结构 |
| pojo · `dto/`、`vo/` | `CreateWatchlistDTO.java`、`WatchlistVO.java` | 业务输入与前端视图输出，实体不直接暴露 |
| rest · `controller/` | `AnalysisController.java` | 接收请求、校验格式、取得可信身份并调用 Service |
| rest · `service/`、`service/impl/` | `IAnalysisService.java`、`AnalysisServiceImpl.java` | 业务契约及规则、权限、数据范围和本地事务实现 |
| rest · `dao/` | `AnalysisTaskOwnershipMapper.java` | 本服务数据访问，Mapper 为采用 MyBatis 时的命名 |
| rest · `service/remote/` | `PythonAnalysisClient.java` | 远程协议、认证、超时和错误转换，远程载荷在 `remote/dto/` |

【强制】包名小写，类型名大驼峰且与文件名一致。完整目录、逐层职责和命名示例由 [Java 工程架构](java_engineering_architecture.md) 维护。system 用户管理的实现例外和教学说明见 [用户管理案例](java_user_management_case.md)；其余未授权功能仅保留骨架。

<a id="sec-4"></a>

## 四、Java 与 Python 的数据和接口边界

当前独立 system 用户 CRUD 为学习案例，暂沿用参考表的账号、密码哈希和状态字段；不提供表内用户登录。正式接入 auth 前必须按下述目标移交凭据和状态职责，不能把当前例外扩展为跨服务双写。

- 【强制】`hrs-auth-service` 与 `hrs-system-service` 使用同一个用户身份。账号状态由 `auth` 单独维护；管理员在 system 服务发起停用，由业务服务授权后调用 `auth` 停用账号和撤销会话。角色、菜单和数据范围按[后端授权方案](../authority/backend/user_role.md)细化。
- 【强制】Java 管任务与用户的归属，Python 管执行状态与报告。以查看报告为例：`AnalysisController` 获取当前用户，`AnalysisServiceImpl` 通过 `AnalysisTaskOwnershipMapper` 校验归属及数据范围，再经 `PythonAnalysisClient` 读取报告。
- 【强制】跨 Java 与 Python 的业务调用走已认证的内部接口。即使共用数据库实例，也不得跨服务读写对方管理的表。业务设置归 Java，模型和数据源凭据、运行参数及诊断归 Python。
- 【强制】客户端地址、凭据和超时均来自运行配置；区分远端业务错误、超时和不可用。远程调用不占用 Java 数据库事务。提交任务等写操作必须定义幂等与超时确认方式，再开启自动重试；详情见 [Java 的远程调用规范](java_engineering_architecture.md#sec-3)。

<a id="sec-5"></a>

## 五、迁移顺序与验收

各批次的文件范围、验证命令和回滚门槛见 [工程架构实施计划](engineering_architecture_plan.md)。

**本期范围**：先完成 P0 基线和 P1 Python 目录迁移，再建立 P2 的三个 Java 服务工程骨架。Java 源码、登录和分析接入及Java/Python 多服务部署留待另行安排。下列顺序描述长期演进目标。

**项目尚未上线，直接按目标结构调整。** 旧源码位置、内部路径或开发命令需要变化时，同批更新现有调用方、脚本、CI 和文档；不为保留旧路径新增转发脚本、重复目录或可切换的两套布局。P1 保留原分析行为和现有功能，已有本地配置和数据仍需保护。

1. **迁移 Python 路径。** 保留包内布局和现有行为，更新根启动脚本、CI、Docker、每日任务、桌面打包、静态资源和策略模板路径。验收现有 CLI、服务、定时任务和桌面版仍能运行；这一批可独立回退。
2. **接入三个 Java 服务。** 先打通「登录 → 提交分析 → 查询进度 → 查看报告」。用两个用户验证列表、读取和删除权限，确认旧报告来源与可见范围，并验收超时重试不会重复创建任务。
3. **交付网页和桌面共用链路。** 验收网页版访问服务器 Java、桌面安装包启动和关闭本机三个 Java 服务与 Python，两端使用同一业务 API。随后逐项迁入业务 CRUD；每迁一项，只保留明确的数据写入方，并在移除旧入口前核对 CLI、定时任务与机器人依赖。

<a id="sec-6"></a>

## 六、前端、部署与仓库资产规范

| 位置 | 设计约定 |
| --- | --- |
| `apps/hrs-web/` | 维护供浏览器与 Electron 共用的页面、路由、组件、状态、国际化和 API 访问。请求收口到 `src/api/`，不要在页面里按运行环境复制业务逻辑。界面组件、国际化和类型命名沿用 [前端约定](../../.conventions/frontend/)；菜单数据来源、结构、加工与持久化见[菜单方案](../authority/frontend/frontend_module_menu.md)；动态路由派生、注册、刷新和守卫见[动态路由方案](../authority/frontend/frontend_async_router.md)；接口字段见[菜单API契约](../authority/frontend/menu_api_contract.md)。 |
| `apps/hrs-desktop/` | 维护窗口、受控的 preload 接口、后端进程生命周期、安装和更新。单机模式打包同一份 Web 界面和本机后端，后端绑定本机地址；界面通过业务 API 访问，桌面桥接只提供需要的本机能力。 |
| `docker/`、`scripts/`、`.github/` | Docker 管镜像和联机部署，脚本统一本地启动、构建及检查，工作流调用这些入口并负责发布。Docker 与桌面各自传入运行地址、数据目录和静态资源位置。 |
| `docs/`、`documents/` | 面向使用者的部署和配置写在 `docs/`，工程设计写在 `documents/engineering/`，专题方案和历史实施记录保留在现有位置。 |
| 配置、运行数据和构建产物 | 区分 Git 仓库根、Python 工程根和运行数据位置。运行数据与配置文件的位置由相应启动环境解析，不能随工作目录或源码移动而改变。配置示例脱敏入库；账号凭据、真实 `.env`、本地数据库、日志和生成报告由运行环境管理。Maven `target/`、Web `dist-web/`、桌面 `dist-desktop/` 为构建产物。Python 随源码分发的股票索引与运行数据分开。 |
