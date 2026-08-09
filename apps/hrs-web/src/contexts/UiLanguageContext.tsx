/**
 * @file UiLanguageContext.tsx
 * @description 界面语言上下文，提供多语言切换和文案翻译能力（zh / en）
 * @module contexts
 */

import type React from 'react';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { formatUiText, UI_TEXT, type UiLanguage, type UiTextKey, type UiTextParams } from '../i18n/uiText';
import { getRuntimeInitialLanguage, getUiLanguageStorage, persistUiLanguage } from '../utils/uiLanguage';

/**
 * 界面语言上下文值类型定义
 */
type UiLanguageContextValue = {
  /** 当前界面语言 */
  language: UiLanguage;
  /** 切换界面语言 */
  setLanguage: (language: UiLanguage) => void;
  /** 翻译函数：根据 key 和可选参数获取当前语言的文案 */
  t: (key: UiTextKey, params?: UiTextParams) => string;
};

/**
 * 降级上下文值
 * 当组件在 Provider 外部使用时提供默认的中文翻译，避免崩溃
 */
const fallbackContext: UiLanguageContextValue = {
  language: 'zh',
  setLanguage: () => undefined,
  t: (key, params) => formatUiText(UI_TEXT.zh[key], params),
};

const UiLanguageContext = createContext<UiLanguageContextValue | null>(null);

/**
 * 界面语言上下文 Provider 组件
 *
 * 在应用根层包裹此 Provider，后代组件即可通过 useUiLanguage() 获取当前语言和翻译函数。
 * 语言偏好会持久化到存储（localStorage / sessionStorage），并在切换时同步 document.lang。
 *
 * @param children - 子组件
 */
export const UiLanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 初始化语言：从运行时存储中读取，无存储时使用默认值
  const [language, setLanguageState] = useState<UiLanguage>(getRuntimeInitialLanguage);

  /**
   * 切换语言并持久化到存储
   * @param nextLanguage - 目标语言
   */
  const setLanguage = useCallback((nextLanguage: UiLanguage) => {
    setLanguageState(nextLanguage);
    persistUiLanguage(getUiLanguageStorage(), nextLanguage);
  }, []);

  // 语言切换时同步 <html lang="..."> 属性，用于辅助功能和 SEO
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
    }
  }, [language]);

  // 使用 useMemo 缓存上下文值，仅当 language 或 setLanguage 变化时重新创建
  const value = useMemo<UiLanguageContextValue>(() => ({
    language,
    setLanguage,
    t: (key, params) => formatUiText(UI_TEXT[language][key], params),
  }), [language, setLanguage]);

  return (
    <UiLanguageContext.Provider value={value}>
      {children}
    </UiLanguageContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components -- useUiLanguage is a hook, co-located for context access
/**
 * 界面语言上下文 Hook
 * 必须在 UiLanguageProvider 内部使用；在 Provider 外部使用时返回降级上下文（中文）
 * @returns 界面语言上下文值
 */
export function useUiLanguage(): UiLanguageContextValue {
  return useContext(UiLanguageContext) ?? fallbackContext;
}
