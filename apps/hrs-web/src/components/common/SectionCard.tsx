/**
 * ===================================
 * 区块卡片组件（SectionCard）
 * ===================================
 *
 * 【功能介绍】
 * 通用「带标题的区块卡片」，用于把一页内的内容划分成若干语义区块（如「持仓概览」「近期成交」）。
 * 在统一卡片（Card）基础上，预置了标题区：可选小标签（subtitle）、主标题（title），
 * 以及标题右侧的操作区（actions，如「查看全部」「编辑」按钮）。
 *
 * 【设计要点】
 * 1. 基于基础 Card 封装（variant="bordered"、padding="md"），保持全站卡片视觉一致。
 * 2. 标题栏采用左右布局（flex justify-between）：左侧小标签 + 标题，右侧操作按钮；
 *    窄内容下通过 items-start 保证多行标题不挤压操作区。
 * 3. 透传 className 给底层 Card，便于外部微调间距或边框。
 *
 * 【使用方式】
 *   <SectionCard title="持仓概览" subtitle="PORTFOLIO" actions={<Button>查看</Button>}>
 *     <YourContent />
 *   </SectionCard>
 */

import type React from 'react';
import { Card } from '../basic/Card';

/** SectionCard 组件的 Props 定义 */
interface SectionCardProps {
  /** 区块主标题（必填） */
  title: string;
  /** 标题上方小标签（可选，如分类/英文标识） */
  subtitle?: string;
  /** 标题右侧操作区节点（可选，一般为按钮或链接） */
  actions?: React.ReactNode;
  /** 区块内容节点 */
  children: React.ReactNode;
  /** 透传到底层 Card 的额外类名 */
  className?: string;
}

/**
 * 区块卡片组件：在统一 Card 内渲染「标题栏 + 内容」。
 *
 * @param props - 组件属性
 * @param props.title - 主标题
 * @param props.subtitle - 小标签
 * @param props.actions - 操作区
 * @param props.children - 内容
 * @param props.className - 额外类名
 * @returns 带标题栏的区块卡片
 */
export const SectionCard: React.FC<SectionCardProps> = ({
  title,
  subtitle,
  actions,
  children,
  className = '',
}) => {
  return (
    // 底层卡片：统一边框 + 中等内边距
    <Card className={className} padding="md" variant="bordered">
      {/* 标题栏：左（小标签+标题）右（操作区）布局 */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          {/* 可选小标签：大写风格，作为区块分类提示 */}
          {subtitle ? <span className="label-uppercase">{subtitle}</span> : null}
          {/* 主标题：二级标题样式 */}
          <h2 className="mt-1 text-lg font-semibold text-foreground">{title}</h2>
        </div>
        {/* 可选操作区：靠右、不收缩，保证按钮不被挤变形 */}
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </div>
      {children}
    </Card>
  );
};
