/**
 * @file WatchlistStockColumn.tsx
 * @description 自选股表格列定义：行情 / 分时 / 成交额等展示列，以及行内备注编辑列。
 *   「分时」列渲染当日分时缩略图，数据由 useWatchlistManager 懒加载合并到条目的 intraday 字段，
 *   未拉到数据时统一显示占位「—」，不影响其它列。
 */

import { HrsButton } from '@components';
import type { TableColumnDef } from '@components/basic/Table';
import { KLineView } from '@components/kline/KLineView';
import type { WatchlistItemWithQuote } from '../../../api/watchlist';
import { formatPercent, getChangeColorClass } from '../../../utils/format';

/** 分时缩略图高度（px）：同时决定该列行高，保持列表紧凑 */
const INTRADAY_THUMB_HEIGHT = 36;

/** 构建列定义所需的行内备注编辑状态与回调 */
export interface WatchlistStockColumnOptions {
  /** 正在编辑备注的自选股 id，null 表示无 */
  noteEditingStockId: number | null;
  /** 备注编辑中的草稿值 */
  noteDraft: string;
  onNoteDraftChange: (draft: string) => void;
  onStartNoteEdit: (id: number, note: string | null) => void;
  onCommitNoteEdit: (id: number) => void | Promise<void>;
  onCancelNoteEdit: () => void;
  /** 点击股票名称（跳转个股 K 线页）回调；未提供时名称不可跳转 */
  onStockClick?: (stock: WatchlistItemWithQuote) => void;
}

/** 金额格式化：按「亿 / 万」缩写，缺失显示「—」，用于成交额与总市值 */
function formatCompactAmount(value: number | undefined | null, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return '—';
  if (value === 0) return '0';
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(decimals)}亿`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(decimals)}万`;
  return value.toFixed(decimals);
}

export function buildWatchlistStockColumns(
  options: WatchlistStockColumnOptions,
): TableColumnDef<WatchlistItemWithQuote>[] {
  const { noteEditingStockId, noteDraft, onNoteDraftChange, onStartNoteEdit, onCommitNoteEdit, onCancelNoteEdit, onStockClick } = options;

  return [
    {
      key: 'stockName',
      title: '股票名称',
      minWidth: 120,
      defaultWidth: '15%',
      render: (stock) => (
        <div
          className="group cursor-pointer truncate pr-2"
          role="button"
          tabIndex={0}
          title="查看 K 线"
          onClick={(e) => {
            e.stopPropagation();
            onStockClick?.(stock);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onStockClick?.(stock);
            }
          }}
        >
          <div className="truncate font-semibold group-hover:text-primary">{stock.stockName || stock.stockCode}</div>
          <div className="truncate text-xs group-hover:text-primary">{stock.stockCode}</div>
        </div>
      ),
    },
    {
      key: 'price',
      title: '现价',
      minWidth: 88,
      defaultWidth: '9%',
      render: (stock) => (
        <div className={getChangeColorClass(stock.quote?.changePct ?? null)}>
          {stock.quote?.price != null ? stock.quote.price.toFixed(2) : '—'}
        </div>
      ),
    },
    {
      key: 'changePct',
      title: '涨跌幅',
      minWidth: 88,
      defaultWidth: '9%',
      render: (stock) => (
        <div className={getChangeColorClass(stock.quote?.changePct ?? null)}>
          {formatPercent(stock.quote?.changePct ?? null)}
        </div>
      ),
    },
    {
      key: 'intraday',
      title: '分时',
      minWidth: 140,
      defaultWidth: '18%',
      // 单元格收紧内边距并裁剪溢出，行高由缩略图固定高度决定，不撑高其它文本列
      cellClassName: '!py-1 overflow-hidden',
      render: (stock) => {
        if (!stock.intraday || stock.intraday.points.length === 0) {
          return <span className="text-xs text-muted-text">—</span>;
        }
        return (
          <div className="w-full min-w-0 overflow-hidden" style={{ height: INTRADAY_THUMB_HEIGHT }}>
            <KLineView
              timeline={stock.intraday.points}
              prevClose={stock.intraday.prevClose}
              height={INTRADAY_THUMB_HEIGHT}
              className="border-none bg-transparent"
            />
          </div>
        );
      },
    },
    {
      key: 'tradeAmount',
      title: '成交额',
      minWidth: 120,
      defaultWidth: '12%',
      render: (stock) => (
        <div className="text-foreground-soft">{formatCompactAmount(stock.quote?.amount ?? null)}</div>
      ),
    },
    {
      key: 'turnoverRate',
      title: '换手率',
      minWidth: 100,
      defaultWidth: '8%',
      render: (stock) => (
        <div className="text-foreground-soft">
          {stock.quote?.turnoverRate != null ? `${stock.quote.turnoverRate.toFixed(2)}%` : '—'}
        </div>
      ),
    },
    {
      key: 'totalMarketValue',
      title: '总市值',
      minWidth: 120,
      defaultWidth: '13%',
      render: (stock) => (
        <div className="text-foreground-soft">{formatCompactAmount(stock.quote?.totalMv ?? null)}</div>
      ),
    },
    {
      key: 'stockNote',
      title: '描述',
      minWidth: 160,
      defaultWidth: '16%',
      render: (stock) => {
        const isEditing = noteEditingStockId === stock.id;
        return (
          <div className="pr-2">
            {isEditing ? (
              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                <input
                  autoFocus
                  value={noteDraft}
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
                  onStartNoteEdit(stock.id, stock.description);
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
