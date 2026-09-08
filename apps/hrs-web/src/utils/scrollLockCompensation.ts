/**
 * scrollLockCompensation.ts
 * ------------------------------------------------------------
 * 解决「弹层锁滚动 → 页面横向抖动」。
 *
 * 现象：react-aria 打开 select / popover / modal 时会给 <html> 注入
 *       overflow: hidden 锁滚动，纵向滚动条随之消失 → 内容可视宽度
 *       +scrollbar 宽（约 15px）→ 整页向右拉伸、抖动。
 *
 * 方案：检测到 <html> 被锁滚动时，同步补一个等宽的 padding-right，
 *       使内容区宽度与锁定前完全一致 → 抖动消除；解锁时撤掉该 padding。
 *       锁滚动行为本身完整保留（背景依然完全不能动）。
 *
 * 为什么不用纯 CSS：
 *   - scrollbar-gutter: stable 无效 —— 该属性只在 overflow 为 scroll / auto
 *     时生效，被改成 overflow: hidden 后直接失效，滚动条槽一起消失（实机验证）。
 *   - overflow: auto !important 会让锁滚动彻底失效（背景仍可滚），不合需求。
 *
 * 时机：MutationObserver 回调是微任务，在当前任务结束、浏览器绘制之前执行，
 *       因此 padding 与 overflow 在同一帧落地，不会出现「先抖一下再补」的闪烁。
 * ------------------------------------------------------------
 */

/** 用探针元素测量经典滚动条宽度：与页面当前是否有滚动条无关，结果确定（叠加式滚动条系统为 0） */
function measureScrollbarWidth(): number {
    const probe = document.createElement('div');
    probe.style.cssText =
        'position:absolute;top:-9999px;width:100px;height:100px;overflow:scroll;visibility:hidden;';
    document.body.appendChild(probe);
    const width = probe.offsetWidth - probe.clientWidth;
    probe.remove();
    return width;
}

/** <html> 当前是否处于锁滚动状态（读最终生效值，兼容 inline 与样式表两种注入方式） */
function isScrollLocked(): boolean {
    const overflowY = window.getComputedStyle(document.documentElement).overflowY;
    return overflowY === 'hidden' || overflowY === 'clip';
}

/** 内容是否纵向溢出 —— 即锁定前 <html> 确实存在滚动条，才需要补偿 */
function hasVerticalOverflow(): boolean {
    const html = document.documentElement;
    return html.scrollHeight > html.clientHeight;
}

let scrollbarWidth = 0;
/** 本次由我们加上的补偿量（用于解锁时精确撤销，不误伤外部已有的 padding-right） */
let appliedPadding = 0;
/** 防止自己的样式写入再次触发 observer 造成回环 */
let syncing = false;

function syncLockCompensation(): void {
    if (syncing) return;
    syncing = true;
    const html = document.documentElement;
    try {
        const shouldCompensate = isScrollLocked() && hasVerticalOverflow() && scrollbarWidth > 0;

        if (shouldCompensate) {
            if (appliedPadding !== scrollbarWidth) {
                html.style.paddingRight = `${scrollbarWidth}px`;
                appliedPadding = scrollbarWidth;
            }
            return;
        }

        if (appliedPadding > 0) {
            // 只减掉自己加的那一份，保留外部本来就有的 padding-right
            const current = parseFloat(html.style.paddingRight) || 0;
            const next = Math.max(0, current - appliedPadding);
            html.style.paddingRight = next > 0 ? `${next}px` : '';
            appliedPadding = 0;
        }
    } finally {
        syncing = false;
    }
}

let observer: MutationObserver | null = null;

/**
 * 初始化滚动锁补偿（应用入口调用一次即可）。
 *
 * 监听 <html> 的 style / class 变化：react-aria 注入 overflow: hidden 时补
 * padding-right，解锁时撤销。视口尺寸变化会重新测量滚动条宽度。
 *
 * @returns 清理函数（断开监听、移除已加的 padding）
 */
export function initScrollLockCompensation(): () => void {
    if (typeof window === 'undefined') return () => {};

    // 幂等：重复调用先断开旧的，避免 StrictMode / HMR 叠加多个 observer
    observer?.disconnect();

    scrollbarWidth = measureScrollbarWidth();

    observer = new MutationObserver(() => {
        syncLockCompensation();
    });
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['style', 'class'],
    });

    const handleResize = () => {
        scrollbarWidth = measureScrollbarWidth();
        syncLockCompensation();
    };
    window.addEventListener('resize', handleResize);

    return () => {
        observer?.disconnect();
        observer = null;
        window.removeEventListener('resize', handleResize);
        const html = document.documentElement;
        if (appliedPadding > 0) {
            const current = parseFloat(html.style.paddingRight) || 0;
            const next = Math.max(0, current - appliedPadding);
            html.style.paddingRight = next > 0 ? `${next}px` : '';
            appliedPadding = 0;
        }
    };
}
