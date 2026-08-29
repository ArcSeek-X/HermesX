/**
 * 实时财经快讯中心（Live News）
 *
 * 对齐华尔街见闻 7x24 快讯页的布局：
 *   顶部 Tab 频道 -> 工具条（搜索 / 只看重要的 / 日期 / 刷新）-> 按日期分组的快讯卡片
 *
 * 关键设计：
 * 1. **Tab 完全由后端驱动**：前端不硬编码 8 个频道。官方源不可用降级到 NewsNow 时，
 *    后端只返回「要闻」，页面自动收敛为单 Tab 并隐藏「只看重要的」开关
 *    （降级源没有重要级字段，勾选后必然为空）。
 * 2. **重要级**：来自上游 score，重要条目的左侧竖线用主色、并带「重要」标签。
 * 3. **空态区分**：科技频道实测重要率为 0，「只看重要的」在该 Tab 必为空，
 *    这里给出专门的文案「本频道暂无重要快讯」，而不是一片空白。
 * 4. 卡片点击跳转官方原文，不在站内嵌全文（合规：内容版权归华尔街见闻）。
 *
 * 接口契约与降级策略详见 docs/live-news.md。
 */

import { useMemo, useState } from 'react';
import { Button } from '../components/basic/Button';
import { Card } from '../components/basic/Card';
import { Checkbox } from '../components/basic/Checkbox';
import { Chip } from '../components/basic/Chip';
import { Input } from '../components/basic/Input';
import { Loading } from '../components/basic/Loading';
import { Select } from '../components/basic/Select';
import { TabNav } from '../components/common/TabNav';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { useLiveNews, useLiveNewsChannels } from '../hooks/useLiveNews';
import type { LiveNewsItem } from '../types/liveNews';

/** 把 `YYYY-MM-DD` 之类的键转为本地日期字符串（用于「今天/昨天」选项） */
function formatDateValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** 把秒级时间戳格式化为 `HH:mm` */
function formatTime(displayTime: number | null): string {
  if (!displayTime) return '--:--';
  const date = new Date(displayTime * 1000);
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${hour}:${minute}`;
}

/**
 * 把快讯正文中的【xxx】标题段拆出来单独加粗展示。
 * 华尔街见闻的快讯常用「【标题】正文」的形式，拆分后更接近原站观感。
 */
function splitLeadingTitle(content: string): { lead: string | null; rest: string } {
  const match = /^【([^】]+)】\s*/.exec(content);
  if (!match) return { lead: null, rest: content };
  return { lead: match[1], rest: content.slice(match[0].length) };
}

/** 单条快讯卡片（不额外封装成组件文件，按项目约定内联在页面内） */
function LiveNewsRow({ item, showImportant }: { item: LiveNewsItem; showImportant: boolean }) {
  const { t } = useUiLanguage();
  const { lead, rest } = splitLeadingTitle(item.content || item.title);
  // 快讯常无标题，展示时回退到正文
  const body = rest || item.title;
  const isImportant = showImportant && item.important;

  return (
    <Card className="mb-2 transition-colors hover:border-[var(--primary)]/40" padding="sm">
      <a
        href={item.uri || undefined}
        target="_blank"
        rel="noopener noreferrer"
        className="flex gap-3 no-underline"
      >
        {/* 左侧竖线：重要用主色，普通用中性色 */}
        <span
          aria-hidden
          className={`mt-0.5 w-[3px] shrink-0 rounded-full ${
            isImportant ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
          }`}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <time className="shrink-0 text-xs tabular-nums text-muted-text">
              {formatTime(item.displayTime)}
            </time>
            {isImportant && (
              <Chip size="sm" color="danger" variant="soft">
                {t('liveNews.importantTag')}
              </Chip>
            )}
            {item.author && (
              <span className="truncate text-xs text-muted-text/70">{item.author}</span>
            )}
          </div>
          <p className="mt-1 text-sm leading-relaxed text-foreground">
            {lead && <span className="font-semibold">{lead}</span>}
            {lead && body ? '　' : null}
            {body}
          </p>
        </div>
      </a>
    </Card>
  );
}

const LiveNewsPage: React.FC = () => {
  const { t } = useUiLanguage();
  const { channels, degraded, loading: channelsLoading } = useLiveNewsChannels();

  const [activeChannel, setActiveChannel] = useState('');
  const [keyword, setKeyword] = useState('');
  const [importantOnly, setImportantOnly] = useState(false);
  const [dateValue, setDateValue] = useState('');

  // 日期下拉选项：全部 / 今天 / 昨天（按用户本地时区计算）
  const dateOptions = useMemo(() => {
    const today = new Date();
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    return [
      { value: '', label: t('liveNews.dateAll') },
      { value: formatDateValue(today), label: t('liveNews.dateToday') },
      { value: formatDateValue(yesterday), label: t('liveNews.dateYesterday') },
    ];
  }, [t]);

  // 默认选中第一个频道（正常为「要闻」，降级时也只剩「要闻」）。
  // 用派生值而非 effect 同步 setState，避免级联渲染。
  const effectiveChannel = activeChannel || channels[0]?.value || '';
  // 降级数据没有重要级字段，此时即便用户此前勾过也按未勾选处理，
  // 防止停留在一个必然为空的筛选态。
  const effectiveImportantOnly = importantOnly && !degraded;

  const {
    grouped,
    loading,
    refreshing,
    error,
    hasMore,
    degraded: listDegraded,
    isEmpty,
    loadMore,
    refresh,
  } = useLiveNews(effectiveChannel, {
    importantOnly: effectiveImportantOnly,
    keyword,
    date: dateValue || null,
  });

  const tabItems = useMemo(
    () => channels.map((channel) => ({ value: channel.value, label: channel.label })),
    [channels]
  );

  // 空态文案：按当前筛选条件给出更具体的提示
  const emptyText = useMemo(() => {
    if (effectiveImportantOnly) return t('liveNews.emptyImportant');
    if (keyword.trim()) return t('liveNews.emptyKeyword');
    if (dateValue) return t('liveNews.emptyDate');
    return t('liveNews.empty');
  }, [effectiveImportantOnly, keyword, dateValue, t]);

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6">
      <header className="mb-4">
        <h1 className="text-xl font-semibold text-foreground">{t('liveNews.title')}</h1>
        <p className="mt-1 text-xs text-muted-text">{t('liveNews.subtitle')}</p>
      </header>

      {/* 降级提示：官方源不可用时告知用户能力已收敛 */}
      {(degraded || listDegraded) && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-300">
          {t('liveNews.degradedTip')}
        </div>
      )}

      {/* 频道 Tab：数据来源于后端，降级时自动收敛为单 Tab */}
      {channelsLoading ? (
        <div className="py-4">
          <Loading label={t('liveNews.loading')} />
        </div>
      ) : (
        tabItems.length > 0 && (
          <TabNav
            items={tabItems}
            value={effectiveChannel}
            onChange={setActiveChannel}
            variant="secondary"
            ariaLabel={t('liveNews.channelTabs')}
          />
        )
      )}

      {/* 工具条：搜索 / 只看重要的 / 日期 / 刷新 */}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Input
          type="text"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder={t('liveNews.searchPlaceholder')}
          aria-label={t('liveNews.searchPlaceholder')}
          className="h-9 min-w-[180px] flex-1"
        />
        {/* 降级数据无重要级字段，此时隐藏该开关 */}
        {!degraded && (
          <Checkbox
            checked={importantOnly}
            onChange={(event) => setImportantOnly(event.target.checked)}
            label={t('liveNews.importantOnly')}
            containerClassName="shrink-0"
          />
        )}
        <Select
          value={dateValue}
          onChange={setDateValue}
          options={dateOptions}
          className="w-[130px] shrink-0"
        />
        <Button
          variant="outline"
          size="sm"
          isLoading={refreshing}
          onClick={() => {
            void refresh();
          }}
        >
          {t('liveNews.refresh')}
        </Button>
      </div>

      {/* 内容区：按日期分组 */}
      <div className="mt-4">
        {loading ? (
          <div className="py-10">
            <Loading label={t('liveNews.loading')} />
          </div>
        ) : error ? (
          <div className="py-10 text-center text-sm text-danger">{error}</div>
        ) : isEmpty ? (
          <div className="py-16 text-center text-sm text-muted-text">{emptyText}</div>
        ) : (
          grouped.map((group) => (
            <section key={group.date} className="mb-4">
              <div className="mb-2 flex items-center gap-3">
                <h2 className="text-sm font-medium text-foreground">{group.label}</h2>
                <span className="h-px flex-1 bg-[var(--border)]" />
              </div>
              {group.items.map((item) => (
                <LiveNewsRow
                  key={`${group.date}-${item.id}`}
                  item={item}
                  showImportant={!degraded}
                />
              ))}
            </section>
          ))
        )}

        {hasMore && !loading && (
          <div className="mt-4 flex justify-center">
            <Button variant="ghost" size="sm" onClick={loadMore}>
              {t('liveNews.loadMore')}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveNewsPage;
