/**
 * 应用根组件
 */

import { AppRouter } from './router';
import { ToastProvider } from './components/common';
import { ThemeProvider, AppSettingsProvider, BoardDataProvider } from './contexts';

export function App() {
  return (
    <ThemeProvider>
      <AppSettingsProvider>
        <BoardDataProvider>
          <ToastProvider>
            <AppRouter />
          </ToastProvider>
        </BoardDataProvider>
      </AppSettingsProvider>
    </ThemeProvider>
  );
}
