/**
 * @file routeRegistry.test.ts
 * @description 路由注册单测：验证 registerAsyncRoutes 经 router.patchRoutes('business', ...)
 *   注入业务路由、addRouteFlag 为 false 时跳过；uninstallAsyncRoutes 清空。
 *   注册逻辑已从 RouterStore 移至 src/router/routeRegistration.ts，故直接测该模块的导出函数。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRouterStore } from '../../stores/RouterStore';
import { registerAsyncRoutes, uninstallAsyncRoutes } from '../routeRegistration';

// vi.mock 工厂会被提升到文件顶部，其引用变量须用 vi.hoisted 提升，避免 TDZ
const { patchRoutes } = vi.hoisted(() => ({ patchRoutes: vi.fn() }));

vi.mock('../appRouter', () => ({ router: { patchRoutes } }));
vi.mock('../asyncRouteFactory', () => ({ buildAsyncRoutes: () => [{ path: 'home' }] }));

const sampleData = vi.hoisted(() =>
  [
    {
      routerKey: 'home',
      routerName: '首页',
      routerPath: '/home',
      routerPagePath: 'pages/Home/HomePage',
      routerType: 'page',
      routerDescription: '',
    },
  ] as unknown[],
);

beforeEach(() => {
  patchRoutes.mockClear();
  useRouterStore.setState({ asyncRouteData: sampleData as never, addRouteFlag: true });
});

describe('路由注册（routeRegistration）', () => {
  it('registerAsyncRoutes：patchRoutes 注入业务路由', () => {
    registerAsyncRoutes();
    expect(patchRoutes).toHaveBeenCalledWith('business', expect.any(Array));
    const injected = patchRoutes.mock.calls[0][1] as Array<{ path?: string }>;
    expect(injected.some((r) => r.path === 'home')).toBe(true);
  });

  it('registerAsyncRoutes：addRouteFlag 为 false 时跳过', () => {
    useRouterStore.setState({ addRouteFlag: false });
    registerAsyncRoutes();
    expect(patchRoutes).not.toHaveBeenCalled();
  });

  it('uninstallAsyncRoutes：patchRoutes 注入空数组', () => {
    uninstallAsyncRoutes();
    expect(patchRoutes).toHaveBeenCalledWith('business', []);
  });
});
