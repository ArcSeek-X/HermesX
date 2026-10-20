/**
 * HrsNumberField —— 通用数字输入组件（基础层），基于 HeroUI（@heroui/react）的 NumberField 封装。
 *
 * 名称：HrsNumberField（数字输入框）
 * 作用：在表单 / 筛选 / 配置等场景提供数字录入能力，底层复用 HeroUI 的 NumberField，
 *       默认呈现左右水平 +/- 步进按钮，与本项目尺寸体系对齐。
 * 描述：
 *   - 支持 xs/sm/md/lg 四档尺寸，由 size 控制整体高度、字号与圆角。
 *   - 继承并透传 HeroUI NumberField 原生能力：value / defaultValue / minValue / maxValue /
 *     step / formatOptions / onChange / isDisabled / isReadOnly 等。
 *   - 默认渲染左右水平 +/- 步进按钮；vertical 为 true 时切换为右侧上下 chevron 排列。
 *   - 可通过 hideControls 完全隐藏步进按钮。
 *   - 支持可选 label 属性，渲染 HeroUI Label 在输入框上方。
 *   - 支持可选 placeholder 占位提示，透传至 HeroUI NumberField.Input（复合结构下仅 Input 接受该属性）。
 *   - 内部样式全部基于 Tailwind 工具类，不引入或新建样式文件。
 * @author Lensgcx (GaoCangxiong)
 */
import React from 'react';
import { NumberField as HeroNumberField, Label, Description } from '@heroui/react';
import { cn } from '../../../utils/cn';

/**
 * HrsNumberField 的 Props。
 * 继承 HeroUI NumberField 根节点所有 Props，并扩展业务自定义属性。
 */
export interface HrsNumberFieldProps extends Omit<React.ComponentProps<typeof HeroNumberField.Root>, 'children'> {
  /** 输入框尺寸，控制整体高度、字号与圆角，默认 'sm'。 */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** 标签文本；传入时会在输入框上方渲染 HeroUI Label。 */
  label?: React.ReactNode;
  /** 辅助描述文本；传入时会在输入框下方渲染 HeroUI Description。 */
  description?: React.ReactNode;
  /** 输入框占位提示文本；透传到 HeroUI NumberField.Input（根节点 Root 不接受该属性）。 */
  placeholder?: string;
  /** 是否隐藏右侧步进按钮，默认 false（显示步进按钮）。 */
  hideControls?: boolean;
  /** 控制步进按钮排列方式：true 为右侧上下垂直排列（chevron），false 为左右水平排列（- / +），默认 false。 */
  vertical?: boolean;
}

/**
 * 不同尺寸对应的整体高度 / 字号 / 圆角，集中维护便于统一调整。
 */
const SIZE_CLASSES: Record<NonNullable<HrsNumberFieldProps['size']>, string> = {
  xs: 'h-7 !text-xs rounded-sm',
  sm: 'h-8 !text-xs rounded-sm',
  md: 'h-9 !text-sm rounded-md',
  lg: 'h-10 !text-base rounded-md',
  xl: 'h-12 !text-base rounded-md',
};

/**
 * Chevron 向上图标（用于步进增加按钮）。
 */
const ChevronUpIcon: React.FC = () => (
  <svg
    aria-hidden="true"
    height="11"
    viewBox="0 0 16 16"
    width="11"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      clipRule="evenodd"
      d="M13.03 10.53a.75.75 0 0 1-1.06 0L8 6.56l-3.97 3.97a.75.75 0 1 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1 0 1.06"
      fill="currentColor"
      fillRule="evenodd"
    />
  </svg>
);

/**
 * Chevron 向下图标（用于步进减少按钮）。
 */
const ChevronDownIcon: React.FC = () => (
  <svg
    aria-hidden="true"
    height="11"
    viewBox="0 0 16 16"
    width="11"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      clipRule="evenodd"
      d="M2.97 5.47a.75.75 0 0 1 1.06 0L8 9.44l3.97-3.97a.75.75 0 1 1 1.06 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0l-4.5-4.5a.75.75 0 0 1 0-1.06"
      fill="currentColor"
      fillRule="evenodd"
    />
  </svg>
);

/**
 * Plus 图标（用于水平布局步进增加按钮）。
 */
const PlusIcon: React.FC = () => (
  <svg
    aria-hidden="true"
    height="12"
    viewBox="0 0 16 16"
    width="12"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      clipRule="evenodd"
      d="M8 2a.75.75 0 0 1 .75.75v4.5h4.5a.75.75 0 0 1 0 1.5h-4.5v4.5a.75.75 0 0 1-1.5 0v-4.5h-4.5a.75.75 0 0 1 0-1.5h4.5v-4.5A.75.75 0 0 1 8 2Z"
      fill="currentColor"
      fillRule="evenodd"
    />
  </svg>
);

/**
 * Minus 图标（用于水平布局步进减少按钮）。
 */
const MinusIcon: React.FC = () => (
  <svg
    aria-hidden="true"
    height="12"
    viewBox="0 0 16 16"
    width="12"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M2.75 8a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 0 1.5h-9A.75.75 0 0 1 2.75 8Z"
      fill="currentColor"
    />
  </svg>
);

/**
 * 通用数字输入组件。
 * - 使用 HeroUI NumberField 的复合结构：Group + Input + IncrementButton/DecrementButton。
 * - 默认左右水平 +/- 按钮用于步进增减；vertical 为 true 时切换为右侧上下 chevron 按钮。
 * - 所有 HeroUI NumberField 原生属性（含受控 / 非受控 / 格式化 / 限制）均透传给根节点。
 */
export const HrsNumberField: React.FC<HrsNumberFieldProps> = ({
  className = '',
  size = 'sm',
  label,
  description,
  placeholder,
  hideControls = false,
  vertical = false,
  ...props
}: HrsNumberFieldProps) => {
  // react-aria 要求：无可见 label 时必须提供 aria-label / aria-labelledby，否则运行时告警。
  // 仅在用户既未传 label、也未传 aria 属性时补一个兜底 aria-label，避免覆盖调用方显式设置。
  const needsAriaFallback = !label && !props['aria-label'] && !props['aria-labelledby'];
  return (
    <HeroNumberField
      {...props}
      {...(needsAriaFallback ? { 'aria-label': 'Number field' } : {})}
      className={cn('hrs-number-field w-full max-w-64', className)}
    >
      {label ? (
        <Label className="mb-1 block text-xs text-secondary-text">{label}</Label>
      ) : null}
      <HeroNumberField.Group
        className={cn(
          'flex items-stretch overflow-hidden border',
          SIZE_CLASSES[size],
        )}
      >
        {/* 水平布局：左侧减少按钮 */}
        {!hideControls && !vertical ? (
          <div className="flex h-full items-stretch border-e border-border/50">
            <HeroNumberField.DecrementButton className="flex h-full w-8 items-center justify-center rounded-none border-0 text-sm transition-colors hover:bg-muted/50">
              <MinusIcon />
            </HeroNumberField.DecrementButton>
          </div>
        ) : null}

        <HeroNumberField.Input
          placeholder={placeholder}
          className={cn(
            'hrs-number-field-input flex-1 bg-transparent px-2 outline-none',
            hideControls ? 'w-full' : 'min-w-0',
          )}
        />

        {/* 垂直布局：右侧上下按钮 */}
        {!hideControls && vertical ? (
          <div className="flex h-full flex-col border-s border-border/50">
            <HeroNumberField.IncrementButton className="flex h-1/2 w-6 items-center justify-center rounded-none border-0 pt-0.5 text-sm transition-colors hover:bg-muted/50">
              <ChevronUpIcon />
            </HeroNumberField.IncrementButton>
            <HeroNumberField.DecrementButton className="flex h-1/2 w-6 items-center justify-center rounded-none border-0 pb-0.5 text-sm transition-colors hover:bg-muted/50">
              <ChevronDownIcon />
            </HeroNumberField.DecrementButton>
          </div>
        ) : null}

        {/* 水平布局：右侧增加按钮 */}
        {!hideControls && !vertical ? (
          <div className="flex h-full items-stretch border-s border-border/50">
            <HeroNumberField.IncrementButton className="flex h-full w-8 items-center justify-center rounded-none border-0 text-sm transition-colors hover:bg-muted/50">
              <PlusIcon />
            </HeroNumberField.IncrementButton>
          </div>
        ) : null}
      </HeroNumberField.Group>
      {description ? (
        <Description className="mt-1 text-xs text-muted">{description}</Description>
      ) : null}
    </HeroNumberField>
  );
};
