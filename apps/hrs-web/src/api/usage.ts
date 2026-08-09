import apiClient from './index';
import { toCamelCase } from './utils';

/**
 * LLM 用量统计（Usage）相关 API。
 * 拉取指定时间范围内的 token 消耗、调用次数，以及按调用类型/模型维度的拆解。
 */

/** 统计周期：今日 / 本月 / 全部 */
export type UsagePeriod = 'today' | 'month' | 'all';

/** 按调用类型的用量拆解 */
export type UsageCallTypeBreakdown = {
  callType: string;
  calls: number;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
};

/** 按模型的用量拆解（含单次最大 token 数） */
export type UsageModelBreakdown = {
  model: string;
  calls: number;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  maxTotalTokens: number;
};

/** 单条调用明细记录 */
export type UsageCallRecord = {
  id: number;
  calledAt: string;
  callType: string;
  model: string;
  stockCode?: string | null;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
};

/** 用量仪表盘聚合数据 */
export type UsageDashboard = {
  period: UsagePeriod;
  fromDate: string;
  toDate: string;
  totalCalls: number;
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalTokens: number;
  byCallType: UsageCallTypeBreakdown[];
  byModel: UsageModelBreakdown[];
  recentCalls: UsageCallRecord[];
};

export const usageApi = {
  /** 获取用量仪表盘（默认周期=本月，最近记录=50 条） */
  getDashboard: async (params: { period?: UsagePeriod; limit?: number } = {}): Promise<UsageDashboard> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/usage/dashboard', {
      params: {
        period: params.period ?? 'month',
        limit: params.limit ?? 50,
      },
    });

    return toCamelCase<UsageDashboard>(response.data);
  },
};
