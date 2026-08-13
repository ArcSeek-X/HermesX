/**
 * Tooltip.tsx
 *
 * 作用简述：
 *   一个轻量的「悬浮提示」组件（Tooltip）。
 *   当鼠标移入 / 键盘聚焦到触发元素（children）时，在视口中以 Fixed 定位
 *   渲染一段提示内容（content）；并会在接近视口边缘时自动翻转显示方向
 *   （上 / 下），同时支持窗口 resize、滚动时实时跟随重定位。提示体通过
 *   React Portal 挂载到 document.body，避免被父级 overflow / z-index 裁切。
 *
 * 使用场景：
 *   - 为图标、按钮、缩写等提供额外的解释性文案。
 *   - 需要无障碍支持（aria-describedby）与可聚焦（focusable）的提示场景。
 */

import type React from 'react';
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../utils/cn';

/**
 * 组件属性定义。
 */
interface TooltipProps {
  /** 提示内容（必填）；为空（falsy）时组件直接透传 children，不渲染任何提示。 */
  content: React.ReactNode;
  /** 触发元素（必填），即悬浮其上时展示提示的主体内容。 */
  children: React.ReactNode;
  /** 期望的提示出现方向，默认 'top'（上方）；空间不足时会自动翻转为反向。 */
  side?: 'top' | 'bottom';
  /** 是否允许触发元素可被 Tab 聚焦（用于键盘无障碍），默认 false。 */
  focusable?: boolean;
  /** 透传到触发元素（span）的额外 className。 */
  className?: string;
  /** 透传到提示体（span）的额外 className，用于定制提示外观。 */
  contentClassName?: string;
}

/**
 * 提示体的定位样式：视口坐标系下的 top / left（像素）。
 */
type TooltipStyle = {
  top: number;
  left: number;
};

/**
 * 悬浮提示组件。
 * 通过 refs 测量触发元素与提示体尺寸，计算 Fixed 定位并确保不被视口裁切，
 * 在 hover / focus 时显示，失焦 / Esc / 移出时隐藏。
 */
export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  side = 'top',
  focusable = false,
  className = '',
  contentClassName = '',
}) => {
  // 触发元素 DOM 引用，用于测量位置与尺寸。
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  // 提示体 DOM 引用，用于测量尺寸以计算定位。
  const tooltipRef = useRef<HTMLSpanElement | null>(null);
  // 生成稳定的唯一 id，用于 aria-describedby 无障碍关联。
  const tooltipId = useId();
  // 是否处于显示状态（hover / focus 触发展开）。
  const [open, setOpen] = useState(false);
  // 实际生效的显示方向（可能因视口空间不足而与 side 不同）。
  const [resolvedSide, setResolvedSide] = useState<'top' | 'bottom'>(side);
  // 提示体最终的 Fixed 定位（top / left，单位 px）。
  const [style, setStyle] = useState<TooltipStyle>({ top: 0, left: 0 });

  // 根据触发元素与提示体尺寸，计算提示体的定位，并在接近视口边缘时自动翻转方向、夹取到安全区域内。
  const updatePosition = useCallback(() => {
    const trigger = triggerRef.current;
    const tooltip = tooltipRef.current;
    if (!trigger || !tooltip) {
      return;
    }

    const triggerRect = trigger.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const gap = 10; // 触发元素与提示体之间的间距
    const margin = 8; // 提示体距视口边缘的安全留白

    let nextSide = side;
    // 先按期望方向计算 top：上方 = 触发器顶部 - 提示高度 - 间距；下方 = 触发器底部 + 间距。
    let top =
      side === 'top'
        ? triggerRect.top - tooltipRect.height - gap
        : triggerRect.bottom + gap;

    // 若期望在上方但会超出顶端，则翻转到底部。
    if (side === 'top' && top < margin) {
      nextSide = 'bottom';
      top = triggerRect.bottom + gap;
    } else if (side === 'bottom' && top + tooltipRect.height > viewportHeight - margin) {
      // 若期望在下方但会超出底端，则翻转回上方。
      nextSide = 'top';
      top = triggerRect.top - tooltipRect.height - gap;
    }

    // 水平方向：先让提示体相对触发器水平居中对齐。
    let left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;
    // 将 left / top 夹取到视口安全区域内（避免提示体溢出视口）。
    left = Math.max(margin, Math.min(left, viewportWidth - tooltipRect.width - margin));
    top = Math.max(margin, Math.min(top, viewportHeight - tooltipRect.height - margin));

    setResolvedSide(nextSide);
    setStyle({ top, left });
  }, [side]);

  // 展开时，在下一帧布局稳定后（raf）计算并应用定位，避免读取到未渲染 / 尺寸为 0 的提示体。
  useLayoutEffect(() => {
    if (!open) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      updatePosition();
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [open, content, updatePosition]);

  // 展开时监听视口变化（resize）与滚动（含捕获阶段，覆盖任意嵌套滚动容器），实时重定位。
  useEffect(() => {
    if (!open) {
      return;
    }

    const handleViewportChange = () => updatePosition();
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('scroll', handleViewportChange, true);

    return () => {
      window.removeEventListener('resize', handleViewportChange);
      window.removeEventListener('scroll', handleViewportChange, true);
    };
  }, [open, updatePosition]);

  // 无障碍 / 空内容处理：若没有提示内容，直接透传 children，不做任何包裹或提示。
  if (!content) {
    return <>{children}</>;
  }

  return (
    <>
      {/* 触发包裹元素：内联 flex，绑定 hover / focus / blur 事件控制展开，Esc 收起 */}
      <span
        ref={triggerRef}
        className={cn('inline-flex', className)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setOpen(false);
          }
        }}
        tabIndex={focusable ? 0 : undefined}
        /* 展开时通过 aria-describedby 关联到提示体 id，提升无障碍可读性 */
        aria-describedby={open ? tooltipId : undefined}
      >
        {children}
      </span>

      {/* 提示体：仅在浏览器环境且展开时，通过 Portal 挂载到 body，脱离父级布局流与裁切 */}
      {typeof document !== 'undefined' && open
        ? createPortal(
            <span
              ref={tooltipRef}
              id={tooltipId}
              role="tooltip"
              style={{
                position: 'fixed',
                top: style.top,
                left: style.left,
              }}
              className={cn(
                // 提示体样式：不可交互、高层级、限定宽度、圆角描边、半透明背景 + 模糊、柔和阴影
                'pointer-events-none z-[120] min-w-max max-w-[18rem] rounded-xl border border-border/70 bg-elevated/95 px-3 py-1.5 text-xs leading-5 text-foreground shadow-[0_16px_40px_rgba(3,8,20,0.18)] backdrop-blur-xl',
                // 根据最终方向设置 transform 原点，便于可能的动画缩放从正确侧展开
                resolvedSide === 'top' ? 'origin-bottom' : 'origin-top',
                contentClassName,
              )}
            >
              {content}
            </span>,
            document.body,
          )
        : null}
    </>
  );
};
