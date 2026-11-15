# <a id="个股k线功能持久化方案"></a>个股 K 线功能持久化方案

> 📝 **方案简述**：为个股 K 线页（`/stock/kline`）定义「当前选中股票」在**刷新、跨路由往返、清空**三类事件下的存活规则。核心是把「选中股票」收敛为**唯一真源**：新建 `stores/StockKLine.ts`，以 zustand store + `@utils/storage` 逻辑键 `stockKLine`（浏览器实际键 `hrs-state-stockKLine`）持久化 `{ code, name }`（类型对齐 `types/stock.ts` 的 `StockRef`），并在该文件内实现增 / 改 / 删 API；URL `?stockCode=` 降级为「外部注入 + 可分享」的镜像，KeepAlive 实例只承载可重建的渲染态。同时配套改造缓存键、`KLineChart` 尺寸监听与全部跳转入口。方案覆盖产品侧确认的 7 个场景，逐条给出验收矩阵。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-13
>
> ✅ **状态**：**已实施（2026-11-13）**。产品侧确认「只看持久化」规则后已按本文落地，落地与验证结果见 [§9](#sec-9)；[§2](#sec-2) 记录的是改造前的问题背景，不再代表当前实现。

## 目录

- [一、Context 与场景契约](#sec-1)
  - [1.1 产品侧 7 个场景](#sec-1-1)
  - [1.2 由事件推导出的硬约束](#sec-1-2)
- [二、现状问题：一个状态、四份副本](#sec-2)
  - [2.1 副本清单](#sec-2-1)
  - [2.2 逐场景失效归因](#sec-2-2)
- [三、设计：单一真源（SSOT）](#sec-3)
  - [3.1 核心决策](#sec-3-1)
  - [3.2 三层职责](#sec-3-2)
  - [3.3 状态结构与持久化键](#sec-3-3)
  - [3.4 Store API：增 / 改 / 删](#sec-3-4)
- [四、读写协议（状态机）](#sec-4)
  - [4.1 唯一判定规则：看持久化](#sec-4-1)
  - [4.2 唯一写入口：select / clear](#sec-4-2)
  - [4.3 入口与参数协议](#sec-4-3)
  - [4.4 正反清单](#sec-4-4)
- [五、配套地基改动](#sec-5)
  - [5.1 KeepAlive 缓存键与 query 解耦](#sec-5-1)
  - [5.2 URL 只做单向注入](#sec-5-2)
  - [5.3 KLineChart 容器尺寸监听](#sec-5-3)
  - [5.4 与 LRU 淘汰的关系](#sec-5-4)
- [六、7 场景验收矩阵](#sec-6)
- [七、与既有文档的关系](#sec-7)
- [八、文件变更清单](#sec-8)
- [九、验证](#sec-9)
- [十、兼容性与风险](#sec-10)
  - [10.1 已接受的取舍](#sec-10-1)
  - [10.2 风险与缓解](#sec-10-2)

<a id="sec-1"></a>

## 一、Context 与场景契约

<a id="sec-1-1"></a>

### 1.1 产品侧 7 个场景

「中科曙光」在下文代表任一具体股票；「展示最近搜索股票列表」即未选中股票的搜索引导态，语义见《个股最近搜索.md》§2「显示时机」。

| # | 起点 | 操作序列 | 期望结果 |
| --- | --- | --- | --- |
| 1 | 外部入口（自选股 / 顶栏 / Scanner / 最近搜索等）搜索「中科曙光」跳转 `/stock/kline` | **刷新页面** | 保留「中科曙光」的 K 线图与信息 |
| 2 | 同 1 | **删除股票搜索栏内容** | 正常展示「最近搜索股票列表」 |
| 3 | 直接进入 `/stock/kline` | 在搜索栏搜索「中科曙光」→ **刷新页面** | 保留「中科曙光」的 K 线图与信息 |
| 4 | 直接进入 `/stock/kline` | 搜索「中科曙光」→ **跳转其他页面 → 再跳回** | 保留「中科曙光」的 K 线图与信息 |
| 5 | 直接进入 `/stock/kline` | 搜索「中科曙光」→ **删除搜索栏内容** | 正常展示「最近搜索股票列表」 |
| 6 | 同 1 | 删除搜索栏内容 → **跳转其他页面 → 再跳回** | 仍展示「最近搜索股票列表」（清空状态不得复活） |
| 7 | 同 1 | **跳转其他页面 → 再跳回** | 保留「中科曙光」的 K 线图与信息 |

<a id="sec-1-2"></a>

### 1.2 由事件推导出的硬约束

7 个场景只围绕**一个状态**：`StockRef | null`，即 `{ code, name }` 或「未选中」（`null` ⇒ 展示最近搜索列表）。类型定义见 [§3.3](#sec-3-3)。三类事件对它的要求互不相同：

| 事件 | 涉及场景 | 推导出的硬约束 |
| --- | --- | --- |
| **刷新** | 1、3 | 整页重载会清空全部内存 ⇒ 真源必须**可持久化恢复**（URL / sessionStorage，不能只靠组件内存） |
| **跳走 → 跳回** | 4、6、7 | 「跳回」的链接是**固定路径 `/stock/kline`、不带任何参数**（侧边栏 `NavLink` 的 `to`、`SettingsPage` 的 `navigate('/stock/kline')`）⇒ 真源**不能依赖 URL 才存在** |
| **清空** | 2、5、6 | 删除后，在**刷新与往返之后仍须是「未选中」**（场景 6）⇒ 清空必须擦掉**所有副本**，不能留一份在刷新时把股票「复活」 |

**结论**：必须存在**单一真源（SSOT）**，且它同时满足「刷新可恢复」+「不随路由变化」+「可被显式删除」。任何"多副本 + 事后同步"的写法都会在组合事件下失配。

**核心判定（产品侧确认）**：页面只认「持久化里有没有值」——有值就恢复该股票，无值就展示「最近搜索股票列表」；**不区分进入方式**（刷新、跳走跳回、菜单点击、手动敲网址一律同规则）。详见 [§4.1](#sec-4-1)。

<a id="sec-2"></a>

## 二、现状问题：一个状态、四份副本

<a id="sec-2-1"></a>

### 2.1 副本清单

| # | 副本 | 位置 | 说明 |
| --- | --- | --- | --- |
| 1 | URL `?stockCode=` | `jump2Kline.md` §2 协议 | 参数名固定 `stockCode`，页面由 `useSearchParams` 读取 |
| 2 | `location.state` | 各跳转点 `navigate('/stock/kline', { state: { stockCode } })` | React Router v7 实际写入 `window.history.state.usr`，**同标签页刷新会保留**（`createBrowserLocation` 启动时从 `globalHistory.state.usr` 读回） |
| 3 | 组件内存 `stockCode` | `pages/Stock/StockKLinePage/StockKLinePage.tsx` | `useState('')`，无持久化 |
| 4 | KeepAlive 实例 | `components/layout/KeepAliveOutlet.tsx` | `activeCacheKey = pathname + search + hash`；带参/不带参是**两个实例**，各自一份 state 与 ECharts 画布 |

此外，当前实现还存在三处与既有文档不一致的偏离：

- 页内搜索**不写 URL**（`handleSearchSubmit` 注释明确「页内搜索不写 `?stockCode=`」），只改内存 ⇒ 刷新必丢。
- 外部入口改用 `location.state` 传参，与《jump2Kline.md》§2 的 `?stockCode=` 协议不一致。
- 《个股K线功能设计方案.md》§6.4 描述的 `PageStateStore.kline` 切片**已从代码移除**（`stores/PageStateStore.tsx` 的 `PageStateStore` 接口无 `kline` 字段，恢复逻辑注释亦标注「已移除的 kline 分区」）；页面状态退回纯组件内存，会话级持久化能力退化。**本方案不恢复该切片**，改为新建独立的 `StockKLine.ts`（见 [§3.1](#sec-3-1)）。

<a id="sec-2-2"></a>

### 2.2 逐场景失效归因

| 场景 | 当前结果 | 根因 |
| --- | --- | --- |
| 1 | 可能保留（依赖 `history.state.usr` 是否随刷新保留） | 状态靠"隐式副作用"而非契约，不可依赖 |
| 2 | **清空后刷新会复活股票** | `onClear` 只清内存 + 删 URL 参数，**未清 `location.state`**；`history.state.usr.stockCode` 刷新后被读回 |
| 3 | **丢失**（回到最近搜索列表） | 页内搜索只写内存，刷新后内存重建 |
| 4 / 7 | **易错乱** | 跳回是无参数固定路径；缓存键含 `search` ⇒ 有参/无参切到不同实例。改 URL 即换实例，会复活旧实例的陈旧行情；旧实例 ECharts 曾在隐藏/塌缩宽度下初始化，`KLineChart` 只监听 `window resize`，图表被压窄 |
| 5 | 清空当下正常 | 但依赖场景 2 的同一条路径，清空不彻底 |
| 6 | **易复活** | 同场景 2：往返过程中残留的 state / 另一缓存实例会把股票带回 |

> 历史上用 `window.history.replaceState` 直接改地址栏的尝试亦不可取：它不通知 React Router，`useLocation().search` 与真实 URL 失同步，后续任何 `setSearchParams` / `navigate` 都会以陈旧 search 为基底把参数加回来。**本方案不采用任何绕过路由层的地址栏改写。**

<a id="sec-3"></a>

## 三、设计：单一真源（SSOT）

<a id="sec-3-1"></a>

### 3.1 核心决策

**规定**：在 `apps/hrs-web/src/stores` **新建 `StockKLine.ts`**，作为「当前选中股票」的唯一真源；持久化逻辑**全部封装在该文件内**，调用方不直接接触浏览器存储。URL `?stockCode=` 降级为「外部注入 + 可分享」的镜像；KeepAlive 实例只承载**可重建的渲染态**。组件内不再持有独立的 `stockCode` state，一律从该 store 派生。

**Why**：

- 不用 URL 当真源 —— 场景 4/7 的「跳回」必然丢失参数，单靠 URL 无法成立。
- 不用组件内存当真源 —— 场景 1/3 的刷新会清空内存。
- 不用 `location.state` —— 它藏在 `history.state.usr`，清空时须额外擦除、跳走跳回时条目残留易误注入，且与 URL 构成双副本，正是「刷新复活」的直接来源。
- **不用 `PageStateStore` 的 `kline` 切片** —— 该切片是「所有页面状态的集合」，恢复逻辑按分区逐项合并、Context 更新会触发全子树重渲染；K 线页的选中股票是**高频、独立、需要明确删除语义**的状态，用专用 store 更内聚，且便于单独测试与单独清理。
- `sessionStorage`（标签页会话级）同时满足「刷新可恢复」与「不随路由变化」，且关标签页自然清空，语义恰好匹配「本标签页的 K 线页当前看哪只股票」。

**How to apply**：全项目只有 `select(ref)` 与 `clear()` 两个业务写入口，底层统一经 `StockKLine.ts` 暴露的 `set / update / remove`；所有入口、页内搜索、清空动作都不得直接改 URL / 存储 / 本地 state。

<a id="sec-3-2"></a>

### 3.2 三层职责

| 层 | 内容 | 写入方 | 生命周期 |
| --- | --- | --- | --- |
| **L1 真源** `stores/StockKLine.ts`（`stockKLine` 键） | `StockRef \| null` = `{ code, name }` 或「未选中」 | `set / update / remove` | 标签页会话；刷新恢复、路由切换不变、关标签页清空、可显式删除 |
| **L2 渲染态** | `stockInfo` / `klineData` / `period` / `searchDisplayLabel` / ECharts 实例 / 请求序号 | 由 L1 的 `code` 变化触发 `loadStockData` | 跟随 KeepAlive 实例；实例销毁后按真源重新拉取 |
| **L3 URL 镜像** | `?stockCode=<code>` | 由 L1 同步（`setSearchParams(..., { replace: true })`） | 外部深链、分享、地址栏可见 |

**`name` 的作用**：L1 同时持久化名称，使刷新 / 跳回后**搜索框展示标签可立即回填**，无需等行情接口或股票索引异步返回；行情加载成功后仍以 `stockInfo.name` 为准覆盖（见 [§4.2](#sec-4-2)），保证标签与行情头一致。

**保留的含义**：场景中「保留 K 线图与信息」指**保留选中意图与最终呈现**。若 KeepAlive 实例仍在，L2 直接复用、无请求；若实例已被淘汰或发生刷新，按 L1 的 `code` 重新拉取（允许短暂加载态），结果一致。

<a id="sec-3-3"></a>

### 3.3 状态结构与持久化键

**规定**：持久化值是一个对象，**只有 `code` 与 `name` 两个字段**，类型直接复用 `types/stock.ts` 的 `StockRef`，不另造同名字段，保证与领域类型单一真源对齐。

```ts
// types/stock.ts:69-74 —— 三层模型 L1「最小标识」
export interface StockRef {
  /** 股票代码（如 600519） */
  code: string;
  /** 股票名称（中文） */
  name: string;   // ← 与 @stock.ts:73 对齐：必填 string
}

// stores/StockKLine.ts
import type { StockRef } from '../types/stock';

/** 选中态：null = 未选中 / 已清空 */
type StockKLineSelection = StockRef | null;
```

**规定**：持久化**逻辑键名**固定为 **`stockKLine`**，介质 `sessionStorage`；经项目 `@utils/storage` 访问后，浏览器中的**实际键名**为 `hrs-state-stockKLine`（前缀来自 `SESSION_STORAGE_PREFIX`），此点已确认接受。值为该对象的 JSON 序列化结果。

```ts
// 会话键；@utils/storage 会自动追加 hrs-state- 前缀
const STOCK_KLINE_SESSION_KEY = 'stockKLine';

// 值示例
{ "code": "603019", "name": "中科曙光" }
```

| 项 | 约定 |
| --- | --- |
| 逻辑键名 | `stockKLine`（传给 `@utils/storage` 的 key） |
| 浏览器实际键名 | `hrs-state-stockKLine` |
| 介质 | `sessionStorage`（标签页会话级） |
| 值 | `{ code: string, name: string }`（`StockRef`）；`name` 未知时写 `''`，不得为 `undefined` |
| 「未选中」 | **键不存在**（`removeStorageItem` 删除），store 内存置 `null` |
| 读写方式 | `StockKLine.ts` 内统一调用 `@utils/storage` 的 `getStorageItem<T> / setStorageItem / removeStorageItem`，均传 `'session'`；工具已内建前缀、JSON 序列化与 `try/catch` 兜底（私有模式 / 配额 / 无 `window`） |
| 与项目规范统一 | 带前缀后该键**纳入** `clearHRSStorage('session')` 批量清理范围，与其他会话态一起管理 |

**持久化原则：只持久化「选中意图」，不持久化「数据」。**

| 字段 | 是否持久化 | 理由 |
| --- | --- | --- |
| `code` | ✅ | 真源主键，驱动数据加载；须能区分「未选中」与「选中但加载失败」 |
| `name` | ✅ | 刷新 / 跳回后立即回填搜索框标签，避免标签空白闪烁 |
| `period` | ❌ | 属 L2 渲染态；实例在则保留，实例销毁 / 刷新后重置 `daily`（取舍见 [§10.1](#sec-10-1)） |
| `stockInfo` / `klineData` / `klineSource` | ❌ | 可由 `code + period` 重新拉取 |
| `searchDisplayLabel` | ❌ | 由 L1 的 `name` + `stockInfo` / 股票索引推导（《jump2Kline.md》§3.2） |
| `searchDraft`（输入草稿） | ❌ | 纯 UI 缓冲 |

**实现要点**：`StockKLine.ts` 在 store 初始化时用 `getStorageItem<unknown>(STOCK_KLINE_SESSION_KEY, 'session')` 恢复（工具内已完成 `JSON.parse`）；取值为 `null` 或结构不合法（缺 `code` / `name` 非 string）时回退为 `null` 且**不回写脏值**，历史残留缺 `name` 时按 `''` 兼容。

<a id="sec-3-4"></a>

### 3.4 Store API：增 / 改 / 删

**规定**：`StockKLine.ts` 必须对外提供**读取、新增/整体覆盖、局部更新、删除**四类能力，且每个写操作同时更新「内存 store」与「sessionStorage」，两者恒一致。实现采用项目既有 zustand（`import { create } from 'zustand'`，与 `stockPoolStore.ts` 一致）。

| API | 签名 | 语义 | 持久化动作 |
| --- | --- | --- | --- |
| Hook | `useStockKLineStore(selector?)` | 组件订阅当前 `StockRef \| null` | 初始化时 `getStorageItem<unknown>(STOCK_KLINE_SESSION_KEY, 'session')` 恢复 |
| 读 | `getStockKLineInfo(): StockRef \| null` | 非 Hook 场景（回调 / effect）同步读取 | 读内存 store |
| **增 / 覆盖** | `setStockKLineInfo(stockToSelect: StockRef): void` | 整体写入一个新对象（新增或换股） | `setStorageItem(STOCK_KLINE_SESSION_KEY, stockToSelect, 'session')` |
| **局部更新** | `updateStockKLineInfo(stockFieldsToUpdate: Partial<StockRef>): void` | 合并更新已有值（如行情返回后补 `name`、修正 `code`）；**当前无值时忽略，不创建半成品对象** | 读-合并-`setStorageItem`；只接受 `code` / `name` |
| **删除** | `removeStockKLineInfo(): void` | 删除选中态（清空搜索框时调用） | `removeStorageItem(STOCK_KLINE_SESSION_KEY, 'session')` + store 置 `null` |

**Why（单一写入口）**：所有写路径都经过这三个 API，才能保证「内存与持久化不漂移」；若允许调用方直接 `setStorageItem` 或绕过 store 写 `hrs-state-stockKLine`，场景 2/6 的「清空后复活」会再次出现。

**How to apply**：

```ts
// 页内搜索提交 / 外部入口注入
setStockKLineInfo({ code: '603019', name: '中科曙光' });

// 行情返回后补全名称（name 未知时先写了 ''）
updateStockKLineInfo({ name: stockInfo.name });

// 点击搜索框清除按钮
removeStockKLineInfo();

// 组件内读取
const stockKLineSelected = useStockKLineStore((klineStore) => klineStore.stockKLineSelected);
```

**约束**：

- 【强制】`setStockKLineInfo` 的入参必须是完整 `StockRef`；`code` 需先经 `normalizeStockCode` / `.split('.')[0]` 归一为纯代码。
- 【强制】`updateStockKLineInfo` 不得用于「从无到有」创建，避免写入 `{ name }` 缺少 `code` 的残缺对象。
- 【强制】`removeStockKLineInfo` 是**唯一**的删除入口；`clear()` 与未来的「退出登录清理」都调用它。
- 【推荐】`stores/index.ts` 追加 `export * from './StockKLine';`，与目录内其他 store 的 barrel 导出惯例保持一致。

<a id="sec-4"></a>

## 四、读写协议（状态机）

<a id="sec-4-1"></a>

### 4.1 唯一判定规则：看持久化

**规定**：页面渲染**只由「持久化里有没有值」决定**，不区分用户是怎么进来的（刷新、跳走跳回、菜单点击、手动敲网址，一律同规则）。

| 持久化（`hrs-state-stockKLine`） | 页面呈现 |
| --- | --- |
| 有 `{ code, name }` | 恢复并显示该股票 ——「出去转一圈回来」仍是中科曙光 |
| 无（键不存在 / 解析后为 `null`） | 展示「最近搜索股票列表」——「重新开一张白纸」 |

**进入页面时唯一的前置动作**：若 URL 带 `?stockCode=`，先用 `select()` 把这次外部意图**写入**持久化（外部入口 / 深链 / 分享链接），此后判定仍回到上表；`name` 暂写 `''`，行情返回后由 `update` 补全。URL 不带参数时**不写入、也不删除**。

```text
进入 /stock/kline：
  URL 带 ?stockCode= → select({ code: normalize(code), name: '' })   // 先补齐持久化
  之后一律判定持久化：
    有值 → 显示该股票
    无值 → 显示「最近搜索股票列表」
```

- 【强制】**URL 无参数时绝不动 L1**。侧边栏「跳回」是无参数固定路径，若把「无参数」解释为「清空」，场景 4/7 的股票必丢。
- 【强制】「清空」= `removeStockKLineInfo()` 删除键；删完后刷新、跳走跳回、手敲网址进来都仍是「无值」→ 一直是列表（场景 2/5/6）。
- URL 有参数且与当前 `code` 不同：视为一次新的显式意图，`select()` 覆盖 L1；相同则同值去重，不重复请求（《jump2Kline.md》§3.1）。
- L1 有值时 `name` 立即回填搜索框展示标签，`code` 驱动 `loadStockData`。

<a id="sec-4-2"></a>

### 4.2 唯一写入口：select / clear

```text
select(stockToSelect: StockRef):               // 外部入口注入、页内搜索提交
  setStockKLineInfo(stockToSelect)                // 增 / 覆盖：L1 真源 + sessionStorage
  setSearchParams({ stockCode: stockToSelect.code }, { replace: true })   // 同步 L3 镜像；replace 不污染历史
  loadStockData(stockToSelect.code)           // 由 L1.code 变化驱动
    └ 成功且 stockToSelect.name 为空 / 与行情名不一致 → updateStockKLineInfo({ name: stockInfo.name })

clear():                                       // 点击搜索框清除按钮
  removeStockKLineInfo()                          // 删除：store 置 null + removeStorageItem('stockKLine','session')
  setSearchParams({}, { replace: true })       // 擦掉 L3 → 刷新不会按参数重载
  复位 L2：stockInfo=null / klineData=[] / 展示标签='' / 作废在途请求序号
  不发起行情请求、不写最近搜索
```

**Why（`replace: true`）**：页内连续搜索 A→B→C 不应在浏览器历史里堆三条 K 线记录；「后退」应直接回到进入 K 线页之前的页面。同时 `replace` 会由 React Router 重写 `history.state`，顺带清掉旧版本可能残留的 `usr.stockCode`，无需再单独处理 `location.state`。

**读取侧彻底不再消费 `location.state`**：既有的 `history.state` 残留不会被任何 effect 读取，因此场景 2/6 的「刷新复活」自动消失，无需 `navigate(..., { state: null })` 之类的补偿动作。

> 与《个股最近搜索.md》§2.1 的衔接：`select()` 对应「显式搜索 / 显式跳转」两类记录时机，照常落库；`clear()` 不属于记录时机，且清空不二次请求。「显示时机」仍以 `!stockInfo` 渲染列表，语义不变。

<a id="sec-4-3"></a>

### 4.3 入口与参数协议

**规定**：参数名**沿用 `stockCode`**（《jump2Kline.md》§2.1 强制），不改为 `code` 或其他名称。理由：协议名本身不是缺陷，改名会破坏外部书签、分享链接与既有测试，而无任何收益；本方案改变的是**该参数的角色定位**（从「真源」降级为「注入 + 镜像」），不是它的拼写。注意区分：URL 参数名是 `stockCode`，而持久化对象里的字段名是 `code`（对齐 `StockRef`）。

**规定**：全部「携带具体股票跳转 K 线」的入口统一回到查询串写法，**废弃 `location.state` 传参**：

```ts
// ✅ 统一写法
navigate(`/stock/kline?stockCode=${encodeURIComponent(normalizeStockCode(code))}`);

// ❌ 废弃：state 藏在 history.state.usr，清空难擦、易双副本
navigate('/stock/kline', { state: { stockCode: code } });
```

**规定**：普通 `<a href>`（`stockMetricViewColumns.tsx` 的 `buildStockKlinePath`）本来就是查询串，保持不变——它承担「新标签页打开 / 复制链接分享」场景，天然无法携带 SPA state。

**规定**：页内搜索 `handleSearchSubmit` 改为调用 `select({ code: resolvedCode, name })`，其中 `name` 取自搜索接口 / 自动补全结果（无名称时传 `''`，由 [§4.2](#sec-4-2) 的 `update` 补全）；不再只 `setStockCode(resolvedCode)`。这是场景 3 能成立的前提。

**规定**：无具体股票的通用入口（设置页「查看股票数据」`navigate('/stock/kline')`）继续允许不带参数，按 [§4.1](#sec-4-1) 的唯一判定走（有持久化则恢复、无则列表），属《jump2Kline.md》§3.3 的合理例外。

<a id="sec-4-4"></a>

### 4.4 正反清单

| 做 / 不做 | 说明 |
| --- | --- |
| ✅ 所有写操作经 `select()` / `clear()`，底层只调 `StockKLine.ts` 的 `set / update / remove` | 单一真源，内存与 `sessionStorage` 恒一致 |
| ✅ 持久化值严格为 `{ code, name }`，类型复用 `StockRef` | 与 `types/stock.ts` 单一真源对齐 |
| ✅ `setSearchParams(..., { replace: true })` | 同步 URL 镜像且不污染历史 |
| ✅ URL 无参数时沿用 L1 | 场景 4/7 的关键 |
| ✅ 清空调用 `removeStockKLineInfo()` 删除 `stockKLine` 键 | 刷新 / 跳回都不复活 |
| ✅ 数据加载只认 L1 的 `code`，不认展示标签 / 输入草稿 | 与《jump2Kline.md》§3.2 一致 |
| ❌ `location.state` 传 `stockCode` | 清空难擦、跳回残留、双副本 |
| ❌ `window.history.replaceState` 改地址栏 | 与 React Router 失同步 |
| ❌ 调用方直接 `setStorageItem` / 绕过 store 写 `hrs-state-stockKLine` | 造成副本漂移，清空后可能复活 |
| ❌ 页内搜索只改组件内存 | 刷新必丢 |
| ❌ 把 URL 无参数解释为「清空」 | 会破坏跨路由往返保留 |
| ❌ 持久化 `stockInfo` / `klineData` / `period` / 展示标签 | 可重建 / 可推导，属 L2 |
| ❌ 把 `name` 写成 `undefined` / 可选字段 | `StockRef.name` 是必填 `string` |

<a id="sec-5"></a>

## 五、配套地基改动

<a id="sec-5-1"></a>

### 5.1 KeepAlive 缓存键与 query 解耦

**规定**：`router/keepAliveConfig.ts` 新增**通用**的「参与缓存键的 query 白名单」配置；`components/layout/KeepAliveOutlet.tsx` 按配置计算 `activeCacheKey`，不再无条件使用 `pathname + search + hash`。

```ts
interface KeepAliveConfig {
  // …既有 exclude / include / maxAliveTime / maxCacheSize
  /** 各路由「参与缓存键」的 query 参数白名单。
   *  未声明的路由 = 全部参与（保持既有语义）；
   *  [] = 该路由完全忽略 search/hash，仅按 pathname 缓存。 */
  cacheKeyParams: Record<string, string[]>;
}

// /stock/kline：query 仅作一次性深链提示，不参与缓存键
cacheKeyParams: { '/stock/kline': [] };
```

**Why**：写 / 删 `?stockCode=` 属于 L3 镜像同步，语义上**不是换页面**。若缓存键仍含 `search`，每次 `select()` / `clear()` 都会切换 KeepAlive 实例，导致 L2 渲染态被换出（陈旧行情）与 ECharts 塌缩宽度重绘（窄图）。忽略 `search` 后，同 pathname 恒为同一实例，`clear()` 的复位直接作用在可见实例上。

**How to apply**：`activeCacheKey` 计算规则 = 命中 `cacheKeyParams` 时，仅取白名单内的 query 参数按固定顺序拼入键（`/stock/kline` 为空 ⇒ 仅 `pathname`）；未命中时沿用 `pathname + search + hash`。`hash` 对声明了白名单的路由一并不参与。

<a id="sec-5-2"></a>

### 5.2 URL 只做单向注入

**规定**：读取侧 effect 只在 URL 出现**新的非空 `stockCode`** 时调用 `select()`；参数消失时**不做任何事**（清空由 `clear()` 显式负责）。禁止把 L1 写成 `searchParams.get('stockCode')` 之类的双向派生。

**Why**：否则侧边栏「跳回」（URL 无参数）会把 L1 冲成 `null`，场景 4/7 失效。

<a id="sec-5-3"></a>

### 5.3 KLineChart 容器尺寸监听

**规定**：`components/kline/KLineChart.tsx` 除现有 `window.addEventListener('resize', …)` 外，为图表容器增加 `ResizeObserver`，尺寸变化时调用 `chart.resize()`，卸载时 `disconnect()`。

**Why**：当前仅监听窗口 resize，容器从 KeepAlive 隐藏态变可见、或自身宽度变化时不会重绘，是「图表被压窄」的直接成因。本方案已通过缓存键改造避免实例切换，此项作为**防御层**，保证未来任何隐藏/显示场景都不再出现窄图。

**How to apply**：`setupTests.ts` 已有 `ResizeObserverMock` 空实现，单测无需额外处理；新增用例可直接断言回调被注册。

<a id="sec-5-4"></a>

### 5.4 与 LRU 淘汰的关系

`KEEP_ALIVE_CONFIG.maxCacheSize = 8` 会淘汰最久未用实例。本方案**不依赖实例存活**：实例被淘汰后重新挂载时，`code` 从 L1（`stockKLine` 键）恢复并重新加载数据，场景 4/7 依旧成立（仅多一次请求）。因此**无需**为该路由做 pin / 免淘汰，也不必放大 `maxCacheSize`。这是「真源外置」相比「靠实例内存保存选中股票」更健壮之处。

<a id="sec-6"></a>

## 六、7 场景验收矩阵

| # | 操作序列 | 期望 | 由哪条机制保证 |
| --- | --- | --- | --- |
| 1 | 外部入口 `?stockCode=中科曙光` → 刷新 | 保留 | 注入写 `stockKLine`（sessionStorage 持久化 `{code,name}`）；刷新后 URL 仍在，同值去重；`name` 立即回填标签 |
| 2 | 外部入口 → 清空 | 最近搜索列表 | `removeStockKLineInfo()` 删键 + 擦 URL + 复位 L2；不再读取 `location.state` |
| 3 | 直接进 → 页内搜「中科曙光」→ 刷新 | 保留 | 页内搜索走 `select()` 写 `stockKLine` + URL；刷新由 L1 / URL 恢复 |
| 4 | 直接进 → 页内搜 → 跳走 → 跳回 | 保留 | 跳回 URL 无参数 ⇒「无参数不清 L1」+ L1 会话级持久化；实例在则复用 L2，否则按 L1 重载 |
| 5 | 直接进 → 页内搜 → 清空 | 最近搜索列表 | `clear()` → `removeStockKLineInfo()` |
| 6 | 外部入口 → 清空 → 跳走 → 跳回 | 最近搜索列表 | `stockKLine` 键已删除、URL 无参数不注入、`history.state` 不被消费 ⇒ 不复活 |
| 7 | 外部入口 → 跳走 → 跳回 | 保留 | 同 4 |

**补充验收**（本方案对既有缺陷与新增能力的回归）：

- 清空后**刷新**仍为列表，且 `getStorageItem('stockKLine', 'session') === null`（浏览器键 `hrs-state-stockKLine` 已不存在）。
- 选中态下该键解析后严格等于 `{ code, name }`，无多余字段。
- 清空过程中不切换 KeepAlive 实例；图表在清空 / 往返 / 隐藏后始终保持完整宽度。
- 清空不产生行情请求、不新增最近搜索记录。
- 外部入口只有 `code` 时，行情返回后 `name` 被 `update` 补全，刷新后标签直接显示名称。

<a id="sec-7"></a>

## 七、与既有文档的关系

| 文档 | 关系 | 后续需同步的内容 |
| --- | --- | --- |
| 《jump2Kline.md》 | **协议沿用、定位调整** | `?stockCode=` 参数名与归一规则不变（§2）；明确 URL 不再是真源而是「注入 + 镜像」；§3.2 补充「展示标签可由 `stockKLine.name` 立即回填，行情返回后仍以行情名为准」；§4 入口清单补齐涨跌停面板、最近搜索卡片、指标视图 navigate；§7 说明废弃 `location.state` 写法 |
| 《个股K线功能设计方案.md》 | **§6.4 被本方案替代** | 标注 `PageStateStore.kline` 切片已被移除且**不再恢复**；「全部状态收敛于 `pageState` 切片」「只占用 `hrs-state-pageState` 一个对象键」两条改为「选中股票收敛于独立 `stores/StockKLine.ts`，键 `stockKLine`」；「周期为会话级」改为「周期属实例态，刷新重置 `1m`（分时）」 |
| 《个股最近搜索.md》 | **语义不变** | §2.1 记录时机（显式搜索 / 显式跳转记录，隐式重载不记录）与 §2「显示时机」保持；补充说明 `select()` / `clear()` 与记录时机的对应关系 |
| 《K线数据加载策略优化方案》《K线图数据接口获取说明》 | 不涉及 | 数据加载链路与接口不变 |
| ADR-002（路由缓存设计基准） | 扩展 | 记录「缓存键 query 白名单」这一新增策略 |

> 本文为新增方案文档，主体设计已实施；上表列出的**既有文档同步改动**中，《个股K线功能设计方案.md》§6.4 已于 2026-11-15 完成同步（选中态收敛于独立 `stores/StockKLine.ts`，默认周期 `1m`），与本文一致；其余条目不影响本次实现的运行契约。

<a id="sec-8"></a>

## 八、文件变更清单

**新增**

| 文件 | 内容 |
| --- | --- |
| `stores/StockKLine.ts` | **本方案核心**：zustand store + `@utils/storage` 逻辑键 `stockKLine`（实际 `hrs-state-stockKLine`）+ `{ code, name }`（`StockRef`）+ `set / update / remove / get` API，见 [§3.3](#sec-3-3)、[§3.4](#sec-3-4) |
| `stores/__tests__/StockKLine.test.ts` | store CRUD 单测：增 / 覆盖 / 局部更新 / 删除 / 初始化恢复 / 脏值兜底 |

**修改 — 页面与状态**

| 文件 | 改动 |
| --- | --- |
| `stores/index.ts` | 追加 `export * from './StockKLine';`（barrel 导出） |
| `pages/Stock/StockKLinePage/StockKLinePage.tsx` | 删除本地 `stockCode` state，改为 `useStockKLineStore()` 派生；`handleSearchSubmit` → `select({ code, name })`；`onClear` → `clear()`（调 `removeStockKLineInfo()`）；URL effect 改为「仅新 code 单向注入」；`name` 用于立即回填展示标签、行情返回后 `update` 补名；移除 `location.state` 读取与 `useLocation` |
| `router/keepAliveConfig.ts` | 新增 `cacheKeyParams`，`/stock/kline: []` |
| `components/layout/KeepAliveOutlet.tsx` | `activeCacheKey` 按白名单计算 |
| `components/kline/KLineChart.tsx` | 容器 `ResizeObserver` → `chart.resize()` |

> 注：`stores/PageStateStore.tsx` **不在改动清单内** —— 本方案不恢复其 `kline` 切片。

**修改 — 跳转入口（统一回 `?stockCode=`）**

| 文件 | 说明 |
| --- | --- |
| `pages/WatchlistPage/components/WatchlistStockTable.tsx` | 自选股列表 |
| `components/layout/ShellHeader.tsx` | 顶栏全局搜索 |
| `pages/Discover/ScannerPage/components/ScannerResultRow.tsx` | 扫描结果行（含 `openInKline` 的 navigate 参数类型恢复单参） |
| `pages/Discover/EodPickerPage/components/EodStockCard.tsx` | 尾盘选股卡片 |
| `pages/Emotion/BoardlistPage/components/LimitUpBoardPanel.tsx` | 涨停板 |
| `pages/Emotion/BoardlistPage/components/LimitDownBoardPanel.tsx` | 跌停板 |
| `pages/Stock/StockKLinePage/components/RecentSearchStockList.tsx` | 最近搜索卡片 |
| `pages/Stock/StockMetricViewPage/StockMetricViewPage.tsx` | 指标视图代码列 navigate（移除 `normalizeStockCode` 单独导入，复用 `buildStockKlinePath`） |
| `pages/Stock/StockMetricViewPage/components/stockMetricViewColumns.tsx` | `<a href>` 查询串保持不变，无需改动 |

**修改 — 测试**

| 文件 | 改动 |
| --- | --- |
| `pages/__tests__/ScannerPage.test.tsx` | 断言回退为 `'/stock/kline?stockCode=600519'` |
| `pages/__tests__/StockKLinePage.*.test.tsx` | 新增 7 场景矩阵用例；刷新 / 往返通过「重新挂载 + 保留 `hrs-state-stockKLine`」模拟 |
| `pages/Stock/StockMetricViewPage/components/__tests__/stockMetricViewColumns.test.tsx` | 断言不变（查询串协议未改） |
| `router/__tests__/`、`components/layout/__tests__/`（如有） | 新增缓存键白名单用例 |
| `components/kline/__tests__/`（如有） | 新增 `ResizeObserver` 注册 / `chart.resize` 调用断言 |

<a id="sec-9"></a>

## 九、验证

**单元 / 集成（Vitest + MemoryRouter）**

| 项 | 模拟方式 | 断言要点 |
| --- | --- | --- |
| Store CRUD | 直接调用 `set / update / remove / get` | 内存值与 `getStorageItem('stockKLine', 'session')` 始终一致；`remove` 后返回 `null`；`update` 在无值时被忽略；脏值解析回退 `null` 且不回写 |
| 刷新 | 重新挂载页面组件，但保留 `hrs-state-stockKLine` 与初始 URL | 保留选中股票（含 `name` 标签）/ 保留清空态 |
| 跳走 → 跳回 | 卸载页面组件后重新挂载于无参数 `/stock/kline`，保留 `hrs-state-stockKLine` | 同上；并验证实例复用时不重复请求 |
| 清空 | 触发 `StockSearch.onClear` | `getStockKLineInfo() === null`、键已删除、URL 无 `stockCode`、列表可见、无行情请求、无最近搜索写入 |
| name 补全 | 以 `?stockCode=603019`（无名称）进入，mock 行情返回 | `updateStockKLineInfo({ name })` 被调用；刷新后标签直接显示「中科曙光（603019.SH）」 |
| 缓存键 | 分别以带参 / 不带参 location 渲染 `KeepAliveOutlet` | `/stock/kline` 恒为同一 `activeCacheKey`；其他路由仍含完整 search |
| 图表尺寸 | mock `ResizeObserver` 触发回调 | `chart.resize()` 被调用 |

**实施后实际执行结果（2026-11-13）**

| 检查 | 结果 |
| --- | --- |
| `read_lints`（覆盖全部改动 / 新增文件） | 0 error、0 warning |
| 本次新增与受影响测试（最终复跑 8 files / 84 tests） | 全通过。其中 K 线页 3 个既有用例集 + `StockKLine.test.ts` 为 4 files / 34 tests；7 场景 persistence、`keepAliveConfig`、`KLineChart` ResizeObserver、`ScannerPage` 为 4 files / 50 tests |
| `CI=true npx vitest run`（全量） | 1417 / 1420 通过；3 个失败均为**未改动文件上的存量问题**：`tests/ui_governance.test.ts`（native `title` 属性）、`src/utils/__tests__/stockIndexLoader.test.ts`（compressIndex tuple 长度）为稳定失败，`ReviewPage.test.tsx`（Today ranking）单跑通过属 flaky。全量日志中的 `stocks.index.json` `ERR_INVALID_URL` 为 jsdom 下相对 URL fetch 的既有警告，不影响结论 |
| `npx vite build` | 成功（仅 chunk size 警告） |
| `npx tsc -b` / `npm run build` | **未通过**，仅报当前工作树预存错误：`hooks/useWatchlistManager.ts` 中 `selectWatchlistQuote` 已定义但未使用、两处调用写成未定义的 `quoteFromStockQuote`；本次改动文件无新增报错 |

> 备注：`useWatchlistManager.ts` 是用户工作树中与本次方案无关的半成品重命名（`git status` 显示其在本轮之前已 modified），本次**未改动**。`npm run build` 的 `tsc -b` 阶段会持续被它挡住，需由该改动的负责人修复后重跑；打包链路已用 `npx vite build` 单独验证。

**手工回归（浏览器，本次未执行，建议逐条补做）**

1. 按 [§6](#sec-6) 逐条走 7 个场景，含「清空后再刷新」「跳回后再刷新」等组合。
2. 在 DevTools → Application → Session Storage 中确认键名为 `hrs-state-stockKLine`、值为 `{code,name}`；清空后键消失。
3. 侧边栏「K 线」与设置页「查看股票数据」两种无参数入口分别验证。
4. 复制带 `?stockCode=` 的链接到新标签页打开（可分享性；新标签页 sessionStorage 独立，不带入上次股票）。
5. 观察图表在清空、跨路由往返、侧栏折叠/展开后是否始终完整宽度。

<a id="sec-10"></a>

## 十、兼容性与风险

<a id="sec-10-1"></a>

### 10.1 已接受的取舍

1. **【已确认】持久化键名带项目前缀**：逻辑键名为 `stockKLine`，经 `@utils/storage` 落盘后浏览器实际键名为 **`hrs-state-stockKLine`**，产品侧已确认无问题。
   **收益**：与 `hrs-state-pageState` 等其他会话态统一管理，`clearHRSStorage('session')` 可一并清理；读写复用项目工具，无需自行处理 `JSON.parse`、前缀与异常兜底。文档与代码中出现的「键 `stockKLine`」一律指**逻辑键名**，断言浏览器实际存储时以 `hrs-state-stockKLine` 为准。
2. **【已确认】唯一判定：看持久化有没有值**（产品侧定稿）：有 `{ code, name }` 就恢复显示该股票（「出去转一圈回来」仍是中科曙光）；没有就展示「最近搜索股票列表」（「重新开一张白纸」）。**不区分进入方式** —— 刷新、从别的页面跳回、菜单点击、手动敲 `/stock/kline` 回车，一律按这一条走。
   **How to apply**：点搜索框 × = 删除持久化，此后无论刷新还是往返都是白纸；外部入口带 `?stockCode=` 进入时先由 `select()` 写入持久化，故「有值」成立，不会误判成白纸。规则详见 [§4.1](#sec-4-1)。
   **Why（旧顾虑已撤销）**：早前把「直接进入 `/stock/kline`」暗含成「必须空态」，才推出「进入即空态」与「跳回保留」不可兼得、需要给菜单加 `?fresh=1` 标记。产品侧确认后，「白纸」由**是否点过 ×（持久化是否被删）**决定，而不是由「从哪进来」决定，二者并不矛盾。本方案**不需要**任何额外标记，也不需要产品二选一。
3. **保留 = 保留选中意图与最终呈现**：刷新或实例被淘汰后会重新请求数据，允许短暂加载态，不承诺图表 DOM / 滚动位置原样恢复。
4. **URL 参数在选中期间保留**：地址栏可见 `?stockCode=`，便于分享与调试；清空时擦除。因缓存键已忽略该参数，保留它不会换实例。
5. **周期不再持久化**：持久化值按约定**只含 `code` 与 `name`**，故 `period` 属 L2 实例态——KeepAlive 实例在则保留，实例销毁 / 刷新后重置 `daily`。7 个场景均未要求周期保留，此取舍不影响验收。
6. **加载失败**：`code` 仍在 `stockKLine` 中，刷新后会按同一代码重试（优于现状「代码丢失需重新搜索」）。

<a id="sec-10-2"></a>

### 10.2 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 旧版本 `location.state` 残留在 `history.state.usr` | 读取侧彻底不再消费 state；`setSearchParams(..., { replace: true })` 由 RR 重写 `history.state`，顺带清除残留 |
| 旧书签 / 外部链接带 `?stockCode=` | 协议名与归一规则不变，按 [§4.1](#sec-4-1) 注入，向后兼容 |
| 旧版本 `hrs-state-pageState` 中的 `kline` 分区残留 | 本方案不读取该切片；`PageStateStore` 现有「按已知分区逐项合并」逻辑会忽略它，无影响 |
| `name` 是快照，可能与最新行情名 / 索引名不一致 | 行情加载成功后 `updateStockKLineInfo({ name: stockInfo.name })` 覆盖；展示标签最终以行情 / 索引为准（《jump2Kline.md》§3.2） |
| 持久化值结构被写脏（缺 `code` / `name` 非 string） | 初始化时校验并回退 `null`，且不回写脏值；`setStockKLineInfo` 入参强制 `StockRef` |
| 无 `window` 环境（SSR / 单测）读取抛错 | `@utils/storage` 的 `getStorageItem` 已内建 `try/catch`，异常时返回 `null`；store 按「未选中」初始化，单测由 jsdom 提供 `sessionStorage` |
| `clearHRSStorage('session')` 会连带清掉 K 线选中态 | 前缀统一后的预期行为：批量清理本就应清空页面状态；单独清空仍走 `removeStockKLineInfo()`（唯一删除入口） |
| zustand store 订阅导致无关组件重渲染 | 该 store 只被 K 线页及少量入口消费，且 `code/name` 变更频率低；必要时用 selector 精确订阅 |
| 清空时 `setSearchParams` 触发路由动作 | 缓存键忽略 `search` ⇒ 不换实例；`replace: true` ⇒ 不新增历史条目 |
| 多标签页共享 `sessionStorage`？ | 否，sessionStorage 按标签页隔离，语义正好；不同标签页各自记住自己的股票 |
| 图表窄图 | 缓存键不再换实例 + `ResizeObserver` 双保险 |
