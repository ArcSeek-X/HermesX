/**
 * WatchlistStockTable —— 自选股列表表格（页面右侧）。
 *
 * 表头：股票名称、现价、涨跌幅、成交额、换手率、总市值、备注、操作。
 * 行情字段（现价/涨跌/成交额/换手率/总市值）由父级合并到 item.quote 后传入，
 * 行情缺失显示「—」。排序与搜索在父级（WatchlistPage）基于 quote 完成。
 */

import { useState } from 'react';
import { ArrowLeftRight, Pencil, Trash2 } from 'lucide-react';
import { Button } from '../basic/Button';
import { Select } from '../basic/Select';
import { Tooltip } from '../basic/Tooltip';
import { ConfirmDialog } from '../common/ConfirmDialog';
import type { WatchlistItemWithQuote, WatchlistGroup } from '../../api/watchlist';

export interface WatchlistStockTableProps {
  items: WatchlistItemWithQuote[];
  loading?: boolean;
  groups: WatchlistGroup[];
  onEditNote: (id: number, note: string) => Promise<void> | void;
  onDelete: (id: number) => Promise<void> | void;
  onMove: (id: number, targetGroupId: number) => Promise<void> | void;
}

function formatNumber(value: number | undefined | null, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return '—';
  if (value === 0) return '0';
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(decimals)}亿`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(decimals)}万`;
  return value.toFixed(decimals);
}

function formatPercent(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function getChangeColor(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return 'text-text-secondary';
  if (value > 0) return 'stock-up';
  if (value < 0) return 'stock-down';
  return 'text-text-secondary';
}

export default function WatchlistStockTable({
  items,
  loading,
  groups,
  onEditNote,
  onDelete,
  onMove,
}: WatchlistStockTableProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingNote, setEditingNote] = useState('');
  const [moveTarget, setMoveTarget] = useState<Record<number, string>>({});
  const [pendingDelete, setPendingDelete] = useState<WatchlistItemWithQuote | null>(null);
  const [moveOpenId, setMoveOpenId] = useState<number | null>(null);

  const startEditNote = (id: number, note: string | null) => {
    setEditingId(id);
    setEditingNote(note ?? '');
  };

  const commitEditNote = async (id: number) => {
    await onEditNote(id, editingNote.trim());
    setEditingId(null);
    setEditingNote('');
  };

  const columns = [
    { key: 'name', title: '股票名称', width: '16%' },
    { key: 'price', title: '现价', width: '10%' },
    { key: 'change', title: '涨跌幅', width: '10%' },
    { key: 'amount', title: '成交额', width: '12%' },
    { key: 'turnover', title: '换手率', width: '10%' },
    { key: 'mv', title: '总市值', width: '12%' },
    { key: 'note', title: '备注', width: '18%' },
    { key: 'op', title: '操作', width: '12%' },
  ];

  return (
    <div className="w-full">
      <div
        className="grid items-center px-3 py-2 rounded-t-md bg-card border-b border-subtle text-xs font-medium text-text-secondary"
        style={{ gridTemplateColumns: columns.map((c) => c.width).join(' ') }}
      >
        {columns.map((c) => (
          <div key={c.key}>{c.title}</div>
        ))}
      </div>

      <div className="max-h-[calc(100vh-260px)] overflow-y-auto">
        {loading && items.length === 0 ? (
          <div className="py-10 text-center text-text-secondary text-sm">加载中…</div>
        ) : items.length === 0 ? (
          <div className="py-10 text-center text-text-secondary text-sm">该分组暂无自选股</div>
        ) : (
          items.map((it) => {
            const q = it.quote;
            const isEditingNote = editingId === it.id;
            const isMoveOpen = moveOpenId === it.id;
            return (
              <div
                key={it.id}
                className="grid items-center px-3 py-2.5 border-b border-subtle/60 hover:bg-card-hover text-sm"
                style={{ gridTemplateColumns: columns.map((c) => c.width).join(' ') }}
              >
                {/* 股票名称 */}
                <div className="truncate pr-2">
                  <div className="text-text font-medium truncate">{it.stockName || it.stockCode}</div>
                  <div className="text-xs text-text-secondary truncate">{it.stockCode}</div>
                </div>

                {/* 现价 */}
                <div className={getChangeColor(q?.changePercent ?? null)}>
                  {q?.currentPrice != null ? q.currentPrice.toFixed(2) : '—'}
                </div>

                {/* 涨跌幅 */}
                <div className={getChangeColor(q?.changePercent ?? null)}>
                  {formatPercent(q?.changePercent ?? null)}
                </div>

                {/* 成交额 */}
                <div className="text-text-secondary">{formatNumber(q?.amount ?? null)}</div>

                {/* 换手率 */}
                <div className="text-text-secondary">
                  {q?.turnoverRate != null ? `${q.turnoverRate.toFixed(2)}%` : '—'}
                </div>

                {/* 总市值 */}
                <div className="text-text-secondary">{formatNumber(q?.totalMv ?? null)}</div>

                {/* 备注 */}
                <div className="pr-2">
                  {isEditingNote ? (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <input
                        autoFocus
                        value={editingNote}
                        onChange={(e) => setEditingNote(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') void commitEditNote(it.id);
                          if (e.key === 'Escape') setEditingId(null);
                        }}
                        className="flex-1 min-w-0 rounded border border-primary/50 bg-card px-1.5 py-0.5 text-xs text-text outline-none"
                        placeholder="备注"
                      />
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => commitEditNote(it.id)}
                      >
                        保存
                      </Button>
                    </div>
                  ) : (
                    <span
                      className="text-text-secondary truncate block cursor-pointer hover:text-text"
                      title={it.note ?? '点击添加备注'}
                      onClick={() => startEditNote(it.id, it.note)}
                    >
                      {it.note || '点击添加'}
                    </span>
                  )}
                </div>

                {/* 操作 */}
                <div className="flex items-center gap-1">
                  {/* 移动归类 */}
                  <div className="relative" onClick={(e) => e.stopPropagation()}>
                    <Tooltip content="移动归类">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="!px-1.5"
                        onClick={() => setMoveOpenId(isMoveOpen ? null : it.id)}
                        aria-label="移动归类"
                      >
                        <ArrowLeftRight className="h-4 w-4" />
                      </Button>
                    </Tooltip>
                    {isMoveOpen && (
                      <div className="absolute right-0 top-9 z-30 w-44 rounded-lg border border-border/70 bg-elevated p-2 shadow-xl">
                        <Select
                          value={moveTarget[it.id] ?? ''}
                          onChange={(v) =>
                            setMoveTarget((prev) => ({ ...prev, [it.id]: v }))
                          }
                          options={groups
                            .filter((g) => g.id !== it.groupId)
                            .map((g) => ({ value: String(g.id), label: g.name }))}
                          placeholder="选择目标分组"
                        />
                        <Button
                          variant="primary"
                          size="sm"
                          className="mt-2 w-full"
                          disabled={!moveTarget[it.id]}
                          onClick={() => {
                            const target = moveTarget[it.id];
                            if (target) {
                              void onMove(it.id, Number(target));
                              setMoveOpenId(null);
                            }
                          }}
                        >
                          确定
                        </Button>
                      </div>
                    )}
                  </div>

                  {/* 编辑备注 */}
                  <Tooltip content="编辑备注">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="!px-1.5"
                      onClick={() => startEditNote(it.id, it.note)}
                      aria-label="编辑备注"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </Tooltip>

                  {/* 删除 */}
                  <Tooltip content="删除">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="!px-1.5 text-danger hover:bg-danger/10"
                      onClick={() => setPendingDelete(it)}
                      aria-label="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </Tooltip>
                </div>
              </div>
            );
          })
        )}
      </div>

      {items.length > 0 && (
        <div className="px-3 py-1.5 text-xs text-text-secondary">
          共 {items.length} 只{loading ? ' · 行情更新中…' : ''}
        </div>
      )}

      <ConfirmDialog
        isOpen={pendingDelete != null}
        title="删除自选股"
        message={`确定将「${pendingDelete?.stockName ?? pendingDelete?.stockCode ?? ''}」从自选股中删除吗？`}
        confirmText="删除"
        cancelText="取消"
        isDanger
        onConfirm={async () => {
          if (pendingDelete) await onDelete(pendingDelete.id);
          setPendingDelete(null);
        }}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
