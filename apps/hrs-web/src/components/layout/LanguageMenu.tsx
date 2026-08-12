/**
 * LanguageMenu
 *
 * 头部「界面语言」入口：单一图标按钮，点击即在中文 / English 之间切换。
 * 图标随当前语言展示：中文显示 Sun，英文显示 Moon（区分直观、视觉一致）。
 * 切换后由 useUiLanguage 持久化到 localStorage 并触发全站文案重渲染。
 */
import { Moon, Sun } from 'lucide-react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

export const LanguageMenu = () => {
  const { t, language, setLanguage } = useUiLanguage();
  const nextLanguage = language === 'zh' ? 'en' : 'zh';
  const isChinese = language === 'zh';

  return (
    <button
      type="button"
      onClick={() => setLanguage(nextLanguage)}
      aria-label={t('header.language')}
      title={t('header.language')}
      className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] border border-border/70 bg-card/80 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
    >
      {isChinese ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
};