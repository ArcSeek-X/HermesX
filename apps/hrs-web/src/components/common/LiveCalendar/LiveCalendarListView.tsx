/**
 * LiveCalendarListView.tsx
 * ------------------------------------------------------------
 * 消息日历的 **List 视图**：按日分组的四列消息列表。
 *
 * ── 为什么 List 视图不走 FullCalendar ────────────────────────────────────
 * v6 自带的 listWeek / listDay（@fullcalendar/list 插件）原生结构只有
 * 「左时间 + 右标题」两列，`eventContent` 只能改每行内容、**不支持自定义列头
 * 与列数**，做不出「时间 / 新闻标题 / 国家 / 重要度」四列真表头。
 * 因此 List 改为与 <FullCalendar> 平级的自定义组件，由 `LiveCalendar`
 * 在 `viewType === 'list'` 时条件渲染。
 *
 * ── 与 LiveCalendar 的职责边界 ──────────────────────────────────────────
 * - 本组件持有 List 视图的**全部展示层**：自绘工具栏 + 列表体。
 *   List 不是 FC 视图，FC 被隐藏时其内置 toolbar 会一起消失，所以工具栏必须自己画；
 *   工具栏刻意复用 FC 的 `.fc-toolbar` / `.fc-button` / `.fc-*-button` 结构，
 *   让 csscover 里那套 `[&_.fc-*]` 覆盖直接命中，视觉与月 / 周 / 日视图一致。
 * - **状态仍在 `LiveCalendar`**：`listRange`（可见范围 + 通知 Page 拉数）与
 *   `viewType`（决定渲染 FC 还是本组件）都由父级持有 —— 视图切换可能卸载本组件，
 *   这个开关不能由本组件自己拥有。工具栏只通过 `onNavigate` / `onViewChange`
 *   上抛用户意图，标题也由 `range` 自行推导。
 * - 重要级色板复用同目录 `eventTheme.ts`，与月/周/日网格视图同一套，避免视觉漂移。
 *
 * ── 数据 ────────────────────────────────────────────────────────────────
 * 直接用 `eventsByDay`（与月 / 周 / 日视图同源），按可见范围过滤 + 按日升序分组，
 * 组内按 `startAt` 升序；**不做归集、不做堆叠**（列表本身就是逐条展开的形态）。
 *
 * ── 四列 ────────────────────────────────────────────────────────────────
 * 时间（全天 / HH:mm）→ 新闻标题（重要级色点 + 标题）→ 国家（国旗 + 名称）
 *      → 重要度（色点 + 文案，复用 newsImportance 的 IMPORTANCE_LABELS）。
 *
 * ── 交互 ────────────────────────────────────────────────────────────────
 * 整行可点击 → 打开详情（`onSelectEvent`，必需）；同时上抛 `onEventClick`（可选），
 * 语义为「点了列表里这一条消息」，**不预设跳转行为**，具体动作由调用方决定。
 */

import { useMemo } from 'react';
import { cn } from '../../../utils/cn';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiLanguage } from '../../../i18n/uiText';
import type { LiveCalendarEventDef } from '../../../types/liveCalendar';
import { formatTime, toDateKey } from '../../../utils/format';
import { IMPORTANCE_LABELS } from '../../../constants/newsImportance';
import { eventThemeMap } from './eventTheme';

/** 四列网格模板：时间固定宽、标题自适应、国家 / 重要度固定宽 */
const LIST_GRID_COLS = 'grid-cols-[96px_1fr_140px_120px]';

/**
 * UI 语言 → Intl locale（日期组头的星期 / 日期、工具栏标题的本地化）。
 *
 * 本组件私有：工具栏已搬入本组件、标题由 `range` 自行推导，
 * 外部不再需要这套语言映射。
 */
function intlLocaleOf(language: UiLanguage): string {
    if (language === 'zh') return 'zh-CN';
    if (language === 'zh-Hant') return 'zh-TW';
    return 'en-US';
}

/**
 * 视图切换目标：三个 FullCalendar 网格视图 + List（自定义视图）。
 *
 * 保留 `'list'`：工具栏上已激活的 List 按钮仍可点击，点击会把可见范围重置为
 * 「当前 FC 可见范围所在周」，与切进 List 视图时的初始范围逻辑保持一致。
 */
export type LiveCalendarViewTarget =
    | 'dayGridMonth'
    | 'timeGridWeek'
    | 'timeGridDay'
    | 'list';

/** List 视图 props */
export interface LiveCalendarListViewProps {
    /** 按天归格的事件（key = `YYYY-MM-DD`），与月 / 周 / 日视图同源 */
    eventsByDay: Map<string, LiveCalendarEventDef[]>;
    /**
     * 可见日期范围（闭区间，含首尾两天）。
     * 与 `LiveCalendarRange` 结构一致；此处不直接引用该类型，
     * 是为了避免 `LiveCalendarListView` 反向依赖 `LiveCalendar.tsx` 造成循环引用。
     */
    range: { start: Date; end: Date };
    /** 点某条消息 → 打开该事件详情 */
    onSelectEvent: (event: LiveCalendarEventDef) => void;
    /**
     * 点击列表里某条消息的行点击回调（**可选**）。
     *
     * 语义是「用户点了这一条消息」，**不预设任何跳转行为** —— 具体做什么
     * （切视图 / 埋点 / 与外部联动）由调用方决定，因此只回传被点击的消息本身，
     * 不再回传一个「目标日期」（那会把「跳转」这个动作预设进回调契约里）。
     */
    onEventClick?: (event: LiveCalendarEventDef) => void;
    /**
     * 工具栏 prev / today / next：按 7 天平移可见范围。
     * **必填** —— 可见范围与「通知 Page 拉数」都由父级持有，本组件只上抛用户意图。
     */
    onNavigate: (dir: 'prev' | 'next' | 'today') => void;
    /**
     * 工具栏视图切换（月 / 周 / 日 / List）。
     * **必填** —— `viewType` 决定渲染 FC 还是本组件，视图状态必须由父级持有，
     * 本组件只上抛「用户想切到哪个视图」。
     */
    onViewChange: (view: LiveCalendarViewTarget) => void;
    /** 外层容器自定义类名（合并优先级最高，放在 cn() 最后） */
    className?: string;
}

/**
 * List 视图：按日期分组的**四列消息列表**。
 *
 * 详见文件头注释（数据来源 / 四列构成 / 交互语义 / 与 LiveCalendar 的边界）。
 */
export function LiveCalendarListView({
    eventsByDay,
    range,
    onSelectEvent,
    onEventClick,
    onNavigate,
    onViewChange,
    className,
}: LiveCalendarListViewProps) {
    const { t, language } = useUiLanguage();
    const locale = intlLocaleOf(language);

    // 按日分组：过滤可见范围 + 组内按 startAt 升序 + 天间按 dayKey 升序；**空天不渲染**
    //（避免整周无事件的日子堆出一串空 section）。
    const groups = useMemo(() => {
        const startKey = toDateKey(range.start);
        const endKey = toDateKey(range.end);
        const out: Array<{ dayKey: string; events: LiveCalendarEventDef[] }> = [];
        eventsByDay.forEach((events, dayKey) => {
            if (!events || events.length === 0) return;
            if (dayKey < startKey || dayKey > endKey) return;
            out.push({ dayKey, events: events.slice().sort((a, b) => a.startAt - b.startAt) });
        });
        out.sort((a, b) => a.dayKey.localeCompare(b.dayKey));
        return out;
    }, [eventsByDay, range]);

    // 工具栏标题：起始日 – 结束日（按 UI 语言本地化）。
    // 直接由 range 推导，父级只需持有状态，不必再单独传一份标题进来。
    const title = useMemo(() => {
        const fmt = (d: Date) =>
            new Intl.DateTimeFormat(locale, {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
            }).format(d);
        return `${fmt(range.start)} – ${fmt(range.end)}`;
    }, [range, locale]);

    return (
        <div className={cn('hrs-liveCalendar-listView flex flex-col', className)}>
            {/* ── 工具栏 ──────────────────────────────────────────────────
                List 不是 FC 视图，FC 被隐藏后其内置 toolbar 也一并消失，故由本组件自绘。
                刻意复用 FC 的 `.fc-toolbar` / `.fc-button-group` / `.fc-button` /
                `.fc-*-button` 结构，让 csscover 里那套 `[&_.fc-*]` 覆盖直接生效，
                视觉与月 / 周 / 日视图一致。
                ⚠ 工具栏必须渲染在空态之上：无消息时也要保留它，否则用户切进 List
                后既不能翻页、也切不回其它视图（死胡同）。 */}
            <div className="fc-toolbar fc-header-toolbar">
                <div className="fc-toolbar-chunk">
                    <div className="fc-button-group">
                        <button
                            type="button"
                            className="fc-button fc-button-primary fc-prev-button"
                            onClick={() => onNavigate('prev')}
                            aria-label={t('component.LiveCalendar.prevMonth')}
                        >
                            <span className="fc-icon fc-icon-chevron-left" />
                        </button>
                        <button
                            type="button"
                            className="fc-button fc-button-primary fc-today-button"
                            onClick={() => onNavigate('today')}
                        >
                            {t('common.datetime.today')}
                        </button>
                        <button
                            type="button"
                            className="fc-button fc-button-primary fc-next-button"
                            onClick={() => onNavigate('next')}
                            aria-label={t('component.LiveCalendar.nextMonth')}
                        >
                            <span className="fc-icon fc-icon-chevron-right" />
                        </button>
                    </div>
                </div>
                <div className="fc-toolbar-chunk">
                    <h2 className="fc-toolbar-title">{title}</h2>
                </div>
                <div className="fc-toolbar-chunk">
                    <button
                        type="button"
                        className="fc-button fc-button-primary fc-dayGridMonth-button"
                        onClick={() => onViewChange('dayGridMonth')}
                    >
                        {t('common.datetime.month')}
                    </button>
                    <button
                        type="button"
                        className="fc-button fc-button-primary fc-timeGridWeek-button"
                        onClick={() => onViewChange('timeGridWeek')}
                    >
                        {t('common.datetime.week')}
                    </button>
                    <button
                        type="button"
                        className="fc-button fc-button-primary fc-timeGridDay-button"
                        onClick={() => onViewChange('timeGridDay')}
                    >
                        {t('common.datetime.day')}
                    </button>
                    {/* 当前即 List 视图：FC 不会为非 FC 视图维护 active 态，故硬编码高亮 */}
                    <button
                        type="button"
                        className="fc-button fc-button-primary fc-list-button fc-button-active"
                        onClick={() => onViewChange('list')}
                    >
                        {t('common.datetime.list')}
                    </button>
                </div>
            </div>

            {/* 空态：可见范围内一条消息都没有（区别于「某天为空」，后者是跳过该天不渲染） */}
            {groups.length === 0 ? (
                <div className="flex items-center justify-center px-4 py-10 text-sm text-muted-foreground">
                    {t('component.LiveCalendar.empty')}
                </div>
            ) : null}

            {groups.map((group) => {
                const date = new Date(`${group.dayKey}T00:00:00`);
                const weekday = new Intl.DateTimeFormat(locale, { weekday: 'long' }).format(date);
                const dateLabel = new Intl.DateTimeFormat(locale, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                }).format(date);
                return (
                    <section key={group.dayKey} className="border-b border-border last:border-b-0">
                        {/* 日期组头：左「星期」、右「日期」；sticky 便于长列表滚动时定位 */}
                        <header className="grid grid-cols-[1fr_auto] items-baseline gap-3 bg-muted/40 px-4 py-2 text-sm">
                            <span className="text-md font-semibold text-foreground">{weekday}</span>
                            <span className="text-xs font-normal text-muted-foreground">
                                {dateLabel}
                            </span>
                        </header>

                        {/* 列头（四列） */}
                        <div
                            className={cn(
                                'grid items-center gap-2 bg-muted/20 px-4 py-1.5 text-xs font-medium text-muted-foreground',
                                LIST_GRID_COLS,
                            )}
                        >
                            <span>{t('component.LiveCalendar.list.columns.time')}</span>
                            <span>{t('component.LiveCalendar.list.columns.title')}</span>
                            <span>{t('component.LiveCalendar.country')}</span>
                            <span>{t('component.LiveCalendar.importance')}</span>
                        </div>

                        {/* 消息行：整行可点击 → onSelectEvent（详情定位）+ onEventClick（可选扩展） */}
                        <ul>
                            {group.events.map((event) => {
                                const theme = eventThemeMap(event.importance);
                                return (
                                    <li key={event.key}>
                                        <button
                                            type="button"
                                            title={event.title}
                                            onClick={() => {
                                                onSelectEvent(event);
                                                onEventClick?.(event);
                                            }}
                                            className={cn(
                                                'grid w-full items-center gap-2 px-4 py-2 text-left text-xs transition-colors',
                                                'hover:bg-hover',
                                                'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
                                                LIST_GRID_COLS,
                                            )}
                                        >
                                            {/* 时间：全天事件显示「全天」，否则 HH:mm */}
                                            <span className="tabular-nums text-sm text-foreground-soft">
                                                {event.isAllDay
                                                    ? t('component.LiveCalendar.allDay')
                                                    : formatTime(event.startAt)}
                                            </span>

                                            {/* 新闻标题：重要级色点 + 标题（过长截断，hover 显示完整 title） */}
                                            <span className="flex min-w-0 items-center gap-1.5">
                                               <span aria-hidden className={cn('shrink-0 text-lg font-bold leading-none', theme.text)}>·</span>
                                                <span className="truncate text-sm leading-tight text-foreground">
                                                    {event.title}
                                                </span>
                                            </span>

                                            {/* 国家：国旗 + 名称 */}
                                            <span className="flex min-w-0 items-center gap-1.5 text-sm text-foreground-soft">
                                                {event.flagUri ? (
                                                    <img
                                                        src={event.flagUri}
                                                        alt=""
                                                        className="h-3 w-4 shrink-0 object-cover"
                                                    />
                                                ) : null}
                                                <span className="truncate">{event.country}</span>
                                            </span>

                                            {/* 重要度：色点 + 文案（复用 newsImportance 标签） */}
                                            <span
                                                className={cn(
                                                    'flex min-w-0 items-center gap-1.5',
                                                    theme.text,
                                                )}
                                            >
                                               <span aria-hidden className={cn('shrink-0 text-lg font-bold leading-none', theme.text)}>·</span>
                                                <span className="truncate text-sm ">
                                                    {IMPORTANCE_LABELS[event.importance] || '—'}
                                                </span>
                                            </span>
                                        </button>
                                    </li>
                                );
                            })}
                        </ul>
                    </section>
                );
            })}
        </div>
    );
}
