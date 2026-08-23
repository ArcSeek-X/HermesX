/**
 * StockDashboardPage —— 市场总览页面
 * =====================================================================
 * 【功能介绍】
 * 市场行情与核心指标的一屏总览，顶部提供「A股 / 港美 / 日韩」三个市场 TAB，
 * 下方以卡片网格展示：指数行情 + 市场统计指标（涨跌家数、涨跌停、成交额、
 * 北向资金、大盘主力、最强板块）。数据每 30 秒自动刷新，TAB 偏好通过
 * useCachedState 持久化到 localStorage，刷新页面后保持上次选择。
 *
 * 【主要能力】
 * - 三个市场 TAB：A股（指数 + 6 张统计卡同网格）、港美、日韩（纯指数卡）。
 * - 并发加载 7 个数据源（指数 / 概览 / 北向 / 主力 / 最强板块 / 港美 / 日韩），
 *   单源失败不影响其他；港美、日韩接口失败时降级为「空列表」，不阻塞整页。
 * - 无感占位：数据未到达前先渲染 EMPTY_INDEX 占位卡片，数据到达后按位置替换，
 *   卡片实例保持稳定、入场动画只跑一次（避免布局抖动与 motion 重挂载）。
 * - 自动刷新：挂载时首次加载，之后每 30 秒轮询；卸载清理定时器。
 *
 * 【状态 / 数据流】
 * - 市场行情（indices / globalIndices / asiaIndices）按 TAB 分三组独立 state。
 * - 概览 / 北向 / 主力 / 最强板块为单组 state，仅 A股 TAB 使用。
 * - 所有接口后端有 60 秒 TTL，前端 30 秒轮询只触发一次并发请求，命中缓存。
 * =====================================================================
 */
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { AppPage, TabNav } from '../components';
import { useCachedState } from '../hooks/useCachedState';
import IndexCard from '../components/indexCard/IndexCard';

import {
  MarketBreadthCard,
  LimitUpDownCard,
  TotalAmountCard,
  NorthboundCard,
  MainFlowCard,
  StrongestSectorCard,
} from '../components/indexCard/MarketStatCards';
import {
  fetchAsiaIndices,
  fetchBoardList,
  fetchGlobalIndices,
  fetchMarketFundFlow,
  fetchMarketIndices,
  fetchMarketOverview,
  fetchNorthboundFlow,
  type BoardListItem,
  type MarketFundFlowData,
  type MarketIndexItem,
  type MarketOverviewData,
  type NorthboundFlowData,
} from '../api/sectorData';
import { CardRoot } from '@heroui/react';

/** 数据自动刷新间隔：30 秒（与原板块分析页仪表盘行为保持一致） */
const REFRESH_INTERVAL_MS = 30_000;

/** 指数占位卡片数量（与后端 MARKET_INDICES 的 10 个指数一致） */
const INDEX_PLACEHOLDER_COUNT = 10;

/** 港美指数占位卡片数量（与后端 MARKET_INDICES_US 的 8 个指数一致） */
const GLOBAL_INDEX_PLACEHOLDER_COUNT = 6;

/** 日韩指数占位卡片数量（与后端 MARKET_INDICES_JP_KR 的 3 个指数一致） */
const ASIA_INDEX_PLACEHOLDER_COUNT = 2;

/** 总览页市场 TAB：a=A股 / hk-us=港美 / jp-kr=日韩 */
type MarketTab = 'a' | 'hk-us' | 'jp-kr';

/** 市场 TAB 标签（顺序即展示顺序） */
const MARKET_TABS: { key: MarketTab; label: string }[] = [
  { key: 'a', label: 'A股' },
  { key: 'hk-us', label: '港美' },
  { key: 'jp-kr', label: '日韩' },
];

/** 空数据占位指数：字段全 null，IndexCard 渲染为 '--'（接口未返回时先行渲染占位） */
const EMPTY_INDEX: MarketIndexItem = {
  name: '--',
  code: '',
  price: null,
  changePercent: null,
  change: null,
  amount: null,
  high: null,
  low: null,
  preClose: null,
};

/**
 * 页面结构（从上到下）：
 * 1. 指数卡片区：全部市场指数的 IndexCard（名称/点位/涨跌幅/涨跌点数/成交额/放量）
 * 2. 统计卡片区：市场涨跌、涨跌停、全市场成交额、北向资金、大盘主力、最强板块
 *
 * 状态管理：
 * - 五个数据接口（指数/概览/北向/主力/板块）挂载时并发加载，之后每 30 秒定时刷新
 * - 数据未返回时不展示 loading：指数卡片区先渲染占位卡片（字段 '--'），数据到达后自动替换
 * - 各数据独立缓存（后端 60 秒 TTL），前端刷新仅触发一次并发请求
 */

/**
 * 总览页面
 *
 * 页面结构（从上到下）：
 * 1. 指数卡片区：全部市场指数的 IndexCard（名称/点位/涨跌幅/涨跌点数/成交额/放量）
 * 2. 统计卡片区：市场涨跌、涨跌停、全市场成交额、北向资金、大盘主力、最强板块
 *
 * 状态管理：
 * - 五个数据接口（指数/概览/北向/主力/板块）挂载时并发加载，之后每 30 秒定时刷新
 * - 数据未返回时不展示 loading：指数卡片区先渲染占位卡片（字段 '--'），数据到达后自动替换
 * - 各数据独立缓存（后端 60 秒 TTL），前端刷新仅触发一次并发请求
 */
/**
 * 指数卡片网格：复用统一的 IndexCard 模板渲染任意市场的指数列表（港美 / 日韩 TAB 使用）。
 * - 数据未到达（indices 为空）时，先按 placeholderCount 渲染空卡片，避免布局抖动。
 * - 真实数据到达后按位置替换，IndexCard 实例保持稳定，入场动画只跑一次。
 *
 * @param indices         真实指数列表（接口返回）
 * @param placeholderCount 占位卡片数量（与后端该市场指数数量一致）
 * @param keyPrefix       卡片 key 前缀，区分不同市场避免复用错误
 */
const IndexCardGrid: React.FC<{
  indices: MarketIndexItem[];
  placeholderCount: number;
  /** 卡片 key 前缀，区分不同市场避免复用错误 */
  keyPrefix: string;
}> = ({ indices, placeholderCount, keyPrefix }) => {
  // 按 placeholderCount 渲染槽位：真实数据不足时用 EMPTY_INDEX 占位补齐，
  // 避免后端实际返回数 < 配置 secid 数（如东财 push2 对某些海外指数不返数据）
  // 时渲染循环越界访问 undefined，导致 IndexCard 抛错触发 RouteBoundary「页面加载失败」
  const totalSlots = Math.max(indices.length, placeholderCount);
  const display: MarketIndexItem[] = Array.from({ length: totalSlots }, (_, i) => indices[i] ?? EMPTY_INDEX);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
      {display.map((item, i) => (
        <IndexCard key={`${keyPrefix}-${i}`} index={item} ordinal={i} />
      ))}
    </div>
  );
};

/**
 * 市场总览主页面组件。
 * 负责：市场 TAB 切换、七个数据源并发加载与 30 秒自动刷新、
 * 占位卡片无感渲染、A股 TAB 下指数卡与统计卡一体化网格布局。
 */
const StockDashboardPage: React.FC = () => {
  // ---- 市场数据状态（按卡片区域分组）----
  /** 指数行情列表（含涨跌点数、成交额） */
  const [indices, setIndices] = useState<MarketIndexItem[]>([]);
  /** 港美指数行情列表（道琼斯、标普500、纳斯达克等） */
  const [globalIndices, setGlobalIndices] = useState<MarketIndexItem[]>([]);
  /** 日韩指数行情列表（日经指数、韩国综指、韩国KOSDAQ） */
  const [asiaIndices, setAsiaIndices] = useState<MarketIndexItem[]>([]);
  /** 市场概览（涨跌家数、涨跌停、成交额、量能） */
  const [overview, setOverview] = useState<MarketOverviewData | null>(null);
  /** 北向资金净流入 */
  const [northbound, setNorthbound] = useState<NorthboundFlowData | null>(null);
  /** 大盘主力资金 */
  const [fundFlow, setFundFlow] = useState<MarketFundFlowData | null>(null);
  /** 最强板块（行业涨幅第一） */
  const [strongestBoard, setStrongestBoard] = useState<BoardListItem | null>(null);

  /** 当前激活的市场 TAB（L2+L4 缓存：localStorage 持久化用户偏好） */
  const [marketTab, setMarketTab] = useCachedState<MarketTab>(
    'dashboard.marketTab',
    'a',
    { storage: 'local' }
  );

  /** 并发加载全部市场数据（指数 + 概览 + 北向 + 主力 + 最强板块 + 港美 + 日韩） */
  const load = useCallback(async () => {
    try {
      // 七个数据源并发请求；港美 / 日韩接口失败时降级为「空列表」，不阻塞整页加载。
      // 其余五个接口任意一个失败会让 Promise.all reject，被下方 catch 吞掉（仅打印日志），
      // 已成功返回的数据不会写入 state——如需「部分成功也渲染」，可改为 allSettled 分别处理。
      const [indexData, overviewData, northboundData, fundFlowData, boardData, globalData, asiaData] = await Promise.all([
        fetchMarketIndices(),
        fetchMarketOverview(),
        fetchNorthboundFlow(),
        fetchMarketFundFlow(),
        fetchBoardList('industry'),
        fetchGlobalIndices().catch(() => [] as MarketIndexItem[]),
        fetchAsiaIndices().catch(() => [] as MarketIndexItem[]),
      ]);
      // 将并发结果分别写入对应 state，触发渲染
      setIndices(indexData);
      setGlobalIndices(globalData);
      setAsiaIndices(asiaData);
      setOverview(overviewData);
      setNorthbound(northboundData);
      setFundFlow(fundFlowData);
      // 最强板块取行业榜第一；榜单为空时置 null（卡片内部降级展示）
      setStrongestBoard(boardData.boards[0] ?? null);
    } catch (err) {
      console.error('Failed to load stock dashboard:', err);
    }
  }, []);

  // 挂载时首次加载，之后每 30 秒自动刷新；卸载时清理定时器
  useEffect(() => {
    // 异步包装首屏加载，避免 effect 内同步调用 setState
    async function init() {
      await load();
    }
    init();
    const timer = setInterval(() => {
      load();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [load]);

  // 指数卡片实际渲染数量（占位阶段用 INDEX_PLACEHOLDER_COUNT，数据到达后用真实长度）
  // 统计卡片区的 ordinal 从该数量之后继续递增，使指数卡与统计卡在入场动画上一体化依次出现
  const indexCount = indices.length > 0 ? indices.length : INDEX_PLACEHOLDER_COUNT;

  // 占位 + 真实数据合并：未到达的索引位用 EMPTY_INDEX 填充，确保列表长度与 key 始终稳定，
  // 避免数据到达后 IndexCard 被卸载重挂载导致 motion 重新触发入场动画
  const displayIndices: MarketIndexItem[] =
    indices.length > 0
      ? indices
      : Array.from({ length: INDEX_PLACEHOLDER_COUNT }, () => EMPTY_INDEX);

  /**
   * 根据当前激活的 marketTab 渲染对应内容。
   * 提取为独立函数（而非在 JSX 内写深层嵌套三元），
   * 可避免 babel 在"? ("包裹的多行 JSX 嵌套三元中丢失 JSX 上下文的解析边界问题。
   *
   * - 'a'（A股）：指数卡片 + 6 张统计卡片同处一个网格，ordinal 连续递增使入场动画一体化；
   * - 'hk-us'（港美）：纯指数卡片网格（全球指数数据）；
   * - 'jp-kr'（日韩）：纯指数卡片网格（日韩指数数据）。
   */
  const renderMarketContent = () => {
    // A股 TAB：指数卡片与统计卡片同处一个网格，首尾相接排列
    if (marketTab === 'a') {
      return (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
          {displayIndices.map((index, i) => (
            // 使用 position index 作为 key：指数顺序固定，数据到达时不会 reorder；
            // 占位 → 真实数据时 key 不变，IndexCard 实例保持稳定，入场动画只跑一次
            <IndexCard key={`index-${i}`} index={index} ordinal={i} />
          ))}
          {/* 统计卡片：ordinal 从 indexCount 之后连续递增，保证入场顺序与指数卡衔接 */}
          <MarketBreadthCard
            ordinal={indexCount}
            riseCount={overview?.riseCount ?? 0}
            fallCount={overview?.fallCount ?? 0}
            flatCount={overview?.flatCount ?? 0}
          />
          <LimitUpDownCard
            ordinal={indexCount + 1}
            limitUpCount={overview?.limitUpCount ?? 0}
            limitDownCount={overview?.limitDownCount ?? 0}
          />
          <TotalAmountCard ordinal={indexCount + 2} totalAmount={overview?.totalAmount ?? 0} />
          <NorthboundCard ordinal={indexCount + 3} data={northbound} />
          <MainFlowCard ordinal={indexCount + 4} data={fundFlow} />
          <StrongestSectorCard ordinal={indexCount + 5} data={strongestBoard} />
        </div>
      );
    }
    // 港美 TAB：纯指数卡片网格，使用全球指数数据
    if (marketTab === 'hk-us') {
      return (
        <IndexCardGrid indices={globalIndices} placeholderCount={GLOBAL_INDEX_PLACEHOLDER_COUNT} keyPrefix="global" />
      );
    }
    // 日韩 TAB：纯指数卡片网格，使用日韩指数数据
    return (
      <IndexCardGrid indices={asiaIndices} placeholderCount={ASIA_INDEX_PLACEHOLDER_COUNT} keyPrefix="asia" />
    );
  };

  return (
    <AppPage>
      <div className="space-y-4">
        {/* ===== 市场 TAB：A股 / 港美 / 日韩（均接入真实指数数据）===== */}
        <TabNav<MarketTab>
          ariaLabel="市场切换"
          variant="secondary"
          items={MARKET_TABS.map(({ key, label }) => ({ value: key, label }))}
          value={marketTab}
          onChange={setMarketTab}
        />

        {/* 按 TAB 渲染不同内容（提取为独立函数，避免深层嵌套三元导致 JSX 上下文切换异常） */}
        {renderMarketContent()}
      </div>
    </AppPage>
  );
};

export default StockDashboardPage;
