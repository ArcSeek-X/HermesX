/**
 * ApiErrorAlert.tsx
 *
 * 作用简述：
 *   一个用于统一展示 API 调用失败信息的错误告警组件（Error Alert）。
 *   接收由请求层解析好的 `ParsedApiError` 对象，渲染出标题、用户友好的
 *   错误文案，并在「原始报错信息」与「展示文案」不一致时，提供可折叠的
 *   详细信息面板（便于开发/排障定位）。同时支持可选的「操作按钮」（如重试）
 *   与「关闭按钮」，适配多语言文案。
 *
 * 使用场景：
 *   - 网络请求失败、后端返回非 2xx、解析异常等需要在界面上提示用户的场合。
 *   - 作为全局或局部的错误展示 UI，与 `api/error` 的解析结果配套使用。
 */

import type React from 'react';
import type { ParsedApiError } from '../../api/error';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

/**
 * 组件属性定义。
 */
interface ApiErrorAlertProps {
  /** 已解析好的 API 错误信息（必须包含 title、message、rawMessage 等字段）。 */
  error: ParsedApiError;
  /** 透传到最外层容器的额外 className，用于外部覆盖/追加样式。 */
  className?: string;
  /** 操作按钮文案（如「重试」）；不传则不显示操作按钮。 */
  actionLabel?: string;
  /** 点击操作按钮时的回调（如重新发起请求）。 */
  onAction?: () => void;
  /** 关闭按钮文案；不传时回退到多语言文案 `common.close`。 */
  dismissLabel?: string;
  /** 点击关闭按钮时的回调（如清空错误状态、隐藏告警）。 */
  onDismiss?: () => void;
}

/**
 * API 错误告警组件。
 * 负责把解析后的错误信息以一致、可读、可折叠详情的样式呈现给用户。
 */
export const ApiErrorAlert: React.FC<ApiErrorAlertProps> = ({
  error,
  className = '',
  actionLabel,
  onAction,
  dismissLabel,
  onDismiss,
}) => {
  const { t } = useUiLanguage();
  // 是否展示「详细信息」折叠面板：
  // 仅当原始报错信息存在，且与给用户看的 message 文案不一致时才展示，
  // 避免展示与提示文案重复、无意义的内容。
  const showDetails = error.rawMessage.trim() && error.rawMessage.trim() !== error.message.trim();

  return (
    // 最外层告警容器：圆角 + 危险色系边框/背景（半透明）/文字色，并合并外部传入的 className。
    // role="alert" 用于无障碍（ARIA），让屏幕阅读器及时播报该错误提示。
    <div
      className={`rounded-xl border border-[hsl(var(--color-danger-alert-border)/0.3)] bg-[hsl(var(--color-danger-alert-bg)/0.1)] px-4 py-3 text-[hsl(var(--color-danger-alert-text))] ${className}`}
      role="alert"
    >
      {/* 头部行：左侧为错误标题 + 文案，右侧为可选的关闭按钮 */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {/* 错误标题（加粗、主要层级） */}
          <p className="text-sm font-semibold">{error.title}</p>
          {/* 用户友好的错误说明文案（较小字、略降透明度） */}
          <p className="mt-1 text-xs opacity-90">{error.message}</p>
        </div>
        {/* 若传入 onDismiss 才渲染关闭按钮；文案优先用 dismissLabel，否则回退多语言的「关闭」 */}
        {onDismiss ? (
          <button
            type="button"
            className="shrink-0 rounded-md border border-[hsl(var(--color-danger-alert-border)/0.3)] bg-[hsl(var(--color-danger-alert-bg)/0.1)] px-2 py-1 text-[11px] text-[hsl(var(--color-danger-alert-text))] transition hover:bg-[hsl(var(--color-danger-alert-bg)/0.15)]"
            onClick={onDismiss}
          >
            {dismissLabel ?? t('common.close')}
          </button>
        ) : null}
      </div>
      {/* 当原始错误信息与展示文案不同步时，展示可折叠的「详细信息」面板（原始报错原样输出） */}
      {showDetails ? (
        <details className="mt-3 rounded-lg border border-subtle bg-surface-2 px-3 py-2">
          <summary className="cursor-pointer text-xs text-[hsl(var(--color-danger-alert-text))] opacity-90">{t('common.details')}</summary>
          {/* pre 保留换行与空白，并允许长内容折行，避免溢出 */}
          <pre className="mt-2 whitespace-pre-wrap break-words text-[11px] leading-5 text-[hsl(var(--color-danger-alert-text))] opacity-85">
            {error.rawMessage}
          </pre>
        </details>
      ) : null}
      {/* 同时提供 actionLabel 与 onAction 时才渲染操作按钮（如「重试」），否则不展示 */}
      {actionLabel && onAction ? (
        <button
          type="button"
          className="mt-3 inline-flex items-center justify-center rounded-md border border-[hsl(var(--color-danger-alert-border)/0.3)] bg-[hsl(var(--color-danger-alert-bg)/0.1)] px-3 py-1.5 text-xs font-medium text-[hsl(var(--color-danger-alert-text))] transition hover:bg-[hsl(var(--color-danger-alert-bg)/0.15)]"
          onClick={onAction}
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
};
