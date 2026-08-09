/**
 * 窗口宽度监听 Hook
 *
 * 监听浏览器窗口宽度变化，返回当前宽度值
 * 使用防抖（默认 150ms）避免频繁触发
 *
 * 使用场景：
 * - 响应式布局：根据窗口宽度切换组件渲染策略
 * - 图表适配：小屏幕时隐藏刻度、调整间距
 * - 移动端检测：宽度小于阈值时启用移动端样式
 *
 * @param debounceMs - 防抖延迟（毫秒），默认 150ms
 * @returns 当前窗口宽度（px）
 *
 * @example
 * ```typescript
 * const width = useWindowWidth();
 * const isMobile = width < 768;
 * const isSmallScreen = width < 1000;
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/** 获取当前窗口宽度（SSR 安全） */
function getWindowWidth(): number {
  if (typeof window === 'undefined') return 0;
  return window.innerWidth;
}

export function useWindowWidth(debounceMs = 150): number {
  const [width, setWidth] = useState(getWindowWidth);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleResize = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = setTimeout(() => {
      setWidth(getWindowWidth());
    }, debounceMs);
  }, [debounceMs]);

  useEffect(() => {
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, [handleResize]);

  return width;
}
