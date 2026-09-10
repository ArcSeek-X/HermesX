/**
 * @fileoverview 组件文档页：TabNav（标签页导航）
 * 路由地址 /docs/component/tabNav，菜单名「标签页」。
 * 用于演示 TabNav 的受控切换、primary/secondary 变体、图标与禁用项、rightSlot 插槽。
 * @module pages
 */

import React, { useState } from 'react';
import { LayoutDashboard, Cloud, Wallet } from 'lucide-react';
import { AppPage, HrsButton, TabNav } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 标签数据（示例一 / 二 / 四共用） */
const TABS = [
  { value: 'overview', label: '概览' },
  { value: 'etf', label: 'ETF 云图' },
  { value: 'flow', label: '资金流向' },
];

/** 标签数据（示例三：图标 + 禁用项） */
const ICON_TABS = [
  { value: 'dashboard', label: '总览', icon: <LayoutDashboard className="h-3.5 w-3.5" aria-hidden="true" /> },
  { value: 'cloud', label: '云图', icon: <Cloud className="h-3.5 w-3.5" aria-hidden="true" /> },
  { value: 'wallet', label: '资金', icon: <Wallet className="h-3.5 w-3.5" aria-hidden="true" />, disabled: true },
];

/** 各 Tab 对应的内容文案（示例一 / 二演示切换效果） */
const TAB_CONTENT: Record<string, string> = {
  overview: '概览：市场行情与核心指标总览。',
  etf: 'ETF 云图：板块资金分布与热度可视化。',
  flow: '资金流向：主力资金净流入 / 流出排行。',
};

/**
 * 标签页导航组件文档演示页。
 *
 * TabNav 基于 HeroUI Tabs 封装：受控组件（value / onChange），支持 primary 与 secondary 两种视觉变体、
 * Tab 图标与禁用项、rightSlot 右侧插槽；文案不换行，选中指示条跟随项目主题色。
 */
export const DocsTabNavPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例一：primary 变体受控值
  const [primaryTab, setPrimaryTab] = useState('overview');
  // 示例二：secondary 变体受控值
  const [secondaryTab, setSecondaryTab] = useState('overview');
  // 示例三：图标 + 禁用项
  const [iconTab, setIconTab] = useState('dashboard');
  // 示例四：rightSlot 插槽
  const [slotTab, setSlotTab] = useState('overview');

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsTabNav.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Tabs 封装的标签页导航（TabNav）。受控组件（value / onChange），支持 primary / secondary 两种视觉变体、
            Tab 图标与禁用项、rightSlot 右侧插槽；文案不换行，选中指示条跟随项目主题色。
          </p>
        </header>

        {/* 1. primary 变体基础用法 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：primary 变体基础用法</h2>
          <p className="text-xs text-muted">
            primary 变体保留 rounded-md 容器圆角；受控 value / onChange，下方内容区随选中 Tab 切换。
          </p>
          <TabNav
            items={TABS}
            value={primaryTab}
            onChange={setPrimaryTab}
            variant="primary"
            ariaLabel="primary 变体示例"
          />
          <p className="text-xs text-secondary-text">当前选中：{primaryTab} —— {TAB_CONTENT[primaryTab]}</p>
        </section>

        {/* 2. secondary 变体 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：secondary 变体</h2>
          <p className="text-xs text-muted">
            secondary 变体容器无圆角（直角），选中指示条跟随项目主题色（--primary）而非 HeroUI 默认蓝色。
          </p>
          <TabNav
            items={TABS}
            value={secondaryTab}
            onChange={setSecondaryTab}
            variant="secondary"
            ariaLabel="secondary 变体示例"
          />
          <p className="text-xs text-secondary-text">当前选中：{secondaryTab} —— {TAB_CONTENT[secondaryTab]}</p>
        </section>

        {/* 3. 图标与禁用项 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：图标与禁用项</h2>
          <p className="text-xs text-muted">
            Tab 支持前置图标（icon）；disabled 为 true 的 Tab 自动收集为 disabledKeys，无法选中。
          </p>
          <TabNav
            items={ICON_TABS}
            value={iconTab}
            onChange={setIconTab}
            variant="primary"
            ariaLabel="图标与禁用示例"
          />
          <p className="text-xs text-secondary-text">当前选中：{iconTab}（「资金」为禁用项）</p>
        </section>

        {/* 4. rightSlot 插槽 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：rightSlot 右侧插槽</h2>
          <p className="text-xs text-muted">
            rightSlot 在标签栏右侧放置自定义内容（如操作按钮），标签与插槽左右两端对齐。
          </p>
          <TabNav
            items={TABS}
            value={slotTab}
            onChange={setSlotTab}
            variant="primary"
            ariaLabel="rightSlot 示例"
            rightSlot={<HrsButton size="xs" variant="ghost" onClick={() => setSlotTab('overview')}>重置</HrsButton>}
          />
          <p className="text-xs text-secondary-text">当前选中：{slotTab}（点击右侧「重置」回到概览）</p>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsTabNavPage;
