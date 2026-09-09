/**
 * LiveCalendarFilter.tsx
 * ------------------------------------------------------------
 * 消息日历筛选：可展开筛选区域（Tab 行下方、日历上方，展开时把日历等内容向下挤压）。
 * 注：触发用的「筛选按钮」不在此处（已移除封装），由使用方 LiveCalendarPage 直接用
 * HrsButton 渲染；本文件只负责筛选区域面板本身。
 *
 * 设计要点：
 * 1. **草稿 / 生效分离**：面板内部持有草稿 state（`draft`），仅点「确认」才
 *    通过 `onApply` 上抛给 Page；输入过程中 Page 与日历不重渲染，避免打字卡顿。
 *    草稿与 `value`（已生效值）单向同步：外部确认 / 重置后立即对齐。
 * 2. **展开动画**：用 motion.div 对 `height: 0 ↔ auto` + opacity 做缓动过渡
 *    （easeOutExpo，比 CSS grid-rows 0fr→1fr 更顺滑），日历在文档流中被自然下推。
 * 3. **纯客户端过滤**：四个条件都不触发网络请求，过滤逻辑在
 *    `hooks/useLiveCalendar.ts` 的 `useLiveCalendarMonths` 内完成，
 *    故月 / 周 / 日 / List 四视图同时生效。
 */

import { memo, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { pinyin } from 'pinyin-pro';
import { TextField, Label } from '@heroui/react';
import { HrsButton, Input, HrsSelect, type HrsSelectDataSourceDef, type HrsSelectOptionDef, } from '../../../components';
import { motion } from 'motion/react';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { cn } from '../../../utils/cn';
import {
    ALL_IMPORTANCE_LEVELS,
    IMPORTANCE_LABELS,
    type ImportanceLevel,
} from '../../../constants/newsImportance';
import type { CalendarCountryDef } from '../../../types/liveCalendar';
import {
    createDefaultLiveCalendarFilter,
    type LiveCalendarFilterValue,
    type LiveCalendarTypeFilter,
} from './LiveCalendarFilterState';

/** 国家下拉里「全部」对应的选项 key（真实 countryId 为空串，故用独立 key） */
const ALL_COUNTRY_KEY = '__all__';

/** 拼音首字母取不到（非中文名）的国家归入该分组，排在 A-Z 之后 */
const OTHER_COUNTRY_GROUP = '#';

/** 国家名 → 拼音首字母（A~Z）；取不到时归入 `#` */
function pinyinInitialOf(name: string): string {
    const [initial = ''] = pinyin(name, { pattern: 'first', toneType: 'none', type: 'array' });
    const letter = initial.charAt(0).toUpperCase();
    return /[A-Z]/.test(letter) ? letter : OTHER_COUNTRY_GROUP;
}

/** 重要度 chip 文案：`0` 无业务文案，回退到「无」 */
function importanceLabel(level: ImportanceLevel, noneText: string): string {
    return IMPORTANCE_LABELS[level] || noneText;
}

// ── 筛选区域 ────────────────────────────────────────────────────────────

export interface LiveCalendarFilterPanelProps {
    /** 是否展开 */
    open: boolean;
    /** 已生效的筛选条件（草稿的同步源） */
    value: LiveCalendarFilterValue;
    /** 国家字典（来自 `useLiveCalendarCountries`） */
    countries: CalendarCountryDef[];
    /** 点「确认」：提交草稿 */
    onApply: (next: LiveCalendarFilterValue) => void;
    /** 点「重置」：清空全部条件 */
    onReset: () => void;
    className?: string;
}

/**
 * 可展开筛选区域。
 *
 * 条件：重要度（多选 chip）、事件类型（三态切换）、国家 / 地区（下拉）、关键词（输入框）。
 * 收起时容器高度为 0（`grid-rows-[0fr]`）且不响应指针事件，但保留 DOM 以维持动画。
 */
export const LiveCalendarFilterPanel = memo(
    ({
        open,
        value,
        countries,
        onApply,
        onReset,
        className,
    }: LiveCalendarFilterPanelProps) => {
        const { t } = useUiLanguage();
        // 草稿：与已生效值分离，输入过程不外抛，避免逐键触发日历重算。
        // 已生效值变化（确认 / 重置）时把草稿拉回一致 —— 用渲染期同步而非 effect，
        // 避免 effect 内 setState 触发的级联渲染。
        const [draft, setDraft] = useState<LiveCalendarFilterValue>(value);
        const [syncedValue, setSyncedValue] = useState<LiveCalendarFilterValue>(value);
        if (value !== syncedValue) {
            setSyncedValue(value);
            setDraft(value);
        }

        // 重置：面板先把草稿与同步基准拉回默认值，再通知 Page。
        // 仅靠 Page 回传不够 —— 若上次生效值就是默认值的同一引用，
        // 下面的引用比较会判定「无变化」，草稿不会被回灌（表现：点了重置但面板不变）。
        const handleReset = () => {
            const next = createDefaultLiveCalendarFilter();
            setSyncedValue(next);
            setDraft(next);
            onReset();
        };

        const flagUriByCountryId = useMemo(() => {
            const map = new Map<string, string>();
            for (const country of countries) {
                if (country.flagUri) map.set(country.countryId, country.flagUri);
            }
            return map;
        }, [countries]);

        // 国家下拉：首项「全部国家/地区」，其余按拼音首字母 A-Z 分组（组内按全拼排序），
        // 无拼音首字母的归入 `#` 组并排在最后。选项渲染为「国旗 + 国名」。
        const countryOptions = useMemo<HrsSelectDataSourceDef>(() => {
            const ordered = [...countries].map((country) => ({
                country,
                initial: pinyinInitialOf(country.countryName),
                full: pinyin(country.countryName, { toneType: 'none' }),
            }));
            ordered.sort((a, b) =>
                a.initial === b.initial
                    ? a.full.localeCompare(b.full)
                    : a.initial.localeCompare(b.initial),
            );

            const groups = new Map<string, HrsSelectOptionDef[]>();
            for (const item of ordered) {
                const options = groups.get(item.initial);
                if (options) {
                    options.push({ key: item.country.countryId, label: item.country.countryName });
                } else {
                    groups.set(item.initial, [
                        { key: item.country.countryId, label: item.country.countryName },
                    ]);
                }
            }

            return [
                { key: ALL_COUNTRY_KEY, label: t('component.LiveCalendar.filter.country.all') },
                ...[...groups.entries()]
                    .sort(([a], [b]) =>
                        a === OTHER_COUNTRY_GROUP ? 1 : b === OTHER_COUNTRY_GROUP ? -1 : a.localeCompare(b),
                    )
                    .map(([initial, options]) => ({
                        key: `country-group-${initial}`,
                        title: initial,
                        options,
                    })),
            ];
        }, [countries, t]);

        // 无国旗的选项（含「全部国家/地区」）不渲染占位块，直接贴左显示国名，
        // 避免触发器与下拉列表里出现一块空区域
        const renderCountryOption = (option: HrsSelectOptionDef) => {
            const flagUri = flagUriByCountryId.get(String(option.key));
            return (
                <span className="flex min-w-0 items-center gap-1.5">
                    {flagUri ? (
                        <img className="h-3 w-4 shrink-0 object-cover" src={flagUri} alt="countryFlag" aria-hidden />
                    ) : null}
                    <span className="truncate text-xs">{option.label}</span>
                </span>
            );
        };

        return (
            <motion.div
                id="live-calendar-filter-panel"
                initial={false}
                animate={{ height: open ? 'auto' : 0, opacity: open ? 1 : 0 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className={cn('overflow-hidden', !open && 'pointer-events-none', className)}
                aria-hidden={!open}
            >
                <div className="mt-2 flex flex-col gap-3 rounded-sm bg-muted/10 px-3 py-3">
                    {/* 三个短字段给「够用」的基准宽度且不放大（grow 0），余量全留给关键词；
                        窗口变窄时先各自收缩到 min-w，再整体换行 */}
                    <div className="flex flex-wrap items-start gap-x-4 gap-y-4">
                        {/* 重要度：多选（受控 ImportanceLevel[]，复用 HrsSelect 多选） */}
                        <FilterField
                            label={t('component.LiveCalendar.filter.importance')}
                            className="min-w-[7rem] flex-[0_1_8.5rem]"
                        >
                            <HrsSelect
                                size="sm"
                                selectionMode="multiple"
                                options={ALL_IMPORTANCE_LEVELS.map((level) => ({
                                    key: level,
                                    label: importanceLabel(
                                        level,
                                        t('component.LiveCalendar.filter.importance.none'),
                                    ),
                                }))}
                                value={draft.importance}
                                onChange={(next) => {
                                    if (!Array.isArray(next)) return;
                                    setDraft((prev) => ({
                                        ...prev,
                                        importance: next as ImportanceLevel[],
                                    }));
                                }}
                                className="w-full"
                            />
                        </FilterField>

                        {/* 类型：全部 / 经济数据 / 大事件（单值，受控 LiveCalendarTypeFilter） */}
                        <FilterField
                            label={t('component.LiveCalendar.filter.type')}
                            className="min-w-[5.5rem] flex-[0_1_6.5rem]"
                        >
                            <HrsSelect
                                size="sm"
                                options={[
                                    { key: 'all', label: t('component.LiveCalendar.filter.type.all') },
                                    { key: 'FD', label: t('component.LiveCalendar.calendarType.FD') },
                                    { key: 'FE', label: t('component.LiveCalendar.calendarType.FE') },
                                ]}
                                value={draft.calendarType}
                                onChange={(next) => {
                                    setDraft((prev) => ({
                                        ...prev,
                                        calendarType: (next as LiveCalendarTypeFilter) || 'all',
                                    }));
                                }}
                                className="w-full"
                            />
                        </FilterField>

                        {/* 国家 / 地区 */}
                        <FilterField
                            label={t('component.LiveCalendar.filter.country')}
                            className="min-w-[7rem] flex-[0_1_9rem]"
                        >
                            <HrsSelect
                                size="sm"
                                options={countryOptions}
                                value={draft.countryId || ALL_COUNTRY_KEY}
                                onChange={(next) =>
                                    setDraft((prev) => ({
                                        ...prev,
                                        countryId:
                                            String(next) === ALL_COUNTRY_KEY
                                                ? ''
                                                : String(next),
                                    }))
                                }
                                renderItem={renderCountryOption}
                                className="w-full"
                                // 滚动容器是弹层本身（.select__popover 自带 overflow-y-auto），
                                // list-box 不可滚动，故仅限高弹层到 ~400px，列表超出时由弹层滚动；
                                // 末尾 ! 是 Tailwind v4 的 !important 修饰符，压制 react-aria Popover
                                // 注入的 inline max-height（按视口自动算的高度），保证 400px 真的生效
                                popoverClassName="countrySelectPopover max-h-[400px]! overflow-y-auto"
                            />
                        </FilterField>

                        {/* 关键词：唯一会放大的字段，吃掉行内剩余空间 */}
                        <FilterField
                            label={t('component.LiveCalendar.filter.keyword')}
                            className="min-w-[11rem] flex-[1_1_14rem]"
                        >
                            <div className="relative w-full">
                                <Search
                                    aria-hidden
                                    className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-text"
                                />
                                <Input
                                    className="w-full pl-7"
                                    value={draft.keyword}
                                    placeholder={t('component.LiveCalendar.filter.keywordPlaceholder')}
                                    onChange={(e) =>
                                        setDraft((prev) => ({
                                            ...prev,
                                            keyword: e.target.value,
                                        }))
                                    }
                                    onKeyDown={(e) => {
                                        // 回车即确认，与点「确认」等价
                                        if (e.key === 'Enter') {
                                            onApply({ ...draft, keyword: draft.keyword.trim() });
                                        }
                                    }}
                                />
                            </div>
                        </FilterField>

                        {/* 操作区：靠右；行容器是 items-start，self-end 使按钮与输入框底部对齐 */}
                        <div className="ml-auto flex shrink-0 items-center gap-2 self-end">
                            <HrsButton variant="ghost" onClick={handleReset}>
                                {t('component.LiveCalendar.filter.reset')}
                            </HrsButton>
                            <HrsButton onClick={() =>
                                onApply({ ...draft, keyword: draft.keyword.trim() })
                            }
                            >
                                {t('component.LiveCalendar.filter.apply')}
                            </HrsButton>
                        </div>
                    </div>
                </div>
            </motion.div>
        );
    },
);
LiveCalendarFilterPanel.displayName = 'LiveCalendarFilterPanel';

/** 筛选区域中的一个「标签 + 控件」单元，使用 HeroUI TextField + Label 取得统一文案与无障碍关联；
 *  外层 TextField 用 `w-auto` 而非 `w-full`，使多个字段能在行容器内水平排成一行（各自再用 flex 分配宽度） */
function FilterField({
    label,
    children,
    className,
}: {
    label: string;
    children: React.ReactNode;
    /** 追加到外层 TextField（控制该字段在水平行内的宽度，如 `flex-[0_1_8.5rem]` / `min-w-[7rem]`） */
    className?: string;
}) {
    return (
        <TextField className={cn('w-auto', className)}>
            <Label className="mb-1 text-xs text-foreground-soft">{label}</Label>
            {children}
        </TextField>
    );
}
