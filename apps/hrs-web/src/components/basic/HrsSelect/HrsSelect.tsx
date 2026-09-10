/**
 * HrsSelect —— 基于 HeroUI v3 Select 的声明式下拉选择器。
 * 使用方仅通过统一 options 入参（扁平 / 分组由数据结构动态解析）与
 * HeroUI 规格基础入参（value / onChange / placeholder / selectionMode …）驱动，
 * 无需关心 Label / Trigger / Popover / ListBox 的组装。
 *
 * - 分组识别：含 options 数组的项即渲染为分组（title 标题 + 自动插入分隔线）；
 * - 样式全部基于 Tailwind 与主题 token，未新建样式类；
 * - 支持 xs~lg 四档尺寸、单选项 disabled、自定义渲染 renderItem、空态与错误提示。
 *
 * @example
 * ```tsx
 * // 基础用法（受控单选，disabled 选项无法被选中）
 * <HrsSelect
 *   label="市场"
 *   placeholder="请选择市场"
 *   options={[
 *     { key: 'a', label: 'A 股' },
 *     { key: 'hk', label: '港股', disabled: true },
 *     { key: 'us', label: '美股' },
 *   ]}
 *   value={market}
 *   onChange={(value) => setMarket(value as string)}
 * />
 *
 * // 分组选项：同样通过 options 传入（含 options 数组即识别为分组），
 * // 每个分组有 title，分组间自动用 <Separator /> 分隔，子项同样支持 disabled
 * <HrsSelect
 *   label="国家"
 *   selectionMode="multiple"
 *   options={[
 *     {
 *       key: 'asia',
 *       title: '亚洲',
 *       options: [
 *         { key: 'cn', label: '中国' },
 *         { key: 'jp', label: '日本', disabled: true },
 *       ],
 *     },
 *     { key: 'europe', title: '欧洲', options: [{ key: 'uk', label: '英国' }] },
 *   ]}
 * />
 * ```
 *
 * @author Lensgcx (GaoCangxiong)
 */

import React from 'react';
import {
    Header,
    Label,
    ListBox,
    Select as HeroSelect,
    type Key,
} from '@heroui/react';
import { cn } from '../../../utils/cn';
import { Chip } from '../Chip';
import { Separator } from '../Separator';

/** 空态占位项的 key，仅当数据源为空时以禁用项形式渲染 */
const EMPTY_OPTION_KEY = '__hrs_select_empty__';

/** 尺寸档位 */
export type HrsSelectSize = 'xs' | 'sm' | 'md' | 'lg';

/**
 * 扁平选项数据结构。
 * disabled 为 true 时该选项不可被选中（由数据驱动）。
 */
export interface HrsSelectOptionDef {
    /** 选项唯一标识（对应 HeroUI ListBox.Item 的 id / value） */
    key: Key;
    /** 选项显示文本 */
    label: string;
    /** 是否禁用该选项（可选）；禁用后不可选中且降透明度 */
    disabled?: boolean;
}

/**
 * 分组选项数据结构。title 渲染为分组 Header，
 * 每个分组之前由组件自动插入分隔线（首个之前不插入）。
 */
export interface HrsSelectSectionDef {
    /** 分组唯一标识 */
    key: string;
    /** 分组标题（渲染为分组 Header，可选） */
    title?: string;
    /** 该分组下的选项列表 */
    options: HrsSelectOptionDef[];
}

/** 统一数据入口：扁平项与分组项可任意组合，由数据结构动态解析 */
export type HrsSelectDataSourceDef = Array<HrsSelectOptionDef | HrsSelectSectionDef>;

/**
 * 判断列表项是否为分组项。
 * @param item - 待判断的列表项（扁平项 HrsSelectOptionDef 或分组项 HrsSelectSectionDef）
 * @returns 为分组项时返回 true，并作为类型谓词将 item 收窄为 HrsSelectSectionDef
 */
const isSelectSection = (
    item: HrsSelectOptionDef | HrsSelectSectionDef,
): item is HrsSelectSectionDef => 'options' in item && Array.isArray(item.options);

/** HrsSelect 组件属性 */
export interface HrsSelectProps {
    // ============ 组件自有字段（内部消费 / 加工） ============
    /**
     * 统一选项数据入口：扁平项与分组项可任意组合，
     * 含 options 数组的项识别为分组（渲染 title 与分隔线）。
     */
    options?: HrsSelectDataSourceDef;
    /** 标签文本（显示在触发器上方，可选） */
    label?: string;
    /** 辅助说明文本（显示在触发器下方，可选） */
    description?: string;
    /** 错误提示文本（配合 isInvalid 使用，可选） */
    errorMessage?: string;
    /** 占位符文本，默认 '请选择' */
    placeholder?: string;
    /** 尺寸档位（控制触发器高度与字号），默认 'sm' */
    size?: HrsSelectSize;
    /** 视觉变体：primary 带阴影，secondary 低强调（适合卡片内），默认 'primary' */
    variant?: 'primary' | 'secondary';
    /** 单选 / 多选模式，默认 'single' */
    selectionMode?: 'single' | 'multiple';
    /**
     * 多选时是否以「折叠标签」形式展示选中值，默认 true。
     * 仅 selectionMode === 'multiple' 时生效：
     * - true：触发器显示「首个选中标签（自带 × 移除）+ 其余数量 + N」，例如 A/B/C 显示 `A + 2`；
     * - false：使用 HeroUI 默认 chip 多选标签（每个自带 ×）。
     */
    collapseTags?: boolean;
    /** 当前选中值（受控，HeroUI 规格：Key | Key[] | null） */
    value?: Key | Key[] | null;
    /** 默认选中值（非受控，HeroUI 规格） */
    defaultValue?: Key | Key[] | null;
    /** 选中值变更回调（HeroUI 规格：单选返回 Key | null，多选返回 Key[]） */
    onChange?: (value: Key | Key[] | null) => void;
    /** 是否占满父容器宽度（HeroUI 规格），默认 true */
    fullWidth?: boolean;
    /** 自定义选项渲染函数（入参为单个选项，返回选项主内容，可选） */
    renderItem?: (option: HrsSelectOptionDef) => React.ReactNode;
    /** 根元素（Label + 触发器 + 提示文本）追加的 className */
    className?: string;
    /** 下拉弹层追加的 className */
    popoverClassName?: string;

    // ============ 透传给 HeroUI Select 的基础入参 ============
    // 以下字段不做加工，统一经 ...heroProps 透传，语义与 HeroUI Select 一致。
    disabledKeys?: Iterable<Key>;
    isDisabled?: boolean;
    isRequired?: boolean;
    isInvalid?: boolean;
    isOpen?: boolean;
    defaultOpen?: boolean;
    onOpenChange?: (isOpen: boolean) => void;
    name?: string;
    autoComplete?: string;
}

/**
 * 各尺寸触发器样式（高度 / 圆角 / 内边距 / 字号）。
 * 注：HeroUI 的 .select__trigger 自带 min-h-9，CSS 中 min-height 会钳制 height，
 * 因此每档必须同步声明匹配的 min-h-*；圆角随尺寸缩放（小尺寸小圆角）。
 */
const SIZE_TRIGGER_STYLES: Record<HrsSelectSize, string> = {
    xs: 'h-7 min-h-7 rounded-sm px-2.5 py-1 text-xxs',
    sm: 'h-8 min-h-8 rounded-sm px-2.5 py-1.5 text-xs',
    md: 'h-9 min-h-9 rounded-sm px-3 text-sm',
    lg: 'h-10 min-h-10 rounded-md px-3.5 text-sm',
};

/** 各尺寸下拉弹层圆角，与触发器同档保证视觉连贯 */
const SIZE_POPOVER_STYLE: Record<HrsSelectSize, string> = {
    xs: 'rounded-sm',
    sm: 'rounded-sm',
    md: 'rounded-sm',
    lg: 'rounded-md',
};

/**
 * 触发器基础样式（边框 / 悬浮 / 键盘焦点反馈，基于主题 token）。
 * 必须带 items-center：HeroUI 的 .select__trigger 未声明垂直对齐，
 * 固定高度下文字会顶部对齐，导致与绝对定位的箭头错位。
 */
const TRIGGER_BASE_STYLES =
    'flex w-full items-center border border-border bg-transparent text-foreground transition-colors hover:border-primary/40 data-[focus-visible=true]:border-primary/60 data-[focus-visible=true]:ring-2 data-[focus-visible=true]:ring-primary/15 data-[disabled=true]:cursor-not-allowed data-[disabled=true]:opacity-50';

/** 下拉弹层基础样式：边框 / 背景 / 阴影（圆角由 SIZE_POPOVER_STYLE 决定） */
const POPOVER_STYLES =
    'border border-border bg-popover p-1 shadow-lg';

/**
 * 选项基础样式：圆角 / 悬浮高亮 / 选中主色 / 禁用降透明度。
 * 注：react-aria hover 仅打 data-hovered=true 而非 data-focused=true，
 * 须同时挂 data-[hovered=true]:bg-primary-faint，否则 dark 主题下 hover 会闪白
 * （HeroUI 默认 hover 背景偏浅，与深色背景冲突）。
 */
const ITEM_STYLES =
    'rounded-sm px-2 py-1.5 text-foreground bg-transparent hover:bg-primary-faintdata-[hovered=true]:bg-primary-faint data-[focused=true]:bg-primary-faint data-[selected=true]:text-primary data-[disabled=true]:cursor-not-allowed data-[disabled=true]:opacity-50';

/** 选中指示器（打钩）：主色 + 展开时旋转 */
const ITEM_INDICATOR_STYLES =
    'text-primary transition-transform duration-200';

/** 分组标题样式 */
const SECTION_HEADER_STYLES =
    'px-2 py-1.5 text-xs font-medium text-muted-text';

/** 标签样式（触发器上方） */
const LABEL_STYLES = 'text-xs font-medium text-muted-text';

/** 辅助说明样式（触发器下方） */
const DESCRIPTION_STYLES = 'text-xs text-muted-text';

/** 错误提示样式（触发器下方） */
const ERROR_MESSAGE_STYLES = 'text-xs text-danger';

/**
 * 将单个扁平选项渲染为 HeroUI ListBox.Item。
 * @param option - 单个扁平选项数据 HrsSelectOptionDef
 * @param renderItem - 可选自定义渲染函数；传入则用它渲染选项主内容，否则显示 label
 * @returns ListBox.Item 元素
 */
const renderOption = (
    option: HrsSelectOptionDef,
    renderItem?: HrsSelectProps['renderItem'],
): React.ReactElement => (
    <ListBox.Item
        key={option.key}
        id={option.key}
        textValue={option.label}
        // disabled 桥接为 HeroUI 的 isDisabled，由 react-aria 保证禁用项不可选中
        isDisabled={option.disabled}
        className={ITEM_STYLES}
    >
        {renderItem ? renderItem(option) : option.label}
        {/* 选中指示器（勾选图标），沿用 HeroUI 默认图标仅追加样式 */}
        <ListBox.ItemIndicator className={ITEM_INDICATOR_STYLES} />
    </ListBox.Item>
);

/**
 * 渲染一个分组（可选 title + 该组全部选项）。
 * @param section - 分组数据 HrsSelectSectionDef
 * @param renderItem - 可选自定义渲染函数，透传给分组内每一项
 * @returns ListBox.Section 元素
 */
const renderSection = (
    section: HrsSelectSectionDef,
    renderItem?: HrsSelectProps['renderItem'],
): React.ReactElement => (
    <ListBox.Section key={section.key}>
        {section.title && (
            <Header className={SECTION_HEADER_STYLES}>{section.title}</Header>
        )}
        {section.options.map((option) => renderOption(option, renderItem))}
    </ListBox.Section>
);

/**
 * 把 options 动态解析为 ListBox 子元素。
 * @param dataSource - 统一选项数据（扁平项与分组项任意组合）
 * @param renderItem - 可选自定义渲染函数，透传给每个选项
 * @returns ListBox 子元素数组（顺序为 Item / Section，分组之间插入 Separator）
 */
const buildListBoxChildren = (
    dataSource: HrsSelectDataSourceDef,
    renderItem?: HrsSelectProps['renderItem'],
): React.ReactNode[] => {
    const children: React.ReactNode[] = [];

    dataSource.forEach((item) => {
        if (isSelectSection(item)) {
            // 非首个渲染元素前插入分隔线；
            // mx-2 与选项 px-2 对齐（水平居中），w-auto 覆盖默认 w-full 避免叠加 margin 溢出
            if (children.length > 0) {
                children.push(
                    <Separator key={`${item.key}__separator`} className="w-auto" gradient />,
                );
            }
            children.push(renderSection(item, renderItem));
        } else {
            children.push(renderOption(item, renderItem));
        }
    });

    return children;
};

export const HrsSelect: React.FC<HrsSelectProps> = ({
    className,
    popoverClassName,
    options,
    value,
    label,
    placeholder = '请选择',
    size = 'sm',
    variant = 'primary',
    selectionMode = 'single',
    collapseTags = true,
    fullWidth = true,
    description,
    errorMessage,
    defaultValue,
    onChange,
    renderItem,
    // 其余 HeroUI Select 规格基础入参统一收集后透传给内部 HeroSelect
    ...heroProps
}) => {
    // 数据源为空时，弹层内展示占位提示
    const isEmpty = !options || options.length === 0;

    // 多选折叠标签：不走 Select.Value 函数子节点（其拿到的是 RAC 渲染状态对象而非条目数组），
    // 改为在 trigger 内直接渲染；空值显示 placeholder。
    /**
     * 根据选项 key 从 options 查出对应的显示文本 label。
     * @param k - 选项 key（扁平项或分组子项的 key）
     * @returns 对应的 label；找不到时回退为 String(k)
     */
    const getLabelByKey = (k: Key): string => {
        if (!options) return String(k);
        for (const item of options) {
            if ('options' in item && Array.isArray(item.options)) {
                for (const sub of item.options) {
                    if (sub.key === k) return sub.label;
                }
            } else if (
                'key' in item &&
                (item as HrsSelectOptionDef).key === k
            ) {
                return (item as HrsSelectOptionDef).label;
            }
        }
        return String(k);
    };
    /**
     * 渲染多选折叠态的触发器内容。
     * @returns 空值显示 placeholder；否则返回「首个选中 Chip（带 × 移除该项）+ 其余数量 + N」
     */
    const renderCollapsedValue = (): React.ReactNode => {
        const keys =
            selectionMode === 'multiple' && Array.isArray(value)
                ? (value as Key[])
                : [];
        // Chip 的 onClose 不带事件参数；内置关闭按钮已 stopPropagation(click)
        const removeFirst = () => {
            onChange?.(keys.slice(1));
        };
        if (keys.length === 0) {
            return (
                <span className="gcxgcxgcxg truncate text-base text-muted-text sm:text-sm">{placeholder}</span>
            );
        }
        const firstLabel = getLabelByKey(keys[0]);
        const restCount = keys.length - 1;
        return (
            <span className="flex min-w-0 flex-1 items-center gap-1">
                {/* 首个选中项：Chip 渲染，onClose 即内嵌 ×（移除该项） */}
                <Chip size={size} radius="sm" variant="secondary" onClose={removeFirst}>
                    <span className="min-w-0 truncate">{firstLabel}</span>
                </Chip>
                {/* 其余选中数量：+ N（无 ×） */}
                {restCount > 0 && (
                    <Chip size={size} radius="sm" variant="secondary">
                        + {restCount}
                    </Chip>
                )}
            </span>
        );
    };

    return (
        <HeroSelect
            // HeroUI 规格基础入参（直接透传）
            placeholder={placeholder}
            // 可访问性兜底：无可见 label 时用 placeholder 作为 aria-label，
            // 避免 HeroUI 报「must specify aria-label / aria-labelledby」
            {...(!label ? { 'aria-label': placeholder } : {})}
            selectionMode={selectionMode}
            value={value}
            defaultValue={defaultValue}
            onChange={onChange}
            variant={variant}
            {...heroProps}
            fullWidth={fullWidth}
            className={cn('hrs-select w-50', className)}
        >
            {/* 标签 */}
            {label && <Label className={LABEL_STYLES}>{label}</Label>}

            {/* 触发器 */}
            <HeroSelect.Trigger className={cn('hrs-select-trigger', TRIGGER_BASE_STYLES, SIZE_TRIGGER_STYLES[size])}>
                {/* 多选折叠标签：文字 + 内嵌 × */}
                {selectionMode === 'multiple' && collapseTags
                    ? renderCollapsedValue()
                    : <HeroSelect.Value className="data-[placeholder=true]:text-muted-text" />}
                {/* 展开箭头 */}
                <HeroSelect.Indicator className="transition-transform duration-200 data-[open=true]:rotate-180" />
            </HeroSelect.Trigger>

            {/* 下拉弹层 */}
            <HeroSelect.Popover className={cn('hrs-select-popover', SIZE_POPOVER_STYLE[size], POPOVER_STYLES, popoverClassName)}>
                <ListBox selectionMode={selectionMode}>
                    {isEmpty ? (
                        /* 空态：以禁用项形式展示提示文案 */
                        <ListBox.Item
                            key={EMPTY_OPTION_KEY}
                            id={EMPTY_OPTION_KEY}
                            textValue={placeholder}
                            isDisabled
                            className="cursor-default px-2 py-3 text-center text-xs text-muted-text"
                        >
                            {placeholder}
                        </ListBox.Item>
                    ) : (
                        /* 扁平 / 分组由数据结构动态解析：含 options 数组识别为分组，否则为普通选项 */
                        buildListBoxChildren(options!, renderItem)
                    )}
                </ListBox>
            </HeroSelect.Popover>

            {/* 辅助说明（可选）；存在错误提示时优先展示错误提示 */}
            {description && !errorMessage && (
                <p className={DESCRIPTION_STYLES}>{description}</p>
            )}
            {errorMessage && <p className={ERROR_MESSAGE_STYLES}>{errorMessage}</p>}
        </HeroSelect>
    );
};
