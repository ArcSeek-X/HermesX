/**
 * 股票列表字符串解析工具
 *
 * 作用：在用户配置“自选股列表”等场景时，把用户输入的自由文本（可能用空格、英文逗号、
 * 中文逗号、顿号、分号等多种分隔符）解析成规范的股票代码数组，并能反向序列化为
 * 单一的英文逗号分隔字符串，便于存储与后端消费。
 */

// 可识别的分隔符集合（一个或多个连续分隔符视为同一分隔）：
//   空白符（空格/制表/换行）、英文逗号(,)、英文分号(;)、中文逗号(，\uFF0C)、顿号(、\u3001)、中文分号(；\uFF1B)
// 用于把用户自由输入的股票列表文本切分为多个代码。
const STOCK_LIST_SEPARATOR_RE = /[\s,;\uFF0C\u3001\uFF1B]+/;

/**
 * 将用户输入的自选股文本解析为股票代码数组。
 *
 * 处理流程：先把 null/undefined 兜底为空串 → 按 {@link STOCK_LIST_SEPARATOR_RE} 切分
 * → 每项 trim 去空白 → 过滤掉空字符串。本函数只做切分与清洗，不校验代码合法性。
 *
 * @param value - 用户输入的原始字符串，可包含空格/中英文逗号/顿号/分号等混合分隔符，也可为 null/undefined
 * @returns 清洗后的股票代码数组（保持输入顺序，空项已剔除）；无有效输入时返回 []
 *
 * @example
 * parseStockListValue('600519, 000001；00700、AAPL') // => ['600519','000001','00700','AAPL']
 * parseStockListValue('  600519  ')                  // => ['600519']
 * parseStockListValue(null)                          // => []
 * parseStockListValue('')                            // => []
 */
export function parseStockListValue(value: string): string[] {
  return String(value ?? '')
    .split(STOCK_LIST_SEPARATOR_RE)
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * 将用户输入的自选股文本规范化为“英文逗号分隔”的单一字符串，便于存储或提交后端。
 * 等价于先 {@link parseStockListValue} 清洗，再用英文逗号 join。
 *
 * @param value - 用户输入的原始字符串（可含任意受支持的分隔符或 null/undefined）
 * @returns 英文逗号分隔的股票代码串；无有效输入时返回空串 ''
 *
 * @example
 * serializeStockListValue('600519, 000001；00700、AAPL') // => '600519,000001,00700,AAPL'
 * serializeStockListValue(null)                          // => ''
 */
export function serializeStockListValue(value: string): string {
  return parseStockListValue(value).join(',');
}
