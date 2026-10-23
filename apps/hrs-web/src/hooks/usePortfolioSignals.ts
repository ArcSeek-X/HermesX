/**
 * 组合页（PortfolioPage）持仓决策信号 Hook
 *
 * 负责持仓行的扁平化、账户范围匹配判定、去重信号查询参数生成，
 * 以及决策信号的并发批量加载、竞态守卫、行-信号映射与单持仓分析提交。
 * 主页面仅传入已加载好的快照/风险与当前账户范围，并接收统一的错误/
 * 分析消息回调，自身不做账户范围决策。
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { formatUiText } from '../i18n/uiText';
import { areStockCodesEquivalent, normalizeStockCode } from '@utils/stock/stockCode';
import { parseDecisionSignalDate } from '@utils/decisionSignalTime';
import { getParsedApiError } from '../api/error';
import { decisionSignalsApi } from '../api/decisionSignals';
import { portfolioApi } from '../api/portfolio';
import type { DecisionSignalItem, DecisionSignalMarket } from '../types/decisionSignals';
import type { FlatPosition, PortfolioSnapshotResponse } from '../types/portfolio';

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

/** 持仓决策信号查询并发数 */
const PORTFOLIO_SIGNAL_LOOKUP_CONCURRENCY = 6;

/** 决策信号支持的地区市场集合 */
const DECISION_SIGNAL_MARKETS = new Set<DecisionSignalMarket>(['cn', 'hk', 'us', 'jp', 'kr', 'tw']);

/** 获取决策信号的时间戳（毫秒），优先使用创建时间，其次更新时间 */
function getSignalTime(item: DecisionSignalItem): number {
  return parseDecisionSignalDate(item.createdAt)?.getTime()
    ?? parseDecisionSignalDate(item.updatedAt)?.getTime()
    ?? 0;
}

/** 判断 right 信号是否比 left 信号更新 */
function isNewerSignal(left: DecisionSignalItem | undefined, right: DecisionSignalItem): boolean {
  if (!left) return true;
  return getSignalTime(right) > getSignalTime(left);
}

/** 将字符串安全转换为决策信号市场标识 */
function toDecisionSignalMarket(value: string | null | undefined): DecisionSignalMarket | undefined {
  const normalized = String(value || '').toLowerCase();
  return DECISION_SIGNAL_MARKETS.has(normalized as DecisionSignalMarket)
    ? normalized as DecisionSignalMarket
    : undefined;
}

/** 生成持仓决策信号查询的唯一键，用于去重 */
function toPositionSignalLookupKey(stockCode: string, market?: DecisionSignalMarket): string {
  return `${market || ''}:${normalizeStockCode(stockCode).toUpperCase()}`;
}

/** 以指定并发数批量执行异步映射，保持结果顺序与输入一致 */
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

/** 加载单个持仓的决策信号查询结果 */
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

/** usePortfolioSignals 的参数 */
interface UsePortfolioSignalsParams {
  /** 当前视图的持仓快照（口径卡展示账户数 / 计价币种 / 成本法） */
  snapshot: PortfolioSnapshotResponse | null;
  /** 当前查询账户 ID，'all' 时为 undefined */
  queryAccountId?: number;
  /** 账户列表长度，用于判定快照是否覆盖全部账户 */
  accountsLength: number;
  /** 整页刷新自增键：变化时强制重新查询（即使快照数据未变） */
  signalsRefreshTick?: number;
  /** 统一错误回调，转发给主页面全局错误提示 */
  onError: (error: unknown) => void;
  /** 分析任务提交成功后的消息回调，用于主页面全局提示 */
  onAnalysisMessage: (message: string) => void;
}

/** usePortfolioSignals 的返回值 */
interface UsePortfolioSignalsResult {
  /** 扁平化持仓行，按市值降序 */
  positionRows: FlatPosition[];
  /** 持仓行键 → 该持仓的最新决策信号 */
  signalByPositionKey: Map<string, DecisionSignalItem>;
  /** 决策信号加载中 */
  signalsLoading: boolean;
  /** 决策信号部分失败警告，null 表示无 */
  signalsWarning: string | null;
  /** 正在提交分析任务的持仓行键，null 表示无 */
  positionUnderAnalysis: string | null;
  /** 提交单个持仓的分析任务 */
  handleAnalyzePosition: (row: FlatPosition) => void;
}

export const usePortfolioSignals = ({
  snapshot,
  queryAccountId,
  accountsLength,
  signalsRefreshTick = 0,
  onError,
  onAnalysisMessage,
}: UsePortfolioSignalsParams): UsePortfolioSignalsResult => {
  const { t } = useUiLanguage();

  const [positionSignals, setPositionSignals] = useState<DecisionSignalItem[]>([]);
  const [positionSignalsLoading, setPositionSignalsLoading] = useState(false);
  const [positionSignalsWarning, setPositionSignalsWarning] = useState<string | null>(null);
  const [positionUnderAnalysis, setPositionUnderAnalysis] = useState<string | null>(null);
  const positionSignalsRequestRef = useRef(0);

  /** 扁平化持仓行：将快照中按账户分组的持仓展平为一维数组，按市值降序 */
  const positionRows = useMemo<FlatPosition[]>(() => {
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
    return accountsLength === 0 || Number(snapshot.accountCount || 0) === accountsLength;
  }, [accountsLength, queryAccountId, snapshot]);

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

  // 加载持仓决策信号：持仓行变化时，以并发方式批量查询最新决策信号
  // 使用请求序列号防止竞态条件，快照不匹配范围时跳过加载
  useEffect(() => {
    if (positionSignalLookups.length === 0) {
      // 数据加载型副作用，按仓库约定关闭该规则
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPositionSignals([]);
      setPositionSignalsWarning(null);
      setPositionSignalsLoading(false);
      return;
    }

    const requestId = positionSignalsRequestRef.current;
    const isActiveRequest = () => positionSignalsRequestRef.current === requestId;

    const loadPositionSignals = async () => {
      setPositionSignalsLoading(true);
      setPositionSignalsWarning(null);
      const results = await mapWithConcurrency(
        positionSignalLookups,
        PORTFOLIO_SIGNAL_LOOKUP_CONCURRENCY,
        loadPortfolioSignalLookup,
      );
      if (!isActiveRequest()) return;
      const collected = results.flatMap((result) => result.items);
      const failures = results.flatMap((result) => (result.error ? [result.error] : []));
      setPositionSignals(collected);
      setPositionSignalsWarning(
        failures.length > 0
          ? (
            collected.length > 0
              ? formatUiText(t('decisionSignals.portfolioPartialWarning'), { message: failures[0] })
              : failures[0]
          )
          : null,
      );
      if (isActiveRequest()) {
        setPositionSignalsLoading(false);
      }
    };

    void loadPositionSignals();

    return () => {
      positionSignalsRequestRef.current += 1;
    };
  }, [positionSignalLookups, snapshotMatchesAccountScope, signalsRefreshTick, t]);

  /** 持仓行与决策信号的映射表：按市场+代码匹配，保留每个持仓对应的最新决策信号 */
  const signalByPositionKey = useMemo(() => {
    const mapped = new Map<string, DecisionSignalItem>();
    for (const row of positionRows) {
      const rowMarket = String(row.market || '').toLowerCase();
      for (const signal of positionSignals) {
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
  }, [positionSignals, positionRows]);

  /** 提交单个持仓的分析任务 */
  const handleAnalyzePosition = async (row: FlatPosition) => {
    const key = `${row.accountId}-${row.symbol}-${row.market}`;
    setPositionUnderAnalysis(key);
    onAnalysisMessage(''); // 先清空上一次分析提示
    onError(null); // 先清空上一次错误
    try {
      const task = await portfolioApi.analyzePosition(row.symbol, {
        accountId: row.accountId,
        analysisPhase: 'auto',
        force: false,
      });
      onAnalysisMessage(`已提交 ${row.symbol} 分析任务：${task.taskId}`);
    } catch (err) {
      onError(err);
    } finally {
      setPositionUnderAnalysis(null);
    }
  };

  return {
    positionRows,
    signalByPositionKey,
    signalsLoading: positionSignalsLoading,
    signalsWarning: positionSignalsWarning,
    positionUnderAnalysis,
    handleAnalyzePosition,
  };
};
