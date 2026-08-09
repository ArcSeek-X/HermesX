/**
 * 查询字符串规范化工具
 *
 * 作用：处理用户在搜索/输入框中输入的股票代码或名称，提供统一的大小写、空白、
 * 全半角（NFKC）规范化，并判断输入“像代码 / 像名称 / 像拼音”，以及提取/去除
 * 交易所后缀。是前端搜索与代码解析链路的基础工具。
 */

/**
 * 规范化查询字符串：
 * - NFKC 统一全半角字符
 * - 去除首尾空白
 * - 转小写（便于后续不区分大小写匹配）
 * - 去除内部多余空白
 */
export function normalizeQuery(query: string): string {
  return query
    .normalize('NFKC')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '');
}

/**
 * 判断单个字符是否为中文（基本汉字区）。
 */
export function isChineseChar(char: string): boolean {
  return /[\u4e00-\u9fa5]/.test(char);
}

/**
 * 判断字符串中是否包含中文字符。
 */
export function containsChinese(query: string): boolean {
  return Array.from(query).some(isChineseChar);
}

/**
 * 从股票代码中提取交易所后缀。
 * 例：600519.SH -> SH，00700.HK -> HK
 */
export function extractMarketSuffix(code: string): string | null {
  const match = code.match(/\.([A-Z]+)$/);
  return match ? match[1] : null;
}

/**
 * 去除股票代码的交易所后缀。
 * 例：600519.SH -> 600519，00700.HK -> 00700
 */
export function removeMarketSuffix(code: string): string {
  return code.replace(/\.[A-Z]+$/, '');
}

/**
 * 规范化股票代码：
 * - 转大写
 * - 去除空白
 * - 保留交易所后缀
 */
export function normalizeStockCode(code: string): string {
  return code.trim().toUpperCase().replace(/\s+/g, '');
}

/**
 * 判断查询是否“像股票代码”（含数字且不含中文）。
 */
export function isStockCodeLike(query: string): boolean {
  const normalized = normalizeQuery(query);
  // 含数字且无中文，可能是一个股票代码
  return /\d/.test(normalized) && !containsChinese(normalized);
}

/**
 * 判断查询是否“像股票名称”（含中文）。
 */
export function isStockNameLike(query: string): boolean {
  return containsChinese(query);
}

/**
 * 判断查询是否“像拼音”（仅由字母组成且无中文）。
 */
export function isPinyinLike(query: string): boolean {
  const normalized = normalizeQuery(query);
  return /^[a-z]+$/.test(normalized) && !containsChinese(query);
}
