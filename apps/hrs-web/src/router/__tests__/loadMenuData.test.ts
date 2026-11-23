import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { NavMenuNode } from '../../types/moduleMenu';
import { getStorageItem } from '../../utils/storage';

const source = vi.hoisted(() => ({ staticMenu: true, nodes: [] as NavMenuNode[], getTree: vi.fn() }));
vi.mock('../manifest', () => ({
  get USE_STATIC_MENU() { return source.staticMenu; },
  MENU_MANIFEST: source.nodes,
  MENU_MANIFEST_FINGERPRINT: 'test-manifest',
}));
vi.mock('../../api/system/menu', () => ({ menuApi: { getTree: source.getTree } }));

function tree(code: string): NavMenuNode[] {
  const common = { menuDescription: '', menuPosition: 'content' as const, menuExpanded: false,
    menuVisible: true, menuSort: 0, menuStatus: 1 as const };
  return [{ ...common, menuCode: code, menuName: code, menuType: 'module', children: [
    { ...common, menuCode: `${code}-page`, menuName: code, menuType: 'page',
      menuRoutePath: `/${code}`, menuPagePath: 'pages/HomePage' },
  ] }];
}

beforeEach(() => {
  vi.resetModules();
  localStorage.clear();
  source.staticMenu = true;
  source.nodes.splice(0, source.nodes.length, ...tree('static'));
  source.getTree.mockReset();
});

async function setup() {
  const { loadMenuData } = await import('../loadMenuData');
  const { useMenuStore } = await import('../../stores/MenuStore');
  const { useRouterStore } = await import('../../stores/RouterStore');
  return { loadMenuData, useMenuStore, useRouterStore };
}

describe('开发调试菜单数据源开关', () => {
  it('开启时从 manifest 同时构建菜单与路由，不请求接口', async () => {
    const { loadMenuData, useMenuStore, useRouterStore } = await setup();
    await loadMenuData();
    expect(source.getTree).not.toHaveBeenCalled();
    expect(Object.keys(useMenuStore.getState().menuData)).toEqual(['static']);
    expect(useRouterStore.getState().asyncRouteData[0].routerPath).toBe('/static');
  });

  it('关闭时只请求一次 API，将返回的同一份节点用于菜单与路由', async () => {
    source.staticMenu = false;
    source.getTree.mockResolvedValue(tree('remote'));
    const { loadMenuData, useMenuStore, useRouterStore } = await setup();
    await loadMenuData();
    expect(source.getTree).toHaveBeenCalledTimes(1);
    expect(Object.keys(useMenuStore.getState().menuData)).toEqual(['remote']);
    expect(useMenuStore.getState().currentMenuData[0].menuCode).toBe('remote-page');
    expect(useRouterStore.getState().asyncRouteData[0].routerPath).toBe('/remote');
    expect(getStorageItem('menu.menuData', 'local')).toMatchObject({
      fingerprint: 'test-manifest', modules: { remote: { menuCode: 'remote' } },
    });
    expect(getStorageItem('router.asyncRouteData', 'local')).toMatchObject({
      fingerprint: 'test-manifest', routes: [{ routerKey: 'remote-page' }],
    });
  });

  it('接口模式刷新从现有缓存恢复菜单、模块选择和路由，不再次请求 API', async () => {
    source.staticMenu = false;
    source.getTree.mockResolvedValue([...tree('first'), ...tree('second')]);
    const initial = await setup();
    await initial.loadMenuData();
    initial.useMenuStore.getState().setCurrentModuleCode('second');
    vi.resetModules();
    const refreshed = await setup();
    expect(source.getTree).toHaveBeenCalledTimes(1);
    expect(Object.keys(refreshed.useMenuStore.getState().menuData)).toEqual(['first', 'second']);
    expect(refreshed.useMenuStore.getState().currentModuleCode).toBe('second');
    expect(refreshed.useMenuStore.getState().currentMenuData[0].menuCode).toBe('second-page');
    expect(refreshed.useRouterStore.getState().asyncRouteData.map(n => n.routerPath))
      .toEqual(['/first', '/second']);
  });

  it('再次登录请求 API，并覆盖已有的菜单与路由缓存', async () => {
    source.staticMenu = false;
    source.getTree.mockResolvedValueOnce(tree('old')).mockResolvedValueOnce(tree('latest'));
    const { loadMenuData, useMenuStore, useRouterStore } = await setup();
    await loadMenuData();
    await loadMenuData();
    expect(source.getTree).toHaveBeenCalledTimes(2);
    expect(Object.keys(useMenuStore.getState().menuData)).toEqual(['latest']);
    expect(useRouterStore.getState().asyncRouteData[0].routerPath).toBe('/latest');
    expect(getStorageItem('menu.menuData', 'local')).toMatchObject({ modules: {
      latest: { menuCode: 'latest' },
    } });
    expect(getStorageItem('router.asyncRouteData', 'local')).toMatchObject({
      routes: [{ routerKey: 'latest-page' }],
    });
  });

  it('API 返回空数组时保持空菜单和路由，不使用 manifest 补齐', async () => {
    source.staticMenu = false;
    source.getTree.mockResolvedValue([]);
    const { loadMenuData, useMenuStore, useRouterStore } = await setup();
    await loadMenuData();
    expect(useMenuStore.getState().menuData).toEqual({});
    expect(useRouterStore.getState().asyncRouteData).toEqual([]);
  });

  it('API 请求失败时抛出错误，不用静态菜单兜底', async () => {
    source.staticMenu = false;
    source.getTree.mockRejectedValue(new Error('菜单接口不可用'));
    const { loadMenuData, useMenuStore, useRouterStore } = await setup();
    await expect(loadMenuData()).rejects.toThrow('菜单接口不可用');
    expect(useMenuStore.getState().menuData).toEqual({});
    expect(useRouterStore.getState().asyncRouteData).toEqual([]);
  });
});
