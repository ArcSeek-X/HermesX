/**
 * screenfull.tsx
 * ------------------------------------------------------------
 * 文件作用：
 *   基于 screenfull.js 封装的全屏 React 组件与 Hook，用于把某个
 *   容器（或整篇文档）一键切换为浏览器全屏模式；按 ESC 由浏览器
 *   原生退出全屏，无需额外逻辑。
 *
 * 使用场景：
 *   - 需要"点击区域即全屏、按 ESC 退出"的交互（如图表、背景、
 *     视频、看板等大屏展示区块）。
 *   - 统一处理各浏览器对 Fullscreen API 的前缀/行为差异；当浏览器
 *     不支持全屏时自动降级为无操作，不抛错、不阻塞交互。
 *
 * 依赖：
 *   - screenfull：对原生 requestFullscreen / exitFullscreen 的跨浏览器
 *     封装，v6 自带 TypeScript 类型声明，无需额外 @types 依赖。
 * ------------------------------------------------------------
 * @author Lensgcx (GaoCangxiong)
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import screenfull from 'screenfull';
import { cn } from '../../../utils/cn';

/** Screenfull 组件属性。 */
export interface ScreenfullProps {
  /** 是否将整篇文档（document.documentElement）作为全屏目标，而非当前容器自身。默认 false（全屏当前容器）。 */
  fullDocument?: boolean;
  /** 全屏状态变化回调，参数为当前是否处于全屏态。默认不处理。 */
  onFullscreenChange?: (isFullscreen: boolean) => void;
  /** 容器自定义类名，可追加 / 覆盖默认样式。默认 ''。 */
  className?: string;
  /** 容器子节点；点击容器任意位置即可切换全屏。默认不渲染子节点。 */
  children?: ReactNode;
}

/** useScreenfull Hook 的返回值结构。 */
export interface UseScreenfullResult {
  /** 当前是否处于全屏态 */
  isFullscreen: boolean;
  /** 当前浏览器是否支持 Fullscreen API（不支持时所有方法均为无操作） */
  isEnabled: boolean;
  /** 进入全屏；未传 target 时默认全屏整篇文档 */
  enter: (target?: Element | null) => void;
  /** 退出全屏 */
  exit: () => void;
  /** 在当前全屏态间切换；未传 target 时默认作用于整篇文档 */
  toggle: (target?: Element | null) => void;
}

/**
 * 全屏控制 Hook。
 * 订阅 screenfull 的 change 事件以同步全屏态，并返回 enter / exit /
 * toggle 方法，供任意按钮或交互触发，而不局限于点击某个容器。
 */
export function useScreenfull(): UseScreenfullResult {
  // 当前全屏态，驱动渲染与回调
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 将 screenfull 原生事件同步进 React state
  const handleChange = useCallback(() => {
    setIsFullscreen(screenfull.isFullscreen);
  }, []);

  // 挂载时订阅 change 事件，卸载时解绑，避免事件泄露
  useEffect(() => {
    if (!screenfull.isEnabled) return;
    screenfull.on('change', handleChange);
    return () => {
      screenfull.off('change', handleChange);
    };
  }, [handleChange]);

  // 进入全屏：浏览器不支持或目标为空时直接返回
  const enter = useCallback((target?: Element | null) => {
    if (!screenfull.isEnabled) return;
    const el = target ?? document.documentElement;
    if (!el) return;
    void screenfull.request(el);
  }, []);

  // 退出全屏：仅在已支持时调用
  const exit = useCallback(() => {
    if (screenfull.isEnabled) void screenfull.exit();
  }, []);

  // 切换全屏：浏览器不支持或目标为空时直接返回
  const toggle = useCallback((target?: Element | null) => {
    if (!screenfull.isEnabled) return;
    const el = target ?? document.documentElement;
    if (!el) return;
    void screenfull.toggle(el);
  }, []);

  return { isFullscreen, isEnabled: screenfull.isEnabled, enter, exit, toggle };
}

/**
 * 全屏切换组件。
 * 将 children 包裹进一个容器，点击容器任意位置即在当前容器
 * （或由 fullDocument 指定的整篇文档）上切换全屏；ESC 由浏览器
 * 原生处理退出。内部借助 useScreenfull 同步全屏态并向上回调。
 */
export const Screenfull: React.FC<ScreenfullProps> = ({
  fullDocument = false,
  onFullscreenChange,
  className = '',
  children,
}) => {
  // 容器 DOM 引用，作为非文档模式下的全屏目标
  const containerRef = useRef<HTMLDivElement>(null);
  const { isFullscreen, toggle } = useScreenfull();

  // 全屏态变化时向上回调（首次挂载若已全屏也会触发一次）
  useEffect(() => {
    onFullscreenChange?.(isFullscreen);
  }, [isFullscreen, onFullscreenChange]);

  // 点击容器切换全屏：文档模式用 documentElement，否则用当前容器
  const handleClick = useCallback(() => {
    const target = fullDocument ? document.documentElement : containerRef.current;
    toggle(target);
  }, [fullDocument, toggle]);

  return (
    <div ref={containerRef} onClick={handleClick} className={cn('relative', className)}>
      {children}
    </div>
  );
};
