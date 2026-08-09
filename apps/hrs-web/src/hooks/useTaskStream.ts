import { useEffect, useRef, useCallback, useState, type MutableRefObject } from 'react';
import { analysisApi } from '../api/analysis';
import { toCamelCase } from '../api/utils';
import type { TaskInfo } from '../types/analysis';
import type { RunFlowEvent } from '../types/runFlow';

/**
 * SSE 事件类型：服务端通过不同事件名推送任务状态变化。
 * connected 表示连接就绪，heartbeat 为保活心跳。
 */
export type SSEEventType =
  | 'connected'
  | 'task_created'
  | 'task_started'
  | 'task_progress'
  | 'task_completed'
  | 'task_failed'
  | 'heartbeat';

/**
 * SSE 事件负载的统一形状（透传给各回调）。
 */
export interface SSEEvent {
  type: SSEEventType;
  task?: TaskInfo;
  flowEvent?: RunFlowEvent;
  timestamp?: string;
}

/**
 * useTaskStream 选项：以回调形式订阅各类任务事件。
 */
export interface UseTaskStreamOptions {
  /** 任务创建时回调 */
  onTaskCreated?: (task: TaskInfo) => void;
  /** 任务开始时回调 */
  onTaskStarted?: (task: TaskInfo) => void;
  /** 任务完成时回调 */
  onTaskCompleted?: (task: TaskInfo) => void;
  /** 任务进度更新时回调 */
  onTaskProgress?: (task: TaskInfo) => void;
  /** 任务失败时回调 */
  onTaskFailed?: (task: TaskInfo) => void;
  /** task_progress 携带的增量运行流事件（用于绘制流程图） */
  onTaskFlowEvent?: (task: TaskInfo, event: RunFlowEvent) => void;
  /** 连接建立时回调 */
  onConnected?: () => void;
  /** 连接出错时回调 */
  onError?: (error: Event) => void;
  /** 是否自动重连，默认 true */
  autoReconnect?: boolean;
  /** 重连延迟（毫秒），默认 3000 */
  reconnectDelay?: number;
  /** 是否启用本 hook，默认 true */
  enabled?: boolean;
}

/**
 * useTaskStream 返回值：连接态与手动 连接/断开 控制。
 */
export interface UseTaskStreamResult {
  /** 当前是否已连接 */
  isConnected: boolean;
  /** 手动重连 */
  reconnect: () => void;
  /** 手动断开 */
  disconnect: () => void;
}

// 仅从这些回调中挑选用于订阅的部分
type TaskStreamCallbacks = Pick<
  UseTaskStreamOptions,
  | 'onTaskCreated'
  | 'onTaskStarted'
  | 'onTaskCompleted'
  | 'onTaskProgress'
  | 'onTaskFailed'
  | 'onTaskFlowEvent'
  | 'onConnected'
  | 'onError'
>;

/** 解析后的负载：任务对象 + 可选的 flow 事件。 */
type ParsedTaskStreamPayload = {
  task: TaskInfo;
  flowEvent?: RunFlowEvent;
};

/** 单个订阅者的句柄：持有最新回调 ref、连接态 setter 与重连配置。 */
type TaskStreamSubscriber = {
  callbacksRef: MutableRefObject<TaskStreamCallbacks>;
  setIsConnected: (value: boolean) => void;
  autoReconnect: boolean;
  reconnectDelay: number;
};

// ===== 模块级单例：所有 useTaskStream 实例共享同一条 SSE 连接 =====
// 多个组件同时挂载时只维持一个 EventSource，避免重复订阅造成的资源浪费与事件重复分发。
let sharedEventSource: EventSource | null = null;
let sharedReconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let sharedConnected = false;
let nextSubscriberId = 1;
const subscribers = new Map<number, TaskStreamSubscriber>();

/** 将后端的 snake_case 负载映射为前端的 camelCase TaskInfo 对象。 */
const toTaskInfo = (data: Record<string, unknown>): TaskInfo => {
  const task: TaskInfo = {
    taskId: data.task_id as string,
    stockCode: data.stock_code as string,
    stockName: data.stock_name as string | undefined,
    status: data.status as TaskInfo['status'],
    progress: data.progress as number,
    message: data.message as string | undefined,
    reportType: data.report_type as string,
    createdAt: data.created_at as string,
    startedAt: data.started_at as string | undefined,
    completedAt: data.completed_at as string | undefined,
    error: data.error as string | undefined,
    originalQuery: data.original_query as string | undefined,
    selectionSource: data.selection_source as string | undefined,
    analysisPhase: data.analysis_phase as TaskInfo['analysisPhase'],
    skills: Array.isArray(data.skills) ? data.skills.map(String) : undefined,
  };

  // 可选字段：仅在后端返回且非空时补齐
  if (typeof data.trace_id === 'string' && data.trace_id.trim()) {
    task.traceId = data.trace_id;
  }
  if (typeof data.region === 'string' && data.region.trim()) {
    task.region = data.region;
  }

  return task;
};

/** 解析 SSE 事件 data：JSON 解析 + 任务映射 + flow_event 驼峰转换；失败时返回 null。 */
const parseEventData = (eventData: string): ParsedTaskStreamPayload | null => {
  try {
    const data = JSON.parse(eventData);
    const task = toTaskInfo(data);
    const flowEvent = data.flow_event
      ? toCamelCase<RunFlowEvent>(data.flow_event)
      : undefined;
    return { task, flowEvent };
  } catch (e) {
    console.error('Failed to parse SSE event data:', e);
    return null;
  }
};

/** 广播连接态给所有订阅者。 */
const notifyConnectionState = (connected: boolean) => {
  sharedConnected = connected;
  subscribers.forEach((subscriber) => subscriber.setIsConnected(connected));
};

/** 遍历所有订阅者，用其「当前最新的」回调集合触发通知。 */
const forEachSubscriber = (notify: (callbacks: TaskStreamCallbacks) => void) => {
  subscribers.forEach((subscriber) => notify(subscriber.callbacksRef.current));
};

/** 清除计划中的重连锁定时器。 */
const clearSharedReconnect = () => {
  if (sharedReconnectTimeout) {
    clearTimeout(sharedReconnectTimeout);
    sharedReconnectTimeout = null;
  }
};

/** 关闭共享连接并通知所有订阅者已断开。 */
const closeSharedConnection = () => {
  clearSharedReconnect();
  if (sharedEventSource) {
    sharedEventSource.close();
    sharedEventSource = null;
  }
  notifyConnectionState(false);
};

/** 安排一次共享重连：取所有开启 autoReconnect 的订阅者中最小的重连延迟。 */
const scheduleSharedReconnect = () => {
  if (sharedReconnectTimeout || subscribers.size === 0) {
    return;
  }
  const reconnectDelays = Array.from(subscribers.values())
    .filter((subscriber) => subscriber.autoReconnect)
    .map((subscriber) => subscriber.reconnectDelay);
  if (reconnectDelays.length === 0) {
    return;
  }
  const reconnectDelay = Math.min(...reconnectDelays);
  sharedReconnectTimeout = setTimeout(() => {
    sharedReconnectTimeout = null;
    connectSharedStream();
  }, reconnectDelay);
};

/**
 * 建立（或复用）共享 SSE 连接，并绑定各事件监听器。
 * 事件到达后解析负载，再广播给全部订阅者的对应回调。
 */
function connectSharedStream() {
  if (sharedEventSource || subscribers.size === 0) {
    return;
  }

  if (typeof window.EventSource !== 'function') {
    notifyConnectionState(false);
    return;
  }

  const url = analysisApi.getTaskStreamUrl();
  const eventSource = new window.EventSource(url, { withCredentials: true });
  sharedEventSource = eventSource;

  eventSource.addEventListener('connected', () => {
    notifyConnectionState(true);
    forEachSubscriber((callbacks) => callbacks.onConnected?.());
  });

  eventSource.addEventListener('task_created', (e) => {
    const payload = parseEventData((e as MessageEvent<string>).data);
    if (payload) {
      forEachSubscriber((callbacks) => callbacks.onTaskCreated?.(payload.task));
    }
  });

  eventSource.addEventListener('task_started', (e) => {
    const payload = parseEventData((e as MessageEvent<string>).data);
    if (payload) {
      forEachSubscriber((callbacks) => callbacks.onTaskStarted?.(payload.task));
    }
  });

  eventSource.addEventListener('task_progress', (e) => {
    const payload = parseEventData((e as MessageEvent<string>).data);
    if (payload) {
      forEachSubscriber((callbacks) => {
        callbacks.onTaskProgress?.(payload.task);
        if (payload.flowEvent) {
          callbacks.onTaskFlowEvent?.(payload.task, payload.flowEvent);
        }
      });
    }
  });

  eventSource.addEventListener('task_completed', (e) => {
    const payload = parseEventData((e as MessageEvent<string>).data);
    if (payload) {
      forEachSubscriber((callbacks) => callbacks.onTaskCompleted?.(payload.task));
    }
  });

  eventSource.addEventListener('task_failed', (e) => {
    const payload = parseEventData((e as MessageEvent<string>).data);
    if (payload) {
      forEachSubscriber((callbacks) => callbacks.onTaskFailed?.(payload.task));
    }
  });

  eventSource.addEventListener('heartbeat', () => {
    // 心跳事件可选：可在此记录最近一次心跳时间
  });

  // 连接错误：通知断开、触发错误回调，并在仍有效时安排自动重连
  eventSource.onerror = (error) => {
    notifyConnectionState(false);
    forEachSubscriber((callbacks) => callbacks.onError?.(error));
    if (sharedEventSource === eventSource) {
      eventSource.close();
      sharedEventSource = null;
    }
    scheduleSharedReconnect();
  };
}

/** 强制重连：先关闭共享连接再重建。 */
const reconnectSharedStream = () => {
  closeSharedConnection();
  connectSharedStream();
};

/**
 * useTaskStream —— 基于 SSE 的实时任务流订阅 hook。
 *
 * 多个组件可同时调用本 hook，但它们共享同一条底层 EventSource 连接（模块级单例），
 * 由 subscribers 多播分发。组件挂载时注册订阅、卸载时注销；最后一个订阅者注销时关闭连接。
 *
 * @param options 事件回调与各开关（enabled / autoReconnect / reconnectDelay）
 * @returns { isConnected, reconnect, disconnect } 连接态与手动控制
 */
export function useTaskStream(options: UseTaskStreamOptions = {}): UseTaskStreamResult {
  const {
    onTaskCreated,
    onTaskStarted,
    onTaskCompleted,
    onTaskProgress,
    onTaskFailed,
    onTaskFlowEvent,
    onConnected,
    onError,
    autoReconnect = true,
    reconnectDelay = 3000,
    enabled = true,
  } = options;

  // 连接态（本地镜像，初始为 false，挂载后会由共享连接态同步）
  const [isConnected, setIsConnected] = useState(false);
  // 本实例在 subscribers Map 中的 id，用于卸载时注销
  const subscriberIdRef = useRef<number | null>(null);
  // 连接延迟定时器句柄，便于在清理时取消未触发的连接
  const connectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 用 ref 保存最新回调，避免因回调引用变化而重建连接
  const callbacksRef = useRef<TaskStreamCallbacks>({
    onTaskCreated,
    onTaskStarted,
    onTaskCompleted,
    onTaskProgress,
    onTaskFailed,
    onTaskFlowEvent,
    onConnected,
    onError,
  });

  // 每次渲染把最新回调写入 ref，供活跃 SSE 处理器读取当前逻辑
  useEffect(() => {
    callbacksRef.current = {
      onTaskCreated,
      onTaskStarted,
      onTaskCompleted,
      onTaskProgress,
      onTaskFailed,
      onTaskFlowEvent,
      onConnected,
      onError,
    };
  });

  /**
   * 断开连接：取消挂起的连接定时器、从订阅者注销，
   * 并在无其余订阅者时关闭共享连接。连接态更新延后到微任务，避免嵌套渲染。
   */
  const disconnect = useCallback(() => {
    if (connectTimerRef.current) {
      window.clearTimeout(connectTimerRef.current);
      connectTimerRef.current = null;
    }
    if (subscriberIdRef.current !== null) {
      subscribers.delete(subscriberIdRef.current);
      subscriberIdRef.current = null;
    }
    if (subscribers.size === 0) {
      closeSharedConnection();
    }
    queueMicrotask(() => setIsConnected(false));
  }, []);

  /** 手动重连：若尚未订阅则先注册，再触发共享重连。 */
  const reconnect = useCallback(() => {
    if (subscriberIdRef.current === null) {
      const subscriberId = nextSubscriberId++;
      subscriberIdRef.current = subscriberId;
      subscribers.set(subscriberId, {
        callbacksRef,
        setIsConnected,
        autoReconnect,
        reconnectDelay,
      });
    }
    reconnectSharedStream();
  }, [autoReconnect, reconnectDelay]);

  // 随 enabled 变化建立或断开订阅：启用时注册订阅者并延迟一拍建立共享连接（避免与渲染同帧）
  useEffect(() => {
    if (enabled) {
      const subscriberId = nextSubscriberId++;
      subscriberIdRef.current = subscriberId;
      subscribers.set(subscriberId, {
        callbacksRef,
        setIsConnected,
        autoReconnect,
        reconnectDelay,
      });
      setIsConnected(sharedConnected);
      connectTimerRef.current = window.setTimeout(() => {
        connectTimerRef.current = null;
        connectSharedStream();
      }, 0);
      return () => {
        disconnect();
      };
    }

    disconnect();
    return () => {
      disconnect();
    };
  }, [autoReconnect, disconnect, enabled, reconnectDelay]);

  return {
    isConnected,
    reconnect,
    disconnect,
  };
}

export default useTaskStream;
