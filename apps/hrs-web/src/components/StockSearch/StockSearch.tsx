/**
 * StockSearch —— 股票代码/名称搜索输入框
 *
 * 前端复用的搜索入口（K 线页、聊天页、首页等）。基于本地股票索引做代码/名称/
 * 拼音/别名的模糊匹配，提供键盘导航、输入法组合态处理，并通过 ErrorBoundary
 * 与 Portal 保证交互稳定、不被父级裁切。
 *
 * 对外回调：
 *   - onChange(raw)：输入框文本变化（原始输入，未标准化）
 *   - onSubmit(code, name, source, metadata)：选中或回车时触发
 *
 * 使用示例：
 *   <StockSearch
 *     value={code}
 *     displayValue={label}               // 可选，仅用于初始化 / 外部重置展示
 *     onChange={(raw) => setCode(raw)}   // raw 为输入框原始文本
 *     onSubmit={(code, name, source, meta) => {
 *       // 下拉选中「贵州茅台」后输出：
 *       //   code    = '600519.SH'  规范代码（带市场后缀）
 *       //   name    = '贵州茅台'
 *       //   source  = 'autocomplete'
 *       //   meta    = { marketTag: 'CN', displayCode: '600519',
 *       //              displayLabel: '贵州茅台（600519.SH）' }
 *       // 手动输入且未命中候选时 source = 'manual'，code 为原始输入文本。
 *     }}
 *   />
 *
 * @author Lensgcx (GaoCangxiong)
 */

import { Component, useRef, useEffect, useState } from 'react';
import type { KeyboardEvent, ErrorInfo, ReactNode } from 'react';
import { SearchField } from '@heroui/react';
import { createPortal } from 'react-dom';
import { useStockIndex } from '../../hooks/useStockIndex';
import { useStockAutocomplete } from '../../hooks/useStockAutocomplete';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { SEARCH_CONFIG } from '../../utils/stockIndexSchema';
import { StockSearchList } from './StockSearchList';
import { cn } from '../../utils/cn';
import type { StockSelectionMeta } from '../../types/stock';
import type { StockSuggestion } from '../../types/stockIndex';


/** StockSearch 组件对外 Props */
export interface StockSearchProps {
  /** 输入值（用于搜索逻辑，通常是解析后的纯代码） */
  value: string;
  /**
   * 输入框展示值（可选），组件的唯一展示通道。
   * 统一格式为「名称（规范代码）」，如「中科曙光（603019.SH）」，由组件内部拼装，
   * 调用方无需自行拼接市场后缀。外部传入仅用于初始化 / 外部重置展示；用户在组件内
   * 完成选择后，展示以组件内部赋值为准。展示优先级：编辑原文 > displayValue > value。
   */
  displayValue?: string;
  /** 输入内容变化回调（参数为输入框原始文本） */
  onChange: (value: string) => void;
  /** 提交回调：携带规范代码、名称、来源（手动输入/下拉选择）与元信息 StockSelectionMeta（marketTag、展示代码、展示标签） */
  onSubmit: (
    code: string,
    name?: string,
    source?: 'manual' | 'autocomplete',
    metadata?: StockSelectionMeta,
  ) => void;
  /** 是否禁用输入框 */
  disabled?: boolean;
  /** 尺寸：xs | sm | md | lg，控制输入框高度、字体大小与圆角（默认 md） */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** 附加 CSS 类名 */
  className?: string;
  /** 点击清除按钮时的回调 */
  onClear?: () => void;
  /**
   * 下拉候选列表渲染方式：
   *   - true  -> 原位渲染（不使用 portal），作为当前组件 DOM 树的一部分；
   *   - false（默认）-> 通过 createPortal 挂到 document.body，避免被父级 overflow/transform 裁切。
   * 注意：无论哪种方式，StockSearchList 内部都会主动清除 react-aria Modal 设置的 inert，
   * 以保证在弹窗内下拉的点击/键盘交互可用。
   */
  originalRender?: boolean;
}

/** 错误边界 Props：在 StockSearchProps 基础上追加 children */
interface StockSearchBoundaryProps extends StockSearchProps {
  children: ReactNode;
}

/**
 * 拼装选中股票在输入框中的展示标签："名称（规范代码）"，如"中科曙光（603019.SH）"。
 *
 * 说明：
 * - 规范代码（canonicalCode）带市场后缀（.SH/.SZ/.HK/.US），信息最完整，便于用户二次确认，
 *   因此展示用它而非纯数字 displayCode；
 * - 名称缺失时退化为仅展示规范代码，避免渲染出"（603019.SH）"这种空名称格式。
 */
function buildDisplayLabel(name?: string, canonicalCode?: string): string {
  if (!canonicalCode) return name ?? '';
  if (!name) return canonicalCode;
  return `${name}（${canonicalCode}）`;
}

/** 错误边界 State：仅记录是否发生渲染异常 */
interface StockSearchBoundaryState {
  hasError: boolean;
}

/**
 * StockSearchBoundary —— 渲染错误边界（class 组件）
 *
 * 作用：捕获 StockSearchInner 渲染期异常（如 hooks 契约不匹配、候选数据异常），
 * 一旦捕获则整体不挂载搜索框（不再降级为普通输入框），避免破损 UI 扩散到页面其它区域。
 */
class StockSearchBoundary extends Component<
  StockSearchBoundaryProps,
  StockSearchBoundaryState
> {
  override state: StockSearchBoundaryState = { hasError: false };

  /** 渲染出错时进入降级状态 */
  static getDerivedStateFromError(): StockSearchBoundaryState {
    return { hasError: true };
  }

  /** 记录异常信息（供排查） */
  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('StockSearch render error; search box unmounted.', error, errorInfo);
  }

  override render() {
    // 渲染异常时已移除降级输入框，异常状态下整体不挂载搜索框，避免破损 UI
    if (this.state.hasError) {
      return null;
    }

    // 正常渲染子树
    return this.props.children;
  }
}

/**
 * StockSearchInner —— 自动补全输入框主体
 *
 * 数据流：useStockIndex 提供本地索引 → useStockAutocomplete 提供候选/下拉开关/
 * 键盘高亮/IME 状态 → 本组件将其绑定到输入框交互。下拉用 fixed 定位 + Portal 渲染，
 * 随滚动/缩放实时重算位置；选中候选后用 justSelectedRef 阻止 value 同步重复触发搜索。
 */
function StockSearchInner({
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
  // 界面语言：默认占位符与清除按钮无障碍标签走 i18n（规范：component.stockSearch.*）
  const { t } = useUiLanguage();
  // 本地股票索引（含加载状态），补全逻辑依赖它做模糊匹配
  const { index, loading: indexLoading } = useStockIndex();
  // 自动补全逻辑：本地模糊搜索（代码/名称/拼音/简拼/别名）+ 键盘高亮 + IME 状态
  const {
    setQuery,
    suggestions,
    isOpen,
    highlightedIndex,
    setHighlightedIndex,
    highlightPrevious,
    highlightNext,
    close,
    isComposing,
    setIsComposing,
    error: autocompleteError, // 与上方 error 区分
  } = useStockAutocomplete(index);

  // size -> 输入框尺寸/字体/圆角映射；用 ! 强制前缀覆盖 HeroUI Group 自带样式，
  // 高度只作用于 Group，Input 以 h-full 跟随撑满，避免两者高度冲突。
  const SIZE_CLASS: Record<'xs' | 'sm' | 'md' | 'lg' | 'xl', string> = {
    xs: '!h-7 !rounded-xs !text-xs ',
    sm: '!h-8 !rounded-sm !text-xs ',
    md: '!h-9 !rounded-md !text-sm ',
    lg: '!h-10 !rounded-md !text-sm ',
    xl: '!h-12 !rounded-md !text-sm ',
  };

  const inputRef = useRef<HTMLInputElement>(null);
  const groupRef = useRef<HTMLDivElement>(null); // 用于对齐下拉框宽度/位置
  const prevValueRef = useRef(value);            // 上一次外部 value，判断是否真变化
  const justSelectedRef = useRef(false);         // 刚完成选择时阻止同步效应重复触发搜索
  const [dropdownStyle, setDropdownStyle] = useState<{ top: number; left: number; width: string } | null>(null);
  const [editingValue, setEditingValue] = useState<string | null>(null); // 编辑中原文，优先于展示通道
  const [displayText, setDisplayText] = useState(displayValue ?? '');    // 展示通道：「名称（代码）」

  // 下拉框 fixed 定位：以 Group 边界为准，保证宽度与视觉外框（含图标/清除按钮）对齐。
  const updateDropdownPosition = () => {
    if (!groupRef.current) {
      setDropdownStyle(null);
      return;
    }

    const rect = groupRef.current.getBoundingClientRect();
    setDropdownStyle({
      top: rect.bottom,
      left: rect.left,
      width: `${rect.width}px`,
    });
  };

  // 收起下拉并清空定位（失焦、Esc、提交等统一入口）
  const closeSuggestions = () => {
    close();
    setDropdownStyle(null);
  };

  // 外部 displayValue 变化（初始化 / 外部重置）时同步进展示通道；
  // 组件内选择不走这里，因此不会覆盖内部赋值。
  const prevDisplayValueRef = useRef(displayValue);
  useEffect(() => {
    if (prevDisplayValueRef.current !== displayValue) {
      prevDisplayValueRef.current = displayValue;
      setDisplayText(displayValue ?? '');
    }
  }, [displayValue]);

  // 显示值优先级：编辑原文 > 展示通道 > value（纯代码）
  const inputValue = editingValue ?? (displayText || undefined) ?? value;

  const placeholder = t('component.stockSearch.placeholder');

  // 外部 value 变化时同步进内部搜索；刚完成下拉选择（justSelectedRef）时跳过，
  // 避免选中回填的 value 再次触发搜索。
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

  // 下拉展开时计算一次位置，并监听窗口 resize 与滚动（capture 捕获所有滚动容器）实时重算。
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

  // 自动补全运行时异常时记录日志，便于定位降级原因
  useEffect(() => {
    if (autocompleteError) {
      console.error('Autocomplete runtime fallback activated.', autocompleteError);
    }
  }, [autocompleteError]);

  // 键盘交互：组合输入期间忽略快捷键；↑/↓ 移动高亮；Enter 选中（无候选时提交原文）；Esc 收起。
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
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
        setEditingValue(null);
        if (suggestions.length > 0) {
          // 未高亮时默认取首项，使输入中文名回车即可自动匹配为对应股票
          selectSuggestion(suggestions[highlightedIndex] ?? suggestions[0]);
        } else {
          onSubmit(value);
        }
        break;
      case 'Escape':
        e.preventDefault();
        closeSuggestions();
        break;
    }
  };

  const handleCompositionStart = () => setIsComposing(true);
  const handleCompositionEnd = () => setIsComposing(false);

  // 失焦清除编辑态，并延迟关闭下拉以保留点击候选的事件窗口
  const handleBlur = () => {
    setEditingValue(null);
    setTimeout(() => closeSuggestions(), 200);
  };

  // 选中某条候选：写入展示通道、回填纯代码、收起下拉并触发 onSubmit
  const selectSuggestion = (s: StockSuggestion) => {
    justSelectedRef.current = true;
    setEditingValue(null);
    const label = buildDisplayLabel(s.name, s.canonicalCode);
    setDisplayText(label);
    onChange(s.displayCode);
    closeSuggestions();
    onSubmit(s.canonicalCode, s.name, 'autocomplete', {
      marketTag: s.market,
      displayCode: s.displayCode,
      displayLabel: label,
    });
  };

  // 下拉候选列表：originalRender=false（默认）经 Portal 挂 body 避免被父级裁切；
  // originalRender=true 则原位渲染，并规避 react-aria Modal 的 inert 限制。
  const renderSuggestions = () => {
    if (!isOpen || !dropdownStyle) return null;
    const list = (
      <StockSearchList
        size={size}
        suggestions={suggestions}
        highlightedIndex={highlightedIndex}
        onSelect={selectSuggestion}
        onMouseEnter={setHighlightedIndex}
        onMouseLeave={() => setHighlightedIndex(-1)}
        style={{ position: 'fixed', ...dropdownStyle }}
      />
    );
    return originalRender ? list : createPortal(list, document.body);
  };

  return (
    <div className="relative stock-autocomplete">
      <SearchField
        name="stock-search"
        aria-label="stock-search-Field"
        value={inputValue}
        onChange={(raw: string) => {
          setEditingValue(raw || null);
          setDisplayText('');
          onChange(raw);
          if (raw === '' && onClear) {
            onClear();
          }
        }}
      >
        <SearchField.Group
          ref={groupRef}
          className={cn(
            SIZE_CLASS[size],
            'w-full flex items-center transition-all border focus:outline-none',
            '!shadow-xs disabled:cursor-not-allowed disabled:opacity-60',
            // 聚焦时仅保留一圈淡光圈，不改变外框颜色
            'focus:!border-border focus:!shadow-[0_0_0_2px_hsl(var(--primary)/0.10)]',
            // 下拉展开时去掉下圆角与下边框，与候选列表共用一条底边
            isOpen && '!rounded-b-none border-b-0',
            className,
          )}
        >
          <SearchField.SearchIcon />
          <SearchField.Input
            ref={inputRef}
            type="text"
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            className={cn('h-full !placeholder:text-xs ![overflow:visible] ![text-overflow:clip]')}
            disabled={disabled}
            placeholder={placeholder}
            aria-label={placeholder}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            onFocus={() => {
              // 已有内容时重新聚焦即触发一次查询并展开下拉
              if (inputValue.length >= SEARCH_CONFIG.MIN_QUERY_LENGTH) {
                setQuery(inputValue);
              }
              if (isOpen) {
                updateDropdownPosition();
              }
            }}
            onBlur={handleBlur}
            // 无障碍：combobox 语义 + 展开状态与下拉列表关联
            aria-autocomplete="none"
            role="combobox"
            aria-expanded={isOpen}
            aria-haspopup="listbox"
            aria-controls="suggestions-list"
          />
          {/* 清除按钮：有内容且可清除时显示（ClearButton 自动清空并触发根 onChange） */}
          {inputValue && onClear && !disabled && (
            <SearchField.ClearButton aria-label={t('common.clear')} />
          )}
        </SearchField.Group>
      </SearchField>

      {/* 索引加载中显示转圈 */}
      {indexLoading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="w-4 h-4 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
        </div>
      )}

      {renderSuggestions()}
    </div>
  );
}

/**
 * StockSearch 对外入口：以错误边界包裹内部实现，渲染异常时整体卸载搜索框，
 * 避免破损 UI 扩散到页面其余部分。
 */
export function StockSearch(props: StockSearchProps) {
  return (
    <StockSearchBoundary {...props}>
      <StockSearchInner {...props} />
    </StockSearchBoundary>
  );
}

/** 默认导出（与具名导出等价） */
export default StockSearch;
