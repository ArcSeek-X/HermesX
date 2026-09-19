# 长期记忆（MEMORY.md）

## 用户偏好
- **注释风格**：精简，删「已移除/已移到」类过程产物与冗余说明，保留 why 与简短步骤标记；中文注释做概述补充，英文 docstring 原样保留。
- **避免过度封装**：无独立状态/复用的简单 UI 直接内联到使用页，不单独塞 `components/`。

## 项目约定（hrs-web）
- **类型检查**：`npx tsc -p tsconfig.app.json --noEmit`（根 tsconfig 是 solution 风格不校验）。按文件名过滤自己改动。
- **i18n**：新增 key 需 zh/zh-Hant/en 三语同时补齐，`UiTextKey` 由 uiText-zh.ts 推导；命名按业务域分层（如 `theme.themeMode.*` / `theme.themeColor.*` / `theme.sidebarTheme.*`）。
- **CSS 变量分层**：主题/语义 token 与 `--nav-*` 唯一来源 `src/style/palette.css`，组件勿复制；`--spacing` 是 Tailwind v4 默认变量不可覆盖；`.module.scss` 自带值须作用域内或 `var(--x, 兜底)`。
- **HeroUI Pro 覆盖**：未分层 CSS 在同特异性恒赢，冲突属性必须加 v4 后缀 `!`。`text-md` 有效勿删。
- **HeroUI 组件样式机制**：`@heroui/react` 组件**不走 portal**（原地渲染）；样式为语义类名（`modal__backdrop`/`modal__container` 等，定义在 `@heroui/styles` 的 `heroui.min.css`，非 Tailwind utilities，与 tailwind content 扫描无关）。二次封装时若替换内部层（如用 rac `ModalOverlay` 替代 `HeroUIModal.Backdrop`），必须手动带上对应 slot 类，否则无定位样式（弹层不可见）。
- **仅大小写重命名坑（macOS 不敏感 FS）**：如 `layoutStore.ts`→`LayoutStore.ts` 改用 shell heredoc 重写并 `wc -c` 校验，勿混 `rm`。
- **端口**：后端 Uvicorn :8000；前端 Vite 实际 :1022（`LOCAL_RUN_GUIDE` 的 5173 过时），`/api`→127.0.0.1:8000，需 Node v20。
- **类型收口**：跨模块共享类型放 `src/types/`；`utils/` 是叶子层，禁止反向 import stores 类型（类型下沉到 types）。
- **隐藏滚动条**：用 `.scrollbar-none`（`global.scss` `@layer utilities`），只视觉隐藏，滚动容器 overflow 由调用方提供。
- **Tailwind v4.1 层顺序**：`global.scss` 须在 `index.css` 的 `@import "tailwindcss"` 之后；自定义 utility 用 `@layer utilities`（勿 `@utility`）。

## 侧边导航（SideBar）
- 页头/侧栏共享 `menudata.ts` 的 `ROUTE_META[pathname]`（ShellHeader 已删手写 TITLES）；新增菜单项自动出现在页头。`NavMenuNode.description` 现为「页面描述」文案（非菜单名副本）。
- **菜单数据源 MenuStore（`src/stores/MenuStore.ts`，2026-09-18 已接线）**：菜单改**模块制**（`ModuleMenuData = { [moduleId]: NavMenuNode[] }`），由 `buildRuntimeMenuData()` 从 `router/manifest` 实时构建；`SidebarNav-new` 用 `useMenuStore((s) => s.currentMenuData)` 消费（**不再读旧 `SideBar/menudata.ts`**，该文件仅剩 PRODUCT_MENU_ITEMS/DEBUG_MENU_ITEMS 供 Docs_sideBar 演示页用）。页头 ROUTE_META 由 `router/routeMeta.ts` 派生（数据源 manifest.MENU_MANIFEST）；manifest.ts 仅存数据、不承载处理逻辑。
  - 持久化键 **`hrs-pref-menu.menuData`**（常量 `MENU_DATA_STORAGE_KEY='menu.menuData'`）与 **`hrs-pref-menu.currentModuleId`**，走 `utils/storage`（localStorage，`hrs-pref-` 前缀）。
  - **`buildMenuData(loginModuleId?)` 是 menuData 的唯一写入点**（`applyMenuState` 里 `init=true` 才写）；已于 2026-09-18 接到 **`LoginCard.tsx` 登录成功分支**（在 `navigate(redirect)` **之前**调用，省略参数则自动取第一个可用模块）。`stores/MenuStore.ts` 已按用户要求改为**存储严格权威**：此前 `readStoredMenuData()` 在存储缺失时回退 `buildRuntimeMenuData()`，现改为**缺失即返回空对象**（`({} as ModuleMenuData)`，`ModuleMenuData = Record<ModuleId, NavMenuNode[]>` 故需断言）→ 未登录时菜单为空。注意 `ModuleId = 'productModel' | 'developmentMode'` 是**字面量联合**，`getValidModuleId` 曾被人改成 `return ""` 导致编译错误（`""` 非法）并使 `getFirstAvailableModuleId` 成为死代码，已恢复为 `return getFirstAvailableModuleId(menuData)`。
  - `setCurrentModuleId(moduleId)` 只改并持久化 `currentModuleId`，**不重写 menuData**。
  - **`menuIcon` 现为图标名字符串（2026-09-18 改）**：`NavMenuNode.menuIcon?: string`，数据只存图标名（`'Home'` 等），渲染层经 `router/menuIcons.ts` 的 `menuIconRegistry`（`Record<string, ComponentType>`）把名字解析回 lucide 组件；未命中则空占位。因此图标可随节点一同 JSON 序列化落盘，**刷新后不再丢失**——此前"组件无法序列化、需 strip/apply 回填"的坑已彻底消除，`MenuStore` 已删除 `stripIconsInNodes`/`buildMenuIconMap`/`applyIconsInNodes`/`mapModuleNodes`/`MenuIconComponent` 整套逻辑。新增菜单项时 `menuIcon` 写字符串名即可，无需再 import 图标组件。
- **头部运行模式切换 `ModeSwitch`（`HeaderComponents/ModeSwitch.tsx`，2026-09-18 迁）**：已从 `AppModeContext` 的 `useAppMode`（`isDevelopmentMode`/`toggleMode`）迁到 `MenuStore`——读 `currentModuleId`、点击直接调 `setCurrentModuleId(currentModuleId === 'developmentMode' ? 'productModel' : 'developmentMode')` 切换模块。`AppModeContext` 现仅被 `App.tsx` Provider 与未渲染的旧 `SidebarNav`/`SidebarNavV2` 引用，已无活跃消费方，待废弃。
- `SidebarNavNew`（自研轻量，纯 React+Tailwind，读 `useLayoutStore.menuCollapsedState` 三态折叠）是当前 Shell 实现。
- **`SideBar` 文件夹活跃性（2026-09-18 核查）**：`MenuNode.tsx`（节点渲染，被 SidebarNavNew 复用）与 `menudata.ts`（仅剩 `PRODUCT_MENU_ITEMS`/`DEBUG_MENU_ITEMS` 供 `Docs_sideBar` 演示页用；`ROUTE_META` 已于 2026-09-18 迁至 `router/manifest`）**必须保留**；`SidebarNavV2.tsx` + `SidebarNavV2.module.scss`（HeroUI Pro 旧版）**已无活跃渲染**（仅备份 `Shell copy.tsx` 注释引用 + `SideBar/index.ts` 导出），已清理（2026-09-18 删除）；删后 Shell copy.tsx 的 V2 引用已注释，`SideBar/index.ts` 仅 `export * from './menudata'`；`SidebarNavV2` 仍 `useAppMode`，是 `AppModeContext` 残留引用方之一，清掉它仍不能立即删 `AppModeContext`（还有 `layout/SidebarNav.tsx` 旧版被 `Docs_sideBar` 引用）。
- **侧栏视觉主题 `sidebarTheme`（pill/square）已落地**：驱动 `SidebarNavNew` 的 `theme` prop，类型下沉 `types/theme.ts`，状态在 `themeStore`（`Shell` 透传 prop，非 ThemeSync），`ThemeSetting` 弹层加「侧栏风格」TabNav+缩略预览。详见 `2026-09-16.md`。

## 状态管理（三套并存）
1. **Zustand（领域/复杂）**：`src/stores/`，组件用选择器订阅，action 引用稳定；`LayoutStore.ts` 侧栏折叠（PascalCase 文件名勿改）。
2. **React Context（环境型）**：`contexts/` + `components/theme/ThemeProvider`，带降级值。
3. **轻量偏好**：`hooks/useCachedState`（localStorage 前缀 hrs-pref-/hrs-state-），跨子树共享才提升。
- **主题持久化已合并为单键（2026-09-19 落地，方案 A）**：原「应用键 `hrs-pref-theme.themeMode`（经 `setStorageItem` 存 JSON 引号串）」+「裸键 `theme`（next-themes 原始串）」双键已合并，**裸 `theme` 键退役**。`NextThemesProvider` 设 `storageKey="hrs-pref-theme.themeMode"`，next-themes 以**原始字符串**直接读写应用键；`themeStore.readStoredMode` 改为读**原始**串（不经 `getStorageItem` 的 JSON.parse），`setThemeMode`/`themeReset` 不再写 mode 键（落盘交给 `ThemeSync` 订阅 themeMode 变化调 next-themes `setTheme`）；`index.html` 内联首屏脚本改读 `hrs-pref-theme.themeMode` 并在 system/缺失时 `matchMedia` 跟随系统（顺带修掉首屏闪烁）。`readStoredMode` 直读应用键（原始串），**无旧裸 `theme` 迁移逻辑**（系统未上线，不需兼容历史数据）。`themeColor`/`sidebarTheme` 仍由 store 经 `setStorageItem` 写（与 next-themes 无关）。所有改主题处仍走 store（`ThemeToggle`/`ThemeSetting` → `setThemeMode`），**无组件绕过 store 直调 setTheme**。
  - ⚠️ **回归红线**：`utils/storage.setStorageItem` 会 `JSON.stringify` 存带引号串，而 next-themes/内联脚本写原始串——故 mode 键**绝不能用 `setStorageItem` 写**、`readStoredMode` **绝不能用 `getStorageItem` 读**（JSON.parse('dark') 抛错→永远回退 'system'）。必须保持 mode 键「原始串 + next-themes 独占写」的约定，否则两格式互相覆盖。
- 侧栏折叠态已迁 `LayoutStore.menuCollapsedState`（offcanvas/collapsed/fully），持久化键 `layout.menuCollapsedState`（实际 `hrs-pref-layout.menuCollapsedState`），落盘写在 action 内。**旧键 `layout.sidebarCollapsed`（hrs-pref-layout.sidebarCollapsed）已彻底废弃**：代码中已无任何读写（原仅 `Shell copy.tsx` 备份文件使用，已改为 `useState(false)`），浏览器里的残留值**不做运行时清理**（用户明确要求不加清理逻辑），自然失效即可。三态宽度 offcanvas=136 / collapsed=64 / fully=0。
  - ⚠️ `LayoutStore.ts` 曾在 2026-09-18 被回退成布尔版（`collapsed` + 键 `layout.sidebarCollapsed`），而 Shell/ShellHeader/SidebarNav-new/SidebarNavV2 都在消费三态 `menuCollapsedState`，导致运行时取到 undefined。已恢复三态版。**改动此文件时务必确认是三态版**（含 `MenuCollapsedState`、`MENU_COLLAPSED_STORAGE_KEY`、`setMenuCollapsedState`/`toggleMenuCollapsedState`），不要退回布尔版。
  - 另外该项目对本文件出现过 `write_to_file` 静默失效（报成功但内容未变/变 0 字节）的情况，编辑后务必 `grep`/`wc -l` 校验；必要时用 shell heredoc 重写。
- ⚠️ 勿引入 Redux。

## 代码注释规范（强制）
文件头 `@file`+`@description`+`@author Lensgcx (GaoCangxiong)`+`@date`；方法注释覆盖"做什么"+`@param`+`@returns`；组件 props 标含义/默认值/必填。禁止复述代码/空话/注释掉的代码/变更过程产物。规范见 `.conventions/common/CODE_ANNOTATION.md`。
