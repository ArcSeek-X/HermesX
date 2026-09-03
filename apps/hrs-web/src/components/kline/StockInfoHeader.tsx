/**
 * 股票信息头部组件
 *
 * 显示股票名称、代码、当前价格、涨跌幅，以及关键指标网格：
 * 今开、昨收、最高、最低、成交量、成交额、换手率、振幅、市盈率(TTM)、总市值
 */

import type React from 'react';
import type { StockInfo } from '../../api/kline';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import {
  formatStockVolumeFromShares,
  formatStockTurnoverAmount,
  formatStockMarketCap,
} from '../../utils/format';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR, STOCK_FLAT_COLOR } from '../../constants/stockColor';

type StockInfoHeaderProps = {
  info: StockInfo;
};

/** 格式化数值（保留 2 位小数） */
function formatNum(value: number | null): string {
  if (value == null) return '-';
  return value.toFixed(2);
}

/** 涨跌颜色（使用全局颜色常量） */
function changeColor(value: number | null): string {
  if (value == null) return STOCK_FLAT_COLOR;
  if (value > 0) return STOCK_UP_COLOR;
  if (value < 0) return STOCK_DOWN_COLOR;
  return STOCK_FLAT_COLOR;
}

/** 指标项 */
function MetricItem({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div className="flex items-baseline gap-2 min-w-0">
      <span className="text-xs text-muted-text whitespace-nowrap shrink-0">{label}</span>
      <span className="text-sm font-semibold tabular-nums whitespace-nowrap" style={valueColor ? { color: valueColor } : undefined}>
        {value}
      </span>
    </div>
  );
}

export const StockInfoHeader: React.FC<StockInfoHeaderProps> = ({ info }) => {
  const { t } = useUiLanguage();
  // 格式工具函数接受 (key: string) => string，而 t 为 UiTextKey 窄类型，此处安全扩宽
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
  const translate: (key: string) => string = t as (key: string) => string;
  const priceColor = changeColor(info.change_percent);
  const changeSign = (info.change ?? 0) > 0 ? '+' : '';
  const percentSign = (info.change_percent ?? 0) > 0 ? '+' : '';

  return (
    <div className="space-y-3">
      {/* 股票名称 + 价格 */}
      <div className="flex items-baseline gap-4 flex-wrap">
        <div>
          <span className="text-xl font-bold text-foreground">{info.stock_name || info.stock_code}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold tabular-nums" style={{ color: priceColor }}>
            {formatNum(info.current_price)}
          </span>
          <span className="text-sm font-medium tabular-nums" style={{ color: priceColor }}>
            {changeSign}{formatNum(info.change)} / {percentSign}{formatNum(info.change_percent)}%
          </span>
        </div>
      </div>

      {/* 关键指标网格（左右对称，末项不顶边） */}
      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-5 gap-x-6 gap-y-2">
        <MetricItem label={t('kline.info.open')} value={formatNum(info.open)} />
        <MetricItem label={t('kline.info.prevClose')} value={formatNum(info.prev_close)} />
        <MetricItem label={t('kline.info.high')} value={formatNum(info.high)} valueColor={changeColor(info.high && info.prev_close ? info.high - info.prev_close : null)} />
        <MetricItem label={t('kline.info.low')} value={formatNum(info.low)} valueColor={changeColor(info.low && info.prev_close ? info.low - info.prev_close : null)} />
        <MetricItem label={t('kline.info.volume')} value={formatStockVolumeFromShares(info.volume, translate)} />
        <MetricItem label={t('kline.info.amount')} value={formatStockTurnoverAmount(info.amount, translate)} />
        <MetricItem label={t('kline.info.turnoverRate')} value={info.turnover_rate != null ? `${info.turnover_rate.toFixed(2)}%` : '-'} />
        <MetricItem label={t('kline.info.amplitude')} value={info.amplitude != null ? `${info.amplitude.toFixed(2)}%` : '-'} />
        <MetricItem label={t('kline.info.peRatioTTM')} value={formatNum(info.pe_ratio_ttm)} />
        <MetricItem label={t('kline.info.totalMarketCap')} value={formatStockMarketCap(info.total_market_cap, translate)} />
      </div>
    </div>
  );
};

export default StockInfoHeader;
