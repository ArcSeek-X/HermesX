/**
 * 应用入口文件（entry point）。
 *
 * 职责：
 * 1. 引入全局样式 index.css 与根组件 App。
 * 2. 用 createRoot 把 React 应用挂载到 index.html 中的 #root 节点。
 * 3. 在最外层包裹 <StrictMode> 与 <ThemeProvider>：
 *    - StrictMode：开发期启用双重渲染等额外检查，帮助发现副作用问题。
 *    - ThemeProvider：提供主题（深色/浅色）上下文，控制全局配色。
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './style/index.css'
import App from './App.tsx'
import { ThemeProvider } from './components/theme/ThemeProvider'

// 找到 DOM 中的 #root 容器并创建根，非 null 断言由 index.html 保证
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
)
