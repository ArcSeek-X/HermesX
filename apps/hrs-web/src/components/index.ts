/**
 * @file index.ts
 * @description components 组件库总出口 barrel：仅聚合 basic 与 common 两个基础/通用目录的组件，
 * 供全项目以 `import { X } from '@components'` 统一消费。
 * ⚠️ 约定：除 basic / common 外的组件（layout / theme / dashboard / sector / kline / watchlist 等）
 * 一律按各自的子路径（如 `@components/layout/Shell`、`@components/theme/ThemeProvider`、`@components/StockSearch/StockSearch`）
 * 直接引入，不进入裸桶——避免桶在入口处提前求值布局组件，触发 appRouter↔Shell 等循环依赖（TDZ）。
 * 别名映射需与 vite.config.ts / vitest.config.ts / tsconfig.app.json 的 @components 保持一致（均已配置）。
 * @author Lensgcx (GaoCangxiong)
 */

// —— 基础层（basic）——
export * from './basic/Index';
export * from './basic/ScrollShadow';
// basic 仅导出了 HrsButton 组件实例，其公开类型 HrsButtonVariant 在此补导出，供外部按桶引用
export type { HrsButtonVariant } from './basic/HrsButton';

// —— 通用层（common，已剔除越界聚合的 layout/theme 组件）——
export * from './common/Index';
