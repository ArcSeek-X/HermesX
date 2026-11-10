/**
 * @file .../__tests__/stockMetricViewConditionEditor.test.tsx
 * @description 股票度量视图条件编辑器的编排测试：显示域回显、草稿隔离、保存整组提交、
 * 取消丢弃、区间校验与快捷删除。
 * 基础 UI 组件（Modal / HrsSelect / HrsNumberField / Chip / HrsButton）替换为轻量 DOM 替身，
 * 让断言聚焦条件草稿与回调编排，不依赖 HeroUI 在 jsdom 下的弹层 / 数字输入实现。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import type React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UiLanguageProvider } from '@/contexts/UiLanguageContext';
import { UI_LANGUAGE_STORAGE_KEY } from '@utils/uiLanguage';
import { StockMetricViewConditionEditor } from '../StockMetricViewConditionEditor';

// Provider 会按浏览器语言推断，测试里固定为简体中文以稳定断言文案
beforeEach(() => {
  window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'zh');
});

vi.mock('@components', () => {
  type SlotProps = { children?: React.ReactNode };
  type ButtonProps = {
    children?: React.ReactNode;
    onClick?: () => void;
    isDisabled?: boolean;
    isLoading?: boolean;
  };
  type SelectProps = {
    options: { key: string; label: string }[];
    value: string;
    onChange: (value: string) => void;
  };
  type NumberProps = {
    value?: number;
    onChange: (value: number) => void;
  };
  type ChipProps = { children?: React.ReactNode; onClose?: () => void };

  const Slot = ({ children }: SlotProps) => <div>{children}</div>;
  const ModalStub = ({ isOpen, children }: SlotProps & { isOpen?: boolean }) =>
    isOpen ? <div data-testid="condition-modal">{children}</div> : null;

  return {
    Chip: ({ children, onClose }: ChipProps) => (
      <span data-testid="condition-chip">
        {children}
        {onClose && <button type="button" aria-label="remove" onClick={onClose}>×</button>}
      </span>
    ),
    HrsButton: ({ children, onClick, isDisabled, isLoading }: ButtonProps) => (
      <button type="button" onClick={onClick} disabled={Boolean(isDisabled || isLoading)}>
        {children}
      </button>
    ),
    HrsNumberField: ({ value, onChange }: NumberProps) => (
      <input
        data-testid="number"
        type="number"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? Number.NaN : Number(e.target.value))}
      />
    ),
    HrsSelect: ({ options, value, onChange }: SelectProps) => (
      <select data-testid="select" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
          <option key={option.key} value={option.key}>{option.label}</option>
        ))}
      </select>
    ),
    Modal: Object.assign(ModalStub, {
      Header: Slot,
      Heading: Slot,
      Body: Slot,
      Footer: Slot,
    }),
  };
});

type EditorProps = React.ComponentProps<typeof StockMetricViewConditionEditor>;

function renderEditor(overrides: Partial<EditorProps> = {}) {
  const props: EditorProps = { conditions: [], onSave: vi.fn(), ...overrides };
  const result = render(
    <UiLanguageProvider>
      <StockMetricViewConditionEditor {...props} />
    </UiLanguageProvider>,
  );
  return { ...result, props };
}

const editButton = () => screen.getByRole('button', { name: /编辑条件/ });
const addButton = () => screen.getByRole('button', { name: '添加条件' });
const saveButton = () => screen.getByRole('button', { name: '保存' });

describe('StockMetricViewConditionEditor', () => {
  it('显示域回显已保存条件；无条件时显示空态', () => {
    const { unmount } = renderEditor();
    expect(screen.getByText('暂无筛选条件')).toBeTruthy();
    unmount();

    renderEditor({ conditions: [{ field: 'price', op: 'gte', value: 10 }] });
    expect(screen.getByText('最新价 大于等于 10')).toBeTruthy();
    expect(screen.queryByTestId('condition-modal')).toBeNull();
  });

  it('点编辑按钮打开模态框，草稿以已保存条件为起点', () => {
    renderEditor({ conditions: [{ field: 'price', op: 'gte', value: 10 }] });
    fireEvent.click(editButton());
    expect(screen.getByTestId('condition-modal')).toBeTruthy();
    // 显示域 1 条 + 草稿列表 1 条
    expect(screen.getAllByTestId('condition-chip')).toHaveLength(2);
  });

  it('表单新增条件后保存，整组提交且添加草稿时不触碰上层', () => {
    const onSave = vi.fn();
    renderEditor({ onSave });
    fireEvent.click(editButton());
    fireEvent.change(screen.getByTestId('number'), { target: { value: '50' } });
    fireEvent.click(addButton());
    expect(screen.getByTestId('condition-chip')).toBeTruthy();
    expect(onSave).not.toHaveBeenCalled();

    fireEvent.click(saveButton());
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith([{ field: 'price', op: 'gte', value: 50 }]);
    expect(screen.queryByTestId('condition-modal')).toBeNull();
  });

  it('保存时自动提交「填了但没点添加」的表单值', () => {
    const onSave = vi.fn();
    renderEditor({ onSave });
    fireEvent.click(editButton());
    fireEvent.change(screen.getByTestId('number'), { target: { value: '20' } });
    fireEvent.click(saveButton());
    expect(onSave).toHaveBeenCalledWith([{ field: 'price', op: 'gte', value: 20 }]);
  });

  it('取消关闭模态框，草稿不提交且再次打开重新初始化', () => {
    const onSave = vi.fn();
    renderEditor({ onSave });
    fireEvent.click(editButton());
    fireEvent.change(screen.getByTestId('number'), { target: { value: '50' } });
    fireEvent.click(addButton());
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.queryByTestId('condition-modal')).toBeNull();

    fireEvent.click(editButton());
    expect(screen.queryByTestId('condition-chip')).toBeNull();
  });

  it('between 区间下限大于上限时禁用添加并给出提示', () => {
    renderEditor();
    fireEvent.click(editButton());
    fireEvent.change(screen.getAllByTestId('select')[1], { target: { value: 'between' } });
    const numbers = screen.getAllByTestId('number');
    fireEvent.change(numbers[0], { target: { value: '100' } });
    fireEvent.change(numbers[1], { target: { value: '10' } });
    expect(addButton()).toBeDisabled();
    expect(screen.getByText('最小不能大于最大')).toBeTruthy();
  });

  it('显示域 Chip 快捷删除调用 onRemove', () => {
    const onRemove = vi.fn();
    renderEditor({ conditions: [{ field: 'price', op: 'gte', value: 10 }], onRemove });
    fireEvent.click(screen.getAllByRole('button', { name: 'remove' })[0]);
    expect(onRemove).toHaveBeenCalledWith(0);
  });
});
