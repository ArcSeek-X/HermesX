/**
 * @file uiText.ts
 * @description i18n 文案入口文件，聚合中英文配置并导出统一的类型、工具函数
 * @module i18n
 */

import zh from './uiText-zh';
import en from './uiText-en';
import type { UiTextKey } from './uiText-zh';

export type UiLanguage = 'zh' | 'en';

export type { UiTextKey };

export const UI_TEXT: Record<UiLanguage, Record<UiTextKey, string>> = {
  zh,
  en,
};

export type UiTextParams = Record<string, string | number>;

export function formatUiText(template: string, params?: UiTextParams): string {
  if (!params) {
    return template;
  }

  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    const value = params[key];
    return value === undefined ? match : String(value);
  });
}
