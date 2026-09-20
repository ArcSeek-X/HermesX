/**
 * @file TextArea.test.tsx
 * @description TextArea 多行文本输入组件单元测试：覆盖 textarea 渲染、受控输入回调与禁用态。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { TextArea } from '../TextArea';

describe('TextArea', () => {
  it('renders a textarea element', () => {
    render(<TextArea placeholder="备注" />);

    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('fires onChange when the value changes', () => {
    const onChange = vi.fn();
    render(<TextArea value="" onChange={onChange} />);

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hello' } });
    expect(onChange).toHaveBeenCalled();
  });

  it('applies the disabled attribute', () => {
    render(<TextArea value="" onChange={() => undefined} disabled />);

    expect(screen.getByRole('textbox')).toBeDisabled();
  });
});
