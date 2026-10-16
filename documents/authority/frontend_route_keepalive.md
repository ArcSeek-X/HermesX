# HermesX - 前端路由缓存（Keep-Alive）架构设计

> 📝 **方案简述**：本方案确立 HermesX Web 前端（`apps/hrs-web`）路由缓存的全局设计基准：切换路由时页面实例保留、切回时状态（表单/筛选项/Tab/滚动位置/已加载数据/图表实例）留存，不重新请求、不出现 loading；缓存范围由单一前端配置文件以**黑名单（pathname）**控制；缓存实现基于第三方库 **`keepalive-for-react` + `keepalive-for-react-router`**（适配 React 19.2 / React Router v7，MIT、6KB、零传递依赖），复用其 LRU、黑白名单、活动态下发能力，叠加本项目的黑名单配置真源、query/hash 重挂载、滚动位置恢复。任何前端路由/布局改动与本方案冲突，均以本方案为准。

> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-15

## 方案目录

- [1. 背景 / 上下文（Context）](#1-背景--上下文context)
  - [1.1 目标（Goals）](#11-目标goals)
  - [1.2 非目标（Non-Goals）](#12-非目标non-goals)
- [2. 现状分析（已核实事实）](#2-现状分析已核实事实)
  - [2.1 路由与渲染链路](#21-路由与渲染链路)
  - [2.2 页面副作用清单](#22-页面副作用清单)
  - [2.3 关键技术结论（读源码验证）](#23-关键技术结论读源码验证)
  - [2.4 与 PageStateStore 的关系](#24-与-pagestatestore-的关系)
- [3. 方案选型（Alternatives Considered）](#3-方案选型alternatives-considered)
- [4. 总体设计](#4-总体设计)
  - [4.1 挂载点与渲染结构](#41-挂载点与渲染结构)
  - [4.2 缓存机制（库能力 + 本项目适配）](#42-缓存机制库能力--本项目适配)
  - [4.3 黑名单配置（单一配置文件）](#43-黑名单配置单一配置文件)
  - [4.4 滚动位置恢复（ScrollContainerContext）](#44-滚动位置恢复scrollcontainercontext)
  - [4.5 后台页暂停（useKeepAliveContext）](#45-后台页暂停usekeepalivecontext)
  - [4.6 新页面接入检查清单](#46-新页面接入检查清单)
- [5. 性能设计](#5-性能设计)
- [6. 兼容性与边界](#6-兼容性与边界)
- [7. 后果（Consequences）](#7-后果consequences)
  - [正面](#正面)
  - [负面 / 成本](#负面--成本)
  - [风险 / 注意](#风险--注意)
- [8. 改动清单（代码执行指引）](#8-改动清单代码执行指引)
- [9. 测试与验证计划](#9-测试与验证计划)
- [10. 评审决策记录](#10-评审决策记录)
- [11. 修订历史](#11-修订历史)

| 项 | 内容 |
|---|---|
| 文档类型 | 前端架构设计 / 方案文档（原 ADR-002，2026-10-15 整体更新并更名） |
| 编号 | ADR-002（沿用，作追溯 ID） |
| 状态 | **已采纳（Accepted）** |
| 关联方案 | `ADR-001`（后端分层架构，同为全局架构基准）；前端实现落地时同步更新 `documents/CHANGELOG.md` 与专题文档 |
| 适用范围 | HermesX Web 前端 `apps/hrs-web`（**全域前端架构基准**；首个落地范围：路由缓存能力） |
| 实现底座 | 第三方库 `keepalive-for-react@6` + `keepalive-for-react-router@6`（React 19.2 / React Router v7） |

> **方案用意**：本方案是 HermesX 前端的**全局架构决策基准**，面向整个 Web 前端工程，不隶属于任何单一功能方案。它确立四项设计立场：① 路由缓存以**页面实例保留**为实现手段（而非状态提升）；② 缓存范围由**单一前端配置文件的黑名单（pathname）**控制，默认全开、显式排除；③ 缓存实现**基于 `keepalive-for-react` 库**，复用其渲染管线与 LRU / 黑名单 / 活动态能力，不引入第二个平行路由渲染层；④ 性能三铁律——失活页 DOM 移出文档（零绘制）、后台页暂停轮询/SSE、`maxCacheSize` LRU 硬上限。
>
> **指导方针**：任何前端方案 / 代码改动若与本方案冲突，均以本方案为准；本方案不被任何单一功能方案"拥有"或"限定"。

---

## <a id="1-背景--上下文context"></a>1. 背景 / 上下文（Context）

当前前端每次切换路由，React Router 数据路由会重建匹配元素树：旧页面组件卸载、新页面挂载，导致组件状态、已请求数据、滚动位置、图表实例全部丢失，用户重新走一遍加载。对股票分析类重页面（K 线、大盘、板块分析、筛选器）而言，重复请求与状态丢失直接影响体验。

### <a id="11-目标goals"></a>1.1 目标（Goals）

1. **路由缓存**：切换路由后页面实例保留；切回时页面状态（表单/筛选项/Tab/滚动位置/已加载数据/图表实例）留存，不重新请求、不出现 loading。
2. **黑名单**：通过一个前端配置文件设置哪些页面不参与缓存，其余全部缓存。
3. **性能**：缓存管理开销合理，切换不卡顿；后台缓存页不空转（轮询/SSE/定时器暂停）。

### <a id="12-非目标non-goals"></a>1.2 非目标（Non-Goals）

- 刷新后恢复：已有 `PageStateStore`（内存 + sessionStorage）承担，与本方案互补。
- 跨标签页共享缓存、页面切换动画、每页独立滚动容器。

---

## <a id="2-现状分析已核实事实"></a>2. 现状分析（已核实事实）

### <a id="21-路由与渲染链路"></a>2.1 路由与渲染链路

- React Router **v7.13 数据路由**（`createBrowserRouter`），业务路由经 `patchRoutes('business')` 动态注入，页面经路由级 `lazy` 懒加载（`src/router/asyncRouteFactory.ts:66-70`）。
- 渲染链：`Shell` → `Main`（唯一滚动容器 `main.hrs-page-container`）→ `KeepAliveOutlet`（封装 `KeepAliveRouteOutlet`，经库的 `useOutlet` 捕获页面元素并缓存；`errorElement` 把每个缓存节点包进 `RouteBoundary`）→ 页面组件。
- 登录页 `/login` 是 **Shell 外的顶层路由**（`appRouter.tsx` 中与 `protected` 平级）；404 兜底 `/404` 在 Shell 内。

### <a id="22-页面副作用清单"></a>2.2 页面副作用清单

| 页面 | 后台行为 | 缓存策略 |
| --- | --- | --- |
| `reviewPage`（/review） | `useDashboardLifecycle`：30s 轮询 + 共享 SSE（`useTaskStream`）+ 自有轮询定时器 | 缓存 + `active` 暂停 |
| `StockDashboardPage`（/market/index） | 自有 `setInterval` 行情刷新 | 缓存 + `active` 暂停 |
| `LiveNewsPage`（/news/live-news） | `useLiveNews` 轮询 | 缓存 + `active` 暂停 |
| `ChatPage`（/choose/chat） | 仅 toast/copy 类短定时器；使用 `setSearchParams`，实例缓存语义不安全 | **黑名单**（不缓存） |
| `HomePage` | 纯搜索入口，无轮询 | 缓存 |

`useTaskStream` 是模块级共享 `EventSource` + 订阅者计数：订阅者清零即断连，因此 `enabled=false` 可以干净地暂停/恢复 SSE。

### <a id="23-关键技术结论读源码验证"></a>2.3 关键技术结论（读源码验证）

1. `keepalive-for-react` 核心包 6KB、MIT、唯一传递依赖 `mitt`；`keepalive-for-react-router` 为 RR 适配层，默认导出 `KeepAliveRouteOutlet`（`import KeepAliveRouteOutlet from 'keepalive-for-react-router'`），内部即 `useLocation()` + `useOutlet()` + `<KeepAlive {...rest}>`，透传全部 `KeepAlive` props（`exclude`/`include`/`max`/`errorElement`/`transition`…）。
2. **失活页的 DOM 节点被库移出文档**（React 实例保留，零布局零绘制），重新激活时重新挂载节点；不需要 `.inactive` / `display:none` CSS。
3. 缓存键 `activeCacheKey`：库默认 `pathname + search`；本项目显式传 `pathname + search + hash`，使 query/hash 变化触发重挂载（决策 4）。
4. `max`（默认 10）按 `lastActiveTime` **LRU** 淘汰；本项目设 8。当前页（活跃页）永不被淘汰。
5. `useKeepAliveContext().active` 提供活动/失活信号（等价原自研 `usePageActive()`）；另有 `useEffectOnActive` / `useEffectOnCreate` / `useKeepAliveRef`（refresh/destroy）等。
6. 工程约束：项目启用 **React Compiler**（`vite.config.ts` 的 `babel-plugin-react-compiler`）+ `eslint-plugin-react-hooks` v7 `flat.recommended`，其中 `set-state-in-render` / `purity` / `refs` 均为 **Error** 级。适配器 `KeepAliveOutlet` 是常规函数组件，无渲染期 setState（仅 `useMemo`/`useRef` 派生），与编译器/lint 兼容；`matchProps` 与 `toMatchRules` 以 `useMemo([])` 固化引用，满足库按引用 memo 比较。
7. `exclude`/`include` 支持 string（全等）与 RegExp；`toMatchRules` 把 `*` 前缀规则转 RegExp。`include` 为空数组时**必须传 `undefined`**（空数组在 JS 中为 truthy，库会误判为「已启用白名单但谁都不匹配」→ 全站不缓存）。
8. 已扫描 `global.scss` 与全部页面：无全局 CSS 以 `.hrs-page-container` 直接子选择器 / `:first-child` / `:last-child` 影响页面根元素；库为每页套 `keep-alive-render > keepalive-cache-div`（均 `height:100%`）两层 div，已核实无 CSS 依赖其直接子级，布局零回归。
9. 核实结论：**menuId ≠ pathname**（如 `index` → `/market/index`、`kline` → `/stock/kline`），故黑名单匹配键采用 pathname。

### <a id="24-与-pagestatestore-的关系"></a>2.4 与 PageStateStore 的关系

`PageStateStore`（L2 内存 + L3 sessionStorage）是"手动状态提升"，能跨刷新保留，但保留不了组件实例、DOM、滚动位置和图表实例。两者**互补**，本方案不动它。

---

## <a id="3-方案选型alternatives-considered"></a>3. 方案选型（Alternatives Considered）

| 方案 | 结论 | 理由 |
| --- | --- | --- |
| A. 第三方 `react-activation` | ❌ | 需引入 `babel-plugin-react-activation` 改构建管线；README 兼容列表仅到 React 18；面向 RR v5/v6 的 Switch 模式，与 data router + `Outlet` 集成需额外适配 |
| B. 扩展 `PageStateStore` 做全量状态提升 | ❌ | 保留不了实例/DOM/滚动/图表，需逐页面手工改造，改造成本高于本方案且易漏 |
| C. 自研 `KeepAliveOutlet`（`useOutlet` 捕获元素 + 冻结 `LocationContext` + LRU） | ⛔ 已废弃（v3 起被 E 取代） | v1/v2 期实现路径；可控可测，但需自行维护槽位协调、LRU、上下文冻结等全部机制，长期维护成本高于成熟库 |
| D. 自建平行路由渲染层（自行解析页面组件、逐层渲染） | ❌ | 绕开 RR 路由渲染即"平行实现"，丢失 `params`/`loaderData`/`matches` 语义，违背仓库"不新增平行实现"约束 |
| E. 第三方 `keepalive-for-react@6` + `keepalive-for-react-router@6` | ✅ **采纳** | 340 star / 144 commits / 2026 年活跃发版 / MIT / 6KB；官方支持 React Router v6/v7/v8 与 React 19.2；提供 `max`（LRU）、`exclude`/`include`、活动态 `useKeepAliveContext().active`、`errorElement` 等能力，与黑名单 / 上限 / 后台暂停诉求一一对应；失活页 DOM 节点移出文档（实例保留、零绘制）。**代价**：① 官方要求开发模式不用 StrictMode；② 不冻结失活页 LocationContext（见 §2.3 与 §6） |

---

## <a id="4-总体设计"></a>4. 总体设计

### <a id="41-挂载点与渲染结构"></a>4.1 挂载点与渲染结构

`Shell.tsx` 一处改动：`{children ?? <RouteOutletBoundary />}` → `{children ?? <KeepAliveOutlet />}`。

```
Shell
└─ Main（滚动容器 main.hrs-page-container，经 ScrollContainerContext 暴露 ref）
   └─ KeepAliveOutlet
      ├─ KeepAliveRouteOutlet（keepalive-for-react-router）
      │   └─ <KeepAlive>（keepalive-for-react，内部 useOutlet 捕获页面元素）
      │        └─ errorElement → RouteBoundary（ErrorBoundary + Suspense，逐页隔离）
      │             └─ 当前页 / 失活页（DOM 节点被库移出文档；activeCacheKey 命中则复用实例）
      └─ RouteScrollRestoration（兄弟组件，渲染在 KeepAliveRouteOutlet 之后；layout effect 恢复滚动）
```

设计要点：

- **在线页不套额外 DOM 包裹**：库为每页套 `keep-alive-render > keepalive-cache-div`（均 `height:100%`），但页面仍在滚动容器内、布局契约不变；回归面最小。
- **逐页错误边界**：`errorElement=RouteBoundary` 让单个缓存页崩溃不扩散到其他页与在线页。
- **滚动恢复独立于缓存节点**：`RouteScrollRestoration` 作为兄弟组件挂在 `KeepAliveRouteOutlet` 之后，其 `useLayoutEffect` 晚于库重建缓存节点 DOM 执行，偏移不被钳制。

### <a id="42-缓存机制库能力--本项目适配"></a>4.2 缓存机制（库能力 + 本项目适配）

| 维度 | 库的默认 | 本项目配置（来自 `KEEP_ALIVE_CONFIG`） |
| --- | --- | --- |
| 缓存键 `activeCacheKey` | `pathname + search` | `pathname + search + hash`（query/hash 变化重挂载，决策 4） |
| 数量上限 `max` | 10 | `maxCacheSize = 8`（LRU 硬上限，内存护栏） |
| 闲置过期 `maxAliveTime` | 0（不过期） | `maxAliveTime = 0`（不过期，仅受数量上限约束） |
| 排除/包含 | — | `exclude` = 黑名单规则（`toMatchRules` 转换后下发） |

- **失活页**：DOM 节点被库移出文档（React 实例保留，零布局零绘制），重新激活时重新挂载节点、实例/状态/数据原样恢复，无二次请求。
- **再次访问**（缓存键已存在且 query/hash 一致）：复用同一元素引用 → React 协调保留实例，状态/滚动/数据全部保留。
- **query/hash 变化**：视为新键，重新挂载（语义可预期，避免"实例还在但 URL 状态不一致"）。
- **LRU**：缓存数超过 `maxCacheSize` 时淘汰最久未用页；刚访问的当前页永不被淘汰。淘汰即卸载，页面 cleanup（`clearInterval`/关闭 SSE/echarts dispose）正常执行。
- **生命周期**：缓存随库内部 state 存续——`Shell` 卸载（登出跳 `/login`）或整页刷新时整体销毁，无需手动清理逻辑。

### <a id="43-黑名单配置单一配置文件"></a>4.3 黑名单配置（单一配置文件）

新增 `src/router/keepAliveConfig.ts`（**纯声明常量，无逻辑**；名单规则到库匹配语法的转换在 `KeepAliveOutlet` 内完成，详见 §4.5）：

```ts
interface KeepAliveConfig {
  /** 黑名单：命中的 pathname 不缓存（离开即销毁），优先级高于 include */
  exclude: KeepAliveRule[];
  /** 白名单：非空时仅缓存命中项；空数组 = 不启用（除 exclude 外都缓存） */
  include: KeepAliveRule[];
  /** 缓存闲置过期时间（秒）：0 = 不过期，仅受 maxCacheSize 约束 */
  maxAliveTime: number;
  /** 缓存页数量硬上限（LRU）：超出淘汰最久未用页，内存护栏 */
  maxCacheSize: number;
}

export const KEEP_ALIVE_CONFIG: KeepAliveConfig = {
  exclude: [
    '/login',       // 登录页（结构上在 Shell 外，双保险；后续新增 /register 一并加入）
    '/choose/chat', // 流式对话 + setSearchParams，实例缓存语义不安全
    '/docs/*',      // 组件调试模块（一条前缀规则覆盖全部子路径）
    '/codeTest',    // 调试页
    '/404',         // 兜底页
  ],
  include: [],
  maxAliveTime: 0,
  maxCacheSize: 8,
};
```

要点：

- **匹配键为 pathname**：黑名单是人工维护的排除清单，pathname 即 URL，直观可预期；无需把 routerKey 透传到 route.handle，`types/router.ts` 与 `asyncRouteFactory.ts` **零改动**。
- 规则语法：`*` 结尾 = 前缀规则（含自身与全部子路径），否则精确匹配；`toMatchRules` 把 `*` 前缀转 RegExp（`/docs/*` → `/^\/docs(\/|$)/`，不误伤 `/docsX`）。
- `maxCacheSize` 是内存护栏，默认 8；blacklist 全开模式下它是唯一硬上限，更重要。
- 白名单 `include` 默认空（走黑名单语义）；改为白名单时填入目标 pathname 规则即可。

### <a id="44-滚动位置恢复scrollcontainercontext"></a>4.4 滚动位置恢复（ScrollContainerContext）

- `Main.tsx` 把 `<main>` 的元素 ref 经 `ScrollContainerContext.Provider` 下发；契约显式、类型安全、不依赖 CSS 类名，将来其他组件需滚动容器可直接复用。
- `KeepAliveOutlet` 内 `RouteScrollRestoration` 通过 `useScrollContainerRef()` 取到滚动容器：passive `scroll` 监听持续把当前偏移按 `pathname+search+hash` 写入 `useRef<Map>`（规避切页时浏览器钳制 scrollTop 的问题）；`useLayoutEffect` 在 key 切换时先存旧值、再把目标 key 的值写回 `scrollTop`。layout effect 在 paint 前同步执行 → 无闪烁。
- **不引入每页独立滚动容器**：避免改动 `Main` 的 `contain`/LightBloom/padding 契约。
- `RouteScrollRestoration` **渲染在 `KeepAliveRouteOutlet` 之后**：库在 layout effect 内重建缓存节点 DOM，本组件的 layout effect 顺序在其后执行，恢复偏移时新页内容已挂载、不被钳制。

### <a id="45-后台页暂停usekeepalivecontext"></a>4.5 后台页暂停（useKeepAliveContext）

- 库对每个缓存页下发 `useKeepAliveContext().active`（true=在线 / false=失活）。自研的 `PageActivityContext` 已删除，统一改用此 hook。
- 页面侧最小接入（仅接有轮询/SSE 的，其余页面零改动即受益）：
  - `reviewPage`：`const { active: isPageActive } = useKeepAliveContext(); useDashboardLifecycle({ ..., enabled: isPageActive })`。hook 已支持 `enabled`；`enabled` 恢复时首载 effect 自动重跑 → **切回即刷新，数据不陈旧**。
  - `StockDashboardPage`：interval effect 增加 `isPageActive` 依赖。
  - `LiveNewsPage`：`useLiveNews` 增加 `enabled` 参数并门控轮询。
- `ChatPage` 在黑名单中，无需处理。

### <a id="46-新页面接入检查清单"></a>4.6 新页面接入检查清单

blacklist 意味着新页面默认进缓存，新增页面时确认：

1. 有轮询/SSE/定时器 → 接 `useKeepAliveContext().active` 控制 `enabled`（否则后台空转）。
2. 有 echarts / lightweight-charts → 激活时 resize（可用 `active` 驱动）。
3. 流式进行中、长表单编辑等实例保留语义不安全的页面 → 加入黑名单（`exclude`）。
4. 参数路由 → 当前 `activeCacheKey` 已含 `search`+`hash`，无需额外处理。

---

## <a id="5-性能设计"></a>5. 性能设计

1. **渲染开销**：非缓存路径与今天完全同路；缓存路径由库内部处理（按引用 memo 比较 `exclude`/`include`、`keep-alive-render` 缓存节点），无轮询、无监听器风暴。
2. **布局/绘制**：失活页 DOM 移出文档 → 零布局零绘制；在线页布局契约与今天一致。
3. **后台空转**：隐藏页轮询/SSE 经 `enabled` 暂停；共享 EventSource 订阅者清零即断连，不占连接数。
4. **切换流畅性**：切回 = 节点重新挂载（实例保留）+ 滚动偏移恢复，无重挂载式重建、无重新请求、无 loading 态；scroll 恢复先于 paint。
5. **内存**：`maxCacheSize` LRU 硬上限；淘汰即卸载，页面 cleanup 正常执行。
6. **图表**：echarts 页在激活时按需 resize（二期，`active` 驱动，避免隐藏期无效 resize 与侧栏折叠导致的尺寸错乱）。
7. **React Compiler 友好**：适配器为常规函数组件，无渲染期副作用；`exclude`/`include` 引用经 `useMemo([])` 固化，与编译器/lint 兼容。

---

## <a id="6-兼容性与边界"></a>6. 兼容性与边界

- **登录/登出/刷新**：Shell 卸载即清缓存（登出）；刷新后从零开始（`PageStateStore` 继续承担跨刷新状态）。登录页结构上在 Shell 外，且已在黑名单显式排除。
- **错误边界**：每个缓存节点经 `errorElement=RouteBoundary`（ErrorBoundary + Suspense），单页崩溃不扩散。隐藏页抛错后切回，该层错误态保留到下次导航（`resetKey` 为各自路由 pathname），可接受；二期可加"激活即 reset"。
- **StrictMode 硬约束**：库官方要求**开发模式不能使用 `<React.StrictMode />`**（双倍挂载导致缓存行为不可预期），`main.tsx` 已移除 StrictMode 包裹。生产模式下 StrictMode 本是 no-op，影响仅限开发期自检能力。
- **已知限制（LocationContext 不冻结）**：库不冻结失活页的 `LocationContext`。失活页不发生自重渲染（库保存的元素引用不变，React 跳过协调），仅当其自身状态变化触发重渲染时才会读到实时 location；轮询/SSE 已按 `active` 暂停，残余触发窗口很小。当前无页面在失活期依赖 location，若将来新增此类页面需评估。
- **行为变化**：query/hash 变化 → 重挂载，与"实例保留"的差异需明文告知。
- **库版本耦合**：本项目 React 19.2 + RR v7 → 用 `@6` 两个包；将来升 RR v8 还要求 Node ≥ 22.22 + React ≥ 19.2.7。升级时回归缓存行为。

---

## <a id="7-后果consequences"></a>7. 后果（Consequences）

### 正面

- 切回页面零请求、零 loading，状态/滚动/图表完整保留，重页面体验显著提升。
- **复用成熟库**：LRU、黑白名单、活动态、错误边界均由库提供，维护责任外包，自研代码量低（适配器 + 配置 + 滚动恢复）。
- 失活页 DOM 移出文档 + 后台暂停 + LRU 硬上限，性能与内存可控。
- 库 MIT、6KB、零传递依赖，bundle 影响小。

### 负面 / 成本

- **引入第三方依赖**：库的后续维护/发版节奏不在本团队控制；版本与 React/RR 耦合（升 RR v8 有 Node/React 下限）。
- **StrictMode 移除**：失去开发期双倍渲染自检；副作用清理改由 `active` 语义与单测兜底。
- **LocationContext 不冻结**：与自研实现相比少一层安全网（见 §6）。
- blacklist 全开带来持续的接入维护成本（新页面检查清单）。

### 风险 / 注意

- 新页面忘接 `useKeepAliveContext().active` 会后台空转 → 检查清单 + review 关注。
- 隐藏页抛错后切回可见错误态（到下次导航才重置）→ 二期加"激活即 reset"。
- `maxCacheSize` 需按实际内存表现调整（默认 8）。
- 库停止维护风险 → 实现本质是其手作版（与自研 v1/v2 同构），必要时可回退自研。

---

## <a id="8-改动清单代码执行指引"></a>8. 改动清单（代码执行指引）

**新增 / 保留**

| 文件 | 职责 |
| --- | --- |
| `src/router/keepAliveConfig.ts` | 配置真源（纯常量：`exclude`/`include`/`maxAliveTime`/`maxCacheSize`） |
| `src/components/layout/KeepAliveOutlet.tsx` | 适配层：`KeepAliveRouteOutlet` + `RouteScrollRestoration` + 私有 `toMatchRules` |
| `src/contexts/ScrollContainerContext.tsx` | 滚动容器 ref Context（`Main` 提供，`KeepAliveOutlet` 消费） |
| `src/components/layout/__tests__/keepAliveConfig.test.ts` | 配置形态单测（3 个） |
| `src/components/layout/__tests__/KeepAliveOutlet.test.tsx` | 库集成测试（4 个） |

**修改**

| 文件 | 改动 |
| --- | --- |
| `src/components/layout/Shell.tsx` | 1 行：`RouteOutletBoundary` → `KeepAliveOutlet` |
| `src/components/layout/Main.tsx` | 提供 `ScrollContainerContext`（约 8 行） |
| `src/main.tsx` | 移除 `<StrictMode>`（库开发模式不兼容），附头注释说明 |
| `src/pages/reviewPage.tsx` | `useKeepAliveContext().active` 控制 `enabled` |
| `src/pages/Market/StockDashboardPage/StockDashboardPage.tsx` | interval 受 `active` 门控 |
| `src/pages/News/LiveNewsPage/LiveNewsPage.tsx` | `useLiveNews` 增加 `enabled` 参数并门控 |
| `src/pages/ErrorPage/RouteBoundary.tsx` | 补充注释：`RouteOutletBoundary` 在缓存场景下禁用（`Outlet` 无法固化已捕获元素） |
| `documents/CHANGELOG.md` | `[Unreleased]` 追加一条 |

**已删除（被库能力取代）**

| 文件 | 原职责 |
| --- | --- |
| `src/router/keepAliveCache.ts` | LRU 纯函数（现由库 `max` 承担） |
| `src/contexts/PageActivityContext.tsx` | 页面活动态（现由库 `useKeepAliveContext().active` 承担） |

**不动**：`PageStateStore`、`types/router.ts`、`asyncRouteFactory.ts`、路由注册链路、其余页面、后端。

---

## <a id="9-测试与验证计划"></a>9. 测试与验证计划

**单元（vitest）— `keepAliveConfig.test.ts`**

- `include` 默认空（黑名单语义）；
- `maxAliveTime` 为 0（不过期）；
- `maxCacheSize` 为 8；
- `exclude` 覆盖登录页、流式对话、调试模块（`/docs/*`）、兜底页。

**组件（RTL + `createMemoryRouter`）— `KeepAliveOutlet.test.tsx`**

- 缓存页 A 输入/计数 → 跳 B → 跳回 A：值仍在（`aliveMounts` 恒为 1，实例未重挂载）。
- 黑名单页（`/docs/*`）跳走再跳回：计数清零（离开即销毁、返回重新挂载）。
- 缓存键含 hash：A → A#two，计数清零（hash 变化触发重挂载）。
- 前缀规则精度：`/docsX`（与 `/docs/*` 同前缀）仍参与缓存（验证 `toMatchRules` 不误伤）。

**门禁与手工验证**

- `cd apps/hrs-web && npm run lint && npm run build && npm test`（AGENTS.md web-gate）。
- DevTools：连续切换 6+ 路由，Performance 录制无 long task；隐藏页无网络请求（轮询/SSE 暂停）；滚动位置逐页恢复；heap 快照稳定。

---

## <a id="10-评审决策记录"></a>10. 评审决策记录

| # | 决策点 | 结论 |
| --- | --- | --- |
| 1 | 缓存模式 | **blacklist（黑名单）**：除清单外全部缓存；白名单能力保留在配置字段中，填入 `include` 即可切换 |
| 2 | 配置载体 | 单一前端配置文件 `src/router/keepAliveConfig.ts`（纯 TS 常量，无新依赖、无环境变量） |
| 3 | 名单匹配键 | **pathname**（核实结论：menuId ≠ pathname；pathname 即 URL 直观可预期，`/docs/*` 一条规则排除调试模块，且无需透传 routerKey） |
| 4 | query/hash 变化 | **重挂载**（替换缓存元素，语义可预期） |
| 5 | 滚动容器获取 | **方案 A：`Main.tsx` 经 `ScrollContainerContext` 下发 ref**（显式契约、类型安全，不耦合 CSS 类名） |
| 6 | 登录/注册页 | **加入黑名单**（`/login`；当前无注册路由，若后续新增 `/register` 一并加入） |
| 7 | manifest 级 per-route 开关 | 不做（避免双真源；黑名单已满足需求） |
| 8 | 实现底座 | **采用第三方库 `keepalive-for-react` + `keepalive-for-react-router`**（2026-10-14 用户决策，v3 起取代自研 v1/v2）；代价：开发模式移除 StrictMode、LocationContext 不冻结 |

---

## <a id="11-修订历史"></a>11. 修订历史

| 日期 | 版本 | 变更 |
| --- | --- | --- |
| 2026-10-14 | v1 | 初稿：按评审结论定稿——blacklist 默认、pathname 匹配、ScrollContainerContext（方案 A）、query/hash 重挂载、登录页入黑名单、无 routerKey 透传改动 |
| 2026-10-14 | v2 | 实现完成并回写两条实现期修正；验证：新增 17 测试全过；A/B 全量对比失败数 235 vs 235 一致、通过 +17，零回归 |
| 2026-10-14 | v3 | 实现改为第三方库 `keepalive-for-react@6` + `keepalive-for-react-router@6`：选型表新增方案 E 并标记 C 被取代；自研 `keepAliveCache.ts`、`PageActivityContext.tsx` 删除；`main.tsx` 移除 StrictMode；三个页面改 `useKeepAliveContext().active`；保留黑名单单一配置真源、`maxCacheSize=8`、query/hash 重挂载、ScrollContainerContext 滚动恢复、新页面检查清单 |
| 2026-10-15 | v4 | 文档整体更新为库实现现状：移除 v1/v2 自研细节与 v3 补丁块；§4.2/§4.3/§4.5/§8 重写为库实际行为（`keepAliveCache`/`PageActivityContext` 已删除、`PageActivityContext` 改 `useKeepAliveContext`、配置改 `exclude`/`include`/`maxAliveTime`/`maxCacheSize`）；文件更名为 `frontend_route_keepalive.md` |
