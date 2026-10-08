# 前端文件与目录命名规范（行业通用基准）

> 适用范围：React + TypeScript + Vite 前端工程（`src` 目录）。
> 制定依据：**行业 / 社区通行做法**，不依赖任何项目内部约定。主要参考：
> - React 官方风格与 JSX 命名惯例（组件名 PascalCase）
> - Airbnb JavaScript / React ESLint 规则（`react/jsx-pascal-case` 等）
> - Vite / Next.js 社区目录惯例（分组目录小写 / kebab-case）
> - `eslint-plugin-unicorn` 的 `filename-case` 社区实践
> - TypeScript 社区对类型 / 模块文件的 camelCase 约定
>
> **本规范目的**：统一「后续新建文件 / 新建文件夹」的命名，避免随意性。下文「总览表」给出速查，「各目录详解」给出可操作的创建规则。

---

## 一、核心规则（一句话）

- **组件（会被 JSX 渲染的值：UI 组件、Context）= PascalCase**；
- **`pages/` 目录例外**：其下文件与子文件夹统一 **camelCase（首字母小写驼峰）且以 `Page` 结尾**，用于与路由注册对应（如 `reviewPage.tsx`、`loginPage/`）**；
- **其余一切模块（hook / util / type / store / api / 常量 / 路由 / 配置）= camelCase**；
- **分组目录（放多个同类文件的文件夹）= lowercase（单字）或 kebab-case（多词）**；
- **仅“与单一 PascalCase 组件同名的协同目录”才用 PascalCase**（如 `Chip/Chip.tsx`）；
- **禁止文件名仅大小写不同**（macOS 大小写不敏感，CI/Linux 会冲突）。
- **基于以上规则补充：`hooks/`下新建文件必须以 `use` 开头，例：`useCachedState.ts`；`pages/`下新建文件和子文件夹必须以 `Page` 结尾，例：`pages/homePage.tsx`；`stores/`下新建文件和子文件夹必须以 `Store` 结尾，例：`stores/authStore.ts`**

---

## 二、src 目录总览表（在各目录下创建内容的规范）

> 图例：✓ 现状已符合 ｜ ⚠️ 现状存在违规，需整改。
> “强制”= 必须遵照，建议纳入 ESLint 长期约束；“推荐”= 社区主流、可微调。

| 目录（名称） | 类别 | 文件类型 | 在该目录创建内容的命名规范 | 强制/推荐 | 仓库现状 |
|---|---|---|---|---|---|
| `components/` | UI 组件 | `.tsx` | 组件文件 **PascalCase**，如 `Modal.tsx` / `HrsButton.tsx` | 强制 | ✓ 一致 |
| `pages/` | 页面 / 路由组件 | `.tsx` | 文件与子文件夹统一 **camelCase + `Page` 后缀（首字母小写驼峰）**，如 `reviewPage.tsx`、`loginPage/` | 强制 | ⚠️ 现有 `DocsPage/` `ErrorPage/` `LoginPage/` 文件夹需改 `docsPage/` `errorPage/` `loginPage/`；`reviewPage.tsx` 已符合 |
| `contexts/` | React Context | `.tsx` | Context 文件 **PascalCase**，如 `UiLanguageContext.tsx` | 强制 | ✓ 一致 |
| `hooks/` | 自定义 Hook | `.ts` | **camelCase 且必须以 `use` 开头**，如 `useCachedState.ts` | 强制 | ✓ 一致 |
| `utils/` | 工具 / 函数 | `.ts` | **camelCase**，如 `stockCode.ts` / `format.ts` | 强制 | ✓ 一致 |
| `types/` | 类型声明 | `.ts` | **camelCase**，如 `analysis.ts` | 强制 | ✓ 一致 |
| `stores/` | 状态 Store | `.ts/.tsx` | **camelCase**（`xxxStore.ts` 或 `useXxxStore.ts`），如 `themeStore.ts` | 强制（依“其余 camelCase”） | ⚠️ 5 个 PascalCase 需改名 |
| `constants/` | 常量 | `.ts` | 文件 **camelCase**；常量值 **UPPER_SNAKE_CASE**，如 `API_BASE_URL` | 推荐 | ✓ 一致 |
| `api/` | API / 服务 | `.ts` | **camelCase**，如 `sectorData.ts` | 强制 | ✓ 一致 |
| `router/` | 路由配置 | `.ts/.tsx` | **camelCase**，如 `appRouter.ts` / `asyncRouteFactory.ts` | 强制 | ✓ 一致 |
| `style/` | 样式 | `.css/.scss` | **kebab / lowercase**；CSS Module 用 `Component.module.css` | 推荐 | ✓ 一致 |
| `assets/` | 静态资源 | 资源本身 | 跟随资源类型，**lowercase / kebab**，如 `logo.svg` | 推荐 | ✓ 一致 |
| `i18n/` `locales/` | 多语言文案 | `.ts` | 特殊：按语言代码命名（如 `uiText-zh.ts`），遵循 i18n 库约定 | 特殊 | ✓ 一致 |
| `__tests__/`（或就近 `*.test.tsx`） | 单元测试 | `.test.ts(x)` | 基础名 **camelCase**，与源同目录或放 `__tests__/` | 强制 | ✓ 一致 |
| 各目录 `index.ts` | 桶文件 | `.ts` | 固定小写 `index.ts` | 推荐 | ✓ 一致 |

---

## 三、各目录创建规范详解（新建文件 / 新建子文件夹）

下文对 `src` 下每个主要目录，分别说明**「在里面新建一个文件」**和**「在里面新建一个子文件夹」**的命名要求与示例。

### 3.1 `components/`（UI 组件）
- **新建文件（单个组件）**：组件文件 = `PascalCase.tsx`（首字母大写驼峰），强制。例：`components/Modal.tsx`、`components/HrsButton.tsx`、`components/Chip.tsx`。
- **新建子文件夹**，分两种情况：
  - **情况一：仅分组 / 分类**（文件夹内放多个相关组件）：用 **kebab-case（首字母小写 + 横杠）**；内部组件文件仍是 `PascalCase.tsx`。例：`components/decision-signals/SignalCard.tsx`、`components/market-review/ReviewCard.tsx`。
  - **情况二：组件协同目录**（文件夹内只放「一个组件」及其私有子组件 / 样式）：用 **PascalCase（首字母大写驼峰）**，文件夹名等于组件名，内部同名 `PascalCase.tsx`。例：组件 `Chip` → 文件夹 `components/Chip/`，内部文件 `components/Chip/Chip.tsx`、`components/Chip/Chip.module.css`。
- ⚠️ 现状：`components/StockSearch/`（PascalCase 分组，应为 kebab）、`components/indexCard/`（camelCase 分组，应为 kebab）违规，应改为 kebab-case。

### 3.2 `pages/`（页面 / 路由组件）

> **特殊规则（覆盖通用组件规则）**：`pages/` 下的文件与子文件夹一律 **camelCase（首字母小写驼峰）且以 `Page` 结尾**，**不采用 PascalCase**。原因：页面需与路由注册对应，统一 camelCase + `Page` 后缀便于识别与路由匹配。

- **新建文件**：页面 = `camelCase + Page` 的 `.tsx`，强制。例：`pages/reviewPage.tsx`、`pages/loginPage.tsx`、`pages/errorPage.tsx`。
- **新建子文件夹**：页面协同目录（页面需私有子组件 / 样式）同样 **camelCase + Page**，内部页面文件仍 `xxxPage.tsx`；其私有子组件按组件规则用 PascalCase。例：文件夹 `pages/loginPage/`，内部 `pages/loginPage/loginPage.tsx` + 私有组件 `pages/loginPage/components/LoginForm.tsx`。
- 路由页一律**命名导出**，禁止 default export。

### 3.3 `hooks/`（自定义 Hook）
- **新建文件**：`camelCase.ts` 且**必须以 `use` 开头**，强制。例：`hooks/useCachedState.ts`、`hooks/useStockSearch.ts`。
- **新建子文件夹**：仅当要分组多个相关 hook 时，用 **kebab-case**，内部文件仍 `useXxx.ts`。例：`hooks/use-field-demo/useField.ts`。

### 3.4 `utils/`（工具 / 函数）
- **新建文件**：`camelCase.ts`，强制。例：`utils/stockCode.ts`、`utils/format.ts`。
- **新建子文件夹**：分组用 **kebab-case**，内部文件仍 `camelCase.ts`。例：`utils/date/parseDate.ts`、`utils/number/formatPercent.ts`。

### 3.5 `api/`（API / 服务封装）
- **新建文件**：`camelCase.ts`，强制。例：`api/sectorData.ts`、`api/index.ts`。
- **新建子文件夹**：分组用 **kebab-case**，内部文件 `camelCase.ts`。例：`api/market/quote.ts`。

### 3.6 `stores/`（状态管理，如 Zustand）
- **新建文件**：`camelCase.ts`（推荐 `xxxStore.ts` 或 `useXxxStore.ts`），强制。例：`stores/themeStore.ts`、`stores/authStore.ts`。
- **新建子文件夹**：分组用 **kebab-case**。例：`stores/user/profileStore.ts`。
- ⚠️ 现状：5 个文件用 PascalCase（`AuthStore`/`LayoutStore`/`MenuStore`/`PageStateStore`/`RouterStore`），按「其余 camelCase」原则应改为 `authStore` 等。

### 3.7 `contexts/`（React Context）
- **新建文件**：`PascalCase.tsx`，强制。例：`contexts/UiLanguageContext.tsx`。
- **新建子文件夹**：单一 Context 协同 → **PascalCase**；多个相关 Context 分组 → **kebab-case**。

### 3.8 `types/`（类型声明）
- **新建文件**：`camelCase.ts`，强制（仅类型 / 接口，无运行时代码）。例：`types/analysis.ts`。
- **新建子文件夹**：分组用 **kebab-case**。例：`types/stock/quote.ts`。

### 3.9 `constants/`（常量）
- **新建文件**：`camelCase.ts`；文件内的常量值用 **UPPER_SNAKE_CASE**。例：`constants/index.ts` 中 `export const API_BASE_URL = '...'`。
- **新建子文件夹**：分组用 **kebab-case**。

### 3.10 `router/`（路由配置）
- **新建文件**：`camelCase.ts` / `.tsx`，强制。例：`router/appRouter.ts`、`router/asyncRouteFactory.ts`。
- **新建子文件夹**：分组用 **kebab-case**。

### 3.11 `style/`（样式）
- **新建文件**：**kebab / lowercase**；CSS Module 必须用 `Component.module.css`（组件名 PascalCase + `.module.css`）。例：`style/global.scss`、`style/Button.module.css`。
- **新建子文件夹**：按功能分组用 **kebab-case**。

### 3.12 `assets/`（静态资源）
- **新建文件**：跟随资源类型，**lowercase / kebab**。例：`assets/logo.svg`、`assets/icon-arrow.png`。
- **新建子文件夹**：分组用 **kebab-case**（`assets/icons/`）。

### 3.13 `i18n/` 与 `locales/`（多语言文案）
- 特殊目录，**不适用上面的组件 / 模块规则**：文案文件按语言代码命名（如 `uiText-zh.ts`、`uiText-zh-Hant.ts`、`uiText-en.ts`），遵循所用 i18n 库的约定，保持现有模式即可。

---

## 四、文件夹推荐原则与通用子目录规则

**文件夹推荐原则（总纲）**：
- **存放单个组件的组件根目录（协同目录）**：`PascalCase`，如 `Button/`、`Chip/`。
- **业务页面、分类目录（`pages`、`utils`、`hooks`、`api` 等）**：优先 `kebab-case`（全小写 + 横杠）。

> 说明：上述第二条为「优先推荐」。实际落地时，`pages/` 当前按 3.2 的显式例外走 **camelCase + `Page` 后缀**；是否改回 kebab 与本条对齐，**本规范暂不处理（待定）**。

在 `components/`、`utils/`、`api/`、`stores/` 等任何「分组目录」下再建子文件夹，按**用途**二选一：

| 子文件夹用途 | 命名 | 示例 | 依据 |
|---|---|---|---|
| 分组型（放多个同类文件 / 组件） | **kebab-case**（多词）/ **lowercase**（单字） | `components/decision-signals/`、`utils/date/` | Vite / Next 社区目录惯例 |
| 组件协同型（只放一个同名组件 + 私有文件） | **PascalCase**（与组件同名） | `components/Chip/Chip.tsx` | React co-location 惯例 |

判定口诀：**“装一堆同类的”用 kebab；“只侍奉一个组件的”用 PascalCase**（注：`pages/` 目录当前走 camelCase + `Page` 后缀，见 3.2，待定是否并入 kebab）。**

---

## 五、跨平台合规红线（必须执行）

- **禁止仅用大小写差异命名文件 / 目录**（如 `StockSearch/` 与 `stocksearch/`、`ReviewPage.tsx` 与 `reviewpage.tsx`）。
  - 原因：macOS 默认 APFS **大小写不敏感**，本地能跑，Linux CI（大小写敏感）上 `git clone/checkout` 会冲突或漏文件，导致构建失败。
  - 做法：重命名一律用 `git mv`；若新旧名仅大小写不同，先 `git mv` 到临时名，再 `git mv` 到目标名。

---

## 六、长期固化（可选但建议）

在 `eslint.config.js` 增加 `unicorn/filename-case`，按扩展名分流：
- `.tsx`（组件 / Context，不含 `pages/`）→ `pascal-case`
- `.ts`（非测试、非 `index.ts`）→ `camel-case`
- 例外白名单：`__tests__/`、`index.ts`、`*.test.ts(x)`、`.config.*`、`demo/`、`pages/`（走 camelCase + `Page` 后缀）

配合 `react-refresh` 插件要求组件文件仅导出组件。

---

## 七、本仓库整改清单（基于上表“仓库现状”）

| # | 整改项 | 目标 | 影响面 | 建议 |
|---|---|---|---|---|
| 1 | `src/pages/DocsPage/`、`ErrorPage/`、`LoginPage/` 等 PascalCase 页面文件夹 | 改为 camelCase + `Page`：`docsPage/`、`errorPage/`、`loginPage/` | 中（路由与 import 引用） | 与路由注册改造一并处理 |
| 2 | `src/components/indexCard/` | `index-card/` | 中 | `git mv` |
| 3 | `src/components/StockSearch/` | `stock-search/` | 中 | `git mv` |
| 4 | 5 个 PascalCase store：`AuthStore`/`LayoutStore`/`MenuStore`/`PageStateStore`/`RouterStore` | 改 camelCase：`authStore`/`layoutStore`/`menuStore`/`pageStateStore`/`routerStore` | 大（大量 import） | 单独 PR，配 codemod 批量改 import |
| 5 | （可选）`eslint.config.js` 加 `unicorn/filename-case` | — | — | 长期约束，配白名单 |

> 备注：`components/kline/` 为单字小写，本身合规；其下 `KLineChart.tsx` 组件名 PascalCase 合规，无需改动。`reviewPage.tsx` 已符合新页面规则（camelCase + `Page`），无需改动。
