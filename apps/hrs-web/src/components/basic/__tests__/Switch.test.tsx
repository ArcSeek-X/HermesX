/**
 * @file Switch.test.tsx
 * @description Switch 开关组件单元测试：覆盖受控切换回调、aria 状态、禁用态与标签渲染。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Switch } from '../Switch';

describe('Switch', () => {
  it('renders a switch with the controlled aria-checked state', () => {
    render(<Switch checked={false} onChange={() => undefined} />);

    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
  });

  it('fires onChange with the toggled value on click', () => {
    const onChange = vi.fn();
    render(<Switch checked={false} onChange={onChange} />);

    fireEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it('does not fire onChange when disabled', () => {
    const onChange = vi.fn();
    render(<Switch checked={false} onChange={onChange} disabled />);

    fireEvent.click(screen.getByRole('switch'));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders the label text when provided', () => {
    render(<Switch checked onChange={() => undefined} label="启用通知" />);

    expect(screen.getByText('启用通知')).toBeInTheDocument();
  });
});
