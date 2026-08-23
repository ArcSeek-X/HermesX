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

/** 板块卡片列表项（用于板块 TAB 卡片展示） */
export type BoardListItem = {
  /** 排名 */
  rank: number;
  /** 板块代码 */
  code: string;
  /** 板块名称 */
  name: string;
  /** 涨跌幅（%） */
  changePercent: number;
  /** 总市值（亿） */
  totalMarketCap: number;
  /** 换手率（%） */
  turnoverRate: number;
  /** 板块内上涨个股数 */
  riseCount: number;
  /** 板块内下跌个股数 */
  fallCount: number;
};

/** 板块卡片列表响应 */
export type BoardListResponse = {
  sectorType: 'industry' | 'concept';
  total: number;
  boards: BoardListItem[];
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
/** 获取板块卡片列表（行业/概念） */
export async function fetchBoardList(
  sectorType: 'industry' | 'concept' = 'industry',
): Promise<BoardListResponse> {
  const response = await apiClient.get('/api/v1/sector/board-list', {
    params: { sector_type: sectorType },
  });
  return response.data;
}

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
  /** 涨跌点数 */
  change: number | null;
  /** 成交额（元） */
  amount: number | null;
  /** 当日最高价 */
  high: number | null;
  /** 当日最低价 */
  low: number | null;
  /** 昨收价 */
  preClose: number | null;
};

/** 获取市场指数数据 */
export async function fetchMarketIndices(): Promise<MarketIndexItem[]> {
  const response = await apiClient.get('/api/v1/sector/market-indices');
  return response.data.indices;
}

/** 获取欧美股主要指数数据（market=us：道琼斯、标普500、纳斯达克、纳指金龙中国等） */
export async function fetchGlobalIndices(): Promise<MarketIndexItem[]> {
  const response = await apiClient.get('/api/v1/sector/market-indices', {
    params: { market: 'us' },
  });
  return response.data.indices;
}

/** 获取日韩主要指数数据（market=jp-kr：日经指数、韩国综指、韩国KOSDAQ） */
export async function fetchAsiaIndices(): Promise<MarketIndexItem[]> {
  const response = await apiClient.get('/api/v1/sector/market-indices', {
    params: { market: 'jp-kr' },
  });
  return response.data.indices;
}

/** 市场概览数据（涨跌家数 + 量能） */
export type MarketOverviewData = {
  riseCount: number;
  fallCount: number;
  flatCount: number;
  totalAmount: number;
  volumeRatio: number | null; // 量比（相较于昨日同时刻成交额），null 表示无数据
  limitUpCount: number; // 涨停家数（按板块涨跌幅限制精确判断）
  limitDownCount: number; // 跌停家数
};

/** 获取市场概览数据（涨跌家数 + 成交额） */
export async function fetchMarketOverview(): Promise<MarketOverviewData> {
  const response = await apiClient.get('/api/v1/sector/market-overview');
  return response.data;
}

/** 北向资金（沪深港通）净流入数据 */
export type NorthboundFlowData = {
  /** 净流入（元），2024-08 后北向实时数据停披露，可能为 null */
  netInflow: number | null;
  name: string | null;
  /** 数据日期 */
  date: string | null;
  /** 上涨家数（北向资金分类汇总；后端暂未返回，渲染为占位符） */
  riseCount?: number | null;
  /** 下跌家数（北向资金分类汇总；后端暂未返回，渲染为占位符） */
  fallCount?: number | null;
};

/** 获取北向资金数据 */
export async function fetchNorthboundFlow(): Promise<NorthboundFlowData> {
  const response = await apiClient.get('/api/v1/sector/northbound-flow');
  return response.data;
}

/** 大盘主力资金净流入数据 */
export type MarketFundFlowData = {
  /** 主力净流入（元） */
  mainNetInflow: number | null;
  /** 主力净流入占比（%） */
  mainNetInflowPercent: number | null;
  /** 数据日期（最近一个交易日） */
  date: string | null;
};

/** 获取大盘主力资金数据 */
export async function fetchMarketFundFlow(): Promise<MarketFundFlowData> {
  const response = await apiClient.get('/api/v1/sector/market-fund-flow');
  return response.data;
}

/** 板块资金流历史 - 单个板块序列 */
export type SectorFundFlowSeries = {
  code: string;
  name: string;
  /** 每日主力净流入（亿），null 表示该日无数据 */
  series: (number | null)[];
  /** 最新一日主力净流入（亿） */
  latest: number | null;
  /** 折线颜色 */
  color: string;
};

/** 板块资金流历史 - 响应结构 */
export type SectorFundFlowResponse = {
  /** 日期数组 */
  dates: string[];
  /** 各板块资金流序列 */
  sectors: SectorFundFlowSeries[];
};

/** 获取板块资金流历史（日线，主力净流入） */
export async function fetchSectorFundFlowHistory(params?: {
  sectorType?: 'industry' | 'concept';
  limit?: number;
  topN?: number;
  sectorCodes?: string[];
}): Promise<SectorFundFlowResponse> {
  const response = await apiClient.get('/api/v1/sector/fund-flow-history', {
    params: {
      sector_type: params?.sectorType ?? 'industry',
      limit: params?.limit ?? 30,
      top_n: params?.topN ?? 10,
      sector_codes: params?.sectorCodes?.join(',') ?? undefined,
    },
  });
  return response.data;
}

/** 板块资金流可选板块列表项 */
export type SectorFundFlowSectorItem = {
  code: string;
  name: string;
};

/** 获取板块资金流可选板块列表 */
export async function fetchSectorFundFlowSectorList(
  sectorType: 'industry' | 'concept' = 'industry',
): Promise<SectorFundFlowSectorItem[]> {
  const response = await apiClient.get('/api/v1/sector/fund-flow-sectors', {
    params: { sector_type: sectorType },
  });
  return response.data.sectors;
}

