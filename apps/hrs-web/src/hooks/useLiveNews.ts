/**
 * 实时财经快讯 Hook。
 *
 * 提供两个 Hook：
 * - `useLiveNewsChannels`：拉频道列表，决定页面渲染几个 Tab（降级时只返回「要闻」）
 * - `useLiveNews`：快讯列表的分页、轮询、按天分组与空态判断
 *
 * 设计要点：
 * 1. Tab 完全由后端驱动，前端**不硬编码** 8 个频道，这样上游降级时 UI 能自动收敛；
 * 2. 轮询默认 30 秒，页面切到后台（`visibilitychange`）时暂停，避免无效请求；
 * 3. 关键词输入做 300ms 防抖，避免每敲一个字都打接口；
 * 4. 依赖变化或卸载时通过 AbortController 取消在途请求，防止竞态导致数据错乱。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  getLiveNews,
  getLiveNewsChannels,
  refreshLiveNews,
} from '../api/liveNews';
import type {
  LiveNewsChannel,
  LiveNewsDateGroup,
  LiveNewsItem,
} from '../types/liveNews';

/** 默认轮询间隔（毫秒） */
const DEFAULT_POLL_INTERVAL_MS = 30_000;
/** 关键词输入防抖时长（毫秒） */
const KEYWORD_DEBOUNCE_MS = 300;

/** 频道列表 Hook 的返回值 */
export interface UseLiveNewsChannelsReturn {
  channels: LiveNewsChannel[];
  /** 是否处于降级模式：只应使用返回的 channels，并隐藏重要级筛选 */
  degraded: boolean;
  source: string;
  loading: boolean;
  error: string | null;
}

/**
 * 拉取快讯频道列表（页面 Tab 数据源）。
 *
 * Tab 来源于后端而非前端常量：官方源不可用降级到 NewsNow 时，
 * 后端只返回「要闻」一个频道，页面会自动收敛为单 Tab。
 */
export function useLiveNewsChannels(): UseLiveNewsChannelsReturn {
  const [channels, setChannels] = useState<LiveNewsChannel[]>([]);
  const [degraded, setDegraded] = useState(false);
  const [source, setSource] = useState('wallstreetcn');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const result = await getLiveNewsChannels();
        if (!active) return;
        setChannels(result.channels);
        setDegraded(result.degraded);
        setSource(result.source);
        setError(null);
      } catch {
        // 接口失败时保持空列表，由页面展示错误态
        if (active) setError('频道列表加载失败');
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    return () => {
      active = false;
    };
  }, []);

  return { channels, degraded, source, loading, error };
}

/** 快讯列表 Hook 的过滤选项 */
export interface UseLiveNewsOptions {
  /** 只看重要的；降级模式下该能力不可用，后端会忽略 */
  importantOnly?: boolean;
  /** 搜索关键词，内部做防抖 */
  keyword?: string;
  /** 精确查询某日 YYYY-MM-DD */
  date?: string | null;
  /** 是否开启轮询，默认开启 */
  autoRefresh?: boolean;
  /** 轮询间隔（毫秒），默认 30 秒 */
  pollIntervalMs?: number;
}

/** 快讯列表 Hook 的返回值 */
export interface UseLiveNewsReturn {
  /** 平铺的快讯列表 */
  items: LiveNewsItem[];
  /** 按天分组后的列表，页面直接按组渲染 */
  grouped: LiveNewsDateGroup[];
  /** 首次加载中 */
  loading: boolean;
  /** 后台轮询刷新中（用于展示轻量刷新态，不遮挡内容） */
  refreshing: boolean;
  error: string | null;
  /** 是否还有下一页 */
  hasMore: boolean;
  /** 是否处于降级模式 */
  degraded: boolean;
  /** 列表是否为空（含「本频道暂无重要快讯」场景） */
  isEmpty: boolean;
  /** 当前过滤条件下的总条数（含未加载的部分），可用于「共 N 条」提示 */
  total: number;
  /** 加载下一页 */
  loadMore: () => void;
  /** 手动刷新：先触发服务端抓取，再重新拉取列表 */
  refresh: () => Promise<void>;
}

/** 把秒级时间戳格式化为 `YYYY-MM-DD` 分组键（按用户本地时区） */
function toDateKey(displayTime: number | null): string {
  if (!displayTime) return '';
  const date = new Date(displayTime * 1000);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** 把秒级时间戳格式化为 `08月28日 周五` 的分组标题 */
function toDateLabel(displayTime: number | null): string {
  if (!displayTime) return '未知时间';
  const date = new Date(displayTime * 1000);
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${month}月${day}日 ${weekdays[date.getDay()]}`;
}

/** 把快讯列表按发布日期分组，保持时间倒序 */
function groupByDate(items: LiveNewsItem[]): LiveNewsDateGroup[] {
  const groups = new Map<string, LiveNewsDateGroup>();
  for (const item of items) {
    const key = toDateKey(item.displayTime);
    const existing = groups.get(key);
    if (existing) {
      existing.items.push(item);
    } else {
      groups.set(key, {
        date: key,
        label: toDateLabel(item.displayTime),
        items: [item],
      });
    }
  }
  return Array.from(groups.values());
}

/**
 * 快讯列表 Hook：按频道分页拉取、可选轮询、按天分组。
 *
 * @param channel 频道 ID；为空时不发起请求（等待 Tab 数据就绪）
 * @param options 过滤与轮询选项
 */
export function useLiveNews(
  channel: string,
  options: UseLiveNewsOptions = {}
): UseLiveNewsReturn {
  const {
    importantOnly = false,
    keyword = '',
    date = null,
    autoRefresh = true,
    pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
  } = options;

  // items 为 null 表示「尚未成功加载过一次」，用于推导首屏加载态；
  // 这样就不必在 effect 中同步 setState（会触发级联渲染），也避免了列表闪烁。
  const [items, setItems] = useState<LiveNewsItem[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [total, setTotal] = useState(0);
  // 仅由用户点击「刷新」按钮驱动，属于事件回调中的 setState，不涉及 effect
  const [manualRefreshing, setManualRefreshing] = useState(false);

  // 关键词防抖后的值，作为查询依赖
  const [debouncedKeyword, setDebouncedKeyword] = useState(keyword);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedKeyword(keyword);
    }, KEYWORD_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [keyword]);

  // 在途请求取消控制器：依赖变化或卸载时中止旧请求，避免竞态
  const abortRef = useRef<AbortController | null>(null);
  // 页面是否可见：后台标签页暂停轮询
  const [visible, setVisible] = useState(
    typeof document === 'undefined' ? true : !document.hidden
  );
  useEffect(() => {
    const handleVisibility = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  /**
   * 拉取列表。
   *
   * 加载态不由本函数设置：首屏加载由 `items === null` 推导，刷新态由
   * `manualRefreshing` 承载。这样本函数内只有数据相关的 setState，
   * 且都发生在 await 之后，避免在 effect 同步路径上触发级联渲染。
   *
   * @param cursor 分页游标；为空表示拉取（或刷新）第一页
   * @param mode 'replace' 覆盖列表（条件变化/刷新）；'append' 追加（加载更多）
   */
  const fetchList = useCallback(
    async (cursor: string | null, mode: 'replace' | 'append') => {
      if (!channel) return;

      // 取消上一次未完成的请求
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const result = await getLiveNews(
          {
            channel,
            importantOnly,
            keyword: debouncedKeyword || undefined,
            date: date || undefined,
            cursor: cursor || undefined,
          },
          controller.signal
        );
        if (controller.signal.aborted) return;

        setItems((prev) => {
          if (mode === 'append') return [...(prev ?? []), ...result.items];
          return result.items;
        });
        setNextCursor(result.nextCursor);
        setDegraded(result.degraded);
        setTotal(result.total);
        setError(null);
      } catch {
        if (controller.signal.aborted) return;
        // 追加失败不影响已加载的内容，仅提示
        setError(mode === 'append' ? '加载更多失败' : '快讯加载失败');
        // 首屏失败时也要脱离加载态，否则会一直转圈
        setItems((prev) => prev ?? []);
      }
    },
    [channel, importantOnly, debouncedKeyword, date]
  );

  // 主查询：频道/重要级/关键词/日期任一变化，都重新拉取第一页。
  //
  // 这里用一个 0ms 定时器把请求推出 effect 的同步执行路径：
  // `react-hooks/set-state-in-effect` 规则不允许在 effect 体内（含其同步调用的
  // 函数）触发 setState，而 fetchList 内部会更新列表数据。延后一个 tick 既能
  // 满足该约束、避免级联渲染，又保留了「依赖变化自动重新拉取」的语义。
  useEffect(() => {
    if (!channel) return;
    let cancelled = false;
    const handle = window.setTimeout(() => {
      if (!cancelled) void fetchList(null, 'replace');
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
      abortRef.current?.abort();
    };
  }, [channel, fetchList]);

  // 轮询：仅第一页、页面可见且开启自动刷新时生效
  useEffect(() => {
    if (!autoRefresh || !visible || !channel) return;
    const timer = window.setInterval(() => {
      void fetchList(null, 'replace');
    }, pollIntervalMs);
    return () => window.clearInterval(timer);
  }, [autoRefresh, visible, channel, pollIntervalMs, fetchList]);

  /** 加载下一页 */
  const loadMore = useCallback(() => {
    if (!nextCursor) return;
    void fetchList(nextCursor, 'append');
  }, [nextCursor, fetchList]);

  /** 手动刷新：先让服务端抓取最新数据，再重拉列表 */
  const refresh = useCallback(async () => {
    setManualRefreshing(true);
    try {
      await refreshLiveNews(channel ? [channel] : undefined);
    } catch {
      // 抓取失败不阻断，仍然重试一次列表拉取，给用户最新的库存数据
    }
    try {
      await fetchList(null, 'replace');
    } finally {
      setManualRefreshing(false);
    }
  }, [channel, fetchList]);

  const grouped = useMemo(() => groupByDate(items ?? []), [items]);
  // 首屏加载态：尚未成功加载过一次，且当前没有报错
  const loading = items === null && !error;

  return {
    items: items ?? [],
    grouped,
    loading,
    refreshing: manualRefreshing,
    error,
    // 后端仅在「取满一页且仍有剩余」时下发游标，因此有游标即可加载更多
    hasMore: Boolean(nextCursor),
    degraded,
    isEmpty: !loading && (items?.length ?? 0) === 0,
    /** 当前过滤条件下的总条数（含未加载的部分），可用于「共 N 条」提示 */
    total,
    loadMore,
    refresh,
  };
}
