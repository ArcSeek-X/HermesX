/**
 * 股票名称截断工具
 *
 * 作用：在 UI 空间有限（如标签、列表项）时，对股票名称做按字符类型分级的长度截断，
 * 避免长名称撑破布局。规则：纯英文最多 15 字符、纯中文最多 8 字符、中英混排最多 10 字符，
 * 超出部分截断并补省略号。
 */

/**
 * 各字符类型下允许的最大长度：
 * - 英文：15 字符
 * - 中文：8 字符
 * - 中英混排：10 字符
 */
export const STOCK_NAME_MAX_LENGTH = {
  ENGLISH: 15,
  CHINESE: 8,
  MIXED: 10,
} as const;

/**
 * 根据名称的字符类型返回允许的最大长度。
 * 优先级：中英混排 > 纯中文 > 纯英文。
 *
 * @param name - 股票名称
 * @returns 该类型对应的最大长度
 */
function getMaxLength(name: string): number {
  const isChinese = /[\u4e00-\u9fa5]/.test(name);
  const isMixed = isChinese && /[a-zA-Z]/.test(name);
  if (isMixed) return STOCK_NAME_MAX_LENGTH.MIXED;
  if (isChinese) return STOCK_NAME_MAX_LENGTH.CHINESE;
  return STOCK_NAME_MAX_LENGTH.ENGLISH;
}

/**
 * 按字符类型截断股票名称。
 * - 纯英文：最多 15 字符
 * - 纯中文：最多 8 字符
 * - 中英混排：最多 10 字符
 * 未超长则原样返回，超长则截取并补一个英文句点作为省略号。
 *
 * @param name - 原始股票名称
 * @returns 截断后的名称（或原名称）
 */
export function truncateStockName(name: string): string {
  if (!name) return name;
  const maxLen = getMaxLength(name);
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen) + '.';
}

/**
 * 判断股票名称是否会被截断（用于 UI 是否显示完整名称的 tooltip 等）。
 *
 * @param name - 股票名称
 * @returns 超过最大长度返回 true
 */
export function isStockNameTruncated(name: string): boolean {
  if (!name) return false;
  return name.length > getMaxLength(name);
}
