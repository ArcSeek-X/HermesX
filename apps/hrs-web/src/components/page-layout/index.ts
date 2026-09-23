/**
 * @file index.ts
 * @description 页面布局相关组件的统一出口 barrel：re-export 本目录组件（PageHeader / EmptyState 等），
 * 供上层按 `@components/page-layout/...` 子路径直接消费。
 * ⚠️ 遵循仓库约定：非 basic / common 的组件（layout / theme 等）不进入裸桶 `@components`，
 * 一律按子路径引入，避免桶在入口处提前求值布局组件，触发 appRouter↔Shell 等循环依赖（TDZ）。
 * @author Lensgcx (GaoCangxiong)
 */

export * from './PageHeader';
export * from './EmptyState';
