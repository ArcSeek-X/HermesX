/**
 * @file WatchlistStockTable.tsx
 * @description 自选股表格：行情渲染、行内备注编辑、右键移动/删除。
 */

import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { HrsButton } from '@components/basic/HrsButton';
import { Select } from '@components/basic/Select';
import { Table, type PaginationDef } from '@components/basic/Table';
import { ConfirmDialog } from '@components/common/ConfirmDialog';
import type { WatchlistItemWithQuote, WatchlistGroup } from '../../../api/watchlist';
import { buildWatchlistStockColumns } from './WatchlistStockColumn';

export interface WatchlistStockTableProps {
  watchlistItems: WatchlistItemWithQuote[];
  watchlistGroups: WatchlistGroup[];
  onStockNoteSave: (id: number, description: string) => Promise<void> | void;
  onStockRemove: (id: number) => Promise<void> | void;
  onStockMove: (id: number, targetGroupId: number) => Promise<void> | void;
  watchlistPagination?: PaginationDef;
}

export default function WatchlistStockTable({
  watchlistItems,
  watchlistGroups,
  onStockNoteSave,
  onStockRemove,
  onStockMove,
  watchlistPagination,
}: WatchlistStockTableProps) {
  const [rightClickMenu, setRightClickMenu] = useState<{ x: number; y: number; item: WatchlistItemWithQuote } | null>(null);
  const rightClickMenuRef = useRef<HTMLDivElement | null>(null);
  const [moveGroupDialog, setMoveGroupDialog] = useState<{ item: WatchlistItemWithQuote; targetGroupId: string } | null>(null);
  const [pendingDeleteStock, setPendingDeleteStock] = useState<WatchlistItemWithQuote | null>(null);

  const navigate = useNavigate();

  const [editingStockId, setEditingStockId] = useState<number | null>(null);
  const [editingNoteDraft, setEditingNoteDraft] = useState('');

  const columns = buildWatchlistStockColumns({
    noteEditingStockId: editingStockId,
    noteDraft: editingNoteDraft,
    onNoteDraftChange: setEditingNoteDraft,
    onStartNoteEdit: (id, note) => {
      setEditingStockId(id);
      setEditingNoteDraft(note ?? '');
    },
    onCommitNoteEdit: async (id) => {
      await onStockNoteSave(id, editingNoteDraft.trim());
      setEditingStockId(null);
      setEditingNoteDraft('');
    },
    onCancelNoteEdit: () => {
      setEditingStockId(null);
      setEditingNoteDraft('');
    },
    onStockClick: (stock) => {
      // 去掉可能的市场后缀（如 .SH），与 K 线页 stockCode 取值口径一致
      const code = String(stock.stockCode).split('.')[0];
      navigate(`/stock/kline?stockCode=${encodeURIComponent(code)}`);
    },
  });

  const openRowContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    const tr = (e.target as HTMLElement).closest('tr');
    const tbody = tr?.parentElement;
    if (!tr || !tbody) return;
    const idx = Array.from(tbody.children).indexOf(tr as HTMLTableRowElement);
    if (idx < 0 || idx >= watchlistItems.length) return;
    setRightClickMenu({ x: e.clientX, y: e.clientY, item: watchlistItems[idx] });
  };

  useEffect(() => {
    if (!rightClickMenu) return;
    const close = (e: MouseEvent) => {
      if (rightClickMenuRef.current && !rightClickMenuRef.current.contains(e.target as Node)) setRightClickMenu(null);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setRightClickMenu(null); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', onKey);
    };
  }, [rightClickMenu]);

  return (
    <div className="h-full w-full" onContextMenu={openRowContextMenu}>
      <Table
        columns={columns}
        rows={watchlistItems}
        isLoading={false}
        pagination={watchlistPagination}
        height="100%"
      />

      {rightClickMenu && typeof document !== 'undefined'
        ? createPortal(
          <div
            ref={rightClickMenuRef}
            className="fixed z-[60] w-36 rounded-lg border border-border/70 bg-elevated py-1 shadow-xl"
            style={{ top: rightClickMenu.y, left: rightClickMenu.x }}
          >
            <button
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-foreground hover:bg-hover"
              onClick={() => {
                setMoveGroupDialog({ item: rightClickMenu.item, targetGroupId: '' });
                setRightClickMenu(null);
              }}
            >
              修改分组
            </button>
            <button
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-danger hover:bg-danger/10"
              onClick={() => {
                setPendingDeleteStock(rightClickMenu.item);
                setRightClickMenu(null);
              }}
            >
              删除自选
            </button>
          </div>,
          document.body,
        )
        : null}

      {moveGroupDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setMoveGroupDialog(null)}
        >
          <div
            className="w-80 rounded-xl border border-border/70 bg-elevated p-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-4 text-sm font-medium text-foreground">
              修改分组 — {moveGroupDialog.item.stockName || moveGroupDialog.item.stockCode}
            </h3>
            <Select
              value={moveGroupDialog.targetGroupId}
              onChange={(v) => setMoveGroupDialog((prev) => prev ? { ...prev, targetGroupId: v } : null)}
              options={watchlistGroups
                .filter((g) => g.id !== moveGroupDialog.item.groupId)
                .map((g) => ({ value: String(g.id), label: g.name }))}
              placeholder="选择目标分组"
            />
            <div className="mt-4 flex justify-end gap-2">
              <HrsButton variant="secondary" size="sm" onClick={() => setMoveGroupDialog(null)}>
                取消
              </HrsButton>
              <HrsButton
                variant="primary"
                size="sm"
                isDisabled={!moveGroupDialog.targetGroupId}
                onClick={() => {
                  void onStockMove(moveGroupDialog.item.id, Number(moveGroupDialog.targetGroupId));
                  setMoveGroupDialog(null);
                }}
              >
                确定
              </HrsButton>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={pendingDeleteStock != null}
        title="删除自选股"
        message={`确定将「${pendingDeleteStock?.stockName ?? pendingDeleteStock?.stockCode ?? ''}」从自选股中删除吗？`}
        confirmText="删除"
        cancelText="取消"
        isDanger
        onConfirm={async () => {
          if (pendingDeleteStock) await onStockRemove(pendingDeleteStock.id);
          setPendingDeleteStock(null);
        }}
        onCancel={() => setPendingDeleteStock(null)}
      />
    </div>
  );
}
