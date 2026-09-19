/**
 * @file Shell.tsx
 * @description 应用外壳布局：桌面端固定侧栏 + 顶部页头 + 主内容区（Web 端已登录页路由根）。
 *
 * 骨架：外层 min-h-screen 不滚动，滚动只发生在内部 hrs-page-container；
 * 子路由经 <Outlet /> 渲染，也可直接包裹 children。桌面侧栏用自研 SidebarNav，
 * 移动端汉堡由 ShellHeader 触发（onOpenMobileNav → mobileOpen；抽屉当前未挂载）。
 *
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-14
 */
import type React from 'react';
import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { ShellHeader } from './ShellHeader';
import { SidebarNav } from './SideBar/SidebarNav';
import { useLayoutStore } from '../../stores';
import { useThemeStore } from '../../stores/themeStore';

type ShellProps = {
  /** 可选子内容（React 节点），不传时改由 <Outlet /> 渲染子路由，默认不传 */
  children?: React.ReactNode;
};

/**
 * 应用外壳布局。
 * @param props.children 可选子内容，优先于 <Outlet /> 渲染（直接包裹模式）
 * @returns 完整的应用布局骨架（侧边栏 + 页头 + 内容区）
 */
export const Shell: React.FC<ShellProps> = ({ children }) => {
  /** 移动端抽屉导航展开态，默认收起 */
  const [mobileOpen, setMobileOpen] = useState(false);
  /**
   * 桌面端侧边栏折叠状态（三态）：offcanvas=正常 / collapsed=半折叠 / fully=完全折叠。
   * 由 Zustand 全局 store（stores/LayoutStore）承载，供跨子树组件读写；
   * 持久化在 store 的 action 内写回 localStorage。
   */
  const menuCollapsedState = useLayoutStore((state) => state.menuCollapsedState);
  const toggleMenuCollapsedState = useLayoutStore((state) => state.toggleMenuCollapsedState);
  /** 侧栏视觉主题：订阅 themeStore，作为 prop 透传给 SidebarNav（与折叠态透传同模式） */
  const sidebarTheme = useThemeStore((state) => state.sidebarTheme);

  /**
   * 监听窗口尺寸变化：
   * 当抽屉打开且窗口宽度放大到桌面端（>= 1024px）时，自动关闭抽屉，
   * 避免桌面端同时出现固定侧边栏和抽屉。
   */
  useEffect(() => {
    if (!mobileOpen) {
      return undefined;
    }

    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [mobileOpen]);

  return (
    // 最外层容器：撑满视口，应用全局背景色与文字色
    <div className="hrs-layout min-h-screen bg-background text-foreground">
      {/* 主体容器：max-w-[1680px] 居中限制最大宽度；flex 行布局；h-[calc(100vh)] 固定高度不滚动，滚动发生在内部 hrs-page-container */}
      <div className="hrs-container mx-auto flex h-[calc(100vh)] w-full max-w-[1680px]">
        {/* 桌面端固定侧边栏（仅 >= lg 显示）：宽度与三态折叠动画由 SidebarNav 内部 motion.div 驱动，此处仅透传折叠态；onNavigate 在导航后关闭移动端抽屉 */}
        <SidebarNav className="" theme={sidebarTheme} menuCollapsedState={menuCollapsedState} onNavigate={() => setMobileOpen(false)} />


        {/* 右侧列：flex-col 纵向排列，flex-1 占据侧边栏外的剩余宽度；lg:px-4 与侧边栏保留 16px 间距 */}
        <div className="flex min-h-0 flex-1 flex-col pb-3 sm:pb-4 sm:px-4 lg:px-4">
          {/* 顶部页头：固定在右侧列顶部，不随内容区滚动 */}
          <ShellHeader
            onToggleSidebar={toggleMenuCollapsedState}
            onOpenMobileNav={() => setMobileOpen(true)}

          />

          {/* 主内容区域：唯一滚动容器 */}
          {/* min-h-0：允许 flex 子元素收缩，使 overflow-y-auto 生效 */}
          {/* bg-background：确保 padding 区域不透明，遮挡滚动内容 */}
          {/* touch-pan-y：允许触摸设备垂直滚动，不拦截手势 */}
          <main className="hrs-page-container
            min-h-0 min-w-0
            pt-4
            flex-1 overflow-y-auto bg-background touch-pan-y"
          >
            {/* 优先渲染 children（直接包裹模式），否则渲染 <Outlet />（路由模式） */}
            {children ?? <Outlet />}
          </main>
        </div>
      </div>
    </div>
  );
};
