import apiClient from './index';
import type { StockQuoteCore } from '../types/stock';

/**
 * K 线（行情）相关 API。
 * 提供股票搜索、K 线数据拉取（支持周期/复权/分页/前向日期游标）、个股基础信息获取，
 * 服务于 K 线图页面。/info 响应已由后端按规范 camelCase 输出；K 线序列的
 * snake_case 字段仍由图表数据层按 KLinePoint 契约对齐。
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
  source?: string | null;
  data: KLinePoint[];
  count?: number;
  has_more?: boolean;
}

/**
 * 实时信息接口响应：字段名与 `StockQuoteCore` 规范 camelCase 完全一致，
 * 另含行情快照时间与数据源标识。页面与 UI 层直接消费，无需边界重命名适配。
 */
export type StockInfo = StockQuoteCore & {
  /** 行情快照时间；后端当前固定为 null */
  updateTime?: string | null;
  /** 实际命中的数据源标识 */
  source?: string | null;
};

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
   * @param fqt 复权模式：0=不复权，1=前复权，2=后复权
   */
  async fetchKLine(
    code: string,
    period: KLinePeriod = 'daily',
    limit = 500,
    beforeDate: string | null = null,
    fqt = 1,
  ): Promise<KLineResponse> {
    const resp = await apiClient.get<KLineResponse>(`/api/v1/kline/${code}/kline`, {
      params: { period, fqt, limit, before_date: beforeDate || undefined },
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
