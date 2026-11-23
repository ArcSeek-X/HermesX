# <a id="frontend-module-menu"></a>前端模块化菜单与动态路由状态方案

> 📝 **方案简述**：本方案确立 `apps/hrs-web` 前端"菜单 + 动态路由"的数据分层与状态管理基准——以 `MENU_MANIFEST` 为唯一真源，菜单与路由共用同一份原始数据；菜单加工/持久化收敛到 `MenuStore`、动态路由树加工/持久化收敛到 `RouterStore`（均 Zustand）；白名单路由（登录页/404/兜底）不进入状态层、仅在 `appRouter.tsx` 内联声明；真源当前为本地常量，后续平滑切换为接口返回。本方案**已落地**，本文档描述当前实现状态。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-23

## 目录

- [一、背景与目标](#sec-1)
- [二、现状（已落地）](#sec-2)
- [三、设计原则](#sec-3)
- [四、总体架构](#sec-4)
- [五、真源数据设计](#sec-5)
- [六、白名单数据设计](#sec-6)
- [七、菜单状态方案（MenuStore）](#sec-7)
- [八、路由状态方案（RouterStore）](#sec-8)
- [九、数据处理流程](#sec-9)
- [十、持久化策略](#sec-10)
- [十一、文件职责与边界](#sec-11)
- [十二、约束与注意](#sec-12)
- [十三、后续演进](#sec-13)

---

<a id="sec-1"></a>

## 一、背景与目标

当前 Web 端菜单、路由、模块切换能力已从"静态写死"演进为"统一配置驱动"：路由真源暂存本地常量，后续切接口返回。本方案需同时满足：

- 菜单与路由共享同一份真源数据；
- 支持模块切换（当前真源含 `productModel` 产品模块、`developmentMode` 调试/文档模块）；
- 支持动态路由生成（登录后注入、刷新还原）；
- 白名单路由（登录页/404/兜底）单独维护、不混入动态路由状态；
- 菜单与路由的加工结果本地持久化；
- 真源从本地常量切到接口时，状态层与消费层尽量少改。

---

<a id="sec-2"></a>

## 二、现状（已落地）

- **数据路由已落地**：`App.tsx` 已用 `RouterProvider router={router}`（`apps/hrs-web/src/App.tsx:20`）装配数据路由，早期手写 `<Routes>` 的 `AppContent` 模式已退役；路由层详见 [前端异步数据路由方案](frontend_async_router.md)。
- **状态层已建**：`MenuStore.ts` 与 `RouterStore.ts` 均存在并承担加工/持久化职责。
- **废弃抽象已清除**：原规划中的 `routerFactory`、`dataFactory.ts` 已不存在；原 `Whitelist.ts` 已移除（全仓 0 引用），白名单改为在 `appRouter.tsx` 内联声明。
- **模块划分已生效**：`MENU_MANIFEST` 第一层为 `NavMenuNode[]`，当前含 `productModel`（产品）与 `developmentMode`（调试/文档）两个模块。

---

<a id="sec-3"></a>

## 三、设计原则

- **单一真源**：菜单与路由都基于同一份 `MENU_MANIFEST` 原始数据。
- **白名单独立**：白名单不混入业务动态路由状态、不入 Store、不持久化。
- **状态中心化**：数据加工、存储、编排统一进入 Zustand（`MenuStore` / `RouterStore`）。
- **结果可缓存**：加工后的菜单数据与动态路由数据允许持久化。
- **逐步演进**：现阶段兼容本地常量真源，后续平滑切换到接口真源。

---

<a id="sec-4"></a>

## 四、总体架构

整体分三层：

### 4.1 真源层

- `router/manifest.ts`（`MENU_MANIFEST`）—— 唯一真源，只承担原始数据存储，不承担加工/状态逻辑。

### 4.2 状态加工层

- `stores/MenuStore.ts` —— 从真源构建全量菜单数据、派生当前模块菜单、持久化。
- `stores/RouterStore.ts` —— 从真源构建动态路由树、持久化；注册动作下沉到 `routeRegistration.ts` 以避免反向依赖 `appRouter`。

### 4.3 消费层

- 侧边栏（`SidebarNav`）/ 应用入口（`ApplicationMenu`）分别消费 `MenuStore` 的 `currentMenuData` 与 `menuData`；
- 路由注册层（`routeRegistration.ts`）消费 `RouterStore` 的 `asyncRouteData`。

---

<a id="sec-5"></a>

## 五、真源数据设计

真源 `MENU_MANIFEST: NavMenuNode[]` 的每一层使用相同节点类型，`menuType` 仅取 `module`、`group`、`page`。当前根节点为两个 module，含 13 个 group、41 个 page。不存在另一套模块字段或模块返回对象。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `menuCode` | `string` | 所有节点的稳定业务标识，例如 `productModel`、`watchlist` |
| `menuName` / `menuDescription` | `string` | 名称与描述，支持国际化键或直写文案 |
| `menuType` | `module / group / page` | 模块、分组、页面，仅类型值不同 |
| `menuRoutePath` | `string?` | 路由路径，例如 `/watchlist`；只有 page 生成页面路由 |
| `menuPagePath` | `string?` | 前端已构建的页面模块路径，供动态导入白名单解析 |
| `menuIcon` / `menuBadge` | `string?` | 图标名、徽章文本 |
| `menuPosition` | `header / content / footer` | 导航区域；模块也使用相同字段 |
| `menuExpanded` / `menuVisible` | `boolean` | 默认展开、导航可见；隐藏页面仍可通过路由直达 |
| `menuSort` | `number` | 同级升序排列，当前值保留原数组顺序 |
| `menuStatus` | `0 / 1` | 禁用/启用；禁用节点及其子树不生成导航和动态路由 |
| `menuPermission` | `string?` | 权限标识预留，不能替代后端授权 |
| `id` / `menuParentId` | `number?` | 预留数据库数字主键/父键；当前静态清单不编造 ID |
| `children` | `NavMenuNode[]?` | 同一类型的子节点；层级由递归计算，不持久化 `level` |
| `auth` | `public / protected`（可选） | 保留现有前端路由扩展；当前页面仍由受保护布局统一守卫 |
| `exact` | `boolean?` | 前端高亮匹配选项，不属于数据库字段；当前清单未配置 |

原 `moduleId/menuId` 合并为 `menuCode`，`moduleName/moduleDescription/moduleIcon` 分别合并为对应的 `menu*` 字段；`routePath` 改为 `menuRoutePath`。未被界面使用的 `moduleGroupId/moduleGroupName` 分类元数据从清单移除，不能将它们机械转换为 `group` 节点。未来如需展示业务/调试分类，另行明确分类模型。

`redirect/fallback` 属于路由层概念，不再属于菜单类型。登录、404 等静态路由继续由 `appRouter.tsx` 管理。清单不声明 `loader`，页面解析由 `menuPagePath` 与构建期页面映射完成。本次仅调整前端，不修改 Java 或数据库。

---

<a id="sec-6"></a>

## 六、白名单数据设计

白名单路由（根 `/`、`/login`、`404`、`*`）**直接在内联 `appRouter.tsx` 声明**，不进入 Zustand 状态层、不参与 localStorage 持久化、不混入 `asyncRouteData`。

**【强制】** 白名单不进入 `RouterStore`、不持久化，这是本方案的重要边界；后续实现时不建议再把白名单塞回状态层。原 `Whitelist.ts` 抽象已移除（全仓 0 引用），不要再引用该文件。

---

<a id="sec-7"></a>

## 七、菜单状态方案（MenuStore）

`MenuStore` 持有如下状态（类型见 `types/moduleMenu.ts`）：

| State | 类型 | 持久化 | 说明 |
| --- | --- | --- | --- |
| `menuData` | `ModuleMenuData`（`Record<MenuCode, NavMenuNode>`） | 是（`menu.menuData`） | 按模块划分的全量菜单数据 |
| `currentModuleCode` | `MenuCode` | 是（`menu.currentModuleCode`） | 当前激活模块，取值来自真源 `menuCode` |
| `currentMenuData` | `NavMenuNode[]` | 否（派生） | `menuData[currentModuleCode]?.children`，运行期计算 |

模块数据和子节点均使用 `NavMenuNode`；按模块建立索引只是便于切换，不产生第二套节点格式。

**Action 设计**：

- `buildMenuData(loginModuleCode?)`（场景一）：从 `MENU_MANIFEST` **实时构建**全量 `menuData`（`buildRuntimeMenuData`），确定 `currentModuleCode`（登录指定或回退第一个非空模块，没有可用模块时为空字符串），派生 `currentMenuData` 并持久化 `menuData` 与 `currentModuleCode`。
- `setCurrentModuleCode(menuCode)`（场景二）：复用已持久化 `menuData`，切换 `currentModuleCode` 并重算 `currentMenuData`，仅持久化 `currentModuleCode`。
- 内部统一出口 `applyMenuState(set, menuData, currentModuleCode, init)`：负责派生 `currentMenuData`、按 `init` 决定是否持久化 `menuData`、始终持久化 `currentModuleCode`、写入 state。

**处理顺序**：从 `MENU_MANIFEST` 读取真源 → 按模块归类生成 `menuData` → 按 `currentModuleCode` 索引得到 `currentMenuData`（即 `menuData[currentModuleCode].children`）→ 更新 Zustand state。场景三（刷新）由 store 初始化时自动从 localStorage 还原 `menuData` 与 `currentModuleCode` 并派生 `currentMenuData`，不需要单独 Action。

**【强制】** `menuData` 的形状是 `Record<MenuCode, NavMenuNode>`（按模块索引、值含 `children`），**不是** `NavMenuNode[]` 扁平数组；消费方先按 `currentModuleCode` 索引取模块，再取 `.children` 作为菜单树。

---

<a id="sec-8"></a>

## 八、路由状态方案（RouterStore）

`RouterStore` 持有如下状态：

| State | 类型 | 持久化 | 说明 |
| --- | --- | --- | --- |
| `asyncRouteData` | `AsyncRouteNode[]`（树状，含 children） | 是（`router.asyncRouteData`） | 动态路由树，存储即唯一权威源，缺失视为未登录（空数组） |
| `addRouteFlag` | `boolean` | 否 | 是否已注入受保护布局；避免每次导航重复 `patchRoutes` |

**Action 设计**：

- `buildAsyncRouterData`（场景一）：登录成功后遍历真源、构建全量动态路由树（`buildAsyncRouteTree`：按 `menuSort` 排序，剔除禁用子树，仅保留 `page`；`module/group` 透传 children）并持久化，同时重置 `addRouteFlag = true`（标记需重新注入）。
- 场景二（刷新，已登录）：store 初始化时由 `readStoredAsyncRouterData()` 从 localStorage 还原 `asyncRouteData`，路由注册层直接消费，无需手动调用。

**【强制】** `asyncRouteData` 仅由 `MENU_MANIFEST` 加工得到；白名单路由不在其中，由 `appRouter.tsx` 注册层合并。注册动作（`registerAsyncRoutes` / `uninstallAsyncRoutes`）已移出 `RouterStore` 到 `routeRegistration.ts`，避免 `RouterStore` 静态依赖 `appRouter`。

---

<a id="sec-9"></a>

## 九、数据处理流程

### 9.1 菜单数据流

```
MENU_MANIFEST 真源
  -> MenuStore.buildMenuData()        （场景一：从真源实时构建）
  -> menuData（持久化 menu.menuData）
  -> currentModuleCode（持久化 menu.currentModuleCode）
  -> currentMenuData（派生，节点含 menuPosition）
  -> 使用方按 menuPosition 自行拆分 header/content/footer
```

### 9.2 路由数据流

```
MENU_MANIFEST 真源
  -> RouterStore.buildAsyncRouterData()   （场景一：登录后构建并落盘）
  -> asyncRouteData（场景二：刷新时从持久化还原）
  -> routeRegistration.registerAsyncRoutes() -> patchRoutes('business', ...)

白名单（/, /login, 404, *）
  -> 在 appRouter.tsx 内联声明，不参与上述状态层
```

---

<a id="sec-10"></a>

## 十、持久化策略

### 10.1 MenuStore 持久化范围

- **需要持久化**：`{ fingerprint, modules: menuData }`（键 `menu.menuData`）、`currentModuleCode`（键 `menu.currentModuleCode`）。
- **不需要持久化**：`currentMenuData`（派生结果，由 `menuData[currentModuleCode]` 直接索引；store 初始化时按持久化的 `menuData + currentModuleCode` 重新计算）。

菜单和路由缓存均使用 `manifest.ts` 导出的 `MENU_MANIFEST_FINGERPRINT`。旧版裸菜单对象、指纹不匹配的缓存不再读取；不转换为旧模块格式。原模块选择键不再使用，登录后写入 `menu.currentModuleCode`。清单变更后旧路由失效，沿用应用现有的重新登录重建流程。

### 10.2 RouterStore 持久化范围

- **需要持久化**：`asyncRouteData`（键 `router.asyncRouteData`）。
- **不需要持久化**：白名单数据（`addRouteFlag` 为运行期标记，亦不持久化）。

---

<a id="sec-11"></a>

## 十一、文件职责与边界

### 11.1 真源文件

- `router/manifest.ts` —— 唯一真源 `MENU_MANIFEST`（模块 + 菜单/路由节点）。

### 11.2 核心状态文件

- `stores/MenuStore.ts` —— 菜单数据加工、存储、持久化、模块切换编排。
- `stores/RouterStore.ts` —— 动态路由树加工、存储、持久化（登录构建 + 刷新还原两场景）。
- `router/routeRegistration.ts` —— 动态路由注册（消费 `RouterStore`，避免反向依赖 `appRouter`）。

### 11.3 已移除 / 不再适用

| 原文件 | 现状 |
| --- | --- |
| `components/layout/SideBar/dataFactory.ts` | 已不存在（加工逻辑已收敛到 `MenuStore`） |
| `router/routerFactory` | 已不存在（路由配置已数据路由化） |
| `router/Whitelist.ts` | 已移除（白名单改为 `appRouter.tsx` 内联声明，全仓 0 引用） |

---

<a id="sec-12"></a>

## 十二、约束与注意

- **命名统一**：使用 `currentMenuData`，避免 `currnetMenuData` 之类的拼写扩散。
- **白名单职责边界**：白名单不入 Store、不持久化，是重要边界（见 §6）。
- **`menuData` 形状**：务必按 `Record<MenuCode, NavMenuNode>` 处理，勿当作扁平 `NavMenuNode[]`。
- **`menuCode ≠ pathname`**：实测菜单 `menuCode`（如 `index` → `/market/index`、`kline` → `/stock/kline`）与 URL pathname 不一致，故黑名单等匹配键采用 pathname（见 [前端路由缓存（Keep-Alive）架构设计](frontend_route_keepalive.md)）。

---

<a id="sec-13"></a>

## 十三、后续演进

当前真源在本地常量中，后续真源将改为接口返回。为兼容未来演进：

1. 将 Store 中"读取真源"的入口抽象为统一方法；
2. 当前先读取本地 `MENU_MANIFEST`；
3. 后续切到接口时，只替换数据读取入口，不改 Store 的状态结构与 `asyncRouteData` / `currentMenuData` 的消费方式；
4. 接口化后可增加版本号、更新时间、远端同步策略。

该方案兼容当前本地真源模式，也兼容后续接口化真源模式，可作为菜单和动态路由重构的正式设计基础。
