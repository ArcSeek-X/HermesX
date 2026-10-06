/**
 * @file LiveCalendarPage.tsx
 * @description 消息日历页面：承接分类 Tab、筛选、手动刷新和选中日详情面板，
 * 并把覆盖月份的数据结果传给 `LiveCalendar` 渲染四视图。
 * @author Lensgcx (GaoCangxiong)
 *
 * 对齐华尔街见闻财经日历页的布局：
 *   顶部标题 + 刷新 -> 单张抬升卡片（工具栏 + 分类 Tab + 月历网格）
 *   -> 选中日详情列表（始终置于日历下方，多列网格）
 *
 * 关键设计：
 * 1. **分类 Tab 由后端驱动**：全部 / 宏观 / 财报 / 新股 / 活动（按后端 `order` 升序展示），label 经 i18n 映射；
 * 2. **日历网格复用 FullCalendar 封装**（LiveCalendar），dayMaxEvents 折叠 + Breezy 风格变量层；
 * 3. **点事件 → 由 LiveCalendar 内部打开详情抽屉（LiveCalendarEventDrawer）看单条内容；点日期格 / 日期标题
 *    → 切换到日视图看当天全部**（切视图由 LiveCalendar 内部 CalendarApi.changeView 完成，
 *    数据仍复用当月拉取结果，不触发重新请求）；
 * 4. 低频数据不轮询，仅提供手动刷新。
 *
 * 接口契约与选型理由详见 docs/Live-calendar.md。
 */

import { cn } from '@utils/cn';
import { startTransition, useCallback, useMemo, useState } from 'react';
import { ChevronDown, Filter } from 'lucide-react';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import type { UiTextKey } from '../i18n/uiText';
import type { CalendarTabValue, LiveCalendarEventDef } from '../types/liveCalendar';
import { IMPORTANCE_COLORS, IMPORTANCE_LABELS } from '../constants/newsImportance';
import {
  HrsButton,
  InlineToast,
  Loading,
  AnimCard,
  TabNav,
  LiveCalendar,
  LiveCalendarFilterPanel,
  countActiveFilters,
  createDefaultLiveCalendarFilter,
  DEFAULT_LIVE_CALENDAR_FILTER,
  type LiveCalendarFilterValue,
  type LiveCalendarRangeRequest,
  type LiveCalendarRange,
  type TabNavItem,
} from '@components';
import { PageHeader } from '@components/page-layout';
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

function createInitialRange(): LiveCalendarRange {
  const now = new Date();
  return monthGridRange(now.getFullYear(), now.getMonth() + 1);
}

const LiveCalendarPage: React.FC = () => {
  const { t } = useUiLanguage();
  const { tabs } = useLiveCalendarTabs();
  const { items: countries, degraded: countriesDegraded } = useLiveCalendarCountries();

  /** 当前可见日期范围，由 `LiveCalendar` 的 `onRangeRequest` 驱动。 */
  const [range, setRange] = useState<LiveCalendarRange>(createInitialRange);
  /** 默认选中「全部」（后端 Tab 列表的首项）。 */
  const [activeTab, setActiveTab] = useState<CalendarTabValue>('all');
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  /** 已生效的筛选条件；仅在点“确认”后更新，避免输入过程中触发重算。 */
  const [filterValue, setFilterValue] = useState<LiveCalendarFilterValue>(
    DEFAULT_LIVE_CALENDAR_FILTER,
  );
  const [filterOpen, setFilterOpen] = useState(false);
  const activeFilterCount = useMemo(() => countActiveFilters(filterValue), [filterValue]);
  const months = useMemo(() => monthsInRange(range), [range]);
  const calendarQuery = useMemo(
    () => ({
      tab: activeTab,
      importance: filterValue.importance,
      calendarType: filterValue.calendarType === 'all' ? undefined : filterValue.calendarType,
      countryId: filterValue.countryId || undefined,
      keyword: filterValue.keyword,
    }),
    [activeTab, filterValue]
  );

  /** 月份集合未变化时保持原 state 引用，避免重复触发取数。 */
  const handleRangeChange = useCallback((next: LiveCalendarRange) => {
    const nextKey = monthsKeyOf(next);
    startTransition(() => {
      setRange((prev) => (monthsKeyOf(prev) === nextKey ? prev : next));
    });
  }, []);

  const {
    eventsByDay,
    resolvedMonthsKey,
    loading,
    isRefreshing,
    degraded,
    error,
    refresh,
  } = useLiveCalendarMonths(months, calendarQuery);

  const handleCalendarRangeRequest = useCallback(
    ({ range: nextRange }: LiveCalendarRangeRequest) => {
      handleRangeChange(nextRange);
    },
    [handleRangeChange]
  );

  const handleTabChange = useCallback((value: CalendarTabValue) => {
    setActiveTab(value);
    setSelectedDay(null);
  }, []);

  const handleFilterToggle = useCallback(() => {
    setFilterOpen((prev) => !prev);
  }, []);

  const handleFilterReset = useCallback(() => {
    setFilterValue(createDefaultLiveCalendarFilter());
  }, []);

  const handleRefresh = useCallback(() => {
    void refresh();
  }, [refresh]);

  /** Tab value 来自后端，label 由页面做 i18n 映射。 */
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

  const selectedEvents = useMemo(
    () => (selectedDay ? eventsByDay.get(selectedDay) ?? [] : []),
    [selectedDay, eventsByDay]
  );

  const emptyText =
    activeTab !== 'all'
      ? t('liveCalendar.emptyTab')
      : activeFilterCount > 0
        ? t('component.LiveCalendar.emptyFilter')
        : t('component.LiveCalendar.empty');

  return (
    <div className="w-full space-y-3">
      <PageHeader title={t('liveCalendar.title')} description={t('liveCalendar.subtitle')}/>

      {/* 数据源暂不可用，当前展示本地缓存数据 */}
      {(degraded || countriesDegraded) && (
        <InlineToast
          variant="warning"
          className="mb-3"
          content={{
            title: t('liveCalendar.degradedTip.title'),
            message: t('liveCalendar.degradedTip.message'),
            rawMessage: t('liveCalendar.degradedTip.message'),
            category: 'unknown',
          }}
        />
      )}

      {/* 日历 + 详情：垂直堆叠（详情始终在日历下方） */}
      <div className="flex flex-col gap-4">
        {/* 日历卡片：AnimCard 提供圆角/边框/背景/入场动画 */}
        <AnimCard className="flex flex-col">
          {/* 卡片头部：分类 Tab + 筛选（按钮在 Tab 行右侧、刷新按钮左边，区域在 Tab 行下方）。
              日期导航（prev/today/next）与视图切换（月/周/日）已由 LiveCalendar 内置工具栏接管，
              不再在本层重复实现，避免两套控件打架。 */}
          <div className="flex flex-col px-4 py-3">
            {tabItems.length > 0 && (
              <TabNav
                items={tabItems}
                value={activeTab}
                onChange={handleTabChange}
                variant="secondary"
                ariaLabel={t('liveCalendar.title')}
                className="justify-between"
                rightSlot={
                  <div className="flex items-center gap-2">
                    {/* 筛选按钮：漏斗图标 + 生效条件角标 + 展开箭头 */}
                    <HrsButton
                      size="sm"
                      variant={activeFilterCount > 0 || filterOpen ? 'primary-soft' : 'outline'}
                      onClick={handleFilterToggle}
                      aria-expanded={filterOpen}
                      aria-controls="live-calendar-filter-panel"
                    >
                      <Filter aria-hidden className="h-3.5 w-3.5" />
                      <span>{t('component.LiveCalendar.filter.button')}</span>
                      {activeFilterCount > 0 ? (
                        <span className="ml-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-xxs font-semibold text-primary-foreground">
                          {activeFilterCount}
                        </span>
                      ) : null}
                      <ChevronDown
                        aria-hidden
                        className={cn(
                          'h-3.5 w-3.5 transition-transform duration-200',
                          filterOpen && 'rotate-180',
                        )}
                      />
                    </HrsButton>
                    <HrsButton
                      size="sm"
                      isLoading={isRefreshing}
                      loadingText={t('liveCalendar.refreshing')}
                      onClick={handleRefresh}
                    >
                      {t('liveCalendar.refresh')}
                    </HrsButton>
                  </div>
                }
              />
            )}

            {/* 筛选区域：收起时高度 0，展开时把日历整体向下挤压 */}
            <LiveCalendarFilterPanel
              open={filterOpen}
              value={filterValue}
              countries={countries}
              onApply={setFilterValue}
              onReset={handleFilterReset}
            />
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
                dataReadyKey={resolvedMonthsKey}
                // 视图/导航变化 → Page 更新可见范围 → 拉取覆盖月份数据
                onRangeRequest={handleCalendarRangeRequest}
                eventsMap={eventsByDay}
                //onSelectDay后续可删除
                onSelectDay={setSelectedDay}
                // 国家字典透传给 LiveCalendar：详情抽屉用它渲染国旗 / 货币 / 国家名
                countries={countries}
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

/** 单条事件卡片（详情面板内） */
function EventCard({ event }: { event: LiveCalendarEventDef }) {
  const { t } = useUiLanguage();
  const color = IMPORTANCE_COLORS[event.importance];
  const label = IMPORTANCE_LABELS[event.importance];

  return (
    <div className="rounded-md border border-border-subtle bg-elevated px-3 py-2">
      <div className="flex items-center gap-2">
        {event.isAllDay ? (
          <span className="text-xxs text-muted-text">{t('component.LiveCalendar.allDay')}</span>
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
