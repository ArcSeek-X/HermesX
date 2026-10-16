# <a id="frontend-module-menu"></a>前端模块化菜单与动态路由状态方案

> 📝 **方案简述**：本方案确立 `apps/hrs-web` 前端"菜单 + 动态路由"的数据分层与状态管理基准——以 `MENU_MANIFEST` 为唯一真源，菜单与路由共用同一份原始数据；菜单加工/持久化收敛到 `MenuStore`、动态路由树加工/持久化收敛到 `RouterStore`（均 Zustand）；白名单路由（登录页/404/兜底）不进入状态层、仅在 `appRouter.tsx` 内联声明；真源当前为本地常量，后续平滑切换为接口返回。本方案**已落地**，本文档描述当前实现状态。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-16

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
- **模块划分已生效**：`MENU_MANIFEST` 第一层为 `ModuleNode[]`，当前含 `productModel`（产品）与 `developmentMode`（调试/文档）两个模块。

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

- 侧边栏（`SidebarNav`）/ 应用入口（`ApplicationMenu`）消费 `MenuStore` 的 `currentMenuData`；
- 路由注册层（`routeRegistration.ts`）消费 `RouterStore` 的 `asyncRouteData`。

---

<a id="sec-5"></a>

## 五、真源数据设计

真源 `MENU_MANIFEST: ModuleNode[]`，两层结构：

```ts
// 第一层：模块节点（ModuleNode）
{ moduleId, moduleName, moduleDescription?, routePath?, moduleGroupId?, moduleGroupName?, moduleIcon?, children: AppRouteNode[] }
// 第二层：路由/菜单节点（AppRouteNode）
type AppRouteNode = Omit<NavMenuNode, 'description'|'exact'|'children'> & {
  menuDescription: string; menuType: RouteMenuType;
  auth?: RouteAuthPolicy; menuVisible?: boolean; redirect?: string;
  menuPagePath?: string; children?: AppRouteNode[];
};
```

| 字段 | 层级 | 说明 |
| --- | --- | --- |
| `moduleId` | 模块 | 模块唯一标识，也是 `currentModuleId` 取值与持久化键 |
| `menuId` | 节点 | 菜单/路由节点唯一标识 |
| `menuName` | 节点 | 菜单名称（i18n key 或直写） |
| `routePath` | 节点 | 路由路径；为空表示不可跳转 |
| `menuType` | 节点 | `'page' \| 'group' \| 'redirect' \| 'fallback'` |
| `auth` | 节点 | `'public' \| 'protected'` |
| `menuVisible` | 节点 | 是否可见（默认可见；`false` 剔除） |
| `menuPagePath` | 节点 | 页面模块路径（如 `'pages/HomePage'`），经 `import.meta.glob` 解析为懒加载导入 |
| `menuPosition` | 节点 | `'header' \| 'content' \| 'footer'`，使用方据此拆分区域 |
| `menuIcon` / `menuBadge` / `level` / `menuExpanded` / `menuDescription` / `redirect` | 节点 | 展示/层级/展开/描述/重定向等 |

**【强制】** 真源**不含** `loader` 字段——页面解析由 `menuPagePath` + 路由级 `import.meta.glob` 动态导入完成（见 [前端异步数据路由方案](frontend_async_router.md) §六），不要在 `MENU_MANIFEST` 中声明页面加载器。

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
| `menuData` | `ModuleMenuData`（`Record<ModuleId, NavModuleNode>`） | 是（`menu.menuData`） | 按模块划分的全量菜单数据 |
| `currentModuleId` | `ModuleId` | 是（`menu.currentModuleId`） | 当前激活模块，取值来自真源 `moduleId` |
| `currentMenuData` | `NavMenuNode[]` | 否（派生） | `menuData[currentModuleId]?.children`，运行期计算 |

其中 `NavModuleNode = { moduleId, moduleName, moduleDescription?, routePath?, moduleGroupId?, moduleGroupName?, moduleIcon?, children: NavMenuNode[] }`，承载模块级元数据 + 菜单树；`NavMenuNode` 为菜单树节点（`menuId` / `menuName?` / `routePath?` / `menuIcon?` / `menuBadge?` / `menuPosition` / `level` / `menuType?` / `menuExpanded` / `description` / `exact?` / `children?`）。

**Action 设计**：

- `buildMenuData(loginModuleId?)`（场景一）：从 `MENU_MANIFEST` **实时构建**全量 `menuData`（`buildRuntimeMenuData`），确定 `currentModuleId`（登录指定或回退第一个非空模块，默认 `productModel`），派生 `currentMenuData` 并持久化 `menuData` 与 `currentModuleId`。
- `setCurrentModuleId(moduleId)`（场景二）：复用已持久化 `menuData`，切换 `currentModuleId` 并重算 `currentMenuData`，仅持久化 `currentModuleId`。
- 内部统一出口 `applyMenuState(set, menuData, currentModuleId, init)`：负责派生 `currentMenuData`、按 `init` 决定是否持久化 `menuData`、始终持久化 `currentModuleId`、写入 state。

**处理顺序**：从 `MENU_MANIFEST` 读取真源 → 按模块归类生成 `menuData` → 按 `currentModuleId` 索引得到 `currentMenuData`（即 `menuData[currentModuleId].children`）→ 更新 Zustand state。场景三（刷新）由 store 初始化时自动从 localStorage 还原 `menuData` 与 `currentModuleId` 并派生 `currentMenuData`，不需要单独 Action。

**【强制】** `menuData` 的形状是 `Record<ModuleId, NavModuleNode>`（按模块索引、值含 `children`），**不是** `NavMenuNode[]` 扁平数组；消费方先按 `currentModuleId` 索引取模块，再取 `.children` 作为菜单树。

---

<a id="sec-8"></a>

## 八、路由状态方案（RouterStore）

`RouterStore` 持有如下状态：

| State | 类型 | 持久化 | 说明 |
| --- | --- | --- | --- |
| `asyncRouteData` | `AsyncRouteNode[]`（树状，含 children） | 是（`router.asyncRouterData`） | 动态路由树，存储即唯一权威源，缺失视为未登录（空数组） |
| `addRouteFlag` | `boolean` | 否 | 是否已注入受保护布局；避免每次导航重复 `patchRoutes` |

**Action 设计**：

- `buildAsyncRouterData`（场景一）：登录成功后遍历真源、构建全量动态路由树（`buildAsyncRouteTree`：仅保留 `page/redirect/fallback`，`group` 仅透传 children）并持久化，同时重置 `addRouteFlag = true`（标记需重新注入）。
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
  -> currentModuleId（持久化 menu.currentModuleId）
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

- **需要持久化**：`menuData`（键 `menu.menuData`）、`currentModuleId`（键 `menu.currentModuleId`）。
- **不需要持久化**：`currentMenuData`（派生结果，由 `menuData[currentModuleId]` 直接索引；store 初始化时按持久化的 `menuData + currentModuleId` 重新计算）。

### 10.2 RouterStore 持久化范围

- **需要持久化**：`asyncRouteData`（键 `router.asyncRouterData`）。
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

> 原规划"后续建议弱化或下线"的三处，均已兑现为"已移除"。

---

<a id="sec-12"></a>

## 十二、约束与注意

- **命名统一**：使用 `currentMenuData`，避免 `currnetMenuData` 之类的拼写扩散。
- **白名单职责边界**：白名单不入 Store、不持久化，是重要边界（见 §6）。
- **`menuData` 形状**：务必按 `Record<ModuleId, NavModuleNode>` 处理，勿当作扁平 `NavMenuNode[]`。
- **`menuId ≠ pathname`**：实测菜单 `menuId`（如 `index` → `/market/index`、`kline` → `/stock/kline`）与 URL pathname 不一致，故黑名单等匹配键采用 pathname（见 [前端路由缓存（Keep-Alive）架构设计](frontend_route_keepalive.md)）。

---

<a id="sec-13"></a>

## 十三、后续演进

当前真源在本地常量中，后续真源将改为接口返回。为兼容未来演进：

1. 将 Store 中"读取真源"的入口抽象为统一方法；
2. 当前先读取本地 `MENU_MANIFEST`；
3. 后续切到接口时，只替换数据读取入口，不改 Store 的状态结构与 `asyncRouteData` / `currentMenuData` 的消费方式；
4. 接口化后可增加版本号、更新时间、远端同步策略。

该方案兼容当前本地真源模式，也兼容后续接口化真源模式，可作为菜单和动态路由重构的正式设计基础。
