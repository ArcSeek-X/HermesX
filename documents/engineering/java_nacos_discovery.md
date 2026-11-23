# system 接入 Nacos 服务注册与发现

## 范围与数据库边界

当前只接入 `hrs-system-service/rest`，不启动 auth 或 analysis，不迁移 Python，不引入 Redis/RabbitMQ/MySQL，也不接入 Nacos 配置中心。Spring 配置继续由本地环境变量提供。

| 服务 | 独立数据库 | 当前状态 |
| --- | --- | --- |
| Python | data/stock_analysis.db | 保留现有运行方式 |
| system | data/hrs_system.db | 本次Java使用的独立SQLite库 |
| auth | data/hrs_auth.db | 后续规划，当前不创建 |
| Java analysis | data/hrs_analysis.db | 后续规划，当前不创建 |

各服务只读写自己的数据，经接口访问其他服务。SQLite 路径仍由 `HRS_SYSTEM_DB_URL` 显式指定，不把 Java 用户表放进 Python 的数据库。父目录须存在；旧库升级见[用户管理案例](java_user_management_case.md)。

## 依赖与版本

system 父 POM 管理 Spring Boot 3.5.14、Spring Cloud 2025.0.0、Spring Cloud Alibaba 2025.0.0.0；rest 引入 `spring-cloud-starter-alibaba-nacos-discovery`。没有给 pojo 或其他服务增加注册客户端依赖。Starter 自动接线注册与发现，无需编写注册HTTP请求，也无需手工调用注册方法。

本机现有容器 `dev-nacos` 为 Nacos 2.5.4，开放8848、9848、9849，当前认证关闭。此版本说明只是本机验证记录，不作为其他环境的默认配置。

**兼容约束**：所选组件使用 Nacos 3.x 客户端。官方要求对接2.x服务端时避开 public/空命名空间，且维护者建议优先使用同代客户端与服务端。因此当前保留现有容器，使用独立命名空间并实测；本次测试不等于对所有2.x功能作兼容承诺。将来升级Nacos须重新验证注册、发现、认证与退出注销。

依据：[版本对应说明](https://sca.aliyun.com/docs/2025.x/overview/version-explain/)、[官方接入及public命名空间约束](https://sca.aliyun.com/docs/2025.x/user-guide/nacos/quick-start/)、[维护者对2.x服务端与3.x客户端的说明](https://github.com/alibaba/spring-cloud-alibaba/issues/4274)。

system 运行配置统一位于 `hrs-system-service/rest/src/main/resources/application.properties`，不再同时保留 YAML；环境变量名称和默认值不变。

## 启动方式

默认 `HRS_SYSTEM_NACOS_ENABLED=false`，支持离线测试和不使用注册中心的单机运行。开启时必须配置地址和专用命名空间ID；`NacosRegistrationConfig` 会拒绝缺失地址、public/空命名空间，以及0.0.0.0等不可作为实例地址的值。

本机已为 HermesX 建立 `hermesx-dev` 命名空间，显示名称为 `HermesX Dev`。这是注册隔离空间，不是业务租户，更不是数据库。

从仓库根使用 Bash：

```bash
./mvnw clean verify
mkdir -p data
export HRS_SYSTEM_DB_URL="jdbc:sqlite:$(pwd)/data/hrs_system.db"
export HRS_SYSTEM_NACOS_ENABLED=true
# 本机已有容器的宿主机映射地址；其他环境按实际地址设置。
export HRS_NACOS_SERVER_ADDR=127.0.0.1:8848
export HRS_NACOS_NAMESPACE=hermesx-dev
export HRS_NACOS_GROUP=DEFAULT_GROUP
export HRS_SYSTEM_REGISTER_IP=127.0.0.1
# 管理API账号与Nacos账号是两套身份，不得混用。
read -r -p '用户管理API账号: ' HRS_SYSTEM_ADMIN_USERNAME
export HRS_SYSTEM_ADMIN_USERNAME
read -r -s -p '用户管理API密码（12至72个UTF-8字节）: ' HRS_SYSTEM_ADMIN_PASSWORD
printf '\n'
export HRS_SYSTEM_ADMIN_PASSWORD
java -jar hrs-system-service/rest/target/hrs-system-service-rest-0.1.0-SNAPSHOT.jar
```

服务仍默认绑定本机、使用随机可用HTTP端口，注册时使用实际启动端口，而不是登记0。调用用户管理API仍需要Basic认证和写操作CSRF，Nacos注册不会绕过接口保护。

如注册中心开启认证，额外设置 `HRS_NACOS_USERNAME`、`HRS_NACOS_PASSWORD`；不把凭据写入Git。Java不自动读取根 `.env`，变量须export到进程。全部变量在 `.env.example` 中有说明。

进入现有Nacos控制台，选择 `HermesX Dev` 命名空间，在服务列表查看 `DEFAULT_GROUP` 下的 `hrs-system-service`，核对实例IP、真实端口及健康状态。正常停止Java后，实例应注销。Nacos只登记与发现地址，不代理业务HTTP请求，也不替你启动服务。

**地址要求**：本机调用时可注册127.0.0.1；容器或其他电脑调用时，必须设置调用方可达的 `HRS_SYSTEM_REGISTER_IP`，并相应设置绑定地址及网络规则。不能登记0.0.0.0，也不能把Docker容器内的localhost误当成宿主机。Nacos客户端通信除8848之外还需要可达的gRPC端口，实际配置以部署为准。

## 验证与限制

离线门禁检查原CRUD及SQLite迁移，另有注册配置校验测试；真实Nacos测试使用临时独立SQLite库和随机API管理凭据，检查服务注册、查询实例、实际HTTP访问与优雅退出注销，不写入Python数据库。

**2026-11-18 本机验证结果**：`./mvnw clean verify` 全部10个模块与12项测试通过；现有 Nacos 2.5.4 + 当前客户端组合在 `hermesx-dev` 中注册健康实例成功，使用注册中心返回的地址访问真实用户HTTP接口成功，优雅停止后实例成功注销。测试使用临时SQLite文件，验证进程已停止，控制台不会长期保留该临时实例。Nacos启用认证后的链路、跨机器网络及Windows尚未验证。

当前没有其他业务调用方，尚未加入Feign或负载均衡业务客户端；验证的是注册中心能够返回实例地址。未来auth/analysis通过服务发现得到system地址时，还需单独设计调用认证、超时与故障处理。

回滚可先设置 `HRS_SYSTEM_NACOS_ENABLED=false` 并重启，保留SQLite数据。若撤回依赖与配置，也不需要删除用户表或改动Python。共享Docker容器没有升级、重启或删除；独立开发命名空间可保留复用。

本专题暂无英文对应文档，本次不新增重复维护的英文版。
