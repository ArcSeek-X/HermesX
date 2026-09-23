/**
 * @file routeRegistration.ts
 * @description 业务路由注册：将 RouterStore 持久化的动态路由树（asyncRouteData）经
 *   `router.patchRoutes('business', ...)` 注入受保护布局下的 business 子路由（登录后 / 刷新时），
 *   或登出时以空数组清空。该逻辑从 RouterStore 中剥离为独立模块，使 RouterStore 不再静态依赖
 *   appRouter——否则在「RouterStore 先求值」的入口下会触发 RouterStore↔appRouter 循环依赖崩溃
 *   （appRouter 顶层 `useRouterStore.getState()` 在 useRouterStore 尚未初始化时执行）。
 *
 * 依赖方向（单向，无循环）：
 *   routeRegistration → appRouter（取 router 实例）
 *   routeRegistration → RouterStore（读写 asyncRouteData / addRouteFlag）
 *   appRouter / RouterStore 均不反向依赖本模块。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-22
 */
import { router } from './appRouter';
import { useRouterStore } from '../stores/RouterStore';
import { buildAsyncRoutes } from './asyncRouteFactory';

/**
 * 登录后 / 刷新时：把持久化的动态业务路由树注入受保护布局下的 business 子路由（404 兜底固定在 protected 内，不在此注入）。
 * 已注入则跳过：避免每次导航都重复 patchRoutes 触发受保护布局重渲染。
 */
export const registerAsyncRoutes = (): void => {
  const state = useRouterStore.getState();
  // 已注入则跳过：addRouteFlag 初始为 true；登录重建路由时 buildAsyncRouterData 会重置为 true 以允许再次注入。
  if (!state.addRouteFlag) return;
  router.patchRoutes('business', [...buildAsyncRoutes(state.asyncRouteData)]);
  // 注入完成后置位，后续导航不再重复注入
  useRouterStore.setState({ addRouteFlag: false });
};

/**
 * 登出时：清空受保护布局下的业务路由（业务路由以持久化为权威源，清空即无业务路由）。
 */
export const uninstallAsyncRoutes = (): void => {
  router.patchRoutes('business', []);
  // 清空后逻辑上回到「未注入」状态：重置标记，使下一次 registerAsyncRoutes 能重新注入，
  // 避免依赖 login 流程里 buildAsyncRouterData 的顺手重置（解除隐性耦合）。
  useRouterStore.setState({ addRouteFlag: true });
};
