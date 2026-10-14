/**
 * @fileoverview 组件文档页：NumberField（数字输入框）
 * 路由地址 /docs/component/numberField，菜单名「数字输入框」。
 * 用于演示 HrsNumberField 的尺寸档位、默认值、格式化、受控用法、范围限制、描述文本、禁用态及隐藏步进按钮。
 * @module pages
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-14
 */

import React, { useState } from 'react';
import { HrsButton, HrsNumberField, showToast } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';

/** 尺寸档位数据（示例一） */
const SIZE_ITEMS = [
  { size: 'xs', label: 'xs（超紧凑）' },
  { size: 'sm', label: 'sm（默认）' },
  { size: 'md', label: 'md' },
  { size: 'lg', label: 'lg' },
  { size: 'xl', label: 'xl' },
] as const;

/**
 * 数字输入组件文档演示页。
 *
 * HrsNumberField 基于 HeroUI NumberField 封装：默认呈现左右水平 +/- 步进按钮；
 * vertical 为 true 时切换为右侧上下 chevron 排列；hideControls 可完全隐藏步进按钮。
 * 继承 HeroUI 原生属性（minValue / maxValue / step / formatOptions / value / onChange 等）全透传；
 * size 五档控制整体高度 / 字号 / 圆角；label / description 可选。
 */
export const DocsNumberFieldPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例三：受控数字
  const [amount, setAmount] = useState<number | undefined>(99);
  // 示例六：数量
  const [quantity, setQuantity] = useState<number | undefined>(1);

  /** 示例三：提交当前金额 */
  const handleConfirm = () => {
    showToast.info({ title: '当前金额', description: `amount = ${amount ?? '（空）'}` });
  };

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsNumberField.title')}</h1>
          <p className="text-xs text-muted">
            通用数字输入组件（NumberField），基于 HeroUI NumberField 封装。默认呈现左右水平 +/- 步进按钮；
            vertical 为 true 时切换为右侧上下 chevron 排列，hideControls 可完全隐藏按钮；
            继承原生属性（minValue / maxValue / step / formatOptions / value / onChange）全透传；
            size 控制整体高度 / 字号 / 圆角，description 传入时在输入框下方渲染辅助说明。
          </p>
        </header>

        {/* 1. 尺寸对比 */}
        <DocsSection title="示例一：尺寸对比" description="size 五档控制整体高度 / 字号 / 圆角：xs（h-7）、sm（h-8，默认）、md（h-9）、lg（h-10）、xl（h-12）。">
          <div className="flex flex-wrap items-end gap-4">
            {SIZE_ITEMS.map((item) => (
              <div key={item.size} className="flex flex-col gap-1">
                <span className="text-xs text-secondary-text">{item.label}</span>
                <HrsNumberField size={item.size} defaultValue={99} minValue={0} label="数量" />
              </div>
            ))}
          </div>
        </DocsSection>

        {/* 2. 按钮布局 */}
        <DocsSection
          title="示例二：按钮布局（vertical / hideControls）"
          description={
            <>
              默认 <code>vertical=false</code> 为左右水平 +/- 按钮；<code>vertical=true</code>
              切换为右侧上下 chevron 按钮； <code>hideControls</code> 可完全隐藏步进按钮，适合不需要快速步进的场景。
            </>
          }
        >
          <div className="flex flex-wrap items-end gap-6">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">horizontal（默认）</span>
              <HrsNumberField defaultValue={1024} minValue={0} step={1} label="Width" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">vertical</span>
              <HrsNumberField vertical defaultValue={99} minValue={0} step={1} label="Amount" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">hideControls</span>
              <HrsNumberField hideControls defaultValue={42} minValue={0} label="No controls" />
            </div>
          </div>
        </DocsSection>

        {/* 3. 默认样式（无 label） */}
        <DocsSection title="示例三：默认样式（含格式化与范围）" description="不传入 label 时仅渲染输入框；通过 formatOptions 显示货币格式，minValue / maxValue 限制范围。">
          <HrsNumberField
            defaultValue={99}
            minValue={0}
            maxValue={1000}
            step={1}
            formatOptions={{
              style: 'currency',
              currency: 'EUR',
              currencySign: 'accounting',
            }}
          />
        </DocsSection>

        {/* 4. 受控用法 */}
        <DocsSection title="示例四：受控用法（value / onChange）" description="使用 value + onChange 实现受控；点击「确认」通过 Toast 回显当前值，「重置」恢复默认值。">
          <div className="flex flex-col gap-3">
            <HrsNumberField
              value={amount}
              onChange={setAmount}
              minValue={0}
              maxValue={10000}
              step={10}
              label="金额（CNY）"
              description="支持 minValue=0 / maxValue=10000 / step=10 的范围与步进限制"
              formatOptions={{
                style: 'currency',
                currency: 'CNY',
                currencyDisplay: 'symbol',
              }}
            />
            <div className="flex items-center gap-3 text-xs text-secondary-text">
              <span>当前值：{amount ?? '（空）'}</span>
              <HrsButton variant="primary" size="sm" onClick={handleConfirm}>确认</HrsButton>
              <HrsButton size="sm" variant="ghost" onClick={() => setAmount(99)}>重置</HrsButton>
            </div>
          </div>
        </DocsSection>

        {/* 5. 范围与步进（minValue / maxValue / step）+ 描述文本 */}
        <DocsSection
          title="示例五：范围与步进（minValue / maxValue / step）+ description"
          description={
            <>
              通过 minValue / maxValue 限制可输入区间，step 设定每次点击步进按钮或方向键增减的步长； description
              传入时在输入框下方渲染辅助说明（Enter the width in pixels）。
            </>
          }
        >
          <HrsNumberField
            defaultValue={1024}
            minValue={0}
            maxValue={1920}
            step={64}
            label="宽度（像素）"
            description="请输入宽度，范围 0 ~ 1920，每次步进 64 像素"
          />
        </DocsSection>

        {/* 6. 禁用与只读 */}
        <DocsSection title="示例六：禁用与只读" description="isDisabled 禁用输入与步进按钮；isReadOnly 仅展示不可编辑。">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">禁用态（isDisabled）</span>
              <HrsNumberField defaultValue={50} isDisabled label="禁用" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">只读态（isReadOnly）</span>
              <HrsNumberField defaultValue={50} isReadOnly label="只读" />
            </div>
          </div>
        </DocsSection>

        {/* 7. 表单组合 */}
        <DocsSection title="示例七：表单组合（HrsNumberField + HrsButton）" description="模拟数量选择场景：限制最小 1、最大 10，点击「加入购物车」回显当前数量。">
          <div className="flex items-center gap-3">
            <HrsNumberField
              value={quantity}
              onChange={setQuantity}
              minValue={1}
              maxValue={10}
              step={1}
              label="数量"
            />
            <HrsButton
              variant="primary"
              size="sm"
              onClick={() => showToast.success({ title: '已加入', description: `数量：${quantity ?? 0}` })}
            >
              加入购物车
            </HrsButton>
          </div>
        </DocsSection>
      </div>
    </AppPage>
  );
};

export default DocsNumberFieldPage;
