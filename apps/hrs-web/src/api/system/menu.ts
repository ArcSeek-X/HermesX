/**
 * system 菜单树查询：接口数据与 MENU_MANIFEST 共用 NavMenuNode 契约。
 * 登录加载入口按开关调用此 API；默认仍使用静态清单，Java 真实接入待契约对齐。
 */
import apiClient from '@/api';
import type { NavMenuNode } from '@/types/moduleMenu';
import type { RestResult } from '@/types/restResult';

/** HTTP 成功但业务失败时，保留服务端业务码与提示，供调用方展示/处理。 */
export class MenuApiError extends Error {
  readonly resultCode: string;
  readonly resultMsg: string;

  constructor(resultCode: string, resultMsg: string) {
    super(resultMsg);
    this.name = 'MenuApiError';
    this.resultCode = resultCode;
    this.resultMsg = resultMsg;
  }
}

/** 契约不符应明确报错，不能返回空菜单或用 manifest 掩盖联调问题。 */
export class MenuContractError extends Error {
  constructor(location: string) {
    super(`菜单接口数据格式不符合约定：${location}`);
    this.name = 'MenuContractError';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireField(valid: boolean, location: string): asserts valid {
  if (!valid) throw new MenuContractError(location);
}

/**
 * TypeScript 类型只约束开发代码，无法保证网络 JSON 正确，因此在 API 边界递归校验。
 * 只校验菜单契约；页面是否存在仍由前端页面导入白名单负责。
 */
function assertMenuTree(value: unknown): asserts value is NavMenuNode[] {
  requireField(Array.isArray(value), 'resultData 必须是菜单树数组');
  const codes = new Set<string>();
  const ids = new Set<number>();
  const routes = new Set<string>();

  function visit(node: unknown, location: string, parent?: Record<string, unknown>): void {
    requireField(isRecord(node), location);
    requireField(typeof node.menuCode === 'string' && node.menuCode.trim().length > 0,
      `${location}.menuCode`);
    const code = node.menuCode as string;
    requireField(!codes.has(code), `${location}.menuCode 重复：${code}`);
    codes.add(code);

    for (const field of ['menuName', 'menuDescription']) {
      requireField(typeof node[field] === 'string', `${location}.${field}`);
    }
    requireField(typeof node.menuType === 'string' && ['module', 'group', 'page'].includes(node.menuType), `${location}.menuType`);
    requireField(parent ? node.menuType !== 'module' : node.menuType === 'module',
      `${location}.menuType：根节点须为 module，子节点须为 group/page`);
    requireField(typeof node.menuPosition === 'string' && ['header', 'content', 'footer'].includes(node.menuPosition),
      `${location}.menuPosition`);
    requireField(node.menuStatus === 0 || node.menuStatus === 1, `${location}.menuStatus`);
    requireField(typeof node.menuSort === 'number' && Number.isFinite(node.menuSort), `${location}.menuSort`);
    for (const field of ['menuExpanded', 'menuVisible']) {
      requireField(typeof node[field] === 'boolean', `${location}.${field}`);
    }
    for (const field of ['menuRoutePath', 'menuPagePath', 'menuIcon', 'menuBadge', 'menuPermission']) {
      requireField(node[field] === undefined || typeof node[field] === 'string', `${location}.${field}`);
    }
    requireField(node.auth === undefined || node.auth === 'public' || node.auth === 'protected',
      `${location}.auth`);
    requireField(node.exact === undefined || typeof node.exact === 'boolean', `${location}.exact`);

    // 静态清单可不带主键；接口若返回主键，须为可无损表示的正整数。
    if (node.id !== undefined) {
      requireField(Number.isSafeInteger(node.id) && (node.id as number) > 0, `${location}.id`);
      const id = node.id as number;
      requireField(!ids.has(id), `${location}.id 重复`);
      ids.add(id);
    }
    if (node.menuParentId !== undefined) {
      requireField(Number.isSafeInteger(node.menuParentId) && (node.menuParentId as number) >= 0,
        `${location}.menuParentId`);
      requireField(node.menuParentId === (parent ? parent.id : 0),
        `${location}.menuParentId 与树的父节点不一致`);
    }
    requireField(node.children === undefined || Array.isArray(node.children), `${location}.children`);
    const children = (node.children ?? []) as unknown[];
    if (node.menuType === 'page') {
      requireField(children.length === 0, `${location}.children：page 不能包含子节点`);
      requireField(typeof node.menuRoutePath === 'string' && node.menuRoutePath.startsWith('/')
        && !node.menuRoutePath.startsWith('//'), `${location}.menuRoutePath`);
      requireField(typeof node.menuPagePath === 'string' && node.menuPagePath.startsWith('pages/'),
        `${location}.menuPagePath`);
      const route = node.menuRoutePath as string;
      requireField(!routes.has(route), `${location}.menuRoutePath 重复：${route}`);
      routes.add(route);
    }
    children.forEach((child, index) => visit(child, `${location}.children[${index}]`, node));
  }
  value.forEach((node, index) => visit(node, `resultData[${index}]`));
}

export const menuApi = {
  /**
   * 获取完整菜单树，直接返回与 MENU_MANIFEST 相同格式的数组。
   * 使用 POST，不发送请求体或 keyword/status 等管理筛选条件，获取完整导航/路由树。
   * 不在这里排序、过滤或写 Store；保留服务端原始字段和顺序。
   * 网络及 HTTP 错误继续由现有 API 客户端处理并向上传递。
   */
  async getTree(): Promise<NavMenuNode[]> {
    const { data } = await apiClient.post<RestResult<NavMenuNode[]>>('/api/system/list-menu');
    requireField(isRecord(data) && typeof data.resultCode === 'string'
      && typeof data.resultMsg === 'string' && 'resultData' in data, '响应须包含 resultCode/resultMsg/resultData');
    if (data.resultCode !== '200') throw new MenuApiError(data.resultCode, data.resultMsg);
    assertMenuTree(data.resultData);
    return data.resultData;
  },
};
