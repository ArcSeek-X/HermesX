/**
 * 决策信号（Decision Signals）相关 API。
 * 负责决策信号的创建/查询/反馈、结果（outcome）的运行与查询、重新评估（reassess）
 * 以及能力开关。所有请求参数统一转 snake_case，响应转 camelCase。
 */

import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  DecisionSignalCreateRequest,
  DecisionSignalFeedbackItem,
  DecisionSignalFeedbackRequest,
  DecisionSignalItem,
  DecisionSignalLatestParams,
  DecisionSignalListParams,
  DecisionSignalListResponse,
  DecisionSignalMutationResponse,
  DecisionSignalOutcomeItem,
  DecisionSignalOutcomeListParams,
  DecisionSignalOutcomeListResponse,
  DecisionSignalOutcomeRunRequest,
  DecisionSignalOutcomeRunResponse,
  DecisionSignalOutcomeStatsBucket,
  DecisionSignalOutcomeStatsParams,
  DecisionSignalOutcomeStatsResponse,
  DecisionSignalProfileCalibrationBucket,
  DecisionSignalReassessRequest,
  DecisionSignalReassessBlockedError,
  DecisionSignalReassessResponse,
  DecisionSignalStatusUpdateRequest,
} from '../types/decisionSignals';

/**
 * 决策信号（Decision Signals）相关 API。
 * 覆盖信号的创建/列表/详情/最新查询/重新评估（reassess）、状态更新，
 * 以及信号结果（outcome）的运行、列表、统计与反馈。
 * 所有请求体统一从 camelCase 转 snake_case；响应中的数组项、嵌套 evidence/metadata 等
 * 特殊处理字段也在此处做归一化，保证前端拿到的都是 camelCase。
 */

/** 剔除值为 undefined 的字段，避免把“未设置”误传后端 */
function omitUndefined(input: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(input).filter(([, value]) => value !== undefined),
  );
}

/** 把数组型查询参数序列为重复 key（如 horizons=a&horizons=b），供 axios paramsSerializer 使用 */
function serializeRepeatedQueryParams(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item === undefined || item === null || item === '') continue;
      searchParams.append(key, String(item));
    }
  }
  return searchParams.toString();
}

/** 把单个信号项归一化为 camelCase，并补回 toCamelCase 不会处理的 evidence/dataQualitySummary/metadata 字段 */
function toDecisionSignalItem(data: Record<string, unknown>): DecisionSignalItem {
  const item = toCamelCase<DecisionSignalItem>(data);
  if ('evidence' in data) item.evidence = data.evidence;
  if ('data_quality_summary' in data) item.dataQualitySummary = data.data_quality_summary;
  if ('metadata' in data) item.metadata = data.metadata;
  return item;
}

/** 把创建/更新响应归一化（含嵌套 item） */
function toDecisionSignalMutationResponse(data: Record<string, unknown>): DecisionSignalMutationResponse {
  const response = toCamelCase<DecisionSignalMutationResponse>(data);
  response.item = toDecisionSignalItem(data.item as Record<string, unknown>);
  return response;
}

/** 把重新评估响应归一化，并校验 preview 必须为对象；回填嵌套 item */
function toDecisionSignalReassessResponse(data: Record<string, unknown>): DecisionSignalReassessResponse {
  const response = toCamelCase<DecisionSignalReassessResponse>(data);
  const rawPreview = data.preview;
  if (rawPreview !== null && (typeof rawPreview !== 'object' || Array.isArray(rawPreview))) {
    throw new Error('DecisionSignal reassess response preview must be an object');
  }
  if (rawPreview) {
    response.preview = toCamelCase<DecisionSignalReassessResponse['preview']>(rawPreview);
    if (response.preview) {
      response.preview.metadata = (rawPreview as Record<string, unknown>).metadata as Record<string, unknown> ?? {};
    }
  } else {
    response.preview = null;
  }
  if (data.item) {
    response.item = toDecisionSignalItem(data.item as Record<string, unknown>);
  }
  return response;
}

/**
 * 从 axios 错误中解析“护栏拦截（guardrail_blocked）”信息。
 * 成功返回 { blockedReason, warnings }，否则返回 null，便于 UI 区分“被护栏拦截”与“普通失败”。
 */
export function getDecisionSignalReassessBlockedError(
  error: unknown,
): DecisionSignalReassessBlockedError | null {
  if (!error || typeof error !== 'object') return null;
  const response = (error as { response?: { data?: unknown } }).response;
  const data = response?.data;
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  const payload = data as Record<string, unknown>;
  if (payload.error !== 'guardrail_blocked' || typeof payload.blocked_reason !== 'string') return null;
  const warnings = Array.isArray(payload.warnings)
    ? payload.warnings.filter((warning): warning is Record<string, unknown> => (
      Boolean(warning) && typeof warning === 'object' && !Array.isArray(warning)
    )).filter((warning) => typeof warning.code === 'string').map((warning) => ({
      code: warning.code as string,
      message: typeof warning.message === 'string' ? warning.message : undefined,
      params: warning.params && typeof warning.params === 'object' && !Array.isArray(warning.params)
        ? warning.params as Record<string, unknown>
        : undefined,
    }))
    : [];
  return { blockedReason: payload.blocked_reason, warnings };
}

/** 把列表响应归一化（校验 items 为数组并逐项转换） */
function toDecisionSignalListResponse(data: Record<string, unknown>): DecisionSignalListResponse {
  const response = toCamelCase<DecisionSignalListResponse>(data);
  if (!Array.isArray(data.items)) {
    throw new Error('DecisionSignal list response items must be an array');
  }
  response.items = data.items.map((item) => toDecisionSignalItem(item as Record<string, unknown>));
  return response;
}

/** 把单个结果项归一化为 camelCase */
function toDecisionSignalOutcomeItem(data: Record<string, unknown>): DecisionSignalOutcomeItem {
  return toCamelCase<DecisionSignalOutcomeItem>(data);
}

/** 把结果列表响应归一化 */
function toDecisionSignalOutcomeListResponse(data: Record<string, unknown>): DecisionSignalOutcomeListResponse {
  const response = toCamelCase<DecisionSignalOutcomeListResponse>(data);
  if (!Array.isArray(data.items)) {
    throw new Error('DecisionSignal outcome list response items must be an array');
  }
  response.items = data.items.map((item) => toDecisionSignalOutcomeItem(item as Record<string, unknown>));
  return response;
}

/** 把运行结果响应归一化 */
function toDecisionSignalOutcomeRunResponse(data: Record<string, unknown>): DecisionSignalOutcomeRunResponse {
  const response = toCamelCase<DecisionSignalOutcomeRunResponse>(data);
  if (!Array.isArray(data.items)) {
    throw new Error('DecisionSignal outcome run response items must be an array');
  }
  response.items = data.items.map((item) => toDecisionSignalOutcomeItem(item as Record<string, unknown>));
  return response;
}

/** 把统计桶（含 unable_reasons）归一化 */
function toDecisionSignalStatsBucket(data: Record<string, unknown>): DecisionSignalOutcomeStatsBucket {
  const bucket = toCamelCase<DecisionSignalOutcomeStatsBucket>(data);
  bucket.unableReasons = (data.unable_reasons as Record<string, number> | undefined) ?? {};
  return bucket;
}

/** 把校准分桶数组兜底为空数组 */
function toProfileCalibrationBuckets(value: unknown): DecisionSignalProfileCalibrationBucket[] {
  return Array.isArray(value) ? value as DecisionSignalProfileCalibrationBucket[] : [];
}

/** 把结果统计响应归一化（含按维度拆解与决策画像校准分桶） */
function toDecisionSignalOutcomeStatsResponse(data: Record<string, unknown>): DecisionSignalOutcomeStatsResponse {
  const response = toCamelCase<DecisionSignalOutcomeStatsResponse>(data);
  response.unableReasons = (data.unable_reasons as Record<string, number> | undefined) ?? {};
  const rawBreakdowns = data.breakdowns as Record<string, unknown[]> | undefined;
  response.breakdowns = {};
  if (rawBreakdowns && typeof rawBreakdowns === 'object') {
    for (const [dimension, buckets] of Object.entries(rawBreakdowns)) {
      response.breakdowns[dimension] = Array.isArray(buckets)
        ? buckets.map((bucket) => toDecisionSignalStatsBucket(bucket as Record<string, unknown>))
        : [];
    }
  }
  const calibration = response.profileCalibration;
  const calibrationBreakdowns = calibration?.breakdowns;
  if (
    calibration
    && calibrationBreakdowns
    && typeof calibrationBreakdowns === 'object'
    && !Array.isArray(calibrationBreakdowns)
  ) {
    calibration.breakdowns = {
      decisionProfile: toProfileCalibrationBuckets(calibrationBreakdowns.decisionProfile),
      decisionProfileAction: toProfileCalibrationBuckets(calibrationBreakdowns.decisionProfileAction),
      decisionProfileHorizon: toProfileCalibrationBuckets(calibrationBreakdowns.decisionProfileHorizon),
      decisionProfileMarketPhase: toProfileCalibrationBuckets(calibrationBreakdowns.decisionProfileMarketPhase),
      decisionProfileDataQualityLevel: toProfileCalibrationBuckets(
        calibrationBreakdowns.decisionProfileDataQualityLevel,
      ),
      profileSource: toProfileCalibrationBuckets(calibrationBreakdowns.profileSource),
    };
  } else {
    response.profileCalibration = undefined;
  }
  return response;
}

/** 把反馈项归一化为 camelCase */
function toDecisionSignalFeedbackItem(data: Record<string, unknown>): DecisionSignalFeedbackItem {
  return toCamelCase<DecisionSignalFeedbackItem>(data);
}

/** 把创建信号请求体（camelCase）转为后端 snake_case 结构 */
function toSnakeCreatePayload(payload: DecisionSignalCreateRequest): Record<string, unknown> {
  return omitUndefined({
    stock_code: payload.stockCode,
    stock_name: payload.stockName,
    market: payload.market,
    source_type: payload.sourceType,
    source_agent: payload.sourceAgent,
    source_report_id: payload.sourceReportId,
    trace_id: payload.traceId,
    decision_profile: payload.decisionProfile,
    market_phase: payload.marketPhase,
    trigger_source: payload.triggerSource,
    action: payload.action,
    action_label: payload.actionLabel,
    confidence: payload.confidence,
    score: payload.score,
    horizon: payload.horizon,
    entry_low: payload.entryLow,
    entry_high: payload.entryHigh,
    stop_loss: payload.stopLoss,
    target_price: payload.targetPrice,
    invalidation: payload.invalidation,
    watch_conditions: payload.watchConditions,
    reason: payload.reason,
    risk_summary: payload.riskSummary,
    catalyst_summary: payload.catalystSummary,
    evidence: payload.evidence,
    data_quality_summary: payload.dataQualitySummary,
    plan_quality: payload.planQuality,
    status: payload.status,
    expires_at: payload.expiresAt,
    metadata: payload.metadata,
    report_language: payload.reportLanguage,
  });
}

/** 把运行结果请求体转为 snake_case */
function toSnakeOutcomeRunPayload(payload: DecisionSignalOutcomeRunRequest): Record<string, unknown> {
  return omitUndefined({
    signal_id: payload.signalId,
    horizons: payload.horizons,
    force: payload.force,
    market: payload.market,
    stock_code: payload.stockCode,
    action: payload.action,
    source_type: payload.sourceType,
    status: payload.status,
    limit: payload.limit,
  });
}

/** 把重新评估请求体转为 snake_case */
function toSnakeReassessPayload(payload: DecisionSignalReassessRequest): Record<string, unknown> {
  return {
    source_report_id: payload.sourceReportId,
    decision_profile: payload.decisionProfile,
    persist: payload.persist ?? false,
  };
}

/** 构造信号列表查询参数（camelCase -> snake_case） */
function toListParams(params: DecisionSignalListParams = {}): Record<string, string | number | boolean> {
  return omitUndefined({
    market: params.market,
    stock_code: params.stockCode,
    action: params.action,
    market_phase: params.marketPhase,
    decision_profile: params.decisionProfile,
    source_type: params.sourceType,
    source_report_id: params.sourceReportId,
    trace_id: params.traceId,
    trigger_source: params.triggerSource,
    status: params.status,
    created_from: params.createdFrom,
    created_to: params.createdTo,
    expires_from: params.expiresFrom,
    expires_to: params.expiresTo,
    holding_only: params.holdingOnly,
    account_id: params.accountId,
    page: params.page,
    page_size: params.pageSize,
  }) as Record<string, string | number | boolean>;
}

/** 构造结果列表查询参数 */
function toOutcomeListParams(params: DecisionSignalOutcomeListParams = {}): Record<string, string | number> {
  return omitUndefined({
    signal_id: params.signalId,
    horizon: params.horizon,
    engine_version: params.engineVersion,
    eval_status: params.evalStatus,
    outcome: params.outcome,
    page: params.page,
    page_size: params.pageSize,
  }) as Record<string, string | number>;
}

/** 构造结果统计查询参数（数组用字符串/字符串数组） */
function toOutcomeStatsParams(params: DecisionSignalOutcomeStatsParams = {}): Record<string, string | string[]> {
  return omitUndefined({
    horizons: params.horizons,
    engine_version: params.engineVersion,
    statuses: params.statuses,
  }) as Record<string, string | string[]>;
}

/** 构造最新信号查询参数 */
function toLatestParams(params: DecisionSignalLatestParams = {}): Record<string, string | number> {
  return omitUndefined({
    market: params.market,
    limit: params.limit,
  }) as Record<string, string | number>;
}

/** 把状态更新请求体转为 snake_case */
function toSnakeStatusPayload(payload: DecisionSignalStatusUpdateRequest): Record<string, unknown> {
  return omitUndefined({
    status: payload.status,
    metadata: payload.metadata,
  });
}

/** 把反馈请求体转为 snake_case */
function toSnakeFeedbackPayload(payload: DecisionSignalFeedbackRequest): Record<string, unknown> {
  return omitUndefined({
    feedback_value: payload.feedbackValue,
    reason_code: payload.reasonCode,
    note: payload.note,
    source: payload.source,
  });
}

/**
 * 构造“最新信号”路径中的股票代码段。
 * 后端路由只接受单段路径，故禁止含 “/” 的代码（如 00700.HK），需改用 00700/HK00700 等形态。
 */
function toLatestStockCodePath(stockCode: string): string {
  if (stockCode.includes('/')) {
    throw new Error(
      'DecisionSignal latest stockCode cannot contain "/" because the backend route accepts a single path segment; use 00700, HK00700, or 00700.HK.',
    );
  }
  return encodeURIComponent(stockCode);
}

export const decisionSignalsApi = {
  /** 创建一条决策信号 */
  async create(payload: DecisionSignalCreateRequest): Promise<DecisionSignalMutationResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/decision-signals',
      toSnakeCreatePayload(payload),
    );
    return toDecisionSignalMutationResponse(response.data);
  },

  /** 分页/条件查询决策信号列表 */
  async list(params: DecisionSignalListParams = {}): Promise<DecisionSignalListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/decision-signals', {
      params: toListParams(params),
    });
    return toDecisionSignalListResponse(response.data);
  },

  /** 按 id 获取单条信号详情 */
  async get(signalId: number): Promise<DecisionSignalItem> {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/decision-signals/${signalId}`);
    return toDecisionSignalItem(response.data);
  },

  /** 获取某股票的最新信号（路径含股票代码，自动校验格式） */
  async getLatest(
    stockCode: string,
    params: DecisionSignalLatestParams = {},
  ): Promise<DecisionSignalListResponse> {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/decision-signals/latest/${toLatestStockCodePath(stockCode)}`,
      { params: toLatestParams(params) },
    );
    return toDecisionSignalListResponse(response.data);
  },

  /** 基于某报告重新评估决策信号（可预览或持久化） */
  async reassess(payload: DecisionSignalReassessRequest): Promise<DecisionSignalReassessResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/decision-signals/reassess',
      toSnakeReassessPayload(payload),
    );
    return toDecisionSignalReassessResponse(response.data);
  },

  /** 更新信号状态（如持有/关闭），并可附带 metadata */
  async updateStatus(
    signalId: number,
    payload: DecisionSignalStatusUpdateRequest,
  ): Promise<DecisionSignalItem> {
    const response = await apiClient.patch<Record<string, unknown>>(
      `/api/v1/decision-signals/${signalId}/status`,
      toSnakeStatusPayload(payload),
    );
    return toDecisionSignalItem(response.data);
  },

  /** 触发信号结果（outcome）计算 */
  async runOutcomes(payload: DecisionSignalOutcomeRunRequest): Promise<DecisionSignalOutcomeRunResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/decision-signals/outcomes/run',
      toSnakeOutcomeRunPayload(payload),
    );
    return toDecisionSignalOutcomeRunResponse(response.data);
  },

  /** 分页查询信号结果列表 */
  async listOutcomes(params: DecisionSignalOutcomeListParams = {}): Promise<DecisionSignalOutcomeListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/decision-signals/outcomes', {
      params: toOutcomeListParams(params),
    });
    return toDecisionSignalOutcomeListResponse(response.data);
  },

  /** 获取信号结果统计（支持多维度拆解，数组参数用重复 key 序列化） */
  async getOutcomeStats(
    params: DecisionSignalOutcomeStatsParams = {},
  ): Promise<DecisionSignalOutcomeStatsResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/decision-signals/outcomes/stats', {
      params: toOutcomeStatsParams(params),
      paramsSerializer: {
        serialize: serializeRepeatedQueryParams,
      },
    });
    return toDecisionSignalOutcomeStatsResponse(response.data);
  },

  /** 获取指定信号的所有结果 */
  async getSignalOutcomes(signalId: number): Promise<DecisionSignalOutcomeListResponse> {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/decision-signals/${signalId}/outcomes`,
    );
    return toDecisionSignalOutcomeListResponse(response.data);
  },

  /** 获取某信号的用户反馈 */
  async getFeedback(signalId: number): Promise<DecisionSignalFeedbackItem> {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/decision-signals/${signalId}/feedback`,
    );
    return toDecisionSignalFeedbackItem(response.data);
  },

  /** 写入（PUT）某信号的用户反馈 */
  async putFeedback(
    signalId: number,
    payload: DecisionSignalFeedbackRequest,
  ): Promise<DecisionSignalFeedbackItem> {
    const response = await apiClient.put<Record<string, unknown>>(
      `/api/v1/decision-signals/${signalId}/feedback`,
      toSnakeFeedbackPayload(payload),
    );
    return toDecisionSignalFeedbackItem(response.data);
  },
};
