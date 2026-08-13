/**
 * ===================================
 * 密码可见性切换图标（EyeToggleIcon）
 * ===================================
 *
 * 【功能介绍】
 * 一个纯展示的「眼睛 / 眼罩」图标组件，用于密码输入框的「显示 / 隐藏」切换按钮中，
 * 以图标直观表达当前密码是否可见。组件本身只负责 rendering 对应图标，不包含点击逻辑或状态。
 *
 * 【设计要点】
 * 1. 双态图标：visible=true 时显示「眼罩（eye-slash）」——表示密码当前可见、点击可隐藏；
 *    visible=false 时显示「眼睛（eye）」——表示密码当前隐藏、点击可显示。
 * 2. 纯展示、无状态：不持有任何内部状态，图标完全由 visible prop 决定，便于父组件统一管理
 *    密码显隐状态。
 * 3. 可定制尺寸：className 默认 'w-4 h-4'，调用方可传入其它尺寸类（如 'w-5 h-5'）。
 * 4. 无障碍：图标为装饰性，统一设置 aria-hidden=true，真实状态由按钮的 aria-label 负责播报。
 *
 * 【使用方式】
 *   <button onClick={toggle} aria-label={visible ? '隐藏密码' : '显示密码'}>
 *     <EyeToggleIcon visible={visible} />
 *   </button>
 */

import type React from 'react';

/** EyeToggleIcon 组件的 Props 定义 */
interface EyeToggleIconProps {
  /** true = 密码可见（显示眼罩图标，提示点击隐藏）；false = 密码隐藏（显示眼睛图标，提示点击显示） */
  visible: boolean;
  /** 图标尺寸类名，默认 'w-4 h-4' */
  className?: string;
}

/**
 * 密码可见性切换图标组件：根据 visible 在「眼睛 / 眼罩」之间切换。
 *
 * @param props - 组件属性
 * @param props.visible - 密码是否可见
 * @param props.className - 图标尺寸类名
 * @returns 对应的 SVG 图标
 */
export const EyeToggleIcon: React.FC<EyeToggleIconProps> = ({ visible, className = 'w-4 h-4' }) => {
  if (visible) {
    // 眼罩图标：密码当前可见，点击可隐藏
    return (
      <svg
        className={className}
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        aria-hidden={true}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88"
        />
      </svg>
    );
  }
  // 眼睛图标：密码当前隐藏，点击可显示
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      aria-hidden={true}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
};
