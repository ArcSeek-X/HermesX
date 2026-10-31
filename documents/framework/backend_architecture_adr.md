# <a id="adr-001hermesx-后端分层架构与统一数据源策略"></a>ADR-001：HermesX - 后端分层架构与统一数据源策略

> 📝 **方案简述**：本 ADR 是 HermesX 后端的全局架构决策基准，面向整个后端工程而不隶属于任何单一功能方案。它确立四项全局设计立场：一是四层后端架构，即数据库层、数据源对接层、功能接口层与横切基础辅助层；二是 data_provider 为唯一脏活层，所有外部与本地源对接收口于此；三是 K 线、基础信息、代码搜索三类基础能力同构、多源可切换、配置驱动选源与回退并保持统一契约；四是统一入口与存储铁律，即 Repository barrel 收口、StockDB 进程独占、外部 API 仅 TTL 缓存不落表。任何后端改动与之冲突均以本 ADR 为准。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-13

## 方案目录

- [浏览目录](#浏览目录)
- [1. 背景 / 上下文（Context）](#1-背景-上下文context)
  - [1.1 目标（Goals）](#11-目标goals)
- [2. 整体设计](#2-整体设计)
  - [2.1 四层架构总览（职责划分）〔D1〕](#21-四层架构总览职责划分d1)
  - [2.2 data_provider 为唯一脏活层（数据源下沉）〔D2〕](#22-dataprovider-为唯一脏活层数据源下沉d2)
  - [2.3 三类基础能力同构、多源可切换〔D3〕](#23-三类基础能力同构多源可切换d3)
  - [2.4 统一数据契约 + 多源平等 + 自动回退 + 周期全集〔D4〕](#24-统一数据契约-多源平等-自动回退-周期全集d4)
  - [2.5 UI 配置页复用运行时改配置基建〔D5〕](#25-ui-配置页复用运行时改配置基建d5)
  - [2.6 kline.py 瘦身为瘦端点〔D6〕](#26-klinepy-瘦身为瘦端点d6)
  - [2.7 设计前提：项目未上线，无历史包袱，按正确做法落地](#27-设计前提项目未上线无历史包袱按正确做法落地)
- [3. 数据库层设计](#3-数据库层设计)
  - [3.1 仓储落表文件清单与职责（现 `src/infrastructure/persistence/repositories/`）](#31-srcrepositories-落表文件清单与职责)
  - [3.2 storage.py —— 落表基座（连接 + 模型 + 原语）](#32-storagepy-落表基座连接-模型-原语)
  - [3.3 数据库层在四层架构中的定位](#33-数据库层在四层架构中的定位)
- [4. 数据源对接层设计](#4-数据源对接层设计)
  - [4.1 data_provider 目录结构与功能包划分](#41-dataprovider-目录结构与功能包划分)
  - [4.2 base.py 三层关系（common 底座 vs 功能包 base）](#42-basepy-三层关系common-底座-vs-功能包-base)
  - [4.3 两类高频查询接口的归类](#43-两类高频查询接口的归类)
  - [4.4 data_provider 目录铺排总表（落地基准）](#44-dataprovider-目录铺排总表落地基准)
  - [4.5 数据源介绍（本项目对接的数据源头清单）](#45-数据源介绍本项目对接的数据源头清单)
- [5. 功能接口层设计](#5-功能接口层设计)
  - [5.1 定位与边界（区别于 ② 数据源对接层）](#51-定位与边界区别于-②-数据源对接层)
  - [5.2 端点目录结构与两层划分](#52-端点目录结构与两层划分)
  - [5.3 功能接口层铺排总表（枚举所有标准功能接口 · 权威基准）](#53-功能接口层铺排总表枚举所有标准功能接口-权威基准)
  - [5.4 与 ② 数据源对接层的关系（调用链路）](#54-与-②-数据源对接层的关系调用链路)
- [6. 横切基础辅助层设计](#6-横切基础辅助层设计)
- [7. 后果（Consequences）](#7-后果consequences)
  - [正面](#正面)
  - [负面 / 成本](#负面-成本)
  - [风险 / 注意](#风险-注意)
- [8. 备选方案（Alternatives Considered）](#8-备选方案alternatives-considered)
- [9. 落地指引（对 `stock_data_view.md` 的修订要求）](#9-落地指引对-stockdataviewmd-的修订要求)
- [10. 修改范围与改造代办清单（代码执行指引）](#10-修改范围与改造代办清单代码执行指引)
  - [10.1 修改范围总览（按层 + 动作分类）](#101-修改范围总览按层-动作分类)
  - [10.2 改造代办清单（逐项勾选）](#102-改造代办清单逐项勾选)
  - [10.3 建议执行顺序与依赖](#103-建议执行顺序与依赖)
  - [10.4 完成判据](#104-完成判据)
  - [10.5 编制期衍生改动（文档 + 代码收尾，已落地）](#105-编制期衍生改动文档-代码收尾已落地)
- [11. 验证 / 落地检查表](#11-验证-落地检查表)
- [12. 备注项](#12-备注项)
  - [12.1 修订历史（迭代里程碑）](#121-修订历史迭代里程碑)
  - [12.2 ADR ↔ 方案 章节映射](#122-adr-方案-章节映射)
  - [12.3 开放项 / 待定（非阻塞，按需闭合）](#123-开放项-待定非阻塞按需闭合)
  - [12.4 编码公约引用](#124-编码公约引用)


| 项 | 内容 |
|---|---|
| 文档类型 | 架构决策记录（Architecture Decision Record） |
| 编号 | ADR-001 |
| 状态 | **已采纳（Accepted）** |
| 关联方案 | `stock_data_view.md`（本地 StockDB 行情数据浏览页 · 建设方案；本 ADR 的**首个遵守者 / 落地方案**） |
| 适用范围 | HermesX 后端（**全域架构基准**；首个落地范围：行情 / 基础信息 / 代码搜索相关能力） |

> **方案用意**：本 ADR 是 HermesX 后端的**全局架构决策基准（Architecture Decision Record）**，面向整个后端工程，不隶属于任何单一功能方案。它确立四项全局性、普惠性的设计立场：① 四层后端架构（数据库层 / 数据源对接层 / 功能接口层 / 横切基础辅助层）；② `data_provider` 为**唯一脏活层**（所有外部 / 本地源对接收口于此）；③ 基础能力**统一数据源策略**（K 线 / 基础信息 / 代码搜索三类能力同构、多源可切换、配置驱动选源与回退、统一契约）；④ 统一入口与存储铁律（Repository barrel 收口、StockDB 进程独占、外部 API 仅 TTL 缓存不落表）。
>
> **指导方针**：任何后端方案 / 代码改动若与本 ADR 冲突，均以本 ADR 为准；本 ADR 不被任何单一功能方案"拥有"或"限定"。`stock_data_view.md`（本地 StockDB 接入）是本 ADR 的**首个遵守者**——其在"接入本地 StockDB 作为三类能力的 `local` source"范围内严格遵循本 ADR，而非本 ADR 的适用范围边界。

---

## <a id="浏览目录"></a>浏览目录

- [1. 背景](#1-背景--上下文context)
  - [1.1 目标（Goals）](#11-目标goals)
- [2. 整体设计](#2-整体设计)
  - [2.1 四层架构总览（职责划分）](#21-四层架构总览职责划分)
  - [2.2 data_provider 为唯一脏活层（数据源下沉）](#22-data_provider-为唯一脏活层数据源下沉)
  - [2.3 三类基础能力同构、多源可切换](#23-三类基础能力同构多源可切换)
  - [2.4 统一数据契约 + 多源平等 + 自动回退 + 周期全集](#24-统一数据契约--多源平等--自动回退--周期全集)
  - [2.5 UI 配置页复用运行时改配置基建](#25-ui-配置页复用运行时改配置基建)
  - [2.6 kline.py 瘦身为瘦端点](#26-klinepy-瘦身为瘦端点)
  - [2.7 设计前提：未上线、无历史包袱、按正确做法](#27-设计前提未上线无历史包袱按正确做法)
- [3. 数据库层设计](#3-数据库层设计)
  - [3.1 仓储落表文件清单与职责（现 `src/infrastructure/persistence/repositories/`）](#31-srcrepositories-落表文件清单与职责)
  - [3.2 storage.py —— 落表基座（连接 + 模型 + 原语）](#32-storagepy-落表基座-连接-模型-原语)
  - [3.3 数据库层在四层架构中的定位](#33-数据库层在四层架构中的定位)
- [4. 数据源对接层设计](#4-数据源对接层设计)
  - [4.1 data_provider 目录结构与功能包划分](#41-data_provider-目录结构与功能包划分)
  - [4.2 base.py 三层关系（common 底座 vs 功能包 base）](#42-basepy-三层关系common-底座-vs-功能包-base)
  - [4.3 两类高频查询接口的归类](#43-两类高频查询接口的归类)
  - [4.4 data_provider 目录铺排总表（落地基准）](#44-data_provider-目录铺排总表落地基准)
  - [4.5 数据源介绍（本项目对接的数据源头清单）](#45-数据源介绍本项目对接的数据源头清单)
- [5. 功能接口层设计](#5-功能接口层设计)
  - [5.1 定位与边界（区别于 ② 数据源对接层）](#51-定位与边界区别于--数据源对接层)
  - [5.2 端点目录结构与两层划分](#52-端点目录结构与两层划分)
  - [5.3 功能接口层铺排总表（枚举所有标准功能接口 · 权威基准）](#53-功能接口层铺排总表枚举所有标准功能接口--权威基准)
  - [5.4 与 ② 数据源对接层的关系（调用链路）](#54-与--数据源对接层的关系调用链路)
- [6. 横切基础辅助层设计](#6-横切基础辅助层设计)
- [7. 后果（Consequences）](#7-后果consequences)
- [8. 备选方案（Alternatives Considered）](#8-备选方案alternatives-considered)
- [9. 落地指引（对 stock_data_view.md 的修订要求）](#9-落地指引对-stock_data_viewmd-的修订要求)
- [10. 修改范围与改造代办清单（代码执行指引）](#10-修改范围与改造代办清单代码执行指引)
  - [10.1 修改范围总览（按层 + 动作分类）](#101-修改范围总览按层-动作分类)
  - [10.2 改造代办清单（逐项勾选）](#102-改造代办清单逐项勾选)
  - [10.3 建议执行顺序与依赖](#103-建议执行顺序与依赖)
  - [10.4 完成判据](#104-完成判据)
- [11. 验证 / 落地检查表](#11-验证--落地检查表)
- [12. 备注项](#12-备注项)
  - [12.1 修订历史（迭代里程碑）](#121-修订历史迭代里程碑)
  - [12.2 ADR ↔ 方案 章节映射](#122-adr--方案--章节映射)
  - [12.3 开放项 / 待定（非阻塞，按需闭合）](#123-开放项--待定非阻塞按需闭合)
  - [12.4 编码公约引用](#124-编码公约引用)

---

## <a id="1-背景-上下文context"></a>1. 背景 / 上下文（Context）

基于对 HermesX 工程现状的实测（只读核查，未改代码），发现以下问题驱动本决策：

1. **K 线端点硬编码**：`api/v1/endpoints/kline.py` 把取数逻辑（`_fetch_kline_from_sina` / `_fetch_kline_from_eastmoney` / `_fetch_kline_from_tencent`）直接写在端点文件内，三级降级写死、无配置开关、无本地源入口。
2. **数据源对接层已存在但不覆盖 K 线**：`data_provider/` 已有 15+ 个 fetcher（东方财富 `efinance`、新浪 `akshare`、腾讯 `tencent`、tushare、pytdx、baostock…）与 `DataFetcherManager`（能力过滤 + 优先级 + 健康度故障转移），但**只覆盖日线 + 技术指标**，无多周期 K 线（1m~yearly + fqt）与代码搜索能力。
3. **本地 StockDB 未接入**：本地已建 StockDB 服务（`127.0.0.1:7899`，实测含 `日k` / `分钟k` 原生表），但尚未接入任何 HermesX 取数路径。
4. **基础能力散落**：基础信息（股票名 / 行业 / 板块）与代码搜索在自选股、大盘、K 线页、搜索框多处被需要，但各自散落在 `kline.py` 等端点内，没有统一可切换的数据源对接层。
5. **诉求**：K 线 / 基础信息 / 代码搜索三类基础能力都应可对接多个数据源（本地 StockDB / 东方财富 / 新浪 / 腾讯 / StockSDK），通过配置动态切换、并可通过 UI 配置页管理。

**决策驱动力**：消除重复、配置驱动、可扩展、职责清晰，且不惊动既有分析层（`stock_service` / 组合风险 / 预警 / 回测等消费 `data_provider` 日线层的服务）。

### <a id="11-目标goals"></a>1.1 目标（Goals）

本 ADR 旨在达成以下 4 项目标——
- **G1 四层分层**：确立 HermesX 后端「数据库层 / 数据源对接层 / 功能接口层 / 横切基础辅助层」四层，消除端点直连外部源的反模式。
- **G2 唯一脏活层**：确立 `data_provider` 为唯一与外部 / 本地源打交道的脏活层；K 线 / 基础信息 / 代码搜索三类基础能力以「功能 × 数据源」二维组织、多源可切换、配置驱动选源 / 回退。
- **G3 统一契约 + 铺排表**：给出统一契约（`KLinePoint` / `StockInfo` / `CodeSearchResult`）与 `data_provider` 目录铺排总表，作为后续代码拆分的唯一对齐基准。
- **G4 可执行落地**：产出可勾选的修改范围与改造代办清单（§10）+ 验证检查表（§11），使决策无需二次解读即可落地为代码。

---

## <a id="2-整体设计"></a>2. 整体设计

> 本章为「先总后分」中的**总**：给出四层架构总览与六项核心决策（D1–D6）。四层各自的落地设计详述见 §3–§6；后果、备选、落地指引、修改范围依次顺延。

### <a id="21-四层架构总览职责划分d1"></a>2.1 四层架构总览（职责划分）〔D1〕

| 层 | 职责 | 工程现状 / 落点 |
|---|---|---|
| ① **数据库层** | 本地数据源、本地配置、**数据字典**落表；外部 API 拉取只做进程内 TTL 缓存、不落表 | 已有 `storage.py` + `src/infrastructure/persistence/repositories/`；StockDB 数据由 StockDB 进程独占管理，HermesX **不直读文件**，只走其 HTTP 接口 |
| ② **数据源对接层（脏活层）** | **唯一**与外部源 / 本地源对接的封装层——所有 `requests` / 协议对接 / 本地库查询全封装于此 | `data_provider/`：保留既有 15+ fetcher；新增 StockDB 接入 |
| ③ **功能接口层** | 面向功能 / UI 的 HTTP 端点（固定契约，不随数据源变）+ 功能编排（组合数据源与业务规则） | `api/v1/endpoints/`（瘦端点）+ `src/services/`（功能编排） |
| ④ **横切基础辅助层** | `config.py` + `system_config_service` + 【应建，O1】数据字典模块，被以上各层读取 | `config.py` + `system_config_service`；数据字典暂无独立表，按 §2.7 本期应建为独立表（不再以 config 顶替） |

> **层级速览表（一句话职责 + 作用 + 对应目录；目录只列一级，不展开）**
>
> 上表偏"工程现状 / 落点"，此处补一张"干什么 / 作用 / 目录"速览，供代码执行时一眼对齐层级归属（与方案 `stock_data_view.md` §3.1 顶部速览表一致）。

| 层级 | 干什么（职责） | 作用 | 对应目录地址（只到目录） |
|---|---|---|---|
| **① 数据库层** | 本地数据源 / 配置 / 字典落表；外部 API 仅 TTL 缓存、不落表 | 本地存储读写边界；StockDB  由其自身进程独占，HermesX 不直读文件 | `src/infrastructure/persistence/repositories/`（+ 根 `storage.py`） |
| **② 数据源对接层**（脏活层） | 唯一对接外部 / 本地源的封装层：`requests` / 协议 / 本地库查询全在此；选源 / 回退 / TTL 在 Manager 内 | 屏蔽多源差异，对上层给统一契约；加源只写一份 `_normalize_*` 映射 | `data_provider/` |
| **③ 功能接口层**（面向功能与 UI） | 面向功能与 UI 的 HTTP 端点（固定契约，不随源变）+ 功能编排 | 唯一对外、面向 UI 的接口边界；换源对 UI 透明，前端零改 | `api/v1/endpoints/`（+ `src/services/`） |
| **④ 横切基础辅助层** | `config.py` + 运行时配置服务 + 数据字典，被各层读取 | 横切全局可读（配置 / 白名单 / 字典），不属竖向流程 | `src/config/settings.py`（横切配置，全局读取） |

### <a id="22-dataprovider-为唯一脏活层数据源下沉d2"></a>2.2 data_provider 为唯一脏活层（数据源下沉）〔D2〕

- 所有与外部源 / 本地源打交道的对接代码都收口到 `data_provider/`。
- StockDB 接入：`data_provider/stockdb_fetcher.py`（直连 `127.0.0.1:7899`）+ 作为 K 线 / 基础信息 / 代码搜索三能力的 `local` source。
- StockSDK 接入：采用 **Python bridge + Node 18 sidecar** 方案，桥接入口统一收口到 `data_provider/stocksdk_bridge.py`；其上层再按能力拆分为 `kline/stock_info/code_search/realtime/sector` 下的 `stocksdk_source.py`。**禁止**在 `src/services/` 或 `api/v1/endpoints/` 直接调用 Node/CLI。
- **不再新建** `src/integrations/stockdb/` 平级独立包，也**不新建** `market_data/` 平级目录。
- 现有 `kline.py` 的内联取数函数（`_fetch_from_*`）迁移为 `data_provider/kline/<source>.py` 中的 source 实现。

### <a id="23-三类基础能力同构多源可切换d3"></a>2.3 三类基础能力同构、多源可切换〔D3〕

K 线（kline）/ 基础信息（stock_info）/ 代码搜索（code_search）各自独立成包，置于 `data_provider/` 下，结构同构；另设 `common/` 承载跨功能公共底座。目录结构、功能包划分、`base.py` 三层关系、两类高频查询接口归类、目录铺排总表等**落地细节**统一归入 §4 数据源对接层设计（本节的决策要点如下）：

- 三类能力 = 同级、同模式：每个能力 = **1 个统一端点**（`api/v1/endpoints/` 下对应文件）+ **base.py（ABC + Manager，继承 common）** + **N 个源适配器** + 按需 `transform`。选源 / 回退 / 每源自带 TTL 全在各自 `base.py` 的 Manager 内。
- 跨功能的公共逻辑（代码归一 / 缓存 / 限流 / 健康探针）统一沉到 `data_provider/common/`，绝不在各源重复。
- **能力间隔离（不影响其他功能）**：三类能力的"多源平等 / 自动回退 / 周期全集"实现**完全封装在各自功能包文件内**（`data_provider/kline/*`、`stock_info/*`、`code_search/*`），由各自 `base.py` 的 Manager 驱动；项目其他功能仍按其既定专属源接入，若后续纳入 `StockSDK` 也只能以 `<capability>/stocksdk_source.py` 方式进入 ② 层，**互不影响、互不耦合**——即"在哪能力里要多源平等，就在哪能力的文件里实现"，不影响项目中其他使用数据源的地方（详见 §4.5 / §4.4）。

### <a id="24-统一数据契约-多源平等-自动回退-周期全集d4"></a>2.4 统一数据契约 + 多源平等 + 自动回退 + 周期全集〔D4〕

- **统一输出契约**（K 线为例）：`KLinePoint{date, open, high, low, close, volume, amount, pct_chg}`；`pct_chg` **统一在层内计算**（决策方案 A，各源不重复算）。
- **适配层同级、优先级全在配置（核心原则）**：`local / eastmoney / sina / tencent / stocksdk` 在 `data_provider/*/base.py` 的源适配器里**完全同级、无内置权重、无硬编码先后**。调用次序与"重要性 / 主次"**100% 由配置栏决定**——`KLINE_DATA_SOURCE` / `STOCKINFO_DATA_SOURCE` / `CODESEARCH_DATA_SOURCE` 指定主源，`*_SOURCE_PRIORITY` 指定回退链的主次先后。配置改了次序即改，代码层对任何源一视同仁，不得把某源写死为"首选/兜底"。
- **自动回退（按配置的次序，而非按源身份）**：主源失败且 `KLINE_FALLBACK_ENABLED=true` 时，严格按 `KLINE_SOURCE_PRIORITY` 链从"次优先级"开始依次尝试其余源；`false` 时主源失败即硬失败。回退顺序的先后只取决于配置里的排列，与各源在适配器中的注册位置无关。
- **周期全集**（取多源并集，直接 / 间接实现不区分）：
  `1m / 5m / 15m / 30m / 60m / 120m / 5d / daily / weekly / monthly / yearly`（日 / 周 / 月 K 的线上取值为 `daily` / `weekly` / `monthly`，与 `kline.py:get_kline` 的 `period` pattern 一致；`1d` / `1w` / `1M` 仅为人类可读别名，不作为线上取值）
  本地 StockDB 原生仅 `日k` + `分钟k`，其余周期由聚合层补齐（见 §3 实测结论）；`StockSDK` 则作为**桥接型聚合源**参与统一契约，不改变上层接口。

> **范围约束（重要）**：上述"多源平等 + 自动回退 + 周期全集"原则**优先适用于 `K 线 / 基础信息 / 代码搜索` 三类基础能力**。本项目的其他能力——实时行情（akshare / tickflow，后续可补 `stocksdk_source`）、板块（按子场景分源：eastmoney 承接指数/概览/资金流/排行，shidaotec 承接行业/个股/ETF/概念云图，后续可补 `stocksdk_source` 承接标准板块/资金流接口）、财务基本面（专享 tushare）、新闻资讯（专享 wallstreetcn）、机构持仓（专享 tw_institutional）——按各自既有方式接入；其中 `StockSDK` 属于**桥接型扩展源**，只允许经 ② 层 provider 适配后暴露给上层。各源完整清单与归属见 §4.5；能力 × 数据源矩阵见 §4.4。


### <a id="25-ui-配置页复用运行时改配置基建d5"></a>2.5 UI 配置页复用运行时改配置基建〔D5〕

- `/settings` 下新增「数据源」Tab（不另起独立菜单），每组能力含：主源下拉 + 回退链排序 + 开关 + 连接测试。
- 持久化调用既有 `POST /api/v1/config`（写 `.env` + `reload_now`）；选源逻辑每次请求读 `config.*_data_source`，无需重启即切换。
- 新增配置键须登记进 `system_config` 运行时白名单（参考 `src/config/settings.py:_WEBUI_RUNTIME_ENV_FILE_PRIORITY_KEYS`）；`StockSDK` 相关桥接配置（如 `STOCKSDK_ENABLED`、`STOCKSDK_NODE_BIN`、`STOCKSDK_BRIDGE_ENTRY`、`STOCKSDK_TIMEOUT_MS`、`STOCKSDK_RATE_LIMIT_RPS`、`STOCKSDK_KLINE_FALLBACK`）同样属于 ④ 层统一配置。

### <a id="26-klinepy-瘦身为瘦端点d6"></a>2.6 kline.py 瘦身为瘦端点〔D6〕

删除内联 `_fetch_kline_from_*`，改为调用 `KlineDataSourceManager.get_kline(...)`；端点签名（`period` / `fqt` / `limit` / `before_date`）不变 → `/stock/kline` 前端零改动。

---

### <a id="27-设计前提项目未上线无历史包袱按正确做法落地"></a>2.7 设计前提：项目未上线，无历史包袱，按正确做法落地

> **核心前提**：HermesX **尚未上线**，不存在代码层与数据层的历史包袱（无存量线上数据需迁移、无已发布契约需兼容、无外部调用方依赖）。因此本 ADR 的所有设计取舍与改造动作，**以"正确的工程做法"为第一优先级**，而非"为兼容存量而妥协"。

由此导出贯穿全文的判定原则（后续 §3–§12 中若干原"临时顶替 / 挂账 / 不纳入"项据此上调或重判）：

- **不堆临时补丁**：能用正确结构（独立表 / 独立模块 / 统一入口）解决的不用 `config.py` 常量、`if/else` 兼容层、静默降级顶替；临时方案只在确有外部阻塞时存在，且必须带明确闭合条件。
- **技术债不挂账为永久状态**：既有"巨类 / 超大文件 / 直连取数"反模式（`BaseFetcher` 巨类、`sector.py` 1819 行），**未上线期是清理的最佳窗口**；可拆为独立 PR 控风险，但不视为"永久不纳入"。
- **统一入口从一开始就建对**：分层边界（数据库层 barrel、数据源矩阵、端点契约）在落地时即收口为唯一一致入口，不在"先能跑、后统一"假设下留分叉。
- **零新增表仍成立，但"正确结构"优先于"少建表"**：重构范围内不借机扩张无关表；但本属该层职责、此前因保守而"先用常量顶替"的结构（如数据字典），应建为正确形态，而非长期用 config 顶替。

## <a id="3-数据库层设计"></a>3. 数据库层设计

> 本章对应「① 数据库层」：本地数据源、本地配置、数据字典落表；外部 API 拉取只做进程内 TTL 缓存、不落表。整体决策见 §2.1 四层架构总览；本 ADR 重构范围内**不借机扩张无关表**，其中数据字典（O1）按 §2.7「正确做法」建为独立表，属本层既有职责、不视为妥协性扩张。

- **StockDB 由进程独占管理**：本地 StockDB 数据（`127.0.0.1:7899`）由 StockDB 自身进程独占，HermesX **不直读文件**，只走其 HTTP 接口（`data_provider/stockdb_fetcher.py` 封装）。
- **本地存储边界**：`src/infrastructure/persistence/repositories/`（+ 根 `storage.py`）承载 HermesX 自身本地数据源 / 配置 / 字典落表；外部 API 拉取只做进程内 TTL 缓存、不落表，避免重复落盘。
- **数据字典（应为独立表，不再用 config 顶替）**：承载跨能力字典，是 ① 数据库层本就属于的职责。因项目未上线（§2.7），**不应长期以 `config.py` 常量顶替**，应建为独立表 + 对应 Repository，作为正确结构落地；具体建模与落地排期见 §6 横切基础辅助层设计 / 开放项 O1（O1 由"可选"上调为"应建独立表"，执行排期见 §6 落地说明）。
- **对应目录**：`src/infrastructure/persistence/repositories/`（+ 根 `storage.py`）；本期数据库层**落表导出已收口（§3.1 / §10.5 D1）、数据字典 O1 按 §2.7 上调为应建独立表（执行见 §6 落地说明）**，除上述外不改动既有模型契约、不新增无关表。

### <a id="31-srcrepositories-落表文件清单与职责"></a>3.1 仓储落表文件清单与职责（现 `src/infrastructure/persistence/repositories/`）

数据库层（①）的本地落表由根 `storage.py`（连接/会话单例 + 全部 ORM 模型/数据字典）与 Repository（薄 DAO）共同承载。各 Repository **统一只依赖 `storage` 的导出 `DatabaseManager` + 对应 ORM 模型**，封装某几张表的 CRUD/查询，**不含业务编排**，由 bootstrap 装配后经端口注入 ③ 应用层用例。

> **迁移状态（2026-10-28，P3/P4 持久化收口 Epic PP-1~PP-7 已完成）**：intelligence / analysis / alert / portfolio / decision / backtest / quote 七个业务域的仓储已全部物理下沉到 `src/infrastructure/persistence/repositories/` 并由 application 端口收敛（`src/application/*/ports.py` 的 `*RepositoryPort` + 工厂 seam）；根 `src/repositories/` 在 git 中已无任何文件（克隆后不存在），守卫已把 `src.repositories` 列为 application 层禁入前缀。下表“文件”列均为当前实际落点。

| 文件 | 主表（ORM 模型） | 作用 | 业务域 |
|---|---|---|---|
| `src/infrastructure/persistence/repositories/stock_repository.py` | `StockDaily` | 日线本地缓存：`get_latest` / `get_range` / `save_dataframe` / `has_today_data`，以及回测用 `get_start_daily` / `get_daily_on_date` / `get_forward_bars`；后两者满足 `application/backtest/ports.py::StockRepositoryPort`（回测窗口解析、决策结果/技能观点评估共用） | 行情缓存 |
| `src/infrastructure/persistence/repositories/portfolio_repository.py` | `PortfolioAccount` / `PortfolioTrade` / `PortfolioCashLedger` / `PortfolioCorporateAction` / `PortfolioPosition` / `PortfolioPositionLot` / `PortfolioDailySnapshot` / `PortfolioFxRate` | 组合 P0 核心：账户 CRUD、交易/资金/公司行动事件写入（带 `BEGIN IMMEDIATE` 锁 + `trade_uid` / `dedup_hash` 去重）、持仓与批次缓存、日快照、汇率；`_invalidate_account_cache_in_session` 失效；3 个跨层异常上收 `application/portfolio/ports.py` | 组合 / 持仓 |
| `src/infrastructure/persistence/repositories/alert_repository.py` | `AlertRuleRecord` / `AlertTriggerRecord` / `AlertNotificationRecord` / `AlertCooldownRecord` | 告警中心：规则 CRUD/分页、触发历史（`create_trigger_if_absent` 去重）、通知记录、冷却 `upsert_cooldown` | 告警 |
| `src/infrastructure/persistence/repositories/analysis_repository.py` | `AnalysisHistory` | 分析历史：`get_by_query_id` / `get_list` / `save` / `count_by_code`，防御式吞异常返回空 | 分析历史 |
| `src/infrastructure/persistence/repositories/decision_signal_repository.py` | `DecisionSignalRecord` | AI 决策信号：`create_if_absent` 幂等合并（含 horizon/phase 松弛回填）、多维 `list`、`expire_due_signals` 过期；DTO `DecisionSignalCreateResult` 归 `application/decision/ports.py` | 决策信号 |
| `src/infrastructure/persistence/repositories/decision_signal_outcome_repository.py` | `DecisionSignalOutcomeRecord` / `DecisionSignalFeedbackRecord` | 信号的"前向结果 + 人工反馈"侧车表：`upsert_outcome` / `upsert_feedback`、`list_stats_rows`（用于 profile 校准）；DTO `OutcomeStatsRow` 归 ports | 信号结果 |
| `src/infrastructure/persistence/repositories/skill_opinion_sample_repository.py` | `SkillOpinionSampleRecord` | 技能意见不可变样本：`insert_missing`（`on_conflict_do_nothing` 按 history+skill+版本），只插不更新 | 技能样本 |
| `src/infrastructure/persistence/repositories/skill_opinion_outcome_repository.py` | `SkillOpinionOutcomeRecord` | 样本前向结果：`list_candidate_keys`（缺失/待评估候选）、`persist_outcome`（终态不覆盖）；DTO `SkillOpinionOutcomeCandidate` 归 ports | 样本结果 |
| `src/infrastructure/persistence/repositories/intelligence_repository.py` | `IntelligenceSource` / `IntelligenceItem` | 资讯情报：`IntelligenceItem` 借 `scope_type` / `scope_value` 区分通用资讯 / 实时快讯 / 消息日历；源 CRUD、items 只补空不覆盖、`list_live_news_items` keyset 游标、保留期清理 | 资讯情报 |
| `src/infrastructure/persistence/repositories/backtest_repository.py` | `BacktestResult` / `BacktestSummary`（关联 `AnalysisHistory`） | 回测：从 `AnalysisHistory` 选候选、`save_results_batch`、`get_results_*`、`upsert_summary`（胜率 / 方向准确率聚合）、`align_existing_result_dates`；纯函数 `parse_analysis_date_from_snapshot` 已下沉 `src/domain/analysis/analysis_context_snapshot.py`（同名静态方法仅作一行委托） | 回测 |

> **导出约定**：application 侧只依赖 `src/application/*/ports.py` 的端口与 ``get_*_repository()`` 工厂，bootstrap 负责注册 infra 实现；根 `src/repositories/` 与 `__init__` 已在 PP-7 删除，不再提供任何 barrel。

### <a id="32-storagepy-落表基座连接-模型-原语"></a>3.2 storage.py —— 落表基座（连接 + 模型 + 原语）

> **门面归位决策（2026-10-28，PP-7）**：ORM `Base` / 模型 / 会话 / schema 兼容 / 仓储实现均已下沉 `src/infrastructure/persistence/`，根 `src/storage.py` **保留为 `DatabaseManager` 门面**（单例装配 + `get_session()` + `write_transaction` + 同名薄委托）并作为**已批准例外**：application 已零依赖它（守卫禁止 `src.infrastructure`，不含 `src.storage` 前缀），搬门面需同时改全仓 import 且无分层收益，故本轮不动；若后续要让 application 也禁止 `src.storage`，应在独立切片中整体搬迁。

- **`DatabaseManager`（进程内单例，metaclass 控制）**：管理 SQLite 连接、`get_session()` 会话、`_run_write_transaction()` 写事务、`BEGIN IMMEDIATE` 锁重试；是所有 Repository 的唯一连接/会话来源，是依赖终点，不依赖任何上层。
- **34 个 ORM 模型（即"数据字典 / 落表 schema"）**：`StockDaily`、`IntelligenceSource` / `IntelligenceItem`、`NewsIntel`、`FundamentalSnapshot`、`AnalysisHistory`、`BacktestResult` / `BacktestSummary`、`Portfolio*`(9 张)、`ConversationMessage` / `ConversationSummary` / `AgentProviderTurn`、`LLMUsage`、`Alert*`(4 张)、`DecisionSignal*`(3 张)、`SkillOpinion*`(2 张)、`WatchlistGroup` / `WatchlistItem`、`DatabaseSchemaMigration`。
  - 其中多数模型已有对应 Repository（见 §3.1）；`NewsIntel` / `FundamentalSnapshot` / `Conversation*` / `LLMUsage` / `Watchlist*` / `DatabaseSchemaMigration` 目前直接经 `DatabaseManager` 原语或别的入口访问，未设专属 Repository（非必需；属稳定期外可选项，可按需补，不计入本 ADR 新增范围）。
- **存储铁律（文件 docstring 强制）**：时间统一 UTC-naive、金额统一元 / 涨跌幅为百分比数值、股票代码纯代码字符串、JSON 列以 `Text` 存字符串、流水表软删除 + 保留期清理；Schema 增量迁移经 `_ensure_*` 幂等补列/补索引。
- **边界**：只做"连接管理 + ORM 模型 + 通用存取原语"，**不含业务编排**；业务在 `src/application/` 与 `src/domain/`。

### <a id="33-数据库层在四层架构中的定位"></a>3.3 数据库层在四层架构中的定位

- **① 数据库层 = 本地落表基座**：承载 HermesX **自身**的本地数据源 / 配置 / 字典落表。本层不依赖 ② 数据源对接层、③ 功能接口层、④ 横切层；是其余所有层的公共依赖终点。
- **与 ② 数据源对接层的边界**：脏活（抓取、字段标准化、fallback、TTL、与 StockDB/外部源对接）全部在 `data_provider/`，经 HTTP 封装；本层 Repository 不写 `requests`、不直读 StockDB 文件。`intelligence_repo.py` 的 docstring 已明示"不负责抓取/标准化/编排（在 `services/intelligence_service` 与 `data_provider`）"——即本 ADR §2 边界的落地。
- **`StockDaily` 是本地日线缓存，不是 StockDB 原生表**：ADR §2 约定"外部 API 只 TTL 缓存不落表"，而 `StockRepository.save_dataframe` 把日线写进 HermesX 自己的 SQLite——这是该原则的"本地缓存例外"。真正的 StockDB 日k/分钟k 原生表由 StockDB 进程独占，HermesX 只经 `data_provider/stockdb_fetcher.py` 走 HTTP，不出现在本层任何 Repository 中。
- **Repository 之间不互相耦合**：各 Repository 只依赖 `storage`，彼此不 import（如 `backtest_repo` 通过 `AnalysisHistory` 外键关联，而非 import `analysis_repo`），保证领域规则不泄漏到模型层、可被多入口复用。
- **调用方**：Repository 的上层是 ③ 功能接口层（`api/v1/endpoints/` 端点 + `src/services/` 编排），Repository 不感知路由/请求/响应。

---

## <a id="4-数据源对接层设计"></a>4. 数据源对接层设计

> 本章对应「② 数据源对接层（脏活层）」：唯一与外部 / 本地源对接的封装层，是 `data_provider/` 的落地设计详述。整体决策见 §2.2、§2.3；本节目录铺排总表以本 ADR §4.4 为唯一对齐基准（方案 §3.8.8 已改为引用本表，不再重复全量内联）。

### <a id="41-dataprovider-目录结构与功能包划分"></a>4.1 data_provider 目录结构与功能包划分

K 线（kline）/ 基础信息（stock_info）/ 代码搜索（code_search）各自独立成包，置于 `data_provider/` 下，结构同构；另设 `common/` 承载跨功能公共底座：

```
data_provider/
├── common/        base.py(DataSource(ABC) + DataSourceManager 通用骨架)
│                  + normalize.py + cache.py + rate_limit.py + health.py
├── stocksdk_bridge.py（Python bridge → Node 18 sidecar → stock-sdk）
├── kline/         base.py(KlineDataSource + KlineDataSourceManager)
│                  + local_stockdb_source.py + eastmoney_source.py
│                  + sina_source.py + tencent_source.py + stocksdk_source.py
│                  + transform.py（多周期时间桶聚合）
├── stock_info/    base.py + local_stockdb_source.py + eastmoney_source.py + stocksdk_source.py
└── code_search/   base.py + local_stockdb_source.py + eastmoney_source.py + stocksdk_source.py
```

> 各能力子包、源适配器、端点、契约的**具体目录结构与命名公约（PEP 8 + HermesX 既有 `*_service.py` / `*_repo.py` / `*_fetcher.py` / `base.py` 规律）以方案 `stock_data_view.md` §3.5 为代码落地模板**，本 ADR 不再重复，避免两处漂移。

> **二维组织原则（功能 × 数据源）**：`data_provider/` 下的能力包按"功能/用途"先分维度，再按"数据源"分维度，目录形态为 `data_provider/<功能>/<源>_source.py`；跨功能的公共逻辑（代码归一/缓存/限流/健康探针）统一沉到 `data_provider/common/`。对 **Node/TS 生态的 StockSDK**，额外引入共享桥接文件 `data_provider/stocksdk_bridge.py` 作为物理后端入口，但其上层仍必须落回各能力包下的 `stocksdk_source.py`。完整能力清单、目标目录树（含层级合并单元格表）、防重复决策与分阶段落地见 §4.4 目录铺排总表。

### <a id="42-basepy-三层关系common-底座-vs-功能包-base"></a>4.2 base.py 三层关系（common 底座 vs 功能包 base）

- **`common/base.py`** = 公共泛型底座，定义最通用的 `DataSource(ABC)` + `DataSourceManager`（选源 / 回退 / 健康 / TTL 由配置驱动）。它**不对应任何具体业务接口**，只提供被继承的"骨架"。
- **各功能包 `base.py`**（如 `code_search/base.py`、`stock_info/base.py`、`kline/base.py`）= 该能力的专属契约与编排层（`CodeSearchDataSource` / `StockInfoDataSource` / `KlineDataSource`），均**继承 `common/base.py`**。每个能力包有自己独立的契约（`CodeSearchResult` / `StockInfo` / `KLinePoint`）与适配器注册，**互不污染**。
- 关系：`common/base.py` 被各功能包 `base.py` **继承**——选源 / 回退逻辑统一在公共层写一遍，功能契约各自独立。

### <a id="43-两类高频查询接口的归类"></a>4.3 两类高频查询接口的归类

- 🔍 **查询接口①（输入 6 位编码 / 名称 → 联想解析出这只股票）** → 落在 **`data_provider/code_search/base.py`**（`CodeSearchDataSource` + `CodeSearchDataSourceManager` + `CodeSearchResult` 契约）。**不在 `common/base.py`。**
- 🔍 **查询接口②（输入 6 位编码查股票信息：名称 / 行业 / 板块 / 列表）** → 落在 **`data_provider/stock_info/base.py`**（`StockInfoDataSource` + `StockInfoDataSourceManager` + `StockInfo` 契约）。**不在 `common/base.py`。**
- 两者**不合并为一个包**（契约 `CodeSearchResult` ≠ `StockInfo`）；底层"股票总表 / 名称↔编码"抓取共享，统一复用既有 `get_stock_name` / `get_stock_list`（即"物理后端"），不在各源重写。
- 当前违规待迁移：`src/services/name_to_code_resolver.py` 在 ③ 功能接口层直接 `import akshare` 取数（违反 §2.2），其取数须下沉到 `code_search/eastmoney_source.py` / `code_search/stocksdk_source.py`；`stock_service.get_stock_name` 从 `BaseFetcher` 巨类迁至 `stock_info/eastmoney_source.py` / `stock_info/stocksdk_source.py`（方案 §3.7 A10 / A12）。

### <a id="44-dataprovider-目录铺排总表落地基准"></a>4.4 data_provider 目录铺排总表（落地基准）

> **`data_provider` 目录铺排总表（代码拆分与最终落地的权威依据）**
>
> 本表是后续代码拆分、新建、挪动的**唯一对齐基准**。改造完成后，`data_provider/` 的实际目录与文件须与本表**逐行一一匹配**（路径、名称、职责一致）。表中"落地阶段"标注该项属于哪一期：阶段1=本期、阶段2=实时行情迁入、阶段3=其余功能包迁入（独立 follow-up）。
>
> **划分总则**：第一维按**功能/用途**分目录（`common`/`kline`/`realtime`/`stock_info`/`code_search`/`sector`/`limit_pool`/`fundamentals`/`news`/`institutional`）；第二维在功能包内按**数据源**拆文件（`<源>_source.py`）；跨功能公共逻辑全部进 `common/`，绝不在各源重复。🔍 标注的两类查询接口详见本 ADR 4.3「两类高频查询接口的归类」（= 方案 §3.8.9）。

| 一级目录（根） | 二级目录（功能包） | 三级（文件） | 作用（干什么） | 对应业务接口（用户视角） | 划分依据 | 落地阶段 |
|---|---|---|---|---|---|---|
| `data_provider/` | `common/` | `__init__.py` | 包标识（空文件，使 `data_provider.common` 可 import） | （公共底座，无独立业务接口，被所有功能包依赖） | 目录标识 | 阶段1 |
| | | `base.py` | 通用 `DataSource(ABC)` + `DataSourceManager`（配置选源/回退/健康/TTL）；各功能包 Manager 继承它 | 同上 | 公共抽象（横切，非功能包） | 阶段1 |
| | | `normalize.py` | 股票代码归一（`canonical_stock_code` 等），复用现有实现 | 同上 | 公共工具 | 阶段1 |
| | | `cache.py` | 统一 TTL 缓存 | 同上 | 公共基础设施 | 阶段1 |
| | | `rate_limit.py` | 限流 / 并发护栏 | 同上 | 公共基础设施 | 阶段1 |
| | | `health.py` | 数据源可用性探针 | 同上 | 公共基础设施 | 阶段1 |
| | `（根文件）` | `stocksdk_bridge.py` | Python 侧共享 StockSDK bridge 客户端：负责 Node 18 进程/sidecar 调起、JSON 序列化、错误映射、超时与健康探针；供多个 `stocksdk_source.py` 复用 | K 线 / 搜索 / 基础信息 / 实时 / 板块的桥接型物理后端 | 跨功能共享物理后端桥 | 阶段1 |
| | `kline/` | `__init__.py` | 包标识 | **K 线图 / 历史多周期行情** | 目录标识 | 阶段1 |
| | | `base.py` | `KlineDataSource(ABC)` + `KlineDataSourceManager`；统一 `KLinePoint` 契约；`pct_chg` 层内计算 | K 线图 / 历史多周期行情 | 第一维=功能 K线（功能包核心） | 阶段1 |
| | | `local_stockdb_source.py` | 源 = 本地 StockDB（127.0.0.1:7899），对接本地库、输出 `KLinePoint`【新写】 | 同上 | 第二维=源 local | 阶段1 |
| | | `eastmoney_source.py` | 源 = 东财，仅做「东财格式 → `KLinePoint`」映射，**复用既有东财通道（efinance/akshare），不重写** | 同上 | 第二维=源 eastmoney | 阶段1 |
| | | `sina_source.py` | 源 = 新浪，格式映射，复用既有新浪通道 | 同上 | 第二维=源 sina | 阶段1 |
| | | `tencent_source.py` | 源 = 腾讯，格式映射，复用 `tencent_fetcher` | 同上 | 第二维=源 tencent | 阶段1 |
| | | `stocksdk_source.py` | 源 = StockSDK，经 `stocksdk_bridge.py` 调用 Node 18 `stock-sdk` 命名空间 API；适合作为桥接型聚合源与备用源 | 同上 | 第二维=源 stocksdk | 阶段1 |
| | | `transform.py` | 多周期时间桶聚合（5m~年）+ `pct_chg` 聚合计算 | 同上 | 功能包内共享能力 | 阶段1 |
| | `realtime/` | `__init__.py` | 包标识 | **实时行情刷新（自选股 / 大盘 / 组合）** | 目录标识 | 阶段2 |
| | | `base.py` | `RealtimeDataSource(ABC)` + `RealtimeDataSourceManager`；复用现有 `RealtimeSource` 枚举与 `UnifiedRealtimeQuote` | 实时行情刷新 | 第一维=功能 实时行情（功能包核心） | 阶段2 |
| | | `akshare_source.py` | 源 = akshare，格式映射（复用既有 akshare 实时通道） | 同上 | 第二维=源 akshare | 阶段2 |
| | | `tickflow_source.py` | 源 = tickflow，格式映射（复用既有 tickflow 实时通道） | 同上 | 第二维=源 tickflow | 阶段2 |
| | | `stocksdk_source.py` | 源 = StockSDK，桥接 `sdk.quotes.*`；用于补充 A/HK/US/Fund 多市场实时行情与统一符号解析 | 同上 | 第二维=源 stocksdk | 阶段2 |
| | `stock_info/` | `__init__.py` | 包标识 | **🔍 查询接口②：输入 6 位编码查股票信息（名称 / 行业 / 板块 / 列表）** | 目录标识 | 阶段1 |
| | | `base.py` | `StockInfoDataSource(DataSource)` + `StockInfoDataSourceManager(DataSourceManager)`（**继承 `common/base.py`**）；`StockInfo` 契约 = **查询接口②落点** | 输入 6 位编码查股票信息 | 第一维=功能 基础信息（功能包核心） | 阶段1 |
| | | `local_stockdb_source.py` | 源 = 本地 StockDB，复用 StockDB 基础信息 | 同上 | 第二维=源 local | 阶段1 |
| | | `eastmoney_source.py` | 源 = 东财，**复用既有 `get_stock_name`/`get_stock_list` + 薄适配壳**；**承接 §3.7 A10：`stock_service.get_stock_name` 从 `BaseFetcher` 巨类迁此** | 同上 | 第二维=源 eastmoney | 阶段1 |
| | | `stocksdk_source.py` | 源 = StockSDK，桥接 `search / code-lists / symbol normalize` 后输出统一 `StockInfo` 契约 | 同上 | 第二维=源 stocksdk | 阶段1 |
| | `code_search/` | `__init__.py` | 包标识 | **🔍 查询接口①：输入 6 位编码 / 名称 → 联想解析出这只股票** | 目录标识 | 阶段1 |
| | | `base.py` | `CodeSearchDataSource(DataSource)` + `CodeSearchDataSourceManager(DataSourceManager)`（**继承 `common/base.py`**）；`CodeSearchResult` 契约 = **查询接口①落点** | 输入 6 位编码 / 名称 → 联想解析出这只股票 | 第一维=功能 代码搜索（功能包核心） | 阶段1 |
| | | `local_stockdb_source.py` | 源 = 本地 StockDB | 同上 | 第二维=源 local | 阶段1 |
| | | `eastmoney_source.py` | 源 = 东财，复用既有搜索接口 + 薄适配壳；**承接 §3.7 A10：`name_to_code_resolver.py` 取数下沉此（③ 功能接口层不再直接 `import akshare` 取数，解析/缓存留薄壳）** | 同上 | 第二维=源 eastmoney | 阶段1 |
| | | `stocksdk_source.py` | 源 = StockSDK，桥接 `sdk.search()` 与符号归一能力，输出 `CodeSearchResult` 契约 | 同上 | 第二维=源 stocksdk | 阶段1 |
| | `sector/` | `__init__.py` | 包标识 | **板块 / 概念 / 热门榜单** | 目录标识 | 阶段3 |
| | | `base.py` | `SectorDataSource(ABC)` + `SectorDataSourceManager`；板块/概念/热门榜单契约 | 板块行情 | 第一维=功能 板块行情（功能包核心） | 阶段3 |
| | | `eastmoney_source.py` | 源 = 东财，承接市场指数 / 市场概览 / 北向资金 / 大盘主力 / 板块列表 / 板块资金流历史等东财接口主链路；**完成 B1 中东财内联取数下沉** | 同上 | 第二维=源 eastmoney | 阶段3 |
| | | `shidaotec_source.py` | 源 = 时到量化，承接行业 / 个股 / ETF / 概念云图的直连取数、缓存与整形 | 同上 | 第二维=源 shidaotec | 阶段3 |
| | | `stocksdk_source.py` | 源 = StockSDK，桥接行业 / 概念板块 / 资金流 / 北向资金等标准板块接口；主要作为 eastmoney 的桥接型补充源，不承接时到量化云图专属接口 | 同上 | 第二维=源 stocksdk | 阶段3 |
| | | `market_cards_source.py` | 功能包内共享能力：统一组装 `/api/v1/sector/market-cards?market=<tab-key>` 卡片列表（B1 已落地，此前漏登记本表，本次补登记） | 同上 | 功能包内共享能力（非数据源维度） | 阶段3 |
| | `limit_pool/` | `__init__.py` | 包标识 | **涨跌停榜单（涨停池 / 跌停池；后续扩炸板池 / 昨日涨停池 / 连板梯队）** | 目录标识 | 阶段3 |
| | | `base.py` | `LimitPoolDataSource(ABC)` + `LimitPoolDataSourceManager`；统一 `LimitPoolEntry` 契约（`code / name / price / change_pct / amount / turnover_rate / seal_amount / first_limit_time / last_limit_time / break_count / limit_stat / consecutive_boards / industry`），以 `pool_type`（`limit_up` / `limit_down`）区分涨跌停；选源 / 回退 / TTL / 健康冷却复用 `common/base.py`（配置键 `limit_pool_data_source` / `limit_pool_source_priority` / `limit_pool_fallback_enabled`，随 B2 落进 `src/config/settings.py` 与运行时白名单） | 涨跌停榜单 | 第一维=功能 涨跌停（功能包核心） | 阶段3 |
| | | `eastmoney_source.py` | 源 = 东财，承接涨停股池 / 跌停股池取数；**复用既有 akshare 东财通道（`stock_zt_pool_em` / `stock_zt_pool_dtgc_em`），不重写**；**承接 B2：涨跌停池从 `BaseFetcher` 巨类下沉** | 同上 | 第二维=源 eastmoney | 阶段3 |
| | | `stocksdk_source.py` | 源 = StockSDK，经 `stocksdk_bridge.py` 桥接涨跌停 / 封板类接口，作为 eastmoney 的桥接型补充源；**用于补齐涨跌停第二源，使回退链真正成立** | 同上 | 第二维=源 stocksdk | 阶段3 |
| | `fundamentals/` | `__init__.py` | 包标识 | **财务基本面（财报 / 估值）** | 目录标识 | 阶段3 |
| | | `base.py` | `FundamentalsDataSource(ABC)` + `FundamentalsDataSourceManager` | 财务数据 | 第一维=功能 基本面（功能包核心） | 阶段3 |
| | | `tushare_source.py` | 源 = tushare，复用 `tushare_fetcher` 财务通道 | 同上 | 第二维=源 tushare | 阶段3 |
| | `news/` | `__init__.py` | 包标识 | **新闻 / 公告 / 财经日历** | 目录标识 | 阶段3 |
| | | `base.py` | `NewsDataSource(ABC)` + `NewsDataSourceManager` | 资讯数据 | 第一维=功能 资讯（功能包核心） | 阶段3 |
| | | `wallstreetcn_source.py` | 源 = 华尔街见闻，复用既有 `wallstreetcn_*` | 同上 | 第二维=源 wallstreetcn | 阶段3 |
| | `institutional/` | `__init__.py` | 包标识 | **机构持仓数据（台股）** | 目录标识 | 阶段3 |
| | | `base.py` | `InstitutionalDataSource(ABC)` + `InstitutionalDataSourceManager` | 机构数据 | 第一维=功能 机构数据（功能包核心） | 阶段3 |
| | | `tw_source.py` | 源 = 台湾机构，复用 `tw_institutional_fetcher` | 同上 | 第二维=源 tw | 阶段3 |

> **既有文件处置（不删不改、降级为"物理后端"）**：现有 `data_provider/akshare_fetcher.py`、`tushare_fetcher.py`、`efinance_fetcher.py`、`tencent_fetcher.py`、`tickflow_fetcher.py`、`yfinance_fetcher.py`、`longbridge_fetcher.py`、`pytdx_fetcher.py`、`baostock_fetcher.py`、`alphavantage_fetcher.py`、`finnhub_fetcher.py` 等**保留**，作为上表中对应 `<源>_source.py` 的底层物理取数后端被复用（例如 `kline/eastmoney_source.py` 内部调用既有东财通道）；`StockSDK` 则以 `data_provider/stocksdk_bridge.py` + Node 18 sidecar 的形式作为另一类"桥接型物理后端"纳入。本期不重写、不删除。待各功能包矩阵（阶段 2/3）成熟、`BaseFetcher` 巨类完成"物理后端 → 矩阵拆解"后，这些顶层 fetcher 再逐步退役。

### <a id="45-数据源介绍本项目对接的数据源头清单"></a>4.5 数据源介绍（本项目对接的数据源头清单）

> 本节以清单形式**完整**介绍本项目在 **② 数据源对接层** 实际对接（含已用、规划内）的数据源头，便于理解"各源是什么、怎么接、与本项目是接口调用还是代码耦合、要不要 key/token"。
>
> **两个范围必须分清**：
> 1. **"多源平等 + 自动回退 + 周期全集"是优先作用于 `K 线 / 基础信息 / 代码搜索` 三类基础能力的设计原则**（见 §2.4 / §2.3）。这三类能力当前规划源集合为 `local(StockDB) / eastmoney / sina / tencent / stocksdk` 五源，五者在 HermesX 的能力层内完全同级、主次由配置决定；其中 `stocksdk` 是桥接型聚合源，而非 Python 侧直连库。
> 2. **其他能力（实时行情 / 板块 / 财务基本面 / 新闻资讯 / 机构持仓）各有其既定专属源**（akshare / tickflow / eastmoney + shidaotec / tushare / wallstreetcn / tw_institutional 等）；若后续引入 `stocksdk_source.py`，也仅作为桥接型补充源纳入 ② 层，不改变 ③ 层契约（见 §4.4 铺排总表）。
>
> 下表按"是否在本 ADR 规划内"分两组：**规划内数据源（11 个，已用或阶段 2/3 规划）**逐行讲清；**未来可选数据源（6 个，连 §4.4 都未纳入）** 仅列于表末脚注。

| 数据源 | 数据源的作用（本项目用它提供什么能力） | 接入方式 | 与本项目的关系（接口调用 / 代码耦合） | 是否需要 key / token 等凭据 |
|---|---|---|---|---|
| **StockDB（local 本地源）** | 本地行情库（独立进程 `127.0.0.1:7899`），提供 K 线（日k / 分钟k 原生，其余周期由 `transform.py` 聚合补齐）、基础信息、代码搜索三能力的 `local` 源 | HTTP（REST，本地回环），由 `data_provider/stockdb_fetcher.py` 封装（阶段 1 新建） | **接口调用**：独立进程；HermesX 不 import 其代码、不直读文件，进程独占管理（见 §3 数据库层设计） | **否**（本地服务；可选 `STOCKDB_REQUIRE_AUTH` 默认关闭，复用 `/api/v1` 的 `ADMIN_AUTH` 即可，O2 可降级为可选项） |
| **StockSDK** | **桥接型聚合源**：覆盖 K 线、实时行情、代码搜索、基础信息、板块与资金面等多个命名空间；在 HermesX 中优先作为 `kline / stock_info / code_search` 的新增源，并可扩展到 `realtime / sector` | Node.js 18+ 中安装 `stock-sdk`，由 `data_provider/stocksdk_bridge.py` 通过 sidecar / subprocess 调用 `StockSDK` 命名空间 API（`quotes` / `kline` / `search` / `board` / `fundFlow` / `northbound` 等） | **跨运行时代码耦合**：Python 不直接 import JS，而是通过桥接层做 JSON 协议调用；治理能力（超时 / 重试 / 限流 / 熔断 / host fallback / kline fallback）收口在 StockSDK 自身的 `RequestClient` | **否**（官方文档显示零运行时依赖、默认无需 key/token；但要求 **Node.js 18+**，且需要仓库内维护桥接脚本与运行时） |
| **东方财富（EastMoney）** | **三类基础能力的主行情源之一**：K 线、基础信息、代码搜索（kline.py 用其 5 个公开接口）；亦为板块行情（sector）中的指数 / 概览 / 资金流 / 排行等能力源；数据最全。属于"多源平等"源之一 | HTTP 直连其公开行情接口（`push2his.eastmoney.com` / `push2.eastmoney.com` / `searchapi.eastmoney.com` 等）+ 经 `akshare` / `efinance` **Python 库**（库内封装反爬） | **代码耦合为主**：当前经 `akshare_fetcher` / `efinance_fetcher` 库依赖（库内发起 HTTP）；本质仍是对方公开 HTTP 接口 | **否**（免费公开，无需 Token；依赖随机 UA / 休眠 / 重试 / 熔断器防封禁） |
| **时到量化（Shidaotec）** | 板块行情（sector）中的行业 / 个股 / ETF / 概念云图能力源，用于树图 / 热力图视图的结构与涨跌幅快照 | HTTP 直连其公开云图接口（`www.shidaotec.com/api/yuntu/*`），由 `data_provider/sector/shidaotec_source.py` 封装 | **接口调用为主**：HermesX 直接发起 HTTP 请求并在 provider 层完成缓存与整形 | **否**（免费公开，无需 Token） |
| **腾讯（Tencent）** | **三类基础能力兜底源之一**（K 线 / 日线，`tencent_fetcher` 末位兜底）；亦经 akshare 取数。属于"多源平等"源之一 | HTTP 直连 `web.ifzq.gtimg.cn/appstock/app/fqkline/get`（`tencent_fetcher` 直连）+ 经 `akshare` | **两种并存**：直连 HTTP（接口调用）+ 经 `akshare`（代码耦合） | **否**（免费公开，无需 Token） |
| **新浪（Sina）** | **三类基础能力兜底源之一**（K 线，kline.py 2 个接口、新老互为降级）；亦经 akshare 取数。属于"多源平等"源之一 | HTTP 直连 `quotes.sina.cn` / `money.finance.sina.com.cn`（kline.py 直连）+ 经 `akshare` | **两种并存**：直连 HTTP（接口调用）+ 经 `akshare`（代码耦合） | **否**（免费公开，无需 Token；但需 `Referer` 头，否则 403） |
| **akshare（通用库 / 实时源）** | **双重角色**：① 实时行情源（`realtime/akshare_source.py`，阶段 2）；② 同时是东财 / 新浪 / 腾讯经其 SDK 取数的"库通道"（kline 三源均"经 akshare"取数）。数据全面，覆盖行情 / 基本面 / 资讯多类 | HTTP 直连其公开接口（`akshare` 库内封装反爬、随机 UA、熔断）+ 经 `akshare` **Python 库**代码耦合 | **代码耦合为主**（经 akshare SDK；库内发起 HTTP） | **否**（免费、无需 Token，`akshare_fetcher.py:12` 注明"免费、无需 Token"） |
| **tickflow（实时源）** | 实时行情源（`realtime/tickflow_source.py`，阶段 2）；提供实时 / 批量日线，作为实时行情能力的补充源 | HTTP 直连其公开行情接口（`tickflow_fetcher.py` 封装，需 API key 鉴权） | **代码耦合**（经 tickflow SDK / HTTP 客户端，需鉴权） | **是，需 `TICKFLOW_API_KEY`**（未配置则不可用，`config.py:772` / `tickflow_fetcher.py:183`） |
| **tushare（财务基本面源）** | 财务基本面源（`fundamentals/tushare_source.py`，阶段 3）；提供财报 / 估值等财务数据 | HTTP 直连 `api.tushare.pro`（`tushare_fetcher.py` 封装，需 token 鉴权） | **代码耦合**（经 tushare SDK，需 token） | **是，需 `TUSHARE_TOKEN`**（有配额限制；未配置则数据源不可用，`tushare_fetcher.py:8,185`） |
| **wallstreetcn 华尔街见闻（新闻资讯源）** | 新闻 / 公告 / 财经日历源（`news/wallstreetcn_source.py`，阶段 3）；提供快讯 / 资讯 / 日历 | HTTP 直连其公开资讯接口（`wallstreetcn_calendar_fetcher.py` / `wallstreetcn_live_news_fetcher.py` 封装） | **代码耦合**（经 HTTP 客户端 / SDK） | **否**（公开接口，未检索到鉴权依赖） |
| **tw_institutional 台湾机构（机构持仓源）** | 机构持仓数据（台股）源（`institutional/tw_source.py`，阶段 3）；提供 TWSE / TPEx 机构买卖数据 | HTTP 直连台湾政府开放资料接口（`tw_institutional_fetcher.py` 封装） | **代码耦合**（经 HTTP 客户端；政府开放资料） | **否**（政府开放资料，commercial-safe，no key，`tw_institutional_fetcher.py:10`） |

> **关系栏要点**：StockDB 是最干净的"纯接口调用"（独立进程、零代码耦合）；StockSDK 是新增的"跨运行时桥接型物理后端"；东财当前以 SDK 代码耦合为主；腾讯 / 新浪为"直连 HTTP + SDK"并存。无论哪种，对上层（③ 功能接口层 / 前端）均通过统一契约（`KLinePoint` / `StockInfo` / `CodeSearchResult` / `UnifiedRealtimeQuote`）透明供给——换源 / 升级源都不影响上层（见 §5.1 铁律）。
>
> **未来可选数据源（连 §4.4 铺排总表都未纳入，仅记录、不纳入本期任何阶段）**：`yfinance` / `longbridge`（需 `LONGBRIDGE_ACCESS_TOKEN`）/ `pytdx` / `baostock` / `alphavantage` / `finnhub`。这些物理后端存在于代码库（`*_fetcher.py`）但不在本 ADR 任何阶段规划内，可后续按同一 `<源>_source.py` 模式扩展（加源只写一份 `_normalize_*` 映射，见 §2.2 / §4.2）。

---

## <a id="5-功能接口层设计"></a>5. 功能接口层设计

> 本章对应「③ 功能接口层」：面向功能 / UI 的 HTTP 端点（固定契约，不随数据源变）+ 功能编排（组合数据源与业务规则）。**本章为该层设计的权威依据**——边界、目录结构、铺排总表、调用链路均在此；主方案 `stock_data_view.md` §3.9 与之对齐、不重复展开。整体决策见 §2.6（kline.py 瘦身为瘦端点）；取数下沉规则见 §4.3。

### <a id="51-定位与边界区别于-②-数据源对接层"></a>5.1 定位与边界（区别于 ② 数据源对接层）

- **功能接口层 = 面向系统标准功能的 HTTP 接口层**。其**输入 / 输出契约是稳定的、标准的**，只随“系统功能”演进，**不随底层数据源变动**而改。
- **典型样例（K 线图）**：K 线图的渲染方式、前端取数接口（`code / period / fqt / limit` → `KLinePoint[]`）是标准的；只有“数据从哪个源来（本地 StockDB / 东财 / 新浪 / 腾讯 / StockSDK）”是个性，且已下沉到 ② 层（`data_provider/kline/` 多源可切换）。换成任意源，K 线端点签名与返回结构**完全不变** → 前端零改。
- **边界铁律**：③ 层**只做路由 + 编排**，不内联任何第三方 / 本地源对接代码（取数一律经 ② 层 `data_provider/*/base.py` 的 Manager）。详见 §2.6（A1 瘦端点、A10 取数下沉）、§4.3（两类查询接口必须归入 ② 层）。
- **与 ② 层的唯一耦合点**：③ 层调用 ② 层的统一契约（`KLinePoint` / `StockInfo` / `CodeSearchResult` 及后续能力契约），源切换对 ③ 透明。

### <a id="52-端点目录结构与两层划分"></a>5.2 端点目录结构与两层划分

```
api/v1/
├── endpoints/          # ③ 功能接口层：HTTP 端点（路由 + 编排，不取数）
│   ├── kline.py  watchlist.py  portfolio.py  backtest.py  alerts.py
│   ├── analysis.py  sector.py  stocks.py  history.py  decision_signals.py
│   ├── alphasift.py  agent.py  intelligence.py
│   ├── auth.py  health.py  system_config.py  usage.py
│   ├── eod_picker.py  scanner.py  limit_pool.py   # 编制后新增，逐项职责见 §5.3
│   └── (规划) stock-info.py  code-search.py   # §4.3 两类查询接口将来上提的端点
└── schemas/           # 请求 / 响应 Pydantic 模型（契约定义，与端点同层固定）
src/services/          # ③ 功能编排层：组合数据源与业务规则（调用 ② 层取数 + 本地 DB）
```

> 两层关系：端点（`endpoints/`）只路由 + 调 `services/*` 编排；`services/` 组合 ② 层取数与本地存储，承载业务规则。两者同属 ③ 功能接口层，均**不直连第三方源**。

### <a id="53-功能接口层铺排总表枚举所有标准功能接口-权威基准"></a>5.3 功能接口层铺排总表（枚举所有标准功能接口 · 权威基准）

> 下表逐文件枚举 `api/v1/endpoints/` 下全部 20 个端点文件。每个文件 = 一个标准功能域；其契约固定、不随数据源变，底层取数由 ② 层透明供给。🌟 = K 线图（边界铁律典型样例）。**本表为权威基准，主方案 §3.9 与之对齐、不重复列全表。**
>
> **登记与命名公约（新增 / 重命名端点必读）**：
>
> 1. **登记**：新增或重命名端点须同步登记本表，避免权威基准与实际目录漂移。
> 2. **按服务端能力域命名，不完全绑定前端菜单**：端点文件名与路由前缀**建议按照服务端能力域**命名（如涨跌停池 → `limit_pool.py` / `/limit-pool`），**不得完全绑定前端菜单分组**（因为菜单会重组、页面会迁移，能力域不会；前端页面只是消费方）。（实例：`emotion.py` / `/emotion` 原按「情绪」菜单命名，已按本公约改名为 `limit_pool.py` / `/limit-pool`。）
> 3. **规划端点**：§5.2 中规划的 `stock-info.py` / `code-search.py`（对应 §4.3 两类查询接口）待 ② 层能力包成熟后上提，届时按上述公约命名并登记本表。
>
> 本表末三行 `limit_pool.py` / `eod_picker.py` / `scanner.py` 为本表编制后新增的端点，追加于表末。

| 目录地址 | 文件夹 | 文件名 | 做什么（标准功能职责） | 作用（面向谁） | 划分依据 | 随数据源变动 |
|---|---|---|---|---|---|---|
| `api/v1/` | `endpoints/` | `kline.py` 🌟 | K 线行情获取 `/{code}/kline`、股票搜索 `/search`、股票信息 `/{code}/info` | 前端 K 线图 / 行情面板（标准渲染接口） | ③ 标准功能接口：契约固定（code/period/fqt → KLinePoint[]） | **否**（底层源切换由 data_provider 透明处理） |
| `api/v1/` | `endpoints/` | `watchlist.py` | 自选股分组与项 CRUD、移动归类（`/watchlist`） | 用户自选股管理 | ③ 用户数据 CRUD，与数据源无关 | 否 |
| `api/v1/` | `endpoints/` | `portfolio.py` | 投资组合、持仓、调仓的 CRUD 与风险计算入口（`/portfolio`） | 组合管理与风险视图 | ③ 用户资产数据 CRUD + 编排 | 否 |
| `api/v1/` | `endpoints/` | `backtest.py` | 回测任务创建 / 查询 / 结果（`/backtest`） | 策略回测 | ③ 输入=策略+标的+区间，输出=回测报告（标准） | 否 |
| `api/v1/` | `endpoints/` | `alerts.py` | 预警规则 CRUD + 触发推送（`/alerts`） | 价格 / 条件预警 | ③ 规则 CRUD，与源无关 | 否 |
| `api/v1/` | `endpoints/` | `analysis.py` | 股票分析异步任务触发 / 状态 / 列表 + SSE 推送（`/analysis`） | 个股 / 市场分析 | ③ 分析编排标准，取数透明 | 否 |
| `api/v1/` | `endpoints/` | `sector.py` | 行业树 / 指数 / 市场概览 / 资金流 / 北向 / 板块成分 / 概念 / ETF（`/sector`） | 板块与市场概览 | ③ 输出标准；当前按子场景分源：eastmoney + shidaotec（个性下沉 ②） | 否 |
| `api/v1/` | `endpoints/` | `stocks.py` | 图片提取代码 / CSV 解析 / 实时行情 / 历史行情（`/stocks`） | 股票基础数据与导入 | ③ 接口标准，取数透明 | 否 |
| `api/v1/` | `endpoints/` | `history.py` | 分析 / 对话 / 资讯历史查询与删除（`/history`） | 历史记录管理（系统产出物 CRUD） | ③ 系统产出物 CRUD | 否 |
| `api/v1/` | `endpoints/` | `decision_signals.py` | 决策信号创建 / 反馈 / 复核 / 结果统计（`/decision-signals`，admin 鉴权） | 决策信号生命周期 | ③ 业务实体 CRUD + 编排 | 否 |
| `api/v1/` | `endpoints/` | `alphasift.py` | 选股策略 / 热点 / 筛选任务 CRUD + 任务状态（`/alphasift`） | 选股筛选 | ③ 筛选编排标准，取数透明 | 否 |
| `api/v1/` | `endpoints/` | `agent.py` | AI 对话 chat / research / 模型 / 技能 / 策略流式接口（`/agent`） | AI 对话 / 研究入口 | ③ 系统级 AI 能力，与行情源无关 | 否 |
| `api/v1/` | `endpoints/` | `intelligence.py` | 资讯源 CRUD / fetch / 快讯 / items（`/intelligence`） | 情报 / 资讯管理 | ③ 源配置 CRUD 标准；抓取后端 SaaS 个性下沉 service | 否 |
| `api/v1/` | `endpoints/` | `auth.py` | 登录 / 会话 / 登出 / 刷新（`/auth`） | 认证授权（横切） | ③ 系统级横切功能接口 | 否 |
| `api/v1/` | `endpoints/` | `health.py` | 服务健康检查（`/health`） | 运维探针（横切） | ③ 系统级横切功能接口 | 否 |
| `api/v1/` | `endpoints/` | `system_config.py` | 配置读写、运行时改配置基建（`/config`，数据源 UI 后台） | 配置管理（横切，支撑 §2.5） | ③ 系统级横切功能接口 | 否 |
| `api/v1/` | `endpoints/` | `usage.py` | 使用量统计查询（`/usage`） | 用量统计（横切） | ③ 系统级横切功能接口 | 否 |
| `api/v1/` | `endpoints/` | `limit_pool.py` | 涨停榜 / 跌停榜单查询（`limit-up-board` / `limit-down-board`，入参 `date` + `limit`） | 涨跌停榜单（当前由「情绪」菜单下的涨跌榜页面消费；菜单调整不影响本端点） | ③ 标准功能接口：契约固定（date + limit → `LimitPoolEntry[]`），取数由 ② 层 `limit_pool/` 透明供给（B2 已落地） | 否 |
| `api/v1/` | `endpoints/` | `eod_picker.py` | 尾盘选股：默认筛选条件 / 提交选股任务 / 轮询任务进度与结果 / 单只股票分时明细（`/eod-picker`） | 尾盘选股 | ③ 选股编排标准，取数透明 | 否 |
| `api/v1/` | `endpoints/` | `scanner.py` | 技术信号扫描：扫描选项 / 提交扫描任务 / 轮询任务状态 / 取消任务（`/scanner`） | 技术信号扫描 | ③ 扫描编排标准，取数透明 | 否 |

### <a id="54-与-②-数据源对接层的关系调用链路"></a>5.4 与 ② 数据源对接层的关系（调用链路）

```
前端 → ③ 端点(endpoints/*.py, 契约固定) → ③ 编排(services/*.py) → ② Manager(data_provider/<能力>/base.py) → ② 源适配器(<源>_source.py) → 外部/本地源
            ↑ 不随源变                            ↑ 组合业务规则                ↑ 多源可切换、配置驱动、对上层透明
```

> 铁律：任何“换数据源”动作只发生在 ② 层内部（改配置 / 加源适配器），**③ 层契约与前端代码零改动**。

## <a id="6-横切基础辅助层设计"></a>6. 横切基础辅助层设计

> 本章对应「④ 横切基础辅助层」：被以上各层读取的全局可读基础设施。整体决策见 §2.5（UI 配置页复用运行时改配置）；数据字典建议见开放项 O1。

- **配置与白名单**：`src/config/settings.py` + `system_config_service`。配置键（`KLINE_*` / `STOCKINFO_*` / `CODESEARCH_*` / `REALTIME_*` / `SECTOR_*` / `LIMITPOOL_*`）须登记进 `system_config` 运行时白名单（`_WEBUI_RUNTIME_ENV_FILE_PRIORITY_KEYS`），新增键须注册；其中 `KLINE_*` / `STOCKINFO_*` / `CODESEARCH_*` 已落地，**`SECTOR_*` / `LIMITPOOL_*` 尚未落进 `src/config/settings.py` 与白名单**（分别随 B1 收尾与 B2 建包补齐，见 §10.2）。
- **数据字典模块（应建为独立表，不再以 config 顶替）**：承载跨能力字典，按 §2.7 正确做法本期建表；具体表结构与落点见开放项 O1。

> **落地说明（暂不行执行，后续再修改）**：本节对「横切基础辅助层」中数据字典（O1）的调整——由"建议新增 / 先用 `config.py` 常量顶替"改为"应建为独立表、不再 config 顶替"——**仅作设计立场记录（与 §2.7 正确做法一致）；对应代码落地（新建数据字典表 + Repository、移除 `config.py` 常量顶替）暂不在本期执行，后续再修改 / 排期**。本期实际不动 `config.py`、不新增数据字典表；O1 维持"设计已定、执行待排"状态。
- **UI 配置页**：`/settings` 下「数据源」Tab 复用既有 `POST /api/v1/config` 运行时写 `.env` + `reload_now`，选源逻辑每次请求读 `config.*_data_source`，无需重启即切换。
- **对应目录**：`src/config/settings.py`（横切配置，全局读取）。

---

## <a id="7-后果consequences"></a>7. 后果（Consequences）

### <a id="正面"></a>正面
- 消除 `kline.py` 硬编码三级降级与 `data_provider` 日线层的功能重叠。
- 新增数据源只需写一份 `_normalize_kline` 映射，不碰渲染层。
- 配置驱动切换，无需改代码 / 重启即可切源；UI 可管。
- 与工程既有 `data_provider` / `system_config` 范式一致，无新概念。

### <a id="负面-成本"></a>负面 / 成本
- 方案范围扩大：从「本地 StockDB 浏览页」升级为「行情基础能力统一层」。
- 需改 `kline.py`（瘦端点）+ 新增 `data_provider/{stockdb_fetcher, stocksdk_bridge, kline, stock_info, code_search}`。

### <a id="风险-注意"></a>风险 / 注意
- `data_provider` 已有 `get_stock_name` / `get_stock_list` / `get_stock_membership_boards`（基础信息 / 列表能力），新的 `stock_info` 能力须**复用**这些既有能力 + 加薄适配壳，避免重复东财 / 新浪 / 腾讯 / StockSDK 桥接取数。
- 复权公式对账（AC-3，原方案 §6.2）仍锁在 K 线能力内，是上线硬阻断，未被本 ADR 改变。
- 数据字典按 §2.7 设计立场应建为独立表（不再以 `config.py` 常量顶替），具体建模与落点见 O1；O1 由"可选"上调为"应建"，但**代码落地暂不行执行（见本节落地说明），后续再修改**。
- 复用 `/api/v1/kline` 端点意味着 K 线接口继承 `ADMIN_AUTH`（属管理后台能力，合理）；这与原方案「独立 `/api/stockdb` 避开鉴权」的取舍不同，属有意反转。

---

## <a id="8-备选方案alternatives-considered"></a>8. 备选方案（Alternatives Considered）

| 方案 | 结论 | 理由 |
|---|---|---|
| A. 平铺塞进 `data_provider/kline_sources/` | **否决** | 与现有「一文件一数据源日线实现」维度冲突；东财 / 新浪 / 腾讯取数会与既有 fetcher 重复（双重实现） |
| B. 新建 `market_data/` 平级目录 | **否决** | 用户认同 `data_provider` 为唯一脏活层，平级目录破坏单一职责 |
| C. 各场景各自硬编码（现状） | **否决** | 正是要消除的重复与不可配置问题 |
| D. 把全系统东财 / 新浪 / 腾讯收编为单一总开关 | **否决** | 会牵动 `stock_service` / 组合风险 / 预警 / 回测等大片，远超范围、风险高 |
| E. 在 Python 服务层直接引入 `StockSDK` | **否决** | `StockSDK` 官方形态为 **Node.js 18+ / 浏览器** 的 TS SDK，HermesX 后端主运行时是 Python；直接在 ③ 层或 service 层调用会破坏分层与语言边界，正确做法应是 ② 层桥接为 `stocksdk_source.py` |

---

## <a id="9-落地指引对-stockdataviewmd-的修订要求"></a>9. 落地指引（对 `stock_data_view.md` 的修订要求）

1. **§3 架构**：改为四层 + `data_provider` 脏活层 + 三类能力子包；原「独立 `/api/stockdb` 页」表述改为「StockDB 作为统一基础能力层的一个 `local` source」，并新增 `StockSDK` 作为桥接型 `stocksdk` source。
2. **§9 配置**：新增数据源切换键（`KLINE_DATA_SOURCE` / `KLINE_FALLBACK_ENABLED` / `KLINE_SOURCE_PRIORITY` 及 `STOCKINFO_*` / `CODESEARCH_*`），并补充 `STOCKSDK_*` 桥接配置块（Node 二进制、bridge 入口、超时、限流、fallback 开关）。
3. **§14 修改范围**：文件清单从 `src/integrations/stockdb/` 改为 `data_provider/{stockdb_fetcher, stocksdk_bridge, kline, stock_info, code_search}` + `scripts/stocksdk_bridge/` + `kline.py` 瘦身；§13 代码骨架的 `src/integrations/stockdb/` 路径为占位，以本 ADR 目录决策为准。
4. **范围取「完整 B」**：方案直接覆盖三类能力统一层规格（K 线含复权对账，基础信息 / 代码搜索同模式），而非仅 K 线。
5. **§5 / §6 / §13 路由前缀**：原 `/api/stockdb/*` 统一改为 `/api/v1/kline`（+ 新增 `/api/v1/stock-info`、`/api/v1/code-search`）；请求 / 响应契约（§5 / §6）仍作为统一 `KLinePoint` / `StockInfo` / `CodeSearch` 契约有效。

---

## <a id="10-修改范围与改造代办清单代码执行指引"></a>10. 修改范围与改造代办清单（代码执行指引）

> 本 ADR 给出设计决策，方案 `stock_data_view.md` §3.6（合规审计）+ §3.7（代码改造代办清单 TODO）给出可执行细节。本节把"**要改动的地方**"在 ADR 内浓缩为可直接勾选的**执行台账**，作为后续写代码的统一指引。所有项默认 `[ ] 未开始`；文件级动作细节以方案 §3.7 为准。

### <a id="101-修改范围总览按层-动作分类"></a>10.1 修改范围总览（按层 + 动作分类）

| 层 | 模块 / 文件 | 动作 | 依据 |
|---|---|---|---|
| ① 数据库层 | `src/repositories/__init__.py`（barrel 收口：补 4 个 Repository 导出） | **修改（仅导出收口，零新增表）** | 2.1：零新增表；§3.1 导出约定；StockDB 由进程独占管理，HermesX 不直读文件 |
| ② 数据源对接层 | `data_provider/common/`（base / normalize / cache / rate_limit / health） | **新建** | 2.3、§4.4 |
| ② 数据源对接层 | `data_provider/stocksdk_bridge.py` + `scripts/stocksdk_bridge/`（Node 18 bridge 入口） | **新建** | 2.2、§4.4、A11 |
| ② 数据源对接层 | `data_provider/kline/`（base / local_stockdb / eastmoney / sina / tencent / stocksdk / transform） | **新建** | 2.2/2.3/2.4、A2–A5、A12 |
| ② 数据源对接层 | `data_provider/stockdb_fetcher.py`（共享 StockDB 客户端） | **新建 / 确认** | 2.2、A6 |
| ② 数据源对接层 | `data_provider/stock_info/`、`data_provider/code_search/`（base + 源） | **新建占位** | 2.3、A9/A10、A12 |
| ② 数据源对接层 | `data_provider/limit_pool/`（base / eastmoney_source / stocksdk_source） | **新建**（阶段3，B2） | 2.3、§4.4、B2 |
| ② 数据源对接层 | 既有顶层 `akshare_fetcher.py` / `tushare_fetcher.py` / `efinance_fetcher.py` / `tencent_fetcher.py` / `tickflow_fetcher.py` 等 | **不改**（降级为"物理后端"被 `<源>_source.py` 复用） | 2.3、§4.4 既有文件处置 |
| ③ 功能接口层 | `api/v1/endpoints/kline.py` | **修改（瘦身）** | 2.6、A1 |
| ③ 功能接口层 | 可选 `api/v1/stock-info`、`api/v1/code-search` | **新增**（随 `stock_info/code_search`） | 2.3 |
| ③ 功能接口层 | `src/services/name_to_code_resolver.py` | **修改（取数下沉 code_search，留薄壳）** | 2.2、A10 / A12 |
| ③ 功能接口层 | `src/services/stock_service.py`（`get_stock_name`） | **修改（迁 `stock_info/eastmoney_source.py` / `stock_info/stocksdk_source.py`）** | 2.2、A10 / A12 |
| ③ 功能接口层 | `api/v1/endpoints/sector.py` | **修改（已瘦身）**：板块相关取数与缓存已下沉到 `data_provider/sector/{eastmoney_source,shidaotec_source,stocksdk_source,market_cards_source}.py`，其中 `stocksdk_source.py` 用于总览页标准市场接口与板块资金接口的优先桥接源，`market_cards_source.py` 用于 `/market/index` 的统一卡片列表聚合 | B1 |
| ③ 功能接口层 | `api/v1/endpoints/emotion.py` → `limit_pool.py`（路由 `/api/v1/emotion` → `/api/v1/limit-pool`） | **修改（按服务端能力域重命名）**：端点不完全绑定前端「情绪」菜单分组；前端封装 `apps/hrs-web/src/api/emotionData.ts` → `limitPoolData.ts` 同步；**不兼容变更**（无兼容层，依据 §2.7）。前端页面目录 `pages/Emotion/` 与路由 `/emotion/boardlist` 属 UI 呈现层，保持不动 | §5.3 命名公约 |
| ③ 功能接口层 | `src/services/` 其余 SaaS 外联（alphasift / intelligence / social_sentiment / stock_index_remote） | **不改** | C1 |
| ④ 横切基础辅助层 | `src/config/settings.py` + `.env.example` | **修改**（新增 `KLINE_*` 等切换键） | 2.4/2.5、A7 |
| ④ 横切基础辅助层 | `system_config` 运行时白名单 | **修改**（注册新键） | 2.5、A7 |
| 前端 | `apps/hrs-web/` 新增「数据源配置」Tab（挂 `/settings` 下） | **新建** | 2.5、A8 |

### <a id="102-改造代办清单逐项勾选"></a>10.2 改造代办清单（逐项勾选）

> 图例：`档位` = A 必须 / B 建议（超方案）/ C 不纳入；`前端` = 是否需前端改动。

**Tier A — 本方案必须（逐项必做）**

- [ ] **A1. `api/v1/endpoints/kline.py` 瘦身**：删内联 `_fetch_kline_from_{sina,eastmoney,tencent}`，仅留路由 + 调用 `KlineDataSourceManager.get_kline()`；端点签名（code/period/fqt/limit/before_date）不变 → 前端零改。`[2.2][2.6]`｜前端：❌
- [ ] **A2. 新建 `data_provider/kline/base.py`**：`KlineDataSource(ABC)`（`get_kline` + `_normalize_kline`）+ `KLinePoint` 契约 + `KlineDataSourceManager`（配置选源/回退，多源同级、优先级纯配置、每源自带 TTL）。`[2.3][2.4]`｜前端：❌
- [ ] **A3. 新建 `data_provider/kline/local_stockdb_source.py`**：`LocalStockDBDataSource` 对接 7899，输出 `KLinePoint`；缺失周期（120m/周/月/年）由 `transform.py` 聚合补齐。`[2.2][2.3]`｜前端：❌
- [ ] **A4. 新建 `data_provider/kline/{eastmoney,sina,tencent,stocksdk}_source.py`**：把 kline.py 现有三源取数**平移**进对应源文件，并新增 `stocksdk_source.py` 经 bridge 调用 `stock-sdk`；各自完成 `_normalize_kline()` 映射；禁止保留副本，消除重复实现。`[2.2][2.3]`｜前端：❌
- [ ] **A5. 新建 `data_provider/kline/transform.py`**：共享时间桶聚合（5m~年）+ `pct_chg` 层内统一计算（派生字段，非各源重复）。`[2.4]`｜前端：❌
- [ ] **A6. 新建 / 确认 `data_provider/stockdb_fetcher.py`**：沉淀独立 StockDB 客户端（连接/鉴权/TTL/异常），供 kline / stock_info / code_search 复用，不进端点层。`[2.2]`｜前端：❌
- [ ] **A7. `src/config/settings.py` + `.env.example` + `system_config` 白名单**：新增 `KLINE_DATA_SOURCE` / `KLINE_FALLBACK_ENABLED` / `KLINE_SOURCE_PRIORITY`（+ `STOCKINFO_*` / `CODESEARCH_*`）并注册进运行时可写白名单（`_WEBUI_RUNTIME_ENV_FILE_PRIORITY_KEYS`）；若引入 `StockSDK`，同时补 `STOCKSDK_ENABLED` / `STOCKSDK_NODE_BIN` / `STOCKSDK_BRIDGE_ENTRY` / `STOCKSDK_TIMEOUT_MS` / `STOCKSDK_RATE_LIMIT_RPS` / `STOCKSDK_KLINE_FALLBACK`。`[2.4][2.5]`｜前端：⚠️ 需 A8 配套
- [ ] **A8. 前端新增「数据源配置」Tab（挂 `/settings`）**：复用 `POST /api/v1/config` 运行时写 `.env`，把 `KLINE_*` / `STOCKINFO_*` / `CODESEARCH_*` 与 `STOCKSDK_*` 纳入可写白名单；选项来自枚举（`local/eastmoney/sina/tencent/stocksdk/auto` + 回退链排序 UI）。`[2.5]`｜前端：✅ 需新增页面
- [ ] **A9. `data_provider/stock_info/`、`data_provider/code_search/` 同模式占位**：各建 `base.py`（`ABC` + `Manager`）+ 契约（`StockInfo` / `CodeSearchResult`）+ 至少 1 个 source；优先复用 `get_stock_name` / `get_stock_list` 加薄适配壳，本地 StockDB 与 `stocksdk_source.py` 接入走同一壳。`[2.3]`｜前端：❌
- [ ] **A10. 取数下沉**：`src/services/name_to_code_resolver.py` 取数迁至 `data_provider/code_search/eastmoney_source.py` / `data_provider/code_search/stocksdk_source.py`（功能接口层不再直接 `import akshare` 取数，解析/缓存留薄壳）；`stock_service.get_stock_name` 从 `BaseFetcher` 巨类迁至 `data_provider/stock_info/eastmoney_source.py` / `data_provider/stock_info/stocksdk_source.py`。`[2.2][2.3]`｜前端：❌
- [ ] **A11. 新建 `data_provider/stocksdk_bridge.py` + `scripts/stocksdk_bridge/`**：落地 Node 18 `stock-sdk` bridge，统一承接 Python ↔ Node 的 JSON 调用、错误码映射、健康探针、超时与限流配置，不允许业务层直接 `subprocess` 调 CLI。`[2.2][2.3]`｜前端：❌
- [ ] **A12. 为 `kline / stock_info / code_search` 增补 `stocksdk_source.py`**：将 `StockSDK` 作为桥接型聚合源纳入统一 Manager；优先覆盖 `sdk.kline.*` / `sdk.search()` / `sdk.quotes.*` / `stock-sdk/symbols` 的符号归一能力，必要时在阶段 2/3 再扩到 `realtime / sector`。`[2.3][2.4]`｜前端：❌

**Tier B — 超方案范围（记录状态，独立 follow-up）**

- [x] **B1. `api/v1/endpoints/sector.py` 瘦化与取数下沉**：原内联东财主链路已下沉到 `data_provider/sector/eastmoney_source.py`，行业 / 个股 / ETF / 概念云图已下沉到 `data_provider/sector/shidaotec_source.py`，总览页标准市场接口与板块资金接口新增 `data_provider/sector/stocksdk_source.py` 作为 StockSDK 优先桥接源，并通过 `data_provider/sector/market_cards_source.py` 统一组装 `/api/v1/sector/market-cards?market=<tab-key>` 卡片列表；`sector.py` 当前仅保留路由参数校验、异常映射与响应编排。`[2.2][2.6]`｜前端：❌｜**已完成（文档同步更新）**

- [x] **B2. 涨跌停池下沉到 `data_provider/limit_pool/`，收口为涨跌停数据的唯一入口**（**已完成 2026-10-19**，仅 ⑤ 第二源待 bridge 支持后启用）：① 把 `get_limit_up_pool` / `get_limit_down_pool` 从 `data_provider/akshare_fetcher.py`（`BaseFetcher` 巨类）与 `data_provider/base.py`（`BaseFetcher` 抽象方法 + `DataFetcherManager` 遍历）下沉到 `data_provider/limit_pool/eastmoney_source.py`，内部**复用既有 akshare 东财通道**（`stock_zt_pool_em` / `stock_zt_pool_dtgc_em`），不重写；② 由 `limit_pool/base.py` 的 `LimitPoolDataSourceManager` 统一供给，选源 / 回退 / TTL / 健康冷却复用 `common/base.py`，并固化 `LimitPoolEntry` 契约（涨停 / 跌停以 `pool_type` 区分，后续炸板池 / 昨日涨停池同构扩展）；③ 消费方 `api/v1/endpoints/limit_pool.py`（原 `emotion.py`）与 `src/services/signal_scanner_service.py` 改调新 Manager，删除端点自建的 `_BOARD_CACHE`（含"取数失败也把空结果缓存 60s"的缺陷）；④ 同步迁移 `tests/test_signal_scanner_service.py` / `tests/test_akshare_realtime_logging.py` 的 mock 点，避免测试绕过真实取数层；⑤ 补 `limit_pool/stocksdk_source.py` 作为第二源——**文件已建**，但 StockSDK bridge（`scripts/stocksdk_bridge/bridge.mjs`）的 action 白名单尚无涨跌停池能力，故 `is_available()` **显式返回 False**：回退链结构上就绪、实际仍为东财单源，待 bridge 扩展后启用（启用步骤见该文件 docstring）；⑥ 把 `LIMITPOOL_DATA_SOURCE` / `LIMITPOOL_FALLBACK_ENABLED` / `LIMITPOOL_SOURCE_PRIORITY` 落进 `src/config/settings.py` 并登记运行时白名单——**注意 `sector` 包当前同样未落地 `SECTOR_*`（`getattr` 兜底走默认单源、不可在 UI 配置），可一并补齐**。`[2.2][2.3][2.5][2.7][§4.4]`｜前端：❌｜**已完成（2026-10-19）**：①②③④⑥ 已落地，⑤ 待 StockSDK bridge 提供涨跌停池 action 后启用

**Tier C — 不纳入（仅记录，不改动）**

- [ ] **C1. `src/services/` 直连外部 SaaS**（alphasift / intelligence / social_sentiment / stock_index_remote）：当前直接 `requests.get` 外部 SaaS/LLM；属 SaaS/通知/LLM 边界，与"行情数据源脏活层"不同上下文，**本期不耦合（边界清晰，非妥协）**；按 §2.7，未上线期亦不应在内部堆兼容/容错补丁，其集成范式（settings + 熔断 + 原子缓存）后续可由 `data_provider` 借鉴。`[不同边界]`｜**显式标注：不改动（边界使然）**

### <a id="103-建议执行顺序与依赖"></a>10.3 建议执行顺序与依赖

1. **先建底座**：A2（base/Manager/契约）→ A3/A4/A5（多源 + 聚合）→ A6（StockDB 客户端）→ A11（StockSDK bridge）。
2. **再瘦端点**：A1（kline.py 改调 Manager，删内联脏活）；此时后端已达标，**前端零改**。
3. **接配置闭环**：A7（config + 白名单）→ A8（前端切换 UI）；此阶段把 `stocksdk` 作为可选源暴露给配置层，但默认关闭。
4. **横向扩展**：A9（stock_info/code_search 同模式）→ A10（取数下沉）→ A12（将 `stocksdk_source.py` 接入三类基础能力）。
5. **独立 follow-up**：B1 已完成，后续仅按能力扩展继续在 `data_provider/sector/` 内演进，不再回退到端点内联取数。
6. **不触碰**：C1（service SaaS）。

### <a id="104-完成判据"></a>10.4 完成判据

- Tier A 全部 `[x]` 后，本方案后端即满足 ADR-001 **2.2 / 2.3 / 2.4 / 2.5 / 2.6**；
- Tier B / C 状态明确（B 排期待办、C 显式不纳），不构成遗留隐患；
- 改造完成后 `data_provider/` 实际目录须与 **§4.4 目录铺排总表** 逐行匹配一致（本 ADR 为唯一真源，方案 §3.8.8 已改为引用本表）。

### <a id="105-编制期衍生改动文档-代码收尾已落地"></a>10.5 编制期衍生改动（文档 + 代码收尾，已落地）

> 本节记录编制本 ADR（§3 数据库层设计补全 + 总目录同步）及前序会话中已实际落地的代码/内容改动，与 ADR-001 主体（data_provider 重构，A1–A12）相互独立、互不阻塞；状态以 `[x]` 标注已落地项。这些改动不改变 ADR-001 的核心结论（零新增表、StockDB 由进程独占），仅做落表层导出收口、前端组件统一与文档补全。

| 层 / 域 | 模块 / 文件 | 动作 | 依据 / 说明 |
|---|---|---|---|
| ① 数据库层 | `src/repositories/__init__.py` | **修改（已落地 `[x]`）**：补齐 `AlertRepository` / `PortfolioRepository` / `IntelligenceRepository` / `SkillOpinionOutcomeRepository` 导出，barrel 收口为 10 个 Repository 的唯一一致入口 | §3.1 导出约定；不触碰 ORM 模型 / 表结构（零新增表） |
| 前端 | `apps/hrs-web/src/pages/PortfolioPage.tsx` | **修改（已落地 `[x]`）**：无账户提示 `InlineAlert` → `InlineToast`（`variant="warning"`），`content` 包为 `ParsedApiError`（`title: text.noAccountsTitle` / `message` / `rawMessage: text.noAccountsMsg` / `category: 'unknown'`） | 前端组件统一；保留原 `className` 视觉 |
| 前端 | `apps/hrs-web/src/locales/featureText.ts`（en） | **修改（已落地 `[x]`）**：`noAccounts` 拆为 `noAccountsTitle` + `noAccountsMsg`，与 zh 对齐 | i18n 文案 parity |
| 文档 | `backend_architecture_adr.md` | **修改（已落地 `[x]`）**：§3 新增 3.1/3.2/3.3（落表文件职责 / storage.py 基座 / 四层定位）；总目录补 3.1–3.3 锚点；修复 10.2 标题与目录锚点不一致 | 本 ADR 数据库层设计补全 |
| ① 数据库层 | `src/services/*`、`tests/*`（Repository 直接 import） | **修改（建议 `[ ]`，D5）**：统一改走 `src/repositories` barrel，落实 §2.7 单一入口 | §2.7 / §3.1 导出约定 |

**衍生改造代办（逐项已勾选）**

- [x] **D1. `src/repositories/__init__.py` barrel 收口**：导出全部 10 个 Repository 类（见 §3.1），作为数据库层唯一一致入口。｜前端：❌
- [x] **D2. `PortfolioPage.tsx` 无账户提示改 `InlineToast`**：`content` 满足 `ParsedApiError` 四字段（`title` / `message` / `rawMessage` / `category`），`rawMessage === message` 不展开"详情"面板。｜前端：✅
- [x] **D3. `featureText.ts`（en）`noAccounts` 拆 `noAccountsTitle`+`noAccountsMsg`**：与 zh 键名对齐，`PortfolioPage` 引用同步（`text.noAccountsTitle` / `text.noAccountsMsg`）。｜前端：✅
- [x] **D4. ADR §3 数据库层设计补全 + 总目录同步 + 10.2 锚点修复**：新增 §3.1/3.2/3.3，总目录补 3.1–3.3 锚点，10.2 标题收敛为「改造代办清单（逐项勾选）」以匹配 `#102-改造代办清单逐项勾选`。｜前端：❌
- [ ] **D5. Repository 直接 import 统一收口到 barrel**：将 `src/services/`、`tests/` 中 `from src.repositories.<x>_repo import <Repository>` 改为 `from src.repositories import <Repository>`（非 Repository 符号如 `PortfolioBusyError` 仍从原模块导入），落实 §2.7 统一入口。｜前端：❌

---

## <a id="11-验证-落地检查表"></a>11. 验证 / 落地检查表

- [ ] `data_provider/stockdb_fetcher.py` 直连 7899 成功返回 `日k` / `分钟k`
- [ ] `data_provider/stocksdk_bridge.py` 能成功调起 Node 18 `stock-sdk`，并完成 JSON 请求 / 响应 / 错误码映射
- [ ] `data_provider/kline/` 五源各自 `_normalize_kline` 输出与 `KLinePoint` 一致
- [ ] `KLINE_DATA_SOURCE` 切换 local / eastmoney / sina / tencent / stocksdk 均出数
- [ ] 主源失败时按 `KLINE_SOURCE_PRIORITY` 自动回退
- [ ] `STOCKINFO_DATA_SOURCE` / `CODESEARCH_DATA_SOURCE` 切换到 `stocksdk` 后，`name_to_code_resolver.py` 与 `stock_service.get_stock_name` 仍保持原契约不变
- [ ] `STOCKSDK_*` 运行时配置（Node 路径 / bridge 入口 / timeout / rate limit / kline fallback）已注册白名单并可通过 `/api/v1/config` 热更新
- [ ] 120m / 5d / yearly 由聚合层补齐（本地源缺失周期不空洞）
- [ ] `/settings` 数据源 Tab 改配置后无需重启即生效（复用 `POST /api/v1/config`）
- [ ] `kline.py` 内联 `_fetch_from_*` 已删除，仅保留路由 + 调用 Manager
- [ ] `data_provider/code_search/base.py` 定义 `CodeSearchDataSource`+Manager（继承 common），`name_to_code_resolver.py` 取数已下沉，由 `eastmoney_source.py` / `stocksdk_source.py` 承接，功能接口层（③）不再直接 `import akshare`
- [ ] `data_provider/stock_info/base.py` 定义 `StockInfoDataSource`+Manager（继承 common），`get_stock_name` 已从 `BaseFetcher` 巨类迁至 `stock_info/eastmoney_source.py` / `stock_info/stocksdk_source.py`
- [x] `data_provider/limit_pool/base.py` 定义 `LimitPoolDataSource`+Manager（继承 common）与 `LimitPoolEntry` 契约；涨停池 / 跌停池取数已从 `data_provider/base.py` 巨类下沉到 `limit_pool/eastmoney_source.py`（`akshare_fetcher.py` 按 §4.4 保留为物理后端）（B2，2026-10-19 已验证）
- [ ] 涨跌停数据收口为唯一入口：`limit_pool.py`（原 `emotion.py`）与 `signal_scanner_service.py` 均经 `limit_pool/` Manager 取涨跌停，③ 层不再经 `DataFetcherManager` 取池数据；`LIMITPOOL_SOURCE_PRIORITY` 在补齐第二源后回退链可生效（B2）

**衍生改动验证（编制期已落地项）**

- [x] **D1 验证**：`src/repositories/__init__.py` 可成功 `import`（barrel 导出 10 个 Repository），`python3 -m py_compile` 通过、lint 0 错误。
- [x] **D2 验证**：`PortfolioPage.tsx` 引用 `InlineToast` 的 `content` 满足 `ParsedApiError`（`title` / `message` / `rawMessage` / `category` 齐全），本地 lint 0 错误；`<InlineAlert>` 无账户提示已从该文件移除。
- [x] **D3 验证**：`featureText.ts` en 的 `noAccountsTitle` / `noAccountsMsg` 与 zh 键名一致，`PortfolioPage` 引用无 undefined 符号。
- [x] **D4 验证**：`backend_architecture_adr.md` 总目录 3.1–3.3 锚点按 IDE 预览 slug 可跳转；§3 与 §10/§11 描述一致（含 10.2 锚点已修复）。
- [ ] **D5 验证**：`src/services/`、`tests/` 中 Repository 类导入统一走 `src/repositories` barrel（非 Repository 符号如 `PortfolioBusyError` 仍从原模块导入）；`python3 -m py_compile` 全量通过。

---

## <a id="12-备注项"></a>12. 备注项

> 本 ADR 的收尾章节：记录修订轨迹、与方案的对应关系、尚未闭合的开放项，以及编码公约引用，便于后续维护与审计。

### <a id="121-修订历史迭代里程碑"></a>12.1 修订历史（迭代里程碑）

| 版本 / 时间 | 关键变更 |
|---|---|
| 初版（2026-10-07 上午） | 确立四层分层 + `data_provider` 唯一脏活层 + 三类基础能力 + 统一契约 |
| 修订 A（2026-10-07 晚） | 内联 `data_provider` 目录铺排总表（方案 §3.8.8 已改为引用本 ADR §4.4）；新增「层级速览表」「两类查询接口归类」「base.py 三层关系」 |
| 修订 B（2026-10-07 晚） | 新增「修改范围与改造代办清单」（现 §10）；原验证表顺延为 §11 |
| 修订 C（2026-10-07 晚） | 目录补全：背景与目标归类、先总后分结构、执行路径置末、新增本「备注项」章 |
| 修订 D（2026-10-07 晚） | 第二章"决策"改名为"整体设计"；按"先总后分"拆分出 §3 数据库层设计 / §4 数据源对接层设计 / §5 功能接口层设计 / §6 横切基础辅助层设计（目录铺排总表等并入 §4）；全文统一四层命名为「数据库层 / 数据源对接层 / 功能接口层 / 横切基础辅助层」 |
| 修订 E（2026-10-07 晚） | **确立"ADR 为主"的落盘顺序**：§5 功能接口层设计升级为该层**权威完整规范**（5.1 定位与边界 / 5.2 端点目录结构 / 5.3 17 个端点铺排总表 / 5.4 调用链路）；主方案 `stock_data_view.md` §3.9 相应**精简为对齐摘要**，权威表迁入 ADR §5.3（避免两处重复、维护漂移）；浏览目录补 5.1–5.4 可点击子项（锚点经 `github-slugger` 校验） |
| 修订 F（2026-10-09） | 新增 `StockSDK` 可行性分析与分层接入方案：将其定义为 **Node 18 桥接型物理后端**，补充 `data_provider/stocksdk_bridge.py` 与各能力 `stocksdk_source.py` 的目录铺排、配置键、执行顺序、验证项与功能接口层边界说明 |
| 修订 G（2026-10-19） | **涨跌停从 `sector/` 剥离，单列 `data_provider/limit_pool/` 功能包**：按「第一维按功能/用途分目录」总则，板块 / 概念（标的维度聚合）与涨跌停榜单（状态维度筛选）属两种不同能力，不应同包；`sector/` 职责收敛为「板块 / 概念 / 热门榜单」，`limit_pool/` 承接涨停池 / 跌停池并预留炸板池 / 昨日涨停池 / 连板梯队，固化 `LimitPoolEntry` 契约（`pool_type` 区分涨跌停）。新增 Tier B 代办 B2（下沉 + 消费方收口 + 第二源）与对应验证项；§5.3 端点铺排表补登记 `emotion.py` / `eod_picker.py` / `scanner.py`（17 → 20；其中 `emotion.py` 于修订 H 改名 `limit_pool.py`）；配置键前缀补登记 `SECTOR_*` / `LIMITPOOL_*` |
| 修订 H（2026-10-19） | **确立端点命名公约，并把涨跌停端点按能力域重命名**：§5.3 新增「登记与命名公约」——端点文件名与路由前缀**建议按照服务端能力域**命名，**不得完全绑定前端菜单分组**（因为菜单会重组、页面会迁移，能力域不会；前端页面只是消费方）。据此 `api/v1/endpoints/emotion.py` / `/api/v1/emotion/*` → `limit_pool.py` / `/api/v1/limit-pool/*`，前端接口封装 `emotionData.ts` → `limitPoolData.ts`；§5.2 目录树补 `eod_picker.py` / `scanner.py` / `limit_pool.py`，§10.1 修改范围登记该重命名。**范围边界**：前端页面目录 `pages/Emotion/`、前端路由 `/emotion/boardlist`、i18n 键 `emotion.board.*` 属 UI 呈现层，不在本次改名范围 |
| 修订 I（2026-10-19） | **B2 落地：涨跌停池下沉到 `data_provider/limit_pool/`**：新建 `limit_pool/{__init__,base,eastmoney_source,stocksdk_source}.py`，固化 `LimitPoolEntry` 契约（13 字段，`pool_type` 区分 `limit_up` / `limit_down`）；`get_limit_up_pool` / `get_limit_down_pool` 从 `data_provider/base.py` 巨类（`BaseFetcher` 抽象方法 + `DataFetcherManager` 遍历）**移除**，`akshare_fetcher.py` 按 §4.4「既有文件处置」**保留为物理后端**并由 `eastmoney_source.py` 复用；消费方 `endpoints/limit_pool.py` 与 `signal_scanner_service.py` 改调 `LimitPoolDataSourceManager`（涨跌停数据收口为唯一入口），端点自建 `_BOARD_CACHE` 删除，**"取数失败也把空结果缓存 60s"缺陷由 Manager「仅在成功时写缓存」的语义修复**；测试 mock 点迁至 `data_provider.limit_pool.get_limit_pool`；`LIMITPOOL_*` 与 `SECTOR_*` 配置键落进 `src/config/settings.py`、运行时白名单与 `.env.example`。**剩余**：`stocksdk_source.py` 因 bridge 无涨跌停 action 而 `is_available()` 返回 False，涨跌停实际仍为东财单源 |

### <a id="122-adr-方案-章节映射"></a>12.2 ADR ↔ 方案 章节映射

| ADR 章节 | 对应方案 `stock_data_view.md` | 关系 |
|---|---|---|
| §1 背景 / 目标 | §1–§2（需求与 StockDB 实测） | ADR 收敛其决策依据 |
| 2.1 四层架构总览 | §3.1（四层定义、目录树、请求流转） | 一一对应 |
| 4.4 目录铺排总表 | （本 ADR 内联，方案 §3.8.8 改为引用） | 本 ADR 为唯一真源 |
| 4.3 两类查询接口 | §3.8.9 | 一一对应 |
| **§5 功能接口层设计**（含 5.3 端点铺排总表） | §3.9（已精简为对齐摘要） | **ADR 为唯一权威基准**，方案只引用不重复列全表 |
| 2.4 统一契约 | §4（契约）/ §3.5（标准化结构） | 一一对应 |
| §10 修改范围 / 代办 | §3.7（改造 TODO） | 一一对应 |
| §11 验证检查表 | §14.9（影响面与回归） | 互补 |

### <a id="123-开放项-待定非阻塞按需闭合"></a>12.3 开放项 / 待定（非阻塞，按需闭合）

- **O1 数据字典模块**：2.1/2.4 提及「【建议新增】数据字典模块」；按 §2.7 正确做法，设计立场应建为独立表 + 对应 Repository，不再以 `config.py` 常量顶替。具体表结构与落点待定；**代码落地暂不在本期执行（见 §6 落地说明），后续再修改**，不长期挂账为临时顶替。
- **O2 StockDB `127.0.0.1:7899` 鉴权**：`STOCKDB_REQUIRE_AUTH` 因复用 `/api/v1` 已继承 `ADMIN_AUTH`，可降级为可选项（见方案 §14.8）。
- **O3 复权对账公式（AC-3）**：复权 vs `gp.js` 对账为上线硬阻断，公式口径需在对账阶段定稿。
- **O6 StockSDK bridge 运行时治理**：`StockSDK` 自身已提供 timeout / retry / rate limit / circuit breaker / host fallback / kline fallback；HermesX 侧仍需决定最终采用 `subprocess` 还是本地 sidecar HTTP/stdio 常驻进程，以及对应的进程守护与日志采样策略。
- **O4 `sector.py` 内联取数（B1）**：已完成下沉并关闭；后续若新增板块子能力，继续收口到 `data_provider/sector/`，不再在端点层追加直连取数。
- **O5 `service` 层 SaaS 外联（C1）**：显式标注不改动，其集成范式后续可借鉴 `data_provider`。

### <a id="124-编码公约引用"></a>12.4 编码公约引用

- 命名 / 目录 / 文件结构以方案 **§3.5（Python 标准化结构）** 为代码落地模板（PEP 8 + HermesX 既有 `*_service.py` / `*_repo.py` / `*_fetcher.py` / `base.py` 规律）。
- 统一契约类型：`KLinePoint` / `StockInfo` / `CodeSearchResult`（见 2.4）。
- 配置键前缀：`KLINE_*` / `STOCKINFO_*` / `CODESEARCH_*` / `REALTIME_*` / `SECTOR_*` / `LIMITPOOL_*` / `STOCKSDK_*`，须登记 `system_config` 白名单（见 §10.2 A7）。
