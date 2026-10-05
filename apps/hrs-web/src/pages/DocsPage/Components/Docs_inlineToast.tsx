/**
 * @fileoverview 组件文档页：InlineToast（内联轻提示）
 * 路由地址 /docs/component/inline-toast，菜单名「内联轻提示」。
 * 用于演示 InlineToast：视觉变体、标题与可展开详情、操作按钮、关闭按钮。
 * @module pages
 */

import React, { useState } from 'react';
import { HrsButton, InlineToast } from '@components';
import type { ParsedApiError } from '../../../api/error';
import { AppPage } from '@components/layout/AppPage';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** InlineToast 支持的视觉变体（示例一展示；注意是 accent 而非 primary） */
type InlineToastVariant = 'default' | 'accent' | 'success' | 'warning' | 'danger';
const VARIANTS: InlineToastVariant[] = ['default', 'accent', 'success', 'warning', 'danger'];

/** 各变体对应的示例内容：rawMessage 与 message 相同，不展示「详情」按钮，便于突出变体本身 */
const variantContent: Record<InlineToastVariant, ParsedApiError> = {
  default: {
    title: '普通提示',
    message: '这是一条中性内联提示，不抢视觉。',
    rawMessage: '这是一条中性内联提示，不抢视觉。',
    category: 'unknown',
  },
  accent: {
    title: '信息提示',
    message: '当前为开发调试模式，部分实时数据可能延迟。',
    rawMessage: '当前为开发调试模式，部分实时数据可能延迟。',
    category: 'unknown',
  },
  success: {
    title: '操作成功',
    message: '数据已成功刷新，无需额外操作。',
    rawMessage: '数据已成功刷新，无需额外操作。',
    category: 'unknown',
  },
  warning: {
    title: '数据降级',
    message: '行情接口超时，已自动降级到本地缓存。',
    rawMessage: '行情接口超时，已自动降级到本地缓存。',
    category: 'upstream_timeout',
  },
  danger: {
    title: '连接失败',
    message: '无法连接到本地 Web 服务，请检查服务是否启动。',
    rawMessage: '无法连接到本地 Web 服务，请检查服务是否启动。',
    category: 'local_connection_failed',
  },
};

/**
 * 内联轻提示组件文档演示页。
 *
 * InlineToast 为内联（跟随文档流）提示卡片，区别于 Toast 的视口浮层：
 * 直接写入页面 DOM，承接 ParsedApiError，渲染标题、用户友好文案与可展开详情；
 * 支持 variant 语义色、操作按钮（actionLabel/onAction）与关闭按钮（onClose）。
 */
export const DocsInlineToastPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例五：关闭后隐藏，提供重置按钮重新展示
  const [dismissed, setDismissed] = useState(false);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">
            {t('layout.nav.development.docsInlineToast.title')}
          </h1>
          <p className="text-xs text-muted">
            内联轻提示（InlineToast）：就地插入页面 DOM 流，承接 ParsedApiError，渲染标题、用户友好文案与可展开详情；
            支持 variant 语义色、操作按钮（actionLabel/onAction）与关闭按钮（onClose）。
          </p>
        </header>

        {/* 1. 五种视觉变体 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：五种视觉变体（variant）</h2>
          <p className="text-xs text-muted">
            default / accent / success / warning / danger；外层语义色边带 + 内层 elevated 卡片；错误告警场景需显式传 variant="danger"。
          </p>
          <div className="flex flex-col gap-3">
            {VARIANTS.map((v) => (
              <InlineToast key={v} variant={v} content={variantContent[v]} />
            ))}
          </div>
        </section>

        {/* 2. 标题与描述：仅标题 / 仅描述 / 标题 + 描述 三种对比 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：标题与描述（title / message）三种对比</h2>
          <p className="text-xs text-muted">
            title 与 message 均为 ParsedApiError 字段；组件会跳过空字段，支持仅标题 / 仅描述 / 标题+描述 三种组合，不出现空白行。
          </p>
          <div className="flex flex-col gap-3">
            <InlineToast
              variant="default"
              content={{ title: '仅标题：数据源已切换为本地缓存。', message: '', rawMessage: '', category: 'unknown' }}
            />
            <InlineToast
              variant="default"
              content={{
                title: '',
                message: '仅描述：当前为开发调试模式，部分实时数据可能延迟。',
                rawMessage: '仅描述：当前为开发调试模式，部分实时数据可能延迟。',
                category: 'unknown',
              }}
            />
            <InlineToast
              variant="accent"
              content={{
                title: '标题 + 描述',
                message: '这是标题与描述组合的内联提示，标题加粗、描述辅以说明。',
                rawMessage: '这是标题与描述组合的内联提示，标题加粗、描述辅以说明。',
                category: 'unknown',
              }}
            />
          </div>
        </section>

        {/* 3. 标题与可展开详情：rawMessage 与 message 不一致时展示「详情」 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：标题与可展开详情（rawMessage 不一致时）</h2>
          <p className="text-xs text-muted">
            rawMessage 与展示文案 message 不一致时，提供可展开的「详细信息」面板，便于开发/排障定位；两者相同则不展示详情按钮。
          </p>
          <div className="flex flex-col gap-3">
            <InlineToast
              variant="danger"
              content={{
                title: '请求失败',
                message: '获取行情数据失败，请稍后重试。',
                rawMessage: 'Error: 504 Gateway Timeout at https://api.example.com/quotes (timeout=8000ms)',
                category: 'upstream_timeout',
              }}
            />
            <InlineToast
              variant="danger"
              content={{
                title: '请求失败',
                message: '获取行情数据失败，请稍后重试。',
                rawMessage: '获取行情数据失败，请稍后重试。',
                category: 'upstream_timeout',
              }}
            />
          </div>
        </section>

        {/* 4. 操作按钮：actionLabel + onAction */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：操作按钮（actionLabel / onAction）</h2>
          <p className="text-xs text-muted">
            同时提供 actionLabel 与 onAction 时，底部右侧渲染操作按钮（如「重试」）；点击触发传入的回调。
          </p>
          <div className="flex flex-col gap-3">
            <InlineToast
              variant="warning"
              content={{
                title: '数据同步失败',
                message: '自选股同步未完成，可点击右侧按钮重试。',
                rawMessage: 'Sync failed: partial data (12/30).',
                category: 'upstream_network',
              }}
              actionLabel="重试"
              onAction={() => {
                /* demo: 实际场景里重新发起请求 */
              }}
            />
            <InlineToast
              variant="danger"
              content={{
                title: '生成任务中断',
                message: '模型服务不可用，可重试或稍后查看状态。',
                rawMessage: 'upstream_llm_400: model overloaded',
                category: 'upstream_llm_400',
              }}
              actionLabel="重试"
              onAction={() => {
                /* demo */
              }}
            />
          </div>
        </section>

        {/* 5. 关闭按钮：onClose + 关闭事件 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：关闭按钮（onClose）/ 关闭事件</h2>
          <p className="text-xs text-muted">
            传入 onClose 时，右上角渲染关闭图标按钮；点击触发 onClose，由调用方决定是否移除提示（此处用状态控制显隐，并提供重置）。
          </p>
          <div className="flex flex-col gap-3">
            {!dismissed ? (
              <InlineToast
                variant="danger"
                content={{
                  title: '会话即将过期',
                  message: '你的登录状态将在 5 分钟后失效，请及时保存。',
                  rawMessage: 'Token expiring in 300s.',
                  category: 'unknown',
                }}
                onClose={() => setDismissed(true)}
              />
            ) : (
              <p className="text-xs text-muted">提示已通过 onClose 关闭（调用方移除了该提示）。</p>
            )}
            <div>
              <HrsButton size="xs" variant="outline" onClick={() => setDismissed(false)}>
                重置示例五
              </HrsButton>
            </div>
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsInlineToastPage;
