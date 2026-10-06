/**
 * LiveCalendar.tsx
 * 消息日历组件：基于 FullCalendar v6 封装月 / 周 / 日视图，并补齐自绘 List 视图、
 * 月视图受控翻月、周视图同时间段归集卡片、日/周视图事件纵向错位等业务行为。
 *
 * 使用场景：
 * - 供 `LiveCalendarPage` 直接消费；
 * - 外部只负责按请求范围准备 `eventsMap`，组件内部管理视图切换、详情抽屉和月视图 staged mount。
 *
 * 样式入口统一在同目录 `csscover.ts`，这里主要维护交互与数据转换逻辑。
 *
 * @author Lensgcx (GaoCangxiong)
 */

import { memo, startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import type { DatesSetArg, EventClickArg, EventMountArg } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { DateClickArg } from '@fullcalendar/interaction';
import zhCnLocale from '@fullcalendar/core/locales/zh-cn';
import zhTwLocale from '@fullcalendar/core/locales/zh-tw';
import { cn } from '../../../utils/cn';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiLanguage } from '../../../i18n/uiText';
import type { CalendarCountryDef, LiveCalendarEventDef } from '../../../types/liveCalendar';
import { LIVE_CALENDAR_CSS_COVER } from './csscover';
import { formatTime } from '../../../utils/format';
// 色板下沉到 eventTheme.ts：网格视图与 List 视图共用，留在本文件会让 List 反向 import 成环。
import { eventThemeMap } from './eventTheme';
// List 视图自绘组件（FC 的 list 插件做不出四列真表头），其工具栏也一并归它自绘。
import { LiveCalendarListView } from './LiveCalendarListView';
// 详情抽屉：点消息 → 内部自管打开（由 Page 传入 countries，不再由 Page 挂载）
import { LiveCalendarEventDrawer } from './LiveCalendarEventDrawer';
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

export interface LiveCalendarRangeRequest {
    /** 当前目标视图类型 */
    viewType: CalendarViewType;
    /** 视图所需的数据范围 */
    range: LiveCalendarRange;
    /** 当前请求对应的锚点日期（月视图取当月 1 号；周/日/List 取当前焦点日期） */
    anchorDate: Date;
    /** 触发原因 */
    reason: 'init' | 'prev' | 'next' | 'today' | 'view-change' | 'list-nav';
    /** 供外层回传 `dataReadyKey` 的稳定 key */
    requestKey: string;
}

/** 业务扩展属性：数据契约经转化喂给 FullCalendar */
export type LiveCalendarProps = React.ComponentProps<typeof FullCalendar> & {
    /** 按天归格的事件（key = YYYY-MM-DD） */
    eventsMap: Map<string, LiveCalendarEventDef[]>;
    /** 点日期空白区 → 通知 Page 选中该日（由 Page 决定如何展示当日全部详情） */
    onSelectDay: (day: string) => void;
    /**
     * 点单条事件 → LiveCalendar 内部自动打开详情抽屉（自管 selectedEvent）。
     * 该回调为可选：如外部需感知点击事件（埋点等）可传入，不影响内部开抽屉行为。
     */
    onSelectEvent?: (event: LiveCalendarEventDef) => void;
    /** 国家字典（国旗 / 货币 / 国家名），来自 Page 的 `useLiveCalendarCountries()`，供详情抽屉渲染 */
    countries?: CalendarCountryDef[];
    /** 组件内部发起的范围请求事件：外层据此准备对应范围的数据 */
    onRangeRequest?: (payload: LiveCalendarRangeRequest) => void;
    /** 外层数据已准备好的 requestKey；月视图会等该 key 就绪后再切换实例 */
    dataReadyKey?: string;
    /** 外层容器自定义类名 */
    className?: string;
};

/** 日历支持的视图类型 */
type CalendarViewType = 'dayGridMonth' | 'timeGridWeek' | 'timeGridDay' | 'list';

/** 月视图切换中的待提交请求 */
interface PendingMonthRequest {
    /** 外层准备数据后回传的 requestKey */
    requestKey: string;
    /** 数据 ready 后真正切换到的目标月份 */
    targetDate: Date;
}

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
const FULL_CALENDAR_PLUGINS = [dayGridPlugin, timeGridPlugin, interactionPlugin];
const FULL_CALENDAR_HEADER_TOOLBAR = {
    start: 'prev,today,next',
    center: 'title',
    end: 'dayGridMonth timeGridWeek timeGridDay list',
} as const;
const MONTH_TOOLBAR_BUTTON_WIDTH = 'w-[80px]';
const TIME_GRID_EVENT_HEIGHT = 10;
const TIME_GRID_EVENT_GAP = 10;

function monthAnchorDateOf(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), 1);
}

function monthGridRangeOf(date: Date): LiveCalendarRange {
    const first = monthAnchorDateOf(date);
    const last = new Date(first.getFullYear(), first.getMonth() + 1, 0);
    const start = new Date(first);
    start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
    const end = new Date(last);
    end.setDate(last.getDate() + (6 - ((last.getDay() + 6) % 7)));
    return { start, end };
}

function monthsKeyOfRange(range: LiveCalendarRange): string {
    const start = new Date(range.start);
    start.setDate(start.getDate() - 1);
    const end = new Date(range.end);
    end.setDate(end.getDate() + 1);
    const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
    const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);
    const keys: string[] = [];
    while (cursor <= endMonth) {
        keys.push(`${cursor.getFullYear()}-${cursor.getMonth() + 1}`);
        cursor.setMonth(cursor.getMonth() + 1);
    }
    return keys.join('|');
}

function shiftMonthDate(date: Date, delta: number): Date {
    return monthAnchorDateOf(new Date(date.getFullYear(), date.getMonth() + delta, 1));
}

/** 归集卡片的双层数据结构：外层是时间组，内层是该组下的事件列表。 */
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
 * 把同一时间桶内的事件整理成归集卡片需要的双层结构。
 *
 * @param events 需先按 `startAt` 升序传入
 * @param method 分组方式；默认只按时间聚合
 * @returns 归集卡片使用的分组结果
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
 * 把按天归格的事件展平为 FullCalendar 可消费的事件数组。
 *
 * 约定：
 * - 周视图满足阈值的同时间段事件合并成归集卡片；
 * - 月 / 日视图保持逐条渲染；
 * - 输出 id 必须稳定，供挂载后缓存 DOM 和定位重排。
 *
 * @param eventsMap 按天归格的事件映射
 * @param viewType 当前视图类型
 * @returns FullCalendar 事件数组
 */
function toFullCalendarEvents(
    eventsMap: Map<string, LiveCalendarEventDef[]>,
    viewType: CalendarViewType,
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

    for (const [dayKey, events] of eventsMap) {
        // 仅周视图归集
        const enableGrouping = viewType === 'timeGridWeek';
        const orderedEvents =
            viewType === 'dayGridMonth'
                ? events
                : events.slice().sort((a, b) => a.startAt - b.startAt);

        // 滑动时间窗口聚类：相邻事件差 ≤ 窗口 → 同组
        const windowSec = SAME_TIME_WINDOW_MIN * 60;
        const groups: Array<{ startAt: number; items: LiveCalendarEventDef[] }> = [];
        // 月视图直接复用 hook 层的「重要级优先」顺序；周 / 日视图再按时间升序，
        // 保证时间轴布局与归集窗口判断都基于真实时间顺序。
        orderedEvents.forEach((event) => {
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

/** 单条事件在月 / 日 / 周视图中的默认卡片内容。 */
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
 * 周视图归集卡片内容。
 *
 * 组头只负责展示时间和重要级；真正可点击的是组内每一条消息，
 * 需要阻止冒泡，避免落回 FullCalendar 的代表事件点击逻辑。
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
 * 消息日历主组件。
 *
 * @param props.eventsMap 按天归格后的事件映射
 * @param props.onSelectDay 点日期后的回调
 * @param props.onSelectEvent 点单条事件后的补充回调，默认只在组件内开详情抽屉
 * @param props.countries 国家字典，供详情抽屉展示国家名 / 货币 / 国旗
 * @param props.onRangeRequest 组件内部需要新数据时抛出的范围请求事件
 * @param props.dataReadyKey 外层已准备好的请求 key，月视图据此再切换月份
 * @param props.className 外层自定义类名
 * @returns 日历组件
 */
const LiveCalendarInner: React.FC<LiveCalendarProps> = ({
    eventsMap,
    onSelectDay,
    onSelectEvent,
    countries,
    onRangeRequest,
    dataReadyKey,
    className,
    ...props
}) => {
    /** 当前视图类型，由 FullCalendar `datesSet` 与 List 视图切换共同维护。 */
    const [viewType, setViewType] = useState<CalendarViewType>('dayGridMonth');
    /** 月视图当前显示的月份锚点。 */
    const [monthViewDate, setMonthViewDate] = useState<Date>(() => monthAnchorDateOf(new Date()));
    /** 月视图 remount key：仅在目标月数据 ready 后更新。 */
    const [monthViewRenderKey, setMonthViewRenderKey] = useState<string>(() => `month-${Date.now()}`);
    /** 月视图翻月中的待提交请求。 */
    const [pendingMonthRequest, setPendingMonthRequest] = useState<PendingMonthRequest | null>(null);
    /** 当前选中的事件；有值时打开详情抽屉。 */
    const [selectedEvent, setSelectedEvent] = useState<LiveCalendarEventDef | null>(null);
    /** 点单条事件：内部打开详情抽屉，并可选地通知外部。 */
    const handleSelectEvent = useCallback(
        (event: LiveCalendarEventDef) => {
            setSelectedEvent(event);
            onSelectEvent?.(event);
        },
        [onSelectEvent],
    );
    /** List 视图可见范围，默认取今天所在周。 */
    const [listRange, setListRange] = useState<{ start: Date; end: Date }>(() =>
        weekRangeOf(new Date()),
    );
    /** `datesSet` 里要用到最新视图类型，避免拿到旧闭包。 */
    const viewTypeRef = useRef<CalendarViewType>('dayGridMonth');
    /** 最近一次 FullCalendar 的可见范围，切到 List 视图时用它确定初始周范围。 */
    const lastFCRange = useRef<{ start: Date; end: Date } | null>(null);
    const events = useMemo(
        () => toFullCalendarEvents(eventsMap, viewType),
        [eventsMap, viewType],
    );
    const calendarRef = useRef<FullCalendar | null>(null);
    const { t, language } = useUiLanguage();
    const initializedRef = useRef(false);
    const isMonthNavigating = pendingMonthRequest !== null;
    const monthToolbarTitle = useMemo(
        () =>
            new Intl.DateTimeFormat(
                language === 'zh-Hant' ? 'zh-TW' : language === 'zh' ? 'zh-CN' : 'en-US',
                { year: 'numeric', month: 'long' },
            ).format(monthViewDate),
        [language, monthViewDate],
    );

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
    const rearrangeFrameRef = useRef<number | null>(null);
    const rearrangeSameTimeEvents = useCallback(() => {
        const api = calendarRef.current?.getApi();
        if (!api) return;
        // 仅在 timeGrid（周/日）视图生效；月视图有自己的事件布局策略，不要干预。
        if (api.view.type !== 'timeGridWeek' && api.view.type !== 'timeGridDay') return;

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

        const byDay = new Map<string, Entry[]>();
        entries.forEach((entry) => {
            const d = new Date(entry.startMs);
            const dayKey = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
            if (!byDay.has(dayKey)) byDay.set(dayKey, []);
            byDay.get(dayKey)!.push(entry);
        });

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
                    entry.el.style.top = `${baseTop + i * (TIME_GRID_EVENT_HEIGHT + TIME_GRID_EVENT_GAP)}px`;
                    entry.el.style.height = `${TIME_GRID_EVENT_HEIGHT}px`;
                });
            });
        });
    }, []);

    const scheduleRearrange = useCallback(() => {
        if (rearrangeFrameRef.current !== null) return;
        rearrangeFrameRef.current = requestAnimationFrame(() => {
            rearrangeFrameRef.current = null;
            rearrangeSameTimeEvents();
        });
    }, [rearrangeSameTimeEvents]);

    useEffect(() => {
        viewTypeRef.current = viewType;
    }, [viewType]);

    useEffect(() => {
        return () => {
            if (rearrangeFrameRef.current !== null) {
                cancelAnimationFrame(rearrangeFrameRef.current);
            }
        };
    }, []);

    /** 月视图切月时，等外层数据 ready 再真正提交月份切换。 */
    useEffect(() => {
        if (!pendingMonthRequest || dataReadyKey !== pendingMonthRequest.requestKey) return;
        const commitId = window.setTimeout(() => {
            setMonthViewDate(pendingMonthRequest.targetDate);
            setMonthViewRenderKey(`${pendingMonthRequest.requestKey}-${Date.now()}`);
            setPendingMonthRequest(null);
        }, 0);
        return () => window.clearTimeout(commitId);
    }, [dataReadyKey, pendingMonthRequest]);

    /**
     * 向外抛出数据请求事件。
     *
     * @param viewType 目标视图
     * @param range 请求范围
     * @param anchorDate 视图锚点日期
     * @param reason 触发原因
     * @returns 本次请求的稳定 key
     */
    const emitDataRequest = useCallback((
        nextViewType: CalendarViewType,
        range: LiveCalendarRange,
        anchorDate: Date,
        reason: LiveCalendarRangeRequest['reason'],
    ) => {
        const requestKey = monthsKeyOfRange(range);
        const payload: LiveCalendarRangeRequest = {
            viewType: nextViewType,
            range,
            anchorDate,
            reason,
            requestKey,
        };
        onRangeRequest?.(payload);
        return requestKey;
    }, [onRangeRequest]);

    /** 月视图翻月时先只发起数据请求，等外层数据 ready 后再 remount 日历实例。 */
    const emitMonthDataRequest = useCallback((
        targetDate: Date,
        reason: LiveCalendarRangeRequest['reason'],
    ) => {
        const anchorDate = monthAnchorDateOf(targetDate);
        const range = monthGridRangeOf(anchorDate);
        const requestKey = emitDataRequest('dayGridMonth', range, anchorDate, reason);
        return { anchorDate, requestKey };
    }, [emitDataRequest]);

    /** 切换到日视图并定位到指定日期（供月视图点击穿透使用；changeView 接受 DateInput） */
    const goToDayView = useCallback((date: Date | string) => {
        calendarRef.current?.getApi().changeView('timeGridDay', date);
    }, []);

    /** 点日期格：月视图切日视图展示当日全部事件；周 / 日视图仅更新选中日 */
    const handleDateClick = useCallback((info: DateClickArg) => {
        const dayKey = info.dateStr.slice(0, 10);
        onSelectDay(dayKey);
        if (info.view.type === 'dayGridMonth') {
            goToDayView(info.date);
        }
    }, [goToDayView, onSelectDay]);

    /**
     * 点事件块：**只打开 Drawer 详情，不切视图**（月 / 周 / 日三视图语义一致）。
     * 切日视图仅由「点日期格 / 日期标题」触发（见 handleDateClick），
     * 两条路径刻意分开：点消息看这条的内容，点日期看那天的全部。
     * 归集卡片内的具体消息走 `GroupedEventContent` 内 onClick（stopPropagation 阻断冒泡）。
     */
    const handleEventClick = useCallback((info: EventClickArg) => {
        const eventDef = info.event.extendedProps.eventDef as LiveCalendarEventDef;
        handleSelectEvent(eventDef);
    }, [handleSelectEvent]);

    /**
     * 视图切换（月 / 周 / 日 / List）。
     * List 视图是自绘实现，切过去时要单独维护它的范围；切回 FC 视图后要调用
     * `updateSize()`，否则隐藏期间的布局不会自动恢复。
     */
    const handleViewChange = useCallback((next: CalendarViewType) => {
        if (next === 'list') {
            setPendingMonthRequest(null);
            const base = lastFCRange.current?.start ?? new Date();
            const nextRange = weekRangeOf(base);
            setListRange(nextRange);
            setViewType('list');
            emitDataRequest('list', { start: nextRange.start, end: nextRange.end }, nextRange.start, 'view-change');
            return;
        }
        if (next !== 'dayGridMonth') {
            setPendingMonthRequest(null);
        }
        setViewType(next);
        requestAnimationFrame(() => {
            const api = calendarRef.current?.getApi();
            if (!api) return;
            api.changeView(next);
            api.updateSize();
        });
    }, [emitDataRequest]);

    /** List 视图导航：按整周平移范围。 */
    const handleListNav = useCallback((dir: 'prev' | 'next' | 'today') => {
        setListRange((prev) => {
            const next =
                dir === 'today'
                    ? weekRangeOf(new Date())
                    : {
                          start: shiftDays(prev.start, dir === 'prev' ? -7 : 7),
                          end: shiftDays(prev.end, dir === 'prev' ? -7 : 7),
                      };
            emitDataRequest('list', { start: next.start, end: next.end }, next.start, 'list-nav');
            return next;
        });
    }, [emitDataRequest]);

    const customButtons = useMemo(
        () => ({
            list: {
                text: t('common.datetime.list'),
                click: () => handleViewChange('list'),
            },
        }),
        [handleViewChange, t],
    );

    const buttonText = useMemo(
        () => ({
            today: t('common.datetime.today'),
            dayGridMonth: t('common.datetime.month'),
            timeGridWeek: t('common.datetime.week'),
            timeGridDay: t('common.datetime.day'),
        }),
        [t],
    );

    const headerToolbar = useMemo(
        () => (viewType === 'dayGridMonth' ? false : FULL_CALENDAR_HEADER_TOOLBAR),
        [viewType],
    );

    /** 月视图 prev / next / today：先请求数据，再等外层 ready 后切换实例。 */
    const handleMonthNavigate = useCallback((dir: 'prev' | 'next' | 'today') => {
        const targetDate =
            dir === 'today'
                ? monthAnchorDateOf(new Date())
                : shiftMonthDate(monthViewDate, dir === 'prev' ? -1 : 1);
        if (dir === 'today' && monthViewDate.getFullYear() === targetDate.getFullYear() &&
            monthViewDate.getMonth() === targetDate.getMonth()) {
            return;
        }
        const request = emitMonthDataRequest(targetDate, dir);
        setPendingMonthRequest((prev) =>
            prev?.requestKey === request.requestKey
                ? prev
                : { requestKey: request.requestKey, targetDate: request.anchorDate }
        );
    }, [emitMonthDataRequest, monthViewDate]);

    const handleDatesSet = useCallback((arg: DatesSetArg) => {
        lastFCRange.current = { start: arg.start, end: arg.end };
        if (viewTypeRef.current === 'list') return;
        const nextViewType = arg.view.type as CalendarViewType;
        const nextRange = { start: arg.start, end: arg.end };
        const anchorDate =
            nextViewType === 'dayGridMonth'
                ? monthAnchorDateOf(arg.view.currentStart)
                : new Date(arg.view.currentStart);
        if (nextViewType === 'dayGridMonth' && !pendingMonthRequest) {
            setMonthViewDate(anchorDate);
        }
        emitDataRequest(nextViewType, nextRange, anchorDate, initializedRef.current ? 'view-change' : 'init');
        initializedRef.current = true;
        startTransition(() => {
            setViewType(nextViewType);
        });
        scheduleRearrange();
    }, [emitDataRequest, pendingMonthRequest, scheduleRearrange]);

    /** 缓存事件 DOM，并在 timeGrid 视图中记录 FC 原始 top 供后续重排使用。 */
    const handleEventDidMount = useCallback((info: EventMountArg) => {
        const harness = (info.el.closest('.fc-timegrid-event-harness') ?? info.el) as HTMLElement;
        eventRefs.current.set(info.event.id, harness);
        const cacheBaseTop = (retriesLeft: number) => {
            const raw = parseFloat(harness.style.top);
            if (Number.isFinite(raw)) {
                eventBaseTops.current.set(info.event.id, raw);
                scheduleRearrange();
            } else if (retriesLeft > 0) {
                requestAnimationFrame(() => cacheBaseTop(retriesLeft - 1));
            }
        };
        cacheBaseTop(4);
        const groupEvents = info.event.extendedProps.groupEvents as
            | LiveCalendarEventDef[]
            | undefined;
        if (groupEvents && groupEvents.length > 0) {
            const groups = eventGroupByTimeAndImportance(groupEvents);
            harness.style.height = `${calcGroupCardHeight(groups)}px`;
        }
    }, [scheduleRearrange]);

    const handleEventWillUnmount = useCallback((info: EventMountArg) => {
        eventRefs.current.delete(info.event.id);
        eventBaseTops.current.delete(info.event.id);
    }, []);

    const handleDayHeaderContent = useCallback((arg: { isToday: boolean; text: string }) => (
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
    ), []);

    const handleEventContent = useCallback((arg: {
        event: {
            extendedProps: {
                eventDef: LiveCalendarEventDef;
                groupEvents?: LiveCalendarEventDef[];
            };
        };
    }) => {
        const groupEvents = arg.event.extendedProps.groupEvents;
        if (groupEvents && groupEvents.length > 0) {
            const groups = eventGroupByTimeAndImportance(groupEvents);
            return (
                <GroupedEventContent
                    groups={groups}
                    onSelectEvent={handleSelectEvent}
                />
            );
        }
        return <CalendarEventContent event={arg.event.extendedProps.eventDef} />;
    }, [handleSelectEvent]);

    const handleMoreLinkContent = useCallback((arg: { num: number }) => (
        <span className="flex items-center gap-1 px-1.5 py-1 text-xs font-normal text-foreground-dim hover:font-semibold">
            +{arg.num} {t('component.LiveCalendar.more')}
        </span>
    ), [t]);

    return (
        <div
            className={cn(LIVE_CALENDAR_CSS_COVER, className)}
        >
            {viewType === 'dayGridMonth' ? (
                <div className="fc-toolbar fc-header-toolbar">
                    <div className="fc-toolbar-chunk">
                        <div className="fc-button-group">
                            <button
                                type="button"
                                className="fc-button fc-button-primary fc-prev-button"
                                onClick={() => handleMonthNavigate('prev')}
                                disabled={isMonthNavigating}
                                aria-label={t('component.LiveCalendar.prevMonth')}
                            >
                                <span className="fc-icon fc-icon-chevron-left" />
                            </button>
                            <button
                                type="button"
                                className={cn('fc-button fc-button-primary fc-today-button', MONTH_TOOLBAR_BUTTON_WIDTH)}
                                onClick={() => handleMonthNavigate('today')}
                                disabled={isMonthNavigating}
                            >
                                {isMonthNavigating
                                    ? t('component.LiveCalendar.loading')
                                    : t('component.LiveCalendar.today')}
                            </button>
                            <button
                                type="button"
                                className="fc-button fc-button-primary fc-next-button"
                                onClick={() => handleMonthNavigate('next')}
                                disabled={isMonthNavigating}
                                aria-label={t('component.LiveCalendar.nextMonth')}
                            >
                                <span className="fc-icon fc-icon-chevron-right" />
                            </button>
                        </div>
                    </div>
                    <div className="fc-toolbar-chunk">
                        <h2 className="fc-toolbar-title">{monthToolbarTitle}</h2>
                    </div>
                    <div className="fc-toolbar-chunk">
                        <button
                            type="button"
                            className={cn(
                                'fc-button fc-button-primary fc-dayGridMonth-button',
                                'fc-button-active',
                            )}
                            onClick={() => handleViewChange('dayGridMonth')}
                        >
                            {t('common.datetime.month')}
                        </button>
                        <button
                            type="button"
                            className="fc-button fc-button-primary fc-timeGridWeek-button"
                            onClick={() => handleViewChange('timeGridWeek')}
                        >
                            {t('common.datetime.week')}
                        </button>
                        <button
                            type="button"
                            className="fc-button fc-button-primary fc-timeGridDay-button"
                            onClick={() => handleViewChange('timeGridDay')}
                        >
                            {t('common.datetime.day')}
                        </button>
                        <button
                            type="button"
                            className="fc-button fc-button-primary fc-list-button"
                            onClick={() => handleViewChange('list')}
                        >
                            {t('common.datetime.list')}
                        </button>
                    </div>
                </div>
            ) : null}
            <div className={cn(viewType === 'list' && 'hidden')}>
                <FullCalendar
                    /** 月视图数据 ready 后通过变更 key 强制 remount 实例。 */
                    key={monthViewRenderKey}
                    /** 持有 FullCalendar 实例，供视图切换和布局重排读取 API。 */
                    ref={calendarRef}
                    /** 注册月 / 周 / 日所需的 FullCalendar 插件。 */
                    plugins={FULL_CALENDAR_PLUGINS}
                    /** 首次挂载默认进入月视图。 */
                    initialView="dayGridMonth"
                    /** 跟随当前 UI 语言切换日历本地化文案。 */
                    locale={calendarLocaleOf(language)}
                    /** 以周一作为一周起始日。 */
                    firstDay={1}
                    /** 月视图单日最多展示 3 条事件，其余折叠到 more popover。 */
                    dayMaxEvents={3}
                    /** 关闭当前时间红线，避免和业务高亮样式冲突。 */
                    nowIndicator={false}
                    /** 让日历按内容自然撑高，不使用内部滚动。 */
                    contentHeight="auto"
                    /** 补齐网格行高，避免月视图行高不齐。 */
                    expandRows={true}
                    /** 注入自定义导航 / 视图切换按钮定义。 */
                    customButtons={customButtons}
                    /** 配置顶部工具栏布局。 */
                    headerToolbar={headerToolbar}
                    /** 覆盖 FullCalendar 内置按钮文案。 */
                    buttonText={buttonText}
                    /** 视图或日期范围变化时同步组件内部状态并向外抛范围请求。 */
                    datesSet={handleDatesSet}
                    /** 事件集合变化后统一调度 timeGrid 视图的错位重排。 */
                    eventsSet={scheduleRearrange}
                    /** 传入当前范围内已加工好的事件数组。 */
                    events={events}
                    /** 事件挂载后缓存 DOM 引用，供 timeGrid 手动重排使用。 */
                    eventDidMount={handleEventDidMount}
                    /** 事件卸载时清理缓存，避免持有失效 DOM。 */
                    eventWillUnmount={handleEventWillUnmount}
                    /** 短事件使用紧凑高度，贴近当前视觉设计。 */
                    eventShortHeight={24}
                    /** timeGrid 事件不横向重叠，改由组件手动做纵向错位。 */
                    slotEventOverlap={false}
                    /** 去掉星期表头默认边框和背景，交给自定义内容控制。 */
                    dayHeaderClassNames="border-0 bg-transparent"
                    /** 自定义星期表头内容，渲染今日高亮和本地化星期。 */
                    dayHeaderContent={handleDayHeaderContent}
                    /** 非本月日期格做弱化处理，今日格保持透明底。 */
                    dayCellClassNames={(arg) =>
                        cn(arg.isToday && 'bg-transparent', arg.isOther && 'bg-muted/20')
                    }
                    /** 给事件节点追加统一的交互态类名。 */
                    eventClassNames={() => [
                        'group block w-full cursor-pointer rounded-md',
                        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
                    ]}
                    /** 自定义事件块内容，区分普通事件和周视图归集卡片。 */
                    eventContent={handleEventContent}
                    /** more 链接使用当前组件的轻量样式。 */
                    moreLinkClassNames="block w-full cursor-pointer border-0 rounded-sm! bg-transparent hover:bg-foreground-subtle"
                    /** 自定义 more 链接文案，显示 “+N more”。 */
                    moreLinkContent={handleMoreLinkContent}
                    /** 点击日期格时切到对应日期并同步外层选中日。 */
                    dateClick={handleDateClick}
                    /** 点击事件时打开详情抽屉或命中归集卡片的选择逻辑。 */
                    eventClick={handleEventClick}
                    /** 月视图 remount 后从当前受控月份重新初始化。 */
                    initialDate={monthViewDate}
                    {...props}
                />
            </div>

            {viewType === 'list' ? (
                /** List 视图不走 FullCalendar，改用自绘列表承接同一批事件数据。 */
                <LiveCalendarListView
                    eventsMap={eventsMap}
                    range={listRange}
                    onSelectEvent={handleSelectEvent}
                    onNavigate={handleListNav}
                    onViewChange={handleViewChange}
                />
            ) : null}

            {selectedEvent ? (
                /** 选中事件后显示详情抽屉，覆盖月格 more popover 等浮层。 */
                <LiveCalendarEventDrawer
                    event={selectedEvent}
                    countries={countries ?? []}
                    onClose={() => setSelectedEvent(null)}
                />
            ) : null}
        </div>
    );
};

export const LiveCalendar = memo(LiveCalendarInner) as React.MemoExoticComponent<
    React.FC<LiveCalendarProps>
>;

LiveCalendar.displayName = 'LiveCalendar';
