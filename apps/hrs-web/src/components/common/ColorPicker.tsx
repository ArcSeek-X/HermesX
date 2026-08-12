/**
 * ===================================
 * 颜色选择器组件（ColorPicker）
 * ===================================
 *
 * 作用：基于 react-colorful 的 HexColorPicker 封装，提供
 * 「色相/饱和度面板 + HEX 输入 + 预设色板」的完整配色控件，
 * 用于主题色等需要精确取色的场景。
 *
 * 设计约束：
 * - 受控组件：通过 value / onChange 读写 HEX 字符串（含 #）
 * - 预设色板可外部传入，缺省使用项目主题相关的默认色板
 * - 内置 HEX 合法性校验，非法输入不向上回写、仅本地提示
 * - 样式复用项目的 CSS 变量（卡片背景、边框、文字、主色）
 */
import { useState } from 'react';
import { HexColorPicker } from 'react-colorful';
import { cn } from '../../utils/cn';

/** 默认预设色板（覆盖中性色、语义色与项目青蓝主色） */
const DEFAULT_PRESETS = [
  '#2C78CD', // 项目主蓝
  '#19B5C4', // 青蓝（primary 近似）
  '#F87171', // 红
  '#34D399', // 绿
  '#FBBF24', // 黄
  '#A78BFA', // 紫
  '#1F2937', // 深灰
  '#FFFFFF', // 白
];

/** HEX 颜色合法性校验：支持 #RGB / #RRGGBB（含可选 #） */
const HEX_PATTERN = /^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

/** ColorPicker 组件属性 */
interface ColorPickerProps {
  /** 当前颜色（HEX 字符串，建议带 #） */
  value: string;
  /** 颜色变更回调，仅在输入合法时触发 */
  onChange: (value: string) => void;
  /** 预设色板，缺省使用 DEFAULT_PRESETS */
  presets?: string[];
  /** 是否显示预设色板，默认 true */
  showPresets?: boolean;
  /** 是否显示 HEX 输入框，默认 true */
  showInput?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 自定义 CSS 类名 */
  className?: string;
}

/**
 * 颜色选择器
 *
 * 渲染 react-colorful 的面板，并叠加 HEX 输入与预设色板，
 * 统一使用项目暗色主题语义类，确保与现有设计系统一致。
 *
 * @param props - 组件属性
 * @returns 带面板 / 输入 / 预设的完整颜色选择器
 */
export const ColorPicker = ({
  value,
  onChange,
  presets = DEFAULT_PRESETS,
  showPresets = true,
  showInput = true,
  disabled = false,
  className = '',
}: ColorPickerProps) => {
  // 本地草稿：HEX 输入框的受控值，允许临时非法输入，校验通过才回写
  const [draft, setDraft] = useState(value);
  // 草稿是否非法（用于输入框边框提示）
  const isDraftInvalid = !HEX_PATTERN.test(draft.trim());

  const commit = (next: string) => {
    if (disabled) return;
    const normalized = next.startsWith('#') ? next : `#${next}`;
    if (HEX_PATTERN.test(normalized)) {
      onChange(normalized.toUpperCase());
    }
  };

  const handleInputChange = (raw: string) => {
    setDraft(raw);
    const trimmed = raw.trim();
    if (HEX_PATTERN.test(trimmed)) {
      commit(trimmed);
    }
  };

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      {/* 色彩面板（react-colorful 自带层级样式，禁用时降低不透明度） */}
      <div className={cn('react-colorful-wrapper', disabled && 'pointer-events-none opacity-50')}>
        <HexColorPicker
          color={value}
          onChange={(hex) => !disabled && onChange(hex)}
        />
      </div>

      {/* HEX 输入 + 预设色板 */}
      {showInput && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-text">HEX</span>
          <input
            type="text"
            value={draft}
            disabled={disabled}
            onChange={(e) => handleInputChange(e.target.value)}
            onBlur={() => setDraft(value)}
            spellCheck={false}
            aria-invalid={isDraftInvalid}
            className={cn(
              'h-8 flex-1 rounded-md border bg-card px-2 font-mono text-xs text-foreground',
              'focus:outline-none focus:ring-2',
              isDraftInvalid ? 'border-danger/40 focus:ring-danger/30' : 'border-subtle focus:ring-primary/30',
              disabled && 'cursor-not-allowed opacity-60',
            )}
            placeholder="#RRGGBB"
          />
        </div>
      )}

      {showPresets && presets.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {presets.map((hex) => {
            const active = value.toLowerCase() === hex.toLowerCase();
            return (
              <button
                key={hex}
                type="button"
                disabled={disabled}
                onClick={() => commit(hex)}
                aria-label={`选择 ${hex}`}
                aria-pressed={active}
                title={hex}
                className={cn(
                  'h-6 w-6 rounded-md border transition-all',
                  active
                    ? 'border-primary ring-2 ring-primary/40'
                    : 'border-subtle hover:border-primary/50',
                  disabled && 'cursor-not-allowed opacity-60',
                )}
                style={{ backgroundColor: hex }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};
