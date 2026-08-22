/**
 * ===================================
 * 标签芯片组件（Chip）
 * ===================================
 *
 * 基于 HeroUI Chip 组件的 API 契约封装（https://heroui.com/en/docs/react/components/chip）。
 * 组件支持 HeroUI Chip 的核心能力与取值：
 *   - variant: primary | secondary | tertiary | soft（视觉风格，默认 secondary）
 *   - color:   default | accent | success | warning | danger | blue | purple | indigo（语义色，默认 default）
 *   - size:    sm | md | lg（尺寸，默认 md）
 *   - radius:  full | sm | md | lg（圆角，默认 full 胶囊）
 *   - onClose：渲染关闭按钮并回调
 *   - isDisabled：禁用态
 *   - children：芯片内容（图标、文字等由调用方自行组合传入）
 *
 * 说明：本项目未引入 HeroUIProvider，HeroUI 语义类依赖其主题 CSS 变量注入才会上色，
 * 故此处用项目自管的 Tailwind 语义色（与 Badge 一致）实现渲染，保证在当前主题下真实生效、
 * 且跟随浅色/深色主题变化。props 名称与取值严格对齐 HeroUI，便于未来平滑迁移。
 */
import React from 'react';
import { Xmark } from '@gravity-ui/icons';
import { cn } from '../../utils/cn';

/** 视觉风格变体 */
type ChipVariant = 'primary' | 'secondary' | 'tertiary' | 'soft';
/** 语义色 */
type ChipColor = 'default' | 'accent' | 'success' | 'warning' | 'danger' | 'blue' | 'purple' | 'indigo';
/** 尺寸 */
type ChipSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
/** 圆角 */
type ChipRadius = 'full' | 'sm' | 'md' | 'lg';

/** Chip 组件的属性定义（对齐 HeroUI Chip API） */
export interface ChipProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'onClose'> {
  /** 芯片显示内容 */
  children: React.ReactNode;
  /** 视觉风格变体 */
  variant?: ChipVariant;
  /** 语义色 */
  color?: ChipColor;
  /** 尺寸 */
  size?: ChipSize;
  /** 圆角 */
  radius?: ChipRadius;
  /** 是否禁用 */
  isDisabled?: boolean;
  /** 关闭回调：传入时渲染关闭按钮 */
  onClose?: () => void;
  /** 自定义 CSS 类名（作用于根元素） */
  className?: string;
}

/**
 * variant × color 组合对应的边框/背景/文字颜色。
 * 采用项目语义色变量，跟随主题色变化。
 */
const variantColorStyles: Record<ChipVariant, Record<ChipColor, string>> = {
  primary: {
    default: 'border-primary/30 bg-primary/15 text-primary',
    accent: 'border-primary/30 bg-primary/15 text-primary',
    success: 'border-success/30 bg-success/15 text-success',
    warning: 'border-warning/30 bg-warning/15 text-warning',
    danger: 'border-danger/30 bg-danger/15 text-danger',
    blue: 'border-blue-500/40 bg-blue-500/20 text-blue-600',
    purple: 'border-purple-500/25 bg-purple-500/12 text-purple-600/90',
    indigo: 'border-indigo-500/40 bg-indigo-500/20 text-indigo-600',
  },
  secondary: {
    default: 'border-border/55 bg-elevated/75 text-secondary-text',
    accent: 'border-primary/30 bg-primary/12 text-primary',
    success: 'border-success/25 bg-success/10 text-success',
    warning: 'border-warning/25 bg-warning/10 text-warning',
    danger: 'border-danger/25 bg-danger/10 text-danger',
    blue: 'border-blue-500/30 bg-blue-500/12 text-blue-600',
    purple: 'border-purple-500/18 bg-purple-500/8 text-purple-600/80',
    indigo: 'border-indigo-500/30 bg-indigo-500/12 text-indigo-600',
  },
  tertiary: {
    default: 'border-border/40 bg-elevated/60 text-muted-text',
    accent: 'border-primary/20 bg-primary/8 text-primary/80',
    success: 'border-success/20 bg-success/8 text-success/90',
    warning: 'border-warning/20 bg-warning/8 text-warning/90',
    danger: 'border-danger/20 bg-danger/8 text-danger/90',
    blue: 'border-blue-500/20 bg-blue-500/8 text-blue-600/90',
    purple: 'border-purple-500/12 bg-purple-500/5 text-purple-600/75',
    indigo: 'border-indigo-500/20 bg-indigo-500/8 text-indigo-600/90',
  },
  soft: {
    default: 'border-transparent bg-elevated/70 text-secondary-text',
    accent: 'border-transparent bg-primary/10 text-primary',
    success: 'border-transparent bg-success/10 text-success',
    warning: 'border-transparent bg-warning/10 text-warning',
    danger: 'border-transparent bg-danger/10 text-danger',
    blue: 'border-transparent bg-blue-500/15 text-blue-600',
    purple: 'border-transparent bg-purple-500/10 text-purple-600/90',
    indigo: 'border-transparent bg-indigo-500/15 text-indigo-600',
  },
};

/** 各尺寸对应的内边距与字号 */
const sizeStyles: Record<ChipSize, string> = {
  xs: 'h-5 px-1.5 text-[11px] gap-0.5',
  sm: 'h-6 px-2 text-xs gap-1',
  md: 'h-7 px-2.5 text-xs gap-1.5',
  lg: 'h-8 px-3 text-sm gap-1.5',
  xl: 'h-9 px-3.5 text-sm gap-2',
};

/** 圆角映射 */
const radiusStyles: Record<ChipRadius, string> = {
  full: 'rounded-full',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
};

/**
 * 标签芯片组件
 *
 * 渲染一个圆角胶囊状的标签，支持 variant/color/size/radius 组合、
 * 关闭按钮与禁用态。API 对齐 HeroUI Chip，样式由项目自管语义色实现；
 * 内容（图标、文字等）由调用方通过 children 自行组合传入。
 *
 * @param props - 组件属性
 * @returns 带样式与可变槽位的标签芯片
 */
export const Chip: React.FC<ChipProps> = ({
  children,
  variant = 'primary',
  color = 'default',
  size = 'md',
  radius = 'full',
  isDisabled = false,
  onClose,
  className = '',
  ...nativeProps
}) => {
  const content = (
    <>
      {children}
      {onClose && (
        <button
          type="button"
          aria-label="关闭"
          disabled={isDisabled}
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          className="ml-0.5 inline-flex shrink-0 items-center justify-center rounded-full text-current/70 transition-colors hover:bg-current/10 hover:text-current"
        >
          <Xmark className="h-3.5 w-3.5" />
        </button>
      )}
    </>
  );

  return (
    <span
      {...nativeProps}
      aria-disabled={isDisabled || undefined}
      className={cn(
        // 基础样式：内联胶囊 + 边框 + 半透明背景 + 毛玻璃
        'inline-flex items-center border font-medium backdrop-blur-sm select-none',
        sizeStyles[size],
        radiusStyles[radius],
        variantColorStyles[variant][color],
        isDisabled && 'cursor-not-allowed opacity-50',
        className,
      )}
    >
      {content}
    </span>
  );
};

export default Chip;
