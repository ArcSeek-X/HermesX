/**
 * ===================================
 * 指标卡片组件（StatCard）
 * ===================================
 *
 * 【功能介绍】
 * 用于展示单个「关键指标」的紧凑卡片（如总收益、回撤、胜率等）。
 * 统一承载：标签（label）、数值（value）、辅助说明（hint）、可选的右侧图标（icon），
 * 并通过 tone 控制左边框色调以表达指标语义（常态 / 主色 / 成功 / 警告 / 危险）。
 *
 * 【设计要点】
 * 1. 语义化色调：tone 映射到对应的边框颜色（如 success 偏绿、danger 偏红），
 *    在不引入图表的情况下以低成本传达指标好坏。
 * 2. 布局：标题行（label 大写小字）在上、数值（大号加粗）居中、hint 在下的纵向结构；
 *    右侧预留 icon 位（一般用于趋势箭头 / 图标）。
 * 3. 视觉风格：圆角卡片 + 半透明背景（bg-card/75）+ 柔和阴影，与全站卡片一致。
 * 4. 数值类型宽松：value / hint 接受 React.ReactNode，可传入富文本、JSX 甚至迷你图。
 *
 * 【使用方式】
 *   <StatCard label="总收益" value="+12.3%" hint="较上月 +5%" tone="success" icon={<TrendUp/>} />
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** StatCard 组件的 Props 定义 */
interface StatCardProps {
  /** 指标标签（如 "Total Return" / "总收益"） */
  label: string;
  /** 指标数值，可为字符串或 JSX 节点 */
  value: React.ReactNode;
  /** 辅助说明文案（如 "Up 5% vs last month"） */
  hint?: React.ReactNode;
  /** 可选的右侧图标（如趋势图标） */
  icon?: React.ReactNode;
  /** 色调变体，影响左边框颜色，默认 default */
  tone?: 'default' | 'primary' | 'success' | 'warning' | 'danger';
  /** 透传的额外类名 */
  className?: string;
}

/** 各 tone 对应的左边框颜色样式 */
const toneStyles = {
  default: 'border-subtle',
  primary: 'border-cyan/18',
  success: 'border-success/18',
  warning: 'border-warning/18',
  danger: 'border-danger/18',
};

/**
 * 指标卡片组件：紧凑展示一个关键指标的数值与说明。
 *
 * @param props - 组件属性
 * @param props.label - 标签
 * @param props.value - 数值
 * @param props.hint - 辅助说明
 * @param props.icon - 图标
 * @param props.tone - 色调
 * @param props.className - 额外类名
 * @returns 带色调边框的指标卡片
 */
export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  hint,
  icon,
  tone = 'default',
  className = '',
}) => {
  return (
    // 卡片容器：圆角 + 半透明背景 + 柔和阴影 + tone 边框
    <div className={cn('rounded-2xl border bg-card/75 p-4 shadow-soft-card', toneStyles[tone], className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          {/* 标签：大写小字，弱化的次级文字 */}
          <p className="text-xs uppercase tracking-[0.22em] text-secondary-text">{label}</p>
          {/* 数值：大号加粗前景色 */}
          <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
          {/* 辅助说明：可选，次级文字 */}
          {hint ? <div className="mt-2 text-sm text-secondary-text">{hint}</div> : null}
        </div>
        {/* 右侧图标：主色高亮（如趋势类图标） */}
        {icon ? <div className="text-cyan">{icon}</div> : null}
      </div>
    </div>
  );
};
