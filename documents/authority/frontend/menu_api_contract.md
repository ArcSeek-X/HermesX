# 菜单树查询接口契约

更新时间：2026-11-23

## 1. 当前交付与接入范围

前端 API 入口为 `apps/hrs-web/src/api/system/menu.ts`，调用 `menuApi.getTree()`，返回 `Promise<NavMenuNode[]>`。节点类型直接复用 `apps/hrs-web/src/types/moduleMenu.ts`，与 `router/manifest.ts` 的 `MENU_MANIFEST` 共用一套字段、枚举和树结构。

已实现请求、统一响应解包、运行时契约校验和错误传递，并由 `router/loadMenuData.ts` 同时为菜单与路由加载数据。`router/manifest.ts` 中的开发调试开关 `USE_STATIC_MENU` 默认 `true`（静态清单）；设为 `false` 后，在登录成功时使用本接口获取菜单。开关是固定配置，不提供运行中的切换功能。接口失败向调用方抛出，不回退到静态清单或空数组。

本轮前端目标已改为 `POST /api/system/list-menu`。Java 的 `MenuController` 当前仍提供旧接口 `GET /api/system/menus/tree`，请求方法和地址尚未同步；当前 `MenuVO` 也仍返回 `parentId/name/type/path/component/sort/visible/status` 等旧字段，尚未满足本契约。当前文档与前端代码是后续 Java 和数据库调整的目标，不能据此前端测试宣称真实服务已联调通过。本文仅定义导航菜单树查询；菜单管理的新增、修改、删除、详情接口不在此次前端交付范围内。

## 2. 请求

| 项目 | 约定 |
| --- | --- |
| 方法 | `POST` |
| 地址 | `/api/system/list-menu` |
| 前端方法 | `menuApi.getTree()` |
| 请求体 | 无，不发送 JSON 数据；Java 接口无需声明必填的请求体 |
| 查询参数 | 当前不传，读取完整菜单树；不传管理搜索的 keyword/status，避免裁剪导航树 |
| 响应格式 | JSON，字段名统一使用 camelCase |
| 请求客户端 | 复用现有 `apiClient`，沿用已有 API 基础地址、超时和凭据设置 |
| 前端请求缓存 | POST 不进入通用 GET 缓存；登录成功时重新请求，返回后由两个 Store 沿用现有 localStorage 持久化 |

接口仍由服务端根据真实认证与授权决定可返回的数据；不以客户端传入企业或组织 ID 代替权限校验。本文不新增认证实现。

目前开发代理仍将 `/api` 指向 Python。真实联调时需安排 system 请求转发或相应部署入口，并确认认证凭据可用；Java 当前启用了 CSRF 防护，POST 接口真实接入时还需对齐 CSRF token 获取与携带方式；本阶段不更改代理、端口、Java 或数据库，不新增环境配置项。

## 3. 成功响应

外层类型为 `RestResult<NavMenuNode[]>`，定义在 `apps/hrs-web/src/types/restResult.ts`。`resultCode` 是字符串业务码，成功固定为 `"200"`；它与 HTTP 状态码属于不同层次。

```json
{
  "resultCode": "200",
  "resultMsg": "操作成功。",
  "resultData": [
    {
      "id": 1,
      "menuParentId": 0,
      "menuCode": "productModel",
      "menuName": "产品",
      "menuDescription": "产品使用模式菜单",
      "menuType": "module",
      "menuRoutePath": "/home",
      "menuIcon": "LayoutDashboard",
      "menuPosition": "content",
      "menuExpanded": false,
      "menuVisible": true,
      "menuSort": 0,
      "menuStatus": 1,
      "children": [
        {
          "id": 2,
          "menuParentId": 1,
          "menuCode": "research",
          "menuName": "股票研究",
          "menuDescription": "股票研究页面分组",
          "menuType": "group",
          "menuPosition": "content",
          "menuExpanded": true,
          "menuVisible": true,
          "menuSort": 0,
          "menuStatus": 1,
          "children": [
            {
              "id": 3,
              "menuParentId": 2,
              "menuCode": "watchlist",
              "menuName": "自选股",
              "menuDescription": "自选股管理",
              "menuType": "page",
              "menuRoutePath": "/watchlist",
              "menuPagePath": "pages/WatchlistPage/WatchlistPage",
              "menuIcon": "Star",
              "menuPosition": "content",
              "menuExpanded": false,
              "menuVisible": true,
              "menuSort": 0,
              "menuStatus": 1,
              "auth": "protected",
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

这是三层结构示例，不代表已经写入数据库，也不代表要求增加 manifest 中不存在的分组。实际菜单内容和页面路径以现有 manifest 为迁移依据；示例数字主键由数据库真实生成，不能把数组下标当作持久化 ID。

`resultData` 与 manifest 均为数组；根节点必须是 module，子节点为 group/page。所有节点使用同一种结构，仅 `menuType` 的值不同。

## 4. 节点字段

| 字段 | JSON 类型 | 必填 | 约定 |
| --- | --- | --- | --- |
| `id` | number | 否 | 数据库正整数主键；静态清单不需要。提供时必须在 JavaScript 安全整数范围内且全树唯一 |
| `menuParentId` | number | 否 | 根节点为 0；子节点对应父节点 id。提供时必须与 children 中的实际位置一致 |
| `menuCode` | string | 是 | 非空稳定业务标识，全树唯一；不等同于数字主键 |
| `menuName` | string | 是 | 名称，支持国际化键或直接文案 |
| `menuDescription` | string | 是 | 描述，无描述时返回空字符串 |
| `menuType` | string | 是 | module / group / page |
| `menuRoutePath` | string | page 必填 | 站内路由路径，以单个 `/` 开头；page 路由全树唯一 |
| `menuPagePath` | string | page 必填 | `pages/` 开头的前端页面模块路径；必须能由现有页面导入白名单解析 |
| `menuIcon` | string | 否 | 现有图标名称 |
| `menuBadge` | string | 否 | 预留徽标文本 |
| `menuPosition` | string | 是 | header / content / footer |
| `menuExpanded` | boolean | 是 | 默认是否展开，使用 true/false |
| `menuVisible` | boolean | 是 | 是否显示导航入口；隐藏不代表禁止路由访问 |
| `menuSort` | number | 是 | 同级升序排序值 |
| `menuStatus` | number | 是 | 0=禁用，1=启用；禁止返回字符串 "0"/"1" |
| `menuPermission` | string | 否 | 权限标识预留，不能替代服务端授权 |
| `children` | array | 否 | 同一类型的子节点数组；叶子省略或返回 []，不能返回 null；page 不含子节点 |
| `auth` | string | 否 | public / protected，保留当前 manifest 的路由扩展语义 |
| `exact` | boolean | 否 | 前端高亮扩展，是否精确匹配路径 |

可选字段无值时省略；字符串可选字段也可返回空字符串，page 必需的路径除外。不要为兼容旧 Java 响应同时返回 name/menuName、type/menuType 等双字段；数据库和 Java 调整时直接按目标契约输出。

API 方法校验后保留字段、顺序和隐藏/禁用节点，不负责 Store 的排序或过滤。页面文件的可解析性由前端路由层验证；远端数据不能提供可直接执行的组件代码或任意导入地址。实际页面仍需要随前端构建发布。

## 5. 失败与空数据

```json
{
  "resultCode": "403",
  "resultMsg": "无权访问菜单。",
  "resultData": null
}
```

| 情况 | 前端方法行为 |
| --- | --- |
| HTTP 成功且 resultCode 为 "200"、resultData 为合法树 | 返回 resultData |
| HTTP 成功且 resultCode 为 "200"、resultData 为 [] | 返回 []，表示没有菜单，不回退到 manifest |
| HTTP 成功但 resultCode 非 "200" | 抛出 MenuApiError，保留 resultCode/resultMsg |
| 缺少包装、旧字段、错误类型、重复业务码、错误父子关系等 | 抛出 MenuContractError，指出不符契约的位置 |
| 网络失败或 HTTP 4xx/5xx | 沿用现有 apiClient 的错误处理并向上传递，保留 HTTP 状态与响应 |

错误业务码最终以 Java 的结果码枚举为准，示例不意味着新增了一套枚举。API 不自行吞错、重试或切换数据源。

## 6. 开发调试开关

在 `apps/hrs-web/src/router/manifest.ts` 中修改：

```ts
export const USE_STATIC_MENU = true;
```

| 值 | 菜单来源 | 行为 |
| --- | --- | --- |
| `true`（当前默认） | 同文件的 `MENU_MANIFEST` | 不请求菜单 API，保留现有静态清单和指纹缓存流程 |
| `false` | `POST /api/system/list-menu` 的 `resultData` | 登录成功后查询；菜单和路由共用同一次返回结果，并沿用现有持久化；刷新时从本地恢复 |

这是开发调试时修改的源码常量，修改后重新登录获取所选数据源的菜单。不设计运行中热切换或模式切换兼容层，也不增加环境变量。开关只在 `loadMenuData()` 内选择数据源；两个 Store 和应用启动入口不判断开关。两种模式共用现有缓存键、清单指纹及 localStorage 读写逻辑，不新增另一套持久化实现。

接口失败时，登录页显示错误并允许重新提交，不用静态清单兜底。刷新时直接恢复已有菜单与路由，不再请求菜单接口；缓存缺失或失效时沿用原有重新登录流程。后续真实接入仍需完成 Java/数据库字段及请求地址对齐、服务转发和认证（含 CSRF）联调，目前未验证真实 Java 服务。

## 7. API、Store 与组件如何分层

| 层 | 文件/位置 | 职责 |
| --- | --- | --- |
| 类型契约 | `types/moduleMenu.ts`、`types/restResult.ts` | 定义统一节点和响应包装 |
| 静态配置 | `router/manifest.ts` | 提供调试开关与静态清单 |
| API | `api/system/menu.ts` | 请求、解包、校验字段和树结构、传递错误 |
| 加载入口 | `router/loadMenuData.ts` | 按固定开关选择数据源，将同一份节点交给两个 Store |
| 菜单状态 | `stores/MenuStore.ts` | 派生菜单、维护当前模块，供组件订阅 |
| 路由状态 | `stores/RouterStore.ts` | 从同一份节点派生页面路由 |
| 组件 | `ApplicationMenu.tsx`、`SidebarNav.tsx` 等 | 使用 `useMenuStore` 订阅状态，不直接请求菜单 API |

`useMenuStore` 已是全局菜单状态的 Hook，不再新增 `hooks/useMenu.ts`。登录页调用统一加载入口，两个 Store 分别加工、持久化菜单和路由，然后注册路由。刷新时，Store 初始化从 localStorage 恢复状态，路由器使用恢复后的路由数据；不额外请求菜单 API。再次登录获取最新菜单并覆盖现有缓存。

```mermaid
flowchart TD
    A["登录成功"] --> B["loadMenuData"]
    B --> C{"USE_STATIC_MENU"}
    C -->|true| D["MENU_MANIFEST"]
    C -->|false| E["menuApi.getTree：POST /api/system/list-menu"]
    D --> F["同一份 NavMenuNode[]"]
    E --> F
    F --> G["MenuStore → 现有持久化 → 菜单组件"]
    F --> H["RouterStore → 现有持久化 → 页面路由"]
```
