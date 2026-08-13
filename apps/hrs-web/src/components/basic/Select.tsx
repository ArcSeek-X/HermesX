/**
 * ===================================
 * 下拉选择器组件（Select）
 * ===================================
 *
 * 作用：
 * 封装 Ant Design Select 组件，统一项目的暗色主题样式：
 * - 自动适配深色背景、边框和文字颜色
 * - 支持下拉面板的暗色主题样式
 * - 支持可选的标签、搜索和空状态提示
 */
import React from 'react';
import { Select as AntSelect } from 'antd';

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
  /** 是否启用搜索功能 */
  searchable?: boolean;
  /** 搜索框占位符 */
  searchPlaceholder?: string;
  /** 无数据时的提示文本 */
  emptyText?: string;
}

/**
 * 下拉选择器组件
 *
 * 对 Ant Design Select 进行主题封装，统一使用 CSS 变量控制颜色，
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
  searchable = false,
  emptyText = '暂无数据',
}) => {
  return (
    <div className={className}>
      {/* 标签 */}
      {label && (
        <label className="mb-1.5 block text-xs font-medium text-muted-text">
          {label}
        </label>
      )}
      <AntSelect
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        showSearch={searchable}
        notFoundContent={emptyText}
        className="w-full"
        style={{
          backgroundColor: 'var(--bg-elevated)',
          borderColor: 'var(--border-subtle)',
          color: 'var(--text-primary)',
        }}
        options={options}
        popupClassName="dark-theme-select-dropdown"
      />
    </div>
  );
};
