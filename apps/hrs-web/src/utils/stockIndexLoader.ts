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
  /** 索引数据 */
  data: StockIndexItem[];
  /** 是否成功加载 */
  loaded: boolean;
  /** 错误信息 */
  error?: Error;
  /** 是否使用了降级模式（加载失败时为 true） */
  fallback: boolean;
}

/**
 * 加载股票索引。
 * 通过追加小时级时间戳参数绕过浏览器缓存（防止后端未正确处理 ETag/Cache-Control 时读到旧文件）。
 *
 * @returns 索引加载结果
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
 * 判断数据是否为压缩格式（元组数组）。
 * 依据：整体是数组、非空、首个元素本身也是数组且首列为字符串。
 */
function isCompressedFormat(data: StockIndexData): data is StockIndexTuple[] {
  if (!Array.isArray(data) || data.length === 0) return false;
  const firstItem = data[0];
  return Array.isArray(firstItem) && typeof firstItem[0] === 'string';
}

/**
 * 将压缩元组格式解压为可读的对象格式，字段顺序参考 INDEX_FIELD 常量。
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
 * 将对象数组压缩为元组数组，用于减小索引文件体积（通常与后端的生成脚本对应）。
 *
 * @param items - 对象格式的股票索引
 * @returns 元组格式的股票索引
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
 * 在索引中按 canonicalCode 查找某只股票。
 *
 * @param canonicalCode - 规范化代码
 * @param index - 股票索引
 * @returns 命中的索引项，未找到返回 null
 */
export function findStockInIndex(
  canonicalCode: string,
  index: StockIndexItem[]
): StockIndexItem | null {
  return index.find(item => item.canonicalCode === canonicalCode) || null;
}

/**
 * 获取热门股票列表（按 popularity 降序，仅限在市股票）。
 *
 * @param index - 股票索引
 * @param limit - 返回数量上限，默认 20
 * @returns 热门股票列表
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
 * 按市场（market）对股票进行分组。
 *
 * @param index - 股票索引
 * @returns 市场名 -> 该市场股票数组 的 Map（仅含在市股票）
 */
export function groupStocksByMarket(
  index: StockIndexItem[]
): Map<string, StockIndexItem[]> {
  const grouped = new Map<string, StockIndexItem[]>();

  for (const item of index) {
    if (!item.active) continue;

    const market = item.market;
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
