/**
 * 导航菜单状态：从统一清单派生模块索引与当前模块侧栏。
 * 与动态路由共用清单指纹，真源变更后丢弃旧缓存，避免使用过期菜单。
 */
import { getStorageItem, setStorageItem } from '@utils/storage';
import { create } from 'zustand';
import { MENU_MANIFEST, MENU_MANIFEST_FINGERPRINT } from '../router/manifest';
import type { ModuleMenuData, MenuCode, NavMenuNode } from '../types/moduleMenu';

const MENU_DATA_STORAGE_KEY = 'menu.menuData';
const CURRENT_MODULE_STORAGE_KEY = 'menu.currentModuleCode';

interface StoredMenuBlob {
  fingerprint: string;
  modules: ModuleMenuData;
}

interface MenuState {
  /** 按模块 menuCode 索引的全量菜单树；节点统一为 NavMenuNode，由 buildMenuData 重建。 */
  menuData: ModuleMenuData;
  /** 当前选中模块的 menuCode（稳定业务标识，非数据库 id），决定侧栏展示哪个模块。 */
  currentModuleCode: MenuCode;
  /** 当前模块的顶层导航节点，即 menuData[currentModuleCode].children，供侧栏直接渲染。 */
  currentMenuData: NavMenuNode[];
  /** 登录后按最新清单重建菜单树并持久化；loginModuleCode 不可用时回退到首个有菜单的模块。 */
  buildMenuData: (loginModuleCode?: MenuCode) => void;
  /** 切换当前模块并持久化选中项；复用已有菜单树，不重新构建。 */
  setCurrentModuleCode: (menuCode: MenuCode) => void;
}

/**
 * 按 menuSort 升序生成可见导航：禁用节点连同子树移除，隐藏分组只透传子节点。
 * 不改写节点业务字段，层级仍由 children 表达。
 */
const buildMenuNodes = (nodes: NavMenuNode[]): NavMenuNode[] =>
  [...nodes].sort((a, b) => a.menuSort - b.menuSort).flatMap((node) => {
    if (node.menuStatus === 0) return [];
    const children = node.children ? buildMenuNodes(node.children) : undefined;
    if (!node.menuVisible) {
      return node.menuType === 'group' ? children ?? [] : [];
    }
    return [{ ...node, children }];
  });

const buildRuntimeMenuData = (): ModuleMenuData =>
  Object.fromEntries(
    buildMenuNodes(MENU_MANIFEST)
      .filter((node) => node.menuType === 'module')
      .map((node) => [node.menuCode, node]),
  );

/** 请求的模块不存在或为空时，选择第一个含菜单的模块；没有可用模块则为空。 */
const getValidModuleCode = (menuData: ModuleMenuData, code?: MenuCode | null): MenuCode => {
  if (code && Object.hasOwn(menuData, code) && menuData[code].children?.length) return code;
  return Object.values(menuData).find((node) => node.children?.length)?.menuCode ?? '';
};

/** 读取本地菜单缓存；指纹不一致或结构异常时返回空对象，等待登录后重建。 */
const readStoredMenuData = (): ModuleMenuData => {
  const stored = getStorageItem<StoredMenuBlob>(MENU_DATA_STORAGE_KEY, 'local');
  if (
    !stored || stored.fingerprint !== MENU_MANIFEST_FINGERPRINT ||
    !stored.modules || typeof stored.modules !== 'object' || Array.isArray(stored.modules)
  ) return {};
  return stored.modules;
};

const initialMenuData = readStoredMenuData();
const initialCurrentModuleCode = getValidModuleCode(
  initialMenuData,
  getStorageItem<MenuCode>(CURRENT_MODULE_STORAGE_KEY, 'local'),
);

/** 统一写入：仅在重建菜单时持久化菜单树，当前模块始终持久化，并同步侧栏数据。 */
const applyMenuState = (
  set: (partial: Partial<MenuState>) => void,
  menuData: ModuleMenuData,
  currentModuleCode: MenuCode,
  persistMenu: boolean,
): void => {
  if (persistMenu) {
    setStorageItem(MENU_DATA_STORAGE_KEY, {
      fingerprint: MENU_MANIFEST_FINGERPRINT,
      modules: menuData,
    } satisfies StoredMenuBlob, 'local');
  }
  setStorageItem(CURRENT_MODULE_STORAGE_KEY, currentModuleCode, 'local');
  set({ menuData, currentModuleCode, currentMenuData: menuData[currentModuleCode]?.children ?? [] });
};

export const useMenuStore = create<MenuState>((set, get) => ({
  menuData: initialMenuData,
  currentModuleCode: initialCurrentModuleCode,
  currentMenuData: initialMenuData[initialCurrentModuleCode]?.children ?? [],
  buildMenuData: (loginModuleCode) => {
    const menuData = buildRuntimeMenuData();
    applyMenuState(set, menuData, getValidModuleCode(menuData, loginModuleCode), true);
  },
  setCurrentModuleCode: (menuCode) => {
    const { menuData } = get();
    applyMenuState(set, menuData, getValidModuleCode(menuData, menuCode), false);
  },
}));
