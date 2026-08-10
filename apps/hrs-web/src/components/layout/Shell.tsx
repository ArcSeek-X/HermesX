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
 * 1. 移动端（< lg 断点，即 < 1024px）：
 *    - 顶部显示浮动工具栏（左侧汉堡菜单按钮 + 右侧主题/语言切换）
 *    - 通过 Drawer 抽屉从左侧滑出导航菜单
 *    - 主内容区域全宽显示，顶部预留工具栏高度（pt-14）
 * 2. 桌面端（>= lg 断点，即 >= 1024px）：
 *    - 左侧显示固定侧边栏（sticky 定位，随页面滚动）
 *    - 侧边栏宽度：展开 136px / 折叠 64px（当前默认展开）
 *    - 主内容区域紧邻侧边栏右侧，无需顶部留白
 * 3. 响应式切换：
 *    - 当窗口从移动端放大到桌面端（>= 1024px）时，自动关闭抽屉，
 *      避免桌面端同时出现固定侧边栏和抽屉导航
 *
 * 布局层级：
 *   Shell（最外层）
 *   ├── 移动端顶部浮动栏（lg:hidden）
 *   ├── 主体容器（max-w-[1680px] 居中）
 *   │   ├── 桌面端侧边栏（lg:flex，sticky）
 *   │   └── 主内容区（flex-1，渲染 children 或 Outlet）
 *   └── 移动端抽屉导航（Drawer，从左侧滑出）
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
import { Menu } from 'lucide-react';
import { Outlet } from 'react-router-dom';
import { Drawer } from '../common/Drawer';
import { SidebarNav } from './SidebarNav';
import { cn } from '../../utils/cn';
import { ThemeToggle } from '../theme/ThemeToggle';
import { UiLanguageToggle } from '../i18n/UiLanguageToggle';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

/** Shell 组件的属性定义 */
type ShellProps = {
  /** 可选的子内容；若未提供，则通过 react-router 的 <Outlet /> 渲染子路由 */
  children?: React.ReactNode;
};

/**
 * 应用外壳布局组件
 *
 * 渲染整个应用的最外层骨架，包括：
 * - 移动端顶部浮动工具栏（汉堡菜单 + 主题/语言切换）
 * - 桌面端左侧固定侧边栏（SidebarNav）
 * - 主内容区域（children 或 <Outlet />）
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
  /** 侧边栏折叠状态：true=折叠（64px）/ false=展开（136px），当前固定为展开，预留折叠能力 */
  const collapsed = false;
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
      {/* ===== 移动端顶部浮动栏（仅 < lg 断点显示）===== */}
      {/* pointer-events-none 让容器不拦截点击，内部按钮通过 pointer-events-auto 恢复交互 */}
      {/* fixed 定位 + z-40 确保浮动在最上层，inset-x-0 水平铺满 */}
      <div className="pointer-events-none fixed inset-x-0 top-3 z-40 flex items-start justify-between px-3 lg:hidden">
        {/* 汉堡菜单按钮：点击打开移动端抽屉导航 */}
        {/* 40x40 圆角按钮，半透明背景 + 毛玻璃模糊，悬停变色 */}
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="pointer-events-auto inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/85 text-secondary-text shadow-soft-card backdrop-blur-md transition-colors hover:bg-hover hover:text-foreground"
          aria-label={t('layout.openNav')}
        >
          <Menu className="h-5 w-5" />
        </button>
        {/* 右上角工具区：语言切换 + 主题切换，水平排列，间距 8px */}
        <div className="pointer-events-auto flex items-center gap-2">
          <UiLanguageToggle />
          <ThemeToggle />
        </div>
      </div>

      {/* ===== 主体区域容器：侧边栏 + 内容区 ===== */}
      {/* mx-auto 水平居中，max-w-[1680px] 限制最大宽度，防止超宽屏内容拉伸 */}
      {/* 响应式内边距：默认 px-3 py-3 → sm:px-4 sm:py-4 → lg:px-5 */}
      <div className="hrs-container mx-auto flex min-h-screen w-full max-w-[1680px] px-3 py-3 sm:px-4 sm:py-4 lg:px-5">
        {/* 桌面端固定侧边栏（仅 >= lg 断点显示） */}
        {/* sticky 定位：随页面滚动但固定在视口顶部偏移 1.5rem 处 */}
        {/* 圆角 1.5rem + 半透明背景 + 毛玻璃模糊 + 柔和阴影，终端风格视觉 */}
        {/* max-h 限制最大高度，留出顶部和底部间距，防止内容溢出视口 */}
        {/* transition-[width] 支持折叠/展开时的宽度过渡动画（200ms） */}
        <aside
          className={cn(
            'hrs-side sticky top-3 z-40 hidden shrink-0 overflow-visible rounded-[1.5rem] border border-[var(--shell-sidebar-border)] bg-card/72 p-2.5 shadow-soft-card backdrop-blur-sm transition-[width] duration-200 lg:flex',
            // 高度约束：视口高度减去顶部偏移量，确保不溢出
            'max-h-[calc(100vh-1.5rem)] self-start sm:top-4 sm:max-h-[calc(100vh-2rem)]',
            // 宽度：折叠 64px / 展开 136px
            collapsed ? 'w-[64px]' : 'w-[136px]'
          )}
          aria-label={t('layout.desktopSidebar')}
        >
          {/* 侧边栏导航组件：variant="rail" 表示桌面端紧凑模式，onNavigate 导航后关闭移动端抽屉 */}
          <SidebarNav collapsed={collapsed} variant="rail" onNavigate={() => setMobileOpen(false)} />
        </aside>

        {/* 主内容区域：占据侧边栏之外的所有剩余空间（flex-1） */}
        {/* min-h-0 min-w-0 防止 flex 子元素内容撑破容器 */}
        {/* pt-14：移动端为顶部浮动栏预留空间（约 56px）；桌面端无需留白（lg:pt-0） */}
        {/* lg:pl-3：桌面端与侧边栏之间保留 12px 间距 */}
        {/* touch-pan-y：允许触摸设备垂直滚动，不拦截手势 */}
        <main className="hrs-page-container min-h-0 min-w-0 flex-1 pt-14 lg:pl-3 lg:pt-0 touch-pan-y">
          {/* 优先渲染 children（直接包裹模式），否则渲染 <Outlet />（路由模式） */}
          {children ?? <Outlet />}
        </main>
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
