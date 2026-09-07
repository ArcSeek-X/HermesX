/**
 * LiveCalendar.tsx
 * ------------------------------------------------------------
 * 消息日历组件：基于 FullCalendar v6（6.1.21）的二次封装，提供
 * **月 / 周 / 日 / 列表**四种视图。
 *
 * 视觉目标：对齐 FullCalendar 官方 Breezy 主题（参考同目录 `demo/event-calendar.tsx`），
 * 在 v6 能力范围内高保真近似：细网格线、星期胶囊表头、今日主题色 pill、
 * 圆角淡色事件块（色点 + 时间在上、标题在下）、溢出折叠为「+N」。
 *
 * 视图要点：
 * - 月视图：按天归格，最多 3 条 + `+N` 折叠；点事件 / 日期格 → 切入日视图定位当日。
 * - 周视图：同时段（默认 60 分钟窗口）达阈值（默认 3 条）的消息归集成一张卡片，
 *   卡片内按时间分组、组内按重要度降序；详见 `GroupedEventContent`。
 * - 日视图：时间轴逐条展示，同时间段事件纵向错开。
 * - List 视图：**不走 FullCalendar**（v6 的 list 插件只有「时间 + 标题」两列，做不出
 *   四列真表头），由 `LiveCalendarListView` 自绘，与本组件平级、按 `viewType` 条件渲染。
 *
 * 版本约束：Breezy 主题基于 FullCalendar 7.x 的 Themes API（`viewClass` / `dayHeaderClass`
 * / `rowEventClass` 等一整套 `*Class` hook），本项目锁 6.1.21，这些 hook 均不存在，
 * 因此改用 v6 等价入口实现同一视觉：`dayHeaderContent` / `dayCellClassNames` /
 * `eventContent` / `moreLinkContent` / `viewClassNames`。故本实现是「视觉近似」，
 * 不可能与 7.x demo 逐像素 1:1。
 *
 * 样式分层：容器层的 `[&_.fc-*]` 覆盖与 `--fc-*` 变量集中在同目录 `csscover.ts`
 * （常量 `LIVE_CALENDAR_CSS_COVER`），改样式请去那里（维护约定写在该文件头部）。
 *
 * 遵循 .conventions/frontend/COMPONENTS.md：`React.ComponentProps` 继承原生 TS 类型、
 * 业务属性解构后其余透传、`cn()` 合并样式且外部 className 优先级最高。
 *
 * 选型理由与主题映射详见 docs/Live-calendar.md §9；List 视图详见 §20。
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
// 色板下沉到 eventTheme.ts：网格视图与 List 视图共用，留在本文件会让 List 反向 import 成环。
import { eventThemeMap } from './eventTheme';
// List 视图自绘组件（FC 的 list 插件做不出四列真表头），其工具栏也一并归它自绘。
import { LiveCalendarListView } from './LiveCalendarListView';
// FullCalendar v6 把样式内联进 JS bundle，官方不再提供独立 CSS；单独 import 会让 vite
// 报 Missing specifier。其 <style> 位于 head 最前，故 Tailwind 原子类可正常覆盖。

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
     * 视图日期范围变化回调（切换视图 / prev / next / today 触发），Page 据此拉取覆盖月份的数据。
     * 必须下发完整可见范围而非单一月份：周视图可能跨月（如 9 月第一周的周一落在 8/31），
     * 只拉周一所在月份会让跨月日无事件。
     */
    onRangeChange?: (range: LiveCalendarRange) => void;
    /** 外层容器自定义类名 */
    className?: string;
};

/** 归集卡片的分组方式（暂不对外暴露，内部预留扩展） */
type GroupMethod = 'timeAndImportance' | 'time';

// ── 周视图：同时段多条消息归集为一张卡片 ──────────────────────────────────
// 同一时间窗口内且数量达阈值的消息合并成一个 FC 事件，卡片内按「(时间, 重要度)」双层结构展示，
// 避免并排挤成窄条或堆叠互相截断。
/**
 * 「同一时间段」容差（分钟），同时作用于两处：
 *  1. 周视图归集卡片：相邻事件 startAt 差 ≤ 该值 → 同组；
 *  2. 周 / 日视图纵向堆叠：相邻事件时间差 ≤ 该值 → 纵向错开。
 * 采用滑动窗口聚类（桶边界由数据驱动、非固定整点），跨整点的连续事件不会被拆开。
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
 * 把桶内事件整理成双层结构：
 * - `time`（默认）：只按 `startAt` 分组，同时间的消息不论重要度合并一组，组内按重要度降序；
 * - `timeAndImportance`：按 (startAt, importance) 分组，时间与重要度都相同才合并。
 *
 * ⚠ 输入须已按 `startAt` 升序（`toFullCalendarEvents` 已保证），否则「相邻」判定失效。
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
        // ── 按时间 + 重要度归集：相邻且时间相同 && 重要度相同才合并 ──
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
 * **同时段归集仅周视图生效**（`viewType === 'timeGridWeek'`）：组内条数 ≥ `GROUP_THRESHOLD`
 * 时合并为一个 FC 事件（`extendedProps.groupEvents` 携带原数组，渲染成归集卡片），
 * 未达阈值则逐条输出；月 / 日视图一律逐条输出。
 *
 * 合并事件的 `eventDef` 取桶内第一条作「代表」，用于点击卡片整体时的详情定位。
 */
function toFullCalendarEvents(
    eventsByDay: Map<string, LiveCalendarEventDef[]>,
    viewType: string,
) {
    const result: Array<{
        // 稳定 id（`evt-...` / `group-...`）：eventDidMount 靠它关联 DOM（纵向重排、卡片撑高）
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
        // 按时间升序
        const sorted = events.slice().sort((a, b) => a.startAt - b.startAt);

        // 仅周视图归集
        const enableGrouping = viewType === 'timeGridWeek';

        // 滑动时间窗口聚类：相邻事件差 ≤ 窗口 → 同组
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

        // 按组输出，保证 FC 事件顺序与视觉顺序一致
        groups.forEach((group) => {
            const bucketStart = group.startAt;
            const bucket = group.items;

            if (enableGrouping && bucket.length >= GROUP_THRESHOLD) {
                // 达标 → 合并成一张归集卡片
                result.push({
                    id: `group-${dayKey}-${bucketStart}`,
                    title: bucket[0].shortTitle,
                    start: new Date(bucketStart * 1000),
                    // 全天标记取组内首条，避免全天事件被误判
                    allDay: bucket[0].isAllDay,
                    extendedProps: { eventDef: bucket[0], groupEvents: bucket },
                });
            } else {
                // 未达标 → 逐条输出
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

/** 单条事件的格子内容：[色点 + 时间] 在上、标题在下，对齐 Breezy rowEvent 的节奏 */
function CalendarEventContent({ event }: { event: LiveCalendarEventDef }) {
    const theme = eventThemeMap(event.importance);
    return (
        <div
            className={cn(
                // w-full 占满日期格；mt/mb 与相邻事件留间距
                'flex w-full flex-col gap-0.5 rounded-sm pl-2 pr-1 pt-1.5 pb-2 mt-1 mb-1.5 text-xs transition-colors',
                theme.bg,
                theme.text,
            )}
        >
            {/* 色点 + 时间（全天事件无时间） */}
            <div className="flex items-center gap-1">
                <span aria-hidden className={cn('shrink-0 text-lg font-bold leading-none', theme.text)}>·</span>
                {!event.isAllDay ? (
                    <div className="shrink-0 font-medium tabular-nums opacity-80">
                        {formatTime(event.startAt)}
                    </div>
                ) : null}
            </div>

            {/* 标题：FC 的 .fc-daygrid-event 默认 white-space:nowrap 会继承下来，
                必须显式 whitespace-normal；不用 truncate，超长撑高后由 dayMaxEvents 折叠成「+N」 */}
            <span className="whitespace-normal break-words font-medium leading-tight">
                {event.shortTitle}
            </span>
        </div>
    );
}

/**
 * 归集卡片内容：按「组（时间 + 重要级）→ 组内消息」双层结构渲染。
 *
 * 交互约定：
 * - **组头（色点 + 时间）纯展示**，无 hover、无点击——它只表达这一组的时间与重要级；
 * - **每条消息是 `<button>`**，点击触发 `onSelectEvent(item)` 并 `stopPropagation()`，
 *   否则会冒泡到 FullCalendar 的 eventClick、用「代表事件」打开错误详情。
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
                // 全天事件无具体时刻，组头不显示时间
                const showTime = group.items.length > 0 && !group.items[0].isAllDay;

                return (
                    <div
                        key={`${group.startAt}-${group.importance}-${gi}`}
                        className={cn(gi > 0 && 'mt-1')}
                    >
                        {/* 组头：纯展示 */}
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

                        {/* 组内消息：色点/文字色取 item 自身 importance（兼容 time 模式混重要度） */}
                        <div className="flex flex-col">
                            {group.items.map((item, ii) => {
                                const theme = eventThemeMap(item.importance);
                                return (
                                    <button
                                        key={`${item.startAt}-${item.shortTitle}-${ii}`}
                                        type="button"
                                        onClick={(e) => {
                                            // 阻止冒泡到 FC eventClick（否则用「代表事件」打开详情）
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

// ── List 视图的范围计算 ─────────────────────────────────────────────────
// 渲染组件在 `LiveCalendarListView.tsx`（自绘，FC 的 list 插件做不出四列真表头）。
// 这里只保留驱动它所需的范围计算：进入时取当前 FC 可见范围所在周，prev / next 按 7 天平移。

/** 取某日所在自然周（firstDay=1 周一）的 [start, end] */
function weekRangeOf(date: Date): { start: Date; end: Date } {
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const offset = (d.getDay() + 6) % 7; // 周一 → 0
    const start = new Date(d);
    start.setDate(d.getDate() - offset);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    return { start, end };
}

/** 日期平移 n 天 */
function shiftDays(date: Date, days: number): Date {
    const d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
}

/**
 * FullCalendar v6 二次封装：月 / 周 / 日视图 + List 视图（后者见 `LiveCalendarListView`）。
 *
 * 月视图点事件或日期格 → 切日视图并定位该日（数据仍来自 Page 按月拉取的 eventsByDay，
 * 切视图不触发重新请求）；周 / 日 / List 视图点击走 onSelectDay / onSelectEvent 的详情定位语义。
 */
export const LiveCalendar = ({
    eventsByDay,
    onSelectDay,
    onSelectEvent,
    onRangeChange,
    className,
    ...props
}: LiveCalendarProps) => {
    // 当前视图类型（dayGridMonth / timeGridWeek / timeGridDay / list），由 datesSet 同步
    const [viewType, setViewType] = useState<string>('dayGridMonth');
    // List 视图可见范围：步长 7 天，默认「今天所在周」
    const [listRange, setListRange] = useState<{ start: Date; end: Date }>(() =>
        weekRangeOf(new Date()),
    );
    /** viewType 的 ref 镜像：datesSet 可能被 FC 持有旧闭包，用 ref 才能可靠判断「FC 处于隐藏态」 */
    const viewTypeRef = useRef<string>('dayGridMonth');
    viewTypeRef.current = viewType;
    /** 最近一次 FullCalendar 可见范围：切到 List 视图时作为初始范围 */
    const lastFCRange = useRef<{ start: Date; end: Date } | null>(null);
    const events = useMemo(
        () => toFullCalendarEvents(eventsByDay, viewType),
        [eventsByDay, viewType],
    );
    const calendarRef = useRef<FullCalendar | null>(null);
    const { t, language } = useUiLanguage();
    // initialDate 为 initial-only，用空依赖固化一次，避免跨午夜重渲染时漂移
    const initialDate = useMemo(() => new Date(), []);

    /**
     * 手动纵向堆叠：FC timeGrid 原生不支持同时间段事件垂直错开
     * （slotEventOverlap=false 并排挤窄、=true 用 z-index 堆叠互相截断），
     * 故事件挂载后保持 FC 给的 left/right 不动，只覆盖 top/height 依次下移。
     * 视图切换 / 数据刷新（datesSet）后会再次重排，避免被 FC 重置。
     */
    const eventRefs = useRef(new Map<string, HTMLElement>());
    /**
     * FC 原始 top（px）缓存：重排会改写 style.top，若每次都读「当前 top」当基准，
     * 多次重排会不断叠加偏移、事件越排越下。基准只在 eventDidMount 时记录（那时还是 FC 原值）。
     */
    const eventBaseTops = useRef(new Map<string, number>());
    /** 纵向堆叠时每条事件的高度（px） */
    const SAME_TIME_EVENT_HEIGHT = 10;
    /** 纵向堆叠时事件之间的垂直间隔（px） */
    const SAME_TIME_EVENT_GAP = 10;

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
            // 归集卡片有独立高度策略（按双层结构行数撑开），不参与重排
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
                // 首帧 slat 坐标可能未测量完成 → 基准缺失时跳过整组；
                // 用 0 兑底会把事件全堆到时间轴顶部，等缓存就绪后的下一次重排再统一错开。
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

    /** 点日期格：月视图切日视图展示当日全部事件；周 / 日视图仅更新选中日 */
    const handleDateClick = (info: DateClickArg) => {
        const dayKey = info.dateStr.slice(0, 10);
        onSelectDay(dayKey);
        if (info.view.type === 'dayGridMonth') {
            goToDayView(info.date);
        }
    };

    /**
     * 点事件块：先打开详情，再切到「事件所属日期」的日视图。
     * 月 / 周视图都切（两者语义一致）；日视图本身已在目标日，只开详情不切换。
     * 归集卡片内的具体消息走 `GroupedEventContent` 内 onClick（stopPropagation 阻断冒泡）。
     */
    const handleEventClick = (info: EventClickArg) => {
        const eventDef = info.event.extendedProps.eventDef as LiveCalendarEventDef;
        onSelectEvent(eventDef);
        if (info.view.type === 'dayGridMonth' || info.view.type === 'timeGridWeek') {
            goToDayView(info.event.start ?? info.event.startStr);
        }
    };

    /**
     * 视图切换（月 / 周 / 日 / List）。
     * - 切到 List：以当前 FC 可见范围所在周（无则今天所在周）为初始范围并通知 Page 拉数；
     * - 切回 FC 视图：⚠ 必须 `updateSize()`——List 下 FC 为 display:none，恢复后不重算会布局塌陷。
     */
    const handleViewChange = (next: string) => {
        if (next === 'list') {
            const base = lastFCRange.current?.start ?? new Date();
            const nextRange = weekRangeOf(base);
            setListRange(nextRange);
            setViewType('list');
            if (onRangeChange) {
                onRangeChange({ start: nextRange.start, end: nextRange.end });
            }
            return;
        }
        setViewType(next);
        requestAnimationFrame(() => {
            const api = calendarRef.current?.getApi();
            if (!api) return;
            api.changeView(next);
            api.updateSize();
        });
    };

    /** List 视图的 prev / today / next：按 7 天平移可见范围，并通知 Page 拉数 */
    const handleListNav = (dir: 'prev' | 'next' | 'today') => {
        const next =
            dir === 'today'
                ? weekRangeOf(new Date())
                : {
                      start: shiftDays(listRange.start, dir === 'prev' ? -7 : 7),
                      end: shiftDays(listRange.end, dir === 'prev' ? -7 : 7),
                  };
        setListRange(next);
        if (onRangeChange) {
            onRangeChange({ start: next.start, end: next.end });
        }
    };

    return (
        <div
            // 覆盖层在前、className 在后：保证调用方类名优先级最高（twMerge 后写的赢）
            className={cn(LIVE_CALENDAR_CSS_COVER, className)}
        >
            {/* FullCalendar：List 视图下隐藏（实例保留，切回时即时恢复、不重建不重拉） */}
            <div className={cn(viewType === 'list' && 'hidden')}>
            <FullCalendar
                ref={calendarRef}
                plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                initialView="dayGridMonth"
                locale={calendarLocaleOf(language)}
                firstDay={1}
                dayMaxEvents={3}
                // 关闭当前时间指示器：易与今日 pill / 事件块混淆，
                // 「今日」语义由 dayHeaderContent 的主题色 pill 承担
                nowIndicator={false}
                // 按内容自由展开（不用固定 height / aspectRatio，避免内部滚动条与挤压）
                contentHeight="auto"
                expandRows={true}
                // ── 工具栏 ──────────────────────────────────────────────
                // start 用逗号 = 同一个 .fc-button-group（prev/today/next 连体胶囊）；
                // end 用空格 = 月/周/日/list 四个独立按钮（配合 csscover 的 :is(...) 渲染成纯文字切换器）。
                // List 按钮只借用 FC 的按钮位与样式（.fc-list-button，见 csscover 的 VIEW_SWITCHER），
                // 它并非 FC 视图，点击后由 handleViewChange('list') 切到自绘 List 视图。
                customButtons={{
                    list: {
                        text: t('common.datetime.list'),
                        click: () => handleViewChange('list'),
                    },
                }}
                headerToolbar={{
                    start: 'prev,today,next',
                    center: 'title',
                    end: 'dayGridMonth timeGridWeek timeGridDay list',
                }}
                buttonText={{
                    today: t('common.datetime.today'),
                    dayGridMonth: t('common.datetime.month'),
                    timeGridWeek: t('common.datetime.week'),
                    timeGridDay: t('common.datetime.day'),
                }}
                // 下发完整可见范围（而非单一月份），原因见 onRangeChange 注释
                datesSet={(arg) => {
                    // 记录 FC 可见范围，供切到 List 视图时作初始范围
                    lastFCRange.current = { start: arg.start, end: arg.end };
                    // List 视图下 FC 处于隐藏态，其 datesSet 若继续生效会把 viewType 打回 dayGridMonth
                    if (viewTypeRef.current === 'list') return;
                    if (onRangeChange) {
                        onRangeChange({ start: arg.start, end: arg.end });
                    }
                    // 记录视图类型，触发 events 重算（归集仅周视图生效）
                    setViewType(arg.view.type);
                    // rAF 等到 eventDidMount 之后再重排，避免读到尚未写入的 inline style.top
                    requestAnimationFrame(() => rearrangeSameTimeEvents());
                }}
                events={events}
                // 事件挂载时记录 event.id → 定位容器(harness) DOM 映射，供手动重排使用；
                // 卸载时清理，避免 Map 持有已脱离 DOM 的元素。
                eventDidMount={(info: EventMountArg) => {
                    // top/height 写在 .fc-timegrid-event-harness 上，info.el 可能是内层 <a>，用 closest 兜底
                    const harness = (info.el.closest('.fc-timegrid-event-harness') ?? info.el) as HTMLElement;
                    eventRefs.current.set(info.event.id, harness);
                    // ⚠ 首帧 slat 坐标可能未测量完成 → top 为空串（parseFloat = NaN）。
                    // 若把 NaN 当 0 缓存，同组事件会被堆到时间轴顶部（首屏错位、导航后恢复）。
                    // 故重试几帧，读到有效像素才缓存；始终无效则不缓存（rearrange 侧会跳过该组）。
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
                    // 归集卡片按双层结构撑高：FC 只按 duration 给约 24px，桶内多条会被裁切
                    const groupEvents = info.event.extendedProps.groupEvents as
                        | LiveCalendarEventDef[]
                        | undefined;
                    if (groupEvents && groupEvents.length > 0) {
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
                // ── 表头：星期胶囊
                dayHeaderClassNames="border-0 bg-transparent"
                dayHeaderContent={(arg) => (
                    // 今日用主题色 pill 高亮，非今日为灰色圆角
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
                // ── 日期格：非本月淡化
                dayCellClassNames={(arg) =>
                    cn(arg.isToday && 'bg-transparent', arg.isOther && 'bg-muted/20')
                }
                // 月视图不自定义 dayCellContent：沿用 FC 默认日期数字，今日高亮由 dayHeaderContent 承担
                // ── 事件块：圆角淡色
                eventClassNames={() => [
                    'group block w-full cursor-pointer rounded-md',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
                ]}
                eventContent={(arg) => {
                    // groupEvents 非空 → 归集卡片（双层结构）；否则单条事件
                    const groupEvents = arg.event.extendedProps.groupEvents as
                        | LiveCalendarEventDef[]
                        | undefined;
                    if (groupEvents && groupEvents.length > 0) {
                        // 分组在调用处算好再传入，GroupedEventContent 只负责渲染
                        const groups = eventGroupByTimeAndImportance(groupEvents);
                        // 与月视图点事件语义一致：打开详情 + 切到该日日视图
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
                // ── 折叠「+N」：浅色胶囊
                moreLinkClassNames="block w-full cursor-pointer border-0 rounded-sm! bg-transparent hover:bg-foreground-subtle"
                moreLinkContent={(arg) => (
                    <span className="flex items-center gap-1 px-1.5 py-1 text-xs font-normal text-foreground-dim hover:font-semibold">
                        +{arg.num} {t('component.LiveCalendar.more')}
                    </span>
                )}
                dateClick={handleDateClick}
                eventClick={handleEventClick}
                initialDate={initialDate}
                {...props}
            />
            </div>

            {/* List 视图：与 FullCalendar 平级；点击走 onSelectEvent（详情面板定位） */}
            {viewType === 'list' ? (
                <LiveCalendarListView
                    eventsByDay={eventsByDay}
                    range={listRange}
                    onSelectEvent={onSelectEvent}
                    onNavigate={handleListNav}
                    onViewChange={handleViewChange}
                />
            ) : null}
        </div>
    );
};
