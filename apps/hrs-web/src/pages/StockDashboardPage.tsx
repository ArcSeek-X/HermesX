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
 * - 前端每次只请求一个统一接口 `/api/v1/sector/market-cards?market=<tab-key>`，
 *   由后端按 TAB key 直接组装标准卡片列表并返回。
 * - 无感占位：数据未到达前先渲染 EMPTY_INDEX 占位卡片，数据到达后按位置替换，
 *   卡片实例保持稳定、入场动画只跑一次（避免布局抖动与 motion 重挂载）。
 * - 自动刷新：挂载时首次加载，之后每 30 秒轮询；卸载清理定时器。
 *
 * 【状态 / 数据流】
 * - 三个 TAB 共用统一 `cards[]` 契约，前端仅维护按 market key 分桶的卡片缓存。
 * - 所有接口后端有 60 秒 TTL，前端 30 秒轮询当前 TAB，只触发一个请求。
 * =====================================================================
 */
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { TabNav } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/page-layout';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { MarketBreadthCard, LimitUpDownCard, TotalAmountCard, NorthboundCard, MainFlowCard, StrongestSectorCard } from '@components/indexCard/MarketStatCards';
import IndexCard from '@components/indexCard/IndexCard';
import { useCachedState } from '../hooks/useCachedState';



import {
  fetchMarketCards,
  type MarketCardItem,
  type MarketIndexItem,
  type MarketTabKey,
} from '../api/sectorData';

/** 数据自动刷新间隔：30 秒（与原板块分析页仪表盘行为保持一致） */
const REFRESH_INTERVAL_MS = 30_000;

/** A股指数占位卡片数量 */
const INDEX_PLACEHOLDER_COUNT = 10;

/** 港美指数占位卡片数量 */
const GLOBAL_INDEX_PLACEHOLDER_COUNT = 6;

/** 日韩指数占位卡片数量 */
const ASIA_INDEX_PLACEHOLDER_COUNT = 2;

/** 总览页市场 TAB：与后端 market-cards 的入参完全一致 */
type MarketTab = MarketTabKey;

/** 市场 TAB 标签（顺序即展示顺序），label 经 i18n 映射，labelKey 指向 dashboard.tab.* */
const MARKET_TABS: { key: MarketTab; labelKey: 'dashboard.tab.a' | 'dashboard.tab.hkUs' | 'dashboard.tab.jpKr' }[] = [
  { key: 'a', labelKey: 'dashboard.tab.a' },
  { key: 'hk-us', labelKey: 'dashboard.tab.hkUs' },
  { key: 'jp-kr', labelKey: 'dashboard.tab.jpKr' },
];

const PLACEHOLDER_CARD_COUNT: Record<MarketTab, number> = {
  a: INDEX_PLACEHOLDER_COUNT,
  'hk-us': GLOBAL_INDEX_PLACEHOLDER_COUNT,
  'jp-kr': ASIA_INDEX_PLACEHOLDER_COUNT,
};

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

function buildPlaceholderCards(market: MarketTab): MarketCardItem[] {
  return Array.from({ length: PLACEHOLDER_CARD_COUNT[market] }, (_, index) => ({
    cardType: 'index_quote',
    cardKey: `placeholder:${market}:${index}`,
    payload: EMPTY_INDEX,
  }));
}

function renderMarketCard(card: MarketCardItem, ordinal: number) {
  switch (card.cardType) {
    case 'index_quote':
      return <IndexCard key={card.cardKey} index={card.payload} ordinal={ordinal} />;
    case 'market_breadth':
      return (
        <MarketBreadthCard
          key={card.cardKey}
          ordinal={ordinal}
          riseCount={card.payload.riseCount}
          fallCount={card.payload.fallCount}
          flatCount={card.payload.flatCount}
        />
      );
    case 'limit_up_down':
      return (
        <LimitUpDownCard
          key={card.cardKey}
          ordinal={ordinal}
          limitUpCount={card.payload.limitUpCount}
          limitDownCount={card.payload.limitDownCount}
        />
      );
    case 'total_amount':
      return <TotalAmountCard key={card.cardKey} ordinal={ordinal} totalAmount={card.payload.totalAmount} />;
    case 'northbound_flow':
      return <NorthboundCard key={card.cardKey} ordinal={ordinal} data={card.payload} />;
    case 'main_flow':
      return <MainFlowCard key={card.cardKey} ordinal={ordinal} data={card.payload} />;
    case 'strongest_board':
      return <StrongestSectorCard key={card.cardKey} ordinal={ordinal} data={card.payload} />;
    default:
      return null;
  }
}

/**
 * 市场总览主页面组件。
 * 负责：市场 TAB 切换、统一卡片接口加载与 30 秒自动刷新、
 * 占位卡片无感渲染、各 TAB 的统一卡片网格展示。
 */
const StockDashboardPage: React.FC = () => {
  const { t } = useUiLanguage();
  /** 当前页按 market key 缓存的统一卡片列表 */
  const [cardsByMarket, setCardsByMarket] = useState<Record<MarketTab, MarketCardItem[] | null>>({
    a: null,
    'hk-us': null,
    'jp-kr': null,
  });

  /** 当前激活的市场 TAB（L2+L4 缓存：localStorage 持久化用户偏好） */
  const [marketTab, setMarketTab] = useCachedState<MarketTab>(
    'dashboard.marketTab',
    'a',
    { storage: 'local' }
  );

  /** 加载单个市场 TAB 的统一卡片列表 */
  const load = useCallback(async (market: MarketTab) => {
    try {
      const response = await fetchMarketCards(market);
      setCardsByMarket((prev) => ({
        ...prev,
        [market]: response.cards,
      }));
    } catch (err) {
      console.error(`Failed to load stock dashboard market cards: ${market}`, err);
    }
  }, []);

  // 挂载时加载当前 TAB，切换 TAB 时按需加载；之后每 30 秒刷新当前 TAB
  useEffect(() => {
    async function init() {
      await load(marketTab);
    }
    init();
    const timer = setInterval(() => {
      load(marketTab);
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [load, marketTab]);

  const currentCards = cardsByMarket[marketTab];
  const displayCards = currentCards && currentCards.length > 0 ? currentCards : buildPlaceholderCards(marketTab);

  return (
    <AppPage>
      <div className="space-y-3">
        <PageHeader title={t('layout.nav.index.title')} description={t('layout.nav.index.description')}/>
        {/* ===== 市场 TAB：A股 / 港美 / 日韩（均接入真实指数数据）===== */}
        <TabNav<MarketTab>
          ariaLabel={t('dashboard.marketSwitch')}
          variant="secondary"
          items={MARKET_TABS.map(({ key, labelKey }) => ({ value: key, label: t(labelKey) }))}
          value={marketTab}
          onChange={setMarketTab}
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
          {displayCards.map((card, index) => renderMarketCard(card, index))}
        </div>
      </div>
    </AppPage>
  );
};

export default StockDashboardPage;
