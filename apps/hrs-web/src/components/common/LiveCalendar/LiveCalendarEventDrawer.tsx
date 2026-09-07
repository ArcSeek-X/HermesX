/**
 * 消息日历 · 单条事件详情抽屉
 * ------------------------------------------------------------
 * 文件作用：
 *   展示某条日历消息的完整详情，供月 / 周 / 日 / List 各视图点击消息时打开。
 *
 * 布局（三段式）：
 *   1. **Header**：时间（年月日 + 时分） + 主标题 `shortTitle`；
 *   2. **Body**：国家徽章（国旗 + 名称 + 货币）+ 分类徽章 → 副标题 `title`
 *              → 正文 `summary`（可滚动）→ 经济数据（仅 `FD` 且有值）；
 *   3. **Footer**：重要度（左，色点 + 文案） + 来源（右，外链）。
 *
 * 设计要点：
 *   - 底座用 `HrsDrawer`（components/basic/Drawer，HeroUI 二次封装），自带焦点陷阱、
 *     Esc 关闭、遮罩点击关闭、拖拽关闭与退场动画，无需重复实现；
 *   - **只展示，不改视图**：打开抽屉时日历停在原视图，语义与「点日期格 / 日期标题
 *     → 切日视图看当天全部」明确区分（后者由 LiveCalendar 内部 handleDateClick 负责）；
 *   - 关闭节奏与项目现有 `ReportMarkdownDrawer` 一致：先置 isOpen=false 播退场动画，
 *     再延迟卸载（300ms），避免内容在动画途中被抽掉；
 *   - 货币符号来自国家字典（由 Page 传入，避免重复请求）；字典未就绪时降级为只显示国家名。
 * ------------------------------------------------------------
 */
import type React from 'react';
import { useCallback, useState } from 'react';
import { HrsDrawer } from '../../basic/Drawer';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { IMPORTANCE_LABELS } from '../../../constants/newsImportance';
import { eventThemeMap } from './eventTheme';
import type { CalendarCountryDef, LiveCalendarEventDef } from '../../../types/liveCalendar';
import { cn } from '../../../utils/cn';
import { formatDate, formatDateTime } from '../../../utils/format';

/** 经济数据单项（公布 / 预期 / 前值） */
function MetricItem({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex flex-col gap-0.5">
            <span className="text-xxs text-muted-foreground">{label}</span>
            <span className="text-sm font-medium tabular-nums text-foreground">
                {value || '—'}
            </span>
        </div>
    );
}

/**
 * 单条事件详情抽屉
 *
 * @param props.event - 要展示的事件（非空，由父组件保证）
 * @param props.countries - 国家字典，按 `countryId` 取货币符号（未就绪时降级）
 * @param props.onClose - 关闭回调（父组件据此清空选中事件并卸载抽屉）
 */
export const LiveCalendarEventDrawer: React.FC<{
    event: LiveCalendarEventDef;
    countries: CalendarCountryDef[];
    onClose: () => void;
}> = ({ event, countries, onClose }) => {
    const [isOpen, setIsOpen] = useState(true);
    const { t } = useUiLanguage();

    // 先播退场动画再卸载，与 ReportMarkdownDrawer 保持同一节奏
    const handleClose = useCallback(() => {
        setIsOpen(false);
        setTimeout(onClose, 300);
    }, [onClose]);

    // 头部时间：非全天 → 「年月日 时分」（formatDateTime）；全天无具体时刻 → 「年月日 全天」。
    // 两者均直接吃秒级时间戳，内部自动 ×1000，无需再 new Date(... * 1000)。
    const timeLabel = event.isAllDay
        ? `${formatDate(event.startAt)} ${t('component.LiveCalendar.allDay')}`
        : formatDateTime(event.startAt);

    const currency = countries.find((item) => item.countryId === event.countryId)?.currency;
    // 重要度色板：与月/周/日日历和 List 视图共用 eventThemeMap，避免两套色板视觉漂移
    const theme = eventThemeMap(event.importance);
    const importanceLabel = IMPORTANCE_LABELS[event.importance];
    // 经济数据仅「经济数据指标」(FD) 且有值时展示，财经大事件 (FE) 无此项
    const hasEconomicData = event.calendarType === 'FD' && !!(event.actual || event.forecast || event.previous);


    console.log('event', event);

    return (
        <HrsDrawer
            isOpen={isOpen}
            onClose={handleClose}
            placement="right"
            size="md"
            // ⚠ 三段容器样式统一走 *ClassName：HrsDrawer 分拣子元素时只取 children，
            // 会丢弃 <HrsDrawer.Body className="..."> 上的 className，写在子元素上不生效。
            headerClassName="items-start"
            bodyClassName="flex flex-col gap-3 overflow-y-auto"
        >
            {/* ── 头部：时间（年月日 + 时分） + 主标题（shortTitle） */}
            <HrsDrawer.Header>
                {/* min-w-0：Header 是 flex 容器，div 作为 flex item 默认 min-width:auto 不收缩，
                    长标题会溢出而非换行；放开后标题可在抽屉宽度内正常折行 */}
                <div className="flex min-w-0 flex-col gap-1">
                    <span className="text-xs tabular-nums text-foreground-soft">
                        {timeLabel}
                    </span>
                    {/* Heading 供 HeroUI 做 aria-labelledby，主标题语义与无障碍都落在这里 */}
                    <HrsDrawer.Heading className="min-w-0 whitespace-normal break-words text-md font-semibold leading-snug text-foreground">
                        {event.shortTitle}
                    </HrsDrawer.Heading>
                </div>
            </HrsDrawer.Header>

            <HrsDrawer.Body>
                {/* 国家：国旗 + 名称 + 货币（字典未就绪时降级为仅名称）；右侧为分类徽章 */}
                <div className="flex flex-wrap items-center gap-3">
                    <span className="flex items-center gap-1.5 text-sm text-foreground">
                        {event.flagUri ? (
                            <img
                                src={event.flagUri}
                                alt="countryFlag"
                                className="h-3 w-4 shrink-0 object-cover"
                            />
                        ) : null}
                        <span>
                            {event.country}
                            {currency ? ` · ${currency}` : ''}
                        </span>
                    </span>
                    <span className="rounded-full bg-muted px-1.5 py-0.5 text-xxs text-foreground-glow">
                        {t(
                            event.calendarType === 'FD'
                                ? 'component.LiveCalendar.calendarType.FD'
                                : 'component.LiveCalendar.calendarType.FE',
                        )}
                    </span>
                </div>

                {/* 副标题：title（与 shortTitle 相同时不重复渲染） */}
                {event.title && event.title !== event.shortTitle ? (
                    <p className="text-sm leading-snug text-foreground-glow">{event.title}</p>
                ) : null}

                {/* 正文：summary；上游未提供前瞻（foresight）时为空，给出占位提示 */}
                {event.summary ? (
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                        {event.summary}
                    </p>
                ) : (
                    <p className="text-sm text-foreground-glow">{t('component.LiveCalendar.drawer.noSummary')}</p>
                )}

                {/* 经济数据：actual / forecast / previous（仅 FD 且有值） */}
                {hasEconomicData ? (
                    <div className="grid grid-cols-3 gap-2 rounded-md border border-border-subtle bg-elevated p-2.5">
                        <MetricItem
                            label={t('component.LiveCalendar.drawer.actual')}
                            value={event.actual}
                        />
                        <MetricItem
                            label={t('component.LiveCalendar.drawer.forecast')}
                            value={event.forecast}
                        />
                        <MetricItem
                            label={t('component.LiveCalendar.drawer.previous')}
                            value={event.previous}
                        />
                    </div>
                ) : null}
            </HrsDrawer.Body>

            {/* ── 底部：重要度（左） + 来源（右，外链） */}
            <HrsDrawer.Footer>
                <div className="flex w-full items-center justify-between gap-3 text-xs">
                    <span className="flex min-w-0 items-center gap-1.5">
                        <span className="shrink-0 text-muted-foreground">
                            {t('component.LiveCalendar.importance')}
                        </span>
                        <span
                            className={cn(
                                'flex min-w-0 items-center gap-1 font-medium',
                                theme.text,
                            )}
                        >
                            <span aria-hidden className="text-lg font-bold leading-none">
                                ·
                            </span>
                            <span className="truncate">{importanceLabel || '—'}</span>
                        </span>
                    </span>
                    {event.sourceUri ? (
                        <a
                            href={event.sourceUri}
                            target="_blank"
                            rel="noreferrer"
                            className="flex shrink-0 items-center gap-1 text-primary hover:underline"
                        >
                            <span className="text-muted-foreground">
                                {t('component.LiveCalendar.drawer.source')}
                            </span>
                            {t('component.LiveCalendar.drawer.sourceName')} →
                        </a>
                    ) : null}
                </div>
            </HrsDrawer.Footer>
        </HrsDrawer>
    );
};
