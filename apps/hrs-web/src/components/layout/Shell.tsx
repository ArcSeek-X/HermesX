/**
 * @file Shell.tsx
 * @description 应用外壳布局：桌面端固定侧栏 + 顶部页头 + 主内容区（Web 端已登录页路由根）。
 *   外层不滚动，滚动只发生在内部 hrs-page-container；子路由经 <KeepAliveOutlet /> 渲染
 *   （含错误边界 + 路由缓存），也可直接包裹 children。
 *
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-14
 */
import type React from 'react';
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { ShellHeader } from './ShellHeader';
import { SidebarNav } from './SideBar/SidebarNav';
import { Main } from './Main';
import { KeepAliveOutlet } from './KeepAliveOutlet';
import { useLayoutStore } from '../../stores';
import { useThemeStore } from '../../stores/themeStore';
import { useAgentChatStore } from '../../stores/agentChatStore';

/** 常驻副作用：把当前 pathname 同步给 agentChatStore，供其感知所在页（如离开 /chat 时决定是否弹 completionBadge） */
const AgentChatRouteSync: React.FC = () => {
  const location = useLocation();
  useEffect(() => {
    useAgentChatStore.getState().setCurrentRoute(location.pathname);
  }, [location.pathname]);
  return null;
};

type ShellProps = {
  /** 可选子内容；不传时经 <KeepAliveOutlet /> 渲染子路由 */
  children?: React.ReactNode;
};

/**
 * 应用外壳布局。
 * @param props.children 可选子内容，优先于子路由渲染（直接包裹模式）
 */
export const Shell: React.FC<ShellProps> = ({ children }) => {
  /** 移动端抽屉导航展开态，默认收起 */
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  /** 桌面端侧栏三态折叠：offcanvas / collapsed / fully，由 Zustand store 承载并持久化 */
  const menuCollapsedState = useLayoutStore((state) => state.menuCollapsedState);
  const toggleMenuCollapsedState = useLayoutStore((state) => state.toggleMenuCollapsedState);
  /** 侧栏视觉主题：订阅 themeStore，透传给 SidebarNav */
  const sidebarTheme = useThemeStore((state) => state.sidebarTheme);

  /** 抽屉打开且窗口放大到桌面端（>= 1024px）时自动收起，避免固定侧栏与抽屉同现 */
  useEffect(() => {
    if (!mobileNavOpen) {
      return undefined;
    }
    const closeOnDesktop = () => {
      if (window.innerWidth >= 1024) {
        setMobileNavOpen(false);
      }
    };
    window.addEventListener('resize', closeOnDesktop);
    return () => window.removeEventListener('resize', closeOnDesktop);
  }, [mobileNavOpen]);

  return (
    <div className="hrs-layout min-h-screen bg-background text-foreground">
      <AgentChatRouteSync />
      <div className="hrs-container mx-auto flex h-[calc(100vh)] w-full max-w-[1680px]">
        {/* 桌面端固定侧栏（仅 >= lg 显示）：折叠态透传，导航后关闭移动端抽屉 */}
        <SidebarNav
          className=""
          theme={sidebarTheme}
          menuCollapsedState={menuCollapsedState}
          onNavigate={() => setMobileNavOpen(false)}
        />

        {/* 右侧列：flex-col 占剩余宽度。竖向 padding 不放这里（已下移到 Main 内部），
            否则滚动容器无法贴到视口底边、固定背景（LightBloom）底部露白 */}
        <div className="flex min-h-0 flex-1 flex-col">
          <ShellHeader
            className="sm:px-4 lg:px-4"
            onToggleSidebar={toggleMenuCollapsedState}
            onOpenMobileNav={() => setMobileNavOpen(true)}
          />
          <Main className="sm:px-4 lg:px-4">
            {/* 优先 children（直接包裹模式），否则经 KeepAliveOutlet 渲染子路由 */}
            {children ?? <KeepAliveOutlet />}
          </Main>
        </div>
      </div>
    </div>
  );
};
