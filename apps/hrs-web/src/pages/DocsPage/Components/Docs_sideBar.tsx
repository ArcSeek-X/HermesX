/**
 * @fileoverview 组件文档页：侧边栏 / Sidebar
 * 路由地址 /docs/component/sideBar，菜单名「侧边栏」。
 * 演示两块内容：
 * 1) 应用自身主导航 SidebarNavOld（default / rail 形态 + collapsed 折叠态）
 * 2) SidebarNav：轻量自研侧栏（纯 React + Tailwind，接入真实菜单数据）
 * @module pages
 */

import React, { useState } from 'react';
import { HrsButton } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { SidebarNavOld } from '@components/layout/SideBar/SidebarNav-old';
import { SidebarNav } from '@components/layout/SideBar/SidebarNav';
import type { SidebarTheme } from '@components/layout/SideBar/SidebarNav';
import type { MenuCollapsedState } from '../../../stores';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 预览区宽度：随 variant / collapsed 变化，模拟真实侧边栏占宽 */
const PREVIEW_WIDTH: Record<'default' | 'rail', { collapsed: number; expanded: number }> = {
  default: { collapsed: 72, expanded: 248 },
  rail: { collapsed: 64, expanded: 88 },
};

/**
 * 侧边导航组件文档演示页。
 *
 * 上半部分 SidebarNavOld 是应用主导航：
 * - variant="default"：标准列表（移动端抽屉）
 * - variant="rail"：图标轨道（桌面端固定侧栏）
 * - collapsed：仅显示图标、隐藏文字
 * 菜单集合随运行模式切换（产品菜单 / 开发调试菜单），「选股」随 AlphaSift 开关显隐。
 *
 * 下半部分演示 SidebarNav：轻量自研侧栏，支持 collapse / group 两种一级菜单形态，菜单数据随运行模式切换。
 */
export const DocsSideBarPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 形态与折叠态受控
  const [variant, setVariant] = useState<'default' | 'rail'>('default');
  const [collapsed, setCollapsed] = useState(false);

  const previewWidth = PREVIEW_WIDTH[variant][collapsed ? 'collapsed' : 'expanded'];

  // ② 交互演示用：实时驱动 SidebarNav 的折叠态与主题，直观展示宽度 CSS 过渡动画的丝滑效果
  const [liveState, setLiveState] = useState<MenuCollapsedState>('offcanvas');
  const [liveTheme, setLiveTheme] = useState<SidebarTheme>('square');

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsSideBar.title')}</h1>
          <p className="text-xs text-muted">
            本页演示两块内容：① 应用自身主导航 SidebarNavOld（default/rail 形态 + collapsed 折叠态，菜单随运行模式切换）；
            ② SidebarNav：轻量自研侧栏（纯 React + Tailwind），支持 collapse / group 两种菜单形态，
            接入与 SidebarNavOld 相同的真实菜单数据。
          </p>
        </header>

        {/* 控制区：形态 / 折叠态切换 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">① SidebarNavOld 控制项</h2>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">形态</span>
              <HrsButton size="sm" variant={variant === 'default' ? 'primary' : 'outline'} onClick={() => setVariant('default')}>default</HrsButton>
              <HrsButton size="sm" variant={variant === 'rail' ? 'primary' : 'outline'} onClick={() => setVariant('rail')}>rail</HrsButton>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">折叠</span>
              <HrsButton size="sm" variant={collapsed ? 'primary' : 'outline'} onClick={() => setCollapsed((v) => !v)}>
                {collapsed ? '折叠（仅图标）' : '展开（含文字）'}
              </HrsButton>
            </div>
          </div>
          <p className="text-xs text-secondary-text">当前：variant={variant}，collapsed={String(collapsed)}，预览宽度 {previewWidth}px</p>
        </section>

        {/* 预览区：固定宽度容器内渲染 SidebarNavOld */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">① SidebarNavOld 预览</h2>
          <p className="text-xs text-muted">
            下方为固定宽度的侧边栏预览（高度固定以模拟真实布局）。点击菜单项会触发路由跳转（演示页内可忽略）。
          </p>
          <div
            className="h-[600px] overflow-hidden"
            style={{ width: previewWidth }}
          >
            <SidebarNavOld variant={variant} collapsed={collapsed} />
          </div>
        </section>

        {/* 轻量自研侧栏 SidebarNav 演示 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">② SidebarNav（轻量自研侧栏）</h2>
          <p className="text-xs text-muted">
            纯 React + Tailwind 自研，零第三方 UI 依赖。菜单取自 MenuStore 的 currentMenuData（随运行模式切换，「选股」随 AlphaSift 开关显隐）。支持两级菜单：routePath 有值才可跳转、无值仅作展示；
            名称取 menuName（i18n key 或直写文案）、图标取 menuIcon，缺省不显示但保留占位对齐。
            宽度由组件自身根节点驱动：按 menuCollapsedState（三态：offcanvas / collapsed / fully）做 CSS 过渡动画（transition-[width]，并提升合成层），
            不再依赖外部容器 / Shell 的 motion.div；折叠态由属性传入（Shell 取自 useLayoutStore），组件自身不订阅 store，只负责内容呈现与自有宽度动画；
            theme 控制方角（square）或大圆角（pill）视觉。下方静态对比写死 menuCollapsedState，便于稳定对照各形态。
          </p>
          <div className="flex flex-wrap gap-6">
            <div className="flex flex-col gap-2">
              <span className="text-xs text-secondary-text">offcanvas · menuMode="collapse"（默认，一级可折叠）</span>
              <div className="h-[520px] w-[160px] overflow-hidden">
                <SidebarNav menuCollapsedState="offcanvas" />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs text-secondary-text">offcanvas · menuMode="group"（一级为分区标题）</span>
              <div className="h-[520px] w-[160px] overflow-hidden">
                <SidebarNav menuCollapsedState="offcanvas" menuMode="group" />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs text-secondary-text">collapsed · 折叠/半折叠（64px 图标栏，只显示图标与 logo）</span>
              <div className="h-[520px] w-[64px] overflow-hidden">
                <SidebarNav menuCollapsedState="collapsed" />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs text-secondary-text">offcanvas · theme="pill"（大圆角主题）</span>
              <div className="h-[520px] w-[160px] overflow-hidden">
                <SidebarNav menuCollapsedState="offcanvas" theme="pill" />
              </div>
            </div>
          </div>

          {/* 交互演示：实时切换三态折叠 + 主题，直观展示 CSS 过渡宽度动画的丝滑效果 */}
          <h3 className="mt-2 text-xs font-medium text-primary-text">交互演示（实时折叠 / 主题切换）</h3>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">折叠态</span>
              {(['offcanvas', 'collapsed', 'fully'] as const).map((s) => (
                <HrsButton
                  key={s}
                  size="sm"
                  variant={liveState === s ? 'primary' : 'outline'}
                  onClick={() => setLiveState(s)}
                >
                  {s}
                </HrsButton>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">主题</span>
              {(['square', 'pill'] as const).map((th) => (
                <HrsButton
                  key={th}
                  size="sm"
                  variant={liveTheme === th ? 'primary' : 'outline'}
                  onClick={() => setLiveTheme(th)}
                >
                  {th}
                </HrsButton>
              ))}
            </div>
          </div>
          {/* 三态语义说明：offcanvas=展开抽屉 / collapsed=折叠(半折叠) / fully=完全折叠 */}
          <ul className="flex flex-col gap-1 text-xs text-secondary-text">
            <li><span className="font-medium text-foreground">offcanvas</span> — 展开抽屉：完整侧栏，图标与文字菜单均显示。</li>
            <li><span className="font-medium text-foreground">collapsed</span> — 折叠 / 半折叠：仅保留 64px 图标栏，隐藏文字。</li>
            <li><span className="font-medium text-foreground">fully</span> — 完全折叠：侧栏收起至宽度 0，不可见（由折叠按钮重新唤出）。</li>
          </ul>
          <div className="h-[520px] w-full max-w-[600px] overflow-hidden rounded-md border border-border/70">
            <SidebarNav menuCollapsedState={liveState} theme={liveTheme} />
          </div>
          <p className="text-xs text-secondary-text">
            点击左侧菜单会触发真实路由跳转（组件内部走 react-router 的 useNavigate），演示页内可忽略；
            上方「折叠态 / 主题」按钮实时驱动 menuCollapsedState 与 theme，可观察宽度 CSS 过渡动画与图标栏切换。
          </p>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsSideBarPage;
