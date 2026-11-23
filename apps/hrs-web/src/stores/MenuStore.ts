/**
 * 菜单状态：统一节点清单 → 按模块索引 → 当前模块侧栏。
 * 菜单与动态路由使用相同清单指纹，结构变更后拒绝还原旧格式缓存。
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
  /** 用模块的 menuCode 索引，所有值都是统一菜单节点。 */
  menuData: ModuleMenuData;
  /** 当前选中模块的稳定业务标识，不是数据库 id。 */
  currentModuleCode: MenuCode;
  currentMenuData: NavMenuNode[];
  buildMenuData: (loginModuleCode?: MenuCode) => void;
  setCurrentModuleCode: (menuCode: MenuCode) => void;
}

/**
 * 生成可见导航：禁用节点连同子树移除；隐藏分组仅透传子节点。
 * 不改写节点字段、不再维护模块专属格式，层级交由渲染组件递归计算。
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
