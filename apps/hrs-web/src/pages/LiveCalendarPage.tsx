/**
 * 消息日历（Live Calendar）
 *
 * 对齐华尔街见闻财经日历页的布局：
 *   顶部标题 + 刷新 -> 单张抬升卡片（工具栏 + 分类 Tab + 月历网格）
 *   -> 选中日详情列表（始终置于日历下方，多列网格）
 *
 * 关键设计：
 * 1. **分类 Tab 由后端驱动**：宏观 / 财报 / 新股 / 活动 / 全部，label 经 i18n 映射；
 * 2. **日历网格复用 FullCalendar 封装**（LiveCalendarGrid），dayMaxEvents 折叠 + Breezy 风格变量层；
 * 3. **点日期空白看该日全部、点单条看该事件详情**，详情列表放在日历下方（不再是右侧栏）；
 * 4. 低频数据不轮询，仅提供手动刷新。
 *
 * 接口契约与选型理由详见 docs/Live-calendar.md。
 */

import { useMemo, useState } from 'react';
import { HrsButton, Loading, TabNav, type TabNavItem } from '../components';
import { LiveCalendarGrid } from '../components/common/LiveCalendarGrid';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import {
  useLiveCalendarCountries,
  useLiveCalendarMonth,
  useLiveCalendarTabs,
} from '../hooks/useLiveCalendar';
import type { CalendarTabValue, LiveCalendarEventDef } from '../types/liveCalendar';
import type { UiTextKey } from '../i18n/uiText';
import { IMPORTANCE_COLORS, IMPORTANCE_LABELS } from '../constants/newsImportance';

/** 月份对象（1~12） */
interface MonthCursor {
  year: number;
  month: number;
}

/** 当前年月 */
function currentMonth(): MonthCursor {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

const LiveCalendarPage: React.FC = () => {
  const { t } = useUiLanguage();
  const { tabs } = useLiveCalendarTabs();
  const { degraded: countriesDegraded } = useLiveCalendarCountries();

  const [cursor, setCursor] = useState<MonthCursor>(currentMonth);
  const [activeTab, setActiveTab] = useState<CalendarTabValue>('all');
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const { eventsByDay, loading, refreshing, degraded, error, refresh } = useLiveCalendarMonth(
    cursor.year,
    cursor.month,
    { tab: activeTab }
  );

  // Tab items：value 来自后端，label 经 i18n 映射
  const tabItems = useMemo<TabNavItem<CalendarTabValue>[]>(
    () =>
      tabs.map((tab) => ({
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
    <div className="mx-auto w-full">
      <header className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{t('liveCalendar.title')}</h1>
          <p className="mt-1 text-xs text-muted-text">{t('liveCalendar.subtitle')}</p>
        </div>
        <HrsButton
          variant="secondary"
          size="sm"
          isLoading={refreshing}
          loadingText={t('liveCalendar.refreshing')}
          onClick={() => void refresh()}
        >
          {t('liveCalendar.refresh')}
        </HrsButton>
      </header>

      {(degraded || countriesDegraded) && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-300">
          {t('liveCalendar.degradedTip')}
        </div>
      )}

      {/* 日历 + 详情：垂直堆叠（详情始终在日历下方） */}
      <div className="flex flex-col gap-4">
        {/* 日历卡片：抬升表面 + 柔和阴影 */}
        <div className="flex min-h-[520px] flex-col overflow-hidden rounded-lg border border-border-dim bg-elevated shadow-soft-card">
          {/* 卡片头部：仅保留分类 Tab。
              日期导航（prev/today/next）与视图切换（月/周/日）已由 LiveCalendarGrid 内置工具栏接管，
              不再在本层重复实现，避免两套控件打架。 */}
          <div className="flex flex-col gap-2 border-b border-border-dim px-4 py-3">
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

          {/* 日历主体：min-h 兜底 + flex-1 grow。LiveCalendarGrid 用 aspectRatio 自撑高度，
              不依赖此处父级确定高度。 */}
          <div className="min-h-[480px] flex-1 p-3">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <Loading label={t('liveCalendar.loading')} />
              </div>
            ) : error ? (
              <div className="flex h-full items-center justify-center text-sm text-secondary-text">
                {error}
              </div>
            ) : (
              <LiveCalendarGrid
                // 初始日期：把 Page 的 cursor（year/month）转成 YYYY-MM-DD 喂给 FullCalendar
                initialDate={`${cursor.year}-${String(cursor.month).padStart(2, '0')}-01`}
                // 视图/导航变化 → Page 更新 cursor → 重新拉对应月份数据
                onRangeChange={setCursor}
                eventsByDay={eventsByDay}
                onSelectDay={setSelectedDay}
                onSelectEvent={(event) => {
                  setSelectedDay(dayKeyOf(event));
                }}
              />
            )}
          </div>
        </div>

        {/* 选中日详情面板：始终在日历下方（Breezy 风格同色卡片） */}
        <div className="rounded-lg border border-border-dim bg-elevated p-4 shadow-soft-card">
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
        </div>
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