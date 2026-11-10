/**
 * @file types/stockMetricView.ts
 * @description 股票度量视图（Stock Metric View）的前端数据契约集合。
 * 仅描述「一份数据结构」：表格行、筛选条件、查询入参与分页响应，全部为 Def 后缀。
 * 标准股票字段一律从 @/types/stock 的 StockQuoteCore 经 Pick 取得，不重定义、不另起别名；
 * 市场类型仅 import 真源 StockMetricViewSupportedMarket，不在此处重复声明。
 * @author Lensgcx (GaoCangxiong)
 */

import type { StockMetricViewSupportedMarket, StockQuoteCore } from './stock';

/** 重新导出市场收窄类型，供消费方统一从本模块引用（单一入口） */
export type { StockMetricViewSupportedMarket };

/** 标准字段：全部经 Pick 取自 StockQuoteCore（含身份字段），不 extends 全量，避免误带多余字段 */
type StockMetricViewStandardFields = Pick<
  StockQuoteCore,
  | 'code'
  | 'name'
  | 'market'
  | 'industry'
  | 'price'
  | 'changePct'
  | 'volume'
  | 'totalMarketCap'
  | 'peRatioTTM'
>;

/**
 * 度量视图表格行：标准字段 + L3 领域扩展字段（平铺）。
 * - market 仅收窄取值（Omit 后改写为 StockMetricViewSupportedMarket），字段名与真源一致。
 * - industry 沿用 StockIdentity 的 string | undefined 语义（后端 null 由 api 适配层归一）。
 * - id 为 Table 组件泛型约束所需的行键，由 api 适配层按 `market:code` 拼接，非后端字段。
 */
export type StockMetricViewRow = Omit<StockMetricViewStandardFields, 'market'> & {
  /** 行键，用于 Table 渲染与 React key，值为 `${market}:${code}` */
  id: string;
  /** 市场地域，收窄为 cn / hk / us 三者之一 */
  market: StockMetricViewSupportedMarket;
  /** 相对成交量（量比） */
  relativeVolume: number | null;
  /** 摊薄每股收益（当期 EPS，非严格摊薄 TTM） */
  epsDiluted: number | null;
  /** EPS 增长 TTM 同比（百分数），hk / us 为 null */
  epsGrowthTtmYoyPct: number | null;
  /** 股息收益率（百分数） */
  dividendYieldPct: number | null;
  /** 分析师评级档位 1–5，hk / us 为 null */
  analystRating: number | null;
};

/** 可作为筛选 / 排序条件的字段；与后端静态注册表 STOCK_METRIC_FIELDS 的 key 逐字一致 */
export type StockMetricViewFilterField =
  | 'market'
  | 'code'
  | 'price'
  | 'changePct'
  | 'totalMarketCap'
  | 'peRatioTTM'
  | 'dividendYieldPct'
  | 'industry'
  | 'epsGrowthTtmYoyPct'
  | 'roePct'
  | 'pbRatio'
  | 'psRatioTTM'
  | 'revenueGrowthYoyPct';

/** 筛选算子：数值比较 / 区间 / 枚举包含 / 字符串模糊匹配 */
export type StockMetricViewFilterOp =
  | 'eq'
  | 'neq'
  | 'gt'
  | 'gte'
  | 'lt'
  | 'lte'
  | 'between'
  | 'in';

/** 单条筛选条件：field + op + value；market 条件仅允许 in / eq，value 为市场值数组 */
export interface StockMetricViewFilterItem {
  /** 字段名，须来自 StockMetricViewFilterField */
  field: StockMetricViewFilterField;
  /** 算子 */
  op: StockMetricViewFilterOp;
  /** 标量或数组；between 用长度为 2 的数组（允许 null 表示单侧无界），in 用数组 */
  value: number | string | boolean | null | Array<string | number | null>;
}

/** 排序描述：field + 方向 */
export interface StockMetricViewSortDef {
  /** 排序字段，须可排序 */
  field: string;
  /** 排序方向 */
  order: 'asc' | 'desc';
}

/** 查询入参：filterList（含市场条件）+ sort + 分页 */
export interface StockMetricViewQueryDef {
  /** 筛选条件数组，缺省或缺少 market 条件时后端默认按 cn 查询 */
  filterList?: StockMetricViewFilterItem[];
  /** 排序，默认 totalMarketCap desc */
  sort?: StockMetricViewSortDef;
  /** 当前页码，从 1 开始 */
  pageNum?: number;
  /** 每页条数，默认 20，范围 1–100 */
  pageSize?: number;
  /** 手动刷新时跳过服务端在线快照 TTL 缓存，默认 false */
  forceRefresh?: boolean;
}

/** 导出入参：复用筛选 DSL（不含分页），并携带本地化表头与可见列顺序 */
export interface StockMetricViewExportDef {
  /** 筛选条件数组，与 query 同构 */
  filterList?: StockMetricViewFilterItem[];
  /** 排序 */
  sort?: StockMetricViewSortDef;
  /** 前端传入的本地化列名（键为列 key） */
  headers: Record<string, string>;
  /** 当前市场可见列 key 顺序 */
  visibleColumns: string[];
  /** 导出上限，默认 5000 */
  limit?: number;
}

/** 查询响应：继承 watchlist 分页形状，响应字段已为 camelCase */
export interface StockMetricViewResultDef {
  /** 当前页数据（后端已分页），无匹配为 [] */
  list: StockMetricViewRow[];
  /** 命中总数（分页前） */
  total: number;
  /** 每页条数，回显请求值 */
  pageSize: number;
  /** 总页数，total = 0 时为 0 */
  pages: number;
  /** 当前页码，回显请求值 */
  pageNum: number;
  /** 离线因子基准日 */
  asOfDate: string;
  /** 本批在线快照的抓取时刻（ISO 8601 带 UTC 偏移）；无可用在线数据时为空串 */
  quoteAsOf: string;
  /** 口径 / 降级提示 */
  warnings: string[];
  /** 是否降级（因子表不可用，仅实时列） */
  degraded: boolean;
}
