/**
 * ===================================
 * 内联提示条组件（InlineAlert）
 * ===================================
 *
 * 【功能介绍】
 * 用于页面内「轻量提示 / 通知」的提示条（非浮层、不脱离文档流），可表达信息、成功、警告、危险
 * 四种语义。常用于表单提交结果、操作提示、权限说明等需要在内容流中就地展示反馈的场景。
 *
 * 【设计要点】
 * 1. 语义变体：variant 映射到对应色调的「边框 + 背景 + 文字」三件套；danger 使用独立的
 *    CSS 变量（--color-danger-alert-*）以便主题精确控制告警色。
 * 2. 无障碍：根节点 role="alert"，使辅助技术能在提示出现时立即播报。
 * 3. 布局：窄屏纵向堆叠、md 及以上标题/正文在左、操作区（action）在右；正文支持长文本换行
 *    （break-words + overflow-wrap:anywhere），避免溢出。
 * 4. 可选区块：title（标题）与 action（如「重试」「查看」按钮）都为可选，按需渲染。
 *
 * 【使用方式】
 *   <InlineAlert variant="warning" title="注意" message="该操作不可撤销" action={<Button>确认</Button>} />
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** 提示语义变体类型 */
type InlineAlertVariant = 'info' | 'success' | 'warning' | 'danger';

/** InlineAlert 组件的 Props 定义 */
interface InlineAlertProps {
  /** 可选标题（加粗显示） */
  title?: string;
  /** 提示正文（可为 JSX 节点） */
  message: React.ReactNode;
  /** 语义变体，默认 info */
  variant?: InlineAlertVariant;
  /** 右侧操作区（可选，一般为按钮） */
  action?: React.ReactNode;
  /** 透传的额外类名 */
  className?: string;
}

/** 各变体对应的「边框 + 背景 + 文字」配色 */
const variantStyles: Record<InlineAlertVariant, string> = {
  info: 'border-cyan/20 bg-cyan/10 text-cyan',
  success: 'border-success/20 bg-success/10 text-success',
  warning: 'border-warning/20 bg-warning/10 text-warning',
  danger: 'border-[hsl(var(--color-danger-alert-border)/0.3)] bg-[hsl(var(--color-danger-alert-bg)/0.1)] text-[hsl(var(--color-danger-alert-text))]',
};

/**
 * 内联提示条组件。
 *
 * @param props - 组件属性
 * @param props.title - 标题
 * @param props.message - 正文
 * @param props.variant - 变体
 * @param props.action - 操作区
 * @param props.className - 额外类名
 * @returns 内联语义提示条
 */
export const InlineAlert: React.FC<InlineAlertProps> = ({
  title,
  message,
  variant = 'info',
  action,
  className = '',
}) => {
  return (
    // 根容器：role=alert 供无障碍播报；应用变体配色与卡片圆角/阴影
    <div
      role="alert"
      className={cn('max-w-full overflow-hidden rounded-2xl border px-4 py-3 shadow-soft-card', variantStyles[variant], className)}
    >
      {/* 内容行：窄屏纵向、宽屏左右分布（内容左、操作右） */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          {/* 可选标题 */}
          {title ? <p className="text-sm font-semibold">{title}</p> : null}
          {/* 正文：支持长文本换行，带轻微透明以区分层级 */}
          <div className={cn('text-sm break-words [overflow-wrap:anywhere]', title ? 'mt-1 opacity-90' : 'opacity-90')}>
            {message}
          </div>
        </div>
        {/* 可选操作区：不收缩，靠右 */}
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </div>
  );
};
