import { useLayoutEffect, useRef, useState } from 'react';
import type { LiveNewsItem } from '../../../types/liveNews';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { motion } from 'motion/react';
import { Chip } from '../../../components';
import { HrsButton } from '../../basic/HrsButton';
import { Separator } from '../../basic/Separator';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../../utils/cn';

/** 把秒级时间戳格式化为 `HH:mm` */
function formatTime(displayTime: number | null): string {
    if (!displayTime) return '--:--';
    const date = new Date(displayTime * 1000);
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${hour}:${minute}`;
}

/**
 * 单条快讯卡片的入参。
 */
export type NewsCardProps = {
    /** 单条快讯数据 */
    item: LiveNewsItem;
    /** 是否处于「只看重要的」模式（控制重要竖线/标签的显隐） */
    showImportant: boolean;
    /** 网格序号，从 0 起算，用于入场动画错位延迟，使卡片逐个淡入上移 */
    ordinal?: number;
};

/**
 * 单条财经快讯卡片。
 *
 * 布局：左时间列 | 垂直分割线 | 右内容列（标题 + 正文）。
 * - 左：发布时间（`HH:mm`），重要条目时间用主题主色强调。
 * - 中：垂直分割线（Separator，secondary 变体 + 两端渐隐），占满卡片高度。
 * - 右：上标题（取自 `item.title`）、下正文（取自 `item.content`）；正文默认 3 行，
 *       超出时末尾出现「展开」按钮，点击展开全部并切换为「收起」。
 * - 重要条目额外在标题行右侧带「重要」标签；作者显示在标题行。
 * - 点击整卡跳转官方原文（`item.uri`），不在站内嵌全文（合规：内容版权归华尔街见闻）。
 * - 入场动画：参考 ListCard，根节点使用 motion.div 实现「淡入 + 上移」，按 ordinal 错位延迟逐个加载。
 */
export function NewsCard({ item, showImportant, ordinal = 0 }: NewsCardProps) {
    const { t } = useUiLanguage();
    const isImportant = showImportant && item.important;
    // 标题取自接口 title 字段；快讯常无标题时回退取 content 首行（数据层已处理）
    const title = item.title;
    const content = item.content;
    const hasTitle = title.trim().length > 0;
    // 渲染层控制标题字数：超过 100 字符以省略号收尾（保留内部换行，不做单行截断）
    const displayTitle = title.length > 50 ? `${title.slice(0, 50)}…` : title;

    // 正文展开控制：未展开时 CSS 裁到 3 行，超出行高才显示「展开」按钮
    const [expanded, setExpanded] = useState(false);
    const [overflow, setOverflow] = useState(false);
    const contentRef = useRef<HTMLParagraphElement>(null);
    // 展开/收起按钮区域 ref：用于精确排除整卡跳转（避免点击按钮触发原文跳转）
    const expanderRef = useRef<HTMLButtonElement>(null);

    // 仅用于判断正文是否超出 3 行（决定「展开」按钮显隐）；不参入高度动画，故只在内容变化时测算一次，
    // 展开/收起不再触发测量与重排版，避免卡顿。预览层常驻 line-clamp-3，直接读 scrollHeight/clientHeight 即可，无需临时改样式。
    useLayoutEffect(() => {
        const el = contentRef.current;
        if (!el) return;
        setOverflow(el.scrollHeight - el.clientHeight > 1);
    }, [content]);

    return (
        <motion.div
            // 入场动画：淡入 + 上移，按 ordinal 错位延迟逐个加载
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut', delay: ordinal * 0.05 }}
            className={cn(
                'mb-2 rounded-lg bg-card border border-subtle p-4',
                'transition-colors hover:border-[var(--primary)]/40',
            )}
        >
            <div
                role="link"
                tabIndex={item.uri ? 0 : -1}
                // 整卡点击跳转原文；落在「展开/收起」按钮区域内则不跳转（用 ref 精确排除，
                // 不依赖事件冒泡拦截——HeroUI 按钮的 press 合成时机与 <a> 默认行为冲突）
                onClick={(e) => {
                    if (expanderRef.current?.contains(e.target as Node)) return;
                    if (item.uri) window.open(item.uri, '_blank', 'noopener,noreferrer');
                }}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && item.uri && !expanderRef.current?.contains(e.target as Node)) {
                        window.open(item.uri, '_blank', 'noopener,noreferrer');
                    }
                }}
                className="flex gap-3 no-underline cursor-pointer"
            >
                {/* 左：发布时间列（固定宽度，右对齐） */}
                <time
                    className={cn(
                        'w-14 shrink-0 pt-0.5 text-right text-xs tabular-nums',
                        isImportant ? 'font-medium text-danger' : 'text-muted-text',
                    )}
                >
                    {formatTime(item.displayTime)}
                </time>

                {/* 中：垂直分割线（占满卡片高度 + 两端渐隐）
                 * 注意：Separator 垂直基类带 h-full，在 row flex 容器中会与 self-stretch 冲突导致高度塌缩为 0；
                 * 用 h-auto 覆盖 h-full，改由 self-stretch 撑满父高。 */}
                <Separator orientation="vertical" variant="default" gradient className="h-auto mx-1 self-stretch" />

                {/* 右：标题 + 正文 */}
                <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-start gap-2">
                        {hasTitle && (
                            <span className={cn('min-w-0 flex-1 break-words whitespace-pre-line text-sm font-semibold leading-snug line-clamp-2', isImportant ? 'text-danger' : 'text-foreground')}>
                                {displayTitle}
                                <Chip
                                    size="sm"
                                    color={isImportant ? 'danger' : 'default'}
                                    variant="primary"
                                    className="shrink-0 ml-2"
                                >
                                    {t(isImportant ? 'liveNews.importantTag' : 'liveNews.normalTag')}
                                </Chip>
                            </span>
                        )}
                    </div>
                    {/* 正文区：常驻 3 行静态预览（绝对定位、卡片底色覆盖，不参与动画）+ 网格动画展开完整正文。
                     * 网格用 grid-template-rows 0fr↔1fr 做高度过渡（浏览器对网格轨道高效插值，比 height:auto 更顺），
                     * 预览盖住网格前 3 行避免重复与留白；展开时网格向下揭示第 4 行起的内容。容器 min-h-[3lh] 保证折叠恒为 3 行。 */}
                    <div className="relative mt-1 min-h-[3lh]">
                        {/* 常驻 3 行预览：不透明卡片底色覆盖网格前 3 行；折叠态即显示 3 行，展开态仍盖住前 3 行防重复 */}
                        <div
                            ref={contentRef}
                            className={cn(
                                'absolute inset-x-0 top-0 h-[3lh] overflow-hidden bg-card line-clamp-3 text-sm leading-relaxed',
                                isImportant ? 'text-danger' : 'text-foreground',
                            )}
                        >
                            {content}
                        </div>
                        {/* 动画展开区：承载完整正文，grid 行高 0fr↔1fr 平滑过渡 */}
                        <div
                            className={cn(
                                'grid transition-[grid-template-rows] duration-400 ease-linear',
                                expanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
                            )}
                        >
                            <div className="min-h-0 overflow-hidden">
                                <p className={cn('text-sm leading-relaxed', isImportant ? 'text-danger' : 'text-foreground')}>
                                    {content}
                                </p>
                            </div>
                        </div>

                    </div>
                    {/* 正文超 3 行且未展开时显示「展开」；展开后显示「收起」 */}
                    {overflow && (
                        // ref 直接挂 HrsButton（HrsButton 已支持 forwardRef 透传 ref 到内部 DOM button），
                        // 精确圈定「展开/收起」按钮区域，使整卡点击跳转逻辑（ref.contains 判断）
                        // 能稳定排除按钮区，避免点展开触发跳转
                        <HrsButton
                            ref={expanderRef}
                            type="button"
                            variant="ghost"
                            size="md"
                            onClick={() => setExpanded((v) => !v)}
                            className="px-1 h-7 gap-0.5 !text-primary  hover:no-underline"
                        >
                            {expanded ? t('liveNews.collapse') : t('liveNews.expand')}
                            <ChevronDown
                                className={cn(
                                    'h-4 w-4 shrink-0 transition-transform',
                                    expanded && 'rotate-180',
                                )}
                                aria-hidden="true"
                            />
                        </HrsButton>
                    )}
                </div>
            </div>
        </motion.div>
    );
}
