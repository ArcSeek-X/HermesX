/**
 * CountryMarketSelect 组件文档演示页：单选、多选、受控用法与尺寸。
 */

import React, { useState } from 'react';
import { CountryMarketSelect, HrsButton, showToast } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';
import { useLiveCalendarCountries } from '../../../hooks/useLiveCalendar';

/**
 * 国家 / 市场下拉组件文档演示页。
 *
 * CountryMarketSelect 基于 HrsSelect 封装：按国名拼音 A~Z 分组、选项渲染「国旗 + 国名」，
 * 通过 `multiple` 切换单选 / 多选（默认单选），对外 `value` / `onChange` 统一为 `string[]`
 * （单选时为 0 或 1 个元素），降低调用方心智负担。
 *
 * 演示数据直接复用 `useLiveCalendarCountries()`——与线上消息日历（LiveCalendarFilter）同一数据源，
 * 保证示例所见即生产所用，国旗亦来自后端下发的真实 `flagUri`。
 */
export const DocsCountryMarketSelectPage: React.FC = () => {
  const { t } = useUiLanguage();
  // 与线上消息日历同一份国家字典（含后端下发的真实 flagUri）
  const { items: countryMarketOption, loading } = useLiveCalendarCountries();

  // 示例一：单选（默认 multiple=false）
  const [single, setSingle] = useState<string[]>([]);
  // 示例二：多选
  const [multi, setMulti] = useState<string[]>(['cn', 'us']);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsCountryMarketSelect.title')}</h1>
          <p className="text-xs text-muted">
            通用国家 / 市场下拉组件（CountryMarketSelect），基于 HrsSelect 封装。选项按国名拼音 A~Z 分组、
            渲染「国旗 + 国名」；通过 <code>multiple</code> 切换单选 / 多选（默认单选）；
            对外 <code>value</code> / <code>onChange</code> 统一为 <code>string[]</code>（单选时长度 0 或 1）。
            下方演示数据来自 <code>useLiveCalendarCountries()</code>，与线上消息日历完全一致。
          </p>
        </header>

        {loading ? (
          <span className="text-xs text-muted">国家字典加载中…</span>
        ) : null}

        {/* 1. 单选（默认） */}
        <DocsSection
          title="示例一：单选（multiple 默认 false）"
          description={
            <>
              默认单选模式：触发器展示单一选中项，再次点击可取消；<code>value</code> 长度为 0 或 1。
              下方实时回显当前选中 ID。
            </>
          }
        >
          <div className="flex flex-col gap-3">
            <CountryMarketSelect
              options={countryMarketOption}
              value={single}
              onChange={setSingle}
              placeholder="请选择国家 / 市场"
              className="w-64"
            />
            <span className="text-xs text-secondary-text">
              当前选中：{single.length ? single[0] : '（未选择）'}
            </span>
          </div>
        </DocsSection>

        {/* 2. 多选 */}
        <DocsSection
          title="示例二：多选（multiple=true）"
          description={
            <>
              多选模式：触发器以「首个 + N」折叠标签展示；空选即代表「全部 / 不筛选」，
              对外回传 <code>string[]</code>（清空时 <code>[]</code>）。下方实时回显选中 ID 列表。
            </>
          }
        >
          <div className="flex flex-col gap-3">
            <CountryMarketSelect
              options={countryMarketOption}
              multiple
              value={multi}
              onChange={setMulti}
              placeholder="全部国家 / 地区"
              className="w-64"
            />
            <span className="text-xs text-secondary-text">
              当前选中：{multi.length ? multi.join('、') : '（全部 / 未选）'}
            </span>
          </div>
        </DocsSection>

        {/* 3. 尺寸对比 */}
        <DocsSection title="示例三：尺寸对比" description="size 四档控制整体高度 / 字号 / 圆角：xs / sm（默认）/ md / lg。">
          <div className="flex flex-wrap items-end gap-4">
            {(['xs', 'sm', 'md', 'lg'] as const).map((size) => (
              <div key={size} className="flex flex-col gap-1">
                <span className="text-xs text-secondary-text">{size}</span>
                <CountryMarketSelect
                  options={countryMarketOption}
                  size={size}
                  value={[]}
                  onChange={() => {}}
                  placeholder={size}
                  className="w-56"
                />
              </div>
            ))}
          </div>
        </DocsSection>

        {/* 4. 受控 + 回显 */}
        <DocsSection
          title="示例四：受控用法（点击回显选中值）"
          description="使用 value + onChange 受控；点击「确认」通过 Toast 回显当前选中的国家 ID 列表，便于对接筛选条件。"
        >
          <div className="flex items-center gap-3">
            <CountryMarketSelect
              options={countryMarketOption}
              multiple
              value={multi}
              onChange={setMulti}
              placeholder="全部国家 / 地区"
              className="w-64"
            />
            <HrsButton
              variant="primary"
              size="sm"
              onClick={() =>
                showToast.info({
                  title: '选中国家',
                  description: multi.length ? multi.join('、') : '（全部）',
                })
              }
            >
              确认
            </HrsButton>
          </div>
        </DocsSection>

        {/* 5. 分组 vs 平铺 */}
        <DocsSection
          title="示例五：分组（A-Z）与平铺（flattening）"
          description={
            <>
              通过 <code>groupBy</code> 控制展示形态：默认 <code>'A-Z'</code> 按拼音首字母分组；
              传入 <code>'flattening'</code> 则完全平铺、不渲染组标题。下方两个均为多选。
            </>
          }
        >
          <div className="flex flex-wrap items-start gap-6">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">groupBy='A-Z'（默认·分组）</span>
              <CountryMarketSelect
                options={countryMarketOption}
                multiple
                groupBy="A-Z"
                value={multi}
                onChange={setMulti}
                placeholder="全部国家 / 地区"
                className="w-64"
              />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">groupBy='flattening'（平铺）</span>
              <CountryMarketSelect
                options={countryMarketOption}
                multiple
                groupBy="flattening"
                value={multi}
                onChange={setMulti}
                placeholder="全部国家 / 地区"
                className="w-64"
              />
            </div>
          </div>
        </DocsSection>
      </div>
    </AppPage>
  );
};

export default DocsCountryMarketSelectPage;
