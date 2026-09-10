/**
 * @fileoverview 组件文档页：HrsButton（通用按钮）
 * 路由地址 /docs/component/button，菜单名「按钮」。
 * 用于演示 HrsButton 的视觉变体、尺寸档位、加载态、禁用态、发光效果与 onClick 事件桥接。
 * @module pages
 */

import React, { useState } from 'react';
import { AppPage, HrsButton } from '../../../components';
import type { HrsButtonVariant } from '../../../components/basic/HrsButton';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 主操作类变体（示例一展示） */
const PRIMARY_VARIANTS: HrsButtonVariant[] = ['primary', 'primary-soft', 'gradient', 'secondary', 'outline', 'ghost'];
/** 语义类变体（示例二展示） */
const SEMANTIC_VARIANTS: HrsButtonVariant[] = ['danger', 'danger-soft', 'success', 'success-soft', 'warning', 'warning-soft'];
/** 尺寸档位（示例三展示） */
const SIZES = ['xs', 'sm', 'md', 'lg', 'xl'] as const;

/**
 * 按钮组件文档演示页。
 *
 * HrsButton 基于 HeroUI Button 二次封装：通过 variant 选择视觉风格、size 选择尺寸档位，
 * 支持 isLoading 加载态（旋转图标 + 文案）、glow 发光效果与 isDisabled 禁用态；
 * onClick 在组件内部桥接为 HeroUI 的 onPress，调用方按原生 onClick 使用即可。
 */
export const DocsButtonPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例四：加载态（点击后模拟 2s 请求，期间按钮自动禁用）
  const [saving, setSaving] = useState(false);
  // 示例六：onClick 事件桥接（点击计数）
  const [clickCount, setClickCount] = useState(0);

  /** 模拟异步保存：进入加载态 2 秒后恢复 */
  const handleSave = () => {
    setSaving(true);
    window.setTimeout(() => setSaving(false), 2000);
  };

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsButton.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Button 封装的通用按钮（HrsButton）。18 种语义化变体、5 档尺寸、加载态（isLoading）
            与发光效果（glow）；onClick 在内部桥接为 HeroUI 的 onPress，原生属性（type / aria-* 等）全部透传。
          </p>
        </header>

        {/* 1. 主操作类变体 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：主操作类变体</h2>
          <p className="text-xs text-muted">
            primary（主色渐变）/ primary-soft（淡主色）/ gradient（青紫渐变）/ secondary / outline / ghost。
          </p>
          <div className="flex flex-wrap items-center gap-3">
            {PRIMARY_VARIANTS.map((v) => (
              <HrsButton key={v} variant={v}>{v}</HrsButton>
            ))}
          </div>
        </section>

        {/* 2. 语义类变体 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：语义类变体</h2>
          <p className="text-xs text-muted">
            danger / success / warning 三组语义色，每组含实心与 -soft 淡色两种。
          </p>
          <div className="flex flex-wrap items-center gap-3">
            {SEMANTIC_VARIANTS.map((v) => (
              <HrsButton key={v} variant={v}>{v}</HrsButton>
            ))}
          </div>
        </section>

        {/* 3. 尺寸对比 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：尺寸对比（size）</h2>
          <p className="text-xs text-muted">
            size 支持 xs / sm / md / lg / xl（默认 sm），字重随档位递增：md 及以下 font-medium、lg 为 font-semibold、xl 为 font-bold。
          </p>
          <div className="flex flex-wrap items-center gap-3">
            {SIZES.map((s) => (
              <HrsButton key={s} size={s}>size={s}</HrsButton>
            ))}
          </div>
        </section>

        {/* 4. 加载态 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：加载态（isLoading）</h2>
          <p className="text-xs text-muted">
            isLoading 为 true 时展示旋转图标 + 文案（loadingText 自定义，缺省回退 i18n 的「处理中...」），期间按钮自动禁用。
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <HrsButton variant="primary" isLoading={saving} onClick={handleSave}>保存设置</HrsButton>
            <HrsButton variant="secondary" isLoading loadingText="加载中...">模拟加载</HrsButton>
            <HrsButton variant="danger" isLoading={saving} onClick={handleSave}>删除</HrsButton>
          </div>
        </section>

        {/* 5. 禁用态与发光 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：禁用态（isDisabled）与发光（glow）</h2>
          <p className="text-xs text-muted">
            isDisabled 禁用按钮（降透明度 + 禁止交互）；glow 为按钮叠加青色发光效果（shadow-glow-cyan）。
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <HrsButton isDisabled>禁用按钮</HrsButton>
            <HrsButton variant="gradient" isDisabled>渐变禁用</HrsButton>
            <HrsButton variant="primary" glow>发光按钮</HrsButton>
            <HrsButton variant="gradient" glow>渐变发光</HrsButton>
          </div>
        </section>

        {/* 6. onClick 事件桥接 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例六：onClick 事件桥接</h2>
          <p className="text-xs text-muted">
            HrsButton 内部将 onClick 桥接为 HeroUI 的 onPress，调用方按原生 onClick 使用即可；下方计数验证桥接生效。
          </p>
          <span className="text-xs text-secondary-text">已点击 {clickCount} 次</span>
          <div className="flex flex-wrap items-center gap-3">
            <HrsButton onClick={() => setClickCount((c) => c + 1)}>点击 +1</HrsButton>
            <HrsButton variant="secondary" onClick={() => setClickCount(0)}>清零</HrsButton>
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsButtonPage;
