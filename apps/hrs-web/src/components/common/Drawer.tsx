/**
 * ===================================
 * 侧边抽屉组件（Drawer）
 * ===================================
 *
 * 【功能介绍】
 * 从屏幕左侧或右侧滑出的全屏遮罩抽屉（侧边面板），常用于展示详情视图（DETAIL VIEW）、
 * 表单、筛选面板等需要临时占用较大空间但不离开当前页面的场景。
 * 组件自带遮罩层（backdrop）、关闭按钮、标题区与可滚动内容区，并支持键盘 Esc 关闭、
 * 多抽屉叠加时的 body 滚动锁定管理。
 *
 * 【设计要点】
 * 1. 渲染策略：isOpen 为 false 时直接返回 null，不挂载任何 DOM，避免无谓的样式与事件开销。
 * 2. 滑入方向：通过 side 控制从 'left'（左侧）或 'right'（右侧）滑入，配合 animate-slide-in-* 动画。
 * 3. 无障碍（a11y）：抽屉主体使用 role="dialog" + aria-modal="true"，标题通过 aria-labelledby 关联；
 *    关闭按钮带 aria-label，遮罩容器 role="presentation"。
 * 4. 全局滚动锁定（body overflow）：
 *    - 用模块级计数器 activeDrawerCount 跟踪当前打开的抽屉数量；
 *    - 第一个抽屉打开时锁定 body 滚动（overflow: hidden），最后一个关闭时恢复；
 *    - 这样多个抽屉可安全叠加，不会因其中一个关闭而误解除滚动锁定。
 * 5. 键盘交互：抽屉打开时监听 keydown，按下 Esc 触发 onClose；卸载时自动移除监听。
 * 6. 样式分层：zIndex 默认 50，可通过 props 覆盖以适配不同层级的遮罩需求；
 *    遮罩层支持 backdropClassName 自定义（如调透明度、模糊强度）。
 *
 * 【使用方式】
 *   <Drawer
 *     isOpen={open}
 *     onClose={() => setOpen(false)}
 *     title="板块详情"
 *     side="right"
 *     width="max-w-2xl"
 *   >
 *     <YourDetailContent />
 *   </Drawer>
 */

import type React from 'react';
import { useEffect, useCallback } from 'react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';

/**
 * 模块级计数器：记录当前处于打开状态的抽屉数量。
 * 用于协调「body 滚动锁定」——只有第一个打开的抽屉上锁、最后一个关闭的抽屉解锁，
 * 避免多个抽屉叠加时彼此误解除滚动锁定。
 */
let activeDrawerCount = 0;

/** Drawer 组件的 Props 定义 */
interface DrawerProps {
  /** 是否打开抽屉；为 false 时组件返回 null，不渲染任何内容 */
  isOpen: boolean;
  /** 关闭抽屉的回调（点击遮罩、关闭按钮或按下 Esc 时触发） */
  onClose: () => void;
  /** 抽屉标题；为空时不渲染标题区（仅关闭按钮） */
  title?: string;
  /** 抽屉内容区子节点 */
  children: React.ReactNode;
  /** 抽屉宽度类名（Tailwind），默认 max-w-2xl */
  width?: string;
  /** 抽屉整体堆叠层级 z-index，默认 50 */
  zIndex?: number;
  /** 滑入方向：'left' 左侧 / 'right' 右侧，默认 'right' */
  side?: 'left' | 'right';
  /** 遮罩层自定义类名（可覆盖透明度、模糊等） */
  backdropClassName?: string;
}

/**
 * 侧边抽屉组件
 *
 * 渲染结构（由外到内）：
 * - 最外层 fixed 全屏容器（承载 z-index 与定位）
 *   - 遮罩层（backdrop）：点击即关闭，支持自定义样式
 *   - 抽屉面板容器：按 side 决定贴左/贴右并控制动画
 *     - 标题栏：DETAIL VIEW 小标签 + 标题 + 关闭按钮
 *     - 内容区：flex-1 + overflow-y-auto，内部内容可滚动
 *
 * @param props - 组件属性
 * @param props.isOpen - 是否打开
 * @param props.onClose - 关闭回调
 * @param props.title - 标题（可选）
 * @param props.children - 内容节点
 * @param props.width - 宽度类名
 * @param props.zIndex - 层级
 * @param props.side - 滑入方向
 * @param props.backdropClassName - 遮罩自定义类名
 * @returns 打开时返回抽屉 UI，关闭时返回 null
 */
export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  width = 'max-w-2xl',
  zIndex = 50,
  side = 'right',
  backdropClassName,
}) => {
  const { t } = useUiLanguage();

  // 键盘交互：抽屉打开时监听 Esc，按下则触发关闭。
  // 用 useCallback 缓存，保证 effect 依赖稳定，避免重复绑定。
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      // 绑定 Esc 关闭监听
      document.addEventListener('keydown', handleKeyDown);
      // 打开抽屉计数 +1
      activeDrawerCount++;
      // 仅当这是第一个打开的抽屉时，锁定 body 滚动
      if (activeDrawerCount === 1) {
        document.body.style.overflow = 'hidden';
      }

      // 卸载/关闭时清理：移除监听、计数 -1，最后一个关闭时恢复 body 滚动
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        activeDrawerCount--;
        if (activeDrawerCount === 0) {
          document.body.style.overflow = '';
        }
      };
    }
  }, [isOpen, handleKeyDown]);

  // 关闭状态：不渲染任何内容
  if (!isOpen) return null;

  // 标题对应的 id，供 aria-labelledby 关联，提升无障碍可读性
  const titleId = title ? `drawer-title-${side}` : undefined;
  // 根据滑入方向决定面板贴左还是贴右、内容水平对齐方式
  const sidePositionClass = side === 'left' ? 'left-0 justify-start' : 'right-0 justify-end';
  // 左侧抽屉用右边框、右侧抽屉用左边框（视觉上贴着屏幕边缘）
  const borderClass = side === 'left' ? 'border-r' : 'border-l';

  return (
    <div className="fixed inset-0 overflow-hidden" style={{ zIndex }} role="presentation">
      {/* 遮罩层：半透明 + 模糊，点击即关闭抽屉 */}
      <div
        className={cn(
          'absolute inset-0 bg-background/80 backdrop-blur-sm transition-opacity duration-300',
          backdropClassName,
        )}
        onClick={onClose}
      />

      {/* 抽屉面板容器：占满高度，按方向贴边并应用宽度限制 */}
      <div className={cn('absolute inset-y-0 flex w-full', sidePositionClass, width)}>
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className={cn(
            'relative flex w-full flex-col bg-card',
            borderClass,
            side === 'right' ? 'border-border/80' : 'border-border/70 shadow-2xl',
            // 根据方向应用不同滑入动画
            side === 'left' ? 'animate-slide-in-left' : 'animate-slide-in-right'
          )}
        >
          {/* 标题栏：左侧 DETAIL VIEW 标签 + 标题，右侧关闭按钮 */}
          <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
            {title ? (
              <div>
                <span className="label-uppercase">DETAIL VIEW</span>
                <h2 id={titleId} className="mt-1 text-lg font-semibold text-foreground">{title}</h2>
              </div>
            ) : <div />}
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/80 text-secondary-text transition-colors hover:bg-hover hover:text-foreground"
              aria-label={t('common.closeDrawer')}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          {/* 内容区：占据剩余空间并可在内部纵向滚动 */}
          <div className="flex-1 overflow-y-auto p-6">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};
