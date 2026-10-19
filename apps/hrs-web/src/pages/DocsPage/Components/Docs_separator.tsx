/**
 * Separator 组件文档演示页：方向、颜色变体、渐隐渐变与垂直分割。
 */

import React from 'react';
import { Separator, type HrsSeparatorVariant } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';

/** 颜色变体（示例一 / 二展示） */
const SEPARATOR_VARIANTS: HrsSeparatorVariant[] = ['default', 'secondary', 'tertiary'];

/**
 * 分割线组件文档演示页。
 *
 * Separator 基于 HeroUI Separator 封装：orientation 控制方向（水平占满宽度 / 垂直占满高度）、
 * variant 控制颜色（default / secondary / tertiary，颜色由 HeroUI 主题 token 提供并自动跟随明暗主题）、
 * gradient 叠加两端渐隐渐变；间距等布局属性由使用方通过 className 控制。
 */
export const DocsSeparatorPage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsSeparator.title')}</h1>
          <p className="text-xs text-muted">
            从 Modal / Drawer 的 Header-Body 分割线抽象而来的通用分割线（Separator）。粗细固定 1px，
            支持水平 / 垂直方向、default / secondary / tertiary 三档颜色变体与两端渐隐渐变（gradient）。
          </p>
        </header>

        {/* 1. 水平三档颜色变体 */}
        <DocsSection title="示例一：水平分割线（variant）" description="default / secondary / tertiary 三档颜色变体（对齐 HeroUI 规格），颜色由主题 token（--separator 系列）提供，自动跟随明暗主题。">
          <div className="flex flex-col gap-4">
            {SEPARATOR_VARIANTS.map((variant) => (
              <div key={variant} className="flex flex-col gap-1">
                <span className="text-[11px] text-muted">variant={variant}</span>
                <Separator variant={variant} />
              </div>
            ))}
          </div>
        </DocsSection>

        {/* 2. 两端渐隐渐变 */}
        <DocsSection title="示例二：两端渐隐渐变（gradient）" description="gradient 在当前 variant 颜色基础上叠加两端 10% ~ 90% 渐隐到透明，视觉更轻，适合卡片 / 弹窗内（Modal 内同款效果）。">
          <div className="flex flex-col gap-4">
            {SEPARATOR_VARIANTS.map((variant) => (
              <div key={variant} className="flex flex-col gap-1">
                <span className="text-[11px] text-muted">variant={variant} + gradient</span>
                <Separator variant={variant} gradient />
              </div>
            ))}
          </div>
        </DocsSection>

        {/* 3. 垂直分割线 */}
        <DocsSection title="示例三：垂直分割线（orientation=vertical）" description="vertical 方向默认占满父容器高度；在 flex row 容器中用 self-stretch 撑满（newsCard 中的时间轴同款用法）。">
          <div className="flex h-28 items-stretch gap-3 rounded-md border border-border/70 bg-card p-4">
            <div className="flex flex-1 items-center justify-center rounded-sm bg-primary-faint text-xs text-secondary-text">左侧区域</div>
            <Separator orientation="vertical" variant="default" gradient className="mx-1 self-stretch" />
            <div className="flex flex-1 items-center justify-center rounded-sm bg-primary-faint text-xs text-secondary-text">右侧区域</div>
            <Separator orientation="vertical" variant="secondary" className="mx-1 self-stretch" />
            <div className="flex flex-1 items-center justify-center rounded-sm bg-primary-faint text-xs text-secondary-text">第三列</div>
          </div>
        </DocsSection>

        {/* 4. 组合场景：模拟 Modal 的 Header-Body 分割 */}
        <DocsSection
          title="示例四：组合场景（模拟弹窗 Header-Body 分割）"
          description={
            <>
              Modal / Drawer 内部即使用 <code className="rounded bg-surface-2 px-1">Separator（default
              + gradient + my-3）</code> 作为 Header 与 Body 之间的分割线。
            </>
          }
        >
          <div className="overflow-hidden rounded-xl border border-border/70 bg-elevated shadow-lg">
            <div className="flex items-center gap-2 px-4 py-3">
              <h3 className="text-sm font-medium text-primary-text">面板标题（Header）</h3>
            </div>
            <Separator gradient className="my-3" />
            <div className="px-4 pb-4">
              <p className="text-xs leading-5 text-secondary-text">
                这里是 Body 内容区。上方的分割线为 default 变体 + 两端渐隐渐变，与 Modal / Drawer 内部渲染效果完全一致。
              </p>
            </div>
            <Separator gradient className="my-3" />
            <div className="flex justify-end gap-2 px-4 py-3">
              <span className="text-xs text-muted-text">Footer 区域（Body-Footer 分割线对称）</span>
            </div>
          </div>
        </DocsSection>
      </div>
    </AppPage>
  );
};

export default DocsSeparatorPage;
