/**
 * 板块数据 API - 通过后端代理调用申万行业分类等外部接口，避免前端直连外部 API 的 CORS 问题。
 * 提供行业/概念板块树形与扁平数据、板块成分股、个股/ETF/概念云图、市场指数与市场概览等能力，
 * 主要服务于板块热力图（treemap）、资金流向与大盘概览页面。
 */

import apiClient from './index';

/** 树形板块节点（支持层级 treemap） */
export type SectorNode = {
  code: string;
  name: string;
  value: number;
  changePercent: number;
  riseCount: number;
  fallCount: number;
  children?: SectorNode[];
  itemStyle?: {
    color?: string;
    borderColor?: string;
    borderWidth?: number;
  };
  label?: {
    show?: boolean;
    formatter?: string;
  };
};

/** 扁平板块项（用于统计卡片） */
export type SectorItem = {
  code: string;
  name: string;
  changePercent: number;
  totalMarketCap: number;
  riseCount: number;
  fallCount: number;
  leaderStock: string;
};

export type StockItem = {
  code: string;
  name: string;
  price: number;
  changePercent: number;
  changeAmount: number;
  volume: number;
  turnover: number;
  amplitude: number;
  high: number;
  low: number;
  open: number;
  prevClose: number;
  totalMarketCap: number;
  turnoverRate: number;
  pe: number;
  pb: number;
};

export type SectorStocksResponse = {
  total: number;
  stocks: StockItem[];
};

/** 获取行业板块树形数据（一级行业包含二级行业子节点） */
export async function fetchIndustryTree(time?: string): Promise<{ sectors: SectorNode[]; snapshotTime: string | null }> {
  const response = await apiClient.get('/api/v1/sector/industry', {
    params: time ? { time } : {},
  });
  return { sectors: response.data.sectors, snapshotTime: response.data.snapshotTime || null };
}

/** 获取行业板块扁平列表（向后兼容） */
export async function fetchIndustrySectors(): Promise<SectorItem[]> {
  const response = await apiClient.get('/api/v1/sector/industry');
  return response.data.sectors;
}

export async function fetchConceptSectors(): Promise<SectorItem[]> {
  const response = await apiClient.get('/api/v1/sector/concept');
  return response.data.sectors;
}

export async function fetchSectorStocks(
  sectorCode: string,
  sectorType: 'industry' | 'concept' = 'industry'
): Promise<SectorStocksResponse> {
  const response = await apiClient.get(`/api/v1/sector/${sectorCode}/stocks`, {
    params: { sector_type: sectorType },
  });
  return response.data;
}

/** 获取个股云图数据（三级树：行业→子行业→个股） */
export async function fetchStockCloudMap(time?: string): Promise<{ sectors: SectorNode[]; snapshotTime: string | null }> {
  const response = await apiClient.get('/api/v1/sector/stock-map', {
    params: time ? { time } : {},
  });
  return { sectors: response.data.sectors, snapshotTime: response.data.snapshotTime || null };
}

/** ETF 涨跌幅周期 */
export type ETFPeriod = 'yesterday' | 'week' | 'month' | 'quarter' | 'half_year' | 'ytd' | 'year' | 'three_year';

/** ETF 周期中文标签 */
export const ETF_PERIOD_LABELS: Record<ETFPeriod, string> = {
  yesterday: '昨日涨跌幅',
  week: '近一周',
  month: '近一月',
  quarter: '近三月',
  half_year: '近半年',
  ytd: '今年以来',
  year: '近一年',
  three_year: '近三年',
};

/** 获取 ETF 云图数据（扁平列表，按市值排序） */
export async function fetchETFCloudMap(
  period: ETFPeriod = 'yesterday',
  topN: number = 100,
): Promise<{ sectors: SectorNode[]; period: ETFPeriod; periodLabel: string }> {
  const response = await apiClient.get('/api/v1/sector/etf-map', {
    params: { period, top_n: topN },
  });
  return {
    sectors: response.data.sectors,
    period: response.data.period,
    periodLabel: response.data.periodLabel,
  };
}

/** 获取概念云图数据（扁平列表，按市值排序） */
export async function fetchConceptCloudMap(
  period: ETFPeriod = 'yesterday',
  topN: number = 100,
): Promise<{ sectors: SectorNode[]; period: ETFPeriod; periodLabel: string }> {
  const response = await apiClient.get('/api/v1/sector/concept-map', {
    params: { period, top_n: topN },
  });
  return {
    sectors: response.data.sectors,
    period: response.data.period,
    periodLabel: response.data.periodLabel,
  };
}

/** 市场指数项 */
export type MarketIndexItem = {
  name: string;
  code: string;
  price: number | null;
  changePercent: number | null;
};

/** 获取市场指数数据 */
export async function fetchMarketIndices(): Promise<MarketIndexItem[]> {
  const response = await apiClient.get('/api/v1/sector/market-indices');
  return response.data.indices;
}

/** 市场概览数据（涨跌家数 + 量能） */
export type MarketOverviewData = {
  riseCount: number;
  fallCount: number;
  flatCount: number;
  totalAmount: number;
  volumeRatio: number | null; // 量比（相较于昨日同时刻成交额），null 表示无数据
  yesterdayAmount: number; // 昨日成交额（元）
  volumeChange: number; // 放量/缩量金额（元，正=放量，负=缩量）
};

/** 获取市场概览数据（涨跌家数 + 成交额） */
export async function fetchMarketOverview(): Promise<MarketOverviewData> {
  const response = await apiClient.get('/api/v1/sector/market-overview');
  return response.data;
}

