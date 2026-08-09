/**
 * @file BacktestPage.tsx
 * @description 回测页面，提供策略回测功能。支持按股票代码、评估窗口天数、
 *              市场阶段、分析日期范围筛选回测结果，展示整体和个股绩效指标，
 *              以及详细的回测结果表格。
 * @module pages
 */
import type React from 'react';
import { useState, useEffect, useCallback } from 'react';
import { Check, Minus, X } from 'lucide-react';
import { backtestApi } from '../api/backtest';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { ApiErrorAlert, Card, Badge, EmptyState, Pagination, StatusDot, Tooltip } from '../components/common';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { formatUiText, type UiLanguage } from '../i18n/uiText';
import {
  BACKTEST_DIRECTION_EXPECTED_LABELS,
  BACKTEST_MOVEMENT_LABELS,
  BACKTEST_OUTCOME_LABELS,
  BACKTEST_PHASE_FILTER_OPTIONS,
  BACKTEST_PHASE_LABELS,
  BACKTEST_STATUS_LABELS,
  BACKTEST_TEXT,
} from '../locales/featureText';
import type {
  BacktestResultItem,
  BacktestRunResponse,
  PerformanceMetrics,
  BacktestPhaseFilter,
} from '../types/backtest';
import { buildDecisionActionLabelMap, getDecisionActionLabel } from '../utils/decisionAction';
import { getMarketPhaseSummaryLabel } from '../utils/marketPhase';
import { usePreference } from '../hooks/usePreference';

/** 回测页面标准输入框样式类名 */
const BACKTEST_INPUT_CLASS =
  'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';
/** 回测页面紧凑型输入框样式类名（用于日期、天数等较短输入） */
const BACKTEST_COMPACT_INPUT_CLASS =
  'input-surface input-focus-glow h-10 rounded-xl border bg-transparent px-3 py-2 text-xs transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';
/** 回测页面多语言文本类型别名 */
type BacktestText = (typeof BACKTEST_TEXT)[UiLanguage];

// ============ Helpers ============

/**
 * 将数值格式化为百分比字符串
 * @param value - 数值（可为 null/undefined）
 * @returns 格式化后的百分比字符串，如 "12.3%"；值为空时返回 "--"
 */
function pct(value?: number | null): string {
  if (value == null) return '--';
  return `${value.toFixed(1)}%`;
}

/**
 * 获取回测结果行的市场阶段标签
 * 优先使用 marketPhaseSummary 的摘要标签，其次回退到 marketPhase 枚举值
 * @param row - 回测结果行数据
 * @param language - 当前 UI 语言
 * @returns 市场阶段标签文本
 */
function phaseLabel(row: BacktestResultItem, language: UiLanguage): string {
  const label = getMarketPhaseSummaryLabel(row.marketPhaseSummary, language);
  if (label) {
    // 移除标签前缀，仅保留阶段名称
    return label
      .replace('市场阶段: ', '')
      .replace('市场阶段：', '')
      .replace('Market phase: ', '');
  }
  return (row.marketPhase ? BACKTEST_PHASE_LABELS[language][row.marketPhase] : undefined) || row.marketPhase || '--';
}

/**
 * 标准化股票代码输入：去除首尾空格并转为大写
 * @param value - 用户输入的股票代码
 * @returns 标准化后的代码字符串；输入为空时返回 undefined
 */
function normalizeBacktestCode(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  return trimmed.toUpperCase();
}

/**
 * 解析评估窗口天数输入
 * @param value - 用户输入的天数字符串
 * @returns 解析后的正整数；输入为空或无效时返回 undefined
 */
function parseEvalWindowDays(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }

  const parsed = parseInt(trimmed, 10);
  if (Number.isNaN(parsed) || parsed < 1) {
    return undefined;
  }

  return parsed;
}

/**
 * 根据值从标签映射中获取显示文本
 * @param value - 原始值
 * @param labels - 标签映射表
 * @returns 映射后的标签文本；值为空时返回 "--"
 */
function labelFromMap(value: string | null | undefined, labels: Record<string, string>): string {
  if (!value) return '--';
  return labels[value] ?? value;
}

/**
 * 渲染回测结果（win/loss/neutral）的徽章组件
 * @param outcome - 回测结果类型
 * @param language - 当前 UI 语言
 * @returns 对应颜色的 Badge 组件
 */
function outcomeBadge(outcome: string | undefined, language: UiLanguage) {
  const labels = BACKTEST_OUTCOME_LABELS[language];
  if (!outcome) return <Badge variant="default">--</Badge>;
  switch (outcome) {
    case 'win':
      return <Badge variant="success" glow>{labels.win}</Badge>;
    case 'loss':
      return <Badge variant="danger" glow>{labels.loss}</Badge>;
    case 'neutral':
      return <Badge variant="warning">{labels.neutral}</Badge>;
    default:
      return <Badge variant="default">{outcome}</Badge>;
  }
}

/**
 * 渲染回测评估状态（completed/insufficient/error）的徽章组件
 * @param status - 评估状态字符串
 * @param language - 当前 UI 语言
 * @returns 对应颜色的 Badge 组件
 */
function statusBadge(status: string, language: UiLanguage) {
  const labels = BACKTEST_STATUS_LABELS[language];
  switch (status) {
    case 'completed':
      return <Badge variant="success">{labels.completed}</Badge>;
    case 'insufficient':
    case 'insufficient_data':
      return <Badge variant="warning">{labels.insufficient}</Badge>;
    case 'error':
      return <Badge variant="danger">{labels.error}</Badge>;
    default:
      return <Badge variant="default">{status}</Badge>;
  }
}

/**
 * 渲染实际涨跌方向（up/down/flat）的徽章组件
 * @param movement - 涨跌方向字符串
 * @param language - 当前 UI 语言
 * @returns 对应颜色的 Badge 组件
 */
function actualMovementBadge(movement: string | null | undefined, language: UiLanguage) {
  const labels = BACKTEST_MOVEMENT_LABELS[language];
  switch (movement) {
    case 'up':
      return <Badge variant="success">{labels.up}</Badge>;
    case 'down':
      return <Badge variant="danger">{labels.down}</Badge>;
    case 'flat':
      return <Badge variant="warning">{labels.flat}</Badge>;
    default:
      return <Badge variant="default">--</Badge>;
  }
}

/**
 * 渲染布尔值的图标组件（是/否/未知）
 * @param value - 布尔值（可为 null/undefined 表示未知）
 * @param text - 多语言文本对象
 * @returns 带状态点的图标 span 元素
 */
function boolIcon(value: boolean | null | undefined, text: BacktestText) {
  if (value === true) {
    return (
      <span
        className="backtest-status-chip backtest-status-chip-success"
        aria-label={text.yes}
      >
        <StatusDot tone="success" className="backtest-status-chip-dot" />
        <Check className="h-3.5 w-3.5" />
      </span>
    );
  }

  if (value === false) {
    return (
      <span
        className="backtest-status-chip backtest-status-chip-danger"
        aria-label={text.no}
      >
        <StatusDot tone="danger" className="backtest-status-chip-dot" />
        <X className="h-3.5 w-3.5" />
      </span>
    );
  }

  return (
    <span
      className="backtest-status-chip backtest-status-chip-neutral"
      aria-label={text.unknown}
    >
      <StatusDot tone="neutral" className="backtest-status-chip-dot" />
      <Minus className="h-3.5 w-3.5" />
    </span>
  );
}

// ============ Metric Row ============

/**
 * 绩效指标行组件：展示单个指标标签和数值
 * @param label - 指标标签
 * @param value - 指标数值文本
 * @param accent - 是否使用高亮样式
 */
const MetricRow: React.FC<{ label: string; value: string; accent?: boolean }> = ({ label, value, accent }) => (
  <div className="backtest-metric-row">
    <span className="label">{label}</span>
    <span className={`value ${accent ? 'accent' : ''}`}>{value}</span>
  </div>
);

/**
 * 生成市场阶段分布文本
 * 从绩效指标的 diagnostics.phaseBreakdown 中提取各阶段数量并拼接为可读文本
 * @param metrics - 绩效指标数据
 * @param language - 当前 UI 语言
 * @returns 阶段分布文本；无数据时返回 null
 */
function phaseBreakdownText(metrics: PerformanceMetrics, language: UiLanguage): string | null {
  const breakdown = metrics.diagnostics?.phaseBreakdown;
  if (!breakdown || typeof breakdown !== 'object') return null;
  const item = breakdown as Record<string, unknown>;
  const phaseLabels = BACKTEST_PHASE_LABELS[language];
  // 按盘前/盘中/盘后/未知顺序拼接各阶段数量
  const parts = [
    [phaseLabels.premarket, item.premarket],
    [phaseLabels.intraday, item.intraday],
    [phaseLabels.postmarket, item.postmarket],
    [phaseLabels.unknown, item.unknown],
  ]
    .map(([label, value]) => `${label} ${Number(value || 0)}`)
    .join(' / ');
  return parts;
}

// ============ Performance Card ============

/**
 * 绩效卡片组件：展示方向准确率、胜率、平均收益等绩效指标
 * @param metrics - 绩效指标数据
 * @param title - 卡片标题
 * @param language - 当前 UI 语言
 */
const PerformanceCard: React.FC<{ metrics: PerformanceMetrics; title: string; language: UiLanguage }> = ({ metrics, title, language }) => {
  const text = BACKTEST_TEXT[language];
  const phaseText = phaseBreakdownText(metrics, language);
  return (
    <Card variant="gradient" padding="md" className="animate-fade-in">
      {/* 卡片标题 */}
      <div className="mb-3">
        <span className="label-uppercase">{title}</span>
      </div>
      {/* 核心绩效指标行 */}
      <MetricRow label={text.directionAccuracy} value={pct(metrics.directionAccuracyPct)} accent />
      <MetricRow label={text.winRate} value={pct(metrics.winRatePct)} accent />
      <MetricRow label={text.avgSimulatedReturn} value={pct(metrics.avgSimulatedReturnPct)} />
      <MetricRow label={text.avgStockReturn} value={pct(metrics.avgStockReturnPct)} />
      <MetricRow label={text.stopLossTriggerRate} value={pct(metrics.stopLossTriggerRate)} />
      <MetricRow label={text.takeProfitTriggerRate} value={pct(metrics.takeProfitTriggerRate)} />
      <MetricRow label={text.avgDaysToFirstHit} value={metrics.avgDaysToFirstHit != null ? metrics.avgDaysToFirstHit.toFixed(1) : '--'} />
      {/* 评估数量统计 */}
      <div className="backtest-metric-footer">
        <span className="text-xs text-muted-text">{text.evaluationCount}</span>
        <span className="text-xs text-secondary-text font-mono">
          {Number(metrics.completedCount)} / {Number(metrics.totalEvaluations)}
        </span>
      </div>
      {/* 盈/亏/中性结果汇总 */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-text">{text.outcomeSummary}</span>
        <span className="text-xs font-mono">
          <span className="text-success">{metrics.winCount}</span>
          {' / '}
          <span className="text-danger">{metrics.lossCount}</span>
          {' / '}
          <span className="text-warning">{metrics.neutralCount}</span>
        </span>
      </div>
      {/* 市场阶段分布（如有诊断数据） */}
      {phaseText ? (
        <div className="mt-3 border-t border-white/10 pt-2 text-xs text-muted-text">
          {formatUiText(text.phaseDistribution, { text: phaseText })}
        </div>
      ) : null}
    </Card>
  );
};

// ============ Run Summary ============

/**
 * 运行结果摘要组件：展示回测运行后的处理数量、保存数量、完成数量等汇总信息
 * @param data - 回测运行响应数据
 * @param language - 当前 UI 语言
 */
const RunSummary: React.FC<{ data: BacktestRunResponse; language: UiLanguage }> = ({ data, language }) => {
  const text = BACKTEST_TEXT[language];
  return (
  <div className="backtest-summary animate-fade-in">
    <span className="label">{text.processed} <span className="value">{data.processed}</span></span>
    <span className="label">{text.saved} <span className="value primary">{data.saved}</span></span>
    <span className="label">{text.completed} <span className="value success">{data.completed}</span></span>
    <span className="label">{text.insufficient} <span className="value warning">{data.insufficient}</span></span>
    {data.errors > 0 && (
      <span className="label">{text.errors} <span className="value danger">{data.errors}</span></span>
    )}
    {data.message && (
      <span className="label message">{data.message}</span>
    )}
  </div>
  );
};

// ============ 主页面 ============

/**
 * 回测主页面组件
 *
 * 职责：
 * - 提供筛选条件输入区（股票代码、评估窗口、市场阶段、日期范围）
 * - 触发回测任务并展示运行摘要
 * - 展示整体绩效卡片和个股绩效卡片
 * - 分页展示回测结果明细表格
 *
 * 数据流：
 * 1. 初始化时拉取最新整体绩效，用其 evalWindowDays 过滤结果
 * 2. 用户点击"运行回测"后，刷新结果列表和绩效指标
 * 3. 用户点击"筛选"按条件重新拉取结果和绩效
 * 4. 用户点击"单日验证"切换为 evalWindowDays=1 的次日验证模式
 */
const BacktestPage: React.FC = () => {
  // 当前 UI 语言及通用翻译函数（来自全局语言上下文）
  const { language, t } = useUiLanguage();
  // 当前语言对应的回测页面多语言文本
  const text = BACKTEST_TEXT[language];
  // 市场阶段筛选下拉选项列表
  const phaseFilterOptions = BACKTEST_PHASE_FILTER_OPTIONS[language];
  // 决策操作建议标签映射（用于表格中展示 AI 预测的操作建议文案）
  const actionLabels = buildDecisionActionLabelMap(t);

  // 设置页面标题
  useEffect(() => {
    document.title = text.documentTitle;
  }, [text.documentTitle]);

  // ===== 输入状态 =====
  // 股票代码筛选输入（非持久化，每次进入页面为空）
  const [codeFilter, setCodeFilter] = useState('');
  // L4 缓存：回测参数偏好（localStorage 永久保存）
  const [analysisDateFrom, setAnalysisDateFrom] = usePreference<string>('backtest-date-from', '');
  const [analysisDateTo, setAnalysisDateTo] = usePreference<string>('backtest-date-to', '');
  const [phaseFilter, setPhaseFilter] = usePreference<BacktestPhaseFilter>('backtest-phase-filter', 'all');
  const [evalDays, setEvalDays] = usePreference<string>('backtest-eval-days', '');
  const [forceRerun, setForceRerun] = usePreference<boolean>('backtest-force-rerun', false);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<BacktestRunResponse | null>(null);
  const [runError, setRunError] = useState<ParsedApiError | null>(null);
  const [pageError, setPageError] = useState<ParsedApiError | null>(null);

  // ===== 结果列表状态 =====
  const [results, setResults] = useState<BacktestResultItem[]>([]); // 当前页回测结果列表
  const [totalResults, setTotalResults] = useState(0); // 结果总数（用于分页计算）
  const [currentPage, setCurrentPage] = useState(1); // 当前页码
  const [isLoadingResults, setIsLoadingResults] = useState(false); // 结果列表加载态
  const pageSize = 20; // 每页结果条数

  // ===== 绩效指标状态 =====
  const [overallPerf, setOverallPerf] = useState<PerformanceMetrics | null>(null); // 整体绩效指标
  const [stockPerf, setStockPerf] = useState<PerformanceMetrics | null>(null); // 个股绩效指标（有代码筛选时才加载）
  const [isLoadingPerf, setIsLoadingPerf] = useState(false); // 绩效指标加载态
  // 实际生效的评估窗口天数：优先取用户输入，其次回退到整体绩效摘要中的值
  const effectiveWindowDays = parseEvalWindowDays(evalDays) ?? overallPerf?.evalWindowDays;
  // 是否为单日（次日）验证模式：评估窗口为 1 天时启用
  const isNextDayValidation = effectiveWindowDays === 1;
  // 单日验证模式下展示次日实际表现列
  const showNextDayActualColumns = isNextDayValidation;

  // 拉取回测结果列表（分页）
  // 按股票代码、评估窗口、日期范围、市场阶段过滤，并更新当前页码与总数
  const fetchResults = useCallback(async (
    page = 1,
    code?: string,
    windowDays?: number,
    startDate?: string,
    endDate?: string,
    phase?: BacktestPhaseFilter,
  ) => {
    setIsLoadingResults(true);
    try {
      const response = await backtestApi.getResults({
        code: code || undefined,
        evalWindowDays: windowDays,
        analysisDateFrom: startDate || undefined,
        analysisDateTo: endDate || undefined,
        analysisPhase: phase && phase !== 'all' ? phase : undefined,
        page,
        limit: pageSize,
      });
      setResults(response.items);
      setTotalResults(response.total);
      setCurrentPage(response.page);
      setPageError(null);
    } catch (err) {
      console.error('Failed to fetch backtest results:', err);
      setPageError(getParsedApiError(err));
    } finally {
      setIsLoadingResults(false);
    }
  }, []);

  // 拉取绩效指标：先取整体绩效，若指定了股票代码则额外取个股绩效
  const fetchPerformance = useCallback(async (
    code?: string,
    windowDays?: number,
    startDate?: string,
    endDate?: string,
    phase?: BacktestPhaseFilter,
  ) => {
    setIsLoadingPerf(true);
    try {
      const overall = await backtestApi.getOverallPerformance({
        evalWindowDays: windowDays,
        analysisDateFrom: startDate || undefined,
        analysisDateTo: endDate || undefined,
        analysisPhase: phase && phase !== 'all' ? phase : undefined,
      });
      setOverallPerf(overall);

      if (code) {
        const stock = await backtestApi.getStockPerformance(code, {
          evalWindowDays: windowDays,
          analysisDateFrom: startDate || undefined,
          analysisDateTo: endDate || undefined,
          analysisPhase: phase && phase !== 'all' ? phase : undefined,
        });
        setStockPerf(stock);
      } else {
        setStockPerf(null);
      }
      setPageError(null);
    } catch (err) {
      console.error('Failed to fetch performance:', err);
      setPageError(getParsedApiError(err));
    } finally {
      setIsLoadingPerf(false);
    }
  }, []);

  // 初始化加载：先拉取最新整体绩效（不带过滤条件，返回最近一次摘要），
  // 再用摘要中的 evalWindowDays 同步到筛选条件，保持结果与绩效口径一致
  useEffect(() => {
    const init = async () => {
      // 获取最新绩效摘要（不带过滤条件返回最近一次的汇总）
      const overall = await backtestApi.getOverallPerformance();
      setOverallPerf(overall);
      // 用摘要中的评估窗口天数同步筛选条件，确保结果列表与绩效口径一致
      const windowDays = overall?.evalWindowDays;
      if (windowDays && !evalDays) {
        setEvalDays(String(windowDays));
      }
      fetchResults(1, undefined, windowDays, undefined, undefined, 'all');
    };
    init();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * 执行回测任务
   * 收集当前筛选条件（股票代码、评估窗口、日期范围、强制重跑），
   * 调用后端 run 接口触发回测，完成后用返回的实际评估窗口天数
   * 同步筛选条件，并刷新结果列表和绩效指标
   */
  const handleRun = async () => {
    setIsRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      // 标准化输入参数：代码转大写、解析评估窗口天数、处理空日期
      const code = normalizeBacktestCode(codeFilter);
      const requestedEvalWindowDays = parseEvalWindowDays(evalDays);
      const dateFrom = analysisDateFrom || undefined;
      const dateTo = analysisDateTo || undefined;
      // 调用后端执行回测（forceRerun 时 minAgeDays 设为 0，跳过最小天数限制）
      const response = await backtestApi.run({
        code,
        force: forceRerun || undefined,
        minAgeDays: forceRerun ? 0 : undefined,
        evalWindowDays: requestedEvalWindowDays,
        analysisDateFrom: dateFrom,
        analysisDateTo: dateTo,
      });
      setRunResult(response);
      // 确定实际生效的评估窗口天数：优先取后端返回值，其次用户输入，最后回退到整体绩效摘要
      const effectiveEvalWindowDays =
        response.appliedEvalWindowDays
        ?? requestedEvalWindowDays
        ?? parseEvalWindowDays(evalDays)
        ?? overallPerf?.evalWindowDays;
      if (effectiveEvalWindowDays != null) {
        setEvalDays(String(effectiveEvalWindowDays));
      }
      // 用实际评估窗口天数刷新结果列表和绩效指标，保持口径一致
      fetchResults(1, code, effectiveEvalWindowDays, dateFrom, dateTo, phaseFilter);
      fetchPerformance(code, effectiveEvalWindowDays, dateFrom, dateTo, phaseFilter);
    } catch (err) {
      setRunError(getParsedApiError(err));
    } finally {
      setIsRunning(false);
    }
  };

  /**
   * 按筛选条件查询结果
   * 根据当前输入的股票代码、评估窗口、日期范围、市场阶段，
   * 重新拉取结果列表（回到第 1 页）和绩效指标
   */
  const handleFilter = () => {
    const code = normalizeBacktestCode(codeFilter);
    const windowDays = parseEvalWindowDays(evalDays);
    setCurrentPage(1);
    fetchResults(1, code, windowDays, analysisDateFrom, analysisDateTo, phaseFilter);
    fetchPerformance(code, windowDays, analysisDateFrom, analysisDateTo, phaseFilter);
  };

  /** 键盘事件处理：在输入框中按 Enter 键时触发筛选查询 */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleFilter();
    }
  };

  /**
   * 切换为单日（次日）验证模式
   * 将评估窗口天数设为 1，重新拉取结果和绩效指标，
   * 用于验证 AI 预测与次日实际涨跌的一致性
   */
  const handleShowNextDay = () => {
    const code = normalizeBacktestCode(codeFilter);
    setEvalDays('1');
    setCurrentPage(1);
    fetchResults(1, code, 1, analysisDateFrom, analysisDateTo, phaseFilter);
    fetchPerformance(code, 1, analysisDateFrom, analysisDateTo, phaseFilter);
  };

  // ===== 分页 =====
  // 总页数 = 向上取整(结果总数 / 每页条数)
  const totalPages = Math.ceil(totalResults / pageSize);

  /** 翻页处理：根据目标页码重新拉取对应页的结果列表 */
  const handlePageChange = (page: number) => {
    const windowDays = parseEvalWindowDays(evalDays);
    fetchResults(page, normalizeBacktestCode(codeFilter), windowDays, analysisDateFrom, analysisDateTo, phaseFilter);
  };

  return (
    <div className="min-h-full flex flex-col rounded-[1.5rem] bg-transparent">
      {/* ===== 页面顶部：筛选条件工具栏 ===== */}
      <header className="flex-shrink-0 border-b border-white/5 px-3 py-3 sm:px-4">
        {/* 筛选控件行：股票代码、评估窗口、市场阶段、日期范围、模式开关、运行按钮 */}
        <div className="flex max-w-5xl flex-wrap items-center gap-2">
          {/* 股票代码筛选输入框：输入代码后按 Enter 触发筛选 */}
          <div className="relative min-w-0 flex-[1_1_220px]">
            <input
              type="text"
              value={codeFilter}
              onChange={(e) => setCodeFilter(e.target.value.toUpperCase())}
              onKeyDown={handleKeyDown}
              placeholder={text.codePlaceholder}
              disabled={isRunning}
              className={BACKTEST_INPUT_CLASS}
            />
          </div>
          {/* 筛选按钮：按当前条件重新拉取结果列表和绩效指标 */}
          <button
            type="button"
            onClick={handleFilter}
            disabled={isLoadingResults}
            className="btn-secondary flex items-center gap-1.5 whitespace-nowrap"
          >
            {text.filter}
          </button>
          {/* 评估窗口天数输入：设置回测评估的时间窗口（1~120 天） */}
          <div className="flex items-center gap-2 whitespace-nowrap lg:w-40 lg:justify-between">
            <span className="text-xs text-muted-text">{text.evalWindow}</span>
            <input
              type="number"
              min={1}
              max={120}
              value={evalDays}
              onChange={(e) => setEvalDays(e.target.value)}
              placeholder="10"
              disabled={isRunning}
              className={`${BACKTEST_COMPACT_INPUT_CLASS} w-24 text-center tabular-nums`}
            />
          </div>
          {/* 市场阶段筛选：按盘前/盘中/盘后阶段过滤回测结果 */}
          <div className="flex items-center gap-2 whitespace-nowrap">
            <span className="text-xs text-muted-text">{text.phase}</span>
            <select
              value={phaseFilter}
              onChange={(e) => setPhaseFilter(e.target.value as BacktestPhaseFilter)}
              disabled={isRunning}
              className={`${BACKTEST_COMPACT_INPUT_CLASS} w-28`}
            >
              {phaseFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
          {/* 分析日期范围 - 起始日期 */}
          <div className="flex items-center gap-2 whitespace-nowrap">
            <span className="text-xs text-muted-text">{text.startDate}</span>
            <input
              type="date"
              aria-label={text.startDateAria}
              value={analysisDateFrom}
              onChange={(e) => setAnalysisDateFrom(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isRunning}
              className={`${BACKTEST_COMPACT_INPUT_CLASS} w-40 text-center tabular-nums`}
            />
          </div>
          {/* 分析日期范围 - 结束日期 */}
          <div className="flex items-center gap-2 whitespace-nowrap">
            <span className="text-xs text-muted-text">{text.endDate}</span>
            <input
              type="date"
              aria-label={text.endDateAria}
              value={analysisDateTo}
              onChange={(e) => setAnalysisDateTo(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isRunning}
              className={`${BACKTEST_COMPACT_INPUT_CLASS} w-40 text-center tabular-nums`}
            />
          </div>
          {/* 单日验证模式开关：将评估窗口设为 1 天，验证次日实际涨跌 */}
          <button
            type="button"
            onClick={handleShowNextDay}
            disabled={isLoadingResults || isLoadingPerf}
            className={`backtest-force-btn ${isNextDayValidation ? 'active' : ''}`}
          >
            <span className="dot" />
            {text.oneDayValidation}
          </button>
          {/* 强制重跑开关：开启后跳过最小天数限制，强制重新执行回测 */}
          <button
            type="button"
            onClick={() => setForceRerun(!forceRerun)}
            disabled={isRunning}
            className={`backtest-force-btn ${forceRerun ? 'active' : ''}`}
          >
            <span className="dot" />
            {text.forceRerun}
          </button>
          {/* 运行回测按钮：触发后端执行回测任务，运行中显示加载动画 */}
          <button
            type="button"
            onClick={handleRun}
            disabled={isRunning}
            className="btn-primary flex items-center gap-1.5 whitespace-nowrap"
          >
            {isRunning ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {text.running}
              </>
            ) : (
              text.runBacktest
            )}
          </button>
        </div>
        {/* 回测运行结果摘要（仅运行后展示） */}
        {runResult && (
          <div className="mt-2 max-w-4xl">
            <RunSummary data={runResult} language={language} />
          </div>
        )}
        {/* 回测运行错误提示（仅运行失败时展示） */}
        {runError && (
          <ApiErrorAlert error={runError} className="mt-2 max-w-4xl" />
        )}
        {/* 当前模式说明文案：单日验证模式 / 多日窗口模式 */}
        <p className="mt-2 text-xs text-muted-text">
          {isNextDayValidation
            ? text.oneDayModeDescription
            : text.windowModeDescription}
        </p>
      </header>

      {/* ===== 页面主体：左侧绩效卡片 + 右侧结果表格 ===== */}
      <main className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden p-3 lg:flex-row">
        {/* 左侧栏：整体绩效卡片 + 个股绩效卡片 */}
        <div className="flex max-h-[38vh] flex-col gap-3 overflow-y-auto lg:max-h-none lg:w-60 lg:flex-shrink-0">
          {isLoadingPerf ? (
            <div className="flex items-center justify-center py-8">
              <div className="backtest-spinner sm" />
            </div>
          ) : overallPerf ? (
            <PerformanceCard metrics={overallPerf} title={text.overallPerformance} language={language} />
          ) : (
            <EmptyState
              title={text.noMetricsTitle}
              description={text.noMetricsDescription}
              className="h-full min-h-[12rem] border-dashed bg-card/45 shadow-none"
            />
          )}

          {stockPerf && (
            <PerformanceCard metrics={stockPerf} title={`${stockPerf.code || codeFilter}`} language={language} />
          )}
        </div>

        {/* 右侧内容区：回测结果明细表格 */}
        <section className="min-h-0 flex-1 overflow-y-auto">
          {/* 页面级错误提示（拉取结果/绩效失败时展示） */}
          {pageError ? (
            <ApiErrorAlert error={pageError} className="mb-3" />
          ) : null}
          {/* 加载中状态 */}
          {isLoadingResults ? (
            <div className="flex flex-col items-center justify-center h-64">
              <div className="backtest-spinner md" />
              <p className="mt-3 text-secondary-text text-sm">{text.loadingResults}</p>
            </div>
          ) : /* 空结果状态 */ results.length === 0 ? (
            <EmptyState
              title={text.noResultsTitle}
              description={text.noResultsDescription}
              className="backtest-empty-state border-dashed"
              icon={(
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              )}
            />
          ) : /* 结果表格区域 */ (
            <div className="animate-fade-in">
              {/* 表格工具栏：结果集标题 + 当前筛选条件摘要 + 滚动提示 */}
              <div className="backtest-table-toolbar">
                <div className="backtest-table-toolbar-meta">
                  <span className="label-uppercase">{isNextDayValidation ? text.nextDayValidation : text.resultSet}</span>
                  <span className="text-xs text-secondary-text">
                    {codeFilter.trim() ? formatUiText(text.filteredStock, { code: codeFilter.trim() }) : text.allStocks}
                    {evalDays ? ` · ${formatUiText(text.dayWindow, { days: evalDays })}` : ''}
                    {phaseFilter !== 'all' ? ` · ${phaseFilterOptions.find((item) => item.value === phaseFilter)?.label ?? phaseFilter}` : ''}
                    {analysisDateFrom ? ` · ${formatUiText(text.fromDate, { date: analysisDateFrom })}` : ''}
                    {analysisDateTo ? ` · ${formatUiText(text.toDate, { date: analysisDateTo })}` : ''}
                  </span>
                </div>
                <span className="backtest-table-scroll-hint">{text.scrollHint}</span>
              </div>
              <div className="backtest-table-wrapper">
                <table className="backtest-table min-w-[900px] w-full text-sm">
                  <thead className="backtest-table-head">
                    <tr className="text-left">
                      <th className="backtest-table-head-cell">{text.stock}</th>
                      <th className="backtest-table-head-cell">{text.analysisDate}</th>
                      <th className="backtest-table-head-cell">{text.phase}</th>
                      <th className="backtest-table-head-cell">{text.aiPrediction}</th>
                      <th className="backtest-table-head-cell">
                        {showNextDayActualColumns ? text.actualPerformance : text.windowReturn}
                      </th>
                      <th className="backtest-table-head-cell">
                        {showNextDayActualColumns ? text.accuracy : text.directionMatch}
                      </th>
                      <th className="backtest-table-head-cell">{text.result}</th>
                      <th className="backtest-table-head-cell">{text.status}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* 遍历回测结果行，渲染每行数据 */}
                    {results.map((row) => {
                      // 获取 AI 预测的操作建议标签
                      const actionLabel = getDecisionActionLabel(row.action, row.actionLabel, null, null, actionLabels);
                      // 拼接预测信息：操作建议 + 趋势预测 + 操作建议文本（过滤空值）
                      const predictionParts = [actionLabel, row.trendPrediction, row.operationAdvice]
                        .filter((part): part is string => Boolean(part));

                      return (
                        <tr
                          key={row.analysisHistoryId}
                          className="backtest-table-row"
                        >
                          <td className="backtest-table-cell backtest-table-code">
                            <div className="flex flex-col">
                              <span>{row.code}</span>
                              <span className="text-xs text-muted-text">{row.stockName || '--'}</span>
                            </div>
                          </td>
                          <td className="backtest-table-cell text-secondary-text">{row.analysisDate || '--'}</td>
                          <td className="backtest-table-cell text-secondary-text">{phaseLabel(row, language)}</td>
                          <td className="backtest-table-cell max-w-[220px] text-foreground">
                            {predictionParts.length ? (
                              <Tooltip
                                content={predictionParts.join(' / ')}
                                focusable
                              >
                                <div className="flex flex-col gap-1">
                                  <span className="block truncate">{actionLabel || row.trendPrediction || '--'}</span>
                                  {actionLabel && row.trendPrediction && (
                                    <span className="block truncate text-xs text-secondary-text">{row.trendPrediction}</span>
                                  )}
                                  {row.operationAdvice && (
                                    <span className="block truncate text-xs text-secondary-text">{row.operationAdvice}</span>
                                  )}
                                </div>
                              </Tooltip>
                            ) : (
                              '--'
                            )}
                          </td>
                          <td className="backtest-table-cell">
                            <div className="flex items-center gap-2">
                              {actualMovementBadge(row.actualMovement, language)}
                              <span className={
                                row.actualReturnPct != null
                                  ? row.actualReturnPct > 0 ? 'text-success' : row.actualReturnPct < 0 ? 'text-danger' : 'text-secondary-text'
                                  : 'text-muted-text'
                              }>
                                {pct(row.actualReturnPct)}
                              </span>
                            </div>
                          </td>
                          <td className="backtest-table-cell">
                            <span className="flex items-center gap-2">
                              {boolIcon(row.directionCorrect, text)}
                              <span className="text-muted-text">
                                {row.directionExpected ? labelFromMap(row.directionExpected, BACKTEST_DIRECTION_EXPECTED_LABELS[language]) : ''}
                              </span>
                            </span>
                          </td>
                          <td className="backtest-table-cell">{outcomeBadge(row.outcome, language)}</td>
                          <td className="backtest-table-cell">{statusBadge(row.evalStatus, language)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="mt-4">
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              </div>

              <p className="text-xs text-muted-text text-center mt-2">
                {formatUiText(text.totalPage, { total: totalResults, page: currentPage, pages: Math.max(totalPages, 1) })}
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default BacktestPage;
