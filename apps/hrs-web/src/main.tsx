/**
 * 应用入口文件（entry point）。
 *
 * 职责：
 * 1. 引入全局样式 index.css 与根组件 App。
 * 2. 用 createRoot 把 React 应用挂载到 index.html 中的 #root 节点。
 * 3. 在最外层包裹 <ThemeProvider>：提供主题（深色/浅色）上下文，控制全局配色。
 *
 * 注意：此处**有意不包裹 <StrictMode>**。路由缓存（keepalive-for-react /
 * keepalive-for-react-router，见 components/layout/KeepAliveOutlet.tsx）官方明确要求
 * 开发模式下不能使用 StrictMode——双倍挂载会导致其缓存行为不可预期。
 * 代价是失去开发期双倍渲染自检；副作用清理改由缓存失活语义
 * （useKeepAliveContext().active）与单测覆盖兜底。
 * 如将来弃用该库或其官方支持 StrictMode，可恢复包裹。
 */
import { initScrollLockCompensation } from '@utils/scrollLockCompensation';
import { createRoot } from 'react-dom/client';
import { ThemeProvider } from '@components/theme/ThemeProvider';
import { useAuthStore } from './stores/AuthStore';
import { useRouterStore } from './stores/RouterStore';
import './style/index.css'
import App from './App.tsx'

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
    // 有意不包裹 StrictMode：路由缓存库（keepalive-for-react）在开发模式下与其不兼容，详见文件头注释
    <ThemeProvider>
      <App/>
    </ThemeProvider>,
  )
}

void bootstrap()
