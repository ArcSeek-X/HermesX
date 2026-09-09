/**
 * ModeSwitch
 *
 * 头部「运行模式」入口：单一图标按钮，点击即在 常规 / 调试 之间切换。
 * 按钮内显示当前模式简称（常规 / 调试），图标随模式变化以直观区分。
 * 切换后持久化到 localStorage，供全站按需读取（如调试面板显隐）。
 */
import { useEffect, useState } from 'react';
import { Bug, CircleDot } from 'lucide-react';

/** 运行模式：常规 / 调试 */
export type AppMode = 'normal' | 'debug';

const STORAGE_KEY = 'hrs.appMode';

export const ModeSwitch = () => {
  const [mode, setMode] = useState<AppMode>(() => {
    const saved = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null;
    return saved === 'debug' ? 'debug' : 'normal';
  });

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const isDebug = mode === 'debug';
  const shortLabel = isDebug ? '调试' : '常规';
  const nextMode: AppMode = isDebug ? 'normal' : 'debug';

  return (
    <button
      type="button"
      onClick={() => setMode(nextMode)}
      aria-label={shortLabel}
      title={shortLabel}
      aria-pressed={isDebug}
      className="inline-flex h-9 select-none items-center gap-1.5 rounded-[10px] border border-border/70 bg-card/80 px-2.5 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
    >
      {isDebug ? <Bug className="h-4 w-4" /> : <CircleDot className="h-4 w-4" />}
      <span aria-hidden className="text-[12px] font-semibold leading-none tracking-tight">
        {shortLabel}
      </span>
    </button>
  );
};
