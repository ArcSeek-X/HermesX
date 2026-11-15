# <a id="国家字典落表方案"></a>System Countries 国家字典落表方案（评审稿 v3）

> 📝 **方案简述**：将「国家 / 市场字典」从「上游实时拉取 + 进程内存缓存」改为**落库为系统数据字典表 `sys_dict_countries`**，并独立为 **`system` 公共服务**——接口、命名、模块归属均从 `intelligence` / `live-calendar` 解耦，作为可复用的数据字典公共能力。国家信息基本不随时间变动，落表后读取统一走 DB；上游仅作初始播种与偶发对账。`country_id` 与 `currency` 在全项目（出入参、控件、库枚举值）**强制统一为大写**。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-15（v3：读取接口 `/api/v1/system/countries`、旧端点直接删除、包 `src/application/system/`、currency 规范明确）
>
> **状态**：评审稿（未实施）

## 目录

- [一、背景与问题](#一背景与问题)
- [二、设计目标](#二设计目标)
- [三、表设计](#三表设计)
- [四、全项目统一大写规范（country_id / currency）](#四全项目统一大写规范country_id--currency)
- [五、落表后的服务端接口（独立 system 服务）](#五落表后的服务端接口独立-system-服务)
- [六、数据同步与初始化](#六数据同步与初始化)
- [七、前端组件 option 来源的影响](#七前端组件-option-来源的影响)
- [八、影响文件清单](#八影响文件清单)
- [九、迁移、回滚与未决项](#九迁移回滚与未决项)

---

## <a id="一背景与问题"></a>一、背景与问题

当前国家字典的链路（见 `data_provider/calendar/wallstreetcn_source.py`、`src/application/intelligence/intelligence_service.py::list_calendar_countries`）：

1. 前端 `CountryMarketSelect` 经 `useLiveCalendarCountries` → `GET /api/v1/intelligence/live-calendar/countries` 获取 `CountryMarketOptionDef[]`；
2. 后端 `list_calendar_countries()` **每次先读进程内存缓存（TTL 默认 86400s），未命中再调上游** `GET https://api-one-wscn.awtmt.com/apiv1/finance/countries`；
3. **全仓无任何国家主数据表**：上游挂了/降级，`degraded=True` 且返回空 `items`；`flag_uri` 为上游远程 URL，未本地化；
4. **`country_id` / `currency` 大小写隐含约定**：上游给大写、服务层查表时 `.upper()` 兜底，但 `currency` 在取数侧仅 `.strip()` 未强制大写；缺少全局强制规范，存在混用风险。

问题：国家是低频静态数据却每次回源 + 内存缓存，链路脆弱；无单一真源表，上游异常无法兜底；`country_id` / `currency` 取值未在全项目统一。

---

## <a id="二设计目标"></a>二、设计目标

1. **落表为系统数据字典表** `sys_dict_countries`：读取统一走 DB，不再每次回源。
2. **独立为 system 公共服务**：接口、命名、模块归属从 `intelligence` / `live-calendar` 解耦，作为可复用的数据字典公共能力（后续同类字典可同址扩展）。
3. **单一真源 + 规范归一**：`country_id` 与 `currency` 在全项目强制统一为大写（出入参、控件、库枚举值一致）。
4. **上游降级可读**：DB 非空时即使上游不可用，国家列表仍可正常返回（`degraded` 仅在「库空且上游失败」时为真）。
5. **软禁用而非硬删**：上游下线的国家用 `is_active=False` 标记，避免破坏历史日历事件中仍引用的 `country_id`。

---

## <a id="三表设计"></a>三、表设计

### 表名

`sys_dict_countries`（系统数据字典表之一；前缀 `sys_dict_` 表明其归属「系统数据字典」公共域，与具体业务域解耦）。

### 表结构（DDL 草案，SQLite / 通用 SQL）

```sql
CREATE TABLE sys_dict_countries (
  id            INTEGER      PRIMARY KEY AUTOINCREMENT,
  country_id    VARCHAR(8)   NOT NULL,                 -- 国家/市场代码（规范大写，如 US/CN/HK），唯一业务键
  country_name  VARCHAR(64)  NOT NULL,                 -- 国家/地区中文名（如 美国/中国/香港）
  currency      VARCHAR(8)   NOT NULL DEFAULT '',      -- 货币 ISO 4217 代码（规范大写，如 USD/CNY/HKD）
  currency_name VARCHAR(32)  NOT NULL DEFAULT '',      -- 货币中文名（如 美元/人民币/港币）
  flag_uri      VARCHAR(512) NOT NULL DEFAULT '',      -- 国旗图片远程 URL（沿用上游，未本地化）
  source        VARCHAR(32)  NOT NULL DEFAULT 'wallstreetcn', -- 数据来源（当前仅 wallstreetcn）
  is_active     BOOLEAN      NOT NULL DEFAULT 1,       -- 是否启用：上游下线置 0，不硬删
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (country_id)
);
CREATE INDEX ix_sys_dict_countries_active ON sys_dict_countries (is_active);
```

> 字段命名与类型对齐仓库约定（见 `models/intelligence.py`、`models/recent_search.py`）：surrogate `id` 自增主键 + 业务唯一键；时间列 `datetime.now`/`utc_naive_now`；查询列加 `index=True`。模型置于 `src/infrastructure/persistence/models/system_dict.py`，注册到仓库唯一 `Base`，并在 `models/__init__.py` 导入以被 `create_all()` 识别。

### 字段映射（→ 前端 `CountryMarketOptionDef`）

| 表字段 | 类型 | 非空 | 说明 | 前端字段 |
| --- | --- | --- | --- | --- |
| `id` | Integer | PK | 自增代理主键 | — |
| `country_id` | String(8) | ✅ UNIQUE | **规范大写**国家代码 | `countryMarketId` |
| `country_name` | String(64) | ✅ | 中文名 | `countryMarketName` |
| `currency` | String(8) | 默认 `''` | **大写** ISO 4217 货币码 | `currency` |
| `currency_name` | String(32) | 默认 `''` | 货币中文名 | `currencyName` |
| `flag_uri` | String(512) | 默认 `''` | 国旗远程 URL（存上游原值） | `flagUri` |
| `source` | String(32) | 默认 `wallstreetcn` | 上游来源标识 | — |
| `is_active` | Boolean | 默认 `True` | 软禁用开关 | —（查询仅返回 `True`） |
| `created_at` / `updated_at` | DateTime | ✅ | 审计时间 | — |

### 枚举 / 取值规范

| 字段 | 取值规范 | 示例 |
| --- | --- | --- |
| `country_id` | **大写、去空格、截断 8 字符**；ISO 3166-1 alpha-2 风格 | `US`、`CN`、`HK`、`JP`、`GB`、`DE`、`FR`、`KR`、`SG` |
| `currency` | **大写** ISO 4217 | `USD`、`CNY`、`HKD`、`JPY`、`EUR`、`GBP` |
| `source` | 上游 source id 字符串 | `wallstreetcn`（当前唯一；预留多源扩展） |
| `is_active` | `1` / `0` | 默认 `1` |

---

## <a id="四全项目统一大写规范country_id--currency"></a>四、全项目统一大写规范（country_id / currency）

**全局约定：项目中 `country_id` 与 `currency` 一律为「大写」；小写一律视为非规范。**

### 4.1 country_id

- **规范值**：大写 2 字母（ISO 3166-1 alpha-2 风格），美国 = `US`、中国 = `CN`、香港 = `HK`。
- **统一范围（出入参、控件、库枚举值一致）**：
  1. **库枚举值**：`sys_dict_countries.country_id` 存大写、UNIQUE，即成全项目唯一规范源；
  2. **入参（同步/播种）**：写库前 `country_id = (raw.get('country_id') or '').strip().upper()`，空值拒入；
  3. **出参（读取 API）**：响应 `country_id` 为大写；前端 `CountryMarketOptionDef.countryMarketId` 即大写；
  4. **控件选择**：`CountryMarketSelect` 的 `value` / `onChange` 回传的 `countryMarketId` 数组恒为大写；
  5. **消费端比较**：日历事件过滤（`event.country_id`）、指标视图筛选等一律按大写比较；既有 `intelligence_service` 中 `.strip().upper()` 兜底调用可保留为防御式无操作，后续清理时可移除，但**不得再引入小写分支**。

> 既有日历事件行 `country_id` 已是上游大写，落表后字典与其天然对齐，无需回填事件表。此前对话中举例的 `cn/us/hk` 小写均非规范，统一为大写。

### 4.2 currency / currency_name

- **华尔街见闻上游返回什么**：上游 `/apiv1/finance/countries` 对每条国家返回原始字段 `currency`（货币代码）与 `currency_name`（货币中文名）。代码 `WallstreetcnCalendarFetcher.fetch_countries`（`data_provider/calendar/wallstreetcn_source.py:164`）对这两个字段**仅做 `.strip()`，未做大小写归一**。实际观测中上游 `currency` 即 ISO 4217 大写码（如 `USD`/`CNY`/`HKD`），`currency_name` 为对应中文名（如 `美元`/`人民币`/`港币`）。
- **规范（已确认）**：
  - `currency`：**统一大写**，写库前 `currency = (raw.get('currency') or '').strip().upper()`，与 `country_id` 同口径；出参、控件展示、库枚举值均大写。
  - `currency_name`：为展示用中文名，大小写无关，**原样存储**（不强制转换）。
- **全项目一致性**：任何读取/展示货币代码的地方使用大写 `currency`；若后续新增「货币」相关控件，其 `value` 亦用大写码，避免与 `country_id` 出现口径分裂。

---

## <a id="五落表后的服务端接口独立-system-服务"></a>五、落表后的服务端接口（独立 system 服务）

国家字典升级为**系统数据字典公共能力**，从 `intelligence` / `live-calendar` 完全解耦：独立服务模块、独立 API 命名空间、独立模型/仓储。

### 5.1 服务与模块归属（新增，不与 intelligence 耦合）

| 层 | 位置 | 职责 |
| --- | --- | --- |
| 模型 | `src/infrastructure/persistence/models/system_dict.py` | `SysDictCountry`（表 `sys_dict_countries`） |
| 仓储 | `src/infrastructure/persistence/repositories/system_dict_repository.py` | `list_active_countries()`、`upsert_countries(rows)` |
| 服务 | `src/application/system/system_dict_service.py` | `list_countries()`（DB-first）、`sync_countries()`（回源对账） |
| 上游源 | `data_provider/system/system_countries_source.py`（适配层） | 复用既有 `WallstreetcnCalendarFetcher.fetch_countries()`，封装为「国家字典可插拔源」端口 |
| API | `api/v1/endpoints/system.py` | 路由前缀 `/api/v1/system` |

> 依赖方向：`api → application/system → infrastructure(persistence/repositories) + data_provider(source)`；`intelligence` / `live-calendar` **不再持有**国家字典逻辑，改为在需要时调用 `SystemDictService`（内部方法），不再暴露自己的 `/countries` 端点。

### 5.2 读取接口（新，独立命名空间）

**`GET /api/v1/system/countries`**

- **鉴权**：公开可读（数据字典属公共基础能力；如需限制可加只读鉴权，与现有日历接口同级）。
- **请求**：无参数。
- **响应** `SystemDictCountriesResponse`：

```json
{
  "items": [
    {
      "country_id": "US",
      "country_name": "美国",
      "currency": "USD",
      "currency_name": "美元",
      "flag_uri": "https://.../us.png"
    }
  ],
  "degraded": false
}
```

- **行为**（`SystemDictService.list_countries` DB-first）：
  1. 读 `sys_dict_countries WHERE is_active = 1`；前端按拼音重排，库顺序无关，故不额外排序；
  2. 若表为空（首跑 / 全禁用）→ 调上游源 `fetch_countries`，**幂等 upsert** 入库后返回；
  3. `degraded`：仅当「库空 **且** 上游失败」时置 `True`；库有数据则 `False`。

### 5.3 同步接口（新，独立命名空间）

**`POST /api/v1/system/countries/sync`**

- **用途**：初始播种 + 周期对账（上游当前国家集合写入/更新字典；上游消失者 `is_active` 置 `0`）。
- **鉴权**：受保护 / 仅管理员（与现有 `refresh` 接口同级）。
- **请求**：无 body（或可选 `{ "force": false }`）。
- **响应**：

```json
{
  "upserted": 42,
  "deactivated": 1,
  "degraded": false
}
```

- **行为**：拉上游 → 对 `country_id` 做 upsert（存在则更新 `country_name/currency/currency_name/flag_uri/source/updated_at`，不存在则插入）；上游不再出现且库中存在者置 `is_active=0`；返回影响计数。

### 5.4 与 intelligence / live-calendar 的解耦

- **直接删除** `GET /api/v1/intelligence/live-calendar/countries` 端点；`IntelligenceService.list_calendar_countries` 与进程内存缓存逻辑**一并移除**。
- 所有原调用方（特别是前端 `useLiveCalendarCountries`）**切换到新接口** `GET /api/v1/system/countries`。
- 若 `live-calendar` 内部仍需国家列表（事件过滤 UI），改为调用 `SystemDictService.list_countries()`（同进程内部调用），**不再对外暴露自己的国家端点**。
- 既有日历事件行 `country_id` 不变，与字典 `country_id` 对齐；无外键约束（loose reference，对齐仓库风格如 `intelligence_items.source_id` 可空）。

---

## <a id="六数据同步与初始化"></a>六、数据同步与初始化

- **懒播种**：`list_countries` 在「表空」时自动从上游 upsert 种子数据，首次调用即完成初始化（幂等）。
- **显式对账**：`POST /system/countries/sync` 供手动或定时任务调用；建议挂在现有运维 / 定时链路（参考 `refreshLiveCalendar`）。
- **不回写事件表**：事件 `country_id` 已是规范大写，不依赖字典表存在，无外键。
- **`flag_uri` 存上游原值**：本期沿用上游远程 URL，不本地化（如需离线可用，后续可下载到 `public/` 并改存相对路径，属可选增强）。

---

## <a id="七前端组件-option-来源的影响"></a>七、前端组件 option 来源的影响

- `CountryMarketSelect` 组件本身**仍不解耦数据源**：只消费 `options: CountryMarketOptionDef[]` 入参，因此组件**无需改动**。
- **但其数据来源 hook 必须改**：原 `useLiveCalendarCountries`（`hooks/useLiveCalendar.ts`）+ `getLiveCalendarCountries`（`api/liveCalendar.ts`）指向旧 `/live-calendar/countries`，现需**重指向新独立接口** `GET /api/v1/system/countries`：
  - 新增 `apps/hrs-web/src/api/systemCountries.ts`：`getSystemCountries()`（归一 camelCase 同前）；
  - 新增/改造 hook（如 `hooks/useSystemCountries.ts` 或复用并改名 `useLiveCalendarCountries` → `useCountryDictionary`），返回 `CountryMarketOptionDef[]`；
  - 所有调用方（`StockMetricViewFilterBar`、`LiveCalendarFilter`、任何用 `CountryMarketSelect` 的地方）改用新 hook。
- 控件输出 `countryMarketId` / `currency` 恒为大写，与全项目大写规范一致，调用方无需再转大小写。

---

## <a id="八影响文件清单"></a>八、影响文件清单

| 文件 | 改动 |
| --- | --- |
| `src/infrastructure/persistence/models/system_dict.py` | **新增** `SysDictCountry` 模型（表 `sys_dict_countries`） |
| `src/infrastructure/persistence/models/__init__.py` | 导入新模型以注册 `Base` |
| `src/infrastructure/persistence/repositories/system_dict_repository.py` | **新增** 仓储方法 |
| `src/application/system/system_dict_service.py` | **新增** `SystemDictService`（DB-first 读取 + 同步） |
| `data_provider/system/system_countries_source.py` | **新增** 上游源适配（复用 `WallstreetcnCalendarFetcher.fetch_countries`） |
| `api/v1/endpoints/system.py` | **新增** 路由（前缀 `/api/v1/system`）：读 `/countries`、同步 `/countries/sync` |
| `api/v1/endpoints/intelligence.py` | **删除** `GET /live-calendar/countries` 端点 |
| `src/application/intelligence/intelligence_service.py` | **移除** `list_calendar_countries` 与内存缓存；内部如需国家列表改调 `SystemDictService` |
| `apps/hrs-web/src/api/systemCountries.ts` | **新增** `getSystemCountries()` |
| `apps/hrs-web/src/hooks/useSystemCountries.ts` | **新增/改造** 国家字典 hook |
| `apps/hrs-web/src/pages/Stock/StockMetricViewPage/components/StockMetricViewFilterBar.tsx` | 改用新 hook |
| `apps/hrs-web/src/components/common/LiveCalendar/LiveCalendarFilter.tsx` | 改用新 hook |
| `documents/product/行情资讯/Live-calendar.md` | 同步 §2/§7：国家字典来源改为 system 字典，旧端点移除 |

> `CountryMarketSelect.tsx` 自身不改；仅其数据提供 hook 与调用方改指向新接口。

---

## <a id="九迁移回滚与未决项"></a>九、迁移、回滚与未决项

- **建表**：依赖仓库既有 `Base.metadata.create_all()`（仅建缺失表）+ `schema_compat` 兜底；新增模型在 `models/system_dict.py` 注册并确保 `models/__init__` 导入，启动即自动建表。无需 Alembic 迁移脚本。
- **回滚**：删除 `SysDictCountry` 模型并 `DROP TABLE sys_dict_countries`、回退 `api/system.py` 与前端 hook 到旧 `/live-calendar/countries` 即可；前端改动可随 hook 回退消解。
- **已决**：
  - 表名 = `sys_dict_countries`；
  - 独立为 `system` 服务，接口命名空间 `/api/v1/system`，读取 `GET /countries`、同步 `POST /countries/sync`；
  - 旧 `/live-calendar/countries` **直接删除**，调用方切到新接口；
  - 包结构 `src/application/system/`（含 `system_dict_service.py`）；上游源 `data_provider/system/system_countries_source.py`；
  - `country_id` 与 `currency` 全项目统一大写（写库前 `.strip().upper()`，同口径）；`currency_name` 原样存中文；库顺序无关（前端按拼音重排）；`flag_uri` 存上游 URL。
- **待评审（剩余）**：无。所有设计决策均已确认，方案可定稿进入实现。
