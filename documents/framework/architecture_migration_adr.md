# ADR-002~006：HermesX 分层迁移过程中的架构决策

> 状态：**已接受（Accepted）** ｜ 建立时间：2026-10-30 ｜ 维护：随迁移推进增补，不回改已接受条目
> 前序：`documents/framework/backend_architecture_adr.md`（ADR-001，后端分层架构与统一数据源策略）
> 判据来源：`ARCHITECTURE_TARGET.md` §2 依赖规则、§4 归属表、§4.5 留存项、§8 确认点、§9.2 决策状态
> 实施流水：`documents/framework/architecture_migration_progress.md`（161 条切片交接记录）

本文件沉淀**分层迁移过程中作出的、影响长期演进的决策**，使这些结论不只留在会话记录或切片流水里（`ARCHITECTURE_TARGET.md` §9.2 末尾要求「后续有明确决策时同步更新本文与对应 ADR」）。

每条 ADR 结构：背景 → 决策 → 依据与证据 → 影响面 → 移除/推翻条件 → 回滚。

---

## ADR-002：端口（Port）按业务域就近定义，不建集中 `src/application/ports/`

- **状态**：已接受（2026-10-30 由本 ADR 成文；实施自 P3 切片起即为该形态）
- **背景**：`ARCHITECTURE_TARGET.md` §2 表述为「端口通常放在 `src.application.ports`」，但那是「通常」而非硬约束。实际搬迁中每个用例簇需要的端口方法面不同（取数 10 方法、渲染 1 方法、遥测 1 方法），集中 barrel 会让 `application/*` 为一个端口的 3 个方法引入 20+ 无关符号，并放大 `patch()` 目标路径。
- **决策**：端口定义落在**所属业务域的 `src/application/<domain>/ports.py`**（或域内专用 `*_ports.py`，如 `analyzer_runtime_ports.py`、`market_data_ports.py`、`llm_ports.py`）；装配落在 `src/bootstrap/<domain>.py` 的 `configure_*()` seam；适配器实现落 `src/infrastructure/`。
- **依据与证据**：实测 `src/application/**/ports.py` 与 `*_ports.py` 共 20 件（`generation`、`agent`、`alert`、`quote`、`notification`、`backtest`、`decision`、`market`、`history`、`intelligence`、`portfolio`、`watchlist`、`usage`、`runtime` 等域各 1–4 件）；`src/bootstrap/` 25 件、31 个 `configure_*` seam；`scripts/check_architecture.py` 的 `src/application/` 规则禁止 `data_provider`/`src.repositories`/`src.infrastructure`，因此端口必须是纯 Protocol、适配器必须在 infra —— 现形态满足。
- **影响面**：新增端口时的默认动作是「在目标域 `ports.py` 追加 Protocol + 同文件 seam 工厂」，不是新建集中包；消费方 import 路径含域名为 patch 目标。
- **移除/推翻条件**：若某端口被 3 个以上域共同消费且语义中立（如通用 KV 存储、时钟），可上收到 `src/domain/shared/` 或新建 `src/application/ports/`；推翻本 ADR 需一次性 re-point 全部 `*_ports.py` import 与测试 patch 串。

---

## ADR-003：`data_provider/` 保留原路径，登记为基础设施例外；新能力适配层落 `src/infrastructure/providers/`

- **状态**：已接受（关闭 `ARCHITECTURE_TARGET.md` §9.2-2）
- **背景**：§9.2 曾把「`data_provider/` 是否实际迁入 `src/infrastructure/providers/`」列为未决。该包 72 个 `.py`、含反向 `import src.*`（实测 18 行），物理迁移需同步 Docker、PyInstaller hidden-import、全仓 import 与测试 patch 面。
- **决策**：**不物理迁移**。`data_provider/` 定位为基础设施适配包并保留顶层路径；依赖倒置通过「应用层只经端口访问 + 守卫禁止 `src/application` → `data_provider`」达成。新增的能力适配层（如 `market_review_provider`、`limit_pool_provider`、`sector_provider`、`stock_data_port` 适配器）落 `src/infrastructure/providers/`，由它包装 `data_provider` 的既有入口。
- **依据与证据**：`ARCHITECTURE_TARGET.md` §4 目标表与 §4.5 留存项表已写明「原位保留」；守卫规则 `src/application/` 禁 `data_provider`、`src/domain/` 禁 `data_provider`；实测 `api/`、`bot/` 对 `data_provider` 的真实 import 为 0。既有 `ADR-001` D2 亦已确认该定位。
- **影响面**：任何人把 `data_provider` 当作「已不存在的旧包」来清理都会失败；文档描述基础设施时需同时提 `data_provider/`（源适配）与 `src/infrastructure/providers/`（端口适配）。
- **移除/推翻条件**：仅当出现明确收益（例如要按数据源做独立部署/依赖裁剪）才重启物理迁移，且需同步 ADR-001、Docker、PyInstaller 与全仓 import 的同步范围评估。
- **回滚**：本决策为「不做某事」，无需回滚。

---

## ADR-004：`src/storage.py` 保留为根级门面（facade），主体不迁四层

- **状态**：已接受（用户批准的例外，而非被遗忘的待办）
- **背景**：`storage.py` 曾承载 1000+ 行的 ORM Base、engine/session、全部业务查询与 schema 兼容升级。P2/P4 已把可分离部分物理下沉：`infrastructure/persistence/{base,session,schema_compat}.py`、`persistence/models/`、`persistence/repositories/`（PP-1~PP-7 清空根 `src/repositories/`）。
- **决策**：`src/storage.py`（现 1049 行）作为 `DatabaseManager` 单例门面**保留原位**：`create_all` + 幂等 `_ensure_*` 薄委托（方法体只做委托，逻辑在 `schema_compat.apply_startup_migrations`），`get_db()`/`get_database_manager()` 归位 `src/bootstrap/database.py`。
- **依据与证据**：`ARCHITECTURE_TARGET.md` §4.5 已登记；progress §1 D3 确认「保留 `create_all` + `_ensure_*` 升级语义」；`tests/test_storage_schema_upgrade.py` 固定「空库」与「存量库升级」双场景，是门面行为的回归锚；实测 `src/storage` 引用面：`src/application/` 22 文件、`src/infrastructure/` 18 文件、`src/bootstrap/` 8 文件、`scripts/check_env.py` 1，`api/`+`bot/` 0（守卫禁入达成）。
- **影响面**：`src.storage` **不在**守卫的 `src/application/` 禁入清单内，因此应用层直连门面不会被拦截 —— 这是有意的过渡期豁免，收敛工作见迁移进度文档 W4.2/W4.3。
- **W4.3 复核结论（2026-10-30，零代码）**：实测 `src/infrastructure` → `src.storage` 共 **18 文件**（`persistence/repositories/` 16 + providers 1 + agent_runtime 1）；storage.py 顶层反向 import 的 repo（`conversation_repo`/`analysis_history_repo`）在自身侧改用函数内懒加载回引 `DatabaseManager`，顶层双向边不共存于同一文件，**无运行时导入环**；但 repo↔门面构成待「`DatabaseManager` 本体迁入 `infrastructure/persistence`」（见下方移除条件）才塌缩的**过渡性双向耦合**，守卫刻意不禁 infra→storage。`src/application` 侧 22 文件的 ad-hoc 直连收敛＝W4.2，经实测需按域拆多切片。
- **W4.2 依赖倒置收敛进展（2026-10-30，真实代码）**：确立并复用「service 内 ad-hoc `self.db`/`get_db()` 直连 → 注入现成 `*RepositoryPort`，bootstrap/调用点用 `DatabaseManager.get_instance()` 或既有真实门面作端口适配器（门面结构性满足 Protocol）」范式；已收敛 **13/22** 文件——① alert 域（`AlertService.self.db` → `HistoryRepositoryPort`，`src/application/alert/` 现 0 storage import，progress §0.154）；② market/`daily_market_context.py`（`DailyMarketContextService.self.db` 单一 `get_analysis_history` → 同一 `HistoryRepositoryPort`，该文件现 0 storage import，progress §0.155）；③ history/`read_model.py`（`HistoryService.self.db` 7 个读方法全命中同一 `HistoryRepositoryPort`，去 `DatabaseManager.get_instance()` 默认、生产 service 按位置传仓储，该文件现 0 storage import，progress §0.156）；④ history/`comparison.py` + `loader.py`（模块级函数 `get_instance()`/`get_db()` 直连沿用 loader 既有模块 seam 范式，各加 `_get_history_repo`/`_get_kline_repo` seam，由 `bootstrap/history.py:configure_history_loader`（main 启动块 + api_lifespan 双入口幂等装配）用 `DatabaseManager` 门面作适配器，两件现 0 storage import，progress §0.157；**history 域整域归零**——成为继 alert 之后第二个整域归零的域）；⑤ runtime/`task_service.py`（`TaskService.get_analysis_history` 方法内 1 处 `get_db()` 只读直连、命中 `HistoryRepositoryPort`，无 `self.db`、无外部调用方、无测试 patch 源符号，沿用模块 seam 范式加 `_get_history_repo` seam + `set_history_repo`，新建 `bootstrap/runtime.py:configure_task_service` 双入口幂等装配 `DatabaseManager` 门面适配器，该文件现 0 storage import，**runtime 域整域归零**——继 alert、history 后第三个整域归零的域，progress §0.158）；⑥ agent/`memory.py`（`AgentMemory.get_stock_history` 函数内懒加载 `get_db` + 1 处只读 `get_analysis_history`、命中 `HistoryRepositoryPort`，且在 try/except 内——seam 未装配时 None→异常→except 吞成 `[]` 优雅降级、比 task_service 更安全；沿用模块 seam 加 `_history_repo` + `set_history_repo`/`_get_history_repo`，由 `bootstrap/agent.py:configure_agent_memory` 双入口幂等装配 `DatabaseManager` 门面，re-point `test_multi_agent.py` 唯一 `@patch("src.storage.get_db")` 消费点→seam getter，该文件现 0 storage import、agent 域 opener 1/8（域未归零、余 7 件多为写/`persist_llm_usage`/`db_factory`），progress §0.159）；⑦ agent/`provider_trace.py`（`persist_provider_trace_turns` 的 `db_factory is None` 回退分支内懒加载 `from src.storage import get_db` 作默认取库工厂、消费方 `chat_executor` 依赖该回退路径；`get_db()` 即返回 `DatabaseManager.get_instance()` 单例、与门面适配器逐字等价——沿用模块 seam 加 `_default_db_factory` + `set_default_db_factory`/`_get_default_db_factory`，回退分支改取 seam，由 `bootstrap/agent.py:configure_provider_trace` 双入口幂等装配 `DatabaseManager.get_instance` 作默认工厂（`chat_executor` 早已依赖该默认，`executor` 于第 8 片亦删除显式 `db_factory=get_db`、改复用默认），片前全仓扫无测试 patch 该回退源符号、补 seam 消费/fail-open/bootstrap 装配 4 处测试，该文件现 0 storage import、agent 域 2/8，progress §0.160）；⑧ agent/`executor.py`（`AgentExecutor._persist_provider_trace` 顶层 `from src.storage import get_db` 唯一用法是把 `db_factory=get_db` 显式传入 `persist_provider_trace_turns`；承接 ⑦ 已装配的默认 db_factory seam（= `DatabaseManager.get_instance`、与 `get_db` 逐字等价）且 `chat_executor` 早已省略 `db_factory` 复用默认，executor 显式传参属冗余 → 删除顶层 storage import 与 `db_factory=get_db` 入参、令其与 chat_executor 一致复用默认 seam，生产经 `configure_provider_trace` 装配后取库对象等价、0 行为变化，bootstrap seam/文件数不变；片前全仓扫 `patch("src.application.agent.executor.get_db")` 仅 `test_agent_executor.py` 1 处、连同真实持久化用例一并 re-point 至 `provider_trace._get_default_db_factory`（`return_value=lambda: db`），该文件现 0 storage import、agent 域 3/8，progress §0.161）；⑨ agent/tools/`search_tools.py` + `data_tools.py`（两件各含模块级 `_get_db()` wrapper `from src.storage import get_db`，分别被 `save_news_intel` 写、`save_daily_data` 写 + `get_analysis_context` 读使用；沿用模块 seam 范式把 wrapper 体改为模块级 `_db_factory` + `set_db_factory()`、`_get_db()` 返回装配工厂产物，由新建 `bootstrap/agent.py:configure_tools_db` 双入口装配 `DatabaseManager.get_instance`；另因 tools 在 `CodexToolProcessRunner` spawn 子进程内执行、不经过进程级 bootstrap，`infrastructure/agent_runtime/codex_tool_process.py:_execute_registered_tool` 在子进程内亦装配两 tools seam（infra→storage/application 守卫允许），补齐无守护读路径 `get_analysis_context` 的取库；两件测试均 patch wrapper `_get_db` 本身、无需 re-point；两件现 0 storage import、agent 域 5/8，progress §0.162）；⑩ agent/`conversation.py`（`ConversationSession` 顶层 `from src.storage import get_db`，仅用于 `add_message → save_conversation_message`（写）与 `get_history → get_conversation_history`（读）两处、无 try/except；两方法在现成 `ConversationRepository` 中签名与默认值（`limit=20`）逐字一致，故新增窄端口 `ConversationMessagePort`（`application/agent/ports.py`）并把会话对象改为模块级 `_conversation_port` seam + `set_conversation_port()`，由新建 `bootstrap/agent.py:configure_agent_conversation()` 双入口以 `ConversationRepository(DatabaseManager.get_instance())` 装配；测试影响面——`test_conversation_manager` / `test_ask_command` 已分别 patch session 方法与整个 manager、不触 seam，2 个真实落库集成用例改在测试内 `patch("...conversation._conversation_port", db)` 接线；该文件现 0 storage import、agent 域 6/8，progress §0.163）。⑪ agent/`chat_context.py`（顶层 `from src.storage import get_db, persist_llm_usage`：3 处读 `get_agent_provider_turns`/`get_conversation_summary`/`get_visible_conversation_messages` + 1 处写 `upsert_conversation_summary`（上下文压缩摘要落库）+ 1 处 `persist_llm_usage`；4 处库操作在现成 `ConversationRepository` 中签名与默认值逐字一致（`inspect.signature` 实测）→ 新增窄端口 `ChatContextPort`（读 3 + 写 1），与 ⑩ 的 `ConversationMessagePort` 由同一仓储对象同时满足，故复用 `bootstrap/agent.py:configure_agent_conversation()` 一并装配、bootstrap 件数与 `configure_*` seam 数不变；`persist_llm_usage` 不为 application 开写通道，而是把既有 `UsageTelemetryPort` 由「只判定」扩为「判定 + 写入」（新增 `persist()`），infra `UsageTelemetryAdapter.persist` 委托 `src.storage`，chat_context 改调 `_usage_telemetry_port.persist(...)`——`configure_usage_telemetry` 已装配同一适配器实例、写侧随对象自动可用；**踩坑（端口声明落后于真实调用点）**：首版端口命名 `ChatContextReadPort` 且只声明 3 个读方法，而同一端口对象实际还写 `upsert_conversation_summary` → 契约漂移，改名 `ChatContextPort` 补写侧方法，并新增参数化用例以 `inspect.signature` 逐方法比对 Protocol 与 `ConversationRepository` 的参数 name/kind/default（忽略注解），把「端口声明必须覆盖全部真实调用点」固化为回归守卫；测试侧 `test_chat_context._reset_db()` 与两处落库集成接线由传 `DatabaseManager` 裸实例改传 `ConversationRepository(db)`（与生产同一适配器、不绕过真实仓储），两条 orchestrator 落库用例改 patch `orchestrator.build_visible_chat_history`；该文件现 0 storage import、agent 域 7/8，progress §0.164）。余 9 文件（含 market/market_review 写路径需新端口、decision 5 件需新增仓储端口、agent 余 1（runner `persist_llm_usage` 单点）与 analysis 2 件的 `get_db`/`persist_llm_usage` 等）待按域推进，全部收敛后再把 `src.storage` 加入 application 禁入清单。
- **移除/推翻条件（= 删除门面的前置）**：`src/application/` 22 个文件与 `src/infrastructure/` 18 个文件全部改走仓储端口/会话工厂后，把 `DatabaseManager` 本体迁入 `infrastructure/persistence/`，并同步桌面/Docker 打包与 `scripts/ci_gate.sh` 名单。
- **回滚**：门面是「下沉的剩余物」，如需回滚只能整簇（storage 本体 + persistence 拆分件 + re-point）一起回。

---

## ADR-005：`src/auth.py` 保留原位（落法 A），认证端口化推迟到有安全基线之后

- **状态**：已接受（D-06 用户批准的默认落法 A）
- **背景**：`src/auth.py`（500 行）提供会话/Cookie/口令哈希等能力，被 `api/` 与 `webui` 链路消费。把它端口化需要引入 `AuthPort` + `infrastructure/security/` 落点（选项 B），但 `ARCHITECTURE_TARGET.md` §9.2-5 要求「认证、Cookie、CORS 与修改类请求防护、性能/启动时间基线须在相关切片开始前记录」，该基线尚未建立。
- **决策**：**保留原位、不端口化、不改行为**。它属于「驱动中立但耦合 HTTP 语义」的遗留例外，与 `storage.py` 同类处理。
- **依据与证据**：§4.5 留存项表实测 4 个根级文件之一；`.claude/reviews/pending-decisions-2026-10-28.md` D-06；T5e 系列把「auth endpoint 层 gate」作为切片前置条件的记录。
- **影响面**：`api/` 直连 `src.auth` 合法（守卫 `api/` 规则只禁 `src.storage`/`src.repositories`/`src.infrastructure`/`data_provider`）。
- **移除/推翻条件**：先补 §9.2-5 的认证/CORS 防护清单与性能基线，再按 ADR-002 模式在 `src/application/<域>/ports.py` 定 `AuthPort`，实现落 `src/infrastructure/security/`（该目录当前不存在）。
- **回滚**：无代码改动，无需回滚。

---

## ADR-006：`src/services/__init__.py` 保留为惰性兼容面；旧目录守卫规则作为 tombstone 保留

- **状态**：已接受（本批复核后成文，关闭「删除还是保留」的悬置项）
- **背景**：T 线收官后 `src/services/` 仅剩 `__init__.py`，其 `__getattr__` 惰性映射唯一符号 `get_task_service` → `src.application.runtime.task_service`。`p0-file-inventory.md §5.2` 与 `decisions-2026-10-28-r2a.md` 曾记「保留为兼容面（0 生产调用方，删除属对外契约变更）」，但迁移进度视图里又一度把「删除」列为待办。
- **决策**：两条并存保留。① **兼容面保留**：删除需同时修改 `scripts/build-backend-macos.sh:94` 与 `scripts/build-backend.ps1:110` 的 PyInstaller `--hidden-import` 列表并跑桌面端打包验证，属高风险启动链路，不在纯收口批次内做。② **tombstone 规则保留**：`scripts/check_architecture.py` 中 `src/services/`、`src/core/` 两条规则即使目录归零也不删，使旧路径复活即刻变红。
- **依据与证据**：实测 `get_task_service` 生产调用 0（`bot/commands/analyze.py:81` 直接 import 新路径）；外部面（`api/`、`bot/`、`main.py`、`server.py`、`webui.py`、`scripts/`、`docker/`、`.github/`）对 `src.services`/`src.core`/`src.agent`/`src.schemas` 的引用仅存在于守卫脚本自身（禁入清单与注释）；`tests/test_check_architecture.py` 用合成工作区自测、不断言 `RULES` 列表内容，因此保留规则不造成测试双源。
- **影响面**：`src/core` 可作为 PEP 420 空命名空间包被解析（无属性、子模块 `ModuleNotFoundError`），不构成行为风险；文档中「旧目录已归零」指 tracked 源文件层面，`__pycache__` 为 git-ignored 本地产物。
- **移除/推翻条件**：兼容面可在任一 PR 中删除，条件是同时改两处打包脚本并附桌面端打包验证证据；tombstone 规则在确认「外部不再以旧路径引用」且无复活风险满一个版本周期后方可撤。
- **回滚**：如需恢复兼容面，重新新增 `src/services/__init__.py` 的 `__getattr__` 映射即可，不影响已下沉实现。

---

## ADR-007：领域层纯规则与用例编排的拆分口径；`src/domain` 禁入 `src.application`

- **状态**：已接受（第 3 批 W4.1 实施同步成文）
- **背景**：`scripts/check_architecture.py` 原存在两处守卫盲区——① `src/config/` 无专入规则（落 `src/` 兜底、仅禁 `api.`/`bot.`），使 §0.118 的 `config → application` 反向边不触守卫；② `src/domain/` 禁入清单不含 `src.application`，使下沉领域的纯规则可被用例层反向重新耦合。同时 `config` 对 `application` 存在 4 条真实依赖（`registry.py:18` 的 `NOTIFICATION_SEVERITIES`、`settings.py:44` 的 noise 纯规则、`:54` 的 `split_stock_list`、`:55` 的 generation catalog 常量）。
- **决策**：① **拆分口径**——无 IO 且不含业务状态机的“纯词表/解析/校验/身份常量”下沉领域层（复用 R2-A3 `local_cli_policy.py` 先例），需进程态的 dedup/cooldown 状态机、需 `GenerationError` 的解析策略留在 `src.application`；采取**物理下沉 + 全量 re-point、不留隐式 re-export**（非加 baseline 豁免），使 `src/config` 彻底只依赖 `src/domain`。② **守卫收紧**——将 `src.application` 加入 `src/domain/` 禁入清单，固化领域不反向依赖用例层的不变量。
- **依据与证据**：3 件新落点（`domain/market/stock_list_parser`、`domain/notification/noise_rules`、`domain/generation/backend_identity`）的等价性经 AST 逐字节 / 值+类型取证；`hasattr(noise,'NOTIFICATION_SEVERITIES')==False` 排除双入口；守卫 `--check` 收紧后 RC=0、全量离线 31f/5537p/4deselected/10e 与基线逐数字一致。
- **影响面**：本口径仅适用于“领域纯件”；CSV 解析、HTTP DTO、模板渲染等不会仅因“纯函数”而进 domain（AT §2 L41）。`src/config/` 专入守卫规则（W4.5）与 `src.storage` 加入 application 禁入清单（W4.2）仍为待办，不在本 ADR 范围。
- **推翻条件**：若未来确定采用完整 DI/集中端口层（推翻 ADR-002 就近放置），本拆分口径需重新评估。
- **回滚**：删 3 个新 domain 件 + 逆向还原 noise.py/catalog.py 头尾 + 逆向 re-point + 撤销 `check_architecture.py` 的 `src.application` 条目，或用 `~/hermesx_b3_pre_20261030_142531.tar.gz` 快照整体复原。

---

## 附：与 `ARCHITECTURE_TARGET.md` 的对应关系

| ADR | 关闭/支撑的条款 |
| --- | --- |
| ADR-002 | §2 端口位置表述「通常」的具体化 |
| ADR-003 | §8 确认点 2、§9.2-2 |
| ADR-004 | §4.3 storage 行、§5.1、§9.2-1 的实施前提 |
| ADR-005 | §9.2-5（认证基线未建 → 不动） |
| ADR-006 | §6 P5「清理确无引用的旧模块」与「收紧 import 守卫」的取舍结论 |
| ADR-007 | §2 L41 domain 依赖方向、§9.2-4 进程模型已决的领域层落地口径 |
