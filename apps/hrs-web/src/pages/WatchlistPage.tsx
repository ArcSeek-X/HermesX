/**
 * @file WatchlistPage.tsx
 * @description 自选股管理页面：左侧分类 + 右侧自选股列表（排序/搜索/新增/移动/编辑）
 * @module pages
 */

import { useMemo, useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { useWatchlistManager } from '../hooks/useWatchlistManager';
import WatchlistGroupPanel from '../components/watchlist/WatchlistGroupPanel';
import WatchlistStockTable from '../components/watchlist/WatchlistStockTable';
import StockSearch from '../components/StockSearch/StockSearch';
import AnimCard from '../components/common/Card/AnimCard';
import { AppPage, Modal, InlineTipCard, HrsButton, Input, Select, TextArea } from '../components';
import { BookmarkFill } from "@gravity-ui/icons";
import { Label, TextField, Description } from "@heroui/react";
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
    createWatchlistGroup,
    updateWatchlistGroup,
    deleteWatchlistGroup,
    activeGroupId,
    setActiveGroupId,
    items: tableList,
    itemsLoading,
    addItem,
    editItemDescription,
    removeItem,
    moveItem,
    indexByCode,
    setPageNum,
    pageNum,
    total,
    pages,
    pageSize,
  } = useWatchlistManager();







  const handlePageChange = useCallback((page: number) => {
    setPageNum(page);
  }, [setPageNum]);

  /** 分页配置对象，传递给 WatchlistStockTable */
  const pagination = useMemo(() => ({
    total,
    pageSize,
    pages,
    pageNum,
    onPageChange: handlePageChange,
  }), [total, pageSize, pages, pageNum, handlePageChange]);

  const [sortKey, setSortKey] = useState<SortKey>('default');
  const [keyword, setKeyword] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [addCode, setAddCode] = useState('');
  const [addName, setAddName] = useState('');
  const [addDescription, setAddDescription] = useState('');
  const [addError, setAddError] = useState<ParsedApiError | null>(null);

  const activeGroup = groups.find((g) => g.id === activeGroupId) ?? null;

  const visibleTableList = useMemo(() => {
    const filtered = tableList.filter((it) => matchKeyword(it, keyword, indexByCode));
    return sortItems(filtered, sortKey);
  }, [tableList, keyword, sortKey, indexByCode]);

  const handleAddSubmit = (code: string, name?: string) => {
    setAddCode(code);
    setAddName(name ?? code);
  };

  const confirmAdd = async () => {
    if (!addCode || activeGroupId == null) return;
    setAddError(null);
    try {
      await addItem(activeGroupId, { stockCode: addCode, stockName: addName, description: addDescription });
      setAddCode('');
      setAddName('');
      setAddDescription('');
      setAddOpen(false);
    } catch (err) {
      setAddError(getParsedApiError(err));
    }
  };


  return (
    <AppPage className="space-y-4 h-full">
      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-4 items-start h-full">
        {/* 左侧：分类（grid 默认 stretch，WatchlistGroupPanel 根节点自带 h-full 撑满高度） */}
        <WatchlistGroupPanel
          groups={groups}
          loading={groupsLoading}
          activeGroupId={activeGroupId}
          onSelect={setActiveGroupId}
          onCreate={createWatchlistGroup}
          onRename={updateWatchlistGroup}
          onDelete={deleteWatchlistGroup}
        />

        {/* 右侧：自选股列表 */}
        <AnimCard className="flex flex-col p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-md font-semibold text-text">
              {activeGroup ? activeGroup.name : '分组'}
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
              <Input
                className="w-64"
                placeholder="搜索名称/代码/拼音"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />

            </div>

            <div className="flex items-center gap-2 flex-1 justify-end">

              <HrsButton isDisabled={activeGroupId == null} onClick={() => setAddOpen(true)} >
                <Plus className="h-4 w-4" />新增
              </HrsButton>
            </div>
          </div>

          {activeGroupId == null ? (
            <div className="py-16 text-center text-text-secondary text-sm">
              请先选择或新增一个分组
            </div>
          ) : (
            <WatchlistStockTable
              items={visibleTableList}
              isLoading={itemsLoading}
              groups={groups}
              onEditDescription={editItemDescription}
              onDelete={removeItem}
              onMove={moveItem}
              pagination={pagination}
            />
          )}
        </AnimCard>
      </div>

      {/* 新增自选股弹窗（复用 StockSearch 选股） */}
      <Modal
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        size="sm"
      >
        <Modal.Header>
          <Modal.Icon className="bg-default text-foreground">
            <BookmarkFill className="size-4" />
          </Modal.Icon>
          <Modal.Heading>新增自选股</Modal.Heading>
        </Modal.Header>

        <Modal.Body>
          <form className="flex flex-col gap-4">
            <TextField className="w-full" variant="secondary">
              <Label>选择股票</Label>
              <StockSearch
                placeholder="输入股票代码或名称"
                value={addCode}
                originalRender
                onChange={setAddCode}
                onSubmit={handleAddSubmit}
              />
              {addCode && (
                <div className="mt-1 text-xs text-primary">已选：{addName}（{addCode}）</div>
              )}
            </TextField>
            <TextField className="w-full">
              <label className="text-sm font-medium text-text">分类描述</label>
              <TextArea
                className="w-full"
                value={addDescription}
                onChange={(e) => setAddDescription(e.target.value)}
                placeholder="请输入自选股描述（选填）"
                aria-describedby="stock-textarea-description"
                rows={5}
                maxLength={200}
              />
              <Description id="stock-textarea-description">
                {addDescription.length} / 200
              </Description>
            </TextField>
            <div className="mb-4">
              {addError && (
                <InlineTipCard variant="danger" content={addError} onDismiss={() => setAddError(null)} />
              )}
            </div>

          </form>





          {/* <div className="mb-3">
            <label className="text-sm text-text-secondary">选择股票</label>
            <div className="mt-1">
              <StockSearch
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
            <Input
              value={addNote}
              onChange={(e) => setAddNote(e.target.value)}
              placeholder="选填"
              className="mt-1 w-full"
            />
          </div>
          {addError ? (
            <div className="mb-4">
              <InlineTipCard variant="danger" content={addError} onDismiss={() => setAddError(null)} />
            </div>
          ) : null} */}
        </Modal.Body>


        <Modal.Footer>
          <HrsButton variant="secondary" onClick={() => setAddOpen(false)}>取消</HrsButton>
          <HrsButton variant="primary" isDisabled={!addCode} onClick={confirmAdd}>保存</HrsButton>
        </Modal.Footer>
      </Modal>

    </AppPage>
  );
};

export default WatchlistPage;
