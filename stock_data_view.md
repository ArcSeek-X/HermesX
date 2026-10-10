# 本地 StockDB 数据视图看板 · 建设方案

> 文档状态：方案（未实现） · 目标仓库：HermesX
> 外部数据源：StockDB（本地服务 `127.0.0.1:7899`，数据目录 `stockdb/data`）
> 参考页面：`stockdb/调用方式/ai_自动开发文档/示范.html`
> 作者：高仓雄（gaocangxiong）
> 更新时间：2026-10-06
> **架构决策基准（本方案为遵守者）**：**`backend_architecture_adr.md`（ADR-001）** 是 HermesX 后端的**全局架构决策基准**（四层架构、`data_provider` 唯一脏活层、基础能力统一数据源策略），面向整个后端工程，不隶属于本方案。本方案是 ADR-001 的**遵守者 / 首个落地方案**：在"接入本地 StockDB（`127.0.0.1:7899`）作为 K 线 / 基础信息 / 代码搜索三类能力的 `local` source"这一范围内，严格遵循 ADR-001 的分层、脏活层与统一数据源约束；凡本方案与 ADR-001 不一致处，以 ADR-001 为准。方案范围已由「本地 StockDB 浏览页」升级为「行情基础能力统一层（多源可切换）」。

---

## 0. 浏览目录

- [1. 背景与目标](#1-背景与目标)
  - [1.1 背景](#11-背景)
  - [1.2 三个前置问题的结论](#12-三个前置问题的结论)
  - [1.3 目标与非目标](#13-目标与非目标)
  - [1.4 验收标准](#14-验收标准)
- [2. 数据源与接口契约](#2-数据源与接口契约)
  - [2.1 数据源定位](#21-数据源定位)
  - [2.2 HTTP 协议契约（已实测）](#22-http-协议契约已实测)
  - [2.3 表结构与字段](#23-表结构与字段)
  - [2.4 协议边界（不得越界）](#24-协议边界不得越界)
- [3. 系统架构与分层](#3-系统架构与分层)
  - [3.1 分层视图](#31-分层视图)
  - [3.2 解耦策略（关键）](#32-解耦策略关键)
  - [3.3 对宿主仓库的改动点（均为纯新增）](#33-对宿主仓库的改动点均为纯新增)
  - [3.4 与既有"外部 HTTP 服务对接"范式的一致性](#34-与既有外部-http-服务对接范式的一致性)
- [4. 数据库说明和设计](#4-数据库说明和设计)
  - [4.1 StockDB 侧（外部，只读）](#41-stockdb-侧外部只读)
  - [4.2 HermesX 侧（本仓库，零建表）](#42-hermesx-侧本仓库零建表)
  - [4.3 容量与性能约束](#43-容量与性能约束)
- [5. 后端接口规格](#5-后端接口规格)
- [6. 数据查询流程](#6-数据查询流程)
  - [6.1 主流程](#61-主流程)
  - [6.2 复权计算流程](#62-复权计算流程)
  - [6.3 周期聚合规则](#63-周期聚合规则)
  - [6.4 全市场 / 大范围查询](#64-全市场--大范围查询)
  - [6.5 失败与降级](#65-失败与降级)
  - [6.6 缓存策略](#66-缓存策略)
- [7. 前端设计](#7-前端设计)
  - [7.1 页面位置与路由](#71-页面位置与路由)
  - [7.2 布局](#72-布局)
  - [7.3 交互规则](#73-交互规则)
  - [7.4 列渲染与字段映射](#74-列渲染与字段映射)
  - [7.5 组件复用清单](#75-组件复用清单)
  - [7.6 状态机](#76-状态机)
- [8. 边界条件与空态](#8-边界条件与空态)
  - [8.1 参数边界](#81-参数边界)
  - [8.2 数据边界（必测）](#82-数据边界必测)
  - [8.3 空态与错误态文案](#83-空态与错误态文案)
- [9. 配置项](#9-配置项)
- [10. 风险、合规与回滚](#10-风险合规与回滚)
  - [10.1 风险清单](#101-风险清单)
  - [10.2 合规约束](#102-合规约束)
  - [10.3 回滚方式](#103-回滚方式)
- [11. 命名规范](#11-命名规范)
  - [11.1 后端](#111-后端)
  - [11.2 前端](#112-前端)
  - [11.3 菜单与路由](#113-菜单与路由)
  - [11.4 前端缓存注意](#114-前端缓存注意)
- [12. 测试与验证现状](#12-测试与验证现状)
  - [12.1 已完成的前置验证](#121-已完成的前置验证)
  - [12.2 待实施时补充的测试](#122-待实施时补充的测试)
  - [12.3 验证缺口](#123-验证缺口)
- [13. 核心实现代码（前后端）](#13-核心实现代码前后端)
  - [13.1~13.16 后端/前端骨架与落地顺序](#131161-后端前端骨架与落地顺序)
- [14. 修改范围](#14-修改范围)
- [附录 A. 文档信息与变更日志](#附录-a-文档信息与变更日志)
  - [A.1 文档信息](#a1-文档信息)
  - [A.2 契约事实来源](#a2-契约事实来源)
  - [A.3 变更日志](#a3-变更日志)
- [架构决策记录 ADR-001（独立文档）](./backend_architecture_adr.md) —— 后端分层 / 统一数据源策略的权威依据

---

## 1. 背景与目标

### 1.1 背景

StockDB 是一套**独立部署的本地股票数据库**：自带服务进程（`stockdb-server`，默认 `127.0.0.1:7899`）、自带数据目录（`stockdb/data`，LevelDB/LGDB 分片 `*.ldb`）、自带同步程序（`数据更新.app`）。官方示例 `示范.html` 是**纯静态页 + 浏览器直连 7899** 的形态。

HermesX 目前没有"直接查看本地全量历史行情（日K/分钟K/周月K/复权）"的页面，需求是把该能力搬进 HermesX Web 控制台，作为独立功能页存在。

### 1.2 三个前置问题的结论

| 问题 | 结论 |
|---|---|
| ① 能结合本地数据源 `stockdb/data` 做出来吗？ | **能**。`data/` 由 StockDB 服务进程独占管理，HermesX **不直接读文件**，统一走 HTTP 接口。已实测：`cmd=get&t=日k:600633:20260729&json=1` 正常返回 JSON。 |
| ② `stockdb/` 下是否有可复用代码？ | **有**：`pybao/stock_sdk.py` + `stockdb.abi3.so`（Python SDK `rd`/`bk`/`zb`，实测 Python 3.11 可 import 并打印 URL）、`http/http_api.py`（HTTP 范式）、`ai_自动开发文档/gp.js`（JS SDK，已混淆不可读改）。<br>**本方案不复用任何代码文件**，只复用**协议与表结构约定**（§2），理由见 §3.2。 |
| ③ 如何结合而不耦合？ | 见 §3 与 **ADR-001**：统一基础能力层（K 线 / 基础信息 / 代码搜索），`data_provider` 为唯一脏活层；StockDB 作为统一层的 `local` source，不另立独立包；不 import 业务 service/repository/model，不写 HermesX 主库。 |

### 1.3 目标与非目标

**目标**：① 新增「本地行情」页面，支持代码 + 日期区间 + 周期 + 复权查询与表格展示；② 代码联想（含名称）与个股交易日联想；③ 板块查询与成分股；④ 导出 CSV；⑤ 数据源不可用时进入明确空态，不影响 HermesX 既有功能。

**非目标（一期）**：① 不做 K 线画图（`tu.js` 混淆不可移植，自研 Canvas 绘图单独立项）；② 不做技术指标计算（39 种指标属 StockDB 侧 `zb_core` 能力）；③ 不做在线行情/财务数据（`get_price`/`get_fundamentals` 有批量限制与封禁风险）；④ 不做行情落库与定时同步。

### 1.4 验收标准

| 编号 | 标准 |
|---|---|
| AC-1 | `/stock-data` 可访问，菜单可见，中/英/繁三语言文案齐全 |
| AC-2 | `600633` + 区间 + `1d` + `qfq`，返回行数与官方 `gp.js` 一致 |
| AC-3 | `qfq` 结果与官方前端逐行对账误差 ≤ `1e-6`（≥3 只有送转史标的 + 1 只无除权标的） |
| AC-4 | 分钟K 可查；`5m/15m/30m/60m/1w/1M` 聚合与手工核算一致 |
| AC-5 | StockDB 未启动时页面显示空态，HermesX 其余功能不受影响 |
| AC-6 | `STOCKDB_ENABLED=false` 时，K 线等端点按 ADR-001 回退其他源或返回空态（不再有 `/api/stockdb/*` 503 路径），`/api/v1/*` 其余功能不受影响 |
| AC-7 | 全市场某日快照请求数 ≤ 5，单次响应 ≤ `STOCKDB_MAX_ROWS` |

---

## 2. 数据源与接口契约

### 2.1 数据源定位

| 项 | 值 |
|---|---|
| 服务 | StockDB 本地服务进程（`stockdb-server`） |
| 地址 | `http://127.0.0.1:7899`（可配置） |
| 数据目录 | `<stockdb>/data`（`*.ldb` 分片，服务独占） |
| 私有写目录 | `<stockdb>/mydb`（本方案不使用） |
| 配置 | `<stockdb>/stockdb.conf`（`server.port: 7899`） |
| 数据更新 | `数据更新.app`，同步源见 `<stockdb>/sync_url.txt` |
| 实测最新交易日 | `20260924` |

### 2.2 HTTP 协议契约（已实测）

```
GET http://127.0.0.1:7899/?cmd=<cmd>&t=<table>&k1=<expr>&k2=<expr>&ap=<ap>&num=<num>&json=1
```

| 参数 | 说明 |
|---|---|
| `cmd` | `get`（键值对）/ `vals`（值集合）/ `keys`（键集合）/ `len`（计数） |
| `t` | 表名，支持前缀通配（`退市*`、`板块*`） |
| `k1`/`k2` | 键表达式，见下表 |
| `ap` | 服务端字段投影 `ap=get.date,close` → 位置数组 `[[20260729,10.54],...]` |
| `num` | 服务端切片：`num=3` 前 3 条，`num=-3` 后 3 条 |
| `json=1` | **必须**，新版服务端不带此参数不返回 JSON |

**键表达式语法**（用官方 SDK `QueryResult.url()` 反查确认）：

| 表达式 | 含义 | SDK 写法 | URL 片段 |
|---|---|---|---|
| `key:600633` | 精确 | `rd.vals("日k","600633","20260729")` | `k1=key:600633` |
| `qz:6` | 前缀（去掉 `*`） | `rd.vals("日k","6*","20260729")` | `k1=qz:6` |
| `qz:2026072` | 日期前缀 | `rd.vals("日k","600633","2026072*")` | `k2=qz:2026072` |
| `all:` | 整层全匹配 | `rd.vals("日k","600633","*")` | `k2=all:` |
| `fwd:A,B` | 闭区间 | `rd.vals("日k","600633","20260720<20260726")` | `k2=fwd:20260720,20260726` |
| `fwz:A,B` | 同区间反序 | `rd.vals("日k","600633","20260720>20260726")` | `k2=fwz:20260720,20260726` |
| `fwd:A,N` | 开放区间 | `rd.vals("日k","600633","20260720<N")` | `k2=fwd:20260720,N` |

> **实测结论**：`fwd:` 区间返回**倒序**（`20260729, 20260728, ...`），`all:` 返回**升序**。
> 因此**后端必须按 `date` 显式重排序**，不得依赖服务端顺序（见 §8.2）。

### 2.3 表结构与字段

**`日k : code : YYYYMMDD -> dict`**

```json
{"date":20260729,"code":"600633","name":"浙数文化","open":10.23,"high":10.58,"low":10.18,
 "close":10.54,"pre_close":10.21,"volume":25741300,"amount":267740000,"turnover":2.03,
 "pct_chg":3.23,"amplitude":3.92,"is_st":false,"vol_ratio":1.02,
 "total_share":1268074472,"float_share":1268074472,
 "total_mv":13366000000,"float_mv":13366000000,"pe_ttm":22.7,"pb":1.29}
```

**`分钟k : code : YYYYMMDDhhmmss -> dict`**

```json
{"code":"600633","date":20260727112900,"open":10.24,"close":10.24,
 "high":10.24,"low":10.23,"volume":27000,"amount":276465}
```

> 分钟K **无** `name`/`pct_chg`/市值类字段，前端列必须按字段存在性动态生成（§7.4）。

**`复权 : code : YYYYMMDD -> dict`**

```json
{"div":0.17,"give":0,"trans":0,"mult":1.016,"cum":5.649}
```

`div` 每 10 股派息（元）、`give` 每 10 股送股、`trans` 每 10 股转增、`mult` 当次系数、`cum` 累计系数。

**`股票代码 -> dict`**：按首字符分组的六位代码数组。A 股股票取 `0`/`3`/`6`；`1`/`5` 含基金债券，`9` 含北交所，是否纳入由 `market` 参数决定。

**`板块* -> list[dict]`**（表名为前缀，须 `cmd=vals&t=板块*`）

```json
{"code":"309265.TI","name":"2026一季报预增","source":"ths","type":"concept",
 "group":"特色指数列表","category":"概念","symbols":["000061","000062"]}
```

**`退市*`**：退市证券代码列表。

### 2.4 协议边界（不得越界）

1. 只走 `127.0.0.1:7899` 的 HTTP 端口，**不得直接读取 `data/*.ldb`**。
2. 只读幂等（`cmd` 只用 `get/vals/keys/len`），**不写 `mydb`**。
3. 全市场扫描只允许按 `qz:` 前缀分片（≤5 个请求），**禁止逐股循环**。
4. 单次返回行数必须受 `STOCKDB_MAX_ROWS` 限制。

---

## 3. 系统架构与分层

### 3.1 分层视图（权威依据见 ADR-001 §4）

本方案的后端分层与统一数据源策略以 **`backend_architecture_adr.md`（ADR-001）** 为**唯一权威基线**。四层架构（数据库层 / 接口对接层（脏活层）/ 功能接口层 / 横切基础辅助层）、各层职责、目录落点、调用链路与端点模型**均见 ADR-001 §3–§5**，本方案不再复述。

> **范围澄清（与 ADR-001 一致）**：本方案的"四源平等 + 自动回退 + 周期全集 + 统一契约"策略**仅约束 `K 线 / 基础信息 / 代码搜索` 三类基础能力**；实时行情（akshare / tickflow）、板块（eastmoney）、财务基本面（tushare）、新闻资讯（wallstreetcn）、机构持仓（tw_institutional）等其余功能仍按各自既定专属源接入，不受四源平等约束，亦不受本方案改造影响。三类能力的"四源平等"实现完全封装在 `data_provider/kline/*`、`stockinfo/*`、`codesearch/*` 各自文件内，不影响项目中其他使用数据源的地方。能力源归属详见 ADR-001 §4.5 / §4.4。

> **架构升级说明（StockDB 接入方式）**：原方案「独立 `/api/stockdb` 页 + 独立包 `src/integrations/stockdb/`」的设计已被 **ADR-001** 取代——StockDB 不再是独立页面 / 独立包，而是统一基础能力层的一个 `local` source。本方案中任何 `/api/stockdb/*` 路由前缀与 `src/integrations/stockdb/` 包路径均为**占位**，以 ADR-001 的目录决策为准；其请求 / 响应契约仍作为统一 `KLinePoint` / `StockInfo` / `CodeSearch` 契约有效（见 §5）。



### 3.2 解耦策略（关键）

| 维度 | 做法 | 为什么不用另一种 |
|---|---|---|
| **代码** | 所有源对接代码下沉到 `data_provider/`（含新增 `stockdb_fetcher` 与 `kline/stockinfo/codesearch` 子包），只依赖 `requests` + 标准库 | 不用 `pybao/stock_sdk.py`：会把 `stockdb.abi3.so` 拉进 HermesX 进程，引入外部二进制、Python 版本与部署形态约束 |
| **协议** | 只复用 §2.2 的 HTTP 文本协议 | 不用 `gp.js`：混淆不可维护，且是浏览器直连形态 |
| **路由** | 复用既有 `api/v1/kline` 端点（瘦端点化），新增 `api/v1/stock-info`、`api/v1/code-search` 同属 `/api/v1` | 不再另立 `/api/stockdb` 独立前缀；统一继承 `ADMIN_AUTH`（属管理后台能力，合理），且前端零改动 |
| **数据** | HermesX 主库**零新增表**，只做进程内 TTL 缓存 | 行情体量大（单股日K 实测 5444 条，全市场 GB 级）；StockDB 数据有独立许可边界 |
| **依赖** | 各 source 只依赖 `data_provider` 基类与 `config`，不 import 业务 `src/services/*`、`src/repositories/*`、`src/core/*` | 保证能力可独立增删、不污染既有分析层（stock_service / 组合风险 / 预警 / 回测等） |
| **故障** | `STOCKDB_ENABLED=false` 或本地源失败 → 按 `KLINE_SOURCE_PRIORITY` 自动回退其他源 / 返回空态 | StockDB 不可用不得影响主流程、调度、报告、通知 |
| **切换** | 数据源由配置 `KLINE_DATA_SOURCE` 等驱动，「设置 → 数据源」Tab 可改、无需重启 | 消除原 `kline.py` 硬编码三级降级（东财→腾讯→新浪）的不可配置问题 |

> 说明：复用 `/api/v1/kline` 意味着 K 线接口继承 `ADMIN_AUTH`（原方案为避开鉴权而用 `/api/stockdb` 独立前缀，此取舍在 ADR-001 中被有意反转）。若后续确须无鉴权暴露本地行情，可再评估独立前缀，但默认不采用。

### 3.3 对宿主仓库的改动点

**后端**
1. `api/app.py`：无需新增 `include_router`（复用既有 `api/v1/kline` 路由）；若新增 `stock-info` / `code-search` 端点，则各加 1 处 `include_router`。
2. `src/config.py`：新增数据源切换配置（`KLINE_DATA_SOURCE` / `KLINE_FALLBACK_ENABLED` / `KLINE_SOURCE_PRIORITY` 等，§9）+ StockDB 连接配置（§9，沿用 `_FALSEY_ENV_VALUES`）。
3. `data_provider/`：新增 `stockdb_fetcher.py` 与 `kline/`、`stockinfo/`、`codesearch/` 三套能力子包（base + N source + transform）。
4. `api/v1/endpoints/kline.py`：瘦端点化，删除内联 `_fetch_from_*`，改调 `KlineDataSourceManager`。
5. `.env.example`：新增配置块（§9）。

**前端**
1. `src/router/manifest.ts`：K 线菜单保留；新增「设置 → 数据源」Tab 节点（或复用既有 `/settings`）。
2. `src/pages/StockDataViewPage.tsx`：保留（K 线页，数据源可配）。
3. `src/api/stockdb.ts`：改为调用 `/api/v1/kline` 等（或并入既有 kline API 模块）。
4. `src/i18n/uiText-{zh,en,zh-Hant}.ts`：补充「数据源设置」相关 key。
5. 新增「数据源配置」页面 / 组件（参考既有 `SettingsPage`）。

### 3.4 与既有"外部 HTTP 服务对接"范式的一致性

`src/services/stock_index_remote_service.py` 是仓库内对接外部 HTTP 的既有范式：`@dataclass(frozen=True) Settings` + `settings_from_config(config)` + `requests.get(url, timeout=...)` + 失败计数/熔断 + 原子写缓存。本方案的 `data_provider` 各 source 沿用同一形状（ADR-001 D2/D3），并复用 `DataFetcherManager` 思想（能力过滤 + 优先级 + 健康度故障转移），但针对 K 线多周期与 UI 契约做独立抽象，避免与日线分析层耦合。

---

### 3.5 Python 标准化目录结构与命名规范（代码落地模板）

> 目录结构与命名公约（四层落点、`snake_case` 模块、`<source>_source.py` / `<Source>DataSource` 类、`__init__.py` 等）以 **ADR-001 §4.4 / §4.5** 为唯一权威，本方案不再复述。以下仅补充 StockDB 接入引入的**增量命名决定**。

#### 3.5.1 新增能力子包的命名决定（消除 `*fetcher` vs `*source` 歧义）

为避免同目录两套语义混淆，明确边界：

- **既有顶层 `data_provider/*_fetcher.py`** = "日线/指标取数器"，被分析层（`stock_service`/组合风险/回测等）消费，**保留不动**。
- **新增三类能力子包**（`kline/` `stockinfo/` `codesearch/`）内，适配器文件统一用 `<source>_source.py`，类名 `<Source>DataSource`；基类 `KlineDataSource(ABC)` 与 `KlineDataSourceManager` 放 `base.py`。
  - 理由：子包是"面向 UI 的统一数据源能力"，用 **DataSource** 概念更贴切；与顶层"日线 Fetcher"区分，避免同一 `data_provider/` 下两套 `*_fetcher` 语义纠缠。
- **共享 StockDB 客户端**：`data_provider/stockdb_fetcher.py`（遵循顶层 `*_fetcher.py` 公约），作为三能力的 `local` source 公共 HTTP 客户端，被 `kline/local_stockdb_source.py`、`stockinfo/local_stockdb_source.py`、`codesearch/local_stockdb_source.py` 复用。

#### 3.5.2 契约（DTO）落点

- `KLinePoint` / `StockInfo` / `CodeSearchResult` 统一契约：定义在各自能力 `base.py`（与 `STANDARD_COLUMNS` 同处，现状已如此）——契约即该能力的抽象一部分，端点与 service 由此导入。
- 端点对外响应模型（Pydantic）按 HermesX 惯例放 `src/schemas/` 或端点文件内；`KLinePoint` 作为 data_provider 内部产出契约，端点按需映射为响应模型。
- 跨能力共用增多时，再抽到 `src/schemas/`；当前阶段不前置抽象。

### 3.6 后端代码合规性审计与改造范围（基于 ADR-001 设计规则）

> 对既有 HermesX 后端代码按 ADR-001（D2 脏活层唯一、D3/D4 统一契约 + 配置驱动、D6 瘦端点）的合规性审计结论，已直接落入 **§3.7 执行清单**：仅 **Tier A（K 线 / 基础信息 / 代码搜索统一 source + 端点瘦身）** 在本方案范围；同根因的 `sector.py`（1819 行、17 个内联取数）列为 **Tier B** 独立 follow-up；service 层直连 SaaS 属不同边界，**Tier C** 不纳入。详细核验证据表属分析过程产物，此处不再保留。

### 3.7 代码改造代办清单（落地执行项 / TODO）

> 本清单是 §3.6 审计结论的**可执行落地版**。后续按本方案改代码时，以此为逐项勾选的执行台账；所有项完成（或显式标注"不在本期"）后，本方案后端才算达标。
>
> **图例**：`文件/位置` → 目标动作；`[规则]` = 违反的 ADR-001 决策；`档位` = A 必须 / B 建议 / C 不纳入；`前端` = 是否需前端改动。所有项默认 `[ ] 未开始`。

#### 3.7.1 Tier A — 本方案必须（逐项必做）

- [ ] **A1. `api/v1/endpoints/kline.py` 瘦身**
  - 当前：内联 `_fetch_kline_from_sina` / `_fetch_kline_from_eastmoney` / `_fetch_kline_from_tencent`（约 560/978 行，73% 为取数脏活），硬编码三级降级；路由被压到第 743 行。`[D2][D6]`
  - 动作：删除三个 `_fetch_*` 及其解析归一逻辑，仅保留路由与"调用 `KlineDataSourceManager.get_kline()`"；固定入参（code/period/fqt/limit/before_date）与出参（`KLinePoint[]`），签名不变 → **前端零改**。
  - 档位：A｜前端：❌ 零改

- [ ] **A2. 新建 `data_provider/kline/base.py`**
  - 当前：无统一契约与选源管理，降级写死在端点层。`[D3][D4]`
  - 动作：定义 `KlineDataSource(ABC)`（`get_kline(code,period,fqt,limit,before_date)→KLinePoint[]` + `_normalize_kline()` 映射）、`KLinePoint` 契约（与 `STANDARD_COLUMNS` 同处）、`KlineDataSourceManager`（**配置驱动选源/回退**：按 `KLINE_DATA_SOURCE` 定主源、`KLINE_SOURCE_PRIORITY` 定回退链主次，四源同级无硬编码先后；每源自带 TTL）。`[ADR-001 §4.4]`
  - 档位：A｜前端：❌ 零改

- [ ] **A3. 新建 `data_provider/kline/local_stockdb_source.py`**
  - 当前：StockDB（127.0.0.1:7899）未接入 data_provider。`[D2][D3]`
  - 动作：实现 `LocalStockDBDataSource`，对接 StockDB 行情接口，输出归一为 `KLinePoint`；原生仅 `日k/分钟k`，120m/周/月/年缺失由 `transform.py` 聚合补齐。
  - 档位：A｜前端：❌ 零改

- [ ] **A4. 新建 `data_provider/kline/{eastmoney_source,sina_source,tencent_source}.py`**
  - 当前：kline.py **重写**了东财/腾讯/新浪取数，而 `data_provider/` 已有 `tencent_fetcher.py`/`efinance_fetcher.py`/`akshare_fetcher.py` → **同一数据源两套实现**。`[D2][D3]`
  - 动作：把 kline.py 现有三源取数**平移**进对应 `<source>_source.py`，各自 `_normalize_kline()` 映射到 `KLinePoint`；**禁止**在新文件外保留副本，消除重复实现。
  - 档位：A｜前端：❌ 零改

- [ ] **A5. 新建 `data_provider/kline/transform.py`**
  - 当前：各源自管周期聚合，无共享聚合器。`[D4]`
  - 动作：实现共享时间桶聚合（5m/15m/30m/60m/120m/5d/周/月/年），本地源缺失周期与回退场景统一复用；`pct_chg` 在层内统一计算（派生字段，非各源重复）。
  - 档位：A｜前端：❌ 零改

- [ ] **A6. 新建/确认 `data_provider/stockdb_fetcher.py`（共享 StockDB 客户端）**
  - 当前：StockDB 客户端无统一落点，易被各能力重复封装。`[D2][3.5.1]`
  - 动作：沉淀独立的 StockDB 客户端（连接/鉴权/TTL/异常），供 `kline` 与后续 `stockinfo`/`codesearch` 复用，不进端点层。
  - 档位：A｜前端：❌ 零改

- [ ] **A7. `src/config.py` + `.env.example` + `system_config` 白名单**
  - 当前：无 `KLINE_DATA_SOURCE` 等切换键，回退无法配置。`[D4][D5]`
  - 动作：在 `@dataclass Config` 与 `.env.example` 新增 `KLINE_DATA_SOURCE` / `KLINE_FALLBACK_ENABLED` / `KLINE_SOURCE_PRIORITY`（+ 预留 `STOCKINFO_*` / `CODESEARCH_*`），并将这些键注册进 `system_config` 运行时可写白名单（`_WEBUI_RUNTIME_ENV_FILE_PRIORITY_KEYS`）。
  - 档位：A｜前端：⚠️ 需 A8 配套

- [ ] **A8. 前端 `apps/hrs-web/` 新增「数据源配置」Tab（挂 `/settings` 下）**
  - 当前：无运行时切换 UI，配置仅启动期 env。`[D5]`
  - 动作：复用 `POST /api/v1/config` 运行时写 `.env`，把 A7 的 `KLINE_*` 纳入可写白名单；选项来自枚举（local/eastmoney/sina/tencent/auto + 回退链排序 UI）。
  - 档位：A｜前端：✅ 需新增页面

- [ ] **A9. `data_provider/stockinfo/`、`data_provider/codesearch/` 同模式占位**
- [ ] **A10.** 迁移 `src/services/name_to_code_resolver.py` 的取数到 `data_provider/code_search/eastmoney_source.py`：③ 层不再直接 `import akshare` 取数，解析/缓存留薄壳；`stock_service.py` 的 `get_stock_name` 随矩阵迁至 `stock_info/eastmoney_source.py` `[D2][D3]`
  - 当前：基础信息/代码搜索未统一，仍散落端点层与 data_provider 既有 `get_stock_name` 等。`[D3][3.5.1]`
  - 动作：各建 `base.py`（`ABC` + `Manager`）+ 契约（`StockInfo` / `CodeSearchResult`）+ 至少 1 个 source 适配器；优先复用 data_provider 既有 `get_stock_name/get_stock_list` 加薄适配壳，本地 StockDB 接入走同一壳。
  - 档位：A｜前端：❌ 零改（首期可仅 base + 接口契约占位）

#### 3.7.2 Tier B — 超方案范围（记录待办，独立 follow-up）

- [ ] **B1. `api/v1/endpoints/sector.py` 瘦化与取数下沉**
  - 当前：内联 **17 个** `_fetch_*` 直连 `push2.eastmoney.com`，文件 **1819 行**，整文件即"东财接口搬运+解析"，与 kline.py 同一反模式，是最大单文件乱源。`[D2][D6]`
  - 动作（建议独立 PR）：17 个取数搬入新建 `data_provider/sector/`（或先抽 `sector_fetcher.py`），端点瘦化为只路由+调 Manager；周期/板块聚合复用 `transform.py` 思路。
  - 档位：B｜前端：❌ 零改（仅重构）｜**不在本方案 v0.3 范围，另行排期**

#### 3.7.3 Tier C — 不纳入（仅记录，不改动）

- [ ] **C1. `src/services/` 直连外部 SaaS**（alphasift / intelligence / social_sentiment / stock_index_remote）
  - 当前：直接 `requests.get` 外部 SaaS/LLM。`[不同边界上下文]`
  - 动作：**本期不纳入**。属 SaaS/通知/LLM 边界，与"行情数据源脏活层"不同上下文；其集成范式（settings + 熔断 + 原子缓存）可由 data_provider 后续统一借鉴，但不与本次改造耦合。
  - 档位：C｜前端：❌｜**显式标注：不改动**

#### 3.7.4 建议执行顺序与依赖

1. **先建底座**：A2（base/Manager/契约）→ A3/A4/A5（四源 + 聚合）→ A6（共享客户端）。
2. **再瘦端点**：A1（kline.py 改调 Manager，删内联脏活）；此时后端已达标，**前端零改**。
3. **接配置闭环**：A7（config + 白名单）→ A8（前端切换 UI）。
4. **横向扩展**：A9（stockinfo/codesearch 同模式）。
5. **独立 follow-up**：B1（sector.py）单独排期，不与本方案耦合。
6. **不触碰**：C1（service SaaS）。

> **完成判据**：Tier A 全部 `[x]` 后，本方案后端即满足 ADR-001 D2/D3/D4/D5/D6；Tier B/C 状态明确（B 排期待办、C 显式不纳），不构成遗留隐患。

### 3.8 数据接入层（data_provider）二维分层规划（功能 × 数据源）

> 本节针对 §3.6 审计暴露的"数据源多、用途杂、分类乱"问题，给出数据接入层（第 ② 层）的**可持续分层方案**。设计理念：**先按"功能/用途"分维度，再按"数据源"分维度**，文件夹与文件据此显式区分，便于管理与维护。本节的"功能×源"二维矩阵是 ADR-001 **D3** 的正式落地细化。

> 数据接入层（第 ② 层）的"功能 × 数据源"二维分层理念（先按功能分维度、再按源分维度，`data_provider/<功能>/<源>_source.py`）及其公共底座 `common/` 设计，**以 ADR-001 §4.3 / §4.4 为权威**；本节仅补充 StockDB 落地的能力清单（§3.8.3）与关键决策（§3.8.5）。"为什么现在乱、如何防再乱"的根因分析属分析过程产物，已并入 §3.7 与 ADR-001，此处不重复。

#### 3.8.3 真实能力清单（与 ADR-001 §4.4 对齐，避免拍脑袋）

| 能力（功能维度） | 当前实现位置（乱在哪） | 服务谁（业务） | 本期 v0.3 |
|---|---|---|---|
| **K 线 / 历史多周期**（kline / daily_data） | `kline.py`（重写）+ `akshare/tushare/efinance` 的 `get_daily_data` | K 线图、回测、选股、预警 | ✅ 本期建矩阵 |
| **实时行情**（realtime_quote） | `akshare/tickflow/yfinance/alphavantage` 的 `get_realtime_quote`；已有 `RealtimeSource` 枚举 | 自选股、大盘、组合 | ⏭ 本期仅留接口，阶段 2 迁入 |
| **基础信息**（stock_info：名称/列表/行业/板块） | 多 fetcher 的 `get_stock_name`/`get_stock_list`（分散） | 各页面表头、下拉、持仓 | ✅ 本期（base + local + 复用） |
| **代码搜索**（code_search） | 无统一实现，散落 | 搜索框联想 | ✅ 本期（base + local + 复用） |
| **板块/概念/涨跌停/热门**（sector） | `BaseFetcher.get_sector_rankings`…；`sector.py` 端点内联 17 个取数 | 板块页、热度 | ⏭ 阶段 3（独立 follow-up，含 §3.7 B1） |
| **财务基本面**（fundamentals） | `fundamental_adapter` / `yfinance_fundamental_adapter` / `tushare` | 财报、估值 | ⏭ 阶段 3 |
| **新闻 / 日历**（news / calendar） | `wallstreetcn_calendar_fetcher` / `wallstreetcn_live_news_fetcher` | 资讯 | ⏭ 阶段 3 |
| **机构数据**（institutional） | `tw_institutional_fetcher` | 台股机构 | ⏭ 阶段 3 |

> 结论：本期只需把**前 4 项**建成矩阵；后 4 项是既有散落实现的"归宿目标"，架构预留即可，不强行搬。

> 数据接入层的完整目标目录结构（含 `common/` 与各功能包）见 **ADR-001 §4.4**；本方案本期（阶段 1）落地的逐项文件、职责与划分依据以 **ADR-001 §4.4 目录铺排总表** 为唯一权威基准，最终目录须与 ADR-001 §4.4 逐行匹配。

#### 3.8.5 关键设计决策（防重复、防再乱）

- **决策 1（逻辑源 ≠ 物理实现）**：用户配置的 `KLINE_DATA_SOURCE=eastmoney/sina/tencent` 是**逻辑源**；其**物理实现复用 `data_provider` 既有取数通道**（`akshare` 包东财+新浪、`efinance` 包东财、`tencent_fetcher` 包腾讯），**不再重写**（直接消除 §3.6 的"同一数据两套实现"）。只有 `local`（StockDB 7899）是新适配器。
- **决策 2（源适配器只做格式映射）**：每个 `<源>_source.py` 仅负责"该源原始响应 → 该功能契约（如 `KLinePoint`）"，归一 / 缓存 / 限流 / 健康全部走 `common/`，避免 20 个源各写一遍。
- **决策 3（四源同级、优先级纯配置）**：沿用已定原则——适配层内 `local/eastmoney/sina/tencent` 完全同级，主次先后 100% 由 `KLINE_DATA_SOURCE` / `KLINE_SOURCE_PRIORITY` 决定，代码不写死任何源的首选/兜底位。
- **决策 4（巨类降级为"物理后端"）**：现有 `akshare_fetcher` / `tushare_fetcher` / `efinance_fetcher` 短期作为 `kline` / `realtime` / `stock_info` 的**物理取数后端被复用**，中期才逐步拆成 capability×source 矩阵（类比 §3.7 B1 的独立 follow-up）。**本期不重写它们**。
- **决策 5（本地源无特权）**：StockDB 只是 `kline/local_stockdb_source.py` 又一个普通源适配器，不在端点层、不在 config 里开特殊分支。

#### 3.8.6 分阶段落地建议

- **阶段 1（本期 v0.3，必做）**：建 `common/` + `kline/`（local 新写 + 3 逻辑源复用既有通道）+ `stock_info/`、`code_search/`（base + local + 复用壳）；`kline.py` 瘦化（§3.7 A1–A6）。
- **阶段 2（建议）**：`realtime/` 迁入矩阵，复用现有 `RealtimeSource` 枚举与 `UnifiedRealtimeQuote`。
- **阶段 3（独立 follow-up）**：`sector/`（含 §3.7 B1 的 `sector.py` 17 取数）、`fundamentals/`、`news/`、`institutional/` 逐步迁入；旧 `akshare_fetcher` 巨类完成"物理后端 → 矩阵拆解"后退役。

#### 3.8.7 与既有章节 / ADR 的关系

- 本节"功能 × 源"二维矩阵 = **ADR-001 D3 的正式落地细化**：D3 原只给三能力包，本节补全维度原则、能力清单、`common/` 与分阶段。
- §3.5 命名规范继续有效；§14.2 文件清单据此补 `data_provider/common/`。
- 不推翻任何既有决策：只是把"三能力包"升级为"按功能分、按源拆"的可持续矩阵。

#### 3.8.8 数据接入层目录铺排总表（代码拆分与最终落地的权威依据）

> **本方案不再内联目录铺排总表——以 ADR-001 §4.4 为唯一真源。** 原 v0.2 在此全量内联的 `data_provider/` 目录铺排总表（含 `common/` 与各功能包、三级文件、划分依据、落地阶段、既有文件处置），现已内联进 **ADR-001 §4.4 目录铺排总表**，作为后续代码拆分、新建、挪动的**唯一对齐基准**：改造完成后 `data_provider/` 的实际目录与文件须与 **ADR-001 §4.4** 逐行一一匹配（路径、名称、职责一致）。
>
> **划分总则（怎么分）**、**`base.py` 三层关系**、**既有文件处置（不删不改、降级为"物理后端"）** 等说明均见 ADR-001 §4.1 / §4.2 / §4.3 / §4.4，本方案不重复，避免双真源漂移。
>
> 🔍 两类高频查询接口（输入编码查股票 / 查股票信息）的归类与落点见 **§3.8.9**（本节不重复总表，仅说明归类依据）。

#### 3.8.9 两类既有查询接口的归类（输入编码查股票 / 查股票信息）

日常使用中有两个高频接口，本质都是"从市场数据源取基础数据"，**归属 ② 数据源对接层，不应在 ③ 端点/服务层直接取数**：

| 既有功能 | 语义 | 归入功能包 | 源适配器 | 当前实况（违规 / 待迁移） |
|---|---|---|---|---|
| 输入 6 位股票编码 / 名称，解析出这只股票（含联想） | 编码↔股票解析、候选列表 | `data_provider/code_search/` | `eastmoney_source.py`（+ `local_stockdb_source.py`） | 现有 `src/services/name_to_code_resolver.py` 在 **③ 服务层直接 `import akshare` 取数**，违反 D2（脏活层唯一）；取数须下沉到 `code_search/eastmoney_source.py`，解析/缓存留 ③ 做薄壳 |
| 查该股票的信息（名称 / 行业 / 板块 / 列表） | 基础信息详情 | `data_provider/stock_info/` | `eastmoney_source.py`（+ `local_stockdb_source.py`） | `src/services/stock_service.py` 调 `manager.get_stock_name()` 已走 data_provider（合规），但 `get_stock_name` 仍躺在巨型 `BaseFetcher` 内，应随矩阵迁至 `stock_info/eastmoney_source.py` |

**合并原则**：两者**不合并为一个包**——契约不同（`CodeSearchResult` vs `StockInfo`）。但底层"股票总表 / 名称↔编码"抓取可共享：两个包的 `eastmoney_source.py` 统一复用既有 `get_stock_name` / `get_stock_list` / `get_stock_membership_boards`（即 ADR 定义的"物理后端"），不在各源重写。本归类与 ADR-001 §4.4 目录表一一对应（`code_search/`、`stock_info/` 两包均已列出 `eastmoney_source.py` + `local_stockdb_source.py`，阶段 1）。

**关于"现在用的是东财"**：实测解析引擎当前实走「本地静态表 `STOCK_NAME_MAP` + AkShare 兜底」，并非直接调东财；`get_stock_name` 走 `data_provider` 的 capability 路由（谁注册 `stock_name` 谁出）。无论具体源是东财还是 AkShare，**架构归属不变**——取数必须收口进 ② 层，建包时按"逻辑源 ≠ 物理实现"复用既有通道即可。


## 3.9 功能接口层（③）设计

> **权威依据：ADR-001 §5**（边界 5.1、目录结构 5.2、铺排总表 5.3、调用链路 5.4 均在 ADR，主方案不重复展开）。本章仅作对齐摘要。设计原则见 §3.1（四层）、§2（ADR 整体设计）。

### 3.9.1 定位与边界（详见 ADR §5.1）

- **③ 功能接口层 = 面向系统标准功能的 HTTP 接口层**，输入 / 输出契约稳定、**不随底层数据源变动**；只路由 + 编排，不内联任何取数（取数一律经 ② 层 Manager）。
- **典型样例（K 线图）**：渲染与取数接口（`code/period/fqt/limit → KLinePoint[]`）标准，仅“数据从哪个源来”是个性、已下沉 ② 层；换源时 ③ 端点签名与返回结构完全不变 → 前端零改。

### 3.9.2 端点目录结构（详见 ADR §5.2）

- `api/v1/endpoints/`：③ 端点（路由 + 编排，不取数）；`api/v1/schemas/`：契约 Pydantic 模型；`src/services/`：③ 编排层（组合 ② 层取数 + 本地 DB）。两层同属 ③，均不直连第三方源。

### 3.9.3 铺排总表（权威见 ADR §5.3）

- **17 个标准功能接口文件**（全部位于 `api/v1/endpoints/` 下），契约固定、不随数据源变，底层取数由 ② 层透明供给。完整逐文件枚举（目录地址 / 文件名 / 做什么 / 作用 / 划分依据 / 随数据源变动）**见 ADR-001 §5.3**，此处不重复。归纳为：
  - **核心行情 / 投资功能（11）**：`kline`（🌟典型样例）、`watchlist`、`portfolio`、`backtest`、`alerts`、`analysis`、`sector`、`stocks`、`history`、`decision_signals`、`alphasift`
  - **系统级 / 横切（6）**：`agent`、`intelligence`、`auth`、`health`、`system_config`、`usage`

### 3.9.4 与 ② 层关系（调用链路见 ADR §5.4）

- 铁律：任何“换数据源”只发生在 ② 层内部，**③ 层契约与前端零改动**（链路图与说明见 ADR §5.4）。

## 4. 数据库说明和设计

### 4.1 StockDB 侧（外部，只读）

| 项 | 说明 |
|---|---|
| 引擎 | LGDB（LevelDB 存储 + 网络层）；`stockdb.conf`：`cache_size: 500`、`write_buffer_size: 16`、`compression: yes` |
| 存储模型 | 分层 K-V：`table : key1 : key2 -> value`，Key 层级 0~2 |
| 数据目录 | `data/`（`*.ldb`），可扩展 `data1/.../dataN` |
| 私有写空间 | `mydb/`（WAL + MANIFEST，**本方案不写**） |
| 访问方式 | 仅通过 `rd` / HTTP 接口；**禁止绕过服务直接操作底层文件** |
| 写入规范 | 未来若需持久化，必须 `rd.pipe().mset(...)` 批量写 `mydb`，且**禁止引入 SQLite/MySQL/DuckDB 等第二套数据库** |

### 4.2 HermesX 侧（本仓库，零建表）

**明确决定：不新增任何数据库表、不引入迁移。**

| 数据 | 存放位置 | 理由 |
|---|---|---|
| 行情查询结果 | 进程内 TTL 缓存（`cache.py`，`dict` + 单调时钟） | 只读派生数据，重启可丢 |
| 代码全集 | 进程内长缓存（默认 TTL 6h） | 变化频率低 |
| 个股交易日列表 | 进程内 LRU 缓存（按 code 分片，上限 500） | 与官方示例页同款设计 |
| 用户查询偏好 | 前端 `localStorage` | 属 UI 状态，不入后端 |
| 后端配置 | `src/config.py` + `.env` | 与仓库既有配置机制一致 |

**缓存键**

```
bars:{codes}:{start}:{end}:{frequency}:{fq}:{fields}:{limit}:{desc}
codes:{market}
dates:{code}
boards:{category}:{keyword}:{withSymbols}
```

代码列表不可直接作 `lru_cache` 键（list 不可哈希），须转 `tuple` 或序列化为字符串。

### 4.3 容量与性能约束

| 项 | 实测 / 估算 | 约束 |
|---|---|---|
| 单股日K 条数 | `cmd=len` = **5444**（自 2000-01-07） | 全量查询须带 `limit` 截断 |
| 单股全量分钟K | ≈ `5444 × 240 ≈ 130 万` 条 | **必须**强制日期区间 + 行数上限 |
| 全市场某日快照 | `k1=qz:6 & k2=key:20260729` + 投影 ≈ 1500 条 | 按 3~5 个前缀分片，总请求数 ≤ 5 |
| 单股日K 单日响应 | ≈ 400 B | 500 行 ≈ 200 KB，可接受 |

---

## 5. 后端接口规格

> **路由前缀与零改基线（与 ADR-001 对齐）**：三类基础能力（K 线 / 基础信息 / 代码搜索）的既有端点统一由 `api/v1/endpoints/kline.py`（`/kline` 路由前缀）承载，签名为既有的 `stock_code / period / fqt / limit / before_date`，**本期零改、前端零改动**（ADR-001 §2.6）。下方 §5.2–§5.4 为这三条**真实既有端点**的契约镜像，是本期落地执行依据；§5.5 列出需前端配合的**可选增强 / 规划端点**，不属于零改基线。StockDB 仅作为 `kline` 端点背后的一个新 `local` 数据源接入（ADR-001 §4.4 / §4.5），不改变端点契约。

**端点归属（与 ADR-001 §5.2 / §5.3 对齐，均为真实既有路由）**

| 能力子接口 | 归属端点（文件） | 路由（真实既有） |
|---|---|---|
| 健康检查 | `api/v1/endpoints/health.py` | `GET /api/v1/health` |
| 代码搜索（查询接口①） | `kline.py`（`/search`） | `GET /api/v1/kline/search?q=` |
| 基础信息（查询接口②） | `kline.py`（`/{stock_code}/info`） | `GET /api/v1/kline/{stock_code}/info` |
| K 线 / 行情（核心） | `kline.py`（`/{stock_code}/kline`） | `GET /api/v1/kline/{stock_code}/kline?period&fqt&limit&before_date` |

> 说明：独立的 `/api/v1/stock-info`、`/api/v1/code-search` 端点为 ADR-001 §5.2 规划，随 `stockinfo/` `codesearch/` 能力包落成（§3.7 A9 / A10）；本期零改不新建独立端点，能力仍由 `kline.py` 承载。统一错误响应沿用 `api/v1/errors.py` 的 `error_body` 结构，错误码以该文件为准（本期零改不新增 / 不重命名错误码）。

### 5.1 健康检查

沿用既有 `GET /api/v1/health`（详见 `api/v1/endpoints/health.py` 的 `HealthResponse`），返回服务 / 数据源概览，供页面头部状态条使用；本期零改，契约不变。

### 5.2 代码搜索（查询接口①）

| Query | 类型 | 默认 | 说明 |
|---|---|---|---|
| `q` | string | **必填** | 搜索关键词（代码 / 名称 / 拼音 / 简拼），`min_length=1` |

```json
{"results": [{"code": "600633", "name": "浙数文化", "market": "SH", "secid": "1.600633"}]}
```

> 既有端点 `GET /api/v1/kline/search`（见 `kline.py:search_stocks`）。独立的 `/api/v1/code-search` 端点为 ADR-001 §5.2 规划，随 `codesearch/` 能力包落成。

### 5.3 基础信息（查询接口②）

| 路径参数 | 类型 | 说明 |
|---|---|---|
| `stock_code` | string | 6 位代码（路径参数） |

> 既有端点 `GET /api/v1/kline/{stock_code}/info`（见 `kline.py:get_stock_info`，返回 `StockInfoResponse`）；本期零改。原方案描述的「交易日列表 `/dates`」端点当前代码中不存在，不纳入本期零改基线；如需日期联想，后续在 `stockinfo/` 能力包内新增，属 §5.5 可选增强。

### 5.4 K 线 / 行情（核心）

| Query | 类型 | 默认 | 说明 |
|---|---|---|---|
| `period` | enum | `daily` | `1m`/`5m`/`15m`/`30m`/`60m`/`120m`/`5d`/`daily`/`weekly`/`monthly`/`yearly`（与 `kline.py:get_kline` 的 `pattern` 一致；本地 StockDB 仅原生 日k/分钟k，其余由 `transform.py` 聚合补齐） |
| `limit` | int | 周期默认值（见 `PERIOD_DEFAULT_LIMITS`，日k 默认 250） | `ge=1, le=10000` |
| `fqt` | int | `1` | 复权：`0`=不复权，`1`=前复权，`2`=后复权 |
| `before_date` | string | — | 分页加载：返回该日期之前的数据 |

> **路径参数** `stock_code`（6 位代码）。返回 `KLineResponse{stock_code, stock_name, period, secid, prev_close, data: KLinePoint[]}`，`KLinePoint` 字段 `date/open/high/low/close/volume/amount/pct_chg`（与 `STANDARD_COLUMNS` 一致）；`volume` 已统一为"手"（÷100）。

- 端点签名（`stock_code` / `period` / `fqt` / `limit` / `before_date`）为**既有契约**，**本期零改、前端零改动**（ADR-001 §2.6）。
- 周期命名以 `kline.py` 实际接受的 token 为准：**`daily` / `weekly` / `monthly`**（**不是** `1d` / `1w` / `1M`）；`1d/1w/1M` 仅为人类可读别名，不作为线上取值。

### 5.5 可选增强与规划端点（需前端配合，超出零改范围）

以下能力**不在本期零改基线内**，落地需前端同步改造，列为独立 follow-up：

- **区间查询 `start` / `end`**：在 `get_kline` 现有 `limit` + `before_date` 分页之上，新增按日期区间取数（需新增参数与前端改造）。
- **字段投影 `fields`**：按需返回子集（需新增参数与前端改造）。
- **周期 / 复权重命名**：`period`→`frequency`、`fqt`→`fq`（`none`/`qfq`/`hfq`）属破坏性重命名，**与前端零改冲突**，仅在独立大版本中评估。
- **交易日列表 `/dates`**：原方案描述的 `GET /api/v1/kline/dates` 当前代码中不存在，如需日期联想在 `stockinfo/` 能力包新增。
- **板块 `/boards`、导出 `/export`**：当前代码中不存在，分别属 `sector/` 能力包（阶段 3）与可选增强，不在本期。

---

## 6. 数据查询流程

### 6.1 主流程（统一经 `/api/v1/kline` 等端点）

```
1. 开关校验   STOCKDB_ENABLED=false → 503 stockdb_disabled
2. 参数规范化 code→6位数字；start/end→8或14位；start>end 自动交换
              非法 → 400 invalid_parameter
3. 查缓存     key = bars:{codes}:{start}:{end}:{freq}:{fq}:{fields}:{limit}:{desc}
4. 取数策略
   ├─ 1d + none → cmd=vals  t=日k   k1=key|qz  k2=fwd|qz|all
   ├─ 1m + none → cmd=vals  t=分钟k k1=key     k2=fwd|qz
   ├─ 5m/15m/30m/60m → 先取 1m，再按时间桶聚合
   ├─ 1w/1M         → 先取 1d，再按周/月桶聚合
   └─ qfq/hfq       → 取原始 + 取 复权 表，再换算
5. 请求 StockDB  requests.get(url, timeout=STOCKDB_TIMEOUT_MS/1000)
              连接异常/超时 → 503 stockdb_unavailable
              非 JSON / 结构异常 → 502 stockdb_bad_response
6. 后处理     按 date 显式排序 → 复权换算 → 周期聚合 → 字段投影 → 截断 limit
7. 写缓存 + 返回 {query, columns, rows, total, truncated, partial, elapsedMs}
```

### 6.2 复权计算流程

```
1. 读复权表  cmd=vals&t=复权&k1=key:{code}&k2=all:  → [{date,div,give,trans,mult,cum}, ...]
2. 按 date 升序；为空则等价于 fq=none（直接返回原始价）
3. cum_last = 最后一条事件的 cum（截至最新的累计系数）
4. 每行 bar（date = d）：
     cum_d = 满足 event.date <= d 的最大 cum；无则 1.0
     qfq : price *= cum_d / cum_last   （最新价不变，历史价下移）
     hfq : price *= cum_d              （最早价不变，后续价上移）
   价格字段：open / high / low / close / pre_close
   volume / amount 不调整
5. pct_chg 用复权后的 close 与 pre_close 重算；
   amplitude / turnover / 市值类字段保持原值，前端标注为"原始口径"。
```

> **校准要求（必做）**：上线前必须把 `qfq` 结果与 StockDB 官方前端 `gp.js` 的 `fq:'qfq'` 输出逐行对账（≥3 只有送转史的标的 + 1 只无除权标的）。误差 > `1e-6` 时以官方结果为准修正公式，结论记入 §12。

### 6.3 周期聚合规则

| 目标周期 | 源周期 | 聚合规则 |
|---|---|---|
| `5m`/`15m`/`30m`/`60m`/`120m` | `1m` | 按自然时间桶（09:30 起算，**跨日不合并**）：`open`=桶内首、`high`=max、`low`=min、`close`=桶内末、`volume`/`amount`=sum、`date`=桶内末条时间戳 |
| `1w` | `1d` | 按自然周（周一~周日）：同上，`date`=本周最后一根日K日期 |
| `1M` | `1d` | 按自然月：同上，`date`=本月最后一根日K日期 |
| `5d` | `1d` | 按 5 个交易日滚动桶：同上，`date`=桶内最后一根日K日期 |
| `yearly` | `1d` | 按自然年：同上，`date`=本年最后一根日K日期 |

- **顺序决定**：先复权、后聚合。复权系数按日生效，分钟级聚合跨日不合并，两者粒度一致；若先聚合再复权，`high/low` 极值会失真。
- 聚合后 `name` 取桶内最后一条，`code` 恒定；非 OHLCV 字段（`pe_ttm`/`pb` 等）取桶内最后一条并标注"期末值"。

### 6.4 全市场 / 大范围查询

```python
prefixes = ["0", "3", "6"]        # a-share 默认
for p in prefixes:
    GET ?cmd=vals&t=日k&k1=qz:{p}&k2=key:{date}&ap=get.code,name,close&json=1
```

- 请求数 ≤ 5，**禁止** `for code in codes: rd.get(...)` 式逐股请求。
- 结果在后端合并、排序、按 `code` 去重。
- 超过 `STOCKDB_MAX_ROWS` 时截断并置 `truncated=true`。

### 6.5 失败与降级

| 场景 | 行为 |
|---|---|
| 连接被拒 / 超时 | 503 `stockdb_unavailable`，前端显示"数据源未启动"引导文案 |
| 返回非 JSON / 结构异常 | 502 `stockdb_bad_response` |
| 查询有效但无数据 | **200 + 空 rows**（不是 404），前端渲染空态 |
| 单前缀失败、其他成功 | 部分成功：返回已有数据 + `partial=true`，不整体失败 |
| 连续失败 N 次 | 客户端短路 `STOCKDB_COOLDOWN_SEC` 秒，避免每次点击都空等超时 |

### 6.6 缓存策略

| 缓存 | TTL | 失效条件 |
|---|---|---|
| `/health` | 15 s | — |
| 代码全集 | 6 h | 进程内长缓存（默认 TTL 6h）；无手动清除端点，重启即失效（见 §4.2） |
| `/dates?code=` | 1 h，LRU 500 项 | 同上 |
| `/bars` | 5 min（`1d`）/ 30 s（分钟级） | 同上 |
| `/boards` | 12 h | 同上 |

> `bars` 缓存键必须包含全部查询参数，否则会出现"切换周期后仍显示旧数据"的经典漂移。

---

## 7. 前端设计

### 7.1 页面位置与路由

| 项 | 值 |
|---|---|
| K 线页面 | `apps/hrs-web/src/pages/StockDataViewPage.tsx`，路由 `/stock/kline`（原有页面，数据源可配） |
| 数据源配置页 | `apps/hrs-web/src/pages/SettingsPage`（或子页），路由 `/settings` 下「数据源」Tab（新增） |
| 菜单 | K 线：`productModel` → `menuId: 'stockData'`；配置：复用既有 `/settings` 菜单 |
| i18n | `layout.nav.stockData.title` / `.description` + 新增「数据源设置」相关 key |
| API | `apps/hrs-web/src/api/stockdb.ts`（或并入既有 kline API 模块） |
| 请求 | `/api/v1/kline`、`/api/v1/stock-info`、`/api/v1/code-search`（vite 已把 `/api` 代理到 `127.0.0.1:8000`，**无需改 vite 配置**） |

### 7.2 布局

```
┌ PageHeader 本地行情 · 状态条：数据源 127.0.0.1:7899 · 最新交易日 2026-09-24 ┐
├ Card（sticky 工具条）                                                      │
│  [代码输入+联想] [开始日期+联想] [结束日期+联想] [周期▾] [复权▾]           │
│  [读取数据] [导出 CSV]   提示：个股 xxx · 交易日 N 天 · 区间 xx~xx         │
├ InlineAlert（错误 / 截断 / 部分成功提示）                                  │
└ Card（数据表）                                                             │
   600633 [1d] 2026-07-20 至 2026-07-29 · 8 行                              │
   Table（columns 动态；isLoading / renderEmptyState / pagination）          │
```

### 7.3 交互规则

1. **代码联想**：页面加载拉一次 `/codes` 建本地索引；输入按"前缀优先、其次包含"过滤；虚拟滚动（行高 32px，缓冲 10 行）。
2. **日期联想**：选中 6 位代码后拉 `/dates?code=`（按 code 缓存）；支持 `YYYY-MM-DD` 与 `YYYYMMDD`，`blur` 时规范化并自动交换起止。
3. **触发时机**：点击「读取数据」、`Enter`、周期/复权 `change`、代码/日期 `blur`（debounce 260ms）。
4. **竞态**：每次请求带递增 `serial`，过期响应丢弃（沿用 `viewer.js` 的 `loadSerial` 设计）。
5. **无日期时**：默认取最近 `limit` 条（`desc=true`），标题显示"最近 N 条"。
6. **排序/翻页/筛选**：只在内存操作，**不得重新请求**。
7. **导出**：前端用当前 `rows` 生成 CSV（BOM + CRLF），文件名 `{code}_{freq}_{start}_to_{end}.csv`。

### 7.4 列渲染与字段映射

后端返回 `columns`，前端查本地 `FIELD_LABELS` 映射中文表头：

| 字段 | 中文表头 | 格式化 |
|---|---|---|
| `date` | 日期/时间 | 8 位 → `YYYY-MM-DD`；14 位 → `YYYY-MM-DD HH:mm:ss` |
| `code` | 代码 | 原样 |
| `name` | 名称 | 原样 |
| `open`/`high`/`low`/`close`/`pre_close` | 开盘价/最高价/最低价/收盘价/前收盘价 | 2 位小数，右对齐 |
| `volume` | 成交量 | 千分位整数 |
| `amount` | 成交额 | 千分位整数 |
| `turnover`/`pct_chg`/`amplitude` | 换手率/涨幅%/振幅% | 2 位小数 + `%` |
| `is_st` | 是否ST | `true`→「是」/「否」 |
| `vol_ratio` | 量比 | 2 位小数 |
| `total_share`/`float_share` | 总股本/流通股本 | 千分位 |
| `total_mv`/`float_mv` | 总市值/流通市值 | 亿/万自适应 |
| `pe_ttm`/`pb` | 市盈率/市净率 | 2 位小数 |

- 分钟K 缺 `name`/`pct_chg`/市值字段时列**自动减少，不得渲染空列**。
- 涨跌用项目既有色板（不新造颜色变量）。（注：A 股惯例涨红跌绿。）

### 7.5 组件复用清单

| 需求 | 复用 |
|---|---|
| 表格 | `components/basic/Table/Table.tsx`（`TableColumnDef` / `PaginationDef` / `renderEmptyState` / `isLoading`） |
| 页面骨架 | `components/layout/AppPage`、`components/page-layout` 的 `PageHeader` / `EmptyState` / `InlineTipCard` |
| 卡片/按钮/提示 | `Card` / `HrsButton` / `InlineAlert` |
| 代码+联想 | **不直接复用** `components/StockSearch/StockSearch.tsx`（其数据源是 HermesX 股票索引），参考其交互另建 `StockDbCodeInput` |
| 日期输入 | 无专用 DatePicker，沿用 `<input type="date">` 方案（`BacktestPage.tsx` 已有先例） |
| 请求 | `src/api/index.ts` 的 `apiClient`（注意 GET 有 L1 内存缓存，见 §11.4） |

### 7.6 状态机

```
idle ──点击/Enter──▶ loading ──成功──▶ success(rows)
  │                    │                   │
  │                    ├──空 rows────────▶ empty
  │                    ├──truncated──────▶ success + InlineAlert
  │                    └──错误──────────▶ error(InlineAlert)
  └──health connected=false──▶ unavailable(EmptyState + 启动引导)
```

---

## 8. 边界条件与空态

### 8.1 参数边界

| 场景 | 处理 |
|---|---|
| 代码为整数 `1`（`000001` 误写） | 后端强制转 6 位字符串；不足时在**入参校验阶段报 400**，不做静默补零 |
| 代码带 `sh`/`sz` 前缀 | 规范化剥离前缀 |
| 代码非 6 位数字 | 400 `invalid_parameter` |
| `start > end` | 自动交换，并在响应 `query` 中回显交换后的值 |
| 只传 `start` 不传 `end` | 日K：查该精确交易日；分钟K：查该精确分钟键 |
| 只传 `end` 不传 `start` | 视为非法（400），不做隐式"从最早到 end"解释 |
| `start`/`end` 都为空 | 取最近 `limit` 条，标题显示"最近 N 条" |
| 分钟K 传 8 位日期 | 视为"整天"：`k2=qz:{YYYYMMDD}` |
| `frequency=1w/1M` + 分钟级日期 | 忽略时分秒部分，按日聚合 |
| `limit` > `STOCKDB_MAX_ROWS` | 静默收敛到上限并置 `truncated=true` |
| `fields` 含不存在字段 | 忽略该字段，不报错（`columns` 自然缺失） |
| `code=6*`（前缀） | 允许；必须同时给出日期约束，否则按 `STOCKDB_MAX_ROWS` 截断 |

### 8.2 数据边界（必测）

| 场景 | 处理 |
|---|---|
| **服务端返回顺序不稳** | `fwd:` 返回倒序、`all:` 返回升序 → **后端必须按 `date` 显式排序**，不得依赖服务端顺序 |
| 停牌 / 无效行情（`close<=0`、`pct_chg` 为 `"-"`/`null`/`NaN`） | 在尾盘统计类计算中排除；**表格展示保留原行**，但 `close` 列渲染为 `-` |
| `date` 字段缺失或非数字 | 该行排到末尾，不参与排序键计算（避免 `TypeError`） |
| 分钟K 缺 `name` | `columns` 不含 `name`，前端不渲染该列 |
| 复权表为空 | 等价于 `fq=none`，**不报错** |
| 复权事件日期晚于所有 bar | `cum_d`=1.0，结果等于原始价 |
| 单股日K 全量 5444 条 | 强制 `limit` 截断 + `truncated=true` |
| 全市场扫描（>5000 标的） | 按前缀分片；任一分片失败仅置 `partial=true` |
| 超长单股分钟查询（>130 万条） | 必须传日期区间；无区间时后端拒绝并返回 400 引导文案 |
| 名称缺失 | `name` 为 `""`，表格显示空，不显示 `undefined` |
| `withSymbols=true` 的板块响应过大 | 单次限制 `STOCKDB_MAX_ROWS`，超出截断 |

### 8.3 空态与错误态文案

| 状态 | 文案 |
|---|---|
| 初始 | 「请输入代码、时间并选择周期，然后点击读取。」 |
| 查询结果为空 | 「数据库中未查询到有效记录，请检查代码或日期区间。」 |
| 数据源未启动 | 「本地 StockDB 服务未启动或不可达。请先运行 `数据更新.app` 同步数据，再启动 `stockdb.app`（端口 7899）。」 |
| 功能关闭 | 「本地行情功能未启用（STOCKDB_ENABLED=false）。」 |
| 截断 | 「结果已超过 N 条，仅展示前 N 条，请收窄日期区间。」 |
| 部分成功 | 「部分数据读取失败（可能是某个代码前缀超时），当前为不完整结果。」 |
| 加载中 | 「正在读取数据…」+ Table `isLoading` |

---

## 9. 配置项

新增于 `src/config.py`（`os.getenv`，`_FALSEY_ENV_VALUES = {"0","false","no","off"}`）并同步 `.env.example`。

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `STOCKDB_ENABLED` | `false` | 本地 StockDB 源总开关。`false` 时本地源不参与 K 线等能力；按 ADR-001 由 `KLINE_SOURCE_PRIORITY` 回退至其他源或返回空态 |
| `STOCKDB_BASE_URL` | `http://127.0.0.1:7899` | StockDB 服务地址 |
| `STOCKDB_TIMEOUT_MS` | `8000` | 单次请求超时（毫秒）。分钟级建议放宽到 15000 |
| `STOCKDB_MAX_ROWS` | `5000` | 单请求最大返回行数 |
| `STOCKDB_CACHE_TTL_SEC` | `300` | `bars` 结果缓存秒数（分钟级取 `min(30, TTL)`） |
| `STOCKDB_COOLDOWN_SEC` | `30` | 连续失败后的短路冷却秒数 |
| `STOCKDB_PASSWORD` | 空 | 可选。服务端 `auth` 开启时透传 |
| `STOCKDB_REQUIRE_AUTH` | `false` | 原 v0.2 为 `/api/stockdb` 独立前缀下的鉴权开关；ADR-001 复用 `/api/v1` 已继承 `ADMIN_AUTH`，本地行情默认即受保护，该开关可降级为可选项（见 §14.8） |

`.env.example` 追加块：

```ini
# ============ 本地 StockDB 行情数据源（可选）============
# 关闭时本地 StockDB 源不参与 K 线等能力；K 线等端点按 ADR-001 回退其他源或返回空态。
STOCKDB_ENABLED=false
# StockDB 本地服务地址（需先运行 stockdb.app，默认端口 7899）
STOCKDB_BASE_URL=http://127.0.0.1:7899
# 单次请求超时（毫秒）
STOCKDB_TIMEOUT_MS=8000
# 单请求最大返回行数
STOCKDB_MAX_ROWS=5000
# 结果缓存秒数
STOCKDB_CACHE_TTL_SEC=300
# 连续失败后的短路冷却秒数
STOCKDB_COOLDOWN_SEC=30
# 服务端开启鉴权时填写，留空表示无需鉴权
# STOCKDB_PASSWORD=
```

### 9.1 数据源切换配置（多源可切换，UI 可管，详见 ADR-001）

在 §9 的 StockDB 连接配置之外，新增「统一基础能力层」的数据源切换键。每组能力（K 线 / 基础信息 / 代码搜索）独立配置，复用既有 `POST /api/v1/config` 运行时写 `.env` + `reload_now` 基建，无需重启即切换。

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `KLINE_DATA_SOURCE` | `local` | K 线主数据源（**优先级最高、先调用**）：`local` / `eastmoney` / `sina` / `tencent` / `auto`（auto = 按 `KLINE_SOURCE_PRIORITY` 取首个可用） |
| `KLINE_FALLBACK_ENABLED` | `true` | 主源失败是否自动回退其余源 |
| `KLINE_SOURCE_PRIORITY` | `local,eastmoney,sina,tencent` | 回退链的**主次先后**（可改，逗号分隔即优先级从高到低）。适配层内四源**完全同级、无内置权重**，此排列**仅由配置决定**，代码层对任何源一视同仁，不得把某源写死为"首选/兜底" |
| `STOCKINFO_DATA_SOURCE` | `local` | 基础信息主源（同枚举） |
| `STOCKINFO_FALLBACK_ENABLED` | `true` | 同上 |
| `CODESEARCH_DATA_SOURCE` | `local` | 代码搜索主源（同枚举） |
| `CODESEARCH_FALLBACK_ENABLED` | `true` | 同上 |

> 注：以上键须登记进 `system_config` 的运行时白名单（参考 `src/config.py:_WEBUI_RUNTIME_ENV_FILE_PRIORITY_KEYS`），方可在 Web「设置 → 数据源」Tab 中读写。

`.env.example` 追加块：

```ini
# ============ 行情基础能力统一层（数据源切换，UI 可管）============
KLINE_DATA_SOURCE=local
KLINE_FALLBACK_ENABLED=true
KLINE_SOURCE_PRIORITY=local,eastmoney,sina,tencent
STOCKINFO_DATA_SOURCE=local
STOCKINFO_FALLBACK_ENABLED=true
CODESEARCH_DATA_SOURCE=local
CODESEARCH_FALLBACK_ENABLED=true
```

> **在 Web「设置」页暴露**：相较原方案「一期不在设置页暴露」，本方案（ADR-001 D5）明确将以上数据源切换键登记进 `system_config` 运行时白名单，在 `/settings` 的「数据源」Tab 中提供主源下拉 + 回退链排序 + 开关 + 连接测试，持久化复用 `POST /api/v1/config`。改动即时生效、无需重启。

---

## 10. 风险、合规与回滚

### 10.1 风险清单

| 风险 | 等级 | 缓解 |
|---|---|---|
| StockDB 未启动 / 端口冲突 | 中 | `/health` 探测 + 空态引导 + 客户端冷却短路；不影响主流程 |
| 大查询拖垮后端进程 | 中 | `STOCKDB_MAX_ROWS` + 强制日期区间 + 前缀分片 + 超时 |
| 复权公式与官方不一致 | **高** | 上线前逐行对账（AC-3）；不对账不得上线 |
| 服务端返回顺序不稳 | 中 | 后端显式按 `date` 排序；单测覆盖 `fwd`/`all` 两种路径 |
| `json=1` 缺失导致非 JSON 响应 | 中 | 客户端统一追加；解析失败 → 502 |
| 数据许可边界（StockDB 数据不得外传/落库） | **高** | 只做只读查询与内存缓存；禁止写入 HermesX 主库；禁止提供批量导出全市场数据 |
| Docker / 桌面端部署时 `127.0.0.1:7899` 不可达 | 中 | 默认 `STOCKDB_ENABLED=false`，部署文档说明需显式配置 `STOCKDB_BASE_URL` |
| 前端 GET 请求被 L1 缓存导致数据不刷新 | 低 | 见 §11.4 |
| 误用在线接口被封禁设备 | 中 | 一期不接入任何在线接口，`stock_sdk` 的 `set_init` 一律不调用 |

### 10.2 合规约束

1. **只读**：本方案对 StockDB 只发 `get/vals/keys/len`，不写 `mydb`。
2. **不旁路**：不直接读 `data/*.ldb`，不复制数据文件到仓库。
3. **不落库**：行情结果只进进程内缓存，不写入 HermesX 数据库。
4. **不外传**：StockDB 数据仅在本机闭环内使用，不作为 LLM 输入批量外发。
5. **不引入第二套数据库**：不在 HermesX 侧为这些数据新建 SQLite/DuckDB/MySQL 表。
6. **桌面端 / Docker**：默认关闭，仅在用户显式配置且同源可达时启用。

### 10.3 回滚方式

| 层级 | 回滚动作 |
|---|---|
| **L0 功能开关**（最快） | `.env` 设 `STOCKDB_ENABLED=false` 并重启后端 → K 线等端点按 ADR-001 回退其他源或返回空态（不再有 `/api/stockdb/*` 503 路径），前端菜单隐藏。无需改代码、无需重启前端。 |
| **L1 前端隐藏** | `manifest.ts` 中 `menuVisible: false` → 菜单消失，路由仍可直达。 |
| **L2 路由摘除** | 删除 `api/app.py` 中的一行 `include_router(...)` → 接口整体消失。 |
| **L3 代码移除** | 删除 `data_provider/{stockdb_fetcher,kline,stockinfo,codesearch}` 中对应 source + 瘦端点改回直连单源 + 前端对应改回。因各 source 仅被 Manager 引用，移除对应源后无悬挂引用。 |
| **L4 版本回滚** | `git revert` 对应提交。 |

> 因本方案**不新增数据库表、不改既有文件语义**，L0~L3 均可在 5 分钟内完成且无数据残留。

---

## 11. 命名规范

### 11.1 后端

| 对象 | 规范 | 示例 |
|---|---|---|
| 包 | 全小写下划线，置于 `data_provider/<capability>/` | `data_provider/kline/local_stockdb_source.py` |
| 路由包 | `api/v1/endpoints/` | `api/v1/endpoints/kline.py` |
| 路由前缀 | `/api/v1`（K 线复用 `kline`，新增 `stock-info`/`code-search`） | `/api/v1/kline` |
| 模块内类名 | PascalCase | `StockDbHttpClient`、`QuerySpec` |
| 函数/变量 | snake_case | `build_key_expr`、`normalize_code` |
| 常量 | 全大写 | `TABLE_DAILY = "日k"` |
| 表名常量 | 直接使用中文表名字面量，集中定义在 `codec.py` | `TABLE_MINUTE = "分钟k"` |
| 错误码 | `stockdb_` 前缀 + 下划线 | `stockdb_unavailable` |
| Pydantic 模型 | PascalCase + 语义后缀 | `BarsResponse`、`CodeItem` |

### 11.2 前端

| 对象 | 规范 | 示例 |
|---|---|---|
| 页面文件 | PascalCase + `Page` 后缀 | `StockDataViewPage.tsx` |
| API 模块 | camelCase | `src/api/kline.ts`（或并入既有 kline API 模块） |
| API 对象 | `xxxApi` | `stockdbApi` |
| 类型 | PascalCase，禁止 `I` 前缀 | `StockDbBarsResponse` |
| 类型定义后缀 | `*Def`（依 `.conventions/frontend/TYPE_NAMING.md`） | `StockDbColumnDef` |
| 子组件 | PascalCase，放 `src/components/stockdb/` | `StockDbCodeInput.tsx` |
| i18n key | 段式命名空间 | `stockData.toolbar.code`、`stockData.empty.noData` |
| 状态 | `useXxx` hook 或 `useState` 语义命名 | `isLoading`、`loadSerial` |

### 11.3 菜单与路由

- `menuId: 'stockData'`（camelCase）
- `routePath: '/stock-data'`（kebab-case）
- `menuName: 'layout.nav.stockData.title'`
- `menuIcon: 'Database'`（lucide PascalCase）

### 11.4 前端缓存注意

`src/api/index.ts` 对 **GET** 请求有 L1 内存缓存，TTL 由 `constants/cacheConfig.ts` 的 `CACHE_TTL_MAP` 决定。
`/api/v1/kline` 等统一端点**不要**登记进 `CACHE_TTL_MAP`（避免与后端缓存双重失效导致调试困难）；如需强制刷新，调用 `clearApiCache('/api/v1/kline')`。

---

## 12. 测试与验证现状

### 12.1 已完成的前置验证（本方案撰写时实测）

| 项 | 命令 / 方法 | 结果 |
|---|---|---|
| 服务连通 | `curl "http://127.0.0.1:7899/?cmd=get&t=日k:600633:20260729&json=1"` | ✅ 返回完整 JSON |
| 服务进程 | `lsof -iTCP:7899` | ✅ `stockdb-s` PID 1983 LISTEN |
| 范围查询 | `cmd=vals&t=日k&k1=key:600633&k2=fwd:20260720,20260729` | ✅ 返回 8 条，**倒序** |
| 字段投影 | 追加 `&ap=get.date,close` | ✅ 位置数组 `[[20260729,10.54],...]` |
| 服务端切片 | `&num=3` / `&num=-3` | ✅ 分别取最早/最新 3 条 |
| 前缀分片 | `k1=qz:6&k2=key:20260729&ap=get.code,name,close` | ✅ 返回 `600000/600004/600006` |
| 分钟K | `cmd=vals&t=分钟k&k2=fwd:20260727093000,20260727113000` | ✅ 返回 14 位 `date` 行 |
| 复权表 | `cmd=vals&t=复权&k1=key:600633&k2=qz:2026` | ✅ `{div,give,trans,mult,cum}` |
| 代码全集 | `cmd=get&t=股票代码` | ✅ 按首字符分组字典 |
| 板块表 | `cmd=vals&t=板块*` | ✅ 含 `code/name/source/type/group/category/symbols` |
| 计数 | `cmd=len&t=日k&k1=key:600633&k2=all:` | ✅ `5444` |
| 最新交易日 | `k2=all:&num=-2&ap=get.date` | ✅ `20260923, 20260924` |
| Python SDK 可用性 | `pyenv 3.11.15` 下 `from stockdb import rd` | ✅ 可 import 并打印 `url()`（仅用于反查协议，**不用于生产**） |

### 12.2 待实施时补充的测试

**后端（`tests/test_stockdb_*.py`，离网，用 `responses`/`unittest.mock` 打桩 HTTP）**

| 测试 | 覆盖点 |
|---|---|
| `test_codec_key_expr` | `key/`qz`/`all`/`fwd`/`fwz` 表达式编码正确 |
| `test_normalize_date` | 8/14 位、`N`、非法输入 |
| `test_sort_stability` | `fwd` 倒序输入 → 输出升序/降序可控（§8.2 核心风险） |
| `test_resample_minute` | `1m→5m/15m/30m/60m` 聚合与手工核算一致 |
| `test_resample_day` | `1d→1w/1M` 聚合 |
| `test_fq_qfq_hfq` | 固定复权事件下的换算结果 |
| `test_truncate_and_partial` | 超限截断、分片部分失败 |
| `test_disabled_returns_503` | `STOCKDB_ENABLED=false` |
| `test_router_contract` | FastAPI `TestClient` 校验出入参 schema 与错误码 |

**前端**：不引入新测试框架（仓库现状），以手工冒烟 + `npm run lint` + `npm run build` 为准。

**手工冒烟清单**

1. `STOCKDB_ENABLED=true` + `KLINE_DATA_SOURCE=local` 启动后端 → K 线端点经 `LocalStockDBDataSource` 出数，`/api/v1/kline?code=xxx&period=1d` 返回 `KLinePoint[]`。
2. 杀掉 `stockdb-server` → `/health` 返回 `connected=false`，页面显示启动引导，HermesX 其余页面正常。
3. 页面查询 `600633` `1d` `qfq` → 与官方 `示范.html` 同参数结果逐行比对（AC-2/AC-3）。
4. 切 `1m` + 单日区间 → 返回 240 行左右；切 `5m` → 48 行左右。
5. 全市场日期快照（`code=6*`）→ 网络面板请求数 ≤ 5。
6. 三语言切换 → 菜单与页面文案无 key 缺失（`uiText` 缺失时会回显 key，易发现）。
7. `npm run lint` + `npm run build` 通过。

### 12.3 验证缺口（须在交付说明中写明）

- 复权对账（AC-3）**尚未执行**，是上线前必须关闭的最高风险项。
- Docker / 桌面端环境下 `127.0.0.1:7899` 可达性未验证。
- Windows 平台下 StockDB 进程与端口行为未验证（文档中的 `.app`/`.exe` 命名以 Windows 为准，macOS 实测为 `stockdb-s`）。

---

## 13. 落地实现要点（取代原代码骨架，权威以 ADR-001 为准）

> **本章已精简**：原 v0.2 的逐文件代码骨架（位于 `src/integrations/stockdb/`、`api/stockdb/`，前缀 `/api/stockdb/*`）已被 **ADR-001** 取代，属于失真的过程产物，不再在此逐文件列出，以免干扰后续代码执行。具体编码以 **§3.7 改造代办清单（TODO）** + **ADR-001 §4.4 目录铺排总表** + **ADR-001** 为唯一权威。

### 13.1 实现要点与可复用逻辑

- **StockDB 对接（local source）**：原 `client.py` / `codec.py` 对 StockDB `127.0.0.1:7899` 的 HTTP 接线 / LevelDB K-V 解析 / 字段映射逻辑，**平移为** `data_provider/stockdb_fetcher.py`（共享客户端）+ `data_provider/kline/local_stockdb_source.py`（K 线源）的实现参考；协议细节以 **§2.2（已实测）** 与 **§4.1** 为准，不得另起协议。
- **周期聚合与复权（transform）**：原 `transform.py` 的时间桶聚合（5m~年）+ `pct_chg` 计算，平移为 `data_provider/kline/transform.py` 的共享聚合器（见 ADR-001 §4.4）。
- **统一契约**：所有源输出归一为 `KLinePoint` / `StockInfo` / `CodeSearchResult`（见 ADR-001 D4），各源只写 `_normalize_*()` 映射，互不污染。
- **端点瘦身**：`api/v1/endpoints/kline.py` 仅路由 + 调 `KlineDataSourceManager.get_kline()`，签名不变（见 §3.7 A1）。
- **复权对账（AC-3）**：复权公式对账为上线硬阻断，须先通过对账再合入（见 §6.2）。

### 13.2 落地顺序（精简，对应 §3.7 代办）

| 阶段 | 内容 | 对应代办 |
|---|---|---|
| P1 | `stockdb_fetcher.py` + `kline/base.py` + 四源 `_normalize` | §3.7 A2 / A3 / A4 / A6 |
| P2 | `kline/transform.py` 聚合 + `pct_chg` | §3.7 A5 |
| P3 | `kline.py` 瘦端点（删内联 `_fetch_*`） | §3.7 A1 |
| P4 | `config.py` + `.env` + 白名单 + 前端 `/settings` Tab | §3.7 A7 / A8 |
| P5 | `stockinfo/` `codesearch/` 同模式 + 取数下沉 | §3.7 A9 / A10 |
| P6 | 复权对账（AC-3）通过后提交 | — |

> 完整文件级动作见 **§3.7**；完整目录落点见 **ADR-001 §4.4**；设计决策见 **ADR-001**。

---

## 14. 修改范围

> 本章汇总"把本方案落地为可运行功能"所需的所有文件改动，便于评审与排期。结论与 §3.3、§9、§13 一致，并补出方案正文中未显式点明、但实现时必然需要的产物（包初始化文件、子组件、测试文件、CHANGELOG 等）。

### 14.1 总览

| 类别 | 新增文件 | 修改文件 |
|---|---|---|
| 后端集成层 | 7 个（含 2 个包 `__init__.py`） | — |
| 后端路由层 | 2 个（含 1 个包 `__init__.py`） | `api/app.py` |
| 后端配置 | — | `src/config.py`、`.env.example` |
| 前端 | 3 个（页面 + API + 子组件） | `src/router/manifest.ts`、3 个 `i18n/uiText-*.ts` |
| 测试 | 4 个 | — |
| 文档 | — | `docs/CHANGELOG.md`（`[Unreleased]` 加一行） |

> 方案 §3.3 称"后端 3 处 / 前端 4 处改动"，其中"前端 4 处"统计的是 manifest / 页面 / API / i18n 四处**修改点**，未计入新建的页面与 API 文件（已被归为"新增"）。本章按"新增文件 vs 修改文件"两维拆解，避免混淆。

### 14.2 新增文件清单（后端，data_provider 内）

| 文件路径 | 对应章节 | 说明 |
|---|---|---|
| `data_provider/common/` | ADR-001 D3 / §4.4 | 跨功能公共底座：`base.py`(通用`DataSource(ABC)`+`DataSourceManager`配置选源/回退/健康/TTL)、`normalize.py`、`cache.py`、`rate_limit.py`、`health.py` |
| `data_provider/stockdb_fetcher.py` | ADR-001 D2 | 直连本地 StockDB `127.0.0.1:7899`，作为三能力的 `local` source 底座 |
| `data_provider/kline/__init__.py` | §11 / §13.1 | 包初始化（空文件，使 `data_provider.kline.*` 可 import） |
| `data_provider/kline/base.py` | ADR-001 D3 | `KlineDataSource(ABC)` + `KlineDataSourceManager`（配置选源 / 自动回退 / 每源自带 TTL）+ 统一 `KLinePoint` 契约 + `pct_chg` 层内计算 |
| `data_provider/kline/local_stockdb_source.py` | §13.1（平移自原 v0.2 实现） | 原 `src/integrations/stockdb/` 的 config/codec/client/transform/cache/service 平移至此，作为 `local` source |
| `data_provider/kline/eastmoney_source.py` | §3.2（重构 kline.py） | 原 `kline.py` 的 `_fetch_kline_from_eastmoney` 迁移为 source，只做「东财格式 → KLinePoint」映射 |
| `data_provider/kline/sina_source.py` | 同上 | 原 `_fetch_kline_from_sina` 迁移 |
| `data_provider/kline/tencent_source.py` | 同上 | 原 `_fetch_kline_from_tencent` 迁移 |
| `data_provider/kline/transform.py` | §13.1（聚合器） | 多周期时间桶聚合（5m/15m/30m/60m/**120m**/5d/周/月/年），本地源与回退场景复用 |
| `data_provider/stockinfo/__init__.py` + `base.py` + `local_stockdb_source.py` + `eastmoney_source.py` | ADR-001 D3 | 基础信息能力（股票名/行业/板块）；`local` 复用 StockDB，`eastmoney` 复用 `data_provider` 既有 `get_stock_name` 等 + 薄适配壳 |
| `data_provider/codesearch/__init__.py` + `base.py` + `local_stockdb_source.py` + `eastmoney_source.py` | ADR-001 D3 | 代码搜索能力（关键字联想）；同模式多源可切换 |

> 注意：v0.2 §13 中拆散的 `service.py` / `config.py` / `codec.py` / `client.py` / `cache.py` / `errors.py` 在落地时统一收口到 `data_provider/kline/` 对应模块（以 ADR-001 目录为准，见 ADR-001 §4.4）；类 / 函数设计、复权与聚合逻辑、字段映射仍然有效，仅包根与文件名以 ADR-001 §4.4 为准。

> 数据接入层（`data_provider/`）的**完整目录铺排、每项职责与划分依据**，以 **ADR-001 §4.4 目录铺排总表** 为唯一权威基准；本节仅列出本期（阶段 1）新增项，最终落地目录须与 ADR-001 §4.4 逐行匹配一致。

### 14.3 修改文件清单（后端）

| 文件路径 | 改动点 | 对应章节 | 风险 |
|---|---|---|---|
| `api/v1/endpoints/kline.py` | 删除内联 `_fetch_kline_from_*`，改调 `KlineDataSourceManager.get_kline(...)`；端点签名（period/fqt/limit/before_date）不变 | §3.3 / ADR-001 D6 | 仅删取数细节、保留路由与契约，前端零改动 |
| `api/app.py` | 若新增 `stock-info` / `code-search` 端点，各加 1 处 `include_router`（复用 `/api/v1`）；K 线无需改动 | §3.3 | 不影响既有 `/api/v1` 与 `ADMIN_AUTH` |
| `src/config.py` | 新增 StockDB 连接配置（8 个 `os.getenv`，沿用 `_FALSEY_ENV_VALUES`）+ 数据源切换配置（`KLINE_*` / `STOCKINFO_*` / `CODESEARCH_*` 见 §9.1） | §3.3 / §9 | §3.3 旧写"6 个"、§9 实际 8 个连接项，落地以 §9 为准；切换键须登记 `system_config` 白名单 |
| `.env.example` | 追加"本地 StockDB 行情数据源"块（§9）+ "行情基础能力统一层（数据源切换）"块（§9.1） | §3.3 / §9 | 键名须与 `src/config.py` 一致 |

> **执行台账**：上表后端改动项逐项对应 **§3.7《代码改造代办清单（TODO）》**（A1–A7 / A9）。落地时按 §3.7.4 顺序勾选执行，全部完成后端项即满足 ADR-001 D2/D3/D4/D5/D6。

### 14.4 新增文件清单（前端）

| 文件路径 | 对应章节 | 说明 |
|---|---|---|
| `apps/hrs-web/src/pages/Settings/DataSourceSetting.tsx`（或并入 `SettingsPage`） | §7.1 / §9.1 | 「数据源」配置页：每组能力主源下拉 + 回退链排序 + 开关 + 连接测试；持久化调 `POST /api/v1/config` |
| `apps/hrs-web/src/components/stock/StockDbCodeInput.tsx`（沿用既有 `StockSearch` 交互） | §7.5 / §13.1 注 | 代码 + 日期联想子组件；数据源替换为统一能力端点 |

> K 线页面 `StockDataViewPage.tsx` 与原 `api/stockdb.ts` 在 ADR-001 下归为**修改项**（复用既有 `/api/v1/kline`），不再作为全新页面新建。

### 14.5 修改文件清单（前端）

| 文件路径 | 改动点 | 对应章节 |
|---|---|---|
| `apps/hrs-web/src/pages/StockDataViewPage.tsx` | 数据源改为经 `KlineDataSourceManager` 可配（local/东财/新浪/腾讯）；UI 不变 | §7 / ADR-001 |
| `apps/hrs-web/src/api/stockdb.ts` | 改调 `/api/v1/kline` 等（或并入既有 kline API 模块） | §7.1 / §13.2 |
| `apps/hrs-web/src/router/manifest.ts` | K 线菜单保留；`/settings` 下追加「数据源」Tab 节点 | §7.1 / §13.2 |
| `apps/hrs-web/src/i18n/uiText-zh.ts` | 追加 `layout.nav.stockData.title` / `.description` + 数据源设置相关 key | §13.2 |
| `apps/hrs-web/src/i18n/uiText-en.ts` | 同上 | §13.2 |
| `apps/hrs-web/src/i18n/uiText-zh-Hant.ts` | 同上 | §13.2 |

> 前端无需改 vite 配置（§7.1 已确认 `/api` 已代理到 `127.0.0.1:8000`）。

### 14.6 新增测试文件（共 4 个）

| 文件路径 | 覆盖点 | 对应章节 |
|---|---|---|
| `tests/test_stockdb_codec.py` | `test_codec_key_expr`、`test_normalize_date` | §12.2 |
| `tests/test_stockdb_transform.py` | `test_sort_stability`、`test_resample_minute`、`test_resample_day`、`test_fq_qfq_hfq` | §12.2 |
| `tests/test_stockdb_service.py` | `test_truncate_and_partial` | §12.2 |
| `tests/test_stockdb_router.py` | `test_disabled_returns_503`、`test_router_contract`（FastAPI `TestClient`） | §12.2 |

> 测试方法：离网，使用 `responses` / `unittest.mock` 打桩 HTTP，不依赖 `127.0.0.1:7899` 实际可达。前端不引入新测试框架（§12.2）。

### 14.7 文档改动

| 文件路径 | 改动点 | 对应章节 |
|---|---|---|
| `docs/CHANGELOG.md` | 在 `[Unreleased]` 段追加一行扁平记录：`[新功能] 新增本地 StockDB 行情浏览（复用 /api/v1/kline 等统一端点，数据源可切换）` | A.3 |

### 14.8 落地前需澄清的契约漂移点（v0.2 → ADR-001 已消解）

> 以下漂移点为 v0.2 方案期间记录，现已由 ADR-001 + §3.7 + ADR-001 §4.4 统一消解，落地直接以新决策为准，无需再纠缠旧表述：

1. **目录 / 路由前缀**：v0.2 的 `src/integrations/stockdb/` 与 `/api/stockdb/*` 已统一为 `data_provider/{stockdb_fetcher,kline,stockinfo,codesearch}` 与 `/api/v1/kline`（+ `/api/v1/stock-info`、`/api/v1/code-search`）；类 / 函数设计、复权与聚合逻辑仍然有效，仅包根与路由前缀以 ADR-001 为准。
2. **配置项数量**：v0.2 §3.3 写"6 个 `os.getenv`"，§9 实际 8 个，落地以 8 个为准；另新增 §9.1 数据源切换键（须登记 `system_config` 白名单）。
3. **`STOCKDB_REQUIRE_AUTH`**：ADR-001 复用 `/api/v1` 已继承 `ADMIN_AUTH`，本地行情默认即受保护，该开关可降级为可选项。
4. **包初始化文件**：`data_provider/kline/__init__.py` 等子包初始化文件必须新建（可为空），import 依赖其存在。
5. **前端子组件 / 取数实现**：`StockDbCodeInput` 子组件、`fetch_dates` / `fetch_boards` 等取数，落地时按统一能力端点（§3.7 A9 / A10）补齐，不复用 v0.2 的"同理带过"写法。
6. **`service` 拆分**：v0.2 §13 的 service 拆三处，落地时统一收口到 `data_provider/kline/` 对应模块（以 ADR-001 目录为准）。

### 14.9 影响面与回归风险（供评估）

- **对既有功能零侵入**：所有新增代码在 `data_provider/{stockdb_fetcher,kline,stockinfo,codesearch}/` 与可选 `api/v1/endpoints/{stock_info,code_search}.py` 内；`kline.py` 仅删取数细节、保留路由与契约；`src/config.py` 仅追加只读环境变量；前端仅在 manifest 追加「数据源」Tab 与 i18n 追加 key。无既有文件语义被改、无主库新增表。
- **可整体开关 / 摘除**：`STOCKDB_ENABLED=false` 或本地源失败 → 按 `KLINE_SOURCE_PRIORITY` 回退其他源 / 返回空态（L0）；删 `data_provider/kline/` 等子包 + 前端新增（L3）。因各 source 经 `data_provider` 基类与 `config` 解耦，删除无悬挂引用。
- **最高风险项**：复权公式与官方 `gp.js` 对账（AC-3，§6.2 / §12.3）尚未执行，是上线硬阻断，落地排期须把"对账 + 修正公式"单列里程碑。
- **未验证环境**：Docker / 桌面端 `127.0.0.1:7899` 可达性、Windows 平台 StockDB 行为未验证；默认 `STOCKDB_ENABLED=false` 部署，不影响既有发布。
---

## 附录 A. 文档信息与变更日志

### A.1 文档信息

| 项 | 内容 |
|---|---|
| 文档名 | 本地 StockDB 行情数据浏览页 · 建设方案 |
| 文件 | `stock_data_view.md`（仓库根目录） |
| 状态 | 方案（未实现），待评审后进入 §13.2 的 P1 |
| 适用版本 | HermesX 当前 main；Python 3.11（`requests` 已在 `requirements.txt`） |
| 依赖文档 | `AGENTS.md`、`docs/CHANGELOG.md`、StockDB `调用方式/python/AI策略python开发接口文档.md`、StockDB `调用方式/ai_自动开发文档/AI策略界面开发纯js接口文档.md` |
| 关联模块 | `data_provider/{stockdb_fetcher,kline,stockinfo,codesearch}/`（新增，ADR-001 脏活层）、`api/v1/endpoints/{kline,stock_info,code_search}.py`（重构/新增）、`apps/hrs-web/src/pages/{StockDataViewPage,Settings/DataSourceSetting}.tsx`（修改/新增）；配套架构决策 `backend_architecture_adr.md`（ADR-001） |
| 未决事项 | ① 复权公式对账（AC-3）未执行（上线硬阻断）；② Docker/桌面端可达性未验证；③ 数据字典是否独立建表待定（ADR-001 建议新增）；④ 方案范围已升级为「行情基础能力统一层」，详见配套 ADR-001 |

### A.2 契约事实来源（本方案中所有"实测"结论）

以下结论均通过实际请求 `127.0.0.1:7899` 或官方 SDK `QueryResult.url()` 得到，不是推测：

1. `json=1` 缺失时不返回 JSON。
2. `k1=qz:6` 为前缀匹配；`k1=6*`、`k1=pre:6` 均无效（返回 `[]`）。
3. `k2=all:` 为整层匹配；`k2=fwd:A,B` 返回**倒序**，`k2=fwz:A,B` 为反序。
4. `ap=get.f1,f2` 为服务端字段投影，返回位置数组。
5. `num=N` 取前 N 条、`num=-N` 取后 N 条。
6. 表名前缀通配写作 `t=板块*` / `t=退市*`（`cmd=vals`）。
7. 分钟K 无 `name`/`pct_chg`/市值字段。
8. 单股日K 计数 `cmd=len` = 5444；最新交易日 `20260924`。

### A.3 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-09-26 | 初稿：完成背景、接口契约实测、架构解耦设计、数据库与缓存设计、接口规格、查询流程、前端设计、边界条件、配置项、风险回滚、命名规范、测试现状与核心实现代码骨架。 |
| v0.2 | 2026-10-06 | 增补：表头增加「作者 / 更新时间」；新增「0. 浏览目录」；新增「14. 修改范围」，按"新增文件 / 修改文件 / 测试 / 文档"两维拆解落地所需改动，并列出 6 处契约漂移点与影响面评估。 |
| v0.3 | 2026-10-07 | 架构升级（配套 ADR-001）：① 后端按四层分层（数据库层 / 数据源层 / 标准接口层 / 横切辅助层），`data_provider` 为唯一脏活层；② 原「独立 /api/stockdb 页」改为「统一基础能力层」——K 线 / 基础信息 / 代码搜索三类能力各自独立成包、同级、多源可切换（本地 StockDB / 东方财富 / 新浪 / 腾讯）；③ 新增 §9.1 数据源切换配置（UI 可管，复用 `POST /api/v1/config`）；④ §3/§7/§14 文件清单与路由前缀全部改为 `data_provider/` + `/api/v1/kline` 等；⑤ 周期全集扩展含 120m/5d/yearly；⑥ 标题/范围升级为「行情基础能力统一层」。 |

> 实现启动后，本节追加实际变更记录；`docs/CHANGELOG.md` 的 `[Unreleased]` 段按仓库约定追加一行扁平记录（`[新功能] 新增本地 StockDB 行情浏览页...`）。
