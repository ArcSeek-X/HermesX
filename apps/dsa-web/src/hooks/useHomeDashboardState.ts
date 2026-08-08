import { useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useStockPoolStore } from '../stores';

/**
 * useHomeDashboardState —— 首页（HomePage）仪表盘状态选择器。
 *
 * 设计意图：
 * - 业务状态（历史记录、进行中任务、行情条、各类加载/错误态、动作方法）统一由 useStockPoolStore 持有，
 *   首页组件只关心「展示」，不重复维护状态。
 * - 本 hook 作为「状态选择层」：用 useShallow 从 store 中一次性挑选首页渲染所需的字段与方法，
 *   并以浅比较避免对象引用变化导致的无谓重渲染。
 * - 额外派生两个 Set（selectedIds / selectedMarketReviewHistoryIds），方便在列表渲染中 O(1) 判重。
 *
 * 这样既保持了现有的视觉契约，又让 HomePage 组件更聚焦于本地 UI 编排。
 */
export function useHomeDashboardState() {
  const dashboardState = useStockPoolStore(
    // useShallow：对返回的字段集合做浅比较，仅当其中任一字段变化时才触发组件更新
    useShallow((state) => ({
      // ===== 输入与错误态 =====
      query: state.query,
      inputError: state.inputError,
      duplicateError: state.duplicateError,
      error: state.error,
      isAnalyzing: state.isAnalyzing,

      // ===== 分析历史（普通） =====
      historyItems: state.historyItems,
      selectedHistoryIds: state.selectedHistoryIds,
      isDeletingHistory: state.isDeletingHistory,
      isLoadingHistory: state.isLoadingHistory,
      isLoadingMore: state.isLoadingMore,
      hasMore: state.hasMore,

      // ===== 大盘复盘历史 =====
      marketReviewHistoryItems: state.marketReviewHistoryItems,
      selectedMarketReviewHistoryIds: state.selectedMarketReviewHistoryIds,
      isLoadingMarketReviewHistory: state.isLoadingMarketReviewHistory,
      isLoadingMoreMarketReviewHistory: state.isLoadingMoreMarketReviewHistory,
      isDeletingMarketReviewHistory: state.isDeletingMarketReviewHistory,
      marketReviewHistoryHasMore: state.marketReviewHistoryHasMore,

      // ===== 报告与详情抽屉 =====
      selectedReport: state.selectedReport,
      isLoadingReport: state.isLoadingReport,
      isHistoryTrendOpen: state.isHistoryTrendOpen,
      markdownDrawerOpen: state.markdownDrawerOpen,

      // ===== 个股历史/行情条 =====
      stockHistoryItems: state.stockHistoryItems,
      stockHistoryTotal: state.stockHistoryTotal,
      stockHistoryHasMore: state.stockHistoryHasMore,
      isLoadingStockHistory: state.isLoadingStockHistory,
      isLoadingMoreStockHistory: state.isLoadingMoreStockHistory,
      stockHistoryError: state.stockHistoryError,
      stockHistoryFilters: state.stockHistoryFilters,
      activeTasks: state.activeTasks,
      notify: state.notify,

      // ===== 动作方法 =====
      setQuery: state.setQuery,
      setNotify: state.setNotify,
      clearError: state.clearError,
      loadInitialHistory: state.loadInitialHistory,
      refreshHistory: state.refreshHistory,
      refreshHistoryForCompletedTask: state.refreshHistoryForCompletedTask,
      loadMoreHistory: state.loadMoreHistory,
      loadMarketReviewHistory: state.loadMarketReviewHistory,
      refreshMarketReviewHistory: state.refreshMarketReviewHistory,
      loadMoreMarketReviewHistory: state.loadMoreMarketReviewHistory,
      selectHistoryItem: state.selectHistoryItem,
      toggleHistorySelection: state.toggleHistorySelection,
      toggleSelectAllVisible: state.toggleSelectAllVisible,
      deleteSelectedHistory: state.deleteSelectedHistory,
      toggleMarketReviewHistorySelection: state.toggleMarketReviewHistorySelection,
      toggleSelectAllVisibleMarketReviewHistory: state.toggleSelectAllVisibleMarketReviewHistory,
      deleteSelectedMarketReviewHistory: state.deleteSelectedMarketReviewHistory,
      submitAnalysis: state.submitAnalysis,
      syncTaskCreated: state.syncTaskCreated,
      syncTaskUpdated: state.syncTaskUpdated,
      syncTaskFailed: state.syncTaskFailed,
      refreshActiveTasks: state.refreshActiveTasks,
      removeTask: state.removeTask,
      openMarkdownDrawer: state.openMarkdownDrawer,
      closeMarkdownDrawer: state.closeMarkdownDrawer,
      openHistoryTrend: state.openHistoryTrend,
      closeHistoryTrend: state.closeHistoryTrend,
      setStockHistoryRange: state.setStockHistoryRange,
      loadMoreStockHistory: state.loadMoreStockHistory,
      stockBarItems: state.stockBarItems,
      isLoadingStockBar: state.isLoadingStockBar,
      stockBarRefreshFailed: state.stockBarRefreshFailed,
      loadStockBar: state.loadStockBar,
      refreshStockBar: state.refreshStockBar,
    })),
  );

  // 历史选中 id 的 Set 视图：供列表项快速判断「是否被选中」（O(1) 判重）
  const selectedIds = useMemo(
    () => new Set(dashboardState.selectedHistoryIds),
    [dashboardState.selectedHistoryIds],
  );
  // 大盘复盘历史选中 id 的 Set 视图
  const selectedMarketReviewHistoryIds = useMemo(
    () => new Set(dashboardState.selectedMarketReviewHistoryIds),
    [dashboardState.selectedMarketReviewHistoryIds],
  );

  // 把派生出的 Set 与原始状态一并返回，调用方既能拿到全部字段，也能直接用 Set 做集合判断
  return {
    ...dashboardState,
    selectedIds,
    selectedMarketReviewHistoryIds,
  };
}

export default useHomeDashboardState;
