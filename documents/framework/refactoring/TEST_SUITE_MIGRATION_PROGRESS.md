# HermesX 测试体系迁移进度台账（TEST_SUITE_MIGRATION_PROGRESS）

> 本文件是 [TEST_SUITE_REFACTORING_PLAN.md](./TEST_SUITE_REFACTORING_PLAN.md) 第 8.2 节约定的**统一迁移记录**，集中维护「文件归属 + 切片状态 + 验证证据」，是本轮测试重构的唯一进度真源。
> 服务端五层迁移完成率（见 `ARCHITECTURE_MIGRATION_STATUS.md`）**不**代表本轮测试整理进度，两者独立计数。

| 项目 | 约定 |
| --- | --- |
| 关联方案 | TEST_SUITE_REFACTORING_PLAN.md v1.2 |
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

## 5. 后续切片与推进计划（进行中）

- **T0 全量归属映射（待完成）**：还需对剩余 ~290 个顶层 `test_*.py` 逐文件确定目标边界/域与「移动/拆分/保留」状态。混合职责文件与大文件（见方案 §4）先登记拆分候选，不强拆。
- **T1 续批（可立即推进）**：继续挑选**无 §2 依赖 + 非文档引用**的纯领域/独立工具测试，按模板分批搬，每批验证 collect=5717 + 目标目录绿。建议每批 5–15 个文件、按业务域成组。
- **T2 按域归类**：处理带路径/包内依赖者——搬迁同片修正 `parents[...]`/`sys.path`，并对被文档引用的文件同步 `docs/*.md`（中英）与 CHANGELOG。config/infrastructure/api/bot/bootstrap/architecture 分域推进。
- **T3 内部拆分**：`test_system_config_service.py`（222 方法）、`test_multi_agent.py`、`test_analysis_api_contract.py` 等按行为契约拆分，追踪用例覆盖对应关系，记录参数化导致的用例数变化。
- **T4 公共依赖治理**：`litellm_stub` → `support/stubs/`（同步 109 引用）、根 conftest 兼容补丁适用范围评估、fixture 作用域下放、`support/paths` 统一根路径辅助。
- **T5 收口**：核对 `scripts/ci_gate.sh`、`.github/workflows/*`、全仓文档中的 `tests/` 硬编码路径；补运行说明；全量离线结果不退化，网络未跑项明示。

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
