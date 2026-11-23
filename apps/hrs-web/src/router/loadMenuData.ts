/** 菜单加载入口：开发时由 manifest 中的固定开关选择数据源。 */
import { menuApi } from '../api/system/menu';
import { useMenuStore } from '../stores/MenuStore';
import { useRouterStore } from '../stores/RouterStore';
import { MENU_MANIFEST, USE_STATIC_MENU } from './manifest';

/**
 * 登录成功后读取一次数据，交给两个 Store 派生菜单和路由，并复用各自的持久化流程。
 * 刷新页面由 Store 初始化恢复本地数据，不调用此入口。
 * 接口失败直接向调用方抛出，不静默改用静态菜单。
 */
export async function loadMenuData(): Promise<void> {
  const nodes = USE_STATIC_MENU ? MENU_MANIFEST : await menuApi.getTree();
  useMenuStore.getState().buildMenuData(undefined, nodes);
  useRouterStore.getState().buildAsyncRouterData(nodes);
}
