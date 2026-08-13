/**
 * ===================================
 * 滚动容器组件（ScrollArea）
 * ===================================
 *
 * 【功能介绍】
 * 一个轻量的「可滚动区域」封装组件。用于在不依赖第三方 virtual-list 库的简单场景下，
 * 将一片内容限制为「内部纵向滚动」，并提供统一的自定义滚动条样式（custom-scrollbar）。
 * 常用于对话框、抽屉、卡片列表等需要固定高度并在内部滚动的容器。
 *
 * 【设计要点】
 * 1. 双层结构：外层容器负责「占位 + 约束最小高度（min-h-0 / flex-1）」，
 *    内层 viewport 负责实际滚动（overflow-y-auto + custom-scrollbar）。
 * 2. 受控滚动：通过 viewportRef 暴露内层 DOM 引用、onScroll 透传滚动事件，方便父组件做
 *    滚动监听、触底加载、滚动位置记忆等。
 * 3. 测试与可观测：支持 testId 注入 data-testid，便于自动化测试定位滚动区。
 *
 * 【使用方式】
 *   <ScrollArea className="h-64" onScroll={handleScroll}>
 *     <LongList />
 *   </ScrollArea>
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** ScrollArea 组件的 Props 定义 */
interface ScrollAreaProps {
  /** 滚动区域内容节点 */
  children: React.ReactNode;
  /** 外层容器自定义类名（如控制高度、flex 行为） */
  className?: string;
  /** 内层滚动视口自定义类名（如控制内边距） */
  viewportClassName?: string;
  /** 注入到滚动视口的 data-testid，用于测试定位 */
  testId?: string;
  /** 暴露内层滚动视口的 DOM 引用 */
  viewportRef?: React.Ref<HTMLDivElement>;
  /** 滚动事件回调（透传到内层视口） */
  onScroll?: React.UIEventHandler<HTMLDivElement>;
}

/**
 * 滚动容器组件
 *
 * 结构：
 * - 外层 div：min-h-0 + flex-1 + overflow-hidden，作为占位与高度约束
 * - 内层 div（viewport）：h-full + overflow-y-auto + custom-scrollbar，承载真实滚动
 *
 * @param props - 组件属性
 * @param props.children - 内容节点
 * @param props.className - 外层容器类名
 * @param props.viewportClassName - 内层视口类名
 * @param props.testId - 测试 id
 * @param props.viewportRef - 视口 DOM 引用
 * @param props.onScroll - 滚动回调
 * @returns 带内部滚动能力与统一滚动条样式的容器
 */
export const ScrollArea: React.FC<ScrollAreaProps> = ({
  children,
  className,
  viewportClassName,
  testId,
  viewportRef,
  onScroll,
}) => {
  return (
    // 外层：约束最小高度并隐藏溢出，确保内部滚动视口可正确获得高度
    <div className={cn('min-h-0 flex-1 overflow-hidden', className)}>
      {/* 内层视口：实际承载滚动，套用项目统一自定义滚动条 */}
      <div
        ref={viewportRef}
        data-testid={testId}
        onScroll={onScroll}
        className={cn('h-full overflow-y-auto custom-scrollbar', viewportClassName)}
      >
        {children}
      </div>
    </div>
  );
};
