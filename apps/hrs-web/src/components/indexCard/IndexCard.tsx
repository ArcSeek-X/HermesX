/**
 * 指数卡片（IndexCard）
 *
 * 总览页指数卡片区复用的单指数行情卡片，自上而下展示：
 * 1. 指数名称
 * 2. 最新点位 + 涨跌幅 / 涨跌点数（随涨跌同色）
 * 3. 成交额（A股）；海外指数无成交额时降级为振幅
 *
 * 行情经后端 /api/v1/sector/market-cards 聚合自东方财富；
 * 富时中国 A50 卡片在 A 股时段与 SGX 夜盘取不同标的，附带行情时间与来源标记。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import type { MarketIndexItem } from '../../api/sectorData';
import { formatAmount, formatPercent, formatPricePoint, getChangeColorClass } from '../../utils/format';
import { AnimatedValue } from '../../utils/animate.tsx';
import AnimCard from '../common/Card/AnimCard/AnimCard';

/** IndexCard 入参 */
export type IndexCardProps = {
  /** 指数行情数据 */
  index: MarketIndexItem;
  /** 网格序号，用于入场动画错位延迟（从 0 起算） */
  ordinal?: number;
};

/**
 * 次要指标行：标签 + 数值，等宽右对齐展示。
 *
 * @param label    指标名（如「成交」「振幅」）
 * @param value    已格式化好的展示串
 * @param valueKey 动画编排 key，值变化时触发过渡
 */
function AuxMetricRow({ label, value, valueKey }: { label: string; value: string; valueKey: string }) {
  return (
    <div className="flex items-center justify-between text-label">
      <span className="text-xs text-muted-text truncate">{label}</span>
      <span className="text-xs text-secondary-text tabular-nums">
        <AnimatedValue valueKey={valueKey}>{value}</AnimatedValue>
      </span>
    </div>
  );
}

/**
 * 派生「成交 / 振幅」指标内容。
 *
 * 有成交额时显示「成交 + 金额」；否则降级为「振幅 + 振幅值」
 * （振幅由 最高/最低/昨收 派生，用于海外指数）。数据缺失时 value 回退 "--"。
 */
type AuxMetric = { label: string; value: string; valueKey: string };
function useAmountOrAmplitudeMetric(idx: MarketIndexItem, amplitude: number | null): AuxMetric {
  if (idx.amount != null) {
    const formatted = formatAmount(idx.amount);
    return { label: '成交', value: formatted, valueKey: formatted };
  }
  const formatted = amplitude != null ? formatPercent(amplitude) : '--';
  return { label: '振幅', value: formatted, valueKey: formatted };
}

/**
 * 富时中国 A50 卡片的行情来源标记：盘中显示「指数 + 行情时间」，
 * 休市 / SGX 夜盘显示「期指 + 行情时间」；其余指数卡片不展示。
 * 时间按浏览器本地时区取到分钟，ISO 解析失败时只保留来源名。
 */
function formatA50QuoteBadge(idx: MarketIndexItem): string | null {
  if (!idx.quoteSource) return null;
  const quoteTime = idx.quoteAsOf ? new Date(idx.quoteAsOf) : null;
  const clock =
    quoteTime && !Number.isNaN(quoteTime.getTime())
      ? `${String(quoteTime.getHours()).padStart(2, '0')}:${String(quoteTime.getMinutes()).padStart(2, '0')}`
      : '';
  const sourceLabel = idx.quoteSource === 'futures' ? '期指' : '指数';
  return clock ? `${sourceLabel} ${clock}` : sourceLabel;
}

/**
 * 指数卡片
 *
 * 布局（自上而下）：名称 → 点位 + 涨跌 → 成交/振幅。
 * 字号字重对齐 Dashboard：点位 24/600 等宽，涨跌行 12、成交/振幅 11（等宽不加粗）。
 * 入场动画用 motion 包实现 slide-up + fade-in，按 ordinal 错位延迟。
 */
export default function IndexCard({ index, ordinal = 0 }: IndexCardProps) {
  // 兜底：上游偶发缺字段时避免渲染异常击穿 RouteBoundary
  const idx: MarketIndexItem =
    index ??
    ({
      name: '--',
      code: '',
      price: null,
      changePct: null,
      change: null,
      amount: null,
      high: null,
      low: null,
      prevClose: null,
    } as MarketIndexItem);

  // 涨跌点数（带符号，2 位小数）
  const changeText =
    idx.change != null ? `${idx.change > 0 ? '+' : ''}${formatPricePoint(idx.change)}` : '--';

  // 振幅% = (最高 - 最低) / 昨收 × 100；三字段均为有限正数才计算，否则 null
  const safeHigh = typeof idx.high === 'number' && Number.isFinite(idx.high) ? idx.high : null;
  const safeLow = typeof idx.low === 'number' && Number.isFinite(idx.low) ? idx.low : null;
  const safePreClose =
    typeof idx.prevClose === 'number' && Number.isFinite(idx.prevClose) && idx.prevClose > 0
      ? idx.prevClose
      : null;
  const amplitude =
    safeHigh != null && safeLow != null && safePreClose != null
      ? ((safeHigh - safeLow) / safePreClose) * 100
      : null;
  const a50QuoteBadge = formatA50QuoteBadge(idx);

  return (
    <AnimCard ordinal={ordinal} gradientBackground className="hrs-index-card">
      {/* 内容层置于 ::before 渐变之上，避免被 bg-card 遮盖 */}
      <div className="relative z-10 flex flex-col justify-between p-4 h-full">
        {/* 指数名称；A50 卡片右侧标注当前行情来源与时间 */}
        <div className="flex items-center justify-between gap-1">
          <div className="text-xs text-muted-text truncate">{idx.name}</div>
          {a50QuoteBadge && (
            <span className="shrink-0 text-[10px] text-muted-text tabular-nums">{a50QuoteBadge}</span>
          )}
        </div>
        {/* 点位 + 涨跌幅/涨跌点数 */}
        <div>
          <div className={`text-2xl font-semibold font-mono mt-1 leading-tight tabular-nums ${getChangeColorClass(idx.changePct)}`}>
            <AnimatedValue valueKey={formatPricePoint(idx.price)}>
              {formatPricePoint(idx.price)}
            </AnimatedValue>
          </div>
          <div className={`text-xs font-mono mt-2 tabular-nums ${getChangeColorClass(idx.changePct)}`}>
            <AnimatedValue valueKey={`${formatPercent(idx.changePct)}|${changeText}`}>
              {formatPercent(idx.changePct)}
              <span className="text-label ml-2">{changeText}</span>
            </AnimatedValue>
          </div>
        </div>

        {/* 成交（A股）/ 振幅（海外）降级展示 */}
        <div className="mt-2">
          <AuxMetricRow {...useAmountOrAmplitudeMetric(idx, amplitude)} />
        </div>
      </div>
    </AnimCard>
  );
}
