/**
 * 简体中文（zh）文案：数据源 dataSource 类别。
 * 由 uiText-zh.ts 按类别拆分，经 uiText-zh/index.ts 聚合；key 与三语主字典保持一致。
 */

export const dataSourceZh = {
  // ---- 数据源 dataSource（跨组件领域定义，见 constants/dataSource.ts） ----
  'dataSource.eastmoney': '东方财富', // 数据源：东财直连
  'dataSource.tencent': '腾讯', // 数据源：腾讯
  'dataSource.sina': '新浪', // 数据源：新浪
  'dataSource.xueqiu': '雪球', // 数据源：雪球
  'dataSource.stocksdk': 'stock-sdk', // 数据源：stock-sdk 兜底
  'dataSource.stockdb': 'StockDB', // 数据源：本地 StockDB
} as const;
