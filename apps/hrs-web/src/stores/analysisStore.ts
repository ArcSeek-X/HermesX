/**
 * 个股分析状态管理 Store
 *
 * 文件用途：
 *   基于 Zustand 的轻量状态管理，负责个股分析页面（Home）的即时分析态与历史报告态切换。
 *   本 Store 只承载"分析/历史"两个视图互斥的状态，不负责监听分析任务进度、历史列表、
 *   任务面板等复杂逻辑（那些在 stockPoolStore 中处理）。
 *
 * 设计要点：
 *   1. 历史报告视图（isHistoryView=true）与分析结果视图（result!=null）互斥，
 *      切换时通过 setResult / setHistoryReport 自动清空对方，避免两种视图重叠显示。
 *   2. 所有状态变更均强制清空 error，保证新视图进入时不被旧错误文案干扰。
 */
import { create } from 'zustand';
import type { ParsedApiError } from '../api/error';
import type { AnalysisResult, AnalysisReport } from '../types/analysis';

/** 个股分析 Store 状态与 Action 定义 */
interface AnalysisState {
  // —— 分析状态（即时分析视图）——
  /** 是否正在请求分析接口 */
  isLoading: boolean;
  /** 最近一次即时分析返回的结果；为 null 表示尚未分析或已切换到历史视图 */
  result: AnalysisResult | null;
  /** 分析过程中出现的统一错误对象；为 null 表示无错误 */
  error: ParsedApiError | null;

  // —— 历史报告视图（查看已生成报告）——
  /** 是否处于"查看历史报告"模式 */
  isHistoryView: boolean;
  /** 当前选中的历史报告；为 null 表示未选中 */
  historyReport: AnalysisReport | null;

  // —— Actions ——
  /** 设置加载态（通常配合外部请求的开始/结束调用） */
  setLoading: (loading: boolean) => void;
  /** 写入分析结果并切回分析视图（清空历史视图与错误） */
  setResult: (result: AnalysisResult | null) => void;
  /** 记录分析错误并停止加载 */
  setError: (error: ParsedApiError | null) => void;
  /** 写入历史报告并切换到历史视图（清空分析结果与错误） */
  setHistoryReport: (report: AnalysisReport | null) => void;
  /** 完全清空所有状态，回到初始空白态 */
  reset: () => void;
  /** 只退出历史视图（保留 result），回到分析视图 */
  resetToAnalysis: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  // 初始状态
  isLoading: false,
  result: null,
  error: null,
  isHistoryView: false,
  historyReport: null,

  // Actions
  /** 仅更新加载态，不影响其它字段 */
  setLoading: (loading) => set({ isLoading: loading }),

  /** 写入分析结果：同步清空错误与历史视图，确保只显示最新分析结果 */
  setResult: (result) =>
    set({
      result,
      error: null,
      isHistoryView: false,
      historyReport: null,
    }),

  /** 记录错误并强制结束加载态 */
  setError: (error) => set({ error, isLoading: false }),

  /** 写入历史报告：进入历史视图，清空分析结果态 */
  setHistoryReport: (report) =>
    set({
      historyReport: report,
      isHistoryView: true,
      result: null,
      error: null,
      isLoading: false,
    }),

  /** 整体重置：回到初始空白态，用于离开分析页或清空上下文 */
  reset: () =>
    set({
      isLoading: false,
      result: null,
      error: null,
      isHistoryView: false,
      historyReport: null,
    }),

  /** 退出历史视图但保留已有分析结果，仅用于视图切换不丢数据 */
  resetToAnalysis: () =>
    set({
      isHistoryView: false,
      historyReport: null,
    }),
}));
