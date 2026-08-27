/**
 * WatchlistStockTable —— 自选股列表表格（页面右侧）。
 *
 * 表头（共 7 列）：股票名称、现价、涨跌幅、成交额、换手率、总市值、备注。
 * 行情字段（现价 / 涨跌幅 / 成交额 / 换手率 / 总市值）由父级 useWatchlistManager
 * 并发拉取实时行情后合并到每条 item.quote 再传入；行情缺失时统一显示「—」。
 *
 * 设计要点：
 * - 排序与搜索在父级（WatchlistPage）基于 item.quote 完成，本组件只负责渲染。
 * - 表格渲染复用通用 <Table> 组件（src/components/basic/Table.tsx），
 *   通过列定义数组 columns + 每列的 render 插槽实现各列个性化渲染。
 * - 备注列支持行内点击编辑。
 * - 表格行支持右键上下文菜单：修改分组（弹窗选择目标分类）、删除自选（二次确认弹窗）。
 * - 删除走二次确认（ConfirmDialog），避免误删。
 */

import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { HrsButton } from '../basic/HrsButton';
import { Select } from '../basic/Select';
import { Table, type TableColumnDef, type PaginationDef } from '../basic/Table';
import { ConfirmDialog } from '../common/ConfirmDialog';
import type { WatchlistItemWithQuote, WatchlistGroup } from '../../api/watchlist';
// 复用全局格式化工具：涨跌幅、涨跌颜色 class（与全站行情展示保持一致）
import { formatPercent, getChangeColorClass } from '../../utils/format';

export interface WatchlistStockTableProps {
  items: WatchlistItemWithQuote[];
  /** 加载态：接口调用中（含行情并发拉取）为 true，数据全部就绪后为 false */
  isLoading?: boolean;
  groups: WatchlistGroup[];
  onEditDescription: (id: number, description: string) => Promise<void> | void;
  onDelete: (id: number) => Promise<void> | void;
  onMove: (id: number, targetGroupId: number) => Promise<void> | void;
  /** 分页配置对象，调用方需保证传入完整字段 */
  pagination?: PaginationDef;
}

/** 数值格式化：自动按「亿 / 万」单位缩写，0 与缺失分别显示；用于成交额、总市值。 */
function formatNumber(value: number | undefined | null, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return '—';
  if (value === 0) return '0';
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(decimals)}亿`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(decimals)}万`;
  return value.toFixed(decimals);
}

export default function WatchlistStockTable({
  items,
  isLoading,
  groups,
  onEditDescription,
  onDelete,
  onMove,
  pagination,
}: WatchlistStockTableProps) {
  /** 右键上下文菜单：记录鼠标位置与目标行数据 */
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; item: WatchlistItemWithQuote } | null>(null);
  const ctxRef = useRef<HTMLDivElement | null>(null);
  /** 修改分组弹窗：记录目标行与选中的目标分组 */
  const [moveDialog, setMoveDialog] = useState<{ item: WatchlistItemWithQuote; targetGroupId: string } | null>(null);
  /** 删除确认：待删除的条目（非空时弹出 ConfirmDialog） */
  const [pendingDelete, setPendingDelete] = useState<WatchlistItemWithQuote | null>(null);

  /** 右键菜单：定位数据行并弹出菜单 */
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    const tr = (e.target as HTMLElement).closest('tr');
    const tbody = tr?.parentElement;
    if (!tr || !tbody) return;
    const idx = Array.from(tbody.children).indexOf(tr as HTMLTableRowElement);
    if (idx < 0 || idx >= items.length) return;
    setCtxMenu({ x: e.clientX, y: e.clientY, item: items[idx] });
  };

  /** 点击菜单外区域 / Esc 关闭右键菜单 */
  useEffect(() => {
    if (!ctxMenu) return;
    const close = (e: MouseEvent) => {
      if (ctxRef.current && !ctxRef.current.contains(e.target as Node)) setCtxMenu(null);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setCtxMenu(null); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', onKey);
    };
  }, [ctxMenu]);

  /**
   * 表格列定义（数据驱动）。
   * 每列通过 TableColumnDef 描述 key / title / width / render 插槽，
   * render 接收整行数据，可返回任意 React 节点以实现个性化渲染。
   */
  const columns: TableColumnDef<WatchlistItemWithQuote>[] = [
    {
      key: 'name',
      title: '股票名称',
      minWidth: 120,
      defaultWidth: '20%',
      // 两行展示：主行显示股票名（缺名称时回退代码），副行显示代码
      render: (it) => (
        <div className="truncate pr-2">
          <div className="text-text font-medium truncate">{it.stockName || it.stockCode}</div>
          <div className="text-xs text-text-secondary truncate">{it.stockCode}</div>
        </div>
      ),
    },
    {
      key: 'price',
      title: '现价',
      minWidth: 80,
      defaultWidth: '10%',
      // 现价按涨跌方向着色
      render: (it) => {
        const q = it.quote;
        return (
          <div className={getChangeColorClass(q?.changePercent ?? null)}>
            {q?.currentPrice != null ? q.currentPrice.toFixed(2) : '—'}
          </div>
        );
      },
    },
    {
      key: 'change',
      title: '涨跌幅',
      minWidth: 80,
      defaultWidth: '10%',
      render: (it) => {
        const q = it.quote;
        return (
          <div className={getChangeColorClass(q?.changePercent ?? null)}>
            {formatPercent(q?.changePercent ?? null)}
          </div>
        );
      },
    },
    {
      key: 'amount',
      title: '成交额',
      minWidth: 80,
      defaultWidth: '10%',
      render: (it) => (
        <div className="text-text-secondary">{formatNumber(it.quote?.amount ?? null)}</div>
      ),
    },
    {
      key: 'turnover',
      title: '换手率',
      minWidth: 80,
      defaultWidth: '10%',
      render: (it) => {
        const q = it.quote;
        return (
          <div className="text-text-secondary">
            {q?.turnoverRate != null ? `${q.turnoverRate.toFixed(2)}%` : '—'}
          </div>
        );
      },
    },
    {
      key: 'mv',
      title: '总市值',
      minWidth: 80,
      defaultWidth: '10%',
      render: (it) => (
        <div className="text-text-secondary">{formatNumber(it.quote?.totalMv ?? null)}</div>
      ),
    },
    {
      key: 'description',
      title: '描述',
      minWidth: 300,
      defaultWidth: '30%',
      render: (it) => {
        const isEditingNote = editingId === it.id;
        return (
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
                  placeholder="描述"
                />
                <HrsButton
                  variant="primary"
                  size="sm"
                  onClick={() => commitEditNote(it.id)}
                >
                  保存
                </HrsButton>
              </div>
            ) : (
              <span
                className="text-text-secondary truncate block cursor-pointer hover:text-text"
                title={it.description ?? '点击添加描述'}
                onClick={(e) => { e.stopPropagation(); startEditNote(it.id, it.description); }}
              >
                {it.description || '点击添加'}
              </span>
            )}
          </div>
        );
      },
    },
  ];

  /** 行内编辑备注：正在编辑的条目 id 与草稿文本 */
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingNote, setEditingNote] = useState('');

  /** 进入备注编辑：记录 id 并初始化草稿文本 */
  const startEditNote = (id: number, note: string | null) => {
    setEditingId(id);
    setEditingNote(note ?? '');
  };

  /** 提交备注编辑：调用父级回调保存，成功后退出编辑态 */
  const commitEditNote = async (id: number) => {
    await onEditDescription(id, editingNote.trim());
    setEditingId(null);
    setEditingNote('');
  };

  return (
    <div className="w-full" onContextMenu={handleContextMenu}>
      {/* 自选股表格：列定义 + 行数据 + 分页 + 空状态由通用 Table 统一渲染 */}
      <Table
        columns={columns}
        rows={items}
        isLoading={isLoading}
        pagination={pagination}
        maxHeight="calc(100vh - 260px)"
      />

      {/* 右键上下文菜单：通过 Portal 渲染到 body，避免被表格 overflow 裁切 */}
      {ctxMenu && typeof document !== 'undefined'
        ? createPortal(
          <div
            ref={ctxRef}
            className="fixed z-[60] w-36 rounded-lg border border-border/70 bg-elevated py-1 shadow-xl"
            style={{ top: ctxMenu.y, left: ctxMenu.x }}
          >
            <button
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-foreground hover:bg-hover"
              onClick={() => {
                setMoveDialog({ item: ctxMenu.item, targetGroupId: '' });
                setCtxMenu(null);
              }}
            >
              修改分组
            </button>
            <button
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-danger hover:bg-danger/10"
              onClick={() => {
                setPendingDelete(ctxMenu.item);
                setCtxMenu(null);
              }}
            >
              删除自选
            </button>
          </div>,
          document.body,
        )
        : null}

      {/* 修改分组弹窗 */}
      {moveDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setMoveDialog(null)}
        >
          <div
            className="w-80 rounded-xl border border-border/70 bg-elevated p-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-4 text-sm font-medium text-foreground">
              修改分组 — {moveDialog.item.stockName || moveDialog.item.stockCode}
            </h3>
            <Select
              value={moveDialog.targetGroupId}
              onChange={(v) => setMoveDialog((prev) => prev ? { ...prev, targetGroupId: v } : null)}
              options={groups
                .filter((g) => g.id !== moveDialog.item.groupId)
                .map((g) => ({ value: String(g.id), label: g.name }))}
              placeholder="选择目标分组"
            />
            <div className="mt-4 flex justify-end gap-2">
              <HrsButton variant="secondary" size="sm" onClick={() => setMoveDialog(null)}>
                取消
              </HrsButton>
              <HrsButton
                variant="primary"
                size="sm"
                isDisabled={!moveDialog.targetGroupId}
                onClick={() => {
                  void onMove(moveDialog.item.id, Number(moveDialog.targetGroupId));
                  setMoveDialog(null);
                }}
              >
                确定
              </HrsButton>
            </div>
          </div>
        </div>
      )}

      {/* 删除二次确认弹窗：pendingDelete 非空时弹出，确认后调用父级 onDelete */}
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
