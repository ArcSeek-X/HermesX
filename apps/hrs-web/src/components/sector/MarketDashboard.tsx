/**
 * 市场仪表盘组件（统一展示涨跌家数、量能和指数）
 *
 * 功能：
 * - 涨跌家数卡片（1个卡片，内部3行：上涨/平盘/下跌，每行标签+数值左右排列）
 * - 量能卡片（1个卡片，内部2行：成交额/量比，每行标签+数值左右排列）
 * - 6 个大盘指数卡片（每个卡片3行：名称/价格/涨跌幅）
 * - 所有卡片统一高度、统一样式
 * - "更多"按钮展开剩余指数（沪深300、中证500、中证2000），展开后与第一行无缝衔接
 * - 组件挂载时首次加载，后续由父组件通过 ref.refresh() 每 30 秒触发刷新
 *
 * 数据来源：
 * - 指数数据：东方财富 push2 API（通过后端 /api/v1/sector/market-indices 代理）
 * - 涨跌家数/量能：东方财富 push2delay API（通过后端 /api/v1/sector/market-overview 代理）
 */
import { useCallback, useEffect, useState, useImperativeHandle, forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';
import {
  fetchMarketIndices,
  fetchMarketOverview,
  type MarketIndexItem,
  type MarketOverviewData,
} from '../../api/sectorData';

/** 暴露给父组件的接口：允许父组件触发手动刷新 */
export type MarketDashboardHandle = {
  refresh: () => void;
};

/** 默认展示的指数数量（前 6 个） */
const VISIBLE_INDEX_COUNT = 6;

/** 卡片统一最小高度（与指数卡片 3 行内容匹配） */
const CARD_MIN_HEIGHT = '96px';

/** 卡片统一最小宽度（防止浏览器拉伸时文字换行） */
const CARD_MIN_WIDTH = '120px';

const MarketDashboard = forwardRef<MarketDashboardHandle>((_props, ref) => {
  const [indices, setIndices] = useState<MarketIndexItem[]>([]);
  const [overview, setOverview] = useState<MarketOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  const load = useCallback(async () => {
    try {
      const [indexData, overviewData] = await Promise.all([
        fetchMarketIndices(),
        fetchMarketOverview(),
      ]);
      setIndices(indexData);
      setOverview(overviewData);
    } catch (err) {
      console.error('Failed to load market dashboard:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useImperativeHandle(ref, () => ({ refresh: load }), [load]);

  useEffect(() => {
    let mounted = true;
    async function init() {
      if (mounted) setLoading(true);
      await load();
    }
    init();
    return () => { mounted = false; };
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
      </div>
    );
  }

  const visibleIndices = indices.slice(0, VISIBLE_INDEX_COUNT);
  const extraIndices = indices.slice(VISIBLE_INDEX_COUNT);
  const hasMore = extraIndices.length > 0;

  return (
    <div>
      {/* 第一行：涨跌家数 + 量能 + 前 6 个指数（共 8 个卡片） */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {/* 涨跌家数卡片（1 个卡片，内部 3 行：上涨/平盘/下跌） */}
        <div
          className="flex flex-col justify-center p-2 rounded-lg bg-card border border-subtle"
          style={{ minHeight: CARD_MIN_HEIGHT, minWidth: CARD_MIN_WIDTH }}
        >
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-text">上涨</span>
              <span className="text-sm font-semibold stock-up tabular-nums">
                {overview?.riseCount ?? '-'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-text">平盘</span>
              <span className="text-sm font-semibold text-muted-text tabular-nums">
                {overview?.flatCount ?? '-'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-text">下跌</span>
              <span className="text-sm font-semibold stock-down tabular-nums">
                {overview?.fallCount ?? '-'}
              </span>
            </div>
          </div>
        </div>

        {/* 量能卡片（3 行：成交额/放量缩量/昨成交） */}
        <div
          className="flex flex-col justify-center p-2 rounded-lg bg-card border border-subtle"
          style={{ minHeight: CARD_MIN_HEIGHT, minWidth: CARD_MIN_WIDTH }}
        >
          <div className="flex flex-col gap-1.5">
            {/* 成交额 */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-text">成交额</span>
              <span className="text-sm font-semibold text-foreground tabular-nums">
                {overview ? formatAmount(overview.totalAmount) : '-'}
              </span>
            </div>
            {/* 放量/缩量 */}
            {overview && overview.volumeChange !== undefined && overview.volumeChange !== 0 ? (
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-text">
                  {overview.volumeChange > 0 ? '放量' : '缩量'}
                </span>
                <span
                  className={`text-sm font-semibold tabular-nums ${
                    overview.volumeChange > 0 ? 'stock-up' : 'stock-down'
                  }`}
                >
                  {formatAmount(Math.abs(overview.volumeChange))}
                </span>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-text">放量</span>
                <span className="text-sm font-semibold text-muted-text tabular-nums">-</span>
              </div>
            )}
            {/* 昨成交 */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-text">昨成交</span>
              <span className="text-sm font-semibold text-foreground tabular-nums">
                {overview ? formatAmount(overview.yesterdayAmount) : '-'}
              </span>
            </div>
          </div>
        </div>

        {/* 前 6 个指数 */}
        {visibleIndices.map((index) => (
          <IndexCard key={index.code} index={index} />
        ))}
      </div>

      {/* 展开区域：剩余指数（与第一行无缝衔接） */}
      {hasMore && (
        <div
          className="overflow-hidden transition-all duration-300 ease-in-out"
          style={{
            maxHeight: expanded ? '300px' : '0px',
            opacity: expanded ? 1 : 0,
          }}
        >
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 mt-3">
            {extraIndices.map((index) => (
              <IndexCard key={index.code} index={index} />
            ))}
          </div>
        </div>
      )}

      {/* "更多"/"收起" 按钮 */}
      {hasMore && (
        <div className="flex justify-center mt-3">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-lg border border-subtle text-muted-text hover:text-foreground hover:border-cyan/50 transition-colors"
          >
            {expanded ? '收起' : '更多'}
            <ChevronDown className={`h-3 w-3 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`} />
          </button>
        </div>
      )}
    </div>
  );
});

MarketDashboard.displayName = 'MarketDashboard';

/** 格式化成交额（元 → 亿元/万亿元） */
function formatAmount(amount: number): string {
  const yi = amount / 1e8;
  if (yi >= 10000) {
    return `${(yi / 10000).toFixed(2)}万亿`;
  }
  return `${yi.toFixed(2)}亿`;
}

/**
 * 指数卡片
 * 展示指数名称、最新价格、涨跌幅（3行内容）
 */
function IndexCard({ index }: { index: MarketIndexItem }) {
  return (
    <div
      className="flex flex-col items-center justify-center p-2 rounded-lg bg-card border border-subtle"
      style={{ minHeight: CARD_MIN_HEIGHT, minWidth: CARD_MIN_WIDTH }}
    >
      <div className="text-xs text-muted-text mb-1">{index.name}</div>
      <div className="text-base font-semibold text-foreground leading-tight tabular-nums">
        {index.price !== null ? index.price.toFixed(2) : '-'}
      </div>
      <div
        className={`text-sm font-medium mt-1 tabular-nums ${
          index.changePercent === null
            ? 'text-muted-text'
            : index.changePercent > 0
              ? 'stock-up'
              : index.changePercent < 0
                ? 'stock-down'
                : 'text-muted-text'
        }`}
      >
        {index.changePercent !== null
          ? `${index.changePercent > 0 ? '+' : ''}${index.changePercent.toFixed(2)}%`
          : '-'}
      </div>
    </div>
  );
}

export default MarketDashboard;
