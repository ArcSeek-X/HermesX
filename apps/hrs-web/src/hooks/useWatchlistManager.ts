/**
 * useWatchlistManager —— 自选股管理状态与操作 Hook。
 *
 * 职责：
 * 1. 加载并维护分类列表、当前选中分类、当前分类下的自选股（含实时行情合并）；
 * 2. 提供分类与自选股的增删改查、移动归类等操作（统一调用 api/watchlist）；
 * 3. 行情合并：按股票代码并发调用 stocksApi.getQuote 填充列表的 quote 字段；
 * 4. 暴露 stockIndex 映射（code -> 本地股票索引记录），供页面做拼音/简拼搜索匹配。
 *
 * 排序与搜索由页面层基于 items + quote 用 useMemo 完成（零后端开销）。
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchGroups,
  createGroup as apiCreateGroup,
  updateGroup as apiUpdateGroup,
  deleteGroup as apiDeleteGroup,
  fetchItems,
  createItem as apiCreateItem,
  updateItem as apiUpdateItem,
  deleteItem as apiDeleteItem,
  moveItem as apiMoveItem,
  type WatchlistGroup,
  type WatchlistItemWithQuote,
  type WatchlistQuote,
} from '../api/watchlist';
import { stocksApi } from '../api/stocks';
import { useStockIndex } from './useStockIndex';

/** 空行情占位（行情缺失时显示「—」） */
const EMPTY_QUOTE: WatchlistQuote = {
  currentPrice: null,
  changePercent: null,
  amount: null,
  turnoverRate: null,
  totalMv: null,
};

function quoteFromStockQuote(q: Awaited<ReturnType<typeof stocksApi.getQuote>> | null): WatchlistQuote {
  if (!q) return { ...EMPTY_QUOTE };
  return {
    currentPrice: q.currentPrice ?? null,
    changePercent: q.changePercent ?? null,
    amount: q.amount ?? null,
    turnoverRate: q.turnoverRate ?? null,
    totalMv: q.totalMv ?? null,
  };
}

export interface UseWatchlistManagerResult {
  // 分类
  groups: WatchlistGroup[];
  groupsLoading: boolean;
  loadGroups: () => Promise<void>;
  createGroup: (name: string) => Promise<void>;
  renameGroup: (id: number, name: string) => Promise<void>;
  removeGroup: (id: number) => Promise<void>;

  // 当前选中分类
  activeGroupId: number | null;
  setActiveGroupId: (id: number | null) => void;

  // 自选股列表（含行情）
  items: WatchlistItemWithQuote[];
  itemsLoading: boolean;
  quotesLoading: boolean;
  loadItems: (groupId: number) => Promise<void>;
  addItem: (groupId: number, payload: { stockCode: string; stockName?: string; note?: string }) => Promise<void>;
  editItemNote: (id: number, note: string) => Promise<void>;
  removeItem: (id: number) => Promise<void>;
  moveItem: (id: number, targetGroupId: number) => Promise<void>;

  // 搜索辅助
  indexByCode: Map<string, { name: string; pinyin: string; pinyinShort: string }>;
}

export function useWatchlistManager(): UseWatchlistManagerResult {
  const [groups, setGroups] = useState<WatchlistGroup[]>([]);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [activeGroupId, setActiveGroupId] = useState<number | null>(null);

  const [items, setItems] = useState<WatchlistItemWithQuote[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [quotesLoading, setQuotesLoading] = useState(false);

  const { index } = useStockIndex(true);

  // 构建 code -> 本地索引（用于拼音/简拼搜索）
  const indexByCode = useMemo(() => {
    const map = new Map<string, { name: string; pinyin: string; pinyinShort: string }>();
    for (const it of index) {
      const entry = {
        name: it.nameZh ?? '',
        pinyin: it.pinyinFull ?? '',
        pinyinShort: it.pinyinAbbr ?? '',
      };
      if (it.canonicalCode) map.set(it.canonicalCode, entry);
      if (it.displayCode) map.set(it.displayCode, entry);
    }
    return map;
  }, [index]);

  const loadGroups = useCallback(async () => {
    setGroupsLoading(true);
    try {
      const data = await fetchGroups();
      setGroups(data);
      setActiveGroupId((prev) => {
        if (prev != null && data.some((g) => g.id === prev)) return prev;
        return data.length > 0 ? data[0].id : null;
      });
    } finally {
      setGroupsLoading(false);
    }
  }, []);

  const loadItems = useCallback(async (groupId: number) => {
    setItemsLoading(true);
    // 先清空列表，等行情全部加载并处理完毕后再一次性渲染，避免中途渲染空行情占位
    setItems([]);
    try {
      const base = await fetchItems(groupId);
      const withQuote: WatchlistItemWithQuote[] = base.map((it) => ({ ...it, quote: { ...EMPTY_QUOTE } }));

      // 先并发拉取全部实时行情；等所有数据加载并处理完毕后再一次性渲染列表
      if (withQuote.length > 0) {
        setQuotesLoading(true);
        try {
          const quotes = await Promise.all(
            withQuote.map((it) =>
              stocksApi.getQuote(it.stockCode).catch(() => null),
            ),
          );
          const merged = withQuote.map((it, i) => {
            const q = quotes[i];
            if (!q) return it;
            return { ...it, quote: quoteFromStockQuote(q) };
          });
          setItems(merged);
        } finally {
          setQuotesLoading(false);
        }
      } else {
        setItems(withQuote);
      }
    } finally {
      setItemsLoading(false);
    }
  }, []);

  // 初始化：加载分类（数据加载副作用，属 effect 同步外部系统的正当用例）
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadGroups();
  }, [loadGroups]);

  // 切换分类时加载该分类股票（数据加载副作用，属 effect 同步外部系统的正当用例）
  useEffect(() => {
    if (activeGroupId != null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void loadItems(activeGroupId);
    } else {
      setItems([]);
    }
  }, [activeGroupId, loadItems]);

  const createGroup = useCallback(
    async (name: string) => {
      const g = await apiCreateGroup(name);
      setGroups((prev) => [...prev, g].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id));
      if (activeGroupId == null) setActiveGroupId(g.id);
    },
    [activeGroupId],
  );

  const renameGroup = useCallback(async (id: number, name: string) => {
    const g = await apiUpdateGroup(id, { name });
    setGroups((prev) => prev.map((x) => (x.id === id ? g : x)));
  }, []);

  const removeGroup = useCallback(
    async (id: number) => {
      await apiDeleteGroup(id);
      setGroups((prev) => prev.filter((x) => x.id !== id));
      setActiveGroupId((prev) => {
        if (prev !== id) return prev;
        const rest = groups.filter((x) => x.id !== id);
        return rest.length > 0 ? rest[0].id : null;
      });
    },
    [groups],
  );

  const addItem = useCallback(
    async (groupId: number, payload: { stockCode: string; stockName?: string; note?: string }) => {
      const item = await apiCreateItem(groupId, payload);
      if (groupId === activeGroupId) {
        // 立即拉取新增股票的实时行情并合并；行情失败不影响新增成功，仍用空行情占位
        let quote: Awaited<ReturnType<typeof stocksApi.getQuote>> | null = null;
        try {
          quote = await stocksApi.getQuote(item.stockCode);
        } catch {
          quote = null;
        }
        setItems((prev) => [{ ...item, quote: quoteFromStockQuote(quote) }, ...prev]);
      }
      return item;
    },
    [activeGroupId],
  );

  const editItemNote = useCallback(async (id: number, note: string) => {
    const item = await apiUpdateItem(id, { note });
    setItems((prev) => prev.map((x) => (x.id === id ? { ...x, note: item.note } : x)));
  }, []);

  const removeItem = useCallback(
    async (id: number) => {
      await apiDeleteItem(id);
      setItems((prev) => prev.filter((x) => x.id !== id));
    },
    [],
  );

  const moveItem = useCallback(
    async (id: number, targetGroupId: number) => {
      const item = await apiMoveItem(id, targetGroupId);
      // 若移动到其它分类，当前列表移除该条；否则更新归属
      setItems((prev) =>
        prev
          .filter((x) => x.id !== id || x.groupId === targetGroupId)
          .map((x) => (x.id === id ? { ...x, groupId: item.groupId } : x)),
      );
    },
    [],
  );

  return {
    groups,
    groupsLoading,
    loadGroups,
    createGroup,
    renameGroup,
    removeGroup,
    activeGroupId,
    setActiveGroupId,
    items,
    itemsLoading,
    quotesLoading,
    loadItems,
    addItem,
    editItemNote,
    removeItem,
    moveItem,
    indexByCode,
  };
}
