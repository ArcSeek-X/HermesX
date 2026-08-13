/**
 * ===================================
 * 状态指示点组件（StatusDot）
 * ===================================
 *
 * 【功能介绍】
 * 一个小型「状态指示点」，用不同颜色 + 可选脉冲动画来表示某项状态（在线 / 警告 / 错误 / 信息等）。
 * 常用于列表、标签、连接状态等需要以最小视觉成本传达状态的场景。
 *
 * 【设计要点】
 * 1. 语义化色调：内置 success / warning / danger / info / neutral 五种色调，每种带柔和外发光
 *    （box-shadow 环），提升辨识度。
 * 2. 无障碍处理：默认 aria-hidden=true（纯装饰性点），当调用方显式传入非空 aria-label 时，
 *    取消 aria-hidden，让辅助技术可读取状态文案，实现「装饰/语义」自动切换。
 * 3. 透传原生属性：通过 ...rest 继承 React.HTMLAttributes<HTMLSpanElement>，
 *    可传入 title、aria-*、onClick 等，灵活性高。
 * 4. 脉冲动画：pulse=true 时叠加 animate-pulse，用于强调「进行中 / 活跃」状态。
 *
 * 【使用方式】
 *   <StatusDot tone="success" />
 *   <StatusDot tone="danger" pulse aria-label="连接已断开" />
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** 状态点色调类型 */
type StatusDotTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

/** StatusDot 组件的 Props 定义（继承原生 span 属性） */
interface StatusDotProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** 状态色调，默认 neutral */
  tone?: StatusDotTone;
  /** 是否启用脉冲动画（强调活跃/进行中状态） */
  pulse?: boolean;
  /** 透传的额外类名 */
  className?: string;
}

/** 各色调对应的样式：背景色 + 柔和外发光环 */
const TONE_STYLES: Record<StatusDotTone, string> = {
  success: 'bg-success shadow-[0_0_0_3px_hsl(var(--success)/0.12)]',
  warning: 'bg-warning shadow-[0_0_0_3px_hsl(var(--warning)/0.14)]',
  danger: 'bg-danger shadow-[0_0_0_3px_hsl(var(--destructive)/0.12)]',
  info: 'bg-cyan shadow-[0_0_0_3px_hsl(var(--primary)/0.12)]',
  neutral: 'bg-muted-text shadow-[0_0_0_3px_hsl(var(--muted-text)/0.12)]',
};

/**
 * 状态指示点组件。
 *
 * @param props - 组件属性
 * @param props.tone - 色调
 * @param props.pulse - 是否脉冲
 * @param props.className - 额外类名
 * @param props....rest - 其余原生 span 属性
 * @returns 一个带色调与外发光的状态点
 */
export const StatusDot: React.FC<StatusDotProps> = ({
  tone = 'neutral',
  pulse = false,
  className = '',
  ...rest
}) => {
  // 仅当显式提供非空 aria-label 时，才允许屏幕阅读器读取（否则视为纯装饰）
  const hasAccessibleLabel = typeof rest['aria-label'] === 'string' && rest['aria-label'].length > 0;

  return (
    <span
      {...rest}
      aria-hidden={hasAccessibleLabel ? undefined : true}
      className={cn(
        'inline-flex h-2.5 w-2.5 shrink-0 rounded-full',
        TONE_STYLES[tone],
        pulse ? 'animate-pulse' : '',
        className,
      )}
    />
  );
};
