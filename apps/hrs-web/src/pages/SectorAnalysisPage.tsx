/**
 * ===================================
 * 板块分析页面（SectorAnalysisPage）
 * ===================================
 *
 * 定位：
 * A 股板块综合分析页面的主入口，整合三大功能模块：
 * 1. 板块（sector）：板块卡片列表，展示行业/概念板块的涨跌幅、总市值、
 *    换手率、涨跌家数，支持类型切换和关键词搜索
 * 2. 云图（cloud-map）：四类资产云图可视化（板块/个股/ETF/概念），
 *    基于 ECharts Treemap 展示，支持实时模式（30 秒自动刷新）和快照模式（历史时间点），
 *    点击行业板块可下钻查看成分股详情
 * 3. 资金（sector-fund）：板块资金流向折线图，支持行业/概念板块筛选、
 *    多日周期选择、板块多选，基于 ECharts 多折线图展示
 *
 * 页面结构（从上到下）：
 * 1. 一级 TAB 页签 + 右侧 更新时间 / 手动刷新按钮（同一行布局）
 * 2. 二级 TAB 页签：
 *    - 「板块」下有：行业板块 / 概念板块
 *    - 「云图」下有：板块云图 / 个股云图 / ETF 云图 / 概念云图
 *    （「资金」无二级 TAB）
 * 3. 各 TAB 对应的内容区域
 *
 * 数据刷新策略（本页核心）：
 * - 「手动刷新」按钮与「倒计时归零」共用同一个刷新入口 refreshActiveTabData，
 *   只刷新当前一级 TAB 下的全部数据，不会重新挂载页面。
 * - 实时模式下倒计时归零会自动重新拉取当前 TAB 数据并重置倒计时；快照模式不启动倒计时。
 *
 * 状态管理：
 * - 一级/二级 TAB、快照时间、周期等用户偏好通过 useCachedState 持久化
 * - 云图数据、资金流数据通过 API 函数从后端获取
 */

import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronUp, Check, LayoutGrid, Boxes, TrendingUp, Search } from 'lucide-react';
import { AppPage, Card, DataRefreshBar, Select, TabNav, type TabNavItem } from '../components';
import {
  InputGroup,
} from '@heroui/react';
import { SectorTreemap } from '../components/sector/SectorTreemap';
import { SectorStockTable } from '../components/sector/SectorStockTable';
import { SectorFundFlowChart } from '../components/sector/SectorFundFlowChart';
import { SectorBoardCards, type BoardType } from '../components/sector/SectorBoardCards';
import {
  fetchIndustryTree,
  fetchStockCloudMap,
  fetchETFCloudMap,
  fetchConceptCloudMap,
  fetchSectorStocks,
  fetchSectorFundFlowHistory,
  fetchSectorFundFlowSectorList,
  ETF_PERIOD_LABELS,
  type SectorNode,
  type StockItem,
  type ETFPeriod,
  type SectorFundFlowResponse,
  type SectorFundFlowSectorItem,
} from '../api/sectorData';
import { useCachedState } from '../hooks/useCachedState';
import { apiCache } from '../utils/apiCache';
import { useUiLanguage } from '../contexts/UiLanguageContext';

/**
 * 交易时段快照时间点（9:30 ~ 15:00，每 30 分钟一个）
 * 注意：13:00 不在数据源（shidaotec getMapData）的合法快照集合内，
 * 该接口对 13:00 返回 time 不合法（下午开盘首分钟无快照），故不列入可选时间点。
 */
const SNAPSHOT_TIMES = [
  '09:30', '10:00', '10:30', '11:00', '11:30',
  '13:30', '14:00', '14:30', '15:00',
];

/** 视图模式：overview 概览（云图）/ detail 详情（成分股表格） */
type ViewMode = 'overview' | 'detail';

/** 当前激活的一级 TAB：sector 板块 / cloud-map 云图 / sector-fund 资金 */
type PrimaryTab = 'sector' | 'cloud-map' | 'sector-fund';

/** 当前激活的二级 TAB（仅云图下使用）：sector 板块 / stock 个股 / etf / concept 概念 */
type CloudMapTab = 'sector' | 'stock' | 'etf' | 'concept';

/** ETF 云图可选的涨跌幅周期（全部 8 个周期） */
const ETF_PERIODS: ETFPeriod[] = ['yesterday', 'week', 'month', 'quarter', 'half_year', 'ytd', 'year', 'three_year'];

/** 概念云图可选的涨跌幅周期（外部 API 仅支持前 6 个周期，不支持 ytd/year/three_year） */
const CONCEPT_PERIODS: ETFPeriod[] = ['yesterday', 'week', 'month', 'quarter', 'half_year'];

const SectorAnalysisPage: React.FC = () => {
  // ===================================================================
  // 国际化与 TAB 配置
  // ===================================================================
  /** 界面语言翻译函数（走三语主字典 UI_TEXT，繁体返回真繁体文案） */
  const { t } = useUiLanguage();

  /**
   * 一级 TAB 配置（数组）。图标 + 文字均通过此数据声明。
   * label 从主字典 UI_TEXT 的 sector.tab.* 取值，随界面语言实时切换（中/英/繁）。
   */
  const PRIMARY_TABS = useMemo<TabNavItem<PrimaryTab>[]>(() => [
    { value: 'sector', label: t('sector.tab.board'), icon: <LayoutGrid className="h-4 w-4" /> },
    { value: 'cloud-map', label: t('sector.tab.cloudMap'), icon: <Boxes className="h-4 w-4" /> },
    { value: 'sector-fund', label: t('sector.tab.fund'), icon: <TrendingUp className="h-4 w-4" /> },
  ], [t]);

  /** 「板块」一级 TAB 下的二级 TAB：行业板块 / 概念板块 */
  const SECTOR_TABS = useMemo<TabNavItem<BoardType>[]>(() => [
    { value: 'industry', label: t('sector.tab.boardIndustry') },
    { value: 'concept', label: t('sector.tab.boardConcept') },
  ], [t]);

  /** 「云图」一级 TAB 下的二级 TAB：板块云图 / 个股云图 / ETF 云图 / 概念云图 */
  const CLOUD_MAP_TABS = useMemo<TabNavItem<CloudMapTab>[]>(() => [
    { value: 'sector', label: t('sector.tab.cloudSector') },
    { value: 'stock', label: t('sector.tab.cloudStock') },
    { value: 'etf', label: t('sector.tab.cloudEtf') },
    { value: 'concept', label: t('sector.tab.cloudConcept') },
  ], [t]);
  // ===================================================================
  // 状态定义
  // ===================================================================

  /** 当前激活的一级 TAB（L2+L4 缓存：localStorage 持久化用户偏好） */
  const [primaryTabValue, setPrimaryTab] = useCachedState<PrimaryTab>(
    'sector.primaryTabValue',
    'sector',
    { storage: 'local' }
  );

  /** 当前激活的云图二级 TAB（仅「云图」一级 TAB 下使用，L2+L4 缓存） */
  const [cloudMapTab, setCloudMapTab] = useCachedState<CloudMapTab>(
    'sector.activeTab',
    'sector',
    { storage: 'local' }
  );

  /** 当前激活的「板块」二级 TAB：industry 行业 / concept 概念（L4 缓存） */
  const [boardTab, setBoardTab] = useCachedState<BoardType>(
    'sector.boardTab',
    'industry',
    { storage: 'local' }
  );

  /** 「板块」一级 TAB 下的搜索关键词（不持久化，会话内有效） */
  const [boardSearchKeyword, setBoardSearchKeyword] = useState('');

  /** 当前视图模式：overview 概览（云图）/ detail 详情（成分股表格） */
  const [viewMode, setViewMode] = useState<ViewMode>('overview');

  /** 云图 Treemap 数据（四类云图共用同一份数据状态） */
  const [treemapData, setTreemapData] = useState<SectorNode[]>([]);
  /** 云图数据加载状态 */
  const [loading, setLoading] = useState(false);
  /** 最后一次数据更新时间
   * 初始值取当前时间，保证「板块」TAB 等无独立加载入口的场景在进入页面时即显示「更新于」；
   * 实际数据加载完成后会被各 load 函数覆盖为接口返回时间。 */
  const [lastUpdate, setLastUpdate] = useState<Date>(() => new Date());

  /** 选中的快照时间（L2+L3 缓存：sessionStorage；空字符串表示实时模式） */
  const [selectedTime, setSelectedTime] = useCachedState<string>(
    'sector.selectedTime',
    '',
    { storage: 'session' }
  );

  /** ETF 云图涨跌幅周期（L4 缓存：localStorage 永久保存） */
  const [etfPeriod, setEtfPeriod] = useCachedState<ETFPeriod>(
    'sector.etfPeriod',
    'yesterday',
    { storage: 'local' }
  );
  /** 概念云图涨跌幅周期（L4 缓存） */
  const [conceptPeriod, setConceptPeriod] = useCachedState<ETFPeriod>(
    'sector.conceptPeriod',
    'yesterday',
    { storage: 'local' }
  );

  /** 个股云图加载错误提示（如请求到无快照的时间点） */
  const [stockError, setStockError] = useState<string | null>(null);
  /** 板块卡片刷新序号：自增时触发 SectorBoardCards 重新拉取后端数据（无感刷新） */
  const [boardRefreshKey, setBoardRefreshKey] = useState(0);

  // ===== 板块资金流状态（仅「资金」一级 TAB 下使用）=====
  /** 板块类型：industry 行业 / concept 概念 */
  const [fundSectorType, setFundSectorType] = useState<'industry' | 'concept'>('industry');
  /** 查询天数 */
  const [fundDays, setFundDays] = useState<string>('30');
  /** 资金流折线图数据 */
  const [fundFlowData, setFundFlowData] = useState<SectorFundFlowResponse>({ dates: [], sectors: [] });
  /** 资金流数据加载状态 */
  const [fundFlowLoading, setFundFlowLoading] = useState(false);
  /** 资金流加载错误信息 */
  const [fundFlowError, setFundFlowError] = useState<string | null>(null);
  /** 可选板块列表 */
  const [availableSectors, setAvailableSectors] = useState<SectorFundFlowSectorItem[]>([]);
  /** 已选中的板块代码列表 */
  const [selectedSectorCodes, setSelectedSectorCodes] = useState<string[]>([]);

  // ===== 详情视图状态（点击板块节点下钻后使用）=====
  /** 当前选中的板块（代码 + 名称） */
  const [selectedSector, setSelectedSector] = useState<{ code: string; name: string } | null>(null);
  /** 板块成分股列表 */
  const [stocks, setStocks] = useState<StockItem[]>([]);
  /** 成分股加载状态 */
  const [stocksLoading, setStocksLoading] = useState(false);

  // ===================================================================
  // 副作用
  // ===================================================================

  /**
   * 概念云图周期合法性校验：若缓存了外部 API 不支持的周期（如 ytd/year/three_year），
   * 重置为默认值 yesterday。
   */
  useEffect(() => {
    if (!CONCEPT_PERIODS.includes(conceptPeriod)) {
      setConceptPeriod('yesterday');
    }
  }, [conceptPeriod, setConceptPeriod]);

  // ===================================================================
  // 数据加载函数（均使用 useCallback 缓存，避免子组件非必要重渲染）
  // ===================================================================

  /** 加载板块云图数据（申万行业分类），time 为空表示实时 */
  const loadSectorCloudMap = useCallback(async (time?: string) => {
      console.log('loadSectorCloudMap', cloudMapTab, time);
    setLoading(true);
    try {
      const result = await fetchIndustryTree(time);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('加载板块云图失败:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /** 加载个股云图数据（三级树：行业 → 细分行业 → 个股），time 为空表示实时 */
  const loadStockCloudMap = useCallback(async (time?: string) => {
    setLoading(true);
    setStockError(null);
    try {
      const result = await fetchStockCloudMap(time);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err: any) {
      console.error('加载个股云图失败:', err);
      // 数据源严谨性：该时间点若无快照，明确提示，不填充其他时间数据
      setStockError(
        time
          ? `「${time}」暂无快照数据，请选择其他时间点`
          : '个股云图数据加载失败，请稍后重试'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  /** 加载 ETF 云图数据（按量化 API 的 period 参数） */
  const loadETFCloudMap = useCallback(async (period?: ETFPeriod) => {
    setLoading(true);
    try {
      const result = await fetchETFCloudMap(period || etfPeriod);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('加载 ETF 云图失败:', err);
    } finally {
      setLoading(false);
    }
  }, [etfPeriod]);

  /** 加载概念云图数据 */
  const loadConceptCloudMap = useCallback(async (period?: ETFPeriod) => {
    setLoading(true);
    try {
      const result = await fetchConceptCloudMap(period || conceptPeriod);
      setTreemapData(result.sectors);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('加载概念云图失败:', err);
    } finally {
      setLoading(false);
    }
  }, [conceptPeriod]);

  /**
   * 按当前云图二级 TAB 加载对应云图数据（统一分发入口）
   *
   * 数据源与选择器差异：
   * - sector（板块云图）：按时间快照 time 拉取
   * - stock（个股云图）：按时间快照 time 拉取
   * - etf（ETF 云图）：使用周期选择器 etfPeriod，忽略 time
   * - concept（概念云图）：使用周期选择器 conceptPeriod，忽略 time
   */
  const loadActiveCloudMap = useCallback((time?: string) => {
    console.log('loadActiveCloudMap', cloudMapTab, time);
    switch (cloudMapTab) {
      case 'sector':
        loadSectorCloudMap(time);
        break;
      case 'stock':
        loadStockCloudMap(time);
        break;
      case 'etf':
        loadETFCloudMap();
        break;
      case 'concept':
        loadConceptCloudMap();
        break;
    }
  }, [cloudMapTab, loadSectorCloudMap, loadStockCloudMap, loadETFCloudMap, loadConceptCloudMap]);

  /** 加载板块资金流的可选板块列表 */
  const loadFundSectorList = useCallback(async (sectorType?: 'industry' | 'concept') => {
    const type = sectorType ?? fundSectorType;
    try {
      const sectors = await fetchSectorFundFlowSectorList(type);
      setAvailableSectors(sectors);
      // 默认选中前 10 个
      setSelectedSectorCodes(sectors.slice(0, 10).map((s) => s.code));
    } catch (e) {
      console.error('加载板块列表失败:', e);
    }
  }, [fundSectorType]);

  /** 加载板块资金流历史数据 */
  const loadFundFlow = useCallback(async (
    sectorType?: 'industry' | 'concept',
    days?: number,
  ) => {
    setFundFlowLoading(true);
    setFundFlowError(null);
    try {
      const data = await fetchSectorFundFlowHistory({
        sectorType: sectorType ?? fundSectorType,
        limit: days ?? Number(fundDays),
        topN: 10,
        sectorCodes: selectedSectorCodes.length > 0 ? selectedSectorCodes : undefined,
      });
      setFundFlowData(data);
    } catch (e) {
      console.error('加载资金流数据失败:', e);
      setFundFlowError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setFundFlowLoading(false);
    }
  }, [fundSectorType, fundDays, selectedSectorCodes]);

  /** 加载行业成分股（点击板块后下钻） */
  const loadSectorStocks = useCallback(async (sectorCode: string, sectorName: string) => {
    setStocksLoading(true);
    setSelectedSector({ code: sectorCode, name: sectorName });
    setViewMode('detail');
    try {
      const result = await fetchSectorStocks(sectorCode, 'industry');
      setStocks(result.stocks);
    } catch (err) {
      console.error('加载成分股失败:', err);
      setStocks([]);
    } finally {
      setStocksLoading(false);
    }
  }, []);

  // ===================================================================
  // 刷新入口（手动刷新 + 倒计时归零共用）
  // ===================================================================

  /**
   * 刷新当前一级 TAB 下的全部数据
   * - 「资金」TAB：重新拉取资金流数据
   * - 其余 TAB（板块 / 云图）：重新拉取对应云图数据
   * 仅重新获取并渲染数据，不触发页面整体重新挂载/刷新，保证体验。
   */
  const refreshActiveTabData = useCallback(() => {
    // 手动/倒计时刷新应强制拉取最新数据：先失效前端 L1 内存缓存，
    // 否则 apiClient 的请求拦截器会命中缓存直接短路，导致后端收不到请求、数据不更新。
    if (primaryTabValue === 'sector-fund') {
      apiCache.invalidate('GET:/api/v1/sector/fund-flow*');
    } else {
      apiCache.invalidate('GET:/api/v1/sector/*');
    }
    if (primaryTabValue === 'sector-fund') {
      loadFundFlow();
    } else if (primaryTabValue === 'sector') {
      // 「板块」一级 TAB：刷新当前激活二级 TAB（industry/concept）的板块卡片数据
      setBoardRefreshKey((k) => k + 1);
    } else {
      // 「云图」一级 TAB：按当前激活二级 TAB（sector/stock/etf/concept）刷新对应云图
      loadActiveCloudMap(selectedTime || undefined);
    }
  }, [primaryTabValue, loadFundFlow, loadActiveCloudMap, selectedTime, setBoardRefreshKey]);

  // ===================================================================
  // 生命周期
  // ===================================================================

  /** 切换到「资金」一级 TAB 时，先加载板块列表，再加载资金流数据 */
  useEffect(() => {
    if (primaryTabValue === 'sector-fund') {
      loadFundSectorList().then(() => loadFundFlow());
    }
    // 仅依赖 primaryTabValue：列表与资金流各自会读取最新的类型/天数/选中项
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [primaryTabValue]);

  /** 首次加载 + TAB 切换时拉取云图数据；实时模式的自动刷新倒计时由 DataRefreshBar 内部管理 */
  useEffect(() => {
    // 板块一级 TAB 通过 loadActiveCloudMap（默认板块云图）加载数据，
    // 自动刷新（含 30s 倒计时）已在 DataRefreshBar 内部自治，本处只负责触发数据加载
    loadActiveCloudMap(selectedTime || undefined);
  }, [primaryTabValue, loadActiveCloudMap, selectedTime]);

  // ===================================================================
  // 事件处理
  // ===================================================================

  /** 切换快照时间（实时 ↔ 历史时间点）：更新选择并立即重新加载云图 */
  const handleTimeSelect = useCallback((time: string) => {
    setSelectedTime(time);
    loadActiveCloudMap(time || undefined);
  }, [setSelectedTime, loadActiveCloudMap]);

  /** 点击板块节点 → 下钻查看成分股 */
  const handleSectorClick = useCallback((sectorCode: string, sectorName: string) => {
    loadSectorStocks(sectorCode, sectorName);
  }, [loadSectorStocks]);

  /** 从详情视图返回概览 */
  const handleBackToOverview = useCallback(() => {
    setViewMode('overview');
    setSelectedSector(null);
    setStocks([]);
  }, []);

  // ===================================================================
  // 辅助函数
  // ===================================================================

  /** 格式化时间为 HH:MM:SS（24 小时制） */
  const formatTime = (date: Date): string =>
    date.toLocaleTimeString('zh-CN', { hour12: false });

  /**
   * 判断快照时间是否已到达：未到达的时间点按钮应禁用，防止查看未来数据
   */
  const isSnapshotTimeAvailable = (timeStr: string): boolean => {
    const now = new Date();
    const [h, m] = timeStr.split(':').map(Number);
    const snapshotMinutes = h * 60 + m;
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    return currentMinutes >= snapshotMinutes;
  };

  // ===================================================================
  // 派生数据（统计卡片 / 标题 / 图例）
  // ===================================================================

  /**
   * 云图统计数据：根据当前 treemapData 计算涨跌统计。
   * 板块/ETF/概念云图使用一级节点统计，个股云图使用叶子节点（个股）统计。
   */
  const cloudMapStats = useMemo(() => {
    const firstLevel = treemapData;
    const totalSectors = firstLevel.length;
    const riseCount = firstLevel.filter((s) => s.changePercent > 0).length;
    const fallCount = firstLevel.filter((s) => s.changePercent < 0).length;
    const avgChange = totalSectors > 0
      ? firstLevel.reduce((sum, s) => sum + (s.changePercent || 0), 0) / totalSectors
      : 0;

    // 个股总数与涨跌数：遍历三级树（行业 → 细分行业 → 个股）的叶子节点
    const stockReducer = (sum: number, industry: SectorNode, predicate: (n: SectorNode) => boolean) =>
      sum + (industry.children || []).reduce(
        (s, sub) => s + (sub.children || []).filter(predicate).length,
        0,
      );
    const stockTotal = treemapData.reduce((sum, industry) => sum + stockReducer(0, industry, () => true), 0);
    const stockRiseCount = treemapData.reduce((sum, industry) => sum + stockReducer(0, industry, (n) => n.changePercent > 0), 0);
    const stockFallCount = treemapData.reduce((sum, industry) => sum + stockReducer(0, industry, (n) => n.changePercent < 0), 0);

    return { totalSectors, riseCount, fallCount, avgChange, stockTotal, stockRiseCount, stockFallCount };
  }, [treemapData]);

  /** 云图卡片主标题（按当前云图二级 TAB 生成） */
  const cloudMapTitle = useMemo(() => {
    switch (cloudMapTab) {
      case 'sector': return '申万行业板块云图';
      case 'stock': return 'A 股个股云图';
      case 'etf': return 'ETF 云图';
      case 'concept': return '概念云图';
    }
  }, [cloudMapTab]);

  /** 云图卡片副标题（显示数量、周期等摘要信息） */
  const cloudMapSubtitle = useMemo(() => {
    const { totalSectors, stockTotal } = cloudMapStats;
    switch (cloudMapTab) {
      case 'sector': return `申万行业板块 · 共 ${totalSectors} 个一级行业`;
      case 'stock': return `A 股全部 · 共 ${totalSectors} 个行业 · ${stockTotal} 只个股`;
      case 'etf': return `ETF 云图 · 市值前 ${totalSectors} 只 ETF · ${ETF_PERIOD_LABELS[etfPeriod]}`;
      case 'concept': return `概念云图 · 市值前 ${totalSectors} 个概念 · ${ETF_PERIOD_LABELS[conceptPeriod]}`;
    }
  }, [cloudMapTab, cloudMapStats, etfPeriod, conceptPeriod]);

  /** 平均涨跌幅文本（带正负号）与颜色 */
  const avgChangeText = `${cloudMapStats.avgChange > 0 ? '+' : ''}${Number(cloudMapStats.avgChange).toFixed(2)}%`;
  const avgChangeColor =
    cloudMapStats.avgChange > 0 ? 'stock-up' : cloudMapStats.avgChange < 0 ? 'stock-down' : 'text-muted-text';

  /** 统计卡片数组（4 张）：标签、数值、颜色按当前云图二级 TAB 动态生成 */
  const statCards: { label: string; value: string | number; color: string }[] = useMemo(() => {
    const { totalSectors, riseCount, fallCount, stockTotal, stockRiseCount, stockFallCount } = cloudMapStats;
    if (cloudMapTab === 'stock') {
      return [
        { label: '行业数', value: totalSectors, color: 'text-foreground' },
        { label: '上涨个股', value: stockRiseCount, color: 'stock-up' },
        { label: '下跌个股', value: stockFallCount, color: 'stock-down' },
        { label: '个股总数', value: stockTotal, color: 'text-foreground' },
        { label: '平均涨跌幅', value: avgChangeText, color: avgChangeColor },
      ];
    }
    return [
      { label: cloudMapTab === 'sector' ? '一级行业数' : cloudMapTab === 'etf' ? 'ETF 数量' : '概念数量', value: totalSectors, color: 'text-foreground' },
      { label: '上涨', value: riseCount, color: 'stock-up' },
      { label: '下跌', value: fallCount, color: 'stock-down' },
      { label: '平均涨跌幅', value: avgChangeText, color: avgChangeColor },
    ];
  }, [cloudMapTab, cloudMapStats, avgChangeText, avgChangeColor]);

  /** 涨跌幅图例色块：-4% ~ +4% 的颜色映射（绿跌红涨） */
  const LEGEND_COLORS: Record<number, string> = {
    '-4': '#22CC55', '-3': '#1AAA44', '-2': '#128833', '-1': '#0A6622',
    '0': '#777777',
    '1': '#661111', '2': '#882222', '3': '#AA3333', '4': '#CC4444',
  };

  // ===================================================================
  // 渲染输出
  // ===================================================================
  return (
    <AppPage>
      <div className="hrs-page-sector space-y-4">
        {/* ===== 整体说明 =====
         * 一级 TAB 行右侧统一挂「更新时间 / 刷新」栏；
         * 二级 TAB 随一级切换：
         * - 「板块」下：行业板块 / 概念板块（boardTab）
         * - 「云图」下：板块云图 / 个股云图 / ETF 云图 / 概念云图（cloudMapTab）
         * - 「资金」无二级 TAB
         */}



        <div className="space-y-3">
           {/* ===== 一级TAB导航 ===== */}
          <TabNav<PrimaryTab>
            items={PRIMARY_TABS}
            value={primaryTabValue}
            onChange={(v) => setPrimaryTab(v)}
            variant="primary"
            ariaLabel="一级导航"
            rightSlot={
              <DataRefreshBar
                lastUpdate={lastUpdate}
                snapshotTime={selectedTime}
                loading={loading}
                onRefresh={refreshActiveTabData}
                onCountdownEnd={refreshActiveTabData}
              />
            }
          />


          {/* ===== 一级TAB为 ”板块“ ===== */}
          {primaryTabValue === 'sector' && (

            <TabNav<BoardType>
              items={SECTOR_TABS}
              value={boardTab}
              onChange={(v) => setBoardTab(v)}
              variant="secondary"
              ariaLabel="二级导航（板块类型）"
              rightSlot={
                // 板块搜索框（仅「板块」下显示，挂在二级 TAB 的右侧）
                <InputGroup className="rounded-sm w-60">
                  <InputGroup.Prefix>
                    <Search className="h-3.5 w-3.5 text-muted-text" />
                  </InputGroup.Prefix>
                  <InputGroup.Input
                    type="text"
                    placeholder="搜索板块..."
                    value={boardSearchKeyword}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setBoardSearchKeyword(e.target.value)
                    }
                  />
                </InputGroup>
              }
            />
          )}
           {/* ===== 一级TAB为” 云图“ ===== */}
          {primaryTabValue === 'cloud-map' && (
            <TabNav<CloudMapTab>
              items={CLOUD_MAP_TABS}
              value={cloudMapTab}
              onChange={(v) => { setCloudMapTab(v); setViewMode('overview'); }}
              variant="secondary"
              ariaLabel="二级导航（云图类型）"
            />
          )}
        </div>

        {/* ===== 3. 板块卡片列表（仅「板块」一级 TAB；类型与搜索词均由二级 TAB 驱动）===== */}
        {primaryTabValue === 'sector' && (
          <SectorBoardCards
            boardType={boardTab}
            searchKeyword={boardSearchKeyword}
            refreshKey={boardRefreshKey}
          />
        )}

        {/* ===== 4. 云图内容（仅「云图」一级 TAB + 概览模式）===== */}
        {primaryTabValue === 'cloud-map' && viewMode === 'overview' && (
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
                  {/* ETF 周期选择器 */}
                  {cloudMapTab === 'etf' && (
                    <Select
                      value={etfPeriod}
                      onChange={(v: string) => {
                        setEtfPeriod(v as ETFPeriod);
                        loadETFCloudMap(v as ETFPeriod);
                      }}
                      options={ETF_PERIODS.map((p) => ({ value: p, label: ETF_PERIOD_LABELS[p] }))}
                      className="w-36"
                    />
                  )}
                  {/* 概念云图周期选择器（仅支持 6 个周期） */}
                  {cloudMapTab === 'concept' && (
                    <Select
                      value={conceptPeriod}
                      onChange={(v: string) => {
                        setConceptPeriod(v as ETFPeriod);
                        loadConceptCloudMap(v as ETFPeriod);
                      }}
                      options={CONCEPT_PERIODS.map((p) => ({ value: p, label: ETF_PERIOD_LABELS[p] }))}
                      className="w-36"
                    />
                  )}
                  {/* 板块/个股云图：时间快照选择器（实时 + 10 个时间点） */}
                  {(cloudMapTab === 'sector' || cloudMapTab === 'stock') && (
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
                        const available = isSnapshotTimeAvailable(t);
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
                  onSectorClick={cloudMapTab === 'sector' ? handleSectorClick : undefined}
                  height="650px"
                />
              )}

              {/* 云图底部信息栏：更新时间 + 面积/颜色含义图例 */}
              <div className="px-4 py-2 border-t border-subtle flex items-center justify-between">
                <span className="text-xs text-muted-text">
                  {lastUpdate && `更新于 ${formatTime(lastUpdate)}`}
                  {(cloudMapTab === 'sector' || cloudMapTab === 'stock') && !selectedTime && ' · 每 30 秒自动刷新'}
                  {(cloudMapTab === 'sector' || cloudMapTab === 'stock') && selectedTime && (
                    <span className="text-cyan"> · 快照模式：{selectedTime}</span>
                  )}
                  {cloudMapTab === 'stock' && stockError && (
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

        {/* ===== 5. 详情视图：点击行业板块后下钻展示成分股表格（仅「云图」一级 TAB + 详情模式）===== */}
        {primaryTabValue === 'cloud-map' && viewMode === 'detail' && selectedSector && (
          <SectorStockTable
            sectorName={`${selectedSector.name}（行业板块）`}
            stocks={stocks}
            loading={stocksLoading}
            onBack={handleBackToOverview}
          />
        )}

        {/* ===== 一级TAB为 ”资金“ ===== */}
        {primaryTabValue === 'sector-fund' && (
          <>
            {/* 控制栏：板块类型 + 板块多选 + 天数 + 查询 */}
            <div className="flex items-center gap-3 flex-wrap">
              <Select
                value={fundSectorType}
                onChange={(v: string) => {
                  const newType = v as 'industry' | 'concept';
                  setFundSectorType(newType);
                  setSelectedSectorCodes([]);
                  setAvailableSectors([]);
                  loadFundSectorList(newType);
                }}
                options={[
                  { value: 'industry', label: '行业板块' },
                  { value: 'concept', label: '概念板块' },
                ]}
                className="w-28"
              />
              {/* 板块多选下拉框（自定义） */}
              <SectorMultiSelect
                items={availableSectors}
                value={selectedSectorCodes}
                onChange={setSelectedSectorCodes}
              />
              <Select
                value={fundDays}
                onChange={(v: string) => setFundDays(v)}
                options={[
                  { value: '10', label: '近10日' },
                  { value: '30', label: '近30日' },
                  { value: '60', label: '近60日' },
                ]}
                className="w-28"
              />
              {/* 查询按钮：刷新板块资金流数据 */}
              <div className="ml-auto flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => loadFundFlow()}
                  disabled={fundFlowLoading}
                  className={`inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150 ${
                    fundFlowLoading
                      ? 'border-cyan/60 bg-cyan/15 text-cyan'
                      : 'border-cyan/60 bg-cyan/10 text-cyan hover:bg-cyan/20'
                  } disabled:opacity-50`}
                >
                  查询
                </button>
              </div>
            </div>

            <Card variant="bordered" padding="none" className="overflow-hidden">
              {fundFlowLoading && fundFlowData.sectors.length === 0 ? (
                <div className="flex items-center justify-center py-24">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
                </div>
              ) : fundFlowError ? (
                <div className="py-12 text-center text-danger text-sm">{fundFlowError}</div>
              ) : fundFlowData.sectors.length === 0 ? (
                <div className="py-12 text-center text-muted-text">暂无数据</div>
              ) : (
                <>
                  {/* 图表标题栏 */}
                  <div className="px-4 py-3 border-b border-subtle">
                    <div className="flex flex-col gap-0.5">
                      <h2 className="text-sm font-semibold text-foreground">
                        {fundSectorType === 'industry' ? '行业' : '概念'}板块资金流向
                      </h2>
                      <p className="text-xs text-muted-text">
                        主力净流入（亿） · 近 {fundDays} 日 · {fundFlowData.sectors.length} 个板块
                      </p>
                    </div>
                  </div>
                  <SectorFundFlowChart data={fundFlowData} height="500px" />
                </>
              )}
            </Card>
          </>
        )}
      </div>
    </AppPage>
  );
};

export default SectorAnalysisPage;

// =============================================
// 板块多选下拉框组件（SectorMultiSelect）
// =============================================
// 作用：为「资金」TAB 提供板块多选功能。
// 交互设计：
// - 触发器：显示已选板块的 tag（最多 3 个 + "+N" 溢出提示）
// - 下拉面板：搜索框 + 板块列表（带勾选标记）+ 底部操作栏（全选/反选）
// - 点击外部自动关闭下拉

/** SectorMultiSelect 组件的属性定义 */
type SectorMultiSelectProps = {
  /** 可选板块列表（从后端 API 获取） */
  items: SectorFundFlowSectorItem[];
  /** 当前已选中的板块代码数组 */
  value: string[];
  /** 选中值变更回调 */
  onChange: (codes: string[]) => void;
};

/**
 * 板块多选下拉框组件
 *
 * 提供板块的多选能力，包含搜索、全选、反选功能。
 * 已选板块以 tag 形式显示在触发器中，最多显示 3 个，超出部分显示 "+N"。
 *
 * @param props.items - 可选板块列表
 * @param props.value - 当前选中的板块代码
 * @param props.onChange - 选中值变更回调
 */
function SectorMultiSelect({ items, value, onChange }: SectorMultiSelectProps) {
  /** 下拉面板是否展开 */
  const [open, setOpen] = useState(false);
  /** 搜索关键词 */
  const [search, setSearch] = useState('');
  /** 容器 ref，用于检测点击外部区域 */
  const containerRef = useRef<HTMLDivElement>(null);

  /** 点击外部区域时自动关闭下拉面板 */
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  /** 根据搜索关键词过滤板块列表（空搜索显示全部） */
  const selectedSet = new Set(value);
  const filtered = search
    ? items.filter((s) => s.name.toLowerCase().includes(search.toLowerCase()))
    : items;

  /** 是否全部选中 */
  const allCodes = items.map((s) => s.code);
  const allSelected = items.length > 0 && items.every((s) => selectedSet.has(s.code));

  /** 全选 / 清空切换 */
  const handleSelectAll = () => {
    onChange(allSelected ? [] : allCodes);
  };

  /** 反选：将已选的取消，未选的选中 */
  const handleInvert = () => {
    const inverted = allCodes.filter((c) => !selectedSet.has(c));
    onChange(inverted);
  };

  /** 单个板块的选中/取消切换 */
  const handleToggle = (code: string) => {
    if (selectedSet.has(code)) {
      onChange(value.filter((c) => c !== code));
    } else {
      onChange([...value, code]);
    }
  };

  /** 触发器显示的 tag 列表（最多显示 3 个，超出部分显示 "+N"） */
  const displayTags = value.slice(0, 3).map((code) => items.find((s) => s.code === code)).filter(Boolean);
  /** 超出 3 个的剩余数量 */
  const extraCount = value.length - 3;

  return (
    <div ref={containerRef} className="relative">
      {/* 触发器 */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 min-w-[180px] max-w-[320px] px-2.5 py-1.5 text-xs rounded-lg border border-subtle bg-bg-elevated text-foreground hover:border-cyan/40 transition-colors"
      >
        <div className="flex items-center gap-1 flex-wrap flex-1 min-w-0">
          {displayTags.map((s) => (
            s && (
              <span
                key={s.code}
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-cyan/15 text-cyan text-xs whitespace-nowrap"
              >
                {s.name}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToggle(s.code);
                  }}
                  className="text-cyan/60 hover:text-cyan"
                >
                  ×
                </button>
              </span>
            )
          ))}
          {extraCount > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-muted/20 text-muted-text text-xs whitespace-nowrap">
              +{extraCount}
            </span>
          )}
          {value.length === 0 && (
            <span className="text-muted-text text-xs">选择板块</span>
          )}
        </div>
        <ChevronUp className={`h-3.5 w-3.5 text-muted-text transition-transform ${open ? '' : 'rotate-180'}`} />
      </button>

      {/* 下拉面板 */}
      {open && (
        <div className="absolute z-50 mt-1 w-72 rounded-lg border border-subtle bg-bg-elevated shadow-xl overflow-hidden">
          {/* 搜索框 */}
          <div className="px-3 py-2 border-b border-subtle">
            <input
              type="text"
              placeholder="搜索板块..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-2 py-1 text-xs rounded border border-subtle bg-bg-primary text-foreground placeholder:text-muted-text focus:outline-none focus:border-cyan/50"
            />
          </div>
          {/* 板块列表 */}
          <div className="max-h-64 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-center text-xs text-muted-text">无匹配板块</div>
            ) : (
              filtered.map((s) => {
                const isSelected = selectedSet.has(s.code);
                return (
                  <button
                    key={s.code}
                    type="button"
                    onClick={() => handleToggle(s.code)}
                    className={`w-full flex items-center justify-between px-3 py-1.5 text-xs transition-colors ${
                      isSelected
                        ? 'text-cyan font-medium'
                        : 'text-foreground hover:bg-muted/10'
                    }`}
                  >
                    <span>{s.name}</span>
                    {isSelected && <Check className="h-3.5 w-3.5 text-cyan" />}
                  </button>
                );
              })
            )}
          </div>
          {/* 底部操作栏 */}
          <div className="flex items-center justify-between px-3 py-2 border-t border-subtle bg-muted/5">
            <span className="text-xs text-muted-text">已选 {value.length} / {items.length}</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSelectAll}
                className="text-xs text-cyan hover:text-cyan/80 transition-colors"
              >
                {allSelected ? '清空' : '全选'}
              </button>
              <span className="text-muted-text/40">|</span>
              <button
                type="button"
                onClick={handleInvert}
                className="text-xs text-cyan hover:text-cyan/80 transition-colors"
              >
                反选
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
