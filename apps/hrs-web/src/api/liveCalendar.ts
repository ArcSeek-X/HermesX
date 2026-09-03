/**
 * 消息日历（Live Calendar）API。
 *
 * 对应后端 `/api/v1/intelligence/live-calendar/*`（见 docs/Live-calendar.md §7）：
 * - GET  /live-calendar/tabs      分类 Tab 列表
 * - GET  /live-calendar/countries 国家字典
 * - GET  /live-calendar           月度事件（分类/国家/重要级/经济数据过滤）
 * - POST /live-calendar/refresh   手动触发抓取
 *
 * 约定：后端返回 snake_case，本层统一 normalize 为 camelCase，
 * 避免后端字段风格泄漏到业务层（对齐 liveNews.ts）。
 */

import apiClient from './index';
import type {
  CalendarCountryDef,
  CalendarTabDef,
  LiveCalendarEventDef,
  LiveCalendarQueryDef,
} from '../types/liveCalendar';

const BASE = '/api/v1/intelligence/live-calendar';

/** 后端返回的原始 Tab（snake_case） */
interface RawCalendarTab {
  value: string;
  label: string;
  order?: number;
}

/** 后端返回的原始国家字典条目（snake_case） */
interface RawCalendarCountry {
  country_id: string;
  country_name: string;
  currency?: string;
  currency_name?: string;
  flag_uri?: string;
}

/** 后端返回的原始事件（snake_case） */
interface RawCalendarEvent {
  id: number;
  key: string;
  start_at: number;
  title?: string;
  short_title?: string;
  summary?: string;
  calendar_type?: string;
  tab_keys?: string[];
  importance?: number;
  country?: string;
  country_id?: string;
  flag_uri?: string;
  actual?: string;
  forecast?: string;
  previous?: string;
  is_all_day?: boolean;
  source_uri?: string;
}

function normalizeTab(raw: RawCalendarTab): CalendarTabDef {
  return {
    value: raw.value as CalendarTabDef['value'],
    label: raw.label,
    order: raw.order ?? 0,
  };
}

function normalizeCountry(raw: RawCalendarCountry): CalendarCountryDef {
  return {
    countryId: raw.country_id,
    countryName: raw.country_name,
    currency: raw.currency ?? '',
    currencyName: raw.currency_name ?? '',
    flagUri: raw.flag_uri ?? '',
  };
}

function normalizeEvent(raw: RawCalendarEvent): LiveCalendarEventDef {
  return {
    id: raw.id,
    key: raw.key,
    startAt: raw.start_at,
    title: raw.title ?? '',
    shortTitle: raw.short_title ?? raw.title ?? '',
    summary: raw.summary ?? '',
    calendarType: raw.calendar_type === 'FD' ? 'FD' : 'FE',
    tabKeys: (raw.tab_keys ?? []) as LiveCalendarEventDef['tabKeys'],
    importance: (raw.importance ?? 0) as LiveCalendarEventDef['importance'],
    country: raw.country ?? '',
    countryId: raw.country_id ?? '',
    flagUri: raw.flag_uri ?? '',
    actual: raw.actual ?? '',
    forecast: raw.forecast ?? '',
    previous: raw.previous ?? '',
    isAllDay: Boolean(raw.is_all_day),
    sourceUri: raw.source_uri ?? '',
  };
}

/** 查询日历分类 Tab 列表 */
export async function getLiveCalendarTabs(): Promise<{
  tabs: CalendarTabDef[];
  degraded: boolean;
}> {
  const response = await apiClient.get<{ tabs?: RawCalendarTab[]; degraded?: boolean }>(
    `${BASE}/tabs`
  );
  const data = response.data ?? {};
  return {
    tabs: (data.tabs ?? []).map(normalizeTab),
    degraded: Boolean(data.degraded),
  };
}

/** 查询国家字典 */
export async function getLiveCalendarCountries(): Promise<{
  items: CalendarCountryDef[];
  degraded: boolean;
}> {
  const response = await apiClient.get<{
    items?: RawCalendarCountry[];
    degraded?: boolean;
  }>(`${BASE}/countries`);
  const data = response.data ?? {};
  return {
    items: (data.items ?? []).map(normalizeCountry),
    degraded: Boolean(data.degraded),
  };
}

/** 查询月度日历事件 */
export async function getLiveCalendarMonth(
  params: LiveCalendarQueryDef,
  signal?: AbortSignal
): Promise<{
  items: LiveCalendarEventDef[];
  total: number;
  serverTime: number;
  degraded: boolean;
  source: string;
}> {
  const query: Record<string, string | number | boolean> = {
    year: params.year,
    month: params.month,
  };
  if (params.tab) query.tab = params.tab;
  if (params.countryId) query.country_id = params.countryId;
  if (params.importanceMin !== undefined) query.importance_min = params.importanceMin;
  if (params.includeEconomicData) query.include_economic_data = params.includeEconomicData;

  const response = await apiClient.get<{
    items?: RawCalendarEvent[];
    total?: number;
    server_time?: number;
    degraded?: boolean;
    source?: string;
  }>(BASE, { params: query, signal });
  const data = response.data ?? {};
  return {
    items: (data.items ?? []).map(normalizeEvent),
    total: data.total ?? 0,
    serverTime: data.server_time ?? Math.floor(Date.now() / 1000),
    degraded: Boolean(data.degraded),
    source: data.source ?? 'wallstreetcn',
  };
}

/** 手动触发指定月份日历抓取 */
export async function refreshLiveCalendar(params: {
  year: number;
  month: number;
}): Promise<{ fetchedCount: number; degraded: boolean; errors: string[] }> {
  const response = await apiClient.post<{
    fetched_count?: number;
    degraded?: boolean;
    errors?: string[];
  }>(`${BASE}/refresh`, { year: params.year, month: params.month });
  const data = response.data ?? {};
  return {
    fetchedCount: data.fetched_count ?? 0,
    degraded: Boolean(data.degraded),
    errors: data.errors ?? [],
  };
}
