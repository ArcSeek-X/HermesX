# HermesX 目标架构实施延续：data_provider 内部职责优化初步方案

> 保留数据源包现有位置，以能力边界收敛旧管理器、具体源实现与公共运行机制；在保持取数契约的前提下逐步改造。

| 项目 | 内容 |
| --- | --- |
| 文档名称 | `ARCHITECTURE_TARGET_DATA_PROVIDER_REFACTORING.md` |
| 作者 | Codex，依据维护者讨论及仓库代码盘点整理 |
| 创建 / 更新时间 | 2026-11-05（Asia/Shanghai） |
| 版本 / 状态 | v0.3，穷举目标路径与 72 文件去向，细化逐批实施；初步设计，尚未执行代码改造，不是完成验收记录 |
| 盘点基线 | `main` / `3737f14f`；开工时工作区干净，后续实施重新记录 HEAD 与状态 |
| 上位方案 | [ARCHITECTURE_TARGET.md](./ARCHITECTURE_TARGET.md) §2、§4.2–4.3、§9.2.1 |
| 已决约束 | [迁移 ADR-003](../architecture_migration_adr.md)：`data_provider/` 原位保留，应用层通过端口访问 |
| 相关专项 | [服务端大文件拆分](./ARCHITECTURE_TARGET_LARGE_FILE_REFACTORING.md)、[测试迁移台账](./TEST_SUITE_MIGRATION_PROGRESS.md) §12 |
| 当前范围 | 数据源包内部职责、依赖、生命周期与测试；必要时联动基础设施端口适配、bootstrap 和打包 |
| 默认不改 | 前端页面、公开 API、数据库 schema、数据源默认顺序与配置语义；若确需变化，另列契约变更切片 |

## 目录

- [1. 与已完成架构改造的关系](#relationship)
- [2. 现状与问题依据](#baseline)
- [3. 目标边界与设计决定](#boundaries)
- [4. 目标目录与职责归属](#structure)
  - [4.1 改造完成后的预期目录列表](#target-tree)
  - [4.2 一级、二级、三级目录](#directory-levels)
  - [4.3 当前根级文件的收敛方向](#root-files)
  - [4.4 名称评估](#naming)
  - [4.5 成熟项目命名参考](#naming-references)
  - [4.6 本轮命名决定](#naming-decision)
- [5. 双取数体系的收敛方法](#convergence)
- [6. 公共机制与行为护栏](#runtime)
- [7. 分阶段执行计划](#phases)
  - [7.1 执行顺序与批次](#batches)
  - [7.2 包外联动与退出条件](#batch-boundaries)
  - [7.3 方案优化点与开工条件](#design-improvements)
- [8. 测试、客户端及打包验收](#validation)
- [9. 风险、回滚与完成标准](#completion)
- [10. 后续执行者交接要求](#handoff)

<a id="relationship"></a>
## 1. 与已完成架构改造的关系

上一轮完成的是服务端分层和应用端口解耦，并未全面重构 `data_provider/` 内部。保留这个根目录是 ADR-003 的明确决定，不是漏搬；但“原位保留”不等于“不再优化”。本专项延续目标方案 §4.3 的文件内部职责拆分要求，不推翻既有目录决策。

```text
API / Bot → application 用例 → 用例侧端口
                                  ↑ 实现
                       infrastructure/providers
                                  ↓
                      data_provider 的能力入口
                                  ↓
                         具体 Source / SDK / HTTP
```

bootstrap 绑定端口实现并接入资源生命周期。应用端口由实际用例定义；数据源内部的 DataSource / Manager 描述技术取数能力，两者不机械复制整套方法。`infrastructure/providers/` 负责边界转换及必要适配，不再实现第二套选源、重试、缓存和回退。

本专项采用独立分阶段设计。原架构迁移、大文件拆分及测试整理的完成记录仍成立，不将本方案中的候选工作倒写成旧阶段未完成。

<a id="baseline"></a>
## 2. 现状与问题依据

2026-11-05 盘点：`data_provider/` 共 72 个 Python 文件；物理行数包含注释与空行，只作为调查线索。

| 位置 / 机制 | 盘点事实 | 初步处理判断 |
| --- | --- | --- |
| `data_provider/base.py` | 约 3696 行，含 BaseFetcher、DataFetcherManager，涉及日线、实时、基本面、名称、板块、预取、缓存、锁及诊断 | 首要职责盘点对象，逐能力提取，不简单切成多个 mixin |
| `akshare_fetcher.py` | 约 2519 行，覆盖多项能力 | 按调用图评估能力拆分；共享客户端按实际复用保留 |
| `tushare_fetcher.py` | 约 1363 行 | 随能力切片评估，不因文件较大就整包迁移 |
| 九个能力目录 | code_search、fundamentals、institutional、kline、limit_pool、news、realtime、sector、stock_info 已存在 | 沿用，避免新建同义平行结构 |
| `common/` | 已有泛型 Manager、cache、health、rate_limit、normalize | 优先复用，先对账语义再抽公共策略 |
| 两种管理体系 | BaseFetcher / DataFetcherManager 与 DataSource / 各能力 Manager 同时存在 | 先对比契约，再逐能力统一实际实现；不能直接删旧管理器 |
| 包入口 | `__init__.py` 显式导出多个具体 Fetcher | 逐步减少内部对顶层聚合入口的依赖，评估惰性导出与可选依赖隔离 |
| 诊断依赖 | `base.py` 直接导入 `src.application.runtime.run_diagnostics` 的具体记录函数 | 调查诊断上下文传播，通过窄回调/端口解耦，不丢失事件 |
| 架构守卫 | 已限制 application/domain/API/Bot 直接依赖数据源；未设置该包自身专用规则 | 增加针对包内部的依赖检查，先核实已有边，再收紧规则 |

上述是结构事实与候选治理点，不表示已证实数据错算、缓存串扰或线上故障。需先建立契约基线。行数和文件数以后续工作树为准，不据此规定硬阈值。

<a id="boundaries"></a>
## 3. 目标边界与设计决定

| 边界 | 应负责 | 不应承担 |
| --- | --- | --- |
| application | 决定业务所需数据、业务策略及如何消费结果 | 指定具体 SDK、拼接第三方 HTTP 协议 |
| infrastructure/providers | 实现用例端口、转换内部结果、适配调用契约 | 复制数据源 Manager 的回退或缓存逻辑 |
| 能力 Manager / 协作者 | 能力内选源、有效性判断、回退、结果聚合或补全 | 报告生成、交易建议、页面字段展示逻辑 |
| 具体 Source / Fetcher | 上游请求、鉴权、分页、协议解析及源字段标准化 | 决定全局业务降级与配置写入 |
| common | 可复用的缓存、限流、健康记录等机制 | 万能服务容器、强迫所有能力使用相同结果模型 |
| bootstrap / 资源拥有者 | 按当前入口装配、关闭所拥有资源 | 在模块导入时启动任务或提前访问网络 |

确定沿用：根目录保留、按能力组织、复用现有端口与公共机制、不增加平行数据源实现。

实施前需验证：日线与页面 K 线的可复用边界、跨能力缓存/熔断状态的作用域、诊断注入形态、SDK 是否可共享与是否线程安全、最终是否保留 DataFetcherManager 门面。没有证据时保留既有行为，不在初稿中强行定死。

基础设施可以实现应用侧端口，不能把所有 `data_provider → application` 引用一律认定错误。应区分纯契约与具体服务依赖：诊断这类协作可注入窄回调；避免为了注入而另造平行遥测框架。

<a id="structure"></a>
## 4. 目标目录与职责归属

<a id="target-tree"></a>
### 4.1 改造完成后的预期目录与逐路径说明

**本表列出 v0.3 建议目标中的每个目录和 Python 文件，不再使用通配符、省略号或“其他源”占位。**它是规划快照，不是当前磁盘清单；“规划”项须经过对应批次的契约核对，不预先创建空壳。实施如发现两项应合并、外部调用需要保留兼容入口或某项没有真实使用者，先在本节及 §4.3 更新具体路径和理由，再实施，不能自行漏项。

架构上的必要性优先于目录数量：下列目标把确有跨能力调用的厂商请求收敛到客户端，能力 Source 保留标准化与契约；若某个具体客户端抽取没有收益，应改为能力内直接实现，并同步本表。目录树中所有 `__init__.py` 都只负责公开导出，不发请求、不创建线程池、不初始化全部 SDK。

```text
data_provider/  # 一级目录：data_provider 子系统根；继续保留现名与 ADR-003 边界
├── calendar/  # [规划] 财经事件日历数据源；不接管交易日规则
│   ├── __init__.py  # [规划] 财经事件日历公开入口；不接管交易日规则
│   └── wallstreetcn_source.py  # [规划] 迁入国家与财经事件查询、分页、时区和异常；复用旧 Fetcher 的唯一实现
├── chip/  # [规划] 筹码数据；由旧 Manager/Fetcher 提取的已有能力，不是新增业务
│   ├── __init__.py  # [规划] 筹码数据能力入口，补齐上一版目录遗漏的现有能力
│   ├── akshare_source.py  # [规划] 原 AkshareFetcher 的筹码原始数据请求与转换
│   ├── base.py  # [规划] 筹码取数请求、结果与协调；保留空值、回退和熔断行为
│   └── tushare_source.py  # [规划] 原 TushareFetcher 的筹码请求与指标输入标准化；纯业务计算复用 domain
├── clients/  # [规划] 真正跨能力复用的供应商协议客户端，不重复 Source 的能力协调
│   ├── akshare/  # [规划] AkShare 多文件共享协议支撑，须确认复用后建立
│   │   ├── __init__.py  # [规划] akshare 共享客户端的必要公开导出，不提前创建资源
│   │   ├── client.py  # [规划] AkShare 共享调用与接口访问支撑，不把整个原 AkshareFetcher 原样移入
│   │   └── conversions.py  # [规划] AkShare 多能力真正共用的协议字段转换；各能力特有转换留 Source
│   ├── stocksdk/  # [规划] 跨能力 Node 桥接封装，不迁移 Node 工程本身
│   │   ├── __init__.py  # [规划] stocksdk 共享客户端的必要公开导出，不提前创建资源
│   │   └── bridge.py  # [规划] 原 StockSdkBridgeClient、settings、进程及 invoke；保持既有 Node 路径和关闭规则
│   ├── tushare/  # [规划] Tushare SDK/HTTP 双模式共享支撑，须保持认证及切换语义
│   │   ├── __init__.py  # [规划] tushare 共享客户端的必要公开导出，不提前创建资源
│   │   ├── client.py  # [规划] 共享 Tushare SDK 认证、资源与查询入口
│   │   └── http.py  # [规划] 原 _TushareHttpClient 的 HTTP 协议和错误处理，统一与 SDK 模式的选择边界
│   ├── __init__.py  # [规划] 跨能力复用客户端入口；不注册全部供应商、不执行网络请求
│   ├── alphavantage.py  # [规划] alphavantage 跨能力共享的认证、HTTP 调用与源配额；只封装供应商协议，不包含全局选源或回退
│   ├── baostock.py  # [规划] baostock 跨能力共享的登录/登出、查询与并发保护；只封装供应商协议，不包含全局选源或回退
│   ├── efinance.py  # [规划] efinance 跨能力共享的多能力 SDK 调用；只封装供应商协议，不包含全局选源或回退
│   ├── finnhub.py  # [规划] finnhub 跨能力共享的认证与 HTTP 调用；只封装供应商协议，不包含全局选源或回退
│   ├── longbridge.py  # [规划] longbridge 跨能力共享的凭据、连接及关闭；只封装供应商协议，不包含全局选源或回退
│   ├── pytdx.py  # [规划] pytdx 跨能力共享的连接池、并发锁和市场协议；只封装供应商协议，不包含全局选源或回退
│   ├── stockdb.py  # [规划] stockdb 跨能力共享的原 StockDbClient、settings、查询及本地源错误；只封装供应商协议，不包含全局选源或回退
│   ├── tencent.py  # [规划] tencent 跨能力共享的共用腾讯请求与解析底座，不合并不同接口的契约；只封装供应商协议，不包含全局选源或回退
│   ├── tickflow.py  # [规划] tickflow 跨能力共享的现有 SDK/HTTP 请求及批量调用；只封装供应商协议，不包含全局选源或回退
│   └── yfinance.py  # [规划] yfinance 跨能力共享的会话及库调用；只封装供应商协议，不包含全局选源或回退
├── code_search/  # [现有] 代码/名称搜索；沿用现有能力目录
│   ├── __init__.py  # [沿用] 代码/名称搜索包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 代码/名称搜索现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── eastmoney_source.py  # [沿用] 东方财富的代码/名称搜索协议、分页和字段标准化；不承担跨厂商回退
│   ├── local_stockdb_source.py  # [沿用] 本地 StockDB的代码/名称搜索协议、分页和字段标准化；不承担跨厂商回退
│   └── stocksdk_source.py  # [沿用] StockSDK的代码/名称搜索协议、分页和字段标准化；不承担跨厂商回退
├── common/  # [现有] 公共取数机制；沿用现有能力目录
│   ├── __init__.py  # [沿用] 公共取数机制包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 现有 DataSource、DataSourceManager；公共协议、选源与回退机制，保留能力级配置差异
│   ├── cache.py  # [沿用] 共享 TTL 缓存机制；键、实例和失效范围由实际能力指定
│   ├── diagnostics.py  # [规划] 包内窄诊断回调及默认装配契约；不导入具体 application 诊断服务、不静默丢事件
│   ├── errors.py  # [规划] 源不可用、限流、取数失败等既有异常定义的单一事实源；保留旧异常身份
│   ├── fetcher_contract.py  # [规划] 从根 base 提取 BaseFetcher 兼容契约；迁移期保留旧方法，随能力切片逐项退出，不继续扩张万能接口
│   ├── health.py  # [沿用] 健康状态与冷却机制；明确厂商/能力/市场故障域
│   ├── normalize.py  # [沿用] 数据源协议使用的代码格式转换；业务代码规则复用 domain 真源
│   └── rate_limit.py  # [沿用] 限流注册及上下文；不改变既有配额和优先级
├── fundamentals/  # [现有] 基本面；沿用现有能力目录
│   ├── __init__.py  # [沿用] 基本面包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── aggregate.py  # [规划] 多源基本面数据块与预算协调；不生成报告或决策信号
│   ├── akshare_source.py  # [规划] akshare 已有基本面字段获取与源标准化；凭实际覆盖接入 aggregate，不假定所有源提供相同字段
│   ├── base.py  # [沿用] 基本面现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── flow_source.py  # [规划] 从旧适配器提取资金流和龙虎榜原始数据获取；业务评价留 application/domain
│   ├── tushare_source.py  # [沿用] 当前名为 Tushare 的基本面入口实际包装旧 DataFetcherManager 聚合链路；迁移前解开回调旧门面的依赖，保持原配置门控与结果来源语义，不假定它只请求 Tushare
│   └── yfinance_source.py  # [规划] yfinance 已有基本面字段获取与源标准化；凭实际覆盖接入 aggregate，不假定所有源提供相同字段
├── institutional/  # [现有] 机构数据；沿用现有能力目录
│   ├── __init__.py  # [沿用] 机构数据包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 机构数据现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── tw_client.py  # [规划] 迁入台湾机构 HTTP 查询和民国日期解析，tw_source 负责能力结果适配
│   └── tw_source.py  # [沿用] 台湾机构的机构数据协议、分页和字段标准化；不承担跨厂商回退
├── kline/  # [现有] 页面多周期 K 线；沿用现有能力目录
│   ├── __init__.py  # [沿用] 页面多周期 K 线包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 页面多周期 K 线现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── daily_akshare_source.py  # [规划] akshare 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_alphavantage_source.py  # [规划] alphavantage 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_baostock_source.py  # [规划] baostock 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_efinance_source.py  # [规划] efinance 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_finnhub_source.py  # [规划] finnhub 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_history.py  # [规划] 分析日线的优先级、市场路由、完整性与预取协调；保留 DataFrame/来源契约
│   ├── daily_longbridge_source.py  # [规划] longbridge 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_normalize.py  # [规划] 原 BaseFetcher 的日线字段清洗、排序与标准化；技术指标纯规则复用 domain，不能再造指标算法
│   ├── daily_pytdx_source.py  # [规划] pytdx 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tencent_source.py  # [规划] tencent 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tickflow_source.py  # [规划] tickflow 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tushare_source.py  # [规划] tushare 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_yfinance_source.py  # [规划] yfinance 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── eastmoney_source.py  # [沿用] 东方财富的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── local_stockdb_source.py  # [沿用] 本地 StockDB的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── sina_source.py  # [沿用] 新浪的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── stocksdk_source.py  # [沿用] StockSDK的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── tencent_source.py  # [沿用] 腾讯的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退；保持页面周期/复权契约，与分析日线不是直接替换关系
│   └── transform.py  # [沿用] K 线排序、复权、StockDB 行归一、重采样与裁剪；保持单位和边界
├── limit_pool/  # [现有] 涨跌停池；沿用现有能力目录
│   ├── __init__.py  # [沿用] 涨跌停池包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── akshare_source.py  # [规划] 承接 AkshareFetcher 已有涨跌停池获取，保留与 EastMoney 直接源不同的请求及失败语义
│   ├── base.py  # [沿用] 涨跌停池现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── eastmoney_source.py  # [沿用] 东方财富的涨跌停池协议、分页和字段标准化；不承担跨厂商回退
│   └── stocksdk_source.py  # [沿用] StockSDK的涨跌停池协议、分页和字段标准化；不承担跨厂商回退
├── market/  # [规划] 市场快照、指数与统计原始数据；不包括市场分析用例
│   ├── __init__.py  # [规划] 全市场快照、指数与统计的公开取数入口，不包括市场分析用例
│   ├── eastmoney_source.py  # [规划] 东方财富全市场快照、指数与统计的实际取数实现，承接旧快照及 sector 辅助
│   ├── indices.py  # [规划] 按市场查询指数原始数据的能力协调，保留来源优先级
│   ├── snapshot.py  # [规划] 封装全市场快照能力；与现有 MarketSnapshotPort 对账，不能重复其外层回退
│   ├── statistics.py  # [规划] 市场涨跌家数等原始统计协调，不吸收市场策略
│   └── tencent_source.py  # [规划] 腾讯全市场快照取数及标准化，承接旧快照模块
├── news/  # [现有] 新闻；沿用现有能力目录
│   ├── __init__.py  # [沿用] 新闻包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 新闻现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── wallstreetcn_live.py  # [规划] 迁入实时新闻频道目录、URL、scope 和响应解析；news Source 委托此实现
│   └── wallstreetcn_source.py  # [沿用] 华尔街见闻的新闻协议、分页和字段标准化；不承担跨厂商回退
├── realtime/  # [现有] 实时行情；沿用现有能力目录
│   ├── __init__.py  # [沿用] 实时行情包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── akshare_source.py  # [沿用] AkShare的实时行情协议、分页和字段标准化；不承担跨厂商回退
│   ├── alphavantage_source.py  # [规划] alphavantage 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── base.py  # [沿用] 实时行情现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── efinance_source.py  # [规划] efinance 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── enrichment.py  # [规划] 实时行情缺字段补全、来源/新鲜度与失败日志协调，不决定交易策略
│   ├── finnhub_source.py  # [规划] finnhub 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── longbridge_source.py  # [规划] longbridge 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── prefetch.py  # [规划] 批量实时预取及缓存写入，保留原调用预算、并发限制和实例作用域
│   ├── pytdx_source.py  # [规划] pytdx 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── tickflow_source.py  # [沿用] Tickflow的实时行情协议、分页和字段标准化；不承担跨厂商回退
│   ├── tushare_source.py  # [规划] tushare 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── types.py  # [规划] 从 realtime_types 提取行情枚举、UnifiedRealtimeQuote 和标量转换；新旧导出保持类型身份
│   └── yfinance_source.py  # [规划] yfinance 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
├── runtime/  # [规划] 包内实例构造、资源拥有关系与关闭；bootstrap 仍负责进程级接线
│   ├── __init__.py  # [规划] 包内构造与资源管理入口，不依赖 bootstrap
│   ├── fetcher_factory.py  # [规划] 默认源构造及可选依赖探测；保留原加载时机和配置优先级
│   └── resources.py  # [规划] 资源所有权和关闭编排，区分借用/自有客户端，不强制统一为单例
├── sector/  # [现有] 板块榜单；沿用现有能力目录
│   ├── __init__.py  # [沿用] 板块榜单包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── akshare_source.py  # [规划] akshare 的现有板块/概念/热股取数能力；与现有同名方法逐项对账后收敛，不新增产品能力
│   ├── base.py  # [沿用] 板块榜单现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── eastmoney_source.py  # [沿用] 东方财富的板块榜单协议、分页和字段标准化；不承担跨厂商回退；市场统计辅助逐步委托 market 对应实现，禁止保留两份算法
│   ├── efinance_source.py  # [规划] efinance 的现有板块/概念/热股取数能力；与现有同名方法逐项对账后收敛，不新增产品能力
│   ├── market_cards_source.py  # [沿用] 现有行情卡片数据聚合与预热入口；取数协调与应用展示策略按调用方分界，不扩张 UI 职责
│   ├── shidaotec_source.py  # [沿用] 世达科技行业、概念、ETF 与个股树图原始数据及源异常，不迁移页面组件
│   ├── stocksdk_source.py  # [沿用] StockSDK的板块榜单协议、分页和字段标准化；不承担跨厂商回退；现有跨市场辅助接口保留必要导出，共享 clients/stocksdk 桥接
│   ├── tickflow_source.py  # [规划] tickflow 的现有板块/概念/热股取数能力；与现有同名方法逐项对账后收敛，不新增产品能力
│   └── tushare_source.py  # [规划] tushare 的现有板块/概念/热股取数能力；与现有同名方法逐项对账后收敛，不新增产品能力
├── stock_info/  # [现有] 股票信息；沿用现有能力目录
│   ├── __init__.py  # [沿用] 股票信息包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 股票信息现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── catalog.py  # [规划] 股票清单获取与标准化；缓存/代码索引持久化通过现有外层流程，不写入应用数据库
│   ├── eastmoney_source.py  # [沿用] 东方财富的股票信息协议、分页和字段标准化；不承担跨厂商回退
│   ├── local_stockdb_source.py  # [沿用] 本地 StockDB的股票信息协议、分页和字段标准化；不承担跨厂商回退
│   ├── name_lookup.py  # [规划] 单个/批量名称回退及缓存协调；不将搜索和精确查询混为一体
│   ├── stocksdk_source.py  # [沿用] StockSDK的股票信息协议、分页和字段标准化；不承担跨厂商回退
│   └── tencent_source.py  # [沿用] 腾讯的股票信息协议、分页和字段标准化；不承担跨厂商回退
├── __init__.py  # [沿用] 数据源子系统精简入口；兼容导出必须绑定同一对象，禁止 eager 导入全部 SDK
├── base.py  # [沿用] 保留 DataFetcherManager 旧调用门面；能力实现委托新协作者，BaseFetcher 如需兼容则再导出公共契约；不保留业务实现副本
└── us_index_mapping.py  # [沿用] 保留已有指数映射兼容入口，复用 domain 真源；不是重新复制一份映射
```

本规划共 **124 个 Python 文件、18 个下级目录**；数量仅用于文档对账，不是要求增加代码或文件的验收指标。当前 72 个源文件的去向均在 §4.3 登记，新增文件不表示新增业务能力。

分析日线使用 `kline/daily_<vendor>_source.py` 命名，现有页面多周期接口仍使用 `<vendor>_source.py`；两者请求和结果不同，可以分别存在，但相同 HTTP/SDK 请求与转换必须复用，不得复制算法。是否能进一步合并由 DP2 对账决定，不要求所有厂商都补齐两种接口。

名称查询和股票清单通过 stock_info 协作者调用共享客户端，不再创建一套完整的同厂商 Source；只复用已有供应能力。旧 BaseFetcher 中技术指标计算须核对既有 domain 真源，若确实需要提取新业务模块，作为包外联动路径登记，不塞入客户端。

<a id="directory-levels"></a>
### 4.2 一级、二级、三级目录分别是什么

统一以 `HermesX/` 为根：`data_provider/` 为一级，能力及支撑目录为二级，`clients/<vendor>/` 为按需三级。文件不是下一层目录；按包根计数时层级应减一，本文不混用口径。

| 一级 | 二级完整路径 | 三级完整路径 | 职责 |
| --- | --- | --- | --- |
| `data_provider/` | `data_provider/calendar/` | 无，不强制细分 | 财经事件日历数据源；不接管交易日规则 |
| `data_provider/` | `data_provider/chip/` | 无，不强制细分 | 筹码数据；由旧 Manager/Fetcher 提取的已有能力，不是新增业务 |
| `data_provider/` | `data_provider/clients/` | `data_provider/clients/akshare/`、`data_provider/clients/stocksdk/`、`data_provider/clients/tushare/` | 真正跨能力复用的供应商协议客户端，不重复 Source 的能力协调 |
| `data_provider/` | `data_provider/code_search/` | 无，不强制细分 | 代码/名称搜索；沿用现有能力目录 |
| `data_provider/` | `data_provider/common/` | 无，不强制细分 | 公共取数机制；沿用现有能力目录 |
| `data_provider/` | `data_provider/fundamentals/` | 无，不强制细分 | 基本面；沿用现有能力目录 |
| `data_provider/` | `data_provider/institutional/` | 无，不强制细分 | 机构数据；沿用现有能力目录 |
| `data_provider/` | `data_provider/kline/` | 无，不强制细分 | 页面多周期 K 线；沿用现有能力目录 |
| `data_provider/` | `data_provider/limit_pool/` | 无，不强制细分 | 涨跌停池；沿用现有能力目录 |
| `data_provider/` | `data_provider/market/` | 无，不强制细分 | 市场快照、指数与统计原始数据；不包括市场分析用例 |
| `data_provider/` | `data_provider/news/` | 无，不强制细分 | 新闻；沿用现有能力目录 |
| `data_provider/` | `data_provider/realtime/` | 无，不强制细分 | 实时行情；沿用现有能力目录 |
| `data_provider/` | `data_provider/runtime/` | 无，不强制细分 | 包内实例构造、资源拥有关系与关闭；bootstrap 仍负责进程级接线 |
| `data_provider/` | `data_provider/sector/` | 无，不强制细分 | 板块榜单；沿用现有能力目录 |
| `data_provider/` | `data_provider/stock_info/` | 无，不强制细分 | 股票信息；沿用现有能力目录 |

只有 clients 下的三组共享协议需要规划三级包。其余能力保持“目录 + 有职责的文件”；不在每个能力下复制 models/services/utils 套路。

<a id="root-files"></a>
### 4.3 当前 72 个 Python 文件的完整去向表

本表覆盖盘点时每个文件一次。“保留/内部收敛”表示路径不变但可能调整实现。“拆分/迁移”不意味着可以直接删除旧文件：调用方、测试 patch、动态导入、冻结包和公开类型均迁完，才移除旧入口。兼容期只导出同一实现，不长期保留两套加载和状态。

| 当前完整路径 | 预期目标路径（相对 data_provider/） | 决定与职责保护 |
| --- | --- | --- |
| `data_provider/__init__.py` | `__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/akshare_fetcher.py` | `kline/daily_akshare_source.py`、`realtime/akshare_source.py`、`fundamentals/akshare_source.py`、`sector/akshare_source.py`、`chip/akshare_source.py`、`clients/akshare/client.py`、`market/indices.py`、`market/statistics.py`、`limit_pool/akshare_source.py`、`clients/akshare/conversions.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/alphavantage_fetcher.py` | `kline/daily_alphavantage_source.py`、`realtime/alphavantage_source.py`、`clients/alphavantage.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/baostock_fetcher.py` | `kline/daily_baostock_source.py`、`clients/baostock.py`、`stock_info/catalog.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/base.py` | `base.py`、`common/errors.py`、`common/fetcher_contract.py`、`common/diagnostics.py`、`kline/daily_history.py`、`kline/daily_normalize.py`、`realtime/enrichment.py`、`realtime/prefetch.py`、`stock_info/name_lookup.py`、`stock_info/catalog.py`、`fundamentals/aggregate.py`、`fundamentals/flow_source.py`、`market/indices.py`、`market/statistics.py`、`chip/base.py`、`runtime/fetcher_factory.py`、`runtime/resources.py` | 按能力拆分，门面仍保留；不能把整个宿主对象传给协作者形成隐式耦合 |
| `data_provider/code_search/__init__.py` | `code_search/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/code_search/base.py` | `code_search/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/code_search/eastmoney_source.py` | `code_search/eastmoney_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/code_search/local_stockdb_source.py` | `code_search/local_stockdb_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/code_search/stocksdk_source.py` | `code_search/stocksdk_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/common/__init__.py` | `common/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/common/base.py` | `common/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/common/cache.py` | `common/cache.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/common/health.py` | `common/health.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/common/normalize.py` | `common/normalize.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/common/rate_limit.py` | `common/rate_limit.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/eastmoney_quote_snapshot.py` | `market/eastmoney_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/efinance_fetcher.py` | `kline/daily_efinance_source.py`、`realtime/efinance_source.py`、`sector/efinance_source.py`、`clients/efinance.py`、`market/indices.py`、`market/statistics.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/finnhub_fetcher.py` | `kline/daily_finnhub_source.py`、`realtime/finnhub_source.py`、`clients/finnhub.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/fundamental_adapter.py` | `fundamentals/akshare_source.py`、`fundamentals/flow_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/fundamentals/__init__.py` | `fundamentals/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/fundamentals/base.py` | `fundamentals/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/fundamentals/tushare_source.py` | `fundamentals/tushare_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/institutional/__init__.py` | `institutional/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/institutional/base.py` | `institutional/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/institutional/tw_source.py` | `institutional/tw_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/__init__.py` | `kline/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/base.py` | `kline/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/eastmoney_source.py` | `kline/eastmoney_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/local_stockdb_source.py` | `kline/local_stockdb_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/sina_source.py` | `kline/sina_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/stocksdk_source.py` | `kline/stocksdk_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/tencent_source.py` | `kline/tencent_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/kline/transform.py` | `kline/transform.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/limit_pool/__init__.py` | `limit_pool/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/limit_pool/base.py` | `limit_pool/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/limit_pool/eastmoney_source.py` | `limit_pool/eastmoney_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/limit_pool/stocksdk_source.py` | `limit_pool/stocksdk_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/longbridge_fetcher.py` | `kline/daily_longbridge_source.py`、`realtime/longbridge_source.py`、`clients/longbridge.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/news/__init__.py` | `news/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/news/base.py` | `news/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/news/wallstreetcn_source.py` | `news/wallstreetcn_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/pytdx_fetcher.py` | `kline/daily_pytdx_source.py`、`realtime/pytdx_source.py`、`clients/pytdx.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/realtime/__init__.py` | `realtime/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/realtime/akshare_source.py` | `realtime/akshare_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/realtime/base.py` | `realtime/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/realtime/tickflow_source.py` | `realtime/tickflow_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/realtime_types.py` | `realtime/types.py`、`common/health.py` | 拆分类型与熔断；保留枚举/异常/类身份，核对全局 breaker 实例作用域 |
| `data_provider/sector/__init__.py` | `sector/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/sector/base.py` | `sector/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/sector/eastmoney_source.py` | `sector/eastmoney_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/sector/market_cards_source.py` | `sector/market_cards_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/sector/shidaotec_source.py` | `sector/shidaotec_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/sector/stocksdk_source.py` | `sector/stocksdk_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/stock_info/__init__.py` | `stock_info/__init__.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/stock_info/base.py` | `stock_info/base.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/stock_info/eastmoney_source.py` | `stock_info/eastmoney_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/stock_info/local_stockdb_source.py` | `stock_info/local_stockdb_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/stock_info/stocksdk_source.py` | `stock_info/stocksdk_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/stock_info/tencent_source.py` | `stock_info/tencent_source.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/stockdb_fetcher.py` | `clients/stockdb.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/stocksdk_bridge.py` | `clients/stocksdk/bridge.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tencent_fetcher.py` | `kline/daily_tencent_source.py`、`clients/tencent.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tencent_quote_snapshot.py` | `market/tencent_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tickflow_fetcher.py` | `kline/daily_tickflow_source.py`、`realtime/tickflow_source.py`、`sector/tickflow_source.py`、`clients/tickflow.py`、`stock_info/catalog.py`、`stock_info/name_lookup.py`、`market/indices.py`、`market/statistics.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tushare_fetcher.py` | `kline/daily_tushare_source.py`、`realtime/tushare_source.py`、`fundamentals/tushare_source.py`、`sector/tushare_source.py`、`chip/tushare_source.py`、`clients/tushare/client.py`、`clients/tushare/http.py`、`stock_info/catalog.py`、`stock_info/name_lookup.py`、`market/indices.py`、`market/statistics.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tw_institutional_fetcher.py` | `institutional/tw_client.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/us_index_mapping.py` | `us_index_mapping.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/wallstreetcn_calendar_fetcher.py` | `calendar/wallstreetcn_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/wallstreetcn_live_news_fetcher.py` | `news/wallstreetcn_live.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/yfinance_fetcher.py` | `kline/daily_yfinance_source.py`、`realtime/yfinance_source.py`、`fundamentals/yfinance_source.py`、`clients/yfinance.py`、`market/indices.py`、`market/statistics.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/yfinance_fundamental_adapter.py` | `fundamentals/yfinance_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |

表中“market/indices.py、statistics.py”负责协调；供应商实际请求在对应共享客户端或 market 具体源。资金流、龙虎榜和板块业务上下文的策略组装不留在数据源：优先复用 `src/application/analysis/`、`src/application/market/` 与现有领域规则，DP0 必须登记实际消费方与具体改动文件，不以通用上下文服务代替职责划分。

旧 AkShare 涨跌停能力与当前 EastMoney 能力源不是直接等价；映射到现有能力的前提是保留请求、结果与源优先级，本规划已单列 `limit_pool/akshare_source.py`，不得强行切换为 EastMoney 直接接口。旧 Fast/增强接口逐项审计，不得因树中没有同名方法就删功能。上述是必须在 DP0 锁定的条件，不是行为变更许可。

<a id="naming"></a>
### 4.4 名称评估：data_provider 是否合适

**合适。它不是错误命名，也不存在行业统一要求必须改成另一名称。**根包表示“数据提供这一子系统”时，单数可以成立；多种源的集合采用复数也能清晰表达，但加一个 s 本身不改善职责边界。

| 名称 | 语义与适用场景 | 对 HermesX 的建议 |
| --- | --- | --- |
| `data_provider` | 数据供给子系统，现有导入和 ADR 使用此名 | **本轮保留**，工程上可接受 |
| `data_providers` | 明确表达多个提供方的集合 | 可选，但当前包还包含能力协调和公共机制，不只是厂商集合；仅单复数变化收益有限 |
| `data_sources` | 外部数据源接入与取数能力集合 | **若未来专门改名，优先评估此名**；覆盖行情、基本面、新闻、日历与机构数据，语义直观 |
| `market_data` | 以市场数据这一领域能力为中心 | 适合更完整的市场数据子系统；需明确新闻/财经日历等边界，不能顺势吞并业务分析和持久化 |
| `connectors` / `data_connectors` | 对接外部系统的连接、鉴权与协议适配 | 更适合具体客户端/源接入层，不能完整表达本包的选源与能力协调职责 |
| `feeds` / `data_feeds` | 行情或数据馈送，容易使读者预期流式订阅 | 当前含大量请求式历史查询与基本面聚合，不作为本项目首选 |
| `adapters` / `integrations` | 泛化外部适配或集成 | 需要父级上下文；根目录单独使用容易与通知、生成、经纪商等其他集成混淆 |

以上适配建议是结合本项目职责作出的工程判断，不是外部项目规定。`market_data` 的语义也并非只能包含价格，最终是否采用取决于团队对领域边界的定义。

<a id="naming-references"></a>
### 4.5 成熟项目的公开命名参考

资料核对时间：2026-11-05。以下只证明相应术语的真实使用，不证明其目录结构可以直接照搬，也不构成项目质量排名。

| 项目 | 官方使用方式 | 对本项目的启示 |
| --- | --- | --- |
| Apache Airflow | 用 providers 表达扩展核心并集成外部系统的可安装包，涵盖 hooks、operators 等。见 [官方 Providers 文档](https://airflow.apache.org/docs/apache-airflow-providers/) | Provider 是成熟的工程术语，但 Airflow 的扩展包比本项目数据源范围更广 |
| Airbyte | 通过 connectors 连接 sources 与 destinations。见 [官方仓库：Sources, Destinations, and Connectors](https://github.com/airbytehq/airbyte/blob/master/docs/platform/move-data/sources-destinations-connectors.md) | Connector 强调接入组件；source 表达输入来源，不能据此把能力协调都命名为 connector |
| QuantConnect / LEAN | 官方量化交易文档使用 Data Providers，描述为实盘算法供给数据的提供方。见 [官方 Data Providers 文档](https://www.quantconnect.com/docs/v2/lean-cli/live-trading/data-providers) | 金融工程中使用 provider 合理；不意味着 Python 根包必须使用复数或复制其框架组织 |

这些案例共同说明不同工程按边界选择词汇。对 HermesX，清晰区分“业务能力、具体数据源、底层客户端”比追求某一个行业名称更重要。

<a id="naming-decision"></a>
### 4.6 本轮命名决定与未来改名边界

- **本轮执行名称仍为 `data_provider/`**。此处是命名评估，不是改名授权，不推翻 ADR-003；目录树、步骤和验收均以现名为准。
- 如果维护者选择未来改为 `data_sources/`，在仓库根目录原位改名即可；“改名”与“搬入 src/infrastructure”是两项独立决策，不能绑定执行。
- 改名前单列切片，盘点绝对/相对导入、动态导入字符串、测试 patch、脚本、Docker、PyInstaller hidden imports、资源路径、守卫规则及文档；同步 ADR，并验证源码运行与冻结后实际导入。
- 优先原子更新仓内消费者；若确有外部依赖需短期兼容，应规定范围和移除条件，不能长期维护两套实现或以两个包名重复加载产生两套注册与状态。
- 本初稿不创建 `data_sources/` 别名目录、不新增兼容包，也不以更名作为内部职责改造的验收前提。

<a id="convergence"></a>
## 5. 双取数体系的收敛方法

先建立“调用场景 → 用例端口 → 现有适配器 → Manager → 具体源”的链路清单，再按能力决策。

| 能力 | 旧链路 / 新入口 | 迁移前必须核对 |
| --- | --- | --- |
| 日线 / K 线 | DataFetcherManager.get_daily_data / kline 的 KLineRequest、KLineResult | DataFrame 与行结果、日期边界、复权、完整性、交易日、市场路由、技术指标、分页与来源标识 |
| 实时行情 | DataFetcherManager.get_realtime_quote / realtime 能力入口 | 各市场优先级、缺字段补全、时间戳、行情新鲜度、批量预取与日志 |
| 基本面 | DataFetcherManager.get_fundamental_context / fundamentals 能力入口 | 覆盖的提供方、预算截止时间、局部失败、字段完整度和业务上下文组装 |
| 名称 / 股票信息 | get_stock_name、批量名称 / stock_info、code_search | 搜索与精确查询区别、名称缓存、跨市场归一化、避免为查名称引入额外实时请求 |
| 板块 / 市场辅助能力 | 旧 Manager 对应方法 / sector 等入口 | 指数、概念、排行榜并非同一能力；按真实场景复用，不全部硬映射到 sector |

每项只能选择经验证的收敛路径：复用现有能力实现；提取共同底层源并保留不同协调策略；或因契约差异暂时保留两种入口。目标是消除重复实现和状态，不要求所有场景只剩一个 Manager 类。

日线和页面 K 线不能简单互换。比如腾讯分析日线已有短历史完整性用例，原 799/800 条边界及日期规则必须保留，不能为了接入新 Manager 放宽原断言。基本面的新入口当前源覆盖也不能被假定等于旧聚合能力。

<a id="runtime"></a>
## 6. 公共机制与行为护栏

| 机制 | 设计要求与迁移约束 |
| --- | --- |
| 选源 / 回退 | 逐能力记录默认顺序、显式指定、禁用回退、不可用源及全失败行为；先保持，再单独讨论策略调整 |
| 超时 / 重试 | 盘点 HTTP、SDK、Manager 的嵌套重试；控制整体调用预算。不能仅缩短外层等待却任由后台请求无限运行 |
| 缓存 | 列明市场、代码、周期、复权、日期范围及必要配置维度；核对 TTL、容量、返回值可变性和失效行为，不统一改为全局缓存 |
| 健康 / 熔断 | 先定义按厂商、能力还是市场隔离的故障域，再决定状态键；一个能力失败不应无依据地熔断该厂商全部能力 |
| 并发 / 资源 | 保留必要串行锁与并发限制；明确会话、SDK、线程池由谁创建、共享和关闭；调用者不能关闭借用资源 |
| 生命周期 | 能力包现有模块级 Manager 与分析流水线的实例 Manager 不直接统一成单例；避免导入期初始化网络连接或后台任务 |
| 错误 / 空数据 | 区分合法无数据、不支持、源故障与数据无效；对外沿用既有空值/异常契约，不能新增 broad fallback 掩盖错误 |
| 结果契约 | 核对单位、时区、代码、复权、排序、重复行、来源和新鲜度；无需新增全仓万能 DTO，HTTP schema 留在 API |
| 诊断 | 保持开始/成功/失败、来源与耗时关联；验证跨线程上下文；断开具体服务耦合时不丢失诊断 |
| 测试替身 | 局部替换实际消费引用，避免修改全进程 requests.get；沿用腾讯隔离回归，不把包内 Session 全局重写作为测试捷径 |

以上护栏不自动构成新配置项。优先使用既有配置；确需新键时，单独说明默认值和兼容影响，同步 `.env.example` 与专题文档。

<a id="phases"></a>
## 7. 分阶段执行计划

<a id="batches"></a>
### 7.1 执行顺序与批次原则

以下是本方案的执行清单，不是本次已经实施的改动。按 B00 → B23 的顺序推进；允许证据充分后合并相邻低风险批次，但必须逐项保留验收记录。涉及多个厂商的批次内部再按表中顺序“一厂商一切片”执行，不能一次替换全部供应方。

每个代码批次均须先读取该批公开入口和调用方，记录改造前结果；同批完成实现、消费者、装配、测试 patch 及必要打包引用。新模块应承接实际职责，不先批量创建空文件。若前置门禁失败，停在该批定位或回滚，不继续堆叠后续批次。

| 顺序 / 对应阶段 | 前置 | 本批具体工作与路径范围 | 本批必须取得的验证 | 回滚边界 |
| --- | --- | --- | --- | --- |
| B00 / DP0 | 无 | 核对 §4.1 目标清单与 §4.3 的 72 文件去向；登记每个公开类/函数的消费者、动态导入、测试 patch、配置与冻结引用 | 源文件数量和去向逐条对账；新路径无碰撞；已有修改不被覆盖 | 仅回退本批文档条目 |
| B01 / DP0 | B00 | 日线/页面 K 线/实时/名称/基本面/筹码/市场/新闻/日历/机构分别建立契约矩阵；登记 DataFrame/DTO、来源、空数据、错误和资源作用域 | 获取当前离线相关测试与收集基线；记录既有失败，不用旧的 5726 等数量代替实测 | 撤回新增特征测试时保留原用例和基线日志 |
| B02 / DP1 | B01 | 从根 base 提取 common/errors.py、fetcher_contract.py；旧入口再导出同一异常/契约对象；不同时改回退逻辑 | 异常和类型身份、继承、导入、旧调用路径验证；不新增循环导入 | 定义与全部再导出原子恢复 |
| B03 / DP1 | B02 | common/diagnostics.py 定义最小事件协作；现有 infrastructure 适配与 bootstrap 接入旧诊断记录函数，移除数据源对具体应用服务的耦合 | 开始/结束/来源/耗时/失败字段及跨线程关联；未装配行为明确，不能吞事件 | 回调注入、装配、测试与旧记录调用同时恢复 |
| B04 / DP1 | B02 | 仅提取 runtime/fetcher_factory.py、resources.py 的构造和关闭职责；SDK 仍在原时机创建，不提前把所有对象改为单例 | 实例数量、默认源顺序、可选依赖缺失、重复关闭、借用资源不被误关 | 工厂与资源所有权一起恢复，不改变运行配置 |
| B05 / DP1 | B01、B04 | 专门对账 fundamentals/tushare_source.py → DataFetcherManager 的真实聚合依赖，设计 aggregate 的底层单向调用；锁定配置门控和 payload/source 语义 | 构造及调用不递归、初始化不引入循环导入；旧入口与新入口对照结果一致 | 聚合入口、门面和 source 同批恢复，禁止只改一端 |
| B06 / DP2 | B02–B05 | 腾讯日线试点：kline/daily_history.py、daily_normalize.py、daily_tencent_source.py；已有 kline/tencent_source.py 不直接替换；共享协议只在真正等价处抽入 clients/tencent.py | 原 799/800 条、上市短历史、日期边界、复权、超时、全源失败和 source 标识；腾讯并发 HTTP 隔离回归保留 | 腾讯相关唯一实现、旧导出与消费者成组回退 |
| B07 / DP2 | B06 | 按 Efinance → AkShare → Tushare 分切片迁分析日线；随实际共享调用提取各 clients；先保留其他能力原实现，不让客户端回调旧门面 | 各市场源顺序、原字段/单位/指标输入、旧接口与新接口数据对照；SDK/HTTP 模式和凭据探测 | 按厂商独立回退；已被其他能力消费的客户端需一起核查 |
| B08 / DP2 | B07 | 按 Yfinance → Baostock → Pytdx → Longbridge → Finnhub → AlphaVantage → Tickflow 分切片处理其余日线源；与 StockDB 页面源保持契约区分 | 港/美/日/韩/台等现有覆盖、指数与 ETF、限流、SDK 缺失、批量预取、线程安全与关闭 | 一厂商一切片回退，不改全局优先级掩盖失败 |
| B09 / DP3 | B04、B08 | realtime/types.py 与 common/health.py 收敛原 realtime_types；先保持 breaker 对象、计数器和故障域 | 枚举/DTO 身份、类型再导出、并发与测试重置；不将实时和筹码故障状态误合并 | 类型/熔断实例/所有导出共同回退 |
| B10 / DP3 | B09 | realtime/enrichment.py、prefetch.py；逐个迁入实时 Source：AkShare/Tickflow 现有入口先对账，再处理 Efinance、Tushare、Pytdx、Longbridge、Finnhub、AlphaVantage、Yfinance | 缺字段补全、新鲜度、全失败日志、港股裸码、市场路由、预取、缓存和并发；不新增原不支持的能力 | 每个实时供应方及补全策略可独立回退；不影响已通过的日线 |
| B11 / DP3 | B05、B10 | fundamentals/aggregate.py、flow_source.py 与 AkShare/Yfinance 实际源；解开名为 Tushare 的旧包装，按真实职责收敛；不为 Finnhub/AlphaVantage 虚构基本面能力 | 预算截止、局部失败、资金流、龙虎榜、not_supported/partial、配置门控和来源标签不变；两入口不循环调用 | aggregate、适配器、旧门面及 source 原子恢复 |
| B12 / DP3 | B08、B11 | stock_info/name_lookup.py、catalog.py；承接各厂商已存在的名称及清单能力，保持 code_search 独立 | 单个/批量名称、缓存隔离、精确查询与模糊搜索、代码规范化；不额外触发实时网络请求 | 名称/清单入口与相关客户端方法一起恢复 |
| B13 / DP3 | B08、B12 | market/snapshot.py、indices.py、statistics.py、eastmoney_source.py、tencent_source.py；与 sector 当前市场辅助函数及现有外层端口逐项收敛 | 市场指数/统计/快照、原回退顺序、共享缓存、字段和来源；不得两个层各重试一次 | 旧快照/sector 辅助入口与新实现同时恢复 |
| B14 / DP3 | B13 | sector 的 AkShare/Efinance/Tushare/Tickflow 能力与现有 EastMoney/StockSDK/Shidaotec/market_cards 对账；limit_pool 单列 akshare_source，不强换成 EastMoney 直接请求 | 行业/概念/热股/所属板块、榜单、涨跌停与市场卡片，原可用源/字段/热身调度保持 | 按能力恢复，共享市场方法只保留一份真源 |
| B15 / DP3 | B09、B11、B14 | chip/base.py、akshare_source.py、tushare_source.py；纯规则检查 domain 真源，源归一与数据获取留在本包 | 筹码有效性、原计算输入与结果、空数据、熔断和失败回退；不能仅比较是否返回字典 | 源、指标规则引用和旧 Manager 方法成组恢复 |
| B16 / DP3 | B04 | calendar/wallstreetcn_source.py；将旧日历 Fetcher 的唯一实现迁入能力目录，暂不扩大公共 Manager 抽象 | 国家、时间范围、分页、时区、字段与错误；不影响交易日历 domain | 日历公开类型/异常/消费者原子恢复 |
| B17 / DP3 | B04 | news/wallstreetcn_live.py 与现有 wallstreetcn_source 的调用收敛；只迁现有代码，不改变新闻抓取安全边界 | 频道、URL、scope、时间解析和源错误；API/应用新闻链路相关安全用例保持 | 新闻客户端、Source、旧异常及调用方一起恢复 |
| B18 / DP3 | B04 | institutional/tw_client.py；tw_source 委托新客户端，避免构造器懒加载 mock 被永久绑定 | 民国日期、台湾代码、买卖超单位与合法空结果；独立运行和随机顺序 | 客户端、懒加载位置、Source 与测试 patch 一起恢复 |
| B19 / DP4 | B08–B18 | 整理 clients/stockdb.py 和 clients/stocksdk/bridge.py 的共享调用；按实际已迁能力去掉旧厂商文件的残余具体实现，检查厂商 client 没有再次成为万能 Fetcher | StockDB 复权、分钟线、搜索/板块；Node bridge 参数、路径、并发、超时和进程退出；不复制取数算法 | 客户端及所有消费能力共同核查，不能只退一个共享文件 |
| B20 / DP4 | B19 | 公共重试/缓存/限流/健康策略审计；只合并已证明等价的机制；梳理增强数据/业务上下文的真实应用消费方 | 总预算、缓存键及可变返回值、冷却与配额、并发上限、业务上下文契约对照 | 共享策略及全部使用者整体回退；不顺手改默认策略 |
| B21 / DP5 | B20 | 收敛根 __init__、base 门面和 us_index_mapping；按 §4.3 逐项核对旧入口是否仍需兼容，迁完才删除旧具体 Fetcher 文件 | 静态/动态导入、异常/类身份、公开方法清单守恒；源码及冻结包均导入成功，无双份注册 | 旧入口/新导出/hidden imports/测试 patch 原子回退 |
| B22 / DP5 | B21 | scripts/check_architecture.py 添加 data_provider 专用规则：禁 API/Bot/bootstrap 与未登记具体应用实现；端口引用按现有架构允许，不能一刀切 | 合成反例能被阻断；当前源码规则通过；不靠新 baseline 豁免隐藏违规 | 规则和对应自测一同恢复，不删除已有外层守卫 |
| B23 / DP6 | B22 | 全量门禁、固定序/明确种子、相关接口消费、Web 构建、干净后端导入与打包、Docker/平台可行验收；更新总览、流水及台账 | 计数变化有解释；SDK/资源在冻结可执行文件实际导入；未验证和外部授权/网络阻塞逐项登记 | 按完整能力切片回退；共享资源和类型不能局部撤回，用户数据保持 |

这 24 个编号是可追踪工作包，不是 24 次提交或 24 个工作日。B07/B08/B10 内部的厂商子片分别验收后才推进；如果某批发现契约不同，应更新矩阵和路径，不强行统一。部分独立能力在依赖满足后可穿插，但不在共享客户端/状态所有者尚未明确时并行修改同一文件。

<a id="batch-boundaries"></a>
### 7.2 包外联动路径与每批退出条件

本节穷举本次计划的包内目标；包外只改实际受影响的既有入口，不承诺“仅改 data_provider”。DP0 必须把运行时动态消费方补到具体文件，不能仅搜索 import。

| 包外路径 | 何时需要联动 | 验收要求 |
| --- | --- | --- |
| `src/infrastructure/providers/analysis_stock_data_provider.py` | 旧分析 Manager 方法被委托或替换时 | StockDataPort 参数、结果、可选能力和实例作用域保持 |
| `src/infrastructure/providers/kline_provider.py` | 页面 K 线/代码搜索/股票信息能力入口调整时 | 字段整形、异常传播与 API Schema 不变 |
| `src/bootstrap/analysis.py`、`src/bootstrap/quote.py` | 工厂、诊断或资源生命周期接线变化时 | CLI/API/测试三入口均装配，不增加隐藏初始化 |
| `src/bootstrap/api_lifecycle.py`、`main.py`、`tests/conftest.py` | 新资源需要明确启停或原装配引用变化时 | 真实生命周期、关闭与测试独立性；不在全局 conftest 掩盖缺失装配 |
| `src/application/analysis/context_enrichment.py`、`src/application/analysis/analysis_context_builder.py`、`src/application/market/daily_market_context.py` | 盘点确认有业务上下文职责需归还应用层时 | 先锁定实际消费者和输入/输出；无需要则不修改 |
| `scripts/build-backend-macos.sh`、`scripts/build-backend.ps1`、`docker/Dockerfile` | 路径变化影响导入/资源收集时；实际 Docker 文件名实施前复核 | 保持默认构建路径，源码 import 与冻结后实际 import 都验收 |
| `tests/infrastructure/providers/` 及真实 API/application 消费方测试 | 每个能力切片 | 真实风险层不被 mock 绕过；不删断言、不加跳过维持绿灯 |

每批退出前需逐项核对：文件去向与公开方法；类型/异常身份；源和市场覆盖；优先级及全失败；缓存/锁/熔断所有者；资源关闭；装配和 patch；打包引用；验证结果与缺口；回滚。任一项未知时登记阻塞并缩小切片，不给整批写“完成”。

<a id="design-improvements"></a>
### 7.3 本次设计的优化点及开工条件

相比 v0.2：补齐筹码等已有能力；撤下无源码依据的 Finnhub/AlphaVantage 基本面候选；区分分析日线与页面 K 线；单列 Tushare 名称包装旧聚合链的依赖解环；穷举文件去向与资源所有权；将大阶段拆为可验证工作包。

代码实施从 B00 开始。本次只完善方案，所有批次状态均为“未开始”，不能把本次 AST 盘点、目录生成或文档校验当作任何批次的代码验收。DP0 如有进一步调整，在原文和流水记录具体变化，不另建同义方案。

<a id="validation"></a>
## 8. 测试、客户端及打包验收

测试沿用现有目录，不另建平行测试体系：

- `tests/infrastructure/providers/` 下的 routing、kline、realtime、fundamentals、cache、common 等分组覆盖源能力与共享机制。
- `tests/application/`、API 与 integration 中的消费方测试验证分析、行情和配置契约；仅移动 patch 时检查真实消费位置，不删断言换取通过。
- 针对源失败、空数据、超时、回退禁用、缓存隔离、并发、关闭及可选依赖缺失补充必要回归。真实协议与关键转换不能全部 mock 掉。
- 涉及共享状态的切片独立进程运行，再固定顺序及明确随机种子复核；记录收集数量变化的理由，不要求数量永远固定。

主要检查入口（使用项目已安装依赖的环境）：

```bash
python scripts/check_architecture.py --check
python -m pytest tests/infrastructure/providers -m "not network" -p no:randomly
python -m pytest tests/infrastructure/providers -m "not network" --randomly-seed=20261105
./scripts/ci_gate.sh all
```

执行前确认命令与当时 CI 插件安装情况。全门禁通过只覆盖本次运行条件；在线调用应单独进行，不把真实网络请求混入离线验收。

| 联动面 | 默认范围与触发条件 |
| --- | --- |
| Web | 仅内部职责提取且 API 不变时无需改页面；仍验证受影响接口与构建。字段、枚举、错误或数据新鲜度语义改变时同切片更新客户端 |
| Desktop | 内部包路径或 SDK 导入变化时检查 PyInstaller hidden imports、资源收集及冻结后实际导入；生命周期变化时补启动/关闭验证 |
| Docker / CI | 导入与依赖变化需补镜像模块导入、构建及启动检查，不能仅凭开发环境 import 通过认定打包成功 |
| 配置 / DB | 默认不改 schema、默认顺序与配置键；确有必要时另列变更及迁移/兼容计划 |

前端全量 lint 按维护者既有安排暂缓；如果具体切片必须改前端，再明确该切片的验证范围。Docker Pro 授权、干净安装网络和桌面启动等已有阻塞独立登记，不在本专项通过删除依赖、改 UI 或停止本机服务来绕过。

<a id="completion"></a>
## 9. 风险、回滚与完成标准

主要风险是取数语义被无意统一、市场路由改变、缓存/熔断扩大作用域、共享资源被提前关闭，以及打包漏收新模块。行数下降不能证明这些风险消除。

完成标准：

1. 逐能力具有公开入口、实际调用方、选源及状态所有者的明确记录。
2. base 不再承载不相关能力的具体实现；是否保留兼容门面有调用方及打包依据。
3. 新旧入口若同时保留，复用同一行为实现或有明确的契约差异；无两套并行复制代码。
4. application 继续只依赖端口；数据源包不直接依赖 API/Bot 或 bootstrap，具体诊断服务依赖已收敛或明确登记。
5. 相关测试、门禁与可执行打包检查有结果，未验证项如实标记；不使用新增 skip、静默空结果或放宽断言关闭失败。
6. 文档与实际落点一致，实施进度按片记录；不以所有文件小于某行数为验收目标。

按能力原子回滚：同时恢复旧实现、调用方、装配、测试 patch 与打包配置，撤回对应新实现，避免双份类型/注册/取数。共享机制的回滚须核对已经迁移的全部使用者，不只撤回最初提取片。用户配置、数据库、日志及本地运行资产不属于代码回滚删除范围。

<a id="handoff"></a>
## 10. 后续执行者交接要求

先读 AGENTS.md、上位目标、ADR-003、本方案及当前源码。以实施时 HEAD 和工作区为准，不把本文盘点当成永久事实；不得从旧架构 P0 重做全部迁移。

每个切片在现有 [架构实施流水](./ARCHITECTURE_MIGRATION_PROGRESS.md) 追加记录，测试专项结果同步统一测试台账，不再新建同义进度文件。至少写明：

```text
切片：DP? / 能力 / 本次职责边界
基线：分支、HEAD、工作区其他任务改动
契约：当前入口、旧/新链路、数据格式、配置、回退与状态所有者
决定：复用 / 提取 / 暂留的具体依据，以及仍待验证的假设
改动：文件落点、消费者、端口、装配、打包与测试联动
验证：命令、结果、收集数量变化、真实风险路径、未运行项及原因
回滚：同批恢复和撤回的文件及状态影响
下一步：最小能力切片及前置条件
```

本方案没有对应英文内部版本；不新增平行译本，不修改 README。本文仅完成源码职责盘点、72 文件去向对账、目录及文档链接核对，未执行代码改造或测试。后续实施、提交、推送和打标签遵循维护者授权及 AGENTS.md。
