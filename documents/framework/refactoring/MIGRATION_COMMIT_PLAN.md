# 架构迁移分步提交方案（W14 / COMMIT PLAN）

> 状态：**已定稿，逐笔执行中**（三项拍板：撤销 1 / 排除 2 / 采纳 3）
> 基线：HEAD `fe7410bb`，零提交，全部改动留在工作树
> 待提交总量：**916** = 423 新增 + 297 修改 + 196 删除（含本方案文件自身）；执行时**排除**非本任务产物的 `build的问题清单.md`，实际入库 **915**。
> 取证时间：2026-10-31

---

## 0. 为什么是这个切法（五条实测证据）

本方案不是按"看起来合理"排的序，五个约束都做过可复现实验（均在 `/tmp` 或 `git worktree` 构造，未触碰主工作区内容）。

| 编号 | 实验 | 构造方式 | 实测结果 | 对方案的约束 |
|---|---|---|---|---|
| **E-1** | 最终状态健康度 | 当前工作区直接跑 | `pytest tests scripts` → **5713 passed / 4 skipped**；`check_architecture.py --check` → **0 违规，RC=0** | 改动本身可交付，问题只在"怎么切" |
| **E-2** | 只切驱动、测试留旧版 | HEAD ∪ 新五层 ∪ 新 api/bot，tests 保持 HEAD | **57 个 collection error，exit 2**（`ImportError`：旧测试从 api/bot 模块导入已迁走的符号） | ❌ 驱动层与它的 wiring 测试**必须同一提交** → C7 不可再拆 |
| **E-3** | 切驱动+切测试，但**保留 legacy 代码** | HEAD ∪ 全部变更，但不删 196 个 legacy 文件 | **5714 passed / 3 skipped，exit 0** | ✅ legacy 删除可独立成提交 → C8 与 C7 解耦 |
| **E-4** | 守卫能否先落地 | HEAD 旧布局 + 空 baseline 跑守卫 | 报出 **15 条违规**（`src/services/*→fastapi/sqlalchemy`、`src/core/pipeline→bot.models`、`api/*→src.storage`、`src/notification.py→bot.*`） | ❌ 守卫脚本 + baseline + CI gate 必须排在删 legacy **之后** → C9 收尾 |
| **E-5** | 逐笔 checkout 独立可运行（`git worktree`） | 先按 C2→C3 顺提交，在 C2 的树上跑 `import src.config` | **`ModuleNotFoundError: No module named 'src.domain'`**：`config/llm_channels.py:16`、`config/settings.py`（9 处）、`config/field_definitions.py`（2 处）均硬依赖 `src.domain.*` | ❌ 五层内部**不是**彼此独立的纯新增 → **domain 必须先于 config 入库**，执行顺序改为 C1 → C3 → C2 → C4… |
| **E-6** | C7/C8 单独 checkout 能否跑绿 | `git worktree` 实跑 C7 `8e43c72b`、C8 `f8971664` 的全量 `pytest tests` | 不拷入属 C9 的 4 件工具链文件时**测试无法收集**；拷入后 C7 **5675 passed / 0 failed**、C8 **5674 passed / 4 skipped / 0 failed** | ⚠️ C7 的测试依赖 C9 的文件 → 本序列**不是逐笔可跑**，bisect 只保证“语义完整”，真实可运行基线从 C9 开始（详见 §7.4） |

> E-3 的 5714 与 E-1 的 5713 差 1：E-3 树里 `tests/test_notification_capabilities.py`（旧测试，最终态已删除）被 `--ignore` 跳过，不是用例增减。

**分片原则**：自底向上纯新增（C2–C6）→ 驱动与测试原子切换（C7）→ 删旧（C8）→ 强制（C9）。legacy 代码在最后两笔之前一直存在但已无人引用，这样 E-2 与 E-4 两个约束都不会被破坏。

**五层之间的实际入库顺序（由 E-5 修正）**：`C1 docs → C3 domain → C2 config → C4 infrastructure → C5 application → C6 bootstrap → C7 驱动+测试 → C8 删 legacy → C9 守卫与工具链`。依据是静态 import 取证：`src/domain` 对外只依赖 `src.domain`（27 处）与 `src.utils`（2 处），不碰 config；`src/config` 硬依赖 `src.domain`（12 处）；`src/utils/time.py` 的消费者在 infrastructure/application，因此随 config 一笔入库仍早于首个消费方。⚠️ 本文余下部分的 **C2/C3 编号指内容组，不代表先后**；执行时以本行的顺序为准。

---

## 1. 提交清单（9 笔）

### C1 `docs(arch): record architecture baseline, layering rules and migration facts`

- **内容**：36 个文件（32 改 + 4 新增）
  - 根级：`AGENTS.md`、`ARCHITECTURE_TARGET.md`、`SKILL.md`、`stock_data_view.md`
  - `docs/` 18 篇：`LLM_CONFIG_GUIDE(_EN)`、`agent-stream-events`、`analysis-context-pack`、`bot-command(_EN)`、`decision-signals`、`full-guide(_EN)`、`image-extract-prompt`、`intelligence-sources`、`llm-providers`、`multi-strategy-contract`、`notifications`、`run-diagnostics-p1/p2/p3`、`settings-help`
  - `documents/`：`CHANGELOG.md`、`framework/` 3 篇 ADR/进度、`product/` 6 篇中文产品文档
  - 新增：`documents/framework/refactoring/ARCHITECTURE_MIGRATION_STATUS.md`、`documents/framework/refactoring/MIGRATION_COMMIT_PLAN.md`（本文件）、`documents/framework/security_performance_baseline.md`、`documents/framework/src_migration_index.md`（4 件）
  - **已定排除**：`build的问题清单.md`（非本任务产物，评估后决定不入库，执行完 9 笔后仍作为未跟踪文件留在工作区）
- **message 描述（评审用中文，实际提交用英文正文）**
  本笔只改文档与协作治理资产，不动任何生产代码。内容是把架构迁移过程中确认下来的事实固化为单一真源：五层职责边界与依赖方向、各层可引用的模块白名单、legacy 路径到目标路径的迁移索引，以及安全与性能基线的量化结论。文档中的路径锚点必须与后续代码提交完全一致，因为有多条测试断言文档与 `.env.example` 不得残留 legacy 路径。把它放在最前，是为了让评审者先获得判断后续 8 笔改动是否合理的参照系。
- **英文 message**

  ```text
  docs(arch): record architecture baseline, layering rules and migration facts

  Capture the confirmed architecture contracts as the single source of truth
  before any code lands: the five-layer responsibilities, the allowed import
  direction per layer, the legacy-path to target-path migration index, and the
  measured security/performance baseline. No production code changes here.
  Path anchors in these documents are load-bearing - several tests assert that
  docs and .env.example carry no legacy paths - so they must match the code
  slices that follow. Ordering this first gives reviewers the reference frame
  to judge the remaining eight commits.
  ```
- **跑什么**：无需跑测试（纯文档）。改 AI 治理资产时补跑 `python scripts/check_ai_assets.py`。

---

### C2 `feat(config): split configuration into src/config with shared utils`

- **内容**：10 个文件（9 新增 + 1 删除）—— **必须在 domain 之后入库**（E-5）
  - 新增 `src/config/`：`__init__.py`（门面转发）、`settings.py`、`env_file.py`、`env_parsers.py`、`llm_channels.py`、`registry.py`、`field_definitions.py`、`field_help.py`
  - 新增 `src/utils/time.py`
  - 删除 `src/config.py`
- **message 描述**
  把原来单文件 `src/config.py` 拆成配置包，按运行时语义分成四个职责面：`settings` 持有配置值与加载单例，`env_parsers`/`llm_channels` 提供解析与档位归一化助手，`registry`/`field_definitions`/`field_help` 承载 Web 设置页字段元数据与帮助文案，`env_file` 只做 `.env` 原子读写。`__init__.py` 仅转发、不新增语义，因此调用方 `from src.config import Config, get_config` 的写法完全不变。删除旧模块是安全的：Python 导入时包优先于同名模块，旧调用方在过渡期仍解析到新包。
- **英文 message**

  ```text
  feat(config): split configuration into src/config with shared utils

  Break the monolithic src/config.py into a package with four distinct
  responsibilities: settings holds runtime values and the load singleton,
  env_parsers and llm_channels provide parsing and tier-normalization
  helpers, registry plus field_definitions/field_help carry the web settings
  page metadata, and env_file only reads/writes .env atomically.
  __init__.py is a pure forwarding facade, so existing call sites
  `from src.config import Config, get_config` stay unchanged. Dropping
  src/config.py is safe: Python resolves a package ahead of a same-named
  module, so not-yet-migrated importers keep working throughout the switch.
  ```
- **跑什么**：`./.venv/bin/python -m pytest -q tests`

---

### C3 `feat(domain): add src/domain business rules layer`

- **内容**：67 个新增文件（`src/domain/`：`analysis`、`generation`、`market`、`notification`、`decision`、`shared` 等子包）
- **message 描述**
  新增领域层，收纳不依赖 IO、框架和外层业务的纯规则：市场清单解析与交易日历语义、通知契约/噪声规则/端点约束、生成链路的后端身份与响应清洗、决策信号归因与上下文包结构、以及跨域共享的脱敏与 URL 校验助手。本笔为纯新增，没有任何模块引用它，因此仓库仍处于旧布局可运行状态。分层规则由守卫强制：领域层禁止引用 `fastapi`、`sqlalchemy`、`data_provider`、`src.services/core/storage/config/repositories/infrastructure/application` 与 `api.`/`bot.`，保证后续不会有代码反向把外层细节塞回规则里。
- **英文 message**

  ```text
  feat(domain): add src/domain business rules layer

  Introduce the domain layer holding pure business rules with no IO,
  framework or outer-layer dependency: market list parsing and trading-calendar
  semantics, notification contracts/noise/endpoint constraints, generation
  backend identity and response sanitizing, decision-signal attribution and the
  analysis context-pack shape, plus shared redaction and URL validation
  helpers. This slice is purely additive - nothing imports it yet, so the
  repository still runs on the legacy layout. The guard enforces the boundary:
  the domain may not reach fastapi, sqlalchemy, data_provider, src.services,
  src.core, src.storage, src.config, src.repositories, src.infrastructure,
  src.application, api. or bot., so later slices cannot smuggle outer details
  back into the rules.
  ```
- **跑什么**：`./.venv/bin/python -m pytest -q tests`

---

### C4 `feat(infrastructure): add src/infrastructure adapters`

- **内容**：109 个新增文件（`src/infrastructure/`：`persistence`、`notification/senders`、`reporting`、`observability`、`generation` 等）
- **message 描述**
  新增基础设施层，集中承载所有 IO 与框架细节：ORM 模型与会话、UTC 时间归一化基座、schema 兼容升级，十余个通知渠道发送器（飞书/钉钉/企微/Telegram/Pushover/邮件/Webhook 等）、图片与文档渲染、可观测性与日志装配。它是五层里的最外圈实现，只被 `bootstrap` 装配给应用层端口，自身禁止依赖 `api.`/`bot.`。本笔仍为纯新增，旧实现原地未动，两套并存但不互相引用，为下一步"切驱动"提供可直接绑定的目标符号，同时让删除旧目录成为一次纯机械动作。
- **英文 message**

  ```text
  feat(infrastructure): add src/infrastructure adapters

  Add the outermost layer holding IO and framework detail: ORM models and
  sessions, the UTC normalization base and schema-compat upgrade path, more
  than a dozen notification senders (Feishu, DingTalk, WeCom, Telegram,
  Pushover, email, webhooks, ...), image/document rendering, and logging and
  observability wiring. It is assembled by src.bootstrap into application
  ports and must not depend on api. or bot., which the guard enforces. Still
  purely additive: the legacy implementations stay untouched and neither side
  imports the other, so this gives the next slice concrete symbols to bind to
  and turns removing the old directories into a mechanical deletion.
  ```
- **跑什么**：`./.venv/bin/python -m pytest -q tests`

---

### C5 `feat(application): add use cases, ports and runtime orchestration`

- **内容**：168 个新增文件（`src/application/`：`analysis`、`notification`、`runtime`、`intelligence`、`generation`、`market`、`history`、`decision`、`portfolio`、`quote` 等）
- **message 描述**
  新增应用层，存放用例编排与自己定义、自己持有的端口：分析流水线与持久化端口、资讯抓取端口与代理边界、生成链路运行时端口、行情/历史/自选/组合/告警等用例，以及调度与系统配置编排。应用层只依赖领域与端口，禁止直接引用具体适配器与驱动（`fastapi`、`sqlalchemy`、`data_provider`、`src.repositories`、`src.infrastructure`、`src.storage`、`api.`、`bot.`），并额外禁止触碰 `src.services` 私有成员，避免外层反向吃掉内层实现细节。本笔为纯新增，旧路径仍完整可用。
- **英文 message**

  ```text
  feat(application): add use cases, ports and runtime orchestration

  Add the use-case layer: the analysis pipeline with its persistence port,
  intelligence fetching behind its own port (including the proxy boundary),
  generation runtime ports, market/history/watchlist/portfolio/alert use
  cases, and scheduling and system-config orchestration. Application depends
  only on the domain and on ports it declares and owns, and may not import
  fastapi, sqlalchemy, data_provider, src.repositories, src.infrastructure,
  src.storage, api. or bot.; it also may not touch private members of
  src.services, which stops the outer layer from swallowing inner
  implementation detail. Purely additive - legacy paths remain fully usable.
  ```
- **跑什么**：`./.venv/bin/python -m pytest -q tests`

---

### C6 `feat(bootstrap): add wiring and process lifecycle`

- **内容**：25 个新增文件（`src/bootstrap/`：`environment`、`logging_setup`、`database`、`scheduling`、`api_lifecycle`、`serve`、`runtime`、以及按域拆分的 `analysis`/`quote`/`notification`/`portfolio`/`watchlist`/`history`/`usage`/`system_config` 等装配模块）
- **message 描述**
  新增装配层，把具体适配器绑定到应用层端口，并集中持有进程级生命周期：环境加载、日志装配、数据库与会话、调度注册、ASGI 生命周期。约定是导入即安全——导入任何 bootstrap 模块都不会启动调度器、打开数据库或发起网络请求；驱动（ASGI app、Bot 客户端）自己注入进来，因此 bootstrap 禁止依赖 `api.`/`bot.`。这一笔补完五层的最后一层，使 C7 只需重写调用点、不必临时造装配代码，从而把最大那笔提交的 diff 面压到最小。
- **英文 message**

  ```text
  feat(bootstrap): add wiring and process lifecycle

  Add the composition layer that binds concrete adapters to application ports
  and owns process-level lifecycle: environment loading, logging setup,
  database and session creation, scheduler registration, ASGI lifecycle and
  serve wiring. Importing any bootstrap module must stay side-effect free -
  no scheduler start, no database open, no network call - and drivers (the
  ASGI app, bot clients) inject themselves, so bootstrap may not import api.
  or bot. Completing the fifth layer here means the next commit only rewrites
  call sites instead of also inventing wiring code, which keeps the largest
  slice's diff surface minimal.
  ```
- **跑什么**：`./.venv/bin/python -m pytest -q tests`

---

### C7 `refactor(ports): switch drivers and tests to the inner layers` ⚠️ 最大且唯一不可拆的一笔

- **内容**：287 个文件（251 改 + 34 新增 + 2 删除）
  - 驱动与入口：`api/`（24 改 + 删 `api/v1/schemas/run_flow.py`）、`bot/`（20）、`data_provider/`（7）、`apps/hrs-web/`（2）、`main.py`、`server.py`
  - 过渡面：`src/storage.py`（瘦身为"装配 DB + 委托 schema 升级 + 单例与 `persist_llm_usage` 入口"三件事）、`src/services/__init__.py`（仅保留 `get_task_service` 惰性兼容映射）、`src/brokers/futu/portfolio.py`、`src/data/stock_index_loader.py`
  - 测试：`tests/` 192 改 + 34 新增（**不含** 3 个守卫测试）+ 删 `tests/test_notification_capabilities.py`
- **message 描述**
  把驱动层与全部测试从 legacy 路径重指向五层：api 端点与 bot 命令改为调用应用层用例，不再直连持久化、数据源或基础设施；`data_provider` 只保留适配职责；Web/桌面客户端同步少量字段与帮助文案引用。同时把 api/bot/`src/services`/`src/storage` 的引用边界钉进回归测试。本笔刻意把"切驱动"与"切测试"合并：实验证明拆开会让 57 个测试模块在收集期 `ImportError`，中间提交直接变红。旧实现此处一律不删，留到下一笔独立成提交。
- **英文 message**

  ```text
  refactor(ports): switch drivers and tests to the inner layers

  Repoint the entry drivers and the whole test suite from legacy paths to the
  five layers: api endpoints and bot commands now call application use cases
  instead of reaching persistence, providers or infrastructure directly;
  data_provider keeps only adapter duties; web/desktop references follow the
  new module names. src/storage.py is narrowed to db assembly, delegated
  schema upgrade and the usage singleton, and src/services/__init__.py keeps a
  single lazy compatibility mapping. Deliberately bundling drivers with their
  tests: an experiment showed that switching drivers while leaving the old
  tests fails collection with 57 ImportErrors, which would turn this commit
  red. No legacy module is deleted here - that is the next, separate slice.
  ```
- **跑什么**：
  ```bash
  ./.venv/bin/python -m pytest -q tests scripts   # 期望全绿（E-3 已验证：5714 passed / 3 skipped）
  ./.venv/bin/python -m compileall -q api bot data_provider src main.py server.py
  ```
- **暂存注意**：守卫三测留给 C9，否则 `test_check_architecture.py` 会因为 `scripts/check_architecture.py` 尚未落地而 `ImportError`。

---

### C8 `chore(arch): delete legacy flat modules and packages`

- **内容**：193 个删除，无新增
  | 目录 | 数量 |
  |---|---|
  | `src/services/`（实现文件，保留 `__init__.py`） | 56 |
  | `src/agent/` | 56 |
  | `src/` 根级扁平 `.py`（`analyzer`/`scheduler`/`search_service`/`stock_analyzer`/`market_analyzer`/`notification*`/`formatters`/`enums`/`md2img`/`feishu_doc`/`logging_config`/`report_language`/`market_phase_*`/`market_structure_prompt`/`market_context`/`daily_market_context_guardrail`/`phase_decision_guardrail`/`analysis_context_pack_*`/`notification_{capabilities,contracts,noise,routing}`） | 24 |
  | `src/notification_sender/` | 15 |
  | `src/llm/` | 12 |
  | `src/repositories/` | 11 |
  | `src/core/`（磁盘上只剩 `__pycache__`，删除后目录自行消失） | 11 |
  | `src/schemas/` | 8 |
- **message 描述**
  删除已无人引用的 legacy 实现。删除前先做全仓引用扫描：`src.{services,core,agent,llm,repositories,schemas,notification_sender}` 与根级扁平模块在生产代码、`api/`、`bot/`、`data_provider/`、测试中的真实导入均已归零（入库前复扫：855 个候选文件、正则捕获 `from/import` 命中为 0），只剩 **6 个**测试文件把这类路径当作"禁止出现"的断言字符串（`test_analysis_endpoint_wiring`、`test_kline_endpoint_wiring`、`test_limit_pool_endpoints`、`test_sector_endpoint_refactor`、`test_bot_use_case_wiring`、`test_analysis_context_builder`），另有守卫测试仅在临时目录里构造同名的假路径（守卫测试本身属 C9，本笔提交时尚未入库），两者都不依赖 legacy 文件存在。实验 E-3 已单独验证过"切完驱动+测试但保留 legacy"这一状态全绿，因此本笔只可能因遗漏引用而失败，diff 是纯删除、可逐文件核对。`src/services/__init__.py` 与 `src/storage.py` 作为对外兼容面刻意保留。
- **英文 message**

  ```text
  chore(arch): delete legacy flat modules and packages

  Remove the legacy implementations that no longer have any referent. Before
  deleting, a repository-wide scan confirmed zero production, api/, bot/,
  data_provider/ and test imports of src.{services,core,agent,llm,repositories,
  schemas,notification_sender} and of the root-level flat modules. The only
  remaining mentions are six tests that keep such paths in forbidden-import
  assertions and the guard test, which builds equivalent paths only inside a
  temporary directory - neither depends on the legacy files existing.
  Experiment E-3 already proved the "switched drivers and tests, legacy still
  present" state is green, so this commit can only fail on a missed reference
  and its diff is pure deletion. src/services/__init__.py and src/storage.py
  are kept as external compatibility surfaces.
  ```
- **跑什么**：
  ```bash
  ./.venv/bin/python -m pytest -q tests scripts
  ./.venv/bin/python -m compileall -q src api bot data_provider main.py server.py
  ```

---

### C9 `build(arch): enforce the import guard and repoint tooling and CI` ⚠️ 必须收尾

- **内容**：20 个文件（14 改 + 6 新增）
  - 新增：`scripts/check_architecture.py`、`scripts/architecture_baseline.json`（`entries: []`）、`scripts/measure_performance_baseline.py`、`tests/test_check_architecture.py`、`tests/test_security_baseline.py`、`tests/test_schema_migration_guard.py`
  - 改：`scripts/ci_gate.sh`（新增 `architecture_check` 与 `architecture` 子命令 + `py_compile` 路径改写）、`scripts/{test.sh,check_env.py,build-backend.ps1,build-backend-macos.sh,codex_app_server_gate_a.py,e2e_test_feishu_app.py,generate_notification_actions_env_table.py}`、`.github/workflows/{ci.yml,docker-publish.yml,ghcr-dockerhub.yml}`、`.github/PULL_REQUEST_TEMPLATE.md`、`setup.cfg`、`requirements.txt`
- **message 描述**
  让新分层从"约定"变成"门禁"。守卫脚本按 `ARCHITECTURE_TARGET.md` 第 2 节的规则表扫描跨层导入，baseline 置空表示零违规债务，CI 通过 `ci_gate.sh architecture` 阻断新增违规；同时把 `ci_gate.sh`、`test.sh`、`check_env.py`、构建脚本与三条 workflow 的冒烟导入、Docker 与 Release 编译路径全部重指向新模块，并同步 `setup.cfg` 的入口清单。**必须排在删除 legacy 之后**：E-4 实测在旧布局上用空 baseline 跑守卫会报出 15 条违规，提前落地会立刻把 CI 打红。
- **英文 message**

  ```text
  build(arch): enforce the import guard and repoint tooling and CI

  Turn the new layering from convention into a gate. The guard script scans
  cross-layer imports against the rule table in ARCHITECTURE_TARGET.md section 2,
  the baseline ships with an empty entries list meaning zero tolerated debt,
  and CI blocks new violations through `ci_gate.sh architecture`. The same
  commit repoints ci_gate.sh, test.sh, check_env.py, the build scripts, three
  workflows (ci, docker-publish, ghcr-dockerhub) and the PR template to the new
  module paths, and updates the declared entry-point list in setup.cfg. This
  must land after the legacy deletion: measured on the old layout with an empty
  baseline the guard reports 15 violations, so landing it earlier would turn CI
  red on arrival.
  ```
- **跑什么**：
  ```bash
  ./.venv/bin/python scripts/check_architecture.py --check          # 期望 RC=0
  ./scripts/ci_gate.sh all
  ./.venv/bin/python -m pytest -q tests scripts
  ```

---

## 2. 数量守恒核对

| 提交 | 新增 | 修改 | 删除 | 小计 |
|---|---:|---:|---:|---:|
| C1 | 4 | 32 | 0 | 36 |
| C2 | 9 | 0 | 1 | 10 |
| C3 | 67 | 0 | 0 | 67 |
| C4 | 109 | 0 | 0 | 109 |
| C5 | 168 | 0 | 0 | 168 |
| C6 | 25 | 0 | 0 | 25 |
| C7 | 34 | 251 | 2 | 287 |
| C8 | 0 | 0 | 193 | 193 |
| C9 | 6 | 14 | 0 | 20 |
| **入库合计** | **422** | **297** | **196** | **915** |

与 `git status --porcelain -uall` 展开口径对比：取证快照 423/297/196=916（含本方案文档），**减去刻意排除的未跟踪件 `build的问题清单.md` 后入库 915**（422 新增 / 297 修改 / 196 删除），可作为"是否漏项"的验收尺。

---

## 3. 逐笔执行脚本（暂存 → 验证 → 提交，**每段自带完整英文 message**）

> ⚠️ **执行顺序没有按 C2→C3 的字面编号**：按 E-5 的结论，先跑下面标为“C3 —— domain 层”的块，再跑“C2 —— config 层”的块；其余 C1→C4→…→C9 依次不变。

> ⚠️ 已获授权逐笔执行（2026-10-31）：每笔暂存与验证完成后贴 `git diff --cached --stat` 给用户，再 `commit`，一笔一确认。**全程不执行 `git push` / `git tag` / 建 PR**，推送节奏由维护者自己掌握。
>
> **message 约定**（与 `AGENTS.md` 一致）：
> 1. 提交正文一律使用下面 heredoc 里的**完整英文 message**，与 §1 各笔的「英文 message」代码块**逐字一致**——执行时不要临场改写、不要翻译、不要截断；§1 的中文描述仅供你评审对照，**不入库**。
> 2. 一律用 `git commit -F -` 从 stdin 读入，不用 `-m` 拼接（避免 shell 引号吃掉换行与反引号）。
> 3. 不加 `Co-Authored-By` / 任何 agent 署名 trailer；title 不含 `#major/#minor/#patch`（**不触发自动 tag**）。
> 4. **先验证后提交**：每笔的 pytest / 守卫必须在该笔 `commit` 之前跑完并全绿，红了就停下排查，不要带病提交。
> 5. heredoc 内的 message 正文**必须顶格**（前置空格会被原样写进提交正文，导致缩进错乱）。

```bash
cd /Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX
V=./.venv/bin/python                       # 已确认存在（venv python 3.11.15）
PYTHONDONTWRITEBYTECODE=1                  # 避免 __pycache__ 混入暂存区
```

### C1 —— 文档与治理资产

```bash
git add -A -- AGENTS.md ARCHITECTURE_TARGET.md SKILL.md stock_data_view.md docs documents
git diff --cached --name-only | wc -l      # 期望 36（已排除 build的问题清单.md，不列入暂存）
python scripts/check_ai_assets.py

git commit -F - <<'MSG'
docs(arch): record architecture baseline, layering rules and migration facts

Capture the confirmed architecture contracts as the single source of truth
before any code lands: the five-layer responsibilities, the allowed import
direction per layer, the legacy-path to target-path migration index, and the
measured security/performance baseline. No production code changes here.
Path anchors in these documents are load-bearing - several tests assert that
docs and .env.example carry no legacy paths - so they must match the code
slices that follow. Ordering this first gives reviewers the reference frame
to judge the remaining eight commits.
MSG
```

### C2 —— config 层

```bash
git add -A -- src/config src/utils src/config.py
git diff --cached --name-only | wc -l      # 期望 10（注意：pathspec `src/config` 不匹配同名文件 `src/config.py`，必须显式列出）
$V -m pytest -q tests

git commit -F - <<'MSG'
feat(config): split configuration into src/config with shared utils

Break the monolithic src/config.py into a package with four distinct
responsibilities: settings holds runtime values and the load singleton,
env_parsers and llm_channels provide parsing and tier-normalization
helpers, registry plus field_definitions/field_help carry the web settings
page metadata, and env_file only reads/writes .env atomically.
__init__.py is a pure forwarding facade, so existing call sites
`from src.config import Config, get_config` stay unchanged. Dropping
src/config.py is safe: Python resolves a package ahead of a same-named
module, so not-yet-migrated importers keep working throughout the switch.
MSG
```

### C3 —— domain 层

```bash
git add -A -- src/domain
git diff --cached --name-only | wc -l      # 期望 67
$V -m pytest -q tests

git commit -F - <<'MSG'
feat(domain): add src/domain business rules layer

Introduce the domain layer holding pure business rules with no IO,
framework or outer-layer dependency: market list parsing and trading-calendar
semantics, notification contracts/noise/endpoint constraints, generation
backend identity and response sanitizing, decision-signal attribution and the
analysis context-pack shape, plus shared redaction and URL validation
helpers. This slice is purely additive - nothing imports it yet, so the
repository still runs on the legacy layout. The guard enforces the boundary:
the domain may not reach fastapi, sqlalchemy, data_provider, src.services,
src.core, src.storage, src.config, src.repositories, src.infrastructure,
src.application, api. or bot., so later slices cannot smuggle outer details
back into the rules.
MSG
```

### C4 —— infrastructure 层

```bash
git add -A -- src/infrastructure
git diff --cached --name-only | wc -l      # 期望 109
$V -m pytest -q tests

git commit -F - <<'MSG'
feat(infrastructure): add src/infrastructure adapters

Add the outermost layer holding IO and framework detail: ORM models and
sessions, the UTC normalization base and schema-compat upgrade path, more
than a dozen notification senders (Feishu, DingTalk, WeCom, Telegram,
Pushover, email, webhooks, ...), image/document rendering, and logging and
observability wiring. It is assembled by src.bootstrap into application
ports and must not depend on api. or bot., which the guard enforces. Still
purely additive: the legacy implementations stay untouched and neither side
imports the other, so this gives the next slice concrete symbols to bind to
and turns removing the old directories into a mechanical deletion.
MSG
```

### C5 —— application 层

```bash
git add -A -- src/application
git diff --cached --name-only | wc -l      # 期望 168
$V -m pytest -q tests

git commit -F - <<'MSG'
feat(application): add use cases, ports and runtime orchestration

Add the use-case layer: the analysis pipeline with its persistence port,
intelligence fetching behind its own port (including the proxy boundary),
generation runtime ports, market/history/watchlist/portfolio/alert use
cases, and scheduling and system-config orchestration. Application depends
only on the domain and on ports it declares and owns, and may not import
fastapi, sqlalchemy, data_provider, src.repositories, src.infrastructure,
src.storage, api. or bot.; it also may not touch private members of
src.services, which stops the outer layer from swallowing inner
implementation detail. Purely additive - legacy paths remain fully usable.
MSG
```

### C6 —— bootstrap 层

```bash
git add -A -- src/bootstrap
git diff --cached --name-only | wc -l      # 期望 25
$V -m pytest -q tests

git commit -F - <<'MSG'
feat(bootstrap): add wiring and process lifecycle

Add the composition layer that binds concrete adapters to application ports
and owns process-level lifecycle: environment loading, logging setup,
database and session creation, scheduler registration, ASGI lifecycle and
serve wiring. Importing any bootstrap module must stay side-effect free -
no scheduler start, no database open, no network call - and drivers (the
ASGI app, bot clients) inject themselves, so bootstrap may not import api.
or bot. Completing the fifth layer here means the next commit only rewrites
call sites instead of also inventing wiring code, which keeps the largest
slice's diff surface minimal.
MSG
```

### C7 —— 切驱动 + 切测试（守卫三测留给 C9）

```bash
git add -A -- api bot data_provider apps main.py server.py \
              src/storage.py src/services/__init__.py src/brokers src/data tests
git reset -q -- tests/test_check_architecture.py tests/test_security_baseline.py tests/test_schema_migration_guard.py
git diff --cached --name-only | wc -l      # 期望 287
$V -m pytest -q tests scripts              # 期望 5714 passed / 3 skipped（E-3 实测值）

git commit -F - <<'MSG'
refactor(ports): switch drivers and tests to the inner layers

Repoint the entry drivers and the whole test suite from legacy paths to the
five layers: api endpoints and bot commands now call application use cases
instead of reaching persistence, providers or infrastructure directly;
data_provider keeps only adapter duties; web/desktop references follow the
new module names. src/storage.py is narrowed to db assembly, delegated
schema upgrade and the usage singleton, and src/services/__init__.py keeps a
single lazy compatibility mapping. Deliberately bundling drivers with their
tests: an experiment showed that switching drivers while leaving the old
tests fails collection with 57 ImportErrors, which would turn this commit
red. No legacy module is deleted here - that is the next, separate slice.
MSG
```

### C8 —— 删 legacy

```bash
git add -A -- src/agent src/services src/core src/llm src/repositories src/schemas src/notification_sender
git add -A -- $(git status --porcelain -uall | awk '$1=="D"{print $2}' | grep '^src/.*\.py$')
# 执行时改用更稳的写法（避开 shell 词分割与八进制转义）：先把 D 路径写进清单，再喂给 git
./.venv/bin/python -c "import subprocess;d=[l[3:] for l in subprocess.run(['git','status','--porcelain','-uall'],capture_output=True,text=True).stdout.splitlines() if l[:2]==' D'];open('/tmp/c8_list.txt','w').write('\n'.join(d)+'\n');print(len(d))"
git add -A --pathspec-from-file=/tmp/c8_list.txt
git diff --cached --name-status --no-renames | wc -l      # 期望 193（全部为 D）
git ls-files src/services/__init__.py src/storage.py src/auth.py src/__init__.py src/webui_frontend.py   # 兼容面必须仍在索引
$V -m pytest -q tests scripts

git commit -F - <<'MSG'
chore(arch): delete legacy flat modules and packages

Remove the legacy implementations that no longer have any referent. Before
deleting, a repository-wide scan confirmed zero production, api/, bot/,
data_provider/ and test imports of src.{services,core,agent,llm,repositories,
schemas,notification_sender} and of the root-level flat modules. The only
remaining mentions are six tests that keep such paths in forbidden-import
assertions and the guard test, which builds equivalent paths only inside a
temporary directory - neither depends on the legacy files existing.
Experiment E-3 already proved the "switched drivers and tests, legacy still
present" state is green, so this commit can only fail on a missed reference
and its diff is pure deletion. src/services/__init__.py and src/storage.py
are kept as external compatibility surfaces.
MSG
```

### C9 —— 守卫与工具链

```bash
git add -A -- scripts .github setup.cfg requirements.txt tests
git diff --cached --name-only | wc -l      # 期望 20
$V scripts/check_architecture.py --check   # 期望 RC=0
./scripts/ci_gate.sh all

git commit -F - <<'MSG'
build(arch): enforce the import guard and repoint tooling and CI

Turn the new layering from convention into a gate. The guard script scans
cross-layer imports against the rule table in ARCHITECTURE_TARGET.md section 2,
the baseline ships with an empty entries list meaning zero tolerated debt,
and CI blocks new violations through `ci_gate.sh architecture`. The same
commit repoints ci_gate.sh, test.sh, check_env.py, the build scripts, three
workflows (ci, docker-publish, ghcr-dockerhub) and the PR template to the new
module paths, and updates the declared entry-point list in setup.cfg. This
must land after the legacy deletion: measured on the old layout with an empty
baseline the guard reports 15 violations, so landing it earlier would turn CI
red on arrival.
MSG
```

### 收尾自检（未跟踪应剩 1 件：`build的问题清单.md`）

```bash
git status --porcelain -uall | grep -v '__pycache__'
git log --oneline fe7410bb..HEAD           # 应为 9 行
git log -1 --format='%B' | head -3         # 抽查正文换行与顶格是否正确
```

**逐笔 vs 攒齐再提**：`git add` 是幂等的、`commit` 才固定边界，所以可以先 `add` 后集中核对再 `commit`。但每笔提交前请核对暂存数与 §2 守恒表一致——数量对不上说明有路径漏挂或误挂；message 一律用本节 heredoc，别手打。

---

## 4. 需要你拍板的三点（执行前已复核，第 1 项撤销）

1. ~~**兼容面与文档口径冲突**~~ —— **已核实为本方案误读，不存在冲突，无需动作**。
   复核结论：`ARCHITECTURE_TARGET.md` 没有 §6.1；「不把包级 shim 当作通用兼容机制」在 §6（L326），而 §4.5「未迁移面文件级索引」的留存项登记表（L283–292）**已经逐条登记** `src/services/__init__.py`（兼容面，全仓 0 生产调用方）与 `src/storage.py`（已批准例外），并给出各自的移除前置条件（ADR-004 / ADR-006，见 `documents/framework/architecture_migration_adr.md`）。因此原 A/B 二选一作废：C1 不再补文档例外，C8 也不扩大删除范围，按现有登记原样提交。
   原 B 方案的附带信息留档备查：若将来真要删 `src/services/__init__.py`，除 `scripts/ci_gate.sh` 的 `py_compile src/storage.py`、`setup.cfg` 入口清单外，还必须同步改 `scripts/build-backend-macos.sh:94` 与 `scripts/build-backend.ps1:110` 的 PyInstaller hidden-import 并跑桌面端打包验证——这正是 ADR-006 选择保留的原因。

2. **`build的问题清单.md` 是否随 C1 入库**
   它是工作区里唯一非本任务产物的未跟踪文件。**已定：排除**，不列入任何一笔的暂存集，来 9 笔提交后它仍以未跟踪状态留在工作区（收尾自检预期剩这一件）。若你后来改主意要留档，单独补一笔 `docs` 提交即可，不要夹进 C1。

3. **`pytest` 裸跑会红（建议顺手修）**
   仓库无 `testpaths`，`pytest` 会去收集 `vibe-template/zentrade/backend/tests` 并以 `ModuleNotFoundError` 中断（exit 2）。建议在 C9 的 `setup.cfg` 里加 `testpaths = tests scripts`，让本地默认命令与 CI 一致；不改也不影响本方案（所有验证命令都已显式指定目录）。

---

## 5. 风险与回滚

| 风险 | 影响 | 缓解 |
|---|---|---|
| C7 diff 巨大（287 文件）不可再拆 | 单笔 review 负担重 | 靠 C1–C6 先把语义讲清；review 时按 `api/` → `bot/` → `data_provider/` → `tests/` 四段看；拆开的代价已由 E-2 量化（57 个收集错误） |
| 中间提交只跑 pytest、未跑守卫 | C1–C8 期间无静态分层校验 | 每笔补跑 `$V -m compileall -q <改动目录>`；守卫在 C9 一次性阻断 |
| `git add -A -- src/...` 误吞 `__pycache__` | 提交夹带二进制垃圾 | `__pycache__/` 已在 `.gitignore` 第 21 行；仍建议 `PYTHONDONTWRITEBYTECODE=1`，并在终审时看 `git diff --cached --stat` |
| C8 遗漏引用 | 该提交红 | 已做全仓 import 扫描（生产/驱动/测试中 legacy 真实引用为 0，只有 6 个"禁止出现"断言 + 守卫测试的 tempdir 构造）；且 E-3 证明"切完但保留"是绿的，删除面是纯减法 |
| 非 ASCII 文件名在 `git status` 里被八进制转义 | 生成清单时漏挂文件 | C1 不使 `git add -A` 扫根级单文件，而是显式列出四个根级 md（`build的问题清单.md` 已定排除）；核对口径统一用 `git status --porcelain -uall` 展开计数 916 |
| **worktree 里缺 `.env.example`（被 `.gitignore` 屏蔽）当代码回归** | 误判 5 条红为迁移缺陷 | 该文件永不在任何提交里；验证前 `cp .env.example <wt>/`，已拷 `.env` 同理（见 §7.4） |
| **C7/C8 的测试依赖 C9 的 4 件工具链文件** | 中间笔不可独立收集 | 已由 E-6 实测定位；不重写历史、不夹带文件，改以 §7.1/§7.4 如实记录可运行基线从 C9 开始 |
| **§1 与 §3 的 message 双处维护漂移** | 提交的正文与评审过的正文不一致 | 已做逐字校验：抽出 §1 九个 text 围栏块与 §3 九个 `<<'MSG'` heredoc 块，去缩进后逐行对比，C1–C9 **全部 IDENTICAL**（行数 10/11/13/11/11/11/12/13/12）。后续若改任一处，必须重跑此对比 |
| **git rename 检测使计数口径飘移** | 按 `--stat` / `--name-only` 核数会对不上守恒表 | C2 的 `src/config.py`（删）与 `src/config/settings.py`（增）被识别为 **rename R087**，9 条路径对应 10 个 porcelain 项。统一改用 **`git diff --cached --name-status --no-renames \| wc -l`** 作为每笔的验收尺 |
| **pathspec `src/config` 不匹配同名文件 `src/config.py`** | 删旧模块那一半静默漏提交，拖到后续笔 | 已实测确认，并在 C2 命令里显式列出 `src/config.py`；C8 删根级 `src/*.py` 同理，必须逐个列路径或先 `git add -n` 干跑核对 |
| 中途想放弃 | — | 未 push 的部分：`git reset --soft fe7410bb` 即可回到零提交状态，改动完整退回工作树（内容与当前一致，因未做任何改写）。⚠️ **C1 已由维护者手动推到 `origin/main`**，该回滚只覆盖本地，远端退出方式见 §7.3。 |
| 自动 tag / Release 被触发 | 意外发版 | 9 笔 title 均不含 `#patch/#minor/#major`，不触发自动 tag；push 与建 PR 另需单独授权 |

---

## 6. 交付结构对照

- **改了什么**：把 916 项工作树变更切成 9 笔有序提交，逐笔给出范围、中英文 commit message、验证命令与暂存命令；§3 按「暂存 → 验证 → 提交」逐笔展开，**每段自带完整英文 message 的 `git commit -F -` heredoc**，执行时无需手打或粘贴。
- **为什么这么改**：顺序由 E-2/E-3/E-4 三组实验约束——驱动与测试必须原子切换、legacy 删除可解耦、守卫必须收尾。
- **验证情况**：最终态全量 `5713 passed / 4 skipped` 与守卫 `0 违规 RC=0` 为直接实测；C7 中间态 `5714 passed / 3 skipped`、C1–C6 纯新增性质、C8 的引用扫描为构造实验 + 静态取证；§1 与 §3 的 9 条英文 message 已脚本对比为逐字一致（代码围栏 22 个、配对完整）。
- **未验证项**：未执行任何 `git commit`；未在真机跑 Docker 与三条 workflow（C9 影响面）；未跑 `npm run build`（C7 触及 `apps/hrs-web` 仅 2 个 i18n/文案文件）。
- **风险点**：见第 5 节，最高为 C7 不可拆带来的 review 负担。
- **回滚方式**：`git reset --soft fe7410bb`（未 push，改动无损退回工作树）。

---

**下一步**：第 4 节三项已按「撤销 1 / 排除 2 / 采纳 3」定稿，你已授权逐笔执行。按第 3 节顺序 C1→C9，每笔先暂存、跑验证、贴 `git diff --cached --stat`，再 `git commit -F -`，一笔一确认。

---

## 7. 执行实况与逐笔健康度（2026-10-31 补，已发生的事实）

### 7.1 已入库

| 执行序 | commit | 对应内容组 | 入库项 | 独立可运行取证 |
|---|---|---|---:|---|
| 1 | `4a315ae1` | C1 docs | 36 | 未单跑 worktree；按 §7.3 判定为**非 test-green** |
| 2 | `cec61271` | C3 domain | 67 | worktree：67/67 模块 import OK，`main`/`server` OK，legacy `src.services` OK |
| 3 | `17b70b72` | C2 config | 10 | worktree：`import src.config` → `ModuleNotFoundError: src.domain`（→ E-5，已重排）；重排后 `pytest tests` → **154 failed / 4999 passed / 3 skipped + 1 收集错误** |
| 4 | `20fb0c9b` | C4 infrastructure | 109 | `compileall` RC=0；未跑 worktree（按 §7.2 判定为 test-green：旧测试不导入它） |
| 5 | `b5014fa2` | C5 application | 168 | 同上 |
| 6 | `10e5a139` | C6 bootstrap | 25 | 同上 |
| 7 | `8e43c72b` | C7 驱动+测试 | 287 | worktree：拷入 `.env` + `.env.example` + C9 的 4 件工具链文件后 **5675 passed / 3 skipped / 0 failed**（原跑 5 failed 系 `.env.example` 被 `.gitignore` 屏蔽，见 §7.4）；**不拷那 4 件则无法收集** |
| 8 | `f8971664` | C8 删 legacy | 193 | worktree（同上环境修正）：**5674 passed / 4 skipped / 0 failed（322.42s）**，`src/` 下 `core`/`agent`/`llm`/`repositories`/`schemas`/`notification_sender` 已不存在，`services/` 只剩 `__init__.py`；仍需那 4 件才能收集 |
| 9 | `7a97cd32` | C9 守卫与工具链 | 20 | 终态主工作区跑完整门禁 `PATH=$PWD/.venv/bin:$PATH ./scripts/ci_gate.sh all` → **5713 passed / 4 deselected / 511 subtests passed（259.96s），`all checks passed`**；守卫 `--check` RC=0、严格 flake8 RC=0、`test.sh code`+`yfinance` 全过 |

执行时偏离本节的四处（均已写回 §0/§3/§5）：C2 与 C3 交换顺序；C2 的暂存命令补 `src/config.py` 显式 pathspec；C8 的暂存命令改用 `--pathspec-from-file`（避开 shell 词分割）；§4 第 3 项最终落的是 **`testpaths = tests`** 而非 `tests scripts`——实测 `scripts/` 无符合 `python_files = test_*.py` 的文件（`e2e_test_feishu_app.py` 不匹配前缀），列入无收益。

⚠️ **三笔纯新增层之间不是彼此可导入的**（不影响 test-green，因为旧测试不导入它们，但影响"完整可运行"的口径）：静态取证 `src/infrastructure` 模块级 `from src.application` **41 处**（适配器实现应用层端口，方向合法），而 `src/application/market/market_light_alerts.py:17` 又模块级 `from src.bootstrap.market import ...`（文件内自述为「过渡设计债，待后续切片端口化」，守卫并未禁这一条）——所以上表 C5 的 message 里"Application depends only on the domain and on ports it declares"是设计意图而非当前实况的完整描述，已知反例就是上述这一行。因此五层的导入完整性只有到 **C6 全部落完**才成立。

### 7.2 逐笔健康度矩阵（方案拍板前未评估到的事实）

| 笔 | 纯新增？ | test-green？ | 原因 |
|---|---|---|---|
| C1 docs | — | ❌ | 文档已改指五层新路径，而断言旧路径的测试仍在 C7 → `test_alerts_docs`、`test_analysis_context_pack_docs` 等约 15 条红 |
| C3 domain | ✅ | ✅ | 全仓无人引用，旧测试不导入它 |
| C2 config | ✅+1 删 | ❌ | 旧测试 patch 已被搬走/删掉的 `Config` 私有 helper 与薄委托 → 约 122 条红，含 1 条 `ImportError` 收集错误 |
| C4 infrastructure / C5 application / C6 bootstrap | ✅ | ✅ | 旧测试不导入它们（已静态取证）。但三层之间模块级互导，单独 checkout 其中一笔时新层自身不可导入，要到 C6 才闭合（不影响 test-green） |
| C7 | 混合（34 新/251 改/2 删） | ✅* | 所有测试适配在这一笔落地；但\*其测试文件 import 了 C9 才入库的 `scripts.check_env` / `scripts.codex_app_server_gate_a` / `scripts.generate_notification_actions_env_table` 与 `requirements.txt` 终版，**单独 checkout C7 不拷这 4 件会直接 collection error**（见 §7.4 E-6）
| C8 | 纯删除 | ✅ | 全仓扫描确认引用为 0，删除后 worktree 实跑 0 failed |
| C9 | 守卫与工具链 | ✅ | 终态 `ci_gate.sh all` 全绿（RC=0），这是本方案唯一的“完整门禁”级取证 |

取证手段：`git worktree add --detach` + 拷入 `.env`（只读，不触碰主工作区），失败归因按 `AttributeError` 聚合：`Config._legacy_keys_to_model_list` ×61、`Config._parse_litellm_yaml` ×56、`_channels_to_model_list` ×3、`src.config.os`/`load_dotenv` ×2、`get_fixed_litellm_temperature` ×1。

### 7.3 为何不为了让每一笔绿而继续拆（已拍板：保留 9 笔）

三种修法均不采纳：

- **把测试适配摘到更早的笔**：不可行。`tests/test_llm_channel_config.py` 终版第 26/27/33 行 import `src.infrastructure`/`src.application`，比 C2 晚两笔。
- **把 config 并入 C7（会变 8 笔）**：能让 C3–C6 全绿，代价是 C7 从 287 → 297 文件，且配置拆分的独立叙事被埋进切换笔。
- **把 C1+C2 都并入 C7（会变 6 笔）**：每一笔都绿，但 C7 ≈ 333 文件，单笔 review 负担最重，文档先行的设计目的消失。

采纳的口径：**不写仅为了中间态可运行而存在的一次性代码**（AGENTS.md：不新增平行实现、不做非任务需要的抽象），以「每笔 message 写明范围 + 本节记录哪几笔非 test-green 及其确切原因」替代完整 bisect 保证。全仓可交付性以**终态实测**为准（见 §0 E-1）。

回滚口径修正：执行期间 `refs/remotes/origin/main` 已从 `4a315ae1` 前进到 `10e5a139`（C1–C6 均由维护者手动推送，agent 全程未执行 push），所以上表的回滚不再全在本地。`git reset --soft fe7410bb` 只能退本地；远端已入库的笔如需退出，由维护者自行决定 revert 或 force-with-lease，本方案不代为实现。

### 7.4 worktree 独立验证的环境修正与 E-6

`git worktree add --detach /tmp/wt-<笔> <commit>` + 用主仓 `.venv/bin/python -m pytest`（`python -m` 使 cwd 进入 `sys.path[0]`，`import src.` 才能解析）。该方法有两个与代码无关的固有缺口，必须知道后才能读数：

1. **`.env.example` 永不在任何提交里**：`.gitignore` 第 3 行 `.env.*` 屏蔽了它（`git ls-tree` 在 `fe7410bb` 与 HEAD 均无该路径）。不拷入时 `test_config_env_compat` / `test_config_registry` / `test_daily_analysis_workflow_llm_env` / `test_searxng_env_docs` 共 **5 条 `FileNotFoundError` 红**；拷入后这四个文件 **164 passed**。→ 验证前必须 `cp .env.example <wt>/`。
2. **E-6（新发现，修正本方案“C7 之后自然全绿”的表述）**：C7 的测试终版直接 import 了属 C9 的 `scripts/check_env.py`、`scripts/codex_app_server_gate_a.py`、`scripts/generate_notification_actions_env_table.py` 与 `requirements.txt` 终版，因此 **C7/C8 单独 checkout 时测试无法收集**，需拷入这 4 件才能跑绿。已按 A 口径**不重写已入库的 C7/C8**（避免在维护者随时可能推送的窗口里改写历史），也不把 4 件从 C9 剔到 C7；推论：本序列的 bisect 粒度是“语义完整”而非“逐笔可跑”，真实可运行基线从 **C9** 开始。

**`testpaths` 改动的 CI 副作用（入库后实测，必须知道）**：`offline_test_suite()` 是裸跑 `python -m pytest -m "not network"`，受 `testpaths` 直接影响。旧值 `.` 在本地以 `-o testpaths=. --ignore=vibe-template` 模拟 CI 干净检出，实测收集 **5727 items**，其中 **10 个恒为 collection error**：`apps/hrs-web/scripts/test_wt/kline/test_wt_kline_backend.py` 与 `…/sector-analysis/test_wt_sector-analysis_backend.py`（已跟踪，自 `fd862ba3` 2026-08-09 入库）用的 `client` fixture 全仓无定义（只在 `tests/conftest.py` 作用域内可见）→ `fixture 'client' not found` ×10，`set -euo pipefail` 下会把 backend-gate 拖红。新值 `tests` 下收集 **5717 items / 0 error**：这 10 个既有错误消失，代价是这 2 个已跟踪的脚本样本不再进入默认收集面（它们本身从入库那天起就不可运行，不属覆盖损失；若将来要修，应移到 `tests/` 下并补 `client` fixture 而不是放宽 `testpaths`）。

**执行明细的落点**：本方案执行后的逐笔 hash 与项数、worktree 取证数值、message 事实纠正（six 而非 four 个禁止出现断言）、本片自有失误与未归因项，已同步追加到流水台账 `documents/framework/refactoring/ARCHITECTURE_MIGRATION_PROGRESS.md` **§0.174**（台账只追加不改写，本节与 §7.1–§7.3 仍是执行结果的第一事实源）。
