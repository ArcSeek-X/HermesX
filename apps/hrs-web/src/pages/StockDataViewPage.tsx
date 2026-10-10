/**
 * @file StockDataViewPage.tsx
 * @description 股票数据视图页面：搜索个股并查看其行情 K 线与基础数据。
 * 作为「K 线」之外的独立数据视图入口，复用既有 kline 组件与 API，拥有独立的状态键。
 * @module pages
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Select } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { StockSearch } from '@components/StockSearch/StockSearch';
import { KLineChart } from '@components/kline/KLineChart';
import { StockInfoHeader } from '@components/kline/StockInfoHeader';
import { PeriodSelector } from '@components/kline/PeriodSelector';
import { klineApi, type KLineAdjustment, type KLinePeriod } from '../api/kline';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { useCachedState } from '../hooks/useCachedState';
import type { UiTextKey } from '../i18n/uiText';
import { usePageState } from '../stores/PageStateStore';

/** 默认周期：日 K */
const DEFAULT_PERIOD: KLinePeriod = 'daily';
/** 单次加载条数 */
const DEFAULT_LIMIT = 500;

/** 将复权模式映射为后端 fqt 参数 */
const adjustmentToFqt = (value: KLineAdjustment): number => {
  switch (value) {
    case 'none':
      return 0;
    case 'hfq':
      return 2;
    case 'qfq':
    default:
      return 1;
  }
};

/** 从输入框文本提取纯股票代码（兼容"名称（规范代码）"与带市场前缀格式） */
const extractStockCode = (raw: string): string => {
  const trimmed = raw.trim();
  const match = trimmed.match(/.*[（](.+?)[）]$/);
  if (match) return match[1].trim();
  return trimmed.split('.').pop() || trimmed;
};

/**
 * 股票数据视图页面。
 * - 提供股票搜索（代码/名称/拼音/简拼 + 自动补全）
 * - 展示选中股票的基础信息头
 * - 渲染多周期 K 线图，支持周期与复权切换
 * 状态键独立（stockDataView.*），不与 K 线页共享缓存。
 */
const StockDataViewPage: React.FC = () => {
  const { t } = useUiLanguage();
  const { state: pageState, setState: setPageState } = usePageState();

  // 股票代码：session 持久化，刷新页面后恢复
  const [stockCode, setStockCode] = useCachedState<string>(
    'stockDataView.stockCode',
    '',
    { storage: 'session' },
  );
  // 默认周期：local 永久保存
  const [period, setPeriod] = useCachedState<KLinePeriod>(
    'stockDataView.period',
    DEFAULT_PERIOD,
    { storage: 'local' },
  );
  const [adjustment, setAdjustment] = useCachedState<KLineAdjustment>(
    'stockDataView.adjustment',
    'qfq',
    { storage: 'local' },
  );

  const periodRef = useRef(period);
  const stockCodeRef = useRef(stockCode);
  const adjustmentRef = useRef(adjustment);

  const stockInfo = pageState.kline.stockInfo;
  const klineData = pageState.kline.klineData;
  const prevClose = pageState.kline.prevClose;
  const klineSource = pageState.kline.klineSource;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 初始化展示标签（返回本页时恢复上次展示）
  const [cachedDisplayValue, setCachedDisplayValue] = useState(() => {
    try {
      const stored = sessionStorage.getItem('hrs-state-stockDataView.displayValue');
      return stored ? JSON.parse(stored) : '';
    } catch {
      return '';
    }
  });

  const autoLoadedRef = useRef(false);
  const loadRequestRef = useRef(0);

  useEffect(() => { periodRef.current = period; }, [period]);
  useEffect(() => { stockCodeRef.current = stockCode; }, [stockCode]);
  useEffect(() => { adjustmentRef.current = adjustment; }, [adjustment]);
  useEffect(() => {
    document.title = t('layout.nav.stockDataView.title');
  }, [t]);

  const loadStockData = useCallback(async (code: string, p: KLinePeriod) => {
    if (!code) return;
    const requestId = ++loadRequestRef.current;
    setLoading(true);
    setError(null);
    try {
      const [info, kline] = await Promise.all([
        klineApi.fetchStockInfo(code),
        klineApi.fetchKLine(
          code,
          p,
          DEFAULT_LIMIT,
          null,
          adjustmentToFqt(adjustmentRef.current),
        ),
      ]);
      if (requestId !== loadRequestRef.current) return;
      setPageState('kline', (prev) => ({
        ...prev,
        stockCode: code,
        stockInfo: info,
        klineData: kline.data,
        prevClose: kline.prev_close ?? null,
        klineSource: kline.source ?? null,
      }));
    } catch (err) {
      if (requestId !== loadRequestRef.current) return;
      console.error('Failed to load stock data:', err);
      setError(t('kline.error'));
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false);
    }
  }, [t, setPageState]);

  const isStockCode = useCallback((value: string): boolean => {
    const pure = value.split('.')[0].trim();
    return /^\d{4,7}$/.test(pure);
  }, []);

  const handleSearchSubmit = useCallback(
    async (
      code: string,
      _name?: string,
      _source?: 'manual' | 'autocomplete',
      metadata?: { market?: unknown; displayCode?: string; displayLabel?: string },
    ) => {
      const pureCode = code.split('.')[0].trim();
      autoLoadedRef.current = false;
      if (metadata?.displayLabel) {
        setCachedDisplayValue(metadata.displayLabel);
        try {
          sessionStorage.setItem(
            'hrs-state-stockDataView.displayValue',
            JSON.stringify(metadata.displayLabel),
          );
        } catch { /* ignore */ }
      }
      if (!isStockCode(pureCode)) {
        try {
          const results = await klineApi.searchStocks(pureCode);
          if (results && results.length > 0) {
            const resolved = results[0].code;
            setStockCode(resolved);
            void loadStockData(resolved, periodRef.current);
          } else {
            setError(t('kline.error'));
          }
        } catch {
          setError(t('kline.error'));
        }
        return;
      }
      setStockCode(pureCode);
      void loadStockData(pureCode, periodRef.current);
    },
    [loadStockData, setStockCode, setCachedDisplayValue, isStockCode, t],
  );

  const handlePeriodChange = useCallback((newPeriod: KLinePeriod) => {
    setPeriod(newPeriod);
    if (stockCodeRef.current) void loadStockData(stockCodeRef.current, newPeriod);
  }, [loadStockData, setPeriod]);

  const handleAdjustmentChange = useCallback((value: string) => {
    const next: KLineAdjustment = value === 'none' || value === 'hfq' ? value : 'qfq';
    setAdjustment(next);
    if (stockCodeRef.current) void loadStockData(stockCodeRef.current, periodRef.current);
  }, [loadStockData, setAdjustment]);

  useEffect(() => {
    if (stockCode && !autoLoadedRef.current && !stockInfo) {
      autoLoadedRef.current = true;
      void loadStockData(stockCode, periodRef.current);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const adjustmentOptions = [
    { value: 'none', label: t('stockData.adjustment.none' as UiTextKey) },
    { value: 'qfq', label: t('stockData.adjustment.qfq' as UiTextKey) },
    { value: 'hfq', label: t('stockData.adjustment.hfq' as UiTextKey) },
  ];

  const sourceLabelKey = (source?: string | null): UiTextKey => {
    switch ((source || '').toLowerCase()) {
      case 'local': return 'kline.source.local' as UiTextKey;
      case 'sina': return 'kline.source.sina' as UiTextKey;
      case 'eastmoney': return 'kline.source.eastmoney' as UiTextKey;
      case 'tencent': return 'kline.source.tencent' as UiTextKey;
      case 'stocksdk': return 'kline.source.stocksdk' as UiTextKey;
      default: return 'kline.source.unknown' as UiTextKey;
    }
  };

  return (
    <AppPage>
      <div className="space-y-4">
        <div className="p-5 rounded-lg bg-card min-h-0">
          <h1 className="text-xl font-semibold text-foreground">
            {t('layout.nav.stockDataView.title')}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-text">
            {t('layout.nav.stockDataView.description')}
          </p>
          <div className="mt-4 max-w-md">
            <StockSearch
              value={stockCode}
              displayValue={cachedDisplayValue || undefined}
              size="xl"
              onChange={(raw: string) => setStockCode(extractStockCode(raw))}
              onSubmit={handleSearchSubmit}
              onClear={() => {
                setStockCode('');
                setCachedDisplayValue('');
                try {
                  sessionStorage.removeItem('hrs-state-stockDataView.displayValue');
                } catch { /* ignore */ }
                setPageState('kline', (prev) => ({
                  ...prev,
                  stockCode: '',
                  stockInfo: null,
                  klineData: [],
                  klineSource: null,
                }));
              }}
            />
          </div>
        </div>

        {stockInfo && (
          <div className="space-y-4">
            <div className="p-5 rounded-lg bg-card min-h-0">
              <StockInfoHeader info={stockInfo} />
            </div>

            <div className="p-5 rounded-lg bg-card min-h-0">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-text">
                  <span className="rounded-full bg-default-100 px-3 py-1">
                    {t('kline.meta.source')}: {t(sourceLabelKey(klineSource))}
                  </span>
                  <span className="rounded-full bg-default-100 px-3 py-1">
                    {t('kline.meta.rows')}: {klineData.length}
                  </span>
                </div>
                <div className="w-40">
                  <Select
                    label={t('stockData.adjustment.label')}
                    value={adjustment}
                    onChange={handleAdjustmentChange}
                    options={adjustmentOptions}
                  />
                </div>
              </div>

              <div className="mt-4">
                {loading ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
                  </div>
                ) : error ? (
                  <div className="flex items-center justify-center py-20 text-muted-text">
                    {error}
                  </div>
                ) : klineData.length === 0 ? (
                  <div className="flex items-center justify-center py-20 text-muted-text">
                    {t('kline.empty')}
                  </div>
                ) : (
                  <KLineChart
                    data={klineData}
                    period={period}
                    height="500px"
                    prevClose={prevClose}
                    stockCode={stockCode}
                  />
                )}
              </div>

              <div className="mt-4 flex items-center justify-end">
                <PeriodSelector period={period} onChange={handlePeriodChange} />
              </div>
            </div>
          </div>
        )}

        {!stockInfo && !loading && (
          <div className="flex items-center justify-center py-20 text-muted-text">
            {t('kline.noStockSelected')}
          </div>
        )}
      </div>
    </AppPage>
  );
};

export default StockDataViewPage;
