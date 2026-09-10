/**
 * @file Checkbox.tsx
 * @description 定制化大尺寸勾选框组件：基于原生 input[type=checkbox] 封装，支持 label 联动点击与容器级样式定制。
 * 使用场景：表单勾选项、协议同意、筛选条件等需要大尺寸勾选框的场合。
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';
import { useId } from 'react';
import { cn } from '../../utils/cn';

/** Checkbox 组件的属性定义：继承原生 input 属性（type 固定为 checkbox），额外支持 label 与容器样式 */
interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** 勾选框右侧的标签文案，可选；不传则只渲染勾选框 */
  label?: string;
  /** 外层容器的自定义 CSS 类名（作用于 flex 容器），默认空 */
  containerClassName?: string;
}

/**
 * 定制化的大尺寸勾选框组件。
 *
 * 渲染 16px 圆角勾选框 + 可选 label；id 由传入值或 useId 自动生成，保证 label 的 htmlFor 与输入框关联正确。
 * @param props - 组件属性，见 CheckboxProps（label / containerClassName 及原生 input 属性）
 * @returns 勾选框与可选 label 的 flex 容器
 */
export const Checkbox: React.FC<CheckboxProps> = ({
  label,
  id,
  className = '',
  containerClassName = '',
  ...props
}) => {
  const generatedId = useId();
  // id 优先取传入值，否则用 useId 生成的稳定 id（label htmlFor 关联需要）
  const checkboxId = id ?? generatedId;

  return (
    <div className={cn('flex items-center gap-3', containerClassName)}>
      <input
        id={checkboxId}
        type="checkbox"
        className={cn(
          'h-4 w-4 cursor-pointer rounded border border-border/70 bg-base text-cyan transition-all',
          'focus:ring-2 focus:ring-cyan/20 focus:outline-none',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      />
      {label && (
        <label
          htmlFor={checkboxId}
          className="cursor-pointer select-none text-sm font-medium text-foreground"
        >
          {label}
        </label>
      )}
    </div>
  );
};
