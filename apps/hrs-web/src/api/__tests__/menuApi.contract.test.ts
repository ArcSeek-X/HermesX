/** 使用真实 API 客户端与响应拦截器，只替换网络适配器，验证菜单契约和缓存行为。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AxiosError, AxiosHeaders, type AxiosAdapter } from 'axios';
import apiClient, { clearAllApiCache } from '@/api';
import { menuApi, MenuApiError, MenuContractError } from '@/api/system/menu';
import { MENU_MANIFEST } from '@/router/manifest';
import type { NavMenuNode } from '@/types/moduleMenu';

vi.mock('@/components/basic/Toast/Toast', () => ({ showToast: { danger: vi.fn() } }));

const originalAdapter = apiClient.defaults.adapter;
const adapter = vi.fn<AxiosAdapter>();
let body: unknown;
const success = (tree: unknown) => ({ resultCode: '200', resultMsg: '操作成功。', resultData: tree });

/** 从真实清单构造三层样本，避免另起一套菜单字段。 */
function sampleTree(): NavMenuNode[] {
  const page = MENU_MANIFEST[0].children!.find((node) => node.menuType === 'page')!;
  return [{
    ...MENU_MANIFEST[0], id: 1, menuParentId: 0,
    children: [{
      ...page, id: 2, menuParentId: 1, menuCode: 'research', menuType: 'group',
      children: [{ ...page, id: 3, menuParentId: 2 }],
    }],
  }];
}

beforeEach(() => {
  clearAllApiCache();
  adapter.mockReset();
  body = success(sampleTree());
  adapter.mockImplementation(async (config) => ({
    data: body, status: 200, statusText: 'OK', headers: {}, config,
  }));
  apiClient.defaults.adapter = adapter;
});

afterEach(() => {
  apiClient.defaults.adapter = originalAdapter;
  clearAllApiCache();
});

describe('menuApi.getTree', () => {
  it('POST 查询完整树，解包 resultData 并保留 manifest 字段与层级', async () => {
    const tree = sampleTree();
    body = success(tree);
    expect(await menuApi.getTree()).toEqual(tree);
    expect(adapter).toHaveBeenCalledTimes(1);
    expect(adapter.mock.calls[0][0]).toMatchObject({
      method: 'post', url: '/api/system/list-menu', withCredentials: true,
    });
    expect(adapter.mock.calls[0][0].params).toBeUndefined();
    expect(adapter.mock.calls[0][0].data).toBeUndefined();
  });

  it('真实 MENU_MANIFEST 可直接作为 resultData，不转换字段或伪造 ID', async () => {
    body = success(MENU_MANIFEST);
    expect(await menuApi.getTree()).toEqual(MENU_MANIFEST);
  });

  it('空数组表示成功但没有菜单，不回退到静态清单', async () => {
    body = success([]);
    expect(await menuApi.getTree()).toEqual([]);
  });

  it('保留隐藏、禁用、排序和路由扩展，交由 Store 加工', async () => {
    const tree = sampleTree();
    Object.assign(tree[0].children![0].children![0], {
      menuStatus: 0, menuVisible: false, menuSort: 8, auth: 'protected', exact: true,
      menuBadge: '新', menuPermission: 'system:menu:read',
    });
    body = success(tree);
    expect(await menuApi.getTree()).toEqual(tree);
  });

  it('连续调用重新请求，不缓存成功数据或业务错误', async () => {
    await menuApi.getTree();
    body = { resultCode: '403', resultMsg: '无权访问菜单。', resultData: null };
    await expect(menuApi.getTree()).rejects.toBeInstanceOf(MenuApiError);
    body = success([]);
    expect(await menuApi.getTree()).toEqual([]);
    expect(adapter).toHaveBeenCalledTimes(3);
  });

  it('HTTP 200 业务失败保留 resultCode/resultMsg', async () => {
    body = { resultCode: 'SYSTEM_MENU_NOT_FOUND', resultMsg: '菜单不存在。', resultData: null };
    await expect(menuApi.getTree()).rejects.toMatchObject({
      name: 'MenuApiError', resultCode: 'SYSTEM_MENU_NOT_FOUND',
      resultMsg: '菜单不存在。', message: '菜单不存在。',
    });
  });

  it('网络错误向上传递，不伪装为空菜单', async () => {
    const error = new AxiosError('Network Error', 'ERR_NETWORK');
    adapter.mockRejectedValueOnce(error);
    await expect(menuApi.getTree()).rejects.toBe(error);
  });

  it('HTTP 错误保留状态和响应，不被契约错误覆盖', async () => {
    const error = new AxiosError('Forbidden', 'ERR_BAD_REQUEST', undefined, undefined, {
      status: 403, statusText: 'Forbidden', headers: {}, config: { headers: new AxiosHeaders() },
      data: { resultCode: '403', resultMsg: '无权访问。', resultData: null },
    });
    adapter.mockRejectedValueOnce(error);
    await expect(menuApi.getTree()).rejects.toBe(error);
    expect(error.response?.status).toBe(403);
  });

  it.each([
    ['缺少响应包装', []],
    ['业务码不是字符串', { resultCode: 200, resultMsg: '操作成功。', resultData: [] }],
    ['缺少 resultMsg', { resultCode: '200', resultData: [] }],
    ['缺少 resultData', { resultCode: '200', resultMsg: '操作成功。' }],
    ['成功数据为 null', success(null)],
    ['数据不是数组', success({ children: [] })],
    ['旧 Java 菜单字段', success([{ id: 1, parentId: 0, name: '产品', type: 'module' }])],
  ])('拒绝错误响应：%s', async (_name, payload) => {
    body = payload;
    await expect(menuApi.getTree()).rejects.toBeInstanceOf(MenuContractError);
  });

  it.each([
    ['重复业务码', { menuCode: 'research' }],
    ['重复数据库 ID', { id: 2 }],
    ['不安全的数据库 ID', { id: Number.MAX_SAFE_INTEGER + 1 }],
    ['父键与树不一致', { menuParentId: 999 }],
    ['数字可见标志', { menuVisible: 1 }],
    ['字符串状态', { menuStatus: '1' }],
    ['空路由', { menuRoutePath: '' }],
    ['缺少页面路径', { menuPagePath: undefined }],
    ['旧菜单类型', { menuType: 'redirect' }],
    ['数组菜单类型', { menuType: ['page'] }],
    ['嵌套模块', { menuType: 'module' }],
    ['错误 children', { children: null }],
    ['page 包含子节点', { children: sampleTree() }],
    ['错误 auth', { auth: 'admin' }],
  ])('递归检查子节点：%s', async (_name, fields) => {
    const tree = sampleTree();
    Object.assign(tree[0].children![0].children![0], fields);
    body = success(tree);
    await expect(menuApi.getTree()).rejects.toBeInstanceOf(MenuContractError);
  });

  it('根节点必须为 module', async () => {
    const tree = sampleTree();
    tree[0].menuType = 'group';
    body = success(tree);
    await expect(menuApi.getTree()).rejects.toBeInstanceOf(MenuContractError);
  });
});
