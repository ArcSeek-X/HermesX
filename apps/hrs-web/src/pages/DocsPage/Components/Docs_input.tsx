/**
 * @fileoverview 组件文档页：Input（通用表单输入框）
 * 路由地址 /docs/component/input，菜单名「输入框」。
 * 用于演示 Input 的尺寸档位、受控用法、type 变体、只读展示与禁用、placeholder/maxLength 及搜索表单组合。
 * @module pages
 */

import React, { useState } from 'react';
import { AppPage, HrsButton, Input, showToast } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 尺寸档位数据（示例一） */
const SIZE_ITEMS = [
  { size: 'xs', label: 'xs（超紧凑）' },
  { size: 'sm', label: 'sm（默认）' },
  { size: 'md', label: 'md' },
  { size: 'lg', label: 'lg' },
] as const;

/**
 * 通用表单输入组件文档演示页。
 *
 * Input 基于 HeroUI Input 封装：继承原生 input 属性全透传（含受控 value / type / onChange）；
 * size 四档控制高度 / 字号 / 圆角；组件不渲染 label / hint 包裹层，提示文案由调用方在外层渲染；
 * 传 value 但未传 onChange 时自动补 readOnly，语义为「只读展示」。
 */
export const DocsInputPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例二：受控输入
  const [controlled, setControlled] = useState('初始内容');
  // 示例三：type 变体（各自受控）
  const [email, setEmail] = useState('');
  const [num, setNum] = useState('');
  const [searchText, setSearchText] = useState('');
  // 示例五：placeholder + maxLength
  const [limited, setLimited] = useState('');
  // 示例六：搜索表单
  const [keyword, setKeyword] = useState('');

  /** 示例六：触发搜索（按钮或 Enter 键），Toast 回显关键词 */
  const handleSearch = () => {
    showToast.info({ title: '搜索', description: `触发搜索，关键词：${keyword || '（空）'}` });
  };

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsInput.title')}</h1>
          <p className="text-xs text-muted">
            通用表单输入组件（Input），基于 HeroUI Input 封装。继承原生 input 属性全透传（含受控 value / type / onChange）；
            size 四档控制高度 / 字号 / 圆角；组件不渲染 label / hint 包裹层，提示文案由调用方在外层渲染。
          </p>
        </header>

        {/* 1. 尺寸对比 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：尺寸对比</h2>
          <p className="text-xs text-muted">
            size 四档控制高度 / 字号 / 圆角：xs（h-7）、sm（h-8，默认）、md（h-9）、lg（h-10）。
          </p>
          <div className="flex flex-wrap items-end gap-4">
            {SIZE_ITEMS.map((item) => (
              <div key={item.size} className="flex flex-col gap-1">
                <span className="text-xs text-secondary-text">{item.label}</span>
                <Input size={item.size} placeholder="请输入内容" />
              </div>
            ))}
          </div>
        </section>

        {/* 2. 受控输入 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：受控输入（value / onChange）</h2>
          <p className="text-xs text-muted">
            原生受控写法：value + onChange，值变化实时回显；点击「清空」重置状态。
          </p>
          <div className="flex items-center gap-3">
            <Input value={controlled} onChange={(e) => setControlled(e.target.value)} placeholder="输入任意内容" />
            <HrsButton size="sm" variant="ghost" onClick={() => setControlled('')}>清空</HrsButton>
          </div>
          <p className="text-xs text-secondary-text">当前值：{controlled || '（空）'}</p>
        </section>

        {/* 3. type 变体 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：type 变体（email / number / search）</h2>
          <p className="text-xs text-muted">
            type 为原生属性透传，浏览器行为（如 number 步进、search 清除按钮）与原生一致。
          </p>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">type=email（受控）</span>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">type=number（受控）</span>
              <Input type="number" value={num} onChange={(e) => setNum(e.target.value)} placeholder="输入数字" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">type=search（受控）</span>
              <Input type="search" value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="搜索框" />
            </div>
          </div>
        </section>

        {/* 4. 只读展示与禁用 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：只读展示与禁用</h2>
          <p className="text-xs text-muted">
            传 value 但未传 onChange 时组件自动补 readOnly（只读展示语义，消除受控告警）；
            disabled 为显式禁用态（半透明 + 禁光标）。
          </p>
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">只读展示（value 无 onChange）</span>
              <Input value="不可编辑的展示值" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">禁用态（disabled）</span>
              <Input value="禁用输入框" disabled />
            </div>
          </div>
        </section>

        {/* 5. placeholder + maxLength */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：placeholder + maxLength</h2>
          <p className="text-xs text-muted">
            placeholder 颜色经组件内联 CSS 变量调淡；maxLength 为原生限制，配合实时字数回显。
          </p>
          <Input
            value={limited}
            onChange={(e) => setLimited(e.target.value)}
            placeholder="最多输入 20 个字符"
            maxLength={20}
          />
          <p className="text-xs text-secondary-text">已输入 {limited.length} / 20 字</p>
        </section>

        {/* 6. 表单组合 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例六：搜索表单组合（Input + HrsButton）</h2>
          <p className="text-xs text-muted">
            Input 与 HrsButton 组合模拟搜索场景；输入框内按 Enter 或点击「搜索」按钮均触发，结果经 Toast 回显。
          </p>
          <div className="flex items-center gap-3">
            <Input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearch();
              }}
              placeholder="输入搜索关键词，回车或点按钮触发"
            />
            <HrsButton variant="primary" size="sm" onClick={handleSearch}>搜索</HrsButton>
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsInputPage;
