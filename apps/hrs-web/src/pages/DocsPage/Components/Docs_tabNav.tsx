/**
 * @fileoverview 组件文档页：TabNav（标签页导航）
 * 路由地址 /docs/component/tabNav，菜单名「标签页」。
 * 用于演示 TabNav 的受控切换、primary/secondary 变体、图标与禁用项、rightSlot 插槽、size 尺寸档位，以及 size × variant 交叉组合。
 * @module pages
 */

import React, { useState } from 'react';
import { LayoutDashboard, Cloud, Wallet } from 'lucide-react';
import { HrsButton, TabNav } from '@components';
import { AppPage } from '@components/layout/AppPage';
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
 * Tab 图标与禁用项、rightSlot 右侧插槽、size 尺寸档位（xs/sm/md/lg/xl，对齐 HrsButton）；
 * 文案不换行，选中指示条跟随项目主题色。
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
  // 示例五：size 尺寸档位
  const [sizeTab, setSizeTab] = useState('overview');
  const [navSize, setNavSize] = useState<'xs' | 'sm' | 'md' | 'lg' | 'xl'>('md');
  // 示例六：size × variant 交叉组合受控值（key 为 `${variant}-${size}`）
  const [crossTab, setCrossTab] = useState<Record<string, string>>({});

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsTabNav.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Tabs 封装的标签页导航（TabNav）。受控组件（value / onChange），支持 primary / secondary 两种视觉变体、
            Tab 图标与禁用项、rightSlot 右侧插槽、size 尺寸档位（xs/sm/md/lg/xl，对齐 HrsButton，默认 sm）。
            size 同步控制 Tab 项高度 / 内边距 / 字号 / 字重，以及 Tab 项、指示条与 primary 容器的圆角；
            文案不换行，secondary 选中指示条跟随项目主题色（--primary）。
          </p>
        </header>

        {/* 1. primary 变体基础用法 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：primary 变体基础用法</h2>
          <p className="text-xs text-muted">
            primary 变体容器圆角随 size 变化（默认 sm 为 !rounded-sm）；受控 value / onChange，下方内容区随选中 Tab 切换。
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

        {/* 5. size 尺寸档位 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：size 尺寸档位</h2>
          <p className="text-xs text-muted">
            size 控制 Tab 项高度 / 内边距 / 字号 / 字重，并同步控制 Tab 项、指示条与 primary 容器的圆角；档位 xs / sm / md / lg / xl 与 HrsButton 对齐，默认 sm。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {(['xs', 'sm', 'md', 'lg', 'xl'] as const).map((size) => (
              <HrsButton
                key={size}
                size="xs"
                variant={navSize === size ? 'primary' : 'secondary'}
                onClick={() => setNavSize(size)}
              >
                {size}
              </HrsButton>
            ))}
          </div>
          <TabNav
            items={TABS}
            value={sizeTab}
            onChange={setSizeTab}
            variant="primary"
            size={navSize}
            ariaLabel="size 尺寸档位示例"
          />
          <p className="text-xs text-secondary-text">当前尺寸：{navSize}（上方按钮可切换档位）</p>
        </section>

        {/* 6. size × variant 交叉组合 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例六：size × variant 交叉组合</h2>
          <p className="text-xs text-muted">
            同一组标签在 size（xs / sm / md / lg / xl）与 variant（primary / secondary）两个维度下的外观对比。
            primary 容器圆角随 size 变化，secondary 容器保持直角；Tab 项与指示条圆角均随 size 同步。
          </p>
          <div className="flex flex-col gap-5">
            {(['primary', 'secondary'] as const).map((variant) => (
              <div key={variant} className="flex flex-col gap-2">
                <span className="text-xs font-medium text-secondary-text">variant = "{variant}"</span>
                <div className="flex flex-wrap items-end gap-4">
                  {(['xs', 'sm', 'md', 'lg', 'xl'] as const).map((size) => {
                    const key = `${variant}-${size}`;
                    return (
                      <div key={key} className="flex flex-col gap-1">
                        <span className="text-[10px] text-muted">size = {size}</span>
                        <TabNav
                          items={TABS}
                          value={crossTab[key] ?? 'overview'}
                          onChange={(v) => setCrossTab((prev) => ({ ...prev, [key]: v }))}
                          variant={variant}
                          size={size}
                          ariaLabel={`${variant} ${size} 组合`}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsTabNavPage;
