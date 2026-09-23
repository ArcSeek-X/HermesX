/**
 * @file Index.ts
 * @description 通用组件层（common）的统一出口 barrel：re-export 本目录通用组件，
 * 供上层通过 `src/components/index.ts` 聚合后统一消费。
 * ⚠️ 仅聚合 common 目录内组件；layout / theme 组件（AppPage / Shell / ShellHeader /
 * ThemeProvider / ThemeToggle / LanguageSwitch / SidebarNavOld）不在此聚合——否则会经裸桶
 * 在入口处提前求值布局组件，触发 appRouter↔Shell 循环依赖（Shell 进入 TDZ）。它们按各自的
 * 子路径（如 `@components/layout/Shell`、`@components/theme/ThemeProvider`）直接引入。
 * @author Lensgcx (GaoCangxiong)
 */
export * from './Card';
export * from './LiveCalendar';
export * from './SectionCard';
export * from './EmptyState';
export * from './InlineAlert';
export * from './StickyActionBar';
export * from './ToastViewport';
export * from './PageHeader';
export * from './EyeToggleIcon';
export * from './Drawer';
export * from './ScrollArea';
export * from './InlineTipCard';
export * from './Collapsible';
export * from './ScoreGauge';
export * from './JsonViewer';
export * from './StatusDot';
export * from './Pagination';
export * from './ConfirmDialog';
export * from './DataRefreshBar';
export * from './TabNav';
export * from './ParticleBackground';
