/**
 * ===================================
 * Toast 视图层容器（ToastViewport）
 * ===================================
 *
 * 【功能介绍】
 * Toast（轻提示）的「视图层容器」，负责把一组 Toast 通知统一挂载到屏幕固定位置。
 * 它本身不管理通知的状态与生命周期，而是作为 portal 式的渲染锚点，承接由 Toast 上下文
 * （如 ToastProvider）通过 children 注入的所有 Toast 节点。
 *
 * 【设计要点】
 * 1. 固定定位：fixed + bottom-5 + right-5，使通知常驻视口右下角，不随页面滚动移动。
 * 2. 层级与穿透：z-50 保证浮于常规内容之上；pointer-events-none 让容器本身不拦截点击，
 *    各 Toast 内部再按需开启交互（如关闭按钮）。
 * 3. 尺寸约束：固定宽度（w-[360px]）并限制为视口宽度减 24px，避免在小屏上溢出。
 * 4. 纵向堆叠：用 flex-col + gap-3 让多条通知之间留有间距、依次排列。
 *
 * 【使用方式】
 *   通常由 ToastProvider 内部渲染，无需手动使用：
 *   <ToastViewport>{toasts.map(t => <ToastItem key={t.id} {...t} />)}</ToastViewport>
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** ToastViewport 组件的 Props 定义 */
interface ToastViewportProps {
  /** 待展示的 Toast 节点（一般来自 Toast 上下文的映射渲染） */
  children: React.ReactNode;
  /** 透传的额外类名 */
  className?: string;
}

/**
 * Toast 视图层容器：固定在右下角、纵向堆叠的 Toast 渲染容器。
 *
 * @param props - 组件属性
 * @param props.children - Toast 节点集合
 * @param props.className - 额外类名
 * @returns 固定在视口右下角的 Toast 容器
 */
export const ToastViewport: React.FC<ToastViewportProps> = ({ children, className = '' }) => {
  return (
    // 固定右下角 + 浮层层级 + 穿透点击 + 固定宽度与堆叠间距
    <div className={cn('pointer-events-none fixed bottom-5 right-5 z-50 flex w-[360px] max-w-[calc(100vw-24px)] flex-col gap-3', className)}>
      {children}
    </div>
  );
};
