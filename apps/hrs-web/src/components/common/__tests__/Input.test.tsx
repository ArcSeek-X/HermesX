import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Input } from '../../basic/Input';

describe('Input', () => {
  it('renders a startContent and applies leading padding', () => {
    render(
      <Input
        placeholder="用户名"
        startContent={<span>@</span>}
      />
    );

    expect(screen.getByText('@')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('用户名')).toHaveClass('pl-10');
  });

  it('renders an endContent and applies trailing padding', () => {
    render(
      <Input
        placeholder="密码"
        endContent={<button type="button">显示</button>}
      />
    );

    expect(screen.getByRole('button', { name: '显示' })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('密码')).toHaveClass('pr-12');
  });

  it('passes through native input attributes', () => {
    render(
      <Input
        placeholder="测试"
        type="text"
        maxLength={10}
        data-testid="native-input"
      />
    );

    const input = screen.getByTestId('native-input');
    expect(input).toHaveAttribute('type', 'text');
    expect(input).toHaveAttribute('maxlength', '10');
  });
});
