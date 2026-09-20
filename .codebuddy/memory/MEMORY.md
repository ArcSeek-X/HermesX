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
- 端口：后端 Uvicorn :8000；前端 Vite :1022（`LOCAL_RUN_GUIDE` 的 5173 过时），`/api`→127.0.0.1:8000，需 Node v20。
- 类型收口：跨模块共享类型放 `src/types/`；`utils/` 是叶子层，禁止反向 import stores 类型。
- 隐藏滚动条：用 `.scrollbar-none`（`global.scss` `@layer utilities`），只视觉隐藏。
- Tailwind v4.1 层顺序：`global.scss` 须在 `index.css` 的 `@import "tailwindcss"` 之后；自定义 utility 用 `@layer utilities`。

## 前端路由架构（data-driven）
- 路由全数据驱动：单一渲染函数 `buildRoute(key, path?, pagePath?, handle?, redirect?)`（`AppContent.tsx`）；`renderDynamicRoute` 同时服务业务/白名单/异常路由。
- `AsyncRouteNode`（`src/types/router.ts`）是唯一节点类型，字段 `routerKey/routerName?/routerPath/routerPagePath/routerType/auth?/redirect?/routerDescription/children?`。
- 业务树 `MENU_MANIFEST`（`AppRouteNode`）经 `RouterStore.toAsyncRouteNode` 映射为 `AsyncRouteNode`（`menuName→routerName`、`menuDescription→routerDescription`），登录后 `buildAsyncRouterData()` 构建并持久化到 `localStorage['router.asyncRouterData']`。
- 白名单/异常路由在 `src/router/Whitelist.ts`（`WHITE_LIST_ROUTE`/`EXCEPTION_ROUTE`/`WHITE_LIST_ROUTE_MANIFEST`，类型 `AsyncRouteNode[]`）；`routerName`/`routerDescription` 是 i18n key（root-redirect→`exception.redirect.*`、not-found→`exception.404.*`、login→`auth.login.*`）。
- ⚠️ 路由标题/描述来源：页头/路由 `handle.menuName` = `routerName`（i18n key）经 `t()` 解析；**`routeMeta.ts` 已移除，不再存在**，由 `asyncRouterData` + `AsyncRouteNode` 原生字段 + `t()` 替代。`layout.appFallbackTitle`（应用回退标题）仍被 `ShellHeader.tsx` 使用，勿删。
- ⚠️ 业务路由仅登录后构建并持久化；未登录时 `asyncRouterData` 为空 → 直访 /home 落入 `*` 兜底渲染 NotFoundPage（非服务端 404）。鉴权关闭（ADMIN_AUTH_ENABLED=false）时无入口构建路由，属已知设计缺口。
- 已删除 `manifestPagePathByKey` 回查（页面路径内联为 `routerPagePath`，无需回查）；持久化还原要求 `routerPagePath` 为 string，缺字段旧 blob 视为无效丢弃。

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
