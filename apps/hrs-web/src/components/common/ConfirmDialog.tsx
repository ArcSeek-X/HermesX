/**
 * ConfirmDialog —— 通用「二次确认」对话框组件
 * =====================================================================
 * 【功能介绍】
 * 一个模态（modal）确认弹窗，用于在执行「不可逆 / 有风险」操作前
 * 向用户二次确认。例如：退出登录、删除持仓、删除告警规则等场景。
 * 组件通过 React Portal 渲染到 document.body，避免被父级
 * stacking context 或 overflow 裁剪，确保始终覆盖在页面最上层。
 *
 * 【主要能力】
 * - isOpen：受控开关，为 false 时直接返回 null（不渲染任何 DOM）。
 * - title / message：标题与提示正文，纯字符串由调用方传入。
 * - confirmText / cancelText：确认 / 取消按钮文案，缺省回退到国际化文案。
 * - isDanger：是否为危险操作；true 时确认按钮呈红色，false 时为主色。
 * - confirmDisabled / cancelDisabled：按钮禁用态（如表单校验未通过）。
 * - onConfirm / onCancel：确认 / 取消回调。
 *   点击遮罩层（非对话框本身）即触发 onCancel（cancelDisabled 时屏蔽）。
 *
 * 【交互与样式】
 * - 遮罩：fixed 全屏 + 半透明黑底 + 背景模糊，居中显示对话框。
 * - 对话框：圆角卡片，标题（text-lg）、正文（text-sm）、底部右对齐双按钮。
 * - 按钮统一复用项目封装的 Button 组件，保持全站视觉与交互一致。
 * - 打开带淡入 + 缩放动画（animate-in fade-in zoom-in）。
 * =====================================================================
 */
import type React from 'react';
import { createPortal } from 'react-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { Button } from '../basic/Button';

/** 组件入参定义 */
interface ConfirmDialogProps {
  /** 是否打开弹窗（受控） */
  isOpen: boolean;
  /** 弹窗标题 */
  title: string;
  /** 提示正文 */
  message: string;
  /** 确认按钮文案，缺省回退到国际化 common.confirm */
  confirmText?: string;
  /** 取消按钮文案，缺省回退到国际化 common.cancel */
  cancelText?: string;
  /** 确认按钮禁用态 */
  confirmDisabled?: boolean;
  /** 取消按钮禁用态；同时控制「点击遮罩是否可取消」 */
  cancelDisabled?: boolean;
  /** 是否为危险操作（确认按钮变红） */
  isDanger?: boolean;
  /** 点击确认按钮的回调 */
  onConfirm: () => void;
  /** 点击取消按钮 / 点击遮罩的回调 */
  onCancel: () => void;
}

/**
 * 通用确认对话框组件。
 * 通过 Portal 渲染到 body，样式与全站其他确认弹窗保持一致。
 */
export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmText,
  cancelText,
  confirmDisabled = false,
  cancelDisabled = false,
  isDanger = false,
  onConfirm,
  onCancel,
}) => {
  // 国际化文案 hook（用于确认/取消按钮的缺省文案）
  const { t } = useUiLanguage();

  // 未打开时完全不渲染，避免多余 DOM 与遮罩
  if (!isOpen) return null;

  // 弹窗结构：外层遮罩 + 内层对话框
  const dialog = (
    // 遮罩层：fixed 全屏、半透明黑底 + 背景模糊，点击遮罩触发取消（除非取消被禁用）
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm transition-all"
      onClick={() => {
        if (!cancelDisabled) {
          onCancel();
        }
      }}
    >
      {/* 对话框卡片：居中、圆角、阴影 + 淡入缩放动画；点击卡片本身阻止冒泡，避免误触遮罩关闭 */}
      <div
        className="mx-4 w-full max-w-sm rounded-xl border border-border/70 bg-elevated p-6 shadow-2xl animate-in fade-in zoom-in duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题 */}
        <h3 className="mb-2 text-lg font-medium text-foreground">{title}</h3>
        {/* 提示正文 */}
        <p className="text-sm text-secondary-text mb-6 leading-relaxed">
          {message}
        </p>
        {/* 底部操作区：右对齐、取消与确认两个按钮 */}
        <div className="flex justify-end gap-3">
          {/* 取消按钮：描边次要样式，缺省文案回退 common.cancel */}
          <Button
            variant="secondary"
            size="md"
            onClick={onCancel}
            disabled={cancelDisabled}
          >
            {cancelText ?? t('common.cancel')}
          </Button>
          {/* 确认按钮：危险操作为红、否则为主色，缺省文案回退 common.confirm */}
          <Button
            variant={isDanger ? 'danger' : 'primary'}
            size="md"
            onClick={onConfirm}
            disabled={confirmDisabled}
          >
            {confirmText ?? t('common.confirm')}
          </Button>
        </div>
      </div>
    </div>
  );

  // 通过 Portal 渲染到 body，脱离父级层级/裁剪限制
  return createPortal(dialog, document.body);
};