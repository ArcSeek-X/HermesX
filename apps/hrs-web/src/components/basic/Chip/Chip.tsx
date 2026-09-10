/**
 * Chip.tsx —— 通用标签芯片（圆角胶囊标签）。
 *
 * 作用：渲染圆角胶囊状标签，支持 variant / color / size / radius 组合、
 * 关闭按钮（onClose）与禁用态（isDisabled）。
 * 使用场景：分类 / 状态标记、筛选器已选条目（带 × 取消）、消息日历条目角标等；
 * 内容（图标、文字）由调用方通过 children 自行组合。
 *
 * 实现说明：API 对齐 HeroUI Chip，但本项目未引入 HeroUIProvider（无主题 CSS 变量注入），
 * 故样式改用项目自管的 Tailwind 语义色实现，保证在浅色 / 深色主题下真实上色；
 * props 名称与取值严格对齐 HeroUI，便于未来平滑迁移。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import React from 'react';
import { Xmark } from '@gravity-ui/icons';
import { cn } from '../../../utils/cn';

/** 视觉风格变体 */
type ChipVariant = 'primary' | 'secondary' | 'tertiary' | 'soft';
/** 语义色 */
type ChipColor = 'default' | 'accent' | 'success' | 'warning' | 'danger' | 'blue' | 'purple' | 'indigo';
/** 尺寸档位 */
type ChipSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
/** 圆角档位 */
type ChipRadius = 'full' | 'sm' | 'md' | 'lg';

/** Chip 组件属性（对齐 HeroUI Chip API） */
export interface ChipProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'onClose'> {
  /** 芯片显示内容（图标、文字等由调用方组合传入，必填） */
  children: React.ReactNode;
  /** 视觉风格变体，默认 'primary' */
  variant?: ChipVariant;
  /** 语义色，默认 'default' */
  color?: ChipColor;
  /** 尺寸，默认 'md' */
  size?: ChipSize;
  /** 圆角，默认 'full'（胶囊） */
  radius?: ChipRadius;
  /** 是否禁用，默认 false */
  isDisabled?: boolean;
  /** 关闭回调：传入时渲染关闭按钮，默认不渲染 */
  onClose?: () => void;
  /** 自定义 CSS 类名（作用于根元素），默认为空 */
  className?: string;
}

/**
 * variant × color 组合对应的边框 / 背景 / 文字颜色（项目语义色变量，跟随主题变化）。
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

/** 各尺寸对应的高度 / 内边距 / 字号 */
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
 * 标签芯片组件。
 * @param props - 组件属性，见 ChipProps（children / variant / color / size / radius / isDisabled / onClose / className）
 * @returns 带样式与可选关闭按钮的 <span> 标签芯片
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
  // 芯片内容：children + 可选关闭按钮（×）
  const content = (
    <>
      {children}
      {onClose && (
        <button
          type="button"
          aria-label="关闭"
          disabled={isDisabled}
          // 关闭按钮可能嵌在可按压容器内（如下拉触发器 <button>）：react-aria 的 press 由
          // pointerdown 驱动，不拦住会让容器触发 press（弹层被打开）并吞掉本按钮的 click
          onPointerDown={(e) => e.stopPropagation()}
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
