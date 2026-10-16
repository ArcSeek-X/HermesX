# <a id="尾盘选股法eod-picker移植方案"></a>尾盘选股法（EOD Picker）移植方案

> 📝 **方案简述**：本方案将参考项目 stock-dashboard 的尾盘选股法（又称一日持股法）移植到 HermesX，前端落地于 /eodPicker 路由页面。它确认了参考项目 analysis.ts 的核心选股逻辑，规定前端三屏结构、筛选卡片、股票卡片、排序栏与持久化照搬参考实现，后端按算法层面对齐提供数据，并给出移植对照表、关键决策、实施顺序、前端组件复用策略，以及与 ADR-001 后端架构的合规性对照。当前后端 service、endpoint 与前端页面均已落地。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-13

## 方案目录

  - [改动日志](#改动日志)
- [目录](#目录)
- [参考项目核心逻辑（已从源码确认）](#参考项目核心逻辑已从源码确认)
- [A. 命名与路由（已落地）](#a-命名与路由已落地)
- [B. 前端：照搬参考项目 UI 与交互](#b-前端照搬参考项目-ui-与交互)
  - [页面三屏结构（照搬）](#页面三屏结构照搬)
  - [筛选卡片（照搬默认条件，可点击编辑）](#筛选卡片照搬默认条件可点击编辑)
  - [股票卡片（照搬）](#股票卡片照搬)
  - [排序栏（照搬）](#排序栏照搬)
  - [持久化（照搬）](#持久化照搬)
  - [适配点（非照搬，必须对接本仓库）](#适配点非照搬必须对接本仓库)
- [C. 后端：为前端提供数据（算法层面对齐参考 analysis.ts）](#c-后端为前端提供数据算法层面对齐参考-analysists)
- [D. 移植对照表](#d-移植对照表)
- [E. 验证与文档](#e-验证与文档)
- [F. 关键决策（已确认，开工基准）](#f-关键决策已确认开工基准)
- [G. 实施顺序](#g-实施顺序)
- [H. 与 ADR-001（后端架构）的合规性对照](#h-与-adr-001后端架构的合规性对照)
- [I. 前端组件复用策略（现成优先）](#i-前端组件复用策略现成优先)
  - [组件使用与修改原则（实现期必须遵守）](#组件使用与修改原则实现期必须遵守)


> 参考项目：`https://github.com/chengzuopeng/stock-dashboard`（演示页 `https://chengzuopeng.github.io/stock-dashboard/eod-picker`）
> 目标：将「尾盘选股法 / 一日持股法」功能移植到 HermesX，前端落在 `/eodPicker` 路由页面。

| 项 | 内容 |
|---|---|
| 关联架构 | `documents/framework/backend_architecture_adr.md`（ADR-001，已采纳） |
| 状态 | 已实施（后端 service + endpoint + 前端页面均已落地，离线单测通过） |

### <a id="改动日志"></a>改动日志

| 时间 | 版本 | 变更摘要 |
|---|---|---|
| 2026-10-10 | v1.0 | 初版方案：参考项目核心逻辑梳理、前端/后端设计、移植对照、验证与文档、关键决策（已确认）、ADR-001 合规性对照、前端组件复用策略；补作者/更新时间/改动日志与可跳转目录 |

---

## <a id="目录"></a>目录

- [参考项目核心逻辑（已从源码确认）](#overview)
- [A. 命名与路由（已落地）](#sec-a)
- [B. 前端：照搬参考项目 UI 与交互](#sec-b)
  - [页面三屏结构（照搬）](#sec-b-1)
  - [筛选卡片（照搬默认条件，可点击编辑）](#sec-b-2)
  - [股票卡片（照搬）](#sec-b-3)
  - [排序栏（照搬）](#sec-b-4)
  - [持久化（照搬）](#sec-b-5)
  - [适配点（非照搬，必须对接本仓库）](#sec-b-6)
- [C. 后端：为前端提供数据](#sec-c)
- [D. 移植对照表](#sec-d)
- [E. 验证与文档](#sec-e)
- [F. 关键决策（已确认，开工基准）](#sec-f)
- [G. 实施顺序](#sec-g)
- [H. 与 ADR-001 的合规性对照](#sec-h)
- [I. 前端组件复用策略（现成优先）](#sec-i)

---

<a id="overview"></a>
## <a id="参考项目核心逻辑已从源码确认"></a>参考项目核心逻辑（已从源码确认）

- **分时强度（Timeline Strength）** = 当日分时中「价格 ≥ 均价线」的采样点占比 × 100%，衡量股价站上均价线的时长，默认阈值 ≥80%。
  - 输入：`{ time, price, avgPrice }[]`
  - 计算：`aboveAvgCount / total * 100`，边界相等算「在均价上方」
- **筛选流程**：
  1. 全市场 A 股实时快照（全量）
  2. 基础过滤：流通市值 50~200 亿 / 量比 ≥1.2 / 当日涨幅 3~5% / 换手率 5~10% / 排除 ST
  3. 逐只拉分时，算分时强度，二次过滤：`ratio < timelineAboveAvgRatio` 剔除
  4. 按分时强度降序输出
- **UI**：开始屏（开始分析大按钮 + 可编辑筛选卡片）→ 进度遮罩（阶段文案/百分比/取消）→ 结果卡片网格（含 SVG 分时图：价格线 / 均价线 / 昨收虚线）
- 涨跌色：红涨绿跌。

<a id="sec-a"></a>
## <a id="a-命名与路由已落地"></a>A. 命名与路由（已落地）

- `apps/hrs-web/src/router/manifest.ts`：`menuId: 'eodPicker'` / `routePath: 'eodPicker'` / `menuPagePath: 'pages/Discover/EodPickerPage'`，level 0，protected。
- 页面文件：`apps/hrs-web/src/pages/Discover/EodPickerPage.tsx`（当前为占位骨架，待实现）。
- i18n：`apps/hrs-web/src/i18n/uiText-{zh,zh-Hant,en}.ts` 中 `layout.nav.eodPicker.title/description` 已更新（三语 key 集合由 `UiTextKey` 类型强制对齐）。

<a id="sec-b"></a>
## <a id="b-前端照搬参考项目-ui-与交互"></a>B. 前端：照搬参考项目 UI 与交互

直接参照参考项目 `src/pages/EndOfDayPicker/EndOfDayPicker.tsx`，按 HermesX 技术栈适配。

<a id="sec-b-1"></a>
### <a id="页面三屏结构照搬"></a>页面三屏结构（照搬）

1. **开始屏**：发光「开始分析」按钮（Zap 图标 + glow）+ 筛选条件卡片。
2. **进度遮罩**：阶段文案（获取行情数据 / 分时结构筛选）+ 百分比 + 进度条 + 取消（abort）。
3. **结果屏**：数量统计、排序栏、股票卡片网格。

<a id="sec-b-2"></a>
### <a id="筛选卡片照搬默认条件可点击编辑"></a>筛选卡片（照搬默认条件，可点击编辑）

| 筛选项 | 默认 | 编辑控件 |
|---|---|---|
| 流通市值 | 50~200 亿 | 两 NumberField（上限可空） |
| 量比 | ≥1.2 | NumberField step 0.1 |
| 当日涨幅 | 3~5% | 两 NumberField step 0.5 |
| 换手率 | 5~10% | 两 NumberField step 0.5 |
| 过滤 ST | 开启 | Toggle |
| 分时强度 | ≥80% | NumberField 0-100 step 5 |

<a id="sec-b-3"></a>
### <a id="股票卡片照搬"></a>股票卡片（照搬）

- 名称 + 代码；涨幅徽章（▲/▼ + 百分比）
- 现价 + 涨跌额 + 「强度 x%」
- **分时图**：复用现有 `KLineChart`（`period='1m'` 分时模式），价格线 + 均价线 + 昨收基准线 + 红涨绿跌（视觉等价参考项目的纯 SVG 图）
- 四宫格：流通市值(亿) / 量比 / 换手率(%) / 成交额
- 加自选按钮（已自选禁用）

<a id="sec-b-4"></a>
### <a id="排序栏照搬"></a>排序栏（照搬）

涨幅 / 分时强度 / 换手率 / 流通市值 / 量比，点击切换 asc/desc，`null` 用 `?? 0` 兜底。

<a id="sec-b-5"></a>
### <a id="持久化照搬"></a>持久化（照搬）

localStorage 存 `filters`（500ms 防抖）、`schemes`（方案）、`recent`（最近使用，上限 5 去重，含 `healFilters` 兜底修复旧版 `0→null`）。

<a id="sec-b-6"></a>
### <a id="适配点非照搬必须对接本仓库"></a>适配点（非照搬，必须对接本仓库）

- 数据来源：参考项目直连 stock-sdk；本仓库改为调 HermesX 后端 `/api/v1/eod-picker/*`（见 C），沿用 `apiClient` 与 `StockScreeningPage` 的轮询模式（2s 轮询 task）。
- 组件：**优先复用本仓库 `components/` 现成组件**（详见 I 节映射表），不重复造轮子；仅在无现成组件时才自行实现（如筛选卡片组合、排序栏、本地持久化模块、API 封装）。
- 分时图：**复用现有 `KLineChart`（`period='1m'` 分时模式）+ 现有 `GET /api/v1/kline`**，不引入新图表组件、不自造 SVG（与参考项目纯 SVG 方案不同，但视觉等价且统一了项目图表栈）。
- i18n：文案走 `useUiLanguage()` 字典，不直接硬编码中文。
- 加自选：调本仓库 watchlist API（参考项目用自有 store）。
- 离开页面必须中止轮询 / 请求，避免后台无效扫描（参考项目有 `AbortController` + 卸载清理）。

<a id="sec-c"></a>
## <a id="c-后端为前端提供数据算法层面对齐参考-analysists"></a>C. 后端：为前端提供数据（算法层面对齐参考 analysis.ts）

- `src/services/eod_picker_service.py`：复刻参考 `calculateTimelineStrength` + `filterBasicQuotes` + 两阶段筛选 + 有界并发（默认并发 4，可配置）。
  - 阶段1 全市场快照：复用 `AkshareFetcher` 全市场缓存（`ak.stock_zh_a_spot_em`，含流通市值 / 量比 / 换手率 / 涨幅，见 `data_provider/akshare_fetcher.py`）。
  - 阶段2 分时：复用 `data_provider/kline/` 1 分钟源（tencent/sina/eastmoney），**均价线 = 累计成交额 / 累计成交量（VWAP）**；需验证分钟源是否带 amount，无则 price×volume 累计近似。
  - **前端分时可视化复用现有 `KLineChart`**：`components/kline/KLineChart.tsx` 已内置「分时模式」（`period === '1m'`），用 `close` 画价格线、用 `amount/volume` 累计算均价线、`prevClose` 画昨收基准线，红涨绿跌 + 双 Y 轴；其消费契约为 `api/kline.ts` 的 `KLinePoint`。因此**卡片分时图直接复用 `KLineChart` + 现有 `GET /api/v1/kline/{code}?period=1m`**，无需自造 SVG、无需新增图表组件。eod-picker 后端只负责用同一 1m 源在筛选阶段算出「分时强度」指标值。
  - 快照短 TTL 缓存（默认 ~30s），避免重复拉全市场。
- `api/v1/endpoints/eod_picker.py` + `api/v1/schemas/eod_picker.py`（薄端点 + 固定契约）：
  - `GET /api/v1/eod-picker/defaults`：返回默认筛选条件（市值 50~200 亿 / 量比 ≥1.2 / 涨幅 3~5% / 换手率 5~10% / 过滤ST=true / 分时强度 ≥80%）。
  - `POST /api/v1/eod-picker/tasks` → 202 + `task_id`（复用 `src/services/task_queue.py` 后台任务）。
  - `GET /api/v1/eod-picker/tasks/{id}` → `{ completed, total, stage }` + **结果摘要**：每只股票含 code/name/price/changePercent/change/volume/amount/turnoverRate/volumeRatio/circulatingMarketCap/totalMarketCap/pe/pb/high/low/open/prevClose/timelineAboveAvgRatio（**不含分时明细**，避免巨型 payload）。
- **分时明细懒加载（已确认）**：前端点卡片展开分时图时，调用**现有** `GET /api/v1/kline/{code}?period=1m`（复用 `data_provider/kline` + `KLineChart` 分时模式），**不新增专用 timeline 端点**。eod-picker 后端仅在筛选阶段用同一 1m 源计算 `timelineAboveAvgRatio`，不回传点阵。
- 注册进 `api/v1/router.py`。
- 非交易日 / 无分时数据：给出明确提示，不做静默降级。
- 不新增必配配置项；并发与缓存 TTL 用常量默认值，如需暴露再加 env 并同步 `.env.example`。

<a id="sec-d"></a>
## <a id="d-移植对照表"></a>D. 移植对照表

| 参考项目 | HermesX 落点 |
|---|---|
| `src/services/analysis.ts` | `src/services/eod_picker_service.py`（Python 复刻算法） |
| `src/pages/EndOfDayPicker/EndOfDayPicker.tsx` | `src/pages/Discover/EodPickerPage.tsx` + 子组件 |
| `src/components/charts/LazyEChart`（分时） | **复用现有 `KLineChart`（`period='1m'` 分时模式）+ `GET /api/v1/kline`**（懒加载，非照搬 SVG） |
| stock-sdk 直连 | HermesX `apiClient` + eod-picker 任务 API（结果摘要），分时明细走现有 kline API |
| localStorage 逻辑 | 照搬，封装到 `eodPickerStorage.ts` 持久化模块 |

<a id="sec-e"></a>
## <a id="e-验证与文档"></a>E. 验证与文档

- 后端：`py_compile` + pytest（覆盖筛选 / 强度计算，离线用例）。
- 前端：`npm run lint` + `npm run build`；PR 描述附页面截图（AGENTS.md 硬规则）。
- 文档：`documents/CHANGELOG.md` [Unreleased] 扁平条目 + 专题 `documents/product/尾盘选股/eod-picker.md`。
- 盘中实测全流程（非盘中仅验证降级提示与 UI）。

<a id="sec-f"></a>
## <a id="f-关键决策已确认开工基准"></a>F. 关键决策（已确认，开工基准）

1. **分时强度计算放后端**：数据层已在后端，前端只照搬 UI 与展示；后端 `eod_picker_service.py` 用 `data_provider/kline` 1m 源计算 `price ≥ 均价线` 占比，前端不重算。
2. **结果列表懒加载**：列表只返回指标 + `timelineAboveAvgRatio`；点卡片展开分时图时，**前端调现有 `GET /api/v1/kline/{code}?period=1m`** 懒加载分时明细（复用 `KLineChart` 分时模式），避免一次返回几十只 ×240 点的巨型 payload。
3. **「方案管理」「最近使用」照搬**：全部存 `localStorage`（`filters` 500ms 防抖、`schemes`、`recent` 上限 5 去重、`healFilters` 兜底），封装为 `eodPickerStorage.ts`，不落后端。
4. **暂不纳入（留作 Phase 3）**：批量加自选联动、尾盘定时推送（结合 `RuntimeSchedulerService` + 通知服务）。

> 上述四项已确认，方案其余章节均按此收敛，可据此开工。

<a id="sec-g"></a>
## <a id="g-实施顺序"></a>G. 实施顺序

1. 后端：数据快照入口（复用 AkshareFetcher 全市场 spot）+ `eod_picker_service.py`（两阶段筛选 + 分时强度计算，纯函数内聚）+ 三个 API（defaults / tasks / tasks/{id}，结果摘要不含分时明细）+ 测试。
2. 前端：实现 `EodPickerPage.tsx`（开始屏 / 进度 / 结果屏 / 排序栏），组合现成组件；`eodPickerStorage.ts` 本地持久化（filters/schemes/recent）；`eodPicker.ts` API 封装；分时图复用 `KLineChart` + 现有 kline API **懒加载**；i18n 走字典。
3. 文档与验证：后端 `py_compile` + pytest；前端 `npm run lint` + `npm run build`；PR 附页面截图；`documents/CHANGELOG.md` [Unreleased] 扁平条目 + `documents/product/尾盘选股/eod-picker.md`。

**Phase 3（本次不纳入）**：批量加自选联动（接现有 watchlist API）、尾盘定时（~14:30）自动跑 + 推送通知（接 `RuntimeSchedulerService` + 通知服务）。

<a id="sec-h"></a>
## <a id="h-与-adr-001后端架构的合规性对照"></a>H. 与 ADR-001（后端架构）的合规性对照

本方案严格遵循 `documents/framework/backend_architecture_adr.md`（ADR-001，已采纳）的四层架构与「`data_provider` 为唯一脏活层」铁律，逐项核对如下：

| ADR-001 条款 | 本方案对应设计 | 合规 |
|---|---|---|
| §2.1 四层架构：③ 功能接口层 = 端点(瘦) + 服务(编排)，② 数据源对接层 = 唯一脏活层 | 端点 `api/v1/endpoints/eod_picker.py` 只做路由 + 任务编排；`src/services/eod_picker_service.py` 做业务编排；**所有外部取数一律走 `data_provider/`**（AkshareFetcher 全市场 spot、`data_provider/kline` 1m），端点/服务层不直接 `requests` | ✅ |
| §2.2 `data_provider` 为唯一脏活层，禁止在 services/endpoints 直连源 | 全市场快照复用 `akshare_fetcher.py` 既有 `stock_zh_a_spot_em` 通道；分时复用 `data_provider/kline/*_source.py`，**均不新增 fetcher、不平行实现** | ✅ |
| §2.4 / §4.4 多源平等 + 自动回退（仅强约束 K线/基础信息/代码搜索三类基础能力） | eod-picker 不属于上述三类能力，但其取数**完全复用**已具备多源回退的既有能力（spot/kline），不引入新的单源硬编码 | ✅ |
| §3 ① 数据库层铁律：外部 API 只做进程内 TTL 缓存、不落表 | 全市场快照采用进程内 TTL 缓存（~30s）；eod-picker 结果为**瞬时计算产物**，仅存于异步任务对象内（内存），**不落任何表**，符合「外部 API 不落表」原则 | ✅ |
| §5.1 / §5.4 ③ 层契约固定、只随功能演进、不随数据源变 | 新增 `/api/v1/eod-picker/*` 三个端点契约固定；底层换源对前端透明（前端只认 task + 结果契约） | ✅ |
| §5.2 / §5.3 端点置于 `api/v1/endpoints/`、契约模型置于 `api/v1/schemas/` | 端点文件 `eod_picker.py` + schema 文件 `eod_picker.py` 注册入 `api/v1/router.py`，命名与目录遵循固有 `*_service.py` / `*_fetcher.py` / `base.py` 规律 | ✅ |
| §2.7 不堆临时补丁、正确结构优先 | strength 计算为纯函数置于 service 层编排内；无 config 顶替、无静默降级（非交易日/无数据明确提示） | ✅ |
| AGENTS.md「优先复用现有模块，不新增平行实现」 | 快照、1m 分时、KLineChart、watchlist、任务队列（`task_queue`）全部复用既有实现，仅新增 eod-picker 专属编排与页面 | ✅ |

**结论**：方案与 ADR-001 一致，无需为 eod-picker 新建数据源能力或突破分层；新增代码量为「一个 service 编排 + 一个端点 + 一个 schema + 一个前端页面（组合现成组件）」，影响面小、契约稳定。

<a id="sec-i"></a>
## <a id="i-前端组件复用策略现成优先"></a>I. 前端组件复用策略（现成优先）

目标：页面功能照搬参考项目，但**组件一律优先采用 `apps/hrs-web/src/components/` 中的现成组件**，无则自行实现。已对 `components/basic`、`components/common`、`components/kline`、`components/layout/PageLayout` 盘点，可用资产如下：

| 页面需求（参考项目组件） | 本项目现成组件 | 复用方式 |
|---|---|---|
| 卡片容器 / 区块 | **`AnimCard`**(`common/Card/AnimCard.tsx`) | 直接复用（结果卡片网格首选：用 `ordinal` 做错位入场动画；可配 `variant='gradient'` / `gradientBackground`） |
| 开始分析按钮 / 各类操作按钮 | `Button` / `HrsButton`(basic) | 直接复用（glow 样式用 Tailwind 复刻） |
| 过滤 ST 开关 Toggle | `Switch`(basic) | 直接复用 |
| 数值输入（市值/量比/涨幅/换手率/强度） | `HrsInput`(basic) | 复用；若需 `type="number"` 而 `HrsInput` 不支持，则在其上包一层薄 numeric wrapper（不算新基础组件） |
| 弹层（方案管理 / 最近使用面板） | `Modal`(basic) / `HrsDrawer`(common) | 直接复用 |
| 排序栏 Tab | `TabNav`(common) | 复用做排序切换，或纯按钮组 |
| 加载 / 进度 | `Loading`(basic) | 复用（进度遮罩自组合） |
| 空态 / 无结果 | `EmptyState`(basic) | 直接复用 |
| 标题区 | `PageHeader`(layout/PageLayout) | 直接复用（占位骨架已用） |
| 提示 Toast | `Toast` / `InlineToast`(basic) | 直接复用（取消/无结果提示） |
| 分页（结果较多时） | `Pagination`(common) | 直接复用 |
| 滚动容器 | `ScrollArea`(common) | 直接复用 |
| **分时图（参考为纯 SVG）** | **`KLineChart`(kline, `period='1m'`)** | **复用现有 ECharts 分时模式**，消费 `KLinePoint`（价格线 + 均价线 + 昨收基准线 + 红涨绿跌），视觉等价且统一图表栈 |

### <a id="组件使用与修改原则实现期必须遵守"></a>组件使用与修改原则（实现期必须遵守）

- **沿用优先**：页面一律复用 `src/components/` 现成组件，不平行造轮子；卡片网格统一用 `AnimCard`（`common/Card`），通过 `ordinal` 实现错位入场、`variant` / `gradientBackground` 控制观感。
- **禁止擅自修改**：实现过程中**不允许修改 `src/components` 下的现有组件**（包括补 props、微调样式、修 bug 等）。若现有组件确实无法满足本功能需求，**必须先向你（用户）提出变更方案并评审通过**后方可修改；未经评审不得擅自改动任何现有组件。
- **不足则隔离，不自改**：若某交互现有组件不完全适配，优先通过**本功能专属的薄封装 / 样式处理**解决（例如在页面目录内建 `FeatureCard`、`numericWrapper` 等），而**不修改**现成组件；若确有必要修改现成组件，则回到上一条走评审流程。
- **引入方式**：基础/通用组件走 `@components` barrel（`basic` / `common`）；`KLineChart` 按 `@components/kline/KLineChart` 子路径引入（避免桶 TDZ），`AnimCard` 经 `common/Card` 聚合后由 `@components` 导出。

**需要新实现的 glue（非基础组件，属本功能专属组合/逻辑）：**
1. 页面主体 `EodPickerPage.tsx` 及其子组件组合：`FilterCard`（筛选卡片，组合 `AnimCard`+`HrsInput`+`Switch`+`Modal`）、`SortBar`、`StockCard`（含分时图，复用 `KLineChart`）、`ResultsGrid`（用 `AnimCard` 网格）、`ProgressOverlay`。
2. 本地持久化模块 `apps/hrs-web/src/api/eodPickerStorage.ts`（filters / schemes / recent，照搬 localStorage 逻辑 + `healFilters` + 500ms 防抖，三语 key 走 i18n）。
3. 后端 API 封装 `apps/hrs-web/src/api/eodPicker.ts`（基于 `apiClient`，复用 401/错误/缓存）。
4. 如需，极薄的 numeric input wrapper（复用 `HrsInput`）。

**不新增**：图表组件、基础输入组件、开关组件等通用件——全部走现成 barrel（`@components` 导出 basic/common，其中卡片用 `common/Card/AnimCard`；`KLineChart` 按 `@components/kline/KLineChart` 子路径引入，避免桶 TDZ）。
