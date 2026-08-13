/**
 * ===================================
 * 应用外壳布局组件（Shell）
 * ===================================
 *
 * 作用：
 * 作为整个 Web 应用的最外层布局骨架，负责搭建页面的整体结构框架。
 * 所有已登录页面都嵌套在此组件内部，它决定了「侧边栏 / 顶部栏 / 内容区」的排布方式。
 *
 * 核心职责：
 * 1. 顶部页头（ShellHeader）：
 *    - 固定在右侧列顶部，不随内容区滚动（滚动发生在 hrs-page-container）
 *    - 移动端（< lg）：左侧汉堡菜单 + 中间页面标题 + 右侧换肤/语言切换
 *    - 桌面端（>= lg）：左侧侧边栏折叠按钮 + 中间页面标题 + 右侧换肤/语言切换
 * 2. 移动端（< lg 断点，即 < 1024px）：
 *    - 通过 Drawer 抽屉从左侧滑出导航菜单
 *    - 主内容区域全宽显示
 * 3. 桌面端（>= lg 断点，即 >= 1024px）：
 *    - 左侧显示固定侧边栏（不随内容区滚动）
 *    - 侧边栏宽度：展开 136px / 折叠 64px，由用户点击页头折叠按钮控制，状态持久化到 localStorage
 *    - 主内容区域紧邻侧边栏右侧
 * 4. 响应式切换：
 *    - 当窗口从移动端放大到桌面端（>= 1024px）时，自动关闭抽屉，
 *      避免桌面端同时出现固定侧边栏和抽屉导航
 *
 * 布局层级：
 *   Shell（最外层）
 *   └── 主体容器（max-w-[1680px] 居中，flex 行布局，h-[calc(100vh-1.5rem)] 固定高度，不滚动）
 *       ├── 左侧：桌面端侧边栏（lg:flex，self-start 固定）
 *       └── 右侧列（flex-col，flex-1）
 *           ├── ShellHeader（h-12，固定，不参与滚动）
 *           └── 主内容区 hrs-page-container（flex-1，overflow-y-auto 滚动容器，渲染 children 或 Outlet）
 *   + 移动端抽屉导航（Drawer，从左侧滑出，挂载在 Shell 下）
 *
 * 使用方式：
 *   作为路由布局组件使用，子路由通过 <Outlet /> 渲染：
 *   <Route element={<Shell />}>
 *     <Route path="dashboard" element={<DashboardPage />} />
 *   </Route>
 *
 *   也可以直接包裹内容：
 *   <Shell>
 *     <YourContent />
 *   </Shell>
 */
import type React from 'react';
import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Drawer } from '../common/Drawer';
import { ShellHeader } from './ShellHeader';
import { SidebarNav } from './SidebarNav';
import { cn } from '../../utils/cn';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { useCachedState } from '../../hooks/useCachedState';

/** Shell 组件的属性定义 */
type ShellProps = {
  /** 可选的子内容；若未提供，则通过 react-router 的 <Outlet /> 渲染子路由 */
  children?: React.ReactNode;
};

/**
 * 应用外壳布局组件
 *
 * 渲染整个应用的最外层骨架，包括：
 * - 顶部页头 ShellHeader（固定在右侧列顶部：页面标题 + 换肤/语言切换）
 * - 桌面端左侧固定侧边栏（SidebarNav）
 * - 主内容区域 hrs-page-container（overflow-y-auto 滚动容器，children 或 <Outlet />）
 * - 移动端抽屉导航（Drawer）
 *
 * 内部通过 useState 管理移动端抽屉的开关状态，
 * 通过 useEffect 监听窗口 resize 事件实现响应式自动关闭。
 *
 * @param props - 组件属性
 * @param props.children - 可选的子内容，优先于 <Outlet /> 渲染
 * @returns 完整的应用布局骨架
 */
export const Shell: React.FC<ShellProps> = ({ children }) => {
  /** 移动端抽屉导航的展开/收起状态 */
  const [mobileOpen, setMobileOpen] = useState(false);
  /** 桌面端侧边栏折叠状态：true=折叠（64px）/ false=展开（136px），通过 useCachedState 持久化到 localStorage */
  const [collapsed, setCollapsed] = useCachedState<boolean>('layout.sidebarCollapsed', false);
  /** 国际化翻译函数，用于获取多语言文本 */
  const { t } = useUiLanguage();

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
    // 最外层容器：撑满整个视口，应用全局背景色和文字颜色
    <div className="hrs-layout min-h-screen bg-background text-foreground">
      {/* ===== 主体区域容器：左侧边栏 + 右侧（页头 + 内容区）===== */}
      {/* mx-auto 水平居中，max-w-[1680px] 限制最大宽度，防止超宽屏内容拉伸 */}
      {/* flex 行布局：左侧侧边栏 + 右侧列 */}
      {/* h-[calc(100vh-1.5rem)]：固定高度，不滚动；滚动发生在内部 hrs-page-container 上 */}
      {/* 响应式内边距：px-3 py-3 → sm:px-4 sm:py-4 → lg:px-5 */}
      <div className="hrs-container mx-auto flex h-[calc(100vh)] w-full max-w-[1680px] px-3 pb-3 sm:px-4 sm:pb-4 lg:px-4">
        {/* ===== 左侧：桌面端固定侧边栏（仅 >= lg 断点显示）===== */}
        {/* self-start：高度自适应内容，不拉伸填满容器 */}
        {/* 圆角 1.5rem + 半透明背景 + 毛玻璃模糊 + 柔和阴影，终端风格视觉 */}
        {/* transition-[width] 支持折叠/展开时的宽度过渡动画（200ms） */}
        <aside
          className={cn(
            'hrs-side h-full z-40 hidden p-2.5 mt-2 shrink-0 overflow-visible self-start border border-[var(--shell-sidebar-border)] bg-card/72 shadow-soft-card backdrop-blur-sm transition-[width,border-radius] duration-200 lg:flex',
            // 宽度：折叠 64px / 展开 136px；圆角：折叠态小圆角、展开态大圆角
            collapsed ? 'w-[64px] rounded-2xl items-center justify-center' : 'w-[136px] rounded-[1.5rem]'
          )}
          aria-label={t('layout.desktopSidebar')}
        >
          {/* 侧边栏导航组件：variant="rail" 表示桌面端紧凑模式，onNavigate 导航后关闭移动端抽屉 */}
          <SidebarNav collapsed={collapsed} variant="rail" onNavigate={() => setMobileOpen(false)} />
        </aside>

        {/* ===== 右侧列：页头 + 主内容区 ===== */}
        {/* flex-col 纵向排列，flex-1 占据侧边栏之外的所有剩余宽度，高度拉伸填满容器 */}
        {/* lg:pl-3：桌面端与侧边栏之间保留 12px 间距 */}
        <div className="flex min-h-0 flex-1 flex-col lg:pl-3">
          {/* ===== 顶部页头（固定，不随内容区滚动）===== */}
          <ShellHeader
            collapsed={collapsed}
            onToggleSidebar={() => setCollapsed((c) => !c)}
            onOpenMobileNav={() => setMobileOpen(true)}
            className = {
             "px-4 md:px-3 lg:px-4"
            }
          />

          {/* ===== 主内容区域（滚动容器）===== */}
          {/* min-h-0：允许 flex 子元素收缩，使 overflow-y-auto 生效 */}
          {/* bg-background：确保 padding 区域不透明，遮挡滚动内容 */}
          {/* touch-pan-y：允许触摸设备垂直滚动，不拦截手势 */}
          <main className="hrs-page-container 
            min-h-0 min-w-0 
            px-4 md:px-3 lg:px-4 pt-4 pb-8   
            flex-1 overflow-y-auto bg-background touch-pan-y"
          >
            {/* 优先渲染 children（直接包裹模式），否则渲染 <Outlet />（路由模式） */}
            {children ?? <Outlet />}
          </main>
        </div>
      </div>

      {/* ===== 移动端抽屉导航（从左侧滑出，仅移动端使用）===== */}
      {/* Drawer 组件提供遮罩层 + 滑入动画，width="max-w-xs" 限制最大宽度 320px */}
      {/* zIndex=90 确保在顶部浮动栏（z-40）之上显示 */}
      <Drawer
        isOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
        title={t('layout.navMenu')}
        width="max-w-xs"
        zIndex={90}
        side="left"
      >
        {/* 抽屉内的侧边栏导航：variant 默认为 full 模式，导航后自动关闭抽屉 */}
        <SidebarNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>
    </div>
  );
};
