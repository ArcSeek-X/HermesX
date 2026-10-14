# <a id="adr-002hermesx-前端路由缓存keep-alive架构设计"></a>ADR-002：HermesX - 前端路由缓存（Keep-Alive）架构设计

> 📝 **方案简述**：本 ADR 确立 HermesX Web 前端（`apps/hrs-web`）路由缓存的全局设计基准：切换路由时页面实例保留、切回时状态（表单/筛选项/Tab/滚动位置/已加载数据/图表实例）留存，不重新请求、不出现 loading；缓存范围由单一前端配置文件以**黑名单（pathname）**控制；缓存管理采用"捕获路由元素 + 冻结 LocationContext + LRU 硬上限 + 后台页暂停"四件套，保证切换不卡顿、后台不空转、内存有界。任何前端路由/布局改动与本 ADR 冲突，均以本 ADR 为准。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-14

## 方案目录

- [浏览目录](#浏览目录)
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
  - [4.2 缓存状态机](#42-缓存状态机)
  - [4.3 冻结 LocationContext](#43-冻结-locationcontext)
  - [4.4 黑名单配置（单一配置文件）](#44-黑名单配置单一配置文件)
  - [4.5 滚动位置保持（ScrollContainerContext）](#45-滚动位置保持scrollcontainercontext)
  - [4.6 后台页暂停（usePageActive）](#46-后台页暂停usepageactive)
  - [4.7 新页面接入检查清单](#47-新页面接入检查清单)
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
| 文档类型 | 架构决策记录（Architecture Decision Record） |
| 编号 | ADR-002 |
| 状态 | **已采纳（Accepted）** |
| 关联方案 | `ADR-001`（后端分层架构，同为全局架构基准）；前端实现落地时同步更新 `docs/CHANGELOG.md` 与专题文档 |
| 适用范围 | HermesX Web 前端 `apps/hrs-web`（**全域前端架构基准**；首个落地范围：路由缓存能力） |

> **方案用意**：本 ADR 是 HermesX 前端的**全局架构决策基准**，面向整个 Web 前端工程，不隶属于任何单一功能方案。它确立四项设计立场：① 路由缓存以**页面实例保留**为实现手段（而非状态提升）；② 缓存范围由**单一前端配置文件的黑名单（pathname）**控制，默认全开、显式排除；③ 缓存实现**复用 React Router 自身渲染管线**（`useOutlet` 捕获 + 冻结 `LocationContext`），不引入第三方 keep-alive 库、不建平行路由渲染层；④ 性能三铁律——隐藏层零布局零绘制、后台页暂停轮询/SSE、`maxCacheSize` LRU 硬上限。
>
> **指导方针**：任何前端方案 / 代码改动若与本 ADR 冲突，均以本 ADR 为准；本 ADR 不被任何单一功能方案"拥有"或"限定"。

> ⚠️ **2026-10-14 修订（v3）：实现由自研改为基于第三方库 `keepalive-for-react`。** 经用户决策，`KeepAliveOutlet` 改为封装 `keepalive-for-react@6` + `keepalive-for-react-router@6`（适配 React 19.2 / React Router v7，两个包均为 MIT、6KB、零传递依赖）。
>
> **仍然有效的设计立场**：黑名单单一配置真源（`src/router/keepAliveConfig.ts`，匹配键 pathname，`/docs/*` 前缀规则）、`maxCacheSize=8` LRU 硬上限、query/hash 变化重挂载、滚动位置保存/恢复（`ScrollContainerContext`，方案 A）、新页面接入检查清单（§4.7）、缓存随 Shell 卸载销毁。
>
> **已被库能力取代、不再适用的章节**：§4.2 缓存状态机（槽位/扁平 keyed 数组/LRU 细节移交库内部）、§4.3 冻结 `LocationContext`（库不冻结，见下方已知差异）、§4.6 `usePageActive`（改为 `useKeepAliveContext().active`）、§8 改动清单中的自研文件部分（`keepAliveCache.ts`、`PageActivityContext.tsx`、原 `KeepAliveOutlet.tsx` 已删除）。
>
> **新增硬约束**：库官方要求**开发模式下不能使用 `<React.StrictMode />`**（双倍挂载导致缓存行为不可预期），`main.tsx` 已移除 StrictMode 包裹（详见该文件头注释；生产模式下 StrictMode 本是 no-op，影响仅限开发期自检能力）。
>
> **已知语义差异**：库不冻结失活页的 `LocationContext`。失活页不发生自重渲染（库保存的元素引用不变，React 跳过协调），仅当其自身状态变化触发重渲染时才会读到实时 location；轮询 / SSE 已按 `active` 暂停，残余触发窗口很小（评估记录见 `.claude/reviews/frontend-route-keepalive-design.md` 附录）。

---

## <a id="浏览目录"></a>浏览目录

- [1. 背景](#1-背景--上下文context)
  - [1.1 目标](#11-目标goals)
  - [1.2 非目标](#12-非目标non-goals)
- [2. 现状分析](#2-现状分析已核实事实)
- [3. 方案选型](#3-方案选型alternatives-considered)
- [4. 总体设计](#4-总体设计)
- [5. 性能设计](#5-性能设计)
- [6. 兼容性与边界](#6-兼容性与边界)
- [7. 后果](#7-后果consequences)
- [8. 改动清单](#8-改动清单代码执行指引)
- [9. 测试与验证](#9-测试与验证计划)
- [10. 评审决策记录](#10-评审决策记录)
- [11. 修订历史](#11-修订历史)

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
- 渲染链：`Shell` → `Main`（唯一滚动容器 `main.hrs-page-container`）→ `RouteOutletBoundary`（ErrorBoundary + Suspense）→ `Outlet` → 页面组件。
- 登录页 `/login` 是 **Shell 外的顶层路由**（`appRouter.tsx` 中与 `protected` 平级）；404 兜底 `/404` 在 Shell 内。

### <a id="22-页面副作用清单"></a>2.2 页面副作用清单

| 页面 | 后台行为 |
| --- | --- |
| `reviewPage`（/review） | `useDashboardLifecycle`：30s 轮询 + 共享 SSE（`useTaskStream`）+ 自有轮询定时器 |
| `StockDashboardPage`（/market/index） | 自有 `setInterval` 行情刷新 |
| `LiveNewsPage`（/news/live-news） | `useLiveNews` 轮询（hook 目前无 `enabled` 参数，需小改支持） |
| `ChatPage`（/choose/chat） | 仅 toast/copy 类短定时器；使用 `setSearchParams`，**加入黑名单** |
| `HomePage` | 纯搜索入口，无轮询 |

`useTaskStream` 是模块级共享 `EventSource` + 订阅者计数：订阅者清零即断连，因此 `enabled=false` 可以干净地暂停/恢复 SSE。

### <a id="23-关键技术结论读源码验证"></a>2.3 关键技术结论（读源码验证）

1. RR v7.13 导出公共 API `useOutlet()` / `useMatches()`；`react-router-dom` 通过 `export * from 'react-router'` 再导出 `UNSAFE_LocationContext`。
2. `_renderMatches` 以 **props** 把 `routeContext`（含 `matches`/`params`）传给 `RenderedRoute`，后者渲染 `RouteContext.Provider`（`react-router/dist/production/chunk-EFMJ2SG4.mjs`）。→ 通过 `useOutlet()` 捕获到的页面元素，其**路由上下文是值冻结的**；之后在别处重渲染该元素，`useParams` 等仍读到原路由的匹配信息。
3. 全仓页面实际使用的路由 API 只有 `useNavigate`（需保持活的全局导航）与 `useSearchParams`（ChatPage/LoginCard）；**没有页面使用 `useParams`/`useLoaderData`/`useMatches`**（已全量 grep `src/pages`）。`useLocation/useSearchParams` 读根级 `LocationContext`（随导航变化）→ **缓存页必须冻结 `LocationContext`**，否则隐藏页会读到当前路由的 location。
4. 工程约束：项目启用 **React Compiler**（`vite.config.ts` 的 `babel-plugin-react-compiler`）+ `eslint-plugin-react-hooks` v7 `flat.recommended`，其中 `set-state-in-render` / `purity` / `refs` 均为 **Error** 级。→ **渲染期禁止副作用、写 ref、无条件 setState**；只允许 React 官方"条件守卫的派生状态更新"模式。本方案据此设计。
5. 已扫描 `global.scss` 与全部页面：无全局 CSS 以 `.hrs-page-container` 直接子选择器 / `:first-child` / `:last-child` 影响页面根元素 → 在滚动容器内追加 `display:none` 隐藏层不会影响现有页面布局。
6. 核实结论：**menuId ≠ pathname**（如 `index` → `/market/index`、`kline` → `/stock/kline`），故黑名单匹配键采用 pathname。

### <a id="24-与-pagestatestore-的关系"></a>2.4 与 PageStateStore 的关系

`PageStateStore`（L2 内存 + L3 sessionStorage）是"手动状态提升"，能跨刷新保留，但保留不了组件实例、DOM、滚动位置和图表实例。两者**互补**，本方案不动它。

---

## <a id="3-方案选型alternatives-considered"></a>3. 方案选型（Alternatives Considered）

| 方案 | 结论 | 理由 |
| --- | --- | --- |
| A. 第三方 `react-activation` | ❌ | React 19 兼容性无官方确认（StrictMode/并发下有已知问题报告）；面向 RR v5/v6 的 Switch 模式，与 data router + `Outlet` 集成需额外适配；引入依赖即引入一套平行的路由缓存实现 |
| B. 扩展 `PageStateStore` 做全量状态提升 | ❌ | 保留不了实例/DOM/滚动/图表，需逐页面手工改造，改造成本高于本方案且易漏 |
| C. 自研 `KeepAliveOutlet`（`useOutlet` 捕获元素 + 冻结 `LocationContext` + LRU） | ⛔ 已被 E 取代（v3 起废弃） |  v1/v2 期的实现路径；可控可测，但需自行维护槽位协调、LRU、上下文冻结等全部机制，长期维护成本高于成熟库 |
| D. 自建平行路由渲染层（自行解析页面组件、逐层渲染） | ❌ | 绕开 RR 路由渲染即"平行实现"，丢失 `params`/`loaderData`/`matches` 语义，违背仓库"不新增平行实现"约束 |
| E. 第三方 `keepalive-for-react@6` + `keepalive-for-react-router@6` | ✅ **采纳（v3 起）** | 340 star / 144 commits / 2026 年活跃发版 / MIT / 6KB；官方支持 React Router v6/v7/v8 与 React 19.2；提供 `max`（LRU）、`exclude`/`include`、`useKeepAliveContext().active`（后台暂停）、`errorElement`、`useEffectOnActive` 等能力，与本 ADR 的黑名单 / 上限 / 暂停诉求一一对应；失活页 DOM 节点被移出文档（实例保留、零绘制）。**代价**：① 官方要求开发模式不用 StrictMode；② 不冻结失活页 LocationContext（见文首修订说明） |

---

## <a id="4-总体设计"></a>4. 总体设计

### <a id="41-挂载点与渲染结构"></a>4.1 挂载点与渲染结构

`Shell.tsx` 一处改动：`{children ?? <RouteOutletBoundary />}` → `{children ?? <KeepAliveOutlet />}`。

```
Shell
└─ Main（滚动容器，经 ScrollContainerContext 暴露 ref）
   └─ KeepAliveOutlet
      └─ RouteBoundary（ErrorBoundary + Suspense，沿用 RouteOutletBoundary 语义）
         ├─ [在线页] 缓存页 → 直接渲染缓存元素（不套 DOM 包裹，布局与今天完全一致）
         │            非缓存页 → <Outlet />（与今天完全一致）
         └─ [隐藏层] <div style="display:none" inert aria-hidden data-keep-alive-key="...">
                       <UNSAFE_LocationContext.Provider value={冻结 location}>
                         <PageActivityContext.Provider value={false}>
                           <RouteBoundary fullPage={false}>{缓存元素}</RouteBoundary>
```

设计要点：

- **在线页不套 DOM 包裹**：`h-full` 链、flex 子项关系、`Main` 的 `contain`/padding 契约零变化，回归面最小。
- **隐藏层 `display:none`**：不参与布局/绘制/合成，浏览器开销接近 0；`inert` 阻止焦点与交互泄漏。
- **每层独立错误边界**：单个缓存页崩溃不扩散到其他层与在线页。

### <a id="42-缓存状态机"></a>4.2 缓存状态机

```ts
type CacheEntry = { key: string; element: React.ReactElement; location: Location };
```

- **缓存键（entries key）** = `pathname`（当前 manifest 全为静态路径，无参数路由；未来引入 `/stock/:code` 等参数路由时需在此扩展 key，否则不同参数会共用同一实例）。
- **槽位 key（React key）** = `pathname + search + hash`：query/hash 变化即换槽位触发重挂载（决策 4）。槽位 children 必须是**一次 `map` 产出的扁平 keyed 数组**——嵌套的 `[当前槽位, ...隐藏槽位数组]` 会被 React 按位置协调，导致当前槽位每次导航都被卸载重挂、实例状态全部丢失（实现期由组件测试锁定，勿改回嵌套结构）。
- **首次访问缓存页**：`useOutlet()` 拿到元素 E，以"条件守卫的渲染期 `setState`"写入 entries（React 官方 derived-state 模式，`set-state-in-render` lint 放行；`activeSlot` 初值为 null，使首屏直载的页面同样入缓存）；同一轮重渲染即从 entries 取 E 渲染 → **同元素对象、同位置、同 key → React 协调保留实例，无二次挂载**。
- **再次访问**（entries 已存在且 query/hash 一致）：渲染 entries 中的旧元素 → 实例/状态/滚动/数据全部保留；只做 LRU touch，**绝不替换元素**。
- **query/hash 变化**：视为新访问，替换元素（重挂载）——语义可预期，避免"实例还在但 URL 状态不一致"。
- **LRU**：entries 超过 `maxCacheSize` 时淘汰队尾；刚访问的在线页位于队首，永不被淘汰。
- **生命周期边界**：entries 是 `KeepAliveOutlet` 的 state → Shell 卸载（登出跳 `/login`）或整页刷新时自动销毁，**无需手动清理逻辑**；登录时的 `patchRoutes` 重建发生在 Shell 挂载前，不涉及存量缓存。

### <a id="43-冻结-locationcontext"></a>4.3 冻结 LocationContext

隐藏层用 `UNSAFE_LocationContext.Provider` 提供捕获时的 location，使缓存页的 `useLocation/useSearchParams` 仍反映自己的路由；`useNavigate` 仍走活的 `NavigationContext`，导航语义不变。

**实现要点（已踩坑）**：该 Context 的 value 是 `{ location, navigationType }` 包装结构（`useLocation()` 内部读 `.location`），**不是裸 `Location`**——直接传裸 Location 会使 `useLocation()` 返回 undefined、整棵子树抛 `Cannot read properties of undefined (reading 'pathname')`。`navigationType` 用公共 API `useNavigationType()` 取值（满足 `Action` 枚举类型；缓存页无消费方读取它）。这是全方案**唯一**使用的 UNSAFE API：RR 升级时若导出消失，TS 编译期直接失败（可见、可修），并用测试锁定行为。

### <a id="44-黑名单配置单一配置文件"></a>4.4 黑名单配置（单一配置文件）

新增 `src/router/keepAliveConfig.ts`：

```ts
export type KeepAliveMode = 'blacklist' | 'whitelist';

export interface KeepAliveConfig {
  /** blacklist=除清单外都缓存（默认）；whitelist=仅清单内缓存 */
  mode: KeepAliveMode;
  /** 路由 pathname 清单：精确路径，或以 `*` 结尾的前缀规则（如 '/docs/*'） */
  routes: string[];
  /** 缓存页数量硬上限（LRU），内存护栏 */
  maxCacheSize: number;
}

export const KEEP_ALIVE_CONFIG: KeepAliveConfig = {
  mode: 'blacklist',
  routes: [
    '/login',       // 登录页（结构上在 Shell 外，双保险；后续新增 /register 一并加入）
    '/choose/chat', // 流式对话 + setSearchParams，实例缓存语义不安全
    '/docs/*',      // 组件调试模块（20 页一条规则）
    '/codeTest',    // 调试页
    '/404',         // 兜底页
  ],
  maxCacheSize: 8,
};

/** 规则匹配：`*` 结尾按前缀匹配（含自身），否则精确匹配 */
const matchesRule = (pathname: string, rule: string): boolean => {
  if (!rule.endsWith('*')) return pathname === rule;
  const base = rule.slice(0, -1).replace(/\/$/, '');
  return pathname === base || pathname.startsWith(`${base}/`);
};

export const isKeepAliveRoute = (
  pathname: string,
  config: KeepAliveConfig = KEEP_ALIVE_CONFIG,
): boolean => {
  const matched = config.routes.some((rule) => matchesRule(pathname, rule));
  return config.mode === 'blacklist' ? !matched : matched;
};
```

要点：

- **匹配键为 pathname**：黑名单是人工维护的排除清单，pathname 即 URL，直观可预期；无需把 routerKey 透传到 route.handle，`types/router.ts` 与 `asyncRouteFactory.ts` **零改动**。
- 当前路由判定直接用 `useLocation().pathname`，与缓存 key 同源。
- `whitelist` 能力保留在类型中（一行切回），不作为默认。
- `maxCacheSize` 是内存护栏，默认 8；blacklist 全开模式下它是唯一硬上限，更重要。

### <a id="45-滚动位置保持scrollcontainercontext"></a>4.5 滚动位置保持（ScrollContainerContext）

- `Main.tsx` 新增约 8 行：`useRef` 持有 `<main>`，外层包 `ScrollContainerContext.Provider`，`<main>` 挂 ref。契约显式、类型安全、不依赖 CSS 类名；将来其他组件需要滚动容器可直接复用。
- `KeepAliveOutlet` 通过 `useContext` 取到滚动容器：passive `scroll` 监听持续把当前偏移按 key 写入 `useRef<Map>`（规避 display:none 切换时浏览器钳制 scrollTop 的问题）；`useLayoutEffect` 在 key 切换时先存旧值、再把目标 key 的值写回 `scrollTop`。layout effect 在 paint 前同步执行 → 无闪烁。
- **不引入每页独立滚动容器**：避免改动 `Main` 的 `contain`/LightBloom/padding 契约。

### <a id="46-后台页暂停usepageactive"></a>4.6 后台页暂停（usePageActive）

- 新增 `src/contexts/PageActivityContext.tsx`：导出 `usePageActive(): boolean`；在线层 Provider `value=true`，隐藏层 `false`。
- 页面侧最小接入（首批只接有轮询/SSE 的，其余页面零改动即受益）：
  - `reviewPage`：`const isActive = usePageActive(); useDashboardLifecycle({ ..., enabled: isActive })`。hook 已支持 `enabled`；`enabled` 恢复时首载 effect 自动重跑 → **切回即刷新，数据不陈旧**。
  - `StockDashboardPage`：interval effect 增加 `isActive` 依赖。
  - `LiveNewsPage`：`useLiveNews` 增加 `enabled` 参数并门控轮询（小改）。
- `ChatPage` 在黑名单中，无需处理。

### <a id="47-新页面接入检查清单"></a>4.7 新页面接入检查清单

blacklist 意味着新页面默认进缓存，新增页面时确认：

1. 有轮询/SSE/定时器 → 接 `usePageActive()` 控制 `enabled`（否则后台空转）。
2. 有 echarts / lightweight-charts → 激活时 resize（可用 `usePageActive` 驱动）。
3. 流式进行中、长表单编辑等实例保留语义不安全的页面 → 加入黑名单。
4. 参数路由 → key 已含 params，无需额外处理。

---

## <a id="5-性能设计"></a>5. 性能设计

1. **渲染开销**：非缓存路径与今天完全同路；缓存路径每次导航仅一次条件守卫 `setState`（≤8 长度数组操作），无轮询、无监听器风暴。
2. **布局/绘制**：隐藏层 `display:none` → 零布局零绘制；在线页无包裹 DOM → 与今天一致。
3. **后台空转**：隐藏页轮询/SSE 经 `enabled` 暂停；共享 EventSource 订阅者清零即断连，不占连接数。
4. **切换流畅性**：切回 = 可见性翻转 + scrollTop 恢复，无重挂载、无重新请求、无 loading 态；scroll 恢复先于 paint。
5. **内存**：`maxCacheSize` LRU 硬上限；淘汰即卸载，页面 cleanup（`clearInterval`/关闭 SSE/echarts dispose）正常执行。
6. **图表**：echarts 页在激活时按需 resize（二期，`usePageActive` 驱动，避免隐藏期无效 resize 与侧栏折叠导致的尺寸错乱）。
7. **React Compiler 友好**：无渲染期副作用；元素入 state 属合法用法；缓存元素同 key 同位置 → 协调稳定。

---

## <a id="6-兼容性与边界"></a>6. 兼容性与边界

- **登录/登出/刷新**：Shell 卸载即清缓存（登出）；刷新后从零开始（`PageStateStore` 继续承担跨刷新状态）。登录页结构上在 Shell 外，且已在黑名单显式排除。
- **错误边界**：在线页由外层 `RouteBoundary` 覆盖（同今天）；隐藏层各自包 `RouteBoundary`，单页崩溃不扩散。隐藏页抛错后切回，该层错误态保留到下次导航（`resetKey` 为冻结 location），可接受；二期可加"激活即 reset"。
- **已知限制**（写入专题文档）：缓存页内 `useNavigation()/useLoaderData()/useRevalidator()` 会读到当前路由状态（当前无页面使用）；参数路由 key 已含 params，无需改结构。
- **行为变化**：query/hash 变化 → 重挂载，与"实例保留"的差异需在专题文档明示。
- **RR 升级风险**：依赖 `RenderedRoute` 以 props 传 `routeContext` 的内部行为 + 一个 UNSAFE 导出；用组件测试锁定"隐藏页 `useLocation` 仍为自身路径""params 冻结"。

---

## <a id="7-后果consequences"></a>7. 后果（Consequences）

### 正面

- 切回页面零请求、零 loading，状态/滚动/图表完整保留，重页面体验显著提升。
- 无新依赖；复用 RR 渲染管线，缓存页与在线页契约一致。
- 隐藏层零绘制 + 后台暂停 + LRU 硬上限，性能与内存可控。
- 回滚成本极低（revert 一个组件 + 一行 Shell 改动即回到现状）。

### 负面 / 成本

- 依赖 RR 内部行为（props 传 routeContext）+ 一个 UNSAFE 导出，升级 RR 需回归。
- 缓存页数据可能陈旧（隐藏期间不刷新），依赖"激活刷新"缓解。
- blacklist 全开带来持续的接入维护成本（新页面检查清单）。
- query/hash 变化重挂载属于行为变化，需文档明示。

### 风险 / 注意

- 新页面忘接 `usePageActive` 会后台空转 → 检查清单 + review 关注。
- 隐藏页抛错后切回可见错误态（到下次导航才重置）→ 二期加"激活即 reset"。
- `maxCacheSize` 需按实际内存表现调整（默认 8）。

---

## <a id="8-改动清单代码执行指引"></a>8. 改动清单（代码执行指引）

**新增**

| 文件 | 职责 |
| --- | --- |
| `src/router/keepAliveConfig.ts` | 配置 + `isKeepAliveRoute`（pathname 匹配） |
| `src/router/keepAliveCache.ts` | `CacheEntry` 类型 + `upsertEntry`（LRU 纯函数） |
| `src/components/layout/KeepAliveOutlet.tsx` | 核心组件 |
| `src/contexts/PageActivityContext.tsx` | `usePageActive` |
| `src/contexts/ScrollContainerContext.tsx` | 滚动容器 ref Context |
| `src/router/__tests__/keepAliveCache.test.ts` | 纯函数单测 |
| `src/components/layout/__tests__/KeepAliveOutlet.test.tsx` | 组件测试 |

**修改**

| 文件 | 改动 |
| --- | --- |
| `src/components/layout/Shell.tsx` | 1 行：`RouteOutletBoundary` → `KeepAliveOutlet` |
| `src/components/layout/Main.tsx` | 提供 `ScrollContainerContext`（约 8 行） |
| `src/pages/reviewPage.tsx` | `enabled: isActive` 接入 |
| `src/pages/Market/StockDashboardPage/StockDashboardPage.tsx` | interval 受 `isActive` 门控 |
| `src/pages/News/LiveNewsPage/LiveNewsPage.tsx` | `useLiveNews` 增加 `enabled` 参数并门控 |
| `src/hooks/useLiveNews.ts` | 增加 `enabled` 参数 |
| `docs/CHANGELOG.md` | `[Unreleased]` 追加一条 |

**不动**：`PageStateStore`、`types/router.ts`、`asyncRouteFactory.ts`、路由注册链路、其余页面、后端。

---

## <a id="9-测试与验证计划"></a>9. 测试与验证计划

**单元（vitest）**

- `upsertEntry`：插入 / touch 不替换元素 / query 变化替换 / LRU 淘汰 / 在线页不被淘汰。
- `isKeepAliveRoute`：精确匹配 / `*` 前缀匹配（含自身）/ blacklist 与 whitelist 两种模式 / 未知路径默认缓存。

**组件（RTL + `createMemoryRouter`）**

- 缓存页 A 输入文字 → 跳 B → 跳回 A：文字仍在（实例保留）。
- 隐藏层 `display:none`（`not.toBeVisible()`）且层内 `usePageActive` 渲染值为 false。
- 黑名单页（如 `/choose/chat`）：跳走再跳回，状态丢失（重挂载）。
- 超过 `maxCacheSize`：最久未用页的卸载 cleanup 执行、隐藏层中不再存在。
- 冻结 location：隐藏层中渲染 `useLocation().pathname` 的文本仍是 A 的路径。

**门禁与手工验证**

- `cd apps/hrs-web && npm run lint && npm run build && npm test`（AGENTS.md web-gate）。
- DevTools：连续切换 6+ 路由，Performance 录制无 long task；隐藏页无网络请求（轮询/SSE 暂停）；滚动位置逐页恢复；heap 快照稳定。
- e2e（playwright，二期可选）：状态保持冒烟。

---

## <a id="10-评审决策记录"></a>10. 评审决策记录

| # | 决策点 | 结论 |
| --- | --- | --- |
| 1 | 缓存模式 | **blacklist（黑名单）**：除清单外全部缓存；whitelist 能力保留在配置类型中，一行可切回 |
| 2 | 配置载体 | 单一前端配置文件 `src/router/keepAliveConfig.ts`（纯 TS 常量，无新依赖、无环境变量） |
| 3 | 名单匹配键 | **pathname**（核实结论：menuId ≠ pathname；pathname 即 URL 直观可预期，`/docs/*` 一条规则排除调试模块，且无需透传 routerKey） |
| 4 | query/hash 变化 | **重挂载**（替换缓存元素，语义可预期） |
| 5 | 滚动容器获取 | **方案 A：`Main.tsx` 新增 `ScrollContainerContext`**（显式契约、类型安全，不耦合 CSS 类名） |
| 6 | 登录/注册页 | **加入黑名单**（`/login`；当前无注册路由，若后续新增 `/register` 一并加入） |
| 7 | manifest 级 per-route 开关 | 不做（避免双真源；黑名单已满足需求） |

---

## <a id="11-修订历史"></a>11. 修订历史

| 日期 | 版本 | 变更 |
| --- | --- | --- |
| 2026-10-14 | v1 | 初稿：按评审结论定稿——blacklist 默认、pathname 匹配、ScrollContainerContext（方案 A）、query/hash 重挂载、登录页入黑名单、无 routerKey 透传改动 |
| 2026-10-14 | v2 | 实现完成并回写两条实现期修正：① `UNSAFE_LocationContext` value 为 `{ location, navigationType }` 包装结构而非裸 Location（§4.3）；② 槽位 children 必须为扁平 keyed 数组，嵌套数组会被按位置协调导致每次导航重挂载（§4.2）。验证：新增 17 测试全过；A/B 全量对比失败数 235 vs 235 一致、通过 +17，零回归 |
| 2026-10-14 | v3 | **实现改为第三方库 `keepalive-for-react@6` + `keepalive-for-react-router@6`**（用户决策）：选型表新增方案 E 并标记 C 被取代；§4.2/§4.3/§4.6/§8 中自研机制相关内容移交库内部；新增硬约束——`main.tsx` 移除 StrictMode（库开发模式不兼容）；新增已知差异——库不冻结失活页 LocationContext。保留立场不变：黑名单单一配置真源、`maxCacheSize=8`、query/hash 重挂载、ScrollContainerContext 滚动恢复、§4.7 检查清单。验证：新增配置测试 6 + 集成测试 3 全过（实例/状态保留、黑名单离开即销毁、hash 重挂载）；layout 目录 5 个存量失败经 HEAD worktree 对照确认与本次无关；`eslint` 对本次改动文件零 error；`vite build` 的 22 个 TS 错误均为存量（位于未触及文件）；dev 服务器模块编译与依赖预打包验证通过 |
