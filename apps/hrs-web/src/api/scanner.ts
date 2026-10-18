import apiClient from './index';
import { toCamelCase } from './utils';
import type { StockRef } from '../types/stock';

/**
 * 技术信号扫描器（Scanner）相关 API。
 * 后端为异步任务模式：POST 提交任务 -> 轮询 GET /tasks/{id} 获取进度与增量结果
 * -> POST /tasks/{id}/cancel 协作式取消。
 *
 * 字段约定：后端为 snake_case，统一经 toCamelCase 深度转换后对外暴露驼峰；
 * 提交时由 serializePayload 转回 snake_case。
 */

/** 股票池来源 */
export type ScannerPoolSource = 'watchlist' | 'ranking' | 'limit_up';

/** 榜单排序字段 */
export type ScannerRankingField = 'amount' | 'change_percent' | 'turnover_rate';

/** 技术信号键（与后端 SIGNAL_KEYS 一致） */
export type ScannerSignalKey =
  | 'ma_golden'
  | 'ma_death'
  | 'macd_golden'
  | 'macd_death'
  | 'rsi_oversold'
  | 'rsi_overbought'
  | 'boll_upper'
  | 'boll_lower';

/** 自选股池条目：纯 {code,name} 对，统一复用 types/stock.ts 的 StockRef（不再重复定义） */

/** 扫描请求（前端驼峰形态） */
export type ScannerStartPayload = {
  poolSource: ScannerPoolSource;
  rankingField: ScannerRankingField;
  topN: number;
  signals: ScannerSignalKey[];
  watchlist?: StockRef[];
};

/** GET /options 返回的选项契约 */
export type ScannerOptions = {
  poolSources: ScannerPoolSource[];
  rankingFields: ScannerRankingField[];
  topNOptions: number[];
  signals: ScannerSignalKey[];
  defaults: {
    poolSource: ScannerPoolSource;
    rankingField: ScannerRankingField;
    topN: number;
    signals: ScannerSignalKey[];
  };
  maxPoolSize: number;
};

/** 单条命中结果 */
export type ScannerResultRow = {
  code: string;
  name: string;
  signals: ScannerSignalKey[];
  scannedAt: string;
};

/** 扫描分步快照：后端全量下发、前端整体替换。
 *  - key：步骤标识（pool=解析股票池 / signal=技术信号扫描），前端据此映射本地化标题
 *  - status：running / done
 *  - total：该步真实股票数量（stocks 可能截断）
 *  - stocks：该步过滤出的股票列表 */
export type ScannerStep = {
  key: string;
  status: string;
  total: number;
  stocks: StockRef[];
};

/** POST /tasks 受理响应 */
export type ScannerAccepted = {
  taskId: string;
  status: string;
  message: string;
};

/** 任务状态（运行中即带增量结果） */
export type ScannerTaskStatus = {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  progress: number;
  message?: string | null;
  error?: string | null;
  poolCount: number;
  scanned: number;
  matchCount: number;
  results: ScannerResultRow[];
  steps?: ScannerStep[];
  cancelled: boolean;
  finished: boolean;
};

/** POST /tasks/{id}/cancel 响应 */
export type ScannerCancelResult = {
  taskId: string;
  cancelled: boolean;
  message: string;
};

/** 默认请求（与后端 DEFAULT_* 保持一致，options 未就绪时的兜底） */
export const DEFAULT_SCAN_PAYLOAD: ScannerStartPayload = {
  poolSource: 'watchlist',
  rankingField: 'amount',
  topN: 20,
  signals: ['ma_golden'],
  watchlist: [],
};

/** 驼峰请求 -> 后端 snake_case 字段 */
export function serializePayload(payload: ScannerStartPayload): Record<string, unknown> {
  return {
    pool_source: payload.poolSource,
    ranking_field: payload.rankingField,
    top_n: payload.topN,
    signals: payload.signals,
    watchlist: (payload.watchlist ?? []).map((item) => ({
      code: item.code,
      name: item.name,
    })),
  };
}

export const scannerApi = {
  /** 获取扫描选项契约（池来源 / 榜单字段 / TopN / 信号键） */
  async getOptions(): Promise<ScannerOptions> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/scanner/options');
    return toCamelCase<ScannerOptions>(response.data);
  },

  /** 提交一次扫描任务，立即返回 taskId */
  async start(payload: ScannerStartPayload): Promise<ScannerAccepted> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/scanner/tasks',
      serializePayload(payload),
    );
    return toCamelCase<ScannerAccepted>(response.data);
  },

  /**
   * 轮询任务进度与增量结果。
   * 带 _t 缓存破坏参数，绕过 apiClient 的 GET L1 缓存（避免轮询命中缓存读到旧状态）。
   */
  async getTask(taskId: string): Promise<ScannerTaskStatus> {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/scanner/tasks/${encodeURIComponent(taskId)}`,
      { params: { _t: Date.now() } },
    );
    return toCamelCase<ScannerTaskStatus>(response.data);
  },

  /** 请求取消扫描（协作式，已命中结果保留） */
  async cancel(taskId: string): Promise<ScannerCancelResult> {
    const response = await apiClient.post<Record<string, unknown>>(
      `/api/v1/scanner/tasks/${encodeURIComponent(taskId)}/cancel`,
    );
    return toCamelCase<ScannerCancelResult>(response.data);
  },
};
