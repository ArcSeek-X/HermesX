/**
 * @file DashboardStateBlock.tsx
 * @description 仪表盘状态区块组件，用于统一渲染加载中、空数据、错误等状态的占位展示
 * @module components/dashboard
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/**
 * 仪表盘状态区块组件的 Props 定义
 */
interface DashboardStateBlockProps {
  /** 状态标题（必填，如"暂无数据"、"正在加载"） */
  title: string;
  /** 状态描述文案（显示在标题下方，用于补充说明） */
  description?: string;
  /** 状态图标（如空数据时的空盒子图标、错误时的警告图标） */
  icon?: React.ReactNode;
  /** 操作区（如"重试"按钮、"刷新"按钮等） */
  action?: React.ReactNode;
  /** 自定义容器类名 */
  className?: string;
  /** 自定义标题类名 */
  titleClassName?: string;
  /** 自定义描述类名 */
  descriptionClassName?: string;
  /** 紧凑模式：减小内边距和字号，用于空间受限的场景 */
  compact?: boolean;
  /** 加载中模式：显示旋转动画替代图标 */
  loading?: boolean;
  /** 标题的 HTML 标签类型，默认 'p'，可根据语义化需求改为 h2/h3/h4/span */
  titleAs?: 'p' | 'h2' | 'h3' | 'h4' | 'span';
}

/**
 * 仪表盘状态区块组件
 *
 * 用于在面板内容为空、加载中或出错时展示统一的占位状态。
 * 布局结构：居中垂直排列（图标 → 标题 + 描述 → 操作按钮）
 *
 * @param props - 组件属性
 * @returns 状态区块 JSX 元素
 */
export const DashboardStateBlock: React.FC<DashboardStateBlockProps> = ({
  title,
  description,
  icon,
  action,
  className = '',
  titleClassName = '',
  descriptionClassName = '',
  compact = false,
  loading = false,
  titleAs = 'p',
}) => {
  // 动态标签：根据 titleAs 选择标题的 HTML 元素
  const TitleTag = titleAs;

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        // 紧凑模式减小间距和内边距
        compact ? 'gap-2 py-6' : 'gap-3 py-10',
        className,
      )}
    >
      {/* 图标区域：loading 时显示旋转动画，否则显示传入的图标 */}
      {loading ? (
        <div className="home-spinner h-6 w-6 animate-spin border-2" aria-hidden="true" />
      ) : icon ? (
        <div className="home-state-icon-muted flex h-11 w-11 items-center justify-center rounded-full bg-subtle">
          {icon}
        </div>
      ) : null}
      {/* 文本区域：标题 + 描述 */}
      <div className="space-y-1">
        <TitleTag className={cn('text-secondary-text', compact ? 'text-xs' : 'text-sm', titleClassName)}>
          {title}
        </TitleTag>
        {/* 描述文案，仅在有值时渲染 */}
        {description ? (
          <p className={cn('mx-auto max-w-xs text-secondary-text', compact ? 'text-label' : 'text-xs', descriptionClassName)}>
            {description}
          </p>
        ) : null}
      </div>
      {/* 操作按钮区，仅在有值时渲染 */}
      {action ? <div className="flex items-center justify-center">{action}</div> : null}
    </div>
  );
};
