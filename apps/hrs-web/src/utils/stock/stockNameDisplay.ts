/**
 * 股票名称截断工具
 *
 * 作用：在 UI 空间有限（如标签、列表项）时，对股票名称做按字符类型分级的长度截断，
 * 避免长名称撑破布局。规则：纯英文最多 15 字符、纯中文最多 8 字符、中英混排最多 10 字符，
 * 超出部分截断并补省略号。
 */

/**
 * 各字符类型下允许的最大显示长度（按“视觉宽度”粗略估算，中文约占 2 个英文宽度）。
 * - 英文（ENGLISH）：15 字符
 * - 中文（CHINESE）：8 字符
 * - 中英混排（MIXED）：10 字符
 *
 * 超出对应上限时由 {@link truncateStockName} 截断并补 '.'。可按 UI 密度调整这些值。
 *
 * @example
 * '贵州茅台'（4 中文 ≤ 8）不截断；'英唐智控股份有限公司'（10 中文）截断为前 8 字 + '.'
 * 'TSLA'（4 英文 ≤ 15）不截断；'Berkshire Hathaway'（17 英文）截断为前 15 字 + '.'
 */
export const STOCK_NAME_MAX_LENGTH = {
  ENGLISH: 15,
  CHINESE: 8,
  MIXED: 10,
} as const;

/**
 * 根据名称的字符构成返回允许的最大长度（内部工具函数）。
 * 判定优先级：中英混排（MIXED）> 纯中文（CHINESE）> 纯英文（ENGLISH）。
 *
 * @param name - 股票名称（任意字符串）
 * @returns 对应类型的最大长度（取自 STOCK_NAME_MAX_LENGTH）
 *
 * @example
 * getMaxLength('贵州茅台')   // => 8（纯中文）
 * getMaxLength('TSLA')       // => 15（纯英文）
 * getMaxLength('英唐智控A')  // => 10（中英混排）
 */
function getMaxLength(name: string): number {
  const isChinese = /[\u4e00-\u9fa5]/.test(name);
  const isMixed = isChinese && /[a-zA-Z]/.test(name);
  if (isMixed) return STOCK_NAME_MAX_LENGTH.MIXED;
  if (isChinese) return STOCK_NAME_MAX_LENGTH.CHINESE;
  return STOCK_NAME_MAX_LENGTH.ENGLISH;
}

/**
 * 按字符类型截断股票名称以适配有限 UI 空间。
 * 规则：纯英文最多 15 字符、纯中文最多 8 字符、中英混排最多 10 字符（阈值见 STOCK_NAME_MAX_LENGTH）。
 * 未超长则原样返回；超长则截取前 N 字符并补一个英文句点 '.' 作为省略号。
 *
 * @param name - 原始股票名称（空串等假值原样返回）
 * @returns 截断后的名称；未超长时返回原名称
 *
 * @example
 * truncateStockName('贵州茅台')                // => '贵州茅台'（未超长）
 * truncateStockName('英唐智控股份有限公司')     // => '英唐智控股份.'（前 8 中文 + '.'）
 * truncateStockName('Berkshire Hathaway')      // => 'Berkshire Hatha.'（前 15 英文 + '.'）
 */
export function truncateStockName(name: string): string {
  if (!name) return name;
  const maxLen = getMaxLength(name);
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen) + '.';
}

/**
 * 判断股票名称是否会被 {@link truncateStockName} 截断。
 * 常用于 UI 决定是否显示完整名称的 tooltip / title 属性。
 *
 * @param name - 股票名称（空串返回 false）
 * @returns 超过最大长度返回 true，否则 false
 *
 * @example
 * isStockNameTruncated('英唐智控股份有限公司') // => true
 * isStockNameTruncated('贵州茅台')            // => false
 */
export function isStockNameTruncated(name: string): boolean {
  if (!name) return false;
  return name.length > getMaxLength(name);
}
