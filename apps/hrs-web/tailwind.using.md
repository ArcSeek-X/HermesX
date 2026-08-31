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

即：**`borderColor` 与 `backgroundColor` 的实际渲染由 `global.scss` 决定，config 中的值仅在 dark 主题下与之一致**。`border-subtle` 有 63 处引用，改动这两个文件任一处都会影响全站边框，需联动评估。

### 2.2 其它既有代码问题（与配置无关，顺带记录）

- `hover:bg-surface-hover`（`MarketReviewRegionSelector.tsx` 3 处）：Tailwind 配置与 `global.scss` 均无 `surface-hover` 定义，是**无效类**，无任何效果。
- `animate-slide-in-left`（`Drawer.tsx`）：config 无此 animation，但 `global.scss:1469` 有手写类 + `:1458` `@keyframes slideInLeft`，**不依赖 config**。

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

**本次删除无需改动**：全文不引用 `--input`、`--ring`、`--surface-1/2/3`、`--input-surface-*`（不同前缀，无关）、`w-18`/`p-18`/`h-22`/`m-22`、`subtle-soft`/`subtle-active`。

需注意：

- 自带 `@keyframes`：`slideInRight`(228)、`spin`(239)、`zoomIn`(248)、`slideInFromTopSm`(259)、`slideInFromTopMd`(270)、`slideInFromBottomMd`(281)、`slideInLeft`(1458)；**无 `fadeIn`**，依赖 config 提供。
- 自带动画类 `.animate-fade-in`(292)、`.animate-slide-in-right`(296)、`.animate-spin`(300)、`.animate-in`(304)、`.animate-slide-in-left`(1469)。
- 第 2.1 节列出的三处同名类覆盖 Tailwind 配置，需在第三批处理。

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

判定与建议：

| 分组 | 建议 |
| --- | --- |
| `--input`、`--ring` | **保留**。palette.css 81–83 行注释说明这两个是 HeroUI/shadcn 同名变量，用于覆盖组件库默认值；删除可能导致 HeroUI 焦点环回落为库默认色。项目内无 `var()` 引用不等于无消费 |
| `--login-input-toggle-*`（12 个） | 疑似登录页改版后遗留。若确认登录页已不使用该套 toggle，可整组删除 |
| `--glow-intensity`、`--bg-hover`、`--home-mobile-overlay-bg`、`--settings-border-overlay`、`--settings-accent-shadow`、`--login-label-text`、`--login-hint-text`、`--login-input-icon` | 均出现在 `palette-viewer.html` 调色板文档中。若该文档仍作为设计交付物，建议保留（或加 `deprecated` 注释） |

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
