# tailwind.config.js 使用情况排查报告

排查对象：`apps/hrs-web/tailwind.config.js`
Tailwind 版本：v4.3.3（CSS-First，通过 `src/style/index.css` 的 `@config "../../tailwind.config.js"` 加载 legacy JS 配置）
最后更新：2026-08-31（已执行第一批删除，见第 0 节）

---

## 0. 变更记录

### 2026-08-31 第一批删除（已执行）

| 删除项 | 原位置 | 连带处理 |
| --- | --- | --- |
| `colors.input`、`colors.ring` | 原 19–20 行 | 同步删除 `hsl-inline.css` 的 `--color-input`、`--color-ring` |
| `colors['subtle-soft']`、`colors['subtle-active']` | 原 101–102 行 | 同步删除 `backgroundColor` 中未注释的同名项 |
| `colors['surface-1']`、`['surface-2']`、`['surface-3']` | 原 103–105 行 | 见下方风险提示 |
| `borderColor` 注释块 | 原 110–114 行 | — |
| `theme.extend.spacing` | 原 169–172 行 | — |

文件规模：206 行 → 187 行。

**编译产物对比验证**（同 candidates 重新编译，前 185471 字节 / 后 184383 字节）：

- 消失的选择器 12 个，其中 8 个是探测用候选（`border-input`、`ring-ring`、`bg-secondary-bg`、`bg-muted-bg`、`bg-subtle-soft`、`bg-subtle-active`、`bg-surface-1`、`bg-surface-3`），**运行时 0 使用**。
- 新增选择器 0 个。
- `@keyframes` 列表前后一致：`spin, pulse, fadeIn, slideInRight`。

### ⚠️ 本次删除引入的唯一实质影响：`bg-surface-2`

`bg-surface-2` 系列 4 个选择器随之消失（`bg-surface-2`、`bg-surface-2/60`、`bg-surface-2/70`、`hover:bg-surface-2`），涉及 **6 处正式代码**：

| 文件 | 用法 |
| --- | --- |
| `src/components/basic/Toast.tsx` | `bg-surface-2`、`hover:bg-surface-2`、`bg-surface-2/60` |
| `src/components/common/InlineTipCard.tsx` | `hover:bg-surface-2`、`bg-surface-2/60` |
| `src/pages/TokenUsagePage.tsx` | `bg-surface-2/70`（表头背景） |

**但：`--surface-1/2/3` 三个变量只在 `src/style/palette-viewer.html` 中定义**（独立静态预览页，不在构建链路），`palette.css` 与 `global.scss` 均未定义。

因此删除前 `bg-surface-2` 解析为 `background-color: var(--surface-2)`，变量未定义 → 声明无效。删除后变为无声明、继承父级背景。**差异在于：若父级存在背景色，删除后会透出父级背景**，这是可见变化。

处理建议（二选一）：

1. 把 `--surface-1/2/3` 补进 `palette.css` 的 `:root` 与 `.dark`（取值可直接沿用 palette-viewer.html：`--surface-1: hsl(var(--card))`、`--surface-2: hsl(var(--elevated))`、`--surface-3: hsl(var(--hover))`）—— 但这样 `bg-surface-2` 类已不存在，需同时改回调用方。
2. 确认这些位置本就期望透明，则忽略。

### 2026-08-31 第二批：以 config 为基准统一动画与边框（用户执行 + 本轮修正）

| 操作 | 执行方 | 结果 |
| --- | --- | --- |
| `animate-slide-in-left` 从 `global.scss` 迁至 config | 用户 | 类已删，config 已加 `animation['slide-in-left']` |
| 补 `keyframes.slideInLeft` 到 config | 本轮修正 | 用户原改动缺失，见问题 B |
| 删除 `global.scss` 的 `@keyframes slideInLeft` | 本轮收尾 | 迁移完成后清除重复定义 |
| 删除 `global.scss` 的 `.bg-subtle`、`.border-subtle`、`.border-subtle-hover:hover` | 用户 | 已删除（前两处为注释状态） |
| 修正 `borderColor.subtle` 的 `hsl()` 双重包裹 | 本轮修正 | 见问题 A |
| 删除全部 `hover:bg-surface-hover` 引用 | 用户 | `MarketReviewRegionSelector.tsx` 3 处已清理，全项目无残留 |
| 删除复现的 `backgroundColor.subtle-soft` / `subtle-active` | 本轮修正 | 见问题 D |

**修正前发现的两个问题（均已修复并编译验证）：**

- **问题 A：`borderColor.subtle` 写成 `hsl(var(--border-subtle))`，导致边框色失效。**
  `--border-subtle` 本身已是 `hsl(var(--border-subtle-raw) / 0.04)`（light）/ `0.08`（dark），再套一层 `hsl()` 得到 `hsl(hsl(...))`，是非法颜色值，浏览器整条声明丢弃。
  编译取证：`.border-subtle { border-color: hsl(var(--border-subtle)); }`。
  影响 `border-subtle` 全部 63 处引用，light / dark 两个主题下边框色都会回退到 currentColor。
  已改为 `var(--border-subtle)`，验证产物：`.border-subtle { border-color: var(--border-subtle); }`。

- **问题 B：`animation['slide-in-left']` 缺少 `keyframes.slideInLeft`。**
  编译取证：`@keyframes` 列表只有 `spin, pulse, fadeIn, slideInRight`，`slideInLeft` 未生成。
  `animate-slide-in-left` 类虽已生成，但找不到对应 keyframes，Drawer 左侧抽屉会无动画直接闪现。
  已补入 config，验证产物 `@keyframes` 列表：`spin, pulse, fadeIn, slideInLeft, slideInRight`。

**遗留待确认（非本轮引入，既有问题）：**

- **问题 C：`--bg-subtle-hover` 从未定义。**
  `palette.css` 无此变量，但 `global.scss` 有两处引用：`:373` `.bg-subtle-hover:hover`、`:1291` `.btn-secondary:hover`。
  两处 `background` 声明均无效。后者是真实可见缺陷：**次要按钮 hover 时背景色无变化**。
  建议：在 `palette.css` 补 `--bg-subtle-hover`（light 可取 `hsl(var(--bg-subtle-raw) / 0.1)`），或改用已有变量。

- **问题 D：`backgroundColor.subtle-soft` / `subtle-active` 复现。**
  第一批已删除的两项在第二批改动中重新出现（0 使用），已再次删除。

**本轮改动的视觉影响：**

| 类 | 删除 global.scss 前 | 现行为（config 值） | light 主题变化 |
| --- | --- | --- | --- |
| `.bg-subtle` | `var(--bg-subtle)` = 0.03 | 0.05 | 略变重 |
| `.border-subtle` | `var(--border-subtle)` = 0.04 | `var(--border-subtle)` = 0.04 | 无变化 |
| `.border-subtle-hover` | 0.06 | 0.15 | **明显变重（2.5 倍）** |

`border-subtle-hover` 在 light 主题下从 0.06 跳到 0.15。若偏重，可改为 `var(--border-subtle-hover)` 以保留 light 0.06 / dark 0.15 的主题差异。

### 2026-08-31 第三批：补齐缺失定义 + 清理冗余变量（已执行）

| 操作 | 结果 |
| --- | --- |
| `palette.css` 补 `--bg-subtle-hover`（light 0.1 / dark 0.15） | 修复 `.btn-secondary:hover` 背景色缺失 |
| `palette.css` 删除 `--bg-hover`、`--home-mobile-overlay-bg`、`--settings-border-overlay`、`--settings-accent-shadow` | 已确认全仓库无运行时消费，light / dark 共 8 行 |
| `global.scss` 删除 `@keyframes slideInRight`、`.animate-fade-in`、`.animate-spin-in-right` 手写类 | 以 config 为基准，keyframes 由 config 提供 |

编译验证：产物 184356 → 184077 字节（减少部分即 palette.css 中被删的 8 行），`@keyframes` 列表保持 `spin, pulse, fadeIn, slideInLeft, slideInRight` 不变。

**遗留待决策**：`--login-input-toggle-*` 等 13 个变量受一个已失效的测试引用，详见 7.3 节。

---

## 1. 排查方法

### 1.1 静态扫描

提取 `content` 覆盖范围内（`index.html` + `src/**/*.{js,ts,jsx,tsx}`）的所有字符串 token，按 Tailwind 全部颜色命名空间交叉匹配，避免只查 `text-`/`bg-` 造成漏判：

`text-`、`bg-`、`border-`、`ring-`、`divide-`、`from-`、`via-`、`to-`、`fill-`、`stroke-`、`shadow-`、`outline-`、`caret-`、`accent-`、`decoration-`、`placeholder-`

同时识别 `hover:`、`dark:`、`md:` 等变体后缀，以及 `/opacity` 透明度修饰符。

### 1.2 真实编译验证

用 Tailwind v4.3.3 的 `compile()` API 加载 `index.css` 完整链路（`@import "tailwindcss"` → `@config` → `palette.css` → `hsl-inline.css`），把源码 token 作为 candidates 编译，直接检查产物 CSS 中每个类的最终声明。

这一步是必要的，它暴露了静态扫描无法发现的事实：`darkMode`/`content`/`container` 在 v4 `@config` 兼容层下是否真的生效、哪些 token 被 `hsl-inline.css` 的 `@theme inline` 覆盖、哪些 Tailwind 类被 `global.scss` 手写类覆盖。

---

## 2. 前提事实（决定哪些配置能删）

| 事实 | 验证结果 | 结论 |
| --- | --- | --- |
| `darkMode: ['class']` | 产物输出 `.dark\:xxx:is(.dark *)`，而非 `@media (prefers-color-scheme: dark)` | **生效，必须保留** |
| `content` | `compile()` 返回的 `sources` 正是这两个 glob | **生效**。保留可限制扫描范围；删除会回退到 v4 全项目自动检测，产物变大 |
| `theme.container` | 产物输出 `--container-2xl`，配置被读取 | 配置生效但全项目 **0 处**使用 `container` 类 → 整块可删 |
| `hsl(var(--x))` 解包问题 | 实测 `.bg-muted` 输出 `background-color: hsl(var(--muted))`，`hsl()` 包裹完好 | v4.3.3 下不复现，`hsl-inline.css` 头部注释已过时 |

### 2.1 ⚠️ `global.scss` 手写类覆盖 Tailwind 类

`global.scss` 是非 layer 的普通 CSS，在 `index.css` 中最后 `@import`，优先级高于 Tailwind 的 utilities layer。以下三处**与 Tailwind 配置生成的类同名，会覆盖配置值**：

| global.scss | 声明 | 覆盖的 Tailwind 类 | 影响 |
| --- | --- | --- | --- |
| `369` 行 `.bg-subtle` | `background: var(--bg-subtle)`（palette.css：light 0.03 / dark 0.05） | `backgroundColor.subtle`（0.05） | light 主题下 0.03 ≠ 0.05 |
| `387` 行 `.border-subtle` | `border-color: var(--border-subtle)`（light 0.04 / dark 0.08） | `borderColor.subtle`（0.08） | light 主题下 0.04 ≠ 0.08 |
| `391` 行 `.border-subtle-hover:hover` | `border-color: var(--border-subtle-hover)`（light 0.06 / dark 0.15） | `borderColor['subtle-hover']`（0.15） | light 主题下 0.06 ≠ 0.15 |

即：**`borderColor` 与 `backgroundColor` 的实际渲染曾由 `global.scss` 决定**，config 中的值仅在 dark 主题下与之一致。`border-subtle` 有 63 处引用。

**第二批已将这三处手写类全部删除，冲突解除，现以 config 为唯一真源。** light 主题下的实际取值变化见第 0 节"本轮改动的视觉影响"。

### 2.2 其它既有代码问题（顺带记录）

- ✅ `hover:bg-surface-hover`（`MarketReviewRegionSelector.tsx` 3 处）：Tailwind 配置与 `global.scss` 均无 `surface-hover` 定义，是无效类。**第二批已在引用处全部删除，全项目无残留。**
- ✅ `animate-slide-in-left`（`Drawer.tsx`）：原依赖 `global.scss:1469` 手写类 + `:1458` `@keyframes slideInLeft`。**第二批已完整迁移至 config**（`animation['slide-in-left']` + `keyframes.slideInLeft`），global.scss 中的类与 keyframes 均已删除。
- ⚠️ `--bg-subtle-hover` 变量从未在 `palette.css` 定义，导致 `global.scss:373` 与 `:1291` 两处 `background` 声明无效，其中 `.btn-secondary:hover` 的 hover 背景色缺失是可见缺陷。详见第 0 节问题 C。

---

## 3. 未使用清单

### 3.1 已删除（第一批，2026-08-31）

`colors.input`、`colors.ring`、`colors['subtle-soft']`、`colors['subtle-active']`、`colors['surface-1']`、`['surface-2']`、`['surface-3']`、`backgroundColor['subtle-soft']`、`backgroundColor['subtle-active']`、`theme.extend.spacing`（`18`、`22`）、`borderColor` 注释块。

### 3.2 仍待删除（P0，零风险）

**colors**

```
dim、overlay-hover、overlay-selected
secondary-bg、muted-bg          （当前为注释状态，可一并清理）
```

`foreground` 系列（7 项中 6 项未用）：

| 变体 | 状态 |
| --- | --- |
| `foreground` | 在用（104 处） |
| `foreground-soft` | 在用（10 处） |
| `foreground-dim`、`glow`、`lightest`、`subtle`、`faint` | **未用** |

`primary` 系列（8 项中 3 项未用）：

| 变体 | 状态 |
| --- | --- |
| `primary`、`primary-foreground` | 在用（66 / 2 处） |
| `primary-glow`、`primary-subtle`、`primary-faint` | 在用（2 / 1 / 2 处） |
| `primary-dim`、`primary-soft`、`primary-lightest` | **未用** |

```
success-dim、success-glow
warning-dim、warning-glow
danger-dim、danger-glow
cyan-dim、cyan-glow
purple-dim、purple-glow
secondary-foreground、muted-foreground、accent-foreground
popover-foreground、card-foreground
destructive
```

> 父级 `secondary`/`muted`/`accent`/`popover`/`card` 均在用，只有 `-foreground` 变体和 `destructive` 本体无引用。

**其它配置块**

| 配置块 | 未使用项 | 在用项 |
| --- | --- | --- |
| `backgroundImage` | `gradient-purple-cyan`、`gradient-card-border` | `gradient-cyan`（1）、`primary-gradient`（1） |
| `boxShadow` | `glow-purple`、`glow-success`、`glow-danger`、`cyan/20`、`cyan/22` | `soft-card`（27）、`soft-card-strong`（3）、`glow-cyan`（2） |
| `fontSize` | `7xl`、`8xl`、`9xl` | `xxs`、`xs`–`6xl`、`10xl` 全部在用 |
| `animation` | `slide-up`、`pulse-glow`、`spin-slow`、`float-in` | `fade-in`（8）、`slide-in-right`（1） |
| `keyframes` | `slideUp`、`floatIn`、`pulseGlow`；`slideInRight` 与 `global.scss:228` 手写定义重复 | `fadeIn` |
| `container` | 整块（`center` / `padding` / `screens`） | — |

---

## 4. 重复定义（P1，合并而非直接删）

1. **`colors.subtle` / `colors['subtle-hover']` 与 `backgroundColor` 同名项值完全相同**（0.05 / 0.1）。
   且 `divide-subtle`（3 处）实测产物为 `hsl(var(--border-subtle-raw) / 0.08)`，走 `borderColor` 命名空间（v3/v4 中 `divideColor` 默认继承 `borderColor`），不是 `colors.subtle` 的 0.05。
   → `colors.subtle` 对现有用法零贡献。

2. **`colors.dim` 与 `borderColor.dim` 值完全相同**，两边引用均为 0。

3. **26 个 token 被 `hsl-inline.css` 的 `@theme inline` 覆盖**，config 中的同名定义不决定最终 CSS：

```
border、background、foreground
primary、primary-foreground
secondary、secondary-foreground、muted-foreground、accent-foreground
destructive、destructive-foreground
popover、popover-foreground
card、card-foreground
base、elevated、hover
secondary-text、muted-text
cyan、purple、success、warning、danger
subtle、subtle-hover
```

> 例外：`colors.muted`、`colors.accent`、`colors.base` 在 `hsl-inline.css` 中或被注释、或被改为不同值，见第 5 节。

---

## 5. 两个坑（删除前必须处理）

### 坑 1：`colors.base` 是语义冲突的死配置

- config 定义：`base: 'hsl(var(--background))'`
- `hsl-inline.css:59` 覆盖：`--color-base: hsl(var(--text-primary))`
- 实测产物：`.bg-base { background-color: hsl(var(--text-primary)) }`

config 中的值与生效值**一个是背景色、一个是文字色**，语义相反。`bg-base` 已被 40 处 / 31 个文件使用，语义已按 `--text-primary` 固化。

处理建议：删除 config 的 `base`，并在 `hsl-inline.css` 注明 `--color-base` 的唯一真源是 `--text-primary`。

### 坑 2：删除 `keyframes.fadeIn` 会导致动画静默失效

`global.scss`：

- `292` 行：`.animate-fade-in { animation: fadeIn 0.3s ease-out; }`
- `318` 行：`.fade-in { animation-name: fadeIn; }`

但 **global.scss 全文没有 `@keyframes fadeIn`**，它依赖 config 的 `keyframes.fadeIn` 产出。删除后 `animate-fade-in`（8 处 JSX）与 `.fade-in` 会全部静止，且不会有构建报错。

补充：`animate-fade-in` / `animate-slide-in-right` 的最终样式由 global.scss 的 unlayered 手写类决定（优先级高于 utilities layer），config 中 `animation` 的值本身不决定渲染结果，仅 `keyframes` 被真实依赖。

---

## 6. 精简方案

### 第一批（已于 2026-08-31 执行）

见第 0 节。206 行 → 187 行。

### 第二批（零风险）

- 删除第 3.2 节全部未使用项
- 删除 `theme.container` 整块
- 清理 `secondary-bg` / `muted-bg` 注释行

预计：187 行 → 约 115 行。

### 第三批（需回归）

- 处理 `colors.base` 语义冲突（删除 config 定义，在 `hsl-inline.css` 标注真源）
- 清理第 4 节中与 `hsl-inline.css` 重复的 26 个 token
- 合并 `colors.subtle` / `colors.dim`
- 处理第 2.1 节 `global.scss` 与 config 的同名类冲突（决定以哪一方为准）

预计：→ 约 70 行。

### 必须保留（看似冗余，删除会改变渲染）

| 配置 | 保留原因 |
| --- | --- |
| `darkMode`、`content` | 在 v4 `@config` 下实测生效，见第 2 节 |
| `fontSize` 的 `xs`–`6xl` | 覆盖了默认值的 line-height。例如 `text-lg` 从默认 `1.125rem/1.75rem` 变为无行高的 `1.125rem`，删除整块会导致大面积行高变化 |
| `borderRadius` 的 `sm`/`md`/`lg`/`3xl` | 值与 Tailwind 默认不同（`lg` = `var(--radius)`、`3xl` = 20px 而默认 24px） |
| `borderColor`、`backgroundColor` | `border-subtle` 63 处、`bg-subtle` 7 处、`bg-subtle-hover` 6 处 |
| `keyframes.fadeIn` | 见坑 2 |

### 可顺带删除（值与默认相同，删后行为不变）

- `borderRadius.xl`（12px = 默认 0.75rem）
- `borderRadius.2xl`（16px = 默认 1rem）

---

## 7. 关联文件检查结论

### 7.1 `src/style/hsl-inline.css`

**已更新**：删除 `--color-input`、`--color-ring` 及其注释（config 删除 `colors.input`/`colors.ring` 后，这两个 token 已无消费者；`border-input` / `ring-ring` 全项目 0 使用）。

其余内容无需改动。`hsl-inline.css` 头部关于"`@config` 会解包 `hsl(var(--x))`"的注释已过时（v4.3.3 实测不复现），可考虑更新但非必须。

### 7.2 `src/style/global.scss`

**第一批**：无需改动。全文不引用 `--input`、`--ring`、`--surface-1/2/3`、`--input-surface-*`（不同前缀，无关）、`w-18`/`p-18`/`h-22`/`m-22`。

**第二批（用户执行）**：删除 `.bg-subtle`(369)、`.border-subtle`(387)、`.border-subtle-hover:hover`(391)、`.animate-slide-in-left`(1469)。
**第二批（本轮收尾）**：删除已迁至 config 的 `@keyframes slideInLeft`。

当前状态：

- 剩余自带 `@keyframes`：`slideInRight`(228)、`spin`(239)、`zoomIn`(248)、`slideInFromTopSm`(259)、`slideInFromTopMd`(270)、`slideInFromBottomMd`(281)。**无 `fadeIn`**，依赖 config 提供（见第 5 节坑 2）。
- 剩余自带动画类 `.animate-fade-in`(292)、`.animate-slide-in-right`(296)、`.animate-spin`(300)、`.animate-in`(304)。前两者与 config 同名，仍会覆盖 config 的 `animation` 值（keyframes 仍由 config 提供），后续批次可清理。
- `@keyframes slideInRight`(228) 与 config 的 `keyframes.slideInRight` 重复定义，内容一致、无实际冲突。
- ⚠️ `.bg-subtle-hover:hover`(373) 与 `.btn-secondary:hover`(1291) 引用的 `--bg-subtle-hover` 在 `palette.css` 中无定义，两处声明无效。

### 7.3 `src/style/palette.css`

**无必须删除项。** 扫描 216 个变量定义后，应用运行时（排除 `palette.css` 自身与调色板文档 `palette-viewer.html`）无消费的变量共 20 个：

```
--input、--ring
--glow-intensity、--bg-hover
--home-mobile-overlay-bg
--settings-border-overlay、--settings-accent-shadow
--login-label-text、--login-hint-text、--login-input-icon
--login-input-toggle-bg / -border / -text
--login-input-toggle-border-hover / -bg-hover / -text-hover / -ring
--login-input-toggle-active-bg / -active-border / -active-text
```

**第三批（已执行）**：补齐缺失定义，删除 4 个确认无引用的变量。

| 操作 | 内容 |
| --- | --- |
| 补充定义 | `--bg-subtle-hover`：light `hsl(var(--bg-subtle-raw) / 0.1)`、dark `hsl(var(--bg-subtle-raw) / 0.15)` |
| 删除 | `--bg-hover`、`--home-mobile-overlay-bg`、`--settings-border-overlay`、`--settings-accent-shadow`（light / dark 各 1 处，共 8 行） |

补齐后 `global.scss` 的 `.bg-subtle-hover:hover` 与 `.btn-secondary:hover` 声明恢复生效，次要按钮 hover 背景色不再缺失。变量总数：216 → 213。

**修正此前一处误判**：`--glow-intensity` 并非冗余，它被 `palette.css` 自身消费（`:185`–`:187` 的 `--sentiment-*-glow` 共 3 处），**必须保留**。上一版扫描因排除定义文件自身而漏判。

**待决策：`--login-input-toggle-*` 等 13 个变量。**

UI 运行时无消费，唯一引用来自 `apps/hrs-web/tests/login-theme-tokens.test.ts` 的 `REQUIRED_LOGIN_TOKENS` 清单。

该测试**当前即为失败状态，且与本次改动无关**：它读取 `src/style/index.css` 并用正则抽取 `:root` / `.dark` 块，但这些 token 定义在 `palette.css` 中，且 index.css 里不存在 `.dark` 块（`darkMatch` 为 `null`）。属于失效测试，未提供有效保护。

可选处理：

1. 保留变量 + 修正测试读取路径（改为解析 `palette.css`）—— 保留保护意图
2. 删除变量 + 同步清理测试清单条目 —— 彻底清理
3. 维持现状

**调色板文档同步提示**：`palette-viewer.html` 的清单数组（735、771、838、839、893–896 行等）仍列有本次删除的 4 个变量。该文档自带独立 `:root` 变量副本，展示不受影响，但两者已不同步。

> `--danger` 曾被初版扫描误判为无引用，实际被 `tailwind.config.js` 引用 3 次（`danger`、`danger-dim`、`danger-glow`），**必须保留**。

---

## 8. 验证方式

1. **产物对比**：精简后用同一套 `compile()` 实验重跑，diff 前后产物 CSS —— 除被删类自身外应完全一致。
2. **构建校验**：`cd apps/hrs-web && npm run lint && npm run build`。
3. **配置加载校验**：`node --input-type=module -e "await import('file://'+process.cwd()+'/tailwind.config.js')"`（第一批删除后已验证通过，无语法错误）。

### 已知验证缺口

- `npx vite build` 在本环境被 watch 检测中断，未能拿到 `dist` 产物。
- 因此**产物对比只做到了 Tailwind 编译层，未覆盖 Vite / SCSS 全链路**。后续批次落地时必须补跑完整 `npm run build`。
- 唯一 lint 提示：`hsl-inline.css:17` 的 `Unknown at rule @theme`，为 VSCode 内置 CSS linter 不识别 Tailwind v4 指令所致，**改动前既有**，非本次引入。

---

## 9. 不稳定因素

- `rounded-3xl` 的 2 处引用中有 1 处在临时文件 `src/pages/LoginPage/2929139019 copy.tsx`；`borderRadius.3xl` 另 1 处在 `LoginCard.tsx`。
- `bg-surface-2` 曾有 1 处引用在临时文件 `src/components/common/123123copy.tsx`（已随本次删除失效，无需处理）。
- 上述临时文件清理后，若 `rounded-3xl` 剩余引用 ≤ 1 处，届时可从保留清单再剔除 `borderRadius.3xl`。
