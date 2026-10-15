/**
 * @file ScrollContainerContext.tsx
 * @description 滚动容器上下文：由应用主内容滚动容器（`Main` 内的 `main.hrs-page-container`）
 *   提供自身元素引用，供路由缓存出口在切页时保存 / 恢复各页滚动偏移。
 *   设计基准见 `documents/架构设计/frontend_route_keepalive.md`（ADR-002）。
 *
 * 采用显式 Context 而非按类名查找：契约类型安全，容器类名调整不会让滚动恢复静默失效。
 * 未包裹 Provider 时返回 null（调用方需判空跳过），保证单测可直接渲染缓存出口。
 */
import { createContext, useContext, type RefObject } from 'react';

/** 滚动容器元素引用；null 表示当前不在滚动容器子树内 */
const ScrollContainerContext = createContext<RefObject<HTMLElement | null> | null>(null);

export const ScrollContainerProvider = ScrollContainerContext.Provider;

/** 获取滚动容器元素引用；不在 Provider 子树内时返回 null */
// eslint-disable-next-line react-refresh/only-export-components -- useScrollContainerRef is a hook, co-located for context access
export function useScrollContainerRef(): RefObject<HTMLElement | null> | null {
  return useContext(ScrollContainerContext);
}
