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
import type {
  BoardListItem,
  MarketFundFlowData,
  NorthboundFlowData,
} from '../../api/sectorData';
import { formatAmount, formatPercent, formatSignedAmount, getChangeColorClass } from '../../utils/format';

/** 通用统计卡片 props */
export type MarketStatCardProps = {
  /** 卡片标题 */
  title: string;
  /** 主值内容 */
  value: ReactNode;
  /** 主值颜色 class（默认 text-foreground） */
  valueClass?: string;
  /** 副值内容 */
  meta: ReactNode;
};

/**
 * 通用统计卡片骨架
 *
 * 布局（自上而下）：标题 → 主值 → 副值，统一高度与内边距。
 */
export function MarketStatCard({ title, value, valueClass, meta }: MarketStatCardProps) {
  return (
    <div className="flex flex-col justify-between p-2.5 rounded-lg bg-card border border-subtle min-h-[96px]">
      <div className="text-xs text-muted-text">{title}</div>
      <div className={`text-base font-semibold leading-tight tabular-nums ${valueClass ?? 'text-foreground'}`}>
        {value}
      </div>
      <div className="text-xs text-secondary-text leading-4">{meta}</div>
    </div>
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
};

/** 市场涨跌卡片：上涨/下跌家数（红绿着色），副值显示平盘数 */
export function MarketBreadthCard({ riseCount, fallCount, flatCount }: MarketBreadthCardProps) {
  return (
    <MarketStatCard
      title="市场涨跌"
      value={
        <span>
          <span className="stock-up">{riseCount}</span>
          <span className="mx-1 text-muted-text">/</span>
          <span className="stock-down">{fallCount}</span>
        </span>
      }
      meta={
        <span>
          上涨 / 下跌 <span className="text-muted-text">· {flatCount} 平</span>
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
};

/** 涨跌停卡片：涨停/跌停家数（红绿着色） */
export function LimitUpDownCard({ limitUpCount, limitDownCount }: LimitUpDownCardProps) {
  return (
    <MarketStatCard
      title="涨跌停"
      value={
        <span>
          <span className="stock-up">{limitUpCount}</span>
          <span className="mx-1 text-muted-text">/</span>
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
};

/** 全市场成交额卡片：A 股实时成交额快照 */
export function TotalAmountCard({ totalAmount }: TotalAmountCardProps) {
  return (
    <MarketStatCard title="全市场成交额" value={formatAmount(totalAmount)} meta="A 股实时成交额快照" />
  );
}

/** 北向资金卡片 props */
export type NorthboundCardProps = {
  /** 北向资金数据（2024-08 后实时数据停披露，netInflow 可能为 null） */
  data: NorthboundFlowData | null;
};

/** 北向资金卡片：沪深港通净流入（随正负着色），副值显示数据日期 */
export function NorthboundCard({ data }: NorthboundCardProps) {
  const inflow = data?.netInflow ?? null;
  return (
    <MarketStatCard
      title="北向资金"
      value={formatSignedAmount(inflow)}
      valueClass={getChangeColorClass(inflow)}
      meta={data?.date ?? '实时快照'}
    />
  );
}

/** 大盘主力卡片 props */
export type MainFlowCardProps = {
  /** 大盘主力资金数据（日线口径，盘中展示最近交易日收盘数据） */
  data: MarketFundFlowData | null;
};

/** 大盘主力卡片：主力净流入（随正负着色），副值显示占比与日期 */
export function MainFlowCard({ data }: MainFlowCardProps) {
  const inflow = data?.mainNetInflow ?? null;
  const percent = data?.mainNetInflowPercent;
  return (
    <MarketStatCard
      title="大盘主力"
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
};

/** 最强板块卡片：板块名称（随涨跌着色），副值显示涨跌幅与强度口径 */
export function StrongestSectorCard({ data }: StrongestSectorCardProps) {
  return (
    <MarketStatCard
      title="最强板块"
      value={data?.name ?? '--'}
      valueClass={getChangeColorClass(data?.changePercent)}
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
