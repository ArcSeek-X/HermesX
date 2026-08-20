/**
 * 通用市场 / 资产类型定义
 *
 * 这些标识（Market / AssetType）属于整个前端项目通用的股票 / 资产语义，
 * 不局限于某一具体业务（如股票索引），故集中在此处统一管理，避免散落到
 * stockIndex 等专用类型文件中导致语义错位、以及各模块自行定义多套互不兼容
 * 的市场表示法。
 */

/** 市场标识（跨项目通用） */
export type Market = 'CN' | 'HK' | 'US' | 'JP' | 'KR' | 'INDEX' | 'ETF' | 'BSE';

/** 资产类型（跨项目通用） */
export type AssetType = 'stock' | 'index' | 'etf';
