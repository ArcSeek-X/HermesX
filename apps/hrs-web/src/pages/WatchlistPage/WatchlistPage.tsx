/**
 * @file WatchlistPage.tsx
 * @description 自选股管理页面：左侧分组 + 右侧列表（排序、搜索、新增、移动、编辑备注）。
 */

import { sortByOrder, sortByFieldDesc } from '@utils/sortFilter';
import { useMemo, useState, useCallback, useEffect } from 'react';
import { motion } from 'motion/react';
import { Plus } from 'lucide-react';
import { useWatchlistManager } from '../../hooks/useWatchlistManager';
import { Modal, InlineToast, HrsButton, HrsInput, TextArea, HrsSelect, AnimCard } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { StockSearch } from '@components/StockSearch/StockSearch';
import WatchlistGroupPanel from './components/WatchlistGroupPanel';
import WatchlistStockTable from './components/WatchlistStockTable';
import { BookmarkFill } from '@gravity-ui/icons';
import { Label, TextField, Description } from '@heroui/react';
import { type WatchlistItemWithQuote } from '../../api/watchlist';
import { getParsedApiError, type ParsedApiError } from '../../api/error';

type WatchlistSortField = 'default' | 'changePercent' | 'amount' | 'turnoverRate' | 'totalMv';

const WATCHLIST_SORT_OPTIONS: { field: WatchlistSortField; label: string }[] = [
  { field: 'default', label: '默认' },
  { field: 'changePercent', label: '涨幅' },
  { field: 'amount', label: '成交额' },
  { field: 'turnoverRate', label: '换手率' },
  { field: 'totalMv', label: '市值' },
];

function stockMatchesSearch(
  stock: WatchlistItemWithQuote,
  searchText: string,
  indexByCode: Map<string, { name: string; pinyin: string; pinyinShort: string }>,
): boolean {
  const query = searchText.trim().toLowerCase();
  if (!query) return true;
  if (stock.stockCode.toLowerCase().includes(query)) return true;
  if ((stock.stockName ?? '').toLowerCase().includes(query)) return true;
  const index = indexByCode.get(stock.stockCode);
  if (index) {
    if (index.name.toLowerCase().includes(query)) return true;
    if (index.pinyin.toLowerCase().includes(query)) return true;
    if (index.pinyinShort.toLowerCase().includes(query)) return true;
  }
  return false;
}

const WatchlistPage: React.FC = () => {
  const {
    groups,
    groupsLoading: isWatchlistGroupsRefreshing,
    createWatchlistGroup,
    updateWatchlistGroup,
    deleteWatchlistGroup,
    activeGroupId: currentGroupId,
    setActiveGroupId: setCurrentGroupId,
    items: watchlistItems,
    addItem,
    editItemDescription,
    removeItem,
    moveItem,
    indexByCode,
    setPageNum: setCurrentPageNum,
    pageNum: currentPageNum,
    total: totalStocks,
    pages: totalPages,
    pageSize: stocksPerPage,
  } = useWatchlistManager();

  const changeWatchlistPage = useCallback((page: number) => {
    setCurrentPageNum(page);
  }, [setCurrentPageNum]);

  const watchlistPagination = useMemo(() => ({
    total: totalStocks,
    pageSize: stocksPerPage,
    pages: totalPages,
    pageNum: currentPageNum,
    onPageChange: changeWatchlistPage,
  }), [totalStocks, stocksPerPage, totalPages, currentPageNum, changeWatchlistPage]);

  const [sortField, setSortField] = useState<WatchlistSortField>('default');
  const [stockSearchInput, setStockSearchInput] = useState('');
  const [debouncedStockSearch, setDebouncedStockSearch] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedStockSearch(stockSearchInput), 200);
    return () => clearTimeout(timer);
  }, [stockSearchInput]);

  const [addStockModalOpen, setAddStockModalOpen] = useState(false);
  const [selectedStockCode, setSelectedStockCode] = useState('');
  const [selectedStockName, setSelectedStockName] = useState('');
  const [stockNoteDraft, setStockNoteDraft] = useState('');
  const [addStockError, setAddStockError] = useState<ParsedApiError | null>(null);

  const currentWatchlistGroup = groups.find((g) => g.id === currentGroupId) ?? null;

  const displayedWatchlistStocks = useMemo(() => {
    const filtered = watchlistItems.filter((stock) => stockMatchesSearch(stock, debouncedStockSearch, indexByCode));
    if (sortField === 'default') {
      return sortByOrder(filtered, (stock) => stock.sortOrder, (stock) => stock.id);
    }
    return sortByFieldDesc(filtered, (stock) => stock.quote?.[sortField]);
  }, [watchlistItems, debouncedStockSearch, sortField, indexByCode]);

  const onSelectStockForAdd = (code: string, name?: string) => {
    setSelectedStockCode(code);
    setSelectedStockName(name ?? code);
  };

  const watchlistSave = async () => {
    if (!selectedStockCode || currentGroupId == null) return;
    setAddStockError(null);
    try {
      await addItem(currentGroupId, { stockCode: selectedStockCode, stockName: selectedStockName, description: stockNoteDraft });
      setSelectedStockCode('');
      setSelectedStockName('');
      setStockNoteDraft('');
      setAddStockModalOpen(false);
    } catch (err) {
      setAddStockError(getParsedApiError(err));
    }
  };

  return (
    <AppPage className="space-y-3 h-full">
      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-4 items-stretch h-full">
        <WatchlistGroupPanel
          groups={groups}
          loading={isWatchlistGroupsRefreshing}
          activeGroupId={currentGroupId}
          onSelect={setCurrentGroupId}
          onCreate={createWatchlistGroup}
          onRename={updateWatchlistGroup}
          onDelete={deleteWatchlistGroup}
        />

        <AnimCard className="flex flex-col p-4 h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-md font-semibold">
              {currentWatchlistGroup ? currentWatchlistGroup.name : '分组'}
            </span>
          </div>

          <div className="flex items-center justify-between gap-10 mb-3 flex-wrap">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <HrsSelect
                className="w-[100px] shrink-0"
                value={sortField}
                onChange={(v) => setSortField(v as WatchlistSortField)}
                options={WATCHLIST_SORT_OPTIONS.map((option) => ({ key: option.field, label: option.label }))}
                placeholder="排序"
              />
              <HrsInput
                className="flex-1 min-w-0"
                placeholder="搜索名称/代码/拼音"
                value={stockSearchInput}
                onChange={(e) => setStockSearchInput(e.target.value)}
              />
            </div>

            <div className="flex items-center shrink-0">
              <HrsButton isDisabled={currentGroupId == null} onClick={() => setAddStockModalOpen(true)}>
                <Plus className="h-4 w-4" />新增
              </HrsButton>
            </div>
          </div>

          {currentGroupId == null ? (
            <div className="py-16 text-center text-foreground-soft text-sm">
              请先选择或新增一个分组
            </div>
          ) : (
            <div className="h-full flex-1 min-h-0">
              <motion.div
                key="watchlist-stock-table"
                className="h-full"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                <WatchlistStockTable
                  watchlistItems={displayedWatchlistStocks}
                  watchlistGroups={groups}
                  onStockNoteSave={editItemDescription}
                  onStockRemove={removeItem}
                  onStockMove={moveItem}
                  watchlistPagination={watchlistPagination}
                />
              </motion.div>
            </div>
          )}
        </AnimCard>
      </div>

      <Modal
        isOpen={addStockModalOpen}
        onClose={() => setAddStockModalOpen(false)}
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
                value={selectedStockCode}
                originalRender
                onChange={setSelectedStockCode}
                onSubmit={onSelectStockForAdd}
              />
              {selectedStockCode && (
                <div className="mt-1 text-xs text-primary">已选：{selectedStockName}（{selectedStockCode}）</div>
              )}
            </TextField>
            <TextField className="w-full">
              <label className="text-sm font-medium text-text">分类描述</label>
              <TextArea
                className="w-full"
                value={stockNoteDraft}
                onChange={(e) => setStockNoteDraft(e.target.value)}
                placeholder="请输入自选股描述（选填）"
                aria-describedby="stock-textarea-description"
                rows={5}
                maxLength={200}
              />
              <Description id="stock-textarea-description">
                {stockNoteDraft.length} / 200
              </Description>
            </TextField>
            <div className="mb-4">
              {addStockError && (
                <InlineToast variant="danger" content={addStockError} onClose={() => setAddStockError(null)} />
              )}
            </div>
          </form>
        </Modal.Body>

        <Modal.Footer>
          <HrsButton variant="secondary" onClick={() => setAddStockModalOpen(false)}>取消</HrsButton>
          <HrsButton variant="primary" isDisabled={!selectedStockCode} onClick={watchlistSave}>保存</HrsButton>
        </Modal.Footer>
      </Modal>
    </AppPage>
  );
};

export default WatchlistPage;
