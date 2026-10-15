// 全量桶：统一从 '@utils' 引入，无需关心具体文件。
// 使用 `export *` 以兼容 verbatimModuleSyntax 并保留类型/值的正确再导出（生产环境会被 Rollup tree-shake）。
export * from './animate';
export * from './apiCache';
export * from './chatExport';
export * from './chatFollowUp';
export * from './chatScroll';
export * from './chatStockCode';
export * from './cn';
export * from './constants';
export * from './copypaste';
export * from './decisionAction';
export * from './decisionSignalLabels';
export * from './decisionSignalProfile';
export * from './decisionSignalTime';
export * from './decisionSignalTimeline';
export * from './format';
export * from './markdown';
export * from './marketPhase';
export * from './marketReviewRegion';
export { normalizeQuery, isChineseChar, containsChinese, extractMarketSuffix, removeMarketSuffix, isStockCodeLike, isStockNameLike, isPinyinLike, normalizeQueryStockCode } from './normalizeQuery';
export * from './portfolioFormat';
export * from './reportLanguage';
export * from './scrollLockCompensation';
export * from './searchStocks';
export * from './sortFilter';
export * from './stock/stockCode';
export * from './stockIndexLoader';
export * from './stockIndexSchema';
export * from './stockList';
export * from './stock/stockNameDisplay';
export * from './storage';
export * from './systemConfigI18n';
export * from './themeColor';
export * from './uiLanguage';
export * from './uuid';
export * from './validation';
// 名称区分：查询路径规范化保留后缀（normalizeQueryStockCode），与 stockCode.normalizeStockCode（剥离后缀）语义相反，
// 二者用不同导出名，避免“同名不同义”。@utils 的 normalizeStockCode 即 stockCode 的规范版（剥离后缀）。
// 注意：normalizeQuery 新增导出需在此处手动补充（已非 export * 自动发现）。
