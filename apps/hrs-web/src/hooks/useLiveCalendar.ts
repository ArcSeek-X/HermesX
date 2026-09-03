/**
 * 消息日历 Hook。
 *
 * 提供三个 Hook：
 * - `useLiveCalendarTabs`：拉分类 Tab 列表（后端驱动）
 * - `useLiveCalendarCountries`：拉国家字典（后端驱动，含降级标记）
 * - `useLiveCalendarMonth`：月度事件的拉取、按天归格与客户端过滤
 *
 * 设计要点（与 useLiveNews 保持一致的约定）：
 * 1. 日历为低频数据，**不轮询**，仅提供手动 refresh；
 * 2. 月份 / includeEconomicData 变化才重新请求，用 AbortController 中止在途请求避免竞态；
 * 3. tab / countryId / importanceMin 变化**不重新请求**（整月数据已在内存），客户端过滤；
 * 4. 按天归格用**本地时区**，避免 toISOString() 的 UTC 错位。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  getLiveCalendarCountries,
  getLiveCalendarMonth,
  getLiveCalendarTabs,
  refreshLiveCalendar,
} from '../api/liveCalendar';
import type {
  CalendarCountryDef,
  CalendarTabDef,
  LiveCalendarEventDef,
} from '../types/liveCalendar';

/** 把秒级时间戳格式化为 `YYYY-MM-DD`（本地时区） */
function toDateKey(startAt: number): string {
  const date = new Date(startAt * 1000);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Tab 列表 Hook */
export function useLiveCalendarTabs(): {
  tabs: CalendarTabDef[];
  loading: boolean;
  error: string | null;
} {
  const [tabs, setTabs] = useState<CalendarTabDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const result = await getLiveCalendarTabs();
        if (!active) return;
        setTabs(result.tabs);
        setError(null);
      } catch {
        if (active) setError('分类加载失败');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  return { tabs, loading, error };
}

/** 国家字典 Hook */
export function useLiveCalendarCountries(): {
  items: CalendarCountryDef[];
  degraded: boolean;
  loading: boolean;
  error: string | null;
} {
  const [items, setItems] = useState<CalendarCountryDef[]>([]);
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const result = await getLiveCalendarCountries();
        if (!active) return;
        setItems(result.items);
        setDegraded(result.degraded);
        setError(null);
      } catch {
        if (active) setError('国家字典加载失败');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  return { items, degraded, loading, error };
}

/** 月度日历 Hook 的过滤选项 */
export interface UseLiveCalendarOptions {
  tab?: CalendarTabDef['value'];
  countryId?: string;
  importanceMin?: number;
  includeEconomicData?: boolean;
}

/** 月度日历 Hook 的返回值 */
export interface UseLiveCalendarReturn {
  /** 当前过滤条件下的平铺事件 */
  events: LiveCalendarEventDef[];
  /** 按 `YYYY-MM-DD`（本地时区）归格，日历网格直接消费 */
  eventsByDay: Map<string, LiveCalendarEventDef[]>;
  loading: boolean;
  isRefreshing: boolean;
  error: string | null;
  degraded: boolean;
  total: number;
  refresh: () => Promise<void>;
}

/**
 * 月度日历 Hook：按月拉取 + 按天归格 + 客户端过滤。
 *
 * @param year 年（UTC 口径）
 * @param month 月（1~12）
 * @param options 过滤选项；其中 `includeEconomicData` 变化会重新请求，其余为客户端过滤
 */
export function useLiveCalendarMonth(
  year: number,
  month: number,
  options: UseLiveCalendarOptions = {}
): UseLiveCalendarReturn {
  const { tab, countryId, importanceMin, includeEconomicData = false } = options;

  const [items, setItems] = useState<LiveCalendarEventDef[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [total, setTotal] = useState(0);
  const [manualRefreshing, setManualRefreshing] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const fetchMonth = useCallback(
    async (mode: 'replace' | 'refresh') => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const result = await getLiveCalendarMonth(
          { year, month, includeEconomicData },
          controller.signal
        );
        if (controller.signal.aborted) return;
        setItems(result.items);
        setTotal(result.total);
        setDegraded(result.degraded);
        setError(null);
      } catch {
        if (controller.signal.aborted) return;
        setError(mode === 'refresh' ? '刷新失败' : '日历加载失败');
        setItems((prev) => prev ?? []);
      }
    },
    [year, month, includeEconomicData]
  );

  // 月份 / includeEconomicData 变化时重新拉取（0ms 定时器推出 effect 同步路径）
  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(() => {
      if (!cancelled) void fetchMonth('replace');
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
      abortRef.current?.abort();
    };
  }, [fetchMonth]);

  /** 手动刷新：先触发服务端抓取，再重拉列表 */
  const refresh = useCallback(async () => {
    setManualRefreshing(true);
    try {
      await refreshLiveCalendar({ year, month });
    } catch {
      // 抓取失败不阻断，仍重试一次列表拉取，给用户最新库存数据
    }
    try {
      await fetchMonth('refresh');
    } finally {
      setManualRefreshing(false);
    }
  }, [year, month, fetchMonth]);

  // 客户端过滤：tab / countryId / importanceMin 变化不重新请求，在内存中过滤
  const events = useMemo(() => {
    let result = items ?? [];
    if (tab && tab !== 'all') {
      result = result.filter((event) => event.tabKeys.includes(tab));
    }
    if (countryId) {
      result = result.filter((event) => event.countryId === countryId);
    }
    if (importanceMin !== undefined) {
      result = result.filter((event) => event.importance >= importanceMin);
    }
    return result;
  }, [items, tab, countryId, importanceMin]);

  // 按天归格（本地时区）
  const eventsByDay = useMemo(() => {
    const map = new Map<string, LiveCalendarEventDef[]>();
    for (const event of events) {
      const key = toDateKey(event.startAt);
      const existing = map.get(key);
      if (existing) {
        existing.push(event);
      } else {
        map.set(key, [event]);
      }
    }
    // 同格内按重要级降序、时间升序，保证重要事件优先露出
    for (const list of map.values()) {
      list.sort((a, b) => b.importance - a.importance || a.startAt - b.startAt);
    }
    return map;
  }, [events]);

  const loading = items === null && !error;

  return {
    events,
    eventsByDay,
    loading,
    isRefreshing: manualRefreshing,
    error,
    degraded,
    total,
    refresh,
  };
}
