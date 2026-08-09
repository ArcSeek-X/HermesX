/**
 * 板块分析页面
 *
 * 功能概览：
 * - 展示 A 股市场板块、个股、ETF、概念四大云图
 * - 顶部展示市场仪表盘（涨跌家数、量能、主要市场指数）
 * - 支持实时模式（每 30 秒自动刷新）和快照模式（查看历史时间点数据）
 * - 支持手动刷新全量数据（云图 + 市场仪表盘）
 * - 点击行业板块可下钻查看成分股详情
 *
 * 页面结构（从上到下）：
 * 1. 页面大标题 + 更新时间 + 手动刷新按钮
 * 2. 市场仪表盘区域（MarketDashboard 组件）
 * 3. TAB 页签切换（板块/个股/ETF/概念）
 * 4. 统计卡片（4 个）
 * 5. 云图卡片（标题栏 + ECharts treemap + 底部图例）
 * 6. 详情视图（点击行业后展示成分股表格）
 */
import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { AppPage, Card, Select } from '../components/common';
import { SectorTreemap } from '../components/sector/SectorTreemap';
import { SectorStockTable } from '../components/sector/SectorStockTable';
import MarketDashboard, { type MarketDashboardHandle } from '../components/sector/MarketDashboard';
import {
  fetchIndustryTree,
  fetchStockCloudMap,
  fetchETFCloudMap,
  fetchConceptCloudMap,
  fetchSectorStocks,
  ETF_PERIOD_LABELS,
  type SectorNode,
  type StockItem,
  type ETFPeriod,
} from '../api/sectorData';
import { useCachedState } from '../hooks/useCachedState';

/** 实时模式下自动刷新间隔：30 秒 */
const REFRESH_INTERVAL_MS = 30_000;

/**
 * 交易时段快照时间点（9:30 ~ 15:00，每 30 分钟一个）
 * 注意：13:00 不在数据源（shidaotec getMapData）的合法快照集合内，
 * 该接口对 13:00 返回 time不合法（下午开盘首分钟无快照），故不列入可选时间点。
 */
const SNAPSHOT_TIMES = [
  '09:30', '10:00', '10:30', '11:00', '11:30',
  '13:30', '14:00', '14:30', '15:00',
];

/** 视图模式：概览（云图）/ 详情（成分股表格） */
type ViewMode = 'overview' | 'detail';

/** 当前激活的一级 TAB */
type PrimaryTab = 'cloud-map' | 'sector-fund';

/** 当前激活的二级 TAB（云图） */
type ActiveTab = 'sector' | 'stock' | 'etf' | 'concept';

/** 当前激活的二级 TAB（板块资金） */
type FundTab = 'a' | 'b' | 'c';

/** ETF 云图可选的涨跌幅周期（全部 8 个周期） */
const ETF_PERIODS: ETFPeriod[] = ['yesterday', 'week', 'month', 'quarter', 'half_year', 'ytd', 'year', 'three_year'];

/** 概念云图可选的涨跌幅周期（外部 API 仅支持前 6 个周期，不支持 ytd/year/three_year） */
const CONCEPT_PERIODS: ETFPeriod[] = ['yesterday', 'week', 'month', 'quarter', 'half_year'];

const SectorAnalysisPage: React.FC = () => {
  // ===== 页面状态 =====
  // L2 + L4 缓存：活跃一级 Tab
  const [primaryTab, setPrimaryTab] = useCachedState<PrimaryTab>(
    'sector.primaryTab',
    'cloud-map',
    { storage: 'local' }
  );
  // L2 + L4 缓存：活跃二级 Tab（云图）
  const [activeTab, setActiveTab] = useCachedState<ActiveTab>(
    'sector.activeTab',
    'sector',
    { storage: 'local' }
  );
  // L2 + L4 缓存：活跃二级 Tab（板块资金）
  const [activeFundTab, setActiveFundTab] = useCachedState<FundTab>(
    'sector.activeFundTab',
    'a',
    { storage: 'local' }
  );
  const [viewMode, setViewMode] = useState<ViewMode>('overview');
  const [treemapData, setTreemapData] = useState<SectorNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  // L2 + L3 缓存：快照时间（PageStateStore + sessionStorage，刷新页面后恢复）
  const [selectedTime, setSelectedTime] = useCachedState<string>(
    'sector.selectedTime',
    '',
    { storage: 'session' }
  );
  // L4 缓存：ETF/概念周期（localStorage 永久保存用户偏好）
  const [etfPeriod, setEtfPeriod] = useCachedState<ETFPeriod>(
    'sector.etfPeriod',
    'yesterday',
    { storage: 'local' }
  );
  const [conceptPeriod, setConceptPeriod] = useCachedState<ETFPeriod>(
    'sector.conceptPeriod',
    'yesterday',
    { storage: 'local' }
  );
  const [countdown, setCountdown] = useState(30); // 自动刷新倒计时（秒）
  const [refreshBtnActive, setRefreshBtnActive] = useState(false); // 手动刷新按钮点击态
  // 个股云图加载错误提示（如请求到数据源无快照的时间点）
  const [stockError, setStockError] = useState<string | null>(null);

  // ===== 详情视图状态 =====
  const [selectedSector, setSelectedSector] = useState<{ code: string; name: string } | null>(null);
  const [stocks, setStocks] = useState<StockItem[]>([]);
  const [stocksLoading, setStocksLoading] = useState(false);

  // ===== Refs =====
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  /** 市场仪表盘组件的 ref，用于触发手动全量刷新 */
  const marketDashboardRef = useRef<MarketDashboardHandle>(null);

  // 校验 conceptPeriod 是否为有效周期，若缓存了不支持的周期则重置为默认值
  useEffect(() => {
    if (!CONCEPT_PERIODS.includes(conceptPeriod)) {
      setConceptPeriod('yesterday');
    }
  }, [conceptPeriod, setConceptPeriod]);

  // ===== 数据加载函数 =====

  /** 加载板块云图数据（申万行业分类） */
  const loadTreemapData = useCallback(async (time?: string) => {
    setLoading(true);
    try {
      const result = await fetchIndustryTree(time);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to load sector data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /** 加载个股云图数据（三级树：行业 → 细分行业 → 个股） */
  const loadStockData = useCallback(async (time?: string) => {
    setLoading(true);
    setStockError(null);
    try {
      const result = await fetchStockCloudMap(time);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err: any) {
      console.error('Failed to load stock cloud data:', err);
      // 数据源严谨性：该时间点若无快照，明确提示，不填充其他时间数据
      const detail = err?.response?.data?.detail || '';
      setStockError(
        time
          ? `「${time}」暂无快照数据，请选择其他时间点`
          : '个股云图数据加载失败，请稍后重试'
      );
      void detail;
    } finally {
      setLoading(false);
    }
  }, []);

  /** 加载 ETF 云图数据（按时到量化 API 的 period 参数） */
  const loadETFData = useCallback(async (period?: ETFPeriod) => {
    setLoading(true);
    try {
      const result = await fetchETFCloudMap(period || etfPeriod);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to load ETF cloud data:', err);
    } finally {
      setLoading(false);
    }
  }, [etfPeriod]);

  /** 加载概念云图数据 */
  const loadConceptData = useCallback(async (period?: ETFPeriod) => {
    setLoading(true);
    try {
      const p: ETFPeriod = period || conceptPeriod;
      const result = await fetchConceptCloudMap(p);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to load concept cloud data:', err);
    } finally {
      setLoading(false);
    }
  }, [conceptPeriod]);

  /**
   * 根据当前 TAB 加载对应云图数据
   * ETF 和概念云图使用周期选择器，板块和个股云图使用时间快照选择器
   */
  const loadData = useCallback((time?: string) => {
    if (activeTab === 'sector') {
      loadTreemapData(time);
    } else if (activeTab === 'stock') {
      loadStockData(time);
    } else if (activeTab === 'etf') {
      loadETFData();
    } else {
      loadConceptData();
    }
  }, [activeTab, loadTreemapData, loadStockData, loadETFData, loadConceptData]);

  /**
   * 全量刷新：同时刷新云图数据和市场指数数据
   * 由标题栏右侧的"手动刷新"按钮触发
   * 点击时重置倒计时，并触发按钮 active 动画
   */
  const handleRefreshAll = useCallback(() => {
    // 重置倒计时为 30 秒
    setCountdown(30);
    // 触发按钮 active 动画（200ms 后恢复）
    setRefreshBtnActive(true);
    setTimeout(() => setRefreshBtnActive(false), 200);
    // 执行全量刷新
    loadData(selectedTime || undefined);
    marketDashboardRef.current?.refresh();
  }, [loadData, selectedTime]);

  /** 加载行业成分股（点击板块后下钻） */
  const loadSectorStocks = useCallback(async (sectorCode: string, sectorName: string) => {
    setStocksLoading(true);
    setSelectedSector({ code: sectorCode, name: sectorName });
    setViewMode('detail');
    try {
      const result = await fetchSectorStocks(sectorCode, 'industry');
      setStocks(result.stocks);
    } catch (err) {
      console.error('Failed to load sector stocks:', err);
      setStocks([]);
    } finally {
      setStocksLoading(false);
    }
  }, []);

  // ===== 生命周期 =====

  /** 首次加载 + 实时模式下的 30 秒自动刷新（含倒计时） */
  useEffect(() => {
    loadData(selectedTime || undefined);
    setCountdown(30); // 重置倒计时
    
    if (!selectedTime) {
      // 每秒递减倒计时
      const countdownTimer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            return 30; // 归零后重置
          }
          return prev - 1;
        });
      }, 1000);
      
      // 每 30 秒自动刷新所有数据（云图 + 市场仪表盘）
      timerRef.current = setInterval(() => {
        loadData();
        marketDashboardRef.current?.refresh();
      }, REFRESH_INTERVAL_MS);
      
      return () => {
        clearInterval(countdownTimer);
        if (timerRef.current) clearInterval(timerRef.current);
      };
    }
    
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loadData, selectedTime]);

  // ===== 事件处理 =====

  /** 切换快照时间（实时 ↔ 历史时间点） */
  const handleTimeSelect = useCallback((time: string) => {
    setSelectedTime(time);
    loadData(time || undefined);
  }, [loadData]);

  /** 点击板块节点 → 下钻查看成分股 */
  const handleSectorClick = useCallback((sectorCode: string, sectorName: string) => {
    loadSectorStocks(sectorCode, sectorName);
  }, [loadSectorStocks]);

  /** 从详情视图返回概览 */
  const handleBack = useCallback(() => {
    setViewMode('overview');
    setSelectedSector(null);
    setStocks([]);
  }, []);

  // ===== 辅助函数 =====

  /** 格式化时间为 HH:MM:SS（24 小时制） */
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { hour12: false });
  };

  /**
   * 判断快照时间是否已到达
   * 未到达的时间点按钮应禁用，防止用户查看未来数据
   */
  const isTimeAvailable = (timeStr: string): boolean => {
    const now = new Date();
    const [h, m] = timeStr.split(':').map(Number);
    const snapshotMinutes = h * 60 + m;
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    return currentMinutes >= snapshotMinutes;
  };

  // ===== 统计数据计算 =====

  const firstLevelSectors = treemapData;
  const totalSectors = firstLevelSectors.length;
  const riseCount = firstLevelSectors.filter((s) => s.changePercent > 0).length;
  const fallCount = firstLevelSectors.filter((s) => s.changePercent < 0).length;
  const avgChange =
    totalSectors > 0
      ? firstLevelSectors.reduce((sum, s) => sum + (s.changePercent || 0), 0) / totalSectors
      : 0;

  /** 个股统计：遍历三级树（行业 → 细分行业 → 个股）的叶子节点 */
  const totalStocks = treemapData.reduce((sum, industry) => {
    const subIndustries = industry.children || [];
    return sum + subIndustries.reduce((s, sub) => s + (sub.children?.length || 0), 0);
  }, 0);

  const stockRiseCount = treemapData.reduce((sum, industry) => {
    const subIndustries = industry.children || [];
    return sum + subIndustries.reduce((s, sub) => {
      const stocks = sub.children || [];
      return s + stocks.filter((stock) => stock.changePercent > 0).length;
    }, 0);
  }, 0);

  const stockFallCount = treemapData.reduce((sum, industry) => {
    const subIndustries = industry.children || [];
    return sum + subIndustries.reduce((s, sub) => {
      const stocks = sub.children || [];
      return s + stocks.filter((stock) => stock.changePercent < 0).length;
    }, 0);
  }, 0);

  // ===== 云图标题与副标题（根据当前 TAB 动态生成） =====

  const cloudMapTitle =
    activeTab === 'sector'
      ? '申万行业板块云图'
      : activeTab === 'stock'
        ? 'A 股个股云图'
        : activeTab === 'etf'
          ? 'ETF 云图'
          : '概念云图';

  const cloudMapSubtitle =
    activeTab === 'sector'
      ? `申万行业板块 · 共 ${totalSectors} 个一级行业`
      : activeTab === 'stock'
        ? `A 股全部 · 共 ${totalSectors} 个行业 · ${totalStocks} 只个股`
        : activeTab === 'etf'
          ? `ETF 云图 · 市值前 ${totalSectors} 只 ETF · ${ETF_PERIOD_LABELS[etfPeriod]}`
          : `概念云图 · 市值前 ${totalSectors} 个概念 · ${ETF_PERIOD_LABELS[conceptPeriod]}`;

  // ===== 统计卡片配置（根据当前 TAB 动态生成标签和颜色） =====

  const avgChangeColor =
    avgChange > 0 ? 'stock-up' : avgChange < 0 ? 'stock-down' : 'text-muted-text';
  const avgChangeText = `${avgChange > 0 ? '+' : ''}${Number(avgChange).toFixed(2)}%`;

  const statCards: { label: string; value: string | number; color: string }[] =
    activeTab === 'sector'
      ? [
          { label: '一级行业数', value: totalSectors, color: 'text-foreground' },
          { label: '上涨行业', value: riseCount, color: 'stock-up' },
          { label: '下跌行业', value: fallCount, color: 'stock-down' },
          { label: '平均涨跌幅', value: avgChangeText, color: avgChangeColor },
        ]
      : activeTab === 'stock'
        ? [
            { label: '行业数', value: totalSectors, color: 'text-foreground' },
            { label: '上涨个股', value: stockRiseCount, color: 'stock-up' },
            { label: '下跌个股', value: stockFallCount, color: 'stock-down' },
            { label: '平均涨跌幅', value: avgChangeText, color: avgChangeColor },
          ]
        : activeTab === 'etf'
          ? [
              { label: 'ETF 数量', value: totalSectors, color: 'text-foreground' },
              { label: '上涨 ETF', value: riseCount, color: 'stock-up' },
              { label: '下跌 ETF', value: fallCount, color: 'stock-down' },
              { label: '平均涨跌幅', value: avgChangeText, color: avgChangeColor },
            ]
          : [
              { label: '概念数量', value: totalSectors, color: 'text-foreground' },
              { label: '上涨概念', value: riseCount, color: 'stock-up' },
              { label: '下跌概念', value: fallCount, color: 'stock-down' },
              { label: '平均涨跌幅', value: avgChangeText, color: avgChangeColor },
            ];

  // ===== 涨跌幅图例色块配置 =====
  // 绿色渐变（-4% → -1%，由亮到暗），灰色（0%），红色渐变（+1% → +4%，由暗到亮）
  const LEGEND_COLORS: Record<number, string> = {
    '-4': '#22CC55',
    '-3': '#1AAA44',
    '-2': '#128833',
    '-1': '#0A6622',
    '0': '#777777',
    '1': '#661111',
    '2': '#882222',
    '3': '#AA3333',
    '4': '#CC4444',
  };

  // ===== 渲染 =====
  return (
    <AppPage>
      <div className="space-y-4">
        {/* ===== 1. 页面大标题 + 更新时间 + 手动刷新按钮 ===== */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-foreground tracking-tight">板块分析</h1>
          <div className="flex items-center gap-3">
            {/* 更新时间提示：实时模式显示倒计时，快照模式显示快照时间 */}
            <span className="text-xs text-muted-text">
              {lastUpdate && `更新于 ${formatTime(lastUpdate)}`}
              {!selectedTime && ` · ${countdown}s 后自动刷新`}
              {selectedTime && <span className="text-cyan"> · 快照模式：{selectedTime}</span>}
            </span>
            {/* 手动刷新按钮：触发全量刷新（云图 + 市场指数） */}
            <button
              type="button"
              onClick={handleRefreshAll}
              disabled={loading}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150 ${
                refreshBtnActive
                  ? 'border-cyan/60 bg-cyan/15 text-cyan scale-95'
                  : 'border-subtle text-muted-text hover:text-foreground hover:border-cyan/50'
              } disabled:opacity-50`}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              {loading ? '刷新中...' : '手动刷新'}
            </button>
          </div>
        </div>

        {/* ===== 2. 市场仪表盘（涨跌家数 + 量能 + 指数） ===== */}
        <MarketDashboard ref={marketDashboardRef} />

        {/* ===== 3. 一级 TAB 页签 ===== */}
        <div className="flex gap-1 border-b border-subtle">
          {([
            ['cloud-map', '云图'],
            ['sector-fund', '板块资金'],
          ] as [PrimaryTab, string][]).map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              onClick={() => setPrimaryTab(tab)}
              className={`px-5 py-2.5 text-sm font-semibold transition-colors border-b-2 -mb-px ${
                primaryTab === tab
                  ? 'border-cyan text-cyan'
                  : 'border-transparent text-muted-text hover:text-foreground'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ===== 4. 二级 TAB 页签 ===== */}
        {primaryTab === 'cloud-map' ? (
          <div className="flex gap-1">
            {([
              ['sector', '板块云图'],
              ['stock', '个股云图'],
              ['etf', 'ETF 云图'],
              ['concept', '概念云图'],
            ] as [ActiveTab, string][]).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => { setActiveTab(tab); setViewMode('overview'); }}
                className={`px-4 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  activeTab === tab
                    ? 'bg-cyan/15 text-cyan'
                    : 'text-muted-text hover:text-foreground hover:bg-white/5'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        ) : (
          <div className="flex gap-1">
            {([
              ['a', 'A'],
              ['b', 'B'],
              ['c', 'C'],
            ] as [FundTab, string][]).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveFundTab(tab)}
                className={`px-4 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  activeFundTab === tab
                    ? 'bg-cyan/15 text-cyan'
                    : 'text-muted-text hover:text-foreground hover:bg-white/5'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {/* ===== 板块资金内容 ===== */}
        {primaryTab === 'sector-fund' && (
          <Card variant="bordered" padding="none" className="overflow-hidden">
            <div className="flex items-center justify-center py-24">
              <h2 className="text-3xl font-bold text-foreground">
                {activeFundTab.toUpperCase()}
              </h2>
            </div>
          </Card>
        )}

        {/* ===== 云图内容 ===== */}
        {primaryTab === 'cloud-map' && viewMode === 'overview' && (
          <>
            {/* 统计卡片（4 个） */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {statCards.map((card) => (
                <Card key={card.label} variant="bordered" padding="sm">
                  <div className="text-xs text-muted-text">{card.label}</div>
                  <div className={`text-lg font-semibold mt-1 ${card.color}`}>{card.value}</div>
                </Card>
              ))}
            </div>

            {/* 云图卡片 */}
            <Card variant="bordered" padding="none" className="overflow-hidden">
              {/* 云图标题栏：左侧标题 + 副标题，右侧周期/时间选择器 */}
              <div className="px-4 py-3 border-b border-subtle flex items-center justify-between">
                <div className="flex flex-col gap-0.5">
                  <h2 className="text-sm font-semibold text-foreground">{cloudMapTitle}</h2>
                  <p className="text-xs text-muted-text">{cloudMapSubtitle}</p>
                </div>
                <div className="flex items-center gap-4">
                  {/* ETF 周期选择器（昨日涨跌幅、近一周、近一月等） */}
                  {activeTab === 'etf' && (
                    <Select
                      value={etfPeriod}
                      onChange={(v) => {
                        setEtfPeriod(v as ETFPeriod);
                        loadETFData(v as ETFPeriod);
                      }}
                      options={ETF_PERIODS.map((p) => ({ value: p, label: ETF_PERIOD_LABELS[p] }))}
                      className="w-36"
                    />
                  )}
                  {/* 概念云图周期选择器（仅支持 6 个周期，外部 API 不支持 ytd/year/three_year） */}
                  {activeTab === 'concept' && (
                    <Select
                      value={conceptPeriod}
                      onChange={(v) => {
                        setConceptPeriod(v as ETFPeriod);
                        loadConceptData(v as ETFPeriod);
                      }}
                      options={CONCEPT_PERIODS.map((p) => ({ value: p, label: ETF_PERIOD_LABELS[p] }))}
                      className="w-36"
                    />
                  )}
                  {/* 板块/个股云图：时间快照选择器（实时 + 10 个时间点） */}
                  {(activeTab === 'sector' || activeTab === 'stock') && (
                    <div className="flex items-center gap-1 text-xs">
                      <button
                        type="button"
                        onClick={() => handleTimeSelect('')}
                        className={`px-2 py-1 rounded transition-colors ${
                          !selectedTime
                            ? 'bg-cyan/20 text-cyan font-medium'
                            : 'text-muted-text hover:text-foreground'
                        }`}
                      >
                        实时
                      </button>
                      {SNAPSHOT_TIMES.map((t) => {
                        const available = isTimeAvailable(t);
                        const isSelected = selectedTime === t;
                        return (
                          <button
                            key={t}
                            type="button"
                            disabled={!available}
                            onClick={() => available && handleTimeSelect(t)}
                            className={`px-2 py-1 rounded transition-colors ${
                              isSelected
                                ? 'bg-cyan/20 text-cyan font-medium'
                                : available
                                  ? 'text-muted-text hover:text-foreground'
                                  : 'text-muted-text/30 cursor-not-allowed'
                            }`}
                            title={available ? `${t} 快照` : `${t} 未到`}
                          >
                            {t}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* 云图主体：ECharts treemap */}
              {loading && treemapData.length === 0 ? (
                <div className="flex items-center justify-center py-24">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
                </div>
              ) : (
                <SectorTreemap
                  data={treemapData}
                  onSectorClick={activeTab === 'sector' ? handleSectorClick : undefined}
                  height="650px"
                />
              )}

              {/* 云图底部信息栏：更新时间 + 面积/颜色含义图例 */}
              <div className="px-4 py-2 border-t border-subtle flex items-center justify-between">
                <span className="text-xs text-muted-text">
                  {lastUpdate && `更新于 ${formatTime(lastUpdate)}`}
                  {(activeTab === 'sector' || activeTab === 'stock') && !selectedTime && ' · 每 30 秒自动刷新'}
                  {(activeTab === 'sector' || activeTab === 'stock') && selectedTime && (
                    <span className="text-cyan"> · 快照模式：{selectedTime}</span>
                  )}
                  {activeTab === 'stock' && stockError && (
                    <span className="text-red-400"> · {stockError}</span>
                  )}
                </span>
                <div className="flex items-center gap-4 text-xs text-muted-text">
                  <span>面积 = 流通市值</span>
                  <div className="flex items-center gap-1.5">
                    <span>颜色 = 涨跌幅</span>
                    {/* 涨跌幅色块图例：-4% ~ +4%，红涨绿跌 */}
                    <span className="inline-flex items-center gap-0.5">
                      {['-4%', '-3%', '-2%', '-1%', '0%', '+1%', '+2%', '+3%', '+4%'].map((label) => {
                        const val = parseInt(label);
                        const bg = LEGEND_COLORS[val] || '#555555';
                        return (
                          <span
                            key={label}
                            className="inline-block h-4 w-7 rounded-sm text-[9px] text-white leading-4 text-center font-medium"
                            style={{ backgroundColor: bg }}
                          >
                            {label}
                          </span>
                        );
                      })}
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          </>
        )}

        {/* ===== 详情视图：点击行业后展示成分股表格 ===== */}
        {primaryTab === 'cloud-map' && viewMode === 'detail' && selectedSector && (
          <SectorStockTable
            sectorName={`${selectedSector.name}（行业板块）`}
            stocks={stocks}
            loading={stocksLoading}
            onBack={handleBack}
          />
        )}
      </div>
    </AppPage>
  );
};

export default SectorAnalysisPage;
