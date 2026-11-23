# Java 部门管理与菜单管理学习案例

更新时间：2026-11-23。参考工程：`vibe-template/scaffold-master-main`。

> **SQL 执行更新（2026-11-24）**：正式 SQL 为 `BASELINE_20261123`，Java已关闭启动初始化并移除分段读取；测试显式使用正式SQL，不再用菜单夹具替换表结构。独立手动工具已实现，正式部署仍待安排，见 [SQL 管理与数据库升级方案](../DB/sql_management_and_execution_plan.md)。

本案例只实现 `hrs-system-service` 的服务端，沿用用户管理的 Spring Boot、MyBatis、SQLite、管理身份和CSRF保护。部门表按要求命名为 **hrs_system_organization**，菜单表命名为 **hrs_system_menu**，目标位置是 system 自己的 `data/hrs_system.db`。**暂不创建此数据库、不导入初始化菜单数据**。Java 菜单接口、对象、业务逻辑及 Mapper 已调整；后续授权仅先整理了正式 SQL 基线，使用内存 SQLite 验证。Python 数据库和前端功能代码未修改。

接口正文已统一为 [RestResult](java_common_response_design.md)：VO/树放在resultData，删除返回HTTP200及resultData=true。

## 1. 从参考工程保留什么，补充什么

| 项目 | scaffold中的做法 | HermesX落地 |
| --- | --- | --- |
| 部门表 | sys_dept | hrs_system_organization，保留主要字段与长度 |
| 菜单表 | sys_menu | hrs_system_menu，直接采用前端已确认的module/group/page统一节点及menu_业务字段 |
| 部门祖先路径 | ancestors字符串 | 服务端计算；移动时在同一事务更新全部子孙，超长则整体回滚 |
| 树查询 | 父子列表组树 | 按sort、id升序；筛选后保留命中节点的祖先，避免子节点丢失 |
| 部门删除 | 有子部门或用户时拒绝 | 同样拒绝，停用但未删除的子节点/用户也计入；其余逻辑删除 |
| 菜单删除 | 检查子节点、角色引用后删除 | 当前检查子节点并逻辑删除；角色菜单关联尚未实现，未来接入时须补关联检查 |
| 菜单ID | 服务端计算nextMenuId | SQLite自增主键，不使用MAX(id)+1，避免并发分配冲突 |
| 权限 | 参考项目已有完整权限底座 | 复用当前配置管理身份，不假装移植了完整角色授权 |
| 必备归属列 | 原表缺少统一归属列，菜单也没有软删除字段 | 两表均增加enterprise_id、organization_id、delete_flag，遵循数据库规范 |

**当前只是部门和菜单数据管理，不是动态授权系统。** 菜单的menuPermission是定义字符串，保存它不会自动授予用户权限；Java导航接口按menuStatus排除禁用子树，menuVisible仅供前端显示控制（父级隐藏时后代也应隐藏）。菜单修改不会自动改写已有登录会话的本地缓存。前端旧显示/状态过滤逻辑尚待按新规则调整。未移植导出、角色菜单分配、企业主数据、用户自助权限或前端页面。

## 2. 每一层放什么

下面路径均相对于 `hrs-system-service/`：

```text
pojo/src/main/java/hermesx/system/
├── base/TreeNode.java
├── dto/
│   ├── OrganizationWriteDTO.java
│   └── MenuWriteDTO.java
├── entity/
│   ├── OrganizationEntity.java
│   └── MenuEntity.java
└── vo/
    ├── OrganizationVO.java
    └── MenuVO.java

rest/src/main/
├── java/hermesx/system/
│   ├── controller/OrganizationController.java
│   ├── controller/MenuController.java
│   ├── service/IOrganizationService.java
│   ├── service/IMenuService.java
│   ├── service/impl/OrganizationServiceImpl.java
│   ├── service/impl/MenuServiceImpl.java
│   ├── dao/OrganizationMapper.java
│   ├── dao/MenuMapper.java
│   ├── utils/TreeUtils.java
│   └── exception/ManagementException.java
└── resources/
    ├── application.properties
    ├── mapper/OrganizationMapper.xml
    ├── mapper/MenuMapper.xml
    # 正式SQL不放resources；服务根目录hrs-system-service.sql按版本管理
```

| 类型 | 大白话 | 本例怎么写 |
| --- | --- | --- |
| WriteDTO | 调用方允许填写什么 | 名称、父节点、业务属性和归属；格式用校验注解，不接受ancestors、deleteFlag或审计人 |
| Entity | 数据库一行是什么样 | 与列对应；含删除标志和审计字段，只在内部流转 |
| VO | 允许返回什么 | 部门返回name等原有字段；菜单返回menuName/menuType等统一字段，隐藏deleteFlag，使用children表达树 |
| Controller | 请求从哪里来，返回什么状态 | 接收JSON、格式校验、调用Service；不写SQL |
| Service接口 | 业务有哪些能力 | create/get/tree/update/delete；菜单另有listMenu完整导航查询，部门另有用户归属校验 |
| ServiceImpl | 什么操作允许，如何保持正确 | 管理权限、父节点、循环、归属、菜单类型和事务 |
| Mapper接口 | 数据库操作的方法声明 | @Mapper生成代理，@Param明确XML参数名 |
| Mapper XML | 实际SQL怎么执行 | #{参数}绑定、record构造映射、祖先路径更新和软删除 |
| TreeUtils | 把平面节点拼成树 | 纯内存算法，不读会话和数据库，不替代业务权限 |
| ManagementException | 可预期业务失败如何说明 | 不存在返回404；树/归属/引用冲突返回409，由统一异常处理器转换 |

WriteDTO在新增和PUT更新中复用，是因为这两种请求允许编辑的字段相同，不是把Entity当DTO。Service接口上的校验约束也适用于同服务内的调用。没有新增另一套DAO或Controller直接调用Mapper的捷径。

## 3. 部门字段与ID关系

| 数据库列 | JSON/Java属性 | 类型、含义及规则 |
| --- | --- | --- |
| id | id | INTEGER自增，Java Long，本部门节点的真实主键 |
| parent_id | parentId | BIGINT，上级部门id；0为根节点，不是实际部门记录 |
| ancestors | ancestors | VARCHAR(500)，从根到直接父节点的ID列表，例如1,2；根为空字符串，路径不含虚拟节点0 |
| dept_name | name / deptName | VARCHAR(100)，名称必填；输入输出用name，Entity用deptName |
| leader | leader | VARCHAR(64)，负责人，可空 |
| phone | phone | VARCHAR(32)，电话，可空，不强制特定国家手机号格式 |
| email | email | VARCHAR(128)，可空，非空输入需符合邮箱格式 |
| sort | sort | INT，非负，缺省0，同级按sort、id升序 |
| status | status | TINYINT，1正常、0停用，缺省1；当前是管理状态，不触发会话撤销 |
| enterprise_id | enterpriseId | BIGINT，可空正整数，企业归属元数据 |
| organization_id | organizationId | BIGINT，可空正整数，组织归属元数据；不是本行的id，也不是parentId |
| delete_flag | 内部deleteFlag | TINYINT，0正常、1已删除；对外VO不返回 |
| create_by / update_by | createBy / updateBy | VARCHAR(64)，由可信管理身份提供，不从请求体读取 |
| create_time / update_time | createTime / updateTime | UTC时间，创建自动生成，更新SQL显式维护 |

这里按用户要求把“部门管理”放进名为organization的表。**用户表的dept_id关联该表id**；用户表的organization_id和部门表的organization_id则是同一类归属元数据，不能把它们都混成部门节点ID。

父子节点必须具有相同enterpriseId和organizationId，NULL也按未分配的真实状态参与比较，不能当通配符。现有节点不支持直接修改归属，防止只改一行造成子树和关联用户跨范围；如需跨归属迁移，需要另行设计完整用例。

部门最多64层，祖级路径最多500字符。不能以自己或任意子孙为父；父节点必须存在且未删除。停用节点仍可以存在于管理树，停用不会级联删除或默认隐藏子节点。

## 4. 菜单字段和父子类型

下表为 Java Mapper 已采用的**目标列契约**，不是已经部署的数据库结构。主键仍为 id；归属、删除和审计字段不加 menu_。其余数据库业务字段加 menu_，接口使用对应 camelCase。

| 目标数据库列 | JSON/Java属性 | 规则 |
| --- | --- | --- |
| id | id | 数据库自增Long主键，不用menuCode替代 |
| menu_parent_id | menuParentId | 父节点主键，根为0 |
| menu_code | menuCode | 必填、最多128字符；trim后在未删除菜单中唯一，是稳定业务标识 |
| menu_name | menuName | 必填、最多100字符；改名称不要求改业务标识 |
| menu_description | menuDescription | 最多500字符，未填写补空字符串 |
| menu_type | menuType | module / group / page |
| menu_route_path | menuRoutePath | page必填完整站内路径，以单个/开头；不由menuCode或父级路径拼接，page路由在未删除菜单中唯一；group路径是可选元数据，不强制以/开头 |
| menu_page_path | menuPagePath | page必填，pages/开头；仅为前端已有页面白名单的标识，不执行Java代码 |
| menu_icon / menu_badge | menuIcon / menuBadge | 可选，各最多64字符 |
| menu_position | menuPosition | header / content / footer，默认content |
| menu_expanded / menu_visible | menuExpanded / menuVisible | JSON布尔值，默认false / true |
| menu_sort / menu_status | menuSort / menuStatus | 非负排序默认0；状态0/1默认1，Java导航返回前排除禁用节点及其整棵子树；管理查询仍可看到禁用记录 |
| menu_permission | menuPermission | 可选、最多128字符；只保存标识，不代替真实授权 |
| menu_auth / menu_exact | auth / exact | 可选路由扩展：public/protected及布尔值；保留manifest原名 |
| enterprise_id / organization_id | enterpriseId / organizationId | 可空正整数；父子归属一致，已有节点不直接修改归属 |
| delete_flag | 内部deleteFlag | 逻辑删除，不对外输出 |
| create_by/update_by/create_time/update_time | 对应camelCase | 审计字段，不接受前端指定 |

VO使用`@JsonInclude(NON_NULL)`省略可选空字段，不能同时返回旧name/type等别名；children始终为数组。实体与DTO不直接当作对外响应。

| 父级 | 允许的子级 |
| --- | --- |
| 根位置menuParentId=0 | 只能module |
| module | group / page |
| group | group / page |
| page | 无，必须是叶子节点 |

更新类型、移动节点时同时校验已有孩子、祖先循环、最大64层及归属，失败时整笔回滚。带未删除孩子的节点不能删除。旧dir/menu/btn不再接受，按钮权限树不属于本次菜单导航契约。

## 5. 一次新增与一次移动如何流转

新增部门：

```text
OrganizationWriteDTO
  → OrganizationController
  → IOrganizationService / OrganizationServiceImpl
      → 检查管理身份、父节点存在性、归属和路径长度
      → OrganizationMapper.insert
      → OrganizationMapper.xml中的INSERT RETURNING id
      → 查询OrganizationEntity并转换OrganizationVO
  → 返回201 Created及Location
```

例如A下有B、B下有C，把B移动到D下时：

```text
移动前：A → B → C       B.ancestors=A，C.ancestors=A,B
移动后：D → B → C       B.ancestors=D，C.ancestors=D,B
```

Service先检查D不是B或B的子孙，再更新B，按父子关系逐个重算子孙路径。整个过程在同一数据库事务内；如果某个子孙路径超出500字符，B的父节点、名称及已更新的子孙路径一起回滚。

菜单没有ancestors列，树根据menuParentId组装；同样先验证父链、类型和移动后深度，再写入。

## 6. 接口和请求语义

两个模块使用相同操作形式：

| 方法 | 部门接口 | 菜单接口 | 成功 |
| --- | --- | --- | --- |
| POST | /api/system/organizations | /api/system/menus | 201 + RestResult(VO)及Location |
| GET | /api/system/organizations/{id} | /api/system/menus/{id} | 200 + RestResult(VO)，详情children为空列表 |
| GET | /api/system/organizations/tree | /api/system/menus/tree | 200 + RestResult(树数组) |
| PUT | /api/system/organizations/{id} | /api/system/menus/{id} | 200 + RestResult(更新后VO) |
| DELETE | /api/system/organizations/{id} | /api/system/menus/{id} | 200 + RestResult(true) |

上表的管理树查询支持keyword、status、enterpriseId、organizationId；keyword按名称字面子串匹配，后3项精确筛选。没有分页，树是完整结构。状态/关键词筛选先保留命中节点，再补齐其祖先作为上下文；祖先可以不满足筛选，不会篡改祖先的真实状态。只命中父节点不会自动返回所有不命中的子孙。resultData中的空树为[]，叶子children也为[]。

另提供 **`POST /api/system/list-menu`** 作为登录后的导航完整树接口：无请求体、不使用管理筛选参数，返回`RestResult<List<MenuVO>>`。复用同一个Service和Mapper，先校验完整树，再递归移除menuStatus不为1的节点及其整棵子树，保持menuSort、id排序；不按menuVisible过滤，也不改写子节点显示标志。不能直接复用管理树的status=1筛选，因为管理查询会补齐禁用祖先。所有返回的page均使用自身完整menuRoutePath；用户级授权字段保留，授权逻辑暂不实现。导航与管理目前共用MenuVO，响应仍保留menuStatus字段，导航中只会是1；前端不应再承担启用状态的业务判断，现有旧判断待客户端阶段移除。空树是[]；坏数据返回500/INVALID_TREE，不伪装成功空树。

**PUT是完整更新可编辑资料，不是PATCH。** 部门仍使用原有name、parentId等字段；菜单必填menuCode、menuName、menuType，page另需两个路径。菜单省略menuParentId会改为根0（只有module合法），menuDescription/menuPosition/menuExpanded/menuVisible/menuSort/menuStatus默认值分别为""/content/false/true/0/1；可选字段省略则清空。修改带归属节点时带回原enterpriseId/organizationId。审计、删除标志及未知字段不接受客户端指定。

错误：400格式、长度或取值错误；401未认证；403无管理权限或CSRF失败；404节点不存在/已删除；409树结构、归属或引用冲突。CSRF校验失败统一返回403/CSRF_INVALID。数据库不可用沿用503响应。没有恢复或物理清理接口。

## 7. 对原用户管理的必要收口

之前的用户案例没有真实部门表，deptId只校验正整数。现在新增部门后，用户新增和修改通过 `IOrganizationService.validateUserDepartment` 检查：

- deptId为NULL：不关联部门。
- 非NULL：部门必须存在且未删除，enterpriseId/organizationId必须与部门一致。
- 部门停用但未删除仍可关联；当前status不承担登录或授权语义。
- 删除部门时，所有未删除用户均算引用，包括停用用户；删除用户后才解除删除阻塞。

这是内部Java API行为收紧，之前随便填写一个不存在deptId的请求现在会失败。旧库中若有孤立deptId，需要管理员明确改成NULL或真实部门，不能自动创建假部门。当前并未给用户表新增数据库外键；校验在业务层执行，各入口都必须经过Service。

## 8. 数据库暂缓实施：当前不能直接运行新菜单Mapper

`data/hrs_system.db` 是目标业务库，本轮未创建或写入。服务 `sql/hrs-system-service.sql` 已改为单一 BASELINE_20261123，用户、部门和目标菜单结构已对齐并通过内存验证。Java已移除旧分段选择，生产配置禁止启动初始化；SQL仅进入测试classpath，不进入业务JAR。独立工具已实现，真实库尚未部署；使用业务接口前须手动运行工具准备匹配结构。

Java旧初始化移除及测试同步已完成。独立工具已实现，后续数据库阶段需按明确安排执行，按明确安排将manifest节点以稳定menuCode导入，配置真实HRS_SYSTEM_DB_URL后再进行真实服务联调。暂不提供默认删表、迁移、种子导入或创建业务数据库命令。

测试通过属性显式开启SQL初始化，并在测试创建的临时SQLite上加载Maven仅供测试复制的正式`sql/hrs-system-service.sql`。旧菜单结构替换夹具已删除；CRUD、MyBatis映射与事务直接在正式目标结构验证，避免另一份DDL掩盖结构偏差。这不代表真实业务库已部署。

## 9. 登录导航查询如何经过各层

```text
前端登录成功 → loadMenuData（接口模式）
  → POST /api/system/list-menu（没有请求体）
  → SecurityFilterChain：验证现有管理身份及CSRF
  → MenuController.listMenu：调用业务接口并包装响应
  → IMenuService / MenuServiceImpl.listMenu
      → 检查管理身份、读取完整节点、校验树数据
      → MenuMapper.all → MenuMapper.xml SELECT
      → MenuEntity → MenuVO → TreeUtils组树
  → {resultCode:"200", resultMsg:"操作成功。", resultData:[...]}
  → 前端现有Store处理、持久化、注册路由后跳转
```

菜单管理创建模块的请求示例（正式目标数据库准备好后才能实调）：

```json
{
  "menuCode": "system",
  "menuName": "系统管理",
  "menuType": "module",
  "menuParentId": 0,
  "menuSort": 0,
  "menuVisible": true,
  "menuStatus": 1
}
```

创建page时填写真实父节点id、稳定menuCode、menuRoutePath和menuPagePath。`menuPagePath`必须对应已发布前端的页面，接口不能凭字符串创建新页面。

目前Java仍要求独立Basic管理身份及CSRF token，前端原有Python登录会话不会自动成为Java身份。**本轮未实现auth服务、Python会话换取Java凭据或代理转发**；POST接口没有为联调方便关闭安全校验。真实联调前需明确这部分接入方案。

## 10. 验证、限制和回滚

执行`mvn -o -pl hrs-system-service/rest -am test`验证本轮Java代码，临时SQLite测试贯穿Controller→Service→Mapper/XML。覆盖菜单完整树POST、统一响应、camelCase字段、布尔类型、可选字段省略、排序、稳定业务码、CRUD、循环、父子关系、归属、重复业务码/路由、逻辑删除、空树、坏树、禁用祖先子树过滤、隐藏节点保留、路径不按业务码拼接、group相对路径元数据及认证/CSRF；同时保留用户、部门和旧用户迁移回归。

正式业务库、建表资源更新、56个manifest节点导入、真实浏览器到Java的认证与转发、Windows/MySQL尚未验收，不将测试夹具成功等同于业务库已部署。没有角色菜单分配或权限动态授权，本阶段完整树仅向现有SYSTEM_ADMIN身份开放。

回滚仅需还原本轮Java源码、Mapper和对应测试/文档，不需要数据库回滚，因为本轮未操作任何业务库。前端功能代码未更改；专题文档暂无英文对应版本，不建立平行翻译。

关联：[Java工程规范](java_engineering_architecture.md)、[数据库规范](../DB/database_rules.md)、[用户案例](java_user_management_case.md)、[菜单接口契约](../authority/frontend/menu_api_contract.md)。
