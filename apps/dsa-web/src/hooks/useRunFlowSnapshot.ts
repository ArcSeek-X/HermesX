import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { analysisApi } from '../api/analysis';
import { getParsedApiError, type ParsedApiError } from '../api/error';
import { historyApi } from '../api/history';
import type { RunFlowEdge, RunFlowEvent, RunFlowNode, RunFlowSnapshot, RunFlowSnapshotSource } from '../types/runFlow';
import { useTaskStream } from './useTaskStream';

/**
 * useRunFlowSnapshot —— 运行流（analysis/backtest 执行过程）可视化快照 hook。
 *
 * 职责：根据 source（实时任务 task / 历史记录 history）拉取运行流快照（DAG：nodes + edges + events），
 * 并在实时场景下，通过 SSE 增量事件实时补充、重放，构建出「分析流水线」的交互式图表。
 */

/** 选项：数据源（task 或 history）与是否启用。 */
interface UseRunFlowSnapshotOptions {
  source?: RunFlowSnapshotSource | null;
  enabled?: boolean;
}

/** 返回值：快照、加载态、错误、手动重新拉取。 */
interface UseRunFlowSnapshotResult {
  snapshot: RunFlowSnapshot | null;
  isLoading: boolean;
  error: ParsedApiError | null;
  refetch: () => Promise<void>;
}

/** 单次请求的状态：用 requestKey 标识当前生效的响应，避免过期响应覆盖新请求。 */
type RunFlowRequestState = {
  requestKey: string;
  snapshot: RunFlowSnapshot | null;
  error: ParsedApiError | null;
};

/** 实时事件环形缓冲上限：仅保留最近 50 条增量事件用于重放，防止内存无限增长。 */
const MAX_BUFFERED_FLOW_EVENTS = 50;

/** 将 source 归一为稳定字符串键，用于判断「数据源是否变化」。 */
const getSourceKey = (source?: RunFlowSnapshotSource | null): string => {
  if (!source) {
    return 'none';
  }
  return source.type === 'task'
    ? `task:${source.taskId}`
    : `history:${source.recordId}`;
};

/** 判定 source 是否为可请求的有效源（task 需有非空 taskId；history 需有有限 recordId）。 */
const isUsableSource = (source?: RunFlowSnapshotSource | null): source is RunFlowSnapshotSource => {
  if (!source) {
    return false;
  }
  if (source.type === 'task') {
    return Boolean(source.taskId.trim());
  }
  return Number.isFinite(source.recordId);
};

/** 取事件时间戳的数值（无效则为 0），用于排序。 */
const eventTime = (event: RunFlowEvent): number => (
  event.timestamp ? Date.parse(event.timestamp) || 0 : 0
);

/** 把新事件并入事件列表：以 id 去重（无 id 用序号兜底），并按时间升序排列。 */
const mergeEvents = (events: RunFlowEvent[], incoming: RunFlowEvent): RunFlowEvent[] => {
  const byId = new Map<string, RunFlowEvent>();
  [...events, incoming].forEach((event, index) => {
    byId.set(event.id || `event-${index}`, event);
  });
  return Array.from(byId.values()).sort((left, right) => eventTime(left) - eventTime(right));
};

/** 校验未知值是否为合法的 RunFlowNode（含 id/lane/kind/label/status 必备字段）。 */
const isRunFlowNode = (value: unknown): value is RunFlowNode => {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const node = value as Partial<RunFlowNode>;
  return Boolean(node.id && node.lane && node.kind && node.label && node.status);
};

/** 从 metadata 中按候选 key 顺序取出首个非空字符串值（兼容 dataType / data_type 等多写法）。 */
const metadataString = (
  metadata: Record<string, unknown> | undefined,
  ...keys: string[]
): string | null => {
  const value = keys
    .map((key) => metadata?.[key])
    .find((item) => typeof item === 'string' && item.trim());
  return typeof value === 'string' ? value.trim() : null;
};

/** 从节点推断数据类型：优先读 metadata.dataType，否则从 provider_* 节点 id 解析。 */
const dataTypeFromNode = (node?: RunFlowNode): string | null => {
  if (!node) {
    return null;
  }
  const metadataValue = metadataString(node.metadata, 'dataType', 'data_type');
  if (metadataValue) {
    return metadataValue;
  }
  if (!node.id.startsWith('provider_')) {
    return null;
  }
  const inferred = node.id.replace(/^provider_/, '').split('_').slice(0, -2).join('_');
  return inferred || null;
};

/** 解析事件关联的数据类型：事件 metadata 优先，回退到节点，再回退 'provider'。 */
const dataTypeFromEvent = (event: RunFlowEvent, node?: RunFlowNode): string => (
  metadataString(event.metadata, 'dataType', 'data_type')
  || dataTypeFromNode(node)
  || 'provider'
);

/** 计算事件归属的节点 id：节点候选优先，否则取 event.nodeId。 */
const eventNodeId = (event: RunFlowEvent, nodeCandidate?: RunFlowNode | null): string | null => (
  nodeCandidate?.id || event.nodeId || null
);

/** 在事件序列中，找到当前事件之前、属于指定类型且关联节点的「最近一条」事件节点 id。 */
const latestEventNodeId = (
  events: RunFlowEvent[],
  nodeById: Map<string, RunFlowNode>,
  types: string[],
  currentEvent: RunFlowEvent,
): string | null => {
  const typeSet = new Set(types);
  const currentTime = eventTime(currentEvent);
  const matchingEvents = events
    .filter((event) => (
      event.id !== currentEvent.id
      && eventTime(event) < currentTime
      && typeSet.has(event.type)
      && event.nodeId
      && nodeById.has(event.nodeId)
    ))
    .sort((left, right) => eventTime(left) - eventTime(right));
  return matchingEvents.at(-1)?.nodeId || null;
};

/** 判断某条 (from→to, kind) 边是否已存在，避免重复边。 */
const edgeExists = (edges: RunFlowEdge[], from: string, to: string, kind: RunFlowEdge['kind']): boolean => (
  edges.some((edge) => edge.from === from && edge.to === to && edge.kind === kind)
);

/** 追加一条边（自环或不重复时跳过），自动生成稳定 id。 */
const appendEdge = (
  edges: RunFlowEdge[],
  from: string,
  to: string,
  kind: RunFlowEdge['kind'],
  status: RunFlowEdge['status'],
  label: string,
  message?: string | null,
): RunFlowEdge[] => {
  if (from === to || edgeExists(edges, from, to, kind)) {
    return edges;
  }
  return [
    ...edges,
    {
      id: `${from}_to_${to}_${kind}`,
      from,
      to,
      kind,
      status,
      label,
      message,
    },
  ];
};

/** 更新指向某个节点的入边状态（如节点由 pending 变为 success/failed 时同步边状态）。 */
const refreshIncomingEdgeStatus = (
  edges: RunFlowEdge[],
  nodeId: string | null,
  status?: RunFlowEdge['status'],
): RunFlowEdge[] => {
  if (!nodeId || !status) {
    return edges;
  }
  let changed = false;
  const refreshed = edges.map((edge) => {
    if (edge.to !== nodeId || edge.status === status) {
      return edge;
    }
    changed = true;
    return {
      ...edge,
      status,
    };
  });
  return changed ? refreshed : edges;
};

/** 判定两次 provider 调用之间的边类型：fallback（降级）/ retry（重试）/ data（普通调用）。 */
const providerTransitionKind = (
  previous: { provider: string | null; success: boolean; fallbackTo: string | null },
  current: { provider: string | null; success: boolean; fallbackFrom: string | null },
): RunFlowEdge['kind'] => {
  if (previous.fallbackTo || current.fallbackFrom) {
    return 'fallback';
  }
  if (previous.provider && current.provider && previous.provider === current.provider) {
    return 'retry';
  }
  if (!previous.success) {
    return 'fallback';
  }
  return 'data';
};

/** 从事件/节点抽取 provider 调用的上下文（provider 名、是否成功、降级方向）。 */
const providerRunFromEvent = (
  event: RunFlowEvent,
  node?: RunFlowNode,
): { provider: string | null; success: boolean; fallbackFrom: string | null; fallbackTo: string | null } => ({
  provider: metadataString(event.metadata, 'provider') || node?.provider || null,
  success: event.severity === 'success' || node?.status === 'success' || node?.status === 'fallback',
  fallbackFrom: metadataString(event.metadata, 'fallbackFrom', 'fallback_from'),
  fallbackTo: metadataString(event.metadata, 'fallbackTo', 'fallback_to'),
});

/**
 * 根据事件类型推导并追加一条「派生边」，串联 DAG 各阶段：
 * - provider_run*：与同 dataType 的上一个 provider 节点相连，标注 调用/重试/降级
 * - llm_run*：由 analysis_pipeline（或 task_queue）指向，标注 生成
 * - history_run：由最近的 llm_run 指向，标注 保存
 * - notification_run：由 history_run / llm_run 指向，标注 通知
 */
const appendDerivedEdge = (
  nodes: RunFlowNode[],
  edges: RunFlowEdge[],
  events: RunFlowEvent[],
  displayEvent: RunFlowEvent,
  nodeId: string | null,
): RunFlowEdge[] => {
  if (!nodeId) {
    return edges;
  }
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const node = nodeById.get(nodeId);
  if (!node) {
    return edges;
  }

  if (displayEvent.type === 'provider_run' || displayEvent.type === 'provider_run_started') {
    const dataType = dataTypeFromEvent(displayEvent, node);
    const currentTime = eventTime(displayEvent);
    // 找到同 dataType、且早于当前事件的「上一个 provider_run」作为连接起点
    const previousEvent = events
      .filter((event) => {
        if (
          event.id === displayEvent.id
          || (event.type !== 'provider_run' && event.type !== 'provider_run_started')
          || !event.nodeId
        ) {
          return false;
        }
        if (eventTime(event) >= currentTime) {
          return false;
        }
        const eventNode = nodeById.get(event.nodeId);
        return Boolean(eventNode && dataTypeFromEvent(event, eventNode) === dataType);
      })
      .sort((left, right) => eventTime(left) - eventTime(right))
      .at(-1);

    // 无前驱时，由 task_queue 拉起（标注「调用」）
    if (!previousEvent?.nodeId) {
      return nodeById.has('task_queue')
        ? appendEdge(edges, 'task_queue', nodeId, 'control', node.status, '调用')
        : edges;
    }

    const previousNode = nodeById.get(previousEvent.nodeId);
    if (!previousNode) {
      return edges;
    }
    const transitionKind = providerTransitionKind(
      providerRunFromEvent(previousEvent, previousNode),
      providerRunFromEvent(displayEvent, node),
    );
    const label = transitionKind === 'fallback'
      ? '降级'
      : transitionKind === 'retry'
        ? '重试'
        : '调用';
    const message = metadataString(displayEvent.metadata, 'fallbackFrom', 'fallback_from', 'fallbackTo', 'fallback_to');
    return appendEdge(edges, previousNode.id, nodeId, transitionKind, node.status, label, message);
  }

  if (displayEvent.type === 'llm_run' || displayEvent.type === 'llm_run_started') {
    const anchor = nodeById.has('analysis_pipeline') ? 'analysis_pipeline' : 'task_queue';
    return nodeById.has(anchor)
      ? appendEdge(edges, anchor, nodeId, 'data', node.status, '生成')
      : edges;
  }

  if (displayEvent.type === 'history_run') {
    const anchor = latestEventNodeId(events, nodeById, ['llm_run', 'llm_run_started'], displayEvent)
      || (nodeById.has('analysis_pipeline') ? 'analysis_pipeline' : 'task_queue');
    return nodeById.has(anchor)
      ? appendEdge(edges, anchor, nodeId, 'data', node.status, '保存')
      : edges;
  }

  if (displayEvent.type === 'notification_run') {
    const anchor = latestEventNodeId(events, nodeById, ['history_run'], displayEvent)
      || latestEventNodeId(events, nodeById, ['llm_run', 'llm_run_started'], displayEvent)
      || (nodeById.has('analysis_pipeline') ? 'analysis_pipeline' : 'task_queue');
    return nodeById.has(anchor)
      ? appendEdge(edges, anchor, nodeId, 'control', node.status, '通知')
      : edges;
  }

  return edges;
};

/**
 * 插入或更新节点：已存在则浅合并（metadata 做深合并），否则追加到末尾。
 */
const upsertNode = (nodes: RunFlowNode[], nodeCandidate: RunFlowNode | null): RunFlowNode[] => {
  if (!nodeCandidate) {
    return nodes;
  }
  const existingIndex = nodes.findIndex((node) => node.id === nodeCandidate.id);
  if (existingIndex < 0) {
    return [...nodes, nodeCandidate];
  }
  return nodes.map((node, index) => {
    if (index !== existingIndex) {
      return node;
    }
    return {
      ...node,
      ...nodeCandidate,
      metadata: {
        ...(node.metadata || {}),
        ...(nodeCandidate.metadata || {}),
      },
    };
  });
};

/** 基于 nodes/edges/events 计算「实时摘要」：瓶颈节点、失败次数、降级次数、模型与数据源数等。 */
const buildLiveSummary = (
  snapshot: RunFlowSnapshot,
  nodes: RunFlowNode[],
  edges: RunFlowEdge[],
  events: RunFlowEvent[],
): RunFlowSnapshot['summary'] => {
  // 瓶颈：耗时（durationMs）最长的节点
  const bottleneck = nodes.reduce<{ id: string | null; duration: number }>((current, node) => {
    const duration = typeof node.durationMs === 'number' && Number.isFinite(node.durationMs)
      ? node.durationMs
      : -1;
    return duration > current.duration ? { id: node.id, duration } : current;
  }, { id: null, duration: -1 });
  const failedAttempts = nodes.filter((node) => (
    (node.status === 'failed' || node.status === 'timeout')
    && ['data_source', 'model', 'artifact', 'notification'].includes(node.kind)
  )).length;
  const fallbackCount = edges.filter((edge) => edge.kind === 'fallback' || edge.kind === 'retry').length;
  const dataSourceCount = nodes.filter((node) => node.kind === 'data_source').length;
  const model = nodes.find((node) => node.kind === 'model' && node.provider)?.provider
    || snapshot.summary.model
    || null;

  return {
    ...snapshot.summary,
    bottleneckNodeId: bottleneck.id || snapshot.summary.bottleneckNodeId || null,
    failedAttempts,
    fallbackCount,
    model,
    dataSourceCount,
    eventCount: events.length,
  };
};

/**
 * 把一个 flow 增量事件合并进快照：提取内嵌 node、去重合并事件、upsert 节点、
 * 并在事件为新时推导边；最后重算摘要。这是实时增量更新的核心归并函数。
 */
const mergeFlowEventIntoSnapshot = (
  snapshot: RunFlowSnapshot,
  flowEvent: RunFlowEvent,
): RunFlowSnapshot => {
  // 事件可能内嵌 node 信息，提取后从事件 metadata 中移除，避免重复
  const nodeCandidate = flowEvent.metadata?.node;
  const eventMetadata = { ...(flowEvent.metadata || {}) };
  delete eventMetadata.node;
  const displayEvent: RunFlowEvent = {
    ...flowEvent,
    metadata: eventMetadata,
  };
  const eventAlreadyPresent = snapshot.events.some((event) => event.id === displayEvent.id);
  const events = mergeEvents(snapshot.events, displayEvent);
  const node = isRunFlowNode(nodeCandidate) ? nodeCandidate : null;
  const nodes = upsertNode(snapshot.nodes, node);
  // 仅当事件为新增时才推导边；已存在则只刷新入边状态
  const edges = eventAlreadyPresent
    ? snapshot.edges
    : refreshIncomingEdgeStatus(
      appendDerivedEdge(
        nodes,
        snapshot.edges,
        events,
        displayEvent,
        eventNodeId(displayEvent, node),
      ),
      eventNodeId(displayEvent, node),
      node?.status,
    );

  return {
    ...snapshot,
    nodes,
    edges,
    events,
    summary: buildLiveSummary(snapshot, nodes, edges, events),
    generatedAt: flowEvent.timestamp || snapshot.generatedAt,
  };
};

/** 把增量事件写入环形缓冲：去重 + 按时间升序 + 仅保留最近 MAX_BUFFERED_FLOW_EVENTS 条。 */
const rememberFlowEvent = (events: RunFlowEvent[], flowEvent: RunFlowEvent): RunFlowEvent[] => {
  const byId = new Map<string, RunFlowEvent>();
  [...events, flowEvent].forEach((event, index) => {
    byId.set(event.id || `${event.type}:${event.nodeId || 'none'}:${event.timestamp || index}`, event);
  });
  return Array.from(byId.values())
    .sort((left, right) => eventTime(left) - eventTime(right))
    .slice(-MAX_BUFFERED_FLOW_EVENTS);
};

/** 仍处于进行中的节点状态集合（用于判断增量事件是否仍需重放）。 */
const ACTIVE_NODE_STATUSES = new Set(['pending', 'running', 'cancel_requested']);

/** 还原增量事件归属的节点 id（优先内嵌 node）。 */
const replayEventNodeId = (flowEvent: RunFlowEvent): string | null => {
  const nodeCandidate = flowEvent.metadata?.node;
  if (isRunFlowNode(nodeCandidate)) {
    return nodeCandidate.id;
  }
  return flowEvent.nodeId || null;
};

/** 判断增量事件是否应重放：无关联节点，或关联节点仍在进行中（其最终态可能尚未落库）。 */
const shouldReplayFlowEvent = (snapshot: RunFlowSnapshot, flowEvent: RunFlowEvent): boolean => {
  const nodeId = replayEventNodeId(flowEvent);
  if (!nodeId) {
    return true;
  }
  const existingNode = snapshot.nodes.find((node) => node.id === nodeId);
  return !existingNode || ACTIVE_NODE_STATUSES.has(existingNode.status);
};

/** 用一组增量事件重放式地归并进快照（实时任务在拿到基础快照后补全进行中节点的最新事件）。 */
const replayFlowEvents = (
  snapshot: RunFlowSnapshot,
  flowEvents: RunFlowEvent[],
): RunFlowSnapshot => flowEvents.reduce(
  (currentSnapshot, flowEvent) => (
    shouldReplayFlowEvent(currentSnapshot, flowEvent)
      ? mergeFlowEventIntoSnapshot(currentSnapshot, flowEvent)
      : currentSnapshot
  ),
  snapshot,
);

export function useRunFlowSnapshot({
  source,
  enabled = true,
}: UseRunFlowSnapshotOptions): UseRunFlowSnapshotResult {
  // 请求状态：用 requestKey 标识当前生效响应（防止过期响应覆盖新请求）
  const [requestState, setRequestState] = useState<RunFlowRequestState>({
    requestKey: 'none',
    snapshot: null,
    error: null,
  });
  // 重新拉取令牌：自增后改变 requestKey，触发 useEffect 重拉
  const [reloadToken, setReloadToken] = useState(0);
  const sourceKey = useMemo(() => getSourceKey(source), [source]);
  const sourceType = source?.type;
  const taskId = source?.type === 'task' ? source.taskId : '';
  const recordId = source?.type === 'history' ? source.recordId : null;
  // 综合标识：数据源 + 重拉令牌，作为本次请求的唯一键
  const requestKey = `${sourceKey}:${reloadToken}`;
  const shouldLoad = enabled && isUsableSource(source);
  // 实时增量事件环形缓冲（仅在 task 场景用于首帧后重放）
  const flowEventBufferRef = useRef<RunFlowEvent[]>([]);

  /** 手动重新拉取：递增 reloadToken。 */
  const refetch = useCallback(async () => {
    setReloadToken((value) => value + 1);
  }, []);

  // 数据源切换时清空缓冲，避免把上一个任务的事件重放到新任务
  useEffect(() => {
    flowEventBufferRef.current = [];
  }, [sourceKey]);

  // 订阅实时任务流（仅 task 源启用）：
  // - 增量事件：先写入缓冲，再并入当前快照（仅当请求键匹配且已有快照，防止乱序覆盖）
  // - 任务完成/失败/连接错误：触发一次整体 refetch，拿到服务端最终快照
  useTaskStream({
    enabled: shouldLoad && sourceType === 'task',
    onTaskFlowEvent: (task, flowEvent) => {
      if (task.taskId !== taskId) {
        return;
      }
      flowEventBufferRef.current = rememberFlowEvent(flowEventBufferRef.current, flowEvent);
      setRequestState((current) => {
        const hasFreshState = current.requestKey === requestKey && current.snapshot;
        if (!hasFreshState) {
          return current;
        }
        return {
          ...current,
          snapshot: mergeFlowEventIntoSnapshot(current.snapshot as RunFlowSnapshot, flowEvent),
        };
      });
    },
    onTaskCompleted: (task) => {
      if (task.taskId === taskId) {
        void refetch();
      }
    },
    onTaskFailed: (task) => {
      if (task.taskId === taskId) {
        void refetch();
      }
    },
    onError: () => {
      if (sourceType === 'task') {
        void refetch();
      }
    },
  });

  // 拉取基础快照：task 源会用缓冲中的增量事件重放补全进行中节点；
  // history 源直接采用后端返回的完整快照。active 标志防止卸载后 setState。
  useEffect(() => {
    if (!shouldLoad || !sourceType) {
      return undefined;
    }

    let active = true;

    const request = sourceType === 'task'
      ? analysisApi.getTaskFlow(taskId)
      : historyApi.getRecordFlow(recordId ?? 0);

    request
      .then((result) => {
        if (active) {
          const snapshot = sourceType === 'task'
            ? replayFlowEvents(result, flowEventBufferRef.current)
            : result;
          setRequestState({
            requestKey,
            snapshot,
            error: null,
          });
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setRequestState({
            requestKey,
            snapshot: null,
            error: getParsedApiError(err),
          });
        }
      });

    return () => {
      active = false;
    };
  }, [recordId, requestKey, shouldLoad, sourceType, taskId]);

  // 只有请求键匹配的响应才对外暴露，否则视为「加载中」
  const hasFreshState = shouldLoad && requestState.requestKey === requestKey;

  return {
    snapshot: hasFreshState ? requestState.snapshot : null,
    isLoading: shouldLoad && !hasFreshState,
    error: hasFreshState ? requestState.error : null,
    refetch,
  };
}
