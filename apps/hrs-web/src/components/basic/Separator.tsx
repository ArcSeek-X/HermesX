/**
 * 分割线组件（Separator）
 *
 * 从 Modal 的 Header / Body 分割线抽象而来的通用分割线，
 * 基础规格对齐 HeroUI Separator，使用方只需关注方向、颜色变体与渐变开关：
 *
 * - orientation：水平（默认，占满父容器宽度）/ 垂直（占满父容器高度）
 * - variant：颜色变体（对齐 HeroUI 规格）—— default / secondary / tertiary，
 *   颜色由 HeroUI 主题 token（--separator 系列）提供，自动跟随明暗主题
 * - gradient：是否叠加两端渐隐渐变（默认 false）—— 在当前 variant 颜色的
 *   基础上，两端 10% ~ 90% 区间渐变到透明，视觉更轻，适合卡片 / 弹窗内
 * - 垂直间距 / 水平间距等布局属性由使用方通过 className 自行控制
 *
 * 内部基于 HeroUI Separator（底层为 react-aria-components 的集合安全
 * Separator）承载，因此可直接放入 ListBox / Menu 等 react-aria 集合
 * 容器中作为分组分割线使用；自身样式全部用 Tailwind 工具类覆盖
 * HeroUI 默认样式（utilities 层优先于 components 层）。
 *
 * @example
 * ```tsx
 * // 默认实色分割线（default 变体）
 * <Separator />
 *
 * // 两端渐隐渐变分割线（Modal 内 Header 与 Body 之间的同款效果）
 * <Separator gradient className="my-3" />
 *
 * // 次级颜色变体 + 渐变
 * <Separator variant="secondary" gradient />
 *
 * // 垂直分割线（常用于左右分区）
 * <Separator orientation="vertical" className="mx-3" />
 * ```
 */
import type { FC } from 'react';
import { Separator as HeroSeparator } from '@heroui/react';
import { cn } from '../../utils/cn';

/** 分割线方向 */
export type HrsSeparatorOrientation = 'horizontal' | 'vertical';

/** 分割线颜色变体（对齐 HeroUI Separator 的 variant 规格） */
export type HrsSeparatorVariant = 'default' | 'secondary' | 'tertiary';

/**
 * 各颜色变体 × 方向的两端渐隐渐变样式。
 * 渐变基于各 variant 对应的 HeroUI 主题颜色变量生成（两端 10% ~ 90%）。
 * --separator / --separator-secondary / --separator-tertiary  样式参数皆取自'@heroui/style'
 * 注 1：必须用固定类名映射（动态拼接的任意值类不会被 Tailwind 扫描生成）。
 * 注 2：渐变是 background-image，而 HeroUI 的 .separator 基类自带
 * background-color（var(--separator)）——CSS 中 background-color 绘制在
 * background-image 之下，会填满渐变的透明端点导致渐变“失效”；
 * 因此渐变时必须叠加 bg-transparent 清掉底层背景色（twMerge 会将
 * bg-transparent 与 bg-[linear-gradient(...)] 归为不同组，两者可共存）。
 */
const GRADIENT_STYLES: Record<
    HrsSeparatorVariant,
    Record<HrsSeparatorOrientation, string>
> = {
    default: {
        //水平
        horizontal:
            'bg-[linear-gradient(to_right,transparent,var(--separator)_10%,var(--separator)_90%,transparent)]',
        //垂直    
        vertical:
            'bg-[linear-gradient(to_bottom,transparent,var(--separator)_10%,var(--separator)_90%,transparent)]',
    },
    secondary: {
        horizontal:
            'bg-[linear-gradient(to_right,transparent,var(--separator-secondary)_10%,var(--separator-secondary)_90%,transparent)]',
        vertical:
            'bg-[linear-gradient(to_bottom,transparent,var(--separator-secondary)_10%,var(--separator-secondary)_90%,transparent)]',
    },
    tertiary: {
        horizontal:
            'bg-[linear-gradient(to_right,transparent,var(--separator-tertiary)_10%,var(--separator-tertiary)_90%,transparent)]',
        vertical:
            'bg-[linear-gradient(to_bottom,transparent,var(--separator-tertiary)_10%,var(--separator-tertiary)_90%,transparent)]',
    },
};

/** 分割线组件属性 */
export interface HrsSeparatorProps {
    /** 方向，默认 'horizontal'（水平占满父容器宽度） */
    orientation?: HrsSeparatorOrientation;
    /** 颜色变体（对齐 HeroUI 规格），默认 'default' */
    variant?: HrsSeparatorVariant;
    /** 是否叠加两端渐隐渐变（在 variant 颜色基础上），默认 false */
    gradient?: boolean;
    /** 自定义 className（间距、宽度覆盖等布局属性由使用方控制） */
    className?: string;
}

/**
 * 通用分割线组件。
 *
 * 渲染层面由 HeroUI Separator（react-aria 集合安全的 hr / div）承载：
 * variant / orientation 直接透传，非渐变时的颜色完全由 HeroUI 主题 token
 * 决定；渐变时以固定映射表叠加两端渐隐的任意值渐变类覆盖默认背景。
 * role="separator" 与 aria-orientation 由其内部自动提供。
 */
export const Separator: FC<HrsSeparatorProps> = ({
    orientation = 'horizontal',
    variant = 'default',
    gradient = false,
    className,
}) => (
    <HeroSeparator
        orientation={orientation}
        variant={variant}
        className={cn(
            'hrs-separator shrink-0 border-0',
            // 基础：水平占满宽度且高 1px，垂直占满高度且宽 1px（可被 className 覆盖）
            orientation === 'horizontal'
                ? 'h-px w-full'
                : 'h-full w-px min-h-0',
            gradient && 'bg-transparent',
            gradient && GRADIENT_STYLES[variant][orientation],
            className,
        )}
    />
);
