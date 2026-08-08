import { useEffect, useRef } from 'react';
import type { TaskInfo } from '../types/analysis';
import { useTaskStream } from './useTaskStream';

/**
 * useDashboardLifecycle —— 仪表盘（首页）数据生命周期编排 hook。
 *
 * 集中管理首页所需的各类数据拉取与刷新时机：
 * 1. 首次挂载：加载历史、行情条、大盘复盘、进行中任务。
 * 2. 周期轮询：每 30 秒静默刷新一次。
 * 3. 可见性恢复（标签页切回前台）：立即刷新一次，避免陈旧数据。
 * 4. 实时任务流（SSE）：根据任务创建/进度/完成/失败事件同步状态并触发对应刷新。
 *
 * 通过传入的各个回调把「何时刷新」与「如何刷新」解耦，调用方只需提供数据操作实现。
 */
type UseDashboardLifecycleOptions = {
  /** 首次加载历史记录 */
  loadInitialHistory: () => Promise<void>;
  /** 刷新历史记录（silent=true 表示静默，不弹错误提示） */
  refreshHistory: (silent?: boolean) => Promise<void>;
  /** 某个任务完成时刷新其相关历史（可选，未提供则回退 refreshHistory(true)） */
  refreshHistoryForCompletedTask?: (task: TaskInfo) => Promise<void>;
  /** 刷新进行中的任务列表 */
  refreshActiveTasks: () => Promise<void>;
  /** 首次加载行情条 */
  loadStockBar: () => Promise<void>;
  /** 刷新行情条 */
  refreshStockBar: () => Promise<void>;
  /** 首次加载大盘复盘历史（可选） */
  loadMarketReviewHistory?: () => Promise<void>;
  /** 刷新大盘复盘历史（可选，silent 控制是否静默） */
  refreshMarketReviewHistory?: (silent?: boolean) => Promise<void>;
  /** 任务创建时同步到本地状态 */
  syncTaskCreated: (task: TaskInfo) => void;
  /** 任务更新（开始/进度）时同步到本地状态 */
  syncTaskUpdated: (task: TaskInfo) => void;
  /** 任务失败时同步到本地状态 */
  syncTaskFailed: (task: TaskInfo) => void;
  /** 从本地状态移除某个任务 */
  removeTask: (taskId: string) => void;
  /** 每次定时/可见性刷新完成后回调 */
  onDashboardDataRefresh?: () => void;
  /** 某个任务完成后相关数据刷新完毕回调 */
  onCompletedTaskDataRefreshed?: (task: TaskInfo) => void;
  /** 是否启用本 hook，默认 true */
  enabled?: boolean;
};

export function useDashboardLifecycle({
  loadInitialHistory,
  refreshHistory,
  refreshHistoryForCompletedTask,
  refreshActiveTasks,
  loadStockBar,
  refreshStockBar,
  loadMarketReviewHistory,
  refreshMarketReviewHistory,
  syncTaskCreated,
  syncTaskUpdated,
  syncTaskFailed,
  removeTask,
  onDashboardDataRefresh,
  onCompletedTaskDataRefreshed,
  enabled = true,
}: UseDashboardLifecycleOptions): void {
  // 待清理的任务移除定时器 id 列表（组件卸载时统一清除，避免对已卸载组件 setState）
  const removalTimeoutsRef = useRef<number[]>([]);

  // 首次挂载：并行加载各类初始数据
  useEffect(() => {
    if (!enabled) {
      return;
    }

    void loadInitialHistory();
    void loadStockBar();
    void loadMarketReviewHistory?.();
    void refreshActiveTasks();
  }, [enabled, loadInitialHistory, loadMarketReviewHistory, loadStockBar, refreshActiveTasks]);

  // 周期轮询：每 30 秒静默刷新一次全部数据源并触发回调
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refreshHistory(true);
      void refreshStockBar();
      void refreshMarketReviewHistory?.(true);
      void refreshActiveTasks();
      onDashboardDataRefresh?.();
    }, 30_000);

    return () => window.clearInterval(intervalId);
  }, [enabled, onDashboardDataRefresh, refreshHistory, refreshMarketReviewHistory, refreshStockBar, refreshActiveTasks]);

  // 标签页重新可见时立即刷新一次（用户切回前台看到最新数据）
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void refreshHistory(true);
        void refreshStockBar();
        void refreshMarketReviewHistory?.(true);
        void refreshActiveTasks();
        onDashboardDataRefresh?.();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [enabled, onDashboardDataRefresh, refreshHistory, refreshMarketReviewHistory, refreshStockBar, refreshActiveTasks]);

  // 卸载时清除所有挂起的任务移除定时器
  useEffect(() => {
    return () => {
      removalTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
      removalTimeoutsRef.current = [];
    };
  }, []);

  /**
   * 安排一次延迟移除任务：用于任务完成/失败后短暂保留在列表中（便于用户看到终态），再自动清除。
   */
  const scheduleTaskRemoval = (taskId: string, delayMs: number) => {
    const timeoutId = window.setTimeout(() => {
      removeTask(taskId);
      removalTimeoutsRef.current = removalTimeoutsRef.current.filter((item) => item !== timeoutId);
    }, delayMs);

    removalTimeoutsRef.current.push(timeoutId);
  };

  // 订阅实时任务流，把 SSE 事件桥接到本地状态与各类刷新：
  // - 创建/开始/进度 → 同步任务状态
  // - 连接成功 → 立即拉取进行中任务
  // - 完成 → 同步状态 + 刷新历史/行情/大盘复盘 + 短暂保留后移除
  // - 失败 → 同步失败状态 + 更久保留后移除
  useTaskStream({
    onTaskCreated: syncTaskCreated,
    onTaskStarted: syncTaskUpdated,
    onTaskProgress: syncTaskUpdated,
    onConnected: () => {
      void refreshActiveTasks();
    },
    onTaskCompleted: (task) => {
      syncTaskUpdated(task);
      const historyRefresh = refreshHistoryForCompletedTask
        ? refreshHistoryForCompletedTask(task)
        : refreshHistory(true);
      const stockBarRefresh = refreshStockBar();
      // 历史与行情刷新都结束后，通知调用方「相关数据已就绪」
      void Promise.allSettled([historyRefresh, stockBarRefresh]).then(() => {
        onCompletedTaskDataRefreshed?.(task);
      });
      void refreshMarketReviewHistory?.(true);
      // 完成后 2 秒自动从列表移除
      scheduleTaskRemoval(task.taskId, 2_000);
    },
    onTaskFailed: (task) => {
      syncTaskFailed(task);
      // 失败后 5 秒自动移除（失败态保留更久，便于排查）
      scheduleTaskRemoval(task.taskId, 5_000);
    },
    onError: () => {
      console.warn('SSE connection disconnected, reconnecting...');
    },
    enabled,
  });
}

export default useDashboardLifecycle;
