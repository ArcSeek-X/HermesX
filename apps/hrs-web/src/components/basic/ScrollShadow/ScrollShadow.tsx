/**
 * @file ScrollShadow.tsx
 * @description 滚动边缘渐隐组件 ScrollShadow（复用单元，对齐 HeroUI Pro ScrollShadow 的 40px 渐隐语义）。
 *
 * 作用：把「可滚动容器的上下边缘随滚动位置做 mask 渐隐」封装成一个可直接丢的标签。
 *   组件本身渲染滚动容器元素（默认 div，可经 as 指定 nav/ul/section 等以保留语义，不额外包裹节点），
 *   内部自动挂 scroll 监听 + ResizeObserver，并在每次渲染后重算，确保内容增减（如菜单显隐）后
 *   不必等下一次滚动才出现渐隐。
 *
 * 使用场景：侧边导航、设置面板、列表、表格体等任意需要「边缘淡出避免生硬截断」的滚动区域。
 *   采用 mask 渐变（black=可见、transparent=透明），兼容玻璃/半透明主题；不依赖不透明底色。
 *
 * 注意：调用方需自行让该元素可滚动（如 overflow-y-auto）并具备确定高度（如 flex-1 min-h-0），
 *   渐隐高度由 size 控制（默认 40px）。
 *
 * @example
 * ```tsx
 * // 侧边导航：保留 <nav> 语义，无多余 DOM 节点
 * <ScrollShadow as="nav" className="flex-1 min-h-0 overflow-y-auto" aria-label="主菜单">
 *   {items}
 * </ScrollShadow>
 *
 * // 普通滚动面板（默认 div）
 * <ScrollShadow className="h-64 overflow-y-auto">...</ScrollShadow>
 * ```
 *
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-14
 */
import React, {
  forwardRef,
  useCallback,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { cn } from '../../../utils/cn';

export interface ScrollShadowProps extends Omit<React.HTMLAttributes<HTMLElement>, 'ref'> {
  /** 渲染的底层元素标签，默认 'div'；传 'nav'/'ul'/'section' 等以保留语义、不额外包裹节点 */
  as?: React.ElementType;
  /** 上下边缘渐隐高度(px)，默认 40，与 HeroUI Pro ScrollShadow 一致 */
  size?: number;
}

export const ScrollShadow = forwardRef<HTMLElement, ScrollShadowProps>(function ScrollShadow(
  { as: Tag = 'div', size = 40, className, style, children, ...rest },
  ref,
) {
  const innerRef = useRef<HTMLElement | null>(null);
  const [fade, setFade] = useState<{ top: boolean; bottom: boolean }>({ top: false, bottom: false });

  // 计算上下边缘是否仍有未滚动到的内容；1px 容差规避亚像素取整误判，状态无变化则跳过 setState
  const recompute = useCallback(() => {
    const el = innerRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const scrollable = scrollHeight > clientHeight + 1;
    const top = scrollable && scrollTop > 1;
    const bottom = scrollable && scrollTop + clientHeight < scrollHeight - 1;
    setFade((prev) => (prev.top === top && prev.bottom === bottom ? prev : { top, bottom }));
  }, []);

  // 合并外部 ref 与内部 ref（内部 ref 用于测量）
  const setRefs = useCallback(
    (node: HTMLElement | null) => {
      innerRef.current = node;
      if (typeof ref === 'function') ref(node);
      else if (ref) (ref as React.MutableRefObject<HTMLElement | null>).current = node;
    },
    [ref],
  );

  // 监听：滚动 + 容器尺寸变化（含宽度动画/折叠重排，这类不触发 React 重渲染）
  useLayoutEffect(() => {
    const el = innerRef.current;
    if (!el) return;
    el.addEventListener('scroll', recompute, { passive: true });
    const observer = new ResizeObserver(recompute);
    observer.observe(el);
    return () => {
      el.removeEventListener('scroll', recompute);
      observer.disconnect();
    };
  }, [recompute]);

  // 内容经 React 重渲染变化（如菜单增删跨过滚动阈值）后重算，避免要等下一次滚动才渐隐
  useLayoutEffect(() => {
    recompute();
  });

  // 按 top/bottom 组合生成 mask 渐变（三态互斥），同时设 maskImage + WebkitMaskImage（Safari）
  const shadowStyle = useMemo<React.CSSProperties | undefined>(() => {
    if (!fade.top && !fade.bottom) return undefined;
    const s = `${size}px`;
    const gradient =
      fade.top && fade.bottom
        ? `linear-gradient(to bottom, transparent, black ${s}, black calc(100% - ${s}), transparent)`
        : fade.top
          ? `linear-gradient(to bottom, transparent, black ${s})`
          : `linear-gradient(to bottom, black calc(100% - ${s}), transparent)`;
    return { maskImage: gradient, WebkitMaskImage: gradient };
  }, [fade, size]);

  return React.createElement(
    Tag,
    {
      ref: setRefs,
      className: cn(className),
      style: { ...style, ...shadowStyle },
      ...rest,
    },
    children,
  );
});
