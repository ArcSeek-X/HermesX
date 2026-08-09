/**
 * 通用格式化工具
 *
 * 作用：集中提供前端展示所需的格式化函数，覆盖：
 * - 日期/时间（含上海时区的交易日语义）
 * - 报告类型标签
 * - 股票成交量（股→万手/亿手）、成交额与总市值（元→亿/万亿）
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
