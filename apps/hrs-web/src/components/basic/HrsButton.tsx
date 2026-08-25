/**
 * hrsButton.tsx
 * ------------------------------------------------------------
 * 文件作用：
 *   通用按钮组件，基于 HeroUI 的 Button 二次封装。在复用 HeroUI Button
 *   的底层能力（无障碍语义、focus 管理、pending 态、原生属性透传等）之上，
 *   保留项目统一的终端/科技感视觉风格、13 种语义化变体、5 档尺寸、
 *   加载态（loading）与发光（glow）效果。
 *   是前端各处按钮的唯一推荐入口，避免在业务代码里手写重复的按钮样式。
 *
 * 设计要点：
 *   - 底座为 HeroUI 的 <Button>（来自 @heroui/react），复用其 press 事件、
 *     pending 态、可访问性处理与原生属性透传；
 *   - 通过 variant 选择视觉风格，通过 size 选择尺寸档位；
 *   - 所有按钮自带 focus-visible 焦点环、disabled 禁用态、过渡动画；
 *   - 支持 loading 态（显示旋转图标 + 文案），loading 时自动禁用按钮；
 *   - 通过 className 透传，可在使用时追加 / 覆盖样式（合并进 cn）；
 *   其余原生 button 属性（onClick、type、aria-* 等）均透传。
 * ------------------------------------------------------------
 */

import React from 'react';
import { Button as HeroButton } from '@heroui/react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';

/**
 * 按钮属性。
 * 并在此基础上扩展了以下项目专用字段。
 */
/** HrsButton 支持的视觉变体（语义化风格）。各变体样式见 BUTTON_VARIANT_STYLES。 */
export type HrsButtonVariant = 'primary' | 'primary-soft' | 'secondary' | 'outline' | 'ghost' | 'gradient' | 'danger' | 'danger-soft' | 'success' | 'success-soft' | 'warning' | 'warning-soft' | 'settings-primary' | 'settings-secondary' | 'action-primary' | 'action-secondary' | 'home-action-ai' | 'home-action-report';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** 视觉变体（语义化风格），默认 'primary'。各变体样式见 BUTTON_VARIANT_STYLES。 */
  variant?: HrsButtonVariant;
  /** 尺寸档位，默认 'md'。各档位高度/内边距/字号见 BUTTON_SIZE_STYLES。 */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** 是否处于加载态。为 true 时展示旋转图标与文案，且按钮被禁用。默认 false。 */
  isLoading?: boolean;
  /** 加载态自定义文案；未提供时回退到 i18n 的 'common.processing'。 */
  loadingText?: string;
  /** 是否启用青色发光效果（glow）。默认 false。 */
  glow?: boolean;
  /** 是否禁用按钮（HeroUI 语义字段）。与原生 disabled 二选一，统一走 isDisabled 透传给 HeroUI。 */
  isDisabled?: boolean;
}

/**
 * 各尺寸档位对应的 Tailwind 类名（高度、圆角、内边距、字号、字重）。
 * 注：字号使用 !text-xs / text-sm，! 用于对抗 index.css 中
 * 未分层的 `button { font: inherit }` 规则，确保字号稳定生效。
 */
const BUTTON_SIZE_STYLES = {
  xs: 'h-7 rounded-sm px-2 !text-xs !font-medium',
  sm: 'h-8 rounded-sm px-3 !text-xs !font-medium',
  md: 'h-9 rounded-sm px-4 !text-xs !font-medium',
  lg: 'h-10 rounded-sm px-5 !text-sm !font-semibold',
  xl: 'h-12 rounded-sm px-6 !text-sm !font-bold',
} as const;

/**
 * 首页「AI 分析 / 报告」类操作的主色样式（基于 CSS 变量，跟随主题）。
 */
const ACTION_AI_STYLES = 'bg-[var(--home-action-ai-bg)] border border-[var(--home-action-ai-border)] text-[var(--home-action-ai-text)] hover:bg-[var(--home-action-ai-hover-bg)]';
/**
 * 首页「AI 分析 / 报告」类操作的报告（次）样式（基于 CSS 变量，跟随主题）。
 */
const ACTION_REPORT_STYLES = 'bg-[var(--home-action-report-bg)] border border-[var(--home-action-report-border)] text-[var(--home-action-report-text)] hover:bg-[var(--home-action-report-hover-bg)]';

/**
 * 各视觉变体对应的 Tailwind 类名。
 * 分组说明：
 *   - 主操作类：primary（主色渐变）、gradient（青→紫渐变）、settings-primary（设置面板主按钮，跟随 --primary）
 *   - 次操作类：secondary（卡片底 + 边框）、settings-secondary（设置面板次按钮，跟随 --primary）
 *   - 轻量类：outline（描边）、ghost（透明、最弱）
 *   - 危险类：danger（实心红）、danger-soft（淡红描边）
 *   - 业务专用：action-primary / action-secondary / home-action-ai / home-action-report（首页 workspace 用）
 */
const BUTTON_VARIANT_STYLES = {
  primary: 'border border-cyan/30 bg-gradient-cyan text-primary-foreground shadow-md shadow-cyan/20 hover:brightness-120',
  'primary-soft': 'border border-cyan/60 bg-cyan/10 text-cyan hover:bg-cyan/15',
  secondary: 'border border-cyan/25 bg-transparent text-cyan hover:bg-cyan/10',
  outline: ' bg-transparent text-foreground hover:bg-cyan/10 hover:bg-subtle',
  ghost: 'border-none bg-transparent text-foreground hover:bg-cyan/10 hover:bg-subtle',

  danger: 'border border-danger/40 bg-danger text-destructive-foreground shadow-md shadow-danger/20 hover:brightness-105',
  'danger-soft': 'border border-danger/60 bg-danger/10 text-danger hover:bg-danger/15',
  success: 'border border-success/40 bg-success text-destructive-foreground shadow-md shadow-success/20 hover:brightness-105',
  'success-soft': 'border border-success/60 bg-success/10 text-success hover:bg-success/15',
  warning: 'border border-warning/40 bg-warning text-destructive-foreground shadow-md shadow-warning/20 hover:brightness-105',
  'warning-soft': 'border border-warning/60 bg-warning/10 text-warning hover:bg-warning/15',


  'settings-primary': 'border settings-button-primary hover:brightness-105 hover:shadow-xl',
  'settings-secondary': 'border settings-button-secondary hover:translate-y-[-1px]',
  gradient: 'border border-cyan/20 bg-gradient-to-r from-cyan to-purple text-primary-foreground shadow-md shadow-cyan/20 hover:brightness-105',
  'action-primary': ACTION_AI_STYLES,
  'action-secondary': ACTION_REPORT_STYLES,
  'home-action-ai': ACTION_AI_STYLES,
  'home-action-report': ACTION_REPORT_STYLES,
} as const;

/**
 * 通用按钮组件。
 * 负责把 size / variant / glow / className 等合并为最终 className，
 * 并处理 loading 态（渲染旋转图标 + 文案）。
 */
export const HrsButton: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'sm',
  isLoading = false,
  loadingText,
  glow = false,
  className = '',
  isDisabled,
  type = 'button',
  onClick,
  ...props
}) => {
  // 用于读取 i18n 文案（loading 默认文案等）
  const { t } = useUiLanguage();
  // 发光效果对应的附加类名（为空字符串时不影响结果）
  const glowStyles = glow ? 'shadow-glow-cyan settings-glow-cyan-hover' : '';
  // 透传的原生 / 语义属性：data-variant 供外部样式与调试区分，
  // aria-busy 供辅助技术识别加载态；统一并入 props 透传给 HeroUI Button。
  const passthroughProps = {
    ...props,
    variant,
    'data-variant': variant,
    'aria-busy': isLoading || undefined,
    className: cn(
      // 基础样式：内联弹性布局、居中、过渡动画（字重由 fontWeight 属性控制）
      'hrs-button inline-flex cursor-pointer items-center justify-center gap-1 transition-all duration-200',
      // 键盘焦点环（可访问性）
      'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-cyan/15 focus-visible:ring-offset-0',
      // 禁用态：禁止事件、禁用光标、降透明度、取消位移
      'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 disabled:transform-none',
      // 尺寸档位样式（含字重）
      BUTTON_SIZE_STYLES[size],
      // 视觉变体样式（项目自定义 Tailwind 类，覆盖 HeroUI 默认 variant 外观）
      BUTTON_VARIANT_STYLES[variant],
      // 发光效果（可选）
      glowStyles,
      // 用户透传的 className（可追加或覆盖上述样式）
      className,
    ),
  } as React.ComponentProps<typeof HeroButton>;


  return (
    <HeroButton
      // 复用 HeroUI 底座：原生属性（aria-* / data-* / className 等）直接透传
      {...passthroughProps}
      // HeroUI 使用 onPress 而非 onClick，将 onClick 桥接到 onPress
      onPress={onClick ? () => onClick({} as React.MouseEvent<HTMLButtonElement>) : undefined}
      isDisabled={isDisabled || isLoading}
      // HeroUI 的 pending 态：加载期间禁止指针事件
      isPending={isLoading}
    >
      {isLoading ? (
        // 加载态：旋转 SVG 图标 + 文案
        <span className="flex items-center justify-center gap-2">
          <svg
            className="h-4 w-4 animate-spin text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          {/* 优先使用自定义 loading 文案，否则回退到通用「处理中」 */}
          {loadingText ?? t('common.processing')}
        </span>
      ) : (
        children
      )}
    </HeroButton>
  );
};
