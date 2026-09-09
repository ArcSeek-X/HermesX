/**
 * @file AppModeContext.tsx
 * @description 应用模式上下文：产品使用模式（productModel）/ 开发调试模式（developmentMode）
 * @module contexts
 *
 * ## 它解决什么问题
 * 头部 ModeSwitch 与侧边栏 SidebarNav 位于不同子树，模式状态必须提升到全局才能联动。
 * 本文件收敛模式的唯一真相来源（含 localStorage 持久化），供两处共享。
 *
 * ## 模式语义
 * - productModel：产品使用模式，侧边栏呈现产品菜单
 * - developmentMode：开发调试模式，侧边栏呈现调试菜单
 *
 * ## 降级策略
 * 未包裹 Provider 时（如单测直接渲染组件）回退到 productModel，保证组件不崩溃。
 */
import type React from 'react';
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

/** 应用模式：productModel=产品使用模式，developmentMode=开发调试模式 */
export type AppMode = 'productModel' | 'developmentMode';

const STORAGE_KEY = 'hrs.appMode';

/** 读取持久化的模式，无存储或值非法时回退到产品使用模式 */
const getInitialMode = (): AppMode => {
  const saved = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null;
  return saved === 'developmentMode' ? 'developmentMode' : 'productModel';
};

type AppModeContextValue = {
  /** 当前应用模式 */
  mode: AppMode;
  /** 是否处于开发调试模式 */
  isDevelopmentMode: boolean;
  /** 直接设定模式并持久化 */
  setMode: (mode: AppMode) => void;
  /** 在两个模式间来回切换 */
  toggleMode: () => void;
};

const fallbackContext: AppModeContextValue = {
  mode: 'productModel',
  isDevelopmentMode: false,
  setMode: () => undefined,
  toggleMode: () => undefined,
};

const AppModeContext = createContext<AppModeContextValue | null>(null);

/** 应用模式 Provider，需包裹所有消费模式的子树（头部 + 侧边栏） */
export const AppModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<AppMode>(getInitialMode);

  const persist = useCallback((next: AppMode) => {
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const setMode = useCallback((next: AppMode) => {
    setModeState(next);
    persist(next);
  }, [persist]);

  const toggleMode = useCallback(() => {
    setModeState((prev) => {
      const next: AppMode = prev === 'developmentMode' ? 'productModel' : 'developmentMode';
      persist(next);
      return next;
    });
  }, [persist]);

  const value = useMemo<AppModeContextValue>(
    () => ({ mode, isDevelopmentMode: mode === 'developmentMode', setMode, toggleMode }),
    [mode, setMode, toggleMode]
  );

  return <AppModeContext.Provider value={value}>{children}</AppModeContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components -- useAppMode is a hook, co-located for context access
/** 获取应用模式；在 Provider 外部使用时返回降级值（productModel） */
export function useAppMode(): AppModeContextValue {
  return useContext(AppModeContext) ?? fallbackContext;
}
