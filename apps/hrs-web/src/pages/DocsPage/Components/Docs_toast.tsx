/**
 * @fileoverview 组件文档页：Toast（命令式轻提示）
 * 路由地址 /docs/component/toast，菜单名「轻提示」。
 * 用于演示 showToast 命令式触发：视觉变体、浮层方位、自动关闭时长、查看详情与手动关闭。
 * @module pages
 */

import React, { useState } from 'react';
import { AppPage, HrsButton, dismissAllToasts, dismissToast, showToast } from '../../../components';
import type { ToastPlacement, ToastVariant } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 6 个浮层方位（示例二展示） */
const PLACEMENTS: ToastPlacement[] = ['top start', 'top', 'top end', 'bottom start', 'bottom', 'bottom end'];

/**
 * 轻提示组件文档演示页。
 *
 * Toast 为命令式组件：全局宿主 <Toast /> 已挂在 App.tsx，任意位置调用 showToast()
 * 即在视口角落弹出浮层卡片；便捷方法 showToast.info / success / warning / danger 预置 variant。
 */
export const DocsToastPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例五：记录最近一条手动关闭 demo 的 id
  const [persistId, setPersistId] = useState<string | null>(null);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsToast.title')}</h1>
          <p className="text-xs text-muted">
            命令式轻提示（Toast）：全局宿主已挂载，任意位置调用 showToast 传入 title / description / variant / placement 等字段
            即可触发；返回 toast id 供 dismissToast 手动关闭，支持 6 个浮层方位与自动关闭时长控制。
          </p>
        </header>

        {/* 1. 五种视觉变体 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：五种视觉变体（variant）</h2>
          <p className="text-xs text-muted">
            default / accent / success / warning / danger；便捷方法 showToast.info / success / warning / danger 预置对应变体。
          </p>
          <div className="flex flex-wrap gap-3">
            {(['default', 'accent', 'success', 'warning', 'danger'] as ToastVariant[]).map((v) => (
              <HrsButton
                key={v}
                variant="secondary"
                onClick={() => showToast({
                  title: `variant = ${v}`,
                  description: `这是一条 ${v} 风格的轻提示，3 秒后自动关闭。`,
                  variant: v,
                })}
              >
                {v}
              </HrsButton>
            ))}
          </div>
        </section>

        {/* 2. 六个浮层方位 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：六个浮层方位（placement）</h2>
          <p className="text-xs text-muted">
            placement 支持上 / 下 × 左 / 中 / 右六方位；同一方位多条 toast 自动纵向堆叠。
          </p>
          <div className="grid max-w-xl grid-cols-3 gap-3">
            {PLACEMENTS.map((p) => (
              <HrsButton
                key={p}
                size="xs"
                variant="outline"
                onClick={() => showToast.info({ title: p, description: `方位：${p}`, placement: p })}
              >
                {p}
              </HrsButton>
            ))}
          </div>
        </section>

        {/* 3. 自动关闭时长 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：自动关闭时长（duration）</h2>
          <p className="text-xs text-muted">
            duration 默认 3000ms；传 0 表示不自动关闭，需手动点 × 或调用 dismissToast 关闭。
          </p>
          <div className="flex flex-wrap gap-3">
            <HrsButton variant="secondary" onClick={() => showToast.success({ title: '默认 3 秒关闭', description: 'duration 缺省为 3000ms' })}>
              默认 3 秒
            </HrsButton>
            <HrsButton variant="secondary" onClick={() => showToast.success({ title: '5 秒后关闭', description: 'duration = 5000', duration: 5000 })}>
              5 秒关闭
            </HrsButton>
            <HrsButton variant="secondary" onClick={() => showToast.warning({ title: '不会自动关闭', description: 'duration = 0，点击右上角 × 手动关闭', duration: 0 })}>
              不自动关闭
            </HrsButton>
          </div>
        </section>

        {/* 4. 查看详情与操作插槽 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：查看详情（rawMessage）与操作插槽（action）</h2>
          <p className="text-xs text-muted">
            rawMessage 与 description 不同时出现「查看详情」展开完整原文；action 在内容区右侧渲染操作按钮插槽。
          </p>
          <div className="flex flex-wrap gap-3">
            <HrsButton
              variant="secondary"
              onClick={() => showToast.danger({
                title: '数据拉取失败',
                description: 'akshare 行情接口超时，已自动降级到备用数据源。',
                rawMessage: 'TimeoutError: connect ETIMEDOUT 172.16.0.3:443\n    at Socket.connectTimeout (node:net:2145:32)\n    at Socket.emit (node:events:523:35)\n    at TCP.dispatch [as ontimeout] (node:net:379:8)',
                duration: 0,
              })}
            >
              错误 + 查看详情
            </HrsButton>
            <HrsButton
              variant="secondary"
              onClick={() => showToast({
                title: '报告已生成',
                description: '《贵州茅台 2026-09-09 分析报告》已保存到报告列表。',
                variant: 'success',
                action: <HrsButton size="xs" variant="ghost" onClick={() => dismissAllToasts()}>查看</HrsButton>,
              })}
            >
              带操作按钮
            </HrsButton>
          </div>
        </section>

        {/* 5. 手动关闭 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：手动关闭（dismissToast / dismissAllToasts）</h2>
          <p className="text-xs text-muted">
            showToast 返回 toast id；dismissToast(id) 关闭指定一条，dismissAllToasts() 关闭全部。
          </p>
          <div className="flex flex-wrap gap-3">
            <HrsButton
              variant="secondary"
              onClick={() => {
                const id = showToast({ title: '待处理任务', description: '这条不会自动关闭，点击下方按钮手动关闭。', duration: 0 });
                setPersistId(id);
              }}
            >
              弹出一条常驻
            </HrsButton>
            <HrsButton variant="danger-soft" isDisabled={!persistId} onClick={() => { if (persistId) dismissToast(persistId); setPersistId(null); }}>
              关闭上一条
            </HrsButton>
            <HrsButton variant="danger-soft" onClick={() => dismissAllToasts()}>
              关闭全部
            </HrsButton>
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsToastPage;
