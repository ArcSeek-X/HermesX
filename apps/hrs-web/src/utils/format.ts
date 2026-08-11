/**
 * 通用格式化工具
 *
 * 作用：集中提供前端展示所需的格式化函数，覆盖：
 * - 日期/时间（含上海时区的交易日语义）
 * - 报告类型标签
 * - 股票/指数点位（保留指定位数小数）
 * - 股票成交量（股→万手/亿手）、成交额与总市值（元→亿/万亿）
 * - 带符号指标（涨跌幅/涨跌额/净流入等）与涨跌颜色（stock-up 红涨 / stock-down 绿跌）
 * 成交量与金额的换算单位与后端 StockInfo 字段原始单位对齐，并支持中英文单位切换。
 */

/**
 * 格式化日期时间为 yyyy/MM/dd HH:mm 格式（zh-CN locale）。
 *
 * @param value - ISO 日期字符串或日期时间字符串，可为 null/undefined
 * @returns 格式化后的日期时间字符串，或无效输入返回原值/占位符
 */
export const formatDateTime = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

/**
 * 格式化日期为 yyyy/MM/dd 格式（zh-CN locale）。
 *
 * @param value - ISO 日期字符串，可为 null/undefined
 * @returns 格式化后的日期字符串，或无效输入返回原值/占位符
 */
export const formatDate = (value?: string): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
};

/**
 * 将 Date 对象转为 YYYY-MM-DD 格式，用于 HTML <input type="date"> 的 value。
 *
 * @param date - JavaScript Date 对象
 * @returns 例如 "2026-08-05"
 */
export const toDateInputValue = (date: Date): string => {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Returns the date N days ago as YYYY-MM-DD in Asia/Shanghai timezone.
 * Consistent with getTodayInShanghai() so both ends of the date range
 * are expressed in the same timezone as the backend.
 */
export const getRecentStartDate = (days: number): string => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(date);
};

/**
 * Returns today's date as YYYY-MM-DD in Asia/Shanghai timezone.
 * Use this instead of the browser-local date for market-day UI semantics.
 */
export const getTodayInShanghai = (): string =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date());

/**
 * 将报告类型枚举值映射为用户可见的中文标签。
 *
 * @param value - 报告类型：simple/detailed/full/brief/market_review/others
 * @returns 中文标签，未知/空值返回 "—"
 */
export const formatReportType = (value?: string): string => {
  if (!value) return '—';
  if (value === 'simple') return '普通';
  if (value === 'detailed') return '标准';
  if (value === 'full') return '完整';
  if (value === 'brief') return '简版';
  if (value === 'market_review') return '大盘';
  return value;
};

/**
 * 格式化股票/指数点位（保留指定位数小数）
 *
 * 通用点位展示入口：指数点位、个股最新价等数值统一走此函数，
 * 避免各处散落 toFixed 调用；null 时返回占位符。
 *
 * @param value  - 点位数值，可为 null
 * @param digits - 保留小数位数，默认 2
 * @returns 格式化后的点位字符串，如 "3324.44"；value 为 null 时返回 "--"
 *
 * @example
 * formatPricePoint(3324.445) → "3324.44" 
 * formatPricePoint(null)     → "--"
 */
export const formatPricePoint = (value: number | null, digits = 2): string => {
  if (value == null) return '--';
  return value.toFixed(digits);
};

/**
 * 格式化股票成交量（原始单位：股）
 *
 * 数据源返回的成交量原始单位为“股”，业务层统一转换为“手”显示。
 * 1 手 = 100 股，万手 = 股 ÷ 10000 ÷ 100。
 *
 * 阈值规则：
 * - >= 10,000 万手（即 1 亿手）：按“亿手”显示，保留两位小数
 * - <  10,000 万手                 ：按“万手”显示，保留两位小数
 *
 * @param value - 股票成交量，单位：股（来自后端 StockInfo.volume），可为 null
 * @param t     - i18n 翻译函数，用于中/英文单位文案切换
 * @returns 格式化后的成交量和单位，例如 "12.50万手"、"3.28亿手"、"12.50M"、"3.28B"；
 *          如果 value 为 null，返回 "-"
 *
 * @example
 * formatStockVolumeFromShares(125000000, zhT)  →  "12.50万手"
 * formatStockVolumeFromShares(32800000000, zhT) →  "3.28亿手"
 * formatStockVolumeFromShares(125000000, enT)  →  "12.50M"
 * formatStockVolumeFromShares(null, zhT)       →  "-"
 */
export const formatStockVolumeFromShares = (
  value: number | null,
  t: (key: string) => string
): string => {
  if (value == null) return '-';
  // 股 → 万手：1 手 = 100 股，万手 = 股 ÷ 10000 ÷ 100
  const wanShou = value / 10000 / 100;
  if (wanShou >= 10000) {
    return `${(wanShou / 10000).toFixed(2)}${t('stockUnit.volumeHundredMillionLots')}`;
  }
  return `${wanShou.toFixed(2)}${t('stockUnit.volumeTenThousandLots')}`;
};

/**
 * 格式化股票成交额（原始单位：元）
 *
 * 数据源返回的成交额原始单位为“元”，业务层统一转换为“亿”或“万亿”显示。
 *
 * 阈值规则：
 * - >= 10,000 亿（即 1 万亿）：按“万亿”显示，保留两位小数
 * - <  10,000 亿              ：按“亿”显示，保留两位小数
 *
 * @param value - 股票成交额，单位：元（来自后端 StockInfo.amount），可为 null
 * @param t     - i18n 翻译函数，用于中/英文单位文案切换
 * @returns 格式化后的成交额和单位，例如 "5.68亿"、"1.23万亿"、"5.68B"、"1.23T"；
 *          如果 value 为 null，返回 "-"
 *
 * @example
 * formatStockTurnoverAmount(568000000, zhT)        →  "5.68亿"
 * formatStockTurnoverAmount(123000000000000, zhT)  →  "1.23万亿"
 * formatStockTurnoverAmount(568000000, enT)        →  "5.68B"
 * formatStockTurnoverAmount(null, zhT)             →  "-"
 */
export const formatStockTurnoverAmount = (
  value: number | null,
  t: (key: string) => string
): string => {
  if (value == null) return '-';
  // 元 → 亿：1 亿 = 100,000,000 元
  const yi = value / 100000000;
  if (yi >= 10000) {
    return `${(yi / 10000).toFixed(2)}${t('stockUnit.amountWanYi')}`;
  }
  return `${yi.toFixed(2)}${t('stockUnit.amountYi')}`;
};

/**
 * 格式化股票总市值（原始单位：元）
 *
 * 数据源返回的总市值原始单位为“元”，业务层统一转换为“亿”或“万亿”显示。
 * 计算逻辑与成交额相同（原始单位一致），但语义独立，便于未来差异化调整。
 *
 * 阈值规则：
 * - >= 10,000 亿（即 1 万亿）：按“万亿”显示，保留两位小数
 * - <  10,000 亿              ：按“亿”显示，保留两位小数
 *
 * @param value - 股票总市值，单位：元（来自后端 StockInfo.total_market_cap），可为 null
 * @param t     - i18n 翻译函数，用于中/英文单位文案切换
 * @returns 格式化后的市值和单位，例如 "3500.00亿"、"2.50万亿"、"3500.00B"、"2.50T"；
 *          如果 value 为 null，返回 "-"
 *
 * @example
 * formatStockMarketCap(350000000000, zhT)         →  "3500.00亿"
 * formatStockMarketCap(250000000000000, zhT)      →  "2.50万亿"
 * formatStockMarketCap(350000000000, enT)         →  "3500.00B"
 * formatStockMarketCap(null, zhT)                 →  "-"
 */
export const formatStockMarketCap = (
  value: number | null,
  t: (key: string) => string
): string => {
  if (value == null) return '-';
  // 元 → 亿：1 亿 = 100,000,000 元
  const yi = value / 100000000;
  if (yi >= 10000) {
    return `${(yi / 10000).toFixed(2)}${t('stockUnit.amountWanYi')}`;
  }
  return `${yi.toFixed(2)}${t('stockUnit.amountYi')}`;
};

/**
 * 格式化成交额（原始单位：元 → 亿/万亿）
 *
 * 通用金额展示入口，无 i18n 依赖（固定中文单位），适合成交额、净流入等
 * 需要"亿/万亿"展示的场景；null/undefined/NaN 返回占位符。
 *
 * @param amount - 金额数值，单位：元，可为 null/undefined
 * @returns 格式化后的金额，如 "6924.12亿"、"1.53万亿"；非法值返回 "--"
 *
 * @example
 * formatAmount(692412000000) → "6924.12亿"
 * formatAmount(null)         → "--"
 */
export const formatAmount = (amount: number | null | undefined): string => {
  if (amount == null || Number.isNaN(amount)) return '--';
  const yi = Math.abs(amount) / 1e8;
  if (yi >= 10000) {
    return `${(yi / 10000).toFixed(2)}万亿`;
  }
  return `${yi.toFixed(2)}亿`;
};

/**
 * 格式化带符号金额（元 → 亿/万亿，正数带 +）
 *
 * 用于净流入/净流出类指标展示；负数为 "-"，零不带符号。
 *
 * @param amount - 金额数值，单位：元，可为 null/undefined
 * @returns 格式化后的带符号金额，如 "+136.50亿"、"-85.20亿"；非法值返回 "--"
 *
 * @example
 * formatSignedAmount(13650000000)  → "+136.50亿"
 * formatSignedAmount(-8520000000)  → "-85.20亿"
 * formatSignedAmount(null)         → "--"
 */
export const formatSignedAmount = (amount: number | null | undefined): string => {
  if (amount == null || Number.isNaN(amount)) return '--';
  const sign = amount > 0 ? '+' : amount < 0 ? '-' : '';
  return `${sign}${formatAmount(Math.abs(amount))}`;
};

/**
 * 格式化百分比（带符号，保留 2 位小数）
 *
 * 用于涨跌幅、净流入占比等百分比指标展示；负数为 "-"，零不带符号。
 *
 * @param value - 百分比数值（如 1.23 表示 1.23%），可为 null/undefined
 * @returns 格式化后的百分比，如 "+1.23%"、"-0.85%"；非法值返回 "--"
 *
 * @example
 * formatPercent(1.23)  → "+1.23%"
 * formatPercent(-0.85) → "-0.85%"
 * formatPercent(null)  → "--"
 */
export const formatPercent = (value: number | null | undefined): string => {
  if (value == null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

/**
 * 涨跌颜色 class（A 股红涨绿跌）
 *
 * 正数返回 stock-up（红），负数返回 stock-down（绿），零/空返回 muted；
 * 与全局主题色定义保持一致，供行情类数值展示统一着色。
 *
 * @param value - 涨跌数值（涨跌幅/涨跌额/净流入等），可为 null/undefined
 * @returns 颜色 class 字符串
 *
 * @example
 * getChangeColorClass(1.23)  → "stock-up"
 * getChangeColorClass(-0.5)  → "stock-down"
 * getChangeColorClass(0)     → "text-muted-text"
 */
export const getChangeColorClass = (value: number | null | undefined): string => {
  if (value == null || value === 0) return 'text-muted-text';
  return value > 0 ? 'stock-up' : 'stock-down';
};
