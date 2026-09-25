# 长期记忆（MEMORY.md）

## 用户偏好
- 注释精简：删「已移除/已移到」类过程产物与冗余说明，保留 why 与简短步骤；中文注释做概述，英文 docstring 原样保留。
- 避免过度封装：无独立状态/复用的简单 UI 直接内联到使用页，不塞 `components/`。

## 项目约定（hrs-web）
- 类型检查：`npx tsc -p tsconfig.app.json --noEmit`（根 tsconfig 是 solution 风格不校验）。
- i18n：新增 key 需 zh/zh-Hant/en 三语同时补齐，`UiTextKey` 由 `uiText-zh.ts` 推导（唯一真源）；命名按业务域分层。规范见 `.conventions/frontend/I18N_NAMING.md`（V1.9：八大类别、三语主字典文件为数据真源、三语同序）。
- CSS 变量分层：主题/语义 token 与 `--nav-*` 唯一来源 `src/style/palette.css`；`--spacing` 是 Tailwind v4 默认变量不可覆盖；`.module.scss` 自带值须作用域内或 `var(--x, 兜底)`。
- HeroUI Pro 覆盖：未分层 CSS 同特异性恒赢，冲突属性加 v4 后缀 `!`；`text-md` 有效勿删。
- HeroUI 组件样式：不走 portal，原地渲染；样式为语义类名（`modal__backdrop` 等，定义在 `@heroui/styles` 的 `heroui.min.css`，非 Tailwind utilities）。二次封装替换内部层须手动带对应 slot 类，否则弹层不可见。
- 仅大小写重命名坑（macOS 不敏感 FS）：如 `layoutStore.ts`→`LayoutStore.ts` 用 shell heredoc 重写并 `wc -c` 校验，勿混 `rm`。
- 端口：后端 Uvicorn :8000；前端 Vite :1022（`LOCAL_RUN_GUIDE` 的 5173 过时），`/api`→127.0.0.1:8000。Node 需 ≥20.19（当前 v22.23.1，`engines` 上限 <27，满足；记忆里"需 v20"仅为宽松说法）。
- **本地启动**：后端用项目根 `.venv`（Python 3.11.15，基于 homebrew `python@3.11`）跑 `.venv/bin/python main.py --serve-only`（监听 8000，贴合 `LOCAL_RUN_GUIDE`；非交互 shell 中 `PYENV_ROOT` 常未导出，直接用 `.venv/bin/python`，不必走 pyenv）；前端 `cd apps/hrs-web && npm run dev`（Vite :1022，`/api`→127.0.0.1:8000）。
  - ⚠️ **vite 缺失坑**：`main.py --serve-only` 启动时会自动 `npm ci` 重装前端依赖，但常装不全 → `node_modules/.bin/vite` 缺失，前端 `npm run dev` 报 `vite: command not found`。**遇此先在 `apps/hrs-web` 用 nvm node v22（`/Users/gaocangxiong/.nvm/versions/node/v22.23.1/bin`）显式 `npm install` 补齐依赖，再启动 Vite**（验证：安装后 `FE=200`）。
  - 常驻方式：本环境 `nohup <cmd> > log 2>&1 &` 可稳定常驻（SIGHUP 已隔离、进程 reparent 到 init），无需依赖工具 watch 模式；普通裸 `&` 无 nohup 可能在会话结束时被回收。
- 类型收口：跨模块共享类型放 `src/types/`；`utils/` 是叶子层，禁止反向 import stores 类型。
- 隐藏滚动条：用 `.scrollbar-none`（`global.scss` `@layer utilities`），只视觉隐藏。
- Tailwind v4.1 层顺序：`global.scss` 须在 `index.css` 的 `@import "tailwindcss"` 之后；自定义 utility 用 `@layer utilities`。

## 前端路由架构（数据路由 / data router，2026-09-20 实施，2026-09-21 解耦异常路由）
- React Router **数据路由**（`createBrowserRouter` + `RouterProvider`）；原声明式 `<Routes>`（`AppContent.tsx`）与 `AuthContext` 已删除。
- 鉴权唯一真源：`src/stores/AuthStore.ts`（Zustand）；`bootstrap()/login/logout` 在此，`main.tsx` **阻塞式** await 后 `render`（首屏前鉴权态就绪）。
- 路由拓扑（`src/router/appRouter.tsx` 顶层平级数组）：
  - `/` → 仅 `index` loader 重定向 `/login`（2026-09-21 起 `AppRoot`/`routeElements.tsx` 已删除，`RouteSync` 迁入 `Shell`，`currentRoute` 才能真实反映业务页位置）。
  - `/login` → 独立路由（无守卫，尊重主动进入）；2026-09-21 起改为**静态导入 `LoginPage` 直渲（`element: <LoginPage/>`），去掉路由级 `lazy`**——避免未登录用户首屏 `/`→`/login` 重定向时的额外异步 chunk 拉取。
  - `protected`（pathless）→ `Shell` + `protectedLoader`（未登录且开启鉴权→`/login`）+ `errorElement:<NotFoundPage/>`；children **初始从 `RouterStore.asyncRouteData` 同步种子写入 `createBrowserRouter` 配置**（`...initialBusinessRoutes`），运行时 `registerAsyncRoutes` 以 `patchRoutes` 整体替换更新。种子化是关键：刷新时初始匹配即可命中业务路由，否则会误落 `*` 兜底跳 /404。
  - **`404` 与 `*` 为顶层平级兄弟路由（2026-09-21 起不再挂在 `protected` 下）**：`404` 用 `protectedLoader` 守卫；`*` loader **自带鉴权判断**——未登录且开启鉴权→`/login?redirect=...`，否则→`/404`。单跳直达，消除「先 /404 再 /login」两段跳转。
- 动态路由注入逻辑已**集中到 `src/stores/RouterStore.ts`**：`registerAsyncRoutes()` / `uninstallAsyncRoutes()` 两个 store 方法，内部 `router.patchRoutes('protected', ...)`；`routeRegistry.tsx` 已删除（2026-09-21 迁入）。`registerAsyncRoutes` 仅把 `buildAsyncRoutes(asyncRouteData)` patch 进 `protected.children`（**不含异常路由**），幂等靠 `addRouteFlag`（登录重建时 `buildAsyncRouterData` 重置为 true，注入后置 false）。调用点：**登录成功 `LoginCard.tsx`**（顺带 `buildAsyncRouterData()` 用当前 `MENU_MANIFEST` 重建）、**登出 `UserSetting.tsx`**（`uninstallAsyncRoutes`+`navigate('/login')`）。⚠️ **`main.tsx` bootstrap 里的 `registerAsyncRoutes()` 调用已被注释掉（有意留空：登录前不重建路由）**，故刷新时仅依赖 localStorage 还原的 `asyncRouteData` 种子，bootstrap 不重建。
- ⚠️ 循环依赖：`RouterStore` 现 import `router`（来自 `appRouter`）与 `buildAsyncRoutes`（来自 `asyncRouteFactory`），与 `appRouter`（import `useRouterStore`）形成良性环状依赖；`router` 仅在方法运行时引用，模块加载阶段不触碰，无 TDZ。
- `src/router/asyncRouteFactory.ts`：`buildAsyncRoutes` 扁平化 `AsyncRouteNode`→`RouteObject[]`，page 走路由级 lazy，`handle:{routerName,routerDescription}` 供 `ShellHeader` 经 `useMatches()`` 读。`pageImporter.ts` 已于 2026-09-21 合并进本文件（`RouteLoader` 类型 / `pageModules` = `import.meta.glob('../pages/**/*.tsx')` / `resolvePageImporter` 现同文件导出），旧 `pageImporter.ts` 已删。
- `src/router/Whitelist.ts`：`WHITE_LIST_ROUTE`/`WHITE_LIST_ROUTE_MANIFEST` 为 `AsyncRouteNode[]`（白名单页与根重定向）；`EXCEPTION_ROUTE` 在 Whitelist.ts 中**当前整体被注释（dead）**，`appRouter.tsx` 直接内联书写顶层 `404` + `*` 兜底路由（非经 `...EXCEPTION_ROUTE` 展开）。`buildExceptionRoutes` 已删除。⚠️ Whitelist.ts 顶部因 EXCEPTION_ROUTE 被注释而残留 5 个未使用导入（`createElement`/`redirect`/`useAuthStore`/`NotFoundPage`/`Shell`），已于 2026-09-21 清理（属预存 broken build 的一部分）。
- ⚠️ 匹配语义：`protected` 是 pathless 布局，其 loader/element **仅当有子路由命中时才执行**；业务路由经 patch 注入。`*` 现为顶层（静态存在），未匹配 URL 由顶层 `*` 收口，不触发 `protectedLoader`（业务鉴权靠 `protectedLoader`，坏地址鉴权靠 `*` loader）。
- ⚠️ 初始化匹配：`createBrowserRouter` 模块加载时即对当前 URL 初始匹配（早于 `RouterProvider` 挂载）。因 `protected.children` 已用 `initialBusinessRoutes` 种子化（取还原的 `asyncRouteData`），初始匹配即含业务路由；`registerAsyncRoutes`（登录 / 刷新 bootstrap）再以 `patchRoutes` 整体替换更新（幂等，靠 `addRouteFlag`）。**切勿把业务路由仅留运行时 patchRoutes 注入**——那会让刷新初始匹配早于注入、把已登录业务地址误判未匹配跳 /404。
- 错误处理分工：`RouteErrorBoundary`（`RouteBoundary.tsx`，读 `useRouteError`）作 `protected`/`login` 的 `errorElement`；`RouteOutletBoundary` 包 `<Outlet/>` 处理页面渲染错误。两层分工。
- ⚠️ `protected` 的 `errorElement` 与顶层 `*`/`404` 不可删，否则未匹配路径落到 RR 内置默认错误页。
- ⚠️ 业务路由仅登录后构建并持久化（`RouterStore.asyncRouteData`，模块加载时从 localStorage 还原）；已登录但路由数据被清 → `main.tsx` bootstrap 检出后本地 `setState({loggedIn:false})` 回退 `/login`（不调服务端）。鉴权关闭（ADMIN_AUTH_ENABLED=false）时无入口构建路由，属已知缺口。
- ⚠️ **加/改路由必重登录坑**：`asyncRouteData` 是 localStorage 持久化的「快照」，只在登录时由 `buildAsyncRouterData()` 从 `MENU_MANIFEST` 重建。`main.tsx` bootstrap 的 `registerAsyncRoutes()` 已注释，刷新不重建。因此往 `MENU_MANIFEST` 新增路由后，若只刷新（已登录会话），运行时路由表仍是旧快照 → 该路径不匹配 → 顶层 `*` 兜底跳 `/404`。**让新路由生效的做法**：退出重登 / 清 `router.asyncRouteData` localStorage 后刷新 / DevTools 跑 `useRouterStore.getState().buildAsyncRouterData()` + `registerAsyncRoutes()`。开发期若想"改 manifest 刷新即用"，应在 `main.tsx` bootstrap 里先 `buildAsyncRouterData()` 再 `registerAsyncRoutes()`（尚未接，属待办）。
- `AsyncRouteNode`（`src/types/router.ts`）字段：`routerKey/routerName?/routerPath/routerPagePath/routerType/auth?/redirect?/routerDescription/children?`；持久化还原要求 `routerPagePath` 为 string。
- 测试暂缓：删除 `App.test.tsx`/`AuthContext.test.tsx`；`SidebarNav/RouteBoundary/Shell` 三测试 `vi.mock` 已指向 `AuthStore`；统一后再补路由级测试（未登录重定向、404、登录后可见、登出清空）。

## 侧边导航（SideBar）
- 菜单数据源 `MenuStore`（`src/stores/MenuStore.ts`）：模块制（`ModuleMenuData = { [moduleId]: NavMenuNode[] }`），由 `buildRuntimeMenuData()` 从 `MENU_MANIFEST` 实时构建；`SidebarNavNew`（自研轻量，纯 React+Tailwind，读 `useLayoutStore.menuCollapsedState` 三态）消费 `useMenuStore((s)=>s.currentMenuData)`。**`router/manifest` 为菜单真源**；旧 `SideBar/menudata.ts` 仅剩 `PRODUCT_MENU_ITEMS`/`DEBUG_MENU_ITEMS` 供 Docs 演示页。
  - 持久化键 `hrs-pref-menu.menuData`（`MENU_DATA_STORAGE_KEY='menu.menuData'`）与 `hrs-pref-menu.currentModuleId`，走 `utils/storage`。
  - `buildMenuData(loginModuleId?)` 是 menuData 唯一写入点（`applyMenuState` 中 `init=true` 才写）；已接到 `LoginCard.tsx` 登录成功分支（在 `navigate(redirect)` 之前）。`readStoredMenuData()` 缺失即返回空对象 → 未登录菜单为空。
  - `setCurrentModuleId` 只改并持久化 `currentModuleId`，不重写 menuData。
  - `menuIcon` 为图标名字符串（`NavMenuNode.menuIcon?: string`），渲染经 `router/menuIcons.ts` 的 `menuIconRegistry` 解析回 lucide 组件；图标可随节点 JSON 序列化落盘，刷新不丢失。新增菜单项写字符串名即可。
- 头部运行模式切换 `ModeSwitch`：从 `AppModeContext.useAppMode` 迁到 `MenuStore`（读 `currentModuleId`，点击切 `setCurrentModuleId`）。`AppModeContext` 已无活跃消费方，待废弃。
- `SideBar` 文件夹：`MenuNode.tsx`（被 SidebarNavNew 复用）与 `menudata.ts` 必须保留；`SidebarNavV2`（HeroUI Pro 旧版）已无活跃渲染、已删除；`Shell copy.tsx` 为备份。

## 状态管理（三套并存）
1. Zustand（领域/复杂）：`src/stores/`，选择器订阅；`LayoutStore.ts` 侧栏折叠（PascalCase 文件名勿改）。
2. React Context（环境型）：`contexts/` + `components/theme/ThemeProvider`，带降级值。
3. 轻量偏好：`hooks/useCachedState`（localStorage 前缀 hrs-pref-/hrs-state-），跨子树共享才提升。
- 主题持久化已合并为单键（2026-09-19）：裸 `theme` 键退役；`NextThemesProvider` 设 `storageKey="hrs-pref-theme.themeMode"`，next-themes 以原始串读写；`themeStore.readStoredMode` 读原始串（不经 JSON.parse），`setThemeMode`/`themeReset` 不再写 mode 键（落盘交给 ThemeSync 订阅调 next-themes `setTheme`）；`themeColor`/`sidebarTheme` 仍由 store 经 `setStorageItem` 写。所有改主题处走 store，无组件绕过直调 setTheme。
  - ⚠️ 回归红线：mode 键绝不能用 `setStorageItem` 写、`readStoredMode` 绝不能用 `getStorageItem` 读（JSON.parse('dark') 抛错→永远回退 'system'）。
- 侧栏折叠态三态 `LayoutStore.menuCollapsedState`（offcanvas/collapsed/fully），键 `hrs-pref-layout.menuCollapsedState`。旧键 `layout.sidebarCollapsed` 已废弃。三态宽度 136/64/0。
  - ⚠️ `LayoutStore.ts` 勿退回布尔版（须含 `MenuCollapsedState`/`MENU_COLLAPSED_STORAGE_KEY`/`setMenuCollapsedState`/`toggleMenuCollapsedState`）。
  - 该项目 `write_to_file` 曾静默失效，编辑后务必 `grep`/`wc -l` 校验，必要时 shell heredoc 重写。
- ⚠️ 勿引入 Redux。

## 代码注释规范（强制）
文件头 `@file`+`@description`+`@author Lensgcx (GaoCangxiong)`+`@date`；方法注释覆盖"做什么"+`@param`+`@returns`；组件 props 标含义/默认值/必填。禁止复述代码/空话/注释掉的代码/过程产物。见 `.conventions/common/CODE_ANNOTATION.md`。
