/**
 * PageHeader.tsx
 *
 * 作用简述：
 *   一个通用的「页面头部 / 页眉」展示组件（Page Header）。
 *   统一承载页面级标题区的布局：可选的小标签（eyebrow）、主标题（title）、
 *   说明文案（description），以及右侧的操作区（actions，如按钮、筛选器等）。
 *   采用玻璃拟态面板样式（glass-panel-lg），并在窄屏下自动切换为纵向堆叠布局。
 *
 * 使用场景：
 *   - 各业务页面（如分析页、列表页、设置页）顶部的统一标题与操作入口区。
 *   - 需要在标题旁放置「返回 / 新建 / 刷新」等操作按钮的场合。
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/**
 * 组件属性定义。
 */
interface PageHeaderProps {
  /** 小标签 / 眉题（可选），通常是一行大写小字，用于标识区块或分类（如分类名、步骤名）。 */
  eyebrow?: string;
  /** 主标题（必填），页面级标题文案。 */
  title: string;
  /** 说明文案（可选），对标题做补充说明，限制最大宽度并适配响应式字号。 */
  description?: string;
  /** 操作区节点（可选），一般放入按钮、下拉等交互入口，位于标题区右侧。 */
  actions?: React.ReactNode;
  /** 透传到最外层容器的额外 className，用于外部覆盖 / 追加样式。 */
  className?: string;
}

/**
 * 页面头部组件。
 * 将眉题、标题、说明与操作区按统一布局渲染，窄屏纵向堆叠、宽屏左右分布。
 */
export const PageHeader: React.FC<PageHeaderProps> = ({
  eyebrow,
  title,
  description,
  actions,
  className = '',
}) => {
  return (
    // 最外层页眉容器：玻璃拟态大面板样式 + 内边距；合并外部 className。
    <header className={cn('glass-panel-lg px-5 py-5', className)}>
      {/* 内容行：默认纵向堆叠（flex-col），md 及以上切换为左右分布（标题左、操作右） */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          {/* 可选眉题：仅在传入 eyebrow 时渲染，使用大写小标签样式 */}
          {eyebrow ? <span className="label-uppercase">{eyebrow}</span> : null}
          {/* 主标题：大号加粗、紧凑字距、使用前景色；md 及以上放大字号 */}
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground md:text-3xl">{title}</h1>
          {/* 可选说明：仅在传入 description 时渲染，限制最大宽度并适配响应式字号，使用次级文字色 */}
          {description ? <p className="mt-2 max-w-2xl text-sm text-secondary-text md:text-base">{description}</p> : null}
        </div>
        {/* 可选操作区：仅在传入 actions 时渲染，使用 flex 自动换行并控制间距 */}
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
};
