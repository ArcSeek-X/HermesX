/**
 * 价格预警（Alerts）相关 API。
 * 负责预警规则的增删改查、启停、测试，以及预警触发记录、通知记录的查询与清理。
 * 请求参数统一从 camelCase 转换为后端 snake_case，响应再转回 camelCase。
 */

import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  AlertDeleteResponse,
  AlertNotificationListQuery,
  AlertNotificationListResponse,
  AlertRuleCreateRequest,
  AlertRuleItem,
  AlertRuleListQuery,
  AlertRuleListResponse,
  AlertRuleTestResponse,
  AlertTriggerListQuery,
  AlertTriggerListResponse,
} from '../types/alerts';

/**
 * 预警（Alerts）相关 API。
 * 负责预警规则的增删改查/启停/测试，以及触发明细、通知记录的查询。
 * 所有请求体统一从前端 camelCase 转为后端 snake_case，响应再转回 camelCase。
 */

/** 剔除对象中值为 undefined 的字段，避免把“未设置”误传给后端 */
function omitUndefined(input: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(input).filter(([, value]) => value !== undefined),
  );
}

/** 将创建预警规则的请求体（camelCase）转换为后端需要的 snake_case 结构 */
function toSnakeRulePayload(payload: AlertRuleCreateRequest): Record<string, unknown> {
  const request: Record<string, unknown> = {};
  if (payload.name !== undefined) request.name = payload.name;
  if (payload.targetScope !== undefined) request.target_scope = payload.targetScope;
  if (payload.target !== undefined) request.target = payload.target;
  if (payload.alertType !== undefined) request.alert_type = payload.alertType;
  if (payload.severity !== undefined) request.severity = payload.severity;
  if (payload.enabled !== undefined) request.enabled = payload.enabled;
  if (payload.parameters !== undefined) {
    request.parameters = omitUndefined({
      direction: payload.parameters.direction,
      price: payload.parameters.price,
      change_pct: payload.parameters.changePct,
      multiplier: payload.parameters.multiplier,
      window: payload.parameters.window,
      period: payload.parameters.period,
      threshold: payload.parameters.threshold,
      fast_period: payload.parameters.fastPeriod,
      slow_period: payload.parameters.slowPeriod,
      signal_period: payload.parameters.signalPeriod,
      k_period: payload.parameters.kPeriod,
      d_period: payload.parameters.dPeriod,
      mode: payload.parameters.mode,
      statuses: payload.parameters.statuses,
      min_drop: payload.parameters.minDrop,
    });
  }
  return request;
}

/** 构造预警规则列表查询参数（camelCase -> snake_case） */
function toRuleListParams(query: AlertRuleListQuery = {}): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {};
  if (query.enabled !== undefined) params.enabled = query.enabled;
  if (query.alertType) params.alert_type = query.alertType;
  if (query.targetScope) params.target_scope = query.targetScope;
  if (query.target) params.target = query.target;
  if (query.source) params.source = query.source;
  if (query.page !== undefined) params.page = query.page;
  if (query.pageSize !== undefined) params.page_size = query.pageSize;
  return params;
}

/** 构造触发记录列表查询参数 */
function toTriggerListParams(query: AlertTriggerListQuery = {}): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (query.ruleId !== undefined) params.rule_id = query.ruleId;
  if (query.target) params.target = query.target;
  if (query.status) params.status = query.status;
  if (query.page !== undefined) params.page = query.page;
  if (query.pageSize !== undefined) params.page_size = query.pageSize;
  return params;
}

/** 构造通知记录列表查询参数 */
function toNotificationListParams(query: AlertNotificationListQuery = {}): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {};
  if (query.triggerId !== undefined) params.trigger_id = query.triggerId;
  if (query.channel) params.channel = query.channel;
  if (query.success !== undefined) params.success = query.success;
  if (query.page !== undefined) params.page = query.page;
  if (query.pageSize !== undefined) params.page_size = query.pageSize;
  return params;
}

export const alertsApi = {
  /** 查询预警规则列表（支持按启用状态/类型/标的/来源/分页过滤） */
  async listRules(query: AlertRuleListQuery = {}): Promise<AlertRuleListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/alerts/rules', {
      params: toRuleListParams(query),
    });
    return toCamelCase<AlertRuleListResponse>(response.data);
  },

  /** 创建一条预警规则 */
  async createRule(payload: AlertRuleCreateRequest): Promise<AlertRuleItem> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/alerts/rules',
      toSnakeRulePayload(payload),
    );
    return toCamelCase<AlertRuleItem>(response.data);
  },

  /** 删除指定预警规则 */
  async deleteRule(ruleId: number): Promise<AlertDeleteResponse> {
    const response = await apiClient.delete<Record<string, unknown>>(`/api/v1/alerts/rules/${ruleId}`);
    return toCamelCase<AlertDeleteResponse>(response.data);
  },

  /** 启用指定预警规则 */
  async enableRule(ruleId: number): Promise<AlertRuleItem> {
    const response = await apiClient.post<Record<string, unknown>>(`/api/v1/alerts/rules/${ruleId}/enable`);
    return toCamelCase<AlertRuleItem>(response.data);
  },

  /** 停用指定预警规则 */
  async disableRule(ruleId: number): Promise<AlertRuleItem> {
    const response = await apiClient.post<Record<string, unknown>>(`/api/v1/alerts/rules/${ruleId}/disable`);
    return toCamelCase<AlertRuleItem>(response.data);
  },

  /** 对指定规则做一次测试触发，返回命中的样本数据 */
  async testRule(ruleId: number): Promise<AlertRuleTestResponse> {
    const response = await apiClient.post<Record<string, unknown>>(`/api/v1/alerts/rules/${ruleId}/test`);
    return toCamelCase<AlertRuleTestResponse>(response.data);
  },

  /** 查询预警触发（命中）记录列表 */
  async listTriggers(query: AlertTriggerListQuery = {}): Promise<AlertTriggerListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/alerts/triggers', {
      params: toTriggerListParams(query),
    });
    return toCamelCase<AlertTriggerListResponse>(response.data);
  },

  /** 查询预警通知发送记录列表（可按触发 id/渠道/成功与否过滤） */
  async listNotifications(query: AlertNotificationListQuery = {}): Promise<AlertNotificationListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/alerts/notifications', {
      params: toNotificationListParams(query),
    });
    return toCamelCase<AlertNotificationListResponse>(response.data);
  },
};
