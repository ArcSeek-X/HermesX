/**
 * @fileoverview 组件文档页：Chip（通用标签芯片）
 * 路由地址 /docs/component/chip，菜单名「标签芯片」。
 * 用于演示 Chip 的 variant / color / size / radius 组合、onClose 可关闭标签与禁用态、图标文字组合场景。
 * @module pages
 */

import React, { useState } from 'react';
import { Star, TrendingUp, TrendingDown, Bell, Folder } from 'lucide-react';
import { AppPage, Chip, showToast } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 视觉风格变体（示例一） */
const VARIANT_ITEMS = [
  { variant: 'primary', label: 'primary' },
  { variant: 'secondary', label: 'secondary' },
  { variant: 'tertiary', label: 'tertiary' },
  { variant: 'soft', label: 'soft' },
] as const;

/** 语义色（示例二） */
const COLOR_ITEMS = [
  { color: 'default', label: 'default' },
  { color: 'accent', label: 'accent' },
  { color: 'success', label: 'success' },
  { color: 'warning', label: 'warning' },
  { color: 'danger', label: 'danger' },
  { color: 'blue', label: 'blue' },
  { color: 'purple', label: 'purple' },
  { color: 'indigo', label: 'indigo' },
] as const;

/** 尺寸档位（示例三） */
const SIZE_ITEMS = [
  { size: 'xs', label: 'xs' },
  { size: 'sm', label: 'sm' },
  { size: 'md', label: 'md（默认）' },
  { size: 'lg', label: 'lg' },
  { size: 'xl', label: 'xl' },
] as const;

/** 圆角档位（示例四） */
const RADIUS_ITEMS = [
  { radius: 'full', label: 'full（胶囊，默认）' },
  { radius: 'sm', label: 'sm' },
  { radius: 'md', label: 'md' },
  { radius: 'lg', label: 'lg' },
] as const;

/**
 * 标签芯片组件文档演示页。
 *
 * Chip 为圆角胶囊标签（API 对齐 HeroUI Chip，样式用项目自管 Tailwind 语义色实现）：
 * variant（primary/secondary/tertiary/soft）× color（8 色）× size（5 档）× radius（4 档）自由组合；
 * onClose 传入时渲染内置 × 按钮（已 stopPropagation，可安全嵌在按压容器内）；isDisabled 半透明禁用；
 * 内容（图标、文字）由调用方通过 children 自行组合。
 */
export const DocsChipPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例五：可关闭标签受控列表
  const [tags, setTags] = useState<string[]>(['自选股', '沪深市场', '半导体', '高股息']);
  // 示例六：筛选器已选条目
  const [filters, setFilters] = useState<string[]>(['财报', '资金流向', '涨跌幅']);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsChip.title')}</h1>
          <p className="text-xs text-muted">
            通用标签芯片（Chip）：圆角胶囊标签，API 对齐 HeroUI Chip。variant × color × size × radius 自由组合，
            onClose 传入时渲染内置 × 按钮，isDisabled 半透明禁用；内容（图标、文字）由调用方通过 children 自行组合。
          </p>
        </header>

        {/* 1. variant 变体 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：variant 变体（同用 accent 色对比）</h2>
          <p className="text-xs text-muted">
            primary 半透明主题色底 + 边框；secondary 更淡的底色；tertiary 浅灰边框 + 更浅底色；soft 无边框纯底色。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {VARIANT_ITEMS.map((item) => (
              <Chip key={item.variant} variant={item.variant} color="accent">{item.label}</Chip>
            ))}
          </div>
        </section>

        {/* 2. 语义色 color */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：语义色 color（8 色，primary 变体）</h2>
          <p className="text-xs text-muted">
            default / accent 走项目主题色，success / warning / danger 走语义色，blue / purple / indigo 为固定色。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {COLOR_ITEMS.map((item) => (
              <Chip key={item.color} variant="primary" color={item.color}>{item.label}</Chip>
            ))}
          </div>
        </section>

        {/* 3. 尺寸对比 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：尺寸对比（size 五档）</h2>
          <p className="text-xs text-muted">
            xs（h-5）→ xl（h-9）五档控制高度 / 内边距 / 字号，默认 md（h-7）。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {SIZE_ITEMS.map((item) => (
              <Chip key={item.size} size={item.size} variant="secondary" color="accent">{item.label}</Chip>
            ))}
          </div>
        </section>

        {/* 4. radius 圆角 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：radius 圆角</h2>
          <p className="text-xs text-muted">
            full 为默认胶囊；sm / md / lg 对应三档圆角矩形。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {RADIUS_ITEMS.map((item) => (
              <Chip key={item.radius} radius={item.radius} variant="primary" color="accent">{item.label}</Chip>
            ))}
          </div>
        </section>

        {/* 5. onClose 可关闭标签 + 禁用 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：onClose 可关闭标签 + isDisabled</h2>
          <p className="text-xs text-muted">
            传入 onClose 渲染内置 × 按钮（点击删除该项，不影响容器点击）；受控列表删除后实时回显；isDisabled 禁用关闭且半透明。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {tags.map((tag) => (
              <Chip
                key={tag}
                variant="secondary"
                color="accent"
                onClose={() => setTags(tags.filter((item) => item !== tag))}
              >
                {tag}
              </Chip>
            ))}
            <Chip variant="primary" color="danger" onClose={() => showToast.warning({ title: '已禁用', description: '禁用态关闭按钮不可点击' })} isDisabled>
              禁用标签
            </Chip>
          </div>
          <p className="text-xs text-secondary-text">剩余标签：{tags.length > 0 ? tags.join(' / ') : '（已全部删除）'}</p>
        </section>

        {/* 6. 组合场景 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例六：组合场景（图标 + 文字、筛选器已选条目）</h2>
          <p className="text-xs text-muted">
            children 由调用方组合：左侧为图标 + 文字标签；右侧模拟筛选器已选条目（「标签 + × 取消」）。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Chip variant="primary" color="success"><TrendingUp className="h-3.5 w-3.5" />上涨</Chip>
            <Chip variant="primary" color="danger"><TrendingDown className="h-3.5 w-3.5" />下跌</Chip>
            <Chip variant="secondary" color="accent"><Star className="h-3.5 w-3.5" />自选股</Chip>
            <Chip variant="tertiary" color="default"><Folder className="h-3.5 w-3.5" />板块</Chip>
            <Chip variant="soft" color="blue"><Bell className="h-3.5 w-3.5" />告警</Chip>
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-3">
            <span className="text-xs text-secondary-text">筛选器已选：</span>
            {filters.length > 0 ? (
              filters.map((item) => (
                <Chip
                  key={item}
                  size="sm"
                  radius="sm"
                  variant="secondary"
                  color="accent"
                  onClose={() => setFilters(filters.filter((f) => f !== item))}
                >
                  {item}
                </Chip>
              ))
            ) : (
              <span className="text-xs text-muted">（无）</span>
            )}
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsChipPage;
