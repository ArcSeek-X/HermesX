/**
 * ===================================
 * 折叠面板组件（Collapsible）
 * ===================================
 *
 * 【功能介绍】
 * 一个可展开 / 折叠的「手风琴式面板」：标题栏常驻，点击标题在「展开内容」与「收起内容」之间切换，
 * 并带有高度与透明度的过渡动画。适用于 FAQ、分组说明、可隐藏的辅助内容等场景。
 *
 * 【设计要点】
 * 1. 内部状态：用 useState 管理 isOpen，defaultOpen 控制初始展开态；点击标题按钮切换。
 * 2. 展开动画：内容容器通过 max-h 与 opacity 过渡实现平滑展开/收起
 *    （展开 max-h-[2000px] + opacity-100，收起 max-h-0 + opacity-0），配合 duration-300 ease-in-out。
 * 3. 标题栏：左侧可选图标（icon）+ 标题（title），右侧箭头随展开态旋转（rotate-180）作视觉指示；
 *    hover 时整行底色变化，提示可点击。
 * 4. 卡片外观：圆角 + 细边框 + 半透明背景 + 柔和阴影，hover 时边框高亮（hover:border-accent）。
 * 5. 溢出约束：最外层 overflow-hidden，避免展开动画期间内容溢出圆角卡片。
 *
 * 【使用方式】
 *   <Collapsible title="高级选项" icon={<Gear/>} defaultOpen>
 *     <AdvancedForm />
 *   </Collapsible>
 */

import React, { useState } from 'react';
import { cn } from '../../utils/cn';

/** Collapsible 组件的 Props 定义 */
interface CollapsibleProps {
  /** 面板标题（常驻标题栏） */
  title: string;
  /** 折叠面板内容节点 */
  children: React.ReactNode;
  /** 初始是否展开，默认 false */
  defaultOpen?: boolean;
  /** 标题左侧的可选图标 */
  icon?: React.ReactNode;
  /** 透传的额外类名 */
  className?: string;
}

/**
 * 折叠面板组件：点击标题展开/收起内容，带过渡动画。
 *
 * @param props - 组件属性
 * @param props.title - 标题
 * @param props.children - 内容
 * @param props.defaultOpen - 初始展开
 * @param props.icon - 标题图标
 * @param props.className - 额外类名
 * @returns 可折叠的卡片面板
 */
export const Collapsible: React.FC<CollapsibleProps> = ({
  title,
  children,
  defaultOpen = false,
  icon,
  className = '',
}) => {
  // 展开/收起状态（受控于点击，初始由 defaultOpen 决定）
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    // 外层卡片：圆角 + 细边框 + 半透明 + 阴影 + hover 高亮；overflow-hidden 约束动画溢出
    <div
      className={cn(
        'overflow-hidden rounded-2xl border border-subtle bg-card/70 shadow-soft-card transition-all duration-300',
        'hover:border-accent',
        className,
      )}
    >
      {/* 标题按钮：整行可点击，左图标+标题，右箭头随展开旋转 */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-hover"
      >
        <div className="flex items-center gap-3">
          {icon && <span className="text-cyan">{icon}</span>}
          <span className="font-medium text-foreground">{title}</span>
        </div>
        <svg
          className={cn('h-5 w-5 text-secondary-text transition-transform duration-300', isOpen && 'rotate-180')}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* 内容容器：max-h + opacity 过渡实现展开/收起动画 */}
      <div
        className={cn('overflow-hidden transition-all duration-300 ease-in-out', isOpen ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0')}
      >
        {/* 内容区：上边框分隔 + 内边距 */}
        <div className="border-t border-subtle px-4 pb-4 pt-2">
          {children}
        </div>
      </div>
    </div>
  );
};
