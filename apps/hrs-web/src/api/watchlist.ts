/**
 * 自选股管理（Watchlist）相关 API。
 * 覆盖分类（group）与自选股（item）的增删改查与移动归类。
 * 排序与搜索在前端完成，本模块仅封装结构化数据的 CRUD。
 *
 * 约定：后端返回 snake_case，前端统一用 toCamelCase 归一化；请求体发送 snake_case。
 */

import apiClient from './index';
import { toCamelCase } from './utils';

/** 分类 */
export interface WatchlistGroup {
  id: number;
  name: string;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

/** 自选股条目（不含实时行情） */
export interface WatchlistItem {
  id: number;
  groupId: number;
  stockCode: string;
  stockName: string | null;
  note: string | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

/** 实时行情（前端合并到条目上展示，字段对齐后端 StockQuote） */
export interface WatchlistQuote {
  currentPrice: number | null;
  changePercent: number | null;
  amount: number | null;
  turnoverRate: number | null;
  totalMv: number | null;
}

export type WatchlistItemWithQuote = WatchlistItem & {
  quote?: WatchlistQuote;
};

/** 分页查询响应 */
export interface WatchlistItemsPaginatedResponse {
  list: WatchlistItem[];
  total: number;
  pageSize: number;
  pages: number;
  pageNum: number;
}

const BASE = '/api/v1/watchlist';

/** 列出所有分类 */
export async function fetchGroups(): Promise<WatchlistGroup[]> {
  const { data } = await apiClient.get<Record<string, unknown>[]>(`${BASE}/groups`);
  return toCamelCase<WatchlistGroup[]>(data);
}

/** 新增分类 */
export async function createGroup(name: string): Promise<WatchlistGroup> {
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/groups`, { name });
  return toCamelCase<WatchlistGroup>(data);
}

/** 编辑分类 */
export async function updateGroup(
  id: number,
  payload: { name?: string; sortOrder?: number },
): Promise<WatchlistGroup> {
  // 请求体使用 snake_case，与后端 schema 字段对齐（项目约定）
  const body: Record<string, unknown> = {};
  if (payload.name !== undefined) body.name = payload.name;
  if (payload.sortOrder !== undefined) body.sort_order = payload.sortOrder;
  const { data } = await apiClient.put<Record<string, unknown>>(`${BASE}/groups/${id}`, body);
  return toCamelCase<WatchlistGroup>(data);
}

/** 删除分类（级联删除其下股票） */
export async function deleteGroup(id: number): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete<Record<string, unknown>>(`${BASE}/groups/${id}`);
  return toCamelCase<{ success: boolean }>(data);
}

/** 分页查询某分类下的自选股 */
export async function fetchItemsPaginated(
  groupId: number,
  pageNum: number,
  pageSize: number,
): Promise<WatchlistItemsPaginatedResponse> {
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/items/query`, {
    group_id: groupId,
    pageNum,
    pageSize,
  });
  return toCamelCase<WatchlistItemsPaginatedResponse>(data);
}

/** 新增自选股到分类 */
export async function createItem(
  groupId: number,
  payload: { stockCode: string; stockName?: string; note?: string },
): Promise<WatchlistItem> {
  // 请求体使用 snake_case，与后端 WatchlistItemCreate schema 字段对齐（项目约定）
  const body: Record<string, unknown> = {
    stock_code: payload.stockCode,
  };
  if (payload.stockName !== undefined) body.stock_name = payload.stockName;
  if (payload.note !== undefined) body.note = payload.note;
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/groups/${groupId}/items`, body);
  return toCamelCase<WatchlistItem>(data);
}

/** 编辑自选股（备注/名称） */
export async function updateItem(
  id: number,
  payload: { note?: string; stockName?: string },
): Promise<WatchlistItem> {
  // 请求体使用 snake_case，与后端 WatchlistItemUpdate schema 字段对齐（项目约定）
  const body: Record<string, unknown> = {};
  if (payload.note !== undefined) body.note = payload.note;
  if (payload.stockName !== undefined) body.stock_name = payload.stockName;
  const { data } = await apiClient.put<Record<string, unknown>>(`${BASE}/items/${id}`, body);
  return toCamelCase<WatchlistItem>(data);
}

/** 删除自选股 */
export async function deleteItem(id: number): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete<Record<string, unknown>>(`${BASE}/items/${id}`);
  return toCamelCase<{ success: boolean }>(data);
}

/** 移动自选股到其他分类 */
export async function moveItem(id: number, targetGroupId: number): Promise<WatchlistItem> {
  const { data } = await apiClient.put<Record<string, unknown>>(`${BASE}/items/${id}/move`, {
    target_group_id: targetGroupId,
  });
  return toCamelCase<WatchlistItem>(data);
}
