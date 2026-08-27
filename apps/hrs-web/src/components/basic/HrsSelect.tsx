/**
 * HrsSelect.tsx
 * ------------------------------------------------------------
 * 组件名称：HrsSelect（通用下拉选择器）
 *
 * 作用：
 *   基于 HeroUI v3 Select 二次封装的声明式下拉选择器。使用方只需通过统一的
 *   options 入参传入选项数据（扁平或分组均可，由数据结构动态解析）与
 *   HeroUI 规格的基础入参（value / onChange / placeholder / selectionMode
 *   等），无需关心内部 Label、Trigger、Popover、ListBox 的组装细节。
 *
 * 描述：
 *   - 统一数据入口 options：既支持扁平选项 HrsSelectOptionDef[]，也支持分组
 *     选项 HrsSelectSectionDef[]（甚至两者混用），组件根据每一项的数据结构
 *     动态解析：含 options 数组的项识别为分组，渲染分组标题（title）
 *     并在每个分组前自动插入 <Separator /> 分割线，使用方无需手写；
 *   - 基础入参遵循 HeroUI Select 规格：value / defaultValue / onChange /
 *     placeholder / selectionMode / isDisabled / isRequired / isInvalid /
 *     disabledKeys / isOpen / onOpenChange / variant / fullWidth 等；
 *   - 内部样式全部基于 Tailwind 工具类与项目主题色 token（primary /
 *     border / muted-text / danger 等），未新建任何样式类；
 *   - 支持 xs / sm / md / lg 四档尺寸（控制触发器高度与字号）、
 *     单个选项禁用（disabled，禁用项无法被选中）、自定义选项渲染
 *     （renderItem）、空态提示、错误提示（isInvalid + errorMessage）等常用能力。
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
 * // 分组选项：同样通过 options 传入（数据结构含 options 数组即识别为分组），
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
 * ------------------------------------------------------------
 */

import React from 'react';
import {
    Header,
    Label,
    ListBox,
    Select as HeroSelect,
    type Key,
} from '@heroui/react';
import { cn } from '../../utils/cn';
import { Separator } from './Separator';

/** 空态占位选项的 key（仅当下拉无任何可选项时渲染，标识为禁用避免被选中） */
const EMPTY_OPTION_KEY = '__hrs_select_empty__';

/** 尺寸档位 */
export type HrsSelectSize = 'xs' | 'sm' | 'md' | 'lg';

/**
 * 下拉选项的数据结构（扁平项）。
 * disabled 为 true 的选项无法被选中（由数据结构驱动）。
 */
export interface HrsSelectOptionDef {
    /** 选项唯一标识（对应 HeroUI ListBox.Item 的 id / value） */
    key: Key;
    /** 选项显示文本 */
    label: string;
    /** 是否禁用该选项（可选）：禁用后无法被选中，展示降透明度样式 */
    disabled?: boolean;
}

/**
 * 分组选项的数据结构（分组项）。
 * 分组完全由数据结构驱动渲染：title 渲染为分组标题（Header），
 * 每个分组之前由组件内部自动插入 <Separator /> 分割线
 * （首个渲染元素之前不插入）。
 */
export interface HrsSelectSectionDef {
    /** 分组唯一标识 */
    key: string;
    /** 分组标题（渲染为分组 Header，可选） */
    title?: string;
    /** 该分组下的选项列表 */
    options: HrsSelectOptionDef[];
}

/** 统一的选项数据入口：扁平项与分组项可任意组合，由数据结构动态解析 */
export type HrsSelectDataSourceDef = Array<HrsSelectOptionDef | HrsSelectSectionDef>;

/**
 * 数据结构解析：判断传入项是否为分组项。
 * 含 options 数组的项识别为分组，否则视为扁平选项。
 */
const isSelectSection = (
    item: HrsSelectOptionDef | HrsSelectSectionDef,
): item is HrsSelectSectionDef => 'options' in item && Array.isArray(item.options);

/**
 * HrsSelect 组件属性。
 * 基础入参遵循 HeroUI Select 规格（value / onChange / placeholder /
 * selectionMode / isDisabled / isRequired / isInvalid / disabledKeys 等），
 * 并在此基础上扩展了统一数据源（options）与布局、提示类字段。
 */
export interface HrsSelectProps {
    // ============ 组件自有的语义化字段（由组件内部消费 / 加工） ============
    /**
     * 统一选项数据入口：扁平项（HrsSelectOptionDef）与分组项（HrsSelectSectionDef）
     * 可任意组合，组件根据每一项的数据结构动态解析渲染；
     * 含 options 数组的项识别为分组（渲染 title 分组标题与分割线）。
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
    /** 视觉变体：primary 带阴影，secondary 低强调（适合放在卡片内），默认 'primary' */
    variant?: 'primary' | 'secondary';
    /** 单选 / 多选模式，默认 'single' */
    selectionMode?: 'single' | 'multiple';
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
    // 以下字段组件内部不做任何加工，统一通过 ...heroProps 透传给底层 HeroSelect，
    // 语义与 HeroUI Select 完全一致（禁用项 / 禁用态 / 必填 / 非法 / 弹层展开等）。
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
 * 各尺寸档位对应的触发器样式（高度、圆角、水平内边距、字号）。
 * 注 1：HeroUI 的 .select__trigger 自带 min-h-9，CSS 中 min-height 会钳制
 * height（即使 height 加 !important 也无效），因此每档必须同步声明
 * 匹配的 min-h-* 才能让 xs / sm 档真正生效。
 * 注 2：圆角随尺寸缩放（小尺寸小圆角，与 Modal 的 SIZE_RADIUS_MAP 同思路）。
 */
const SIZE_TRIGGER_STYLES: Record<HrsSelectSize, string> = {
    xs: 'h-7 min-h-7 rounded-sm px-2.5 py-1 text-xxs',
    sm: 'h-8 min-h-8 rounded-sm px-2.5 py-1.5 text-xs',
    md: 'h-9 min-h-9 rounded-sm px-3 text-sm',
    lg: 'h-10 min-h-10 rounded-md px-3.5 text-sm',
};

/**
 * 各尺寸档位对应的下拉弹层圆角。
 * 与 SIZE_TRIGGER_STYLES 的触发器圆角同档，保证展开时视觉连贯。
 */
const SIZE_POPOVER_STYLE: Record<HrsSelectSize, string> = {
    xs: 'rounded-sm',
    sm: 'rounded-sm',
    md: 'rounded-sm',
    lg: 'rounded-md',
};

/**
 * 触发器基础样式：边框、悬浮与键盘焦点反馈（全部基于主题色 token）。
 * 注：必须带 items-center —— HeroUI 的 .select__trigger 未声明垂直对齐
 * （flex 默认 stretch），固定高度下文字会顶部对齐；箭头指示器是
 * absolute + my-auto 自行居中的，不补齐会导致文字与箭头错位。
 */
const TRIGGER_BASE_STYLES =
    'flex w-full items-center border border-border bg-transparent text-foreground transition-colors hover:border-primary/40 data-[focus-visible=true]:border-primary/60 data-[focus-visible=true]:ring-2 data-[focus-visible=true]:ring-primary/15 data-[disabled=true]:cursor-not-allowed data-[disabled=true]:opacity-50';

/** 下拉弹层基础样式：边框、背景与阴影（圆角由 SIZE_POPOVER_STYLE 按尺寸映射） */
const POPOVER_STYLES =
    'border border-border bg-popover p-1 shadow-lg';

/** 选项基础样式：圆角、悬浮高亮、选中态主色文字、禁用态降透明度
 * 重要：鼠标 hover 项时 react-aria 仅给元素打 data-hovered=true 而非 data-focused=true，
 * 若只设置 data-[focused=true]:bg-primary-faint，鼠标悬浮态会用 HeroUI 默认 hover 背景
 * （dark 主题下偏浅色），会与深色背景产生一次「白色一闪」的切换。
 * 因此同时挂 data-[hovered=true]:bg-primary-faint，让 hover 态由项目主题色接管。 */
const ITEM_STYLES =
    'rounded-sm px-2 py-1.5 text-foreground bg-transparent hover:bg-primary-faintdata-[hovered=true]:bg-primary-faint data-[focused=true]:bg-primary-faint data-[selected=true]:text-primary data-[disabled=true]:cursor-not-allowed data-[disabled=true]:opacity-50';

/** 选中指示器样式（选中 - 打钩）：主色 + 展开时旋转 */
const ITEM_INDICATOR_STYLES =
    'text-primary transition-transform duration-200';

/** 分组标题样式 */
const SECTION_HEADER_STYLES =
    'px-2 py-1.5 text-xs font-medium text-muted-text';

/** 标签样式（触发器上方） */
const LABEL_STYLES = 'text-xs font-medium text-muted-text';

/** 辅助说明文本样式（触发器下方） */
const DESCRIPTION_STYLES = 'text-xs text-muted-text';

/** 错误提示文本样式（触发器下方） */
const ERROR_MESSAGE_STYLES = 'text-xs text-danger';

/**
 * 渲染单个选项。
 *
 * 内部负责把 HrsSelectOptionDef 转换为 HeroUI ListBox.Item：
 * 普通选项渲染主文本，也支持通过 renderItem 完全自定义主内容。
 *
 * @param option - 选项数据
 * @param renderItem - 使用方传入的自定义渲染函数（可选）
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
        // 数据字段 disabled 桥接为 HeroUI 的 isDisabled，
        // 由 react-aria 保证禁用项无法被选中（鼠标 / 键盘均不可选）
        isDisabled={option.disabled}
        className={ITEM_STYLES}
    >
        {renderItem ? renderItem(option) : option.label}
        {/* 选中指示器（勾选图标），保持 HeroUI 默认图标、仅追加样式 */}
        <ListBox.ItemIndicator className={ITEM_INDICATOR_STYLES} />
    </ListBox.Item>
);

/**
 * 渲染一个分组（可选标题 + 该组全部选项）。
 *
 * @param section - 分组数据
 * @param renderItem - 使用方传入的自定义渲染函数（可选）
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
 * 统一数据入口的动态解析：把 options 数据转换为 ListBox 的子元素列表。
 *
 * 解析规则（完全由数据结构驱动）：
 *   - 分组项（含 options 数组）→ 渲染 ListBox.Section（可选 title 标题 + 子项），
 *     且每个非首元素分组前自动插入 <Separator /> 分割线；
 *   - 扁平项 → 直接渲染 ListBox.Item。
 *
 * @param dataSource - 统一选项数据（扁平项 / 分组项可任意组合）
 * @param renderItem - 使用方传入的自定义渲染函数（可选）
 * @returns ListBox 子元素数组：[Item, Section, Separator, Section, ...]
 */
const buildListBoxChildren = (
    dataSource: HrsSelectDataSourceDef,
    renderItem?: HrsSelectProps['renderItem'],
): React.ReactNode[] => {
    const children: React.ReactNode[] = [];

    dataSource.forEach((item) => {
        if (isSelectSection(item)) {
            // 分组项：非首个渲染元素前插入分割线
            // mx-2 与选项 px-2 对齐（左右对称内缩即水平居中）；
            // w-auto 覆盖组件默认 w-full，避免满宽叠加 margin 溢出
            if (children.length > 0) {
                children.push(
                    <Separator key={`${item.key}__separator`} className="w-auto" gradient />,
                );
            }
            children.push(renderSection(item, renderItem));
        } else {
            // 扁平项
            children.push(renderOption(item, renderItem));
        }
    });

    return children;
};

/**
 * 通用下拉选择器组件（声明式）。
 *
 * 内部组装 HeroUI Select 的 Label / Trigger / Popover / ListBox 结构，
 * 使用方只需通过统一的 options 入参传入数据与 HeroUI 规格的基础入参即可，
 * 扁平 / 分组由数据结构动态解析。
 */
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
    fullWidth = true,
    description,
    errorMessage,
    defaultValue,
    onChange,
    renderItem,
    // 其余 HeroUI Select 规格的基础入参（disabledKeys / isDisabled /
    // isRequired / isInvalid / isOpen / defaultOpen / onOpenChange / name /
    // autoComplete 等）统一收集后透传给内部 HeroSelect
    ...heroProps
}) => {
    // 是否无任何可选项（数据源为空时在弹层内展示占位提示）
    const isEmpty = !options || options.length === 0;

    return (
        <HeroSelect
            // ---- HeroUI 规格的基础入参（直接透传） ----
            placeholder={placeholder}
            // 可访问性兜底：无可见 label 时，用 placeholder 作为 aria-label，
            // 避免 HeroUI 报「must specify aria-label / aria-labelledby」；
            // 若调用方通过 heroProps 显式传入 aria-label / aria-labelledby，会覆盖此兜底。
            {...(!label ? { 'aria-label': placeholder } : {})}
            selectionMode={selectionMode}
            value={value}
            defaultValue={defaultValue}
            onChange={onChange}
            variant={variant}
            {...heroProps}
            fullWidth={fullWidth}
            className={cn('hrs-select', className)}
        >
            {/* 标签（可选） */}
            {label && <Label className={LABEL_STYLES}>{label}</Label>}

            {/* 触发器：选中值 + 下拉箭头指示器 */}
            <HeroSelect.Trigger className={cn('hrs-select-trigger', TRIGGER_BASE_STYLES, SIZE_TRIGGER_STYLES[size])}>
                <HeroSelect.Value />
                {/* 箭头指示器：展开时旋转 180° */}
                <HeroSelect.Indicator className="transition-transform duration-200 data-[open=true]:rotate-180" />
            </HeroSelect.Trigger>

            {/* 下拉弹层：统一数据入口动态解析（扁平项 / 分组项 / 空态提示） */}
            <HeroSelect.Popover className={cn('hrs-select-popover', SIZE_POPOVER_STYLE[size], POPOVER_STYLES, popoverClassName)}>
                <ListBox selectionMode={selectionMode}>
                    {isEmpty ? (
                        /* 空态：以禁用项的形式展示提示文案 */
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
                        /*
                         * 扁平 / 分组由数据结构动态解析：
                         * 含 options 数组的项识别为分组（Section + 自动分割线），
                         * 否则渲染为普通选项（Item）。
                         */
                        buildListBoxChildren(options!, renderItem)
                    )}
                </ListBox>
            </HeroSelect.Popover>

            {/* 辅助说明（可选）：存在错误提示时优先展示错误提示 */}
            {description && !errorMessage && (
                <p className={DESCRIPTION_STYLES}>{description}</p>
            )}
            {errorMessage && <p className={ERROR_MESSAGE_STYLES}>{errorMessage}</p>}
        </HeroSelect>
    );
};
