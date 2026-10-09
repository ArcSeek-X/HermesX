/**
 * @file Main.tsx
 * @description 应用主内容滚动容器组件（hrs-page-container）。
 *
 * 作为 Shell 右侧列的唯一滚动容器，承担两件事：
 * 1. 渲染业务页内容（children，通常来自 <Outlet /> / RouteOutletBoundary）；
 * 2. 承载页面级固定背景：在「暗色主题 + 白名单路由」下渲染 LightBloom 光晕，作为 Ambient 背景。
 *
 * 关键布局约束（与 Shell 协同）：
 * - 盒子需贴到视口底边：竖向 padding 归属本组件自身（而非外层列），否则被
 *   [contain:layout_paint] 裁剪的 fixed 背景（LightBloom）底部会露出一条留白。
 * - [contain:layout_paint] 让本组件成为其 fixed 后代的「包含块 + 裁剪边界」，
 *   使背景相对本容器固定且不随内容滚动，同时不会越界盖到侧边栏/页头。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';
import { useLocation } from 'react-router-dom';
import { useTheme } from 'next-themes';
import { useThemeStore } from '../../stores/themeStore';
import { cn } from '../../utils/cn';
import LightBloom from '../vibeBack/LightBloom';

/**
 * 需要展示 LightBloom 背景光晕的路由白名单（精确匹配 location.pathname）。
 * 仅当处于白名单路由且为暗色主题时，背景光晕才渲染；其它路由一律不展示。
 * 如需扩展到其它页面，在此数组追加对应路径即可。
 */
const BACKGROUND_ROUTES = ['/home'];

/** Main 组件的 Props 定义 */
interface MainProps {
  /** 业务页内容节点，通常为 <Outlet /> / RouteOutletBoundary 渲染结果 */
  children?: React.ReactNode;
  /** 透传到 <main> 的额外类名：经 cn（tailwind-merge）与外部类合并，不覆盖布局约束类 */
  className?: string;
}

/**
 * 应用主内容滚动容器组件。
 *
 * 渲染一个带统一布局约束的 <main>（hrs-page-container），在暗色主题且命中白名单路由时
 * 注入 LightBloom 作为固定背景（zIndex 为负，稳定沉在内容之下），并渲染子内容。
 *
 * @param props.children - 业务页内容
 * @param props.className - 追加到 <main> 的外部类名
 * @returns 带滚动容器与（条件）背景光晕的页面主内容区
 */
export const Main: React.FC<MainProps> = ({ children, className }) => {
  // 当前路由路径：用于判断是否在背景光晕白名单内
  const { pathname } = useLocation();
  // 当前解析主题（next-themes）：用于决定是否展示暗色背景光晕
  const { resolvedTheme } = useTheme();
  // 取自系统主题主色（HEX），用户切换主色/主题时实时联动
  const { themeColor } = useThemeStore();

  // 仅当处于白名单路由且为暗色主题时，展示页面级固定背景光晕
  const showBackground =
    resolvedTheme === 'dark' && BACKGROUND_ROUTES.some((route) => pathname === route);

  return (
    <main className={cn(
      `hrs-page-container
      min-h-0 min-w-0 pt-4 pb-3 sm:pb-4
      flex-1 overflow-y-auto touch-pan-y
      [contain:layout_paint] will-change-[width]`,
      className,
    )}
    >
      {/* 页面级固定背景：仅暗色主题 + 白名单路由展示；zIndex 为负，稳定沉在内容之下
          （LightBloom 自身 position:fixed + 本组件 contain 使其成为相对本容器的固定背景） */}
      {showBackground && (
        <LightBloom
          style={{ position: 'fixed', inset: 0, zIndex: -1 }}
          background="transparent"
          baseColor={themeColor}
        />
      )}
      {children}
    </main>
  );
};
