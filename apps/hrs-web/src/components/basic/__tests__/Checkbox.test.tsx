/**
 * @file Checkbox.test.tsx
 * @description Checkbox 大尺寸勾选框组件单元测试：覆盖 label 关联、点击切换回调与禁用态。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Checkbox } from '../Checkbox';

describe('Checkbox', () => {
  it('renders the label and associates it with the checkbox input', () => {
    render(<Checkbox label="同意协议" onChange={() => undefined} />);

    const input = screen.getByLabelText('同意协议');
    expect(input).toHaveAttribute('type', 'checkbox');
  });

  it('fires onChange when the checkbox is clicked', () => {
    const onChange = vi.fn();
    render(<Checkbox label="同意协议" onChange={onChange} />);

    // 组件把 onChange 直接透传给原生 input，点击应触发一次回调（具体选中态由调用方从事件读取）。
    fireEvent.click(screen.getByLabelText('同意协议'));
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('renders a disabled input when disabled', () => {
    const onChange = vi.fn();
    render(<Checkbox label="同意协议" onChange={onChange} disabled />);

    expect(screen.getByLabelText('同意协议')).toBeDisabled();
  });
});
