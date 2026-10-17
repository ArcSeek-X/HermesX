# <a id="jump2kline"></a>跳转个股 K 线页统一方案（`?stockCode=` 直达）

> 📝 **方案简述**：统一本项目所有「跳转到个股 K 线页 `/stock/kline`」的入口，一律采用查询参数模式 `…/stock/kline?stockCode=<代码>`，由 K 线页自行解析加载行情与 K 线、自行生成搜索框展示标签；跳转方不再写 sessionStorage。覆盖范围：全项目所有按股票跳转 K 线的入口及其消费逻辑、新增入口规范。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-17

## 目录

- [一、概述与范围](#sec-1)
- [二、统一跳转协议](#sec-2)
  - [2.1 URL 与参数](#sec-2-1)
  - [2.2 代码形态与归一](#sec-2-2)
- [三、K 线页消费逻辑](#sec-3)
  - [3.1 参数解析与数据加载](#sec-3-1)
  - [3.2 搜索框展示标签生成](#sec-3-2)
  - [3.3 无参数兜底](#sec-3-3)
- [四、跳转入口清单](#sec-4)
- [五、正反清单](#sec-5)
- [六、新增入口指引](#sec-6)
- [七、兼容性与风险](#sec-7)

<a id="sec-1"></a>

## 一、概述与范围

**规定**：凡按具体股票跳转到个股 K 线页的场景，统一使用查询参数 `?stockCode=<代码>`，不再使用「写 sessionStorage + `navigate('/stock/kline')`」的旧模式。

**Why**：旧模式把「目标股票」藏在 sessionStorage（`kline.stockCode`）里，链接不可复现、不可分享、多入口各写一份易漂移；改为 URL 参数后，跳转意图显式化，单一消费方（K 线页）统一解析，逻辑收敛、可测试、可回溯。

**How to apply**：适用于 `apps/hrs-web/src` 内所有携带具体股票、跳转到 `/stock/kline` 的入口；无具体股票的通用入口（如设置页「查看股票数据」）不传 `stockCode`，见 [§3.3](#sec-3-3)。

**覆盖边界**：

| 维度 | 是否覆盖 |
| --- | --- |
| 按股票跳转 K 线的入口 | ✅ 强制统一 |
| K 线页对参数的解析/加载/展示 | ✅ 本文约定 |
| 无具体股票的通用入口 | ➖ 允许不带 `stockCode` |
| K 线图本身的数据接口与渲染 | ❌ 见《K线图数据接口获取说明.md》等专题文档 |

<a id="sec-2"></a>

## 二、统一跳转协议

<a id="sec-2-1"></a>

### 2.1 URL 与参数

**规定**：跳转目标形如

```text
http://<host>/stock/kline?stockCode=000422
```

- 【强制】参数名固定为 `stockCode`（与 K 线页内部状态同名，便于对照）。
- 【强制】参数值必须经 `encodeURIComponent` 编码后拼接。
- 【推荐】使用 `react-router-dom` 的 `useNavigate()` 进行跳转，保证 SPA 内导航。

```ts
// ✅ 正确：带 ?stockCode= 直达
navigate(`/stock/kline?stockCode=${encodeURIComponent(code)}`);
```

<a id="sec-2-2"></a>

### 2.2 代码形态与归一

**规定**：`stockCode` 取值既可以是纯数字（`000422`），也可以是带市场后缀的规范代码（`000422.SZ` / `600519.SH` / `00700.HK`）；K 线页统一按 `.split('.')[0]` 归一为纯代码后再请求接口。

- 【强制】跳转方传入代码前，如本地已持有规范代码，直接传规范代码亦可（页面会归一）；如持有纯代码，直接传纯代码。
- 【推荐】入口若已有归一工具（如 `normalizeStockCode` / `toFullStockSymbol`），复用而非重复实现。

| 传入示例 | 页面归一后 | 说明 |
| --- | --- | --- |
| `000422` | `000422` | 纯数字，直接用 |
| `000422.SZ` | `000422` | 带后缀，页面去后缀 |
| `00700.HK` | `00700` | 港股，页面去后缀 |

<a id="sec-3"></a>

## 三、K 线页消费逻辑

组件：`apps/hrs-web/src/pages/Stock/StockKLinePage/StockKLinePage.tsx`。

<a id="sec-3-1"></a>

### 3.1 参数解析与数据加载

**规定**：页面通过 `useSearchParams()` 读取 `stockCode`，归一为纯代码后写入内部 `stockCode` 状态；该状态变化触发并行请求 `/api/v1/kline/{code}/info` 与 `/api/v1/kline/{code}/kline`。

**How to apply**：

- 已加载相同代码时跳过，避免重复请求（以 `loadedStockCodeRef` 比对）。
- 与页内手动搜索共用同一条加载链路（`loadStockData`），二者行为一致。

<a id="sec-3-2"></a>

### 3.2 搜索框展示标签生成

**规定**：搜索框展示标签「名称（规范代码）」由 K 线页以**已加载行情**为准生成，并持久化到 sessionStorage 供返回本页恢复；**跳转方不再写入展示标签**。

- 生成优先级：本地股票索引命中 → `名称（规范代码）`（带市场后缀）；索引未命中 → `行情名（代码）`；再退化 → 纯代码。
- 【强制】跳转方不得写 `hrs-state-kline.displayValue`，避免与页面生成逻辑冲突、产生脏数据。
- **Why**：标签格式（尤其市场后缀）以索引/行情为唯一真源，集中在页面一处生成，才能保证「搜索框与行情头上下一致」，且索引异步后到也能自动补全后缀。

<a id="sec-3-3"></a>

### 3.3 无参数兜底

**规定**：当跳转目标不带 `stockCode` 时，页面回退到内部 `stockCode` 状态（sessionStorage 持久化的上次代码）；若也为空，则展示「未选股」提示。

**How to apply**：适用于无具体股票的通用入口，例如设置页「查看股票数据」按钮（`SettingsPage.tsx` 中 `navigate('/stock/kline')`）——它面向的是「打开 K 线数据页」而非某只股票，允许不带 `stockCode`，属合理例外。

<a id="sec-4"></a>

## 四、跳转入口清单

| 入口 | 文件 | 模式 | 状态 |
| --- | --- | --- | --- |
| 自选股列表（点股票名） | `pages/WatchlistPage/components/WatchlistStockTable.tsx` | `?stockCode=` | ✅ 已统一 |
| 顶栏全局股票搜索 | `components/layout/ShellHeader.tsx` | `?stockCode=` | ✅ 已统一 |
| 信号扫描结果行 | `pages/Discover/ScannerPage/components/ScannerResultRow.tsx` | `?stockCode=` | ✅ 已统一 |
| 尾盘选股卡片 | `pages/Discover/EodPickerPage/components/EodStockCard.tsx` | `?stockCode=` | ✅ 已统一 |
| 设置页「查看股票数据」 | `pages/SettingsPage.tsx` | 无 code（通用入口） | ➖ 合理保留 |

<a id="sec-5"></a>

## 五、正反清单

| 做 / 不做 | 说明 |
| --- | --- |
| ✅ `navigate('/stock/kline?stockCode=' + encodeURIComponent(code))` | 显式、可复现 |
| ✅ 复用入口已有的代码归一工具 | 避免重复实现 |
| ✅ 无具体股票时才允许 `navigate('/stock/kline')` | 通用入口例外 |
| ❌ `setStorageItem('kline.stockCode', …)` 再 `navigate('/stock/kline')` | 旧模式，已废弃 |
| ❌ 跳转方写 `hrs-state-kline.displayValue` | 标签由页面生成 |
| ❌ 拼接未编码的原始代码到 URL | 需 `encodeURIComponent` |

<a id="sec-6"></a>

## 六、新增入口指引

**How to apply**：新增任何「跳转某只股票 K 线」的入口时，按以下模板实现，无需关心加载与展示细节：

```tsx
import { useNavigate } from 'react-router-dom';

// 组件内
const navigate = useNavigate();

// 持有股票代码 code（纯代码或规范代码均可）时：
const openKline = (code: string) => {
  navigate(`/stock/kline?stockCode=${encodeURIComponent(code)}`);
};
```

- 【强制】不得再新增写 sessionStorage 的跳转写法。
- 【推荐】若入口卡片/行已有点击跳转，沿用上述单行写法，保持全项目一致。

<a id="sec-7"></a>

## 七、兼容性与风险

**规定**：统一后 K 线页仍向后兼容不带 `stockCode` 的直跳（走 [§3.3](#sec-3-3) 兜底），旧书签 / 外部链接不会白屏。

| 项 | 说明 |
| --- | --- |
| 向后兼容 | 不带 `stockCode` 时用上次代码或空态，行为不变 |
| sessionStorage | `kline.stockCode` 仍由页面自身维护（刷新/切路由恢复），仅移除跳转方写入 |
| 展示标签 | 改由页面生成，索引异步后到会自动补后缀；极端情况退化为「名称（纯代码）」 |
| 已验证 | 自选股 / 顶栏 / 扫描 / 尾盘四类入口均改为 `?stockCode=`；K 线页功能测试与直达同步回归通过 |
