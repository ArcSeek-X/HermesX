/**
 * ===================================
 * 吸底操作栏组件（StickyActionBar）
 * ===================================
 *
 * 【功能介绍】
 * 一个「吸底（sticky）操作栏」容器，用于把一组操作按钮（如保存 / 取消 / 提交）固定在内容底部，
 * 随页面滚动始终可见，提升长表单或长列表场景下的操作可达性。
 *
 * 【设计要点】
 * 1. 吸底定位：sticky + bottom-4 + z-20，使其悬浮在内容之上；配合 backdrop-blur 毛玻璃背景，
 *    即使下方内容滚动经过也能保持可读性。
 * 2. 视觉层次：半透明卡片背景（bg-card/85）+ 柔和阴影（shadow-soft-card）+ 细边框，
 *    与页面其它部分形成轻微分割而不突兀。
 * 3. 操作区布局：内部统一 flex 右对齐 + 自动换行（flex-wrap），按钮过多时自动折行而非溢出。
 * 4. 纯容器：本身不含按钮，仅负责布局与样式，具体按钮由 children 传入，复用性强。
 *
 * 【使用方式】
 *   <StickyActionBar>
 *     <Button variant="secondary">取消</Button>
 *     <Button variant="primary">保存</Button>
 *   </StickyActionBar>
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** StickyActionBar 组件的 Props 定义 */
interface StickyActionBarProps {
  /** 操作按钮等子节点 */
  children: React.ReactNode;
  /** 透传的额外类名，用于覆盖/追加样式 */
  className?: string;
}

/**
 * 吸底操作栏组件。
 *
 * @param props - 组件属性
 * @param props.children - 操作区子节点
 * @param props.className - 额外类名
 * @returns 吸底固定、毛玻璃背景的操作栏容器
 */
export const StickyActionBar: React.FC<StickyActionBarProps> = ({ children, className = '' }) => {
  return (
    // 外层吸底容器：sticky 定位 + 毛玻璃 + 圆角卡片样式
    <div className={cn('sticky bottom-4 z-20 rounded-2xl border border-subtle bg-card/85 p-3 shadow-soft-card backdrop-blur-md', className)}>
      {/* 内部操作区：右对齐 + 自动换行，承载具体按钮 */}
      <div className="flex flex-wrap items-center justify-end gap-2">{children}</div>
    </div>
  );
};
