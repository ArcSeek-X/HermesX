/**
 * ModeSwitch
 *
 * 头部「运行模式」入口：单一图标按钮，点击即在 产品使用模式 / 开发调试模式 之间切换。
 * 按钮内显示当前模式简称（常规 / 调试），图标随模式变化以直观区分。
 * 模式状态由 AppModeContext 统一持有（持久化到 localStorage），切换后侧边栏菜单随之切换。
 */
import { Bug, CircleDot } from 'lucide-react';
import { useAppMode } from '../../../contexts/AppModeContext';

export const ModeSwitch = () => {
  const { isDevelopmentMode, toggleMode } = useAppMode();
  const shortLabel = isDevelopmentMode ? '调试' : '常规';

  return (
    <button
      type="button"
      onClick={toggleMode}
      aria-label={shortLabel}
      title={shortLabel}
      aria-pressed={isDevelopmentMode}
      className="inline-flex h-9 select-none items-center gap-1.5 rounded-[10px] border border-border/70 bg-card/80 px-2.5 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
    >
      {isDevelopmentMode ? <Bug className="h-4 w-4" /> : <CircleDot className="h-4 w-4" />}
      <span aria-hidden className="text-[12px] font-semibold leading-none tracking-tight">
        {shortLabel}
      </span>
    </button>
  );
};
