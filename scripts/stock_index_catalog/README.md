# <a id="stock-index-catalog-readme"></a>stock_index_catalog 目录说明

> 📝 **简介**：本目录是「前端股票搜索自动补全索引」的离线生成工具集——负责从数据源抓取股票基础资料清单、生成压缩索引 `apps/hrs-web/public/stocks.index.json`，并同步到前端/桌面构建产物。与运行时的行情/分析数据源（`data_provider/**/tushare_*.py`）无关。
>
> 👤 **维护**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-10

## 目录

- [一、这个目录是做什么的](#sec-1)
- [二、目录结构与文件职责](#sec-2)
  - [2.1 顶层脚本](#sec-2-1)
  - [2.2 `fetcher/` 抓取器目录](#sec-2-2)
  - [2.3 `static_markets/` 静态兜底市场](#sec-2-3)
- [三、数据流与依赖关系](#sec-3)
- [四、如何执行](#sec-4)
  - [4.1 前置条件](#sec-4-1)
  - [4.2 一键执行（推荐）](#sec-4-2)
  - [4.3 分步执行与常用参数](#sec-4-3)
  - [4.4 增量合并（不重建整份索引）](#sec-4-4)
- [五、新增一个数据源（在 `fetcher/` 下扩展）](#sec-5)
- [六、常见问题与注意事项](#sec-6)

<a id="sec-1"></a>

## 一、这个目录是做什么的

前端 `StockSearch` 组件在用户输入股票代码 / 名称 / 拼音时，是在静态文件 `apps/hrs-web/public/stocks.index.json` 中做本地模糊匹配（见 `src/utils/stockIndexLoader.ts` 的 `unpackTuples`）。**前端能搜到哪些股票，完全取决于这个索引文件最后一次生成时包含的内容。**

本目录把"生成这个索引"需要的脚本集中管理，职责覆盖三步：

1. **抓取**：从数据源（默认 Tushare）拉取 A 股 / 港股 / 美股的股票基础资料。
2. **生成**：把 CSV 清单转换成压缩元组数组索引（含名称规范化、拼音/别名、市场判定、`listDate`）。
3. **同步**：把生成的索引同步到 `dist-web/static/`（桌面端构建产物），避免重新 `npm run build`。

> ❗ 与 `data_provider/**/tushare_*.py`（运行时 K 线、实时报价、财务等行情系统）**不是一条线**，后者不参与前端搜索索引的生成。

<a id="sec-2"></a>

## 二、目录结构与文件职责

<a id="sec-2-1"></a>

### 2.1 顶层脚本

| 文件 | 作用 | 是否直接调外部 API |
|---|---|---|
| `refresh_stock_index.py` | **一键入口 / 编排器**。串联「抓取 → 生成 → 同步 `dist-web`」三步，本身不直接发请求。 | ❌ 否 |
| `generate_index_from_csv.py` | **核心生成器（全量重建）**。读取各源 CSV，做名称规范化、拼音/别名、市场判定、压缩为元组数组，**覆盖写** `apps/hrs-web/public/stocks.index.json`；缺哪份 CSV 就丢哪个市场。 | ❌ 否 |
| `merge_stock_index_from_csv.py` | **增量合并器（打补丁）**。按 `--cn / --bse / --hk / --us / --jp / --kr` 指定市场，保留现有索引每条记录，只做「加条目」与「补字段缺省值」；新条目按市场分段插入，`listDate` 统一为 `YYYY-MM-DD`；不依赖其它市场 CSV 是否齐全。 | ❌ 否 |
| `reorder_stock_index.py` | **排序后处理器（不增不减）**。按「市场分组 → A股交易所 → 上市日期升序」重排现有索引，**不改记录数、不改字段值**；排序规则由 `index_sort.py` 统一提供，`merge` 在写盘前也会自动调用同一规则（见 [§2.4](#sec-2-4)）。 | ❌ 否 |

**三种索引写盘脚本的区别（务必看清）**：

| 类别 | 脚本 | 行为 | 适用场景 |
|---|---|---|---|
| **全部替换（全量重建）** | `refresh_stock_index.py`（编排）→ `generate_index_from_csv.py` | 从 CSV **重新生成整份索引并覆盖写**；索引里有但 CSV 里没有的记录会丢失 | 数据源齐全、需要整体刷新 |
| **增量更新（打补丁）** | `merge_stock_index_from_csv.py` | **保留现有索引每一条**，只「加新条目 / 补字段缺省值」 | 只更新部分市场（如本次北交所 +41 只） |
| **仅排序（不增不减）** | `reorder_stock_index.py` | **既不新增、也不删除、不修改任何字段**，只调整记录排列顺序 | 产出后做规范化排序（[§2.4](#sec-2-4)） |

> 🔑 一句话：`refresh` / `generate` = 推倒重来；`merge` = 打补丁；`reorder` = 重新排队。
> ⚠️ 增量合并是「打补丁」，下次 `refresh` 全量重建会覆盖它（见 [§4.4](#sec-4-4)）。

<a id="sec-2-2"></a>

### 2.2 `fetcher/` 抓取器目录

每个数据源一个脚本，产出结构一致的 `data/stock_index_catalog/stock_list_*.csv`。其中 A 股按交易所拆成两份：沪深写 `stock_list_cn.csv`、北交所写 `stock_list_bse.csv`，生成器分别按 `CN` / `BSE` 市场组装。

| 文件 | 作用 |
|---|---|
| `fetcher/fetch_tushare_stock_list_all.py` | **唯一真正调用 Tushare 的脚本**。调 `pro.stock_basic` / `pro.hk_basic` / `pro.us_basic`，写入 `data/stock_index_catalog/stock_list_{cn,bse,hk,us}.csv`（A 股按 `ts_code` 后缀拆成沪深 `.SH`/`.SZ` 与北交所 `.BJ`）；支持 `--a-rk`（用 `rt_k` 修正**沪深** A 股 `XD/XR/DR/N/C` 前缀名称，北交所不参与）。**Tushare 专属**，换源需替换。 |
| `fetcher/fetch_baostock_stock_list_cn.py` | **沪深 A 股的替代数据源**。调 `baostock.query_stock_basic()`（免费、无需 token、需联网），过滤 `type=1 且 status=1`，只产出 `data/stock_index_catalog/stock_list_cn.csv`；列名与 Tushare CSV 完全一致，并提供真实上市日期 `list_date`。范围严格为 `cn`，不产出其它市场文件。 |
| `fetcher/fetch_akshare_stock_list_bse.py` | **北交所 A 股的替代数据源**。调 `akshare.stock_info_bj_name_code()`（免费、无需 token、需联网），只产出 `data/stock_index_catalog/stock_list_bse.csv`；列名与 Tushare CSV 完全一致，并提供真实上市日期 `list_date`。范围严格为 `bse`，与 Tushare 拆分出的同名文件**可互换**（二者取其一即可，单独运行会覆盖）。 |

> 💡 **命名规范**：`fetch + 数据源 + stock_list + 范围`，例如 `fetch_tushare_stock_list_all.py`（`all` 表示全市场）、`fetch_baostock_stock_list_cn.py`（`cn` 表示沪深）。想加新数据源时，在 `fetcher/` 下按此规范新增 `fetch_<source>_stock_list_<scope>.py` 即可（见 [§5](#sec-5)）。

> ⚠️ **baostock 抓取器的两个边界（重要）**：
> - **未登记**到 `refresh_stock_index.py` 的 `FETCHER_SCRIPTS`，需单独运行。因为 `--fetch-source` 是整条索引链路的全局源，而 baostock 只覆盖沪深，直接接入会牵连港 / 美 / 日 / 韩数据。单独运行生成 CSV 后，补齐其它市场 CSV 再走 `generate_index_from_csv.py` 全量重建；若只有沪深这一份，改走 [§4.4](#sec-4-4) 的增量合并，**不要**直接全量重建。
> - **`list_date` 源格式不同、索引格式统一**：baostock 的 `ipoDate` 是 `YYYY-MM-DD`，Tushare 的 `list_date` 是 `YYYYMMDD`，akshare 的 `上市日期` 是 `YYYY-MM-DD`；CSV 保留各自源格式，由生成器 / 合并器在写索引第 11 列 `listDate` 时统一规范化为 `YYYY-MM-DD`（符合前端 `stockIndex.ts` 约定）。因此三类来源的 CSV **可以自由混用**，无需额外转换。
> - **`fetch_akshare_stock_list_bse.py`** 同样未登记 `FETCHER_SCRIPTS`：它只覆盖北交所，且生成的就是 `stock_list_bse.csv`（与 Tushare 拆分出的同名文件可互换）；单独运行会覆盖该文件，故不接入 `refresh` 的全局源。

<a id="sec-2-3"></a>

### 2.3 `static_markets/` 静态兜底市场

Tushare **没有**日本 / 韩国接口，因此 JP/KR 永远走这里的静态文件，它们是 JP/KR 的唯一权威源。

| 文件 | 作用 |
|---|---|
| `static_markets/stock_list_jp.csv` | 日本市场股票清单（代码 / 名称 / 上市日期等，格式与抓取 CSV 同构）。 |
| `static_markets/stock_list_kr.csv` | 韩国市场股票清单。 |

> ⚠️ 不要在 `refresh` 正常流程中删除这两个文件，否则 JP/KR 搜索将缺数据。

<a id="sec-2-4"></a>

### 2.4 索引排序规范（reorder_stock_index.py）

`stocks.index.json` 的**规范排序**由 `index_sort.py` 统一实现（`sort_records()`），`reorder_stock_index.py` 与
`merge_stock_index_from_csv.py` 共用——前者是按需纯重排工具；后者在**每次合并写盘前**自动调用，保证增量合并的输出也符合规范。规则如下：

1. **顶层市场分组顺序**：A股（上证 `.SH` → 深圳 `.SZ` → 北交所 `.BJ`）、HK、US、JP、KR。
   - A股把 `CN`（沪深）与 `BSE`（北交所）合并为一组，组内再按交易所细分。
2. **A股内部交易所顺序**：上海（`SH`）→ 深圳（`SZ`）→ 北京 / 北交所（`BJ`），按 `canonicalCode` 后缀判定。
3. **组内按上市日期升序**：每个市场 / 交易所分组内，按第 11 列 `list_date`（`YYYY-MM-DD`）从早到晚排序；
   无日期 / 非法日期的记录排在**该分组末尾**。

> 该脚本只调整记录顺序、不改任何字段值，且复用 generate / merge 的紧凑排版，重复执行结果稳定。
> 前端 `stockIndex.ts` 按 `canonicalCode` 建字典检索，顺序无关，重排不影响功能。

```bash
python3 scripts/stock_index_catalog/reorder_stock_index.py
```

<a id="sec-2-5"></a>

### 2.5 CSV 统一格式（stock_list_*.csv）与字段说明

所有由抓取器产出的 CSV（`stock_list_cn.csv` / `stock_list_bse.csv` / `stock_list_hk.csv` / `stock_list_us.csv`）
共用**同一套 17 列表头**，列名与顺序完全等同于 Tushare `stock_basic` 的字段集。这样
`generate_index_from_csv.py` / `merge_stock_index_from_csv.py` 无需关心来源即可统一消费，不同来源的 CSV 也可
自由混用。文件为 `utf-8-sig` 编码、首行为表头、逗号分隔。

| 列名 | 含义 | 取值 / 说明 |
|---|---|---|
| `ts_code` | 唯一代码（带交易所后缀） | `600519.SH` / `000001.SZ` / `920000.BJ` / `00700.HK` / `AAPL` / `7203.T` / `005930.KS` |
| `symbol` | 展示代码（去后缀或裸代码） | `600519` / `000001` / `920000` / `00700` / `AAPL` |
| `name` | 证券名称（中文） | `贵州茅台` |
| `area` | 地区 | `贵州` |
| `industry` | 所属行业 | `白酒` |
| `fullname` | 公司全称 | 英文 / 中文全称 |
| `enname` | 英文名称 | `Kweichow Moutai Co., Ltd.` |
| `cnspell` | 中文拼音 | 全拼 |
| `market` | 市场中文标签 | `主板` / `科创板` / `创业板` / `北交所` 等（生成器不消费，仅用于可读性） |
| `exchange` | 交易所代码 | `SSE` / `SZSE` / `BSE` 等 |
| `curr_type` | 交易币种 | `CNY` / `USD` / `HKD` |
| `list_status` | 上市状态 | `L` = 上市；`D` = 退市 |
| `list_date` | 上市日期 | 源格式可能是 `YYYYMMDD`（Tushare）或 `YYYY-MM-DD`（baostock / akshare）；写索引时统一规范化为 `YYYY-MM-DD` |
| `delist_date` | 退市日期 | 空或 `YYYY-MM-DD` |
| `is_hs` | 沪深港通标识 | `H` / `S` / 空 |
| `act_name` | 实际控制人 | 空或名称 |
| `act_ent_type` | 实际控制人类型 | 空或类型 |

> **生成器实际消费的字段**：`parse_stock_row` 只读取 `ts_code / symbol / name / aliases / list_date` 五类，
> 其余（拼音、别名、市场、交易所等）由代码后缀与内置规则推导，或在生成阶段补全。因此 CSV 即使只填其中部分列
> （如 baostock / akshare 仅填充子集、静态 JP/KR 种子仅 5 列）也能被正常消费。
> **静态 JP/KR 例外**：`static_markets/stock_list_{jp,kr}.csv` 是手工维护的 **5 列子集**
> （`ts_code, symbol, name, enname, aliases`），并非完整 17 列表头，但生成器同样兼容。

<a id="sec-2-6"></a>

### 2.6 CSV 数据源与字段覆盖

生成 `stock_list_*.csv` 的数据源如下，**不同源覆盖的字段差异明显**（✓ 填充 / — 留空 / △ 部分市场有值）：

| 字段 / 数据源 | Tushare | baostock | akshare | 静态 JP·KR（种子） |
|---|---|---|---|---|
| `ts_code` | ✓ | ✓ | ✓ | ✓ |
| `symbol` | ✓ | ✓ | ✓ | ✓ |
| `name` | ✓ | ✓ | ✓ | ✓ |
| `area` | △ | — | ✓ | — |
| `industry` | △ | — | ✓ | — |
| `fullname` | △ | — | — | — |
| `enname` | ✓ | — | — | ✓ |
| `cnspell` | ✓ | — | — | — |
| `market` | △ | ✓ | ✓ | — |
| `exchange` | ✓ | ✓ | ✓ | — |
| `curr_type` | ✓ | — | — | — |
| `list_status` | ✓ | ✓ | ✓ | — |
| `list_date` | ✓ | ✓ | ✓ | — |
| `delist_date` | ✓ | — | — | — |
| `is_hs` | △ | — | — | — |
| `act_name` | △ | — | — | — |
| `act_ent_type` | △ | — | — | — |

图例：
- **✓ 填充**：该源稳定提供此字段。
- **— 留空**：该源不提供，CSV 中留空（生成器以空值兼容）。
- **△ Tushare 部分市场**：A股 / 港股 / 北交所经 `stock_basic` 返回**完整 17 列**；美股经 `us_basic` 不返回
  `area / industry / fullname / market / is_hs / act_name / act_ent_type`（留空）。

各源范围与覆盖程度：
- **Tushare**（`fetch_tushare_stock_list_all.py`）：唯一**全市场**源（沪深 / 北交所 / 港股 / 美股）。A股 / 港股 / 北交所为完整 17 列；美股经 `us_basic` 仅部分字段。需 token，已登记 `refresh` 的 `FETCHER_SCRIPTS`。
- **baostock**（`fetch_baostock_stock_list_cn.py`）：仅**沪深 CN**，填充 7 列（`ts_code / symbol / name / market / exchange / list_status / list_date`）。免费、无需 token；未登记 `refresh`（只覆盖沪深）。
- **akshare**（`fetch_akshare_stock_list_bse.py`）：仅**北交所 BSE**，填充 9 列（`ts_code / symbol / name / area / industry / market / exchange / list_status / list_date`）。免费、无需 token；未登记 `refresh`（只覆盖北交所）。
- **静态 JP·KR**（`static_markets/stock_list_{jp,kr}.csv`）：Tushare **无**日 / 韩接口，故为手工维护的 5 列种子文件（无 API），是 JP/KR 的唯一权威源，生成器直接读取。

<a id="sec-2-7"></a>

### 2.7 索引副本清单（路径 / 用途 / 来源）

`stocks.index.json` 只有**一份真身**由 generate / merge 产出，其余都是为不同运行环境保留的本地拷贝：

| 副本路径 | 用途 | 来源 / 生成方式 |
|---|---|---|
| `apps/hrs-web/public/stocks.index.json` | **真身**；Vite dev server 与后端 `api/app.py` 直接提供前端自动补全索引 | `generate_index_from_csv.py` / `merge_stock_index_from_csv.py` 唯一产出（git 跟踪） |
| `dist-web/static/stocks.index.json` | 生产 web 构建产物内嵌副本 | `refresh_stock_index.py` 的 `_sync_static_index()`（仅此一份）；或 `merge --sync-copies` |
| `dist-desktop/frontend/static/stocks.index.json` | 桌面端 web 前端构建产物内嵌副本 | `merge --sync-copies`（仅当目标已存在时刷新） |
| `apps/hrs-desktop/dist/mac-arm64/.../HermesX.app/.../static/stocks.index.json` | 发布版 macOS App 内副本（无需联网） | `merge --sync-copies`（仅当目标已存在时刷新，不会凭空创建 App bundle 目录） |
| `data/cache/stocks.index.json` | **运行时远程缓存**：后端运行期从 GitHub raw URL 拉取最新索引、校验后原子写入（TTL 48h） | `src/application/quote/stock_index_remote_service.py`；也可由 `merge --sync-copies` 刷新 |
| `src/data/cache/stocks.index.json` | **历史遗留**同步目标 | 原在 `merge` 的 `COPY_TARGETS` 中，已移出同步列表并删除该文件（目录为空、无任何代码读取，可一并删除） |

**运行期读取优先级**（`src/data/stock_index_loader.py`）：优先 `data/cache/`（远程缓存，平局权重最高），
兜底 `dist-web/static/`（或 `HRS_STATIC_DIR` 环境变量指向的桌面包内目录）。即运行中的后端默认用远程缓存那份；
若 `data/cache/` 不存在才回退到构建内嵌副本。

<a id="sec-3"></a>

## 三、数据流与依赖关系

```text
fetcher/fetch_tushare_stock_list_all.py --a-rk
        │  写入（A 股按交易所拆成两份）
        ▼
data/stock_index_catalog/
    stock_list_cn.csv      沪深 A 股（.SH / .SZ；--a-rk 只修正这份）
    stock_list_bse.csv     北交所 A 股（.BJ）
    stock_list_hk.csv      港股
    stock_list_us.csv      美股
        │  （/data/ 被 git 忽略，本地按需生成）
static_markets/stock_list_{jp,kr}.csv   （JP/KR 始终走静态兜底，无上游）
        │
        ▼
generate_index_from_csv.py --source tushare
        │  写出
        ▼
apps/hrs-web/public/stocks.index.json
        │  （若前端已构建）同步
        ▼
dist-web/static/stocks.index.json
```

> `stock_list_cn.csv` 有两个可选来源：Tushare 抓取器（随 `refresh` 全链路产出）或 `fetcher/fetch_baostock_stock_list_cn.py`（单独运行）。两者列名同构；`list_date` 源格式不同，但写索引时统一为 `YYYY-MM-DD`，见 [§2.2](#sec-2-2)。

**关键依赖：**

- `pypinyin`：`generate_index_from_csv.py` 必装，否则直接退出（用于生成拼音/简拼搜索键）。
- `tushare` + `.env` 中的 `TUSHARE_TOKEN`：仅抓取阶段需要；账号积分要求 A/港 **2000**、美 **120 试用 / 5000 正式**。
- **字段顺序强约定**：生成器输出的元组顺序必须与前端 `src/utils/stockIndexSchema.ts` 的 `INDEX_FIELD` 逐列对应，否则前端解压错位。新增字段一律**追加在末尾**，不改已有下标。

<a id="sec-4"></a>

## 四、如何执行

<a id="sec-4-1"></a>

### 4.1 前置条件

1. 处于仓库根目录（脚本内部以 `REPO_ROOT` 为基准，且 `refresh` 的子进程 `cwd=REPO_ROOT`）。
2. 已激活 Python 虚拟环境（通常为 `.venv/bin/python`）。
3. `pip install tushare pypinyin`；若改用 baostock 生成沪深 CSV 或 akshare 生成北交所 CSV，另装 `pip install baostock akshare`。
4. 在 `.env` 配置 `TUSHARE_TOKEN=你的token`（`.env` 已被 git 忽略，不会提交）。
5. 账号积分满足目标市场的接口门槛。

> 走 Tushare 全链路才需要第 4、5 条；`fetch_baostock_stock_list_cn.py` 免费、无需 token 与积分，但只生成沪深 CSV。

<a id="sec-4-2"></a>

### 4.2 一键执行（推荐）

```bash
# 从仓库根目录执行
python3 scripts/stock_index_catalog/refresh_stock_index.py
```

等价于依次执行：抓取（Tushare，`--a-rk` 修正 A 股名称）→ 生成（`--source tushare`）→ 若 `dist-web/` 已构建则同步静态索引。

<a id="sec-4-3"></a>

### 4.3 分步执行与常用参数

```bash
# 1) 仅抓取（Tushare 全市场，A 股名称修正模式）
python3 scripts/stock_index_catalog/fetcher/fetch_tushare_stock_list_all.py --a-rk

# 1') 或用 baostock 单独生成沪深 CSV（免费、无需 token，只产出 stock_list_cn.csv）
python3 scripts/stock_index_catalog/fetcher/fetch_baostock_stock_list_cn.py

# 1'') 或用 akshare 单独生成北交所 CSV（免费、无需 token，只产出 stock_list_bse.csv）
python3 scripts/stock_index_catalog/fetcher/fetch_akshare_stock_list_bse.py

# 2) 仅生成（用已有 CSV 重新生成索引）
python3 scripts/stock_index_catalog/generate_index_from_csv.py --source tushare

# 3) 仅校验不写盘
python3 scripts/stock_index_catalog/generate_index_from_csv.py --test
```

**参数速查表：**

| 脚本 | 参数 | 说明 |
|---|---|---|
| `refresh_stock_index.py` | `--fetch-source {tushare,akshare}` | 选择抓取数据源，默认 `tushare`；`generate` 的 `--source` 会跟随此值。 |
| `refresh_stock_index.py` | `--skip-fetch` | 跳过抓取，仅用现有 CSV 重新生成索引。 |
| `fetcher/fetch_tushare_stock_list_all.py` | `--a-rk` | 开启沪深 A 股实时名称修正（覆盖 `stock_list_cn.csv`；`stock_list_bse.csv` 不参与）。 |
| `fetcher/fetch_baostock_stock_list_cn.py` | `--output-dir` | 输出目录，默认 `data/stock_index_catalog/`。 |
| `fetcher/fetch_akshare_stock_list_bse.py` | `--output-dir` | 输出目录，默认 `data/stock_index_catalog/`。 |
| `generate_index_from_csv.py` | `--source {tushare,akshare}` | 选择读取哪类 CSV，默认 `tushare`。 |
| `generate_index_from_csv.py` | `--test` / `-t` | 测试模式：只读取 + 校验，不写文件。 |

<a id="sec-4-4"></a>

### 4.4 增量合并（不重建整份索引）

当只有部分市场的 CSV（例如只跑了 baostock，目录下仅有 `stock_list_cn.csv`）时，**不要**直接跑 `generate_index_from_csv.py`——它是全量覆盖写，会把 31678 条砍到 5284 条。改用 `merge_stock_index_from_csv.py`：保留现有索引的每一条记录，只加新条目、补字段缺省值。
`merge` 在写盘前会自动按 [§2.4](#sec-2-4) 规范重排，因此增量合并的输出**同样是有序的**——新条目会按规则落入正确位置（市场分组 → 交易所 → 上市日期升序），无需再单独跑 `reorder`。

```bash
# 先看报告（不写盘，强烈建议先跑一次）
python3 scripts/stock_index_catalog/merge_stock_index_from_csv.py --cn --dry-run

# 确认后写盘；多个市场可同时指定，参数带值可自定义 CSV 路径
python3 scripts/stock_index_catalog/merge_stock_index_from_csv.py \
    --cn --bse data/tmp/stock_list_bse.csv --jp

# 写盘并同步其余索引副本
python3 scripts/stock_index_catalog/merge_stock_index_from_csv.py --cn --sync-copies
```

| 参数 | 说明 |
|---|---|
| `--cn` / `--bse` / `--hk` / `--us` / `--jp` / `--kr` | 指定要合并的市场；不带值用默认 CSV 路径，带值用指定文件。默认：CN/BSE/HK/US 取 `data/stock_index_catalog/stock_list_<m>.csv`；JP/KR 取 `static_markets/stock_list_<m>.csv`。 |
| `--index PATH` | 目标索引，默认 `apps/hrs-web/public/stocks.index.json`。 |
| `--dry-run` | 只打印合并报告，不写盘。 |
| `--sync-copies` | 写盘后同步其余 5 份索引副本（仅覆盖已存在的）。 |
| `--update-existing` | 允许用 CSV 覆盖已有非空字段；默认关闭，只补缺省值。 |

**合并语义**：

1. 所有现有记录补齐到 11 列（末列 `listDate`，无来源填 `""`）；历史索引里残留的 `YYYYMMDD` 会统一规范化为 `YYYY-MM-DD`。
2. CSV 中已存在的代码，只填「缺失或为空」的列；非空字段一律保留。
3. CSV 中不存在于索引的代码，作为完整 11 列新条目**插入到所属市场分段末尾**（顺序 `CN → BSE → HK → US → JP → KR`），不追加到数组最末尾；现有记录的相对顺序不变。
4. 插入锚点 = 该市场在现有索引中最后一次出现的位置 + 1。现有索引的 CN/BSE、JP/KR 存在交错段（旧版单份 A 股 CSV 按代码排序所致），用「最后一次」可保证新条目仍落在本市场块内；索引里没有该市场时，退到前一个存在市场的锚点。

脚本会先备份 `.bak`、再原子写落盘，且重复执行幂等。新增记录复用生成器的 `parse_stock_row` / `build_stock_index` / `compress_index` 产出，格式与全量重建一致。

> ⚠️ 增量合并是「打补丁」，下次 `refresh_stock_index.py` 全量重建会覆盖它。要长期保持，需补齐各市场 CSV 走正规重建，或把增量逻辑固化进生成器。
>
> ✅ 日期格式由 `generate_index_from_csv.normalize_list_date()` 单点收敛：合法 `YYYYMMDD` 转成 `YYYY-MM-DD`，已是目标格式或无法解析的值原样保留。因此全量重建与增量合并两条路径的输出一致。

<a id="sec-5"></a>

## 五、新增一个数据源（在 `fetcher/` 下扩展）

以新增 AkShare 为例，步骤如下。若只想做**单市场、不接入 `refresh`** 的抓取器，直接参考现成的 `fetcher/fetch_baostock_stock_list_cn.py`（复用同构 `CSV_COLUMNS`，只产出 `stock_list_cn.csv`，不登记 `FETCHER_SCRIPTS`）。

1. **新增抓取器**：在 `fetcher/` 下创建 `fetcher/fetch_akshare_stock_list_all.py`，产出与现有同构的 CSV。
   - 若沿用现有 `generate` 的 AkShare 读取逻辑，应写入 `logs/stock_basic_*.csv`（对应 `generate --source akshare` 的 `load_akshare_data`）；
   - 若想写入 `data/stock_index_catalog/stock_list_*.csv`（与 Tushare 一致），则需在 `generate` 中增加对应的 `load_<source>_data()` 读取函数（参考 `load_tushare_data` / `load_akshare_data`）。

2. **登记到 `refresh_stock_index.py`**：在 `FETCHER_SCRIPTS` 字典增加一项（argparse 的 `choices` 已用 `list(FETCHER_SCRIPTS.keys())` 自动包含新 key，无需改参数定义）：

   ```python
   FETCHER_SCRIPTS = {
       "tushare": "scripts/stock_index_catalog/fetcher/fetch_tushare_stock_list_all.py",
       "akshare": "scripts/stock_index_catalog/fetcher/fetch_akshare_stock_list_all.py",
   }
   ```

3. **对齐生成期读取**：保证 `refresh` 的 `--fetch-source` 与传给 `generate` 的 `--source` 一致（当前实现中 `generate --source` 已自动跟随 `--fetch-source`）。若新源需要不同于 `load_tushare_data` 的列布局，在 `generate_index_from_csv.py` 增加 `--source` 选项与对应 `load_*` 函数。

4. **验证**：

   ```bash
   python3 scripts/stock_index_catalog/refresh_stock_index.py --fetch-source akshare
   ```

   若 `fetcher/fetch_akshare_stock_list_all.py` 尚不存在，脚本会**提前报错退出（rc=2）**并提示「未找到抓取器 …（akshare 数据源尚未实装）」，不会误执行。

5. **JP/KR 兜底**：若新数据源覆盖日韩市场，可自行移除对 `static_markets/` 的依赖；否则 JP/KR 继续走静态兜底。

<a id="sec-6"></a>

## 六、常见问题与注意事项

- **索引字段顺序**：生成元组顺序必须与前端 `src/utils/stockIndexSchema.ts` 的 `INDEX_FIELD` 一致；新增列只能追加在末尾。
- **`data/` 不进 git**：`/data/` 被 `.gitignore` 忽略（含子目录 `data/stock_index_catalog/`），`stock_list_*.csv` 与最终索引均为本地按需生成，看不到文件是正常现象。
- **缺 token / 积分不足**：`refresh` 在抓取阶段即退出（rc=2），**不会改写** `public/stocks.index.json`，可放心重试。
- **`static_markets/` 不可删**：JP/KR 的唯一权威源（Tushare 无日韩接口）。
- **`__pycache__/` 不要提交**：已被 `.gitignore` 忽略，属自动生成的字节码缓存，删掉无害。
- **路径基准**：所有脚本内部基于 `Path(__file__)` 计算仓库根，因此脚本本身可在任意 `cwd` 下被调用；但 `refresh` 的子进程显式以仓库根为 `cwd`，故文档中的命令示例均从仓库根执行。
