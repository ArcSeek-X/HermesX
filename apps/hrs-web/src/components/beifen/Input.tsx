/**
 * Input —— 通用表单输入组件（基础层）。
 *
 * 定位与适用范围：
 * - 面向「大表单」场景（登录页、设置表单），内置 label / hint / error 状态与
 *   完整的 aria 无障碍接线。
 * - 高度固定（h-11），不适用于紧凑型搜索框（如板块搜索的 py-1 text-xs），
 *   此类场景请保留内联 <input>。
 * - 内置前导图标仅覆盖 password / key；如需自定义图标（如 Search），
 *   需扩展 `iconType`，当前暂不支持。
 */
import type React from 'react';
import { useId, useState } from 'react';
import { Lock, Key } from 'lucide-react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';
import { EyeToggleIcon } from '../common/EyeToggleIcon';

/**
 * Input 的 Props。继承原生 input 属性 —— 所有原生属性都会透传给内部 <input>。
 */
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  trailingAction?: React.ReactNode;
  /** 选择输入框的视觉外观。 */
  appearance?: 'default' | 'login';
  /** 启用内置的密码可见性切换按钮。 */
  allowTogglePassword?: boolean;
  /** 控制前导图标样式。 */
  iconType?: 'password' | 'key' | 'none';
  /** 允许外部控制密码可见性状态。 */
  passwordVisible?: boolean;
  /** 受控模式下可见性变化时通知父组件。 */
  onPasswordVisibleChange?: (visible: boolean) => void;
}

/**
 * 兼容受控 / 非受控的文本输入组件。
 * - label、hint、error 均为可选，组件本身不渲染表单控件包裹层。
 * - 设置 `allowTogglePassword` 后，密码输入框自带可见性切换按钮。
 */
export const Input = ({ 
  label, 
  hint, 
  error, 
  className = '', 
  id, 
  trailingAction, 
  appearance = 'default',
  allowTogglePassword,
  iconType = 'none',
  passwordVisible,
  onPasswordVisibleChange,
  ...props 
}: InputProps) => {
  const { t } = useUiLanguage();
  const generatedId = useId();

  // 按 id -> name -> 自动生成的顺序解析输入框 id，保证 label / aria 关联始终有效。
  const inputId = id ?? props.name ?? generatedId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  // 合并调用方传入的 aria-describedby 与 hint / error 的 id，供屏幕阅读器使用。
  const describedBy = [props['aria-describedby'], errorId ?? hintId].filter(Boolean).join(' ') || undefined;
  const ariaInvalid = props['aria-invalid'] ?? (error ? true : undefined);

  const [isPasswordVisible, setIsPasswordVisible] = useState(false);

  // 密码可见性由组件自管理，或通过 `passwordVisible` 由外部控制。
  const isPasswordInput = props.type === 'password';
  const isVisibilityControlled = typeof passwordVisible === 'boolean';
  const isLoginAppearance = appearance === 'login';
  const visible = isVisibilityControlled ? passwordVisible : isPasswordVisible;
  const effectiveType = isPasswordInput && allowTogglePassword && visible ? 'text' : props.type;

  // 前导图标仅作装饰（禁用 pointer-events）；目前只内置 password / key 两种。
  const renderLeadingIcon = () => {
    if (iconType === 'password') {
      return (
        <Lock
          className={cn(
            'h-4 w-4',
            isLoginAppearance ? 'text-[var(--login-input-icon)]' : 'text-muted-text/55'
          )}
        />
      );
    }
    if (iconType === 'key') {
      return (
        <Key
          className={cn(
            'h-4 w-4',
            isLoginAppearance ? 'text-[var(--login-input-icon)]' : 'text-muted-text/55'
          )}
        />
      );
    }
    return null;
  };

  const leadingIcon = renderLeadingIcon();

  // 出错时用错误色覆盖聚焦边框 / 聚焦光环的 CSS 变量。
  const inputStyle = error
    ? {
      ...props.style,
      ['--input-surface-border-focus' as string]: 'hsla(var(--destructive), 0.4)',
      ['--input-surface-focus-ring' as string]: '0 0 0 4px hsla(var(--destructive), 0.1)',
    }
    : props.style;

  // 内置的密码可见性切换按钮；自定义 `trailingAction` 优先级更高。
  const defaultTrailingAction = isPasswordInput && allowTogglePassword ? (
    <button
      type="button"
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-200 focus:outline-none focus:ring-2',
        isLoginAppearance
          ? visible
            ? 'border-[var(--login-input-toggle-active-border)] bg-[var(--login-input-toggle-active-bg)] text-[var(--login-input-toggle-active-text)] shadow-[0_0_14px_var(--login-accent-glow)] focus:ring-[var(--login-input-toggle-ring)]'
            : 'border-[var(--login-input-toggle-border)] bg-[var(--login-input-toggle-bg)] text-[var(--login-input-toggle-text)] hover:border-[var(--login-input-toggle-border-hover)] hover:bg-[var(--login-input-toggle-bg-hover)] hover:text-[var(--login-input-toggle-text-hover)] focus:ring-[var(--login-input-toggle-ring)]'
          : visible
            ? 'border-warning/40 bg-warning/15 text-warning shadow-[0_0_10px_hsla(var(--warning),0.15)]'
            : 'border-border/40 bg-muted/20 text-muted-text hover:border-warning/40 hover:text-warning hover:shadow-[0_0_10px_hsla(var(--warning),0.15)] focus:ring-primary/30'
      )}
      onClick={() => {
        const nextVisible = !visible;
        if (!isVisibilityControlled) {
          setIsPasswordVisible(nextVisible);
        }
        onPasswordVisibleChange?.(nextVisible);
      }}
      aria-label={visible ? t('common.hideContent') : t('common.showContent')}
      tabIndex={-1}
    >
      <EyeToggleIcon visible={visible} />
    </button>
  ) : null;

  const finalTrailingAction = trailingAction || defaultTrailingAction;

  // 布局结构：可选 label -> 输入行（前导图标 / 尾部操作）-> error 或 hint。
  return (
    <div className="flex flex-col">
      {label ? (
        <label
          htmlFor={inputId}
          className={cn(
            'mb-2 text-sm font-medium',
            isLoginAppearance ? 'text-[var(--login-label-text)]' : 'text-foreground'
          )}
        >
          {label}
        </label>
      ) : null}
      <div className="relative flex items-center">
        {leadingIcon && (
          <div className="absolute left-3.5 z-10 pointer-events-none">
            {leadingIcon}
          </div>
        )}
        <input
          id={inputId}
          aria-describedby={describedBy}
          aria-invalid={ariaInvalid}
          style={inputStyle}
          data-appearance={appearance}
          className={cn(
            'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all',
            'focus:outline-none',
            isLoginAppearance ? 'input-appearance-login' : '',
            error ? 'border-danger/30' : '',
            leadingIcon ? 'pl-10' : '',
            finalTrailingAction ? 'pr-12' : '',
            'disabled:cursor-not-allowed disabled:opacity-60',
            className,
          )}
          {...props}
          type={effectiveType}
        />
        {finalTrailingAction ? (
          <div className="absolute inset-y-0 right-2 flex items-center">
            {finalTrailingAction}
          </div>
        ) : null}
      </div>
      {error ? (
        <p
          id={errorId}
          role="alert"
          className={cn(
            'mt-2 text-xs',
            isLoginAppearance ? 'text-[var(--login-error-text)]' : 'text-danger'
          )}
        >
          {error}
        </p>
      ) : hint ? (
        <p
          id={hintId}
          className={cn(
            'mt-2 text-xs',
            isLoginAppearance ? 'text-[var(--login-hint-text)]' : 'text-secondary-text'
          )}
        >
          {hint}
        </p>
      ) : null}
    </div>
  );
};
