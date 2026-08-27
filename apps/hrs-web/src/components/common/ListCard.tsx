/**
 * ListCard —— 通用列表卡片按钮组件
 * 作用：在设置 / 分类导航等场景下，作为可点击的列表项卡片。
 * 由左侧图标、主标题（及可选描述）、右侧计数徽标（或 hover 时的编辑/删除操作）组成，
 * 支持选中态高亮与基于序号的错位入场动画，供多个列表页统一复用。
 */

import { useState } from 'react';
import type { ComponentType, SVGProps } from 'react';
import { motion } from 'motion/react';
import { Pencil, Trash2, Layers3 } from 'lucide-react';
import { Chip, HrsButton } from '../';
import { cn } from '../../utils/cn';

export interface ListCardProps {
    /** 左侧图标，默认使用 Layers3 */
    icon?: ComponentType<SVGProps<SVGSVGElement>>;
    /** 主标题（必填） */
    title: string;
    /** 次要描述，显示在标题行下方并以左缩进对齐；为空时不渲染 */
    description?: string;
    /** 右侧计数徽标数值，默认 0 */
    count?: number;
    /** 是否选中态，切换左侧图标/标题高亮与左侧边框阴影 */
    isActive?: boolean;
    /** 点击卡片（标题行）触发 */
    onClick?: () => void;
    /** 网格序号，从 0 起算，用于入场动画错位延迟，使卡片逐个淡入上移 */
    ordinal?: number;
    /** 编辑回调，传入后鼠标移入时显示编辑按钮（替代计数徽标） */
    onEdit?: () => void;
    /** 删除回调，传入后鼠标移入时显示删除按钮（替代计数徽标） */
    onDelete?: () => void;
}

/**
 * 列表卡片按钮，适用于设置 / 分类导航等场景。
 *
 * 视觉结构（竖向 flex-col，两行）：
 * - 第一行：左侧图标 + 中间标题（弹性占满、左对齐）+ 右侧计数徽标；
 *           当传入 onEdit / onDelete 且鼠标移入时，右侧切换为编辑 / 删除按钮。
 * - 第二行：描述文本，左缩进以与标题对齐；仅在存在 description 时渲染。
 *
 * 交互：通过 isActive 切换选中态样式，onClick 触发选择；
 *       hover 时若提供了操作回调则以按钮替换计数（与计数互斥，不撑宽卡片）。
 * 动画：基于 ordinal 的错位入场（淡入 + 上移）。
 */
export function ListCard({
    icon: Icon = Layers3,
    title,
    description,
    count = 0,
    isActive = false,
    onClick,
    ordinal = 0,
    onEdit,
    onDelete,
}: ListCardProps) {
    const [hovered, setHovered] = useState(false);
    // 仅当确实提供了操作回调且处于 hover 态时，才用按钮替换计数徽标
    const showActions = hovered && (onEdit || onDelete);
    return (
        // 注意：根元素使用 div 而非 button，避免「button 嵌套 button」
        // （内部编辑 / 删除按钮本身是 <button>，若根也是 button 会触发 hydration 错误）。
        // 通过 role="button" + tabIndex + 键盘事件保留可点击卡片的可访问性。
        <motion.div
            role="button"
            tabIndex={0}
            // 入场动画：淡入 + 上移，按 ordinal 错位延迟逐个加载
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut', delay: ordinal * 0.05 }}
            className={cn(
                'group flex w-full min-w-[9rem] flex-col items-stretch rounded-md border gap-1 px-3 pt-2 pb-3 text-left',
                'transition-[background-color,border-color,box-shadow] duration-[600ms] cursor-pointer outline-none',
                'focus-visible:ring-2 focus-visible:ring-primary-glow',
                'lg:min-w-0 lg:w-full lg:items-stretch',
                isActive
                    ? 'border-primary-glow bg-primary-subtle shadow-[inset_3px_0_0_hsl(var(--primary)/0.74)]'
                    : 'border-transparent bg-transparent hover:bg-primary-faint',
            )}
            onClick={onClick}
            onKeyDown={(e) => {
                if ((e.key === 'Enter' || e.key === ' ') && onClick) {
                    e.preventDefault();
                    onClick();
                }
            }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            aria-current={isActive ? 'page' : undefined}
        >
            {/* 第一行：左图标 + 中标题 + 右计数/操作按钮 */}
            <div className="flex min-w-0 w-full items-center h-7 gap-3">
                <Icon
                    className={cn('h-4 w-4 shrink-0', isActive ? 'text-[hsl(var(--primary))]' : 'text-muted-text')}
                    aria-hidden="true"
                />
                {/* 中：主标题（弹性占满、左对齐，超长截断） */}
                <span className="min-w-0 flex-1">
                    <span className={cn('block truncate text-sm font-medium', isActive ? 'text-foreground' : 'text-secondary-text')}>
                        {title}
                    </span>
                </span>
                {/* 右：计数徽标 / 编辑删除按钮（hover 时互斥切换） */}
                <span className="flex shrink-0 items-center">
                    {showActions ? (
                        <span
                            className="flex items-center"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {onEdit ? (
                                <HrsButton
                                    variant="ghost"
                                    size="xs"
                                    onClick={onEdit}
                                    aria-label="编辑"
                                    className="!px-1.5"
                                >
                                    <Pencil className="h-3.5 w-3.5" />
                                </HrsButton>
                            ) : null}
                            {onDelete ? (
                                <HrsButton
                                    variant="ghost"
                                    size="xs"
                                    onClick={onDelete}
                                    aria-label="删除"
                                    className="!px-1.5 text-danger hover:bg-danger/10"
                                >
                                    <Trash2 className="h-3.5 w-3.5" />
                                </HrsButton>
                            ) : null}
                        </span>
                    ) : (
                        <Chip
                            color={isActive ? 'accent' : 'default'}
                            variant={isActive ? 'primary' : 'secondary'}
                            size="xs"
                            className="shrink-0"
                        >
                            {count}
                        </Chip>
                    )}
                </span>
            </div>
            {/* 第二行：描述，左缩进 ml-7（= 图标宽 16px + gap 12px）以与标题对齐 */}
            {description ? (
                <span className={cn('text-xs ml-7 leading-5 lg:line-clamp-2', isActive ? 'text-secondary-text' : 'text-muted-text')}>
                    {description}
                </span>
            ) : null}
        </motion.div>
    );
}
