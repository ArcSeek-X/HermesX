/**
 * 情绪面板 - 涨跌榜数据接口。
 * 后端代理东财/akshare 涨停池（/api/v1/emotion/*），前端不直接连外部 API，避免 CORS。
 * 后端返回 snake_case，经 toCamelCase 统一转 camelCase。
 */

import apiClient from './index';
import { toCamelCase } from './utils';
import type { StockLimitUpQuote, StockLimitDownQuote } from '../types/stock';

/**
 * 涨跌停榜单响应。
 * 明细项统一引用 types/stock.ts 的榜单领域类型（单一真源）；
 * UI 行 key `id`（= 股票代码，后端不返回）由页面层行类型承载，不进领域类型（见 stock_type.md §7.1）。
 */
export type LimitUpBoardResponse = {
  /** 查询交易日 YYYYMMDD */
  date: string;
  /** 明细列表 */
  items: StockLimitUpQuote[];
};

/** 跌停榜单响应：字段与涨停榜单同构 */
export type LimitDownBoardResponse = {
  /** 查询交易日 YYYYMMDD */
  date: string;
  /** 明细列表 */
  items: StockLimitDownQuote[];
};

/**
 * 获取涨停榜单。
 * @param date 交易日 YYYYMMDD，省略则取当天
 * @param limit 返回条数上限
 */
export async function fetchLimitUpBoard(date?: string, limit = 100): Promise<LimitUpBoardResponse> {
  const { data } = await apiClient.get('/api/v1/emotion/limit-up-board', {
    params: { date, limit },
  });
  return toCamelCase<LimitUpBoardResponse>(data);
}

/**
 * 获取跌停榜单。
 * @param date 交易日 YYYYMMDD，省略则取当天
 * @param limit 返回条数上限
 */
export async function fetchLimitDownBoard(date?: string, limit = 100): Promise<LimitDownBoardResponse> {
  const { data } = await apiClient.get('/api/v1/emotion/limit-down-board', {
    params: { date, limit },
  });
  return toCamelCase<LimitDownBoardResponse>(data);
}
