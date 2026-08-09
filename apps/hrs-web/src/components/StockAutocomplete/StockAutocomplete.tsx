/**
 * StockAutocomplete —— 股票代码/名称搜索输入框组件
 *
 * 文件作用：
 * 提供带"输入即提示"的股票搜索输入框，是整个前端复用的搜索入口（K 线页、聊天页等）。
 * 组件职责：
 *   1. 通过 useStockIndex 加载本地股票索引，useAutocomplete（股票搜索自动补全）做
 *      代码/中文名/拼音全拼/拼音简拼/别名的本地模糊匹配，并渲染下拉候选列表；
 *   2. 支持键盘导航（↑/↓ 移动高亮、Enter 提交、Esc 收起）、IME 输入法组合态处理；
 *   3. 多层降级保护：索引加载失败（fallback）、搜索运行时异常（runtimeFallback）、
 *      渲染异常（ErrorBoundary）时，一律退化为普通输入框（FallbackInput），
 *      保证搜索输入能力不整体失效；
 *   4. 下拉框通过 createPortal 挂到 document.body，避免被父级 overflow 裁剪。
 *
 * 对外契约：
 *   - onChange：输入内容变化（原始文本）
 *   - onSubmit(code, name, source, metadata)：提交搜索，code 为规范代码（如 600519.SH）
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

/** 输入框统一样式类：圆角、聚焦光晕、禁用态等（两种模式共用，保证外观一致） */
const AUTOCOMPLETE_INPUT_CLASS =
  'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';

/** StockAutocomplete 组件对外 Props */
export interface StockAutocompleteProps {
  /** 输入值（用于搜索逻辑，通常是解析后的纯代码） */
  value: string;
  /** 输入框展示值（可选，如"中科曙光（603019）"，缺省时回退到 value） */
  displayValue?: string;
  /** 输入内容变化回调（参数为输入框原始文本） */
  onChange: (value: string) => void;
  /** 提交回调：携带规范代码、名称、来源（手动输入/下拉选择）与元信息（市场、展示代码） */
  onSubmit: (
    code: string,
    name?: string,
    source?: 'manual' | 'autocomplete',
    metadata?: { market?: Market; displayCode?: string },
  ) => void;
  /** 是否禁用输入框 */
  disabled?: boolean;
  /** 占位提示文案 */
  placeholder?: string;
  /** 无障碍标签（aria-label） */
  ariaLabel?: string;
  /** 附加 CSS 类名 */
  className?: string;
  /** 点击清除按钮时的回调 */
  onClear?: () => void;
}

/**
 * FallbackInput —— 降级用的普通输入框
 *
 * 触发场景：股票索引加载失败/加载中、自动补全运行时异常、组件渲染异常时，
 * 由外层统一退化为本组件。功能最小化：仅支持输入、回车提交、清除按钮，
 * 提交时把当前输入原文交给 onSubmit（由调用方走后端搜索解析）。
 */
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
  // 输入框显示内容优先级：编辑中的原文 > displayValue（如"名称（代码）"）> value
  const inputValue = editingValue ?? displayValue ?? value;
  return (
    <div className="relative">
      <input
        type="text"
        value={inputValue}
        onChange={(e) => {
          const raw = e.target.value;
          setEditingValue(raw); // 记录编辑态，显示用户输入原文
          onChange(raw);        // 同步给外部（调用方解析并更新 value）
        }}
        onKeyDown={(e) => {
          // 回车提交：有输入内容时把当前值交回 onSubmit（外部会做后端搜索解析）
          if (e.key === 'Enter' && !disabled && value) {
            e.preventDefault(); // 阻止表单默认提交，避免页面刷新
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
          inputValue && onClear && 'pr-9', // 有清除按钮时预留右侧空间
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

/** 错误边界 Props：在 StockAutocompleteProps 基础上追加 children */
interface StockAutocompleteBoundaryProps extends StockAutocompleteProps {
  children: ReactNode;
}

/** 错误边界 State：仅记录是否发生渲染异常 */
interface StockAutocompleteBoundaryState {
  hasError: boolean;
}

/**
 * StockAutocompleteBoundary —— 渲染错误边界（class 组件）
 *
 * 作用：捕获 StockAutocompleteInner 渲染期异常（如 hooks 契约不匹配、候选数据异常），
 * 一旦捕获立即降级渲染 FallbackInput，避免整个页面因搜索框白屏。
 * 这是"最后一道防线"：正常情况下 fallback/runtimeFallback 已覆盖降级路径。
 */
class StockAutocompleteBoundary extends Component<
  StockAutocompleteBoundaryProps,
  StockAutocompleteBoundaryState
> {
  override state: StockAutocompleteBoundaryState = { hasError: false };

  /** 渲染出错时进入降级状态 */
  static getDerivedStateFromError(): StockAutocompleteBoundaryState {
    return { hasError: true };
  }

  /** 记录异常信息（供排查） */
  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Autocomplete runtime error. Falling back to plain input.', error, errorInfo);
  }

  override render() {
    // 已降级：剥离 children 后把其余 Props 交给 FallbackInput
    if (this.state.hasError) {
      const { children, ...fallbackProps } = this.props;
      void children;
      return <FallbackInput {...fallbackProps} />;
    }

    // 正常渲染子树
    return this.props.children;
  }
}

/**
 * StockAutocompleteInner —— 自动补全输入框主体
 *
 * 数据流：
 *   useStockIndex() 提供本地股票索引 → useAutocomplete(index) 提供
 *   候选列表/下拉开关/键盘高亮/IME 状态 → 本组件负责把它们绑定到输入框交互上。
 *
 * 关键交互细节：
 *   - value（外部受控）与内部 query 通过 useEffect 同步，但用户刚选中候选时
 *     用 justSelectedRef 跳过同步，避免选中后重复触发搜索；
 *   - 下拉框用 fixed 定位 + createPortal 渲染，随滚动/缩放实时重算位置。
 */
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
  // 股票索引：加载本地 /stocks.index.json；fallback=true 时降级为普通输入框
  const { index, loading, fallback } = useStockIndex();
  // 自动补全逻辑：本地模糊搜索（代码/名称/拼音/简拼/别名）+ 键盘高亮 + IME 状态
  const {
    // query,             // 内部查询词由 setQuery 维护，组件未直接读取
    setQuery,
    suggestions,          // 候选列表
    isOpen,               // 下拉是否展开
    highlightedIndex,     // 键盘高亮项索引
    setHighlightedIndex,  // 手动设置高亮（鼠标悬停时用）
    highlightPrevious,    // 高亮上移
    highlightNext,        // 高亮下移
    close,                // 关闭下拉
    // reset,             // 整体重置由外部触发（清空按钮走 onClear）
    isComposing,          // 是否处于输入法组合输入中
    setIsComposing,       // 设置输入法组合状态
    runtimeFallback,      // 搜索逻辑异常降级标记
    error: autocompleteError, // 自动补全运行时错误
  } = useAutocomplete(index);

  const inputRef = useRef<HTMLInputElement>(null);
  const prevValueRef = useRef(value);      // 上一次的外部 value，用于比较是否真变化
  const justSelectedRef = useRef(false);  // 标记刚刚完成了选择，阻止同步效应重新触发搜索
  // 下拉框定位（fixed）：top/left/width，随输入框位置与尺寸变化重算
  const [dropdownStyle, setDropdownStyle] = useState<{ top: number; left: number; width: string } | null>(null);
  // 编辑状态：用户正在编辑输入框时，使用原始输入值而非 displayValue
  // 避免 displayValue（如"名称（代码）"）覆盖用户的编辑操作
  const [editingValue, setEditingValue] = useState<string | null>(null);

  /** 依据输入框当前 DOM 位置计算下拉框的 fixed 定位 */
  const updateDropdownPosition = () => {
    if (!inputRef.current) {
      setDropdownStyle(null);
      return;
    }

    const rect = inputRef.current.getBoundingClientRect();
    setDropdownStyle({
      top: rect.bottom,   // 下拉框紧贴输入框下沿
      left: rect.left,
      width: `${rect.width}px`, // 与输入框同宽
    });
  };

  /** 关闭下拉并清空定位（失焦、Esc、提交等场景统一入口） */
  const closeSuggestions = () => {
    close();
    setDropdownStyle(null);
  };

  // 输入框显示值：编辑中显示用户原文，否则显示 displayValue（如"名称（代码）"）或 value
  const inputValue = editingValue ?? displayValue ?? value;

  // 外部 value 与内部 query 同步：仅当 value 真正变化时把 setQuery 同步过去，
  // 保证外部受控值（如清空、选中后回填）能反映到内部搜索状态；
  // 若刚完成下拉选择（justSelectedRef），跳过本次同步——选中时已通过 onChange
  // 更新了外部 value，无需再触发一次搜索。
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

  // 下拉框位置同步：展开时先算一次位置，并监听窗口 resize 与页面滚动
  // （capture=true 捕获所有滚动容器）实时重算，避免下拉框与输入框错位。
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

  // 自动补全运行时异常时输出错误日志，便于定位降级原因
  useEffect(() => {
    if (!autocompleteError) {
      return;
    }

    console.error('Autocomplete runtime fallback activated.', autocompleteError);
  }, [autocompleteError]);

  /**
   * 键盘事件处理：
   * - 输入法组合期间（isComposing）不响应，避免中文输入时误触快捷键；
   * - ↑/↓：移动高亮（useAutocomplete 内部做循环）；
   * - Enter：有高亮项时提交该项，否则把输入原文直接提交；
   * - Esc：收起下拉。
   */
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
          // 有高亮项：提交该项（规范代码 + 名称 + 来源 autocomplete + 市场元信息）
          const selected = suggestions[highlightedIndex];
          justSelectedRef.current = true; // 阻止同步效应重新触发搜索
          onChange(selected.displayCode);
          closeSuggestions();
          onSubmit(selected.canonicalCode, selected.nameZh, 'autocomplete', {
            market: selected.market,
            displayCode: selected.displayCode,
          });
        } else {
          // 无高亮项：把输入原文直接提交（调用方会解析，如后端搜索）
          onSubmit(value);
        }
        break;
      case 'Escape':
        e.preventDefault();
        closeSuggestions();
        break;
    }
  };

  // IME 组合开始：标记组合态，键盘处理期间忽略快捷键
  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  // IME 组合结束：恢复键盘处理
  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  // 失焦：清除编辑态恢复展示值；延迟 200ms 关闭下拉，
  // 给点击下拉项留出事件窗口（避免点击建议时下拉已先消失）
  const handleBlur = () => {
    setEditingValue(null); // 失焦时清除编辑状态，恢复 displayValue
    setTimeout(() => closeSuggestions(), 200);
  };

  // 降级路径：索引加载中/加载失败（fallback）或搜索运行时异常（runtimeFallback）时，
  // 渲染普通输入框，仅保留"输入 + 回车提交 + 清除"基础能力
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

  // 正常模式：自动补全输入框 + 清除按钮 + 加载指示 + 下拉候选列表
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
          // 重新聚焦时若下拉已展开，重算一次位置（布局可能已变化）
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
          isOpen && "rounded-b-none", // 下拉展开时去掉下圆角，与列表无缝衔接
          inputValue && onClear && 'pr-9',
          className
        )}
        // 无障碍：combobox 语义 + 展开状态与下拉列表关联
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

      {/* Loading indicator：索引加载中显示转圈（正常模式下加载完才渲染列表） */}
      {loading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="w-4 h-4 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
        </div>
      )}

      {/* Suggestion dropdown list：下拉候选列表，通过 Portal 挂到 body，避免被父级裁剪 */}
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

/**
 * StockAutocomplete 对外入口
 *
 * 用错误边界包裹内部实现：渲染期任何异常都会降级为普通输入框，
 * 保证搜索输入功能可用性，不拖垮整个页面。
 */
export function StockAutocomplete(props: StockAutocompleteProps) {
  return (
    <StockAutocompleteBoundary {...props}>
      <StockAutocompleteInner {...props} />
    </StockAutocompleteBoundary>
  );
}

/** 默认导出（与具名导出等价） */
export default StockAutocomplete;
