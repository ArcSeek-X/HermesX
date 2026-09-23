/**
 * @file PageHeader.tsx
 * @description 通用页眉组件：统一承载页面级标题区的布局（可选眉题 eyebrow、主标题 title、
 *   说明 description 与右侧操作区 rightSlot），窄屏纵向堆叠、宽屏左右分布。外层容器复用 AnimCard
 *   的卡片描边与入场动画，便于各业务页面顶部保持一致的标题与操作入口。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-23
 */

import type React from 'react';
import { cn } from '../../utils/cn';
import AnimCard from './Card/AnimCard';

/** PageHeader 组件入参。 */
interface PageHeaderProps {
  /** 小标签 / 眉题，可选；通常是一行大写小字，用于标识区块或分类（如分类名、步骤名）。默认不显示。 */
  eyebrow?: string;
  /** 主标题，必填；页面级标题文案。 */
  title: string;
  /** 说明文案，可选；对标题做补充说明，限制最大宽度并适配响应式字号。默认不显示。 */
  description?: string;
  /** 右侧插槽节点，可选；一般放入按钮、下拉等交互入口，位于标题区右侧。参考 TabNav 的 rightSlot 封装形式（不收缩、垂直居中），内部排版交由调用方控制。默认不渲染。 */
  rightSlot?: React.ReactNode;
  /** 透传到最外层 AnimCard 容器的额外 className，用于外部覆盖 / 追加样式。默认 ''。 */
  className?: string;
}

/**
 * 渲染页面头部：组装眉题、标题、说明与操作区，窄屏纵向堆叠、宽屏左右分布。
 * 外层复用 AnimCard 提供卡片描边与淡入上移入场动画；语义标题区由内部 <header> 承载。
 *
 * @param props - 组件属性，详见 PageHeaderProps
 */
export const PageHeader: React.FC<PageHeaderProps> = ({
  eyebrow,
  title,
  description,
  rightSlot,
  className = '',
}) => {
  return (
    <AnimCard className={cn('px-4 py-4', className)}>
      {/* 语义标题区；w-full 抵消 AnimCard 根节点 flex 对子项宽度的收缩，保证宽屏下操作区贴右 */}
      <header className="w-full">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            {eyebrow ? <span className="text-xs leading-none tracking-[0.3em] uppercase">{eyebrow}</span> : null}
            <h1 className="mt-2 text-xl font-semibold tracking-tight text-foreground md:text-2xl">{title}</h1>
            {description ? <p className="mt-3 max-w-2xl text-sm text-muted-text md:text-base">{description}</p> : null}
          </div>
          {/* 右侧插槽由 rightSlot 承载，参考 TabNav 的 hrs-tab-slot 封装：不收缩、垂直居中，内部排版交由调用方 */}
          {rightSlot && <div className="hrs-pageheader-slot flex shrink-0 items-center gap-2">{rightSlot}</div>}
        </div>
      </header>
    </AnimCard>
  );
};
