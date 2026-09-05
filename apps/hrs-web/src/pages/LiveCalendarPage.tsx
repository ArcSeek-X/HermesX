/**
 * 消息日历（Live Calendar）
 *
 * 对齐华尔街见闻财经日历页的布局：
 *   顶部标题 + 刷新 -> 单张抬升卡片（工具栏 + 分类 Tab + 月历网格）
 *   -> 选中日详情列表（始终置于日历下方，多列网格）
 *
 * 关键设计：
 * 1. **分类 Tab 由后端驱动**：全部 / 宏观 / 财报 / 新股 / 活动（按后端 `order` 升序展示），label 经 i18n 映射；
 * 2. **日历网格复用 FullCalendar 封装**（LiveCalendar），dayMaxEvents 折叠 + Breezy 风格变量层；
 * 3. **月视图下点事件标题或日期格 → 切换到日视图并展示当日全部事件**（LiveCalendar 内部
 *    通过 CalendarApi.changeView 完成，数据仍复用当月拉取结果，不触发重新请求）；
 *    日/周视图下点击仍定位到日历下方详情面板（不再是右侧栏）；
 * 4. 低频数据不轮询，仅提供手动刷新。
 *
 * 接口契约与选型理由详见 docs/Live-calendar.md。
 */

import { useCallback, useMemo, useState } from 'react';
import { HrsButton, Loading, AnimCard, TabNav, LiveCalendar, type LiveCalendarRange, type TabNavItem } from '../components';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import type { UiTextKey } from '../i18n/uiText';
import type { CalendarTabValue, LiveCalendarEventDef } from '../types/liveCalendar';
import { IMPORTANCE_COLORS, IMPORTANCE_LABELS } from '../constants/newsImportance';
import {
  monthGridRange,
  monthsInRange,
  useLiveCalendarCountries,
  useLiveCalendarMonths,
  useLiveCalendarTabs,
} from '../hooks/useLiveCalendar';



/** 序列化月份集合为稳定 key（供范围变化时比较，避免相等范围重复触发拉取） */
function monthsKeyOf(range: LiveCalendarRange): string {
  return monthsInRange(range)
    .map((m) => `${m.year}-${m.month}`)
    .join('|');
}

const LiveCalendarPage: React.FC = () => {
  const { t } = useUiLanguage();
  const { tabs } = useLiveCalendarTabs();
  const { degraded: countriesDegraded } = useLiveCalendarCountries();

  // 当前可见日期范围（由 LiveCalendar 的 datesSet 驱动）。初始化为本月月视图范围。
  const [range, setRange] = useState<LiveCalendarRange>(() => {
    const now = new Date();
    return monthGridRange(now.getFullYear(), now.getMonth() + 1);
  });
  // 默认选中「全部」（后端 Tab 列表的首项）
  const [activeTab, setActiveTab] = useState<CalendarTabValue>('all');
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  // 可见范围覆盖的所有月份（后端按月取数，跨月周次/月视图填充格需多月合并）
  const months = useMemo(() => monthsInRange(range), [range]);

  // 范围变化：月份集合相同时保持原 state 引用，避免无谓的重新拉取
  const handleRangeChange = useCallback((next: LiveCalendarRange) => {
    const nextKey = monthsKeyOf(next);
    setRange((prev) => (monthsKeyOf(prev) === nextKey ? prev : next));
  }, []);

  const { eventsByDay, loading, isRefreshing, degraded, error, refresh } =
    useLiveCalendarMonths(months, { tab: activeTab });

  // Tab items：value 来自后端，label 经 i18n 映射；展示顺序按后端 order 升序 （全部 → 宏观 → 财报 → 新股 → 活动）
  const tabItems = useMemo<TabNavItem<CalendarTabValue>[]>(
    () =>
      [...tabs]
        .sort((a, b) => a.order - b.order)
        .map((tab) => ({
          value: tab.value,
          label: t(`liveCalendar.tabs.${tab.value}` as UiTextKey),
        })),
    [tabs, t]
  );

  // 选中日的全部事件
  const selectedEvents = useMemo(
    () => (selectedDay ? eventsByDay.get(selectedDay) ?? [] : []),
    [selectedDay, eventsByDay]
  );

  const emptyText =
    activeTab !== 'all' ? t('liveCalendar.emptyTab') : t('liveCalendar.empty');

  return (
    <div className="mx-auto w-full pr-1">
      <header className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{t('liveCalendar.title')}</h1>
          <p className="mt-1 text-xs text-muted-text">{t('liveCalendar.subtitle')}</p>
        </div>
        <HrsButton
          size="sm"
          isLoading={isRefreshing}
          loadingText={t('liveCalendar.refreshing')}
          onClick={() => void refresh()}
        >
          {t('liveCalendar.refresh')}
        </HrsButton>
      </header>

      {/* 数据源暂不可用，当前展示本地缓存数据 */}
      {(degraded || countriesDegraded) && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-300">
          {t('liveCalendar.degradedTip')}
        </div>
      )}

      {/* 日历 + 详情：垂直堆叠（详情始终在日历下方） */}
      <div className="flex flex-col gap-4">
        {/* 日历卡片：AnimCard 提供圆角/边框/背景/入场动画 */}
        <AnimCard className="flex flex-col">
          {/* 卡片头部：仅保留分类 Tab。
              日期导航（prev/today/next）与视图切换（月/周/日）已由 LiveCalendar 内置工具栏接管，
              不再在本层重复实现，避免两套控件打架。 */}
          <div className="flex flex-col gap-2 px-4 py-3">
            {tabItems.length > 0 && (
              <TabNav
                items={tabItems}
                value={activeTab}
                onChange={(value) => {
                  setActiveTab(value);
                  setSelectedDay(null);
                }}
                variant="secondary"
                ariaLabel={t('liveCalendar.title')}
                className="justify-start"
              />
            )}
          </div>

          {/* 日历主体：不限制高度，LiveCalendar 按内容自由展开（contentHeight="auto"）。
              仅加载/错误兜底态用 min-h 占位，避免空白塌陷。 */}
          <div className="p-3">
            {loading ? (
              <div className="flex min-h-[480px] items-center justify-center">
                <Loading label={t('liveCalendar.loading')} />
              </div>
            ) : error ? (
              <div className="flex min-h-[480px] items-center justify-center text-sm text-secondary-text">
                {error}
              </div>
            ) : (
              <LiveCalendar
                // 视图/导航变化 → Page 更新可见范围 → 拉取覆盖月份数据
                onRangeChange={handleRangeChange}
                eventsByDay={eventsByDay}
                onSelectDay={setSelectedDay}
                onSelectEvent={(event) => {
                  setSelectedDay(dayKeyOf(event));
                }}
              />
            )}
          </div>
        </AnimCard>

        {/* 选中日详情面板：始终在日历下方 */}
        <AnimCard className="p-4">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-foreground">
              {selectedDay ?? '—'}
            </h2>
            {selectedEvents.length > 0 && (
              <span className="text-xxs text-muted-text">
                {t('liveCalendar.eventsCount', { count: selectedEvents.length })}
              </span>
            )}
          </div>
          {selectedEvents.length === 0 ? (
            <p className="text-xs text-muted-text">
              {selectedDay ? emptyText : t('liveCalendar.selectHint')}
            </p>
          ) : (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {selectedEvents.map((event) => (
                <li key={event.key}>
                  <EventCard event={event} />
                </li>
              ))}
            </ul>
          )}
        </AnimCard>
      </div>
    </div>
  );
};

/** 事件 → 本地时区 YYYY-MM-DD（供详情面板定位） */
function dayKeyOf(event: LiveCalendarEventDef): string {
  const d = new Date(event.startAt * 1000);
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

/** 单条事件卡片（详情面板内） */
function EventCard({ event }: { event: LiveCalendarEventDef }) {
  const { t } = useUiLanguage();
  const color = IMPORTANCE_COLORS[event.importance];
  const label = IMPORTANCE_LABELS[event.importance];
  return (
    <div className="rounded-md border border-border-subtle bg-elevated px-3 py-2">
      <div className="flex items-center gap-2">
        {event.isAllDay ? (
          <span className="text-xxs text-muted-text">{t('liveCalendar.allDay')}</span>
        ) : (
          <span className="text-xxs text-muted-text">{formatTime(event.startAt)}</span>
        )}
        {label ? (
          <span className={`text-xxs ${color}`}>{label}</span>
        ) : null}
      </div>
      <p className="mt-1 text-sm text-foreground">{event.title}</p>
      {event.summary ? (
        <p className="mt-1 line-clamp-3 text-xs text-secondary-text">{event.summary}</p>
      ) : null}
    </div>
  );
}

/** 秒级时间戳 → 本地 HH:mm */
function formatTime(startAt: number): string {
  const d = new Date(startAt * 1000);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export default LiveCalendarPage;
