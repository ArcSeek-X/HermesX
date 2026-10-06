/**
 * @file useLiveCalendar.ts
 * @description 消息日历页面的数据 Hook：提供 Tab、国家字典和按月缓存的事件查询能力，
 * 供 `LiveCalendarPage` 组合月 / 周 / 日 / List 四视图数据。
 * @author Lensgcx (GaoCangxiong)
 *
 * 提供三个 Hook：
 * - `useLiveCalendarTabs`：拉分类 Tab 列表（后端驱动）
 * - `useLiveCalendarCountries`：拉国家字典（后端驱动，含降级标记）
 * - `useLiveCalendarMonths`：按月缓存、补缺拉取、合并、按天归格与客户端过滤
 *
 * 设计要点：
 * 1. 日历为低频数据，**不轮询**，仅提供手动 refresh；
 * 2. 覆盖月份集合 / includeEconomicData 变化才重新请求；同月请求走缓存 + in-flight 去重；
 * 3. tab / countryId / importanceMin / keyword 等筛选**不重新请求**，统一走客户端过滤；
 * 4. 按天归格用**本地时区**，避免 toISOString() 的 UTC 错位；
 * 5. 后端按月取数，前端按覆盖月份合并，并在命中缓存后后台预取相邻月份，优化翻月体验。
 */

import { toDateKeyFromSeconds } from '@utils/format';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveCalendarRange } from '@components';
import { ALL_IMPORTANCE_LEVELS, type ImportanceLevel } from '../constants/newsImportance';
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

/** 月份对象（1~12） */
export interface MonthCursor {
  year: number;
  month: number;
}

interface CachedLiveCalendarMonthResult {
  /** 该月原始事件数组，供客户端筛选复用 */
  items: LiveCalendarEventDef[];
  /** 该月预先归格后的结果，供无筛选路径直接复用 */
  eventsByDay: Map<string, LiveCalendarEventDef[]>;
  total: number;
  serverTime: number;
  degraded: boolean;
  source: string;
}

function monthKeyOf(month: MonthCursor): string {
  return `${month.year}-${month.month}`;
}

function cacheKeyOfMonth(month: MonthCursor, includeEconomicData: boolean): string {
  return `${monthKeyOf(month)}-${includeEconomicData ? 'fd' : 'no-fd'}`;
}

function monthsKeyOf(months: MonthCursor[]): string {
  return months.map(monthKeyOf).join('|');
}

function shiftMonth(month: MonthCursor, delta: number): MonthCursor {
  const next = new Date(month.year, month.month - 1 + delta, 1);
  return { year: next.getFullYear(), month: next.getMonth() + 1 };
}

function adjacentMonthsOf(months: MonthCursor[]): MonthCursor[] {
  if (months.length === 0) return [];
  const first = months[0];
  const last = months[months.length - 1];
  const seen = new Set(months.map(monthKeyOf));
  return [shiftMonth(first, -1), shiftMonth(last, 1)].filter((month) => {
    const key = monthKeyOf(month);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function buildEventsByDay(items: LiveCalendarEventDef[]): Map<string, LiveCalendarEventDef[]> {
  const map = new Map<string, LiveCalendarEventDef[]>();
  for (const event of items) {
    const key = toDateKeyFromSeconds(event.startAt);
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

/** Tab 列表 Hook */
export function useLiveCalendarTabs(): {
  /** 分类 Tab 列表（后端驱动；'all' 全部分类入口由 Page 层拼接） */
  tabs: CalendarTabDef[];
  /** 首次加载中（数据未就绪） */
  loading: boolean;
  /** 加载失败信息；null 表示成功 */
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
  /** 国家字典列表：国旗、名称、货币(ISO 代码)等，供事件卡片 / 详情抽屉展示国家信息 */
  items: CalendarCountryDef[];
  /** 降级标记：后端部分字段缺失时置 true，UI 可据此弱化展示（如缺货币 / 国旗时降级为仅名称） */
  degraded: boolean;
  /** 首次加载中（数据未就绪） */
  loading: boolean;
  /** 加载失败信息；null 表示成功 */
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
  /** 重要度多选（客户端过滤）；长度等于 `ALL_IMPORTANCE_LEVELS` 时视为不过滤 */
  importance?: ImportanceLevel[];
  /** 事件类型：`FE` 大事件 / `FD` 经济数据；不传 = 全部。客户端过滤，不重新请求 */
  calendarType?: 'FE' | 'FD';
  /** 标题关键词（客户端过滤，匹配 title / shortTitle，忽略大小写） */
  keyword?: string;
}

/** 月度日历 Hook 的返回值 */
export interface UseLiveCalendarReturn {
  /** 当前过滤条件下的平铺事件 */
  events: LiveCalendarEventDef[];
  /** 按 `YYYY-MM-DD`（本地时区）归格，日历网格直接消费 */
  eventsByDay: Map<string, LiveCalendarEventDef[]>;
  /** 当前已应用到页面的数据所覆盖的月份集合 key */
  resolvedMonthsKey: string;
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
  const {
    tab,
    countryId,
    importanceMin,
    includeEconomicData = true,
    importance,
    calendarType,
    keyword,
  } = options;

  /** `null` 表示首屏尚未拿到可显示数据；失败时保留上一帧避免空屏闪烁。 */
  const [visibleResults, setVisibleResults] = useState<CachedLiveCalendarMonthResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  /** 覆盖月份范围内的事件总数，各月 total 累加，不受客户端过滤影响。 */
  const [total, setTotal] = useState(0);
  /** 手动刷新期间驱动按钮 loading 态。 */
  const [manualRefreshing, setManualRefreshing] = useState(false);
  const [resolvedMonthsKey, setResolvedMonthsKey] = useState('');
  /** 按月缓存接口结果，避免翻月时重复请求。 */
  const cacheRef = useRef(new Map<string, CachedLiveCalendarMonthResult>());
  /** 同月在途请求复用同一个 Promise，避免并发重复打点。 */
  const inflightRef = useRef(new Map<string, Promise<CachedLiveCalendarMonthResult>>());
  /** 仅让最后一次请求结果生效，避免乱序回写。 */
  const requestSeqRef = useRef(0);

  const loadMonth = useCallback(
    async (
      month: MonthCursor,
      force = false
    ): Promise<CachedLiveCalendarMonthResult> => {
      const cacheKey = cacheKeyOfMonth(month, includeEconomicData);
      if (!force) {
        const cached = cacheRef.current.get(cacheKey);
        if (cached) return cached;
        const inflight = inflightRef.current.get(cacheKey);
        if (inflight) return inflight;
      }

      const request = getLiveCalendarMonth({
        year: month.year,
        month: month.month,
        includeEconomicData,
      }).then((result) => {
        const cachedResult: CachedLiveCalendarMonthResult = {
          ...result,
          eventsByDay: buildEventsByDay(result.items),
        };
        cacheRef.current.set(cacheKey, cachedResult);
        return cachedResult;
      });

      inflightRef.current.set(cacheKey, request);
      try {
        return await request;
      } finally {
        inflightRef.current.delete(cacheKey);
      }
    },
    [includeEconomicData]
  );

  const getCachedVisibleResults = useCallback(
    (targetMonths: MonthCursor[]) => {
      return targetMonths
        .map((month) => cacheRef.current.get(cacheKeyOfMonth(month, includeEconomicData)))
        .filter((result): result is CachedLiveCalendarMonthResult => Boolean(result));
    },
    [includeEconomicData]
  );

  const applyVisibleMonthsFromCache = useCallback(
    (targetMonths: MonthCursor[]) => {
      const cachedResults = getCachedVisibleResults(targetMonths);
      if (cachedResults.length === 0) return false;

      setVisibleResults(cachedResults);
      setTotal(cachedResults.reduce((sum, result) => sum + result.total, 0));
      setDegraded(cachedResults.some((result) => result.degraded));
      setResolvedMonthsKey(monthsKeyOf(targetMonths));
      return true;
    },
    [getCachedVisibleResults]
  );

  const prefetchAdjacentMonths = useCallback(
    (targetMonths: MonthCursor[]) => {
      adjacentMonthsOf(targetMonths).forEach((month) => {
        const cacheKey = cacheKeyOfMonth(month, includeEconomicData);
        if (cacheRef.current.has(cacheKey) || inflightRef.current.has(cacheKey)) return;
        void loadMonth(month).catch(() => undefined);
      });
    },
    [includeEconomicData, loadMonth]
  );

  const fetchMonths = useCallback(
    async (mode: 'replace' | 'refresh') => {
      const currentRequest = ++requestSeqRef.current;
      const hasVisibleCache = applyVisibleMonthsFromCache(months);
      const monthsToLoad =
        mode === 'refresh'
          ? months
          : months.filter(
              (month) => !cacheRef.current.has(cacheKeyOfMonth(month, includeEconomicData))
            );

      if (monthsToLoad.length === 0) {
        if (hasVisibleCache) {
          setError(null);
          prefetchAdjacentMonths(months);
        } else {
          setVisibleResults((prev) => prev ?? []);
          setResolvedMonthsKey('');
        }
        return;
      }

      const results = await Promise.allSettled(
        monthsToLoad.map((month) => loadMonth(month, mode === 'refresh'))
      );
      if (currentRequest !== requestSeqRef.current) return;

      const hasVisibleMonths = applyVisibleMonthsFromCache(months);
      if (hasVisibleMonths) {
        setError(null);
        prefetchAdjacentMonths(months);
        return;
      }

      if (results.every((result) => result.status === 'rejected')) {
        setError(mode === 'refresh' ? '刷新失败' : '日历加载失败');
        setVisibleResults((prev) => prev ?? []);
        setResolvedMonthsKey('');
      }
    },
    [applyVisibleMonthsFromCache, includeEconomicData, loadMonth, months, prefetchAdjacentMonths]
  );

  /** 覆盖月份 / includeEconomicData 变化时重新拉取；命中缓存时直接复用，仅补缺月。 */
  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(() => {
      if (!cancelled) void fetchMonths('replace');
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
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

  /** 预构造 O(1) 判定结构，避免逐条事件里重复创建 Set / 归一化字符串。 */
  const keywordMatcher = useMemo(() => (keyword ?? '').trim().toLowerCase(), [keyword]);
  const importanceSet = useMemo(
    () =>
      importance && importance.length > 0 && importance.length < ALL_IMPORTANCE_LEVELS.length
        ? new Set<number>(importance)
        : null,
    [importance],
  );
  const hasClientFilters = Boolean(
    (tab && tab !== 'all') ||
    countryId ||
    importanceMin !== undefined ||
    importanceSet ||
    calendarType ||
    keywordMatcher,
  );

  const items = useMemo(
    () => visibleResults?.flatMap((result) => result.items) ?? [],
    [visibleResults],
  );

  /** 客户端过滤：变化不重新请求，直接在已加载事件上做内存筛选。 */
  const events = useMemo(() => {
    let result = items;
    if (tab && tab !== 'all') {
      result = result.filter((event) => event.tabKeys.includes(tab));
    }
    if (countryId) {
      result = result.filter((event) => event.countryId === countryId);
    }
    if (importanceMin !== undefined) {
      result = result.filter((event) => event.importance >= importanceMin);
    }
    if (importanceSet) {
      result = result.filter((event) => importanceSet.has(event.importance));
    }
    if (calendarType) {
      result = result.filter((event) => event.calendarType === calendarType);
    }
    if (keywordMatcher) {
      result = result.filter(
        (event) =>
          event.title.toLowerCase().includes(keywordMatcher) ||
          event.shortTitle.toLowerCase().includes(keywordMatcher),
      );
    }
    return result;
  }, [items, tab, countryId, importanceMin, importanceSet, calendarType, keywordMatcher]);

  /** 按天归格（本地时区）；无筛选时直接复用缓存分桶结果，减少切月重算。 */
  const eventsByDay = useMemo(() => {
    if (!hasClientFilters) {
      const map = new Map<string, LiveCalendarEventDef[]>();
      for (const result of visibleResults ?? []) {
        for (const [dayKey, list] of result.eventsByDay) {
          const existing = map.get(dayKey);
          if (existing) {
            existing.push(...list);
          } else {
            map.set(dayKey, list.slice());
          }
        }
      }
      for (const list of map.values()) {
        if (list.length > 1) {
          list.sort((a, b) => b.importance - a.importance || a.startAt - b.startAt);
        }
      }
      return map;
    }
    return buildEventsByDay(events);
  }, [events, hasClientFilters, visibleResults]);

  /** 首屏加载态：尚无可显示数据且当前没有错误。 */
  const loading = visibleResults === null && !error;

  return {
    /** 当前过滤条件（tab / countryId / importanceMin）下的平铺事件数组 */
    events,
    /** 按本地时区 `YYYY-MM-DD` 归格的事件映射，日历网格直接消费 */
    eventsByDay,
    /** 当前已应用到页面的数据所覆盖的月份集合 key */
    resolvedMonthsKey,
    /** 首屏加载中（items 为 null 且无 error） */
    loading,
    /** 是否正在手动刷新（refresh 调用期间为 true） */
    isRefreshing: manualRefreshing,
    /** 加载失败信息；null 表示成功 */
    error,
    /** 降级标记：任意覆盖月份后端降级时置 true，UI 据此弱化展示 */
    degraded,
    /** 覆盖月份范围内的事件总数（各月 total 累加，不受客户端过滤影响） */
    total,
    /** 手动刷新：触发服务端逐月抓取后再重拉当前可见范围 */
    refresh,
  };
}
