/** 最近搜索卡片的数据契约与占位行情构造（页面、列表、卡片共用） */

import type { KLinePoint, StockInfo } from '../../../../api/kline';

/** 最近搜索卡片数据：行情快照 + 迷你分时（分时由批量接口异步补齐） */
export interface RecentSearchStockCardData {
  /** 行情快照，含名称 / 代码 / 价格 / 指标 */
  stockQuote: StockInfo;
  /** 当日分时缩略数据，未到位时为空数组 */
  timeline: KLinePoint[];
  /** 分时昨收基准价：优先批量分时，其次行情前收 */
  prevClose: number | null;
}

/** 构造无行情的占位快照；批量行情缺失与加载占位卡片共用 */
export function createEmptyStockQuote(stockCode = '--', stockName = '--'): StockInfo {
  return {
    code: stockCode,
    name: stockName,
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
  };
}
