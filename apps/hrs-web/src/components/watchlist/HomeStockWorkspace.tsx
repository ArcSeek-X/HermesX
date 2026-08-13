/**
 * @file HomeStockWorkspace.tsx
 * @description 首页股票工作区组件，提供「历史 / 自选股 / 今日分析」三个 TAB 的统一入口。
 *
 * 核心功能：
 * - 历史 TAB：复用 StockBar 组件展示历史分析记录列表，支持选中与删除。
 * - 自选股 TAB：展示自选股列表，支持添加 / 移除 / 刷新 / 批量分析（全部 / 仅待分析），
 *   并展示当日覆盖率、待分析数量等统计信息。
 * - 今日 TAB：展示当天已完成的分析记录列表，并提供自选股覆盖率与最高评分概览。
 *
 * 主要依赖：
 * - React hooks：useState（草稿输入）、useMemo（状态样式计算）
 * - lucide-react：图标库
 * - common 组件：Badge / Button / Input / ScrollArea / StatusDot
 * - dashboard 组件：DashboardPanelHeader / DashboardStateBlock
 * - history 组件：StockBar
 * - i18n：useUiLanguage 提供多语言文案
 * - 工具函数：formatDateTime / truncateStockName / getSentimentColor / decisionAction
 */
import type React from 'react';
import { useMemo, useState } from 'react';
import {
  ArrowDownWideNarrow,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Loader2,
  Play,
  Plus,
  Star,
  Trash2,
} from 'lucide-react';
import { Badge, Button, Input, ScrollArea, StatusDot } from '../';
import { DashboardPanelHeader, DashboardStateBlock } from '../dashboard';
import { StockBar } from '../history';
import type { StockBarItem, TaskInfo } from '../../types/analysis';
import { getSentimentColor } from '../../types/analysis';
import { buildDecisionActionLabelMap, getDecisionActionLabel } from '../../utils/decisionAction';
import { formatDateTime } from '../../utils/format';
import { truncateStockName } from '../../utils/stockName';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey, UiTextParams } from '../../i18n/uiText';

/** 首页工作区 TAB 类型：'watchlist'=自选股 | 'today'=今日分析 | 'history'=历史记录 */
export type HomeWorkspaceTab = 'watchlist' | 'today' | 'history';

/** 自选股批量分析模式：'all'=分析全部 | 'pending'=仅分析当日未分析的 */
export type WatchlistAnalyzeMode = 'all' | 'pending';

/**
 * 自选股行数据结构，用于自选股 TAB 中的每一行展示。
 */
export interface HomeWatchlistRow {
  /** 股票代码，如 600519 / hk00700 / AAPL */
  code: string;
  /** 最新一条分析记录（来自历史列表），可能不存在 */
  latestItem?: StockBarItem;
  /** 当日是否已分析 */
  analyzedToday: boolean;
  /** 当日分析状态是否正在加载中 */
  isTodayStatusLoading?: boolean;
  /** 当日分析状态是否获取失败（未知） */
  isTodayStatusUnknown?: boolean;
  /** 当前正在执行的异步任务信息（如批量分析），无任务时为 undefined */
  activeTask?: TaskInfo;
}

/**
 * 批量分析状态展示信息。
 */
interface BatchStatus {
  /** 状态样式变体：success=成功 | warning=警告 | danger=危险 */
  variant: 'success' | 'warning' | 'danger';
  /** 展示给用户的状态消息文案 */
  message: string;
}

/**
 * HomeStockWorkspace 组件的 Props 接口，由父组件传入数据与回调。
 */
interface HomeStockWorkspaceProps {
  /** 当前激活的 TAB */
  activeTab: HomeWorkspaceTab;
  /** 切换 TAB 的回调 */
  onTabChange: (tab: HomeWorkspaceTab) => void;
  /** 自选股行数据列表 */
  watchlistRows: HomeWatchlistRow[];
  /** 自选股列表是否正在加载 */
  watchlistLoading: boolean;
  /** 自选股操作（添加/移除/刷新）是否正在进行中，用于禁用按钮 */
  watchlistActioning: boolean;
  /** 自选股操作相关的提示消息（如添加成功/失败） */
  watchlistMessage: string | null;
  /** 添加股票到自选股列表 */
  onAddToWatchlist: (code: string) => Promise<void>;
  /** 从自选股列表移除股票 */
  onRemoveFromWatchlist: (code: string) => Promise<void>;
  /** 刷新自选股列表 */
  onRefreshWatchlist: () => Promise<void>;
  /** 触发批量分析，mode 指定分析全部或仅待分析 */
  onAnalyzeWatchlist: (mode: WatchlistAnalyzeMode) => Promise<void>;
  /** 是否正在进行批量分析 */
  isBatchAnalyzing: boolean;
  /** 批量分析结果状态，null 表示无状态需展示 */
  batchStatus: BatchStatus | null;
  /** 今日已完成的分析记录列表 */
  todayItems: StockBarItem[];
  /** 今日分析列表是否正在加载 */
  isLoadingTodayItems: boolean;
  /** 今日分析列表加载是否出错 */
  todayLoadError: boolean;
  /** 自选股中当日已分析的数量（用于覆盖率统计） */
  watchlistAnalyzedTodayCount: number;
  /** 历史分析记录列表 */
  historyItems: StockBarItem[];
  /** 历史列表是否正在加载 */
  isLoadingHistory: boolean;
  /** 当前选中的股票代码（历史 TAB 高亮用） */
  selectedStockCode?: string;
  /** 当前选中的记录 ID（历史 TAB 高亮用） */
  selectedRecordId?: number;
  /** 点击历史记录项的回调 */
  onHistoryItemClick: (recordId: number) => void;
  /** 删除股票记录的回调（历史 TAB） */
  onDeleteStock?: (stockCode: string) => Promise<void> | void;
  /** 是否正在删除股票记录 */
  isDeleting?: boolean;
  /** 自定义 className */
  className?: string;
}

/**
 * 根据任务状态返回对应的国际化标签文案。
 *
 * @param task - 任务信息对象，为 undefined 时返回空字符串
 * @param t - 国际化翻译函数
 * @returns 任务状态的展示文案；无法识别的状态直接返回原始 status 字符串
 */
function getTaskStatusLabel(task: TaskInfo | undefined, t: (key: UiTextKey, params?: UiTextParams) => string) {
  if (!task) return '';
  if (task.status === 'processing') return t('taskPanel.processing');
  if (task.status === 'pending') return t('taskPanel.pending');
  if (task.status === 'cancel_requested') return t('taskPanel.cancelRequested');
  return task.status;
}

/**
 * 评分徽章组件。
 * 根据分析记录的情感评分（sentimentScore）和操作建议（action）渲染带颜色的徽章。
 * 无评分数据时展示「暂无数据」文案。
 *
 * @param item - 分析记录，包含评分、操作建议等字段
 */
const ScoreBadge: React.FC<{ item?: StockBarItem }> = ({ item }) => {
  const { t } = useUiLanguage();
  // 提取情感评分，非数字类型视为无数据
  const score = typeof item?.sentimentScore === 'number' ? item.sentimentScore : null;
  // 根据评分获取对应颜色
  const color = score !== null ? getSentimentColor(score) : null;
  // 无评分或无颜色时展示「暂无数据」
  if (score === null || !color) {
    return <span className="text-[11px] text-muted-text">{t('common.noData')}</span>;
  }

  // 构建操作建议标签映射表，用于将 action 枚举值转换为可读文案
  const actionLabels = buildDecisionActionLabelMap(t);
  // 获取操作建议的展示文案（优先使用 actionLabel，其次 operationAdvice，最后回退到默认情感标签）
  const operationLabel = getDecisionActionLabel(
    item?.action,
    item?.actionLabel,
    item?.operationAdvice,
    t('history.sentiment'),
    actionLabels,
  );

  return (
    <Badge
      variant="default"
      size="sm"
      className="shrink-0 shadow-none text-[11px] font-semibold leading-none"
      style={{
        // 文字颜色使用评分对应颜色
        color,
        // 边框颜色为评分颜色的 19% 透明度
        borderColor: `${color}30`,
        // 背景颜色为评分颜色的 6% 透明度
        backgroundColor: `${color}10`,
      }}
    >
      {operationLabel} {score}
    </Badge>
  );
};

/**
 * 自选股行项组件。
 * 展示单只自选股的信息：股票名称、代码、当日分析状态图标、最近分析时间、
 * 评分徽章、移除按钮，以及正在执行的任务状态。
 *
 * @param row - 自选股行数据
 * @param onRemove - 移除自选股的回调
 * @param disabled - 是否禁用操作按钮（如批量操作进行中时）
 */
const WatchlistRowItem: React.FC<{
  row: HomeWatchlistRow;
  onRemove: (code: string) => Promise<void>;
  disabled: boolean;
}> = ({ row, onRemove, disabled }) => {
  const { t } = useUiLanguage();
  // 获取当前任务状态的展示文案
  const taskLabel = getTaskStatusLabel(row.activeTask, t);
  // 获取最新分析记录
  const item = row.latestItem;
  // 股票名称：优先使用分析记录中的名称，回退到代码
  const stockName = item?.stockName || row.code;

  return (
    <div className="home-subpanel grid min-w-0 gap-2 px-3 py-2.5">
      {/* 顶部：股票信息 + 操作区 */}
      <div className="flex min-w-0 items-start justify-between gap-2">
        {/* 左侧：股票名称、状态图标、代码、分析时间 */}
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2">
            {/* 股票名称（截断处理） */}
            <span className="truncate text-sm font-semibold text-foreground">
              {truncateStockName(stockName)}
            </span>
            {/* 当日分析状态图标：加载中 -> 未知 -> 已分析 -> 未分析 */}
            {row.isTodayStatusLoading ? (
              <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-text" aria-label={t('watchlist.todayStatusLoading')} />
            ) : row.isTodayStatusUnknown ? (
              <CircleAlert className="h-3.5 w-3.5 shrink-0 text-warning" aria-label={t('watchlist.todayStatusUnavailable')} />
            ) : row.analyzedToday ? (
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" aria-label={t('watchlist.analyzedToday')} />
            ) : (
              <Clock3 className="h-3.5 w-3.5 shrink-0 text-muted-text" aria-label={t('watchlist.notAnalyzedToday')} />
            )}
          </div>
          {/* 股票代码 + 最近分析时间 */}
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-secondary-text">{row.code}</span>
            {item?.lastAnalysisTime ? (
              <>
                <span className="h-1 w-1 rounded-full bg-subtle-hover" />
                <span className="text-[11px] text-muted-text">{formatDateTime(item.lastAnalysisTime)}</span>
              </>
            ) : null}
          </div>
        </div>
        {/* 右侧：评分徽章 + 移除按钮 */}
        <div className="flex shrink-0 items-center gap-1.5">
          <ScoreBadge item={item} />
          <Button
            type="button"
            variant="ghost"
            size="xsm"
            className="h-7 w-7 px-0"
            disabled={disabled}
            aria-label={t('watchlist.removeAria', { code: row.code })}
            onClick={() => void onRemove(row.code)}
          >
            <Trash2 className="h-3.5 w-3.5 text-danger" aria-hidden="true" />
          </Button>
        </div>
      </div>
      {/* 底部：正在执行的任务状态（如有） */}
      {row.activeTask ? (
        <div className="flex min-w-0 items-center gap-2 text-[11px] text-muted-text">
          <StatusDot
            // 处理中状态使用蓝色脉冲点，其他状态使用灰色静态点
            tone={row.activeTask.status === 'processing' ? 'info' : 'neutral'}
            pulse={row.activeTask.status === 'processing'}
            className="h-1.5 w-1.5"
          />
          <span className="truncate">{t('watchlist.taskRunning', { status: taskLabel })}</span>
        </div>
      ) : null}
    </div>
  );
};

/**
 * 今日分析项组件。
 * 以按钮形式展示一条今日已完成的分析记录，点击后跳转到对应记录详情。
 *
 * @param item - 今日分析记录
 * @param onClick - 点击记录项的回调，传入记录 ID
 */
const TodayItem: React.FC<{ item: StockBarItem; onClick: (recordId: number) => void }> = ({ item, onClick }) => {
  // 股票名称：优先使用分析记录中的名称，回退到代码
  const stockName = item.stockName || item.stockCode;

  return (
    <button
      type="button"
      className="home-subpanel grid w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2 px-3 py-2.5 text-left"
      onClick={() => onClick(item.id)}
    >
      {/* 左侧：股票名称 + 代码 */}
      <div className="min-w-0">
        <span className="block truncate text-sm font-semibold text-foreground">
          {truncateStockName(stockName)}
        </span>
        <span className="mt-1 block truncate font-mono text-[11px] text-secondary-text">
          {item.stockCode}
        </span>
      </div>
      {/* 右侧：评分徽章 */}
      <ScoreBadge item={item} />
    </button>
  );
};

/**
 * 首页股票工作区主组件。
 *
 * 该组件是首页侧边栏的核心区域，提供三个 TAB：
 * - 历史（history）：复用 StockBar 展示历史分析记录，支持选中与删除
 * - 自选股（watchlist）：展示自选股列表，支持增删改查与批量分析
 * - 今日（today）：展示当日已完成的分析记录
 *
 * 历史 TAB 采用独立布局（不使用 glass-card 容器），
 * 自选股与今日 TAB 共享同一容器结构（头部统计 + 滚动列表 + 底部操作）。
 */
export const HomeStockWorkspace: React.FC<HomeStockWorkspaceProps> = ({
  activeTab,
  onTabChange,
  watchlistRows,
  watchlistLoading,
  watchlistActioning,
  watchlistMessage,
  onAddToWatchlist,
  onRemoveFromWatchlist,
  onRefreshWatchlist,
  onAnalyzeWatchlist,
  isBatchAnalyzing,
  batchStatus,
  todayItems,
  isLoadingTodayItems,
  todayLoadError,
  watchlistAnalyzedTodayCount,
  historyItems,
  isLoadingHistory,
  selectedStockCode,
  selectedRecordId,
  onHistoryItemClick,
  onDeleteStock,
  isDeleting = false,
  className = '',
}) => {
  const { t } = useUiLanguage();
  /** 添加自选股输入框的草稿值 */
  const [draftCode, setDraftCode] = useState('');
  /** 待分析的自选股数量：排除已分析、加载中、状态未知的行 */
  const pendingWatchlistCount = watchlistRows
    .filter((row) => !row.analyzedToday && !row.isTodayStatusLoading && !row.isTodayStatusUnknown)
    .length;
  /** 是否存在当日状态不可用的自选股（加载中或未知），用于禁用「仅分析待分析」按钮 */
  const isTodayStatusUnavailable = watchlistRows.some((row) => row.isTodayStatusLoading || row.isTodayStatusUnknown);
  /** 今日分析列表中评分最高的一条记录（列表已按评分排序，取第一项） */
  const topTodayItem = todayItems[0];
  /** TAB 配置：历史 / 自选股 / 今日 */
  const tabs: Array<{ key: HomeWorkspaceTab; label: string }> = [
    { key: 'history', label: t('watchlist.tabHistory') },
    { key: 'watchlist', label: t('watchlist.tabWatchlist') },
    { key: 'today', label: t('watchlist.tabToday') },
  ];

  /** 根据 batchStatus 的 variant 计算对应的样式类名（边框/背景/文字颜色） */
  const statusClassName = useMemo(() => {
    if (!batchStatus) return '';
    if (batchStatus.variant === 'danger') return 'border-danger/30 bg-danger/10 text-danger';
    if (batchStatus.variant === 'warning') return 'border-warning/30 bg-warning/10 text-warning';
    return 'border-success/30 bg-success/10 text-success';
  }, [batchStatus]);

  /** 添加自选股表单提交处理：去除首尾空格后调用 onAddToWatchlist，成功后清空输入框 */
  const handleAddSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const code = draftCode.trim();
    if (!code) return;
    void onAddToWatchlist(code).then(() => setDraftCode(''));
  };

  {/* TAB 页签区域：三等分布局，选中项高亮 */}
  const renderTabs = (
    <div className="grid grid-cols-3 gap-1 rounded-xl border border-subtle bg-base/40 p-1">
      {tabs.map((tab) => {
        const selected = activeTab === tab.key;
        return (
          <button
            key={tab.key}
            type="button"
            aria-pressed={selected}
            className={`h-8 rounded-lg px-2 text-xs font-medium transition-colors ${
              selected ? 'bg-primary/15 text-primary shadow-inner' : 'text-secondary-text hover:bg-hover hover:text-foreground'
            }`}
            onClick={() => onTabChange(tab.key)}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );

  // 历史 TAB：直接复用 StockBar 组件，采用独立布局（不使用 glass-card 容器）
  if (activeTab === 'history') {
    return (
      <div className={`flex min-h-0 flex-1 flex-col gap-2 ${className}`}>
        {renderTabs}
        <StockBar
          items={historyItems}
          isLoading={isLoadingHistory}
          selectedStockCode={selectedStockCode}
          selectedRecordId={selectedRecordId}
          onItemClick={onHistoryItemClick}
          onDeleteStock={onDeleteStock}
          isDeleting={isDeleting}
          className="flex-1 overflow-hidden"
        />
      </div>
    );
  }

  return (
    <aside className={`glass-card flex min-h-0 flex-1 flex-col overflow-hidden ${className}`}>
      {/* 头部区域：TAB 页签 + 统计信息 + 操作按钮 */}
      <div className="space-y-3 border-b border-subtle px-4 py-4">
        {renderTabs}

        {activeTab === 'watchlist' ? (
          <>
            {/* 自选股面板标题 */}
            <DashboardPanelHeader
              className="mb-0"
              title={t('watchlist.title')}
              titleClassName="text-sm font-medium"
              leading={<Star className="h-4 w-4 text-primary" aria-hidden="true" />}
              actions={<span className="text-[11px] text-muted-text">{t('common.itemsCount', { count: watchlistRows.length })}</span>}
            />
            {/* 统计卡片：当日覆盖率 + 待分析数量 */}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-subtle bg-base/35 px-3 py-2">
                <p className="text-[11px] text-muted-text">{t('watchlist.todayCoverage')}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{watchlistAnalyzedTodayCount}/{watchlistRows.length}</p>
              </div>
              <div className="rounded-xl border border-subtle bg-base/35 px-3 py-2">
                <p className="text-[11px] text-muted-text">{t('watchlist.pendingToday')}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{pendingWatchlistCount}</p>
              </div>
            </div>
            {/* 批量分析按钮：分析全部 + 仅分析待分析 */}
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                size="sm"
                variant="home-action-ai"
                className="whitespace-nowrap px-2 text-xs"
                disabled={watchlistRows.length === 0 || isBatchAnalyzing}
                isLoading={isBatchAnalyzing}
                loadingText={t('watchlist.submitting')}
                onClick={() => void onAnalyzeWatchlist('all')}
              >
                <Play className="h-4 w-4" aria-hidden="true" />
                {t('watchlist.analyzeAll')}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="home-action-report"
                className="whitespace-nowrap px-2 text-xs"
                disabled={pendingWatchlistCount === 0 || isTodayStatusUnavailable || isBatchAnalyzing}
                onClick={() => void onAnalyzeWatchlist('pending')}
              >
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                {t('watchlist.analyzePending')}
              </Button>
            </div>
            {/* 添加自选股表单：输入框 + 提交按钮 */}
            <form className="grid grid-cols-[minmax(0,1fr)_auto] gap-2" onSubmit={handleAddSubmit}>
              <Input
                value={draftCode}
                onChange={(event) => setDraftCode(event.target.value)}
                placeholder={t('watchlist.addPlaceholder')}
                className="h-9 rounded-lg px-3 text-xs"
                disabled={watchlistActioning}
                aria-label={t('watchlist.addPlaceholder')}
              />
              <Button
                type="submit"
                size="sm"
                variant="secondary"
                className="h-9 w-9 px-0"
                disabled={!draftCode.trim() || watchlistActioning}
                isLoading={watchlistActioning}
                aria-label={t('watchlist.add')}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
              </Button>
            </form>
            {/* 批量分析结果状态提示 */}
            {batchStatus ? (
              <div className={`rounded-xl border px-3 py-2 text-xs ${statusClassName}`}>
                {batchStatus.message}
              </div>
            ) : null}
            {/* 自选股操作提示消息（如添加/移除结果） */}
            {watchlistMessage ? (
              <div className="rounded-xl border border-subtle bg-base/35 px-3 py-2 text-xs text-secondary-text">
                {watchlistMessage}
              </div>
            ) : null}
          </>
        ) : (
          <>
            {/* 今日分析面板标题 */}
            <DashboardPanelHeader
              className="mb-0"
              title={t('watchlist.todayTitle')}
              titleClassName="text-sm font-medium"
              leading={<CalendarDays className="h-4 w-4 text-cyan" aria-hidden="true" />}
              actions={<span className="text-[11px] text-muted-text">{t('common.itemsCount', { count: todayItems.length })}</span>}
            />
            {/* 统计卡片：自选股覆盖率 + 最高评分 */}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-subtle bg-base/35 px-3 py-2">
                <p className="text-[11px] text-muted-text">{t('watchlist.watchlistCoverage')}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{watchlistAnalyzedTodayCount}/{watchlistRows.length}</p>
              </div>
              <div className="rounded-xl border border-subtle bg-base/35 px-3 py-2">
                <p className="text-[11px] text-muted-text">{t('watchlist.topScore')}</p>
                <p className="mt-1 truncate text-sm font-semibold text-foreground">
                  {topTodayItem?.sentimentScore ?? '-'}
                </p>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 滚动列表区域：根据 TAB 渲染自选股列表或今日分析列表 */}
      <ScrollArea viewportClassName="p-4" className="min-h-0 flex-1">
        {activeTab === 'watchlist' ? (
          // 自选股列表：加载中 -> 空列表 -> 正常列表
          watchlistLoading ? (
            <DashboardStateBlock loading compact title={t('watchlist.loading')} />
          ) : watchlistRows.length === 0 ? (
            <DashboardStateBlock
              compact
              title={t('watchlist.emptyTitle')}
              description={t('watchlist.emptyDescription')}
            />
          ) : (
            <div className="space-y-2">
              {/* 列表排序提示 */}
              <div className="flex items-center gap-2 text-[11px] text-muted-text">
                <ArrowDownWideNarrow className="h-3.5 w-3.5" aria-hidden="true" />
                {t('watchlist.listHint')}
              </div>
              {/* 自选股列表 */}
              {watchlistRows.map((row) => (
                <WatchlistRowItem
                  key={row.code}
                  row={row}
                  onRemove={onRemoveFromWatchlist}
                  disabled={watchlistActioning}
                />
              ))}
            </div>
          )
        ) : (
          // 今日分析列表：加载中 -> 加载出错 -> 空列表 -> 正常列表
          isLoadingTodayItems ? (
            <DashboardStateBlock loading compact title={t('watchlist.loading')} />
          ) : todayLoadError ? (
            <DashboardStateBlock
              compact
              title={t('watchlist.todayLoadErrorTitle')}
              description={t('watchlist.todayLoadErrorDescription')}
            />
          ) : todayItems.length === 0 ? (
            <DashboardStateBlock
              compact
              title={t('watchlist.todayEmptyTitle')}
              description={t('watchlist.todayEmptyDescription')}
            />
          ) : (
            <div className="space-y-2">
              {/* 列表排序提示 */}
              <div className="flex items-center gap-2 text-[11px] text-muted-text">
                <ArrowDownWideNarrow className="h-3.5 w-3.5" aria-hidden="true" />
                {t('watchlist.todaySortHint')}
              </div>
              {/* 今日分析列表 */}
              {todayItems.map((item) => (
                <TodayItem key={`${item.stockCode}-${item.id}`} item={item} onClick={onHistoryItemClick} />
              ))}
            </div>
          )
        )}
      </ScrollArea>

      {/* 底部区域：自选股 TAB 显示刷新按钮 */}
      {activeTab === 'watchlist' ? (
        <div className="border-t border-subtle px-4 py-3">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="w-full"
            disabled={watchlistLoading}
            onClick={() => void onRefreshWatchlist()}
          >
            {t('watchlist.refresh')}
          </Button>
        </div>
      ) : null}
    </aside>
  );
};

export default HomeStockWorkspace;
