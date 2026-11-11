/**
 * 个股最近搜索（Recent Search）相关 API。
 *
 * 使用场景：个股 K 线页搜索框下方的卡片列表——列表读取、记录一次搜索、一键清空。
 * 约定：后端返回 snake_case，前端统一用 toCamelCase 归一化；请求体发送 snake_case。
 */

import apiClient from './index';
import { toCamelCase } from './utils';

/** 一条最近搜索记录（不含实时行情，行情由 stocksApi.batchQuote 补齐） */
export interface RecentSearchItem {
  id: number;
  userId: string;
  stockCode: string;
  stockName: string | null;
  market: string | null;
  createDateTime: string | null;
  updateDateTime: string | null;
}

/** 记录一次搜索的入参；market 缺省时由后端按代码推断 */
export interface RecordRecentSearchPayload {
  stockCode: string;
  stockName?: string | null;
  market?: string | null;
}

/** 读取最近搜索列表（后端按最近搜索时间倒序，最多 10 条） */
export async function getRecentSearchList(): Promise<RecentSearchItem[]> {
  const { data } = await apiClient.get<{ items?: Record<string, unknown>[] }>(
    '/api/v1/recent-search/list',
  );
  return (data.items ?? []).map((item) => toCamelCase<RecentSearchItem>(item));
}

/** 记录 / 更新一条搜索；返回被写入的条目 */
export async function recordRecentSearch(payload: RecordRecentSearchPayload): Promise<RecentSearchItem> {
  const { data } = await apiClient.post<{ item: Record<string, unknown> }>(
    '/api/v1/recent-search/record',
    {
      stock_code: payload.stockCode,
      stock_name: payload.stockName ?? null,
      market: payload.market ?? null,
    },
  );
  return toCamelCase<RecentSearchItem>(data.item);
}

/** 一键清空当前用户全部最近搜索记录 */
export async function clearRecentSearch(): Promise<void> {
  await apiClient.delete('/api/v1/recent-search/clear');
}
