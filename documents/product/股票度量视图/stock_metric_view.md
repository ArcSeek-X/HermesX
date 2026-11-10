# <a id="sec-0"></a>股票度量视图 · 全市场查询与筛选 · 实现方案

> 📝 **方案简述**：在 `/stock/stockMetricView` 建设「股票度量视图」，覆盖 cn / hk / us 三市场的全市场查询与筛选能力。核心契约：**前后端词根统一为 `metric`（见 §2.3）**、**表格列在前端静态定义**、**市场与其它筛选条件统一放进 `filterList` 数组**、**列表行字段平铺**、**股票字段与类型全链路统一（`types/stock.ts` 单一真源 + 适配层边界，见 §5.4）**、**卡片容器统一用 `AnimCard`**。本方案定义最终交付形态与落地规格：列头与接口出入参、数据表与跑批、四层前端分层、字段与类型约束、验证与回滚。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-07

<a id="sec-toc"></a>

## 目录

- [1. 结论摘要](#sec-1)
- [2. 命名规范](#sec-2)
  - [2.1 命名规定](#sec-2-1)
  - [2.2 命名映射表](#sec-2-2)
  - [2.3 词根统一规则（全局强制）](#sec-2-3)
- [3. 目标、非目标与验收标准](#sec-3)
  - [3.1 目标与非目标](#sec-3-1)
  - [3.2 验收标准](#sec-3-2)
- [4. 实现基线与可复用资产](#sec-4)
  - [4.1 数据来源与可得性](#sec-4-1)
  - [4.2 前端可复用资产](#sec-4-2)
  - [4.3 持久化与调度约定](#sec-4-3)
- [5. 总体架构](#sec-5)
  - [5.1 数据流](#sec-5-1)
  - [5.2 职责切分](#sec-5-2)
  - [5.3 字段映射](#sec-5-3)
  - [5.4 字段与类型统一规则（全局强制）](#sec-5-4)
- [6. 数据库设计](#sec-6)
  - [6.1 表清单](#sec-6-1)
  - [6.2 `stock_metric_period` 字段清单](#sec-6-2)
  - [6.3 `stock_metric_daily` 字段清单](#sec-6-3)
  - [6.4 `stock_metric_calc_run` 字段清单](#sec-6-4)
  - [6.5 主键、索引与 DDL](#sec-6-5)
  - [6.6 字段约定（强制项）](#sec-6-6)
  - [6.7 容量、幂等与保留](#sec-6-7)
- [7. 接口与列定义](#sec-7)
  - [7.1 接口清单](#sec-7-1)
  - [7.2 前端列定义与列头清单](#sec-7-2)
  - [7.3 `POST /api/v1/stock-metric/query`](#sec-7-3)
  - [7.4 `POST /api/v1/stock-metric/export`](#sec-7-4)
  - [7.5 通用契约与错误响应](#sec-7-5)
  - [7.6 复用接口与内部上游](#sec-7-6)
- [8. 前端实现方案](#sec-8)
  - [8.1 分层规定](#sec-8-1)
  - [8.2 文件清单](#sec-8-2)
  - [8.3 页面布局](#sec-8-3)
  - [8.4 组件清单](#sec-8-4)
  - [8.5 `useStockMetricView` 契约](#sec-8-5)
  - [8.6 交互规则](#sec-8-6)
  - [8.7 类型、样式与 i18n](#sec-8-7)
- [9. 后端改动清单](#sec-9)
- [10. 跑批与调度](#sec-10)
- [11. 口径、合规与风险](#sec-11)
- [12. 分阶段交付](#sec-12)
- [13. 验证矩阵与回滚](#sec-13)

---

<a id="sec-1"></a>

## 1. 结论摘要

| 项 | 结论 | 依据 |
|---|---|---|
| 数据 | 【强制】东财 `clist` 按市场换 `fs` 即可覆盖 cn / hk / us 全市场，默认 13 列中 11 列三市场可直接取得，2 列仅 cn 可得 | [§4.1](#sec-4-1)、[§7.2](#sec-7-2) |
| 缺失数据 | 【强制】hk / us 的「EPS 增长 TTM同比」「分析师评级」无可用来源时置 `null`、前端隐藏该列，不填 0、不编造估算值 | [§7.2](#sec-7-2) |
| 列定义 | 【强制】表格列在前端按 `TableColumnDef[]` 静态定义；后端不提供 `/columns` 端点，筛选 / 排序白名单由后端内置静态注册表校验 | [§7.2](#sec-7-2) |
| 查询入参 | 【强制】市场筛选与其它条件**统一放入 `filterList: []`**，不再有顶层 `markets` 字段 | [§7.3](#sec-7-3) |
| 列表行 | 【强制】13 列字段**平铺在行对象顶层**，不使用 `values` 嵌套 | [§7.3](#sec-7-3) |
| 类型真源 | 【强制】`types/stock.ts` 是股票标识 / 市场 / 行情字段唯一真源；标准字段经 `Pick` 复用、领域扩展字段一处定义全链路同名，不新增平行枚举 / 平行行情类型 / 同义别名 | [§5.4](#sec-5-4)、[§8.7](#sec-8-7) |
| 字段边界 | 【强制】既有后端 snake_case 契约保持不动（由既有适配层消化）；内部 provider / DB 的蛇形名与大写 market tag 只停在接入层；新建 `/query`、`/export` 直接以标准字段名输出，不引入第三套命名 | [§5.4](#sec-5-4) |
| 市场范围 | 【强制】只支持 `cn` / `hk` / `us` 三市场，不引入 `jp` / `kr` / `tw` / `BSE` | [§7.5](#sec-7-5) |
| 接口 | 【强制】精简为 2 个：`POST /query`、`POST /export`；分页继承 `PaginatedResponse` | [§7.1](#sec-7-1) |
| 卡片容器 | 【强制】统一用 `AnimCard`（`components/common/Card/AnimCard/AnimCard.tsx`），不使用裸 `Card` | [§8.4](#sec-8-4) |
| 合规 | 【强制】不抓取、不转售 TradingView 数据，只复刻交互与字段语义，数据全部自建 | [§11](#sec-11) |
| 架构 | 【强制】慢变因子离线落 SQLite，快变列在线 join 实时快照后现场计算，禁止把 PE / 市值 / 股息率落库 | [§5.2](#sec-5-2) |
| 命名 | 【强制】不使用 `screener`，页面路由 `/stock/stockMetricView`，前端 API 模块为 `api/stockMetricView.ts` | [§2](#sec-2) |
| 词根统一 | 【强制】前端 / API / 服务 / 表共用 `metric` 单一词根（`stockMetricView` / `stock-metric` / `stock_metric`），仅按语言惯例变体；`View` 只用于视图层，不进存储 / 服务层 | [§2.3](#sec-2-3) |

---

<a id="sec-2"></a>

## 2. 命名规范

<a id="sec-2-1"></a>

### 2.1 命名规定

【强制】页面路由、接口、表名、前端模块均不带 `screener`；全链路采用**单一词根 `metric`**，按语言惯例变体为 `stockMetricView`（前端 camelCase / PascalCase）、`stock-metric`（URL kebab-case）、`stock_metric`（Python / DB snake_case）；形态后缀（`View` / `Page` / `Service` / `Repo` / `Def`）按层保留，其中 `View` 只用于前端与对外查询契约，不进入存储层与服务层。

【强制】所有新增文件、端点、表、任务名、日志前缀、文档标题统一采用 [§2.2](#sec-2-2) 的映射；路由固定为 `/stock/stockMetricView`，`manifest.ts` 的 `menuId` / `routePath` / `menuPagePath` 与三语 i18n 键按该词根取值；现有 `/discover/*` 入口不改。规则见 [§2.3](#sec-2-3)。

<a id="sec-2-2"></a>

### 2.2 命名映射表

| 层 | 名称 | 动作 | 说明 |
|---|---|---|---|
| 功能 / 菜单 | 股票度量视图（Stock Metric View）· 全市场查询与筛选 | 修改 | `menuId: stockMetricView`，中文标题为「股票度量视图」，英文标题为 `Stock Metric View` |
| 页面路由 | `/stock/stockMetricView` | 修改 | 同步改 `routePath` / `menuId` / `menuPagePath` / 三语 i18n 键；不新增菜单项，不做旧路由重定向（功能未上线） |
| 前端页面 | `apps/hrs-web/src/pages/Stock/StockMetricViewPage/` | 修改 | 填充空壳 |
| 前端 API 模块 | `apps/hrs-web/src/api/stockMetricView.ts` | 新增 | **定名 `stockMetricView.ts`**，导出 `stockMetricViewApi.query / exportCsv`（**无 `getColumns`**） |
| 前端类型真源 | `apps/hrs-web/src/types/stock.ts` | 修改 | **只新增** `StockMetricViewSupportedMarket = Extract<MarketLocale, 'cn' \| 'hk' \| 'us'>`（与 `AlertSupportedMarket` 同款），不新增第二套市场枚举、不改动既有类型 |
| 前端视图类型 | `apps/hrs-web/src/types/stockMetricView.ts` | 新增 | 行 / 筛选 / 分页类型；`import type` 引用 `stock.ts`，标准字段 `Pick<StockQuoteCore, ...>` 精确组合，**不重定义任何股票字段或市场类型**（[§5.4](#sec-5-4)） |
| 前端 Hook | `apps/hrs-web/src/hooks/useStockMetricView.ts` | 新增 | 领域状态与请求编排 |
| 前端列定义 | `pages/Stock/StockMetricViewPage/components/stockMetricViewColumns.tsx` | 新增 | 静态 `TableColumnDef<StockMetricViewRow>[]` |
| API 前缀 | `/api/v1/stock-metric` | 新增 | 端点文件 `api/v1/endpoints/stock_metric.py`，仅 2 个端点 |
| 表 | `stock_metric_period`、`stock_metric_daily`、`stock_metric_calc_run` | 新增 | 存指标事实 / 派生值，避免与 `stock_daily` 语义重叠 |
| 模型 / 仓储 | `models/stock_metric.py`、`repositories/stock_metric_repo.py` | 新增 | 挂既有 `src/infrastructure/persistence/` |
| 应用服务 | `src/application/quote/stock_metric_service.py` | 新增 | 内置静态列注册表 `STOCK_METRIC_FIELDS` |
| 跑批任务 | `stock_metric_quarterly`、`stock_metric_daily` | 新增 | 见 [§10](#sec-10) |

> 【强制】前端 `stockMetricView.ts`、后端前缀 `/api/v1/stock-metric`、应用服务 `stock_metric_service.py`、表 `stock_metric_*` 共用同一词根 `metric`，仅按语言惯例变体。规则见 [§2.3](#sec-2-3)。

> 【强制】不使用 `/api/v1/stocks/metrics`；全市场列表端点只挂在 `/api/v1/stock-metric` 下。

<a id="sec-2-3"></a>

### 2.3 词根统一规则（全局强制）

**规定**：【强制】本功能所有命名共用**单一词根 `metric`**——前端 `stockMetric*` / `StockMetric*`，URL `stock-metric*`，Python / DB `stock_metric*`。禁止再出现第二词根；形态后缀按层保留，不构成命名漂移。

按下表约束各层；新增文件时先查此表，不得就地发明等价名字。

| 维度 | 规定 |
|---|---|
| 词根变体 | 【强制】TS camelCase `stockMetric*` / PascalCase `StockMetric*`；URL kebab-case `stock-metric*`；Python / DB snake_case `stock_metric*`。三种变体是**同一词根的语言惯例**，不算不一致 |
| 形态后缀 | 【强制】`View`（视图层）/ `Page`（页面）/ `Service`（应用服务）/ `Repo`（仓储）/ `Def`（数据契约）/ `Props`（组件入参）/ `period·daily·calc_run`（表）按层保留；遵循 `.conventions/frontend/TYPE_NAMING.md` |
| `View` 边界 | 【强制】`View` 只出现在前端页面、TS 类型与对外查询契约（`StockMetricViewRow` / `StockMetricViewQueryResponse`）；存储层与服务层**不加** `View`（`stock_metric_service.py` / `stock_metric_period` 保持不变） |
| 既有资产 | 【强制】`manifest.ts` 的 `menuId` / `routePath` / `menuName` / `menuDescription` / `menuPagePath`、空壳页面目录与文件名、三语 i18n 键（`layout.nav.stockMetricView.*` / `stockMetricView.*`）随词根同步改名；三语同改同序 |
| 路由兼容 | 【强制】路由固定为 `/stock/stockMetricView`，不做旧路由重定向 |
| 语义边界 | 【强制】`metric` 是内容语义，**不表示「接口直接读 `stock_metric_*` 表」**——见 [§5.2](#sec-5-2) 的在线 / 离线边界；`price` / `volume` 等行情列在筛选器语境同样视作一个 metric，不得另立 `quote*` 词根 |
| 校验 | 【强制】PR 检查 [§13](#sec-13) 命名一致性项；源码与本方案不得残留第二词根 |

---

<a id="sec-3"></a>

## 3. 目标、非目标与验收标准

<a id="sec-3-1"></a>

### 3.1 目标与非目标

✅ **目标**

- 在 `/stock/stockMetricView` 提供 cn / hk / us 三市场的全市场个股数据表：查询条件区、固定 13 列、按列排序、分页、CSV 导出。
- 数据口径、来源、更新时间在 UI 可见；`—`（无数据）与 `0` 语义分离。
- 某市场无来源的列置空并隐藏，不显示无意义列。
- 前端类型与 `types/stock.ts` 单一真源保持一致；离线跑批可重复执行、可追溯、不污染历史行。

❌ **非目标（本期不做）**

- 不抓 / 不转售 TradingView 数据，不追求与 TradingView 数值完全一致。
- 不实现后端列定义端点、动态加列、列集切换、保存筛选、预置滤网、条件告警、图表视图、AI 自然语言筛选（二期 / 三期评估）。
- 不支持 `jp` / `kr` / `tw` / `BSE` 市场。
- 不引入新数据库、不引入 Alembic、不改 `stock_daily` 表结构。
- 不提供实时行情订阅与交易所授权行情。

<a id="sec-3-2"></a>

### 3.2 验收标准

| 编号 | 标准 |
|---|---|
| AC-1 | 三市场均可返回全市场列表（cn 5000+ / hk 4000+ / us 13000+），列值口径与币种标注可见 |
| AC-2 | 至少支持 8 个筛选条件（价格、涨跌%、总市值、PE、股息率、ROE、板块、EPS 同比）与任意列排序；市场与其它条件均在 `filterList` 中；分页响应字段与 `get_items_list` 一致（`list / total / pages / pageNum / pageSize`），响应 < 1s（不含上游请求） |
| AC-3 | 亏损股 PE、未分红股股息率、无评级覆盖股票显示 `—`，不被「< 10」类条件误命中；hk / us 的「EPS 增长 TTM同比」「分析师评级」两列不显示 |
| AC-4 | 盘中查询的 PE / 总市值 / 股息率随实时价变化，不出现「昨日值」 |
| AC-5 | 跑批重复执行同一 `as_of_date` 不产生重复行；财报更正生成新 `revision`，旧行保留 |
| AC-6 | 关闭跑批开关后，页面降级为「仅实时列」仍可用，不 500 |
| AC-7 | CSV 导出列顺序与前端列定义一致，空值输出空单元格而非 `0`，hk / us 隐藏列不出现在导出中 |
| AC-8 | 切换市场后 `pageNum` 重置为 1，不支持的筛选条件被清除，列数组按该市场静态可用性重算 |
| AC-9 | `list` 元素为平铺字段（无 `values` 嵌套），字段名与 `types/stock.ts` 一致（`peRatioTTM` / `totalMarketCap` / `changePct` / `industry` 等），`market` 为小写 `cn/hk/us` |

---

<a id="sec-4"></a>

## 4. 实现基线与可复用资产

<a id="sec-4-1"></a>

### 4.1 数据来源与可得性

【强制】所有列数据自建，不抓取 / 不转售 TradingView 数据；只支持 `cn` / `hk` / `us`，市场值统一小写。

| 来源 | 用途 | 约束 |
|---|---|---|
| 东财 `push2 clist`（按市场换 `fs`） | cn / hk / us 全市场实时快照，提供 13 列中的 11 列 | 三市场返回同一套字段；`pz <= 100` 翻页、`fid = f12` 稳定排序、批量并发 ≤ 4 |
| 东财 `datacenter-web` `RPT_LICO_FN_CPD` / `RPT_PUBLIC_BS_APPOIN` / `RPT_SHAREBONUS_DET` / `RPT_WEB_RESPREDICT` | 仅 cn 的 EPS TTM 同比、收益日期、分红口径校验、研报评级聚合（离线跑批） | 全市场分页拉取；hk / us 不接入 |
| 东财 `push2his` 日线 / 本地 `stock_daily` | 二期 Beta 与多周期表现 | 并发 ≤ 4；`stock_daily` 只读，不改表结构 |

【强制】hk / us 无来源的 3 项（EPS 增长 TTM 同比、分析师评级、将近收益日期）一律置 `null` 并按 [§7.2](#sec-7-2) 隐藏整列；不填 `0`、不估算、不引入单只低频数据源充当全市场来源。

【强制】上游 `f13` 市场号与 `StockIndexMarketTag` 大写值只在数据接入层使用，对外契约与 DB 一律归一化为小写 `cn` / `hk` / `us`（[§8.7](#sec-8-7)）。字段级映射与市场可用性见 [§5.3](#sec-5-3) 与 [§7.2](#sec-7-2)。

<a id="sec-4-2"></a>

### 4.2 前端可复用资产

| 资产 | 路径 | 关键约束 |
|---|---|---|
| 股票类型真源 | `apps/hrs-web/src/types/stock.ts` | `MarketLocale` 小写 `cn/hk/us/...`；`StockRef` / `StockIdentity` / `StockQuoteCore`（`price` / `changePct` / `volume` / `peRatioTTM` / `totalMarketCap` / `industry`）；L3 用 `Pick<StockQuoteCore, ...>` 精确组合；类型层不约束单位 |
| 表格 | `apps/hrs-web/src/components/basic/Table/Table.tsx` | `TableColumnDef<T>` 需 `key/title/minWidth/defaultWidth`，支持 `allowsSorting/render`；`TableProps` 支持 `sortDescriptor/onSortChange/isLoading/renderEmptyState/pagination` |
| 卡片容器 | `apps/hrs-web/src/components/common/Card/AnimCard/AnimCard.tsx` | 默认导出 `AnimCard`，经 `Card/index.ts` 聚合进 `@components` 裸桶；`AnimCardProps` 含 `ordinal` / `variant` / `gradientBackground` / `onClick` / `tooltip` / `className` / `style` / `id` |
| 裸桶导出 | `apps/hrs-web/src/components/index.ts` | 只聚合 `basic/` 与 `common/`；**`Table`、`EmptyState` 未进裸桶**，须按 `@components/basic/Table`、`@components/basic/EmptyState` 引入 |
| 查询条件范式 | `pages/Discover/EodPickerPage/EodPickerPage.tsx:170-297` | `FilterCard` 为页面内联组件；筛选条件 `localStorage` 持久化见 `:315-334` |
| Hook 范式 | `hooks/usePortfolioSignals.ts`、`hooks/useWatchlist.ts` | `requestId` 竞态守卫、`mountedRef` 防卸载写入、领域命名返回值 |
| API 范式 | `api/stocks.ts`、`api/scanner.ts`、`api/eodPicker.ts` | `export const xxxApi = { async fn }` 直调 `apiClient`；响应 `toCamelCase` 幂等归一化 |
| 表格组合参照 | `pages/Trading/PortfolioPage/components/PortfolioTablePanel.tsx` | `AnimCard` 包表格、排序状态在面板 / hook、列定义抽离 |
| i18n | `i18n/uiText-zh.ts`（唯一键真源） | 三语同改同序，键前缀 `stockMetricView.` |

> 【强制】数值区间用双 `HrsNumberField`，CSV 导出在服务端自行实现，不引入新 UI 库。
>
> 【强制】筛选条件数组契约名固定为 `filterList`，不得套用其它页面的筛选字段命名。

<a id="sec-4-3"></a>

### 4.3 持久化与调度约定

| 规则 | 级别 | 现状 | 建议 |
|---|---|---|---|
| 模型风格 | 【强制】 | 经典声明式 `Base = declarative_base()`（`src/infrastructure/persistence/base.py:36`），全 `Column` | 新模型放 `models/stock_metric.py`，**必须在 `models/__init__.py` 登记**，否则 `create_all` 静默漏表 |
| 建表与演进 | 【强制】 | 启动 `Base.metadata.create_all` + `schema_compat.apply_startup_migrations()`，无 Alembic | 新表靠登记自动创建；老库不给已有表补列，后续改列写幂等 `ensure_*` |
| 全局字段约定 | 【强制】 | UTC naive（新代码用 `utc_naive_now`）、金额元、**比率存百分数**、纯代码字符串、JSON 用 Text、不物理删除按保留期清理（`base.py:18-24`） | DB 列名 snake_case；**DB 的 `market` 值也用小写 `cn/hk/us`**，与 `MarketLocale` 一致 |
| 批量写 | 【强制】 | `repositories/market_data_repo.py:136-227` 的 `sqlite_insert(...).on_conflict_do_update()` 分块 upsert | 复用；事务走 `DatabaseManager._run_write_transaction()`（`BEGIN IMMEDIATE` + 锁退避） |
| 保留期清理 | 【推荐】 | `repositories/intelligence_repository.py:487` 的 `apply_retention()` | 复用范式 |
| 调度 | 【强制】 | `RuntimeSchedulerService`（`src/application/runtime/runtime_scheduler.py:107`）由 `src/bootstrap/api_lifecycle.py:178-188` 装配 | 固定时刻用 `SCHEDULE_TIMES`，周期任务用 `add_background_task()` |

---

<a id="sec-5"></a>

## 5. 总体架构

<a id="sec-5-1"></a>

### 5.1 数据流

```text
[离线跑批]  datacenter(A股财报/预约披露/研报评级) + push2his 日线
                │  季频 / 日频 / 事件驱动
                ▼
        stock_metric_period / stock_metric_daily / stock_metric_calc_run
                │  慢变因子：EPS TTM 同比、评级聚合、收益日期、分红分子
                │
[在线查询]  POST /api/v1/stock-metric/query
                │  请求体：filterList[]（含 market 条件）+ sort + pageNum/pageSize
                ├─ 解析 filterList 的 market 条件 → 归一化 cn/hk/us
                ├─ 实时快照：东财 clist，按市场分别翻页（pz=100，并发 ≤ 4）
                ├─ 按 (market, code) 内存 merge 落库因子，取 MAX(as_of_date)
                ├─ 静态列白名单筛选 → 排序 → 分页 → 平铺 13 列字段
                └─ 响应：list / total / pages / pageNum / pageSize + 业务字段
```

<a id="sec-5-2"></a>

### 5.2 职责切分

【强制】只把跨数据源 join、需窗口历史、更新频率低的字段落库；价格的函数一律在线计算。新增列时先判定「是否价格的函数」——是则在线，否则离线；判定结果与来源写入前端静态列定义元数据（[§7.2](#sec-7-2)），后端静态注册表同步登记。

【强制】`stock_metric_*` 是**离线指标事实表**，只存下表左列的慢变因子；`/api/v1/stock-metric` 是**度量视图查询接口**，返回「在线 clist 快照 ⊕ 离线因子」join 后的行（一期 13 列中 11 列来自在线快照，仅 2 列来自离线表）。在筛选器语境中每一列都是一个 metric，不另立 `quote*` 词根（词根规则见 [§2.3](#sec-2-3)）。

| 职责 | 离线落库 | 在线计算 |
|---|---|---|
| 判定标准 | 跨源 join、需窗口历史、需追溯、更新频率低 | 价格的函数、实时接口已有 |
| 字段 | EPS TTM 同比、评级聚合、收益日期、分红分子、二期 Beta / 多周期表现 / 技术评级 | 价格、涨跌%、成交量、相对成交量、总市值、PE / PB / PS、股息率、EPS（当期）、板块、ROE |
| 更新 | 季频（财报）/ 日频（收盘后，二期） | 每次请求 |

<a id="sec-5-3"></a>

### 5.3 字段映射

> 【强制】下表「列 key」同时是前端列定义 key、`filterList[].field`、`sort.field` 与响应行字段名，与 `types/stock.ts` 同名字段保持一致；不再使用 `total_mv` / `pe_ttm` / `sector` 等别名。完整字段字典、四层命名边界与禁止别名清单见 [§5.4](#sec-5-4)。

| 列 key | 在线 / 离线 | 来源 | 口径备注 |
|---|---|---|---|
| `market` / `code` / `name` | 在线 | `MarketLocale` + clist `f12/f14` | 小写 `cn/hk/us`；`StockRef` 提供 `code/name` |
| `price` / `changePct` / `volume` / `relativeVolume` | 在线 | clist `f2/f3/f5/f10` | 与 `StockQuoteCore` 同名字段；量比口径可能与 TradingView 不同 |
| `totalMarketCap` / `peRatioTTM` | 在线 | clist `f20` / `f115` | 与 `StockQuoteCore` 同名；亏损股用 `null` |
| `epsDiluted` | 在线 | clist `f112` | **当期 EPS**，非严格摊薄 TTM，列头标注 |
| `dividendYieldPct` | 在线 | clist `f133` | 百分数；三市场可用，列头标注「东财口径」 |
| `industry` | 在线 | clist `f100` | 复用 `StockIdentity.industry`；值域随市场不同 |
| `epsGrowthTtmYoyPct` | 离线（仅 cn） | A 股 `RPT_LICO_FN_CPD` 多期计算 | hk / us 置空 |
| `analystRating` | 离线（仅 cn） | `RPT_WEB_RESPREDICT` 评级分布聚合 1–5 档 | **近似替代**；hk / us 无来源，置空 |
| `peg` | 在线（二期） | PE ÷ cn 增长率分母 | hk / us 缺增长率，二期评估 |
| `beta1Y` | 离线（二期） | `push2his` 三市场日线 vs 各自基准指数回归 | 基准不同：沪深300 / 恒指 / 标普500 |
| `lastEarningsDate` / `nextEarningsDate` | 离线 | `f221` 报告期 / A 股 `RPT_PUBLIC_BS_APPOIN` | 二期启用 |

<a id="sec-5-4"></a>

### 5.4 字段与类型统一规则（全局强制）

**规定**：【强制】`apps/hrs-web/src/types/stock.ts`（规范见 `documents/types/stock_type.md`）是项目内**股票标识、市场枚举与行情基础字段的唯一真源**。本功能涉及的任何「股票字段」——无论出现在 TS 类型、`TableColumnDef[].key`、`filterList[].field`、`sort.field`、CSV `visibleColumns`、对外 JSON 行，还是后端 `STOCK_METRIC_FIELDS` 注册表——**只能有一个名字**，且与 `stock.ts` 现有字段逐字一致；不得新增平行枚举、平行行情类型或任何同义别名。

按下方「四层边界」限定命名允许出现的层，按「字段字典」取名字，按「类型定义归属与新增流程」改动。

**四层边界（命名在哪一层允许不同）**

| 层 | 允许出现的名字 | 规定 |
|---|---|---|
| ① 前端业务层：`types/` / `api/` / `hooks/` / 列定义 / 组件 / `filterList[].field` / `sort.field` / 对外 JSON 行 / CSV `visibleColumns` | **仅 `stock.ts` 标准名 + 下方「领域扩展字段」名** | 【强制】一处定义、全链路同名；任何同义别名视为缺陷 |
| ② 既有后端契约：`api/v1/schemas/stocks.py` 的 `stock_code` / `current_price` / `change_percent` / `total_mv` 等 | 保持 snake_case / 旧名 | 【强制】差异由既有 `api/stocks.ts` 适配层消化；本功能不复用这些旧名 |
| ③ 内部数据接入层：`data_provider/realtime/types.py` 的 `change_pct` / `pe_ratio` / `total_mv`、东财 `f2/f3/…` 字段号、`StockIndexMarketTag` 大写标记 | 上游原名**只在接入层出现** | 【强制】服务层出口前一次性映射为 ① 的标准名；禁止把 provider 字段名 / 大写市场标记透传到业务类型、API 响应或前端（见 [§6.6](#sec-6-6)、[§11](#sec-11)） |
| ④ 存储层：`stock_metric_*` 表列名 snake_case、`_pct` 后缀 | DB 实现名 | 【强制】仅存在于 SQL / ORM 模型，不外泄为业务字段名；ORM 属性到行 DTO 的映射集中在 `stock_metric_service.py` 出口 |

> 【强制】`/query` / `/export` 属于 ① 的对外投影，直接以标准字段名输出，不额外引入 snake_case 别名；既有后端契约保持不动。

**字段字典 · 标准字段（取自 `stock.ts`，逐字一致）**

| 字段 | 真源 | 类型 / 可空 | 全链路出现位置 | 禁止别名 |
|---|---|---|---|---|
| `market` | `StockIdentity.market?: MarketLocale`，本功能用 `Extract` 收窄 | 必填 `cn/hk/us` | 行字段 / `filterList` / DB `market` / 响应 | `CN`、`region`、`Market` |
| `code` | `StockRef.code` | `string` | 行 / 列 1 | `stockCode`、`symbol`、`stock_code` |
| `name` | `StockRef.name` | `string` | 行 / 列 2 | `stockName`、`nameZh`、`stock_name` |
| `price` | `StockQuoteCore.price` | `number \| null` | 行 / 列 3 / 筛选 | `currentPrice`、`current_price` |
| `changePct` | `StockQuoteCore.changePct` | `number \| null` | 行 / 列 4 / 筛选 | `changePercent`、`change_percent`、`change_pct` |
| `volume` | `StockQuoteCore.volume` | `number \| null` | 行 / 列 5 | `vol`、`turnover` |
| `totalMarketCap` | `StockQuoteCore.totalMarketCap` | `number \| null` | 行 / 列 7 / 筛选 / 默认排序 | `totalMv`、`total_mv`、`marketCap` |
| `peRatioTTM` | `StockQuoteCore.peRatioTTM` | `number \| null` | 行 / 列 8 / 筛选 | `peTtm`、`pe_ttm`、`peRatioTtm`、`pe_ratio` |
| `industry` | `StockIdentity.industry?: string` | 可选 `string` | 行 / 列 12 / 筛选 | `sector`、`board`、`industryName` |

**字段字典 · 领域扩展字段（L3，本功能一处定义、全链路同名）**

| 字段 | 用途 | 类型 / 可空 | 阶段 |
|---|---|---|---|
| `relativeVolume` | 相对成交量（量比） | `number \| null` | 一期 · 列 6 |
| `epsDiluted` | 摊薄每股收益（当期 EPS） | `number \| null` | 一期 · 列 9 |
| `epsGrowthTtmYoyPct` | EPS 增长 TTM 同比 | `number \| null` | 一期 · 列 10 |
| `dividendYieldPct` | 股息收益率 | `number \| null` | 一期 · 列 11 |
| `analystRating` | 分析师评级 1–5 | `number \| null` | 一期 · 列 13 |
| `roePct` | 净资产收益率 | `number \| null` | 一期 · 筛选 |
| `pbRatio` | 市净率 | `number \| null` | 一期 · 筛选 |
| `psRatioTTM` | 市销率 | `number \| null` | 一期 · 筛选 |
| `revenueGrowthYoyPct` | 营收同比 | `number \| null` | 一期 · 筛选（仅 cn） |
| `peg` | PEG | `number \| null` | 二期 · 筛选 |
| `beta1Y` | Beta（1Y） | `number \| null` | 二期 · 筛选 |
| `lastEarningsDate` / `nextEarningsDate` | 最近 / 将近收益日期 | `string \| null` | 二期 · 筛选 |

- 【强制】统一 camelCase；数值字段一律 `number | null` 三态（与 `StockQuoteCore` 一致），领域文本字段 `string | null`（标准身份字段 `industry` 按下方可空协议规则取 `string | undefined`）；百分数用 `Pct` 后缀（`dividendYieldPct` / `roePct` / `epsGrowthTtmYoyPct` / `revenueGrowthYoyPct`），比率倍数用 `Ratio` + 口径后缀（`pbRatio` / `psRatioTTM`，与 `peRatioTTM` 同构），时间窗后缀写 `TTM` / `Yoy` / `1Y`。
- 【强制】单位不写进字段名（不出现 `MarketCapYi` 一类），「亿 / 元 / %」换算交 `stockMetricViewColumns.tsx` 的 `render` 与 `format.ts`（`stock_type.md` §3.1）。
- 【强制】这些字段**不进 `stock.ts` 核心层**（`stock_type.md` §3.4「不得硬塞核心层」），只在 `types/stockMetricView.ts` 的 L3 行类型 / `StockMetricViewFilterField` 中声明一次；后端 `STOCK_METRIC_FIELDS` 与 DB 列名按 ①④ 层规则映射，不产生第三套名字。

**类型定义归属与新增流程**

- 【强制】`StockMetricViewSupportedMarket` **只定义一次**：在 `types/stock.ts` 用 `Extract<MarketLocale, 'cn' | 'hk' | 'us'>`，与 `AlertSupportedMarket` / `MarketReviewSupportedMarket` 同款（`stock_type.md` §6.4）；`types/stockMetricView.ts` 只 `import type`，**不得 `export type` 重定义**。同理不新增 `Market` / `StockQuote` / `StockMetricViewMarket` 等平行类型。
- 【强制】`StockMetricViewRow` 的标准字段一律 `Pick<StockQuoteCore, ...>` 组合（不 `extends` 全量）；`market` 只以 `Omit<…, 'market'> & { market: StockMetricViewSupportedMarket }` **收窄取值**，字段名不变；`industry` 沿用 `StockIdentity` 的 `string | undefined` 语义，不另造 `string | null` 类型。
- 【强制】可空协议统一：行情数值 `T | null`；后端 `industry: null` 由 `api/stockMetricView.ts` 适配层归一为 `undefined`（差异消化在适配层，适配层不进 `types/`，`stock_type.md` §5.4）；组件统一用 `value == null` 渲染 `—`。
- 【强制】新增或改名任一股票字段：先更新本节字段字典与 `documents/types/stock_type.md`，再同步 `stock.ts`（若属标准字段）、`stockMetricView.ts`、`stockMetricViewColumns.tsx`、`api/stockMetricView.ts`、`STOCK_METRIC_FIELDS`、i18n 键、DB 映射与 [§13](#sec-13) 一致性检查项；禁止在某一层就地发明等价名字（`stock_type.md` §3.3）。

---

<a id="sec-6"></a>

## 6. 数据库设计

<a id="sec-6-1"></a>

### 6.1 表清单

| 表名 | 用途 | 写入频率 | 主键 | 保留期 |
|---|---|---|---|---|
| `stock_metric_period` | 季频财报事实与财报派生值（TTM / 同比 / 收益日期 / 分红分子） | 财报季，按水位触发 | `(market, code, report_period, period_type, revision)` | 长期保留 |
| `stock_metric_daily` | 日频派生因子（Beta、多周期表现、技术评级、评级聚合、PEG 分母），二期写入 | 收盘后一次 | `(market, code, as_of_date)` | 默认 90 天 |
| `stock_metric_calc_run` | 跑批水位线、幂等与审计留痕 | 每次跑批一次 | `run_id` | 长期保留 |

> 【强制】沿用 `DATABASE_PATH` 指向的 `data/stock_analysis.db`，不引入第二套数据库，不改 StockDB 只读契约与 `/api/v1/kline` 等既有端点；不新建股票主数据表（复用 `stocks.index.json` 与 `data_provider/stock_info/catalog.py`），不给 `stock_daily` 加列。一期只建 `stock_metric_period` + `stock_metric_calc_run`。

<a id="sec-6-2"></a>

### 6.2 `stock_metric_period` 字段清单

| 字段 | 类型 | 非空 | 含义 |
|---|---|---|---|
| `market` | `TEXT` | 是 | 市场地域，小写 `cn` / `hk` / `us`（与 `MarketLocale` 一致）；与 `code` 共同唯一定位标的 |
| `code` | `TEXT` | 是 | 纯代码字符串，不带市场后缀（如 `600519`） |
| `report_period` | `DATE` | 是 | 报告期季末日（如 `2026-09-30`） |
| `period_type` | `TEXT` | 是 | 口径：`Q1` / `H1` / `Q3` / `FY` / `TTM` |
| `revision` | `INTEGER` | 是 | 财报更正 / 追溯重述版本号，默认 `0` |
| `is_latest` | `INTEGER` | 是 | 是否为该报告期最新修订，默认 `1` |
| `publish_date` | `DATE` | 否 | 「最近收益日期」：财报实际披露日 |
| `next_publish_date` | `DATE` | 否 | 「将近收益日期」：A 股预约披露日，hk / us 为 `NULL` |
| `currency` | `TEXT` | 是 | 币种（`CNY` / `HKD` / `USD`），金额一律原币 |
| `eps_basic` | `REAL` | 否 | 基本每股收益（元 / 股） |
| `eps_diluted` | `REAL` | 否 | 稀释每股收益（元 / 股） |
| `eps_ttm` | `REAL` | 否 | 滚动 12 个月每股收益（元 / 股） |
| `eps_ttm_yoy_pct` | `REAL` | 否 | 每股收益 TTM 同比增长（百分数）；hk / us 为 `NULL` |
| `revenue_ttm` | `REAL` | 否 | 营业收入 TTM（元） |
| `revenue_ttm_yoy_pct` | `REAL` | 否 | 营收 TTM 同比（百分数） |
| `net_profit_ttm` | `REAL` | 否 | 归母净利润 TTM（元） |
| `net_profit_ttm_yoy_pct` | `REAL` | 否 | 归母净利 TTM 同比（百分数） |
| `roe_ttm_pct` | `REAL` | 否 | 净资产收益率 TTM（百分数） |
| `gross_margin_pct` | `REAL` | 否 | 毛利率（百分数） |
| `operating_cf_ttm` | `REAL` | 否 | 经营活动现金流 TTM（元） |
| `free_cf_ttm` | `REAL` | 否 | 自由现金流 TTM（元） |
| `total_assets` | `REAL` | 否 | 总资产（元） |
| `total_liabilities` | `REAL` | 否 | 总负债（元） |
| `dividend_ps_ttm` | `REAL` | 否 | 每股现金分红 TTM（元 / 股），用于 `f133` 口径校验 |
| `payout_ratio_pct` | `REAL` | 否 | 派息率（百分数） |
| `data_status` | `TEXT` | 否 | 数据质量：`OK` / `MISSING` / `ESTIMATED` / `NA`（**仅库内使用，不透出 API**） |
| `source_chain` | `TEXT` | 否 | JSON 字符串：上游来源、字段映射、抓取时间（库内使用） |
| `calc_version` | `TEXT` | 是 | 计算规则版本，公式变更时递增 |
| `created_at` | `DATETIME` | 是 | 创建时间（UTC naive，用 `utc_naive_now`） |
| `updated_at` | `DATETIME` | 是 | 更新时间（UTC naive） |

<a id="sec-6-3"></a>

### 6.3 `stock_metric_daily` 字段清单

| 字段 | 类型 | 非空 | 含义 |
|---|---|---|---|
| `market` | `TEXT` | 是 | 市场地域，小写 `cn` / `hk` / `us` |
| `code` | `TEXT` | 是 | 纯代码字符串 |
| `as_of_date` | `DATE` | 是 | 因子计算基准交易日，查询取 `MAX(as_of_date)` |
| `beta_1y` | `REAL` | 否 | 近 1 年 Beta（对该市场基准指数日收益回归） |
| `beta_3y` | `REAL` | 否 | 近 3 年 Beta |
| `ret_1w_pct` | `REAL` | 否 | 近 1 周收益率（百分数） |
| `ret_1m_pct` | `REAL` | 否 | 近 1 月收益率（百分数） |
| `ret_3m_pct` | `REAL` | 否 | 近 3 月收益率（百分数） |
| `ret_6m_pct` | `REAL` | 否 | 近 6 月收益率（百分数） |
| `ret_ytd_pct` | `REAL` | 否 | 年初至今收益率（百分数） |
| `ret_1y_pct` | `REAL` | 否 | 近 1 年收益率（百分数） |
| `volatility_1y_pct` | `REAL` | 否 | 近 1 年年化波动率（百分数） |
| `tech_rating` | `INTEGER` | 否 | 综合技术评级（档位，口径见前端列定义） |
| `tech_signal` | `TEXT` | 否 | JSON 字符串：子评级与技术信号明细 |
| `growth_rate_for_peg_pct` | `REAL` | 否 | PEG 分母（增长率百分数），hk / us 为 `NULL` |
| `analyst_score` | `REAL` | 否 | 研报评级聚合得分（1–5 档，仅 cn） |
| `analyst_count` | `INTEGER` | 否 | 覆盖机构数 |
| `target_price_low` | `REAL` | 否 | 机构目标价下限（原币） |
| `target_price_high` | `REAL` | 否 | 机构目标价上限（原币） |
| `eps_forecast_fy1` | `REAL` | 否 | 未来一财年 EPS 一致预期（元 / 股） |
| `rating_as_of` | `DATE` | 否 | 评级数据截止日 |
| `data_status` | `TEXT` | 否 | 数据质量（库内使用，不透出 API） |
| `source_chain` | `TEXT` | 否 | JSON 字符串：上游来源、字段映射、抓取时间（库内使用） |
| `calc_version` | `TEXT` | 是 | 计算规则版本 |
| `created_at` | `DATETIME` | 是 | 创建时间（UTC naive） |
| `updated_at` | `DATETIME` | 是 | 更新时间（UTC naive） |

<a id="sec-6-4"></a>

### 6.4 `stock_metric_calc_run` 字段清单

| 字段 | 类型 | 非空 | 含义 |
|---|---|---|---|
| `run_id` | `TEXT` | 是 | 跑批唯一 ID（主键） |
| `job_type` | `TEXT` | 是 | 任务类型：`stock_metric_quarterly` / `stock_metric_daily` |
| `as_of_date` | `DATE` | 是 | 本次跑批数据基准日 |
| `status` | `TEXT` | 是 | 状态：`running` / `succeeded` / `failed` / `partial` |
| `calc_version` | `TEXT` | 是 | 本次使用的计算规则版本 |
| `source_watermark` | `TEXT` | 否 | JSON 字符串：各上游最后成功时间 / 报告期水位 |
| `row_count` | `INTEGER` | 否 | 写入行数 |
| `error_message` | `TEXT` | 否 | 失败原因摘要 |
| `started_at` | `DATETIME` | 是 | 开始时间（UTC naive） |
| `finished_at` | `DATETIME` | 否 | 结束时间（UTC naive） |

<a id="sec-6-5"></a>

### 6.5 主键、索引与 DDL

【强制】字段定义以 [§6.2](#sec-6-2) – [§6.4](#sec-6-4) 为准，落地为 SQLAlchemy 经典 `Column` 模型（非手写 DDL）；以下仅列约束与索引。

```sql
CREATE UNIQUE INDEX ux_stock_metric_period_latest
  ON stock_metric_period (market, code, report_period, period_type)
  WHERE is_latest = 1;

CREATE INDEX ix_stock_metric_period_date
  ON stock_metric_period (report_period, period_type);

CREATE INDEX ix_stock_metric_daily_asof
  ON stock_metric_daily (as_of_date);

CREATE UNIQUE INDEX ux_stock_metric_run_uniq
  ON stock_metric_calc_run (job_type, as_of_date, calc_version);
```

| 约束 | 级别 | 说明 |
|---|---|---|
| 三表主键 | 【强制】 | 见 [§6.1](#sec-6-1)；`market` 必须进主键，值小写 |
| `ux_stock_metric_period_latest` | 【强制】 | 部分唯一索引，保证同一报告期 / 口径只有一条 `is_latest = 1` |
| `ix_stock_metric_daily_asof` | 【强制】 | 查询必须按 `as_of_date` 裁剪后再内存过滤 |
| `ux_stock_metric_run_uniq` | 【推荐】 | 同一任务 / 基准日 / 版本只保留一条成功记录，支撑幂等重跑 |

<a id="sec-6-6"></a>

### 6.6 字段约定（强制项）

| 规则 | 级别 | 现状 | 建议 |
|---|---|---|---|
| 主键必须带 `market` | 【强制】 | 主键含 `market`，值小写 `cn/hk/us` | 纯代码跨市场会撞（`000001` 既是平安银行也是上证指数） |
| `market` 值统一小写 | 【强制】 | `types/stock.ts` 的 `MarketLocale` 为小写规范值 | 对外契约与 DB 均用 `cn/hk/us`；上游大写 `StockIndexMarketTag` 只在接入层使用 |
| 比率存百分数 | 【强制】 | `base.py:18-24` 约定「涨跌幅百分数」 | `3.55` 而非 `0.0355`，DB 字段名统一 `_pct` 后缀；**仅存储层命名**，对外一律映射为 [§5.4](#sec-5-4) 字段字典的 `…Pct` 标准名 |
| 金额只存原币 | 【强制】 | 无汇率字段 | 只存原币 + `currency`，不存汇率换算后的市值 |
| 财报可追溯重述 | 【强制】 | `RPT_LICO_FN_CPD` 有 `UPDATE_DATE` / `ISNEW` | `revision` + `is_latest` 在同一事务内翻转 |
| 查询强制 `as_of_date = MAX(as_of_date)` | 【强制】 | API 层不接受客户端传历史日 | 漏了会查出三市场合计 2.4 万只 × N 天；回看能力另立端点 |
| `NULL` 与 `0` 分离 | 【强制】 | 亏损股 PE、未分红股股息率、hk/us 缺失列 | 用 `NULL` + `data_status`，API 只回 `null`，前端渲染 `—` 或隐藏列 |
| 血缘与口径元数据不可省 | 【强制】 | `source_chain` / `calc_version` / `data_status` | 仅库内保留，用于重算与审计；不随每行响应重复下发 |
| 不拆「最新表 / 历史表」 | 【推荐】 | 同表 + 索引 + 保留期 | 拆表引入双写一致性；Beta 的数据源是 `push2his` 日线 |
| 索引数量克制 | 【推荐】 | SQLite 多条件 AND 通常只用一个索引 | 先按 `as_of_date` 裁剪再内存过滤 |

<a id="sec-6-7"></a>

### 6.7 容量、幂等与保留

| 项 | 规定 |
|---|---|
| 容量 | 三市场合计约 2.4 万只；日频因子 2.4 万 × 250 交易日 ≈ 600 万行 / 年，含索引约 4–6 GB；**一期不写日频表**（仅 A 股季频），二期启用日频时须先评估容量与保留期 |
| 幂等 | 【强制】批量写用 `sqlite_insert(...).on_conflict_do_update(index_elements=[...])`；写事务统一 `_run_write_transaction()` |
| 历史行 | 【强制】历史行不可变；公式变更递增 `calc_version`，重算只写最新 `as_of_date`，保证 point-in-time 语义 |
| 跑批留痕 | 【强制】每次跑批写 `stock_metric_calc_run`，`source_watermark` 记各上游水位；失败可重跑同一 `as_of_date`，不写半成品 |
| 保留期 | 【强制】新增 `STOCK_METRIC_DAILY_RETENTION_DAYS`（默认 90）与 `STOCK_METRIC_JOB_ENABLED`（默认 `true`），复用 `apply_retention()` 范式；按 `AGENTS.md` 同步配置文档与 `documents/CHANGELOG.md` 的 `[Unreleased]`（扁平 `- [类型] 描述`） |

---

<a id="sec-7"></a>

## 7. 接口与列定义

<a id="sec-7-1"></a>

### 7.1 接口清单

| 编号 | 方法 | 路径 | 用途 | 请求 / 响应格式 | 阶段 |
|---|---|---|---|---|---|
| API-1 | `POST` | `/api/v1/stock-metric/query` | 全市场指标分页查询（`filterList` 筛选 / 排序 / 分页），响应继承 `PaginatedResponse` | `application/json` / `application/json` | 一期 |
| API-2 | `POST` | `/api/v1/stock-metric/export` | 按当前筛选条件导出 CSV | `application/json` / `text/csv` | 一期 |

> 【强制】**不提供 `GET /api/v1/stock-metric/columns`**：列在前端静态定义（[§7.2](#sec-7-2)），后端只保留一份静态列注册表 `STOCK_METRIC_FIELDS` 用于筛选 / 排序白名单校验与行字段填充。
>
> 【强制】API-1 的分页返回格式以 `POST /api/v1/watchlist/get_items_list` 为准：`list / total / pages / pageNum / pageSize`，详见 [§7.3](#sec-7-3)。
>
> 【强制】两个端点统一挂在 `/api/v1` 前缀下（`api/v1/router.py` 增加一行 `include_router`），继承既有鉴权与统一错误体（`api/v1/errors.py` 的 `error_body`）。
>
> 【强制】**对外契约字段统一 camelCase**，与 `apps/hrs-web/src/types/stock.ts` 的字段名逐字一致（`peRatioTTM` / `totalMarketCap` / `changePct` / `industry` / `market`），`filterList` / `pageNum` / `pageSize` 亦为 camelCase；完整字段字典与四层边界见 [§5.4](#sec-5-4)。Pydantic 行模型直接以标准字段名声明；`api/stockMetricView.ts` **不做二次驼峰转换**（`camelcase-keys` 会把 `peRatioTTM` 降级为 `peRatioTtm`）；DB / provider 的 snake_case 只出现在存储层与接入层，服务层出口做一次组装。

<a id="sec-7-2"></a>

### 7.2 前端列定义与列头清单

**规定**：【强制】表格列写成 `apps/hrs-web/src/pages/Stock/StockMetricViewPage/components/stockMetricViewColumns.tsx` 中的静态 `TableColumnDef<StockMetricViewRow>[]`，每项必填 `key` / `title` / `minWidth` / `defaultWidth`，可排序列设 `allowsSorting: true`；`key` 必须是 `StockMetricViewRow` 的字段名；`title` 由 `t('stockMetricView.column.*')` 生成。列定义逐项写全（不用元数据数组 + 通用 render 分发隐式生成），单元格渲染提取为同文件命名函数供各列引用，暂不做工厂化收敛；市场可用性写在每项 `markets` 字段上，切换市场时据此裁剪。

前端列定义与后端 `STOCK_METRIC_FIELDS` 注册表共用同一套 `key`；新增列必须同改两处并更新三语 i18n；列元数据（单位、来源、口径、市场可用性）作为静态常量随列定义一起维护。

**一期固定列头清单（13 列，字段平铺在行对象顶层）**

| # | `key`（= 行字段名） | 列头（中文） | i18n 键后缀 | 值类型 / 单位 | 数据来源 | cn | hk | us | 不可得时 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `code` | 代码 | `code` | 文本 | clist `f12` | ✅ | ✅ | ✅ | — |
| 2 | `name` | 名称 | `name` | 文本 | clist `f14` | ✅ | ✅ | ✅ | — |
| 3 | `price` | 最新价 | `price` | 数值 / 原币 | clist `f2` | ✅ | ✅ | ✅ | `—` |
| 4 | `changePct` | 涨跌幅 | `changePct` | 百分数 `%` | clist `f3` | ✅ | ✅ | ✅ | `—` |
| 5 | `volume` | 成交量 | `volume` | 数值 / 手或股 | clist `f5` | ✅ | ✅ | ✅ | `—` |
| 6 | `relativeVolume` | 相对成交量 | `relativeVolume` | 数值（量比） | clist `f10` | ✅ | ✅ | ✅ | `—` |
| 7 | `totalMarketCap` | 总市值 | `totalMarketCap` | 数值 / 原币 | clist `f20` | ✅ | ✅ | ✅ | `—` |
| 8 | `peRatioTTM` | 市盈率 P/E | `peRatioTTM` | 数值 | clist `f115`（TTM）/ `f9`（动态） | ✅ | ✅ | ✅ | 亏损股 `—` |
| 9 | `epsDiluted` | 摊薄每股收益 | `epsDiluted` | 数值 / 原币每股 | clist `f112`（**当期 EPS**） | ✅ | ✅ | ✅ | `—`；列头标注口径 |
| 10 | `epsGrowthTtmYoyPct` | 每股收益增长 TTM同比 | `epsGrowthTtmYoyPct` | 百分数 `%` | cn：`RPT_LICO_FN_CPD` 多期计算 | ✅ | ❌ | ❌ | **hk / us 隐藏整列** |
| 11 | `dividendYieldPct` | 股息收益率 | `dividendYieldPct` | 百分数 `%` | clist `f133`（东财口径） | ✅ | ✅ | ✅ | `—` |
| 12 | `industry` | 板块 | `industry` | 文本 | clist `f100` | ✅ | ✅ | ✅ | `—`；值域随市场不同 |
| 13 | `analystRating` | 分析师评级 | `analystRating` | 档位 1–5 | cn：`RPT_WEB_RESPREDICT` 聚合 | ✅ | ❌ | ❌ | **hk / us 隐藏整列** |

> 可得性依据见 [§4.1](#sec-4-1)。13 个业务列中 **11 列三市场可直接取得**；仅第 10、13 列在 hk / us 无来源。`market` 是行的标识字段（小写 `cn/hk/us`）：列表在序号列之后**单独占一列**，仅以放大的国旗呈现（本地化市场名保留在 `title` / `aria-label`），便于识别市场与原币；它不计入 13 个业务列。前端另有不进契约、不进 CSV 的序号列。**整列（列头 + 单元格）按 `align: left | right | center` 统一对齐**：序号、市场与所属板块列居中、代码与名称列左对齐、数字 / 金额列右对齐。

**置空与隐藏规则**

| 规则 | 级别 | 内容 |
|---|---|---|
| 单元格级 | 【强制】 | 无值 / 无来源一律 `null`，渲染 `—`；不得填 `0`、不得用估算值冒充；排序时 `null` 置末尾 |
| 整列级 | 【强制】 | 某市场整列无来源时，从该市场的 `TableColumnDef[]` 中**剔除该列**（hk / us 剔除第 10、13 列），列表上不显示 |
| 筛选条件 | 【强制】 | 该市场不可用的筛选字段从条件下拉移除并清除 `filterList` 中对应项；排序字段同理回退到默认 `totalMarketCap` |
| 导出 | 【强制】 | 导出列 = 当前市场可见列，隐藏列不出现在 CSV 表头 |
| 币种 | 【强制】 | cn / hk / us 分别按 `CNY` / `HKD` / `USD` 原币展示，不做汇率折算；股价 / 每股收益 / 总市值单元格附带币种代码，币种单位以小一号字号（`text-[10px]`）独立渲染、数值保持单元格原字号，空值不附带单位；数字金额列整列右对齐。前端市场单选后不产生跨市场混排；后端仍保留多值时**按市场分组（cn → hk → us）、仅组内比较原币数值**并通过 `warnings` 提示，禁止把不同币种的绝对值混排 |
| 涨跌配色 | 【强制】 | `changePct` 一律经 `getChangeColorClass()`（`src/utils/format.ts`）取色：正数 `stock-up`（红）、负数 `stock-down`（绿）、0 / `null` `text-muted-text`（灰）；色值来自 `palette.css` 的 `--stock-up` / `--stock-down` 令牌与 `global.scss` 的全局类，禁止硬编码 `text-red-*` / `text-green-*`，cn / hk / us 三市场不区分 |
| 固定列 | 【推荐】 | 通用 `Table` 的 `TableColumnDef.fixed` 取 `true` / `'left'` / `'right'`：`true` 等价固定在左侧，不传或 `false` 为默认不固定；固定列须从首列 / 末列起连续声明；偏移由 `fixedColumns.ts` 的 `useFixedColumnOffsets`（`ResizeObserver` + `MutationObserver`）按运行时列宽累加并写入容器 CSS 变量 `--hrs-table-fixed-*`，列宽拖动后自动更新，CSS Modules 类名统一 `colFixed*`；度量视图默认固定前 4 列（序号、市场、代码、名称）；固定列单元格在常态 / hover / 选中态均须保持不透明背景（HeroUI 的 `bg-surface/40` 半透明会透出下方滚动单元格内容），列头层级需高于固定列单元格 |
| 固定列分隔阴影 | 【推荐】 | 固定区与滚动区之间只在连续左固定区末列 / 右固定区首列渲染一条 16px 竖直渐淡阴影，用于区分固定列与普通列；用 `::before` 实现以避开 HeroUI 列头已占用的 `::after` 分隔线，色值取自 `--foreground` 主题令牌、随明暗主题变化 |
| K 线跳转 | 【强制】 | 代码归一复用 `utils/stock/stockCode.ts` 的 `normalizeStockCode`（覆盖前缀 / 后缀写法，不再自行 `split('.')` 去后缀），归一后经 `encodeURIComponent` 拼入 URL；链接 href 与页面 navigate 共用 `buildStockKlinePath` 单一真源。代码列与名称列仅 `market === 'cn'` 渲染跳转链接（`?stockCode=` 协议，见 jump2Kline.md）；两列在 cn / hk / us 三市场一律 `font-semibold text-primary` 加粗主题色（共用单一常量，是否可跳转不改变视觉层级）；hk / us 一期 K 线图不支持，渲染纯文本并给出 title 提示 |
| 口径提示 | 【推荐】 | `epsDiluted` 标注「当期 EPS，非严格摊薄 TTM」；`relativeVolume` 标注「量比口径」；`analystRating` 标注「券商研报评级聚合，非一致预期」 |

**筛选条件可用字段（非默认列，一期可作为筛选 / 排序）**

| `key` | 含义 | 来源 | cn | hk | us | 阶段 |
|---|---|---|---|---|---|---|
| `market` | 市场地域 | `filterList` 专用维度，值 `cn/hk/us` | ✅ | ✅ | ✅ | 一期 |
| `roePct` | 净资产收益率 | `f37` | ✅ | ✅ | ✅ | 一期 |
| `pbRatio` | 市净率 | `f23` | ✅ | ✅ | ✅ | 一期 |
| `psRatioTTM` | 市销率 | `f130` | ✅ | ✅ | ✅ | 一期 |
| `revenueGrowthYoyPct` | 营收同比 | cn：`RPT_LICO_FN_CPD` `YSTZ` | ✅ | ❌ | ❌ | 一期（仅 cn） |
| `peg` | PEG | PE ÷ 增长率分母 | ✅ | ❌ | ❌ | 二期 |
| `beta1Y` | Beta（1Y） | `push2his` 日线回归，基准按市场 | ✅ | ✅ | ✅ | 二期 |
| `lastEarningsDate` | 最近收益日期 | `f221` 报告期 / A 股 `NOTICE_DATE` | ✅ | ⚠️ | ⚠️ | 二期 |
| `nextEarningsDate` | 将近收益日期 | cn：`RPT_PUBLIC_BS_APPOIN` | ✅ | ❌ | ❌ | 二期 |

> ⚠️ 表示仅有 `f221` 报告期近似值，非真实披露日。

<a id="sec-7-3"></a>

### 7.3 `POST /api/v1/stock-metric/query`

**规定**：【强制】分页响应继承 `api/v1/schemas/common.py` 的 `PaginatedResponse`，用 `src/utils/pagination.paginate_response()` 构造；返回 `list / total / pages / pageNum / pageSize` 同层字段，不嵌套 `data`，不使用 `rows` / `page` / `page_size`。

【强制】后端 `StockMetricViewQueryResponse(PaginatedResponse)` 覆写 `list: List[StockMetricViewRowOut]` 并追加业务字段；端点用 `paginate_response(...)` 生成基础字典后补齐业务字段；前端 `StockMetricViewResultDef` 对齐 `WatchlistItemsPaginatedResponse`。

**入参（`application/json`）**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `filterList` | `StockMetricViewFilterItem[]` | 否 | **筛选条件数组（含市场条件）**，默认 `[]`；见下表。缺省或缺少 `market` 条件时默认按 `['cn']` 查询 |
| `sort` | `SortDef` | 否 | 默认 `{ "field": "totalMarketCap", "order": "desc" }` |
| `pageNum` | `integer` | 否 | 当前页码，从 `1` 开始，默认 `1`；沿用 `WatchlistItemsQueryRequest` 驼峰命名 |
| `pageSize` | `integer` | 否 | 每页条数，默认 `20`，范围 `1–100` |

`StockMetricViewFilterItem` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `field` | `StockMetricViewFilterField` | 静态注册表 `key`，须标记 `filterable = true`；`market` 为市场维度专用值 |
| `op` | `string` | 算子，见下表 |
| `value` | `number \| string \| boolean \| array \| null` | `between` 用长度为 2 的数组，`in` 用数组 |

| 算子 | 含义 | `value` 形态 |
|---|---|---|
| `eq` / `neq` | 等于 / 不等于 | 标量 |
| `gt` / `gte` / `lt` / `lte` | 数值比较 | 标量数值 |
| `between` | 闭区间 | `[min, max]`，允许 `null` 表示单侧无界 |
| `in` | 枚举包含 | 数组（用于 `market`、`industry`） |

> 【强制】市场筛选以 `{ "field": "market", "op": "in", "value": ["cn"] }` 形式放入 `filterList`，与数值 / 文本条件同构；`market` 条件只允许 `in` / `eq`，值必须是 `cn` / `hk` / `us` 的子集，且**整组条件中最多一条**。**前端市场筛选为单选**，`value` 恒为单元素数组；后端仍校验多值子集以兼容旧客户端，并保留多市场时的币种分组排序防御。
>
> 【性能】在线快照按市场做 20s TTL 缓存（`data_provider/market/eastmoney_source.py`），翻页 / 排序 / 切市场复用同一次全市场抓取；按市场细粒度锁防缓存击穿，回源失败沿用最近一次成功快照。`POST /query` 可选 `forceRefresh: boolean`（默认 `false`），前端「刷新」按钮传 `true` 强制回源；老客户端不传即命中缓存。缓存随行保存该批数据的抓取时刻（ISO 8601 带 UTC 偏移），命中缓存 / 沿用旧快照都回传该时刻，`quoteAsOf` 不再取响应生成时刻。

`SortDef` 字段：`field`（`string`，须 `sortable = true`）、`order`（`asc` / `desc`）。

**出参（`application/json`，继承 `PaginatedResponse`）**

| 字段 | 类型 | 含义 |
|---|---|---|
| `list` | `StockMetricViewRowOut[]` | 当前页数据；无匹配为 `[]` 而非 `null` |
| `total` | `integer` | 命中总数（分页前） |
| `pageSize` | `integer` | 每页条数，回显请求值 |
| `pages` | `integer` | 总页数，`ceil(total / pageSize)`，`total = 0` 时为 `0` |
| `pageNum` | `integer` | 当前页码，回显请求值 |
| `asOfDate` | `string` | 离线因子基准日 |
| `quoteAsOf` | `string`（ISO 8601，带 UTC 偏移） | 本批在线快照的抓取时刻（缓存写入时刻）；命中 TTL 缓存或回源失败沿用旧快照时返回该批缓存自己的时刻，不用响应生成时刻顶替；全部市场无在线数据时为空串 |
| `warnings` | `string[]` | 口径 / 降级提示 |
| `degraded` | `boolean` | 是否降级（如因子表不可用，仅实时列） |

> 【强制】业务附加字段与分页字段**同层**，不包 `data`；`list` 元素不含 `values` 包装、不含 `dataStatus` / `sourceChain`，数据质量由 `null` 与 `warnings` 表达。

`list` 元素 `StockMetricViewRowOut` 字段（**平铺**，与 [§7.2](#sec-7-2) 的 13 列一一对应）：

| 字段 | 类型 | 含义 |
|---|---|---|
| `market` | `string`（`StockMetricViewSupportedMarket`） | 市场地域，小写 `cn` / `hk` / `us`，为 `MarketLocale` 子集 |
| `code` / `name` | `string` | 标的标识（`StockRef`） |
| `price` / `changePct` / `volume` / `totalMarketCap` / `peRatioTTM` | `number \| null` | 行情核心字段（与 `StockQuoteCore` 同名同义） |
| `relativeVolume` | `number \| null` | 相对成交量（量比） |
| `epsDiluted` | `number \| null` | 摊薄每股收益（当期 EPS） |
| `epsGrowthTtmYoyPct` | `number \| null` | EPS 增长 TTM 同比（百分数）；hk / us 为 `null` |
| `dividendYieldPct` | `number \| null` | 股息收益率（百分数） |
| `industry` | `string \| null` | 板块 / 所属行业（`StockIdentity.industry`） |
| `analystRating` | `number \| null` | 分析师评级档位 1–5；hk / us 为 `null` |

> 【强制】本表字段名逐项对应 [§5.4](#sec-5-4) 字段字典。`industry` 在后端为 `string \| null`，前端经 `api/stockMetricView.ts` 适配层归一为 `StockIdentity.industry` 的 `string \| undefined`，差异只消化在适配层。

请求示例：

```json
{
  "filterList": [
    { "field": "market", "op": "in", "value": ["cn"] },
    { "field": "totalMarketCap", "op": "gte", "value": 100000000000 },
    { "field": "peRatioTTM", "op": "lt", "value": 20 }
  ],
  "sort": { "field": "totalMarketCap", "order": "desc" },
  "pageNum": 1,
  "pageSize": 50
}
```

响应示例（行字段平铺）：

```json
{
  "list": [
    {
      "market": "cn",
      "code": "601398",
      "name": "工商银行",
      "price": 8.44,
      "changePct": 1.08,
      "volume": 1234567,
      "relativeVolume": 0.98,
      "totalMarketCap": 2940000000000,
      "peRatioTTM": 7.83,
      "epsDiluted": 0.8,
      "epsGrowthTtmYoyPct": 2.93,
      "dividendYieldPct": 3.79,
      "industry": "银行Ⅱ",
      "analystRating": 5
    }
  ],
  "total": 5376,
  "pageSize": 50,
  "pages": 108,
  "pageNum": 1,
  "asOfDate": "2026-11-07",
  "quoteAsOf": "2026-11-07T06:52:31.123456+00:00",
  "warnings": ["分析师评级由券商研报评级聚合，口径与 TradingView 一致预期不同"],
  "degraded": false
}
```

前端类型（`apps/hrs-web/src/types/stockMetricView.ts`）：标准字段**只从 `types/stock.ts` 取**，不重定义任何股票字段或市场类型（[§5.4](#sec-5-4)）：

```ts
import type {
  StockMetricViewSupportedMarket, // 定义在 types/stock.ts，本文件只 import，不重定义
  StockQuoteCore,
} from '@/types/stock';

/** 标准字段：全部经 Pick 取自 StockQuoteCore（含身份字段 market / industry），不 extends 全量 */
type StockMetricViewStandardFields = Pick<
  StockQuoteCore,
  | 'code' | 'name' | 'market' | 'industry'
  | 'price' | 'changePct' | 'volume' | 'totalMarketCap' | 'peRatioTTM'
>;

/** 行：标准字段 + L3 领域扩展字段（平铺）；market 仅收窄取值，名字与真源一致 */
export type StockMetricViewRow = Omit<StockMetricViewStandardFields, 'market'> & {
  market: StockMetricViewSupportedMarket;
  relativeVolume: number | null;
  epsDiluted: number | null;
  epsGrowthTtmYoyPct: number | null;
  dividendYieldPct: number | null;
  analystRating: number | null;
};

export type StockMetricViewFilterField =
  | 'market' | 'price' | 'changePct' | 'totalMarketCap' | 'peRatioTTM'
  | 'dividendYieldPct' | 'industry' | 'epsGrowthTtmYoyPct'
  | 'roePct' | 'pbRatio' | 'psRatioTTM' | 'revenueGrowthYoyPct';

export interface StockMetricViewFilterItem {
  field: StockMetricViewFilterField;
  op: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'between' | 'in';
  value: number | string | boolean | null | Array<string | number>;
}

export interface StockMetricViewQueryDef {
  filterList?: StockMetricViewFilterItem[];
  sort?: { field: string; order: 'asc' | 'desc' };
  pageNum?: number;
  pageSize?: number;
}

/** 继承 watchlist 分页形状；响应字段已是 camelCase */
export interface StockMetricViewResultDef {
  list: StockMetricViewRow[];
  total: number;
  pageSize: number;
  pages: number;
  pageNum: number;
  asOfDate: string;
  quoteAsOf: string;
  warnings: string[];
  degraded: boolean;
}
```

> 【强制】`api/stockMetricView.ts` 对后端已是 camelCase 的响应**原样透传，禁止二次 `toCamelCase`**（实测 `camelcase-keys` 会把 `peRatioTTM` / `psRatioTTM` 降级为 `peRatioTtm` / `psRatioTtm`，导致整列取值为空）；**禁止**依赖自动驼峰转换生成缩写字段名。后端返回 `industry: null` 时由 `api/stockMetricView.ts` 适配层归一为 `undefined`（差异消化在适配层，不进 `types/`），组件统一用 `value == null` 渲染 `—`。后端 `STOCK_METRIC_FIELDS` 注册表的 key 与 [§5.4](#sec-5-4) 字段字典及 `StockMetricViewFilterField` 逐项一致。

<a id="sec-7-4"></a>

### 7.4 `POST /api/v1/stock-metric/export`

**入参（`application/json`）**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `filterList` / `sort` | 同 [§7.3](#sec-7-3) | 否 | 复用同一筛选 DSL（含 `market` 条件），不含 `pageNum` / `pageSize` |
| `headers` | `Record<string, string>` | 否 | 前端传入的本地化列名（键为列 `key`），服务端按当前市场可见列顺序输出表头 |
| `visibleColumns` | `string[]` | 否 | 当前市场可见列 `key` 顺序；缺省用该市场静态默认列序 |
| `limit` | `integer` | 否 | 默认 `5000`，上限 `5000`；超出部分截断并在响应头提示 |

**出参**

| 项 | 规格 |
|---|---|
| 成功 | `200`，`Content-Type: text/csv; charset=utf-8`；`Content-Disposition: attachment; filename="stock-metric-view_YYYYMMDD.csv"` |
| 内容 | UTF-8 BOM + CRLF 换行；首行表头（`headers` 优先，否则列 `key`）；首列固定 `market,code,name`；空值输出空单元格；数值不做千分位格式化 |
| 隐藏列 | 【强制】hk / us 的第 10、13 列不出现在表头与数据行 |
| 截断 | 响应头 `X-Export-Truncated: 1` 表示达到 `limit` |
| 失败 | 返回统一 JSON 错误体（[§7.5](#sec-7-5)），不返回半份 CSV |

> 【强制】导出走服务端，不由前端循环分页拉取；导出与 `/query` 使用同一套筛选与列可见性口径。

<a id="sec-7-5"></a>

### 7.5 通用契约与错误响应

| 约束 | 级别 | 规定 |
|---|---|---|
| 白名单 | 【强制】 | `filterList[].field` 与 `sort.field` 必须来自后端内置静态注册表 `STOCK_METRIC_FIELDS`（key 与前端 `StockMetricViewFilterField` 一致，含 `filterable` / `sortable` / `markets` 标记）；禁止拼接任意 SQL 或列名 |
| 市场白名单 | 【强制】 | `filterList` 中 `market` 条件的值仅 `cn` / `hk` / `us`，大小写按 `MarketLocale` 归一化 |
| 条件数量 | 【强制】 | `filterList` 长度 `<= 20`，`market` 条件最多 1 条；`sort` 缺省回退 `totalMarketCap desc` |
| 参数校验 | 【强制】 | `pageNum >= 1`、`pageSize` 范围 `1–100`、`export.limit <= 5000`；非法值返回 `422` |
| 错误体 | 【强制】 | 沿用 `api/v1/errors.py` 的 `error_body`，由 `api/middlewares/error_handler.py` 归一为顶层 `{ error, message, detail? }`；前端用 `api/error.ts` 解析 |
| 降级 | 【强制】 | 上游快照失败按现有回退链降级；全部失败返回 `503` + 空态，不返回半假数值；落库因子缺失时对应列返回 `null`，`degraded = true`，不阻塞查询 |
| 缺失数据 | 【强制】 | 无来源列返回 `null`，不填 0、不估算；前端按 [§7.2](#sec-7-2) 隐藏整列 |
| 口径展示 | 【强制】 | 响应携带 `asOfDate` / `quoteAsOf` / `warnings`，UI 必须展示数据来源与新鲜度 |
| 缓存 | 【推荐】 | 实时快照沿用 `REALTIME_CACHE_TTL`；`/query` 与 `/export` 不登记 `CACHE_TTL_MAP`，避免双重失效 |

错误码约定：

| HTTP | 场景 | 前端处理 |
|---|---|---|
| `400` | `filterList` 非法字段 / 算子 / 该市场不支持的字段 / 重复 `market` 条件 | `InlineAlert` 提示具体字段 |
| `422` | 参数越界（分页、市场值、导出上限、条件数量） | 表单内联错误 |
| `503` | 全部行情源不可用 | 空态 + 重试按钮 |
| `200 + degraded` | 因子表不可用 / 部分源失败 | 顶部 `InlineAlert` 提示 |

```json
{
  "error": "STOCK_METRIC_INVALID_FILTER",
  "message": "Unsupported filter field: fooBar",
  "detail": { "field": "fooBar" }
}
```

<a id="sec-7-6"></a>

### 7.6 复用接口与内部上游

| 类型 | 接口 / 来源 | 用途 | 约束 |
|---|---|---|---|
| 分页契约参照 | `POST /api/v1/watchlist/get_items_list`（`WatchlistItemsPaginatedResponse`） | 提供 `list / total / pages / pageNum / pageSize` 形状与 `paginate_response()` 构造方式 | 【强制】`/query` 继承同名同类型字段 |
| 复用（对外） | `api/v1/endpoints/watchlist.py` 现有端点 | 二期 `scope = watchlist` 的自选表范围 | 不改契约 |
| 复用（对外） | `api/v1/endpoints/sector.py` 现有端点 | 二期指数 / 板块选项 | 不改契约，路径以 `api/v1/router.py` 注册为准 |
| 内部上游 | 东财 `push2.eastmoney.com/api/qt/clist/get` | cn / hk / us 全市场实时快照（按市场换 `fs`） | `pz <= 100`、并发 ≤ 4 |
| 内部上游 | 东财 `push2his.eastmoney.com/api/qt/stock/kline/get` | 二期 Beta 的三市场日线 | 并发 ≤ 4 |
| 内部上游 | `datacenter-web` `RPT_LICO_FN_CPD` / `RPT_PUBLIC_BS_APPOIN` / `RPT_SHAREBONUS_DET` / `RPT_WEB_RESPREDICT` | A 股财报、披露日、分红、评级 | 全市场分页拉取，仅离线跑批调用 |
| 内部数据 | `stock_daily` 本地表 | 二期 A 股 Beta / 多周期表现计算 | 只读，不修改表结构 |

---

<a id="sec-8"></a>

## 8. 前端实现方案

<a id="sec-8-1"></a>

### 8.1 分层规定

**规定**：【强制】采用 `components - page - useXXXXX - api` 四层，依赖方向单向向下，组件与页面不直接发请求；**列定义是前端静态资产，类型真源在 `types/stock.ts`**。

```text
types/stock.ts ─────────────────────────────┐ (MarketLocale / StockQuoteCore)
   └── types/stockMetricView.ts ─────────────┤ (行 / 筛选 / 分页类型)
                                           ▼
pages/Stock/StockMetricViewPage/StockMetricViewPage.tsx   (page：组装与布局)
   ├── pages/.../components/*                       (components：纯展示 + 受控交互)
   │      └── stockMetricViewColumns.tsx              (静态 TableColumnDef[] + 列元数据)
   └── hooks/useStockMetricView.ts                    (useXXXXX：状态、请求、竞态、持久化)
              └── api/stockMetricView.ts              (api：query / exportCsv 两个方法)
                         └── /api/v1/stock-metric/*
```

| 层 | 目录 / 文件 | 职责 | 依赖 | 约束 |
|---|---|---|---|---|
| `page` | `pages/Stock/StockMetricViewPage/StockMetricViewPage.tsx` | 页面骨架、区域编排、把 hook 返回值分发给子组件 | `components` + `useStockMetricView` | 【强制】不写请求逻辑、不内联列定义 |
| `components` | `pages/Stock/StockMetricViewPage/components/` | 查询条件区、指标表格、导出按钮、口径提示；静态列定义 | 仅 `props` + 列常量 + 类型真源 | 【强制】不直接调用 `apiClient`，不持有业务请求状态 |
| `useXXXXX` | `src/hooks/useStockMetricView.ts` | `filterList` / 排序 / 分页状态、请求编排、`requestId` 竞态守卫、`localStorage` 持久化 | `api/stockMetricView.ts` + 类型真源 | 【强制】不返回 JSX；不反向依赖页面 / 列定义；返回值用领域命名 + `UseStockMetricViewResult` |
| `api` | `src/api/stockMetricView.ts` | `stockMetricViewApi.query / exportCsv`；camelCase 响应原样透传（**禁止二次 `toCamelCase`**，会破坏 `peRatioTTM` 等连续大写字段）；仅做 `id` 拼接与 `industry: null` 归一 | `apiClient` + 类型真源 | 【强制】不含 UI 状态、不返回列定义、不缓存业务结果 |

✅ **值得做**

- 列定义与列元数据（单位、来源、口径、市场可用性）放同一文件，切换市场时一次重算 `columns`。
- `requestId` 递增守卫过期响应（参照 `hooks/usePortfolioSignals.ts:201-212`），`mountedRef` 防卸载写入（参照 `hooks/useWatchlist.ts:23-32`）。
- `filterList` 持久化到 `localStorage`（参照 `EodPickerPage.tsx:315-334`），刷新后自动恢复并触发一次查询。
- 后端 `STOCK_METRIC_FIELDS` 与前端 `StockMetricViewFilterField` 用同一套 key，PR 检查两侧一致。

❌ **必须避免**

- 在页面组件里 `apiClient.post(...)`；在 `components` 里持有 `isLoading` 并自行请求。
- 从 `@components` 裸桶引入 `Table` / `EmptyState`（未进桶）。
- 手写原生 `<button>`（标准按钮用 `@components` 的 `HrsButton`）；新增 CSS / SCSS 文件。
- 组件内硬编码中文列名；筛选 / 排序参数绕过后端静态白名单。
- 为「按市场切列」再向后端发一次列定义请求；在前端另造 `Market` / `StockQuote` 类型、大写市场值，或为任何股票字段另起别名（见 [§5.4](#sec-5-4)）。

<a id="sec-8-2"></a>

### 8.2 文件清单

| 文件 | 动作 | 内容 |
|---|---|---|
| `src/types/stock.ts` | 修改 | **只在此处定义** `StockMetricViewSupportedMarket = Extract<MarketLocale, 'cn' \| 'hk' \| 'us'>`；不改既有类型 |
| `src/types/stockMetricView.ts` | 新增 | `StockMetricViewRow` / `StockMetricViewFilterItem` / `StockMetricViewQueryDef` / `StockMetricViewResultDef`；`import type` 引用真源，不重定义股票字段（见 [§7.3](#sec-7-3)、[§5.4](#sec-5-4)） |
| `src/api/stockMetricView.ts` | 新增 | `stockMetricViewApi.query / exportCsv`；`filterList` 请求体；响应字段名已与类型真源一致 |
| `src/hooks/useStockMetricView.ts` | 新增 | 领域状态、请求编排、竞态守卫、持久化、`UseStockMetricViewResult`（分页字段与 `PaginationDef` 同名） |
| `src/hooks/index.ts` | 修改 | 【推荐】登记 `useStockMetricView` 及其类型导出 |
| `src/pages/Stock/StockMetricViewPage/StockMetricViewPage.tsx` | 修改 | 填充空壳，组装布局 |
| `src/pages/Stock/StockMetricViewPage/components/StockMetricViewFilterBar.tsx` | 新增 | 查询条件区（市场条件 + 常用条件 + 已启用 Chip + 添加 / 重置 / 查询），统一输出 `filterList` |
| `src/pages/Stock/StockMetricViewPage/components/StockMetricViewMetricTable.tsx` | 新增 | `AnimCard` + `Table` 封装、排序、受控分页、空态、`—` 渲染 |
| `src/pages/Stock/StockMetricViewPage/components/stockMetricViewColumns.tsx` | 新增 | **静态 `TableColumnDef<StockMetricViewRow>[]` 13 列 + 列元数据 + 按市场可用性过滤函数**（[§7.2](#sec-7-2)） |
| `src/i18n/uiText-{zh,zh-Hant,en}.ts` | 修改 | 三语同改同序，键前缀 `stockMetricView.`（列名 13 个 + 空态 / 错误 / 导出提示） |

> 【强制】沿用 [§2.2](#sec-2-2) 的路由与菜单命名，不新增额外入口；一期不实现列集切换 / 加列组件，不登记 `/columns` 缓存键。

<a id="sec-8-3"></a>

### 8.3 页面布局

```text
┌ AppPage ───────────────────────────────────────────────────────────────┐
│ PageHeader  股票度量视图                                                │
│   rightSlot: [市场单选 cn/hk/us] [刷新] [导出 CSV]                     │
│ DataRefreshBar  行情时间 14:52:31 · 因子基准 2026-11-07 · 币种/数据源  │
├ AnimCard · 查询条件区（Collapsible 可折叠）────────────────────────────┤
│ 常用条件: 价格 | 涨跌 % | 总市值 | P/E | 股息率 % | ROE | 板块 | …     │
│   每条 = 字段名 + 算子 + 单值或双值区间 + 移除 ×                       │
│ [+ 添加条件] [重置] [查询]      已启用条件 Chip × N                    │
│   → 统一组装为 filterList（含 { field:'market', op:'in', ... }）       │
├ InlineAlert  口径提示 / 降级警告 / 错误提示 / 缺失列说明                │
├ AnimCard · 结果区 ─────────────────────────────────────────────────────┤
│ StockMetricViewMetricTable                                                │
│   Table（序号 + 市场 + 13 业务列；整列对齐 / 列头排序 / 空态）        │
│   Pagination（受控，分页字段直取响应；常驻不随 loading 隐藏）         │
└───────────────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 数据来源 | 交互 |
|---|---|---|---|
| 页头 | `AppPage` / `PageHeader` | i18n | 市场单选（写入 `filterList` 的 `market` 条件）、手动刷新、导出 |
| 新鲜度条 | `DataRefreshBar` + 页头因子基准文本 | `quoteAsOf` 转 `Date` 传 `lastUpdate`（实时模式，`snapshotTime` 不传）/ `asOfDate` 单独展示 | 点击刷新、倒计时归零自动刷新 |
| 查询条件区 | `AnimCard` + `StockMetricViewFilterBar` + `StockMetricViewConditionEditor` | 前端静态列元数据的 `filterable` 列 + `code` | `StockSearch` 选中股票写入 `code eq` 条件（跨市场自动切市场）并立即查询；显示域只读回显已保存条件（含 code Chip）、点「编辑条件」打开模态框表单批量新增 / 移除草稿、点「保存」整组回写并回显（取消 / 关闭丢弃草稿）、重置、查询 |
| 提示区 | `InlineAlert` | `warnings` / `degraded` / 错误 / 隐藏列说明 | 重试 |
| 结果区 | `AnimCard` + `StockMetricViewMetricTable` / `Table` / `Pagination` | `/query` 的 `list`，分页取 `total` / `pages` / `pageNum` / `pageSize` | 列头排序、翻页、`—` 空值渲染 |

> 【强制】查询条件区与结果区各用一个 `AnimCard`（`ordinal` 分别取 0 / 1 形成错位入场），不使用裸 `Card`；一期不提供列集 Tabs，二期若开放多列集仍按前端静态列定义扩展。

<a id="sec-8-4"></a>

### 8.4 组件清单

| 区域 | 组件 | 引入路径 | 用途 | 备注 |
|---|---|---|---|---|
| 布局 | `AppPage` | `@components/layout/AppPage` | 页面容器 | 已有 |
| 布局 | `PageHeader` | `@components/layout/PageLayout/PageHeader` | 标题 + `rightSlot` | 已有，复用现有 i18n 标题键 |
| **卡片容器** | **`AnimCard`** | **`@components`**（实现：`components/common/Card/AnimCard/AnimCard.tsx`） | 条件区 / 结果区卡片 | 【强制】**替代裸 `Card`**；经 `Card/index.ts` 聚合导出，默认导出组件由桶转为命名导出；`AnimCardProps` 提供 `ordinal`（入场错位）、`variant`（`default` / `gradient`）、`gradientBackground`、`tooltip`、`onClick`、`className`、`style`、`id` |
| 布局 | `DataRefreshBar` | `@components/common/DataRefreshBar` | 数据新鲜度与刷新 | 已有 |
| 查询条件 | `HrsInput` | `@components` | 文本条件输入 | 裸桶可用 |
| 查询条件 | `HrsNumberField` | `@components` | 数值与区间双输入 | 裸桶可用；无 Slider 封装 |
| 查询条件 | `HrsSelect` / `Select` | `@components` | 市场、算子、板块下拉 | 裸桶可用；市场值小写 `cn/hk/us` |
| 查询条件 | `Chip` | `@components` | 已启用条件标签与移除 | 裸桶可用 |
| 查询条件 | `StockSearch` | `@components/StockSearch` | 股票搜索（写入 `code` 条件） | 选中回传 `displayCode` / `marketTag`，跨市场自动切市场；键击原文不提交 |
| 查询条件 | `Switch` / `HrsCheckbox` | `@components` | 布尔条件（如排除 ST） | 裸桶可用 |
| 查询条件 | `Collapsible` | `@components` | 条件区折叠 | 仓库无 Accordion 封装 |
| 查询条件 | `Modal` | `@components` | 「编辑条件」模态框 | 表单在 `Modal.Body`，取消 / 保存在 `Modal.Footer` |
| 查询条件 | `StockMetricViewConditionEditor` | 页面 `components/` | 显示域 + 编辑按钮 + 条件编辑模态框 | 纯受控：草稿仅在模态框内，保存时整组回写 |
| 结果区 | `Table` | `@components/basic/Table` | 可排序数据表 | **不在裸桶**；`TableColumnDef` 必填 `minWidth/defaultWidth` |
| 结果区 | `EmptyState` | `@components/basic/EmptyState` | 空态 | **不在裸桶**；配合 `renderEmptyState` |
| 结果区 | `Pagination` | `@components` | 受控分页 | `PaginationDef` 由 hook 提供 |
| 反馈 | `InlineAlert` | `@components` | 口径 / 降级 / 错误提示 | 裸桶可用 |
| 操作 | `HrsButton` | `@components` | 查询 / 重置 / 导出 / 刷新 | 【强制】不手写原生 `<button>` |

> 【推荐】`AnimCard` 用法参照 `pages/Trading/PortfolioPage/components/PortfolioTablePanel.tsx:277`：`className="flex-1 min-h-0 flex-col p-4"` 包裹表格；条件区用 `variant="default"`，结果区可用 `gradientBackground` 增强层次。

> 【强制】`/query` 已由后端分页：前端把 `list` 直接作为 `Table` 的 `rows`，把 `total` / `pageSize` / `pages` / `pageNum` 组装成 `PaginationDef` 传入，**不做二次切片**；`isLoading` 时不渲染分页栏。
>
> 【强制】数值列格式化集中在 `stockMetricViewColumns.tsx`：百分数带 `%`、市值按 `万亿 / 亿` 缩写、货币带原币代码、`null` 渲染 `—`；币种随 `market` 变化。

<a id="sec-8-5"></a>

### 8.5 `useStockMetricView` 契约

`UseStockMetricViewResult` 返回值（领域命名；列定义来自静态常量，不进入 hook 返回值）：

| 字段 | 类型 | 含义 |
|---|---|---|
| `filterList` | `StockMetricViewFilterItem[]` | 全部筛选条件，**含 `market` 条件** |
| `selectedMarket` | `StockMetricViewSupportedMarket` | 从 `filterList` 派生，供 UI 单选展示与列可见性裁剪 |
| （列定义） | `TableColumnDef<StockMetricViewRow>[]` | 由页面按当前市场调用静态列元数据构建，Hook 不反向依赖组件层 |
| `sortDescriptor` | `{ field, order }` | 当前排序 |
| `pageNum` / `pageSize` / `pages` / `total` | `number` | 分页状态，字段名与 `PaginationDef` 一致，无需映射 |
| `list` | `StockMetricViewRow[]` | 当前页数据（后端已分页，直接作为 `Table` 的 `rows`） |
| `asOfDate` / `quoteAsOf` | `string` | 因子基准日 / 行情时间 |
| `warnings` | `string[]` | 口径与降级提示 |
| `isLoading` / `isExporting` / `degraded` | `boolean` | 请求与降级状态 |
| `errorMessage` | `string \| null` | 错误信息 |
| `setMarketFilter` | `(v: StockMetricViewSupportedMarket) => void` | 改写 `filterList` 中的 `market` 条件并重置页码 |
| `addFilter` / `removeFilter` / `resetFilters` | `(...) => void` | 条件增删与重置（操作 `filterList`） |
| `setSortDescriptor` / `setPageNum` | `(v) => void` | 排序 / 翻页 |
| `refresh` | `() => void` | 手动刷新（传 `forceRefresh=true` 跳过 TTL 缓存） |
| `exportCsv` | `() => Promise<void>` | 触发导出（传当前可见列 + 本地化 `headers`） |

```ts
export interface UseStockMetricViewResult {
  filterList: StockMetricViewFilterItem[];
  selectedMarket: StockMetricViewSupportedMarket;
  list: StockMetricViewRow[];
  total: number;
  pageSize: number;
  pages: number;
  pageNum: number;
  isLoading: boolean;
  errorMessage: string | null;
  setMarketFilter: (v: StockMetricViewSupportedMarket) => void;
  refresh: () => void;
  exportCsv: (visibleColumns: { key: string; title: string }[]) => Promise<void>;
  // 其余字段见上表
}
```

> 【强制】每次请求携带递增 `requestId`，只接受最后一次响应；卸载后不写状态；`filterList` 持久化到 `localStorage`，恢复后触发一次查询。
>
> 【强制】翻页时把 `pageNum` 写入请求体，响应回来后整组替换 `list` / `total` / `pages` / `pageNum` / `pageSize`；不累积拼接多页数据，不按 `pages` 预拉全量。

<a id="sec-8-6"></a>

### 8.6 交互规则

| 编号 | 级别 | 规则 |
|---|---|---|
| I-1 | 【强制】 | 页面挂载**直接发起 `/query`**（不等待任何列定义请求）；缺省 `filterList` 时补一条 `{ field: 'market', op: 'in', value: ['cn'] }` |
| I-2 | 【强制】 | 筛选条件变更不立即请求，点「查询」或 `Enter` 触发；排序 / 翻页立即请求 |
| I-3 | 【强制】 | 排序 / 翻页保留当前 `filterList`；重置条件清空非 `market` 条件并回到第 1 页 |
| I-4 | 【强制】 | 请求期间旧表格保留并置 `isLoading`，不闪空态；失败展示 `InlineAlert` + 重试 |
| I-5 | 【推荐】 | 数值区间用两个 `HrsNumberField`，留空表示单侧无界；`between` 的 `min > max` 时前端内联报错 |
| I-6 | 【推荐】 | 导出携带当前 `filterList` / `sort` / `visibleColumns` 与本地化 `headers`；导出中禁用按钮 |
| I-7 | 【推荐】 | 列头展示静态元数据中的 `source` / `caliber_note` 提示，不宣称与 TradingView 数值一致 |
| I-8 | 【强制】 | 所有列值为 `null` 时渲染 `—`，不渲染 `0`、不参与数值排序（置末尾） |
| I-9 | 【强制】 | 切换市场时：`pageNum = 1`、改写 `filterList` 的 `market` 条件、清除该市场不支持的条件、按静态列可用性重算 `visibleColumns`（hk / us 隐藏第 10、13 列），并用 `InlineAlert` 提示被隐藏的列 |
| I-10 | 【推荐】 | 市场单选后列数组按当前市场裁剪（无来源列直接剔除），金额单元格附原币代码，不做汇率折算 |

<a id="sec-8-7"></a>

### 8.7 类型、样式与 i18n

| 项 | 规定 |
|---|---|
| 类型真源 | 【强制】`apps/hrs-web/src/types/stock.ts` 与 `documents/types/stock_type.md` 是股票标识 / 市场语义 / 行情字段的唯一真源；本功能**不得新建平行类型、平行枚举或同义别名**，完整规则见 [§5.4](#sec-5-4) |
| 支持范围类型 | 【强制】`StockMetricViewSupportedMarket` **只在 `types/stock.ts` 定义一次**（`Extract<MarketLocale, 'cn' \| 'hk' \| 'us'>`，与 `AlertSupportedMarket` 同款）；`types/stockMetricView.ts` 只 `import type`，不 `export type` 重定义 |
| 行类型 | 【强制】`StockMetricViewRow` 的标准字段（含 `market` / `industry`）一律 `Pick<StockQuoteCore, ...>` 组合（**不 extends 全量**）；`market` 仅用 `Omit` 收窄取值，不重声明标准字段；扩展列按 [§5.4](#sec-5-4) 领域扩展字典平铺声明 |
| 字段命名 | 【强制】列 key、行字段、`filterList[].field`、`sort.field`、CSV `visibleColumns`、后端 `STOCK_METRIC_FIELDS` key 全部使用 [§5.4](#sec-5-4) 字段字典中的同一名字；`peRatioTTM` / `totalMarketCap` / `changePct` / `industry` 与 `stock.ts` 逐字一致；禁止 `totalMv` / `peTtm` / `peRatioTtm` / `sector` / `changePercent` 等别名 |
| 可空协议 | 【强制】行情数值统一 `T \| null` 三态；`industry` 沿用 `StockIdentity` 的 `string \| undefined`，后端 `null` 由 `api/stockMetricView.ts` 适配层归一为 `undefined`，适配层不进 `types/` |
| 单位 | 【强制】类型层不约束单位（`stock.ts` §3.1），「亿 / 元 / %」的换算与展示由 `stockMetricViewColumns.tsx` 的 `render` 负责 |
| 类型命名 | 【强制】数据契约用 `Def` 后缀（`StockMetricViewQueryDef`），组件入参用 `Props` 后缀（`StockMetricViewFilterBarProps`）；遵循 `.conventions/frontend/TYPE_NAMING.md` |
| 组件规范 | 【强制】命名导出、禁默认导出（引用既有 `AnimCard` 时按桶的命名导出使用）、完整透传原生 Props、`cn` 合并且外部 `className` 最后、禁新增 CSS / SCSS、禁 `!important`；遵循 `.conventions/frontend/COMPONENTS.md` |
| 样式 | 【强制】Tailwind + HSL 变量；`Table` 自带 scss 属既有例外，不新增样式文件 |
| i18n | 【强制】`i18n/uiText-zh.ts` 为唯一键真源，`zh` / `zh-Hant` / `en` 三语同改同序；键前缀 `stockMetricView.column.*` 对应 13 个列头，另含空态 / 错误 / 导出 / 隐藏列提示；市场 label 后缀沿用小写 `cn/hk/us`；禁组件硬编码；遵循 `.conventions/frontend/I18N_NAMING.md` |

---

<a id="sec-9"></a>

## 9. 后端改动清单

| 层 | 文件 | 动作 | 说明 |
|---|---|---|---|
| 数据接入 | `data_provider/market/eastmoney_source.py` | 修改 | 扩展 `_FS` 为三市场参数（cn / hk / us 各自 `fs`）、扩展 `_FIELDS`（`f2/f3/f5/f6/f9/f10/f12/f14/f20/f23/f37/f100/f112/f115/f130/f133/f221`）；保留 `pz <= 100` 翻页与现有回退；接入层把大写原始市场标记归一化为小写 `MarketLocale` 值 |
| 数据接入 | `data_provider/fundamentals/` | 修改 | A 股财报期、预约披露、研报评级、分红字段映射（hk / us 不接入，直接置空） |
| 契约 | `api/v1/schemas/stock_metric.py` | 新增 | 请求模型 `filterList: List[FilterItem]`（含 `market` 条件）、`sort`、`pageNum`、`pageSize`；`StockMetricViewQueryResponse` 继承 `common.PaginatedResponse` 并覆写 `list: List[StockMetricViewRowOut]`；**行模型 13 列字段平铺、字段名逐字取自 [§5.4](#sec-5-4) 字段字典**；无列定义模型 |
| 端点 | `api/v1/endpoints/stock_metric.py` | 新增 | **仅 2 个端点**；`/query` 解析 `filterList`、用 `paginate_response()` 生成分页字典后补业务字段，`response_model=StockMetricViewQueryResponse` |
| 路由 | `api/v1/router.py` | 修改 | 增加 `prefix="/stock-metric"` 的 `include_router` 一行 |
| 工具（复用） | `src/utils/pagination.py` | 复用 | `paginate_response()` / `compute_pages()` 直接复用，不改动 |
| 应用 | `src/application/quote/stock_metric_service.py` | 新增 | 内置静态列注册表 `STOCK_METRIC_FIELDS`（key 与前端 `StockMetricViewFilterField` 同名，含 `filterable` / `sortable` / `markets`）；解析 `filterList` 的 `market` 条件；三市场 clist 拉取与 merge；缺失列置 `null`；按 `pageNum` / `pageSize` 做 offset/limit 返回 `(items, total)`；平铺组装行；CSV 导出；离线因子计算 |
| 模型 | `src/infrastructure/persistence/models/stock_metric.py` | 新增 | 3 个经典 `Column` 模型（一期只写 2 张表），`market` 值小写 |
| 模型登记 | `src/infrastructure/persistence/models/__init__.py` | 修改 | 【强制】必须登记，否则 `create_all` 漏表 |
| 仓储 | `src/infrastructure/persistence/repositories/stock_metric_repo.py` | 新增 | 批量 upsert、取最新 `as_of_date`、保留期清理 |
| 调度 | `src/application/runtime/runtime_scheduler.py` / `src/bootstrap/api_lifecycle.py` | 修改 | 注册季频跑批任务，避开 18:00 分析任务 |
| 配置 | `src/config/settings.py`、`src/config/field_definitions.py` | 修改 | 2 个新键，默认可运行；同步 `docs/full-guide.md` 配置清单 |
| 文档 | `documents/CHANGELOG.md` | 修改 | `[Unreleased]` 扁平格式追加一条 |

> 【强制】后端改动不触碰 `/discover/*` 相关端点；前端改动清单见 [§8.2](#sec-8-2)。

---

<a id="sec-10"></a>

## 10. 跑批与调度

| Job | 频率 | 输入 | 输出 | 阶段 |
|---|---|---|---|---|
| `stock_metric_quarterly` | 财报季每日检查水位，有更新才跑 | `RPT_LICO_FN_CPD`、`RPT_PUBLIC_BS_APPOIN`、`RPT_SHAREBONUS_DET`、`RPT_WEB_RESPREDICT`（均 A 股） | `stock_metric_period` + `stock_metric_calc_run` | 一期 |
| `stock_metric_daily` | 收盘后一次 | `push2his` 三市场日线、评级聚合、财报派生值 | `stock_metric_daily` | 二期 |

| 约束 | 级别 | 规定 |
|---|---|---|
| 上游并发 | 【强制】 | 访问 `push2` / `push2his` 的批量逻辑并发 ≤ 4 并带重试退避；三市场全量翻页按 `pz = 100`、`fid = f12` 稳定排序 |
| 错峰 | 【强制】 | 与 AI 分析任务共用 `data/stock_analysis.db`（WAL + `BEGIN IMMEDIATE`），跑批避开 `SCHEDULE_TIMES` 默认 18:00 |
| 幂等 | 【强制】 | 同一 `as_of_date` 可重复执行且结果一致；失败只留 `stock_metric_calc_run` 记录，不写半成品 |
| 降级 | 【强制】 | 关闭 `STOCK_METRIC_JOB_ENABLED` 后 `/query` 跳过落库因子，仅返回实时列（AC-6） |
| 市场覆盖 | 【强制】 | 一期跑批只处理 `cn`；hk / us 的离线因子列直接置 `null`，不伪造覆盖 |

---

<a id="sec-11"></a>

## 11. 口径、合规与风险

| 风险 | 影响 | 处置 |
|---|---|---|
| TradingView 条款 | 数据使用合规 | 【强制】只复刻交互，数据全自建；正式商用前由法务复核条款 |
| 口径不一致 | TTM / 摊薄 EPS / 股息率 / 板块 / 评级档位与 TradingView 不同 | 【强制】UI 展示静态列元数据中的来源与口径；`epsDiluted` 标「当期 EPS」、评级标估算；不宣称「与 TradingView 一致」 |
| `f133` 股息率口径 | 上游口径可能与 TTM 股息率不同 | 【强制】上线前用 `RPT_SHAREBONUS_DET` 交叉校验；列头标注「东财口径」 |
| 跨市场币种 | cn / hk / us 分别 CNY / HKD / USD，金额不可直接比较 | 【强制】按原币展示，不做汇率折算；前端市场单选后不产生跨市场混排，后端保留多值时的分组排序防御 |
| 市场值大小写 | 上游 `StockIndexMarketTag` 大写与 `MarketLocale` 小写并存 | 【强制】只在数据接入层归一化，对外契约与 DB 一律小写 `cn/hk/us`；禁止在业务类型中直接使用大写标记 |
| 字段名漂移 | 各层命名不一致 / 前端二次驼峰转换破坏缩写字段 | 【强制】按 [§5.4](#sec-5-4) 字段字典全链路同名；后端已为 camelCase 时前端原样透传，不做二次 `toCamelCase`；不依赖自动转换生成缩写字段名 |
| hk / us 部分列无来源 | EPS 同比、分析师评级、将近收益日期 | 【强制】置 `null`，前端隐藏整列；不填 0、不估算 |
| 动态列集合切换 | 切市场时列数 13 ↔ 15，React Aria 按行数据对象缓存已渲染的 `Row`，旧行复用旧 `columns` 会抛 `Cell count must match column count` | 【强制】`Table` 以列 key 签名作为 `Body` / `Row` 的 `dependencies` 精确失效缓存；切市场同步清空旧市场行；不重挂载整表，保留选中 / 排序 / 列宽状态 |
| 免费源延迟行情 | 盘中数值滞后 | 标 `quoteAsOf`；对外发布另需交易所行情授权评估 |
| 落库固化估算值 | 估算被当成权威数据 | 库内 `data_status` + `calc_version` + 不可变历史行；API 只回 `null` 与 `warnings` |
| 财报追溯重述 | 旧值残留导致筛选错误 | `revision` + `is_latest` 事务内翻转 |
| SQLite 写竞争 / 容量 | 跑批与分析任务抢锁，日频表二期增长快 | 错峰调度、WAL 重试、90 天保留期；二期启用日频前先做容量评估（[§6.7](#sec-6-7)） |
| 上游限流 / 接口变更 | 三市场快照缺失 | 双源回退（东财 / akshare / 腾讯，港美无回退时置空）、`degraded = true`、页面降级不 500 |

---

<a id="sec-12"></a>

## 12. 分阶段交付

| 阶段 | 范围 | 交付物 |
|---|---|---|
| 一期 MVP | **cn / hk / us 三市场**；前端静态 13 列（hk / us 隐藏 2 列）；`filterList` 筛选（含市场条件）、行字段平铺、排序分页、服务端 CSV 导出；只建 `stock_metric_period` + `stock_metric_calc_run`，仅 cn 跑季频 job | 填充 `StockMetricViewPage`、2 个端点、2 张表、1 个季频 job、四层前端、类型真源对齐 |
| 二期 | 扩展列（Beta / PEG / 最近与将近收益日期 / ROE / PB / PS）、`stock_metric_daily` 日频 job、前端列集切换（仍为静态列定义）、补 hk / us 缺失数据源（若有）、`scope = watchlist/index` | 日频表与跑批、扩展列定义、范围筛选 |
| 三期（评估） | 长尾指标长表、保存筛选、预置滤网、AI 自然语言筛选、图表视图 | 策略选股能力另立页面，复用本方案指标表 |

---

<a id="sec-13"></a>

## 13. 验证矩阵与回滚

**验证**

| 面 | 命令 / 动作 |
|---|---|
| 后端 | `./scripts/ci_gate.sh`；最低 `./.venv/bin/python -m py_compile <changed_python_files>`；新增 `pytest -m "not network"` 覆盖仓储 upsert、`revision` 翻转、静态白名单校验、`filterList` 的 `market` 条件解析、三市场缺失列 `null`、重复跑批幂等 |
| 前端 | `cd apps/hrs-web && npm ci && npm run lint && npm run build` |
| 联调 | 后端 `./.venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000`；前端 `cd apps/hrs-web && npm run dev`（端口 1022，`/api` 代理 8000）；人工核对 AC-1 ~ AC-9，逐个切换 cn / hk / us |
| 类型一致性 | 【强制】按 [§5.4](#sec-5-4) 字段字典逐项核对 `stock.ts` / `stockMetricView.ts` / 列定义 / `filterList` / `sort` / 后端 `STOCK_METRIC_FIELDS` / Pydantic 行模型字段名；确认 `StockMetricViewSupportedMarket` 只在 `stock.ts` 定义一次、全仓无 `totalMv` / `peTtm` / `changePercent` 等别名；`tsc` 覆盖 `Pick<StockQuoteCore, ...>` 组合 |
| 数据 | 【强制】上线前用 `RPT_SHAREBONUS_DET` 对 `f133` 抽样复核、三市场各抽 3 只核对 13 列值；确认港股人民币柜台（如 `89988`）的 `f20` / `f2` 币种口径；三市场全量翻页端到端压测（us 约 139 页） |
| 命名一致性 | 【强制】按 [§2.3](#sec-2-3) 逐项核对前端模块 / 路由 / i18n 键 / API 前缀 / 端点文件 / 服务 / 表 / 静态注册表的词根；确认源码与本方案无第二词根残留、三语 i18n 键同改同序 |
| PR | 【强制】涉及 Web UI 变更，PR 描述附页面前后对比截图（`AGENTS.md` §1） |

**回滚**

| 级别 | 动作 |
|---|---|
| L1 | `manifest.ts` 中 `menuVisible: false` 隐藏菜单，路由仍可直达 |
| L2 | 摘除 `api/v1/router.py` 一行 `include_router`，两个端点整体下线 |
| L3 | 关闭 `STOCK_METRIC_JOB_ENABLED` 停止跑批；【强制】表不删，按保留期自然清理 |
| L4 | 前端回滚到空壳 `StockMetricViewPage.tsx`（当前 31 行版本） |


