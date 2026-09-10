/**
 * @file SettingsLoading.tsx
 * @description 设置页加载态组件：设置数据加载中的占位骨架/提示。
 * 使用场景：设置页数据加载期间。
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';

export const SettingsLoading: React.FC = () => {
  return (
    <div className="space-y-4 animate-fade-in">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="rounded-[1.15rem] border settings-border bg-[var(--settings-surface)] p-4 shadow-soft-card">
          <div className="settings-skeleton-strong h-3 w-32 rounded" />
          <div className="settings-skeleton-soft mt-3 h-10 rounded-lg" />
        </div>
      ))}
    </div>
  );
};
