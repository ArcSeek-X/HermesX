# 长期记忆（MEMORY.md）

## 用户偏好
- **注释风格**：偏好精简。删除「修改过程产物」类注释（如"已移除 XX""已移到 XX 文件"）与和代码自明/彼此重复的冗余说明；保留有价值的 why（设计取舍、踩坑原因）与简短步骤标记（如 `// 1) 收集...`）。中英文混合项目中，中文注释做概述级补充，原有英文 docstring 原样保留。
- **避免过度封装（组件粒度）**：只是用基础组件拼几个图标/文案/角标、无独立状态与复用场景的简单 UI，直接在使用它的页面内联实现，不要单独塞进 `components/`。例：消息日历「筛选按钮」原封装为 `LiveCalendarFilterButton`，用户要求撤掉，改为页面内 `HrsButton` + lucide 图标 + `cn` 渲染。

## 项目约定（hrs-web）
- **类型检查必须用 `npx tsc -p tsconfig.app.json --noEmit`**：根 `tsconfig.json` 是 solution 风格（`files:[]` + `references`），`tsc -p tsconfig.json` 什么都不校验。仓库有大量存量错误（@testing-library/react 缺 screen/fireEvent、HrsButton forwardRef、Pagination `xs`、PasswordInput `prefixNode` 等），校验自己改动按文件名过滤。
- **全局跨子树状态放 `contexts/` 并挂到 `App.tsx`**：Provider 一律提供降级值（`useContext(...) ?? fallback`），保证单测不包 Provider 也能渲染。
- **动画库**：用 `motion`（v12，framer-motion 新版），统一 `import { motion } from 'motion/react'`（不是 `framer-motion`）。首屏不播动画用 `initial={false}`。无共享过渡预设，各组件内联 `transition={{ duration, ease }}`。
- **抽屉组件**：新代码统一用 `components/basic/Drawer.tsx`（HrsDrawer，HeroUI 底座）；`components/common/Drawer.tsx` 为旧版，勿用。
- **i18n 命名空间**：日历文案为 `component.LiveCalendar.*`（非 `liveCalendar.*`）；新增 key 需 zh / zh-Hant / en 三语同时补齐（`UiTextKey` 由 uiText-zh.ts 推导）。
- **日期时间格式化**：一律复用 `utils/format.ts` 的 `formatDate`/`formatDateTime`/`formatTime`（接受秒级时间戳，内部 ×1000）；需随 UI 语言本地化的用 `toIntlLocale(language)`（全站唯一 locale 映射），勿在各组件重复写 zh-CN/zh-TW/en-US 三元判断。
- **基础组件目录规范**：`components/basic/` 下统一「文件夹 + index.ts」结构：`<Name>/<Name>.tsx` 放实现，`<Name>/index.ts` 用 `export * from './<Name>'` 再导出（有默认导出的额外 `export { default } from './<Name>'`）。平铺 `basic/X.tsx` 迁移为文件夹时，内部相对 import 多一层目录（`../../utils/cn` → `../../../utils/cn`）。
- **组件文档页约定**：演示/文档页放 `apps/hrs-web/src/pages/DocsPage/Components/`，命名 `Docs_<组件名>.tsx`，路由 `/docs/component/<x>`，页面用 `<AppPage>` 包裹；新增需在 `docs/CHANGELOG.md` 的 `[Unreleased]` 顶部加 `- [文档] ...`。
- **CSS 变量分层（不可越界）**：主题/语义 token（`--primary`、`--foreground`、`--radius` 等）与导航令牌（`--nav-*`）唯一来源是 `src/style/palette.css`（`:root` 与 `.dark` 各一份），组件文件不要复制/重定义，否则主题切换失效并与共用方脱钩。`--spacing` 是 Tailwind v4 默认主题变量，不可在组件内覆盖。组件 `.module.scss` 若自带值只能：① 声明在自身 class 作用域内；或 ② 用 `var(--x, 兜底)` 给回退。
- **HeroUI Pro 样式覆盖**：Pro 的 CSS（`@heroui-pro/react/dist/css/index.css`）未分层，Tailwind v4 工具类在 `@layer utilities` 内——同特异性下未分层样式恒赢。覆盖 Pro 时凡 Pro 明确设了冲突值的属性必须加 v4 后缀 `!`（如 `flex-row! w-full! py-3! justify-start!`）。`text-md` 在本项目有效（勿误删）。
- **HeroUI 3.2.4 Modal 的 PressResponder 警告坑**：声明式 `HrsModal` 不用 `HeroUIModal.Backdrop`，改用 `react-aria-components/Modal` 的 `ModalOverlay` 直接包裹 `HeroUIModal.Container`（Container 是 forwardRef DOM div），否则触发 "A PressResponder was rendered without a pressable child"（功能不受影响，仅 console 噪音）。
- **仅大小写不同的重命名是坑（macOS 大小写不敏感 FS）**：如 `layoutStore.ts`→`LayoutStore.ts` 后 `write_to_file` 可能写入成功但内容未更新甚至变 0 字节，必须用 shell heredoc（`cat > file << 'EOF'`）重写；写后务必 `wc -c`/`grep` 校验。同条命令勿混 `rm`（会触发 safe-delete 拦截）。
- **前后端端口**：后端 FastAPI+Uvicorn 监听 `8000`（`python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000`，根目录，需先 `source .venv/bin/activate`），文档 `http://localhost:8000/docs`。前端 Vite **实际端口 `1022`**（非 5173，`LOCAL_RUN_GUIDE.md` 的 5173 已过时），`/api` 代理到 `127.0.0.1:8000`；启动需 Node v20。杀进程 `pkill -f uvicorn` / `pkill -f vite`。后台常驻启动必须 `nohup ... &`（子 shell 包裹）。

## 侧边导航（SideBar）
- **轻量自研侧栏 `SidebarNavNew`（2026-09-13 新增，`components/layout/SideBar/SidebarNav-new.tsx`）**：因 HeroUI Pro `Sidebar` 过重（RAC Tree + Context Provider + 多层 data-slot，DOM 约 8~10 层）自研；纯 React + Tailwind，零第三方 UI 依赖；DOM 扁平 `aside > nav > ul > li > (a|button)`。功能对齐 V2：两级菜单、运行模式切换、AlphaSift 过滤「选股」、路由高亮、三态折叠（读 `useLayoutStore.menuCollapsedState`，collapsed 为 64px 图标栏）、模式切换自动跳首个菜单；样式复用 v1 的 `--nav-*` 令牌。要点：① 展开态用「`userExpanded[id] ?? node.menuExpanded`」派生，不用 effect 同步；② 含子级一级行拆成「NavLink/button 主区 + 独立箭头 button」避免 button 嵌套 a；③ 支持 `menuMode='group'`。
- **V2（`SidebarNavV2.tsx`，基于 HeroUI Pro Sidebar）保留未删**（用户要求），同目录 `index.ts` 桶导出（`export * from './SidebarNavV2'` + `export { default }` + `export * from './menudata'`）；外部从 `components/layout/SideBar` 导入。菜单数据（PRODUCT/DEBUG_NAV_ITEMS）已拆到 `menudata.ts`（`NavItem` 类型来自 `../SidebarNav`）。V2 额外提供可选 `onNavigate?: () => void` 供移动端抽屉跳转后关闭。
- **两级菜单节点类型 `NavMenuNode`（定义在 `SideBar/menudata.ts`）**：一二级共用 `menuKey/menuName/routePath/menuIcon/children?/exact?`；`routePath` 有值才可跳转，一级为空串即纯分组；`menuName` 走 `t()`、直写文案原样显示（`t(k as UiTextKey) || k` 兜底）；`menuIcon` 类型 `ComponentType<{ className?: string }> | undefined`，无图标时**整个省略该字段**（写 `''`/`null` 触发 TS2322）。
- **切换侧栏实现**：改 Shell 的 import 与组件名即可（props 兼容 `className`/`onNavigate`/`menuMode`）。Shell 当前用 `SidebarNavNew`，未挂载移动端 Drawer。

## 状态管理（三套并存）
1. **Zustand（领域/复杂状态首选）**：`src/stores/`（复数）下 `agentChatStore`/`analysisStore`/`stockPoolStore`/`LayoutStore.ts`（侧栏折叠，**PascalCase 文件名是用户指定，勿改回**），均 `create from 'zustand'`，`index.ts` barrel 导出。组件用选择器订阅（`useLayoutStore((s) => s.xxx)`），action 单独取引用稳定。
2. **React Context（环境型）**：`contexts/` 下 `AppModeContext`/`AuthContext`/`UiLanguageContext` + `components/theme/ThemeProvider`，一律带降级值。
3. **轻量用户偏好（单组件内）**：用 `hooks/useCachedState`（useState + 自动持久化 localStorage，键前缀 `hrs-pref-`/`hrs-state-`），返回 `[value, setValue, reset]`；跨子树共享才提升为 Context/Zustand。
- **侧栏折叠态已从 `useCachedState` 布尔 `collapsed` 迁到 Zustand `LayoutStore.menuCollapsedState`**（三态 `'offcanvas'`默认/`'collapsed'`/`'fully'`，类型 `MenuCollapsedState`）；提供 `setMenuCollapsedState`/`toggleMenuCollapsedState`（offcanvas→collapsed→fully 循环）。持久化键 `layout.menuCollapsedState`，落盘写在 action 内不用 persist 中间件。三态宽度 **offcanvas=136px / collapsed=64px / fully=0**。V2 在 collapsed 下只渲染图标（读 `menuCollapsedState` 派生 `isCollapsedRail`，跳过 label/trigger/submenu），无障碍名靠 MenuItem `textValue`。HeroUI Pro 自带 `collapsible="icon"` 机制因 Provider 未受控 `isOpen` 恒 true 不生效，半折叠只显图标是手动实现。
- **⚠️ 勿引入 Redux**：2026-09-13 曾短暂引入后移除，改用 Zustand，避免并存两套状态库。
- **ShellHeader 属性已改 `menuCollapsedState: MenuCollapsedState`**（原 `collapsed: boolean`）；按钮图标三态 fully→`PanelLeftOpen`、collapsed→`ChevronsLeft`、offcanvas→`PanelLeftClose`；aria-label 复用 `layout.expandSidebar`/`layout.collapseSidebar`，未新增 i18n。

## 代码注释规范（仓库级强制）
规范文件 `.conventions/common/CODE_ANNOTATION.md`（融合阿里 Java 手册 / Google Style / TSDoc）。要点：① 文件头必含 `@file` + `@description`（作用 + 使用场景/被谁引用）+ `@author Lensgcx (GaoCangxiong)` + `@date yyyy-MM-dd`；② 方法注释覆盖"做什么" + 每个 `@param` 含义与边界 + `@returns`；③ 组件每个 props 标含义 + 默认值 + 是否必填；④ 常量/变量一句话说明业务含义。禁止：复述代码的注释、空话、注释掉的代码，以及"已移除 XX""已移到 XX 文件"类变更过程产物（发现即删）。执行时只动注释、不动代码逻辑与命名。
