/**
 * @fileoverview 组件文档页：AnimCard（动画卡片）
 * 路由地址 /docs/component/animCard，菜单名「动画卡片」。
 * 用于演示 AnimCard 的基础样式、错位入场动画、渐变边框与渐变背景。
 * @module pages
 */

import React from 'react';
import { AppPage, AnimCard } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/**
 * 动画卡片组件文档演示页。
 *
 * AnimCard 是统一封装的动画卡片容器：自带 rounded-lg / border / bg-card 基础样式与
 * 「淡入 + 上移」入场动画；ordinal 控制错位延迟，variant=gradient 启用渐变边框，
 * gradientBackground 叠加主题色渐变背景。
 */
export const DocsAnimCardPage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsAnimCard.title')}</h1>
          <p className="text-xs text-muted">
            统一封装的动画卡片容器（AnimCard）。自带 rounded-lg / border / bg-card 基础样式与「淡入 + 上移」入场动画；
            ordinal 错位延迟逐个加载，支持 gradient 渐变边框与 gradientBackground 主题色渐变背景。
          </p>
        </header>

        {/* 1. 基础卡片 + 错位入场 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：基础卡片 + ordinal 错位入场</h2>
          <p className="text-xs text-muted">
            ordinal 从 0 起算，每张卡片按 ordinal * 0.05s 错位延迟入场，形成逐个淡入上移的效果（刷新页面可重看动画）。
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <AnimCard key={i} ordinal={i} className="flex min-h-24 flex-col justify-center gap-1 p-5">
                <span className="text-sm font-medium text-primary-text">卡片 {i + 1}</span>
                <span className="text-xs text-muted-text">ordinal={i}，入场延迟 {(i * 0.05).toFixed(2)}s</span>
              </AnimCard>
            ))}
          </div>
        </section>

        {/* 2. 渐变边框 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：渐变边框（variant=gradient）</h2>
          <p className="text-xs text-muted">
            gradient 变体为双层结构（外层渐变衬底 + 内层底色盖板）形成渐变描边；gradBorderAngle 控制渐变角度（默认 135°）。
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            <AnimCard variant="gradient" className="flex min-h-24 flex-col justify-center gap-1 p-5">
              <span className="text-sm font-medium text-primary-text">135°（默认）</span>
              <span className="text-xs text-muted-text">gradBorderAngle=135</span>
            </AnimCard>
            <AnimCard variant="gradient" gradBorderAngle={45} className="flex min-h-24 flex-col justify-center gap-1 p-5">
              <span className="text-sm font-medium text-primary-text">45°</span>
              <span className="text-xs text-muted-text">gradBorderAngle=45</span>
            </AnimCard>
            <AnimCard variant="gradient" gradBorderAngle={270} className="flex min-h-24 flex-col justify-center gap-1 p-5">
              <span className="text-sm font-medium text-primary-text">270°</span>
              <span className="text-xs text-muted-text">gradBorderAngle=270</span>
            </AnimCard>
          </div>
        </section>

        {/* 3. 渐变背景 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：渐变背景（gradientBackground）</h2>
          <p className="text-xs text-muted">
            gradientBackground 叠加左上角淡蓝色径向渐变 + 顶部白色线性高光，颜色随主题色（--primary）换肤。
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <AnimCard gradientBackground className="flex min-h-28 flex-col justify-center gap-1 p-5">
              <span className="text-sm font-medium text-primary-text">渐变背景卡片</span>
              <span className="text-xs text-muted-text">gradientBackground=true</span>
            </AnimCard>
            <AnimCard gradientBackground variant="gradient" className="flex min-h-28 flex-col justify-center gap-1 p-5">
              <span className="text-sm font-medium text-primary-text">渐变背景 + 渐变边框</span>
              <span className="text-xs text-muted-text">两者可叠加使用</span>
            </AnimCard>
          </div>
        </section>

        {/* 4. 网格组合 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：网格布局组合</h2>
          <p className="text-xs text-muted">
            在 grid 容器中混合 default / gradient / gradientBackground 三种形态，ordinal 使整组卡片按顺序错位入场。
          </p>
          <div className="grid gap-4 sm:grid-cols-4">
            {[
              { variant: 'default' as const, gradientBackground: false, label: 'default' },
              { variant: 'gradient' as const, gradientBackground: false, label: 'gradient' },
              { variant: 'default' as const, gradientBackground: true, label: 'gradientBackground' },
              { variant: 'gradient' as const, gradientBackground: true, label: 'gradient + 背景' },
            ].map((cfg, i) => (
              <AnimCard
                key={cfg.label}
                ordinal={i}
                variant={cfg.variant}
                gradientBackground={cfg.gradientBackground}
                className="flex min-h-24 items-center justify-center p-4 text-center"
              >
                <span className="text-xs font-medium text-primary-text">{cfg.label}</span>
              </AnimCard>
            ))}
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsAnimCardPage;
