/**
 * @file index.ts
 * @description 页面布局相关组件的统一出口 barrel：re-export 本仓库布局组件（PageHeader / EmptyState 等）。
 * 实际实现已迁移至 `components/layout/PageLayout`、`components/layout/Empty`，此处仅做兼容 re-export，
 * 供上层继续按 `@components/page-layout/...` 子路径直接消费，避免批量改动既有引用。
 * ⚠️ 遵循仓库约定：非 basic / common 的组件（layout / theme 等）不进入裸桶 `@components`，
 * 一律按子路径引入，避免桶在入口处提前求值布局组件，触发 appRouter↔Shell 等循环依赖（TDZ）。
 * @author Lensgcx (GaoCangxiong)
 */

export * from '../layout/PageLayout/PageHeader';
export * from '../layout/Empty/EmptyState';
