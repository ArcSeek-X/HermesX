/**
 * 个股 K 线页「最近搜索」单卡：行情头 + 价格 + 迷你分时 + 指标网格。
 * 支持占位态（字段全空、不可点击）以避免列表加载中空白闪烁。
 */

import { memo } from 'react';
import { Plus } from 'lucide-react';
import { AnimCard, HrsButton } from '@components';
import { AVG_PRICE_LINE_COLOR, KLineView } from '@components/kline/KLineView';
import { formatAmount, formatPercent, formatPricePoint } from '@utils/format';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { STOCK_DOWN_COLOR, STOCK_UP_COLOR } from '../../../../constants/stockColor';
import type { KLinePoint, StockInfo } from '../../../../api/kline';

/**
 * 单张卡片的数据源：通用股票对象（与 StockInfoHeader 共用）+ 迷你分时。
 * 卡片先以行情信息即时插入，分时统一由批量分时接口异步补齐（首屏历史与搜索插入同一口径）。
 */
export interface RecentSearchStockCardData {
  /** 通用股票对象（StockInfo），含名称/代码/行情 */
  info: StockInfo;
  /** 迷你分时走势（当日分时缩略图，由 batch-timeline 异步补齐；未到位时为空数组） */
  timeline: KLinePoint[];
  /** 分时昨收基准价，优先取批量分时、其次取行情前收 */
  prevClose: number | null;
}

/** 最近搜索卡片组件入参 */
export interface RecentSearchStockCardProps {
  /** 卡片数据 */
  cardData: RecentSearchStockCardData;
  /** 网格序号，用于入场动画错位延迟（从 0 起算） */
  ordinal: number;
  /** 点击整卡回调，由列表组件跳转到该股 K 线页 */
  onOpen: (stockCode: string) => void;
  /** 占位态：字段全空、不可点击，用于列表加载中避免空白闪烁 */
  isPlaceholder?: boolean;
}

/** 涨跌方向色：红涨绿跌，缺失涨跌幅时按涨色处理（与徽章一致） */
function trendColorOf(changePct: number | null | undefined): string {
  return (changePct ?? 0) >= 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR;
}

/** 指标网格单元：左侧标签 + 右侧数值，浅灰底（与 EodStockCard 的 dataItem 同款） */
function RecentSearchMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-black/[0.03] px-3 py-2 dark:bg-white/[0.04]">
      <span className="text-[11px] text-muted-text">{label}</span>
      <span className="text-xs font-medium">{value}</span>
    </div>
  );
}

/**
 * 最近搜索股票卡片：展示实时价格、迷你分时与四项指标，底部含「加入自选」按钮。
 * 「加入自选」按钮当前仅 UI 占位（onClick 留空），自选逻辑尚未接入。
 * memo 化避免行情批量回填时未变化的卡片重绘走势图。
 */
function RecentSearchStockCard({
  cardData,
  ordinal,
  onOpen,
  isPlaceholder = false,
}: RecentSearchStockCardProps) {
  const { t } = useUiLanguage();
  const { info, timeline, prevClose } = cardData;

  // 行情缺失时回落到分时最后一点（盘中为最新成交价，收盘后即收盘价）
  const latestTimelinePrice = timeline.length > 0 ? timeline[timeline.length - 1].close : null;
  const stockPrice = info.price ?? latestTimelinePrice ?? null;
  const isUp = (info.changePct ?? 0) >= 0;
  const trendColor = trendColorOf(info.changePct);
  // 涨跌额 = 现价 - 昨收；任一缺失则显示占位
  const changeAmount =
    stockPrice !== null && info.prevClose != null && info.prevClose > 0
      ? stockPrice - info.prevClose
      : null;

  const metrics = [
    { label: t('kline.recentSearch.stockCard.price'), value: formatPricePoint(stockPrice) },
    { label: t('kline.recentSearch.stockCard.amplitude'), value: formatPercent(info.amplitude) },
    { label: t('kline.recentSearch.stockCard.totalMarketCap'), value: formatAmount(info.totalMarketCap) },
    { label: t('kline.recentSearch.stockCard.turnoverRate'), value: formatPercent(info.turnoverRate) },
  ];
  const legendItems = [
    { label: t('kline.recentSearch.stockCard.priceLegend'), color: trendColor },
    { label: t('kline.recentSearch.stockCard.avgPriceLegend'), color: AVG_PRICE_LINE_COLOR },
  ];

  return (
    <AnimCard
      ordinal={ordinal}
      onClick={isPlaceholder ? undefined : () => onOpen(info.code)}
      tooltip={isPlaceholder ? undefined : t('kline.recentSearch.stockCard.openKline')}
      className={`flex h-full flex-col p-4 ${
        isPlaceholder ? '' : 'transition-transform duration-200 hover:-translate-y-0.5'
      }`}
    >
      {/* 头部：名称 + 代码 | 涨跌幅徽章 */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold leading-tight">
            {info.name ?? info.code}
          </div>
          <div className="mt-0.5 text-xs text-muted-text">{info.code}</div>
        </div>
        <span
          className="flex shrink-0 items-center gap-1 rounded-sm px-2 py-1 text-xs font-semibold"
          style={{ color: trendColor, backgroundColor: `${trendColor}1a` }}
        >
          <span aria-hidden className="text-[9px]">{isUp ? '▲' : '▼'}</span>
          {formatPercent(info.changePct)}
        </span>
      </div>

      {/* 价格区：大字号最新价 + 右侧涨跌额 */}
      <div className="mt-3 flex items-start justify-between gap-2">
        <div className="text-xl font-bold leading-tight" style={{ color: trendColor }}>
          {formatPricePoint(stockPrice)}
        </div>
        <span className="text-xs font-medium" style={{ color: trendColor }}>
          {changeAmount === null ? '--' : `${isUp ? '+' : ''}${changeAmount.toFixed(2)}`}
        </span>
      </div>

      {/* 迷你分时走势 + 图例：图表去边框/背景融入浅灰容器 */}
      <div className="mt-3 rounded-lg bg-black/[0.03] p-2 dark:bg-white/[0.04]">
        <KLineView timeline={timeline} prevClose={prevClose} height={110} className="border-none bg-transparent" />
        <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-text">
          {legendItems.map((item) => (
            <span key={item.label} className="flex items-center gap-1.5">
              <span aria-hidden className="h-[2px] w-4 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      </div>

      {/* 指标网格：股票价格 / 振幅 / 总市值 / 换手率 */}
      <div className="mt-3 grid grid-cols-2 gap-2">
        {metrics.map((metric) => (
          <RecentSearchMetric key={metric.label} label={metric.label} value={metric.value} />
        ))}
      </div>

      {/* 操作区：加入自选（逻辑待接入，当前仅按钮 UI 占位；占位态不渲染） */}
      {!isPlaceholder && (
        <div className="mt-3">
          {/* TODO: 接入加入自选逻辑（onAddToWatchlist） */}
          <HrsButton variant="outline" size="sm" className="w-full justify-center">
            <Plus className="h-3.5 w-3.5" aria-hidden />
            {t('kline.recentSearch.addWatchlist')}
          </HrsButton>
        </div>
      )}
    </AnimCard>
  );
}

export default memo(RecentSearchStockCard);
