/**
 * 系统配置（System Config）相关 API。
 * 负责系统设置/调度/LLM 渠道/代理/后端状态等的查询与更新，以及配置导入导出、
 * 自选股（watchlist）管理。更新接口会区分 400（校验错误）与 409（冲突）并抛出
 * 对应的 typed error，供页面差异化提示。
 */

import apiClient from './index';
import { createParsedApiError, getParsedApiError, type ParsedApiError } from './error';
import { toCamelCase } from './utils';
import type {
  AgentBackendStatusPreviewRequest,
  AgentBackendStatusResponse,
  DiscoverLLMChannelModelsRequest,
  DiscoverLLMChannelModelsResponse,
  ExportSystemConfigResponse,
  GenerationBackendStatusPreviewRequest,
  GenerationBackendStatusResponse,
  ImportSystemConfigRequest,
  SchedulerRunNowResponse,
  SchedulerStatusResponse,
  SetupStatusResponse,
  SystemConfigConflictResponse,
  SystemConfigResponse,
  SystemConfigSchemaResponse,
  SystemConfigValidationErrorResponse,
  TestLLMChannelRequest,
  TestLLMChannelResponse,
  TestGenerationBackendRequest,
  TestGenerationBackendResponse,
  TestNotificationChannelRequest,
  TestNotificationChannelResponse,
  UpdateSystemConfigRequest,
  UpdateSystemConfigResponse,
  ValidateSystemConfigRequest,
  ValidateSystemConfigResponse,
} from '../types/systemConfig';

/**
 * 系统配置（SystemConfig）相关 API。
 * 覆盖配置的读取/校验/更新/导入导出、Schema 与初始化状态、
 * 生成后端/智能体后端的状态与连通性测试、调度器状态与手动触发、
 * 以及 LLM/通知渠道测试与模型发现。同时提供自选队列（watchlist）的增删查。
 * 额外定义了两种可抛给 UI 的 typed error：校验失败（400）与版本冲突（409）。
 */

/** 配置校验失败错误：携带逐条 issue 与规范化错误，供设置页高亮定位 */
export class SystemConfigValidationError extends Error {
  issues: SystemConfigValidationErrorResponse['issues'];
  parsedError: ParsedApiError;

  constructor(message: string, issues: SystemConfigValidationErrorResponse['issues'], parsedError?: ParsedApiError) {
    super(message);
    this.name = 'SystemConfigValidationError';
    this.issues = issues;
    this.parsedError = parsedError ?? createParsedApiError({
      title: '配置校验失败',
      message,
      rawMessage: message,
      status: 400,
      category: 'http_error',
    });
  }
}

/** 配置版本冲突错误：携带当前 configVersion，供 UI 提示“与他人并发修改” */
export class SystemConfigConflictError extends Error {
  currentConfigVersion?: string;
  parsedError: ParsedApiError;

  constructor(message: string, currentConfigVersion?: string, parsedError?: ParsedApiError) {
    super(message);
    this.name = 'SystemConfigConflictError';
    this.currentConfigVersion = currentConfigVersion;
    this.parsedError = parsedError ?? createParsedApiError({
      title: '配置版本冲突',
      message,
      rawMessage: message,
      status: 409,
      category: 'http_error',
    });
  }
}

/** 把更新配置请求体转 snake_case（maskToken 默认打码、reloadNow 默认 true） */
function toSnakeUpdatePayload(payload: UpdateSystemConfigRequest): Record<string, unknown> {
  return {
    config_version: payload.configVersion,
    mask_token: payload.maskToken ?? '******',
    reload_now: payload.reloadNow ?? true,
    items: payload.items.map((item) => ({
      key: item.key,
      value: item.value,
    })),
  };
}

/** 把校验请求体转 snake_case */
function toSnakeValidatePayload(payload: ValidateSystemConfigRequest): Record<string, unknown> {
  return {
    items: payload.items.map((item) => ({
      key: item.key,
      value: item.value,
    })),
  };
}

/** 把导入配置请求体转 snake_case */
function toSnakeImportPayload(payload: ImportSystemConfigRequest): Record<string, unknown> {
  return {
    config_version: payload.configVersion,
    content: payload.content,
    reload_now: payload.reloadNow ?? true,
  };
}

/** 把 LLM 渠道连通性测试请求体转 snake_case（未提供的字段用安全默认值） */
function toSnakeTestChannelPayload(payload: TestLLMChannelRequest): Record<string, unknown> {
  const request: Record<string, unknown> = {
    name: payload.name,
    protocol: payload.protocol,
    base_url: payload.baseUrl ?? '',
    api_key: payload.apiKey ?? '',
    models: payload.models,
    enabled: payload.enabled ?? true,
    timeout_seconds: payload.timeoutSeconds ?? 20,
    use_saved_secret: payload.useSavedSecret ?? false,
  };
  if (payload.capabilityChecks && payload.capabilityChecks.length > 0) {
    request.capability_checks = payload.capabilityChecks;
  }
  return request;
}

/** 把通知渠道测试请求体转 snake_case（标题/正文有默认测试文案） */
function toSnakeNotificationTestPayload(payload: TestNotificationChannelRequest): Record<string, unknown> {
  return {
    channel: payload.channel,
    items: (payload.items || []).map((item) => ({
      key: item.key,
      value: item.value,
    })),
    mask_token: payload.maskToken ?? '******',
    title: payload.title ?? 'DSA 通知测试',
    content: payload.content ?? '这是一条来自 DSA Web 设置页的通知测试消息。',
    timeout_seconds: payload.timeoutSeconds ?? 20,
  };
}

/** 把模型发现请求体转 snake_case */
function toSnakeDiscoverModelsPayload(payload: DiscoverLLMChannelModelsRequest): Record<string, unknown> {
  return {
    name: payload.name,
    protocol: payload.protocol,
    base_url: payload.baseUrl ?? '',
    api_key: payload.apiKey ?? '',
    models: payload.models,
    timeout_seconds: payload.timeoutSeconds ?? 20,
    use_saved_secret: payload.useSavedSecret ?? false,
  };
}

/** 把生成后端状态预览请求体转 snake_case */
function toSnakeGenerationBackendStatusPreviewPayload(
  payload: GenerationBackendStatusPreviewRequest = {},
): Record<string, unknown> {
  return {
    items: (payload.items || []).map((item) => ({
      key: item.key,
      value: item.value,
    })),
    mask_token: payload.maskToken ?? '******',
  };
}

/** 把生成后端冒烟测试请求体转 snake_case（mode 默认 json，可指定 backendId/超时） */
function toSnakeGenerationBackendSmokePayload(payload: TestGenerationBackendRequest = {}): Record<string, unknown> {
  const request: Record<string, unknown> = {
    mode: payload.mode ?? 'json',
    items: (payload.items || []).map((item) => ({
      key: item.key,
      value: item.value,
    })),
    mask_token: payload.maskToken ?? '******',
  };
  if (payload.backendId) {
    request.backend_id = payload.backendId;
  }
  if (payload.timeoutSeconds !== undefined && payload.timeoutSeconds !== null) {
    request.timeout_seconds = payload.timeoutSeconds;
  }
  return request;
}

/** 把智能体后端状态预览请求体转 snake_case */
function toSnakeAgentBackendPayload(
  payload: AgentBackendStatusPreviewRequest = {},
): Record<string, unknown> {
  return {
    items: (payload.items || []).map((item) => ({ key: item.key, value: item.value })),
    mask_token: payload.maskToken ?? '******',
  };
}

export const systemConfigApi = {
  /** 获取系统配置（includeSchema 控制是否一并返回表单 Schema） */
  async getConfig(includeSchema = true): Promise<SystemConfigResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/system/config', {
      params: { include_schema: includeSchema },
    });
    return toCamelCase<SystemConfigResponse>(response.data);
  },

  /** 导出当前配置为环境变量文本 */
  async exportEnv(): Promise<ExportSystemConfigResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/system/config/export');
    return toCamelCase<ExportSystemConfigResponse>(response.data);
  },

  /** 桌面端导出配置（复用导出接口） */
  async exportDesktopEnv(): Promise<ExportSystemConfigResponse> {
    return this.exportEnv();
  },

  /** 获取配置项的 Schema 定义（用于动态渲染设置表单） */
  async getSchema(): Promise<SystemConfigSchemaResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/system/config/schema');
    return toCamelCase<SystemConfigSchemaResponse>(response.data);
  },

  /** 获取初始化设置状态（是否已完成首 run setup） */
  async getSetupStatus(): Promise<SetupStatusResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/system/config/setup/status');
    return toCamelCase<SetupStatusResponse>(response.data);
  },

  /** 获取生成后端（模型通道）的运行状态 */
  async getGenerationBackendStatus(): Promise<GenerationBackendStatusResponse> {
    const response = await apiClient.get<Record<string, unknown>>(
      '/api/v1/system/config/generation-backends/status',
    );
    return toCamelCase<GenerationBackendStatusResponse>(response.data);
  },

  /** 基于草稿配置预览生成后端状态（不持久化） */
  async previewGenerationBackendStatus(
    payload: GenerationBackendStatusPreviewRequest = {},
  ): Promise<GenerationBackendStatusResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/generation-backends/status/preview',
      toSnakeGenerationBackendStatusPreviewPayload(payload),
    );
    return toCamelCase<GenerationBackendStatusResponse>(response.data);
  },

  /** 对生成后端做冒烟测试（验证模型通道可用性） */
  async testGenerationBackend(payload: TestGenerationBackendRequest = {}): Promise<TestGenerationBackendResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/generation-backends/smoke-test',
      toSnakeGenerationBackendSmokePayload(payload),
    );
    return toCamelCase<TestGenerationBackendResponse>(response.data);
  },

  /** 获取智能体后端运行状态 */
  async getAgentBackendStatus(): Promise<AgentBackendStatusResponse> {
    const response = await apiClient.get<Record<string, unknown>>(
      '/api/v1/system/config/agent-backends/status',
    );
    return toCamelCase<AgentBackendStatusResponse>(response.data);
  },

  /** 基于草稿配置预览智能体后端状态（不持久化） */
  async previewAgentBackendStatus(
    payload: AgentBackendStatusPreviewRequest = {},
  ): Promise<AgentBackendStatusResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/agent-backends/status/preview',
      toSnakeAgentBackendPayload(payload),
    );
    return toCamelCase<AgentBackendStatusResponse>(response.data);
  },

  /** 获取调度器运行状态 */
  async getSchedulerStatus(): Promise<SchedulerStatusResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/system/scheduler/status');
    return toCamelCase<SchedulerStatusResponse>(response.data);
  },

  /** 手动立即触发一次调度任务 */
  async runSchedulerNow(): Promise<SchedulerRunNowResponse> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/system/scheduler/run-now');
    return toCamelCase<SchedulerRunNowResponse>(response.data);
  },

  /** 校验配置（不持久化），返回校验结果与逐条 issue */
  async validate(payload: ValidateSystemConfigRequest): Promise<ValidateSystemConfigResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/validate',
      toSnakeValidatePayload(payload),
    );
    return toCamelCase<ValidateSystemConfigResponse>(response.data);
  },

  /** 从文本导入配置（env 格式） */
  async importEnv(payload: ImportSystemConfigRequest): Promise<UpdateSystemConfigResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/import',
      toSnakeImportPayload(payload),
    );
    return toCamelCase<UpdateSystemConfigResponse>(response.data);
  },

  /** 桌面端导入配置（复用导入接口） */
  async importDesktopEnv(payload: ImportSystemConfigRequest): Promise<UpdateSystemConfigResponse> {
    return this.importEnv(payload);
  },

  /** 测试单个 LLM 渠道连通性 */
  async testLLMChannel(payload: TestLLMChannelRequest): Promise<TestLLMChannelResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/llm/test-channel',
      toSnakeTestChannelPayload(payload),
    );
    return toCamelCase<TestLLMChannelResponse>(response.data);
  },

  /** 测试单个通知渠道连通性（发送测试消息） */
  async testNotificationChannel(payload: TestNotificationChannelRequest): Promise<TestNotificationChannelResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/notification/test-channel',
      toSnakeNotificationTestPayload(payload),
    );
    return toCamelCase<TestNotificationChannelResponse>(response.data);
  },

  /** 让后端按渠道配置发现可用模型列表 */
  async discoverLLMChannelModels(
    payload: DiscoverLLMChannelModelsRequest,
  ): Promise<DiscoverLLMChannelModelsResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/system/config/llm/discover-models',
      toSnakeDiscoverModelsPayload(payload),
    );
    return toCamelCase<DiscoverLLMChannelModelsResponse>(response.data);
  },

  /**
   * 提交配置更新（PUT）。
   * 拦截 400 抛 SystemConfigValidationError（带 issues），409 抛 SystemConfigConflictError（带当前版本），
   * 其余错误原样向上抛，便于 UI 统一处理。
   */
  async update(payload: UpdateSystemConfigRequest): Promise<UpdateSystemConfigResponse> {
    try {
      const response = await apiClient.put<Record<string, unknown>>(
        '/api/v1/system/config',
        toSnakeUpdatePayload(payload),
      );
      return toCamelCase<UpdateSystemConfigResponse>(response.data);
    } catch (error: unknown) {
      const parsed = getParsedApiError(error);
      if (error && typeof error === 'object' && 'response' in error) {
        const status = (error as { response?: { status?: number } }).response?.status;
        const payloadData = (error as { response?: { data?: unknown } }).response?.data;

        if (status === 400) {
          const validationError = toCamelCase<SystemConfigValidationErrorResponse>(payloadData ?? {});
          throw new SystemConfigValidationError(
            parsed.message || validationError.message || '配置校验失败',
            validationError.issues || [],
            parsed,
          );
        }

        if (status === 409) {
          const conflict = toCamelCase<SystemConfigConflictResponse>(payloadData ?? {});
          throw new SystemConfigConflictError(
            parsed.message || conflict.message || '配置版本冲突',
            conflict.currentConfigVersion,
            parsed,
          );
        }
      }

      throw error;
    }
  },

  /**
   * 获取自选队列股票代码列表
   */
  getWatchlist: async (): Promise<string[]> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/stocks/watchlist');
    const data = toCamelCase<{ stockCodes: string[] }>(response.data);
    return data.stockCodes || [];
  },

  /**
   * 添加股票到自选队列（返回更新后的列表）
   */
  addToWatchlist: async (stockCode: string): Promise<string[]> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/stocks/watchlist/add', {
      stock_code: stockCode,
    });
    const data = toCamelCase<{ stockCodes: string[] }>(response.data);
    return data.stockCodes || [];
  },

  /**
   * 从自选队列移除股票（返回更新后的列表）
   */
  removeFromWatchlist: async (stockCode: string): Promise<string[]> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/stocks/watchlist/remove', {
      stock_code: stockCode,
    });
    const data = toCamelCase<{ stockCodes: string[] }>(response.data);
    return data.stockCodes || [];
  },
};
