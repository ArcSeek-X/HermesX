/**
 * ===================================
 * 下拉选择器组件（Select）
 * ===================================
 *
 * 作用：
 * 基于原生 <select> 实现的下拉选择器，统一项目的暗色主题样式：
 * - 自动适配深色背景、边框和文字颜色
 * - 支持可选的标签、禁用状态
 *
 * 说明：
 * - 原实现基于 Ant Design Select，项目移除 antd 依赖后改用原生 <select>，
 *   对外 props 接口保持不变（value / onChange / options / label 等）。
 * - searchable / searchPlaceholder / emptyText 为兼容保留字段：
 *   原生 <select> 不支持输入搜索，当前实现忽略这些 prop。
 */
import React from 'react';
import { ChevronDown } from 'lucide-react';

/** 下拉选项的数据结构 */
interface SelectOption {
  /** 选项值 */
  value: string;
  /** 选项显示文本 */
  label: string;
}

/** Select 组件的属性定义 */
interface SelectProps {
  /** 表单字段 ID */
  id?: string;
  /** 当前选中的值 */
  value: string;
  /** 值变更回调 */
  onChange: (value: string) => void;
  /** 选项列表 */
  options: SelectOption[];
  /** 标签文本（显示在选择器上方） */
  label?: string;
  /** 占位符文本 */
  placeholder?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 自定义 CSS 类名 */
  className?: string;
  /** 是否启用搜索功能（原生实现不支持，保留兼容） */
  searchable?: boolean;
  /** 搜索框占位符（原生实现不支持，保留兼容） */
  searchPlaceholder?: string;
  /** 无数据时的提示文本（原生实现不支持，保留兼容） */
  emptyText?: string;
}

/**
 * 下拉选择器组件
 *
 * 基于原生 <select> 实现，使用与项目输入框一致的 CSS 主题样式，
 * 确保与项目暗色主题一致。
 *
 * @param props - 组件属性
 * @returns 带标签和暗色样式的下拉选择器
 */
export const Select: React.FC<SelectProps> = ({
  value,
  onChange,
  options,
  label,
  placeholder = '请选择',
  disabled = false,
  className = '',
}) => {
  return (
    <div className={className}>
      {/* 标签 */}
      {label && (
        <label className="mb-1.5 block text-xs font-medium text-muted-text">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="input-surface input-focus-glow w-full appearance-none rounded-lg border bg-transparent px-3 py-2 pr-9 text-sm text-foreground transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        >
          {placeholder && !value && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          aria-hidden
          className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-text"
        />
      </div>
    </div>
  );
};
