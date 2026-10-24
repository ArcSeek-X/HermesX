/**
 * HrsSelect 组件文档演示页：基础单选、分组选项、多选折叠、尺寸档位与校验态。
 */

import React, { useState } from 'react';
import { HrsSelect, type HrsSelectDataSourceDef, type HrsSelectSize } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';

/** 基础单选数据源（示例一 / 四 / 五 / 六共用） */
const MARKET_OPTIONS: HrsSelectDataSourceDef = [
  { key: 'a', label: 'A 股' },
  { key: 'hk', label: '港股', disabled: true },
  { key: 'us', label: '美股' },
];

/** 分组数据源（示例二）：含 options 数组的项识别为分组，分组间自动插入分隔线 */
const GROUPED_OPTIONS: HrsSelectDataSourceDef = [
  {
    key: 'asia',
    title: '亚洲',
    options: [
      { key: 'cn', label: '中国' },
      { key: 'jp', label: '日本', disabled: true },
      { key: 'kr', label: '韩国' },
    ],
  },
  {
    key: 'europe',
    title: '欧洲',
    options: [
      { key: 'uk', label: '英国' },
      { key: 'de', label: '德国' },
    ],
  },
  { key: 'global', label: '全球（扁平项）' },
];

/** 多选数据源（示例三） */
const MULTI_OPTIONS: HrsSelectDataSourceDef = [
  { key: 'watchlist', label: '自选股' },
  { key: 'sector', label: '板块' },
  { key: 'kline', label: 'K 线' },
  { key: 'news', label: '快讯' },
];

/** 尺寸档位（示例四展示） */
const SELECT_SIZES: HrsSelectSize[] = ['xs', 'sm', 'md', 'lg'];

/**
 * 下拉选择组件文档演示页。
 *
 * HrsSelect 基于 HeroUI v3 Select 声明式封装：统一通过 options 入参驱动
 * （扁平项与分组项由数据结构动态解析），value / onChange 遵循 HeroUI 规格。
 */
export const DocsSelectPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例一 / 五 / 六：单选受控值
  const [market, setMarket] = useState<string | null>(null);
  // 示例二：分组单选受控值
  const [country, setCountry] = useState<string | null>(null);
  // 示例三：多选受控值（collapseTags 开 / 关各一个）
  const [multiCollapse, setMultiCollapse] = useState<string[]>(['watchlist']);
  const [multiChips, setMultiChips] = useState<string[]>(['watchlist', 'news']);
  // 示例四：尺寸对比（共享一个受控值）
  const [sizeValue, setSizeValue] = useState<string | null>(null);
  // 示例五：必填校验（未选择时 isInvalid + errorMessage）
  const [requiredMarket, setRequiredMarket] = useState<string | null>(null);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsSelect.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI v3 Select 声明式封装的下拉选择器（HrsSelect）。统一 options 数据入口（扁平 / 分组动态解析），
            支持单选 / 多选、四档尺寸、选项禁用、label / description / errorMessage 与 renderItem 自定义渲染。
          </p>
        </header>

        {/* 1. 基础单选 */}
        <DocsSection title="示例一：基础单选（受控）" description="value / onChange 遵循 HeroUI 规格（单选回传 Key），数据字段 disabled 的选项不可被选中（降透明度 + 禁光标）。">
          <span className="text-xs text-secondary-text">当前选中：{market ?? '无'}</span>
          <div className="flex max-w-64 flex-col gap-3">
            <HrsSelect
              label="市场"
              placeholder="请选择市场"
              options={MARKET_OPTIONS}
              value={market}
              onChange={(v) => setMarket(v as string)}
            />
          </div>
        </DocsSection>

        {/* 2. 分组选项 */}
        <DocsSection title="示例二：分组选项" description="含 options 数组的项识别为分组（title 渲染分组标题），分组之间自动插入 Separator 分隔线；扁平项与分组可任意混排。">
          <span className="text-xs text-secondary-text">当前选中：{country ?? '无'}</span>
          <div className="flex max-w-64 flex-col gap-3">
            <HrsSelect
              label="国家 / 地区"
              placeholder="请选择国家或地区"
              options={GROUPED_OPTIONS}
              value={country}
              onChange={(v) => setCountry(v as string)}
            />
          </div>
        </DocsSection>

        {/* 3. 多选模式 */}
        <DocsSection title="示例三：多选模式（selectionMode）" description="selectionMode=multiple 时 value 为 Key[]；collapseTags（默认 true）以「首个 Chip（带 ×）+ 其余 + N」折叠展示， 关闭后使用 HeroUI 默认 chip 多选标签（每个自带 ×）。">
          <div className="flex flex-wrap items-start gap-6">
            <div className="flex max-w-72 flex-col gap-3">
              <span className="text-[11px] text-muted">collapseTags=true（默认）</span>
              <HrsSelect
                label="关注模块"
                placeholder="请选择模块"
                selectionMode="multiple"
                options={MULTI_OPTIONS}
                value={multiCollapse}
                onChange={(v) => setMultiCollapse(v as string[])}
              />
              <span className="text-xs text-secondary-text">当前选中：{multiCollapse.join(' / ') || '无'}</span>
            </div>
            <div className="flex max-w-72 flex-col gap-3">
              <span className="text-[11px] text-muted">collapseTags=false</span>
              <HrsSelect
                label="关注模块"
                placeholder="请选择模块"
                selectionMode="multiple"
                collapseTags={false}
                options={MULTI_OPTIONS}
                value={multiChips}
                onChange={(v) => setMultiChips(v as string[])}
              />
              <span className="text-xs text-secondary-text">当前选中：{multiChips.join(' / ') || '无'}</span>
            </div>
          </div>
        </DocsSection>

        {/* 4. 尺寸对比 */}
        <DocsSection title="示例四：尺寸对比（size）" description="size 支持 xs / sm / md / lg（默认 sm），控制触发器高度 / 内边距 / 字号与弹层圆角。">
          <div className="flex flex-wrap items-end gap-6">
            {SELECT_SIZES.map((size) => (
              // 列宽需 >= HrsSelect 根元素内置的固定宽度 w-50（200px）：
              // 容器更窄时 select 会溢出容器并压住相邻列，导致互相堆叠
              <div key={size} className="flex w-50 flex-col gap-2">
                <span className="text-[11px] text-muted">size={size}</span>
                <HrsSelect
                  size={size}
                  placeholder="请选择"
                  options={MARKET_OPTIONS}
                  value={sizeValue}
                  onChange={(v) => setSizeValue(v as string)}
                />
              </div>
            ))}
          </div>
        </DocsSection>

        {/* 5. 校验态 */}
        <DocsSection title="示例五：校验态（isInvalid + errorMessage）" description="isRequired 标记必填；未选择时 isInvalid + errorMessage 联动报错，选择后恢复；description 与 errorMessage 互斥展示（有错误优先）。">
          <div className="flex max-w-64 flex-col gap-3">
            <HrsSelect
              label="市场（必填）"
              placeholder="请选择市场"
              isRequired
              isInvalid={!requiredMarket}
              errorMessage={requiredMarket ? undefined : '市场为必填项，请选择'}
              description="选择后将用于行情数据源过滤"
              options={MARKET_OPTIONS}
              value={requiredMarket}
              onChange={(v) => setRequiredMarket(v as string)}
            />
          </div>
        </DocsSection>

        {/* 6. 整组件禁用与自定义渲染 */}
        <DocsSection title="示例六：整组件禁用与 renderItem 自定义渲染" description="isDisabled 禁用整个选择器；renderItem 自定义选项主内容渲染（入参为单个选项对象）。">
          <div className="flex flex-wrap items-start gap-6">
            <div className="flex max-w-64 flex-col gap-3">
              <span className="text-[11px] text-muted">isDisabled（整组件禁用）</span>
              <HrsSelect
                label="市场"
                placeholder="请选择市场"
                isDisabled
                options={MARKET_OPTIONS}
                defaultValue="a"
              />
            </div>
            <div className="flex max-w-64 flex-col gap-3">
              <span className="text-[11px] text-muted">renderItem（自定义选项渲染）</span>
              <HrsSelect
                label="市场"
                placeholder="请选择市场"
                options={MARKET_OPTIONS}
                renderItem={(option) => (
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
                    {option.label}
                  </span>
                )}
                defaultValue="a"
              />
            </div>
          </div>
        </DocsSection>
      </div>
    </AppPage>
  );
};

export default DocsSelectPage;
