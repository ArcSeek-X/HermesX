/**
 * @fileoverview 组件文档页：TextArea（通用多行文本输入框）
 * 路由地址 /docs/component/textArea，菜单名「文本域」。
 * 用于演示 TextArea 的受控用法、尺寸档位、rows 行数、variant 变体、禁用与只读及提交表单组合。
 * @module pages
 */

import React, { useState } from 'react';
import { AppPage, HrsButton, TextArea, showToast } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 尺寸档位数据（示例二） */
const SIZE_ITEMS = [
  { size: 'xs', label: 'xs（超紧凑）' },
  { size: 'sm', label: 'sm（默认）' },
  { size: 'md', label: 'md' },
  { size: 'lg', label: 'lg' },
] as const;

/** rows 行数档位数据（示例三） */
const ROWS_ITEMS = [
  { rows: 3, label: 'rows=3' },
  { rows: 5, label: 'rows=5（组件默认）' },
  { rows: 8, label: 'rows=8' },
];

/**
 * 通用多行文本输入组件文档演示页。
 *
 * TextArea 基于 HeroUI TextArea 封装：继承原生 textarea 属性全透传（含受控 value / onChange）；
 * size 四档控制最小高度 / 字号 / 圆角（实际高度仍由 rows 与拖拽共同决定）；rows 默认 5；
 * variant 支持 primary（带阴影）与 secondary（无阴影，适配 Surface）。
 */
export const DocsTextAreaPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例一：基础受控
  const [text, setText] = useState('这是一段初始的多行文本内容，用于演示 TextArea 的受控用法。');
  // 示例五：maxLength
  const [limited, setLimited] = useState('');
  // 示例六：提交表单
  const [draft, setDraft] = useState('');

  /** 示例六：模拟提交，Toast 回显内容首行 */
  const handleSubmit = () => {
    const firstLine = draft.split('\n')[0] || '（空）';
    showToast.success({ title: '提交成功', description: `内容首行：${firstLine}` });
  };

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsTextArea.title')}</h1>
          <p className="text-xs text-muted">
            通用多行文本输入组件（TextArea），基于 HeroUI TextArea 封装。继承原生 textarea 属性全透传；
            size 控制最小高度 / 字号 / 圆角，rows 控制可见行数，variant 切换 primary（带阴影）与 secondary（无阴影）。
          </p>
        </header>

        {/* 1. 基础受控用法 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：基础受控用法（value / onChange）</h2>
          <p className="text-xs text-muted">
            原生受控写法与 HTML textarea 一致：value + onChange，输入时实时回显字数。
          </p>
          <TextArea value={text} onChange={(e) => setText(e.target.value)} placeholder="输入多行内容" />
          <p className="text-xs text-secondary-text">当前 {text.length} 字</p>
        </section>

        {/* 2. 尺寸对比 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：尺寸对比</h2>
          <p className="text-xs text-muted">
            size 四档控制最小高度 / 字号 / 圆角：xs（min-h-16）、sm（min-h-20，默认）、md（min-h-24）、lg（min-h-28）。
          </p>
          <div className="flex flex-wrap items-end gap-4">
            {SIZE_ITEMS.map((item) => (
              <div key={item.size} className="flex flex-col gap-1">
                <span className="text-xs text-secondary-text">{item.label}</span>
                <TextArea size={item.size} placeholder="请输入内容" />
              </div>
            ))}
          </div>
        </section>

        {/* 3. rows 可见行数 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：rows 可见行数</h2>
          <p className="text-xs text-muted">
            rows 对应原生 rows 属性，控制默认可见行数；组件默认 rows=5，可独立于 size 设定，实际高度仍可拖拽调整（resize-y）。
          </p>
          <div className="flex flex-wrap items-end gap-4">
            {ROWS_ITEMS.map((item) => (
              <div key={item.rows} className="flex flex-col gap-1">
                <span className="text-xs text-secondary-text">{item.label}</span>
                <TextArea rows={item.rows} placeholder="输入多行内容" />
              </div>
            ))}
          </div>
        </section>

        {/* 4. variant 对比 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：variant 变体</h2>
          <p className="text-xs text-muted">
            primary 为默认样式（带阴影）；secondary 无阴影，适配放置在 Surface 容器内的场景。
          </p>
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">primary（默认，带阴影）</span>
              <TextArea variant="primary" placeholder="primary 变体" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">secondary（无阴影）</span>
              <TextArea variant="secondary" placeholder="secondary 变体" />
            </div>
          </div>
        </section>

        {/* 5. 禁用与只读 + maxLength */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：禁用与只读 + maxLength</h2>
          <p className="text-xs text-muted">
            disabled 显式禁用；传 value 但未传 onChange 时自动补 readOnly（只读展示语义）；maxLength 原生限制配合字数回显。
          </p>
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">禁用态（disabled）</span>
              <TextArea value="禁用的多行内容" disabled />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-secondary-text">只读展示（value 无 onChange）</span>
              <TextArea value="不可编辑的只读展示内容" />
            </div>
          </div>
          <TextArea
            value={limited}
            onChange={(e) => setLimited(e.target.value)}
            placeholder="最多输入 100 个字符"
            maxLength={100}
          />
          <p className="text-xs text-secondary-text">已输入 {limited.length} / 100 字</p>
        </section>

        {/* 6. 提交表单组合 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例六：提交表单组合（TextArea + HrsButton）</h2>
          <p className="text-xs text-muted">
            模拟备注提交场景：填写多行备注后点击「提交」，经 Toast 回显内容首行。
          </p>
          <TextArea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="填写多行备注内容"
            rows={4}
          />
          <div className="flex flex-wrap gap-3 border-t border-border/60 pt-3">
            <HrsButton variant="primary" size="sm" onClick={handleSubmit}>提交</HrsButton>
            <HrsButton size="sm" variant="ghost" onClick={() => setDraft('')}>清空</HrsButton>
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsTextAreaPage;
