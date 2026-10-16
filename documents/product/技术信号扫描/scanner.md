# <a id="技术信号扫描scanner移植方案"></a>技术信号扫描（Scanner）移植方案

> 📝 **方案简述**：本方案将参考项目 stock-dashboard 的「信号扫描」移植到 HermesX，前端落地于 `/discover/scanner` 路由页面（占位页已存在，本次实现）。它确认了参考项目 `Scanner.tsx` + `analysis.ts` 的核心逻辑：股票池 × 信号模板 → 逐只取日 K 算指标 → 命中即出结果，支持取消；规定前端左配置 / 右结果双栏照搬参考实现；后端按「异步任务 + 增量结果 + 协作式取消」提供数据；给出移植对照表、范围裁剪、关键决策与 ADR-001 合规性对照。当前后端 service、endpoint 与前端页面均已落地。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-14

## 方案目录

- [改动日志](#改动日志)
- [参考项目核心逻辑（已从源码确认）](#参考项目核心逻辑已从源码确认)
- [A. 命名与路由（已落地）](#a-命名与路由已落地)
- [B. 前端：照搬参考项目 UI 与交互](#b-前端照搬参考项目-ui-与交互)
- [C. 后端：数据契约](#c-后端数据契约)
- [D. 移植对照表](#d-移植对照表)
- [E. 范围裁剪（未复刻项与原因）](#e-范围裁剪未复刻项与原因)
- [F. 关键决策（已确认，开工基准）](#f-关键决策已确认开工基准)
- [G. 验证](#g-验证)
- [H. 与 ADR-001（后端架构）的合规性对照](#h-与-adr-001后端架构的合规性对照)
- [I. 前端组件复用策略（现成优先）](#i-前端组件复用策略现成优先)

> 参考项目：`https://github.com/chengzuopeng/stock-dashboard`（演示页 `https://chengzuopeng.github.io/stock-dashboard/scanner`）
> 目标：将「信号扫描」功能移植到 HermesX，前端落在 `/discover/scanner` 路由页面。

| 项 | 内容 |
|---|---|
| 关联架构 | `documents/framework/backend_architecture_adr.md`（ADR-001，已采纳） |
| 状态 | 已实施（后端 service + endpoint + 前端页面均已落地，离线单测与页面冒烟通过） |

### <a id="改动日志"></a>改动日志

| 时间 | 版本 | 变更摘要 |
|---|---|---|
| 2026-10-14 | v1.0 | 初版方案 + 落地：参考项目逻辑梳理、前后端设计、数据契约、移植对照表、范围裁剪、关键决策、验证结论、ADR-001 合规对照、组件复用策略 |

---

<a id="参考项目核心逻辑已从源码确认"></a>
## 参考项目核心逻辑（已从源码确认）

- **两个输入维度**：股票池（自选股 / 手选板块 / 榜单 TopN / 涨停·强势池 / 盘口异动池）× 信号模板（8 个，多选）。
- **信号判定**（`analysis.ts: detectSignals`）：取近 1 年日 K（含 MA/MACD/RSI/BOLL 指标），按「最后一根 vs 前一根」的边界穿越判定：
  - MA 金叉 / 死叉：MA5 与 MA10 交叉
  - MACD 金叉 / 死叉：DIF 与 DEA 交叉
  - RSI 超卖 / 超买：RSI6 或 RSI12 低于 30 / 高于 70
  - BOLL 突破上轨 / 跌破下轨：收盘价越过上轨 / 下轨
- **执行**：并发 4（`DEFAULT_SCAN_CONCURRENCY`），`onResult` 逐条增量出结果，进度文案为「阶段 + 已完成/总数」；`AbortController` 取消、离开页面自动中止。
- **UI**：左栏（股票池来源卡 + 信号模板卡 + 开始/取消按钮）/ 右栏（结果列表：名称·代码·命中信号·时间·加自选，点击跳详情页）。

<a id="a-命名与路由已落地"></a>
## A. 命名与路由（已落地）

- `apps/hrs-web/src/router/manifest.ts`：`menuId: 'scanner'` / `routePath: '/discover/scanner'` / `menuPagePath: 'pages/Discover/ScannerPage/ScannerPage'`，`auth: 'protected'`（菜单已登记，无需改动）。
- 页面文件：`apps/hrs-web/src/pages/Discover/ScannerPage/ScannerPage.tsx` + `components/ScannerResultRow.tsx`。
- i18n：`scanner.*` 命名空间，三语（`uiText-zh.ts` / `uiText-zh-Hant.ts` / `uiText-en.ts`）同步；`layout.nav.scanner.title/description` 已更新为「信号扫描」。
- 后端：`src/services/scanner_indicators.py`（信号纯函数）、`src/services/signal_scanner_service.py`（编排）、`api/v1/endpoints/scanner.py`（`/api/v1/scanner`）。

<a id="b-前端照搬参考项目-ui-与交互"></a>
## B. 前端：照搬参考项目 UI 与交互

- **左栏**：股票池来源（TabNav：自选股 / 榜单 TopN / 涨停池）+ 子配置（榜单排序字段 TabNav + TopN 档位按钮组）+ 信号模板卡片网格（8 个，标签 + 说明，点击切换）+ 开始/取消按钮。
- **右栏**：扫描结果卡（标题 + 「N 个触发」计数 + 进度），结果行含名称 / 代码 / 命中信号 Chip / 扫描时间 / 加自选；整行点击跳个股 K 线页。
- **交互差异适配（非照搬）**：参考项目在浏览器内并发取数并逐条 `onResult`；本仓库为后端任务，采用 2s 轮询 + 任务未完成即返回已命中的增量结果，视觉上仍是逐步出结果。
- **取消**：运行中显示「取消扫描」按钮；离开页面（组件卸载）自动请求取消，避免后台跑完上百只股票。
- **持久化**：不做本地持久化（扫描条件为一次性操作，与参考项目一致）。

<a id="c-后端数据契约"></a>
## C. 后端：数据契约

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/scanner/options` | 池来源 / 榜单字段 / TopN / 信号键与默认值（前端不写死契约） |
| POST | `/api/v1/scanner/tasks` | 提交任务 → 202 + `task_id` |
| GET | `/api/v1/scanner/tasks/{id}` | 轮询；运行中即返回增量结果（拍平 `results` / `pool_count` / `scanned` / `cancelled`） |
| POST | `/api/v1/scanner/tasks/{id}/cancel` | 协作式取消，保留已命中结果 |

请求体（snake_case）：`pool_source` / `ranking_field` / `top_n` / `signals` / `watchlist[{code,name}]`；非法取值由服务端回落到默认值。

关键约束：

- 代码统一以**裸码**（`600519`）进出，交易所后缀在入口归一化，避免前端/后端格式漂移。
- 日 K 取 `data_provider/kline`（多源回退 + qfq + 30s TTL），约 250 根（≈1 年）。
- 单只取数失败 fail-open（记 warning，不中断批次）。
- 结果顺序对齐股票池顺序，避免并发完成顺序导致列表跳动。
- 并发固定 4（与 `eod_picker_service` 一致，东财 push2his 对高并发限流严格）。

<a id="d-移植对照表"></a>
## D. 移植对照表

| 参考项目 | HermesX | 差异 |
|---|---|---|
| `services/analysis.ts: scanSignalPool` | `src/services/signal_scanner_service.py: run_signal_scan` | 前端并发 → 后端任务；并发上限同为 4 |
| `detectSignals`（前端算） | `src/services/scanner_indicators.py: detect_signals` | 算法口径一致（MACD/RSI 对齐 `src/stock_analyzer.py`，BOLL 为本仓库新增） |
| `getAllAShareQuotes` / `getZTPool` | `eod_picker_service.get_realtime_quote_snapshot` / `DataFetcherManager.get_limit_up_pool` | 复用既有数据源与回退链 |
| 自选股池（前端 `watchlistStore`） | 前端传入默认自选分组条目（含名称） | 后端不感知用户态，避免鉴权耦合 |
| `AbortController` 取消 | 模块级 `threading.Event` 注册表 + cancel 端点 | 协作式：当前批次后停止，已命中结果保留 |
| `onResult` 逐条回调 | 轮询返回增量结果 | 见 B 节 |
| 结果项跳 `/s/{code}` | 写入 sessionStorage 后跳 `/stock/kline` | 对齐 EOD Picker 既有跳转契约 |

<a id="e-范围裁剪未复刻项与原因"></a>
## E. 范围裁剪（未复刻项与原因）

| 参考项 | 状态 | 原因 |
|---|---|---|
| 手选板块（行业/概念成分股） | 未复刻 | 本仓库 `api/v1/endpoints/sector.py` 成分股为空实现，接入需新增数据源 |
| 涨停池子类（强势 / 炸板 / 跌停 / 次新） | 未复刻 | 仅 `get_limit_up_pool` 可用，其余需扩展 akshare 接口 |
| 盘口异动池 | 未复刻 | 本仓库无对应数据源 |
| 板块成分 / 异动相关的 UI Tab | 未渲染 | 与裁剪项保持一致，避免出现无数据的入口 |

后续如补齐数据源，只需在 `POOL_SOURCES` 增加枚举 + 前端 i18n 文案 + 池解析分支，前端选项契约由 `/options` 驱动。

<a id="f-关键决策已确认开工基准"></a>
## F. 关键决策（已确认，开工基准）

1. **股票池范围**：先做自选股 / 榜单 TopN / 涨停池三个有现成数据源的池，其余数据源就绪后再扩展。
2. **结果呈现**：轮询 + 增量结果（不扩展通用 SSE 载荷契约，避免污染 RunFlowEvent）。
3. **取消**：scanner 自建 `threading.Event` 注册表 + cancel 端点，不修改通用 `task_queue`。
4. **不新增数据源与三方依赖**：只复用 `data_provider` 既有能力。
5. **不修改共享组件**：页面内组合 `AnimCard / TabNav / Chip / HrsButton / EmptyState / PageHeader`。

<a id="g-验证"></a>
## G. 验证

| 项 | 结果 |
|---|---|
| 离线单测 `tests/test_signal_scanner_service.py`（20 例） | 通过（指标判定 / 请求规整 / 三种池解析 / 并发与进度 / 取消保留部分结果 / 端点路径契约） |
| 既有回归 `tests/test_eod_picker_service.py`（13 例） | 通过 |
| 页面冒烟 `src/pages/__tests__/ScannerPage.test.tsx`（4 例） | 通过（提交 → 轮询增量 → 渲染、未选信号禁用、取消请求、加自选与跳转） |
| 前端 lint / `vite build` | 通过（`ScannerPage` / `ScannerResultRow` 产出独立 chunk） |
| 后端接口级联调（本地 8001 免鉴权实例） | `options` 正常；涨停池 Top20 命中 17；榜单 Top300 取消后 `scanned=115 / match_count=16 / cancelled=true` |

未验证项：浏览器真实点击（环境无可用浏览器自动化 CLI），以 jsdom 页面冒烟 + 接口级联调替代。

<a id="h-与-adr-001后端架构的合规性对照"></a>
## H. 与 ADR-001（后端架构）的合规性对照

| ADR-001 要求 | 本方案 |
|---|---|
| 数据源访问经 `data_provider` 统一封装 | 复用 `data_provider/kline`、`DataFetcherManager`、`eod_picker_service`，未直连三方 SDK |
| 业务逻辑在 `src/services`，API 层只做编排 | 信号判定与扫描编排在 `src/services`，`api/v1/endpoints/scanner.py` 仅做请求校验与任务挂载 |
| 异步长任务走任务队列 + 进度上报 | `task_queue.submit_background_task` + `update_task_progress` |
| 前端不写死业务契约 | 池来源 / 信号键 / TopN 由 `/options` 下发 |
| 多语言三语同步 | `scanner.*` 三语齐备，类型由 `UiTextKey` 强制对齐 |

<a id="i-前端组件复用策略现成优先"></a>
## I. 前端组件复用策略（现成优先）

| 用途 | 组件 | 引入路径 |
|---|---|---|
| 分区卡片 | `AnimCard` | `@components` |
| 池来源 / 排序字段切换 | `TabNav` | `@components` |
| 命中信号标签 | `Chip` | `@components` |
| 开始 / 取消 / TopN | `HrsButton` | `@components` |
| 页头 / 空态 | `PageHeader` / `EmptyState` | `@components/layout/PageLayout/PageHeader` / `@components/basic/EmptyState` |

组件使用与修改原则：

- 不修改任何共享组件；样式用 Tailwind + `hsl(var(--*))` 主题变量，不新增 scss。
- 信号模板为「标签 + 说明」双行卡片，`HrsButton` 无法呈现，故保留原生 `button`（与 EOD Picker 圆形 CTA 的处理一致）。
- 加自选按钮外层包裹 `div` 阻止冒泡（`HrsButton` 的 `onClick` 桥接 `onPress`，不可在回调内 `stopPropagation`）。
