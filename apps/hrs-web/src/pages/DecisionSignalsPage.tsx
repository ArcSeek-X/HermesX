/**
 * @file DecisionSignalsPage.tsx
 * @fileoverview 决策信号页面，提供决策信号的列表筛选、最新信号查看、
 *               时间线浏览、信号详情抽屉、状态管理、反馈提交、
 *               重评估预览与持久化等完整功能。
 *
 * 主要功能：
 * - 多维度筛选信号列表（市场、股票、动作、阶段、来源、状态等）
 * - 按股票上下文查看最新信号与历史时间线
 * - 信号详情抽屉展示完整信息（含 outcome、feedback）
 * - 信号状态管理（关闭 / 作废 / 归档）
 * - 用户反馈提交（useful / not_useful 等）
 * - 重评估预览与持久化（保守 / 均衡 / 激进策略）
 * - 全局命中统计与策略校准展示
 *
 * 核心依赖：
 * - decisionSignalsApi：决策信号 CRUD 接口
 * - historyApi：历史记录接口（用于生成股票候选）
 * - useStockIndex：股票索引 Hook（用于热门候选）
 * - useUiLanguage：UI 语言上下文（国际化）
 * - usePreference：用户偏好持久化 Hook（localStorage 缓存策略偏好）
 * @module pages
 */
import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, BarChart3, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import {
  decisionSignalsApi,
  getDecisionSignalReassessBlockedError,
} from '../api/decisionSignals'; // 决策信号 API 接口
import { getParsedApiError, type ParsedApiError } from '../api/error'; // API 错误解析工具
import { historyApi } from '../api/history'; // 历史记录 API
import {
  ApiErrorAlert,
  AppPage,
  Card,
  ConfirmDialog,
  Drawer,
  EmptyState,
  InlineAlert,
  PageHeader,
  Pagination,
} from '../components/common'; // 通用 UI 组件
import {
  DecisionSignalCard,
  DecisionSignalDetails,
} from '../components/decision-signals/DecisionSignalDisplay'; // 决策信号展示组件
import { DecisionSignalProfileCalibration } from '../components/decision-signals/DecisionSignalProfileCalibration'; // 策略校准展示
import { DecisionSignalTimeline } from '../components/decision-signals/DecisionSignalTimeline'; // 时间线组件
import { StockAutocomplete } from '../components/StockAutocomplete'; // 股票自动补全输入
import { useUiLanguage } from '../contexts/UiLanguageContext'; // UI 语言上下文
import { useStockIndex } from '../hooks/useStockIndex'; // 股票索引 Hook
import { usePreference } from '../hooks/usePreference'; // 用户偏好持久化 Hook
import type { UiTextKey } from '../i18n/uiText'; // UI 文本键类型
import type { DecisionAction, MarketPhaseValue, StockBarItem } from '../types/analysis'; // 分析相关类型
import type {
  DecisionSignalItem,
  DecisionSignalFeedbackItem,
  DecisionSignalFeedbackValue,
  DecisionSignalListParams,
  DecisionSignalMarket,
  DecisionSignalOutcomeItem,
  DecisionSignalOutcomeStatsResponse,
  DecisionSignalReassessResponse,
  DecisionSignalReassessBlockedError,
  DecisionSignalSourceType,
  DecisionSignalStatus,
  DecisionProfile,
  DecisionProfileDisplay,
} from '../types/decisionSignals'; // 决策信号类型定义
import type { Market, StockIndexItem } from '../types/stockIndex'; // 股票索引类型
import { cn } from '../utils/cn'; // className 合并工具
import { buildDecisionActionLabelMap } from '../utils/decisionAction'; // 决策动作标签构建
import {
  getDecisionSignalMarketLabel,
  getDecisionSignalMarketPhaseLabel,
  getDecisionSignalSourceTypeLabel,
} from '../utils/decisionSignalLabels'; // 决策信号标签工具
import { getDecisionProfile } from '../utils/decisionSignalProfile'; // 决策策略解析
import { parseDecisionSignalDate } from '../utils/decisionSignalTime'; // 信号时间解析
import { areStockCodesEquivalent } from '../utils/stockCode'; // 股票代码等价判断

// 分页大小常量
const PAGE_SIZE = 20; // 列表分页每页条数
const TIMELINE_PAGE_SIZE = 100; // 时间线分页每页条数
const STOCK_CANDIDATE_LIMIT = 8; // 股票候选列表最大数量
const DAY_MS = 86400_000; // 一天的毫秒数，用于时间范围计算

// 列表筛选条件类型
type ListFilters = {
  market: '' | DecisionSignalMarket; // 市场筛选
  stockCode: string; // 股票代码筛选
  action: '' | DecisionAction; // 决策动作筛选
  marketPhase: '' | MarketPhaseValue; // 市场阶段筛选
  sourceType: '' | DecisionSignalSourceType; // 信号来源类型筛选
  sourceReportId: string; // 来源报告 ID 筛选
  status: '' | DecisionSignalStatus; // 信号状态筛选
};

// 时间线时间范围选项：30天 / 90天 / 180天
type TimelineRange = '30d' | '90d' | '180d';
// 时间线状态筛选：全部 / 仅活跃
type TimelineStatusFilter = 'all' | 'active';

// 时间线筛选条件类型
type TimelineFilters = {
  market: '' | DecisionSignalMarket; // 市场筛选
  range: TimelineRange; // 时间范围
  status: TimelineStatusFilter; // 状态筛选
  decisionProfile: '' | DecisionProfileDisplay; // 决策策略筛选
};

// 时间线市场来源：context 表示由股票上下文自动推断，user 表示用户手动选择
type TimelineMarketSource = 'context' | 'user' | null;

// 时间线筛选更新结果，包含新的筛选条件和市场来源
type TimelineFilterUpdate = {
  filters: TimelineFilters;
  marketSource: TimelineMarketSource;
};

// 已应用的时间线上下文，包含筛选条件和股票代码
type AppliedTimelineContext = TimelineFilters & {
  stockCode: string;
};

// 股票上下文类型，用于最新信号和时间线查询
type StockContext = {
  code: string; // 股票代码
  displayCode?: string; // 展示用代码（如带前缀）
  name?: string; // 股票名称
  market?: DecisionSignalMarket; // 市场
};

// 股票候选类型，包含来源标记（历史记录或热门股票）
type StockCandidate = StockContext & {
  source: 'history' | 'popular';
};

// 待确认的状态变更请求
type PendingStatusChange = {
  item: DecisionSignalItem; // 目标信号项
  status: Extract<DecisionSignalStatus, 'closed' | 'invalidated' | 'archived'>; // 目标状态
  message: string; // 确认提示消息
};

// 当前选中的信号，source 标记信号来源（列表/最新/时间线/持久化）
type SelectedSignal = {
  item: DecisionSignalItem;
  source: 'list' | 'latest' | 'timeline' | 'persisted';
};

/** 判断值是否为普通对象（非数组、非 null） */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// 市场选项列表
const MARKET_OPTIONS: DecisionSignalMarket[] = ['cn', 'hk', 'us', 'jp', 'kr', 'tw'];
// 决策动作选项列表
const ACTION_OPTIONS: DecisionAction[] = ['buy', 'add', 'hold', 'reduce', 'sell', 'watch', 'avoid', 'alert'];
// 市场阶段选项列表
const PHASE_OPTIONS: MarketPhaseValue[] = ['premarket', 'intraday', 'lunch_break', 'closing_auction', 'postmarket', 'non_trading', 'unknown'];
// 信号来源类型选项列表
const SOURCE_OPTIONS: DecisionSignalSourceType[] = ['analysis', 'agent', 'alert', 'market_review', 'manual'];
// 信号状态选项列表
const STATUS_OPTIONS: DecisionSignalStatus[] = ['active', 'expired', 'invalidated', 'closed', 'archived'];

// 可执行的状态操作列表：关闭 / 作废 / 归档
const STATUS_ACTIONS: Array<PendingStatusChange['status']> = ['closed', 'invalidated', 'archived'];
// 重评估支持的策略列表
const REASSESS_PROFILES: DecisionProfile[] = ['conservative', 'balanced', 'aggressive'];

// 信号状态对应的 UI 文本键映射
const STATUS_LABEL_KEYS: Record<DecisionSignalStatus, UiTextKey> = {
  active: 'decisionSignals.active',
  expired: 'decisionSignals.expired',
  invalidated: 'decisionSignals.invalidated',
  closed: 'decisionSignals.closed',
  archived: 'decisionSignals.archived',
};

// 状态操作按钮对应的 UI 文本键映射
const STATUS_ACTION_LABEL_KEYS: Record<PendingStatusChange['status'], UiTextKey> = {
  closed: 'decisionSignals.close',
  invalidated: 'decisionSignals.invalidate',
  archived: 'decisionSignals.archive',
};

// 状态操作确认弹窗对应的 UI 文本键映射
const STATUS_ACTION_CONFIRM_KEYS: Record<PendingStatusChange['status'], UiTextKey> = {
  closed: 'decisionSignals.closeConfirm',
  invalidated: 'decisionSignals.invalidateConfirm',
  archived: 'decisionSignals.archiveConfirm',
};

// 列表筛选默认值（默认只看活跃信号）
const DEFAULT_LIST_FILTERS: ListFilters = {
  market: '',
  stockCode: '',
  action: '',
  marketPhase: '',
  sourceType: '',
  sourceReportId: '',
  status: 'active',
};

// 时间线筛选默认值（默认 90 天范围、全部状态）
const DEFAULT_TIMELINE_FILTERS: TimelineFilters = {
  market: '',
  range: '90d',
  status: 'all',
  decisionProfile: '',
};

// 时间范围对应的天数映射
const TIMELINE_RANGE_DAYS: Record<TimelineRange, number> = {
  '30d': 30,
  '90d': 90,
  '180d': 180,
};

/**
 * 解析来源报告 ID 字符串为数字。
 * 仅接受正整数字符串，无效输入返回 undefined。
 * @param value - 用户输入的来源报告 ID 字符串
 * @returns 解析后的正整数，或 undefined
 */
function parseSourceReportId(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
}

/**
 * 从 URL 查询参数中解析初始筛选条件。
 * 支持 sourceReportId 和 source_report_id 两种参数名。
 * @param search - URL 查询字符串
 * @returns 初始列表筛选条件
 */
function getInitialFilters(search = typeof window === 'undefined' ? '' : window.location.search): ListFilters {
  const params = new URLSearchParams(search);
  const sourceReportId = parseSourceReportId(params.get('sourceReportId') ?? params.get('source_report_id') ?? '');
  if (sourceReportId === undefined) return DEFAULT_LIST_FILTERS;
  return {
    ...DEFAULT_LIST_FILTERS,
    sourceReportId: String(sourceReportId),
  };
}

/**
 * 将筛选条件转换为 API 请求参数。
 * 当存在来源报告 ID 时，使用来源报告 ID 模式查询；
 * 否则使用常规多条件筛选模式。
 * @param filters - 筛选条件
 * @param page - 当前页码
 * @returns API 请求参数对象
 */
function toListParams(filters: ListFilters, page: number): DecisionSignalListParams {
  const sourceReportId = parseSourceReportId(filters.sourceReportId);
  if (sourceReportId !== undefined) {
    return {
      sourceReportId,
      sourceType: 'analysis',
      page,
      pageSize: PAGE_SIZE,
    };
  }

  return {
    market: filters.market || undefined,
    stockCode: filters.stockCode.trim() || undefined,
    action: filters.action || undefined,
    marketPhase: filters.marketPhase || undefined,
    sourceType: filters.sourceType || undefined,
    status: filters.status || undefined,
    page,
    pageSize: PAGE_SIZE,
  };
}

/**
 * 刷新"最新信号"来源的选中项。
 * 当最新信号列表重新加载后，尝试在新的列表中找到当前选中的信号并更新。
 * @param current - 当前选中的信号
 * @param latestItems - 最新的信号列表
 * @returns 更新后的选中信号，或 null（如果已不存在）
 */
function refreshLatestSelection(
  current: SelectedSignal | null,
  latestItems: DecisionSignalItem[],
): SelectedSignal | null {
  if (!current || current.source !== 'latest') return current;
  const refreshed = latestItems.find((item) => item.id === current.item.id);
  return refreshed ? { source: 'latest', item: refreshed } : null;
}

/**
 * 刷新"时间线"来源的选中项。
 * 当时间线列表重新加载后，尝试在新的列表中找到当前选中的信号并更新。
 * @param current - 当前选中的信号
 * @param timelineItems - 时间线信号列表
 * @returns 更新后的选中信号，或 null（如果已不存在）
 */
function refreshTimelineSelection(
  current: SelectedSignal | null,
  timelineItems: DecisionSignalItem[],
): SelectedSignal | null {
  if (!current || current.source !== 'timeline') return current;
  const refreshed = timelineItems.find((item) => item.id === current.item.id);
  return refreshed ? { source: 'timeline', item: refreshed } : null;
}

/**
 * 将市场标识标准化为决策信号市场类型。
 * 处理 BSE -> cn、INDEX/ETF/UNKNOWN -> undefined 等特殊映射。
 * @param value - 原始市场标识
 * @returns 标准化后的市场类型，或 undefined
 */
function normalizeDecisionSignalMarket(value: unknown): DecisionSignalMarket | undefined {
  const market = String(value ?? '').trim().toUpperCase();
  if (!market || market === 'INDEX' || market === 'ETF' || market === 'UNKNOWN') return undefined;
  if (market === 'CN' || market === 'BSE') return 'cn';
  if (market === 'HK') return 'hk';
  if (market === 'US') return 'us';
  if (market === 'JP') return 'jp';
  if (market === 'KR') return 'kr';
  if (market === 'TW') return 'tw';
  if (MARKET_OPTIONS.includes(market.toLowerCase() as DecisionSignalMarket)) {
    return market.toLowerCase() as DecisionSignalMarket;
  }
  return undefined;
}

/** 生成股票候选的唯一标识键（市场:代码 或 仅代码），用于去重 */
function getCandidateKey(candidate: Pick<StockCandidate, 'code' | 'market'>): string {
  const code = candidate.code.trim().toUpperCase();
  return candidate.market ? `${candidate.market}:${code}` : code;
}

/** 将历史记录中的 StockBarItem 转换为股票候选项，过滤掉 MARKET 等非个股条目 */
function toHistoryCandidate(item: StockBarItem): StockCandidate | null {
  const code = String(item.stockCode || '').trim();
  if (!code || code.toUpperCase() === 'MARKET') return null;
  return {
    code,
    displayCode: code,
    name: item.stockName || undefined,
    market: normalizeDecisionSignalMarket(item.marketPhaseSummary?.market),
    source: 'history',
  };
}

/**
 * 从股票索引中提取热门股票候选列表。
 * 按 popularity 降序排列，去重后截取指定数量。
 * @param index - 股票索引列表
 * @param limit - 最大候选数量
 * @returns 热门股票候选列表
 */
function toPopularCandidates(index: StockIndexItem[], limit = STOCK_CANDIDATE_LIMIT): StockCandidate[] {
  const candidates: StockCandidate[] = [];
  const seen = new Set<string>();
  const sorted = [...index]
    .filter((item) => item.active && item.assetType === 'stock')
    .sort((left, right) => (right.popularity ?? 0) - (left.popularity ?? 0));

  for (const item of sorted) {
    const market = normalizeDecisionSignalMarket(item.market);
    const candidate: StockCandidate = {
      code: item.canonicalCode,
      displayCode: item.displayCode,
      name: item.nameZh,
      market,
      source: 'popular',
    };
    const key = getCandidateKey(candidate);
    if (seen.has(key)) continue;
    seen.add(key);
    candidates.push(candidate);
    if (candidates.length >= limit) break;
  }

  return candidates;
}

/**
 * 将时间线筛选条件转换为 API 请求参数。
 * 根据时间范围计算 createdFrom 和 createdTo 时间戳。
 * @param filters - 时间线筛选条件
 * @param stockCode - 股票代码
 * @returns API 请求参数对象
 */
function toTimelineParams(filters: TimelineFilters, stockCode: string): DecisionSignalListParams {
  const days = TIMELINE_RANGE_DAYS[filters.range];
  const createdTo = new Date();
  const createdFrom = new Date(createdTo.getTime() - days * DAY_MS);
  return {
    market: filters.market || undefined,
    stockCode,
    createdFrom: createdFrom.toISOString(),
    createdTo: createdTo.toISOString(),
    status: filters.status === 'active' ? 'active' : undefined,
    decisionProfile: filters.decisionProfile || undefined,
    page: 1,
    pageSize: TIMELINE_PAGE_SIZE,
  };
}

/**
 * 将信号项插入或更新到列表中（upsert 操作）。
 * 如果已存在同 ID 的信号则替换，然后按创建时间降序排序。
 * @param current - 当前信号列表
 * @param item - 要插入或更新的信号
 * @param limit - 可选，限制列表最大长度
 * @returns 更新后的信号列表
 */
function upsertDecisionSignal(
  current: DecisionSignalItem[],
  item: DecisionSignalItem,
  limit?: number,
): DecisionSignalItem[] {
  const next = [item, ...current.filter((candidate) => candidate.id !== item.id)];
  next.sort((left, right) => {
    const leftTime = parseDecisionSignalDate(left.createdAt)?.getTime() ?? Number.NEGATIVE_INFINITY;
    const rightTime = parseDecisionSignalDate(right.createdAt)?.getTime() ?? Number.NEGATIVE_INFINITY;
    return rightTime - leftTime || right.id - left.id;
  });
  return limit ? next.slice(0, limit) : next;
}

/** 判断信号项是否匹配指定的股票上下文（代码等价且市场一致） */
function itemMatchesStockContext(item: DecisionSignalItem, context: StockContext): boolean {
  return areStockCodesEquivalent(item.stockCode, context.code)
    && (!context.market || item.market === context.market);
}

/**
 * 判断信号项是否匹配已应用的时间线上下文。
 * 检查股票代码、市场、状态、策略以及创建时间是否在时间范围内。
 * @param item - 待判断的信号项
 * @param context - 已应用的时间线上下文
 * @param now - 当前时间戳，默认为 Date.now()
 * @returns 是否匹配
 */
function itemMatchesAppliedTimeline(
  item: DecisionSignalItem,
  context: AppliedTimelineContext,
  now = Date.now(),
): boolean {
  if (!areStockCodesEquivalent(item.stockCode, context.stockCode)) return false;
  if (context.market && item.market !== context.market) return false;
  if (context.status === 'active' && item.status !== 'active') return false;
  if (context.decisionProfile && getDecisionProfile(item) !== context.decisionProfile) return false;
  const createdAt = parseDecisionSignalDate(item.createdAt)?.getTime();
  if (createdAt === undefined) return false;
  return createdAt >= now - TIMELINE_RANGE_DAYS[context.range] * DAY_MS && createdAt <= now;
}

function isSameStockContext(
  previousContext: StockContext | null,
  nextContext: StockContext,
): boolean {
  return previousContext?.code.trim().toUpperCase() === nextContext.code.trim().toUpperCase()
    && previousContext?.market === nextContext.market;
}

function buildNextTimelineFilters(
  currentFilters: TimelineFilters,
  previousContext: StockContext | null,
  nextContext: StockContext,
  marketSource: TimelineMarketSource,
): TimelineFilterUpdate {
  if (isSameStockContext(previousContext, nextContext)) {
    return { filters: currentFilters, marketSource };
  }
  if (nextContext.market) {
    return {
      filters: { ...currentFilters, market: nextContext.market },
      marketSource: 'context',
    };
  }
  if (marketSource === 'context') {
    return {
      filters: { ...currentFilters, market: '' },
      marketSource: null,
    };
  }
  return { filters: currentFilters, marketSource };
}

function draftMatchesStockContext(draft: string, context: StockContext | null): context is StockContext {
  if (!context) return false;
  const normalizedDraft = draft.trim().toUpperCase();
  if (!normalizedDraft) return false;
  return normalizedDraft === context.code.trim().toUpperCase()
    || normalizedDraft === String(context.displayCode ?? '').trim().toUpperCase();
}

function formatStatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return Number(value).toFixed(2).replace(/\.?0+$/, '');
}

function formatStatPercent(value: number | null | undefined): string {
  const formatted = formatStatNumber(value);
  return formatted === '-' ? formatted : `${formatted}%`;
}

/**
 * 决策信号页面主组件。
 *
 * 管理三个数据视图：
 * 1. 信号列表（多条件筛选 + 分页）
 * 2. 最新信号（按股票上下文查询最近 5 条）
 * 3. 时间线（按股票上下文 + 时间范围查询历史信号）
 *
 * 同时提供信号详情抽屉（含 outcome、feedback、状态操作）、
 * 重评估预览与持久化、全局命中统计等功能。
 */
const DecisionSignalsPage: React.FC = () => {
  const { t } = useUiLanguage();
  const actionLabels = useMemo(() => buildDecisionActionLabelMap(t), [t]); // 决策动作标签映射（如 buy -> "买入"）
  const { index: stockIndex } = useStockIndex(); // 股票索引（用于热门候选列表）

  // ===== 列表筛选与分页状态 =====
  const [filters, setFilters] = useState<ListFilters>(() => getInitialFilters()); // 当前编辑中的筛选条件（尚未提交）
  const [appliedFilters, setAppliedFilters] = useState<ListFilters>(() => getInitialFilters()); // 已提交生效的筛选条件
  const [page, setPage] = useState(1); // 当前页码
  const [items, setItems] = useState<DecisionSignalItem[]>([]); // 当前页的信号列表
  const [total, setTotal] = useState(0); // 信号总条数（用于分页计算）
  const [loading, setLoading] = useState(true); // 列表是否正在加载
  const [error, setError] = useState<ParsedApiError | null>(null); // 列表加载错误

  // ===== 信号详情抽屉状态 =====
  const [selected, setSelected] = useState<SelectedSignal | null>(null); // 当前选中的信号（来源标记：列表/最新/时间线/持久化）
  const [pendingStatus, setPendingStatus] = useState<PendingStatusChange | null>(null); // 待确认的状态变更请求
  const [statusUpdating, setStatusUpdating] = useState(false); // 状态变更是否进行中

  // ===== 全局命中统计状态 =====
  const [outcomeStats, setOutcomeStats] = useState<DecisionSignalOutcomeStatsResponse | null>(null); // 全局命中统计数据
  const [statsLoading, setStatsLoading] = useState(true); // 统计是否正在加载
  const [statsError, setStatsError] = useState<ParsedApiError | null>(null); // 统计加载错误

  // ===== 股票上下文与候选列表状态 =====
  const [stockDraft, setStockDraft] = useState(''); // 股票输入框草稿值
  const [activeStockContext, setActiveStockContext] = useState<StockContext | null>(null); // 当前活跃的股票上下文
  const [historyCandidates, setHistoryCandidates] = useState<StockCandidate[]>([]); // 历史记录中的股票候选列表
  const [historyCandidatesLoaded, setHistoryCandidatesLoaded] = useState(false); // 历史候选是否已加载完毕

  // ===== 最新信号视图状态 =====
  const [latestItems, setLatestItems] = useState<DecisionSignalItem[]>([]); // 最新信号列表
  const [latestSearched, setLatestSearched] = useState(false); // 是否已执行过最新信号查询
  const [latestLoading, setLatestLoading] = useState(false); // 最新信号是否正在加载
  const [latestError, setLatestError] = useState<ParsedApiError | null>(null); // 最新信号加载错误

  // ===== 时间线视图状态 =====
  const [timelineFilters, setTimelineFilters] = useState<TimelineFilters>(DEFAULT_TIMELINE_FILTERS); // 时间线筛选条件
  const [appliedTimelineContext, setAppliedTimelineContext] = useState<AppliedTimelineContext | null>(null); // 已生效的时间线上下文
  const [timelineItems, setTimelineItems] = useState<DecisionSignalItem[]>([]); // 时间线信号列表
  const [timelineSearched, setTimelineSearched] = useState(false); // 是否已执行过时间线查询
  const [timelineLoading, setTimelineLoading] = useState(false); // 时间线是否正在加载
  const [timelineError, setTimelineError] = useState<ParsedApiError | null>(null); // 时间线加载错误
  const [timelineTruncated, setTimelineTruncated] = useState(false); // 时间线结果是否被截断（总数超过返回数量）

  // ===== 信号详情子数据状态（outcome 和 feedback） =====
  const [selectedOutcomes, setSelectedOutcomes] = useState<DecisionSignalOutcomeItem[]>([]); // 选中信号的实际表现（命中/未命中）
  const [selectedOutcomesLoading, setSelectedOutcomesLoading] = useState(false); // 表现数据是否正在加载
  const [selectedOutcomesError, setSelectedOutcomesError] = useState<ParsedApiError | null>(null); // 表现数据加载错误
  const [selectedFeedback, setSelectedFeedback] = useState<DecisionSignalFeedbackItem | null>(null); // 选中信号的用户反馈
  const [selectedFeedbackLoading, setSelectedFeedbackLoading] = useState(false); // 反馈数据是否正在加载
  const [selectedFeedbackError, setSelectedFeedbackError] = useState<ParsedApiError | null>(null); // 反馈数据加载错误
  const [feedbackSaving, setFeedbackSaving] = useState(false); // 反馈是否正在保存

  // ===== 重评估（reassess）状态 =====
  // L4 缓存：reassess 配置偏好（localStorage 永久保存）
  const [reassessProfile, setReassessProfile] = usePreference<DecisionProfile>('decision-signals-reassess-profile', 'balanced');
  const [reassessResponse, setReassessResponse] = useState<DecisionSignalReassessResponse | null>(null); // 重评估响应（预览或持久化结果）
  const [reassessLoading, setReassessLoading] = useState(false); // 重评估预览是否正在加载
  const [reassessPersisting, setReassessPersisting] = useState(false); // 重评估持久化是否进行中
  const [reassessPersistConfirm, setReassessPersistConfirm] = useState(false); // 是否显示持久化确认弹窗
  const [reassessPersistBlocked, setReassessPersistBlocked] = useState<DecisionSignalReassessBlockedError | null>(null); // 持久化被拦截的错误信息
  const [reassessError, setReassessError] = useState<ParsedApiError | null>(null); // 重评估错误

  // ===== 请求竞态防护 Refs =====
  // 每个数据源维护独立的 requestId，确保只有最新请求的结果会更新状态
  const requestIdRef = useRef(0); // 列表请求 ID
  const statsRequestIdRef = useRef(0); // 统计请求 ID
  const latestRequestIdRef = useRef(0); // 最新信号请求 ID
  const timelineRequestIdRef = useRef(0); // 时间线请求 ID
  const detailRequestIdRef = useRef(0); // 详情子数据请求 ID
  const reassessRequestIdRef = useRef(0); // 重评估请求 ID
  const selectedSignalIdRef = useRef<number | null>(null); // 当前选中信号 ID（防止反馈响应竞态）
  const statusUpdateInFlightRef = useRef(false); // 状态更新是否正在进行（防止重复触发）
  const timelineMarketSourceRef = useRef<TimelineMarketSource>(null); // 时间线市场筛选来源（context 自动推断 / user 手动选择）

  // 热门股票候选列表：从股票索引按 popularity 降序提取，缓存依赖 stockIndex
  const popularCandidates = useMemo(
    () => toPopularCandidates(stockIndex, STOCK_CANDIDATE_LIMIT),
    [stockIndex],
  );
  // 股票候选列表：优先使用历史记录候选，无历史时回退到热门候选
  const stockCandidates = historyCandidates.length > 0 ? historyCandidates : popularCandidates;
  // 候选模式标记：用于 UI 展示"最近浏览"或"热门"标题
  const stockCandidateMode: 'history' | 'popular' | 'empty' = historyCandidates.length > 0
    ? 'history'
    : stockCandidates.length > 0
      ? 'popular'
      : 'empty';

  // 设置页面标题（国际化）
  useEffect(() => {
    document.title = t('decisionSignals.pageTitle');
  }, [t]);

  // 组件挂载时加载历史记录中的股票候选列表（从 historyApi 获取最近浏览的股票）
  useEffect(() => {
    let mounted = true;
    void historyApi.getStockBarList({ limit: STOCK_CANDIDATE_LIMIT })
      .then((response) => {
        if (!mounted) return;
        // 遍历历史记录，转换为股票候选并去重
        const nextCandidates: StockCandidate[] = [];
        const seen = new Set<string>();
        for (const item of response.items) {
          const candidate = toHistoryCandidate(item);
          if (!candidate) continue;
          const key = getCandidateKey(candidate);
          if (seen.has(key)) continue;
          seen.add(key);
          nextCandidates.push(candidate);
          if (nextCandidates.length >= STOCK_CANDIDATE_LIMIT) break;
        }
        setHistoryCandidates(nextCandidates);
      })
      .catch(() => {
        if (mounted) setHistoryCandidates([]);
      })
      .finally(() => {
        if (mounted) setHistoryCandidatesLoaded(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  /**
   * 加载指定页码的信号列表。
   * 通过 requestId 防止竞态，确保只有最新请求的结果会更新状态。
   * 如果请求的页码超出总页数，自动回退到最后一页。
   * @param nextPage - 要加载的页码
   */
  const loadSignalsForPage = useCallback(async (nextPage: number) => {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);
    try {
      const response = await decisionSignalsApi.list(toListParams(appliedFilters, nextPage));
      if (requestIdRef.current !== requestId) return; // 竞态保护：丢弃过期响应
      // 页码越界保护：如果请求页码超出范围，回退到最后一页
      const lastPage = Math.max(1, Math.ceil(response.total / PAGE_SIZE));
      if (response.total > 0 && nextPage > lastPage) {
        setPage(lastPage);
        return;
      }
      setItems(response.items);
      setTotal(response.total);
      setError(null);
      // 尝试在新的列表中刷新当前选中的信号（来源为 list 时）
      setSelected((current) => {
        if (!current) return current;
        if (current.source !== 'list') return current;
        const refreshed = response.items.find((item) => item.id === current.item.id);
        return refreshed ? { source: 'list', item: refreshed } : null;
      });
    } catch (err) {
      if (requestIdRef.current !== requestId) return;
      setError(getParsedApiError(err));
      setItems([]);
      setTotal(0);
      setSelected((current) => (current?.source === 'list' ? null : current));
    } finally {
      if (requestIdRef.current === requestId) {
        setLoading(false);
      }
    }
  }, [appliedFilters]);

  /** 加载当前页码的信号列表（loadSignalsForPage 的便捷封装） */
  const loadSignals = useCallback(async () => {
    await loadSignalsForPage(page);
  }, [loadSignalsForPage, page]);

  /**
   * 加载全局命中统计数据。
   * 统计所有已复盘信号的总数、命中率、命中/未命中/无法判断的数量。
   */
  const loadOutcomeStats = useCallback(async () => {
    const requestId = statsRequestIdRef.current + 1;
    statsRequestIdRef.current = requestId;
    setStatsLoading(true);
    try {
      const response = await decisionSignalsApi.getOutcomeStats();
      if (statsRequestIdRef.current !== requestId) return; // 竞态保护
      setOutcomeStats(response);
      setStatsError(null);
    } catch (err) {
      if (statsRequestIdRef.current !== requestId) return;
      setOutcomeStats(null);
      setStatsError(getParsedApiError(err));
    } finally {
      if (statsRequestIdRef.current === requestId) {
        setStatsLoading(false);
      }
    }
  }, []);

  // appliedFilters 或 page 变化时重新加载信号列表
  useEffect(() => {
    void loadSignals();
    return () => {
      requestIdRef.current += 1; // 卸载时使所有进行中的请求失效
    };
  }, [loadSignals]);

  // 组件挂载时加载全局命中统计
  useEffect(() => {
    void loadOutcomeStats();
    return () => {
      statsRequestIdRef.current += 1;
    };
  }, [loadOutcomeStats]);

  // 组件卸载时使最新信号和时间线请求失效（防止内存泄漏和状态更新竞态）
  useEffect(() => () => {
    latestRequestIdRef.current += 1;
  }, []);

  useEffect(() => () => {
    timelineRequestIdRef.current += 1;
  }, []);

  // 选中信号变化时，并行加载其 outcome（实际表现）和 feedback（用户反馈）数据
  useEffect(() => {
    selectedSignalIdRef.current = selected?.item.id ?? null;
    // 未选中信号时，清空所有详情子数据状态
    if (!selected) {
      detailRequestIdRef.current += 1;
      setSelectedOutcomes([]);
      setSelectedOutcomesError(null);
      setSelectedFeedback(null);
      setSelectedFeedbackError(null);
      setSelectedOutcomesLoading(false);
      setSelectedFeedbackLoading(false);
      return;
    }

    // 发起并行请求：outcome 和 feedback 互不依赖
    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;
    setSelectedOutcomesLoading(true);
    setSelectedFeedbackLoading(true);
    setSelectedOutcomesError(null);
    setSelectedFeedbackError(null);

    // 加载信号的实际表现（命中/未命中/无法判断）
    void decisionSignalsApi.getSignalOutcomes(selected.item.id)
      .then((response) => {
        if (detailRequestIdRef.current !== requestId) return; // 竞态保护
        setSelectedOutcomes(response.items);
      })
      .catch((err) => {
        if (detailRequestIdRef.current !== requestId) return;
        setSelectedOutcomes([]);
        setSelectedOutcomesError(getParsedApiError(err));
      })
      .finally(() => {
        if (detailRequestIdRef.current === requestId) {
          setSelectedOutcomesLoading(false);
        }
      });

    // 加载信号的用户反馈
    void decisionSignalsApi.getFeedback(selected.item.id)
      .then((response) => {
        if (detailRequestIdRef.current !== requestId) return; // 竞态保护
        setSelectedFeedback(response);
      })
      .catch((err) => {
        if (detailRequestIdRef.current !== requestId) return;
        setSelectedFeedback(null);
        setSelectedFeedbackError(getParsedApiError(err));
      })
      .finally(() => {
        if (detailRequestIdRef.current === requestId) {
          setSelectedFeedbackLoading(false);
        }
      });
  }, [selected]);

  // ===== 重评估上下文派生值 =====
  const appliedSourceReportId = parseSourceReportId(appliedFilters.sourceReportId); // 已提交筛选中的来源报告 ID
  const selectedSourceReportId = selected?.item.sourceReportId ?? undefined; // 选中信号的来源报告 ID
  // 重评估使用的来源报告 ID：优先使用选中信号的，其次使用筛选条件的
  const reassessSourceReportId = selected ? selectedSourceReportId : appliedSourceReportId;
  // 重评估上下文键：当来源报告 ID 或策略变化时触发重评估状态重置
  const reassessContextKey = [
    reassessSourceReportId ?? '',
    reassessProfile,
  ].join(':');

  // 来源报告 ID 或重评估策略变化时，重置重评估相关状态
  useEffect(() => {
    reassessRequestIdRef.current += 1;
    setReassessResponse(null);
    setReassessError(null);
    setReassessLoading(false);
    setReassessPersisting(false);
    setReassessPersistConfirm(false);
    setReassessPersistBlocked(null);
  }, [reassessContextKey]);

  /**
   * 执行重评估预览（不持久化）。
   * 根据当前选中的策略（保守/均衡/激进）和来源报告 ID，
   * 向后端请求重评估预览结果，展示新的决策动作、得分、入场区间等。
   */
  const handleReassess = useCallback(async () => {
    if (!reassessSourceReportId) return;
    const requestId = reassessRequestIdRef.current + 1;
    reassessRequestIdRef.current = requestId;
    setReassessLoading(true);
    setReassessError(null);
    setReassessPersistBlocked(null);
    try {
      const response = await decisionSignalsApi.reassess({
        sourceReportId: reassessSourceReportId,
        decisionProfile: reassessProfile,
        persist: false, // 仅预览，不持久化
      });
      if (reassessRequestIdRef.current !== requestId) return; // 竞态保护
      setReassessResponse(response);
    } catch (err) {
      if (reassessRequestIdRef.current !== requestId) return;
      setReassessResponse(null);
      setReassessError(getParsedApiError(err));
    } finally {
      if (reassessRequestIdRef.current === requestId) {
        setReassessLoading(false);
      }
    }
  }, [reassessProfile, reassessSourceReportId]);

  /** 提交筛选条件：将编辑中的筛选条件应用到 appliedFilters 并重置到第一页 */
  const handleApplyFilters = (event: React.FormEvent) => {
    event.preventDefault();
    setAppliedFilters(filters);
    setPage(1);
  };

  /** 重置最新信号视图：清空列表、错误和选中状态 */
  const resetLatestView = useCallback(() => {
    latestRequestIdRef.current += 1; // 使进行中的请求失效
    setLatestItems([]);
    setLatestSearched(false);
    setLatestLoading(false);
    setLatestError(null);
    setSelected((current) => (current?.source === 'latest' ? null : current));
  }, []);

  /**
   * 根据股票上下文加载最新信号列表。
   * 查询指定股票最近 5 条信号，并尝试在结果中刷新当前选中信号。
   * @param context - 股票上下文（代码、市场）
   */
  const loadLatestForContext = useCallback(async (context: StockContext) => {
    const stockCode = context.code.trim();
    if (!stockCode) return;
    const requestId = latestRequestIdRef.current + 1;
    latestRequestIdRef.current = requestId;
    setLatestLoading(true);
    setLatestError(null);
    setLatestSearched(true);
    setLatestItems([]);
    setSelected((current) => (current?.source === 'latest' ? null : current));
    try {
      const response = await decisionSignalsApi.getLatest(stockCode, {
        market: context.market,
        limit: 5,
      });
      if (latestRequestIdRef.current !== requestId) return; // 竞态保护
      setLatestItems(response.items);
      // 尝试在新的列表中刷新当前选中的信号（来源为 latest 时）
      setSelected((current) => refreshLatestSelection(current, response.items));
    } catch (err) {
      if (latestRequestIdRef.current !== requestId) return;
      setLatestItems([]);
      setSelected((current) => refreshLatestSelection(current, []));
      setLatestError(getParsedApiError(err));
    } finally {
      if (latestRequestIdRef.current === requestId) {
        setLatestLoading(false);
      }
    }
  }, []);

  /** 重置时间线视图：清空列表、错误、截断标记和已应用上下文 */
  const resetTimelineView = useCallback(() => {
    timelineRequestIdRef.current += 1; // 使进行中的请求失效
    setTimelineItems([]);
    setTimelineSearched(false);
    setTimelineLoading(false);
    setTimelineError(null);
    setTimelineTruncated(false);
    setAppliedTimelineContext(null);
    setSelected((current) => (current?.source === 'timeline' ? null : current));
  }, []);

  /**
   * 根据股票上下文和时间线筛选条件加载时间线信号列表。
   * 按时间范围（30/90/180 天）查询指定股票的历史信号，
   * 并记录已应用的时间线上下文（用于后续乐观更新判断）。
   * @param context - 股票上下文（代码、市场）
   * @param filtersSnapshot - 时间线筛选条件快照
   */
  const loadTimelineForContext = useCallback(async (
    context: StockContext,
    filtersSnapshot: TimelineFilters,
  ) => {
    const stockCode = context.code.trim();
    if (!stockCode) return;
    const requestId = timelineRequestIdRef.current + 1;
    timelineRequestIdRef.current = requestId;
    setTimelineLoading(true);
    setTimelineError(null);
    setTimelineSearched(true);
    setTimelineItems([]);
    setTimelineTruncated(false);
    setAppliedTimelineContext(null);
    setSelected((current) => (current?.source === 'timeline' ? null : current));
    // 记录已应用的时间线上下文，用于后续判断新信号是否匹配
    const nextAppliedContext: AppliedTimelineContext = {
      ...filtersSnapshot,
      stockCode,
    };
    try {
      const response = await decisionSignalsApi.list(toTimelineParams(filtersSnapshot, stockCode));
      if (timelineRequestIdRef.current !== requestId) return; // 竞态保护
      setAppliedTimelineContext(nextAppliedContext);
      setTimelineItems(response.items);
      // 标记结果是否被截断（总数超过返回的条数）
      setTimelineTruncated(response.total > response.items.length);
      setSelected((current) => refreshTimelineSelection(current, response.items));
    } catch (err) {
      if (timelineRequestIdRef.current !== requestId) return;
      setTimelineItems([]);
      setTimelineTruncated(false);
      setSelected((current) => refreshTimelineSelection(current, []));
      setTimelineError(getParsedApiError(err));
    } finally {
      if (timelineRequestIdRef.current === requestId) {
        setTimelineLoading(false);
      }
    }
  }, []);

  const handlePersistReassess = useCallback(async () => {
    const preview = reassessResponse?.preview;
    const guardrail = preview && isRecord(preview.metadata.guardrail_result)
      ? preview.metadata.guardrail_result
      : null;
    if (!reassessSourceReportId || !preview || guardrail?.passed !== true) return;

    const requestId = reassessRequestIdRef.current + 1;
    reassessRequestIdRef.current = requestId;
    setReassessPersistConfirm(false);
    setReassessPersisting(true);
    setReassessError(null);
    setReassessPersistBlocked(null);
    try {
      const response = await decisionSignalsApi.reassess({
        sourceReportId: reassessSourceReportId,
        decisionProfile: reassessProfile,
        persist: true,
      });
      if (reassessRequestIdRef.current !== requestId) return;
      if (!response.item || !response.persistStatus) {
        throw new Error('DecisionSignal reassess persist response item and persist_status are required');
      }
      const authoritativeItem = response.item;
      const shouldOptimisticallyUpsert = response.persistStatus !== 'existing';
      setReassessResponse(response);
      setSelected((current) => (
        current
          ? { source: 'persisted', item: authoritativeItem }
          : null
      ));
      if (
        shouldOptimisticallyUpsert
        &&
        activeStockContext
        && authoritativeItem.status === 'active'
        && itemMatchesStockContext(authoritativeItem, activeStockContext)
      ) {
        setLatestItems((current) => upsertDecisionSignal(current, authoritativeItem, 5));
        void loadLatestForContext(activeStockContext);
      }
      if (
        shouldOptimisticallyUpsert
        &&
        appliedTimelineContext
        && itemMatchesAppliedTimeline(authoritativeItem, appliedTimelineContext)
      ) {
        setTimelineItems((current) => upsertDecisionSignal(current, authoritativeItem));
        void loadTimelineForContext(
          {
            code: appliedTimelineContext.stockCode,
            market: appliedTimelineContext.market || undefined,
          },
          appliedTimelineContext,
        );
      }
      void loadSignalsForPage(page);
    } catch (err) {
      if (reassessRequestIdRef.current !== requestId) return;
      const blocked = getDecisionSignalReassessBlockedError(err);
      if (blocked) {
        setReassessPersistBlocked(blocked);
        setReassessError(null);
      } else {
        setReassessError(getParsedApiError(err));
      }
    } finally {
      if (reassessRequestIdRef.current === requestId) {
        setReassessPersisting(false);
      }
    }
  }, [
    activeStockContext,
    appliedTimelineContext,
    loadLatestForContext,
    loadSignalsForPage,
    loadTimelineForContext,
    page,
    reassessProfile,
    reassessResponse,
    reassessSourceReportId,
  ]);

  const applyStockContext = useCallback((nextContext: StockContext) => {
    const nextTimeline = buildNextTimelineFilters(
      timelineFilters,
      activeStockContext,
      nextContext,
      timelineMarketSourceRef.current,
    );
    timelineMarketSourceRef.current = nextTimeline.marketSource;
    setActiveStockContext(nextContext);
    setStockDraft(nextContext.displayCode ?? nextContext.code);
    setTimelineFilters(nextTimeline.filters);
    void loadLatestForContext(nextContext);
    void loadTimelineForContext(nextContext, nextTimeline.filters);
  }, [activeStockContext, loadLatestForContext, loadTimelineForContext, timelineFilters]);

  const handleStockSubmit = useCallback((
    code: string,
    name?: string,
    _source?: 'manual' | 'autocomplete',
    metadata?: { market?: Market; displayCode?: string },
  ) => {
    const trimmedCode = code.trim();
    if (!trimmedCode) return;
    applyStockContext({
      code: trimmedCode,
      displayCode: metadata?.displayCode,
      name,
      market: normalizeDecisionSignalMarket(metadata?.market),
    });
  }, [applyStockContext]);

  const handleCandidateSelect = useCallback((candidate: StockCandidate) => {
    applyStockContext(candidate);
  }, [applyStockContext]);

  const handleStockFormSubmit = useCallback((code: string) => {
    if (draftMatchesStockContext(code, activeStockContext)) {
      applyStockContext(activeStockContext);
      return;
    }
    handleStockSubmit(code);
  }, [activeStockContext, applyStockContext, handleStockSubmit]);

  const handleClearStockContext = useCallback(() => {
    setStockDraft('');
    setActiveStockContext(null);
    timelineMarketSourceRef.current = null;
    setTimelineFilters((current) => ({ ...current, market: '' }));
    resetLatestView();
    resetTimelineView();
  }, [resetLatestView, resetTimelineView]);

  const handleTimelineSearch = useCallback((event: React.FormEvent) => {
    event.preventDefault();
    if (!activeStockContext) return;
    void loadTimelineForContext(activeStockContext, timelineFilters);
  }, [activeStockContext, loadTimelineForContext, timelineFilters]);

  const handleStatusUpdate = async () => {
    if (!pendingStatus || statusUpdateInFlightRef.current) return;
    statusUpdateInFlightRef.current = true;
    setStatusUpdating(true);
    try {
      const updated = await decisionSignalsApi.updateStatus(pendingStatus.item.id, {
        status: pendingStatus.status,
      });
      setPendingStatus(null);
      setLatestItems((current) => current.flatMap((item) => {
        if (item.id !== updated.id) return [item];
        return updated.status === 'active' ? [updated] : [];
      }));
      setTimelineItems((current) => current.flatMap((item) => {
        if (item.id !== updated.id) return [item];
        return appliedTimelineContext?.status === 'active' && updated.status !== 'active' ? [] : [updated];
      }));
      setSelected((current) => {
        if (!current || current.item.id !== updated.id) return current;
        if (current.source === 'latest') {
          return updated.status === 'active' ? { source: 'latest', item: updated } : null;
        }
        if (current.source === 'timeline') {
          return appliedTimelineContext?.status === 'active' && updated.status !== 'active'
            ? null
            : { source: 'timeline', item: updated };
        }
        if (current.source === 'persisted') {
          return { source: 'persisted', item: updated };
        }
        if (!parseSourceReportId(appliedFilters.sourceReportId) && appliedFilters.status && updated.status !== appliedFilters.status) return null;
        return { source: 'list', item: updated };
      });
      setError(null);
      await loadSignalsForPage(page);
      await loadOutcomeStats();
    } catch (err) {
      setError(getParsedApiError(err));
      setPendingStatus(null);
    } finally {
      setStatusUpdating(false);
      statusUpdateInFlightRef.current = false;
    }
  };

  const handleFeedbackSubmit = useCallback(async (feedbackValue: DecisionSignalFeedbackValue) => {
    if (!selected || feedbackSaving) return;
    const signalId = selected.item.id;
    setFeedbackSaving(true);
    try {
      const updated = await decisionSignalsApi.putFeedback(signalId, {
        feedbackValue,
        source: 'web',
      });
      if (selectedSignalIdRef.current !== signalId) return;
      setSelectedFeedback(updated);
      setSelectedFeedbackError(null);
    } catch (err) {
      if (selectedSignalIdRef.current !== signalId) return;
      setSelectedFeedbackError(getParsedApiError(err));
    } finally {
      setFeedbackSaving(false);
    }
  }, [feedbackSaving, selected]);

  const renderReassessPanel = () => {
    const preview = reassessResponse?.preview ?? null;
    const persistedItem = reassessResponse?.item ?? null;
    const persistStatus = reassessResponse?.persistStatus ?? null;
    const terminalExisting = persistStatus === 'existing' && persistedItem?.status !== 'active';
    const persistedAlertVariant = terminalExisting
      ? 'warning'
      : persistStatus === 'existing'
        ? 'info'
        : 'success';
    const persistedTitleKey: UiTextKey = terminalExisting
      ? 'decisionSignals.reassessPersistedTerminalTitle'
      : persistStatus === 'existing'
        ? 'decisionSignals.reassessPersistedExistingTitle'
        : persistStatus === 'refreshed'
          ? 'decisionSignals.reassessPersistedRefreshedTitle'
          : 'decisionSignals.reassessPersistedCreatedTitle';
    const persistedMessageKey: UiTextKey = terminalExisting
      ? 'decisionSignals.reassessPersistedTerminalExisting'
      : persistStatus === 'existing'
        ? 'decisionSignals.reassessPersistedExisting'
        : persistStatus === 'refreshed'
          ? 'decisionSignals.reassessPersistedRefreshed'
          : 'decisionSignals.reassessPersistedCreated';
    const metadata = preview?.metadata ?? {};
    const guardrail = isRecord(metadata.guardrail_result) ? metadata.guardrail_result : null;
    const rawAction = typeof guardrail?.raw_action === 'string' ? guardrail.raw_action : null;
    const finalAction = typeof guardrail?.final_action === 'string' ? guardrail.final_action : null;
    const passed = typeof guardrail?.passed === 'boolean' ? guardrail.passed : null;
    return (
      <div className="rounded-xl border border-border/60 bg-elevated/30 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">{t('decisionSignals.reassessTitle')}</h3>
            </div>
            <p className="mt-1 text-xs text-secondary-text">
              {reassessSourceReportId
                ? t('decisionSignals.reassessSource', { id: reassessSourceReportId })
                : t('decisionSignals.reassessUnsupported')}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <select
              className="input-surface input-focus-glow h-10 rounded-xl border bg-transparent px-3 text-sm"
              value={reassessProfile}
              onChange={(event) => setReassessProfile(event.target.value as DecisionProfile)}
              aria-label={t('decisionSignals.reassessProfile')}
              disabled={!reassessSourceReportId || reassessLoading || reassessPersisting}
            >
              {REASSESS_PROFILES.map((profile) => (
                <option key={profile} value={profile}>
                  {t(`decisionSignals.profile.${profile}` as UiTextKey)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary inline-flex h-10 items-center justify-center gap-2"
              onClick={() => void handleReassess()}
              disabled={!reassessSourceReportId || reassessLoading || reassessPersisting}
            >
              <RefreshCw className={cn('h-4 w-4', reassessLoading ? 'animate-spin' : '')} />
              {t('decisionSignals.reassessPreview')}
            </button>
          </div>
        </div>

        {!reassessSourceReportId ? (
          <InlineAlert
            className="mt-3"
            variant="warning"
            title={t('decisionSignals.reassessUnsupportedTitle')}
            message={t('decisionSignals.reassessUnsupported')}
          />
        ) : null}
        {reassessError ? <ApiErrorAlert className="mt-3" error={reassessError} /> : null}
        {reassessPersistBlocked ? (
          <div className="mt-3 space-y-2">
            <InlineAlert
              variant="danger"
              title={t('decisionSignals.reassessPersistBlockedTitle')}
              message={reassessPersistBlocked.blockedReason}
            />
            {reassessPersistBlocked.warnings.length ? (
              <ul className="list-disc space-y-1 pl-5 text-sm text-secondary-text">
                {reassessPersistBlocked.warnings.map((warning, index) => (
                  <li key={`${warning.code}-${index}`}>{warning.message || warning.code}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        {persistedItem ? (
          <InlineAlert
            className="mt-3"
            variant={persistedAlertVariant}
            title={t(persistedTitleKey)}
            message={t(
              persistedMessageKey,
              {
                id: persistedItem.id,
                status: t(STATUS_LABEL_KEYS[persistedItem.status]),
              },
            )}
          />
        ) : null}
        {preview ? (
          <div className="mt-4 space-y-3">
            {reassessResponse?.blockedReason ? (
              <InlineAlert
                variant="warning"
                title={t('decisionSignals.reassessBlockedTitle')}
                message={reassessResponse.blockedReason}
              />
            ) : null}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.action')}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{actionLabels[preview.action]}</p>
              </div>
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.score')}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{preview.score ?? '-'}</p>
              </div>
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.confidence')}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{preview.confidence ?? '-'}</p>
              </div>
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.horizon')}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{preview.horizon ?? '-'}</p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.entryRange')}</p>
                <p className="mt-1 text-sm text-foreground">
                  {preview.entryLow || preview.entryHigh
                    ? `${preview.entryLow ?? '-'} ~ ${preview.entryHigh ?? '-'}`
                    : '-'}
                </p>
              </div>
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.stopLoss')}</p>
                <p className="mt-1 text-sm text-foreground">{preview.stopLoss ?? '-'}</p>
              </div>
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.targetPrice')}</p>
                <p className="mt-1 text-sm text-foreground">{preview.targetPrice ?? '-'}</p>
              </div>
              <div className="rounded-lg border border-border/50 bg-background/40 p-3">
                <p className="text-xs text-secondary-text">{t('decisionSignals.reassessRawFinal')}</p>
                <p className="mt-1 text-sm text-foreground">{rawAction ?? '-'} {'->'} {finalAction ?? '-'}</p>
              </div>
            </div>
            <div className="space-y-2 text-sm text-secondary-text">
              {passed === false ? (
                <p className="font-medium text-warning">{t('decisionSignals.reassessBlockedNote')}</p>
              ) : null}
              {preview.invalidation ? <p><span className="text-foreground">{t('decisionSignals.invalidation')}:</span> {preview.invalidation}</p> : null}
              {preview.reason ? <p><span className="text-foreground">{t('decisionSignals.reason')}:</span> {preview.reason}</p> : null}
              {preview.riskSummary ? <p><span className="text-foreground">{t('decisionSignals.riskSummary')}:</span> {preview.riskSummary}</p> : null}
              {preview.watchConditions ? <p><span className="text-foreground">{t('decisionSignals.watchConditions')}:</span> {preview.watchConditions}</p> : null}
            </div>
            {reassessResponse?.warnings.length ? (
              <div className="rounded-lg border border-warning/30 bg-warning/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-warning">{t('decisionSignals.reassessWarnings')}</p>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-secondary-text">
                  {reassessResponse.warnings.map((warning, index) => (
                    <li key={`${warning.code}-${index}`}>{warning.message || warning.code}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {passed === true ? (
              <div className="flex justify-end">
                <button
                  type="button"
                  className="btn-primary inline-flex h-10 items-center justify-center gap-2"
                  onClick={() => setReassessPersistConfirm(true)}
                  disabled={reassessLoading || reassessPersisting}
                >
                  <ShieldCheck className="h-4 w-4" />
                  {reassessPersisting
                    ? t('decisionSignals.reassessPersisting')
                    : t('decisionSignals.reassessPersist')}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
        {persistedItem && reassessResponse?.warnings.length ? (
          <div className="mt-3 rounded-lg border border-warning/30 bg-warning/10 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-warning">{t('decisionSignals.reassessWarnings')}</p>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-secondary-text">
              {reassessResponse.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message || warning.code}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    );
  };

  const activeStockLabel = activeStockContext
    ? [
      activeStockContext.displayCode ?? activeStockContext.code,
      activeStockContext.name,
      activeStockContext.market,
    ].filter(Boolean).join(' / ')
    : null;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <AppPage>
      <div className="space-y-5">
        <PageHeader
          eyebrow={t('decisionSignals.activeOnly')}
          title={t('decisionSignals.title')}
          description={t('decisionSignals.description')}
          actions={(
            <button
              type="button"
              className="btn-secondary inline-flex items-center gap-2"
              onClick={() => {
                void loadSignals();
                void loadOutcomeStats();
              }}
              disabled={loading}
            >
              <RefreshCw className={cn('h-4 w-4', loading ? 'animate-spin' : '')} />
              {t('decisionSignals.refresh')}
            </button>
          )}
        />

        <Card title={t('decisionSignals.stockContextTitle')} subtitle={t('decisionSignals.stockContextDescription')} padding="md">
          <form
            className="flex flex-col gap-3 md:flex-row"
            onSubmit={(event) => {
              event.preventDefault();
              handleStockFormSubmit(stockDraft);
            }}
          >
            <div className="min-w-0 flex-1">
              <StockAutocomplete
                value={stockDraft}
                onChange={setStockDraft}
                onSubmit={handleStockSubmit}
                placeholder={t('decisionSignals.stockContextPlaceholder')}
                ariaLabel={t('decisionSignals.stockContextInput')}
              />
            </div>
            <button
              type="submit"
              className="btn-primary inline-flex h-11 items-center justify-center gap-2"
              disabled={!stockDraft.trim()}
            >
              <Search className="h-4 w-4" />
              {t('decisionSignals.stockContextApply')}
            </button>
            <button
              type="button"
              className="btn-secondary inline-flex h-11 items-center justify-center gap-2"
              onClick={handleClearStockContext}
              disabled={!activeStockContext && !stockDraft}
            >
              {t('decisionSignals.stockContextClear')}
            </button>
          </form>

          {activeStockLabel ? (
            <p className="mt-3 text-sm text-secondary-text">
              {t('decisionSignals.stockContextCurrent', { stock: activeStockLabel })}
            </p>
          ) : (
            <p className="mt-3 text-sm text-secondary-text">{t('decisionSignals.stockContextEmpty')}</p>
          )}

          {historyCandidatesLoaded && stockCandidates.length > 0 ? (
            <div className="mt-4">
              <p className="text-xs font-medium uppercase text-muted-text">
                {stockCandidateMode === 'history'
                  ? t('decisionSignals.stockContextRecent')
                  : t('decisionSignals.stockContextPopular')}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {stockCandidates.map((candidate) => (
                  <button
                    key={`${candidate.source}:${getCandidateKey(candidate)}`}
                    type="button"
                    className="rounded-full border border-border/70 bg-elevated/40 px-3 py-1.5 text-sm text-foreground transition-colors hover:border-primary/60 hover:text-primary"
                    onClick={() => handleCandidateSelect(candidate)}
                  >
                    <span className="font-mono">{candidate.displayCode ?? candidate.code}</span>
                    {candidate.name ? <span className="ml-1 text-secondary-text">{candidate.name}</span> : null}
                    {candidate.market ? <span className="ml-1 text-muted-text">/ {candidate.market}</span> : null}
                  </button>
                ))}
              </div>
            </div>
          ) : historyCandidatesLoaded ? (
            <p className="mt-4 text-sm text-secondary-text">{t('decisionSignals.stockContextNoCandidates')}</p>
          ) : null}
        </Card>

        <Card padding="md">
          <form className="grid gap-3 md:grid-cols-3 xl:grid-cols-7" onSubmit={handleApplyFilters}>
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={filters.market}
              onChange={(event) => setFilters((current) => ({ ...current, market: event.target.value as ListFilters['market'] }))}
              aria-label={t('decisionSignals.market')}
            >
              <option value="">{t('decisionSignals.allMarkets')}</option>
              {MARKET_OPTIONS.map((market) => (
                <option key={market} value={market}>{getDecisionSignalMarketLabel(market, t)}</option>
              ))}
            </select>
            <input
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={filters.stockCode}
              onChange={(event) => setFilters((current) => ({ ...current, stockCode: event.target.value }))}
              placeholder={t('decisionSignals.stockCode')}
              aria-label={t('decisionSignals.stockCode')}
            />
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={filters.action}
              onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value as ListFilters['action'] }))}
              aria-label={t('decisionSignals.action')}
            >
              <option value="">{t('decisionSignals.allActions')}</option>
              {ACTION_OPTIONS.map((action) => (
                <option key={action} value={action}>{actionLabels[action]}</option>
              ))}
            </select>
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={filters.marketPhase}
              onChange={(event) => setFilters((current) => ({ ...current, marketPhase: event.target.value as ListFilters['marketPhase'] }))}
              aria-label={t('decisionSignals.marketPhase')}
            >
              <option value="">{t('decisionSignals.allPhases')}</option>
              {PHASE_OPTIONS.map((phase) => (
                <option key={phase} value={phase}>{getDecisionSignalMarketPhaseLabel(phase, t)}</option>
              ))}
            </select>
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={filters.sourceType}
              onChange={(event) => setFilters((current) => ({ ...current, sourceType: event.target.value as ListFilters['sourceType'] }))}
              aria-label={t('decisionSignals.source')}
            >
              <option value="">{t('decisionSignals.allSources')}</option>
              {SOURCE_OPTIONS.map((source) => (
                <option key={source} value={source}>{getDecisionSignalSourceTypeLabel(source, t)}</option>
              ))}
            </select>
            <input
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={filters.sourceReportId}
              onChange={(event) => setFilters((current) => ({ ...current, sourceReportId: event.target.value }))}
              placeholder={t('decisionSignals.sourceReportId')}
              aria-label={t('decisionSignals.sourceReportId')}
              inputMode="numeric"
              min={1}
              step={1}
              type="number"
            />
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={filters.status}
              onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as ListFilters['status'] }))}
              aria-label={t('decisionSignals.status')}
            >
              <option value="">{t('decisionSignals.allStatuses')}</option>
              {STATUS_OPTIONS.map((status) => <option key={status} value={status}>{t(STATUS_LABEL_KEYS[status])}</option>)}
            </select>
            <button type="submit" className="btn-primary inline-flex h-11 items-center justify-center gap-2">
              <Search className="h-4 w-4" />
              {t('decisionSignals.filter')}
            </button>
          </form>
        </Card>

        {!selected && appliedSourceReportId ? (
          <Card padding="md">
            {renderReassessPanel()}
          </Card>
        ) : null}

        <Card title={t('decisionSignals.statsTitle')} subtitle={t('decisionSignals.statsDescription')} padding="md">
          <p className="mb-3 text-sm text-secondary-text">{t('decisionSignals.statsGlobalScope')}</p>
          {statsError ? (
            <ApiErrorAlert
              error={{ ...statsError, title: t('decisionSignals.statsErrorTitle') }}
              actionLabel={t('common.retry')}
              onAction={() => void loadOutcomeStats()}
            />
          ) : statsLoading ? (
            <p className="text-sm text-secondary-text">{t('common.loading')}...</p>
          ) : outcomeStats && outcomeStats.total > 0 ? (
            <div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-xl border border-border/60 bg-elevated/40 px-3 py-3">
                  <p className="text-xs text-secondary-text">{t('decisionSignals.statsTotal')}</p>
                  <p className="mt-1 text-2xl font-semibold text-foreground">{outcomeStats.total}</p>
                </div>
                <div className="rounded-xl border border-border/60 bg-elevated/40 px-3 py-3">
                  <p className="text-xs text-secondary-text">{t('decisionSignals.statsHitRate')}</p>
                  <p className="mt-1 text-2xl font-semibold text-success">{formatStatPercent(outcomeStats.hitRatePct)}</p>
                </div>
                <div className="rounded-xl border border-border/60 bg-elevated/40 px-3 py-3">
                  <p className="text-xs text-secondary-text">{t('decisionSignals.outcome.hit')}</p>
                  <p className="mt-1 text-2xl font-semibold text-success">{outcomeStats.hit}</p>
                </div>
                <div className="rounded-xl border border-border/60 bg-elevated/40 px-3 py-3">
                  <p className="text-xs text-secondary-text">{t('decisionSignals.outcome.miss')}</p>
                  <p className="mt-1 text-2xl font-semibold text-danger">{outcomeStats.miss}</p>
                </div>
                <div className="rounded-xl border border-border/60 bg-elevated/40 px-3 py-3">
                  <p className="text-xs text-secondary-text">{t('decisionSignals.outcome.unable')}</p>
                  <p className="mt-1 text-2xl font-semibold text-warning">{outcomeStats.unable}</p>
                </div>
              </div>
              {outcomeStats.profileCalibration ? (
                <DecisionSignalProfileCalibration calibration={outcomeStats.profileCalibration} />
              ) : null}
            </div>
          ) : (
            <EmptyState
              className="border-none bg-transparent py-6 shadow-none"
              title={t('decisionSignals.noReviewedStatsTitle')}
              description={t('decisionSignals.noReviewedStatsDescription')}
              icon={<BarChart3 className="h-6 w-6" />}
            />
          )}
        </Card>

        <Card title={t('decisionSignals.latestTitle')} subtitle={t('decisionSignals.latestDescription')} padding="md">
          {!activeStockContext ? (
            <EmptyState
              className="border-none bg-transparent py-6 shadow-none"
              title={t('decisionSignals.stockContextGuideTitle')}
              description={t('decisionSignals.stockContextGuideDescription')}
              icon={<Activity className="h-6 w-6" />}
            />
          ) : null}
          {latestError ? <ApiErrorAlert className="mt-3" error={latestError} /> : null}
          {latestSearched && !latestLoading && !latestError && latestItems.length === 0 ? (
            <EmptyState
              className="mt-4 border-none bg-transparent py-6 shadow-none"
              title={t('decisionSignals.noLatestTitle')}
              description={t('decisionSignals.noLatestDescription')}
              icon={<Activity className="h-6 w-6" />}
            />
          ) : null}
          {latestLoading ? <p className="mt-3 text-sm text-secondary-text">{t('common.loading')}...</p> : null}
          {latestItems.length > 0 ? (
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {latestItems.map((item) => (
                <DecisionSignalCard
                  key={item.id}
                  item={item}
                  onSelect={(selectedItem) => setSelected({ source: 'latest', item: selectedItem })}
                  selected={selected?.item.id === item.id}
                />
              ))}
            </div>
          ) : null}
        </Card>

        <Card title={t('decisionSignals.timelineTitle')} subtitle={t('decisionSignals.timelineDescription')} padding="md">
          <form className="grid gap-3 md:grid-cols-5" onSubmit={handleTimelineSearch}>
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={timelineFilters.market}
              onChange={(event) => {
                const market = event.target.value as TimelineFilters['market'];
                timelineMarketSourceRef.current = market ? 'user' : null;
                setTimelineFilters((current) => ({ ...current, market }));
              }}
              aria-label={t('decisionSignals.timelineMarket')}
            >
              <option value="">{t('decisionSignals.allMarkets')}</option>
              {MARKET_OPTIONS.map((market) => (
                <option key={market} value={market}>{getDecisionSignalMarketLabel(market, t)}</option>
              ))}
            </select>
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={timelineFilters.range}
              onChange={(event) => setTimelineFilters((current) => ({ ...current, range: event.target.value as TimelineRange }))}
              aria-label={t('decisionSignals.timelineRange')}
            >
              <option value="30d">{t('decisionSignals.timelineRange.30d')}</option>
              <option value="90d">{t('decisionSignals.timelineRange.90d')}</option>
              <option value="180d">{t('decisionSignals.timelineRange.180d')}</option>
            </select>
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={timelineFilters.status}
              onChange={(event) => setTimelineFilters((current) => ({ ...current, status: event.target.value as TimelineStatusFilter }))}
              aria-label={t('decisionSignals.timelineStatus')}
            >
              <option value="all">{t('decisionSignals.timelineStatus.all')}</option>
              <option value="active">{t('decisionSignals.timelineStatus.active')}</option>
            </select>
            <select
              className="input-surface input-focus-glow h-11 rounded-xl border bg-transparent px-3 text-sm"
              value={timelineFilters.decisionProfile}
              onChange={(event) => setTimelineFilters((current) => ({
                ...current,
                decisionProfile: event.target.value as TimelineFilters['decisionProfile'],
              }))}
              aria-label={t('decisionSignals.timelineProfile')}
            >
              <option value="">{t('decisionSignals.allProfiles')}</option>
              {REASSESS_PROFILES.map((profile) => (
                <option key={profile} value={profile}>
                  {t(`decisionSignals.profile.${profile}` as UiTextKey)}
                </option>
              ))}
              <option value="unknown">{t('decisionSignals.profile.unknown')}</option>
            </select>
            <button
              type="submit"
              className="btn-secondary inline-flex h-11 items-center justify-center gap-2"
              disabled={timelineLoading || !activeStockContext?.code}
            >
              <Search className="h-4 w-4" />
              {t('decisionSignals.timelineSearch')}
            </button>
          </form>
          <div className="mt-4">
            {!timelineSearched ? (
              <EmptyState
                className="border-none bg-transparent py-6 shadow-none"
                title={activeStockContext ? t('decisionSignals.timelineGuideTitle') : t('decisionSignals.stockContextGuideTitle')}
                description={activeStockContext ? t('decisionSignals.timelineGuideDescription') : t('decisionSignals.stockContextGuideDescription')}
                icon={<Activity className="h-6 w-6" />}
              />
            ) : (
              <DecisionSignalTimeline
                items={timelineItems}
                selectedId={selected?.item.id ?? null}
                loading={timelineLoading}
                error={timelineError?.message ?? null}
                truncated={timelineTruncated}
                onSelect={(selectedItem) => setSelected({ source: 'timeline', item: selectedItem })}
              />
            )}
          </div>
        </Card>

        {error ? (
          <ApiErrorAlert
            error={{ ...error, title: t('decisionSignals.errorTitle') }}
            actionLabel={t('common.retry')}
            onAction={() => void loadSignals()}
          />
        ) : null}

        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-secondary-text">{t('decisionSignals.total', { total })}</p>
          {loading ? <span className="text-xs text-secondary-text">{t('common.loading')}...</span> : null}
        </div>

        {!loading && items.length === 0 ? (
          <EmptyState
            title={t('decisionSignals.emptyTitle')}
            description={t('decisionSignals.emptyDescription')}
            icon={<Activity className="h-7 w-7" />}
          />
        ) : (
          <div className="grid gap-3 xl:grid-cols-2">
            {items.map((item) => (
              <DecisionSignalCard
                key={item.id}
                item={item}
                onSelect={(selectedItem) => setSelected({ source: 'list', item: selectedItem })}
                selected={selected?.item.id === item.id}
              />
            ))}
          </div>
        )}

        <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      <Drawer
        isOpen={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={t('decisionSignals.detailTitle')}
        width="max-w-3xl"
      >
        {selected ? (
          <div className="space-y-4">
            {renderReassessPanel()}
            <DecisionSignalDetails
              item={selected.item}
              outcomes={selectedOutcomes}
              outcomesLoading={selectedOutcomesLoading}
              outcomesError={selectedOutcomesError?.message ?? null}
              feedback={selectedFeedback}
              feedbackLoading={selectedFeedbackLoading}
              feedbackSaving={feedbackSaving}
              feedbackError={selectedFeedbackError?.message ?? null}
              onFeedbackSubmit={handleFeedbackSubmit}
              actions={STATUS_ACTIONS.map((status) => (
                <button
                  key={status}
                  type="button"
                  className="btn-secondary !px-3 !py-1.5 !text-xs"
                  onClick={() => setPendingStatus({
                    item: selected.item,
                    status,
                    message: t(STATUS_ACTION_CONFIRM_KEYS[status]),
                  })}
                  disabled={statusUpdating || selected.item.status === status}
                >
                  {t(STATUS_ACTION_LABEL_KEYS[status])}
                </button>
              ))}
            />
          </div>
        ) : null}
      </Drawer>

      {statusUpdating ? (
        <InlineAlert
          className="fixed bottom-5 right-5 z-[60] max-w-sm"
          variant="info"
          title={t('common.processing')}
          message={t('decisionSignals.confirmStatusTitle')}
        />
      ) : null}

      <ConfirmDialog
        isOpen={reassessPersistConfirm}
        title={t('decisionSignals.reassessPersistConfirmTitle')}
        message={t('decisionSignals.reassessPersistConfirmMessage')}
        confirmText={t('decisionSignals.reassessPersist')}
        confirmDisabled={reassessPersisting}
        cancelDisabled={reassessPersisting}
        onConfirm={() => void handlePersistReassess()}
        onCancel={() => setReassessPersistConfirm(false)}
      />

      <ConfirmDialog
        isOpen={Boolean(pendingStatus)}
        title={t('decisionSignals.confirmStatusTitle')}
        message={pendingStatus?.message ?? ''}
        confirmText={t('common.confirm')}
        confirmDisabled={statusUpdating}
        cancelDisabled={statusUpdating}
        onConfirm={() => void handleStatusUpdate()}
        onCancel={() => setPendingStatus(null)}
      />
    </AppPage>
  );
};

export default DecisionSignalsPage;
