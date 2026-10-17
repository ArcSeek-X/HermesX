/**
 * @file Discover/EodPickerPage/components/EodStockCard.tsx
 * @description 尾盘选股结果屏中的单只股票卡片组件（从 EodPickerPage 抽取，自包含）。
 *   结构自上而下：头部（名称 / 代码 / 涨跌徽章）→ 价格区（现价 / 涨跌额 / 分时强度）
 *   → 缩略走势区（KLineView + 图例）→ 指标网格（流通市值 / 量比 / 换手率 / 成交额）→ 加自选按钮。
 *   整卡点击跳转个股 K 线页；「加自选」按钮经包裹层阻止冒泡，不触发跳转。
 *   文件比页面深一级，相对导入需 ../../../../ 回到 src/。
 */

import { useNavigate } from 'react-router-dom';
import { Check, Plus } from 'lucide-react';
import { AnimCard, HrsButton } from '@components';
import { AVG_PRICE_LINE_COLOR, KLineView } from '@components/kline/KLineView';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR } from '../../../../constants/stockColor';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { EodPickerStock } from '../../../../api/eodPicker';

// ----------------------------- 格式化与展示工具 -----------------------------

/** 数字格式化：统一保留 digits 位小数；无效值返回 '-'（卡片与筛选态共用，故导出）。 */
export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  return v.toFixed(digits);
}

/** 成交额格式化：按数量级自动切换单位（亿 / 万 / 取整）；无效值返回 '-'。 */
function fmtAmount(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)}万`;
  return v.toFixed(0);
}

/** 百分比格式化：带正负号与百分号；无效值返回 '-'。 */
function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
}

/** 涨跌方向色：红涨绿跌（changePct 为 null 时按涨色处理，与 ▲ 徽章一致）。 */
function trendColorOf(changePct: number | null | undefined): string {
  return (changePct ?? 0) >= 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR;
}

/** 指标网格单元：左侧标签 + 右侧数值，浅灰底（对齐参考项目 dataItem 样式）。 */
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-black/[0.03] px-3 py-2 dark:bg-white/[0.04]">
      <span className="text-[11px] text-muted-text">{label}</span>
      <span className="text-xs font-medium">{value}</span>
    </div>
  );
}

// ----------------------------- 股票卡片 -----------------------------

/** 股票卡片 Props */
export type EodStockCardProps = {
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
function EodStockCard({ stock, ordinal, inWatchlist, canAddWatchlist, onAddToWatchlist }: EodStockCardProps) {
  const { t } = useUiLanguage();
  const navigate = useNavigate();

  // 点击卡片跳转个股 K 线页：统一带 ?stockCode= 直达，数据与展示标签由 K 线页自行加载生成
  const openInKline = () => {
    const pureCode = stock.code.split('.')[0].trim();
    navigate(`/stock/kline?stockCode=${encodeURIComponent(pureCode)}`);
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
    { label: t('eodPicker.EodStockCard.circMv'), value: `${fmtNum(stock.circMv)}亿` },
    { label: t('eodPicker.EodStockCard.volumeRatio'), value: fmtNum(stock.volumeRatio) },
    { label: t('eodPicker.EodStockCard.turnoverRate'), value: `${fmtNum(stock.turnoverRate)}%` },
    { label: t('eodPicker.EodStockCard.amount'), value: fmtAmount(stock.amount) },
  ];
  const legendItems = [
    { label: t('eodPicker.EodStockCard.priceLegend'), color: trendColor },
    { label: t('eodPicker.EodStockCard.avgPriceLegend'), color: AVG_PRICE_LINE_COLOR },
  ];

  return (
    <AnimCard
      ordinal={ordinal}
      onClick={openInKline}
      tooltip={t('eodPicker.EodStockCard.openKline')}
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
          <div className="text-xs text-muted-text">{t('eodPicker.EodStockCard.currentPrice')}</div>
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
            {t('eodPicker.EodStockCard.strength')} {stock.strength.toFixed(0)}%
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
            {inWatchlist ? t('eodPicker.EodStockCard.inWatchlist') : t('eodPicker.EodStockCard.addWatchlist')}
          </HrsButton>
        </div>
      )}
    </AnimCard>
  );
}

export default EodStockCard;
