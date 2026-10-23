/**
 * @file keyValueCard.tsx
 * @description 键值指标卡片（KeyValueCard）：以「标签 + 大号数值」的纵向结构展示单项关键指标。
 *   外层复用 AnimCard（gradientBackground）获得与 Card 族一致的渐变底与错位入场动画，ordinal 控制延迟。
 *   标签 / 数值样式对齐 IndexCard：小号弱化标签（超长省略）+ 大号等宽数值（tabular-nums 保证数字对齐）。
 * 使用场景：持仓总览等看板的单项指标，经 Card/index.ts 聚合导出，以 `import { KeyValueCard } from '@components'` 引用。
 * @author Lensgcx (GaoCangxiong)
 */

import type { ReactNode } from 'react';
import { AnimCard } from '../AnimCard';
import { cn } from '../../../../utils/cn';

/** KeyValueCard 组件的 Props 定义。 */
export interface KeyValueCardProps {
  /** 指标标签（如 "总权益" / "Total Equity"），必填 */
  label: string;
  /** 指标数值，可为字符串或 JSX 节点，必填 */
  value: ReactNode;
  /** 前置单位（如货币符号 "¥" / "$"），可选；不传则不渲染 */
  preValue?: string;
  /** 后置单位（如 "元" / "%" / "股"），可选；不传则不渲染 */
  suffixValue?: string;
  /** 网格序号，从 0 起算，用于入场动画错位延迟（每个延迟 0.05s），默认 0 */
  ordinal?: number;
  /** 透传的额外类名（追加而非覆盖），可选 */
  className?: string;
}

/**
 * 渲染单个键值指标卡片。
 * 纵向展示 label（小号弱化标签）与 value（大号等宽数值），外层由 AnimCard 提供渐变底与入场动画。
 *
 * @param props - 组件属性，详见 KeyValueCardProps
 * @returns 标签 + 数值的指标卡片
 */
export function KeyValueCard({ label, value, preValue, suffixValue, ordinal = 0, className }: KeyValueCardProps) {
  return (
    <AnimCard className={cn('flex-col p-5', className)} gradientBackground ordinal={ordinal}>
      {/* 标签：小号弱化，超长省略 */}
      <div className="text-xs text-muted-text truncate">{label}</div>
      {/* 数值：大号等宽，tabular-nums 保证多位数字对齐；前后置单位更小且弱化，未传则不渲染 */}
      <div className="mt-2 text-2xl font-semibold font-mono leading-tight tabular-nums text-foreground">
        {preValue ? <span className="mr-1 text-sm font-medium text-foreground-soft">{preValue}</span> : null}
        {value}
        {suffixValue ? <span className="ml-1 text-sm font-medium text-foreground-soft">{suffixValue}</span> : null}
      </div>
    </AnimCard>
  );
}
