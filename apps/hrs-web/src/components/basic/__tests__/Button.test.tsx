/**
 * @file Button.test.tsx
 * @description Button 通用按钮组件的单元测试：覆盖渲染、变体、加载态与点击交互。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Button } from '../Button';

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);

    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('uses button type by default and exposes the selected variant', () => {
    render(<Button variant="danger">Delete</Button>);

    const button = screen.getByRole('button', { name: 'Delete' });
    expect(button).toHaveAttribute('type', 'button');
    expect(button).toHaveAttribute('data-variant', 'danger');
    expect(button.className).toContain('bg-danger');
  });

  it('disables the button when loading and shows loading text', () => {
    render(<Button isLoading loadingText="Saving">Save</Button>);

    const button = screen.getByRole('button', { name: /saving/i });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('Saving')).toBeInTheDocument();
  });

  it('falls back to the i18n processing label while loading', () => {
    render(<Button isLoading>Save</Button>);

    // 未传 loadingText 时回退到多语言「处理中」
    expect(screen.getByRole('button')).toHaveTextContent('处理中');
  });

  it('supports the danger-subtle variant', () => {
    render(<Button variant="danger-subtle">Bulk Delete</Button>);

    const button = screen.getByRole('button', { name: 'Bulk Delete' });
    expect(button).toHaveAttribute('data-variant', 'danger-subtle');
    expect(button.className).toContain('border-danger/60');
    expect(button.className).toContain('bg-danger/10');
  });

  it.each([
    ['action-primary', '--home-action-ai-bg', '--home-action-ai-border', '--home-action-ai-text'],
    ['action-secondary', '--home-action-report-bg', '--home-action-report-border', '--home-action-report-text'],
  ] as const)('supports the %s variant', (variant, bgToken, borderToken, textToken) => {
    render(<Button variant={variant}>Quick Action</Button>);

    const button = screen.getByRole('button', { name: 'Quick Action' });
    expect(button).toHaveAttribute('data-variant', variant);
    expect(button.className).toContain(bgToken);
    expect(button.className).toContain(borderToken);
    expect(button.className).toContain(textToken);
  });

  it('forwards click events and keeps the button disabled when explicitly disabled', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Submit</Button>);

    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    expect(onClick).toHaveBeenCalledTimes(1);

    render(<Button disabled>Blocked</Button>);
    expect(screen.getByRole('button', { name: 'Blocked' })).toBeDisabled();
  });
});
