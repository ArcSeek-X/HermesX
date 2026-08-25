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
  getWatchlistGroups,
  createWatchlistGroup as apiCreateGroup,
  updateWatchlistGroup as apiUpdateGroup,
  deleteWatchlistGroup as apiDeleteGroup,
  getWatchlistItems,
  createWatchlistItem as apiCreateWatchlistItem,
  updateWatchlistItem as apiUpdateItem,
  deleteWatchlistItem as apiDeleteItem,
  moveWatchlistItem as apiMoveItem,
  type WatchlistGroup,
  type WatchlistItem,
  type WatchlistItemWithQuote,
  type WatchlistQuote,
} from '../api/watchlist';
import { stocksApi } from '../api/stocks';
import { useStockIndex } from './useStockIndex';

/**
 * 空行情占位对象。
 * 当某只股票实时行情拉取失败（接口异常或数据源无数据）时，
 * 列表里的 quote 字段会回到这个空值，UI 上统一显示为「—」。
 */
const EMPTY_QUOTE: WatchlistQuote = {
  currentPrice: null, // 现价
  changePercent: null, // 涨跌幅（%）
  amount: null, // 成交额（元）
  turnoverRate: null, // 换手率（%）
  totalMv: null, // 总市值（元）
};

/**
 * 把后端 stocksApi.getQuote 返回的行情对象，统一转换成列表使用的 WatchlistQuote。
 * 用 ?? 兜底，保证任何字段缺失都回到 null（而非 undefined），便于 UI 判断显示「—」。
 * @param q 后端实时行情对象，可能为 null（拉取失败）
 */
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

/** 默认每页数量（分页拉取自选股列表时使用） */
const DEFAULT_PAGE_SIZE = 2;

/** hook 对外暴露的状态与操作集合 */
export interface UseWatchlistManagerResult {
  // —— 分类（左侧面板）——
  groups: WatchlistGroup[]; // 全部分类列表
  groupsLoading: boolean; // 分类加载中
  loadGroups: () => Promise<void>; // 重新拉取分类列表
  createWatchlistGroup: (name: string, description?: string) => Promise<void>; // 新增分类
  updateWatchlistGroup: (groupCode: string, payload: { name?: string; description?: string }) => Promise<void>; // 编辑分类（按 groupCode 定位）
  deleteWatchlistGroup: (groupCode: string) => Promise<void>; // 删除分类（按 groupCode 定位，后端级联删除其下股票）

  // —— 当前选中分类 ——
  activeGroupId: number | null; // 当前选中的分类 id
  setActiveGroupId: (id: number | null) => void; // 切换分类（会自动重置页码）

  // —— 自选股列表（右侧面板，含行情）——
  items: WatchlistItemWithQuote[]; // 当前分类下的自选股（已合并行情）
  itemsLoading: boolean; // 列表/行情整体加载中
  quotesLoading: boolean; // 仅行情并发拉取中
  loadItems: (groupId: number, pageNum?: number) => Promise<void>; // 加载某分类某一页
  addItem: (groupId: number, payload: { stockCode: string; stockName?: string; description?: string }) => Promise<WatchlistItem>; // 新增自选股
  editItemDescription: (id: number, description: string) => Promise<void>; // 编辑备注
  removeItem: (id: number) => Promise<void>; // 删除自选股
  moveItem: (id: number, targetGroupId: number) => Promise<void>; // 移动归类

  // —— 分页 ——
  pageNum: number; // 当前页码（从 1 开始）
  total: number; // 当前分类下股票总数
  pages: number; // 总页数
  pageSize: number; // 每页数量
  setPageNum: (page: number) => void; // 翻页

  // —— 搜索辅助 ——
  // code -> 本地股票索引（中文名 / 全拼 / 简拼），供页面层做拼音/简拼搜索匹配
  indexByCode: Map<string, { name: string; pinyin: string; pinyinShort: string }>;
}

export function useWatchlistManager(): UseWatchlistManagerResult {
  // —— 分类相关状态 ——
  const [groups, setGroups] = useState<WatchlistGroup[]>([]); // 分类列表
  const [groupsLoading, setGroupsLoading] = useState(false); // 分类加载中标志
  const [activeGroupId, setActiveGroupId] = useState<number | null>(null); // 当前选中的分类 id

  // —— 自选股列表相关状态 ——
  const [items, setItems] = useState<WatchlistItemWithQuote[]>([]); // 当前分类下的自选股（含行情）
  const [itemsLoading, setItemsLoading] = useState(false); // 列表 + 行情整体加载中
  const [quotesLoading, setQuotesLoading] = useState(false); // 仅行情并发拉取中

  // —— 分页状态 ——
  const [pageNum, setPageNum] = useState(1); // 当前页码（从 1 开始）
  const [total, setTotal] = useState(0); // 当前分类下股票总数
  const [pages, setPages] = useState(0); // 总页数
  const pageSize = DEFAULT_PAGE_SIZE; // 每页数量（固定值，便于后续按需调整）

  // 本地股票索引（全量 A/港/美股基础信息，含中文名与拼音），用于拼音/简拼搜索匹配
  const { index } = useStockIndex(true);

  /**
   * 把本地股票索引按代码建立映射，供页面层搜索时根据输入（中文/拼音/简拼）匹配股票。
   * 同时登记 canonicalCode（规范化代码）与 displayCode（展示代码）两个键，
   * 以兼容 watchlist 里存储的代码格式与索引代码格式不一致的情况。
   */
  const indexByCode = useMemo(() => {
    const map = new Map<string, { name: string; pinyin: string; pinyinShort: string }>();
    for (const it of index) {
      const entry = {
        name: it.nameZh ?? '', // 中文名
        pinyin: it.pinyinFull ?? '', // 全拼，如 zhongkeshuguang
        pinyinShort: it.pinyinAbbr ?? '', // 简拼，如 zksg
      };
      if (it.canonicalCode) map.set(it.canonicalCode, entry);
      if (it.displayCode) map.set(it.displayCode, entry);
    }
    return map;
  }, [index]);

  /**
   * 拉取分类列表。
   * 同时维护「当前选中分类」：若之前的选中项仍在列表中则保持不变，
   * 否则自动选中第一个分类（保证右侧始终有分类可展示）。
   */
  const loadGroups = useCallback(async () => {
    setGroupsLoading(true);
    try {
      const data = await getWatchlistGroups();
      setGroups(data);
      setActiveGroupId((prev) => {
        if (prev != null && data.some((g) => g.id === prev)) return prev;
        return data.length > 0 ? data[0].id : null;
      });
    } finally {
      setGroupsLoading(false);
    }
  }, []);

  /**
   * 加载某分类指定页的自选股，并合并实时行情。
   *
   * 关键设计：先清空列表（setItems([])），再并发拉取每只股票的实时行情，
   * 等所有「列表数据 + 行情数据」都加载并处理完毕之后，才一次性 setItems 渲染，
   * 避免先渲染空行情占位、再闪一下填充行情的视觉效果。
   *
   * - 单只股票行情拉取失败会被 .catch(() => null) 兜底，不影响其它股票；
   * - 行情缺失的条目保留 EMPTY_QUOTE 占位，UI 显示「—」。
   */
  const loadItems = useCallback(async (groupId: number, page: number = 1) => {
    setItemsLoading(true);
    setItems([]); // 清空，加载期间表格展示「加载中…」
    try {
      const result = await getWatchlistItems(groupId, page, pageSize);
      setTotal(result.total); // 记录总数用于分页
      setPages(result.pages); // 记录总页数

      // 先把后端返回的股票条目铺好，行情字段先用空占位
      const withQuote: WatchlistItemWithQuote[] = result.list.map((it) => ({ ...it, quote: { ...EMPTY_QUOTE } }));

      // 并发拉取每只股票的实时行情
      if (withQuote.length > 0) {
        setQuotesLoading(true);
        try {
          const quotes = await Promise.all(
            withQuote.map((it) =>
              stocksApi.getQuote(it.stockCode).catch(() => null),
            ),
          );
          // 按索引把行情合并回对应条目，最后一次性渲染
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
        // 没有任何股票时，直接渲染空列表
        setItems(withQuote);
      }
    } finally {
      setItemsLoading(false);
    }
  }, [pageSize]);

  // 初始化：组件挂载后拉取分类列表。
  // 这里 setState 发生在 effect 中，但属于「从外部系统（后端）同步数据」的正当副作用，
  // 因此用针对性 eslint-disable 关闭 react-hooks/set-state-in-effect 规则。
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadGroups();
  }, [loadGroups]);

  // 当「选中分类」或「页码」变化时，重新加载该分类对应页的数据。
  useEffect(() => {
    if (activeGroupId != null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void loadItems(activeGroupId, pageNum);
    } else {
      setItems([]); // 没有选中分类时清空列表
    }
  }, [activeGroupId, pageNum, loadItems]);

  /** 新增分类：写入后追加到本地列表（按 sortOrder/id 排序），若此前无选中项则自动选中新建项 */
  const createWatchlistGroup = useCallback(
    async (name: string, description?: string) => {
      const g = await apiCreateGroup(name, description);
      setGroups((prev) => [...prev, g].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id));
      if (activeGroupId == null) setActiveGroupId(g.id);
    },
    [activeGroupId],
  );

  /** 编辑分类（按 groupCode 定位）：更新后替换本地列表中对应项 */
  const updateWatchlistGroup = useCallback(async (groupCode: string, payload: { name?: string; description?: string }) => {
    const g = await apiUpdateGroup({ groupCode, ...payload });
    setGroups((prev) => prev.map((x) => (x.groupCode === groupCode ? g : x)));
  }, []);

  /** 删除分类（按 groupCode 定位，后端级联删除其下股票）：本地同步移除并更新选中项，页码回到第 1 页 */
  const deleteWatchlistGroup = useCallback(
    async (groupCode: string) => {
      await apiDeleteGroup(groupCode);
      const removed = groups.find((x) => x.groupCode === groupCode);
      setGroups((prev) => prev.filter((x) => x.groupCode !== groupCode));
      setActiveGroupId((prev) => {
        if (removed && prev !== removed.id) return prev;
        const rest = groups.filter((x) => x.groupCode !== groupCode);
        return rest.length > 0 ? rest[0].id : null;
      });
      setPageNum(1);
    },
    [groups],
  );

  /**
   * 新增自选股。成功后：
   * - 若新增的分类正是当前展示的分类，则立即为这只股票拉取实时行情并合并，
   *   把新条目插到列表最前面（仍走「先拿到行情再渲染」的逻辑，避免空占位）。
   * - 行情拉取失败不影响新增成功，仅该条显示空行情占位。
   * - 若新增到其它分类，则不改动当前列表（由用户切换分类时自然加载）。
   */
  const addItem = useCallback(
    async (groupId: number, payload: { stockCode: string; stockName?: string; description?: string }) => {
      const item = await apiCreateWatchlistItem(groupId, payload);
      if (groupId === activeGroupId) {
        let quote: Awaited<ReturnType<typeof stocksApi.getQuote>> | null = null;
        try {
          quote = await stocksApi.getQuote(item.stockCode);
        } catch {
          quote = null; // 行情失败降级为空占位，不阻断新增
        }
        setItems((prev) => [{ ...item, quote: quoteFromStockQuote(quote) }, ...prev]);
      }
      return item;
    },
    [activeGroupId],
  );

  /** 切换分类：更新选中项，并把页码重置为第 1 页（不同分类的页数不同） */
  const handleSetActiveGroupId = useCallback((id: number | null) => {
    setActiveGroupId(id);
    setPageNum(1);
  }, []);

  /** 编辑备注：更新后同步替换本地列表中该条的 description 字段 */
  const editItemDescription = useCallback(async (id: number, description: string) => {
    const item = await apiUpdateItem(id, { description });
    setItems((prev) => prev.map((x) => (x.id === id ? { ...x, description: item.description } : x)));
  }, []);

  /** 删除自选股：后端删除后从本地列表移除该条 */
  const removeItem = useCallback(
    async (id: number) => {
      await apiDeleteItem(id);
      setItems((prev) => prev.filter((x) => x.id !== id));
    },
    [],
  );

  /**
   * 移动归类：把股票从当前分类移动到目标分类。
   * - 若目标分类与当前展示分类不同，则从当前列表移除该条（移动走了）；
   * - 若目标分类就是当前分类（理论上不会触发），则仅更新其 groupId 保持不变。
   */
  const moveItem = useCallback(
    async (id: number, targetGroupId: number) => {
      const item = await apiMoveItem(id, targetGroupId);
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
    createWatchlistGroup,
    updateWatchlistGroup,
    deleteWatchlistGroup,
    activeGroupId,
    setActiveGroupId: handleSetActiveGroupId,
    items,
    itemsLoading,
    quotesLoading,
    loadItems,
    addItem,
    editItemDescription,
    removeItem,
    moveItem,
    pageNum,
    total,
    pages,
    pageSize,
    indexByCode,
    setPageNum,
  };
}
