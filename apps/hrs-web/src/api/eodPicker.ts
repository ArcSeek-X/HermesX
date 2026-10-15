import apiClient from './index';
import { toCamelCase } from './utils';
import type { KLinePoint } from './kline';

/**
 * 尾盘选股法（EOD Picker）相关 API。
 * 后端为异步任务模式：POST 提交任务 -> 轮询 GET /tasks/{id} 获取进度与结果。
 * 分时明细通过 GET /stocks/{code}/timeline 懒加载（避免一次返回几十只 × 240 点）。
 */

/** 筛选条件（驼峰，与后端 snake_case 字段在请求时由 serializeFilters 转换） */
export type EodPickerFilters = {
  circMvMin: number;
  circMvMax: number | null;
  volumeRatioMin: number;
  changePctMin: number;
  /** null = 不设上限 */
  changePctMax: number | null;
  turnoverRateMin: number;
  /** null = 不设上限 */
  turnoverRateMax: number | null;
  excludeSt: boolean;
  strengthMin: number;
  limit: number;
};

/** 单只命中股票的展示数据 */
export type EodPickerStock = {
  code: string;
  name: string;
  price: number | null;
  changePct: number | null;
  circMv: number | null;
  volumeRatio: number | null;
  turnoverRate: number | null;
  amount: number | null;
  strength: number;
  prevClose: number | null;
  /** 下采样分时点（KLinePoint 形态，供卡片分时图直接渲染） */
  timeline: KLinePoint[];
};

export type EodPickerResult = {
  filters: EodPickerFilters;
  totalScanned: number;
  candidateCount: number;
  matchCount: number;
  stocks: EodPickerStock[];
  /** 选股基准交易日（休市时为上一个已收盘交易日，YYYY-MM-DD） */
  tradeDate?: string | null;
  generatedAt: string;
};

export type EodPickerAccepted = {
  taskId: string;
  traceId?: string | null;
  status: string;
  message: string;
};

/** 进度步骤中的单只股票条目（名称 + 代码） */
export type EodPickerStepStock = {
  code: string;
  name: string;
};

/** 进度模态框中的筛选步骤快照（后端阶段性全量下发，前端整体替换） */
export type EodPickerStep = {
  /** 步骤标识：basic 基础条件过滤 / strength 分时强度过滤 */
  key: string;
  /** 步骤状态：running 进行中 / done 已完成 */
  status: 'running' | 'done';
  /** 该步骤真实股票数（可能大于 stocks.length，后者受后端上限截断） */
  total: number;
  stocks: EodPickerStepStock[];
};

export type EodPickerTaskStatus = {
  taskId: string;
  traceId?: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  progress?: number | null;
  message?: string | null;
  error?: string | null;
  result?: EodPickerResult | null;
  /** 各筛选步骤的股票快照（轮询期间逐阶段填充，完成后清空） */
  steps?: EodPickerStep[];
};

export type EodPickerTimeline = {
  code: string;
  name: string;
  prevClose: number | null;
  points: KLinePoint[];
};

/** 默认筛选条件（与后端 DEFAULT_FILTERS 保持一致） */
export const DEFAULT_FILTERS: EodPickerFilters = {
  circMvMin: 50,
  circMvMax: 200,
  volumeRatioMin: 1.2,
  changePctMin: 3,
  changePctMax: 5,
  turnoverRateMin: 5,
  turnoverRateMax: 10,
  excludeSt: true,
  strengthMin: 80,
  limit: 240,
};

/** 驼峰筛选条件 -> 后端 snake_case 字段 */
export function serializeFilters(f: EodPickerFilters): Record<string, unknown> {
  return {
    circ_mv_min: f.circMvMin,
    circ_mv_max: f.circMvMax,
    volume_ratio_min: f.volumeRatioMin,
    change_pct_min: f.changePctMin,
    change_pct_max: f.changePctMax,
    turnover_rate_min: f.turnoverRateMin,
    turnover_rate_max: f.turnoverRateMax,
    exclude_st: f.excludeSt,
    strength_min: f.strengthMin,
    limit: f.limit,
  };
}

export const eodPickerApi = {
  /** 获取后端默认筛选条件 */
  async getDefaults(): Promise<EodPickerFilters> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/eod-picker/defaults');
    return toCamelCase<EodPickerFilters>(response.data);
  },

  /** 提交一次选股任务，立即返回 taskId */
  async start(filters: EodPickerFilters): Promise<EodPickerAccepted> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/eod-picker/tasks', {
      filters: serializeFilters(filters),
    });
    return toCamelCase<EodPickerAccepted>(response.data);
  },

  /**
   * 轮询任务进度与结果。
   * 带 _t 缓存破坏参数，绕过 apiClient 的 GET L1 缓存（避免轮询命中缓存读到旧状态）。
   */
  async getTask(taskId: string): Promise<EodPickerTaskStatus> {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/eod-picker/tasks/${encodeURIComponent(taskId)}`,
      { params: { _t: Date.now() } },
    );
    return toCamelCase<EodPickerTaskStatus>(response.data);
  },

  /** 懒加载单只股票完整分时明细 */
  async getTimeline(code: string): Promise<EodPickerTimeline> {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/eod-picker/stocks/${encodeURIComponent(code)}/timeline`,
    );
    return toCamelCase<EodPickerTimeline>(response.data);
  },
};
