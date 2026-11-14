/**
 * 个股 K 线页：选中股票以 stores/StockKLine.ts 为唯一真源（sessionStorage 持久化），
 * URL ?stockCode= 仅作外部注入与镜像；行情与 K 线由 StockKLineChartPanel 自行加载。
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { StockSearch } from '@components/StockSearch/StockSearch';
import { useSearchParams } from 'react-router-dom';

import { klineApi, type StockInfo } from '../../../api/kline';
import {
  recordRecentSearch,
  getRecentSearchList,
  clearRecentSearch,
  type RecentSearchItem,
} from '../../../api/recentSearch';
import { stocksApi, DEFAULT_LIMIT_SIZE } from '../../../api/stocks';
import type { BatchTimelineItem } from '../../../api/stocks';
import {
  getStockKLineInfo,
  removeStockKLineInfo,
  setStockKLineInfo,
  useStockKLineStore,
} from '../../../stores/StockKLine';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useStockIndex } from '../../../hooks/useStockIndex';
import { getStockDisplayLabel } from '../../../utils/stock/stockNameDisplay';
import type { StockIndexItem } from '../../../types/stockIndex';
import type { StockSearchSelection } from '@components/StockSearch/types';
import type { StockRef } from '../../../types/stock';
import RecentSearchStockList from './components/RecentSearchStockList';
import StockKLineChartPanel from './components/StockKLineChartPanel';
import { createEmptyStockQuote, type RecentSearchStockCardData } from './components/recentSearchStockData';

/** 最近搜索卡片展示上限，与批量行情接口的默认 limit 保持一致 */
const RECENT_SEARCH_DISPLAY_LIMIT = DEFAULT_LIMIT_SIZE;

/**
 * 生成搜索框展示标签「名称（规范代码）」，如「贵州茅台（600519.SH）」。
 *
 * 页面与 store 只持有纯代码，交易所后缀只存在于本地索引的 canonicalCode，
 * 因此必须按 displayCode 反查索引；URL 直达、刷新恢复、内部选股、行情补名
 * 等所有入口都共用这里生成标签。返回值按信息完整度退化，见下方示例。
 *
 * @example
 * // 索引含 { canonicalCode: '600519.SH', displayCode: '600519', name: '贵州茅台' }
 * buildSearchLabel(stockIndex, '600519', '');      // => '贵州茅台（600519.SH）'
 * buildSearchLabel([], '600519', '贵州茅台');       // => '贵州茅台（600519）'
 * buildSearchLabel([], '600519', undefined);       // => '600519'
 *
 * 维护约定：后续做代码精简 / 优化时不要删掉这段注释，它记录了
 * 「后缀只能来自索引」与「所有入口共用同一标签路径」这两个设计约束。
 */
function buildSearchLabel(
  stockIndex: StockIndexItem[], // 本地股票索引，按 displayCode 匹配
  code: string, // 纯代码，如 '600519'
  fallbackName?: string, // 索引未命中时的名称兜底
): string {
  const indexMatch = stockIndex.find((item) => item.displayCode === code);
  if (indexMatch?.name) {
    return getStockDisplayLabel(indexMatch.name, indexMatch.canonicalCode);
  }
  return getStockDisplayLabel(fallbackName, indexMatch?.canonicalCode ?? code);
}

/** 从纯代码、带后缀代码或「名称（代码）」中提取纯数字股票代码 */
function extractNumericCode(rawText: string): string {
  const cleanedText = rawText.replace(/[（）]/g, '');
  const match = cleanedText.match(/\d{4,7}/);
  return match ? match[0] : '';
}

/** 剥离交易所后缀并转大写，统一行情与落库代码的关联键 */
function normalizeStockCode(stockCode: string): string {
  return stockCode.split('.')[0].trim().toUpperCase();
}

/** 组装最近搜索卡片；分时由 fillRecentCardTimelines 异步补齐，避免慢接口阻塞首屏 */
async function buildRecentStockCards(
  recentRecords: RecentSearchItem[],
): Promise<RecentSearchStockCardData[]> {
  const recentStockCodes = recentRecords
    .map((recentRecord) => normalizeStockCode(recentRecord.stockCode))
    .filter(Boolean);
  const batchQuotes = recentStockCodes.length ? await stocksApi.batchQuote(recentStockCodes) : [];
  const quotesByCode = new Map(
    batchQuotes.map((batchQuote) => [normalizeStockCode(batchQuote.code), batchQuote]),
  );
  return recentRecords.slice(0, RECENT_SEARCH_DISPLAY_LIMIT).map((recentRecord) => {
    const normalizedCode = normalizeStockCode(recentRecord.stockCode);
    const matchedQuote = quotesByCode.get(normalizedCode);
    const cardStockQuote: StockInfo = matchedQuote
      ? { ...matchedQuote, updateTime: null, source: null }
      : createEmptyStockQuote(recentRecord.stockCode, recentRecord.stockName ?? '');
    return {
      stockQuote: cardStockQuote,
      timeline: [],
      prevClose: matchedQuote?.prevClose ?? null,
    };
  });
}

/** 按代码把批量分时回填到已渲染卡片 */
function mergeRecentTimelines(
  recentCards: RecentSearchStockCardData[],
  batchTimelines: BatchTimelineItem[],
): RecentSearchStockCardData[] {
  if (batchTimelines.length === 0) return recentCards;
  const timelinesByCode = new Map(
    batchTimelines.map((timelineItem) => [normalizeStockCode(timelineItem.code), timelineItem]),
  );
  return recentCards.map((recentCard) => {
    const timelineItem = timelinesByCode.get(normalizeStockCode(recentCard.stockQuote.code));
    if (!timelineItem) return recentCard;
    return {
      ...recentCard,
      timeline: timelineItem.points ?? [],
      prevClose: timelineItem.prevClose ?? recentCard.prevClose,
    };
  });
}

const StockKLinePage: React.FC = () => {
  const { t } = useUiLanguage();
  const [searchParams, setSearchParams] = useSearchParams();
  // router 的 setSearchParams 引用随 search 变化；放进 ref 保持业务回调稳定，避免 URL 注入 effect 被重复触发
  const setSearchParamsRef = useRef(setSearchParams);
  useEffect(() => {
    setSearchParamsRef.current = setSearchParams;
  }, [setSearchParams]);
  const { index: stockIndex } = useStockIndex();

  const selectedKLineStock = useStockKLineStore((klineStore) => klineStore.stockKLineSelected);
  const stockCode = selectedKLineStock?.code ?? '';
  // 标签是派生值：本地索引异步到位后页面重渲染即自动补上后缀与名称
  const stockDisplayLabel = buildSearchLabel(stockIndex, stockCode, selectedKLineStock?.name);
  const [stockSearchValue, setStockSearchValue] = useState(stockCode);
  const [searchError, setSearchError] = useState<string | null>(null);
  /** 每次显式选中递增，让图表面板按「一次查看」重新实例化并重新加载 */
  const [stockViewSession, setStockViewSession] = useState(0);

  const [recentStockCards, setRecentStockCards] = useState<RecentSearchStockCardData[]>([]);
  const [isRecentCardsLoading, setIsRecentCardsLoading] = useState(true);
  const isRecentCardsMountedRef = useRef(true);

  /** 只回填已存在的卡片；清空后列表为空时跳过，避免把旧分时写回 */
  const fillRecentCardTimelines = useCallback(async (recentStockCodes: string[]) => {
    const uniqueStockCodes = [...new Set(recentStockCodes.filter(Boolean))].slice(0, RECENT_SEARCH_DISPLAY_LIMIT);
    if (uniqueStockCodes.length === 0) return;
    try {
      const batchTimelines = await stocksApi.batchTimeline(uniqueStockCodes);
      if (!isRecentCardsMountedRef.current || batchTimelines.length === 0) return;
      setRecentStockCards((currentRecentCards) =>
        currentRecentCards.length === 0
          ? currentRecentCards
          : mergeRecentTimelines(currentRecentCards, batchTimelines),
      );
    } catch (error) {
      console.error('Failed to load recent timelines:', error);
    }
  }, []);

  useEffect(() => {
    const loadRecentSearches = async () => {
      setIsRecentCardsLoading(true);
      try {
        const recentRecords = await getRecentSearchList();
        const remoteCards = await buildRecentStockCards(recentRecords);
        if (!isRecentCardsMountedRef.current) return;
        // 列表返回前用户可能已搜索出新卡片，按规范化代码去重合入，保留本地最新项置顶
        setRecentStockCards((currentRecentCards) => {
          const locallyInsertedCards = currentRecentCards.filter(
            (localCard) =>
              !remoteCards.some(
                (remoteCard) =>
                  normalizeStockCode(remoteCard.stockQuote.code) === normalizeStockCode(localCard.stockQuote.code),
              ),
          );
          return [...locallyInsertedCards, ...remoteCards].slice(0, RECENT_SEARCH_DISPLAY_LIMIT);
        });
        setIsRecentCardsLoading(false);

        const recentStockCodes = recentRecords
          .slice(0, RECENT_SEARCH_DISPLAY_LIMIT)
          .map((recentRecord) => normalizeStockCode(recentRecord.stockCode))
          .filter(Boolean);
        void fillRecentCardTimelines(recentStockCodes);
      } catch (error) {
        console.error('Failed to load recent searches:', error);
        if (isRecentCardsMountedRef.current) setIsRecentCardsLoading(false);
      }
    };
    void loadRecentSearches();
    return () => {
      isRecentCardsMountedRef.current = false;
    };
  }, [fillRecentCardTimelines]);

  /** 搜索成功后插入本地卡片（去重置顶、限长）；迷你分时与主图 1 分钟 K 线解耦 */
  const upsertRecentStockCard = useCallback((stockQuote: StockInfo) => {
    const normalizedCode = normalizeStockCode(stockQuote.code);
    setRecentStockCards((currentRecentCards) => {
      const dedupedCards = currentRecentCards.filter(
        (existingCard) => normalizeStockCode(existingCard.stockQuote.code) !== normalizedCode,
      );
      const insertedCard: RecentSearchStockCardData = {
        stockQuote,
        timeline: [],
        prevClose: stockQuote.prevClose ?? null,
      };
      return [insertedCard, ...dedupedCards].slice(0, RECENT_SEARCH_DISPLAY_LIMIT);
    });
    void fillRecentCardTimelines([normalizedCode]);
  }, [fillRecentCardTimelines]);

  /** 图表面板首次加载成功：插入卡片并落库，保持「行情成功后才记录」的契约 */
  const handleStockQuoteLoaded = useCallback((stockQuote: StockInfo) => {
    const selectedCode = getStockKLineInfo()?.code;
    if (!selectedCode) return;
    upsertRecentStockCard(stockQuote);
    // 落库异常不得中断主流程，否则卡片不会插入，还会误报「K 线数据加载失败」
    const reportRecordFailure = (error: unknown) => console.error('Failed to record recent search:', error);
    try {
      void Promise.resolve(
        recordRecentSearch({ stockCode: selectedCode, stockName: stockQuote.name ?? null }),
      ).catch(reportRecordFailure);
    } catch (error) {
      reportRecordFailure(error);
    }
  }, [upsertRecentStockCard]);

  const clearRecentSearches = useCallback(async () => {
    try {
      await clearRecentSearch();
    } catch (error) {
      console.error('Failed to clear recent searches:', error);
      return;
    }
    setRecentStockCards([]);
  }, []);

  /** 唯一业务写入口：写持久化真源 + 同步 URL 镜像 + 复位 UI；图表加载由面板自行驱动 */
  const commitStockSelection = useCallback(
    (stockRef: StockRef, options?: { syncUrl?: boolean }) => {
      const code = normalizeStockCode(stockRef.code);
      if (!code) return;
      const name = typeof stockRef.name === 'string' ? stockRef.name : '';
      setStockKLineInfo({ code, name });
      // KeepAlive 缓存键忽略 search，改 URL 只更新地址栏、不会切换页面实例
      if (options?.syncUrl !== false) {
        setSearchParamsRef.current(
          (prev) => {
            if (prev.get('stockCode') === code) return prev;
            const next = new URLSearchParams(prev);
            next.set('stockCode', code);
            return next;
          },
          { replace: true },
        );
      }
      setStockSearchValue(code);
      setSearchError(null);
      setStockViewSession((session) => session + 1);
    },
    [],
  );

  const clearSelectedStock = useCallback(() => {
    setSearchError(null);
    setStockSearchValue('');
    removeStockKLineInfo();
    // 用最新 search 判断，避免残留的 ?stockCode= 被单向注入 effect 复活股票
    setSearchParamsRef.current(
      (prev) => {
        if (!prev.has('stockCode')) return prev;
        const next = new URLSearchParams(prev);
        next.delete('stockCode');
        return next;
      },
      { replace: true },
    );
  }, []);

  const handleStockSearchSubmit = useCallback(
    async (stock: StockSearchSelection) => {
      const submittedKeyword = stock.canonicalCode.trim();
      setSearchError(null);
      if (!submittedKeyword) {
        setSearchError(t('kline.stockNotFound'));
        return;
      }
      let resolvedCode = extractNumericCode(submittedKeyword);
      let resolvedName = stock.name ?? '';
      if (!resolvedCode) {
        // 纯中文名等无数字输入：经后端搜索解析为规范代码
        try {
          const searchResults = await klineApi.searchStocks(submittedKeyword);
          if (!searchResults?.length) {
            setSearchError(t('kline.stockNotFound'));
            return;
          }
          resolvedCode = searchResults[0].code;
          resolvedName = searchResults[0].name ?? '';
        } catch {
          // 搜索接口异常属于加载失败，不是「未找到股票」
          setSearchError(t('kline.error'));
          return;
        }
      }
      commitStockSelection({ code: normalizeStockCode(resolvedCode), name: resolvedName });
    },
    [commitStockSelection, t],
  );

  // URL 只做单向注入：参数消失不能当作清空，否则持久化中的股票会被冲掉
  useEffect(() => {
    const stockCodeFromUrl = searchParams.get('stockCode');
    if (!stockCodeFromUrl) return;
    const code = normalizeStockCode(stockCodeFromUrl);
    if (!code || getStockKLineInfo()?.code === code) return;
    commitStockSelection({ code, name: '' }, { syncUrl: false });
  }, [searchParams, commitStockSelection]);

  return (
    <AppPage>
      <div className="space-y-4">
        <PageHeader title={t('layout.nav.kline.title')} description={t('layout.nav.kline.description')} />

        {/* 搜索区：限宽股票搜索框，承载联想、选股提交与清空 */}
        <div className="max-w-md">
          <StockSearch
            value={stockSearchValue}
            displayValue={stockDisplayLabel || undefined}
            size="xl"
            onChange={setStockSearchValue}
            onSubmit={handleStockSearchSubmit}
            onClear={clearSelectedStock}
          />
        </div>

        {/* 未选中股票：展示搜索异常提示与最近搜索记录 */}
        {!stockCode && (
          <>
            {searchError && (
              <div className="flex items-center justify-center py-6 text-muted-text">{searchError}</div>
            )}
            <RecentSearchStockList
              recentCards={recentStockCards}
              isRecentCardsLoading={isRecentCardsLoading}
              onClearRecentSearches={clearRecentSearches}
            />
          </>
        )}

        {/* 已选中股票：面板自行加载行情/K 线并处理周期、全量与左滑；key 绑定选股会话号，重复搜索同一股票也重新挂载 */}
        {stockCode && (
          <StockKLineChartPanel
            key={`${stockCode}-${stockViewSession}`}
            stockCode={stockCode}
            onStockQuoteLoaded={handleStockQuoteLoaded}
          />
        )}
      </div>
    </AppPage>
  );
};

export default StockKLinePage;
