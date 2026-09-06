/**
 * eventTheme.ts
 * ------------------------------------------------------------
 * 消息日历「重要级 → 色板」映射：月 / 周 / 日网格视图与 List 视图**共用**。
 *
 * 为什么要单独抽一个模块：
 * - `LiveCalendar.tsx`（月/周/日，基于 FullCalendar）与 `LiveCalendarListView.tsx`
 *   （List 视图，自绘）都要按 `importance` 取同一套配色；
 * - 若两边各存一份，改色时极易漏改，两套视觉悄悄漂移；
 * - 若留在 `LiveCalendar.tsx` 由 List 组件反向 import，会形成
 *   `LiveCalendar → LiveCalendarListView → LiveCalendar` **循环依赖**
 *   （LiveCalendar 渲染 List 视图依赖它，它又回来取色板）。
 * 因此下沉为同目录的叶子模块，两个视图各自单向依赖它，无环。
 *
 * 样式约定：只产出 Tailwind 令牌类名（bg-* / text-*），不新建自定义 CSS/SCSS，
 * 与 .conventions/frontend/COMPONENTS.md 保持一致。
 */

/** 事件色板：底色（含 hover）、文字色、色点色 —— 对应 Breezy 的 event-color 混入方案 */
export interface EventTone {
    /** 事件块底色 + hover 加深（Breezy：event 色低比例混入背景） */
    bg: string;
    /** 事件块文字色（Breezy：event 色半量混入前景） */
    text: string;
    /** 左侧重要级色点 */
    dot: string;
}

/**
 * 重要级 → 事件色板（Breezy 风格：低饱和、轻量色块）。
 *
 * @param importance - 统一业务量纲：0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要
 * @returns 该重要级对应的底色 / 文字色 / 色点色
 */
export function eventThemeMap(importance: number): EventTone {
    switch (importance) {
        //4=非常重要
        case 4:
            return { bg: 'bg-danger/8 hover:bg-danger/15', text: 'text-danger/90', dot: 'bg-danger/90' };
        //3=重要
        case 3:
            return { bg: 'bg-warning/8 hover:bg-warning/15', text: 'text-warning/90', dot: 'bg-warning/90' };
        //2=较重要
        case 2:
            return { bg: 'bg-primary/10 hover:bg-primary/15', text: 'text-primary/90', dot: 'bg-primary/90' };
        //1=普通、0=无
        default:
            return {
                bg: 'bg-foreground/4 hover:bg-foreground/10',
                text: 'text-foreground/70',
                dot: 'bg-foreground/70',
            };
    }
}
