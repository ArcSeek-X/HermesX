import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PasswordInput } from '../../basic/PasswordInput';

describe('PasswordInput', () => {
  it('renders a key icon and applies leading padding', () => {
    const { container } = render(<PasswordInput placeholder="API Key" iconType="key" />);

    expect(container.querySelector('svg')).not.toBeNull();
    expect(screen.getByPlaceholderText('API Key')).toHaveClass('pl-10');
  });

  it('toggles password visibility in uncontrolled mode', () => {
    render(<PasswordInput placeholder="密码" type="password" allowTogglePassword />);

    const input = screen.getByPlaceholderText('密码');
    expect(input).toHaveAttribute('type', 'password');

    fireEvent.click(screen.getByRole('button', { name: '显示内容' }));
    expect(input).toHaveAttribute('type', 'text');
  });

  it('supports controlled password visibility', () => {
    const onPasswordVisibleChange = vi.fn();

    render(
      <PasswordInput
        placeholder="API Key"
        type="password"
        allowTogglePassword
        passwordVisible
        onPasswordVisibleChange={onPasswordVisibleChange}
      />
    );

    expect(screen.getByPlaceholderText('API Key')).toHaveAttribute('type', 'text');

    fireEvent.click(screen.getByRole('button', { name: '隐藏内容' }));
    expect(onPasswordVisibleChange).toHaveBeenCalledWith(false);
  });
});
