/**
 * Toolbar.tsx
 *
 * 作用简述：
 *   一个通用的「工具条 / 操作栏」布局组件（Toolbar）。
 *   将一组操作类元素按「左区（left）」与「右区（right）」分列，常用于页面内
 *   的筛选、搜索、批量操作、主行动按钮等的承载。采用玻璃拟态面板样式
 *   （glass-panel），窄屏下左右区纵向堆叠，宽屏下左右分布、右区末端对齐。
 *
 * 使用场景：
 *   - 列表页 / 分析页顶部的筛选器 + 操作按钮组合。
 *   - 任意需要将操作入口在水平两端分布的工具栏区域。
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/**
 * 组件属性定义。
 */
interface ToolbarProps {
  /** 左区内容（可选），通常放置筛选、搜索、标题类元素，flex 自动换行。 */
  left?: React.ReactNode;
  /** 右区内容（可选），通常放置主操作按钮，宽屏下向右（末端）对齐。 */
  right?: React.ReactNode;
  /** 透传到最外层容器的额外 className，用于外部覆盖 / 追加样式。 */
  className?: string;
}

/**
 * 工具条组件。
 * 将左右两区按统一布局渲染，窄屏纵向堆叠、宽屏左右分布，承载操作类元素。
 */
export const Toolbar: React.FC<ToolbarProps> = ({ left, right, className = '' }) => {
  return (
    // 最外层工具条容器：玻璃面板样式；默认纵向堆叠（flex-col），md 及以上切换为左右分布。
    <div className={cn('glass-panel flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between', className)}>
      {/* 左区：flex 自动换行并控制子项间距 */}
      <div className="flex flex-wrap items-center gap-2">{left}</div>
      {/* 右区：flex 自动换行；宽屏下 md:justify-end 使内容靠右（末端）对齐 */}
      <div className="flex flex-wrap items-center gap-2 md:justify-end">{right}</div>
    </div>
  );
};
