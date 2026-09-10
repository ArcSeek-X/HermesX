/**
 * Switch 开关组件
 *
 * 简单的 iOS 风格开关，受控组件（checked / onChange），支持禁用与左侧标签。
 * 使用场景：设置项的开启/关闭切换。
 * @author Lensgcx (GaoCangxiong)
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** Switch 开关组件的属性定义 */
export interface SwitchProps {
  /** 是否开启，必填（受控） */
  checked: boolean;
  /** 状态变化回调，接收切换后的值，必填 */
  onChange: (checked: boolean) => void;
  /** 是否禁用，默认 false */
  disabled?: boolean;
  /** 开关左侧标签文字，可选 */
  label?: string;
  /** 额外 CSS 类名（作用于外层 label 容器），默认空 */
  className?: string;
}

/**
 * 开关组件。
 * 渲染 role="switch" 的按钮 + 可选左侧标签；点击切换 checked 并回调 onChange。
 * @param props - 组件属性，见 SwitchProps
 * @returns label 包裹的开关（按钮 + 可选文字）
 */
export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  disabled = false,
  label,
  className,
}) => {
  return (
    <label
      className={cn(
        'inline-flex items-center gap-2 cursor-pointer select-none',
        disabled && 'opacity-50 cursor-not-allowed',
        className,
      )}
    >
      {label && <span className="text-sm text-muted-text">{label}</span>}
      {/* 开关本体：role=switch 供辅助技术识别，aria-checked 同步受控值 */}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          'relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors duration-200 ease-in-out',
          checked
            ? 'bg-[hsl(var(--primary))]'
            : 'bg-muted',
        )}
      >
        {/* 滑轨上的白色滑块：checked 时右移（translate-x-4），否则靠左（translate-x-0.5） */}
        <span
          className={cn(
            'pointer-events-none inline-block h-4 w-4 translate-y-0.5 rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ease-in-out',
            checked ? 'translate-x-4' : 'translate-x-0.5',
          )}
        />
      </button>
    </label>
  );
};

export default Switch;
