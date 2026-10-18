/**
 * 股票行情头部组件。
 * 展示股票名称、代码、最新价、涨跌额/涨跌幅，以及关键行情指标网格：
 * 今开、昨收、最高、最低、成交量、成交额、换手率、振幅、市盈率(TTM)、总市值。
 *
 * @author Lensgcx (GaoCangxiong)
 */

import type React from 'react';
import type { StockQuoteCore } from '../../types/stock';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import {
  formatStockVolumeFromShares,
  formatStockTurnoverAmount,
  formatStockMarketCap,
} from '../../utils/format';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR, STOCK_FLAT_COLOR } from '../../constants/stockColor';

export interface StockInfoHeaderProps {
  /** 当前股票的行情快照（名称/代码/价格/各项指标），必填；类型取自 types/stock.ts 单一真源 */
  info: StockQuoteCore;
}

/** 行情数值格式化为 2 位小数；空值显示占位符 "-" */
function formatQuoteValue(value: number | null): string {
  if (value == null) return '-';
  return value.toFixed(2);
}

/** 根据涨跌值返回对应颜色：涨红、跌绿、平/空为中性色 */
function getChangeColor(value: number | null): string {
  if (value == null) return STOCK_FLAT_COLOR;
  if (value > 0) return STOCK_UP_COLOR;
  if (value < 0) return STOCK_DOWN_COLOR;
  return STOCK_FLAT_COLOR;
}

/** 单个行情指标项：标签 + 数值，数值可单独指定颜色（如最高/最低相对昨收的红绿） */
function QuoteMetric({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
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
  // useUiLanguage 的 t 入参为 UiTextKey 窄类型，而格式化工具要求 (key: string) => string，
  // 此处安全扩宽签名以复用同一翻译函数
  const translate: (key: string) => string = t as (key: string) => string;
  const priceColor = getChangeColor(info.changePct);
  const changeSign = (info.change ?? 0) > 0 ? '+' : '';
  const percentSign = (info.changePct ?? 0) > 0 ? '+' : '';

  // 最高/最低相对昨收的红绿：高于昨收为红，低于昨收为绿
  const highColor = getChangeColor(info.high != null && info.prevClose != null ? info.high - info.prevClose : null);
  const lowColor = getChangeColor(info.low != null && info.prevClose != null ? info.low - info.prevClose : null);

  return (
    <div className="space-y-3">
      {/* 股票名称 + 最新价 */}
      <div className="flex items-baseline gap-4 flex-wrap">
        <div>
          <span className="text-xl font-bold text-foreground">{info.name || info.code}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold tabular-nums" style={{ color: priceColor }}>
            {formatQuoteValue(info.price)}
          </span>
          <span className="text-sm font-medium tabular-nums" style={{ color: priceColor }}>
            {changeSign}{formatQuoteValue(info.change)} / {percentSign}{formatQuoteValue(info.changePct)}%
          </span>
        </div>
      </div>

      {/* 关键指标网格 */}
      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-5 gap-x-6 gap-y-2">
        <QuoteMetric label={t('kline.info.open')} value={formatQuoteValue(info.open)} />
        <QuoteMetric label={t('kline.info.prevClose')} value={formatQuoteValue(info.prevClose)} />
        <QuoteMetric label={t('kline.info.high')} value={formatQuoteValue(info.high)} valueColor={highColor} />
        <QuoteMetric label={t('kline.info.low')} value={formatQuoteValue(info.low)} valueColor={lowColor} />
        <QuoteMetric label={t('kline.info.volume')} value={formatStockVolumeFromShares(info.volume, translate)} />
        <QuoteMetric label={t('kline.info.amount')} value={formatStockTurnoverAmount(info.amount, translate)} />
        <QuoteMetric label={t('kline.info.turnoverRate')} value={info.turnoverRate != null ? `${info.turnoverRate.toFixed(2)}%` : '-'} />
        <QuoteMetric label={t('kline.info.amplitude')} value={info.amplitude != null ? `${info.amplitude.toFixed(2)}%` : '-'} />
        <QuoteMetric label={t('kline.info.peRatioTTM')} value={formatQuoteValue(info.peRatioTTM)} />
        <QuoteMetric label={t('kline.info.totalMarketCap')} value={formatStockMarketCap(info.totalMarketCap, translate)} />
      </div>
    </div>
  );
};

export default StockInfoHeader;
