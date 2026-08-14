/**
 * @file UiLanguageContext.tsx
 * @description 界面语言上下文，提供多语言切换与文案翻译能力（zh / zh-Hant / en）
 * @module contexts
 *
 * ## 它解决什么问题
 * 全站 UI 文案需要跟随用户语言实时切换，且语言偏好要在刷新后保持。
 * 本文件把「当前语言状态 + 切换动作 + 翻译函数 t()」收敛到一个 React Context 里，
 * 避免每个组件各自维护语言状态或重复读取存储。
 *
 * ## 与其他模块的关系（上下游）
 * - 上游（数据来源）：
 *   - `utils/uiLanguage.ts`
 *     - `getRuntimeInitialLanguage()`：Provider 初始化时读取语言（优先级：运行时注入 > 持久化存储 > 浏览器语言推断 > 默认 zh）。
 *     - `getUiLanguageStorage()` / `persistUiLanguage()`：切换时把语言写入存储，供下次启动恢复。
 *     - `toCnOrEn(language)`：把繁体 'zh-Hant' 折叠回 'zh'，供**业务字典**（只有 zh/en 的本地化表，如 featureText.ts）安全取值。
 *   - `i18n/uiText.ts`
 *     - `UI_TEXT`：三语齐全的主字典（含真繁体），经 `formatUiText()` 渲染后由 `t()` 暴露给组件。
 *     - `UiLanguage` 类型在此定义为 `'zh' | 'zh-Hant' | 'en'`。
 * - 下游（消费者）：
 *   - 任意后代组件通过 `useUiLanguage()` 拿到 `language / setLanguage / t`。
 *   - 主字典文案走 `t()`（真繁体，不经过toCnOrEn）。
 *   - 业务域本地字典（告警/回测/组合等）在消费方用 `toCnOrEn(language)` 做键，繁体模式下回退简体。
 *
 * ## 繁体支持的责任边界
 * 本文件负责「语言状态的真相来源 + document.lang 同步」；
 * 繁体字典的真繁体翻译在 `uiText-zh-Hant.ts`，业务字典的繁体回退在消费方的 `toCnOrEn()`。
 * 三者分工，本文件不直接持有任何业务文案。
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

  // 语言切换时同步 <html lang="..."> 属性，用于辅助功能和 SEO。
  // 繁体 'zh-Hant' 直接透传（与 uiText-zh-Hant.ts 的主字典繁体文案保持一致），
  // 简体映射为 'zh-CN'，英文为 'en'。
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = language === 'en' ? 'en' : language === 'zh-Hant' ? 'zh-Hant' : 'zh-CN';
    }
  }, [language]);

  // 使用 useMemo 缓存上下文值，仅当 language 或 setLanguage 变化时重新创建。
  // t() 直接命中三语主字典 UI_TEXT[language]，繁体下返回真繁体文案，不经过 toCnOrEn。
  // （业务字典的繁体回退由各自消费方的 toCnOrEn(language) 负责，不在本 Context 内。）
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
