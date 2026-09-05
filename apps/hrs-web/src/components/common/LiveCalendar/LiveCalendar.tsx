/**
 * LiveCalendar.tsx
 * ------------------------------------------------------------
 * 消息日历的月历网格组件：基于 FullCalendar v6（6.1.21）的二次封装。
 *
 * 视觉目标：对齐 FullCalendar themes.fullcalendar.io 的 Breezy 主题
 * （参考实现见同目录 `demo/event-calendar.tsx`），在 v6 能力范围内做高保真近似：
 * - 细网格线 + 极浅边框，无外框（外框由页面卡片提供）；
 * - 表头星期：小字、半透明灰、居中、圆角胶囊；
 * - 今日日期：主题色实心 pill（白字、加粗），非今日为可 hover 的浅色圆角；
 * - 事件块：圆角淡色块 + 重要级色点 + 时间在上一行、标题在下一行，非全天事件才显示时间；
 * - 溢出折叠为「+N」浅色胶囊，点开为圆角浮层（popover）。
 *
 * 周视图专属：同时段（默认 60 分钟窗口）内达到阈值（默认 3 条）的消息归集成一张卡片，
 * 卡片内按时间分组、组内按重要度降序，组头显示色点 + 时间（纯展示、不可交互），
 * 组内每条消息独立可 hover / 可点击。详见 `GroupedEventContent` 与相关常量。
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
 * 样式分层：容器层的几百条 `[&_.fc-*]` 覆盖类名与 `--fc-*` 变量已抽到同目录
 * `csscover.ts`（常量 `LIVE_CALENDAR_CSS_COVER`），本文件只保留一次引用；
 * 改样式请去那里，维护约定（顺序即优先级、类名必须完整字面量、`!` 不可省）写在该文件头部。
 *
 * 选型理由与主题映射详见 docs/Live-calendar.md §9。
 */

import { useCallback, useMemo, useRef, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import type { EventClickArg, EventMountArg } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { DateClickArg } from '@fullcalendar/interaction';
import zhCnLocale from '@fullcalendar/core/locales/zh-cn';
import zhTwLocale from '@fullcalendar/core/locales/zh-tw';
import { cn } from '../../../utils/cn';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiLanguage } from '../../../i18n/uiText';
import type { LiveCalendarEventDef } from '../../../types/liveCalendar';
import { LIVE_CALENDAR_CSS_COVER } from './csscover';
import { formatTime } from '../../../utils/format';
// FullCalendar v6 将样式内联进 JS bundle（CSS-in-JS），官方不再提供独立 CSS 文件，
// 无需（也不支持）单独 import CSS，否则 vite import-analysis 会报 Missing specifier。
// 其注入的 <style data-fullcalendar> 位于 head 最前，故 Tailwind 原子类可正常覆盖。

/**
 * 视图当前可见的日期范围（datesSet 的 start/end 闭区间）。供 Page 据此拉取覆盖月份的数据。
 * 各视图语义：月视图含上/下月填充格（如 9 月视图从 8/31 周一起）、周视图 = 周一~周日、日视图 = 当天。
 */
export interface LiveCalendarRange {
    /** 可见范围起始日（本地时区） */
    start: Date;
    /** 可见范围结束日（本地时区） */
    end: Date;
}

/** 业务扩展属性：数据契约经转化喂给 FullCalendar，业务字段仅以下四个 */
export type LiveCalendarProps = React.ComponentProps<typeof FullCalendar> & {
    /** 按天归格的事件（key = YYYY-MM-DD） */
    eventsByDay: Map<string, LiveCalendarEventDef[]>;
    /** 点日期空白区 → 打开该日全部详情 */
    onSelectDay: (day: string) => void;
    /** 点单条事件 → 打开该事件详情 */
    onSelectEvent: (event: LiveCalendarEventDef) => void;
    /**
     * 视图日期范围变化回调（切换视图 / prev / next / today 触发）。Page 据此拉取可见范围
     * 覆盖的所有月份数据并合并（后端按月取数）。不能用单一月份（如 view.currentStart 的年月）
     * 推导：周视图可见范围可能跨月（如 9 月第一周的周一落在 8/31），只拉周一所在月份会让
     * 跨月日（9/2、9/3 等）在网格中无事件。
     */
    onRangeChange?: (range: LiveCalendarRange) => void;
    /** 外层容器自定义类名 */
    className?: string;
};

/** 归集卡片的分组方式（暂不对外暴露，内部预留扩展） */
type GroupMethod = 'timeAndImportance' | 'time';

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
function eventThemeMap(importance: number): EventTone {
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

// ── 周视图：同时段多条消息归集为一张卡片 ──────────────────────────────────
// 把「同一时间窗口内」且数量达到阈值的多条消息合并成一个 FullCalendar 事件，
// 卡片内按「(时间, 重要度)」双层结构展示，避免并排挤成窄条或堆叠互相截断。
/**
 * 判定「同一时间段」的容差（分钟），同时控制两处：
 *  1. 周视图归集卡片：相邻事件 startAt 差 ≤ 该值 → 归为同一张卡片；
 *  2. 周/日视图纵向堆叠：相邻事件时间差 ≤ 该值 → 纵向错开（rearrangeSameTimeEvents）。
 * 使用滑动窗口聚类（桶边界由数据驱动、非固定整点），避免把跨整点的连续事件拆开。
 * 默认 60 分钟（1 小时）；修改后两处都会跟着变。
 */
const SAME_TIME_WINDOW_MIN = 60;
/** 桶内消息数达到该阈值才归集成卡片；未达阈值的仍逐条渲染。 */
const GROUP_THRESHOLD = 3;
/** 归集卡片内「组头」（重要级色点 + 时间）的高度（px）。 */
const GROUP_FIRST_ROW_HEIGHT = 24;
/** 归集卡片内每条消息的行高（px）。 */
const GROUP_ROW_HEIGHT = 20;
/** 归集卡片上下内距（px）。 */
const GROUP_PADDING = 10;

/**
 * 归集分组（**双层数据结构**）。
 *
 * 归集卡片的本质是「合并相同时间、相同重要度的新闻消息」，所以数据不再是扁平的
 * 事件数组，而是先按 (startAt, importance) 分出一层「组」，组内再放该时间点的消息列表。
 * - 外层：组（一个时间点 + 一个重要级），携带 dot 色点 + 时间，作为不可交互的分组标题；
 * - 内层：该组下的消息列表，每条可 hover、可点击。
 */
export interface GroupedEventGroup {
    /** 该组的时间戳（秒）；组内所有消息时间相同 */
    startAt: number;
    /**
     * 该组的重要级（决定组头色点色）：
     * - timeAndImportance 模式：组内所有消息 importance 相同，取任一即可；
     * - time 模式：组内可能有不同 importance，取最大值作为代表。
     */
    importance: number;
    /** 组内消息列表 */
    items: LiveCalendarEventDef[];
}

/**
 * 把桶内事件整理成双层结构，支持两种分组方式：
 *
 * - `timeAndImportance`（默认）：按 (startAt, importance) 分组，相邻且时间 + 重要度均相同
 *   的事件合并进同一组；只要时间或重要度之一变化就新开一组。
 * - `time`：只按 startAt 分组，同一时间的消息不论重要度都合并到一组，
 *   组内按重要度降序排列（高重要度在前）。
 *
 * ⚠ 要求输入 `events` 已按 startAt 升序（toFullCalendarEvents 中已保证），
 * 否则「相邻」判定不成立、同一时间点的消息可能被拆成多组。
 */
function eventGroupByTimeAndImportance(
    events: LiveCalendarEventDef[],
    method: GroupMethod = 'time',
): GroupedEventGroup[] {
    const groups: GroupedEventGroup[] = [];

    if (method === 'time') {
        // ── 按时间归集：同一 startAt 的消息合并到一组，组内按重要度降序 ──
        events.forEach((item) => {
            const tail = groups[groups.length - 1];
            if (tail && tail.startAt === item.startAt) {
                tail.items.push(item);
                // 组头重要度取组内最大值（高重要度 = 大数字）
                tail.importance = Math.max(tail.importance, item.importance);
            } else {
                groups.push({
                    startAt: item.startAt,
                    importance: item.importance,
                    items: [item],
                });
            }
        });
        // 组内按重要度降序（高重要度排在前面）
        groups.forEach((g) => g.items.sort((a, b) => b.importance - a.importance));
    } else {
        // ── 按时间 + 重要度归集（默认）：相邻且时间相同 && 重要度相同才合并 ──
        events.forEach((item) => {
            const tail = groups[groups.length - 1];
            if (tail && tail.startAt === item.startAt && tail.importance === item.importance) {
                tail.items.push(item);
            } else {
                groups.push({
                    startAt: item.startAt,
                    importance: item.importance,
                    items: [item],
                });
            }
        });
    }

    return groups;
}

/** 计算归集卡片的期望总高（px）：各组(组头 + 组内消息) + 卡片上下内距。 */
function calcGroupCardHeight(groups: GroupedEventGroup[]): number {
    const rows = groups.reduce(
        (sum, g) => sum + GROUP_FIRST_ROW_HEIGHT + g.items.length * GROUP_ROW_HEIGHT,
        0,
    );
    return rows + GROUP_PADDING * 2;
}

/**
 * 把按天归格的事件展平为 FullCalendar 的 EventInput 数组。
 *
 * 关键：这里会做**同时段归集**，但**仅在「周」视图生效**。
 * 月视图、日视图都按单条事件逐条输出（月视图有自己的 +N 折叠浮层；
 * 日视图时间轴高度足够、不需要归集）。
 *
 * 仅周视图时的归集流程：
 * 1. 按 startAt 升序排序；
 * 2. 按「滑动时间窗口」聚类：相邻事件 startAt 差 ≤ SAME_TIME_WINDOW_MIN 分钟 → 归一组
 *    （桶边界由数据驱动，而非固定整点；跨整点的连续事件不会被强行拆开）；
 * 3. 组内条数 >= GROUP_THRESHOLD → 合并成**一个** FC 事件，extendedProps.groupEvents 携带原数组，
 *    eventContent 会把它们渲染成一张归集卡片；
 * 4. 组内条数未达阈值 → 逐条输出，同时间段的由 `rearrangeSameTimeEvents` 做纵向堆叠。
 *
 * 合并事件的 eventDef 取桶内第一条作为「代表」，用于点击卡片整体时的详情定位。
 */
function toFullCalendarEvents(
    eventsByDay: Map<string, LiveCalendarEventDef[]>,
    viewType: string,
) {
    const result: Array<{
        // 稳定 id：单条为 `evt-${dayKey}-${i}-${startAt}`，归集卡片为 `group-${dayKey}-${bucketStart}`。
        // 便于 eventDidMount 通过 event.id 关联 DOM（纵向重排、归集卡片高度设置都依赖它）。
        id: string;
        title: string;
        start: Date;
        allDay: boolean;
        extendedProps: {
            eventDef: LiveCalendarEventDef;
            /** 仅归集卡片有值：桶内按时间排序后的原事件数组 */
            groupEvents?: LiveCalendarEventDef[];
        };
    }> = [];

    for (const [dayKey, events] of eventsByDay) {
        // 1) 按时间升序
        const sorted = events.slice().sort((a, b) => a.startAt - b.startAt);

        // 归集仅在周视图启用；月视图/日视图都逐条输出。
        const enableGrouping = viewType === 'timeGridWeek';

        // 2) 按「滑动时间窗口」聚类：相邻事件 startAt 差 ≤ SAME_TIME_WINDOW_MIN 分钟则归一组
        //    （与纵向堆叠的算法一致：桶边界由数据驱动，跨整点连续事件不会被固定小时切分拆开）
        const windowSec = SAME_TIME_WINDOW_MIN * 60;
        const groups: Array<{ startAt: number; items: LiveCalendarEventDef[] }> = [];
        sorted.forEach((event) => {
            const tail = groups[groups.length - 1];
            if (tail && (event.startAt - tail.startAt) <= windowSec) {
                tail.items.push(event);
            } else {
                groups.push({ startAt: event.startAt, items: [event] });
            }
        });

        // 3) 每组输出（保证 FC 事件顺序与视觉顺序一致）
        groups.forEach((group) => {
            const bucketStart = group.startAt;
            const bucket = group.items;

            if (enableGrouping && bucket.length >= GROUP_THRESHOLD) {
                // 3a) 达标（且处于周视图） → 合并成一张归集卡片
                result.push({
                    id: `group-${dayKey}-${bucketStart}`,
                    title: bucket[0].shortTitle,
                    start: new Date(bucketStart * 1000),
                    // 归集卡片整体视为一个时间块；全天标记取组内首条，避免全天事件被误判。
                    allDay: bucket[0].isAllDay,
                    extendedProps: { eventDef: bucket[0], groupEvents: bucket },
                });
            } else {
                // 3b) 未达标 → 逐条输出
                bucket.forEach((event, i) => {
                    result.push({
                        id: `evt-${dayKey}-${i}-${event.startAt}`,
                        title: event.shortTitle,
                        start: new Date(event.startAt * 1000),
                        allDay: event.isAllDay,
                        extendedProps: { eventDef: event },
                    });
                });
            }
        });
    }
    return result;
}

/** 单条事件的格子内容：[色点] [时间] [标题]，对齐 Breezy rowEvent 的顺序与节奏 */
function CalendarEventContent({ event }: { event: LiveCalendarEventDef }) {
    const theme = eventThemeMap(event.importance);
    return (
        <div
            className={cn(
                // 事件条目：垂直 flex。第一行放 [圆点 + 时间]，第二行放标题，
                // 对齐 Breezy 月历事件块「小标识在上、标题在下」的节奏。
                // w-full 占满日期格宽度，事件内容不会溢出格子；py-1 给上下呼吸感，my-1 与相邻事件留间距。
                'flex w-full flex-col gap-0.5 rounded-sm pl-2 pr-1 pt-1.5 pb-2 mt-1 mb-1.5 text-xs transition-colors',
                theme.bg,
                theme.text,
            )}
        >
            {/* 第一行：圆点 + 时间（水平居中排列） */}
            <div className="flex items-center gap-1">
                <span aria-hidden className={cn('shrink-0 text-lg font-bold leading-none', theme.text)}>·</span>
                {!event.isAllDay ? (
                    <div className="shrink-0 font-medium tabular-nums opacity-80">
                        {formatTime(event.startAt)}
                    </div>
                ) : null}
            </div>

            {/* 第二行：标题，允许自动换行。
                 - FullCalendar 的 .fc-daygrid-event 默认带 white-space:nowrap，会直接继承给
                   自定义 eventContent，所以这里必须用 whitespace-normal 显式覆盖。
                 - break-words 对英文长词/URL 做断词，中文 CJK 会在字符间自然换行。
                 不再使用 truncate，标题长时会撑高事件行，FullCalendar 的 dayMaxEvents
                 会自动把装不下的事件折叠成「+N」。 */}
            <span className="whitespace-normal break-words font-medium leading-tight">
                {event.shortTitle}
            </span>
        </div>
    );
}

/**
 * 归集卡片内容：**双层结构**渲染。
 *
 * - 外层 `groups`：已按(时间,或时间+重要度) 分好组的数组，每组渲染一个「组头」（色点 + 时间）；
 * - 内层 `group.items`：该组下的消息列表，每条渲染为独立可交互的一行。
 *
 * 交互约定（重要）：
 * - **组头（色点 + 时间）是纯展示元素**（`div` / `span`），
 *   鼠标移入没有 hover 背景、点击也不触发任何事件——因为它只表示「这一组的时间与重要级」；
 * - **每条消息是 `<button>`**，鼠标移入有 `hover:bg-hover` 背景反馈，
 *   点击触发 `onSelectEvent(item)`，并通过 `stopPropagation` 阻止冒泡到
 *   FullCalendar 的 eventClick（否则会用「代表事件」打开错误的详情）。
 */
function GroupedEventContent({
    groups,
    onSelectEvent,
}: {
    /** 已按 (时间,或时间+重要度) 分好组的双层数据 */
    groups: GroupedEventGroup[];
    onSelectEvent: (event: LiveCalendarEventDef) => void;
}) {
    return (
        <div className="flex w-full flex-col rounded-sm bg-foreground-faint mt-1 px-0.5 py-1 transition-colors">
            {groups.map((group, gi) => {
                const theme = eventThemeMap(group.importance);
                // 组头是否显示时间：组内首条为「非全天事件」才显示（全天事件没有具体时刻）
                const showTime = group.items.length > 0 && !group.items[0].isAllDay;

                return (
                    // 组之间用 mt-1 分隔，形成「按时间 + 重要度归类」的分段视觉
                    <div
                        key={`${group.startAt}-${group.importance}-${gi}`}
                        className={cn(gi > 0 && 'mt-1')}
                    >
                        {/* 组头：重要级色点 + 时间。纯展示，无 hover、无点击。 */}
                        {showTime ? (
                            <div
                                className="flex items-center gap-1 px-1"
                                style={{ minHeight: `${GROUP_FIRST_ROW_HEIGHT}px` }}
                            >
                                <span aria-hidden className={cn('shrink-0 text-lg font-bold leading-none', theme.text)}>·</span>

                                <span className="text-xs font-medium tabular-nums opacity-80">
                                    {formatTime(group.startAt)}
                                </span>
                            </div>
                        ) : null}

                        {/* 组内消息列表：每条独立可 hover / 可点击，
                             色点与文字色取 item 自身的 importance（兼容 time 模式混重要度） */}
                        <div className="flex flex-col">
                            {group.items.map((item, ii) => {
                                const theme = eventThemeMap(item.importance);
                                return (
                                    <button
                                        key={`${item.startAt}-${item.shortTitle}-${ii}`}
                                        type="button"
                                        onClick={(e) => {
                                            // 阻止冒泡：避免触发 FullCalendar 的 eventClick（那会用「代表事件」打开详情）
                                            e.stopPropagation();
                                            onSelectEvent(item);
                                        }}
                                        style={{ minHeight: `${GROUP_ROW_HEIGHT}px` }}
                                        className="flex w-full cursor-pointer items-center gap-1 rounded-sm px-1 text-left transition-colors hover:bg-hover"
                                    >
                                        <span
                                            className={cn(
                                                'min-w-0 flex-1 truncate text-xs font-medium leading-tight',
                                                theme.text,
                                            )}
                                        >
                                            {item.shortTitle}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

/** UI 语言 → FullCalendar 内置 locale（英文用内置默认 locale，传 undefined 即可） */
function calendarLocaleOf(language: UiLanguage) {
    if (language === 'zh') return zhCnLocale;
    if (language === 'zh-Hant') return zhTwLocale;
    return undefined;
}

/**
 * FullCalendar v6 二次封装：月历事件展示，dayMaxEvents 折叠 + 主题变量作用域。
 *
 * 月视图下点单条事件或日期格 → 切换到日视图（timeGridDay）并定位该日，展示当日全部事件
 * （事件数据仍来自 Page 按月拉取的 eventsByDay，切视图不触发重新请求）；日/周视图下
 * 点击仍走 onSelectDay / onSelectEvent 的详情面板定位语义。
 */
export const LiveCalendar = ({
    eventsByDay,
    onSelectDay,
    onSelectEvent,
    onRangeChange,
    className,
    ...props
}: LiveCalendarProps) => {
    // 当前视图类型（dayGridMonth / timeGridWeek / timeGridDay），由 datesSet 同步。
    // 「同时段归集」仅在 timeGridWeek 生效，月视图/日视图都逐条输出。
    const [viewType, setViewType] = useState<string>('dayGridMonth');
    const events = useMemo(
        () => toFullCalendarEvents(eventsByDay, viewType),
        [eventsByDay, viewType],
    );
    const calendarRef = useRef<FullCalendar | null>(null);
    // 工具栏按钮文案与 FullCalendar locale（星期表头、aria 提示等）随 UI 语言切换
    const { t, language } = useUiLanguage();
    // 日历初始定位日 = 今天。仅挂载时生效（FullCalendar 的 initialDate 为 initial-only），
    // 用 useMemo 空依赖固化一次，避免跨午夜后重渲染时值变化。调用方无需显式传入。
    const initialDate = useMemo(() => new Date(), []);

    /**
     * FullCalendar timeGrid（周/日视图）原生不支持「同时间段事件垂直堆叠」：
     * - slotEventOverlap=false 时同 slot 事件左右并排挤成一列；
     * - slotEventOverlap=true 时 z-index 堆叠互相截断。
     * 这里在事件挂载后手动把同一列、同一时间段（差 < SAME_TIME_WINDOW_MIN 分钟）的
     * harness 改为**纵向错开**：保持 FC 给的 left/right 不动（仍占 1/N 列宽），
     * 只覆盖 top/height，让组内事件按时间顺序在垂直方向依次下移，
     * 每条高度取 SAME_TIME_EVENT_HEIGHT。
     * 视图切换/数据刷新（datesSet）后会再次重排，避免被 FC 重置。
     */
    const eventRefs = useRef(new Map<string, HTMLElement>());
    /**
     * FC 原始计算出的 top（px）。**必须**单独缓存：rearrange 会把 el.style.top 改掉，
     * 如果每次重排都读「当前 top」当基准，多次重排（datesSet + 多个 eventDidMount 的 rAF）
     * 会不断叠加 i*(height+gap)，事件会越排越往下跑飞。基准只在 eventDidMount 时记录
     * （那时 style.top 还是 FC 刚写入的原始值、尚未被本组件改动）。
     */
    const eventBaseTops = useRef(new Map<string, number>());
    /** 纵向堆叠时每条事件的高度（px）。调大可让堆叠的事件块更高。 */
    const SAME_TIME_EVENT_HEIGHT = 10;
    /** 纵向堆叠时事件之间的垂直间隔（px）。 */
    const SAME_TIME_EVENT_GAP = 10;
    // 时间窗口常量由模块顶部 SAME_TIME_WINDOW_MIN 统一控制（归集卡片 + 纵向堆叠都读它）。

    const rearrangeSameTimeEvents = useCallback(() => {
        const api = calendarRef.current?.getApi();
        if (!api) return;
        // 仅在 timeGrid（周/日）视图生效；月视图有自己的事件布局策略，不要干预。
        if (api.view.type !== 'timeGridWeek' && api.view.type !== 'timeGridDay') return;

        // 1) 收集当前可见事件：id / startMs / harness DOM
        const all = api.getEvents();
        type Entry = { id: string; startMs: number; el: HTMLElement };
        const entries: Entry[] = [];
        all.forEach((e) => {
            if (!e.start) return;
            // 归集卡片已有独立的高度策略（按双层结构行数撑开），不参与这里的纵向重排，
            // 否则高度会被 SAME_TIME_EVENT_HEIGHT 覆盖、把桶内多条消息压回一截。
            if (e.extendedProps.groupEvents) return;
            const el = eventRefs.current.get(e.id);
            if (!el) return;
            entries.push({ id: e.id, startMs: e.start.getTime(), el });
        });
        if (entries.length === 0) return;

        // 2) 按列（日期）分组
        const byDay = new Map<string, Entry[]>();
        entries.forEach((entry) => {
            const d = new Date(entry.startMs);
            const dayKey = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
            if (!byDay.has(dayKey)) byDay.set(dayKey, []);
            byDay.get(dayKey)!.push(entry);
        });

        // 3) 每列内：按时间排序，按「同时间段窗口」分组成堆叠单元
        const windowMs = SAME_TIME_WINDOW_MIN * 60 * 1000;
        byDay.forEach((dayEntries) => {
            dayEntries.sort((a, b) => a.startMs - b.startMs);
            const groups: Entry[][] = [];
            dayEntries.forEach((entry) => {
                const tail = groups[groups.length - 1];
                if (tail && Math.abs(entry.startMs - tail[0].startMs) < windowMs) {
                    tail.push(entry);
                } else {
                    groups.push([entry]);
                }
            });

            // 4) 仅对「同时间段」组（>=2 条）做纵向堆叠；单条事件保持 FC 原定位
            groups.forEach((group) => {
                if (group.length < 2) return;
                // 基准 top 逐个校验：首帧挂载时 FC 的 slat 坐标（时间格行高）可能还没
                // 测量完成，eventBaseTops 里没有有效值。此时**跳过整组**，用 0 兑底会把
                // 事件全部堆到时间轴顶部（0 点位置）；等缓存就绪后的下一次 rearrange 再统一错开。
                const baseTops: number[] = [];
                for (const entry of group) {
                    const cached = eventBaseTops.current.get(entry.id);
                    if (typeof cached === 'number' && Number.isFinite(cached)) {
                        baseTops.push(cached);
                    } else {
                        return;
                    }
                }
                group.forEach((entry, i) => {
                    // 基准 top 取「FC 原始值」的缓存，不能读当前 style.top
                    //（它已被上一次重排改过，直接读会累积偏移、事件越排越下）。
                    const baseTop = baseTops[i] ?? 0;
                    entry.el.style.top = `${baseTop + i * (SAME_TIME_EVENT_HEIGHT + SAME_TIME_EVENT_GAP)}px`;
                    entry.el.style.height = `${SAME_TIME_EVENT_HEIGHT}px`;
                });
            });
        });
    }, []);

    /** 切换到日视图并定位到指定日期（供月视图点击穿透使用；changeView 接受 DateInput） */
    const goToDayView = (date: Date | string) => {
        calendarRef.current?.getApi().changeView('timeGridDay', date);
    };

    /**
     * 点日期格：月视图 → 先通知 Page 定位详情，再切换日视图展示当日全部事件；
     * 周/日视图 → 仅更新选中日（timeGrid 的 dateStr 带时刻，截前 10 位归一为 YYYY-MM-DD）。
     */
    const handleDateClick = (info: DateClickArg) => {
        const dayKey = info.dateStr.slice(0, 10);
        onSelectDay(dayKey);
        if (info.view.type === 'dayGridMonth') {
            goToDayView(info.date);
        }
    };

    /**
     * 点事件块：统一语义 —— 先打开该事件详情，再切到「事件所属日期」的日视图。
     *
     * 覆盖两类触发源：
     * 1. 单条事件（走 CalendarEventContent 渲染）；
     * 2. 归集卡片整体（周视图，点卡片空白处；卡片内的具体消息不在这里，见下方 eventContent
     *    里包的那层 handleSelectInGroup，它 stopPropagation 阻断了冒泡）。
     *
     * 月视图 / 周视图都切日视图（用户要求两者语义一致）；日视图本身已在目标日，不再切换。
     */
    const handleEventClick = (info: EventClickArg) => {
        const eventDef = info.event.extendedProps.eventDef as LiveCalendarEventDef;
        onSelectEvent(eventDef);
        if (info.view.type === 'dayGridMonth' || info.view.type === 'timeGridWeek') {
            goToDayView(info.event.start ?? info.event.startStr);
        }
    };
    return (
        <div
            // 容器样式：这里只引用抽出去的覆盖层常量，顺序约定为「覆盖层在前、className 在后」，
            // 保证调用方传入的类名优先级最高（twMerge 后写的赢）。
            className={cn(LIVE_CALENDAR_CSS_COVER, className)}
        >
            <FullCalendar
                ref={calendarRef}
                plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                initialView="dayGridMonth"
                locale={calendarLocaleOf(language)}
                firstDay={1}
                dayMaxEvents={3}
                // 关闭「当前时间」指示器（timeGrid 默认渲染的横向蓝线 + 蓝色圆点）：
                // 用户觉得该视觉无意义且容易与今日 pill / 事件块混淆；
                // 「今日」语义改由 dayHeaderContent（周/日表头）的主题色 pill 承担。
                nowIndicator={false}
                // 高度策略：不传固定 height，让日历按内容自由展开（无内部纵向滚动条）。
                // - 不用 aspectRatio（会按宽度固定月视图比例，反而可能挤压内容）；
                // - contentHeight="auto"：月/周/日视图都按自身内容撑开高度；
                // - expandRows：事件稀疏时仍均分行高/时间槽，避免空白分布不均。
                contentHeight="auto"
                expandRows={true}
                // ── 工具栏：内置 prev/today/next + title + 月/周/日切换器 ────────────
                // 之前由 LiveCalendarPage 自带的"今日 + 月翻页"按钮被此处接管，避免重复；
                // 分类 Tab 与刷新按钮仍在 Page 层（功能与视图导航正交，不重复）。
                // start 用逗号分隔 = 同一个 .fc-button-group（连体胶囊），顺序即视觉顺序：
                // 「前(prev) / 今天(today) / 后(next)」，与 Breezy demo 的 `prev,today,next` 一致。
                // end 用空格分隔 = 月/周/日为三个独立按钮（不包进 button-group），
                // 配合上方 :is(...) 选择器渲染成纯文字切换器。
                headerToolbar={{
                    start: 'prev,today,next',
                    center: 'title',
                    end: 'dayGridMonth timeGridWeek timeGridDay',
                }}
                buttonText={{
                    today: t('common.datetime.today'),
                    dayGridMonth: t('common.datetime.month'),
                    timeGridWeek: t('common.datetime.week'),
                    timeGridDay: t('common.datetime.day'),
                }}
                // 视图日期范围变化（prev/next/today/切换视图）→ 通知 Page 拉取覆盖月份的数据。
                // 直接下发可见范围 start/end（月视图含上/下月填充格；周视图 = 周一~周日），
                // 由 Page 推导覆盖的所有月份后合并请求。不能只取单一月份：周视图可见范围
                // 可能跨月（如 9 月第一周的周一落在 8/31），只拉周一所在月份会让跨月日
                // （9/2、9/3 等）在网格中无事件，刷新也无济于事。
                datesSet={(arg) => {
                    if (onRangeChange) {
                        onRangeChange({ start: arg.start, end: arg.end });
                    }
                    // 记录当前视图类型，触发 events 重算（归集仅周视图生效）。
                    setViewType(arg.view.type);
                    // 视图切换 / 数据刷新后会清空并重新挂载事件 harness，FC 会重新算 top/height，
                    // 这里再触发一次纵向重排 + 归集卡片高度设置。
                    // rAF 等到 eventDidMount 之后的同一帧再执行，避免拿到还未写入的 inline style.top。
                    requestAnimationFrame(() => rearrangeSameTimeEvents());
                }}
                events={events}
                // 事件挂载时记录 event.id → 定位容器(harness) DOM 映射，供手动重排使用；
                // 卸载时清理，避免 Map 持有已脱离 DOM 的元素。
                eventDidMount={(info: EventMountArg) => {
                    // FC v6 的定位容器是 .fc-timegrid-event-harness（top/height 写在它身上），
                    // 而 info.el 可能是内层 <a class="fc-timegrid-event">（无 top）。
                    // 用 closest 兑底，保证拿到真正带 inline style.top 的元素。
                    const harness = (info.el.closest('.fc-timegrid-event-harness') ?? info.el) as HTMLElement;
                    eventRefs.current.set(info.event.id, harness);
                    // ⚠ 首帧挂载时 FC 的 slat 坐标（时间格行高）可能尚未测量完成，
                    // computeSegVStyle 会把 top 写成空字符串（v6 用 top/bottom 定位），
                    // 此时 parseFloat('') = NaN，直接缓存会变成 0，rearrange 用 baseTop=0
                    // 把所有同组事件堆到时间轴顶部（0 点位置），且会覆盖 FC 之后补写的
                    // 正确 top——表现为「首屏错位、prev/next 导航后恢复」。
                    // 因此这里重试几帧：读到有效像素值才缓存；始终无效则不缓存，
                    // rearrange 侧遇到缺失基准的组会跳过（保持 FC 自己的定位）。
                    const cacheBaseTop = (retriesLeft: number) => {
                        const raw = parseFloat(harness.style.top);
                        if (Number.isFinite(raw)) {
                            eventBaseTops.current.set(info.event.id, raw);
                            requestAnimationFrame(() => rearrangeSameTimeEvents());
                        } else if (retriesLeft > 0) {
                            requestAnimationFrame(() => cacheBaseTop(retriesLeft - 1));
                        }
                    };
                    cacheBaseTop(4);
                    // 归集卡片按双层结构撑开高度（各组：组头 + 组内消息 × 行高，另加上下内距）。
                    // 不这样做的话，FC 只按 duration 给一个很矮的高度（约 eventShortHeight 24px），
                    // 桶内多条消息会被裁切成一节。
                    const groupEvents = info.event.extendedProps.groupEvents as
                        | LiveCalendarEventDef[]
                        | undefined;
                    if (groupEvents && groupEvents.length > 0) {
                        // 高度按「双层结构」计算：各组(组头 + 组内消息)累加 + 卡片上下内距，
                        // 与 GroupedEventContent 实际渲染的行数保持一致，避免内容被裁切。
                        const groups = eventGroupByTimeAndImportance(groupEvents);
                        harness.style.height = `${calcGroupCardHeight(groups)}px`;
                    }
                }}
                eventWillUnmount={(info: EventMountArg) => {
                    eventRefs.current.delete(info.event.id);
                    eventBaseTops.current.delete(info.event.id);
                }}
                // 短事件按 Breezy 的紧凑高度渲染（v6 支持该选项）
                eventShortHeight={24}
                // 时间网格（周/日视图）：关闭事件堆叠。同时间段多条事件（如同分钟发布的快讯）
                // 改为横向并排分列，避免全部叠成一团；默认 true 会让同 slot 的事件按 z-index 堆叠
                // 并互相截断，导致「12:02 一坨」的问题。月视图不受此选项影响。
                slotEventOverlap={false}
                // ── 表头：星期胶囊（对齐 Breezy dayHeaderInnerClass / dayHeaderContent）
                dayHeaderClassNames="border-0 bg-transparent"
                dayHeaderContent={(arg) => (
                    // 周/日视图下，今日所在的表头单元格用主题色 pill 高亮（替代之前 dayCellContent
                    // 在日期格顶部画的圆点）；非今日保持原来的灰色圆角矩形。
                    <span
                        className={cn(
                            'inline-flex items-center justify-center px-1.5 py-1 text-xs font-semibold tracking-wide transition-colors',
                            arg.isToday
                                ? 'rounded-full bg-primary text-primary-foreground'
                                : 'rounded-sm text-muted-foreground',
                        )}
                    >
                        {arg.text}
                    </span>
                )}
                // ── 日期格：非本月淡化、非今日弱化（对齐 Breezy dayCellClass）
                dayCellClassNames={(arg) =>
                    cn(arg.isToday && 'bg-transparent', arg.isOther && 'bg-muted/20')
                }
                // 月视图下不自定义 dayCellContent：FC 用默认 `a.fc-daygrid-day-number` 渲染
                // 日期数字（月视图）；今日 pill 已改由 dayHeaderContent 在周/日表头承载。
                // ── 事件：圆角淡色块（对齐 Breezy rowEventClass）
                eventClassNames={() => [
                    'group block w-full cursor-pointer rounded-md',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
                ]}
                eventContent={(arg) => {
                    // 归集卡片（extendedProps.groupEvents 非空）渲染为双层结构的消息列表；
                    // 其余走单条事件渲染（[色点 + 时间] 在上、标题在下，标题可换行）。
                    const groupEvents = arg.event.extendedProps.groupEvents as
                        | LiveCalendarEventDef[]
                        | undefined;
                    if (groupEvents && groupEvents.length > 0) {
                        // 先把扁平事件数组整理成双层结构（按时间 + 重要度分组），
                        // 再把分组结果 A 传给 GroupedEventContent，组件内不再做分组计算。
                        const groups = eventGroupByTimeAndImportance(groupEvents);
                        // 周视图下点归集卡片内的消息：打开详情 + 切到该日日视图
                        // （与月视图 handleEventClick 点事件 → 切日视图的语义一致）。
                        const handleSelectInGroup = (item: LiveCalendarEventDef) => {
                            onSelectEvent(item);
                            calendarRef.current
                                ?.getApi()
                                .changeView('timeGridDay', new Date(item.startAt * 1000));
                        };
                        return (
                            <GroupedEventContent
                                groups={groups}
                                onSelectEvent={handleSelectInGroup}
                            />
                        );
                    }
                    return (
                        <CalendarEventContent event={arg.event.extendedProps.eventDef as LiveCalendarEventDef} />
                    );
                }}
                // ── 更多+   折叠「+N」：浅色胶囊（对齐 Breezy rowMoreLinkClass）
                moreLinkClassNames="block w-full cursor-pointer border-0 rounded-sm! bg-transparent hover:bg-foreground-subtle"
                moreLinkContent={(arg) => (
                    <span className="flex items-center gap-1 px-1.5 py-1 text-xs font-normal text-foreground-dim hover:font-semibold">
                        +{arg.num} {t('liveCalendar.more')}
                    </span>
                )}
                dateClick={handleDateClick}
                eventClick={handleEventClick}
                initialDate={initialDate}
                {...props}
            />
        </div>
    );
};
