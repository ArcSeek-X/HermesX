---
name: i18n-naming-skill
description: 前端 i18n 多语言管理规范。统一 `apps/hrs-web/src/i18n/` 三语主字典的 key 命名、八大类别前缀契约、字典排列顺序与新增文案流程。
---

# i18n 多语言管理规范

> 适用范围：`apps/hrs-web/src/i18n/` 三语主字典（`uiText-zh.ts` / `uiText-zh-Hant.ts` / `uiText-en.ts`，经 `uiText.ts` 聚合为 `UI_TEXT`，由 `UiLanguageContext.t()` 消费）。
>
> 本规范对**新增文案强制生效**；存量 key 不统一改名，通过「登记表 + 渐进迁移」管理。

## 三语主字典文件（i18n 数据真源）

全站界面文案的**唯一数据真源**是 `apps/hrs-web/src/i18n/` 下的三个主字典文件。三者由 `uiText.ts` 聚合成 `UI_TEXT`，再由 `UiLanguageContext.t()`（业务代码通过 `useUiLanguage()` 取 `t`）消费；类型系统 `Record<UiLanguage, Record<UiTextKey, string>>` 强制三语 key 集合对齐（缺任何一语即编译报错）。

| 文件                  | 语言             | 角色与功能边界                                                                                                                                                                                                        |
| ------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `uiText-zh.ts`      | 简体中文（zh）     | **所有 key 的真源（source of truth）**。新增 / 删除 key 必须先改此文件；`UiTextKey` 类型由本文件推导，另两语必须补齐完全相同的 key 集合，否则类型编译失败。每个 key 必须附行尾中文注释说明用途。                                                          |
| `uiText-zh-Hant.ts` | 繁体中文（zh-Hant） | 繁体译本。**必须是真繁体**，不允许用简体或拼音替代。key 集合与排列顺序必须与 `uiText-zh.ts` 完全一致。                                                                                                                              |
| `uiText-en.ts`      | 英文（en）        | 英文译本。key 集合与排列顺序必须与 `uiText-zh.ts` 完全一致。                                                                                                                                                  |

功能边界要点：

- 三者**只承载 `key → 文案` 的纯数据映射，不含任何逻辑**；聚合、类型推导与语言消费统一在 `uiText.ts` 完成，组件不得绕过 `t()` 直接引用某个语言文件。
- **语义定义权归 `uiText-zh.ts`**：`zh` 文件是 key 唯一权威来源，另两语仅做等值翻译，不得新增 / 删减 key，亦不得改变 key 名。
- 三语文件**必须保持完全相同的排列顺序**（见 §4），否则跨语言 diff 无法对照、review 难比对。
- 强业务域、且繁体需求弱的文案不进三语主字典，而是走业务字典（见 §5）；但本规范仍以三语主字典为**唯一权威真源**，业务字典不得与之重复定义通用 UI 文案。

## 1. 总则

1. 全站界面文案必须走 i18n 字典，**禁止在组件中硬编码用户可见文案**（含 `document.title`、`title` 属性、`alert()` 等）。
2. `uiText-zh.ts` 是所有 key 的**真源（source of truth）**，新增/删除 key 必须三语文件同步修改（类型系统会强制校验）。
3. 繁体必须是**真繁体**，不允许用简体或拼音替代。
4. 每个 key 在字典文件中必须附行尾中文注释，说明用途。
5. 新增 key 前必须先检索现有 key，禁止同义重复（如已有 `common.cancel`，不得再造 `common.cancelBtn`）。
6. 加入到全局 `common.` 的内容必须严谨，必要情况下需要二次确认，以免污染全局。

## 2. 八大类别与 key 前缀契约

| # | 类别        | key 前缀                                                              | 覆盖范围                                                                           | 现状（截至 V1.8）                                                                                              |
| - | --------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| 1 | 全局 common | `common.*`                                                          | 通用动作/状态/占位符：取消、确认、加载、暂无数据、重试等普适文案                                              | 27 key，合规                                                                                                |
| 2 | 语言类别      | `language.*`                                                        | 语言切换、语言名称、语言简写                                                                 | 9 key，合规                                                                                                 |
| 3 | 主题类别      | `theme.*`                                                           | 主题切换、主题模式、主色设置                                                                 | 9 key，合规                                                                                                 |
| 4 | 布局与菜单     | `layout.*`（含 `layout.header.*` / `layout.nav.*`）                    | 侧边栏、导航框架、一二级菜单（`layout.nav.`）、头部操作区（`layout.header.`）                        | 62 key 含 `layout.nav.*` 34（17 项 × title/description）+ `layout.header.*` 3 + 布局直属；另有存量 `header.` 3 key 待迁入 `layout.header.` |
| 5 | 组件类别      | `component.<组件名>.<具体内容>`                                            | 基础组件、业务组件、通用组件的内部文案                                                            | `component.runFlow.*` 106 / `component.taskPanel.*` 14 / `component.StockSearch.*` 1；存量 `stockBar.` 5 待迁 |
| 6 | 异常页面      | `exception.*`                                                      | 框架级异常路由的路由级标题与描述：404 路由、重定向路由（区别于 `notFound.*`/`routeError.*` 页面内容） | 4 key（`exception.404.*` 2 + `exception.redirect.*` 2）；本会话新增                                                            |
| 7 | 登录/注册     | `auth.login.*`、`auth.register.*`（预留）                                | 登录页、初始密码设置页、注册页                                                                | 27 key（`auth.login.*`；本会话新增 title/description）；**V1.1 已由存量** **`login.`** **迁移完成**                       |
| 8 | 页面类别      | `<路由名>.<一级功能>[.<二级>]`                                               | 各页面专属文案                                                                        | 存量已基本合规；新增 `liveNews.` 18 key                                                                            |

> 编号说明：V1.1 相对 V1.0 调整了第 4/5/6 类的编号——布局与菜单为第 4 类、组件为第 5 类、登录注册为第 6 类；V1.8 新增第 6 类「异常页面」，原第 6/7 类顺延为第 7/8 类（登录注册 / 页面）。

## 3. 命名细则

### 3.1 通用规则

- 分隔符统一为 `.`；每段使用 camelCase（数字/缩写保留原样，如 `1m`、`5d`）。
- key 层级上限 **4 段**。
- 末段描述具体语义，推荐使用固定词表：`title` / `description` / `placeholder` / `hint` / `emptyTitle` / `emptyDescription` / `errorTitle` / `loading` / `submit` 等。

### 3.2 异常页面类别（第 6 类）

- 前缀：`exception.*`，覆盖框架级异常路由的**路由级**标题/描述。这些文案以 i18n key 形式直接挂在 `AsyncRouteNode.routerName` / `routerDescription` 上——白名单 / 异常路由见 `router/Whitelist.ts` 的 `WHITE_LIST_ROUTE_MANIFEST`，业务路由由 `RouterStore.buildAsyncRouterData()` 从 `MENU_MANIFEST` 映射得到；再经 `AppContent.tsx` 的 `buildRoute` 注入路由 `handle` 的 `menuName` / `description`，由 `t()` 在渲染期解析为对应语言文案。**本类不再依赖已移除的 `routeMeta.ts`**。
- 当前两项：`exception.404.*`（404 路由）、`exception.redirect.*`（根路径重定向路由）。
- 与 `notFound.*` / `routeError.*`（第 8 类 页面，由 `NotFoundPage` / `RouteBoundary` 作为**页面内容**消费）分工明确：本类为路由元数据，后者为页面正文，二者不混用、不重复。

### 3.3 页面类别（第 8 类）

- 路由名 = 路由 path 段的 camelCase，一段路由对应一个前缀。
- 一级：`<路由名>.<一级>`，例：`kline.title`
- 二级：`<路由名>.<一级>.<二级>`，例：`kline.period.1m`
- 页面专属文案必须挂页面命名空间，不得散落到 `common.`

**路由 → key 前缀对照表（举例）：**

| 路由前缀                          | 页面                | 备注                                                |
| ----------------------------- | ----------------- | ------------------------------------------------- |
| `home.*`                      | 首页                | 当前主字典无该命名空间                                       |
| `review.*`                    | 复盘（每日选股分析）        | 54 key                                            |
| `watchlist.*`                 | 自选                | 38 key                                            |
| `kline.*`                     | 个股 K 线            | 43 key                                            |
| `liveNews.*`                  | 实时财经快讯            | 18 key                                            |
| `usage.*`                     | 用量                | 36 key                                            |
| `settings.*`                  | 设置                | 275 key                                           |
| `chat.*`                      | 问股                | 25 key                                            |
| `decisionSignals.*`           | AI 建议             | 206 key                                           |
| `sector.*`                    | 板块分析              | 9 key；对照表原写作 `sectorAnalysis.`，以字典实际 `sector.` 为准 |
| `history.*`                   | 分析历史              | 19 key                                            |
| `stockTrend.*`                | 个股趋势              | 32 key                                            |
| `stockCloud.*`                | 个股云图              | 预留                                                |
| `codeTest.*`                  | 测试页               | 当前主字典无该命名空间（V1.4 前曾为 `layout.route.codeTest.*`，V1.5 已删除） |
| `notFound.*` / `routeError.*` | 404 / 路由错误（页面内容）    | 各 4 key；路由级 handle 见第 6 类 `exception.*`            |

### 3.4 组件类别（第 5 类）

- 格式：`component.<组件名>.<具体内容>`
- **新增组件命名空间统一使用 camelCase**，示例：`component.runFlow.drawerTitle`、`component.taskPanel.title`
- 仅被单一组件使用的文案挂组件命名空间；被 ≥2 个页面/组件复用的文案，上提到 `common.`（普适语义）或抽为独立组件命名空间。**为确保** **`common.`** **纯粹性，上提到** **`common.`** **需确认审核。**

### 3.5 登录/注册类别（第 7 类）

- 登录：`auth.login.*`（含路由级 `auth.login.title` / `auth.login.description`，见第 6 类路由 handle 复用约定）
- 注册：`auth.register.*`（当前页面无实现，前缀预留，实现时直接按新规范落地）

### 3.6 布局与菜单类别（第 4 类）子域划分

第 4 类内部按**布局语义**划分为四个子域：

| 子域    | key 前缀            | 说明                     | key 数 |
| ----- | ----------------- | ---------------------- | ----- |
| 布局直属  | `layout.<直属>`     | 侧边栏折叠/展开、登出、兜底标题等框架级文案 | 13    |
| 头部操作区 | `layout.header.*` | 头部主题设置、语言、用户设置         | 3     |
| 导航菜单  | `layout.nav.<项>.title` / `.description` | 侧边栏菜单项；每项含名称与描述，17 项 → 34 key | 34    |

**`layout.nav` 与顶栏标题的分工**：

- `layout.nav.<项>.title/description`：**侧边栏菜单项**的名称与描述，**同时作为路由顶栏标题/描述**。
- 历史上存在独立的 `layout.route.*`（路由级顶栏标题/描述，32 key，V1.5 删除），经核查无任何业务代码引用，属于死代码。
- `ShellHeader.tsx` 的 `TITLES` 路由映射**统一取 `layout.nav.*`**，菜单与顶栏共用同一套文案，避免两处维护。
  ⚠️ 因此新增菜单项时须同步登记进 `TITLES`，否则该路由的顶栏会回退到兜底标题。

## 4. 字典文件内的排列顺序

新增/整理 key 时必须遵循本节顺序，使三语文件保持可对照的、稳定的结构。

### 4.1 大类之间

按第 1 → 8 类顺序排列；每个大类以 `// ---- 类别名 ----` 分组注释起始。

### 4.2 大类内部排序依据

| 类别             | 排序依据                                                                     | 理由                                                      |
| -------------- | ------------------------------------------------------------------------ | ------------------------------------------------------- |
| 第 1 类 common   | 命名空间字母序 A–Z                                                              | 仅 `common`，组内 key 再按字母序                                 |
| 第 2 类 language | 命名空间字母序 A–Z                                                              | 仅 `language`                                            |
| 第 3 类 theme    | 命名空间字母序 A–Z                                                              | 仅 `theme`                                               |
| 第 4 类 布局与菜单    | **布局语义顺序**：`layout` 直属 → `layout.header` → `layout.nav` | 由框架到细节、由外到内，符合阅读路径                                      |
| 第 4 类 `layout.nav` 子域内 | **按项目名聚合，项目内 `title` 在前、`description` 在后** | 字母序会把 `description` 排在 `title` 之前，不利于对照阅读；按项目聚合后同一项的名称与描述相邻 |
| 第 5 类 组件       | **组件注册名 A–Z**                                                            | 对齐 `component.<注册名>.` 契约，便于按组件定位                        |
| 第 6 类 异常页面      | 命名空间字母序 A–Z                                                              | 仅 `exception`                                            |
| 第 7 类 登录/注册    | 命名空间字母序 A–Z                                                              | 仅 `auth`                                                |
| 第 8 类 页面       | 命名空间字母序 A–Z                                                              | 页面间无稳定业务序，字母序查找最快（如 `report` < `review` < `routeError`） |

### 4.3 命名空间内部

同一命名空间下的 key 按**字母序 A–Z** 排列；存在二级/三级分类时，先按分类名聚合，再在分类内按字母序。

### 4.4 三语文件必须同序

`zh` / `zh-Hant` / `en` 三份文件必须按**完全相同的顺序**排列，否则跨语言 diff 无法对照。

> ⚠️ 类型系统（`UI_TEXT: Record<UiLanguage, Record<UiTextKey, string>>`）只强制三语 **key 集合对齐**，**不校验顺序**。顺序一致性靠本节约定与 PR review 保证。

## 5. 字典边界

| 字典            | 位置                                               | 语言                            | 适用内容                  |
| ------------- | ------------------------------------------------ | ----------------------------- | --------------------- |
| 主字典 `UI_TEXT` | `src/i18n/uiText-{zh,zh-Hant,en}.ts`             | zh / zh-Hant / en 三语齐全        | 全站通用 UI 文案（本规范八大类）    |
| 业务字典          | `src/locales/featureText.ts`、`settingsHelp.ts` 等 | 仅 zh / en，繁体经 `toCnOrEn()` 回退 | 告警/回测/组合等业务域文案、配置帮助文本 |

规则：界面框架与通用交互文案进主字典；强业务域、且繁体需求弱的文案可留在业务字典，但新增业务字典必须登记在本规范第 6 节。

> 说明：`alerts` / `backtest` / `portfolio` 等页面的业务文案走 `featureText.ts`，故主字典中**没有**对应命名空间，这是符合规范的。

## 6. 新增文案流程

### 6.1 判定类别（决策树）

1. 是否全站普适（动作/状态/占位符）？→ `common.`（需确认审核，避免污染全局）
2. 是否语言/主题/布局菜单/头部相关？→ 对应第 2/3/4 类
3. 是否仅某一组件内部使用？→ `component.<注册名>.`
4. 是否登录注册链路？→ `auth.login.*` / `auth.register.*`
5. 是否框架级异常路由（404/重定向）的路由级标题/描述？→ `exception.*`（第 6 类）
6. 以上都不是 → 页面类别 `<路由名>.`（第 8 类）

**查重**：全局搜索候选语义，禁止重复新增。

### 6.2 三语同改

- `zh` / `zh-Hant` / `en` 三份文件补同一 key，附行尾注释；缺任何一语类型编译即报错。
- **模板参数**：占位符统一 `{name}` 形式（`formatUiText` 契约）；中英文量词/单位差异在各自语言文件内处理（如 `{count}只` vs `{count} stocks`），不允许把单位写死在组件里。

## 7. 存量登记表（需要实时更新）

统计基线：2026-09-20，主字典共 **1023 key / 27 个一级命名空间**（V1.5 删除无引用的 `layout.route.*` 32 key 后；本会话新增 `exception.*` 4 key + `auth.login.title/description` 2 key）。

| 命名空间                                                                                                                                                                                                        | key 数                                                                 | 归属类别 | 合规性                                   |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ---- | ------------------------------------- |
| `common.`                                                                                                                                                                                                   | 27                                                                    | 1    | 合规，保持不动                               |
| `language.`                                                                                                                                                                                                 | 9                                                                     | 2    | 合规，保持不动                               |
| `theme.`                                                                                                                                                                                                    | 9                                                                     | 3    | 合规，保持不动                               |
| `layout.`                                                                                                                                                                                                   | 62                                                                    | 4    | 合规，保持不动                               |
| `layout.header.`                                                                                                                                                                                            | 3                                                                     | 4    | 合规（V1.1 已由 `header.*` 迁移完成）           |
| `component.runFlow.*`                                                                                                                                                                                       | 106                                                                   | 5    | 合规（V1.2 已由 `runFlow.` 迁移完成）           |
| `component.taskPanel.*`                                                                                                                                                                                     | 14                                                                    | 5    | 合规（V1.2 已由 `taskPanel.` 迁移完成）         |
| `component.LiveCalendar.*`                                                                                                                                                                                  | 12                                                                    | 5    | 合规（V1.6/V1.7 由 `liveCalendar.` 解耦：组件网格/List 内部与共享文案） |
| `stockBar.`                                                                                                                                                                                                 | 5                                                                     | 5    | **存量，待迁至** **`component.stockBar.*`** |
| `exception.*`                                                                                                                                                                                               | 4                                                                     | 6（新增） | 合规（本会话新增：404/重定向路由的 route handle 标题与描述）      |
| `auth.login.`                                                                                                                                                                                               | 27                                                                    | 7    | 合规（V1.1 已由 `login.` 迁移完成；本会话新增 title/description） |
| `chat.` / `decisionSignals.` / `history.` / `kline.` / `liveNews.` / `notFound.` / `report.` / `review.` / `routeError.` / `sector.` / `settings.` / `stockTrend.` / `stockUnit.` / `usage.` / `watchlist.` | 25 / 206 / 19 / 43 / 18 / 4 / 3 / 54 / 4 / 9 / 275 / 32 / 4 / 36 / 38 | 8    | 合规（页面/页面内组件域），保持不动                    |

**渐进迁移约定**：不为改名单独发 PR；当存量文件发生实质性重构时，可顺带迁移该文件的文案并全量替换调用点。

## 8. 验证与守护

- **现有硬约束（保留）**：`UI_TEXT: Record<UiLanguage, Record<UiTextKey, string>>` 类型强制三语 key 对齐。
- **评审约定**：PR review 时检查新增 key 的：类别归属、层级上限、注释齐全、三语齐全、**排列顺序符合第 4 节**。
- **后续事项（本规范不实现）**：在 web-gate 中补充「未使用 key 检测」脚本，定期清理死 key；补充「三语顺序一致性」检查。

## 9. 版本改动记录

| 版本   | 更新时间         | 更新内容                                                                                                                                                                                                                                                                                                                       |
| ---- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| V1.0 | `2026-08-28` | 首次定稿，确立七大类别、页面/组件命名契约、存量登记表与渐进迁移约定                                                                                                                                                                                                                                                                                         |
| V1.1 | `2026-08-29` | ① 调整第 4/5/6 类编号（布局菜单 / 组件 / 登录注册）；② 新增第 4 节「字典文件内的排列顺序」；③ 第 4 类新增 `layout.header.*` 子域与 `header.*` 迁移约定；④ 更新登记表：`login.`→`auth.login.` 迁移完成、`common` 27、`layout` 62、新增 `liveNews` 18 / `component` 1；⑤ 总则第 1 条补充禁止硬编码 `document.title` 等                                                                                   |
| V1.2 | `2026-08-29` | ① 第 5 类存量 `runFlow.` / `taskPanel.` 迁移为 `component.runFlow.*` / `component.taskPanel.*`（共 120 key），组件名统一采用 camelCase；② 修复 `NotFoundPage` 硬编码，启用已有 key `notFound.pageTitle`；③ `notFound.pageTitle` 品牌名统一为 `HermesX`；④ 新增 `alerts.pageTitle`；⑤ `uiText-zh-Hant.ts` 内部变量 `zh`→`zhHant`，并移除与 `uiText-zh.ts` 重复的 `UiTextKey` 导出 |
| V1.3 | `2026-08-29` | ① `layout.nav.*` 拆分为 `.title` / `.description` 两级，`description` 内容参考 `layout.route.*.description`（新增 17 条，繁体版使用真繁体，避免复制 route 中既有的简体残留）；② `component.StockSearch.placeholder` 由 PascalCase 统一为 camelCase（同步修改 `StockSearch.tsx` 调用点），至此第 5 类组件命名空间全部统一为 camelCase；③ 补充「改 key 大小写须同步核对调用点」的实操提醒                             |
| V1.4 | `2026-08-30` | ① `ShellHeader.tsx` 的 `TITLES` 路由映射由 `layout.route.*` 改为 `layout.nav.*`，菜单与顶栏共用同一套文案；② 新增排序细则：`layout.nav` 子域按项目名聚合，且项目内 `title` 在前、`description` 在后（字母序会导致 description 在前）；③ 明确 `layout.nav` 与 `layout.route` 的分工，以及路由未登记进 `TITLES` 时顶栏回退兜底标题的风险 |
| V1.5 | `2026-08-30` | ① 全局核查确认 `layout.route.*`（32 key）无任何业务代码引用，属死代码，已删除；② 同步更新第 4 类子域表、排序依据、存量登记表与基线计数（主字典回落至 1017 key）；③ 明确顶栏标题由 `layout.nav.*` 经 `ShellHeader.tsx` 的 `TITLES` 复用，不再保留独立 route 命名空间 |
| V1.6 | `2026-09-06` | ① 将 `liveCalendar.*` 中属于 `LiveCalendar` 网格组件内部的 7 个 key（country / importance / list.columns.time / list.columns.title / more / prevMonth / nextMonth）解耦至 `component.LiveCalendar.*`，页面级 key（title / subtitle / refresh* / degradedTip / loading / empty / emptyTab / eventsCount / selectHint / allDay / tabs.*）保留在 `liveCalendar.*`；② 三语文件同步迁移并全量替换调用点（LiveCalendar.tsx） |
| V1.7 | `2026-09-06` | ① 将继续定位为「组件层/页面与组件共享」的 5 个 key（allDay / empty / today / includeEconomicData / emptyImportance）从 `liveCalendar.*` 解耦至 `component.LiveCalendar.*`；`allDay`/`empty` 被 `LiveCalendarListView.tsx` 与 `LiveCalendarPage.tsx` 共用（按规范第 3.3 条归组件命名空间）；② 三语文件同步迁移，`liveCalendar.*` 仅保留纯页面级 key（title / subtitle / refresh* / degradedTip / loading / emptyTab / eventsCount / selectHint / tabs.*），`component.LiveCalendar.*` 由 7 增至 12；③ 注：`today` 与 `common.datetime.today`（工具栏已用）语义重复且无调用点，`includeEconomicData`/`emptyImportance` 当前亦无调用点，系按语义归入组件命名空间，待后续接线上线或清理 |
| V1.8 | `2026-09-20` | ① 新增第 6 类「异常页面」（`exception.*`，4 key：404 路由 / 重定向路由的 route handle 标题与描述），原第 6/7 类（登录注册 / 页面）顺延为第 7/8 类；② `auth.login.*` 新增 `title` / `description`（登录路由 handle），计数 25 → 27；③ 明确 `exception.*`（路由元数据）与 `notFound.*` / `routeError.*`（页面内容，仍属第 8 类）的分工；④ 各文件 `// ---- 第 N 类 ----` 分组注释同步为 1–8 编号，消除原「第 6 类」撞号冗余 |
| V1.9 | `2026-09-20` | ① 新增「三语主字典文件（i18n 数据真源）」小节，以表格 + 列表介绍 `uiText-zh.ts` / `uiText-zh-Hant.ts` / `uiText-en.ts` 三者的角色与功能边界（唯一数据真源、`zh` 为 key 权威、纯数据映射不含逻辑、三语同序、业务字典不得重复定义通用 UI 文案）；② 修正 §3.2 对 `routeMeta.ts` 的失效引用——路由级标题/描述现由 `AsyncRouteNode.routerName` / `routerDescription`（i18n key，来自 `asyncRouterData` 与白名单 manifest）经 `AppContent.tsx` 的 `buildRoute` 注入路由 `handle`、渲染期 `t()` 解析，原 `routeMeta.ts` 已移除，不再依赖 |

