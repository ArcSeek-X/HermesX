/**
 * @file WatchlistStockColumn.ts
 * @description 自选股表格列配置。将列定义与渲染逻辑从组件中抽离，便于独立维护。
 */

import { HrsButton } from '@components/basic/HrsButton';
import type { TableColumnDef } from '@components/basic/Table';
import type { WatchlistItemWithQuote } from '../../../api/watchlist';
import { formatPercent, getChangeColorClass } from '../../../utils/format';

export interface WatchlistStockColumnOptions {
  editingStockId: number | null;
  editingNoteDraft: string;
  onNoteDraftChange: (draft: string) => void;
  onStartEditNote: (id: number, note: string | null) => void;
  onCommitNoteEdit: (id: number) => void | Promise<void>;
  onCancelNoteEdit: () => void;
}

/** 数值格式化：自动按「亿 / 万」单位缩写，0 与缺失分别显示；用于成交额、总市值。 */
function formatNumber(value: number | undefined | null, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return '—';
  if (value === 0) return '0';
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(decimals)}亿`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(decimals)}万`;
  return value.toFixed(decimals);
}

export function buildWatchlistStockColumns(
  options: WatchlistStockColumnOptions,
): TableColumnDef<WatchlistItemWithQuote>[] {
  const { editingStockId, editingNoteDraft, onNoteDraftChange, onStartEditNote, onCommitNoteEdit, onCancelNoteEdit } = options;

  return [
    {
      key: 'stockName',
      title: '股票名称',
      minWidth: 120,
      defaultWidth: '15%',
      render: (stock) => (
        <div className="group cursor-pointer truncate pr-2">
          <div className="truncate font-semibold group-hover:text-primary">{stock.stockName || stock.stockCode}</div>
          <div className="truncate text-xs group-hover:text-primary">{stock.stockCode}</div>
        </div>
      ),
    },
    {
      key: 'currentPrice',
      title: '现价',
      minWidth: 100,
      defaultWidth: '10%',
      render: (stock) => {
        const quote = stock.quote;
        return (
          <div className={getChangeColorClass(quote?.changePercent ?? null)}>
            {quote?.currentPrice != null ? quote.currentPrice.toFixed(2) : '—'}
          </div>
        );
      },
    },
    {
      key: 'changePercent',
      title: '涨跌幅',
      minWidth: 100,
      defaultWidth: '10%',
      render: (stock) => {
        const quote = stock.quote;
        return (
          <div className={getChangeColorClass(quote?.changePercent ?? null)}>
            {formatPercent(quote?.changePercent ?? null)}
          </div>
        );
      },
    },
    {
      key: 'tradeAmount',
      title: '成交额',
      minWidth: 120,
      defaultWidth: '15%',
      render: (stock) => (
        <div className="text-foreground-soft">{formatNumber(stock.quote?.amount ?? null)}</div>
      ),
    },
    {
      key: 'turnoverRate',
      title: '换手率',
      minWidth: 100,
      defaultWidth: '10%',
      render: (stock) => {
        const quote = stock.quote;
        return (
          <div className="text-foreground-soft">
            {quote?.turnoverRate != null ? `${quote.turnoverRate.toFixed(2)}%` : '—'}
          </div>
        );
      },
    },
    {
      key: 'totalMarketValue',
      title: '总市值',
      minWidth: 120,
      defaultWidth: '15%',
      render: (stock) => (
        <div className="text-foreground-soft">{formatNumber(stock.quote?.totalMv ?? null)}</div>
      ),
    },
    {
      key: 'stockNote',
      title: '描述',
      minWidth: 200,
      defaultWidth: '25%',
      render: (stock) => {
        const isEditing = editingStockId === stock.id;
        return (
          <div className="pr-2">
            {isEditing ? (
              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                <input
                  autoFocus
                  value={editingNoteDraft}
                  onChange={(e) => onNoteDraftChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void onCommitNoteEdit(stock.id);
                    if (e.key === 'Escape') onCancelNoteEdit();
                  }}
                  className="min-w-0 flex-1 rounded border border-primary/50 bg-card px-1.5 py-0.5 text-xs text-text outline-none"
                  placeholder="描述"
                />
                <HrsButton variant="primary" size="sm" onClick={() => onCommitNoteEdit(stock.id)}>
                  保存
                </HrsButton>
              </div>
            ) : (
              <span
                className="block cursor-pointer truncate text-foreground-soft hover:text-text"
                title={stock.description ?? '点击添加描述'}
                onClick={(e) => {
                  e.stopPropagation();
                  onStartEditNote(stock.id, stock.description);
                }}
              >
                {stock.description || '点击添加'}
              </span>
            )}
          </div>
        );
      },
    },
  ];
}
