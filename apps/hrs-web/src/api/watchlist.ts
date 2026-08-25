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
  groupCode: string;
  description: string;
  sortOrder: number;
  itemCount: number;
  createDateTime: string;
  updateDateTime: string;
}

/** 自选股条目（不含实时行情） */
export interface WatchlistItem {
  id: number;
  groupId: number;
  stockCode: string;
  stockName: string | null;
  description: string | null;
  sortOrder: number;
  createDateTime: string;
  updateDateTime: string;
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

/** 列出所有分类（含每个分类的个股数量 itemCount） */
export async function getWatchlistGroups(): Promise<WatchlistGroup[]> {
  const { data } = await apiClient.get<Record<string, unknown>[]>(`${BASE}/get_group_list`);
  return toCamelCase<WatchlistGroup[]>(data);
}

/** 新增分类 */
export async function createWatchlistGroup(
  name: string,
  description?: string,
  sortOrder?: number,
): Promise<WatchlistGroup> {
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/create_group`, {
    name,
    description,
    sortOrder,
  });
  return toCamelCase<WatchlistGroup>(data);
}

/** 编辑分类（按 groupCode 定位） */
export async function updateWatchlistGroup(params: {
  groupCode: string;
  name?: string;
  description?: string;
  sortOrder?: number;
}): Promise<WatchlistGroup> {
  // 请求体使用 snake_case，与后端 schema 字段对齐（项目约定）
  const body: Record<string, unknown> = { group_code: params.groupCode };
  if (params.name !== undefined) body.name = params.name;
  if (params.description !== undefined) body.description = params.description;
  if (params.sortOrder !== undefined) body.sort_order = params.sortOrder;
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/update_group`, body);
  return toCamelCase<WatchlistGroup>(data);
}

/** 删除分类（按 groupCode 定位，级联删除其下股票） */
export async function deleteWatchlistGroup(groupCode: string): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete<Record<string, unknown>>(`${BASE}/delete_group/${groupCode}`);
  return toCamelCase<{ success: boolean }>(data);
}

/** 分页查询某分类下的自选股 */
export async function getWatchlistItems(
  groupId: number,
  pageNum: number,
  pageSize: number,
): Promise<WatchlistItemsPaginatedResponse> {
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/get_items_list`, {
    group_id: groupId,
    pageNum,
    pageSize,
  });
  return toCamelCase<WatchlistItemsPaginatedResponse>(data);
}

/** 新增自选股到分类 */
export async function createWatchlistItem(
  groupId: number,
  payload: { stockCode: string; stockName?: string; description?: string },
): Promise<WatchlistItem> {
  // 请求体使用 snake_case，与后端 WatchlistItemCreate schema 字段对齐（项目约定）
  const body: Record<string, unknown> = {
    stock_code: payload.stockCode,
  };
  if (payload.stockName !== undefined) body.stock_name = payload.stockName;
  if (payload.description !== undefined) body.description = payload.description;
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/create_item/${groupId}`, body);
  return toCamelCase<WatchlistItem>(data);
}

/** 编辑自选股（备注/名称） */
export async function updateWatchlistItem(
  id: number,
  payload: { description?: string; stockName?: string },
): Promise<WatchlistItem> {
  // 请求体使用 snake_case，与后端 WatchlistItemUpdate schema 字段对齐（项目约定）
  const body: Record<string, unknown> = {};
  if (payload.description !== undefined) body.description = payload.description;
  if (payload.stockName !== undefined) body.stock_name = payload.stockName;
  const { data } = await apiClient.post<Record<string, unknown>>(`${BASE}/update_item/${id}`, body);
  return toCamelCase<WatchlistItem>(data);
}

/** 删除自选股 */
export async function deleteWatchlistItem(id: number): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete<Record<string, unknown>>(`${BASE}/delete_item/${id}`);
  return toCamelCase<{ success: boolean }>(data);
}

/** 移动自选股到其他分类 */
export async function moveWatchlistItem(id: number, targetGroupId: number): Promise<WatchlistItem> {
  const { data } = await apiClient.put<Record<string, unknown>>(`${BASE}/move_item/${id}`, {
    target_group_id: targetGroupId,
  });
  return toCamelCase<WatchlistItem>(data);
}
