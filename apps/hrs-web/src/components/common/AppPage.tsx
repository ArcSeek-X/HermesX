/**
 * ===================================
 * 应用页面容器组件（AppPage）
 * ===================================
 *
 * 作用：
 * 作为所有业务页面的顶层容器，提供统一的页面布局规范：
 * - 限制最大宽度（max-w-7xl），居中显示
 * - 统一内外边距（px/pb/pt），适配移动端和桌面端
 * - 保证最小高度撑满视口（min-h-full）
 *
 * 使用方式：
 *   <AppPage>
 *     <YourPageContent />
 *   </AppPage>
 */
import type React from 'react';
import { useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';

/**
 * 从当前路由路径派生「页面标识名」，用于拼装 <main> 的路由类名（hrs-apge-<name>）。
 * 规则：
 * - 取 pathname 的最后一段（去掉首尾斜杠），例如 /stock-dashboard -> stock-dashboard
 * - 根路径 "/" 归为 home
 * - 空段（如路径以斜杠结尾）回退到上一级段，仍为空则归为 home
 */
const getRouteName = (pathname: string): string => {
  const segments = pathname.split('/').filter(Boolean);
  if (segments.length === 0) return 'home';
  return segments[segments.length - 1];
};

/** AppPage 组件的 Props 定义 */
interface AppPageProps {
  /** 子节点内容，通常为页面主体内容 */
  children: React.ReactNode;
  /** 自定义 CSS 类名，用于覆盖默认样式 */
  className?: string;
}

/**
 * 应用页面容器组件
 *
 * 渲染一个 <main> 标签，包裹页面内容，提供统一的布局约束：
 * - mx-auto：水平居中
 * - min-h-full：最小高度撑满父容器
 * - max-w-7xl：最大宽度限制（1280px）
 * - px-4/pb-8/pt-4：默认内边距
 * - md:px-6 lg:px-8：响应式水平内边距
 *
 * @param props - 组件属性
 * @param props.children - 页面内容
 * @param props.className - 可选的自定义样式类名
 * @returns 带统一布局约束的页面容器
 */
export const AppPage: React.FC<AppPageProps> = ({ children, className = '' }) => {
  // 当前路由信息，用于派生页面级标识类名
  const location = useLocation();
  // 路由标识名，如 stock-dashboard / home / settings
  const routeName = getRouteName(location.pathname);
  return (
    <main
      className={cn(
        'hrs-page-main',
        // 路由级标识类：hrs-apge-<当前路由名称>，便于按页面定制样式
        `hrs-apge-${routeName}`,
        // 布局约束：居中 + 最小高度
        'mx-auto min-h-full w-full',
        // 用户自定义样式（优先级最高）
        className,
      )}
    >
      {children}
    </main>
  );
};
