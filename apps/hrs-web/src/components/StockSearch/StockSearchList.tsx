/** 股票搜索候选列表：市场徽标 | 名称 + 代码 | 匹配类型徽标 */

import type { CSSProperties } from 'react';
import type { StockSuggestion } from '../../types/stockIndex';
import type { StockSearchSize } from './types';
import { Chip } from '../';
import { cn } from '../../utils/cn';
import AnimCard from '../common/Card/AnimCard/AnimCard';

const DROPDOWN_CORNER_CLASS: Record<StockSearchSize, string> = {
  xs: 'rounded-b-sm',
  sm: 'rounded-b-sm',
  md: 'rounded-b-md',
  lg: 'rounded-b-lg',
  xl: 'rounded-b-xl',
};

const MARKET_BADGE_STYLE = {
  CN: { label: 'A股', color: 'danger' },
  HK: { label: '港股', color: 'success' },
  US: { label: '美股', color: 'indigo' },
  JP: { label: '日股', color: 'purple' },
  KR: { label: '韩股', color: 'purple' },
  INDEX: { label: '指数', color: 'warning' },
  ETF: { label: 'ETF', color: 'warning' },
  BSE: { label: '北交所', color: 'blue' },
} as const;

const MATCH_TYPE_BADGE_STYLE = {
  exact: { label: '精确', color: 'accent', variant: 'primary' },
  prefix: { label: '前缀', color: 'success', variant: 'soft' },
  contains: { label: '包含', color: 'warning', variant: 'soft' },
  fuzzy: { label: '模糊', color: 'default', variant: 'soft' },
} as const;

export interface StockSearchListProps {
  suggestions: StockSuggestion[];
  /** -1 表示无高亮 */
  highlightedIndex: number;
  onSelect: (suggestion: StockSuggestion) => void;
  onMouseEnter: (suggestionIndex: number) => void;
  onMouseLeave?: () => void;
  size?: StockSearchSize;
  /** Portal 的 fixed 定位 */
  style?: CSSProperties;
}

export function StockSearchList({
  suggestions,
  highlightedIndex,
  onSelect,
  onMouseEnter,
  onMouseLeave,
  size = 'md',
  style,
}: StockSearchListProps) {
  if (suggestions.length === 0) return null;

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
        className={cn('h-full px-2 overflow-auto', DROPDOWN_CORNER_CLASS[size])}
        role="listbox"
        onMouseLeave={onMouseLeave}
      >
        {suggestions.map((suggestion, suggestionIndex) => (
          <li
            key={suggestion.canonicalCode}
            role="option"
            aria-selected={suggestionIndex === highlightedIndex}
            className={cn(
              'px-2 py-2 rounded-md cursor-pointer grid grid-cols-[auto_1fr_auto] gap-3 items-center',
              'hover:bg-primary-faint',
              suggestionIndex === highlightedIndex && 'bg-primary-subtle',
            )}
            onClick={() => onSelect(suggestion)}
            onMouseEnter={() => onMouseEnter(suggestionIndex)}
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

/** 未知市场直接抛错，由 StockSearch 的错误边界整体卸载搜索框 */
function MarketBadge({ market }: { market: string }) {
  const badgeStyle = MARKET_BADGE_STYLE[market as keyof typeof MARKET_BADGE_STYLE];
  if (!badgeStyle) throw new Error(`Unsupported market in stock suggestion: ${market}`);

  return (
    <Chip color={badgeStyle.color} size="xs" radius="sm" className="min-w-[3rem] justify-center">
      {badgeStyle.label}
    </Chip>
  );
}

function MatchTypeBadge({ matchType }: { matchType: StockSuggestion['matchType'] }) {
  const badgeStyle = MATCH_TYPE_BADGE_STYLE[matchType];

  return (
    <Chip variant={badgeStyle.variant} color={badgeStyle.color} size="xs" radius="sm" className="shrink-0">
      {badgeStyle.label}
    </Chip>
  );
}

export default StockSearchList;
