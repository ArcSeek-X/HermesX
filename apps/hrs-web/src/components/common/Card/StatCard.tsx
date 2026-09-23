/**
 * @file StatCard.tsx
 * @description 统计卡片（StatCard）组件：紧凑展示单个关键指标（标签 + 数值 + 辅助说明 + 可选图标），
 *   通过 variant 控制左侧强调条与图标色调以传达指标语义（常态 / 主色 / 成功 / 警告 / 危险）。
 *   基于 motion 实现淡入上移的入场动画，配合 ordinal 可错位逐个加载，用于看板、统计汇总等场景。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-23
 *
 * 使用场景：
 * - 被各业务页面（如 Token 用量看板、行情概览）以 `import { StatCard } from '@components'` 引用。
 * - 依赖：motion/react（入场动画）、@/utils/cn（类名合并）；视觉令牌与 Card 族（ListCard）保持一致。
 */

import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import { cn } from '../../../utils/cn';

/**
 * 指标卡片视觉变体：仅影响左侧强调条与图标颜色，不改变布局与字号。
 * - default：中性灰强调条，无语义着色；
 * - primary：主色（青）强调，用于核心指标；
 * - success：绿色，表示正向 / 良好；
 * - warning：黄色，表示注意 / 波动；
 * - danger： 红色，表示负向 / 风险。
 */
type StatCardVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger';

/**
 * 各 variant 对应的视觉令牌：左侧强调条（bg 字段，控制左侧边框色）、图标颜色（icon），
 * 以及 hover 时二者的高亮态（bgHover / iconHover）。
 * hover 跟随各自 variant 的语义色：带透明度的变体（default / primary）hover 时提亮到满色，
 * 语义色（success / warning / danger）保持同族色，不再统一切到主色。
 */
const VARIANT_STYLES: Record<
  StatCardVariant,
  { bg: string; icon: string; bgHover: string; iconHover: string }
> = {
  default: {
    bg: 'border-l-4 border-l-foreground-lightest',
    icon: 'text-foreground-soft',
    bgHover: 'hover:border-l-primary',
    iconHover: 'group-hover:text-primary',
  },
  primary: {
    bg: 'border-l-4 border-l-primary/80',
    icon: 'text-primary/80',
    bgHover: 'hover:border-l-primary',
    iconHover: 'group-hover:text-primary',
  },
  success: {
    bg: 'border-l-4 border-l-success/80',
    icon: 'text-success',
    bgHover: 'hover:border-l-success',
    iconHover: 'group-hover:text-success',
  },
  warning: {
    bg: 'border-l-4 border-l-warning/80',
    icon: 'text-warning',
    bgHover: 'hover:border-l-warning',
    iconHover: 'group-hover:text-warning',
  },
  danger: {
    bg: 'border-l-4 border-l-danger/80',
    icon: 'text-danger',
    bgHover: 'hover:border-l-danger',
    iconHover: 'group-hover:text-danger',
  },
};

/** StatCard 组件的 Props 定义（组件入参，随实现绑定，故用 Props 后缀）。 */
export interface StatCardProps {
  /** 指标标签（如 "Total Return" / "总收益"），必填 */
  label: string;
  /** 指标数值，可为字符串或 JSX 节点，必填 */
  value: ReactNode;
  /** 辅助说明文案（如 "Up 5% vs last month"），可选 */
  hint?: ReactNode;
  /** 可选的右侧图标（如趋势图标），接受任意 ReactNode，可选 */
  icon?: ReactNode;
  /** 视觉变体，决定左侧强调条与图标颜色，默认 'default' */
  variant?: StatCardVariant;
  /** 网格序号，从 0 起算，用于入场动画错位延迟（每个延迟 0.05s），默认 0 */
  ordinal?: number;
  /** 透传的额外类名（追加而非覆盖），可选 */
  className?: string;
}

/**
 * 渲染单个指标卡片。
 * 以纵向结构展示 label（大写小标签）、value（大号数值）与可选 hint（辅助说明），右侧展示可选 icon；
 * variant 决定左侧强调条与图标颜色。组件通过 motion 在挂载时淡入上移，ordinal 控制错位延迟以实现逐个入场。
 *
 * @param props - 组件属性，详见 StatCardProps
 * @returns 带色调强调条的指标卡片
 */
export function StatCard({
  label,
  value,
  hint,
  icon,
  variant = 'default',
  ordinal = 0,
  className,
}: StatCardProps) {
  const { bg, icon: iconColor, bgHover, iconHover } = VARIANT_STYLES[variant];
  return (
    <motion.div
      // 入场动画：淡入 + 上移，按 ordinal 错位延迟逐个加载
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut', delay: ordinal * 0.05 }}
      className={cn(
        'group rounded-lg border border-subtle bg-card/75 p-4',
        'transition-[background-color,border-color] duration-[600ms] hover:bg-card',
        bg,
        bgHover,
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {/* 标签 */}
          <p className="text-xs uppercase tracking-[0.22em] text-secondary-text">{label}</p>
          {/* 数值 */}
          <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
          {/* 辅助说明 */}
          {hint ? <div className="mt-2 text-sm text-secondary-text">{hint}</div> : null}
        </div>
        {/* 右侧图标：按 variant 着色（如趋势类图标） */}
        {icon ? <div className={cn(iconColor, 'transition-colors', iconHover)}>{icon}</div> : null}
      </div>
    </motion.div>
  );
}
