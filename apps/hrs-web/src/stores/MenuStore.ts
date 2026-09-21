/**
 * @file MenuStore.ts
 * @description 菜单状态 Store（Zustand）。以路由清单 `MENU_MANIFEST` 为唯一真值源，
 *   构建「按模块划分」的导航菜单数据，并派生当前模块的菜单树（currentMenuData）。
 *
 * 三类状态的持久化边界：
 * - menuData：所有模块与菜单的全量数据，需持久化到 localStorage（菜单数据源）。
 * - currentModuleId：当前选中模块，需持久化。
 * - currentMenuData：由 menuData + currentModuleId 派生的当前模块菜单树，运行期计算，不持久化。
 *
 * 三个业务场景与 Store 入口的对应关系（登录功能尚未实现，以下入口供后续直接调用）：
 * - 场景一 首次登录：登录成功后调用 `buildMenuData(loginModuleId?)` ——
 *   构建全量 menuData、确定 currentModuleId（登录指定或回退第一个可用模块）、派生 currentMenuData，并持久化。
 * - 场景二 切换模块：UI 调用 `setCurrentModuleId(moduleId)` ——
 *   复用已持久化的 menuData（不重建），切换 currentModuleId 并重算 currentMenuData，仅持久化 currentModuleId。
 * - 场景三 刷新浏览器：store 初始化时（模块加载）自动从 localStorage 还原 menuData 与
 *   currentModuleId 并派生 currentMenuData（见文件底部 `initial*` 初始化），无需手动调用。
 *
 * 使用场景：被左侧导航、顶部导航等布局组件经由 `useMenuStore` 读取 `currentMenuData`。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-17
 */
import { create } from 'zustand';
import { MENU_MANIFEST, type AppRouteNode } from '../router/manifest';
import type { ModuleMenuData, ModuleId, NavMenuNode } from '../types/moduleMenu';
import { getStorageItem, setStorageItem } from '../utils/storage';

/** localStorage 中持久化「全量菜单数据（menuData）」的键；存储即菜单数据源，有则直接可用 */
const MENU_DATA_STORAGE_KEY = 'menu.menuData';
/** localStorage 中持久化「当前选中模块 id（currentModuleId）」的键 */
const CURRENT_MODULE_STORAGE_KEY = 'menu.currentModuleId';
/** 未配置或配置失效时的回退默认模块 id */
const DEFAULT_MODULE_ID: ModuleId = 'productModel';

interface MenuState {
  /** 按模块划分的完整菜单数据：{ [moduleId]: NavMenuNode[] }。需持久化（见 MENU_DATA_STORAGE_KEY） */
  menuData: ModuleMenuData;
  /** 当前激活的模块 id；取值来自各菜单节点的 moduleId 字段，需持久化（见 CURRENT_MODULE_STORAGE_KEY） */
  currentModuleId: ModuleId;
  /** 当前模块下实际渲染的菜单树：由 menuData[currentModuleId] 派生，运行期计算，不持久化；
   *  节点携带 menuPosition 字段，使用方自行按区域拆分 */
  currentMenuData: NavMenuNode[];
  /** 场景一：登录后构建全量菜单并初始化当前模块。loginModuleId 为登录指定模块，省略则取第一个可用模块 */
  buildMenuData: (loginModuleId?: ModuleId) => void;
  /** 场景二：切换当前模块。复用已持久化的 menuData，仅更新 currentModuleId 与派生视图 */
  setCurrentModuleId: (moduleId: ModuleId) => void;
}

/**
 * 将路由节点（AppRouteNode）映射为导航菜单节点（NavMenuNode）。
 * 仅搬运展示所需的字段，未命中的字段回退为默认值；若存在子节点则一并挂上。
 * @param node 源路由节点，不允许为 null
 * @param children 已构建好的子菜单节点；为空或 undefined 时不挂 children 字段
 * @returns 转换后的 NavMenuNode
 */
const toNavMenuNode = (node: AppRouteNode, children?: NavMenuNode[]): NavMenuNode => ({
  menuId: node.menuId,
  menuName: node.menuName,
  routePath: node.routePath ?? '',
  menuIcon: node.menuIcon,
  menuBadge: node.menuBadge,
  menuPosition: node.menuPosition,
  level: node.level,
  menuExpanded: node.menuExpanded,
  description: node.menuDescription,
  children: children?.length ? children : undefined,
});

/**
 * 递归构建菜单节点数组。
 * 过滤规则：① menuVisible === false 的节点剔除；
 * ② group 类型节点不可见时仅透传其子节点（不保留分组壳），可见时作为分组项保留。
 * 模块归属已由 MENU_MANIFEST 的模块子树结构性保证，无需逐节点按 moduleId 过滤。
 * @param nodes 路由节点森林（已是某一模块的子树）
 * @returns 可见的菜单节点数组（不含不可见节点）；无匹配时返回空数组
 */
const buildModuleMenuNodes = (nodes: AppRouteNode[]): NavMenuNode[] =>
  nodes.flatMap((node) => {
    const children = node.children?.length ? buildModuleMenuNodes(node.children) : undefined;
    const isVisible = node.menuVisible !== false;
    if (node.menuType === 'group') {
      if (!isVisible) {
        return children ?? [];
      }
      return [toNavMenuNode(node, children)];
    }

    if (!isVisible) {
      return [];
    }

    return [toNavMenuNode(node, children)];
  });

/**
 * 构建全量运行时菜单数据：遍历每个模块 id，生成对应的菜单树。
 * 基于路由清单实时计算、不读 localStorage，因此始终反映最新路由结构。
 * @returns 形如 { [moduleId]: NavMenuNode[] } 的全量菜单数据
 */
const buildRuntimeMenuData = (): ModuleMenuData => {
  const menuData = {} as ModuleMenuData;
  for (const moduleNode of MENU_MANIFEST) {
    // 直接取模块子树构建菜单（模块归属已结构性保证）
    menuData[moduleNode.moduleId] = buildModuleMenuNodes(moduleNode.children ?? []);
  }
  return menuData;
};



/**
 * 从菜单数据中选出一个「至少有菜单项」的模块 id。
 * @param menuData 全量菜单数据，不允许为 null
 * @returns 第一个非空模块的 id；全部为空时回退 DEFAULT_MODULE_ID
 */
const getFirstAvailableModuleId = (menuData: ModuleMenuData): ModuleId => {
  const keys = Object.keys(menuData) as ModuleId[];
  const first = keys.find((item) => Array.isArray(menuData[item]) && menuData[item].length > 0);
  return first ?? DEFAULT_MODULE_ID;
};

/**
 * 校验模块 id 有效性：传入的 id 在菜单数据中存在且对应非空数组才采用，
 * 否则回退到第一个可用模块。
 * @param menuData 全量菜单数据
 * @param moduleId 待校验的模块 id，允许为 undefined / null（视为无效）
 * @returns 有效的模块 id（必为 menuData 中存在的键）
 */
const getValidModuleId = (menuData: ModuleMenuData, moduleId?: ModuleId | null): ModuleId => {
  if (moduleId && Array.isArray(menuData[moduleId])) {
    return moduleId;
  }
  return getFirstAvailableModuleId(menuData);
};

/**
 * 读取持久化的菜单数据（menuData）。
 * 存储即唯一权威数据源：有值就用存储里的（"存什么用什么"）；
 * 存储缺失或非对象时返回空对象，**不回退任何实时计算的兜底数据**——
 * 菜单数据只在登录成功后由 buildMenuData() 构建并落盘，未登录即为空。
 * 副作用：读取 localStorage（'local' 作用域）的 MENU_DATA_STORAGE_KEY。
 * @returns 持久化的菜单数据；缺失或格式非法时返回空对象
 */
const readStoredMenuData = (): ModuleMenuData => {
  const stored = getStorageItem<ModuleMenuData>(MENU_DATA_STORAGE_KEY, 'local');
  // 只接受对象形态：null（缺失/解析失败/存储不可用）与 JSON 基本类型一律视为「没有」。
  // 这里断言而非补壳二个模块键：ModuleMenuData 为 Record<ModuleId, NavMenuNode[]>，
  // 「空对象」是刻意的合法初值，补 { productModel: [], developmentMode: [] } 反而伪装成已初始化。
  if (!stored || typeof stored !== 'object') {
    return {} as ModuleMenuData;
  }
  // menuIcon 已是可序列化的图标名字符串，随节点一同落盘，无需再从运行时清单回填，直接以存储为权威源
  return stored;
};

/**
 * 读取并校验持久化的当前模块 id（currentModuleId）。
 * currentModuleId 来自各菜单节点的 moduleId 字段，故需校验其是否仍存在于菜单数据中。
 * 副作用：读取 localStorage（'local' 作用域）的 CURRENT_MODULE_STORAGE_KEY。
 * @param menuData 全量菜单数据，用于校验存储值是否有效
 * @returns 有效的当前模块 id；存储缺失或非法时回退到第一个可用模块
 */
const readStoredCurrentModuleId = (menuData: ModuleMenuData): ModuleId => {
  const storedModuleId = getStorageItem<ModuleId>(CURRENT_MODULE_STORAGE_KEY, 'local');
  return getValidModuleId(menuData, storedModuleId);
};

// ===== 场景三：从持久化加载 - store 初始化（模块加载时自动执行）=====
// 从 localStorage 还原 menuData 与 currentModuleId（缺失则回退运行时结构），并派生 currentMenuData。
// 刷新浏览器时即走此路径，无需手动调用。
const initialMenuData = readStoredMenuData();
const initialCurrentModuleId = readStoredCurrentModuleId(initialMenuData) || "";
const initialCurrentMenuData = initialMenuData[initialCurrentModuleId] ?? [];

/**
 * 内部统一出口：派生视图 + 持久化 + 写入 state（消除各 action 的重复骨架）。
 * 因 store 改用隐式返回对象字面量（无 `return`），此处需显式接收 `set`。
 * @param set Zustand 的 set
 * @param menuData 全量菜单数据
 * @param currentModuleId 当前激活模块
 * @param init 是否首次登录加载处理，需要一并持久化 menuData（场景一=true；场景二=false，menuData 未变）
 */
const applyMenuState = (
  set: (partial: Partial<MenuState>) => void,
  menuData: ModuleMenuData,
  currentModuleId: ModuleId,
  init: boolean,
): void => {
  const currentMenuData = menuData[currentModuleId] ?? [];
  if (init) {
    // menuIcon 为图标名字符串，可随节点一同 JSON 序列化落盘，无需针对图标做特殊处理
    setStorageItem(MENU_DATA_STORAGE_KEY, menuData, 'local');
  }
  setStorageItem(CURRENT_MODULE_STORAGE_KEY, currentModuleId, 'local');
  set({ menuData, currentModuleId, currentMenuData });
};

export const useMenuStore = create<MenuState>((set, get) => ({
  // 场景三：以下初始 state 在 store 初始化时由 localStorage 还原（见 initial*），直接内联无需 return
  menuData: initialMenuData,
  currentModuleId: initialCurrentModuleId,
  currentMenuData: initialCurrentMenuData,

  // 场景一：首次登录成功 → 构建全量 menuData 并初始化当前模块
  buildMenuData: (loginModuleId) => {
    //构建完整的模块菜单数据
    const menuData = buildRuntimeMenuData();
    const currentModuleId = getValidModuleId(menuData, loginModuleId);
    applyMenuState(set, menuData, currentModuleId, true);
  },

  // 场景二：已登录切换模块 → 复用已持久化的 menuData（不重建），仅切模块 + 派生
  setCurrentModuleId: (moduleId) => {
    const { menuData } = get();
    const currentModuleId = getValidModuleId(menuData, moduleId);
    applyMenuState(set, menuData, currentModuleId, false);
  },
}));
