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
import { initScrollLockCompensation } from './utils/scrollLockCompensation'
import { useAuthStore } from './stores/AuthStore'
import { useRouterStore } from './stores/RouterStore'

// 弹层锁滚动（overflow: hidden）时补等宽 padding-right，消除整页横向抖动
initScrollLockCompensation()

/**
 * 启动引导：先拉取鉴权状态并注入业务路由，再挂载 React，
 * 保证首屏路由匹配前鉴权态已就绪、业务路由已落表（避免首屏闪烁 / 误重定向）。
 */
const bootstrap = async () => {
  await useAuthStore.getState().bootstrap()
  const auth = useAuthStore.getState()
  const routerStore = useRouterStore.getState()
  // 已登录但路由数据丢失（内存与持久化皆空）→ 会话不完整，本地置为非登录态，
  // 交由既有守卫（root→/login、protectedLoader→/login）回退登录页，而非用 MENU_MANIFEST 重建。
  if (auth.loggedIn && routerStore.asyncRouteData.length === 0) {
    useAuthStore.setState({ loggedIn: false })
  }

  // useRouterStore.getState().registerAsyncRoutes();

  // 找到 DOM 中的 #root 容器并创建根，非 null 断言由 index.html 保证
  createRoot(document.getElementById('root')!).render(
    // React 18 StrictMode 在开发模式下的「双倍 effect 执行（挂载 → 卸载 → 再挂载）」，用于暴露副作用清理问题
    <StrictMode>
      <ThemeProvider>
        <App/>
      </ThemeProvider>
    </StrictMode>,
  )
}

void bootstrap()
