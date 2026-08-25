import type { ComponentType, SVGProps } from 'react';
import { motion } from 'motion/react';
import { Layers3 } from 'lucide-react';
import { Chip } from '../';
import { cn } from '../../utils/cn';

export interface ListCardProps {
    icon?: ComponentType<SVGProps<SVGSVGElement>>;
    title: string;
    description?: string;
    count?: number;
    isActive?: boolean;
    onClick?: () => void;
    /** 网格序号，用于入场动画错位延迟（从 0 起算），实现卡片逐个动态加载 */
    ordinal?: number;
}

/**
 * 列表卡片按钮：用于设置分类导航等场景，左侧图标 + 标题/描述 + 右侧计数徽标。
 * 通过 isActive 切换选中态样式，onClick 触发选择。
 * ordinal 控制入场动画的错位延迟，使卡片依次淡入上移。
 */
export function ListCard({
    icon: Icon = Layers3,
    title,
    description,
    count = 0,
    isActive = false,
    onClick,
    ordinal = 0,
}: ListCardProps) {
    return (
        <motion.button
            type="button"
            // 入场动画：淡入 + 上移，按 ordinal 错位延迟逐个加载
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut', delay: ordinal * 0.05 }}
            className={cn(
                'flex min-w-[9rem] items-center gap-2 rounded-md border px-3 py-2.5 text-left',
                'transition-[background-color,border-color,box-shadow] duration-[600ms]',
                'lg:min-w-0 lg:w-full lg:items-start lg:gap-3 lg:px-3 lg:py-3',
                isActive
                    ? 'border-primary-glow bg-primary-subtle shadow-[inset_3px_0_0_hsl(var(--primary)/0.74)]'
                    : 'border-transparent bg-transparent hover:bg-primary-faint',
            )}
            onClick={onClick}
            aria-current={isActive ? 'page' : undefined}
        >
            <Icon
                className={cn('h-4 w-4 shrink-0 lg:mt-0.5', isActive ? 'text-[hsl(var(--primary))]' : 'text-muted-text')}
                aria-hidden="true"
            />
            <span className="min-w-0 flex-1">
                <span className={cn('block truncate text-sm font-medium', isActive ? 'text-foreground' : 'text-secondary-text')}>
                    {title}
                </span>
                {description ? (
                    <span className={cn('mt-1 hidden text-xs leading-5 lg:line-clamp-2', isActive ? 'text-secondary-text' : 'text-muted-text')}>
                        {description}
                    </span>
                ) : null}
            </span>
            <Chip
                color={isActive ? 'accent' : 'default'}
                variant={isActive ? 'primary' : 'secondary'}
                size="xs"
                className="shrink-0"
            >
                {count}
            </Chip>
        </motion.button>
    );
}
