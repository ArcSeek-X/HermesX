/**
 * ===================================
 * 卡片容器组件（Card）
 * ===================================
 *
 * 作用：
 * 提供多种视觉风格的卡片容器，用于包裹页面中的内容区块：
 * - default：默认终端风格卡片
 * - bordered：带边框的卡片
 * - gradient：渐变边框卡片
 * 支持标题、副标题、悬停效果和多种内边距规格。
 */
import type React from 'react';
import { cn } from '../../utils/cn';

/** Card 组件的属性定义 */
interface CardProps {
  /** 卡片标题 */
  title?: string;
  /** 卡片副标题（显示在标题上方） */
  subtitle?: string;
  /** 卡片内容 */
  children: React.ReactNode;
  /** 自定义 CSS 类名 */
  className?: string;
  /** 内联样式 */
  style?: React.CSSProperties;
  /** 卡片视觉风格：default 默认 / bordered 边框 / gradient 渐变 */
  variant?: 'default' | 'bordered' | 'gradient';
  /** 是否启用悬停效果 */
  hoverable?: boolean;
  /** 内边距规格：none 无 / sm 小 / md 中 / lg 大 */
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

/**
 * 卡片容器组件
 *
 * 根据 variant 属性渲染不同风格的卡片：
 * - gradient 模式使用双层 div 实现渐变边框效果
 * - default/bordered 模式使用单层 div，通过 CSS 类区分
 *
 * @param props - 组件属性
 * @returns 带标题和内容区域的卡片容器
 */
export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  className = '',
  style,
  variant = 'default',
  hoverable = false,
  padding = 'md',
}) => {
  // 内边距样式映射
  const paddingStyles = {
    none: '',
    sm: 'p-4',
    md: 'p-5',
    lg: 'p-6',
  };

  // 视觉风格对应的 CSS 类名
  const variantStyles = {
    default: 'terminal-card',
    bordered: 'terminal-card',
    gradient: 'gradient-border-card',
  };

  // 悬停效果样式
  const hoverStyles = hoverable ? 'terminal-card-hover cursor-pointer' : '';

  // 渐变模式：需要外层容器实现渐变边框
  if (variant === 'gradient') {
    return (
      <div className={cn(variantStyles.gradient, className)} style={style}>
        <div className={cn('gradient-border-card-inner', paddingStyles[padding])}>
          {(title || subtitle) && (
            <div className="mb-3">
              {subtitle ? <span className="label-uppercase">{subtitle}</span> : null}
              {title ? <h3 className="mt-1 text-lg font-semibold text-foreground">{title}</h3> : null}
            </div>
          )}
          {children}
        </div>
      </div>
    );
  }

  // 默认/边框模式：单层 div
  return (
    <div
      style={style}
      className={cn('rounded-2xl', variantStyles[variant], hoverStyles, paddingStyles[padding], className)}
    >
      {(title || subtitle) && (
        <div className="mb-3">
          {subtitle ? <span className="label-uppercase">{subtitle}</span> : null}
          {title ? <h3 className="mt-1 text-lg font-semibold text-foreground">{title}</h3> : null}
        </div>
      )}
      {children}
    </div>
  );
};
