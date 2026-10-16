/**
 * FullscreenToggle
 *
 * 头部「全屏」入口：单一图标按钮，点击即在整篇文档（document.documentElement）
 * 上切换浏览器全屏；按 ESC 由浏览器原生退出全屏。图标随状态切换：非全屏显示
 * 四角括号（Maximize），全屏显示四支向内箭头（Shrink）。
 * 底层复用 basic/Screenfull 的 useScreenfull Hook；浏览器不支持全屏时按钮
 * 自动禁用，避免无效点击。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import { Maximize, Shrink } from 'lucide-react';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useScreenfull } from '../../basic/Screenfull';

export const FullscreenToggle = () => {
  const { t } = useUiLanguage();
  // 全局头部切换作用于整篇文档；isEnabled 用于在不支持全屏时禁用按钮
  const { isFullscreen, isEnabled, toggle } = useScreenfull();
  // 文案随状态切换：全屏时提示"退出全屏"，否则提示"全屏"
  const label = isFullscreen ? t('layout.header.exitFullscreen') : t('layout.header.fullscreen');

  return (
    <button
      type="button"
      onClick={() => toggle()}
      disabled={!isEnabled}
      aria-label={label}
      title={label}
      className="inline-flex h-9 w-9 select-none items-center justify-center rounded-[10px] border border-border/70 bg-card/80 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
    >
      {isFullscreen ? (
        <Shrink className="h-4 w-4" aria-hidden />
      ) : (
        <Maximize className="h-4 w-4" aria-hidden />
      )}
    </button>
  );
};
