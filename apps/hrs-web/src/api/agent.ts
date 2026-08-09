import apiClient from './index';
import { API_BASE_URL } from '../utils/constants';
import { createApiError, isApiRequestError, parseApiError } from './error';
import { toCamelCase } from './utils';
import type { AgentBackendStatusResponse } from '../types/systemConfig';

/**
 * 智能体（Agent）对话与状态相关 API。
 * 提供一次性对话、SSE 流式对话、技能列表、后端状态、会话历史管理等能力。
 */

/** 流式对话的可选配置（目前主要用来传入 AbortSignal 以支持取消） */
export interface ChatStreamOptions {
  signal?: AbortSignal;
}

/** 判断一个错误是否为用户主动取消（AbortError），便于上层区分“取消”与“失败” */
export function isAbortError(error: unknown): boolean {
  return typeof error === 'object'
    && error !== null
    && 'name' in error
    && error.name === 'AbortError';
}

/** 一次性（非流式）对话请求体 */
export interface ChatRequest {
  /** 用户消息文本 */
  message: string;
  /** 需要启用的技能 id 列表（可选） */
  skills?: string[];
}

/** 流式对话请求体：在普通对话基础上支持会话/请求追踪与附加上下文 */
export interface ChatStreamRequest extends ChatRequest {
  /** 会话 id（用于多轮上下文） */
  session_id?: string;
  /** 请求 id（用于后续取消流式请求） */
  request_id?: string;
  /** 附加上下文（透传给后端） */
  context?: unknown;
}

/** 取消流式对话的响应：后端是否接受取消，以及对应的请求 id */
export interface CancelChatStreamResponse {
  accepted: boolean;
  request_id: string;
}

/** 一次性对话的响应 */
export interface ChatResponse {
  /** 是否成功 */
  success: boolean;
  /** 助手回复内容 */
  content: string;
  /** 会话 id */
  session_id: string;
  /** 失败时的错误信息 */
  error?: string;
}

/** 智能体后端状态响应（复用系统配置中的后端状态类型） */
export type AgentStatusResponse = AgentBackendStatusResponse;

/** 单个技能的元信息 */
export interface SkillInfo {
  id: string;
  name: string;
  description: string;
}

/** 技能列表响应（含默认技能 id） */
export interface SkillsResponse {
  skills: SkillInfo[];
  default_skill_id: string;
}

/** 会话列表项（用于历史会话侧边栏） */
export interface ChatSessionItem {
  session_id: string;
  title: string;
  message_count: number;
  created_at: string | null;
  last_active: string | null;
}

/** 单条会话消息 */
export interface ChatSessionMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string | null;
}

export const agentApi = {
  /** 发送一次性对话（非流式，超时 120s，适用于短问答） */
  async chat(payload: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/api/v1/agent/chat', payload, {
      timeout: 120000,
    });
    return response.data;
  },
  /** 获取可用技能列表与默认技能 id */
  async getSkills(): Promise<SkillsResponse> {
    const response = await apiClient.get<SkillsResponse>('/api/v1/agent/skills');
    return response.data;
  },
  /** 获取智能体后端运行状态（模型/通道可用性等） */
  async getStatus(): Promise<AgentStatusResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/agent/status');
    return toCamelCase<AgentStatusResponse>(response.data);
  },
  /** 获取历史会话列表（默认最近 50 条） */
  async getChatSessions(limit = 50): Promise<ChatSessionItem[]> {
    const response = await apiClient.get<{ sessions: ChatSessionItem[] }>('/api/v1/agent/chat/sessions', { params: { limit } });
    return response.data.sessions;
  },
  /** 获取指定会话的全部消息（用于回看历史对话） */
  async getChatSessionMessages(sessionId: string): Promise<ChatSessionMessage[]> {
    const response = await apiClient.get<{ messages: ChatSessionMessage[] }>(`/api/v1/agent/chat/sessions/${sessionId}`);
    return response.data.messages;
  },
  /** 删除指定历史会话 */
  async deleteChatSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/agent/chat/sessions/${sessionId}`);
  },
  /** 兼容旧路径的发送接口；成功返回 { success: true }，失败则抛出包含后端 message 的错误 */
  async sendChat(content: string): Promise<{ success: boolean }> {
    const response = await apiClient.post<{
      success: boolean;
      error?: string;
      message?: string;
    }>('/api/v1/agent/chat/send', { content });
    const data = response.data;
    if (data.success === false) {
      throw new Error(data.message || '发送失败');
    }
    return { success: true };
  },
  /**
   * 发起流式对话（SSE）。
   * 不走 axios，直接使用 fetch 以便把 ReadableStream 透传给调用方做增量渲染，
   * 并支持通过 AbortSignal 取消。非 2xx 时统一解析为 typed ApiError 抛出。
   */
  async chatStream(
    payload: ChatStreamRequest,
    options?: ChatStreamOptions,
  ): Promise<Response> {
    const base = API_BASE_URL || '';
    const url = `${base}/api/v1/agent/chat/stream`;
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include',
        signal: options?.signal,
      });

      if (response.ok) {
        return response;
      }

      const contentType = response.headers.get('content-type') || '';
      let responseData: unknown = null;
      if (contentType.includes('application/json')) {
        responseData = await response.json().catch(() => null);
      } else {
        responseData = await response.text().catch(() => null);
      }

      const parsed = parseApiError({
        response: {
          status: response.status,
          statusText: response.statusText,
          data: responseData,
        },
      });
      throw createApiError(parsed, {
        response: {
          status: response.status,
          statusText: response.statusText,
          data: responseData,
        },
      });
    } catch (error: unknown) {
      if (isApiRequestError(error)) {
        throw error;
      }
      if (isAbortError(error)) {
        throw error;
      }

      const parsed = parseApiError(error);
      throw createApiError(parsed, { cause: error });
    }
  },
  /** 按 request_id 取消进行中的流式对话 */
  async cancelChatStream(requestId: string): Promise<CancelChatStreamResponse> {
    const response = await apiClient.post<CancelChatStreamResponse>(
      `/api/v1/agent/chat/stream/${encodeURIComponent(requestId)}/cancel`,
    );
    return response.data;
  },
};
