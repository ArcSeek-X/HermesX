/**
 * @fileoverview 组件文档页：ListCard（通用列表卡片）
 * 路由地址 /docs/component/listCard，菜单名「列表卡片」。
 * 用于演示 ListCard 的图标/标题/描述/计数徽标、选中态与 hover 编辑删除操作。
 * @module pages
 */

import React, { useState } from 'react';
import { Star, Folder, Bell } from 'lucide-react';
import { AppPage, HrsButton, showToast } from '../../../components';
import { ListCard } from '../../../components/common/Card';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 组合列表演示数据（示例四）：分类列表 */
const CATEGORY_ITEMS = [
  { id: 'watch', icon: Star, title: '自选股', description: '重点关注的自选股列表', count: 12 },
  { id: 'sector', icon: Folder, title: '板块分组', description: '按行业板块组织的分组', count: 8 },
  { id: 'alert', icon: Bell, title: '告警规则', description: '价格预警与通知规则', count: 3 },
];

/**
 * 列表卡片组件文档演示页。
 *
 * ListCard 为可点击的列表项卡片：左侧图标 + 主标题（可选描述）+ 右侧计数徽标；
 * 传入 onEdit / onDelete 后，hover 时计数徽标切换为编辑 / 删除按钮；
 * isActive 控制选中态（左侧主题色边框 + 高亮），ordinal 控制错位入场动画。
 */
export const DocsListCardPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例二：选中态（单选切换）
  const [activeId, setActiveId] = useState<string | null>(null);
  // 示例四：组合列表的选中项
  const [categoryActive, setCategoryActive] = useState<string>('watch');

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsListCard.title')}</h1>
          <p className="text-xs text-muted">
            通用列表卡片（ListCard）：左图标 + 主标题（可选描述）+ 右侧计数徽标；isActive 控制选中态（左侧主题色边框 + 高亮），
            传入 onEdit / onDelete 后 hover 时切换为操作按钮，ordinal 控制错位入场动画。
          </p>
        </header>

        {/* 1. 基础用法 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：基础用法</h2>
          <p className="text-xs text-muted">
            icon（缺省用 Layers3）/ title 必填 / description 可选（渲染在标题下方并与标题左对齐）/ count 计数徽标（默认 0）。
          </p>
          <div className="flex max-w-xs flex-col gap-2">
            <ListCard icon={Star} title="自选股" description="重点关注的自选股列表" count={12} ordinal={0} />
            <ListCard icon={Folder} title="板块分组" count={8} ordinal={1} />
          </div>
        </section>

        {/* 2. 选中态 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：选中态（isActive）</h2>
          <p className="text-xs text-muted">
            isActive 为 true 时展示左侧主题色内阴影边框 + 图标/标题高亮 + 计数徽标切换主题色；onClick 实现单选切换。
          </p>
          <span className="text-xs text-secondary-text">当前选中：{activeId ?? '无'}</span>
          <div className="flex max-w-xs flex-col gap-2">
            {CATEGORY_ITEMS.map((item, i) => (
              <ListCard
                key={item.id}
                icon={item.icon}
                title={item.title}
                description={item.description}
                count={item.count}
                ordinal={i}
                isActive={activeId === item.id}
                onClick={() => setActiveId(item.id)}
              />
            ))}
          </div>
        </section>

        {/* 3. hover 编辑/删除操作 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：hover 编辑 / 删除操作</h2>
          <p className="text-xs text-muted">
            传入 onEdit / onDelete 后，鼠标移入卡片时计数徽标切换为编辑 / 删除按钮（与计数互斥）；点击操作会触发 Toast 回显。
          </p>
          <div className="flex max-w-xs flex-col gap-2">
            <ListCard
              icon={Star}
              title="自选股"
              description="鼠标移入查看操作按钮"
              count={12}
              onEdit={() => showToast.info({ title: '编辑', description: '已触发 onEdit 回调' })}
              onDelete={() => showToast.warning({ title: '删除', description: '已触发 onDelete 回调' })}
            />
          </div>
        </section>

        {/* 4. 组合列表 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：组合列表（选中态 + 操作按钮）</h2>
          <p className="text-xs text-muted">
            结合 isActive 选中态与 onEdit / onDelete 操作，模拟「设置-分类导航」场景的完整列表。
          </p>
          <div className="flex max-w-xs flex-col gap-2">
            {CATEGORY_ITEMS.map((item, i) => (
              <ListCard
                key={item.id}
                icon={item.icon}
                title={item.title}
                description={item.description}
                count={item.count}
                ordinal={i}
                isActive={categoryActive === item.id}
                onClick={() => setCategoryActive(item.id)}
                onEdit={() => showToast.info({ title: `编辑「${item.title}」`, description: '已触发 onEdit 回调' })}
                onDelete={() => showToast.warning({ title: `删除「${item.title}」`, description: '已触发 onDelete 回调' })}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-3 border-t border-border/60 pt-3">
            <HrsButton variant="primary" size="sm" onClick={() => showToast.success({ title: '保存成功', description: `当前选中的分类：${categoryActive}` })}>
              保存当前选中
            </HrsButton>
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsListCardPage;
