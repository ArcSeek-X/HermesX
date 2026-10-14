/**
 * @fileoverview 组件文档页：EmptyState（空状态）
 * 路由地址 /docs/component/empty-state，菜单名「空状态」。
 * 用于演示 EmptyState 的两种外层形态（card / text）与强调色变体（primary / muted / danger / success），
 * 以及图标、说明文案、操作区等插槽用法。
 * @module pages
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-14
 */

import React from 'react';
import { Inbox } from 'lucide-react';
import { EmptyState } from '@components/basic/EmptyState';
import { AppPage } from '@components/layout/AppPage';
import { HrsButton } from '@components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';

/** 强调色变体清单（与 EmptyStateVariant 一一对应） */
const VARIANTS = [
  { key: 'primary', label: 'primary（默认主色）' },
  { key: 'muted', label: 'muted（中性）' },
  { key: 'danger', label: 'danger（错误 / 警告）' },
  { key: 'success', label: 'success（成功）' },
] as const;

/**
 * 空状态组件文档演示页。
 *
 * EmptyState 用于在页面 / 列表无数据、无结果或初始占位时友好提示用户。
 * - type：'card' 为带虚线边框 + 柔和阴影的卡片；'text' 为纯文字（默认）。
 * - variant：控制图标与主标题的强调色，支持 primary / muted / danger / success。
 * 两种形态均复用同一套 motion.div 入场动画。
 */
export const DocsEmptyStatePage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">
            {t('layout.nav.development.docsEmptyState.title')}
          </h1>
          <p className="text-xs text-muted">
            用于页面 / 列表在无数据、无结果或初始占位时友好提示用户的空状态组件（EmptyState）。
            支持 card / text 两种外层形态，以及 primary / muted / danger / success 四种强调色变体；
            图标、说明文案、操作区均为可选插槽。
          </p>
        </header>

        {/* 1. 默认 text 形态 */}
        <DocsSection
          title="示例一：默认 text 形态（type='text'）"
          description="不传 type 时的默认表现：仅居中布局 + 内边距，无边框 / 阴影 / 背景，适合内嵌在卡片或列表内部。"
        >
          <EmptyState
            title="暂无数据"
            description="当前没有可展示的内容，试着调整筛选条件或稍后再来。"
            icon={<Inbox className="h-10 w-10" />}
            action={
              <HrsButton variant="primary" size="sm" onClick={() => {}}>
                添加自选股
              </HrsButton>
            }
          />
        </DocsSection>

        {/* 2. card 形态：图标 + 说明 + 操作区 */}
        <DocsSection
          title="示例二：card 形态（type='card'）"
          description="带虚线边框 + 柔和阴影的卡片，常用于整页占位；icon / description / action 均为可选插槽。"
        >
          <EmptyState
            type="card"
            title="暂无自选股"
            description="你还没有添加任何自选股，点击下方按钮开始关注。"
            icon={<Inbox className="h-10 w-10" />}
            action={
              <HrsButton variant="primary" size="sm" onClick={() => {}}>
                添加自选股
              </HrsButton>
            }
          />
        </DocsSection>

        {/* 3. 强调色变体 */}
        <DocsSection
          title="示例三：强调色变体（variant）"
          description="variant 控制图标与主标题的强调色；默认 primary，另支持 muted / danger / success。"
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {VARIANTS.map(({ key, label }) => (
              <EmptyState
                key={key}
                type="card"
                variant={key}
                icon={<Inbox className="h-8 w-8" />}
                title={label}
                description="标题与图标跟随 variant 强调色变化。"
              />
            ))}
          </div>
        </DocsSection>

        {/* 4. 形态对比 */}
        <DocsSection
          title="示例四：card 与 text 形态对比"
          description="左为 text（纯文字，无边框）；右为 card（虚线边框 + 阴影）。内部内容结构完全一致，仅外层容器样式不同。"
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <EmptyState title="text 形态" description="无边框、无阴影、无背景，仅居中内容。" />
            <EmptyState
              type="card"
              icon={<Inbox className="h-8 w-8" />}
              title="card 形态"
              description="带虚线边框 + 柔和阴影的卡片。"
            />
          </div>
        </DocsSection>
      </div>
    </AppPage>
  );
};

export default DocsEmptyStatePage;
