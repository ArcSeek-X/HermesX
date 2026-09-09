/**
 * HrsCheckbox
 * 基于 HeroUI v3 Checkbox 二次封装的通用勾选框。
 *
 * 内部结构固定为 Checkbox → Checkbox.Content → Checkbox.Control →
 * Checkbox.Indicator，使用方无需关心拼装细节：
 *   - 传 options 数组 → 进入「多选组」模式（循环渲染、统一维护选中集合）；
 *   - 不传 options → 退化为单个勾选框（HeroUI 原生用法完全一致）。
 *
 * 原生能力（isDisabled / isReadOnly / isIndeterminate / isRequired / isInvalid /
 * validate 等）全部透传；多选组支持受控（value: string[]）与非受控
 * （defaultValue 或 option.defaultSelected）两种用法，onChange 统一回传选中集合。
 *
 * @example
 * ```tsx
 * // 1. 多选组（受控）
 * const [values, setValues] = useState<string[]>(['cn']);
 * <HrsCheckbox
 *   name="countries"
 *   value={values}
 *   onChange={(next) => setValues(next as string[])}
 *   options={[
 *     { value: 'cn', label: '中国' },
 *     { value: 'us', label: '美国', defaultSelected: true },
 *     { value: 'jp', label: '日本', disabled: true },
 *   ]}
 * />
 *
 * // 2. 多选组（非受控 + 横向排列 + 小尺寸）
 * <HrsCheckbox
 *   size="sm"
 *   orientation="horizontal"
 *   defaultValue={['newsletter']}
 *   options={[
 *     { value: 'notifications', label: 'Enable notifications' },
 *     { value: 'newsletter', label: 'Subscribe to newsletter' },
 *     { value: 'marketing', label: 'Receive marketing updates' },
 *   ]}
 * />
 *
 * // 3. 单个勾选框（HeroUI 原生用法）
 * <HrsCheckbox
 *   value="on"
 *   name="terms"
 *   label="Accept terms and conditions"
 *   isRequired
 *   onChange={(checked) => setChecked(checked as boolean)}
 * />
 * ```
 * ------------------------------------------------------------
 */

import React, { useMemo, useState } from 'react';
import { Checkbox as HeroCheckbox, Description, FieldError, type CheckboxRootProps } from '@heroui/react';
import { cn } from '../../../utils/cn';
import {
    ROOT_BASE_STYLES,
    CONTENT_BASE_STYLES,
    CONTROL_BASE_STYLES,
    INDICATOR_BASE_STYLES,
    LABEL_BASE_STYLES,
    DESCRIPTION_STYLES,
    ERROR_STYLES,
    CONTROL_SIZE_STYLES,
    INDICATOR_SIZE_STYLES,
    LABEL_SIZE_STYLES,
    ORIENTATION_STYLES,
} from './styleConfig';

/** 尺寸档位（业务增量：同时缩放勾选框、图标与文案） */
export type HrsCheckboxSize = 'sm' | 'md' | 'lg';

/** 多选组的排列方向 */
export type HrsCheckboxOrientation = 'vertical' | 'horizontal';

/**
 * 多选组的单个选项数据结构。
 * 完整继承 HeroUI Checkbox 原生属性，并额外提供语义化别名
 * disabled / readOnly / indeterminate / required / invalid；
 * 冲突时以 HeroUI 原生字段为准（原生字段 ?? 语义别名 ?? 组件级字段）。
 * isSelected 由多选组统一受控，故从原生类型中移除。
 */
export interface HrsCheckboxOptionDef
    extends Omit<CheckboxRootProps, 'children' | 'value' | 'isSelected' | 'className'> {
    value: string; /** 选项唯一值（同时作为该 checkbox 提交表单时的 value） */
    label: React.ReactNode;  /** 选项显示文案（同时作为可访问名称） */
    disabled?: boolean;/** 是否禁用*/
    readOnly?: boolean; /** 是否只读 */
    indeterminate?: boolean; /** 是否半选 */
    required?: boolean; /** 是否必填 */
    invalid?: boolean; /** 是否校验失败 */
    defaultSelected?: boolean;  /** 非受控模式下的初始选中态 */
    description?: React.ReactNode; /** 该选项的辅助说明文本 */
    errorMessage?: React.ReactNode;   /** 该选项的错误提示文本（存在时优先于 description 渲染） */
    indicator?: React.ReactNode;  /** 自定义指示器内容（覆盖默认的勾选 / 半选图标） */
    className?: string; /** 该选项根节点追加的 className（优先级高于组件级 className） */
}

/**
 * HrsCheckbox 组件属性。
 *
 * 通过 Omit + 交叉的方式完整继承 HeroUI Checkbox 原生类型
 * （等价于 React.ComponentProps<typeof Checkbox>），仅对以下三个字段做
 * 语义扩展：children（单选模式自定义内容）、value（双模式下类型不同）、
 * onChange（双模式下回参不同）。
 */
export interface HrsCheckboxProps extends Omit<CheckboxRootProps, 'children' | 'value' | 'onChange'> {
    /**
     * 选项数据源。传入且非空时进入「多选组」模式并循环渲染；
     * 不传时进入「单选框」模式（与 HeroUI 原生 Checkbox 行为一致）。
     */
    options?: HrsCheckboxOptionDef[];
    /**
     * 是否为多选组模式，默认 true（多选）。
     * 为 true 且 options 非空时进入「多选组」模式并循环渲染；
     * 为 false（或 options 为空）时进入「单选框」模式（与 HeroUI 原生 Checkbox 行为一致）。
     */
    multiple?: boolean;
    /**
     * 受控值：
     *   - 多选组模式：string[]（选中项的 value 集合），传入即进入受控；
     *   - 单选框模式：string（HeroUI 原生的表单 value）。
     */
    value?: string[] | string;
    /** 多选组模式下的非受控初始选中集合（单选模式请用原生 defaultSelected） */
    defaultValue?: string[];
    /**
     * 变更回调：
     *   - 多选组模式：回传新的选中集合 string[]（顺序与 options 一致）；
     *   - 单选框模式：回传是否选中 boolean（与 HeroUI 原生签名一致）。
     */
    onChange?: (value: string[] | boolean) => void;
    /** 单选框模式的自定义内容（优先级高于 label，渲染在勾选框之后） */
    children?: React.ReactNode;
    /** 单选框模式的显示文案 */
    label?: React.ReactNode;
    /** 单选框模式的辅助说明文本 */
    description?: React.ReactNode;
    /** 单选框模式的错误提示文本（存在时优先于 description 渲染） */
    errorMessage?: React.ReactNode;
    /** 自定义指示器内容（覆盖默认的勾选 / 半选图标，选项级 indicator 优先） */
    indicator?: React.ReactNode;
    /** 尺寸档位，默认 'md' */
    size?: HrsCheckboxSize;
    /** 多选组的排列方向，默认 'horizontal' */
    orientation?: HrsCheckboxOrientation;
    /**
     * 多选组模式下可选中的最小数量。
     * 当前选中数 ≤ min 时，已勾选项不可取消勾选（触达下限后自动锁定已选项）。
     * 仅多选组模式生效；不传则不限制下限。
     */
    min?: number;
    /**
     * 多选组模式下可选中的最大数量。
     * 当前选中数 ≥ max 时，未勾选项不可再勾选（触达上限后锁定未选项）。
     * 仅多选组模式生效；不传则不限制上限。
     */
    max?: number;
    /** 多选组外层容器追加的 className（仅多选组模式渲染） */
    containerClassName?: string;
    /** Checkbox.Content（可点击区域）追加的 className */
    contentClassName?: string;
    /** Checkbox.Control（勾选框本体）追加的 className */
    controlClassName?: string;
    /** Checkbox.Indicator（勾选 / 半选图标）追加的 className */
    indicatorClassName?: string;
    /** 显示文案追加的 className */
    labelClassName?: string;
}

/**
 * 通用勾选框组件。
 *
 * 多选组模式：按 options 循环渲染，统一维护受控 / 非受控选中集合；
 * 单选框模式：直接渲染一个 HeroUI Checkbox，保留全部原生能力。
 * 两种模式共用同一套 Checkbox.Content / Control / Indicator 组装逻辑与
 * 分层 className 钩子。
 */
export const HrsCheckbox: React.FC<HrsCheckboxProps> = ({
    options,
    multiple = true,
    value,
    defaultValue,
    onChange,
    children,
    label,
    description,
    errorMessage,
    indicator,
    size = 'md',
    orientation = 'horizontal',
    min,
    max,
    className,
    containerClassName,
    contentClassName,
    controlClassName,
    indicatorClassName,
    labelClassName,
    isSelected,
    defaultSelected,
    ...heroProps
}) => {
    /** 是否多选组模式（multiple 为 true 且 options 非空） */
    const isMultiple = multiple && Array.isArray(options) && options.length > 0;
    /** 多选组是否为受控（value 为数组即受控） */
    const isMultipleControlled = isMultiple && Array.isArray(value);

    // 非受控多选组的内部状态；为 undefined 时回退到「选项自带 defaultSelected」
    const [innerValues, setInnerValues] = useState<string[] | undefined>(defaultValue);

    /** 非受控回退集合：由 options 中 defaultSelected 为 true 的项派生（随 options 变化重新计算） */
    const fallbackValues = useMemo(
        () =>
            (options ?? [])
                .filter((option) => option.defaultSelected === true)
                .map((option) => option.value),
        [options],
    );

    /** 当前生效的选中集合（受控用外部 value，非受控用内部状态或回退集合） */
    const selectedValues = useMemo(
        () => (isMultipleControlled ? (value as string[]) : innerValues ?? fallbackValues),
        [isMultipleControlled, value, innerValues, fallbackValues],
    );

    /** 选中集合的 Set 形式，供单项渲染时 O(1) 查询 */
    const selectedSet = useMemo(() => new Set(selectedValues), [selectedValues]);

    /** 多选组单项变更：更新选中集合并回传（输出顺序与 options 一致） */
    const handleGroupChange = (changedValue: string, nextSelected: boolean): void => {
        // min / max 守卫：触达上限 / 下限时拦截本次变更
        if (nextSelected) {
            if (max != null && selectedSet.size >= max) return;
        } else if (min != null && selectedSet.size <= min) {
            return;
        }

        const nextSet = new Set(selectedSet);
        if (nextSelected) {
            nextSet.add(changedValue);
        } else {
            nextSet.delete(changedValue);
        }
        const nextValues = (options ?? [])
            .filter((option) => nextSet.has(option.value))
            .map((option) => option.value);

        if (!isMultipleControlled) {
            setInnerValues(nextValues);
        }
        onChange?.(nextValues);
    };

    /** 单选框模式的变更处理：直接回传 HeroUI 原生的 boolean */
    const handleSingleChange = (nextSelected: boolean): void => {
        onChange?.(nextSelected);
    };

    /** 渲染说明 / 错误提示，二者须为 Checkbox.Content 的相邻兄弟节点（HeroUI 约定）；错误提示优先 */
    const renderHelpText = (
        errorText?: React.ReactNode,
        descText?: React.ReactNode,
    ): React.ReactNode => {
        if (errorText) {
            return <FieldError className={ERROR_STYLES}>{errorText}</FieldError>;
        }
        if (descText) {
            return <Description className={DESCRIPTION_STYLES}>{descText}</Description>;
        }
        return null;
    };

    /** 统一的 Content / Control / Indicator 组装（两种模式共用） */
    const renderInner = (
        content: React.ReactNode,
        itemIndicator?: React.ReactNode,
    ): React.ReactNode => (
        <HeroCheckbox.Content className={cn(CONTENT_BASE_STYLES, contentClassName)}>
            <HeroCheckbox.Control
                className={cn(CONTROL_BASE_STYLES, CONTROL_SIZE_STYLES[size], controlClassName)}
            >
                <HeroCheckbox.Indicator
                    className={cn(
                        INDICATOR_BASE_STYLES,
                        INDICATOR_SIZE_STYLES[size],
                        indicatorClassName,
                    )}
                >
                    {/* 为 undefined 时由 HeroUI 渲染默认的勾选 / 半选图标 */}
                    {itemIndicator ?? indicator}
                </HeroCheckbox.Indicator>
            </HeroCheckbox.Control>
            {content}
        </HeroCheckbox.Content>
    );

    /** 统一的显示文案节点 */
    const renderLabel = (content: React.ReactNode): React.ReactNode => (
        <span
            data-slot="label"
            className={cn(LABEL_BASE_STYLES, LABEL_SIZE_STYLES[size], labelClassName)}
        >
            {content}
        </span>
    );

    // ==================== 多选组模式：循环渲染 options ====================
    if (isMultiple) {
        return (
            <div className={cn('hrs-checkbox-group flex', ORIENTATION_STYLES[orientation], containerClassName)} >
                {(options ?? []).map((option) => {
                    const {
                        value: optionValue,
                        label: optionLabel,
                        disabled,
                        readOnly,
                        indeterminate,
                        required,
                        invalid,
                        description: optionDescription,
                        errorMessage: optionErrorMessage,
                        indicator: optionIndicator,
                        className: optionClassName,
                        onChange: onOptionChange,
                        // 其余为 HeroUI 原生属性（isDisabled / isReadOnly /
                        // isIndeterminate / isRequired / isInvalid / name /
                        // id / autoFocus / onFocus / onBlur / validate ...）
                        ...optionProps
                    } = option;

                    // min / max 约束下的单项可用性：达上限禁未选，达下限禁已选
                    const isChecked = selectedSet.has(optionValue);
                    const atMax = max != null && selectedSet.size >= max;
                    const atMin = min != null && selectedSet.size <= min;
                    const effectiveDisabled =
                        (optionProps.isDisabled ?? disabled ?? heroProps.isDisabled) ||
                        (!isChecked && atMax) ||
                        (isChecked && atMin);

                    return (
                        <HeroCheckbox
                            key={optionValue}
                            // 组件级原生属性先铺底，选项级原生属性覆盖组件级
                            {...heroProps}
                            {...optionProps}
                            // 多选组：子项 value 为 string；整体选中态由组件级 value 经 selectedSet 驱动，受控时通过 isSelected 回灌
                            value={optionValue}
                            isSelected={selectedSet.has(optionValue)}
                            // 状态字段优先级：选项原生 > 选项语义别名 > 组件级
                            isDisabled={effectiveDisabled}
                            isReadOnly={optionProps.isReadOnly ?? readOnly ?? heroProps.isReadOnly}
                            isIndeterminate={
                                optionProps.isIndeterminate ??
                                indeterminate ??
                                heroProps.isIndeterminate
                            }
                            isRequired={optionProps.isRequired ?? required ?? heroProps.isRequired}
                            isInvalid={optionProps.isInvalid ?? invalid ?? heroProps.isInvalid}
                            onChange={(nextSelected) => {
                                handleGroupChange(optionValue, nextSelected);
                                // 选项级原生 onChange 继续保留（单项副作用钩子）
                                onOptionChange?.(nextSelected);
                            }}
                            className={cn(ROOT_BASE_STYLES, className, optionClassName)}
                        >
                            {renderInner(optionLabel ? renderLabel(optionLabel) : null, optionIndicator)}
                            {renderHelpText(optionErrorMessage, optionDescription)}
                        </HeroCheckbox>
                    );
                })}
            </div>
        );
    }

    // ==================== 单选框模式：HeroUI 原生用法 ====================
    return (
        <HeroCheckbox
            {...heroProps}
            // 单选框：value 为 string 表单值（数组格式已在多选组分流中处理）
            value={typeof value === 'string' ? value : undefined}
            isSelected={isSelected}
            defaultSelected={defaultSelected}
            onChange={handleSingleChange}
            className={cn(ROOT_BASE_STYLES, className)}
        >
            {renderInner(
                children ?? (label ? renderLabel(label) : null),
                indicator,
            )}
            {renderHelpText(errorMessage, description)}
        </HeroCheckbox>
    );
};
