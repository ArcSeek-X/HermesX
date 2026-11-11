/**
 * Stock Index Type Definitions
 * 股票指数 / 股票检索类型定义
 *
 * Stock data index for autocomplete functionality.
 * 用于自动补全（autocomplete）功能的股票数据索引。
 *
 * Note: Common market / asset identifiers (AssetType / StockIndexMarketTag) are
 * defined in ./stock and re-used here, since they are project-wide concepts
 * rather than stock-index-specific.
 */
import type { AssetType, StockIndexMarketTag } from './stock';

/**
 * Stock index item (full format)
 * 股票索引项（完整格式）
 */
export interface StockIndexItem {
  /** Canonical code: 600519.SH / 规范代码，带交易所后缀 */
  canonicalCode: string;
  /** Display code: 600519 / 展示代码，不带后缀 */
  displayCode: string;
  /** Chinese name: 贵州茅台 / 中文名称 */
  name: string;
  /** English name: Kweichow Moutai / 英文名称 */
  nameEn?: string;
  /** Pinyin full: guizhoumaotai / 全拼 */
  pinyinFull?: string;
  /** Pinyin abbreviation: gzmt / 拼音首字母缩写 */
  pinyinAbbr?: string;
  /** Aliases: ["茅台"] / 别名（俗称）列表 */
  aliases?: string[];
  /** Market / 所属市场 */
  market: StockIndexMarketTag;
  /** Asset type / 资产类型 */
  assetType: AssetType;
  /** Is active / 是否在市（是否有效） */
  active: boolean;
  /** Popularity / 热度（用于排序） */
  popularity?: number;
  /** Listing date (上市日期), from CSV list_date, e.g. "1991-01-29" / 上市日期，取自 CSV 的 list_date */
  listDate?: string;
}

/**
 * Stock search suggestion item
 * 股票搜索建议项（自动补全结果中用到的精简结构）
 */
export interface StockSuggestion {
  /** Canonical code / 规范代码，带交易所后缀 */
  canonicalCode: string;
  /** Display code / 展示代码，不带后缀 */
  displayCode: string;
  /** Chinese name / 中文名称 */
  name: string;
  /** Market / 所属市场 */
  market: StockIndexMarketTag;
  /** Match type / 匹配类型 */
  matchType: 'exact' | 'prefix' | 'contains' | 'fuzzy';
  /** Match field / 匹配字段 */
  matchField: 'code' | 'name' | 'pinyin' | 'alias';
  /** Sort score / 排序得分 */
  score: number;
}

/**
 * Compressed format stock index item (for reducing file size)
 * 压缩格式的股票索引项（用于减小文件体积）
 */
export type StockIndexTuple = [
  string,  // canonicalCode / 规范代码
  string,  // displayCode / 展示代码
  string,  // name / 中文名称
  string | undefined, // pinyinFull / 全拼
  string | undefined, // pinyinAbbr / 拼音缩写
  string[], // aliases (required, use empty array if none) / 别名列表（必填，无则空数组）
  StockIndexMarketTag, // market / 所属市场
  AssetType, // assetType / 资产类型
  boolean, // active / 是否在市
  number | undefined, // popularity / 热度
  string | undefined, // listDate (上市日期) / 上市日期
];

/**
 * Stock index data (supports two formats)
 * 股票索引数据（支持两种格式：完整对象数组或压缩元组数组）
 */
export type StockIndexData = StockIndexItem[] | StockIndexTuple[];
