/** 股票搜索候选下拉：市场徽标 | 名称 + 代码 | 匹配类型徽标 */

import type { CSSProperties } from 'react';
import type { StockSuggestion } from '../../types/stockIndex';
import type { StockSearchSize } from './types';
import { Chip } from '../';
import { cn } from '../../utils/cn';
import AnimCard from '../common/Card/AnimCard/AnimCard';

const SUGGESTION_DROPDOWN_CORNER_CLASS: Record<StockSearchSize, string> = {
  xs: 'rounded-b-sm',
  sm: 'rounded-b-sm',
  md: 'rounded-b-md',
  lg: 'rounded-b-lg',
  xl: 'rounded-b-xl',
};

const MARKET_BADGE_STYLES = {
  CN: { label: 'A股', color: 'danger' },
  HK: { label: '港股', color: 'success' },
  US: { label: '美股', color: 'indigo' },
  JP: { label: '日股', color: 'purple' },
  KR: { label: '韩股', color: 'purple' },
  INDEX: { label: '指数', color: 'warning' },
  ETF: { label: 'ETF', color: 'warning' },
  BSE: { label: '北交所', color: 'blue' },
} as const;

const MATCH_TYPE_BADGE_STYLES = {
  exact: { label: '精确', color: 'accent', variant: 'primary' },
  prefix: { label: '前缀', color: 'success', variant: 'soft' },
  contains: { label: '包含', color: 'warning', variant: 'soft' },
  fuzzy: { label: '模糊', color: 'default', variant: 'soft' },
} as const;

export interface StockSearchListProps {
  /** 本地索引匹配出的候选股票 */
  stockSuggestions: StockSuggestion[];
  /** 键盘高亮的候选索引；-1 表示无高亮 */
  highlightedSuggestionIndex: number;
  /** 选中候选（点击或回车确认） */
  onSelectSuggestion: (suggestion: StockSuggestion) => void;
  /** 鼠标移入候选时设置高亮 */
  onHighlightSuggestion: (suggestionIndex: number) => void;
  /** 鼠标移出列表时清除高亮 */
  onClearSuggestionHighlight?: () => void;
  size?: StockSearchSize;
  /** Portal 的 fixed 定位 */
  style?: CSSProperties;
}

export function StockSearchList({
  stockSuggestions,
  highlightedSuggestionIndex,
  onSelectSuggestion,
  onHighlightSuggestion,
  onClearSuggestionHighlight,
  size = 'md',
  style,
}: StockSearchListProps) {
  if (stockSuggestions.length === 0) return null;

  return (
    // z-[100000] 与 HeroUI 遮罩持平；Portal 挂 body 且晚于遮罩，同层级按 DOM 顺序胜出
    <AnimCard
      gradientBackground
      className="relative z-[100000] max-h-100 mt-2 py-3"
      id="suggestions-list"
      style={style}
    >
      {/* 内容层需置于 ::before 渐变之上 */}
      <ul
        className={cn('h-full px-2 overflow-auto', SUGGESTION_DROPDOWN_CORNER_CLASS[size])}
        role="listbox"
        onMouseLeave={onClearSuggestionHighlight}
      >
        {stockSuggestions.map((suggestion, suggestionIndex) => (
          <li
            key={suggestion.canonicalCode}
            role="option"
            aria-selected={suggestionIndex === highlightedSuggestionIndex}
            className={cn(
              'px-2 py-2 rounded-md cursor-pointer grid grid-cols-[auto_1fr_auto] gap-3 items-center',
              'hover:bg-primary-faint',
              suggestionIndex === highlightedSuggestionIndex && 'bg-primary-subtle',
            )}
            onClick={() => onSelectSuggestion(suggestion)}
            onMouseEnter={() => onHighlightSuggestion(suggestionIndex)}
          >
            <MarketBadge market={suggestion.market} />
            {/* min-w-0 防止长名称撑破栅格 */}
            <div className="flex flex-col min-w-0 overflow-hidden">
              <span
                className="!text-xs font-medium text-foreground break-all line-clamp-2"
                title={suggestion.name}
              >
                {suggestion.name}
              </span>
              <span className="!text-xs text-secondary-text truncate">
                {suggestion.displayCode}
              </span>
            </div>
            <MatchTypeBadge matchType={suggestion.matchType} />
          </li>
        ))}
      </ul>
    </AnimCard>
  );
}

/** 未知市场抛错，由 StockSearch 的错误边界整体卸载搜索框 */
function MarketBadge({ market }: { market: string }) {
  const marketBadgeStyle = MARKET_BADGE_STYLES[market as keyof typeof MARKET_BADGE_STYLES];
  if (!marketBadgeStyle) throw new Error(`Unsupported market in stock suggestion: ${market}`);

  return (
    <Chip color={marketBadgeStyle.color} size="xs" radius="sm" className="min-w-[3rem] justify-center">
      {marketBadgeStyle.label}
    </Chip>
  );
}

function MatchTypeBadge({ matchType }: { matchType: StockSuggestion['matchType'] }) {
  const matchTypeBadgeStyle = MATCH_TYPE_BADGE_STYLES[matchType];

  return (
    <Chip variant={matchTypeBadgeStyle.variant} color={matchTypeBadgeStyle.color} size="xs" radius="sm" className="shrink-0">
      {matchTypeBadgeStyle.label}
    </Chip>
  );
}

export default StockSearchList;
