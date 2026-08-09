/**
 * 大盘分析区域（Region）工具
 *
 * 作用：定义大盘分析（market review）支持的区域枚举，以及它们的展示顺序常量，
 * 并提供将区域多选集合序列化为接口所需的字符串（全选时记为 'both'，否则用逗号拼接）。
 */

import type { MarketReviewRegion } from '../types/analysis';

export type { MarketReviewRegion };

export const MARKET_REVIEW_REGION_ORDER: readonly MarketReviewRegion[] = ['cn', 'hk', 'us', 'jp', 'kr'];

export function serializeMarketReviewRegions(regions: readonly MarketReviewRegion[]): string {
  const ordered = MARKET_REVIEW_REGION_ORDER.filter((region) => regions.includes(region));
  return ordered.length === MARKET_REVIEW_REGION_ORDER.length ? 'both' : ordered.join(',');
}
