/**
 * @file StockKLinePage.tsx
 * @description 个股 K 线页面，提供股票搜索、基本信息展示和多周期 K 线图浏览功能
 * @module pages
 *
 * 功能：
 * 1. 搜索框：支持代码/名称/拼音/简拼搜索 + 自动补全
 * 2. 股票信息头部：显示名称、价格、涨跌幅、关键指标
 * 3. K 线图 + 周期选择器：多周期 K 线展示
 *
 * 缓存策略：
 * - stockCode: L2 + L3（sessionStorage），切换路由和刷新页面后恢复
 * - period: L4（localStorage），永久保存用户偏好
 * - stockInfo/klineData: L2（PageStateStore），切换路由不丢失
 * - API 请求: L1（apiCache），TTL 内自动去重
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AppPage, Switch } from '../components';
import AnimCard from '../components/common/Card/AnimCard';
import { StockSearch } from '../components/StockSearch/StockSearch';
import { KLineChart } from '../components/kline/KLineChart';
import { StockInfoHeader } from '../components/kline/StockInfoHeader';
import { PeriodSelector } from '../components/kline/PeriodSelector';
import { klineApi, type KLinePeriod } from '../api/kline';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { useCachedState } from '../hooks/useCachedState';
import { usePageState } from '../stores/PageStateStore';
import type { Market } from '../types/market';

/**
 * 个股 K 线页面组件
 *
 * 职责：
 * - 提供股票搜索（支持代码/名称/拼音/简拼）和自动补全
 * - 展示选中股票的基本信息（名称、价格、涨跌幅等）
 * - 渲染多周期 K 线图，支持周期切换、全量数据加载和左滑加载历史
 *
 * 缓存层级：
 * - stockCode: sessionStorage 持久化，刷新页面后恢复
 * - period: localStorage 永久保存用户偏好
 * - stockInfo/klineData: PageStateStore，切换路由不丢失
 */
const StockKLinePage: React.FC = () => {
  const { t } = useUiLanguage();
  const { state: pageState, setState: setPageState } = usePageState();

  /**
   * 从输入框文本提取纯股票代码：
   * - "中科曙光（603019.SH）" → "603019.SH"（去掉名称与全角括号）
   * - 其余情况原样返回（兼容带市场前缀如 SH.603019）
   */
  const extractStockCode = useCallback((raw: string): string => {
    const trimmed = raw.trim();
    const match = trimmed.match(/.*[（](.+?)[）]$/);
    if (match) return match[1].trim();
    return trimmed.split('.').pop() || trimmed;
  }, []);

  // L2 + L3 缓存：股票代码（sessionStorage 持久化，刷新页面后恢复）
  const [stockCode, setStockCode] = useCachedState<string>(
    'kline.stockCode',
    '',
    { storage: 'session' }
  );

  // L4 缓存：默认周期（localStorage 永久保存用户偏好）
  // 默认值为 '1m'（分时），用户搜索时优先使用分时图
  const [period, setPeriod] = useCachedState<KLinePeriod>(
    'kline.period',
    '1m',
    { storage: 'local' }
  );

  // 用 ref 保存最新 period，解决闭包捕获旧值的问题
  const periodRef = useRef(period);
  periodRef.current = period;

  // 用 ref 保存最新 stockCode，解决闭包捕获旧值的问题
  const stockCodeRef = useRef(stockCode);
  stockCodeRef.current = stockCode;

  // L2 缓存：股票信息和 K 线数据（PageStateStore，切换路由不丢失）
  const stockInfo = pageState.kline.stockInfo;
  const klineData = pageState.kline.klineData;
  const prevClose = pageState.kline.prevClose;

  // 输入框展示标签：由 StockSearch 组件统一产出（"名称（规范代码）"，如"中科曙光（603019.SH）"），
  // 本页只负责缓存与回传，不自行拼接格式（遵守组件规范）。
  // 用途仅为初始化显示 / 返回本页时恢复上次展示。
  const [cachedDisplayValue, setCachedDisplayValue] = useState(() => {
    try {
      const stored = sessionStorage.getItem('hrs-state-kline.displayValue');
      return stored ? JSON.parse(stored) : '';
    } catch {
      return '';
    }
  });

  const [loading, setLoading] = useState(false); // 股票数据加载中状态
  const [error, setError] = useState<string | null>(null); // 数据加载错误信息
  const [showSwitch, setShowSwitch] = useState(false); // 全量数据开关状态（开启时拉取 limit=10000）

  // 分钟线最大加载上限（避免 ECharts 卡顿）
  const MINUTE_KLINE_MAX_LIMIT = 5000;

  // 防止自动加载时重复触发
  const autoLoadedRef = useRef(false);
  // 用于取消过期的请求（避免快速切换周期时旧请求覆盖新状态）
  const loadRequestRef = useRef(0);
  // 分页加载同步锁：useState 更新是异步的，拖动滑块连续触发 dataZoom 事件时
  // 必须用 ref 同步判定，否则同一页会被并发请求并重复前置拼接（K线形态重复、时间轴倒退）
  const loadingMoreRef = useRef(false);
  // 分页请求序号：切换股票/周期时递增，使进行中的分页结果作废
  const loadMoreRequestRef = useRef(0);

  // 用 ref 保存最新的 showSwitch，避免闭包捕获旧值
  const showSwitchRef = useRef(showSwitch);
  showSwitchRef.current = showSwitch;

  /** 加载股票数据 */
  const loadStockData = useCallback(async (code: string, p: KLinePeriod, limit?: number) => {
    if (!code) return;
    const requestId = ++loadRequestRef.current;
    // 整体数据即将被替换，作废所有进行中的分页加载请求
    loadMoreRequestRef.current++;
    setLoading(true);
    setError(null);
    try {
      // 并行获取股票信息和 K 线数据（API 缓存自动去重）
      const [info, kline] = await Promise.all([
        klineApi.fetchStockInfo(code),
        klineApi.fetchKLine(code, p, limit),
      ]);

      // 如果已有更新的请求，丢弃本次结果
      if (requestId !== loadRequestRef.current) return;

      // 保存到 PageStateStore（L2 缓存）
      setPageState('kline', (prev) => ({
        ...prev,
        stockCode: code,
        stockInfo: info,
        klineData: kline.data,
        prevClose: kline.prev_close ?? null,
      }));
    } catch (err) {
      // 如果已有更新的请求，忽略本次错误
      if (requestId !== loadRequestRef.current) return;
      console.error('Failed to load stock data:', err);
      setError(t('kline.error'));
    } finally {
      if (requestId === loadRequestRef.current) {
        setLoading(false);
      }
    }
  }, [t, setPageState]);

  /** 判断是否为有效股票代码（纯数字，可能带市场前缀） */
  const isStockCode = useCallback((value: string): boolean => {
    const pure = value.split('.')[0].trim();
    return /^\d{4,7}$/.test(pure);
  }, []);

  /** 搜索提交回调 */
  const handleSearchSubmit = useCallback(
    async (
      code: string,
      _name?: string,
      _source?: 'manual' | 'autocomplete',
      metadata?: { market?: Market; displayCode?: string; displayLabel?: string },
    ) => {
      const pureCode = code.split('.')[0].trim();
      autoLoadedRef.current = false; // 手动搜索时重置自动加载标记

      // 缓存组件统一产出的展示标签（"名称（规范代码）"），仅用于返回本页时初始化显示
      if (metadata?.displayLabel) {
        setCachedDisplayValue(metadata.displayLabel);
        try {
          sessionStorage.setItem('hrs-state-kline.displayValue', JSON.stringify(metadata.displayLabel));
        } catch { /* ignore */ }
      }

      // 搜索时默认使用分时（1m）
      const searchPeriod: KLinePeriod = '1m';

      // 如果输入不是有效股票代码（如中文名称），先通过后端搜索 API 解析
      if (!isStockCode(pureCode)) {
        try {
          const results = await klineApi.searchStocks(pureCode);
          if (results && results.length > 0) {
            const resolved = results[0].code;
            setStockCode(resolved);
            setPeriod(searchPeriod);
            setShowSwitch(false); // 切换股票时重置全量数据开关
            void loadStockData(resolved, searchPeriod);
          } else {
            setError(t('kline.error'));
          }
        } catch {
          setError(t('kline.error'));
        }
        return;
      }

      // 有效股票代码：使用传入的 name 或清空
      setStockCode(pureCode);
      setPeriod(searchPeriod);
      setShowSwitch(false); // 切换股票时重置全量数据开关
      void loadStockData(pureCode, searchPeriod);
    },
    [
      loadStockData,
      setPeriod,
      setStockCode,
      setCachedDisplayValue,
      isStockCode,
      t,
    ],
  );

  /** 周期切换回调 */
  const handlePeriodChange = useCallback(
    (newPeriod: KLinePeriod) => {
      setPeriod(newPeriod);
      // 使用 ref 获取最新的 stockCode，避免闭包捕获旧值
      if (stockCodeRef.current) {
        // 切换周期时，如果全量数据开关开启，传入 limit=10000
        const limit = showSwitchRef.current ? 10000 : undefined;
        void loadStockData(stockCodeRef.current, newPeriod, limit);
      }
    },
    [loadStockData, setPeriod],
  );

  /** 全量数据开关切换 */
  const handleFullDataToggle = useCallback((checked: boolean) => {
    setShowSwitch(checked);
    console.log('[全量数据开关]', checked ? '开启 → limit=10000' : '关闭 → 使用后端默认值', 'stockCode:', stockCodeRef.current, 'period:', periodRef.current);
    if (stockCodeRef.current) {
      // 开启：传 limit=10000 拉全量；关闭：不传 limit，使用后端周期默认值
      const limit = checked ? 10000 : undefined;
      void loadStockData(stockCodeRef.current, periodRef.current, limit);
    }
  }, [loadStockData]);

  /** 分页加载历史数据（左滑触发） */
  const loadMoreHistory = useCallback(async () => {
    // 同步锁防止重复加载：拖动滑块会连续触发多次 dataZoom 事件，
    // 若不加锁，多个并发请求会以相同 earliestDate 拉取同一页并重复前置，
    // 导致 K 线数据循环重复、时间轴乱序
    if (loadingMoreRef.current || klineData.length === 0) return;

    // 分钟线性能保护：超过上限时停止加载
    const isMinutePeriod = ['5m', '15m', '30m', '60m', '120m'].includes(periodRef.current);
    if (isMinutePeriod && klineData.length >= MINUTE_KLINE_MAX_LIMIT) {
      return;
    }

    const earliestDate = klineData[0]?.date;
    if (!earliestDate) return;

    loadingMoreRef.current = true;
    const requestId = ++loadMoreRequestRef.current;
    try {
      const moreData = await klineApi.fetchKLine(
        stockCodeRef.current,
        periodRef.current,
        250,           // 每次加载250条
        earliestDate,  // beforeDate：返回此日期之前的数据
      );

      // 请求已过期（期间切换了股票/周期或触发了新的整体加载）：丢弃结果
      if (requestId !== loadMoreRequestRef.current) return;

      if (moreData?.data?.length > 0) {
        // 将新数据插入到现有数据前面。
        // 使用函数式更新基于最新状态合并，并过滤掉不早于当前首条的数据，
        // 双重保障避免重复/乱序数据混入
        setPageState('kline', (prev) => {
          const currentEarliest = prev.klineData[0]?.date;
          const older = currentEarliest
            ? moreData.data.filter((item) => item.date < currentEarliest)
            : moreData.data;
          if (older.length === 0) return prev;
          return { ...prev, klineData: [...older, ...prev.klineData] };
        });
      }
    } catch (err) {
      console.error('Failed to load more history:', err);
    } finally {
      loadingMoreRef.current = false;
    }
  }, [klineData, setPageState]);

  /** 组件挂载时：如果有缓存的股票代码，自动加载数据 */
  useEffect(() => {
    if (stockCode && !autoLoadedRef.current && !stockInfo) {
      autoLoadedRef.current = true;
      void loadStockData(stockCode, periodRef.current);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AppPage>
      <div className="space-y-4">
        {/* ===== 搜索框区（页面标题已由顶部 header 展示）===== */}
        <div className="max-w-md">
          <StockSearch
            value={stockCode}
            // 仅用于初始化显示：传入组件统一格式的展示标签（页面不自行拼接）
            displayValue={cachedDisplayValue || undefined}
            size="xl"
            onChange={(raw) => {
              // 编辑时从输入文本提取纯代码并更新（兼容"名称（代码）"展示格式）
              setStockCode(extractStockCode(raw));
            }}
            onSubmit={handleSearchSubmit}
            onClear={() => {
              setStockCode('');
              setCachedDisplayValue('');
              try { sessionStorage.removeItem('hrs-state-kline.displayValue'); } catch { /* ignore */ }
              setPageState('kline', (prev) => ({
                ...prev,
                stockCode: '',
                stockInfo: null,
                klineData: [],
              }));
            }}
          />
        </div>

        {/* ===== 股票信息与 K 线图区（选股后显示）===== */}
        {stockInfo && (
          <>
            {/* 股票信息头部 */}
            <AnimCard className="p-5 min-h-0">
              <StockInfoHeader info={stockInfo} />
            </AnimCard>

            {/* K 线图 + 周期选择器 */}
            <AnimCard className="p-5 min-h-0">
              <div className="space-y-3 w-full">
                {/* K 线图（全宽铺满） */}
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
                    暂无 K 线数据
                  </div>
                ) : (
                  <KLineChart
                    data={klineData}
                    period={period}
                    height="500px"
                    prevClose={prevClose}
                    stockCode={stockCode}
                    showAllData={showSwitch}
                    onDataZoomBoundary={showSwitch ? undefined : loadMoreHistory}
                  />
                )}

                {/* 周期选择器（底部左侧） */}
                <div className="flex items-center justify-between">
                  {/* 仅在 5日K、日K、周K 模式下显示全量数据开关 */}
                  {['5d', 'daily', 'weekly'].includes(period) && (
                    <Switch
                      checked={showSwitch}
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

        {/* ===== 未选股提示区 ===== */}
        {!stockInfo && !loading && (
          <div className="flex items-center justify-center py-20 text-muted-text">
            {t('kline.noStockSelected')}
          </div>
        )}
      </div>
    </AppPage>
  );
};

export default StockKLinePage;
