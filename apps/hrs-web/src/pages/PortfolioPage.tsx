/**
 * @file PortfolioPage.tsx
 * @description 投资组合页面，管理账户、持仓快照、风险指标、交易/资金/公司行为录入与查询，支持券商 CSV 导入和汇率刷新
 * @module pages
 */

import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Pie, PieChart, ResponsiveContainer, Tooltip, Legend, Cell } from 'recharts';
import { decisionSignalsApi } from '../api/decisionSignals';
import { portfolioApi } from '../api/portfolio';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { InlineTipCard, Card, Badge, ConfirmDialog, EmptyState, InlineAlert } from '../components';
import { PortfolioSignalSummary } from '../components/decision-signals/DecisionSignalDisplay';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { formatUiText } from '../i18n/uiText';
import { PORTFOLIO_TEXT } from '../locales/featureText';
import { usePreference } from '../hooks/usePreference';
import type { FxRefreshFeedback } from '../utils/portfolioFormat';
import {
  buildFxRefreshFeedback,
  formatBrokerLabel,
  formatCashDirectionLabel,
  formatCorporateActionLabel,
  formatMoney,
  formatPct,
  formatPositionMoney,
  formatPositionPrice,
  formatSideLabel,
  formatSignedPct,
  getCsvCommitVariant,
  getCsvParseVariant,
  getFxRefreshFeedbackVariant,
  getPositionPriceLabel,
  getTodayIso,
  hasPositionPrice,
} from '../utils/portfolioFormat';
import type {
  DecisionSignalItem,
  DecisionSignalMarket,
} from '../types/decisionSignals';
import type {
  PortfolioAccountItem,
  PortfolioCashDirection,
  PortfolioCashLedgerListItem,
  PortfolioCorporateActionListItem,
  PortfolioCorporateActionType,
  PortfolioCostMethod,
  PortfolioImportBrokerItem,
  PortfolioImportCommitResponse,
  PortfolioImportParseResponse,
  PortfolioPositionItem,
  PortfolioRiskResponse,
  PortfolioSide,
  PortfolioSnapshotResponse,
  PortfolioTradeListItem,
} from '../types/portfolio';
import { areStockCodesEquivalent, normalizeStockCode } from '../utils/stockCode';
import { parseDecisionSignalDate } from '../utils/decisionSignalTime';
import { buildDecisionActionLabelMap, getDecisionActionLabel } from '../utils/decisionAction';
import { toCnOrEn } from '../utils/uiLanguage';

/** 饼图颜色调色板 */
const PIE_COLORS = ['#00d4ff', '#00ff88', '#ffaa00', '#ff7a45', '#7f8cff', '#ff4466'];
/** 事件记录默认每页条数 */
const DEFAULT_PAGE_SIZE = 20;
/** 持仓决策信号查询并发数 */
const PORTFOLIO_SIGNAL_LOOKUP_CONCURRENCY = 6;
/** 券商列表接口不可用时的内置回退券商 */
const FALLBACK_BROKERS: PortfolioImportBrokerItem[] = [
  { broker: 'huatai', aliases: [], displayName: '华泰' },
  { broker: 'citic', aliases: ['zhongxin'], displayName: '中信' },
  { broker: 'cmb', aliases: ['cmbchina', 'zhaoshang'], displayName: '招商' },
];

/** 账户选择选项：'all' 表示全部账户，数字表示具体账户 ID */
type AccountOption = 'all' | number;
/** 事件类型：交易/资金/公司行为 */
type EventType = 'trade' | 'cash' | 'corporate';

/** 扁平化持仓行：在持仓数据基础上附加账户 ID 和名称，用于表格展示 */
type FlatPosition = PortfolioPositionItem & {
  accountId: number;
  accountName: string;
};

/** 持仓决策信号查询参数 */
type PortfolioSignalLookup = {
  stockCode: string;
  market?: DecisionSignalMarket;
};

/** 持仓决策信号查询结果 */
type PortfolioSignalLookupResult = {
  items: DecisionSignalItem[];
  error: string | null;
};

/** 页面支持的语言 */
type PortfolioPageLanguage = 'zh' | 'en';

/** 数据质量限制标签的中英文映射表 */
const PORTFOLIO_LIMITATION_LABELS: Record<string, Record<PortfolioPageLanguage, string>> = {
  realtime_quote_best_effort: {
    zh: '实时行情为尽力获取',
    en: 'Realtime quotes are best-effort',
  },
  fx_and_cost_basis_partial: {
    zh: '汇率与成本基础为部分口径',
    en: 'FX and cost basis are partial',
  },
  sector_and_risk_metrics_limited: {
    zh: '行业与风险指标覆盖有限',
    en: 'Sector and risk metrics are limited',
  },
};

type PendingDelete =
  | { eventType: 'trade'; id: number; message: string }
  | { eventType: 'cash'; id: number; message: string }
  | { eventType: 'corporate'; id: number; message: string };

type PendingAccountDelete = {
  accountId: number;
  accountName: string;
};

type FxRefreshContext = {
  viewKey: string;
  requestId: number;
};

/** 输入框公共样式类名 */
const PORTFOLIO_INPUT_CLASS =
  'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';
/** 下拉选择框公共样式类名（在输入框样式基础上增加下拉箭头空间） */
const PORTFOLIO_SELECT_CLASS = `${PORTFOLIO_INPUT_CLASS} appearance-none pr-10`;
/** 文件选择器公共样式类名 */
const PORTFOLIO_FILE_PICKER_CLASS =
  'input-surface input-focus-glow flex h-11 w-full cursor-pointer items-center justify-center rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';

/**
 * 获取决策信号的时间戳（毫秒），优先使用创建时间，其次更新时间
 * @param item - 决策信号项
 * @returns 毫秒时间戳，无法解析时返回 0
 */
function getSignalTime(item: DecisionSignalItem): number {
  return parseDecisionSignalDate(item.createdAt)?.getTime()
    ?? parseDecisionSignalDate(item.updatedAt)?.getTime()
    ?? 0;
}

/**
 * 判断 right 信号是否比 left 信号更新
 * @param left - 已有的信号（可为 undefined）
 * @param right - 待比较的信号
 * @returns right 是否比 left 更新
 */
function isNewerSignal(left: DecisionSignalItem | undefined, right: DecisionSignalItem): boolean {
  if (!left) return true;
  return getSignalTime(right) > getSignalTime(left);
}

/**
 * 格式化数据质量限制标签，根据界面语言返回对应的本地化文本
 * @param limitation - 限制标识
 * @param language - 界面语言
 * @returns 本地化后的限制说明文本
 */
function formatPortfolioLimitation(limitation: string, language: PortfolioPageLanguage): string {
  return PORTFOLIO_LIMITATION_LABELS[limitation]?.[language] ?? limitation;
}

/** 决策信号支持的地区市场集合 */
const DECISION_SIGNAL_MARKETS = new Set<DecisionSignalMarket>(['cn', 'hk', 'us', 'jp', 'kr', 'tw']);
type PortfolioAccountMarket = 'cn' | 'hk' | 'us' | 'jp' | 'kr' | 'tw';

/**
 * 将字符串安全转换为决策信号市场标识
 * @param value - 原始市场字符串
 * @returns 合法市场标识或 undefined（不合法时）
 */
function toDecisionSignalMarket(value: string | null | undefined): DecisionSignalMarket | undefined {
  const normalized = String(value || '').toLowerCase();
  return DECISION_SIGNAL_MARKETS.has(normalized as DecisionSignalMarket)
    ? normalized as DecisionSignalMarket
    : undefined;
}

/**
 * 生成持仓决策信号查询的唯一键，用于去重
 * @param stockCode - 股票代码
 * @param market - 市场标识（可选）
 * @returns 格式为 "市场:标准化代码" 的键
 */
function toPositionSignalLookupKey(stockCode: string, market?: DecisionSignalMarket): string {
  return `${market || ''}:${normalizeStockCode(stockCode).toUpperCase()}`;
}

/**
 * 以指定并发数批量执行异步映射，保持结果顺序与输入一致
 * @param items - 输入数组
 * @param concurrency - 最大并发数
 * @param mapper - 异步映射函数
 * @returns 与输入顺序一致的映射结果数组
 */
async function mapWithConcurrency<T, R>(
  items: T[],
  concurrency: number,
  mapper: (item: T) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let nextIndex = 0;
  const workerCount = Math.min(Math.max(1, concurrency), items.length);

  await Promise.all(Array.from({ length: workerCount }, async () => {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      results[currentIndex] = await mapper(items[currentIndex]);
    }
  }));

  return results;
}

/**
 * 加载单个持仓的决策信号查询结果
 * @param lookup - 查询参数（股票代码和市场）
 * @returns 信号列表和可能的错误信息
 */
async function loadPortfolioSignalLookup(lookup: PortfolioSignalLookup): Promise<PortfolioSignalLookupResult> {
  try {
    const response = await decisionSignalsApi.getLatest(lookup.stockCode, {
      market: lookup.market,
      limit: 1,
    });
    return { items: response.items, error: null };
  } catch (err) {
    return { items: [], error: getParsedApiError(err).message };
  }
}

/**
 * 投资组合页面组件
 *
 * 职责：
 * - 管理多账户的创建、切换和删除
 * - 展示持仓快照（总权益/市值/现金）和风险指标（回撤/止损/集中度/AI 风险信号）
 * - 支持手工录入交易/资金流水/公司行为，并查询和删除事件记录
 * - 支持券商 CSV 导入（解析预演 + 提交写入）
 * - 支持汇率刷新和持仓决策信号查询
 *
 * 核心状态：
 * - accounts / selectedAccount / costMethod：账户与成本方式
 * - snapshot / risk：快照和风险数据
 * - eventType / tradeEvents / cashEvents / corporateEvents：事件记录
 * - tradeForm / cashForm / corpForm：各录入表单
 * - brokers / csvFile / csvDryRun：CSV 导入相关
 */
const PortfolioPage: React.FC = () => {
  const { language, t } = useUiLanguage();
  const text = PORTFOLIO_TEXT[toCnOrEn(language)];
  const decisionActionLabels = useMemo(() => buildDecisionActionLabelMap(t), [t]); // 决策动作标签映射表

  // 设置页面标题
  useEffect(() => {
    document.title = text.documentTitle;
  }, [text.documentTitle]);

  const [accounts, setAccounts] = useState<PortfolioAccountItem[]>([]); // 账户列表
  // L4 缓存：账户选择和成本方式偏好（localStorage 永久保存）
  const [selectedAccount, setSelectedAccount] = usePreference<AccountOption>('portfolio-selected-account', 'all'); // 当前选中的账户（'all' 为全部）
  const [showCreateAccount, setShowCreateAccount] = useState(false); // 是否展开新建账户表单
  const [accountCreating, setAccountCreating] = useState(false); // 账户创建提交中状态
  const [accountCreateError, setAccountCreateError] = useState<string | null>(null); // 账户创建错误信息
  const [accountCreateSuccess, setAccountCreateSuccess] = useState<string | null>(null); // 账户创建成功提示
  const [accountForm, setAccountForm] = useState({ // 新建账户表单数据
    name: '',
    broker: 'Demo',
    market: 'cn' as PortfolioAccountMarket,
    baseCurrency: 'CNY',
  });
  const [costMethod, setCostMethod] = usePreference<PortfolioCostMethod>('portfolio-cost-method', 'fifo'); // L4 缓存：成本计算方式（FIFO/加权平均）
  const [snapshot, setSnapshot] = useState<PortfolioSnapshotResponse | null>(null); // 持仓快照数据
  const [risk, setRisk] = useState<PortfolioRiskResponse | null>(null); // 风险指标数据
  const [isLoading, setIsLoading] = useState(false); // 快照和风险数据加载中状态
  const [fxRefreshing, setFxRefreshing] = useState(false); // 汇率刷新中状态
  const [fxRefreshFeedback, setFxRefreshFeedback] = useState<FxRefreshFeedback | null>(null); // 汇率刷新结果反馈
  const [error, setError] = useState<ParsedApiError | null>(null); // 全局错误信息
  const [riskWarning, setRiskWarning] = useState<string | null>(null); // 风险数据降级警告
  const [writeWarning, setWriteWarning] = useState<string | null>(null); // 写入操作提示（如需先选择账户）
  const [portfolioSignals, setPortfolioSignals] = useState<DecisionSignalItem[]>([]); // 持仓决策信号列表
  const [portfolioSignalsLoading, setPortfolioSignalsLoading] = useState(false); // 决策信号加载中状态
  const [portfolioSignalsWarning, setPortfolioSignalsWarning] = useState<string | null>(null); // 决策信号部分失败警告
  const [portfolioSignalsRefreshKey, setPortfolioSignalsRefreshKey] = useState(0); // 决策信号刷新触发键（手动刷新时递增）
  const portfolioSignalsRequestRef = useRef(0); // 决策信号请求序列号，用于取消过期请求
  const [positionAnalysisLoadingKey, setPositionAnalysisLoadingKey] = useState<string | null>(null); // 当前正在提交分析的持仓行键
  const [positionAnalysisMessage, setPositionAnalysisMessage] = useState<string | null>(null); // 持仓分析任务提交结果提示

  const [brokers, setBrokers] = useState<PortfolioImportBrokerItem[]>([]); // 可用券商列表
  const [selectedBroker, setSelectedBroker] = useState('huatai'); // 当前选中的券商（用于 CSV 导入）
  const [csvFile, setCsvFile] = useState<File | null>(null); // 用户选择的 CSV 文件
  const [csvDryRun, setCsvDryRun] = useState(true); // CSV 导入是否仅预演（不实际写入）
  const [csvParsing, setCsvParsing] = useState(false); // CSV 解析中状态
  const [csvCommitting, setCsvCommitting] = useState(false); // CSV 提交中状态
  const [csvParseResult, setCsvParseResult] = useState<PortfolioImportParseResponse | null>(null); // CSV 解析结果
  const [csvCommitResult, setCsvCommitResult] = useState<PortfolioImportCommitResponse | null>(null); // CSV 提交结果
  const [brokerLoadWarning, setBrokerLoadWarning] = useState<string | null>(null); // 券商列表加载降级警告

  const [eventType, setEventType] = useState<EventType>('trade'); // 事件记录类型（交易/资金/公司行为）
  const [eventDateFrom, setEventDateFrom] = useState(''); // 事件筛选：起始日期
  const [eventDateTo, setEventDateTo] = useState(''); // 事件筛选：截止日期
  const [eventSymbol, setEventSymbol] = useState(''); // 事件筛选：股票代码
  const [eventSide, setEventSide] = useState<'' | PortfolioSide>(''); // 事件筛选：买卖方向
  const [eventDirection, setEventDirection] = useState<'' | PortfolioCashDirection>(''); // 事件筛选：资金方向
  const [eventActionType, setEventActionType] = useState<'' | PortfolioCorporateActionType>(''); // 事件筛选：公司行为类型
  const [eventPage, setEventPage] = useState(1); // 事件记录当前页码
  const [eventTotal, setEventTotal] = useState(0); // 事件记录总数
  const [eventLoading, setEventLoading] = useState(false); // 事件记录加载中状态
  const [tradeEvents, setTradeEvents] = useState<PortfolioTradeListItem[]>([]); // 交易流水列表
  const [cashEvents, setCashEvents] = useState<PortfolioCashLedgerListItem[]>([]); // 资金流水列表
  const [corporateEvents, setCorporateEvents] = useState<PortfolioCorporateActionListItem[]>([]); // 公司行为列表
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null); // 待确认删除的事件记录
  const [deleteLoading, setDeleteLoading] = useState(false); // 事件删除中状态
  const [pendingAccountDelete, setPendingAccountDelete] = useState<PendingAccountDelete | null>(null); // 待确认删除的账户
  const [accountDeleteLoading, setAccountDeleteLoading] = useState(false); // 账户删除中状态

  const [tradeForm, setTradeForm] = useState({ // 交易录入表单数据
    symbol: '',
    tradeDate: getTodayIso(),
    side: 'buy' as PortfolioSide,
    quantity: '',
    price: '',
    fee: '',
    tax: '',
    tradeUid: '',
    note: '',
  });
  const [cashForm, setCashForm] = useState({ // 资金流水录入表单数据
    eventDate: getTodayIso(),
    direction: 'in' as PortfolioCashDirection,
    amount: '',
    currency: '',
    note: '',
  });
  const [corpForm, setCorpForm] = useState({ // 公司行为录入表单数据
    symbol: '',
    effectiveDate: getTodayIso(),
    actionType: 'cash_dividend' as PortfolioCorporateActionType,
    cashDividendPerShare: '',
    splitRatio: '',
    note: '',
  });

  const queryAccountId = selectedAccount === 'all' ? undefined : selectedAccount; // 查询用的账户 ID（'all' 时为 undefined）
  const refreshViewKey = `${selectedAccount === 'all' ? 'all' : `account:${selectedAccount}`}:cost:${costMethod}`; // 当前视图的唯一标识（账户+成本方式），用于判断刷新上下文是否过期
  const refreshContextRef = useRef<FxRefreshContext>({ viewKey: refreshViewKey, requestId: 0 }); // 汇率刷新上下文 ref，存储视图标识和请求序列号
  const hasAccounts = accounts.length > 0; // 是否存在账户
  const writableAccount = selectedAccount === 'all' ? undefined : accounts.find((item) => item.id === selectedAccount); // 当前可写入的账户对象（'all' 时为 undefined）
  const writableAccountId = writableAccount?.id; // 当前可写入的账户 ID
  const writeBlocked = !writableAccountId; // 是否阻止写入操作（未选择具体账户时为 true）
  const canDeleteSelectedAccount = Boolean(writableAccountId) && !isLoading && !fxRefreshing && !accountDeleteLoading; // 是否允许删除当前账户
  const totalEventPages = Math.max(1, Math.ceil(eventTotal / DEFAULT_PAGE_SIZE)); // 事件记录总页数
  const currentEventCount = eventType === 'trade' // 当前事件类型下的事件条数
    ? tradeEvents.length
    : eventType === 'cash'
      ? cashEvents.length
      : corporateEvents.length;

  /** 判断指定的刷新上下文是否仍然有效（视图标识和请求序列号均匹配） */
  const isActiveRefreshContext = (requestedViewKey: string, requestedRequestId: number) => {
    return (
      refreshContextRef.current.viewKey === requestedViewKey
      && refreshContextRef.current.requestId === requestedRequestId
    );
  };

  /**
   * 加载账户列表
   * 加载后自动校正选中状态：若已选账户不存在则回退到第一个或 'all'
   */
  const loadAccounts = useCallback(async () => {
    try {
      const response = await portfolioApi.getAccounts(false);
      const items = response.accounts || [];
      setAccounts(items);
      setSelectedAccount((prev) => {
        if (items.length === 0) return 'all';
        if (prev !== 'all' && !items.some((item) => item.id === prev)) return items[0].id;
        return prev;
      });
      if (items.length === 0) setShowCreateAccount(true);
    } catch (err) {
      setError(getParsedApiError(err));
    }
  }, []);

  /**
   * 加载可用券商列表
   * 接口返回为空或不可用时回退到内置券商列表（华泰/中信/招商）
   */
  const loadBrokers = useCallback(async () => {
    try {
      const response = await portfolioApi.listImportBrokers();
      const brokerItems = response.brokers || [];
      if (brokerItems.length === 0) {
        setBrokers(FALLBACK_BROKERS);
        setBrokerLoadWarning('券商列表接口返回为空，已回退为内置券商列表（华泰/中信/招商）。');
        if (!FALLBACK_BROKERS.some((item) => item.broker === selectedBroker)) {
          setSelectedBroker(FALLBACK_BROKERS[0].broker);
        }
        return;
      }
      setBrokers(brokerItems);
      setBrokerLoadWarning(null);
      if (!brokerItems.some((item) => item.broker === selectedBroker)) {
        setSelectedBroker(brokerItems[0].broker);
      }
    } catch {
      setBrokers(FALLBACK_BROKERS);
      setBrokerLoadWarning('券商列表接口不可用，已回退为内置券商列表（华泰/中信/招商）。');
      if (!FALLBACK_BROKERS.some((item) => item.broker === selectedBroker)) {
        setSelectedBroker(FALLBACK_BROKERS[0].broker);
      }
    }
  }, [selectedBroker]);

  /**
   * 加载持仓快照和风险指标
   * 快照和风险数据分别请求，风险请求失败时降级为仅展示快照
   */
  const loadSnapshotAndRisk = useCallback(async () => {
    setIsLoading(true);
    setRiskWarning(null);
    try {
      const snapshotData = await portfolioApi.getSnapshot({
        accountId: queryAccountId,
        costMethod,
        includeRealtime: false,
      });
      setSnapshot(snapshotData);
      setError(null);

      try {
        const riskData = await portfolioApi.getRisk({
          accountId: queryAccountId,
          costMethod,
          includeRealtime: false,
        });
        setRisk(riskData);
      } catch (riskErr) {
        setRisk(null);
        const parsed = getParsedApiError(riskErr);
        setRiskWarning(parsed.message || '风险数据获取失败，已降级为仅展示快照数据。');
      }
    } catch (err) {
      setSnapshot(null);
      setRisk(null);
      setError(getParsedApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, [queryAccountId, costMethod]);

  /**
   * 加载事件记录指定页
   * 根据当前事件类型（交易/资金/公司行为）调用对应 API，支持日期、代码、方向等筛选条件
   * @param page - 要加载的页码
   */
  const loadEventsPage = useCallback(async (page: number) => {
    setEventLoading(true);
    try {
      if (eventType === 'trade') {
        const response = await portfolioApi.listTrades({
          accountId: queryAccountId,
          dateFrom: eventDateFrom || undefined,
          dateTo: eventDateTo || undefined,
          symbol: eventSymbol || undefined,
          side: eventSide || undefined,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });
        setTradeEvents(response.items || []);
        setEventTotal(response.total || 0);
      } else if (eventType === 'cash') {
        const response = await portfolioApi.listCashLedger({
          accountId: queryAccountId,
          dateFrom: eventDateFrom || undefined,
          dateTo: eventDateTo || undefined,
          direction: eventDirection || undefined,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });
        setCashEvents(response.items || []);
        setEventTotal(response.total || 0);
      } else {
        const response = await portfolioApi.listCorporateActions({
          accountId: queryAccountId,
          dateFrom: eventDateFrom || undefined,
          dateTo: eventDateTo || undefined,
          symbol: eventSymbol || undefined,
          actionType: eventActionType || undefined,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });
        setCorporateEvents(response.items || []);
        setEventTotal(response.total || 0);
      }
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setEventLoading(false);
    }
  }, [
    eventActionType,
    eventDateFrom,
    eventDateTo,
    eventDirection,
    eventSide,
    eventSymbol,
    eventType,
    queryAccountId,
  ]);

  /** 加载事件记录（使用当前页码） */
  const loadEvents = useCallback(async () => {
    await loadEventsPage(eventPage);
  }, [eventPage, loadEventsPage]);

  /**
   * 刷新投资组合数据：并行加载快照/风险和事件记录
   * @param page - 事件记录页码，默认为当前页
   */
  const refreshPortfolioData = useCallback(async (page = eventPage) => {
    await Promise.all([loadSnapshotAndRisk(), loadEventsPage(page)]);
  }, [eventPage, loadEventsPage, loadSnapshotAndRisk]);

  // 页面挂载时：并行加载账户列表和券商列表
  useEffect(() => {
    void loadAccounts();
    void loadBrokers();
  }, [loadAccounts, loadBrokers]);

  // 快照/风险数据加载：账户选择或成本方式变化时触发
  useEffect(() => {
    void loadSnapshotAndRisk();
  }, [loadSnapshotAndRisk]);

  // 事件记录加载：页码、筛选条件或加载函数变化时触发
  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  // 视图切换时重置汇率刷新状态：账户或成本方式变化时，清除上一次的刷新反馈并递增请求序列号
  useEffect(() => {
    refreshContextRef.current = {
      viewKey: refreshViewKey,
      requestId: refreshContextRef.current.requestId + 1,
    };
    setFxRefreshing(false);
    setFxRefreshFeedback(null);
  }, [refreshViewKey]);

  // 筛选条件变化时重置到第一页
  useEffect(() => {
    setEventPage(1);
  }, [eventType, queryAccountId, eventDateFrom, eventDateTo, eventSymbol, eventSide, eventDirection, eventActionType]);

  // 写入限制解除时清除提示
  useEffect(() => {
    if (!writeBlocked) {
      setWriteWarning(null);
    }
  }, [writeBlocked]);

  /**
   * 扁平化持仓行：将快照中嵌套的账户-持仓结构展平为一维数组
   * 按市值降序排列，用于持仓表格展示
   */
  const positionRows: FlatPosition[] = useMemo(() => {
    if (!snapshot) return [];
    const rows: FlatPosition[] = [];
    for (const account of snapshot.accounts || []) {
      for (const position of account.positions || []) {
        rows.push({
          ...position,
          accountId: account.accountId,
          accountName: account.accountName,
        });
      }
    }
    rows.sort((a, b) => Number(b.marketValueBase || 0) - Number(a.marketValueBase || 0));
    return rows;
  }, [snapshot]);

  /** 判断快照数据是否与当前账户范围匹配（用于决定是否加载决策信号） */
  const snapshotMatchesAccountScope = useMemo(() => {
    if (!snapshot) return false;
    const snapshotAccountIds = new Set((snapshot.accounts || []).map((account) => account.accountId));
    if (queryAccountId !== undefined) {
      return snapshotAccountIds.size === 1 && snapshotAccountIds.has(queryAccountId);
    }
    return accounts.length === 0 || Number(snapshot.accountCount || 0) === accounts.length;
  }, [accounts.length, queryAccountId, snapshot]);

  /** 从持仓行中提取去重后的决策信号查询参数列表 */
  const positionSignalLookups = useMemo(() => {
    const lookups = new Map<string, PortfolioSignalLookup>();
    for (const row of positionRows) {
      const stockCode = String(row.symbol || '').trim();
      if (!stockCode) continue;
      const market = toDecisionSignalMarket(row.market);
      const key = toPositionSignalLookupKey(stockCode, market);
      if (!lookups.has(key)) {
        lookups.set(key, { stockCode, market });
      }
    }
    return Array.from(lookups.values());
  }, [positionRows]);

  // 加载持仓决策信号：持仓行或刷新键变化时，以并发方式批量查询最新决策信号
  // 使用请求序列号防止竞态条件，快照不匹配范围时跳过加载
  useEffect(() => {
    if (positionSignalLookups.length === 0) {
      setPortfolioSignals([]);
      setPortfolioSignalsWarning(null);
      setPortfolioSignalsLoading(false);
      return;
    }

    const requestId = portfolioSignalsRequestRef.current;
    const isActiveRequest = () => portfolioSignalsRequestRef.current === requestId;

    const loadPortfolioSignals = async () => {
      setPortfolioSignalsLoading(true);
      setPortfolioSignalsWarning(null);
      const results = await mapWithConcurrency(
        positionSignalLookups,
        PORTFOLIO_SIGNAL_LOOKUP_CONCURRENCY,
        loadPortfolioSignalLookup,
      );
      if (!isActiveRequest()) return;
      const collected = results.flatMap((result) => result.items);
      const failures = results.flatMap((result) => (result.error ? [result.error] : []));
      setPortfolioSignals(collected);
      setPortfolioSignalsWarning(
        failures.length > 0
          ? (
              collected.length > 0
                ? formatUiText(t('decisionSignals.portfolioPartialWarning'), { message: failures[0] })
                : failures[0]
            )
          : null,
      );
      if (isActiveRequest()) {
        setPortfolioSignalsLoading(false);
      }
    };

    void loadPortfolioSignals();

    return () => {
      portfolioSignalsRequestRef.current += 1;
    };
  }, [portfolioSignalsRefreshKey, positionSignalLookups, snapshotMatchesAccountScope, t]);

  /**
   * 持仓行与决策信号的映射表
   * 遍历所有持仓行和决策信号，按市场+代码匹配，保留每个持仓对应的最新决策信号
   * 键格式为 "账户ID-代码-市场"，用于在表格中快速查找对应信号
   */
  const signalByPositionKey = useMemo(() => {
    const mapped = new Map<string, DecisionSignalItem>();
    for (const row of positionRows) {
      const rowMarket = String(row.market || '').toLowerCase();
      for (const signal of portfolioSignals) {
        const signalMarket = String(signal.market || '').toLowerCase();
        if (rowMarket && signalMarket && rowMarket !== signalMarket) {
          continue;
        }
        if (!areStockCodesEquivalent(row.symbol, signal.stockCode)) {
          continue;
        }
        const key = `${row.accountId}-${row.symbol}-${row.market}`;
        const existing = mapped.get(key);
        if (isNewerSignal(existing, signal)) {
          mapped.set(key, signal);
        }
      }
    }
    return mapped;
  }, [portfolioSignals, positionRows]);

  /**
   * 提交单个持仓的分析任务
   * @param row - 持仓行数据（包含账户 ID、代码、市场）
   */
  const handleAnalyzePosition = async (row: FlatPosition) => {
    const key = `${row.accountId}-${row.symbol}-${row.market}`;
    setPositionAnalysisLoadingKey(key);
    setPositionAnalysisMessage(null);
    setError(null);
    try {
      const task = await portfolioApi.analyzePosition(row.symbol, {
        accountId: row.accountId,
        analysisPhase: 'auto',
        force: false,
      });
      setPositionAnalysisMessage(`已提交 ${row.symbol} 分析任务：${task.taskId}`);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setPositionAnalysisLoadingKey(null);
    }
  };

  /** 行业集中度饼图数据：从风险指标中提取前 6 大行业及其权重百分比 */
  const sectorPieData = useMemo(() => {
    const sectors = risk?.sectorConcentration?.topSectors || [];
    return sectors
      .slice(0, 6)
      .map((item) => ({
        name: item.sector,
        value: Number(item.weightPct || 0),
      }))
      .filter((item) => item.value > 0);
  }, [risk]);

  /** 持仓集中度回退饼图数据：当行业数据不可用时，使用前 6 大持仓的权重百分比 */
  const positionFallbackPieData = useMemo(() => {
    if (!risk?.concentration?.topPositions?.length) {
      return [];
    }
    return risk.concentration.topPositions
      .slice(0, 6)
      .map((item) => ({
        name: item.symbol,
        value: Number(item.weightPct || 0),
      }))
      .filter((item) => item.value > 0);
  }, [risk]);

  // 集中度饼图数据：优先使用行业维度，不可用时回退到持仓维度
  const concentrationPieData = sectorPieData.length > 0 ? sectorPieData : positionFallbackPieData;
  // 集中度展示模式：'sector' 为行业维度，'position' 为持仓维度
  const concentrationMode = sectorPieData.length > 0 ? 'sector' : 'position';

  /**
   * 提交交易录入表单
   * 验证账户选择后调用创建交易 API，成功后刷新持仓数据并清空表单
   * @param e - 表单提交事件
   */
  const handleTradeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!writableAccountId) {
      setWriteWarning('请先在右上角选择具体账户，再进行录入或导入提交。');
      return;
    }
    try {
      setWriteWarning(null);
      await portfolioApi.createTrade({
        accountId: writableAccountId,
        symbol: tradeForm.symbol,
        tradeDate: tradeForm.tradeDate,
        side: tradeForm.side,
        quantity: Number(tradeForm.quantity),
        price: Number(tradeForm.price),
        fee: Number(tradeForm.fee || 0),
        tax: Number(tradeForm.tax || 0),
        tradeUid: tradeForm.tradeUid || undefined,
        note: tradeForm.note || undefined,
      });
      await refreshPortfolioData();
      setTradeForm((prev) => ({ ...prev, symbol: '', tradeUid: '', note: '' }));
    } catch (err) {
      setError(getParsedApiError(err));
    }
  };

  /**
   * 提交资金流水录入表单
   * 验证账户选择后调用创建资金流水 API，成功后刷新持仓数据
   * @param e - 表单提交事件
   */
  const handleCashSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!writableAccountId) {
      setWriteWarning('请先在右上角选择具体账户，再进行录入或导入提交。');
      return;
    }
    try {
      setWriteWarning(null);
      await portfolioApi.createCashLedger({
        accountId: writableAccountId,
        eventDate: cashForm.eventDate,
        direction: cashForm.direction,
        amount: Number(cashForm.amount),
        currency: cashForm.currency || undefined,
        note: cashForm.note || undefined,
      });
      await refreshPortfolioData();
      setCashForm((prev) => ({ ...prev, note: '' }));
    } catch (err) {
      setError(getParsedApiError(err));
    }
  };

  /**
   * 提交公司行为录入表单
   * 根据公司行为类型（现金分红/拆并股）调用对应 API，成功后刷新持仓数据
   * @param e - 表单提交事件
   */
  const handleCorporateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!writableAccountId) {
      setWriteWarning('请先在右上角选择具体账户，再进行录入或导入提交。');
      return;
    }
    try {
      setWriteWarning(null);
      await portfolioApi.createCorporateAction({
        accountId: writableAccountId,
        symbol: corpForm.symbol,
        effectiveDate: corpForm.effectiveDate,
        actionType: corpForm.actionType,
        cashDividendPerShare: corpForm.cashDividendPerShare ? Number(corpForm.cashDividendPerShare) : undefined,
        splitRatio: corpForm.splitRatio ? Number(corpForm.splitRatio) : undefined,
        note: corpForm.note || undefined,
      });
      await refreshPortfolioData();
      setCorpForm((prev) => ({ ...prev, symbol: '', note: '' }));
    } catch (err) {
      setError(getParsedApiError(err));
    }
  };

  /**
   * 解析 CSV 文件（预演模式）
   * 调用后端解析接口预览文件内容，不实际写入数据
   */
  const handleParseCsv = async () => {
    if (!csvFile) return;
    try {
      setCsvParsing(true);
      const parsed = await portfolioApi.parseCsvImport(selectedBroker, csvFile);
      setCsvParseResult(parsed);
      setCsvCommitResult(null);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setCsvParsing(false);
    }
  };

  /**
   * 提交 CSV 导入
   * 根据预演开关决定是否实际写入数据，非预演模式下成功后刷新持仓数据
   */
  const handleCommitCsv = async () => {
    if (!csvFile) return;
    if (!writableAccountId) {
      setWriteWarning('请先在右上角选择具体账户，再进行录入或导入提交。');
      return;
    }
    try {
      setWriteWarning(null);
      setCsvCommitting(true);
      const committed = await portfolioApi.commitCsvImport(writableAccountId, selectedBroker, csvFile, csvDryRun);
      setCsvCommitResult(committed);
      if (!csvDryRun) {
        await refreshPortfolioData();
      }
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setCsvCommitting(false);
    }
  };

  /**
   * 打开事件记录删除确认对话框
   * 验证账户选择后设置待删除项，触发确认弹窗
   * @param item - 待删除的事件记录信息（含类型、ID、确认消息）
   */
  const openDeleteDialog = (item: PendingDelete) => {
    if (!writableAccountId) {
      setWriteWarning('请先在右上角选择具体账户，再进行删除修正。');
      return;
    }
    setPendingDelete(item);
  };

  /**
   * 打开账户删除确认对话框
   * 验证已选择具体账户后设置待删除账户信息，触发确认弹窗
   */
  const openAccountDeleteDialog = () => {
    if (!writableAccount) {
      setWriteWarning('请先选择具体账户，再删除持仓账户。');
      return;
    }
    setPendingAccountDelete({
      accountId: writableAccount.id,
      accountName: writableAccount.name,
    });
  };

  /**
   * 确认删除账户
   * 删除后自动切换到下一个可用账户（或 'all'），若无剩余账户则展开新建表单
   */
  const handleConfirmAccountDelete = async () => {
    if (!pendingAccountDelete || accountDeleteLoading) return;

    try {
      setAccountDeleteLoading(true);
      setWriteWarning(null);
      await portfolioApi.deleteAccount(pendingAccountDelete.accountId);
      const nextAccount = accounts.find((item) => item.id !== pendingAccountDelete.accountId);
      setSelectedAccount(nextAccount?.id ?? 'all');
      setPendingAccountDelete(null);
      setShowCreateAccount(!nextAccount);
      await loadAccounts();
      setEventPage(1);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setAccountDeleteLoading(false);
    }
  };

  /**
   * 确认删除事件记录
   * 根据事件类型调用对应删除 API，删除最后一条时自动回退到上一页
   */
  const handleConfirmDelete = async () => {
    if (!pendingDelete || deleteLoading) return;
    if (!writableAccountId) {
      setWriteWarning('请先在右上角选择具体账户，再进行删除修正。');
      setPendingDelete(null);
      return;
    }

    const nextPage = currentEventCount === 1 && eventPage > 1 ? eventPage - 1 : eventPage;
    try {
      setDeleteLoading(true);
      setWriteWarning(null);
      if (pendingDelete.eventType === 'trade') {
        await portfolioApi.deleteTrade(pendingDelete.id);
      } else if (pendingDelete.eventType === 'cash') {
        await portfolioApi.deleteCashLedger(pendingDelete.id);
      } else {
        await portfolioApi.deleteCorporateAction(pendingDelete.id);
      }
      setPendingDelete(null);
      if (nextPage !== eventPage) {
        setEventPage(nextPage);
      }
      await refreshPortfolioData(nextPage);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setDeleteLoading(false);
    }
  };

  /**
   * 创建新账户
   * 验证账户名称后调用创建 API，成功后自动切换到新账户并收起表单
   * @param e - 表单提交事件
   */
  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = accountForm.name.trim();
    if (!name) {
      setAccountCreateError('账户名称不能为空。');
      setAccountCreateSuccess(null);
      return;
    }
    try {
      setAccountCreating(true);
      setAccountCreateError(null);
      setAccountCreateSuccess(null);
      const created = await portfolioApi.createAccount({
        name,
        broker: accountForm.broker.trim() || undefined,
        market: accountForm.market,
        baseCurrency: accountForm.baseCurrency.trim() || 'CNY',
      });
      await loadAccounts();
      setSelectedAccount(created.id);
      setShowCreateAccount(false);
      setWriteWarning(null);
      setAccountForm({
        name: '',
        broker: 'Demo',
        market: accountForm.market,
        baseCurrency: accountForm.baseCurrency,
      });
      setAccountCreateSuccess('账户创建成功，已自动切换到该账户。');
    } catch (err) {
      const parsed = getParsedApiError(err);
      setAccountCreateError(parsed.message || '创建账户失败，请稍后重试。');
      setAccountCreateSuccess(null);
    } finally {
      setAccountCreating(false);
    }
  };

  /** 手动刷新全部数据：并行加载账户、快照/风险、事件记录和券商列表，并触发决策信号刷新 */
  const handleRefresh = async () => {
    await Promise.all([loadAccounts(), loadSnapshotAndRisk(), loadEvents(), loadBrokers()]);
    setPortfolioSignalsRefreshKey((current) => current + 1);
  };

  /**
   * 在指定刷新上下文中重新加载快照和风险数据
   * 每步都检查上下文是否仍然有效，避免视图切换后旧请求覆盖新状态
   * @param requestedViewKey - 请求时的视图标识
   * @param requestedRequestId - 请求时的序列号
   * @param requestedAccountId - 请求时的账户 ID
   * @param requestedCostMethod - 请求时的成本计算方式
   * @returns 是否成功加载（上下文失效时返回 false）
   */
  const reloadSnapshotAndRiskForScope = useCallback(async (
    requestedViewKey: string,
    requestedRequestId: number,
    requestedAccountId: number | undefined,
    requestedCostMethod: PortfolioCostMethod,
  ): Promise<boolean> => {
    if (!isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
      return false;
    }

    setRiskWarning(null);

    try {
      const snapshotData = await portfolioApi.getSnapshot({
        accountId: requestedAccountId,
        costMethod: requestedCostMethod,
        includeRealtime: false,
      });
      if (!isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
        return false;
      }
      setSnapshot(snapshotData);
      setError(null);

      try {
        const riskData = await portfolioApi.getRisk({
          accountId: requestedAccountId,
          costMethod: requestedCostMethod,
          includeRealtime: false,
        });
        if (!isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
          return false;
        }
        setRisk(riskData);
        setRiskWarning(null);
      } catch (riskErr) {
        if (!isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
          return false;
        }
        setRisk(null);
        const parsed = getParsedApiError(riskErr);
        setRiskWarning(parsed.message || '风险数据获取失败，已降级为仅展示快照数据。');
      }
      return true;
    } catch (err) {
      if (!isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
        return false;
      }
      setSnapshot(null);
      setRisk(null);
      setError(getParsedApiError(err));
      return false;
    }
  }, []);

  /**
   * 刷新汇率数据
   * 调用后端汇率刷新接口后重新加载快照/风险数据，使用刷新上下文防止竞态条件
   */
  const handleRefreshFx = async () => {
    if (!hasAccounts || isLoading || fxRefreshing) {
      return;
    }

    const requestedViewKey = refreshViewKey;
    const requestedAccountId = queryAccountId;
    const requestedCostMethod = costMethod;
    const requestedRequestId = refreshContextRef.current.requestId + 1;
    refreshContextRef.current = {
      viewKey: requestedViewKey,
      requestId: requestedRequestId,
    };

    try {
      setFxRefreshing(true);
      setFxRefreshFeedback(null);
      const result = await portfolioApi.refreshFx({
        accountId: requestedAccountId,
      });
      if (!isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
        return;
      }
      const reloaded = await reloadSnapshotAndRiskForScope(
        requestedViewKey,
        requestedRequestId,
        requestedAccountId,
        requestedCostMethod,
      );
      if (!reloaded || !isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
        return;
      }
      setFxRefreshFeedback(buildFxRefreshFeedback(result));
    } catch (err) {
      if (!isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
        return;
      }
      setError(getParsedApiError(err));
    } finally {
      if (isActiveRefreshContext(requestedViewKey, requestedRequestId)) {
        setFxRefreshing(false);
      }
    }
  };

  // AI 风险信号预览项：取前 3 条用于卡片展示
  const decisionSignalRiskPreviewItems = (risk?.decisionSignalRisk?.items ?? []).slice(0, 3);
  // 格式化决策信号风险动作标签：将信号动作转换为用户可读的标签文本
  const formatDecisionSignalRiskAction = (signal: Partial<DecisionSignalItem>): string => (
    getDecisionActionLabel(
      signal.action,
      signal.actionLabel,
      null,
      text.alert,
      decisionActionLabels,
    ) ?? text.alert
  );
  // 快照数据质量提示：当数据为部分口径时，将限制标签拼接为本地化提示文本
  const snapshotQualityMessage = snapshot?.dataQuality === 'partial' && snapshot.limitations?.length
    ? snapshot.limitations
      .map((limitation) => formatPortfolioLimitation(limitation, toCnOrEn(language)))
      .join(language === 'en' ? '; ' : '；')
    : null;

  return (
    <div className="portfolio-page min-h-screen space-y-4 p-4 md:p-6">
      {/* ===== 页面标题与账户选择区 ===== */}
      <section className="space-y-3">
        <div className="space-y-2">
          <p className="text-xs md:text-sm text-secondary">
            {text.description}
          </p>
        </div>
        {hasAccounts ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
            <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_220px_280px] gap-2 items-end">
              <div>
                <p className="text-xs text-secondary mb-1">{text.accountView}</p>
                <select
                  value={String(selectedAccount)}
                  onChange={(e) => setSelectedAccount(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                  className={PORTFOLIO_SELECT_CLASS}
                >
                  <option value="all">{text.allAccounts}</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name} (#{account.id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <p className="text-xs text-secondary mb-1">{text.costMethod}</p>
                <select
                  value={costMethod}
                  onChange={(e) => setCostMethod(e.target.value as PortfolioCostMethod)}
                  className={PORTFOLIO_SELECT_CLASS}
                >
                  <option value="fifo">{text.fifo}</option>
                  <option value="avg">{text.avg}</option>
                </select>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary text-sm flex-1"
                  onClick={() => {
                    setShowCreateAccount((prev) => !prev);
                    setAccountCreateError(null);
                    setAccountCreateSuccess(null);
                  }}
                >
                  {showCreateAccount ? text.collapseCreate : text.createAccount}
                </button>
                <button
                  type="button"
                  onClick={() => void handleRefresh()}
                  disabled={isLoading || fxRefreshing}
                  className="btn-secondary text-sm flex-1"
                >
                  {isLoading ? text.refreshing : text.refreshData}
                </button>
                <button
                  type="button"
                  onClick={openAccountDeleteDialog}
                  disabled={!canDeleteSelectedAccount}
                  className="btn-secondary text-sm flex-1 border-red-400/40 text-red-100 hover:bg-red-500/15 disabled:border-white/10 disabled:text-secondary"
                >
                  {accountDeleteLoading ? text.deletingAccount : text.deleteAccount}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <InlineAlert
            variant="warning"
            className="inline-block rounded-lg px-3 py-2 text-xs shadow-none"
            message={text.noAccounts}
          />
        )}
      </section>

      {/* ===== 全局提示区（错误/风险/写入/分析提示）===== */}
      {error ? <InlineTipCard variant="danger" content={error} onDismiss={() => setError(null)} /> : null}
      {riskWarning ? (
        <InlineAlert
          variant="warning"
          title={text.riskDegraded}
          message={riskWarning}
        />
      ) : null}
      {writeWarning ? (
        <InlineAlert
          variant="warning"
          title={text.operationHint}
          message={writeWarning}
        />
      ) : null}
      {positionAnalysisMessage ? (
        <InlineAlert
          variant="success"
          title={text.analysisTask}
          message={positionAnalysisMessage}
        />
      ) : null}

      {/* ===== 新建账户表单区 ===== */}
      {(showCreateAccount || !hasAccounts) ? (
        <Card padding="md">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-foreground">新建账户</h2>
            {hasAccounts ? (
              <button
                type="button"
                className="btn-secondary text-xs px-3 py-1"
                onClick={() => {
                  setShowCreateAccount(false);
                  setAccountCreateError(null);
                  setAccountCreateSuccess(null);
                }}
              >
                收起
              </button>
            ) : (
              <span className="text-xs text-secondary">创建后自动切换到该账户</span>
            )}
          </div>
          {accountCreateError ? (
            <InlineAlert
              variant="danger"
              className="mt-2 rounded-lg px-2 py-1 text-xs shadow-none"
              title="创建账户失败"
              message={accountCreateError}
            />
          ) : null}
          {accountCreateSuccess ? (
            <InlineAlert
              variant="success"
              className="mt-2 rounded-lg px-2 py-1 text-xs shadow-none"
              title="创建账户成功"
              message={accountCreateSuccess}
            />
          ) : null}
          <form className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2" onSubmit={handleCreateAccount}>
            <input
              className={`${PORTFOLIO_INPUT_CLASS} md:col-span-2`}
              placeholder="账户名称（必填）"
              value={accountForm.name}
              onChange={(e) => setAccountForm((prev) => ({ ...prev, name: e.target.value }))}
            />
            <input
              className={PORTFOLIO_INPUT_CLASS}
              placeholder="券商（可选，如 Demo/华泰）"
              value={accountForm.broker}
              onChange={(e) => setAccountForm((prev) => ({ ...prev, broker: e.target.value }))}
            />
            <input
              className={PORTFOLIO_INPUT_CLASS}
              placeholder="基准币（如 CNY/USD/HKD）"
              value={accountForm.baseCurrency}
              onChange={(e) => setAccountForm((prev) => ({ ...prev, baseCurrency: e.target.value.toUpperCase() }))}
            />
            <select
              className={PORTFOLIO_SELECT_CLASS}
              value={accountForm.market}
              onChange={(e) => setAccountForm((prev) => ({ ...prev, market: e.target.value as PortfolioAccountMarket }))}
            >
              <option value="cn">市场：A 股（cn）</option>
              <option value="hk">市场：港股（hk）</option>
              <option value="us">市场：美股（us）</option>
              <option value="jp">市场：日股（jp）</option>
              <option value="kr">市场：韩股（kr）</option>
              <option value="tw">市场：台股（tw）</option>
            </select>
            <button type="submit" className="btn-secondary text-sm" disabled={accountCreating}>
              {accountCreating ? '创建中...' : '创建账户'}
            </button>
          </form>
        </Card>
      ) : null}

      {/* ===== 快照数据质量提示区 ===== */}
      {snapshotQualityMessage ? (
        <InlineAlert
          variant="warning"
          title={text.snapshotPartialTitle}
          message={snapshotQualityMessage}
          className="rounded-xl px-3 py-2 text-xs shadow-none"
        />
      ) : null}

      {/* ===== 总览统计卡片区（总权益/市值/现金/汇率状态）===== */}
      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <Card variant="gradient" padding="md">
          <p className="text-xs text-secondary">{text.totalEquity}</p>
          <p className="mt-1 text-xl font-semibold text-foreground">{formatMoney(snapshot?.totalEquity, snapshot?.currency || 'CNY')}</p>
        </Card>
        <Card variant="gradient" padding="md">
          <p className="text-xs text-secondary">{text.totalMarketValue}</p>
          <p className="mt-1 text-xl font-semibold text-foreground">{formatMoney(snapshot?.totalMarketValue, snapshot?.currency || 'CNY')}</p>
        </Card>
        <Card variant="gradient" padding="md">
          <p className="text-xs text-secondary">{text.totalCash}</p>
          <p className="mt-1 text-xl font-semibold text-foreground">{formatMoney(snapshot?.totalCash, snapshot?.currency || 'CNY')}</p>
        </Card>
        <Card variant="gradient" padding="md">
          <div className="flex items-start justify-between gap-3">
            <p className="text-xs text-secondary">{text.fxStatus}</p>
            <button
              type="button"
              className="btn-secondary !px-3 !py-1 !text-xs shrink-0"
              onClick={() => void handleRefreshFx()}
              disabled={!hasAccounts || isLoading || fxRefreshing}
            >
              {fxRefreshing ? text.refreshing : text.refreshFx}
            </button>
          </div>
          <div className="mt-2">{snapshot?.fxStale ? <Badge variant="warning">{text.stale}</Badge> : <Badge variant="success">{text.latest}</Badge>}</div>
          {fxRefreshFeedback ? (
            <InlineAlert
              variant={getFxRefreshFeedbackVariant(fxRefreshFeedback.tone)}
              title={text.fxRefreshResult}
              message={fxRefreshFeedback.text}
              className="mt-3 rounded-xl px-3 py-2 text-xs shadow-none"
            />
          ) : null}
        </Card>
      </section>

      {/* ===== 持仓表格与集中度饼图区 ===== */}
      <section className="grid grid-cols-1 xl:grid-cols-3 gap-3">
        <Card className="xl:col-span-2" padding="md">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-foreground">{text.positionsTitle}</h2>
            <span className="text-xs text-secondary">{formatUiText(text.countItems, { count: positionRows.length })}</span>
          </div>
          {portfolioSignalsWarning ? (
            <InlineAlert
              variant="warning"
              title={t('decisionSignals.portfolioWarningTitle')}
              message={portfolioSignalsWarning}
              className="mb-3 rounded-xl px-3 py-2 text-xs shadow-none"
            />
          ) : null}
          {positionRows.length === 0 ? (
            <EmptyState
              title={text.noPositionsTitle}
              description={text.noPositionsDescription}
              className="border-none bg-transparent px-4 py-8 shadow-none"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-[860px] w-full text-sm">
                <thead className="text-xs text-secondary border-b border-white/10">
                  <tr>
                    <th className="text-left py-2 pr-2">{text.account}</th>
                    <th className="text-left py-2 pr-2">{text.code}</th>
                    <th className="text-right py-2 pr-2">{text.quantity}</th>
                    <th className="text-right py-2 pr-2">{text.avgCost}</th>
                    <th className="text-right py-2 pr-2">{text.lastPrice}</th>
                    <th className="text-right py-2 pr-2">{text.marketValue}</th>
                    <th className="text-right py-2 pr-3">{text.unrealizedPnl}</th>
                    <th className="text-right py-2 pr-3">{text.returnPct}</th>
                    <th className="min-w-[9rem] text-right py-2 pr-3">{t('decisionSignals.portfolioColumn')}</th>
                    <th className="w-20 text-right py-2">{text.action}</th>
                  </tr>
                </thead>
                <tbody>
                  {positionRows.map((row) => {
                    const rowKey = `${row.accountId}-${row.symbol}-${row.market}`;
                    const analyzing = positionAnalysisLoadingKey === rowKey;
                    const signal = signalByPositionKey.get(rowKey);
                    return (
                    <tr key={rowKey} className="border-b border-white/5">
                      <td className="py-2 pr-2 text-secondary">{row.accountName}</td>
                      <td className="py-2 pr-2 font-mono text-foreground">{row.symbol}</td>
                      <td className="py-2 pr-2 text-right">{row.quantity.toFixed(2)}</td>
                      <td className="py-2 pr-2 text-right">{row.avgCost.toFixed(4)}</td>
                      <td className="py-2 pr-2 text-right">
                        <div>{formatPositionPrice(row)}</div>
                        <div className={`text-[11px] ${hasPositionPrice(row) ? 'text-secondary' : 'text-warning'}`}>
                          {getPositionPriceLabel(row)}
                        </div>
                      </td>
                      <td className="py-2 pr-2 text-right">{formatPositionMoney(row.marketValueBase, row)}</td>
                      <td
                        className={`py-2 pr-3 text-right ${
                          hasPositionPrice(row)
                            ? row.unrealizedPnlBase >= 0
                              ? 'text-success'
                              : 'text-danger'
                            : 'text-secondary'
                        }`}
                      >
                        {formatPositionMoney(row.unrealizedPnlBase, row)}
                      </td>
                      <td
                        className={`py-2 pr-3 text-right ${
                          hasPositionPrice(row) && row.unrealizedPnlPct !== null && row.unrealizedPnlPct !== undefined
                            ? row.unrealizedPnlPct >= 0
                              ? 'text-success'
                              : 'text-danger'
                            : 'text-secondary'
                        }`}
                      >
                        {formatSignedPct(row.unrealizedPnlPct)}
                      </td>
                      <td className="py-2 pr-3 text-right align-top">
                        <PortfolioSignalSummary item={signal} loading={portfolioSignalsLoading} />
                      </td>
                      <td className="py-2 text-right">
                        <button
                          type="button"
                          onClick={() => void handleAnalyzePosition(row)}
                          disabled={analyzing}
                          className="btn-secondary px-2 py-1 text-xs disabled:cursor-wait disabled:opacity-60"
                        >
                          {analyzing ? text.submitting : text.analyze}
                        </button>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card padding="md">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            {concentrationMode === 'sector' ? text.sectorConcentration : text.positionConcentrationFallback}
          </h2>
          {concentrationPieData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={concentrationPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90}>
                    {concentrationPieData.map((entry, index) => (
                      <Cell key={`cell-${entry.name}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `${Number(value).toFixed(2)}%`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              title={text.noConcentrationTitle}
              description={text.noConcentrationDescription}
              className="border-none bg-transparent px-4 py-10 shadow-none"
            />
          )}
          <div className="mt-3 text-xs text-secondary space-y-1">
            <div>{text.displayScope}: {concentrationMode === 'sector' ? text.sectorDimension : text.positionDimensionFallback}</div>
            <div>{text.sectorAlert}: {risk?.sectorConcentration?.alert ? text.yes : text.no}</div>
            <div>{text.topWeight}: {formatPct(risk?.sectorConcentration?.topWeightPct ?? risk?.concentration?.topWeightPct)}</div>
          </div>
        </Card>
      </section>

      {/* ===== 写入限制提示 ===== */}
      {writeBlocked && hasAccounts ? (
        <InlineAlert
          variant="warning"
          className="rounded-lg px-3 py-2 text-xs shadow-none"
          message={text.writeBlocked}
        />
      ) : null}

      {/* ===== 风险指标卡片区（回撤/止损/范围/AI 风险信号）===== */}
      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.drawdownMonitor}</h3>
          <div className="text-xs text-secondary space-y-1">
            <div>{text.maxDrawdown}: {formatPct(risk?.drawdown?.maxDrawdownPct)}</div>
            <div>{text.currentDrawdown}: {formatPct(risk?.drawdown?.currentDrawdownPct)}</div>
            <div>{text.alert}: {risk?.drawdown?.alert ? text.yes : text.no}</div>
          </div>
        </Card>
        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.stopLossWarning}</h3>
          <div className="text-xs text-secondary space-y-1">
            <div>{text.triggeredCount}: {risk?.stopLoss?.triggeredCount ?? 0}</div>
            <div>{text.nearCount}: {risk?.stopLoss?.nearCount ?? 0}</div>
            <div>{text.alert}: {risk?.stopLoss?.nearAlert ? text.yes : text.no}</div>
          </div>
        </Card>
        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.scope}</h3>
          <div className="text-xs text-secondary space-y-1">
            <div>{text.accountCount}: {snapshot?.accountCount ?? 0}</div>
            <div>{text.currency}: {snapshot?.currency || 'CNY'}</div>
            <div>{text.costMethodShort}: {(snapshot?.costMethod || costMethod).toUpperCase()}</div>
          </div>
        </Card>
        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.aiRiskSignals}</h3>
          <div className="text-xs text-secondary space-y-1">
            {risk?.decisionSignalRisk?.available === false ? (
              <div className="text-warning">{text.aiRiskUnavailable}</div>
            ) : (
              <>
                <div>{text.aiRiskTotal}: {risk?.decisionSignalRisk?.total ?? 0}</div>
                <div>
                  {text.sellSignals}: {risk?.decisionSignalRisk?.actions?.sell ?? 0} · {text.reduceSignals}: {risk?.decisionSignalRisk?.actions?.reduce ?? 0} · {text.alertSignals}: {risk?.decisionSignalRisk?.actions?.alert ?? 0}
                </div>
                {decisionSignalRiskPreviewItems.length > 0 ? (
                  <div className="space-y-1 pt-1">
                    {decisionSignalRiskPreviewItems.map((item) => (
                      <div key={`${item.accountId ?? 'all'}-${item.market}-${item.symbol}-${item.signal.id ?? item.signal.action}`} className="truncate text-foreground">
                        {item.symbol} · {formatDecisionSignalRiskAction(item.signal)}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div>{text.noAiRiskSignals}</div>
                )}
              </>
            )}
          </div>
        </Card>
      </section>

      {/* ===== 手工录入表单区（交易/资金/公司行为）===== */}
      <section className="grid grid-cols-1 xl:grid-cols-3 gap-3">
        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-3">手工录入：交易</h3>
          <form className="space-y-2" onSubmit={handleTradeSubmit}>
            <input className={PORTFOLIO_INPUT_CLASS} placeholder="股票代码（例如 600519）" value={tradeForm.symbol}
              onChange={(e) => setTradeForm((prev) => ({ ...prev, symbol: e.target.value }))} required />
            <div className="grid grid-cols-2 gap-2">
              <input className={PORTFOLIO_INPUT_CLASS} type="date" value={tradeForm.tradeDate}
                onChange={(e) => setTradeForm((prev) => ({ ...prev, tradeDate: e.target.value }))} required />
              <select className={PORTFOLIO_SELECT_CLASS} value={tradeForm.side}
                onChange={(e) => setTradeForm((prev) => ({ ...prev, side: e.target.value as PortfolioSide }))}>
                <option value="buy">买入</option>
                <option value="sell">卖出</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input className={PORTFOLIO_INPUT_CLASS} type="number" min="0" step="0.0001" placeholder="数量（必填）" value={tradeForm.quantity}
                onChange={(e) => setTradeForm((prev) => ({ ...prev, quantity: e.target.value }))} required />
              <input className={PORTFOLIO_INPUT_CLASS} type="number" min="0" step="0.0001" placeholder="成交价（必填）" value={tradeForm.price}
                onChange={(e) => setTradeForm((prev) => ({ ...prev, price: e.target.value }))} required />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input className={PORTFOLIO_INPUT_CLASS} type="number" min="0" step="0.0001" placeholder="手续费（可选）" value={tradeForm.fee}
                onChange={(e) => setTradeForm((prev) => ({ ...prev, fee: e.target.value }))} />
              <input className={PORTFOLIO_INPUT_CLASS} type="number" min="0" step="0.0001" placeholder="税费（可选）" value={tradeForm.tax}
                onChange={(e) => setTradeForm((prev) => ({ ...prev, tax: e.target.value }))} />
            </div>
            <p className="text-xs text-secondary">手续费和税费可留空，系统将按 0 处理。</p>
            <button type="submit" className="btn-secondary w-full" disabled={!writableAccountId}>提交交易</button>
          </form>
        </Card>

        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-3">手工录入：资金流水</h3>
          <form className="space-y-2" onSubmit={handleCashSubmit}>
            <div className="grid grid-cols-2 gap-2">
              <input className={PORTFOLIO_INPUT_CLASS} type="date" value={cashForm.eventDate}
                onChange={(e) => setCashForm((prev) => ({ ...prev, eventDate: e.target.value }))} required />
              <select className={PORTFOLIO_SELECT_CLASS} value={cashForm.direction}
                onChange={(e) => setCashForm((prev) => ({ ...prev, direction: e.target.value as PortfolioCashDirection }))}>
                <option value="in">流入</option>
                <option value="out">流出</option>
              </select>
            </div>
            <input className={PORTFOLIO_INPUT_CLASS} type="number" min="0" step="0.0001" placeholder="金额"
              value={cashForm.amount} onChange={(e) => setCashForm((prev) => ({ ...prev, amount: e.target.value }))} required />
            <input className={PORTFOLIO_INPUT_CLASS} placeholder={`币种（可选，默认 ${writableAccount?.baseCurrency || '账户基准币'}）`} value={cashForm.currency}
              onChange={(e) => setCashForm((prev) => ({ ...prev, currency: e.target.value }))} />
            <button type="submit" className="btn-secondary w-full" disabled={!writableAccountId}>提交资金流水</button>
          </form>
        </Card>

        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-3">手工录入：公司行为</h3>
          <form className="space-y-2" onSubmit={handleCorporateSubmit}>
            <input className={PORTFOLIO_INPUT_CLASS} placeholder="股票代码" value={corpForm.symbol}
              onChange={(e) => setCorpForm((prev) => ({ ...prev, symbol: e.target.value }))} required />
            <div className="grid grid-cols-2 gap-2">
              <input className={PORTFOLIO_INPUT_CLASS} type="date" value={corpForm.effectiveDate}
                onChange={(e) => setCorpForm((prev) => ({ ...prev, effectiveDate: e.target.value }))} required />
              <select className={PORTFOLIO_SELECT_CLASS} value={corpForm.actionType}
                onChange={(e) => setCorpForm((prev) => ({ ...prev, actionType: e.target.value as PortfolioCorporateActionType }))}>
                <option value="cash_dividend">现金分红</option>
                <option value="split_adjustment">拆并股调整</option>
              </select>
            </div>
            {corpForm.actionType === 'cash_dividend' ? (
              <input className={PORTFOLIO_INPUT_CLASS} type="number" min="0" step="0.000001" placeholder="每股分红"
                value={corpForm.cashDividendPerShare}
                onChange={(e) => setCorpForm((prev) => ({ ...prev, cashDividendPerShare: e.target.value, splitRatio: '' }))} required />
            ) : (
              <input className={PORTFOLIO_INPUT_CLASS} type="number" min="0" step="0.000001" placeholder="拆并股比例"
                value={corpForm.splitRatio}
                onChange={(e) => setCorpForm((prev) => ({ ...prev, splitRatio: e.target.value, cashDividendPerShare: '' }))} required />
            )}
            <button type="submit" className="btn-secondary w-full" disabled={!writableAccountId}>提交企业行为</button>
          </form>
        </Card>
      </section>

      {/* ===== CSV 导入与事件记录区 ===== */}
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-3">券商 CSV 导入</h3>
          <div className="space-y-2">
            {brokerLoadWarning ? (
              <InlineAlert
                variant="warning"
                className="rounded-lg px-2 py-1 text-xs shadow-none"
                message={brokerLoadWarning}
              />
            ) : null}
            <div className="grid grid-cols-2 gap-2">
              <select className={PORTFOLIO_SELECT_CLASS} value={selectedBroker} onChange={(e) => setSelectedBroker(e.target.value)}>
                {brokers.length > 0 ? (
                  brokers.map((item) => <option key={item.broker} value={item.broker}>{formatBrokerLabel(item.broker, item.displayName)}</option>)
                ) : (
                  <option value="huatai">huatai（华泰）</option>
                )}
              </select>
              <label className={PORTFOLIO_FILE_PICKER_CLASS}>
                选择 CSV
                <input type="file" accept=".csv" className="hidden"
                  onChange={(e) => setCsvFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)} />
              </label>
            </div>
            <div className="flex items-center gap-2 text-xs text-secondary">
              <input id="csv-dry-run" type="checkbox" checked={csvDryRun} onChange={(e) => setCsvDryRun(e.target.checked)} />
              <label htmlFor="csv-dry-run">仅预演（不写入）</label>
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary flex-1" disabled={!csvFile || csvParsing} onClick={() => void handleParseCsv()}>
                {csvParsing ? '解析中...' : '解析文件'}
              </button>
              <button type="button" className="btn-secondary flex-1"
                disabled={!csvFile || !writableAccountId || csvCommitting} onClick={() => void handleCommitCsv()}>
                {csvCommitting ? '提交中...' : '提交导入'}
              </button>
            </div>
            {csvParseResult ? (
              <InlineAlert
                variant={getCsvParseVariant(csvParseResult)}
                title="CSV 解析结果"
                message={`有效 ${csvParseResult.recordCount} 条，跳过 ${csvParseResult.skippedCount} 条，错误 ${csvParseResult.errorCount} 条。`}
                className="rounded-lg px-3 py-2 text-xs shadow-none"
              />
            ) : null}
            {csvCommitResult ? (
              <InlineAlert
                variant={getCsvCommitVariant(csvCommitResult, csvDryRun)}
                title={csvDryRun ? 'CSV 预演结果' : 'CSV 提交结果'}
                message={`${csvDryRun ? '预演检查' : '实际写入'}：写入 ${csvCommitResult.insertedCount} 条，重复 ${csvCommitResult.duplicateCount} 条，失败 ${csvCommitResult.failedCount} 条。`}
                className="rounded-lg px-3 py-2 text-xs shadow-none"
              />
            ) : null}
          </div>
        </Card>

        <Card padding="md">
          <h3 className="text-sm font-semibold text-foreground mb-3">事件记录</h3>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <select className={PORTFOLIO_SELECT_CLASS} value={eventType} onChange={(e) => setEventType(e.target.value as EventType)}>
                <option value="trade">交易流水</option>
                <option value="cash">资金流水</option>
                <option value="corporate">公司行为</option>
              </select>
              <button type="button" className="btn-secondary text-sm" onClick={() => void loadEvents()} disabled={eventLoading}>
                {eventLoading ? '加载中...' : '刷新流水'}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input className={PORTFOLIO_INPUT_CLASS} type="date" value={eventDateFrom} onChange={(e) => setEventDateFrom(e.target.value)} />
              <input className={PORTFOLIO_INPUT_CLASS} type="date" value={eventDateTo} onChange={(e) => setEventDateTo(e.target.value)} />
            </div>
            {(eventType === 'trade' || eventType === 'corporate') ? (
              <input className={PORTFOLIO_INPUT_CLASS} placeholder="按股票代码筛选" value={eventSymbol}
                onChange={(e) => setEventSymbol(e.target.value)} />
            ) : null}
            {eventType === 'trade' ? (
              <select className={PORTFOLIO_SELECT_CLASS} value={eventSide} onChange={(e) => setEventSide(e.target.value as '' | PortfolioSide)}>
                <option value="">全部买卖方向</option>
                <option value="buy">买入</option>
                <option value="sell">卖出</option>
              </select>
            ) : null}
            {eventType === 'cash' ? (
              <select className={PORTFOLIO_SELECT_CLASS} value={eventDirection}
                onChange={(e) => setEventDirection(e.target.value as '' | PortfolioCashDirection)}>
                <option value="">全部资金方向</option>
                <option value="in">流入</option>
                <option value="out">流出</option>
              </select>
            ) : null}
            {eventType === 'corporate' ? (
              <select className={PORTFOLIO_SELECT_CLASS} value={eventActionType}
                onChange={(e) => setEventActionType(e.target.value as '' | PortfolioCorporateActionType)}>
                <option value="">全部公司行为</option>
                <option value="cash_dividend">现金分红</option>
                <option value="split_adjustment">拆并股调整</option>
              </select>
            ) : null}
            <div className="text-[11px] text-secondary">
              {writeBlocked ? '删除修正仅在单账户视图可用。请先选择具体账户后再删除错误流水。' : '如有错误流水，可直接删除后重新录入。'}
            </div>
            <div className="max-h-64 overflow-auto rounded-lg border border-white/10 p-2">
              {eventType === 'trade' && tradeEvents.map((item) => (
                <div key={`t-${item.id}`} className="flex items-start justify-between gap-3 border-b border-white/5 py-2 text-xs text-secondary">
                  <div className="min-w-0">
                    {item.tradeDate} {formatSideLabel(item.side)} {item.symbol} 数量={item.quantity} 价格={item.price}
                  </div>
                  {!writeBlocked ? (
                    <button
                      type="button"
                      className="btn-secondary shrink-0 !px-3 !py-1 !text-[11px]"
                      onClick={() => openDeleteDialog({
                        eventType: 'trade',
                        id: item.id,
                        message: `确认删除 ${item.tradeDate} 的${formatSideLabel(item.side)}流水 ${item.symbol}（数量 ${item.quantity}，价格 ${item.price}）吗？`,
                      })}
                    >
                      删除
                    </button>
                  ) : null}
                </div>
              ))}
              {eventType === 'cash' && cashEvents.map((item) => (
                <div key={`c-${item.id}`} className="flex items-start justify-between gap-3 border-b border-white/5 py-2 text-xs text-secondary">
                  <div className="min-w-0">
                    {item.eventDate} {formatCashDirectionLabel(item.direction)} {item.amount} {item.currency}
                  </div>
                  {!writeBlocked ? (
                    <button
                      type="button"
                      className="btn-secondary shrink-0 !px-3 !py-1 !text-[11px]"
                      onClick={() => openDeleteDialog({
                        eventType: 'cash',
                        id: item.id,
                        message: `确认删除 ${item.eventDate} 的资金流水（${formatCashDirectionLabel(item.direction)} ${item.amount} ${item.currency}）吗？`,
                      })}
                    >
                      删除
                    </button>
                  ) : null}
                </div>
              ))}
              {eventType === 'corporate' && corporateEvents.map((item) => (
                <div key={`ca-${item.id}`} className="flex items-start justify-between gap-3 border-b border-white/5 py-2 text-xs text-secondary">
                  <div className="min-w-0">
                    {item.effectiveDate} {formatCorporateActionLabel(item.actionType)} {item.symbol}
                  </div>
                  {!writeBlocked ? (
                    <button
                      type="button"
                      className="btn-secondary shrink-0 !px-3 !py-1 !text-[11px]"
                      onClick={() => openDeleteDialog({
                        eventType: 'corporate',
                        id: item.id,
                        message: `确认删除 ${item.effectiveDate} 的公司行为 ${formatCorporateActionLabel(item.actionType)}（${item.symbol}）吗？`,
                      })}
                    >
                      删除
                    </button>
                  ) : null}
                </div>
              ))}
              {!eventLoading
                && ((eventType === 'trade' && tradeEvents.length === 0)
                  || (eventType === 'cash' && cashEvents.length === 0)
                  || (eventType === 'corporate' && corporateEvents.length === 0)) ? (
                    <EmptyState
                      title="暂无流水"
                      description="调整筛选条件或先录入一笔交易、资金流水或公司行为。"
                      className="border-none bg-transparent px-3 py-6 shadow-none"
                    />
                  ) : null}
            </div>
            <div className="flex items-center justify-between text-xs text-secondary">
              <span>第 {eventPage} / {totalEventPages} 页</span>
              <div className="flex gap-2">
                <button type="button" className="btn-secondary text-xs px-3 py-1" disabled={eventPage <= 1}
                  onClick={() => setEventPage((prev) => Math.max(1, prev - 1))}>
                  上一页
                </button>
                <button type="button" className="btn-secondary text-xs px-3 py-1" disabled={eventPage >= totalEventPages}
                  onClick={() => setEventPage((prev) => Math.min(totalEventPages, prev + 1))}>
                  下一页
                </button>
              </div>
            </div>
          </div>
        </Card>
      </section>
      {/* ===== 确认对话框区（事件删除/账户删除）===== */}
      <ConfirmDialog
        isOpen={Boolean(pendingDelete)}
        title="删除错误流水"
        message={pendingDelete?.message || '确认删除这条流水吗？'}
        confirmText={deleteLoading ? '删除中...' : '确认删除'}
        cancelText="取消"
        isDanger
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => {
          if (!deleteLoading) {
            setPendingDelete(null);
          }
        }}
      />
      <ConfirmDialog
        isOpen={Boolean(pendingAccountDelete)}
        title={text.deleteAccountTitle}
        message={
          pendingAccountDelete
            ? formatUiText(text.deleteAccountMessage, {
              name: pendingAccountDelete.accountName,
              id: pendingAccountDelete.accountId,
            })
            : ''
        }
        confirmText={accountDeleteLoading ? text.deletingAccount : text.deleteAccountConfirm}
        isDanger
        onConfirm={() => void handleConfirmAccountDelete()}
        onCancel={() => {
          if (!accountDeleteLoading) {
            setPendingAccountDelete(null);
          }
        }}
      />
    </div>
  );
};

export default PortfolioPage;
