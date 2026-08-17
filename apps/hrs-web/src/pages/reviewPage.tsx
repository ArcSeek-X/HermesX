/**
 * @file reviewPage.tsx
 * @description 系统首页，集成股票分析、大盘回顾、自选股管理、历史记录、任务面板等核心功能
 * @module pages
 */
import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BarChart3, Check, SlidersHorizontal, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getParsedApiError, type ParsedApiError } from '../api/error';
import { analysisApi, DuplicateTaskError } from '../api/analysis';
import { historyApi } from '../api/history';
import { agentApi, type SkillInfo } from '../api/agent';
import { systemConfigApi } from '../api/systemConfig';
import { ApiErrorAlert, Button, Drawer, EmptyState, InlineAlert } from '../components';
import { DashboardStateBlock } from '../components/dashboard';
import { StockAutocomplete } from '../components/StockAutocomplete';
import { StockHistoryTrendDrawer } from '../components/history';
import { ReportMarkdownDrawer } from '../components/report/ReportMarkdownDrawer';
import { MarketReviewReportView } from '../components/report/MarketReviewReportView';
import { MarketReviewRegionSelector } from '../components/market-review/MarketReviewRegionSelector';
import { ReportSummary } from '../components/report/ReportSummary';
import { RunFlowPanel } from '../components/run-flow';
import { TaskPanel } from '../components/tasks';
import {
  HomeStockWorkspace,
  type HomeWatchlistRow,
  type HomeWorkspaceTab,
  type WatchlistAnalyzeMode,
} from '../components/watchlist/HomeStockWorkspace';
import { useDashboardLifecycle, useHomeDashboardState } from '../hooks';
import { useWatchlist } from '../hooks/useWatchlist';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import type { SetupStatusResponse } from '../types/systemConfig';
import { normalizeReportLanguage } from '../utils/reportLanguage';
import type {
  AnalyzeAsyncResponse,
  HistoryItem,
  MarketReviewPayload,
  MarketReviewRegion,
  StockBarItem,
  TaskInfo,
} from '../types/analysis';
import type { RunFlowSnapshotSource } from '../types/runFlow';
import { getTodayInShanghai } from '../utils/format';
import { normalizeStockCode } from '../utils/stockCode';

/** 大盘回顾通知类型：包含变体（成功/警告/危险）、标题和消息 */
type MarketReviewNotice = {
  variant: 'success' | 'warning' | 'danger';
  title: string;
  message: string;
} | null;

/** 运行流程抽屉状态：关闭或打开时携带来源与标题 */
type RunFlowDrawerState =
  | { open: false }
  | { open: true; source: RunFlowSnapshotSource; title: string };

/** 股票分析路由导航状态：从其他页面跳转时携带的股票信息 */
type StockAnalysisNavigationState = {
  stockCode?: string;
  stockName?: string;
  autoAnalyze?: boolean;
  selectionSource?: string;
};

/** 重复任务提示横幅自动消失时间（毫秒） */
const DUPLICATE_BANNER_AUTO_DISMISS_MS = 5000;
/** 批量分析时的分块大小，避免单次请求过大 */
const BATCH_ANALYSIS_CHUNK_SIZE = 50;
/** 今日分析列表每页加载条数 */
const TODAY_ANALYSIS_PAGE_SIZE = 100;
/** 服务端本地日期时间格式正则：匹配 YYYY-MM-DD[T\s]HH:mm 格式 */
const SERVER_LOCAL_DATE_TIME_PATTERN = /^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/;

/** 批量分析结果状态：包含变体和消息 */
type BatchAnalyzeStatus = {
  variant: 'success' | 'warning' | 'danger';
  message: string;
} | null;

/** 自选股历史记录查找状态：记录签名、已查到的 key 集合和失败的 key 集合 */
type WatchlistHistoryLookupState = {
  signature: string;
  settledKeys: Set<string>;
  failedKeys: Set<string>;
};

/**
 * 将时间字符串转换为上海时区（UTC+8）的日期键（YYYY-MM-DD 格式）
 * 用于判断分析记录是否属于"今日"，统一以上海时区为基准
 * @param value - 时间字符串，可能为 ISO 格式或服务端本地时间
 * @returns 上海时区日期键，如 "2024-01-15"；解析失败返回空字符串
 */
function getShanghaiDateKey(value?: string | null): string {
  if (!value) return '';
  const trimmed = value.trim();
  // 服务端本地时间格式补全时区偏移为 +08:00
  const normalized = SERVER_LOCAL_DATE_TIME_PATTERN.test(trimmed)
    ? `${trimmed.replace(' ', 'T')}+08:00`
    : trimmed;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(date);
}

/**
 * 将时间字符串转换为时间戳（毫秒），用于排序比较
 * @param value - 时间字符串
 * @returns 时间戳数值；解析失败返回 0
 */
function getShanghaiTimeValue(value?: string | null): number {
  if (!value) return 0;
  const trimmed = value.trim();
  const normalized = SERVER_LOCAL_DATE_TIME_PATTERN.test(trimmed)
    ? `${trimmed.replace(' ', 'T')}+08:00`
    : trimmed;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

/**
 * 将日期键偏移指定天数，返回新的日期键
 * @param dateKey - 原始日期键（YYYY-MM-DD）
 * @param days - 偏移天数，正数为未来，负数为过去
 * @returns 偏移后的日期键
 */
function shiftDateKey(dateKey: string, days: number): string {
  const date = new Date(`${dateKey}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/**
 * 将股票代码标准化为大写归一化形式，作为 Map 的 key 使用
 * @param code - 原始股票代码
 * @returns 标准化后的大写股票代码；空值返回空字符串
 */
function getStockCodeKey(code?: string | null): string {
  const trimmed = (code ?? '').trim();
  return trimmed ? normalizeStockCode(trimmed).toUpperCase() : '';
}

/**
 * 将股票代码数组分块，每块大小为 BATCH_ANALYSIS_CHUNK_SIZE
 * 用于批量分析时分批发送请求，避免单次请求过大
 * @param codes - 股票代码数组
 * @returns 分块后的二维数组
 */
function chunkStockCodes(codes: string[]): string[][] {
  const chunks: string[][] = [];
  for (let index = 0; index < codes.length; index += BATCH_ANALYSIS_CHUNK_SIZE) {
    chunks.push(codes.slice(index, index + BATCH_ANALYSIS_CHUNK_SIZE));
  }
  return chunks;
}

/**
 * 统计批量分析响应中已接受和重复的任务数量
 * @param result - 异步分析响应
 * @returns 包含 accepted（已接受数）和 duplicates（重复数）的对象
 */
function countBatchAccepted(result: AnalyzeAsyncResponse): { accepted: number; duplicates: number } {
  if ('accepted' in result) {
    return {
      accepted: result.accepted.length,
      duplicates: result.duplicates.length,
    };
  }
  return { accepted: 1, duplicates: 0 };
}

/**
 * 将历史记录项转换为股票条目项，用于在侧边栏历史列表中展示
 * @param item - 历史记录项
 * @returns 转换后的股票条目项
 */
function toStockBarItemFromHistoryItem(item: HistoryItem): StockBarItem {
  return {
    id: item.id,
    stockCode: item.stockCode,
    stockName: item.stockName,
    reportType: item.reportType,
    sentimentScore: item.sentimentScore,
    operationAdvice: item.operationAdvice,
    action: item.action ?? null,
    actionLabel: item.actionLabel ?? null,
    analysisCount: 0,
    lastAnalysisTime: item.createdAt,
    modelUsed: item.modelUsed,
    marketPhaseSummary: item.marketPhaseSummary ?? null,
  };
}

/**
 * 获取指定日期（上海时区）的所有个股分析记录（排除大盘回顾）
 * 分页加载服务端数据，查询前后各一天以覆盖时区边界，然后按上海日期精确过滤
 * @param dateKey - 上海时区日期键（YYYY-MM-DD）
 * @returns 转换为 StockBarItem 数组的今日分析记录
 */
async function getTodayAnalysisItems(dateKey: string): Promise<StockBarItem[]> {
  const items: StockBarItem[] = [];
  let loadedRecordCount = 0;
  let page = 1;

  while (true) {
    const response = await historyApi.getList({
      // History dates are filtered in the server's local timezone. Query the
      // adjacent dates too, then apply the exact Shanghai-day filter below.
      startDate: shiftDateKey(dateKey, -1),
      endDate: shiftDateKey(dateKey, 1),
      page,
      limit: TODAY_ANALYSIS_PAGE_SIZE,
    });

    loadedRecordCount += response.items.length;
    for (const item of response.items) {
      if (item.stockCode === 'MARKET' || item.reportType === 'market_review') {
        continue;
      }
      items.push(toStockBarItemFromHistoryItem(item));
    }

    if (
      response.items.length === 0
      || response.items.length < TODAY_ANALYSIS_PAGE_SIZE
      || loadedRecordCount >= response.total
    ) {
      break;
    }

    page += 1;
  }

  return items;
}

/**
 * 首页组件
 * 系统主界面，集成以下核心功能：
 * - 股票分析：输入股票代码发起分析，支持自动补全和策略选择
 * - 大盘回顾：触发并轮询大盘回顾任务，展示结果报告
 * - 自选股管理：查看自选股列表、今日分析状态、批量分析
 * - 历史记录：查看历史分析报告，支持趋势图、Markdown 全文
 * - 任务面板：展示当前活跃的分析任务
 * @returns 首页的 JSX 元素
 */
const HomePage: React.FC = () => {
  /** 路由导航函数 */
  const navigate = useNavigate();
  /** 当前路由位置信息，用于读取导航状态 */
  const location = useLocation();
  /** UI 语言和翻译函数 */
  const { language: uiLanguage, t } = useUiLanguage();
  /** 移动端侧边栏是否展开 */
  const [sidebarOpen, setSidebarOpen] = useState(false);
  /** 大盘回顾任务是否正在提交中 */
  const [isSubmittingMarketReview, setIsSubmittingMarketReview] = useState(false);
  /** 大盘回顾通知信息（成功/警告/危险） */
  const [marketReviewNotice, setMarketReviewNotice] = useState<MarketReviewNotice>(null);
  /** 大盘回顾 API 错误信息 */
  const [marketReviewError, setMarketReviewError] = useState<ParsedApiError | null>(null);
  /** 大盘回顾报告 Markdown 内容 */
  const [marketReviewReport, setMarketReviewReport] = useState<string | null>(null);
  /** 大盘回顾结构化数据载荷 */
  const [marketReviewPayload, setMarketReviewPayload] = useState<MarketReviewPayload | null>(null);
  /** 大盘回顾地区覆盖设置（覆盖默认地区） */
  const [marketReviewRegionOverride, setMarketReviewRegionOverride] = useState<MarketReviewRegion[] | undefined>();
  /** 可用的分析策略（技能）列表 */
  const [analysisSkills, setAnalysisSkills] = useState<SkillInfo[]>([]);
  /** 当前选中的策略 ID */
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  /** 策略选择菜单是否展开 */
  const [strategyMenuOpen, setStrategyMenuOpen] = useState(false);
  /** 运行流程抽屉状态 */
  const [runFlowDrawer, setRunFlowDrawer] = useState<RunFlowDrawerState>({ open: false });
  /** 重复任务提示横幅是否可见 */
  const [duplicateBannerVisible, setDuplicateBannerVisible] = useState(false);
  /** 侧边栏工作区当前标签页：history（历史）/ today（今日）/ watchlist（自选股） */
  const [sidebarWorkspaceTab, setSidebarWorkspaceTab] = useState<HomeWorkspaceTab>('history');
  /** 是否正在批量分析自选股 */
  const [isBatchAnalyzingWatchlist, setIsBatchAnalyzingWatchlist] = useState(false);
  /** 批量分析结果状态 */
  const [batchAnalyzeStatus, setBatchAnalyzeStatus] = useState<BatchAnalyzeStatus>(null);
  /** 自选股历史记录查找结果（按标准化代码索引） */
  const [watchlistHistoryItemsByCode, setWatchlistHistoryItemsByCode] = useState<Map<string, StockBarItem>>(new Map());
  /** 自选股历史记录查找状态：签名、已处理 key、失败 key */
  const [watchlistHistoryLookupState, setWatchlistHistoryLookupState] = useState<WatchlistHistoryLookupState>({
    signature: '',
    settledKeys: new Set(),
    failedKeys: new Set(),
  });
  /** 今日分析历史记录列表 */
  const [todayHistoryItems, setTodayHistoryItems] = useState<StockBarItem[]>([]);
  /** 是否正在加载今日分析记录 */
  const [isLoadingTodayAnalysisItems, setIsLoadingTodayAnalysisItems] = useState(false);
  /** 今日分析记录加载是否失败 */
  const [todayAnalysisLoadFailed, setTodayAnalysisLoadFailed] = useState(false);
  /** 今日分析刷新版本号，递增触发重新加载 */
  const [todayAnalysisRefreshVersion, setTodayAnalysisRefreshVersion] = useState(0);
  /** 股票条目初始加载是否已完成 */
  const [isStockBarInitialLoadSettled, setIsStockBarInitialLoadSettled] = useState(false);
  /** 重复任务提示横幅自动消失的定时器引用 */
  const duplicateBannerTimer = useRef<number | null>(null);
  /** 大盘回顾轮询定时器引用 */
  const marketReviewPollTimer = useRef<number | null>(null);
  /** 股票条目加载是否已启动的标记，用于区分首次加载和后续加载 */
  const stockBarLoadStartedRef = useRef(false);
  /** 仪表板滚动容器引用，用于控制滚动位置 */
  const dashboardScrollRef = useRef<HTMLElement | null>(null);
  /** 策略选择菜单容器引用，用于点击外部关闭菜单 */
  const strategyMenuRef = useRef<HTMLDivElement | null>(null);
  /** 策略选择触发按钮引用，用于关闭菜单后恢复焦点 */
  const strategyButtonRef = useRef<HTMLButtonElement | null>(null);
  /** 策略菜单项按钮引用数组，用于键盘导航聚焦 */
  const strategyItemRefs = useRef<Array<HTMLButtonElement | null>>([]);
  /** 策略菜单打开时初始聚焦项索引，用于键盘交互 */
  const strategyInitialFocusIndexRef = useRef<number | null>(null);

  /** 停止大盘回顾任务轮询，清除定时器 */
  const stopMarketReviewPolling = useCallback(() => {
    if (marketReviewPollTimer.current !== null) {
      window.clearInterval(marketReviewPollTimer.current);
      marketReviewPollTimer.current = null;
    }
  }, []);

  /** 将仪表板滚动位置滚动到顶部，用于大盘回顾反馈信息展示后引导用户查看 */
  const scrollMarketReviewFeedbackIntoView = useCallback(() => {
    const scrollContainer = dashboardScrollRef.current;
    if (!scrollContainer) {
      return;
    }

    if (typeof scrollContainer.scrollTo === 'function') {
      scrollContainer.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    scrollContainer.scrollTop = 0;
  }, []);

  // 组件卸载时停止大盘回顾轮询
  useEffect(() => stopMarketReviewPolling, [stopMarketReviewPolling]);
  /** 系统初始化状态（配置检查项是否完整） */
  const [setupStatus, setSetupStatus] = useState<SetupStatusResponse | null>(null);

  /**
   * 首页仪表板状态 Hook：统一管理股票分析、历史记录、任务同步、报告加载等核心状态与操作
   * 解构出的属性按职责分组：
   * - 搜索/输入：query（搜索关键词）、inputError（输入校验错误）、duplicateError（重复任务错误）
   * - 通用错误：error（全局错误信息）、clearError（清除错误）
   * - 分析状态：isAnalyzing（是否分析中）、submitAnalysis（提交分析任务）
   * - 报告展示：selectedReport（当前选中的报告）、isLoadingReport（报告加载中）
   * - 历史趋势：isHistoryTrendOpen（趋势抽屉开关）、openHistoryTrend/closeHistoryTrend
   * - 大盘回顾历史：marketReviewHistoryItems、loadMarketReviewHistory、refreshMarketReviewHistory
   * - 个股历史：stockHistoryItems/stockHistoryTotal/stockHistoryHasMore 及分页加载方法
   * - 活跃任务：activeTasks 及任务同步方法（syncTaskCreated/Updated/Failed、refreshActiveTasks、removeTask）
   * - Markdown 抽屉：markdownDrawerOpen、openMarkdownDrawer、closeMarkdownDrawer
   * - 股票条目（侧边栏列表）：stockBarItems、isLoadingStockBar、stockBarRefreshFailed、loadStockBar/refreshStockBar
   * - 通知开关：notify、setNotify
   */
  const {
    query,
    inputError,
    duplicateError,
    error,
    isAnalyzing,
    selectedReport,
    isLoadingReport,
    isHistoryTrendOpen,
    marketReviewHistoryItems,
    stockHistoryItems,
    stockHistoryTotal,
    stockHistoryHasMore,
    isLoadingStockHistory,
    isLoadingMoreStockHistory,
    stockHistoryError,
    stockHistoryFilters,
    activeTasks,
    markdownDrawerOpen,
    setQuery,
    clearError,
    loadInitialHistory,
    refreshHistory,
    refreshHistoryForCompletedTask,
    loadMarketReviewHistory,
    refreshMarketReviewHistory,
    selectHistoryItem,
    submitAnalysis,
    notify,
    setNotify,
    syncTaskCreated,
    syncTaskUpdated,
    syncTaskFailed,
    refreshActiveTasks,
    removeTask,
    openMarkdownDrawer,
    closeMarkdownDrawer,
    openHistoryTrend,
    closeHistoryTrend,
    setStockHistoryRange,
    loadMoreStockHistory,
    stockBarItems,
    isLoadingStockBar,
    stockBarRefreshFailed,
    loadStockBar,
    refreshStockBar,
  } = useHomeDashboardState();

  /** 清除重复任务提示横幅定时器 */
  const clearDuplicateBannerTimer = useCallback(() => {
    if (duplicateBannerTimer.current !== null) {
      window.clearTimeout(duplicateBannerTimer.current);
      duplicateBannerTimer.current = null;
    }
  }, []);

  /** 手动关闭重复任务提示横幅 */
  const dismissDuplicateBanner = useCallback(() => {
    clearDuplicateBannerTimer();
    setDuplicateBannerVisible(false);
  }, [clearDuplicateBannerTimer]);

  /**
   * 监听重复任务错误变化：
   * - 无错误时隐藏横幅
   * - 有错误时显示横幅并在设定时间后自动消失
   */
  useEffect(() => {
    if (!duplicateError) {
      clearDuplicateBannerTimer();
      setDuplicateBannerVisible(false);
      return undefined;
    }

    setDuplicateBannerVisible(true);
    clearDuplicateBannerTimer();
    duplicateBannerTimer.current = window.setTimeout(() => {
      duplicateBannerTimer.current = null;
      setDuplicateBannerVisible(false);
    }, DUPLICATE_BANNER_AUTO_DISMISS_MS);

    return clearDuplicateBannerTimer;
  }, [clearDuplicateBannerTimer, duplicateError]);

  // 设置页面标题
  useEffect(() => {
    document.title = t('home.pageTitle');
  }, [t]);

  /**
   * 加载系统初始化状态，检查配置是否完整
   * 组件挂载时执行一次，失败时静默处理
   */
  useEffect(() => {
    let active = true;
    systemConfigApi.getSetupStatus()
      .then((status) => {
        if (active) {
          setSetupStatus(status);
        }
      })
      .catch(() => {
        if (active) {
          setSetupStatus(null);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  /**
   * 加载可用的分析策略（技能）列表
   * 组件挂载时执行一次，失败时置为空数组
   */
  useEffect(() => {
    let active = true;
    agentApi.getSkills()
      .then((response) => {
        if (active) {
          setAnalysisSkills(response.skills);
        }
      })
      .catch(() => {
        if (active) {
          setAnalysisSkills([]);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  /**
   * 策略菜单展开时监听全局鼠标按下事件
   * 点击菜单外部时关闭菜单
   */
  useEffect(() => {
    if (!strategyMenuOpen) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target;
      if (target instanceof Node && strategyMenuRef.current?.contains(target)) {
        return;
      }
      setStrategyMenuOpen(false);
    };

    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [strategyMenuOpen]);

  /**
   * 当策略列表变化时，如果当前选中的策略已不存在于列表中，则重置为默认策略
   */
  useEffect(() => {
    if (selectedStrategyId && !analysisSkills.some((skill) => skill.id === selectedStrategyId)) {
      setSelectedStrategyId('');
    }
  }, [analysisSkills, selectedStrategyId]);

  /** 当前选中报告的语言（归一化后） */
  const reportLanguage = normalizeReportLanguage(selectedReport?.meta.reportLanguage);
  /** 实时大盘回顾报告的语言（归一化后） */
  const liveMarketReviewLanguage = normalizeReportLanguage(marketReviewPayload?.language);
  /** 当前选中报告是否为大盘回顾类型 */
  const isMarketReviewHistoryReport = selectedReport?.meta.reportType === 'market_review';
  /** 当前选中报告是否无法查看历史趋势（无股票代码） */
  const isHistoryTrendUnavailable = !selectedReport || !selectedReport.meta.stockCode;

  /**
   * 当历史趋势不可用但趋势抽屉已打开时，自动关闭趋势抽屉
   */
  useEffect(() => {
    if (!isHistoryTrendUnavailable || !isHistoryTrendOpen) {
      return;
    }
    closeHistoryTrend();
  }, [closeHistoryTrend, isHistoryTrendOpen, isHistoryTrendUnavailable]);

  /** 当前选中的策略对象 */
  const selectedStrategy = useMemo(
    () => analysisSkills.find((skill) => skill.id === selectedStrategyId),
    [analysisSkills, selectedStrategyId],
  );
  /** 当前选中的分析策略 ID 数组（未选择时为 undefined） */
  const selectedAnalysisSkills = useMemo(
    () => (selectedStrategyId ? [selectedStrategyId] : undefined),
    [selectedStrategyId],
  );
  /** 策略选项列表：默认策略 + 所有可用策略 */
  const strategyOptions = useMemo(
    () => [
      { id: '', name: t('home.defaultStrategyName'), description: t('home.defaultStrategyDescription') },
      ...analysisSkills.map((skill) => ({
        id: skill.id,
        name: skill.name,
        description: skill.description,
      })),
    ],
    [analysisSkills, t],
  );
  /** 关闭策略菜单，可选择是否将焦点恢复到触发按钮 */
  const closeStrategyMenu = useCallback((restoreFocus = false) => {
    setStrategyMenuOpen(false);
    if (restoreFocus) {
      strategyButtonRef.current?.focus();
    }
  }, []);
  /** 选择策略并关闭菜单 */
  const selectStrategy = useCallback((strategyId: string) => {
    setSelectedStrategyId(strategyId);
    setStrategyMenuOpen(false);
  }, []);
  /** 聚焦策略菜单中指定索引的项（循环导航） */
  const focusStrategyItem = useCallback((index: number) => {
    const itemCount = strategyOptions.length;
    if (itemCount === 0) {
      return;
    }
    const nextIndex = (index + itemCount) % itemCount;
    strategyItemRefs.current[nextIndex]?.focus();
  }, [strategyOptions.length]);
  /** 获取当前选中策略在选项列表中的索引 */
  const getSelectedStrategyIndex = useCallback(() => {
    const selectedIndex = strategyOptions.findIndex((option) => option.id === selectedStrategyId);
    return selectedIndex >= 0 ? selectedIndex : 0;
  }, [selectedStrategyId, strategyOptions]);
  // 策略菜单项引用数组按选项数量截断
  useEffect(() => {
    strategyItemRefs.current = strategyItemRefs.current.slice(0, strategyOptions.length);
  }, [strategyOptions.length]);
  /**
   * 策略菜单打开后，将焦点设置到目标菜单项
   * 目标项为初始焦点索引（键盘触发时）或当前选中项
   */
  useEffect(() => {
    if (!strategyMenuOpen) {
      return undefined;
    }

    const targetIndex = strategyInitialFocusIndexRef.current ?? getSelectedStrategyIndex();
    strategyInitialFocusIndexRef.current = null;
    const timeout = window.setTimeout(() => focusStrategyItem(targetIndex), 0);
    return () => window.clearTimeout(timeout);
  }, [focusStrategyItem, getSelectedStrategyIndex, strategyMenuOpen]);
  /** 策略按钮键盘事件处理：上下方向键打开菜单并聚焦首/末项 */
  const handleStrategyButtonKeyDown = useCallback((event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') {
      return;
    }

    event.preventDefault();
    const targetIndex = event.key === 'ArrowUp' ? strategyOptions.length - 1 : 0;
    if (strategyMenuOpen) {
      focusStrategyItem(targetIndex);
      return;
    }
    strategyInitialFocusIndexRef.current = targetIndex;
    setStrategyMenuOpen(true);
  }, [focusStrategyItem, strategyMenuOpen, strategyOptions.length]);
  /** 策略菜单键盘导航：Esc 关闭、上下方向键移动、Home/End 跳转首尾、Tab 关闭 */
  const handleStrategyMenuKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    const itemCount = strategyOptions.length;
    if (itemCount === 0) {
      return;
    }

    const currentIndex = strategyItemRefs.current.findIndex((item) => item === document.activeElement);
    switch (event.key) {
      case 'Escape':
        event.preventDefault();
        closeStrategyMenu(true);
        break;
      case 'ArrowDown':
        event.preventDefault();
        focusStrategyItem(currentIndex >= 0 ? currentIndex + 1 : 0);
        break;
      case 'ArrowUp':
        event.preventDefault();
        focusStrategyItem(currentIndex >= 0 ? currentIndex - 1 : itemCount - 1);
        break;
      case 'Home':
        event.preventDefault();
        focusStrategyItem(0);
        break;
      case 'End':
        event.preventDefault();
        focusStrategyItem(itemCount - 1);
        break;
      case 'Tab':
        setStrategyMenuOpen(false);
        break;
      default:
        break;
    }
  }, [closeStrategyMenu, focusStrategyItem, strategyOptions.length]);
  /** 系统初始化是否需要用户操作（有未完成的必需检查项） */
  const setupNeedsAction = setupStatus ? !setupStatus.isComplete : false;
  /** 系统初始化缺失项的标签文案（最多取前 3 项） */
  const setupMissingLabels = useMemo(() => {
    if (!setupStatus) {
      return '';
    }
    const requiredNeedsAction = setupStatus.checks
      .filter((check) => check.required && check.status === 'needs_action')
      .map((check) => check.title);
    return requiredNeedsAction.slice(0, 3).join(uiLanguage === 'en' ? ', ' : '、');
  }, [setupStatus, uiLanguage]);

  /**
   * 任务完成后的数据刷新回调
   * 非大盘回顾任务完成时，递增今日分析刷新版本号以触发重新加载
   */
  const handleCompletedTaskDataRefreshed = useCallback((task: TaskInfo) => {
    if (task.reportType !== 'market_review') {
      setTodayAnalysisRefreshVersion((version) => version + 1);
    }
  }, []);

  /** 仪表板数据刷新回调：递增今日分析刷新版本号 */
  const handleDashboardDataRefresh = useCallback(() => {
    setTodayAnalysisRefreshVersion((version) => version + 1);
  }, []);

  /**
   * 仪表板生命周期 Hook：注册任务事件回调与数据刷新策略
   * - 任务创建/更新/失败/移除时同步活跃任务列表
   * - 初始加载历史记录、股票条目、大盘回顾历史
   * - 任务完成后按报告类型刷新对应数据（个股或大盘回顾）
   * - onDashboardDataRefresh：仪表板数据刷新时递增今日分析版本号
   * - onCompletedTaskDataRefreshed：任务完成数据刷新后的回调
   */
  useDashboardLifecycle({
    loadInitialHistory,
    refreshHistory,
    refreshHistoryForCompletedTask,
    loadMarketReviewHistory,
    refreshMarketReviewHistory,
    loadStockBar,
    refreshStockBar,
    syncTaskCreated,
    syncTaskUpdated,
    syncTaskFailed,
    refreshActiveTasks,
    removeTask,
    onDashboardDataRefresh: handleDashboardDataRefresh,
    onCompletedTaskDataRefreshed: handleCompletedTaskDataRefreshed,
  });

  /**
   * 监听股票条目加载状态变化：
   * - 加载开始时标记已启动
   * - 加载完成或已有数据时标记初始加载已结束
   * 用于控制自选股今日分析状态的查询时机
   */
  useEffect(() => {
    if (isLoadingStockBar) {
      stockBarLoadStartedRef.current = true;
      return;
    }
    if (stockBarLoadStartedRef.current || stockBarItems.length > 0) {
      setIsStockBarInitialLoadSettled(true);
    }
  }, [isLoadingStockBar, stockBarItems.length]);

  /** 自选股状态 Hook：提供自选股列表和增删改查操作 */
  const watchlistState = useWatchlist();
  /** 自选股代码按标准化形式去重后的 [key, 原始code] 数组 */
  const watchlistCodesByNormalized = useMemo(() => {
    const codesByNormalized = new Map<string, string>();
    for (const code of watchlistState.watchlistCodes) {
      const key = getStockCodeKey(code);
      if (!key || key === 'MARKET' || codesByNormalized.has(key)) {
        continue;
      }
      codesByNormalized.set(key, code);
    }
    return Array.from(codesByNormalized.entries());
  }, [watchlistState.watchlistCodes]);

  /** 股票条目按标准化代码索引的 Map（排除大盘回顾条目） */
  const stockBarItemByCode = useMemo(() => {
    const itemsByCode = new Map<string, StockBarItem>();
    for (const item of stockBarItems) {
      if (item.stockCode === 'MARKET') {
        continue;
      }
      const key = getStockCodeKey(item.stockCode);
      if (key) {
        itemsByCode.set(key, item);
      }
    }
    return itemsByCode;
  }, [stockBarItems]);

  /** 是否可以开始查找自选股历史记录（股票条目初始加载已完成） */
  const canLookupWatchlistHistory = !isLoadingStockBar && isStockBarInitialLoadSettled;

  /** 自选股中缺少今日分析数据的条目（在股票条目中未找到的） */
  const watchlistMissingHistoryEntries = useMemo(
    () => (
      canLookupWatchlistHistory
        ? watchlistCodesByNormalized.filter(([key]) => !stockBarItemByCode.has(key))
        : []
    ),
    [canLookupWatchlistHistory, stockBarItemByCode, watchlistCodesByNormalized],
  );

  /** 缺失条目的签名（用换行符拼接的 key 字符串），用于检测变化触发重新查找 */
  const watchlistMissingHistorySignature = useMemo(
    () => watchlistMissingHistoryEntries.map(([key]) => key).join('\n'),
    [watchlistMissingHistoryEntries],
  );

  /**
   * 查找自选股中缺失今日分析数据的股票的历史记录
   * 对每个缺失的股票代码单独查询历史 API，将结果合并到状态中
   * 支持取消（组件卸载或依赖变化时）
   */
  useEffect(() => {
    if (!canLookupWatchlistHistory) {
      setWatchlistHistoryItemsByCode(new Map());
      setWatchlistHistoryLookupState({ signature: '', settledKeys: new Set(), failedKeys: new Set() });
      return undefined;
    }

    const missingCodes = watchlistMissingHistoryEntries.map(([, code]) => code);
    const missingKeys = watchlistMissingHistoryEntries.map(([key]) => key);
    const currentSignature = watchlistMissingHistorySignature;

    if (missingCodes.length === 0) {
      setWatchlistHistoryItemsByCode(new Map());
      setWatchlistHistoryLookupState({ signature: '', settledKeys: new Set(), failedKeys: new Set() });
      return;
    }

    let isCanceled = false;
    setWatchlistHistoryLookupState({ signature: currentSignature, settledKeys: new Set(), failedKeys: new Set() });
    void (async () => {
      try {
        const results = await Promise.all(
          missingCodes.map(async (code) => {
            try {
              const response = await historyApi.getList({ stockCode: code, limit: 1 });
              return { code, item: response.items[0] ?? null, failed: false };
            } catch {
              return { code, item: null, failed: true };
            }
          }),
        );

        if (isCanceled) {
          return;
        }

        const next = new Map<string, StockBarItem>();
        const failedKeys = new Set<string>();
        for (const entry of results) {
          const key = getStockCodeKey(entry.code);
          if (!key) {
            continue;
          }
          if (entry.failed) {
            failedKeys.add(key);
            continue;
          }
          if (entry.item) {
            next.set(key, toStockBarItemFromHistoryItem(entry.item));
          }
        }
        setWatchlistHistoryItemsByCode(next);
        setWatchlistHistoryLookupState({
          signature: currentSignature,
          settledKeys: new Set(missingKeys),
          failedKeys,
        });
      } catch {
        if (!isCanceled) {
          setWatchlistHistoryItemsByCode(new Map());
          setWatchlistHistoryLookupState({
            signature: currentSignature,
            settledKeys: new Set(missingKeys),
            failedKeys: new Set(missingKeys),
          });
        }
      }
    })();

    return () => {
      isCanceled = true;
    };
  }, [canLookupWatchlistHistory, watchlistMissingHistoryEntries, watchlistMissingHistorySignature]);

  /** 清除大盘回顾相关状态（停止轮询、清空报告和通知） */
  const clearMarketReviewState = useCallback(() => {
    stopMarketReviewPolling();
    setMarketReviewReport(null);
    setMarketReviewPayload(null);
    setMarketReviewNotice(null);
    setMarketReviewError(null);
  }, [stopMarketReviewPolling]);

  /**
   * 历史记录点击事件处理：清除大盘回顾状态、选中历史记录、关闭侧边栏
   * @param recordId - 历史记录 ID
   */
  const handleHistoryItemClick = useCallback((recordId: number) => {
    clearMarketReviewState();
    void selectHistoryItem(recordId);
    setSidebarOpen(false);
  }, [clearMarketReviewState, selectHistoryItem]);

  /** 是否正在删除股票 */
  const [isDeletingStock, setIsDeletingStock] = useState(false);
  /**
   * 删除指定股票的所有历史记录
   * 删除后刷新股票条目和历史列表，如果是大盘回顾则同时刷新大盘回顾历史
   * @param stockCode - 要删除的股票代码
   */
  const handleDeleteStock = useCallback(async (stockCode: string) => {
    if (isDeletingStock) return;
    setIsDeletingStock(true);
    try {
      // 调用 API 删除指定股票的所有历史记录
      await historyApi.deleteByCode(stockCode);
      // 刷新股票条目列表和历史记录列表
      await refreshStockBar();
      await refreshHistory(true);
      // 如果删除的是大盘回顾（MARKET），额外刷新大盘回顾历史
      if (stockCode === 'MARKET') {
        await refreshMarketReviewHistory(false);
      }
    } catch {
      // error silently ignored
    } finally {
      setIsDeletingStock(false);
    }
  }, [isDeletingStock, refreshMarketReviewHistory, refreshStockBar, refreshHistory]);

  /**
   * 提交股票分析的事件处理函数
   * 将股票代码、名称、查询来源和选中策略传递给分析提交逻辑
   * @param stockCode - 股票代码
   * @param stockName - 股票名称
   * @param selectionSource - 选择来源：手动输入/自动补全/导入/图片
   */
  const handleSubmitAnalysis = useCallback(
    (
      stockCode?: string,
      stockName?: string,
      selectionSource?: 'manual' | 'autocomplete' | 'import' | 'image',
    ) => {
      void submitAnalysis({
        stockCode,
        stockName,
        originalQuery: query,
        selectionSource: selectionSource ?? 'manual',
        skills: selectedAnalysisSkills,
      });
    },
    [query, selectedAnalysisSkills, submitAnalysis],
  );

  /**
   * 监听路由导航状态变化：
   * 当从其他页面携带股票代码导航到首页时，自动填入搜索框
   * 如果带有 autoAnalyze 标记，则自动触发分析
   */
  useEffect(() => {
    const state = location.state as StockAnalysisNavigationState | null;
    const stockCode = typeof state?.stockCode === 'string' ? state.stockCode.trim() : '';
    if (!stockCode) {
      return;
    }
    const stockName = typeof state?.stockName === 'string' ? state.stockName.trim() : '';
    setQuery(stockCode);
    // 清除导航状态，避免刷新时重复触发
    navigate(location.pathname, { replace: true, state: null });
    if (state?.autoAnalyze) {
      handleSubmitAnalysis(stockCode, stockName || undefined, 'import');
    }
  }, [handleSubmitAnalysis, location.pathname, location.state, navigate, setQuery]);

  /**
   * 跳转到 AI 对话页进行追问
   * 仅对非大盘回顾类型的报告生效，携带股票代码、名称和记录 ID
   */
  const handleAskFollowUp = useCallback(() => {
    if (selectedReport?.meta.id === undefined || selectedReport.meta.reportType === 'market_review') {
      return;
    }

    const code = selectedReport.meta.stockCode;
    const name = selectedReport.meta.stockName;
    const rid = selectedReport.meta.id;
    navigate(`/chat?stock=${encodeURIComponent(code)}&name=${encodeURIComponent(name)}&recordId=${rid}`);
  }, [navigate, selectedReport]);

  /**
   * 重新分析当前选中的股票
   * 使用强制刷新模式重新提交分析任务
   */
  const handleReanalyze = useCallback(() => {
    if (!selectedReport || selectedReport.meta.reportType === 'market_review') {
      return;
    }

    void submitAnalysis({
      stockCode: selectedReport.meta.stockCode,
      stockName: selectedReport.meta.stockName,
      originalQuery: selectedReport.meta.stockCode,
      selectionSource: 'manual',
      forceRefresh: true,
      skills: selectedAnalysisSkills,
    });
  }, [selectedAnalysisSkills, selectedReport, submitAnalysis]);

  /**
   * 打开任务运行流程抽屉
   * @param task - 当前任务信息
   */
  const openTaskRunFlow = useCallback((task: TaskInfo) => {
    const stock = task.stockName || task.stockCode || task.taskId;
    setRunFlowDrawer({
      open: true,
      source: { type: 'task', taskId: task.taskId },
      title: t('runFlow.taskDrawerTitle', { stock }),
    });
  }, [t]);

  /**
   * 打开历史记录运行流程抽屉
   * @param recordId - 历史记录 ID
   */
  const openHistoryRunFlow = useCallback((recordId: number) => {
    const meta = selectedReport?.meta.id === recordId ? selectedReport.meta : null;
    const stock = meta?.stockName || meta?.stockCode || String(recordId);
    setRunFlowDrawer({
      open: true,
      source: { type: 'history', recordId },
      title: t('runFlow.historyDrawerTitle', { stock }),
    });
  }, [selectedReport, t]);

  /** 关闭运行流程抽屉 */
  const closeRunFlowDrawer = useCallback(() => {
    setRunFlowDrawer({ open: false });
  }, []);

  /**
   * 轮询大盘回顾任务状态
   * 以 2 秒间隔轮询，最多 120 次（4 分钟），根据状态更新 UI：
   * - pending/processing：显示进行中提示
   * - completed：显示报告并刷新大盘回顾历史
   * - failed：显示错误信息
   * - 其他：显示未知状态提示
   * @param taskId - 大盘回顾任务 ID
   */
  const pollMarketReviewStatus = useCallback(
    async (taskId: string) => {
      stopMarketReviewPolling();

      const maxAttempts = 120;
      const intervalMs = 2000;
      let attempts = 0;

      const poll = async (): Promise<boolean> => {
        if (attempts >= maxAttempts) {
          stopMarketReviewPolling();
          setMarketReviewReport(null);
          setMarketReviewPayload(null);
          setMarketReviewNotice({
            variant: 'danger',
            title: t('home.marketReviewTimeout'),
            message: t('home.marketReviewTimeoutMessage'),
          });
          scrollMarketReviewFeedbackIntoView();
          return false;
        }

        attempts += 1;

        try {
          const status = await analysisApi.getStatus(taskId);
          // 任务进行中（排队或处理中）：清空已有报告，展示进度提示
          if (status.status === 'pending' || status.status === 'processing') {
            setMarketReviewReport(null);
            setMarketReviewPayload(null);
            const progress = typeof status.progress === 'number'
              ? `${status.progress}%`
              : t('home.progressActive');
            setMarketReviewNotice({
              variant: 'warning',
              title: t('home.marketReviewInProgress'),
              message: status.region
                ? t('home.taskStatusWithRegion', { status: status.status, progress, region: status.region })
                : t('home.taskStatus', { status: status.status, progress }),
            });
            return true;
          }

          // 任务完成：停止轮询，保存报告和结构化数据，刷新大盘回顾历史
          if (status.status === 'completed') {
            stopMarketReviewPolling();
            const marketReviewText = typeof status.marketReviewReport === 'string'
              ? status.marketReviewReport
              : '';
            setMarketReviewReport(marketReviewText ? marketReviewText.trim() : null);
            setMarketReviewPayload(status.marketReviewPayload ?? null);
            setMarketReviewNotice({
              variant: 'success',
              title: t('home.marketReviewCompleted'),
              message: marketReviewText ? t('home.marketReviewCompletedWithReport') : t('home.marketReviewCompletedWithoutReport'),
            });
            setMarketReviewError(null);
            await refreshMarketReviewHistory(true);
            scrollMarketReviewFeedbackIntoView();
            return false;
          }

          // 任务失败：停止轮询，清空报告，展示错误信息
          if (status.status === 'failed') {
            stopMarketReviewPolling();
            setMarketReviewReport(null);
            setMarketReviewPayload(null);
            setMarketReviewError(
              getParsedApiError({
                response: {
                  status: 500,
                  data: {
                    error: 'market_review_failed',
                    message: status.error || t('home.marketReviewFailed'),
                  },
                },
              }),
            );
            setMarketReviewNotice(null);
            scrollMarketReviewFeedbackIntoView();
            return false;
          }

          // 未知任务状态：停止轮询，展示未知状态提示
          stopMarketReviewPolling();
          setMarketReviewReport(null);
          setMarketReviewPayload(null);
          setMarketReviewNotice({
            variant: 'danger',
            title: t('home.marketReviewUnknownStatus'),
            message: t('home.unknownTaskStatus', { status: status.status }),
          });
          scrollMarketReviewFeedbackIntoView();
          return false;
        // 轮询请求异常：解析错误，达到最大尝试次数则终止轮询，否则继续重试
        } catch (err: unknown) {
          const parsed = getParsedApiError(err);
          if (attempts >= maxAttempts) {
            stopMarketReviewPolling();
            setMarketReviewReport(null);
            setMarketReviewPayload(null);
            setMarketReviewError(parsed);
            setMarketReviewNotice(null);
            scrollMarketReviewFeedbackIntoView();
            return false;
          }
          return true;
        }

        return true;
      };

      // 首次轮询返回 true（需要继续）时，启动定时轮询
      if (await poll()) {
        marketReviewPollTimer.current = window.setInterval(() => {
          void poll().then((shouldContinue) => {
            // 轮询返回 false（任务完成/失败/超时）时停止定时器
            if (!shouldContinue) {
              stopMarketReviewPolling();
            }
          });
        }, intervalMs);
      }
    },
    [refreshMarketReviewHistory, scrollMarketReviewFeedbackIntoView, stopMarketReviewPolling, t],
  );

  /**
   * 触发大盘回顾分析
   * 重置状态后调用 API 触发，成功后如有 taskId 则开始轮询任务状态
   */
  const handleTriggerMarketReview = useCallback(async () => {
    // 重置大盘回顾相关状态，准备提交
    setIsSubmittingMarketReview(true);
    setMarketReviewNotice(null);
    setMarketReviewError(null);
    setMarketReviewReport(null);
    setMarketReviewPayload(null);
    scrollMarketReviewFeedbackIntoView();
    try {
      // 调用 API 触发大盘回顾分析，携带通知开关和地区覆盖设置
      const result = await analysisApi.triggerMarketReview({
        sendNotification: notify,
        regions: marketReviewRegionOverride,
      });
      setMarketReviewNotice({
        variant: 'success',
        title: t('home.marketReviewSubmitted'),
        message: t('home.marketReviewSubmittedWithRegion', {
          message: result.message,
          region: result.region,
        }),
      });
      scrollMarketReviewFeedbackIntoView();

      if (result.taskId) {
        await pollMarketReviewStatus(result.taskId);
      }
    } catch (err: unknown) {
      setMarketReviewError(getParsedApiError(err));
      setMarketReviewNotice(null);
      scrollMarketReviewFeedbackIntoView();
    } finally {
      setIsSubmittingMarketReview(false);
    }
  }, [marketReviewRegionOverride, notify, pollMarketReviewStatus, scrollMarketReviewFeedbackIntoView, t]);

  /** 今日上海时区日期键 */
  const todayDateKey = getTodayInShanghai();
  /**
   * 当侧边栏切换到"今日"标签页时，加载今日分析记录
   * 或今日分析刷新版本号变化时重新加载
   */
  useEffect(() => {
    if (sidebarWorkspaceTab !== 'today') {
      return undefined;
    }

    let active = true;
    setIsLoadingTodayAnalysisItems(true);
    setTodayAnalysisLoadFailed(false);
    void getTodayAnalysisItems(todayDateKey)
      .then((items) => {
        if (active) {
          setTodayHistoryItems(items);
          setTodayAnalysisLoadFailed(false);
        }
      })
      .catch(() => {
        if (active) {
          setTodayHistoryItems([]);
          setTodayAnalysisLoadFailed(true);
        }
      })
      .finally(() => {
        if (active) {
          setIsLoadingTodayAnalysisItems(false);
        }
      });

    return () => {
      active = false;
    };
  }, [sidebarWorkspaceTab, todayAnalysisRefreshVersion, todayDateKey]);

  /** 活跃任务按标准化股票代码索引的 Map（排除大盘回顾和已完成任务） */
  const activeTaskByCode = useMemo(() => {
    const tasksByCode = new Map<string, TaskInfo>();
    for (const task of activeTasks) {
      if (!['pending', 'processing', 'cancel_requested'].includes(task.status)) {
        continue;
      }
      if (task.reportType === 'market_review') {
        continue;
      }
      const key = getStockCodeKey(task.stockCode);
      if (key) {
        tasksByCode.set(key, task);
      }
    }
    return tasksByCode;
  }, [activeTasks]);

  /**
   * 自选股行数据：合并股票条目和补充历史记录，计算今日分析状态
   * 每行包含：股票代码、最新条目、是否今日已分析、状态加载/未知、活跃任务
   */
  const watchlistRows = useMemo<HomeWatchlistRow[]>(() => (
    watchlistState.watchlistCodes.map((code) => {
      const key = getStockCodeKey(code);
      const latestItem = key
        ? stockBarItemByCode.get(key) ?? watchlistHistoryItemsByCode.get(key)
        : undefined;
      // 该股票是否在股票条目列表中缺失（需要通过历史记录补充查询）
      const isMissingFromStockBar = Boolean(key && !stockBarItemByCode.has(key));
      // 今日分析状态是否未知：股票条目刷新失败，或补充历史查询也失败时为 true
      const isTodayStatusUnknown = Boolean(
        stockBarRefreshFailed
        || (
          isMissingFromStockBar
          && canLookupWatchlistHistory
          && watchlistHistoryLookupState.signature === watchlistMissingHistorySignature
          && watchlistHistoryLookupState.failedKeys.has(key)
        ),
      );
      // 今日分析状态是否加载中：股票条目缺失且补充历史查询尚未完成时为 true
      const isTodayStatusLoading = Boolean(
        isMissingFromStockBar
        && !isTodayStatusUnknown
        && (
          !canLookupWatchlistHistory
          ||
          watchlistHistoryLookupState.signature !== watchlistMissingHistorySignature
          || !watchlistHistoryLookupState.settledKeys.has(key)
        ),
      );
      return {
        code,
        latestItem,
        analyzedToday: !isTodayStatusLoading && !isTodayStatusUnknown && getShanghaiDateKey(latestItem?.lastAnalysisTime) === todayDateKey,
        isTodayStatusLoading,
        isTodayStatusUnknown,
        activeTask: key ? activeTaskByCode.get(key) : undefined,
      };
    })
  ), [
    activeTaskByCode,
    canLookupWatchlistHistory,
    stockBarRefreshFailed,
    stockBarItemByCode,
    todayDateKey,
    watchlistHistoryItemsByCode,
    watchlistHistoryLookupState,
    watchlistMissingHistorySignature,
    watchlistState.watchlistCodes,
  ]);

  /** 自选股中今日已分析的股票数量 */
  const watchlistAnalyzedTodayCount = useMemo(
    () => watchlistRows.filter((row) => row.analyzedToday).length,
    [watchlistRows],
  );

  /** 自选股中待分析（未今日分析且状态已确定）的股票代码列表 */
  const pendingWatchlistCodes = useMemo(
    () => watchlistRows
      .filter((row) => !row.analyzedToday && !row.isTodayStatusLoading && !row.isTodayStatusUnknown)
      .map((row) => row.code),
    [watchlistRows],
  );

  /** 自选股今日分析状态是否被阻塞（有正在加载或状态未知的行） */
  const watchlistTodayStatusBlocked = useMemo(
    () => watchlistRows.some((row) => row.isTodayStatusLoading || row.isTodayStatusUnknown),
    [watchlistRows],
  );

  /**
   * 今日分析记录列表：过滤出上海时区当日的记录，按情绪分数和时间倒序排列
   */
  const todayAnalysisItems = useMemo(() => {
    const itemsById = new Map<number, StockBarItem>();
    const addItem = (item: StockBarItem) => {
      if (item.stockCode === 'MARKET' || item.reportType === 'market_review') {
        return;
      }
      if (getShanghaiDateKey(item.lastAnalysisTime) !== todayDateKey) {
        return;
      }
      itemsById.set(item.id, item);
    };

    for (const item of todayHistoryItems) {
      addItem(item);
    }

    return Array.from(itemsById.values())
      .sort((left, right) => {
        const leftScore = typeof left.sentimentScore === 'number' ? left.sentimentScore : -1;
        const rightScore = typeof right.sentimentScore === 'number' ? right.sentimentScore : -1;
        if (rightScore !== leftScore) {
          return rightScore - leftScore;
        }
        const leftTime = getShanghaiTimeValue(left.lastAnalysisTime);
        const rightTime = getShanghaiTimeValue(right.lastAnalysisTime);
        return rightTime - leftTime;
      });
  }, [todayDateKey, todayHistoryItems]);

  /**
   * 批量分析自选股
   * 支持两种模式：
   * - pending：仅分析今日尚未分析的股票
   * - all：分析所有自选股
   * 将股票代码分块提交，统计成功/重复/失败数量，最后刷新活跃任务列表
   * @param mode - 分析模式
   */
  const handleAnalyzeWatchlist = useCallback(async (mode: WatchlistAnalyzeMode) => {
    if (mode === 'pending' && watchlistTodayStatusBlocked) {
      setBatchAnalyzeStatus({
        variant: 'warning',
        message: t('watchlist.pendingStatusUnavailable'),
      });
      return;
    }

    // 根据模式选择待分析的股票代码来源
    const sourceCodes = mode === 'pending' ? pendingWatchlistCodes : watchlistState.watchlistCodes;
    // 按标准化代码去重，避免同一股票被重复提交
    const seen = new Set<string>();
    const targetCodes = sourceCodes.filter((code) => {
      const key = getStockCodeKey(code);
      if (!key || seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });

    if (targetCodes.length === 0) {
      setBatchAnalyzeStatus({
        variant: 'warning',
        message: mode === 'pending' ? t('watchlist.noPendingAnalyze') : t('watchlist.noStocksAnalyze'),
      });
      return;
    }

    setIsBatchAnalyzingWatchlist(true);
    setBatchAnalyzeStatus(null);
    let acceptedCount = 0;
    let duplicateCount = 0;
    let confirmedCodeCount = 0;
    let submissionError: ParsedApiError | null = null;
    try {
      // 将目标代码分块逐批提交，避免单次请求过大
      for (const chunk of chunkStockCodes(targetCodes)) {
        try {
          const result = await analysisApi.analyzeAsync({
            stockCodes: chunk,
            reportType: 'detailed',
            notify,
            skills: selectedAnalysisSkills,
          });
          const counts = countBatchAccepted(result);
          acceptedCount += counts.accepted;
          duplicateCount += counts.duplicates;
          const confirmedInChunk = counts.accepted + counts.duplicates;
          confirmedCodeCount += Math.min(confirmedInChunk, chunk.length);
          if (confirmedInChunk !== chunk.length) {
            submissionError = getParsedApiError(new Error(t('watchlist.batchIncompleteResponse', {
              confirmed: confirmedInChunk,
              requested: chunk.length,
            })));
            break;
          }
        } catch (error: unknown) {
          if (error instanceof DuplicateTaskError && chunk.length === 1) {
            duplicateCount += 1;
            confirmedCodeCount += 1;
            continue;
          }
          submissionError = getParsedApiError(error);
          break;
        }
      }

      // 即使请求失败也需要对账：超时或断连可能发生在服务端已接受任务之后，
      // 之前分块提交的任务可能仍在运行，因此刷新活跃任务列表以同步状态
      await refreshActiveTasks();
      setSidebarWorkspaceTab('watchlist');

      if (submissionError) {
        if (acceptedCount > 0 || duplicateCount > 0) {
          setBatchAnalyzeStatus({
            variant: 'warning',
            message: t('watchlist.batchPartiallySubmitted', {
              accepted: acceptedCount,
              duplicates: duplicateCount,
              unconfirmed: targetCodes.length - confirmedCodeCount,
              error: submissionError.message || t('watchlist.batchFailed'),
            }),
          });
        } else {
          setBatchAnalyzeStatus({
            variant: 'danger',
            message: submissionError.message || t('watchlist.batchFailed'),
          });
        }
        return;
      }

      setBatchAnalyzeStatus({
        variant: acceptedCount > 0 ? 'success' : 'warning',
        message: t('watchlist.batchSubmitted', {
          accepted: acceptedCount,
          duplicates: duplicateCount,
        }),
      });
    } catch (error: unknown) {
      const parsed = getParsedApiError(error);
      setBatchAnalyzeStatus({
        variant: 'danger',
        message: parsed.message || t('watchlist.batchFailed'),
      });
    } finally {
      setIsBatchAnalyzingWatchlist(false);
    }
  }, [
    notify,
    pendingWatchlistCodes,
    refreshActiveTasks,
    selectedAnalysisSkills,
    t,
    watchlistTodayStatusBlocked,
    watchlistState.watchlistCodes,
  ]);

  /**
   * 合并后的股票条目列表：将最新的大盘回顾条目与个股条目合并，按时间倒序排列
   */
  const mergedStockBarItems = useMemo<StockBarItem[]>(() => {
    const latestMarketReview = marketReviewHistoryItems[0];
    const stockItems = stockBarItems.filter((item) => item.stockCode !== 'MARKET');
    if (!latestMarketReview) {
      return stockItems;
    }

    const marketReviewItem: StockBarItem = {
      id: latestMarketReview.id,
      stockCode: 'MARKET',
      stockName: latestMarketReview.stockName || t('home.marketReview'),
      reportType: 'market_review',
      sentimentScore: latestMarketReview.sentimentScore,
      operationAdvice: latestMarketReview.operationAdvice,
      analysisCount: Math.max(marketReviewHistoryItems.length, 1),
      lastAnalysisTime: latestMarketReview.createdAt,
      modelUsed: latestMarketReview.modelUsed,
      marketPhaseSummary: latestMarketReview.marketPhaseSummary,
    };

    return [marketReviewItem, ...stockItems].sort((left, right) => {
      const leftTime = left.lastAnalysisTime ? Date.parse(left.lastAnalysisTime) : 0;
      const rightTime = right.lastAnalysisTime ? Date.parse(right.lastAnalysisTime) : 0;
      return rightTime - leftTime;
    });
  }, [marketReviewHistoryItems, stockBarItems, t]);

  /** 侧边栏内容（任务面板 + 自选股工作区），桌面端常驻、移动端抽屉展示 */
  const sidebarContent = useMemo(
    () => (
      <div className="flex min-h-0 h-full flex-col gap-3 overflow-hidden">
        <TaskPanel tasks={activeTasks} onOpenRunFlow={openTaskRunFlow} />
        <HomeStockWorkspace
          activeTab={sidebarWorkspaceTab}
          onTabChange={setSidebarWorkspaceTab}
          watchlistRows={watchlistRows}
          watchlistLoading={watchlistState.isLoading}
          watchlistActioning={watchlistState.isActioning}
          watchlistMessage={watchlistState.actionMessage}
          onAddToWatchlist={watchlistState.addToWatchlist}
          onRemoveFromWatchlist={watchlistState.removeFromWatchlist}
          onRefreshWatchlist={watchlistState.refresh}
          onAnalyzeWatchlist={handleAnalyzeWatchlist}
          isBatchAnalyzing={isBatchAnalyzingWatchlist}
          batchStatus={batchAnalyzeStatus}
          todayItems={todayAnalysisItems}
          isLoadingTodayItems={isLoadingTodayAnalysisItems}
          todayLoadError={todayAnalysisLoadFailed}
          watchlistAnalyzedTodayCount={watchlistAnalyzedTodayCount}
          historyItems={mergedStockBarItems}
          isLoadingHistory={isLoadingStockBar}
          selectedStockCode={selectedReport?.meta.stockCode}
          selectedRecordId={selectedReport?.meta.id}
          onHistoryItemClick={handleHistoryItemClick}
          onDeleteStock={handleDeleteStock}
          isDeleting={isDeletingStock}
          className="flex-1 overflow-hidden"
        />
      </div>
    ),
    [
      activeTasks,
      batchAnalyzeStatus,
      handleAnalyzeWatchlist,
      handleDeleteStock,
      handleHistoryItemClick,
      isBatchAnalyzingWatchlist,
      isDeletingStock,
      isLoadingStockBar,
      isLoadingTodayAnalysisItems,
      todayAnalysisLoadFailed,
      mergedStockBarItems,
      openTaskRunFlow,
      selectedReport?.meta.id,
      selectedReport?.meta.stockCode,
      sidebarWorkspaceTab,
      todayAnalysisItems,
      watchlistAnalyzedTodayCount,
      watchlistRows,
      watchlistState.actionMessage,
      watchlistState.addToWatchlist,
      watchlistState.isActioning,
      watchlistState.isLoading,
      watchlistState.refresh,
      watchlistState.removeFromWatchlist,
    ],
  );

  return (
    <div
      data-testid="home-dashboard"
      className="flex h-[calc(100vh-5rem)] w-full flex-col overflow-hidden md:flex-row sm:h-[calc(100vh-5.5rem)] lg:h-[calc(100vh-2rem)]"
    >
      <div className="flex-1 flex flex-col min-h-0 min-w-0 max-w-full lg:max-w-6xl mx-auto w-full">
        {/* ===== 顶部操作栏：股票搜索 + 策略选择 + 大盘回顾 + 分析按钮 ===== */}
        <header className="relative z-30 flex min-w-0 flex-shrink-0 items-center overflow-visible px-3 py-3 md:px-4 md:py-4">
          <div className="flex min-w-0 flex-1 flex-col gap-2.5 md:flex-row md:items-center">
            <div className="flex min-w-0 flex-1 items-center gap-2.5">
              <button
                onClick={() => setSidebarOpen(true)}
                className="md:hidden -ml-1 flex-shrink-0 rounded-lg p-1.5 text-secondary-text transition-colors hover:bg-hover hover:text-foreground"
                aria-label={t('home.historyButton')}
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <div className="relative min-w-0 flex-1">
                <StockAutocomplete
                  value={query}
                  onChange={setQuery}
                  onSubmit={(stockCode, stockName, selectionSource) => {
                    handleSubmitAnalysis(stockCode, stockName, selectionSource);
                  }}
                  placeholder={t('home.placeholder')}
                  disabled={isAnalyzing}
                  className={inputError ? 'border-danger/50' : undefined}
                />
              </div>
              {analysisSkills.length > 0 ? (
                <div ref={strategyMenuRef} className="relative flex-shrink-0">
                  <button
                    ref={strategyButtonRef}
                    id="strategy-menu-button"
                    type="button"
                    aria-haspopup="menu"
                    aria-expanded={strategyMenuOpen}
                    aria-controls={strategyMenuOpen ? 'strategy-menu' : undefined}
                    onClick={() => setStrategyMenuOpen((open) => !open)}
                    onKeyDown={handleStrategyButtonKeyDown}
                    disabled={isAnalyzing}
                    className="home-surface-button flex h-10 max-w-[8.5rem] items-center gap-1.5 rounded-xl px-3 text-xs text-foreground disabled:cursor-not-allowed disabled:opacity-60 sm:max-w-[11rem]"
                  >
                    <SlidersHorizontal className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                    <span className="truncate">{selectedStrategy?.name || t('home.strategy')}</span>
                  </button>
                  {strategyMenuOpen ? (
                    <div
                      id="strategy-menu"
                      role="menu"
                      aria-labelledby="strategy-menu-button"
                      onKeyDown={handleStrategyMenuKeyDown}
                      className="absolute right-0 top-11 z-[120] max-h-80 w-[min(18rem,calc(100vw-1.5rem))] overflow-y-auto rounded-xl border border-subtle bg-elevated p-1.5 text-sm text-foreground shadow-2xl"
                    >
                      {strategyOptions.map((option, index) => {
                        const selected = selectedStrategyId === option.id;
                        return (
                          <button
                            key={option.id || 'default'}
                            ref={(node) => {
                              strategyItemRefs.current[index] = node;
                            }}
                            type="button"
                            role="menuitemradio"
                            aria-checked={selected}
                            tabIndex={-1}
                            onClick={() => selectStrategy(option.id)}
                            className="flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-hover"
                          >
                            <Check className={`mt-0.5 h-4 w-4 flex-shrink-0 ${selected ? 'opacity-100' : 'opacity-0'}`} aria-hidden="true" />
                            <span className="min-w-0">
                              <span className="block font-medium">{option.name}</span>
                              <span className="mt-0.5 line-clamp-2 block text-xs leading-5 text-muted-text">{option.description}</span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
            <div className="flex min-w-0 flex-wrap items-center gap-2.5">
              <MarketReviewRegionSelector
                value={marketReviewRegionOverride}
                disabled={isSubmittingMarketReview}
                onChange={setMarketReviewRegionOverride}
              />
              <label className="flex h-10 flex-shrink-0 cursor-pointer items-center gap-1.5 rounded-xl border border-subtle bg-surface/60 px-3 text-xs text-secondary-text select-none transition-colors hover:border-subtle-hover hover:text-foreground has-disabled:cursor-not-allowed has-disabled:opacity-50">
                <input
                  type="checkbox"
                  checked={notify}
                  disabled={isSubmittingMarketReview}
                  onChange={(e) => setNotify(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-border accent-primary"
                />
                {t('home.notify')}
              </label>
              <Button
                type="button"
                variant="secondary"
                size="md"
                isLoading={isSubmittingMarketReview}
                loadingText={t('home.submitMarketReview')}
                onClick={() => void handleTriggerMarketReview()}
                className="h-10 flex-1 whitespace-nowrap md:flex-none"
              >
                <BarChart3 className="h-4 w-4" aria-hidden="true" />
                {t('home.marketReview')}
              </Button>
              <button
                type="button"
                onClick={() => handleSubmitAnalysis()}
                disabled={!query || isAnalyzing}
                className="btn-primary flex h-10 flex-1 items-center justify-center gap-1.5 whitespace-nowrap md:flex-none"
              >
                {isAnalyzing ? (
                  <>
                    <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    {t('home.analyzing')}
                  </>
                ) : (
                  t('home.analyze')
                )}
              </button>
            </div>
          </div>
        </header>

        {/* ===== 输入错误 / 重复任务提示区 ===== */}
        {inputError || (duplicateError && duplicateBannerVisible) ? (
          <div className="px-3 pb-2 md:px-4">
            {inputError ? (
              <InlineAlert
                variant="danger"
                title={t('home.inputInvalid')}
                message={inputError}
                className="rounded-xl px-3 py-2 text-xs shadow-none"
              />
            ) : null}
            {!inputError && duplicateError && duplicateBannerVisible ? (
              <InlineAlert
                variant="warning"
                title={t('home.duplicateTask')}
                message={duplicateError}
                action={(
                  <button
                    type="button"
                    onClick={dismissDuplicateBanner}
                    aria-label={t('common.close')}
                    className="-my-1 -mr-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg opacity-70 transition-colors hover:bg-warning/15 hover:opacity-100"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                )}
                className="rounded-xl px-3 py-2 text-xs shadow-none"
              />
            ) : null}
          </div>
        ) : null}

        {/* ===== 系统初始化不完整提示区 ===== */}
        {setupNeedsAction ? (
          <div className="px-3 pb-2 md:px-4">
            <InlineAlert
              variant="warning"
              title={t('home.setupIncomplete')}
              message={
                setupMissingLabels
                  ? t('home.setupMissingWithLabels', { labels: setupMissingLabels })
                  : t('home.setupMissingGeneric')
              }
              action={(
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => navigate('/settings')}
                >
                  {t('home.goSettings')}
                </Button>
              )}
              className="rounded-xl px-3 py-2 text-xs shadow-none"
            />
          </div>
        ) : null}

        {/* ===== 主内容区：左侧边栏（桌面常驻 + 移动抽屉） + 右侧仪表板 ===== */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          {/* 桌面端常驻侧边栏 */}
          <div className="hidden min-h-0 w-64 shrink-0 flex-col overflow-hidden pl-4 pb-4 md:flex lg:w-72">
            {sidebarContent}
          </div>

          {/* 移动端侧边栏抽屉 */}
          {sidebarOpen ? (
            <div className="fixed inset-0 z-40 md:hidden" onClick={() => setSidebarOpen(false)}>
              <div className="page-drawer-overlay absolute inset-0" />
              <div
                className="dashboard-card absolute bottom-0 left-0 top-0 flex w-72 flex-col overflow-hidden !rounded-none !rounded-r-xl p-3 shadow-2xl"
                onClick={(event) => event.stopPropagation()}
              >
                {sidebarContent}
              </div>
            </div>
          ) : null}

          {/* ===== 仪表板主滚动区：大盘回顾通知/报告 + 错误提示 + 报告展示 ===== */}
          <section
            ref={dashboardScrollRef}
            data-testid="home-dashboard-scroll"
            className="flex-1 min-w-0 min-h-0 overflow-x-auto overflow-y-auto px-3 pb-4 md:px-6 touch-pan-y"
          >
            {/* 大盘回顾通知提示 */}
            {marketReviewNotice ? (
              <div className="mb-3">
                <InlineAlert
                  variant={marketReviewNotice.variant}
                  title={marketReviewNotice.title}
                  message={marketReviewNotice.message}
                  className="rounded-xl px-3 py-2 text-xs shadow-none"
                />
              </div>
            ) : null}

            {/* 大盘回顾错误提示 */}
            {marketReviewError ? (
              <div className="mb-3">
                <ApiErrorAlert
                  error={marketReviewError}
                  className="mb-1"
                  onDismiss={() => setMarketReviewError(null)}
                />
              </div>
            ) : null}

            {/* 大盘回顾报告展示 */}
            {marketReviewReport ? (
              <MarketReviewReportView
                content={marketReviewReport}
                payload={marketReviewPayload}
                reportLanguage={liveMarketReviewLanguage}
                className="mb-3"
              />
            ) : null}

            {/* 通用错误提示 */}
            {error ? (
              <ApiErrorAlert
                error={error}
                className="mb-3"
                onDismiss={clearError}
              />
            ) : null}
            {/* ===== 报告加载中状态 ===== */}
            {!marketReviewReport && isLoadingReport ? (
              <div className="flex h-full flex-col items-center justify-center">
                <DashboardStateBlock title={t('home.loadingReport')} loading />
              </div>
            ) : !marketReviewReport && selectedReport ? (
              /* ===== 报告展示区：操作按钮 + 历史趋势/报告摘要 ===== */
              <div className={isHistoryTrendOpen ? 'max-w-6xl space-y-4 pb-8' : 'max-w-4xl space-y-4 pb-8'}>
                {/* 报告操作按钮栏 */}
                <div className="flex flex-wrap items-center justify-end gap-2">
                  {!isMarketReviewHistoryReport ? (
                    <>
                      <Button
                        variant="home-action-ai"
                        size="sm"
                        disabled={isAnalyzing || selectedReport.meta.id === undefined}
                        onClick={handleReanalyze}
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        {t('home.reanalyze')}
                      </Button>
                      <Button
                        variant="home-action-ai"
                        size="sm"
                        disabled={selectedReport.meta.id === undefined}
                        onClick={handleAskFollowUp}
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        {t('home.askAi')}
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="home-action-ai"
                      size="sm"
                      disabled={isSubmittingMarketReview}
                      isLoading={isSubmittingMarketReview}
                      loadingText={t('home.submitMarketReview')}
                      onClick={() => void handleTriggerMarketReview()}
                    >
                      <BarChart3 className="h-4 w-4" />
                      {t('home.rerunMarketReview')}
                    </Button>
                  )}
                  <Button
                    variant="home-action-ai"
                    size="sm"
                    disabled={selectedReport.meta.id === undefined || isHistoryTrendUnavailable}
                    className={isHistoryTrendOpen ? 'border-primary/70 bg-primary/15 text-primary shadow-glow-cyan' : undefined}
                    onClick={() => {
                      if (isHistoryTrendOpen) {
                        closeHistoryTrend();
                        return;
                      }
                      void openHistoryTrend();
                    }}
                  >
                    <BarChart3 className="h-4 w-4" />
                    {t('home.historyTrend')}
                  </Button>
                  <Button
                    variant="home-action-ai"
                    size="sm"
                    disabled={selectedReport.meta.id === undefined}
                    onClick={openMarkdownDrawer}
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    {t('home.fullReport')}
                  </Button>
                </div>
                {/* 历史趋势抽屉 或 报告摘要展示 */}
                {isHistoryTrendOpen ? (
                  <StockHistoryTrendDrawer
                    key={`stock-history-${selectedReport.meta.id}`}
                    report={selectedReport}
                    items={stockHistoryItems}
                    total={stockHistoryTotal}
                    hasMore={stockHistoryHasMore}
                    isLoading={isLoadingStockHistory}
                    isLoadingMore={isLoadingMoreStockHistory}
                    error={stockHistoryError}
                    filters={stockHistoryFilters}
                    onClose={closeHistoryTrend}
                    onRangeChange={(range) => void setStockHistoryRange(range)}
                    onLoadMore={() => void loadMoreStockHistory()}
                    onSelectRecord={(recordId) => void selectHistoryItem(recordId)}
                    onRetry={() => void openHistoryTrend()}
                  />
                ) : (
                  <ReportSummary
                    data={selectedReport}
                    isHistory
                    onOpenRunFlow={openHistoryRunFlow}
                    watchlist={{
                      isInWatchlist: watchlistState.isInWatchlist,
                      onToggle: watchlistState.toggleWatchlist,
                      isActioning: watchlistState.isActioning,
                      actionMessage: watchlistState.actionMessage,
                    }}
                  />
                )}
              </div>
            ) : !marketReviewReport ? (
              /* ===== 空状态：引导用户开始分析 ===== */
              <div className="flex h-full items-center justify-center">
                <EmptyState
                  title={t('home.startAnalysisTitle')}
                  description={t('home.startAnalysisDescription')}
                  className="max-w-xl border-dashed"
                  icon={(
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  )}
                />
              </div>
            ) : null}
          </section>
        </div>
      </div>

      {/* ===== Markdown 全文报告抽屉 ===== */}
      {markdownDrawerOpen && selectedReport?.meta.id ? (
        <ReportMarkdownDrawer
          key={selectedReport.meta.id}
          recordId={selectedReport.meta.id}
          stockName={selectedReport.meta.stockName || ''}
          stockCode={selectedReport.meta.stockCode}
          reportLanguage={reportLanguage}
          onClose={closeMarkdownDrawer}
        />
      ) : null}

      {/* ===== 运行流程抽屉 ===== */}
      {runFlowDrawer.open ? (
        <Drawer
          isOpen={runFlowDrawer.open}
          onClose={closeRunFlowDrawer}
          title={t('runFlow.drawerTitle')}
          width="max-w-[96vw]"
          zIndex={80}
        >
          <RunFlowPanel
            key={`${runFlowDrawer.source.type}-${runFlowDrawer.source.type === 'task' ? runFlowDrawer.source.taskId : runFlowDrawer.source.recordId}`}
            source={runFlowDrawer.source}
            title={runFlowDrawer.title}
          />
        </Drawer>
      ) : null}

    </div>
  );
};

export default HomePage;
