/**
 * LiveCalendarGrid.tsx
 * ------------------------------------------------------------
 * 消息日历的月历网格组件：基于 FullCalendar v6（6.1.21）的二次封装。
 *
 * 视觉目标：对齐 FullCalendar themes.fullcalendar.io 的 Breezy 主题
 * （参考实现见同目录 `demo/event-calendar.tsx`），在 v6 能力范围内做高保真近似：
 * - 细网格线 + 极浅边框，无外框（外框由页面卡片提供）；
 * - 表头星期：小字、半透明灰、居中、圆角胶囊；
 * - 今日日期：主题色实心圆点（白字、加粗），非今日为可 hover 的浅色圆角；
 * - 事件块：圆角淡色块 + 重要级色点，时间为加粗等宽数字在前、标题在后（与 demo 的
 *   rowEvent 顺序一致），非全天事件才显示时间；
 * - 溢出折叠为「+N」浅色胶囊，点开为圆角浮层（popover）。
 *
 * 版本约束（重要）：
 * demo 的 Breezy 主题基于 FullCalendar 7.x 的 Themes API（`viewClass` / `toolbarClass` /
 * `dayHeaderClass` / `dayCellClass` / `blockEventClass` / `rowEventClass` / `popoverClass`
 * 等一整套 `*Class` hook）。本项目锁定 6.1.21，这些 hook 均不存在，因此这里改用 v6 支持
 * 的等价入口实现同一视觉：
 * - `dayHeaderClassNames` / `dayHeaderContent`   ← 7.x 的 dayHeaderClass / dayHeaderInnerClass
 * - `dayCellClassNames`   / `dayCellContent`     ← 7.x 的 dayCellClass / dayCellTopInnerClass
 * - `eventClassNames`     / `eventContent`       ← 7.x 的 rowEventClass / rowEventInnerClass
 * - `moreLinkClassNames`  / `moreLinkContent`    ← 7.x 的 rowMoreLinkClass / InnerClass
 * - `viewClassNames`                             ← 7.x 的 viewClass
 * v6 注入的其余结构样式（.fc-daygrid-day-top 的 row-reverse、.fc-daygrid-day-number 的
 * padding、.fc-h-event 的背景与边框等）通过容器层 Tailwind arbitrary variants 精确覆盖。
 * 因此本实现是「视觉近似」，不可能与 7.x demo 逐像素 1:1。
 *
 * 遵循 .conventions/frontend/COMPONENTS.md：
 * - 通过 `React.ComponentProps<typeof FullCalendar>` 完整继承原生 TS 类型；
 * - 解构业务自定义属性（eventsByDay / onSelectDay / onSelectEvent），其余透传；
 * - 用 `cn()` 合并样式，外部 className 优先级最高（放在合并最后）；
 * - 不新建自定义 CSS/SCSS，样式走 Tailwind 令牌 + FullCalendar 的 `--fc-*` 变量层。
 *
 * 选型理由与主题映射详见 docs/Live-calendar.md §9。
 */

import { useMemo } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import zhCnLocale from '@fullcalendar/core/locales/zh-cn';
import { cn } from '../../../utils/cn';
import type { LiveCalendarEventDef } from '../../../types/liveCalendar';
// 基础样式，后续用Tailwind覆盖美化
// import '@fullcalendar/core/main.css';

// FullCalendar v6 将样式内联进 JS bundle（CSS-in-JS），官方不再提供独立 CSS 文件，
// 无需（也不支持）单独 import CSS，否则 vite import-analysis 会报 Missing specifier。
// 其注入的 <style data-fullcalendar> 位于 head 最前，故 Tailwind 原子类可正常覆盖。

/** 视图当前显示范围的年/月（按视图 startDate 计算）。供 Page 据此拉取对应月份数据。 */
export interface LiveCalendarRange {
    year: number;
    month: number;
}

/** 业务扩展属性：数据契约经转化喂给 FullCalendar，业务字段仅以下四个 */
export type LiveCalendarGridProps = React.ComponentProps<typeof FullCalendar> & {
    /** 按天归格的事件（key = YYYY-MM-DD） */
    eventsByDay: Map<string, LiveCalendarEventDef[]>;
    /** 点日期空白区 → 打开该日全部详情 */
    onSelectDay: (day: string) => void;
    /** 点单条事件 → 打开该事件详情 */
    onSelectEvent: (event: LiveCalendarEventDef) => void;
    /**
     * 视图日期范围变化回调（切换视图 / prev / next / today 触发）。Page 据此请求对应月份数据。
     * 用 startDate 的年月，因后端按月取数；跨月周次取 start 月。
     */
    onRangeChange?: (range: LiveCalendarRange) => void;
    /** 外层容器自定义类名 */
    className?: string;
};

/** 事件色板：底色（含 hover）、文字色、色点色 —— 对应 Breezy 的 event-color 混入方案 */
interface EventTone {
    /** 事件块底色 + hover 加深（Breezy：event 色低比例混入背景） */
    bg: string;
    /** 事件块文字色（Breezy：event 色半量混入前景） */
    text: string;
    /** 左侧重要级色点 */
    dot: string;
}

/** 重要级 → 事件色板（Breezy 风格：低饱和、轻量色块） */
function eventTone(importance: number): EventTone {
    switch (importance) {
        case 4:
            return { bg: 'bg-warning/15 hover:bg-warning/25', text: 'text-warning', dot: 'bg-warning' };
        case 3:
            return { bg: 'bg-primary/15 hover:bg-primary/25', text: 'text-primary', dot: 'bg-primary' };
        case 2:
            return { bg: 'bg-primary/10 hover:bg-primary/20', text: 'text-primary/80', dot: 'bg-primary/60' };
        default:
            return {
                bg: 'bg-muted/40 hover:bg-muted/60',
                text: 'text-secondary-text',
                dot: 'bg-muted-foreground/50',
            };
    }
}

/** 秒级时间戳 → 本地 HH:mm（用于事件块内时间标签） */
function formatHHMM(startAt: number): string {
    const d = new Date(startAt * 1000);
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/** 把按天归格的事件展平为 FullCalendar 的 EventInput 数组 */
function toFullCalendarEvents(eventsByDay: Map<string, LiveCalendarEventDef[]>) {
    const result: Array<{
        title: string;
        start: Date;
        allDay: boolean;
        extendedProps: { eventDef: LiveCalendarEventDef };
    }> = [];

    for (const events of eventsByDay.values()) {
        for (const event of events) {
            result.push({
                title: event.shortTitle,
                start: new Date(event.startAt * 1000),
                allDay: event.isAllDay,
                extendedProps: { eventDef: event },
            });
        }
    }
    return result;
}

/** 单条事件的格子内容：[色点] [时间] [标题]，对齐 Breezy rowEvent 的顺序与节奏 */
function CalendarEventContent({ event }: { event: LiveCalendarEventDef }) {
    const tone = eventTone(event.importance);
    return (
        <div
            className={cn(
                'flex w-full items-center gap-1 rounded-md px-1 py-0.5 text-xs transition-colors',
                tone.bg,
                tone.text,
            )}
        >
            <span
                aria-hidden
                className={cn('h-1.5 w-1.5 shrink-0 rounded-full', tone.dot)}
            />
            {!event.isAllDay ? (
                <span className="shrink-0 font-medium tabular-nums opacity-80">
                    {formatHHMM(event.startAt)}
                </span>
            ) : null}
            <span className="min-w-0 flex-1 truncate font-medium leading-tight">
                {event.shortTitle}
            </span>
        </div>
    );
}

/** FullCalendar v6 二次封装：月历事件展示，dayMaxEvents 折叠 + 主题变量作用域 */
export const LiveCalendarGrid = ({
    eventsByDay,
    onSelectDay,
    onSelectEvent,
    onRangeChange,
    className,
    ...props
}: LiveCalendarGridProps) => {
    const events = useMemo(() => toFullCalendarEvents(eventsByDay), [eventsByDay]);
    return (
        <div
            className={cn(
                // 容器：占满可用宽度，字号继承页面。
                // 高度策略：不使用 h-full / height="100%"。调用方（LiveCalendarPage）给的是
                // `min-h-[480px] flex-1` 的 flex item，其高度是 flex 布局算出的 auto 语义，
                // 子元素任何 `height: 100%` 都解析不出确定值，会把 wrapper 与整个日历压成 0。
                // 因此高度交给 FullCalendar 的 aspectRatio 自撑开（见下方组件配置）。
                'hrs-calendar-Live w-full [&_.fc]:text-sm',
                // ── FullCalendar 主题变量层 ────────────────────────────────────────────
                // 中和 v6 注入样式的默认取色，把控制权交给下面的 Tailwind 层
                // 网格线：用设计令牌 --border（217 28% 84%）加深后再半透明，在白底上清晰可见；
                // 不能用 --border-dim-raw（= foreground / 0.05-0.08），那种深色低透明在浅底上几乎隐形，
                // 会让人误以为整张日历没渲染。
                '[--fc-border-color:hsl(var(--border)_/_0.6)]',
                '[--fc-page-bg-color:transparent]',
                '[--fc-neutral-bg-color:hsl(var(--muted)_/_0.4)]',
                '[--fc-neutral-text-color:hsl(var(--muted-foreground))]',
                // 今日底色交给日期圆点表达，整格不铺色（Breezy 同款）
                '[--fc-today-bg-color:transparent]',
                // 事件底色/边框/文字全部由 eventContent 渲染，锚点保持透明
                '[--fc-event-bg-color:transparent]',
                '[--fc-event-border-color:transparent]',
                '[--fc-event-text-color:hsl(var(--foreground))]',
                '[--fc-event-selected-overlay-color:hsl(var(--primary)_/_0.12)]',
                '[--fc-small-font-size:0.75rem]',
                '[--fc-daygrid-event-dot-width:6px]',
                // 工具栏按钮：覆盖 v6 的 --fc-button-* 变量，让 FullCalendar 默认按钮样式与
                // 项目令牌对齐（圆角描边 + 选中态浅灰）。下面再用 Tailwind 调整形状。
                '[--fc-button-text-color:hsl(var(--foreground))]',
                '[--fc-button-bg-color:hsl(var(--background))]',
                '[--fc-button-border-color:hsl(var(--border-dim-raw)_/_0.12)]',
                '[--fc-button-hover-bg-color:hsl(var(--hover))]',
                '[--fc-button-hover-border-color:hsl(var(--border-dim-raw)_/_0.12)]',
                '[--fc-button-active-bg-color:hsl(var(--muted))]',
                '[--fc-button-active-border-color:hsl(var(--border-dim-raw)_/_0.12)]',

                // ── 网格框架 ──────────────────────────────────────────────────────────
                // 去掉 v6 给 .fc-scrollgrid 加的外框，网格线只保留单元格之间的一条。
                // 注意：v6 的 scrollgrid 算法依赖默认的 `border-collapse: separate` + `border-spacing`，
                // 强制改为 collapse 会让 body 行高计算为 0，整张日历塌成空白，因此不要覆盖此属性。
                '[&_.fc-scrollgrid]:border-0',
                '[&_.fc-theme-standard_td]:border-(--fc-border-color)',
                '[&_.fc-theme-standard_th]:border-(--fc-border-color)',

                // ── 表头（星期行）────────────────────────────────────────────────────
                '[&_.fc-col-header]:bg-transparent',
                '[&_.fc-col-header-cell]:border-x-0',
                '[&_.fc-col-header-cell]:border-t-0',
                '[&_.fc-col-header-cell]:bg-transparent',
                '[&_.fc-col-header-cell]:px-0',
                '[&_.fc-col-header-cell]:py-2',
                '[&_.fc-col-header-cell]:align-middle',
                '[&_.fc-col-header-cell]:font-medium',
                '[&_.fc-col-header-cell_cushion]:block',
                '[&_.fc-col-header-cell_cushion]:p-0',
                '[&_.fc-col-header-cell_cushion]:text-center',
                '[&_.fc-scrollgrid-sync-inner]:p-0',

                // ── 日期格 ────────────────────────────────────────────────────────────
                // frame 保留 v6 默认的 `min-height: 100%`（占满 td），不要设为 0，否则整格塌缩。
                '[&_.fc-daygrid-day]:p-0',
                // v6 默认 .fc-daygrid-day-top 是 row-reverse（日期靠右），改为靠左
                '[&_.fc-daygrid-day-top]:m-0',
                '[&_.fc-daygrid-day-top]:flex-row',
                '[&_.fc-daygrid-day-top]:items-center',
                '[&_.fc-daygrid-day-top]:justify-start',
                '[&_.fc-daygrid-day-top]:p-0',
                '[&_.fc-daygrid-day-top]:ps-1',
                '[&_.fc-daygrid-day-top]:pt-1.5',
                // 日期数字容器：去掉 v6 的 padding，改由 dayCellContent 画圆点
                '[&_.fc-daygrid-day-number]:p-0',
                '[&_.fc-daygrid-day-number]:no-underline',
                // 非本月默认 opacity .3 会把圆点一起压暗，改为自定义文字淡化
                '[&_.fc-day-other_.fc-daygrid-day-top]:opacity-100',
                // 事件区与底部「+N」区
                '[&_.fc-daygrid-day-events]:mb-0',
                '[&_.fc-daygrid-day-events]:mt-0.5',
                '[&_.fc-daygrid-day-events]:px-1',
                '[&_.fc-daygrid-day-bottom]:my-0',
                '[&_.fc-daygrid-day-bottom]:px-1',
                '[&_.fc-daygrid-day-bottom]:pb-1',
                '[&_.fc-daygrid-day-bottom]:pt-0.5',

                // ── 事件锚点 ──────────────────────────────────────────────────────────
                // 透明化锚点，全部视觉交给 CalendarEventContent 渲染
                '[&_.fc-daygrid-event]:m-0',
                '[&_.fc-daygrid-event]:mb-px',
                '[&_.fc-daygrid-event]:ms-0.5',
                '[&_.fc-daygrid-event]:me-0.5',
                '[&_.fc-daygrid-event]:border-0',
                '[&_.fc-daygrid-event]:bg-transparent',
                '[&_.fc-daygrid-event]:p-0',
                '[&_.fc-daygrid-event]:shadow-none',
                '[&_.fc-daygrid-event:hover]:bg-transparent',
                '[&_.fc-daygrid-event]:focus-visible:outline-none',
                '[&_.fc-event-main]:p-0',
                '[&_.fc-event-main]:bg-transparent',
                '[&_.fc-event-main-frame]:p-0',
                '[&_.fc-event-title-container]:hidden',
                '[&_.fc-event-time]:hidden',

                // ── 周次标签（showWeekNumbers 开启时生效）─────────────────────────────
                '[&_.fc-daygrid-week-number]:inline-flex',
                '[&_.fc-daygrid-week-number]:min-w-[34px]',
                '[&_.fc-daygrid-week-number]:items-center',
                '[&_.fc-daygrid-week-number]:justify-center',
                '[&_.fc-daygrid-week-number]:rounded-ee-md',
                '[&_.fc-daygrid-week-number]:border-e',
                '[&_.fc-daygrid-week-number]:border-b',
                '[&_.fc-daygrid-week-number]:border-(--fc-border-color)',
                '[&_.fc-daygrid-week-number]:bg-muted/40',
                '[&_.fc-daygrid-week-number]:px-1.5',
                '[&_.fc-daygrid-week-number]:py-0.5',
                '[&_.fc-daygrid-week-number]:text-[11px]',
                '[&_.fc-daygrid-week-number]:font-medium',
                '[&_.fc-daygrid-week-number]:text-muted-foreground',
                '[&_.fc-daygrid-week-number]:no-underline',

                // ── 折叠浮层（点「+N」弹出）───────────────────────────────────────────
                '[&_.fc-popover]:overflow-hidden',
                '[&_.fc-popover]:rounded-lg',
                '[&_.fc-popover]:border',
                '[&_.fc-popover]:border-border-dim',
                '[&_.fc-popover]:bg-elevated',
                '[&_.fc-popover]:shadow-soft-card',
                '[&_.fc-popover-header]:flex',
                '[&_.fc-popover-header]:items-center',
                '[&_.fc-popover-header]:justify-between',
                '[&_.fc-popover-header]:bg-transparent',
                '[&_.fc-popover-header]:px-3',
                '[&_.fc-popover-header]:py-2',
                '[&_.fc-popover-title]:text-xs',
                '[&_.fc-popover-title]:font-semibold',
                '[&_.fc-popover-title]:text-foreground',
                '[&_.fc-popover-close]:inline-flex',
                '[&_.fc-popover-close]:size-6',
                '[&_.fc-popover-close]:items-center',
                '[&_.fc-popover-close]:justify-center',
                '[&_.fc-popover-close]:rounded-md',
                '[&_.fc-popover-close]:text-muted-foreground',
                '[&_.fc-popover-close:hover]:bg-hover',
                '[&_.fc-more-popover_.fc-popover-body]:p-2',

                // ── 工具栏（prev/today/next + title + 视图切换器）───────────────────────
                // v6 工具栏默认用 display:flex; justify-content:space-between; align-items:center;
                // 这里给 padding 与下边距分隔日历主体，并在月/周/日切换按钮组上做"相邻拼接"视觉。
                '[&_.fc-toolbar]:flex',
                '[&_.fc-toolbar]:flex-wrap',
                '[&_.fc-toolbar]:items-center',
                '[&_.fc-toolbar]:justify-between',
                '[&_.fc-toolbar]:gap-3',
                '[&_.fc-toolbar]:px-4',
                '[&_.fc-toolbar]:py-3',
                '[&_.fc-header-toolbar]:mb-0',
                '[&_.fc-toolbar-title]:text-base',
                '[&_.fc-toolbar-title]:font-semibold',
                '[&_.fc-toolbar-title]:text-foreground',
                // 通用按钮（prev/next/today）：白底描边圆角
                '[&_.fc-button]:rounded-md',
                '[&_.fc-button]:bg-background',
                '[&_.fc-button]:border',
                '[&_.fc-button]:border-border-dim',
                '[&_.fc-button]:text-foreground',
                '[&_.fc-button]:shadow-soft-card',
                '[&_.fc-button:hover]:bg-hover',
                '[&_.fc-button-primary.fc-button-active]:bg-muted',
                '[&_.fc-button-primary.fc-button-active]:text-foreground',
                '[&_.fc-button-primary.fc-button-active]:shadow-none',
                '[&_.fc-button-primary.fc-button-active]:border-border-dim',
                // 按钮组（视图切换器）：相邻按钮去掉双边框，整体呈一个胶囊
                '[&_.fc-button-group_.fc-button]:rounded-none',
                '[&_.fc-button-group_.fc-button:first-child]:rounded-l-md',
                '[&_.fc-button-group_.fc-button:last-child]:rounded-r-md',
                '[&_.fc-button-group_.fc-button:not(:first-child)]:-ml-px',
                '[&_.fc-button-group_.fc-button:first-child]:ml-0',
                className,
            )}
        >
            <FullCalendar
                plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                initialView="dayGridMonth"
                locale={zhCnLocale}
                firstDay={1}
                dayMaxEvents={3}
                // 高度策略：不再传 height="100%"（父容器是 flex item，height:100% 无法解析为确定值，
                // 会把 view-harness 算成 0，整张日历塌成空白）。v6 各视图有各自的合理默认尺寸：
                // - dayGridMonth: aspectRatio 1.35（行数已知，宽度决定高度）
                // - timeGridWeek/Day: contentHeight auto，按需撑开
                // 加 expandRows 让月视图事件少时行高仍均分；timeGrid 视图不依赖此参数。
                aspectRatio={1.35}
                expandRows={true}
                // ── 工具栏：内置 prev/today/next + title + 月/周/日切换器 ────────────
                // 之前由 LiveCalendarPage 自带的"今日 + 月翻页"按钮被此处接管，避免重复；
                // 分类 Tab 与刷新按钮仍在 Page 层（功能与视图导航正交，不重复）。
                headerToolbar={{
                    start: 'prev,next today',
                    center: 'title',
                    end: 'dayGridMonth,timeGridWeek,timeGridDay',
                }}
                buttonText={{
                    today: '今天',
                    dayGridMonth: '月',
                    timeGridWeek: '周',
                    timeGridDay: '日',
                }}
                // 视图日期范围变化（prev/next/today/切换视图）→ 通知 Page 拉对应月份数据
                datesSet={(arg) => {
                    if (!onRangeChange) return;
                    const d = arg.start;
                    onRangeChange({ year: d.getFullYear(), month: d.getMonth() + 1 });
                }}
                events={events}
                // 短事件按 Breezy 的紧凑高度渲染（v6 支持该选项）
                eventShortHeight={24}
                // ── 表头：星期胶囊（对齐 Breezy dayHeaderInnerClass / dayHeaderContent）
                dayHeaderClassNames="border-0 bg-transparent"
                dayHeaderContent={(arg) => (
                    <span className="inline-flex items-center justify-center rounded-sm px-1.5 py-1 text-xs font-semibold tracking-wide text-muted-foreground">
                        {arg.text}
                    </span>
                )}
                // ── 日期格：非本月淡化、非今日弱化（对齐 Breezy dayCellClass）
                dayCellClassNames={(arg) =>
                    cn(arg.isToday && 'bg-transparent', arg.isOther && 'bg-muted/20')
                }
                // ── 日期数字：今日=主题色实心圆点（对齐 Breezy dayCellTopInnerClass）
                dayCellContent={(arg) => (
                    <span
                        className={cn(
                            'inline-flex h-7 min-w-7 items-center justify-center rounded-full px-1.5 text-sm font-medium transition-colors',
                            arg.isToday
                                ? 'bg-primary text-primary-foreground'
                                : arg.isOther
                                    ? 'text-muted-foreground/45'
                                    : 'text-foreground hover:bg-hover',
                        )}
                    >
                        {arg.dayNumberText}
                    </span>
                )}
                // ── 事件：圆角淡色块（对齐 Breezy rowEventClass）
                eventClassNames={() => [
                    'group block w-full cursor-pointer rounded-md',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
                ]}
                eventContent={(arg) => (
                    <CalendarEventContent
                        event={arg.event.extendedProps.eventDef as LiveCalendarEventDef}
                    />
                )}
                // ── 折叠「+N」：浅色胶囊（对齐 Breezy rowMoreLinkClass）
                moreLinkClassNames="block w-full cursor-pointer rounded-md border-0 bg-transparent p-0 text-left hover:bg-transparent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                moreLinkContent={(arg) => (
                    <span className="flex items-center gap-1 rounded-md bg-muted/50 px-1.5 py-0.5 text-xs font-medium text-secondary-text transition-colors hover:bg-muted">
                        +{arg.num}
                    </span>
                )}
                dateClick={(info) => onSelectDay(info.dateStr)}
                eventClick={(info) => onSelectEvent(info.event.extendedProps.eventDef as LiveCalendarEventDef)}
                {...props}
            />
        </div>
    );
};
