/**
 * @file Input.test.tsx
 * @description Input 基础输入框组件的单元测试：覆盖尺寸档位、原生属性透传、只读兜底与左右插槽。
 * @author Lensgcx (GaoCangxiong)
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Input } from '../Input';

describe('Input', () => {
  it('renders a single input element by default', () => {
    render(<Input placeholder="用户名" data-testid="native-input" />);

    const input = screen.getByTestId('native-input');
    expect(input.tagName).toBe('INPUT');
    // 默认尺寸 sm：h-8 / !text-xs / rounded-sm
    expect(input.className).toContain('h-8');
    expect(input.className).toContain('rounded-sm');
    expect(input.className).toContain('hrs-input-surface');
  });

  it.each([
    ['xs', 'h-7'],
    ['sm', 'h-8'],
    ['md', 'h-9'],
    ['lg', 'h-10'],
  ] as const)('applies the %s size classes', (size, heightClass) => {
    render(<Input size={size} placeholder="尺寸" data-testid="native-input" />);

    expect(screen.getByTestId('native-input').className).toContain(heightClass);
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

  it('marks a value without onChange as read-only to avoid react-aria warnings', () => {
    render(<Input value="只读值" data-testid="native-input" />);

    expect(screen.getByTestId('native-input')).toHaveAttribute('readonly');
  });

  it('keeps an editable input when onChange is provided', () => {
    render(<Input value="可编辑" onChange={() => undefined} data-testid="native-input" />);

    expect(screen.getByTestId('native-input')).not.toHaveAttribute('readonly');
  });

  it('renders prefix and suffix nodes through the input group without leaking them to the DOM', () => {
    render(
      <Input
        placeholder="令牌"
        data-testid="native-input"
        prefixNode={<span>@</span>}
        suffixNode={<button type="button">显示</button>}
      />
    );

    const input = screen.getByTestId('native-input');
    expect(screen.getByText('@')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '显示' })).toBeInTheDocument();
    // 插槽不得作为未知属性落到 <input> 上
    expect(input).not.toHaveAttribute('prefixnode');
    expect(input).not.toHaveAttribute('suffixnode');
  });

  it('merges the caller className into the generated class list', () => {
    render(<Input className="custom-input" data-testid="native-input" />);

    expect(screen.getByTestId('native-input').className).toContain('custom-input');
  });
});
