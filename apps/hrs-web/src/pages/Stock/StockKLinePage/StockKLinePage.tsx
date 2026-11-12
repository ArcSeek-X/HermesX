/**
 * @file Stock/StockKLinePage/StockKLinePage.tsx
 * @description 个股 K 线页：股票搜索、行情头部、多周期 K 线图与历史分页加载。
 *
 * 入口：既支持页内搜索，也支持外部带 ?stockCode= 直达（自选股、顶栏搜索等统一模式）。
 * 状态：全部收敛于 PageStateStore.kline 单一对象（stockInfo 个股行情 + klineInfo 周期/数据/来源 两键），
 * 刷新后由该对象恢复；股票代码与搜索框展示标签均从恢复的 stockInfo 派生，不额外持久化。
 * 最近搜索：未选中股票时显示搜索引导列表，查询成功后隐藏并让位给行情/K 线；显式入口加载成功时
 * 直接落库一条记录，并把搜索到的通用股票对象（StockInfo）+ 分时插入本地列表，清空时不二次请求。
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Switch, AnimCard } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { StockSearch } from '@components/StockSearch/StockSearch';
import { KLineChart } from '@components/kline/KLineChart';
import { StockInfoHeader } from '@components/kline/StockInfoHeader';
import { PeriodSelector } from '@components/kline/PeriodSelector';
import { useSearchParams } from 'react-router-dom';

import { klineApi, type KLinePeriod, type StockInfo, type KLinePoint } from '../../../api/kline';
import {
  recordRecentSearch,
  getRecentSearchList,
  clearRecentSearch,
  type RecentSearchItem,
} from '../../../api/recentSearch';
import { stocksApi, DEFAULT_LIMIT_SIZE } from '../../../api/stocks';
import type { BatchTimelineItem } from '../../../api/stocks';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useStockIndex } from '../../../hooks/useStockIndex';
import { usePageState } from '../../../stores/PageStateStore';
import type { StockIndexItem } from '../../../types/stockIndex';
import type { StockQuoteCore } from '../../../types/stock';
import type { RecentSearchEntry } from './components/RecentSearchCard';
import RecentSearchList from './components/RecentSearchList';

/** 新搜索/直达时默认展示分时 */
const DEFAULT_PERIOD: KLinePeriod = '1m';
/** 全量数据模式一次性拉取条数 */
const FULL_DATA_LIMIT = 10000;
/** 历史分页每次向前拉取条数 */
const HISTORY_PAGE_SIZE = 250;
/** 分钟线分页上限，超出后停止左滑加载，避免 ECharts 卡顿 */
const MINUTE_KLINE_MAX_LIMIT = 5000;
/** 分钟类周期（用于分页上限判定） */
const MINUTE_PERIODS: KLinePeriod[] = ['5m', '15m', '30m', '60m', '120m'];
/** 展示全量数据开关的周期 */
const FULL_DATA_PERIODS: KLinePeriod[] = ['5d', 'daily', 'weekly'];

/** 生成与搜索框一致的展示标签「名称（规范代码）」：优先用本地索引补市场后缀，缺失时退化为行情名+代码 */
function buildSearchLabel(stockIndex: StockIndexItem[], stockInfo: StockQuoteCore, code: string): string {
  const hit = stockIndex.find((item) => item.displayCode === code);
  if (hit) return hit.name ? `${hit.name}（${hit.canonicalCode}）` : hit.canonicalCode;
  return stockInfo.name ? `${stockInfo.name}（${stockInfo.code || code}）` : code;
}

/** 从任意输入（纯代码、带市场后缀、或「名称（代码）」展示格式）中提取纯数字股票代码 */
function extractNumericCode(raw: string): string {
  const cleaned = raw.replace(/[（）]/g, '');
  const match = cleaned.match(/\d{4,7}/);
  return match ? match[0] : '';
}

/** 最近搜索卡片渲染 / 本地列表上限：直接复用批量接口的默认 limiteSize（DEFAULT_LIMIT_SIZE），确保「前端渲染卡片数量 == limiteSize」一致；后端 MAX_RECENT_SEARCH_RECORDS 需 ≥ 此值以供给足够 codes。 */
const RECENT_SEARCH_DISPLAY_LIMIT = DEFAULT_LIMIT_SIZE;

/** 剥离交易所后缀并转大写，作为落库代码与行情纯代码的统一关联键（如 600519.SH → 600519） */
function normalizeStockCode(stockCode: string): string {
  return stockCode.split('.')[0].trim().toUpperCase();
}

/** 历史记录缺行情时构造占位 StockInfo（仅 code/name，数值字段置 null 降级展示） */
function buildPlaceholderStockInfo(record: RecentSearchItem): StockInfo {
  return {
    code: record.stockCode,
    name: record.stockName ?? '',
    price: null,
    change: null,
    changePct: null,
    amount: null,
    volume: null,
    turnoverRate: null,
    prevClose: null,
    open: null,
    high: null,
    low: null,
    amplitude: null,
    peRatioTTM: null,
    totalMarketCap: null,
    updateTime: null,
    source: null,
  };
}

/**
 * 阶段一：历史记录 + 批量行情组装卡片（不含分时）。
 * 首屏只需 list + batch-quote 即可渲染；分时留到阶段二异步补齐，避免被慢接口拖住整页。
 */
async function buildRecentEntries(items: RecentSearchItem[]): Promise<RecentSearchEntry[]> {
  const codes = items.map((it) => normalizeStockCode(it.stockCode)).filter(Boolean);
  const quotes = codes.length ? await stocksApi.batchQuote(codes) : [];
  const quoteMap = new Map(quotes.map((q) => [normalizeStockCode(q.code), q]));
  return items.slice(0, RECENT_SEARCH_DISPLAY_LIMIT).map((it) => {
    const normalizedCode = normalizeStockCode(it.stockCode);
    const quote = quoteMap.get(normalizedCode);
    const info: StockInfo = quote ? { ...quote, updateTime: null, source: null } : buildPlaceholderStockInfo(it);
    return {
      info,
      timeline: [],
      prevClose: quote?.prevClose ?? null,
    };
  });
}

/** 阶段二：把批量分时按代码回填到已渲染的卡片，不阻塞首屏。 */
function mergeRecentTimelines(
  entries: RecentSearchEntry[],
  timelines: BatchTimelineItem[],
): RecentSearchEntry[] {
  if (timelines.length === 0) return entries;
  const timelineMap = new Map(timelines.map((t) => [normalizeStockCode(t.code), t]));
  return entries.map((entry) => {
    const tl = timelineMap.get(normalizeStockCode(entry.info.code));
    if (!tl) return entry;
    return {
      ...entry,
      timeline: tl.points ?? [],
      prevClose: tl.prevClose ?? entry.prevClose,
    };
  });
}

const StockKLinePage: React.FC = () => {
  const { t } = useUiLanguage();
  const { state: pageState, setState: setPageState } = usePageState();
  const [searchParams, setSearchParams] = useSearchParams();
  const { index: stockIndex } = useStockIndex();

  // 当前股票代码：仅内存态，刷新后从已恢复的 pageState.kline.stockInfo.code 派生
  // 取舍：上次加载失败（stockInfo 为 null）时，刷新后代码为空、不再自动重试
  const [stockCode, setStockCode] = useState(() => pageState.kline.stockInfo?.code ?? '');
  // 全量数据开关：开启时按 FULL_DATA_LIMIT 拉取
  const [allDataEnabled, setAllDataEnabled] = useState(false);
  // 个股行情与 K 线的加载状态；加载失败时保存错误文案用于错误态展示
  const [isStockDataLoading, setIsStockDataLoading] = useState(false);
  const [stockDataError, setStockDataError] = useState<string | null>(null);
  // 搜索框输入缓冲：仅用于受控显示，不驱动加载；加载只认解析后的规范代码
  const [searchDraft, setSearchDraft] = useState(stockCode);
  // 搜索框展示标签：以已加载行情为准生成，可由恢复的 stockInfo 直接重算，无需持久化
  const [searchDisplayLabel, setSearchDisplayLabel] = useState('');

  // 页面状态：个股行情 stockInfo + K 线数据/周期/来源 klineInfo（刷新后由该单一对象恢复）
  const stockInfo = pageState.kline.stockInfo;
  const klineInfo = pageState.kline.klineInfo;
  const klineData = klineInfo.klineData;
  const period = klineInfo.period;
  const prevClose = stockInfo?.prevClose ?? null;

  // 以下 ref 保存最新值，规避回调/闭包捕获旧值；在 commit 后用 effect 同步，
  // 不在渲染期直接读写 ref（否则触发 react-hooks/refs 报错）
  const latestPeriodRef = useRef(period);
  const latestStockCodeRef = useRef(stockCode);
  const allDataEnabledRef = useRef(allDataEnabled);
  useEffect(() => {
    latestPeriodRef.current = period;
    latestStockCodeRef.current = stockCode;
    allDataEnabledRef.current = allDataEnabled;
  }, [period, stockCode, allDataEnabled]);
  // 已加载的股票代码，用于换股去重（避免 PageStateStore 残留旧数据导致不刷新）
  const lastLoadedStockCodeRef = useRef<string | null>(null);
  // 整体加载请求序号：递增使过期结果作废
  const stockDataRequestSeqRef = useRef(0);
  // 历史分页：并发锁 + 请求序号（换股/换周期时作废进行中的分页）
  const historyLoadLockRef = useRef(false);
  const historyRequestSeqRef = useRef(0);
  // 待记录的最近搜索代码：仅显式搜索 / ?stockCode= 直达时设置，切周期等隐式重载不设置
  const recordPendingStockCodeRef = useRef<string | null>(null);
  // 最近搜索：前端本地维护的卡片数据源（搜索时插入 stockInfo + 分时，清空不二次请求）
  const [recentEntries, setRecentEntries] = useState<RecentSearchEntry[]>([]);
  const [isRecentHistoryLoading, setIsRecentHistoryLoading] = useState(true);

  // 初始化：阶段一 list + 行情立即渲染卡片，阶段二分时异步回填（不阻塞首屏，满足"清空不请求"）
  useEffect(() => {
    let active = true;
    const init = async () => {
      setIsRecentHistoryLoading(true);
      try {
        const items = await getRecentSearchList();
        const entries = await buildRecentEntries(items);
        if (!active) return;
        setRecentEntries(entries);
        setIsRecentHistoryLoading(false); // 首屏先渲染，分时区域随后补齐

        const codes = items
          .slice(0, RECENT_SEARCH_DISPLAY_LIMIT)
          .map((it) => normalizeStockCode(it.stockCode))
          .filter(Boolean);
        if (codes.length === 0) return;
        void stocksApi
          .batchTimeline(codes)
          .then((timelines) => {
            if (!active) return;
            setRecentEntries((prev) =>
              // 清空后 prev 为空，跳过回填，避免把旧分时写回已清空的列表
              prev.length === 0 ? prev : mergeRecentTimelines(prev, timelines),
            );
          })
          .catch((error) => {
            console.error('Failed to load recent timelines:', error);
          });
      } catch (error) {
        console.error('Failed to load recent searches:', error);
        if (active) setIsRecentHistoryLoading(false);
      }
    };
    void init();
    return () => {
      active = false;
    };
  }, []);

  /**
   * 搜索成功后把通用股票对象 + 分时插入本地列表（去重置顶、限长），供最近搜索卡片即时展示，不触发任何网络请求。
   * 优先用行情昨收，缺失时回退分时末点（盘中可外推、收盘即收盘价）。
   */
  const insertRecentEntry = useCallback((info: StockInfo, timeline: KLinePoint[]) => {
    setRecentEntries((prev) => {
      const normalizedCode = normalizeStockCode(info.code);
      const deduped = prev.filter((entry) => normalizeStockCode(entry.info.code) !== normalizedCode);
      const next: RecentSearchEntry = {
        info,
        timeline,
        prevClose: info.prevClose ?? (timeline.length ? timeline[timeline.length - 1].close : null),
      };
      return [next, ...deduped].slice(0, RECENT_SEARCH_DISPLAY_LIMIT);
    });
  }, []);

  /** 一键清空：先清空本地（即时反馈），再同步服务端 */
  const clearRecentSearches = useCallback(async () => {
    try {
      await clearRecentSearch();
    } catch (error) {
      console.error('Failed to clear recent searches:', error);
      return;
    }
    setRecentEntries([]);
  }, []);

  /** 加载指定股票的行情与 K 线数据 */
  const loadStockData = useCallback(
    async (code: string, targetPeriod: KLinePeriod, limit?: number) => {
      if (!code) return;
      lastLoadedStockCodeRef.current = code;
      const requestId = ++stockDataRequestSeqRef.current;
      historyRequestSeqRef.current++; // 整体数据即将替换，作废进行中的分页
      setIsStockDataLoading(true);
      setStockDataError(null);
      try {
        const [info, kline] = await Promise.all([
          klineApi.fetchStockInfo(code),
          klineApi.fetchKLine(code, targetPeriod, limit),
        ]);
        if (requestId !== stockDataRequestSeqRef.current) return; // 已有更新的请求，丢弃本次
        setPageState('kline', (prev) => ({
          ...prev,
          stockInfo: info,
          klineInfo: {
            ...prev.klineInfo,
            period: targetPeriod,
            klineData: kline.data,
            klineSource: kline.source ?? null,
          },
        }));
        // 显式入口加载成功：落库（静默 POST，不影响展示）+ 前端本地插入卡片数据
        if (recordPendingStockCodeRef.current === code) {
          recordPendingStockCodeRef.current = null;
          void recordRecentSearch({ stockCode: code, stockName: info.name ?? null }).catch((error) => {
            // 记录失败不阻断 K 线页主流程
            console.error('Failed to record recent search:', error);
          });
          insertRecentEntry(info, kline.data);
        }
      } catch (err) {
        if (requestId !== stockDataRequestSeqRef.current) return;
        console.error('Failed to load stock data:', err);
        setStockDataError(t('kline.error'));
      } finally {
        if (requestId === stockDataRequestSeqRef.current) setIsStockDataLoading(false);
      }
    },
    [t, setPageState, insertRecentEntry],
  );

  /** 切换当前周期：周期持久化于 pageState.kline.klineInfo.period */
  const changePeriod = useCallback(
    (nextPeriod: KLinePeriod) => {
      setPageState('kline', (prev) => ({
        ...prev,
        klineInfo: { ...prev.klineInfo, period: nextPeriod },
      }));
      latestPeriodRef.current = nextPeriod; // 同步 ref，避免同一 tick 内读到旧周期
    },
    [setPageState],
  );

  /** 搜索提交：解析出规范代码后切到该股票，并默认使用分时周期 */
  const handleSearchSubmit = useCallback(
    async (rawCode: string) => {
      // 先尝试从输入中提取纯数字代码（兼容「名称（代码）」展示格式与 .SH/.SZ 后缀）
      let resolvedCode = extractNumericCode(rawCode);
      if (!resolvedCode) {
        // 纯中文名等无数字输入：经后端搜索解析为规范代码
        try {
          const results = await klineApi.searchStocks(rawCode.trim());
          if (!results?.length) {
            setStockDataError(t('kline.error'));
            return;
          }
          resolvedCode = results[0].code;
        } catch {
          setStockDataError(t('kline.error'));
          return;
        }
      }
      recordPendingStockCodeRef.current = resolvedCode;
      setStockCode(resolvedCode);
      changePeriod(DEFAULT_PERIOD);
      setAllDataEnabled(false); // 换股重置全量数据开关
      // 同步 URL 的 stockCode：否则进入时若带旧代码，刷新会恢复到 URL 里的旧股票而非当前搜索的
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('stockCode', resolvedCode);
          return next;
        },
        { replace: true },
      );
      void loadStockData(resolvedCode, DEFAULT_PERIOD);
    },
    [changePeriod, loadStockData, setStockCode, setSearchParams, t],
  );

  /** 切换周期：沿用当前股票与全量开关状态重新拉取 */
  const handlePeriodChange = useCallback(
    (nextPeriod: KLinePeriod) => {
      changePeriod(nextPeriod);
      const code = latestStockCodeRef.current;
      if (!code) return;
      const limit = allDataEnabledRef.current ? FULL_DATA_LIMIT : undefined;
      void loadStockData(code, nextPeriod, limit);
    },
    [changePeriod, loadStockData],
  );

  /** 切换全量数据开关：开启拉全量，关闭回退到周期默认条数 */
  const handleFullDataToggle = useCallback(
    (enabled: boolean) => {
      setAllDataEnabled(enabled);
      const code = latestStockCodeRef.current;
      if (!code) return;
      const limit = enabled ? FULL_DATA_LIMIT : undefined;
      void loadStockData(code, latestPeriodRef.current, limit);
    },
    [loadStockData],
  );

  /** 左滑加载更早历史：前置拼接并去重/保序，防止并发与重复 */
  const loadMoreHistory = useCallback(async () => {
    if (historyLoadLockRef.current || klineData.length === 0) return;
    const currentPeriod = latestPeriodRef.current;
    if (MINUTE_PERIODS.includes(currentPeriod) && klineData.length >= MINUTE_KLINE_MAX_LIMIT) return;
    const earliestDate = klineData[0]?.date;
    if (!earliestDate) return;

    historyLoadLockRef.current = true;
    const requestId = ++historyRequestSeqRef.current;
    try {
      const more = await klineApi.fetchKLine(
        latestStockCodeRef.current,
        currentPeriod,
        HISTORY_PAGE_SIZE,
        earliestDate,
      );
      if (requestId !== historyRequestSeqRef.current) return; // 已过期（换股/换周期/整页重载）
      if (more?.data?.length) {
        setPageState('kline', (prev) => {
          const current = prev.klineInfo;
          const currentEarliest = current.klineData[0]?.date;
          const older = currentEarliest
            ? more.data.filter((item) => item.date < currentEarliest)
            : more.data;
          if (!older.length) return prev;
          return { ...prev, klineInfo: { ...current, klineData: [...older, ...current.klineData] } };
        });
      }
    } catch (err) {
      console.error('Failed to load more history:', err);
    } finally {
      historyLoadLockRef.current = false;
    }
  }, [klineData, setPageState]);

  // stockCode 变化（页内搜索 / 外部直达）且尚未加载该代码时，拉取数据
  useEffect(() => {
    if (!stockCode || lastLoadedStockCodeRef.current === stockCode) return;
    void loadStockData(stockCode, latestPeriodRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stockCode]);

  // 外部带 ?stockCode= 直达：写入 stockCode 触发加载，并重置展示标签避免残留上一只股票
  useEffect(() => {
    const code = searchParams.get('stockCode');
    if (!code) return;
    const pure = code.split('.')[0].trim();
    if (!pure || pure === latestStockCodeRef.current) return;
    // 外部页面跳转（自选股/顶栏/Scanner 等）视为显式直达；刷新后代码未变不会走到这里
    recordPendingStockCodeRef.current = pure;
    setSearchDraft(pure);
    setSearchDisplayLabel('');
    setStockCode(pure);
  }, [searchParams]);

  // 搜索框展示标签：始终以当前已加载行情为准，行情或索引变化时重算（索引后到会自动补后缀）
  useEffect(() => {
    if (!stockInfo) return;
    const code = latestStockCodeRef.current;
    if (!code) return;
    setSearchDisplayLabel(buildSearchLabel(stockIndex, stockInfo, code));
  }, [stockInfo, stockIndex]);

  return (
    <AppPage>
      <div className="space-y-4">
        <PageHeader title={t('layout.nav.kline.title')} description={t('layout.nav.kline.description')} />
        {/* 页内股票搜索框 */}
        <div className="max-w-md">
          <StockSearch
            value={searchDraft}
            displayValue={searchDisplayLabel || undefined}
            size="xl"
            onChange={setSearchDraft}
            onSubmit={handleSearchSubmit}
            onClear={() => {
              recordPendingStockCodeRef.current = null;
              setSearchDraft('');
              setStockCode('');
              setSearchDisplayLabel('');
              setPageState('kline', (prev) => ({
                ...prev,
                stockInfo: null,
                klineInfo: { ...prev.klineInfo, klineData: [], klineSource: null },
              }));
              // 同步移除 URL 的 stockCode：否则刷新后「外部直达」逻辑会按残留代码重新恢复该股票
              setSearchParams(
                (prev) => {
                  const next = new URLSearchParams(prev);
                  next.delete('stockCode');
                  return next;
                },
                { replace: true },
              );
            }}
          />
        </div>

        {/* 最近搜索：仅未选中股票时作为搜索引导，选中后让位给行情/K 线 */}
        {!stockInfo && (
          <>
            {stockDataError && !isStockDataLoading && (
              <div className="flex items-center justify-center py-6 text-muted-text">{stockDataError}</div>
            )}
            <RecentSearchList
              list={recentEntries}
              isHistoryLoading={isRecentHistoryLoading}
              onClear={clearRecentSearches}
            />
          </>
        )}

        {stockInfo && (
          <>
            <AnimCard className="p-5 min-h-0">
              <StockInfoHeader info={stockInfo} />
            </AnimCard>

            <AnimCard className="p-5 min-h-0">
              <div className="w-full space-y-3">
                {isStockDataLoading ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
                  </div>
                ) : stockDataError ? (
                  <div className="flex items-center justify-center py-20 text-muted-text">{stockDataError}</div>
                ) : klineData.length === 0 ? (
                  <div className="flex items-center justify-center py-20 text-muted-text">暂无 K 线数据</div>
                ) : (
                  <KLineChart
                    data={klineData}
                    period={period}
                    height="500px"
                    prevClose={prevClose}
                    stockCode={stockCode}
                    showAllData={allDataEnabled}
                    onDataZoomBoundary={allDataEnabled ? undefined : loadMoreHistory}
                  />
                )}

                <div className="flex items-center justify-between">
                  {FULL_DATA_PERIODS.includes(period) && (
                    <Switch
                      checked={allDataEnabled}
                      onChange={handleFullDataToggle}
                      label={t('kline.fullData')}
                      className="whitespace-nowrap text-muted-text"
                    />
                  )}
                  <PeriodSelector period={period} onChange={handlePeriodChange} />
                </div>
              </div>
            </AnimCard>
          </>
        )}

      </div>
    </AppPage>
  );
};

export default StockKLinePage;
