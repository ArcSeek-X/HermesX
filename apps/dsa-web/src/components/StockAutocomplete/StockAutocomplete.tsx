/**
 * StockAutocomplete Component
 *
 * Stock code/name autocomplete input box
 * Supports keyboard navigation, IME input method, graceful degradation
 */

import { Component, useRef, useEffect, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useStockIndex } from '../../hooks/useStockIndex';
import { useAutocomplete } from '../../hooks/useAutocomplete';
import { SuggestionsList } from './SuggestionsList';
import { cn } from '../../utils/cn';
import type { Market } from '../../types/stockIndex';

const AUTOCOMPLETE_INPUT_CLASS =
  'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';

export interface StockAutocompleteProps {
  /** Input value (used for search logic) */
  value: string;
  /** Display value shown in the input box (optional, falls back to value) */
  displayValue?: string;
  /** Value change callback */
  onChange: (value: string) => void;
  /** Submit callback (code, name, source, metadata) */
  onSubmit: (
    code: string,
    name?: string,
    source?: 'manual' | 'autocomplete',
    metadata?: { market?: Market; displayCode?: string },
  ) => void;
  /** Whether disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Accessible label */
  ariaLabel?: string;
  /** Additional CSS class name */
  className?: string;
  /** Callback when clear button is clicked */
  onClear?: () => void;
}

function FallbackInput({
  value,
  displayValue,
  onChange,
  onSubmit,
  onClear,
  disabled = false,
  placeholder = '输入股票代码或名称',
  ariaLabel,
  className,
}: StockAutocompleteProps) {
  // 编辑状态：用户正在编辑时使用原始输入值，避免 displayValue 覆盖编辑
  const [editingValue, setEditingValue] = useState<string | null>(null);
  // 使用 displayValue 作为输入框显示内容（如"名称（代码）"），value 用于搜索逻辑
  const inputValue = editingValue ?? displayValue ?? value;
  return (
    <div className="relative">
      <input
        type="text"
        value={inputValue}
        onChange={(e) => {
          const raw = e.target.value;
          setEditingValue(raw);
          onChange(raw);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !disabled && value) {
            e.preventDefault();
            setEditingValue(null);
            onSubmit(value);
          }
        }}
        onBlur={() => setEditingValue(null)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        disabled={disabled}
        className={cn(
          AUTOCOMPLETE_INPUT_CLASS,
          inputValue && onClear && 'pr-9',
          className
        )}
        data-autocomplete-mode="fallback"
      />
      {/* 清除按钮：有内容时显示 X 图标 */}
      {inputValue && onClear && !disabled && (
        <button
          type="button"
          onClick={() => {
            setEditingValue(null);
            onClear();
          }}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 flex h-6 w-6 items-center justify-center rounded-full text-muted-text transition-colors hover:bg-foreground/10 hover:text-foreground"
          aria-label="清除输入"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      )}
    </div>
  );
}

interface StockAutocompleteBoundaryProps extends StockAutocompleteProps {
  children: ReactNode;
}

interface StockAutocompleteBoundaryState {
  hasError: boolean;
}

class StockAutocompleteBoundary extends Component<
  StockAutocompleteBoundaryProps,
  StockAutocompleteBoundaryState
> {
  override state: StockAutocompleteBoundaryState = { hasError: false };

  static getDerivedStateFromError(): StockAutocompleteBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Autocomplete runtime error. Falling back to plain input.', error, errorInfo);
  }

  override render() {
    if (this.state.hasError) {
      const { children, ...fallbackProps } = this.props;
      void children;
      return <FallbackInput {...fallbackProps} />;
    }

    return this.props.children;
  }
}

function StockAutocompleteInner({
  value,
  displayValue,
  onChange,
  onSubmit,
  onClear,
  disabled = false,
  placeholder = '输入股票代码或名称',
  ariaLabel,
  className,
}: StockAutocompleteProps) {
  const { index, loading, fallback } = useStockIndex();
  const {
    // query,
    setQuery,
    suggestions,
    isOpen,
    highlightedIndex,
    setHighlightedIndex,
    highlightPrevious,
    highlightNext,
    close,
    // reset,
    isComposing,
    setIsComposing,
    runtimeFallback,
    error: autocompleteError,
  } = useAutocomplete(index);

  const inputRef = useRef<HTMLInputElement>(null);
  const prevValueRef = useRef(value);
  const justSelectedRef = useRef(false); // 标记刚刚完成了选择，阻止同步效应重新触发搜索
  const [dropdownStyle, setDropdownStyle] = useState<{ top: number; left: number; width: string } | null>(null);
  // 编辑状态：用户正在编辑输入框时，使用原始输入值而非 displayValue
  // 避免 displayValue（如"名称（代码）"）覆盖用户的编辑操作
  const [editingValue, setEditingValue] = useState<string | null>(null);

  const updateDropdownPosition = () => {
    if (!inputRef.current) {
      setDropdownStyle(null);
      return;
    }

    const rect = inputRef.current.getBoundingClientRect();
    setDropdownStyle({
      top: rect.bottom,
      left: rect.left,
      width: `${rect.width}px`,
    });
  };

  const closeSuggestions = () => {
    close();
    setDropdownStyle(null);
  };

  // 输入框显示值：编辑时使用用户输入的原始值，否则使用 displayValue 或 value
  const inputValue = editingValue ?? displayValue ?? value;

  // Sync external value with internal query (only when value truly changes)
  // Skip when justSelectedRef is true (user just picked a suggestion — don't re-trigger search)
  useEffect(() => {
    if (prevValueRef.current !== value) {
      if (justSelectedRef.current) {
        justSelectedRef.current = false;
        prevValueRef.current = value;
        return;
      }
      setQuery(value);
      prevValueRef.current = value;
    }
  }, [value, setQuery]);

  // Calculate suggestion box position (using fixed positioning)
  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const frameId = window.requestAnimationFrame(updateDropdownPosition);
    window.addEventListener('resize', updateDropdownPosition);
    window.addEventListener('scroll', updateDropdownPosition, true);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener('resize', updateDropdownPosition);
      window.removeEventListener('scroll', updateDropdownPosition, true);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!autocompleteError) {
      return;
    }

    console.error('Autocomplete runtime fallback activated.', autocompleteError);
  }, [autocompleteError]);

  // Keyboard event handling
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Skip if composing (IME)
    if (isComposing) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        highlightNext();
        break;
      case 'ArrowUp':
        e.preventDefault();
        highlightPrevious();
        break;
      case 'Enter':
        e.preventDefault();
        setEditingValue(null); // 提交时清除编辑状态
        if (highlightedIndex >= 0 && suggestions[highlightedIndex]) {
          // Select highlighted item
          const selected = suggestions[highlightedIndex];
          justSelectedRef.current = true; // 阻止同步效应重新触发搜索
          onChange(selected.displayCode);
          closeSuggestions();
          onSubmit(selected.canonicalCode, selected.nameZh, 'autocomplete', {
            market: selected.market,
            displayCode: selected.displayCode,
          });
        } else {
          // Submit directly
          onSubmit(value);
        }
        break;
      case 'Escape':
        e.preventDefault();
        closeSuggestions();
        break;
    }
  };

  // IME handling
  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  // Delay closing on blur (avoid immediate close when clicking suggestion items)
  const handleBlur = () => {
    setEditingValue(null); // 失焦时清除编辑状态，恢复 displayValue
    setTimeout(() => closeSuggestions(), 200);
  };

  // Fallback mode: use normal input
  if (fallback || loading || runtimeFallback) {
    return (
      <FallbackInput
        value={value}
        displayValue={displayValue}
        onChange={onChange}
        onSubmit={onSubmit}
        onClear={onClear}
        disabled={disabled}
        placeholder={placeholder}
        ariaLabel={ariaLabel}
        className={className}
      />
    );
  }

  return (
    <div className="relative stock-autocomplete">
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => {
          const raw = e.target.value;
          setEditingValue(raw); // 标记正在编辑，使用原始输入值
          onChange(raw);
        }}
        onKeyDown={handleKeyDown}
        onCompositionStart={handleCompositionStart}
        onCompositionEnd={handleCompositionEnd}
        onFocus={() => {
          if (isOpen) {
            updateDropdownPosition();
          }
        }}
        onBlur={handleBlur}
        placeholder={placeholder}
        aria-label={ariaLabel}
        disabled={disabled}
        className={cn(
          AUTOCOMPLETE_INPUT_CLASS,
          isOpen && "rounded-b-none",
          inputValue && onClear && 'pr-9',
          className
        )}
        aria-autocomplete="none"
        role="combobox"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-controls="suggestions-list"
      />

      {/* 清除按钮：有内容时显示 X 图标 */}
      {inputValue && onClear && !disabled && (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 flex h-6 w-6 items-center justify-center rounded-full text-muted-text transition-colors hover:bg-foreground/10 hover:text-foreground z-10"
          aria-label="清除输入"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      )}

      {/* Loading indicator */}
      {loading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="w-4 h-4 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
        </div>
      )}

      {/* Suggestion dropdown list */}
      {isOpen && dropdownStyle && createPortal(
        <SuggestionsList
          suggestions={suggestions}
          highlightedIndex={highlightedIndex}
          onSelect={(s) => {
            justSelectedRef.current = true; // 阻止同步效应重新触发搜索
            setEditingValue(null); // 选择建议时清除编辑状态
            // Update external value (shown in input box)
            onChange(s.displayCode);
            // Close dropdown list
            closeSuggestions();
            // Submit analysis
            onSubmit(s.canonicalCode, s.nameZh, 'autocomplete', {
              market: s.market,
              displayCode: s.displayCode,
            });
          }}
          onMouseEnter={(index) => setHighlightedIndex(index)}
          style={{ position: 'fixed', ...dropdownStyle }}
        />,
        document.body
      )}
    </div>
  );
}

export function StockAutocomplete(props: StockAutocompleteProps) {
  return (
    <StockAutocompleteBoundary {...props}>
      <StockAutocompleteInner {...props} />
    </StockAutocompleteBoundary>
  );
}

export default StockAutocomplete;
