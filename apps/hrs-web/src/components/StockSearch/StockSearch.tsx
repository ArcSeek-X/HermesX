/**
 * 股票搜索输入框：本地索引模糊匹配、键盘导航与输入法组合态处理。
 * 下拉经 Portal 挂 body 避免被父级裁切；渲染异常由错误边界整体卸载。
 */

import { Component, useCallback, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, ErrorInfo, ReactNode } from 'react';
import { SearchField } from '@heroui/react';
import { createPortal } from 'react-dom';
import { useStockIndex } from '../../hooks/useStockIndex';
import { useStockAutocomplete } from '../../hooks/useStockAutocomplete';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { SEARCH_CONFIG } from '../../utils/stockIndexSchema';
import { searchStocks } from '../../utils/searchStocks';
import { getStockDisplayLabel } from '../../utils/stock/stockNameDisplay';
import { StockSearchList } from './StockSearchList';
import { cn } from '../../utils/cn';
import type { StockSuggestion } from '../../types/stockIndex';
import type { StockSearchSelection, StockSearchSize } from './types';

const SEARCH_FIELD_SIZE_CLASS: Record<StockSearchSize, string> = {
  xs: '!h-7 !rounded-xs !text-xs',
  sm: '!h-8 !rounded-sm !text-xs',
  md: '!h-9 !rounded-md !text-sm',
  lg: '!h-10 !rounded-md !text-sm',
  xl: '!h-12 !rounded-md !text-sm',
};

/** 失焦后延迟收起下拉，给候选点击留出触发窗口 */
const SUGGESTION_BLUR_CLOSE_DELAY_MS = 200;

export interface StockSearchProps {
  ariaLabel?: string;
  /** 受控值，通常是解析后的纯代码 */
  value: string;
  /** 展示标签「名称（规范代码）」；仅用于初始化 / 重置，优先级：编辑原文 > 本值 > value */
  displayValue?: string;
  onChange: (value: string) => void;
  onSubmit: (stock: StockSearchSelection) => void;
  disabled?: boolean;
  size?: StockSearchSize;
  className?: string;
  onClear?: () => void;
  /** 原位渲染下拉（默认经 Portal 挂 body） */
  originalRender?: boolean;
}

/** 渲染异常时整体卸载搜索框，避免破损 UI 扩散到页面其它区域 */
class StockSearchBoundary extends Component<{ children: ReactNode }, { hasRenderError: boolean }> {
  override state = { hasRenderError: false };

  static getDerivedStateFromError(): { hasRenderError: boolean } {
    return { hasRenderError: true };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('StockSearch render error; search box unmounted.', error, errorInfo);
  }

  override render() {
    return this.state.hasRenderError ? null : this.props.children;
  }
}

function StockSearchInner({
  ariaLabel,
  value,
  displayValue,
  onChange,
  onSubmit,
  onClear,
  disabled = false,
  size = 'sm',
  className,
  originalRender = false,
}: StockSearchProps) {
  const { t } = useUiLanguage();
  const { index: stockIndex, loading: isStockIndexLoading } = useStockIndex();
  const {
    setQuery: updateSuggestionQuery,
    suggestions: stockSuggestions,
    isOpen: isSuggestionDropdownOpen,
    highlightedIndex: highlightedSuggestionIndex,
    setHighlightedIndex: setHighlightedSuggestionIndex,
    highlightPrevious: highlightPreviousSuggestion,
    highlightNext: highlightNextSuggestion,
    close: closeAutocomplete,
    reset: resetAutocomplete,
    runtimeFallback: isAutocompleteRuntimeFallback,
    isComposing: isImeComposing,
    setIsComposing: setIsImeComposing,
    error: autocompleteError,
  } = useStockAutocomplete(stockIndex);

  const searchFieldGroupRef = useRef<HTMLDivElement>(null);
  const previousStockCodeRef = useRef(value);
  const previousStockLabelRef = useRef(displayValue);
  const isClearInFlightRef = useRef(false);
  const [suggestionDropdownPosition, setSuggestionDropdownPosition] = useState<{
    top: number;
    left: number;
    width: string;
  } | null>(null);
  const [stockQueryDraft, setStockQueryDraft] = useState<string | null>(null);
  const [confirmedStockLabel, setConfirmedStockLabel] = useState(displayValue ?? '');

  const visibleInputText = stockQueryDraft ?? (confirmedStockLabel || value);
  const stockSearchPlaceholder = t('component.stockSearch.placeholder');

  const syncSuggestionDropdownPosition = useCallback(() => {
    if (!searchFieldGroupRef.current) {
      setSuggestionDropdownPosition(null);
      return;
    }
    const groupRect = searchFieldGroupRef.current.getBoundingClientRect();
    setSuggestionDropdownPosition({
      top: groupRect.bottom,
      left: groupRect.left,
      width: `${groupRect.width}px`,
    });
  }, []);

  const closeSuggestionDropdown = () => {
    // close() 会取消挂起防抖，否则定时器到期后下拉会重新弹出
    closeAutocomplete();
    setSuggestionDropdownPosition(null);
  };

  // ClearButton 会同时触发 onChange('') 与 onClear，去重保证一次点击只清空一次
  const handleStockSearchClear = () => {
    if (isClearInFlightRef.current) return;
    isClearInFlightRef.current = true;
    setStockQueryDraft(null);
    setConfirmedStockLabel('');
    resetAutocomplete();
    closeSuggestionDropdown();
    onChange('');
    onClear?.();
    queueMicrotask(() => {
      isClearInFlightRef.current = false;
    });
  };

  const commitStockSuggestion = (suggestion: StockSuggestion) => {
    setStockQueryDraft(null);
    const displayLabel = getStockDisplayLabel(suggestion.name, suggestion.canonicalCode);
    setConfirmedStockLabel(displayLabel);
    onChange(suggestion.displayCode);
    closeSuggestionDropdown();
    onSubmit({
      ...suggestion,
      code: suggestion.displayCode,
      displayLabel,
      source: 'autocomplete',
    });
  };

  const handleStockSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (isImeComposing) return;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        highlightNextSuggestion();
        break;
      case 'ArrowUp':
        event.preventDefault();
        highlightPreviousSuggestion();
        break;
      case 'Enter': {
        event.preventDefault();
        // 提交可见文本而非外部 value：快速输入后回车时 value 可能仍是上一轮旧值
        const submittedText = visibleInputText.trim();
        setStockQueryDraft(null);

        // 防抖未结算时候选为空：同步查一次本地索引，精确命中即可直接提交。
        // 运行时降级时保持「回车提交原文」的语义，不伪装成 autocomplete 选中。
        let suggestionToCommit: StockSuggestion | undefined = stockSuggestions[highlightedSuggestionIndex];
        if (!suggestionToCommit && !isAutocompleteRuntimeFallback && submittedText) {
          const numericStockCode = submittedText.match(/\d{4,7}/)?.[0] ?? '';
          suggestionToCommit = searchStocks(numericStockCode || submittedText, stockIndex, { limit: 1 }).find(
            (matched) => matched.matchType === 'exact',
          );
        }
        if (!suggestionToCommit) suggestionToCommit = stockSuggestions[0];
        if (suggestionToCommit) {
          commitStockSuggestion(suggestionToCommit);
          break;
        }

        closeSuggestionDropdown();
        if (submittedText) {
          onSubmit({
            canonicalCode: submittedText,
            code: submittedText,
            displayLabel: submittedText,
            source: 'manual',
          });
        }
        break;
      }
      case 'Escape':
        event.preventDefault();
        closeSuggestionDropdown();
        break;
    }
  };

  useEffect(() => {
    if (previousStockLabelRef.current !== displayValue) {
      previousStockLabelRef.current = displayValue;
      setConfirmedStockLabel(displayValue ?? '');
    }
  }, [displayValue]);

  // 只有用户正在编辑时才把外部 value 同步进搜索；回填已确认股票只收起下拉，不要求二次确认
  useEffect(() => {
    if (previousStockCodeRef.current === value) return;
    previousStockCodeRef.current = value;
    if (value === '') {
      setConfirmedStockLabel('');
      setStockQueryDraft(null);
    }
    if (stockQueryDraft === null) {
      closeAutocomplete();
      setSuggestionDropdownPosition(null);
      return;
    }
    updateSuggestionQuery(value);
  }, [value, updateSuggestionQuery, stockQueryDraft, closeAutocomplete]);

  useEffect(() => {
    if (!isSuggestionDropdownOpen) return;

    const frameId = window.requestAnimationFrame(syncSuggestionDropdownPosition);
    window.addEventListener('resize', syncSuggestionDropdownPosition);
    window.addEventListener('scroll', syncSuggestionDropdownPosition, true);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener('resize', syncSuggestionDropdownPosition);
      window.removeEventListener('scroll', syncSuggestionDropdownPosition, true);
    };
  }, [isSuggestionDropdownOpen, syncSuggestionDropdownPosition]);

  useEffect(() => {
    if (autocompleteError) {
      console.error('Autocomplete runtime fallback activated.', autocompleteError);
    }
  }, [autocompleteError]);

  const renderSuggestionDropdown = () => {
    if (!isSuggestionDropdownOpen || !suggestionDropdownPosition) return null;
    const suggestionDropdown = (
      <StockSearchList
        size={size}
        stockSuggestions={stockSuggestions}
        highlightedSuggestionIndex={highlightedSuggestionIndex}
        onSelectSuggestion={commitStockSuggestion}
        onHighlightSuggestion={setHighlightedSuggestionIndex}
        onClearSuggestionHighlight={() => setHighlightedSuggestionIndex(-1)}
        style={{ position: 'fixed', ...suggestionDropdownPosition }}
      />
    );
    return originalRender ? suggestionDropdown : createPortal(suggestionDropdown, document.body);
  };

  return (
    // stock-autocomplete 是 global.scss 中首页 placeholder/边框覆盖的选择器钩子，不可删
    <div className="relative stock-autocomplete">
      <SearchField
        name="stock-search"
        value={visibleInputText}
        // react-aria 的 ClearButton 走 onClear，不能只依赖 onChange('')，否则展示标签可能残留
        onClear={handleStockSearchClear}
        onChange={(raw: string) => {
          if (raw === '') {
            handleStockSearchClear();
            return;
          }
          setStockQueryDraft(raw || null);
          setConfirmedStockLabel('');
          updateSuggestionQuery(raw);
          onChange(raw);
        }}
      >
        <SearchField.Group
          ref={searchFieldGroupRef}
          className={cn(
            SEARCH_FIELD_SIZE_CLASS[size],
            'w-full flex items-center transition-all border focus:outline-none',
            '!shadow-xs disabled:cursor-not-allowed disabled:opacity-60',
            'focus:!border-border focus:!shadow-[0_0_0_2px_hsl(var(--primary)/0.10)]',
            isSuggestionDropdownOpen && '!rounded-b-none border-b-0',
            className,
          )}
        >
          <SearchField.SearchIcon />
          <SearchField.Input
            type="text"
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            className="h-full !placeholder:text-xs ![overflow:visible] ![text-overflow:clip]"
            disabled={disabled}
            placeholder={stockSearchPlaceholder}
            aria-label={ariaLabel ?? stockSearchPlaceholder}
            onKeyDown={handleStockSearchKeyDown}
            onCompositionStart={() => setIsImeComposing(true)}
            onCompositionEnd={() => setIsImeComposing(false)}
            onFocus={() => {
              // 已确认的展示标签不重新搜索；开始输入后由 onChange 展开候选
              if (!confirmedStockLabel && visibleInputText.length >= SEARCH_CONFIG.MIN_QUERY_LENGTH) {
                updateSuggestionQuery(visibleInputText);
              }
              if (isSuggestionDropdownOpen) syncSuggestionDropdownPosition();
            }}
            onBlur={() => {
              setStockQueryDraft(null);
              setTimeout(() => closeSuggestionDropdown(), SUGGESTION_BLUR_CLOSE_DELAY_MS);
            }}
            aria-autocomplete="none"
            role="combobox"
            aria-expanded={isSuggestionDropdownOpen}
            aria-haspopup="listbox"
            aria-controls="suggestions-list"
          />
          {visibleInputText && onClear && !disabled && (
            <SearchField.ClearButton aria-label={t('common.clear')} />
          )}
        </SearchField.Group>
      </SearchField>

      {isStockIndexLoading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="w-4 h-4 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
        </div>
      )}

      {renderSuggestionDropdown()}
    </div>
  );
}

export function StockSearch(props: StockSearchProps) {
  return (
    <StockSearchBoundary>
      <StockSearchInner {...props} />
    </StockSearchBoundary>
  );
}

export default StockSearch;
