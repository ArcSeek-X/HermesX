# Java 部门管理与菜单管理学习案例

更新时间：2026-11-24。参考工程：`vibe-template/scaffold-master-main`。

> **SQL 执行更新（2026-11-24）**：正式 SQL 包含冻结的 `BASELINE_20261123` 和组织迁移 `ORGANIZATION_20261124`，Java已关闭启动初始化并移除分段读取；测试显式使用正式SQL，不再用菜单夹具替换表结构。独立手动工具已实现，本机system库已初始化，生产部署仍待安排，见 [SQL 管理与数据库升级方案](../DB/sql_management_and_execution_plan.md)。

本案例说明 `hrs-system-service` 的服务端分层；组织前端已在[组织管理方案](../product/系统设置/system_org_management.md)配套实现，沿用用户管理的 Spring Boot、MyBatis、SQLite、管理身份和CSRF保护。部门表按要求命名为 **hrs_system_organization**，菜单表命名为 **hrs_system_menu**，目标位置是 system 自己的 `data/hrs_system.db`。**本机system库已初始化，组织测试集已导入，菜单数据暂不导入**。Java 菜单接口、对象、业务逻辑及 Mapper 已调整；后续授权仅先整理了正式 SQL 基线，使用内存 SQLite 验证。Python 数据库未修改；组织页面与前端API已按确认的接口契约实现，本机开发代理已接通组织页面，正式网关认证仍待安排。

接口正文已统一为 [RestResult](java_common_response_design.md)：VO/树放在resultData，删除返回HTTP200及resultData=true。

## 1. 从参考工程保留什么，补充什么

| 项目 | scaffold中的做法 | HermesX落地 |
| --- | --- | --- |
| 部门表 | sys_dept | hrs_system_organization，保留主要字段与长度 |
| 菜单表 | sys_menu | hrs_system_menu，直接采用前端已确认的module/group/page统一节点及menu_业务字段 |
| 部门祖先路径 | ancestors字符串 | 服务端计算；移动时在同一事务更新全部子孙，超长则整体回滚 |
| 树查询 | 父子列表组树 | 组织按sort、organization_id升序，菜单按menuSort、id升序；筛选后保留命中节点的祖先，避免子节点丢失 |
| 部门删除 | 有子部门或用户时拒绝 | 同样拒绝，停用但未删除的子节点/用户也计入；其余逻辑删除 |
| 菜单删除 | 检查子节点、角色引用后删除 | 当前检查子节点并逻辑删除；角色菜单关联尚未实现，未来接入时须补关联检查 |
| 菜单ID | 服务端计算nextMenuId | SQLite自增主键，不使用MAX(id)+1，避免并发分配冲突 |
| 权限 | 参考项目已有完整权限底座 | 复用当前配置管理身份，不假装移植了完整角色授权 |
| 必备字段 | 原表缺少统一归属列，菜单也没有软删除字段 | 两表有enterprise_id、delete_flag；菜单organization_id为归属，组织organization_id为唯一主键，遵循组织主数据表特例 |

**当前只是部门和菜单数据管理，不是动态授权系统。** 菜单的menuPermission是定义字符串，保存它不会自动授予用户权限；Java导航接口按menuStatus排除禁用子树，menuVisible仅供前端显示控制（父级隐藏时后代也应隐藏）。菜单修改不会自动改写已有登录会话的本地缓存。前端旧显示/状态过滤逻辑尚待按新规则调整。未移植导出、角色菜单分配、企业主数据、用户自助权限或菜单前端页面。

## 2. 每一层放什么

下面路径均相对于 `hrs-system-service/`：

```text
pojo/src/main/java/hermesx/system/
├── base/TreeNode.java
├── dto/
│   ├── OrganizationWriteDTO.java
│   ├── OrganizationEditDTO.java
│   ├── OrganizationDeleteDTO.java
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
    # 正式SQL不放resources；服务sql/hrs-system-service.sql按版本管理
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

组织表采用20列结构，完整约束见[组织字段表](../product/系统设置/system_org_management.md#sec-3)。MyBatis使用显式构造映射，数据库前缀不要求暴露为JSON前缀。

| 数据库列 | JSON/Java属性 | 类型、含义及规则 |
| --- | --- | --- |
| organization_id | organizationId | INTEGER自增唯一主键；不再有id或独立组织归属列 |
| parent_id / ancestors | parentId / ancestors | 上级主键、服务端计算的祖先路径；0为根 |
| organization_name / organization_short_name / organization_code | name / shortName / code | 名称100、简称64、业务编码64；name必填 |
| organization_email / organization_phone / organization_leader | email / phone / leader | 邮箱128、电话32、负责人文本64 |
| organization_nature / organization_type / remark | nature / type / remark | 字典编码32、字典编码32、备注500；页面字典待配置时禁用下拉框并保留旧值 |
| sort / status | sort / status | 非负排序、启用1/停用0 |
| enterprise_id | enterpriseId | 可空正整数，企业元数据，不直接等于操作者权限 |
| delete_flag | 内部deleteFlag | 0正常、1已删除；VO不返回 |
| create_by / update_by / create_time / update_time | createBy / updateBy / createTime / updateTime | 可信操作者、UTC时间；不接受前端填写 |

用户dept_id引用组织表organization_id；用户自己的organization_id仍是原有归属元数据，不能拿它和组织节点主键比较。父子及关联用户只校验同enterpriseId，NULL表示未分配，不是通配符。现有组织不能直接修改企业归属。

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
      → OrganizationMapper.xml中的INSERT RETURNING organization_id
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

组织接口已按确认的操作路径收敛；菜单管理沿用原接口，避免无关改动。

| 方法 | 组织接口 | 成功resultData |
| --- | --- | --- |
| POST | /api/system/organization/list-organization | ListPageVO：list/total/pages/pageNum/pageSize |
| GET | /api/system/organization/get-organization-tree | 完整上级候选树，可选enterpriseId，无表格筛选条件 |
| GET | /api/system/organization/detail-organization/{organizationId} | OrganizationVO，children为空数组 |
| POST | /api/system/organization/add-organization | 201 + OrganizationVO及Location |
| POST | /api/system/organization/edit-organization | OrganizationVO；JSON含organizationId和13个完整字段 |
| POST | /api/system/organization/delete-organization | true；JSON只含organizationId |

列表请求直接为common PageQueryDTO（pageNum/pageSize/filterList），不包resultData；响应一律RestResult。默认1/20、pageSize范围1～100；组织页面请求1/10。服务端按同一节点的条件AND过滤，再保留祖先并按根分页；一次返回当前页结果子树，展开不发请求。只命中父节点不自动带出未命中子孙。具体筛选结构与完整示例见[组织接口方案](../product/系统设置/system_org_management.md#sec-6)。

菜单管理接口仍为POST /api/system/menus、GET /api/system/menus/{id}、GET /api/system/menus/tree、PUT /api/system/menus/{id}、DELETE /api/system/menus/{id}。管理树支持keyword/status/enterpriseId/organizationId，不分页；筛选保留祖先。

另提供 **`POST /api/system/list-menu`** 作为登录后的导航完整树接口：无请求体、不使用管理筛选参数，返回`RestResult<List<MenuVO>>`。复用同一个Service和Mapper，先校验完整树，再递归移除menuStatus不为1的节点及其整棵子树，保持menuSort、id排序；不按menuVisible过滤，也不改写子节点显示标志。不能直接复用管理树的status=1筛选，因为管理查询会补齐禁用祖先。所有返回的page均使用自身完整menuRoutePath；用户级授权字段保留，授权逻辑暂不实现。导航与管理目前共用MenuVO，响应仍保留menuStatus字段，导航中只会是1；前端不应再承担启用状态的业务判断，现有旧判断待客户端阶段移除。空树是[]；坏数据返回500/INVALID_TREE，不伪装成功空树。

**组织POST编辑、菜单PUT均是完整更新可编辑资料，不是PATCH。** 组织使用name、shortName、code、nature、type、remark等13个写入字段，organizationId只在编辑体中定位；菜单必填menuCode、menuName、menuType，page另需两个路径。菜单省略menuParentId会改为根0（只有module合法），menuDescription/menuPosition/menuExpanded/menuVisible/menuSort/menuStatus默认值分别为""/content/false/true/0/1；可选字段省略则清空。修改组织需带回enterpriseId，菜单需带回原enterpriseId/organizationId。审计、删除标志及未知字段不接受客户端指定。

错误：400格式、长度或取值错误；401未认证；403无管理权限或CSRF失败；404节点不存在/已删除；409树结构、归属或引用冲突。CSRF校验失败统一返回403/CSRF_INVALID。数据库不可用沿用503响应。没有恢复或物理清理接口。

## 7. 对原用户管理的必要收口

之前的用户案例没有真实部门表，deptId只校验正整数。现在新增部门后，用户新增和修改通过 `IOrganizationService.validateUserDepartment` 检查：

- deptId为NULL：不关联部门。
- 非NULL：部门必须存在且未删除，enterpriseId必须与部门一致；用户organizationId不参与和组织节点主键的比较。
- 部门停用但未删除仍可关联；当前status不承担登录或授权语义。
- 删除部门时，所有未删除用户均算引用，包括停用用户；删除用户后才解除删除阻塞。

这是内部Java API行为收紧，之前随便填写一个不存在deptId的请求现在会失败。旧库中若有孤立deptId，需要管理员明确改成NULL或真实部门，不能自动创建假部门。当前并未给用户表新增数据库外键；校验在业务层执行，各入口都必须经过Service。

## 8. 数据库部署仍待手动安排

`data/hrs_system.db` 已由手动工具初始化并写入组织验证数据。服务 `sql/hrs-system-service.sql` 包含冻结的BASELINE_20261123与ORGANIZATION_20261124，用户、组织和菜单目标结构已通过临时SQLite验证。Java已移除旧分段选择，生产配置禁止启动初始化；SQL仅进入测试classpath，不进入业务JAR。独立工具已实现，本机库及服务已就绪；其他环境使用业务接口前仍须手动准备匹配结构。

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

Java仍要求独立Basic管理身份及CSRF token，前端Python登录会话不会自动成为Java身份。组织页面已通过Vite本机开发代理代传现有管理校验信息，仅允许本机同源请求，凭据与Java session不进入浏览器；POST保护保持开启。正式auth、Token与网关认证未实现，不能把本机代传作为正式用户授权方案，配置与流程见[组织管理方案第九节](../product/系统设置/system_org_management.md#sec-9)。

## 10. 验证、限制和回滚

执行`mvn -o -pl hrs-system-service/rest -am test`验证本轮Java代码，临时SQLite测试贯穿Controller→Service→Mapper/XML。覆盖菜单完整树POST、统一响应、camelCase字段、布尔类型、可选字段省略、排序、稳定业务码、CRUD、循环、父子关系、归属、重复业务码/路由、逻辑删除、空树、坏树、禁用祖先子树过滤、隐藏节点保留、路径不按业务码拼接、group相对路径元数据及认证/CSRF；同时保留用户、部门和旧用户迁移回归。

本机独立库已初始化，组织页面的真实查询、分页和CRUD已通过开发代理验收；菜单56个manifest节点导入、正式登录/网关认证、生产部署和Windows/MySQL尚未验收，不将本机管理员联调等同于正式用户授权已实现。没有角色菜单分配或权限动态授权，本阶段完整树仅向现有SYSTEM_ADMIN身份开放。

system本机独立库已写入组织测试数据，回滚需同时考虑源码与数据库结构；停止服务并保留后续变更后，按数据库规范使用备份恢复，不能只回滚Java连接不匹配的表结构。本案例聚焦Java，配套前端及开发代理实现见组织管理方案；专题文档暂无英文对应版本，不建立平行翻译。

关联：[Java工程规范](java_engineering_architecture.md)、[数据库规范](../DB/database_rules.md)、[用户案例](java_user_management_case.md)、[菜单接口契约](../authority/frontend/menu_api_contract.md)。

本机初始化、组织演示SQL、服务启动/停止和私有管理配置位置统一见[组织管理方案11.4](../product/系统设置/system_org_management.md#sec-11)。本机开发代理已接通组织接口并保留现有Basic/CSRF；正式登录/Token/网关认证暂缓，本次未导入用户或菜单数据。
