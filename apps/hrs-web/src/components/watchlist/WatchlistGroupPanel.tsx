/**
 * WatchlistGroupPanel —— 自选股分类面板（页面左侧）。
 *
 * 结构：
 * - 顶部：标题「分组」+ 新增分组（输入框 + 新增按钮）
 * - 列表：一层平铺的分类；鼠标移入每条显示「编辑 / 删除」图标
 *
 * 纯展示 + 交互回调，状态由父级（WatchlistPage / useWatchlistManager）托管。
 */

import { useState } from 'react';
import { Plus, Pencil, Trash2, Check, X } from 'lucide-react';
import AnimCard from '../common/Card/AnimCard';
import { Button } from '../basic/Button';
import { Input } from '../basic/Input';
import { ConfirmDialog } from '../common/ConfirmDialog';
import type { WatchlistGroup } from '../../api/watchlist';

export interface WatchlistGroupPanelProps {
  groups: WatchlistGroup[];
  loading?: boolean;
  activeGroupId: number | null;
  onSelect: (id: number) => void;
  onCreate: (name: string) => Promise<void> | void;
  onRename: (id: number, name: string) => Promise<void> | void;
  onDelete: (id: number) => Promise<void> | void;
}

export default function WatchlistGroupPanel({
  groups,
  loading,
  activeGroupId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: WatchlistGroupPanelProps) {
  const [newName, setNewName] = useState('');
  const [adding, setAdding] = useState(false);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const [pendingDelete, setPendingDelete] = useState<WatchlistGroup | null>(null);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setAdding(true);
    try {
      await onCreate(name);
      setNewName('');
    } finally {
      setAdding(false);
    }
  };

  const startEdit = (g: WatchlistGroup) => {
    setEditingId(g.id);
    setEditingName(g.name);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditingName('');
  };

  const commitEdit = async () => {
    const name = editingName.trim();
    if (!name || editingId == null) {
      cancelEdit();
      return;
    }
    await onRename(editingId, name);
    cancelEdit();
  };

  return (
    <AnimCard className="flex flex-col p-4 h-full">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base font-semibold text-text">分组</span>
        <span className="text-xs text-text-secondary">({groups.length})</span>
      </div>

      {/* 新增分组 */}
      <div className="flex items-center gap-2 mb-3">
        <Input
          placeholder="新分组名称"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void handleCreate();
          }}
          className="flex-1"
        />
        <Button variant="primary" size="md" isLoading={adding} onClick={handleCreate}>
          <Plus className="h-4 w-4" />
          新增
        </Button>
      </div>

      {/* 分类列表（一层平铺） */}
      <div className="flex-1 overflow-y-auto -mx-1 px-1 space-y-1.5">
        {loading && groups.length === 0 ? (
          <div className="text-sm text-text-secondary py-6 text-center">加载中…</div>
        ) : groups.length === 0 ? (
          <div className="text-sm text-text-secondary py-6 text-center">暂无分组，请先新增</div>
        ) : (
          groups.map((g) => {
            const isActive = g.id === activeGroupId;
            const isEditing = editingId === g.id;
            return (
              <div
                key={g.id}
                onClick={() => !isEditing && onSelect(g.id)}
                className={[
                  'group flex items-center justify-between rounded-md px-3 py-2 cursor-pointer transition-colors',
                  isActive
                    ? 'bg-primary/15 border border-primary/40 text-text'
                    : 'hover:bg-card-hover border border-transparent text-text-secondary hover:text-text',
                ].join(' ')}
              >
                {isEditing ? (
                  <div className="flex items-center gap-1 flex-1" onClick={(e) => e.stopPropagation()}>
                    <Input
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') void commitEdit();
                        if (e.key === 'Escape') cancelEdit();
                      }}
                      autoFocus
                      className="flex-1"
                    />
                    <Button variant="ghost" size="sm" onClick={commitEdit} aria-label="保存">
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={cancelEdit} aria-label="取消">
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <span className="truncate text-sm">{g.name}</span>
                    <span
                      className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => startEdit(g)}
                        aria-label="编辑"
                        className="!px-1.5"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setPendingDelete(g)}
                        aria-label="删除"
                        className="!px-1.5 text-danger hover:bg-danger/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </span>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      <ConfirmDialog
        isOpen={pendingDelete != null}
        title="删除分组"
        message={`确定删除分组「${pendingDelete?.name ?? ''}」吗？该分组下的自选股将一并删除。`}
        confirmText="删除"
        cancelText="取消"
        isDanger
        onConfirm={async () => {
          if (pendingDelete) await onDelete(pendingDelete.id);
          setPendingDelete(null);
        }}
        onCancel={() => setPendingDelete(null)}
      />
    </AnimCard>
  );
}
