# <a id="user-role"></a>后端用户、角色与菜单授权方案

> 📝 **方案简述**：以 `scaffold-master-main` 的 MySQL 实现为参考，说明用户、角色、菜单和按钮权限如何建表、关联和生效，并列出前后端接口契约，作为 HermesX 后端权限设计的参考。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-17

## 目录

- [一、范围与关系](#sec-1)
- [二、主表字段](#sec-2)
  - [2.1 用户表](#sec-2-1)
  - [2.2 角色表](#sec-2-2)
  - [2.3 菜单与按钮权限表](#sec-2-3)
  - [2.4 共用审计字段](#sec-2-4)
- [三、关联表字段](#sec-3)
- [四、授权如何生效](#sec-4)
- [五、接入约束](#sec-5)
- [六、接口规格](#sec-6)
  - [6.1 通用格式与错误](#sec-6-1)
  - [6.2 登录、会话与动态路由](#sec-6-2)
  - [6.3 用户管理](#sec-6-3)
  - [6.4 角色管理与权限图谱](#sec-6-4)
  - [6.5 菜单管理](#sec-6-5)

<a id="sec-1"></a>

## 一、范围与关系

**结论：**参考实现采用基于角色的访问控制（RBAC）。用户通过角色获得功能权限；菜单、目录和按钮存放在同一张树形表中；数据可见范围由角色另行配置。下文描述的是脚手架的表结构和行为，HermesX 尚未按本文实施建表或迁移。

| 关系 | 实现 | 用途 |
| --- | --- | --- |
| 用户 ↔ 角色 | `sys_user_role`，多对多 | 一个用户可分配多个角色，一个角色可分配给多个用户 |
| 角色 ↔ 菜单或按钮 | `sys_role_menu`，多对多 | 一个角色可授权多个节点，一个节点也可授予多个角色 |
| 菜单节点 → 父节点 | `sys_menu.parent_id` → `sys_menu.id` | 组织目录、页面和按钮；根节点的父节点 ID 为 `0` |
| 用户 → 所属部门 | `sys_user.dept_id` → `sys_dept.id` | 记录用户所属部门，供部门级数据范围判断 |
| 角色 ↔ 自定义部门 | `sys_role_dept`，多对多 | 为采用自定义数据范围的角色配置部门 |

<a id="sec-2"></a>

## 二、主表字段

参考脚手架使用 MySQL，表引擎为 `InnoDB`，默认字符集为 `utf8mb4`。

<a id="sec-2-1"></a>

### 2.1 用户表：`sys_user`

| 字段 | 类型 | 可空 | 默认值或约束 | 用途 |
| --- | --- | --- | --- | --- |
| `id` | `BIGINT` | 否 | 自增主键 | 用户 ID |
| `username` | `VARCHAR(64)` | 否 | 唯一索引 | 登录账号 |
| `password` | `VARCHAR(128)` | 否 | 无默认值 | 登录密码的 BCrypt 哈希 |
| `nickname` | `VARCHAR(64)` | 否 | 无默认值 | 用户昵称 |
| `phone` | `VARCHAR(32)` | 是 | `NULL` | 手机号 |
| `email` | `VARCHAR(128)` | 是 | `NULL` | 邮箱 |
| `dept_id` | `BIGINT` | 是 | `NULL`，普通索引 | 所属部门 ID |
| `status` | `TINYINT` | 否 | `1`，普通索引 | `1` 正常，`0` 停用 |
| `last_login_time` | `DATETIME` | 是 | `NULL` | 最近一次成功登录的时间 |
| `deleted` | `TINYINT` | 否 | `0` | 软删除标记：`0` 未删除，`1` 已删除 |

<a id="sec-2-2"></a>

### 2.2 角色表：`sys_role`

| 字段 | 类型 | 可空 | 默认值或约束 | 用途 |
| --- | --- | --- | --- | --- |
| `id` | `BIGINT` | 否 | 自增主键 | 角色 ID |
| `role_name` | `VARCHAR(100)` | 否 | 无默认值 | 角色名称 |
| `role_code` | `VARCHAR(64)` | 否 | 唯一索引 | 角色编码，如 `super_admin`（超级管理员） |
| `data_scope` | `VARCHAR(32)` | 否 | `SELF` | 数据可见范围，取值见 [§4](#sec-4) |
| `sort` | `INT` | 否 | `0` | 排序号 |
| `status` | `TINYINT` | 否 | `1` | `1` 正常，`0` 停用 |
| `builtin` | `TINYINT` | 否 | `0` | 内置标记：`1` 内置，`0` 非内置 |
| `remark` | `VARCHAR(500)` | 是 | `NULL` | 角色备注 |
| `deleted` | `TINYINT` | 否 | `0` | 软删除标记：`0` 未删除，`1` 已删除 |

<a id="sec-2-3"></a>

### 2.3 菜单与按钮权限表：`sys_menu`

| 字段 | 类型 | 可空 | 默认值或约束 | 用途 |
| --- | --- | --- | --- | --- |
| `id` | `BIGINT` | 否 | 主键，非自增 | 菜单或按钮的节点 ID |
| `parent_id` | `BIGINT` | 否 | `0`，普通索引 | 父节点 ID，`0` 表示根节点 |
| `menu_name` | `VARCHAR(100)` | 否 | 无默认值 | 节点名称 |
| `menu_type` | `VARCHAR(16)` | 否 | 无默认值 | `dir` 目录、`menu` 页面、`btn` 按钮 |
| `icon` | `VARCHAR(64)` | 是 | `NULL` | 菜单图标 |
| `path` | `VARCHAR(200)` | 是 | `NULL` | 前端路由路径 |
| `component` | `VARCHAR(200)` | 是 | `NULL` | 前端组件路径 |
| `permission` | `VARCHAR(128)` | 是 | `NULL`，普通索引 | 权限码，如 `system:user:add`（新增用户） |
| `sort` | `INT` | 否 | `0` | 排序号 |
| `visible` | `TINYINT` | 否 | `1` | 导航可见性：`1` 显示，`0` 隐藏 |
| `status` | `TINYINT` | 否 | `1` | 节点状态：`1` 正常，`0` 停用 |

参考实现通过 `MAX(id) + 1` 生成菜单 ID。菜单表没有软删除字段，删除时应用会先检查是否存在子节点或角色授权。

<a id="sec-2-4"></a>

### 2.4 共用审计字段

以下字段适用于三张主表，关联表不包含这些字段。

| 字段 | 类型 | 可空 | 默认值或约束 | 用途 |
| --- | --- | --- | --- | --- |
| `create_by` | `VARCHAR(64)` | 是 | `NULL` | 创建人 |
| `update_by` | `VARCHAR(64)` | 是 | `NULL` | 更新人 |
| `create_time` | `DATETIME` | 是 | `CURRENT_TIMESTAMP` | 创建时间 |
| `update_time` | `DATETIME` | 是 | `CURRENT_TIMESTAMP`，记录更新时自动刷新 | 更新时间 |

<a id="sec-3"></a>

## 三、关联表字段

| 表 | 字段与逻辑引用 | 联合主键 |
| --- | --- | --- |
| `sys_user_role`：用户角色关联 | `user_id`（用户 ID）→ `sys_user.id`；`role_id`（角色 ID）→ `sys_role.id` | `(user_id, role_id)` |
| `sys_role_menu`：角色菜单关联 | `role_id`（角色 ID）→ `sys_role.id`；`menu_id`（菜单或按钮 ID）→ `sys_menu.id` | `(role_id, menu_id)` |
| `sys_role_dept`：角色自定义部门关联 | `role_id`（角色 ID）→ `sys_role.id`；`dept_id`（部门 ID）→ `sys_dept.id` | `(role_id, dept_id)` |

每张关联表只有表中所列的两列，均为 `BIGINT NOT NULL`。联合主键防止重复分配。参考建表脚本未声明外键，表中的箭头表示逻辑关系。

<a id="sec-4"></a>

## 四、授权如何生效

| 场景 | 脚手架行为 |
| --- | --- |
| 普通用户的权限码 | 通过用户角色和角色菜单两张关联表，取启用且未删除的角色所关联的启用节点；返回非空权限码并去重，不检查 `visible`。 |
| 普通用户的导航 | 从同一授权链取启用、可见的 `dir` 和 `menu` 节点；`btn` 不进入导航。 |
| 页面与按钮 | 页面和按钮是不同的授权节点。以「用户管理」为例，页面是 `system:user:list`，「新增用户」按钮是 `system:user:add`；授予页面权限不会自动授予新增权限。 |
| 超级管理员 | 用户持有启用且未删除的 `super_admin` 角色时，直接读取全部启用节点的非空权限码，以及全部启用且可见的目录和页面。 |

`data_scope` 表示用户能看哪些记录，与上表中的功能授权分开计算。

| 取值 | 含义 |
| --- | --- |
| `SELF` | 默认范围，仅本人 |
| `DEPT` | 本部门 |
| `DEPT_AND_CHILD` | 本部门及下级部门 |
| `CUSTOM` | 使用 `sys_role_dept` 配置的部门 |
| `ALL` | 全部数据 |

<a id="sec-5"></a>

## 五、接入约束

以下规则适用于 HermesX 后续采用本方案时。

Java 模块归属、基础包名和依赖方向见 [HermesX Java 与 Python 后端协作方案](../../framework/java_python_backend_design.md)。注册和会话归 `hermesx.auth`，组织、角色、菜单及后台用户管理归 `hermesx.system`；本文保留授权规则和接口参考。

| 级别 | 规则 | 原因与用法 |
| --- | --- | --- |
| 【强制】 | 后端单独判断功能权限和数据范围。 | 页面能打开，不代表其中的写操作已获授权；功能获授权后，查询仍需按数据范围过滤。 |
| 【强制】 | 菜单隐藏与权限撤销分别处理。 | `visible` 仅控制导航。需要撤销某个角色的操作权限时，应移除对应授权；用户还可能通过其他角色保有同一权限。 |
| 【强制】 | 菜单接口接入前，先确定字段映射。 | HermesX 前端现以 `MENU_MANIFEST` 作为菜单和路由真源。接口需明确如何映射模块、节点 ID、节点类型和路由字段，再替换读取入口。见[前端模块化菜单方案](../frontend/frontend_module_menu.md)。 |
| 【推荐】 | 实施时采用能保证并发唯一的菜单 ID 分配方式。 | 脚手架的 `MAX(id) + 1` 在并发新增时可能计算出相同的 ID。 |

接口规格见 [§6](#sec-6)。

依据：本地脚手架的 `vibe-template/scaffold-master-main/scaffold-system/sql/V1__init_schema.sql`、同目录的 `V2__seed_data.sql`，以及后端的 `AuthMapper.java`、`AuthService.java`、`SystemDataScopeResolver.java` 和 `SystemManagementService.java`。未连接运行数据库，未修改表结构、应用代码或前端菜单配置。

<a id="sec-6"></a>

## 六、接口规格

本节记录 `scaffold-master-main` 当前实现，覆盖登录、会话、动态路由、用户、角色、菜单及权限图谱。路径均为完整的脚手架 API 路径；HermesX 主项目现有的 `/api/v1` Cookie 会话契约不因本文改变。部门和岗位的独立管理接口不在本节范围内，用户页用到的部门和岗位选项已纳入。

<a id="sec-6-1"></a>

### 6.1 通用格式与错误

| 项目 | 格式与约束 |
| --- | --- |
| 身份凭证 | 除验证码和登录外，发送 `Authorization: Bearer <token>`。写入接口有请求体时使用 `Content-Type: application/json`。 |
| 路径参数 | 下文的 `{id}` 必填，为十进制整数，对应用户、角色或菜单 ID。 |
| JSON 响应 | 统一包装为 `{code: integer, message: string, data: T 或 null, traceId: string 或 null}`。依次为业务码、提示、业务数据和追踪 ID。成功为 HTTP `200`、`code: 200`；表中只列 `data` 的结构。 |
| 创建响应 | `{id: integer}`：新建记录的 ID。 |
| 分页响应 | `{rows: T[], total: integer, pageNum: integer, pageSize: integer}`：当前页记录、总数、页码、每页数量。 |
| CSV 下载 | 成功时返回 `text/csv;charset=UTF-8`，通过 `Content-Disposition` 提供文件名；响应体是 CSV，不使用 JSON 包装。 |
| 类型记法 | `integer` 为 JSON 整数，`boolean` 为布尔值，`T[]` 为数组；注明“可空”的响应字段可为 `null`。表中 `—` 表示没有该参数或请求体。 |

| 分页查询参数 | 类型 | 必填 | 默认值与行为 |
| --- | --- | --- | --- |
| `pageNum` | `integer` | 否 | 默认 `1`；小于 `1` 时按 `1`。 |
| `pageSize` | `integer` | 否 | 默认 `10`；小于 `1` 时用默认值；最大 `100`。 |
| `sortField`、`sortOrder` | `string` | 否 | 分页对象可接收排序字段、排序方向，但本文的用户和角色列表使用固定 SQL 排序，这两个字段不改变结果顺序。 |

| HTTP 状态 | `code` | 场景 |
| --- | --- | --- |
| `400` | 通常 `400` | 参数或 JSON 不合法、验证码或密码校验失败、业务条件不满足。业务异常固定使用 HTTP `400`；例如 `/me` 或 `/routes` 已进入服务但账号被停用或删除时，业务码为 `401`。 |
| `401` | `401` | 受保护请求没有有效会话。 |
| `403` | `403` | 会话通过，但不满足接口权限。 |
| `404` / `405` / `500` | 同 HTTP 状态 | 资源不存在、方法不支持或未处理的服务端错误。 |

<a id="sec-6-2"></a>

### 6.2 登录、会话与动态路由

| 方法与路径 | 权限 | 查询参数 | JSON 请求体 | 成功响应 `data` |
| --- | --- | --- | --- | --- |
| `GET /api/auth/captcha` | 公开 | — | — | `{uuid: string, code: string}`：验证码 ID、4 位验证码文本；保留 300 秒，验证时不区分大小写。当前响应直接提供验证码文本给前端渲染。 |
| `POST /api/auth/login` | 公开 | — | 登录请求，见下表 | `{token: string, expiresIn: integer}`：JWT 和有效期秒数。 |
| `GET /api/auth/me` | 已登录 | — | — | 当前用户对象，见下表。 |
| `GET /api/auth/routes` | 已登录 | — | — | `{routes: RouteNode[]}`：当前用户的可导航节点树。 |
| `POST /api/auth/logout` | 已登录 | — | — | `null`；撤销本次请求的 Token。 |
| `PUT /api/auth/password` | 已登录 | — | `{oldPassword: string, newPassword: string}`，均必填且非空，新密码 6–64 字符，与原密码不同。 | `null`。 |

| 登录请求字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `username` | `string` | 是 | 非空登录账号。 |
| `password` | `string` | 是 | 非空登录密码。 |
| `captchaUuid` | `string` | 是 | 验证码接口返回的 `uuid`。 |
| `captcha` | `string` | 是 | 用户输入的验证码；校验时已存在的验证码记录会被消费。 |

| 响应对象 | 字段 | 类型 | 含义 |
| --- | --- | --- | --- |
| 当前用户 | `userId` | `integer` | 用户 ID。 |
| 当前用户 | `username`、`nickname` | `string` | 登录账号、昵称。 |
| 当前用户 | `deptId`、`deptName` | `integer`、`string`，可空 | 部门 ID 和名称。 |
| 当前用户 | `roles`、`permissions` | `string[]` | 有效角色编码、去重后的权限码。 |
| `RouteNode` | `id`、`parentId` | `integer` | 节点与父节点 ID；父节点不在返回集合时，该节点作为树根。 |
| `RouteNode` | `name` | `string` | 节点名称。 |
| `RouteNode` | `path`、`component`、`icon`、`permission` | `string`，可空 | 路由、前端组件标识、图标、权限码。 |
| `RouteNode` | `children` | `RouteNode[]` | 子节点，叶节点为 `[]`。 |

<a id="sec-6-3"></a>

### 6.3 用户管理

| 方法与路径 | 权限码 | 查询参数 | JSON 请求体 | 成功响应 |
| --- | --- | --- | --- | --- |
| `GET /api/system/users` | `system:user:list` | 分页参数 + 用户筛选 | — | `data` 为 `UserRow` 分页，按用户 ID 排序，受数据范围限制。 |
| `GET /api/system/users/options` | `system:user:list` | — | — | `data` 为用户表单选项对象，见下表。 |
| `GET /api/system/users/export` | `system:user:list` | 用户筛选 | — | `users.csv`，受数据范围限制，最多 5,000 行数据。 |
| `POST /api/system/users` | `system:user:add` | — | 用户写入字段，见下表。 | `data = {id}`。 |
| `PUT /api/system/users/{id}` | `system:user:edit` | — | 用户写入字段，见下表。 | `data = null`。 |
| `PUT /api/system/users/{id}/status` | `system:user:edit` | — | `{status: integer}`，必填，只接受 `0` 或 `1`；该接口禁止停用内置管理员。 | `data = null`。 |
| `PUT /api/system/users/{id}/password` | `system:user:resetPwd` | — | `{password?: string}`，缺省或空白时使用脚手架内置重置默认值；最终密码长度为 6–64 字符。 | `data = null`。 |
| `DELETE /api/system/users/{id}` | `system:user:remove` | — | — | `data = null`；软删除，禁止删除内置管理员。 |

| 用户筛选参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | `string` | 否 | 模糊匹配账号、昵称或手机号。 |
| `status` | `integer` | 否 | 按状态等值过滤，正常为 `1`，停用为 `0`。 |
| `deptId` | `integer` | 否 | 选择部门及其下级。 |
| `postId` | `integer` | 否 | 按已关联的岗位 ID 过滤。 |

| 写入字段 | 类型 | 新建 | 编辑 |
| --- | --- | --- | --- |
| `username` | `string` | 必填，非空且唯一。 | 不修改。 |
| `password` | `string` | 可省略；空白或缺省使用脚手架内置初始值，服务端存哈希。 | 不修改；使用重置密码接口。 |
| `nickname` | `string` | 必填，非空。 | 可省略，空白或 `null` 保留。 |
| `phone`、`email` | `string` | 可省略，分别为电话、邮箱。 | 可省略；`null` 保留，空字符串会写入。 |
| `deptId` | `integer` | 可省略，为部门 ID。 | 可省略，`null` 保留原部门。 |
| `status` | `integer` | 可省略，默认 `1`。 | 可省略，`null` 保留。 |
| `roleIds`、`postIds` | `integer[]` | 可省略，无初始关联。分别为角色和岗位 ID 列表。 | 省略或 `null` 保留，`[]` 清空，非空数组整体替换。 |

| 响应对象 | 字段 | 类型与含义 |
| --- | --- | --- |
| `UserRow` | `id`、`status` | `integer`：用户 ID、启停状态。 |
| `UserRow` | `username`、`nickname`、`phone`、`email`、`deptName` | `string`：账号、昵称、手机号、邮箱、部门名；后三项可空。 |
| `UserRow` | `postName`、`roleName` | `string`：岗位和角色的名称，各自以逗号连接；无关联时为空串。 |
| `UserRow` | `createTime`、`lastLogin` | `string`，可空：创建时间、最近登录时间，格式为 `yyyy-MM-dd HH:mm`。 |
| 用户表单选项 | `depts` | 部门节点数组；每项含 `id`、`parentId`、`status`（整数）、`name`（名称）、`children`（同结构子节点数组）。 |
| 用户表单选项 | `roles`、`posts` | 已启用角色、岗位的选项数组，元素为 `{id: integer, name: string}`；没有新增或编辑用户权限时返回空数组。 |
| 用户表单选项 | `initPassword` | `string`：配置中的表单初始密码；没有新增或重置密码权限，或没有对应配置时返回空串。 |

<a id="sec-6-4"></a>

### 6.4 角色管理与权限图谱

| 方法与路径 | 权限码 | 查询参数 | JSON 请求体 | 成功响应 |
| --- | --- | --- | --- | --- |
| `GET /api/system/roles` | `system:role:list` | 分页参数 + 角色筛选 | — | `data` 为 `RoleRow` 分页，按排序号、角色 ID 排序。 |
| `GET /api/system/roles/{id}/menus` | `system:role:list` | — | — | `data = {menuIds: integer[]}`：已存储的授权节点 ID，无关联时为 `[]`。 |
| `GET /api/system/roles/export` | `system:role:list` | 角色筛选 | — | `roles.csv`，最多 5,000 行数据。 |
| `POST /api/system/roles` | `system:role:add` | — | 角色写入字段，见下表。 | `data = {id}`。 |
| `PUT /api/system/roles/{id}` | `system:role:edit` | — | 角色写入字段，见下表。 | `data = null`；内置角色不可更新。 |
| `DELETE /api/system/roles/{id}` | `system:role:remove` | — | — | `data = null`；移除菜单关联并软删除角色。内置角色或仍分配给用户的角色不可删除。 |
| `GET /api/system/permissions/graph` | `system:role:list` | — | — | `data` 为权限图谱对象，见下表。 |

角色筛选均为可选：`keyword: string` 模糊匹配角色名或角色编码；`status: integer` 按启停状态等值过滤。

| 写入字段 | 类型 | 新建 | 编辑 |
| --- | --- | --- | --- |
| `name` | `string` | 必填，角色名称。 | 可省略，空白或 `null` 保留。 |
| `code` | `string` | 必填，角色编码，唯一。 | 不修改。 |
| `dataScope` | `string` | 可省略，默认 `SELF`；范围编码见 [§4](#sec-4)。 | 可省略，空白或 `null` 保留。接口无自定义部门 ID 字段。 |
| `sort`、`status` | `integer` | 可省略，排序号默认 `0`，启停状态默认 `1`。 | 可省略，`null` 保留。 |
| `remark` | `string` | 可省略，角色备注。 | 可省略，`null` 保留，空字符串会写入。 |
| `menuIds` | `integer[]` | 可省略，无初始菜单授权。 | 省略或 `null` 保留，`[]` 清空，非空数组整体替换。 |

| 响应对象 | 字段 | 类型与含义 |
| --- | --- | --- |
| `RoleRow` | `id`、`userCount`、`sort`、`status` | `integer`：角色 ID、已分配且未删除的用户数、排序号、启停状态。 |
| `RoleRow` | `name`、`code`、`dataScope` | `string`：角色名称、角色编码、数据范围的中文显示值，例如“仅本人数据权限”；写入时使用范围编码。 |
| `RoleRow` | `createTime`、`remark` | `string`，可空：创建时间（`yyyy-MM-dd HH:mm`）和备注。 |
| `RoleRow` | `builtin`、`menuIds` | `boolean`、`integer[]`：是否内置、已授权节点 ID 列表。 |
| 权限图谱 | `usersVisible` | `boolean`：当前账号是否具有 `system:user:list`。 |
| 权限图谱 | `users` | 用户节点数组：`id`、`status`（整数），`username`、`nickname`、`deptName`（字符串，部门名可空）；受数据范围限制，最多 2,000 个。 |
| 权限图谱 | `roles` | 角色节点数组：取 `RoleRow` 的 `id`、`name`、`code`、`dataScope`、`status`、`builtin`、`userCount`、`menuIds`，最多 5,000 个。 |
| 权限图谱 | `menus` | 扁平菜单节点数组，字段同 [§6.5](#sec-6-5) 的 `MenuNode`，不包含 `component` 和 `children`。 |
| 权限图谱 | `userRoles` | `[integer, integer][]`：每项为 `[用户 ID, 角色 ID]`，只返回图谱用户的关联。无用户查询权限时，`users`、`userRoles` 都是空数组。 |

角色授权弹窗同时调用角色已授权菜单接口和管理菜单树接口，因此打开并保存授权涉及 `system:role:list`、`system:menu:list` 和 `system:role:edit` 三个权限。管理菜单树和登录后加载的导航树不是同一个接口。

<a id="sec-6-5"></a>

### 6.5 菜单管理

| 方法与路径 | 权限码 | 查询参数 | JSON 请求体 | 成功响应 |
| --- | --- | --- | --- | --- |
| `GET /api/system/menus/tree` | `system:menu:list` | 菜单筛选 | — | `data = MenuNode[]`，含目录、页面和按钮，按筛选结果组树；父节点未被选中时子节点作为树根。 |
| `GET /api/system/menus/export` | `system:menu:list` | 菜单筛选 | — | `menus.csv`，按筛选结果导出。 |
| `POST /api/system/menus` | `system:menu:add` | — | 菜单写入字段，见下表。 | `data = {id}`。 |
| `PUT /api/system/menus/{id}` | `system:menu:edit` | — | 菜单写入字段，见下表。 | `data = null`。 |
| `DELETE /api/system/menus/{id}` | `system:menu:remove` | — | — | `data = null`；有子节点或已分配角色时拒绝删除。 |

菜单筛选均为可选：`keyword: string` 模糊匹配菜单名或权限码；`status: integer` 按启停状态等值过滤。未指定时不按状态或可见性过滤。

| 字段 | 类型 | 写入请求 | `MenuNode` 响应含义 |
| --- | --- | --- | --- |
| `id` | `integer` | 请求体不接收；编辑时由路径传入。 | 节点 ID。 |
| `parentId` | `integer` | 新建默认 `0`；编辑可省略。 | 父节点 ID，`0` 为根。 |
| `name` | `string` | 新建必填且非空；编辑可省略，空白保留。 | 节点名称。 |
| `type` | `string` | 新建默认 `menu`；编辑可省略。 | `dir` 目录、`menu` 页面、`btn` 按钮。 |
| `icon`、`path`、`component`、`permission` | `string` | 均可省略；更新时 `null` 保留、空字符串会写入。 | 图标、路由、前端组件标识、权限码，可空。 |
| `sort`、`visible`、`status` | `integer` | 分别默认 `0`、`1`、`1`；编辑可省略。 | 排序号、是否显示（`1` 显示）、是否启用（`1` 启用）。 |
| `children` | `MenuNode[]` | 请求体不接收。 | 子节点，叶节点为 `[]`。 |

| CSV 文件 | 列顺序 |
| --- | --- |
| `users.csv` | 登录账号、用户昵称、手机号、邮箱、部门、岗位、角色、状态、创建时间、最近登录 |
| `roles.csv` | 角色名称、权限字符、数据权限、状态、创建时间、备注 |
| `menus.csv` | 菜单名称、类型、图标、路由地址、组件路径、权限标识、排序、状态 |

接口依据：脚手架的 `AuthController.java`、`SystemManagementController.java`、`AuthService.java`、`SystemManagementService.java`、`SystemManagementMapper.java`，及请求和响应类型，对照前端 `scaffold-vue/src/api/auth.ts` 和 `scaffold-vue/src/api/system.ts`。
