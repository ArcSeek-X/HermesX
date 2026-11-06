# HermesX 目标架构实施延续：data_provider 内部职责优化初步方案

> 保留数据源包现有位置，以能力边界收敛旧管理器、具体源实现与公共运行机制；在保持取数契约的前提下逐步改造。

| 项目 | 内容 |
| --- | --- |
| 文档名称 | `ARCHITECTURE_TARGET_DATA_PROVIDER_REFACTORING.md` |
| 作者 | Codex，依据维护者讨论及仓库代码盘点整理 |
| 创建 / 更新时间 | 2026-11-05 / 2026-11-06（Asia/Shanghai） |
| 版本 / 状态 | v1.0，根目录收敛 R0–R5 已完成：15/15（100%）；原 B23 的 Windows/Intel/桌面窗口缺口独立跟踪，Docker 子项已补验 |
| 盘点基线 | `main` / `3737f14f`；开工时工作区干净，后续实施重新记录 HEAD 与状态 |
| 上位方案 | [ARCHITECTURE_TARGET.md](./ARCHITECTURE_TARGET.md) §2、§4.2–4.3、§9.2.1 |
| 已决约束 | [迁移 ADR-003](../architecture_migration_adr.md)：`data_provider/` 原位保留，应用层通过端口访问 |
| 相关专项 | [服务端大文件拆分](./ARCHITECTURE_TARGET_LARGE_FILE_REFACTORING.md)、[测试迁移台账](./TEST_SUITE_MIGRATION_PROGRESS.md) §12 |
| 当前范围 | 数据源包内部职责、依赖、生命周期与测试；必要时联动基础设施端口适配、bootstrap 和打包 |
| 根目录整理补充 | §11 已列完整目标树与下一步执行计划；24 个根 Python 文件收敛到 2 个入口；代码迁移和本轮验收全部完成，15/15（100%）；Linux/ARM64 Docker 构建与容器运行通过；不计入原 B00–B23 进度 |
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
  - [7.4 整体进度与当前步骤](#execution-progress)
  - [7.5 B16–B20 实施与策略对账](#b16-b20-decisions)
  - [7.6 B21–B23 与最终验收](#final-acceptance)
- [8. 测试、客户端及打包验收](#validation)
- [9. 风险、回滚与完成标准](#completion)
- [10. 后续执行者交接要求](#handoff)
- [11. 根目录收敛补充方案（实施与验收）](#root-convergence)
  - [11.2 完整目标目录与职责](#root-final-tree)
  - [11.3 根文件逐项去向](#root-file-destinations)
  - [11.4 文件内部职责拆分](#root-internal-split)
  - [11.5 下一步执行计划与验收](#root-execution-plan)
  - [11.6 最终交接与后续边界](#root-next-step)

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
├── calendar/  # [已实施] 财经事件日历数据源；不接管交易日规则
│   ├── __init__.py  # [已实施] 财经事件日历公开入口；不接管交易日规则
│   └── wallstreetcn_source.py  # [已实施] 迁入国家与财经事件区间查询、秒级 UTC 和异常（原接口无分页）；复用旧 Fetcher 的唯一实现
├── chip/  # [已实施] 筹码数据；由旧 Manager/Fetcher 提取的已有能力，不是新增业务
│   ├── __init__.py  # [已实施] 筹码数据能力入口，补齐上一版目录遗漏的现有能力
│   ├── akshare_source.py  # [已实施] 原 AkshareFetcher 的筹码原始数据请求与转换
│   ├── base.py  # [已实施] 原筹码协调与提供方有效性解析；复用 domain 模型/共同阈值，保留空值、回退和熔断
│   └── tushare_source.py  # [已实施] 原 TushareFetcher 的筹码请求与指标输入标准化；纯业务计算复用 domain
├── clients/  # [已实施] 真正跨能力复用的供应商协议客户端，不重复 Source 的能力协调
│   ├── akshare/  # [已实施] AkShare 跨能力 UA/节流协议支撑，沿用原实例状态
│   │   ├── __init__.py  # [已实施] akshare 共享客户端的必要公开导出，不提前创建资源
│   │   └── client.py  # [已实施] AkShare 共享 UA/两类节流访问，不包含能力取数或全局回退
│   ├── stocksdk/  # [已实施] 跨能力 Node 桥接封装，不迁移 Node 工程本身
│   │   ├── __init__.py  # [已实施] stocksdk 共享客户端的必要公开导出，不提前创建资源
│   │   └── bridge.py  # [已实施] 原 StockSdkBridgeClient、settings、进程及 invoke；保持既有 Node 路径和关闭规则
│   ├── tushare/  # [已实施] Tushare 共享 HTTP 客户端及协议资源，保留原认证/地址选择语义
│   │   ├── __init__.py  # [已实施] tushare 共享客户端的必要公开导出，不提前创建资源
│   │   ├── client.py  # [已实施] 共享 Tushare 认证、限额、交易日期与查询资源访问
│   │   └── http.py  # [已实施] 原 _TushareHttpClient 的 HTTP 协议和错误处理，沿用原 direct HTTP 选择，不新增 SDK fallback
│   ├── __init__.py  # [已实施] 跨能力复用客户端入口；不注册全部供应商、不执行网络请求
│   ├── baostock.py  # [已实施] Baostock 共享模块缓存及登录/登出会话；只封装供应商协议，不包含全局选源或回退
│   ├── efinance.py  # [已实施] Efinance 共享 UA/节流及历史请求准备；只封装供应商协议，不包含全局选源或回退
│   ├── longbridge.py  # [已实施] Longbridge 共享连接、失效冷却与静态信息缓存；只封装供应商协议，不包含全局选源或回退
│   ├── pytdx.py  # [已实施] Pytdx 共享会话、主机轮询与连接冷却；只封装供应商协议，不包含全局选源或回退
│   ├── stockdb.py  # [已实施] stockdb 跨能力共享的原 StockDbClient、settings、查询及本地源错误；只封装供应商协议，不包含全局选源或回退
│   └── tickflow.py  # [已实施] TickFlow SDK 创建/关闭及跨能力缓存、权限状态；只封装供应商协议，不包含全局选源或回退
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
│   ├── diagnostics.py  # [已实施] 包内窄诊断回调及默认装配契约；不导入具体 application 诊断服务、不静默丢事件
│   ├── execution.py  # [已实施，B20 增补] 原预算扣减/重试/超时槽执行，状态和线程工厂窄回调，不新增重试层
│   ├── errors.py  # [已实施] 源不可用、限流、取数失败等既有异常定义的单一事实源；保留旧异常身份
│   ├── fetcher_contract.py  # [已实施] 从根 base 提取 BaseFetcher 兼容契约；迁移期保留旧方法，随能力切片逐项退出，不继续扩张万能接口
│   ├── health.py  # [已收敛] 原健康探针及实时/筹码熔断；状态、锁与故障域保持独立，不合并单例
│   ├── normalize.py  # [沿用] 数据源协议使用的代码格式转换；业务代码规则复用 domain 真源
│   └── rate_limit.py  # [沿用] 限流注册及上下文；不改变既有配额和优先级
├── fundamentals/  # [现有] 基本面；沿用现有能力目录
│   ├── __init__.py  # [沿用] 基本面包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── aggregate.py  # [独立聚合已实施] CN/海外聚合、预算与板块块协调；直接加载唯一实现，原缓存/锁仍由资源所有者持有
│   ├── akshare_source.py  # [厂商实现已归位] akshare 已有基本面字段获取与源标准化；凭实际覆盖接入 aggregate，不假定所有源提供相同字段
│   ├── base.py  # [沿用] 基本面现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── flow_source.py  # [已实施] 资金流/龙虎榜块预算、超时及状态协调；原始厂商接口在同目录 AkShare Source，避免复制；不承担交易评价
│   ├── tushare_source.py  # [加载已改造] 历史 tushare id/门控与来源标签保留，直接绑定独立多源聚合，不回调公开门面，不假定仅请求 Tushare
│   ├── source_contract.py  # [B11 增补] 基本面请求/结果与 Source 协议，base 再导出同一对象，避免具体源优先导入时回到默认注册表
│   └── yfinance_source.py  # [厂商实现已归位] yfinance 已有基本面字段获取与源标准化；凭实际覆盖接入 aggregate，不假定所有源提供相同字段
├── institutional/  # [现有] 机构数据；沿用现有能力目录
│   ├── __init__.py  # [沿用] 机构数据包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 机构数据现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── tw_client.py  # [已实施] 迁入台湾机构 HTTP 查询和民国日期解析，tw_source 负责能力结果适配
│   └── tw_source.py  # [沿用] 台湾机构的机构数据协议、分页和字段标准化；不承担跨厂商回退
├── kline/  # [已扩展] 分别承接分析日线与页面多周期 K 线，保留各自契约
│   ├── __init__.py  # [沿用] 页面多周期 K 线包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 页面多周期 K 线现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── daily_akshare_source.py  # [日线部分已实施] akshare 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_alphavantage_source.py  # [日线部分已实施] alphavantage 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_baostock_source.py  # [日线部分已实施] baostock 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_efinance_source.py  # [日线部分已实施] efinance 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_finnhub_source.py  # [日线部分已实施] finnhub 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_history.py  # [已实施] 分析日线的优先级、市场路由、完整性与预取协调；保留 DataFrame/来源契约
│   ├── daily_longbridge_source.py  # [日线部分已实施] longbridge 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_normalize.py  # [已实施] 原 BaseFetcher 的日线字段清洗、排序与标准化；技术指标纯规则复用 domain，不能再造指标算法
│   ├── daily_pytdx_source.py  # [日线部分已实施] pytdx 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tencent_source.py  # [已归位] tencent 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tickflow_source.py  # [日线部分已实施] tickflow 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tushare_source.py  # [日线部分已实施] tushare 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_yfinance_source.py  # [日线部分已实施] yfinance 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── eastmoney_source.py  # [沿用] 东方财富的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── local_stockdb_source.py  # [沿用] 本地 StockDB的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── sina_source.py  # [沿用] 新浪的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── stocksdk_source.py  # [沿用] StockSDK的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── tencent_source.py  # [沿用] 腾讯的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退；保持页面周期/复权契约，与分析日线不是直接替换关系
│   └── transform.py  # [沿用] K 线排序、复权、StockDB 行归一、重采样与裁剪；保持单位和边界
├── limit_pool/  # [现有] 涨跌停池；沿用现有能力目录
│   ├── __init__.py  # [沿用] 涨跌停池包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── akshare_source.py  # [已实施] 原 AkShare 涨跌停获取/排序/字段/节流，不改为新 HTTP 通道；现有 EastMoney 包装仍使用该原 SDK 能力
│   ├── source_contract.py  # [已实施，B14 增补] 原涨跌停 DTO/常量/Source 协议，具体源导入不触发默认注册
│   ├── base.py  # [沿用] 涨跌停池现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── eastmoney_source.py  # [沿用] 东方财富的涨跌停池协议、分页和字段标准化；不承担跨厂商回退
│   └── stocksdk_source.py  # [沿用] StockSDK的涨跌停池协议、分页和字段标准化；不承担跨厂商回退
├── market/  # [已实施] 市场快照、指数与统计原始数据；不包括市场分析用例
│   ├── __init__.py  # [已实施] 全市场快照、指数与统计的公开取数入口，不包括市场分析用例
│   ├── eastmoney_source.py  # [快照已归位] 原 clist 全市场快照；B14 卡片辅助在 indices/statistics，Session/缓存仍归 sector 原模块，不混用返回契约
│   ├── indices.py  # [已实施] 按市场查询指数原始数据的能力协调，保留来源优先级
│   ├── snapshot.py  # [已实施] 封装全市场快照能力；与现有 MarketSnapshotPort 对账，不能重复其外层回退
│   ├── statistics.py  # [已实施] 市场涨跌家数等原始统计协调，不吸收市场策略
│   └── tencent_source.py  # [已实施] 腾讯全市场快照取数及标准化，承接旧快照模块
├── news/  # [现有] 新闻；沿用现有能力目录
│   ├── __init__.py  # [沿用] 新闻包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 新闻现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── wallstreetcn_live.py  # [已实施] 迁入实时新闻频道目录、URL、scope 和响应解析；news Source 委托此实现
│   └── wallstreetcn_source.py  # [沿用] 华尔街见闻的新闻协议、分页和字段标准化；不承担跨厂商回退
├── realtime/  # [现有] 实时行情；沿用现有能力目录
│   ├── __init__.py  # [沿用] 实时行情包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── akshare_source.py  # [实时部分已实施] 保留现有能力包装，承接原 Fetcher 实时通道及缓存取数与标准化，不承担跨厂商回退
│   ├── alphavantage_source.py  # [实时部分已实施] alphavantage 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── base.py  # [沿用] 实时行情现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── efinance_source.py  # [实时部分已实施] efinance 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── coordination.py  # [已实施，B21 增补] 原分析实时路由/回退与单源尝试，保持市场、HK 参数、配置/锁/诊断
│   ├── enrichment.py  # [已实施] 缺字段补全、来源 token 和新鲜度；路由及失败诊断日志仍在原 Manager，不决定交易策略
│   ├── finnhub_source.py  # [实时部分已实施] finnhub 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── longbridge_source.py  # [实时部分已实施] longbridge 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── prefetch.py  # [已实施] 批量实时预取及缓存写入，保留原调用预算、并发限制和实例作用域
│   ├── pytdx_source.py  # [实时部分已实施] pytdx 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── tickflow_source.py  # [实时部分已实施] 保留现有能力包装，承接原 Fetcher 实时取数、预取和标准化，共用原客户端与缓存
│   ├── tushare_source.py  # [实时部分已实施] tushare 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── source_contract.py  # [B10 增补] 轻量实时 Source 协议，base 再导出同一对象，避免具体源导入默认注册表形成循环
│   ├── types.py  # [已实施] 从 realtime_types 提取行情枚举、UnifiedRealtimeQuote 和标量转换；新旧导出保持类型身份
│   └── yfinance_source.py  # [实时部分已实施] yfinance 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
├── runtime/  # [部分实施] 包内实例构造、资源拥有关系与关闭；bootstrap 仍负责进程级接线
│   ├── __init__.py  # [规划] 包内构造与资源管理入口，不依赖 bootstrap
│   └── fetcher_factory.py  # [已实施] 默认源构造及可选依赖探测；保留原加载时机和配置优先级
├── sector/  # [现有] 板块榜单；沿用现有能力目录
│   ├── __init__.py  # [沿用] 板块榜单包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── akshare_source.py  # [已实施] 行业/概念/人气榜及原候选回退，复用原 SDK/节流
│   ├── coordination.py  # [已实施，B14 增补] 行业/概念/人气/所属板块协调，显式接入原类级缓存和诊断，不传整个宿主
│   ├── source_contract.py  # [已实施，B14 增补] 板块请求/结果及 Source 协议，隔离默认注册并保留 base 再导出身份
│   ├── base.py  # [沿用] 板块榜单现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── eastmoney_source.py  # [沿用] 东方财富的板块榜单协议、分页和字段标准化；不承担跨厂商回退；市场辅助已委托 market indices/statistics 唯一实现，原 Session/缓存保留，禁止保留两份算法
│   ├── efinance_source.py  # [已实施] 行业排行及所属板块，复用原执行器/超时/SDK
│   ├── market_cards_source.py  # [沿用] 现有行情卡片数据聚合与预热入口；取数协调与应用展示策略按调用方分界，不扩张 UI 职责
│   ├── shidaotec_source.py  # [沿用] 世达科技行业、概念、ETF 与个股树图原始数据及源异常，不迁移页面组件
│   ├── stocksdk_source.py  # [沿用] StockSDK的板块榜单协议、分页和字段标准化；不承担跨厂商回退；跨市场辅助已委托 market 唯一实现，原缓存与桥接 getter 保留，clients/stocksdk 已于 B19 归位
│   ├── tickflow_source.py  # [已实施] 原 SW1 行业排行，复用同一 SDK/权限/实例缓存及锁
│   └── tushare_source.py  # [已实施] 原行业排行与交易时间/配额，不新增概念或热股能力
├── stock_info/  # [现有] 股票信息；沿用现有能力目录
│   ├── __init__.py  # [沿用] 股票信息包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # [沿用] 股票信息现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── catalog.py  # [已实施] 三厂商公开股票清单与 Pytdx 内部分页，复用原 SDK/缓存；索引持久化沿用外层流程，不写应用数据库
│   ├── eastmoney_source.py  # [沿用] 东方财富的股票信息协议、分页和字段标准化；不承担跨厂商回退
│   ├── local_stockdb_source.py  # [沿用] 本地 StockDB的股票信息协议、分页和字段标准化；不承担跨厂商回退
│   ├── name_lookup.py  # [已实施] 单个/预取/批量名称协调和七厂商精确查询，原缓存所有权保持，不将搜索和精确查询混为一体
│   ├── stocksdk_source.py  # [沿用] StockSDK的股票信息协议、分页和字段标准化；不承担跨厂商回退
│   └── tencent_source.py  # [沿用] 腾讯的股票信息协议、分页和字段标准化；不承担跨厂商回退
├── __init__.py  # [沿用] 数据源子系统精简入口；兼容导出必须绑定同一对象，禁止 eager 导入全部 SDK
├── akshare_fetcher.py  # [必要兼容，B21 审计保留] 保留厂商类型/资源构造/私有覆盖点；能力与共享协议委托唯一实现
├── alphavantage_fetcher.py  # [必要兼容，B21 审计保留] 保留可选美股源类型/配置门面；日线/实时/名称委托能力实现
├── baostock_fetcher.py  # [必要兼容，B21 审计保留] 保留类型/构造与会话覆盖点，协议/清单/能力实现已归位
├── eastmoney_quote_snapshot.py  # [必要兼容，B21 审计保留] 原 Session/函数兼容再导出；实现为 market/eastmoney_source.py
├── efinance_fetcher.py  # [必要兼容，B21 审计保留] 保留类型及旧报价 DTO/资源覆盖点；能力与共享节流已归位
├── finnhub_fetcher.py  # [必要兼容，B21 审计保留] 保留可选美股源类型/配置门面；日线/实时/名称委托能力实现
├── fundamental_adapter.py  # [必要兼容，B21 审计保留] 同一 AkshareFundamentalAdapter 兼容再导出，不保留算法副本
├── longbridge_fetcher.py  # [必要兼容，B21 审计保留] 保留类型/凭据兼容助手和资源覆盖点，协议委托 clients/longbridge.py
├── pytdx_fetcher.py  # [必要兼容，B21 审计保留] 保留类型/主机配置和协议转换助手，能力与会话委托唯一实现
├── realtime_types.py  # [必要兼容，B21 审计保留] 原枚举/DTO/转换/熔断 getter 兼容再导出，状态仍唯一且故障域分离
├── stockdb_fetcher.py  # [必要兼容，B21 审计保留] canonical clients/stockdb 模块别名；共享单例/Session/私有替换点
├── stocksdk_bridge.py  # [必要兼容，B21 审计保留] canonical clients/stocksdk/bridge 模块别名；共享单例/原仓库路径
├── tencent_fetcher.py  # [必要兼容，B21 审计保留] 原 TencentFetcher/异常同对象再导出，唯一实现在 kline/daily_tencent_source.py
├── tencent_quote_snapshot.py  # [必要兼容，B21 审计保留] 原 Session/函数兼容再导出；实现为 market/tencent_source.py
├── tickflow_fetcher.py  # [必要兼容，B21 审计保留] 保留类型/构造与转换覆盖点；共享 SDK/缓存和能力算法已归位
├── tushare_fetcher.py  # [必要兼容，B21 审计保留] 保留类型/构造/转换覆盖点及同一 HTTP 类再导出，查询/配额/能力已归位
├── tw_institutional_fetcher.py  # [必要兼容，B21 审计保留] canonical institutional/tw_client 模块别名；保留旧类/常量/pickle 路径
├── wallstreetcn_calendar_fetcher.py  # [必要兼容，B21 审计保留] canonical calendar/wallstreetcn_source 模块别名，DTO/异常身份保持
├── wallstreetcn_live_news_fetcher.py  # [必要兼容，B21 审计保留] canonical news/wallstreetcn_live 模块别名，频道/DTO/异常身份保持
├── yfinance_fetcher.py  # [必要兼容，B21 审计保留] 保留类型/转换兼容入口，能力实现已归位，不加回调 Source 的 client
├── yfinance_fundamental_adapter.py  # [必要兼容，B21 审计保留] 同一 YfinanceFundamentalAdapter 兼容再导出，不保留算法副本
├── base.py  # [沿用] 保留 DataFetcherManager 旧调用门面；能力实现委托新协作者，BaseFetcher 如需兼容则再导出公共契约；不保留业务实现副本
└── us_index_mapping.py  # [沿用] 保留已有指数映射兼容入口，复用 domain 真源；不是重新复制一份映射
```

本规划共 **146 个 Python 文件、18 个下级目录**；数量仅用于文档对账，不是要求增加代码或文件的验收指标。原 72 文件的去向与当前 21 个根级兼容入口保留决定均已登记，逐文件证据见[验收附件](./ARCHITECTURE_TARGET_DATA_PROVIDER_ACCEPTANCE.md)，新增文件不表示新增业务能力。

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
| `data_provider/akshare_fetcher.py` | `kline/daily_akshare_source.py`、`realtime/akshare_source.py`、`fundamentals/akshare_source.py`、`sector/akshare_source.py`、`chip/akshare_source.py`、`clients/akshare/client.py`、`market/indices.py`、`market/statistics.py`、`limit_pool/akshare_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/alphavantage_fetcher.py` | `kline/daily_alphavantage_source.py`、`realtime/alphavantage_source.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/baostock_fetcher.py` | `kline/daily_baostock_source.py`、`clients/baostock.py`、`stock_info/catalog.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/base.py` | `base.py`、`common/errors.py`、`common/fetcher_contract.py`、`common/diagnostics.py`、`kline/daily_history.py`、`kline/daily_normalize.py`、`realtime/enrichment.py`、`realtime/prefetch.py`、`stock_info/name_lookup.py`、`stock_info/catalog.py`、`fundamentals/aggregate.py`、`fundamentals/flow_source.py`、`market/indices.py`、`market/statistics.py`、`chip/base.py`、`runtime/fetcher_factory.py` | 按能力拆分，门面仍保留；不能把整个宿主对象传给协作者形成隐式耦合 |
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
| `data_provider/finnhub_fetcher.py` | `kline/daily_finnhub_source.py`、`realtime/finnhub_source.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
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
| `data_provider/pytdx_fetcher.py` | `kline/daily_pytdx_source.py`、`realtime/pytdx_source.py`、`clients/pytdx.py`、`stock_info/catalog.py`、`stock_info/name_lookup.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
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
| `data_provider/tencent_fetcher.py` | `kline/daily_tencent_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tencent_quote_snapshot.py` | `market/tencent_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tickflow_fetcher.py` | `kline/daily_tickflow_source.py`、`realtime/tickflow_source.py`、`sector/tickflow_source.py`、`clients/tickflow.py`、`stock_info/catalog.py`、`stock_info/name_lookup.py`、`market/indices.py`、`market/statistics.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tushare_fetcher.py` | `kline/daily_tushare_source.py`、`realtime/tushare_source.py`、`fundamentals/tushare_source.py`、`sector/tushare_source.py`、`chip/tushare_source.py`、`clients/tushare/client.py`、`clients/tushare/http.py`、`stock_info/catalog.py`、`stock_info/name_lookup.py`、`market/indices.py`、`market/statistics.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/tw_institutional_fetcher.py` | `institutional/tw_client.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/us_index_mapping.py` | `us_index_mapping.py` | 保留/内部收敛；职责见 §4.1，原公开契约保持 |
| `data_provider/wallstreetcn_calendar_fetcher.py` | `calendar/wallstreetcn_source.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/wallstreetcn_live_news_fetcher.py` | `news/wallstreetcn_live.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
| `data_provider/yfinance_fetcher.py` | `kline/daily_yfinance_source.py`、`realtime/yfinance_source.py`、`fundamentals/yfinance_source.py`、`market/indices.py`、`market/statistics.py` | 拆分/迁移；先保留必要委托，全部消费者及打包迁完后撤旧入口 |
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
| B03 / DP1 | B02 | common/diagnostics.py 仅消费 provider_diagnostic_ports；激活原诊断 trace 时绑定同一记录实现，保留直接库调用；不要求新 bootstrap 前置步骤 | 开始/结束/来源/耗时/失败字段及跨线程关联；未装配行为明确，不能吞事件 | 回调注入、装配、测试与旧记录调用同时恢复 |
| B04 / DP1 | B02 | 提取 runtime/fetcher_factory.py；审计现有关闭职责，本轮保持 Manager 的锁/排序/资源所有权，resources.py 仅在独立封装有收益时创建；SDK 不提前实例化 | 实例数量、默认源顺序、可选依赖缺失、重复关闭、借用资源不被误关 | 工厂与资源所有权一起恢复，不改变运行配置 |
| B05 / DP1 | B01、B04 | 专门对账 fundamentals/tushare_source.py → DataFetcherManager 的真实聚合依赖，设计 aggregate 的底层单向调用；锁定配置门控和 payload/source 语义 | 构造及调用不递归、初始化不引入循环导入；旧入口与新入口对照结果一致 | 聚合入口、门面和 source 同批恢复，禁止只改一端 |
| B06 / DP2 | B02–B05 | 腾讯日线试点：kline/daily_history.py、daily_normalize.py、daily_tencent_source.py；已有 kline/tencent_source.py 不直接替换；共享协议只在真正等价处抽入 clients/tencent.py | 原 799/800 条、上市短历史、日期边界、复权、超时、全源失败和 source 标识；腾讯并发 HTTP 隔离回归保留 | 腾讯相关唯一实现、旧导出与消费者成组回退 |
| B07 / DP2 | B06 | 按 Efinance → AkShare → Tushare 分切片迁分析日线；随实际共享调用提取各 clients；先保留其他能力原实现，不让客户端回调旧门面 | 各市场源顺序、原字段/单位/指标输入、旧接口与新接口数据对照；SDK/HTTP 模式和凭据探测 | 按厂商独立回退；已被其他能力消费的客户端需一起核查 |
| B08 / DP2 | B07 | 按 Yfinance → Baostock → Pytdx → Longbridge → Finnhub → AlphaVantage → Tickflow 分切片处理其余日线源；与 StockDB 页面源保持契约区分 | 港/美/日/韩/台等现有覆盖、指数与 ETF、限流、SDK 缺失、批量预取、线程安全与关闭 | 一厂商一切片回退，不改全局优先级掩盖失败 |
| B09 / DP3 | B04、B08 | realtime/types.py 与 common/health.py 收敛原 realtime_types；先保持 breaker 对象、计数器和故障域 | 枚举/DTO 身份、类型再导出、并发与测试重置；不将实时和筹码故障状态误合并 | 类型/熔断实例/所有导出共同回退 |
| B10 / DP3 | B09 | realtime/enrichment.py、prefetch.py；逐个迁入实时 Source：AkShare/Tickflow 现有入口先对账，再处理 Efinance、Tushare、Pytdx、Longbridge、Finnhub、AlphaVantage、Yfinance | 缺字段补全、新鲜度、全失败日志、港股裸码、市场路由、预取、缓存和并发；不新增原不支持的能力 | 每个实时供应方及补全策略可独立回退；不影响已通过的日线 |
| B11 / DP3 | B05、B10 | fundamentals/aggregate.py、flow_source.py 与 AkShare/Yfinance 实际源；解开名为 Tushare 的旧包装，按真实职责收敛；不为 Finnhub/AlphaVantage 虚构基本面能力 | 预算截止、局部失败、资金流、龙虎榜、not_supported/partial、配置门控和来源标签不变；两入口不循环调用 | aggregate、适配器、旧门面及 source 原子恢复 |
| B12 / DP3 | B08、B11 | stock_info/name_lookup.py、catalog.py；承接各厂商已存在的名称及清单能力，保持 code_search 独立 | 单个/批量名称、缓存隔离、精确查询与模糊搜索、代码规范化；不额外触发实时网络请求 | 名称/清单入口与相关客户端方法一起恢复 |
| B13 / DP3 | B08、B12 | market/snapshot.py、indices.py、statistics.py、eastmoney_source.py、tencent_source.py；与现有外层端口收敛并对账 sector 市场辅助契约，卡片缓存/预热辅助保持完整状态边界由 B14 处理 | 市场指数/统计/快照、原回退顺序、共享缓存、字段和来源；不得两个层各重试一次 | 旧快照/指数统计入口与新实现成组恢复；sector 卡片辅助按 B14 边界恢复 |
| B14 / DP3 | B13 | 接续 B13 的 sector 市场辅助及缓存/预热；sector 的 AkShare/Efinance/Tushare/Tickflow 能力与现有 EastMoney/StockSDK/Shidaotec/market_cards 对账；limit_pool 单列 akshare_source，不强换成 EastMoney 直接请求 | 行业/概念/热股/所属板块、榜单、涨跌停与市场卡片，原可用源/字段/热身调度保持 | 按能力恢复，共享市场方法只保留一份真源 |
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
| `src/application/runtime/provider_diagnostic_ports.py`、`src/application/runtime/run_diagnostics.py` | B03 的窄回调端口及 trace 激活绑定；不保存第二份上下文 | 新事件字段、脱敏、跨线程/嵌套 trace、未激活 trace 的普通取数行为保持 |
| `src/bootstrap/analysis.py`、`src/bootstrap/quote.py` | 工厂、诊断或资源生命周期接线变化时 | CLI/API/测试三入口均装配，不增加隐藏初始化 |
| `src/bootstrap/api_lifecycle.py`、`main.py`、`tests/conftest.py` | 新资源需要明确启停或原装配引用变化时 | 真实生命周期、关闭与测试独立性；不在全局 conftest 掩盖缺失装配 |
| `src/application/analysis/context_enrichment.py`、`src/application/analysis/analysis_context_builder.py`、`src/application/market/daily_market_context.py` | 盘点确认有业务上下文职责需归还应用层时 | 先锁定实际消费者和输入/输出；无需要则不修改 |
| `scripts/build-backend-macos.sh`、`scripts/build-backend.ps1`、`docker/Dockerfile` | 路径变化影响导入/资源收集时；实际 Docker 文件名实施前复核 | 保持默认构建路径，源码 import 与冻结后实际 import 都验收 |
| `tests/infrastructure/providers/` 及真实 API/application 消费方测试 | 每个能力切片 | 真实风险层不被 mock 绕过；不删断言、不加跳过维持绿灯 |

每批退出前需逐项核对：文件去向与公开方法；类型/异常身份；源和市场覆盖；优先级及全失败；缓存/锁/熔断所有者；资源关闭；装配和 patch；打包引用；验证结果与缺口；回滚。任一项未知时登记阻塞并缩小切片，不给整批写“完成”。

<a id="design-improvements"></a>
### 7.3 本次设计的优化点及开工条件

相比 v0.2：补齐筹码等已有能力；撤下无源码依据的 Finnhub/AlphaVantage 基本面候选；区分分析日线与页面 K 线；单列 Tushare 名称包装旧聚合链的依赖解环；穷举文件去向与资源所有权；将大阶段拆为可验证工作包。

代码实施已按 B00–B22 完成当前范围；早期切片见实施流水 §0.180–0.193。B00/B01 原矩阵和动态使用者已收口，B23 实际验收缺口见 §7.6 与验收附件，未达到全专项 100%。

<a id="execution-progress"></a>
### 7.4 整体进度与当前步骤

**统计对象仅为本轮 data_provider 专项，不是整个 HermesX 或已完成的上一轮架构迁移。**按 B00–B23 共 24 个工作包等权统计；只有该批实现、范围内验证及记录收口后才计入完成数。部分完成或验收中的批次不折算；此比例用于任务追踪，不代表代码量、工时或剩余 token 比例。

| 指标 | 当前值（2026-11-05） |
| --- | --- |
| 整体进度 | **95.8% = 23 / 24** |
| 已完成 | B00、B01、B02、B03、B04、B05、B06、B07、B08、B09、B10、B11、B12、B13、B14、B15、B16、B17、B18、B19、B20、B21、B22 |
| 当前批次 | **B23 部分验收：源码/干净环境冻结/本机后端/DMG 已验证；Docker 授权及跨平台/窗口未收口** |
| 尚未收口 | B23 的 Windows/Intel 与桌面窗口验证（Docker 已补验）；详见验收附件 |
| 未开始 | 无；B23 已执行但未全部通过 |

| 批次 | 状态 | 已完成范围 / 下一步 |
| --- | --- | --- |
| B00 | 完成 | 原 72 文件、802 引用及 17 项受控动态导出对账；保留 21 根兼容路径，附可复现审计脚本 |
| B01 | 完成 | 321 调用契约/字段对账、16 能力矩阵及输入输出/状态/异常/测试映射，见验收附件 |
| B02 | 完成 | 异常/Fetcher 契约唯一实现与旧导出兼容 |
| B03 | 完成 | 诊断端口、原 trace 激活绑定及跨线程回归 |
| B04 | 完成 | 默认源工厂提取；资源所有权审计，关闭逻辑保留原宿主 |
| B05 | 完成 | 基本面 Source 单向加载边界及回路反证；聚合算法拆分属 B11 |
| B06 | 完成 | 腾讯归位、日线协调、字段清洗及完整门禁对照收口；门禁仍有已登记的既有 API 失败 |
| B07 | 完成 | 三厂商日线协议/标准化及共享状态回归收口；其他能力和共享客户端仍按后续批次处理 |
| B08 | 完成 | 七供应商日线职责提取；原会话/SDK/限流/缓存/冷却所有权及原重试保留，回归与全量门禁对照收口 |
| B09 | 完成 | DTO/熔断归位；保留原健康探针及独立状态，旧导出/序列化/导入顺序兼容与全量门禁对照收口 |
| B10 | 完成 | 补全/预取、九源实时职责提取和轻量协议解环；共享状态、默认注册及载荷不变，11 项回归和全量门禁对照收口 |
| B11 | 完成 | 独立聚合/资金流与双适配器、轻量协议解环；临时叶绑定撤下，保留原资源/门控/载荷，最终回归与门禁对照收口 |
| B12 | 完成 | 名称回退/预取/批量与七厂商名称、四类清单/分页归位；原 SDK/缓存/搜索边界保持，回归和完整门禁对照收口 |
| B13 | 完成 | 快照/指数/统计归位及同源公式去重；外层回退/单位/Session 保持，最终回归与完整门禁对照收口；卡片辅助归 B14 |
| B14 | 完成 | 板块/榜单/涨跌停、协议解环及卡片辅助接线；原状态/字段/预热保持，18 项新回归与完整门禁对照收口 |
| B15 | 完成 | 筹码协调/双源、domain 纯计算及共同阈值归位；不同输入解析保留，8 项新回归、随机序及完整门禁对照收口 |
| B16 | 完成 | 日历唯一实现及旧 DTO/异常入口，国家/时间/响应关闭原样 |
| B17 | 完成 | 快讯客户端与现有资讯 Source 接线，原安全请求回调和 scope/游标保持 |
| B18 | 完成 | 台湾客户端归位、动态工厂及替身隔离，机构/报告链路验证 |
| B19 | 完成 | 两个共享客户端与七厂商 36 个协议方法；7 个残余能力方法归位，按真实收益撤下 5 个无必要目标文件 |
| B20 | 完成 | 执行预算唯一实现、增强拼装归位；缓存/配额/健康及应用消费方对账，非等价策略保持 |
| B21 | 完成 | 按需导出、日线/实时协调移出；必要兼容入口审计保留，源码/冻结路径验证 |
| B22 | 完成 | data_provider 依赖规则、登记端口与字面动态导入检测；4 组反例和原守卫通过，baseline 未扩容 |
| B23 | 部分验收/阻塞 | 后端门禁、Web、干净环境冻结与本机运行、ARM64 DMG 已实测；Docker Pro 授权、Windows/Intel/窗口仍有缺口 |

每个批次结束同步本表、当前总览及实施流水，并向维护者报告：整体百分比、完成数、当前批次/子步骤、验证结论、既有失败或未验证项、下一步。当前 B00–B22 为 23/24 = 95.8%；B23 全部验收收口后才计 100%，子步骤不单独提高整体比例。


<a id="b16-b20-decisions"></a>
### 7.5 B16–B20 实施决定、资源与策略对账（2026-11-05）

本节记录 B16–B20 当时的实施结果和目录快照。后续 B00/B01/B21/B22 已收口，当前未完成项与证据以 §7.6 和验收附件为准；下文 125 文件等数量为当时快照。

| 批次 | 唯一实现与当前落点 | 保持与边界 |
| --- | --- | --- |
| B16 | `calendar/wallstreetcn_source.py` | 原国家、事件 DTO/异常与 Fetcher；macrodatas 本就无分页，不虚构游标；秒级 UTC、全天 0、国家字段与响应关闭原样；不接管交易日历 domain |
| B17 | `news/wallstreetcn_live.py`，现有 `news/wallstreetcn_source.py` 改接 canonical 客户端 | 原频道/scope、游标、请求头、4 MiB 限制和错误；日历原 8 MiB 限制保持。仍由应用注入安全 request_get，禁止重建 requests 绕开 DNS/SSRF 复检；归档/分类/落库/NewsNow 降级不下沉 |
| B18 | `institutional/tw_client.py`，`tw_source.py` 装配时解析客户端 | 民国日期、TW/TWO、股数/正负号、合法空结果、整市场缓存/逐 key 锁及单独 breaker；通过按需导出保留旧工厂 patch，避免临时替身永久绑定；未更改已接入报告的基本面块 |
| B19 | `clients/stockdb.py`、`clients/stocksdk/bridge.py`；七厂商共享协议文件与 Tushare HTTP 类 | 单例/锁/Session 不复制；Node 相对路径和 cwd 仍指同一仓库，参数/超时/错误映射不变。共享类只做连接、配额/缓存访问，无 Source 工厂/能力回退或 BaseFetcher 继承 |
| B19 接续 | `kline/daily_{akshare,efinance,tickflow}_source.py`、`stock_info/catalog.py` | AkShare/Efinance 路由与原 AkShare 美股私有接口、TickFlow 批预取、Efinance 基本信息归位；原路由排除市场、UA/节流、负权限缓存、部分结果和调用次序保持 |
| B20 | `common/execution.py`、`realtime/enrichment.py` | 原基本面预算/重试/超时槽唯一实现、两厂商增强载荷拼装；不增加重试层或改变可见载荷。公共缓存、限流、健康机制经审计按实际差异保留 |

五个旧整模块入口（calendar/live/TW/StockDB/StockSDK）是 canonical 模块的兼容别名，共享同一模块对象：旧 DTO/异常和旧 pickle GLOBAL 引用可解析，重置旧 `_CLIENT` 与私有常量直接作用到唯一状态。Tushare 根模块再导出同一 HTTP 类。包内和分时基础设施适配器已改用 canonical import；测试保留历史导入以验证兼容。

其余旧 Fetcher 暂留构造、资源状态、纯协议助手及窄委托；36 个共享协议方法已迁入 `clients/`，7 个残余能力方法已归位。跨能力 SDK/缓存/配额仍由原实例唯一持有，显式字段 getter/setter 写回原位置；低层资源方法回调保留原覆盖点，不调用旧公开取数算法，不传整个宿主。没有新增默认客户端或提前网络初始化。根门面收口及剩余私有助手的最终定位归 B21，不把本轮等同于已删除旧文件。

**按实际收益修正目标树**：不创建 `clients/alphavantage.py`、`finnhub.py`、`tencent.py`、`yfinance.py` 与 `clients/akshare/conversions.py`。前两者当前没有独立跨能力共享资源/配额实现可迁；腾讯的日线与页面/快照契约不同，不强合 Session/解析；Yfinance 现有 helper 已委托 market，不能再套一个回调 Source 的客户端；AkShare 转换各有实际能力归属，继续原 seam/Source，未证等价不抽万能 conversions。未来出现真正共享协议时再建立。新增 `common/execution.py` 承接确实存在的执行机制，故目标 **129 − 5 + 1 = 125 Python 文件，仍 18 下级目录**；当前 145 件含迁移中的旧兼容文件，不要求立刻等于目标。

| 机制 / 唯一状态 | 已核对的实际契约 | 本轮决定 |
| --- | --- | --- |
| Root tenacity 与叶 Source | 日线既有装饰器次数、等待、异常筛选保持；叶路由仍按原候选尝试 | 不在新客户端叠加重试，不混成所有能力通用次数 |
| `common/execution.py` | 逐次扣同一预算；worker 超时后继续占用原槽，真实退出 finally 才释放；启动失败归还槽 | 原算法归位；不宣称线程可强制取消，不在调用方超时即释放配额 |
| `common/cache.py` | 具名键、整数化 TTL、strict `<` 过期，falsey 载荷不同于 MISS；返回原可变对象 | 保留现有语义；不新增自动深拷贝或统一键 |
| `clients/stockdb.py` | 实例缓存/Session；TTL 保留小数；配置/冷却检查先于缓存；共享载荷不复制 | 与公共缓存非等价，保留原轻量实现及哨兵；不把缓存当作冷却期兜底 |
| 名称/基本面/概念/实时/TickFlow | 各自键、TTL、锁、返回副本/原对象、负权限与继承状态不同；基本面缓存仍按原股票键，不改为预算键 | 不强合缓存实例、时钟或过期方式 |
| sector 卡片缓存 | fresh/stale/cold、后台预热与共享 timestamp 延续 B14 | 不替换成阻塞 TTL 缓存或取消现有预热 |
| `common/rate_limit.py` | 具名信号量首个容量生效；异常退出释放；当前实际取数未接入该 guard | 保留库契约，不为了“复用”改现有并发；厂商分钟限额、抖动及批次配额仍分开 |
| 健康注册表 / breakers | HealthProbeRegistry 原按 source_id 共享；日线、实时、筹码及每个台湾客户端 breaker 的状态与阈值不同 | 不合并故障域、阈值或重置入口，不添加新的健康单例 |

**真实应用消费方**：`get_enhanced_data` 当前只见旧厂商兼容方法及手工 main 示例，无生产应用调用；维持既有便利载荷，不另建应用用例。`get_fundamental_context` 则经 `src/infrastructure/providers/analysis_stock_data_provider.py` → `src/application/analysis/pipeline.py`/`stock_data_port.py`，以及 Agent 的 `src/infrastructure/agent_runtime/market_data_provider.py` → `src/application/agent/tools/data_tools.py` 消费；AlphaSift 桥接也有独立调用。上下文构建/信号/报告和提示词继续由 application/domain 消费，不下沉到 clients。原预算、status/coverage/source_chain 和机构数据字段不变，无 API/Web/Desktop/数据库/配置联动改造。

**实施中发现并修正的联动缺陷**：首轮完整检查出现 Agent 子进程 handler_error（5855 passed / 2 failed，377.64s）。临时观测定位到 Pandas 导入时 `calendar.day_abbr` 缺失：旧 `test_us_index_mapping.py` 在收集阶段把 data_provider/ 提升为顶层搜索路径，新日历包遮蔽标准库。该测试已改为包限定导入，原断言保留；新增独立子进程反例，未预加载标准库或绕过真实 worker。修正后全仓收集 + 原 Agent 用例 **1 passed / 5862 deselected（11.38s）**，最终结果以下方稳定版本门禁为准；诊断插件仅在 /tmp，未改 Agent 生产逻辑。

验收：新增 4 文件 30 项、相关随机序 658 passed / 1 skipped / 2 deselected（53.15s），全仓收集 5863（+30，13.95s）、417 个测试模块；最终完整结果见架构流水 §0.193、测试台账 §26。新入口与旧引用均在源码执行验证；已核查 macOS/Windows 后端打包脚本引用方式，本批未做冻结导入、真实 Node/供应商联网、Docker 或安装包实测，不以模拟 subprocess 错误测试充当平台验收。前端全量 lint 继续暂缓。

回滚按五个整模块 alias+canonical+消费者导入成组恢复；七个客户端协议与 Root 窄委托/字段写回、能力残余方法与增强拼装、执行预算与 Root 委托分别成组恢复。不得只删 canonical 留下 shim/委托，不覆盖 B02–B15 或维护者图册等并行修改。无数据库迁移、环境配置或用户数据需要撤销；未 commit/push/tag。


<a id="final-acceptance"></a>
### 7.6 B21–B23 与最终验收（2026-11-06）

原 72 文件及 321 调用契约、802 条 Python 引用、13 条脚本/工作流引用、17 项动态导出与逐能力矩阵已补齐。[验收附件](./ARCHITECTURE_TARGET_DATA_PROVIDER_ACCEPTANCE.md) 为当前逐文件决定和最终证据，不再保留“矩阵待补”为当前待办。

B21 完成包根按需解析，原 __all__ 和对象身份保持；Manager 的日线入口、实时路由/回退和单源尝试迁到能力协作者，原 HK 通道参数等完整保留。21 个根兼容文件因工厂、调用方、私有覆盖与旧载荷需要继续保留，源码及冻结包均加载；不以“改造完成”作为无条件删除依据。资源仍由原 Manager/Fetcher 拥有，不创建无收益的 resources.py；最终目录按实际保留项修正为 **125 − 1 + 1 + 21 = 146 文件 / 18 下级目录**。

B22 的 data_provider 专用规则阻断 API/Bot/bootstrap/具体 application 导入，仅登记 provider_diagnostic_ports 端口；字面动态导入及别名同样检测，计算型动态注册单独审计。4 组反例和原守卫通过，未新增 baseline 豁免。

B23 已完成完整后端门禁、相关随机序、Web 构建、独立干净依赖安装、源码与冻结全包导入、临时 DB 后端健康/首页，以及 ARM64 DMG 构建/签名/只读挂载校验。静态 OpenAPI 只同步描述，结构不变；配置测试隔离仅阻止本机 .env 和先前启动捕获污染，显式临时文件仍真实解析，生产配置语义未改。完整结果与纠错见附件及流水 §0.194/测试台账 §27。

**当前仍为 95.8%**：Docker Web 与完整镜像已在 §11 的续验中通过（本地官方 OCI 输入，Linux/ARM64）；Windows/Intel 仍未验收，桌面窗口本轮已实测未通过（误认现有后端）；网络观测有超时/缺 key 的跳过。前端全量 lint 仍暂缓，不把这些写作通过或用文档收口替代实际验证。未修改 Web/Desktop 界面、数据库或默认配置，未 commit/push/tag。

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

前端全量 lint 按维护者既有安排暂缓；如果具体切片必须改前端，再明确该切片的验证范围。Docker 依赖下载、跨平台和桌面启动等环境/验收阻塞独立登记，不在本专项通过删除依赖、改 UI 或停止本机服务来绕过。

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

B11 已用独立聚合原子替换 B05 临时叶绑定与旧加载工厂，状态继续由原资源所有者持有；B06 日线指标公式保持原样；当前 B23 部分验收，最新结果见架构流水 §0.194、测试台账 §27 和验收附件。

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

本方案没有对应英文内部版本；不新增平行译本，不修改 README。本文仅完成源码职责盘点、72 文件去向对账、目录及文档链接核对，首批代码和验证已追加到架构及测试台账，其余阶段尚未完成。后续实施、提交、推送和打标签遵循维护者授权及 AGENTS.md。

2026-11-06 补充复核（较早批次）：当时 Docker 标准构建缺 Pro CSS；后续维护者注释导入，本轮已通过 Web 构建，后续已通过有限安装重试及本地官方 OCI 输入完成全镜像和容器验收（见 §11）。ARM64 桌面隔离窗口已实际启动，但误认现有 8000 服务，自带后端端口冲突退出。Windows 缺当前运行环境，Rosetta 可用仅证明基础 x86_64 执行，不能代替 Intel 产品验收。详见[验收附件 §6](./ARCHITECTURE_TARGET_DATA_PROVIDER_ACCEPTANCE.md#gap-recheck)，B23 仍未关闭。

<a id="root-convergence"></a>
## 11. 根目录收敛补充方案（2026-11-06，R0–R5 完成）

本节回应 B00–B22 之后根目录仍较平铺的问题，是上位 `ARCHITECTURE_TARGET.md`“按职责拆分、入口装配与能力实现分离”的继续落实。**本节目标代码及 R0–R5 验收已完成，15/15（100%）；完整门禁、固定序检查、干净冻结与 Linux/ARM64 Docker 构建/容器运行通过。本轮镜像使用已校验的本地官方镜像 OCI 上下文，未修改 Docker 全局镜像加速配置。**§4 的 146 文件 / 18 下级目录保留为上一轮落点快照；本节是下一轮目标，有关根目录去向以本节为准。原 B23 打包与平台验收缺口独立跟踪，原阶段的 95.8% 不包含本节新增工作。

### 11.1 当前事实与整理判断

本轮按当前工作树盘点，根目录有 **24 个 Python 文件**（不包括子目录及缓存）：

| 类别 | 文件数 | 判断 |
| --- | ---: | --- |
| 包入口、管理器、指数兼容工具 | 3 | `__init__.py`、`base.py`、`us_index_mapping.py`；其中 `base.py` 1497 行，仍应区分协调、资源所有权和纯规则 |
| 厂商 Fetcher / 资源与能力装配门面 | 10 | AkShare 955 行、TickFlow 915 行、Longbridge 653 行、Efinance 637 行、Tushare 629 行、Pytdx 340 行、Yfinance 321 行、Baostock 233 行、Finnhub 92 行、AlphaVantage 90 行；并非全是薄转接 |
| 已有唯一实现的兼容转导出或模块别名 | 11 | 大部分 9–35 行，真正实现已经进入能力或客户端目录；迁移调用方后可评估删除 |
| 合计 | **24** | 前一轮的“21 个兼容文件”包括上述 10 个仍承载装配/资源及残余逻辑的文件与 11 个薄入口，不应理解成 21 个空壳 |

原先保留入口是为了分批验证与避免同时更换大量调用路径，不是要求永久保留平铺结构。当前项目未上线，内部调用方、工厂和测试可以一并迁移；这些引用本身不能成为永久保留旧文件的理由。存在真实外部消费者、持久化对象模块路径或扩展覆盖契约时，应先查证再作有期限的兼容决定。

另发现两处具体的反向依赖：`common/normalize.py`、`clients/stocksdk/bridge.py` 为复用股票代码规则导入 `data_provider.base`。整理时应改为直接依赖规则真源 `src.domain.market.stock_codes`，避免低层模块因一个纯函数加载运行管理器。不能只移动文件后留下新的导入环。

<a id="root-final-tree"></a>
### 11.2 下一轮目标目录与职责

建议保持现有“按能力组织”为主，新增 `runtime/fetchers/` 仅归类仍有价值的厂商级装配/资源门面。它不成为第二套能力实现，也不把各能力目录重新塞回厂商目录。

以下列出本轮改造完成后的**完整目标 Python 目录**，包含全部能力目录、共享客户端、公共机制和运行装配；不是局部示例，不省略既有 Source。缓存、日志、运行数据与构建产物不属于此源码树。

```text
data_provider/  # 一级：数据源子系统，原位保留
├── __init__.py  # 保留 17 项包级公开惰性导出，绑定唯一实现
├── base.py  # 薄公开兼容面，不持有取数实现、连接或缓存
├── calendar/  # 财经事件日历数据源；不接管交易日规则
│   ├── __init__.py  # 财经事件日历公开入口；不接管交易日规则
│   └── wallstreetcn_source.py  # 迁入国家与财经事件区间查询、秒级 UTC 和异常（原接口无分页）；复用旧 Fetcher 的唯一实现
├── chip/  # 筹码数据；由旧 Manager/Fetcher 提取的已有能力，不是新增业务
│   ├── __init__.py  # 筹码数据能力入口，补齐上一版目录遗漏的现有能力
│   ├── base.py  # 原筹码协调与提供方有效性解析；复用 domain 模型/共同阈值，保留空值、回退和熔断
│   ├── akshare_source.py  # 原 AkshareFetcher 的筹码原始数据请求与转换
│   └── tushare_source.py  # 原 TushareFetcher 的筹码请求与指标输入标准化；纯业务计算复用 domain
├── clients/  # 真正跨能力复用的供应商协议客户端，不重复 Source 的能力协调
│   ├── __init__.py  # 跨能力复用客户端入口；不注册全部供应商、不执行网络请求
│   ├── akshare/  # AkShare 跨能力 UA/节流协议支撑，沿用原实例状态
│   │   ├── __init__.py  # akshare 共享客户端的必要公开导出，不提前创建资源
│   │   └── client.py  # AkShare 共享 UA/两类节流访问，不包含能力取数或全局回退
│   ├── stocksdk/  # 跨能力 Node 桥接封装，不迁移 Node 工程本身
│   │   ├── __init__.py  # stocksdk 共享客户端的必要公开导出，不提前创建资源
│   │   └── bridge.py  # 原 StockSdkBridgeClient、settings、进程及 invoke；保持既有 Node 路径和关闭规则
│   ├── tushare/  # Tushare 共享 HTTP 客户端及协议资源，保留原认证/地址选择语义
│   │   ├── __init__.py  # tushare 共享客户端的必要公开导出，不提前创建资源
│   │   ├── client.py  # 共享 Tushare 认证、限额、交易日期与查询资源访问
│   │   └── http.py  # 原 _TushareHttpClient 的 HTTP 协议和错误处理，沿用原 direct HTTP 选择，不新增 SDK fallback
│   ├── baostock.py  # Baostock 共享模块缓存及登录/登出会话；只封装供应商协议，不包含全局选源或回退
│   ├── efinance.py  # Efinance 共享 UA/节流及历史请求准备；只封装供应商协议，不包含全局选源或回退
│   ├── longbridge.py  # Longbridge 共享连接、失效冷却与静态信息缓存；只封装供应商协议，不包含全局选源或回退
│   ├── pytdx.py  # Pytdx 共享会话、主机轮询与连接冷却；只封装供应商协议，不包含全局选源或回退
│   ├── stockdb.py  # stockdb 跨能力共享的原 StockDbClient、settings、查询及本地源错误；只封装供应商协议，不包含全局选源或回退
│   └── tickflow.py  # TickFlow SDK 创建/关闭及跨能力缓存、权限状态；只封装供应商协议，不包含全局选源或回退
├── code_search/  # 代码/名称搜索；沿用现有能力目录
│   ├── __init__.py  # 代码/名称搜索包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 代码/名称搜索现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── eastmoney_source.py  # 东方财富的代码/名称搜索协议、分页和字段标准化；不承担跨厂商回退
│   ├── local_stockdb_source.py  # 本地 StockDB的代码/名称搜索协议、分页和字段标准化；不承担跨厂商回退
│   └── stocksdk_source.py  # StockSDK的代码/名称搜索协议、分页和字段标准化；不承担跨厂商回退
├── common/  # 公共取数机制；沿用现有能力目录
│   ├── __init__.py  # 公共取数机制包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 现有 DataSource、DataSourceManager；公共协议、选源与回退机制，保留能力级配置差异
│   ├── cache.py  # 共享 TTL 缓存机制；键、实例和失效范围由实际能力指定
│   ├── diagnostics.py  # 包内窄诊断回调及默认装配契约；不导入具体 application 诊断服务、不静默丢事件
│   ├── errors.py  # 源不可用、限流、取数失败等既有异常定义的单一事实源；保留旧异常身份
│   ├── execution.py  # 原预算扣减/重试/超时槽执行，状态和线程工厂窄回调，不新增重试层
│   ├── fetcher_contract.py  # 从根 base 提取 BaseFetcher 兼容契约；迁移期保留旧方法，随能力切片逐项退出，不继续扩张万能接口
│   ├── health.py  # 原健康探针及实时/筹码熔断；状态、锁与故障域保持独立，不合并单例
│   ├── normalize.py  # 协议格式标准化；纯股票代码规则直接依赖 domain，不回引 base
│   ├── rate_limit.py  # 限流注册及上下文；不改变既有配额和优先级
│   └── symbols.py  # 共享供应商代码适配，复用 domain 真源，不复制业务识别规则
├── fundamentals/  # 基本面；沿用现有能力目录
│   ├── __init__.py  # 基本面包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 基本面现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── aggregate.py  # CN/海外聚合、预算与板块块协调；直接加载唯一实现，原缓存/锁仍由资源所有者持有
│   ├── akshare_source.py  # akshare 已有基本面字段获取与源标准化；凭实际覆盖接入 aggregate，不假定所有源提供相同字段
│   ├── flow_source.py  # 资金流/龙虎榜块预算、超时及状态协调；原始厂商接口在同目录 AkShare Source，避免复制；不承担交易评价
│   ├── source_contract.py  # 基本面请求/结果与 Source 协议，base 再导出同一对象，避免具体源优先导入时回到默认注册表
│   ├── tushare_source.py  # 历史 tushare id/门控与来源标签保留，直接绑定独立多源聚合，不回调公开门面，不假定仅请求 Tushare
│   └── yfinance_source.py  # yfinance 已有基本面字段获取与源标准化；凭实际覆盖接入 aggregate，不假定所有源提供相同字段
├── institutional/  # 机构数据；沿用现有能力目录
│   ├── __init__.py  # 机构数据包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 机构数据现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── tw_client.py  # 迁入台湾机构 HTTP 查询和民国日期解析，tw_source 负责能力结果适配
│   └── tw_source.py  # 台湾机构的机构数据协议、分页和字段标准化；不承担跨厂商回退
├── kline/  # 分别承接分析日线与页面多周期 K 线，保留各自契约
│   ├── __init__.py  # 页面多周期 K 线包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 页面多周期 K 线现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── daily_akshare_source.py  # akshare 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_alphavantage_source.py  # alphavantage 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_baostock_source.py  # baostock 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_efinance_source.py  # efinance 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_finnhub_source.py  # finnhub 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_history.py  # 分析日线的优先级、市场路由、完整性与预取协调；保留 DataFrame/来源契约
│   ├── daily_longbridge_source.py  # longbridge 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_normalize.py  # 原 BaseFetcher 的日线字段清洗、排序与标准化；技术指标纯规则复用 domain，不能再造指标算法
│   ├── daily_pytdx_source.py  # pytdx 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tencent_source.py  # tencent 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tickflow_source.py  # tickflow 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_tushare_source.py  # tushare 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── daily_yfinance_source.py  # yfinance 的分析日线能力，承接旧 Fetcher 的 _fetch_raw_data/_normalize_data；需要时复用同厂商协议客户端，不复制页面 K 线分页逻辑
│   ├── eastmoney_source.py  # 东方财富的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── local_stockdb_source.py  # 本地 StockDB的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── sina_source.py  # 新浪的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── stocksdk_source.py  # StockSDK的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退
│   ├── tencent_source.py  # 腾讯的页面多周期 K 线协议、分页和字段标准化；不承担跨厂商回退；保持页面周期/复权契约，与分析日线不是直接替换关系
│   └── transform.py  # K 线排序、复权、StockDB 行归一、重采样与裁剪；保持单位和边界
├── limit_pool/  # 涨跌停池；沿用现有能力目录
│   ├── __init__.py  # 涨跌停池包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 涨跌停池现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── akshare_source.py  # 原 AkShare 涨跌停获取/排序/字段/节流，不改为新 HTTP 通道；现有 EastMoney 包装仍使用该原 SDK 能力
│   ├── eastmoney_source.py  # 东方财富的涨跌停池协议、分页和字段标准化；不承担跨厂商回退
│   ├── source_contract.py  # 原涨跌停 DTO/常量/Source 协议，具体源导入不触发默认注册
│   └── stocksdk_source.py  # StockSDK的涨跌停池协议、分页和字段标准化；不承担跨厂商回退
├── market/  # 市场快照、指数与统计原始数据；不包括市场分析用例
│   ├── __init__.py  # 全市场快照、指数与统计的公开取数入口，不包括市场分析用例
│   ├── eastmoney_source.py  # 原 clist 全市场快照；B14 卡片辅助在 indices/statistics，Session/缓存仍归 sector 原模块，不混用返回契约
│   ├── indices.py  # 按市场查询指数原始数据的能力协调，保留来源优先级
│   ├── snapshot.py  # 封装全市场快照能力；与现有 MarketSnapshotPort 对账，不能重复其外层回退
│   ├── statistics.py  # 市场涨跌家数等原始统计协调，不吸收市场策略
│   └── tencent_source.py  # 腾讯全市场快照取数及标准化，承接旧快照模块
├── news/  # 新闻；沿用现有能力目录
│   ├── __init__.py  # 新闻包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 新闻现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── wallstreetcn_live.py  # 迁入实时新闻频道目录、URL、scope 和响应解析；news Source 委托此实现
│   └── wallstreetcn_source.py  # 华尔街见闻的新闻协议、分页和字段标准化；不承担跨厂商回退
├── realtime/  # 实时行情；沿用现有能力目录
│   ├── __init__.py  # 实时行情包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 实时行情现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── akshare_source.py  # 保留现有能力包装，承接原 Fetcher 实时通道及缓存取数与标准化，不承担跨厂商回退
│   ├── alphavantage_source.py  # alphavantage 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── coordination.py  # 原分析实时路由/回退与单源尝试，保持市场、HK 参数、配置/锁/诊断
│   ├── efinance_source.py  # efinance 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── enrichment.py  # 缺字段补全、来源 token 和新鲜度；路由及失败诊断日志仍在原 Manager，不决定交易策略
│   ├── finnhub_source.py  # finnhub 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── longbridge_source.py  # longbridge 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── prefetch.py  # 批量实时预取及缓存写入，保留原调用预算、并发限制和实例作用域
│   ├── pytdx_source.py  # pytdx 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── source_contract.py  # 轻量实时 Source 协议，base 再导出同一对象，避免具体源导入默认注册表形成循环
│   ├── tickflow_source.py  # 保留现有能力包装，承接原 Fetcher 实时取数、预取和标准化，共用原客户端与缓存
│   ├── tushare_source.py  # tushare 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
│   ├── types.py  # 从 realtime_types 提取行情枚举、UnifiedRealtimeQuote 和标量转换；新旧导出保持类型身份
│   └── yfinance_source.py  # yfinance 的现有实时行情能力及字段转换；保留市场支持与凭据探测，不新增原来没有的能力
├── runtime/  # 包内装配与资源生命周期；进程级接线仍由 bootstrap 负责
│   ├── __init__.py  # 必要导出，不提前加载全部 SDK
│   ├── fetchers/  # 跨能力厂商装配门面，不复制 Source 或 Client
│   │   ├── __init__.py  # 厂商装配包入口，不批量创建实例
│   │   ├── akshare.py  # akshare 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── alphavantage.py  # alphavantage 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── baostock.py  # baostock 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── efinance.py  # efinance 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── finnhub.py  # finnhub 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── longbridge.py  # longbridge 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── pytdx.py  # pytdx 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── tickflow.py  # tickflow 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   ├── tushare.py  # tushare 构造、共享资源所有权与能力绑定；不承载能力算法
│   │   └── yfinance.py  # yfinance 构造、共享资源所有权与能力绑定；不承载能力算法
│   ├── fetcher_factory.py  # 默认源构造及可选依赖探测；保留原加载时机和配置优先级
│   └── manager.py  # DataFetcherManager；共享资源、锁、生命周期与能力入口协调
├── sector/  # 板块榜单；沿用现有能力目录
│   ├── __init__.py  # 板块榜单包入口，仅导出必要公共能力，不创建连接或启动任务
│   ├── base.py  # 板块榜单现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
│   ├── akshare_source.py  # 行业/概念/人气榜及原候选回退，复用原 SDK/节流
│   ├── coordination.py  # 行业/概念/人气/所属板块协调，显式接入原类级缓存和诊断，不传整个宿主
│   ├── eastmoney_source.py  # 东方财富的板块榜单协议、分页和字段标准化；不承担跨厂商回退；市场辅助已委托 market indices/statistics 唯一实现，原 Session/缓存保留，禁止保留两份算法
│   ├── efinance_source.py  # 行业排行及所属板块，复用原执行器/超时/SDK
│   ├── market_cards_source.py  # 现有行情卡片数据聚合与预热入口；取数协调与应用展示策略按调用方分界，不扩张 UI 职责
│   ├── shidaotec_source.py  # 世达科技行业、概念、ETF 与个股树图原始数据及源异常，不迁移页面组件
│   ├── source_contract.py  # 板块请求/结果及 Source 协议，隔离默认注册并保留 base 再导出身份
│   ├── stocksdk_source.py  # StockSDK的板块榜单协议、分页和字段标准化；不承担跨厂商回退；跨市场辅助已委托 market 唯一实现，原缓存与桥接 getter 保留，clients/stocksdk 已于 B19 归位
│   ├── tickflow_source.py  # 原 SW1 行业排行，复用同一 SDK/权限/实例缓存及锁
│   └── tushare_source.py  # 原行业排行与交易时间/配额，不新增概念或热股能力
└── stock_info/  # 股票信息；沿用现有能力目录
    ├── __init__.py  # 股票信息包入口，仅导出必要公共能力，不创建连接或启动任务
    ├── base.py  # 股票信息现有请求、结果、Source 契约及 Manager 入口；不强制为凑文件数再拆 models/service
    ├── catalog.py  # 三厂商公开股票清单与 Pytdx 内部分页，复用原 SDK/缓存；索引持久化沿用外层流程，不写应用数据库
    ├── eastmoney_source.py  # 东方财富的股票信息协议、分页和字段标准化；不承担跨厂商回退
    ├── local_stockdb_source.py  # 本地 StockDB的股票信息协议、分页和字段标准化；不承担跨厂商回退
    ├── name_lookup.py  # 单个/预取/批量名称协调和七厂商精确查询，原缓存所有权保持，不将搜索和精确查询混为一体
    ├── stocksdk_source.py  # StockSDK的股票信息协议、分页和字段标准化；不承担跨厂商回退
    └── tencent_source.py  # 腾讯的股票信息协议、分页和字段标准化；不承担跨厂商回退
```

本轮目标快照为 **137 个 Python 文件、19 个下级目录**。这是路径对账结果，不是文件数量考核；后续只有实际职责或契约证据才可调整，调整时同步本树、§11.3 和验收映射。

根目录目标从 **24 个 Python 文件收敛到 2 个**。这是职责清楚后的目标形态，不是删除文件的硬指标。保留 `base.py` 是为了集中兼容常用的 BaseFetcher / DataFetcherManager 等公开导入；包内生产模块应直接使用契约、能力或运行模块，不再经 `base.py` 聚合。`common/symbols.py` 只接收确有共享调用的纯适配；单源转换仍留该源，已有 `common/normalize.py` 的职责不另抄一份。

腾讯日线的唯一类实现已经在 `kline/daily_tencent_source.py`，无需为了对齐厂商名单再造 `runtime/fetchers/tencent.py`。只有真实跨能力装配或资源共享才进入 `runtime/fetchers/`。同样，不新增 `legacy/`、`compat/`、`misc/` 收纳箱，也不把旧 Fetcher 整体改名 Client 后直接塞进 `clients/`。

<a id="root-file-destinations"></a>
### 11.3 原 24 个根文件的逐文件决定

截至 R4，22 个旧根模块路径已退出，两个根入口保留；完整目标树与磁盘路径一致。下表记录原 24 文件的迁移决定，路径均相对 `data_provider/`。删除旧路径的前提是同批更新运行代码、动态导出、测试 patch、脚本与打包引用；若发现实际持久化模块路径，先记录消费者和迁移办法。

| 当前根文件 | 下一轮落点 | 旧路径的最终处理 |
| --- | --- | --- |
| `__init__.py` | 原位，注册改为新规范路径 | 保留 17 项导出及惰性加载行为 |
| `base.py` | 管理器迁 `runtime/manager.py`；契约沿用 `common/fetcher_contract.py`；规则复用 domain 或能力目录 | 原位仅保留明确公开的薄转导出；私有符号按真实使用迁移 |
| `akshare_fetcher.py` | `runtime/fetchers/akshare.py`；残余请求/转换先依职责归位 | 调用方迁移后删除，不再留同名空壳 |
| `alphavantage_fetcher.py` | `runtime/fetchers/alphavantage.py` | 同上 |
| `baostock_fetcher.py` | `runtime/fetchers/baostock.py` | 同上 |
| `efinance_fetcher.py` | `runtime/fetchers/efinance.py`；协议与 DTO 按下表处理 | 同上 |
| `finnhub_fetcher.py` | `runtime/fetchers/finnhub.py` | 同上 |
| `longbridge_fetcher.py` | `runtime/fetchers/longbridge.py`；认证/协议辅助迁现有 client | 同上 |
| `pytdx_fetcher.py` | `runtime/fetchers/pytdx.py`；连接协议辅助迁现有 client | 同上 |
| `tickflow_fetcher.py` | `runtime/fetchers/tickflow.py`；转换/日线/缓存访问按职责处理 | 同上 |
| `tushare_fetcher.py` | `runtime/fetchers/tushare.py`；HTTP 地址等协议辅助迁现有 client | 同上 |
| `yfinance_fetcher.py` | `runtime/fetchers/yfinance.py` | 同上，不为归类新建无收益的 Yfinance Client |
| `eastmoney_quote_snapshot.py` | 已有 `market/eastmoney_source.py` | 更新消费者后删除旧转导出 |
| `tencent_quote_snapshot.py` | 已有 `market/tencent_source.py` | 更新消费者后删除旧转导出 |
| `fundamental_adapter.py` | 已有 `fundamentals/akshare_source.py` | 更新消费者后删除旧转导出 |
| `yfinance_fundamental_adapter.py` | 已有 `fundamentals/yfinance_source.py` | 更新消费者后删除旧转导出 |
| `realtime_types.py` | DTO 用已有 `realtime/types.py`；熔断器用已有 `common/health.py` | 拆开消费者实际依赖后删除，不复制状态对象 |
| `stockdb_fetcher.py` | 已有 `clients/stockdb.py` | 更新消费者后删除旧模块别名 |
| `stocksdk_bridge.py` | 已有 `clients/stocksdk/bridge.py` | 更新消费者后删除旧模块别名 |
| `tencent_fetcher.py` | 已有 `kline/daily_tencent_source.py` | 删除旧转导出；顶层 TencentFetcher 仍惰性导出同一个类 |
| `tw_institutional_fetcher.py` | 已有 `institutional/tw_client.py` | 更新消费者后删除旧模块别名，保留能力 Source 的注入行为 |
| `wallstreetcn_calendar_fetcher.py` | 已有 `calendar/wallstreetcn_source.py` | 更新消费者后删除旧模块别名 |
| `wallstreetcn_live_news_fetcher.py` | 已有 `news/wallstreetcn_live.py` | 更新消费者后删除旧模块别名 |
| `us_index_mapping.py` | 映射与识别直接使用 `src.domain.market.us_index_symbols`；Yahoo 查询适配迁 `common/symbols.py` | 更新消费者后删除；顶层映射、识别、查询导出继续指向唯一对象/函数 |

<a id="root-internal-split"></a>
### 11.4 文件内部也要收敛，不能只换文件夹

| 目前残余职责 | 推荐归属与处理 |
| --- | --- |
| AkShare 实时量额解析、实时错误文案 | `realtime/akshare_source.py`；核对 A/H 股单位及错误分类，不移动到通用运行管理器 |
| AkShare 超时调用、进程 worker 与清理 | 现有 `clients/akshare/client.py`；保留超时与子进程清理，实际验证 spawn 及冻结环境可定位 worker |
| Efinance 超时调用与东财协议辅助 | 现有 `clients/efinance.py`；日线与实时各自的错误语义由对应 Source 保留 |
| `EfinanceRealtimeQuote` 旧 DTO | 核实消费契约后迁 `realtime/efinance_source.py`；不直接替换为字段可能不同的 UnifiedRealtimeQuote，不增加第二份 DTO |
| Longbridge OAuth、凭据、缓存文件和连接协议辅助 | 现有 `clients/longbridge.py`；资源仍只由单一 Fetcher 所有，不复制配置或 token 缓存 |
| Pytdx 主机配置解析；Tushare HTTP 地址解析 | 分别进入现有 `clients/pytdx.py`、`clients/tushare/http.py`；配置名称、默认值与解析时机不变 |
| TickFlow 日线整理、日期范围与截断判断 | 现有 `kline/daily_tickflow_source.py`；行情百分比/量额转换进相应实时/板块能力，跨能力协议转换才进入 `clients/tickflow.py` |
| TickFlow 缓存与能力权限状态 | 维持原共享作用域和所有者，能力实现通过窄接口读写；不让每个 Source 新建一份缓存或权限状态 |
| Manager 的市场识别、板块标准化等纯逻辑 | 先与 domain 及 `sector/coordination.py` 核对等价性再复用或提取；不同输入容错不可仅因名字相似合并 |
| 通用规范化与 StockSDK 对 `base.py` 的反向依赖 | 直接依赖 `src.domain.market.stock_codes`；`common` 与 `clients` 不经运行装配层获得纯函数 |

运行门面可以保留必要的显式能力委托，但不得继续积累数据解析、业务判断或大量为满足旧测试私有 patch 而保留的转换方法。反过来，也不能为减少回调数把整个 Manager/Fetcher 作为万能宿主传入 Source。

<a id="root-execution-plan"></a>
### 11.5 分批执行与验收

**当前状态：R0–R5 全部完成，15/15（100%）。Docker 镜像、17 导出/136 子模块、UID 1000 正式入口、健康与 Web 首页 200 均已通过；原跨平台/桌面窗口缺口独立保留。**

执行依赖为 R0 → R1 → R2 → R3a–R3j → R4 → R5。R3 按下表顺序逐源推进，每个源独立迁移、验证和记录；不得一次性搬完十个源后再找共同失败原因。

| 工作包 | 本批具体动作与交付 | 验证及完成条件 | 状态 |
| --- | --- | --- | --- |
| R0 | 记录当时 HEAD/工作区，刷新 24 根文件、17 公开导出、工厂、动态引用、序列化与扩展覆盖清单；为审计脚本登记旧符号到新路径的映射方案 | 新旧路径及消费者逐项对应，记录既有失败与环境缺口；保留用户及并行任务改动 | 已完成 |
| R1 | 修正 common/normalize、StockSDK bridge 对 base 的反向依赖；迁移指数查询和共享符号适配及其调用方，退出 us_index_mapping 旧路径 | 市场代码边界、查询返回值、映射对象身份、包级惰性导出、依赖检查通过 | 已完成 |
| R2 | 迁移 §11.3 的 11 个薄兼容入口全部消费者，更新惰性导出和测试 patch，删除对应旧文件 | 状态/异常/类型只有一个真源；独立导入与相关能力测试通过；旧运行引用清零 | 已完成 |
| R3a | AlphaVantage 门面迁 runtime/fetchers/alphavantage.py；同步工厂与调用方 | 日线、实时、名称、凭据缺失及可选依赖路径保持 | 已完成 |
| R3b | Finnhub 门面迁 runtime/fetchers/finnhub.py；同步工厂与调用方 | 日线、实时、名称、凭据缺失及失败行为保持 | 已完成 |
| R3c | Baostock 门面迁移，剩余共享会话辅助归 clients/baostock.py | 登录/登出、日线、清单、异常清理与资源所有权保持 | 已完成 |
| R3d | Yfinance 门面迁移，能力解析留既有 Source，不新增平行 Client | 多市场日线、实时、名称、基本面与时间/单位边界保持 | 已完成 |
| R3e | Pytdx 门面迁移，主机与连接协议辅助归现有 Client | 主机切换、冷却、日线/实时/清单及关闭行为保持 | 已完成 |
| R3f | Tushare 门面迁移，地址解析/认证协议辅助归现有 Client | SDK/HTTP 选择、配额、日线/筹码/板块及可选启用条件保持 | 已完成 |
| R3g | Efinance 门面迁移；超时协议归 Client，旧 DTO 及行情解析归能力 | 日线/ETF/实时报价/清单/板块、量额及旧 DTO 字段契约保持 | 已完成 |
| R3h | Longbridge 门面迁移；OAuth、缓存文件及连接协议归现有 Client | 原凭据模式、token 缓存、懒连接、冷却、日线/实时与关闭保持 | 已完成 |
| R3i | AkShare 门面迁移；实时解析归能力，超时 worker/清理归 Client | 日线/实时/基本面/筹码/板块/涨跌停相关路径及子进程超时清理保持；冻结 worker 可定位 | 已完成 |
| R3j | TickFlow 门面迁移；日线整理/截断归日线，实时/板块转换归对应能力 | 批预取、缓存键/作用域、权限状态、限额与关闭保持，无额外 SDK 实例 | 已完成 |
| R4 | 管理器迁 runtime/manager.py；纯规则归位；base 仅保留明确公共面，所有内部消费者改用规范路径 | 优先级、市场路由、可选源、资源关闭、并发锁和应用消费保持；无循环导入 | 已完成 |
| R5 | 对账完整目标树、24 根文件去向、公开导出、审计脚本、工厂/脚本/工作流与验收附件 | 相关固定/随机序测试、完整后端门禁、源码与干净环境冻结全包导入通过；Docker/桌面/跨平台各自如实记录 | 已完成：本轮必需验收通过，Linux/ARM64 容器验收及清理完成 |

**进度计算**：15 个工作包等权，已完成且验证通过的工作包数 / 15；每完成一个约增加 6.7 个百分点，使用实际分数计算后四舍五入。该比例表示工作包完成率，不表示耗时或 token 消耗比例。文档更新不计为 R0 完成，R3 任一源未过本批验证不得提前计入；R5 存在必需验收阻塞时保持未完成。

每批同步：`本轮进度 X/15（Y%）｜当前工作包｜验证结果｜剩余阻塞｜下一步`。记录追加到既有架构流水，测试证据同步现有测试台账，逐文件契约/路径和最终结果同步验收附件，不另建平行进度文档。

验证入口沿用 §8。优先完成本批有实际风险的现有能力测试；全局门禁放在 R5 或确有跨源影响时执行。旧模块路径删除时同步审计映射、工厂、动态导出、测试 patch 与打包引用；不能降低断言、清空旧基线或新增 skip 换取通过。

实施时还需注意：

- `scripts/check_provider_contracts.py` 的旧基线与旧路径有历史审计用途。迁移后保留“旧契约 → 新路径”映射，不能仅删掉不再命中的检查就宣称兼容通过；明确删除的旧模块路径属于本轮受控内部变更。
- 原包级 `from data_provider import ...` 公共导出保留，内部模块改路径不要求修改 Web 页面、API 字段、数据库或配置。若新增观察到这些行为变化，应暂停该切片并单列契约变更。
- PyInstaller 已收集整个 data_provider 包，仍需真实冻结加载新路径及可选源；跨平台、Docker 和桌面端故障以实际结果分别记录。用户已注释 Pro CSS 导入，旧 Docker 失败仅是该次记录，后续状态必须以重新构建为准。
- 每批同时迁移实现、工厂、调用方和测试，回滚亦以该批完整恢复；不覆盖本机数据、凭据、用户前端修改或其他并行文档。
- 新增工作按 R0–R5 独立报告阶段与完成比例，不用改写 B00–B23 的历史进度表示本节已经执行。

本节为中文内部设计及实施记录，没有对应英文版本；未修改 README。生产代码、调用方、测试、脚本与结构 ADR 已同步。最终随机序完整门禁 5866 passed / 1 skipped / 4 deselected / 511 subtests（386.15s），固定序相关检查 634 passed；243 代码对象签名、冻结 17 导出/136 子模块、冻结 worker 与健康 200 均通过。验收附件 §7 记录完整证据；Docker 的前序 502 已通过有限安装重试恢复；以校验后的本地官方镜像上下文完成构建及容器验收，R5 已完成。


<a id="root-next-step"></a>
### 11.6 最终交接与后续边界

- 已完成：137 个 Python 文件/19 下级目录与本节目标逐项一致；22 旧根路径退出，两个根入口保留；10 厂商门面、Manager 与残余职责归位；原公开包导出、状态/资源所有权及行为契约有审计和测试证据。
- 验收通过：固定序相关检查、seed=20261106 完整后端门禁、独立干净依赖、全包源码/冻结导入、ARM64 冻结构建/签名、冻结 spawn worker 与临时 DB 健康接口；scripts/test.sh 深路径和 CI 递归语法检查同步。
- Docker 新增验收已关闭：系统包安装首次失败后最多重试 3 次，持续失败仍中止；17 项部署/打包回归与 Dockerfile 检查通过。镜像使用本地官方基础镜像 OCI 输入构建，容器 17 导出/136 子模块、依赖一致性、UID 1000、健康/首页 200 通过，仅清理自己的验收容器及匿名卷。常规标签解析仍依赖本机镜像加速地址/网络，本轮未更改这些全局配置。
- 既有独立缺口：Windows、Intel、桌面窗口端到端仍按原 B23 记录；前端全量 lint 继续暂缓。本轮没有新增这些平台的通过结论。
- 回滚：按本节逐文件映射同批恢复旧模块及所有消费者、工厂/公开导出、审计、测试、脚本与能力提取；勿 reset 整个工作区或覆盖维护者 CSS/并行文档、用户数据和凭据。未 commit/push/tag。
