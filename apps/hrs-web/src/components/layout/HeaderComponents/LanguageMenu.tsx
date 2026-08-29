/**
 * LanguageMenu
 *
 * 头部「界面语言」入口：单一图标按钮，点击即在中文 / English 之间切换。
 * 图标随当前语言展示：中文显示文字「文」、英文显示「EN」（区分直观）。
 * 切换后由 useUiLanguage 持久化到 localStorage 并触发全站文案重渲染。
 */
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiLanguage } from '../../../i18n/uiText';

export const LanguageMenu = () => {
  const { t, language, setLanguage } = useUiLanguage();
  // 三语循环切换：简体中文 -> 繁體中文 -> English -> 简体中文
  const nextLanguage: UiLanguage = language === 'zh' ? 'zh-Hant' : language === 'zh-Hant' ? 'en' : 'zh';
  const shortLabel = language === 'zh' ? t('language.short.zh') : language === 'zh-Hant' ? t('language.short.zhHant') : t('language.short.en');

  return (
    <button
      type="button"
      onClick={() => setLanguage(nextLanguage)}
      aria-label={t('layout.header.language')}
      title={t('layout.header.language')}
      className="inline-flex h-9 w-9 select-none items-center justify-center rounded-[10px] border border-border/70 bg-card/80 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
    >
      <span
        aria-hidden
        className="text-[12px] font-semibold leading-none tracking-tight"
      >
        {shortLabel}
      </span>
    </button>
  );
};