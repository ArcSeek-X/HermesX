/**
 * UI 语言解析与持久化工具
 *
 * 作用：统一管理前端界面语言（目前支持 zh / en）的初始解析、读取与持久化。
 * 初始语言优先级：localStorage 中已保存的用户选择 > 浏览器语言首选项；并提供
 * SSR 安全（typeof window 判断）的运行时入口，保证服务端渲染与客户端表现一致。
 */

import type { UiLanguage } from '../i18n/uiText';

/**
 * 将界面语言收敛为「简体中文 / 英文」二元，供仅支持中英双语的本地字典与
 * 格式化函数使用。繁體中文(zh-Hant)回退到简体中文(zh)，避免索引/参数类型报错。
 *
 * @param language - 当前界面语言
 * @returns 'zh' | 'en'
 */
export function toCnOrEn(language: UiLanguage): 'zh' | 'en' {
  return language === 'en' ? 'en' : 'zh';
}

/** 界面语言在 localStorage 中的存储键名 */
export const UI_LANGUAGE_STORAGE_KEY = 'hrs.uiLanguage';

/**
 * 将任意输入规范化为受支持的语言枚举，非法值返回 null。
 *
 * @param value - 待检查的值
 * @returns 'zh' | 'zh-Hant' | 'en' 或 null
 */
export function normalizeUiLanguage(value?: string | null): UiLanguage | null {
  if (value === 'zh' || value === 'zh-Hant' || value === 'en') {
    return value;
  }
  return null;
}

/**
 * 从给定 Storage 中读取已保存的语言偏好。
 * Storage 不存在或读取异常时返回 null。
 */
function getStoredUiLanguage(storage?: Storage | null): UiLanguage | null {
  if (!storage) {
    return null;
  }

  try {
    return normalizeUiLanguage(storage.getItem(UI_LANGUAGE_STORAGE_KEY));
  } catch {
    return null;
  }
}

/**
 * 获取运行时的 localStorage 引用（非浏览器环境返回 null）。
 */
export function getUiLanguageStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/**
 * 将用户选择的语言持久化到 Storage。
 * Storage 不可用时静默忽略（内存中的语言状态仍会生效）。
 *
 * @param storage - Storage 实例（可为 null）
 * @param language - 要保存的语言
 */
export function persistUiLanguage(storage: Storage | null, language: UiLanguage): void {
  if (!storage) {
    return;
  }

  try {
    storage.setItem(UI_LANGUAGE_STORAGE_KEY, language);
  } catch {
    // 忽略存储失败；内存中的语言仍会更新
  }
}

/**
 * 根据浏览器语言列表推断界面语言：命中 zh 前缀走中文，命中 en 前缀走英文，
 * 否则默认中文。
 *
 * @param navigatorLike - 提供 language/languages 的浏览器对象（可注入便于测试）
 */
function getBrowserUiLanguage(navigatorLike?: Pick<Navigator, 'language' | 'languages'> | null): UiLanguage {
  const languageCandidates = [
    ...(Array.isArray(navigatorLike?.languages) ? navigatorLike?.languages ?? [] : []),
    navigatorLike?.language,
  ].filter((language): language is string => Boolean(language));

  for (const candidate of languageCandidates) {
    const normalized = candidate.toLowerCase();
    if (normalized.startsWith('zh')) {
      // 繁體中文區域（台灣/香港/澳門）走 zh-Hant，其余简体走 zh
      if (normalized.startsWith('zh-tw') || normalized.startsWith('zh-hant') || normalized.startsWith('zh-hk') || normalized.startsWith('zh-mo')) {
        return 'zh-Hant';
      }
      return 'zh';
    }
    if (normalized.startsWith('en')) {
      return 'en';
    }
  }

  return 'zh';
}

/**
 * 解析初始界面语言：优先使用已保存偏好，否则回退到浏览器语言。
 *
 * @param storage - Storage 实例
 * @param navigatorLike - 浏览器语言对象
 */
export function resolveInitialUiLanguage({
  storage,
  navigatorLike,
}: {
  storage?: Storage | null;
  navigatorLike?: Pick<Navigator, 'language' | 'languages'> | null;
} = {}): UiLanguage {
  const stored = getStoredUiLanguage(storage);
  if (stored) {
    return stored;
  }

  return getBrowserUiLanguage(navigatorLike);
}

/**
 * 运行时（浏览器）初始语言入口：在非浏览器环境默认返回中文，否则结合
 * localStorage 与 window.navigator 解析。供应用初始化时调用。
 */
export function getRuntimeInitialLanguage(): UiLanguage {
  if (typeof window === 'undefined') {
    return 'zh';
  }

  return resolveInitialUiLanguage({
    storage: getUiLanguageStorage(),
    navigatorLike: window.navigator,
  });
}
