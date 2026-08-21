/**
 * hooks 统一出口（barrel file）。
 * 在其它模块中可通过 `import { useAuth, useSystemConfig } from '../hooks'` 集中引入，
 * 避免散落的相对路径 import，便于后续重构目录结构。
 */
export { useAuth } from './useAuth';
export { useStockAutocomplete } from './useStockAutocomplete';
export { useCachedState } from './useCachedState';
export { useDashboardLifecycle } from './useDashboardLifecycle';
export { useHomeDashboardState } from './useHomeDashboardState';
export { usePreference } from './usePreference';
export { useRunFlowSnapshot } from './useRunFlowSnapshot';
export { useStockIndex } from './useStockIndex';
export { useSystemConfig } from './useSystemConfig';
export { useTaskStream } from './useTaskStream';
