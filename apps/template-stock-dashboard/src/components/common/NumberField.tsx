import { useState } from 'react';

interface NumberFieldProps {
  value: number | null;
  onCommit: (value: number | null) => void;
  /** 允许清空提交 null（语义=不限）；默认清空时回退原值 */
  nullable?: boolean;
  min?: number;
  max?: number;
  step?: number | string;
  className?: string;
  placeholder?: string;
  onClick?: (e: React.MouseEvent) => void;
}

/**
 * 草稿缓冲的数字输入：输入期间持有字符串，blur/Enter 才 parse + 夹取提交。
 * 受控 input 直接 Number(x)||fallback 会导致小数输不进去（"0.5" 键入 "0" 即被弹回）、负值直通入库。
 */
export function NumberField({
  value,
  onCommit,
  nullable = false,
  min,
  max,
  step,
  className,
  placeholder,
  onClick,
}: NumberFieldProps) {
  const [draft, setDraft] = useState(value === null ? '' : String(value));
  const [lastValue, setLastValue] = useState(value);

  // 外部值变化（重置/加载方案）时在渲染期同步草稿，避免 effect 级联渲染
  if (value !== lastValue) {
    setLastValue(value);
    setDraft(value === null ? '' : String(value));
  }

  const commit = () => {
    if (draft.trim() === '') {
      if (nullable) {
        if (value !== null) onCommit(null);
        return;
      }
      setDraft(value === null ? '' : String(value));
      return;
    }

    const parsed = Number(draft);
    if (!Number.isFinite(parsed)) {
      setDraft(value === null ? '' : String(value));
      return;
    }

    let next = parsed;
    if (min !== undefined && next < min) next = min;
    if (max !== undefined && next > max) next = max;
    setDraft(String(next));
    if (next !== value) onCommit(next);
  };

  return (
    <input
      type="number"
      className={className}
      value={draft}
      min={min}
      max={max}
      step={step}
      placeholder={placeholder}
      onClick={onClick}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          e.currentTarget.blur();
        }
      }}
    />
  );
}
