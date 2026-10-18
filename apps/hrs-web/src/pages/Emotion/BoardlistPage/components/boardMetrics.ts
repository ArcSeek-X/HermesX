/**
 * @file boardMetrics.ts
 * @description 涨跌停榜单词局指标：涨停池与跌停池字段同构（东财双接口经后端归一），
 *   聚合逻辑通用。炸板率、昨日涨停溢价等依赖额外股池的指标不在此聚合，由指标卡层占位。
 */

import type { LimitBoardQuote } from '../../../../types/stock';

/** 涨跌停榜单词局指标（金额单位：元；比率单位：%） */
export interface LimitBoardSummary {
  /** 榜单家数（涨停 / 跌停数量） */
  boardCount: number;
  /** 最高连板数（跌停榜表示连续跌停次数），0 表示无数据 */
  maxBoards: number;
  /** 最高连板标的名称，无数据为 null */
  topBoardStockName: string | null;
  /** 封单总额（元） */
  totalSealAmount: number;
  /** 榜单个股成交总额（元） */
  totalTurnoverAmount: number;
  /** 封单占成交比（%），无成交额时为 null */
  sealAmountRatio: number | null;
  /** 平均换手率（%），无数据为 null */
  avgTurnoverRate: number | null;
}

/** 由涨停 / 跌停池聚合 KPI 指标 */
export function summarizeLimitBoard(items: LimitBoardQuote[]): LimitBoardSummary {
  let maxBoards = 0;
  let topBoardStockName: string | null = null;
  let totalSealAmount = 0;
  let totalTurnoverAmount = 0;
  let turnoverRateSum = 0;
  let turnoverRateCount = 0;

  for (const item of items) {
    const boards = item.consecutiveBoards ?? 0;
    if (boards > maxBoards) {
      maxBoards = boards;
      topBoardStockName = item.name;
    }
    totalSealAmount += item.sealAmount ?? 0;
    totalTurnoverAmount += item.amount ?? 0;
    if (item.turnoverRate != null) {
      turnoverRateSum += item.turnoverRate;
      turnoverRateCount += 1;
    }
  }

  return {
    boardCount: items.length,
    maxBoards,
    topBoardStockName,
    totalSealAmount,
    totalTurnoverAmount,
    sealAmountRatio: totalTurnoverAmount > 0 ? (totalSealAmount / totalTurnoverAmount) * 100 : null,
    avgTurnoverRate: turnoverRateCount > 0 ? turnoverRateSum / turnoverRateCount : null,
  };
}
