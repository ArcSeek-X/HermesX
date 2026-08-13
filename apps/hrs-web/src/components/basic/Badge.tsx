/**
 * ===================================
 * 标签徽章组件（Badge）
 * ===================================
 *
 * 作用：
 * 显示小型状态标签，支持多种颜色变体和发光效果：
 * - default：默认灰色
 * - success：成功绿色
 * - warning：警告黄色
 * - danger：危险红色
 * - info：信息青色
 * - history：历史紫色
 */
import React from 'react';
import { cn } from '../../utils/cn';

/** 徽章颜色变体类型 */
type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'history';

/** Badge 组件的属性定义 */
interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** 徽章显示内容 */
  children: React.ReactNode;
  /** 颜色变体 */
  variant?: BadgeVariant;
  /** 尺寸：sm 小 / md 中 */
  size?: 'sm' | 'md';
  /** 是否启用发光阴影效果 */
  glow?: boolean;
  /** 自定义 CSS 类名 */
  className?: string;
  /** 内联样式 */
  style?: React.CSSProperties;
}

/** 各变体对应的边框、背景、文字颜色 */
const variantStyles: Record<BadgeVariant, string> = {
  default: 'border-border/55 bg-elevated/75 text-secondary-text',
  success: 'border-success/20 bg-success/10 text-success',
  warning: 'border-warning/20 bg-warning/10 text-warning',
  danger: 'border-danger/20 bg-danger/10 text-danger',
  info: 'border-cyan/30 bg-cyan/12 text-cyan',
  history: 'border-purple/20 bg-purple/10 text-purple',
};

/** 各变体对应的发光阴影颜色 */
const glowStyles: Record<BadgeVariant, string> = {
  default: '',
  success: 'shadow-success/20',
  warning: 'shadow-warning/20',
  danger: 'shadow-danger/20',
  info: 'shadow-cyan/20',
  history: 'shadow-purple/20',
};

/**
 * 标签徽章组件
 *
 * 渲染一个圆角胶囊状的标签，支持 6 种颜色变体和可选的发光效果。
 *
 * @param props - 组件属性
 * @returns 带颜色和样式的标签徽章
 */
export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  glow = false,
  className = '',
  style,
  ...rest
}) => {
  // 尺寸对应的内边距和字体大小
  const sizeStyles = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  return (
    <span
      {...rest}
      style={style}
      className={cn(
        // 基础样式：圆角胶囊 + 边框 + 半透明背景 + 毛玻璃
        'inline-flex items-center gap-1 rounded-full border font-medium backdrop-blur-sm',
        sizeStyles,
        variantStyles[variant],
        glow && `shadow-lg ${glowStyles[variant]}`,
        className,
      )}
    >
      {children}
    </span>
  );
};
