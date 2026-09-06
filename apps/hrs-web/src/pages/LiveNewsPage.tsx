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
// 组件统一从 components 桶文件引入，避免逐层深引用 basic/ 内部路径
import { Checkbox, HrsButton, HrsSelect, Input, Loading, TabNav, type HrsSelectOptionDef, } from '../components';
import { NewsCard } from '../components/common/Card/newsCard';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { useLiveNews, useLiveNewsChannels } from '../hooks/useLiveNews';
import { toDateKey } from '../utils/format';

const LiveNewsPage: React.FC = () => {
    const { t } = useUiLanguage();
    const { channels, degraded, loading: channelsLoading } = useLiveNewsChannels();

    const [activeChannel, setActiveChannel] = useState('');
    const [keyword, setKeyword] = useState('');
    const [importantOnly, setImportantOnly] = useState(false);
    const [dateValue, setDateValue] = useState('');

    // 日期下拉选项：全部 / 今天 / 昨天（按用户本地时区计算）
    // HrsSelect 的选项约定为 { key, label }，key 为空串表示「不限日期」
    const dateOptions = useMemo<HrsSelectOptionDef[]>(() => {
        const today = new Date();
        const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
        return [
            { key: '', label: t('liveNews.dateAll') },
            { key: toDateKey(today), label: t('liveNews.dateToday') },
            { key: toDateKey(yesterday), label: t('liveNews.dateYesterday') },
        ];
    }, [t]);

    // 默认选中第一个频道（正常为「要闻」，降级时也只剩「要闻」）。
    // 用派生值而非 effect 同步 setState，避免级联渲染。
    const effectiveChannel = activeChannel || channels[0]?.value || '';
    // 降级数据没有重要级字段，此时即便用户此前勾过也按未勾选处理，
    // 防止停留在一个必然为空的筛选态。
    const effectiveImportantOnly = importantOnly && !degraded;

    const {
        newsGroupedByDate,
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

    const channelTabItems = useMemo(
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
        <div className="mx-auto w-full">
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
                channelTabItems.length > 0 && (
                    <TabNav
                        items={channelTabItems}
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
                <HrsSelect
                    value={dateValue}
                    // 单选模式下回调返回 Key | null；非字符串（多选数组 / null）统一按「不限日期」处理
                    onChange={(value) => setDateValue(typeof value === 'string' ? value : '')}
                    options={dateOptions}
                    size="sm"
                    className="w-[130px] shrink-0"
                />
                <HrsButton
                    size="sm"
                    isLoading={refreshing}
                    loadingText={t('liveNews.refreshing')}
                    onClick={() => { void refresh(); }}
                >
                    {t('liveNews.refresh')}
                </HrsButton>
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
                    newsGroupedByDate.map((group) => (
                        <section key={group.date} className="mb-4">
                            <div className="mb-2 flex items-center gap-3">
                                <h2 className="text-sm font-medium text-foreground">{group.label}</h2>
                                <span className="h-px flex-1 bg-[var(--border)]" />
                            </div>
                            {group.items.map((item, idx) => (
                                <NewsCard
                                    key={`${group.date}-${item.id}`}
                                    item={item}
                                    showImportant={!degraded}
                                    ordinal={idx}
                                />
                            ))}
                        </section>
                    ))
                )}

                {hasMore && !loading && (
                    <div className="mt-4 flex justify-center">
                        <HrsButton variant="ghost" size="sm" onClick={loadMore}>
                            {t('liveNews.loadMore')}
                        </HrsButton>
                    </div>
                )}
            </div>
        </div>
    );
};

export default LiveNewsPage;
