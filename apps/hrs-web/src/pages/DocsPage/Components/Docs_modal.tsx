/**
 * @fileoverview 组件文档页：Modal（模态框）
 * 路由地址 /docs/component/modal，菜单名「模态框」。
 * 用于演示 Modal 的声明式用法：Header/Heading/Body/Footer 组织、尺寸档位、弹出位置、遮罩变体与长内容滚动。
 * @module pages
 */

import React, { useState } from 'react';
import { AppPage, HrsButton, Modal } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 尺寸档位（示例二展示） */
const MODAL_SIZES = ['xs', 'sm', 'md', 'lg', 'full', 'cover'] as const;
/** 弹出位置（示例三展示） */
const MODAL_PLACEMENTS = ['top', 'center', 'bottom'] as const;
/** 遮罩变体（示例四展示） */
const MODAL_VARIANTS = ['opaque', 'blur', 'transparent'] as const;

/**
 * 模态框组件文档演示页。
 *
 * Modal 基于 HeroUI Modal 二次封装：isOpen / onClose 控制显隐，
 * children 用 Modal.Header / Modal.Heading / Modal.Body / Modal.Footer 组织内容；
 * Header 与 Body 之间自动渲染渐变分割线（Separator）。
 */
export const DocsModalPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例一：基础声明式模态框
  const [basicOpen, setBasicOpen] = useState(false);
  // 示例二：尺寸对比（复用同一个模态框切换 size）
  const [sizeDemo, setSizeDemo] = useState<(typeof MODAL_SIZES)[number] | null>(null);
  // 示例三：弹出位置
  const [placementDemo, setPlacementDemo] = useState<(typeof MODAL_PLACEMENTS)[number] | null>(null);
  // 示例四：遮罩变体 + 关闭行为
  const [variantDemo, setVariantDemo] = useState<(typeof MODAL_VARIANTS)[number] | null>(null);
  const [noDismissOpen, setNoDismissOpen] = useState(false);
  const [noCloseBtnOpen, setNoCloseBtnOpen] = useState(false);
  // 示例五：长内容滚动
  const [scrollDemo, setScrollDemo] = useState<'inside' | 'outside' | null>(null);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsModal.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Modal 封装的模态框（Modal）。isOpen / onClose 控制显隐，children 用 Header / Heading / Body / Footer 组织；
            支持 xs~cover 六档尺寸、top / center / bottom 弹出位置与 opaque / blur / transparent 三种遮罩变体。
          </p>
        </header>

        {/* 1. 声明式基础用法 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：声明式基础用法</h2>
          <p className="text-xs text-muted">
            Modal.Header + Modal.Heading 组织标题（自动带右上角关闭按钮），Header 与 Body 之间自动渲染渐变分割线。
          </p>
          <div className="flex flex-wrap gap-3">
            <HrsButton onClick={() => setBasicOpen(true)}>打开基础模态框</HrsButton>
          </div>
        </section>

        {/* 2. 尺寸对比 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：尺寸对比（size）</h2>
          <p className="text-xs text-muted">
            size 支持 xs / sm / md / lg / full / cover 六档（full 全屏无圆角、cover 覆盖式大尺寸）。
          </p>
          <div className="flex flex-wrap gap-3">
            {MODAL_SIZES.map((s) => (
              <HrsButton key={s} variant="secondary" onClick={() => setSizeDemo(s)}>
                size={s}
              </HrsButton>
            ))}
          </div>
        </section>

        {/* 3. 弹出位置 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：弹出位置（placement）</h2>
          <p className="text-xs text-muted">placement 支持 top / center（默认）/ bottom，控制模态框在视口中的垂直对齐位置。</p>
          <div className="flex flex-wrap gap-3">
            {MODAL_PLACEMENTS.map((p) => (
              <HrsButton key={p} variant="secondary" onClick={() => setPlacementDemo(p)}>
                {p}
              </HrsButton>
            ))}
          </div>
        </section>

        {/* 4. 遮罩变体与关闭行为 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：遮罩变体（variant）与关闭行为</h2>
          <p className="text-xs text-muted">
            variant 支持 opaque（默认渐变）/ blur（更深渐变）/ transparent（无遮罩）；isDismissable 控制点击遮罩是否关闭，hideCloseButton 隐藏关闭按钮。
          </p>
          <div className="flex flex-wrap gap-3">
            {MODAL_VARIANTS.map((v) => (
              <HrsButton key={v} variant="secondary" onClick={() => setVariantDemo(v)}>
                {v}
              </HrsButton>
            ))}
            <HrsButton variant="secondary" onClick={() => setNoDismissOpen(true)}>
              禁遮罩关闭
            </HrsButton>
            <HrsButton variant="secondary" onClick={() => setNoCloseBtnOpen(true)}>
              隐藏关闭按钮
            </HrsButton>
          </div>
        </section>

        {/* 5. 长内容滚动 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：长内容滚动（scroll）</h2>
          <p className="text-xs text-muted">
            scroll=inside 时内容区内部滚动（Header / Footer 固定），outside 时整个 Dialog 随页面滚动。
          </p>
          <div className="flex flex-wrap gap-3">
            <HrsButton variant="secondary" onClick={() => setScrollDemo('inside')}>
              inside
            </HrsButton>
            <HrsButton variant="secondary" onClick={() => setScrollDemo('outside')}>
              outside
            </HrsButton>
          </div>
        </section>
      </div>

      {/* 示例一模态框：默认配置（md / center / opaque） */}
      <Modal isOpen={basicOpen} onClose={() => setBasicOpen(false)}>
        <Modal.Header>
          <Modal.Heading>基础模态框</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm leading-6 text-secondary-text">
            这里是 Modal.Body 的内容区。点击遮罩、按 Esc 或右上角关闭按钮均可关闭；
            Header 与 Body 之间自动渲染 default 变体 + 两端渐隐的分割线。
          </p>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="ghost" onClick={() => setBasicOpen(false)}>取消</HrsButton>
          <HrsButton variant="primary" onClick={() => setBasicOpen(false)}>确定</HrsButton>
        </Modal.Footer>
      </Modal>

      {/* 示例二模态框：动态切换尺寸 */}
      <Modal isOpen={sizeDemo !== null} onClose={() => setSizeDemo(null)} size={sizeDemo ?? 'md'}>
        <Modal.Header>
          <Modal.Heading>size = {sizeDemo}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm leading-6 text-secondary-text">当前尺寸档位为 {sizeDemo}，圆角随尺寸档位自动映射。</p>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="primary" onClick={() => setSizeDemo(null)}>关闭</HrsButton>
        </Modal.Footer>
      </Modal>

      {/* 示例三模态框：动态切换弹出位置 */}
      <Modal isOpen={placementDemo !== null} onClose={() => setPlacementDemo(null)} placement={placementDemo ?? 'center'}>
        <Modal.Header>
          <Modal.Heading>placement = {placementDemo}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm leading-6 text-secondary-text">当前弹出位置为 {placementDemo}。</p>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="primary" onClick={() => setPlacementDemo(null)}>关闭</HrsButton>
        </Modal.Footer>
      </Modal>

      {/* 示例四模态框：动态切换遮罩变体 */}
      <Modal isOpen={variantDemo !== null} onClose={() => setVariantDemo(null)} variant={variantDemo ?? 'opaque'}>
        <Modal.Header>
          <Modal.Heading>variant = {variantDemo}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm leading-6 text-secondary-text">
            当前遮罩变体为 {variantDemo}。transparent 变体不渲染遮罩背景。
          </p>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="primary" onClick={() => setVariantDemo(null)}>关闭</HrsButton>
        </Modal.Footer>
      </Modal>

      {/* 示例四：禁止点击遮罩关闭（只能通过按钮关闭） */}
      <Modal isOpen={noDismissOpen} onClose={() => setNoDismissOpen(false)} isDismissable={false}>
        <Modal.Header>
          <Modal.Heading>禁遮罩关闭</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm leading-6 text-secondary-text">isDismissable=false：点击遮罩不会关闭，请使用下方按钮关闭。</p>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="primary" onClick={() => setNoDismissOpen(false)}>知道了</HrsButton>
        </Modal.Footer>
      </Modal>

      {/* 示例四：隐藏右上角关闭按钮 */}
      <Modal isOpen={noCloseBtnOpen} onClose={() => setNoCloseBtnOpen(false)} hideCloseButton>
        <Modal.Header>
          <Modal.Heading>无关闭按钮</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm leading-6 text-secondary-text">hideCloseButton：右上角关闭按钮已隐藏，请使用下方按钮或按 Esc 关闭。</p>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="primary" onClick={() => setNoCloseBtnOpen(false)}>关闭</HrsButton>
        </Modal.Footer>
      </Modal>

      {/* 示例五模态框：长内容滚动对比 */}
      <Modal isOpen={scrollDemo !== null} onClose={() => setScrollDemo(null)} scroll={scrollDemo ?? 'inside'} size="sm">
        <Modal.Header>
          <Modal.Heading>scroll = {scrollDemo}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <div className="flex flex-col gap-2">
            {Array.from({ length: 12 }, (_, i) => (
              <p key={i} className="text-sm leading-6 text-secondary-text">
                第 {i + 1} 段：这是用于演示滚动行为的长内容。scroll=inside 时仅 Body 区域滚动，Header 与 Footer 保持固定。
              </p>
            ))}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="primary" onClick={() => setScrollDemo(null)}>关闭</HrsButton>
        </Modal.Footer>
      </Modal>
    </AppPage>
  );
};

export default DocsModalPage;
