/**
 * 个股 K 线页「最近搜索」区块：标题 + 清空（二次确认）+ 空态 + 卡片网格。
 * 完全受控：数据由页面注入，自身不发起网络请求。
 */

import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import { ConfirmDialog, HrsButton } from '@components';
import { EmptyState } from '@components/basic/EmptyState';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import RecentSearchStockCard, { type RecentSearchStockCardData } from './RecentSearchStockCard';

/** 最近搜索列表受控入参：数据源由页面维护，列表本身不发起请求 */
interface RecentSearchStockListProps {
  /** 最近搜索卡片数据（通用股票对象 + 分时），由页面累积 */
  cards: RecentSearchStockCardData[];
  /** 首次加载中（页面从服务端拉历史记录） */
  isRecentCardsLoading: boolean;
  /** 一键清空：调用方先清空本地再同步服务端 */
  onClear: () => void;
}

/** 卡片网格布局：真实卡片与加载占位共用，避免两处样式漂移 */
const RECENT_CARD_GRID_CLASS = 'grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4';

/** 加载中占位卡片数量（避免空白闪烁） */
const PLACEHOLDER_CARD_COUNT = 4;

/** 加载中占位条目：行情字段全空，卡片渲染为 `--`（对齐 /market/index 的占位卡片做法） */
const PLACEHOLDER_CARD_DATA: RecentSearchStockCardData = {
  info: {
    code: '--',
    name: '--',
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
  },
  timeline: [],
  prevClose: null,
};

/** 最近搜索列表区块：仅在 K 线页未选中股票时渲染，作为搜索引导 */
function RecentSearchStockList({
  cards,
  isRecentCardsLoading,
  onClear,
}: RecentSearchStockListProps) {
  const { t } = useUiLanguage();
  const navigate = useNavigate();

  const [isClearConfirmOpen, setIsClearConfirmOpen] = useState(false);

  /** 整卡跳转：沿用全项目统一的 ?stockCode= 直达模式 */
  const openStockKLine = useCallback(
    (stockCode: string) => {
      const pureCode = stockCode.split('.')[0].trim();
      navigate(`/stock/kline?stockCode=${encodeURIComponent(pureCode)}`);
    },
    [navigate],
  );

  const confirmClear = useCallback(() => {
    setIsClearConfirmOpen(false);
    void onClear();
  }, [onClear]);

  return (
    <section className="space-y-3" aria-label={t('kline.recentSearch.title')}>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">{t('kline.recentSearch.title')}</h2>
        {cards.length > 0 && (
          <HrsButton variant="danger-soft" size="sm" onClick={() => setIsClearConfirmOpen(true)}>
            <Trash2 className="h-3.5 w-3.5" aria-hidden />
            {t('kline.recentSearch.clear')}
          </HrsButton>
        )}
      </div>

      {/* 首次加载中：渲染占位卡片，避免空白/空态闪烁（对齐 /market/index） */}
      {isRecentCardsLoading && cards.length === 0 ? (
        <div className={RECENT_CARD_GRID_CLASS}>
          {Array.from({ length: PLACEHOLDER_CARD_COUNT }, (_, ordinal) => (
            <RecentSearchStockCard
              key={`placeholder-${ordinal}`}
              cardData={PLACEHOLDER_CARD_DATA}
              ordinal={ordinal}
              onOpen={openStockKLine}
              isPlaceholder
            />
          ))}
        </div>
      ) : cards.length === 0 ? (
        <EmptyState title={t('kline.recentSearch.empty')} variant="muted" type="text" />
      ) : (
        <div className={RECENT_CARD_GRID_CLASS}>
          {cards.map((cardData, ordinal) => (
            <RecentSearchStockCard
              key={cardData.info.code}
              cardData={cardData}
              ordinal={ordinal}
              onOpen={openStockKLine}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={isClearConfirmOpen}
        title={t('kline.recentSearch.title')}
        message={t('kline.recentSearch.clearConfirm')}
        isDanger
        onConfirm={confirmClear}
        onCancel={() => setIsClearConfirmOpen(false)}
      />
    </section>
  );
}

export default RecentSearchStockList;
