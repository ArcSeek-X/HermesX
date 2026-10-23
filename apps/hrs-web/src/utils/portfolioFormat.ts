/**
 * 投资组合（Portfolio）展示格式化工具
 *
 * 作用：为组合管理相关页面提供金额、百分比、价格、买卖方向、公司行为、券商等字段的
 * 统一格式化与中文标签，并把后端返回的导入/汇率刷新结果转换为前端提示（tone/variant），
 * 便于 UI 以一致的视觉风格展示各类状态与反馈。
 */

import type {
  PortfolioCashDirection,
  PortfolioCorporateActionType,
  PortfolioFxRefreshResponse,
  PortfolioImportCommitResponse,
  PortfolioImportParseResponse,
  PortfolioPositionItem,
  PortfolioSide,
} from '../types/portfolio';
import { toDateKey } from './format';

/** 汇率刷新反馈：语气（neutral / success / warning）与对应提示文案。 */
export type FxRefreshFeedback = {
  tone: 'neutral' | 'success' | 'warning';
  text: string;
};

/** InlineAlert 视觉变体别名（info / success / warning / danger）。 */
export type PortfolioAlertVariant = 'info' | 'success' | 'warning' | 'danger';

/**
 * 获取当天日期字符串。
 *
 * @returns 本地当天日期，格式 `YYYY-MM-DD`。
 * @example
 * getTodayIso() // "2026-10-22"
 */
export function getTodayIso(): string {
  return toDateKey(new Date());
}

/**
 * 格式化金额：固定两位小数 + 千分位，币种作为前缀。
 *
 * @param value - 金额数值；`undefined` / `null` / `NaN` 时返回占位符。
 * @param currency - 币种代码，作为前缀拼接，默认 `'CNY'`。
 * @returns 形如 `"{币种} {千分位金额}"` 的字符串；无效输入返回 `'--'`。
 * @example
 * formatMoney(1234.5)        // "CNY 1,234.50"
 * formatMoney(1234.5, 'USD') // "USD 1,234.50"
 * formatMoney(null)          // "--"
 */
export function formatMoney(value: number | undefined | null, currency = 'CNY'): string {
  if (value == null || Number.isNaN(value)) return '--';
  return `${currency} ${Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * 格式化百分比：固定两位小数，不做正负号修饰。
 *
 * @param value - 百分比数值（如 `12.3456` 表示 12.3456%）；`undefined` / `null` / `NaN` 时返回占位符。
 * @returns 形如 `"12.35%"` 的字符串；无效输入返回 `'--'`。
 * @example
 * formatPct(12.3456) // "12.35%"
 * formatPct(-3.2)    // "-3.20%"
 * formatPct(null)    // "--"
 */
export function formatPct(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '--';
  return `${value.toFixed(2)}%`;
}

/**
 * 格式化带符号百分比：正值补 `+`，负值保留自带 `-`，零不加号。
 *
 * @param value - 百分比数值；`undefined` / `null` / `NaN` 时返回占位符。
 * @returns 形如 `"+12.35%"` / `"-3.20%"` 的字符串；无效输入返回 `'--'`。
 * @example
 * formatSignedPct(5)    // "+5.00%"
 * formatSignedPct(-3.2) // "-3.20%"
 * formatSignedPct(0)    // "0.00%"
 */
export function formatSignedPct(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * 判断持仓行是否具备有效价格（可用于展示现价 / 市值 / 盈亏）。
 *
 * @param row - 持仓行数据（读取 `priceAvailable` / `priceSource`）。
 * @returns `priceAvailable !== false` 且 `priceSource !== 'missing'` 时为 `true`，否则 `false`。
 * @example
 * hasPositionPrice({ priceAvailable: true, priceSource: 'history_close' }) // true
 * hasPositionPrice({ priceAvailable: false, priceSource: 'missing' })     // false
 */
export function hasPositionPrice(row: PortfolioPositionItem): boolean {
  return row.priceAvailable !== false && row.priceSource !== 'missing';
}

/**
 * 格式化持仓现价：有效价格保留 4 位小数，缺价返回占位符。
 *
 * @param row - 持仓行数据（读取 `lastPrice`，并按 `hasPositionPrice` 判定有效性）。
 * @returns 形如 `"1680.5000"` 的字符串；缺价返回 `'--'`。
 * @example
 * formatPositionPrice({ lastPrice: 1680.5, priceAvailable: true, priceSource: 'history_close' }) // "1680.5000"
 * formatPositionPrice({ lastPrice: 0, priceAvailable: false, priceSource: 'missing' })          // "--"
 */
export function formatPositionPrice(row: PortfolioPositionItem): string {
  if (!hasPositionPrice(row)) return '--';
  return row.lastPrice.toFixed(4);
}

/**
 * 格式化持仓金额：按行的计价币种（`valuationCurrency`）格式化，缺价返回占位符。
 *
 * @param value - 待格式化的金额数值。
 * @param row - 持仓行数据（提供 `valuationCurrency`，并按 `hasPositionPrice` 判定有效性）。
 * @returns 形如 `"HKD 4,200.00"` 的字符串；缺价返回 `'--'`。
 * @example
 * formatPositionMoney(4200, { valuationCurrency: 'HKD', priceAvailable: true, priceSource: 'realtime_quote' }) // "HKD 4,200.00"
 * formatPositionMoney(4200, { valuationCurrency: 'HKD', priceAvailable: false, priceSource: 'missing' })     // "--"
 */
export function formatPositionMoney(value: number, row: PortfolioPositionItem): string {
  if (!hasPositionPrice(row)) return '--';
  return formatMoney(value, row.valuationCurrency);
}

/**
 * 生成持仓现价的口径副文本（价格来源 / 提供商 / 日期）。
 *
 * @param row - 持仓行数据（读取 `priceSource` / `priceProvider` / `priceStale` / `priceDate`）。
 * @returns 缺价 `"缺价"`；实时价 `"实时价"` 或 `"实时价 · {提供商}"`；收盘价 `"收盘价"` 或过期时
 *          `"收盘价 · {日期}"`；其余返回原始 `priceSource`，为空时 `"未知来源"`。
 * @example
 * getPositionPriceLabel({ priceAvailable: true, priceSource: 'realtime_quote', priceProvider: '东方财富' }) // "实时价 · 东方财富"
 * getPositionPriceLabel({ priceAvailable: true, priceSource: 'history_close', priceStale: true, priceDate: '2026-03-18' }) // "收盘价 · 2026-03-18"
 * getPositionPriceLabel({ priceAvailable: false, priceSource: 'missing' }) // "缺价"
 */
export function getPositionPriceLabel(row: PortfolioPositionItem): string {
  if (!hasPositionPrice(row)) return '缺价';
  if (row.priceSource === 'realtime_quote') {
    return row.priceProvider ? `实时价 · ${row.priceProvider}` : '实时价';
  }
  if (row.priceSource === 'history_close') {
    return row.priceStale && row.priceDate ? `收盘价 · ${row.priceDate}` : '收盘价';
  }
  return row.priceSource || '未知来源';
}

/**
 * 买卖方向转中文标签。
 *
 * @param value - 方向值：`'buy'` 或 `'sell'`。
 * @returns `'买入'` 或 `'卖出'`。
 * @example
 * formatSideLabel('buy')  // "买入"
 * formatSideLabel('sell') // "卖出"
 */
export function formatSideLabel(value: PortfolioSide): string {
  return value === 'buy' ? '买入' : '卖出';
}

/**
 * 现金流向转中文标签。
 *
 * @param value - 方向值：`'in'` 或 `'out'`。
 * @returns `'流入'` 或 `'流出'`。
 * @example
 * formatCashDirectionLabel('in')  // "流入"
 * formatCashDirectionLabel('out') // "流出"
 */
export function formatCashDirectionLabel(value: PortfolioCashDirection): string {
  return value === 'in' ? '流入' : '流出';
}

/**
 * 公司行为类型转中文标签。
 *
 * @param value - 行为类型：`'cash_dividend'` 为现金分红，其余归为拆并股调整。
 * @returns `'现金分红'` 或 `'拆并股调整'`。
 * @example
 * formatCorporateActionLabel('cash_dividend') // "现金分红"
 * formatCorporateActionLabel('stock_split')   // "拆并股调整"
 */
export function formatCorporateActionLabel(value: PortfolioCorporateActionType): string {
  return value === 'cash_dividend' ? '现金分红' : '拆并股调整';
}

/**
 * 格式化券商展示名：优先用展示名，其次内置映射，最后原样返回。
 *
 * @param value - 券商代码（如 `'huatai'`）。
 * @param displayName - 可选展示名；非空时以 `"{代码}（{展示名}）"` 返回。
 * @returns 券商标签；无展示名时按内置映射（huatai/citic/cmb）补充中文，仍无则原样返回 `value`。
 * @example
 * formatBrokerLabel('huatai')             // "huatai（华泰）"
 * formatBrokerLabel('huatai', '华泰证券') // "huatai（华泰证券）"
 * formatBrokerLabel('custom')             // "custom"
 */
export function formatBrokerLabel(value: string, displayName?: string): string {
  if (displayName && displayName.trim()) return `${value}（${displayName.trim()}）`;
  if (value === 'huatai') return 'huatai（华泰）';
  if (value === 'citic') return 'citic（中信）';
  if (value === 'cmb') return 'cmb（招商）';
  return value;
}

/**
 * 把汇率刷新结果转换为前端提示（语气 + 文案）。
 *
 * @param data - 汇率刷新响应（读取 `refreshEnabled` / `pairCount` / `updatedCount` / `staleCount` / `errorCount`）。
 * @returns `{ tone, text }`：禁用或无可刷新为 `neutral`；全部成功为 `success`；存在过期或失败为 `warning`。
 * @example
 * buildFxRefreshFeedback({ refreshEnabled: false }) // { tone: 'neutral', text: '汇率在线刷新已被禁用。' }
 * buildFxRefreshFeedback({ updatedCount: 1, staleCount: 0, errorCount: 0, pairCount: 1 }) // { tone: 'success', text: '汇率已刷新，共更新 1 对。' }
 * buildFxRefreshFeedback({ updatedCount: 1, staleCount: 2, errorCount: 0, pairCount: 3 }) // { tone: 'warning', text: '已尝试刷新，但仍有部分货币对使用 stale/fallback 汇率。更新 1 对，仍过期 2 对，失败 0 对。' }
 */
export function buildFxRefreshFeedback(data: PortfolioFxRefreshResponse): FxRefreshFeedback {
  if (data.refreshEnabled === false) {
    return {
      tone: 'neutral',
      text: '汇率在线刷新已被禁用。',
    };
  }

  if (data.pairCount === 0) {
    return {
      tone: 'neutral',
      text: '当前范围无可刷新的汇率对。',
    };
  }

  if (data.updatedCount > 0 && data.staleCount === 0 && data.errorCount === 0) {
    return {
      tone: 'success',
      text: `汇率已刷新，共更新 ${data.updatedCount} 对。`,
    };
  }

  const summary = `更新 ${data.updatedCount} 对，仍过期 ${data.staleCount} 对，失败 ${data.errorCount} 对。`;
  if (data.staleCount > 0) {
    return {
      tone: 'warning',
      text: `已尝试刷新，但仍有部分货币对使用 stale/fallback 汇率。${summary}`,
    };
  }

  return {
    tone: 'warning',
    text: `在线刷新未完全成功。${summary}`,
  };
}

/**
 * 把汇率提示语气映射为 InlineAlert 视觉变体。
 *
 * @param tone - 提示语气：`'success'` / `'warning'` / `'neutral'`。
 * @returns `'success'` / `'warning'` / `'info'`（`neutral` 归为 `info`）。
 * @example
 * getFxRefreshFeedbackVariant('success') // 'success'
 * getFxRefreshFeedbackVariant('neutral') // 'info'
 */
export function getFxRefreshFeedbackVariant(tone: FxRefreshFeedback['tone']): PortfolioAlertVariant {
  if (tone === 'success') return 'success';
  if (tone === 'warning') return 'warning';
  return 'info';
}

/**
 * CSV 解析结果的提示变体：存在错误或跳过行为 `warning`，否则 `info`。
 *
 * @param result - 解析响应（读取 `errorCount` / `skippedCount`）。
 * @returns `'warning'` 或 `'info'`。
 * @example
 * getCsvParseVariant({ errorCount: 0, skippedCount: 0 }) // 'info'
 * getCsvParseVariant({ errorCount: 0, skippedCount: 2 }) // 'warning'
 */
export function getCsvParseVariant(result: PortfolioImportParseResponse): PortfolioAlertVariant {
  return result.errorCount > 0 || result.skippedCount > 0 ? 'warning' : 'info';
}

/**
 * CSV 提交结果的提示变体：演练（dry-run）恒为 `info`；否则有失败 / 重复为 `warning`，全部成功为 `success`。
 *
 * @param result - 提交响应（读取 `failedCount` / `duplicateCount`）。
 * @param isDryRun - 是否为演练模式。
 * @returns `'info'` / `'warning'` / `'success'`。
 * @example
 * getCsvCommitVariant({ failedCount: 0, duplicateCount: 0 }, true)  // 'info'
 * getCsvCommitVariant({ failedCount: 1, duplicateCount: 0 }, false) // 'warning'
 * getCsvCommitVariant({ failedCount: 0, duplicateCount: 0 }, false) // 'success'
 */
export function getCsvCommitVariant(result: PortfolioImportCommitResponse, isDryRun: boolean): PortfolioAlertVariant {
  if (isDryRun) return 'info';
  return result.failedCount > 0 || result.duplicateCount > 0 ? 'warning' : 'success';
}
