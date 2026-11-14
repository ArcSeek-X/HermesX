/**
 * 个股 K 线面板：按股票代码自行加载行情与 K 线，并管理周期 / 全量 / 左滑交互。
 * 页面只给出当前股票；首次加载成功时回报行情，供页面维护最近搜索。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Switch, AnimCard } from '@components';
import { KLineChart } from '@components/kline/KLineChart';
import { StockInfoHeader } from '@components/kline/StockInfoHeader';
import { PeriodSelector } from '@components/kline/PeriodSelector';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { klineApi, type KLinePeriod, type KLinePoint, type StockInfo } from '../../../../api/kline';
import { getStockKLineInfo, updateStockKLineInfo } from '../../../../stores/StockKLine';

const DEFAULT_PERIOD: KLinePeriod = '1m';
const FULL_DATA_LIMIT = 10000;
const HISTORY_PAGE_SIZE = 250;
/** 分钟线分页上限，超出后停止左滑加载，避免 ECharts 卡顿 */
const MINUTE_KLINE_MAX_LIMIT = 5000;
const MINUTE_PERIODS: KLinePeriod[] = ['5m', '15m', '30m', '60m', '120m'];
const FULL_DATA_PERIODS: KLinePeriod[] = ['5d', 'daily', 'weekly'];

export interface StockKLineChartPanelProps {
  /** 当前选中的纯股票代码 */
  stockCode: string;
  /** 首次加载成功时回报行情；切周期 / 全量 / 左滑不触发 */
  onStockQuoteLoaded?: (stockQuote: StockInfo) => void;
}

function StockKLineChartPanel({ stockCode, onStockQuoteLoaded }: StockKLineChartPanelProps) {
  const { t } = useUiLanguage();
  const [stockQuote, setStockQuote] = useState<StockInfo | null>(null);
  const [klinePoints, setKlinePoints] = useState<KLinePoint[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<KLinePeriod>(DEFAULT_PERIOD);
  const [isFullDataEnabled, setIsFullDataEnabled] = useState(false);
  const [isKLineLoading, setIsKLineLoading] = useState(true);
  const [klineLoadError, setKlineLoadError] = useState<string | null>(null);

  const latestKLinePeriodRef = useRef(selectedPeriod);
  const latestFullDataEnabledRef = useRef(isFullDataEnabled);
  const stockDataRequestSeqRef = useRef(0);
  const historyRequestSeqRef = useRef(0);
  const isEarlierDataLoadingRef = useRef(false);
  const hasReportedStockQuoteRef = useRef(false);
  const isMountedRef = useRef(true);

  const loadStockView = useCallback(
    async (targetPeriod: KLinePeriod, limit?: number) => {
      if (!isMountedRef.current) return;
      const requestId = ++stockDataRequestSeqRef.current;
      historyRequestSeqRef.current++; // 整体数据即将替换，作废进行中的分页
      setIsKLineLoading(true);
      setKlineLoadError(null);
      try {
        const [quote, klineResult] = await Promise.all([
          klineApi.fetchStockInfo(stockCode),
          klineApi.fetchKLine(stockCode, targetPeriod, limit),
        ]);
        if (requestId !== stockDataRequestSeqRef.current) return;
        setStockQuote(quote);
        setKlinePoints(klineResult.data);
        // 外部入口注入时 name 可能为空，行情返回后以接口名称修正持久化值
        const persisted = getStockKLineInfo();
        if (persisted?.code === stockCode && quote.name && persisted.name !== quote.name) {
          updateStockKLineInfo({ name: quote.name });
        }
        if (!hasReportedStockQuoteRef.current) {
          hasReportedStockQuoteRef.current = true;
          onStockQuoteLoaded?.(quote);
        }
      } catch (error) {
        if (requestId !== stockDataRequestSeqRef.current) return;
        console.error('Failed to load stock data:', error);
        setKlineLoadError(t('kline.error'));
      } finally {
        if (requestId === stockDataRequestSeqRef.current) setIsKLineLoading(false);
      }
    },
    [stockCode, onStockQuoteLoaded, t],
  );

  // 组件按「一次选股」实例化（页面用 key 控制），挂载时异步加载一次即可
  useEffect(() => {
    queueMicrotask(() => void loadStockView(DEFAULT_PERIOD));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 卸载时作废在途请求，避免清空股票后旧结果写回或触发落库
  useEffect(
    () => () => {
      isMountedRef.current = false;
      stockDataRequestSeqRef.current++;
      historyRequestSeqRef.current++;
    },
    [],
  );

  const handlePeriodChange = useCallback(
    (nextPeriod: KLinePeriod) => {
      setSelectedPeriod(nextPeriod);
      latestKLinePeriodRef.current = nextPeriod;
      const limit = latestFullDataEnabledRef.current ? FULL_DATA_LIMIT : undefined;
      void loadStockView(nextPeriod, limit);
    },
    [loadStockView],
  );

  const handleFullDataToggle = useCallback(
    (enabled: boolean) => {
      setIsFullDataEnabled(enabled);
      latestFullDataEnabledRef.current = enabled;
      const limit = enabled ? FULL_DATA_LIMIT : undefined;
      void loadStockView(latestKLinePeriodRef.current, limit);
    },
    [loadStockView],
  );

  /** 左滑加载更早历史：按最早日期前置拼接并去重，防止并发与重复 */
  const loadEarlierKLinePoints = useCallback(async () => {
    if (isEarlierDataLoadingRef.current || klinePoints.length === 0) return;
    const currentPeriod = latestKLinePeriodRef.current;
    if (MINUTE_PERIODS.includes(currentPeriod) && klinePoints.length >= MINUTE_KLINE_MAX_LIMIT) return;
    const earliestDate = klinePoints[0]?.date;
    if (!earliestDate) return;

    isEarlierDataLoadingRef.current = true;
    const requestId = ++historyRequestSeqRef.current;
    try {
      const earlier = await klineApi.fetchKLine(
        stockCode,
        currentPeriod,
        HISTORY_PAGE_SIZE,
        earliestDate,
      );
      if (requestId !== historyRequestSeqRef.current) return;
      if (earlier?.data?.length) {
        setKlinePoints((currentPoints) => {
          const currentEarliest = currentPoints[0]?.date;
          const older = currentEarliest
            ? earlier.data.filter((point) => point.date < currentEarliest)
            : earlier.data;
          if (!older.length) return currentPoints;
          return [...older, ...currentPoints];
        });
      }
    } catch (error) {
      console.error('Failed to load more history:', error);
    } finally {
      isEarlierDataLoadingRef.current = false;
    }
  }, [klinePoints, stockCode]);

  return (
    <>
      {stockQuote && (
        <AnimCard className="p-5 min-h-0">
          <StockInfoHeader info={stockQuote} />
        </AnimCard>
      )}

      <AnimCard className="p-5 min-h-0">
        <div className="w-full space-y-3">
          {isKLineLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
            </div>
          ) : klineLoadError ? (
            <div className="flex items-center justify-center py-20 text-muted-text">{klineLoadError}</div>
          ) : klinePoints.length === 0 ? (
            <div className="flex items-center justify-center py-20 text-muted-text">暂无 K 线数据</div>
          ) : (
            <KLineChart
              data={klinePoints}
              period={selectedPeriod}
              height="500px"
              prevClose={stockQuote?.prevClose ?? null}
              stockCode={stockCode}
              showAllData={isFullDataEnabled}
              onDataZoomBoundary={isFullDataEnabled ? undefined : loadEarlierKLinePoints}
            />
          )}

          <div className="flex items-center justify-between">
            {FULL_DATA_PERIODS.includes(selectedPeriod) && (
              <Switch
                checked={isFullDataEnabled}
                onChange={handleFullDataToggle}
                label={t('kline.fullData')}
                className="whitespace-nowrap text-muted-text"
              />
            )}
            <PeriodSelector period={selectedPeriod} onChange={handlePeriodChange} />
          </div>
        </div>
      </AnimCard>
    </>
  );
}

export default StockKLineChartPanel;
