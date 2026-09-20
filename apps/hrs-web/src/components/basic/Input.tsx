/**
 * Input —— 通用表单输入组件（基础层），基于 HeroUI（@heroui/react）的 Input 封装。
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
import { useId } from 'react';
import { Input as HeroInput, InputGroup } from '@heroui/react';
import { cn } from '../../utils/cn';

/**
 * Input 的 Props。继承原生 input 属性 —— 所有原生属性都会透传给内部 HeroUI Input。
 *
 * 受控用法（参考 HeroUI Input）：
 *   // 原生受控（推荐，本项目统一用此写法）
 *   <Input value={value} onChange={(e) => setValue(e.target.value)} type="text" />
 *   // HeroUI / react-aria 风格
 *   <Input value={value} onValueChange={setValue} type="password" />
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
}

/**
 * 通用文本输入组件，底层渲染 HeroUI 的 Input。
 * - 组件不渲染表单控件包裹层；hint / error 提示由调用方在外层渲染。
 * - 需要密码可见性切换请使用 PasswordInput。
 */
export const Input = ({
  className = '',
  size = 'sm',
  prefixNode,
  suffixNode,
  ...props
}: InputProps) => {
  const generatedId = useId();

  // 按 name -> 自动生成的顺序解析输入框 id（id 已随 ...props 透传，无需单独解构）。
  const inputId = props.name ?? generatedId;

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
  // 是否走 InputGroup 组合：只要有任一插槽就需要外层 group 承载边框与背景。
  const hasSlots = Boolean(prefixNode) || Boolean(suffixNode);
  // 边框 / 背景 / 尺寸：组合模式下上提到外层 group，输入框自身只保留文字与圆角。
  const surfaceClasses = 'hrs-input-surface border';

  const heroProps = {
    id: inputId,
    className: cn(
      hasSlots ? 'hrs-input w-full' : cn('hrs-input w-50', surfaceClasses),

      // 'input-surface input-focus-glow border bg-transparent transition-all',
      // 'focus:outline-none',
      // // 外部阴影调淡：覆盖默认 surface 阴影
      // '!shadow-xs',
      // // 聚焦时外框不变色，仅保留一圈更淡的聚焦光圈反馈
      // 'focus:!border-border focus:!shadow-[0_0_0_2px_hsl(var(--primary)/0.10)]',
      // 'disabled:cursor-not-allowed disabled:opacity-60',

      // '!placeholder:text-muted / 0.1',

       sizeClasses[size],
      className,
    ),
    ...props,
    readOnly: props.readOnly ?? (isReadOnlyView ? true : undefined),
    // 占位符颜色由全局 .input-surface::placeholder 经 CSS 变量控制，Tailwind placeholder: 工具类会被其覆盖；
    // 这里以内联变量覆盖使其更淡（/0.1 透明度），且仅作用于当前输入框实例。
    style: {
      ...(props.style as React.CSSProperties | undefined),
      '--input-surface-placeholder': 'hsl(var(--muted-text) / 0.6)',
    } as React.CSSProperties,
  };

  // 无插槽：维持原有的单个输入框结构（零额外 DOM）。
  if (!hasSlots) {
    return <HeroInput {...(heroProps as object)} />;
  }

  // 有插槽：用 HeroUI InputGroup 承载边框 / 背景，插槽分别落入 Prefix / Suffix，
  // 避免把 React 节点作为未知属性透传到 <input> 上（会被 React 告警并序列化成 [object Object]）。
  return (
    <InputGroup.Root
      className={cn('hrs-input-group w-50', surfaceClasses, sizeClasses[size])}
      style={heroProps.style as React.CSSProperties}
    >
      {prefixNode ? <InputGroup.Prefix>{prefixNode}</InputGroup.Prefix> : null}
      <InputGroup.Input {...(heroProps as object)} />
      {suffixNode ? <InputGroup.Suffix>{suffixNode}</InputGroup.Suffix> : null}
    </InputGroup.Root>
  );
};
