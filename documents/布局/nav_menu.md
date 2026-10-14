# <a id="侧边导航菜单sidebarnav设计方案"></a>侧边导航菜单（SidebarNav）设计方案

> 📝 **方案简述**：本方案设计 HermesX 侧边导航菜单 SidebarNav。它定义 NavMenuNode 节点模型与从清单到 Store 再到侧栏的数据流、持久化边界以及 content 与 footer 区域拆分，说明菜单与路由的关系，包括 matchPath 高亮判定、激活的双触发、模块切换自动跳转首个菜单、父级自动展开，实现三态折叠、滑行毛玻璃、按压反馈与兄弟让位四种交互，并给出主题令牌、CSS Module 封装策略、性能设计、文件清单与后续风险。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-13

## 方案目录

- [目录](#目录)
- [1. 背景与目标](#1-背景与目标)
- [2. 术语与缩略语](#2-术语与缩略语)
- [3. 整体架构](#3-整体架构)
  - [3.1 分层关系](#31-分层关系)
  - [3.2 组件职责划分](#32-组件职责划分)
- [4. 菜单数据结构与存储](#4-菜单数据结构与存储)
  - [4.1 节点模型 `NavMenuNode`](#41-节点模型-navmenunode)
  - [4.2 数据流：清单 → Store → 侧栏](#42-数据流清单-store-侧栏)
  - [4.3 持久化边界](#43-持久化边界)
  - [4.4 区域拆分（content / footer）](#44-区域拆分content-footer)
- [5. 与路由的关系](#5-与路由的关系)
  - [5.1 高亮判定 `matchPath`](#51-高亮判定-matchpath)
  - [5.2 激活的双触发（自身 / 子项）](#52-激活的双触发自身-子项)
  - [5.3 模块切换自动跳转首个菜单](#53-模块切换自动跳转首个菜单)
  - [5.4 父级自动展开（深链 / 刷新）](#54-父级自动展开深链-刷新)
- [6. 交互实现](#6-交互实现)
  - [6.1 三态折叠](#61-三态折叠)
  - [6.2 滑行毛玻璃（Sliding Thumb）](#62-滑行毛玻璃sliding-thumb)
  - [6.3 按压反馈（Press Feedback）](#63-按压反馈press-feedback)
  - [6.4 兄弟让位（Sibling Dim，`:has()`）](#64-兄弟让位sibling-dimhas)
- [7. 样式与主题](#7-样式与主题)
  - [7.1 主题令牌 `--nav-*`](#71-主题令牌-nav)
  - [7.2 CSS Module 封装策略](#72-css-module-封装策略)
  - [7.3 明暗主题](#73-明暗主题)
- [8. 性能设计](#8-性能设计)
- [9. 文件清单](#9-文件清单)
- [10. 风险与后续](#10-风险与后续)


| 项 | 内容 |
| --- | --- |
| **适用模块** | `apps/hrs-web/src/components/layout/SideBar/` |
| **文档状态** | 现行实现说明（含滑行玻璃 / 按压反馈 / 兄弟让位交互） |

---

## <a id="目录"></a>目录

- [1. 背景与目标](#1-背景与目标)
- [2. 术语与缩略语](#2-术语与缩略语)
- [3. 整体架构](#3-整体架构)
  - [3.1 分层关系](#31-分层关系)
  - [3.2 组件职责划分](#32-组件职责划分)
- [4. 菜单数据结构与存储](#4-菜单数据结构与存储)
  - [4.1 节点模型 `NavMenuNode`](#41-节点模型-navmenunode)
  - [4.2 数据流：清单 → Store → 侧栏](#42-数据流清单--store--侧栏)
  - [4.3 持久化边界](#43-持久化边界)
  - [4.4 区域拆分（content / footer）](#44-区域拆分content--footer)
- [5. 与路由的关系](#5-与路由的关系)
  - [5.1 高亮判定 `matchPath`](#51-高亮判定-matchpath)
  - [5.2 激活的双触发（自身 / 子项）](#52-激活的双触发自身--子项)
  - [5.3 模块切换自动跳转首个菜单](#53-模块切换自动跳转首个菜单)
  - [5.4 父级自动展开（深链 / 刷新）](#54-父级自动展开深链--刷新)
- [6. 交互实现](#6-交互实现)
  - [6.1 三态折叠](#61-三态折叠)
  - [6.2 滑行毛玻璃（Sliding Thumb）](#62-滑行毛玻璃sliding-thumb)
  - [6.3 按压反馈（Press Feedback）](#63-按压反馈press-feedback)
  - [6.4 兄弟让位（Sibling Dim，`:has()`）](#64-兄弟让位sibling-dimhas)
- [7. 样式与主题](#7-样式与主题)
  - [7.1 主题令牌 `--nav-*`](#71-主题令牌---nav-)
  - [7.2 CSS Module 封装策略](#72-css-module-封装策略)
  - [7.3 明暗主题](#73-明暗主题)
- [8. 性能设计](#8-性能设计)
- [9. 文件清单](#9-文件清单)
- [10. 风险与后续](#10-风险与后续)

---

## <a id="1-背景与目标"></a>1. 背景与目标

侧边导航（`SidebarNav`）是 HRS 桌面端布局的固定导航容器，承载「品牌区 + 主菜单（content）+ 底部菜单（footer）」。

设计目标：

1. **纯自研、零第三方 UI 依赖**：仅用 React + Tailwind + 主题 CSS 变量，与历史实现 `SidebarNav-old.tsx` 共用同一套视觉令牌。
2. **交互丝滑、性能友好**：参考 `scaffold-vue` 的三类交互（滑行毛玻璃、按压下陷、兄弟让位），在 React 下以「CSS transform + Framer Motion + 纯 CSS `:has()`」等价实现，避免逐帧主线程改布局。
3. **数据驱动、与路由解耦**：菜单树由路由清单 `MENU_MANIFEST` 经 `MenuStore` 派生，组件只消费 `currentMenuData`，不直接依赖路由文件。

> 参考来源：`scaffold-master-main/scaffold-vue` 的 `Sidebar.vue` / `composables/motion.ts` / `styles/layout.css` / `styles/materials.css`。技术栈不同（Vue → React），仅对齐**最终效果**。

---

## <a id="2-术语与缩略语"></a>2. 术语与缩略语

| 术语 | 含义 |
| --- | --- |
| `offcanvas` | 折叠态之一：正常展开（160px / 160px） |
| `collapsed` | 折叠态之一：半折叠图标栏（80px / 64px），仅显示图标 |
| `fully` | 折叠态之一：完全收起（0px，隐藏边框） |
| `menuMode` | 一级菜单展示模式：`collapse`（可折叠项）/ `group`（分区标题） |
| `theme` | 视觉主题：`pill`（大圆角）/ `square`（方角） |
| `active` | 当前路由命中的菜单项（含自身命中或子项命中） |
| `navThumb` | 唯一一块毛玻璃高亮块，绝对定位、靠 `transform` 在菜单项间滑行 |
| `matchPath` | 菜单路由是否命中当前路径的判定函数（单一真源） |

---

## <a id="3-整体架构"></a>3. 整体架构

### <a id="31-分层关系"></a>3.1 分层关系

```
Shell 布局层（useLayoutStore 提供 menuCollapsedState）
        │  props: menuCollapsedState, theme, menuMode, onNavigate
        ▼
┌─────────────────────────── SidebarNav.tsx ───────────────────────────┐
│  · 从 MenuStore 取 currentMenuData                                     │
│  · AlphaSift 过滤「选股」 + 按 menuPosition 拆 content / footer         │
│  · 维护展开态 userExpanded、isExpanded（含父级自动展开）                  │
│  · 滑行玻璃定位（syncThumb）+ 滚动 / Resize 同步                        │
│  · 渲染品牌区 + 菜单区（含唯一 .navThumb）+ footer                      │
│        │  props: node, level, collapsedState, menuMode, isExpanded...   │
│        ▼
│  ┌──────────────────── MenuNode.tsx ────────────────────┐             │
│  │ · 路由高亮 matchPath + active 双触发                    │             │
│  │ · 四种形态：图标栏 / 分组标题 / 可折叠 / 叶子           │             │
│  │ · 按压反馈（motion whileTap）+ data-active 钩子         │             │
│  │ · 含子级时递归渲染一层 <ul>（group / collapse 两种渲染）│             │
│  └──────────────────────────────────────────────────────┘             │
└───────────────────────────────────────────────────────────────────────┘
        ▲
        │  useMenuStore (Zustand)
┌─────────────────────────── MenuStore.ts ───────────────────────────┐
│  MENU_MANIFEST（路由清单，唯一真源）→ buildRuntimeMenuData             │
│  → menuData（持久化）/ currentModuleId（持久化）/ currentMenuData（派生）│
└──────────────────────────────────────────────────────────────────────┘
```

### <a id="32-组件职责划分"></a>3.2 组件职责划分

| 文件 | 职责 |
| --- | --- |
| `SidebarNav.tsx` | 数据组织（取数 / 过滤 / 区域拆分）、展开态、折叠三态、滑行玻璃生命周期、页面骨架 |
| `MenuNode.tsx` | 单节点渲染（四种形态）、路由高亮、跳转、子级递归、按压钩子 |
| `SidebarNav.module.scss` | 侧栏专属样式（毛玻璃块 + `:has()` 兄弟让位），CSS Module 封装，不泄露全局 |
| `menuPath.ts` | `matchPath` 单一真源（供 `MenuNode` 与 `SidebarNav` 复用，避免 react-refresh 仅导出组件的限制） |
| `MenuStore.ts` | 菜单数据与状态管理（构建 / 切换 / 持久化 / 派生） |
| `src/types/moduleMenu.ts` | 菜单类型契约（`NavMenuNode` / `NavModuleNode` / `ModuleMenuData`） |
| `src/style/palette.css` | `--nav-*` 主题令牌（毛玻璃块引用其中的 `--primary` / `--nav-item-height` / `--radius`） |

---

## <a id="4-菜单数据结构与存储"></a>4. 菜单数据结构与存储

### <a id="41-节点模型-navmenunode"></a>4.1 节点模型 `NavMenuNode`

定义于 `src/types/moduleMenu.ts`。同一套字段承载一级（分组）与二级（子项）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `menuId` | `string` | 节点唯一标识，同时作为 Tree 节点 id |
| `menuName` | `string?` | 菜单名称，i18n key 或直写文案 |
| `routePath` | `string?` | 路由路径；为空表示不可跳转 |
| `menuIcon` | `string?` | 图标名（lucide-react 组件名），运行时经白名单 `menuIconRegistry` 解析 |
| `menuBadge` | `string?` | 徽章文本 |
| `menuPosition` | `'header' \| 'content' \| 'footer'` | 所在区域，使用方据此拆分渲染 |
| `level` | `number` | 菜单层级（从 0 起），用于缩进 / 字号 |
| `menuType` | `'page' \| 'group' \| 'redirect' \| 'fallback'?` | 节点类型；`group` 仅作分区标题 |
| `menuExpanded` | `boolean` | 是否默认展开 |
| `description` | `string` | 页面描述，用于 tooltip |
| `exact` | `boolean?` | 是否精确匹配路由高亮 |
| `children` | `NavMenuNode[]?` | 子菜单节点；存在时渲染为嵌套项 |

> 注：当前侧栏实际仅使用 `content` 与 `footer` 两个区域（`header` 由顶部导航消费）。

### <a id="42-数据流清单-store-侧栏"></a>4.2 数据流：清单 → Store → 侧栏

```
MENU_MANIFEST（router/manifest.ts，唯一真源）
      │  buildRuntimeMenuData() 遍历每个模块子树
      ▼
menuData: Record<ModuleId, NavModuleNode>   ── 全量菜单数据（含模块元数据 + 菜单树）
      │  getValidModuleId() 校验当前模块
      ▼
currentModuleId: ModuleId                    ── 当前激活模块（持久化）
      │  menuData[currentModuleId]?.children
      ▼
currentMenuData: NavMenuNode[]               ── 当前模块菜单树（运行期派生，不持久化）
      │  useMenuStore((s) => s.currentMenuData)
      ▼
SidebarNav → contentItems / footerItems（按 menuPosition 拆分）
```

构建细节：
- `toNavMenuNode`：将 `AppRouteNode` 映射为 `NavMenuNode`（仅搬运展示字段）。
- `buildModuleMenuNodes`：递归构建并过滤 `menuVisible === false` 的节点；`group` 类型不可见时仅透传其子节点。

### <a id="43-持久化边界"></a>4.3 持久化边界

`MenuStore` 区分三类状态、各司其持久化职责：

| 状态 | 持久化 | 键 | 说明 |
| --- | --- | --- | --- |
| `menuData` | 是（localStorage） | `menu.menuData` | 全量菜单数据源，「存什么用什么」，缺失不回退实时数据 |
| `currentModuleId` | 是（localStorage） | `menu.currentModuleId` | 当前模块，刷新可还原 |
| `currentMenuData` | 否 | — | 由 `menuData + currentModuleId` 派生，运行期计算 |

三个业务场景：
- **首次登录**：`buildMenuData(loginModuleId?)` 构建全量并落盘 `menuData` + 写 `currentModuleId`。
- **切换模块**：`setCurrentModuleId(id)` 复用已持久化 `menuData`，仅更新 `currentModuleId` 并重算派生视图。
- **刷新浏览器**：store 初始化时从 localStorage 还原两者并派生 `currentMenuData`，无需手动调用。

### <a id="44-区域拆分content-footer"></a>4.4 区域拆分（content / footer）

`SidebarNav` 从 `MenuStore` 取 `currentMenuData`，经 `useMemo` 做两件事后拆分：

1. **AlphaSift 过滤**：未启用时剔除 `menuId === 'screening'`（选股入口）。
2. **按 `menuPosition` 分区**：
   - `contentItems = filtered.filter(menuPosition === 'content')`
   - `footerItems = filtered.filter(menuPosition === 'footer')`

拆分结果分别渲染到「主菜单滚动区」与「固定底部区」。

---

## <a id="5-与路由的关系"></a>5. 与路由的关系

### <a id="51-高亮判定-matchpath"></a>5.1 高亮判定 `matchPath`

定义在 `menuPath.ts`（单一真源，被 `MenuNode` 与 `SidebarNav` 复用）：

```ts
export const matchPath = (routePath, exact, pathname): boolean => {
  if (!routePath) return false;
  return exact
    ? pathname === routePath
    : pathname === routePath || pathname.startsWith(`${routePath}/`);
};
```

- 非精确（`exact` 为假）：当前路径等于路由或为其子路径即命中（支持二级页高亮一级）。
- 精确（`exact` 为真）：仅完全相等命中。

### <a id="52-激活的双触发自身-子项"></a>5.2 激活的双触发（自身 / 子项）

`MenuNode` 中：

```ts
const active =
  matchPath(routePath, exact, pathname) ||
  (hasChildren && children.some((c) => matchPath(c.routePath, c.exact, pathname)));
```

- 父级在「自身命中」或「任一子项命中」时同步高亮（对齐参考实现 `selfCurrent` / `childCurrent`）。
- 高亮视觉：父级仅文字加粗变主色（`MENU_ITEM_TEXT_ACTIVE`）；真正承载背景高亮的**是叶子项**（见 6.2）。

### <a id="53-模块切换自动跳转首个菜单"></a>5.3 模块切换自动跳转首个菜单

`SidebarNav` 监听 `currentMenuData` 变化（跳过首次挂载以免覆盖深链）：

```ts
const firstItem = contentItems[0];
const target = firstItem.children?.length ? firstItem.children[0] : firstItem;
if (target?.routePath) navigate(target.routePath);
```

- 一级含二级 → 跳到其内部第一个二级；否则跳该一级本身。

### <a id="54-父级自动展开深链-刷新"></a>5.4 父级自动展开（深链 / 刷新）

为避免「深链直达子页、但父级未展开导致子项不在 DOM、滑行玻璃无落点」：

```ts
const isExpanded = (node) => {
  if (userExpanded[node.menuId] !== undefined) return userExpanded[node.menuId];
  if (node.children?.some((c) => matchPath(c.routePath, c.exact, pathname))) return true; // 命中子项 → 自动展开
  return node.menuExpanded;
};
```

- 用户显式切换（`userExpanded`）优先；否则若某子项命中当前路由则父级自动展开；最后回退数据默认值。

---

## <a id="6-交互实现"></a>6. 交互实现

### <a id="61-三态折叠"></a>6.1 三态折叠

折叠态由外部（`Shell` 的 `useLayoutStore`）传入 `menuCollapsedState`，组件不自行订阅，便于复用与测试。

- 根节点宽度由 `style={{ width: sidebarWidth }}` 驱动，配 `transition-[width]` + `transform-gpu` + `will-change:width`，纯 CSS 过渡、提升为合成层，避免 motion 逐帧改 width 触发整页重排。
- `THEME_CONFIG`：按 `theme` 与 `collapsedState` 查表得到三态宽度（如 `pill: 160/80/0`、`square: 160/64/0`）与容器 / `aside` 类名。
- `collapsed`（图标栏）态：`MenuNode` 走独立分支，仅渲染图标 + `title`/`aria-label` 可访问性兜底，文字用 `hidden` 常驻挂载（避免切换瞬间 DOM 增删导致布局抖动）。

### <a id="62-滑行毛玻璃sliding-thumb"></a>6.2 滑行毛玻璃（Sliding Thumb）

**核心思想**（对应参考的 `slideThumb`）：菜单区只有「一块」毛玻璃 `.navThumb`，靠 `transform: translateY` 在菜单项之间**滑行**；图标 / 文字不动，只有背景材质在移动。

实现要点：

1. **结构**：`menuAreaRef`（`position: relative` 的菜单区包裹层，包含主菜单 `<nav>` 与 footer）首子节点放置唯一 `<div className={styles.navThumb} aria-hidden>`，`pointer-events: none` 不挡点击。
2. **定位**：`syncThumb(animate)` 用 `getBoundingClientRect` 量出 `[data-active="true"]` 项相对包裹层的 `y`，写 `transform: translateY(y)`；高度恒为 `var(--nav-item-height)`（所有项等高），故只动 `transform`（纯合成层）。
3. **动画策略**：
   - `animate=true`（仅**真实路由切换**）：回落模块 CSS 的 `transition: transform .42s cubic-bezier(.22,1,.36,1)` 播滑行。
   - `animate=false`（挂载 / 折叠 / 滚动 / resize）：`transition: none` 瞬时贴合，避免无意义位移与拖影。
4. **同步时机**（均 `rAF`/`useLayoutEffect` 节流，主线程友好）：
   - `useLayoutEffect`：路由 / 菜单数据 / 折叠态变化 → 同步；用 `prevPathRef` 区分「真实路由切换」才播动画；深链时父级刚自动展开、子菜单高度动画未结束，300ms 后补一次同步修正落点。
   - `scroll` 监听（主菜单，passive + rAF）：滚动时玻璃贴合当前项。
   - `ResizeObserver`：折叠动画 / 字号加载导致尺寸变化 → 瞬时对齐。
5. **可见性**：非 `offcanvas`（折叠图标栏 / 完全收起）时 `opacity:0` 隐藏玻璃，改由叶子项自带激活背景（`MENU_ITEM_ACTIVE`）承担高亮；`offcanvas` 时移除叶子自身背景，避免双重高亮。

> 设计取舍：参考项目用 GSAP 逐帧改 `transform`，本项目改用 CSS transition + 单块元素，更省、更贴合「简单高效」诉求；`[data-active]` 钩子落在真正高亮的**叶子项**而非父级。

### <a id="63-按压反馈press-feedback"></a>6.3 按压反馈（Press Feedback）

对应参考的 `installPressFeedback`（`scale: 0.955` + `back.out` 回弹）。

- 点击元素（折叠图标栏 `<a>`、可折叠父级 `<div>`、叶子 `<a>`）均改为 Framer Motion 的 `motion.*`。
- `whileTap={{ scale: 0.965 }}` + 弹簧回弹 `transition={{ type: 'spring', stiffness: 520, damping: 28 }}`：点下去轻微下陷，松手弹回。
- 与滑行玻璃解耦：按压缩放作用于菜单项自身（`transform: scale`），玻璃独立绝对定位，互不干扰。

### <a id="64-兄弟让位sibling-dimhas"></a>6.4 兄弟让位（Sibling Dim，`:has()`）

对应 `layout.css` 的 `:has()` 规则，纯 CSS、零 JS：

```scss
@media (hover: hover) {
  .navList:has(.menuItem:hover) .menuItem:not(:hover):not([data-active="true"]) {
    opacity: 0.62;
  }
}
```

- hover 某项时，同级**非选中**项降到 `opacity: .62` 让位；`[data-active="true"]`（当前激活项）始终满亮。
- 作用域由 CSS Module 的 `.navList` / `.menuItem`（哈希类）+ 全局属性选择器 `[data-active]` 共同约束，仅作用于同一列表内兄弟项。
- 透明度过渡由 `MENU_ITEM_BASE` 的 `transition-[...opacity] duration-200` 承担。

---

## <a id="7-样式与主题"></a>7. 样式与主题

### <a id="71-主题令牌-nav"></a>7.1 主题令牌 `--nav-*`

位于 `src/style/palette.css`，明暗主题各一套（通过 `[data-theme]` 切换）。毛玻璃块与菜单项均引用其中变量，保证主题一致：

| 变量 | 用途 |
| --- | --- |
| `--primary` | 主色（毛玻璃描边 / 内高光 / 文字激活色） |
| `--nav-item-height` | 菜单项行高（玻璃块高度，恒定 44px） |
| `--nav-active-bg` / `--nav-active-border` | 折叠态激活背景 / 边框 |
| `--nav-hover-bg` | hover 背景 |
| `--nav-divider` | 分区分隔线 |
| `--radius` | 圆角基准（玻璃块 `calc(var(--radius) - 4px)`） |

### <a id="72-css-module-封装策略"></a>7.2 CSS Module 封装策略

- 新增 `SidebarNav.module.scss`：承载 `.navThumb` 与 `:has()` 兄弟让位两类**侧栏专属**样式。
- 类名经 CSS Module 哈希（如 `.navList` / `.menuItem` / `.navThumb`），**不泄露到全局**；`MenuNode` 与 `SidebarNav` 共享同一模块 import。
- 全局性属性选择器 `[data-active="true"]` 在模块中保持全局语义，不哈希。
- 通用布局 / 间距仍用 Tailwind 工具类（行内），令牌走 `palette.css`——与项目既有约定一致。

### <a id="73-明暗主题"></a>7.3 明暗主题

- 明暗通过根节点 `data-theme` 切换 `--nav-*` / `--primary` 等变量；组件层无需条件判断。
- `prefers-reduced-motion`：`.navThumb` 关掉过渡；根节点宽度过渡也用 `motion-reduce:transition-none` 降级。

---

## <a id="8-性能设计"></a>8. 性能设计

| 手段 | 收益 |
| --- | --- |
| 玻璃块单元素 + 仅 `transform` 动画 | 纯合成层，不触发 layout / paint |
| 宽度过渡走 `transform-gpu + will-change:width` | 避免整页重排 |
| `scroll` 监听 `rAF` 节流 + passive | 滚动同步不阻塞主线程 |
| `useLayoutEffect` 测量（路由变化） | 绘制前完成定位，无闪烁 |
| `useMemo` 缓存 content/footer 拆分 | 避免每次渲染重复 filter |
| `transition: none` 瞬时贴合 | 滚动 / 折叠时不播无用滑行 |
| 子菜单高度动画 `AnimatePresence` height auto | 子项数量不定，高度由 motion 实测 |

---

## <a id="9-文件清单"></a>9. 文件清单

| 文件 | 角色 |
| --- | --- |
| `SidebarNav.tsx` | 侧栏容器：取数 / 区域拆分 / 展开态 / 滑行玻璃生命周期 / 骨架 |
| `MenuNode.tsx` | 单节点：四形态渲染 / 路由高亮 / 跳转 / 按压 / `data-active` 钩子 |
| `SidebarNav.module.scss` | 侧栏专属样式（毛玻璃 + `:has()` 兄弟让位），CSS Module |
| `menuPath.ts` | `matchPath` 单一真源（抽出以满足 react-refresh 仅导出组件约定） |
| `MenuStore.ts` | 菜单状态（Zustand）：构建 / 切换 / 持久化 / 派生 |
| `src/types/moduleMenu.ts` | `NavMenuNode` / `NavModuleNode` / `ModuleMenuData` 类型契约 |
| `src/style/palette.css` | `--nav-*` 主题令牌 |
| `router/manifest.ts` | `MENU_MANIFEST`：菜单数据唯一真源 |

---

## <a id="10-风险与后续"></a>10. 风险与后续

1. **行为变化**：父级自动展开（命中子项即展开）改变了「用户未展开则保持收起」的原交互，属正向改进但属行为变更，需在验收时确认。
2. **实机视觉未验收**：滑行手感、毛玻璃模糊强度、兄弟让位观感、明暗对比度、深链落点、折叠切换闪烁需在浏览器实机确认；`prefers-reduced-motion` 仅降级了玻璃过渡，按压回弹未单独降级。
3. **内边距耦合**：玻璃块 `left/right: 8px` 依赖主菜单与 footer 均为 `px-2`；若日后改内边距需同步调整。
4. **可访问性**：`aria-current="page"` 已挂在激活叶子；折叠图标栏用 `title` / `aria-label` 兜底，后续可补充 `aria-expanded` 等。
5. **后续可增强**：菜单项拖拽排序、徽章动效、键盘导航（方向键聚焦）等。
