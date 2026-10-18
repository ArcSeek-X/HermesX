/**
 * @file 股票基础信息 / 市场语义 单一真源类型
 * @description
 *   集中定义股票标识、行情基础字段，以及市场 / 资产 / 交易所的正交枚举。
 *   原 types/market.ts 的扁平 Market 联合已按维度拆分为 MarketLocale / AssetType /
 *   Exchange / StockIndexMarketTag，并整体收口至本文件（详见 documents/types/stock_type.md）。
 *   本文件是依赖图最底层：仅定义类型、不 import 任何上层模块；被 api/*、types/*、pages/*
 *   等各层按精确路径引用，是股票相关字段的唯一真源。
 * @author Lensgcx (GaoCangxiong) - ArcSeek-X
 */

/* ------------------------------------------------------------------ *
 * 市场 / 资产 / 交易所 正交维度（原 types/market.ts 收口于此）
 * ------------------------------------------------------------------ */

/**
 * 市场地域：纯地域维度，不含资产类别 / 交易所。
 * 规范形态为小写，对齐后端契约与 i18n label 后缀（见 stock_type.md §3.1 / §6）。
 */
export type MarketLocale =
  | 'cn' // 中国大陆 A 股（含上交所 / 深交所 / 北交所）
  | 'hk' // 香港
  | 'us' // 美国
  | 'jp' // 日本
  | 'kr' // 韩国
  | 'tw'; // 台湾

/** 资产类型：个股 / 指数 / ETF（承接原扁平 Market 中被污染的 INDEX / ETF 语义） */
export type AssetType =
  | 'stock' // 个股
  | 'index' // 指数
  | 'etf'; // ETF

/** 交易所：隶属于地域之下的细分维度（当前主要用于区分北交所） */
export type Exchange =
  | 'SSE' // 上海证券交易所
  | 'SZSE' // 深圳证券交易所
  | 'BSE'; // 北京证券交易所

/**
 * 搜索索引源数据的原始 market 标记：如实反映上游大小写与取值。
 * 这不是"地域"，而是后端 / 索引用一个扁平字符串承载的"国别 + 交易所 + 资产类别 + 哨兵"。
 * 消费前必须经边界适配层（api / loader）归一化为 MarketLocale / AssetType / Exchange；
 * 标准类型绝不直接使用本类型（见 stock_type.md §3.1 / §6）。
 */
export type StockIndexMarketTag =
  | 'CN' // 地域：中国大陆（原始大写）
  | 'HK' // 地域：香港（原始大写）
  | 'US' // 地域：美国（原始大写）
  | 'JP' // 地域：日本（原始大写）
  | 'KR' // 地域：韩国（原始大写）
  | 'TW' // 地域：台湾（原始大写）
  | 'INDEX' // 资产类别：指数
  | 'ETF' // 资产类别：ETF
  | 'BSE' // 交易所：北交所（隶属 cn）
  | 'UNKNOWN'; // 缺省哨兵（应归一为 undefined，而非地域取值）

/** 各 Feature 支持范围用 Extract 表达：既单一真源，又不为不支持的市场补假 i18n */
export type AlertSupportedMarket = Extract<MarketLocale, 'cn' | 'hk' | 'us'>;
export type MarketReviewSupportedMarket = Extract<MarketLocale, 'cn' | 'hk' | 'us' | 'jp' | 'kr'>;

/* ------------------------------------------------------------------ *
 * 三层模型：L1 标识 → L2 行情核心 → L3 领域扩展
 * ------------------------------------------------------------------ */

/** ①-a 最小标识：必填项不能再多（现有双字段 pair 类型正好满足） */
export interface StockRef {
  /** 股票代码（如 600519） */
  code: string;
  /** 股票名称（中文） */
  name: string;
}

/**
 * ①-b 完整标识：市场 / 资产 / 交易所 / 代码展示形态 / 英文名 / 行业 / 概念。
 * 除 code / name 外全部可选 —— 可选成员不强制下游补齐，轻量引用（如 pair 类型）仍可赋值；
 * 搜索 / 跨市场场景可按需携带。market / assetType / exchange 由 P0 统一后的正交类型引入。
 */
export interface StockIdentity extends StockRef {
  /** 市场地域：纯地域维度，小写规范值（cn/hk/us/jp/kr/tw）；交易所、资产类别不在此处 */
  market?: MarketLocale;
  /** 资产类型：个股 / 指数 / ETF */
  assetType?: AssetType;
  /** 所属交易所（如 BSE），仅需区分交易所的场景使用；北交所呈现为 { market:'cn', exchange:'BSE' } */
  exchange?: Exchange;
  /** 带交易所后缀的规范代码（如 600519.SH），跨市场 / 搜索场景使用 */
  canonicalCode?: string;
  /** 展示用代码（如 600519），用户界面直接显示 */
  displayCode?: string;
  /** 英文名（如 Kweichow Moutai），国际化 / 搜索辅助 */
  nameEn?: string;
  /** 所属行业（完整信息的一部分，如 白酒 / 半导体）；可选，源未提供时由边界适配层补默认值或留空 */
  industry?: string;
  /** 所属概念（完整信息的一部分）：一只股票可同时属于多个概念（如 白酒 / 国企改革 / 基金重仓），故为数组；可选，源未提供时留空 */
  concepts?: string[];
}

/**
 * ② 行情核心层：字段清单 + 含义的唯一真源。
 * 类型层不约束单位（见 stock_type.md §3.1）：字段均为 number，注释中的（元）/（%）仅标注常见来源单位；
 * 实际"亿 / 元"等展示换算交由渲染层 format.ts 与各列定义负责，核心层不承载单位语义。
 */
export interface StockQuoteCore extends StockIdentity {
  /** 最新价（元） */
  price: number | null;
  /** 涨跌额（元） */
  change: number | null;
  /** 涨跌幅（%，1.23 表示 1.23%） */
  changePct: number | null;
  /** 成交额（元） */
  amount: number | null;
  /** 成交量（股） */
  volume: number | null;
  /** 换手率（%） */
  turnoverRate: number | null;
  /** 昨收价（元） */
  prevClose: number | null;
  /** 今开（元） */
  open: number | null;
  /** 最高（元） */
  high: number | null;
  /** 最低（元） */
  low: number | null;
  /** 振幅（%，由来源提供；类型层不约束计算口径） */
  amplitude: number | null;
  /** 市盈率 TTM（倍；来源未提供时为 null） */
  peRatioTTM: number | null;
  /** 总市值（单位由来源决定，渲染层换算；类型层不约束单位） */
  totalMarketCap: number | null;
}

/* ------------------------------------------------------------------ *
 * L3 领域扩展：用 Pick<StockQuoteCore, ...> 精确组合，不 extends 全量
 * ------------------------------------------------------------------ */

/**
 * 涨停榜单：后端返回 7 个通用字段，用 Pick 精确挑选。
 * industry 属股票完整信息，已统一收口至 StockIdentity（经 StockQuoteCore 继承），此处由 Pick 引入。
 */
export interface StockLimitUpQuote
  extends Pick<StockQuoteCore, 'code' | 'name' | 'price' | 'changePct' | 'amount' | 'turnoverRate' | 'industry'> {
  /** 封板资金 / 封单额（元） */
  sealAmount: number | null;
  /** 首次封板时间 HHMMSS，无值返回空串 */
  firstLimitTime: string;
  /** 最后封板时间 HHMMSS */
  lastLimitTime: string;
  /** 炸板次数 */
  breakCount: number | null;
  /** 涨停统计（如 '3/2'，表示 2 天内涨停 3 次） */
  limitStat: string;
  /** 连板数（1 = 首板） */
  consecutiveBoards: number | null;
}
