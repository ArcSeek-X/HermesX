/**
 * @file PasswordInput.test.tsx
 * @description PasswordInput 密码输入框组件的单元测试：覆盖前导图标、可见性切换（受控 / 非受控）与回调。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PasswordInput } from '../PasswordInput';

describe('PasswordInput', () => {
  it('renders the leading icon for the requested iconType', () => {
    const { container } = render(<PasswordInput placeholder="API Key" iconType="key" />);

    expect(container.querySelector('svg')).not.toBeNull();
  });

  it('renders no leading icon when iconType is none', () => {
    const { container } = render(<PasswordInput placeholder="API Key" />);

    expect(container.querySelector('svg')).toBeNull();
  });

  it('toggles password visibility in uncontrolled mode', () => {
    render(<PasswordInput placeholder="密码" type="password" allowTogglePassword />);

    const input = screen.getByPlaceholderText('密码');
    expect(input).toHaveAttribute('type', 'password');

    fireEvent.click(screen.getByRole('button', { name: '显示内容' }));
    expect(input).toHaveAttribute('type', 'text');

    fireEvent.click(screen.getByRole('button', { name: '隐藏内容' }));
    expect(input).toHaveAttribute('type', 'password');
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
    // 受控模式下组件自身不翻转状态，仍保持外部传入的可见态
    expect(screen.getByPlaceholderText('API Key')).toHaveAttribute('type', 'text');
  });

  it('does not render the toggle button for non-password inputs', () => {
    render(<PasswordInput placeholder="账号" type="text" allowTogglePassword />);

    expect(screen.queryByRole('button', { name: '显示内容' })).not.toBeInTheDocument();
  });

  it('reports visibility changes in uncontrolled mode as well', () => {
    const onPasswordVisibleChange = vi.fn();

    render(
      <PasswordInput
        placeholder="密码"
        type="password"
        allowTogglePassword
        onPasswordVisibleChange={onPasswordVisibleChange}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '显示内容' }));
    expect(onPasswordVisibleChange).toHaveBeenCalledWith(true);
  });
});
