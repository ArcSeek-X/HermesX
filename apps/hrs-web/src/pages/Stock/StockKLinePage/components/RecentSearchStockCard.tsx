/**
 * 个股 K 线页「最近搜索」单卡：行情头 + 价格 + 迷你分时 + 指标网格。
 * 占位态字段全空且不可点击，避免列表加载时空白闪烁。
 */

import { memo } from 'react';
import { Plus } from 'lucide-react';
import { AnimCard, HrsButton } from '@components';
import { AVG_PRICE_LINE_COLOR, KLineView } from '@components/kline/KLineView';
import { formatAmount, formatPercent, formatPricePoint } from '@utils/format';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { STOCK_DOWN_COLOR, STOCK_UP_COLOR } from '../../../../constants/stockColor';
import type { RecentSearchStockCardData } from './recentSearchStockData';

/** 最近搜索卡片入参 */
export interface RecentSearchStockCardProps {
  /** 卡片数据 */
  cardData: RecentSearchStockCardData;
  /** 网格序号，用于入场动画错位延迟（从 0 起算） */
  cardOrdinal: number;
  /** 点击整卡，跳转到该股 K 线页 */
  onOpenKLine: (stockCode: string) => void;
  /** 占位态：字段全空、不可点击 */
  isPlaceholder?: boolean;
}

/** 涨跌方向色：红涨绿跌，缺失涨跌幅时按涨色处理 */
function resolveStockTrendColor(changePct: number | null | undefined): string {
  return (changePct ?? 0) >= 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR;
}

/** 指标网格单元：左侧标签 + 右侧数值 */
function StockQuoteMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-black/[0.03] px-3 py-2 xl:px-2 xl:py-1.5 dark:bg-white/[0.04]">
      <span className="text-[11px] text-muted-text xl:text-[10px]">{label}</span>
      <span className="text-xs font-medium xl:text-[11px]">{value}</span>
    </div>
  );
}

/**
 * 最近搜索股票卡片：实时价格、迷你分时、四项指标与「加入自选」按钮。
 * 四列布局（xl 及以上）卡片变窄，间距与字号同步收紧；结构与功能不变。
 * memo 化避免批量回填分时后未变化的卡片重绘走势图。
 */
function RecentSearchStockCard({
  cardData,
  cardOrdinal,
  onOpenKLine,
  isPlaceholder = false,
}: RecentSearchStockCardProps) {
  const { t } = useUiLanguage();
  const { stockQuote, timeline, prevClose } = cardData;

  // 行情缺失时回落分时最后一点：盘中为最新成交价，收盘后即收盘价
  const latestTimelinePrice = timeline.length > 0 ? timeline[timeline.length - 1].close : null;
  const stockPrice = stockQuote.price ?? latestTimelinePrice ?? null;
  const isPriceUp = (stockQuote.changePct ?? 0) >= 0;
  const priceTrendColor = resolveStockTrendColor(stockQuote.changePct);
  // 涨跌额 = 现价 - 昨收；任一缺失时显示占位
  const priceChangeAmount =
    stockPrice !== null && stockQuote.prevClose != null && stockQuote.prevClose > 0
      ? stockPrice - stockQuote.prevClose
      : null;

  const stockMetrics = [
    { label: t('kline.recentSearch.stockCard.price'), value: formatPricePoint(stockPrice) },
    { label: t('kline.recentSearch.stockCard.amplitude'), value: formatPercent(stockQuote.amplitude) },
    { label: t('kline.recentSearch.stockCard.totalMarketCap'), value: formatAmount(stockQuote.totalMarketCap) },
    { label: t('kline.recentSearch.stockCard.turnoverRate'), value: formatPercent(stockQuote.turnoverRate) },
  ];
  const timelineLegendItems = [
    { label: t('kline.recentSearch.stockCard.priceLegend'), color: priceTrendColor },
    { label: t('kline.recentSearch.stockCard.avgPriceLegend'), color: AVG_PRICE_LINE_COLOR },
  ];

  return (
    <AnimCard
      ordinal={cardOrdinal}
      onClick={isPlaceholder ? undefined : () => onOpenKLine(stockQuote.code)}
      tooltip={isPlaceholder ? undefined : t('kline.recentSearch.stockCard.openKline')}
      className={`flex h-full flex-col p-4 xl:p-3 ${
        isPlaceholder ? '' : 'transition-transform duration-200 hover:-translate-y-0.5'
      }`}
    >
      {/* 头部：名称 + 代码 | 涨跌幅徽章 */}
      <div className="flex items-start justify-between gap-2 xl:gap-1.5">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold leading-tight xl:text-xs">
            {stockQuote.name ?? stockQuote.code}
          </div>
          <div className="mt-0.5 text-xs text-muted-text xl:text-[11px]">{stockQuote.code}</div>
        </div>
        <span
          className="flex shrink-0 items-center gap-1 rounded-sm px-2 py-1 text-xs font-semibold xl:gap-0.5 xl:px-1.5 xl:py-0.5 xl:text-[11px]"
          style={{ color: priceTrendColor, backgroundColor: `${priceTrendColor}1a` }}
        >
          <span aria-hidden className="text-[9px] xl:text-[8px]">{isPriceUp ? '▲' : '▼'}</span>
          {formatPercent(stockQuote.changePct)}
        </span>
      </div>

      {/* 价格区：大字号最新价 + 右侧涨跌额 */}
      <div className="mt-3 flex items-start justify-between gap-2 xl:mt-2 xl:gap-1.5">
        <div className="text-xl font-bold leading-tight xl:text-lg" style={{ color: priceTrendColor }}>
          {formatPricePoint(stockPrice)}
        </div>
        <span className="text-xs font-medium xl:text-[11px]" style={{ color: priceTrendColor }}>
          {priceChangeAmount === null ? '--' : `${isPriceUp ? '+' : ''}${priceChangeAmount.toFixed(2)}`}
        </span>
      </div>

      {/* 迷你分时走势 + 图例 */}
      <div className="mt-3 rounded-lg bg-black/[0.03] p-2 xl:mt-2 xl:p-1.5 dark:bg-white/[0.04]">
        <KLineView timeline={timeline} prevClose={prevClose} height={96} className="border-none bg-transparent" />
        <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-text xl:mt-1 xl:gap-2 xl:text-[10px]">
          {timelineLegendItems.map((legendItem) => (
            <span key={legendItem.label} className="flex items-center gap-1.5">
              <span aria-hidden className="h-[2px] w-4 rounded-full xl:w-3" style={{ backgroundColor: legendItem.color }} />
              {legendItem.label}
            </span>
          ))}
        </div>
      </div>

      {/* 指标网格：股票价格 / 振幅 / 总市值 / 换手率 */}
      <div className="mt-3 grid grid-cols-2 gap-2 xl:mt-2 xl:gap-1.5">
        {stockMetrics.map((stockMetric) => (
          <StockQuoteMetric key={stockMetric.label} label={stockMetric.label} value={stockMetric.value} />
        ))}
      </div>

      {/* 操作区：加入自选占位态不渲染 */}
      {!isPlaceholder && (
        <div className="mt-3 xl:mt-2">
          {/* TODO: 接入加入自选逻辑（onAddToWatchlist） */}
          <HrsButton variant="outline" size="sm" className="w-full justify-center">
            <Plus className="h-3.5 w-3.5 xl:h-3 xl:w-3" aria-hidden />
            {t('kline.recentSearch.addWatchlist')}
          </HrsButton>
        </div>
      )}
    </AnimCard>
  );
}

export default memo(RecentSearchStockCard);
