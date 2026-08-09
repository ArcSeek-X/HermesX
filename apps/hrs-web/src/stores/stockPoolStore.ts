import { create } from 'zustand';
import { analysisApi, DuplicateTaskError } from '../api/analysis';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { historyApi } from '../api/history';
import type { AnalysisReport, HistoryItem, HistoryListResponse, ReportLanguage, StockBarItem, StockHistoryFilters, StockHistoryRange, TaskInfo } from '../types/analysis';
import { getRecentStartDate, getTodayInShanghai } from '../utils/format';
import { normalizeStockCode } from '../utils/stockCode';
import { isObviouslyInvalidStockQuery, looksLikeStockCode, validateStockCode } from '../utils/validation';

/** 普通历史报告列表每页条数 */
const PAGE_SIZE = 20;
/** 个股历史走势每次加载条数 */
const STOCK_HISTORY_PAGE_SIZE = 20;
/** 大盘历史报告每次加载条数 */
const MARKET_REVIEW_HISTORY_PAGE_SIZE = 10;
/** 大盘历史报告的虚拟股票代码标识 */
const MARKET_REVIEW_HISTORY_CODE = 'MARKET';

/** 股票来源类型：手动输入、自动补全、批量导入、图片识别 */
type SelectionSource = 'manual' | 'autocomplete' | 'import' | 'image';

/** 加载历史报告的选项 */
type FetchHistoryOptions = {
  /** 加载后自动选中第一条 */
  autoSelectFirst?: boolean;
  /** 是否重置分页（从头加载） */
  reset?: boolean;
  /** 静默刷新：保留现有列表，仅追加/更新项 */
  silent?: boolean;
  /** 针对指定股票代码，自动选中其最新一条报告 */
  selectLatestForStockCode?: string;
};

/** 提交分析任务的选项 */
type SubmitAnalysisOptions = {
  stockCode?: string;
  stockName?: string;
  /** 用户原始输入（可能是名称/代码/混合） */
  originalQuery?: string;
  selectionSource?: SelectionSource;
  /** 是否开启完成通知 */
  notify?: boolean;
  /** 强制刷新（忽略缓存） */
  forceRefresh?: boolean;
  /** 启用的技能标签 */
  skills?: string[];
  /** 报告语言 */
  reportLanguage?: ReportLanguage;
};

/** 已完成任务的选中意图：记录手动选中的序号与报告 ID，用于轮询抵回时还原选中态 */
type CompletedTaskSelectionIntent = {
  manualSelectionSeq: number;
  selectedReportId: number | undefined;
};

// —— 并发请求序号计数器 ——
// 每个网络请求维度维护独立递增 seq，请求返回时通过比较 requestId === *RequestSeq
// 判断是否已被更新的请求取代，若被取代则丢弃过期响应，避免竞态。
let reportRequestSeq = 0;
let analyzeRequestSeq = 0;
let historyRequestSeq = 0;
let marketReviewHistoryRequestSeq = 0;
let stockHistoryRequestSeq = 0;
let stockBarRequestSeq = 0;
let activeTaskRequestSeq = 0;
/** 主动任务列表的本地修订计数，用于触发依赖重算 */
let activeTaskLocalRevision = 0;
let manualSelectionRequestSeq = 0;
let manualSelectionRequestId = 0;
/** 已被用户忽略（dismiss）的任务 ID 集合，忽略后不再自动选中或弹通知 */
const dismissedTaskIds = new Set<string>();
/** 待处理的"已完成任务→选中报告"意图，按 key 存储，轮询对账后消费 */
const pendingCompletedTaskSelectionKeys = new Map<string, CompletedTaskSelectionIntent>();

export interface StockPoolState {
  // —— 输入与提交态 ——
  /** 当前股票查询输入框内容 */
  query: string;
  /** 最近一次选股来源 */
  selectionSource: SelectionSource;
  /** 是否开启分析完成通知 */
  notify: boolean;
  /** 输入框校验错误文案（如格式不合法） */
  inputError?: string;
  /** 重复任务提示（检测到已存在相同股票的分析任务） */
  duplicateError: string | null;
  /** 统一错误对象（网络/服务端错误） */
  error: ParsedApiError | null;
  /** 是否正在提交分析 */
  isAnalyzing: boolean;

  // —— 普通历史报告 ——
  /** 历史报告列表 */
  historyItems: HistoryItem[];
  /** 勾选的历史报告 ID（用于批量删除） */
  selectedHistoryIds: number[];
  /** 是否正在删除历史 */
  isDeletingHistory: boolean;
  /** 是否首次加载历史中 */
  isLoadingHistory: boolean;
  /** 是否加载更多历史中 */
  isLoadingMore: boolean;
  /** 是否还有更多历史可加载 */
  hasMore: boolean;
  /** 当前历史分页页码 */
  currentPage: number;

  // —— 大盘历史报告 ——
  /** 大盘历史报告列表 */
  marketReviewHistoryItems: HistoryItem[];
  /** 勾选的大盘历史 ID */
  selectedMarketReviewHistoryIds: number[];
  /** 是否正在加载大盘历史 */
  isLoadingMarketReviewHistory: boolean;
  /** 是否加载更多大盘历史中 */
  isLoadingMoreMarketReviewHistory: boolean;
  /** 是否正在删除大盘历史 */
  isDeletingMarketReviewHistory: boolean;
  /** 大盘历史是否还有更多 */
  marketReviewHistoryHasMore: boolean;
  /** 当前大盘历史分页页码 */
  marketReviewHistoryPage: number;

  // —— 报告详情 ——
  /** 当前选中的历史报告详情 */
  selectedReport: AnalysisReport | null;
  /** 是否正在加载报告详情 */
  isLoadingReport: boolean;

  // —— 个股历史走势（抽屉） ——
  /** 个股历史走势抽屉是否展开 */
  isHistoryTrendOpen: boolean;
  /** 个股历史走势报告列表 */
  stockHistoryItems: HistoryItem[];
  /** 个股历史报告总数 */
  stockHistoryTotal: number;
  /** 个股历史当前分页页码 */
  stockHistoryPage: number;
  /** 个股历史是否还有更多 */
  stockHistoryHasMore: boolean;
  /** 是否加载个股历史中 */
  isLoadingStockHistory: boolean;
  /** 是否加载更多个股历史中 */
  isLoadingMoreStockHistory: boolean;
  /** 个股历史加载错误 */
  stockHistoryError: ParsedApiError | null;
  /** 个股历史筛选条件（日期区间/模型/排序） */
  stockHistoryFilters: StockHistoryFilters;

  // —— 分析任务 ——
  /** 进行中的分析任务列表 */
  activeTasks: TaskInfo[];
  /** Markdown 报告抽屉是否打开 */
  markdownDrawerOpen: boolean;

  // —— 股票条 ——
  /** 最近 90 天股票条列表 */
  stockBarItems: StockBarItem[];
  /** 是否正在加载股票条 */
  isLoadingStockBar: boolean;
  /** 股票条刷新是否失败 */
  stockBarRefreshFailed: boolean;

  // —— Actions ——
  /** 更新查询输入 */
  setQuery: (query: string) => void;
  /** 清空统一错误 */
  clearError: () => void;
  /** 清空内联提示（inputError / duplicateError） */
  clearInlineMessages: () => void;
  /** 打开 Markdown 报告抽屉 */
  openMarkdownDrawer: () => void;
  /** 关闭 Markdown 报告抽屉 */
  closeMarkdownDrawer: () => void;
  /** 打开个股历史走势抽屉并加载数据 */
  openHistoryTrend: () => Promise<void>;
  /** 关闭个股历史走势抽屉 */
  closeHistoryTrend: () => void;
  /** 切换个股历史日期区间后重载 */
  setStockHistoryRange: (range: StockHistoryRange) => Promise<void>;
  /** 加载更多个股历史 */
  loadMoreStockHistory: () => Promise<void>;
  /** 首次加载普通历史 */
  loadInitialHistory: () => Promise<void>;
  /** 刷新普通历史（silent 时为静默追加） */
  refreshHistory: (silent?: boolean) => Promise<void>;
  /** 分析任务完成时刷新历史并自动选中对应报告 */
  refreshHistoryForCompletedTask: (task: TaskInfo) => Promise<void>;
  /** 加载更多普通历史 */
  loadMoreHistory: () => Promise<void>;
  /** 加载大盘历史 */
  loadMarketReviewHistory: () => Promise<void>;
  /** 刷新大盘历史（silent 时为静默追加） */
  refreshMarketReviewHistory: (silent?: boolean) => Promise<void>;
  /** 加载更多大盘历史 */
  loadMoreMarketReviewHistory: () => Promise<void>;
  /** 选中某条历史报告（isUserInitiated 标记是否用户主动点击） */
  selectHistoryItem: (recordId: number, isUserInitiated?: boolean) => Promise<void>;
  /** 切换单条历史勾选 */
  toggleHistorySelection: (recordId: number) => void;
  /** 切换当前页全选 */
  toggleSelectAllVisible: () => void;
  /** 删除勾选的历史报告 */
  deleteSelectedHistory: () => Promise<void>;
  /** 切换单条大盘历史勾选 */
  toggleMarketReviewHistorySelection: (recordId: number) => void;
  /** 切换大盘历史当前页全选 */
  toggleSelectAllVisibleMarketReviewHistory: () => void;
  /** 删除勾选的大盘历史报告 */
  deleteSelectedMarketReviewHistory: () => Promise<void>;
  /** 提交股票分析任务 */
  submitAnalysis: (options?: SubmitAnalysisOptions) => Promise<void>;
  /** 设置是否开启通知 */
  setNotify: (notify: boolean) => void;
  /** 同步任务创建事件（来自 SSE/WebSocket） */
  syncTaskCreated: (task: TaskInfo) => void;
  /** 同步任务更新事件 */
  syncTaskUpdated: (task: TaskInfo) => void;
  /** 同步任务失败事件 */
  syncTaskFailed: (task: TaskInfo) => void;
  /** 拉取最新进行中的任务列表（轮询对账） */
  refreshActiveTasks: () => Promise<void>;
  /** 从列表移除某任务 */
  removeTask: (taskId: string) => void;
  /** 重置首页工作台所有状态到初始态 */
  resetDashboardState: () => void;
  /** 加载股票条 */
  loadStockBar: () => Promise<void>;
  /** 刷新股票条 */
  refreshStockBar: () => Promise<void>;
}

/** Store 初始状态：所有字段回到空白/默认，用于 resetDashboardState */
const initialState = {
  query: '',
  selectionSource: 'manual' as SelectionSource,
  notify: true,
  inputError: undefined,
  duplicateError: null,
  error: null,
  isAnalyzing: false,
  historyItems: [] as HistoryItem[],
  selectedHistoryIds: [] as number[],
  isDeletingHistory: false,
  isLoadingHistory: false,
  isLoadingMore: false,
  // 默认认为还有更多，首次加载后会由接口返回的 hasMore 修正
  hasMore: true,
  currentPage: 1,
  marketReviewHistoryItems: [] as HistoryItem[],
  selectedMarketReviewHistoryIds: [] as number[],
  isLoadingMarketReviewHistory: false,
  isLoadingMoreMarketReviewHistory: false,
  isDeletingMarketReviewHistory: false,
  marketReviewHistoryHasMore: false,
  marketReviewHistoryPage: 1,
  selectedReport: null as AnalysisReport | null,
  isLoadingReport: false,
  isHistoryTrendOpen: false,
  stockHistoryItems: [] as HistoryItem[],
  stockHistoryTotal: 0,
  stockHistoryPage: 1,
  stockHistoryHasMore: false,
  isLoadingStockHistory: false,
  isLoadingMoreStockHistory: false,
  stockHistoryError: null as ParsedApiError | null,
  stockHistoryFilters: {
    range: 'all' as StockHistoryRange,
    model: 'all',
    sort: 'desc' as const,
  },
  activeTasks: [] as TaskInfo[],
  markdownDrawerOpen: false,
  stockBarItems: [] as StockBarItem[],
  isLoadingStockBar: false,
  stockBarRefreshFailed: false,
};

/** 构造普通历史查询参数：默认取最近 30 天，分页大小 PAGE_SIZE */
function buildHistoryParams(page: number) {
  return {
    startDate: getRecentStartDate(30),
    endDate: getTodayInShanghai(),
    page,
    limit: PAGE_SIZE,
  };
}

/** 构造大盘历史查询参数：固定股票代码 MARKET，报告类型 market_review */
function buildMarketReviewHistoryParams(page: number) {
  return {
    stockCode: MARKET_REVIEW_HISTORY_CODE,
    reportType: 'market_review' as const,
    page,
    limit: MARKET_REVIEW_HISTORY_PAGE_SIZE,
  };
}

/** 构造个股历史查询参数：按股票代码、日期区间（30d/90d）分页加载 */
function buildStockHistoryParams(stockCode: string, page: number, filters: StockHistoryFilters) {
  const params: {
    stockCode: string;
    reportType?: 'market_review';
    startDate?: string;
    endDate?: string;
    page: number;
    limit: number;
  } = {
    stockCode,
    page,
    limit: STOCK_HISTORY_PAGE_SIZE,
  };

  if (stockCode === MARKET_REVIEW_HISTORY_CODE) {
    params.reportType = 'market_review';
  }

  if (filters.range === '30d') {
    params.startDate = getRecentStartDate(30);
    params.endDate = getTodayInShanghai();
  } else if (filters.range === '90d') {
    params.startDate = getRecentStartDate(90);
    params.endDate = getTodayInShanghai();
  }

  return params;
}

/** 将完整分析报告转换为历史列表项（仅取摘要关键字段）；缺少 id 时返回 null */
function reportToHistoryItem(report: AnalysisReport): HistoryItem | null {
  if (report.meta.id === undefined) {
    return null;
  }

  return {
    id: report.meta.id,
    queryId: report.meta.queryId,
    stockCode: report.meta.stockCode,
    stockName: report.meta.stockName,
    reportType: report.meta.reportType,
    trendPrediction: report.summary.trendPrediction,
    analysisSummary: report.summary.analysisSummary,
    sentimentScore: report.summary.sentimentScore,
    operationAdvice: report.summary.operationAdvice,
    action: report.summary.action,
    actionLabel: report.summary.actionLabel,
    currentPrice: report.meta.currentPrice,
    changePct: report.meta.changePct,
    modelUsed: report.meta.modelUsed,
    createdAt: report.meta.createdAt,
  };
}

/** 归一化选中的报告：若大盘报告缺少 stockCode，补上虚拟标识 MARKET */
function normalizeSelectedReport(report: AnalysisReport): AnalysisReport {
  if (report.meta.reportType !== 'market_review' || report.meta.stockCode) {
    return report;
  }
  return {
    ...report,
    meta: {
      ...report.meta,
      stockCode: MARKET_REVIEW_HISTORY_CODE,
    },
  };
}

/** 将股票代码归一化为大写规范 key，用于任务与历史之间的跨维度匹配 */
function normalizeStockCodeKey(stockCode: string | undefined): string {
  const trimmed = (stockCode ?? '').trim();
  return trimmed ? normalizeStockCode(trimmed).toUpperCase() : '';
}

/** 任务完成后入队"选中意图"，待历史刷新返回时按 key 还原选中态 */
function queueCompletedTaskSelection(
  stockCode: string | undefined,
  selectedReport: AnalysisReport | null,
): void {
  const key = normalizeStockCodeKey(stockCode);
  if (key) {
    pendingCompletedTaskSelectionKeys.set(key, {
      manualSelectionSeq: manualSelectionRequestSeq,
      selectedReportId: selectedReport?.meta.id,
    });
  }
}

/** 消费已入队的"任务完成→选中意图"：在刷新后的历史列表中定位应自动选中的项，并清理队列 */
function consumeCompletedTaskSelection(items: HistoryItem[], selectedReport: AnalysisReport | null): HistoryItem | undefined {
  if (pendingCompletedTaskSelectionKeys.size === 0) {
    return undefined;
  }
  if (manualSelectionRequestId !== 0) {
    pendingCompletedTaskSelectionKeys.clear();
    return undefined;
  }

  if (selectedReport?.meta.reportType === 'market_review') {
    pendingCompletedTaskSelectionKeys.clear();
    return undefined;
  }

  if (selectedReport) {
    const selectedStockCode = normalizeStockCodeKey(selectedReport.meta.stockCode);
    const pendingSelectionIntent = selectedStockCode
      ? pendingCompletedTaskSelectionKeys.get(selectedStockCode)
      : undefined;
    if (!selectedStockCode || pendingSelectionIntent === undefined) {
      pendingCompletedTaskSelectionKeys.clear();
      return undefined;
    }
    if (pendingSelectionIntent.manualSelectionSeq !== manualSelectionRequestSeq) {
      pendingCompletedTaskSelectionKeys.clear();
      return undefined;
    }
    if (pendingSelectionIntent.selectedReportId !== selectedReport.meta.id) {
      pendingCompletedTaskSelectionKeys.clear();
      return undefined;
    }

    for (const key of Array.from(pendingCompletedTaskSelectionKeys.keys())) {
      if (key !== selectedStockCode) {
        pendingCompletedTaskSelectionKeys.delete(key);
      }
    }

    const latestItem = items.find(
      (item) =>
        item.reportType !== 'market_review' &&
        normalizeStockCodeKey(item.stockCode) === selectedStockCode,
    );
    if (latestItem) {
      pendingCompletedTaskSelectionKeys.delete(selectedStockCode);
    }
    return latestItem;
  }

  const latestItem = items.find((item) => {
    if (item.reportType === 'market_review') {
      return false;
    }
    const stockCode = normalizeStockCodeKey(item.stockCode);
    const pendingSelectionIntent = pendingCompletedTaskSelectionKeys.get(stockCode);
    return stockCode.length > 0 && pendingSelectionIntent?.manualSelectionSeq === manualSelectionRequestSeq;
  });
  if (latestItem) {
    pendingCompletedTaskSelectionKeys.clear();
  }
  return latestItem;
}

/** 判断报告创建日期是否落在指定区间（all/30d/90d）内 */
function isDateInHistoryRange(createdAt: string | undefined, range: StockHistoryRange): boolean {
  if (range === 'all') {
    return true;
  }
  if (!createdAt) {
    return false;
  }

  const reportDate = createdAt.slice(0, 10);
  const startDate = range === '30d' ? getRecentStartDate(30) : getRecentStartDate(90);
  const endDate = getTodayInShanghai();

  return reportDate >= startDate && reportDate <= endDate;
}

/** 将新选中的报告插入历史列表头部（若不在区间内或已存在则忽略），保证即时可见 */
function includeSelectedReport(
  items: HistoryItem[],
  report: AnalysisReport,
  range: StockHistoryRange,
): HistoryItem[] {
  const current = reportToHistoryItem(report);
  if (!current || !isDateInHistoryRange(current.createdAt, range) || items.some((item) => item.id === current.id)) {
    return items;
  }
  return [current, ...items];
}

/** 按 id 对历史列表去重，避免静默刷新/轮询对账时重复项 */
function dedupeHistoryItems(items: HistoryItem[]): HistoryItem[] {
  const seen = new Set<number>();
  return items.filter((item) => {
    if (seen.has(item.id)) {
      return false;
    }
    seen.add(item.id);
    return true;
  });
}

/** 重置个股历史走势相关状态（打开新抽屉或切换股票时调用） */
function resetStockHistoryState(set: (partial: Partial<StockPoolState>) => void) {
  set({
    stockHistoryItems: [],
    stockHistoryTotal: 0,
    stockHistoryPage: 1,
    stockHistoryHasMore: false,
    isLoadingStockHistory: false,
    isLoadingMoreStockHistory: false,
    stockHistoryError: null,
  });
}

/**
 * 拉取个股历史走势报告列表（内部方法）。
 * 根据 options.reset 决定首次加载或追加更多；通过 stockHistoryRequestSeq 丢弃过期响应。
 * 首次加载会把当前选中的报告插入列表头部（若在区间内）。
 */
async function fetchStockHistory(
  get: () => StockPoolState,
  set: (partial: Partial<StockPoolState>) => void,
  options: { reset?: boolean } = {},
): Promise<HistoryListResponse | null> {
  const { reset = true } = options;
  const state = get();
  const report = state.selectedReport;

  if (!report || !report.meta.stockCode) {
    resetStockHistoryState(set);
    set({
      isHistoryTrendOpen: false,
    });
    return null;
  }

  const page = reset ? 1 : state.stockHistoryPage + 1;
  const requestId = ++stockHistoryRequestSeq;
  set(
    reset
      ? { isLoadingStockHistory: true, isLoadingMoreStockHistory: false, stockHistoryError: null }
      : { isLoadingMoreStockHistory: true, stockHistoryError: null },
  );

  try {
    const response = await historyApi.getList(
      buildStockHistoryParams(report.meta.stockCode, page, state.stockHistoryFilters),
    );
    if (requestId !== stockHistoryRequestSeq) {
      return null;
    }

    const nextItems = reset
      ? dedupeHistoryItems(includeSelectedReport(response.items, report, state.stockHistoryFilters.range))
      : dedupeHistoryItems([...get().stockHistoryItems, ...response.items]);
    const nextTotal = Math.max(response.total, nextItems.length);
    set({
      stockHistoryItems: nextItems,
      stockHistoryTotal: nextTotal,
      stockHistoryPage: page,
      stockHistoryHasMore: nextItems.length < nextTotal,
    });
    return response;
  } catch (error) {
    if (requestId !== stockHistoryRequestSeq) {
      return null;
    }
    set({ stockHistoryError: getParsedApiError(error) });
    return null;
  } finally {
    if (requestId === stockHistoryRequestSeq) {
      set({
        isLoadingStockHistory: false,
        isLoadingMoreStockHistory: false,
      });
    }
  }
}

/**
 * 拉取普通历史报告列表（内部方法）。
 * 支持 reset（从头加载）/ silent（静默追加新项）/ autoSelectFirst（自动选首条）/
 * selectLatestForStockCode（为某股票自动选最新报告）。通过 historyRequestSeq 丢弃过期响应。
 */
async function fetchHistory(
  get: () => StockPoolState,
  set: (partial: Partial<StockPoolState>) => void,
  options: FetchHistoryOptions = {},
): Promise<HistoryListResponse | null> {
  const {
    autoSelectFirst = false,
    reset = true,
    silent = false,
    selectLatestForStockCode,
  } = options;
  const currentState = get();
  const page = reset ? 1 : currentState.currentPage + 1;
  if (reset) {
    queueCompletedTaskSelection(selectLatestForStockCode, currentState.selectedReport);
  }
  const requestId = ++historyRequestSeq;

  if (!silent) {
    set(
      reset
        ? { isLoadingHistory: true, isLoadingMore: false, currentPage: 1 }
        : { isLoadingMore: true },
    );
  }

  try {
    const response = await historyApi.getList(buildHistoryParams(page));
    if (requestId !== historyRequestSeq) {
      return null;
    }

    if (silent && reset) {
      const existingIds = new Set(get().historyItems.map((item) => item.id));
      const newItems = response.items.filter((item) => !existingIds.has(item.id));
      if (newItems.length > 0) {
        set({ historyItems: [...newItems, ...get().historyItems] });
      }
    } else if (reset) {
      set({
        historyItems: response.items,
        currentPage: 1,
      });
    } else {
      set({
        historyItems: [...get().historyItems, ...response.items],
        currentPage: page,
      });
    }

    if (!silent) {
      const totalLoaded = reset ? response.items.length : get().historyItems.length;
      set({ hasMore: totalLoaded < response.total });
    }

    const visibleIds = new Set(get().historyItems.map((item) => item.id));
    set({
      selectedHistoryIds: get().selectedHistoryIds.filter((id) => visibleIds.has(id)),
    });

    if (reset) {
      const latestCompletedTaskItem = consumeCompletedTaskSelection(response.items, get().selectedReport);
      const selectedReport = get().selectedReport;
      if (latestCompletedTaskItem && latestCompletedTaskItem.id !== selectedReport?.meta.id) {
        await get().selectHistoryItem(latestCompletedTaskItem.id, false);
      } else if (autoSelectFirst && response.items.length > 0 && !selectedReport) {
        await get().selectHistoryItem(response.items[0].id, false);
      }
    }

    return response;
  } catch (error) {
    if (requestId !== historyRequestSeq) {
      return null;
    }
    set({ error: getParsedApiError(error) });
    return null;
  } finally {
    if (requestId === historyRequestSeq) {
      set({
        isLoadingHistory: false,
        isLoadingMore: false,
      });
    }
  }
}

async function fetchMarketReviewHistory(
  get: () => StockPoolState,
  set: (partial: Partial<StockPoolState>) => void,
  options: FetchHistoryOptions = {},
): Promise<HistoryListResponse | null> {
  const { reset = true, silent = false } = options;
  const currentState = get();
  const page = reset ? 1 : currentState.marketReviewHistoryPage + 1;
  const requestId = ++marketReviewHistoryRequestSeq;

  if (!silent) {
    set(
      reset
        ? { isLoadingMarketReviewHistory: true, isLoadingMoreMarketReviewHistory: false, marketReviewHistoryPage: 1 }
        : { isLoadingMoreMarketReviewHistory: true },
    );
  }

  try {
    const response = await historyApi.getList(buildMarketReviewHistoryParams(page));
    if (requestId !== marketReviewHistoryRequestSeq) {
      return null;
    }

    if (silent && reset) {
      const existingIds = new Set(get().marketReviewHistoryItems.map((item) => item.id));
      const newItems = response.items.filter((item) => !existingIds.has(item.id));
      if (newItems.length > 0) {
        set({ marketReviewHistoryItems: [...newItems, ...get().marketReviewHistoryItems] });
      }
    } else if (reset) {
      set({
        marketReviewHistoryItems: response.items,
        marketReviewHistoryPage: 1,
      });
    } else {
      set({
        marketReviewHistoryItems: dedupeHistoryItems([...get().marketReviewHistoryItems, ...response.items]),
        marketReviewHistoryPage: page,
      });
    }

    const totalLoaded = reset ? response.items.length : get().marketReviewHistoryItems.length;
    set({ marketReviewHistoryHasMore: totalLoaded < response.total });

    const visibleIds = new Set(get().marketReviewHistoryItems.map((item) => item.id));
    set({
      selectedMarketReviewHistoryIds: get().selectedMarketReviewHistoryIds.filter((id) => visibleIds.has(id)),
    });

    return response;
  } catch (error) {
    if (requestId !== marketReviewHistoryRequestSeq) {
      return null;
    }
    set({ error: getParsedApiError(error) });
    return null;
  } finally {
    if (requestId === marketReviewHistoryRequestSeq) {
      set({
        isLoadingMarketReviewHistory: false,
        isLoadingMoreMarketReviewHistory: false,
      });
    }
  }
}

export const useStockPoolStore = create<StockPoolState>((set, get) => ({
  ...initialState,

  // ===== Actions 实现 =====

  /** 更新查询输入：切换为手动来源并清空输入错误/重复提示 */
  setQuery: (query) => {
    set({
      query,
      selectionSource: 'manual',
      inputError: undefined,
      duplicateError: null,
    });
  },

  /** 清空统一错误对象 */
  clearError: () => set({ error: null }),

  /** 清空内联提示（输入错误 + 重复提示） */
  clearInlineMessages: () => set({ inputError: undefined, duplicateError: null }),

  /** 设置是否开启分析完成通知 */
  setNotify: (notify) => set({ notify }),

  /** 打开 Markdown 报告抽屉 */
  openMarkdownDrawer: () => set({ markdownDrawerOpen: true }),

  /** 关闭 Markdown 报告抽屉 */
  closeMarkdownDrawer: () => set({ markdownDrawerOpen: false }),

  /**
   * 打开个股历史走势抽屉。
   * 仅当已选中含股票代码的报告时生效；打开后加载该股票的历史走势第一页。
   */
  openHistoryTrend: async () => {
    if (!get().selectedReport || !get().selectedReport?.meta.stockCode) {
      return;
    }
    set({ isHistoryTrendOpen: true });
    await fetchStockHistory(get, set, { reset: true });
  },

  /** 关闭个股历史走势抽屉：递增请求序号丢弃进行中响应并重置相关状态 */
  closeHistoryTrend: () => {
    stockHistoryRequestSeq += 1;
    resetStockHistoryState(set);
    set({
      isHistoryTrendOpen: false,
    });
  },

  /** 切换个股历史日期区间（30d/90d/all）后，若抽屉打开则重新加载 */
  setStockHistoryRange: async (range) => {
    set({
      stockHistoryFilters: {
        ...get().stockHistoryFilters,
        range,
      },
    });
    if (get().isHistoryTrendOpen) {
      await fetchStockHistory(get, set, { reset: true });
    }
  },

  /** 加载更多个股历史：抽屉未开/加载中/无更多时直接返回 */
  loadMoreStockHistory: async () => {
    const state = get();
    if (!state.isHistoryTrendOpen || state.isLoadingMoreStockHistory || !state.stockHistoryHasMore) {
      return;
    }
    await fetchStockHistory(get, set, { reset: false });
  },

  /** 首次加载普通历史并自动选中首条（页面初始化时调用） */
  loadInitialHistory: async () => {
    await fetchHistory(get, set, { autoSelectFirst: true, reset: true });
  },

  /** 刷新普通历史：silent 时静默追加，否则整页替换 */
  refreshHistory: async (silent = false) => {
    await fetchHistory(get, set, { reset: true, silent });
  },

  /**
   * 分析任务完成后刷新普通历史并自动选中该股票最新报告。
   * 大盘任务（market_review）不自动选中个股；通过 silent 追加避免列表跳动。
   */
  refreshHistoryForCompletedTask: async (task) => {
    await fetchHistory(get, set, {
      reset: true,
      silent: true,
      selectLatestForStockCode: task.reportType === 'market_review' ? undefined : task.stockCode,
    });
  },

  /** 加载更多普通历史：已加载完或无更多时直接返回 */
  loadMoreHistory: async () => {
    const state = get();
    if (state.isLoadingMore || !state.hasMore) {
      return;
    }
    await fetchHistory(get, set, { reset: false });
  },

  /** 加载大盘历史：从头加载第一页 */
  loadMarketReviewHistory: async () => {
    await fetchMarketReviewHistory(get, set, { reset: true });
  },

  /** 刷新大盘历史：silent 时静默追加，否则整页替换 */
  refreshMarketReviewHistory: async (silent = false) => {
    await fetchMarketReviewHistory(get, set, { reset: true, silent });
  },

  /** 加载更多大盘历史：已加载完或无更多时直接返回 */
  loadMoreMarketReviewHistory: async () => {
    const state = get();
    if (state.isLoadingMoreMarketReviewHistory || !state.marketReviewHistoryHasMore) {
      return;
    }
    await fetchMarketReviewHistory(get, set, { reset: false });
  },

  /**
   * 选中某条历史报告并加载详情。
   * isUserInitiated=true 标记用户主动点击（计入 manualSelection 计数器，用于区分自动选中场景）。
   * 选中后：若报告无股票代码（如大盘）则关闭个股走势抽屉；若抽屉已展开则同步刷新个股走势。
   * 通过 reportRequestSeq 丢弃过期响应；错误统一写入 error。
   */
  selectHistoryItem: async (recordId, isUserInitiated = true) => {
    const requestId = ++reportRequestSeq;
    if (isUserInitiated) {
      manualSelectionRequestSeq += 1;
      manualSelectionRequestId = requestId;
    }
    const shouldShowInitialLoading = !get().selectedReport;

    if (shouldShowInitialLoading) {
      set({ isLoadingReport: true });
    }

    try {
      const report = normalizeSelectedReport(await historyApi.getDetail(recordId));
      if (requestId !== reportRequestSeq) {
        return;
      }

      set({
        selectedReport: report,
        error: null,
        isLoadingReport: false,
      });

      if (!report.meta.stockCode) {
        stockHistoryRequestSeq += 1;
        resetStockHistoryState(set);
        set({ isHistoryTrendOpen: false });
        return;
      }

      if (get().isHistoryTrendOpen) {
        await fetchStockHistory(get, set, { reset: true });
      }
    } catch (error) {
      if (requestId !== reportRequestSeq) {
        return;
      }

      set({
        error: getParsedApiError(error),
        isLoadingReport: false,
      });
    } finally {
      if (isUserInitiated && manualSelectionRequestId === requestId) {
        manualSelectionRequestId = 0;
      }
    }
  },

  /** 切换单条历史勾选状态（用于批量删除选择） */
  toggleHistorySelection: (recordId) => {
    const selected = new Set(get().selectedHistoryIds);
    if (selected.has(recordId)) {
      selected.delete(recordId);
    } else {
      selected.add(recordId);
    }

    set({ selectedHistoryIds: Array.from(selected) });
  },

  /** 当前页全选/取消全选：若当前页已全部选中则取消可见项，否则并入可见项 */
  toggleSelectAllVisible: () => {
    const visibleIds = get().historyItems.map((item) => item.id);
    const selectedIds = get().selectedHistoryIds;
    const visibleSet = new Set(visibleIds);
    const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));

    set({
      selectedHistoryIds: allSelected
        ? selectedIds.filter((id) => !visibleSet.has(id))
        : Array.from(new Set([...selectedIds, ...visibleIds])),
    });
  },

  /**
   * 批量删除勾选的历史报告。
   * 删除后清空勾选、整页刷新历史；若当前选中的报告被删除，则自动选中新列表首条，
   * 否则关闭个股走势抽屉并清空选中报告。
   */
  deleteSelectedHistory: async () => {
    const state = get();
    const recordIds = Array.from(new Set(state.selectedHistoryIds));
    if (recordIds.length === 0 || state.isDeletingHistory) {
      return;
    }

    set({ isDeletingHistory: true });
    try {
      await historyApi.deleteRecords(recordIds);

      const deletedIds = new Set(recordIds);
      const selectedWasDeleted = state.selectedReport?.meta.id !== undefined
        && deletedIds.has(state.selectedReport.meta.id);

      set({ selectedHistoryIds: [] });

      const freshPage = await fetchHistory(get, set, { reset: true });

      if (selectedWasDeleted) {
        const nextItem = freshPage?.items?.[0];
        if (nextItem) {
          await get().selectHistoryItem(nextItem.id, false);
        } else {
          stockHistoryRequestSeq += 1;
          resetStockHistoryState(set);
          set({
            isHistoryTrendOpen: false,
            selectedReport: null,
          });
        }
      }
    } catch (error) {
      set({ error: getParsedApiError(error) });
    } finally {
      set({ isDeletingHistory: false });
    }
  },

  /** 切换单条大盘历史勾选状态（用于批量删除选择） */
  toggleMarketReviewHistorySelection: (recordId) => {
    const selected = new Set(get().selectedMarketReviewHistoryIds);
    if (selected.has(recordId)) {
      selected.delete(recordId);
    } else {
      selected.add(recordId);
    }

    set({ selectedMarketReviewHistoryIds: Array.from(selected) });
  },

  /** 大盘历史当前页全选/取消全选 */
  toggleSelectAllVisibleMarketReviewHistory: () => {
    const visibleIds = get().marketReviewHistoryItems.map((item) => item.id);
    const selectedIds = get().selectedMarketReviewHistoryIds;
    const visibleSet = new Set(visibleIds);
    const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));

    set({
      selectedMarketReviewHistoryIds: allSelected
        ? selectedIds.filter((id) => !visibleSet.has(id))
        : Array.from(new Set([...selectedIds, ...visibleIds])),
    });
  },

  /**
   * 批量删除勾选的大盘历史报告。
   * 删除后清空勾选、整页刷新大盘历史；若当前选中的大盘报告被删除，则自动选中新列表首条，
   * 否则关闭个股走势抽屉并清空选中报告。
   */
  deleteSelectedMarketReviewHistory: async () => {
    const state = get();
    const recordIds = Array.from(new Set(state.selectedMarketReviewHistoryIds));
    if (recordIds.length === 0 || state.isDeletingMarketReviewHistory) {
      return;
    }

    set({ isDeletingMarketReviewHistory: true });
    try {
      await historyApi.deleteRecords(recordIds);

      const deletedIds = new Set(recordIds);
      const selectedWasDeleted = state.selectedReport?.meta.id !== undefined
        && state.selectedReport.meta.reportType === 'market_review'
        && deletedIds.has(state.selectedReport.meta.id);

      set({ selectedMarketReviewHistoryIds: [] });

      const freshPage = await fetchMarketReviewHistory(get, set, { reset: true });

      if (selectedWasDeleted) {
        const nextItem = freshPage?.items?.[0];
        if (nextItem) {
          await get().selectHistoryItem(nextItem.id, false);
        } else {
          set({ selectedReport: null });
        }
      }
    } catch (error) {
      set({ error: getParsedApiError(error) });
    } finally {
      set({ isDeletingMarketReviewHistory: false });
    }
  },

  /**
   * 提交股票分析任务（异步）。
   * 流程：输入校验（空/明显非法/股票代码格式）→ 归一化股票代码 → 调分析接口 →
   * 成功后清空输入框、刷新进行中任务、加载并自动选中该股票最新历史、清理过期任务选中意图。
   * 若检测到重复任务（DuplicateTaskError），显示 duplicateError 提示。
   */
  submitAnalysis: async (options) => {
    const state = get();
    const rawStockCode = options?.stockCode ?? state.query;
    const stockCodeInput = rawStockCode.trim();
    const stockName = options?.stockName;
    const selectionSource = options?.selectionSource ?? state.selectionSource;
    const originalQuery = (options?.originalQuery ?? state.query).trim();
    const notify = options?.notify ?? state.notify;
    const forceRefresh = options?.forceRefresh ?? false;
    const skills = options?.skills;

    if (!stockCodeInput) {
      set({ inputError: '请输入股票代码', duplicateError: null });
      return;
    }

    if (selectionSource !== 'autocomplete' && isObviouslyInvalidStockQuery(stockCodeInput)) {
      set({ inputError: '请输入有效的股票代码或股票名称', duplicateError: null });
      return;
    }

    let normalizedStockCode = stockCodeInput;
    if (selectionSource === 'autocomplete' || looksLikeStockCode(stockCodeInput)) {
      const { valid, message, normalized } = validateStockCode(stockCodeInput);
      if (!valid) {
        set({ inputError: message, duplicateError: null });
        return;
      }
      normalizedStockCode = normalized;
    }

    set({
      inputError: undefined,
      duplicateError: null,
      error: null,
      isAnalyzing: true,
    });

    const requestId = ++analyzeRequestSeq;
    try {
      await analysisApi.analyzeAsync({
        stockCode: normalizedStockCode,
        reportType: 'detailed',
        stockName,
        originalQuery: originalQuery || stockCodeInput,
        selectionSource,
        notify,
        forceRefresh,
        skills,
        ...(options?.reportLanguage !== undefined && { reportLanguage: options.reportLanguage }),
      });

      if (requestId !== analyzeRequestSeq) {
        return;
      }

      set({
        query: '',
        selectionSource: 'manual',
      });
    } catch (error) {
      if (requestId !== analyzeRequestSeq) {
        return;
      }

      if (error instanceof DuplicateTaskError) {
        set({
          duplicateError: `股票 ${error.stockCode} 正在分析中，请等待完成`,
        });
        return;
      }

      set({ error: getParsedApiError(error) });
    } finally {
      if (requestId === analyzeRequestSeq) {
        set({ isAnalyzing: false });
      }
    }
  },

  // 任务事件同步：已忽略的任务直接跳过，避免误弹通知/自动选中
  syncTaskCreated: (task) => {
    if (dismissedTaskIds.has(task.taskId)) {
      return;
    }
    if (get().activeTasks.some((item) => item.taskId === task.taskId)) {
      return;
    }
    activeTaskLocalRevision += 1;
    set({ activeTasks: [...get().activeTasks, task] });
  },

  /** 同步任务更新：原地替换列表中对应任务，计入本地修订计数 */
  syncTaskUpdated: (task) => {
    if (dismissedTaskIds.has(task.taskId)) {
      return;
    }
    const nextTasks = [...get().activeTasks];
    const index = nextTasks.findIndex((item) => item.taskId === task.taskId);
    if (index >= 0) {
      nextTasks[index] = task;
      activeTaskLocalRevision += 1;
      set({ activeTasks: nextTasks });
    }
  },

  /** 同步任务失败：更新任务态并写入统一错误，供页面提示 */
  syncTaskFailed: (task) => {
    get().syncTaskUpdated(task);
    set({ error: getParsedApiError(task.error || '分析失败') });
  },

  /**
   * 轮询对账进行中任务列表。
   * 拉取远端 pending/processing/cancel_requested 任务，与本地 activeTasks 合并；
   * 若远端快照完整且与请求期间无本地改动（localRevision 一致），可裁剪掉本地多余项，
   * 避免已完成任务残留。通过 activeTaskRequestSeq 丢弃过期响应。
   */
  refreshActiveTasks: async () => {
    const requestId = ++activeTaskRequestSeq;
    const localRevisionAtRequest = activeTaskLocalRevision;
    try {
      const response = await analysisApi.getTasks({
        status: 'pending,processing,cancel_requested',
        limit: 100,
      });
      if (requestId !== activeTaskRequestSeq) {
        return;
      }

      const remoteTasks = response.tasks.filter(
        (task) => !dismissedTaskIds.has(task.taskId),
      );
      const remoteTaskIds = new Set(remoteTasks.map((task) => task.taskId));
      const remoteTaskById = new Map(remoteTasks.map((task) => [task.taskId, task]));
      const activeTaskCount = response.pending
        + response.processing
        + response.tasks.filter((task) => task.status === 'cancel_requested').length;
      const isCompleteSnapshot = response.tasks.length === activeTaskCount;
      const canPruneLocalTasks = isCompleteSnapshot && activeTaskLocalRevision === localRevisionAtRequest;

      const currentTasks = get().activeTasks;
      const nextTasks = currentTasks
        .filter((task) => !dismissedTaskIds.has(task.taskId))
        .filter((task) => !canPruneLocalTasks || remoteTaskIds.has(task.taskId))
        .map((task) => remoteTaskById.get(task.taskId) ?? task);

      const localTaskIds = new Set(nextTasks.map((task) => task.taskId));
      for (const task of remoteTasks) {
        if (!localTaskIds.has(task.taskId)) {
          nextTasks.push(task);
        }
      }

      const hasActiveTaskChanges = nextTasks.length !== currentTasks.length
        || nextTasks.some((task, index) => task !== currentTasks[index]);
      if (hasActiveTaskChanges) {
        activeTaskLocalRevision += 1;
        set({ activeTasks: nextTasks });
      }
    } catch {
      // Keep the current task panel when reconciliation cannot reach the API.
    }
  },

  /** 移除任务：标记为已忽略并移出列表（即用户手动 dismiss） */
  removeTask: (taskId) => {
    dismissedTaskIds.add(taskId);
    const currentTasks = get().activeTasks;
    const nextTasks = currentTasks.filter((task) => task.taskId !== taskId);
    if (nextTasks.length !== currentTasks.length) {
      activeTaskLocalRevision += 1;
    }
    set({ activeTasks: nextTasks });
  },

  /** 重置整个首页工作台：递增所有请求序号以丢弃进行中的响应，并清空全部本地决策状态 */
  resetDashboardState: () => {
    historyRequestSeq += 1;
    marketReviewHistoryRequestSeq += 1;
    stockHistoryRequestSeq += 1;
    reportRequestSeq = 0;
    analyzeRequestSeq = 0;
    manualSelectionRequestSeq = 0;
    manualSelectionRequestId = 0;
    stockBarRequestSeq += 1;
    activeTaskRequestSeq += 1;
    activeTaskLocalRevision += 1;
    dismissedTaskIds.clear();
    pendingCompletedTaskSelectionKeys.clear();
    set({ ...initialState });
  },

  /** 加载股票条（最近 90 天个股热度/涨跌）；通过 stockBarRequestSeq 丢弃过期响应 */
  loadStockBar: async () => {
    const state = get();
    if (state.isLoadingStockBar) return;
    const requestSeq = ++stockBarRequestSeq;
    set({ isLoadingStockBar: true });
    try {
      const response = await historyApi.getStockBarList({
        startDate: getRecentStartDate(90),
        endDate: getTodayInShanghai(),
      });
      if (requestSeq !== stockBarRequestSeq) {
        return;
      }
      set({ stockBarItems: response.items, stockBarRefreshFailed: false });
    } catch {
      if (requestSeq !== stockBarRequestSeq) {
        return;
      }
      set({ stockBarRefreshFailed: true });
    } finally {
      if (requestSeq === stockBarRequestSeq) {
        set({ isLoadingStockBar: false });
      }
    }
  },

  /** 刷新股票条：与 loadStockBar 同接口，用于手动刷新/定时刷新 */
  refreshStockBar: async () => {
    const requestSeq = ++stockBarRequestSeq;
    try {
      const response = await historyApi.getStockBarList({
        startDate: getRecentStartDate(90),
        endDate: getTodayInShanghai(),
      });
      if (requestSeq !== stockBarRequestSeq) {
        return;
      }
      set({ stockBarItems: response.items, stockBarRefreshFailed: false });
    } catch {
      if (requestSeq !== stockBarRequestSeq) {
        return;
      }
      set({ stockBarRefreshFailed: true });
    } finally {
      if (requestSeq === stockBarRequestSeq) {
        set({ isLoadingStockBar: false });
      }
    }
  },
}));
