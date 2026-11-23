import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getStorageItem, setStorageItem } from '../../utils/storage';
import type { ModuleMenuData, NavMenuNode } from '../../types/moduleMenu';

const { manifest } = vi.hoisted(() => ({ manifest: [] as unknown[] }));
vi.mock('../../router/manifest', () => ({
  MENU_MANIFEST: manifest,
  MENU_MANIFEST_FINGERPRINT: 'current-manifest',
}));

const node = (menuCode: string, overrides: Partial<NavMenuNode> = {}): NavMenuNode => ({
  menuCode,
  menuName: menuCode,
  menuDescription: '',
  menuType: 'page',
  menuPosition: 'content',
  menuExpanded: false,
  menuVisible: true,
  menuSort: 0,
  menuStatus: 1,
  menuRoutePath: `/${menuCode}`,
  menuPagePath: 'pages/HomePage',
  auth: 'protected',
  ...overrides,
});

beforeEach(() => {
  vi.resetModules();
  localStorage.clear();
  manifest.splice(0, manifest.length,
    node('products', {
      menuType: 'module',
      children: [node('stock', { menuType: 'group', children: [node('kline')] }), node('watchlist')],
    }),
    node('debug', { menuType: 'module', menuSort: 1, children: [node('docs')] }),
  );
});
afterEach(() => localStorage.clear());

describe('菜单与路由统一节点集成', () => {
  it('模块选择、节点字段和模块切换都使用 menuCode，刷新后恢复同一树', async () => {
    const { useMenuStore } = await import('../MenuStore');
    useMenuStore.getState().buildMenuData('products');
    expect(useMenuStore.getState().currentModuleCode).toBe('products');
    expect(useMenuStore.getState().menuData.products).toMatchObject({
      menuCode: 'products', menuName: 'products', menuType: 'module',
    });
    expect(useMenuStore.getState().currentMenuData.map((n) => n.menuCode)).toEqual(['stock', 'watchlist']);
    const stored = getStorageItem<{ fingerprint: string; modules: ModuleMenuData }>('menu.menuData', 'local');
    expect(stored?.fingerprint).toBe('current-manifest');
    useMenuStore.getState().setCurrentModuleCode('debug');
    expect(useMenuStore.getState().currentMenuData[0].menuCode).toBe('docs');
    expect(getStorageItem('menu.menuData', 'local')).toEqual(stored);
    vi.resetModules();
    const restored = (await import('../MenuStore')).useMenuStore.getState();
    expect(restored.currentModuleCode).toBe('debug');
    expect(restored.currentMenuData[0].menuCode).toBe('docs');
  });

  it('路由只由 page 生成，module/group 的路由字段不会抢占页面', async () => {
    const { useRouterStore } = await import('../RouterStore');
    useRouterStore.getState().buildAsyncRouterData();
    expect(useRouterStore.getState().asyncRouteData.map((n) => n.routerKey)).toEqual(['kline', 'watchlist', 'docs']);
    expect(useRouterStore.getState().asyncRouteData[0]).toMatchObject({
      routerPath: '/kline', routerName: 'kline', routerPagePath: 'pages/HomePage', auth: 'protected',
    });
    vi.resetModules();
    expect((await import('../RouterStore')).useRouterStore.getState().asyncRouteData).toHaveLength(3);
  });

  it('同级按 menuSort 排序；隐藏分组透传子项，隐藏页面保留直达路由，禁用子树同时剔除', async () => {
    manifest.splice(0, manifest.length, node('products', { menuType: 'module', children: [
      node('last', { menuSort: 9 }),
      node('hidden-group', { menuType: 'group', menuSort: 1, menuVisible: false, children: [node('promoted')] }),
      node('hidden-page', { menuVisible: false, menuSort: 2 }),
      node('disabled-group', { menuType: 'group', menuStatus: 0, children: [node('disabled-child')] }),
      node('disabled-page', { menuStatus: 0 }),
    ] }), node('disabled-module', { menuType: 'module', menuStatus: 0, children: [node('disabled-module-child')] }));
    const { useMenuStore } = await import('../MenuStore');
    const { useRouterStore } = await import('../RouterStore');
    useMenuStore.getState().buildMenuData();
    useRouterStore.getState().buildAsyncRouterData();
    expect(Object.keys(useMenuStore.getState().menuData)).toEqual(['products']);
    expect(useMenuStore.getState().currentMenuData.map((n) => n.menuCode)).toEqual(['promoted', 'last']);
    expect(useRouterStore.getState().asyncRouteData.map((n) => n.routerKey)).toEqual(['promoted', 'hidden-page', 'last']);
  });

  it('无效或空模块回退到第一个可用模块，不使用数据库数字主键选模块', async () => {
    manifest.unshift(node('empty', { menuType: 'module', menuSort: -1, children: [] }));
    const { useMenuStore } = await import('../MenuStore');
    useMenuStore.getState().buildMenuData('empty');
    expect(useMenuStore.getState().currentModuleCode).toBe('products');
    useMenuStore.getState().setCurrentModuleCode('missing');
    expect(useMenuStore.getState().currentModuleCode).toBe('products');
    manifest.length = 0;
    useMenuStore.getState().buildMenuData();
    expect(useMenuStore.getState().currentModuleCode).toBe('');
    expect(useMenuStore.getState().currentMenuData).toEqual([]);
  });

  it.each(['legacy', 'stale'])('拒绝 %s 菜单和路由缓存，登录后重建统一格式', async (format) => {
    setStorageItem('menu.menuData', format === 'legacy'
      ? { products: { moduleId: 'products', children: [{ menuId: 'old' }] } }
      : { fingerprint: 'old-manifest', modules: { products: node('old') } }, 'local');
    setStorageItem('menu.currentModuleId', 'products', 'local');
    setStorageItem('router.asyncRouteData', { fingerprint: 'old-manifest', routes: [{ routerKey: 'old' }] }, 'local');
    const { useMenuStore } = await import('../MenuStore');
    const { useRouterStore } = await import('../RouterStore');
    expect(useMenuStore.getState().menuData).toEqual({});
    expect(useMenuStore.getState().currentMenuData).toEqual([]);
    expect(useRouterStore.getState().asyncRouteData).toEqual([]);
    useMenuStore.getState().buildMenuData();
    useRouterStore.getState().buildAsyncRouterData();
    expect(useMenuStore.getState().currentModuleCode).toBe('products');
    expect(useRouterStore.getState().asyncRouteData.map((n) => n.routerKey)).toContain('watchlist');
  });
});
