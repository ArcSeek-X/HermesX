/**
 * InlineTipCard.tsx
 *
 * 作用简述：
 *   一个通用的「内联提示卡片」组件，可承载成功 / 信息 / 警告 / 危险等多种语义，
 *   最常见用法是承接由请求层解析好的 `ParsedApiError`，渲染出标题、用户友好的
 *   错误文案，并在「原始报错信息」与「展示文案」不一致时，提供可展开的
 *   详细信息面板（便于开发/排障定位）。同时支持可选的「操作按钮」（如重试）
 *   与「关闭按钮」，适配多语言文案。
 *
 * 与 Toast 的区别（视觉同源，但使用场景不同）：
 *   - Toast：固定在视口角落，通过 <Toast /> 挂在 body 下的 portal 渲染，
 *     命令式调用，适合“请求拦截器里统一抛出”之类的瞬态提示。
 *   - InlineTipCard（当前组件）：**内联插入到调用方 DOM 流**（placement="inside"），
 *     适合放在页面内容区，作为「带状区域提示」长期展示。
 *   两者共用同一套样式策略：外层语义色实色背景 + 内层 elevated 卡片内缩 2px
 *   露出边色 + 头部「title + 关闭按钮」 + 主体「描述 + 查看详情 + action」。
 *
 * 视觉风格（variant）：
 *   - 默认 `default`（中性灰），不抢视觉；
 *   - 需要"错误告警"效果（即原 ApiErrorAlert 的红色样式）时，调用方必须显式传 `variant="danger"`；
 *   - 还支持 `accent` / `success` / `warning`，按需选用。
 *
 * 使用场景：
 *   - 网络请求失败、后端返回非 2xx、解析异常等需要在界面上提示用户的场合（传 variant="danger"）。
 *   - 作为全局或局部的内联提示 UI，与 `api/error` 的解析结果配套使用。
 */

import { useState } from 'react';
import type React from 'react';
import type { ParsedApiError } from '../../api/error';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';
import AnimCard from './Card/AnimCard';
import { HrsButton, type HrsButtonVariant } from '../basic/HrsButton';
import { CloseIcon } from '@heroui/react';

/**
 * 视觉风格枚举（与 `Toast.tsx` 中的 `ToastVariant` 保持一致，便于两个组件视觉同源）。
 * 默认 `default`（中性灰）；错误告警场景需调用方显式传 `danger`。
 */
type InlineTipCardVariant = 'default' | 'accent' | 'success' | 'warning' | 'danger';

/**
 * 把 InlineTipCardVariant 映射到 HrsButton 支持的 variant（HrsButton 的 variant 枚举
 * 不含 default / accent，需在此统一转换；warning / danger 用 soft 柔和档避免内联操作过刺眼）。
 */
const CARD_BUTTON_VARIANT_MAPPING: Record<InlineTipCardVariant, HrsButtonVariant> = {
    default: 'secondary',
    accent: 'primary',
    success: 'success-soft',
    warning: 'warning-soft',
    danger: 'danger-soft',
};

/**
 * 组件属性定义。
 *
 * 入参保持不变以兼容现有调用方；新增可选 `variant` 以承载本次样式重构的能力。
 */
interface InlineTipCardProps {
    /** 已解析好的 API 错误信息（必须包含 title、message、rawMessage 等字段）。 */
    error: ParsedApiError;
    /** 透传到最外层容器的额外 className，用于外部覆盖/追加样式。 */
    className?: string;
    /**
     * 视觉风格，默认 `default`（中性灰，不抢视觉）。
     * 错误告警场景请显式传 `variant="danger"` 以还原原 ApiErrorAlert 的红色效果；
     * 也支持 `accent` / `success` / `warning`，便于在调用方按需选用。
     */
    variant?: InlineTipCardVariant;
    /** 操作按钮文案（如「重试」）；不传则不显示操作按钮。 */
    actionLabel?: string;
    /** 点击操作按钮时的回调（如重新发起请求）。 */
    onAction?: () => void;
    /** 点击关闭按钮时的回调（如清空错误状态、隐藏告警）。 */
    onDismiss?: () => void;
}

/**
 * 与 Toast.tsx 对齐的 variant 样式表：
 *   - bg      ：外层 AnimCard 的实色背景（用作主题色边/底）
 *   - surface ：上层内容区背景（elevated 卡片，营造"上下两层、内层左侧内缩 2px"的边带效果）
 *   - icon    ：头部图标 + title 的语义色（前景色）
 *   - title   ：title 字色（与 icon 同色，更强语义）
 *
 * 注意：bg/surface/icon/title 字段语义与 Toast.tsx 对齐，便于两个组件视觉同步。
 */
const variantStylesConfig: Record<InlineTipCardVariant, {
    bg: string;
    surface: string;
    icon: string;
    title: string;
}> = {
    default: {
        bg: 'bg-subtle',
        surface: 'bg-elevated/95',
        icon: 'text-secondary-text',
        title: 'text-foreground',
    },
    accent: {
        bg: 'bg-primary',
        surface: 'bg-elevated/95',
        icon: 'text-primary',
        title: 'text-primary',
    },
    success: {
        bg: 'bg-success',
        surface: 'bg-elevated/95',
        icon: 'text-success',
        title: 'text-success',
    },
    warning: {
        bg: 'bg-warning',
        surface: 'bg-elevated/95',
        icon: 'text-warning',
        title: 'text-warning',
    },
    danger: {
        bg: 'bg-danger',
        surface: 'bg-elevated/95',
        icon: 'text-danger',
        title: 'text-danger',
    },
};

/**
 * variant 对应的 alert role：危险/警告用 `alert`（即时播报），其余用 `status`。
 */
const alertRoleFor = (variant: InlineTipCardVariant): 'alert' | 'status' =>
    variant === 'danger' || variant === 'warning' ? 'alert' : 'status';

/**
 * API 错误告警组件。
 * 负责把解析后的错误信息以一致、可读、可折叠详情的样式呈现给用户。
 *
 * 重构说明（参考 Toast.tsx:214-293 的视觉结构）：
 *   - 外层 AnimCard 用作"实色语义色"垫片，覆盖 AnimCard 自带的 `bg-card border border-subtle min-h-[110px]`；
 *   - 内层 elevated 卡片整体内缩 2px（`ml-[2px]`），仅露出外层的左+上侧一条语义色边；
 *   - 头部：title（语义色字） + 右侧关闭按钮；
 *   - 主体：description + 查看详情 + 右侧 action 按钮；
 *   - 详情：用 state 控制展开/收起（与 Toast 一致；不再使用浏览器原生 <details>，便于控制动画与样式）。
 */
export const InlineTipCard: React.FC<InlineTipCardProps> = ({
    error,
    className = '',
    variant = 'default',
    actionLabel,
    onAction,
    onDismiss,
}) => {
    const { t } = useUiLanguage();
    // 选择当前 variant 的样式（与 Toast.tsx 中的 variantStyles 字段名一一对应）。
    const variantStyles = variantStylesConfig[variant];

    // 是否展示「详细信息」展开面板：
    // 仅当原始报错信息存在，且与给用户看的 message 文案不一致时才展示，
    // 避免展示与提示文案重复、无意义的内容。
    const showDetails = !!error.rawMessage.trim() && error.rawMessage.trim() !== error.message.trim();
    // 详情面板展开状态（默认收起）。
    const [detailsOpen, setDetailsOpen] = useState(false);

    // 当传入 onDismiss 时，渲染右侧图标关闭按钮（参考 Toast.tsx 的关闭按钮样式）。
    const showDismiss = !!onDismiss;

    return (
        // 最外层：AnimCard 作为"实色语义色"背景垫片，
        // 使用 `!min-h-0 border-none` 覆盖 AnimCard 默认的 `min-h-[110px]` 与 `border border-subtle`，
        // 再叠加 `variantStyles.bg` 把整个外层涂成 variant 语义色（同时也是"边带"）。
        <AnimCard
            className={cn(
                'hrs-api-error-alert relative w-full !min-h-0 overflow-hidden rounded-md shadow-sm border-none backdrop-blur',
                variantStyles.bg,
                className
            )}
        >
            {/*
                上层内容卡片（elevated 半透明）：
                  - 整体 `ml-[2px]`，与外层右上/下边缘对齐，露出左+上 2px 的语义色边带；
                  - `min-w-0` 防止内部 flex 子项把容器撑爆；
                  - `variantStyles.surface` 给内层加 elevated 背景，使其与外层形成层次。
            */}
            <div
                role={alertRoleFor(variant)}
                className={cn(
                    'flex w-full min-w-0 flex-col rounded-md ml-[2px] px-4 py-2 gap-1',
                    variantStyles.surface
                )}
            >
                {/*
                    头部：title（语义色字） + 右侧图标关闭按钮（参考 Toast.tsx）。
                    注：此处未复刻 Toast 的"图标圆圈"，以保持 InlineTipCard 的轻量内联风格。
                */}
                <div className="flex items-center gap-2.5">
                    {/* title 块，flex-1 占满剩余空间，truncate 防止溢出 */}
                    <div className="min-w-0 flex-1">
                        <p className={cn('truncate text-sm font-semibold leading-5', variantStyles.title)}>
                            {error.title}
                        </p>
                    </div>

                    {/* 关闭按钮（图标）：复用 Toast.tsx 的样式与 CloseIcon */}
                    {showDismiss ? (
                        <button
                            type="button"
                            aria-label={t('common.close')}
                            onClick={onDismiss}
                            className="shrink-0 inline-flex h-6 w-6  rounded-md  items-center justify-center 
                            text-muted-text/60 transition-colors hover:bg-surface-2 hover:text-muted-text
                            focus:outline-none"
                        >
                            <CloseIcon className="h-3.5 w-3.5" />
                        </button>
                    ) : null}
                </div>

                {/*
                    主体：description + 查看详情 + 右侧 action 按钮（若提供）。
                    左缩进 `pl-[34px]` 与头部图标宽度（24 + 8 gap + 2 左内缩 = 34）对齐，让 description 与 title 同样从图标后开始。
                */}
                <div className="flex items-center gap-3">
                    <div className="min-w-0 flex-1">
                        {/* 给用户看的友好文案：与 Toast 一致用 muted-text + line-clamp-3，避免单条 toast/alert 占太高 */}
                        <p className="line-clamp-3 text-xs leading-4 text-muted-text">{error.message}</p>

                        {showDetails ? (
                            <button
                                type="button"
                                onClick={() => setDetailsOpen((v) => !v)}
                                className={cn(
                                    'mt-1 inline-flex items-center gap-1 text-xs font-medium transition',
                                    variantStyles.icon,
                                    'hover:opacity-80'
                                )}
                                aria-expanded={detailsOpen}
                            >
                                <span className="text-xs leading-4">
                                    {/* 收起/展开都用 i18n 的「详情」文案，保持简单；状态由箭头旋转表达 */}
                                    {t('common.details')}
                                </span>
                                <svg
                                    viewBox="0 0 12 12"
                                    fill="none"
                                    className={cn('h-3 w-3 transition-transform', detailsOpen && 'rotate-180')}
                                    stroke="currentColor"
                                    strokeWidth="1.6"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    aria-hidden="true"
                                >
                                    <path d="M3 4.5l3 3 3-3" />
                                </svg>
                            </button>
                        ) : null}
                    </div>

                    {/* 操作按钮（如「重试」）：同时提供 actionLabel 与 onAction 才渲染，复用项目统一 HrsButton */}
                    {actionLabel && onAction ? (
                        <HrsButton
                            variant={CARD_BUTTON_VARIANT_MAPPING[variant]}
                            size="sm"
                            onClick={onAction}
                            className={cn( 'shrink-0',)}
                        >
                            {actionLabel}
                        </HrsButton>
                    ) : null}
                </div>

                {/*
                    详情展开区：仅在 showDetails && detailsOpen 时显示。
                    与 Toast 一致：用带边框/背景的容器包住 <pre>，并允许长字符串折行。
                */}
                {showDetails && detailsOpen ? (
                    <div className="rounded-md border border-border/60 bg-surface-2/60 px-2 py-1">
                        <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-muted-text">
                            {error.rawMessage}
                        </pre>
                    </div>
                ) : null}
            </div>
        </AnimCard>
    );
};
