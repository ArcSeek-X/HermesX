# 侧栏菜单滑动高亮交互 —— 技术拆解与复用指南

> 本文拆解 `scaffold-vue` 侧边导航「点击切换时一块玻璃在菜单项之间滑行」的交互实现，
> 并给出在后续项目中复用该交互的落地方案。

## 1. 交互效果

点击任意菜单项时，选中态背景不是"闪现切换"，而是**一块半透明玻璃从旧项平滑滑行到新项**：
图标和文字保持不动，只有背景材质在移动。切换时带有"按得下去"的按压回弹，以及
hover 时其它项淡出让位的细节。整体克制、高级。

## 2. 分层架构

实现由四层协作，职责清晰（符合项目"通用能力沉淀到组件/工具"的准则）：

| 层 | 文件 | 职责 |
|----|------|------|
| DOM 结构 | `scaffold-vue/src/components/layout/Sidebar.vue` | 渲染玻璃块 + 菜单项，派生激活态，触发同步 |
| 定位与动效 | `scaffold-vue/src/composables/motion.ts`（`slideThumb`） | 用 GSAP 把玻璃贴到目标项，处理缩放/滚动补偿 |
| 样式材质 | `scaffold-vue/src/styles/layout.css` + `scaffold-vue/src/styles/materials.css` | 玻璃定位盒 + 珍珠玻璃材质 + 文字过渡 |
| 全局手感 | `scaffold-vue/src/composables/motion.ts`（`installPressFeedback`） | 事件委托统一实现按压回弹 |

## 3. 核心机制拆解

### 3.1 一块玻璃，而非每项一个背景

关键 DOM（`Sidebar.vue`）：

```
<nav ref="nav" class="rail-nav">                 ← 定位父级 (position: relative)
  <span ref="thumb" class="nav-thumb m-pill" />  ← 唯一玻璃块（z-index: 0，pointer-events: none）
  <button class="nav-item is-active">...</button> ← 菜单项（z-index: 1，压在玻璃上）
```

- 玻璃与菜单项是**兄弟关系**，靠 `z-index` 叠放，玻璃永远在文字底下。
- 全导航只有**一块**玻璃，切换 = 移动这一块，因此能做"滑行"而非"闪现"。

### 3.2 路由驱动状态（单一真相源）

```ts
const activeKey = computed(() => String(route.name ?? ''))
```

激活态从路由名派生，不维护本地状态。天然兼容深链、前进/后退、刷新——任何入口只要路由变了，
高亮自动对齐。

### 3.3 定位与动效：`slideThumb`（motion.ts 第 177-197 行）

用几何差值把玻璃"贴"到目标项，坐标写成 `transform`（竖直方向写 `y` + `height`）：

```ts
const pr = parent.getBoundingClientRect()   // 容器包围盒
const tr = target.getBoundingClientRect()   // 目标项包围盒
// 缩放折算：祖先若在缩放，包围盒带缩放比例，需折回布局像素
const ky = parent.offsetHeight ? pr.height / parent.offsetHeight : 1
props = { y: (tr.top - pr.top)/ky - parent.clientTop + parent.scrollTop, height: tr.height/ky }
gsap.to(thumb, { ...props, duration: DUR.slide, ease: EASE.glide, overwrite: true })
```

设计要点：
- **几何差值**而非 `offsetTop`，玻璃与目标项不必同一父级，兼容复杂布局。
- **缩放补偿（`kx`/`ky`）**：弹窗/命令面板从触发点展开时祖先在缩放，防止首帧量错位。
- **滚动补偿**：减去 `clientTop`、加上 `scrollTop`，导航区可滚动时依然准确。
- **滑行手感**来自 `ease: 'power4.out'`（glide）+ `duration: 0.52`（快出慢收有余韵）。

### 3.4 触发时机：`sync` + `instant` 参数（Sidebar 第 25-38 行）

`sync()` 找到 `.is-active` 项并调 `slideThumb`。用 `instant` 严格区分「是否播动画」：

| 时机 | 触发 | instant |
|------|------|---------|
| 首次挂载 | `onMounted` → `sync(true)` | ✅ 瞬移，避免入场乱飞 |
| 用户切换路由 | `watch(activeKey)` → `sync()` | ❌ **播滑行**（唯一动画场景）|
| 菜单数据/折叠侧栏 | `watch([navGroups, railCollapsed])` → `sync(true)` | ✅ 瞬时对齐 |
| 容器尺寸变化 | `ResizeObserver` → `sync(true)` | ✅ 瞬时对齐 |

且都用 `nextTick`，确保 Vue 先把 `is-active` class 写入 DOM 再量位置。
**克制原则**：只有用户导航才动画，环境变化一律瞬时，不做无意义位移。

### 3.5 样式材质

- `.nav-thumb`（layout.css 96-106）：`position: absolute`、左右留 12px、`height: 38px`、
  `pointer-events: none`；`transform` 完全交给 GSAP，CSS 不写 transition（避免两套动画打架）。
- `.m-pill`（materials.css）：珍珠玻璃——白边 + 高光 + 内阴影，选中态最亮的一块。
- `.nav-item` 只过渡 `color`：选中变深、图标变蓝。
- 兄弟让位（layout.css 132-134）：`:has()` 纯 CSS，hover 时其它非选中项降到 `opacity: .62`。

### 3.6 按压反馈（全局事件委托）

`installPressFeedback`（motion.ts 65-84）把 `.nav-item` 纳入 PRESSABLE 选择器，按下
`scale: 0.955`、松开用 `back.out(1.6)` 弹回。不写在组件里，所有可点控件共享同一手感。

## 4. 为什么这套设计"高明"

1. **单一玻璃复用** → 能做滑行而非闪现。
2. **路由驱动** → 前进后退/刷新/深链天然一致。
3. **动画只用于真实切换** → `instant` 参数克制不滥用。
4. **几何/缩放/滚动三重补偿** → 边界情况鲁棒。
5. **职责分层** → 结构 / 动效 / 材质 / 手感各司其职，高度可复用。

> `slideThumb` 是轴向通用的（`axis: 'x' | 'y'`），同一段逻辑也被分段控件（segmented）
> 横向滑块复用。

## 5. 复用落地方案

在新项目中复刻该交互，建议按以下顺序迁移：

1. **迁移动效底座**：把 `motion.ts` 中的 `EASE` / `DUR` / `skipMotion` / `slideThumb` /
   `installPressFeedback` 抽出为独立动效模块（依赖 `gsap`）。
2. **抽导航组件**：将 `Sidebar.vue` 中「thumb + activeKey + sync + watch」的模式抽成
   通用 `NavRail` 组件，数据入口保留 `navGroups` 结构（`{ key, items: [{ key, label, path, icon }] }`）。
3. **保留 CSS 约定**：`.nav-thumb` 定位盒 + `m-pill` 材质 + `z-index` 叠放 + `transform`
   不写 CSS transition，三条不可省。
4. **接入路由**：`activeKey` 必须从 `route.name` 派生，不接受外部受控状态。
5. **无障碍**：保留 `aria-current="page"` 与 `prefers-reduced-motion` 降级（`skipMotion` 已处理）。

最小可复用单元清单：

- `slideThumb(thumb, target, axis, instant)` —— 核心定位与滑行。
- 一段 `sync()` + `watch(activeKey)` + `onMounted(sync(true))` + `ResizeObserver` —— 触发骨架。
- `.nav-thumb{position:absolute;...;pointer-events:none;z-index:0}` + `.nav-item{position:relative;z-index:1}` —— 叠放约定。
