/**
 * StockSearch —— 股票代码/名称搜索输入框组件
 *
 * 整个前端复用的搜索入口（K 线页、聊天页、首页等）。职责：
 *   1. 基于本地股票索引做代码/中文名/拼音全拼/简拼/别名的模糊匹配，渲染下拉候选；
 *   2. 支持键盘导航（↑/↓ 高亮、Enter 提交、Esc 收起）与 IME 输入法组合态处理；
 *   3. 渲染异常由 ErrorBoundary 捕获，避免破损 UI 扩散；
 *   4. 下拉默认通过 createPortal 挂到 document.body 避免被父级裁剪；
 *      可通过 originalRender 切换为原位渲染。
 *
 * 对外契约：
 *   - onChange(value)：输入内容变化（原始文本）
 *   - onSubmit(code, name, source, metadata)：提交搜索，code 为规范代码（如 600519.SH）
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
import type { Market } from '../../types/market';


/** StockSearch 组件对外 Props */
export interface StockSearchProps {
  /** 输入值（用于搜索逻辑，通常是解析后的纯代码） */
  value: string;
  /**
   * 输入框展示值（可选）——组件唯一的展示通道。
   *
   * 【统一格式】"股票名称（规范代码）"，如"中科曙光（603019.SH）"；
   *   规范代码带市场后缀（.SH/.SZ/.HK/.US），由组件内部统一拼装，调用方不应自行拼接。
   *
   * 【组件内自赋值】用户在下拉中选中（含回车选中）后，组件会自行把展示文案
   *   写入本通道并立即显示，调用方无需维护展示状态。
   *
   * 【外部传入仅用于初始化显示】外部传入的值只作为"组件初始化 / 外部重置"时的展示文案；
   *   一旦用户在组件内完成选择，展示文案以组件内部赋值为准（覆盖外部传入值）。
   *
   * 【优先级】编辑中原文 > 展示通道（displayValue） > value（纯代码）。
   */
  displayValue?: string;
  /** 输入内容变化回调（参数为输入框原始文本） */
  onChange: (value: string) => void;
  /** 提交回调：携带规范代码、名称、来源（手动输入/下拉选择）与元信息（市场、展示代码、展示标签） */
  onSubmit: (
    code: string,
    name?: string,
    source?: 'manual' | 'autocomplete',
    metadata?: { market?: Market; displayCode?: string; displayLabel?: string },
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
function buildDisplayLabel(nameZh?: string, canonicalCode?: string): string {
  if (!canonicalCode) return nameZh ?? '';
  if (!nameZh) return canonicalCode;
  return `${nameZh}（${canonicalCode}）`;
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
    console.error('Autocomplete runtime error. Falling back to plain input.', error, errorInfo);
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
 * 数据流：
 *   useStockIndex() 提供本地股票索引 → useStockAutocomplete(index) 提供
 *   候选列表/下拉开关/键盘高亮/IME 状态 → 本组件负责把它们绑定到输入框交互上。
 *
 * 关键交互细节：
 *   - value（外部受控）与内部 query 通过 useEffect 同步，但用户刚选中候选时
 *     用 justSelectedRef 跳过同步，避免选中后重复触发搜索；
 *   - 下拉框用 fixed 定位 + createPortal 渲染，随滚动/缩放实时重算位置。
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
  // 界面语言：默认占位符与清除按钮无障碍标签走 i18n（规范：component.StockSearch.*）
  const { t } = useUiLanguage();
  // 股票索引：加载本地 /stocks.index.json
  const { index, loading } = useStockIndex();
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
    isComposing,          // 是否处于输入法组合输入中
    setIsComposing,       // 设置输入法组合状态
    error: autocompleteError, // 自动补全运行时错误
  } = useStockAutocomplete(index);

  // size -> 输入框尺寸/字体/圆角映射
  // 用 ! 强制前缀确保高度/圆角覆盖 HeroUI Group 自带样式；高度只作用于 Group，
  // Input 用 h-full 跟随 Group 撑满，避免两者写死高度冲突导致外观不生效。
  const SIZE_CLASS: Record<'xs' | 'sm' | 'md' | 'lg' | 'xl', string> = {
    xs: '!h-7 !rounded-xs !text-xs ',
    sm: '!h-8 !rounded-sm !text-xs ',
    md: '!h-9 !rounded-md !text-sm ',
    lg: '!h-10 !rounded-md !text-sm ',
    xl: '!h-12 !rounded-md !text-sm ',
  };



  const inputRef = useRef<HTMLInputElement>(null);
  const groupRef = useRef<HTMLDivElement>(null); // SearchField.Group DOM，用于下拉框宽度/位置对齐
  const prevValueRef = useRef(value);      // 上一次的外部 value，用于比较是否真变化
  const justSelectedRef = useRef(false);  // 标记刚刚完成了选择，阻止同步效应重新触发搜索
  // 下拉框定位（fixed）：top/left/width，随输入框位置与尺寸变化重算
  const [dropdownStyle, setDropdownStyle] = useState<{ top: number; left: number; width: string } | null>(null);
  // 编辑中原文：用户正在输入时优先使用，避免展示通道（"名称（代码）"）覆盖编辑操作
  const [editingValue, setEditingValue] = useState<string | null>(null);
  // 展示通道（唯一）："股票名称（规范代码）"，如"中科曙光（603019.SH）"。
  // 初始由外部 displayValue 同步（仅用于初始化显示），选中候选后由组件内自赋值。
  const [displayText, setDisplayText] = useState(displayValue ?? '');

  /** 依据 SearchField.Group 当前 DOM 位置计算下拉框的 fixed 定位 */
  // 使用 Group 而非 Input 的边界，保证下拉框宽度与视觉外框（含搜索图标/清除按钮）对齐。
  const updateDropdownPosition = () => {
    if (!groupRef.current) {
      setDropdownStyle(null);
      return;
    }

    const rect = groupRef.current.getBoundingClientRect();
    setDropdownStyle({
      top: rect.bottom,           // 下拉框紧贴输入框外框下沿
      left: rect.left,
      width: `${rect.width}px`,   // 与输入搜索框外框同宽
    });
  };

  /** 关闭下拉并清空定位（失焦、Esc、提交等场景统一入口） */
  const closeSuggestions = () => {
    close();
    setDropdownStyle(null);
  };

  // 外部 displayValue 变化（初始化 / 外部重置）时同步进展示通道；
  // 组件内的选择不经由此处，故不会覆盖内部赋值（符合"外部传入仅用于初始化"）。
  const prevDisplayValueRef = useRef(displayValue);
  useEffect(() => {
    if (prevDisplayValueRef.current !== displayValue) {
      prevDisplayValueRef.current = displayValue;
      setDisplayText(displayValue ?? '');
    }
  }, [displayValue]);

  // 显示值优先级：编辑中原文 > 展示通道 > value（纯代码）
  const inputValue = editingValue ?? (displayText || undefined) ?? value;

  // 占位符取自当前语言的组件默认文案
  const multilingual_placeholder =  t('component.StockSearch.placeholder');

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
   * - ↑/↓：移动高亮（useStockAutocomplete 内部做循环）；
   * - Enter：有候选时优先选中高亮项；无高亮项但有候选时默认选中第一项（将中文名等输入自动转换为对应股票）；无任何候选时才把输入原文提交；
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
        if (suggestions.length > 0) {
          // 有候选：优先取键盘高亮项，未高亮（highlightedIndex < 0）时默认取第一项，
          // 这样输入中文名（如"中科曙光"）回车即可自动匹配并转换为对应股票代码，
          // 而非把原始中文输入当代码提交。
          const selected = suggestions[highlightedIndex] ?? suggestions[0];
          justSelectedRef.current = true; // 阻止同步效应重新触发搜索
          // 组件内自赋值：把"名称（规范代码）"写入唯一展示通道并立即显示
          setDisplayText(buildDisplayLabel(selected.nameZh, selected.canonicalCode));
          // value 保持纯代码（搜索语义），与展示通道解耦
          onChange(selected.displayCode);
          closeSuggestions();
          onSubmit(selected.canonicalCode, selected.nameZh, 'autocomplete', {
            market: selected.market,
            displayCode: selected.displayCode,
            displayLabel: buildDisplayLabel(selected.nameZh, selected.canonicalCode),
          });
        } else {
          // 无任何候选：把输入原文直接提交（调用方会解析，如后端搜索）
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

  // 自动补全输入框 + 清除按钮 + 加载指示 + 下拉候选列表
  // 基于 HeroUI InputGroup：外层 wrapper 复用项目输入框样式类，
  // 基于 HeroUI SearchField：受控根组件管理输入值，Group 承载视觉框样式，
  // 内置 SearchIcon + ClearButton（ClearButton 自动清空并触发根 onChange），
  // Input 挂键盘/IME/焦点逻辑与 combobox 无障碍语义，下拉展开时去掉下圆角
  return (
    <div className="hrs-stock-search relative stock-autocomplete">
      <SearchField
        name="stock-search"
        aria-label="stock-search-Field"
        value={inputValue}
        // 本回调仅由用户实际输入触发（选中回填走外部 onChange prop，不进此处）
        onChange={(raw: string) => {
          setEditingValue(raw); // 标记正在编辑，使用原始输入值
          setDisplayText(''); // 清空展示通道，避免残留上一只股票名
          onChange(raw);
          if (raw === '' && onClear) {
            setEditingValue(null);
            onClear();
          }
        }}
      >
        <SearchField.Group
          ref={groupRef}
          className={cn(
            /** 输入框统一样式类：尺寸/圆角/字体跟随 size 映射，聚焦光晕、禁用态等（两种模式共用，外观修改一致） */
            SIZE_CLASS[size],

            'w-full flex items-center transition-all border disabled:cursor-not-allowed disabled:opacity-60',

            ' focus:outline-none',
            // 外部阴影调淡：覆盖默认 surface 阴影
            '!shadow-xs',
            // 聚焦时外框不变色，仅保留一圈更淡的聚焦光圈反馈
            'focus:!border-border focus:!shadow-[0_0_0_2px_hsl(var(--primary)/0.10)]',
            'disabled:cursor-not-allowed disabled:opacity-60',


            // 下拉展开时去掉下圆角与下边框，与下拉列表共用一条底边，避免圆角/边框错位
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
            placeholder={multilingual_placeholder}
            aria-label={multilingual_placeholder}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            onFocus={() => {
              // 输入框已有内容时，重新聚焦即触发一次查询并展开下拉框（如候选变化/窗口变动）
              if (inputValue.length >= SEARCH_CONFIG.MIN_QUERY_LENGTH) {
                setQuery(inputValue);
              }
              // 若下拉已展开，重算一次位置（布局可能已变化）
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

      {/* Loading indicator：索引加载中显示转圈（正常模式下加载完才渲染列表） */}
      {loading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="w-4 h-4 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
        </div>
      )}

      {/* 下拉候选列表：originalRender=false（默认）经 Portal 挂 body，避免被父级裁切；
          originalRender=true 则原位渲染，并规避 react-aria Modal 的 inert 限制。 */}
      {isOpen && dropdownStyle && (() => {
        // 抽取下拉列表元素，仅包裹方式（原位 / Portal 挂 body）随 originalRender 变化，避免重复书写
        const dropdown = (
          <StockSearchList
            size={size}
            suggestions={suggestions}
            highlightedIndex={highlightedIndex}
            onSelect={(s) => {
              justSelectedRef.current = true; // 阻止同步效应重新触发搜索
              setEditingValue(null); // 选择建议时清除编辑状态，让展示通道生效
              // 组件内自赋值：把"名称（规范代码）"写入唯一展示通道并立即显示
              setDisplayText(buildDisplayLabel(s.nameZh, s.canonicalCode));
              // 回填纯代码给 value（搜索语义），与展示通道解耦
              onChange(s.displayCode);
              // Close dropdown list
              closeSuggestions();
              // Submit analysis
              onSubmit(s.canonicalCode, s.nameZh, 'autocomplete', {
                market: s.market,
                displayCode: s.displayCode,
                displayLabel: buildDisplayLabel(s.nameZh, s.canonicalCode),
              });
            }}
            onMouseEnter={(index) => setHighlightedIndex(index)}
            onMouseLeave={() => setHighlightedIndex(-1)}
            style={{ position: 'fixed', ...dropdownStyle }}
          />
        );
        return originalRender ? dropdown : createPortal(dropdown, document.body);
      })()}
    </div>
  );
}

/**
 * StockSearch 对外入口
 *
 * 用错误边界包裹内部实现：渲染期任何异常都会降级为普通输入框，
 * 保证搜索输入功能可用性，不拖垮整个页面。
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
