/**
 * Toast.tsx
 *
 * 作用简述：
 *   轻量命令式 Toast 组件
 *   视觉上参考 HeroUI Toast 风格：圆角卡片 + 语义色边/淡色底/图标 + 头部（图标+标题+关闭按钮）
 *   + 主体（描述+查看详情+右侧操作插槽），定位走视口浮层（placement 固定到上/下 × 左/中/右 6 方位）。
 *
 * 与 ApiErrorAlert 的区别：
 *   - ApiErrorAlert：内联插入页面 DOM 流（placement="inside"），由调用方就地渲染。
 *   - Toast：固定在视口角落，通过 <Toast /> 挂在 body 下的 portal 渲染，
 *     用命令式 showToast() 在任意位置（如 API 拦截器）触发，零第三方依赖。
 *
 * 用法：
 *   1. 应用根渲染一次 <Toast />（通常挂到 App.tsx）。
 *   2. 任意位置命令式调用，入参统一为单对象（含 title/description/variant/placement 等）：
 *        showToast({ title, description, variant: 'success', placement: 'top' })
 *     便捷方法（variant 预设，入参对象可不传 variant）：
 *        showToast.info({ title, description, placement })      // accent 风格
 *        showToast.success({ title, description, placement })
 *        showToast.warning({ title, description, placement })
 *        showToast.danger({ title, description, placement })
 */

import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CloseIcon } from '@heroui/react';
import AnimCard from '../common/Card/AnimCard';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';

/**
 * 浮层方位：上/下 × 左/中/右。
 */
export type ToastPlacement =
    | 'top start'
    | 'top'
    | 'top end'
    | 'bottom start'
    | 'bottom'
    | 'bottom end';

/** Toast 视觉风格 */
export type ToastVariant = 'default' | 'accent' | 'success' | 'warning' | 'danger';

/** Toast 内容与展示配置（命令式入参），同时作为 ToastContent 的内容契约 */
export interface ToastOptions {
    /** 主标题（必填） */
    title: string;
    /** 详细描述（必填） */
    description: string;
    /** 原始错误/详情：传了之后会在「查看详情」里展开 */
    rawMessage?: string;
    /** 头部图标：传 ReactNode 时优先用，否则按 variant 自动选 */
    icon?: React.ReactNode;
    /** 视觉风格，默认 default */
    variant?: ToastVariant;
    /** 内容区右侧操作按钮插槽 */
    action?: React.ReactNode;
    /** 自动关闭毫秒数，默认 3000；传 0 则不自动关闭 */
    duration?: number;
    /** 附加到外层卡片的 className */
    className?: string;
    /** 浮层方位，默认 "top" */
    placement?: ToastPlacement;
    }

/**
 * 把 placement 映射为 fixed 浮层的 inline style。
 * 用 inline style 而非 Tailwind 类，规避 Tailwind v4 JIT 对动态类名的扫描遗漏。
 */
function placementStyle(placement: ToastPlacement): React.CSSProperties {
    const base: React.CSSProperties = {
        position: 'fixed',
        zIndex: 9999,
        width: 'min(80vw, 400px)',
        pointerEvents: 'auto',
    };

    switch (placement) {
        case 'top start':
            return { ...base, top: 12, left: 16 };
        case 'top':
            return { ...base, top: 12, left: '50%', transform: 'translateX(-50%)' };
        case 'top end':
            return { ...base, top: 12, right: 16 };
        case 'bottom start':
            return { ...base, bottom: 12, left: 16 };
        case 'bottom':
            return { ...base, bottom: 12, left: '50%', transform: 'translateX(-50%)' };
        case 'bottom end':
        default:
            return { ...base, bottom: 12, right: 16 };
    }
}

/**
 * 各 variant 对应的语义色样式：
 *  - bg：AnimCard 外层背景/边框语义色（由外层带动淡色语义边）
 *  - surface：上层内容区卡片背景
 *  - icon / iconBg：状态图标文字色 / 圆形底
 *  - title：标题文字色
 */
const variantStylesConfig: Record<
    ToastVariant,
    { bg: string; surface: string; icon: string; iconBg: string; title: string }
> = {
    default: {
        bg: 'bg-border',
        surface: 'bg-elevated/96',
        icon: 'text-secondary-text',
        iconBg: 'bg-surface-2',
        title: 'text-foreground',
    },
    accent: {
        bg: 'bg-primary',
        surface: 'bg-elevated/96',
        icon: 'text-primary',
        iconBg: 'bg-primary/15',
        title: 'text-primary',
    },
    success: {
        bg: 'bg-success',
        surface: 'bg-elevated/96',
        icon: 'text-success',
        iconBg: 'bg-success/15',
        title: 'text-success',
    },
    warning: {
        bg: 'bg-warning',
        surface: 'bg-elevated/96',
        icon: 'text-warning',
        iconBg: 'bg-warning/15',
        title: 'text-warning',
    },
    danger: {
        bg: 'bg-danger',
        surface: 'bg-elevated/96',
        icon: 'text-danger',
        iconBg: 'bg-danger/15',
        title: 'text-danger',
    },
};

/**
 * 各 variant 对应的默认状态图标（HeroUI 风格描边 SVG）。
 * 注意：accent 与 default 共用同一「信息」图标（圆圈 + 竖线 + 圆点），差异仅由配色体现。
 */
function VariantIcon({ variant }: { variant: ToastVariant }): React.ReactElement {
    const cls = 'h-4 w-4';
    switch (variant) {
        case 'success':
            // 圆圈 + 勾
            return (
                <svg viewBox="0 0 24 24" fill="none" className={cls} stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M8 12.5l2.8 2.8L16 9.5" />
                </svg>
            );
        case 'warning':
            return (
                <svg viewBox="0 0 24 24" fill="none" className={cls} stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M12 3.5l9 16H3l9-16z" />
                    <path d="M12 10v4.5" />
                    <circle cx="12" cy="17.5" r="0.6" fill="currentColor" />
                </svg>
            );
        case 'danger':
            return (
                <svg viewBox="0 0 24 24" fill="none" className={cls} stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M9 9l6 6M15 9l-6 6" />
                </svg>
            );
        case 'accent':
        case 'default':
        default:
            return (
                <svg viewBox="0 0 24 24" fill="none" className={cls} stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 8v5" />
                    <circle cx="12" cy="16.2" r="0.6" fill="currentColor" />
                </svg>
            );
    }
}

/**
 * 单条 Toast 内容卡片（参考 HeroUI 风格），由 Toast 宿主渲染。
 *  - header：图标圈 + 标题，最右 X 关闭按钮
 *  - body：描述 + 「查看详情」（点击展开 rawMessage）+ 右侧 action 插槽
 *  - 内容区四周内缩 2px 露出外层语义色边；description 最多 3 行省略
 */
const ToastContent: React.FC<{
    variant?: ToastVariant;
    title: string;
    description: string;
    rawMessage?: string;
    icon?: React.ReactNode;
    action?: React.ReactNode;
    onDismiss: () => void;
    className?: string;
}> = ({ variant = 'default', title, description, rawMessage, icon, action, onDismiss, className }) => {
    const { t } = useUiLanguage();
    const [detailsOpen, setDetailsOpen] = useState(false);
    const variantStyles = variantStylesConfig[variant];

    // description 最多显示 3 行（CSS line-clamp），超出自动省略号。
    // 「查看详情」仍依赖传入的 rawMessage，用于展示完整原文。
    const mergedRaw = rawMessage?.trim() ?? '';
    const showDetails = !!(mergedRaw && mergedRaw.trim() && mergedRaw.trim() !== description.trim());

    return (
        <AnimCard
            className={cn(
                'hrs-toast-content relative w-full !min-h-0 overflow-hidden rounded-md shadow-md backdrop-blur',
                variantStyles.bg,
                className
            )}
        >
            {/* 上层内容区：左边内缩 8px（ml-[2]），露出外层语义色边 */}
            <div
                role={variant === 'danger' || variant === 'warning' ? 'alert' : 'status'}
                className={cn('flex w-full min-w-0 flex-col rounded ml-2 px-3 py-2', variantStyles.surface)}
            >
                {/* header：图标 + title + 关闭按钮（三者水平居中对齐） */}
                <div className="flex items-center gap-2.5">
                    <div
                        className={cn(
                            'inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
                            variantStyles.iconBg,
                            variantStyles.icon
                        )}
                    >
                        {icon ?? <VariantIcon variant={variant} />}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className={cn('truncate text-sm font-semibold leading-5', variantStyles.title)}>{title}</p>
                    </div>
                    <button
                        type="button"
                        aria-label={t('common.close')}
                        onClick={onDismiss}
                        className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-text transition hover:bg-surface-2 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    >
                        <CloseIcon className="h-3.5 w-3.5" />
                    </button>
                </div>

                {/* body：description + 查看详情 + action 插槽 */}
                <div className="mt-1 flex items-end gap-3 pl-[34px]">
                    <div className="min-w-0 flex-1">
                        <p className="line-clamp-3 text-xs leading-4 text-muted-text">{description}</p>
                        {showDetails ? (
                            <button
                                type="button"
                                onClick={() => setDetailsOpen((v) => !v)}
                                className={cn(
                                    'mt-1 inline-flex items-center gap-1 text-xs font-medium transition',
                                    variantStyles.icon,
                                    'hover:opacity-80'
                                )}
                                aria-expanded={detailsOpen}
                            >
                                <span className="text-xs leading-4">{detailsOpen ? '收起详情' : t('common.details')}</span>
                                <svg
                                    viewBox="0 0 12 12"
                                    fill="none"
                                    className={cn('h-3 w-3 transition-transform', detailsOpen && 'rotate-180')}
                                    stroke="currentColor"
                                    strokeWidth="1.6"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    aria-hidden="true"
                                >
                                    <path d="M3 4.5l3 3 3-3" />
                                </svg>
                            </button>
                        ) : null}
                    </div>
                    {action ? <div className="shrink-0">{action}</div> : null}
                </div>

                {/* 详情展开区 */}
                {showDetails && detailsOpen ? (
                    <div className="ml-[34px] mt-1 rounded-md border border-border/60 bg-surface-2/60 px-2 py-1">
                        <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-muted-text">
                            {mergedRaw}
                        </pre>
                    </div>
                ) : null}
            </div>
        </AnimCard>
    );
};

/* ------------------------------------------------------------------ *
 * 命令式 Toast：模块级队列 + 订阅宿主渲染 + showToast 触发。
 *   - 队列存储待渲染 Toast（含 placement/duration）
 *   - 通过 useSyncExternalStore 订阅，宿主按队列渲染
 * ------------------------------------------------------------------ */

interface ToastItem {
    id: string;
    options: ToastOptions;
}

let toastItems: ToastItem[] = [];
const listeners = new Set<() => void>();
let seq = 0;

function emitChange() {
    listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

function getSnapshot(): ToastItem[] {
    return toastItems;
}

/** showToast 及其便捷方法（variant 预设）的调用接口 */
export interface ShowToastAPI {
  /** 以单对象入参触发一个 Toast */
  (options: ToastOptions): string;
  /** info 便捷封装：固定 variant 为 accent（信息/强调风格） */
  info: (options: Omit<ToastOptions, 'variant'>) => string;
  /** success 便捷封装：固定 variant 为 success */
  success: (options: Omit<ToastOptions, 'variant'>) => string;
  /** warning 便捷封装：固定 variant 为 warning */
  warning: (options: Omit<ToastOptions, 'variant'>) => string;
  /** danger 便捷封装：固定 variant 为 danger */
  danger: (options: Omit<ToastOptions, 'variant'>) => string;
}

/** 触发函数本体：向模块级队列追加一条 Toast 并通知宿主刷新 */
function toastFn(options: ToastOptions): string {
  const id = `toast-${++seq}`;
  toastItems = [
    ...toastItems,
    {
      id,
      options,
    },
  ];
  emitChange();
  return id;
}

/**
 * 命令式 Toast 触发函数（应用入口）。
 *  - showToast({ ... })：通用，variant 由入参决定（默认 default）
 *  - showToast.info/success/warning/danger({ ... })：variant 预设便捷方法
 * @param options Toast 内容与展示配置（title/description/variant/placement/...）
 * @returns       toast id，可用于 dismissToast
 */
export const showToast: ShowToastAPI = Object.assign(toastFn, {
  info: (options: Omit<ToastOptions, 'variant'>): string => toastFn({ ...options, variant: 'accent' }),
  success: (options: Omit<ToastOptions, 'variant'>): string => toastFn({ ...options, variant: 'success' }),
  warning: (options: Omit<ToastOptions, 'variant'>): string => toastFn({ ...options, variant: 'warning' }),
  danger: (options: Omit<ToastOptions, 'variant'>): string => toastFn({ ...options, variant: 'danger' }),
});

/** 手动关闭指定 Toast。 */
export function dismissToast(id: string): void {
    toastItems = toastItems.filter((item) => item.id !== id);
    emitChange();
}

/** 关闭全部 Toast。 */
export function dismissAllToasts(): void {
    if (toastItems.length === 0) return;
    toastItems = [];
    emitChange();
}

/** 向后兼容：旧名 dismissErrorToast 等价于 dismissToast。 */
export function dismissErrorToast(id: string): void {
    dismissToast(id);
}

/**
 * 全局 Toast 宿主：在应用根渲染一次即可。
 * 内部用 useSyncExternalStore 订阅模块队列，通过 portal 把每条 toast 挂到 body 下：
 *  - placement 从 options 解构，用于视口定位；同方位多条 toast 自动堆叠（纵向累加 92px）
 *  - duration > 0 时注册自动关闭定时器；组件卸载时清理全部定时器
 *  - 空队列时渲染 null，避免无用 DOM
 */
export const Toast: React.FC = () => {
    const items = React.useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
    const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
    // 每个 placement 的堆叠计数，用于同方位多条 toast 的纵向偏移。
    const counters = new Map<ToastPlacement, number>();
    const rendered: React.ReactNode[] = [];

    // 注册自动关闭定时器 / 清理已消失 toast 的定时器
    React.useEffect(() => {
        items.forEach((item) => {
            const dur = item.options.duration ?? 3000;
            if (dur > 0 && !timers.current.has(item.id)) {
                const handle = setTimeout(() => dismissToast(item.id), dur);
                timers.current.set(item.id, handle);
            }
        });
        timers.current.forEach((handle, id) => {
            if (!items.some((i) => i.id === id)) {
                clearTimeout(handle);
                timers.current.delete(id);
            }
        });
    }, [items]);

    React.useEffect(() => {
        const map = timers.current;
        return () => {
            map.forEach((h) => clearTimeout(h));
            map.clear();
        };
    }, []);

    if (items.length === 0 || typeof document === 'undefined') {
        return null;
    }

    for (const item of items) {
        // placement 与 duration 仅用于定位/计时，不透传给 ToastContent。
        const { placement = 'top', ...contentOptions } = item.options;
        const idx = counters.get(placement) ?? 0;
        counters.set(placement, idx + 1);
        // 同方位堆叠：沿对应轴向累加 92px 间距（含卡片高度与间隔）。
        const stack: React.CSSProperties =
            placement.startsWith('top')
                ? { top: 12 + idx * 52 }
                : { bottom: 12 + idx * 52 };
        rendered.push(
            <div
                className="hrs-toast"
                key={item.id}
                style={{ ...placementStyle(placement), ...stack }}
                aria-live="polite"
            >
                <ToastContent
                    {...contentOptions}
                    onDismiss={() => dismissToast(item.id)}
                />
            </div>
        );
    }

    return createPortal(<>{rendered}</>, document.body);
};
