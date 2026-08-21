/**
 * 股票搜索算法
 *
 * 作用：基于股票索引（StockIndexItem）实现自动补全搜索，支持多种匹配方式：
 * - 精确匹配：代码、名称、拼音、别名
 * - 前缀匹配：代码前缀、名称前缀、拼音前缀
 * - 包含匹配：代码包含、名称包含、拼音包含
 * 对每条命中结果计算匹配评分（越高越相关），并按评分与热度排序返回 Top N 建议项，
 * 另提供高亮渲染（带 HTML 转义，防止 XSS）供搜索结果 UI 使用。
 */

import type { StockIndexItem, StockSuggestion } from '../types/stockIndex';
import { normalizeQuery } from './normalizeQuery';
import { MATCH_SCORE, SEARCH_CONFIG } from './stockIndexSchema';

/** 搜索选项 */
export interface SearchOptions {
  /** 返回结果数量上限 */
  limit?: number;
  /** 是否只展示在市股票 */
  activeOnly?: boolean;
}

/**
 * 在股票索引中搜索。
 *
 * @param query - 用户输入的查询
 * @param index - 股票索引
 * @param options - 搜索选项
 * @returns 命中的股票建议列表（已排序、截断到 limit）
 */
export function searchStocks(
  query: string,
  index: StockIndexItem[],
  options: SearchOptions = {}
): StockSuggestion[] {
  const normalizedQuery = normalizeQuery(query);
  if (!normalizedQuery) {
    return [];
  }
  const limit = options.limit || SEARCH_CONFIG.DEFAULT_LIMIT;
  const activeOnly = options.activeOnly !== false;

  // 过滤索引：activeOnly 时剔除不在市的股票
  const filteredIndex = index.filter(item => {
    if (activeOnly && !item.active) return false;
    return true;
  });

  // 为每条索引项计算匹配评分
  const suggestions = filteredIndex.map(item => ({
    item,
    score: calculateMatchScore(normalizedQuery, item),
  }));

  // 过滤掉评分为 0（完全不匹配）的项
  const matched = suggestions.filter(s => s.score > 0);

  // 排序：先按评分降序，评分相同时按热度（popularity）降序
  matched.sort((a, b) => {
    if (a.score !== b.score) return b.score - a.score;
    return (b.item.popularity || 0) - (a.item.popularity || 0);
  });

  // 返回前 N 项，并映射为前端所需的建议结构
  return matched.slice(0, limit).map(s => ({
    canonicalCode: s.item.canonicalCode,
    displayCode: s.item.displayCode,
    nameZh: s.item.nameZh,
    market: s.item.market,
    matchType: determineMatchType(s.score),
    matchField: determineMatchField(normalizedQuery, s.item),
    score: s.score,
  }));
}

/**
 * 计算单条索引项相对查询的匹配评分。
 *
 * 评分规则：
 * - 100：精确匹配 canonical code
 * - 99 ：精确匹配 display code
 * - 98 ：精确匹配中文名称
 * - 97 ：精确匹配别名
 * - 96 ：精确匹配拼音缩写
 * - 80-89：前缀匹配（越高越优先）
 * - 60-69：包含匹配
 * - 0  ：不匹配
 */
function calculateMatchScore(query: string, item: StockIndexItem): number {
  let score = 0;
  const q = query.toLowerCase();
  const normalizedCanonicalCode = normalizeQuery(item.canonicalCode);
  const normalizedDisplayCode = normalizeQuery(item.displayCode);
  const normalizedName = normalizeQuery(item.nameZh);
  const normalizedPinyinFull = normalizeQuery(item.pinyinFull || '');
  const normalizedPinyinAbbr = normalizeQuery(item.pinyinAbbr || '');
  const normalizedAliases = item.aliases?.map(alias => normalizeQuery(alias)) || [];

  // 1. 精确匹配（96-100 分），按字段优先级取最高分
  if (q === normalizedCanonicalCode) return 100;
  if (q === normalizedDisplayCode) return 99;
  if (q === normalizedName) return 98;
  if (normalizedAliases.some(a => a === q)) return 97;
  if (q === normalizedPinyinAbbr) return 96;

  // 2. 前缀匹配（77-80 分），用 Math.max 叠加避免后续包含匹配覆盖高分
  if (normalizedDisplayCode.startsWith(q)) score = Math.max(score, 80);
  if (normalizedName.startsWith(q)) score = Math.max(score, 79);
  if (normalizedPinyinAbbr.startsWith(q)) score = Math.max(score, 78);
  if (normalizedAliases.some(a => a.startsWith(q))) score = Math.max(score, 77);

  // 3. 包含匹配（57-60 分）
  if (normalizedDisplayCode.includes(q)) score = Math.max(score, 60);
  if (normalizedName.includes(q)) score = Math.max(score, 59);
  if (normalizedPinyinFull.includes(q)) score = Math.max(score, 58);
  if (normalizedAliases.some(a => a.includes(q))) score = Math.max(score, 57);

  return score;
}

/**
 * 根据评分判断匹配类型（exact / prefix / contains / fuzzy）。
 * 阈值取自 MATCH_SCORE 常量。
 */
function determineMatchType(score: number): 'exact' | 'prefix' | 'contains' | 'fuzzy' {
  if (score >= MATCH_SCORE.EXACT_MIN) return 'exact';
  if (score >= MATCH_SCORE.PREFIX_MIN) return 'prefix';
  if (score >= MATCH_SCORE.CONTAINS_MIN) return 'contains';
  return 'fuzzy';
}

/**
 * 判断匹配命中的字段（code / name / pinyin / alias），用于结果展示“按哪类字段匹配”。
 */
function determineMatchField(query: string, item: StockIndexItem): 'code' | 'name' | 'pinyin' | 'alias' {
  const q = query.toLowerCase();
  const normalizedCanonicalCode = normalizeQuery(item.canonicalCode);
  const normalizedDisplayCode = normalizeQuery(item.displayCode);
  const normalizedName = normalizeQuery(item.nameZh);
  const normalizedPinyinFull = normalizeQuery(item.pinyinFull || '');
  const normalizedPinyinAbbr = normalizeQuery(item.pinyinAbbr || '');
  const normalizedAliases = item.aliases?.map(alias => normalizeQuery(alias)) || [];

  if (normalizedCanonicalCode.includes(q) ||
      normalizedDisplayCode.includes(q)) {
    return 'code';
  }
  if (normalizedName.includes(q)) return 'name';
  if (normalizedPinyinFull.includes(q) ||
      normalizedPinyinAbbr.includes(q)) {
    return 'pinyin';
  }
  if (normalizedAliases.some(a => a.includes(q))) return 'alias';
  return 'name';
}

/**
 * 转义 HTML 特殊字符，防止注入（用于高亮渲染前的文本片段）。
 */
function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * 在文本中高亮命中片段。
 *
 * @param text - 原始文本
 * @param query - 查询字符串
 * @returns 经过 HTML 转义、并用安全 <mark> 标签包裹命中片段的 HTML 字符串
 */
export function highlightMatch(text: string, query: string): string {
  const normalizedQuery = normalizeQuery(query);
  if (!normalizedQuery) return escapeHtml(text);

  const index = text.toLowerCase().indexOf(normalizedQuery);
  if (index === -1) return escapeHtml(text);

  const before = text.substring(0, index);
  const match = text.substring(index, index + normalizedQuery.length);
  const after = text.substring(index + normalizedQuery.length);

  // 返回各转义片段，命中部分用安全 <mark> 包裹
  return `${escapeHtml(before)}<mark>${escapeHtml(match)}</mark>${escapeHtml(after)}`;
}
