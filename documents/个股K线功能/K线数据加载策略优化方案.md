# K线数据加载策略优化方案

> 版本：v2.0
> 日期：2026-08-05
> 状态：待评审
> 基于现有代码分析

***

## 一、背景与问题

### 1.1 当前实现（基于代码现状）

| 组件                 | 现状                                                         | 代码位置                                 |
| ------------------ | ---------------------------------------------------------- | ------------------------------------ |
| 后端默认 limit         | `2000`（所有周期统一）                                             | `api/v1/endpoints/kline.py` L691     |
| 前端默认 limit         | `10000`（所有周期统一）                                            | `apps/dsa-web/src/api/kline.ts` L108 |
| 5日K实现              | 错误：`"5d": 1` 复用1分钟分时数据，过滤最近5个交易日                           | `kline.py` L64, L208-221             |
| 分页加载               | 不支持左滑追加历史数据                                                | —                                    |
| dataZoom 初始范围      | `start: 0, end: 100`（显示全部数据）                               | `KLineChart.tsx` L884                |
| 全量数据开关             | UI 已实现（Switch 组件），但未接入数据加载逻辑                               | `StockKLinePage.tsx` L87, L274-281   |
| `loadStockData` 签名 | `loadStockData(code: string, p: KLinePeriod)` — 无 limit 参数 | `StockKLinePage.tsx` L95             |

### 1.2 核心问题

1. **一刀切的 limit 不合理**：前端统一传 `limit=10000`，分钟线拉10000条会卡顿，年K拉10000条浪费
2. **5日K概念错误**：当前用1分钟数据模拟5日（过滤最近5个交易日的分钟数据）
3. **支持切换全量数据查询和部分数据查询**：需要根据是否是全量数据（股票从上市交易以来的所有数据）来切换是否加载全量数据，无法左滑加载更早历史，用户体验差
4. **渲染性能风险**：分钟线一次性加载过多数据导致 ECharts 卡顿
5. **开关未接入逻辑**：全量数据 Switch 组件已渲染，但 `onChange={setShowSwitch}` 只改状态，不影响数据请求

***

## 二、设计原则

### 2.1 两个核心概念区分

| 概念          | 定义                               | 控制方                     |
| ----------- | -------------------------------- | ----------------------- |
| **接口返回总条数** | 后端给到前端的全部 bar 数组长度（预加载，供左右拖动）    | 后端 API `limit` 参数       |
| **屏幕可见柱子**  | 当前视口肉眼看到多少根（ECharts dataZoom 控制） | 前端 `dataZoom.start/end` |

### 2.2 行业标准参考

| 周期   | 含义           | 数据颗粒度   | 渲染类型                 |      每交易日产出bar数 |        接口默认返回(预加载) |              屏幕可见柱子(一屏) | 业务说明                                                |
| :--- | :----------- | :------ | :------------------- | --------------: | -----------------: | ----------------------: | :-------------------------------------------------- |
| 1m   | 当日分时         | 1分钟     | line折线+bar成交量        |             240 |       240根（当日全部分钟） | 240（全部展示，不开启dataZoom滑块） | 带分时均价线；无蜡烛K线；仅返回当日，不回溯历史；Y轴支持价格/涨跌幅双模式              |
| 5分   | 5分钟K线        | 5分钟     | candlestick蜡烛+bar成交量 |              48 |       240根（约5个交易日） |                  80‑120 | K线蜡烛；左滑边界分页追加历史；支持dataZoom缩放                        |
| 15分  | 15分钟K线       | 15分钟    | candlestick蜡烛+bar成交量 |              16 |      200根（约12个交易日） |                  80‑120 | K线蜡烛；左滑边界分页追加历史；支持dataZoom缩放                        |
| 30分  | 30分钟K线       | 30分钟    | candlestick蜡烛+bar成交量 |               8 |      160根（约20个交易日） |                  80‑120 | K线蜡烛；左滑边界分页追加历史；支持dataZoom缩放                        |
| 60分  | 60分钟K线(1小时)  | 60分钟    | candlestick蜡烛+bar成交量 |               4 |      120根（约30个交易日） |                  70‑100 | K线蜡烛；左滑边界分页追加历史；支持dataZoom缩放                        |
| 120分 | 120分钟K线(2小时) | 120分钟   | candlestick蜡烛+bar成交量 |               2 |      100根（约50个交易日） |                   60‑90 | K线蜡烛；左滑边界分页追加历史；支持dataZoom缩放                        |
| 日K   | 日线           | 交易日     | candlestick蜡烛+bar成交量 |               1 |       250根（近1年交易日） |                  80‑120 | K线蜡烛；行业通用默认；左滑分页追加更早历史；支持dataZoom缩放                 |
| 五日   | 五日多日分时       | 1分钟     | line折线+bar成交量        |             240 | 1200根（5个交易日完整分钟数据） |    1200（全部展示，无dataZoom） | **非蜡烛K线**；拼接5个交易日分时，带分时均价；Y轴默认涨跌幅；X轴做交易日分割标记；不做分页加载 |
| 周K   | 周线           | 自然交易周聚合 | candlestick蜡烛+bar成交量 | 0.2（每周5交易日合成1根） |          150根（约3年） |                   60‑80 | K线蜡烛；可全量返回，数据量极大时再分页；支持dataZoom缩放                   |
| 月K   | 月线           | 自然月聚合   | candlestick蜡烛+bar成交量 |      1/12（每月1根） |           80根（约7年） |                   40‑60 | K线蜡烛；直接返回上市以来全部数据；支持dataZoom缩放                      |
| 年K   | 年线           | 自然年聚合   | candlestick蜡烛+bar成交量 |            1根/年 |          40根（上市全部） |                   20‑30 | K线蜡烛；**从日K本地聚合**（历史年日期≈12-31，当年≈当前交易日）；总量很小，全量返回；支持dataZoom缩放 |

***

## 三、后端改造方案

### 3.1 周期默认 limit 映射表

**文件**：`api/v1/endpoints/kline.py`

**当前代码**（L687-692）：

```python
@router.get("/{stock_code}/kline", response_model=KLineResponse)
def get_kline(
    stock_code: str,
    period: str = Query("daily", ...),
    limit: int = Query(2000, ge=1, le=10000, description="数据条数"),
    fqt: int = Query(1, ge=0, le=2, ...),
):
```

**改为**：

```python
# 新增：各周期默认预加载条数（模块顶部，L70 附近）
PERIOD_DEFAULT_LIMITS = {
    "1m":    240,    # 分时：当日全部分钟数据
    "5m":    240,    # 5分钟：约5个交易日
    "15m":   200,    # 15分钟：约12个交易日
    "30m":   160,    # 30分钟：约20个交易日
    "60m":   120,    # 60分钟：约30个交易日
    "120m":  100,    # 120分钟：约50个交易日
    "5d":    120,    # 5日K：约2.5年（需修复聚合逻辑）
    "daily": 250,    # 日K：近1年
    "weekly": 150,   # 周K：约3年
    "monthly": 80,   # 月K：约7年
    "yearly": 40,    # 年K：上市以来全部
}

# 接口签名修改（L687-692）
@router.get("/{stock_code}/kline", response_model=KLineResponse)
def get_kline(
    stock_code: str,
    period: str = Query("daily", ...),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="数据条数（不传则使用周期默认值）"),
    fqt: int = Query(1, ge=0, le=2, ...),
    before_date: Optional[str] = Query(None, description="分页加载：返回此日期之前的数据"),
):
    # 如果前端未传 limit，使用周期默认值
    if limit is None:
        limit = PERIOD_DEFAULT_LIMITS.get(period, 250)
    
    # ... 原有逻辑不变
```

**变更点**：

- `limit` 默认值从 `2000` 改为 `None`（自动根据周期选择）
- 新增 `before_date` 可选参数（用于分页加载，详见 3.4）
- 前端可以不传 `limit`，后端自动使用合理默认值

### 3.2 前端 API 客户端调整

**文件**：`apps/dsa-web/src/api/kline.ts`

**当前代码**（L105-118）：

```typescript
async fetchKLine(
    stockCode: string,
    period: KLinePeriod = 'daily',
    limit: number = 10000,  // ← 硬编码默认 10000
    fqt: number = 1,
): Promise<KLineResponse> {
    const response = await apiClient.get<KLineResponse>(
      `/api/v1/kline/${stockCode}/kline`,
      { params: { period, limit, fqt } },
    );
    return response.data;
},
```

**改为**：

```typescript
async fetchKLine(
    stockCode: string,
    period: KLinePeriod = 'daily',
    limit?: number,          // ← 改为可选，不传则后端使用周期默认值
    fqt: number = 1,
    beforeDate?: string,     // ← 新增：分页加载
): Promise<KLineResponse> {
    const params: Record<string, any> = { period, fqt };
    if (limit !== undefined) params.limit = limit;
    if (beforeDate) params.before_date = beforeDate;

    const response = await apiClient.get<KLineResponse>(
      `/api/v1/kline/${stockCode}/kline`,
      { params },
    );
    return response.data;
},
```

### 3.3 5日K线修复

**当前错误实现**（`kline.py` 三处相同逻辑）：

```python
# 新浪 L208-221 / 东方财富 L337-349 / 腾讯 L489-502
# 5日周期（5d）：只返回最近5个交易日的分钟数据
if period == "5d" and kline_data:
    dates = []
    seen = set()
    for item in reversed(kline_data):
        date_part = item["date"].split(" ")[0]
        if date_part not in seen:
            seen.add(date_part)
            dates.append(date_part)
        if len(dates) >= 5:
            break
    kline_data = [item for item in kline_data if item["date"].split(" ")[0] in seen]
```

**正确实现**：每5个交易日合成1根K线

**方案 A（推荐）：后端本地聚合**

在 `kline.py` 中新增聚合函数，修改5日K数据获取流程：

```python
def _aggregate_5d_kline(daily_data: List[Dict]) -> List[Dict]:
    """
    将日K数据聚合为5日K线
    
    规则：
    - 每5个交易日合成1根K线
    - 开盘价：第1天的开盘价
    - 收盘价：第5天的收盘价
    - 最高价：5天中的最高价
    - 最低价：5天中的最低价
    - 成交量：5天成交量之和
    - 成交额：5天成交额之和
    - 涨跌幅：5天累计涨跌幅
    - 换手率：5天换手率之和
    """
    result = []
    for i in range(0, len(daily_data), 5):
        chunk = daily_data[i:i+5]
        if not chunk:
            continue
        
        aggregated = {
            "date": chunk[-1]["date"],  # 使用最后一天日期
            "open": chunk[0]["open"],
            "close": chunk[-1]["close"],
            "high": max(d["high"] for d in chunk),
            "low": min(d["low"] for d in chunk),
            "volume": sum(d["volume"] or 0 for d in chunk),
            "amount": sum(d["amount"] or 0 for d in chunk),
            "change_percent": chunk[-1].get("change_percent"),  # 使用最后一天的涨跌幅
            "turnover_rate": sum(d.get("turnover_rate") or 0 for d in chunk),
        }
        result.append(aggregated)
    
    return result
```

**修改数据获取流程**：

在 `_get_kline_data` 函数（L512-575）中，5日K不再走分钟线分支，改为走日K分支 + 本地聚合：

```python
# 修改 _get_kline_data 的分支逻辑
# 将 "5d" 从分钟线分支移到日K分支

if period in ("daily", "weekly", "monthly", "yearly", "5d"):
    # 日K及以上周期（含5日K）
    # ... 原有日K获取逻辑 ...
    
    # 5日K特殊处理：获取日K后聚合
    if period == "5d" and kline_data:
        # 5日K需要更多日K数据来聚合（120根5日K × 5天 = 600根日K）
        # 如果数据不够，重新拉取更多
        if len(kline_data) < 600:
            _, more_daily = _get_kline_data(stock_code, "daily", 600, fqt)
            if more_daily:
                kline_data = more_daily
        kline_data = _aggregate_5d_kline(kline_data)
    
    return stock_name, kline_data
else:
    # 分钟线：新浪 → 腾讯 → 东方财富（原逻辑不变）
```

**同时删除**三个数据源函数中的5日K过滤逻辑：

- `_fetch_kline_from_sina` L208-221（删除）
- `_fetch_kline_from_eastmoney` L337-349（删除）
- `_fetch_kline_from_tencent` L489-502（删除）

**修改** **`SINA_SCALE_MAP`** **和** **`EASTMONEY_KLT_MAP`**：

```python
# 5d 不再复用1分钟，改为复用日K
SINA_SCALE_MAP = {
    # ...
    "5d": 240,   # 改为复用日K数据（240分钟=日K）
    # ...
}
```

> 注意：新浪 API 不直接支持5日K周期，所以5日K的获取策略是：拉取日K数据 → 本地聚合。
> 东方财富和腾讯同理，`"5d"` 在各自映射表中也应改为日K的 klt 值。

### 3.4 分页加载支持（左滑追加历史）

**新增** **`before_date`** **参数处理**：

在 `get_kline` 接口中（L687+），当传入 `before_date` 时，返回该日期之前的数据：

```python
# 在获取 kline_data 之后，添加 before_date 过滤
if before_date and kline_data:
    # kline_data 已按日期升序排列
    # 找到 before_date 的位置其之前的数据
    kline_data = [item for item in kline_data if item["date"] < before_date]
    # 取最后 limit 条
    kline_data = kline_data[-limit:]
```

**前端调用示例**：

```typescript
// 首次加载：不传 limit 和 beforeDate，后端使用周期默认值
klineApi.fetchKLine("603019", "daily")
// → 返回最近250根日K

// 左滑追加：传最早日期，返回更早的250根
klineApi.fetchKLine("603019", "daily", 250, 1, "2025-08-01")
// → 返回2025-08-01之前的250根日K
```

***

## 四、前端改造方案

### 4.1 全量数据开关（接入数据加载逻辑）

**文件**：`apps/dsa-web/src/pages/StockKLinePage.tsx`

**当前状态**：

- Switch 组件已渲染（L274-281），但 `onChange={setShowSwitch}` 只更新状态
- `loadStockData`（L95-134）不接受 `limit` 参数，始终调用 `klineApi.fetchKLine(code, p)` 使用默认值

**改造步骤**：

#### 步骤 1：修改 `loadStockData` 支持 limit 参数

```typescript
// 当前（L95）
const loadStockData = useCallback(async (code: string, p: KLinePeriod) => {

// 改为
const loadStockData = useCallback(async (code: string, p: KLinePeriod, limit?: number) => {
```

并在内部调用处传入 limit：

```typescript
// 当前（L104）
klineApi.fetchKLine(code, p),

// 改为
klineApi.fetchKLine(code, p, limit),
```

#### 步骤 2：开关变化时重新加载数据

```typescript
// 当前（L276-277）
onChange={setShowSwitch}

// 改为
onChange={(checked: boolean) => {
  setShowSwitch(checked);
  // 开启：传 limit=10000 拉全量；关闭：不传 limit，使用后端周期默认值
  const limit = checked ? 10000 : undefined;
  if (stockCodeRef.current) {
    void loadStockData(stockCodeRef.current, periodRef.current, limit);
  }
}}
```

#### 步骤 3：周期切换时保持开关状态

```typescript
// 当前 handlePeriodChange（L185-194）
const handlePeriodChange = useCallback(
  (newPeriod: KLinePeriod) => {
    setPeriod(newPeriod);
    if (stockCodeRef.current) {
      void loadStockData(stockCodeRef.current, newPeriod);
    }
  },
  [loadStockData, setPeriod],
);

// 改为：切换周期时，如果开关开启，传入 limit=10000
const handlePeriodChange = useCallback(
  (newPeriod: KLinePeriod) => {
    setPeriod(newPeriod);
    if (stockCodeRef.current) {
      const limit = showSwitch ? 10000 : undefined;
      void loadStockData(stockCodeRef.current, newPeriod, limit);
    }
  },
  [loadStockData, setPeriod, showSwitch],
);
```

**完整 UI 布局**（保持现有结构不变）：

```tsx
{/* 当前已实现（L272-283） */}
<div className="flex items-center justify-between">
  {/* 分时图模式下，切换开关自动隐藏 */}
  {period !== '1m' && (
    <Switch
      checked={showSwitch}
      onChange={handleFullDataToggle}
      label="全量数据"
      className="whitespace-nowrap text-muted-text"
    />
  )}
  <PeriodSelector period={period} onChange={handlePeriodChange} />
</div>
```

**交互逻辑总结**：

| 用户操作       | 开关状态 | 传给后端的 limit | 行为             |
| ---------- | ---- | ----------- | -------------- |
| 首次加载       | 关闭   | 不传（后端用默认值）  | 按周期返回合理数量      |
| 打开开关       | 开启   | `10000`     | 拉取全量历史数据       |
| 切换周期（开关开启） | 开启   | `10000`     | 新周期也拉全量        |
| 切换周期（开关关闭） | 关闭   | 不传          | 新周期使用默认值       |
| 分时模式       | —    | —           | 开关隐藏，始终只返回当日数据 |

### 4.2 dataZoom 初始可见范围

**文件**：`apps/dsa-web/src/components/kline/KLineChart.tsx`

**当前代码**（L883-894）：

```typescript
dataZoom: [
  { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: 0, end: 100 },
  {
    type: 'slider', xAxisIndex: [0, 1, 2, 3],
    top: '88%', height: 24, start: 0, end: 100,
    // ...
  },
],
```

**问题**：`start: 0, end: 100` 显示全部数据，数据量大时柱子挤在一起。

**改造**：根据周期计算初始可见范围，只显示最近 N 根柱子：

```typescript
// 在 KLineChart.tsx 顶部（computeMA 函数附近）新增常量
/** 各周期初始可见柱子数量（一屏显示） */
const PERIOD_VISIBLE_BARS: Record<string, number> = {
  "5m":    100,
  "15m":   100,
  "30m":   100,
  "60m":   80,
  "120m":  70,
  "5d":    70,
  "daily": 100,
  "weekly": 70,
  "monthly": 50,
  "yearly": 30,
};
```

**在** **`useEffect`** **内计算 dataZoom 初始值**（非分时分支，约 L880 处）：

```typescript
// 计算 dataZoom 初始范围
const visibleBars = PERIOD_VISIBLE_BARS[period] || 100;
const totalBars = data.length;
// 如果总数据少于可见柱子，显示全部
const dzStart = totalBars > visibleBars
  ? ((totalBars - visibleBars) / totalBars) * 100
  : 0;

// 替换原有 dataZoom 配置
dataZoom: [
  { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: dzStart, end: 100 },
  {
    type: 'slider', xAxisIndex: [0, 1, 2, 3],
    top: '88%', height: 24, start: dzStart, end: 100,
    textStyle: { color: colors.textColor, fontSize: 11 },
    borderColor: colors.axisLineColor,
    fillerColor: 'rgba(0, 212, 255, 0.15)',
    handleStyle: { color: '#00d4ff', borderWidth: 2, width: 10, height: 26 },
    moveHandleSize: 8, showDetail: false,
  },
],
```

**效果**：

- 日K 250条数据 → 初始显示最近100条（start=60, end=100）
- 年K 40条数据 → 全部显示（start=0, end=100，因为 40 < 30 不满足条件 → 实际 40 > 30，start=25）
- 用户仍可通过 dataZoom 滑块/滚轮查看完整历史

### 4.3 左滑分页加载

**文件**：`apps/dsa-web/src/pages/StockKLinePage.tsx`

**新增状态**：

```typescript
const [isLoadingMore, setIsLoadingMore] = useState(false);
```

**方案**：监听 KLineChart 的 dataZoom 事件，当用户拖动到最左侧时触发分页加载。

**问题**：当前 `KLineChart` 组件的 dataZoom 事件监听在组件内部（`KLineChart.tsx` L1021-1029），父组件无法直接感知。

**解决方案**：给 `KLineChart` 新增 `onDataZoomBoundary` 回调 prop。

#### KLineChart.tsx 改动

```typescript
// Props 新增（L64-73）
type KLineChartProps = {
  data: KLinePoint[];
  period: KLinePeriod;
  height?: string;
  prevClose?: number | null;
  /** 新增：当 dataZoom 拖动到左边界时触发 */
  onDataZoomBoundary?: () => void;
};

// 在现有的 dataZoom 事件处理中（L1021-1029）添加边界检测
const handleDataZoom = (params: any) => {
  if (params.batch) {
    const batch = params.batch[0];
    const start = batch.start ?? 0;
    const end = batch.end ?? 100;
    const count = Math.round(data.length * (end - start) / 100);
    visibleCountRef.current = Math.max(1, count);
    
    // 新增：当拖动到左边界 5% 以内时，触发分页加载
    if (start <= 5 && onDataZoomBoundary) {
      onDataZoomBoundary();
    }
  }
};
```

#### StockKLinePage.tsx 改动

```typescript
// 新增分页加载逻辑
const loadMoreHistory = useCallback(async () => {
  if (isLoadingMore || klineData.length === 0) return;
  
  const earliestDate = klineData[0]?.date;
  if (!earliestDate) return;
  
  setIsLoadingMore(true);
  try {
    const moreData = await klineApi.fetchKLine(
      stockCode,
      period,
      250,           // 每次加载250条
      1,
      earliestDate,  // beforeDate：返回此日期之前的数据
    );
    
    if (moreData?.data?.length > 0) {
      // 将新数据插入到现有数据前面
      setPageState('kline', (prev) => ({
        ...prev,
        klineData: [...moreData.data, ...prev.klineData],
      }));
    }
  } catch (err) {
    console.error('Failed to load more history:', err);
  } finally {
    setIsLoadingMore(false);
  }
}, [isLoadingMore, klineData, stockCode, period, setPageState]);

// KLineChart 传入回调
<KLineChart
  data={klineData}
  period={period}
  height="500px"
  prevClose={prevClose}
  onDataZoomBoundary={loadMoreHistory}
/>
```

### 4.4 分钟线性能保护

**文件**：`apps/dsa-web/src/components/kline/KLineChart.tsx`

**问题**：分钟线如果用户持续左滑加载，可能累积数千条数据导致 ECharts 卡顿。

**解决方案**：

1. **分钟线最大加载上限**（在 `StockKLinePage.tsx` 中控制）：

```typescript
const MINUTE_KLINE_MAX_LIMIT = 5000;

const loadMoreHistory = useCallback(async () => {
  // 分钟线保护
  const isMinutePeriod = ['5m', '15m', '30m', '60m', '120m'].includes(period);
  if (isMinutePeriod && klineData.length >= MINUTE_KLINE_MAX_LIMIT) {
    return; // 静默停止加载
  }
  // ... 原有分页加载逻辑
}, [...]);
```

1. **ECharts 降采样**（在 `KLineChart.tsx` 的 candlestick series 中添加）：

```typescript
// 非分时蜡烛图 series（当前 L901-938）
{
  name: 'kline',
  type: 'candlestick',
  data: klineData,
  // 新增：大数据量时启用降采样
  ...(data.length > 500 ? { sampling: 'lttb' } : {}),
  itemStyle: { ... },
  // ...
}
```

> 注意：`sampling: 'lttb'` 仅对折线图/柱状图有效，candlestick 类型不支持。
> 对于 K 线图，大数据量的性能保护主要依赖 dataZoom 限制可见范围 + 分页加载，而非降采样。

### 4.5 时间轴标签密度自适应

**当前实现**（`KLineChart.tsx` L839-843）：

```typescript
interval: (index: number) => {
  const threshold = isSmallScreen ? 20 : 30;
  if (visibleCountRef.current <= threshold) return true;
  return timeAxisLabelIndices.has(index);
},
```

**问题**：`visibleCountRef.current` 初始值等于 `data.length`，当 dataZoom 初始 `start > 0` 时，实际可见柱子数远小于 `data.length`，导致标签过密。

**改造**：在 dataZoom 事件处理中同步更新 `visibleCountRef`，并在初始化时设置正确值：

```typescript
// 初始化时根据 dataZoom 起始值设置可见数量
const actualVisibleBars = Math.min(visibleBars, totalBars);
visibleCountRef.current = actualVisibleBars;
```

***

## 五、5日K线修复详细方案

### 5.1 当前错误实现

**三个数据源中都有相同逻辑**：

| 数据源  | 文件位置                | 错误逻辑                                |
| ---- | ------------------- | ----------------------------------- |
| 新浪   | `kline.py` L208-221 | `"5d": 1` → scale=1 获取分钟数据 → 过滤最近5天 |
| 东方财富 | `kline.py` L337-349 | `"5d": 1` → klt=1 → 同上              |
| 腾讯   | `kline.py` L489-502 | `"5d": "1min"` → 同上                 |

**问题**：

- 返回的是分钟级数据（数百根），不是5日K线
- 概念混淆：5日分时 ≠ 5日K线

### 5.2 正确实现方案

**核心思路**：5日K = 每5个交易日合成1根K线，数据源使用日K。

**修改** **`SINA_SCALE_MAP`** **/** **`EASTMONEY_KLT_MAP`** **/** **`TENCENT_PERIOD_MAP`**：

```python
# 5d 映射改为日K的参数
SINA_SCALE_MAP["5d"] = 240       # 日K
EASTMONEY_KLT_MAP["5d"] = 101    # 日K
TENCENT_PERIOD_MAP["5d"] = "day" # 日K
```

**修改** **`_get_kline_data`** **分支逻辑**（L512-575）：

```python
def _get_kline_data(stock_code, period, limit, fqt):
    # 5日K：使用日K数据聚合
    if period == "5d":
        # 需要更多日K数据来聚合（120根5日K × 5 = 600根日K）
        fetch_limit = max(limit * 5, 600)
        _, daily_data = _get_kline_data(stock_code, "daily", fetch_limit, fqt)
        if daily_data:
            stock_name = _get_stock_name_from_cache(stock_code)
            return stock_name, _aggregate_5d_kline(daily_data)
        return None, []
    
    # 日K及以上周期（原逻辑不变）
    if period in ("daily", "weekly", "monthly", "yearly"):
        # ...
```

**删除三个数据源函数中的5d特殊处理**：

- `_fetch_kline_from_sina` L208-221
- `_fetch_kline_from_eastmoney` L337-349
- `_fetch_kline_from_tencent` L489-502

***

## 六、年K线修复详细方案

### 6.1 当前问题

- 腾讯API对年K线支持不佳，只返回当天数据（代码注释已明确记录）
- 东方财富/新浪的年K线数据由API端聚合，日期格式和聚合规则不可控
- 无法保证每根K线的日期为该年12-31（或年末最后一个交易日）

### 6.2 正确实现方案

**核心思路**：年K = 按自然年分组日K数据，每年合成1根K线，数据源使用日K。

**新增 `_aggregate_yearly_kline` 聚合函数**：

```python
def _aggregate_yearly_kline(daily_data: list) -> list:
    """
    将日K数据聚合为年K线

    规则：
    - 按自然年分组，每年合成1根K线
    - 开盘价：该年第一个交易日的开盘价
    - 收盘价：该年最后一个交易日的收盘价
    - 最高价：该年所有交易日中的最高价
    - 最低价：该年所有交易日中的最低价
    - 成交量：该年成交量之和
    - 成交额：该年成交额之和
    - 日期：该年最后一个交易日的日期
      - 历史年：约为 12-31（实际为年末最后一个交易日）
      - 当年：截止到当前交易日
    """
    from collections import OrderedDict
    yearly_groups = OrderedDict()
    for item in daily_data:
        year = item["date"][:4]
        if year not in yearly_groups:
            yearly_groups[year] = []
        yearly_groups[year].append(item)

    result = []
    for year, chunk in yearly_groups.items():
        aggregated = {
            "date": chunk[-1]["date"],   # 该年最后一个交易日
            "open": chunk[0]["open"],    # 该年第一个交易日开盘价
            "close": chunk[-1]["close"], # 该年最后一个交易日收盘价
            "high": max(d["high"] for d in chunk),
            "low": min(d["low"] for d in chunk),
            "volume": sum(d["volume"] or 0 for d in chunk),
            "amount": sum(d["amount"] or 0 for d in chunk),
            "change_percent": chunk[-1].get("change_percent"),
            "turnover_rate": sum(d.get("turnover_rate") or 0 for d in chunk),
        }
        result.append(aggregated)
    return result
```

**修改 `_get_kline_data` 分支逻辑**：

```python
def _get_kline_data(stock_code, period, limit, fqt):
    # ... 5d 分支 ...

    # 年K：使用日K数据聚合（第三方API对年K支持不佳）
    if period == "yearly":
        stock_name, daily_data = _get_kline_data(stock_code, "daily", 10000, fqt)
        if daily_data:
            return stock_name, _aggregate_yearly_kline(daily_data)
        return None, []

    # 日K/周K/月K（原逻辑，不再包含 yearly）
    if period in ("daily", "weekly", "monthly"):
        # ...
```

**清理旧的年K特殊处理**：

- 删除复权分支中的 `if kline_data and (period != "yearly" or len(kline_data) >= 2)` 判断
- 删除注释“腾讯API对年K线支持不佳”
- `period in (...)` 中移除 `"yearly"`

***

## 七、成交量单位统一

### 7.1 问题描述

三个数据源的成交量单位不一致：

| 数据源 | f56/volume 单位 | amount 说明 |
| --- | --- | --- |
| 东方财富 | **手**（1手=100股） | 真实成交额（元） |
| 腾讯 | **股** | 估算值 = volume × close |
| 新浪 | **股** | 估算值 = volume × close |

前端 `formatVolume` 假设 volume 单位为"手"（`vol / 10000 → 万手`），如果数据来自腾讯/新浪（单位为股），成交量显示会偏小100倍。

### 7.2 修复方案

**统一内部单位为"股"，输出时转为"手"**：

```python
# 1. _fetch_kline_from_eastmoney() 中：东方财富 vol 从手转股（×100）
raw_vol = float(parts[5]) if parts[5] != "-" else None
"volume": raw_vol * 100 if raw_vol is not None else None,

# 2. get_kline() 端点中：返回前端前从股转手（÷100）
for item in kline_data:
    if item.get("volume") is not None:
        item["volume"] = item["volume"] / 100
```

**数据流**：

```
东方财富(f56=手) → ×100 → 股 ─┐
腾讯(原始=股) ──────── 股 ─┼→ 聚合(5d/yearly) → ÷100 → 手 → 前端
新浪(原始=股) ──────── 股 ─┘
```

### 7.3 验证

- 年K 2025年（东方财富数据）：vol=11659.79万手 ✓，amt=9855.83亿 ✓
- 日/周/月K 均包含当前交易日数据 ✓
- 成交额来自东方财富真实值（非腾讯估算值） ✓

***

## 八、改动清单

### 8.1 后端文件

| 文件                          | 改动                                                                                                                                                                                                                                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `api/v1/endpoints/kline.py` | 1. 新增 `PERIOD_DEFAULT_LIMITS` 映射表2. `get_kline` 接口 `limit` 改为 `Optional[int]`，默认 `None`3. 新增 `before_date` 可选参数 + 过滤逻辑4. 新增 `_aggregate_5d_kline` 聚合函数5. 新增 `_aggregate_yearly_kline` 聚合函数6. 修改 `_get_kline_data` 分支：5d/yearly 走日K聚合7. 删除三个数据源函数中的5d过滤逻辑8. 删除旧的年K特殊处理逻辑9. 修改 `SINA_SCALE_MAP`/`EASTMONEY_KLT_MAP`/`TENCENT_PERIOD_MAP` 中5d映射10. **东方财富 vol ×100（手→股），统一内部单位为股**11. **`get_kline` 端点 vol ÷100（股→手），匹配前端预期** |

### 8.2 前端文件

| 文件                                                 | 改动                                                                                                                                                                                      |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/dsa-web/src/api/kline.ts`                    | 1. `fetchKLine` 的 `limit` 改为可选参数2. 新增 `beforeDate` 参数                                                                                                                                   |
| `apps/dsa-web/src/components/kline/KLineChart.tsx` | 1. 新增 `PERIOD_VISIBLE_BARS` 常量2. dataZoom `start` 按周期计算（替换 `start: 0`）3. Props 新增 `onDataZoomBoundary` 回调4. dataZoom 事件处理中添加左边界检测5. 初始化 `visibleCountRef` 为正确的可见数量                      |
| `apps/dsa-web/src/pages/StockKLinePage.tsx`        | 1. `loadStockData` 新增 `limit?` 参数2. Switch `onChange` 接入数据加载逻辑3. `handlePeriodChange` 感知开关状态4. 新增 `isLoadingMore` 状态5. 新增 `loadMoreHistory` 分页加载函数6. KLineChart 传入 `onDataZoomBoundary` |

***

## 九、验证计划

### 9.1 后端验证

```bash
# 1. 验证各周期默认 limit（不传 limit 参数）
curl "http://localhost:8000/api/v1/kline/603019/kline?period=5m"
# 预期：返回约240条数据

curl "http://localhost:8000/api/v1/kline/603019/kline?period=daily"
# 预期：返回约250条数据

curl "http://localhost:8000/api/v1/kline/603019/kline?period=yearly"
# 预期：返回20-40条数据

# 2. 验证5日K线（应为合成K线，非分钟数据）
curl "http://localhost:8000/api/v1/kline/603019/kline?period=5d"
# 预期：返回约120条数据，每条代表5个交易日

# 3. 验证分页加载
curl "http://localhost:8000/api/v1/kline/603019/kline?period=daily&before_date=2025-08-01"
# 预期：返回2025-08-01之前的数据

# 4. 验证前端传 limit 覆盖默认值
curl "http://localhost:8000/api/v1/kline/603019/kline?period=daily&limit=10000"
# 预期：返回全量数据
```

### 9.2 前端验证

1. **初始加载**：
   - 切换各周期，验证 dataZoom 初始可见柱子数量符合预期（日K约100根、年K约30根）
   - 验证滑块位置正确（不是从头到尾显示）
2. **全量数据开关**：
   - 分时图模式下开关不显示 ✓（已实现）
   - 非分时图模式下开关显示，默认关闭
   - 开启开关 → 验证 limit=10000 全量加载
   - 关闭开关 → 验证恢复周期默认数据量
   - 切换周期时 → 验证开关状态保持，数据按当前开关状态重新加载
3. **左滑分页**：
   - 拖动 dataZoom 滑块到最左侧
   - 验证自动加载更早历史数据
   - 验证新数据插入到现有数据前面
   - 验证图表不闪烁
4. **5日K线**：
   - 验证显示为真正的5日合成K线（非分钟数据）
   - 验证K线数量约120根
   - 验证每根K线代表5个交易日
5. **分钟线性能**：
   - 持续左滑加载分钟线
   - 验证超过5000条时停止加载

***

## 十、风险与回滚

### 10.1 风险点

| 风险                             | 影响     | 缓解措施                           |
| ------------------------------ | ------ | ------------------------------ |
| 5日K线聚合逻辑错误                     | 数据不准确  | 与通达信/同花顺对比验证                   |
| 分页加载导致数据重复                     | 图表显示异常 | 后端 `before_date` 严格过滤 + 前端日期去重 |
| dataZoom 初始范围变更影响现有体验          | 用户需适应  | 可通过滑块查看完整数据                    |
| 默认 limit 变更影响现有用户              | 数据量变化  | 前端可显式传 limit 覆盖                |
| `_get_kline_data` 递归调用5d→daily | 潜在死循环  | 5d分支内直接调用数据源函数而非递归             |

### 10.2 回滚方案

1. **后端回滚**：恢复 `limit` 默认值为 `2000`，移除 `before_date` 参数，恢复5d原逻辑
2. **前端回滚**：恢复 `fetchKLine` 默认 `limit=10000`，恢复 `dataZoom start: 0, end: 100`，移除分页逻辑
3. **开关回滚**：Switch 组件保持现有UI，只需将 `onChange` 恢复为 `setShowSwitch`

***

## 十一、实施顺序

建议按以下顺序实施，每步可独立验证：

1. **后端** **`PERIOD_DEFAULT_LIMITS`** **+** **`limit`** **可选** → 验证各周期默认数据量
2. **前端** **`fetchKLine`** **limit 可选** → 验证前端不传 limit 时后端行为正确
3. **全量数据开关接入逻辑** → 验证开关切换时数据量变化
4. **dataZoom 初始可见范围** → 验证各周期初始显示柱子数量
5. **5日K线修复** → 验证合成K线数据正确性
6. **分页加载（before\_date + 左滑）** → 验证左滑追加历史
7. **分钟线性能保护** → 验证大数据量下流畅度

***

## 十二、总结

本方案核心改动：

1. **后端**：按周期智能设置默认 limit，支持分页加载，修复5日K线为日K聚合
2. **前端 API**：`limit` 改为可选，新增 `beforeDate` 参数
3. **前端图表**：dataZoom 初始范围按周期调整，支持左边界检测触发分页
4. **前端页面**：全量数据开关接入数据加载逻辑，新增分页加载状态管理
5. **性能**：分钟线最大加载上限，避免卡顿

预期效果：

- 各周期初始加载数据量合理，渲染流畅
- 用户可通过开关主动选择加载全量历史
- 用户可左滑查看更早历史，体验接近专业行情软件
- 5日K线概念正确，数据准确

