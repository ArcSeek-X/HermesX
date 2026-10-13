/**
 * @file EodPickerPage.tsx
 * @description 尾盘选股页面（EOD Picker）
 *   照搬参考项目 chengzuopeng/stock-dashboard 的「尾盘选股法」界面与功能：
 *   - 开始屏：开始分析 + 可编辑筛选条件（流通市值 / 量比 / 涨幅 / 换手率 / 排除ST / 分时强度）
 *   - 进度遮罩：阶段文案 + 百分比（轮询后端任务）
 *   - 结果屏：数量统计 + 排序按钮组 + 股票卡片网格（含 KLineView 缩略走势图与「加自选」，
 *     点击卡片携带代码跳转个股 K 线页 /stock/kline）
 *   数据来自后端 /api/v1/eod-picker/*（异步任务）。
 *   组件均复用本仓库 components（AnimCard / HrsButton / HrsNumberField / KLineView 等），
 *   不修改现有组件，仅在页面内做组合与薄封装。
 * @module pages
 */

import type React from 'react';
import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap,
  SlidersHorizontal,
  ArrowUpDown,
  Check,
  Plus,
  RotateCcw,
  SearchX,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';
import { AnimCard, HrsButton, HrsNumberField, Modal } from '@components';
import { PageHeader, EmptyState } from '@components/page-layout';
import { AVG_PRICE_LINE_COLOR, KLineView } from '@components/kline/KLineView';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR } from '../../constants/stockColor';
import { setStorageItem } from '../../utils/storage';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import {
  eodPickerApi,
  DEFAULT_FILTERS,
  type EodPickerFilters,
  type EodPickerResult,
  type EodPickerStock,
} from '../../api/eodPicker';
import {
  createWatchlistItem,
  getWatchlistGroups,
  getAllWatchlistItems,
} from '../../api/watchlist';
import { toApiErrorMessage } from '../../api/error';
import {
  loadFilters,
  saveFiltersDebounced,
} from '../../api/eodPickerStorage';

/** 排序字段：分时强度 / 当日涨幅 / 换手率 / 流通市值 / 量比（与下方 sortButtonItems 的 value 对应） */
type SortKey = 'strength' | 'changePct' | 'turnoverRate' | 'circMv' | 'volumeRatio';
/** 页面阶段：start 开始屏（筛选配置）/ running 任务轮询中（进度遮罩）/ result 结果屏（卡片网格） */
type Phase = 'start' | 'running' | 'result';

/** 自选股代码集合拉取：改用 getAllWatchlistItems 自动分页，不再依赖单页大 pageSize（后端上限 100） */

// ----------------------------- 工具函数 -----------------------------
/**
 * 数字格式化：统一保留 digits 位小数。
 * @param v - 待格式化数值，允许 null / undefined / NaN
 * @param digits - 保留小数位数，默认 2
 * @returns 格式化字符串；无效值统一返回 '-'
 */
function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  return v.toFixed(digits);
}

/**
 * 成交额格式化：按数量级自动切换单位。
 * @param v - 成交额（元），允许 null / undefined
 * @returns >=1 亿转「x.xx亿」，>=1 万转「x.xx万」，其余取整；无效值返回 '-'
 */
function fmtAmount(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)}万`;
  return v.toFixed(0);
}

/**
 * 百分比格式化：带正负号与百分号。
 * @param v - 百分比数值（如 3.52 表示 3.52%），允许 null / undefined
 * @returns 形如 '+3.52%' / '-1.20%'；无效值返回 '-'
 */
function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
}

// ----------------------------- 筛选卡（行内编辑，严格对齐参考项目 stock-dashboard 的尺寸 / 字号 / 间距） -----------------------------
/**
 * 筛选卡行容器：左侧标签 + 右侧控件区，浅灰底圆角条。
 * 非编辑态整行可点击（点击回到编辑态）；行内按钮需自行 stopPropagation 防止误触发。
 * @param label - 行标签文案（走 i18n）
 * @param children - 右侧控件区内容（FilterRange / FilterSingle / 开关按钮等）
 */
function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg bg-black/[0.04] px-3 py-3 dark:bg-white/[0.05]">
      <span className="shrink-0 text-xs text-secondary-text">{label}</span>
      <div className="flex items-center gap-1">{children}</div>
    </div>
  );
}

/**
 * 筛选值展示态文本：小字号加粗。
 * @param children - 展示内容
 * @param className - 附加 class，供调用方覆写颜色（如 ST 开关开启时高亮主题色）
 */
function FilterValue({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`text-xs font-medium text-foreground ${className}`}>{children}</span>;
}

/**
 * 区间型筛选（最小 ~ 最大 + 单位）：编辑态渲染两个数字输入框，展示态渲染文本。
 * @param editing - 是否编辑态；false 时展示「最小 ~ 最大（或无上限文案）」
 * @param min - 最小值，null 表示未设置
 * @param max - 最大值，null 表示不设上限（展示态显示 unlimited 文案）
 * @param unit - 单位文案（如「亿」「%」），展示在数值后
 * @param unlimited - 无上限时的占位文案（i18n）
 * @param onMin - 最小值变更回调，入参 null 表示清空
 * @param onMax - 最大值变更回调，入参 null 表示不设上限
 */
function FilterRange({
  editing,
  min,
  max,
  unit,
  unlimited,
  onMin,
  onMax,
}: {
  editing: boolean;
  min: number | null;
  max: number | null;
  unit: string;
  unlimited: string;
  onMin: (v: number | null) => void;
  onMax: (v: number | null) => void;
}) {
  if (!editing) {
    return (
      <FilterValue>
        {fmtNum(min, 0)} ~ {max === null ? unlimited : fmtNum(max, 0)}
        <span className="text-[11px] text-muted-text">{unit}</span>
      </FilterValue>
    );
  }
  return (
    <>
      <HrsNumberField vertical className="w-[80px]" value={min ?? undefined} onChange={(v) => onMin(v ?? null)} />
      <span className="text-xs text-muted-text">~</span>
      <HrsNumberField vertical className="w-[80px]" value={max ?? undefined} onChange={(v) => onMax(v ?? null)} />
      <span className="text-[11px] text-muted-text">{unit}</span>
    </>
  );
}

/**
 * 单值型筛选（≥ 值 + 可选单位）：编辑态渲染数字输入框，展示态渲染「≥ 值」文本。
 * @param editing - 是否编辑态；false 时展示「≥ 值」
 * @param value - 阈值，null 表示未设置
 * @param unit - 单位文案（可选），展示在数值后
 * @param digits - 展示态小数位数，默认 1
 * @param onValue - 阈值变更回调，入参 null 表示清空
 */
function FilterSingle({
  editing,
  value,
  unit,
  digits = 1,
  onValue,
}: {
  editing: boolean;
  value: number | null;
  unit?: string;
  digits?: number;
  onValue: (v: number | null) => void;
}) {
  return (
    <>
      {editing ? (
        <HrsNumberField vertical className="w-[60px]" value={value ?? undefined} onChange={(v) => onValue(v ?? null)} />
      ) : (
        <FilterValue>≥ {fmtNum(value, digits)}</FilterValue>
      )}
      {unit && <span className="text-[11px] text-muted-text">{unit}</span>}
    </>
  );
}

/**
 * 筛选卡：开始屏的可编辑筛选条件面板。
 * 默认进入编辑态；点「完成」收起为展示态（整卡可点击重新进入编辑）。
 * 六个筛选项（流通市值 / 量比 / 当日涨幅 / 换手率 / 排除ST / 分时强度）的变更
 * 经 onChange 合并不再各自 setState，重置经 onReset 回到 DEFAULT_FILTERS。
 * @param filters - 当前筛选条件（由页面层持有并持久化）
 * @param onChange - 筛选字段局部变更回调（接收 patch 合并）
 * @param onReset - 重置为默认筛选条件回调
 */
function FilterCard({
  filters,
  onChange,
  onReset,
}: {
  filters: EodPickerFilters;
  onChange: (patch: Partial<EodPickerFilters>) => void;
  onReset: () => void;
}) {
  const { t } = useUiLanguage();
  const [editing, setEditing] = useState(true);
  const unlimited = t('eodPicker.filters.unlimited');

  return (
    <div
      onClick={() => !editing && setEditing(true)}
      className={`mx-auto w-full max-w-[700px] rounded-xl border bg-[hsl(var(--card))] p-6 transition-colors ${editing ? 'cursor-default border-[hsl(var(--primary))]' : 'cursor-pointer border-subtle hover:border-[hsl(var(--primary)/0.5)]'
        }`}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <SlidersHorizontal className="h-5 w-5" />
          {t('eodPicker.filters.title')}
        </div>
        {editing ? (
          <div className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <HrsButton variant="ghost" size="sm" onClick={() => onReset()}>
              <RotateCcw className="h-3.5 w-3.5" />
              {t('eodPicker.start.resetFilters')}
            </HrsButton>
            <HrsButton variant="primary" size="sm" onClick={() => setEditing(false)}>
              <Check className="h-3.5 w-3.5" />
              {t('eodPicker.filters.done')}
            </HrsButton>
          </div>
        ) : (
          <span className="text-[11px] text-muted-text">{t('eodPicker.start.editFilters')}</span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {/* 流通市值 */}
        <FilterRow label={t('eodPicker.filters.circMv')}>
          <FilterRange
            editing={editing}
            min={filters.circMvMin}
            max={filters.circMvMax}
            unit="亿"
            unlimited={unlimited}
            onMin={(v) => onChange({ circMvMin: v ?? 0 })}
            onMax={(v) => onChange({ circMvMax: v })}
          />
        </FilterRow>

        {/* 量比 */}
        <FilterRow label={t('eodPicker.filters.volumeRatio')}>
          <FilterSingle
            editing={editing}
            value={filters.volumeRatioMin}
            onValue={(v) => onChange({ volumeRatioMin: v ?? 0 })}
          />
        </FilterRow>

        {/* 当日涨幅 */}
        <FilterRow label={t('eodPicker.filters.changePct')}>
          <FilterRange
            editing={editing}
            min={filters.changePctMin}
            max={filters.changePctMax}
            unit="%"
            unlimited={unlimited}
            onMin={(v) => onChange({ changePctMin: v ?? 0 })}
            onMax={(v) => onChange({ changePctMax: v })}
          />
        </FilterRow>

        {/* 换手率 */}
        <FilterRow label={t('eodPicker.filters.turnoverRate')}>
          <FilterRange
            editing={editing}
            min={filters.turnoverRateMin}
            max={filters.turnoverRateMax}
            unit="%"
            unlimited={unlimited}
            onMin={(v) => onChange({ turnoverRateMin: v ?? 0 })}
            onMax={(v) => onChange({ turnoverRateMax: v })}
          />
        </FilterRow>

        {/* 过滤ST股票 */}
        <FilterRow label={t('eodPicker.filters.excludeSt')}>
          {editing ? (
            <span onClick={(e) => e.stopPropagation()}>
              <HrsButton
                variant="ghost"
                size="sm"
                className={filters.excludeSt ? '!text-[hsl(var(--primary))]' : '!text-muted-text'}
                onClick={() => onChange({ excludeSt: !filters.excludeSt })}
              >
                {filters.excludeSt ? (
                  <ToggleRight className="h-[22px] w-[22px]" />
                ) : (
                  <ToggleLeft className="h-[22px] w-[22px]" />
                )}
                {filters.excludeSt ? t('eodPicker.filters.on') : t('eodPicker.filters.off')}
              </HrsButton>
            </span>
          ) : (
            <FilterValue className={filters.excludeSt ? 'text-[hsl(var(--primary))]' : ''}>
              {filters.excludeSt ? t('eodPicker.filters.on') : t('eodPicker.filters.off')}
            </FilterValue>
          )}
        </FilterRow>

        {/* 分时强度 */}
        <FilterRow label={t('eodPicker.filters.strength')}>
          <FilterSingle
            editing={editing}
            value={filters.strengthMin}
            unit="%"
            digits={0}
            onValue={(v) => onChange({ strengthMin: v ?? 0 })}
          />
        </FilterRow>
      </div>
    </div>
  );
}

// ----------------------------- 股票卡片（视觉对齐参考项目 EndOfDayPicker：涨跌徽章 + 价格区 + 缩略走势 + 指标网格 + 加自选） -----------------------------
/** 指标网格单元：左侧标签 + 右侧数值，浅灰底（对齐参考项目 dataItem 样式）。 */
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-black/[0.03] px-3 py-2 dark:bg-white/[0.04]">
      <span className="text-[11px] text-muted-text">{label}</span>
      <span className="text-xs font-medium">{value}</span>
    </div>
  );
}

/** 规范展示代码：'603019' -> '603019.SH' / '000001' -> '000001.SZ' / 北交 -> '.BJ'（与 StockSearch 契约一致）。 */
function buildDisplayCode(code: string): string {
  const pure = code.split('.')[0].trim();
  if (code.includes('.')) return code;
  if (pure.startsWith('6')) return `${pure}.SH`;
  if (/^[489]/.test(pure)) return `${pure}.BJ`;
  return `${pure}.SZ`;
}

/** 涨跌方向色：红涨绿跌（changePct 为 null 时按涨色处理，与 ▲ 徽章一致）。 */
function trendColorOf(changePct: number | null | undefined): string {
  return (changePct ?? 0) >= 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR;
}

/** 股票卡片 Props */
type StockCardProps = {
  /** 单只命中股票的展示数据（含下采样分时 timeline），必填 */
  stock: EodPickerStock;
  /** 网格序号，用于入场动画错位延迟 */
  ordinal: number;
  /** 是否已在默认自选分组中（控制「加自选」按钮态） */
  inWatchlist: boolean;
  /** 是否存在可写入的自选分组；无分组时隐藏「加自选」按钮 */
  canAddWatchlist: boolean;
  /** 点击「加自选」回调，由页面层写入默认分组 */
  onAddToWatchlist: (stock: EodPickerStock) => void;
};

/**
 * 股票卡片：结果屏网格中的单只股票展示单元（视觉对齐参考项目 EndOfDayPicker）。
 * 结构自上而下：头部（名称 / 代码 / 涨跌徽章）→ 价格区（现价 / 涨跌额 / 分时强度）
 * → 缩略走势区（KLineView + 图例）→ 指标网格（流通市值 / 量比 / 换手率 / 成交额）→ 加自选按钮。
 * 整卡点击跳转个股 K 线页；「加自选」按钮经包裹层阻止冒泡，不触发跳转。
 * @param stock - 股票展示数据
 * @param ordinal - 网格序号（入场动画延迟）
 * @param inWatchlist - 是否已在默认自选分组
 * @param canAddWatchlist - 是否存在可写入分组（无分组时隐藏按钮）
 * @param onAddToWatchlist - 加自选回调（页面层写默认分组）
 */
function StockCard({ stock, ordinal, inWatchlist, canAddWatchlist, onAddToWatchlist }: StockCardProps) {
  const { t } = useUiLanguage();
  const navigate = useNavigate();

  // 点击卡片跳转个股 K 线页：写入 sessionStorage 共享键（与 ShellHeader/StockKLinePage 同键），
  // K 线页 useEffect([stockCode]) 监听到代码后自动加载 /info 与 /kline；
  // 展示标签（"名称（规范代码）"）写入 hrs-state-kline.displayValue 供页内搜索框初始化显示。
  const openInKline = () => {
    const pureCode = stock.code.split('.')[0].trim();
    setStorageItem('kline.stockCode', pureCode, 'session');
    try {
      sessionStorage.setItem(
        'hrs-state-kline.displayValue',
        JSON.stringify(`${stock.name}（${buildDisplayCode(stock.code)}）`),
      );
    } catch { /* ignore */ }
    navigate('/stock/kline');
  };

  // 涨跌方向：驱动徽章、涨跌额与走势图例配色（红涨绿跌）
  const isUp = (stock.changePct ?? 0) >= 0;
  const trendColor = trendColorOf(stock.changePct);
  // 涨跌额 = 现价 - 昨收；任一缺失则不展示
  const changeAmount =
    stock.price !== null && stock.prevClose !== null && stock.prevClose > 0
      ? stock.price - stock.prevClose
      : null;
  // 指标网格（顺序即展示顺序）与走势图例（价格线色随涨跌方向，均价线固定橙）
  const metrics = [
    { label: t('eodPicker.card.circMv'), value: `${fmtNum(stock.circMv)}亿` },
    { label: t('eodPicker.card.volumeRatio'), value: fmtNum(stock.volumeRatio) },
    { label: t('eodPicker.card.turnoverRate'), value: `${fmtNum(stock.turnoverRate)}%` },
    { label: t('eodPicker.card.amount'), value: fmtAmount(stock.amount) },
  ];
  const legendItems = [
    { label: t('eodPicker.card.priceLegend'), color: trendColor },
    { label: t('eodPicker.card.avgPriceLegend'), color: AVG_PRICE_LINE_COLOR },
  ];

  return (
    <AnimCard
      ordinal={ordinal}
      onClick={openInKline}
      tooltip={t('eodPicker.card.openKline')}
      className="flex h-full flex-col p-4 transition-transform duration-200 hover:-translate-y-0.5"
    >
      {/* 头部：名称 + 代码 | 涨跌幅徽章（涨跌色浅底胶囊） */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold leading-tight">{stock.name}</div>
          <div className="mt-0.5 text-xs text-muted-text">{stock.code}</div>
        </div>
        <span
          className="flex shrink-0 items-center gap-1 rounded-sm px-2 py-1 text-xs font-semibold"
          style={{ color: trendColor, backgroundColor: `${trendColor}1a` }}
        >
          <span aria-hidden className="text-[9px]">{isUp ? '▲' : '▼'}</span>
          {fmtPct(stock.changePct)}
        </span>
      </div>

      {/* 价格区：现价 + 涨跌额 | 分时强度徽章（左右两列同节奏：标签行与数值行分别水平对齐） */}
      <div className="mt-3 flex items-start justify-between gap-2">
        {/* 左列：现价标签 + 最新价（fmtNum 对缺失值统一兜底为 '-'） */}
        <div>
          {/* 「现价」弱化小标签：说明下方大字号数值为最新成交价 */}
          <div className="text-xs text-muted-text">{t('eodPicker.card.currentPrice')}</div>
          {/* 最新价主视觉：大字号加粗；leading-tight 收敛行高，与右列数值行保持同一水平线 */}
          <div className="mt-1 text-xl font-bold leading-tight">{fmtNum(stock.price)}</div>
        </div>
        {/* 右列：涨跌额 + 分时强度徽章，纵向堆叠与左列两行一一对应 */}
        <div className="flex flex-col items-end">
          {/* 涨跌额 = 现价 - 昨收，颜色随涨跌方向；恒占位（缺失显示 '-'）保证两行结构稳定对齐 */}
          <span className="text-xs font-medium" style={{ color: trendColor }}>
            {changeAmount !== null ? `${isUp ? '+' : ''}${changeAmount.toFixed(2)}` : '-'}
          </span>
          {/* 分时强度徽章：价格站在均价线（VWAP）之上的采样点占比，主题色浅底胶囊 */}
          <span className="mt-1 rounded bg-[hsl(var(--primary)/0.12)] px-2 py-0.5 text-xs font-medium text-[hsl(var(--primary))]">
            {t('eodPicker.result.strength')} {stock.strength.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* 缩略走势区：浅灰底容器 + 图例；图表本体去默认边框/背景融入容器 */}
      <div className="mt-3 rounded-lg bg-black/[0.03] p-2 dark:bg-white/[0.04]">
        <KLineView timeline={stock.timeline} prevClose={stock.prevClose} height={110} className="border-none bg-transparent" />
        <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-text">
          {legendItems.map((item) => (
            <span key={item.label} className="flex items-center gap-1.5">
              <span aria-hidden className="h-[2px] w-4 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      </div>

      {/* 指标网格 */}
      <div className="mt-3 grid grid-cols-2 gap-2">
        {metrics.map((m) => (
          <Metric key={m.label} label={m.label} value={m.value} />
        ))}
      </div>

      {/* 加自选：包裹层阻止冒泡，避免点击触发卡片跳转（HrsButton 的 onClick 桥接 onPress，不可在其中 stopPropagation） */}
      {canAddWatchlist && (
        <div className="mt-3 pt-1" onClick={(e) => e.stopPropagation()}>
          <HrsButton
            variant="outline"
            size="sm"
            className={`w-full ${inWatchlist ? '!text-success bg-success/10' : 'bg-black/[0.03] dark:bg-white/[0.04]'}`}
            isDisabled={inWatchlist}
            onClick={() => onAddToWatchlist(stock)}
          >
            {inWatchlist ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            {inWatchlist ? t('eodPicker.card.inWatchlist') : t('eodPicker.card.addWatchlist')}
          </HrsButton>
        </div>
      )}
    </AnimCard>
  );
}

// ----------------------------- 主页面 -----------------------------
/**
 * 尾盘选股页面（EOD Picker）。
 *
 * 三阶段状态机（phase）：
 * - start：开始屏，展示「开始分析」大按钮 + FilterCard 筛选面板；
 * - running：进度遮罩，轮询后端任务（2s 间隔）刷新阶段文案与百分比；
 * - result：结果屏，统计行 + 排序按钮组 + 股票卡片网格。
 *
 * 筛选条件经 eodPickerStorage 防抖持久化到 localStorage；选股任务为异步模式
 * （POST 提交 -> GET 轮询）；卡片「加自选」写入排序第一个自选分组。
 */
const EodPickerPage: React.FC = () => {
  const { t } = useUiLanguage();

  /** 筛选条件：初始值从 localStorage 恢复，变更后防抖持久化 */
  const [filters, setFilters] = useState<EodPickerFilters>(() => loadFilters());
  /** 当前页面阶段：start / running / result */
  const [phase, setPhase] = useState<Phase>('start');
  /** 轮询中的任务 id；null 表示无进行中任务 */
  const [taskId, setTaskId] = useState<string | null>(null);
  /** 任务进度百分比（0~100） */
  const [progress, setProgress] = useState(0);
  /** 任务阶段文案（后端下发的当前步骤描述） */
  const [message, setMessage] = useState('');
  /** 页面级错误提示（任务失败 / 加自选失败等），展示在顶部横幅 */
  const [error, setError] = useState<string | null>(null);
  /** 选股结果；completed 时由轮询写入，重新分析时清空 */
  const [result, setResult] = useState<EodPickerResult | null>(null);

  /** 排序字段：默认按分时强度 */
  const [sortKey, setSortKey] = useState<SortKey>('strength');
  /** 排序方向：desc 降序（默认）/ asc 升序 */
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  // —— 自选股（卡片「加自选」）——
  /** 默认自选分组 id：结果到达后取排序第一个分类；无任何分类时为 null（隐藏加自选按钮） */
  const [watchlistGroupId, setWatchlistGroupId] = useState<number | null>(null);
  /** 默认分组内已存在的股票代码集合（纯代码），供卡片展示「已自选」 */
  const [watchlistCodes, setWatchlistCodes] = useState<Set<string>>(new Set());

  // 选股结果到达后同步自选股状态：取排序第一个分类作为默认「加自选」目标，
  // 并拉取其股票代码集合。加载失败不阻断结果展示（降级为无分组 / 空集合）。
  useEffect(() => {
    if (!result) return undefined;
    let active = true;
    const loadWatchlistState = async () => {
      try {
        const groups = await getWatchlistGroups();
        if (!active) return;
        const firstGroup =
          groups.length > 0
            ? [...groups].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id)[0]
            : null;
        if (!firstGroup) {
          setWatchlistGroupId(null);
          setWatchlistCodes(new Set());
          return;
        }
        setWatchlistGroupId(firstGroup.id);
        const items = await getAllWatchlistItems(firstGroup.id);
        if (!active) return;
        setWatchlistCodes(new Set(items.map((it) => it.stockCode.split('.')[0])));
      } catch (err) {
        if (!active) return;
        // 自选股状态加载失败不阻断结果展示，但要把真实原因透出给用户（此前静默吞掉导致只报错无说明）
        setWatchlistGroupId(null);
        setWatchlistCodes(new Set());
        setError(toApiErrorMessage(err));
      }
    };
    void loadWatchlistState();
    return () => {
      active = false;
    };
  }, [result]);

  /** 加自选：写入默认分组；后端 409（分组内已存在）按成功处理，同步「已自选」状态 */
  const addToWatchlist = useCallback(
    async (stock: EodPickerStock) => {
      if (watchlistGroupId === null) return;
      const pureCode = stock.code.split('.')[0].trim();
      try {
        await createWatchlistItem(watchlistGroupId, { stockCode: pureCode, stockName: stock.name });
        setWatchlistCodes((prev) => new Set(prev).add(pureCode));
      } catch (err) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (status === 409) {
          setWatchlistCodes((prev) => new Set(prev).add(pureCode));
          return;
        }
        // 透出后端真实错误原因（如股票代码未收录、分类不存在等），不再只显示笼统文案
        setError(toApiErrorMessage(err));
      }
    },
    [watchlistGroupId, t],
  );

  /** 筛选变更：合并 patch 更新 state，并防抖持久化到 localStorage */
  const updateFilter = (patch: Partial<EodPickerFilters>) => {
    const next = { ...filters, ...patch };
    setFilters(next);
    saveFiltersDebounced(next);
  };

  /** 开始分析：清空旧结果与错误，提交异步任务并进入轮询阶段 */
  const start = async () => {
    setError(null);
    setResult(null);
    try {
      const accepted = await eodPickerApi.start(filters);
      setTaskId(accepted.taskId);
      setProgress(0);
      setMessage('');
      setPhase('running');
    } catch (err) {
      // 透出后端真实错误原因（含 422 校验详情等），不再只显示笼统文案
      setError(toApiErrorMessage(err));
    }
  };

  /** 取消任务：丢弃 taskId 回到开始屏（后端任务继续跑完，仅前端停止轮询） */
  const cancel = () => {
    setTaskId(null);
    setPhase('start');
  };

  // 轮询任务进度（递归 setTimeout，绕过 GET 缓存）
  useEffect(() => {
    if (!taskId || phase !== 'running') return undefined;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const task = await eodPickerApi.getTask(taskId);
        if (!active) return;
        setProgress(task.progress ?? 0);
        setMessage(task.message || '');
        if (task.status === 'completed') {
          if (task.result) {
            setResult(task.result);
          }
          setPhase('result');
        } else if (task.status === 'failed') {
          setError(
            `${t('eodPicker.error.failed')}${task.error ? `：${task.error}` : ''}`,
          );
          setPhase('start');
        } else {
          timer = setTimeout(poll, 2000);
        }
      } catch {
        if (!active) return;
        timer = setTimeout(poll, 2000);
      }
    };
    void poll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [taskId, phase, filters, t]);

  /** 排序后的股票列表：按 sortKey 字段 + sortDir 方向排序；缺失值按 -Infinity 沉底 */
  const sortedStocks = useMemo(() => {
    if (!result) return [];
    const arr = [...result.stocks];
    const dir = sortDir === 'asc' ? 1 : -1;
    arr.sort((a, b) => {
      const av = (a[sortKey] as number) ?? -Infinity;
      const bv = (b[sortKey] as number) ?? -Infinity;
      return (av - bv) * dir;
    });
    return arr;
  }, [result, sortKey, sortDir]);

  /** 排序按钮组配置：value 为排序字段（SortKey），label 为按钮文案（i18n） */
  const sortButtonItems = [
    { value: 'strength', label: t('eodPicker.result.sort.strength') },
    { value: 'changePct', label: t('eodPicker.filters.changePct') },
    { value: 'turnoverRate', label: t('eodPicker.filters.turnoverRate') },
    { value: 'circMv', label: t('eodPicker.filters.circMv') },
    { value: 'volumeRatio', label: t('eodPicker.filters.volumeRatio') },
  ] as const;

  return (
    // 页面根容器：全宽 + 垂直间距统一 12px（space-y-3）
    <div className="mx-auto w-full space-y-3">
      {/* 页头：标题 + 描述（复用 page-layout 的 PageHeader） */}
      <PageHeader
        title={t('layout.nav.eodPicker.title')}
        description={t('layout.nav.eodPicker.description')}
      />

      {/* 错误横幅：任务提交失败 / 任务失败 / 加自选失败时展示 */}
      {error && (
        <div className="rounded-lg border border-[hsl(var(--danger)/0.4)] bg-[hsl(var(--danger)/0.08)] px-4 py-2 text-sm text-[hsl(var(--danger))]">
          {error}
        </div>
      )}

      {/* 开始屏：圆形「开始分析」主按钮 + 筛选卡 */}
      {phase === 'start' && (
        <div className="space-y-8 pb-4">
          {/* 圆形「开始分析」按钮（参照参考项目）：自定义样式 CTA，HrsButton 无法呈现故保留原生 button */}
          <div className="flex justify-center pt-8">
            <button
              type="button"
              onClick={start}
              className="flex h-[180px] w-[180px] flex-col items-center justify-center gap-2 rounded-full bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--primary)/0.7)] text-white shadow-[0_8px_32px_hsl(var(--primary)/0.35)] ring-4 ring-[hsl(var(--primary)/0.12)] transition-transform duration-300 hover:scale-105 active:scale-95"
            >
              <Zap className="h-7 w-7" />
              <span className="text-base font-semibold">{t('eodPicker.start.button')}</span>
            </button>
          </div>

          {/* 筛选卡：变更走 updateFilter（合并 + 防抖持久化）；重置回 DEFAULT_FILTERS 并立即持久化 */}
          <FilterCard
            filters={filters}
            onChange={updateFilter}
            onReset={() => {
              setFilters(DEFAULT_FILTERS);
              saveFiltersDebounced(DEFAULT_FILTERS);
            }}
          />
        </div>
      )}

      {/* 结果屏：统计行 + 排序按钮组 + 卡片网格（result 与 phase 同时就绪才渲染） */}
      {phase === 'result' && result && (
        <div className="space-y-3">
          {/* 统计行：左侧为「总扫描 → 候选 → 命中」漏斗与基准交易日，右侧为「重新分析」入口 */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-secondary-text">
              {result.tradeDate && (
                <span className="ml-2 text-xs text-muted-text">
                  {t('eodPicker.result.basis')} {result.tradeDate}：
                </span>
              )}
              <span className="ml-2">
               {t('eodPicker.result.title')}： {result.totalScanned}，
              </span>
              <span className="ml-2">
              {'候选：'} {result.candidateCount}，
              </span>
              <span className="ml-2">
              {'命中：'} {result.matchCount}
              </span>
            </div>
            <HrsButton

              onClick={() => {
                setResult(null);
                setPhase('start');
              }}
            >
              {t('eodPicker.result.reanalyze')}
            </HrsButton>
          </div>

          {/* 排序按钮组：点击切换排序字段，再次点击当前字段切换升降序（方向箭头标注在激活按钮上） */}
          <div role="group" aria-label={t('eodPicker.result.sortBy')} className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-xs text-foreground-soft">
              <ArrowUpDown className="h-4 w-4" />
              {t('eodPicker.result.sortBy')}：
            </span>
            {sortButtonItems.map((item) => {
              // active = 当前排序字段：点击切换升降序；非激活字段：点击切换排序字段（保持当前方向）
              const active = sortKey === item.value;
              return (
                <HrsButton
                  key={item.value}
                  variant={active ? 'primary-soft' : 'outline'}
                  size="sm"
                  className={active ? undefined : 'bg-black/[0.04] dark:bg-white/[0.05]'}
                  onClick={() =>
                    active
                      ? setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      : setSortKey(item.value)
                  }
                >
                  {item.label}
                  {active && <span className="text-xs">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </HrsButton>
              );
            })}
          </div>

          {/* 卡片网格：移动端 1 列 / 平板 2 列 / 桌面 3 列 / 宽屏 4 列（卡片含走势图与指标网格，3 列时单卡宽度更舒展） */}
          {sortedStocks.length === 0 ? (
            <EmptyState
              title={t('eodPicker.result.empty')}
              description={t('eodPicker.result.emptyDesc')}
              icon={<SearchX className="h-10 w-10" />}
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
              {sortedStocks.map((s, i) => (
                <StockCard
                  key={s.code}
                  stock={s}
                  ordinal={i}
                  inWatchlist={watchlistCodes.has(s.code.split('.')[0])}
                  canAddWatchlist={watchlistGroupId !== null}
                  onAddToWatchlist={addToWatchlist}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* 进度遮罩：任务轮询期间以 Modal 呈现（禁用遮罩点击关闭，避免误触中断轮询；关闭入口为内置标题 X 与底部取消） */}
      <Modal
        isOpen={phase === 'running'}
        onClose={cancel}
        size="md"
        variant="blur"
        isDismissable={false}
      >
        <Modal.Header>
          <Modal.Heading>{t('eodPicker.running.title')}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          {/* 进度区：旋转指示器 + 百分比进度条（宽度由 progress 驱动）+ 阶段文案 */}
          <div className="flex flex-col items-center gap-4">
            <div className="h-10 w-10 animate-spin rounded-full border-2 border-[hsl(var(--primary)/0.3)] border-t-[hsl(var(--primary))]" />
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-[hsl(var(--primary))] transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex w-full items-center justify-between text-sm">
              <span className="text-secondary-text">{message || '...'}</span>
              <span className="font-medium">{progress}%</span>
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="secondary" size="md" className="w-full" onClick={cancel}>
            {t('eodPicker.running.cancel')}
          </HrsButton>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default EodPickerPage;
