# <a id="java-engineering-architecture"></a>HermesX Java 工程架构

> 📝 **方案简述**：以 `newsee-litemdm` 的 `pojo + rest` 结构为主要参考，约定三个 Java 服务的目录、模块依赖、分层职责、文件命名及 Python 接入边界。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-18

## 目录

- [一、范围与依赖方向](#sec-1)
- [二、各层职责与文件命名](#sec-2)
- [三、Java 与 Python 的调用边界](#sec-3)
- [四、目录示例](#sec-4)
- [五、提交前检查](#sec-5)
- [六、标准依据与示例项目的取舍](#sec-6)

<a id="sec-1"></a>

## 一、范围与依赖方向

### 1.1 当前状态与目标

菜单Java接口已实现`POST /api/system/list-menu`及管理CRUD，统一module/group/page和menuCode等字段；导航排除禁用子树，管理查询保留禁用记录，page完整路径不由业务码拼接。依赖公共响应JAR及共享树工具。业务数据库、正式建表和菜单数据导入暂缓；详情见[菜单Java专题](java_menu_navigation.md)。前端隐藏祖先和旧状态过滤逻辑尚待按最新约定调整，用户级授权暂不实现。

【强制】本文描述已确认的目标：**三个 Java 服务 + 一个 Python 服务**。仓库现已建立根聚合 POM、三个服务及各自的 pojo/rest 工程骨架，其中 system 已实现独立的 SQLite 用户管理学习案例（启动类、CRUD、管理接口保护），auth 与 analysis 仍为骨架。整体方案与实施计划已同步此结构，现有 Python/Web/桌面入口未切换。

【强制】项目尚未上线，以正确的目标结构直接调整工程与开发入口。实际迁移时同批更新构建、测试、打包、调用方和文档，不为旧路径长期保留转发或重复布局。初始阶段只建立骨架；现按用户授权增加 system 用户管理案例，**不扩展 auth/analysis 业务，不切换现有 Python、Web 和桌面运行链路**。下文目录模板仍包含未来功能，实际案例文件和逐层解释见 [用户管理学习案例](java_user_management_case.md)。

| 服务目录 | Java 基础包 | 负责什么 | 不负责什么 |
| --- | --- | --- | --- |
| `hrs-auth-service/` | `hermesx.auth` | 注册、登录、凭据、账号状态、会话及身份认证 | 组织菜单管理、分析计算 |
| `hrs-system-service/` | `hermesx.system` | 用户资料、组织部门、角色、权限、菜单、数据字典、业务系统设置 | 密码和会话写入、模型与数据源运行配置 |
| `hrs-analysis-service/` | `hermesx.analysis` | 自选股与分组、最近搜索、研究偏好、分析任务归属、报告访问授权，以及 Python 分析调用编排 | 行情抓取、技术指标和 LLM 计算 |
| `python/` | 保留现有 Python 包结构和 `src` 导入名 | 行情与数据源、技术分析、新闻与 LLM 分析、执行状态和报告生成 | Java 账号、组织权限及业务数据写入 |

账号与用户资料通过稳定用户标识关联。目标架构中账号状态由 auth 维护，角色权限由 system 维护；跨服务操作通过接口协调，不能直接修改对方数据库。Java 服务是否使用同一数据库实例、具体数据库产品、认证协议和持久化框架，留待接入阶段确定。当前骨架使用 JDK 17 编译目标、Maven 3.9.9 Wrapper 和 Maven Compiler Plugin 3.14.1，system 案例引入 Spring Boot 3.5.14、MyBatis Mapper/XML 与 SQLite JDBC 3.49.1.0，其余服务不引入运行框架依赖。

**当前案例的明确例外**：为参考 scaffold 的用户表独立完成 CRUD，`hrs_system_user` 暂时包含 username、password（BCrypt 哈希）和 status。没有实现表内用户登录、会话或正式角色权限；管理 API 使用外部配置的独立管理身份。后续接入 auth 前须移交凭据及账号状态的唯一写入责任。具体字段、接口、验证和限制见 [用户管理学习案例](java_user_management_case.md)。

### 1.2 `pojo` 与 `rest` 怎么分工

`pojo` 在本项目中是“数据类型模块”的名字；`rest` 是“可运行的业务服务模块”的名字。它们是 Maven 模块，**不是两个微服务，也不是两个需要分别启动的进程**。每个 Java 服务都有自己的一组 `pojo/` 和 `rest/`。

| 对比项 | `pojo/` | `rest/` |
| --- | --- | --- |
| 大白话 | 定义数据长什么样 | 定义收到请求后怎么处理 |
| 主要内容 | `base`、`entity`、`dto`、`vo` 数据类型 | 启动类、Controller、Service、DAO、远程客户端和运行配置 |
| 登录举例 | `LoginDTO` 定义用户名与密码字段，`CurrentUserVO` 定义允许返回的用户信息 | `LoginController` 接收请求，`LoginServiceImpl` 校验登录并调用账号数据访问组件 |
| 能否单独启动 | 不提供启动入口，构建普通 JAR | 后续接入框架后构建可执行服务 JAR |
| 依赖关系 | 不依赖本服务的 rest，也不依赖其他服务实现 | 依赖本服务 pojo |
| 禁止放入 | Controller、业务服务实现、数据库访问、远程调用、服务启动配置 | 不重复声明 pojo 已定义的 Entity、业务 DTO、VO |

拆分的目的，是让数据定义和运行实现有明确边界，让编译依赖能约束职责。代价是每个服务增加两个 Maven 子模块和相应构建配置。即使 pojo 构建为独立 JAR，也**不代表允许其他微服务直接依赖其中的数据库实体**；对外以接口契约通信，不把 pojo 当全系统共享模型包。

POJO 原意是 Plain Old Java Object，指普通 Java 对象，并不天然等于“实体模块”。这里把数据类型集中放入名为 pojo 的模块，是 HermesX 参考示例项目作出的工程约定。

### 1.3 构建与代码依赖

```text
根 pom.xml（聚合三个服务、统一构建约定，不运行）
  └─ 每个服务的 pom.xml（聚合 pojo 与 rest，不运行）
       ├─ pojo（普通 JAR：数据定义）
       └─ rest（后续可执行 JAR）──依赖──→ 本服务 pojo

Controller → Service 接口 → ServiceImpl → DAO → 本服务数据
                                      └→ service/remote 中的 Client → 其他服务
```

- 【强制】根和服务级 POM 使用 `pom` packaging；pojo 与 rest 是独立子模块，artifactId 全仓唯一，例如 `hrs-auth-service-pojo`、`hrs-auth-service-rest`。
- 【强制】每个 rest 只依赖自己的 pojo，不依赖其他服务的 rest，不通过 Maven 依赖或数据库访问绕过服务边界。
- 【强制】Controller 只调用 Service，不直接访问 DAO 或远程 Client。ServiceImpl 编排业务、权限和本地事务；DAO 与 Client 不互调，不反向依赖 Controller 或 Service。
- 【强制】按照示例采用按层平铺的包结构。`controller/`、`service/` 下直接按业务命名 Java 文件，不再嵌套 `auth/`、`system/`、`research/`。
- 【强制】远程调用统一放 `service/remote/`；原方案的 `client/` 不再作为目标目录。它虽然位于 service 路径内，职责仍是远程适配，不承担本地业务决策。

<a id="sec-2"></a>

## 二、各层职责与文件命名

### 2.1 Maven 目录和 Java 包路径

以下路径均相对于仓库根；`<服务>` 为上述三个 Java 服务目录之一，`<业务包>` 为 `auth`、`system` 或 `analysis`。

| 目录或文件 | 用途与内容 |
| --- | --- |
| 根 `pom.xml` | 聚合三个服务并统一版本、构建插件等约定；不聚合 Python/npm 工程 |
| `mvnw`、`mvnw.cmd`、`.mvn/wrapper/` | Maven Wrapper：分别供 Unix/macOS、Windows 使用仓库约定的 Maven；不是 Java 业务代码 |
| `<服务>/pom.xml` | 聚合该服务的 pojo 与 rest |
| `<服务>/pojo/pom.xml` | 声明数据类型模块的标识及必要依赖，不引入服务启动和数据库连接能力 |
| `<服务>/rest/pom.xml` | 声明本服务 pojo、运行框架、数据库驱动与测试等所需依赖；具体依赖在实施时选择 |
| `src/main/java/` | 每个子模块的生产 Java 源码根目录；不是包名 |
| `java/hermesx/<业务包>/` | 源码根下的 Java 包路径，例如 `hermesx.auth`，继续往下的 `vo` 对应 `hermesx.auth.vo` |
| `src/main/resources/` | 配置、SQL 映射等非 Java 运行资源 |
| `src/test/java/` | 测试 Java 文件，包路径对应被测源码 |
| `src/test/resources/` | 测试配置、固定输入及数据库测试夹具，不放真实密钥和用户数据 |
| 各模块 `target/` | Maven 生成的类文件、测试结果与 JAR；构建产物不提交 Git |

`hrs-auth-service/pojo/src/main/java/hermesx/auth/vo/` **里面放 `.java` 文件**。例如 `CurrentUserVO.java` 中声明 `package hermesx.auth.vo;`，公开类型名为 `CurrentUserVO`。目录名 `hrs-auth-service` 是工程名称，不是 Java 包名，不加进 `package`，也不用给包名增加 `service` 后缀。

### 2.2 pojo 模块：数据类型

| 包目录 | 职责及允许内容 | 文件命名与示例 | 不应放什么 |
| --- | --- | --- | --- |
| `base/` | 本服务内确有共性的基础数据类型，例如审计字段、分页输入和结果结构 | `BaseEntity.java`、`PageQueryDTO.java`、`PageVO.java` | 通用业务服务、数据库连接；不为凑层次强制所有类型继承同一个基类 |
| `entity/` | 本服务拥有的持久化数据结构，可按所选框架加映射注解 | `业务名Entity.java`：`AccountEntity.java`、`UserProfileEntity.java`、`WatchlistEntity.java` | HTTP 请求处理、远程调用；不直接作为前端入参或响应 |
| `dto/` | 本服务接口输入与业务数据传递类型，按具体操作限制字段，可带声明式格式校验 | `动作+业务名DTO.java` 或 `业务名+用途DTO.java`：`LoginDTO.java`、`CreateUserDTO.java`、`UpdateRoleDTO.java`、`WatchlistQueryDTO.java` | 密码校验实现、SQL、会话读写；不接受客户端指定可信操作者身份 |
| `vo/` | 本项目 VO 指 View Object：明确允许返回给前端的视图数据，可由多种来源组装 | `业务名VO.java`：`CurrentUserVO.java`、`MenuTreeVO.java`、`WatchlistVO.java`、`AnalysisReportVO.java` | 密码散列、内部凭据、未经筛选的 Entity 或远程完整响应 |

【强制】DTO、Entity、VO 职责分开，不用一个“万能 User”贯穿所有边界。VO 在本规范中不表示领域驱动设计中的 Value Object。DTO 可以包含登录所需密码，但不得被日志直接输出；响应 VO 不返回密码或密码散列。客户端提交的用户 ID 等业务目标字段，仍需服务端授权校验。

【推荐】基础类型只在真正复用时建立。审计字段应由服务端赋值，不因为 DTO 继承 BaseEntity 就允许用户修改创建人、账号状态等内部字段。pojo 可包含必要的校验和映射注解，但不进行 IO，也不装配运行服务。

### 2.3 rest 模块：业务处理与运行

| 包目录 | 职责 | 文件命名与示例 | 约束 |
| --- | --- | --- | --- |
| 基础包根 | 服务启动与组件扫描入口 | `AuthApplication.java`、`SystemApplication.java`、`AnalysisApplication.java` | 放在各自基础包下，避免扫描其他服务的实现 |
| `controller/` | 接收 HTTP 请求、触发参数格式校验、取认证上下文、调用 Service、返回 VO | `业务名Controller.java`：`LoginController.java`、`UserController.java`、`WatchlistController.java` | 不写 SQL、不直调 Client、不在这里集中实现业务权限 |
| `service/` | 声明本服务的业务能力、输入输出和业务契约 | `I业务名Service.java`：`ILoginService.java`、`IUserService.java`、`IWatchlistService.java` | 不接收 HttpServletRequest，不返回 HTTP 响应对象；`I` 前缀为本项目约定 |
| `service/impl/` | 实现业务规则、数据权限、业务编排及本地事务边界 | `业务名ServiceImpl.java`：`LoginServiceImpl.java`、`UserServiceImpl.java`、`WatchlistServiceImpl.java` | 实现对应接口；写操作的归属与权限不能只依靠 Controller 检查 |
| `service/remote/` | 适配其他 Java 服务或 Python 的接口、认证、序列化、超时与远程错误 | `目标或能力名Client.java`：`AuthClient.java`、`SystemPermissionClient.java`、`PythonAnalysisClient.java` | 不写本地业务表，不决定当前用户是否有权访问本地资源；不强制选择 Feign |
| `service/remote/dto/` | 保存本服务消费的远端协议结构 | `目标+操作+Request/Response.java`：`PythonSubmitAnalysisRequest.java`、`PythonTaskStatusResponse.java` | 与 pojo 的前端 DTO/VO 分开，不直接向前端透传 |
| `dao/` | 读取、更新本服务拥有的数据，负责查询条件与持久化映射 | 采用 MyBatis 时 `业务名Mapper.java`：`AccountMapper.java`、`UserProfileMapper.java`、`WatchlistMapper.java` | 不跨服务访问数据，不发 HTTP 请求；若选其他框架统一使用对应 `Dao` 或 `Repository` 命名，不叠加纯转发层 |
| `config/` | 框架装配、HTTP 客户端、持久化及参数绑定配置 | `用途Config.java`、`用途Properties.java`：`WebConfig.java`、`PythonAnalysisProperties.java` | 不硬编码地址、密钥、端口、环境分支；不夹带业务处理 |
| `security/` | 认证上下文、凭据验证接线、身份和授权机制适配 | `CurrentUser.java`、`AuthenticationFilter.java` | 不替代 Service 中针对具体数据的权限校验；不默认指定 JWT 等技术方案 |
| `exception/` | 明确业务异常、错误代码及全局 HTTP 异常映射 | `业务名Exception.java`、`ErrorCode.java`、`GlobalExceptionHandler.java` | 不吞掉异常返回默认成功，不泄露堆栈或敏感信息给前端 |
| `interceptor/`（按需） | Web 请求级拦截，例如请求跟踪；Filter 也可在此归置 | `用途Interceptor.java`、`用途Filter.java`：`RequestTraceInterceptor.java` | 不把业务服务塞进拦截器，不与 security 重复实现认证 |
| `utils/`（按需） | 小范围可复用的纯工具 | `用途Utils.java`：`StockCodeUtils.java` | 不存放 Service、DAO、远程 Client 或隐式读会话/数据库的万能工具 |

文件后缀体现职责，包内按业务文件名分类，不再建立 `controller/auth/`、`service/system/` 等子包。目录树中的按需目录仅在有实际职责时创建，不能用空实现增加层数。

### 2.4 resources 与测试文件

| 路径 | 内容 | 命名与约束 |
| --- | --- | --- |
| `rest/src/main/resources/application.yml` | 服务运行配置和外部配置占位引用 | 不放真实密钥；新配置同步脱敏 `.env.example` 与文档 |
| `rest/src/main/resources/mapper/`（如采用 MyBatis XML） | DAO 映射对应的 SQL XML | `WatchlistMapper.xml` 对应 `WatchlistMapper.java`，namespace 为完整 Mapper 类型名，语句 ID 对应方法名 |
| `rest/src/main/resources/db/migration/`（如采用 Flyway） | 本服务拥有的数据结构迁移 | 例如 `V1__create_watchlist.sql`；版本唯一；不迁移其他服务的表；迁移工具尚未选定 |
| `pojo/src/test/java/hermesx/<业务包>/` | 必要的数据类型约束测试 | `LoginDTOTest.java`；不为纯 getter/setter 增加镜像测试 |
| `rest/src/test/java/hermesx/<业务包>/` | Controller 契约、Service 规则、DAO 查询与远程失败路径验证 | `WatchlistControllerTest.java`、`WatchlistServiceImplTest.java`、`PythonAnalysisClientTest.java`；对应生产包 |
| `rest/src/test/resources/` | 测试配置与夹具 | 例如 `application-test.yml`，不能默认连接真实生产或个人数据库 |

### 2.5 命名与对象转换

- 【强制】包名全小写；公开顶层类型名与 `.java` 文件名相同，使用大驼峰；方法和字段使用小驼峰，常量使用大写下划线，例如 `MAX_PAGE_SIZE`。
- 【强制】本项目业务输入统一 DTO 后缀，前端输出统一 VO 后缀；远程协议类型使用 Request/Response 后缀。实体统一 Entity 后缀，避免同一职责多套叫法。
- 【强制】Controller 依赖 Service 接口；Impl 实现接口；DAO 仅负责本服务数据；跨服务由 ServiceImpl 调用 Client。基础类和工具不得成为越层捷径。
- 【推荐】前端协议转换位于 HTTP 边界，远端协议转换位于 Client 边界，实体与业务数据转换由业务服务或明确的转换组件完成。复杂且复用时再提取转换类，不为每个字段拷贝增加一层。

例如新增自选股：`CreateWatchlistDTO → WatchlistController → IWatchlistService / WatchlistServiceImpl → WatchlistMapper → 本服务数据`。实现类从认证上下文取得可信操作者，检查股票与分组约束，组装 `WatchlistEntity` 落库，再形成 `WatchlistVO`；不能接受前端指定其他用户后直接写入。

<a id="sec-3"></a>

## 三、Java 与 Python 的调用边界

- 【强制】分析业务由 `hrs-analysis-service` 的 ServiceImpl 经 `service/remote/PythonAnalysisClient.java` 调用 Python。Java 与 Python 通过接口契约通信，不相互导入源码，也不直接操作对方表。
- 【强制】Java 校验已认证身份、权限及任务归属；Python 维护执行状态与报告内容。即使共享数据库实例，各服务仍只写自己管理的数据。
- 【强制】地址、服务凭据和超时从运行配置提供；网页和桌面复用相同业务接口，服务器部署与本地运行通过配置区分。本文不要求当前桌面立即启动三个 Java 服务。
- 【强制】Client 区分远端业务错误、超时和服务不可用，不以空列表、null 或默认成功掩盖失败。仅对可安全重放的操作重试；提交任务等写操作先确定幂等键与超时后的受理确认方式。
- 【强制】本地数据库事务不覆盖远程请求，不在持有数据库事务时等待远端。任务归属记录与 Python 任务创建的顺序、失败补偿和对账须在实现前明确，不宣称跨进程自动原子提交。
- 【强制】system 管业务系统设置；模型、数据源凭据、分析参数和运行诊断仍由 Python 的现有配置机制维护，不为迁目录复制一份配置真源。

查看报告示例：`AnalysisController → IAnalysisService / AnalysisServiceImpl → AnalysisTaskOwnershipMapper` 校验归属，通过后调用 `PythonAnalysisClient` 获取报告，转换为 `AnalysisReportVO` 返回。

Python 内部分层与数据源规则见 [Python 工程架构](python_engineering_architecture.md)。

<a id="sec-4"></a>

## 四、目录示例

未实现的服务仍以 `.gitkeep` 保存包目录，配置为注释占位；system 已有可运行用户管理案例，使用 `dao/UserMapper.java` 与 `resources/mapper/UserMapper.xml`。原根目录的用户空文件 `test.java` 已原样迁至 auth 服务 rest 的对应包下，不属于新实现。以下是目标全仓关系及三个服务的完整层级模板。文件是命名示例；尚未授权的功能不要求实现这些 Java 类。`mapper/`、`db/migration/` 等依具体技术选型创建。

```text
HermesX/
├── pom.xml                                  # 聚合三个 Java 服务
├── mvnw / mvnw.cmd                          # Maven Wrapper 入口
├── .mvn/wrapper/                            # Wrapper 版本与下载配置
├── hrs-auth-service/
│   ├── pom.xml                              # 聚合本服务 pojo、rest
│   ├── pojo/
│   │   ├── pom.xml                          # hrs-auth-service-pojo
│   │   └── src/
│   │       ├── main/java/hermesx/auth/
│   │       │   ├── base/BaseEntity.java
│   │       │   ├── entity/AccountEntity.java
│   │       │   ├── dto/LoginDTO.java
│   │       │   ├── dto/RegisterDTO.java
│   │       │   └── vo/CurrentUserVO.java
│   │       └── test/java/hermesx/auth/
│   └── rest/
│       ├── pom.xml                          # hrs-auth-service-rest
│       └── src/
│           ├── main/
│           │   ├── java/hermesx/auth/
│           │   │   ├── AuthApplication.java
│           │   │   ├── controller/LoginController.java
│           │   │   ├── controller/RegistrationController.java
│           │   │   ├── service/ILoginService.java
│           │   │   ├── service/IRegistrationService.java
│           │   │   ├── service/impl/LoginServiceImpl.java
│           │   │   ├── service/impl/RegistrationServiceImpl.java
│           │   │   ├── service/remote/SystemPermissionClient.java
│           │   │   ├── service/remote/dto/SystemPermissionResponse.java
│           │   │   ├── dao/AccountMapper.java
│           │   │   ├── config/WebConfig.java
│           │   │   ├── security/CurrentUser.java
│           │   │   ├── exception/GlobalExceptionHandler.java
│           │   │   ├── interceptor/                # 按需
│           │   │   └── utils/                      # 按需
│           │   └── resources/
│           │       ├── application.yml
│           │       └── mapper/AccountMapper.xml
│           └── test/
│               ├── java/hermesx/auth/
│               └── resources/
├── hrs-system-service/
│   ├── pom.xml
│   ├── pojo/
│   │   ├── pom.xml                          # hrs-system-service-pojo
│   │   └── src/
│   │       ├── main/java/hermesx/system/
│   │       │   ├── base/BaseEntity.java
│   │       │   ├── entity/UserProfileEntity.java
│   │       │   ├── entity/DepartmentEntity.java
│   │       │   ├── entity/RoleEntity.java
│   │       │   ├── entity/MenuEntity.java
│   │       │   ├── entity/DictionaryEntryEntity.java
│   │       │   ├── entity/SystemSettingEntity.java
│   │       │   ├── dto/CreateUserDTO.java
│   │       │   ├── dto/UpdateRoleDTO.java
│   │       │   ├── vo/UserProfileVO.java
│   │       │   └── vo/MenuTreeVO.java
│   │       └── test/java/hermesx/system/
│   └── rest/
│       ├── pom.xml                          # hrs-system-service-rest
│       └── src/
│           ├── main/
│           │   ├── java/hermesx/system/
│           │   │   ├── SystemApplication.java
│           │   │   ├── controller/              # UserController、DepartmentController、
│           │   │   │                            # RoleController、PermissionController、
│           │   │   │                            # MenuController、DictionaryController、SettingsController
│           │   │   ├── service/                 # IUserService、IDepartmentService 等接口
│           │   │   │   ├── impl/                # UserServiceImpl 等实现
│           │   │   │   └── remote/
│           │   │   │       ├── AuthClient.java
│           │   │   │       └── dto/AuthAccountStatusResponse.java
│           │   │   ├── dao/UserProfileMapper.java
│           │   │   ├── config/
│           │   │   ├── security/
│           │   │   ├── exception/
│           │   │   ├── interceptor/             # 按需
│           │   │   └── utils/                   # 按需
│           │   └── resources/
│           │       ├── application.yml
│           │       └── mapper/UserProfileMapper.xml
│           └── test/
│               ├── java/hermesx/system/
│               └── resources/
├── hrs-analysis-service/
│   ├── pom.xml
│   ├── pojo/
│   │   ├── pom.xml                          # hrs-analysis-service-pojo
│   │   └── src/
│   │       ├── main/java/hermesx/analysis/
│   │       │   ├── base/BaseEntity.java
│   │       │   ├── entity/WatchlistEntity.java
│   │       │   ├── entity/AnalysisTaskOwnershipEntity.java
│   │       │   ├── dto/CreateWatchlistDTO.java
│   │       │   ├── dto/SubmitAnalysisDTO.java
│   │       │   ├── vo/WatchlistVO.java
│   │       │   └── vo/AnalysisReportVO.java
│   │       └── test/java/hermesx/analysis/
│   └── rest/
│       ├── pom.xml                          # hrs-analysis-service-rest
│       └── src/
│           ├── main/
│           │   ├── java/hermesx/analysis/
│           │   │   ├── AnalysisApplication.java
│           │   │   ├── controller/WatchlistController.java
│           │   │   ├── controller/AnalysisController.java
│           │   │   ├── service/IWatchlistService.java
│           │   │   ├── service/IAnalysisService.java
│           │   │   ├── service/impl/WatchlistServiceImpl.java
│           │   │   ├── service/impl/AnalysisServiceImpl.java
│           │   │   ├── service/remote/
│           │   │   │   ├── PythonAnalysisClient.java
│           │   │   │   ├── SystemPermissionClient.java
│           │   │   │   └── dto/
│           │   │   │       ├── PythonSubmitAnalysisRequest.java
│           │   │   │       └── PythonTaskStatusResponse.java
│           │   │   ├── dao/WatchlistMapper.java
│           │   │   ├── dao/AnalysisTaskOwnershipMapper.java
│           │   │   ├── config/PythonAnalysisProperties.java
│           │   │   ├── security/
│           │   │   ├── exception/
│           │   │   ├── interceptor/             # 按需
│           │   │   └── utils/                   # 按需
│           │   └── resources/
│           │       ├── application.yml
│           │       └── mapper/
│           │           ├── WatchlistMapper.xml
│           │           └── AnalysisTaskOwnershipMapper.xml
│           └── test/
│               ├── java/hermesx/analysis/
│               └── resources/
├── python/                                  # 一个 Python 分析服务，保留内部现有结构
├── apps/
│   ├── hrs-web/                             # Web 前端
│   └── hrs-desktop/                         # Electron 桌面应用
├── docker/                                  # 容器部署定义
├── scripts/                                 # 开发、验证和构建脚本
├── .github/                                 # 工作流与协作配置
└── documents/engineering/                   # 整体、Java、Python 方案和实施计划
```

各服务的配置、测试与工具目录遵循第二节相同规则；示例未穷举全部 CRUD 文件。Web 与桌面是客户端，既不依赖 Java pojo JAR，也不直接访问 Java 数据库。

<a id="sec-5"></a>

## 五、提交前检查

- [ ] 区分已存在骨架和目标目录，文档不将规划描述成已上线能力。
- [ ] 根 POM 聚合三个服务，服务 POM 聚合自己的 pojo/rest，artifactId 唯一，rest 只依赖自己的 pojo。
- [ ] Java 包名分别为 `hermesx.auth`、`hermesx.system`、`hermesx.analysis`，文件位置与声明一致。
- [ ] 各层按业务文件名区分，没有重新引入层内 auth/system/research 分类。
- [ ] Controller → Service → DAO 与 Service → remote Client 边界成立，数据权限不会因换入口被绕过。
- [ ] DTO、VO、Entity 和远程协议类型各守边界；账号、权限和任务数据只有明确写入方。
- [ ] 远程超时、错误、幂等和补偿方式明确，不把远程请求包含在本地数据库事务中。
- [ ] 技术选型确定后才引入框架与驱动，未照搬参考项目私服、注册中心和中间件依赖。
- [ ] 按实际改动验证构建与相关业务路径；仅文档修改无需运行 Java/Python 业务测试。
- [ ] 实际骨架迁移时同步整体方案、实施计划和构建入口，不覆盖已有用户文件。

<a id="sec-6"></a>

## 六、标准依据与示例项目的取舍

**`pojo + rest` 是本项目采用的结构，不是 Java 行业强制标准。** [Maven 标准目录说明](https://maven.apache.org/guides/introduction/introduction-to-the-standard-directory-layout.html)约定默认源码、资源与测试路径；[Spring Boot 代码结构说明](https://docs.spring.io/spring-boot/reference/using/structuring-your-code.html)不要求唯一的代码布局。不要把 Maven 的 `src/main/java` 惯例与本项目的模块名字混为一谈。

| 参考项目中的结构 | HermesX 采用的做法 |
| --- | --- |
| 根 POM 聚合 `newsee-litemdm-pojo` 与 `newsee-litemdm-rest` | 在三个服务中分别聚合 `pojo/`、`rest/`，根 POM 再聚合三个服务 |
| pojo 内的 `base/entity/dto/vo` | 保留职责划分，统一 Entity、DTO、VO 命名后缀 |
| rest 内的 `controller/service/impl/remote/dao` | 保留层级，以业务文件名分类；远程组件统一 Client 后缀 |
| `IMaterialMasterDataService` 与 `MaterialMasterDataServiceImpl` | 采用 `I业务名Service` 与 `业务名ServiceImpl` 配对 |
| `MaterialMasterDataMapper.java` 与同名 XML | 如采用 MyBatis，沿用 Mapper 与 XML 对应规则 |
| 私有父 POM、私服以及各类中间件配置 | 不照搬；根据 HermesX 运行和桌面打包需求单独选型 |

参考项目存在 Controller 直调远程服务、业务方法使用 HTTP 请求对象等写法。HermesX 借鉴目录组织，不将这些写法作为规范。成熟工程的关键是职责清楚、依赖可控、数据边界明确和构建可验证，而不是必须把模块命名为 pojo 或 rest。
