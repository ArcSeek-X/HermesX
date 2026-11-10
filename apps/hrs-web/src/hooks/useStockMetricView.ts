/**
 * @file hooks/useStockMetricView.ts
 * @description 股票度量视图领域状态机：持有筛选 / 排序 / 分页状态，负责请求编排
 * （竞态守卫、卸载防写入）、筛选条件持久化与 CSV 导出；仅返回领域命名的结果对象，不依赖页面组件。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { stockMetricViewApi } from '@/api/stockMetricView';
import { getParsedApiError } from '@/api/error';
import type {
  StockMetricViewFilterField,
  StockMetricViewFilterItem,
  StockMetricViewFilterOp,
  StockMetricViewResultDef,
  StockMetricViewRow,
  StockMetricViewSortDef,
  StockMetricViewSupportedMarket,
} from '@/types/stockMetricView';

/** localStorage 持久化键：保存筛选条件（不含分页 / 排序） */
const FILTER_STORAGE_KEY = 'hermesx.stockMetricView.filters';
/** 默认筛选：仅 cn 市场 */
const DEFAULT_MARKET_FILTER: StockMetricViewFilterItem = {
  field: 'market',
  op: 'in',
  value: ['cn'],
};
/** 默认排序：总市值降序 */
const DEFAULT_SORT: StockMetricViewSortDef = { field: 'totalMarketCap', order: 'desc' };
/** 每页默认条数 */
const DEFAULT_PAGE_SIZE = 20;
/** cn 专属离线列：切到 hk / us 时整列被剔除，排序字段必须回退，避免指向不存在的列 */
const CN_ONLY_SORT_FIELDS = new Set(['epsGrowthTtmYoyPct', 'analystRating']);

/**
 * 把在线快照抓取时刻（ISO 8601 带 UTC 偏移）解析为 Date；空串 / 非法值返回 null。
 * 旧版后端回的是 UTC-naive 串（无时区标记），浏览器会误按本地时区解析；对其补 Z
 * 按 UTC 处理，避免前后端版本错配时显示时间差 8 小时。
 */
function parseQuoteAsOf(value: string): Date | null {
  if (!value) return null;
  const hasTimezone = value.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(value);
  const parsed = new Date(hasTimezone ? value : `${value}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** 把任意历史市场值收窄为单个受支持市场；非法 / 多值一律取首个有效值或回退 cn */
function normalizeMarket(value: unknown): StockMetricViewSupportedMarket {
  const first = Array.isArray(value) ? value[0] : value;
  return first === 'cn' || first === 'hk' || first === 'us' ? first : 'cn';
}

/** 从 localStorage 读取筛选条件；解析失败、非数组或历史多市场值都归一为单选契约 */
function loadPersistedFilters(): StockMetricViewFilterItem[] {
  try {
    const raw = localStorage.getItem(FILTER_STORAGE_KEY);
    if (!raw) return [DEFAULT_MARKET_FILTER];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [DEFAULT_MARKET_FILTER];
    const filters = parsed as StockMetricViewFilterItem[];
    const market = filters.find((item) => item.field === 'market');
    return [
      { field: 'market', op: 'in', value: [normalizeMarket(market?.value)] },
      ...filters.filter((item) => item.field !== 'market'),
    ];
  } catch {
    return [DEFAULT_MARKET_FILTER];
  }
}

/** 持久化筛选条件到 localStorage；写入失败（隐私模式等）静默忽略 */
function persistFilters(filters: StockMetricViewFilterItem[]): void {
  try {
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filters));
  } catch {
    /* 忽略持久化失败 */
  }
}

/** useStockMetricView 返回值：领域命名，列定义由页面组件自行组装 */
export interface UseStockMetricViewResult {
  /** 完整筛选条件（含 market 条件） */
  filterList: StockMetricViewFilterItem[];
  /** 可编辑的非市场条件（供筛选区渲染） */
  conditions: StockMetricViewFilterItem[];
  /** 当前选择的市场（单选，从 market 条件派生） */
  selectedMarket: StockMetricViewSupportedMarket;
  /** 当前页数据（后端已分页，直接作为 Table 的 rows） */
  list: StockMetricViewRow[];
  /** 命中总数 */
  total: number;
  /** 每页条数 */
  pageSize: number;
  /** 总页数 */
  pages: number;
  /** 当前页码 */
  pageNum: number;
  /** 当前排序（领域语义） */
  sortDescriptor: StockMetricViewSortDef;
  /** 离线因子基准日 */
  asOfDate: string;
  /** 本批在线快照的抓取时刻（ISO 8601 带 UTC 偏移） */
  quoteAsOf: string;
  /** 由 quoteAsOf 解析出的抓取时刻，供新鲜度条展示；无数据 / 非法值为 null */
  quoteUpdatedAt: Date | null;
  /** 口径 / 降级提示 */
  warnings: string[];
  /** 是否降级（因子表不可用，仅实时列） */
  degraded: boolean;
  /** 是否加载中 */
  isLoading: boolean;
  /** 是否导出中 */
  isExporting: boolean;
  /** 错误信息（null 表示无错误） */
  errorMessage: string | null;
  /** 切换市场（单选）并重置到第 1 页 */
  setMarketFilter: (market: StockMetricViewSupportedMarket) => void;
  /** 用整组非市场筛选条件替换（条件编辑器保存时一次性提交） */
  setConditions: (items: StockMetricViewFilterItem[]) => void;
  /** 选中 / 清除股票搜索：维护 code 条件，可选同步市场单选，立即查询并回到第 1 页 */
  selectStock: (code: string | null, market?: StockMetricViewSupportedMarket | null) => void;
  /** 按 conditions 下标删除一条筛选条件 */
  removeFilter: (index: number) => void;
  /** 清空非市场条件（保留 market）并回到第 1 页 */
  resetFilters: () => void;
  /** 设置排序并回到第 1 页 */
  setSortDescriptor: (sort: StockMetricViewSortDef) => void;
  /** 翻页 */
  setPageNum: (pageNum: number) => void;
  /** 点「查询」提交当前筛选条件并回到第 1 页 */
  applyFilters: () => void;
  /** 手动刷新（沿用当前筛选 / 排序 / 分页） */
  refresh: () => void;
  /** 触发 CSV 导出（传入当前可见列定义以获取本地化表头） */
  exportCsv: (visibleColumns: { key: string; title: string }[]) => Promise<void>;
}

/** useStockMetricView：股票度量视图的查询状态机 */
export function useStockMetricView(): UseStockMetricViewResult {
  const [filterList, setFilterList] = useState<StockMetricViewFilterItem[]>(loadPersistedFilters);
  const [sortDescriptor, setSort] = useState<StockMetricViewSortDef>(DEFAULT_SORT);
  const [pageNum, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const [list, setList] = useState<StockMetricViewRow[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [asOfDate, setAsOfDate] = useState('');
  const [quoteAsOf, setQuoteAsOf] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [degraded, setDegraded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 竞态守卫：仅接受最后一次请求的响应
  const requestIdRef = useRef(0);
  // 卸载后禁止写入状态
  const mountedRef = useRef(true);
  // 最新请求参数快照，避免闭包取到过期值
  const paramsRef = useRef({ filterList, sortDescriptor, pageNum, pageSize });

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    paramsRef.current = { filterList, sortDescriptor, pageNum, pageSize };
  }, [filterList, sortDescriptor, pageNum, pageSize]);

  /** 发起查询；overrides 优先于当前快照，用于即时翻页 / 排序 / 切市场 */
  const queryMetricView = useCallback(
    async (overrides: Partial<{
      filterList: StockMetricViewFilterItem[];
      sort: StockMetricViewSortDef;
      pageNum: number;
      pageSize: number;
      forceRefresh: boolean;
    }> = {}) => {
      const requestId = ++requestIdRef.current;
      const payload = {
        filterList: overrides.filterList ?? paramsRef.current.filterList,
        sort: overrides.sort ?? paramsRef.current.sortDescriptor,
        pageNum: overrides.pageNum ?? paramsRef.current.pageNum,
        pageSize: overrides.pageSize ?? paramsRef.current.pageSize,
        forceRefresh: overrides.forceRefresh ?? false,
      };
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const result: StockMetricViewResultDef = await stockMetricViewApi.query(payload);
        // 过期响应或已卸载：丢弃，避免覆盖最新结果
        if (requestIdRef.current !== requestId || !mountedRef.current) return;
        // 请求期间保留上一页数据，避免表格闪空；仅在拿到新数据后替换
        setList(result.list);
        setTotal(result.total);
        setPages(result.pages);
        setPage(result.pageNum);
        setPageSize(result.pageSize);
        setAsOfDate(result.asOfDate);
        setQuoteAsOf(result.quoteAsOf);
        setWarnings(result.warnings);
        setDegraded(result.degraded);
      } catch (err) {
        if (requestIdRef.current !== requestId || !mountedRef.current) return;
        setErrorMessage(getParsedApiError(err).message);
      } finally {
        if (requestIdRef.current === requestId && mountedRef.current) setIsLoading(false);
      }
    },
    [],
  );

  // 首次挂载即发起查询；后续由交互显式触发
  useEffect(() => {
    // 挂载即查询属预期；setState-in-effect / 空依赖为误报
    // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
    void queryMetricView();
  }, []);

  // 从 filterList 派生市场条件、可编辑条件与当前单选市场
  const marketCondition = useMemo(
    () => filterList.find((f) => f.field === 'market'),
    [filterList],
  );
  const conditions = useMemo(
    () => filterList.filter((f) => f.field !== 'market'),
    [filterList],
  );
  const selectedMarket = useMemo(
    () => normalizeMarket(marketCondition?.value),
    [marketCondition],
  );
  /** 在线快照抓取时刻：随 quoteAsOf 变化，供 DataRefreshBar 的 lastUpdate 使用 */
  const quoteUpdatedAt = useMemo(() => parseQuoteAsOf(quoteAsOf), [quoteAsOf]);

  /** 用新的非市场条件重组 filterList（market 条件始终置首），并持久化 */
  const commitConditions = useCallback(
    (nextConditions: StockMetricViewFilterItem[]) => {
      const market = marketCondition ?? DEFAULT_MARKET_FILTER;
      const next = [market, ...nextConditions];
      setFilterList(next);
      persistFilters(next);
    },
    [marketCondition],
  );

  const setMarketFilter = useCallback(
    (market: StockMetricViewSupportedMarket) => {
      const marketConditionItem: StockMetricViewFilterItem = {
        field: 'market',
        op: 'in',
        value: [market],
      };
      const next = [marketConditionItem, ...conditions];
      const currentSort = paramsRef.current.sortDescriptor;
      // 切到 hk / us 后 cn 专属列被剔除，若仍按这些列排序会让列头排序状态指向不存在的列
      const needsSortFallback =
        market !== 'cn' && CN_ONLY_SORT_FIELDS.has(currentSort.field);
      setFilterList(next);
      persistFilters(next);
      setPage(1);
      // 切市场会同步改变列集合；先清掉旧市场行，避免「新列 + 旧行」进入表格集合
      setList([]);
      setTotal(0);
      setPages(0);
      if (needsSortFallback) setSort(DEFAULT_SORT);
      void queryMetricView({
        filterList: next,
        sort: needsSortFallback ? DEFAULT_SORT : currentSort,
        pageNum: 1,
      });
    },
    [conditions, queryMetricView],
  );

  /** 用整组非市场条件替换：条件编辑器保存时一次性提交，避免逐条写入的闭包覆盖 */
  const setConditions = useCallback(
    (items: StockMetricViewFilterItem[]) => {
      commitConditions(items);
      setPage(1);
    },
    [commitConditions],
  );

  /** 选中 / 清除股票搜索：code 条件整组替换；传入 market 时同步市场单选
   * （搜索覆盖全市场索引，选中跨市场股票时自动切换，保证列表能看到该股票），立即查询 */
  const selectStock = useCallback(
    (code: string | null, market?: StockMetricViewSupportedMarket | null) => {
      const rest = conditions.filter((item) => item.field !== 'code');
      const nextConditions: StockMetricViewFilterItem[] = code
        ? [...rest, { field: 'code', op: 'eq', value: code }]
        : rest;
      const marketItem: StockMetricViewFilterItem = market
        ? { field: 'market', op: 'in', value: [market] }
        : (marketCondition ?? DEFAULT_MARKET_FILTER);
      const next = [marketItem, ...nextConditions];
      const targetMarket = normalizeMarket(marketItem.value);
      const currentSort = paramsRef.current.sortDescriptor;
      const needsSortFallback =
        targetMarket !== 'cn' && CN_ONLY_SORT_FIELDS.has(currentSort.field);
      setFilterList(next);
      persistFilters(next);
      setPage(1);
      if (needsSortFallback) setSort(DEFAULT_SORT);
      void queryMetricView({
        filterList: next,
        sort: needsSortFallback ? DEFAULT_SORT : currentSort,
        pageNum: 1,
      });
    },
    [conditions, marketCondition, queryMetricView],
  );

  const removeFilter = useCallback(
    (index: number) => {
      const nextConditions = conditions.filter((_, i) => i !== index);
      commitConditions(nextConditions);
    },
    [commitConditions, conditions],
  );

  const resetFilters = useCallback(() => {
    commitConditions([]);
    setPage(1);
  }, [commitConditions]);

  const setSortDescriptor = useCallback(
    (sort: StockMetricViewSortDef) => {
      setSort(sort);
      void queryMetricView({ sort, pageNum: 1 });
    },
    [queryMetricView],
  );

  const setPageNum = useCallback(
    (next: number) => {
      setPage(next);
      void queryMetricView({ pageNum: next });
    },
    [queryMetricView],
  );

  const applyFilters = useCallback(() => {
    setPage(1);
    void queryMetricView({ pageNum: 1 });
  }, [queryMetricView]);

  /** 手动刷新：跳过服务端在线快照 TTL 缓存，其余翻页 / 排序交互命中缓存 */
  const refresh = useCallback(() => {
    void queryMetricView({ forceRefresh: true });
  }, [queryMetricView]);

  const exportCsv = useCallback(
    async (visibleColumns: { key: string; title: string }[]) => {
      setIsExporting(true);
      setErrorMessage(null);
      try {
        const headers: Record<string, string> = {};
        visibleColumns.forEach((column) => {
          headers[column.key] = column.title;
        });
        const blob = await stockMetricViewApi.exportCsv({
          filterList: paramsRef.current.filterList,
          sort: paramsRef.current.sortDescriptor,
          headers,
          visibleColumns: visibleColumns.map((column) => column.key),
          limit: 5000,
        });
        // 触发浏览器下载（文件名带日期，避免依赖额外日期库）
        const dateStamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `stock-metric-view_${dateStamp}.csv`;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        URL.revokeObjectURL(url);
      } catch (err) {
        setErrorMessage(getParsedApiError(err).message);
      } finally {
        setIsExporting(false);
      }
    },
    [],
  );

  return {
    filterList,
    conditions,
    selectedMarket,
    list,
    total,
    pageSize,
    pages,
    pageNum,
    sortDescriptor,
    asOfDate,
    quoteAsOf,
    quoteUpdatedAt,
    warnings,
    degraded,
    isLoading,
    isExporting,
    errorMessage,
    setMarketFilter,
    setConditions,
    selectStock,
    removeFilter,
    resetFilters,
    setSortDescriptor,
    setPageNum,
    applyFilters,
    refresh,
    exportCsv,
  };
}

/** 筛选字段可选项（供筛选区下拉使用） */
export const STOCK_METRIC_FILTERABLE_FIELDS: StockMetricViewFilterField[] = [
  'price',
  'changePct',
  'totalMarketCap',
  'peRatioTTM',
  'dividendYieldPct',
  'roePct',
  'pbRatio',
  'psRatioTTM',
  'revenueGrowthYoyPct',
];

/** 可选算子（数值字段支持比较 / 区间，枚举字段支持 in） */
export const STOCK_METRIC_FILTER_OPS: StockMetricViewFilterOp[] = [
  'eq',
  'neq',
  'gt',
  'gte',
  'lt',
  'lte',
  'between',
  'in',
];
