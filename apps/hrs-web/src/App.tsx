/**
 * 应用根组件：装配全局 Provider 并挂载数据路由（RouterProvider）。
 * Provider 顺序（由外到内）：UiLanguage → AppMode → PageState → RouterProvider。
 * 鉴权守卫由路由 loader（protectedLoader）承担，不再依赖 AuthProvider。
 */

import type React from 'react';
import { UiLanguageProvider } from './contexts/UiLanguageContext';
import { AppModeProvider } from './contexts/AppModeContext';
import { PageStateProvider } from './stores/PageStateStore';
import { RouterProvider } from 'react-router-dom';
import { router } from './router/appRouter';
import { Toast } from '@components';
import './App.css';

const App: React.FC = () => (
  <UiLanguageProvider>
    <AppModeProvider>
      <PageStateProvider>
        <RouterProvider router={router} />
      </PageStateProvider>
    </AppModeProvider>
    <Toast />
  </UiLanguageProvider>
);

export default App;
