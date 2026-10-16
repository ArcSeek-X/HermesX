# <a id="自选股管理watchlist接口契约对照表"></a>自选股管理（Watchlist）接口契约对照表

> 📝 **方案简述**：本文档汇总自选股管理模块从数据库到前端页面的完整数据链路，包含 stock_watchlist_group 分类表与 stock_watchlist_item 自选股表的字段定义、类型、约束与来源，以及服务端接口、前端 API、前端 Hook 与功能说明的四方对照表，并补充错误响应与校验规则、命名语义说明，用于前后端协作时快速核对字段与调用关系。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-13

## 方案目录

- [一、`stock_watchlist_group`（分类表）](#一stockwatchlistgroup分类表)
- [二、`stock_watchlist_item`（自选股表）](#二stockwatchlistitem自选股表)
- [三、接口 / 前端 API / Hook / 功能说明 四方对照](#三接口-前端-api-hook-功能说明-四方对照)
- [四、错误响应与校验规则](#四错误响应与校验规则)
- [命名语义说明](#命名语义说明)

> 本文档汇总自选股管理模块从数据库到前端页面的完整数据链路，包含：
>
> 1. 数据库表字段（`stock_watchlist_group`、`stock_watchlist_item`）
> 2. 服务端接口 / 前端 API / 前端 Hook / 功能说明 的四方对照
>
> 核对日期：2026-10-13（已按当前代码实现核对）。代码依据：
> `src/storage.py`（ORM 模型）、`api/v1/endpoints/watchlist.py`（路由）、`api/v1/schemas/watchlist.py`（Schema）、
> `apps/hrs-web/src/api/watchlist.ts`（前端 API）、`apps/hrs-web/src/hooks/useWatchlistManager.ts`（前端 Hook）。

***

## <a id="一stockwatchlistgroup分类表"></a>一、`stock_watchlist_group`（分类表）

| 字段名              | 类型          | 必填/默认・约束                     | 说明                                                          | 来源   |
| ---------------- | ----------- | ---------------------------- | ----------------------------------------------------------- | ---- |
| `id`             | Integer     | 主键自增                         | 分类唯一 ID                                                      | 系统   |
| `name`           | String(50)  | 非空、唯一、索引                      | 分类名称                                                         | 前端传入 |
| `sort_order`     | Integer     | 非空，默认 `0`，索引                  | 排序权重；未传时后端取当前最大值 +1                                          | 前端可传 |
| `group_code`     | String(64)  | 非空、唯一、索引                      | 分组编码，规则 `WG-{enterpriseId}-{yyyyMMdd}-{6位流水}`，企业内唯一         | **服务端生成** |
| `description`    | String(255) | 可空，默认 `''`                   | 分类描述                                                         | 前端传入（选填） |
| `delete_flag`    | SmallInteger | 非空，默认 `0`，索引                 | 逻辑删除标志（`0`=有效 / `1`=已删）                                      | 服务端  |
| `create_user_id` | String(64)  | 可空                           | 创建人 ID                                                       | 服务端  |
| `create_date_time` | DateTime  | 非空，默认 `utc_naive_now`         | 创建时间                                                         | 服务端  |
| `update_user_id` | String(64)  | 可空                           | 更新人 ID                                                       | 服务端  |
| `update_date_time` | DateTime  | 非空，默认 `utc_naive_now`，`onupdate` 自动刷新 | 更新时间                                                         | 服务端  |

> 注：`enterpriseId` 在企业体系实现前由后端常量 `ENTERPRISE_ID = "01"` 固定，故实际编码形如 `WG-01-20261013-000001`；流水号取「当日该企业已存在同类编码数量 + 1」，格式化为 6 位。

***

## <a id="二stockwatchlistitem自选股表"></a>二、`stock_watchlist_item`（自选股表）

| 字段名              | 类型          | 必填/默认・约束                     | 说明                                | 来源   |
| ---------------- | ----------- | ---------------------------- | --------------------------------- | ---- |
| `id`             | Integer     | 主键自增                         | 自选股唯一 ID                          | 系统   |
| `group_id`       | Integer     | 非空，索引，外键 → `stock_watchlist_group.id`（`ON DELETE CASCADE`） | 所属分类 ID                           | 前端传入 |
| `stock_code`     | String(32)  | 非空，索引                        | 规范股票代码，如 `600519.SH`              | 前端传入 |
| `stock_name`     | String(64)  | 可空                           | 冗余股票名称                            | 前端传入 |
| `description`    | Text        | 可空                           | 自选股描述（原 `note` 字段已改名）             | 前端传入 |
| `sort_order`     | Integer     | 非空，默认 `0`，索引                 | 分类内排序权重（后端固定写入 `0`）               | 服务端  |
| `delete_flag`    | SmallInteger | 非空，默认 `0`，索引                 | 逻辑删除标志                            | 服务端  |
| `create_user_id` | String(64)  | 可空                           | 创建人 ID                            | 服务端  |
| `create_date_time` | DateTime  | 非空，默认 `utc_naive_now`         | 创建时间                              | 服务端  |
| `update_user_id` | String(64)  | 可空                           | 更新人 ID                            | 服务端  |
| `update_date_time` | DateTime  | 非空，默认 `utc_naive_now`，`onupdate` 自动刷新 | 更新时间                              | 服务端  |

**表级约束**：`UniqueConstraint('group_id', 'stock_code', name='uix_watchlist_item_group_code')`
→ 同一分类下股票代码唯一，由数据库层硬保证（非仅应用层校验）。

> 注：`item_count`（当前分组下的个股数量）**不是数据库字段**，由后端 `GET /get_group_list` 实时 `COUNT` 计算返回，不入库。

***

## <a id="三接口-前端-api-hook-功能说明-四方对照"></a>三、接口 / 前端 API / Hook / 功能说明 四方对照

| 服务端接口（方法 + 路径）                              | 前端请求 API（`api/watchlist.ts`）                                                     | 前端 Hook（`useWatchlistManager.ts`）                                  | 接口功能说明                                                                                             |
| ------------------------------------------ | --------------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `GET /api/v1/watchlist/get_group_list`     | `getWatchlistGroups()`                                                            | `loadGroups()`（结果落到 `groups` 状态）                                    | 列出全部分类，按 `sort_order, id` 升序返回未删除分类，并实时 `COUNT` 每个分类下的个股数量（`item_count`）；Hook 加载后若无选中项则自动选中第一个分类 |
| `POST /api/v1/watchlist/create_group`      | `createWatchlistGroup(name, description?, sortOrder?)`                            | `createWatchlistGroup(name, description?)`                          | 新增分类；服务端生成 `group_code`；名称为空→422、重名→409；未传 `sort_order` 时取当前最大值 +1                                |
| `POST /api/v1/watchlist/update_group`      | `updateWatchlistGroup({ groupCode, name?, description?, sortOrder? })`            | `updateWatchlistGroup(groupCode, { name?, description? })`           | 按 `group_code` 定位，可改名称（重名→409）/ 描述 / 排序，刷新 `update_date_time`                                       |
| `DELETE /api/v1/watchlist/delete_group/{groupCode}` | `deleteWatchlistGroup(groupCode)`                                          | `deleteWatchlistGroup(groupCode)`                                   | 逻辑删除分类（`delete_flag=1`）并级联逻辑删除其下所有自选股；返回 `{ success: true }`                                        |
| `POST /api/v1/watchlist/get_items_list`    | `getWatchlistItems(groupId, pageNum, pageSize)`                                   | `loadItems(groupId, pageNum?)`（Hook 内 `pageSize` 固定 `10`）           | 分页查询某分类下的自选股；body 入参 `group_id / pageNum / pageSize`（`pageSize` 限 1–100），返回 `list / total / pages / pageNum / pageSize`，过滤已逻辑删除项，按 `sort_order, id` 升序 |
| `POST /api/v1/watchlist/create_item/{id}`  | `createWatchlistItem(groupId, { stockCode, stockName?, description? })`           | `addItem(groupId, { stockCode, stockName?, description? })`          | 新增自选股到指定分类（路径 `{id}` 即目标 `group_id`）；校验股票代码存在、分类存在、同分类下不重复                                          |
| `POST /api/v1/watchlist/update_item/{id}`  | `updateWatchlistItem(id, { description?, stockName? })`                           | `editItemDescription(id, description)`                              | 修改自选股描述或名称，刷新 `update_date_time`                                                                     |
| `DELETE /api/v1/watchlist/delete_item/{id}` | `deleteWatchlistItem(id)`                                                         | `removeItem(id)`                                                    | 逻辑删除自选股；返回 `{ success: true }`                                                                       |
| `PUT /api/v1/watchlist/move_item/{id}`     | `moveWatchlistItem(id, targetGroupId)`                                            | `moveItem(id, targetGroupId)`                                       | 移动自选股到其他分类（body `target_group_id`）；校验目标分类存在、目标分类下不重复；目标即当前分类时为空操作                                   |

**前端 API 层补充函数（无独立服务端接口）**

| 前端函数                              | 说明                                                                                              |
| --------------------------------- | ----------------------------------------------------------------------------------------------- |
| `getAllWatchlistItems(groupId)`   | 在前端自动翻页取尽某分类全部自选股：内部以 `pageSize=100`（后端上限）循环调用 `getWatchlistItems`，最多 50 页，用于「已自选」状态比对等需要全量代码的场景 |

***

## <a id="四错误响应与校验规则"></a>四、错误响应与校验规则

错误响应统一为 `detail: { error, message }` 结构。

| HTTP 状态码 | `error` 码           | 触发场景                                 |
| -------- | ------------------- | ------------------------------------ |
| 400      | `invalid_code`      | 股票代码无效或未收录（未通过主数据索引核验）                |
| 404      | `not_found`         | 分类 / 自选股 / 目标分类不存在                    |
| 409      | `duplicate_name`    | 分类名称已存在                              |
| 409      | `duplicate_item`    | 同分类（或目标分类）下该股票已存在                    |
| 422      | `invalid_name`      | 分类名称为空                               |
| 422      | `invalid_code`      | 股票代码为空                               |

**股票代码核验规则**：后端 `create_item` 通过 `get_stock_name_index_map()`（源自股票主数据索引，覆盖 A 股 / 港股 / 美股等全市场）核验 `stock_code` 是否存在；不存在则返回 400。若索引加载发生异常，则**降级放行**（记 warning 日志），避免主数据缺失拖垮新增功能。

***

### <a id="命名语义说明"></a>命名语义说明

- **语义化动词**已落地：`create`=新增、`update`=修改更新、`delete`=删除、`get`=查询、`move`=移动归类。
- 所有删除类接口均为**逻辑删除**（`delete_flag=1`），不物理删数据。
- 分类定位统一使用 `group_code`（服务端生成、企业内唯一）；自选股定位使用数字 `id`。
- ⚠️ **三层方法名并不完全一致**：后端与前端 `api/watchlist.ts` 使用 `create/update/delete/move` 前缀的完整命名，而 **Hook 层是面向 UI 的短名**（`addItem` / `editItemDescription` / `removeItem` / `moveItem` / `loadGroups` / `loadItems`）。对接时请以本表第三列（Hook 列）为准，不要假定三层同名。
- **字段大小写约定**：后端为 snake_case；前端响应经 `toCamelCase` 归一化（如 `group_code → groupCode`）；前端**请求体**按后端 Schema 发送 snake_case（`group_code`、`stock_code`、`stock_name`、`target_group_id`、`sort_order`），而前端函数**入参**用 camelCase（`groupCode`、`sortOrder`、`stockName`）。
- `GET /groups/{id}/items`（`list_items`）接口已删除（前端未使用），统一走 `get_items_list` 分页查询。

