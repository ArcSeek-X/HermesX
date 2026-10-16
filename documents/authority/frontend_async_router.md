# <a id="frontend-async-router"></a>前端异步数据路由方案

> 📝 **方案简述**：本方案确立 `apps/hrs-web` 前端路由层的实现基准——以 React Router v7 数据路由（`createBrowserRouter` + `RouterProvider`）为底座，路由真源 `MENU_MANIFEST` 经 `RouterStore` 加工为 `asyncRouteData` 持久化、登录后通过 `patchRoutes('business')` 动态注入受保护布局；鉴权收敛为单一 `protectedLoader` 守卫，页面经路由级 `lazy` 自动代码分割。本方案**已落地**，本文档描述当前实现状态（非规划）。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-16

## 目录

- [一、背景与定位](#sec-1)
- [二、总体架构](#sec-2)
- [三、路由真源与加工链路](#sec-3)
- [四、动态注入与注入时机](#sec-4)
- [五、鉴权守卫](#sec-5)
- [六、页面懒加载与页头元数据](#sec-6)
- [七、使用规范](#sec-7)
- [八、关键文件职责](#sec-8)
- [九、已知限制与注意](#sec-9)

---

<a id="sec-1"></a>

## 一、背景与定位

**规定**：前端路由层采用 React Router v7 数据路由，路由配置、鉴权守卫、代码分割统一收敛到数据路由机制，废弃早期"声明式 `<Routes>` + 组件内命令式鉴权"混写的模式。

**Why**：早期声明式 `<Routes>` 下，`ShellHeader` 读取页头标题/描述需用 `useMatches()` + `handle`，但 `useMatches` 仅在数据路由中可用——曾因误用在声明式路由下抛 `Uncaught Error: useMatches must be used within a data router` 导致页头白屏。此外鉴权逻辑混写在组件体内，难复用、难测试。数据路由原生支持 `handle`/`useMatches`、`loader` 守卫、路由级 `lazy`，正好闭环这些痛点。

**How to apply**：任何新增页面/路由改动都走 `MENU_MANIFEST` 真源 + 动态注入路径，不回退到手写 `<Route>` 声明；跨路由的页头元数据一律经 `handle` + `useMatches` 读取。可与 [前端模块化菜单与动态路由状态方案](frontend_module_menu.md) 配套阅读。

---

<a id="sec-2"></a>

## 二、总体架构

路由实例在 `router/appRouter.tsx` 以 `createBrowserRouter` 创建（`appRouter.tsx:56-104`），实际结构如下：

```
createBrowserRouter([
  { HydrateFallback, children: [
      { index: true, loader: () => redirect('/login') },                         // 根：统一落地登录页
      { path:'/login', element:<LoginPage/>, handle:{...}, errorElement },        // 顶层，恒可达，脱离 Shell
      { id:'protected', element:<Shell/>, loader:protectedLoader, errorElement, children: [
          { path:'404', loader:()=>null, element:<NotFoundPage/> },               // 兜底固定在 Shell 内
          { id:'business', children: initialBusinessRoutes },                     // 动态业务路由容器（刷新种子）
      ]},
      { path:'*', loader:({request}) => guardAuthRedirect(request) ?? redirect('/404') }, // 顶层收口
  ]},
])
```

要点：

- **登录页 `/login`** 在 `protected` 之外、顶层独立可达，渲染时脱离 `Shell`；其 `handle` 携带 `auth.login.title` / `auth.login.description` 静态元数据。
- **受保护布局 `protected`** 为 pathless 父路由（`id:'protected'`），`element:<Shell/>` 提供布局，`protectedLoader` 做鉴权守卫，`errorElement` 兜底；其 `<Outlet/>` 渲染业务子路由。
- **业务路由挂在 pathless 容器 `id:'business'` 下**（而非直接挂 `protected.children`），与 `404` 兜底分离——登录后 `patchRoutes('business', ...)` 整体替换业务路由时不会冲掉固定在 Shell 内的 `404`。
- **`*` 顶层兜底**统一收口未匹配路径：未登录跳 `/login`、已登录跳 `/404`（单跳，消除"先 /404 再 /login"的两段跳转）。

---

<a id="sec-3"></a>

## 三、路由真源与加工链路

```
MENU_MANIFEST (router/manifest.ts)              ← 唯一真源（ModuleNode[]，第一层为模块，children 为 AppRouteNode）
      │ 登录后 RouterStore.buildAsyncRouterData()
      ▼
RouterStore.asyncRouteData (AsyncRouteNode[])   ← 运行时权威源，持久化 localStorage('router.asyncRouterData')
      │ 路由注册层消费
      ▼
asyncRouteFactory.buildAsyncRoutes(nodes) → RouteObject[]   （page→{path,handle,lazy}，redirect→{path,loader}）
      │ routeRegistration.registerAsyncRoutes → patchRoutes('business', ...)
      ▼
router (createBrowserRouter) → Shell 的 <Outlet/> 渲染
```

- **真源** `MENU_MANIFEST`：以菜单字段为基线叠加路由/鉴权字段（`RouteMenuType = 'page'|'group'|'redirect'|'fallback'`、`auth?: 'public'|'protected'`、`menuPagePath?`），页面不在此声明 `loader`，页面解析由 `menuPagePath` + 动态导入完成（见 §6）。真源结构详见 [前端模块化菜单与动态路由状态方案](frontend_module_menu.md)。
- **加工** `RouterStore.buildAsyncRouterData()`：递归 `buildAsyncRouteTree` 仅保留 `page/redirect/fallback` 节点（`group` 仅透传 children），映射为 `AsyncRouteNode`（字段见 `types/router.ts`：`routerKey=menuId`、`routerName=menuName`、`routerPagePath=menuPagePath`、`routerType=menuType`…），构建后落盘。
- **还原**：store 初始化时由 `readStoredAsyncRouterData()` 从 localStorage 还原（场景二：刷新浏览器），无需手动调用。

---

<a id="sec-4"></a>

## 四、动态注入与注入时机

业务路由的注入由 `router/routeRegistration.ts` 承担，与 `appRouter` 解耦以避免循环依赖。

| 动作 | 实现 | 触发时机 |
| --- | --- | --- |
| 登录后注入 | `registerAsyncRoutes()`：`patchRoutes('business', [...buildAsyncRoutes(asyncRouteData)])` | 登录成功、刷新（已登录）时 |
| 登出清空 | `uninstallAsyncRoutes()`：`patchRoutes('business', [])` | 登出 |
| 防重复注入 | `addRouteFlag`：已注入则跳过，避免每次导航都 `patchRoutes` 触发 `protected` 重渲染 | 注入后置 false，登录重建数据时重置为 true |

**【强制】** `appRouter` 创建路由时**必须**把 `initialBusinessRoutes = buildAsyncRoutes(useRouterStore.getState().asyncRouteData)` 作为 `business` 容器的初始 `children` 写入（即"种子路由"），而非仅运行时 `patchRoutes`（`appRouter.tsx:40-43`）。否则刷新时首屏匹配早于注入，会把已登录业务地址（如 `/home`）误判为未匹配而落到 `*` 兜底跳 `/404`。

**【强制】** `routeRegistration` 不反向静态依赖 `appRouter`：`router` 实例由 `appRouter` 在 `createBrowserRouter` 之后通过 `attachRouter(router)` 回注，`routeRegistration` 经 `routerRef` 调用 `patchRoutes`，打破 `appRouter → login → routeRegistration → appRouter` 的环。

---

<a id="sec-5"></a>

## 五、鉴权守卫

**规定**：鉴权收敛为单一守卫 `protectedLoader`，所有受保护路由经此校验；未登录且开启鉴权即 `throw redirect('/login?redirect=<来源路径>')`。

实际实现抽出一个共享 helper `guardAuthRedirect(request)`（`appRouter.tsx:27-34`），被两处 loader 复用：

- `protectedLoader`（受保护布局守卫）；
- 顶层 `*` 兜底 loader：先 `guardAuthRedirect`，未命中（已登录/未开鉴权）则 `redirect('/404')`。

（`404` 兜底在 `protected` 内，loader 返回 `null`，已受 `protectedLoader` 保护。）

守卫读取 `useAuthStore.getState()`（`authEnabled` / `loggedIn`）——因 loader 运行在 React 之外，无法用 `useAuth()` Hook，故 auth 状态须可经 store 的 `getState()` 同步读取。`useAuth` 即 `useAuthStore` 的重导出（`hooks/useAuth.ts`）。

---

<a id="sec-6"></a>

## 六、页面懒加载与页头元数据

- **路由级 `lazy` 自动分割**：`buildAsyncRoutes` 对 page 节点产出 `lazy: () => resolvePageImporter(routerPagePath)!().then(m => ({ Component: m.default }))`（`asyncRouteFactory.ts:66-70`）。`resolvePageImporter` 经 `import.meta.glob('../pages/**/*.tsx')` 在构建期静态收集页面模块，按 `../${pagePath}.tsx` 解析，Vite 据此自动代码分割；加载失败由路由级 `errorElement` 兜底。
- **页头元数据**：每个 page 节点挂 `handle: { routerName, routerDescription }`，`ShellHeader` 经 `useMatches()` 读取渲染页头标题/描述，闭环早期白屏问题。

**【强制】** 所有 `menuPagePath` 目标页面模块**必须默认导出**组件（`m.default`），否则 `.then(m => ({ Component: m.default }))` 取到 `undefined` 导致渲染异常（Phase 0 前置校验：确认所有 `menuPagePath` 目标为默认导出）。

---

<a id="sec-7"></a>

## 七、使用规范

**【强制】** 新增业务页面：在 `MENU_MANIFEST` 增节点（`menuPagePath` 指向 `pages/...`、`menuType:'page'`），无需手写路由；业务路由由 `buildAsyncRoutes` 自动生成并经 `business` 容器注入，**禁止**在 `appRouter` 内直接增删业务 `Route` 项。

**【推荐】** 静态/白名单路由（`/`、`/login`、`404`、`*`）直接在 `appRouter.tsx` 声明（原 `Whitelist.ts` 抽象已移除，不再单独维护白名单文件）；它们不进入 `RouterStore`、不参与持久化。

**【强制】** 修改 `appRouter` 的资源寻址或 `business` 容器结构时，须保留 §4 的"种子路由"机制与 `attachRouter` 解耦，禁止把 `patchRoutes` 调用写回 `appRouter` 静态依赖链。

**【推荐】** `protectedLoader` 与 `*` 兜底的鉴权逻辑统一走 `guardAuthRedirect`，新增需要鉴权的兜底路由时复用该 helper，不要各写一份 `redirect`。

---

<a id="sec-8"></a>

## 八、关键文件职责

| 文件 | 职责 |
| --- | --- |
| `router/appRouter.tsx` | 创建 `createBrowserRouter`；定义 `/`、`/login`、受保护布局 `protected`、业务容器 `business`、`404`、`*`；`guardAuthRedirect` 共享守卫；`attachRouter` 回注实例 |
| `router/asyncRouteFactory.ts` | `import.meta.glob` 收集页面 + `resolvePageImporter`；`buildAsyncRoutes(nodes)` 产出 `RouteObject[]`（page→lazy/handle，redirect→loader） |
| `router/routeRegistration.ts` | `registerAsyncRoutes` / `uninstallAsyncRoutes`（消费 `asyncRouteData` + `addRouteFlag`）；经 `attachRouter` 的 `routerRef` 调 `patchRoutes('business')` |
| `stores/RouterStore.ts` | 真源加工：`buildAsyncRouterData` 构建并持久化 `asyncRouteData`（`router.asyncRouterData`）；初始化时还原 |
| `stores/AuthStore.ts` | 鉴权状态（`authEnabled` / `loggedIn` / `bootstrap` / `login` / `logout`），`getState()` 供 loader 同步读取 |
| `hooks/useAuth.ts` | `useAuthStore` 的 re-export，业务组件统一入口 |
| `types/router.ts` | `AsyncRouteNode`、`RouteHandle` 类型契约 |
| `router/manifest.ts` | 路由/菜单唯一真源 `MENU_MANIFEST` |

---

<a id="sec-9"></a>

## 九、已知限制与注意

- **bootstrap 阻塞首屏**：`AuthStore.bootstrap()` 在渲染前拉取鉴权状态（一次网络往返），内部工具可接受；`main.tsx` 仍保留此阻塞式初始化（已确认采用，不启用根 loader 备选方案）。
- **`*` 兜底与 `404` 协同**：未登录访问任意未匹配路径→`*` 直接 `/login`（单跳）；已登录→`/404`（在 Shell 内）。新增兜底路由需注意这一优先级。
- **真源仍是本地文件**：`MENU_MANIFEST` 为本地常量，后续切接口真源时仅替换读取入口，路由加工/注册链路不变（见 [前端模块化菜单与动态路由状态方案](frontend_module_menu.md) §十三）。
- **与 Keep-Alive 的关系**：路由层与缓存层正交，缓存方案见 [前端路由缓存（Keep-Alive）架构设计](frontend_route_keepalive.md)。
