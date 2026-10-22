/**
 * 通用数字 / 金额格式化工具
 *
 * 提供可复用的数字展示原语 formatNumber：按需千分位分组、固定小数位、百分比换算，
 * 并可加前后缀与正负号；覆盖金额、百分比、带符号涨跌、原始数值等展示场景。
 * 与 portfolioFormat 等业务格式化解耦，供全项目按需引用。
 */

/** formatNumber 的格式化选项 */
export interface FormatNumberOptions {
  /** 是否启用千分位分组，默认 true */
  grouping?: boolean;
  /** 保留小数位数，默认 2；传 0 取整 */
  decimals?: number;
  /**
   * 百分比处理，默认 false：
   * - true：数值 ×100 并追加 '%'（用于比率，如 0.1234 → "12.34%"）；
   * - 'suffix'：不缩放，仅追加 '%'（用于已是百分比的数值，如 12.34 → "12.34%"）；
   * - false：不加 '%'。
   */
  percent?: boolean | 'suffix';
  /** 正值是否补 '+' 号，默认 false */
  signed?: boolean;
  /** 前缀（如货币符号 '¥'），默认无 */
  prefix?: string;
  /** 后缀（如单位 ' 元'），默认无 */
  suffix?: string;
  /** 无效值（null / undefined / NaN / Infinity）占位符，默认 '--' */
  fallback?: string;
}

/**
 * 通用数字格式化：按需千分位分组、固定小数位、百分比换算，并可加前后缀与正负号。
 *
 * 设计为可复用的数字展示原语，覆盖「金额 / 百分比 / 带符号涨跌 / 原始数值」等场景；
 * 无效值（null / undefined / NaN / Infinity）统一返回占位符。
 *
 * @param value - 待格式化的数值。
 * @param options - 格式化选项，详见 FormatNumberOptions。
 * @returns 格式化后的字符串。
 * @example
 * formatNumber(1234.5)                                   // "1,234.50"（默认千分位 + 2 位小数）
 * formatNumber(1234.5, { grouping: false })              // "1234.50"
 * formatNumber(1680.5, { decimals: 4 })                  // "1,680.5000"
 * formatNumber(0.123456, { percent: true, decimals: 2 }) // "12.35%"（×100 后加 %）
 * formatNumber(12.34, { percent: 'suffix' })             // "12.34%"（仅加 %，不缩放）
 * formatNumber(5, { signed: true })                      // "+5.00"
 * formatNumber(-3.2, { signed: true })                   // "-3.20"
 * formatNumber(1234.5, { prefix: '¥ ' })                 // "¥ 1,234.50"
 * formatNumber(88, { suffix: ' 元', decimals: 0 })       // "88 元"
 * formatNumber(null)                                     // "--"
 * formatNumber(NaN, { fallback: 'N/A' })                 // "N/A"
 */
export function formatNumber(value: number | undefined | null, options: FormatNumberOptions = {}): string {
  const {
    grouping = true,
    decimals = 2,
    percent = false,
    signed = false,
    prefix = '',
    suffix = '',
    fallback = '--',
  } = options;

  if (value == null || !Number.isFinite(value)) return fallback;

  // percent === true 时按比率 ×100；'suffix' 仅加 % 不缩放
  const scaled = percent === true ? value * 100 : value;
  const fixed = scaled.toFixed(decimals);

  let body = fixed;
  if (grouping) {
    const negative = fixed.startsWith('-');
    const [intPart, decPart] = (negative ? fixed.slice(1) : fixed).split('.');
    const groupedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    body = `${negative ? '-' : ''}${groupedInt}${decPart ? `.${decPart}` : ''}`;
  }

  const sign = signed && scaled > 0 ? '+' : '';
  const percentSuffix = percent ? '%' : '';
  return `${prefix}${sign}${body}${percentSuffix}${suffix}`;
}
