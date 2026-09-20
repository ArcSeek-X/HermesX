/**
 * @file Select.test.tsx
 * @description Select 基础下拉选择器组件单元测试：覆盖标签渲染、选项渲染、受控变更回调、受控值与禁用态。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Select } from '../Select';

describe('Select', () => {
  const options = [
    { value: 'all', label: '全部状态' },
    { value: 'enabled', label: '已启用' },
    { value: 'disabled', label: '已停用' },
  ];

  it('renders the label and all option labels', () => {
    render(<Select label="启停状态" value="all" onChange={() => undefined} options={options} />);

    expect(screen.getByText('启停状态')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '全部状态' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '已启用' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '已停用' })).toBeInTheDocument();
  });

  it('fires onChange with the selected value', () => {
    const onChange = vi.fn();
    render(<Select label="启停状态" value="all" onChange={onChange} options={options} />);

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'disabled' } });

    expect(onChange).toHaveBeenCalledWith('disabled');
  });

  it('reflects the controlled value (selected option)', () => {
    render(<Select label="启停状态" value="enabled" onChange={() => undefined} options={options} />);

    expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('enabled');
  });

  it('applies the disabled attribute', () => {
    render(<Select label="启停状态" value="all" onChange={() => undefined} options={options} disabled />);

    expect(screen.getByRole('combobox')).toBeDisabled();
  });
});
