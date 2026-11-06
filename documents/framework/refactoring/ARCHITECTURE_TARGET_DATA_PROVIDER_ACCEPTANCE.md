# HermesX data_provider 优化：兼容、能力契约与最终验收

> ARCHITECTURE_TARGET_DATA_PROVIDER_REFACTORING.md 的实施验收附件；保留 B00/B01 与 B21–B23 的验收快照，并在 §7 记录根目录收敛 R0–R5 的当前证据及未通过项。

| 项目 | 内容 |
| --- | --- |
| 作者 | Codex，依据现有实现、原始 Git 基线和实测结果整理 |
| 更新时间 | 2026-11-06（Asia/Shanghai） |
| 基线 | `984f338b`；未提交专项工作树，保留维护者并行修改 |
| 上位方案 | [data_provider 专项](./ARCHITECTURE_TARGET_DATA_PROVIDER_REFACTORING.md)、[目标架构](./ARCHITECTURE_TARGET.md) |
| 状态 | 根目录收敛 R0–R5 完成，15/15（100%）；Linux/ARM64 镜像及容器已验收，原 B23 跨平台/桌面窗口缺口保留 |

## 目录

- [1. 审计口径与复现](#audit)
- [2. 原始 72 文件逐项结果](#files)
- [3. 逐能力契约与行为矩阵](#capabilities)
- [4. 最终验证与环境缺口](#verification)
- [5. 回滚与后续执行](#rollback)
- [6. 剩余缺口复核](#gap-recheck)
- [7. 根目录收敛实施与验收](#root-convergence-acceptance)

<a id="audit"></a>
> 当前根目录收敛进度见 §7；§1–§6 保留上一轮 B00–B23 验收快照，旧路径保留记录不代表本轮仍保留。

## 1. 审计口径与复现

审计使用原始基线中的 72 个 Python 文件，而非以改造后的文件列表冒充原始范围。检查 321 个公开函数/方法/显式构造器及 property；对照既有参数名称、参数类型（位置/关键字）、位置参数顺序和默认值是否存在，并核对 dataclass 字段顺序。该检查不等于所有函数行为或类型注解的形式化证明，也不单凭签名相同判断兼容。

当前扫描源码、API、Bot、脚本、数据源和测试，共发现 **802 条 Python 静态或字面符号引用**，另对账 **13 条脚本/工作流引用**，包含根 main.py 与 .github 自动化。17 项包根动态导出注册项均解析为预期唯一对象；默认工厂、5 个整模块兼容别名、协议再导出、私有 patch 字符串和打包路径分别有源码/测试/冻结证据。计算产生的任意动态字符串不在 AST 守卫可证明范围；当前受控注册表通过实际导入对账，而不是静默忽略。

复现（仓库根目录，输出放到本地临时目录）：

```bash
python scripts/check_provider_contracts.py --baseline 984f338b --output /tmp/hermesx-provider-contract-audit.json
python scripts/check_architecture.py --check
HRS_PACKAGED_IMPORT_PROBE=data_provider python main.py
```

原公开调用契约：**321 项检查、0 不兼容**。新可选参数允许增加；配置默认值、字段单位、源顺序、预算和降级则结合下表与原有行为测试核验。日志、JSON 原始报告与打包产物为 /tmp 本地产物，不作为产品资源合入。

### 上一轮兼容路径决定（B21 历史快照，当前落点见 §7）

当前保留 **21 个根级兼容文件**，原因包括默认工厂/调用方仍使用既有 Fetcher 类型、现有私有覆盖点，以及旧 pickle GLOBAL 路径；源码与冻结包都需要它们。B21 没有在旧使用者仍存在时删除文件。五个整模块 shim 共享 canonical 模块对象，其余为原位薄接口/窄委托，均无第二份取数算法或 SDK 状态。根 `base.py` 保留 Manager 的资源状态和装配；实时/日线协调已移出。`us_index_mapping.py` 继续使用同一 domain 映射，不另造规则。

包根改为按需导出，原 __all__ 不变；不缓存临时替换的对象。没有为了迁移层级新建空的 runtime/resources.py。目标树已按本轮必要保留项修正为实际落点，不把目录数量当作实现指标。

<a id="files"></a>
## 2. 原始 72 文件上一轮逐项结果（当前退出路径见 §7）

“模块转接”表示旧模块直接解析为 canonical 模块；“原位/兼容入口”包含同路径保留或同对象再导出。详细职责去向仍以专项 §4.3 为准，新增 74 个文件不冒充原始文件。

| 原始路径 | 当前解析模块 | 公开调用检查数 | 结论 |
| --- | --- | ---: | --- |
| `data_provider/__init__.py` | `data_provider` | 0 | 原位/兼容入口，保留 |
| `data_provider/akshare_fetcher.py` | `data_provider.akshare_fetcher` | 13 | 原位/兼容入口，保留 |
| `data_provider/alphavantage_fetcher.py` | `data_provider.alphavantage_fetcher` | 3 | 原位/兼容入口，保留 |
| `data_provider/baostock_fetcher.py` | `data_provider.baostock_fetcher` | 3 | 原位/兼容入口，保留 |
| `data_provider/base.py` | `data_provider.base` | 36 | 原位/兼容入口，保留 |
| `data_provider/code_search/__init__.py` | `data_provider.code_search` | 0 | 原位/兼容入口，保留 |
| `data_provider/code_search/base.py` | `data_provider.code_search.base` | 7 | 原位/兼容入口，保留 |
| `data_provider/code_search/eastmoney_source.py` | `data_provider.code_search.eastmoney_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/code_search/local_stockdb_source.py` | `data_provider.code_search.local_stockdb_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/code_search/stocksdk_source.py` | `data_provider.code_search.stocksdk_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/common/__init__.py` | `data_provider.common` | 0 | 原位/兼容入口，保留 |
| `data_provider/common/base.py` | `data_provider.common.base` | 10 | 原位/兼容入口，保留 |
| `data_provider/common/cache.py` | `data_provider.common.cache` | 6 | 原位/兼容入口，保留 |
| `data_provider/common/health.py` | `data_provider.common.health` | 7 | 原位/兼容入口，保留 |
| `data_provider/common/normalize.py` | `data_provider.common.normalize` | 3 | 原位/兼容入口，保留 |
| `data_provider/common/rate_limit.py` | `data_provider.common.rate_limit` | 4 | 原位/兼容入口，保留 |
| `data_provider/eastmoney_quote_snapshot.py` | `data_provider.eastmoney_quote_snapshot` | 1 | 原位/兼容入口，保留 |
| `data_provider/efinance_fetcher.py` | `data_provider.efinance_fetcher` | 9 | 原位/兼容入口，保留 |
| `data_provider/finnhub_fetcher.py` | `data_provider.finnhub_fetcher` | 3 | 原位/兼容入口，保留 |
| `data_provider/fundamental_adapter.py` | `data_provider.fundamental_adapter` | 3 | 原位/兼容入口，保留 |
| `data_provider/fundamentals/__init__.py` | `data_provider.fundamentals` | 0 | 原位/兼容入口，保留 |
| `data_provider/fundamentals/base.py` | `data_provider.fundamentals.base` | 5 | 原位/兼容入口，保留 |
| `data_provider/fundamentals/tushare_source.py` | `data_provider.fundamentals.tushare_source` | 3 | 原位/兼容入口，保留 |
| `data_provider/institutional/__init__.py` | `data_provider.institutional` | 0 | 原位/兼容入口，保留 |
| `data_provider/institutional/base.py` | `data_provider.institutional.base` | 3 | 原位/兼容入口，保留 |
| `data_provider/institutional/tw_source.py` | `data_provider.institutional.tw_source` | 2 | 原位/兼容入口，保留 |
| `data_provider/kline/__init__.py` | `data_provider.kline` | 0 | 原位/兼容入口，保留 |
| `data_provider/kline/base.py` | `data_provider.kline.base` | 7 | 原位/兼容入口，保留 |
| `data_provider/kline/eastmoney_source.py` | `data_provider.kline.eastmoney_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/kline/local_stockdb_source.py` | `data_provider.kline.local_stockdb_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/kline/sina_source.py` | `data_provider.kline.sina_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/kline/stocksdk_source.py` | `data_provider.kline.stocksdk_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/kline/tencent_source.py` | `data_provider.kline.tencent_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/kline/transform.py` | `data_provider.kline.transform` | 7 | 原位/兼容入口，保留 |
| `data_provider/limit_pool/__init__.py` | `data_provider.limit_pool` | 0 | 原位/兼容入口，保留 |
| `data_provider/limit_pool/base.py` | `data_provider.limit_pool.base` | 7 | 原位/兼容入口，保留 |
| `data_provider/limit_pool/eastmoney_source.py` | `data_provider.limit_pool.eastmoney_source` | 2 | 原位/兼容入口，保留 |
| `data_provider/limit_pool/stocksdk_source.py` | `data_provider.limit_pool.stocksdk_source` | 2 | 原位/兼容入口，保留 |
| `data_provider/longbridge_fetcher.py` | `data_provider.longbridge_fetcher` | 5 | 原位/兼容入口，保留 |
| `data_provider/news/__init__.py` | `data_provider.news` | 0 | 原位/兼容入口，保留 |
| `data_provider/news/base.py` | `data_provider.news.base` | 3 | 原位/兼容入口，保留 |
| `data_provider/news/wallstreetcn_source.py` | `data_provider.news.wallstreetcn_source` | 6 | 原位/兼容入口，保留 |
| `data_provider/pytdx_fetcher.py` | `data_provider.pytdx_fetcher` | 4 | 原位/兼容入口，保留 |
| `data_provider/realtime/__init__.py` | `data_provider.realtime` | 0 | 原位/兼容入口，保留 |
| `data_provider/realtime/akshare_source.py` | `data_provider.realtime.akshare_source` | 2 | 原位/兼容入口，保留 |
| `data_provider/realtime/base.py` | `data_provider.realtime.base` | 6 | 原位/兼容入口，保留 |
| `data_provider/realtime/tickflow_source.py` | `data_provider.realtime.tickflow_source` | 3 | 原位/兼容入口，保留 |
| `data_provider/realtime_types.py` | `data_provider.realtime_types` | 14 | 原位/兼容入口，保留 |
| `data_provider/sector/__init__.py` | `data_provider.sector` | 0 | 原位/兼容入口，保留 |
| `data_provider/sector/base.py` | `data_provider.sector.base` | 6 | 原位/兼容入口，保留 |
| `data_provider/sector/eastmoney_source.py` | `data_provider.sector.eastmoney_source` | 16 | 原位/兼容入口，保留 |
| `data_provider/sector/market_cards_source.py` | `data_provider.sector.market_cards_source` | 2 | 原位/兼容入口，保留 |
| `data_provider/sector/shidaotec_source.py` | `data_provider.sector.shidaotec_source` | 5 | 原位/兼容入口，保留 |
| `data_provider/sector/stocksdk_source.py` | `data_provider.sector.stocksdk_source` | 12 | 原位/兼容入口，保留 |
| `data_provider/stock_info/__init__.py` | `data_provider.stock_info` | 0 | 原位/兼容入口，保留 |
| `data_provider/stock_info/base.py` | `data_provider.stock_info.base` | 6 | 原位/兼容入口，保留 |
| `data_provider/stock_info/eastmoney_source.py` | `data_provider.stock_info.eastmoney_source` | 2 | 原位/兼容入口，保留 |
| `data_provider/stock_info/local_stockdb_source.py` | `data_provider.stock_info.local_stockdb_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/stock_info/stocksdk_source.py` | `data_provider.stock_info.stocksdk_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/stock_info/tencent_source.py` | `data_provider.stock_info.tencent_source` | 1 | 原位/兼容入口，保留 |
| `data_provider/stockdb_fetcher.py` | `data_provider.clients.stockdb` | 10 | 模块转接，保留 |
| `data_provider/stocksdk_bridge.py` | `data_provider.clients.stocksdk.bridge` | 19 | 模块转接，保留 |
| `data_provider/tencent_fetcher.py` | `data_provider.tencent_fetcher` | 1 | 原位/兼容入口，保留 |
| `data_provider/tencent_quote_snapshot.py` | `data_provider.tencent_quote_snapshot` | 1 | 原位/兼容入口，保留 |
| `data_provider/tickflow_fetcher.py` | `data_provider.tickflow_fetcher` | 10 | 原位/兼容入口，保留 |
| `data_provider/tushare_fetcher.py` | `data_provider.tushare_fetcher` | 11 | 原位/兼容入口，保留 |
| `data_provider/tw_institutional_fetcher.py` | `data_provider.institutional.tw_client` | 3 | 模块转接，保留 |
| `data_provider/us_index_mapping.py` | `data_provider.us_index_mapping` | 1 | 原位/兼容入口，保留 |
| `data_provider/wallstreetcn_calendar_fetcher.py` | `data_provider.calendar.wallstreetcn_source` | 3 | 模块转接，保留 |
| `data_provider/wallstreetcn_live_news_fetcher.py` | `data_provider.news.wallstreetcn_live` | 9 | 模块转接，保留 |
| `data_provider/yfinance_fetcher.py` | `data_provider.yfinance_fetcher` | 3 | 原位/兼容入口，保留 |
| `data_provider/yfinance_fundamental_adapter.py` | `data_provider.yfinance_fundamental_adapter` | 1 | 原位/兼容入口，保留 |

<a id="capabilities"></a>
## 3. 逐能力契约与行为矩阵

来源覆盖按现有实现记录，不把无实现的 BaseFetcher 默认返回值算成可用能力；默认注册与可手动调用的 Source 也不混为一谈。下表测试目录均为实际仓库路径，完整最终运行覆盖其现有用例；已有网络观测的 skip 另列，不当作成功。

| 能力 / canonical 入口 | 原有源与范围 | 关键输入、输出和状态契约 | 验证落点 |
| --- | --- | --- | --- |
| 分析日线 `kline/daily_history.py` + daily_* | 11 厂商，按原市场/ETF/指数规则过滤；不扩大覆盖 | 原代码规范化、日期、最短/799–800 条边界、复权、标准列/单位、指标输入、失败回退；共享 SDK/限额及原 tenacity 不叠加 | `tests/infrastructure/providers/kline/`、`routing/`、原流水线/选股测试 |
| 页面 K 线 `kline/base.py` | local / stocksdk / eastmoney / sina / tencent，按原配置 | KLineRequest/Result、多周期/复权/分页、成交量展示口径、prev_close 与错误映射；不套用分析日线契约 | `tests/api/kline/`、providers/routing 与原 Local/StockSDK 测试 |
| 实时 `realtime/coordination.py`、`base.py` | 分析侧九厂商/通道；能力默认 tencent、akshare_sina、akshare_em，TickFlow 显式启用 | 同一 UnifiedRealtimeQuote、HK 源参数、指数路由、缺字段补全、freshness/来源、预取、串行锁与独立熔断 | `tests/infrastructure/providers/realtime/`、routing、API/流水线 |
| 基本面 `fundamentals/aggregate.py` | 原 CN 多源、海外 Yfinance、台湾机构，旧 Tushare 名称包装不虚构新源 | status/coverage/source_chain、预算分配/扣减、缓存与超时槽、partial/not_supported、跨入口无递归；字段/来源标签原样 | `tests/infrastructure/providers/fundamentals/`、institutional/report wiring、Agent tools |
| 资金流/龙虎榜 `fundamentals/flow_source.py` | 原 CN/AkShare 适配；非适用市场/ETF 仍不支持 | 原预算/重试、块形状/覆盖率和空/失败语义，不添加衍生交易结论 | providers/fundamentals 与原分析上下文测试 |
| 股票名称 `stock_info/name_lookup.py` | Manager + 七厂商原有名称能力 | 单个/批量/轻量预取、原 key/缓存写回、None 与原无实时选项；不增加网络支路 | providers/catalog、stock_info/name_catalog 回归 |
| 股票清单 `stock_info/catalog.py` | Tushare / Baostock / TickFlow 公共清单，Pytdx 内部分页 | 原精确 symbol、分页、缓存/资源关闭、缺 SDK/负权限行为；Efinance 基本信息仍独立方法 | providers/catalog、name_catalog/shared state 测试 |
| 代码搜索 `code_search/base.py` | local / stocksdk / eastmoney | query/limit、代码/市场字段和原排序；不与名称查询或索引持久化合并 | providers/routing、原搜索/代码 API 测试 |
| 指数/统计 `market/indices.py`、`statistics.py` | 原六厂商指数、已有统计能力与卡片辅助 | 原市场支持、金额/涨跌单位、同源纯公式去重；不把卡片结果形状替代复盘结果 | providers/market、原 JP/KR/TW/HK/US 指数和 market review 测试 |
| 全市场快照 `market/snapshot.py` | 原 EastMoney → Tencent → AkShare | 逐股 DataFrame、原索引过滤、分页重试/部分结果及各源市值单位；外层不叠加重试 | providers/market、`tests/application/analysis/screening/test_eod_picker_service.py` |
| 板块/榜单/卡片 `sector/` | 默认 eastmoney；原手工适配器与 AkShare/Efinance/Tushare/TickFlow 能力保持 | 行业/概念/人气/所属板块、类级/实例/模块缓存及返回副本、Session/桥接、fresh/stale/cold 与后台预热 | providers/sector、API sector、相关板块/市场流水线 |
| 涨跌停池 `limit_pool/` | 原 AkShare；能力 eastmoney / stocksdk，StockSDK 仍明确不可用 | 原日期/排序/时间与数值字段、DTO/常量、空/错误、旧 pickle；不虚构 Node bridge 能力 | providers/common 协议边界、limit_pool API、原行情测试 |
| 筹码 `chip/` | AkShare / Tushare | 原请求/时间窗口、分位计算与比例单位、有效性解析差异、0 集中度、半开探测释放与回退；domain 为纯计算真源 | providers/chip、`tests/domain/analysis/test_chip_metrics.py` 与原 domain 规则 |
| 财经日历 `calendar/wallstreetcn_source.py` | 华尔街见闻国家/宏观日历 | 无分页、秒级 UTC/全天 0、原 DTO/异常/8 MiB、请求关闭；安全回调仍由应用注入 | providers/calendar、`tests/integration/intelligence/test_live_calendar.py` |
| 快讯 `news/wallstreetcn_live.py` | 原 8 频道；应用层保留 NewsNow 降级 | scope/cursor、文本/秒级时间、4 MiB、异常/关闭、SSRF/DNS 回调与数据落库边界 | providers/calendar、`tests/integration/intelligence/test_live_news.py`、intelligence 安全用例 |
| 台湾机构 `institutional/tw_client.py` | TWSE / TPEx，TW/TWO 且不扩展裸码 | 民国日期、shares 正负号、合法空结果、整市场缓存/逐 key 锁、独立 breaker；装配时解析，mock 作用域恢复 | providers/institutional、report wiring、原网络漂移观测 |

共享资源/策略矩阵见专项 §7.5。B22 只允许登记的 `src.application.runtime.provider_diagnostic_ports`；API/Bot/bootstrap 和具体应用实现（含可解析的动态字面导入）均被反例阻断，未扩充 baseline 掩盖违规。

<a id="verification"></a>
## 4. 最终验证与环境缺口

| 范围 | 实测结果 | 结论边界 |
| --- | --- | --- |
| 最新完整门禁，seed=20261106 | **5865 passed / 1 skipped / 4 deselected / 27 warnings / 511 subtests（383.67s）**；架构/语法/关键静态及确定性检查全过 | 当前版本门禁全绿 |
| 首轮完整门禁，seed=20261105 | 5865 passed / 1 skipped / 4 deselected / 27 warnings / 511 subtests（372.94s） | 原生产代码已通过；其后只完善配置测试隔离 |
| 首次随机全量，seed=20261106 | 5864 passed / 1 failed / 1 skipped / 4 deselected（384.81s） | 暴露配置测试继承启动捕获状态、读取本机 .env；未当作通过 |
| 配置隔离修正 | 46 passed（4.11s），生产配置不变 | 每例 reset；仅隔离本机 .env，显式临时文件仍走真实解析；最新全量已复核 |
| 最终相关随机序 | 644 passed / 1 skipped / 2 deselected（40.57s） | 数据源 + 架构守卫 + 打包测试 |
| API/守卫/打包等定向 | 64 passed（8.04s） | OpenAPI 仅描述同步，结构化去掉 description 后与原规范一致 |
| B00/兼容 | 72 文件 / 321 调用契约 / 802 引用 / 17 根导出，0 错误 | 含 property、参数顺序/默认存在性和 dataclass 字段；不等于证明任意输入行为 |
| macOS 本机环境冻结 | 新输出构建成功；235 代码对象签名规范化；17 导出和 145 子模块实际加载 | 使用既有依赖，不冒充干净依赖安装 |
| 干净 Python 环境 | 独立 venv 安装完整 requirements 成功，pip check 无损坏依赖；源码全数据源导入成功 | 初次受默认网络限制；正常网络权限下 GitHub 安装完成，不改系统/项目环境 |
| 干净环境冻结 | 新 PyInstaller 6.22.3 产物；243 对象签名检查；--help 与 17 导出/145 子模块导入通过 | 初次缓存写入权限问题用临时 PYINSTALLER_CONFIG_DIR 修正，仅隔离验证环境 |
| 冻结后端实际启动 | 临时 DB/日志 + 系统分配空闲端口，health 200（56 bytes）、首页 200（1815 bytes） | 仅关闭本次子进程，未停止既有服务；不能替代 Electron 窗口端到端 |
| Web | npm run build 通过（28.23s） | 使用本机既有 node_modules；未改页面；全量 lint 按维护者安排暂缓 |
| Desktop 原生测试 | 49 passed（约 3.22s） | 无桌面生产代码变化 |
| macOS ARM64 DMG | 临时目录 .app/DMG 构建成功；267 对象签名检查，DMG 校验/只读挂载和包内后端 145 子模块导入通过 | 验证复制保留 symlink；磁盘镜像工具需系统访问；无 Apple 身份/公证，不安装到 Applications |
| Node bridge | 源码侧实际 Node 进程 ping 成功（supportsCacheClear=true） | 验证迁移后的入口/cwd/协议，未宣称冻结包内 Node 完整运行或行情接口已验证 |
| 网络观测 | 1 passed / 3 skipped（208.53s） | TPEx 通过；TWSE 连接超时、Anspire 两条缺 key；未宣称全部网络通过 |
| 标准 Dockerfile 完整镜像 | 构建在 @heroui-pro/react/css 解析阶段失败 | **仍受维护者已确认保留的 Pro 授权缺口阻塞**，未删依赖或替换样式 |
| Windows / Intel | 尚无本轮安装运行证据 | **未验收**；Rosetta 基础进程成功不能代替产品 Intel 验收 |
| macOS 桌面窗口 | 2026-11-06 隔离用户目录实际启动；窗口连接已有 8000 服务，自己的后端因端口占用退出 | **已验证未通过**；详见 §6，不以页面可见代替自带后端就绪 |

B23 仍未全部通过，专项 **95.8%（23/24）**。数据源代码收敛已完成；桌面启动故障、授权和平台条件仍需处理/补验，不以“文档写完”记为 100%。源树 146 Python 文件、18 下级目录，测试收集 5870（417 原模块 + 1 新公开面模块 = 418 模块），顶层测试 0。


### 明确不作出的结论

Docker 的标准全镜像尚未成功；不能以现有 node_modules 下 Web 构建或后端冻结通过代替干净容器。Windows/Intel 安装运行、长期性能与零偶发承诺均未证明；桌面窗口已复核但因误认其他后端而失败。前端全量 lint 按维护者决定继续暂缓。

<a id="rollback"></a>
## 5. 回滚与后续执行

- Root lazy exports、能力协调与 Root 窄委托成组恢复，保留原 DTO/异常身份与资源所有权；不能仅删新模块。
- 共享协议/策略改动依专项 §7.5 按能力切片恢复，保留原缓存键、Session/锁/SDK/超时槽与配置默认值。
- 打包脚本和 main 的诊断导入增强成组恢复；无需回滚用户数据库或安装目录。所有本轮构建在 /tmp，未覆盖原 dist-desktop 产物。
- 静态 OpenAPI 仅更新描述；结构化剥除 description 后与原文件一致，无 API 行为改变。
- Docker 下一步是按现有 HeroUI Pro 授权提供实际样式并重跑标准构建，禁止删除依赖/改页面绕过；桌面平台验收按现有环境补齐。
- 未执行 commit/push/tag，内部中文验收附件无英文对应版本。


<a id="gap-recheck"></a>
## 6. 剩余缺口复核（2026-11-06）

维护者要求复核“目前能否验证”。本次仅做验收和记录，未修补产品页面、桌面启动链路或改变 Pro 依赖。

| 缺口 | 当前条件与实际操作 | 结论 / 下一步 |
| --- | --- | --- |
| 标准 Docker 全镜像 | Docker 29.8.2 可用；重跑仓库标准 Dockerfile。Web 阶段仍报 Can't resolve '@heroui-pro/react/css'。本机可见 Pro 包为 1.0.0-beta.10，只有 postinstall 壳、无 CSS 导出，当前进程无 HEROUI_AUTH_TOKEN | **可以复验，但未通过**。不据此断言账号未购买；需要将有效授权资源/CI 凭据接入干净构建后再验。未登录、提取或打印凭据，未替换样式 |
| ARM64 桌面窗口端到端 | 用隔离用户目录启动已打包 .app，先在临时 Electron 副本验证 userData 确实为临时路径；读取实际窗口 URL/截图和自身启动日志 | **可以验证，实测失败**：端口/健康响应未能证明连接的是自带后端，不能关闭缺口 |
| Windows | 本机 arm64 macOS；未发现 Wine/Wine64/PowerShell 或常见 Parallels/VMware/UTM/VirtualBox 应用；当前代码仍未提交/推送 | **当前无完整验证环境**。需要 Windows 主机/VM，或提交当前代码后使用对应 CI，不能拿旧远端结果替代 |
| Intel | Rosetta 可运行 x86_64 基础命令及系统 Python 3.9.6，但当前后端 Mach-O 仅 arm64；没有发现可用于该项目完整依赖的已配置 x86_64 Python 环境 | **只能部分核验环境，未验收产品**。需准备支持的 x86_64 Python/SDK/产物与运行环境；不能把 Rosetta 可用写为 Intel 通过 |

### 桌面失败的证据链

本次临时用户目录为 `/tmp/hermesx-gap-recheck/desktop-profile`，自带后端为上一轮干净环境生成并打入验收 .app 的冻结程序。日志显示：

1. 08:55:16（Asia/Shanghai）选择 8000，启动自己的后端 PID 5213。
2. 仅 170ms 后即将 8000 健康响应判定为就绪，窗口加载 `http://127.0.0.1:8000/`，随后显示该服务的市场页。
3. 08:55:23 自带后端报告 `FastAPI port is not available: 127.0.0.1:8000`，08:55:24 以 exit code 1 退出。
4. 端口实际监听者是另一 Python 进程 PID 25415，不是本次 PID 5213。窗口能显示页面不能作为此次自带后端启动成功的证据。

下一步应收敛端口选择/竞争窗口与健康检查的后端身份判定。现有证据确认错误连接，但不单凭日志推断端口探测实现的全部根因。启动日志还记录了前端自动构建路径未找到及更新检查 404，分别保留为观察项，不用它们替代本次已证实的端口/身份问题。

本次开发运行时探针曾被系统终止，随后原 node_modules/Electron.app 路径不可用，无法据此证明原因。仅在 /tmp 解压已缓存的同版本 Electron（31.7.7），修复该临时副本的残缺签名后完成隔离目录探针；未恢复/覆盖原 node_modules、未关闭 Gatekeeper、未改系统安全设置。

截图、页面元信息、启动日志及 Docker 日志仅存 `/tmp/hermesx-gap-recheck/`，不作为仓库文件合入。测试结束仅关闭本次带临时目录标记的应用进程 PID 5206；自己的后端已退出，原有 8000 监听进程仍保持 PID 25415，未停止用户服务。未复制到 Applications、未读写既有 HermesX 用户目录、未提交 Git。

专项进度仍为 **95.8%（23/24）**；本次把“窗口未验收”更新为“已验收失败”，没有提高百分比。


<a id="root-convergence-acceptance"></a>
## 7. 根目录收敛实施续篇（R0–R5，2026-11-06）

这是专项方案 §11 的新增范围，不覆盖前文 B00–B23 历史结果。基线 HEAD 为 `984f338b`，工作区含上一轮未提交的数据源改动、维护者的 Web CSS 注释及并行图册修改，全部保留，不进行 reset/stash/commit/push/tag。

R0 原始审计：72 文件、321 调用契约、802 引用、0 错误。运行代码未发现以待删除旧模块路径存储 pickle/joblib 的实现；此前构造的旧路径反序列化测试属于迁移期兼容验证。本轮按方案退出内部模块路径，仅保留包级公开导出与 base 的明确公开兼容；真实外部旧路径载荷不再作无条件兼容承诺，未读取或迁移用户本地数据库。

R1 已将指数识别及映射消费直接指向 domain，Yahoo 查询位于 common/symbols；common/normalize、StockSDK bridge、实时 Manager、股票代码规范化适配器与邮件发送器使用 domain 纯规则，不再因代码处理加载 base。新增独立进程低层导入测试，覆盖不加载运行管理器。190 个相关测试通过，架构守卫通过；审计仍覆盖 72 文件/321 契约，809 引用、0 错误。

审计脚本为明确退出的旧模块登记规范模块或逐符号映射，而不是从旧基线移除这些文件/契约；后续报告分别列出旧文件是否保留与新实现地址。公开导出注册改为绝对模块路径，允许指数规则直接指向 domain；仍惰性解析且不永久缓存测试替换。


### R2–R4 实现与批次验证

- R2：11 个薄入口退出；消费者指向已有能力/客户端，公开 TencentFetcher 指向唯一日线类；旧迁移测试改为规范类型/载荷与状态验证，保留真实清理、超时、回退和字段断言。旧模块别名不再作为内部契约，base 异常旧载荷仍支持。
- R3a/R3b：AlphaVantage、Finnhub 装配归位，日线/实时/名称和最新凭据绑定 49 passed（9.68s）；包括发现并修正测试中的计算型旧模块导入。
- R3c：Baostock 代码转换及美股协议识别归现有 Client，会话所有权不变；28 passed（3.38s）。
- R3d：Yfinance 共享符号转换归 common/symbols，保留各市场输入容错及原覆盖点；76 passed（3.46s）。
- R3e：Pytdx 主机解析与市场协议转换归 Client，连接冷却/轮询/断开保持；28 passed（3.63s）。
- R3f：Tushare HTTP 地址归 http，代码/交易日选择辅助归 Client；日线、实时、筹码、板块等 314 passed（23.50s）。
- R3g：Efinance 旧报价 DTO 归实时能力、历史 secid/错误格式化归日线、超时执行归 Client；原超时配置解析时机及缓存所有权保持；111 passed（9.48s）。
- R3h：Longbridge 协议、凭据、OAuth 缓存辅助归 Client，资源仍归同一门面；48 passed（4.33s）。测试保留原日志标签，协议 patch 改为实际消费位置。
- R3i：AkShare 实时解析/错误格式化归实时能力，进程执行/清理归 Client，涨跌停时间解析归涨跌停能力；316 passed（25.44s），包含真实 spawn/超时/回收。随后修正协议解析导入别名，避免覆盖统一实时 safe_float/safe_int；由最终全量复验覆盖。
- R3j：TickFlow 日线日期/截断/批量辅助归日线，共享协议归 Client，实时时间戳与限价适配归实时；保留窄纯函数回调及原共享缓存。全量数据源首轮发现提取后的日期依赖/类名引用遗漏，修正后相关 29 passed（6.65s）；静态检查补齐 List 类型导入，最终全量待验。
- R4：Manager 归 runtime/manager；板块与基本面格式化归能力、通用标量缺失判断归 common、市场纯规则归 domain/common；base 只剩薄公共导出。修正诊断/超时/持仓测试的旧模块替换位置，71 passed（7.07s）。审计 72 原文件/321 契约/945 引用/17 导出、0 错误；架构守卫通过。

目标及实际均为 137 Python 文件、19 下级目录，根仅 __init__.py/base.py。源码及独立干净依赖环境实际加载 17 项导出和 136 子模块；pip check 通过。R0–R4 共 14/15（93.3%），R5 正在完整门禁/冻结/部署验收，不计提前通过。

本轮发现 scripts/test.sh 的嵌入 Python 和语法文件清单仍引用 AkShare/Yfinance 旧路径，已迁移后重新执行完整门禁。此类引用不属于 Python AST 文件扫描可覆盖范围，脚本/工作流需与审计结果一起核对。


### R5 验收结果（含前序失败记录）（2026-11-06）

| 检查 | 本轮实际结果 |
| --- | --- |
| 目标目录对账 | 137 个 Python 文件、19 下级目录逐项一致；根仅 __init__.py/base.py |
| 历史契约审计 | 原 72 文件、321 契约继续检查，945 引用与 17 项绝对路径惰性导出，0 错误；22 旧内部路径退出有规范映射 |
| 固定顺序相关检查 | 数据源 + 架构脚本 + 打包契约：634 passed / 1 skipped / 2 deselected（42.06s） |
| 完整随机序门禁首轮 | seed=20261106：5864 passed / 2 failed / 1 skipped / 4 deselected / 27 warnings / 511 subtests（486.97s）；失败仅是 ADR 结构测试仍要求 stocksdk_bridge.py 旧路径 |
| 结构测试纠正 | 迁移预期到 clients/stocksdk/bridge.py，登记 10 厂商/Manager/公共符号路径及两个根入口；ADR 补充实施落点；2 passed（3.50s）；完整门禁最终重跑全部通过，见下行 |
| 完整随机序门禁最终 | seed=20261106：5866 passed / 1 skipped / 4 deselected / 27 warnings / 511 subtests（386.15s），语法/架构/关键静态/确定性检查和全量离线测试均通过 |
| CI 递归语法检查 | ci_gate.sh 改为 compileall -q data_provider，覆盖迁入的全部子目录；bash -n 与 syntax 阶段通过 |
| 干净依赖环境 | pip check 无冲突；源码 17 项导出 / 136 子模块实际加载通过 |
| 干净环境冻结产物 | PyInstaller 6.22.3 新构建完成；243 个代码对象签名检查通过；--help 及 alphasift.dsa_adapter、futu、orjson、data_provider 探针均通过；17 项导出 / 136 子模块实际加载 |
| 冻结 spawn worker | 外部驱动只将 worker 执行入口设为新冻结程序，移除仓库路径与驱动重载；新 clients.akshare.client worker 能返回结果并退出。外部驱动 tracker 留在其真实解释器，避免混合解释器 flags；不以此额外声称覆盖整个冻结父进程的 tracker 启动链路 |
| 冻结后端启动 | 临时目录/临时 DB/OS 分配空闲端口运行 --serve-only，/api/health 返回 200（56 字节），仅停止本次进程并清理临时 DB，既有服务未动 |
| 前序标准 Docker 两次构建（历史） | Web 阶段通过，Pro CSS 已不是本轮阻塞；两次运行时系统包安装均遇 Debian CDN 的多个 HTTP 502，镜像未完成，未运行最终容器 |
| Windows/Intel/Desktop 窗口 | 本轮未补验，沿用 §6 的既有范围与缺口；本轮原生 ARM64 后端成功不能替代客户端或其他平台验收 |

冻结产物在 `/tmp/hermesx-root-r5-frozen/dist/stock_analysis`。首次受限构建在 SDK 默认日志及 PyInstaller 二进制缓存权限失败，已在允许相应访问后重新构建，未使用失败产物。服务探针使用临时 DB，未修改项目或系统端口配置。

最终全量门禁日志 `/tmp/hermesx-root-r5-backend-final.log` 已完成并通过。Docker 两次失败日志分别为 `/tmp/hermesx-root-r5-docker.log`、`/tmp/hermesx-root-r5-docker-retry.log`；不为网络问题顺手改 Docker 基础镜像、系统源、依赖或用户前端。


### 本轮退出的 22 个根模块与原契约覆盖

以下与审计脚本同一报告对账；列出的是旧内部深路径退出，包级公开导出继续保留。

| 旧模块文件 | 唯一新模块 / 符号目标 | 原公开调用检查数 |
| --- | --- | ---: |
| `data_provider/akshare_fetcher.py` | `data_provider.runtime.fetchers.akshare` | 13 |
| `data_provider/alphavantage_fetcher.py` | `data_provider.runtime.fetchers.alphavantage` | 3 |
| `data_provider/baostock_fetcher.py` | `data_provider.runtime.fetchers.baostock` | 3 |
| `data_provider/eastmoney_quote_snapshot.py` | `data_provider.market.eastmoney_source` | 1 |
| `data_provider/efinance_fetcher.py` | `data_provider.runtime.fetchers.efinance` | 9 |
| `data_provider/finnhub_fetcher.py` | `data_provider.runtime.fetchers.finnhub` | 3 |
| `data_provider/fundamental_adapter.py` | `data_provider.fundamentals.akshare_source` | 3 |
| `data_provider/longbridge_fetcher.py` | `data_provider.runtime.fetchers.longbridge` | 5 |
| `data_provider/pytdx_fetcher.py` | `data_provider.runtime.fetchers.pytdx` | 4 |
| `data_provider/realtime_types.py` | `data_provider.realtime.types` | 14 |
| `data_provider/stockdb_fetcher.py` | `data_provider.clients.stockdb` | 10 |
| `data_provider/stocksdk_bridge.py` | `data_provider.clients.stocksdk.bridge` | 19 |
| `data_provider/tencent_fetcher.py` | `data_provider.kline.daily_tencent_source` | 1 |
| `data_provider/tencent_quote_snapshot.py` | `data_provider.market.tencent_source` | 1 |
| `data_provider/tickflow_fetcher.py` | `data_provider.runtime.fetchers.tickflow` | 10 |
| `data_provider/tushare_fetcher.py` | `data_provider.runtime.fetchers.tushare` | 11 |
| `data_provider/tw_institutional_fetcher.py` | `data_provider.institutional.tw_client` | 3 |
| `data_provider/us_index_mapping.py` | `data_provider.common.symbols；src.domain.market.us_index_symbols` | 1 |
| `data_provider/wallstreetcn_calendar_fetcher.py` | `data_provider.calendar.wallstreetcn_source` | 3 |
| `data_provider/wallstreetcn_live_news_fetcher.py` | `data_provider.news.wallstreetcn_live` | 9 |
| `data_provider/yfinance_fetcher.py` | `data_provider.runtime.fetchers.yfinance` | 3 |
| `data_provider/yfinance_fundamental_adapter.py` | `data_provider.fundamentals.yfinance_source` | 1 |

data_provider/base.py 保留为薄公开兼容面；DataFetcherManager 的唯一实现是 runtime/manager.py，BaseFetcher 是 common/fetcher_contract.py，异常是 common/errors.py，纯规则是 domain。旧 base 异常 pickle GLOBAL 仍通过公开兼容面解析，不重新复制异常类型。


### 最终状态与后续边界

本轮 R0–R5 **15/15（100%）**：代码归位、固定/随机测试、审计、干净冻结、Docker Linux/ARM64 构建与容器运行验证已全部完成。前序网络失败保留为历史证据；最终镜像使用校验摘要后的本地官方 OCI 基础镜像输入，正式 Dockerfile 的安装步骤最多额外重试 3 次，失败仍非零退出。

本机默认镜像加速地址与直连网络依然可能影响新的标签解析，不把本次临时 OCI 构建输入当作已修复全局网络。原 B23 的 Windows/Intel/桌面窗口缺口独立保留，前端全量 lint 继续暂缓；无 Git 提交。

### Docker 续验：服务恢复与构建网络处理（2026-11-06，历史处理过程）

维护者启动 Docker 后，服务实测 29.8.2/aarch64 可用；普通构建仍有镜像加速地址 403 和 Debian 部分包 502，主机 HTTP 成功不能代替容器网络成功。以临时容器复核曾失败包：HTTP 下载 200/115116 字节，HTTPS 出现 EOF，未改 Docker 全局镜像加速或代理配置。

先验证 APT 的 Acquire::Retries 后发现部分 502 仍直接终止安装，故最终 Dockerfile 改为**一个安装步骤重试机制**：首次安装失败后最多重试 3 次（合计最多 4 次），持续失败非零退出；更新失败不继续安装，成功才清理索引。不叠加多层重试，不跳过软件包，不更换源或依赖。执行真实 RUN shell 的受控传输测试覆盖首次成功、失败恢复、耗尽失败、更新失败；连同入口/打包检查 **17 passed（8.11s）**，shell 测试使用封闭 PATH，不会在主机运行真实 apt-get/rm。

为独立验证项目而不修改本机失效镜像加速配置，将本地已拉取的官方 Node/Python 镜像保存为临时 OCI 布局，校验镜像索引 SHA-256，再以 Buildx 命名上下文提供给同一 Dockerfile。Node 摘要 `2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0`；Python 摘要 `94a8fee35252d06ab75856f15f12c7bae67b10e8a6da93c7fded82b2610926cd`。此为本次构建输入快照，不把它们写入产品配置或更改基础镜像声明。

构建命令：

```bash
docker buildx build --load -f docker/Dockerfile \
  --build-context node:20-slim=oci-layout:///tmp/hermesx-r5-official-bases-oci@sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0 \
  --build-context python:3.11-slim-bookworm=oci-layout:///tmp/hermesx-r5-official-bases-oci@sha256:94a8fee35252d06ab75856f15f12c7bae67b10e8a6da93c7fded82b2610926cd \
  -t hermesx:provider-root-r5 .
```

OCI 目录需先由本机可用官方镜像导出，本例不是可脱离该输入直接执行的通用部署命令。Buildx `--call=check` 通过；系统包首次安装 5 项 502，第二次只补下载剩余 3971 kB 后安装成功（173.6s），正在继续 Python 依赖与最终镜像阶段。完整镜像、容器导入与健康验证未结束前，R5 保持 14/15（93.3%）。中英文部署排障与 changelog 已同步。

参考：[Docker 命名/OCI 构建上下文](https://docs.docker.com/reference/cli/docker/buildx/build/#additional-build-contexts---build-context)。此前短暂的权限审核超时已通过重试解决，不是本次网络或项目失败的原因。


### Docker 最终镜像与容器验收（2026-11-06）

| 项目 | 最终结果 |
| --- | --- |
| 构建输入 | 当前 Dockerfile + 已校验摘要的本地官方 Node/Python OCI 命名上下文；未换依赖、软件源或全局镜像加速配置 |
| 最终镜像 | `hermesx:provider-root-r5`，Linux/ARM64，sha256:573862bdc2fe546f3d574525403c3def9331fbbd119b8b15fc3dda98cbd270cd |
| 镜像依赖 | 以 hrs 用户运行 pip check：No broken requirements found |
| 完整数据源 | 17 项公开导出、136 子模块全部加载；根两文件及 BaseFetcher/Manager 唯一身份断言通过 |
| 实际启动 | 使用镜像正式 entrypoint 和 --serve-only，主进程 /proc/1/status 确认为 UID 1000；不是用 docker exec 默认用户冒充运行身份 |
| HTTP | 由 Docker 分配临时宿主端口，/api/health 200（56 字节），Web 首页 200（1815 字节） |
| 清理 | 仅关闭带本次验收标签的容器；--rm 清理容器/匿名卷，未挂载仓库、用户数据或既有卷；原有 dev 服务继续运行 |
| 新增部署回归 | 17 passed（8.11s）；4 个受控 shell 反例覆盖成功/恢复/耗尽失败/更新失败，未在主机执行真实包安装或清理 |

构建日志 `/tmp/hermesx-root-r5-docker-oci.log`；容器断言日志 `/tmp/hermesx-root-r5-container-acceptance.log`；临时验收代码与官方基础镜像导出留在 /tmp，不合入仓库。此前无限重跑整次构建没有作为修复；最终是一个有上限的安装步骤重试机制，第二次安装仅补齐缺失包后成功，验证失败耗尽仍退出。

**R5 已关闭，15/15（100%）**。本次 Docker 修复不改 Python 后端业务代码；最后一次完整后端门禁仍为 5866 passed/511 subtests，新增部署逻辑另以 17 项定向回归和真实镜像/容器验证覆盖，不虚报包含新增测试的全量结果。中英文部署文档已同步，未修改 README、用户 CSS、并行图册或全局 Docker 配置，未 commit/push/tag。
