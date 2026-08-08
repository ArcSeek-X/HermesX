/**
 * 页面状态缓存 Store（L2 - 内存缓存）
 *
 * 提供全局页面状态管理，切换路由时状态保留
 * 支持 sessionStorage 持久化（L3），刷新页面后恢复
 *
 * 架构说明：
 * - L2: PageStateStore 提供内存级缓存，组件卸载时状态不丢失
 * - L3: 自动同步到 sessionStorage，刷新页面后从 sessionStorage 恢复
 * - 与 useCachedState 配合使用，支持嵌套键名访问
 *
 * 使用场景：
 * - K 线页面：保存股票代码、周期、K 线数据
 * - 板块分析：保存当前 Tab、筛选条件
 * - 其他页面：保存临时状态，避免路由切换后丢失
 */

import type React from 'react';
import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { getStorageItem, setStorageItem } from '../utils/storage';
import type { KLinePeriod, StockInfo, KLinePoint } from '../api/kline';

// ============ 类型定义 ============

/** K 线页面状态 */
export interface KLinePageState {
  stockCode: string | null;
  stockName: string | null;
  period: KLinePeriod;
  stockInfo: StockInfo | null;
  klineData: KLinePoint[];
  prevClose: number | null;
}

/** 板块分析页面状态 */
export interface SectorPageState {
  activeTab: 'concept' | 'etf';
  conceptLimit: number;
  etfLimit: number;
}

/** 股票筛选页面状态 */
export interface ScreeningPageState {
  filters: Record<string, unknown>;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

/** 投资组合页面状态 */
export interface PortfolioPageState {
  viewMode: 'list' | 'chart';
  selectedStock: string | null;
}

/** 决策信号页面状态 */
export interface DecisionSignalsPageState {
  selectedSignal: string | null;
  dateRange: [string, string];
}

/** 回测页面状态 */
export interface BacktestPageState {
  strategyConfig: Record<string, unknown>;
  lastResult: unknown;
}

/** 警报页面状态 */
export interface AlertsPageState {
  editingRule: unknown;
  filterStatus: 'all' | 'active' | 'inactive';
}

/** 全局页面状态（所有页面的状态集合） */
export interface PageStateStore {
  kline: KLinePageState;
  sector: SectorPageState;
  screening: ScreeningPageState;
  portfolio: PortfolioPageState;
  decisionSignals: DecisionSignalsPageState;
  backtest: BacktestPageState;
  alerts: AlertsPageState;
}

/** Store 上下文类型 */
interface PageStateContextType {
  /** 当前状态 */
  state: PageStateStore;
  /** 更新指定模块的状态 */
  setState: <K extends keyof PageStateStore>(
    key: K,
    value: PageStateStore[K] | ((prev: PageStateStore[K]) => PageStateStore[K])
  ) => void;
  /** 重置指定模块的状态 */
  resetState: (key: keyof PageStateStore) => void;
  /** 重置所有状态 */
  resetAll: () => void;
}

// ============ 默认状态 ============

/** 各页面的默认状态 */
const DEFAULT_STATE: PageStateStore = {
  kline: {
    stockCode: null,
    stockName: null,
    period: 'daily',
    stockInfo: null,
    klineData: [],
    prevClose: null,
  },
  sector: {
    activeTab: 'concept',
    conceptLimit: 100,
    etfLimit: 50,
  },
  screening: {
    filters: {},
    sortBy: 'market_cap',
    sortOrder: 'desc',
  },
  portfolio: {
    viewMode: 'list',
    selectedStock: null,
  },
  decisionSignals: {
    selectedSignal: null,
    dateRange: ['', ''],
  },
  backtest: {
    strategyConfig: {},
    lastResult: null,
  },
  alerts: {
    editingRule: null,
    filterStatus: 'all',
  },
};

// ============ Context ============

const PageStateContext = createContext<PageStateContextType | null>(null);

// ============ Provider 组件 ============

/**
 * 页面状态 Provider
 *
 * 提供全局页面状态管理，自动同步到 sessionStorage
 * 应用启动时从 sessionStorage 恢复状态
 */
export const PageStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 从 sessionStorage 恢复状态，如果没有则使用默认状态
  const [state, setState] = useState<PageStateStore>(() => {
    try {
      const saved = getStorageItem<Partial<PageStateStore>>('pageState', 'session');
      if (saved) {
        // 合并保存的状态和默认状态（确保新增字段有默认值）
        return {
          ...DEFAULT_STATE,
          ...saved,
          kline: { ...DEFAULT_STATE.kline, ...saved.kline },
          sector: { ...DEFAULT_STATE.sector, ...saved.sector },
          screening: { ...DEFAULT_STATE.screening, ...saved.screening },
          portfolio: { ...DEFAULT_STATE.portfolio, ...saved.portfolio },
          decisionSignals: { ...DEFAULT_STATE.decisionSignals, ...saved.decisionSignals },
          backtest: { ...DEFAULT_STATE.backtest, ...saved.backtest },
          alerts: { ...DEFAULT_STATE.alerts, ...saved.alerts },
        };
      }
    } catch {
      // 恢复失败时使用默认状态
    }
    return DEFAULT_STATE;
  });

  // 状态变化时同步到 sessionStorage（L3 持久化）
  useEffect(() => {
    try {
      setStorageItem('pageState', state, 'session');
    } catch {
      // 存储失败时静默处理
    }
  }, [state]);

  // 更新指定模块的状态
  const handleSetState = useCallback(
    <K extends keyof PageStateStore>(
      key: K,
      value: PageStateStore[K] | ((prev: PageStateStore[K]) => PageStateStore[K])
    ) => {
      setState((prev) => {
        const newValue = typeof value === 'function' ? value(prev[key]) : value;
        return { ...prev, [key]: newValue };
      });
    },
    []
  );

  // 重置指定模块的状态
  const handleResetState = useCallback(<K extends keyof PageStateStore>(key: K) => {
    setState((prev) => ({ ...prev, [key]: DEFAULT_STATE[key] as PageStateStore[K] }));
  }, []);

  // 重置所有状态
  const handleResetAll = useCallback(() => {
    setState(DEFAULT_STATE);
  }, []);

  return (
    <PageStateContext.Provider
      value={{
        state,
        setState: handleSetState,
        resetState: handleResetState,
        resetAll: handleResetAll,
      }}
    >
      {children}
    </PageStateContext.Provider>
  );
};

// ============ Hook ============

/**
 * 使用页面状态（完整 Store）
 *
 * @returns 状态对象和更新方法
 * @throws 如果在 PageStateProvider 外部使用会抛出错误
 *
 * @example
 * ```typescript
 * const { state, setState, resetState } = usePageState();
 * setState('kline', { ...state.kline, stockCode: '603019' });
 * ```
 */
export function usePageState(): PageStateContextType {
  const context = useContext(PageStateContext);
  if (!context) {
    throw new Error('usePageState must be used within PageStateProvider');
  }
  return context;
}

/**
 * 使用指定模块的页面状态
 *
 * @param key - 模块键名（如 'kline', 'sector'）
 * @returns [该模块的状态, 更新函数]
 *
 * @example
 * ```typescript
 * const [klineState, setKlineState] = useModuleState('kline');
 * setKlineState({ ...klineState, stockCode: '603019' });
 * ```
 */
export function useModuleState<K extends keyof PageStateStore>(
  key: K
): [PageStateStore[K], (value: PageStateStore[K] | ((prev: PageStateStore[K]) => PageStateStore[K])) => void] {
  const { state, setState } = usePageState();
  const moduleState = state[key];

  const setModuleState = useCallback(
    (value: PageStateStore[K] | ((prev: PageStateStore[K]) => PageStateStore[K])) => {
      setState(key, value);
    },
    [key, setState]
  );

  return [moduleState, setModuleState];
}
