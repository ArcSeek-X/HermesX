/**
 * HrsInput —— 通用表单输入组件（基础层），基于 HeroUI（@heroui/react）的 Input 封装。
 *
 * 定位与适用范围：
 * - 提供 sm/md/lg 三档尺寸（外加 xs 紧凑档），由 size 控制高度、字号与圆角。
 * - 仅承载 HeroUI Input 本身的能力：原生属性透传（含受控 value / type / onChange）。
 * - 支持左 / 右插槽（prefixNode / suffixNode）：传入任一插槽时自动切换为
 *   HeroUI InputGroup 组合结构（边框与背景由外层 group 承载），未传时仍是单个输入框。
 * - 密码场景（Lock / Key 图标、可见性切换）请使用 PasswordInput。
 * @author Lensgcx (GaoCangxiong)
 */
import type * as React from 'react';
import { useId, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { Input as HeroInput, InputGroup } from '@heroui/react';
import { cn } from '../../../utils/cn';

/**
 * HrsInput 的 Props。继承原生 input 属性 —— 所有原生属性都会透传给内部 HeroUI Input。
 *
 * 受控用法（参考 HeroUI Input）：
 *   // 原生受控（推荐，本项目统一用此写法）
 *   <HrsInput value={value} onChange={(e) => setValue(e.target.value)} type="text" />
 *   // HeroUI / react-aria 风格
 *   <HrsInput value={value} onValueChange={setValue} type="password" />
 *
 * 其中 value / type / onChange 均来自继承的原生 input 属性，会通过 ...props 透传。
 *
 * size 尺寸（控制高度 / 行高 / 字号 / 圆角）：
 *   - 'xs'：h-7  text-xs  rounded-sm（超紧凑）
 *   - 'sm'：h-8  text-xs  rounded-sm
 *   - 'md'：h-9  text-sm  rounded-md
 *   - 'lg'：h-10 text-base rounded-md
 */
export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** 输入框尺寸，控制高度、行高与字号，默认 'sm'。 */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** 左侧插槽内容（如图标）；传入后组件切换为 InputGroup 组合结构。 */
  prefixNode?: React.ReactNode;
  /** 右侧插槽内容（如密码可见性切换按钮）；传入后组件切换为 InputGroup 组合结构。 */
  suffixNode?: React.ReactNode;
  /**
   * 是否在输入内容后显示「清除」按钮（输入框右侧 ×），默认 true。
   * 点击清空输入（触发 onChange / onValueChange 上抛空串）；无内容 / 只读时不显示。
   * 受控与非受控用法均支持：受控读 value，非受控经内部镜像值（含 defaultValue 种子）判断。
   * 实现为绝对定位覆盖层，不切换 InputGroup 结构，故打字过程输入框不会重挂载、不丢焦点。
   */
  clearable?: boolean;
  /** 清除按钮的无障碍标签，默认 '清除'。 */
  clearLabel?: string;
}

export const HrsInput = ({
  className = '',
  size = 'sm',
  prefixNode,
  suffixNode,
  clearable = true,
  clearLabel = '清除',
  ...props
}: InputProps) => {
  const generatedId = useId();

  // 按 name -> 自动生成的顺序解析输入框 id（id 已随 ...props 透传，无需单独解构）。
  const inputId = props.name ?? generatedId;

  // 非受控清空用：直接清空底层 DOM input 的实时值（受控由 props.onChange 上抛空串处理）。
  const inputRef = useRef<HTMLInputElement>(null);

  // 受控 / 非受控分流：clearable 依赖「当前显示值」判断是否显示 ×。
  // 非受控用法（无 value，仅 placeholder / defaultValue）下 props.value 恒为 undefined，
  // 需经 onChange 把实时输入镜像进 internalValue；受控用法以 props.value 为唯一真源，镜像不参与。
  const isControlled = props.value !== undefined;
  const [internalValue, setInternalValue] = useState<string>(
    String(props.value ?? props.defaultValue ?? ''),
  );
  const displayValue = isControlled ? (props.value as string) : internalValue;

  // 不同尺寸对应的高度 / 行高 / 字号 / 水平内边距，集中维护便于统一调整。
  const sizeClasses: Record<NonNullable<InputProps['size']>, string> = {
    xs: 'h-7 !text-xs rounded-sm',
    sm: 'h-8 !text-xs rounded-sm',
    md: 'h-9 !text-sm rounded-md',
    lg: 'h-10 !text-base rounded-md',
  };

  // 原生属性 + 固定样式统一透传给 HeroUI Input。
  // 注：HeroUI v3 基于 react-aria-components，其 Input props 类型在部分 IDE 解析下不完整，
  // 因此以 object 类型透传，保证原生属性（含 value / type / onChange 等）正常下发。
  //
  // 受控警告防护：HeroUI(react-aria) 在「传了 value 但未传 onChange/readOnly」时会告警
  // "provided a value prop to a form field without an onChange handler"。
  // 此时语义即为「只读展示」，这里自动补 readOnly，消除告警且不改变既有视觉/行为。
  const isReadOnlyView = props.value !== undefined && props.onChange === undefined;
  // 是否走 InputGroup 组合：用户显式传入任一插槽就需要外层 group 承载边框与背景。
  const hasSlots = Boolean(prefixNode) || Boolean(suffixNode);
  // 边框 / 背景 / 尺寸：组合模式下上提到外层 group，输入框自身只保留文字与圆角。
  const surfaceClasses = 'hrs-input-surface border';
  // 有内容 + 非只读 + 开启 clearable 时显示清除按钮（绝对定位覆盖，不触发结构切换）。
  // 用 displayValue 而非 props.value：受控读 props.value，非受控读镜像值。
  const showClear = clearable && !isReadOnlyView && String(displayValue ?? '').length > 0;

  // onChange 包装：非受控时把键入值同步进镜像 state，驱动 showClear 重算；
  // 受控时不写镜像（props.value 为真源），避免多余重渲染。
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!isControlled) setInternalValue(event.target.value);
    props.onChange?.(event);
  };

  const heroProps = {
    id: inputId,
    className: cn(
      // 有插槽时输入框恒为 w-full 填满外层 group；无插槽时用户 className 直接作用于输入框自身。
      hasSlots ? 'hrs-input w-full' : cn('hrs-input w-50', surfaceClasses),
      sizeClasses[size],
      // clearable 时给输入框右侧留出清除按钮空间，避免文字被覆盖
      clearable ? 'pr-7' : '',
    ),
    ...props,
    // 覆盖 ...props 中的 onChange，使非受控镜像逻辑生效（受控时 handleChange 仅透传）。
    onChange: handleChange,
    readOnly: props.readOnly ?? (isReadOnlyView ? true : undefined),
    // 占位符颜色由全局 .input-surface::placeholder 经 CSS 变量控制，Tailwind placeholder: 工具类会被其覆盖；
    // 这里以内联变量覆盖使其更淡（/0.1 透明度），且仅作用于当前输入框实例。
    style: {
      ...(props.style as React.CSSProperties | undefined),
      '--input-surface-placeholder': 'hsl(var(--muted-text) / 0.6)',
    } as React.CSSProperties,
  };

  // 清除：构造 value='' 的受控变更并上抛（同时兼容 HeroUI onValueChange 风格）；
  // 非受控时同步清空镜像值 + 底层 DOM 值，保证 × 随即消失且输入框文字真的被清空。
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

  // 输入框本体：保持与既有分支完全一致的结构（无插槽 = 单输入框；有插槽 = InputGroup）。
  // ref 直接挂在 input 元素上（而非 heroProps 内），供非受控清空时直接操作 DOM 值。
  const inputNode = !hasSlots ? (
    <HeroInput {...(heroProps as object)} ref={inputRef} />
  ) : (
    // 有插槽：用 HeroUI InputGroup 承载边框 / 背景，插槽分别落入 Prefix / Suffix，
    // 避免把 React 节点作为未知属性透传到 <input> 上（会被 React 告警并序列化成 [object Object]）。
    // 注意：有插槽时用户传入的 className 作用于外层 group 容器（而非内层输入框），
    // 以保证 w-* 等容器级样式能控制整体宽度，内层输入框保持 w-full 填满容器。
    // 有插槽时：clearable 下外层 relative 容器承接用户 className（含宽度），
    // group 自身需 w-full 填满容器，否则 .input-group 的 inline-flex 会收缩到内容宽度；
    // ！clearable 时无外层容器，直接把用户 className（含宽度）落到 group 上。
    <InputGroup.Root
      className={cn('hrs-input-group w-50', surfaceClasses, sizeClasses[size], clearable ? 'w-full' : '', !clearable ? className : '')}
      style={heroProps.style as React.CSSProperties}
    >
      {prefixNode ? <InputGroup.Prefix>{prefixNode}</InputGroup.Prefix> : null}
      <InputGroup.Input {...(heroProps as object)} ref={inputRef} />
      {suffixNode ? <InputGroup.Suffix>{suffixNode}</InputGroup.Suffix> : null}
    </InputGroup.Root>
  );

  // clearable：用相对定位容器包裹输入框，清除按钮绝对定位覆盖在右侧。
  // 容器（而非内部输入框）承接用户 className，保证 w-* 等容器级样式仍能控制整体宽度；
  // 该容器始终存在（clearable 为常量），不会因输入内容变化而在「单输入框 ↔ InputGroup」间切换，
  // 故打字过程中输入框元素身份稳定、焦点不丢失。
  if (clearable) {
    return (
      <div className={cn('relative', className)} style={heroProps.style}>
        {inputNode}
        {clearButton}
      </div>
    );
  }

  // 无 clearable（显式关闭）：维持原结构；无插槽时用户 className 直接作用于输入框。
  if (!hasSlots) {
    return (
      <HeroInput
        {...(heroProps as object)}
        className={cn(heroProps.className, className)}
      />
    );
  }
  return inputNode;
};
