/**
 * 股票索引加载器
 *
 * 作用：负责从后端静态资源（/stocks.index.json）加载股票自动补全索引，并支持
 * 对象数组与压缩元组数组两种格式的自动识别与解压。同时提供索引的查找、热门排序、
 * 按市场分组等常用衍生能力。加载失败时返回 fallback 标志，使上层可降级到内置索引或旧模式。
 */

import type { StockIndexData, StockIndexItem, StockIndexTuple } from '../types/stockIndex';
import { INDEX_FIELD } from './stockIndexSchema';

/** 索引加载结果：包含解析后的数据、是否成功、错误信息以及是否进入降级模式 */
export interface IndexLoadResult {
  /** 索引数据（StockIndexItem[] 对象数组；压缩元组格式会在 loadStockIndex 内自动解压为对象数组） */
  data: StockIndexItem[];
  /** 是否成功加载（网络请求与 JSON 解析均无异常） */
  loaded: boolean;
  /** 错误信息：仅当 loaded=false 时存在 */
  error?: Error;
  /** 是否进入降级模式（加载或解析失败时为 true，上层可据此回退到内置索引或旧模式） */
  fallback: boolean;
}

/**
 * 从后端静态资源加载股票自动补全索引（/stocks.index.json）。
 *
 * 行为说明：
 * - 请求时追加按小时取整的 `_t` 时间戳参数，绕过浏览器/CDN 缓存，避免后端未正确处理
 *   ETag / Cache-Control 时读到旧索引文件。
 * - 自动识别两种数据格式：对象数组（StockIndexItem[]）与压缩元组数组（StockIndexTuple[]），
 *   若为压缩格式会先解压成对象数组再返回。
 * - 加载或解析失败时进入降级模式（fallback=true、data 为空数组），上层可据此回退到内置索引或旧模式。
 *
 * @returns 索引加载结果 {@link IndexLoadResult}：成功时 loaded=true、fallback=false；
 *          失败时 loaded=false、fallback=true 且附带 error。
 *
 * @example
 * const result = await loadStockIndex();
 * if (result.loaded) {
 *   console.log(result.data.length); // 股票条数
 * } else {
 *   console.warn('索引加载失败，降级处理', result.error);
 * }
 */
export async function loadStockIndex(): Promise<IndexLoadResult> {
  try {
    // 追加 _t 时间戳（按小时取整）以绕过缓存
    const response = await fetch(`/stocks.index.json?_t=${Math.floor(Date.now() / 3600000)}`);

    if (!response.ok) {
      throw new Error(`Failed to load index: ${response.status} ${response.statusText}`);
    }

    const data: StockIndexData = await response.json();

    // 若为压缩格式（元组数组），先解压成对象数组
    const items = isCompressedFormat(data)
      ? unpackTuples(data as StockIndexTuple[])
      : data as StockIndexItem[];

    return {
      data: items,
      loaded: true,
      fallback: false,
    };
  } catch (error) {
    console.error('[StockIndexLoader] Failed to load stock index:', error);
    return {
      data: [],
      loaded: false,
      error: error as Error,
      fallback: true,  // 加载失败，降级到内置索引/旧模式
    };
  }
}

/**
 * 判断索引数据是否为“压缩元组数组”格式。
 *
 * 判定依据：整体是一个非空数组，且首个元素本身也是数组、其首列为字符串（规范代码）。
 * 对象数组格式的首个元素是普通对象，因此可据此区分两种格式。
 *
 * @param data - 待判定的索引数据（可能是对象数组或元组数组）
 * @returns 为压缩元组数组时返回 true，否则 false
 *
 * @example
 * isCompressedFormat([['600519','600519','贵州茅台']]) // true（元组数组）
 * isCompressedFormat([{ canonicalCode:'600519' }])     // false（对象数组）
 */
function isCompressedFormat(data: StockIndexData): data is StockIndexTuple[] {
  if (!Array.isArray(data) || data.length === 0) return false;
  const firstItem = data[0];
  return Array.isArray(firstItem) && typeof firstItem[0] === 'string';
}

/**
 * 将压缩元组数组解压为可读的对象数组。
 *
 * 字段顺序严格遵循 {@link INDEX_FIELD} 常量（CANONICAL_CODE / DISPLAY_CODE / NAME_ZH / ...），
 * 与后端的索引生成脚本保持一致，新增字段时只需同步 INDEX_FIELD 即可。
 *
 * @param tuples - 压缩元组数组，每个元组的列顺序由 INDEX_FIELD 约定
 * @returns 解压后的对象数组（StockIndexItem[]）
 *
 * @example
 * // 输入：['600519', '600519', '贵州茅台', 'guizhoumaotai', 'gzm', [], 'CN', 'stock', true, 100]
 * // 输出：{ canonicalCode:'600519', displayCode:'600519', nameZh:'贵州茅台', ... }
 */
function unpackTuples(tuples: StockIndexTuple[]): StockIndexItem[] {
  return tuples.map(tuple => ({
    canonicalCode: tuple[INDEX_FIELD.CANONICAL_CODE],
    displayCode: tuple[INDEX_FIELD.DISPLAY_CODE],
    nameZh: tuple[INDEX_FIELD.NAME_ZH],
    pinyinFull: tuple[INDEX_FIELD.PINYIN_FULL],
    pinyinAbbr: tuple[INDEX_FIELD.PINYIN_ABBR],
    aliases: tuple[INDEX_FIELD.ALIASES],
    market: tuple[INDEX_FIELD.MARKET],
    assetType: tuple[INDEX_FIELD.ASSET_TYPE],
    active: tuple[INDEX_FIELD.ACTIVE],
    popularity: tuple[INDEX_FIELD.POPULARITY],
  }));
}

/**
 * 将对象数组压缩为元组数组，用于减小索引文件体积（与后端的索引生成脚本对应）。
 *
 * 与 {@link unpackTuples} 互逆：列顺序由 {@link INDEX_FIELD} 约定，aliases 为空时补 []。
 *
 * @param items - 对象格式的股票索引（StockIndexItem[]）
 * @returns 压缩后的元组数组（StockIndexTuple[]），每个元组的列顺序见 INDEX_FIELD
 *
 * @example
 * compressIndex([{ canonicalCode:'600519', displayCode:'600519', nameZh:'贵州茅台', ... }])
 * // => [['600519','600519','贵州茅台',...]]
 */
export function compressIndex(items: StockIndexItem[]): StockIndexTuple[] {
  return items.map(item => [
    item.canonicalCode,
    item.displayCode,
    item.nameZh,
    item.pinyinFull,
    item.pinyinAbbr,
    item.aliases || [],
    item.market,
    item.assetType,
    item.active,
    item.popularity,
  ]);
}

/**
 * 在索引中按规范代码（canonicalCode）精确查找某只股票。
 *
 * @param canonicalCode - 规范代码，如 '600519.SH' / 'HK00700' / 'AAPL'（需与索引中的 canonicalCode 完全一致）
 * @param index - 股票索引（StockIndexItem[]）
 * @returns 命中的索引项；未找到时返回 null
 *
 * @example
 * findStockInIndex('600519.SH', index) // => { canonicalCode:'600519.SH', nameZh:'贵州茅台', ... }
 * findStockInIndex('000000.SH', index) // => null
 */
export function findStockInIndex(
  canonicalCode: string,
  index: StockIndexItem[]
): StockIndexItem | null {
  return index.find(item => item.canonicalCode === canonicalCode) || null;
}

/**
 * 获取热门股票列表：仅包含在市（active=true）股票，按 popularity 降序排列后截取前 limit 条。
 *
 * @param index - 股票索引（StockIndexItem[]）
 * @param limit - 返回数量上限，默认 20（传入 <=0 或非数字时仍按默认 20 处理）
 * @returns 热门股票数组（StockIndexItem[]），已按热度从高到低排序
 *
 * @example
 * getPopularStocks(index)      // 前 20 只
 * getPopularStocks(index, 10)  // 前 10 只
 */
export function getPopularStocks(
  index: StockIndexItem[],
  limit: number = 20
): StockIndexItem[] {
  return [...index]
    .filter(item => item.active)
    .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
    .slice(0, limit);
}

/**
 * 将索引原始 market 标记归一化为"地域分组键"（小写）。
 * - 地域标记 CN/HK/US/JP/KR/TW → 小写 cn/hk/us/jp/kr/tw；
 * - BSE（北交所）→ 并入 cn 桶，不单独成桶（见 stock_type.md §6 方案 A）；
 * - INDEX/ETF/UNKNOWN 等非地域标记 → 小写原值（index/etf/unknown），保留为独立桶，避免丢数据。
 */
function toMarketGroupKey(rawMarket: string): string {
  const tag = String(rawMarket || '').trim().toUpperCase();
  if (tag === 'BSE') return 'cn';
  return tag.toLowerCase();
}

/**
 * 按市场（地域）对股票分组，仅包含在市（active=true）股票。
 * 分组键为归一化后的小写地域（北交所并入 cn）。
 *
 * @param index - 股票索引（StockIndexItem[]）
 * @returns 市场地域（如 'cn' / 'hk' / 'us'） -> 该市场股票数组 的 Map；
 *          退市股票（active=false）会被跳过
 *
 * @example
 * const groups = groupStocksByMarket(index);
 * groups.get('cn') // => StockIndexItem[]（A股，含北交所）
 * groups.get('hk') // => StockIndexItem[]（港股）
 */
export function groupStocksByMarket(
  index: StockIndexItem[]
): Map<string, StockIndexItem[]> {
  const grouped = new Map<string, StockIndexItem[]>();

  for (const item of index) {
    if (!item.active) continue;

    const market = toMarketGroupKey(item.market);
    if (!grouped.has(market)) {
      grouped.set(market, []);
    }
    const group = grouped.get(market);
    if (group) {
      group.push(item);
    }
  }

  return grouped;
}
