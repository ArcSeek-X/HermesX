/**
 * 股票列表字符串解析工具
 *
 * 作用：在用户配置“自选股列表”等场景时，把用户输入的自由文本（可能用空格、英文逗号、
 * 中文逗号、顿号、分号等多种分隔符）解析成规范的股票代码数组，并能反向序列化为
 * 单一的英文逗号分隔字符串，便于存储与后端消费。
 */

// 可识别的分隔符集合：空白符、英文逗号、英文分号、中文逗号（，）、顿号（、）、中文分号（；）
const STOCK_LIST_SEPARATOR_RE = /[\s,;\uFF0C\u3001\uFF1B]+/;

/**
 * 将用户输入的自选股文本解析为股票代码数组。
 *
 * @param value - 用户输入的原始字符串（可能为 null/undefined）
 * @returns 去除空白并过滤空项后的股票代码数组
 */
export function parseStockListValue(value: string): string[] {
  return String(value ?? '')
    .split(STOCK_LIST_SEPARATOR_RE)
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * 将用户输入的自选股文本规范化为英文逗号分隔的字符串。
 *
 * @param value - 用户输入的原始字符串
 * @returns 以英文逗号拼接的股票代码串（如 "600519,00700,AAPL"）
 */
export function serializeStockListValue(value: string): string {
  return parseStockListValue(value).join(',');
}
