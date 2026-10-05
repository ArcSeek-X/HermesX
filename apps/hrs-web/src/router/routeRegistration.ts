/**
 * @file routeRegistration.ts
 * @description 业务路由注册：将 RouterStore 持久化的动态路由树（asyncRouteData）经
 *   `router.patchRoutes('business', ...)` 注入受保护布局下的 business 子路由（登录后 / 刷新时），
 *   或登出时以空数组清空。该逻辑从 RouterStore 中剥离为独立模块，使 RouterStore 不再静态依赖 appRouter。
 *
 * 依赖方向（单向，无循环）：
 *   appRouter → routeRegistration（仅取 `attachRouter` 注入 router 实例，调用时机在 appRouter 模块求值末尾）
 *   routeRegistration → RouterStore（读写 asyncRouteData / addRouteFlag）
 *   routeRegistration → asyncRouteFactory（构建路由对象）
 *   routeRegistration 不反向依赖 appRouter / RouterStore / asyncRouteFactory。
 *
 * 解耦说明：router 实例由 appRouter 在 `createBrowserRouter(...)` 之后通过 `attachRouter(router)` 反向注入本模块，
 * 而非本模块 `import { router } from './appRouter'` 静态取值——后者会使
 * appRouter → LoginPage → LoginCard → routeRegistration → appRouter 形成闭环（routeRegistration 顶层虽仅函数体内
 * 引用 router，但静态依赖图已闭环，属最脆弱的一环）。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-22
 */
import type { createBrowserRouter } from 'react-router-dom';
import { useRouterStore } from '../stores/RouterStore';
import { buildAsyncRoutes } from './asyncRouteFactory';

/** appRouter 创建 router 实例后回注，解除 routeRegistration → appRouter 的静态反向依赖（避免循环依赖） */
type AppRouter = ReturnType<typeof createBrowserRouter>;
let routerRef: AppRouter | null = null;
export const attachRouter = (router: AppRouter): void => {
  routerRef = router;
};

/**
 * 登录后 / 刷新时：把持久化的动态业务路由树注入受保护布局下的 business 子路由（404 兜底固定在 protected 内，不在此注入）。
 * 已注入则跳过：避免每次导航都重复 patchRoutes 触发受保护布局重渲染。
 */
export const registerAsyncRoutes = (): void => {
  const state = useRouterStore.getState();
  // 已注入则跳过：addRouteFlag 初始为 true；登录重建路由时 buildAsyncRouterData 会重置为 true 以允许再次注入。
  if (!state.addRouteFlag) return;
  // router 由 appRouter 经 attachRouter 注入；未注入前（理论上不会在此路径触发）安全跳过
  routerRef?.patchRoutes('business', [...buildAsyncRoutes(state.asyncRouteData)]);
  // 注入完成后置位，后续导航不再重复注入
  useRouterStore.setState({ addRouteFlag: false });
};

/**
 * 登出时：清空受保护布局下的业务路由（业务路由以持久化为权威源，清空即无业务路由）。
 */
export const uninstallAsyncRoutes = (): void => {
  routerRef?.patchRoutes('business', []);
  // 清空后逻辑上回到「未注入」状态：重置标记，使下一次 registerAsyncRoutes 能重新注入，
  // 避免依赖 login 流程里 buildAsyncRouterData 的顺手重置（解除隐性耦合）。
  useRouterStore.setState({ addRouteFlag: true });
};
