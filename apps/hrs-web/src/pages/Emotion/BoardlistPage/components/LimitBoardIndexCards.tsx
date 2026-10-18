/**
 * @file LimitBoardIndexCards.tsx
 * @description 涨跌停榜单 KPI 指标卡组：涨停 / 跌停看板共用，指标配置随 boardType 区分。
 *   炸板率与昨日涨停溢价依赖炸板股池 / 昨日涨停池，后端尚未提供，暂以 -- 占位。
 */

import type { ReactNode } from 'react';
import { MarketStatCard } from '@components/indexCard/MarketStatCards';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { UiTextKey, UiTextParams } from '../../../../i18n/uiText';
import { formatAmount, getBoardCountColor } from '../../../../utils/format';
import type { LimitBoardSummary } from './boardMetrics';

/** 数据不可用时的占位符 */
const VALUE_PLACEHOLDER = '--';

/** 指标卡网格：移动端 2 列 / 平板 3 列 / 桌面 5 列 */
const CARD_GRID_CLASS = 'grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5';

/** i18n 翻译函数类型（与 useUiLanguage 的 t 一致） */
type TranslateFn = (key: UiTextKey, params?: UiTextParams) => string;

export interface LimitBoardIndexCardsProps {
  /** 榜单语义：决定指标取值与连板高度色系 */
  boardType: 'limit-up' | 'limit-down';
  /** 榜单聚合指标 */
  boardSummary: LimitBoardSummary;
  /** 数据加载中：加载态下指标一律展示占位符，避免闪现 0 值 */
  isBoardLoading?: boolean;
}

/** 单张指标卡的渲染配置 */
interface IndexCardItem {
  titleKey: UiTextKey;
  value: ReactNode;
  valueKey: string;
  valueClass?: string;
  meta: ReactNode;
}

/** 连板高度取值：与列表连板列同款亮度递进着色（连板越多色越深，10 板封顶） */
function renderMaxBoardsValue(
  maxBoards: number,
  isBoardLoading: boolean,
  boardType: 'limit-up' | 'limit-down',
  t: TranslateFn,
): ReactNode {
  if (isBoardLoading || maxBoards <= 0) return VALUE_PLACEHOLDER;
  return (
    <span style={{ color: getBoardCountColor(maxBoards, boardType) }}>
      {t('emotion.board.kpi.boardsValue', { count: maxBoards })}
    </span>
  );
}

/** 封单占成交比辅助说明 */
function renderSealRatioMeta(sealAmountRatio: number | null, isBoardLoading: boolean, t: TranslateFn): ReactNode {
  if (isBoardLoading || sealAmountRatio == null) return VALUE_PLACEHOLDER;
  return t('emotion.board.kpi.sealRatio', { ratio: `${sealAmountRatio.toFixed(1)}%` });
}

/** 涨停榜指标卡配置 */
function buildLimitUpCards(t: TranslateFn, boardSummary: LimitBoardSummary, isBoardLoading: boolean): IndexCardItem[] {
  const { boardCount, maxBoards, topBoardStockName, totalSealAmount, sealAmountRatio } = boardSummary;
  const prevDayDelta = t('emotion.board.kpi.prevDayDelta', { delta: VALUE_PLACEHOLDER });

  return [
    {
      titleKey: 'emotion.board.kpi.limitUpCount',
      value: isBoardLoading ? VALUE_PLACEHOLDER : boardCount,
      valueKey: String(boardCount),
      valueClass: 'stock-up',
      meta: prevDayDelta,
    },
    {
      titleKey: 'emotion.board.kpi.maxBoards',
      value: renderMaxBoardsValue(maxBoards, isBoardLoading, 'limit-up', t),
      valueKey: String(maxBoards),
      meta: topBoardStockName ? t('emotion.board.kpi.topBoardStock', { name: topBoardStockName }) : VALUE_PLACEHOLDER,
    },
    {
      titleKey: 'emotion.board.kpi.sealAmount',
      value: isBoardLoading ? VALUE_PLACEHOLDER : formatAmount(totalSealAmount),
      valueKey: String(totalSealAmount),
      meta: renderSealRatioMeta(sealAmountRatio, isBoardLoading, t),
    },
    {
      titleKey: 'emotion.board.kpi.breakRate',
      value: VALUE_PLACEHOLDER,
      valueKey: VALUE_PLACEHOLDER,
      valueClass: 'stock-up',
      meta: prevDayDelta,
    },
    {
      titleKey: 'emotion.board.kpi.previousPremium',
      value: VALUE_PLACEHOLDER,
      valueKey: VALUE_PLACEHOLDER,
      valueClass: 'stock-up',
      meta: prevDayDelta,
    },
  ];
}

/** 跌停榜指标卡配置 */
function buildLimitDownCards(t: TranslateFn, boardSummary: LimitBoardSummary, isBoardLoading: boolean): IndexCardItem[] {
  const { boardCount, maxBoards, topBoardStockName, totalSealAmount, totalTurnoverAmount, sealAmountRatio, avgTurnoverRate } =
    boardSummary;
  const prevDayDelta = t('emotion.board.kpi.prevDayDelta', { delta: VALUE_PLACEHOLDER });

  return [
    {
      titleKey: 'emotion.board.kpi.limitDownCount',
      value: isBoardLoading ? VALUE_PLACEHOLDER : boardCount,
      valueKey: String(boardCount),
      valueClass: 'stock-down',
      meta: prevDayDelta,
    },
    {
      titleKey: 'emotion.board.kpi.maxDownBoards',
      value: renderMaxBoardsValue(maxBoards, isBoardLoading, 'limit-down', t),
      valueKey: String(maxBoards),
      meta: topBoardStockName ? t('emotion.board.kpi.topBoardStock', { name: topBoardStockName }) : VALUE_PLACEHOLDER,
    },
    {
      titleKey: 'emotion.board.kpi.downSealAmount',
      value: isBoardLoading ? VALUE_PLACEHOLDER : formatAmount(totalSealAmount),
      valueKey: String(totalSealAmount),
      meta: renderSealRatioMeta(sealAmountRatio, isBoardLoading, t),
    },
    {
      titleKey: 'emotion.board.kpi.downTurnoverAmount',
      value: isBoardLoading ? VALUE_PLACEHOLDER : formatAmount(totalTurnoverAmount),
      valueKey: String(totalTurnoverAmount),
      meta: prevDayDelta,
    },
    {
      titleKey: 'emotion.board.kpi.avgTurnoverRate',
      value: isBoardLoading || avgTurnoverRate == null ? VALUE_PLACEHOLDER : `${avgTurnoverRate.toFixed(2)}%`,
      valueKey: String(avgTurnoverRate),
      meta: t('emotion.board.kpi.liquidityNote'),
    },
  ];
}

/** 涨跌停榜单 KPI 指标卡组 */
export function LimitBoardIndexCards({ boardType, boardSummary, isBoardLoading = false }: LimitBoardIndexCardsProps) {
  const { t } = useUiLanguage();
  const cards =
    boardType === 'limit-up'
      ? buildLimitUpCards(t, boardSummary, isBoardLoading)
      : buildLimitDownCards(t, boardSummary, isBoardLoading);

  return (
    <div className={CARD_GRID_CLASS}>
      {cards.map((card, ordinal) => (
        <MarketStatCard
          key={card.titleKey}
          ordinal={ordinal}
          title={t(card.titleKey)}
          value={card.value}
          valueKey={card.valueKey}
          valueClass={card.valueClass}
          meta={card.meta}
        />
      ))}
    </div>
  );
}
