/**
 * 股票搜索下拉建议列表组件
 *
 * 负责在 StockSearch 输入联想时，渲染候选股票/指数/ETF 列表。
 * 外层用 AnimCard 包裹（带渐变背景与外边阴影），内部 <ul> 为可滚动列表。
 * 每个候选项为三栏布局：市场徽标 | 名称+代码 | 匹配类型徽标。
 */

import type { CSSProperties } from 'react';
import type { StockSuggestion } from '../../types/stockIndex';
import { Chip } from '../';
import { cn } from '../../utils/cn';
import AnimCard from '../common/Card/AnimCard';

// 下拉列表底部圆角映射：跟随输入框 size，保证下拉与输入框视觉连贯
const ROUNDED_CLASS: Record<'xs' | 'sm' | 'md' | 'lg' | 'xl', string> = {
  xs: 'rounded-b-sm',
  sm: 'rounded-b-sm',
  md: 'rounded-b-md',
  lg: 'rounded-b-lg',
  xl: 'rounded-b-xl',
};

export interface StockSearchListProps {
  /** 候选建议列表 */
  suggestions: StockSuggestion[];
  /** 当前高亮项索引（键盘/鼠标悬停选中项），-1 表示无高亮 */
  highlightedIndex: number;
  /** 点击某一项时的选择回调 */
  onSelect: (suggestion: StockSuggestion) => void;
  /** 鼠标移入某一项的回调（传入该项索引） */
  onMouseEnter: (index: number) => void;
  /** 鼠标移出整个列表的回调（用于清除高亮） */
  onMouseLeave?: () => void;
  /** 输入框尺寸：下拉列表圆角跟随输入框 */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** 自定义样式（来自 Portal 的 fixed 定位 top/left/width 等） */
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
  // 无候选时不渲染，避免空下拉框
  if (suggestions.length === 0) {
    return null;
  }

  return (
    // 外层 AnimCard：渐变背景 + 浮层层级 + 最大高度 + 外边阴影；style 透传固定定位
    <AnimCard gradientBackground className="relative z-[100] max-h-100 mt-2 py-3" id="suggestions-list"
      style={{
        ...style,
      }}>
      {/* 内容层置于 ::before 渐变之上，避免被 bg-card 遮盖 */}
      <ul
        className={cn(
          'h-full px-2 overflow-auto',
          ROUNDED_CLASS[size],
        )}
        role="listbox"
        onMouseLeave={onMouseLeave}
      >
        {suggestions.map((suggestion, index) => (
          // 单条候选项：三栏栅格布局（市场徽标 | 名称+代码 | 匹配类型徽标）
          <li
            key={suggestion.canonicalCode}
            role="option"
            aria-selected={index === highlightedIndex}
            className={cn(
              'px-2 py-2 rounded-md cursor-pointer grid grid-cols-[auto_1fr_auto] gap-3 items-center',
              // 鼠标移入：淡淡主题色高亮
              'hover:bg-[hsl(var(--primary)/0.05)]',
              // 键盘/鼠标选中态：主题色略深
              index === highlightedIndex && 'bg-[hsl(var(--primary)/0.1)]',
            )}
            onClick={() => onSelect(suggestion)}
            onMouseEnter={() => onMouseEnter(index)}
          >
            {/* 左栏：市场标识徽标（A股/港股/美股……） */}
            <MarketBadge market={suggestion.market} />

            {/* 中栏：名称（超长换行，最多两行）+ 代码（截断）。min-w-0 保证不被长内容撑破栅格 */}
            <div className="flex flex-col min-w-0 overflow-hidden">
              <span
                className="!text-xs font-medium text-primary-text break-all line-clamp-2"
                title={suggestion.nameZh}
              >
                {suggestion.nameZh}
              </span>
              <span className="!text-xs text-secondary-text truncate">
                {suggestion.displayCode}
              </span>
            </div>

            {/* 右栏：匹配类型徽标（精确/前缀/包含/模糊），固定不压缩 */}
            <MatchTypeBadge matchType={suggestion.matchType} />
          </li>
        ))}
      </ul>
    </AnimCard>
  );
}

// 市场标识 -> 中文标签 + 徽标配色（A股红、港股绿、美股青……）
// variant/color 为 Chip 规格字段（color 仅作语义占位，真实配色由 className 透传自定义色实现） purple、indigo
const MARKET_BADGE_CONFIG = {
  CN: { label: 'A股', variant: 'primary', color: 'danger' },
  HK: { label: '港股', variant: 'primary', color: 'success' },
  US: { label: '美股', variant: 'primary', color: 'indigo' },
  JP: { label: '日股', variant: 'primary', color: 'purple' },
  KR: { label: '韩股', variant: 'primary', color: 'purple' },
  INDEX: { label: '指数', variant: 'primary', color: 'warning' },
  ETF: { label: 'ETF', variant: 'primary', color: 'warning', },
  BSE: { label: '北交所', variant: 'primary', color: 'blue' },
} as const;

// 市场徽标：显示市场中文名，颜色区分不同市场
function MarketBadge({ market }: { market: string }) {
  const config = MARKET_BADGE_CONFIG[market as keyof typeof MARKET_BADGE_CONFIG];

  // 市场值不在支持范围内直接抛错，避免渲染出未知徽标
  if (!config) {
    throw new Error(`Unsupported market in stock suggestion: ${market}`);
  }

  return (
    <Chip variant={config.variant} color={config.color} size="xs" radius="sm" className={cn('min-w-[3rem] justify-center', config.className)}>
      {config.label}
    </Chip>
  );
}

// 匹配类型徽标：根据匹配方式显示对应中文标签与配色
function MatchTypeBadge({ matchType }: { matchType: string }) {
  const configMap = {
    exact: { label: '精确', color: 'accent', variant: 'primary' },
    prefix: { label: '前缀', color: 'success', variant: 'soft' },
    contains: { label: '包含', color: 'warning', variant: 'soft' },
    fuzzy: { label: '模糊', color: 'default', variant: 'soft' },
  } as const;

  // 未知匹配类型兜底为“模糊”
  const config = configMap[matchType as keyof typeof configMap] || configMap.fuzzy;

  return (
    <Chip variant={config.variant} color={config.color} size="xs" radius="sm" className="shrink-0">
      {config.label}
    </Chip>
  );
}

export default StockSearchList;
