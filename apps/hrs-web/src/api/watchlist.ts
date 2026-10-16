/**
 * 自选股管理（Watchlist）相关 API。
 * 覆盖分类（group）与自选股（item）的增删改查与移动归类。
 * 排序与搜索在前端完成，本模块仅封装结构化数据的 CRUD。
 *
 * 约定：后端返回 snake_case，前端统一用 toCamelCase 归一化；请求体发送 snake_case。
 */

import apiClient from './index';
import { toCamelCase } from './utils';
import type { KLinePoint } from './kline';

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
  /** 昨收价：分时缩略图的涨跌基准与昨收虚线（后端已返回，前端补齐映射） */
  prevClose: number | null;
}

/** 当日分时明细（KLinePoint 形态），供自选股列表分时缩略图列渲染 */
export interface WatchlistIntraday {
  /** 分时点（date 为 'YYYY-MM-DD HH:mm:ss'，由后端 trends2 通路标准化） */
  points: KLinePoint[];
  /** 昨收价：分时基准线；上游缺失时为 null，前端退化为首末点比较 */
  prevClose: number | null;
}

export type WatchlistItemWithQuote = WatchlistItem & {
  quote?: WatchlistQuote;
  /** 当日分时（懒加载）：未拉取 / 拉取失败 / 无数据时为 undefined，缩略图列显示占位 */
  intraday?: WatchlistIntraday;
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

/** 单页最大数量：与后端 schema（pageSize le=100）保持一致，分页拉取时据此翻页 */
const WATCHLIST_PAGE_SIZE = 100;
/** 单分类极端情况下的最大翻页次数，避免异常时无限请求 */
const WATCHLIST_MAX_PAGES = 50;

/**
 * 拉取某分类下的全部自选股（自动分页）。
 * 后端单页 pageSize 上限为 100，本函数以 WATCHLIST_PAGE_SIZE 翻页直到取尽，
 * 供「已自选」状态比对等需要全量代码的场景使用。
 */
export async function getAllWatchlistItems(groupId: number): Promise<WatchlistItem[]> {
  const all: WatchlistItem[] = [];
  let pageNum = 1;
  while (pageNum <= WATCHLIST_MAX_PAGES) {
    const page = await getWatchlistItems(groupId, pageNum, WATCHLIST_PAGE_SIZE);
    all.push(...page.list);
    if (page.list.length < WATCHLIST_PAGE_SIZE) break;
    pageNum += 1;
  }
  return all;
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
