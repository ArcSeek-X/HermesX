/**
 * 消息日历 Hook。
 *
 * 提供三个 Hook：
 * - `useLiveCalendarTabs`：拉分类 Tab 列表（后端驱动）
 * - `useLiveCalendarCountries`：拉国家字典（后端驱动，含降级标记）
 * - `useLiveCalendarMonths`：可见范围覆盖的所有月份并行拉取、合并、按天归格与客户端过滤
 *
 * 设计要点（与 useLiveNews 保持一致的约定）：
 * 1. 日历为低频数据，**不轮询**，仅提供手动 refresh；
 * 2. 覆盖月份集合 / includeEconomicData 变化才重新请求，用 AbortController 中止在途请求避免竞态；
 * 3. tab / countryId / importanceMin 变化**不重新请求**（已加载数据在内存），客户端过滤；
 * 4. 按天归格用**本地时区**，避免 toISOString() 的 UTC 错位；
 * 5. 后端按月取数，视图可见范围（月视图含上/下月填充格、跨月周次）可能覆盖多个月，
 *    故按月并行拉取后合并，避免跨月日（如 9 月第一周中的 9/2、9/3）无数据。
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
import type { LiveCalendarRange } from '../components/common/LiveCalendar';

/** 月份对象（1~12） */
export interface MonthCursor {
  year: number;
  month: number;
}

/**
 * 推导日期闭区间覆盖的所有月份（去重、升序）。
 *
 * 为兼容任意时区，两端各外扩 1 天：事件 `start_at` 为秒级 UTC，按本地时区归格后，
 * 某可见日的部分时段可能落在 UTC 前一日（如 UTC+8 下本地 9/1 00:00~08:00 = 8/31 16:00~24:00 UTC）；
 * 只按可见范围本身的年月拉取会漏掉这些事件。
 */
export function monthsInRange(range: LiveCalendarRange): MonthCursor[] {
  const months: MonthCursor[] = [];
  // 两端各外扩 1 天，兼容任意时区下本地可见日与 UTC 日期的偏移
  const start = new Date(range.start);
  start.setDate(start.getDate() - 1);
  const end = new Date(range.end);
  end.setDate(end.getDate() + 1);

  const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
  const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);
  while (cursor <= endMonth) {
    months.push({ year: cursor.getFullYear(), month: cursor.getMonth() + 1 });
    cursor.setMonth(cursor.getMonth() + 1);
  }
  return months;
}

/** 计算某月月视图的可见日期范围（周一起始，含上/下月填充格），供 Page 初始化首屏范围 */
export function monthGridRange(year: number, month: number): LiveCalendarRange {
  const first = new Date(year, month - 1, 1);
  const last = new Date(year, month, 0);
  const start = new Date(first);
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
  const end = new Date(last);
  end.setDate(last.getDate() + (6 - ((last.getDay() + 6) % 7)));
  return { start, end };
}

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
 * 多月日历 Hook：按可见范围覆盖的月份并行拉取 + 合并 + 按天归格 + 客户端过滤。
 *
 * @param months 可见范围覆盖的月份（升序去重；来自 `monthsInRange`）
 * @param options 过滤选项；其中 `includeEconomicData` 变化会重新请求，其余为客户端过滤
 */
export function useLiveCalendarMonths(
  months: MonthCursor[],
  options: UseLiveCalendarOptions = {}
): UseLiveCalendarReturn {
  const { tab, countryId, importanceMin, includeEconomicData = false } = options;

  const [items, setItems] = useState<LiveCalendarEventDef[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [total, setTotal] = useState(0);
  const [manualRefreshing, setManualRefreshing] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const fetchMonths = useCallback(
    async (mode: 'replace' | 'refresh') => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const results = await Promise.all(
          months.map((m) =>
            getLiveCalendarMonth(
              { year: m.year, month: m.month, includeEconomicData },
              controller.signal
            )
          )
        );
        if (controller.signal.aborted) return;
        // 各月窗口互斥，直接按月份顺序拼接即可保持时间升序
        const merged = results.flatMap((result) => result.items);
        setItems(merged);
        setTotal(results.reduce((sum, result) => sum + result.total, 0));
        setDegraded(results.some((result) => result.degraded));
        setError(null);
      } catch {
        if (controller.signal.aborted) return;
        setError(mode === 'refresh' ? '刷新失败' : '日历加载失败');
        setItems((prev) => prev ?? []);
      }
    },
    [months, includeEconomicData]
  );

  // 覆盖月份 / includeEconomicData 变化时重新拉取（0ms 定时器推出 effect 同步路径）
  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(() => {
      if (!cancelled) void fetchMonths('replace');
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
      abortRef.current?.abort();
    };
  }, [fetchMonths]);

  /** 手动刷新：先触发覆盖月份的服务端抓取（逐月，单月失败不阻断），再重拉列表 */
  const refresh = useCallback(async () => {
    setManualRefreshing(true);
    await Promise.all(
      months.map((m) =>
        refreshLiveCalendar({ year: m.year, month: m.month }).catch(() => undefined)
      )
    );
    try {
      await fetchMonths('refresh');
    } finally {
      setManualRefreshing(false);
    }
  }, [months, fetchMonths]);

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
