/**
 * HrsInput —— 基于 HeroUI Input 封装的通用输入框（基础层）。
 *
 * - size 控制高度 / 字号 / 圆角：xs(h-7) / sm(h-8) / md(h-9) / lg(h-10)，默认 sm。
 * - 原生属性（value / type / onChange 等）经 ...props 透传。
 * - prefixNode / suffixNode：传入任一时切换为 HeroUI InputGroup 组合（边框由外层 group 承载）。
 * - clearable：默认开启，输入框有内容且非只读时显示右侧「×」清除按钮（绝对定位，不切换结构，打字不丢焦点）。
 * - 密码场景请用 PasswordInput。
 * @author Lensgcx (GaoCangxiong)
 */
import type * as React from 'react';
import { useId, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { Input as HeroInput, InputGroup } from '@heroui/react';
import { cn } from '../../../utils/cn';

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** 尺寸，控制高度、字号与圆角，默认 'sm'。 */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** 左侧插槽（如图标）；传入即切换为 InputGroup 组合结构。 */
  prefixNode?: React.ReactNode;
  /** 右侧插槽（如可见性切换）；传入即切换为 InputGroup 组合结构。 */
  suffixNode?: React.ReactNode;
  /** 是否显示右侧清除按钮，默认 true（无内容 / 只读时不显示）。 */
  clearable?: boolean;
  /** 清除按钮的无障碍标签，默认 '清除'。 */
  clearLabel?: string;
}

const SIZE_CLASSES: Record<NonNullable<InputProps['size']>, string> = {
  xs: 'h-7 !text-xs rounded-sm',
  sm: 'h-8 !text-xs rounded-sm',
  md: 'h-9 !text-sm rounded-md',
  lg: 'h-10 !text-base rounded-md',
};

// 边框由 Tailwind 承载（不再依赖 global.scss 的 .hrs-input-surface 等未定义类）。
const SURFACE = 'border';

export const HrsInput = ({
  className = '',
  size = 'sm',
  prefixNode,
  suffixNode,
  clearable = true,
  clearLabel = '清除',
  ...props
}: InputProps) => {
  const inputId = props.name ?? useId();
  const inputRef = useRef<HTMLInputElement>(null);

  // 受控 / 非受控分流：clearable 依赖当前显示值判断是否显示 ×。
  const isControlled = props.value !== undefined;
  const [internalValue, setInternalValue] = useState<string>(
    String(props.value ?? props.defaultValue ?? ''),
  );
  const displayValue = isControlled ? (props.value as string) : internalValue;

  // 传了 value 却没传 onChange/readOnly 时，react-aria 会告警；语义即只读展示，这里自动补 readOnly。
  const isReadOnlyView = props.value !== undefined && props.onChange === undefined;
  const hasSlots = Boolean(prefixNode) || Boolean(suffixNode);
  const showClear = clearable && !isReadOnlyView && String(displayValue ?? '').length > 0;

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!isControlled) setInternalValue(event.target.value);
    props.onChange?.(event);
  };

  // 输入框样式：有插槽时不带边框（边框上提到 group）；clearable 时 w-full 填满外层容器并留出清除按钮空间。
  const inputClassName = cn(
    hasSlots
      ? 'w-full'
      : clearable
        ? cn('w-full', SURFACE)
        : cn('w-50', SURFACE),
    SIZE_CLASSES[size],
    clearable ? 'pr-7' : '',
  );

  const heroProps = {
    id: inputId,
    className: inputClassName,
    ...props,
    onChange: handleChange,
    readOnly: props.readOnly ?? (isReadOnlyView ? true : undefined),
    style: props.style,
  };

  // 构造 value='' 的变更上抛（兼容 onValueChange）；非受控同步清空镜像值与底层 DOM 值。
  const handleClear = () => {
    if (!isControlled) {
      setInternalValue('');
      if (inputRef.current) inputRef.current.value = '';
    }
    const event = { target: { value: '' } } as unknown as React.ChangeEvent<HTMLInputElement>;
    props.onChange?.(event);
    (props as { onValueChange?: (value: string) => void }).onValueChange?.('');
  };

  const clearButton = showClear ? (
    <button
      type="button"
      aria-label={clearLabel}
      onClick={handleClear}
      className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center text-muted-text transition-colors hover:text-foreground"
    >
      <X aria-hidden className="h-3.5 w-3.5" />
    </button>
  ) : null;

  const inputNode = !hasSlots ? (
    <HeroInput {...(heroProps as object)} ref={inputRef} />
  ) : (
    // 有插槽：用 HeroUI InputGroup 承载边框，插槽落入 Prefix / Suffix，避免 React 节点透传到 <input>。
    <InputGroup.Root
      className={cn(
        'w-50',
        SURFACE,
        SIZE_CLASSES[size],
        clearable ? 'w-full' : '',
        !clearable ? className : '',
      )}
      style={heroProps.style as React.CSSProperties}
    >
      {prefixNode ? <InputGroup.Prefix>{prefixNode}</InputGroup.Prefix> : null}
      <InputGroup.Input {...(heroProps as object)} ref={inputRef} />
      {suffixNode ? <InputGroup.Suffix>{suffixNode}</InputGroup.Suffix> : null}
    </InputGroup.Root>
  );

  // clearable：外层 relative 容器默认 w-50（显式宽度，避免被 CSS Grid 拉伸），
  // 输入框 w-full 填满容器，清除按钮贴输入框右缘内侧；传 w-full / col-span 时由 tailwind-merge 覆盖为全宽。
  if (clearable) {
    return (
      <div className={cn('relative w-50', className)} style={heroProps.style}>
        {inputNode}
        {clearButton}
      </div>
    );
  }

  // 关闭 clearable：无插槽时 className 直接作用于输入框；有插槽返回 group。
  if (!hasSlots) {
    return <HeroInput {...(heroProps as object)} className={cn(heroProps.className, className)} />;
  }
  return inputNode;
};
