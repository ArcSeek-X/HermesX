/**
 * HrsCheckbox style config
 * ------------------------------------------------------------
 * 集中维护 HrsCheckbox 组件的「基础样式」与「尺寸 / 排列方向样式」。
 * 从 HrsCheckbox.tsx 拆分而来，组件本体只保留结构与逻辑。
 *
 * 颜色约定（本项目）：
 *   - Control 的 before 伪元素背景用 var(--primary)（HeroUI 默认是 var(--accent)，
 *     本主题 --accent 非期望蓝，故覆写为 primary）；
 *   - Indicator 内部勾选 / 半选图标强制 text-white（选中蓝底上的浅色勾）。
 * ------------------------------------------------------------
 */

import type { HrsCheckboxSize, HrsCheckboxOrientation } from './HrsCheckbox';

/** 勾选框 - 各尺寸档位对应的勾选框（Control）尺寸 */
export const CONTROL_SIZE_STYLES: Record<HrsCheckboxSize, string> = {
    sm: 'size-3.5',
    md: 'size-4',
    lg: 'size-5',
};

/** 各尺寸档位对应的指示器（Indicator）尺寸 */
export const INDICATOR_SIZE_STYLES: Record<HrsCheckboxSize, string> = {
    sm: 'size-2.5',
    md: 'size-3',
    lg: 'size-3.5',
};

/** 各尺寸档位对应的文案字号 */
export const LABEL_SIZE_STYLES: Record<HrsCheckboxSize, string> = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
};

/** 多选组各排列方向的容器布局 */
export const ORIENTATION_STYLES: Record<HrsCheckboxOrientation, string> = {
    vertical: 'flex-col gap-2',
    horizontal: 'flex-row flex-wrap gap-x-5 gap-y-2',
};

/**
 * 根（Checkbox 字段）基础样式。
 * group 供子插槽按需以 group-data-* / group-aria-* 派生状态样式。
 */
export const ROOT_BASE_STYLES = 'hrs-checkbox group';

/** Checkbox.Content 基础样式：可点击区域（勾选框 + 文案），间距对齐项目规范 */
export const CONTENT_BASE_STYLES = 'hrs-checkbox-content items-center gap-2';

/** Checkbox.Control 基础样式：勾选框本体，圆角对齐项目 rounded-sm 规范 */
export const CONTROL_BASE_STYLES = 'hrs-checkbox-control rounded-xs before:!rounded-xs before:!bg-primary';

/** Checkbox.Indicator 基础样式：勾选 / 半选图标容器 */
export const INDICATOR_BASE_STYLES =
    'hrs-checkbox-indicator group-data-[selected=true]:[&_[data-slot=checkbox-default-indicator--checkmark]]:!text-white group-data-[indeterminate=true]:[&_[data-slot=checkbox-default-indicator--indeterminate]]:!text-white';

/** 显示文案基础样式 */
export const LABEL_BASE_STYLES = 'hrs-checkbox-label cursor-[inherit] text-foreground select-none';

/** 辅助说明文本样式 */
export const DESCRIPTION_STYLES = 'hrs-checkbox-description text-xs text-foreground-soft';

/** 错误提示文本样式 */
export const ERROR_STYLES = 'hrs-checkbox-error text-xs text-danger';
