/**
 * InputTest —— 通用输入框组件（基础层）。
 *
 * 支持以下输入框常用 API：
 * - prefix / suffix / allowClear / onClear / onPressEnter / size / clearIcon / maxLength
 * - status / variant / disabled
 * - 默认 size 为 `medium`
 *
 * 自有扩展（非标准 Input API）：
 * - label：可选表单标签，点击聚焦输入框
 * - hint：辅助提示文案
 * - error：错误文案（非空时输入框边框变红 + 错误文字 + aria-invalid=true）
 *
 * 原生 input 属性（除 `size` 外）全部透传：
 * type / value / defaultValue / onChange / disabled / readOnly / placeholder / maxLength 等。
 */
import type * as React from 'react';
import { useId, useState } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';

/** 输入框尺寸（3 档）。 */
export type InputSize = 'large' | 'medium' | 'small';

/** 校验状态。 */
export type InputStatus = 'error' | 'warning';

/**
 * InputTest 的 Props。
 *
 * 主要字段：
 * - prefix：前置图标（ReactNode，纯装饰）
 * - suffix：后置图标（ReactNode，纯装饰）
 * - allowClear：是否允许显示清除按钮
 * - clearIcon：自定义清除图标
 * - clearLabel：清除按钮的无障碍标签（默认"清除"）
 * - onClear：清除按钮点击后的回调（onChange 已自动通知清空值，这里仅额外通知清除事件）
 * - onPressEnter：按下回车键的回调
 * - size：`large | medium | small`，默认 `medium`
 * - status：`error | warning`，校验状态（仅影响边框颜色与 aria-invalid，不直接渲染文案）
 *
 * 自有扩展（非标准 Input API）：
 * - label：表单标签
 * - hint：辅助提示
 * - error：错误文案（同时启用错误样式与 aria-invalid，并显示错误文字）
 *
 * status 与 error 的优先级：
 * - `error` 字符串非空 → 红边 + 错误文字 + aria-invalid=true（最强）
 * - `status === 'error'` → 红边 + aria-invalid=true（不显示文案）
 * - `status === 'warning'` → 琥珀边，aria-invalid 不变（warning ≠ invalid）
 * - 调用方显式传 `aria-invalid` 拥有最高优先级，会被原样透传
 */
export interface InputTestProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size' | 'prefix'> {
  /** 尺寸，默认 `medium`。 */
  size?: InputSize;
  /** 前置图标（纯装饰，不拦截点击）。 */
  prefix?: React.ReactNode;
  /** 后置图标（纯装饰，不拦截点击）。 */
  suffix?: React.ReactNode;
  /** 是否显示清除按钮（有值且未禁用时显示，点击后清空）。 */
  allowClear?: boolean;
  /** 自定义清除按钮图标。 */
  clearIcon?: React.ReactNode;
  /** 清除按钮点击后的回调。 */
  onClear?: (e: React.MouseEvent<HTMLElement>) => void;
  /** 清除按钮的无障碍标签。 */
  clearLabel?: string;
  /** 按下回车键的回调。 */
  onPressEnter?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  /** 可选表单标签，点击聚焦输入框。 */
  label?: string;
  /** 辅助提示文案。 */
  hint?: string;
  /** 错误文案（非空时输入框边框变红 + 显示错误文字 + aria-invalid）。 */
  error?: string;
  /**
   * 校验状态。
   * - `error`：红边 + aria-invalid=true（若未显式传入 aria-invalid）。
   * - `warning`：琥珀边，aria-invalid 不变。
   * 优先级：`error` 字符串 > `status === 'error'` > `status === 'warning'` > 默认。
   */
  status?: InputStatus;
}

// 尺寸样式：高度 / 水平内边距 / 字体大小
const SIZE_CLASSES: Record<InputSize, string> = {
  large: 'h-10 px-3.5 text-base',
  medium: 'h-9 px-3 text-sm',
  small: 'h-8 px-2.5 text-sm',
};

// 有 prefix/suffix 时的水平内边距，避免文字与图标重叠
const ICON_PADDING: Record<InputSize, { left: string; right: string }> = {
  large: { left: 'pl-9', right: 'pr-9' },
  medium: { left: 'pl-8', right: 'pr-8' },
  small: { left: 'pl-7', right: 'pr-7' },
};

// prefix/suffix 在输入框内的水平定位
const ICON_POSITION: Record<InputSize, { left: string; right: string }> = {
  large: { left: 'left-3', right: 'right-3' },
  medium: { left: 'left-2.5', right: 'right-2.5' },
  small: { left: 'left-2', right: 'right-2' },
};

/**
 * 通用文本输入框。
 *
 * 受控 / 非受控均支持：
 * - 传 `value`：受控模式，值由外部管理。
 * - 传 `defaultValue`：非受控模式，内部维护状态。
 *
 * 清除行为：
 * - onChange 会被自动调用（伪造事件，value=''），保证受控/非受控统一清空。
 * - onClear 仅作为"清除事件"通知，方便调用方埋点或触发额外逻辑。
 *
 * 回车行为：
 * - onPressEnter 会在 Enter 键按下时调用，但不会阻止已有的 onKeyDown。
 */
export const InputTest = ({
  size = 'medium',
  prefix,
  suffix,
  allowClear,
  clearIcon,
  onClear,
  clearLabel = '清除',
  onPressEnter,
  label,
  hint,
  error,
  status,
  className,
  id,
  value,
  defaultValue,
  onChange,
  onKeyDown,
  ...props
}: InputTestProps) => {
  const generatedId = useId();

  // 按 id -> name -> 自动生成的顺序解析输入框 id，保证 label / aria 关联始终有效
  const inputId = id ?? props.name ?? generatedId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  // 合并调用方传入的 aria-describedby 与 hint / error 的 id，供屏幕阅读器使用
  const describedBy =
    [props['aria-describedby'], errorId ?? hintId].filter(Boolean).join(' ') || undefined;
  // 调用方显式传入 aria-invalid 拥有最高优先级；否则按 status / error 计算
  // warning 不置 invalid（语义上不等同错误），error 字符串或 status='error' 置 invalid
  const computedInvalid = error || status === 'error' ? true : undefined;
  const ariaInvalid = props['aria-invalid'] ?? computedInvalid;

  // 校验状态边框颜色：error 字符串 > status='error' > status='warning' > 默认
  // 使用 `!` 前缀是因为 .input-surface 在 @layer components 中直接设了 border-color，
  // 需要强制覆盖才能在 status / error 状态下显示对应的语义颜色。
  const statusBorderClass =
    error || status === 'error'
      ? '!border-danger/30'
      : status === 'warning'
        ? '!border-warning/30'
        : '';

  // 受控 / 非受控：传 value 即受控，否则用内部状态承载 defaultValue
  const isControlled = value !== undefined;
  const [innerValue, setInnerValue] = useState(defaultValue ?? '');
  const currentValue = isControlled ? value : innerValue;
  const hasValue = currentValue !== undefined && currentValue !== '';
  const showClear = Boolean(allowClear) && hasValue && !props.disabled;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!isControlled) {
      setInnerValue(e.target.value);
    }
    onChange?.(e);
  };

  const handleClear = (e: React.MouseEvent<HTMLElement>) => {
    if (!isControlled) {
      setInnerValue('');
    }
    // 通知"清除事件"发生
    onClear?.(e);
    // 构造空值事件，让受控 / 非受控场景统一走 onChange 同步状态
    onChange?.({
      target: { value: '' },
      currentTarget: { value: '' },
    } as unknown as React.ChangeEvent<HTMLInputElement>);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // 先调用调用方原始 onKeyDown，避免吞掉其它按键处理
    onKeyDown?.(e);
    if (e.key === 'Enter' && !e.defaultPrevented) {
      onPressEnter?.(e);
    }
  };

  // 布局结构：可选 label -> 输入行（前缀 / 后缀或清除按钮）-> error 或 hint
  return (
    <div className="flex flex-col">
      {label ? (
        <label
          htmlFor={inputId}
          className="mb-2 text-sm font-medium text-foreground"
        >
          {label}
        </label>
      ) : null}
      <div className="relative flex items-center">
        {prefix ? (
          <span
            aria-hidden
            className={cn(
              'pointer-events-none absolute z-10 flex items-center text-muted-text',
              ICON_POSITION[size].left,
            )}
          >
            {prefix}
          </span>
        ) : null}
        <input
          id={inputId}
          aria-describedby={describedBy}
          aria-invalid={ariaInvalid}
          value={currentValue}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          className={cn(
            'input-surface input-focus-glow w-full rounded-lg border bg-transparent text-foreground transition-all',
            'placeholder:text-muted-text focus:outline-none',
            SIZE_CLASSES[size],
            prefix ? ICON_PADDING[size].left : '',
            showClear || suffix ? ICON_PADDING[size].right : '',
            statusBorderClass,
            'disabled:cursor-not-allowed disabled:opacity-60',
            className,
          )}
          {...props}
        />
        {showClear ? (
          <button
            type="button"
            onClick={handleClear}
            aria-label={clearLabel}
            tabIndex={-1}
            disabled={props.disabled}
            className={cn(
              'absolute z-10 flex items-center justify-center rounded-full text-muted-text transition-colors',
              'hover:text-foreground hover:bg-white/10 focus:outline-none',
              ICON_POSITION[size].right,
            )}
          >
            {clearIcon ?? <X className="h-3.5 w-3.5" />}
          </button>
        ) : suffix ? (
          <span
            aria-hidden
            className={cn(
              'pointer-events-none absolute z-10 flex items-center text-muted-text',
              ICON_POSITION[size].right,
            )}
          >
            {suffix}
          </span>
        ) : null}
      </div>
      {error ? (
        <p
          id={errorId}
          role="alert"
          className="mt-1.5 text-xs text-danger"
        >
          {error}
        </p>
      ) : hint ? (
        <p
          id={hintId}
          className="mt-1.5 text-xs text-secondary-text"
        >
          {hint}
        </p>
      ) : null}
    </div>
  );
};