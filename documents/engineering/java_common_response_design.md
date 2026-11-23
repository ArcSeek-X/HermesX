# Java common 与统一接口响应

更新时间：2026-11-19。本文记录已经实现的公共模块与system接口契约，参考Newsee common的统一枚举/包装思路，按HermesX实际功能裁剪。

## 1. 模块和依赖

`hrs-common` 是普通公共JAR，不是第四个Java微服务，没有启动类、数据库或Nacos注册。根POM聚合它；system/pojo和system/rest显式依赖它。auth/analysis仍是业务骨架，未来实现接口时再按需接入。

```text
hrs-common/
├── pom.xml
└── src/
    ├── main/java/hermesx/common/
    │   ├── rest/ResultCode.java
    │   ├── rest/ResultCodeEnum.java
    │   ├── rest/RestResult.java
    │   ├── vo/PageVO.java
    │   ├── dao/、entity/、dto/             # 预留，.gitkeep保留
    │   └── exception/、constant/、utils/、validation/  # 预留
    └── test/java/hermesx/common/rest/RestResultTest.java

hrs-system-service/pojo/src/main/java/hermesx/system/
└── enums/SystemResultCodeEnum.java
```

common的生产代码只依赖Java，不引入Spring Web、数据库、业务Entity或用户身份模型。预留dao/entity不意味着common拥有业务表。原system/base/PageVO迁至common/vo/PageVO，原ErrorVO移除；TreeNode仍是system自己的树视图结构。

## 2. 唯一响应结构

system的用户、部门、菜单及CSRF JSON接口统一返回三个字段：

```json
{
  "resultCode": "200",
  "resultMsg": "操作成功。",
  "resultData": true
}
```

- resultCode：字符串，供程序判断，成功统一为"200"；失败保留有意义的业务码，不依赖中文匹配。
- resultMsg：默认由枚举提供，需要具体业务说明时使用明确编写的安全文案，不返回底层异常原文。
- resultData：实际数据，对象、数组、分页对象或布尔值；失败固定为null且保留此字段。

RestResult是不可变record，success每次创建独立对象，不使用共享可变SUCCESS对象。不存在业务层套一次、Controller再套一次的双重包装。

### 成功数据

| 场景 | resultData | HTTP |
| --- | --- | --- |
| 用户/部门/菜单新增 | 新对象VO | 201，保留Location |
| 详情、修改 | 对应VO | 200 |
| 用户分页 | {rows,total,page,pageSize} | 200 |
| 部门树、菜单树 | 树形数组；无数据为[] | 200 |
| 删除 | true | 200，替代旧204 |
| CSRF | {token,headerName,parameterName} | 200 |

分页参数仍在resultData内部，不在最外层重复分页字段。VO的密码白名单和树结构规则不变。HTTP状态码独立于业务结果码，新建201仍可带resultCode="200"。

### 失败示例

HTTP404，用户不存在：

```json
{
  "resultCode": "USER_NOT_FOUND",
  "resultMsg": "用户不存在或已删除。",
  "resultData": null
}
```

HTTP409，不能删除有下级的部门：

```json
{
  "resultCode": "HAS_CHILDREN",
  "resultMsg": "存在下级部门，不能删除",
  "resultData": null
}
```

## 3. 结果码在哪里维护

`hermesx.common.rest.ResultCode` 定义getCode()/getMessage()，公共和业务枚举均实现该接口。

公共枚举 `hrs-common/src/main/java/hermesx/common/rest/ResultCodeEnum.java`：

| resultCode | 默认resultMsg | HTTP |
| --- | --- | --- |
| 200 | 操作成功。 | 200/201 |
| INVALID_REQUEST | 请求参数格式、长度或取值不正确。 | 400 |
| UNAUTHENTICATED | 身份认证失败，请提供有效凭据。 | 401 |
| FORBIDDEN | 无权执行此操作。 | 403 |
| CSRF_INVALID | 请求校验失败，请刷新校验信息后重试。 | 403 |
| NOT_FOUND | 请求的资源不存在。 | 404 |
| METHOD_NOT_ALLOWED | 当前接口不支持此请求方法。 | 405 |
| NOT_ACCEPTABLE | 无法提供请求指定的响应格式。 | 406 |
| UNSUPPORTED_MEDIA_TYPE | 不支持此请求内容类型。 | 415 |
| INTERNAL_ERROR | 系统暂时无法处理请求，请稍后重试。 | 500 |
| DATABASE_UNAVAILABLE | 数据服务暂不可用，请稍后重试。 | 503 |

业务枚举 `hrs-system-service/pojo/src/main/java/hermesx/system/enums/SystemResultCodeEnum.java`：

| resultCode | 默认提示 | HTTP |
| --- | --- | --- |
| USER_NOT_FOUND | 用户不存在或已删除。 | 404 |
| USERNAME_EXISTS | 登录账号已存在。 | 409 |
| ORGANIZATION_NOT_FOUND | 部门不存在或已删除。 | 404 |
| MENU_NOT_FOUND | 菜单不存在或已删除。 | 404 |
| MENU_CODE_EXISTS | 菜单业务标识已存在。 | 409 |
| MENU_ROUTE_EXISTS | 页面路由已存在。 | 409 |
| HAS_CHILDREN | 存在下级数据，不能删除。 | 409 |
| DEPARTMENT_IN_USE | 部门仍关联用户，不能删除。 | 409 |
| INVALID_PARENT | 父节点无效或会造成循环引用。 | 409 |
| SCOPE_MISMATCH | 企业或组织归属不一致。 | 409 |
| INVALID_MENU_TYPE | 菜单父子类型不符合规则。 | 409 |
| TREE_TOO_DEEP | 树形结构超过允许的层级。 | 409 |
| ANCESTORS_TOO_LONG | 部门祖级路径超过允许长度。 | 409 |
| INVALID_TREE | 树形数据异常，请联系管理员。 | 500 |

业务调用直接引用枚举，不在服务中重复手写码字符串。已知业务冲突可细化resultMsg，例如目录/按钮不同的删除提示，但保持resultCode稳定。通用码不放入订单、支付或其他未实现领域；每个新码应有明确含义和验证场景。

## 4. 返回在哪里包装

- 成功：User/Organization/Menu Controller显式调用RestResult.success，Service仍返回业务类型，Mapper只访问数据。
- 已知业务失败：ManagementException携带ResultCode与错误类别；GlobalExceptionHandler映射HTTP状态和RestResult。
- 参数格式、JSON、路径、方法及媒体类型错误：GlobalExceptionHandler统一转换，405保留Allow响应头。
- 认证失败：RestSecurityHandler作为AuthenticationEntryPoint，返回401 JSON并保留WWW-Authenticate认证挑战。
- 权限和CSRF失败：RestSecurityHandler作为AccessDeniedHandler，分别返回FORBIDDEN或CSRF_INVALID。
- 容器错误分发：ApiErrorController统一/error响应；安全链只对ERROR分发放行，不把正常业务接口公开。
- 未预期异常：返回INTERNAL_ERROR，不直接返回Throwable.message、SQL、密码或堆栈。可预期密码长度/按钮权限错误改为显式业务异常，不用“所有IllegalArgumentException都是用户输入错误”的宽泛处理。

没有引入无差别ResponseBodyAdvice；未来文件下载、SSE、流式协议需独立声明，不自动套JSON。HEAD按HTTP协议没有响应体，不能要求HEAD也传三字段JSON。被反向代理/连接层拒绝、超大请求头等未进入应用的错误，不保证由本服务包装。

## 5. 调用方必须同步的地方

本项目尚未上线，直接调整到新契约，不保留旧响应字段或两套包装开关。

```text
用户ID：原 body.id           → body.resultData.id
分页：  原 body.rows/total   → body.resultData.rows/total
树数组：原 body              → body.resultData
CSRF：  原 body.token        → body.resultData.token
错误码：原 body.code         → body.resultCode
错误文案：原 body.message    → body.resultMsg
删除：  原 HTTP204空体       → HTTP200 + resultData=true
```

写接口仍需要管理认证、CSRF token和对应Cookie。获取token的示例改为：

```bash
CSRF_TOKEN=$(printf '%s' "$CSRF_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["resultData"]["token"])')
```

Python API、Web和桌面入口没有切换或修改；它们现有Python响应不受影响。未来前端接入Java时必须按这个契约取数据，不能假设修改common就自动改变Python服务。

## 6. 验证与回滚

公共模块验证不可变独立响应、失败null数据和非法契约。system测试保留真实SQLite业务风险验证，并增加协议边界测试：公共/业务码无重复、恰好三字段、仅包装一次、认证/CSRF、400/404/405/406/415、异常脱敏及容器错误分发。

2026-11-19验证：`./mvnw clean verify` 全部11个模块、共30项测试通过（common 3项、system 27项）；真实可执行JAR验证统一成功/错误结构、认证挑战及三组CRUD，测试进程已停止。产物不含旧ErrorVO、旧PageVO或测试探针。未验证Windows及未来跨服务业务调用。

本次不改表、不迁移真实用户库；测试使用临时库。回滚需同批撤回common依赖、Controller/错误处理、测试和调用示例；不需要数据库逆迁移，不能只退回某个Controller造成新旧协议混杂。

本专题暂无英文对应版本，本次不增加平行翻译。关联：[Java工程规范](java_engineering_architecture.md)、[用户案例](java_user_management_case.md)、[部门菜单案例](java_organization_menu_management_case.md)。
