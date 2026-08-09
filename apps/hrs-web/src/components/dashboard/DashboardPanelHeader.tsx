/**
 * @file DashboardPanelHeader.tsx
 * @description 仪表盘面板头部组件，统一渲染面板的眉标（eyebrow）、标题、前导图标和操作按钮
 * @module components/dashboard
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/**
 * 仪表盘面板头部组件的 Props 定义
 */
interface DashboardPanelHeaderProps {
  /** 眉标文本（通常为大写小标签，显示在标题上方或左侧） */
  eyebrow?: React.ReactNode;
  /** 面板标题 */
  title?: React.ReactNode;
  /** 右侧操作区（按钮、开关等） */
  actions?: React.ReactNode;
  /** 标题前导图标（显示在眉标/标题左侧） */
  leading?: React.ReactNode;
  /** 自定义容器类名 */
  className?: string;
  /** 自定义标题区域类名 */
  headingClassName?: string;
  /** 自定义标题文字类名 */
  titleClassName?: string;
  /** 是否为眉标添加强调色样式 */
  accentEyebrow?: boolean;
}

/**
 * 仪表盘面板头部组件
 *
 * 布局结构：左侧（前导图标 + 眉标 + 标题） 右侧（操作按钮区）
 * 当 eyebrow、title、actions 三者均为空时返回 null，不渲染任何内容
 *
 * @param props - 组件属性
 * @returns 面板头部 JSX 元素，或 null
 */
export const DashboardPanelHeader: React.FC<DashboardPanelHeaderProps> = ({
  eyebrow,
  title,
  actions,
  leading,
  className = '',
  headingClassName = '',
  titleClassName = '',
  accentEyebrow = false,
}) => {
  // 三者均为空时无需渲染
  if (!eyebrow && !title && !actions) {
    return null;
  }

  return (
    // 面板头部容器：左右两端对齐
    <div className={cn('mb-4 flex items-center justify-between gap-3', className)}>
      {/* 左侧标题区域：前导图标 + 眉标 + 标题 */}
      {(eyebrow || title) ? (
        <div className={cn('flex items-baseline gap-2', headingClassName)}>
          {/* 前导图标 */}
          {leading ? <span className="shrink-0">{leading}</span> : null}
          {/* 眉标文本，accentEyebrow 时附加强调色 */}
          {eyebrow ? (
            <span className={cn('label-uppercase', accentEyebrow && 'home-title-accent')}>
              {eyebrow}
            </span>
          ) : null}
          {/* 主标题 */}
          {title ? <h3 className={cn('text-base font-semibold text-foreground', titleClassName)}>{title}</h3> : null}
        </div>
      ) : null}
      {/* 右侧操作按钮区 */}
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
};
