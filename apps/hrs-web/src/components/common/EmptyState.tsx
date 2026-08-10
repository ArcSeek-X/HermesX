/**
 * EmptyState.tsx
 *
 * 作用简述：
 *   一个通用的「空状态 / 空数据」展示组件（Empty State）。
 *   当页面或列表没有数据、没有结果、或处于初始占位状态时，用它来友好地
 *   提示用户，而非展示一片空白。组件支持自定义标题、补充说明、图标
 *   以及操作入口（如「去添加」「刷新」「返回」等按钮）。
 *
 * 使用场景：
 *   - 搜索 / 筛选无结果。
 *   - 列表为空（无收藏、无历史记录等）。
 *   - 数据加载完成但内容为空，需要引导用户下一步操作的场合。
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/**
 * 组件属性定义。
 */
interface EmptyStateProps {
  /** 空状态主标题（必填），用于一句话说明当前没有内容的原因或状态。 */
  title: string;
  /** 补充说明文案（可选），对标题做进一步解释，居中且限制最大宽度。 */
  description?: string;
  /** 顶部图标（可选），通常是装饰性 SVG / Icon 节点，使用主题青色着色。 */
  icon?: React.ReactNode;
  /** 操作区节点（可选），一般放入按钮等引导用户操作的入口。 */
  action?: React.ReactNode;
  /** 透传到最外层容器的额外 className，用于外部覆盖 / 追加样式。 */
  className?: string;
}

/**
 * 空状态展示组件。
 * 将标题、说明、图标、操作区按统一布局居中渲染，呈现虚线边框卡片样式。
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
  className = '',
}) => {
  return (
    // 最外层卡片：圆角 + 虚线边框 + 半透明卡片背景 + 居中 + 柔和阴影；合并外部 className。
    <div className={cn('rounded-2xl border border-dashed border-border/60 bg-card/50 px-6 py-10 text-center shadow-soft-card', className)}>
      {/* 可选图标区：仅在传入 icon 时渲染，使用青色着色并居中 */}
      {icon ? <div className="mb-4 flex justify-center text-cyan">{icon}</div> : null}
      {/* 主标题：基础字号、加粗、使用前景色 */}
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      {/* 可选说明文案：仅在传入 description 时渲染，限制最大宽度并居中，使用次级文字色 */}
      {description ? <p className="mx-auto mt-2 max-w-md text-sm text-secondary-text">{description}</p> : null}
      {/* 可选操作区：仅在传入 action 时渲染，用于放置引导操作的按钮等节点 */}
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </div>
  );
};
