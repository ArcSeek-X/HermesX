# HermesX 测试体系迁移进度台账（TEST_SUITE_MIGRATION_PROGRESS）

> 本文件是 [TEST_SUITE_REFACTORING_PLAN.md](./TEST_SUITE_REFACTORING_PLAN.md) 第 8.2 节约定的**统一迁移记录**，集中维护「文件归属 + 切片状态 + 验证证据」，是本轮测试重构的唯一进度真源。
> 服务端五层迁移完成率（见 `ARCHITECTURE_MIGRATION_STATUS.md`）**不**代表本轮测试整理进度，两者独立计数。

| 项目 | 约定 |
| --- | --- |
| 关联方案 | TEST_SUITE_REFACTORING_PLAN.md v1.3 |
| 台账创建 | 2026-11-01 |
| 迁移基线 | `main`，收集基线 **5717 tests / ~5–7s**（含 network，`--collect-only`）|
| 推进口径 | 严格 T0→T5 分片、逐片验证、禁止一次性大爆炸搬迁 |
| Git | 全程不自动 commit/push/tag/PR，遵循 AGENTS.md，需用户授权 |

## 1. 事实基线（T0，2026-11-01 实测）

| 项目 | 实测值 | 说明 |
| --- | ---: | --- |
| `tests/` git 跟踪文件 | 306 | 与方案 §1 的 rg 口径一致 |
| 顶层 `test_*.py` | 294 | 方案基线写 298，属正常漂移，以工作树为准 |
| `tests/__init__.py` | 存在 | `tests` 是常规包（218 B，仅文档字符串） |
| 根 `conftest.py` | 295 行 | 全局 asyncio/anyio/TestClient 兼容补丁 + 会话级端口工厂（autouse），**对所有后代目录自动生效** |
| 既有子目录 | `agent/`（4 测试）、`fixtures/notification_reports/`（3 .md） | **均无 `__init__.py`** |
| 顶层非测试 .py | `conftest.py`、`litellm_stub.py`、`longbridge_live_smoke.py`、`tw_institutional_live_smoke.py` | 后两者为非默认收集在线脚本 |
| setup.cfg | `testpaths=tests`、`python_files=test_*.py`、`addopts=-v --tb=short`、markers=unit/integration/network/benchmark | 首轮保持不动 |

## 2. 依赖热点（决定哪些文件「不能裸搬」的闸门）

搬迁前必须逐文件核对以下四类，命中者要么先修路径、要么留待对应切片：

| 依赖类型 | 命中文件数 | 影响 | 处置策略 |
| --- | ---: | --- | --- |
| 仓库根路径推导 `parents[1]`/`parent.parent` | 40 | 目录深度变化后根路径算错 | 搬迁时改为「上溯到含 `src`/`main.py` 的目录」的健壮定位，或改用统一 `support/paths` 辅助（T4） |
| 包内导入 `from tests.litellm_stub` / `import tests` | 109 | 依赖 `tests` 包 + 仓库根在 sys.path | 保持 `litellm_stub` 现路径不动直到 T4；搬迁仅对**不使用它**的文件先行 |
| `sys.path` 就地操作 | 61 | 与目录深度耦合 | 随路径治理（T4）逐项收敛，搬迁前先排除 |
| 文档写死 `tests/test_xxx.py` 路径 | 多份 docs | 移动后文档回归证据断链 | 被文档引用的文件搬迁时**必须同片**更新 `docs/*.md`（含中英）与 CHANGELOG |

> 关键稳定器：只要文件仍在 `tests/` 之下、且 basename 全仓唯一，根 `conftest.py` 依旧生效、`from src...`/`from data_provider...` 绝对导入不受影响。真正需要治理的是上述四类**相对/包级**依赖。

## 3. 已验证的搬迁模板（T1 固化）

单个「干净文件」（无 §2 四类依赖、未被文档引用）的标准搬迁：

1. 预检：`grep` 确认文件不含 `parents[/parent.parent`、`sys.path`、`from tests`/`litellm_stub`，且不被其它测试 import、不被 docs 写死引用。
2. `mkdir -p tests/<边界>/<域>/` —— **不建 `__init__.py`**（沿用 `agent/`、`fixtures/` 既有且已验证约定）。
3. `git mv tests/test_x.py tests/<边界>/<域>/test_x.py`（保留历史，状态 `R`）。
4. 验证：全量 `--collect-only -q` 数量必须与基线一致（当前 **5717**）；对被搬文件所在目录跑 `pytest <新目录> -q` 必须全绿。
5. 本台账追加一行记录（原→新、被测职责、依赖、状态、证据）。

## 4. 切片记录

### T1 低耦合试点（✅ 已完成并验证，2026-11-01）

搬迁前基线与搬迁后收集均为 **5717**；4 个被搬文件合并运行 **331 passed / 0 failed**。

| 原路径 | 目标路径 | 被测职责（SUT） | 依赖 | 状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `tests/test_portfolio_risk_rules.py` | `tests/domain/portfolio/test_portfolio_risk_rules.py` | `src.domain.portfolio.risk_rules` 纯规则 | 无 | ✅ | collect 5717；子集 passed |
| `tests/test_decision_action.py` | `tests/domain/decision/test_decision_action.py` | `src.domain.decision.action`/`scale` 纯规则 | 无 | ✅ | 同上 |
| `tests/test_pipeline_domain_rules.py` | `tests/domain/analysis/test_pipeline_domain_rules.py` | `src.domain.analysis.pipeline_rules` 纯规则 | 无 | ✅ | 同上 |
| `tests/test_stock_code_utils.py` | `tests/application/quote/test_stock_code_utils.py` | `src.application.quote.stock_code_utils` + `data_provider.base`（文件名似 domain，实为 application 边界，按 §2 决定归 application） | 无 | ✅ | 同上 |

新建目录：`tests/domain/{portfolio,decision,analysis}`、`tests/application/quote`（均无 `__init__.py`）。

### T1 批 2：纯 domain 单边界叶子测试（✅ 已验证，2026-11-01）

9 个「单一 `src.domain.*` 边界 + 无 P/S/K/`__file__` 依赖 + 非文档引用」文件，`git mv` 到 `tests/domain/<子域>/`：

| 目标 | 文件 |
| --- | --- |
| `domain/backtest/` | test_backtest_summary |
| `domain/decision/` | test_decision_profile_policy / _signal_data_quality / _signal_summary |
| `domain/generation/` | test_llm_response_content |
| `domain/market/` | test_market_symbol_utils / test_stock_list_parser |
| `domain/notification/` | test_notification_routing |
| `domain/shared/` | test_report_language |

排除（文档写死引用，留待带文档同步的 T2 切片）：`test_backtest_engine`（full-guide_EN.md）、`test_trading_calendar`（market-support.md）。验证：`--collect-only` **5717**；`tests/domain`+`tests/application` **382 passed**。

### T1 批 3：application 单边界叶子测试（✅ 已验证，2026-11-01）

29 个「单一 `src.application.*` 边界 + 无 P/S/K/`__file__` 依赖 + 非文档引用」文件，按 AST 被测边界 `git mv` 到 `tests/application/<域>/`（agent/analysis/history/market/notification/portfolio/quote/reporting/runtime/usage）。排除（文档写死引用）：`test_daily_market_context`、`test_scheduler_background`。

> ⚠️ **关键方法论修正（本批发现）**：`pytest tests/application` 子集跑出 `test_portfolio_alerts` 4 例假红，根因是 `configure_portfolio_repository()` 由**兄弟测试模块的导入期副作用**配置全局端口（`test_portfolio_service/api`、`test_alert_api`、`test_decision_signal_*` 等仍在顶层），子集未收集配置方 → 端口未就绪。**这不是搬迁引入的回归**，而是既有顺序耦合（`test_portfolio_alerts` 自身不配置端口、依赖他者先配置），归 **T4 治理**（应改为自带 `configure_portfolio_repository()` 或局部 fixture）。
> **结论：纯搬迁片必须以「全量 `pytest -m "not network"`」为权威验收；子集跑可能因导入期全局副作用假红，须先判定顺序耦合再下结论。**

累计 T1（试点 4 + 批 2 的 9 + 批 3 的 29 = **42 个文件**）后跑**全量离线门禁**：`5713 passed, 4 deselected, 0 failed`（250s），与历史基线一致，**零回归**。顶层 `test_*.py` 由 294 降至 252。

### T1 批 4：config/settings + api/common 无歧义归属（✅ 已验证，2026-11-01）

方案 §3.1 已明确列出、归属无歧义的 7 个文件（均单一边界 + 无 P/S/K/`__file__` + 非文档引用）：

| 目标 | 文件 |
| --- | --- |
| `tests/config/settings/` | test_config_manager / test_config_module_split / test_news_strategy_config |
| `tests/api/common/` | test_api_health / test_api_app_cors / test_api_error_helpers / test_mimetypes_windows_init |

验证：`--collect-only` **5717**；子集 **37 passed**；**累计 49 文件**后再跑全量离线门禁 `5713 passed, 4 deselected, 0 failed`（257s）、**零回归**。顶层 `test_*.py` 降至 245。

### T1 批 5：infrastructure/providers 按能力 + infrastructure 细分（✅ 已验证，2026-11-01）

16 个「单一 data_provider/infrastructure 边界 + 无 P/S/K/`__file__` + 非文档引用」文件，按方案 §3.3「数据源按能力优先」`git mv`：

| 目标 | 文件 |
| --- | --- |
| `infrastructure/providers/kline/` | test_kline_endpoint_refactor / test_stooq_fallback / test_yfinance_normalize |
| `infrastructure/providers/realtime/` | test_akshare_realtime_logging / test_hk_realtime_routing |
| `infrastructure/providers/common/` | test_data_fetcher_manager_hk_bare_code / test_fetcher_source_optimization / test_stocksdk_bridge_and_sources / test_provider_cache |
| `infrastructure/providers/code_search/` | test_stock_code_bse / test_yfinance_hk_bare_code |
| `infrastructure/providers/stock_info/` | test_tencent_stock_info_source |
| `infrastructure/providers/fundamentals/` | test_yfinance_fundamental_adapter |
| `infrastructure/notification/senders/` | test_feishu_stream |
| `infrastructure/observability/` | test_logging_config |
| `infrastructure/search/` | test_search_serpapi_provider |

排除（文档引用，归 T2）：test_a_share_fetcher_code_conversion / test_realtime_types / test_stockdb_transform / test_llm_param_recovery；排除（用 `__file__`，归 T2）：test_schema_migration_guard。验证：collect **5717**；**累计 65 文件**后全量离线门禁 `5713 passed, 4 deselected, 0 failed`（249s）、**零回归**。顶层 `test_*.py` 降至 229。

### T1 批 6：api 按能力 + infrastructure(security/brokers/indexing) + tooling（✅ 已验证，2026-11-01）

增强盘存（新增 `__file__` 列）后，取「单一被测边界 + 无 P/S/K/`__file__` + 非文档引用」且归属可由方案 §3 目录树/§映射表直接确定的 8 个文件：

| 目标 | 文件 | 归属依据 |
| --- | --- | --- |
| `api/quote/` | test_stock_watchlist_api / test_stocks_timeline_api | 方案 line 197「stocks、kline 与 timeline HTTP 契约」 |
| `api/common/` | test_decision_signal_contract_isolation | 跨 schema 契约守卫（非端点专属），与批 4 通用 API 契约同组 |
| `infrastructure/security/` | test_auth / test_cwe345_xff_bypass | 方案 line 263「密码/会话/可信代理实现」；XFF=get_client_ip 可信代理 |
| `infrastructure/brokers/` | test_futu_portfolio_service | 方案 line 182「Futu 等经纪商适配」 |
| `infrastructure/indexing/` | test_stock_index_loader | 方案 line 180「股票索引与映射文件加载」 |
| `tooling/test_runtime/` | test_threadless_test_client | 方案 line 294「TestClient 兼容 shim → tooling/test_runtime」 |

仍排除（文档写死引用，归 T2）：test_daily_market_context、test_scheduler_background、test_backtest_engine、test_trading_calendar（+ 批 5 已列 4 项）。验证：collect **5717**；**累计 73 文件**后全量离线门禁 `5713 passed, 4 deselected, 0 failed`（252s）、**零回归**。顶层 `test_*.py` 降至 221。

## 4A. T2 首切片：单一边界但被文档写死引用的 8 件（✅ 已验证，2026-11-01）

这 8 件无 P/S/K/`__file__` 搬迁 hazard，唯一障碍是被用户可见文档当**活动指针**（可执行 pytest 命令/回归验收路径）引用；方案 §4 已给出确定归属，故搬迁与文档同步同片完成（仅改活动指针，不改迁移台账/CHANGELOG 历史叙述）：

| 新路径 | 同步的文档（中英） |
| --- | --- |
| `application/market/test_daily_market_context.py` | analysis-context-pack.md |
| `application/runtime/test_scheduler_background.py` | run-diagnostics-p3.md（含组合命令） |
| `infrastructure/providers/common/test_a_share_fetcher_code_conversion.py` | run-diagnostics-p0.md |
| `infrastructure/providers/realtime/test_realtime_types.py` | run-diagnostics-p3.md |
| `infrastructure/providers/kline/test_stockdb_transform.py` | stock_data_view.md |
| `domain/backtest/test_backtest_engine.py` | full-guide.md + full-guide_EN.md |
| `domain/market/test_trading_calendar.py` | market-support.md |
| `infrastructure/generation/backends/test_llm_param_recovery.py` | LLM_CONFIG_GUIDE.md + LLM_CONFIG_GUIDE_EN.md |

依据：providers/common（跨能力归一 A 股前缀码）、providers/kline（重采样/复权）、generation/backends（方案 line 288）。验证：`--collect-only` **5717**；`docs/` 与根 `*.md` 旧顶层路径引用残留 **0**（排除 CHANGELOG）；`scripts/`+`.github/` 无硬编码引用；**累计 81 文件**后全量离线门禁 `5713 passed, 4 deselected, 0 failed`（243s）、**零回归**。顶层 `test_*.py` 降至 213。未改 `setup.cfg`/conftest/stub，未提交。

## 4B. K 类（`from tests.litellm_stub`）安全性验证 + 单边界搬迁（✅ 已验证，2026-11-01）

**关键认知修正**：盘存中的 K 标记全部是 `from tests.litellm_stub import ensure_litellm_stub` 绝对包导入，经 `tests` 包 + 根 conftest 注入的仓库根 sys.path 解析，**与子目录深度无关**——前 81 件零回归已间接证实，本片直接拿 K-无P/S/F 文件做实证：先搬 3 件（akshare_history_timeout → providers/kline、hk_stock_name_fallback → providers/realtime、tushare_fetcher_http_client → providers/common）后 collect 仍 **5717**、新位置定向 **26 passed**，确认 `from tests.litellm_stub` 在子目录仍解析。再补 2 件（litellm_fallback_pricing → agent_runtime（llm_adapter，§177）、tushare_fetcher_followups → providers/common（trade calendar + 限速））。

| 新路径 | 能力依据 |
| --- | --- |
| `infrastructure/providers/kline/test_akshare_history_timeout.py` | 方案 line 283 显式 |
| `infrastructure/providers/realtime/test_hk_stock_name_fallback.py` | _get_hk_realtime_quote 实时报价名降级 |
| `infrastructure/providers/common/test_tushare_fetcher_http_client.py` | 方案 line 286（通用 HTTP client） |
| `infrastructure/providers/common/test_tushare_fetcher_followups.py` | get_trade_time + 限速→跨能力归一（§161） |
| `infrastructure/agent_runtime/test_litellm_fallback_pricing.py` | llm_adapter §177（贴被测模块，不猜 telemetry） |

方法论结论：**K 不是搬迁阻断项**，仅需 P/S/F（深度敏感）才需改代码。验证：**累计 86 文件**后全量离线门禁 `5713 passed, 4 deselected, 0 failed`（246s）、**零回归**。顶层 `test_*.py` 降至 208。未改代码/stub/conftest，未提交。待办：litellm_stub 本体→support/stubs 仍归 T4（牵动 22+ 处引用）。

## 4C. T4 地基：`support/paths::get_repo_root()` + 首个 P 类转换（✅ 已验证，2026-11-01）

按用户定策略（建统一根辅助而非逐点 bump），新建 `tests/support/paths.py`：以仓库根三件套（`setup.cfg`+`pyproject.toml`+`main.py` 同时命中）自 `__file__` 向上回溯，**与子目录深度无关**。实测：`tests/support/` 无 `__init__.py` 仍可 `from tests.support.paths import get_repo_root`（tests 常规包 + 命名空间子包 + 根 conftest 注入仓库根 sys.path）。

首个 P 类切片（`parents[1]` 求仓库根）——转换代码用 `get_repo_root()` 后 `git mv`（需同时保留 `pathlib.Path` 导入，因多个文件在类型标注里裸用 `Path`）：

| 新路径 | 原仓库根用法 |
| --- | --- |
| `config/settings/test_config_env_compat.py` | 读 `.env.example` |
| `config/deployment/test_docker_entrypoint.py`（新建） | 读 docker/*、requirements、docs |
| `api/contract/test_api_schema_pydantic.py`（新建） | 读 documents/archify/api_spec.json |
| `infrastructure/providers/kline/test_tencent_fetcher.py` | 子进程 cwd（daily K-line fetcher） |

暂缓（跨切 CI/文档契约，归主边界就近不清晰，待 integration/docs-contract 桶）：`test_daily_analysis_workflow_notification_env`、`test_decision_signal_docs`。验证：`--collect-only` **5717**；4 件定向 **92 passed**；**累计 90 文件**后全量离线门禁 `5713 passed, 4 deselected, 0 failed`（255s）、**零回归**。顶层 `test_*.py` 降至 204。未提交。

### 回滚方式（本片）

```bash
git mv tests/domain/portfolio/test_portfolio_risk_rules.py tests/test_portfolio_risk_rules.py
git mv tests/domain/decision/test_decision_action.py      tests/test_decision_action.py
git mv tests/domain/analysis/test_pipeline_domain_rules.py tests/test_pipeline_domain_rules.py
git mv tests/application/quote/test_stock_code_utils.py   tests/test_stock_code_utils.py
```

随后 `--collect-only` 应回到 5717、顶层文件数恢复。本片仅移动 4 个无依赖文件，未触碰 conftest/stub/配置/文档。

## 4D. S 类：data_provider fetcher 测试统一根注入 + 按能力搬迁（✅ 已验证，2026-11-01）

S 类特征：`sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))`——仓库顶层自注入的**冗余**根路径 idiom（根 conftest 已保证仓库根在 sys.path 上），搬迁后 `'..'` 随深度失配。修法：改用 `get_repo_root()`（复用 4C 地基），保留该行为等价的显式注入以最小化语义变化；若替换后 `os.` 再无其它用法则删 `import os`（本批 10 件删、4 件保留：alphavantage/finnhub/longbridge/tickflow_manager_routing 他处仍用 os）。经画像确认这 15 件（含样板 `test_yfinance_us_indices`）均为**单一被测边界（仅触 `data_provider.*`）、docref clean、无 `parents`/其它 `__file__`**，据方案 §3.2 能力子目录归位：

| 能力子目录 | 文件 |
| --- | --- |
| `providers/kline` | test_yfinance_us_indices（样板）、test_efinance_main_indices、test_etf_daily_routing、test_tickflow_fetcher |
| `providers/realtime` | test_longbridge_fetcher |
| `providers/fundamentals` | test_fundamental_adapter、test_fundamental_context |
| `providers/institutional`（新建） | test_tw_institutional_fetcher、test_tw_institutional_network、test_tw_institution_report_wiring |
| `providers/common` | test_alphavantage_fetcher、test_finnhub_fetcher、test_tickflow_manager_routing、test_tickflow_market_review_fallback、test_fetcher_logging |

判定依据：日线/指数/ETF/历史取数 → kline；Longbridge 港美股实时报价 → realtime；fundamental 适配/上下文 → fundamentals；TW 机构/资金流 → institutional；跨能力的通用 HTTP 取数与 `_normalize_data` 归一、manager 选源/降级路由、fetcher 日志 → common（方案 line 161「选源、限速与跨能力归一」）。`test_tw_institutional_network` 带 `@pytest.mark.network`，离线门禁自动 deselect（2 例），搬迁不改变其收集属性。遗留既有风格项（F401 `logging` 未用属 HEAD 既有、非本批引入；E123/W293 等）不在门禁 `--select=E9,F63,F7,F82` 阻断集内，按最小改动不顺手改。验证：`--collect-only` **5717**；`tests/infrastructure/providers/` 定向 **377 passed / 2 deselected**；**累计 105 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（255s）、**零回归**。顶层 `test_*.py` 降至 189。门禁级 flake8（E9,F63,F7,F82）对搬迁目录干净。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

逐件 `git mv` 回顶层即可，例：`git mv tests/infrastructure/providers/kline/test_yfinance_us_indices.py tests/test_yfinance_us_indices.py`；代码改动仅 S 行与 `import os`/`get_repo_root` 导入，可 `git checkout --` 还原。未触碰 conftest/stub/配置/文档。

## 4E. S 类非-provider 单一边界件：agent/analysis 扁平 + generation/telemetry、persistence 新建（✅ 已验证，2026-11-01）

继 4D 后，继续处理剩余 **单一被测边界、docref clean、无 `parents`/其它 `__file__`** 的非-provider S 件（同样 `..` 根注入 idiom 改用 `get_repo_root()`）；按§3.3「只有 1-2 个测试文件的能力直接放二级目录」与现有 `application/agent`/`application/analysis` **扁平**先例，不为其新建三级子目录：

| 新路径 | 文件 | 边界 |
| --- | --- | --- |
| `application/agent/`（扁平） | test_data_tools_get_capital_flow、test_data_tools_get_stock_info、test_data_tools_portfolio_snapshot、test_agent_orchestrator_sniper_fallback、test_provider_trace | agent 用例/工具/编排/provider trace |
| `application/analysis/`（扁平） | test_pipeline_prefetch_dry_run、test_stock_data_port | 分析 pipeline 预取 dry-run、股票数据端口 |
| `infrastructure/notification/senders/` | test_notification_sender | 通知渠道发送实现 |
| `infrastructure/generation/telemetry/`（新建） | test_llm_adapter_provider_trace | provider trace 技术实现（方案 line 173/288） |
| `infrastructure/persistence/`（新建） | test_storage | ORM/建表/仓储基座（os 多处仍用→保留 `import os`） |

转换明细：9 件 os 仅 S 行→删 `import os`；仅 test_storage os 多处使用→保留。验证：`--collect-only` **5717**；10 件定向 **178 passed**；**累计 115 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（249s）、**零回归**。顶层 `test_*.py` 降至 179。门禁级 flake8（E9,F63,F7,F82）对搬迁目录干净；docs/scripts/.github 无残留旧顶层路径引用。未改 conftest/setup.cfg/stub，未提交。

尚未搬迁的其余 S 件均属多边界（pipeline_*/agent_*/notification_*/chat_context/multi_agent/run_diagnostics_*/tw_report_consumption 等）→ **归 T3**「主边界就近 + integration」；或带 `parents`/其它 `__file__`/docref（如 test_agent_pipeline parents+docs×5、test_agent_registry parents=4、test_notification_report_fixtures 其它 `__file__`、test_yfinance_hk/jp_kr_indices docref market-support.md）需配合专项修正。临时转换脚本已删除，未入库。

### 回滚方式（本片）

逐件 `git mv` 回顶层；代码改动仅 S 行与 `import os`/`get_repo_root` 导入，可 `git checkout --` 还原；新建的 `generation/telemetry/`、`persistence/` 空目录可随手回收。未触碰 conftest/stub/配置/文档。

## 4F. P 类续批：tooling 四子目 + bootstrap/entrypoints + domain/notification（✅ 已验证，2026-11-01）

转入 P 类（`Path(__file__).resolve().parents[1]` / `.parent.parent` 求仓库根读文件）。先取**单一边界、docref clean、仅 1 处求根表达式、无 `syspath`** 的低歧义子批：将求根表达式统一换为 `get_repo_root()`（与 `parents[1]` 行为等价，均为仓库根），在列 0 模块级导入区末尾插入 `get_repo_root` 导入；并以 **`\bPath\b`（排除 import 行、含类型标注裸用）** 判据在 Path 再无他用时删 `from pathlib import Path`（本批 11 件删、仅 test_packaging_build_scripts 因 `path: Path`/`tmp_path: Path` 标注多处使用→保留，实证判据对标注感知可靠）：

| 新路径 | 文件 |
| --- | --- |
| `tooling/scripts/`（新建） | test_build_release_notes、test_check_env_encoding |
| `tooling/docs/`（新建） | test_alerts_docs、test_searxng_env_docs、test_analysis_context_pack_docs |
| `tooling/workflows/`（新建） | test_ai_review_github_api |
| `tooling/packaging/`（新建） | test_desktop_installer_config、test_desktop_packaging_assets、test_packaging_build_scripts、test_futu_distribution_contract |
| `bootstrap/entrypoints/`（新建） | test_bootstrap_entrypoints |
| `domain/notification/` | test_notification_rendering |

暂缓目标模糊件：`test_data_provider_adr_structure`（adr 结构 vs architecture 待定）、`test_kline_schema`（读 api schema 源文件，归属需区分契约/架构）；其余带 `parents` 且多边界（bot_use_case_wiring parents=4、decision_signal_api/service 重锈混合、image_stock_extractor_vision_port、kline/limit_pool/sector endpoint wiring、config_registry parents=8+docref、agent_backend/frozen_context）→ **归 T3**；带 `syspath`+`parents` 双修件（agent_pipeline/registry、fetch_tushare_stock_list、generate_index_from_csv、refresh_stock_index、static_assets_consistency）需同时改 S+P。验证：`--collect-only` **5717**；12 件定向 **93 passed**；**累计 127 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（244s）、**零回归**。顶层 `test_*.py` 降至 167。门禁级 flake8（E9,F63,F7,F82）对新建目录干净；docs/scripts/.github 无残留旧顶层路径引用。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

逐件 `git mv` 回顶层；代码改动仅求根表达式与 `pathlib`/`get_repo_root` 导入，可 `git checkout --` 还原；新建的空目录可随手回收。临时转换脚本已删除、未入库。

## 4G. S 类尾部 provider 残留子批：yfinance hk/jp_kr + us_index_mapping（✅ 已验证，2026-11-01）

F 类盘存结论：纯「同目录旁资源」型 F 极少，绝大多数 `__file__` 用法要么与已导入生产模块绑定的 `Path(module.__file__)`（搬迁安全），要么与多边界/`syspath`+`parents` 双修纠缠（归 T3）——干净 F 子批不成立。据此转做 S 类尾部的 3 个 provider 残留件，因转换语义各异（标准 `'..'`、注入 `data_provider` 子目录的变体），逐件精确改而非脚本：

| 新路径 | 文件 | 转换 |
| --- | --- | --- |
| `infrastructure/providers/kline/` | test_yfinance_hk_indices | 标准 `'..'` S 模式→`get_repo_root()`，os 仅 S 行→删 `import os` |
| `infrastructure/providers/kline/` | test_yfinance_jp_kr_indices | 同上 |
| `infrastructure/providers/kline/` | test_us_index_mapping | 变体 S：注入 `<repo>/data_provider` 子目录→`get_repo_root() / 'data_provider'`，保留直连导入语义，删 `import os` |

暂缓 `test_tushare_fetcher_get_stock_list`：该件支持脱离 pytest 独立运行（docstring 有 `python3 tests/...`），且在 `_PROJECT_ROOT` 计算前引入 `get_repo_root` 会造成独立运行下的自举死循环（既做 sys.path 又 `load_dotenv` 读 .env）→留待专项/T3。文档同步：hk/jp_kr 被 `docs/market-support.md`（line 31 回归覆盖路径、line 64 离线验证命令）当活动指针引用，随搬迁更新为新路径（该文档仅中文版，无中英对需同步）；us_index_mapping、tushare 无 docref。验证：`--collect-only` **5717**；3 件定向 **41 passed**；**累计 130 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（230.53s）、**零回归**。顶层 `test_*.py` 降至 164。门禁级 flake8（E9,F63,F7,F82）干净；docs/scripts/.github 无残留旧顶层路径引用。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

逐件 `git mv` 回顶层；代码改动仅 S 行与 `import os`/`get_repo_root` 导入；`market-support.md` 两处路径引用 `git checkout --` 还原。未新建目录（复用既有 providers/kline）。

## 4H. 转入「分类搬迁」阶段：路径干净件的边界归位（首批 bootstrap+agent seam，✅ 已验证，2026-11-01）

S/P 路径治理对单一边界件已穷尽后，重新盘存顶层 164 件：修正早前 awk 口径误报，实测 **105 件 `sys.path`/`parents`/`__file__` 全为 0**（路径完全干净，无需任何代码修正，仅需按被测边界归类 + `git mv`，属纯分类搬迁），余 59 件带 hazard（归 T3/专项）。据此从 T2 机械路径修正转入“分类搬迁”新阶段。该阶段每件需人工判边界，歧义度高于路径批，按“质量优于数量”取边界最无歧义、docref clean 的子批开工：

| 新路径 | 文件 | 边界依据 |
| --- | --- | --- |
| `bootstrap/`（二级直放） | test_bootstrap_api_lifecycle / _database / _environment / _scheduling | 主题即 `src.bootstrap.*` 装配（导入的 runtime_scheduler/api.deps 正是被装配对象） |
| `application/agent/` | test_agent_conversation_port_seam / test_agent_tools_db_seam | agent 域窄端口/db seam，与同目录既有 provider_trace/conversation_manager 同类 |

暂缓：agent route/surface（test_agent_litellm_route_resolution/test_agent_tool_surface）实跨 app+infra/agent_runtime 层；search 组 5 件、backtest 中 service/repo_record_mapping 跨 app/intelligence+infra/persistence 多层→归 T3 谨慎定边界。验证：`--collect-only` **5717**；6 件定向 **46 passed**；**累计 136 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（223.48s）、**零回归**。顶层 `test_*.py` 降至 158。无代码改动（纯 git mv）；docs/scripts/.github 无残留旧顶层路径引用。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

6 件逐件 `git mv` 回顶层即可（零代码改动、零新建目录，bootstrap/ 与 application/agent/ 均为既有目录）。

## 4I. 分类搬迁批 2：深度模块画像定位 application/quote+analysis+persistence 单边界件（✅ 已验证，2026-11-01）

对剩余 99 件路径干净件逐件取 `src.层.域` 导入计数（主导边界启发式），再读实际导入行确认主题（避免计数误判，如 image_stock_extractor 已迁 `src.application.analysis`）：

| 新路径 | 文件 | 主题依据（主导导入） |
| --- | --- | --- |
| `application/quote/` | test_intraday_timeline_service | `src.application.quote.intraday_timeline_service`（单一） |
| `application/quote/` | test_stock_service | `src.application.quote.{service,stock_service}` | QuoteService/StockService |
| `application/analysis/` | test_eod_picker_service | `src.application.analysis.eod_picker_service`（单一） |
| `application/analysis/` | test_analysis_context_builder | `src.application.analysis.analysis_context_builder`（主导） |
| `application/analysis/` | test_image_stock_extractor_litellm | `src.application.analysis.image_stock_extractor` |
| `infrastructure/persistence/` | test_storage_schema_upgrade | `src.infrastructure.persistence.{base,models.*}` schema 升级（主导 5） |

**口径纠偏（重要）**：本任务盘存脚本的 docref 扫描只覆盖 `docs/`，漏了 `documents/`；逐件搬迁后残留核对（含 `documents/`）拦截到——`test_eod_picker_service` 被 `documents/product/技术信号扫描/scanner.md:128` 当既有回归路径引用，已同步为新路径（line 127 signal_scanner 本批未搬→不动）。**后续批的 docref 扫描必须同时覆盖 `docs/` 与 `documents/`**。验证：`--collect-only` **5717**；6 件定向 **93 passed**；**累计 142 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（253.57s）、**零回归**。顶层 `test_*.py` 降至 152。零代码改动（纯 git mv）；docs/documents/scripts/.github 无残留旧顶层路径引用。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

6 件逐件 `git mv` 回顶层 + `scanner.md:128` 一行路径 `git checkout --` 还原。零新建目录（三个目标目录均既有）。

## 4J. 分类搬迁批 3：新建 application/intelligence + market/sender 单边界件（✅ 已验证，2026-11-01）

延续批 2 方法（导入计数 + 读实际行定主题），本批 docref 扫描**已同时覆盖 `docs/` 与 `documents/`**（吸取 §4I 口径纠偏）：

| 新路径 | 文件 | 主题依据 |
| --- | --- | --- |
| `application/intelligence/`（新建） | test_importance_rescale | sole `src.application.intelligence.intelligence_service` |
| `application/intelligence/`（新建） | test_social_sentiment_service | sole `src.application.intelligence.social_sentiment_service` |
| `application/market/` | test_market_light_service | `src.application.market.*`（market_light/review/analyzer）主导 3 |
| `infrastructure/notification/senders/` | test_dingtalk_sender | sole `...senders.dingtalk_sender` + config |

**api 端点批暂缓决策**：`tests/api/` 根下目前仅有主题子目录（common/quote/contract）、无直放件，且库存含大量 `*_api` 端点件（usage/auth/alert/portfolio/system_config/watchlist/intelligence/…）；为不零散破坏 api 目录约定，把 usage_api 等 `*_api` 件拆出，留待专门的“api 端点批”统一定 api/ 归类结构。decision_signal_extractor（含 3 处 bootstrap.configure_* 装配、跨 decision+analysis）也暂缓→后续/T3。验证：`--collect-only` **5717**；4 件定向 **45 passed**；**累计 146 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（234.13s）、**零回归**。顶层 `test_*.py` 降至 148。零代码改动（纯 git mv）；docs/documents/scripts/.github 无残留旧顶层路径引用。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

4 件逐件 `git mv` 回顶层；新建的空目录 `application/intelligence/` 可随手回收（market/senders 为既有目录）。

## 4K. api 端点批（镜像子目录）：10 个路径干净 `*_api` 件按端点域归位（✅ 已验证，2026-11-01）

经用户确认采用**与 `api/v1/endpoints/` 1:1 镜像的 `tests/api/<domain>/` 子目录**结构（而非扁平/粗粒度）。先筛顶层 14 个 `*_api`：路径干净 11 件（本批先做 docref-clean 的 **10** 件，system_config_api 含 5 处中英文档活动指针拆为独立 doc-sync 子片）、带 hazard 3 件（agent_conversation_api/backtest_api 含 `__file__`、decision_signal_api 含 parents+`__file__`→延后）。逐件用路由路径核对端点归属（避免目录命名错配）：

| 新子目录 | 文件 | 端点路由证据 |
| --- | --- | --- |
| `api/agent/` | test_agent_chat_api, test_agent_models_api | `/api/v1/agent/`, `endpoints.agent` |
| `api/alerts/` | test_alert_api | `/api/v1/alerts/` |
| `api/alphasift/` | test_alphasift_api | `/api/v1/alphasift/` |
| `api/auth/` | test_auth_api | `/api/v1/auth/`（主） |
| `api/decision_signals/` | test_decision_signal_outcome_api | 端点 decision_signals |
| `api/intelligence/` | test_intelligence_api | `/api/v1/intelligence/` |
| `api/portfolio/` | test_portfolio_api | `/api/v1/portfolio/` |
| `api/usage/` | test_usage_api | `/api/v1/usage/` |
| `api/watchlist/` | test_watchlist_api | bootstrap.watchlist |

既有 `api/{common,contract,quote}` 不动（T1 已验）；新建 9 个端点域子目录。**关键验证点**：子集跑 10 件时 decision_signal_outcome（4）+ portfolio（1）共 5 例 FAILED——经全量门禁复跑为 **5713 passed / 4 deselected / 0 failed**，判定为**既有 seam/导入顺序耦合子集假红**（bootstrap.configure_* 端口装配在跨模块导入期发生，子集跑不走完整装配链），非搬迁引入：10 件均路径干净、零代码改动、根 conftest 一致适用，与历史基线同口径。验证：`--collect-only` **5717**；**累计 156 文件**后全量离线门禁 `5713 passed / 4 deselected / 0 failed`（232.37s）、**零回归**。顶层 `test_*.py` 降至 138。docs/documents/scripts/.github 无残留旧顶层路径引用。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

10 件逐件 `git mv` 回顶层；新建的 9 个 `api/<domain>/` 空目录可随手回收（零代码改动）。子集假红与本批无关，回滚不变化。

## 4L. api 端点批 doc-sync 子片：system_config_api 归位 + 5 文档 9 处活动指针同步（✅ 已验证，2026-11-01）

§4K 拆出的独立 doc-sync 子片。`tests/api/system_config/` 目录已在 §4K 建好但留空，本片把 `test_system_config_api.py`（路径完全干净：sys/parents/file 均为 0，主路由 `/api/v1/system`）`git mv` 归位，并同步其文档活动指针。

**docref 实际规模纠偏**：§4K 记为「5 处」系低估，逐目录 grep（双目录 `docs/`+`documents/`）实测为 **5 个文档文件的 9 处**引用，全部是「回归验证位置/兼容验证入口」活动指针（非 CHANGELOG/台账历史叙述），须随搬迁更新为新路径：

| 文档 | 处数 | 语义 |
| --- | --- | --- |
| `docs/llm-providers.md` | 1 | 系统配置链路验证闭环 |
| `docs/analysis-context-pack.md` | 1 | 兼容性证据回归核验点 |
| `docs/LLM_CONFIG_GUIDE_EN.md` | 2 | 依赖约束回归覆盖 / 恢复路径证据 |
| `docs/LLM_CONFIG_GUIDE.md` | 4 | 兼容验证入口 / 回归覆盖 / 接口校验 / 恢复证据 |
| `docs/full-guide.md` | 1 | Issue #1306/#1391 兼容验证沿用 |

统一以 `replace_all` 把 `tests/test_system_config_api.py` → `tests/api/system_config/test_system_config_api.py`；因 `_api.py` 与 `_service.py` 为互斥的完整后缀，替换不会误伤同目录的 `test_system_config_service.py` 引用。验证：搬迁件定向跑 2 failed / 33 passed（generation_backend 两例），经全量门禁复跑为 **5713 passed / 4 deselected / 0 failed**（239.36s）、`--collect-only` **5717**、零回归——判定同 §4K 的 seam/导入顺序子集假红（路径干净、零代码改动、全量上下文通过），非搬迁引入。残留旧路径核对（双目录 + scripts/.github）为空。至此**累计 157 件**、顶层 `test_*.py` 降至 137。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

`git mv tests/api/system_config/test_system_config_api.py tests/`，5 个文档 9 处路径以 `replace_all` 反向还原为 `tests/test_system_config_api.py`；`tests/api/system_config/` 空目录随手回收。

## 4M. 分类搬迁批 4：新建 tests/bot/ ← bot 命令/调度/平台组 5 件（✅ 已验证，2026-11-01）

重新盘存顶层 137 件：**78 件路径干净**（sys/parents/file 均 0）+ 59 件带 hazard（T3/专项）。对 78 件逐件取 `src.层.域`（含 api/bot/data_provider）导入画像后，取主题最连贯、双目录 docref 均 clean 的 **bot 组 5 件**：逐件确认测试主体均为 `bot.commands.*`/`bot.dispatcher`/`bot.models`/`bot.platforms.*`（src 侧仅 `src.domain.notification.bot_message.BotMessage` DTO 与 `src.config.Config` 等支撑类型，非测试主体）：

| 新路径 | 文件 | 主体依据 |
| --- | --- | --- |
| `bot/`（新建） | test_ask_command | `bot.commands.ask.AskCommand` |
| `bot/`（新建） | test_bot_dispatcher_async | `bot.dispatcher.CommandDispatcher` + `bot.commands.base`/`bot.models` |
| `bot/`（新建） | test_bot_market_command | `bot.commands.market.MarketCommand` |
| `bot/`（新建） | test_bot_status_command | `bot.commands.status.StatusCommand` |
| `bot/`（新建） | test_feishu_stream_ordering | `bot.platforms.feishu_stream.FeishuStreamHandler` |

对应 AGENTS.md §3 “`bot/` 机器人接入”边界。新建 `tests/bot/`（沿用既有不建 `__init__.py`、靠 basename 唯一约定）。5 件均零代码改动。**portfolio 组 4 件均暂缓 T3**：`test_portfolio_pr2`（api.app+auth+bootstrap 重集成）、`test_portfolio_service`（persistence×2+providers+bootstrap+storage 多边界）、两个 `_port`（application.portfolio ↔ infrastructure.providers port seam）——按“跨 app+infra 层件归 T3”纪律不入本批。验证：5 件定向 **47 passed**（bot 测试自包含，无子集假红）、全量离线门禁 **5713 passed / 4 deselected / 0 failed**（232.09s）、`--collect-only` **5717**、零回归；双目录+scripts/.github 无残留旧路径。至此**累计 162 件**、顶层 `test_*.py` 降至 132。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

5 件逐件 `git mv` 回 `tests/`；新建的空目录 `tests/bot/` 随手回收（零代码改动）。

## 4N. 分类搬迁批 5：runtime(2)+domain/analysis(2)+backtest(1)+bot(1) 六件单边界归位（✅ 已验证，2026-11-01）

重新盘存顶层 132 件：**73 件路径干净** + 59 件带 hazard。逐件读实际导入行确认主体后，取主体单边界、目标目录均既有、双目录 docref 均 clean 的 **6 件**纯 `git mv`（零代码改动）：

| 目标目录 | 文件 | 主体依据 |
| --- | --- | --- |
| `application/runtime/` | test_runtime_scheduler_service | SOLE `src.application.runtime.runtime_scheduler` |
| `application/runtime/` | test_belong_boards_run_flow | `src.application.runtime.run_diagnostics`（data_provider 仅支撑） |
| `domain/analysis/` | test_stock_analyzer_bias | `src.domain.analysis.stock_analyzer`（decision.scale 仅打分 helper） |
| `domain/analysis/` | test_stock_analyzer_rsi | `StockTrendAnalyzer` 主体（domain.alert 仅 rsi helper） |
| `domain/backtest/` | test_backtest_domain_records | `src.domain.backtest` records（persistence models 支撑） |
| `bot/`（补批 4） | test_discord_platform | `bot.platforms.discord.DiscordPlatform`（src 侧仅 ChatType DTO） |

**重要纠偏**：`test_discord_platform` 上轮画像因 `src.domain.notification`(1) vs `bot`(1) 计数打平而被归入 domain 侧，但读实际导入行后确认主体为 `DiscordPlatform`（bot 平台）、src 侧仅 `ChatType` DTO，与批 4 bot 组同形→应属 `tests/bot/`。**计数启发式会误杀“DTO 支撑型”件，必须读实际导入行复核**。本批暂缓 T3/独立片：`test_run_flow`（api+history+indexing+runtime 多边界）、`test_llm_channel_config`/`test_system_config_service`（多重边界 + full-guide/market-support/settings-help 活动指针）、`test_signal_scanner_service`（混合 + scanner.md:127）、`test_analysis_metadata`（SOLE src.utils，需单独议新建 utils 目录）、`test_market_strategy`/`test_analysis_context_pack_schema`（跨 domain 子边界）。验证：6 件定向 **51 passed**（日志中 `reraise`/market-cards 预热为噪声，非失败）、全量离线门禁 **5713 passed / 4 deselected / 0 failed**（253.52s）、`--collect-only` **5717**、零回归；双目录+scripts/.github 无残留旧路径。至此**累计 168 件**、顶层 `test_*.py` 降至 126。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

6 件逐件 `git mv` 回 `tests/`（四个目标目录均既有，无需回收空目录；零代码改动）。

## 4O. 分类搬迁批 6：domain/market(2)+application/agent(2) 四件（含一次 docref 升格拦截）（✅ 已验证，2026-11-01）

重新盘存顶层 126 件：**67 件路径干净**（已接近 clean 单边界穷尽，余多为真·双边界 T3 候选）。本批应用 §4N 固化的 **DTO 支撑型判据**：`test_daily_market_context_guardrail` 虽以 `src.application.analysis` 为主边，但断言对象是 `src.domain.market.daily_context_guardrail.apply_daily_market_context_guardrail`，`analyzer.AnalysisResult` 仅 DTO→主体实为 **domain/market**（纠正计数误归）。取确定单主体、目标目录均既有、双目录 docref 均 clean 的 **4 件**纯 `git mv`（零代码改动）：

| 目标目录 | 文件 | 主体依据 |
| --- | --- | --- |
| `domain/market/` | test_daily_market_context_guardrail | 断言 `domain.market.apply_daily_market_context_guardrail`（app.analysis 仅 DTO） |
| `domain/market/` | test_market_strategy | 断言 `domain.market.strategy.get_market_strategy_blueprint`（MarketAnalyzer 仅上下文） |
| `application/agent/` | test_data_tools_daily_history_cache | `agent.tools.data_tools._handle_get_daily_history`（history 仅协作） |
| `application/agent/` | test_strategy_scheduler | `agent.skills.scheduler.AgentSkillScheduler` |

**流程发现（重要）**：`test_daily_market_context_guardrail` 是经 DTO 判据临时升格的件，**pre-check 阶段未覆盖其 docref**，但搬迁后收尾双目录扫描拦截到 `docs/analysis-context-pack.md:113` 将其列为「验收路径」活动指针→已同步为 domain/market 新路径。教训：**任何升格/改判的件必须补走 pre-docref，且搬迁后双目录扫描是权威拦截层，不可省。**本批暂缓：analyzer_news_prompt/decision_stability（app+domain 两函数均断言、真混合）、report_language_prompt_directives（agent↔reporting 双 subject）、live_news/security_baseline（多重边界 + live-news.md/security_performance_baseline.md 活动指针→独立 doc-sync 片）、chip_distribution_manager（SOLE 但 realtime/common 能力归属待定）。验证：4 件定向 **37 passed**、全量离线门禁 **5713 passed / 4 deselected / 0 failed**（245.19s）、`--collect-only` **5717**、零回归；双目录+scripts/.github 无残留旧路径（guardrail 已修）。至此**累计 172 件**、顶层 `test_*.py` 降至 122。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

4 件逐件 `git mv` 回 `tests/`；`docs/analysis-context-pack.md:113` 一行路径以 `replace` 还原为 `tests/test_daily_market_context_guardrail.py`；`scripts/_tmp_inv_b6.py` 已删（零代码改动）。

## 4P. doc-sync 片：signal_scanner_service→application/decision + 2 件经完整读断言升判 T3（✅ 已验证，2026-11-01）

批 6 交付曾把 live_news/security_baseline/signal_scanner_service 三件标为「边界清晰但带活动指针」的候选 doc-sync 片。本片按待办「先定边界再同步指针」的要求，对三件**逐一读完整断言分布**（把 §4O 固化的收尾权威拦截前移到 pre-check），结果**纠正了批 6 的乐观判断**：

| 件 | 断言主体分布（实测） | 判定 |
| --- | --- | --- |
| test_live_news（797 行） | `WallstreetcnLiveNewsFetcher`(data_provider) 与 `IntelligenceService`(app/intelligence) 两组均**成规模直接断言**；且第 43-44 行**导入期** `configure_news_source()`/`configure_intelligence_repository()` 触发 bootstrap 端口装配副作用（seam） | 双 SUT + 导入期 seam → **T3/integration**，不搬 |
| test_security_baseline（276 行） | cookie 标志（api `_cookie_params`/middleware）与 `src.auth`（session secret/verify/常量时间）**均衡**，是刻意跨层安全不变量契约 | 跨层无单一桶 → **T3/integration-security**，不搬 |
| test_signal_scanner_service（337 行） | `svc.*`(application/decision，约 10 例：`normalize_request`/`resolve_stock_pool`/`run_signal_scan`/`release_run`) **主导** + `ind.detect_signals`(domain/analysis 6 例) 为其调用的指标原语；文件名即 service | 主边界 **application/decision 就近**，可搬 |

仅第三件满足单一主边界，取纯 `git mv` 归新建 `tests/application/decision/`（顶层另有 decision_signal_service/extractor、alert_worker 等多件 `src.application.decision` 测试，后续可继续聚拢该桶）；路径完全干净（sys/parents/file 全 0、无 open/Path/os.path），零代码改动。同步活动指针 `documents/product/技术信号扫描/scanner.md:127`（离线单测回归位置）；`documents/framework/backend_architecture_adr.md:571` 的同串引用系**历史 ADR 迁移叙述**（已完成 2026-10-19，历史留真）不改。

**流程结论（重要）**：三件里 2 件经完整读断言从「doc-sync 候选」升判为 T3，印证批 6「clean 单边界红利已近尾声、继续凑批易违背 §1.2」的自我预警——**剩余顶层件的归类必须以「读断言分布」为 pre-check 权威步，不能沿用批 6 前基于计数/初筛的边界判断**。验证：搬迁件定向 **20 passed**（与 scanner.md「20 例」一致）、全量离线门禁 **5713 passed / 4 deselected / 0 failed**（245.87s）、`--collect-only` **5717**、零回归；双目录活动指针残留清零（ADR 历史正确排除）。至此**累计 173 件**、顶层 `test_*.py` 降至 121。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

`git mv tests/application/decision/test_signal_scanner_service.py tests/` 并删除空目录 `tests/application/decision/`；`scanner.md:127` 一行还原为 `tests/test_signal_scanner_service.py`；live_news/security_baseline 未动。

## 4Q. 分类搬迁批 7：providers/common(1)+application/reporting(1)+config/settings(1) 三件（含一次 git 索引态异常上报）（✅ 已验证，2026-11-01）

重新盘存顶层 121 件：**62 件路径干净 + 59 件带 hazard**。严格以「读完整断言分布」作 pre-check（不沿用计数/初筛的乐观标注）：62 件干净里**仅 1 件 SOLE**（test_chip_distribution_manager），其余均 ≥ 2-bound，且绝大多数已在批 5/6 被判为真混合（analyzer_news_prompt、decision_stability、run_flow、portfolio 组、backtest service/repo、search 组、live_news/security_baseline 等）。本批从 2-bound 中挑出「第二边界实为 DTO/helper、主边界就近」的确定件：

| 目标目录 | 文件 | 主体依据（断言分布） |
| --- | --- | --- |
| `infrastructure/providers/common/` | test_chip_distribution_manager | SOLE `data_provider`；断言 `DataFetcherManager.get_chip_distribution` 跨 fetcher 选源降级（与同目录 `test_data_fetcher_manager_*`/`*_fallback`/`*_manager_routing` 同族） |
| `application/reporting/` | test_report_renderer | 断言均为 `reporting.report_renderer.render`；`application.analysis.AnalysisResult` 仅在构造/类型标注出现→纯 DTO（DTO 支撑型判据） |
| `config/settings/` | test_config_validate_structured | 主体 `Config.validate_structured`/`ConfigIssue`；`domain.generation.backend_identity` 仅作错误消息里的样本字符串→helper；与同目录 config_manager/env_compat 同族 |

三件均路径完全干净（sys/parents/file 全 0、无 `from tests.`/包内导入）、双目录 docref 均 clean、零代码改动。**暂缓**：test_report_language_fallbacks_ko（domain.shared 占位文本 + application.market 标题两组均断言、ko sweep 双 subject）、test_autocomplete_pr0（`class TestAnalyzeRequest`(api.schemas) + `class TestTaskInfo`(runtime.task_queue) 两个对等测试类→双 SUT）→归 T3。

**⚠️ git 索引态异常（非本任务发起、非破坏性）**：本片收尾核查发现，此前已暂存的 `R` 重命名集体退化为「旧路径 ` D` + 新目录 `??`」。排查 HEAD 发现：① **HEAD 仍跟踪全部旧测试路径**、无新路径→测试搬迁从未被提交（仅存在于工作树）；② HEAD 相对基线 fe7410bb 领先 **44 个提交**，均为 `gaocangxiong` 于 2026-11-01 23:40–23:41 一分钟内提交的**纯文档提交**（Update CHANGELOG.md/scanner.md/PLAN.md、Create PROGRESS.md）→系用户/其环境 checkpoint 在提交文档并伴随一次 index reset，**非本 agent 发起的 commit**（本会话全程未跑 commit/add/reset/stash，批 7 三个 git mv 仍为正确已暂存 `R`）。物理重构完整无损（294→118 = 176 件纯搬迁、无删除）；未暂存的 D+?? 在提交时 `git add -A` + rename 检测（-M）会自动重新配对，零数据风险。因此本台账的累计口径改用**稳健的物理口径**（顶层 `test_*.py` 294 递减），不再以 git 已暂存 R 计数为准。待用户自行确认 checkpoint 行为后再统一提交。

验证：3 件定向 **102 passed**、全量离线门禁 **5713 passed / 4 deselected / 0 failed**（237.61s）、`--collect-only` **5717**、零回归；双目录+scripts/.github 无活动残留。至此**累计 176 件**（物理口径）、顶层降至 **118**。未改 conftest/setup.cfg/stub，未提交。

### 回滚方式（本片）

3 件逐件 `git mv` 回 `tests/`（目标目录均为既有且非空，无需回收）；本批零代码改动、零 docref 变更。

## 4R T3-a 跨切首片：新建 `tests/utils/` + 无 hazard 就近/入口件 8 件（2026-11-02）

T3 设计经用户确认（单一新增 `integration/` 桶 + 其余复用既有桶 + hazard 先修后归 + 仅 autocomplete_pr0 拆分）。T3-a 仅取**路径干净、纯 `git mv` 零代码改动**的就近/入口/安全件：

| 文件 | 边界签名（读完整断言定 SUT） | 目标 | 规则 |
|---|---|---|---|
| `test_security_baseline` | api cookie 标志 + src.auth session/secret 跨层安全不变量 | `infrastructure/security/`（已含 auth.py、cwe_xff） | R4 security |
| `test_auth_status_setup_state` | `endpoints.auth.auth_status/update_settings` 主导，src.auth 为状态源 | `api/auth/` | R1 |
| `test_main_portfolio` | `import main` + `main.parse_arguments/resolve_portfolio_stock_codes` | `bootstrap/entrypoints/` | R1 入口 |
| `test_main_schedule_mode` | `import main` + schedule 模式配置/通知编排 | `bootstrap/entrypoints/` | R1 入口 |
| `test_news_intel` | `DatabaseManager.save_news_intel` 持久化去重，search_service 为 DTO | `infrastructure/persistence/` | R1 |
| `test_get_latest_data` | `DatabaseManager.get_latest_data`，models 为 DTO | `infrastructure/persistence/` | R1 |
| `test_search_tools_persistence` | `agent.tools.search_tools` 持久化，intelligence.search_service 为 DTO | `application/agent/` | R1 |
| `test_analysis_metadata` | SOLE `src.utils.analysis_metadata`（utils 族后续聚拢） | 🆕 `tests/utils/` | SOLE |

- `notification_diagnostics`（application.alert↔notification 跨子域、无 tests/application/alert 目录）**延至 T3-b integration/notification**，不在本片强归。
- 活动指针同步：`documents/framework/security_performance_baseline.md` ×3（security_baseline 守卫用例路径）、`docs/analysis-context-pack.md:113`（main_schedule_mode 验收路径）→ 均为可执行回归路径，已随迁更新；同 line 内其余待搬件路径随各自片同步。
- 验证：定向 133 passed；**全量离线门禁 `pytest tests -m "not network"` = 5713 passed / 4 deselected / 0 failed**（231.57s），collect 不变 → 零回归；顶层 118 → 110，物理累计 184 件。

---

## 4S T3-b 跨切/就近片：新建 `tests/integration/` 稀疏桶（11） + 主 SUT 就近（39）（共 50 件，2026-11-02）

**策略修订**（较初始设计更收敛）：经回顾批 1「seam 件可就近」先例 + AGENTS.md §7「不新增平行结构」，确立：**仅真正跨 ≥3 特性域的端到端/seam-heavy 件进稀疏 `integration/`，其余按主 SUT 模块就近归既有桶**（避免 `integration/` 退化为与特性树平行的第二套目录）。逐件读完整断言分布定主 SUT。

**integration/（11 件，跨 ≥3 域端到端/seam-heavy）**：
- `integration/analysis`←analysis_integration（api+runtime+auth TestClient 端到端触发）、analysis_api_contract（api+analysis+history+indexing+runtime 合约）
- `integration/intelligence`←live_news（fetcher+service+api+persistence seam）、live_calendar（dp news+config+persistence+service seam）、intelligence_analysis_integration（config+analysis+market+persistence seam）
- `integration/decision`←skill_opinion_samples（agent+analysis+decision+persistence seam）、decision_signal_extractor（analysis+decision+persistence ×3 bootstrap seam）
- `integration/portfolio`←portfolio_pr2（portfolio+auth+api+decision ×4 bootstrap seam）、portfolio_service（service+persistence+providers seam）
- `integration/generation`←llm_channel_config（config+domain.generation+infra.generation+app.runtime 三域 channel 配置）
- `integration/alert`←alert_worker（notification+alert+decision+config ×4 bootstrap seam）

**主 SUT 就近（39 件，含 2 个新建二级目录）**：application/agent←agent_tool_surface/skill_load_warning/agent_litellm_route_resolution；infrastructure/agent_runtime←codex_tool_process/codex_app_server_gate_a；infrastructure/search←search_searxng/search_tavily_provider；application/intelligence←search_news_freshness/search_service_concurrency/intelligence_service；application/analysis←analysis_context_pack_overview/analyzer_news_prompt/decision_stability/pipeline_daily_market_context/pipeline_related_boards/chip_structure_fallback；application/reporting←report_language_prompt_directives/analysis_context_pack_prompt；application/market←market_review_runtime/report_language_fallbacks_ko；application/runtime←run_flow/system_config_service/generation_backend_status_service；application/history←analysis_history；🆕 application/watchlist←watchlist_use_case；application/notification←notification_diagnostics；application/decision←decision_signal_outcome_service/skill_opinion_outcomes；🆕 application/backtest←backtest_service；domain/analysis←analysis_context_pack_schema；infrastructure/persistence←backtest_repo_record_mapping/decision_signal_repo；infrastructure/generation←generation_backend/local_cli_backend；infrastructure/providers/common←jp_kr_market_support/tw_market_support/realtime_quote_fallback_logging；application/portfolio←portfolio_risk_belong_boards_port/portfolio_service_realtime_port。

- 活动指针同步（均为可执行回归路径）：analysis_api_contract×5、live_news×2、llm_channel_config×多处、analyzer_news_prompt/decision_stability/pipeline_daily_market_context/market_review_runtime/system_config_service/analysis_history——以 `find docs documents -name '*.md' | xargs sed` 递归双目录同步，残留旧路径清零。
- 验证：integration 子片定向 389 passed；39 就近件纯 git mv；**全量离线门禁 = 5713 passed / 4 deselected / 0 failed**（两次子片各 229/231s），collect 不变 → 零回归；顶层 110 → 60（余均 hazard + autocomplete_pr0），物理累计 234。

---

## 4T T3-c 拆分片：`test_autocomplete_pr0.py` 按真实边界三段拆分（2026-11-02）

顶层唯一剩余的「干净但双 SUT」件。全文读完发现实为 4 个类、**3 个真实边界**，按边界三段拆分（非原计划两段）：
- `api/contract/test_autocomplete_analyze_request.py`←TestAnalyzeRequest（5 例，仅 `api.v1.schemas.analysis.AnalyzeRequest` 请求契约）
- `application/runtime/test_task_queue_autocomplete_fields.py`←TestTaskInfo(3)+TestTaskQueue(4)（均针对 `task_queue` 的 TaskInfo/AnalysisTaskQueue，共 7 例）
- `integration/analysis/test_autocomplete_end_to_end.py`←TestIntegration(2 例，AnalyzeRequest→get_task_queue 跨 api+runtime 端到端）

原件 `git rm`；14 例总数与拆分前三文件之和一致（5+7+2），collect 恒 5717。原件无 docref 活动指针（已核）。验证：拆分三件定向 **14 passed**；**全量离线门禁 = 5713 passed / 4 deselected / 0 failed**（238.86s），零回归；顶层 60 → 59（均为 hazard），物理累计 235。

---

## 4U T3-e 结构守卫片：`bound=0` 仓库结构/契约守卫件路径修正 + 归位 `tooling/*` 与 `api/contract`（8 件，2026-11-02）

这批不测运行时行为，而是校验仓库文件结构 / 工作流 env / 脚本契约 / schema 契约，逐件先修深度敏感路径（`Path(__file__).parent[s]` → `get_repo_root()`；`sys.path.insert(... 'scripts')` 保留但对齐根辅助），再按守卫对象就近归位（先做 T3-e、后做 T3-d，因守卫件归属最无歧义）：

| 件 | 守卫对象（读全文确认） | 路径修正 | 目标 |
|---|---|---|---|
| test_check_architecture | importlib 加载 `scripts/check_architecture.py` + 扫真实仓库 | `REPO_ROOT=parent.parent`→`get_repo_root()`（保留 Path，别处仍用） | tooling/scripts |
| test_generate_index_from_csv | `scripts/generate_index_from_csv.py` 单元 | `sys.path.insert(Path(__file__).parent.parent/'scripts')`→`get_repo_root()/'scripts'`，删 Path 导入 | tooling/scripts |
| test_refresh_stock_index | `scripts/refresh_stock_index` importlib | `ROOT=parent.parent`→`get_repo_root()`，删 Path 导入 | tooling/scripts |
| test_fetch_tushare_stock_list | `scripts/fetch_tushare_stock_list` importlib | 同上 | tooling/scripts |
| test_daily_analysis_workflow_llm_env | `.github/workflows/00-daily-analysis.yml` + 模板/env 静态校验 | `ROOT_DIR=parent.parent`→`get_repo_root()`，删 Path 导入 | tooling/workflows |
| test_daily_analysis_workflow_notification_env | 同上 yml + `docs/notifications.md` 表 + scripts/src 常量 | `ROOT_DIR`→`get_repo_root()`，删 Path 导入 | tooling/workflows |
| test_data_provider_adr_structure | `data_provider/` 目录与 ADR-001 结构对齐 + 语法编译 | `ROOT=parents[1]`→`get_repo_root()`，删 Path 导入 | tooling/docs |
| test_kline_schema | `api/v1/schemas/kline.py` Pydantic 字段契约（importlib 隔离加载） | `_SCHEMA_PATH=parents[1]`→`get_repo_root()`，删 Path 导入 | api/contract |

> 注：`test_static_assets_consistency` 经读全文判定为 **scripts 检查器 + 大量 `api.app` 资源服务/股票索引路由** 的混合件（非纯结构守卫），不纳入本批，归 T3-d 处理。

docref：9 处匹配全落在 `documents/framework/**`（ADR/refactoring/迁移台账）与 CHANGELOG 等**历史留真**治理文档，无 `docs/*.md` 产品文档或 `.github` 工作流的**活动 pytest 指针**，故本批无需活动指针同步。验证：8 件全量离线门禁 **5713 passed / 4 deselected / 0 failed**（231.96s），零回归；顶层 59 → 51（均为 hazard），物理累计 243。（定向曾出现 `dotenv` stub 泄漏假红：`fetch_tushare_stock_list` 模块级桩只注入 `load_dotenv`，当它在同进程先于 `notification_env`（需 `dotenv_values`）被收集时污染 `sys.modules`；属既有跨文件导入顺序耦合，非搬迁引入，全量收集顺序下门禁绿。）

---

## 4V T3-d hazard 多边界件：51 件逐簇修路径 + 读断言定主 SUT 归位（顶层 51 → 0，物理累计 294，2026-11-02）

承接 T3-e（先做归属最无歧义的 bound=0 守卫件），T3-d 处理剩余 51 个 hazard 件。按主 SUT 簇分片推进，每片先修路径 hazard 再 `git mv` 归位，**每片均跑全量离线门禁对账零回归**。路径 hazard 三分法：① `sys.path.insert(0, abspath(dirname(__file__),'..'))` = 仓库根自注入（conftest 已提供根路径），删行即可，若 `os`/`sys` 再无他用则删对应 import；② `Path(__file__).resolve().parent[s]` 求根 = 深度敏感，改 `get_repo_root()`（注入 `scripts`/`data` 子路径的改为 `get_repo_root()/'scripts'` 保留访问）；③ 引用**被测模块**的 `module.__file__`（读源码断言）= 深度安全，纯搬迁不改码。

| 簇 | 件数 | 主 SUT 判据 | 路径修法 | 目标桶 |
|---|---|---|---|---|
| api endpoint 接线 | 8 | `api/v1/endpoints/*` 分层接线契约 | 4 件 `parents[1]`/`.parent.parent`→`get_repo_root()`（kline/limit_pool/sector/decision_signal），4 件仅 `module.__file__` 安全纯搬 | api/{kline,limit_pool,stocks,analysis,sector,backtest,agent,decision_signals} |
| agent 簇 | 9 | `src.application.agent.*` + infra.search + api.agent | 删冗余根自注入/转 `get_repo_root()`/`strategies_dir`→根辅助，多余 `os`/`sys`/`Path` 删导入；anspire `os.path` 求根→`str(get_repo_root())` | application/agent(7)+infrastructure/search(1)+api/agent(1) |
| pipeline 簇 | 7 | `src.application.analysis.pipeline.StockAnalysisPipeline`（既有 `test_pipeline_*` 家族先例） | 6 件删根自注入（realtime 另修 `data/test_issue234.db`→`get_repo_root()/'data'`）；persistence_port 仅 `module.__file__` 安全 | application/analysis |
| signal_attribution | 4 | schema 件=`report_schema`+`domain.shared.report_language`（单元）；e2e/real_paths/supplement 跨 analyzer+notification+history+utils（集成） | schema 件无 hazard 纯搬；其余删 `..'/src'`/自目录/root 注入块（os/sys 仅此处用） | application/analysis(1)+integration/analysis(3) |
| notification/misc S 件 | 8 | formatters/report_fixtures→`domain.shared.text_chunking`；llm_usage→`infra.generation.usage`；task_service→`application.runtime`；chat_context→`application.agent`；tw_report/notification→`application.notification`；data_fetcher→`DataFetcherManager`（`test_data_fetcher_manager_*` 先例） | 各删根自注入（llm_usage 保留 os/Path，notification 保留 sys 因 `sys.modules` mock），report_fixtures `FIXTURE_DIR=Path(__file__).parent/'fixtures'`→`get_repo_root()/'tests'/'fixtures'` | domain/shared(2)+infra/generation/telemetry(1)+application/runtime(1)+application/agent(1)+application/notification(2)+infra/providers/common(1) |
| 混合/P/守卫尾部 | 15 | analyzer_domain_rules→`domain.analysis`(chip/prompt)+`domain.decision`；bot_use_case_wiring→bot 分层守卫；config_registry→`src.config.registry`；decision_signal_docs→docs 契约守卫；decision_signal_service→`application.decision`；image_vision→`application.analysis`+infra.generation；market_analyzer/market_review→`application.analysis`/`application.market`；run_diagnostics_p1/p2→`application.runtime.run_diagnostics`；schedule_times→`domain.shared`；schema_migration_guard→`infra.persistence.schema_compat`；static_assets_consistency→`scripts.check_static_assets`+api.app（混合判主 scripts 侧）；tushare→`data_provider.tushare_fetcher`；webui_frontend→`src.webui_frontend` 入口件 | parents[1]/parent.parent 求根→`get_repo_root()`（config_registry 8 处、bot 4 处、static `SCRIPT_DIR`→`get_repo_root()/'scripts'`、tushare `_PROJECT_ROOT`→`str(get_repo_root())` 供 `load_dotenv`）；market_analyzer/market_review/schema_guard/webui 仅 `module.__file__`/`tmp_path`+monkeypatch 安全纯搬；p1/p2 删根自注入 | domain/analysis(1)+bot(1)+config/settings(1)+tooling/docs(1)+application/decision(1)+application/analysis(2)+application/market(1)+application/runtime(2)+domain/shared(1)+infra/persistence(1)+tooling/scripts(1)+infra/providers/common(1)+bootstrap/entrypoints(1) |

> 关键判定：`test_tushare_fetcher_get_stock_list` 的 `__main__` 用 `unittest.main()`（非 `pytest.main([__file__])`），直跑不自我递归，无死循环风险，正常搬迁；`test_static_assets_consistency` 从 T3-e 剔除后按主 SUT（`check_static_assets` 脚本模块为顶层导入依赖、api.app 侧复用同一一致性逻辑）归 `tooling/scripts`，`SCRIPT_DIR` 改走根辅助保留 `importlib.import_module('check_static_assets')` 可解析；`agent_frozen_context` 等双关注点件按 P5 整件归主边界桶不拆。

docref：本批在 `docs/`、`documents/` 全量核对 34 个搬迁件名，命中仅落在 `documents/framework/refactoring/ARCHITECTURE_MIGRATION_PROGRESS.md`、`src_migration_index.md`、`CHANGELOG.md` 的**历史留真**迁移记录（记录各切片当时实跑命令），无 `docs/*.md` 产品文档或 `.github` 工作流的**活动 pytest 指针**，故无需活动指针同步（agent 簇的 8 处活动指针已在 T3-d 子批2 单独 sed 同步、残留清零）。

验证：T3-d 全程 4 次全量离线门禁均 **5713 passed / 4 deselected / 0 failed**（pipeline+signal 合并片 228.34s、notif/misc 片 239.28s、尾部 15 件片 232.50s，另 pipeline 单独片 235.24s；EXIT=0），各簇定向亦全绿（71 / 46 / 270 / 437 passed），零回归。顶层 `test_*.py` 51 → **0**，物理累计 **294**（= T0 基线顶层 294 全部归位）。残留顶层仅 `conftest.py`（基础设施，留）、`litellm_stub.py`（待 T4 → `support/stubs`）、`longbridge_live_smoke.py`/`tw_institutional_live_smoke.py`（network 门控 smoke，留）。全程零提交、未动 git 索引（早期已暂存 rename 退化为 `D+??` 的索引态异常仍待用户处置）。

---

## 4W T4 公共依赖治理 + T5 收口：stub/smoke 归位、docs 活动指针同步、随机顺序如实登记（2026-11-02）

承接 T3 全部收官（顶层 `test_*.py`=0），本片交付 T4（公共依赖治理）与 T5（收口）。全程零提交、未动 git 索引（用户最后一次性提交）。

- **T4-A stub 归位**：`git mv tests/litellm_stub.py → tests/support/stubs/litellm_stub.py`。40 个消费件（38 `import ensure_litellm_stub` + 2 `import ensure_litellm_stub, remove_litellm_stub`）的 `from tests.litellm_stub import` 单形态 sed 重指为 `from tests.support.stubs.litellm_stub import`；残留旧模块路径 0。`tests/__init__.py` 使 `tests` 为常规包、根 conftest 注入仓库根 sys.path，深层子包**无需** `__init__.py` 即可解析（符合方案 §5.3「不批量新增 `__init__.py`」）。import 冒烟（ensure→`litellm.__hrs_test_stub__`→remove）+ py_compile 均绿。stub 内部只写 `sys.modules["litellm"]`、无自指模块路径，故其体内 `litellm_stub.` 变量名不受影响。
- **T4-B smoke 归位**：`git mv` 两个直跑在线脚本 → `tests/tooling/manual_smoke/`。二者无 `test_` 前缀、pytest 不收集、不靠 conftest；其 `_PROJECT_ROOT = os.path.dirname(__file__)/".."` 自举 sys.path **早于**任何 `tests.*` 导入（鸡生蛋），故**不能**用 `get_repo_root()`；改深度为 `"..","..",".."`（manual_smoke→tooling→tests→根），运行时校验解析到仓库根（`main.py`/`pyproject.toml` 均命中）。docstring 内调用命令 + 2 处跨件 docstring 引用（`test_tw_institutional_network.py` / `test_longbridge_fetcher.py`）同步；CHANGELOG/PLAN/PROGRESS/reviews 历史留真不改。
- **T4-C `src.utils` 族聚拢（取证后为 no-op）**：`src/utils/` = {analysis_metadata, data_processing, market_review_region, pagination, sanitize, sniper_points, time}；仅 `test_analysis_metadata.py` 以单一 `src.utils` 模块为主 SUT（已在 `tests/utils/`）。`data_processing`/`sanitize` 仅作为**支撑 import** 出现在 pipeline/signal/decision/context-pack 域测试（主 SUT 非 utils），按「勿以支撑 import 误杀归类」原则留原桶；`market_review_region`/`pagination`/`sniper_points`/`time` 无 dotted-path 专属测试件；亦无 `from src.utils import` 非点号形态。结论：`tests/utils/` 已正确最小化，无件需搬。
- **T4-D 模块级副作用 / 全局补丁审计（保持原样 + 上报）**：全仓测试 **0 处模块级（无缩进）`sys.modules` 写入**，38 个写 `sys.modules` 的文件均在函数/fixture 内局部注入——§5.3 无机械收敛对象。`ensure_litellm_stub()` 的模块顶层调用是刻意导入期 seam（被测模块自身 top-level `import litellm`），不可降为 fixture。conftest 的 asyncio/AnyIO 唤醒补偿 + `_ThreadlessTestClient`（TestClient 替换）为方案 §5.2 明确的**独立证据驱动治理对象**：改其全局作用域须先复现原「沙箱首唤醒丢失」问题、按证据定范围，非文件搬迁范畴，本片**不盲改**，登记为后续独立片。
- **T5 硬路径收口**：`scripts/` + `.github/` 对 tests 旧路径 **0 硬编码**（CI 仅 `pytest -m "not network"` + `testpaths=tests` 递归；`setup.cfg` `python_files=test_*.py` 全递归、默认 import-mode + basename 唯一，无需改配置）。`docs/*.md` 发现 **7 个 stale 顶层活动指针**（`test_config_env_compat`/`test_config_registry`/`test_market_analyzer_generate_text`/`test_market_review`/`test_pipeline_market_phase_context`/`test_run_diagnostics_p1`/`test_run_diagnostics_p2`），逐一按当前实际子路径 sed 同步、残留 0。`documents/` 447 命中全部为 `CHANGELOG.md` 历史留真、`.claude/reviews/` 为审查历史——均不改。doc-anchor 守卫（`test_analysis_context_pack_docs`/`test_decision_signal_docs`/`test_config_registry`/`test_docker_entrypoint`）不断言 `tests/test_*.py` 串，编辑不破锚点。
- **T5 随机顺序（如实登记未验证）**：本环境 pytest 9.1.1 **未安装 pytest-randomly/order/xdist/parallel**，方案 §8.1「已有 pytest-randomly 环境下记录 seed」的前提不满足；安装属新增 dev 依赖且改变收集语义，需单独授权，不在搬迁范围。以确定性全量门禁 + 高 seam 簇定向作为替代证据。子集直跑时 `test_system_config_api` 出现 2 处失败为**导入顺序假红**（该件在全量权威门禁中随兄弟模块安装 stub 后绿），非搬迁回归。

> 复核纠正（2026-11-02）：此前 §4W 曾把 `tests/tooling/test_runtime/`（内含 `test_threadless_test_client.py`，测 conftest `_ThreadlessTestClient` shim）标为「`test_` 前缀目录命名瑕疵」，**判断有误**。核对方案 `TEST_SUITE_REFACTORING_PLAN.md` 目标目录树 line 230/294：`tooling/test_runtime/` 是方案**明确指定**的桶（注释「测试 client、兼容工具本身的回归」），与 line 231 指定的 `tooling/manual_smoke/` 平级；`test_` 前缀目录名是方案有意选择（与 `manual_smoke/` 同为 tooling 下固定子目录）。故按「单一真源/不改与方案冲突」原则**保留原样、不重命名**；用户请求的「test_runtime 目录清理」经此取证结论为无需清理（已在位、与方案一致、collect 正常、无任何代码/文档路径依赖它）。

验证：T4-A/B/C 合并后全量离线门禁 **5713 passed / 4 deselected / 0 failed**（256.23s，EXIT=0）；docs 同步后再跑最终权威全量门禁 **5713 passed / 4 deselected / 0 failed**（250.60s，EXIT=0）、`--collect-only` 恒 **5717**（=5713+4 network），零回归。定向 stub+doc-anchor 簇 498 passed / 1 skip（skip 为离线门控的 network 类件）。`flake8 --select=E9,F63,F7,F82` on 改动件 = 0。顶层残留仅 `conftest.py`（基础设施，留）、`__init__.py`（包标识，留）；`test_*.py` 恒 0、stub 与 smoke 已归位。HEAD 未变、零提交、未动 git 索引。

---

## 5. 当前状态与后续计划（2026-11-03 更新）

| 阶段 | 当前状态 | 当前证据 / 后续边界 |
| --- | --- | --- |
| T0 / T1 / T2 | 目录归位完成 | tests/ 顶层 test_*.py 为 0，不再有“剩余约 290 个顶层”待处理 |
| T3 | 本轮大文件内部拆分完成 | 16 → 113 测试模块，1520 方法内容保持，另归类 64 文件；见拆分映射 |
| T4 | 原生运行机制及本轮顺序验证通过 | 保留真实 asyncio / AnyIO / TestClient；消除本轮发现的两类测试状态污染，固定序与双随机种子全绿 |
| T5 | 本轮当前文档收口完成 | 活动路径及双语对应文档同步；历史执行记录保留，5725 是当前收集基线 |
| 尚存边界 | 不算本轮已通过项 | UI 原生 title 规则、全量前端 lint、Docker 授权、桌面端口问题及未验证平台，见架构总览 |

目录和文件的逐项对应及一二三级目录文件数见 [TEST_SUITE_SPLIT_MAPPING.md](./TEST_SUITE_SPLIT_MAPPING.md)。本节只反映当前状态，§1–4W、§7–9 的数字与结论保留为当时的执行记录。

### 每片收尾必做

1. 全量 `--collect-only` 与基线对账（记录任何 +/- 及原因）。
2. 受影响目录 `pytest` 绿；涉共享状态时增加随机顺序验证。
3. 本台账追加切片记录（含分支/HEAD、开工时工作树其他改动、旧→新用例对应、失败/跳过差异、未验证项、回滚）。
4. 触及用户/文档可见路径时同步 CHANGELOG 与 `docs/*`。

## 6. 风险与边界

- 目录层级以三级为上限；叶目录约 5–15 文件为浏览参考，非验收硬指标。
- 不以删用例/改标记（network/skip/xfail）让门禁变绿；删除或合并须说明保护行为与替代证据。
- `apps/hrs-web`、`apps/hrs-desktop` 的客户端原生测试留在各自目录，不并入根 `tests/`。
- 本台账数值更新必须注明基线日期；历史统计不覆盖当前状态。

## 7. 后续修正：生产页面扫描与系统配置 API 测试独立装配（2026-11-02）

针对迁移完成后的复核，本片处理两项：

- Web 的 `asyncRouteFactory.ts` 使用 Vite 负匹配排除页面树中的 `__tests__/`、`tests/` 及 `.test.tsx`/`.spec.tsx`，真实页面仍保持递归懒加载。新增回归直接验证 Vite 展开的页面/测试文件映射，避免 mock 掉扫描边界。
- `tests/api/system_config/test_system_config_api.py` 在每个用例准备时调用生产 `configure_generation_runtime()` 装配真实端口；用 patch 的 cleanup 保存并恢复其写入的全部六个模块级 seam，不依赖其他测试文件的导入副作用，也不把装配状态泄漏给后续用例。原先单跑的两个失败是真实的测试初始化缺口，本片补齐；生产端口缺失时的 fail-fast 行为保持。

定向验证：系统配置 API 独立运行 **35 passed**；页面扫描回归 **81 passed**；改动的两个前端文件 ESLint 通过；`npm run build`（含 TypeScript 检查）通过。新产物 `dist-web/assets/` 中 `.test-*`/`.spec-*` JS chunk **0 个**，扫描 JS 也未发现 `__tests__/`、`.test.tsx`、`.spec.tsx` 或 `__vitest_` 残留。

扩大路由回归发现 `appRouter.test.ts` 一条、`routeRegistry.test.ts` 两条既有失败：使用修复前的页面 glob 重新运行这两个文件，同样 **3 failed / 3 passed**。两处问题不在本片修复范围，记录为未清理的既有测试债务；不能将本片定向通过解读为所有 Web 测试通过。构建仍有既有循环 chunk/混合导入与大 chunk 警告。

已同步 `docs/desktop-package.md` 的前端输出目录和扫描边界说明，以及 `documents/CHANGELOG.md`。

完整后端门禁 `PATH="$PWD/.venv/bin:$PATH" ./scripts/ci_gate.sh all`：syntax、architecture、严格 flake8 和 deterministic 阶段通过；离线阶段在沙箱内得到 **12 failed / 5701 passed / 1 skipped / 4 deselected / 511 subtests passed（316.67s）**。失败集中在 `test_live_news.py`（11 条）与 `test_tencent_fetcher.py`（1 条）。代表性新闻失败在不收集本片修改测试的独立进程中同样复现，错误为外部来源域名 DNS 解析失败；腾讯短历史用例单独复跑通过。获准在沙箱外复跑上述两个文件后 **51 passed（9.81s）**。据此记录沙箱内完整门禁未绿、相关失败文件环境外复跑全绿；未将两次结果拼成一次“完整门禁全绿”，腾讯用例首次失败的具体原因未进一步确认。

## 8. 后续修正：路由测试契约与新闻离线 DNS 边界（2026-11-02）

基线：`main`，HEAD `7fc4f0fd`，开工工作树干净。本片只调整测试与记录，不修改生产 API、行情规则或 URL 安全校验，也不删除用例、不添加 skip/xfail/network 标记。

| 失败簇 | 原因与处理 | 保护行为 |
| --- | --- | --- |
| `appRouter.test.ts` 1 条 | 生产 `protectedLoader` 返回 redirect Response，旧测试仍要求抛异常；改为检查返回值 | 验证 HTTP 302、登录地址与原访问路径/查询参数的编码；保留已登录和禁用鉴权时的放行断言 |
| `routeRegistry.test.ts` 2 条 | 生产通过 `attachRouter()` 注入实例，旧测试仍 mock 静态 `appRouter` 导出；每个用例显式注入 router | 验证注册、重复注册跳过、关闭注册标志时跳过、卸载清空与标志复位 |
| `test_live_news.py` 11 条 | HTTP/抓取 mock 未覆盖来源 URL 校验中的真实 DNS，导致业务测试依赖外网；service/API 用例按用例作用域固定公网解析结果并通过 cleanup 恢复 | 继续执行真实 URL/IP 安全校验；新增私网解析与 DNS 失败两条回归，不直接 mock 掉 `_validate_url` |
| 腾讯短历史 1 条 | 尚未稳定复现，不进行猜测性修改 | 检查 799 条历史未达到 800 条上限的实际分支及 scoped HTTP patch；保留原断言与失败可见性，根因仍待确认 |

定向验证：Web 三个路由测试文件 **87 passed**；新闻测试独立运行 **41 passed**（新增 2 条）；既有 intelligence service 测试 **26 passed**（含 URL/DNS 安全路径）。改动的前端文件 ESLint 与 `npm run build`（含 TypeScript 检查）通过。构建仍有既有循环 chunk、混合导入和大 chunk 警告。

第一轮完整离线验证：`./.venv/bin/python -m pytest tests -m 'not network' -q -o addopts= --tb=short`，**5715 passed / 1 skipped / 4 deselected / 511 subtests passed（329.58s，退出码 0）**。相对 §7 增加的两个用例均为 DNS 安全回归；12 条原失败本轮均未出现。另逐阶段验证 `scripts/ci_gate.sh` 的 syntax、architecture、flake8、deterministic 均通过。

第二轮按原入口执行完整门禁：`PATH="$PWD/.venv/bin:$PATH" ./scripts/ci_gate.sh all`，所有阶段通过，离线部分 **5715 passed / 1 skipped / 4 deselected / 511 subtests passed（310.67s）**，最终输出 `backend-gate: all checks passed`，退出码 0；腾讯短历史用例再次在正常全量顺序中通过。两轮均在受限环境内完成，未依赖外部网络放行；完整门禁通过的结论不等于腾讯历史偶发失败的根因已关闭。

腾讯用例的边界：本轮按正常全量收集/执行顺序通过，不能由此认定其历史偶发失败已修复。未发现足以归因的共享状态泄漏，未更改腾讯生产实现，也未将重跑通过写为根因关闭。现有全量测试仍会输出部分后台行情预热的网络失败日志及既有依赖弃用/测试类收集警告，本片未改造后台生命周期。

未验证：真实外网数据源与全部 Web 测试。没有用户界面变更，故无页面截图；本片只更新中文迁移台账，项目没有对应的英文台账。回滚：撤回本片两个 Web 测试文件、新闻测试文件及本节/CHANGELOG 记录的改动即可；不涉及数据迁移。未执行 commit、tag 或 push。

## 9. Web 全量测试收敛与原生测试运行机制治理（2026-11-03）

基线 HEAD `a6397960`，开工工作树干净。范围为用户指定的两项：Web 全量测试修复、公共测试运行机制治理；前端全量 lint 清理明确留到最后。本片未 commit/tag/push。工作期间另出现后端源文件及 `setup.cfg` 的格式调整，非本片主动修改，予以保留；不得将整个工作区差异一概归入本片。

### 9.1 Web 失败的根因与修复

| 根因 | 最终处理与保留的保护行为 |
| --- | --- |
| 页面使用 Router，但单测未装配；rerender 又丢失上下文 | 通过局部 `renderWithRouter` 的 wrapper 装配真实 MemoryRouter，rerender 延续上下文；不全局 mock 路由 hook |
| 原分析首页已迁入 `reviewPage.tsx`，页面缓存默认未激活 | 原 `HomePage.test.tsx` 改为 `ReviewPage.test.tsx`，指向实际复盘工作台，并装配真实 KeepAlive；保留原分析、报告、任务流、自选、竞态覆盖，重置每例 mock 响应 |
| 认证/agent store、设置模块的测试 mock 仍针对旧导出或 barrel 路径 | 对齐 `useAuthStore`、`getState().setCurrentRoute` 和实际叶模块入口，保持页面编排与独立子组件的各自覆盖 |
| Node 环境没有 Element；主题 CSS 已抽入 palette；首屏仍读旧主题键 | DOM shim 检查 Element 存在；主题 token 守卫读取实际 palette；首屏读取 `hrs-pref-theme` 对象并保留旧键迁移窗口，执行真实内联脚本覆盖 light/dark/system、非法/不可用存储 |
| 控件标签与搜索受控状态缺口 | Select 透传/生成 id 并关联 label，通知输入增加可访问名称；股票搜索支持上下文名称及外部清空。提示方式迁移已按用户要求撤回，详见 §9.4 |
| 持仓账户竞态与测试宿主缺失 | `usePortfolioSignals` 真正检查快照账户匹配，匹配前清空旧信号/暂停查询。测试装配真实 Toast 并清理队列，进入持仓表格后断言明细，保留延迟响应反例；额外的汇率状态展示已按 §9.5 撤回 |
| 旧交互、文案与时间假设 | Tab 通过 tab 角色交互；路由边界使用当前可见导航；时间线续期样本落在查询窗口内；等待调度状态异步加载完成后再操作，不延长全局超时掩盖失败 |
| jsdom 无 WebGL | UniverseBackground 单测在引擎边界注入明确的构造错误，保留真实外壳、错误报告和卸载验证；不宣称验证了真实 Three.js/WebGL 渲染 |

`web-gate` 新增 `npm test`（在原 lint/build 前）；未取消或放松既有 lint 检查。AGENTS 的 CI 表与中英贡献文档同步。仍须注意：测试通过不代表当前含既有 lint 债务的完整 Web CI 已绿。

### 9.2 原生框架机制治理

移除根 `tests/conftest.py` 对 asyncio 唤醒/执行器关闭、AnyIO worker/from_thread、FastAPI/Starlette TestClient 的全部模块级替换；保留现有生产端口装配，不新增环境开关或平行 client。

旧 `test_threadless_test_client.py` 改为 `test_framework_runtime.py`：5 条原行为覆盖改为原生契约，再新增 5 条（含取消参数化两例），共 **10 条**。覆盖 Cookie 连续请求、上下文内外 lifespan、异常传播/500、ContextVar、原生执行器收尾、CapacityLimiter 串行约束、worker→event-loop 往返、`abandon_on_cancel` 的等待与放弃语义；显式检查 TestClient、AnyIO、asyncio 仍来自框架模块。临时线程通过释放事件和完成信号收尾。

### 9.3 验证、边界与交接

| 验证 | 结果 |
| --- | --- |
| Web 全量 `npm test`（§9.4 撤回前） | **118 files / 1305 passed / 0 failed（82.26s）**；此为当时结果，撤回 Tooltip 迁移后不再代表当前全绿，详见 §9.4 |
| 完整后端 `PATH="$PWD/.venv/bin:$PATH" ./scripts/ci_gate.sh all` | 所有阶段通过；**5720 passed / 1 skipped / 4 deselected / 511 subtests passed（356.12s）** |
| 原生运行机制定向 | **10 passed**；相对上一片后端基线新增 5 条 |
| Web 生产构建 | TypeScript 与 Vite 均通过；仍有既有循环/混合导入、大 chunk 警告 |
| AI 资产治理、改动 Python 严格 flake8、差异空白检查 | 通过 |
| 可视证据（历史） | 隔离浏览器、模拟 API 的临时截图 `/tmp/hermesx-portfolio-stale.png` 曾覆盖额外汇率状态展示；该展示已按 §9.5 撤回，截图不再代表当前页面，不得用于当前 PR 验收；未入库 |

未验证或明确延期：前端全量 lint 清理、真实外网/第三方服务、Three.js/WebGL 实际渲染、Docker 与 Electron 安装包及远端 Actions。本次并未关闭腾讯历史偶发失败的根因调查。Web 测试仍有 jsdom Canvas/scrollTo 提示，后端仍有依赖弃用与收集警告；不能把这些日志当作已消除。

中英贡献文档已同步；本台账、测试方案、`docs/decision-signals.md` 无对应英文专题，未新增平行译本。对外 API 字段及数据库 schema 未变。回滚应以本片路径/改动为单位恢复测试、运行机制、少量 Web 修复及 CI/文档；不得整仓 reset，以免覆盖并行的其他工作；回滚原生测试机制时须同时恢复旧回归文件，不能只恢复 client 替换。

### 9.4 范围纠正：撤回未经要求的 Tooltip 迁移（2026-11-03）

用户明确要求本次不引入 Tooltip。已完整撤回 `StockSearchList.tsx`、`BeyondShell.tsx`、`boardColumns.tsx`、`WatchlistStockColumn.tsx` 的 Tooltip import/包裹，恢复原有 DOM 与 title；同批恢复 `LiveCalendarListView.tsx` 的原生 title。这五个文件与本片 HEAD 一致，不再属于本次改动。

旧 `ui_governance.test.ts` 要求上述页面不得出现原生 title，与用户保留当前提示方式的要求存在冲突；本片保留该测试，不删除断言、不加白名单或 skip 来隐藏失败。故撤回后的当前状态不能再称为 Web 全量全绿，原 1305 passed 仅作撤回前的历史验证。后续如要调整提示规范或该守卫，必须作为明确的独立决定，不能借测试修复改造页面。

撤回后定向验证：`StockSearch.test.tsx`、`UniverseBackground.test.tsx` 与 `ui_governance.test.ts` 合计 **27 passed / 1 failed**；唯一失败为既有的原生 title 禁用守卫。检查本次 Web diff，新增 Tooltip import 与包裹均为 0。

### 9.5 范围纠正：撤回持仓页额外汇率状态展示（2026-11-03）

按用户要求删除 `PortfolioPage.tsx` 页头新增的“汇率状态：过期/最新”，恢复原有布局；该页面文件不再有本片差异。账户范围匹配与旧响应隔离修复仍保留在 `usePortfolioSignals.ts`。

测试按现有设计验证：旧汇率快照下手动刷新入口可用且不会自动刷新；刷新后从原有 Toast 核对结果和最新汇率状态，同时保留请求范围、快照/风险重载、失败与竞态断言。不再要求页面额外渲染独立状态文字，也不以新增 UI 满足旧断言。

验证：`PortfolioPage.test.tsx` **28 passed**；`npm run build`（TypeScript + Vite）通过，保留既有 chunk 警告；`git diff --check` 通过。未重跑全部 Web 测试，§9.4 的原生 title 守卫失败仍未处理。本片未提交或推送。

## 10. 测试文件内部拆分、目录细分与验收（2026-11-03）

### 10.1 范围与交接

- 代码基线：main / `2ba90010`，开始时工作区干净；本轮无 commit / push / tag。
- [完整旧→新映射与目录统计](./TEST_SUITE_SPLIT_MAPPING.md)：16 个 ≥1800 行文件拆为 113 个测试模块，16 个局部 support；64 个其他模块按业务能力迁移。
- tests/ 当前 397 个测试模块，顶层 0，最大 1725 行；三级目录内叶目录最多 15 件。服务端源文件第二轮拆分不在本轮范围。
- 每个被拆测试方法 / 函数及装饰器 AST 共 1520 项保持一致；完整 nodeid 映射（含参数与重复次数）对账前后均 5725 项。未通过删除断言、跳过或改 network 标记减少覆盖。
- 原 unittest 共同准备提取为不含 test_ 方法、不继承 TestCase 的私有 fixture mixin；只在本域复用。配置注册测试跨类常量改显式导入 fixture，避免导入测试类触发重复收集。
- analysis API 临时 ENV_FILE 作用域从模块级泄漏改为局部 patch.dict；去掉已不归属单一测试模块的整进程环境 teardown。

### 10.2 随机顺序定位与修复

首次随机种子 20261103 报告 12 条失败，其中拆分后的两处常量引用和在运行期间加载的旧打包 fake 已修正。进一步定位的真实顺序污染：

| 问题 | 根因 | 修复与保护边界 |
| --- | --- | --- |
| 台湾机构数据测试串扰 | patch 原定义模块的构造器，首次懒加载 TwInstitutionalSource 时 from-import 把 mock 永久绑定在消费模块 | patch `data_provider.institutional.tw_source.TwInstitutionalFetcher`，保留真实初始化失败及 fail-open 分支 |
| 运行时调度共享锁占用 | 静态资源启动测试进入真实 lifespan，读到开发环境配置后启动实际调度分析；测试退出时工作线程尚在运行 | 该静态资源测试局部 mock RuntimeSchedulerService 与行情预热，仍运行真实 TestClient/lifespan，断言 stop 调用；不强制释放生产共享锁、不全局关闭生命周期 |

调度生命周期测试的 5 个场景还局部隔离无关的 `_schedule_market_cards_warmup`，避免离线调度契约测试后台请求真实行情；最终相关子集 46 passed。

依赖在 `.github/requirements-ci.txt` 增加 pytest-randomly；本机版本 5.0.0。默认加载该插件时顺序会随机化；要复现本轮结果必须传明确种子，固定序则禁用插件。历史腾讯行情偶发失败本轮未复现，根因仍未确认，不能据三轮通过宣布根因关闭。

### 10.3 最终验证

| 运行方式 | 结果 | 时间 |
| --- | --- | ---: |
| 固定序，`-p no:randomly` | 5720 passed / 1 skipped / 4 deselected / 511 subtests | 343.06s |
| `--randomly-seed=20261103` | 同上 | 393.96s |
| `--randomly-seed=20261104` | 同上 | 338.71s |
| 16 个原拆分组独立进程运行 | 16/16 通过，覆盖各组全部新模块 | 各组 2.08–94.29s |
| 架构守卫 | 通过 | — |
| flake8 `E9,F63,F7,F82` | 0 | — |
| Desktop `npm test` | 49 passed | 3.29s |
| 打包脚本定向测试 | 5 passed | 4.90s |

复现命令（仓库根目录使用已装依赖的 Python 环境）：

```bash
python -m pytest tests --collect-only -q -o addopts= -p no:randomly
python -m pytest tests -m "not network" -p no:randomly -q -o addopts= --tb=short
python -m pytest tests -m "not network" --randomly-seed=20261103 -q -o addopts= --tb=short
python -m pytest tests -m "not network" --randomly-seed=20261104 -q -o addopts= --tb=short
python scripts/check_architecture.py --check
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

最终 20261104 复核在补齐 5 个调度生命周期场景的行情预热隔离后重新运行，结果保持不变（338.71s）；46 条相关定向测试也通过。

27 条既有框架弃用警告和 1 条既有跳过仍保留；网络测试未运行。运行日志为本机 `/tmp/hermesx-final-fixed.log`、`/tmp/hermesx-final-random-20261103.log`、`/tmp/hermesx-final-random-20261104-clean.log`；临时文件不是长期 CI 证据，后续应在 CI 留存结果。

### 10.4 平台验收与未闭环项

Docker daemon 已确认运行。修复 Dockerfile ENV 行内注释解析错误；镜像经过系统依赖和 npm ci，最终干净 Web 构建缺少 `@heroui-pro/react/css`。维护者明确选择保留 Pro 依赖、记录授权缺口；没有删除 CSS 导入或调整页面。Docker 完整镜像和容器启动仍未通过。

macOS arm64 实际打包发现 Python 运行库移除签名后无法加载，改为修复 ad-hoc 签名，外层 app 也保持完整 ad-hoc 封印。后端 --help、Electron .app、DMG 构建与只读挂载检查通过（259 个代码对象严格验证），Gatekeeper 因未使用 Apple Developer 身份而拒绝符合当前分发边界。独立打包后端在临时目录 `/api/health` 与首页均 200。实际 Electron 窗口启动被本机 8000 端口冲突及就绪判定问题阻塞，首页 internal_error；未改本机已有服务，未宣称桌面端到端通过。未执行 /Applications 安装、Windows 或 Intel 验收。

打包后第三方 protobuf 运行库会出现在 dist-desktop，旧 flake8 全树扫描误报 4540 项；仅将 dist-desktop / dist-web / .electron-builder-cache 加入产物排除，源码严重检查仍开启。Docker 上下文也排除这些本地产物。

### 10.5 文档、风险与回滚

当前总览重写为最新状态，旧过程保留在历史流水；14 份活动测试路径文档同步，涉及中英文对应者均同步。desktop-package.md 无对应英文专题文件，本轮仅更新现有中文版本。没有修改 README。

主要风险是支持模块的共享装配和跨模块状态，已用内容对账、固定序和双随机序覆盖；这不等于任意顺序和任意环境均无风险。完整映射用于后续增补测试与局部回滚，恢复旧模块时须撤回对应新模块，避免重复收集。打包修复可独立按本轮文件撤回，不操作用户数据。UI 规则、全量前端 lint、服务端第二轮拆分继续作为后续工作。
