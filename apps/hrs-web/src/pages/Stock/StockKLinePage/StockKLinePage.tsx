/**
 * @file Stock/StockKLinePage/StockKLinePage.tsx
 * @description 个股 K 线页：股票搜索、行情头部、多周期 K 线图与历史分页加载。
 *
 * 入口：既支持页内搜索，也支持外部带 ?stockCode= 直达（自选股、顶栏搜索等统一模式）。
 * 状态：全部收敛于 PageStateStore.kline 单一对象（stockInfo 个股行情 + klineInfo 周期/数据/来源 两键），
 * 刷新后由该对象恢复；股票代码与搜索框展示标签均从恢复的 stockInfo 派生，不额外持久化。
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Switch, AnimCard } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { StockSearch } from '@components/StockSearch/StockSearch';
import { KLineChart } from '@components/kline/KLineChart';
import { StockInfoHeader } from '@components/kline/StockInfoHeader';
import { PeriodSelector } from '@components/kline/PeriodSelector';
import { useSearchParams } from 'react-router-dom';

import { klineApi, toStockSnapshot, type KLinePeriod } from '../../../api/kline';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useStockIndex } from '../../../hooks/useStockIndex';
import { usePageState } from '../../../stores/PageStateStore';
import type { StockIndexItem } from '../../../types/stockIndex';
import type { StockQuoteCore } from '../../../types/stock';

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
  if (hit) return hit.nameZh ? `${hit.nameZh}（${hit.canonicalCode}）` : hit.canonicalCode;
  return stockInfo.name ? `${stockInfo.name}（${stockInfo.code || code}）` : code;
}

/** 判断是否为纯数字股票代码（可带市场后缀，如 600519.SH） */
function isNumericCode(value: string): boolean {
  return /^\d{4,7}$/.test(value.split('.')[0].trim());
}

const StockKLinePage: React.FC = () => {
  const { t } = useUiLanguage();
  const { state: pageState, setState: setPageState } = usePageState();
  const [searchParams] = useSearchParams();
  const { index: stockIndex } = useStockIndex();

  // 当前股票代码：仅内存态，刷新后从已恢复的 pageState.kline.stockInfo.code 派生
  // 取舍：上次加载失败（stockInfo 为 null）时，刷新后代码为空、不再自动重试
  const [stockCode, setStockCode] = useState(() => pageState.kline.stockInfo?.code ?? '');
  // 全量数据开关：开启时按 FULL_DATA_LIMIT 拉取
  const [allDataEnabled, setAllDataEnabled] = useState(false);
  // 行情/K 线加载状态与错误
  const [isStockDataLoading, setIsStockDataLoading] = useState(false);
  const [stockLoadError, setStockLoadError] = useState<string | null>(null);
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

  // 以下 ref 保存最新值，规避回调/闭包捕获旧值
  const latestPeriodRef = useRef(period);
  latestPeriodRef.current = period;
  const latestStockCodeRef = useRef(stockCode);
  latestStockCodeRef.current = stockCode;
  const allDataEnabledRef = useRef(allDataEnabled);
  allDataEnabledRef.current = allDataEnabled;
  // 已加载的股票代码，用于换股去重（避免 PageStateStore 残留旧数据导致不刷新）
  const loadedStockCodeRef = useRef<string | null>(null);
  // 整体加载请求序号：递增使过期结果作废
  const fetchRequestSeqRef = useRef(0);
  // 历史分页：并发锁 + 请求序号（换股/换周期时作废进行中的分页）
  const historyFetchLockRef = useRef(false);
  const historyRequestSeqRef = useRef(0);

  /** 加载指定股票的行情与 K 线数据 */
  const loadStockData = useCallback(
    async (code: string, targetPeriod: KLinePeriod, limit?: number) => {
      if (!code) return;
      loadedStockCodeRef.current = code;
      const requestId = ++fetchRequestSeqRef.current;
      historyRequestSeqRef.current++; // 整体数据即将替换，作废进行中的分页
      setIsStockDataLoading(true);
      setStockLoadError(null);
      try {
        const [info, kline] = await Promise.all([
          klineApi.fetchStockInfo(code),
          klineApi.fetchKLine(code, targetPeriod, limit),
        ]);
        if (requestId !== fetchRequestSeqRef.current) return; // 已有更新的请求，丢弃本次
        setPageState('kline', (prev) => ({
          ...prev,
          stockInfo: toStockSnapshot(info),
          klineInfo: {
            ...prev.klineInfo,
            period: targetPeriod,
            klineData: kline.data,
            klineSource: kline.source ?? null,
          },
        }));
      } catch (err) {
        if (requestId !== fetchRequestSeqRef.current) return;
        console.error('Failed to load stock data:', err);
        setStockLoadError(t('kline.error'));
      } finally {
        if (requestId === fetchRequestSeqRef.current) setIsStockDataLoading(false);
      }
    },
    [t, setPageState],
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
      const input = rawCode.split('.')[0].trim();
      let resolvedCode = input;
      if (!isNumericCode(input)) {
        // 非纯数字（如中文名）：经后端搜索解析为规范代码
        try {
          const results = await klineApi.searchStocks(input);
          if (!results?.length) {
            setStockLoadError(t('kline.error'));
            return;
          }
          resolvedCode = results[0].code;
        } catch {
          setStockLoadError(t('kline.error'));
          return;
        }
      }
      setStockCode(resolvedCode);
      changePeriod(DEFAULT_PERIOD);
      setAllDataEnabled(false); // 换股重置全量数据开关
      void loadStockData(resolvedCode, DEFAULT_PERIOD);
    },
    [changePeriod, loadStockData, setStockCode, t],
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
    if (historyFetchLockRef.current || klineData.length === 0) return;
    const currentPeriod = latestPeriodRef.current;
    if (MINUTE_PERIODS.includes(currentPeriod) && klineData.length >= MINUTE_KLINE_MAX_LIMIT) return;
    const earliestDate = klineData[0]?.date;
    if (!earliestDate) return;

    historyFetchLockRef.current = true;
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
      historyFetchLockRef.current = false;
    }
  }, [klineData, setPageState]);

  // stockCode 变化（页内搜索 / 外部直达）且尚未加载该代码时，拉取数据
  useEffect(() => {
    if (!stockCode || loadedStockCodeRef.current === stockCode) return;
    void loadStockData(stockCode, latestPeriodRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stockCode]);

  // 外部带 ?stockCode= 直达：写入 stockCode 触发加载，并重置展示标签避免残留上一只股票
  useEffect(() => {
    const code = searchParams.get('stockCode');
    if (!code) return;
    const pure = code.split('.')[0].trim();
    if (!pure || pure === latestStockCodeRef.current) return;
    setSearchDraft(pure);
    setSearchDisplayLabel('');
    setStockCode(pure);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // 搜索框展示标签：始终以当前已加载行情为准，行情或索引变化时重算（索引后到会自动补后缀）
  useEffect(() => {
    if (!stockInfo) return;
    const code = latestStockCodeRef.current;
    if (!code) return;
    setSearchDisplayLabel(buildSearchLabel(stockIndex, stockInfo, code));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stockInfo, stockIndex]);

  return (
    <AppPage>
      <div className="space-y-4">
        {/* 页内股票搜索框（页面标题由顶部 header 展示） */}
        <div className="max-w-md">
          <StockSearch
            value={searchDraft}
            displayValue={searchDisplayLabel || undefined}
            size="xl"
            onChange={setSearchDraft}
            onSubmit={handleSearchSubmit}
            onClear={() => {
              setSearchDraft('');
              setStockCode('');
              setSearchDisplayLabel('');
              setPageState('kline', (prev) => ({
                ...prev,
                stockInfo: null,
                klineInfo: { ...prev.klineInfo, klineData: [], klineSource: null },
              }));
            }}
          />
        </div>

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
                ) : stockLoadError ? (
                  <div className="flex items-center justify-center py-20 text-muted-text">{stockLoadError}</div>
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

        {!stockInfo && !isStockDataLoading && (
          <div className="flex items-center justify-center py-20 text-muted-text">
            {t('kline.noStockSelected')}
          </div>
        )}
      </div>
    </AppPage>
  );
};

export default StockKLinePage;
