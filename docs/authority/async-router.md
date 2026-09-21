# 动态路由与数据路由迁移方案（async-router）

> **文档类型**：规划与执行方案 v2（已定稿 · 待实施，尚未改动业务代码）
> **创作者**：Lensgcx (GaoCangxiong)
> **创建日期**：2026-09-20
> **适用范围**：`apps/hrs-web` 前端路由层（声明式 `<Routes>` → 数据路由 `RouterProvider`）
> **关联文件**：`router/manifest.ts`、`stores/RouterStore.ts`、`router/Whitelist.ts`、`router/pageImporter.ts`、`App.tsx`、`AppContent.tsx`、`contexts/AuthContext.tsx`、`pages/LoginPage/LoginCard.tsx`、`components/layout/ShellHeader.tsx`

---

## 目录

1. [背景](#1-背景)
2. [设计目标与决策](#2-设计目标与决策)
3. [总体架构规划](#3-总体架构规划)
4. [实现路径（分阶段）](#4-实现路径分阶段)
5. [作用路径（导航流转）](#5-作用路径导航流转)
6. [数据链路（路由来源与落地）](#6-数据链路路由来源与落地)
7. [路由功能说明](#7-路由功能说明)
8. [涉及文件与核心代码](#8-涉及文件与核心代码)
9. [风险与缓解](#9-风险与缓解)
10. [收益](#10-收益)
11. [测试影响](#11-测试影响)
12. [评审要点与待确认项](#12-评审要点与待确认项)

---

## 1. 背景

当前 `apps/hrs-web` 的路由采用 **React Router 声明式 API**（`BrowserRouter` + `<Routes>` + `<Route>` 元素），路由渲染与鉴权拦截混写在 `AppContent.tsx` 中。该架构存在两个问题：

1. **`useMatches` / `handle` 不可用**：声明式 `<Routes>` 下没有任何 hook 能读取 `<Route handle={...}>`。此前为给 `ShellHeader` 取"当前页标题/描述"而引入的 `useMatches()`，在运行期直接抛 `Uncaught Error: useMatches must be used within a data router`，导致页头组件白屏崩溃。临时方案已回退为 `useLocation` + `matchPath` 查 `MENU_MANIFEST`（见 `ShellHeader.tsx`）。
2. **命令式路由与鉴权耦合**：`AppContent` 在组件体内用 `useAuth()` 判断 `isLoading/loadError/loggedIn`，再手动 `<Navigate>` 或独立渲染登录页，逻辑分散、难以复用、难以测试。

**数据路由（`createBrowserRouter` + `RouterProvider`）** 能原生支持 `handle`/`useMatches`、路由级 `loader`（鉴权守卫）、路由级 `lazy`（自动代码分割 + `errorElement`），正好解决上述痛点，且与 `ChatPage.test.tsx` 已在使用的 `createMemoryRouter` 测试范式一致。

> 注意：本方案保留现有"路由即数据驱动"的设计——业务路由来自 `MENU_MANIFEST`，登录后构建并持久化为 `asyncRouterData`，刷新时还原。`asyncRouterData` 缺失（未登录/被清）即视为"无业务路由"。

---

## 2. 设计目标与决策

### 2.1 设计目标

- 让 `ShellHeader` 能用 `useMatches()` + `handle` 读取当前路由元数据（闭环崩溃问题）。
- 鉴权拦截收敛为**单一守卫 loader**，删除 `AppContent` 混写的命令式逻辑。
- 业务路由保留"登录后动态注入 / 持久化还原"语义，不改 `RouterStore` 的权威源定位。
- 路由级 `lazy` 自动代码分割，移除手写的 `React.lazy` + `lazyPageCache`。

### 2.2 已确认决策（评审通过的三项）

| 决策点 | 选项 | 说明 |
|---|---|---|
| **D1 鉴权拦截位置** | **方案②**：auth 状态迁入 Zustand `AuthStore`，由 `loader` 抛 `redirect()` | loader 运行在 React 之外，无法用 `useAuth()`（Context），故 auth 必须可经 `getState()` 读取。保留 `useAuth()` 钩子名（改读 store），业务组件零改动。 |
| **D2 业务路由是否仍"登录后动态注入"** | **方案②**：保留 `asyncRouterData` 持久化 + `router.patchRoutes('protected', ...)` 注入，登出清空 | 忠实现有语义："持久化即路由权威源，未登录/清空则无业务路由"。保留 `RouterStore`。 |
| **D3 懒加载策略** | **方案②**：路由级 `lazy`（`() => import().then(m => ({ Component: m.default }))`）+ `handle` | 更地道，自动代码分割 + 配 `errorElement` 兜底加载失败。 |

### 2.3 被否决的备选

- **D1 方案①（组件级守卫 `<RequireAuth>`）**：改动小但无法用 `useMatches` 之外的 loader 能力，且仍把鉴权写在组件里。否决。
- **D2 方案A（静态全量生成路由）**：最简单，但放弃了"持久化缺失即无路由"的语义，与既有 `RouterStore` 设计冲突。否决。

### 2.4 本轮补充确认（用户决议）

1. **登出清空路由（D2② 落地）**：登出时显式 `clearBusinessRoutes()`（`patchRoutes('protected', [])`）清空业务路由，与 `asyncRouterData` 持久化清空一并生效。
2. **测试暂缓**：测试与单测不在实施阶段逐 Phase 执行，统一在**所有功能确认开发完毕**后再补充。
3. **`handle` 字段**：采用 `{ routerName, routerDescription }`，复用 `AsyncRouteNode` 原生字段，不新增 manifest 字段。
4. **轻量 `RouteErrorBoundary`**：先行新增一个读取 `useRouteError()` 的轻量边界组件，作为 `protected` 的 `errorElement`；后续再评估合并/调整。

---

## 3. 总体架构规划

### 3.1 Before / After

```
【Before】声明式 + 命令式鉴权
UiLanguage > AppMode > BrowserRouter > AuthProvider > PageStateProvider > AppContent
   AppContent 内部:
     <Routes>
       <Route element={<Shell><RouteOutletBoundary/></Shell>}>
         {WHITE_LIST_ROUTE...} {dynamicRoutes...} {EXCEPTION_ROUTE...}   // 来自 asyncRouterData
       </Route>
     </Routes>
   + 命令式鉴权: if (authEnabled && !loggedIn) return <Navigate to="/login?redirect=..."/>

【After】数据路由 + loader 守卫
UiLanguage > AppMode > PageStateProvider > RouterProvider(router)
   router = createBrowserRouter([
     { path:'/login', lazy: LoginPage, errorElement: <StandaloneRouteBoundary/> },   // 顶层，恒可达
     { path:'/',      loader: () => redirect('/login') },                           // 根重定向（顶层静态）
     { id:'protected', element:<Shell/>, loader: protectedLoader,
       errorElement:<RouteErrorBoundary/>, children: [] },                          // 初始空，patchRoutes 注入
   ])
```

- `AuthProvider` 移除；`PageStateProvider` 上移到 `RouterProvider` 之上作祖先（context 向下穿透路由元素）。
- `AppContent.tsx` 退役，其职责被"路由配置 + loader + `Shell`"吸收。
- `protectedLoader` 在每次访问受保护路由时同步读取 `AuthStore.getState()`，未登录即 `throw redirect('/login?redirect=...')`。

### 3.2 新增模块职责划分

| 新模块 | 职责 |
|---|---|
| `stores/AuthStore.ts` | Zustand 鉴权状态（替代 `AuthContext`），含 `bootstrap/login/logout/changePassword`；`useAuth()` 改读此 store。 |
| `router/routeConfig.ts` | 纯函数 `buildProtectedRoutes(nodes): RouteObject[]`，复用现有 flatten + 映射，产出 `lazy` / `redirect` / `handle`。 |
| `router/appRouter.ts` | `export const router = createBrowserRouter([...])` + `protectedLoader` + `registerBusinessRoutes()` / `clearBusinessRoutes()`。 |
| `router/routeRegistry.ts` | 隔离 `patchRoutes` 调用，避免 `AuthStore` ↔ `appRouter` 循环依赖。 |

---

## 4. 实现路径（分阶段）

- **Phase 0（不接 RouterProvider）**：抽 `buildProtectedRoutes(nodes)` 纯函数，单测验证映射（path / lazy / redirect / handle）正确。**前置校验**：确认所有 `menuPagePath` 目标模块**默认导出**组件。
- **Phase 1（AuthStore）**：新建 `AuthStore`，把 `AuthContext` 的状态与动作搬入；`useAuth` 改读 store（返回结构不变）；删除 `contexts/AuthContext.tsx`；同步改造所有 `useAuth` mock 测试（见 §11）。
- **Phase 2（路由配置）**：新建 `routeConfig.ts`（`buildProtectedRoutes`）+ `appRouter.ts`（router + `protectedLoader` + 注册/清空辅助）。
- **Phase 3（接入）**：改 `App.tsx` / `main.tsx`——`main.tsx` 渲染前 `await useAuthStore.getState().bootstrap()` 并完成首屏 `registerBusinessRoutes()`；`App.tsx` 用 `RouterProvider` 替换 `BrowserRouter`；删除 `AppContent.tsx`。
- **Phase 4（登录/登出联动）**：`LoginCard` 登录成功后调 `registerBusinessRoutes()` 再 `navigate(redirect)`；`UserSetting` 登出成功后调 `clearBusinessRoutes()`。
- **Phase 5（元数据闭环）**：恢复 `ShellHeader` 的 `handle` + `useMatches()`；删除 `getLazyPage` / `LoginLazyPage` 及 `React.lazy` 缓存。
- **Phase 6（测试，暂缓）**：测试与单测统一在**所有功能确认开发完毕**后补充，不在实施阶段逐 Phase 执行；届时跑 `ChatPage.test.tsx`（已用 `RouterProvider`）并补路由级测试（未登录重定向、404、登录后路由可见、登出清空）。

---

## 5. 作用路径（导航流转）

| 场景 | 流转 |
|---|---|
| **首次进入（未登录 + 鉴权开启）** | `main.tsx` `bootstrap()` 拉取状态 → `loggedIn=false` → 访问任意路径命中 `protectedLoader` → `throw redirect('/login?redirect=<当前路径>')` → 渲染 `/login`。 |
| **登录成功** | `LoginCard.handleSubmit`：`login(password)` → `buildMenuData()` + `buildAsyncRouterData()`（持久化 `asyncRouterData`）→ `registerBusinessRoutes()`（`patchRoutes('protected', ...)`）→ `navigate(redirect, {replace})` → 命中业务路由渲染。 |
| **已登录刷新** | 模块加载：`RouterStore` 从 localStorage 还原 `asyncRouterData`；`main.tsx` `bootstrap()` 后 `registerBusinessRoutes()` 还原业务路由 → 首屏即可命中。 |
| **未登录 / 登录态失效（刷新）** | 登录 cookie 已清 → `bootstrap()` 得 `loggedIn=false` → `asyncRouterData` 为空 → `registerBusinessRoutes()` 注入空 → 访问任意业务路径被 `protectedLoader` 重定向到 `/login`。 |
| **已登录但路由持久化被清（刷新）** | 仅 `router.asyncRouterData` 被清、登录 cookie 仍在（`loggedIn=true`）→ `main.tsx` `bootstrap()` 检出「已登录但路由数据空」→ 本地 `setState({ loggedIn: false })`（不调服务端）将残缺会话置为非登录态 → 既有守卫（`root→/login`、`protectedLoader→/login`）直接回退到 `/login`，而非用 `MENU_MANIFEST` 重建；重新登录后由 `LoginCard` 从 `MENU_MANIFEST` 重建动态路由。 |
| **登出** | `UserSetting` → `AuthStore.logout()`（刷新状态为未登录）→ `clearBusinessRoutes()`（`patchRoutes('protected', [])`）→ `navigate('/login')`。 |
| **直接访问受保护路径（已登录）** | `protectedLoader` 放行 → 匹配 `children` 中的业务路由 → `Shell` 的 `<Outlet/>` 渲染页面。 |
| **访问不存在路径（已登录）** | 命中 `protected` 下的 `*` → `NotFoundPage`（在壳内显示）。 |

---

## 6. 数据链路（路由来源与落地）

```
                        ┌─────────────────────────────────────────┐
                        │  MENU_MANIFEST  (router/manifest.ts)     │  ← 唯一真源（含 menuPagePath / routePath / menuName / menuDescription）
                        └─────────────────────────────────────────┘
                                          │ 登录后
                                          ▼
                        ┌─────────────────────────────────────────┐
                        │  RouterStore.buildAsyncRouteTree()       │  buildAsyncRouterData()
                        │  AppRouteNode → AsyncRouteNode（树）      │
                        └─────────────────────────────────────────┘
                                          │ 持久化（localStorage: router.asyncRouterData）
                                          ▼
                        ┌─────────────────────────────────────────┐
                        │  useRouterStore.asyncRouterData          │  ← 运行时权威源（刷新还原）
                        └─────────────────────────────────────────┘
                                          │ registerBusinessRoutes()
                                          ▼
                        ┌─────────────────────────────────────────┐
                        │  routeConfig.buildProtectedRoutes(nodes) │  → RouteObject[]
                        │    page  → { path, handle, lazy }        │
                        │    redirect → { path, loader: redirect } │
                        │    fallback → { path:'*', element }      │
                        └─────────────────────────────────────────┘
                                          │ router.patchRoutes('protected', ...)
                                          ▼
                        ┌─────────────────────────────────────────┐
                        │  router (createBrowserRouter)            │  → RouterProvider 渲染
                        └─────────────────────────────────────────┘

页面模块解析链路：
   menuPagePath ('pages/XxxPage') → pageImporter.resolvePageImporter() → import.meta.glob('../pages/**/*.tsx')
                                  → 路由级 lazy: () => importer().then(m => ({ Component: m.default }))

鉴权链路：
   main.tsx bootstrap() → authApi.getStatus() → AuthStore.{authEnabled,loggedIn,...}
   protectedLoader({request}) → useAuthStore.getState() → 未登录则 redirect('/login?redirect=...')
```

---

## 7. 路由功能说明

| 路由 / 能力 | 说明 |
|---|---|
| **根重定向 `/`** | 顶层静态 `loader: () => redirect('/login')`，与鉴权状态无关，保证任意入口都统一落地到登录页（已登录用户访问 `/` 也会正常进入登录页，尊重其主动跳转选择）。 |
| **登录路由 `/login`** | 顶层独立路由，**不在 `protected` 之下**，恒可达；路由级 `lazy` 加载 `LoginPage`，`errorElement` 用 `StandaloneRouteBoundary`。脱离 `Shell` 独立渲染。 |
| **受保护布局 `protected`** | 路径无关（pathless）父路由，`id:'protected'`，`element:<Shell/>`；`loader` 统一做鉴权守卫；`errorElement` 兜底 `lazy` 加载失败。其 `<Outlet/>` 渲染业务子路由。 |
| **业务动态路由** | 来自 `asyncRouterData`（由 `MENU_MANIFEST` 加工），经 `patchRoutes` 注入 `protected.children`；`handle:{ routerName, routerDescription }` 承载页头元数据，供 `ShellHeader` 经 `useMatches()` 读取。 |
| **404 兜底 `*` / `/404`** | 顶层平级兄弟路由（与 `protected` 平级），由 `Whitelist.EXCEPTION_ROUTE`（`RouteObject[]`）直接声明、`appRouter` 展开为顶层平级；`*` loader 自带鉴权判断：未登录且开启鉴权 → `/login?redirect=...`（鉴权优先级，单跳直达），已登录/未开鉴权 → `/404`。与业务路由解耦，消除未匹配路径先 `/404` 再 `/login` 的两段跳转；`NotFoundPage` 提供「重新登录」操作（`AuthStore.logout()` + `navigate('/login')`）以重建动态路由。 |
| **重定向型路由** | `menuType==='redirect'` 的节点（如根路径重定向），映射为 `{ path, loader: () => redirect(target) }`。 |
| **懒加载** | 路由级 `lazy`：`() => resolvePageImporter(pagePath)!().then(m => ({ Component: m.default }))`，Vite 自动按 `import.meta.glob` 产物做代码分割；加载失败由 `errorElement` 兜底。 |
| **错误处理** | 内容区渲染错误保留组件级 `RouteOutletBoundary`（包在 `Shell` 内包裹 `<Outlet/>`，报错不丢侧栏）；`lazy` 模块加载失败用 RR `errorElement`。两者分工，不互相替代。 |

---

## 8. 涉及文件与核心代码

### 8.1 现有代码（引用，作为数据链路真源）

**`router/manifest.ts`** — 路由唯一真源（节选结构）：
```ts
export type AppRouteNode = Omit<NavMenuNode, 'description'|'exact'|'children'> & {
  menuDescription: string;
  menuType: RouteMenuType;          // 'page' | 'group' | 'redirect' | 'fallback'
  auth?: RouteAuthPolicy;           // 'public' | 'protected'
  redirect?: string;
  menuPagePath?: string;            // 'pages/StockDashboardPage'
  children?: AppRouteNode[];
};
export const MENU_MANIFEST: ModuleNode[] = [ /* 按模块划分的菜单/页面树 */ ];
export const isPageLikeRouteNode = (n) => n.menuType === 'page' || n.menuType === 'redirect' || n.menuType === 'fallback';
```

**`stores/RouterStore.ts`** — 持久化权威源（节选）：
```ts
const ASYNC_ROUTER_STORAGE_KEY = 'router.asyncRouterData';
const buildAsyncRouteTree = (nodes): AsyncRouteNode[] =>
  nodes.flatMap((node) => {
    const children = node.children?.length ? buildAsyncRouteTree(node.children) : undefined;
    if (!isPageLikeRouteNode(node) || !node.routePath) return children ?? [];
    return [toAsyncRouteNode(node, children)];
  });
const readStoredAsyncRouterData = (): AsyncRouteNode[] => {
  const stored = getStorageItem<AsyncRouteNode[]>(ASYNC_ROUTER_STORAGE_KEY, 'local');
  return Array.isArray(stored)
    && stored.every((n) => n && typeof n.routerKey === 'string' && typeof n.routerPagePath === 'string')
    ? stored : [];
};
// 初始 state 在 store 初始化时由 localStorage 还原；buildAsyncRouterData() 登录后构建并落盘
```

**`router/Whitelist.ts`** — 白名单/异常路由（节选）：
```ts
export const WHITE_LIST_ROUTE: AsyncRouteNode[] = [
  { routerKey:'root-redirect', routerPath:'/', routerType:'redirect', redirect:'/home', auth:'protected' },
  { routerKey:'login', routerPath:'/login', routerType:'page', auth:'public', routerPagePath:'pages/LoginPage/LoginPage' },
];
export const EXCEPTION_ROUTE: AsyncRouteNode[] = [
  { routerKey:'not-found', routerPath:'*', routerType:'fallback', auth:'protected', routerPagePath:'pages/NotFoundPage' },
];
```

**`router/pageImporter.ts`** — 页面模块懒加载解析：
```ts
const pageModules = import.meta.glob('../pages/**/*.tsx');
export const resolvePageImporter = (pagePath?: string) => {
  if (!pagePath) return undefined;
  return (pageModules[`../${pagePath}.tsx`] as RouteLoader | undefined);
};
```

### 8.2 目标代码（拟实现，待评审）

**`router/routeConfig.ts`**：
```ts
import type { RouteObject } from 'react-router-dom';
import type { AsyncRouteNode } from '../types/router';
import { resolvePageImporter } from './pageImporter';

export const buildProtectedRoutes = (nodes: AsyncRouteNode[]): RouteObject[] => {
  const flatten = (ns: AsyncRouteNode[]): AsyncRouteNode[] =>
    ns.flatMap((n) => [ ...(n.routerPath ? [n] : []), ...(n.children ? flatten(n.children) : []) ]);
  return flatten(nodes).map((n) => ({
    path: n.routerPath,
    handle: { routerName: n.routerName, routerDescription: n.routerDescription },   // 页头元数据真源（复用 AsyncRouteNode 原生字段）
    ...(n.routerType === 'redirect'
      ? { loader: () => redirect(n.redirect!) }
      : { lazy: () => resolvePageImporter(n.routerPagePath)!()
            .then((m) => ({ Component: (m as { default: ComponentType }).default })) }),
  }));
};
```

**`router/Whitelist.ts`**（异常兜底路由：直接以 RouteObject[] 书写，外部展开为顶层平级）：
```ts
import { createElement } from 'react';
import type { RouteObject } from 'react-router-dom';
import { redirect } from 'react-router-dom';
import { useAuthStore } from '../stores/AuthStore';
import NotFoundPage from '../pages/NotFoundPage';

export const EXCEPTION_ROUTE: RouteObject[] = [
  {
    path: '404',
    loader: ({ request }) => {
      const { authEnabled, loggedIn } = useAuthStore.getState();
      if (authEnabled && !loggedIn) {
        const u = new URL(request.url);
        throw redirect(`/login?redirect=${encodeURIComponent(u.pathname + u.search)}`);
      }
      return null;
    },
    element: createElement(NotFoundPage),
  },
  {
    path: '*',
    loader: ({ request }) => {
      const { authEnabled, loggedIn } = useAuthStore.getState();
      const u = new URL(request.url);
      if (authEnabled && !loggedIn) return redirect(`/login?redirect=${encodeURIComponent(u.pathname + u.search)}`);
      return redirect('/404');
    },
  },
];
```

**`router/appRouter.tsx`**（节选：直接展开 `...EXCEPTION_ROUTE` 为顶层平级兄弟路由）：
```ts
import { createBrowserRouter, redirect, type LoaderFunctionArgs } from 'react-router-dom';
import { useAuthStore } from '../stores/AuthStore';
import { useRouterStore } from '../stores/RouterStore';
import { WHITE_LIST_ROUTE, EXCEPTION_ROUTE } from './Whitelist';
import { resolvePageImporter } from './pageImporter';
import { buildProtectedRoutes } from './routeConfig';
import { Shell } from '../components';
import { RouteErrorBoundary } from '../components/layout/RouteBoundary';
import NotFoundPage from '../pages/NotFoundPage';

const protectedLoader = ({ request }: LoaderFunctionArgs) => {
  const { authEnabled, loggedIn } = useAuthStore.getState();
  if (authEnabled && !loggedIn) {
    const u = new URL(request.url);
    throw redirect(`/login?redirect=${encodeURIComponent(u.pathname + u.search)}`);
  }
  return null;
};

export const router = createBrowserRouter([
  { path: '/', loader: () => redirect('/login'), errorElement: <RouteErrorBoundary /> },
  { path: '/login', lazy: () => resolvePageImporter('pages/LoginPage/LoginPage')!().then((m) => ({ Component: m.default })),
    errorElement: <RouteErrorBoundary /> },
  { id: 'protected', element: <Shell/>, loader: protectedLoader, errorElement: <NotFoundPage/>, children: [] },
  // 异常兜底：顶层平级，直接来自 Whitelist.EXCEPTION_ROUTE（与 protected 解耦，单跳直达）
  ...EXCEPTION_ROUTE,
]);

export const registerBusinessRoutes = () => {
  const data = useRouterStore.getState().asyncRouterData;
  router.patchRoutes('protected', [...buildProtectedRoutes(data)]);  // 仅业务路由，异常兜底已在顶层
};
export const clearBusinessRoutes = () => router.patchRoutes('protected', []);
```

**`stores/AuthStore.ts`**（草图，替代 `AuthContext`）：
```ts
export const useAuthStore = create<AuthState>((set) => ({
  authEnabled:false, loggedIn:false, isLoading:true, loadError:null,
  passwordSet:false, passwordChangeable:false, setupState:'no_password',
  bootstrap: async () => { /* authApi.getStatus，同原 fetchStatus，含登出重置 dashboard */ },
  login: async (pw) => { await authApi.login(pw); await get().bootstrap(); return { success:true }; },
  logout: async () => { try { await authApi.logout(); } finally { await get().bootstrap(); } },
  changePassword: ..., refreshStatus: ...,
}));
// hooks/useAuth.ts 改为: export { useAuthStore as useAuth } 或 const useAuth = () => useAuthStore();
```

**`main.tsx`**（草图）：
```ts
// 渲染前完成鉴权 bootstrap + 首屏路由注入（避免首屏 404）
await useAuthStore.getState().bootstrap();
registerBusinessRoutes();
createRoot(...).render(<StrictMode><ThemeProvider><App/></ThemeProvider></StrictMode>);
```

**`ShellHeader.tsx`**（恢复 `useMatches`，闭环崩溃）：
```ts
const matches = useMatches();
const handle = matches[matches.length - 1]?.handle as { routerName?: string; routerDescription?: string } | undefined;
const current = handle ? { title: handle.routerName ?? '', description: handle.routerDescription } : undefined;
```

### 8.3 文件变更清单

| 文件 | 动作 |
|---|---|
| `stores/AuthStore.ts` | 新增（替代 `AuthContext`） |
| `hooks/useAuth.ts` | 改（`useAuth` 改读 `AuthStore`，结构不变） |
| `contexts/AuthContext.tsx` | 删除 |
| `router/routeConfig.ts` | 新增（`buildProtectedRoutes`） |
| `router/appRouter.ts` | 新增（router + loader + 注册/清空） |
| `router/routeRegistry.ts` | 新增（隔离 `patchRoutes`，避免循环依赖） |
| `App.tsx` | 改（`AuthProvider` 移除，`RouterProvider` 替换 `BrowserRouter`） |
| `main.tsx` | 改（bootstrap + 首屏 `registerBusinessRoutes`） |
| `AppContent.tsx` | 删除（职责被路由配置 + loader 吸收） |
| `pages/LoginPage/LoginCard.tsx` | 改（登录后 `registerBusinessRoutes()` 再 `navigate`） |
| `components/layout/HeaderComponents/UserSetting.tsx` | 改（登出后 `clearBusinessRoutes()`） |
| `components/layout/ShellHeader.tsx` | 改（恢复 `handle` + `useMatches`） |
| `router/pageImporter.ts` | 保留（供路由级 `lazy` 使用） |

<!-- PART2_ANCHOR -->

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| **bootstrap 阻塞首屏（已接受）**：`main.tsx` 渲染前 `await` 鉴权请求（一次网络往返）。 | 内部量化工具可接受，作为已确认方案；根 loader 备选不采用。 |
| **patchRoutes 时序**：刷新首屏必须在 `RouterProvider` 挂载前注入业务路由，否则短暂 404。 | 当前方案在 `main.tsx` 同步 `registerBusinessRoutes()` 后再渲染，安全。 |
| **循环依赖**：`AuthStore.logout` 想调 `clearBusinessRoutes` 会反向依赖 `appRouter`。 | 用 `router/routeRegistry.ts` 隔离 `patchRoutes` 调用，打破环。 |
| **默认导出假设**：若存在非默认导出的页面模块，`.then(m => ({Component:m.default}))` 需针对性调整。 | Phase 0 前置校验所有 `menuPagePath` 目标是否默认导出组件。 |
| **loader 抛 redirect 副作用**：未登录访问任意受保护路径都被重定向到 `/login?redirect=...`。 | 与现行为一致，属预期；`redirect` 参数保留来源路径，登录后可回跳。 |
| **测试 mock 改造量（暂缓）**：约 8 个测试文件当前 mock `useAuth`/`AuthContext`，本轮决议测试统一在收尾阶段处理。 | 收尾阶段统一改为 `useAuthStore.setState(...)`；`AuthContext.test.tsx` 重写为 `AuthStore` 测试。 |

---

## 10. 收益

- **闭环崩溃问题**：`handle` + `useMatches` 终于可用，`ShellHeader` 页头标题/描述回归"同源"读取，彻底解决 `useMatches must be used within a data router` 白屏。
- **鉴权收敛**：单一 `protectedLoader` 守卫，删除 `AppContent` 混写的命令式鉴权逻辑，结构更清晰、可测。
- **代码分割自动化**：路由级 `lazy` 自动分割 + `errorElement` 兜底，移除手写 `lazyPageCache` / `getLazyPage` / `LoginLazyPage`。
- **范式统一**：与 `ChatPage.test.tsx` 已用的 `createMemoryRouter` 测试范式一致，便于后续接 `loader` 数据预取、`<Form>` action 等数据路由能力。

---

## 11. 测试影响

> ⏸ **本轮决议：测试暂缓**。测试与单测统一在**所有功能确认开发完毕**后补充，不在实施阶段逐 Phase 执行。以下为届时需改造/新增的测试清单，仅作规划存档。

以下测试当前 mock `useAuth` / `AuthContext`，迁移后需改为 `useAuthStore.setState(...)`（或对应 mock store）：

- `App.test.tsx`、`AuthContext.test.tsx`（整文件重写为 `AuthStore` 测试）
- `pages/__tests__/LoginPage.test.tsx`、`pages/__tests__/SettingsPage.test.tsx`
- `components/layout/__tests__/SidebarNav.test.tsx`、`RouteBoundary.test.tsx`、`Shell.test.tsx`
- `pages/__tests__/ChatPage.test.tsx`（已用 `RouterProvider`，主要同步 route config 形态）

建议新增路由级测试覆盖：

1. **未登录重定向**：以 `createMemoryRouter` 构造含 `protected` 守卫的路由，访问 `/home` 应重定向到 `/login`。
2. **404 兜底**：登录态访问不存在路径应渲染 `NotFoundPage`（壳内）。
3. **登录后路由可见**：调用 `registerBusinessRoutes()` 后，`/stock-dashboard` 等能匹配并渲染。
4. **登出清空**：`clearBusinessRoutes()` 后业务路径不再匹配（依赖 loader 重定向）。

---

## 12. 评审要点与待确认项

以下评审要点已全部确认（均采用文档默认方案），可按 Phase 0–6 实施（**当前未改动任何业务代码**）：

1. ✅ **`main.tsx` 阻塞式 bootstrap（已确认采用②）**：保留 `await bootstrap()` 后再 `render` 的默认方案；根 loader（`router.initialize()`）备选方案不实施（内部工具首屏延迟可忽略，且其 `patchRoutes` 时序更复杂）。
2. ✅ **登出清空路由（已确认）**：`UserSetting` 登出成功 → `clearBusinessRoutes()`（`patchRoutes('protected', [])`）清空业务路由；依赖 `router/routeRegistry.ts` 隔离避免循环依赖。
3. ✅ **测试暂缓（已确认）**：测试与单测统一在**所有功能确认开发完毕**后补充，不在实施阶段逐 Phase 执行；涉及约 8 个测试文件的 `useAuth` mock 迁移届时统一处理。
4. ✅ **`handle` 元数据字段（已确认）**：采用 `{ routerName, routerDescription }`，直接复用 `AsyncRouteNode` 原生字段（页头标题取 `routerName`、描述取 `routerDescription`），无需新增 manifest 字段。
5. ✅ **先新增轻量 `RouteErrorBoundary`（已确认）**：新增读取 `useRouteError()` 的轻量边界组件，作为 `protected` 的 `errorElement` 兜底 `lazy` 加载/渲染异常；后续再评估是否与 `StandaloneRouteBoundary`/`RouteOutletBoundary` 合并或调整。

---

> 文档状态：**规划版 v2（已定稿 · 待实施）**。v2 较 v1 的变更：① 登出清空路由（D2②）落地确认；② 测试暂缓至功能确认后统一补充；③ `handle` 字段定为 `{ routerName, routerDescription }`；④ 先行新增轻量 `RouteErrorBoundary`；⑤ 四.2 修订（已登录但路由持久化被清时先落 NotFound 再点重新登录）；⑥ 评审要点 #1 确认采用阻塞式 bootstrap（②），根 loader 备选不实施。所有评审要点已确认，可按 Phase 0–6 进入实施；实施中若文档与代码现实不符将同步修订。
