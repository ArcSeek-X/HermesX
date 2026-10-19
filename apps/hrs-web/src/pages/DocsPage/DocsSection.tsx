/**
 * DocsSection 容器：统一承载「标题 + 说明 + 演示」卡片区块，供各文档页复用。
 */

import React, { type ReactNode } from 'react';

/** 示例区块容器属性 */
interface DocsSectionProps {
  /** 区块标题，展示为区块内二级标题 */
  title: string;
  /** 区块说明，展示在标题下方；支持富文本（如行内 <code>） */
  description?: ReactNode;
  /** 区块演示内容 */
  children: ReactNode;
}

/**
 * 组件文档页示例区块容器。
 *
 * 以统一规格承载「标题 + 说明 + 演示内容」：圆角边框卡片、标题使用次级字重、
 * 说明使用弱化小字号。供所有 Docs_* 文档页复用，避免每个页面重复相同的布局结构。
 */
export const DocsSection: React.FC<DocsSectionProps> = ({ title, description, children }) => (
  <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
    <h2 className="text-sm font-medium text-primary-text">{title}</h2>
    {description ? <p className="text-xs text-muted">{description}</p> : null}
    {children}
  </section>
);

export default DocsSection;
