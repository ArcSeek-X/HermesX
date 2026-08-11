/**
 * 市场统计卡片组件（MarketStatCards）
 *
 * 为总览页面提供可复用的市场统计卡片集合：
 * - MarketStatCard：通用卡片骨架（标题 + 主值 + 副值），各卡片统一布局与样式
 * - MarketBreadthCard：市场涨跌（上涨/下跌家数 + 平盘）
 * - LimitUpDownCard：涨跌停（涨停/跌停家数）
 * - TotalAmountCard：全市场成交额
 * - NorthboundCard：北向资金（沪深港通净流入）
 * - MainFlowCard：大盘主力（主力净流入 + 占比）
 * - StrongestSectorCard：最强板块（涨幅第一的行业板块）
 *
 * 数据来源：market-overview（涨跌/涨跌停/成交额/量能）、northbound-flow（北向）、
 * market-fund-flow（大盘主力）、board-list（最强板块），均通过后端代理。
 */
import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import type {
  BoardListItem,
  MarketFundFlowData,
  NorthboundFlowData,
} from '../../api/sectorData';
import { formatAmountRounding, formatPercent, formatSignedAmount, getChangeColorClass } from '../../utils/format';

/** 通用统计卡片 props */
export type MarketStatCardProps = {
  /** 卡片标题 */
  title: string;
  /** 标题样式 class（默认 text-xs text-muted-text，可覆盖为更醒目的标题样式） */
  titleClassName?: string;
  /** 主值内容 */
  value: ReactNode;
  /** 主值颜色 class（默认 text-foreground） */
  valueClass?: string;
  /** 额外 class（合并到主值容器，用于覆盖/追加样式） */
  className?: string;
  /** 副值内容 */
  meta: ReactNode;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
};

/**
 * 通用统计卡片骨架
 *
 * 布局（自上而下）：标题与主值紧邻无间隙，副值贴底（mt-auto），统一高度与内边距。
 * 入场动画使用 framer-motion（本项目以 motion 包提供）：slide-up + fade-in，
 * 按 ordinal 在同类卡片间错位延迟。
 */
export function MarketStatCard({ title, titleClassName, value, valueClass, className, meta, ordinal = 0 }: MarketStatCardProps) {
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
      <div className="relative z-10 flex flex-col p-4 h-full">
        <div className={titleClassName ?? 'text-xs text-muted-text'}>{title}</div>
        <div className={`text-2xl lg:text-2xl font-semibold mt-2 leading-tight tabular-nums ${valueClass ?? 'text-foreground'}  ${className ?? ''}`}>
          {value}
        </div>
        <div className="mt-auto text-xs text-secondary-text leading-4">{meta}</div>
      </div>
    </motion.div>
  );
}

/** 市场涨跌卡片 props */
export type MarketBreadthCardProps = {
  /** 上涨家数 */
  riseCount: number;
  /** 下跌家数 */
  fallCount: number;
  /** 平盘家数 */
  flatCount: number;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
};

/** 市场涨跌卡片：上涨/下跌家数（红绿着色），副值显示平盘数 */
export function MarketBreadthCard({ riseCount, fallCount, flatCount, ordinal }: MarketBreadthCardProps) {
  return (
    <MarketStatCard
      title="市场涨跌"
      ordinal={ordinal}
      value={
        <span className="inline-flex items-baseline gap-1">
          <span className="stock-up">{riseCount}</span>
          <span className="text-sm text-muted-text">/</span>
          <span className="stock-down">{fallCount}</span>
        </span>
      }
      meta={
       <span className="flex items-center justify-between">
          <span>
            上涨 / 下跌
          </span>
          <span className="text-muted-text">· {flatCount} 平</span>
        </span>
      }
    />
  );
}

/** 涨跌停卡片 props */
export type LimitUpDownCardProps = {
  /** 涨停家数 */
  limitUpCount: number;
  /** 跌停家数 */
  limitDownCount: number;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
};

/** 涨跌停卡片：涨停/跌停家数（红绿着色） */
export function LimitUpDownCard({ limitUpCount, limitDownCount, ordinal }: LimitUpDownCardProps) {
  return (
    <MarketStatCard
      title="涨跌停"
      ordinal={ordinal}
      value={
        <span>
          <span className="stock-up">{limitUpCount}</span>
          <span className="mx-1 text-sm text-muted-text">/</span>
          <span className="stock-down">{limitDownCount}</span>
        </span>
      }
      meta="涨停 / 跌停"
    />
  );
}

/** 全市场成交额卡片 props */
export type TotalAmountCardProps = {
  /** 全市场成交额（元） */
  totalAmount: number;
  /** 放量/缩量金额（元，正=放量，负=缩量），可选 */
  volumeChange?: number;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
};

/**
 * 全市场成交额卡片：A 股实时成交额快照（以"亿"为单位）；
 * 副值第一行显示放量/缩量金额（带正负颜色），第二行显示快照说明。
 */
export function TotalAmountCard({ totalAmount, volumeChange, ordinal }: TotalAmountCardProps) {
  const isIncrease = volumeChange != null && volumeChange > 0;
  const isDecrease = volumeChange != null && volumeChange < 0;
  const volumeChangeText =
    volumeChange != null ? `${volumeChange > 0 ? '+' : ''}${formatAmountRounding(volumeChange, 'yi')}` : '--';
  const volumeChangeClass = isIncrease ? 'stock-up' : isDecrease ? 'stock-down' : 'text-muted-text';
  return (
    <MarketStatCard
      title="全市场成交额"
      ordinal={ordinal}
      value={formatAmountRounding(totalAmount, 'yi')}
      meta={
        <div className="flex flex-col gap-0.5">
          <div className={`${volumeChangeClass} mt-2 text-xs` }>
            较上一日 {isIncrease ? '增量' : isDecrease ? '缩量' : '持平'} {volumeChangeText}
          </div>
          <div className="text-muted-text mt-2">A 股实时成交额快照</div>
        </div>
      }
    />
  );
}

/** 北向资金卡片 props */
export type NorthboundCardProps = {
  /** 北向资金数据（2024-08 后实时数据停披露，netInflow 可能为 null） */
  data: NorthboundFlowData | null;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
};

/**
 * 北向资金卡片：沪深港通净流入（随正负着色），主值居中；
 * 底部左侧为数据日期，右侧为"北向汇总"分类标签（参考模板卡片布局）。
 */
export function NorthboundCard({ data, ordinal }: NorthboundCardProps) {
  const inflow = data?.netInflow ?? null;
  return (
    <MarketStatCard
      title="北向资金"
      ordinal={ordinal}
      titleClassName="text-xs text-muted-text"
      value={formatSignedAmount(inflow)}
      valueClass={getChangeColorClass(inflow)}
      meta={
        <span className="flex items-center justify-between">
          <span>
            <span className="stock-up">
              上涨 {data?.riseCount != null ? data.riseCount : '--'}
            </span>
            <span className="mx-1 text-muted-text">/</span>
            <span className="stock-down">
              下跌 {data?.fallCount != null ? data.fallCount : '--'}
            </span>
          </span>
          <span className="text-muted-text">北向汇总</span>
        </span>
      }
    />
  );
}

/** 大盘主力卡片 props */
export type MainFlowCardProps = {
  /** 大盘主力资金数据（日线口径，盘中展示最近交易日收盘数据） */
  data: MarketFundFlowData | null;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
};

/** 大盘主力卡片：主力净流入（随正负着色），副值显示占比与日期 */
export function MainFlowCard({ data, ordinal }: MainFlowCardProps) {
  const inflow = data?.mainNetInflow ?? null;
  const percent = data?.mainNetInflowPercent;
  return (
    <MarketStatCard
      title="大盘主力"
      ordinal={ordinal}
      value={formatSignedAmount(inflow)}
      valueClass={getChangeColorClass(inflow)}
      meta={
        <span>
          {percent != null ? `占比 ${formatPercent(percent)}` : '当日快照'}
          {data?.date ? <span className="text-muted-text"> · {data.date}</span> : null}
        </span>
      }
    />
  );
}

/** 最强板块卡片 props */
export type StrongestSectorCardProps = {
  /** 最强板块数据（行业板块涨幅第一） */
  data: BoardListItem | null;
  /** 卡片在网格中的序号，用于入场动画错位延迟（从 0 开始） */
  ordinal?: number;
};

/** 最强板块卡片：板块名称（随涨跌着色），副值显示涨跌幅与强度口径 */
export function StrongestSectorCard({ data, ordinal }: StrongestSectorCardProps) {
  return (
    <MarketStatCard
      title="最强板块"
      ordinal={ordinal}
      value={data?.name ?? '--'}
      valueClass={getChangeColorClass(data?.changePercent)}
      className="md:text-xl"
      meta={
        data ? (
          <span>
            {formatPercent(data.changePercent)} <span className="text-muted-text">· 行业强度</span>
          </span>
        ) : (
          '--'
        )
      }
    />
  );
}
