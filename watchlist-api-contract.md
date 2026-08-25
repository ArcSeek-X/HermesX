# 自选股管理（Watchlist）接口契约对照表

> 本文档汇总自选股管理模块从数据库到前端页面的完整数据链路，包含：
>
> 1. 数据库表字段（`stock_watchlist_group`、`stock_watchlist_item`）
> 2. 服务端接口 / 前端 API / 前端 Hook / 功能说明 的四方对照
>
> 生成日期：2026-08-25

***

## 一、`stock_watchlist_group`（分类表）

| 字段名                | 类型           | 必填/默认  | 说明                                    | 来源        |
| ------------------ | ------------ | ------ | ------------------------------------- | --------- |
| `id`               | int          | 主键自增   | 分类唯一 ID                               | 系统        |
| `name`             | varchar(50)  | 非空     | 分类名称（唯一约束）                            | 前端传入      |
| `sort_order`       | int          | 默认 0   | 排序权重                                  | 前端可传/后端自增 |
| `group_code`       | varchar      | 非空     | 分组编码，规则 `WG-01-yyyyMMdd-000001`，企业内唯一 | **服务端生成** |
| `description`      | varchar(255) | 默认空    | 分类描述                                  | 前端传入（选填）  |
| `delete_flag`      | int          | 默认 0   | 逻辑删除标志（1=已删）                          | 服务端       |
| `create_user_id`   | —            | 默认空    | 创建人 ID                                | 服务端       |
| `create_date_time` | datetime     | 默认 now | 创建时间                                  | 服务端       |
| `update_user_id`   | —            | 默认空    | 更新人 ID                                | 服务端       |
| `update_date_time` | datetime     | 默认 now | 更新时间                                  | 服务端       |

***

## 二、`stock_watchlist_item`（自选股表）

| 字段名                | 类型          | 必填/默认  | 说明                    | 来源   |
| ------------------ | ----------- | ------ | --------------------- | ---- |
| `id`               | int         | 主键自增   | 自选股唯一 ID              | 系统   |
| `group_id`         | int         | 非空     | 所属分类 ID（外键）           | 前端传入 |
| `stock_code`       | varchar(32) | 非空     | 规范股票代码，如 `600519.SH`  | 前端传入 |
| `stock_name`       | varchar(64) | 可空     | 冗余股票名称                | 前端传入 |
| `description`      | text        | 可空     | 自选股描述（原 `note` 字段已改名） | 前端传入 |
| `sort_order`       | int         | 默认 0   | 排序权重                  | 服务端  |
| `delete_flag`      | int         | 默认 0   | 逻辑删除标志（1=已删）          | 服务端  |
| `create_user_id`   | —           | 默认空    | 创建人 ID                | 服务端  |
| `create_date_time` | datetime    | 默认 now | 创建时间                  | 服务端  |
| `update_user_id`   | —           | 默认空    | 更新人 ID                | 服务端  |
| `update_date_time` | datetime    | 默认 now | 更新时间                  | 服务端  |

> 注：`item_count`（当前分组下的个股数量）**不是数据库字段**，由后端 `GET /get_group_list` 实时 `COUNT` 计算返回，不入库。

***

## 三、接口 / 前端 API / Hook / 功能说明 四方对照

| 服务端接口 API（路径 + 语义化函数）                                    | 前端请求 API（`api/watchlist.ts`）                                         | 前端 Hook（`useWatchlistManager.ts`）                         | 接口功能说明                                                               |
| -------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------- |
| `GET /api/v1/watchlist/get_group_list`                   | `getWatchlistGroups()`                                               | `getWatchlistGroups()`                                    | 列出全部分类，按 `sort_order` 升序返回未删除分类，并实时 `COUNT` 每个分类下的个股数量（`item_count`） |
| `POST /api/v1/watchlist/create_group`                    | `createWatchlistGroup({name, description?, sortOrder?})`             | `createWatchlistGroup(name, description?)`                | 新增分类，服务端生成 `group_code`（规则 `WG-01-yyyyMMdd-000001`），名称唯一校验           |
| `POST  /api/v1/watchlist/update_group`                   | `updateWatchlistGroup({group_code,name?, description?, sortOrder?})` | `updateWatchlistGroup({group_code,name?, description?})`  | 修改/更新分类，可改名称（唯一校验）/描述/排序，刷新 `update_date_time`                       |
| `DELETE /api/v1/watchlist/delete_group/{group_code}`     | `deleteWatchlistGroup(group_code)`                                   | `deleteWatchlistGroup(group_code)`                        | 删除分类（逻辑删除 `delete_flag=1`），级联逻辑删除其下所有自选股                             |
| `POST /api/v1/watchlist/get_items_list`                  | `getWatchlistItems(groupId, pageNum, pageSize)`                      | `getWatchlistItems(groupId,pageNum,pageSize)`             | 分页查询某分类下的自选股，返回 `list/total/pages/pageNum/pageSize`，过滤已逻辑删除项         |
| `POST /api/v1/watchlist/create_item/{id}`                | `createWatchlistItem(groupId, {stockCode, stockName?, description?})`         | `addItem(groupId, {stockCode, stockName?, description?})` | 新增自选股到指定分类，校验股票代码合法性、分类存在性、同分类下不可重复                                  |
| `POST /api/v1/watchlist/update_item/{id}`                | `updateWatchlistItem(id, {description?, stockName?})`                | `updateWatchlistItem(id, description)`                    | 修改/更新自选股描述或名称，刷新 `update_date_time`                                  |
| `DELETE /api/v1/watchlist/delete_item/{id}`              | `deleteWatchlistItem(id)`                                            | `deleteWatchlistItem(id)`                                 | 删除自选股（逻辑删除 `delete_flag=1`）                                          |
| `PUT /api/v1/watchlist/move_item/{id}`                   | `moveWatchlistItem(id, targetGroupId)`                               | `moveWatchlistItem(id, targetGroupId)`                    | 移动自选股到其他分类，校验目标分类存在、目标分类下不可重复                                        |

### 命名语义说明

- 语义化动词已落地：`create`=新增、`update`=修改更新、`remove`(`delete`)=删除、`get`=查询、`move`=移动。
- 所有删除类接口均为**逻辑删除**（`delete_flag=1`），不物理删数据；同一业务语义下后端、前端 API、Hook 三层方法名保持一致。
- 分类定位统一使用 `group_code`（服务端生成、企业内唯一）；自选股定位使用数字 `id`。
- `GET /groups/{id}/items`（`list_items`）接口已删除（前端未使用，统一走 `get_items_list` 分页查询）。

