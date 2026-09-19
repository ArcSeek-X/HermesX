/**
 * 布局状态管理 Store
 *
 * 文件用途：
 *   基于 Zustand 的轻量状态管理，承载桌面端侧边栏折叠态 menuCollapsedState。
 *   该状态原先是 Shell 组件内的布尔 state（useCachedState），现提升为全局三态字符串，
 *   供跨子树组件读写，无需层层透传 props。
 *
 * 三态语义：
 *   - offcanvas：正常状态（不折叠），默认值
 *   - collapsed：半折叠
 *   - fully：完全折叠
 *
 * 设计要点：
 *   1. 落盘写在 action 内（而非 store 订阅），行为与原先 useCachedState 的即时写入一致。
 *   2. 读取时做合法性校验，非法值（含迁移前遗留的布尔值）一律回退默认 offcanvas。
 */
import { create } from 'zustand';
import { getStorageItem, setStorageItem } from '../utils/storage';

/** 侧栏折叠状态：offcanvas=正常（不折叠）/ collapsed=半折叠 / fully=完全折叠 */
export type MenuCollapsedState = 'offcanvas' | 'collapsed' | 'fully';

/** 持久化键（utils/storage 自动加 hrs-pref- 前缀，实际为 hrs-pref-layout.menuCollapsedState） */
const MENU_COLLAPSED_STORAGE_KEY = 'layout.menuCollapsedState';

/** 默认状态：正常（不折叠） */
const DEFAULT_STATE: MenuCollapsedState = 'offcanvas';

/** 点击切换时的循环顺序：正常 → 半折叠 → 完全折叠 → 回到正常 */
const STATE_CYCLE: MenuCollapsedState[] = ['offcanvas', 'collapsed', 'fully'];

/** 读取持久化值；非法值回退到默认状态 */
const readStoredState = (): MenuCollapsedState => {
  const stored = getStorageItem<MenuCollapsedState>(MENU_COLLAPSED_STORAGE_KEY, 'local');
  return stored && STATE_CYCLE.includes(stored) ? stored : DEFAULT_STATE;
};

/** 布局 Store 状态与 Action 定义 */
interface LayoutState {
  /** 侧栏折叠状态，默认 offcanvas（正常，不折叠） */
  menuCollapsedState: MenuCollapsedState;
  /** 直接设定折叠状态 */
  setMenuCollapsedState: (state: MenuCollapsedState) => void;
  /** 按「正常 → 半折叠 → 完全折叠」循环切换 */
  toggleMenuCollapsedState: () => void;
}

export const useLayoutStore = create<LayoutState>((set, get) => ({
  // 初始状态：优先从 localStorage 恢复，非法值回退 offcanvas
  menuCollapsedState: readStoredState(),

  /** 直接设定折叠状态并落盘 */
  setMenuCollapsedState: (state) => {
    setStorageItem(MENU_COLLAPSED_STORAGE_KEY, state, 'local');
    set({ menuCollapsedState: state });
  },

  /** 在三种状态间循环并落盘 */
  toggleMenuCollapsedState: () => {
    const current = get().menuCollapsedState;
    const next = STATE_CYCLE[(STATE_CYCLE.indexOf(current) + 1) % STATE_CYCLE.length];
    setStorageItem(MENU_COLLAPSED_STORAGE_KEY, next, 'local');
    set({ menuCollapsedState: next });
  },
}));
