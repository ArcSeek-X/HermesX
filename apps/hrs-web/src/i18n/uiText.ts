/**
 * @file uiText.ts
 * @description i18n 主字典入口：聚合 zh / zh-Hant / en 三语文案，并导出统一的语言类型与翻译工具
 * @module i18n
 *
 * ## 它解决什么问题
 * 全站通用 UI 文案（按钮、标题、导航、提示语等）需要支持多语言且 key 集合保持一致。
 * 本文件把三语文案聚合为单一 `UI_TEXT` 字典，并统一 `UiLanguage` 类型与 `formatUiText()` 模板渲染，
 * 让所有组件用同一套 key 访问文案，避免散落各处的硬编码字符串和语言不一致。
 *
 * ## 与其他模块的关系（上下游）
 * - 上游（文案来源，本文件 import）：
 *   - `uiText-zh.ts`：简体中文文案，定义 `UiTextKey` 类型（key 的真相来源，三语必须对齐）。
 *   - `uiText-zh-Hant.ts`：繁体中文文案，key 集合与 zh 完全一致（真繁体翻译）。
 *   - `uiText-en.ts`：英文文案。
 * - 下游（消费者）：
 *   - `contexts/UiLanguageContext.tsx`：在 `t()` 中通过 `UI_TEXT[language][key]` 命中主字典，
 *   - 任意组件：通过 `useUiLanguage().t(key, params)` 或直接使用 `formatUiText(UI_TEXT[language][key], params)`。
 *   - `utils/uiLanguage.ts`：消费 `UiLanguage` 类型，提供 `toCnOrEn()` 等业务字典回退工具。
 *
 * ## 责任边界
 * - 主字典只覆盖「全站通用 UI 文案」，且三语齐全（含真繁体）。
 * - 业务域本地字典（告警/回测/组合等，只有 zh/en）不在此文件，其繁体回退由消费方的 `toCnOrEn()` 负责。
 * - 新增文案：必须同时在 zh / zh-Hant / en 三份文件中补同一 key，否则 `UI_TEXT` 类型会报错。
 */

import zh from './uiText-zh';
import zhHant from './uiText-zh-Hant';
import en from './uiText-en';
import type { UiTextKey } from './uiText-zh';

/** 支持的语言：简体中文 / 繁体中文 / 英文。繁体 'zh-Hant' 为主字典真繁体，业务字典回退在 toCnOrEn()。 */
export type UiLanguage = 'zh' | 'zh-Hant' | 'en';

export type { UiTextKey };

/** 三语主字典：以 UiTextKey 为第一层 key，语言为第二层。三语文案 key 集合必须对齐。 */
export const UI_TEXT: Record<UiLanguage, Record<UiTextKey, string>> = {
  zh,
  'zh-Hant': zhHant,
  en,
};

/** 模板参数：用于 {name} 形式的占位符替换 */
export type UiTextParams = Record<string, string | number>;

/**
 * 将模板中的 {key} 占位符替换为 params 中对应的值。
 * 未提供参数的占位符原样保留（不抛错），保证单语/缺参场景下也能安全渲染。
 * @param template - 含 {key} 占位符的文案模板
 * @param params - 可选的参数映射
 * @returns 渲染后的字符串
 */
export function formatUiText(template: string, params?: UiTextParams): string {
  if (!params) {
    return template;
  }

  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    const value = params[key];
    return value === undefined ? match : String(value);
  });
}
