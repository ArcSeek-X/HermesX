/**
 * HrsDrawer 组件文档演示页：滑出方向、尺寸档位、遮罩变体与插槽。
 */

import React, { useState } from 'react';
import { HrsButton, HrsDrawer, type HrsDrawerPlacement, type HrsDrawerSize, type HrsDrawerVariant } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';

/**
 * 抽屉组件文档演示页。
 *
 * HrsDrawer 基于 HeroUI Drawer 二次封装：isOpen / onClose 控制显隐，
 * children 用 HrsDrawer.Body / HrsDrawer.Footer 组织内容；
 * placement 控制滑出方向（左右控宽度、上下控高度），size 提供 xs~full 七档。
 */
export const DocsDrawerPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例一：基础声明式抽屉
  const [basicOpen, setBasicOpen] = useState(false);
  // 示例二：四个滑出方向（同一时刻只开一个，null 表示关闭）
  const [direction, setDirection] = useState<HrsDrawerPlacement | null>(null);
  // 示例三：尺寸对比（复用同一个抽屉切换 size）
  const [sizeDemo, setSizeDemo] = useState<HrsDrawerSize | null>(null);
  // 示例四：遮罩变体对比
  const [variantDemo, setVariantDemo] = useState<HrsDrawerVariant | null>(null);
  // 示例五：底部抽屉（showHandle 拖拽手柄 + hideCloseButton + footer 快捷插槽）
  const [handleOpen, setHandleOpen] = useState(false);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsDrawer.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Drawer 封装的侧滑抽屉（HrsDrawer）。isOpen / onClose 控制显隐，children 用 Body / Footer 组织；
            支持左右上下四方向、xs~full 七档尺寸（左右方向控宽度、上下方向控高度）与 opaque/blur/transparent 三种遮罩变体。
          </p>
        </header>

        {/* 1. 声明式基础用法：title + Body + Footer */}
        <DocsSection title="示例一：声明式基础用法" description="title 快捷标题 + HrsDrawer.Body / HrsDrawer.Footer 组织内容，默认从右侧滑出（placement=right、size=md、variant=opaque）， 点击遮罩、按 Esc 或右上角关闭按钮均可关闭。">
          <div className="flex flex-wrap gap-3">
            <HrsButton onClick={() => setBasicOpen(true)}>打开基础抽屉</HrsButton>
          </div>
        </DocsSection>

        {/* 2. 四个滑出方向 */}
        <DocsSection title="示例二：四个滑出方向（placement）" description="placement 支持 top / bottom / left / right；左右方向由 size 控制宽度，上下方向由 size 控制最大高度。">
          <div className="flex flex-wrap gap-3">
            {(['top', 'right', 'bottom', 'left'] as HrsDrawerPlacement[]).map((placement) => (
              <HrsButton key={placement} variant="secondary" onClick={() => setDirection(placement)}>
                {placement}
              </HrsButton>
            ))}
          </div>
        </DocsSection>

        {/* 3. 尺寸对比 */}
        <DocsSection title="示例三：尺寸对比（size）" description="size 支持 xs / sm / md / lg / xl / xxl / full 七档；窄视口自动铺满可用宽度，避免档位失去区分度。">
          <div className="flex flex-wrap gap-3">
            {(['xs', 'sm', 'md', 'lg', 'xl'] as HrsDrawerSize[]).map((size) => (
              <HrsButton key={size} variant="secondary" onClick={() => setSizeDemo(size)}>
                size={size}
              </HrsButton>
            ))}
          </div>
        </DocsSection>

        {/* 4. 遮罩变体 */}
        <DocsSection title="示例四：遮罩变体（variant）" description="variant 支持 opaque（默认渐变遮罩）/ blur（更深渐变）/ transparent（无遮罩，不阻挡背景交互）。">
          <div className="flex flex-wrap gap-3">
            {(['opaque', 'blur', 'transparent'] as HrsDrawerVariant[]).map((variant) => (
              <HrsButton key={variant} variant="secondary" onClick={() => setVariantDemo(variant)}>
                {variant}
              </HrsButton>
            ))}
          </div>
        </DocsSection>

        {/* 5. 手柄 + 隐藏关闭按钮 + footer 快捷插槽 */}
        <DocsSection title="示例五：手柄 / 隐藏关闭按钮 / footer 插槽" description="showHandle 显示顶部拖拽手柄（支持拖拽关闭）、hideCloseButton 隐藏右上角关闭按钮、 footer 快捷插槽与 children 中的 Footer 可共存。">
          <div className="flex flex-wrap gap-3">
            <HrsButton onClick={() => setHandleOpen(true)}>打开底部抽屉</HrsButton>
          </div>
        </DocsSection>
      </div>

      {/* 示例一抽屉：默认配置（right / md / opaque） */}
      <HrsDrawer
        isOpen={basicOpen}
        onClose={() => setBasicOpen(false)}
        title="基础抽屉"
        footer={<HrsButton variant="primary" onClick={() => setBasicOpen(false)}>知道了</HrsButton>}
      >
        <HrsDrawer.Body>
          <div className="flex flex-col gap-3 text-sm leading-6 text-secondary-text">
            <p>这里是 HrsDrawer.Body 的内容区。Header 与 Body 之间自动渲染渐变分割线（Separator）。</p>
            <p>默认自带焦点陷阱、Esc 关闭、滚动锁定与拖拽关闭能力（均来自 HeroUI Drawer 底座）。</p>
          </div>
        </HrsDrawer.Body>
      </HrsDrawer>

      {/* 示例二抽屉：动态切换滑出方向 */}
      <HrsDrawer
        isOpen={direction !== null}
        onClose={() => setDirection(null)}
        placement={direction ?? 'right'}
        title={`placement = ${direction}`}
      >
        <HrsDrawer.Body>
          <p className="text-sm leading-6 text-secondary-text">
            当前滑出方向为 {direction}。top / bottom 方向由 size 控制最大高度，left / right 方向由 size 控制宽度。
          </p>
        </HrsDrawer.Body>
      </HrsDrawer>

      {/* 示例三抽屉：动态切换尺寸 */}
      <HrsDrawer
        isOpen={sizeDemo !== null}
        onClose={() => setSizeDemo(null)}
        size={sizeDemo ?? 'md'}
        title={`size = ${sizeDemo}`}
      >
        <HrsDrawer.Body>
          <p className="text-sm leading-6 text-secondary-text">
            当前尺寸档位为 {sizeDemo}。左右方向抽屉按宽度档位展开（窄视口自动铺满），上下方向抽屉按高度档位展开。
          </p>
        </HrsDrawer.Body>
      </HrsDrawer>

      {/* 示例四抽屉：动态切换遮罩变体 */}
      <HrsDrawer
        isOpen={variantDemo !== null}
        onClose={() => setVariantDemo(null)}
        variant={variantDemo ?? 'opaque'}
        title={`variant = ${variantDemo}`}
      >
        <HrsDrawer.Body>
          <p className="text-sm leading-6 text-secondary-text">
            当前遮罩变体为 {variantDemo}。transparent 变体不渲染遮罩背景，抽屉滑出时背景仍可交互。
          </p>
        </HrsDrawer.Body>
      </HrsDrawer>

      {/* 示例五抽屉：底部滑出 + 手柄 + 隐藏关闭按钮 + footer 插槽 */}
      <HrsDrawer
        isOpen={handleOpen}
        onClose={() => setHandleOpen(false)}
        placement="bottom"
        size="md"
        showHandle
        hideCloseButton
        title="底部抽屉（可拖拽关闭）"
        footer={<HrsButton variant="ghost" onClick={() => setHandleOpen(false)}>取消</HrsButton>}
      >
        <HrsDrawer.Body>
          <p className="text-sm leading-6 text-secondary-text">
            showHandle 已开启：顶部手柄可拖拽下拉关闭。hideCloseButton 隐藏了右上角关闭按钮，
            关闭途径为拖拽手柄、按 Esc 或点击遮罩。
          </p>
        </HrsDrawer.Body>
      </HrsDrawer>
    </AppPage>
  );
};

export default DocsDrawerPage;
