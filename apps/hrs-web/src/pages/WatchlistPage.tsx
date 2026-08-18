/**
 * @file WatchlistPage.tsx
 * @description 自选股管理页面：左侧分类 + 右侧自选股列表（排序/搜索/新增/移动/编辑）
 * @module pages
 */

import { useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { AppPage } from '../components';
import { useWatchlistManager } from '../hooks/useWatchlistManager';
import WatchlistGroupPanel from '../components/watchlist/WatchlistGroupPanel';
import WatchlistStockTable from '../components/watchlist/WatchlistStockTable';
import AnimCard from '../components/common/Card/AnimCard';
import StockAutocomplete from '../components/StockAutocomplete/StockAutocomplete';
import { ApiErrorAlert, Button, Select } from '../components';
import { type WatchlistItemWithQuote } from '../api/watchlist';
import { getParsedApiError, type ParsedApiError } from '../api/error';

type SortKey = 'default' | 'changePercent' | 'amount' | 'turnoverRate' | 'totalMv';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'default', label: '默认' },
  { value: 'changePercent', label: '涨幅' },
  { value: 'amount', label: '成交额' },
  { value: 'turnoverRate', label: '换手率' },
  { value: 'totalMv', label: '市值' },
];

/** 匹配关键词：名称 / 代码 / 拼音 / 拼音简拼 */
function matchKeyword(
  item: WatchlistItemWithQuote,
  keyword: string,
  indexByCode: Map<string, { name: string; pinyin: string; pinyinShort: string }>,
): boolean {
  const kw = keyword.trim().toLowerCase();
  if (!kw) return true;
  if (item.stockCode.toLowerCase().includes(kw)) return true;
  if ((item.stockName ?? '').toLowerCase().includes(kw)) return true;
  const idx = indexByCode.get(item.stockCode);
  if (idx) {
    if (idx.name.toLowerCase().includes(kw)) return true;
    if (idx.pinyin.toLowerCase().includes(kw)) return true;
    if (idx.pinyinShort.toLowerCase().includes(kw)) return true;
  }
  return false;
}

function sortItems(items: WatchlistItemWithQuote[], key: SortKey): WatchlistItemWithQuote[] {
  const list = [...items];
  if (key === 'default') {
    return list.sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id);
  }
  return list.sort((a, b) => {
    const av = a.quote?.[key] ?? -Infinity;
    const bv = b.quote?.[key] ?? -Infinity;
    return bv - av;
  });
}

const WatchlistPage: React.FC = () => {
  const {
    groups,
    groupsLoading,
    createGroup,
    renameGroup,
    removeGroup,
    activeGroupId,
    setActiveGroupId,
    items,
    itemsLoading,
    quotesLoading,
    addItem,
    editItemNote,
    removeItem,
    moveItem,
    indexByCode,
  } = useWatchlistManager();

  const [sortKey, setSortKey] = useState<SortKey>('default');
  const [keyword, setKeyword] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [addCode, setAddCode] = useState('');
  const [addName, setAddName] = useState('');
  const [addNote, setAddNote] = useState('');
  const [addError, setAddError] = useState<ParsedApiError | null>(null);

  const activeGroup = groups.find((g) => g.id === activeGroupId) ?? null;

  const visibleItems = useMemo(() => {
    const filtered = items.filter((it) => matchKeyword(it, keyword, indexByCode));
    return sortItems(filtered, sortKey);
  }, [items, keyword, sortKey, indexByCode]);

  const handleSearchSubmit = (code: string, name?: string) => {
    if (code) setKeyword(code);
    else if (name) setKeyword(name);
  };

  const handleAddSubmit = (code: string, name?: string) => {
    setAddCode(code);
    setAddName(name ?? code);
  };

  const confirmAdd = async () => {
    if (!addCode || activeGroupId == null) return;
    setAddError(null);
    try {
      await addItem(activeGroupId, { stockCode: addCode, stockName: addName, note: addNote });
      setAddCode('');
      setAddName('');
      setAddNote('');
      setAddOpen(false);
    } catch (err) {
      setAddError(getParsedApiError(err));
    }
  };

  return (
    <AppPage className="space-y-4">

      <div className="space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4 items-start">
          {/* 左侧：分类 */}
          <div className="h-[calc(100vh-180px)]">
            <WatchlistGroupPanel
              groups={groups}
              loading={groupsLoading}
              activeGroupId={activeGroupId}
              onSelect={setActiveGroupId}
              onCreate={createGroup}
              onRename={renameGroup}
              onDelete={removeGroup}
            />
          </div>

          {/* 右侧：自选股列表 */}
          <AnimCard className="flex flex-col p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-base font-semibold text-text">
                {activeGroup ? activeGroup.name : '请选择分组'}
              </span>
            </div>

            <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-sm text-text-secondary">排序</span>
                <Select
                  value={sortKey}
                  onChange={(v) => setSortKey(v as SortKey)}
                  options={SORT_OPTIONS}
                />
              </div>

              <div className="flex items-center gap-2 flex-1 justify-end">
                <div className="w-64">
                  <StockAutocomplete
                    placeholder="搜索名称/代码/拼音"
                    value={keyword}
                    onChange={setKeyword}
                    onSubmit={handleSearchSubmit}
                  />
                </div>
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => setAddOpen(true)}
                  disabled={activeGroupId == null}
                >
                  <Plus className="h-4 w-4" />
                  新增
                </Button>
              </div>
            </div>

            {activeGroupId == null ? (
              <div className="py-16 text-center text-text-secondary text-sm">
                请先选择或新增一个分组
              </div>
            ) : (
              <WatchlistStockTable
                items={visibleItems}
                loading={itemsLoading || quotesLoading}
                groups={groups}
                onEditNote={editItemNote}
                onDelete={removeItem}
                onMove={moveItem}
              />
            )}
          </AnimCard>
        </div>

        {/* 新增自选股弹窗（复用 StockAutocomplete 选股） */}
        {addOpen && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
            onClick={() => setAddOpen(false)}
          >
            <div
              className="w-[420px] rounded-lg bg-card border border-subtle p-5 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-base font-semibold text-text mb-4">新增自选股</div>
              <div className="mb-3">
                <label className="text-sm text-text-secondary">选择股票</label>
                <div className="mt-1">
                  <StockAutocomplete
                    placeholder="输入股票代码或名称"
                    value={addCode}
                    onChange={setAddCode}
                    onSubmit={handleAddSubmit}
                  />
                </div>
                {addCode && (
                  <div className="mt-1 text-xs text-primary">已选：{addName}（{addCode}）</div>
                )}
              </div>
              <div className="mb-4">
                <label className="text-sm text-text-secondary">备注</label>
                <input
                  value={addNote}
                  onChange={(e) => setAddNote(e.target.value)}
                  placeholder="选填"
                  className="mt-1 w-full rounded border border-subtle bg-card px-2 py-1.5 text-sm text-text outline-none focus:border-primary"
                />
              </div>
              {addError ? (
                <div className="mb-4">
                  <ApiErrorAlert error={addError} onDismiss={() => setAddError(null)} />
                </div>
              ) : null}
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="md" onClick={() => setAddOpen(false)}>
                  取消
                </Button>
                <Button variant="primary" size="md" disabled={!addCode} onClick={confirmAdd}>
                  保存
                </Button>
              </div>
            </div>
          </div>
        )}

      </div>
    </AppPage>
  );
};

export default WatchlistPage;
