/**
 * @file routeRegistry.test.ts
 * @description RouterStore 路由注册单测：验证 registerAsyncRoutes 经 router.patchRoutes('protected', ...)
 *   注入业务路由、addRouteFlag 为 false 时跳过；uninstallAsyncRoutes 清空。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRouterStore } from '../../stores/RouterStore';

// vi.mock 工厂会被提升到文件顶部，其引用变量须用 vi.hoisted 提升，避免 TDZ
const { patchRoutes } = vi.hoisted(() => ({ patchRoutes: vi.fn() }));

vi.mock('../../router/appRouter', () => ({ router: { patchRoutes } }));
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

describe('RouterStore 路由注册', () => {
  it('registerAsyncRoutes：patchRoutes 注入业务路由', () => {
    useRouterStore.getState().registerAsyncRoutes();
    expect(patchRoutes).toHaveBeenCalledWith('protected', expect.any(Array));
    const injected = patchRoutes.mock.calls[0][1] as Array<{ path?: string }>;
    expect(injected.some((r) => r.path === 'home')).toBe(true);
  });

  it('registerAsyncRoutes：addRouteFlag 为 false 时跳过', () => {
    useRouterStore.setState({ addRouteFlag: false });
    useRouterStore.getState().registerAsyncRoutes();
    expect(patchRoutes).not.toHaveBeenCalled();
  });

  it('uninstallAsyncRoutes：patchRoutes 注入空数组', () => {
    useRouterStore.getState().uninstallAsyncRoutes();
    expect(patchRoutes).toHaveBeenCalledWith('protected', []);
  });
});
