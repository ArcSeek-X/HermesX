# HermesX 工程架构图册 V2

**入口：[打开交互图册](index.html)。** 图册包含系统、前端、后端总图，以及路由、页面、主题、分析、Agent、行情、持久化、报告通知、运行支撑和桌面端专题。统一入口提供视图切换、节点搜索、职责卡片、源码符号与行号、静态导入、关系登记和完整路由页面清单。每张 Archify 图也可独立打开。

分析日期：2026-11-04。基线为本地 HEAD `bcab0218613d8985600a66ac1b9857931a8b312c` **加当时未提交的工作树内容**；单独检出该提交不能复现全部源码证据。当前目录记录 13 个视图、180 个分层节点、812 个关联源码文件、40 个 `MENU_MANIFEST` 页面入口。节点按视图计数，同一模块可以出现在总图与专题中；关联文件按路径去重。

## 视图导航

建议先看系统运行全景，再从前端或后端总图进入专题。独立图支持 Archify 的搜索、聚焦、路径探索、深浅主题与导出；图册中的“展开图面”和“独立查看”用于阅读较密集的总图。

| 编号 | 视图 | 要回答的问题 |
| --- | --- | --- |
| 01 | [系统运行全景与边界](system.html) | 浏览器、Electron、Python、Bot、进程内任务、存储与外部服务分别在哪里运行？ |
| 02 | [前端完整分层与功能组织](frontend.html) | 应用、模块、页面、业务组件、基础组件如何组合，状态与协议由谁负责？ |
| 03 | [后端完整职责与业务域](backend.html) | 驱动、领域、应用、就近端口、基础设施、装配与配置如何分治？ |
| 04 | [前端启动、鉴权与动态路由](routes.html) | 登录、首屏恢复、菜单加工、路由注入和页面缓存如何衔接？ |
| 05 | [功能页面与业务组件对应](pages.html) | 行情、资讯、智能分析、交易、选股与系统功能分别由哪些页面承载？ |
| 06 | [主题、样式、参数与缓存](theme.html) | 视觉参数、组件属性、查询参数及各类缓存分别归谁管理？ |
| 07 | [个股分析与结果交付链](analysis.html) | 任务如何取数、构建上下文、分析、保存结果并生成报告？ |
| 08 | [Agent 内部编排、工具与生成](agent.html) | 会话、阶段预算、专长 Agent、技能策略、工具、模型后端与最终解释如何配合？ |
| 09 | [行情能力、数据源与降级](quote.html) | 两类行情 Manager 有何区别，StockDB 与 StockSDK 如何接入？ |
| 10 | [业务持久化、模型与存储契约](persistence.html) | Repository、ORM、DatabaseManager、Session 与 SQLite 各承担什么职责？ |
| 11 | [报告、通知与 Bot 闭环](delivery.html) | 内容、格式、接收方、渠道、来源会话回复与投递诊断如何分离？ |
| 12 | [交易、风险、任务与配置支撑](control.html) | 决策、持仓、告警、回测、调度、诊断、运行配置与认证如何协作？ |
| 13 | [Electron 启动与本地运行边界](desktop.html) | 主进程、preload、Web 渲染进程与 Python 后端如何启动和通信？ |

## 图的语义与阅读边界

总图中的区域框表示职责归组，不自动表示部署单元、进程或网络隔离区。框中多个实现可能按配置择一启用，也可能只在特定入口或任务中使用。图表库、React 组件、Python 端口和领域规则均不应理解为独立网络服务。

| 关系 | 含义 | 阅读约束 |
| --- | --- | --- |
| 组织与组合 | 应用包含模块、模块组织页面、页面组合组件 | 不保证每层都对应独立目录、独立包或强制封装层 |
| 代码依赖 | 一层使用另一层的类型、规则或公开契约 | 直接导入可在源码卡片核对；归组边不等于每个成员都互相 import |
| 运行调用与数据流 | 输入、取数、生成、保存、投递与事件消费 | 总图允许省略中间函数和返回方向；协议以边标签及源码为准 |
| 装配 | bootstrap 将适配器或工厂注入应用端口 | 不是每次业务请求都重复执行的步骤 |
| 用户功能衔接 | 从行情、选股进入研究、决策或持仓观察 | 不证明页面互相 import、自动导航或存在自动交易链路 |

支持性细节收进职责与源码卡片。页面可直接使用基础组件、Hook 或 API；主题作用于整个组件树；应用用例可分别消费仓储、行情、生成和通知端口。省略重复边，不改变这些实际关系。

## 前端契约

`apps/hrs-web/src/main.tsx` 引导鉴权并挂载 React，最外层是 ThemeProvider；`App.tsx` 装配 UiLanguage → AppMode → PageState → RouterProvider 与全局 Toast。鉴权状态在 AuthStore，导航守卫在路由 loader；旧版 AuthProvider 链不适用于当前实现。

`router/manifest.ts` 的 `MENU_MANIFEST` 定义产品与开发模式。MenuStore 加工菜单，RouterStore 持久化异步路由数据；asyncRouteFactory 构建页面路由，routeRegistration 注册或卸载业务子树。刷新种子与登录后动态注册是不同环节。登录、404 和兜底在 appRouter 固定定义，不计入提取的 40 个 manifest 页面。

功能页面覆盖首页、自选、K线、本地行情、大盘、板块、涨跌停、新闻、财经日历、Agent 对话、决策信号、持仓、复盘、回测、告警、扫描、尾盘选股、AlphaSift、用量、设置，以及开发组件文档和 CodeTest。具体组件既有 `components/` 下的共享业务组件，也有页面内的局部组合；“模块”是导航与功能组织，不是独立微前端。

Props / callback 连接父子组件，URL 与路由定位页面，Store / Context 管理不同作用域的状态，Hook 管取数与交互生命周期，API 模块处理请求与 DTO 映射。Axios JSON 请求带 Cookie 并使用 GET 内存缓存；Agent 流式请求有 fetch 等专门入口，不将全部 SSE 归入 Axios。

主题真源是 `stores/themeStore.ts`，模式、主色、侧栏主题统一保存于 `hrs-pref-theme`。ThemeProvider / ThemeSync 桥接 next-themes、DOM class 与 CSS 变量；`style/index.css` 汇入 Tailwind、HeroUI、palette、hsl-inline 和 global.scss，局部样式补充具体表现。KeepAlive 页面缓存、GET TTL/LRU 内存缓存、localStorage 持久状态和服务端数据缓存是不同机制。

## 后端、运行时与数据边界

后端以当前 `domain / application / infrastructure / bootstrap / config` 结构解释：domain 放纯模型与规则，application 按业务域组织用例，infrastructure 承接 IO，bootstrap 装配能力与生命周期，config 提供运行值及字段元数据。`src/utils` 是保留的共享辅助。

**端口按消费域就近定义。** 当前规则不要求创建集中的 `src/application/ports/`；例如分析的 `stock_data_port.py`、`persistence_port.py`、Agent 的 `llm_ports.py` 和持仓的 `ports.py`。端口是进程内契约，适配器由 bootstrap 注入。分析取数与持久化的必需能力漏装配会显式失败，不能解释为“任何错误都返回空值”。

`api/`、CLI 和 `bot/` 是驱动入口；不应假设所有启动都经过 main.py。ASGI lifespan 管理装配与调度资源，runtime 的进程内队列、线程与 worker 不构成独立消息队列或分布式任务集群。Electron 主进程管理 Python 后端与窗口，Web 渲染端复用同一前端，preload 提供受控桌面接口。

| 边界 | 当前源码事实 |
| --- | --- |
| 业务数据库 | `Config.get_db_url()` 实际返回 SQLite URL；路径来自配置。保留其它后端条件分支不代表已经支持或验收 |
| 业务仓储 | `src/infrastructure/persistence/repositories/` 按域组织，models 定义 ORM，session 管连接、事务和锁冲突重试 |
| DatabaseManager | `src/storage.py` 保留薄门面与生命周期职责，模型与引擎已有独立落点 |
| StockDB | `data_provider/stockdb_fetcher.py` 是本地 HTTP 只读客户端；源数据库由 StockDB 服务进程持有，HermesX 不直接打开源文件 |
| StockSDK | `stocksdk_bridge.py` 按请求通过 `subprocess.run` 调用 Node 桥接并设置超时，不是新增的常驻微服务 |
| 行情获取 | 能力型 Source Manager 与分析 DataFetcherManager 并存；三类基础能力的优先级规则不自动适用于全部新闻、板块和旧 Fetcher |
| TTL 与持久化 | StockDaily 是 HermesX 本地日线缓存例外；外部 API 缓存原则不禁止保存分析历史、决策、报告等业务结果 |
| 保留落点 | `src/auth.py`、`src/storage.py`、`src/brokers/futu/portfolio.py` 实际存在，目标文档的候选目录不代表已全部迁移 |

模型服务、搜索、市场数据、消息通道与经纪商均按配置启用。架构图描述实现位置与能力范围，不表示配置已启用、网络可达或线上调用成功。Bot 入站平台、通知出站渠道与源会话回复的覆盖范围也不同。

## 源码证据与维护方式

| 文件 | 用途 |
| --- | --- |
| [index.html](index.html) | 图册导航、职责卡片、源码核对与页面目录；内嵌目录数据，可在本地直接打开 |
| `*.html` | 13 张独立 Archify 交互架构图 |
| `*.json`（图名对应） | 各图类型化规格：节点、坐标、边、归组与图内卡片 |
| [architecture-catalog.json](architecture-catalog.json) | 视图、职责、关系、页面、源码摘要、公开符号、行号、静态导入与文件 SHA-256 |
| [source-map.json](source-map.json) | 节点到源码范围和文件的映射 |
| `*.receipt.json` | 绑定规格与 HTML SHA-256、字节数及确定性检查结果的 Archify 交付回执 |
| [validation.md](validation.md) | 本次验证状态与临时浏览器证据位置；以该记录说明的范围为准 |

源码证据包含静态提取结果：Python 使用语法树提取公开定义和导入，前端文件提取导出与导入文本。**812 个关联文件不表示对全部文件进行了逐行人工审计。** 动态导入、反射、工厂装配、条件执行与跨函数调用不能仅凭清单完整还原；静态导入也不能直接证明运行时可达。主要职责与接线结合入口代码、关键实现和文档分析，证据用于核对与进一步追踪。

文件 SHA-256 对应提取时的工作树字节；行号和符号可能随后续代码改动漂移。维护时应同时更新图规格、目录、映射和图册内嵌数据，再重新生成受影响图的回执。不要将旧图的回执或截图用于证明新图通过验证。

## 参考文档

- [架构目标与依赖约束](../framework/refactoring/ARCHITECTURE_TARGET.md)
- [架构迁移当前状态](../framework/refactoring/ARCHITECTURE_MIGRATION_STATUS.md)
- [后端架构 ADR](../framework/backend_architecture_adr.md)
- [前端模块与菜单](../authority/frontend_module_menu.md)
- [前端异步路由](../authority/frontend_async_router.md)
- [前端路由缓存](../authority/frontend_route_keepalive.md)
- [主题说明](../theme/theme.md)
- [Agent 流式事件](../../docs/agent-stream-events.md)
- [决策信号](../../docs/decision-signals.md)
- [通知说明](../../docs/notifications.md)

ADR 的四层业务职责视角与后续五层代码依赖视角分别解释。文档出现目标目录、历史落点或旧接口时，以当前可执行代码与专项权威规则核对；本图册不修改原始迁移历史。新增图册与说明使用中文，当前没有对应英文页需要同步。

## 验证范围、风险与回滚

图册为文档产物，未改变应用业务逻辑。已核对本说明引用的主要目录、文件与实际实现；确定性图检查、浏览器布局及图册交互的最终状态分别记录在 [validation.md](validation.md)，不能互相替代。

Docs only, application tests not run。未执行行情、LLM、搜索、通知、经纪商在线验证，也未执行应用端到端、Docker 或桌面安装包验收。主要维护风险是工作树继续变化导致职责、行号或摘要过时，以及把归组关系误读为直接调用或已部署拓扑。

回滚仅涉及本任务新增 `documents/archify-V2/` 图册产物及 `documents/CHANGELOG.md` 中对应的一条记录。若目录之后已有其他人的修改，应逐项核对后回退本次内容；不回退仓库原有未提交改动，不操作业务数据库、凭据和运行文件。
