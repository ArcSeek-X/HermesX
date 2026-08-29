# 实时财经快讯中心（Live News）设计方案

> 目标：将华尔街见闻 `https://wallstreetcn.com/live/global` 的 7x24 快讯能力搬入 HermesX，提供「多频道 Tab + 重要级筛选 + 关键词搜索 + 按日过滤」的资讯板块。
>
> 本文为**方案文档**，所有接口契约、字段映射、实测数据均需在实施阶段严格遵循。

***

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 数据源能力核实（实测佐证）](#2-数据源能力核实实测佐证)
- [3. 频道 ID 枚举（查询入参）](#3-频道-id-枚举查询入参)
- [4. 系统架构与分层](#4-系统架构与分层)
- [5. 数据库设计](#5-数据库设计)
- [6. 后端接口规格（详细）](#6-后端接口规格详细)
- [7. 前端设计](#7-前端设计)
- [8. 接口 / 前端 API / Hook 三方对照表](#8-接口--前端-api--hook-三方对照表)
- [9. 时间维度查询能力](#9-时间维度查询能力)
- [10. 降级策略（官方源 → NewsNow）](#10-降级策略官方源--newsnow)
- [11. 边界条件与空态处理](#11-边界条件与空态处理)
- [12. 配置与开关](#12-配置与开关)
- [13. 实施计划](#13-实施计划)
- [14. 风险、合规与回滚](#14-风险合规与回滚)
- [15. 命名规范说明](#15-命名规范说明)

***

## 1. 背景与目标

### 1.1 需求来源

参考华尔街见闻 7x24 快讯页 `https://wallstreetcn.com/live/global`，该页面具备：

- 顶部 **8 个频道 Tab**：要闻 / A股 / 美股 / 港股 / 外汇 / 商品 / 债券 / 科技
- 工具条：**日期过滤**、**关键词搜索**、**「只看重要的」** 开关、手动刷新
- 内容区：按**日期分组**的快讯卡片，左侧竖线区分**重要 / 非重要**

### 1.2 与本项目的契合度

用户开发的资讯板块围绕**股票、财经及相关行业新闻**，而华尔街见闻快讯内容以**宏观经济、政策、公司财报、商品外汇**为主，与本项目的 A股 / 港股 / 美股分析主线高度吻合，是合适的资讯源。

### 1.3 项目现状（复用基础）

| 已有能力        | 位置                                      | 状态                                     |
| ----------- | --------------------------------------- | -------------------------------------- |
| 资讯服务主干      | `src/services/intelligence_service.py`  | ✅ 支持 `rss` / `atom` / `newsnow` 三种协议   |
| 资讯持久化       | `src/repositories/intelligence_repo.py` | ✅ 统一落 `intelligence_items`             |
| 资讯 API      | `api/v1/endpoints/intelligence.py`      | ✅ 已注册 `/api/v1/intelligence/*`         |
| NewsNow 内置源 | `_NEWSNOW_DEFAULT_SOURCE_DEFS`          | ✅ 已含 `wallstreetcn-quick` 等 5 个源       |
| 配置项         | `src/config.py` + `.env.example`        | ✅ 已含 `news_intel_*`、`newsnow_base_url` |
| 前端路由        | `apps/hrs-web/src/App.tsx`              | ✅ 壳 + 子路由结构，新增页面成本低                    |
| SSE 通道      | `/api/v1/analysis/events`               | ✅ 已有（本期不复用，见 §4.4）                     |
| **独立快讯页**   | —                                       | ❌ **缺失，本期建设**                          |

> **结论**：后端资讯采集与沉淀链路已具备约 70%，本期重点是**新增华尔街见闻直连能力**、**频道与重要级建模**、**前端快讯页面**。

***

## 2. 数据源能力核实（实测佐证）

> 所有数据均为真实调用结果，非推测。

### 2.1 华尔街见闻官方接口（主数据源）

**端点**

```
GET https://api-one.wallstcn.com/apiv1/content/lives?channel=<频道ID>&limit=<N>
```

**请求头**（实测必需）

| Header       | 值                           |
| ------------ | --------------------------- |
| `User-Agent` | 常规浏览器 UA                    |
| `Referer`    | `https://wallstreetcn.com/` |

**实测调用结果（2026-08-28 23:03，limit=30）**

| Tab | channel 参数          | 条数 | 最新时间        | 重要率(score≥2) | 最新 3 条真实内容（★=重要）                                                                                |
| --- | ------------------- | -- | ----------- | ------------ | ----------------------------------------------------------------------------------------------- |
| 要闻  | `global-channel`    | 30 | 08-28 23:03 | 10/30        | 现货钯金涨8.00%，现报1457.21美元/盎司。美股超大规模云服务商指数涨超2.4%，刷新日高至98.76点PVC夜盘收涨约3.1%，焦煤涨约3.1%，LPG涨约2.4%         |
| A股  | `a-stock-channel`   | 30 | 08-28 23:03 | 6/30         | 现货钯金涨8.00%…PVC夜盘收涨约3.1%…★美联储主席凯文·沃什警告称，通胀并未出现有意义的放缓                                             |
| 美股  | `us-stock-channel`  | 30 | 08-28 23:03 | 14/30        | 现货钯金涨8.00%…美股超大规模云服务商指数涨超2.4%…据知情人士透露，Notion计划今年员工规模扩大约30%                                      |
| 港股  | `hk-stock-channel`  | 30 | 08-28 22:24 | 10/30        | ★沃什就通胀目标发表评论后，市场对加息预期正在升温沃什讲话之际，现货黄金跌超0.9%，刷新日低至4543.90美元/盎司旭辉控股集团公告，上半年已确认收入约人民币45.37亿         |
| 科技  | `tech-channel`      | 30 | 08-28 17:08 | **0/30**     | AI机器人公司Sharpa已完成超45亿人民币融资，投资方含阿里、美团、腾讯GFK：2026年7月中国音频市场，1000元以上高端TWS华为居首8月21日猛士X700全球首秀，猛士与华为合作 |
| 商品  | `commodity-channel` | 30 | 08-28 23:00 | 7/30         | PVC夜盘收涨约3.1%，焦煤涨约3.1%…特朗普称计划授权农民和牧场主自行加工食品★沃什在杰克逊霍尔央行年会首秀之际，美国10年期国债收益率呈V形反转                    |
| 外汇  | `forex-channel`     | 30 | 08-28 22:35 | 17/30        | 从海关总署获悉，我国对上合组织其他成员国进出口保持稳定增长★市场对美联储加息的预期正在升温现货黄金跌超0.9%…                                        |
| 债券  | `bond-channel`      | 30 | 08-28 22:37 | 11/30        | 邮储银行行长芦苇在中期业绩发布会回答分析师提问越秀地产召开2026年中期业绩发布会国海证券：上半年归母净利润5.51亿元，同比增长48.96%                         |

**8 频道全部返回** **`code=20000`**。

### 2.2 佐证出的 4 个关键事实（直接影响设计）

| # | 事实                                                                                                                                                                                                           | 设计影响                                                      |
| - | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| 1 | `channels` 是**多值数组**，一条快讯可属多频道。实测 id=3157010 为 `["global-channel","a-stock-channel","xgb","financing","goldc","us-stock-channel"]`——**内部频道标记比 8 个 Tab 更多**（另有 `xgb`新股 / `financing`融资 / `goldc`黄金 / `oil`原油） | 一条快讯需**按频道拆多行**落库；为后续更细分类预留空间                             |
| 2 | `score` 重要级真实有效，实测分布 `{1:69, 2:29, 3:2}`；score≥2 的均为央行讲话、政策发文、重磅财报                                                                                                                                           | **重要级直接使用官方** **`score`**，无需启发式猜测                         |
| 3 | **`tech-channel`** **重要率 0/30，且更新最慢**（17:08 vs 其他 23:03），其条目 `channels` 仅为 `["tech-channel"]`，**独立于 global 主流**                                                                                              | ① 8 频道须**各自抓取**，不可只抓 global；② 科技 Tab「只看重要的」必为空，需空态（见 §11） |
| 4 | A股/美股/外汇/商品/债券 与 global **内容高度重叠**（最新几条 id 相同），是主流按 `channels` 打的过滤视图                                                                                                                                        | 落库按 `(source_id, url, scope_value)` 天然去重，重复写入无副作用         |

### 2.3 NewsNow 兜底源（能力对比）

| source\_id                                   | 条数    | 内容类型                                              | 可用         |
| -------------------------------------------- | ----- | ------------------------------------------------- | ---------- |
| `wallstreetcn`                               | 30    | 与 `wallstreetcn-quick` **完全相同**（同 id 3156951），为别名 | ✅ 等价       |
| `wallstreetcn-quick`                         | 30    | 快讯流 `livenews/{id}`，**带** **`extra.date`**        | ✅ **兜底选用** |
| `wallstreetcn-news`                          | 25    | 深度文章 `articles/{id}`                              | ❌ 非快讯      |
| `wallstreetcn-hot`                           | 10    | 热门文章，`extra=None` **无时间戳**                        | ❌ 无法时间分组   |
| `wallstreetcn-global/-a-share/-us/-hk/-tech` | **0** | **不存在**                                           | ❌ 无子频道     |

**NewsNow 三处硬伤**（正是需要官方源的原因）：

1. **无频道**：对 wallstreetcn 只有「快讯 / 文章」两类，**0 个频道**
2. **无重要级**：字段仅 `{id, title, url, extra.date}`，无 `score`、无正文
3. **无分页**：`limit` / `page` / `cursor` 参数**实测全部无效**，固定 30 条；时间跨度仅 **1.31 小时**

### 2.4 官方源 vs NewsNow 能力矩阵

| 能力                | 官方 `/content/lives`              | NewsNow `wallstreetcn-quick` |
| ----------------- | -------------------------------- | ---------------------------- |
| 频道 Tab            | ✅ 8 个                            | ❌ 0 个（合并流）                   |
| 重要级 `score`       | ✅ 有                              | ❌ 无                          |
| 正文 `content_text` | ✅ 有                              | ❌ 只有标题                       |
| 分页 / 历史           | ✅ `next_cursor` + `limit` 上限 100 | ❌ 固定 30 条，无分页                |
| 实时游标              | ✅ `polling_cursor`               | ❌ 无                          |
| 时间字段覆盖率           | ✅ 100%                           | ✅ 100%                       |
| 稳定性 / SLA         | ⚠️ 非公开接口                         | ⚠️ 公共实例                      |

***

## 3. 频道 ID 枚举（查询入参）

### 3.1 8 个频道（对应前端 Tab）

| 序号 | 频道 ID（上游入参 `channel`） | Tab 文案 | 落库 `scope_value` | 说明                          |
| -- | --------------------- | ------ | ---------------- | --------------------------- |
| 1  | `global-channel`      | 要闻     | `global`         | 7x24 快讯主集合，官方回传频道名 `7x24快讯` |
| 2  | `a-stock-channel`     | A股     | `a-stock`        | A股相关，与 global 高度重叠          |
| 3  | `us-stock-channel`    | 美股     | `us-stock`       | 美股相关                        |
| 4  | `hk-stock-channel`    | 港股     | `hk-stock`       | 港股相关                        |
| 5  | `tech-channel`        | 科技     | `tech`           | 科技/互联网，**独立于主流，更新最慢**       |
| 6  | `commodity-channel`   | 商品     | `commodity`      | 期货、贵金属、原油                   |
| 7  | `forex-channel`       | 外汇     | `forex`          | 外汇、汇率、央行                    |
| 8  | `bond-channel`        | 债券     | `bond`           | 债券、利率、国债                    |

> **顺序即前端 Tab 展示顺序**，与华尔街见闻站点频道栏一致，单一真源为
> ``data_provider/wallstreetcn_live_news.py`` 的 ``LIVE_NEWS_CHANNELS``。
> 前端不硬编码频道，完全由 ``GET /live-news/channels`` 驱动。

> **入参/落库映射规则**：上游入参带 `-channel` 后缀，落库 `scope_value` 存**去后缀短码**（`global` / `a-stock` / …），转换由 Fetcher 层统一处理。

### 3.2 上游额外频道标记（本期不暴露为 Tab，记录备查）

实测 `channels` 数组中还出现过：`xgb`（新股）、`financing`（融资）、`goldc`（黄金）、`oil`（原油）、`commodity`（商品）。

这些是比 8 个 Tab 更细的内部标记，**本期不单独建 Tab**，但落库时保留在 `raw_payload` 中，为后续「二级分类」预留能力。

***

## 4. 系统架构与分层

### 4.1 分层总览

| 层                | 文件                                           | 职责                                                      | 本期改动                                    |
| ---------------- | -------------------------------------------- | ------------------------------------------------------- | --------------------------------------- |
| **配置层**          | `src/config.py` + `.env.example`             | 开关、阈值、上游地址                                              | 新增 `wscn_live_news_*` 系列配置              |
| **Fetcher 层**    | `data_provider/wallstreetcn_live_news.py` 🆕 | 纯 HTTP：8 频道拉取、`polling_cursor` 增量、`next_cursor` 翻页、超时重试 | **全部新增**                                |
| **Service 层**    | `src/services/intelligence_service.py`       | 编排：**官方源 → 失败降级 NewsNow**；字段标准化；`importance` 计算         | **扩展**，新增 3 个方法                         |
| **Repository 层** | `src/repositories/intelligence_repo.py`      | 落库与查询                                                   | **扩展**，新增按 channel / importance / 日期 查询 |
| **Schema 层**     | `api/v1/schemas/intelligence.py`             | Pydantic 出入参模型                                          | **扩展**，新增 7 个模型                         |
| **API 层**        | `api/v1/endpoints/intelligence.py`           | HTTP 暴露                                                 | **扩展**，新增 4 个路由（**不新建 endpoint 文件**）    |
| **刷新策略**        | `src/services/intelligence_service.py`       | 按需惰性刷新与节流                                             | **新增** `ensure_live_news_fresh()`，见 §4.4 |
| **前端 API 层**     | `apps/hrs-web/src/api/liveNews.ts` 🆕        | 封装 HTTP 调用                                              | **全部新增**                                |
| **前端 Hook 层**    | `apps/hrs-web/src/hooks/useLiveNews.ts` 🆕   | 轮询、分页、按日分组                                              | **全部新增**                                |
| **前端页面层**        | `apps/hrs-web/src/pages/LiveNewsPage.tsx` 🆕 | 布局渲染                                                    | **全部新增**                                |

### 4.2 数据流

```
调度器(5min) / 手动触发
        │
        ▼
WallstreetcnLiveNewsFetcher  ──失败──▶  NewsNow Fetcher(兜底)
        │                                      │
        └──────────► 标准化 ◄──────────────────┘
                        │
                        ▼
              IntelligenceRepository.upsert_items()
                        │
                        ▼
              intelligence_items 表
                        │
                        ▼
        GET /api/v1/intelligence/live-news
                        │
                        ▼
        useLiveNews() ──▶ LiveNewsPage 渲染
```

### 4.3 抓取策略

| 项    | 策略                                                       | 依据                          |
| ---- | -------------------------------------------------------- | --------------------------- |
| 抓取范围 | **8 个频道全部抓取**                                            | 实测 tech 独立于 global，不可只抓主流   |
| 抓取频率 | 默认 **5 分钟**                                              | 主流 100 条覆盖约 2.8 小时，5 分钟不漏数据 |
| 增量方式 | `polling_cursor` 拉最新                                     | 上游提供快讯 id 游标                |
| 历史补齐 | `next_cursor` 向下翻页                                       | 首次启用时补齐历史                   |
| 去重   | `(source_id, url, scope_type, scope_value, market)` 唯一约束 | 复用现有约束                      |
| 保留期  | 沿用 `news_intel_retention_days`（默认 30 天）                  | 复用现有配置                      |

> ⚠️ **历史深度依赖持续落库**：上游是滚动窗口，不补抓则永久丢失。启用后需持续累积，才能支撑「查询 8月26日」这类历史回溯。

### 4.4 实时性方案（已选定：B1，实现时调整为「按需惰性刷新」）

采用 **后端落库 + 前端轮询**，但抓取触发方式在实现时做了调整：

- 前端：`useLiveNews` 内 30 秒轮询 `GET /live-news`
- 手动刷新：`POST /live-news/refresh`
- 后端：**按需惰性刷新**（`ensure_live_news_fresh()`），而非挂在 `runtime_scheduler` 上

#### 为什么不挂 `runtime_scheduler`（与原方案的偏差）

原方案 §4.1 计划「挂现有 `runtime_scheduler` tick」。实现时发现该调度器的 background task
**只有在 `schedule_enabled=True` 时才会随调度器启动**：

```python
# src/services/runtime_scheduler.py
def start(self, *, run_immediately=False):
    config = self._config_provider()
    if not self._is_schedule_enabled(config):   # schedule_enabled 为 False 直接 return
        self.stop()
        return
```

快讯是与「定时分析」无关的独立能力，不应被 `schedule_enabled` 开关牵连
（否则未开启定时分析的用户永远拿不到快讯）。因此改为**惰性触发**：

| 场景             | 行为                                  | 理由                   |
| -------------- | ----------------------------------- | -------------------- |
| 频道无数据（冷启动）     | **同步**抓取该频道                         | 保证首屏不空白，单频道约 1 次上游请求 |
| 有数据但超过配置间隔     | **后台线程**异步刷新全量                       | 不阻塞响应，本次先返回库存数据      |
| `interval = 0` | 跳过自动抓取                              | 仅保留手动刷新入口            |

**节流保护**（两道闸）：

1. 配置间隔 `WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC`（默认 300 秒）
2. 绝对最小间隔 60 秒（`_LIVE_NEWS_MIN_FETCH_INTERVAL_SECONDS`），防止配置异常把请求打爆到上游

> ⚠️ 实现要点：读取配置时不能用 `value or 默认值` 写法。`0` 是合法配置（关闭自动抓取），
> 但会被 `or` 判为 falsy 而错误回退到默认值，导致开关静默失效。
> 已由 `IntelligenceService._config_int()` 统一处理，`tests/test_live_news.py` 有对应回归用例。

**本期不引入 SSE 推送**。项目虽有 `/api/v1/analysis/events` SSE 通道，但新增快讯推送通道会显著增加前后端复杂度，留作后续演进。

***

## 5. 数据库设计

### 5.1 落表清单（实际只改 1 张表，不新建表）

| 表名                     | 作用     | 本期改动                         |
| ---------------------- | ------ | ---------------------------- |
| `intelligence_items`   | 沉淀快讯条目 | **新增 1 列** `importance` + 索引 |
| `intelligence_sources` | 注册数据源  | **本期不改**（见下方说明）             |

#### 为什么不注册到 `intelligence_sources`（与原方案的偏差）

原方案计划「新增 2 行数据」到 `intelligence_sources`。实现时改为**不注册**，快讯走独立抓取链路：

| 维度      | 注册源                                     | **不注册（选定）**                             |
| ------- | ---------------------------------------- | --------------------------------------- |
| 多频道表达   | 一条源记录无法表达 8 个频道                          | 快讯以 `scope_type='channel'` 自行表达频道       |
| 通用抓取链路  | `fetch_enabled_sources()` 会误抓（无对应协议分支而失败） | 互不影响，快讯有独立的 `refresh_live_news()`       |
| 抓取语义    | 通用链路按「源」抓一次；快讯需按频道抓 8 次并拆多行               | 语义匹配                                    |
| 源管理页语义  | 会混入「资讯源管理」列表                             | 不污染既有语义                                 |

因此快讯落库时：`source_id = None`、`source_name = '华尔街见闻快讯'`、
`source_type` 为 `wscn_live_news`（官方源）或 `newsnow`（降级源）。
去重由 `upsert_items` 中「`source_id is None` 时按 `source_name` 匹配」的既有分支保证。

### 5.2 `intelligence_sources`（已有结构，本期不改动）

| 字段                                               | 类型                     | 说明                                                      |
| ------------------------------------------------ | ---------------------- | ------------------------------------------------------- |
| `id`                                             | Integer PK             | 主键                                                      |
| `name`                                           | String(100) unique idx | 源名，如 `华尔街见闻快讯(官方)`                                      |
| `source_type`                                    | String(32) idx         | 现有 `rss`/`atom`/`newsnow`，**本期新增** **`wscn_live_news`** |
| `url`                                            | String(1000)           | 上游地址                                                    |
| `enabled`                                        | Boolean idx            | 开关                                                      |
| `scope_type` / `scope_value` / `market`          | String idx             | 作用域                                                     |
| `last_status` / `last_error` / `last_fetched_at` | —                      | 健康检查                                                    |
| `created_at` / `updated_at`                      | DateTime               | 时间戳                                                     |

### 5.3 `intelligence_items`（已有 + 本期新增 1 列）

| 字段                            | 类型                                | 本期        | 承载内容                                                 |
| ----------------------------- | --------------------------------- | --------- | ---------------------------------------------------- |
| `id`                          | Integer PK                        | —         | 自增主键                                                 |
| `source_id`                   | Integer FK idx                    | —         | → `intelligence_sources.id`，区分数据源                    |
| `source_name` / `source_type` | String idx                        | —         | `wallstreetcn` / `wscn_live_news` \| `newsnow`       |
| `title`                       | String(300) **NOT NULL**          | —         | 快讯 `title` 常为空 → **回退取** **`content_text`** **首行截断** |
| `summary`                     | Text                              | —         | ← `content_text`                                     |
| `url`                         | String(1000) idx                  | —         | ← `uri`（`livenews/{id}`）                             |
| `source`                      | String(100)                       | —         | 固定 `华尔街见闻`                                           |
| `published_at`                | DateTime idx                      | —         | ← `display_time`（**秒**）                              |
| `fetched_at`                  | DateTime idx                      | —         | 入库时间                                                 |
| `scope_type`                  | String(32) idx                    | **复用**    | 固定填 `'channel'`（**新增枚举值**）                           |
| `scope_value`                 | String(64) idx                    | **复用**    | 频道短码：`global` / `a-stock` / …                        |
| `market`                      | String(32) idx                    | —         | `cn` / `hk` / `us` / `global`                        |
| `raw_payload`                 | Text                              | —         | 原始 JSON，留痕备查                                         |
| **`importance`**              | **Integer idx**                   | **🆕 新增** | ← `score`（1 / 2 / 3）                                 |
| 唯一约束                          | `uix_intel_item_source_scope_url` | **不动**    | `(source_id, url, scope_type, scope_value, market)`  |

**新增列 DDL**

```sql
ALTER TABLE intelligence_items ADD COLUMN importance INTEGER;
CREATE INDEX ix_intel_item_importance ON intelligence_items (importance);
CREATE INDEX ix_intel_item_channel_time ON intelligence_items (scope_value, published_at);
```

### 5.4 为何用 `scope_type='channel'` 复用，而非新增 `channel` 列

> 该方案已经用户确认。

| 维度      | `scope_type='channel'` 复用（**选定**）            | 新增 `channel` 列                        |
| ------- | -------------------------------------------- | ------------------------------------- |
| 唯一约束    | **无需改动**                                     | 需重建 `uix_intel_item_source_scope_url` |
| 迁移风险    | **低**（仅加 1 列 + 索引）                           | 中高（改约束可能影响存量数据）                       |
| 多频道存储   | `scope_value` 在约束内 → 同 url 不同频道各存一行，**天然去重** | 需自行保证                                 |
| 与现有查询兼容 | 复用 `list_items(scope_type, scope_value)` 签名  | 需新增查询分支                               |
| 语义清晰度   | 中（需约定枚举值）                                    | 高                                     |

### 5.5 多数据源支持统一落一张表

华尔街见闻官方源、NewsNow、RSS/Atom **统一落** **`intelligence_items`**，靠 `source_id` / `source_name` / `source_type` 区分来源。

**标准化字段映射**

| 标准字段           | 华尔街见闻官方                        | NewsNow（兜底）          | RSS / Atom |
| -------------- | ------------------------------ | -------------------- | ---------- |
| `title`        | `title` \|\| `content_text` 首行 | `title`              | `title`    |
| `summary`      | `content_text`                 | `title`（无正文）         | `summary`  |
| `url`          | `uri`                          | `url`                | `link`     |
| `published_at` | `display_time`（**秒**）          | `extra.date`（**毫秒**） | `pubDate`  |
| `importance`   | `score`                        | **NULL**（无此能力）       | NULL       |
| `scope_value`  | `channels[]` 拆多行               | `global` 单行          | 源配置        |

> ⚠️ **单位陷阱**：华尔街见闻 `display_time` 是**秒级**，NewsNow `extra.date` 是**毫秒级**。标准化层必须统一换算，否则时间排序与按日过滤会错乱。

### 5.6 项目内其他数据源及落表情况

| 类别         | 数据源                                                                                                                                                                                                             | 作用                                                | 落表 | 落表位置                                                                                    |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | -- | --------------------------------------------------------------------------------------- |
| **行情类**    | `data_provider/` 下 12 个 fetcher：`akshare` / `baostock` / `efinance` / `pytdx` / `tencent` / `tushare`（A股）`yfinance` / `alphavantage` / `finnhub`（美股）`longbridge`（港股）`tickflow`（实时 tick）`tw_institutional`（台股法人） | OHLCV 日线、实时报价、基本面                                 | ✅  | **`stock_daily`**（code+date 唯一，含 OHLCV + 技术指标）**`fundamental_snapshot`**（P0 write-only） |
| **资讯类（旧）** | `src/services/news_service.py`（已被替代）                                                                                                                                                                            | 个股新闻，按股票代码检索                                      | ✅  | **`news_intel`**（按 `code` 关联，`ReportNews.tsx` 仍在使用）                                     |
| **资讯类（新）** | `IntelligenceService`（RSS/Atom/NewsNow）                                                                                                                                                                         | 大盘 / 板块 / 市场级资讯                                   | ✅  | **`intelligence_items`** ← **本期快讯同样落此表**                                                |
| **社交舆情**   | `src/services/social_sentiment_service.py`                                                                                                                                                                      | Reddit / X / Polymarket 情绪（仅美股）                   | ❌  | 实时查询，用完即弃                                                                               |
| **搜索增强**   | `src/search_service.py`                                                                                                                                                                                         | Anspire / Tavily / Brave 等，给 LLM 注入 news\_context | ❌  | 实时查询                                                                                    |

**规律**：**结构化且可复用**的数据（行情、资讯）落表供历史回溯；**一次性上下文**（舆情、LLM 搜索）不落表以避免存储膨胀。本期快讯属可复用资讯，落 `intelligence_items` 符合既有分层惯例。

***

## 6. 后端接口规格（详细）

> 所有接口挂载在现有 `api/v1/endpoints/intelligence.py`，**不新建 endpoint 文件**。
> 路由前缀：`/api/v1/intelligence`

### 6.1 新增接口总览

| # | 接口名称     | 方法   | 接口地址                                       | 说明                 |
| - | -------- | ---- | ------------------------------------------ | ------------------ |
| 1 | 查询快讯频道列表 | GET  | `/api/v1/intelligence/live-news/channels`  | Tab 数据源，降级时只返回 1 个 |
| 2 | 查询快讯列表   | GET  | `/api/v1/intelligence/live-news`           | 快讯流主接口             |
| 3 | 手动刷新快讯   | POST | `/api/v1/intelligence/live-news/refresh`   | 触发抓取               |
| 4 | 查询快讯详情   | GET  | `/api/v1/intelligence/live-news/{item_id}` | 单条详情               |

### 6.2 接口 1：查询快讯频道列表

| 项        | 内容                                        |
| -------- | ----------------------------------------- |
| **接口名称** | 查询快讯频道列表                                  |
| **接口地址** | `/api/v1/intelligence/live-news/channels` |
| **请求方式** | `GET`                                     |
| **认证**   | 沿用现有会话认证                                  |

**入参**：无

**出参**

| 字段         | 类型                  | 说明                          |
| ---------- | ------------------- | --------------------------- |
| `channels` | `LiveNewsChannel[]` | 频道列表，见下方模型                  |
| `degraded` | `boolean`           | `true` 表示当前处于 NewsNow 降级模式  |
| `source`   | `string`            | `wallstreetcn` \| `newsnow` |

`LiveNewsChannel`：`{ value: string, label: string }`

**响应示例**

```json
{
  "channels": [
    { "value": "global-channel", "label": "要闻" },
    { "value": "a-stock-channel", "label": "A股" },
    { "value": "us-stock-channel", "label": "美股" },
    { "value": "hk-stock-channel", "label": "港股" },
    { "value": "tech-channel", "label": "科技" },
    { "value": "commodity-channel", "label": "商品" },
    { "value": "forex-channel", "label": "外汇" },
    { "value": "bond-channel", "label": "债券" }
  ],
  "degraded": false,
  "source": "wallstreetcn"
}
```

**降级响应示例**

```json
{
  "channels": [{ "value": "global-channel", "label": "要闻" }],
  "degraded": true,
  "source": "newsnow"
}
```

### 6.3 接口 2：查询快讯列表

| 项        | 内容                               |
| -------- | -------------------------------- |
| **接口名称** | 查询快讯列表                           |
| **接口地址** | `/api/v1/intelligence/live-news` |
| **请求方式** | `GET`                            |
| **认证**   | 沿用现有会话认证                         |

**入参（Query）**

| 参数               | 类型      | 必填    | 默认       | 校验                  | 说明                           |
| ---------------- | ------- | ----- | -------- | ------------------- | ---------------------------- |
| `channel`        | string  | **是** | —        | 枚举见 §3.1            | 频道 ID，如 `a-stock-channel`    |
| `important_only` | boolean | 否     | `false`  | —                   | 只看重要的（`score >= 2`）          |
| `keyword`        | string  | 否     | —        | 长度 ≤ 100            | 关键词模糊匹配（标题 / 正文）             |
| `date`           | string  | 否     | —        | `YYYY-MM-DD`        | 精确查询某日（见 §9）                 |
| `date_from`      | string  | 否     | —        | `YYYY-MM-DD`        | 起始日期（含）                      |
| `date_to`        | string  | 否     | —        | `YYYY-MM-DD`        | 结束日期（含）                      |
| `cursor`         | string  | 否     | —        | —                   | 分页游标，取上次响应 `next_cursor`     |
| `limit`          | integer | 否     | `30`     | `1 <= limit <= 100` | 每页条数                         |
| `mode`           | string  | 否     | `cached` | `cached` \| `live`  | `cached` 读库；`live` 直连上游（排查用） |

> **优先级**：同时传 `date` 与 `date_from`/`date_to` 时，**以** **`date`** **为准**。

**出参**

| 字段            | 类型               | 说明                 |
| ------------- | ---------------- | ------------------ |
| `items`       | `LiveNewsItem[]` | 快讯列表，见下方模型         |
| `next_cursor` | string \| null   | 下一页游标，`null` 表示无更多 |
| `degraded`    | boolean          | 是否降级数据             |
| `server_time` | integer          | 服务端时间戳（秒），供前端校准    |
| `total`       | integer          | 当前条件下总条数（用于空态判断）   |

`LiveNewsItem`

| 字段             | 类型             | 说明                                            |
| -------------- | -------------- | --------------------------------------------- |
| `id`           | integer        | 快讯 ID（上游 id）                                  |
| `title`        | string         | 标题，快讯常为空串                                     |
| `content`      | string         | 正文（多行，`\n` 分隔段落）                              |
| `display_time` | integer        | 发布时间（**秒级**时间戳）                               |
| `score`        | integer        | 重要级：1 普通 / 2 重要 / 3 非常重要                      |
| `important`    | boolean        | `score >= 2`                                  |
| `channels`     | string\[]      | 所属频道（上游原始值）                                   |
| `uri`          | string         | 原文链接 `https://wallstreetcn.com/livenews/{id}` |
| `author`       | string \| null | 作者                                            |

**响应示例**

```json
{
  "items": [
    {
      "id": 3157010,
      "title": "",
      "content": "现货钯金涨8.00%，现报1457.21美元/盎司。",
      "display_time": 1787925480,
      "score": 1,
      "important": false,
      "channels": ["global-channel", "a-stock-channel", "us-stock-channel"],
      "uri": "https://wallstreetcn.com/livenews/3157010",
      "author": "葛冬瑾"
    }
  ],
  "next_cursor": "1787912832",
  "degraded": false,
  "server_time": 1787925480,
  "total": 100
}
```

**错误响应**

| HTTP | code | 场景                                 |
| ---- | ---- | ---------------------------------- |
| 400  | —    | `channel` 非法 / `limit` 越界 / 日期格式错误 |
| 500  | —    | 内部异常                               |

### 6.4 接口 3：手动刷新快讯

| 项        | 内容                                       |
| -------- | ---------------------------------------- |
| **接口名称** | 手动刷新快讯                                   |
| **接口地址** | `/api/v1/intelligence/live-news/refresh` |
| **请求方式** | `POST`                                   |
| **认证**   | 沿用现有会话认证                                 |

**入参（Body, JSON）**

| 参数         | 类型        | 必填 | 默认     | 说明            |
| ---------- | --------- | -- | ------ | ------------- |
| `channels` | string\[] | 否  | 全部 8 个 | 指定刷新的频道 ID 列表 |

**出参**

| 字段              | 类型        | 说明                                       |
| --------------- | --------- | ---------------------------------------- |
| `fetched_count` | integer   | 本次新入库条数                                  |
| `degraded`      | boolean   | 是否走了降级                                   |
| `errors`        | object\[] | 各频道失败详情 `{channel, error}`，**fail-open** |

**响应示例**

```json
{
  "fetched_count": 42,
  "degraded": false,
  "errors": []
}
```

### 6.5 接口 4：查询快讯详情

| 项        | 内容                                         |
| -------- | ------------------------------------------ |
| **接口名称** | 查询快讯详情                                     |
| **接口地址** | `/api/v1/intelligence/live-news/{item_id}` |
| **请求方式** | `GET`                                      |
| **认证**   | 沿用现有会话认证                                   |

**入参（Path）**

| 参数        | 类型      | 必填    | 说明    |
| --------- | ------- | ----- | ----- |
| `item_id` | integer | **是** | 快讯 ID |

**出参**：`LiveNewsItem`（模型同 §6.3）

**错误响应**：`404` 快讯不存在

### 6.6 复用的现有接口（不改）

| 接口名称      | 方法   | 地址                                           | 本期用途                  |
| --------- | ---- | -------------------------------------------- | --------------------- |
| 资讯源列表     | GET  | `/api/v1/intelligence/sources`               | 查看 wallstreetcn 源注册状态 |
| 创建资讯源     | POST | `/api/v1/intelligence/sources`               | 注册 `wscn_live_news` 源 |
| 批量拉取（启用源） | POST | `/api/v1/intelligence/sources/fetch-enabled` | 定时任务的批量入口             |
| 查询资讯条目    | GET  | `/api/v1/intelligence/items`                 | 通用查询，**保持向后兼容**       |

> `GET /items` 现有参数：`scope_type` / `scope_value` / `market` / `query` / `days` / `page` / `page_size`。本期**不修改**其签名，快讯数据同样可经此接口查出（用 `scope_type=channel`）。

***

## 7. 前端设计

### 7.1 页面布局（对齐华尔街见闻）

```
┌────────────────────────────────────────────────────────────────┐
│ 快讯中心                                                        │
├────────────────────────────────────────────────────────────────┤
│ 要闻  A股  美股  港股  外汇  商品  债券  科技      ← TabNav      │
├────────────────────────────────────────────────────────────────┤
│ [🔍 搜索快讯…Input] ☐只看重要的  [日期▾Select] [刷新Button]     │
├────────────────────────────────────────────────────────────────┤
│  08月28日 周五                                    ← 日期分组头   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │▌23:03  现货钯金涨8.00%，现报1457.21美元/盎司。          │    │
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │▌23:00  PVC夜盘收涨约3.1%，焦煤涨约3.1%…        ★重要    │    │
│  └────────────────────────────────────────────────────────┘    │
│  08月27日 周四                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │▌14:04  【美团电话会：预期三季度外卖UE同比改善】…  ★重要 │    │
│  └────────────────────────────────────────────────────────┘    │
│                    [加载更多 Button]                            │
└────────────────────────────────────────────────────────────────┘
```

**视觉特征**（对齐华尔街见闻）：

- 左侧**竖线颜色**区分重要级：主色 / 红色 = 重要，灰色 = 普通
- `【】`内标题**加粗**
- 时间格式为 `HH:mm`，日期分组头为 `MM月DD日 周X`

### 7.2 控件选型（全部复用已有组件）

| 用途        | 组件                  | 路径                                    | 关键 Props                                                                                 |
| --------- | ------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------- |
| 频道 Tab    | **`TabNav`**        | `components/common/TabNav.tsx`        | `items:{value,label}[]`、`value`、`onChange`、`variant:'secondary'`、`rightSlot`、`ariaLabel` |
| 搜索框       | **`Input`**         | `components/basic/Input.tsx`          | 原生 `value` / `onChange` / `placeholder` 透传                                               |
| 只看重要的     | **`Checkbox`**      | `components/basic/Checkbox.tsx`       | `isSelected` / `onValueChange`                                                           |
| 日期选择      | **`Select`**        | `components/basic/Select.tsx`         | 日期过滤下拉                                                                                   |
| 新闻卡片容器    | **`Card`**          | `components/basic/Card.tsx`           | 卡片容器                                                                                     |
| 频道 / 重要标签 | **`Chip`**          | `components/basic/Chip.tsx`           | 小标签                                                                                      |
| 刷新 / 加载更多 | **`Button`**        | `components/basic/Button.tsx`         | `onPress`                                                                                |
| 加载态       | **`Loading`**       | `components/basic/Loading.tsx`        | —                                                                                        |
| 日期分组分隔    | **`Separator`**     | `components/basic/Separator.tsx`      | —                                                                                        |
| 降级提示      | **`InlineTipCard`** | `components/common/InlineTipCard.tsx` | 降级 / 空态提示                                                                                |

> **约束**：
>
> 1. 搜索框**只复用** `components/basic/Input.tsx`，**不新增任何本地 Input 组件**（项目约定：该文件是所有输入框改动的唯一目标文件）。
> 2. 新闻卡片**不额外封装成新组件**，在 `LiveNewsPage.tsx` 内用 `Card` + `Chip` 组合渲染；仅将「日期分组头」抽成页面内纯展示小函数。

### 7.3 前端 API 层：`apps/hrs-web/src/api/liveNews.ts`

| 方法名                         | 请求                                             | 入参                        | 出参                         |
| --------------------------- | ---------------------------------------------- | ------------------------- | -------------------------- |
| `getLiveNewsChannels()`     | `GET /api/v1/intelligence/live-news/channels`  | 无                         | `LiveNewsChannelsResponse` |
| `getLiveNews(params)`       | `GET /api/v1/intelligence/live-news`           | `GetLiveNewsParams`       | `LiveNewsResponse`         |
| `refreshLiveNews(params?)`  | `POST /api/v1/intelligence/live-news/refresh`  | `{ channels?: string[] }` | `RefreshLiveNewsResponse`  |
| `getLiveNewsDetail(itemId)` | `GET /api/v1/intelligence/live-news/{item_id}` | `itemId: number`          | `LiveNewsItem`             |

**类型定义**（`apps/hrs-web/src/types/liveNews.ts`）

```ts
export interface LiveNewsChannel {
  value: string;   // 'a-stock-channel'
  label: string;   // 'A股'
}

export interface LiveNewsItem {
  id: number;
  title: string;
  content: string;
  display_time: number;      // 秒级时间戳
  score: number;             // 1 普通 / 2 重要 / 3 非常重要
  important: boolean;        // score >= 2
  channels: string[];
  uri: string;
  author?: string | null;
}

export interface GetLiveNewsParams {
  channel: string;
  important_only?: boolean;
  keyword?: string;
  date?: string;             // YYYY-MM-DD
  date_from?: string;
  date_to?: string;
  cursor?: string;
  limit?: number;
  mode?: 'cached' | 'live';
}

export interface LiveNewsResponse {
  items: LiveNewsItem[];
  next_cursor: string | null;
  degraded: boolean;
  server_time: number;
  total: number;
}

export interface LiveNewsChannelsResponse {
  channels: LiveNewsChannel[];
  degraded: boolean;
  source: string;
}

export interface RefreshLiveNewsResponse {
  fetched_count: number;
  degraded: boolean;
  errors: Array<{ channel: string; error: string }>;
}
```

### 7.4 前端 Hook 层：`apps/hrs-web/src/hooks/useLiveNews.ts`

| Hook 名                          | 入参                                           | 返回                                               | 职责                   |
| ------------------------------- | -------------------------------------------- | ------------------------------------------------ | -------------------- |
| `useLiveNewsChannels()`         | 无                                            | `{ channels, degraded, source, loading, error }` | 拉频道列表，**决定渲染几个 Tab** |
| `useLiveNews(channel, options)` | `channel: stringoptions: UseLiveNewsOptions` | `UseLiveNewsResult`                              | 分页拉取 + 30s 轮询 + 按天分组 |

**`UseLiveNewsOptions`**

| 字段              | 类型             | 默认      | 说明                |
| --------------- | -------------- | ------- | ----------------- |
| `importantOnly` | boolean        | `false` | 只看重要的             |
| `keyword`       | string         | `''`    | 关键词（内部做 300ms 防抖） |
| `date`          | string \| null | `null`  | `YYYY-MM-DD`，精确某日 |
| `autoRefresh`   | boolean        | `true`  | 是否 30s 轮询         |

**`UseLiveNewsResult`**

| 字段           | 类型                                                              | 说明                                |
| ------------ | --------------------------------------------------------------- | --------------------------------- |
| `items`      | `LiveNewsItem[]`                                                | 平铺列表                              |
| `grouped`    | `Array<{ date: string; label: string; items: LiveNewsItem[] }>` | **按天分组**结果，`label` 形如 `08月28日 周五` |
| `loading`    | boolean                                                         | 首次加载中                             |
| `refreshing` | boolean                                                         | 后台轮询中                             |
| `error`      | string \| null                                                  | 错误信息                              |
| `hasMore`    | boolean                                                         | 是否还有下一页                           |
| `loadMore`   | `() => void`                                                    | 加载更多                              |
| `refresh`    | `() => Promise<void>`                                           | 手动刷新（调 `refreshLiveNews` 后重新拉取）   |
| `degraded`   | boolean                                                         | 是否降级数据                            |
| `isEmpty`    | boolean                                                         | 空态判断（含"本频道暂无重要快讯"场景）              |

**实现要点**

- 轮询：`setInterval` 30s，页面 `visibilitychange` 隐藏时暂停，避免无效请求
- 请求取消：`AbortController` + 依赖变化时清理
- Tab 缓存：用项目已有 `useCachedState` 记住上次选中频道
- 分组：按 `display_time` 本地时区转 `YYYY-MM-DD` 后分组

### 7.5 路由与入口注册

| 文件                                             | 改动                                                          |
| ---------------------------------------------- | ----------------------------------------------------------- |
| `apps/hrs-web/src/App.tsx`                     | 新增 `<Route path="/live-news" element={<LiveNewsPage />} />` |
| `apps/hrs-web/src/components/layout/Shell.tsx` | 侧边栏新增「快讯中心」入口                                               |

***

## 8. 接口 / 前端 API / Hook 三方对照表

| 功能说明                                  | 后端接口（方法 + 地址）                                  | 前端 API 方法                   | 前端 Hook                              |
| ------------------------------------- | ---------------------------------------------- | --------------------------- | ------------------------------------ |
| **获取频道 Tab 列表**决定渲染几个 Tab；降级时只返回「要闻」  | `GET /api/v1/intelligence/live-news/channels`  | `getLiveNewsChannels()`     | `useLiveNewsChannels()`              |
| **查询快讯列表**按频道 / 重要级 / 关键词 / 日期过滤，支持分页 | `GET /api/v1/intelligence/live-news`           | `getLiveNews(params)`       | `useLiveNews(channel, options)`      |
| **手动刷新快讯**触发服务端抓取（调用后端接口 3 后自动重新拉列表）  | `POST /api/v1/intelligence/live-news/refresh`  | `refreshLiveNews(params?)`  | `useLiveNews().refresh()`            |
| **查询快讯详情**单条快讯完整内容                    | `GET /api/v1/intelligence/live-news/{item_id}` | `getLiveNewsDetail(itemId)` | —（按需直接调用）                            |
| **按天分组渲染**纯前端逻辑，非接口                   | —                                              | —                           | `useLiveNews().grouped`              |
| **加载更多（翻页）**使用上次响应 `next_cursor`      | 同「查询快讯列表」                                      | `getLiveNews({ cursor })`   | `useLiveNews().loadMore()`           |
| **30 秒自动轮询**前端定时重拉第 1 页               | 同「查询快讯列表」                                      | `getLiveNews(params)`       | `useLiveNews({ autoRefresh: true })` |

***

## 9. 时间维度查询能力

### 9.1 每条资讯是否都带「资讯时间」？→ **是，覆盖率 100%**（实测）

对每个频道拉取 `limit=100` 后的实测结果：

| Tab | channel             | 条数  | 有 `display_time` | 覆盖率      |
| --- | ------------------- | --- | ---------------- | -------- |
| 要闻  | `global-channel`    | 100 | 100              | **100%** |
| A股  | `a-stock-channel`   | 100 | 100              | **100%** |
| 美股  | `us-stock-channel`  | 100 | 100              | **100%** |
| 港股  | `hk-stock-channel`  | 100 | 100              | **100%** |
| 科技  | `tech-channel`      | 100 | 100              | **100%** |
| 商品  | `commodity-channel` | 100 | 100              | **100%** |
| 外汇  | `forex-channel`     | 100 | 100              | **100%** |
| 债券  | `bond-channel`      | 100 | 100              | **100%** |

**兜底源同样 100%**：NewsNow `wallstreetcn-quick` 30 条全部带 `extra.date`。

> 反例（本期不使用）：NewsNow 的**文章源** `wallstreetcn-hot` 覆盖率为 **0%**（`extra=None`）。这正是兜底源**只选** **`wallstreetcn-quick`** **快讯源、不选** **`hot`/`news`** **文章源**的原因。

### 9.2 结论：界面加时间查询条件即可过滤特定某日

**可行**。因为 `published_at` 100% 有值，`date` / `date_from` / `date_to` 参数可直接下推到 SQL 过滤。

| 场景     | 前端操作               | 后端参数                    |
| ------ | ------------------ | ----------------------- |
| 查特定某日  | 日期下拉选 `2026-08-26` | `date=2026-08-26`       |
| 查日期区间  | 自定义起止              | `date_from` + `date_to` |
| 默认（不限） | 日期下拉选「全部」          | 不传日期参数                  |

**实测频道日期分布（limit=100）**

| 频道                          | 100 条覆盖的日期                           | 含义                |
| --------------------------- | ------------------------------------ | ----------------- |
| 要闻 / A股 / 美股 / 港股 / 外汇 / 债券 | 仅 `08-28` 当天                         | 高频频道，100 条约覆盖 1 天 |
| 商品                          | `08-26`20条 / `08-27`38条 / `08-28`42条 | 覆盖约 3 天           |
| **科技**                      | `03-20` \~ `08-28`（**跨度约 5 个月**）     | 低频频道，100 条覆盖数月    |

> ⚠️ **重要提示**：高频频道单次拉取仅覆盖约 1 天，**历史回溯能力完全依赖持续落库累积**。若希望支持「查询 30 天前」，需从启用之日起持续抓取，并合理设置 `news_intel_retention_days`。

### 9.3 时区处理

- 上游 `display_time` 为 **Unix 秒级时间戳**（UTC）
- 落库 `published_at` 统一存 **UTC**
- 前端展示与按日分组按**用户本地时区**转换
- 后端日期过滤参数（`date` / `date_from` / `date_to`）按**服务端时区**解析，需在文档中明确，避免跨时区差一天

***

## 10. 降级策略（官方源 → NewsNow）

### 10.1 降级链

```
官方 /apiv1/content/lives
        │ 失败
        ▼
NewsNow wallstreetcn-quick（项目已内置，0 改造成本）
        │ 失败
        ▼
返回空列表 + degraded:true（绝不 500）
```

### 10.2 降级时的能力差异与前端应对

> **核心问题**：NewsNow 无 8 个频道，它具备**几个**频道？答：**0 个**（只有一条未分类合并流）。

因此**前端 Tab 绝不能硬编码 8 个**，必须由后端驱动：

| 模式                | `GET /live-news/channels` 返回                               | 前端表现                                                                                                                |
| ----------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **正常**（官方源可用）     | 8 个频道                                                      | 渲染 8 个 Tab，与华尔街见闻一致                                                                                                 |
| **降级**（走 NewsNow） | `[{value:'global-channel', label:'要闻'}]` + `degraded:true` | ① **只渲染 1 个 Tab**② 顶部 `InlineTipCard` 提示：「实时源暂不可用，当前为聚合降级数据（无频道分类与重要级）」③ **隐藏「只看重要的」开关**（降级数据无 `score`）④ 不渲染「★重要」标签 |

**实现要点**

| 前端元素             | 正常模式                             | 降级模式               |
| ---------------- | -------------------------------- | ------------------ |
| Tab 数据源          | `useLiveNewsChannels().channels` | 同源，但只有 1 项         |
| 只看重要的 `Checkbox` | 显示可用                             | **隐藏 / 禁用**        |
| ★重要 `Chip`       | 渲染                               | 不渲染                |
| 降级提示条            | 不显示                              | 显示 `InlineTipCard` |
| 频道切换             | 8 个 Tab 可切                       | 仅「要闻」              |

> 设计原则：**上游降级对用户可见、可控**，而非静默丢失功能。

***

## 11. 边界条件与空态处理

| 场景                                     | 处理方式                                               |
| -------------------------------------- | -------------------------------------------------- |
| **科技 Tab 勾选「只看重要的」**实测科技频道重要率 **0/30** | 显示空态文案：**「本频道暂无重要快讯」**，而非空白列表（**已与用户确认**）          |
| 关键词搜索无结果                               | 空态：「未找到与「{keyword}」相关的快讯」                          |
| 指定日期无数据                                | 空态：「{date} 暂无快讯」                                   |
| 上游全部不可用                                | 空态 + 提示：「资讯源暂时不可用，请稍后重试」                           |
| 首次进入无历史数据                              | 空态 + 引导：「正在获取最新快讯…」并自动触发一次刷新                       |
| 降级模式                                   | 顶部提示条（见 §10.2）                                     |
| 快讯 `title` 为空                          | 回退取 `content` 首行截断 300 字符（因 `title` 字段 `NOT NULL`） |
| 滚动加载到底                                 | `next_cursor` 为 `null` 时隐藏「加载更多」                   |

***

## 12. 配置与开关

### 12.1 新增配置项

| 配置项           | 环境变量                                | 类型    | 默认                             | 说明                   |
| ------------- | ----------------------------------- | ----- | ------------------------------ | -------------------- |
| 上游地址          | `WSCN_LIVE_NEWS_BASE_URL`           | str   | `https://api-one.wallstcn.com` | 官方接口基址               |
| 功能开关          | `WSCN_LIVE_NEWS_ENABLED`            | bool  | `true`                         | 关闭则整个快讯能力停用          |
| 抓取间隔          | `WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC` | int   | `300`                          | 按需刷新的节流间隔（秒），`0` = 关闭自动抓取（详见 §4.4） |
| 重要级阈值         | `WSCN_LIVE_NEWS_IMPORTANT_SCORE`    | int   | `2`                            | `score >= 该值` 视为重要   |
| 单页默认条数        | `WSCN_LIVE_NEWS_DEFAULT_LIMIT`      | int   | `30`                           | 列表默认每页条数             |
| 请求超时          | `WSCN_LIVE_NEWS_TIMEOUT_SEC`        | float | `8.0`                          | 单频道请求超时              |
| 是否降级到 NewsNow | `WSCN_LIVE_NEWS_FALLBACK_NEWSNOW`   | bool  | `true`                         | 官方源失败时是否走 NewsNow    |

### 12.2 复用的现有配置

| 配置项                               | 默认值                            | 用途        |
| --------------------------------- | ------------------------------ | --------- |
| `news_intel_retention_days`       | `30`                           | 资讯保留天数    |
| `news_intel_max_items_per_source` | `50`                           | 单源单次的采集上限 |
| `news_intel_auto_fetch_enabled`   | `False`                        | 分析前是否自动拉取 |
| `newsnow_base_url`                | `https://newsnow.busiyi.world` | 兜底源基址     |

> 按项目规范：新增配置项**必须同步更新** **`.env.example`** **与本文档**。

***

## 13. 实施计划

| 阶段                  | 内容                                              | 涉及文件                                                          | 状态     |
| ------------------- | ----------------------------------------------- | ------------------------------------------------------------- | ------ |
| **① 配置**            | 新增 `WSCN_LIVE_NEWS_*` 配置项与解析                    | `src/config.py`、`.env.example`                                | ✅ 已完成  |
| **② Fetcher**       | 8 频道抓取 + cursor 增量 + 翻页 + 超时重试                  | `data_provider/wallstreetcn_live_news.py` 🆕                  | ✅ 已完成  |
| **③ Schema**        | 7 个 Pydantic 模型                                 | `api/v1/schemas/intelligence.py`                              | ✅ 已完成  |
| **④ Service**       | 编排、降级、字段标准化（`importance` / 频道短码 / 秒毫秒换算）       | `src/services/intelligence_service.py`                        | ✅ 已完成  |
| **⑤ Repository**    | 新增 `importance` 列 + 索引 + 迁移；按频道/重要级/日期查询       | `src/repositories/intelligence_repo.py`、`src/storage.py`      | ✅ 已完成  |
| **⑥ API**           | 4 个新路由                                          | `api/v1/endpoints/intelligence.py`                            | ✅ 已完成  |
| **⑦ 刷新策略**          | 按需惰性刷新 + 双闸节流（改为不挂 `runtime_scheduler`，见 §4.4） | `src/services/intelligence_service.py`                        | ✅ 已完成  |
| **⑧ 前端类型 & API**    | 类型定义 + 4 个 API 方法                               | `src/types/liveNews.ts` 🆕、`src/api/liveNews.ts` 🆕           | ✅ 已完成  |
| **⑨ 前端 Hook**       | 2 个 Hook（轮询、分页、防抖、分组）                           | `src/hooks/useLiveNews.ts` 🆕                                 | ✅ 已完成  |
| **⑩ 前端页面**          | 页面 + 路由 + 侧边栏入口 + i18n（中/繁/英）                   | `src/pages/LiveNewsPage.tsx` 🆕、`App.tsx`、`SidebarNav.tsx`    | ✅ 已完成  |
| **⑪ 测试**            | 后端单测 26 例（Fetcher / Service / 降级 / 边界）          | `tests/test_live_news.py` 🆕                                  | ✅ 已完成  |
| **⑫ 文档**            | 本文档按实施结果校准 + `docs/CHANGELOG.md` 追加一行            | 见 §14.4                                                       | ⏳ 待合入时 |

#### 实施中的三处偏差（已同步到对应章节）

| #   | 原方案                          | 实际实现                    | 原因                                      | 详见        |
| --- | ---------------------------- | ----------------------- | --------------------------------------- | --------- |
| 1   | 挂 `runtime_scheduler` tick   | 改为按需惰性刷新                | 该调度器依赖 `schedule_enabled`，会牵连快讯能力        | §4.4      |
| 2   | 注册 2 行数据到 `intelligence_sources` | 改为不注册，走独立链路             | 一条源记录无法表达 8 频道，且会被通用抓取链路误抓               | §5.1      |
| 3   | Schema 放 `src/schemas/`      | 放 `api/v1/schemas/`     | 项目既有 intelligence schema 实际位置在此，保持一致    | §4.1      |

***

## 14. 风险、合规与回滚

### 14.1 风险与缓解

| 风险                        | 等级 | 缓解措施                                                                 |
| ------------------------- | -- | -------------------------------------------------------------------- |
| **官方接口非公开**，无 SLA，可能鉴权或变更 | 高  | ① 自动降级 NewsNow；② `WSCN_LIVE_NEWS_ENABLED` 可一键关闭；③ 请求带合法 UA / Referer |
| 高频请求被限流 / 封禁              | 中  | 默认 5 分钟间隔 + 服务端缓存；各频道串行请求，不并发                                        |
| 上游返回结构变更                  | 中  | 字段全部按**可选**解析（`title` 可空、`score` 缺省为 1），缺失不抛异常                       |
| 科技频道更新慢、无重要级              | 低  | 空态处理（§11）；不影响其他频道                                                    |
| 历史数据丢失（滚动窗口）              | 中  | 持续落库累积；文档明确提示                                                        |
| 时间单位混淆（秒 vs 毫秒）           | 中  | 标准化层统一换算 + 单测覆盖                                                      |
| 前端轮询造成请求压力                | 低  | 页面隐藏时暂停轮询；30s 间隔                                                     |

### 14.2 合规

| 项    | 说明                                          |
| ---- | ------------------------------------------- |
| 内容版权 | 快讯内容版权归华尔街见闻所有                              |
| 存储策略 | 仅存**摘要 + 原文链接**，不在 HermesX 内嵌全文             |
| 跳转   | 卡片点击跳转官方原文 `wallstreetcn.com/livenews/{id}` |
| 文档声明 | 本文档顶部标注数据源与致谢                               |

### 14.3 回滚方式

| 场景      | 回滚动作                                                                     |
| ------- | ------------------------------------------------------------------------ |
| 整体功能回滚  | `git revert` 对应 PR（单一特性单 PR）                                             |
| 仅停上游抓取  | 设 `WSCN_LIVE_NEWS_ENABLED=false` + `WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC=0` |
| 仅下线前端页面 | 移除 `App.tsx` 路由 + `Shell.tsx` 侧边栏入口                                      |
| 数据库回滚   | `importance` 列可空，删除列不影响存量数据；唯一约束未改动                                      |

### 14.4 交付前需同步的文档

| 文档                      | 改动                                                                            |
| ----------------------- | ----------------------------------------------------------------------------- |
| 本文档 `docs/live-news.md` | 实施后按实际落地情况校准                                                                  |
| `docs/CHANGELOG.md`     | `[Unreleased]` 段追加一行（**扁平格式，禁加类目标题**）：`- [新功能] 实时财经快讯中心：华尔街见闻 8 频道快讯流页面与 API` |
| `.env.example`          | 追加 `WSCN_LIVE_NEWS_*` 配置项及说明                                                  |
| PR 描述                   | 按项目规范**必须附页面截图**                                                              |

***

## 15. 命名规范说明

> 已按用户建议，将 `live` 统一调整为 `live_news`，避免与「直播」语义混淆。

| 层次                  | 命名风格                           | 示例                                                                  |
| ------------------- | ------------------------------ | ------------------------------------------------------------------- |
| **后端接口路径**          | kebab-case（REST 惯例）            | `/api/v1/intelligence/live-news/channels`                           |
| **后端方法名**           | snake\_case（Python 惯例）         | `list_live_news()` / `refresh_live_news()` / `live_news_channels()` |
| **数据库列**            | snake\_case                    | `importance`                                                        |
| **前端文件名**           | camelCase                      | `liveNews.ts` / `useLiveNews.ts`                                    |
| **前端 API 方法**       | camelCase + `get`/`refresh` 前缀 | `getLiveNews()` / `getLiveNewsChannels()` / `refreshLiveNews()`     |
| **前端 Hook**         | camelCase + `use` 前缀           | `useLiveNews()` / `useLiveNewsChannels()`                           |
| **前端类型**            | PascalCase                     | `LiveNewsItem` / `LiveNewsChannel` / `LiveNewsResponse`             |
| **前端页面 / 路由**       | PascalCase / kebab-case        | `LiveNewsPage.tsx` / `/live-news`                                   |
| **配置项**             | UPPER\_SNAKE                   | `WSCN_LIVE_NEWS_ENABLED`                                            |
| **source\_type 枚举** | snake\_case                    | `wscn_live_news`                                                    |

***

## 附录 A：实测原始数据快照

- 采集时间：2026-08-28 21:00 \~ 23:10 (UTC+8)
- 官方接口：`https://api-one.wallstcn.com/apiv1/content/lives`
- 兜底接口：`https://newsnow.busiyi.world/api/s?id=wallstreetcn-quick`
- 8 频道均返回 `code=20000`，`limit=100` 生效
- 游标语义：`next_cursor`（时间戳，向下翻更早）、`polling_cursor`（快讯 id，向上拉最新）
- `symbols` 字段实测 **100 条中 0 条有值**，免费接口不返回关联标的

> ⚠️ **个股关联提醒**：`symbols` 无值，若后续要做「快讯命中我的自选股」，只能靠**文本匹配股票名 / 代码**（如「比亚迪」→ `002594`）。该能力列为**后续可选增强**，不混入本期范围。

