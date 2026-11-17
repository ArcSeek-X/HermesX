# <a id="java-python-backend-design"></a>HermesX Java 与 Python 后端协作方案

> 📝 **方案简述**：确定 HermesX 的目标仓库结构、Java 模块和代码分层、Python 分析服务的边界，以及网页与桌面单机版的统一接入方式。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-17

## 目录

- [一、部署与功能归属](#sec-1)
- [二、目标工程目录](#sec-2)
- [三、Java 分层与文件命名](#sec-3)
- [四、Java 与 Python 的数据和接口边界](#sec-4)
- [五、迁移顺序与验收](#sec-5)

<a id="sec-1"></a>

## 一、部署与功能归属

本方案描述目标架构，尚未实施。首期部署 **一个 Java 业务 API 和一个 Python 分析服务**。Java 的 `auth`、`system`、`research` 是同一个 Spring Boot 应用中的业务模块，共用根目录的 `pom.xml` 和一个启动类。后续只有在独立部署、扩容或复用需求明确时，才考虑拆分。

| 模块或服务 | 负责内容 |
| --- | --- |
| Java · `auth` | 注册、登录、退出、凭据、账号启停和会话撤销。 |
| Java · `system` | 用户后台管理、组织部门、角色权限、数据范围、菜单、数据字典和业务设置。 |
| Java · `research` | 自选股、分组、最近搜索、研究偏好、分析任务归属和访问授权。 |
| Python · `hrs-analysis` | 行情、指标、新闻情报、个股分析、大盘复盘、回测、选股、决策信号、报告、Agent，以及模型和数据源的运行配置。投组台账与计算、预警执行、定时任务、机器人和通知首期继续复用现有 Python 实现。 |

【强制】网页与桌面共用同一套 Java 业务 API 和 Python 分析接口。网页版由服务器运行两个后端；桌面单机版由 Electron 管理本机两个后端的启动、就绪和退出。浏览器与 Electron 都访问 Java，Java 按需访问 Python。单机与服务器各自保存数据；需要共享账号和数据时，桌面需连接同一服务器。

<a id="sec-2"></a>

## 二、目标工程目录

```text
HermesX/
├── pom.xml                        # Java 构建入口
├── mvnw / mvnw.cmd
├── .mvn/wrapper/
├── src/
│   ├── main/
│   │   ├── java/hermesx/
│   │   │   ├── HermesApiApplication.java
│   │   │   ├── config/            # 应用与客户端配置
│   │   │   ├── web/               # 全局 HTTP 错误处理
│   │   │   ├── auth/
│   │   │   │   ├── account/
│   │   │   │   ├── session/
│   │   │   │   └── security/
│   │   │   ├── system/
│   │   │   │   ├── user/
│   │   │   │   ├── organization/
│   │   │   │   ├── permission/
│   │   │   │   ├── menu/
│   │   │   │   ├── dictionary/
│   │   │   │   └── settings/
│   │   │   └── research/
│   │   │       ├── watchlist/
│   │   │       ├── recentsearch/
│   │   │       ├── preferences/
│   │   │       └── analysis/
│   │   └── resources/
│   │       ├── application.yml
│   │       └── db/migration/       # 如采用 Flyway
│   └── test/
│       ├── java/hermesx/           # 与被测代码包名对应
│       └── resources/
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
│   └── hrs-desktop/               # Electron、安装和更新
├── docker/                        # 镜像、Compose 和容器启动
├── scripts/                       # 验证、构建、打包和辅助工具
├── .github/                       # CI、定时任务和发布
├── .conventions/backend/          # Java 编码约定
├── docs/                          # 使用、配置和部署指南
└── documents/                     # 架构、授权、产品方案和 CHANGELOG
```

- 【强制】基础包名为 `hermesx`，启动类为 `hermesx.HermesApiApplication`。业务模块使用 `hermesx.auth`、`hermesx.system`、`hermesx.research`，测试包与源码对应。
- 【强制】包名只组织代码。构建产物由 Maven 的构建配置命名，例如 Java 后端可使用 `hrs-api` 作为 `artifactId`，产物为 `target/hrs-api-<version>.jar`。
- 【强制】模块按各自工程目录构建。根目录的 `src/` 最终只放 Java 源码和资源，现有 Python `src/` 随 Python 工程迁入 `python/src/`。本地数据库、实际环境配置、日志、报告和构建产物不纳入源码版本管理。

<a id="sec-3"></a>

## 三、Java 分层与文件命名

【强制】先按业务分包，再按职责分层。调用方向为 `Controller → Service → DAO`，远程访问从 `Service → Client` 发起。跨 Java 模块调用对方公开的服务方法，不访问其内部 DAO，不产生循环依赖。

| 目录 | 文件示例 | 职责 |
| --- | --- | --- |
| `controller/` | `AnalysisController.java` | 接收请求、校验格式、从认证上下文取得操作者，调用 Service 并组装响应。 |
| `service/` | `AnalysisService.java` | 执行业务规则、权限和数据范围检查，协调 DAO 与 Client，定义本地事务边界。 |
| `dao/` | `AnalysisTaskOwnershipDao.java` | 查询和写入本模块管理的数据。使用 MyBatis 时可按需采用 `dao/mapper/XxxMapper.java`，无需添加纯转发 DAO。 |
| `client/` | `PythonAnalysisClient.java` | 处理远程协议、认证、超时和错误转换。远程请求与响应类型放在 `client/dto/`。 |
| `dto/` | `CreateWatchlistRequest.java`、`WatchlistResponse.java` | 对外请求和响应；数据库实体放 `dao/entity/`，不直接暴露给前端。 |
| `domain/` | `StockSymbol.java`、`WatchlistRules.java` | 按需存放业务模型、值对象和纯规则。 |

【强制】包名小写，Java 类型名用大驼峰，文件名与公开顶层类型名一致。按职责建立目录，业务没有对应职责就不建空目录。详细命名、对象转换、依赖规则和审查清单见 [Java 后端分层与文件组织规范](../../.conventions/backend/JAVA_LAYERING.md)，该规范是编码细则的维护入口。

<a id="sec-4"></a>

## 四、Java 与 Python 的数据和接口边界

- 【强制】`auth/account` 与 `system/user` 使用同一个用户身份。账号状态由 `auth` 单独维护；管理员在 `system/user` 发起停用，由业务服务授权后调用 `auth` 停用账号和撤销会话。角色、菜单和数据范围按[后端授权方案](../authority/backend/user_role.md)细化。
- 【强制】Java 管任务与用户的归属，Python 管执行状态与报告。以查看报告为例：`AnalysisController` 获取当前用户，`AnalysisService` 通过 `AnalysisTaskOwnershipDao` 校验归属及数据范围，再经 `PythonAnalysisClient` 读取报告。
- 【强制】跨 Java 与 Python 的业务调用走已认证的内部接口。即使共用数据库实例，也不得跨服务读写对方管理的表。业务设置归 Java，模型和数据源凭据、运行参数及诊断归 Python。
- 【强制】客户端地址、凭据和超时均来自运行配置；区分远端业务错误、超时和不可用。远程调用不占用 Java 数据库事务。提交任务等写操作必须定义幂等与超时确认方式，再开启自动重试；详情见[远程调用规范](../../.conventions/backend/JAVA_LAYERING.md#sec-3)。

<a id="sec-5"></a>

## 五、迁移顺序与验收

1. **迁移 Python 路径。** 保留包内布局和现有行为，更新根启动脚本、CI、Docker、每日任务、桌面打包、静态资源和策略模板路径。验收现有 CLI、服务、定时任务和桌面版仍能运行；这一批可独立回退。
2. **接入根目录 Java 工程。** 先打通「登录 → 提交分析 → 查询进度 → 查看报告」。用两个用户验证列表、读取和删除权限，确认旧报告来源与可见范围，并验收超时重试不会重复创建任务。
3. **交付网页和桌面共用链路。** 验收网页版访问服务器 Java、桌面安装包启动和关闭本机 Java 与 Python，两端使用同一业务 API。随后逐项迁入业务 CRUD；每迁一项，只保留明确的数据写入方，并在移除旧入口前核对 CLI、定时任务与机器人依赖。
