# <a id="stock-type"></a>股票基础信息类型统一方案

> 📝 **方案简述**：统一 HermesX 前端（apps/hrs-web）中约 48 个"股票基础信息"重复类型，消除命名/单位/可空协议/蛇形字段四类漂移；结论为不做"穷举式 god type"，而落地 `types/stock.ts` 三层模型（StockRef / StockIdentity / StockQuoteCore + 领域 Pick 扩展），并前置完成市场语义正交拆分（P0，收口进 `types/stock.ts`），分 P1→P3 渐进迁移，后端契约不动、差异由前端适配层消化。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-17

## 设计总览（基准 · 准则 · 方案 · 目标 · 行动计划）

> 评审速览：以下五项为本方案的提炼结论，详细依据见后续各章（§1–§9）。

<a id="sec-overview-baseline"></a>

### 设计基准（Baseline）

- **命名基准（字段词典）**：`code` / `name` / `price` / `changePct` / `amount` / `turnoverRate`（沿用现有 `LimitUpItem`，100% 一致、零改名）。
- **后端契约不动**：字段差异一律由前端适配层消化（§4 决策 2）。
- **规范最高权威**：本方案凌驾 `TYPE_NAMING.md §6` 等既有约定（§3.3）。
- **无历史包袱**：可 P0→P3 一气呵成（§4 决策 3）。
- **单位不在类型层表达**：一律 `number`，亿/元换算交渲染层 `format.ts`（§3.1）。
- **枚举规范形态 = 小写**：第三方大小写不统一由边界归一化，标准类型不接收原始大小写/词汇（§3.1）。

<a id="sec-overview-principles"></a>

### 设计准则（Principles）

- 【强制】**单一真源**：`src/types/stock.ts` 收口标识 / 市场 / 资产 / 行情基础字段与枚举。
- 【强制】**三层模型**：L1 `StockRef`/`StockIdentity`、L2 `StockQuoteCore`、L3 `Pick` 组合；不做穷举式 god type。
- 【强制】**领域类型用 `Pick` 组合**，不 `extends` 全量（不谎称后端返回了未提供字段）。
- 【强制】**引用方向**：标准字段从 `stock.ts` 取；`stockIndex.ts` 复用 `StockIdentity`，不得重定义身份字段（§3.4）。
- 【强制】**字段数宽松**：标准类型 = 约束下限 + 字段词典；数据源字段少于标准→缺失须可选或边界补默认；多于标准→忽略或用 `Pick`/`extends` 扩展，不硬塞核心层（§3.4）。
- 【强制】**适配层不进 `types/`**（`TYPE_NAMING.md §4`）：放 api 层或 `src/api/quoteAdapter.ts`。
- 【强制】**枚举/大小写统一小写 + 边界归一化**：标准类型绝不接收原始大小写/词汇（§3.1）。
- 【红线】不建 barrel；不穷举 god type；不动后端契约；不掩盖单位歧义（§3.2）。

<a id="sec-overview-scheme"></a>

### 设计方案（Scheme）

- **单文件收口** `src/types/stock.ts`：`StockRef`/`StockIdentity`/`StockQuoteCore` + 领域 `Pick` 扩展（`LimitUpStockQuote`/`WatchlistQuote`…）。
- **市场语义正交拆分（P0）**：`MarketLocale`（地域·小写）＋`AssetType`＋`Exchange`＋`StockIndexMarketTag`（原始标记）；`BSE → { market:'cn', exchange:'BSE' }`（方案 A，§6.5）。
- **边界归一化**：api `toCamelCase` 与 `stockIndexLoader` 把大写 / 原始标记收敛为小写规范值。
- **收口合并**：`market.ts` 并入 `stock.ts` 并**直接删除旧名 `Market`**；`stockIndex.ts` 去重身份字段（`nameZh→name`，§7.4）。

<a id="sec-overview-goals"></a>

### 具体目标（Goals）

- 消除四类漂移：命名 / 单位 / 可空协议 / 蛇形孤岛。
- 约 48 个重复类型统一到单一真源，引用方向收敛。
- 字段名 / 枚举值 / 大小写全仓一致；标准类型纯净（可选成员可选，多余字段不进核心）。
- 编译期可验证迁移，规避 `BoardlistPage` 式字符串 key 静默失效。
- 不引入新 i18n 假支持（`Extract` 子集表达各 feature 支持范围）。

<a id="sec-overview-plan"></a>

### 行动计划（Phased Plan）

- **P0 市场语义正交拆分**：定义 `MarketLocale`/`AssetType`/`Exchange`/`StockIndexMarketTag`；`market.ts` 并入 `stock.ts` 并**直接删除旧名 `Market`**；`stockIndexLoader` / `normalizeDecisionSignalMarket` / `groupStocksByMarket` 边界归一化；测试夹具同步（§6.3）。
- **P1 涨停榜单（样板）**：落地 `stock.ts`；`LimitUpItem` → `LimitUpStockQuote`（删别名）；`id` 外移至 `BoardlistPage` 行类型（§7.1）。
- **P2 自选股**：`WatchlistQuote` `Pick` 化；`StockQuote` 不动，由 `quoteFromStockQuote` 适配；触及 5 文件（§7.2）。
- **P3 其余类型（独立成期·批量）**：`EodPickerStock`/`AlphaSiftHotspotStock` `Pick` 化；`StockItem`/`MarketIndexItem` 改名 + 截图回归；pair 类型 → `StockRef`；`stockIndex.ts` 去重（P3-6）。波及前端页面/展示、后端接口层、第三方映射四层（§7.3）。

## 目录

- [设计总览（基准 · 准则 · 方案 · 目标 · 行动计划）](#sec-overview)
  - [设计基准](#sec-overview-baseline)
  - [设计准则](#sec-overview-principles)
  - [设计方案](#sec-overview-scheme)
  - [具体目标](#sec-overview-goals)
  - [行动计划](#sec-overview-plan)
- [一、背景与问题](#sec-1)
- [二、现状审计摘要](#sec-2)
  - [2.1 现存类型规模与分布](#sec-2-1)
  - [2.2 四类漂移](#sec-2-2)
  - [2.3 根因：前端字段名源于后端 snake_case](#sec-2-3)
  - [2.4 关键风险证据：单位歧义](#sec-2-4)
- [三、总体目标与红线](#sec-3)
  - [3.1 目标](#sec-3-1)
  - [3.2 红线（明确不做）](#sec-3-2)
  - [3.3 权威性（本规范最高权重）](#sec-3-3)
  - [3.4 引用方向与字段数量不一致的处置](#sec-3-4)
- [四、已确认决策基线](#sec-4)
- [五、目标模型：三层结构](#sec-5)
  - [5.1 L1 标识层：StockRef + StockIdentity](#sec-5-1)
  - [5.2 L2 行情核心层：StockQuoteCore](#sec-5-2)
  - [5.3 L3 领域扩展层：Pick 组合](#sec-5-3)
  - [5.4 适配层放置规则](#sec-5-4)
  - [5.5 totalMarketCap 与单位归一](#sec-5-5)
- [六、P0：市场语义正交拆分](#sec-6)
  - [6.1 问题：5 套 market 联合并非同物](#sec-6-1)
  - [6.2 目标类型定义](#sec-6-2)
  - [6.3 逐文件改动表](#sec-6-3)
  - [6.4 Extract 子集策略](#sec-6-4)
- [七、分期执行计划](#sec-7)
  - [7.1 P1 涨停榜单](#sec-7-1)
  - [7.2 P2 自选股](#sec-7-2)
  - [7.3 P3 其余类型](#sec-7-3)
  - [7.4 P3-6 股票索引类型收口](#sec-7-4)
- [八、风险登记表](#sec-8)
- [九、开放决策点](#sec-9)

<a id="sec-1"></a>

## 一、背景与问题

用户在实现 `/emotion/boardlist`（涨跌榜）时发现：`LimitUpItem`（`apps/hrs-web/src/api/emotionData.ts:11-40`）承载的"代码/名称/现价/涨幅/封单额/成交额/换手率/连板/所属行业"等字段，与项目中大量其它股票类型高度同源。用户诉求有两点：

1. 把这类"股票基础信息"类型统一字段、统一类型，集中到 `apps/hrs-web/src/types/`；
2. 将股票基础信息**穷举**进单一类型，以满足项目内所有股票相关类型定义，并统一"对象信息 / 字段 / 含义 / 单位"的说明。

核心立场：**方向正确（应统一），但"穷举式 god type"不可取**。正确做法是"三层模型 + 渐进迁移 + 适配层"，在消除漂移的同时不掩盖单位歧义、不触发大规模静默回归。

<a id="sec-2"></a>

## 二、现状审计摘要

<a id="sec-2-1"></a>

### 2.1 现存类型规模与分布

- 全仓约 **48 个** stock-ish 类型，散布于 `src/api/*`（约 30 个）与 `src/types/*`（18 个）。
- 既有 `src/types/` 下无 `index.ts` barrel（符合 `TYPE_NAMING.md §6`），各文件为叶子模块。
- 重复程度极高的字段簇：`code/name/price/changePercent/amount/turnoverRate/prevClose/industry` 在 `LimitUpItem`、`WatchlistQuote`、`StockQuote`、`StockItem`、`EodPickerStock`、`AlphaSiftHotspotStock`、`MarketIndexItem` 等多处手工重复。

<a id="sec-2-2"></a>

### 2.2 四类漂移

| 漂移类型 | 实例 |
|---|---|
| **命名**（最普遍） | 涨跌幅：`changePct` / `changePercent` / `change_percent` 三种；代码：`code` / `stockCode` / `symbol` / `stock_code` / `canonicalCode` 五种 |
| **单位**（最危险） | `totalMarketCap` 同名字段，`sectorData.ts` 的 `BoardListItem` 是**亿**、`StockItem` 是**元** |
| **可空协议** | `LimitUpItem`/`WatchlistQuote` 用 `T \| null`（三态）；`StockQuote`/`StockItem` 用 `T?`（二态） |
| **蛇形孤岛** | `api/kline.ts` 刻意不走 `toCamelCase`，且有 `klineApi.contract.test.ts` 护栏 |

<a id="sec-2-3"></a>

### 2.3 根因：前端字段名源于后端 snake_case

前端字段名是**后端 snake_case 经 `toCamelCase` 自动生成**的。例如 `LimitUpItem.changePct` 之所以叫 `changePct`，是因为后端返回 `change_pct`。因此"统一前端类型"实质上等于**要统一后端响应字段名**，否则需在 api 层加映射。这是用户选择"先加适配层、不动后端"的根本原因。

<a id="sec-2-4"></a>

### 2.4 关键风险证据：单位歧义

`sectorData.ts` 中同名字段两种单位并存：

```50:51:apps/hrs-web/src/api/sectorData.ts
  /** 总市值（亿） */
  totalMarketCap: number;
```

而同文件 `StockItem.totalMarketCap`（`:80`）为**元**（消费端 `SectorStockTable.tsx:42` 走 `/1e8`）。若把字段合并进一个 god type，类型系统将**永久掩盖**该歧义。此外全仓 `amount` 的"元"单位靠 **7 处分散的渲染层 `/1e8`** 维持（`StockScreeningPage.tsx:170`、`WatchlistStockColumn.tsx:33`、`EodStockCard.tsx:31`、`KLineChart.tsx:237`、`SectorStockTable.tsx:42`、`SectorBoardCards.tsx:150`、`format.ts`×4）。

> **策略修正（见 §3.1 / §5.5）**：单位不再在类型层表达。核心类型一律 `number`（单位无关），具体"亿/元/万"换算交由渲染层 `format.ts` 与各列表头定义决定。单位歧义由"类型约束"降级为"展示约定"，并统一收口到 `format.ts` 的 `formatAmount` 单一 helper。

<a id="sec-3"></a>

## 三、总体目标与红线

<a id="sec-3-1"></a>

### 3.1 目标

【强制】建立 `src/types/stock.ts` 作为股票标识、市场/资产枚举与行情基础字段的**单一真源**（依据 `TYPE_NAMING.md §2` 后端 DTO/领域模型、`§5` 单真源），统一字段名与可空协议（`T | null` 三态）。

【强制】**单位不在类型层表达**：所有金额/数量字段类型均为 `number`（单位无关）；"亿/元/万"等展示换算一律交由渲染层 `format.ts` 与各列表头定义负责（见 §5.5），核心类型不承载单位语义。比率字段亦为 `number`（百分数值，如 `1.23` 表示 1.23%）。

【强制】**枚举值与大小写统一为小写标准形态，且由边界归一化保障**：`MarketLocale` 等所有枚举的规范形态一律**小写**（如 `cn`/`hk`/`us`）。第三方数据源 / 上游接口返回的大小写不统一（如 `CN`/`Cn`/`cn` 混用、或 `BSE`/`INDEX`/`ETF`/`UNKNOWN` 等原始标记）是**预期内**情况，一律在 **api/loader 边界适配层**（`api/*` 的 `toCamelCase`、`stockIndexLoader` 的归一化函数）收敛为规范小写与固定枚举值；**标准类型绝不接收原始大小写或原始词汇**。即：标准类型是"约束下限 + 固定词典"，大小写 / 词汇归一化是边界职责，不属于消费方（呼应 §3.4）。

【推荐】领域专属字段保留在各 api 模块，通过 `Pick<StockQuoteCore, ...>` 组合，不污染核心层。

<a id="sec-3-2"></a>

### 3.2 红线（明确不做）

| 项 | 理由 |
|---|---|
| 不动 `api/kline.ts` 蛇形孤岛 | 刻意绕过 `toCamelCase`，且有 `klineApi.contract.test.ts` 护栏 |
| 不做任何单位换算 | 改动会令上述 7 处 `/1e8` 静默差 1e8 倍 |
| 不改后端任何字段 | 已确认决策（兼容桌面端等其它消费方） |
| 不建 `types/index.ts` barrel | `TYPE_NAMING.md §6` 明令禁止 |

<a id="sec-3-3"></a>

### 3.3 权威性（本规范最高权重）

【强制】本方案文档是项目内"股票信息 / 字段 / 枚举值"的**最高权威规范**，适用于本仓库所有前端（及约定范围内的后端契约对齐）场景；当本规范与既有约定（如 `TYPE_NAMING.md §6` 的"按域分文件、禁止 barrel"、各 api 模块的历史内联类型）冲突时，**以本规范为准**。

【强制】代码（`src/types/stock.ts` 及其在 `src/api/*` 的消费方）必须可逐字段追溯至本规范的字段表、命名与枚举值；任何新增或修改股票相关类型，**先改本规范、再改代码**，禁止在代码层"就地发明"等价类型（`TYPE_NAMING.md §5` 单真源）。

【推荐】因本项目尚未上线、无历史包袱，可一次性完成 P0→P3 的统一，不必受"渐进以避免线上回归"约束；但所有改名仍需保证编译期可验证（避免 `BoardlistPage.tsx` 式字符串 key 静默失效）。

<a id="sec-3-4"></a>

### 3.4 引用方向与字段数量不一致的处置

【强制】**引用方向**：所有股票身份 / 行情基础字段，必须从 `src/types/stock.ts` 引用（`StockRef` / `StockIdentity` / `StockQuoteCore` 及其衍生类型）。`src/types/stockIndex.ts` 只承载搜索索引专属类型（`StockIndexItem` / `StockSuggestion` / `StockIndexTuple`），且**自身必须 `import type` 复用 `stock.ts` 的 `StockIdentity`**（见 §7.4），不得重新定义身份字段。若某引用方只需身份 / 行情字段，应直接 `import type { StockIdentity } from 'stock'`，**不得为取 `code`/`name`/`market` 而从 `stockIndex.ts` 间接引用标准字段**。

【强制】**标准类型字段数 ≠ 数据源字段数，二者允许不一致**，分两种：

- **数据源字段少于标准（标准 10 字段，源只给 5）**：允许，前提是**缺失字段在标准里为可选（`?`）**。本规范要求身份层字段（除 `code`/`name` 外）一律可选，故源只给 `code`/`name`/`market` 仍能赋值给 `StockIdentity`（结构类型系统天然允许"字段子集"）。若源缺失的是**必填**字段，则属契约不符——要么将该字段在标准里降为可选，要么在边界适配层补默认值，不得让消费方在 `undefined` 上裸奔。
- **数据源字段多于标准（标准 10 字段，源给 20）**：一律允许。TypeScript 对"非字面量对象"允许携带多余属性，标准类型相当于在数据上的"取景器"，多余字段被忽略、无害。若消费方**确实需要**那多出的字段，按本规范 L3 模式：用 `extends` / `Pick<StockQuoteCore, ...>` 组合标准 + 追加领域专属字段（如 `StockIndexItem` 即"标准身份 + pinyin/aliases/active/popularity"），**不得为图省事把多余字段硬塞进核心层**。

> 结论：`stock.ts` 是"约束下限"（必填项）与"字段词典"（可选全集），不是"数据源的精确镜像"。多退少补都在边界（api / loader 适配层）处理，标准类型自身保持纯净。

<a id="sec-4"></a>

## 四、已确认决策基线

| # | 决策 | 结论 |
|---|---|---|
| 1 | 字段命名基准 | `code` / `name` / `price` / `changePct` / `amount` / `turnoverRate` |
| 2 | 后端 | **不动**；字段名差异一律由前端适配层消化 |
| 3 | 节奏 | 分期：P0（市场拆分）→ P1（涨停榜）→ P2（自选股）→ P3（其余）；因无历史包袱可一气呵成 |
| 4 | 单位策略 | 类型层一律 `number`（单位无关），亿/元换算交由渲染层 `format.ts` 与列定义 |
| 5 | 规范权重 | 本方案为最高权威，凌驾 `TYPE_NAMING.md §6` 等既有约定；实现以此为准 |

<a id="sec-5"></a>

## 五、目标模型：三层结构

落地于 `apps/hrs-web/src/types/stock.ts`，文件头须含 `@file` / `@description` / `@author`（依据 `TYPE_NAMING.md §7`），每个字段一句话中文注释，单位明确。

<a id="sec-5-1"></a>

### 5.1 L1 标识层：StockRef + StockIdentity

```ts
/** ①-a 股票信息，最小标识：必填项不能再多（现有 7 个双字段 pair 类型正好满足） */
export interface StockRef {
  /** 股票代码（如 600519） */
  code: string;
  /** 股票名称 */
  name: string;
}

/**
 * ①-b 完整身份标识：市场 / 资产类型 / 代码展示形态 / 英文名。
 * 全部可选 —— 可选成员不强制下游补齐，既有 pair 类型仍能赋值，
 * 搜索/跨市场场景可按需携带。market/assetType 由 P0 统一后的类型引入。
 */
export interface StockIdentity extends StockRef {
  /** 市场地域：纯地域维度，小写规范值（`cn`/`hk`/`us`/`jp`/`kr`/`tw`）；交易所、资产类别不在此处，见 §3.1 / §6 */
  market?: MarketLocale;
  /** 资产类型：个股 / 指数 / ETF（原 `Market` 联合中被污染的 `INDEX`/`ETF` 语义在此承接） */
  assetType?: AssetType;
  /** 带交易所后缀的规范代码（如 `600519.SH`），跨市场 / 搜索场景使用 */
  canonicalCode?: string;
  /** 展示用代码（如 `600519`），用户界面直接显示 */
  displayCode?: string;
  /** 英文名（如 `Kweichow Moutai`），国际化 / 搜索辅助 */
  nameEn?: string;
  /** 所属行业（完整信息的一部分，如 `白酒` / `半导体`）；可选，源未提供时由边界适配层补默认值或留空 */
  industry?: string;
  /** 所属概念（完整信息的一部分）：一只股票可同时属于多个概念（如 `白酒` / `国企改革` / `基金重仓`），故为数组；可选，源未提供时留空 */
  concepts?: string[];
}
```

<a id="sec-5-2"></a>

### 5.2 L2 行情核心层：StockQuoteCore

```ts
/**
 * ② 行情核心层：字段清单 + 含义的唯一真源（穷举层）。
 * 类型层不约束单位（见 §3.1）：字段均为 number，注释中的（元）/（%）仅标注常见来源单位；
 * 实际"亿/元"等展示换算交由渲染层 format.ts 与各列定义负责，核心层不承载单位语义。
 */
export interface StockQuoteCore extends StockIdentity {
  /** 最新价（元） */
  price: number | null;
  /** 涨跌额（元） */
  change: number | null;
  /** 涨跌幅（%，1.23 表示 1.23%） */
  changePct: number | null;
  /** 成交额（元） */
  amount: number | null;
  /** 成交量（股） */
  volume: number | null;
  /** 换手率（%） */
  turnoverRate: number | null;
  /** 昨收价（元） */
  prevClose: number | null;
  /** 今开（元） */
  open: number | null;
  /** 最高（元） */
  high: number | null;
  /** 最低（元） */
  low: number | null;
  /** 总市值（单位由来源决定，渲染层换算；类型层不约束单位） */
  totalMarketCap: number | null;
}
```

<a id="sec-5-3"></a>

### 5.3 L3 领域扩展层：Pick 组合

【强制】领域类型**必须用 `Pick<StockQuoteCore, ...>` 组合**，不得 `extends` 全量——核心层是"字段字典"而非"数据模板"，`extends` 会谎称后端返回了 `change/volume/open/high/low` 等未提供字段。

```ts
/**
 * 涨停榜单：后端返回 7 个通用字段，用 Pick 精确挑选。
 * `industry` 属股票完整信息，已统一收口至 `StockIdentity`（经 `StockQuoteCore` 继承），此处由 Pick 引入，不再作为领域专属字段。
 */
export interface LimitUpStockQuote
  extends Pick<StockQuoteCore, 'code' | 'name' | 'price' | 'changePct' | 'amount' | 'turnoverRate' | 'industry'> {
  /** 封板资金 / 封单额（元） */
  sealAmount: number | null;
  /** 首次封板时间 HHMMSS，无值返回空串 */
  firstLimitTime: string;
  /** 最后封板时间 HHMMSS */
  lastLimitTime: string;
  /** 炸板次数 */
  breakCount: number | null;
  /** 涨停统计（如 '3/2'，表示 2 天内涨停 3 次） */
  limitStat: string;
  /** 连板数（1 = 首板） */
  consecutiveBoards: number | null;
}
```

<a id="sec-5-4"></a>

### 5.4 适配层放置规则

【强制】`TYPE_NAMING.md §4` 规定 `types/` 不得依赖 `utils`/`stores`/`components`。适配函数是运行时代码，**禁止放进 `types/stock.ts`**。

- 仅单模块使用 → 就地放在该 `*Api.ts`（如既有 `useWatchlistManager.ts` 的 `quoteFromStockQuote`）。
- 被 ≥2 模块复用 → 新建 `src/api/quoteAdapter.ts`（仍属叶子层，只 `import type` from `types/stock`）。

<a id="sec-5-5"></a>

### 5.5 关于 totalMarketCap 与单位归一

`totalMarketCap` 历史上存在"亿 vs 元"混用（见 §2.4），但本规范已确立 **"类型层不表达单位"** 原则（§3.1）：核心字段一律 `number`，单位由渲染层决定。因此 `totalMarketCap` **纳入核心层**，类型为 `number | null`，其展示单位由各消费表在列定义中通过 `format.ts` 的 `formatAmount` 转换——若某来源确以"亿"返回，则对应列渲染时除 `1e8`，与现有 7 处 `/1e8` 模式一致，但统一收口到单一 helper，避免散落。

<a id="sec-6"></a>

## 六、P0：市场语义正交拆分

<a id="sec-6-1"></a>

### 6.1 问题：5 套 market 联合并非同物

`StockIdentity` 引入 `market?` 前，必须先统一 market 联合。证据显示 `types/market.ts:11` 的 `Market` 与 `portfolio.ts:13`、`decisionSignals.ts:13`、`alerts.ts:23`、`analysis.ts:11` 的联合**不是同一概念的拷贝，而是 4 种语义共用 `market` 一名**：

| 实际语义 | 混淆取值 | 正确处理 |
|---|---|---|
| 地域 | CN/HK/US/JP/KR/TW | 统一成地域联合 |
| 资产类别 | `INDEX` / `ETF` | 已有 `AssetType` 承接，从 market 剔除 |
| 交易所（北交所） | `BSE` | 隶属 `cn` 之下，独立 `Exchange` 维度 |
| 缺省哨兵 | `UNKNOWN` | 应为 `undefined`，不是取值 |

`DecisionSignalsPage.tsx:313-326` 的 `normalizeDecisionSignalMarket` 手运行时映射暴露：运行时确有 `TW`、`UNKNOWN`，而 `types/market.ts:11` 声明中**两者皆缺**——即现有 `Market` 类型在说谎，编译器无法兜住漏项。三处穷举 `Record<X, ...>`（`MarketReviewRegionSelector.tsx:38`、`decisionSignalLabels.ts:21`、`featureText.ts:36`）既是风险也是安全网：扩值会立即编译报错。

<a id="sec-6-2"></a>

### 6.2 目标类型定义

```ts
// src/types/stock.ts —— 市场 / 资产 / 交易所唯一真源（原 types/market.ts 收口于此，见 §3.3）

/** 市场地域（唯一真源），小写以对齐后端契约与 i18n label 后缀 */
export type MarketLocale =
  | 'cn' | 'hk' | 'us' | 'jp' | 'kr' | 'tw';

/** 资产类型：承接原 Market 被污染的 INDEX / ETF 语义 */
export type AssetType = 'stock' | 'index' | 'etf';

/** 交易所：隶属于地域之下的细分维度 */
export type Exchange = 'SSE' | 'SZSE' | 'BSE';

/** 各 Feature 支持范围用 Extract 表达：既单一真源，又不为不支持的市场补假 i18n */
export type AlertSupportedMarket = Extract<MarketLocale, 'cn' | 'hk' | 'us'>;
export type MarketReviewSupportedMarket = Extract<MarketLocale, 'cn' | 'hk' | 'us' | 'jp' | 'kr'>;
```

> **收口说明（依据 §3.3 权威性）**：上述 `MarketLocale` / `AssetType` / `Exchange` 原分散于 `types/market.ts`，现统一收口至 `src/types/stock.ts`（单一真源）。迁移方式：在 `stock.ts` 定义权威枚举，并**直接删除 `types/market.ts` 的 `Market` 类型与整个文件**（不保留 `type Market = MarketLocale` 兼容别名）；全仓消费方在 P0 同步改为引用 `stock.ts` 新类型（见 §9 已确认）。该合并刻意覆盖 `TYPE_NAMING.md §6` 的"按域分文件"约定，以本规范最高权威为准。

<a id="sec-6-3"></a>

### 6.3 逐文件改动表

| # | 文件:行 | 现状 | 改为 |
|---|---|---|---|
| 1 | `types/market.ts:11` | `Market = 'CN'\|...\|'BSE'` | 扩写为 `MarketLocale` + 保留 `AssetType` + 新增 `Exchange` + 2 个 `Extract` 子集 |
| 2 | `types/portfolio.ts:13,27,190,210` | 4 处内联 `'cn'\|'hk'\|'us'\|'jp'\|'kr'\|'tw'` | `MarketLocale` |
| 3 | `types/decisionSignals.ts:13` | `DecisionSignalMarket` | `type DecisionSignalMarket = MarketLocale` |
| 4 | `types/alerts.ts:23` | `MarketRegion`（仅 3 值） | `AlertSupportedMarket` |
| 5 | `types/analysis.ts:11` | `MarketReviewRegion`（5 值） | `MarketReviewSupportedMarket` |
| 6 | `types/stockIndex.ts:15-38` | `market: Market`（大写、不准确） | `market` 改用 `stock.ts` 的 `StockIndexMarketTag`（如实含 `INDEX/ETF/BSE/UNKNOWN`）；该文件整体收口见 §7.4 |
| 7 | `pages/PortfolioPage.tsx:177` | 内联 `PortfolioAccountMarket` | `MarketLocale` |
| 8 | `utils/stockIndexLoader.ts:210` | `groupStocksByMarket` 直接以 `item.market` 字符串分组 | 边界归一化（BSE→`{market:'cn',exchange:'BSE'}` 等）；并改为按 `market`（归一后为 `cn`）分组，使北交所并入 `cn` 桶而非独立 `'BSE'` 桶 |
| 9 | `pages/DecisionSignalsPage.tsx:313-316` | 手写 `normalizeDecisionSignalMarket`，内含 `if (market==='CN'||market==='BSE') return 'cn'` | 逻辑迁入 loader/适配层；BSE 改为输出 `{ market:'cn', exchange:'BSE' }`，不再特判为独立地域 |
| 10 | `components/StockSearch/__tests__/StockSearch.test.tsx:91,581` | `market: 'BSE'` 测试夹具 | 改为 `{ market:'cn', exchange:'BSE' }` 形态，与新类型一致 |

**大小写定小写（已确认）**：`MarketLocale` 等枚举规范形态统一为小写。搜索索引侧（大写 `CN`/`BSE`/…）仅在 `stockIndexLoader` 一处归一化；若选大写则需在 portfolio/decisions/alerts/analysis **四处**边界适配。小写明显更省，契合"适配层最少化"。第三方/源数据大小写不统一一律在 api/loader 边界收敛为小写，标准类型不接收原始大小写（见 §3.1 强制规则）。

<a id="sec-6-4"></a>

### 6.4 Extract 子集策略

【强制】各 Feature 的 market 联合一律 `Extract<MarketLocale, ...>`，**不得**直接全量引用 `MarketLocale`。理由：alerts 真实只支持 cn/hk/us，强扩到 6 值会迫使为其补 jp/kr/tw 三语标签（假支持）。`Extract` 同时满足单一真源与"不多承诺"，**且本方案因此不产生任何 i18n 新增**。

<a id="sec-6-5"></a>

### 6.5 根因：BSE 为何被误归类进地域联合（设计问题 + 代码副作用）

**结论：本质是类型设计 / 数据建模问题，并催生了代码层 workaround，二者都需在 P0 一并修正。**

- **根因（设计）**：`Market` 联合（`types/market.ts:11`）把 4 种正交语义压进同一个字段——地域（CN/HK/US…）、资产类别（INDEX/ETF）、交易所（BSE）、哨兵（UNKNOWN）。其源头是**后端 / 索引数据用一个扁平 `market` 字符串承载了"国别 + 交易所 + 资产类别"**，前端 `types/market.ts` 直接 1:1 镜像了该扁平字符串，未做维度正交拆分。北交所（BSE，代码后缀 `.BJ`）因此被当成与 `CN` 平级的"地域"，而非"中国境内的交易所"。
- **代码层已暴露的自相矛盾（证据）**：
  - `DecisionSignalsPage.tsx:316` 的运行时归一化 `if (market === 'CN' || market === 'BSE') return 'cn'` —— **运行时早已知道 BSE 就是中国**，却仍在类型里把它列为独立地域值，类型在说谎（`TYPE_NAMING.md §5` 单真源场景）。
  - `stockIndexLoader.ts:210` `groupStocksByMarket` 直接以 `item.market` 字符串分组：若存在 `market:'BSE'` 的股票，会生成独立的 `'BSE'` 桶，**脱离 A 股（cn）桶**，与"北交所属于中国 A 股"的业务事实相悖。
  - 三处 `Record<X, ...>` 标签映射（`decisionSignalLabels.ts:21`、`featureText.ts:36`、`MarketReviewRegionSelector.tsx:38`）均不含 `BSE` 键，未归一化的 BSE 会静默渲染成 `'-'`。
- **为何方案 A 能根治**：把 `market` 限定为纯地域（`cn`/`hk`/…），`BSE` 在边界归一化为 `{ market:'cn', exchange:'BSE' }`。于是 `groupStocksByMarket` 天然把北交所并入 `cn` 桶、`normalizeDecisionSignalMarket` 不再需特判 BSE、标签映射也不再遗漏——**类型与运行时终于一致**。

<a id="sec-7"></a>

## 七、分期执行计划

<a id="sec-7-1"></a>

### 7.1 P1 涨停榜单（样板就绪，待执行）

- 新增 `types/stock.ts`（L1+L2+L3）；`emotionData.ts` 把内联 `LimitUpItem` 改为引用 `LimitUpStockQuote`，**删除 `LimitUpItem` 别名**（统一为规范命名，同步更新 `BoardlistPage.tsx` 的 import 与 `useState`/`Table`/`columns` 类型）。
- 因选定命名基准与现有 `LimitUpItem` **100% 一致**，本阶段**零字段改名、无适配层**，风险最低，可直接落地。
- **`id` 字段处置（已定）**：`id`（= 股票代码，纯 UI 行 key，后端不返回）**不进入** `LimitUpStockQuote`；改在 `BoardlistPage` 行类型承载（如 `type BoardRow = LimitUpStockQuote & { id: string }`，映射时 `id = code`），或直接以 `code` 作为表格 `key`（更彻底，可删 `id` 字段）。领域类型保持纯净（依据 §3.4）。

<a id="sec-7-2"></a>

### 7.2 P2 自选股（收益最高）

- `WatchlistQuote`（`api/watchlist.ts:38-46`）改为 `Pick<StockQuoteCore, 'price'|'changePct'|'amount'|'turnoverRate'|'prevClose'> & { totalMv: number | null }`。
- `StockQuote`（`api/stocks.ts:122-137`）**不动**（后端契约镜像）；改名由既有 `useWatchlistManager.ts:61-71` 的 `quoteFromStockQuote` 适配函数承担（`currentPrice→price`、`changePercent→changePct`）。
- 涉及：`api/watchlist.ts`、`hooks/useWatchlistManager.ts`、`pages/WatchlistPage/components/WatchlistStockColumn.tsx`、`WatchlistStockTable.tsx`、`HomeStockWorkspace.tsx`。

<a id="sec-7-3"></a>

### 7.3 P3 其余类型（按风险从低到高；独立成期）

> **范围与受影响面（重要）**：P3 **不只是改 `types`**。一旦字段名统一（如 `changePercent→changePct`、`turnover→amount`），改动会沿调用链向**四层**扩散，工作量远大于 P0/P1/P2，须逐类型核对：
> - **① 类型层**：统一引入 `types/stock.ts`（`StockRef` / `StockIdentity` / `StockQuoteCore` 及其 `Pick` 衍生），消除各 `api/*` 模块的手工重复类型。
> - **② 前端页面与展示数据处理**：表格列绑定、动态排序、`format.ts` 展示换算等依赖字段名处须同步（典型如 `SectorStockTable.tsx` 手写 15 列，见 `StockItem` 行）。
> - **③ 后端接口层**：字段改名涉及契约对齐——本方案默认**后端不动、差异由前端适配层消化**（§4 决策 2），故此处以"确认适配层覆盖"为准，不主动改后端。
> - **④ 第三方接口映射**：`api/*` 经 `toCamelCase` 把后端 snake_case 自动转 camelCase；若改名触达映射键（如 `change_percent→changePct`），须确认映射与消费方一致，避免静默错位。
>
> 因牵涉面广、需逐类型核对展示与映射，**P3 单独开一期**，在 P0→P2 之后**批量统一**执行，不混入早期阶段。

| 项 | 现状 | 改法 | 风险 |
|---|---|---|---|
| `EodPickerStock`（`api/eodPicker.ts:28-41`） | 字段名已符合基准 | `Pick` 化，零改名 | 低 |
| `AlphaSiftHotspotStock`（`api/alphasift.ts:142-154`） | 全 optional | `Partial<Pick<...>>` | 低 |
| `StockItem`（`api/sectorData.ts:67-84`） | `changePercent→changePct`、`turnover→amount` | 改名 + 处理 `totalMarketCap` 单位 | **高**：`SectorStockTable.tsx` 手写 15 列，**须附前后对比截图回归** |
| `MarketIndexItem`（`api/sectorData.ts:202-217`） | `changePercent→changePct`、`preClose→prevClose` | 改名 | 中：`IndexCard.tsx` 有手写 fallback |
| pair 类型 | `ScannerWatchlistItem` 等 7 个 | 纯双字段者替换为 `StockRef` | 低 |

<a id="sec-7-4"></a>

### 7.4 P3-6 股票索引类型收口（stockIndex.ts）

`src/types/stockIndex.ts` 与 `stock.ts` 的 `StockIdentity` **存在真实重叠**，但**不应整体并入** `stock.ts`——其中 `StockSuggestion` / `StockIndexTuple` / `StockIndexData` 是搜索索引的序列化 / 联想专属类型，不属于通用股票身份。正确做法：**去重身份字段、保留搜索专属字段**。

**重叠分析（`StockIndexItem` 11 字段 vs `StockIdentity`）**

| `StockIndexItem` 字段 | 处置 |
|---|---|
| `canonicalCode` / `displayCode` / `nameEn?` / `market` / `assetType` | **继承**：已是 `StockIdentity` 成员 |
| `nameZh` | **改名 → `name`**（与 `StockIdentity.name` 对齐；当前 `nameZh` 即中文名，属命名漂移） |
| `pinyinFull?` / `pinyinAbbr?` / `aliases?` / `active` / `popularity?` | **保留**：搜索 / 补全专属，不入核心 |

**目标形态**

```ts
// stockIndex.ts —— 仅保留搜索索引专属类型，身份字段复用 StockIdentity
import type { StockIdentity, StockIndexMarketTag, AssetType } from './stock';

/** 股票索引项（全量格式）：身份字段复用 StockIdentity，仅保留补全专属字段 */
export interface StockIndexItem extends StockIdentity {
  /** 拼音全拼 */
  pinyinFull?: string;
  /** 拼音缩写 */
  pinyinAbbr?: string;
  /** 别名 */
  aliases?: string[];
  /** 是否启用 */
  active: boolean;
  /** 热度 */
  popularity?: number;
}

/** 搜索联想项：身份 + 联想元数据 */
export interface StockSuggestion extends StockIdentity {
  /** 匹配类型 */
  matchType: 'exact' | 'prefix' | 'contains' | 'fuzzy';
  /** 匹配字段 */
  matchField: 'code' | 'name' | 'pinyin' | 'alias';
  /** 排序分 */
  score: number;
}

/** 压缩元组格式（减包体） */
export type StockIndexTuple = [
  string,                // canonicalCode
  string,                // displayCode
  string,                // name（原 nameZh）
  string | undefined,    // pinyinFull
  string | undefined,    // pinyinAbbr
  string[],              // aliases
  StockIndexMarketTag,   // market
  AssetType,             // assetType
  boolean,               // active
  number | undefined,    // popularity
];
export type StockIndexData = StockIndexItem[] | StockIndexTuple[];
```

> 注：`StockIdentity.name` 在本项目即中文名（与 `nameEn` 对应），故 `nameZh` 直接对齐为 `name`；`StockIndexTuple` 元组下标 2 的映射由 `stockIndexLoader.ts` 同步从 `nameZh` 改为 `name`。

**迁移成本（机械但面广）**：`nameZh→name` 触及约 15 个文件、`stockIndexLoader.ts`（元组映射）、`searchStocks.ts`、`StockSearch*.tsx`、`useStockAutocomplete.ts`、`ChatPage.tsx` 及 4 个测试文件，总计约 80+ 处引用。因无历史包袱可一次性完成，但**必须连带更新测试**（`stockIndexLoader.test.ts` / `searchStocks.test.ts` / `StockSearch.test.tsx` 的 `nameZh` 断言会失败）。建议独立成 P3-6，附前后对比验证。

**引用方向（依据 §3.4）**：`stockIndex.ts` 改造后必须 `import type { StockIdentity, ... } from './stock'`，自身只保留搜索专属字段；所有"只用身份 / 行情字段"的引用方改从 `stock.ts` 取 `StockIdentity` / `StockQuoteCore`，不再为取 `code`/`name`/`market` 而从 `stockIndex.ts` 间接引用。

<a id="sec-8"></a>

## 八、风险登记表

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| 1 | `BoardlistPage.tsx` 用字符串 key（`key:'changePct'`、`(a as Record<string, unknown>)[column]` 动态排序） | 后续改名**编译器拦不住**，静默失效 | P2/P3 每次改名必须同步 grep 字符串 key（含 `ScannerPage.tsx:73` 的 key→i18n 映射表） |
| 2 | P2 改名 `currentPrice→price` | 触碰自选股 5 文件 | 类型系统报全部漏改点，可兜底（异于风险 1） |
| 3 | `totalMarketCap` 单位歧义 | 数值差 1e8 倍 | 类型层不表达单位（§3.1）：核心层收口为 `number`，亿/元换算统一在渲染层 `format.ts`（§5.5） |
| 4 | 可空协议不统一（三态 vs 二态） | UI 的 `--` 判断失效 | 核心层统一 `T \| null`，消费方用 `Partial<Pick<>>` 表达可选 |

<a id="sec-9"></a>

## 九、开放决策点

**已确认（本版）**
- `market.ts` 并入 `stock.ts`（§6.2）：市场 / 资产 / 交易所枚举统一收口至 `stock.ts`；`Market` 旧名**直接删除**、`market.ts` 一并删除，不留兼容别名（§9 已确认）。
- `stockIndex.ts` 与 `stock.ts` 身份字段去重（§7.4）：`StockIndexItem` / `StockSuggestion` 改 `extends StockIdentity`，`nameZh→name`，搜索专属字段保留。
- **`BSE` 采用方案 A（§6.5）**：`BSE → { market:'cn', exchange:'BSE' }`，新增独立 `Exchange` 维度，不丢弃交易所信息；并同步修正 `groupStocksByMarket` / `normalizeDecisionSignalMarket` / 测试夹具等使用点（见 §6.3）。
- **P1 别名与 `id` 处置（§7.1）**：删除 `LimitUpItem` 别名、统一为 `LimitUpStockQuote`；`id`（=code 的 UI 行 key）外移至 `BoardlistPage` 行类型，不进标准类型。
- **P3 独立成期、批量执行（§7.3）**：字段改名波及前端页面/展示、后端接口层、第三方接口映射四层，范围大；P3 单独开一期，在 P0→P2 之后批量统一。`StockItem` 迁移须附 `SectorStockTable` 前后对比截图（写入 §7.3 表格风险列）。
- **P0 大小写定小写（§3.1 / §6.3）**：`MarketLocale` 等枚举规范形态统一为小写；第三方/源数据大小写不统一由 api/loader 边界归一化，标准类型不接收原始大小写（见 §3.1 新增强制规则）。
- **旧名 `Market` 直接删除（§6.2 / §9）**：P0 内删除 `type Market`，**不留** `type Market = MarketLocale` 兼容别名；`market.ts` 一并删除，全仓引用改指 `stock.ts` 新类型（locale 上下文用 `MarketLocale`，`stockIndex.ts` 原始标记用 `StockIndexMarketTag`）。

**待确认**：无（全部决策已确认，可进入 P0→P3 执行）。
