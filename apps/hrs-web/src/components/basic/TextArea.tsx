/**
 * TextArea —— 通用多行文本输入组件（基础层），基于 HeroUI（@heroui/react）的 TextArea 封装。
 *
 * 名称：TextArea（多行文本输入框）
 * 作用：在表单 / 配置 / 备注等场景提供多行文本录入能力，底层复用 HeroUI 的 TextArea，
 *       并统一本项目尺寸体系与视觉规范。
 * 描述：
 *   - 支持 sm/md/lg 三档尺寸（外加 xs 紧凑档），由 size 控制最小高度、字号与圆角；
 *     rows 控制默认可见行数（默认 3，与 HeroUI 一致），可被 size 之外独立设定。
 *   - 继承所有原生 <textarea> 属性（value / defaultValue / onChange / placeholder / disabled /
 *     readOnly / maxLength 等）并原样透传，受控写法与 HTML 一致：
 *       <TextArea value={v} onChange={(e) => setV(e.target.value)} />
 *   - variant 沿用 HeroUI 规格（'primary' 默认带阴影、'secondary' 无阴影适配 Surface）。
 *   - 校验 / 标签 / 错误文案等高级能力，建议配合 HeroUI 的 <TextField> 包裹使用。
 *   - 内部样式全部基于 Tailwind 工具类，不引入或新建样式类（除复用项目既有 surface 变量）。
 */
import type * as React from 'react';
import { useId } from 'react';
import { TextArea as HeroTextArea } from '@heroui/react';
import { cn } from '../../utils/cn';

/**
 * TextArea 的 Props。继承原生 textarea 属性 —— 所有原生属性都会透传给内部 HeroUI TextArea。
 *
 * 受控用法（参考 HeroUI TextArea / 原生 textarea）：
 *   // 原生受控（推荐，本项目统一用此写法）
 *   <TextArea value={value} onChange={(e) => setValue(e.target.value)} rows={4} />
 *
 * size 尺寸（控制最小高度 / 字号 / 圆角）：
 *   - 'xs'：min-h-16 text-xs  rounded-sm（超紧凑）
 *   - 'sm'：min-h-20 text-xs  rounded-sm
 *   - 'md'：min-h-24 text-sm  rounded-md
 *   - 'lg'：min-h-28 text-base rounded-md
 * 注：size 仅设定最小高度，实际高度仍可由 rows 与用户拖拽（resize）共同决定。
 */
export interface TextAreaProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'size'> {
  /** 输入框尺寸，控制最小高度、字号与圆角，默认 'sm'。 */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** 可见文本行数（对应原生 rows），默认 3，与 HeroUI TextArea 一致。 */
  rows?: number;
  /** HeroUI 视觉变体：'primary' 带阴影默认样式；'secondary' 无阴影，适用于 Surface 内。 */
  variant?: 'primary' | 'secondary';
}

/**
 * 通用多行文本输入组件，底层渲染 HeroUI 的 TextArea。
 * - 组件不渲染表单控件包裹层；label / hint / error 由调用方在外层渲染（建议用 TextField 包裹）。
 * - 所有原生属性 + 固定样式统一透传，尺寸经抽象映射避免重复代码。
 */
export const TextArea = ({
  className = '',
  size = 'sm',
  rows = 5,
  variant = 'primary',
  ...props
}: TextAreaProps) => {
  const generatedId = useId();

  // 按 name -> 自动生成的顺序解析输入框 id（id 已随 ...props 透传，无需单独解构）。
  const textAreaId = props.name ?? generatedId;

  // 不同尺寸对应的最小高度 / 字号 / 圆角，集中维护便于统一调整。
  const sizeClasses: Record<NonNullable<TextAreaProps['size']>, string> = {
    xs: '!text-xs rounded-sm',
    sm: '!text-xs rounded-sm',
    md: '!text-sm rounded-md',
    lg: '!text-base rounded-md',
  };

  // 原生属性 + 固定样式统一透传给 HeroUI TextArea。
  // 注：HeroUI v3 基于 react-aria-components，其 TextArea props 类型在部分 IDE 解析下不完整，
  // 因此以 object 类型透传，保证原生属性（含 value / onChange 等）正常下发。

  // 受控警告防护：HeroUI(react-aria) 在「传了 value 但未传 onChange/readOnly」时会告警
  // "provided a value prop to a form field without an onChange handler"。
  // 此时语义即为「只读展示」，这里自动补 readOnly，消除告警且不改变既有视觉/行为。
  const isReadOnlyView = props.value !== undefined && props.onChange === undefined;
  const heroProps = {
    id: textAreaId,
    variant,
    rows,
    className: cn(
      'hrs-textarea w-50 resize-y border bg-transparent transition-all',
      'focus:outline-none',
      'disabled:cursor-not-allowed disabled:opacity-60',
      sizeClasses[size],
      className,
    ),
    ...props,
    readOnly: props.readOnly ?? (isReadOnlyView ? true : undefined),
    // 占位符颜色由全局 surface 变量控制，这里以内联变量覆盖使其更淡，仅作用于当前实例。
    style: {
      ...(props.style as React.CSSProperties | undefined),
      '--input-surface-placeholder': 'hsl(var(--muted-text) / 0.6)',
    } as React.CSSProperties,
  };

  return (
    <HeroTextArea {...(heroProps as object)} />
  );
};
