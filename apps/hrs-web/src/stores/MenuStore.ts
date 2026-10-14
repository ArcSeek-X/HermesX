/**
 * @file MenuStore.ts
 * @description 菜单状态 Store（Zustand）。以路由清单 `MENU_MANIFEST` 为唯一真值源，
 *   构建「按模块划分」的导航菜单数据，并派生当前模块的菜单树（currentMenuData）。
 *
 * 持久化边界：
 * - menuData：全量菜单数据，持久化到 localStorage（菜单数据源）。
 * - currentModuleId：当前选中模块，持久化。
 * - currentMenuData：由 menuData + currentModuleId 派生，运行期计算，不持久化。
 *
 * 三个入口：
 * - buildMenuData(loginModuleId?)：登录成功后构建全量菜单并初始化当前模块（场景一）。
 * - setCurrentModuleId(moduleId)：复用已持久化 menuData 切换模块（场景二）。
 * - 初始化：store 加载时从 localStorage 还原 menuData / currentModuleId 并派生（场景三，无需手动调用）。
 *
 * 使用场景：被左侧/顶部导航等布局组件经 `useMenuStore` 读取 `currentMenuData`。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-17
 */
import { getStorageItem, setStorageItem } from '@utils/storage';
import { create } from 'zustand';
import { MENU_MANIFEST, type AppRouteNode } from '../router/manifest';
import type { ModuleMenuData, ModuleId, NavMenuNode } from '../types/moduleMenu';

/** 持久化「全量菜单数据」的键；存储即菜单数据源，有则直接可用 */
const MENU_DATA_STORAGE_KEY = 'menu.menuData';
/** 持久化「当前选中模块 id」的键 */
const CURRENT_MODULE_STORAGE_KEY = 'menu.currentModuleId';
/** 未配置或配置失效时的回退默认模块 id */
const DEFAULT_MODULE_ID: ModuleId = 'productModel';

interface MenuState {
  /** 按模块划分的完整菜单数据：{ [moduleId]: NavModuleNode }，含模块元数据与菜单树，需持久化 */
  menuData: ModuleMenuData;
  /** 当前激活模块 id，取值来自菜单节点的 moduleId；需持久化 */
  currentModuleId: ModuleId;
  /** 当前模块下实际渲染的菜单树：由 menuData[currentModuleId] 派生，运行期计算，不持久化 */
  currentMenuData: NavMenuNode[];
  /** 登录后构建全量菜单并初始化当前模块；loginModuleId 省略则取第一个可用模块 */
  buildMenuData: (loginModuleId?: ModuleId) => void;
  /** 切换当前模块：复用已持久化 menuData，仅更新 currentModuleId 与派生视图 */
  setCurrentModuleId: (moduleId: ModuleId) => void;
}

/** 路由节点 → 导航菜单节点：仅搬运展示字段，未命中字段回退默认值，存在子节点则一并挂上 */
const toNavMenuNode = (node: AppRouteNode, children?: NavMenuNode[]): NavMenuNode => ({
  menuId: node.menuId,
  menuName: node.menuName,
  routePath: node.routePath ?? '',
  menuIcon: node.menuIcon,
  menuBadge: node.menuBadge,
  menuPosition: node.menuPosition,
  level: node.level,
  menuType: node.menuType,
  menuExpanded: node.menuExpanded,
  description: node.menuDescription,
  children: children?.length ? children : undefined,
});

/**
 * 递归构建可见菜单节点数组。
 * 过滤规则：menuVisible === false 的节点剔除；group 不可见时仅透传其子节点（不保留分组壳）。
 * 模块归属已由 MENU_MANIFEST 的子树结构保证，无需逐节点按 moduleId 过滤。
 */
const buildModuleMenuNodes = (nodes: AppRouteNode[]): NavMenuNode[] =>
  nodes.flatMap((node) => {
    const children = node.children?.length ? buildModuleMenuNodes(node.children) : undefined;
    const isVisible = node.menuVisible !== false;
    if (node.menuType === 'group') {
      return isVisible ? [toNavMenuNode(node, children)] : (children ?? []);
    }
    return isVisible ? [toNavMenuNode(node, children)] : [];
  });

/** 基于路由清单实时构建全量运行时菜单数据（不读 localStorage，始终反映最新路由结构） */
const buildRuntimeMenuData = (): ModuleMenuData => {
  const menuData = {} as ModuleMenuData;
  for (const moduleNode of MENU_MANIFEST) {
    menuData[moduleNode.moduleId] = {
      moduleId: moduleNode.moduleId,
      moduleName: moduleNode.moduleName,
      moduleDescription: moduleNode.moduleDescription,
      routePath: moduleNode.routePath,
      moduleGroupId: moduleNode.moduleGroupId,
      moduleGroupName: moduleNode.moduleGroupName,
      moduleIcon: moduleNode.moduleIcon,
      children: buildModuleMenuNodes(moduleNode.children ?? []),
    };
  }
  return menuData;
};

/** 选出第一个「非空（含菜单项）」的模块 id；全部为空时回退 DEFAULT_MODULE_ID */
const getFirstAvailableModuleId = (menuData: ModuleMenuData): ModuleId => {
  const first = (Object.keys(menuData) as ModuleId[]).find(
    (id) => menuData[id].children.length > 0,
  );
  return first ?? DEFAULT_MODULE_ID;
};

/** 校验模块 id 有效性：存在于 menuData 且对应非空才采用，否则回退第一个可用模块 */
const getValidModuleId = (menuData: ModuleMenuData, moduleId?: ModuleId | null): ModuleId => {
  if (moduleId && menuData[moduleId]) {
    return moduleId;
  }
  return getFirstAvailableModuleId(menuData);
};

/**
 * 读取持久化的菜单数据：有值即以存储为权威源；缺失或非对象时返回空对象（不回退实时兜底）。
 * 菜单数据仅由 buildMenuData() 登录后构建落盘，未登录即为空，「空对象」是刻意的合法初值。
 */
const readStoredMenuData = (): ModuleMenuData => {
  const stored = getStorageItem<ModuleMenuData>(MENU_DATA_STORAGE_KEY, 'local');
  if (!stored || typeof stored !== 'object') {
    return {} as ModuleMenuData;
  }
  return stored;
};

/** 读取并校验持久化的 currentModuleId；存储缺失或非法时回退第一个可用模块 */
const readStoredCurrentModuleId = (menuData: ModuleMenuData): ModuleId => {
  const storedModuleId = getStorageItem<ModuleId>(CURRENT_MODULE_STORAGE_KEY, 'local');
  return getValidModuleId(menuData, storedModuleId);
};

// 场景三：store 初始化时从 localStorage 还原（刷新浏览器走此路径，无需手动调用）
const initialMenuData = readStoredMenuData();
const initialCurrentModuleId = readStoredCurrentModuleId(initialMenuData);
const initialCurrentMenuData = initialMenuData[initialCurrentModuleId]?.children ?? [];

/**
 * 统一出口：派生 currentMenuData + 持久化 + 写入 state，消除各 action 的重复骨架。
 * @param init true=场景一（menuData 变更，一并持久化）；false=场景二（仅切模块）
 */
const applyMenuState = (
  set: (partial: Partial<MenuState>) => void,
  menuData: ModuleMenuData,
  currentModuleId: ModuleId,
  init: boolean,
): void => {
  const currentMenuData = menuData[currentModuleId]?.children ?? [];
  if (init) {
    setStorageItem(MENU_DATA_STORAGE_KEY, menuData, 'local');
  }
  setStorageItem(CURRENT_MODULE_STORAGE_KEY, currentModuleId, 'local');
  set({ menuData, currentModuleId, currentMenuData });
};

export const useMenuStore = create<MenuState>((set, get) => ({
  // 初始 state 由场景三从 localStorage 还原，直接内联
  menuData: initialMenuData,
  currentModuleId: initialCurrentModuleId,
  currentMenuData: initialCurrentMenuData,

  // 场景一：登录成功 → 构建全量 menuData 并初始化当前模块
  buildMenuData: (loginModuleId) => {
    //构建完整的模块菜单数据
    const menuData = buildRuntimeMenuData();
    const currentModuleId = getValidModuleId(menuData, loginModuleId);
    console.log('menuData',menuData)
    applyMenuState(set, menuData, currentModuleId, true);
  },

  // 场景二：已登录切换模块 → 复用已持久化 menuData，仅切模块 + 派生
  setCurrentModuleId: (moduleId) => {
    const { menuData } = get();
    const currentModuleId = getValidModuleId(menuData, moduleId);
    applyMenuState(set, menuData, currentModuleId, false);
  },
}));
