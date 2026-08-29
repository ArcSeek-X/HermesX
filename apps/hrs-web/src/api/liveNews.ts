/**
 * 实时财经快讯（Live News）API。
 *
 * 对应后端 `/api/v1/intelligence/live-news/*`（见 docs/live-news.md）：
 * - GET  /live-news/channels  频道列表（前端 Tab 数据源）
 * - GET  /live-news           快讯列表（频道/重要级/关键词/日期过滤 + 游标分页）
 * - POST /live-news/refresh   手动触发抓取
 * - GET  /live-news/{id}      单条详情
 *
 * 说明：
 * 1. 这些接口的缓存 TTL 在 `constants/cacheConfig.ts` 中显式设为 0，
 *    否则会命中 60 秒的默认缓存，导致前端 30 秒轮询拿不到新数据。
 * 2. 后端返回的降级标记 `degraded` 原样透出，由页面决定是否隐藏重要级筛选。
 */

import apiClient from './index';
import type {
  LiveNewsChannelsResponse,
  LiveNewsQueryParams,
  LiveNewsRefreshResponse,
  LiveNewsResponse,
} from '../types/liveNews';

const BASE = '/api/v1/intelligence/live-news';

/** 后端返回的原始快讯条目（snake_case） */
interface RawLiveNewsItem {
  id: number;
  title?: string;
  content?: string;
  display_time?: number | null;
  score?: number;
  important?: boolean;
  channels?: string[];
  uri?: string;
  author?: string | null;
}

/** 后端返回的原始列表响应（snake_case） */
interface RawLiveNewsResponse {
  items?: RawLiveNewsItem[];
  next_cursor?: string | null;
  degraded?: boolean;
  server_time?: number;
  total?: number;
}

/** 后端返回的原始频道列表响应 */
interface RawLiveNewsChannelsResponse {
  channels?: Array<{ value: string; label: string }>;
  degraded?: boolean;
  source?: string;
}

/** 后端返回的原始刷新响应 */
interface RawLiveNewsRefreshResponse {
  fetched_count?: number;
  degraded?: boolean;
  errors?: Array<{ channel: string; error: string }>;
}

/** snake_case -> camelCase 归一化，避免后端字段风格泄漏到业务层 */
function normalizeItem(raw: RawLiveNewsItem) {
  return {
    id: raw.id,
    title: raw.title ?? '',
    content: raw.content ?? '',
    displayTime: raw.display_time ?? null,
    score: raw.score ?? 1,
    important: Boolean(raw.important),
    channels: raw.channels ?? [],
    uri: raw.uri ?? '',
    author: raw.author ?? null,
  };
}

/**
 * 查询快讯频道列表。
 *
 * 正常返回 8 个频道；官方源不可用降级时只返回「要闻」且 degraded=true，
 * 页面据此只渲染单个 Tab 并隐藏重要级筛选。
 */
export async function getLiveNewsChannels(): Promise<LiveNewsChannelsResponse> {
  const response = await apiClient.get<RawLiveNewsChannelsResponse>(`${BASE}/channels`);
  const data = response.data ?? {};
  return {
    channels: data.channels ?? [],
    degraded: Boolean(data.degraded),
    source: data.source ?? 'wallstreetcn',
  };
}

/**
 * 查询快讯列表。
 *
 * @param params 查询条件；channel 必填，其余可选。空值参数不会发给后端。
 * @param signal 可选的取消信号。快讯页会频繁切换频道/条件并发起轮询，
 *   传入 signal 才能真正中止在途请求，避免旧请求的响应覆盖新数据。
 */
export async function getLiveNews(
  params: LiveNewsQueryParams,
  signal?: AbortSignal
): Promise<LiveNewsResponse> {
  const query: Record<string, string | number | boolean> = { channel: params.channel };
  if (params.importantOnly !== undefined) query.important_only = params.importantOnly;
  if (params.keyword) query.keyword = params.keyword;
  if (params.date) query.date = params.date;
  if (params.dateFrom) query.date_from = params.dateFrom;
  if (params.dateTo) query.date_to = params.dateTo;
  if (params.cursor) query.cursor = params.cursor;
  if (params.limit !== undefined) query.limit = params.limit;

  const response = await apiClient.get<RawLiveNewsResponse>(BASE, { params: query, signal });
  const data = response.data ?? {};
  return {
    items: (data.items ?? []).map(normalizeItem),
    nextCursor: data.next_cursor ?? null,
    degraded: Boolean(data.degraded),
    serverTime: data.server_time ?? Math.floor(Date.now() / 1000),
    total: data.total ?? 0,
  };
}

/**
 * 手动触发快讯抓取。
 *
 * @param channels 指定刷新的频道 ID 列表；为空表示刷新全部频道。
 */
export async function refreshLiveNews(channels?: string[]): Promise<LiveNewsRefreshResponse> {
  const response = await apiClient.post<RawLiveNewsRefreshResponse>(`${BASE}/refresh`, {
    channels: channels ?? null,
  });
  const data = response.data ?? {};
  return {
    fetchedCount: data.fetched_count ?? 0,
    degraded: Boolean(data.degraded),
    errors: data.errors ?? [],
  };
}

/** 查询单条快讯详情 */
export async function getLiveNewsDetail(itemId: number) {
  const response = await apiClient.get<RawLiveNewsItem>(`${BASE}/${itemId}`);
  return normalizeItem(response.data);
}
