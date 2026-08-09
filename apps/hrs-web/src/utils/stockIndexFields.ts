/**
 * 股票索引字段常量定义
 *
 * 作用：定义股票自动补全索引（stocks.index.json）中每条记录的字段顺序与常量。
 * 索引为了减小体积，采用“对象数组”与“元组数组（压缩格式）”两种形态，
 * 本文件集中维护字段名、压缩格式下的下标映射、匹配评分阈值和搜索配置，
 * 供 stockIndexLoader 等模块统一引用，避免散落的魔法数字。
 */

/** 股票索引项的字段名列表（同时用于压缩格式元组下标的语义说明） */
export const STOCK_INDEX_FIELDS = [
  'canonicalCode',
  'displayCode',
  'nameZh',
  'pinyinFull',
  'pinyinAbbr',
  'aliases',
  'market',
  'assetType',
  'active',
  'popularity',
] as const;

/**
 * 压缩格式（元组数组）中各字段的下标。
 * 例如 tuple[INDEX_FIELD.CANONICAL_CODE] 即 canonicalCode。
 */
export const INDEX_FIELD = {
  CANONICAL_CODE: 0,
  DISPLAY_CODE: 1,
  NAME_ZH: 2,
  PINYIN_FULL: 3,
  PINYIN_ABBR: 4,
  ALIASES: 5,
  MARKET: 6,
  ASSET_TYPE: 7,
  ACTIVE: 8,
  POPULARITY: 9,
} as const;

/**
 * 搜索匹配评分阈值（得分 0-100）：
 * - EXACT_MIN：精确匹配的最低分
 * - PREFIX_MIN：前缀匹配的最低分
 * - CONTAINS_MIN：包含匹配的最低分
 * - FUZZY_MIN：模糊匹配的最低分
 */
export const MATCH_SCORE = {
  EXACT_MIN: 96,   // 精确匹配最低分
  PREFIX_MIN: 77,  // 前缀匹配最低分
  CONTAINS_MIN: 57, // 包含匹配最低分
  FUZZY_MIN: 1,    // 模糊匹配最低分
} as const;

/**
 * 搜索相关配置：
 * - DEFAULT_LIMIT：默认返回结果数
 * - DEBOUNCE_MS：输入防抖延迟（毫秒）
 * - MIN_QUERY_LENGTH：触发搜索的最小查询长度
 * - ACTIVE_ONLY：是否只展示在市（active）股票
 */
export const SEARCH_CONFIG = {
  DEFAULT_LIMIT: 10,      // 默认返回结果数
  DEBOUNCE_MS: 200,       // 防抖延迟（毫秒）
  MIN_QUERY_LENGTH: 2,    // 最小查询长度
  ACTIVE_ONLY: true,      // 仅展示在市股票
} as const;
