# Palette Viewer（调色盘参数可视化）

把 `apps/hrs-web/src/style/palette.css` 的 CSS 设计令牌（主题变量）生成一个静态 HTML 对照表，
帮助开发者直观感知每个参数的**作用**与**具体颜色表现**。

**触发场景**：用户提到 `palette.css`、设计令牌、主题变量看不懂/想可视化、要做参数对照表、
想看 light/dark 主题下各变量的真实取值与色块，或要做本项目参数与 HeroUI 同名参数的冲突比对。

## 输入

- 源文件：`apps/hrs-web/src/style/palette.css`（`:root` = 浅色，` .dark` = 深色，含 HSL 分量与嵌套 `var()` 引用）。
- 关联文件：`apps/hrs-web/src/style/index.css`（`@import "./palette.css"`，且其 `:root` 中若干 HeroUI 同名冲突变量被注释，浅色值需从此处取回）。
- HeroUI v3 默认主题变量（light/dark 实际声明，使用 `oklch()` / 自包含颜色），用于「HeroUI比对」页。

## 产物

- 输出文件：与源文件同目录，即 `apps/hrs-web/src/style/palette-viewer.html`。
- 纯静态 HTML（内联 CSS 变量 + 原生 JS），浏览器直接打开即可，无需构建。

## 页面结构

### 全局 Header
- 顶部 sticky header，内含两个 nav 页签（互斥切换）：
  1. `调色盘参数`
  2. `HeroUI比对`
- 右上角全局主题切换按钮：`🌙 深色 (Dark)` / `☀️ 浅色 (Light)`，挂在 `<html class="dark">` 上，全局生效。
- 切换主题后，所有表格的参数值、RGBA、颜色块必须**自动重算刷新**（用 `getComputedStyle` 实时取值 + `requestAnimationFrame` 后重渲染）。

### 一、调色盘参数页
1. 文件标题 + 副标题（讲清作用：`palette.css` 由 `index.css` 经 `@import` 引入，是主题令牌核心来源；颜色参数显示色块+RGBA，非颜色参数仅显示原始值）。
2. Tab 页签：`颜色参数` / `非颜色参数`，切换时表格与对应搜索框联动。
3. 每个 Tab 各有一个搜索框，按**参数名称**实时筛选、刷新表格；无结果显示「无匹配参数」。
4. 表格列要求：
   - **颜色参数 Tab**：序号、类型（颜色/非颜色）、所属风格（浅色/深色）、参数名称、参数含义（中文）、参数值、参数值 RGBA、颜色块。
   - **非颜色参数 Tab**：序号、类型（颜色/非颜色）、所属风格（浅色/深色）、参数名称、参数含义（中文）、参数值（无 RGBA / 颜色块列）。
   - 「所属风格」列显示当前激活主题（浅色/深色）。

### 二、HeroUI比对页
1. 文件标题 + 副标题（讲清作用：本项目 `index.css`/`palette.css` 的同名变量位于 `@layer` 之外（unlayered），优先级恒高于 HeroUI theme layer，会**单向覆盖** HeroUI 同名变量；本页显性比对本项目覆盖后的色差/失效）。
2. 搜索框，按参数名称筛选、刷新表格。
3. 表格列：序号、所属风格（浅色/深色）、参数名称、参数含义（中文）、HRS的参数值、HRS颜色块、HeroUI的参数、HeroUI颜色块（左右并排对照）。

## 关键实现要点（已踩坑，必须遵守）

### 1. 内联变量定义，light 缺值需补回
- HTML 内联 `palette.css` 完整的 `:root`（浅色）与 `.dark`（深色）变量块，颜色块用 `background: var(--xxx)` 渲染，浏览器自动解析嵌套 `var()`、`hsl(var())`。
- 浅色 `:root` 中 `--background/--foreground/--border/--muted/--accent` 在源文件被注释，需按 `index.css` 注释里的浅色值补回（如 `--background: 216 33% 97%`），否则浅色下这些变量未定义、相关色块失效。

### 2. 裸 HSL 分量必须补 `hsl()`
- 形如 `--primary: 193 100% 43%` 是 HSL **分量**，浏览器不能直接当颜色，必须包成 `hsl(193 100% 43%)`。
- 渲染前用正则 `/^[\d.]+(?:\s+[\d.]+%){2,3}$/` 判裸分量；是则补 `hsl(...)`，否则（含 `hsl()`/`var()`/`#`/`linear-gradient`）原样交给浏览器。

### 3. RGBA 转换
- 颜色参数需显示「参数值 RGBA」：用隐藏 probe 元素把任意颜色声明解析成浏览器实色 `rgb()/rgba()` 再读取显示（如 `hsl(193 100% 43%)` → `rgb(0, 182, 196)`）。
- probe 解析回退：`getComputedStyle(probe).backgroundColor`，避免直接显示未解析的裸分量。

### 4. HeroUI 的 oklch 必须显式转 rgb（重要，否则画成纯黑）
- HeroUI 值形如 `oklch(0.205 0 0)`（L=0.205 是深灰，不是纯黑）。**绝不能**直接塞进 `background`——一旦环境对 oklch 解析异常会回退成无效色（视觉接近纯黑），造成「0.205 深灰被画成纯黑」的视觉不匹配。
- 必须在 JS 内实现 `oklchToRgb()`（标准 oklch→线性 sRGB 矩阵转换，含 `oklch(L C H / alpha%)` 的 alpha 处理），再用统一出口 `toDisplayColor()`：含 oklch→转 rgb，其余原样。HeroUI 色块统一走 `toDisplayColor()`。
- 参考转换公式（Björn Ottosson oklab 矩阵）：
  - `a = C*cos(H°)`, `b = C*sin(H°)`；`l_ = L+0.3963377774a+0.2158037573b`；`m_ = L-0.1055613458a-0.0638541728b`；`s_ = L-0.0894841775a-1.2914855480b`
  - `l=l_³, m=m_³, s=s_³`
  - `R=4.0767416621l-3.3077115913m+0.2309699292s`；`G=-1.2684380046l+2.6097574011m-0.3413193965s`；`Bl=-0.0041960863l-0.7034186147m+1.7076147010s`
  - 线性→gamma sRGB：`x<=0.0031308 ? 12.92x : 1.055*x^(1/2.4)-0.055`，clamp 后 `*255` 取整。

### 5. 列宽约束
- 参数含义列最宽（`min-width` 约 320px），参数名称次之（约 250px），其余（序号 48 / 类型 84 / 风格 84 / 参数值 220 / RGBA 170 / 颜色块 70）等宽，**各列宽差异不能太大**。

### 6. 数据维护
- 每个参数需配中文含义与分组标签（Base/Color/Sentiment/Design/Nav/Home/Shadow/Settings/Chat/Backtest/Login/Font 等），标记 `isColor`（颜色 vs 非颜色：圆角/辉光半径/阴影/渐变/字体栈/高度/内边距为非颜色）。
- 非颜色值（`--radius`、`--glow-spread`、`--glow-intensity`、`--nav-item-height`、`--nav-item-padding-x`、所有 `--shadow-*`、`--gradient-primary`、`--*-shadow`、`--home-rail-bg`、`--home-history-item-selected-bg`、`--font-mono` 等）不渲染颜色块，显示「非颜色」。

## 交付说明
- 本文件是**预览/文档工具**，与 `palette.css` 非自动同步；若源文件增删/修改变量或含义，需同步更新 HTML 内联变量块与 `VARS`/`HEROUI` 数据数组。
- HeroUI 深色调取值取自其默认主题 `themes/default/variables.css`，若团队锁定不同版本需微调 `HEROUI` 数组的 light/dark 值。
- 纯静态 HTML，交付时说明用浏览器直接打开 `apps/hrs-web/src/style/palette-viewer.html` 验证；无需 dev server。
