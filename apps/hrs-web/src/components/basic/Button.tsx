/**
 * Button.tsx
 * ------------------------------------------------------------
 * 文件作用：
 *   通用按钮组件。封装了项目统一的按钮视觉风格（终端/科技感主题）、
 *   多种语义化变体（主操作、次操作、描边、危险、设置面板专用等）、
 *   多档尺寸、加载态（loading）与发光（glow）效果。
 *   是前端各处按钮的唯一推荐入口，避免在业务代码里手写重复的按钮样式。
 *
 * 设计要点：
 *   - 通过 variant 选择视觉风格，通过 size 选择尺寸档位；
 *   - 所有按钮自带 focus-visible 焦点环、disabled 禁用态、过渡动画；
 *   - 支持 loading 态（显示旋转图标 + 文案），loading 时自动禁用按钮；
 *   - 通过 className 透传，可在使用时追加 / 覆盖样式（合并进 cn）；
 *   其余原生 button 属性（onClick、type、aria-* 等）均透传。
 * ------------------------------------------------------------
 */

import React from 'react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';

/**
 * 按钮属性。
 * 继承自原生 <button> 的所有属性（onClick / type / disabled / aria-* 等均可直接使用），
 * 并在此基础上扩展了以下项目专用字段。
 */
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** 视觉变体（语义化风格），默认 'primary'。各变体样式见 BUTTON_VARIANT_STYLES。 */
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'gradient' | 'danger' | 'danger-subtle' | 'settings-primary' | 'settings-secondary' | 'action-primary' | 'action-secondary' | 'home-action-ai' | 'home-action-report';
  /** 尺寸档位，默认 'md'。各档位高度/内边距/字号见 BUTTON_SIZE_STYLES。 */
  size?: 'xsm' | 'sm' | 'md' | 'lg' | 'xl';
  /** 是否处于加载态。为 true 时展示旋转图标与文案，且按钮被禁用。默认 false。 */
  isLoading?: boolean;
  /** 加载态自定义文案；未提供时回退到 i18n 的 'common.processing'。 */
  loadingText?: string;
  /** 是否启用青色发光效果（glow）。默认 false。 */
  glow?: boolean;
}

/**
 * 各尺寸档位对应的 Tailwind 类名（高度、圆角、内边距、字号）。
 * 注：字号使用 !text-xs / text-sm，! 用于对抗 index.css 中
 * 未分层的 `button { font: inherit }` 规则，确保字号稳定生效。
 */
const BUTTON_SIZE_STYLES = {
  xsm: 'h-6 rounded-xsm px-2 !text-xs',
  sm: 'h-7 rounded-sm px-3 !text-xs',
  md: 'h-8 rounded-md px-4 !text-xs',
  lg: 'h-10 rounded-xl px-5 text-sm',
  xl: 'h-12 rounded-xl px-6 text-sm',
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
 *   - 危险类：danger（实心红）、danger-subtle（淡红描边）
 *   - 业务专用：action-primary / action-secondary / home-action-ai / home-action-report（首页 workspace 用）
 */
const BUTTON_VARIANT_STYLES = {
  primary: 'border border-cyan/30 bg-primary-gradient text-primary-foreground shadow-lg shadow-cyan/20 hover:brightness-105',
  secondary: 'border border-border/70 bg-card text-foreground shadow-soft-card hover:bg-hover',
  'settings-primary': 'border settings-button-primary hover:brightness-105 hover:shadow-xl',
  'settings-secondary': 'border settings-button-secondary hover:translate-y-[-1px]',
  outline: 'border border-cyan/25 bg-transparent text-cyan hover:bg-cyan/10',
  ghost: 'border border-transparent bg-transparent text-secondary-text hover:bg-hover hover:text-foreground',
  gradient: 'border border-cyan/20 bg-gradient-to-r from-cyan to-purple text-primary-foreground shadow-lg shadow-cyan/20 hover:brightness-105',
  danger: 'border border-danger/40 bg-danger text-destructive-foreground shadow-lg shadow-danger/20 hover:brightness-105',
  'danger-subtle': 'border border-danger/60 bg-danger/10 text-danger hover:bg-danger/15',
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
export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  loadingText,
  glow = false,
  className = '',
  disabled,
  type = 'button',
  ...props
}) => {
  // 用于读取 i18n 文案（loading 默认文案等）
  const { t } = useUiLanguage();
  // 发光效果对应的附加类名（为空字符串时不影响结果）
  const glowStyles = glow ? 'shadow-glow-cyan settings-glow-cyan-hover' : '';

  return (
    <button
      type={type}
      // 加载态标记，供辅助技术与样式识别
      aria-busy={isLoading || undefined}
      // 记录当前变体，便于外部样式 / 调试区分
      data-variant={variant}
      className={cn(
        // 基础样式：内联弹性布局、居中、字重、过渡动画
        'hrs-button inline-flex cursor-pointer items-center justify-center gap-2 font-medium transition-all duration-200',
        // 键盘焦点环（可访问性）
        'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-cyan/15 focus-visible:ring-offset-0',
        // 禁用态：禁止事件、禁用光标、降透明度、取消位移
        'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 disabled:transform-none',
        // 尺寸档位样式
        BUTTON_SIZE_STYLES[size],
        // 视觉变体样式
        BUTTON_VARIANT_STYLES[variant],
        // 发光效果（可选）
        glowStyles,
        // 用户透传的 className（可追加或覆盖上述样式）
        className,
      )}
      // 显式禁用：父级 disabled 或处于 loading 时均禁用
      disabled={disabled || isLoading}
      {...props}
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
    </button>
  );
};
