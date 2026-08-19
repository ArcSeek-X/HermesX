/**
 * Input —— 通用表单输入组件（基础层），基于 HeroUI（@heroui/react）的 Input 封装。
 *
 * 定位与适用范围：
 * - 提供 sm/md/lg 三档尺寸（外加 xs 紧凑档），由 size 控制高度、字号与圆角。
 * - 仅承载 HeroUI Input 本身的能力：原生属性透传（含受控 value / type / onChange）。
 * - 密码场景（Lock / Key 图标、可见性切换）请使用 PasswordInput。
 */
import type * as React from 'react';
import { useId } from 'react';
import { Input as HeroInput } from '@heroui/react';
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
}

/**
 * 通用文本输入组件，底层渲染 HeroUI 的 Input。
 * - 组件不渲染表单控件包裹层；hint / error 提示由调用方在外层渲染。
 * - 需要密码可见性切换请使用 PasswordInput。
 */
export const Input = ({
  className = '',
  size = 'sm',
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
  const heroProps = {
    id: inputId,
    className: cn(
      'hrs-input w-50',
      'input-surface input-focus-glow border bg-transparent transition-all',
      sizeClasses[size],
      'focus:outline-none',
      // 外部阴影调淡：覆盖默认 surface 阴影
      '!shadow-sm',
      // 聚焦时外框不变色，仅保留一圈更淡的聚焦光圈反馈
      'focus:!border-border focus:!shadow-[0_0_0_2px_hsl(var(--primary)/0.10)]',
      'disabled:cursor-not-allowed disabled:opacity-60',
      className,
    ),
    ...props,
  };

  return (
    <HeroInput {...(heroProps as object)} />
  );
};
