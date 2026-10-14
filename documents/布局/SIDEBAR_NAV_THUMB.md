# <a id="sidebar-nav-thumb"></a>侧栏菜单滑动高亮交互方案设计

> 📝 **方案简述**：本文拆解 HermesX 侧边导航（React + Tailwind 自研）「点击切换时一块玻璃在菜单项之间滑行」的交互实现，并给出在后续项目中复用该交互的落地方案。核心设计是"单一玻璃复用 + 路由驱动高亮 + 几何定位与瞬时/滑行双模 + 落点补偿（折叠上移 / 子菜单开合漂移修正）"，使选中态背景能在菜单项间平滑滑行而非闪现，且数据 / 编排 / 节点 / 动效职责分离、高度可复用。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-14

## 目录

- [1. 交互效果](#sec-1)
- [2. 分层架构](#sec-2)
- [3. 核心机制拆解](#sec-3)
  - [3.1 一块玻璃，而非每项一个背景](#sec-3-1)
  - [3.2 路由驱动高亮（单一真相源）](#sec-3-2)
  - [3.3 定位与动效：slideThumb](#sec-3-3)
  - [3.4 触发时机：syncThumb + 瞬时/滑行双模](#sec-3-4)
  - [3.5 样式材质](#sec-3-5)
  - [3.6 按压反馈（组件级 whileTap）](#sec-3-6)
- [4. 为什么这套设计"高明"](#sec-4)
- [5. 复用落地方案](#sec-5)

<a id="sec-1"></a>

## 1. 交互效果

点击任意菜单项时，选中态背景不是"闪现切换"，而是**一块半透明玻璃从旧项平滑滑行到新项**：
图标和文字保持不动，只有背景材质在移动。切换时带有"按得下去"的按压回弹，以及
hover 时其它项淡出让位的细节。整体克制、高级。

<a id="sec-2"></a>

## 2. 分层架构

实现由四层协作，职责清晰（符合项目"通用能力沉淀到组件/工具"的准则）：

| 层 | 文件 | 职责 |
|----|------|------|
| 数据 | `stores/MenuStore.ts`（`useMenuStore`） | 以 `MENU_MANIFEST` 为唯一真值源，构建 `currentMenuData`（按当前模块筛选、含 `menuPosition`） |
| 编排 | `SidebarNav.tsx` | 取 `currentMenuData`、AlphaSift 过滤「选股」、content/footer 分区、展开态、模块切换自动跳转、DOM 接线（含唯一玻璃块 `.navThumb`） |
| 节点 | `MenuNode.tsx` | 单节点四形态渲染（图标栏 / 分组标题 / 可折叠 / 叶子）、路由高亮、点击跳转、子级递归、标记 `data-active` / `data-menu-id` |
| 玻璃动效 | `useNavThumb.ts` | 落点解析（`resolveHighlightMenuId`）、定位与滑行（`slideThumb`）、触发骨架、滚动 / `ResizeObserver` 同步 |

<a id="sec-3"></a>

## 3. 核心机制拆解

<a id="sec-3-1"></a>

### 3.1 一块玻璃，而非每项一个背景

关键 DOM（`SidebarNav.tsx` 菜单区）：

```tsx
<div ref={menuAreaRef} className="relative ...">          {/* 定位父级 (position: relative) */}
  <div ref={thumbRef} className={styles.navThumb} />      {/* 唯一玻璃块（z-index: 0，pointer-events: none） */}
  <ScrollShadow as="nav">…<MenuNode … />…</ScrollShadow>  {/* 菜单项（z-index: 1，压在玻璃上） */}
</div>
```

- 玻璃与菜单项是**兄弟关系**，靠 `z-index` 叠放，玻璃永远在文字底下。
- 全导航只有**一块**玻璃，切换 = 移动这一块，因此能做"滑行"而非"闪现"。
- 玻璃仅 `offcanvas` 态可见并承担选中背景；`collapsed`（64px 图标栏）/ `fully` 态由菜单项自带背景承接。

<a id="sec-3-2"></a>

### 3.2 路由驱动高亮（单一真相源）

高亮与玻璃落点**同源**：均从 `pathname`（`react-router`）派生，不维护本地高亮状态。

- 落点解析 `resolveHighlightMenuId(menuNodes, pathname, isExpanded)`：单遍遍历（`findBestChain` + `isBetterChain`）求"当前路径最佳命中链"，多命中时先取完全相等、再取更深者；命中项被折叠祖先隐藏时落点上移到链上第一个可见祖先（折叠含激活子项的一级菜单时玻璃落到该一级菜单）。
- 节点高亮 `MenuNode` 内 `isActiveRoute = matchPath(自身) || 任意子项 matchPath`，与落点共用同一 `matchPath` 原语。

天然兼容深链、前进/后退、刷新——任何入口只要路由变了，高亮与玻璃自动对齐。

<a id="sec-3-3"></a>

### 3.3 定位与动效：`slideThumb`

用几何差值把玻璃"贴"到目标行，坐标写成 `transform: translateY(y)`：

```ts
const ar = menuArea.getBoundingClientRect()    // 容器包围盒
const tr = targetRow.getBoundingClientRect()   // 目标行包围盒
const y = tr.top - ar.top                      // 实时计算，滚动天然安全
```

设计要点：
- **几何差值**而非 `offsetTop`，玻璃与目标行不必同一父级，兼容复杂布局。
- **动画贴合**：用 Web Animations API 从"当前视觉位置"（`getCurrentY` 读 `getComputedStyle` 的 `m42`）滑到目标，无 WAAPI 时回退直接写 `transform`。
- **覆盖进行中动画**：`thumb.getAnimations().forEach(a => a.cancel())`（等价 gsap `overwrite: true`），避免多次切换叠加错位。
- **滑行手感**：`easing: cubic-bezier(0.22,1,0.36,1)` + `duration: 520ms`（快出慢收有余韵）；减弱动效时 300ms。
- **CSS 不写 transition**——`transform` 完全交给 `slideThumb`，避免两套动画打架。

<a id="sec-3-4"></a>

### 3.4 触发时机：syncThumb + 瞬时/滑行双模

`syncThumb(animateSlide)` 找到落点行（`findTarget` 按 `highlightMenuId` 精确匹配 `[data-menu-id]`，避免折叠退场旧行误匹配）并调 `slideThumb`。用 `animateSlide` 严格区分「是否播动画」：

| 时机 | 触发 | animateSlide |
|------|------|--------------|
| 首次挂载 | 初始化 → `syncThumb(false)` | 瞬移，避免入场乱飞 |
| 用户切换路由 | `pathname` 变化 → `syncThumb(true)` | ✅ **播滑行**（唯一动画场景）|
| 折叠/展开、菜单数据变化 | `ResizeObserver` / 折叠态变化 → `syncThumb(false)` | 瞬时对齐 |
| 容器尺寸变化 | `ResizeObserver`（菜单区 + 每个 `ul`）→ `syncThumb(false)` | 瞬时对齐 |
| 滚动 | `scroll`（rAF 节流）→ `syncThumb(false)` | 瞬时贴合（避免拖影）|
| 跨父级切换漂移 | 300ms 后测漂移 > 2px → `syncThumb(true, settle)` | 补一段短滑行修正 |

**克制原则**：只有用户导航才动画，环境变化一律瞬时，不做无意义位移。跨父级切换时子菜单 `height` 动画未结束会令落点 Y 短暂偏移，故滑行后再做一次"漂移检测"补正（否则主动画会被无条件掐断、时长失效）。

<a id="sec-3-5"></a>

### 3.5 样式材质

- 菜单行基础样式集中在 `MenuNode.tsx` 的 `MENU_ITEM_*` 常量（`MENU_ITEM_BASE` 含 `position` 相关 `z-[1]`、`border-transparent` 占位边框防激活抖动、opacity 过渡供兄弟让位）；激活背景 `MENU_ITEM_ACTIVE` 仅 `collapsed`/`fully` 态使用。
- `.navThumb`（`.module.scss`）：绝对定位、`pointer-events: none`、`z-index: 0`；`transform` 完全交给 `slideThumb`，**CSS 不写 transition**。
- 兄弟让位：菜单项 `transition` 含 `opacity`，配合 `:has()`（scss 内）在 hover 时其它非选中项淡出。
- 文字/图标激活色：叶子在 `offcanvas` 态仅保留文字激活色（背景已由玻璃承担），避免双重高亮。

<a id="sec-3-6"></a>

### 3.6 按压反馈（组件级 whileTap）

按压回弹由 `motion` 的 `whileTap` 在每个菜单行上实现，而非全局事件委托：

```tsx
whileTap={MENU_ITEM_PRESS}            // { scale: 0.965 }
transition={MENU_ITEM_PRESS_SPRING}   // { type: 'spring', stiffness: 520, damping: 28 }
```

按下轻微下陷、松手弹簧回弹；所有行共享同一组常量（`MENU_ITEM_PRESS` / `MENU_ITEM_PRESS_SPRING`），手感一致且无需在组件外挂事件委托。

<a id="sec-4"></a>

## 4. 为什么这套设计"高明"

1. **单一玻璃复用** → 能做滑行而非闪现。
2. **路由驱动高亮与落点同源** → 前进后退/刷新/深链天然一致，无双份状态失同步。
3. **动画只用于真实切换** → `animateSlide` 双模克制不滥用。
4. **几何定位 + 落点补偿** → 折叠上移 + 子菜单开合漂移修正，边界情况鲁棒。
5. **职责分层** → 数据 / 编排 / 节点 / 动效各司其职，高度可复用。

> `slideThumb` 是零依赖的可复用单元（Web Animations API，等价 GSAP `to(thumb,{y})`），同一段几何定位逻辑也可复用于横向滑块等轴向场景。

<a id="sec-5"></a>

## 5. 复用落地方案

在新项目中复刻该交互，建议按以下顺序迁移：

1. **迁移动效底座**：把 `useNavThumb.ts` 中的 `slideThumb`（零依赖）+ `matchPath` / `resolveHighlightMenuId` 抽出为独立动效模块。
2. **抽导航组件**：将 `SidebarNav` + `MenuNode` 中「`.navThumb` + 路由高亮 + 展开态 + 滚动/RO 同步」的模式抽成通用 `NavRail` 组件，数据入口保留 `currentMenuData`（`NavMenuNode[]`，含 `menuPosition`）。
3. **保留 CSS 约定**：唯一 `.navThumb`（absolute, z-0, `pointer-events:none`）+ 菜单项 `z-1` + `transform` 不写 CSS transition + `:has()` 兄弟让位，三条不可省。
4. **接入路由**：高亮与落点必须从 `pathname`（react-router）派生，不接受外部受控状态。
5. **无障碍**：保留 `aria-current="page"` 与 `prefers-reduced-motion` 降级（`reduceMotionRef` + `THUMB_SLIDE_REDUCED_MS`）。

最小可复用单元清单：

- `slideThumb(thumb, targetRow, menuArea, animateSlide, duration)` —— 核心定位与滑行。
- `resolveHighlightMenuId(menuNodes, pathname, isExpanded)` + `matchPath(routePath, exact, pathname)` —— 落点/高亮解析原语。
- `useNavThumb({ menuItems, pathname, isExpanded, collapsedState })` —— 触发骨架（路由 watch + 滚动 + ResizeObserver）。
- `.navThumb{position:absolute;…;pointer-events:none;z-index:0}` + 菜单项 `{position:relative;z-index:1}` —— 叠放约定。
