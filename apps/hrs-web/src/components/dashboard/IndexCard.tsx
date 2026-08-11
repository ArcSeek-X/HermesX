/**
 * 指数卡片组件（IndexCard）
 *
 * 展示单个市场指数的核心行情指标，供总览页面指数卡片区复用：
 * - 指数名称、指数点位（最新价）
 * - 指数涨跌幅、指数涨跌点数（同色展示）
 * - 成交额（该指数当日成交额，元）
 *
 * 数据来源：通过后端 /api/v1/sector/market-indices 代理的东方财富指数行情。
 */
import type { MarketIndexItem } from '../../api/sectorData';
import { formatAmount, formatPercent, formatPricePoint, getChangeColorClass } from '../../utils/format';

/** IndexCard 组件 props */
export type IndexCardProps = {
  /** 指数行情数据（名称/点位/涨跌幅/涨跌点数/成交额） */
  index: MarketIndexItem;
};

/**
 * 指数卡片
 *
 * 布局（自上而下）：
 * 1. 指数名称（左对齐）
 * 2. 指数点位 + 涨跌幅/涨跌点数（随涨跌着色）
 * 3. 成交额
 *
 * 字号/字重对齐模板 Dashboard.tsx：点位 24px/600 等宽字体，
 * 涨跌幅行 12px、涨跌点数与成交额 11px（均等宽字体、不加粗）。
 */
export default function IndexCard({ index }: IndexCardProps) {
  // 涨跌点数（带符号，保留 2 位小数）
  const changeText =
    index.change != null ? `${index.change > 0 ? '+' : ''}${formatPricePoint(index.change)}` : '--';

  return (
    <div className="hrs-index-card flex flex-col justify-between p-2.5 rounded-lg bg-card border border-subtle min-h-[110px]">
      {/* 指数名称 */}
      <div className="text-xs text-muted-text truncate">{index.name}</div>

      {/* 指数点位 + 涨跌幅/涨跌点数 */}
      <div>
        <div
          className={`text-2xl font-semibold leading-tight font-mono tabular-nums ${getChangeColorClass(index.changePercent)}`}
        >
          {formatPricePoint(index.price)}
        </div>
        <div className={`text-xs font-mono mt-0.5 tabular-nums ${getChangeColorClass(index.changePercent)}`}>
          {formatPercent(index.changePercent)}
          <span className="text-label">{changeText}</span>
        </div>
      </div>

      {/* 成交额 */}
      <div className="mt-1.5 flex items-center justify-between text-label font-mono">
        <span className="text-muted-text">成交</span>
        <span className="text-foreground tabular-nums">{formatAmount(index.amount)}</span>
      </div>
    </div>
  );
}
