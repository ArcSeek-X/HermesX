/**
 * EmptyState.tsx
 *
 * 作用简述：
 *   一个通用的「空状态 / 空数据」展示组件（Empty State）。
 *   当页面或列表没有数据、没有结果、或处于初始占位状态时，用它来友好地
 *   提示用户，而非展示一片空白。组件支持自定义标题、补充说明、图标
 *   以及操作入口（如「去添加」「刷新」「返回」等按钮）。
 *
 * 使用场景：
 *   - 搜索 / 筛选无结果。
 *   - 列表为空（无收藏、无历史记录等）。
 *   - 数据加载完成但内容为空，需要引导用户下一步操作的场合。
 *
 * @author Lensgcx (GaoCangxiong)
 */

import type React from 'react';
import { motion } from 'motion/react';
import { cn } from '../../../utils/cn';

/** 视觉变体：控制图标与主标题的强调色。默认 'primary'（主题青色）。 */
type EmptyStateVariant = 'primary' | 'muted' | 'danger' | 'success';

/** 各变体对应的文字色类名（Tailwind text-* 工具类）。 */
const EMPTY_STATE_VARIANT_COLOR: Record<EmptyStateVariant, string> = {
  primary: 'text-primary',
  muted: 'text-muted',
  danger: 'text-danger',
  success: 'text-success',
};

/**
 * 组件属性定义。
 */
interface EmptyStateProps {
  /** 空状态主标题（必填），用于一句话说明当前没有内容的原因或状态。 */
  title: string;
  /** 补充说明文案（可选），对标题做进一步解释，居中且限制最大宽度。 */
  description?: string;
  /** 顶部图标（可选），通常是装饰性 SVG / Icon 节点，按 variant 着色。 */
  icon?: React.ReactNode;
  /** 操作区节点（可选），一般放入按钮等引导用户操作的入口。 */
  action?: React.ReactNode;
  /** 视觉变体，控制图标与主标题的强调色；默认 'primary'。 */
  variant?: EmptyStateVariant;
  /** 外层形态：'card' 为带虚线边框与阴影的卡片；'text' 为纯文字（无边框 / 阴影 / 背景）。默认 'text'。 */
  type?: 'card' | 'text';
  /** 透传到最外层容器的额外 className，用于外部覆盖 / 追加样式。 */
  className?: string;
}

/**
 * 空状态展示组件。
 * 将标题、说明、图标、操作区按统一布局居中渲染；外层形态由 type 决定：
 *   - 'card'（默认历史外观）：虚线边框 + 柔和阴影的卡片；
 *   - 'text'：纯文字，无边框 / 阴影 / 背景。
 * 两种形态均基于 motion.div 复用同一套入场动画。
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
  variant = 'primary',
  type = 'text',
  className = '',
}) => {
  // 内部区域内容：图标 / 主标题 / 说明 / 操作区，两种形态共用，仅外层容器样式不同。
  const content = (
    <>
      {/* 可选图标区：仅在传入 icon 时渲染，按 variant 着色并居中 */}
      {icon ? (
        <div className={cn('mb-4 flex justify-center', EMPTY_STATE_VARIANT_COLOR[variant])}>{icon}</div>
      ) : null}
      {/* 主标题：基础字号、加粗，颜色随 variant 变化（默认主题青色） */}
      <h3 className={cn('text-xl font-semibold', EMPTY_STATE_VARIANT_COLOR[variant])}>{title}</h3>
      {/* 可选说明文案：仅在传入 description 时渲染，限制最大宽度并居中，使用次级文字色 */}
      {description ? <p className="mx-auto mt-2 max-w-md text-sm text-secondary-text">{description}</p> : null}
      {/* 可选操作区：仅在传入 action 时渲染，用于放置引导操作的按钮等节点 */}
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </>
  );

  // 外层容器样式按 type 分别处理：card 叠加虚线边框 / 阴影 / 背景，text 仅保留居中布局与内边距。
  const wrapperClassName =
    type === 'card'
      ? cn(
          'hrs-empty-state flex flex-col items-center text-center rounded-md border border-dashed border-border/60 bg-card/50 px-6 py-10 shadow-soft-card min-h-[110px]',
          className,
        )
      : cn('hrs-empty-state flex flex-col items-center text-center px-6 py-10', className);

  return (
    <motion.div
      className={wrapperClassName}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
    >
      {content}
    </motion.div>
  );
};
