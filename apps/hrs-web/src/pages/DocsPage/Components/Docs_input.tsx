/**
 * @fileoverview 组件文档页：Input（通用表单输入框）
 * 路由地址 /docs/component/input，菜单名「输入框」。
 * 用于演示 Input 的尺寸档位、受控用法、type 变体、只读展示与禁用、placeholder/maxLength、清除按钮（clearable，默认开启）及搜索表单组合。
 * @module pages
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-14
 */

import React, { useState } from 'react';
import { HrsButton, HrsInput, showToast } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';

/** 尺寸档位数据（示例一） */
const SIZE_ITEMS = [
  { size: 'xs', label: 'xs（超紧凑）' },
  { size: 'sm', label: 'sm（默认）' },
  { size: 'md', label: 'md' },
  { size: 'lg', label: 'lg' },
] as const;

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
  // 示例七：清除按钮（clearable，默认开启）
  const [clearableText, setClearableText] = useState('带清除按钮的示例文本');
  const [noClearText, setNoClearText] = useState('关闭清除按钮');

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
        <DocsSection title="示例一：尺寸对比" description="size 四档控制高度 / 字号 / 圆角：xs（h-7）、sm（h-8，默认）、md（h-9）、lg（h-10）。">
          <div className="flex flex-wrap items-end gap-4">
            {SIZE_ITEMS.map((item) => (
              <div key={item.size} className="flex flex-col gap-1">
                <span className="text-xs text-secondary-text">{item.label}</span>
                <HrsInput size={item.size} placeholder="请输入内容" />
              </div>
            ))}
          </div>
        </DocsSection>

        {/* 2. 受控输入 */}
        <DocsSection title="示例二：受控输入（value / onChange）" description="原生受控写法：value + onChange，值变化实时回显；点击「清空」重置状态。">
          <div className="flex items-center gap-3">
            <HrsInput value={controlled} onChange={(e) => setControlled(e.target.value)} placeholder="输入任意内容" />
            <HrsButton size="sm" variant="ghost" onClick={() => setControlled('')}>清空</HrsButton>
          </div>
          <p className="text-xs text-secondary-text">当前值：{controlled || '（空）'}</p>
        </DocsSection>

        {/* 3. type 变体 */}
        <DocsSection title="示例三：type 变体（email / number / search）" description="type 为原生属性透传，浏览器行为（如 number 步进、search 清除按钮）与原生一致。">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">type=email（受控）</span>
              <HrsInput type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">type=number（受控）</span>
              <HrsInput type="number" value={num} onChange={(e) => setNum(e.target.value)} placeholder="输入数字" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">type=search（受控）</span>
              <HrsInput type="search" value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="搜索框" />
            </div>
          </div>
        </DocsSection>

        {/* 4. 只读展示与禁用 */}
        <DocsSection title="示例四：只读展示与禁用" description="传 value 但未传 onChange 时组件自动补 readOnly（只读展示语义，消除受控告警）； disabled 为显式禁用态（半透明 + 禁光标）。">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">只读展示（value 无 onChange）</span>
              <HrsInput value="不可编辑的展示值" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">禁用态（disabled）</span>
              <HrsInput value="禁用输入框" disabled />
            </div>
          </div>
        </DocsSection>

        {/* 5. placeholder + maxLength */}
        <DocsSection title="示例五：placeholder + maxLength" description="placeholder 颜色经组件内联 CSS 变量调淡；maxLength 为原生限制，配合实时字数回显。">
          <HrsInput
            value={limited}
            onChange={(e) => setLimited(e.target.value)}
            placeholder="最多输入 20 个字符"
            maxLength={20}
          />
          <p className="text-xs text-secondary-text">已输入 {limited.length} / 20 字</p>
        </DocsSection>

        {/* 6. 表单组合 */}
        <DocsSection title="示例六：搜索表单组合（Input + HrsButton）" description="Input 与 HrsButton 组合模拟搜索场景；输入框内按 Enter 或点击「搜索」按钮均触发，结果经 Toast 回显。">
          <div className="flex items-center gap-3">
            <HrsInput
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearch();
              }}
              placeholder="输入搜索关键词，回车或点按钮触发"
            />
            <HrsButton variant="primary" size="sm" onClick={handleSearch}>搜索</HrsButton>
          </div>
        </DocsSection>

        {/* 7. 清除按钮 clearable（默认开启） */}
        <DocsSection
          title="示例七：清除按钮（clearable，默认开启）"
          description="clearable 默认 true：输入框有内容时，右侧出现 × 关闭按钮，点击清空（触发 onChange 上抛空串）；无内容 / 只读 / 禁用时不显示。受控与非受控用法均支持。传 clearable={false} 可显式关闭该按钮。"
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">受控（value + onChange）</span>
              <HrsInput
                value={clearableText}
                onChange={(e) => setClearableText(e.target.value)}
                placeholder="输入内容后，右侧出现清除按钮"
              />
              <p className="text-xs text-secondary-text">当前值：{clearableText || '（空）'}</p>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">非受控（仅 defaultValue，无 value / onChange）</span>
              <HrsInput defaultValue="非受控初始值" placeholder="输入内容后，右侧同样出现清除按钮" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">显式 clearable=&#123;false&#125;（始终无清除按钮）</span>
              <HrsInput
                value={noClearText}
                onChange={(e) => setNoClearText(e.target.value)}
                clearable={false}
                placeholder="该输入框不显示清除按钮"
              />
              <p className="text-xs text-secondary-text">当前值：{noClearText || '（空）'}</p>
            </div>
          </div>
        </DocsSection>
      </div>
    </AppPage>
  );
};

export default DocsInputPage;
