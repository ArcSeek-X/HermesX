/**
 * StockSearch 模块共享类型。
 * onSubmit 提交载荷属于组件对外契约，不放进全局股票索引类型。
 */
import type { StockSuggestion } from '../../types/stockIndex';

/** 搜索框尺寸：决定输入高度与下拉圆角 */
export type StockSearchSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

/** 搜索提交载荷：下拉选中时含完整候选信息；手工输入兜底时仅代码 / 展示标签 / 来源 */
export type StockSearchSelection = Partial<StockSuggestion> & {
  /** 规范代码（带后缀 600519.SH）；手工兜底时为输入框原文 */
  canonicalCode: string;
  /** 纯代码（600519），对齐 StockRef.code；手工兜底时为输入框原文 */
  code: string;
  /** 组合展示标签「名称（规范代码）」 */
  displayLabel: string;
  /** 提交来源：manual 为回车原文，autocomplete 为候选选中 */
  source: 'manual' | 'autocomplete';
};
