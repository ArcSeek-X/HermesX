/**
 * PasswordInput —— 密码输入组件（基础层），基于基础 Input 封装。
 *
 * 职责范围：
 * - 内置前导图标（Lock / Key，仅装饰）。
 * - 内置可选的密码可见性切换按钮（受控 / 非受控）。
 * - 其余输入能力（样式、原生属性透传）委托给基础 Input。
 */
import type * as React from 'react';
import { useState } from 'react';
import { Lock, Key } from 'lucide-react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';
import { EyeToggleIcon } from '../common/EyeToggleIcon';
import { Input, type InputProps } from './Input';

/**
 * PasswordInput 的 Props。继承基础 Input 的全部属性。
 */
export interface PasswordInputProps extends InputProps {
  /** 是否启用内置的密码可见性切换按钮。仅当 type="password" 时生效。 */
  allowTogglePassword?: boolean;
  /**
   * 前导图标类型：
   * - 'password'：锁图标
   * - 'key'：钥匙图标
   * - 'none'：不渲染前导图标（默认值）
   */
  iconType?: 'password' | 'key' | 'none';
  /**
   * 受控模式下的密码可见性状态。
   * 传入 boolean 时组件进入受控模式，可见性由父组件全权管理；
   * 不传则组件内部自管理（非受控模式）。
   */
  passwordVisible?: boolean;
  /** 可见性变化时通知父组件（受控 / 非受控模式下切换按钮被点击时都会触发）。 */
  onPasswordVisibleChange?: (visible: boolean) => void;
}

/**
 * 前导图标映射表：iconType → 对应的图标元素。
 * - 图标仅作视觉装饰：pointer-events 由 Input 插槽容器统一禁用，不会遮挡输入框点击。
 * - 'none' 与未收录的类型均返回 null（不渲染）。
 * - React 元素是不可变的纯描述对象，跨实例复用该常量表是安全的。
 */
const LEADING_ICON_MAP: Record<'password' | 'key' | 'none', React.ReactNode> = {
  password: <Lock className="h-4 w-4 text-muted-text/55" />,
  key: <Key className="h-4 w-4 text-muted-text/55" />,
  none: null,
};

/**
 * 密码输入组件：前导图标 + 可选可见性切换按钮。
 *
 * 可见性状态管理（两种模式，由是否传入 `passwordVisible` 决定）：
 * - 非受控（默认）：内部 useState 自管理，切换按钮直接翻转内部状态。
 * - 受控：父组件通过 `passwordVisible` 传入状态，`onPasswordVisibleChange`
 *   把用户的切换意图上报给父组件，由父组件决定是否更新状态。
 * 无论哪种模式，点击切换按钮都会触发 `onPasswordVisibleChange` 回调，
 * 便于父组件统一响应（如记录日志、埋点等）。
 */
export const PasswordInput = ({
  className = '',
  allowTogglePassword,
  iconType = 'none',
  passwordVisible,
  onPasswordVisibleChange,
  ...props
}: PasswordInputProps) => {
  const { t } = useUiLanguage();
  // 非受控模式下的内部可见性状态（受控模式下该状态不参与最终取值）。
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);

  // 是否为密码输入框：只有密码框才具备"明文 / 密文"切换的语义。
  const isPasswordInput = props.type === 'password';
  // 受控模式判定：只要外部传入了布尔型 passwordVisible 即为受控。
  const isVisibilityControlled = typeof passwordVisible === 'boolean';
  // 最终可见性：受控取外部值，非受控取内部状态。
  const visible = isVisibilityControlled ? passwordVisible : isPasswordVisible;
  // 有效 type：密码框 + 允许切换 + 当前可见 → 明文 'text'；否则保持原 type。
  const effectiveType = isPasswordInput && allowTogglePassword && visible ? 'text' : props.type;

  // 前导图标：根据 iconType 查映射表（仅装饰，不参与交互）。
  const prefixIcon = LEADING_ICON_MAP[iconType] ?? null;

  // 内置的密码可见性切换按钮；仅密码框且启用切换时渲染。
  const toggleButton = isPasswordInput && allowTogglePassword ? (
    <button
      type="button"
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-200 focus:outline-none focus:ring-2',
        visible
          // 可见（明文）态：warning 色系高亮 + 微光，提示"当前可读"。
          ? 'border-warning/40 bg-warning/15 text-warning shadow-[0_0_10px_hsla(var(--warning),0.15)]'
          // 隐藏（密文）态：低饱和中性色，hover 时预亮为 warning。
          : 'border-border/40 bg-muted/20 text-muted-text hover:border-warning/40 hover:text-warning hover:shadow-[0_0_10px_hsla(var(--warning),0.15)] focus:ring-primary/30',
      )}
      onClick={() => {
        // 计算下一次可见性：非受控先更新内部状态，随后统一上报回调。
        const nextVisible = !visible;
        if (!isVisibilityControlled) {
          setIsPasswordVisible(nextVisible);
        }
        onPasswordVisibleChange?.(nextVisible);
      }}
      // 无障碍：按当前可见性给出"显示内容 / 隐藏内容"的语义化描述。
      aria-label={visible ? t('common.hideContent') : t('common.showContent')}
      // 脱离 Tab 焦点序列：避免切换按钮干扰密码输入的主 Tab 流（鼠标 / 触摸不受影响）。
      // 注意：这是有意为之的可访问性权衡——纯键盘用户无法通过 Tab 聚焦到该按钮。
      tabIndex={-1}
    >
      <EyeToggleIcon visible={visible} />
    </button>
  ) : null;

  return (
    <Input
      {...props}
      type={effectiveType}
      // 前导图标放入左侧插槽（prefixNode），切换按钮放入右侧插槽（suffixNode）。
      prefixNode={prefixIcon}
      suffixNode={toggleButton}
      className={className}
    />
  );
};
