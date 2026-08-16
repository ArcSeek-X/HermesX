/**
 * Input —— 通用表单输入组件（基础层），基于 HeroUI（@heroui/react）的 Input 封装。
 *
 * 定位与适用范围：
 * - 高度固定（h-11），不适用于紧凑型搜索框（如板块搜索的 py-1 text-xs），
 *   此类场景请保留内联 <input>。
 * - 仅承载 HeroUI Input 本身的能力：原生属性透传 + 通用前导 / 尾部插槽。
 * - 密码场景（Lock / Key 图标、可见性切换）请使用 PasswordInput。
 */
import type * as React from 'react';
import { useId } from 'react';
import { Input as HeroInput } from '@heroui/react';
import { cn } from '../../utils/cn';

/**
 * Input 的 Props。继承原生 input 属性 —— 所有原生属性都会透传给内部 HeroUI Input。
 */
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** 前导节点（图标等装饰），绝对定位于输入框左侧。 */
  prefixNode?: React.ReactNode;
  /** 尾部节点（按钮等操作），绝对定位于输入框右侧。 */
  suffixNode?: React.ReactNode;
}

/**
 * 通用文本输入组件，底层渲染 HeroUI 的 Input。
 * - 组件不渲染表单控件包裹层；hint / error 提示由调用方在外层渲染。
 * - 需要密码可见性切换请使用 PasswordInput。
 */
export const Input = ({
  className = '',
  id,
  prefixNode,
  suffixNode,
  ...props
}: InputProps) => {
  const generatedId = useId();

  // 按 id -> name -> 自动生成的顺序解析输入框 id。
  const inputId = id ?? props.name ?? generatedId;

  // 原生属性 + 固定样式统一透传给 HeroUI Input。
  // 注：HeroUI v3 基于 react-aria-components，其 Input props 类型在部分 IDE 解析下不完整，
  // 因此以 object 类型透传，保证原生属性（含 aria-*）正常下发。
  const heroProps = {
    ...props,
    id: inputId,
    fullWidth: true,
    className: cn(
      'input-surface input-focus-glow w-full rounded-md border bg-transparent px-4 text-sm transition-all',
      'focus:outline-none',
      prefixNode ? 'pl-10' : '',
      suffixNode ? 'pr-12' : '',
      'disabled:cursor-not-allowed disabled:opacity-60',
      className,
    ),
  };

  return (
    <div className="hrs-input relative flex items-center">
      {prefixNode ? (
        <div className="pointer-events-none absolute left-3.5 z-10">{prefixNode}</div>
      ) : null}
      <HeroInput {...(heroProps as object)} />
      {suffixNode ? (
        <div className="absolute inset-y-0 right-2 flex items-center">{suffixNode}</div>
      ) : null}
    </div>
  );
};
