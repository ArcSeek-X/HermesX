import React from 'react';
import { Select as AntSelect } from 'antd';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
  emptyText?: string;
}

/**
 * Ant Design Select wrapper component.
 * Styled to match the project's dark theme.
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
