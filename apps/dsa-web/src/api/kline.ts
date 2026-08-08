import apiClient from './index';

/**
 * K 线（行情）相关 API。
 * 提供股票搜索、K 线数据拉取（支持周期/复权/分页/前向日期游标）、个股基础信息获取，
 * 服务于 K 线图页面。注意前端 KLinePoint 使用驼峰字段，后端为 snake_case，
 * 字段对齐由图表数据层负责。
 */

export type KLinePeriod =
  | '1m' | '5m' | '15m' | '30m' | '60m' | '120m'
  | '5d' | 'daily' | 'weekly' | 'monthly' | 'yearly';

export type KLineAdjustment = 'none' | 'qfq' | 'hfq';

/**
 * 单根 K 线数据点。
 * 字段形态以 KLineChart 实际读取为准（驼峰：open/close/high/low/volume/amount），
 * 与后端 KLinePoint 的蛇形字段（open_price 等）由数据层负责对齐。
 */
export interface KLinePoint {
  date: string;
  open: number | null;
  close: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  amount: number | null;
  change_percent: number | null;
  turnover_rate: number | null;
}

/**
 * K 线接口响应。
 * 注意：KLineChart 通过 `kline.data` 读取点数组，`prev_close` 用于前收价参考。
 */
export interface KLineResponse {
  stock_code?: string;
  stock_name?: string;
  prev_close: number | null;
  data: KLinePoint[];
  count?: number;
  has_more?: boolean;
}

/**
 * 实时信息接口响应（蛇形字段，与 StockInfoHeader 实际读取一致）。
 */
export interface StockInfo {
  stock_code: string;
  stock_name: string;
  current_price: number | null;
  change: number | null;
  change_percent: number | null;
  prev_close: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  amount: number | null;
  turnover_rate: number | null;
  amplitude: number | null;
  pe_ratio_ttm: number | null;
  total_market_cap: number | null;
}

/** 搜索接口单条结果 */
export interface StockSearchResult {
  code: string;
  name: string;
  market?: string;
}

/**
 * K 线页面 API 封装。
 * 三个接口对应后端：
 * - GET /api/v1/kline/{code}/kline   （period / fqt / limit / before_date）
 * - GET /api/v1/kline/{code}/info
 * - GET /api/v1/kline/search?q=
 */
export const klineApi = {
  /**
   * 获取单只股票的 K 线数据。
   * @param code 股票代码
   * @param period K 线周期
   * @param limit 返回条数；全量模式由调用方传入 10000
   * @param beforeDate 分页游标（可选），传上一页第一条 K 线日期以向前翻页
   */
  async fetchKLine(
    code: string,
    period: KLinePeriod = 'daily',
    limit = 500,
    beforeDate: string | null = null,
  ): Promise<KLineResponse> {
    const resp = await apiClient.get<KLineResponse>(`/api/v1/kline/${code}/kline`, {
      params: { period, fqt: 1, limit, before_date: beforeDate || undefined },
    });
    return resp.data;
  },

  /** 获取单只股票的实时行情信息（价格、涨跌幅、指标网格） */
  async fetchStockInfo(code: string): Promise<StockInfo> {
    const resp = await apiClient.get<StockInfo>(`/api/v1/kline/${code}/info`);
    return resp.data;
  },

  /**
   * 按关键词搜索股票代码。
   * 当输入为非纯数字代码（如中文名称）时调用，用于解析出真实代码后再加载 K 线。
   */
  async searchStocks(query: string): Promise<StockSearchResult[]> {
    const resp = await apiClient.get<{ query: string; results: StockSearchResult[] }>(
      '/api/v1/kline/search',
      { params: { q: query } },
    );
    return resp.data.results;
  },
};
