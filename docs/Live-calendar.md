# 消息日历（Live Calendar）设计方案

> 目标：将华尔街见闻 `https://wallstreetcn.com/calendar` 的财经日历能力搬入 HermesX，提供「宏观 / 财报 / 新股 / 活动 分类 Tab + 月历视图 + 按天标注事件」的日历板块。
>
> 路由：`/live-calendar`；页面组件：`LiveCalendarPage`。
>
> 本文为**方案文档**，所有接口契约、字段映射、实测数据均需在实施阶段严格遵循。

***

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 数据源能力核实（实测佐证）](#2-数据源能力核实实测佐证)
- [3. 分类 Tab 枚举与打标规则](#3-分类-tab-枚举与打标规则)
- [4. 系统架构与分层](#4-系统架构与分层)
- [5. 数据库设计](#5-数据库设计)
- [6. 与 live-news 的差异对比与落表建议](#6-与-live-news-的差异对比与落表建议)
- [7. 后端接口规格（详细）](#7-后端接口规格详细)
- [8. 前端设计](#8-前端设计)
- [9. 日历控件选型与封装方案](#9-日历控件选型与封装方案)
- [10. 接口 / 前端 API / Hook 三方对照表](#10-接口--前端-api--hook-三方对照表)
- [11. 时间维度与精简标题规则](#11-时间维度与精简标题规则)
- [12. 降级策略](#12-降级策略)
- [13. 边界条件与空态处理](#13-边界条件与空态处理)
- [14. 配置与开关](#14-配置与开关)
- [15. 实施计划](#15-实施计划)
- [16. 风险、合规与回滚](#16-风险合规与回滚)
- [17. 命名规范说明](#17-命名规范说明)

***

## 1. 背景与目标

### 1.1 需求来源

参考华尔街见闻财经日历页 `https://wallstreetcn.com/calendar`，该页面具备：

- 顶部 **月份切换**：`◀ 上月 │ 9月2026 │ 10月2026 │ … │ 下月 ▶`
- 工具条：**分类 Tab**（宏观 / 财报 / 新股 / 活动）、**国家筛选**、**重要性筛选**
- 内容区：**月历网格**，每个日期格内标注当天事件，事件带**重要级色阶**与**国旗标识**

### 1.2 关键差异（相对 live-news）

| 维度     | live-news（快讯）        | live-calendar（日历）             |
| ------ | -------------------- | ----------------------------- |
| 时间语义   | 「已发生」，按发布时间倒序流       | 「将发生 / 已发生」，按**日期格子**聚合        |
| 组织方式   | 时间线列表，按天分组           | 月历网格，按天定位                     |
| 刷新语义   | 30s 轮询追新             | 按月拉取 + 手动刷新（低频）               |
| 上游接口   | `/apiv1/content/lives` | `/apiv1/finance/macrodatas`    |
| 上游分类   | `channels`（8 频道）     | `calendar_type`（`FE` / `FD`）+ 服务端打标 |

### 1.3 项目现状（复用基础）

| 已有能力       | 位置                                      | 状态                                        |
| ---------- | --------------------------------------- | ----------------------------------------- |
| 资讯服务主干     | `src/services/intelligence_service.py`  | ✅ 支持 `rss` / `atom` / `newsnow` 三种协议       |
| 资讯持久化      | `src/repositories/intelligence_repo.py` | ✅ 统一落 `intelligence_items`                 |
| 资讯 API     | `api/v1/endpoints/intelligence.py`      | ✅ 已注册 `/api/v1/intelligence/*`（快讯已挂载）      |
| 华尔街见闻抓取范式  | `data_provider/wallstreetcn_live_news.py` | ✅ 可直接照搬其 fetcher 结构（见 §4.1）               |
| 配置项        | `src/config.py` + `.env.example`        | ✅ 资讯类配置入口齐备                               |
| 前端路由       | `apps/hrs-web/src/App.tsx`              | ✅ lazy import + 子路由结构                     |
| 前端基础控件     | `apps/hrs-web/src/components/basic/`    | ✅ 有 `HrsButton` / `Card` / `Badge` 等       |
| **日历控件**   | —                                       | ❌ **缺失，本期封装**                             |
| **日历页面**   | —                                       | ❌ **缺失，本期建设**                             |

> **结论**：后端资讯采集与沉淀链路已完备，本期重点是**新增华尔街见闻日历 fetcher**、**事件分类打标**、**复用现表落库**、**前端日历控件与页面**。

***

## 2. 数据源能力核实（实测佐证）

> 所有数据均为真实调用结果，非推测。抓取时间 2026-09-01，使用 Playwright + Chromium 抓包与 curl 双重验证。

### 2.1 可用接口（实测 `code=20000`）

| #   | 接口                                                                                    | 用途     | 状态                  |
| --- | ------------------------------------------------------------------------------------- | ------ | ------------------- |
| 1   | `GET https://api-one-wscn.awtmt.com/apiv1/finance/countries`                          | 国家字典   | ✅ 200，返回国家/币种/国旗    |
| 2   | `GET https://api-one-wscn.awtmt.com/apiv1/finance/macrodatas?start=<ts>&end=<ts>`     | 日历事件主源 | ✅ 200，返回 `FE` + `FD` |

**请求头**（必需）

| Header       | 值                                    |
| ------------ | ------------------------------------ |
| `User-Agent` | 常规浏览器 UA                             |
| `Referer`    | `https://wallstreetcn.com/calendar`  |

**实测请求样例**（页面首屏真实发出）

```
GET https://api-one-wscn.awtmt.com/apiv1/finance/macrodatas?start=1788192000&end=1788278399
```

> 时间戳换算：`1788192000` = `2026-08-31 16:00:00 UTC` ≈ 北京时间 `9/1 00:00`；
> `1788278399` = `2026-09-01 15:59:59 UTC` ≈ 北京时间 `9/1 23:59`。
> 即页面首屏**只拉当天一天**，跨月展示由前端按月逐次拉取。

### 2.2 接口全景枚举（含不可用项）

按 `20000`（OK）/ `71404`（Not Found）/ `50004`（参数不正确）实测枚举：

| 端点                                              | 状态     | 说明                       |
| ----------------------------------------------- | ------ | ------------------------ |
| `GET /apiv1/finance/countries`                  | ✅ 200  | 国家字典                     |
| `GET /apiv1/finance/macrodatas?start=&end=`     | ✅ 200  | **主日历源**，本期唯一事件来源        |
| `GET /apiv1/finance/reports?start=&end=`        | ⚠️ 200 | 结构合法但 `items=[]`（见 §2.4） |
| `GET /apiv1/finance/ipodatas?start=&end=`       | ⚠️ 200 | 结构合法但 `items=[]`（见 §2.4） |
| `/apiv1/finance/{activitydatas,eventsdatas,earnings,fiscal,fiscaldatas,…}` | ❌ 71404 | 端点不存在                    |
| `/apiv1/content/calendar*`、`/apiv1/calendar/*`   | ❌ 71404 | 端点不存在                    |
| `apiv2` / `apiv3` / 其它子域名（`api-three`、`api-fin`、`data`） | ❌      | 均不可用                     |

### 2.3 macrodatas 返回结构（实测字段全集）

```json
{
  "code": 20000,
  "message": "OK",
  "data": {
    "items": [
      {
        "id": 15044,
        "public_date": 1788192000,
        "observation_date": "",
        "wscn_ticker": "",
        "country": "美国",
        "title": "美联储主席沃什在杰克逊霍尔年会首秀",
        "event": "",
        "country_id": "US",
        "quantity": "",
        "unit": "",
        "importance": 4,
        "mark": "",
        "push_status": false,
        "flag_uri": "https://wpimg-wscn.awtmt.com/<hash>.jpg",
        "calendar_key": "",
        "actual": "",
        "forecast": "",
        "previous": "",
        "revised": "",
        "period": "",
        "calendar_type": "FE",
        "subscribe_status": false,
        "uri": "",
        "assets": "",
        "foresight": "前瞻 | ……"
      }
    ]
  }
}
```

**字段语义与取值分布**

| 字段              | 类型      | 含义                                | 实测分布                                              |
| --------------- | ------- | --------------------------------- | ------------------------------------------------- |
| `id`            | int     | 上游事件 ID                           | 稳定，用作去重键                                          |
| `public_date`   | int     | 事件时间（**秒级 UTC**）                 | 部分为 `0`（全天事件，无具体时刻）                               |
| `calendar_type` | string  | **`FE`** 财经大事件 / **`FD`** 经济数据指标 | 569 条中 `FE=88`、`FD=481`                            |
| `country` / `country_id` | string  | 国家中文名 / 代码                        | 美 145、日 72、中 72、英 53、欧元区 42、德 32、法 29…（共 15+ 国/地区） |
| `importance`    | int     | 重要级（**上游量纲**）                     | **取值集合 `{1,2,3,4}`，上限 4，不存在 5**（3105 条样本实测）。归一化为业务量纲见 §5.7.3 |
| `wscn_ticker`   | string  | 宏观指标代码                            | **仅 `FD` 有值**（如 `JP121749`、`DE132200`），非个股代码；`FE` 恒空 |
| `title`         | string  | 事件标题（简短）                          | 日历格子主文案                                           |
| `foresight`     | string  | 前瞻解读（长文本）                         | 详情页正文；`FD` 多为                                     |
| `flag_uri`      | string  | 国旗图 URL                           | 与 `countries` 接口一致                                 |
| `actual` / `forecast` / `previous` / `revised` | string  | 实际值 / 预测值 / 前值 / 修订值              | **仅 `FD` 有值**，经济数据四件套                              |
| `uri`           | string  | 原文链接                              | `FE` 多为空                                          |

### 2.4 关键结论：分类 Tab 是前端过滤，不是后端分流

**实测方式**：浏览器加载 `/calendar` 后，依次点击「宏观 / 财报 / 新股 / 活动」Tab，监听网络请求。

**实测结果**：**点击任一 Tab 均不产生新的网络请求**。页面加载期只发出 `countries` + `macrodatas` 两个数据请求。

**结论**：

1. 华尔街见闻的「宏观 / 财报 / 新股 / 活动」是**同一批数据 + 客户端过滤**的产物，上游**不提供**分类参数（实测 `channel` / `region` / `market` / `type` / `category` / `ticker` 等参数组合对 `reports` 均返回 0 条）。
2. `reports` / `ipodatas` 端点虽存在，但对**未登录态**恒返回 `items=[]`（覆盖 2024 全年、2026-01、2026-04、2026-08~09 多个区间均验证为空），**本期不作为数据源依赖**，仅预留契约（见 §7.4）。
3. 因此本项目的分类能力必须**自建**：由服务端对 `macrodatas` 返回的事件做**关键字打标**，下发 `tab_keys`（设计见 §3）。

### 2.5 实测样例（佐证分类可行性）

区间 `2026-08-28 ~ 2026-09-25`，共 **569** 条（`FE` 88 / `FD` 481）。以下 `FE` 条目证明「宏观 / 财报 / 新股 / 活动」四类均可从同一批数据中打标切分：

| 日期 / 时刻          | 国家  | 重要级 | 标题                                    | 命中分类 |
| ---------------- | --- | --- | ------------------------------------- | ---- |
| 08-28 04:45      | 美国  | 4   | Marvell 财报与电话会                        | 财报   |
| 08-28 12:02      | 中国  | 2   | 燧原科技 IPO 初步询价                         | 新股   |
| 08-29 12:02      | 中国  | 4   | 长鑫科技上市后首份半年报预计将公布                     | 财报   |
| 08-31 00:00      | 中国  | 3   | A股半年报披露截止日(8月31日)                     | 财报   |
| 08-31 09:20      | 中国  | 4   | 智谱等33只中国股票正式纳入MSCI指数                  | 宏观   |
| 08-31 12:02      | 美国  | 4   | G20财长和央行行长会议，贝森特或警告各国配合对伊经济制裁          | 宏观   |
| 09-01 09:20      | 中国  | 4   | Shein 港股上市                            | 新股   |
| 09-01 12:02      | 中国  | 3   | 2026年上合组织成员国元首理事会会议举行                  | 宏观   |
| 09-01 16:30      | 奥地利 | 1   | 欧洲央行管委科赫尔发表讲话                         | 宏观   |
| 09-02 21:45      | 加拿大 | 3   | 加拿大央行公布利率决议                           | 宏观   |
| 09-03 12:02      | 中国  | 4   | 2026世界动力电池大会9/3-9/4日举行                | 活动   |
| 09-10 01:00      | 美国  | 4   | 苹果 2026 秋季新品发布会（iPhone Fold 首秀…）      | 活动   |
| 09-17 12:02      | 中国  | 3   | 华为全联接大会 2026（上海）                      | 活动   |
| 09-23 12:02      | 美国  | 4   | Meta Connect 2026                     | 活动   |

> **说明**：`FD`（经济数据，481 条）如「8月官方制造业PMI」「二季度GDP同比终值」等，**不参与四个分类 Tab**，仅在「宏观」Tab 下作为可选补充（见 §3.3）。

***

## 3. 分类 Tab 枚举与打标规则

### 3.1 为什么由服务端打标

虽然华尔街见闻是前端过滤，但本项目**不在前端跑正则**，理由：

1. **单一真源**：分类规则只在服务端维护一份，前后端不会漂移；
2. **可落库**：打标结果可持久化，便于后续统计 / 回测复用；
3. **前端简单**：前端只做 `tab_keys.includes(activeTab)` 的包含判断。

### 3.2 Tab 枚举与打标规则

Tab 定义由服务端常量 `LIVE_CALENDAR_TABS` 维护，前端通过 `GET /live-calendar/tabs` 拉取（与 live-news「Tab 由后端驱动」的一致约定）。

| Tab key    | 中文   | 命中规则（`title` + `foresight` 正则）                                                                                                  | 数据来源                       |
| ---------- | ---- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------- |
| `macro`    | 宏观   | `央行\|联储\|美联储\|议息\|利率决议\|褐皮书\|杰克逊霍尔\|CPI\|PMI\|GDP\|非农\|失业率\|通胀\|关税\|休市\|峰会\|国事访问\|公投\|外长\|元首\|理事会\|讲话\|货币政策` | `calendar_type=FE`          |
| `earnings` | 财报   | `财报\|季报\|中报\|年报\|半年报\|业绩\|业绩发布会\|电话会\|披露截止\|财务业绩`                                                                        | `calendar_type=FE`          |
| `ipo`      | 新股   | `IPO\|上市\|招股\|询价\|申购\|挂牌\|纳入.*指数`                                                                                            | `calendar_type=FE`          |
| `activity` | 活动   | `大会\|峰会\|论坛\|发布会\|博览会\|数博会\|展会\|展览\|Connect\|峰会\|会议\|发售\|上新\|开源`                                                       | `calendar_type=FE`          |
| `all`      | 全部   | 不过滤（默认展示 `FE` 全部）                                                                                                              | `calendar_type=FE`          |

> **多归属**：一条事件可命中多个 Tab（如「Shein 港股上市」同时命中 `ipo`；「A股半年报披露截止日」命中 `earnings`）。与 live-news「一条快讯属多频道各存一行」的处理保持一致——**多归属事件按 Tab 拆多行落库**，由唯一约束天然去重（见 §5.3）。

### 3.3 `FD`（经济数据）的定位

| 项       | 决策                                                                       |
| ------- | ------------------------------------------------------------------------ |
| 是否入库    | ✅ 入库（`scope_value='economic_data'`），保留 `actual/forecast/previous` 四值    |
| 是否进 Tab | 默认**不进**四个分类 Tab；在「宏观」Tab 下提供「显示经济数据」开关，开启后合并展示                          |
| 理由      | `FD` 单月 481 条、多为细分指标（如「8月东京CPI(除生鲜食品)同比」），全量进日历格子会淹没 `FE` 重点事件，且格子空间不足 |

### 3.4 未在上游发现的频道

经全量枚举（§2.2），华尔街见闻日历**不存在**「活动」等分类的独立接口。除上述 4 类外，实测数据中还客观存在但**本期不做独立 Tab** 的主题，供后续扩展参考：

| 潜在主题 | 样例                                    | 本期处理        |
| ---- | ------------------------------------- | ----------- |
| 科技发布 | 苹果秋季发布会 / 高通骁龙峰会 / Meta Connect 2026 | 归入 `activity` |
| 地缘政治 | 上合峰会 / 金砖会晤 / 乌俄谈判                    | 归入 `macro`  |
| 人事变动 | 蒂姆·库克卸任苹果 CEO                         | 归入 `macro`  |
| 休市提醒 | 英国金融市场因银行假日休市                         | 归入 `macro`  |

***

## 4. 系统架构与分层

### 4.1 后端分层与改动清单

沿用 live-news 已验证的四层结构：

```
┌──────────────────────────────────────────────────────────────┐
│ API 层        api/v1/endpoints/intelligence.py                │
│               + GET  /live-calendar/tabs                     │
│               + GET  /live-calendar/countries                │
│               + GET  /live-calendar                          │
│               + POST /live-calendar/refresh                  │
│               api/v1/schemas/intelligence.py（新增 4 个模型）      │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│ Service 层    src/services/intelligence_service.py            │
│               + CalendarService                              │
│                 · 月份时间窗换算（UTC）                          │
│                 · 调用 fetcher → 打标 → 落库 → 出库              │
│                 · 上游失败时降级（读库存 + degraded=true）        │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│ Provider 层   data_provider/wallstreetcn_calendar.py（新增）     │
│               + WallstreetcnCalendarFetcher                  │
│                 照搬 wallstreetcn_live_news.py 的：             │
│                 · __init__(base_url, timeout, request_get)    │
│                 · fetch_countries() / fetch_range(start, end) │
│                 · parse_payload() / _coerce_int() 等私有辅助    │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│ Repository 层 src/repositories/intelligence_repo.py           │
│               + upsert_calendar_events(events)               │
│               + list_calendar_events(year, month, tab)       │
│               （复用现 ORM，不新增表）                             │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│ Storage 层    src/storage.py（IntelligenceItem，不新增模型）      │
└──────────────────────────────────────────────────────────────┘
```

**逐层改动表**

| 层         | 文件                                          | 动作 | 改动内容                                                                                     |
| --------- | ------------------------------------------- | -- | ---------------------------------------------------------------------------------------- |
| API       | `api/v1/endpoints/intelligence.py`          | 新增 | 4 个路由（挂现 `/api/v1/intelligence` 前缀下，与 live-news 并列）                                       |
| API       | `api/v1/schemas/intelligence.py`            | 新增 | `CalendarTab` / `CalendarCountry` / `CalendarEvent` / `CalendarMonthResponse` 等 Pydantic 模型 |
| Service   | `src/services/intelligence_service.py`      | 新增 | `CalendarService`（**不动**现有 `LiveNewsService` 任何逻辑）                                        |
| Provider  | `data_provider/wallstreetcn_calendar.py`    | 新增 | `WallstreetcnCalendarFetcher`（结构对齐 `wallstreetcn_live_news.py`）                          |
| Repository| `src/repositories/intelligence_repo.py`     | 新增 | `upsert_calendar_events()` / `list_calendar_events()`（**不动**现有快讯方法）                       |
| Storage   | `src/storage.py`                            | **仅新增迁移函数** | 复用 `IntelligenceItem`；所需列（`scope_type` / `scope_value` / `importance`）**均已存在，不加列**（核实见 §5.1.1、§5.7.6）。仅需新增 `importance` 存量归一化迁移函数，不改现有列与索引 |
| Config    | `src/config.py` + `.env.example`            | 新增 | `WALLSTREETCN_CALENDAR_ENABLED` / `_TIMEOUT` / `_BASE_URL`                                |
| Tests     | `tests/test_live_calendar.py`               | 新增 | fetcher 解析单测（不触网）+ service 集成测（mock fetcher）                                           |
| Docs      | `docs/Live-calendar.md`、`docs/CHANGELOG.md` | 新增 | 本文档 + CHANGELOG 一行                                                                       |

### 4.2 前端分层与改动清单

| 层      | 文件                                                    | 动作 | 改动内容                                          |
| ------ | ----------------------------------------------------- | -- | --------------------------------------------- |
| 类型     | `apps/hrs-web/src/types/liveCalendar.ts`              | 新增 | 数据契约类型（按 TYPE_NAMING 用 `Def` 后缀，见 §8.4）        |
| API    | `apps/hrs-web/src/api/liveCalendar.ts`                | 新增 | 4 个 API 函数（snake→camel 归一化，对齐 `liveNews.ts` 风格） |
| Hook   | `apps/hrs-web/src/hooks/useLiveCalendar.ts`           | 新增 | 3 个 Hook                                      |
| 常量     | `apps/hrs-web/src/constants/cacheConfig.ts`           | 修改 | 追加 `liveCalendar` 缓存键                         |
| 常量     | `apps/hrs-web/src/constants/newsImportance.ts`           | 新增 | 重要度共享语义（§8.5，快讯与日历复用）                        |
| 页面     | `apps/hrs-web/src/pages/LiveCalendarPage.tsx`         | 新增 | 页面装配（月份条 + Grid + 详情面板）                      |
| 控件     | `apps/hrs-web/src/components/common/LiveCalendarGrid/` | 新增 | FullCalendar v6 二次封装（目录见 §9.4，含 `index.ts`）     |
| 控件     | `apps/hrs-web/src/components/common/LiveCalendarTabs/` | 新增 | 分类 Tab（基于 HeroUI `Tabs`，目录同规范）                 |
| 路由     | `apps/hrs-web/src/App.tsx`                            | 修改 | lazy import + `<Route path="/live-calendar">`  |
| 导航     | `apps/hrs-web/src/components/layout/SidebarNav.tsx`   | 修改 | `NAV_ITEMS` 追加一项                              |
| i18n   | `apps/hrs-web/src/i18n/uiText.ts`                     | 修改 | `liveCalendar.*` 文案（I18N_NAMING 第 7 类）          |
| 依赖     | `apps/hrs-web/package.json`                           | 修改 | 新增 FullCalendar 系列（§14）；**不装** `date-fns`     |

***

## 5. 数据库设计

### 5.1 结论：不新增表，复用 `intelligence_items`

**落表策略**：与 live-news 共用 `intelligence_items`，靠 `scope_type` / `scope_value` 区分。

| 业务        | `scope_type` | `scope_value`                                          |
| --------- | ------------ | ------------------------------------------------------ |
| 通用资讯      | `symbol` / `market` / `sector` | 股票代码 / 市场 / 板块                     |
| 实时快讯（现有）  | `channel`    | 频道短码（`global` / `a-stock` / … 8 个）                       |
| **消息日历（本期）** | **`calendar`** | **分类短码（`macro` / `earnings` / `ipo` / `activity` / `economic_data`）** |

> 该设计与现有 `IntelligenceItem` docstring 声明的「通用资讯与实时快讯共用本表，靠 `scope_type`/`scope_value` 区分」完全一致，属于**契约内扩展**，非平行实现。

#### 5.1.1 `scope_type` / `scope_value` 字段现状：**已存在，无需新增列**

两列均为 `IntelligenceItem` **模型原生列**（`src/storage.py:345-347`），建表时由 `create_all` 直接带上，**不是后期补的**：

```python
scope_type  = Column(String(32), nullable=False, default='market', index=True)
scope_value = Column(String(64), nullable=False, default=INTELLIGENCE_ITEM_NULL_SCOPE_VALUE, index=True)
```

| 校验项    | 结论                                                                                                                    |
| ------ | --------------------------------------------------------------------------------------------------------------------- |
| 列是否存在  | ✅ 已存在                                                                                                                 |
| 长度是否够用 | ✅ `scope_type` VARCHAR(32) 容纳 `calendar`（8 字符）；`scope_value` VARCHAR(64) 容纳最长分类短码 `economic_data`（13 字符），余量充足     |
| 是否需迁移  | ❌ 无需任何 DDL / 迁移脚本                                                                                                     |
| 索引是否覆盖 | ✅ 已有 `ix_intel_item_scope_time(scope_type, scope_value, market, published_at)`，完全覆盖日历主查询形态                           |

> ⚠️ **易踩的坑：`_ALLOWED_SCOPE_TYPES` 白名单**
>
> `src/services/intelligence_service.py:66` 定义了：
> ```python
> _ALLOWED_SCOPE_TYPES = {"symbol", "market", "sector"}
> ```
> 该白名单**不包含** `channel`，也**不包含** `calendar`。但它**仅用于** `_normalize_source_fields()`（同文件 :494），即**创建/更新资讯源配置（`IntelligenceSource`）时**的入参校验。
>
> **关键判据**：快讯使用的 `scope_type='channel'` 同样不在该白名单内，但快讯功能正常工作——因为**快讯不注册源**（`source_id` 为 `NULL`），根本不经过此校验。
>
> **因此日历必须遵循与快讯相同的约定**：**不向 `intelligence_sources` 表注册源记录，`source_id` 保持 `NULL`**。只要遵守该约定，`scope_type='calendar'` 不会触发任何校验错误。实施时需加一条集成测断言该行为。

#### 5.1.2 为什么日历「不注册源」：架构判据

> 本节回答「注册源是什么、为什么要注册、日历该不该注册」。结论是**不注册**，但这是基于架构职责的判断，不是图省事。

**注册源的本质**：在 `intelligence_sources` 表插入一条记录。**它不是「数据源清单」，而是「通用调度器的抓取任务表」**——注册的直接后果是被批量抓取（`intelligence_service.py:381-408`）：

```python
def fetch_enabled_sources(self) -> Dict[str, Any]:
    rows, total = self.repo.list_sources(enabled=True, page=1, page_size=100)
    for row in rows:
        results.append(self.fetch_source(row.id))   # ← 遍历抓取
```

**注册带来的能力**

| 能力       | 说明                                                       |
| -------- | -------------------------------------------------------- |
| 批量调度     | `fetch_enabled_sources()` 遍历 `enabled=True` 全部行           |
| 配置承载     | URL、协议、`scope_type`/`scope_value`/`market` 归属             |
| 健康状态     | `last_status` / `last_error` / `last_fetched_at`（**最实在的收益**） |
| 用户启停     | `enabled` 字段 + 管理 API                                    |
| SSRF 校验  | 抓取前校验 URL 合法性                                            |

**当前已注册的源**：`_NEWSNOW_DEFAULT_SOURCE_DEFS`（`service.py:136` 起）共 **5 个**内置源，注册时统一 `scope_type="market"`（`service.py:1008`）：

| 源                    | `source_id`          | `market` |
| -------------------- | -------------------- | -------- |
| NewsNow 财联社热门        | `cls-hot`            | cn       |
| NewsNow 雪球热门股票       | `xueqiu-hotstock`    | cn       |
| NewsNow 华尔街见闻快讯      | `wallstreetcn-quick` | cn       |
| NewsNow 金十数据         | `jin10`              | global   |
| NewsNow 格隆汇          | `gelonghui`          | cn       |

**未注册的**：快讯（`scope_type='channel'`）。

**判断标准：通用链路能否正确表达该抓取任务**

| 维度                                | RSS / NewsNow | 快讯                | 日历                  |
| --------------------------------- | ------------- | ----------------- | ------------------- |
| 抓取所需参数                            | 仅 URL（无参数）    | `channel`（**8 个**） | `year`+`month`（**时间窗**） |
| 通用链路 `fetch_source(id)` 能否表达       | ✅ 能            | ❌ 一条记录装不下 8 频道    | ❌ **链路中根本没有月份参数**   |
| 调度方式                              | 批量遍历          | 独立入口 `refresh_live_news()` | 独立入口（按月 + 手动刷新）    |
| 触发时机                              | 分析管线 / 大盘复盘 / API | 列表接口惰性触发          | 页面按月拉取 + 手动刷新       |

**四条判据**

1. **注册了也抓不对**——日历需要 `year/month` 时间窗，而 `fetch_source(row.id)` 只接受 `source_id`，通用链路无法传递月份参数。这是契约不匹配，不是配置问题。
2. **注册会被误抓**——一旦 `enabled=True`，`fetch_enabled_sources()` 就会遍历到它并以错误参数抓取。这正是快讯 docstring 所写的「会被通用抓取链路误抓」。
3. **白名单冲突**——注册要求 `scope_type ∈ {symbol, market, sector}`。`calendar` 不在其中，只有两条路：改白名单（把内置能力混进「用户自定义源」语义，污染通用逻辑），或填 `market`（语义错误，日历不是市场维度）。两条都不对。
4. **健康状态可用既有范式替代**——快讯已给出不注册也能暴露状态的范式：类变量 `_live_news_degraded` + 接口下发 `degraded` 字段。日历照此办理（见 §12），无需依赖注册表。

> **结论：日历不注册源，与快讯保持同一架构位置。**
>
> 补充事实：通用自动抓取开关 `news_intel_auto_fetch_enabled` **默认为 `False`**（`config.py:837`），即默认不自动抓取；其调用方仅为个股分析管线（`pipeline.py:2735`）、大盘复盘（`market_analyzer.py:1821`）与 HTTP API（`intelligence.py:199`），**无 cron 定时**。这进一步说明注册与否不影响日历的可用性。

### 5.2 现有表结构（`intelligence_items`，不改 DDL）

> 下表为**现有真实结构**，本期**不修改任何一行**。（`scope_type` / `scope_value` 为模型原生列，见 §5.1.1；`importance` 虽已存在但属后期补充列，上线检查项见 §5.7.6）

```sql
CREATE TABLE intelligence_items (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id    INTEGER REFERENCES intelligence_sources(id) ON DELETE SET NULL,
  source_name  VARCHAR(100),
  source_type  VARCHAR(32)  NOT NULL DEFAULT 'rss',
  title        VARCHAR(300) NOT NULL,
  summary      TEXT,
  url          VARCHAR(1000) NOT NULL,
  source       VARCHAR(100),
  published_at DATETIME,
  fetched_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,
  scope_type   VARCHAR(32)  NOT NULL DEFAULT 'market',
  scope_value  VARCHAR(64)  NOT NULL DEFAULT '_',
  market       VARCHAR(32)  NOT NULL DEFAULT 'cn',
  raw_payload  TEXT,
  importance   INTEGER
);

CREATE UNIQUE INDEX uix_intel_item_source_scope_url
  ON intelligence_items (source_id, url, scope_type, scope_value, market);
CREATE INDEX ix_intel_item_scope_time
  ON intelligence_items (scope_type, scope_value, market, published_at);
CREATE INDEX ix_intel_item_fetch_time
  ON intelligence_items (fetched_at);
CREATE INDEX ix_intel_item_channel_importance_time
  ON intelligence_items (scope_value, importance, published_at);
```

### 5.3 字段映射（上游 → 落库）

| 上游 `macrodatas` 字段                              | 落库列             | 转换规则                                                       |
| ----------------------------------------------- | --------------- | ---------------------------------------------------------- |
| `id`                                            | `raw_payload` + `url` | `url = f"wscn-calendar/{id}"`（构造稳定去重键；上游 `uri` 多为空，不可用）    |
| `title`                                         | `title`         | 直接取；为空时回退 `foresight` 首行截断 300 字                           |
| `foresight`                                     | `summary`       | 直接取                                                        |
| `public_date`                                   | `published_at`  | `datetime.utcfromtimestamp()`；**为 0 时**取该日 00:00:00（全天事件） |
| `importance`                                    | `importance`    | **原值直存（`1~4`）**；缺失或非法时填 **`0`**（无，非"普通"）。统一业务量纲见 §5.7     |
| `country_id`                                    | `market`        | 归一：`US→us` / `CN→cn` / `HK→hk` / 其余→`global`               |
| 整条原始 JSON                                       | `raw_payload`   | `json.dumps(..., ensure_ascii=False)`，保留 `actual/forecast/previous` 等未映射字段 |
| —                                               | `source_name`   | 固定 `'wallstreetcn-calendar'`                               |
| —                                               | `source_type`   | 固定 `'wscn_calendar'`                                       |
| —                                               | `source`        | 固定 `'华尔街见闻'`                                               |
| —                                               | `scope_type`    | 固定 `'calendar'`                                            |
| 打标结果（§3.2）                                      | `scope_value`   | `macro` / `earnings` / `ipo` / `activity` / `economic_data` |
| —                                               | `source_id`     | `NULL`（与快讯一致：日历源不注册到 `intelligence_sources`）               |

### 5.4 多归属事件的落库

一条事件命中 N 个 Tab 时**存 N 行**（`scope_value` 各不相同），由 `uix_intel_item_source_scope_url` 天然不冲突，与快讯「多频道各存一行」完全一致。

> ⚠️ **SQLite 注意**：`source_id` 为 `NULL` 时 SQLite 唯一约束不生效（`NULL != NULL`），因此去重**必须由仓储层按 `source_name + url + scope_value` 显式匹配后 upsert**，与快讯现有实现保持一致。

### 5.5 国家字典的落库

`countries` 接口返回的国家字典**不进 `intelligence_items`**（避免污染资讯表）。

| 方案                    | 选择                                                                        |
| --------------------- | ------------------------------------------------------------------------- |
| A. 新建 `calendar_countries` 表 | ❌ 新增表，违反复用原则                                                              |
| B. 内存缓存（TTL 24h）      | ✅ **选用**：国家字典是低频稳定数据，进程内缓存即可，重启自动重建                                       |
| C. 每次请求转发上游           | ❌ 增加上游压力与延迟                                                               |

### 5.6 索引与清理

| 项      | 决策                                                                                  |
| ------ | ----------------------------------------------------------------------------------- |
| 新增索引   | ❌ **不新增**。现有 `ix_intel_item_scope_time(scope_type, scope_value, market, published_at)` 已完全覆盖「按分类 + 月份范围查事件」的查询形态 |
| 保留期清理  | ❌ **不纳入** `fetched_at` 保留期清理。日历为按月全量覆盖写，历史月份有归档价值；清理策略由后续需求单独定义                    |
| 写入压力   | 单月约 600 条 × 多归属膨胀 ≈ 1000~1500 行/月，远低于快讯的轮询写入量                                       |

### 5.7 `importance` 字段：统一业务量纲方案

> 这是本次落表设计中**唯一需要改造既有链路**的字段。以下为多轮评审后收敛的最终方案。

#### 5.7.1 设计原则

> **数据源只是数据提供方；重要度的业务定义归本项目所有。**

上游（华尔街见闻快讯 `score`、华尔街见闻日历 `importance`、NewsNow、RSS/Atom）各自的重要级量纲互不相同，**这些上游量纲只允许出现在「归一化入口」一处**。归一化之后，落库列、API 契约、前端渲染统一使用本项目定义的业务量纲。

该原则带来三个直接收益：

1. **换源不改契约**——将来替换或新增数据源，只需在入口补一条映射，前端零感知；
2. **跨源可比较**——不同数据源的重要度可直接比较与统一筛选；
3. **消除一致性陷阱**——下游不再出现「同一字段两种量纲」的分裂状态。

#### 5.7.2 统一量纲定义

| 值   | 语义      | 说明                             |
| --- | ------- | ------------------------------ |
| `0` | **无**   | 数据源未提供重要度信息（**不是「最低等级」**）      |
| `1` | 普通      |                                |
| `2` | 较重要     |                                |
| `3` | 重要      | **默认阈值所在档**                    |
| `4` | 非常重要    |                                |

**`0` 的语义边界（重要）**

| | `0`（无） | `1`（普通） |
|---|---|---|
| 含义 | 数据源**没告诉我**重要度 | 数据源明确说**这是普通的** |
| 筛选 `>= 3` | 不命中 | 不命中 |
| 排序 | 落在末位 | 倒数第二 |
| UI | **不渲染任何重要度标记** | 渲染「普通」色阶 |

> ⚠️ 切勿把「上游缺失」兜底为 `1`。「没告诉我」≠「这是普通的」，兜底成 `1` 会污染统计（如「普通级事件数」会混入无数据条目）。

#### 5.7.3 各数据源的归一化映射

| 数据源                    | 上游字段         | 上游取值        | 归一化映射                            | 落库值       |
| ---------------------- | ------------ | ----------- | -------------------------------- | --------- |
| **华尔街见闻日历**（本期）        | `importance` | `{1,2,3,4}` | **原值直存**                         | `{1,2,3,4}` |
| 华尔街见闻日历（上游缺失/非法）      | —            | 缺失          | → `0`                            | `0`       |
| **华尔街见闻快讯**（改造）        | `score`      | `{1,2,3}`   | **`{1→1, 2→3, 3→4}`**（语义守恒）      | `{1,3,4}` |
| **NewsNow 降级源**（改造）    | 无该字段         | —           | → `0`                            | `0`       |
| 通用 RSS / Atom（现状保持）     | 无该字段         | —           | 本期**不处理**，维持 `NULL`（见 §5.7.6 待确认） | `NULL`    |

**快讯映射为何是 `{1→1, 2→3, 3→4}` 而非简单 `+1`**

快讯上游语义为 `1=普通 / 2=重要 / 3=非常重要`（见 `storage.py:351` 注释），**本身没有「较重要」这一档**。

| 原值 | 原语义  | 简单 `+1`  | 落入语义               | 语义守恒映射 | 落入语义  |
| -- | ---- | -------- | ------------------ | ------ | ----- |
| 1  | 普通   | 2        | 较重要 ❌ **虚增一档**     | **1**  | 普通 ✅  |
| 2  | 重要   | 3        | 重要 ✅               | **3**  | 重要 ✅  |
| 3  | 非常重要 | 4        | 非常重要 ✅             | **4**  | 非常重要 ✅ |

采用语义守恒映射，快讯落库取值集合为 `{1,3,4}`（无 `2`），如实反映「快讯无较重要档」。

#### 5.7.4 数据流与唯一归一化点

```
【入口】数据源（上游量纲仅在此出现）
   华尔街见闻日历 importance ∈ {1,2,3,4}   │   华尔街见闻快讯 score ∈ {1,2,3}   │   NewsNow 无字段
        ↓                                    ↓                            ↓
【归一化】唯一映射点                            【归一化】                       【归一化】
   CalendarService                     _entry_to_live_news_fields()      同上
   原值直存 / 缺失→0                      {1→1,2→3,3→4} / 无→0              → 0
        ↓                                    ↓                            ↓
        └────────────────────────────────────┴────────────────────────────┘
                                             ↓
                            【落库】intelligence_items.importance
                                  统一业务量纲 {0,1,2,3,4}
                                             ↓
                            【输出】API JSON → 前端
                                  score 恒为 number（0~4）
```

> `raw_payload` 中**继续保留上游原始值**（快讯的 `entry.score` 等），仅用于数据溯源与回滚；**不参与 API 输出**。

#### 5.7.5 阈值：统一取 `3`

「重要」对应量纲 `3`，阈值统一为 **3**。

| 数据       | 落库量纲         | 阈值 3 命中  | 等价于上游      | 占比      |
| -------- | ------------ | -------- | ---------- | ------- |
| 快讯（改造后）  | `{1,3,4}`    | `{3,4}`  | 原 `{2,3}`  | **31%** |
| 日历       | `{1,2,3,4}`  | `{3,4}`  | 原 `{3,4}`  | **31.9%** |

> ✅ 两者一致，且与快讯改造前（阈值 `2` → 31%）**完全持平，用户无感知**。

**阈值实测依据（日历 `FE` 932 条）**

| 阈值   | 命中       | 占比    |
| ---- | -------- | ----- |
| `2`  | 497/932  | 53.3% |
| `3`  | 297/932  | 31.9% |
| `4`  | 124/932  | 13.3% |

阈值 `2` 会让 53.3% 的事件被判为「重要」，筛选失去区分度；`3` 是合理档位。

#### 5.7.6 存量数据迁移（必须执行）

**字段现状：`importance` 列已存在，但属于「后期补充列」**

`importance` 列定义见 `src/storage.py:354`（`Column(Integer, nullable=True, index=True)`）。与 `scope_type` / `scope_value` 这类**模型原生列**不同，它是后续迭代补上的：

| 场景   | 行为                                                                                        |
| ---- | ----------------------------------------------------------------------------------------- |
| 新建库  | `create_all` 建表时直接带上该列                                                                     |
| 存量库  | 由 `_ensure_intelligence_item_importance_column()`（`storage.py:1993`）启动时幂等补齐，**失败仅告警不阻断启动** |

> **上线检查项**：需确认目标库该列已存在。若补列曾失败（日志含 `[Intelligence] … 补充 importance 列失败`），重要级将全部退化为 `NULL`，须先人工修复。

**不迁移会造成严重功能回归**：阈值改为 `3` 后，若历史快讯仍是旧量纲 `{1,2,3}`，则只有 `3` 命中，重要率从 **31% 暴跌至 2%**。

**迁移 SQL（快讯）**

```sql
UPDATE intelligence_items
SET importance = CASE
    WHEN importance IS NULL THEN 0      -- 降级源：无 → 0
    WHEN importance = 1     THEN 1      -- 普通 → 普通
    WHEN importance = 2     THEN 3      -- 重要 → 重要
    WHEN importance = 3     THEN 4      -- 非常重要 → 非常重要
    ELSE importance
END
WHERE scope_type = 'channel';
```

> ⚠️ **SQL 陷阱**：`NULL` 不能用 `=` 比较，必须写成 `WHEN importance IS NULL`，写成 `CASE importance WHEN NULL THEN 0` 将**永不匹配**。
>
> ⚠️ `WHERE scope_type = 'channel'` 不可省略，否则会误改日历与通用资讯数据。

**幂等性（关键风险）**

迁移前后取值集合存在交集（前 `{1,2,3}` / 后 `{0,1,3,4}`），**无法从数据形态判断是否已迁移**，重复执行会导致二次映射。

因此必须采用**标记式幂等**：执行前检查 `DatabaseSchemaMigration` 表中是否存在对应 version（如 `live_news_importance_rescale_v1`），存在则跳过。

> 参照实现：`_ensure_schema_migration_record`（`storage.py:1551`）的版本记录方式 + `_ensure_intelligence_items_scoped_unique_index_once`（`storage.py:1864`）的「检查→跳过」结构。

**待确认：通用资讯（`symbol`/`market`/`sector`）的存量 `NULL`**

本期**建议暂不迁移**，理由：通用资讯目前**没有任何代码消费 `importance`**（仅快讯与日历使用），此时全表迁移属于为尚未出现的需求预付成本，违反最小改动原则。待通用资讯产生重要度需求时再迁不迟。

| 选项          | 做法                    | 评价                       |
| ----------- | --------------------- | ------------------------ |
| **A. 只迁快讯**（建议） | 仅 `scope_type='channel'` | 改动小、风险低；通用资讯仍为 `NULL` |
| B. 全表迁移     | 所有 `NULL` → `0`         | 彻底统一；但改动当前无消费方的数据     |

#### 5.7.7 改动点汇总（5 处）

| #   | 位置                              | 改动                                                       |
| --- | ------------------------------- | -------------------------------------------------------- |
| 1   | `service.py:1390`               | 快讯写入映射：`int(entry.score or 1)` → 映射函数（无→`0`）；`raw_payload.score` **保持原始值不动** |
| 2   | `service.py:1428`               | 降级源 `"importance": None` → **`0`**                         |
| 3   | `service.py:1472-1487`          | **简化**：`score` 直接读 `importance` 列，**删除** `raw_payload` 优先与 fallback 分支 |
| 4   | `storage.py`                    | 新增迁移函数（标记式幂等）                                            |
| 5   | `config.py`                     | `wscn_live_news_important_score` 默认 `2` → **`3`**           |

**改动点 3 的前后对比**

```python
# 改造前（6 行，两条路径语义可能分裂）
score = raw.get("score")
if not isinstance(score, int):
    score = int(item.importance) if item.importance is not None else 1
importance = item.importance

# 改造后（1 行，天然一致）
score = item.importance
```

> 由于归一化已在入口完成，`item.importance` 恒为业务量纲，**无需反向映射**，fallback 分支自然消失。

#### 5.7.8 前后端职责

| 环节    | 职责                                                                                       |
| ----- | ---------------------------------------------------------------------------------------- |
| 后端    | 归一化唯一映射点落库；`score` 输出业务量纲（`0~4` 的 `number`）；`important` = `importance >= 3`                |
| 前端    | 消费 `importance` 数值做色阶与筛选；共享常量见 §8.5                                                     |
| UI 色阶 | `0` **不渲染标记** / `1` 灰 / `2` 浅主色 / `3` 主色 / `4` 暖色高亮+加粗                                  |
| 阈值    | 后端 `wscn_live_news_important_score` 与日历阈值均取 `3`；前端 `IMPORTANT_THRESHOLD` 常量与之对齐          |

#### 5.7.9 建议补充的回归测试

| #   | 测试                                                          | 目的            |
| --- | ----------------------------------------------------------- | ------------- |
| 1   | 快讯映射函数：`{None→0, 1→1, 2→3, 3→4}` 逐值断言                       | 映射正确性         |
| 2   | 迁移函数**连续执行两次**，结果与执行一次相同                                     | 幂等性（最关键）      |
| 3   | 迁移后同一样本的 `important` 结果与迁移前一致                                | 用户无感知         |
| 4   | 迁移 SQL 的影响行数等于 `scope_type='channel'` 的总行数                  | 未误伤其他业务       |
| 5   | `list_calendar_events()` 结果集 `scope_type` 全为 `calendar`      | 防跨业务查询        |
| 6   | 快讯 `important_only=True` 的查询条件含 `scope_type == 'channel'`   | 防跨业务查询        |

***

## 6. 与 live-news 的差异对比与落表建议

### 6.1 差异对比

| 维度        | live-news（快讯）                        | live-calendar（日历）                            | 是否冲突 |
| --------- | ------------------------------------ | -------------------------------------------- | ---- |
| 上游接口      | `/apiv1/content/lives?channel=`     | `/apiv1/finance/macrodatas?start=&end=`      | 否    |
| 上游域名      | `api-one.wallstcn.com`               | `api-one-wscn.awtmt.com`                     | 否    |
| 上游分类字段    | `channels`（8 频道，多值数组）                | `calendar_type`（`FE`/`FD`）+ 服务端打标            | 否    |
| 时间语义      | 已发生，秒级实时                             | 将发生/已发生，日粒度 + 可选时刻                           | 否    |
| 拉取频率      | 30s 轮询                               | 按月拉取 + 手动刷新（低频）                              | 否    |
| 单批数据量     | 30 条/次                               | ~600 条/月                                     | 否    |
| `title`   | 常为空，需回退 `content` 首行                 | 恒有值                                          | 否    |
| 正文字段      | `content`（快讯正文）                      | `foresight`（前瞻解读）                            | 否    |
| 时间字段      | `display_time`（秒级）                   | `public_date`（秒级，可为 0）                       | 否    |
| `importance` | `score`，上游取值 `{1,2,3}`，**需归一化为 `{1,3,4}`** | `importance`，上游取值 `{1,2,3,4}`，**原值直存** | ✅ 已统一为业务量纲 `{0,1,2,3,4}`，阈值均取 `3`（见 §5.7） |
| 唯一性       | `scope_type='channel'` + 频道短码        | `scope_type='calendar'` + 分类短码               | 否    |
| 多归属       | 一条快讯属多频道 → 各存一行                      | 一条事件属多分类 → 各存一行                              | 否（同机制） |
| 独有字段      | `author`                             | `actual/forecast/previous/revised`（进 `raw_payload`） | 否    |
| 清理策略      | 按 `fetched_at` 保留期清理                 | 不清理，按月覆盖                                     | ⚠️ 见下 |

> ⚠️ **唯一需要注意的点**：现有保留期清理若按 `fetched_at` 全表扫描删除，**会误删日历数据**。实施时须在清理 SQL 中**显式排除** `scope_type='calendar'`（或改为按 `source_type IN ('rss','atom','newsnow','wscn_live_news')` 正向筛选）。

### 6.2 落表建议

**建议：落一张表（复用 `intelligence_items`）**。

| 论证角度   | 说明                                                                                    |
| ------ | ------------------------------------------------------------------------------------- |
| 契约一致性  | 该表 docstring 已明确声明「靠 `scope_type`/`scope_value` 区分多业务」，日历属于契约内扩展，不是新范式                  |
| 字段可容纳性 | 两者字段语义高度同构（标题/正文/时间/来源/重要级）；`importance` 量纲差异已通过「存原值 + 独立阈值 + 查询隔离」解决（§5.7），独有字段进 `raw_payload` 无损保留 |
| 索引已覆盖  | 现有 `ix_intel_item_scope_time` 已覆盖日历的主查询形态，无需新增索引与迁移                                     |
| 运维成本   | 不新增表 = 无 DDL 迁移、无双写、无跨表联查；回滚只需按 `scope_type` 过滤                                        |
| 仓库硬规则  | 符合 `AGENTS.md`「优先复用现有模块、配置入口、脚本和测试，**不新增平行实现**」与「默认稳定性优先于顺手优化」                        |
| 数据量    | 日历约 1000~1500 行/月，远期（3 年）约 5 万行，与该表现有量级同数量级，不构成拆分理由                                   |

**何时才需要拆表**（本期不触发，仅记录判断阈值）：

- 单表行数超过 **百万级**且日历查询出现明显退化；
- 日历需要**独立生命周期**（如按年归档、独立备份策略）；
- 需要为日历增加**大量专属列**（超过 5 个非 `raw_payload` 可承载的查询列）。

若届时拆表，建议表名为 `live_calendar_events`，主键携带 `month_key`，并保留 `source_type='wscn_calendar'` 以便数据迁移。

***

## 7. 后端接口规格（详细）

统一前缀：`/api/v1/intelligence`

### 7.1 `GET /live-calendar/tabs` — 分类 Tab 列表

| 项    | 内容                    |
| ---- | --------------------- |
| 请求方式 | GET                   |
| 入参   | 无                     |
| 出参   | `CalendarTabsResponse` |

**出参**

| 字段         | 类型               | 说明                                                    |
| ---------- | ---------------- | ----------------------------------------------------- |
| `tabs`     | `CalendarTab[]`  | Tab 列表                                                |
| `degraded` | `bool`           | 恒 `false`（Tab 为服务端常量，不依赖上游）                           |

`CalendarTab`：

| 字段       | 类型     | 示例          |
| -------- | ------ | ----------- |
| `value`  | string | `"earnings"` |
| `label`  | string | `"财报"`       |
| `order`  | int    | `2`         |

### 7.2 `GET /live-calendar/countries` — 国家字典

| 项    | 内容                         |
| ---- | -------------------------- |
| 请求方式 | GET                        |
| 入参   | 无                          |
| 出参   | `CalendarCountriesResponse` |

**出参**

| 字段         | 类型                   | 说明                     |
| ---------- | -------------------- | ---------------------- |
| `items`    | `CalendarCountry[]`  | 国家列表                   |
| `degraded` | `bool`               | 上游失败时为 `true`，`items` 为空 |

`CalendarCountry`：

| 字段             | 类型     | 上游字段             | 示例                     |
| -------------- | ------ | ---------------- | ---------------------- |
| `country_id`   | string | `country_id`     | `"US"`                 |
| `country_name` | string | `country_name`   | `"美国"`                 |
| `currency`     | string | `currency`       | `"USD"`                |
| `currency_name`| string | `currency_name`  | `"美元"`                 |
| `flag_uri`     | string | `flag_uri`       | `"https://wpimg-wscn.awtmt.com/<hash>.jpg"` |

> 服务端进程内缓存 24h；上游失败时 `degraded=true`，前端隐藏国家筛选器。

### 7.3 `GET /live-calendar` — 月度日历事件（主接口）

| 项    | 内容                       |
| ---- | ------------------------ |
| 请求方式 | GET                      |
| 出参   | `CalendarMonthResponse`  |

**入参（Query）**

| 参数            | 类型   | 必填 | 默认          | 校验                              | 说明            |
| ------------- | ---- | -- | ----------- | ------------------------------- | ------------- |
| `year`        | int  | 是  | —           | `2000 <= year <= 2100`          | 年（UTC 口径）     |
| `month`       | int  | 是  | —           | `1 <= month <= 12`              | 月             |
| `tab`         | string | 否  | `all`       | 枚举 `macro/earnings/ipo/activity/all` | 分类过滤     |
| `country_id`  | string | 否  | 空（全部）       | 长度 2 的大写字母                      | 国家过滤          |
| `importance_min` | int | 否  | `0`         | `0 <= n <= 4`                   | 最低重要级；`0` 表示含「无重要级」条目（量纲见 §5.7.2） |
| `include_economic_data` | bool | 否 | `false` | —                               | 是否包含 `FD` 经济数据 |

**时间窗换算规则**（服务端内部）

```
start = calendar.timegm((year, month, 1, 0, 0, 0))          # 当月 1 日 00:00:00 UTC
end   = calendar.timegm((year + (month==12), month%12 + 1, 1, 0, 0, 0)) - 1
```

> **说明**：上游按 UTC 秒级时间戳过滤，服务端取「整月 UTC 区间」后，由前端按**用户本地时区**归格，避免跨时区错位。

**出参**

| 字段           | 类型                | 说明                          |
| ------------ | ----------------- | --------------------------- |
| `items`      | `CalendarEvent[]` | 事件列表（按 `start_at` 升序）       |
| `server_time`| int               | 服务端秒级时间戳（前端对时）              |
| `total`      | int               | 过滤后总条数                      |
| `degraded`   | bool              | 上游失败时为 `true`（数据来自库存或为空）    |
| `source`     | string            | 固定 `"wallstreetcn"`         |

`CalendarEvent`：

| 字段               | 类型       | 说明                                        |
| ---------------- | -------- | ----------------------------------------- |
| `id`             | int      | 上游事件 ID                                   |
| `key`            | string   | 前端 React key，格式 `wscn-calendar-{id}`      |
| `start_at`       | int      | 事件时间，秒级 UTC                               |
| `title`          | string   | 事件标题（原文）                                  |
| `short_title`    | string   | **精简标题**（规则见 §11.2），日历格子直接渲染              |
| `summary`        | string   | 前瞻解读（详情面板正文）                              |
| `calendar_type`  | string   | `FE` / `FD`                               |
| `tab_keys`       | string[] | 命中的分类（如 `["ipo"]`），前端按此过滤                 |
| `importance`     | int      | 重要级，统一业务量纲 `0~4`（`0`=无，见 §5.7.2）         |
| `country`        | string   | 国家中文名                                     |
| `country_id`     | string   | 国家代码                                      |
| `flag_uri`       | string   | 国旗图 URL                                   |
| `actual`         | string   | 实际值（仅 `FD`）                               |
| `forecast`       | string   | 预测值（仅 `FD`）                               |
| `previous`       | string   | 前值（仅 `FD`）                                |
| `is_all_day`     | bool     | `public_date` 为 0 时为 `true`（全天事件）         |
| `source_uri`     | string   | 上游 `uri`，可能为空                             |

### 7.4 `POST /live-calendar/refresh` — 手动刷新

| 项    | 内容                          |
| ---- | --------------------------- |
| 请求方式 | POST                        |

**入参（Body）**

| 字段       | 类型   | 必填 | 说明                       |
| -------- | ---- | -- | ------------------------ |
| `year`   | int  | 是  | 年                        |
| `month`  | int  | 是  | 月                        |

**出参**

| 字段             | 类型       | 说明                    |
| -------------- | -------- | --------------------- |
| `fetched_count`| int      | 本次抓取并落库的事件数（去重后）     |
| `degraded`     | bool     | 上游失败时为 `true`         |
| `errors`       | string[] | 错误信息（脱敏，禁止含 token）    |

### 7.5 预留契约（本期不实现）

`GET /live-calendar/earnings?symbol=&start=&end=` 用于未来接入个股财报明细（当前公开接口对未登录态返回空，见 §2.4）。**本期仅在文档中占位，不写实现**，避免空壳接口。

***

## 8. 前端设计

### 8.1 页面布局

```
┌────────────────────────────────────────────────────────────┐
│  ◀ 上月  │  9月2026  │  10月2026  │  11月2026  │  下月 ▶   [今天] │
├────────────────────────────────────────────────────────────┤
│  [宏观] [财报] [新股] [活动] [全部]    国家▾  重要级▾  [🔄 刷新]   │
├────────────────────────────────────────────────────────────┤
│   周日    周一    周二    周三    周四    周五    周六            │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐               │
│  │     │  01 │  02 │  03 │  04 │  05 │  06 │               │
│  │     │ ●财报│ ●宏观│ ●新股│ ●活动│     │     │               │
│  │     │ ●宏观│ ●宏观│ ●财报│ ●宏观│     │     │               │
│  │     │+3更 │     │ ●活动│     │     │     │               │
│  └─────┴─────┴─────┴─────┴─────┴─────┴─────┘               │
│  ……其余 5 周……                                               │
└────────────────────────────────────────────────────────────┘
```

**交互约定**

| 元素             | 行为（FullCalendar 事件映射见括号）                                          |
| -------------- | ------------------------------------------------------------------- |
| 月份切换           | 顶部横向月份条（仿华尔街见闻），自绘（`HrsButton`），点击切换 → 更新 `initialDate` 并触发新月份拉取 |
| 分类 Tab         | 切换后**不重新请求**，前端按 `tab_keys` 过滤已加载的当月数据                          |
| 每格事件条          | 最多 **3 条**（`dayMaxEvents: 3`）；超出显示 `+N 更多`（`moreLinkText`）            |
| 点**单条**事件       | 展开该事件详情（`eventClick`）                                               |
| 点日期格**空白**区    | 展开该日全部事件面板（`dateClick`，含 `summary` 全文）                             |
| `+N 更多`        | 点击打开该日全部事件面板（`moreLinkClick` 自定义）                                  |
| 事件色阶            | 统一量纲：`0` **不渲染标记** / `1` 灰 / `2` 浅主色 / `3` 主色 / `4` 暖色高亮+加粗（§5.7.2、§8.5） |
| 今日格             | FullCalendar 内置 `--fc-today-bg-color` 主题变量高亮（§9.6）               |
| 非当前月日期         | FullCalendar dayGrid 默认置灰，且不喂事件数据（后端按选定月返回）                       |

### 8.2 前端 API 层（`apps/hrs-web/src/api/liveCalendar.ts`）

| 函数名                            | 入参                                     | 出参                                    | 说明                       |
| ------------------------------ | -------------------------------------- | ------------------------------------- | ------------------------ |
| `getLiveCalendarTabs()`        | 无                                      | `{ tabs: CalendarTabDef[]; degraded: boolean }` | 拉取 Tab 列表（后端驱动）  |
| `getLiveCalendarCountries()`   | 无                                      | `{ items: CalendarCountryDef[]; degraded: boolean }` | 拉取国家字典           |
| `getLiveCalendarMonth(params)` | `{ year, month, tab?, countryId?, importanceMin?, includeEconomicData? }` | `{ items: LiveCalendarEventDef[]; total: number; serverTime: number; degraded: boolean; source: string }` | 拉取整月事件 |
| `refreshLiveCalendar(params)`  | `{ year, month }`                      | `{ fetchedCount: number; degraded: boolean; errors: string[] }` | 触发服务端抓取   |

**约定**（对齐现有 `liveNews.ts`）：

- 文件内定义 `Raw*` 接口描述后端 snake_case 结构，导出前统一 `normalize*()` 转 camelCase，**避免后端字段风格泄漏到业务层**；
- 空值参数不发给后端；
- 支持透传 `AbortSignal`。

### 8.3 前端 Hook 层（`apps/hrs-web/src/hooks/useLiveCalendar.ts`）

| Hook                                    | 入参                                              | 返回                                                                                                                     | 职责                                                |
| --------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `useLiveCalendarTabs()`                 | 无                                               | `{ tabs, degraded, loading, error }`                                                                                    | 拉 Tab 列表，挂载时请求一次                                  |
| `useLiveCalendarCountries()`            | 无                                               | `{ items, degraded, loading, error }`                                                                                   | 拉国家字典，挂载时请求一次                                     |
| `useLiveCalendarMonth(year, month, options)` | `year: number`；`month: number`；`options?: { tab?, countryId?, importanceMin?, includeEconomicData? }` | `{ events, eventsByDay, loading, refreshing, error, degraded, total, refresh }` | 按月拉取 + 按天归格 + 客户端过滤 |

**`useLiveCalendarMonth` 返回字段明细**

| 字段            | 类型                          | 说明                                       |
| ------------- | --------------------------- | ---------------------------------------- |
| `events`      | `LiveCalendarEventDef[]`    | 当前过滤条件下的平铺事件                             |
| `eventsByDay` | `Map<string, LiveCalendarEventDef[]>` | 按 `YYYY-MM-DD`（本地时区）归格，`LiveCalendarGrid` 直接消费 |
| `loading`     | boolean                     | 首次加载中                                    |
| `refreshing`  | boolean                     | 手动刷新中（不遮挡内容）                             |
| `error`       | string \| null               | 错误信息                                     |
| `degraded`    | boolean                     | 上游降级标记                                   |
| `total`       | number                      | 总条数                                      |
| `refresh`     | `() => Promise<void>`       | 先触发服务端抓取，再重拉列表（对齐 `useLiveNews.refresh`） |

**实现要点**（沿用 `useLiveNews` 已验证的约定）

1. **不轮询**：日历为低频数据，`autoRefresh` 默认关闭；仅提供手动 `refresh`。
2. **月份/过滤条件变化**时用 `AbortController` 中止在途请求，避免竞态。
3. `tab` / `countryId` / `importanceMin` 变化**不重新请求整月**，在 `useMemo` 中对已加载数据做客户端过滤（因为整月数据已在内存）。
4. 按天归格在前端用**本地时区**构造 `YYYY-MM-DD` key（手写格式化，勿用 `toISOString()` 避免 UTC 错位）；喂给 FullCalendar 的事件 `start`：全天事件用 `YYYY-MM-DD`、有时刻事件用 `YYYY-MM-DDTHH:mm`（FullCalendar 对无时区串按本地时区解析，与本地上屏一致）。**无需引入任何日期库**。

### 8.4 前端类型（`apps/hrs-web/src/types/liveCalendar.ts`）

> 命名遵循 `.conventions/frontend/TYPE_NAMING.md`：**描述数据契约 → `Def`**（可脱离组件独立存在，来自 API / 配置）；组件挂载接口才用 `Props`（见 §9.4）。

```ts
import type { ImportanceLevel } from '../constants/newsImportance';

/** Tab 值 union（不含 Def：是取值枚举而非数据结构） */
export type CalendarTabValue = 'macro' | 'earnings' | 'ipo' | 'activity' | 'all';

/** Tab 定义（后端 `/live-calendar/tabs` 返回的数据契约） */
export interface CalendarTabDef {
  value: CalendarTabValue;
  label: string;
  order: number;
}

/** 国家字典条目（`/live-calendar/countries` 数据契约） */
export interface CalendarCountryDef {
  countryId: string;
  countryName: string;
  currency: string;
  currencyName: string;
  flagUri: string;
}

/** 日历事件（`/live-calendar` 数据契约；§7.3 CalendarEvent 的 camelCase 归一化） */
export interface LiveCalendarEventDef {
  id: number;
  key: string;             // 上游去重键
  startAt: number;         // 秒级 UTC
  title: string;
  shortTitle: string;      // 精简标题，格子直接渲染（§11.2）
  summary: string;
  calendarType: 'FE' | 'FD';
  tabKeys: CalendarTabValue[];
  /** 统一业务量纲：0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要（§5.7.2） */
  importance: ImportanceLevel;
  country: string;
  countryId: string;
  flagUri: string;
  actual: string;
  forecast: string;
  previous: string;
  isAllDay: boolean;
  sourceUri: string;
}

/** 月度查询参数（`/live-calendar?year=&month=` 数据契约） */
export interface LiveCalendarQueryDef {
  year: number;
  month: number;
  tab?: CalendarTabValue;
  countryId?: string;
  importanceMin?: number;
  includeEconomicData?: boolean;
}
```

> **约定**：API 层（`api/liveCalendar.ts`）内部保留 `Raw*` snake_case 结构，导出前 `normalize*()` 转上述 camelCase `Def`，与 `liveNews.ts` 风格一致。

**类型 ↔ 后端对照**

| 前端 `Def` | 后端 schema | 备注 |
| --- | --- | --- |
| `CalendarTabDef` | `CalendarTab` | 列表项 |
| `CalendarCountryDef` | `CalendarCountry` | 列表项 |
| `LiveCalendarEventDef` | `CalendarEvent` | 单个事件 |
| `LiveCalendarQueryDef` | 查询参数 | 非后端出参 |

### 8.5 前端共享常量：重要度语义（`apps/hrs-web/src/constants/newsImportance.ts`）

> **抽象时机**：重要度语义此前仅有快讯一个使用方，本期日历成为**第二个使用方**，符合「第二次出现才抽象」的时机，故抽出共享常量，避免两套语义漂移。

```ts
/** 重要级，统一业务量纲（与后端 §5.7.2 一一对应） */
export type ImportanceLevel = 0 | 1 | 2 | 3 | 4;

export const IMPORTANCE = {
  NONE: 0,        // 无（数据源未提供重要度）
  NORMAL: 1,      // 普通
  MINOR: 2,       // 较重要
  IMPORTANT: 3,   // 重要
  CRITICAL: 4,    // 非常重要
} as const;

/** 文案映射；0 不展示文案 */
export const IMPORTANCE_LABELS: Record<ImportanceLevel, string> = {
  0: '', 1: '普通', 2: '较重要', 3: '重要', 4: '非常重要',
};

/** 色阶映射（快讯竖线 / 日历格子色点共用）；0 返回 null 表示不渲染 */
export const IMPORTANCE_COLORS: Record<ImportanceLevel, string | null> = {
  0: null, 1: 'text-secondary-text', 2: 'text-cyan/70',
  3: 'text-cyan', 4: 'text-warning font-semibold',
};

/** 「重要」判定阈值，与后端 wscn_*_important_score 默认值对齐 */
export const IMPORTANT_THRESHOLD: ImportanceLevel = 3;

/** 是否重要 */
export function isImportant(level: number | null | undefined): boolean {
  return typeof level === 'number' && level >= IMPORTANT_THRESHOLD;
}
```

**消费方**

| 模块   | 用途                                                            |
| ---- | ------------------------------------------------------------- |
| 快讯   | `newsCard.tsx` 的重要竖线 / 「重要」标签；「只看重要的」筛选                       |
| 日历   | `LiveCalendarGrid` 的事件色点；`importance_min` 筛选                  |

**快讯侧的同步改动**

| 文件                                    | 改动                                                                                             |
| ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `types/liveNews.ts:26`                | 注释由 `1=普通 / 2=重要 / 3=非常重要` 更新为 `0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要`                           |
| `types/liveNews.ts`                   | `score: number` → `score: ImportanceLevel`（复用共享类型）                                            |
| `api/liveNews.ts:73`                  | `score: raw.score ?? 1` → `score: raw.score ?? 0`（**兜底值由 1 改为 0**，与「缺失=无」语义一致）                    |
| `components/common/Card/newsCard.tsx` | 改用 `isImportant(item.important ?? item.score)`；`0` 不渲染重要度标记                                    |

> **后端改造对前端的功能影响为零**：快讯页面实际只消费 `important` 布尔值（`newsCard.tsx:46`：`const isImportant = showImportant && item.important;`），且归一化后 `important` 的判定结果**与改造前完全一致**（阈值同步 2→3），故快讯 UI 行为不变。上述改动仅为语义对齐与共享复用。

***

## 9. 日历控件选型与封装方案

### 9.1 决策演进记录（防止返工）

本节经历了三轮评审，最终结论是 **FullCalendar v6 二次封装**。演进记录保留，避免后人重复评估：

| 轮次 | 候选 | 否决理由 | 结论 |
| --- | --- | --- | --- |
| 1 | 自实现 + `date-fns` | 需求其实是"每格多行文字标题 + 溢出折叠"的**标准事件月历形态**，自实现属重复造轮子，且可访问性/本地化需手写 | 放弃 |
| 2 | HeroUI 内置 `Calendar` | **语义模型不符**（见 §9.2），选型时误判其能力 | 放弃 |
| 3 | **FullCalendar v6** | — | ✅ **最终选用** |

### 9.2 否决 HeroUI `Calendar` 的论证（为何选型控件而非选择器）

HeroUI 3.2.4 确内置 `calendar` 复合组件，但它是 react-aria 系的**日期选择器**（与 `DatePicker` 同族），语义假设与本需求冲突：

| 维度 | HeroUI Calendar 的设计假设 | 本需求 | 冲突 |
| --- | --- | --- | --- |
| 产品定位 | 单值/范围**选择器**，表单控件 | 平铺**展示**的事件月历 | 定位错位 |
| 格内内容 | 只有「日期数字」一个语义单元 | 日期 + N 条消息标题 + 溢出折叠 | 塞内容破坏 grid 语义 |
| 键盘可达性 | 格内仅 1 个可聚焦点（日期） | 每条消息需逐条可达/可点 | 格内文字对键盘/读屏不可达 |
| 交互语义 | 点击格 = 选中日期（写入 value） | 点空白 = 展开该日详情 | 需 hack 拦截，与选中态冲突 |
| 格子尺寸 | 高 ~32-44px（放下日期数字即可） | 需 ~100px 放 3 行文字 | 7 列等高撑爆版面 |
| 溢出处理 | 无「+N 更多」概念 | 每格最多 3 条 + `+N` 折叠 | 完全自造 |

**结论**：在 react-aria Calendar 之上做"事件月历"是逆向使用——语义层不可调和，且得到的可访问性比自实现更差（键盘只能摸到日期、摸不到格内消息）。**否决。**

### 9.3 FullCalendar 选型（最终）

**React 19 兼容性已实测确认**（peerDependencies，2026-09-02）：

| 候选 | 版本 | React peer | 「每格 N 条 + more」 | 生态 | 结论 |
| --- | --- | --- | --- | --- | --- |
| **FullCalendar** | `@fullcalendar/react@6.1.21` | ✅ `^17\|\|^18\|\|^19` | ✅ **dayGrid 原生内置** | 最大（3.0M 下载/月） | ✅ **选用** |
| Schedule-X | `@schedule-x/react@4.1.0` | ✅ `^16.7\|\|^17\|\|^18\|\|^19` | 需自行实现折叠 | 较小 | 备选 |
| react-big-calendar | — | 需核实 | 月视图弱（周/日为主场） | 中 | ❌ |
| HeroUI Calendar | 内置 | ✅ | ❌ | — | ❌（§9.2） |

**需求逐条映射**：

| 需求 | FullCalendar 能力 |
| --- | --- |
| 每格最多 3 条 + 溢出折叠 | `dayMaxEvents: 3` **内置**（dayGrid 月视图设计目标） |
| 溢出处「+N 更多」 | `moreLinkText` / `moreLinkClick` **原生**，点击可自定义打开该日面板 |
| 点单条消息看详情 | `eventClick`（命中单条事件） |
| 点格子空白看该日全部 | `dateClick`（需 `interaction` 插件，命中空白区） |
| 消息前重要级色点 / 国家标签 | `eventContent` 渲染任意 JSX，样式走项目 `IMPORTANCE_COLORS`（§8.5） |
| 中文本地化 / 周一开头 | `locale: 'zh-cn'`、`firstDay: 1` 内置 |
| 事件按天 | `start: 'YYYY-MM-DD'`（全天）或带时刻 ISO，事件数组直喂 |
| 页面自适应 | `height: '100%'` 占满容器 |

> **为何用 v6 而非 v7**（2026-09-03 复核，结论：维持 v6.1.21）：FullCalendar v7 已发布 `core` / `react` 正式版（7.0.2），但 `daygrid` / `interaction` 这两个**本期必需**的插件至今没有 7.x 正式版。
>
> **版本时间线（决策依据）**
>
> | 日期 | 事件 |
> | --- | --- |
> | 2025-02-21 | `daygrid` / `interaction` 发布 **7.0.0-rc.0** ← 此后 **18 个月零更新** |
> | 2026-06-18 | **v6.1.21 发布**（v6 线终点；官方在推 v7 的前一天仍专门维护） |
> | 2026-06-19 | `core` / `react` 发布 **v7.0.0 正式版** |
> | 2026-07-24 | `core` / `react` 发布 **7.0.2**（当前 `latest`） |
>
> **三条否决理由**
>
> 1. **插件 RC 已停更 18 个月**：`daygrid@7.0.0-rc.0` / `interaction@7.0.0-rc.0` 停留在 2025-02-21，而 `core` 同期已迭代 `rc.1→rc.2→rc.3→7.0.0→7.0.1→7.0.2` 共 6 版，期间含 v7.0.0 的 BREAKING 变更（新增 `temporal-polyfill` peer 依赖）。
> 2. **硬依赖冲突**：`daygrid@7.0.0-rc.0` 硬依赖 `@fullcalendar/core@7.0.0-rc.0`（**精确版本**，非范围），与 `core@7.0.2` 冲突；混搭需 `--legacy-peer-deps` 且内部 API 错配风险高。
> 3. **v6.1.21 并非过时版本**：它发布于 v7 正式版**前一天**（2026-06-18），是官方为插件空窗期维护的收官版；对 `daygrid` / `interaction` 而言 npm `latest` 至今仍是 `6.1.21`，即本项目已在用官方认可的最新稳定版。其 peer 已声明支持 React 19（`^17||^18||^19`）。
>
> **升级触发条件**：待 `daygrid` / `interaction` 发布 7.x 正式版（即 `npm view @fullcalendar/daygrid dist-tags` 的 `latest` 变为 7.x）后重新评估。届时改动面仅限：① `package.json` 四个包版本号；② 加装 `temporal-polyfill@^1.0.1`（v7 BREAKING 新增必需 peer 依赖）；③ `LiveCalendarGrid.tsx` 适配 v7 API 变化。因封装层已用 `React.ComponentProps<typeof FullCalendar>` 完整透传、页面层不直接依赖 FullCalendar API，**业务代码与样式层无需改动**。

**前端依赖清单（`apps/hrs-web/package.json`）**

| 包 | 版本 | 用途 |
| --- | --- | --- |
| `@fullcalendar/react` | `^6.1.21` | React 封装层 |
| `@fullcalendar/core` | `^6.1.21` | 核心 |
| `@fullcalendar/daygrid` | `^6.1.21` | 月视图（本期唯一视图） |
| `@fullcalendar/interaction` | `^6.1.21` | `dateClick` / `eventClick` |

**明确不引入**：`date-fns` / `dayjs`（FullCalendar 自带日期体系，归格与格式化均手写，见 §8.3）；`@internationalized/date`（随 HeroUI Calendar 方案一并否决，不声明）；`temporal-polyfill`（仅 v7 peer 需要，v6 无需）。

### 9.4 二次封装：遵循 `.conventions/frontend/COMPONENTS.md`

**规范落点**

| COMPONENTS.md 条款 | 落地 |
| --- | --- |
| 组件命名大写 / 命名导出 / 禁默认导出 | `LiveCalendarGrid` / `LiveCalendarTabs`，`index.ts` 内 `export * from './LiveCalendarGrid'` |
| 目录 | 非 HeroUI 封装、属业务组件 → `src/components/common/<组件名>/`（basic=HeroUI 二次封装，common=组件组合/三方封装） |
| 完整透传原生 Props | `React.ComponentProps<typeof FullCalendar>` 继承 + TS 交叉类型扩展业务字段 |
| 解构业务属性、剩余透传 | 同 `HrsButton.tsx` 模板 |
| 外部 className 优先级最高 | `cn(bizClass, className)`，`className` 收尾 |
| 禁止自定义样式文件 / 禁 `!important` | 样式走 Tailwind 令牌 + CSS 变量作用域（§9.6），**不新建任何 CSS/SCSS** |
| 头部注释 + 代码注释 | 遵守 |

**目录结构**

```
src/components/common/LiveCalendarGrid/
├── LiveCalendarGrid.tsx
└── index.ts                 # export * from './LiveCalendarGrid'
```

**组件源码骨架**（供实施参照）

```tsx
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import zhCnLocale from '@fullcalendar/core/locales/zh-cn';
import { cn } from '../../../utils/cn';
import type { LiveCalendarEventDef } from '../../../types/liveCalendar';

/** 业务扩展属性：数据契约经转化喂给 FullCalendar，业务字段仅以下三个 */
export type LiveCalendarGridProps = React.ComponentProps<typeof FullCalendar> & {
  /** 按天归格的事件（key = YYYY-MM-DD） */
  eventsByDay: Map<string, LiveCalendarEventDef[]>;
  /** 点日期空白区 → 打开该日全部详情 */
  onSelectDay: (day: string) => void;
  /** 点单条事件 → 打开该事件详情 */
  onSelectEvent: (event: LiveCalendarEventDef) => void;
};

/** FullCalendar v6 二次封装：月历事件展示，dayMaxEvents 折叠 + 主题变量作用域 */
export const LiveCalendarGrid = ({
  eventsByDay,
  onSelectDay,
  onSelectEvent,
  className,
  ...props
}: LiveCalendarGridProps) => (
  // 主题作用域 div：CSS 变量层把项目令牌映射为 FullCalendar 的 --fc-*（见 §9.6），不新建样式文件
  <div className={cn('h-full [&_.fc]:h-full', className)}>
    <FullCalendar
      plugins={[dayGridPlugin, interactionPlugin]}
      initialView="dayGridMonth"
      locale={zhCnLocale}
      firstDay={1}
      dayMaxEvents={3}
      height="100%"
      events={toFullCalendarEvents(eventsByDay)}
      eventContent={(arg) => <CalendarEventContent arg={arg} />}
      dateClick={(info) => onSelectDay(info.dateStr)}
      eventClick={(info) => onSelectEvent(info.event.extendedProps.eventDef)}
      {...props}
    />
  </div>
);
```

**组件 Props / 类型命名（按 TYPE_NAMING.md）**

| 命名 | 归类 | 理由 |
| --- | --- | --- |
| `LiveCalendarEventDef` | `Def` | 描述「一条事件的数据契约」，可脱离组件独立存在（来自 API），被组件解析渲染 |
| `LiveCalendarGridProps` | `Props` | 组件挂载接口，含 `className` / 回调 / render 透传 |

### 9.5 `LiveCalendarTabs` 封装（HeroUI `Tabs`）

基于 HeroUI `Tabs` 薄封装：主题对齐项目主色 + Tab 由 `useLiveCalendarTabs()` 后端驱动。

```ts
// src/components/common/LiveCalendarTabs/
import { Tabs } from '@heroui/react';
export type LiveCalendarTabsProps = React.ComponentProps<typeof Tabs> & {
  tabs: CalendarTabDef[];
  activeTab: CalendarTabValue;
  onChangeTab: (tab: CalendarTabValue) => void;
  /** 各 Tab 事件计数徽标 */
  counts?: Record<string, number>;
};
```

> **不新建 `basic/TabNav.tsx`**：本期只有日历页需要该形态 Tab，放 `common/`；出现第二个使用方再上提（「不提前抽象」）。

### 9.6 主题与样式约定（约束落地）

> 原则：**Tailwind 原生样式 + tailwind.config 令牌为唯一样式来源；不新增 CSS/SCSS 文件；不使用 `global.scss` 定义类。**

**已核实的样式事实**

1. `index.css` 经 `@config "../../tailwind.config.js"` 使 v4 加载 v3 配置——config 语义色板**全部生效**；
2. `global.scss`（2120 行）类全部是业务专属（`chat-*` / `backtest-*` / `dashboard-card` 等），**无任何通用组件类**、与日历零交集，弃用零成本；
3. `hrs-global.css` 已被 `index.css:7` 注释，废弃。

**可用令牌摘录（日历直接使用）**

| 类别 | 令牌 → 工具类 |
| --- | --- |
| 背景 | `bg-base` / `bg-elevated` / `bg-card` / `bg-subtle` / `hover:bg-subtle` |
| 文字 | `text-foreground`（含 `-dim/-soft/-faint`）/ `text-secondary-text` / `text-muted-text` / `text-cyan` |
| 语义色 | `text-success` / `text-warning` / `text-danger`（事件色阶，配合 §8.5） |
| 边框 | `border` / `border-dim` / `border-cyan` |
| 渐变 | `bg-gradient-cyan` / `bg-gradient-purple-cyan` |
| 阴影 | `shadow-soft-card` / `shadow-glow-cyan` |
| 圆角 | `rounded-sm/md/lg` / `rounded-xl` |
| 字号 | `text-xxs`(10) / `xs`(12) / `sm`(14) |
| 动画 | `animate-fade-in` / `animate-slide-up` / `animate-float-in` |

**FullCalendar 主题映射（唯一必要的变量层）**

FullCalendar 内部结构无法用 Tailwind 类逐点控制，需在其 CSS 变量层（`--fc-*`）映射项目令牌。做法：在组件根 div 上用 **Tailwind arbitrary properties** 声明一套 `--fc-*`，值引用项目令牌——**不新建任何样式文件**：

```tsx
<div
  className={cn(
    'h-full [&_.fc]:h-full',
    // FullCalendar 主题变量 → 项目令牌（经 config hsl(var(--x))，随 .dark 自动联动）
    '[--fc-border-color:theme(colors.border.DEFAULT)]',
    '[--fc-page-bg-color:theme(colors.elevated)]',
    '[--fc-neutral-bg-color:theme(colors.subtle)]',
    '[--fc-today-bg-color:theme(colors.primary/0.06)]',
    '[--fc-button-text-color:theme(colors.primary)]',
    '[--fc-button-bg-color:theme(colors.base)]',
    '[--fc-event-bg-color:theme(colors.base)]',
    '[--fc-event-text-color:theme(colors.foreground)]',
    className,
  )}
>
```

> 具体 `--fc-*` 变量名以 FullCalendar v6 实际 CSS 为准，实施时对照其 `daygrid.css` 校准；映射值一律取 config 令牌，**禁止写死色值**。

**两条硬性约束（写入本模块约定）**

1. 新增组件**禁止定义全局 CSS 类**（不加 `.live-calendar-*` 进任何 scss/css）；状态样式用 Tailwind 条件类或 `data-*`；
2. **禁止在组件内直接裸写 `var(--x)`**——必须经 tailwind.config 已映射的语义令牌（`bg-*`/`text-*`/`border-*`）或上述 `--fc-*` 主题变量层。

***

## 10. 接口 / 前端 API / Hook 三方对照表

| 功能说明        | 三方接口（上游）                                                    | 后端 HTTP 接口                                        | 后端分层（Fetcher / Service / Repo）                                                                 | 前端 API 函数                     | 前端 Hook                                    |
| ----------- | ----------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------- | ------------------------------------------ |
| 拉取分类 Tab 列表 | —（服务端常量，不依赖上游）                                              | `GET /api/v1/intelligence/live-calendar/tabs`     | `CalendarService.list_tabs()`（纯常量返回）                                                            | `getLiveCalendarTabs()`       | `useLiveCalendarTabs()`                    |
| 拉取国家字典      | `GET api-one-wscn.awtmt.com/apiv1/finance/countries`        | `GET /api/v1/intelligence/live-calendar/countries`| `WallstreetcnCalendarFetcher.fetch_countries()` → `CalendarService.list_countries()`（内存缓存 24h） | `getLiveCalendarCountries()`  | `useLiveCalendarCountries()`               |
| 拉取月度日历事件    | `GET api-one-wscn.awtmt.com/apiv1/finance/macrodatas?start=&end=` | `GET /api/v1/intelligence/live-calendar?year=&month=` | `fetcher.fetch_range()` → `Service.get_month()`（打标） → `Repo.upsert_calendar_events()` + `Repo.list_calendar_events()` | `getLiveCalendarMonth(params)`| `useLiveCalendarMonth(year, month, opts)`  |
| 手动刷新当月      | 同 ↑（强制回源）                                                    | `POST /api/v1/intelligence/live-calendar/refresh` | `CalendarService.refresh()`（跳过缓存直连上游）                                                           | `refreshLiveCalendar(params)` | `useLiveCalendarMonth().refresh()`         |
| 个股财报明细（预留）  | 待定（akshare / yahoo / tushare）                                | `GET /live-calendar/earnings`（**本期不实现**）          | —                                                                                              | —                             | —                                          |

***

## 11. 时间维度与精简标题规则

### 11.1 时间处理

| 环节        | 规则                                                                                       |
| --------- | ---------------------------------------------------------------------------------------- |
| 上游 → 后端   | `public_date` 为**秒级 UTC**；为 `0` 时表示全天事件，取该日 `00:00:00 UTC` 并置 `is_all_day=true`           |
| 后端 → 前端   | `start_at` 保持秒级 UTC 原样下发，**不做时区转换**                                                       |
| 前端归格      | 前端按**用户本地时区**把 `start_at` 转 `YYYY-MM-DD` key（本地手写格式化，勿用 `toISOString()`）；FullCalendar 事件 `start` 用同 key 或带时刻串（按本地解析，与归格一致） |
| 展示        | 全天事件只显示日期；有时刻的事件显示 `HH:mm`（本地时区）                                                          |
| 跨时区注意     | 后端按「整月 UTC 区间」拉取；前端只把「落在选定月（本地）内」的事件喂给 FullCalendar，格内事件由 dayGrid 按 `start` 日期定位，边界自然正确 |

### 11.2 精简标题规则（日历格子）

日历格子宽度有限，`short_title` 由服务端生成（保证前后端一致），规则：

| 步骤   | 规则                                                                        | 示例                                                                 |
| ---- | ------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 1    | 去除 `foresight` 前缀 `前瞻 \| `                                                | —                                                                  |
| 2    | 去除括号内的补充说明（中文全角括号）                                                        | `2026世界动力电池大会9/3-9/4日举行` → `2026世界动力电池大会`                          |
| 3    | 按 `、` `/` `：` 取第一段                                                         | `太阳诱电上调MLCC价格/三菱刀具调价` → `太阳诱电上调MLCC价格`                             |
| 4    | 去除常见冗余后缀：`将于…举行` / `将举行` / `预计将公布` / `正式生效` 等                              | `长鑫科技上市后首份半年报预计将公布` → `长鑫科技上市后首份半年报`                               |
| 5    | 截断至 **18 个中文字符**（英文按 0.5 宽度折算），超出加 `…`                                     | `智谱等33只中国股票正式纳入MSCI指数`（18 字，保留）                                    |
| 6    | 截断失败（全英文长串）时按字节截断至 36 字节                                                   | `Meta Connect 2026`（保留）                                            |

> 详情面板与 hover tooltip 展示**完整 `title`**，不受此规则影响。

***

## 12. 降级策略

与 live-news 的「官方源 → NewsNow」不同，日历**无等价兜底源**（NewsNow 无日历品类）。降级策略如下：

| 场景              | 行为                                                                                     |
| --------------- | -------------------------------------------------------------------------------------- |
| 上游 `macrodatas` 失败 | ① 读库存（该月已落库数据）返回，`degraded=true`；② 库存无数据则返回空 `items` + `degraded=true`；**不抛 5xx** |
| 上游 `countries` 失败  | `degraded=true` + 空 `items`，前端**隐藏国家筛选器**                                              |
| 上游返回非 `20000`    | 同上，并记录脱敏错误日志（禁止落库含 token 的上游原文）                                                       |
| 上游超时             | `timeout` 默认 8s（对齐 `wallstreetcn_live_news.py`），超时即走库存降级                                |
| 单条解析失败          | 跳过该条，不影响整批；错误计数计入 `refresh` 的 `errors`                                                 |
| 总开关关闭           | `WALLSTREETCN_CALENDAR_ENABLED=false` 时，接口返回空列表 + `degraded=true`，前端展示「功能未启用」空态         |

**前端降级呈现**

- `degraded=true` 时在页面顶部展示轻量提示条（不遮挡内容）：`数据可能不是最新，来自本地缓存`；
- 隐藏依赖上游的筛选器（国家筛选）；
- 保留已加载数据的完整交互能力。

***

## 13. 边界条件与空态处理

| 场景                        | 处理                                                       |
| ------------------------- | -------------------------------------------------------- |
| 某月无任何事件                   | 日历网格正常渲染，格子为空；页面中部展示空态插画 + `本月暂无日历事件`                   |
| 某 Tab 下无事件                | 网格空；提示 `当前分类下本月暂无事件，试试「全部」`                             |
| `importance_min` 过滤后为空     | 提示 `没有符合重要级条件的事件，试试降低筛选条件`                              |
| `public_date = 0`（全天事件）   | 归入该日，排序时排在有时刻事件**之前**，标 `全天`                             |
| `title` 为空                 | 回退 `foresight` 首行截断 300 字；仍为空则用 `（无标题）`                  |
| 一条事件命中多个 Tab              | `tab_keys` 为多值，任一命中即展示；落库拆多行（§5.4）                       |
| 请求上一年 / 下一年               | `year` 校验 `2000~2100`，越界返回 422                           |
| 未来月份                      | 允许查询（华尔街见闻有前瞻数据），无数据时走空态                                 |
| 跨月边界事件                    | 前端按本地时区归格后过滤非本月（§11.1）                                   |
| 快速连续切换月份                  | `AbortController` 中止在途请求，仅保留最后一次                          |
| `uri` 为空                   | 详情面板不展示「查看原文」链接                                          |
| 上游 `importance` 缺失/非法     | 填 **`0`**（无，**不是** `1`）；取值范围钳制到 `0~4`；参与 `importance_min` 过滤时按实际值比较 |

***

## 14. 配置与开关

新增配置项（同步 `.env.example` 与本文档）：

| 配置项                              | 默认值                                  | 说明                          |
| -------------------------------- | ------------------------------------ | --------------------------- |
| `WALLSTREETCN_CALENDAR_ENABLED`  | `true`                               | 总开关；关闭时接口降级为空列表             |
| `WALLSTREETCN_CALENDAR_BASE_URL` | `https://api-one-wscn.awtmt.com`     | 上游地址（不写死在代码里）               |
| `WALLSTREETCN_CALENDAR_TIMEOUT`  | `8`                                  | 单请求超时（秒），对齐快讯 fetcher       |
| `WALLSTREETCN_CALENDAR_REFERER`  | `https://wallstreetcn.com/calendar`  | 上游必需 `Referer`              |
| `CALENDAR_COUNTRIES_CACHE_TTL`   | `86400`                              | 国家字典内存缓存时长（秒）               |
| `WALLSTREETCN_CALENDAR_IMPORTANT_SCORE` | `3`                          | 日历「重要」阈值。量纲统一后与快讯取值相同（均为 `3`），但**保留独立配置项**以便各自调整（见 §5.7.5）      |
| `WSCN_LIVE_NEWS_IMPORTANT_SCORE` | `2` → **`3`**              | **存量配置项改造**：快讯阈值随量纲归一化同步上调，保证「重要」判定结果与改造前一致（见 §5.7.5、§5.7.7）    |

> **不新增**开关项：分类打标规则为代码常量（§3.2），不做配置化——避免「配置驱动业务语义」的复杂度，规则变更走代码发布。

***

## 15. 实施计划

| 阶段        | 内容                                                                                                   | 产出                                                          | 验证                                       |
| --------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------- |
| **P0 量纲改造** | 快讯 `importance` 归一化（§5.7.7 改动点 1/2/3）+ 存量迁移函数（改动点 4）+ 阈值上调（改动点 5）                                     | 快讯功能行为不变，全表 `importance` 统一为业务量纲                             | §5.7.9 全部 6 条回归测试，尤其**幂等性**与「迁移前后 important 结果一致」 |
| **P1 数据层** | `data_provider/wallstreetcn_calendar.py`（fetcher + 解析器）                                              | 可独立调用 `fetch_countries()` / `fetch_range()`                 | `tests/test_live_calendar.py` 解析单测（不触网）  |
| **P2 服务层** | `CalendarService`（打标 + 时间窗换算 + 降级）+ `IntelligenceRepo` 两个新方法                                        | 服务层可落库、可出库                                                  | service 集成测（mock fetcher，不触网）            |
| **P3 接口层** | 4 个路由 + Pydantic 模型                                                                                 | 接口可访问                                                       | `curl` 实测 + `python -m pytest -m "not network"` |
| **P4 前端底座**| types(`*Def`) / api / hooks / i18n / 路由 / 侧边栏 + 依赖安装（FullCalendar 系列）                                | 页面可访问，数据可拉取                                                 | `npm run lint`                           |
| **P5 日历组件**| `LiveCalendarGrid`（FullCalendar 封装，§9.4）+ `LiveCalendarTabs` + `importance.ts` 共享常量（§8.5） + 详情面板             | 完整交互、深色/浅色主题一致                                               | `npm run build` + 深/浅主题冒烟             |
| **P6 文档**  | `docs/Live-calendar.md`（本文）+ `docs/CHANGELOG.md` 一行                                                | —                                                           | 人工核对命令与文件名                               |

**验证矩阵**（按 `AGENTS.md` §6）

| 改动面    | 必跑                                                                       |
| ------ | ------------------------------------------------------------------------ |
| Python 后端 | `python -m py_compile <changed_files>` + `python -m pytest -m "not network"` |
| Web 前端 | `cd apps/hrs-web && npm ci && npm run lint && npm run build`               |

***

## 16. 风险、合规与回滚

### 16.1 风险与应对

| 风险                                       | 影响          | 应对                                                                 |
| ---------------------------------------- | ----------- | ------------------------------------------------------------------ |
| **上游接口无 SLA**，路径/参数/字段可能变更               | 功能整体失效      | fetcher 层集中封装上游细节；`parse_payload` 对字段缺失做容错；预留 `BASE_URL` 配置可切换      |
| **分类依赖中文关键字正则**，上游标题措辞变化会漏标              | 分类不准        | 规则集中在一个常量（§3.2）；`all` Tab 兜底展示全部事件，漏标不影响可见性                        |
| **存量迁移未幂等导致二次映射** | 快讯重要级错乱 | 迁移前后取值集合有交集（前 `{1,2,3}` / 后 `{0,1,3,4}`），**无法从数据形态判断**是否已迁移；必须用 `DatabaseSchemaMigration` 标记式幂等（§5.7.6）+「连跑两次结果一致」断言 |
| **迁移 SQL 误伤其他业务** | 日历/通用资讯数据被改 | `WHERE scope_type = 'channel'` 不可省略；补「影响行数 == channel 总行数」断言            |
| **迁移 SQL 用 `=` 判断 NULL** | NULL 分支永不匹配，降级源仍为 NULL | 必须写 `WHEN importance IS NULL`，不可写 `CASE importance WHEN NULL`（§5.7.6）    |
| **只改阈值不迁移存量** | 快讯重要率从 31% **暴跌至 2%** | 迁移与阈值调整**必须同批次发布**，不可拆分（§5.7.6）                                          |
| **存量库 `importance` 列缺失** | 日历重要级全退化为 `NULL` | 该列为后补列，上线前确认目标库已补齐；若日志出现「补充 importance 列失败」需先人工修复（§5.7）                  |
| **FullCalendar 主题变量版本漂移** | 深/浅色主题错位 | `--fc-*` 变量名随 FullCalendar 大版本可能变更；全部映射收敛在 `LiveCalendarGrid` 主题变量层（§9.6），升级时只改该处并做深/浅色冒烟 |
| **保留期清理误删日历数据**（§6.1 ⚠️）                | 历史月份数据丢失    | 清理 SQL 显式排除 `scope_type='calendar'`；上线前补一条集成测断言                     |
| **`FD` 数据量占比高**（481/569）                 | 日历格子被淹没     | 默认不展示 `FD`，通过 `include_economic_data` 显式开启                          |
| **个股财报明细缺失**（蔚来/Ciena/博通 等）             | 与参考图存在能力差   | 文档明示能力边界；二期通过 `akshare` / `yahoo` / `tushare` 接入（§7.5 预留）           |
| **本地代理环境（Clash fake-ip）SSRF 误拦**        | 抓取失败        | 复用快讯已落地的方案：对受信任内置源放行 `198.18.0.0/15` 网段                             |
| **跨时区归格错位**                              | 事件显示在错误日期   | 后端统一下发 UTC 秒级；前端按本地时区归格并过滤非本月（§11.1）                                |

### 16.2 合规

- 上游为华尔街见闻**前端内部接口**（无官方文档，抓包逆向获得），仅用于**个人/内部研究**，须遵守其服务条款；
- 请求须带真实 `User-Agent` + `Referer`，**不做高频轮询**（日历为低频拉取，天然合规）；
- 落库数据**不对外二次分发**；
- 错误日志**脱敏**，禁止记录含 token/密钥的上游原文。

### 16.3 回滚方式

| 范围       | 回滚动作                                                                                          |
| -------- | --------------------------------------------------------------------------------------------- |
| 仅前端      | 移除 `/live-calendar` 路由与 `SidebarNav` 项；卸载 `@fullcalendar/*`（若无其他使用方）                                    |
| 仅后端      | 移除 `intelligence.py` 中的 4 个路由；`CalendarService` / fetcher 不再被调用                                |
| 全部回滚     | 回退 feature 分支。**日历数据表无需回滚**——仅追加了 `scope_type='calendar'` 的行，不影响快讯与通用资讯                        |
| 数据清理（可选） | `DELETE FROM intelligence_items WHERE source_type = 'wscn_calendar';`（**不删任何既有数据**）           |
| **P0 量纲改造单独回滚** | ① 回滚代码（映射函数、阈值 `3→2`）；② **反向迁移存量**：`UPDATE intelligence_items SET importance = CASE WHEN importance=0 THEN NULL WHEN 1 THEN 1 WHEN 3 THEN 2 WHEN 4 THEN 3 END WHERE scope_type='channel';`；③ 删除 `DatabaseSchemaMigration` 中的 version 记录。**反向迁移依赖 `raw_payload.score`**（保留原始值，见 §5.7.4），故迁移可逆 |

***

## 17. 命名规范说明

| 对象         | 命名                                       | 理由                                                    |
| ---------- | ---------------------------------------- | ----------------------------------------------------- |
| 路由         | `/live-calendar`                         | 与现有 `/live-news` 对称                                   |
| 页面组件       | `LiveCalendarPage`                       | 与 `LiveNewsPage` 对称                                   |
| 后端文件       | `data_provider/wallstreetcn_calendar.py` | 与 `wallstreetcn_live_news.py` 对称（snake_case）          |
| 后端 Service | `CalendarService`                        | 与 `LiveNewsService` 同住 `intelligence_service.py`       |
| 前端 API 文件  | `api/liveCalendar.ts`                    | 与 `api/liveNews.ts` 对称（camelCase）                     |
| 前端 Hook    | `hooks/useLiveCalendar.ts`               | 与 `hooks/useLiveNews.ts` 对称                           |
| 前端类型       | `types/liveCalendar.ts`                  | 与 `types/liveNews.ts` 对称                              |
| 落库 `source_type` | `wscn_calendar`                     | 与 `wscn_live_news` 对称                                 |
| 落库 `scope_type`  | `calendar`                          | 与 `channel` 并列                                        |
| HTTP 路径    | 全小写短横线 `/live-calendar`                 | 与 `/live-news` 一致                                     |
| HTTP 查询参数  | snake_case（`country_id`、`importance_min`）| 与 live-news 现有参数风格一致                                  |
| HTTP 响应字段  | snake_case（`start_at`、`short_title`）      | 与 live-news 响应一致，前端负责 camelCase 转换                   |
| 前端数据契约类型 | `*Def`（`LiveCalendarEventDef` / `CalendarTabDef` / `CalendarCountryDef` / `LiveCalendarQueryDef`） | TYPE_NAMING：描述数据 → `Def` |
| 前端组件       | `LiveCalendarGrid` / `LiveCalendarTabs`   | 大驼峰，命名导出；目录 `components/common/<名>/`（COMPONENTS.md） |
| 前端 i18n    | `liveCalendar.*`                          | I18N_NAMING 第 7 类：路由 path camelCase 前缀，与 `liveNews.*` 并列 |

***

## 附录 A：实测证据索引

| 项             | 内容                                                                                                                                            |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 抓包工具          | Playwright + Chromium（headless），监听 `page.on('request')`                                                                                         |
| 抓包时间          | 2026-09-01                                                                                                                                    |
| 验证区间          | `2026-08-28 ~ 2026-09-25`（对应参考图日期范围）                                                                                                           |
| 主接口返回         | `569` 条（`FE` 88 / `FD` 481）                                                                                                                     |
| Tab 点击是否触发新请求 | ❌ 否（宏观 / 财报 / 新股 / 活动 均未触发）                                                                                                                    |
| 页面首屏请求        | `GET /apiv1/finance/countries`、`GET /apiv1/finance/macrodatas?start=1788192000&end=1788278399`                                                    |
| 其它端点枚举        | 见 §2.2                                                                                                                                        |
| 原始证据落盘        | `.claude/reviews/live-calendar-feasibility-2026-09-01.md`                                                                                         |

## 附录 B：与参考图的能力差（明确记录）

参考图中出现的**逐只公司财报条目**（如 `蔚来(09866.HK) 中报`、`Credo(CRDO.US) 第一季报`、`博通`、`慧与`、`Ciena`、`甲骨文`、`Adobe`）在当前**公开未登录态**接口下**无法获取**：

- `macrodatas` 只返回 `FE` 级别的财报事件（如「Marvell 财报与电话会」），不含逐公司条目；
- `reports` / `ipodatas` 端点对未登录态恒返回 `items=[]`（已跨 2024 全年、2026-01、2026-04、2026-08~09 多区间验证）。

**本期处理方式**：如实呈现 `FE` 中的财报事件，并在文档中记录该能力边界；二期通过 akshare / Yahoo Finance / Tushare 等数据源补齐（契约见 §7.5）。
