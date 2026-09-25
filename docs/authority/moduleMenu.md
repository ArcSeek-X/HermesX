# 模块化菜单与动态路由状态分层方案

## 文档信息

- 文档名称：模块化菜单与动态路由状态分层方案
- 文档路径：[docs/authority/moduleMenu.md](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/docs/authority/moduleMenu.md)
- 作者：Lensgcx (GaoCangxiong) / AI 协作整理
- 适用范围：[apps/hrs-web](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web)
- 当前状态：已实现（与 `MenuStore` 代码对齐）

## 目录

1. 背景与目标
2. 现状问题
3. 设计原则
4. 总体架构
5. 真源数据设计
6. 白名单数据设计
7. 菜单状态方案
8. 路由状态方案
9. 数据处理流程
10. 持久化策略
11. 文件职责划分
12. 后续演进建议
13. 风险与注意事项
14. 实施顺序建议

## 1. 背景与目标

当前 Web 端的菜单、路由、模块切换能力正在从“静态写死”向“统一配置驱动”演进。现阶段真源数据暂时存放在本地文件中，后续会改为接口返回。因此需要先建立一套稳定的数据分层与状态管理方案，使系统同时满足以下目标：

- 菜单与路由共享同一份真源数据
- 支持模块切换，例如产品模块、调试模块
- 支持动态路由生成
- 支持白名单路由单独维护
- 支持菜单与路由结果的本地持久化
- 后续真源从本地文件切换到接口时，状态层与消费层尽量少改

## 2. 现状问题

当前路由与菜单能力存在以下问题：

- 页面路由在 [App.tsx](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/App.tsx) 中手写维护，扩展成本高
- 菜单数据与路由数据存在分散维护问题，容易发生漂移
- 菜单和路由的加工逻辑尚未沉淀到稳定的状态中心
- 未来真源改为接口返回后，如果仍采用静态散落结构，接入成本会明显升高

## 3. 设计原则

本方案遵循以下原则：

- 单一真源：菜单与路由都基于同一份原始数据
- 白名单独立：白名单不混入业务动态路由状态
- 状态中心化：数据加工、数据存储、数据编排统一进入 Zustand
- 结果可缓存：加工后的菜单数据和动态路由数据允许持久化
- 逐步演进：现阶段兼容本地文件真源，后续平滑切换到接口真源

## 4. 总体架构

整体分为三层：

### 4.1 真源层

- [manifest.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/manifest.ts)
- [Whitelist.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/Whitelist.ts)

职责：

- 保存原始菜单/路由真源结构
- 不承担加工逻辑
- 未来支持从接口数据替换本地文件数据

### 4.2 状态加工层

- [MenuStore](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/MenuStore)
- [RouterStore.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/RouterStore.ts)

职责：

- 从真源中读取数据
- 对真源进行加工处理
- 持有加工后的可消费结果
- 执行本地持久化
- 对外暴露模块切换、菜单切换、路由刷新等 action

### 4.3 消费层

- 侧边栏组件消费菜单状态
- 路由注册层消费动态路由状态

## 5. 真源数据设计

当前“真源数据”暂时存放在 [manifest.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/manifest.ts) 中，只承担原始数据存储职责，不再承担工厂方法或状态逻辑。

真源数据应满足以下要求：

- 以菜单字段为基础
- 包含模块字段 `moduleId`
- 包含菜单类型字段 `menuType`
- 包含路由路径 `routePath`
- 包含菜单可见性 `menuVisible`
- 包含重定向字段 `redirect`
- 包含异步页面加载器 `loader`

真源的定位是“原始输入”，不是“最终消费数据”。

## 6. 白名单数据设计

白名单独立维护在 [Whitelist.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/Whitelist.ts) 中。

白名单设计要求：

- 不进入 Zustand 状态层
- 不参与本地持久化
- 不混入 `asyncRouterData`
- 在最终路由注册时与动态路由合并

典型白名单示例：

- `/login`
- `/`

## 7. 菜单状态方案

[MenuStore](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/MenuStore) 持有以下状态。

### 7.1 State 定义

#### `menuData`

含所有模块及其菜单数据，需持久化。

建议结构：

```ts
type MenuDataMap = Record<string, NavMenuNode[]>
```

推荐示例：

```ts
{
  productModel: [...],
  developmentMode: [...],
}
```

#### `currentModuleId`

当前模块 ID，需持久化。

说明：

- 用于标识当前激活模块
- 取值来源于真源中的 `moduleId`
- 切换模块时更新并写入本地缓存

#### `currentMenuData`

当前模块对应的菜单数据，不做本地持久化。

由 `menuData[currentModuleId]` 直接索引得到，节点本身携带 `menuPosition` 字段（取值 `header` / `content` / `footer`）。

说明：

- 分区（头部 / 主体 / 底部）**不再由 Store 拆分**，Store 只暴露扁平的 `currentMenuData`
- 使用方（如侧边栏）获取 `currentMenuData` 后，按需按 `menuPosition` 自行过滤出各区域菜单

### 7.2 Action 设计

MenuStore 实际提供以下 Action：

- `buildMenuData(loginModuleId?: ModuleId)`：场景一入口。构建全量 `menuData`、确定 `currentModuleId`（登录指定或回退第一个可用模块）、派生 `currentMenuData`，并持久化 `menuData` 与 `currentModuleId`。
- `setCurrentModuleId(moduleId: ModuleId)`：场景二入口。复用已持久化的 `menuData`（不重建），切换 `currentModuleId` 并重算 `currentMenuData`，仅持久化 `currentModuleId`。

内部统一出口 `applyMenuState(set, menuData, currentModuleId, init)`：负责派生 `currentMenuData`、按 `init` 决定是否持久化 `menuData`、始终持久化 `currentModuleId`、并写入 state。两个 Action 均经此出口，避免重复骨架。

说明：

- 已移除早期设计中的 `setMenuData` / `syncCurrentMenuData` / `splitCurrentMenus` / `refreshMenus` / `resetMenus`，分区拆分职责下放给使用方

### 7.3 菜单处理逻辑

处理顺序如下：

1. 从 [manifest.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/manifest.ts) 读取真源
2. 按 `moduleId` 归类生成 `menuData`（深度遍历收集去重模块 id，逐模块生成菜单树）
3. 根据 `currentModuleId` 索引得到 `currentMenuData`（即 `menuData[currentModuleId]`）
4. 更新 Zustand state

说明：

- `currentMenuData` 不再进一步按区域拆分，`menuPosition` 字段随节点保留，由使用方按需拆分
- 场景三（刷新浏览器）由 Store 初始化时自动从 localStorage 还原 `menuData` 与 `currentModuleId` 并派生 `currentMenuData`，不需要单独 Action

## 8. 路由状态方案

[RouterStore.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/RouterStore.ts) 持有以下状态。

### 8.1 State 定义

#### `asyncRouterData`

动态路由树（树状结构，含 children），需持久化。

要求：

- 是一份完整的动态路由树状结构
- 支持一二级路由
- 不在状态层中拆分为 `businessRoutes`、`exceptionRoutes`
- 仅由 `MENU_MANIFEST` 加工得到；白名单路由不在其中，由注册层合并

### 8.2 Action 设计

建议在 Store 中提供以下方法，覆盖两个核心场景：

- `buildAsyncRouterData`：场景一，登录成功后构建全量动态路由树并持久化（唯一写入点）

场景二（刷新浏览器，已登录）不提供单独方法：store 初始化时直接从 localStorage 还原 `asyncRouterData`，路由注册层消费它即可建立动态路由，无需手动调用。

### 8.3 路由处理逻辑

处理顺序如下：

1. 从 [manifest.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/manifest.ts) 读取真源
2. 过滤出参与动态路由的节点（page/redirect/fallback；group 仅透传 children）
3. 将真源加工为一份完整的树状动态路由结构
4. 存入 `asyncRouterData` 并落盘（场景一）；刷新时从持久化还原（场景二）
5. 在路由注册阶段，将 [Whitelist.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/Whitelist.ts) 中的白名单路由与 `asyncRouterData` 合并后使用

## 9. 数据处理流程

### 9.1 菜单数据流

```text
manifest 真源
  -> MenuStore.buildMenuData()
  -> menuData（持久化）
  -> currentModuleId（持久化）
  -> currentMenuData（派生，节点含 menuPosition）
  -> 使用方按 menuPosition 自行拆分区域
```

### 9.2 路由数据流

```text
manifest 真源
  -> RouterStore.buildAsyncRouterData()（场景一：登录后构建并落盘）
  -> asyncRouterData（场景二：刷新时从持久化还原）

Whitelist 白名单
  -> 路由注册层

最终路由
  = whiteListRoutes + asyncRouterData
```

## 10. 持久化策略

### 10.1 MenuStore 持久化范围

需要持久化：

- `menuData`（键：`menu.menuData`）
- `currentModuleId`（键：`menu.currentModuleId`）

不需要持久化：

- `currentMenuData`

说明：

- `currentMenuData` 属于派生结果，由 `menuData[currentModuleId]` 直接索引
- 应在 Store 初始化时根据持久化的 `menuData + currentModuleId` 重新计算（场景三自动还原）

### 10.2 RouterStore 持久化范围

需要持久化：

- `asyncRouterData`

不需要持久化：

- 白名单数据

说明：

- `asyncRouterData` 属于一次加工后的完整结果
- 页面刷新后可直接恢复，避免重复处理

## 11. 文件职责划分

### 11.1 保留为真源文件

- [manifest.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/manifest.ts)
- [Whitelist.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/Whitelist.ts)

### 11.2 核心状态文件

- [MenuStore](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/MenuStore)
- [RouterStore.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/RouterStore.ts)

### 11.3 后续建议弱化或下线的文件

- [dataFactory.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/components/layout/SideBar/dataFactory.ts)
- [routerFactory](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/routerFactory)

原因：

- 既然本轮决定将数据处理逻辑收敛到 Zustand 状态层，这两个工厂文件后续不再适合作为长期核心入口

## 12. 后续演进建议

当前真源在本地文件中，后续真源将改为接口返回。为兼容未来演进，建议：

1. 将 Store 中“读取真源”的入口抽象为统一方法
2. 当前先读取本地文件
3. 后续切到接口时，只替换数据读取入口，不改 Store 的状态结构
4. 在接口化后，可增加版本号、更新时间、远端同步策略

## 13. 风险与注意事项

### 13.1 命名统一

建议统一使用 `currentMenuData`，不要保留 `currnetMenuData` 这种拼写，以免后续传播到全局使用中。

### 13.2 文件扩展名规范

像 [MenuStore](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/MenuStore) 这类无扩展名文件，后续建议确认仓库规范。若工程最终需要完整的 lint、类型检查和 IDE 支持，推荐统一成 `.ts` 或 `.tsx`。

### 13.3 动态路由树结构

`asyncRouterData` 需要在一开始就明确树状结构格式，避免后续路由注册层再次做二次转换。

### 13.4 白名单职责边界

白名单不进入 Store，不持久化，这是本方案的重要边界。后续实现时不建议再把白名单塞回状态层。

## 14. 实施顺序建议

建议按以下顺序落地：

1. 完成 [MenuStore](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/MenuStore) 的状态设计与持久化实现
2. 完成 [RouterStore.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/RouterStore.ts) 的动态路由树加工与持久化实现
3. 让侧边栏开始消费 `MenuStore`
4. 让动态路由注册层开始消费 `RouterStore`
5. 清理或下线 [dataFactory.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/components/layout/SideBar/dataFactory.ts) 与 [routerFactory](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/routerFactory)

## 结论

本方案最终确立如下边界：

- [manifest.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/manifest.ts) 和 [Whitelist.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/router/Whitelist.ts) 只保存原始真源
- [MenuStore](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/MenuStore) 负责菜单数据的加工、存储、持久化、模块切换编排
- [RouterStore.ts](file:///Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/apps/hrs-web/src/stores/RouterStore.ts) 负责动态路由树的加工、存储、持久化（登录构建 + 刷新还原两场景）
- 白名单独立维护，不进入 Zustand 状态层

该方案兼容当前本地真源模式，也兼容后续接口化真源模式，适合作为下一阶段菜单和动态路由重构的正式设计基础。
