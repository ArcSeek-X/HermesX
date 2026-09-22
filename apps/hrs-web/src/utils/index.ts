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
export { normalizeQuery, isChineseChar, containsChinese, extractMarketSuffix, removeMarketSuffix, isStockCodeLike, isStockNameLike, isPinyinLike, normalizeStockCode as normalizeQueryStockCode } from './normalizeQuery';
export * from './portfolioFormat';
export * from './reportLanguage';
export * from './scrollLockCompensation';
export * from './searchStocks';
export * from './sortFilter';
export * from './stockCode';
export * from './stockIndexLoader';
export * from './stockIndexSchema';
export * from './stockList';
export * from './stockName';
export * from './storage';
export * from './systemConfigI18n';
export * from './themeColor';
export * from './uiLanguage';
export * from './uuid';
export * from './validation';
// 撞名说明：normalizeQuery 与 stockCode 都导出 normalizeStockCode。
// 此处对 normalizeQuery 做显式再导出并把其 normalizeStockCode 别名为 normalizeQueryStockCode，
// stockCode 仍走 export *，故 @utils 的 normalizeStockCode 取 stockCode 的实现（规范版本）。
// 注意：normalizeQuery 新增导出需在此处手动补充（已非 export * 自动发现）。
