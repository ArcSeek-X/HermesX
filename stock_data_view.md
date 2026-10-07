# 本地 StockDB 行情数据浏览页 · 建设方案

> 文档状态：方案（未实现） · 目标仓库：HermesX
> 外部数据源：StockDB（本地服务 `127.0.0.1:7899`，数据目录 `stockdb/data`）
> 参考页面：`stockdb/调用方式/ai_自动开发文档/示范.html`
> 作者：高仓雄（gaocangxiong）
> 更新时间：2026-10-06

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
| ③ 如何结合而不耦合？ | 见 §3：独立集成包 + 独立路由前缀 + 独立开关；不 import 业务 service/repository/model，不写 HermesX 主库，不进 `api/v1`。 |

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
| AC-6 | `STOCKDB_ENABLED=false` 时 `/api/stockdb/*` 全部 503，且 `/api/v1/*` 全部正常 |
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

### 3.1 分层视图

```
浏览器 apps/hrs-web
  StockDataViewPage → src/api/stockdb.ts → apiClient → /api/stockdb/*
        │ 同源（vite dev 已把 /api 代理到 127.0.0.1:8000）
        ▼
HermesX 后端 FastAPI（server.py → api/app.py）
  api/stockdb/                    ← 路由层（前缀 /api/stockdb）
    ├── router.py                 ← 参数校验 + 错误映射
    └── schemas.py                ← Pydantic 出入参
        │
  src/integrations/stockdb/       ← 集成层（新增独立包）
    ├── config.py     Settings / 开关
    ├── client.py     HTTP 协议客户端（URL 构造 + 超时 + 冷却）
    ├── codec.py      键表达式编码 / 日期规范化
    ├── transform.py  复权 + 周期聚合 + 排序 + 投影 + 截断
    └── cache.py      进程内 TTL 缓存
        │ requests.get(..., timeout=)
        ▼
StockDB 独立进程 127.0.0.1:7899 → data/*.ldb
```

### 3.2 解耦策略（关键）

| 维度 | 做法 | 为什么不用另一种 |
|---|---|---|
| **代码** | 新建 `src/integrations/stockdb/`，只依赖 `requests` + 标准库 | 不用 `pybao/stock_sdk.py`：会把 `stockdb.abi3.so` 拉进 HermesX 进程，引入外部二进制、Python 版本与部署形态约束（Docker / Desktop 打包均受影响） |
| **协议** | 只复用 §2.2 的 HTTP 文本协议 | 不用 `gp.js`：混淆不可维护，且是浏览器直连形态 |
| **路由** | 挂 `/api/stockdb`，**不进 `api/v1/router.py`** | `api/v1` 受 `ADMIN_AUTH` 中间件保护且与业务 schema 混杂；独立前缀更易开关与下线 |
| **数据** | HermesX 主库**零新增表**，只做进程内 TTL 缓存 | 行情体量大（单股日K 实测 5444 条，全市场 GB 级）；StockDB 数据有独立许可边界 |
| **依赖** | 不 import `src/services/*`、`src/repositories/*`、`src/core/*` | 保证模块可整体删除且不留悬挂引用 |
| **故障** | `STOCKDB_ENABLED=false` → 503；超时/连接失败 → 空态 | StockDB 不可用不得影响主流程、调度、报告、通知 |
| **生命周期** | 不注册进 `app_lifespan` 调度体系，只用惰性单例客户端 | 避免与 `RuntimeSchedulerService` 争抢启停顺序 |

> 说明：`api/middlewares/auth.py` 只拦截 `/api/v1/` 前缀，故 `/api/stockdb/*` 默认**不受** `ADMIN_AUTH` 保护。若需保护，见 §9 `STOCKDB_REQUIRE_AUTH`。

### 3.3 对宿主仓库的改动点（均为纯新增）

**后端 3 处**

1. `api/app.py`：新增 1 处 `include_router(stockdb_router, prefix="/api/stockdb")`。
2. `src/config.py`：新增 6 个 `os.getenv` 配置项（§9）。
3. `.env.example`：新增配置项注释块。

**前端 4 处**

1. `src/router/manifest.ts`：新增菜单节点。
2. `src/pages/StockDataViewPage.tsx`：新增页面。
3. `src/api/stockdb.ts`：新增 API 模块。
4. `src/i18n/uiText-{zh,en,zh-Hant}.ts`：各新增 2 条导航 key。

### 3.4 与既有"外部 HTTP 服务对接"范式的一致性

`src/services/stock_index_remote_service.py` 已是仓库内对接外部 HTTP 服务的既有范式：`@dataclass(frozen=True) Settings` + `settings_from_config(config)` + `requests.get(url, timeout=...)` + 失败计数/熔断 + 原子写缓存。
本方案沿用同一形状，但**放在独立包内不复用其代码**，避免与其业务语义绑定。

---

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

统一前缀：**`/api/stockdb`**（不进 `/api/v1`）。

统一错误响应（沿用 `api/v1/errors.py` 的 `error_body` 结构）：

```json
{"error": "stockdb_unavailable", "message": "本地 StockDB 服务未启动或不可达（127.0.0.1:7899）", "detail": null}
```

| HTTP | error code | 触发条件 |
|---|---|---|
| 400 | `invalid_parameter` | 代码非 6 位数字、日期非法、周期/复权非法 |
| 404 | `stockdb_not_found` | 指定资源不存在（如板块代码） |
| 502 | `stockdb_bad_response` | 服务端返回结构异常 / 非 JSON |
| 503 | `stockdb_disabled` | `STOCKDB_ENABLED=false` |
| 503 | `stockdb_unavailable` | 连接失败 / 超时 |

### 5.1 `GET /api/stockdb/health`

连通性与数据源概览，供页面头部状态条使用。

```json
{
  "enabled": true,
  "connected": true,
  "baseUrl": "http://127.0.0.1:7899",
  "latencyMs": 12,
  "latestTradeDate": "20260924",
  "codeCount": 5421,
  "checkedAt": "2026-09-26T10:12:33+08:00"
}
```

`connected=false` 时 `latestTradeDate`/`codeCount` 为 `null`，但 HTTP 仍返回 **200**（页面据此渲染空态，不用异常态打断）。

### 5.2 `GET /api/stockdb/codes`

| Query | 类型 | 默认 | 说明 |
|---|---|---|---|
| `market` | enum | `a-share` | `a-share`（0/3/6）/ `all`（0/1/3/5/6/9） |
| `keyword` | string | — | 代码或名称模糊过滤（服务端内存过滤） |
| `limit` | int | `0` | 0 = 不限制 |

```json
{"items": [{"code": "600633", "name": "浙数文化"}], "total": 5421}
```

> 名称从最近交易日快照投影 `ap=get.code,name` 取（3~5 个前缀请求），避免逐股查询；取不到时 `name` 为 `""`，不得报错。

### 5.3 `GET /api/stockdb/dates`

个股交易日列表（倒序），用于日期输入框联想。

| Query | 类型 | 默认 | 说明 |
|---|---|---|---|
| `code` | string | **必填** | 6 位数字 |
| `limit` | int | `2000` | 上限 5000 |

```json
{"code":"600633","dates":["20260924","20260923"],"total":5444}
```

### 5.4 `GET /api/stockdb/bars`（核心）

| Query | 类型 | 默认 | 说明 |
|---|---|---|---|
| `code` | string | **必填** | 单代码 `600633`、逗号分隔 `600633,000001` 或前缀 `6*` |
| `start` | string | — | `YYYYMMDD` 或 14 位 `YYYYMMDDhhmmss` |
| `end` | string | — | 同上，或 `N`（到最新） |
| `frequency` | enum | `1d` | `1d`/`1m`/`5m`/`15m`/`30m`/`60m`/`1w`/`1M` |
| `fq` | enum | `none` | `none`/`qfq`/`hfq` |
| `fields` | string | — | 逗号分隔；不传返回全字段对象行 |
| `limit` | int | `500` | 单代码最大条数，上限 `STOCKDB_MAX_ROWS` |
| `desc` | bool | `true` | `true` 时间倒序 |

**单代码响应**

```json
{
  "query": {"code":"600633","start":"20260720","end":"20260729","frequency":"1d","fq":"qfq","desc":true},
  "columns": ["date","code","name","open","high","low","close","volume","amount","pct_chg"],
  "rows": [{"date":20260729,"code":"600633","name":"浙数文化","open":10.23,"close":10.54}],
  "total": 8,
  "truncated": false,
  "partial": false,
  "elapsedMs": 34
}
```

**多代码响应**：`rows` 变为 `{"600633":[...],"000001":[...]}`，`columns` 取并集。

- `columns` 由后端按**字段存在性**动态生成，前端直接按 `columns` 渲染，避免硬编码列。
- `truncated=true`：被 `limit` 截断，前端提示"结果已截断，请收窄区间"。
- `partial=true`：多前缀查询中部分分片失败，仅返回已成功数据。

### 5.5 `GET /api/stockdb/boards`

| Query | 类型 | 默认 | 说明 |
|---|---|---|---|
| `category` | enum | — | `concept`/`sw1`/`sw2`/`sw3`（对应 0/1/2/3） |
| `keyword` | string | — | 板块名称模糊匹配 |
| `withSymbols` | bool | `false` | 是否返回成分股（体量大，默认否） |

```json
{"items":[{"code":"801760.SL","name":"传媒","source":"sw","type":"sw_1","group":"申万行业指数列表","category":"sw1"}],"total":28}
```

### 5.6 `GET /api/stockdb/export`

参数同 `bars`，返回 `text/csv`（带 UTF-8 BOM）+ `Content-Disposition: attachment`。一期可选；前端亦可直接导出（§7.3）。

---

## 6. 数据查询流程

### 6.1 主流程（`GET /api/stockdb/bars`）

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
| `5m`/`15m`/`30m`/`60m` | `1m` | 按自然时间桶（09:30 起算，**跨日不合并**）：`open`=桶内首、`high`=max、`low`=min、`close`=桶内末、`volume`/`amount`=sum、`date`=桶内末条时间戳 |
| `1w` | `1d` | 按自然周（周一~周日）：同上，`date`=本周最后一根日K日期 |
| `1M` | `1d` | 按自然月：同上，`date`=本月最后一根日K日期 |

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
| `/codes` | 6 h | 手动 `POST /api/stockdb/cache/clear` |
| `/dates?code=` | 1 h，LRU 500 项 | 同上 |
| `/bars` | 5 min（`1d`）/ 30 s（分钟级） | 同上 |
| `/boards` | 12 h | 同上 |

> `bars` 缓存键必须包含全部查询参数，否则会出现"切换周期后仍显示旧数据"的经典漂移。

---

## 7. 前端设计

### 7.1 页面位置与路由

| 项 | 值 |
|---|---|
| 页面 | `apps/hrs-web/src/pages/StockDataViewPage.tsx` |
| 路由 | `/stock-data` |
| 菜单 | `productModel` → `menuId: 'stockData'`，`menuIcon: 'Database'`，`menuVisible: true` |
| i18n | `layout.nav.stockData.title` / `.description`（三个语言文件各 2 条） |
| API | `apps/hrs-web/src/api/stockdb.ts` |
| 请求 | `/api/stockdb/*`（vite 已把 `/api` 代理到 `127.0.0.1:8000`，**无需改 vite 配置**） |

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
| `STOCKDB_ENABLED` | `false` | 总开关。`false` 时 `/api/stockdb/*` 全部 503 **且前端菜单隐藏** |
| `STOCKDB_BASE_URL` | `http://127.0.0.1:7899` | StockDB 服务地址 |
| `STOCKDB_TIMEOUT_MS` | `8000` | 单次请求超时（毫秒）。分钟级建议放宽到 15000 |
| `STOCKDB_MAX_ROWS` | `5000` | 单请求最大返回行数 |
| `STOCKDB_CACHE_TTL_SEC` | `300` | `bars` 结果缓存秒数（分钟级取 `min(30, TTL)`） |
| `STOCKDB_COOLDOWN_SEC` | `30` | 连续失败后的短路冷却秒数 |
| `STOCKDB_PASSWORD` | 空 | 可选。服务端 `auth` 开启时透传 |
| `STOCKDB_REQUIRE_AUTH` | `false` | `true` 时在 `api/stockdb/router.py` 内自行挂载 JWT/管理员依赖（因为 `/api/stockdb` 不在 `auth` 中间件默认保护范围内） |

`.env.example` 追加块：

```ini
# ============ 本地 StockDB 行情数据源（可选）============
# 关闭时 /api/stockdb/* 返回 503，前端不显示「本地行情」菜单。
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

> **不进 `src/core/config_registry.py`**：一期不在 Web「设置」页暴露这些项（StockDB 是本机数据源，页面改地址无意义）。若后续需要，再按既有规则登记。

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
| **L0 功能开关**（最快） | `.env` 设 `STOCKDB_ENABLED=false` 并重启后端 → 所有 `/api/stockdb/*` 返回 503，前端菜单隐藏。无需改代码、无需重启前端。 |
| **L1 前端隐藏** | `manifest.ts` 中 `menuVisible: false` → 菜单消失，路由仍可直达。 |
| **L2 路由摘除** | 删除 `api/app.py` 中的一行 `include_router(...)` → 接口整体消失。 |
| **L3 代码移除** | 删除 `src/integrations/stockdb/` + `api/stockdb/` 两个目录 + 前端 4 处新增。因无外部 import 指向它们，删除后无悬挂引用。 |
| **L4 版本回滚** | `git revert` 对应提交。 |

> 因本方案**不新增数据库表、不改既有文件语义**，L0~L3 均可在 5 分钟内完成且无数据残留。

---

## 11. 命名规范

### 11.1 后端

| 对象 | 规范 | 示例 |
|---|---|---|
| 包 | 全小写下划线，置于 `src/integrations/stockdb/` | `src/integrations/stockdb/client.py` |
| 路由包 | `api/stockdb/` | `api/stockdb/router.py` |
| 路由前缀 | `/api/stockdb` | `/api/stockdb/bars` |
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
| API 模块 | camelCase | `src/api/stockdb.ts` |
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
`/api/stockdb/*` **不要**登记进 `CACHE_TTL_MAP`（避免与后端缓存双重失效导致调试困难）；如需强制刷新，调用 `clearApiCache('/api/stockdb')`。

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

1. `STOCKDB_ENABLED=true` 启动后端 → `/api/stockdb/health` 返回 `connected=true`。
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

## 13. 核心实现代码（前后端）

> 以下为落地时的核心骨架，已按实测协议编写。文件名与 §11 命名规范一致。

### 13.1 后端：`src/integrations/stockdb/config.py`

```python
# -*- coding: utf-8 -*-
"""StockDB 集成层配置。

职责：
1. 从环境变量读取 StockDB 连接与限流参数
2. 提供不可变 Settings 与工厂函数（与 stock_index_remote_service 同形状）
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_FALSEY = {"0", "false", "no", "off"}


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSEY


def _as_int(raw: str | None, default: int) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class StockDbSettings:
    """StockDB 连接配置。"""

    enabled: bool
    base_url: str
    timeout_ms: int
    max_rows: int
    cache_ttl_sec: int
    cooldown_sec: int
    password: str | None


def settings_from_env() -> StockDbSettings:
    """从环境变量构造配置；未启用时其余字段仍返回可用默认值。"""
    return StockDbSettings(
        enabled=_as_bool(os.getenv("STOCKDB_ENABLED"), False),
        base_url=(os.getenv("STOCKDB_BASE_URL") or "http://127.0.0.1:7899").rstrip("/"),
        timeout_ms=_as_int(os.getenv("STOCKDB_TIMEOUT_MS"), 8000),
        max_rows=_as_int(os.getenv("STOCKDB_MAX_ROWS"), 5000),
        cache_ttl_sec=_as_int(os.getenv("STOCKDB_CACHE_TTL_SEC"), 300),
        cooldown_sec=_as_int(os.getenv("STOCKDB_COOLDOWN_SEC"), 30),
        password=(os.getenv("STOCKDB_PASSWORD") or "").strip() or None,
    )
```

### 13.2 后端：`src/integrations/stockdb/codec.py`

```python
# -*- coding: utf-8 -*-
"""StockDB 协议编解码。

职责：
1. 定义表名常量与键表达式编码（key/qz/all/fwd/fwz）
2. 规范化代码与日期，生成请求参数
"""

from __future__ import annotations

import re
from urllib.parse import urlencode

TABLE_DAILY = "日k"
TABLE_MINUTE = "分钟k"
TABLE_ADJUST = "复权"
TABLE_CODES = "股票代码"
TABLE_BOARD = "板块*"
TABLE_DELISTED = "退市*"

MINUTE_FREQUENCIES = {"1m", "5m", "15m", "30m", "60m"}
DAY_FREQUENCIES = {"1d", "1w", "1M"}

_CODE_RE = re.compile(r"^\d{6}$")
_DIGITS_RE = re.compile(r"\D")


def normalize_code(raw: str) -> str:
    """规范化股票代码：剥离 sh/sz 前缀与非数字，保留 6 位。"""
    text = str(raw or "").strip().lower()
    if text.startswith(("sh", "sz")):
        text = text[2:]
    return _DIGITS_RE.sub("", text)


def is_valid_code(code: str) -> bool:
    """判断是否为合法 6 位代码。"""
    return bool(_CODE_RE.match(code or ""))


def normalize_date(raw: str) -> str:
    """规范化日期：返回 8 位或 14 位数字串；非法返回空串。"""
    digits = _DIGITS_RE.sub("", str(raw or ""))
    if len(digits) >= 14:
        return digits[:14]
    if len(digits) >= 8:
        return digits[:8]
    return ""


def key_expr(value: str) -> str:
    """精确键表达式。"""
    return f"key:{value}"


def prefix_expr(value: str) -> str:
    """前缀表达式：'6*' / '60063*' -> 'qz:6' / 'qz:60063'。"""
    return f"qz:{value.rstrip('*')}"


def all_expr() -> str:
    """整层匹配表达式。"""
    return "all:"


def range_expr(start: str, end: str, desc: bool = False) -> str:
    """闭区间表达式；desc=True 使用 fwz，否则 fwd。

    end 为 'N' 或空时表示开放区间。
    """
    lo = start or "N"
    hi = end or "N"
    tag = "fwz" if desc else "fwd"
    return f"{tag}:{lo},{hi}"


def date_key_expr(start: str, end: str, desc: bool = False) -> str:
    """按起止日期生成 k2 表达式。

    - 都不传 -> all:
    - 只传 start -> 前缀 qz:（日K 传 8 位即整天，分钟K 传 8 位即整天）
    - 都传 -> 范围 fwd/fwz
    """
    if not start and not end:
        return all_expr()
    if start and not end:
        return prefix_expr(start)
    return range_expr(start, end or "N", desc=desc)


def build_query(
    cmd: str,
    table: str,
    k1: str | None = None,
    k2: str | None = None,
    fields: str | None = None,
    num: int | None = None,
) -> str:
    """构造 StockDB 查询串（不含 host）。

    始终追加 json=1；字段投影走服务端 ap=get.<fields>。
    """
    params: list[tuple[str, str]] = [("cmd", cmd), ("t", table)]
    if k1:
        params.append(("k1", k1))
    if k2:
        params.append(("k2", k2))
    if fields:
        params.append(("ap", f"get.{fields}"))
    if num:
        params.append(("num", str(num)))
    params.append(("json", "1"))
    return "?" + urlencode(params)
```

### 13.3 后端：`src/integrations/stockdb/client.py`

```python
# -*- coding: utf-8 -*-
"""StockDB HTTP 客户端。

职责：
1. 发送只读命令（get/vals/keys/len）并解析 JSON
2. 超时控制与连续失败冷却短路
3. 把传输层异常翻译为统一的 StockDbError
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.integrations.stockdb import codec
from src.integrations.stockdb.config import StockDbSettings, settings_from_env

logger = logging.getLogger(__name__)


class StockDbError(Exception):
    """StockDB 访问错误，携带面向 API 层的错误码与 HTTP 状态。"""

    def __init__(self, code: str, message: str, status: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class StockDbClient:
    """StockDB 只读客户端（进程内惰性单例）。"""

    def __init__(self, settings: StockDbSettings | None = None) -> None:
        self._settings = settings or settings_from_env()
        self._session = requests.Session()
        self._fail_count = 0
        self._cooldown_until = 0.0

    @property
    def settings(self) -> StockDbSettings:
        return self._settings

    def _guard(self) -> None:
        """开关与冷却短路检查。"""
        if not self._settings.enabled:
            raise StockDbError("stockdb_disabled", "本地 StockDB 功能未启用", 503)
        if time.monotonic() < self._cooldown_until:
            raise StockDbError(
                "stockdb_unavailable",
                f"本地 StockDB 连续失败，已在冷却中（{self._settings.cooldown_sec}s）",
                503,
            )

    def request(self, query: str) -> Any:
        """执行查询串，返回已解析的 JSON；异常统一为 StockDbError。"""
        self._guard()
        url = f"{self._settings.base_url}/{query.lstrip('/')}"
        try:
            response = self._session.get(url, timeout=self._settings.timeout_ms / 1000)
        except requests.exceptions.RequestException as exc:
            self._mark_failure()
            raise StockDbError(
                "stockdb_unavailable",
                f"本地 StockDB 服务未启动或不可达（{self._settings.base_url}）",
                503,
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            self._mark_failure()
            raise StockDbError("stockdb_bad_response", "StockDB 返回内容不是合法 JSON", 502) from exc

        self._fail_count = 0
        return payload

    def _mark_failure(self) -> None:
        """累计失败并在达到阈值后进入冷却。"""
        self._fail_count += 1
        if self._fail_count >= 3:
            self._cooldown_until = time.monotonic() + self._settings.cooldown_sec
            self._fail_count = 0
            logger.warning("StockDB 连续失败，进入 %ss 冷却", self._settings.cooldown_sec)

    def ping(self) -> tuple[bool, int]:
        """连通性探测，返回 (是否连通, 耗时毫秒)。"""
        started = time.monotonic()
        try:
            self.request(codec.build_query("get", codec.TABLE_CODES))
        except StockDbError:
            return False, int((time.monotonic() - started) * 1000)
        return True, int((time.monotonic() - started) * 1000)


_CLIENT: StockDbClient | None = None


def get_client() -> StockDbClient:
    """获取进程内单例客户端。"""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = StockDbClient()
    return _CLIENT
```

### 13.4 后端：`src/integrations/stockdb/transform.py`

```python
# -*- coding: utf-8 -*-
"""StockDB 数据后处理。

职责：
1. 按 date 显式排序（服务端顺序不可信）
2. 复权换算（qfq / hfq）
3. 周期聚合（1m -> 5m/15m/30m/60m；1d -> 1w/1M）
4. 字段投影、生成 columns、按上限截断
"""

from __future__ import annotations

import bisect
import datetime
from typing import Any, Iterable

PRICE_FIELDS = ("open", "high", "low", "close", "pre_close")
SUM_FIELDS = ("volume", "amount")


def sort_rows(rows: list[dict[str, Any]], desc: bool) -> list[dict[str, Any]]:
    """按 date 排序；缺失或非数字 date 的行排到末尾。"""

    def sort_key(row: dict[str, Any]) -> tuple[int, Any]:
        raw = row.get("date")
        try:
            return (0, int(raw))
        except (TypeError, ValueError):
            return (1, str(raw))

    return sorted(rows, key=sort_key, reverse=desc)


def apply_adjust(
    rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
    fq: str,
) -> list[dict[str, Any]]:
    """按复权事件换算价格。

    qfq: price *= cum_d / cum_last（最新价不变，历史价下移）
    hfq: price *= cum_d          （最早价不变，后续价上移）
    复权表为空或 fq=none 时原样返回。
    """
    if fq not in ("qfq", "hfq") or not events:
        return rows

    ordered = sorted(
        (e for e in events if _to_int(e.get("date")) is not None),
        key=lambda e: int(e["date"]),
    )
    if not ordered:
        return rows

    event_dates = [int(e["date"]) for e in ordered]
    event_cums = [_to_float(e.get("cum")) or 1.0 for e in ordered]
    cum_last = event_cums[-1] or 1.0

    result: list[dict[str, Any]] = []
    for row in rows:
        date = _to_int(row.get("date"))
        if date is None:
            result.append(row)
            continue
        # 日K 是 8 位，分钟K 是 14 位，统一截取前 8 位比对事件日期
        day = int(str(date)[:8])
        idx = bisect.bisect_right(event_dates, day) - 1
        cum_d = event_cums[idx] if idx >= 0 else 1.0
        factor = cum_d / cum_last if fq == "qfq" else cum_d

        new_row = dict(row)
        for field in PRICE_FIELDS:
            value = _to_float(new_row.get(field))
            if value is None:
                continue
            new_row[field] = round(value * factor, 6)
        close = _to_float(new_row.get("close"))
        pre_close = _to_float(new_row.get("pre_close"))
        if close is not None and pre_close:
            new_row["pct_chg"] = round((close - pre_close) / pre_close * 100, 4)
        result.append(new_row)
    return result


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None  # 过滤 NaN


def resample(rows: list[dict[str, Any]], frequency: str) -> list[dict[str, Any]]:
    """周期聚合。frequency 为 1d/1m 时原样返回。"""
    if frequency in ("1d", "1m", None, ""):
        return rows
    if frequency in ("5m", "15m", "30m", "60m"):
        return _resample_minute(rows, int(frequency[:-1]))
    if frequency == "1w":
        return _resample_day(rows, "week")
    if frequency == "1M":
        return _resample_day(rows, "month")
    raise ValueError(f"不支持的周期: {frequency}")


def _bucket_key(date_int: int, mode: str) -> str:
    """按模式生成日粒度桶键，保证跨周/跨月不错误合并。"""
    text = str(date_int)[:8]
    if mode == "month":
        return text[:6]
    year, month, day = int(text[:4]), int(text[4:6]), int(text[6:8])
    iso = datetime.date(year, month, day).isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _merge_bucket(bucket: list[dict[str, Any]]) -> dict[str, Any]:
    """把一个桶内的行合并为一行。"""
    merged: dict[str, Any] = dict(bucket[-1])
    for field in ("open",):
        merged[field] = bucket[0].get(field)
    for field in ("high",):
        values = [_to_float(r.get(field)) for r in bucket]
        merged[field] = max((v for v in values if v is not None), default=None)
    for field in ("low",):
        values = [_to_float(r.get(field)) for r in bucket]
        merged[field] = min((v for v in values if v is not None), default=None)
    for field in SUM_FIELDS:
        total = sum(_to_float(r.get(field)) or 0.0 for r in bucket)
        if any(r.get(field) is not None for r in bucket):
            merged[field] = total
    return merged


def _resample_minute(rows: list[dict[str, Any]], step: int) -> list[dict[str, Any]]:
    """分钟聚合：按交易日内的分钟序号分桶，跨日不合并。"""
    buckets: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for row in rows:
        date = _to_int(row.get("date"))
        if date is None or len(str(date)) < 12:
            continue
        minutes = int(str(date)[8:10]) * 60 + int(str(date)[10:12])
        key = f"{str(date)[:8]}|{minutes // step}"
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(row)
    return [_merge_bucket(buckets[key]) for key in order]


def _resample_day(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    """日K 聚合为周/月。"""
    buckets: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for row in rows:
        date = _to_int(row.get("date"))
        if date is None:
            continue
        key = _bucket_key(int(str(date)[:8]), mode)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(row)
    return [_merge_bucket(buckets[key]) for key in order]


def build_columns(rows: Iterable[dict[str, Any]], preferred: tuple[str, ...]) -> list[str]:
    """按字段存在性生成列顺序：优先已知字段，其余追加。"""
    seen: set[str] = set()
    columns: list[str] = []
    for row in rows:
        for field in row.keys():
            if field not in seen:
                seen.add(field)
    for field in preferred:
        if field in seen and field not in columns:
            columns.append(field)
    for field in seen:
        if field not in columns:
            columns.append(field)
    return columns


def project(rows: list[dict[str, Any]], fields: list[str] | None) -> list[dict[str, Any]]:
    """按字段投影；fields 为空时原样返回。"""
    if not fields:
        return rows
    return [{f: row.get(f) for f in fields} for row in rows]


def truncate(rows: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], bool]:
    """按上限截断，返回 (结果, 是否被截断)。"""
    if limit and len(rows) > limit:
        return rows[:limit], True
    return rows, False
```

### 13.5 后端：`src/integrations/stockdb/service.py`

```python
# -*- coding: utf-8 -*-
"""StockDB 业务编排。

职责：
1. 把 API 层请求翻译为 StockDB 查询
2. 串联 取数 -> 排序 -> 复权 -> 聚合 -> 投影 -> 截断
3. 查询缓存
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.integrations.stockdb import codec, transform
from src.integrations.stockdb.cache import get_cache, _MISS
from src.integrations.stockdb.client import StockDbClient, StockDbError, get_client
from src.integrations.stockdb.errors import InvalidParameterError

FIELD_ORDER = (
    "date", "code", "name", "open", "high", "low", "close", "pre_close",
    "volume", "amount", "turnover", "pct_chg", "amplitude",
    "is_st", "vol_ratio", "total_share", "float_share",
    "total_mv", "float_mv", "pe_ttm", "pb",
)

A_SHARE_PREFIXES = ("0", "3", "6")
ALL_PREFIXES = ("0", "1", "3", "5", "6", "9")


@dataclass
class BarsResult:
    """bars 查询结果。"""

    columns: list[str]
    rows: Any
    total: int
    truncated: bool
    partial: bool
    elapsed_ms: int
    query: dict[str, Any] = field(default_factory=dict)
```

### 13.5.1 后端：`src/integrations/stockdb/errors.py`

```python
# -*- coding: utf-8 -*-
"""StockDB 集成层参数校验错误。"""

from __future__ import annotations


class InvalidParameterError(Exception):
    """入参非法；由路由层转换为 400 invalid_parameter。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
```

### 13.6 后端：`src/integrations/stockdb/cache.py`

```python
# -*- coding: utf-8 -*-
"""进程内 TTL 缓存。

职责：为查询结果提供按 key 的 TTL 缓存，避免重复访问 StockDB。
"""

from __future__ import annotations

import threading
import time
from typing import Any

_MISS = object()


class TtlCache:
    """线程安全的 TTL 缓存；过期项在读取时惰性清理。"""

    def __init__(self, max_items: int = 512) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._max_items = max_items
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return _MISS
            expire_at, value = item
            if expire_at < time.time():
                self._data.pop(key, None)
                return _MISS
            return value

    def set(self, key: str, value: Any, ttl_sec: int) -> None:
        with self._lock:
            if len(self._data) >= self._max_items:
                oldest = min(self._data.items(), key=lambda kv: kv[1][0])[0]
                self._data.pop(oldest, None)
            self._data[key] = (time.time() + ttl_sec, value)

    def clear(self, prefix: str = "") -> int:
        with self._lock:
            if not prefix:
                count = len(self._data)
                self._data.clear()
                return count
            keys = [k for k in self._data if k.startswith(prefix)]
            for key in keys:
                self._data.pop(key, None)
            return len(keys)


_CACHE: TtlCache | None = None


def get_cache() -> TtlCache:
    """获取进程内单例缓存。"""
    global _CACHE
    if _CACHE is None:
        _CACHE = TtlCache()
    return _CACHE
```

### 13.7 后端：service 核心取数（`src/integrations/stockdb/service.py` 续）

```python
def _source_table_frequency(frequency: str) -> tuple[str, str]:
    """返回 (源表名, 源周期)：分钟级/周月季均先取最细粒度。"""
    if frequency == "1d":
        return codec.TABLE_DAILY, "1d"
    if frequency == "1m":
        return codec.TABLE_MINUTE, "1m"
    if frequency in codec.MINUTE_FREQUENCIES:
        return codec.TABLE_MINUTE, "1m"
    if frequency in ("1w", "1M"):
        return codec.TABLE_DAILY, "1d"
    raise InvalidParameterError(f"不支持的周期: {frequency}")


def _fetch_raw(
    client: StockDbClient,
    table: str,
    code: str,
    start: str,
    end: str,
    limit: int,
) -> list[dict[str, Any]]:
    """取单个代码或前缀的原始行（服务端不保证顺序，此处不排序）。"""
    # 前缀查询必须给出日期约束，避免全量扫描
    k1 = codec.prefix_expr(code) if code.endswith("*") else codec.key_expr(code)
    k2 = codec.date_key_expr(start, end)
    query = codec.build_query("vals", table, k1=k1, k2=k2, num=limit or None)
    payload = client.request(query)
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _fetch_adjust_events(client: StockDbClient, code: str) -> list[dict[str, Any]]:
    """读取复权事件表。"""
    query = codec.build_query(
        "vals", codec.TABLE_ADJUST, k1=codec.key_expr(code), k2=codec.all_expr()
    )
    payload = client.request(query)
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def fetch_bars(
    *,
    code: str,
    start: str = "",
    end: str = "",
    frequency: str = "1d",
    fq: str = "none",
    fields: str = "",
    limit: int = 500,
    desc: bool = True,
    client: StockDbClient | None = None,
) -> BarsResult:
    """查询行情。code 支持单代码、逗号分隔多代码、'6*' 前缀。"""
    client = client or get_client()
    settings = client.settings
    started = time.monotonic()

    if fq not in ("none", "qfq", "hfq"):
        raise InvalidParameterError("复权类型必须是 none / qfq / hfq")
    limit = max(1, min(limit or 500, settings.max_rows))

    codes = [c for c in (codec.normalize_code(c) for c in code.split(",")) if c]
    if not codes:
        raise InvalidParameterError("代码不能为空")
    for single in codes:
        if not single.endswith("*") and not codec.is_valid_code(single):
            raise InvalidParameterError(f"代码必须是 6 位数字: {single}")
        # 前缀查询必须带日期约束，避免无界全量扫描
        if single.endswith("*") and not start and end != "N" and not end:
            raise InvalidParameterError("前缀代码（如 6*）必须同时提供 start 或 end 日期约束")

    start_norm = codec.normalize_date(start)
    end_norm = codec.normalize_date(end)
    if start and not start_norm:
        raise InvalidParameterError(f"开始日期非法: {start}")
    if end and end != "N" and not end_norm:
        raise InvalidParameterError(f"结束日期非法: {end}")
    if start_norm and end_norm and start_norm > end_norm:
        start_norm, end_norm = end_norm, start_norm

    table, _source_freq = _source_table_frequency(frequency)
    # 聚合前需要更长的原始数据，按聚合倍率放大服务端取数上限
    raw_limit = limit if frequency in ("1d", "1m") else limit * 240
    raw_limit = min(max(raw_limit, limit), settings.max_rows)

    # 缓存 TTL：分钟级数据变化快，TTL 收敛到 30s；日K 用配置值
    cache_ttl = min(settings.cache_ttl_sec, 30) if frequency != "1d" else settings.cache_ttl_sec
    cache_key = "|".join(["bars", code, start_norm, end_norm, frequency, fq, fields, str(limit), str(desc)])
    cached = get_cache().get(cache_key)
    if cached is not _MISS:
        return cached

    rows_by_code: dict[str, list[dict[str, Any]]] = {}
    partial = False
    for single in codes:
        try:
            rows = _fetch_raw(client, table, single, start_norm, end_norm, raw_limit)
        except StockDbError:
            if len(codes) == 1:
                raise
            partial = True
            continue
        if fq != "none" and not single.endswith("*"):
            try:
                events = _fetch_adjust_events(client, single)
            except StockDbError:
                events = []
            rows = transform.apply_adjust(rows, events, fq)
        rows = transform.sort_rows(rows, desc=False)
        rows = transform.resample(rows, frequency)
        rows_by_code[single] = rows

    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    query_meta = {
        "code": code,
        "start": start_norm,
        "end": end_norm,
        "frequency": frequency,
        "fq": fq,
        "desc": desc,
    }

    if len(codes) == 1 and not codes[0].endswith("*"):
        rows = rows_by_code.get(codes[0], [])
        rows = transform.sort_rows(rows, desc=desc)
        rows, truncated = transform.truncate(rows, limit)
        rows = transform.project(rows, field_list)
        columns = transform.build_columns(rows, FIELD_ORDER)
        result = BarsResult(
            columns=columns,
            rows=rows,
            total=len(rows),
            truncated=truncated,
            partial=partial,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            query=query_meta,
        )
        get_cache().set(cache_key, result, cache_ttl)
        return result

    projected: dict[str, list[dict[str, Any]]] = {}
    truncated = False
    for single, rows in rows_by_code.items():
        rows = transform.sort_rows(rows, desc=desc)
        rows, cut = transform.truncate(rows, limit)
        truncated = truncated or cut
        projected[single] = transform.project(rows, field_list)

    all_rows = [row for rows in projected.values() for row in rows]
    columns = transform.build_columns(all_rows, FIELD_ORDER)
    result = BarsResult(
        columns=columns,
        rows=projected,
        total=sum(len(rows) for rows in projected.values()),
        truncated=truncated,
        partial=partial,
        elapsed_ms=int((time.monotonic() - started) * 1000),
        query=query_meta,
    )
    get_cache().set(cache_key, result, cache_ttl)
    return result
```

### 13.8 后端：`api/stockdb/schemas.py`

```python
# -*- coding: utf-8 -*-
"""StockDB 路由层 Schema。

职责：定义 /api/stockdb/* 的出入参模型。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Frequency = Literal["1d", "1m", "5m", "15m", "30m", "60m", "1w", "1M"]
FqType = Literal["none", "qfq", "hfq"]
MarketType = Literal["a-share", "all"]
BoardCategory = Literal["concept", "sw1", "sw2", "sw3"]


class HealthResponse(BaseModel):
    """数据源连通性与概览。"""

    enabled: bool
    connected: bool
    base_url: str = Field(alias="baseUrl")
    latency_ms: int | None = Field(default=None, alias="latencyMs")
    latest_trade_date: str | None = Field(default=None, alias="latestTradeDate")
    code_count: int | None = Field(default=None, alias="codeCount")
    checked_at: str = Field(alias="checkedAt")

    model_config = {"populate_by_name": True}


class CodeItem(BaseModel):
    """证券代码条目。"""

    code: str
    name: str = ""


class CodesResponse(BaseModel):
    """代码全集响应。"""

    items: list[CodeItem]
    total: int


class DatesResponse(BaseModel):
    """个股交易日列表响应。"""

    code: str
    dates: list[str]
    total: int


class BarsQuery(BaseModel):
    """bars 查询回显。"""

    code: str
    start: str = ""
    end: str = ""
    frequency: str
    fq: str
    desc: bool


class BarsResponse(BaseModel):
    """行情响应。rows 为单代码列表或多代码映射。"""

    query: BarsQuery
    columns: list[str]
    rows: Any
    total: int
    truncated: bool
    partial: bool
    elapsed_ms: int = Field(alias="elapsedMs")

    model_config = {"populate_by_name": True}


class BoardItem(BaseModel):
    """板块条目。"""

    code: str
    name: str
    source: str = ""
    type: str = ""
    group: str = ""
    category: str = ""


class BoardsResponse(BaseModel):
    """板块列表响应。"""

    items: list[BoardItem]
    total: int
```

### 13.9 后端：`api/stockdb/router.py`

```python
# -*- coding: utf-8 -*-
"""StockDB 行情浏览路由。

职责：
1. 暴露 /api/stockdb/* 只读接口
2. 参数校验与错误码映射（不依赖 api/v1 任何业务模块）
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

from api.stockdb.schemas import (
    BarsResponse,
    BoardCategory,
    BoardsResponse,
    CodesResponse,
    DatesResponse,
    Frequency,
    FqType,
    HealthResponse,
    MarketType,
)
from src.integrations.stockdb import service
from src.integrations.stockdb.client import StockDbError, get_client
from src.integrations.stockdb.errors import InvalidParameterError

router = APIRouter()


def _to_api_error(exc: StockDbError):
    """把集成层错误转换为 HTTPException。"""
    from fastapi import HTTPException

    return HTTPException(
        status_code=exc.status,
        detail={"error": exc.code, "message": exc.message},
    )


@router.get("/health", response_model=HealthResponse, summary="StockDB 数据源连通性")
def get_health() -> HealthResponse:
    """探测 StockDB 是否可达，并回显最新交易日与代码数量。"""
    client = get_client()
    connected, latency = client.ping()
    latest: str | None = None
    code_count: int | None = None
    if connected:
        try:
            latest, code_count = service.fetch_overview(client)
        except StockDbError:
            latest, code_count = None, None
    return HealthResponse(
        enabled=client.settings.enabled,
        connected=connected,
        base_url=client.settings.base_url,
        latency_ms=latency,
        latest_trade_date=latest,
        code_count=code_count,
        checked_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )


@router.get("/bars", response_model=BarsResponse, summary="查询行情")
def get_bars(
    code: str = Query(..., description="6 位代码、逗号分隔多代码或 '6*' 前缀"),
    start: str = Query("", description="YYYYMMDD 或 14 位时间戳"),
    end: str = Query("", description="YYYYMMDD、14 位时间戳或 N"),
    frequency: Frequency = Query("1d"),
    fq: FqType = Query("none"),
    fields: str = Query("", description="逗号分隔字段，为空返回全字段"),
    limit: int = Query(500, ge=1),
    desc: bool = Query(True),
) -> BarsResponse:
    """查询日K/分钟K，支持周期聚合与复权。"""
    try:
        result = service.fetch_bars(
            code=code,
            start=start,
            end=end,
            frequency=frequency,
            fq=fq,
            fields=fields,
            limit=limit,
            desc=desc,
        )
    except InvalidParameterError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_parameter", "message": exc.message},
        ) from exc
    except StockDbError as exc:
        raise _to_api_error(exc) from exc

    return BarsResponse(
        query=result.query,
        columns=result.columns,
        rows=result.rows,
        total=result.total,
        truncated=result.truncated,
        partial=result.partial,
        elapsed_ms=result.elapsed_ms,
    )


@router.get("/codes", response_model=CodesResponse, summary="证券代码全集")
def get_codes(
    market: MarketType = Query("a-share"),
    keyword: str = Query("", description="代码或名称模糊过滤"),
    limit: int = Query(0, ge=0, description="0 表示不限制"),
) -> CodesResponse:
    """返回代码全集（含名称），用于前端联想。"""
    try:
        items = service.fetch_codes(market=market, keyword=keyword, limit=limit)
    except StockDbError as exc:
        raise _to_api_error(exc) from exc
    return CodesResponse(items=items, total=len(items))


@router.get("/dates", response_model=DatesResponse, summary="个股交易日列表")
def get_dates(
    code: str = Query(..., description="6 位代码"),
    limit: int = Query(2000, ge=1, le=5000),
) -> DatesResponse:
    """返回个股历史交易日（倒序），用于日期联想。"""
    try:
        dates = service.fetch_dates(code=code, limit=limit)
    except InvalidParameterError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_parameter", "message": exc.message},
        ) from exc
    except StockDbError as exc:
        raise _to_api_error(exc) from exc
    return DatesResponse(code=code, dates=dates, total=len(dates))


@router.get("/boards", response_model=BoardsResponse, summary="板块列表")
def get_boards(
    category: BoardCategory | None = Query(None),
    keyword: str = Query(""),
    limit: int = Query(500, ge=1),
) -> BoardsResponse:
    """返回板块（概念 / 申万一二级）列表。"""
    try:
        items = service.fetch_boards(category=category, keyword=keyword, limit=limit)
    except StockDbError as exc:
        raise _to_api_error(exc) from exc
    return BoardsResponse(items=items, total=len(items))
```

### 13.10 后端：service 其余方法签名（概览 / 代码 / 日期 / 板块）

```python
def fetch_overview(client: StockDbClient) -> tuple[str | None, int | None]:
    """返回 (最新交易日, 代码数量)。

    最新交易日：取一只高流动性样本股最后一条日K的 date。
    代码数量：按 market 前缀统计 股票代码 表条目数。
    """
    sample = "600633"
    query = codec.build_query(
        "vals", codec.TABLE_DAILY,
        k1=codec.key_expr(sample), k2=codec.all_expr(),
        fields="date", num=-1,
    )
    payload = client.request(query)
    latest = None
    if isinstance(payload, list) and payload and isinstance(payload[0], list):
        latest = str(payload[0][0])

    codes = client.request(codec.build_query("get", codec.TABLE_CODES))
    count = None
    if isinstance(codes, dict):
        count = sum(len(v) for v in codes.values() if isinstance(v, list))
    return latest, count


def fetch_codes(
    *, market: str = "a-share", keyword: str = "", limit: int = 0
) -> list[dict[str, str]]:
    """代码全集：先取 股票代码 索引，再用最近交易日快照补全名称。

    返回 [{"code": "...", "name": "..."}]；由路由层的 Pydantic 模型校验。
    集成层不依赖 api 层模型，保持单向依赖。
    """
    client = get_client()
    prefixes = A_SHARE_PREFIXES if market == "a-share" else ALL_PREFIXES
    index = client.request(codec.build_query("get", codec.TABLE_CODES))
    if not isinstance(index, dict):
        return []
    codes: list[str] = []
    for prefix in prefixes:
        codes.extend(c for c in index.get(prefix, []) if isinstance(c, str))
    codes = sorted(set(codes))

    # 名称：最近交易日快照投影，按前缀分片（≤6 个请求）
    names: dict[str, str] = {}
    latest, _ = fetch_overview(client)
    if latest:
        for prefix in prefixes:
            query = codec.build_query(
                "vals", codec.TABLE_DAILY,
                k1=codec.prefix_expr(prefix), k2=codec.key_expr(latest),
                fields="code,name",
            )
            try:
                payload = client.request(query)
            except StockDbError:
                continue
            if isinstance(payload, list):
                for row in payload:
                    if isinstance(row, list) and len(row) >= 2:
                        names[str(row[0])] = str(row[1] or "")

    items = [{"code": c, "name": names.get(c, "")} for c in codes]
    if keyword:
        text = keyword.strip()
        items = [
            item for item in items
            if text in item["code"] or text in item["name"]
        ]
    if limit:
        items = items[:limit]
    return items
```

> `fetch_dates` / `fetch_boards` 同理：`fetch_dates` 用 `t=日k&k1=key:{code}&k2=all:&ap=get.date&num=-{limit}` 后倒序去重；`fetch_boards` 用 `t=板块*` 全量后按 `category`/`keyword` 内存过滤。实现时务必复用 `codec.build_query`，不要手写查询串。

### 13.11 后端：`api/app.py` 挂载（唯一改动点）

```python
# api/app.py —— 在 app.include_router(api_v1_router, prefix="/api/v1") 之后追加
from api.stockdb.router import router as stockdb_router

    app.include_router(stockdb_router, prefix="/api/stockdb", tags=["StockDB"])
```

> 注意：`api/middlewares/auth.py` 只拦截 `/api/v1/`，`/api/stockdb/*` 默认不受 `ADMIN_AUTH` 保护。若设置 `STOCKDB_REQUIRE_AUTH=true`，需在 `router.py` 内通过 `dependencies=[Depends(...)]` 自行挂载。

### 13.12 前端：`apps/hrs-web/src/api/stockdb.ts`

```ts
/**
 * @fileoverview 本地 StockDB 行情数据 API。
 * 所有请求走 /api/stockdb/*，由 HermesX 后端代理到本地 StockDB 服务（127.0.0.1:7899）。
 * @module api
 */

import apiClient from './index';

/** 周期频率 */
export type StockDbFrequency = '1d' | '1m' | '5m' | '15m' | '30m' | '60m' | '1w' | '1M';

/** 复权类型 */
export type StockDbFq = 'none' | 'qfq' | 'hfq';

/** 市场范围 */
export type StockDbMarket = 'a-share' | 'all';

/** 数据源连通性与概览 */
export type StockDbHealth = {
  enabled: boolean;
  connected: boolean;
  baseUrl: string;
  latencyMs: number | null;
  latestTradeDate: string | null;
  codeCount: number | null;
  checkedAt: string;
};

/** 代码条目 */
export type StockDbCodeItem = { code: string; name: string };

/** bars 查询回显 */
export type StockDbBarsQuery = {
  code: string;
  start: string;
  end: string;
  frequency: string;
  fq: string;
  desc: boolean;
};

/** 单行行情（字段由后端 columns 决定，此处按宽松类型处理） */
export type StockDbBarRow = Record<string, string | number | boolean | null>;

/** 行情响应 */
export type StockDbBarsResponse = {
  query: StockDbBarsQuery;
  columns: string[];
  /** 单代码为数组；多代码为 { code: rows } */
  rows: StockDbBarRow[] | Record<string, StockDbBarRow[]>;
  total: number;
  truncated: boolean;
  partial: boolean;
  elapsedMs: number;
};

/** bars 查询参数 */
export type StockDbBarsParams = {
  code: string;
  start?: string;
  end?: string;
  frequency?: StockDbFrequency;
  fq?: StockDbFq;
  fields?: string;
  limit?: number;
  desc?: boolean;
};

export const stockdbApi = {
  /** 数据源连通性 */
  getHealth: async (): Promise<StockDbHealth> => {
    const response = await apiClient.get<StockDbHealth>('/api/stockdb/health');
    return response.data;
  },

  /** 代码全集（含名称） */
  getCodes: async (params: { market?: StockDbMarket; keyword?: string } = {}): Promise<StockDbCodeItem[]> => {
    const response = await apiClient.get<{ items: StockDbCodeItem[]; total: number }>(
      '/api/stockdb/codes',
      { params: { market: params.market ?? 'a-share', keyword: params.keyword ?? '' } },
    );
    return response.data.items;
  },

  /** 个股交易日列表（倒序） */
  getDates: async (code: string, limit = 2000): Promise<string[]> => {
    const response = await apiClient.get<{ dates: string[] }>('/api/stockdb/dates', {
      params: { code, limit },
    });
    return response.data.dates;
  },

  /** 行情查询 */
  getBars: async (params: StockDbBarsParams): Promise<StockDbBarsResponse> => {
    const response = await apiClient.get<StockDbBarsResponse>('/api/stockdb/bars', {
      params: {
        code: params.code,
        start: params.start ?? '',
        end: params.end ?? '',
        frequency: params.frequency ?? '1d',
        fq: params.fq ?? 'none',
        fields: params.fields ?? '',
        limit: params.limit ?? 500,
        desc: params.desc ?? true,
      },
    });
    return response.data;
  },
};
```

### 13.13 前端：`StockDataViewPage.tsx` 核心逻辑

```tsx
/**
 * @fileoverview 本地行情数据浏览页：对接本地 StockDB 数据源，
 * 支持按代码 + 日期区间 + 周期 + 复权查询并表格展示，支持导出 CSV。
 * @module pages
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Database } from 'lucide-react';
import { stockdbApi, type StockDbBarRow, type StockDbFq, type StockDbFrequency } from '../api/stockdb';
import { Card, HrsButton, InlineAlert } from '@components';
import { EmptyState, PageHeader } from '@components/page-layout';
import { AppPage } from '@components/layout/AppPage';
import { Table, type TableColumnDef } from '@components/basic/Table';

/** 字段中文表头映射 */
const FIELD_LABELS: Record<string, string> = {
  date: '日期/时间', code: '代码', name: '名称',
  open: '开盘价', high: '最高价', low: '最低价', close: '收盘价', pre_close: '前收盘价',
  volume: '成交量', amount: '成交额', turnover: '换手率',
  pct_chg: '涨幅%', amplitude: '振幅%', is_st: '是否ST', vol_ratio: '量比',
  total_share: '总股本', float_share: '流通股本',
  total_mv: '总市值', float_mv: '流通市值', pe_ttm: '市盈率', pb: '市净率',
};

/** 日期展示：8 位 -> YYYY-MM-DD；14 位 -> YYYY-MM-DD HH:mm:ss */
function displayDate(value: unknown): string {
  const text = String(value ?? '');
  if (text.length === 8) {
    return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
  }
  if (text.length === 14) {
    return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)} `
      + `${text.slice(8, 10)}:${text.slice(10, 12)}:${text.slice(12, 14)}`;
  }
  return text;
}

/** 单元格渲染：日期特殊处理，其余原样或空占位 */
function renderCell(field: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '-';
  if (field === 'date') return displayDate(value);
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function StockDataViewPage() {
  const [code, setCode] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [frequency, setFrequency] = useState<StockDbFrequency>('1d');
  const [fq, setFq] = useState<StockDbFq>('qfq');

  const [rows, setRows] = useState<StockDbBarRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState('');
  const [noticeText, setNoticeText] = useState('');

  // 竞态保护：过期响应直接丢弃
  const serialRef = useRef(0);

  const loadData = useCallback(async () => {
    const normalized = code.replace(/\D/g, '');
    if (!/^\d{6}$/.test(normalized)) return;

    const serial = ++serialRef.current;
    setIsLoading(true);
    setErrorText('');
    setNoticeText('');
    try {
      const result = await stockdbApi.getBars({
        code: normalized,
        start: start.replace(/\D/g, ''),
        end: end.replace(/\D/g, ''),
        frequency,
        fq,
        limit: 500,
        desc: true,
      });
      if (serial !== serialRef.current) return;

      const list = Array.isArray(result.rows) ? result.rows : [];
      setRows(list);
      setColumns(result.columns);
      if (result.truncated) setNoticeText('结果已超过上限，仅展示部分数据，请收窄日期区间。');
      if (result.partial) setNoticeText((prev) => `${prev} 部分数据读取失败，当前结果不完整。`);
    } catch (error) {
      if (serial !== serialRef.current) return;
      setRows([]);
      setColumns([]);
      setErrorText(error instanceof Error ? error.message : '读取数据失败');
    } finally {
      if (serial === serialRef.current) setIsLoading(false);
    }
  }, [code, start, end, frequency, fq]);

  /** 表格列定义：完全由后端返回的 columns 驱动 */
  const tableColumns = useMemo<TableColumnDef<StockDbBarRow>[]>(
    () =>
      columns.map((field) => ({
        key: field,
        title: FIELD_LABELS[field] ?? field,
        minWidth: field === 'date' ? 150 : 90,
        defaultWidth: field === 'date' ? 160 : 110,
        render: (row) => renderCell(field, row[field]),
      })),
    [columns],
  );

  /** 导出 CSV：BOM + CRLF，兼容 Excel */
  const exportCsv = useCallback(() => {
    if (!rows.length) return;
    const escape = (value: unknown) => {
      const text = String(value ?? '').replace(/"/g, '""');
      return /[,\n"]/.test(text) ? `"${text}"` : text;
    };
    const header = columns.map((f) => FIELD_LABELS[f] ?? f).join(',');
    const body = rows.map((row) => columns.map((f) => escape(row[f])).join(','));
    const blob = new Blob([`\ufeff${[header, ...body].join('\r\n')}\r\n`], {
      type: 'text/csv;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${code}_${frequency}_${start || 'all'}_to_${end || start || 'all'}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [rows, columns, code, frequency, start, end]);

  return (
    <AppPage>
      <PageHeader title="本地行情" icon={Database} />
      <Card>
        {/* 工具条：代码 / 开始日期 / 结束日期 / 周期 / 复权 + 读取 + 导出 */}
        <HrsButton onPress={loadData} isDisabled={isLoading}>读取数据</HrsButton>
        <HrsButton onPress={exportCsv} isDisabled={!rows.length}>导出 CSV</HrsButton>
      </Card>

      {errorText ? <InlineAlert tone="danger">{errorText}</InlineAlert> : null}
      {noticeText ? <InlineAlert tone="warning">{noticeText}</InlineAlert> : null}

      <Card>
        <Table
          columns={tableColumns}
          rows={rows.map((row, index) => ({ id: index, ...row }))}
          isLoading={isLoading}
          renderEmptyState={() => (
            <EmptyState
              title="暂无数据"
              description="请输入代码、时间并选择周期，然后点击读取。"
            />
          )}
        />
      </Card>
    </AppPage>
  );
}
```

> 工具条中的代码/日期联想（虚拟滚动下拉）为 `StockDbCodeInput` 子组件，交互参照 `components/StockSearch/StockSearch.tsx`，数据源替换为 `stockdbApi.getCodes` / `getDates`。

### 13.14 前端：`manifest.ts` 菜单节点

```ts
// apps/hrs-web/src/router/manifest.ts —— productModel.children 内追加
{
  menuId: 'stockData',
  menuName: 'layout.nav.stockData.title',
  routePath: '/stock-data',
  menuIcon: 'Database',
  menuPosition: 'content',
  level: 0,
  menuExpanded: false,
  menuDescription: 'layout.nav.stockData.description',
  menuType: 'page',
  auth: 'protected',
  menuVisible: true,
  menuPagePath: 'pages/StockDataViewPage',
},
```

### 13.15 前端：i18n（三个语言文件各 2 条）

```ts
// src/i18n/uiText-zh.ts
'layout.nav.stockData.title': '本地行情', // 本地行情导航项
'layout.nav.stockData.description': '对接本地 StockDB 的历史行情浏览', // 本地行情导航项描述

// src/i18n/uiText-en.ts
'layout.nav.stockData.title': 'Local Quotes',
'layout.nav.stockData.description': 'Browse historical quotes from the local StockDB',

// src/i18n/uiText-zh-Hant.ts
'layout.nav.stockData.title': '本地行情', // 本地行情導航項
'layout.nav.stockData.description': '對接本地 StockDB 的歷史行情瀏覽', // 本地行情導航項描述
```

### 13.16 落地顺序建议

| 阶段 | 内容 | 产出 |
|---|---|---|
| P1 | `config.py` / `codec.py` / `client.py` / `errors.py` + 单测 | 协议层可用，可用脚本直接 curl 对拍 |
| P2 | `cache.py` / `transform.py` + 单测（排序、聚合、复权） | 纯函数层可用 |
| P3 | `service.py` + `schemas.py` + `router.py` + `app.py` 挂载 | `/api/stockdb/*` 可访问 |
| P4 | 复权对账（AC-3） | 修正复权公式，**未通过不得进入 P5** |
| P5 | 前端 `stockdb.ts` + 页面 + manifest + i18n | 页面可用 |
| P6 | 冒烟 + `npm run lint` + `npm run build` + `./scripts/ci_gate.sh` | 可提交 |

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

### 14.2 新增文件清单（后端，共 9 个）

| 文件路径 | 对应章节 | 说明 |
|---|---|---|
| `src/integrations/stockdb/__init__.py` | §11.1 / §13 | 包初始化（方案正文未单列，但 `from src.integrations.stockdb import codec` 以及 `service.py` 内 `from ... import codec, transform` 都依赖此包存在，必须新建，可为空文件） |
| `src/integrations/stockdb/config.py` | §13.1 | `StockDbSettings` + `settings_from_env`，8 个环境变量读取 |
| `src/integrations/stockdb/codec.py` | §13.2 | 表名常量 + 键表达式编码（`key/qz/all/fwd/fwz`）+ 代码/日期规范化 + `build_query` |
| `src/integrations/stockdb/client.py` | §13.3 | `StockDbClient`（惰性单例）、`StockDbError`、超时与冷却短路、`ping` |
| `src/integrations/stockdb/transform.py` | §13.4 | `sort_rows` / `apply_adjust` / `resample` / `build_columns` / `project` / `truncate` |
| `src/integrations/stockdb/cache.py` | §13.6 | 进程内线程安全 `TtlCache`（单例 `get_cache`） |
| `src/integrations/stockdb/errors.py` | §13.5.1 | `InvalidParameterError` |
| `src/integrations/stockdb/service.py` | §13.5 / §13.7 / §13.10 | 业务编排：`fetch_bars`、`fetch_overview`、`fetch_codes`、`fetch_dates`、`fetch_boards`、聚合放大取数等 |
| `api/stockdb/__init__.py` | §11.1 / §13 | 路由包初始化（空文件，使 `api.stockdb.router` 可被 import） |
| `api/stockdb/schemas.py` | §13.8 | Pydantic 出入参：`HealthResponse` / `CodesResponse` / `DatesResponse` / `BarsResponse` / `BoardsResponse` 等 |
| `api/stockdb/router.py` | §13.9 | `APIRouter`，暴露 `/health` `/bars` `/codes` `/dates` `/boards` + 错误码映射 |

> 注意：`service.py` 正文分 §13.5（类与常量）、§13.7（取数核心）、§13.10（概览/代码/日期/板块）三处给出，落地时合并为单个 `service.py`。

### 14.3 修改文件清单（后端，共 3 个）

| 文件路径 | 改动点 | 对应章节 | 风险 |
|---|---|---|---|
| `api/app.py` | 在 `include_router(api_v1_router, prefix="/api/v1")` 之后追加 `app.include_router(stockdb_router, prefix="/api/stockdb", tags=["StockDB"])` | §3.3-1 / §13.11 | 唯一后端挂载点；不影响 `/api/v1` 与 `ADMIN_AUTH` |
| `src/config.py` | 新增 8 个 `os.getenv`（`STOCKDB_ENABLED`、`STOCKDB_BASE_URL`、`STOCKDB_TIMEOUT_MS`、`STOCKDB_MAX_ROWS`、`STOCKDB_CACHE_TTL_SEC`、`STOCKDB_COOLDOWN_SEC`、`STOCKDB_PASSWORD`、`STOCKDB_REQUIRE_AUTH`），沿用既有 `_FALSEY_ENV_VALUES` 约定 | §3.3-2 / §9 | §3.3 写"6 个"、§9 实际列出 8 个，落地以 8 个为准；`STOCKDB_REQUIRE_AUTH` 在 §13.1 的 `StockDbSettings` 中未建模，若需鉴权需补字段或仅由路由层读取 |
| `.env.example` | 追加"本地 StockDB 行情数据源（可选）"配置块（8 个变量 + 注释） | §3.3-3 / §9 | 必须与 `src/config.py` 的键名保持一致 |

### 14.4 新增文件清单（前端，共 3 个）

| 文件路径 | 对应章节 | 说明 |
|---|---|---|
| `apps/hrs-web/src/api/stockdb.ts` | §13.12 | `stockdbApi`（`getHealth` / `getCodes` / `getDates` / `getBars`）+ 全部 TS 类型 |
| `apps/hrs-web/src/pages/StockDataViewPage.tsx` | §13.13 | 页面主体：工具条 + 表格 + 导出 CSV + 状态机 |
| `apps/hrs-web/src/components/stockdb/StockDbCodeInput.tsx` | §7.5 / §13.13 注 | 代码 + 日期联想子组件（虚拟滚动下拉），交互参照 `StockSearch`，数据源替换为 `stockdbApi.getCodes` / `getDates`；方案正文只给了交互要求，未给完整代码，需实现 |

### 14.5 修改文件清单（前端，共 4 个）

| 文件路径 | 改动点 | 对应章节 |
|---|---|---|
| `apps/hrs-web/src/router/manifest.ts` | `productModel.children` 内追加 `menuId: 'stockData'` 节点（`routePath` `/stock-data`、`menuIcon` `Database`、`menuPagePath` `pages/StockDataViewPage`） | §13.14 |
| `apps/hrs-web/src/i18n/uiText-zh.ts` | 追加 `layout.nav.stockData.title` / `.description` 两条 | §13.15 |
| `apps/hrs-web/src/i18n/uiText-en.ts` | 同上 | §13.15 |
| `apps/hrs-web/src/i18n/uiText-zh-Hant.ts` | 同上 | §13.15 |

> 前端无需改 vite 配置（§7.1 已确认 `/api` 已代理到 `127.0.0.1:8000`）；无需把 `/api/stockdb/*` 登记进 `CACHE_TTL_MAP`（§11.4）。

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
| `docs/CHANGELOG.md` | 在 `[Unreleased]` 段追加一行扁平记录：`[新功能] 新增本地 StockDB 行情浏览页（/stock-data + /api/stockdb/*）` | A.3 |

### 14.8 落地前需澄清的契约漂移点

1. **配置项数量不一致**：§3.3 写"6 个 `os.getenv`"，§9 与 `.env.example` 实际列出 8 个。落地以 8 个为准。
2. **`STOCKDB_REQUIRE_AUTH` 未建模**：§9 定义了该开关，但 §13.1 的 `StockDbSettings` 未含此字段，§13.9 路由层也未挂鉴权依赖。若一期就要支持鉴权，需补 `settings` 字段并在 `router.py` 加 `dependencies=[Depends(...)]`；否则可留待后续。
3. **包初始化文件缺失说明**：`src/integrations/stockdb/__init__.py` 与 `api/stockdb/__init__.py` 在正文与 §13 代码块中均未出现，但 `from src.integrations.stockdb import codec` / `api.stockdb.router` 的导入方式必须有这两个空包文件，否则 `import` 失败。`L3 代码移除`（§10.3）也依赖这两个包目录整体可删除。
4. **`StockDbCodeInput` 子组件无代码**：§13.13 仅在注释中说明该子组件的存在与交互参考，未提供实现骨架。前端 P5 阶段需要先补全该组件，否则页面工具条的联想能力无法实现。
5. **`fetch_dates` / `fetch_boards` 未给完整实现**：§13.10 仅给了 `fetch_overview` 与 `fetch_codes` 的代码，另两个方法以文字描述（"同理"）带过，落地时须按 §13.10 末段要求复用 `codec.build_query` 实现，不得手写查询串。
6. **`service.py` 拆分三处**：§13.5（类定义）、§13.7（取数）、§13.10（概览/代码/日期/板块）的代码需合并为单一 `service.py`，注意避免重复定义（如 `FIELD_ORDER`、`A_SHARE_PREFIXES` 已在 §13.5 给出）。

### 14.9 影响面与回归风险（供评估）

- **对既有功能零侵入**：所有改动独立在 `src/integrations/stockdb/`、`api/stockdb/`、`apps/hrs-web/src/{api,pages,components/stockdb}/` 内；`api/app.py` 仅追加一行 `include_router`；`src/config.py` 仅追加只读环境变量；前端仅在 manifest 追加菜单节点与 i18n 追加两条 key。无既有文件语义被改、无主库新增表。
- **可整体开关 / 摘除**：`STOCKDB_ENABLED=false` 时后端全 503、前端菜单隐藏（L0）；删 `include_router` 一行（L2）；删两个目录 + 前端新增（L3）。因无外部 import 指向它们，删除无悬挂引用。
- **最高风险项**：复权公式与官方 `gp.js` 对账（AC-3，§6.2 / §12.3）尚未执行，是进入 P5 前的硬阻断，落地排期须把"对账 + 修正公式"单列里程碑。
- **未验证环境**：Docker / 桌面端 `127.0.0.1:7899` 可达性、Windows 平台 StockDB 行为未验证；默认 `STOCKDB_ENABLED=false` 部署，不影响既有发布。

---

## 附录 A. 文档信息与变更日志

### A.1 文档信息

| 项 | 内容 |
|---|---|
| 文档名 | 本地 StockDB 行情数据浏览页 · 建设方案 |
| 文件 | `stock_data_view.md`（仓库根目录） |
| 状态 | 方案（未实现），待评审后进入 §13.16 的 P1 |
| 适用版本 | HermesX 当前 main；Python 3.11（`requests` 已在 `requirements.txt`） |
| 依赖文档 | `AGENTS.md`、`docs/CHANGELOG.md`、StockDB `调用方式/python/AI策略python开发接口文档.md`、StockDB `调用方式/ai_自动开发文档/AI策略界面开发纯js接口文档.md` |
| 关联模块 | `src/integrations/stockdb/`（新增）、`api/stockdb/`（新增）、`apps/hrs-web/src/pages/StockDataViewPage.tsx`（新增） |
| 未决事项 | ① 复权公式对账（AC-3）未执行；② Docker/桌面端可达性未验证；③ 是否在设置页暴露配置项待定 |

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

> 实现启动后，本节追加实际变更记录；`docs/CHANGELOG.md` 的 `[Unreleased]` 段按仓库约定追加一行扁平记录（`[新功能] 新增本地 StockDB 行情浏览页...`）。
