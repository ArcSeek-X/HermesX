# <a id="stock-index-catalog-readme"></a>stock_index_catalog 目录说明

> 📝 **简介**：本目录是「前端股票搜索自动补全索引」的离线生成工具集——负责从数据源抓取股票基础资料清单、生成压缩索引 `apps/hrs-web/public/stocks.index.json`，并同步到前端/桌面构建产物。与运行时的行情/分析数据源（`data_provider/**/tushare_*.py`）无关。
>
> 👤 **维护**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-09

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
| `generate_index_from_csv.py` | **核心生成器**。读取各源 CSV，做名称规范化、拼音/别名、市场判定、压缩为元组数组，写入 `apps/hrs-web/public/stocks.index.json`。 | ❌ 否 |

<a id="sec-2-2"></a>

### 2.2 `fetcher/` 抓取器目录

每个数据源一个脚本，产出结构一致的 `data/stock_list_*.csv`。

| 文件 | 作用 |
|---|---|
| `fetcher/fetch_tushare_stock_list.py` | **唯一真正调用 Tushare 的脚本**。调 `pro.stock_basic` / `pro.hk_basic` / `pro.us_basic`，把 A/港/美 列表写入 `data/stock_list_{a,hk,us}.csv`；支持 `--a-rk`（用 `rt_k` 修正 A 股 `XD/XR/DR/N/C` 前缀名称）。**Tushare 专属**，换源需替换。 |

> 💡 想加新数据源时，在 `fetcher/` 下新增 `fetch_<source>_stock_list.py` 即可（见 [§5](#sec-5)）。

<a id="sec-2-3"></a>

### 2.3 `static_markets/` 静态兜底市场

Tushare **没有**日本 / 韩国接口，因此 JP/KR 永远走这里的静态文件，它们是 JP/KR 的唯一权威源。

| 文件 | 作用 |
|---|---|
| `static_markets/stock_list_jp.csv` | 日本市场股票清单（代码 / 名称 / 上市日期等，格式与抓取 CSV 同构）。 |
| `static_markets/stock_list_kr.csv` | 韩国市场股票清单。 |

> ⚠️ 不要在 `refresh` 正常流程中删除这两个文件，否则 JP/KR 搜索将缺数据。

<a id="sec-3"></a>

## 三、数据流与依赖关系

```text
fetcher/fetch_tushare_stock_list.py --a-rk
        │  写入
        ▼
data/stock_list_{a,hk,us}.csv   （/data/ 被 git 忽略，本地按需生成）
        │
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
3. `pip install tushare pypinyin`。
4. 在 `.env` 配置 `TUSHARE_TOKEN=你的token`（`.env` 已被 git 忽略，不会提交）。
5. 账号积分满足目标市场的接口门槛。

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
# 1) 仅抓取（A 股名称修正模式）
python3 scripts/stock_index_catalog/fetcher/fetch_tushare_stock_list.py --a-rk

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
| `fetcher/fetch_tushare_stock_list.py` | `--a-rk` | 开启 A 股实时名称修正（覆盖 `stock_list_a.csv`）。 |
| `generate_index_from_csv.py` | `--source {tushare,akshare}` | 选择读取哪类 CSV，默认 `tushare`。 |
| `generate_index_from_csv.py` | `--test` / `-t` | 测试模式：只读取 + 校验，不写文件。 |

<a id="sec-5"></a>

## 五、新增一个数据源（在 `fetcher/` 下扩展）

以新增 AkShare 为例，步骤如下：

1. **新增抓取器**：在 `fetcher/` 下创建 `fetcher/fetch_akshare_stock_list.py`，产出与现有同构的 CSV。
   - 若沿用现有 `generate` 的 AkShare 读取逻辑，应写入 `logs/stock_basic_*.csv`（对应 `generate --source akshare` 的 `load_akshare_data`）；
   - 若想写入 `data/stock_list_*.csv`（与 Tushare 一致），则需在 `generate` 中增加对应的 `load_<source>_data()` 读取函数（参考 `load_tushare_data` / `load_akshare_data`）。

2. **登记到 `refresh_stock_index.py`**：在 `FETCHER_SCRIPTS` 字典增加一项（argparse 的 `choices` 已用 `list(FETCHER_SCRIPTS.keys())` 自动包含新 key，无需改参数定义）：

   ```python
   FETCHER_SCRIPTS = {
       "tushare": "scripts/stock_index_catalog/fetcher/fetch_tushare_stock_list.py",
       "akshare": "scripts/stock_index_catalog/fetcher/fetch_akshare_stock_list.py",
   }
   ```

3. **对齐生成期读取**：保证 `refresh` 的 `--fetch-source` 与传给 `generate` 的 `--source` 一致（当前实现中 `generate --source` 已自动跟随 `--fetch-source`）。若新源需要不同于 `load_tushare_data` 的列布局，在 `generate_index_from_csv.py` 增加 `--source` 选项与对应 `load_*` 函数。

4. **验证**：

   ```bash
   python3 scripts/stock_index_catalog/refresh_stock_index.py --fetch-source akshare
   ```

   若 `fetcher/fetch_akshare_stock_list.py` 尚不存在，脚本会**提前报错退出（rc=2）**并提示「未找到抓取器 …（akshare 数据源尚未实装）」，不会误执行。

5. **JP/KR 兜底**：若新数据源覆盖日韩市场，可自行移除对 `static_markets/` 的依赖；否则 JP/KR 继续走静态兜底。

<a id="sec-6"></a>

## 六、常见问题与注意事项

- **索引字段顺序**：生成元组顺序必须与前端 `src/utils/stockIndexSchema.ts` 的 `INDEX_FIELD` 一致；新增列只能追加在末尾。
- **`data/` 不进 git**：`/data/` 被 `.gitignore` 忽略，`stock_list_*.csv` 与最终索引均为本地按需生成，看不到文件是正常现象。
- **缺 token / 积分不足**：`refresh` 在抓取阶段即退出（rc=2），**不会改写** `public/stocks.index.json`，可放心重试。
- **`static_markets/` 不可删**：JP/KR 的唯一权威源（Tushare 无日韩接口）。
- **`__pycache__/` 不要提交**：已被 `.gitignore` 忽略，属自动生成的字节码缓存，删掉无害。
- **路径基准**：所有脚本内部基于 `Path(__file__)` 计算仓库根，因此脚本本身可在任意 `cwd` 下被调用；但 `refresh` 的子进程显式以仓库根为 `cwd`，故文档中的命令示例均从仓库根执行。
