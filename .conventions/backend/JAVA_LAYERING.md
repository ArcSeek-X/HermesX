# <a id="java-layering"></a>Java 后端分层与文件组织规范

> 📝 **方案简述**：约定 HermesX Java 后端的包结构、依赖方向、各层文件命名与数据边界，使网页端和桌面端复用同一套业务规则，Java 与 Python 各自维护自己的数据。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-17

## 目录

- [一、范围与依赖方向](#sec-1)
- [二、各层职责与文件命名](#sec-2)
- [三、Java 与 Python 的调用边界](#sec-3)
- [四、目录示例](#sec-4)
- [五、提交前检查](#sec-5)

<a id="sec-1"></a>

## 一、范围与依赖方向

【强制】本规范适用于根目录 Java 工程的新增代码。基础包名统一为 `hermesx`，Spring Boot 启动类为 `hermesx.HermesApiApplication`，`hermesx.auth`、`hermesx.system` 和 `hermesx.research` 位于根包下。整体目录、部署与迁移顺序见 [HermesX Java 与 Python 后端协作方案](../../documents/framework/java_python_backend_design.md)。

【强制】Java 源码位于 `src/main/java/hermesx/`，先按业务分包，例如 `auth/account`、`system/user`、`research/watchlist`，再在该业务包下按职责划分。测试位于 `src/test/java/hermesx/`，使用被测代码对应的包名。

```text
Controller → Service → DAO → Java 管理的数据
                 └───→ Client → Python 或其他远程服务
```

- 【强制】`Controller` 通过 `Service` 执行业务，不直接访问 `DAO` 或 `Client`；`DAO` 和 `Client` 不互调，也不反向依赖 `Service` 或 `Controller`。
- 【强制】跨业务模块通过对方公开的服务方法或接口调用，不直接访问对方的内部实现、`DAO` 或数据表。例如 `system/user` 调用 `auth/account` 提供的停用操作，账号状态由 `auth/account` 维护。模块之间不得循环依赖。
- 【推荐】按实际职责创建目录。仅查询远端数据的业务可以只有 `controller/`、`service/` 和 `client/`，无需创建空的 `dao/`。简单业务直接用一个 `XxxService` 类，有多个实现或确实需要稳定契约时再拆接口。

<a id="sec-2"></a>

## 二、各层职责与文件命名

| 目录 | 放什么、怎么命名 | 职责边界 |
| --- | --- | --- |
| `controller/` | `WatchlistController.java`、`AnalysisController.java` | 接收 HTTP 参数、触发格式校验、从认证上下文取得当前操作者、调用服务并组装 HTTP 响应。业务判断不写在控制器里，也不从请求体信任操作者 ID。 |
| `service/` | `WatchlistService.java`、`AnalysisService.java`；需要时可加 `CreateWatchlistCommand.java` 等用例入参类型 | 执行业务校验、操作权限与数据范围检查，编排 DAO、客户端和其他模块的公开方法。由服务定义本地事务边界。公开用例不接收 HTTP 请求或返回 HTTP 响应对象。 |
| `dao/` | `WatchlistDao.java`、`AnalysisTaskOwnershipDao.java` | 负责所属模块的数据查询和持久化。按业务授权范围建立查询条件，业务授权本身由服务判断。不得访问 Python 所管表，也不得在这里发远程请求。 |
| `client/` | `PythonAnalysisClient.java`；远程请求、响应类型放 `client/dto/`，如 `PythonAnalysisTaskResponse.java` | 处理远程协议、认证、序列化、超时和远程错误转换。只负责调用对方服务，不决定当前用户是否有权访问资源，也不写本地业务表。 |
| `dto/` | `CreateWatchlistRequest.java`、`WatchlistResponse.java` | 本模块面向前端的请求和响应结构。不得直接把数据库实体、远程响应或凭据返回给前端。 |
| `dao/entity/`（按需） | `WatchlistEntity.java`、`AnalysisTaskOwnershipEntity.java` | 存放与表结构或持久化框架绑定的类型。实体不得作为 Controller 的请求或响应。 |
| `domain/`（按需） | `Watchlist.java`、`StockSymbol.java`、`WatchlistRules.java` | 放业务模型、值对象和纯规则，不引用 HTTP、数据库或远程客户端。简单 CRUD 不要求创建领域层。 |

- 【强制】包名使用小写；Java 文件名与公开顶层类型名一致，类型名使用大驼峰。命名应体现业务和职责，例如 `CreateWatchlistRequest`，避免 `Data`、`CommonService` 等无法判断用途的名称。
- 【强制】同一模块统一数据访问入口的命名。默认使用 `XxxDao`；如选用 MyBatis，可把框架映射类型放在 `dao/mapper/` 并命名为 `XxxMapper`。Mapper 若已承担完整访问职责，服务可以在本模块直接使用它，不必再加一层只转发的 DAO。持久化工具选择不改变调用边界。
- 【推荐】转换代码放在负责该边界的位置：HTTP 类型由 Controller 转换，远程载荷由 Client 转换，持久化类型由 DAO 转换。仅在转换确有复用或复杂度时提取命名明确的转换类。

<a id="sec-3"></a>

## 三、Java 与 Python 的调用边界

- 【强制】Java 通过业务模块的 `client/` 调用 Python。调用地址、服务凭据和超时由运行配置提供，不能写死；网页部署和桌面单机版使用同一套接口，分别配置服务地址。
- 【强制】Java 根据已认证身份和任务归属判断谁能提交、查看或删除；Python 保存并维护分析执行状态和报告。Java DAO 只写 Java 所管的数据，例如任务与用户的归属关系。即使两端共用数据库实例，也不得跨服务读写对方的表。
- 【强制】Client 明确区分远端业务错误、超时和服务不可用等情况，并保留可供排查的错误语义；不能用空列表、`null` 或默认成功掩盖调用失败。仅按接口契约重试可安全重放的操作；创建任务等有副作用的调用须先具备幂等约定，才能自动重试。
- 【强制】远程调用不能加入 Java 数据库事务，不在持有数据库事务期间等待远端。若用例同时写本地归属记录和创建远程任务，设计时必须约定超时后如何确认远端是否已受理，以及失败后如何重试或对账，避免重复创建和结果脱离归属。

<a id="sec-4"></a>

## 四、目录示例

```text
src/main/java/hermesx/research/
├── watchlist/
│   ├── controller/WatchlistController.java
│   ├── service/WatchlistService.java
│   ├── dao/WatchlistDao.java
│   └── dto/
│       ├── CreateWatchlistRequest.java
│       └── WatchlistResponse.java
└── analysis/
    ├── controller/AnalysisController.java
    ├── service/AnalysisService.java
    ├── dao/AnalysisTaskOwnershipDao.java
    ├── dto/AnalysisReportResponse.java
    └── client/
        ├── PythonAnalysisClient.java
        └── dto/PythonAnalysisReportResponse.java
```

查看报告时，`AnalysisController` 取得当前用户和任务 ID；`AnalysisService` 通过 `AnalysisTaskOwnershipDao` 核对数据范围，授权通过后再调用 `PythonAnalysisClient`。远端响应在客户端适配，对外报告结构在控制器边界组装。

<a id="sec-5"></a>

## 五、提交前检查

- [ ] 所有入口统一经过所属业务的 Service，权限校验与业务规则不会因调用入口不同而被绕过。
- [ ] 跨模块只用公开服务方法，跨服务只用 Client；DAO 只处理本模块拥有的数据。
- [ ] HTTP DTO、远程 DTO 和数据库实体各自留在所属边界。
- [ ] 涉及远程调用时，检查超时、错误映射，以及有副作用操作的重试条件。
- [ ] 按实际风险验证：控制器请求与响应、服务权限和归属、复杂 DAO 查询、客户端对远程失败的处理。
