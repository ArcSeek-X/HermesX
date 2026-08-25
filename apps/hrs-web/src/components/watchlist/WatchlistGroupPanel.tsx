/**
 * WatchlistGroupPanel —— 自选股分类面板（页面左侧）。
 *
 * 结构：
 * - 顶部：标题「分组」+ 新增分类按钮（点击弹出表单弹框）
 * - 列表：一层平铺的分类，使用 ListCard 展示（标题=分类名称、描述=分类描述、右侧 Chip=个股数量）
 * - 每条卡片右上角有「编辑 / 删除」操作（包裹层），编辑复用新增弹框
 *
 * 纯展示 + 交互回调，状态由父级（WatchlistPage / useWatchlistManager）托管。
 */

import { useState } from 'react';
import { Plus, Pencil, Trash2, Layers3 } from 'lucide-react';
import AnimCard from '../common/Card/AnimCard';
import { ListCard } from '../common/ListCard';
import { HrsButton, Input } from '../index';
import { Modal } from '../basic/Modal';
import { ConfirmDialog } from '../common/ConfirmDialog';
import type { WatchlistGroup } from '../../api/watchlist';

export interface WatchlistGroupPanelProps {
  groups: WatchlistGroup[];
  loading?: boolean;
  activeGroupId: number | null;
  onSelect: (id: number) => void;
  /** 新增分类（分类名称必填、分类描述选填） */
  onCreate: (name: string, description?: string) => Promise<void> | void;
  /** 编辑分类（分类名称必填、分类描述选填），按 groupCode 定位 */
  onRename: (groupCode: string, payload: { name?: string; description?: string }) => Promise<void> | void;
  /** 删除分类（逻辑删除），按 groupCode 定位 */
  onDelete: (groupCode: string) => Promise<void> | void;
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
  // 弹框状态：editingGroup 为 null 表示新增，非 null 表示编辑（带初始值）
  const [modalOpen, setModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<WatchlistGroup | null>(null);
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [saving, setSaving] = useState(false);

  // 删除确认
  const [pendingDelete, setPendingDelete] = useState<WatchlistGroup | null>(null);

  const openCreate = () => {
    setEditingGroup(null);
    setFormName('');
    setFormDescription('');
    setModalOpen(true);
  };

  const openEdit = (g: WatchlistGroup) => {
    setEditingGroup(g);
    setFormName(g.name);
    setFormDescription(g.description || '');
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingGroup(null);
    setFormName('');
    setFormDescription('');
  };

  const handleSave = async () => {
    const name = formName.trim();
    if (!name) return; // 分类名称为必填项
    setSaving(true);
    try {
      if (editingGroup) {
        await onRename(editingGroup.groupCode, { name, description: formDescription.trim() });
      } else {
        await onCreate(name, formDescription.trim());
      }
      closeModal();
    } finally {
      setSaving(false);
    }
  };

  const isNameValid = formName.trim().length > 0;

  return (
    <AnimCard className="flex flex-col p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold text-text">分组</span>
          <span className="text-xs text-text-secondary">({groups.length})</span>
        </div>
        <HrsButton variant="primary" size="sm" onClick={openCreate}>
          <Plus className="h-4 w-4 m-0" />
          新增分类
        </HrsButton>
      </div>

      {/* 分类列表（一层平铺，使用 ListCard） */}
      <div className="flex-1 overflow-y-auto -mx-1 px-1 space-y-1.5">
        {loading && groups.length === 0 ? (
          <div className="text-sm text-text-secondary py-6 text-center">加载中…</div>
        ) : groups.length === 0 ? (
          <div className="text-sm text-text-secondary py-6 text-center">暂无分组，请先新增</div>
        ) : (
          groups.map((g, index) => {
            const isActive = g.id === activeGroupId;
            return (
              <div key={g.id} className="relative">
                <ListCard
                  icon={Layers3}
                  title={g.name}
                  description={g.description || '—'}
                  count={g.itemCount}
                  isActive={isActive}
                  ordinal={index}
                  onClick={() => onSelect(g.id)}
                />
                {/* 右上角操作区（包裹层） */}
                <div className="absolute right-2 top-2 flex gap-1">
                  <HrsButton
                    variant="ghost"
                    size="sm"
                    onClick={() => openEdit(g)}
                    aria-label="编辑"
                    className="!px-1.5"
                  >
                    <Pencil className="h-4 w-4" />
                  </HrsButton>
                  <HrsButton
                    variant="ghost"
                    size="sm"
                    onClick={() => setPendingDelete(g)}
                    aria-label="删除"
                    className="!px-1.5 text-danger hover:bg-danger/10"
                  >
                    <Trash2 className="h-4 w-4" />
                  </HrsButton>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 新增 / 编辑分类弹框 */}
      <Modal isOpen={modalOpen} onClose={closeModal} size="md">
        <Modal.Header>
          <Modal.Heading>{editingGroup ? '编辑分类' : '新增分类'}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-text">
                分类名称<span className="text-danger ml-0.5">*</span>
              </label>
              <Input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="请输入分类名称"
                maxLength={50}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && isNameValid) void handleSave();
                }}
                autoFocus
              />
              {!isNameValid && (
                <p className="text-xs text-danger">分类名称不能为空</p>
              )}
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-text">分类描述</label>
              <Input
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="请输入分类描述（选填）"
                maxLength={255}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && isNameValid) void handleSave();
                }}
              />
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="secondary" onClick={closeModal}>
            取消
          </HrsButton>
          <HrsButton variant="primary" isLoading={saving} disabled={!isNameValid} onClick={handleSave}>
            {editingGroup ? '保存' : '创建'}
          </HrsButton>
        </Modal.Footer>
      </Modal>

      <ConfirmDialog
        isOpen={pendingDelete != null}
        title="删除分组"
        message={`确定删除分组「${pendingDelete?.name ?? ''}」吗？该分组下的自选股将一并删除。`}
        confirmText="删除"
        cancelText="取消"
        isDanger
        onConfirm={async () => {
          if (pendingDelete) await onDelete(pendingDelete.groupCode);
          setPendingDelete(null);
        }}
        onCancel={() => setPendingDelete(null)}
      />
    </AnimCard>
  );
}
