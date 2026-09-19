/**
 * 应用根组件：负责全局 Provider 装配与路由渲染。
 *
 * 设计要点：
 * 1. 全局 Provider 分层：UI 语言 → 运行模式 → 路由 → 鉴权 → 页面状态，逐层向内包裹，
 *    保证子组件都能消费到对应的上下文。
 *    （跨子树的全局状态如侧栏折叠走 src/stores/ 下的 Zustand store，无需 Provider 包裹。）
 * 2. 路由采用「壳布局 + 子路由出口」结构（Shell + RouteOutletBoundary），
 *    左侧导航栏常驻，右侧内容区随路由切换——具体渲染逻辑见抽取出的 AppContent。
 * 3. 鉴权态介入路由：未登录且开启鉴权时，受保护路由会被重定向到 /login。
 */

import type React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { Toast } from './components/basic/Toast';
import { UiLanguageProvider } from './contexts/UiLanguageContext';
import { AppModeProvider } from './contexts/AppModeContext';
import { AuthProvider } from './contexts/AuthContext';
import { PageStateProvider } from './stores/PageStateStore';
import AppContent from './AppContent';
import './App.css';

/**
 * 应用最外层组件：装配全局 Provider 并形成渲染树。
 * Provider 顺序（由外到内）：
 *   UiLanguageProvider → AppModeProvider → Router → AuthProvider → PageStateProvider → AppContent
 */
const App: React.FC = () => {
  return (
    <UiLanguageProvider>
      <AppModeProvider>
        <Router>
          <AuthProvider>
            <PageStateProvider>
              <AppContent />
            </PageStateProvider>
          </AuthProvider>
        </Router>
      </AppModeProvider>
      {/* 全局错误 toast 宿主：订阅命令式队列，在任意 API 报错时弹出 danger 浮层 */}
      <Toast />
    </UiLanguageProvider>
  );
};

export default App;
