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
import { motion } from 'motion/react';
import type { MarketIndexItem } from '../../api/sectorData';
import { formatAmount, formatPercent, formatPricePoint, getChangeColorClass } from '../../utils/format';

/** IndexCard 组件 props */
export type IndexCardProps = {
  /** 指数行情数据（名称/点位/涨跌幅/涨跌点数/成交额） */
  index: MarketIndexItem;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
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
 *
 * 交互：使用 framer-motion（本项目以 motion 包提供）实现刷新时的
 * slide-up + fade-in 入场动画，并在同批卡片间按 ordinal 错位延迟。
 */
export default function IndexCard({ index, ordinal = 0 }: IndexCardProps) {
  // 涨跌点数（带符号，保留 2 位小数）
  const changeText =
    index.change != null ? `${index.change > 0 ? '+' : ''}${formatPricePoint(index.change)}` : '--';

  return (
    <motion.div
      className="hrs-index-card relative overflow-hidden rounded-lg bg-card border border-subtle min-h-[110px]
        before:content-[''] before:absolute before:inset-0 before:z-0 before:rounded-[inherit] before:pointer-events-none
        before:bg-[linear-gradient(180deg,rgba(255,255,255,0.05),transparent_44%),radial-gradient(circle_at_top_right,rgba(105,178,255,0.12),transparent_34%)]"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut', delay: ordinal * 0.05 }}
    >
      {/* 内容层抬升到 ::before 之上，避免渐变被 bg-card 背景遮盖 */}
      <div className="relative z-10 flex flex-col justify-between p-4 h-full">
        {/* 指数名称 */}
        <div className="text-xs text-muted-text truncate">{index.name}</div>
        {/* 指数点位 + 涨跌幅/涨跌点数 */}
        <div>
          <div className={`text-2xl font-semibold font-mono mt-1 leading-tight tabular-nums ${getChangeColorClass(index.changePercent)}`}>
            {formatPricePoint(index.price)}
          </div>
          <div className={`text-xs font-mono mt-2 tabular-nums ${getChangeColorClass(index.changePercent)}`}>
            {formatPercent(index.changePercent)}
            <span className="text-label ml-2">{changeText}</span>
          </div>
        </div>

        {/* 成交额（参考模板为非等宽正文） */}
        <div className="mt-2 flex items-center justify-between text-label">
          <span className="text-muted-text">成交</span>
          <span className="text-foreground tabular-nums">{formatAmount(index.amount)}</span>
        </div>
      </div>
    </motion.div>
  );
}
