# 长期记忆（MEMORY.md）

## 用户偏好
- **注释风格**：精简，删「已移除/已移到」类过程产物与冗余说明，保留 why 与简短步骤标记；中文注释做概述补充，英文 docstring 原样保留。
- **避免过度封装**：无独立状态/复用的简单 UI 直接内联到使用页，不单独塞 `components/`。

## 项目约定（hrs-web）
- **类型检查**：`npx tsc -p tsconfig.app.json --noEmit`（根 tsconfig 是 solution 风格不校验）。按文件名过滤自己改动。
- **i18n**：新增 key 需 zh/zh-Hant/en 三语同时补齐，`UiTextKey` 由 uiText-zh.ts 推导；命名按业务域分层（如 `theme.themeMode.*` / `theme.themeColor.*` / `theme.sidebarTheme.*`）。
- **CSS 变量分层**：主题/语义 token 与 `--nav-*` 唯一来源 `src/style/palette.css`，组件勿复制；`--spacing` 是 Tailwind v4 默认变量不可覆盖；`.module.scss` 自带值须作用域内或 `var(--x, 兜底)`。
- **HeroUI Pro 覆盖**：未分层 CSS 在同特异性恒赢，冲突属性必须加 v4 后缀 `!`。`text-md` 有效勿删。
- **仅大小写重命名坑（macOS 不敏感 FS）**：如 `layoutStore.ts`→`LayoutStore.ts` 改用 shell heredoc 重写并 `wc -c` 校验，勿混 `rm`。
- **端口**：后端 Uvicorn :8000；前端 Vite 实际 :1022（`LOCAL_RUN_GUIDE` 的 5173 过时），`/api`→127.0.0.1:8000，需 Node v20。
- **类型收口**：跨模块共享类型放 `src/types/`；`utils/` 是叶子层，禁止反向 import stores 类型（类型下沉到 types）。
- **隐藏滚动条**：用 `.scrollbar-none`（`global.scss` `@layer utilities`），只视觉隐藏，滚动容器 overflow 由调用方提供。
- **Tailwind v4.1 层顺序**：`global.scss` 须在 `index.css` 的 `@import "tailwindcss"` 之后；自定义 utility 用 `@layer utilities`（勿 `@utility`）。

## 侧边导航（SideBar）
- 页头/侧栏共享 `menudata.ts` 的 `ROUTE_META[pathname]`（ShellHeader 已删手写 TITLES）；新增菜单项自动出现在页头。`NavMenuNode.description` 现为「页面描述」文案（非菜单名副本）。
- `SidebarNavNew`（自研轻量，纯 React+Tailwind，读 `useLayoutStore.menuCollapsedState` 三态折叠）是当前 Shell 实现；V2（HeroUI Pro）保留未删。
- **侧栏视觉主题 `sidebarTheme`（pill/square）已落地**：驱动 `SidebarNavNew` 的 `theme` prop，类型下沉 `types/theme.ts`，状态在 `themeStore`（`Shell` 透传 prop，非 ThemeSync），`ThemeSetting` 弹层加「侧栏风格」TabNav+缩略预览。详见 `2026-09-16.md`。

## 状态管理（三套并存）
1. **Zustand（领域/复杂）**：`src/stores/`，组件用选择器订阅，action 引用稳定；`LayoutStore.ts` 侧栏折叠（PascalCase 文件名勿改）。
2. **React Context（环境型）**：`contexts/` + `components/theme/ThemeProvider`，带降级值。
3. **轻量偏好**：`hooks/useCachedState`（localStorage 前缀 hrs-pref-/hrs-state-），跨子树共享才提升。
- 侧栏折叠态已迁 `LayoutStore.menuCollapsedState`（offcanvas/collapsed/fully）。
- ⚠️ 勿引入 Redux。

## 代码注释规范（强制）
文件头 `@file`+`@description`+`@author Lensgcx (GaoCangxiong)`+`@date`；方法注释覆盖"做什么"+`@param`+`@returns`；组件 props 标含义/默认值/必填。禁止复述代码/空话/注释掉的代码/变更过程产物。规范见 `.conventions/common/CODE_ANNOTATION.md`。
