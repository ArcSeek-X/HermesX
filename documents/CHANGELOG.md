# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> For user-friendly release highlights, see the [GitHub Releases](https://github.com/ArcSeek-X/HermesX/releases) page.

## [Unreleased]
- [文档] 架构迁移文档归档：将 `ARCHITECTURE_TARGET.md`（原仓库根）、`documents/framework/architecture_migration_progress.md`、`documents/framework/src_migration_index.md` 三份统一迁入 `documents/framework/refactoring/`（`git mv` 保留历史）。同步更新“活指针”的仓库根相对路径引用：源码 docstring 3 处（`src/application/generation/__init__.py`、`src/domain/notification/__init__.py`、`src/domain/generation/__init__.py`）、`documents/framework/architecture_migration_adr.md`、`ARCHITECTURE_MIGRATION_STATUS.md`、`MIGRATION_COMMIT_PLAN.md`、以及 `ARCHITECTURE_TARGET.md` 自身对另两份文件的引用。CHANGELOG 历史条目、progress 台账内部历史叙述（“只追加不改写”）、未入库的 `.claude/reviews/` 产物、`MIGRATION_COMMIT_PLAN.md` 对 C1 提交内容的历史描述均按“历史记录保真”原则保留旧路径不改。经全仓核对：无任何代码按路径读取这三份文件、无 Markdown 相对链接指向它们，故零运行时/CI 断链风险；`check_architecture.py --check` RC=0、`check_ai_assets.py` RC=0、三个 src 文件 py_compile OK。Docs only，守卫与治理脚本已复跑，全量 pytest 未重跑。
- [文档] 架构迁移台账改名：将 `documents/framework/refactoring/architecture_migration_progress.md` 重命名为全大写 `ARCHITECTURE_MIGRATION_PROGRESS.md`（与同目录 `ARCHITECTURE_MIGRATION_STATUS.md` 命名一致），`git mv` 两步法绕过 macOS 大小写不敏感文件系统以保留历史。同步把 8 处嵌目录路径的“活指针”改为大写：源码 docstring 3 处（`src/application/generation/__init__.py`、`src/domain/notification/__init__.py`、`src/domain/generation/__init__.py`）、`documents/framework/architecture_migration_adr.md`、`ARCHITECTURE_MIGRATION_STATUS.md`、`MIGRATION_COMMIT_PLAN.md`、`ARCHITECTURE_TARGET.md` 自身、以及本条 CHANGELOG 的 W14 条目锚点。CHANGELOG 历史条目与台账内部历史叙述按“历史记录保真”保留原小写文件名不改（仅为散文提及，非功能路径）。经全仓核对：无任何代码/测试按路径读取该文件、无 Markdown 相对链接指向它，故大小写敏感 Linux CI 零断链风险；`check_architecture.py --check` RC=0、`check_ai_assets.py` RC=0、三个 src 文件 py_compile OK。Docs only，全量 pytest 未重跑。
- [chore] 架构迁移**W14：将 915 项工作树变更按方案切为 9 笔已入库提交**（基线 `fe7410bb` → `7a97cd32`，逐笔 hash：`4a315ae1` docs / `cec61271` domain / `17b70b72` config / `20fb0c9b` infrastructure / `b5014fa2` application / `10e5a139` bootstrap / `8e43c72b` 驱动+测试 / `f8971664` 删 legacy / `7a97cd32` 守卫与工具链）。**终态验证**：`PATH=$PWD/.venv/bin:$PATH ./scripts/ci_gate.sh all` 全部阶段通过 → **5713 passed / 4 deselected / 511 subtests passed（259.96s）**，守卫 `check_architecture.py --check` RC=0（baseline `entries: []`，零豁免债务）、严格 flake8 `E9,F63,F7,F82` RC=0、`test.sh code`+`yfinance` 全过；旧布局的 196 个 legacy 文件已全删，`src/services/__init__.py`（仅余 `get_task_service` 惰性映射）与 `src/storage.py`/`src/auth.py`/`src/webui_frontend.py` 按既定例外保留。**逐笔独立验证（`git worktree`）**：C8 删 legacy 后 **5674 passed / 4 skipped / 0 failed（322.42s）**，删除前的全仓引用扫描实测生产/驱动/测试真实 import 为 0（仅剩 6 个“禁止出现”断言与守卫测试的临时目录构造）。⚠️ **已知不完美（已拍板接受，详见方案 §7）**：C1–C6 为语义完整的中间态但**非 test-green**（C2 约 122 条红、C1 约 15 条文档路径断言红，均由 C7 的测试适配修复）；C7/C8 的测试直接 import C9 的 4 件工具链文件，单独 checkout 不拷入则无法收集 → **本序列提供“语义完整”而非“逐笔可跑”的 bisect，真实可运行基线从 C9 开始**；本轮未执行任何 `git push`/`git tag`/建 PR（推送由维护者手动完成）。同时按方案 §4 已定项补 `setup.cfg` 的 `[tool:pytest] testpaths = tests`（原为 `.`，使本地裸跑 `pytest` 会被 gitignored 的 `vibe-template/zentrade/backend/tests` conftest `ModuleNotFoundError: No module named 'app'` 中断；改为 `tests` 后实测收集 **5717 items**、7.40s 无错误；CI 侧 `ci_gate.sh offline-tests` 亦不再收集 `apps/hrs-web/scripts/test_wt/*` 两个已跟踪但自 `fd862ba3`（2026-08-09）起就恒为 collection error（`fixture 'client' not found` ×10）的脚本样本，旧配置下模拟实测为 5727 items / 10 errors），`build的问题清单.md` 按既定不入库。详见 `documents/framework/refactoring/MIGRATION_COMMIT_PLAN.md` §0/§5/§7 与流水台账 `documents/framework/refactoring/ARCHITECTURE_MIGRATION_PROGRESS.md` §0.174。
- [文档] 新增 `documents/framework/refactoring/MIGRATION_COMMIT_PLAN.md`（W14 分步提交方案，**已按该方案逐笔执行完毕**，执行结果与偏离见当文 §7）：将当前 916 项工作树变更（423 新增 / 297 修改 / 196 删除）切为 9 笔有序提交（**入库 915 项**，`build的问题清单.md` 已定排除），逐笔给出范围、中英文 commit message、验证命令与暂存命令；执行章节按「暂存 → 验证 → 提交」逐笔展开，**每段自带完整英文 message 的 `git commit -F -` heredoc**（已脚本校验与 §1 的英文块逐字一致，且与 9 笔**已提交正文**逐字一致）。切分顺序由五项实测约束决定：最终态全量 **5713 passed / 4 deselected** 且守卫 `--check` **0 违规 RC=0**；仅切驱动不切测试 → **57 个 collection error**（因此 C7 不可拆）；切驱动+切测试但保留 legacy → **5714 passed / 3 skipped**（因此删 legacy 可独立成笔）；旧布局上用空 baseline 跑守卫 → **15 条违规**（因此守卫与 CI gate 必须收尾）；**E-5**：`src/config` 硬依赖 `src.domain`（12 处）→ domain 必须先于 config 入库。**E-6**：C7/C8 的测试依赖 C9 的 4 件工具链文件 → 中间笔不可独立收集。另记录三项待拍板结论：~~兼容面与文档口径冲突~~（执行前复核为**本条误读**：`ARCHITECTURE_TARGET.md` 无 §6.1，`src/services/__init__.py` 与 `src/storage.py` 已在 §4.5 留存项登记表连同 ADR-004/006 移除前置条件中逐条登记，无需改动）、`build的问题清单.md` 是否入库（已定：排除）、仓库无 `testpaths` 导致裸跑 `pytest` 会被 `vibe-template/` 中断（已定：随 C9 的 `setup.cfg` 补上）。
- [修复] 修复**资讯抓取将模块级代理常量按引用交给 `requests` 而被就地污染**（`src/application/intelligence/intelligence_service.py`，W13 既有失败清零片）：`_get_with_validated_dns` 原先 `request_kwargs.setdefault("proxies", _DISABLE_REQUEST_PROXIES)` 传入的是常量对象本身，而 `requests` 在 `trust_env` 路径（`sessions.merge_environment_settings`）会对调用方传入的 proxies 做 `proxies.setdefault(k, v)` **就地写入**环境探测结果（本机系统代理会注入 `'use': 'false'`），使该常量一旦被真实请求经过就永久变形——「非受信任源显式禁用代理、防止代理侧绕过 SSRF 判定」的边界随之失真，且表现为跨测试的顺序依赖串扰。改为传入副本 `dict(_DISABLE_REQUEST_PROXIES)`（全仓仅此一处引用外泄）。新增回归测试 `test_fetch_passes_proxy_dict_copy_not_the_shared_constant`：模拟 `requests` 的就地写入并断言常量保持 `{"http": None, "https": None}`、每次调用拿到的都是新副本；已**反向验证**（临时回退生产修复 → 该测试失败）。用户可见行为不变（禁用代理的语义更确定）。
- [测试] 架构迁移 **W13：W12 遗留的 5 条既有失败全部清零**（离线基线 **5 failed / 5707 passed → 0 failed / 5713 passed / 4 deselected（250.86s）**，随机序另跑 3 轮定向 + 1 轮全量复核）：① `requirements.txt:2` 中文注释与 `test_check_env_encoding` 的 ASCII 可解码断言契约冲突 → **按测试契约把该行注释改为 ASCII 英文**（保留原语义；该断言保护的是非 UTF-8 locale 下 `pip install -r` 的读取安全，属有效约束，不放宽测试）；② `test_fundamental_context::test_sector_rankings_use_ordered_fallback` 原依赖上游真实网络返回（东财失败→新浪兜底返回真实行业名）→ 让 `data_provider/sector` provider 层确定性失败，真正按用例意图验证注入 fetchers 的优先级回退顺序；③④ `test_yfinance_fundamental_adapter` 2 条 `ttm_event_count` 随日期漂移（生产 TTM 窗口 `pd.Timestamp.now() - 365d` 语义正确，是 fixture 用了绝对日期）→ 新增 `_ttm_quarterly_dividend_index()` 按「今天」相对生成 4 个季度除息日，`events[0]` 期望值同源自计算；⑤ `test_intelligence_service::test_fetch_enabled_sources_is_fail_open` 顺序依赖 → 根因即上一条 `[修复]` 的常量污染，生产修复后自然转绿（不改测试）。新增 1 条回归用例，其余改动均在测试/注释层，未触及分层契约；详见 `documents/framework/architecture_migration_progress.md` §0.173。
- [修复] 架构迁移**第 5 批收官后 W12 提交前审计：清零 2 处既有缺陷**（零提交，HEAD `fe7410bb` 未变）：① `src/application/runtime/scheduler.py` 的 `Scheduler._refresh_daily_schedule_if_needed` 在 178/232 行**重复定义**，Python 类体内后定义静默覆盖前定义，导致 178 版（单时间点刷新）为永远不可能执行的死代码——已删除，**运行时行为零变化**（本来就只可能走 232 版）；② `tests/test_tencent_stock_info_source.py:32` 的样例构造受运算符优先级影响（`.encode("gbk")` 只作用于末段字面量）而产生 `can only concatenate str (not "bytes") to str`——补括号修正，**生产件 `data_provider/stock_info/tencent_source.py` 本身正确**（推翻了 W9 片将其记为生产缺陷的归因）。全量离线基线 **6 failed / 5706 passed → 5 failed / 5707 passed / 4 deselected（257.22s）**；余 5 条既有失败逐条归因后**不擅自改绿**（`requirements.txt` 中文注释↔ASCII 断言契约冲突、`fundamental_context` 依赖上游真实返回、yfinance 2 条 TTM 窗口漂移、`intelligence_service` 跨测试全局状态串扰）。架构面同时现场复核全部成立（旧目录 / 行首锚定旧 import / 非 py 层残留 / application与config 禁入边均实测 **0**），守卫 `--check` RC=0、严格 flake8 RC=0、定向 **12 passed**；详见 `documents/framework/architecture_migration_progress.md` §0.172。
- [改进] 架构迁移**第 5 批 W5：§4.3 七项大件拆分全部落地**（真实代码改动、零提交，HEAD `fe7410bb` 未变）：按「纯规则/声明数据下沉 domain + 编排留 application」口径拆分——`analyzer.py` 4849→**4379**（`domain/analysis/chip_rules` + `prompt_sanitizer`）、`pipeline.py` 3947→**3732**（`domain/analysis/pipeline_rules` 334 行）、`src/config/registry.py` 6954→**372** 且 `src/config/settings.py` 3802→**3254**（`src/config/field_definitions` 5457 / `field_help` 1157 / `env_parsers` 273 / `env_file` 289 / `llm_channels` 279）、`system_config_service.py` 5242→**4328**（`llm_config_validation` 972）、`image_stock_extractor` 收敛为 330 行用例 + `VisionCompletionPort`（68）+ `LitellmVisionAdapter`（73）+ bootstrap seam（`configure_*` 32→**33**，bootstrap 文件数 25 不变）、`notification.py` 3063→**2863**（`domain/notification/rendering` 325）、新建 `domain/portfolio/risk_rules`（139）。行为零回归：新增 7 个 domain/端口回归测试文件，定向 **103 passed**，全量离线 passed 5577→5706。D3 50% → **75%**；详见 `documents/framework/architecture_migration_progress.md` §0.171。
- [改进] 架构迁移**第 5 批 W6：schema 演进决策收口**（零代码风险、零提交）：实测确认现状为 `Base.metadata.create_all()` + 幂等 `apply_startup_migrations`，**不引入 Alembic/版本化迁移框架**——会形成平行装配实现，且桌面端 SQLite 无迁移编排入口。改为用 AST 守卫锁装配契约：新增 `tests/test_schema_migration_guard.py`（每个 `ensure_*`/`backfill_*` 必须自 `apply_startup_migrations` 可达、有依赖顺序的迁移保持先后、首参恒为 `db_session`）。决策与推翻条件写入 `documents/framework/architecture_migration_adr.md` **ADR-008**，`ARCHITECTURE_TARGET.md` §9.2-1 转「已决」。D5 85% → **100%**。
- [改进] 架构迁移**第 5 批 W7：安全不变量与性能基线成文**（取证 + 新增守卫测试，零提交）：取证 `src/auth.py`（32B secret + `0600`、`pbkdf2_hmac` + `hmac.compare_digest`、`nonce.ts.sig` 三段式过期、`XFF` 取最右值、5 次/300s 限流）、`_cookie_params`（`httponly`/`samesite=lax`/HTTPS 下 `secure`）、`api/middlewares/auth.py`（8 条精确白名单）、`api/app.py` CORS（默认 4 源 + `credentials=True`；`CORS_ALLOW_ALL` 时 `["*"]` 且 `credentials=False`，二者互斥），固化为 `tests/test_security_baseline.py` **15 条**；**决策**：`src/auth.py` 维持 ADR-005 落法 A（不端口化，无「可替换驱动」），重评条件＝多用户/OAuth、跨进程会话、部署单元拆分。新增可复跑脚本 `scripts/measure_performance_baseline.py`（隔离子进程 + 临时库 + 抑制调度启动），实测 `import api.app` 1427–1480ms／lifespan 4421–4547ms（32 表）／`create_app()` 0.88–0.94ms／OpenAPI 153 paths 首次 637–658ms／健康与状态接口 p95 ≤2.63ms；阈值（import ≤3000ms、lifespan ≤10000ms、create_app ≤50ms、openapi ≤2000ms、接口 p95 ≤20ms、搜索 20/100/200ms）与未覆盖项写入 `documents/framework/security_performance_baseline.md`。D5 同步转 **100%**。
- [修复] 修复**资讯源模板路由单复数不一致**与**告警实时行情端口异常未收敛**（真实代码缺陷、零提交）：① `api/v1/endpoints/intelligence.py` 装饰器写 `/sources/template/{template_id}`（单数），而 `docs/intelligence-sources.md`、endpoint docstring 与全部测试均用复数 → 统一改为 `/sources/templates/{template_id}`；② `data_provider/realtime` 能力层在「全部数据源失败」时抛 `LookupError`，而适配器 `src/infrastructure/providers/alert_realtime_quote.py` 未捕获，违反 `RealtimeQuotePort` 文档「无有效数据返回 `None`」契约 → 捕获后记汇总日志并返回 `None`（与旧 `DataFetcherManager` 降级行为一致），避免告警侧静默无数据。
- [测试] 架构迁移**第 5 批 W9：文档与测试旧路径漂移清零**（零运行时行为改动、零提交）：`docs/*.md` 与 `AGENTS.md` 中 18 处指向已删除旧目录（`src/{core,schemas,agent,llm,repositories,notification_sender}/`）的具体文件路径全部改指五层新落点，仅保留 1 处刻意保留的历史叙述；`tests/test_alerts_docs.py` 对 `alerts.md` 锚点式标题的裸 token 断言改为锚点感知，8 条既有失败归零（`19 passed`）。另修好 14 条同类漂移/环境类失败：搜索性能与 bot dispatcher 改注已下线的 `_get_akshare_name_to_code` → 改走 `_code_search_port` seam、文档锚点断言改新路径、资讯/用量接口按既有约定 patch `is_auth_enabled` 并显式调用 `configure_intelligence_repository()`、`setup.cfg` 注册 `benchmark` marker。全量离线 **6 failed / 5706 passed / 4 deselected（268.91s）**，剩余 6 条均为既有失败并逐条归因（`requirements.txt` 中文注释、真实网络兜底断言、跨测试全局状态串扰、腾讯兜底用例、yfinance TTM 窗口随日期漂移）；其中腾讯兜底用例原记为 `tencent_source` 的 `str + bytes` **生产缺陷**，已由 W12 审计更正为**测试 helper 缺陷**并修好。
- [改进] 架构迁移**第 4 批 W4.5：`src/config` 5 条外层边全部物理收敛 + 新增 `src/config/` 专入守卫（config 只依赖 domain、第 4 批收官）**（真实代码改动、零提交，HEAD `fe7410bb` 未变）：实测 `src/config`（4 件）外层边共 5 条——① `settings.py` 模块级 `from src.infrastructure.generation import generation_params`；②③ `settings.py` 函数体内懒加载 `llm_adapter`（thinking `extra_body` / fallback wire models）；④⑤ 两处 `from data_provider.base import normalize_stock_code`。按 AT §2「`src/config` 只依赖 domain」执行**物理收敛（不用 baseline 豁免）**：① 别名→wire model 的纯列表解析（`find_model_list_entries` / `find_model_list_entry` / `resolve_litellm_wire_model`）逐字下沉新建 `src/domain/generation/wire_models.py`（无厂商表、零 IO），`generation_params` 删原 3 函数、改同名 re-import（运行时 `is` 同一函数、单一实现），`application/agent/provider_trace.py` 改直连 domain——同时闭合 W10.1「同名双入口」（原记录真源 `infrastructure/agent_runtime/generation_params.py` 实测不存在）；② 厂商参数规则不下沉 domain（`domain/generation` 只放与厂商无关纯规则）：既有 `GenerationRuntimePort` 新增 `thinking_extra_body(model)` 与 `resolve_fallback_wire_models(model, model_list)`，infra `GenerationRuntimeAdapter` 两方法内延迟 import `llm_adapter`，`analyzer` 两处调用改经端口（与同函数内既有 `apply_params`/`completion_with_recovery` 一致、**零新装配点**）；③ `normalize_stock_code` 改由 `src.domain.market.stock_codes` 取（`data_provider/base.py:34` 本就是 re-export，零语义变化）；④ 删 `src/config` 6 个薄委托（wire model/thinking/fallback/固定温度×2/温度归一）与 `config/__init__.py` 同名 re-export，唯一外部消费者 `tests/test_llm_channel_config.py` 改直连 infra `generation_params`。**守卫**：`scripts/check_architecture.py` 新增 `src/config/` 专入规则（禁 `fastapi`/`sqlalchemy`/`data_provider`/`src.services`/`src.core`/`src.repositories`/`src.infrastructure`/`src.storage`/`src.application`/`api.`/`bot.`；`src.utils` 作为遗留共享 helper 保持允许），`--check` RC=0、`scan()` 实测 `src/config` 违规 **0**，规则自测对 infra/data_provider/application 命中、对 domain/utils 放行；运行时取证：`import src.config` 后 `sys.modules` 中 infra/application/services/core/repositories/storage/data_provider/fastapi/sqlalchemy/api./bot. 前缀模块 **0 个**。适配器功能实测 `thinking_extra_body('deepseek-chat')→{'thinking':{'type':'enabled'}}`、`'gpt-4o'→None`、`resolve_fallback_wire_models('kimi_router', ml)→['openai/moonshot/kimi-k2.6']`、`domain.resolve_litellm_wire_model is infra.resolve_litellm_wire_model→True`。验证：py_compile 10 件 OK、守卫 RC=0、严格 flake8 `E9,F63,F7,F82` RC=0、定向簇 10 文件 **587 passed**（llm_channel / llm_param_recovery / provider_trace / llm_adapter_provider_trace / market_analyzer_generate_text / system_config_service / system_config_api / generation_backend / generation_backend_status_service / agent_pipeline）、**全量离线 `--continue-on-collection-errors` 31 failed / 5577 passed / 4 deselected / 11 errors（253.86s）——passed 与上片持平（本片不增用例），FAILED 集合归一后与基线 `diff` 为空 → IDENTICAL，0 新增回归**；ERROR 11 条仍全为既有三处（`apps/hrs-web/scripts/test_wt/*`、`vibe-template/zentrade/backend/tests`）。快照（sha256+readlink，**3696→3697**）逐条比对：ADDED 1（`src/domain/generation/wire_models.py`）/ REMOVED 0 / MODIFIED 22（**9 个目标代码与测试文件**：`provider_trace.py`、`analyzer.py`、`runtime_ports.py`、`config/__init__.py`、`config/settings.py`、`port_runtime.py`、`generation_params.py`、`test_llm_channel_config.py`、`check_architecture.py` + **4 份文档** + **9 条运行时噪声**：data 3／logs 2／vibe-template 4），无越界源码改动。回写 STATUS（W4.5 ⏳→✅、W4 段收官、W10.1 闭环、切片 173→174、`src/` py 379→382、domain 59→60；D2 保持 88.00、综合保持 83.85%）、ADR-004 补 ⑰ 与 progress §0.170。
- [改进] 架构迁移**第 4 批 W4.2 第 16 片：analysis/pipeline 持久化端口化，**W4.2 收官（22/22 文件 0 storage 直连）、`src.storage` 入 application 禁入清单**（真实代码改动、零提交，HEAD `fe7410bb` 未变）：`application/analysis/pipeline.py` 构造期 `self.db = get_db()` 的消费面覆盖 9 个方法 / 16 处调用 → 新增 `AnalysisPipelinePersistencePort`（`application/analysis/persistence_port.py`，10 方法；`get_analysis_history` 单列供 `DailyMarketContextService` 复用）＋ infra `DatabaseManagerPipelinePersistenceAdapter` 逐方法委托宿主公开面（宿主已是仓储薄委托，且 `analyze_ma_status` 仅存于宿主公开面，另行拼装会造成判定口径漂移）＋ 新增 `bootstrap/analysis.py:configure_analysis_pipeline_persistence()`（注册适配器类、每管线现建句柄、对 `DatabaseManager.reset_instance()` 敏感），在 CLI／`api_lifecycle`／测试 conftest 三入口与取数端口同批装配（**bootstrap 25 件不变、`configure_*` seam 31→32**）。`SkillOpinionSampleService` 由 `db_manager=self.db` 改 `repo=get_skill_opinion_sample_repository()`（宿主 `get_session` 契约不向端口泄漏）；`DailyMarketContextService(history_repo=self.db)` 由端口对象直接满足。测试：17 处 `pipeline.get_db` patch 目标 re-point、1 处构造断言改 `repo`，新增 `tests/test_pipeline_persistence_port.py` 6 条回归（逐方法委托/kwargs、`isinstance`、三方参数面一致、未装配显式报错、工厂不缓存、源码 0 storage）。**守卫收口**：`src/application/` 禁入清单加入 `src.storage`，`--check` 0 违规。验证：py_compile 10 件 OK、守卫 RC=0、严格 flake8 `E9,F63,F7,F82` RC=0、pipeline 相关簇 **355 passed**、**全量离线 31 failed / 5577 passed / 4 deselected / 11 errors（257.04s）——passed 5571→5577（+6）、FAILED 集合归一后与基线 `diff` 为空 → IDENTICAL，0 新增回归**。快照 3693→3694（ADDED 1 = 新测试文件、REMOVED 0、MODIFIED 12 目标 + 运行时噪声）。回写 STATUS（W4.2 **22/22** 余 0、D2 87.73→**88.00**、综合 83.80→**83.85%**、切片 172→173、seam 31→32）与 ADR-004 补 ⑯；详见 progress §0.169。
- [改进] 架构迁移**第 4 批 W4.2 第 15 片：market/market_review 复盘历史落库改走 `MarketReviewHistoryPort`，market 域 storage 直连归零 2/2**（真实代码改动、零提交，HEAD `fe7410bb` 未变）：`application/market/market_review.py` 仅两处函数内 `from src.storage import DatabaseManager`——`_persist_market_review_history`（`db.save_analysis_history(...)`）与 `_refresh_market_review_history_diagnostics`（`getattr(db, "update_analysis_history_diagnostics", None)`），两者在现成 `AnalysisHistoryRepository` 中签名与默认值逐字一致 → 新增窄端口 `MarketReviewHistoryPort`（`application/market/ports.py`，2 方法逐项对齐）＋模块级 `_default_history_repo_factory` seam（`set_default_history_repo_factory` / `_get_history_repo`），由既有 `bootstrap/market.py:configure_market_review`（main + api_lifespan 双入口已在）追加注册 `lambda: AnalysisHistoryRepository(DatabaseManager.get_instance())`——注册**工厂**而非实例，仓储每次写历史时按当前单例现建，对 `DatabaseManager.reset_instance()` 保持敏感（**bootstrap 25 件 / 31 seam 不变**）；未装配时保存路径沿用原 fail-open 语义（`record_history_run(report_saved=False)` + warning + 返回 0）、诊断回写静默跳过。测试：`test_market_review.py` 3 个真实落库用例在 `setUp` 注册同域仓储工厂、`tearDown` 复位；`test_run_flow.py` 的 fake-db 用例由 `patch("src.storage.DatabaseManager.get_instance")` re-point 为 `patch.object(market_review_module, "_get_history_repo")`；另补 `TestMarketReviewHistoryPort` 3 条回归（未装配降级、端口/仓储签名对齐、源码 0 storage）。验证：py_compile 5 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` RC=0、application 行首锚定 storage import 由 **2 文件/3 行降至 1 文件/1 行**（仅余 `analysis/pipeline.py`）、market/bootstrap/run_flow 簇 **213 passed**、**全量离线 `--continue-on-collection-errors` 31 failed / 5571 passed / 4 deselected / 11 errors（253.86s）——passed 5568→5571（+3 新用例）、FAILED 集合归一后与基线 `diff` 为空 → IDENTICAL，0 新增回归**。快照（sha256 + readlink，3693→3693）逐条比对：ADDED 0 / REMOVED 0 / MODIFIED 16（5 个目标文件 + 11 条运行时噪声），无越界源码改动。回写 STATUS（W4.2 **21/22** 余 1、D2 87.45→**87.73**、综合 83.74→**83.80%**、切片 171→172）与 ADR-004 补 ⑮；详见 progress §0.168。
- [改进] 架构迁移**第 4 批 W4.2 第 14 片：analysis/analyzer 用量遥测写侧改走 `GenerationUsagePort.persist`，analysis 域 1/2 收敛**（真实代码改动、零提交，HEAD `fe7410bb` 未变）：`application/analysis/analyzer.py` 的 storage 直连只有 `from src.storage import persist_llm_usage` 及两处调用（`call_type="market_review"`、`call_type="analysis"` + `stock_code=code`），均在既有 `should_persist` 守卫之后；因该文件在 D-01 / R2-A3 阶段已有 `_generation_usage_port` seam，本片采**端口扩容 + 消费者追平**：`GenerationUsagePort`（`application/generation/runtime_ports.py`）由「只判定」扩为「判定 + 写入」，新增 `persist(usage, model, *, call_type, stock_code=None)`，infra 侧 `GenerationUsageAdapter.persist`（`infrastructure/generation/adapters/port_usage.py`）委托 `src.storage.persist_llm_usage` 并逐字透传关键字标签；analyzer 两处调用改 `usage_port.persist(...)`，`should_persist` 守卫与 `call_type` / `stock_code` 取值逐字不变，`configure_generation_runtime()` 已装配同一 adapter 实例，故**零新装配点**（bootstrap 25 件 / 31 `configure_*` seam 均未变）。测试：`tests/test_market_analyzer_generate_text.py` 7 处 `patch("...persist_llm_usage")` re-point 为 `patch.object(_usage_port(), "persist")`（保留真实 `should_persist`，不弱化守卫路径），并新增 `TestGenerationUsagePersistPort` 2 条回归（adapter 委托 `src.storage` 且标签参数逐字透传；analyzer 源码不含 `from src.storage`、模块无 `persist_llm_usage` 属性，防回退）。验证：py_compile 4 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` RC=0、analyzer 行首锚定 storage import 计数 0、application 真实 import 面由 3 文件/4 行降至 **2 文件/3 行**（analysis 1 + market 2）、analysis / generation 簇 **500 passed**、`test_market_analyzer_generate_text.py` **106 passed**（+2）、**全量离线 `--continue-on-collection-errors` 31 failed / 5568 passed / 4 deselected / 11 errors（252.74s）——passed 5566→5568（+2 新用例）、FAILED 集合归一后与基线 `diff` 为空 → IDENTICAL，0 新增回归**。快照（sha256 + readlink，3688→3688）逐条比对：ADDED 0 / REMOVED 0 / MODIFIED 16（4 个目标文件 + 12 条 data / logs / vibe-template 运行时噪声），无越界源码改动。回写 STATUS（W4.2 **20/22** 余 2、D2 87.18→**87.45**、综合 83.65→**83.74%**、切片 170→171）与 ADR-004 补 ⑭；详见 progress §0.167。
- [改进] 架构迁移**第 4 批 W4.2 第 13 片：decision 域 5 件历史读取改走 `HistoryRepositoryPort` + 域级默认来源 seam，decision 域 storage 直连归零**（真实代码改动、零提交，HEAD `fe7410bb` 未变）：`decision_signal_service.py`（`self.db = db_manager or getattr(self.repo, "db", None) or DatabaseManager.get_instance()`）与 `decision_signal_reassess_service.py`（`self.db = db or DatabaseManager.get_instance()`）的 storage 耦合都只消费 `get_analysis_history_by_id` 单一读方法，直接命中现成 `HistoryRepositoryPort`——字段 `self.db`→`self.history_repo`、优先级链逐字保留（显式句柄 → 仓储自带 `db` → bootstrap 默认来源），惰性回填方法内改为先取局部变量并在 `None` 时 debug 跳过（不再让 `AttributeError` 落到既有宽 `except` 而伪装成“回填失败”告警）；`skill_opinion_sample_service` / `skill_opinion_outcome_service` / `decision_signal_outcome_service` 三件的 storage import 仅为类型注解 `Optional[DatabaseManager]` 服务（`db_manager` 只喂给既有仓储工厂），故去 import、注解放宽为 `Optional[Any]`、运行时零变化。为前两件在 `application/decision/ports.py` 新增域级默认来源 seam（`_default_history_repo_factory` + `set_default_history_repo_factory`/`get_default_history_repo`，与 PP-1/PP-4 同型持可调用工厂以适配 `DatabaseManager.reset_instance()`），由既有 `bootstrap/decision.py:configure_decision_repositories()`（main + api_lifespan 双入口已在、**25 件 / 31 seam 不变**）追加装配 `DatabaseManager.get_instance`。**自查修正一处真实语义漂移**：首版 reassess 内层构造写成 `DecisionSignalService(history_repo=...)`，丢了收敛前 `db_manager=self.db` 的传递面（调用方显式传 `db` 时内层仓储会退回全局单例）；比对 `git show HEAD:src/services/decision_signal_reassess_service.py` 原文后补回 `db_manager=db`，并用新用例断言 `signal_service.repo.db is isolated_db` 锁死。测试：`tests/test_decision_signal_service.py` 追加 7 条用例（默认 seam 未装配＝`None`／已装配生效、显式 `history_repo` 优先、仓储 `db` 优先于默认源、无 `db` 仓储回落默认源、无源时回填跳过且不抛异常、reassess 向内层透传 `db`），锁住优先级链与降级契约。验证：py_compile 7 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` RC=0、decision 域行首锚定 storage import 计数 0、application 真实 import 面由 8 文件/9 行降至 **3 文件/4 行**（analysis 2 + market 1）、decision 簇 8 测试文件 329 passed、**全量离线 `--continue-on-collection-errors` 31 failed / 5566 passed / 4 deselected / 11 errors（266.66s）——passed 5559→5566（+7 新用例）、FAILED 集合去 ` - <reason>` 后缀后与基线 `diff` 为空 → IDENTICAL，0 新增回归**。快照（sha256+readlink，3681→3683）逐条比对：ADDED 2（当日日志）、REMOVED 0、MODIFIED 18（8 个目标文件 + 10 条 data/vibe-template 运行时噪声），无越界源码改动。回写 STATUS（W4.2 19/22 余 3、decision 域归零、D2 86%→**87%**、综合 83.45→**83.65%**、切片 169→170）与 ADR-004 补 ⑬；详见 progress §0.166。
- [改进] 架构迁移**第 4 批 W4.2 第 12 片：agent/runner 用量遥测改走 `UsageTelemetryPort.persist`，agent 域整域归零 8/8**（真实代码改动、零提交；⚠️ 基线已由 HEAD `8d98792d` 外部前进至 `fe7410bb`——3 个文档提交，非本会话操作）：`application/agent/runner.py` 顶层 `from src.storage import persist_llm_usage as _persist_usage` 唯一使用点是 agent 主循环单步 LLM 调用后的「判定 + 落库」；因该文件在 D-01 阶段已有 `_usage_telemetry_port` seam，且第 11 片已把 `UsageTelemetryPort` 由「只判定」扩为「判定 + 写入」（新增 `persist()`、infra `UsageTelemetryAdapter.persist` 委托 `src.storage`），本片属**消费者追平**：删 storage import，`_persist_usage(response.usage, model_for_usage, call_type="agent")` 改调 `_usage_telemetry_port.persist(...)`，位置参数与关键字形态逐字不变；`configure_usage_telemetry()` 已把同一 `UsageTelemetryAdapter` 实例同时注入 runner 与 chat_context 两个 seam，故**零新装配点**（bootstrap 25 件 / 31 `configure_*` seam 均未变）。NPE 安全性由既有 `_should_persist_usage_telemetry()` 在 `port is None` 时返回 `False` 并 debug 跳过保证；**不采用**在 runner 内保留 storage 兜底 import 的写法（会把依赖方向重新拉回 application→storage），正确语义为未装配即静默跳过并补测试锁住。测试影响面：`tests/test_agent_executor.py` 4 处 `patch("...runner._persist_usage")` 随符号删除失效 → 统一改 `as usage_port` + `patch.object(usage_port, "persist")`；新增 1 条回归用例 `test_run_agent_loop_skips_usage_persist_when_telemetry_port_unwired`（`port=None` 不崩溃、`total_tokens` 正常累计、`src.storage.persist_llm_usage` 零调用）。runner 现 0 storage import、**agent 域整域归零 8/8**（继 alert、history、runtime 后第四个整域归零的域），累计 W4.2 收敛 14/22 文件、余 8（decision 5 / analysis 2 / market 1）。验证：py_compile 两件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` RC=0、runner 行首锚定 storage import 计数 0、usage 子集 7 passed、agent 执行链 9 文件 334 passed / 1 failed（唯一失败命中基线）、**全量离线 `--continue-on-collection-errors` 31 failed / 5559 passed / 4 deselected / 11 errors（249.86s）——passed 5558→5559（+1 新用例）、FAILED 集合去除 ` - <reason>` 截断后缀后与基线 `diff` 为空 → IDENTICAL，0 新增回归**；errors 11 系基线 10（hrs-web test_wt）+ 1（`vibe-template/zentrade` gitignored 外部模板、与本任务无关）。开工/收官内容清单快照（sha256+readlink、3681 条目）逐条目比对：ADDED 0 / REMOVED 0 / MODIFIED 14，真实改动仅 2 个目标文件，其余 12 条为 logs/data/vibe-template 运行时噪声。回写 STATUS（W4.2 14/22 余 8、agent 8/8、D2 85%→86%、综合 83.25→83.45%、切片 168→169）与 ADR-004 补 ⑫；详见 progress §0.165。
- [改进] 架构迁移**第 4 批 W4.2 第 11 片：agent/chat_context 上下文读写窄端口 + `UsageTelemetryPort` 写侧扩展收敛（agent 域 7/8）**（真实代码改动、零提交，HEAD `8d98792d` 未变）：`chat_context.py` 顶层 `from src.storage import get_db, persist_llm_usage` 覆盖 3 处读（`get_agent_provider_turns`/`get_conversation_summary`/`get_visible_conversation_messages`）+ 1 处写（压缩摘要 `upsert_conversation_summary`）+ 1 处用量落库。因 4 处库操作在现成 `ConversationRepository` 中签名与默认值逐字一致（`inspect.signature` 实测），新增窄端口 `ChatContextPort`（`src/application/agent/ports.py`，读 3 + 写 1）并把 chat_context 改模块级 `_chat_context_port` seam + `set_chat_context_port()`；因同一仓储对象亦满足第 10 片的 `ConversationMessagePort`，故复用 `bootstrap/agent.py:configure_agent_conversation()` 一并装配（双入口 main/api_lifespan 已存在，**bootstrap 25 件 / 31 `configure_*` seam 均未新增**）。`persist_llm_usage` 不为 application 开写通道，而是把既有 `UsageTelemetryPort` 由「只判定」扩为「判定 + 写入」（新增 `persist()`），infra `UsageTelemetryAdapter.persist` 委托 `src.storage`，chat_context 改调 `_usage_telemetry_port.persist(...)`——`configure_usage_telemetry` 已装配同一适配器实例、写侧随对象自动可用、无需新装配点。**契约漂移自纠**：首版端口命名 `ChatContextReadPort` 且只声明 3 个读方法，而同一端口对象实际还写 `upsert_conversation_summary`；改名 `ChatContextPort` 补写侧方法，并新增参数化用例 `test_port_protocol_is_satisfied_by_conversation_repository` 以 `inspect.signature` 逐方法比对 Protocol 与 `ConversationRepository` 的参数 name/kind/default（忽略注解），把「端口声明必须覆盖全部真实调用点」固化为回归守卫。测试影响面：`test_chat_context.py:_reset_db()` 与 `test_agent_executor.py`/`test_multi_agent.py` 的落库集成接线由传 `DatabaseManager` 裸实例改传 `ConversationRepository(db)`（与生产同一适配器、不绕过真实仓储）；两条 orchestrator 落库用例（`test_chat_persists_user_and_assistant_messages`/`test_chat_persists_failure_message`）改为 patch `orchestrator.build_visible_chat_history` 返回 `[]`，与同文件同类用例一致、不再依赖全局库读空历史。另在 `tests/test_agent_conversation_port_seam.py` 追加 5 用例（chat_context seam 往返、可见消息读侧消费、两端口协议一致性 ×2、adapter `persist` 委托 storage）。chat_context 现 0 storage import、**agent 域 7/8**（余 1：runner `persist_llm_usage` 单点），累计 W4.2 收敛 13/22 文件、余 9（agent 1/decision 5/analysis 2/market 1）。验证：py_compile 9 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、targeted（`test_chat_context` + 新 seam + `test_llm_usage`）114 passed、agent 执行链（executor/multi_agent/chat_executor/backend/llm_usage）376 passed（仅 1 条基线既有 `test_realtime_rules_create_fetcher_manager_per_quote_check` 失败）、**全量离线 `--continue-on-collection-errors` 31 failed / 5558 passed / 4 deselected / 11 errors（250.70s）——passed 5553→5558（+5 新测试）、FAILED 测试 ID 集合与基线逐条 IDENTICAL（`diff` 空）→ 0 新增回归**；errors 11 系基线 10（hrs-web test_wt）+ 1（`vibe-template/zentrade` gitignored 外部模板、与本任务无关）。开工前内容清单快照（sha256+readlink、3680 条目）改后逐条目比对：9 个目标源/测试文件（ports/usage_telemetry_ports/usage_telemetry_provider/chat_context/bootstrap-agent/test_chat_context/test_agent_conversation_port_seam/test_agent_executor/test_multi_agent），余为 logs/data 运行时噪声、无越界源码改动、无删除。回写 STATUS W4.2/D2/§0.4 计数 167→168・§7/header（23:03）与 ADR-004 补 ⑪ agent/chat_context 证据（bootstrap 25 件/31 seam 不变）；详见 progress §0.164。
- [改进] 架构迁移**第 4 批 W4.2 第 10 片：agent/conversation 对话消息窄端口收敛（agent 域 6/8）**（真实代码改动、零提交，HEAD `8d98792d` 未变）：`ConversationSession` 顶层 `from src.storage import get_db` 仅用于 `add_message → save_conversation_message`（写）与 `get_history → get_conversation_history`（读）两处、无 try/except。因两方法在现成 `ConversationRepository` 中签名与默认值（`limit=20`）逐字一致，新增窄端口 `ConversationMessagePort`（`src/application/agent/ports.py`），会话对象改模块级 `_conversation_port` seam + `set_conversation_port()`，由新建 `bootstrap/agent.py:configure_agent_conversation()` 双入口（main 进程级块 + api_lifespan）以 `ConversationRepository(DatabaseManager.get_instance())` 装配（与旧 `get_db()` 同一单例、0 行为变化）。测试影响面：`test_conversation_manager` 已 patch `ConversationSession.add_message`（autospec）、`test_ask_command` patch 整个 `conversation_manager`，均不触 seam、无需 re-point；但 2 个依赖真实落库的集成用例（`test_agent_executor::test_chat_persists_single_provider_trace_and_reinjects_without_duplication`、`test_multi_agent::test_chat_does_not_read_or_write_provider_trace`）原先靠 `get_db()` 直连落库，首轮全量因此各 +1 回归，改为测试内 `patch("src.application.agent.conversation._conversation_port", db)` 接线后归零（同 §0.161 先例）。另新增 `tests/test_agent_conversation_port_seam.py`（4 用例：setter 往返、写消费、读消费、bootstrap 装配）。conversation 现 0 storage import、**agent 域 6/8**（余 2：chat_context 混合读写、runner `persist_llm_usage` 需扩展 UsageTelemetryPort 写侧协议），累计 W4.2 收敛 12/22 文件、余 10（agent 2/decision 5/analysis 2/market 1）。验证：py_compile 6 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、targeted（新 seam 4 + `test_conversation_manager` + `test_ask_command` + `test_agent_chat_executor` + `test_agent_backend`）46 passed、两条回归隔离复跑 2 passed、**全量离线 `--continue-on-collection-errors` 31 failed / 5553 passed / 4 deselected / 11 errors（256.20s）——passed 5549→5553（+4 新测试）、FAILED 测试 ID 集合与基线逐条 IDENTICAL（`diff` 空）→ 0 新增回归**；errors 11 系基线 10（hrs-web test_wt）+ 1（`vibe-template/zentrade` gitignored 外部模板、与本任务无关）。开工前内容清单快照（sha256+readlink、3679 条目）改后逐条目比对：7 个目标源/测试文件（ports/conversation/bootstrap-agent/api_lifecycle/main/test_agent_executor/test_multi_agent）+ 1 新增测试文件，余为 logs/data 运行时噪声、无越界源码改动。回写 STATUS W4.2/D2/§0.4 计数 166→167・§4 seam 30→31・§7/header 与 ADR-004 补 ⑩ agent/conversation 证据；详见 progress §0.163。
- [改进] 架构迁移**第 4 批 W4.2 第 9 片：agent/tools（search_tools + data_tools）`_get_db` 工厂 seam 收敛（agent 域 5/8）**（真实代码改动、零提交，HEAD `8d98792d` 未变）：两件 tools 各含模块级 `_get_db()` wrapper（`from src.storage import get_db; return get_db()`），分别被 `save_news_intel` 写、`save_daily_data` 写 + `get_analysis_context` 读使用。沿用 comparison/loader/task_service/memory/provider_trace 既有模块 seam 范式：wrapper 体改为模块级 `_db_factory` + `set_db_factory()`（`_get_db()` 返回装配工厂产物），由新建 `bootstrap/agent.py:configure_tools_db()` 双入口（`main` 进程级块 + `api_lifespan`）装配 `DatabaseManager.get_instance`。**关键修复**：tools 在 `CodexToolProcessRunner` 的 spawn 子进程内执行、不经过进程级 bootstrap（子进程刻意 fresh import 以免继承父库连接），故 `infrastructure/agent_runtime/codex_tool_process.py:_execute_registered_tool` 在子进程内亦装配两 tools seam（infra→storage/application 守卫允许）——否则无守护读路径 `get_analysis_context` 会因 seam=None 崩溃；首轮全量正是 +1 回归（`test_codex_tool_process.py::test_three_production_tools_execute_through_spawned_worker`），子进程补齐后归零。测试影响面：全部 DB 相关 tools 测试均 patch wrapper `_get_db` 本身（search 5 / data 4 + 1 monkeypatch），wrapper 符号保留即兼容、**无需 re-point**；另新增 `tests/test_agent_tools_db_seam.py`（5 用例：seam 往返 ×2、取库消费 ×2、bootstrap 装配 ×1）。两件现 0 storage import、**agent 域 5/8**（余 3：conversation/chat_context 混合读写、runner `persist_llm_usage`），累计 W4.2 收敛 11/22 文件、余 11（agent 3/decision 5/analysis 2/market 1）。验证：py_compile 7 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、targeted（tools 4 文件 + codex_tool_process + 新 seam 文件）全绿、**全量离线 `--continue-on-collection-errors` 31 failed / 5549 passed / 4 deselected / 11 errors（259.80s）——passed 5544→5549（+5 新测试）、FAILED 测试 ID 集合与基线逐条 IDENTICAL（`diff` 空）→ 0 新增回归**；errors 11 系基线 10（hrs-web test_wt）+ 1（`vibe-template/zentrade` gitignored 外部模板、与本任务无关）。开工前内容清单快照（sha256+readlink、3677 条目含符号链接）改后逐条目比对：6 个目标源文件（search_tools/data_tools/bootstrap-agent/api_lifecycle/main/codex_tool_process）+ 1 新增测试文件，余为 logs/data 运行时噪声、无越界源码改动。回写 STATUS W4.2/D2/§0.4 计数 165→166・§7/header 与 ADR-004 补 ⑨ agent/tools 证据+ bootstrap 29→30 seam（文件数仍 25）；详见 progress §0.162。
- [改进] 架构迁移**第 4 批 W4.2 第 8 片：agent/executor 复用 provider_trace 默认 db_factory seam 收敛（agent 域 3/8）**（真实代码改动、零提交，HEAD `8d98792d` 未变）：`AgentExecutor._persist_provider_trace` 顶层 `from src.storage import get_db` 唯一用法是把 `db_factory=get_db` 显式传入 `persist_provider_trace_turns`；第 7 片已为 provider_trace 装配默认 db_factory seam（= `DatabaseManager.get_instance`、与 `get_db` 逐字等价），且 `chat_executor` 早已省略 `db_factory` 依赖该默认 → executor 显式传参属冗余。改动：删除 executor 顶层 storage import 与 `db_factory=get_db` 入参、令其与 chat_executor 一致复用默认 seam（生产经 `configure_provider_trace` 装配后取库对象完全等价、0 行为变化，bootstrap 25 件/29 seam 不变）。片前全仓扫 `patch("src.application.agent.executor.get_db")` 仅 `test_agent_executor.py` 1 处（fail-open 用例）：连同真实持久化用例 `test_chat_persists_..._without_duplication` 一并将 patch/接线目标 re-point 到 `src.application.agent.provider_trace._get_default_db_factory`（`return_value=lambda: db`）、无需改生产语义；另校正 `bootstrap/agent.py:configure_provider_trace` docstring 示例（executor 现依赖默认）。executor 现 0 storage import、**agent 域 3/8**（余 5 件为写路径/`persist_llm_usage`/混合读写），累计 W4.2 收敛 9/22 文件、余 13（agent 5/decision 5/analysis 2/market 1）。验证：py_compile 3 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、executor+provider_trace+chat_executor+chat_context targeted **103 passed**（含 2 处 re-point 用例实跑通过）、**全量离线 `--continue-on-collection-errors` 31 failed / 5544 passed / 4 deselected / 11 errors（266.90s）——passed 不变（本片仅改测试、未增用例）、FAILED 测试 ID 集合与基线逐条 IDENTICAL（`diff` 空）→ 0 新增回归**；errors 11 系基线 10（hrs-web test_wt）+ 1（`vibe-template/zentrade` gitignored 外部模板、与本任务无关）。开工前内容清单快照（sha256+readlink、3675 条目含符号链接）改后逐条目比对：除 3 个目标源文件（executor.py/bootstrap-agent.py/test_agent_executor.py）外仅 logs/data 运行时噪声变动、无越界源码改动。回写 STATUS W4.2/D2/§0.4 计数 164→165・§7/header 与 ADR-004 补 ⑧ agent/executor 证据（bootstrap 25 件/29 seam 不变）；详见 progress §0.161。
- [改进] 架构迁移**第 4 批 W4.2 第 7 片：agent/provider_trace 默认 db_factory seam 收敛（agent 域 2/8）**（真实代码改动、零提交，HEAD `8d98792d` 未变）：`persist_provider_trace_turns` 的 `db_factory is None` 回退分支内懒加载 `from src.storage import get_db` 作默认取库工厂，消费方 `chat_executor` 依赖该回退路径（executor 则显式传 `db_factory=get_db`、不受影响）；`get_db()` 即返回 `DatabaseManager.get_instance()` 单例、与门面适配器逐字等价。沿用 comparison/loader/task_service/memory 模块 seam 范式：provider_trace.py 加 `_default_db_factory` + `set_default_db_factory`/`_get_default_db_factory`、回退分支 `from src.storage import get_db` → `db_factory = _get_default_db_factory()`；在既有 `bootstrap/agent.py`（顶层已 import `DatabaseManager`、非新文件）新增 `configure_provider_trace()`，`main.py` 进程级块与 `api_lifecycle` 双入口 `configure_agent_memory()` 后调用。片前全仓扫 `patch("src.storage.get_db")`/provider_trace 消费点，确认无测试 patch 该回退源符号（`test_agent_executor.py` patch 的是 executor 自身 `get_db`、非本路径）；补 4 处测试（seam accessor 往返、经 seam 的真实持久化消费路径、seam 未装配 fail-open、bootstrap 装配断言）。provider_trace 现 0 storage import、**agent 域 2/8**（域未归零，余 6 件多为写路径/`persist_llm_usage`/`db_factory`），累计 W4.2 收敛 8/22 文件、余 14。验证：py_compile 5 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、provider_trace+executor+chat_executor+chat_context targeted **103 passed**（provider_trace 9、含 4 新增）、**全量离线 `--continue-on-collection-errors` 31 failed / 5544 passed / 4 deselected / 11 errors（276.38s）——passed 恰 +4、FAILED 测试 ID 集合与最新基线逐条 IDENTICAL（`diff` 空、含 2 条 test_multi_agent 既有失败不变，隔离复跑证实系顺序依赖 flake、与本任务无关）→ 0 新增回归**；errors 11 系基线 10（hrs-web test_wt）+ 1（`vibe-template/zentrade` gitignored 外部模板 conftest `import app` 失败、与本任务无关、未动 setup.cfg/模板、用 `--continue-on-collection-errors` 越过）。开工前内容清单快照（sha256+readlink、3671 条目含符号链接）改后逐条目比对：除 5 个目标源文件外仅 logs/db/vibe-template 运行时噪声变动、无越界源码改动。回写 STATUS W4.2/D2/§0.4 计数 163→164・§7/header 与 ADR-004 补 ⑦ agent/provider_trace 证据 + bootstrap 28→29 seam；详见 progress §0.160。
- [改进] 架构迁移**第 4 批 W4.2 第 6 片：agent/memory 模块级 seam 收敛（agent 域 opener）**（真实代码改动、零提交，HEAD `8d98792d` 未变）：`AgentMemory.get_stock_history` 是 agent 域最干净的单一只读 storage 耦合（函数内懒加载 `from src.storage import get_db` + `get_analysis_history`、命中现成 `HistoryRepositoryPort`、且包在 try/except 内 → seam 未装配时异常被吞成 `[]` 优雅降级、比上片 task_service 更安全）。沿用 comparison/loader/task_service 既有模块 seam 范式：memory.py 加 `_history_repo` seam + `set_history_repo`/`_get_history_repo`、`db = get_db()`→`db = _get_history_repo()`；在既有 `bootstrap/agent.py`（顶层已 import `DatabaseManager`、非新文件）新增 `configure_agent_memory()`（仿 `configure_usage_telemetry`），`main.py` 进程级块与 `api_lifecycle` 双入口 `configure_usage_telemetry()` 后调用。落地上一片沉淀的 patch 盲区教训——片前全仓扫 `patch("src.storage.get_db")` 消费点，re-point `test_multi_agent.py` 唯一 `@patch("src.storage.get_db")`→`_get_history_repo` 并补 1 处 bootstrap 装配测试，未复现 +N 回归。memory 现 0 storage import、**agent 域 opener 1/8**（域未归零，余 7 件多为写路径/`persist_llm_usage`/`db_factory`），累计 W4.2 收敛 7/22 文件、余 15。验证：py_compile 5 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、memory+task_service targeted **9 passed**、**全量离线 `--continue-on-collection-errors` 31 failed / 5540 passed / 4 deselected / 11 errors（286.08s）——passed 恰 +1、FAILED 集合与上片基线逐条 IDENTICAL（`diff` 空）→ 0 新增回归**；errors 11 系基线 10（hrs-web test_wt）+ 1（`vibe-template/zentrade` gitignored 外部模板 conftest `import app` 失败、mtime 19:25 恰在上片全量期落盘、与本任务无关、未动 setup.cfg/模板目录、用 `--continue-on-collection-errors` 越过后 surfacing）。回写 STATUS W4.2/D2/§0.4 计数 162→163・§7/header 与 ADR-004 补 ⑥ agent/memory 证据 + bootstrap 27→28 seam；详见 progress §0.159。开工快照 `~/hermesx_b4w42agentmem_pre_20261030_193913.tar.gz`（96.5 MB，`SET_EQUAL: True`，1716 文件含符号链接）。
- [改进] 架构迁移**第 4 批 W4.2 第 5 片：runtime/task_service 模块级 seam 收敛，runtime 整域归零**（真实代码改动、零提交，HEAD `8d98792d` 未变）：`TaskService.get_analysis_history` 是 runtime 域唯一 storage 耦合（顶层 `from src.storage import get_db` + 方法内 1 处 `db = get_db()`，只读、命中现成 `HistoryRepositoryPort`），无 `self.db`、`get_analysis_history` 全仓无调用方、`test_task_service.py` 不测该方法且全仓无测试 patch `src.storage.get_db` 驱动 task_service → seam 转换无下游 patch 风险。沿用 comparison/loader 既有模块 seam 范式：task_service.py 去 storage import、加 `_history_repo` seam + `set_history_repo`/`_get_history_repo`、`db = get_db()`→`db = _get_history_repo()`；新建 `bootstrap/runtime.py:configure_task_service()`（`DatabaseManager` 门面作适配器、bootstrap→storage 合法、setter 幂等），在 `main.py` 进程级装配块（`configure_history_loader()` 后）与 `api_lifespan`（`src/bootstrap/api_lifecycle.py`）双入口调用；补 2 处 seam 回归测试（消费路径 + bootstrap 装配）。task_service 现 0 storage import，**runtime 域整域归零**（继 alert、history 后第三个），累计 W4.2 收敛 6/22 文件、余 16。验证：py_compile 4 件 OK、守卫 `--check` RC=0、flake8 改动文件 RC=0、`test_task_service.py` targeted **4 passed**（+2 新增）、**全量离线 31 failed / 5539 passed / 4 deselected / 10 errors（335.93s）——passed 恰 +2（新增用例）、FAILED 集合 31 条与基线逐条一致（含隔离复跑确认 `test_bot_dispatcher_async` 那条系既有 `name_to_code_resolver` patch 目标缺失、非本片）→ 0 新增回归**。回写 STATUS W4.2/D2/§0.4 计数 161→162・§7/header 与 ADR-004 补第 5 片证据 + bootstrap 24→25 件/26→27 seam；详见 progress §0.158。开工快照 `~/hermesx_b4w42taskservice_pre_20261030_191942.tar.gz`（96.5 MB，`SET_EQUAL: True`，1715 文件含符号链接）。
- [改进] 架构迁移**第 4 批 W4.2 第 4 片：history/comparison + loader 模块级 seam 收敛，history 整域归零**（真实代码改动、零提交，HEAD `8d98792d` 未变）：两件均为模块级函数直连（`comparison.py` 的 `get_signal_changes*` 用 `DatabaseManager.get_instance()`、`loader.py` 的 `load_history_df` 用函数级 `from src.storage import get_db`），沿用 loader 既有 `set_history_daily_bar_fetcher` 模块 seam 范式（`Any` 类型、无 Protocol），各加 `_get_history_repo`/`_get_kline_repo` seam + `set_history_repo`/`set_history_kline_repo` setter，由 `bootstrap/history.py:configure_history_loader`（`main.py` 进程级装配块 + `api_lifespan` 双入口、setter 幂等）以 `DatabaseManager` 门面作适配器装配（bootstrap→storage 合法）。comparison 唯一生产调用方 `notification.py` 已包 try/except、loader DB 主路本在 try/except 内降级 → 行为与旧取数同一对象一致。re-point 测试 patch 目标 14 处：`test_history_loader.py` 6 + `test_data_tools_daily_history_cache.py` 8 处 `@patch("src.storage.get_db")`→seam getter（`data_tools._get_db` 不动；首轮全量出现 +4 回归即此 patch 盲区，FAILED 列表 diff 定位后补改回基线）。comparison/loader 现 0 storage import，**history 域（read_model/comparison/loader）全部归零、继 alert 之后第二个整域归零**，累计 W4.2 收敛 5/22 文件、余 17。验证：py_compile 4 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、history/缓存 targeted 全通过、**全量离线 31 failed / 5537 passed / 4 deselected / 10 errors（278.53s）与基线逐数字一致、FAILED 集合 IDENTICAL → 0 新增回归**。回写 STATUS W4.2/D2/§0.4 计数 160→161・§7/header 与 ADR-004 补第 4 片证据；详见 progress §0.157。开工快照 `~/hermesx_b4w42history_pre_20261030_185456.tar.gz`（96.68 MB，`SET_EQUAL: True`）。
- [改进] 架构迁移**第 4 批 W4.2 第 3 片：history/read_model 依赖倒置收敛**（真实代码改动、零提交，HEAD `8d98792d` 未变）：延续「service 内 ad-hoc `self.db` 直连 → 注入现成 `*RepositoryPort`」范式，将 `HistoryService.self.db`（模块级 `from src.storage import DatabaseManager`）的 7 个读方法（分页/详情/删除/新闻等）全部改走现成 `HistoryRepositoryPort`——生产 `service.py:44` 早已按位置传入仓储，故去 `DatabaseManager.get_instance()` 默认、字段 `self.db`→`self.history_repo`、import 改端口；取证确认生产无裸构造、2 处测试裸构造 `HistoryService()` 仅访问不触库的 `_generate_single_stock_markdown`、无外部访问实例 `.db`。re-point 仅 `test_history_news_fallback.py` 2 处关键字 `db_manager=`→`history_repo=`（余位置参自动兼容）。该文件现 0 storage import，history 域未归零（余 comparison/loader 函数级懒加载需 seam），累计 W4.2 收敛 3/22 文件、余 19（market_review 写路径需新端口、decision 5 件需新增端口）。验证：py_compile 3 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、history 相关 targeted **182 passed**、**全量离线 31 failed / 5537 passed / 4 deselected / 10 errors（257.35s）与基线逐数字一致 → 0 新增回归**。回写 STATUS W4.2/D2/§0.4 计数 159→160・§7/header 与 ADR-004 补 W4.2 实施证据；详见 progress §0.156。开工快照 `~/hermesx_b4w42readmodel_pre_20261030_175915.tar.gz`（96.68 MB，`SET_EQUAL: True`）。
- [改进] 架构迁移**第 4 批 W4.2 第 2 片：market/daily_market_context 依赖倒置收敛**（真实代码改动、零提交，HEAD `8d98792d` 未变）：延续 alert 片确立的「service 内 ad-hoc `self.db` 直连 → 注入现成 `*RepositoryPort`」范式，将 `DailyMarketContextService.self.db`（模块级 `from src.storage import DatabaseManager`、类内仅一处 `get_analysis_history`）改为注入现成 `HistoryRepositoryPort`，调用点（生产 `pipeline.py:1838`/`main.py:510/513`）传入既有真实门面作端口适配器；该文件现 0 storage import。同步 re-point 生产 3 点 + 测试 32 点（28 构造 + 4 处 mock 调用断言）`db_manager=`→`history_repo=`。market 域未整体归零（`market_review.py` 仍 2 处函数内懒加载），累计 W4.2 收敛 2/22 文件。验证：py_compile 4 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、alert targeted 未受影响、daily_market 相关 targeted **187 passed**、**全量离线 31 failed / 5537 passed / 4 deselected / 10 errors（292.19s）与基线逐数字一致 → 0 新增回归**。回写 STATUS W4.2/D2/§0.4 计数 158→159・§7/header 与 ADR-004 补 W4.2 实施证据；详见 progress §0.155。开工快照 `~/hermesx_b4w42dmc_pre_20261030_171110.tar.gz`（96.68 MB，`SET_EQUAL: True`）。
- [改进] 架构迁移**第 4 批 W4.2 首个域切片：alert 域依赖倒置收敛**（真实代码改动、零提交，HEAD `8d98792d` 未变）：将 `AlertService` 遗留的 `self.db` 跨域直连（`alert/worker.py:599` 调 `get_analysis_history` 查询分析历史）由 `from src.storage import DatabaseManager` 改为注入现成 `HistoryRepositoryPort`（`history/ports.py`，签名与 worker 关键字调用完全吻合），复用 `bootstrap/history.py` 同一范式以 `DatabaseManager.get_instance()` 作端口适配器（门面结构性满足 Protocol）。改动 3 件：`application/alert/service.py`（去 storage import + `db_manager`/`self.db` 死赋值，新增 `history_repo` 参数）、`application/alert/worker.py`（`self.service.db.` → `self.service.history_repo.`，None 优雅降级与原行为一致）、`bootstrap/alert.py`（`build_alert_service` 去 `db_manager=db`、传 `history_repo=db`；bootstrap→storage 合法，import 保留）；`src/application/alert/` 现 **0 storage import**。验证：py_compile 3 件 OK、守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、alert targeted **96 passed**（8 failed 全在 `test_alerts_docs.py`，即 W9.2 既有基线）、**全量离线 31 failed / 5537 passed / 4 deselected / 10 errors（290.23s）与基线逐数字一致 → 0 新增回归**。回写：STATUS W4.2 ⏳→🔄（记 alert 1/8）+ §0.3/§4/§7/§0.4 与 ADR-004 补实施证据；余 7 域（agent 8/decision 5/history 3/analysis 2/market 2/backtest 0/runtime 1，共 21 文件）待按同一范式逐域推进，22 文件全收敛后再把 `src.storage` 加入 application 禁入清单。开工快照 `~/hermesx_b4w42alert_pre_20261030_163755.tar.gz`（96.67 MB，`SET_EQUAL: True`）；详见 progress §0.154。
- [文档] 架构迁移**第 4 批首片：W4.3 `infra → src.storage` 门面方向复核闭环 + W4.2/W4.5 实测切片重估**（零代码改动、零提交，HEAD `8d98792d` 未变）：对 `infrastructure → src.storage` 依赖方向做实测复核，结论：infra→storage 共 **18 文件**（`persistence/repositories/` 16 + providers 1 + agent_runtime 1，较旧记 19 订正）；`storage.py` 顶层反向 import 的 repo 在自身侧用函数内懒加载回引 `DatabaseManager`，顶层双向边不共存于同一文件→**无运行时导入环**；但 repo↔门面构成 ADR-004 已预见、待「`DatabaseManager` 本体迁入 `infrastructure/persistence`」才塌缩的**过渡性双向耦合**，守卫刻意不禁 infra→storage（零代码）。同时实测重估：W4.2（22 文件跨 8 域、service 内 ad-hoc `get_db()`/`DatabaseManager()` 直连、测试 28 处 patch 目标）与 W4.5（config→infrastructure 3 条边：`settings.py:76` 模块级 `generation_params` + `:563/:577` 懒加载 `llm_adapter`）体量均大于原 M 估，**需按域拆多切片**、不单会话强收。回写：`refactoring/ARCHITECTURE_MIGRATION_STATUS.md`（W4.3 ⏳→✅ + §0.0/§0.2/§0.4/§5/§7）与 `architecture_migration_adr.md` ADR-004（新增复核结论 + 三处 19→18）同步；全局综合保持 **83%**（W4.3 为零代码复核、不改百分比）。开工快照 `~/hermesx_b4_pre_20261030_152831.tar.gz`（96.67 MB，`SET_EQUAL: True`）；详见 progress §0.153。
- [文档] 架构迁移**文档治理**（零代码改动、零提交，HEAD `8d98792d` 未变）：将状态总览 `ARCHITECTURE_MIGRATION_STATUS.md` 由仓库根目录移至 `documents/framework/refactoring/`；新增 **§0.0 全局进度评估（图形化）**（HTML `<progress>` + Unicode 块条 + Mermaid `pie`，全局综合 **83%（区间 80%–86%）**，两口径 A 分层归位 95% / B 全量验收 83%）；按「只保留最新状态」原则将 §7「变更日志」（逐条发现/自纠/取证推翻等已解决项）重写为**里程碑摘要**，过程明细统一归 `architecture_migration_progress.md` 流水台账（新增 §0.152）；同步固化两文档分工（STATUS=全局总览、progress=执行明细）并刷新陈旧实测数字（切片 156／`src/` py 378／四层 domain 59・application 165／快照 194）。详见 progress §0.152。
- [chore] 架构迁移**第 3 批**（W4.1 领域纯件下沉 + W4.4 端口布局成文，零提交，HEAD `8d98792d` 未变）：收敛 `scripts/check_architecture.py` 两处守卫盲区。① **W4.1**：复用 R2-A3 `local_cli_policy.py` 先例，采取物理下沉 + 全量 re-point（不加 baseline 豁免、不留隐式 re-export），将三组纯件从用例/配置层下沉领域层：`stock_list_parser`（`mv` 自 `application/quote`，`cmp` 逐字节一致）→ `domain/market/`、通知等级词表与免打扰/时区校验纯规则（`ast.get_source_segment` 5 函数逐字节一致 + 4 常量值一致）→ 新建 `domain/notification/noise_rules.py`（`application/notification/noise.py` 407→342 行，仅留 dedup/cooldown 状态机）、backend 身份 12 常量（值+类型 identical）→ 新建 `domain/generation/backend_identity.py`（`application/generation/catalog.py` 仅留解析策略）；累计 re-point 5+4+17=26 件，使 `src/config` 彻底只依赖 `src/domain`。② 收紧守卫：`src/domain/` 禁入清单新增 `src.application`，防领域纯规则被用例层反向重新耦合。③ **W4.4**：`ARCHITECTURE_TARGET.md` §2 写明「不建集中 `src/application/ports/`、按业务域就近放置 `ports.py`」为既定策略（引 ADR-002）。验证：守卫 `--check` RC=0、严格 flake8 `E9,F63,F7,F82` 计数 0、装配冒烟 OK、targeted 14 文件 **699 passed**、**全量离线 31 failed / 5537 passed / 4 deselected / 10 errors（287.00s）与既有基线逐数字一致 → 0 新增回归**。开工快照 `~/hermesx_b3_pre_20261030_142531.tar.gz`（96.66 MB，`SET_EQUAL: True`）；详见 progress §0.151。
- [测试] 架构迁移**第 2 批收口**（W1 验证矩阵，零源码改动、零提交，HEAD `8d98792d` 未变）：全量离线基线 **31 failed / 5537 passed / 4 deselected / 10 errors**（296.54s）与既有基线逐数字一致（10 个 ERROR 全在 `apps/hrs-web/scripts/test_wt/*`，8 个 FAILED 为 `tests/test_alerts_docs.py` 与 `alerts.md` 锚点式标题的既有耦合）；**全路由 OpenAPI A/B** 以 `git worktree` 取 HEAD 真基线对比，**153 paths / 239 schemas 逐字节 IDENTICAL**（路径集合／方法面／schema 名集／字段集四项全一致），取代早期仅 watchlist 9 路由的局部证据；**三入口真实进程 smoke** `main.py --serve-only`、`uvicorn server:app`、`webui.py` 均 `/health` 200（`webui.py` 只读 `.env` 的 `WEBUI_PORT`、不读 `--port`，需环境变量覆盖）；**空库创建实测** 32 表 / 229 索引无缺无余；**旧库升级实测**（24.8 MB 真实副本）重跑幂等（表/索引/列/行数零变化），删表可自动重建，但**删除未被 `_ensure_*` 白名单覆盖的列不会自动补回**（`agent_provider_turns.messages_json` 14→13），为 AT §9.2-1「schema 版本化迁移」未决项提供可复现风险证据；**Electron 桌面端打包经用户同意砍掉**（实测 `apps/hrs-desktop/` 本次 0 改动），以 Web 构建 + Docker import smoke + hidden-import 清单核对替代。两项未绿：**Web `npm run lint`/`npm run build` 失败**（58 lint errors / 26 TS errors，逐个确认报错的 20 个文件全部为 HEAD 未改动文件，属前端既有债务而非迁移回归）；**Docker 真实 build 未跑**（本机 daemon 未运行，已用 CI `docker-build` 同款 8 条 smoke import 全部通过 + `docker/Dockerfile`、`docker-compose.yml`、`entrypoint.sh` 对旧模块路径 0 残留作为替代）。总门禁 `./scripts/ci_gate.sh` 已取到最终结果：**RC=1**，但前 4 阶段全绿（`py_compile` 22 组硬编码路径、守卫 `--check` `No architecture violations found.`、严格 flake8 `E9,F63,F7,F82` 计数 **0**、`test.sh code` + `test.sh yfinance` 全通过），退出码仅来自第 5 阶段 offline suite 的既有基线（**31 failed / 5537 passed / 4 deselected / 10 errors / 507 subtests**，264.82s，与独立全量跑逐数字一致）。详见 `documents/framework/architecture_migration_progress.md` §0.150。
- [文档] 架构迁移**第 1 批收口**（W2 文档收口 6 项 + W3 清理尾巴 5 项，零代码改动、零提交）：`ARCHITECTURE_TARGET.md` L256（§4.3 notification 行）由「解继承端口化留 P4」改为终态块（R2-B3 解 14-mixin 继承 + R2-B5 物理迁 `infrastructure/notification/senders/` + R3-S11 补 `ImageRenderPort`；仍余 `application/notification/notification.py` 3063 行模板渲染未分离），§9.2 新增 **§9.2.1 已决表**（`data_provider/` 原位例外／自研守卫已进 `scripts/ci_gate.sh`／进程模型单进程假设 3 项转已决；schema 版本化与安全性能基线 2 项保留未决），§4.5 补「例外与移除前置条件」与「磁盘层面复核」两段；新建 `documents/framework/architecture_migration_adr.md` 沉淀 **ADR-002~006**（端口按业务域就近放置／`data_provider/` 原位／`src/storage.py` 门面例外及其移除条件／`src/auth.py` D-06 落法 A／`src/services/__init__.py` 兼容面与 tombstone 规则双保留）；`ARCHITECTURE_MIGRATION_STATUS.md` 回写 W2/W3 全项状态并新增 W9（docs/AGENTS.md 旧路径漂移）/W10（`resolve_litellm_wire_model` 双入口）待办，全量验收口径 70% → **73%**。磁盘清理：删除 `src/UNKNOWN.egg-info/`（AT §3 点名的构建残留）与 `src/repositories/` 空目录。**取证改判**：原定「删 `src/services/__init__.py` 兼容面」阻力小的推断有误 —— `scripts/build-backend-macos.sh:94` 与 `scripts/build-backend.ps1:110` 的 PyInstaller `--hidden-import` 仍引用该模块，故**不删**，改为成文例外 + 删除前置条件（ADR-006）；同理原定「新建 `adr/` 目录」与「补运行矩阵成文」两项经复核分分别为与 ADR-001 冲突、progress §2 已成文，均已修正。验证：守卫 `--check` RC=0、`baseline.entries` 仍 `[]`、兼容面冒烟通过、受影响文档断言测试簇 7 文件 **69 passed / 8 failed**（8 个均为 `tests/test_alerts_docs.py` 与 `alerts.md` 锚点式标题的既有耦合，HEAD 版同样失败，非本批回归）；HEAD `8d98792d` 未变；`src/core/__pycache__/` 9 个 `.pyc` 因工具限制未清（git-ignored，实测 `src.core.pipeline` `ModuleNotFoundError`，无行为影响）。
- [文档] 新增根目录 `ARCHITECTURE_MIGRATION_STATUS.md`：架构迁移的**唯一进度视图**（与流水台账 `architecture_migration_progress.md` 分工互补），按「整体任务 P0–P5 → 分步任务 E1–E20 → 子任务/待办 W1–W8」三级编号组织，含两口径完成度（分层归位 95%／全量验收 70%）、六维度打分、7 天执行节奏、38 项待办（标注 S/M/L 难度与是否需拍板）、先易后难的六批次执行顺序、更新协议与重取证命令。数据全部为 2026-10-30 实测（376 py／四层 56-166-107-24-4／守卫基线空／149 片／221 快照——后三项由同期 §0.149 复核订正为 153 片／187 快照，全量验收口径 70% 订正为 73%；待办系列后因第 1–2 批取证新增 W9/W10/W11 而扩为 **W1–W11 / 43 子项**，切片数因 §0.150 为 **154**）。零代码改动、HEAD 未变。
- [文档] 架构迁移 R3 收口（终态盘点 + 活文档对齐 + 守卫复核）：`src_migration_index.md` 标题与 §0 改为终态口径（待迁移件 **0**，2026-10-28 的 96 件统计降为历史基线，历史 bullet 不改写）；`ARCHITECTURE_TARGET.md` §4 目标表 6 行补终态（`data_provider/` 明确**原位保留**且应用层只经端口、`src/services/` 仅余兼容面、`src/core`/`analyzer`/`search_service`/`src/schemas`/`md2img`/`feishu_doc` 完成态、`auth`+`data`/`patches`/`brokers`/`utils` 例外与原位保留），§4.5 新增「留存项」表 + 已归零簇清单并把原 113 件表降为历史基线，§4.1 中与 S15b 矛盾的「仍待后续片」改为当时态；守卫复核确认 `architecture_baseline.json` 的 `entries` 仍为 `[]`（无历史豁免），`src/core/`、`src/services/` 两条规则刻意保留为 tombstone。零代码改动、HEAD 未变。
- [chore] 架构迁移 R3-S16（根级 `src/scheduler.py` 下沉 `src/application/runtime/scheduler.py` + 调度时间纯函数单源化，D-07 落法 A）：先把 `normalize_schedule_times`（原 L27-48）逐字抽到 `src/domain/shared/schedule_times.py`（函数体与 HEAD 完全一致），消掉 `src/config/settings.py` 对 `src/scheduler` 的模块级 import（`config → application` 反向边）；再 `git mv` 沉 `Scheduler`/`GracefulShutdown`/`run_with_schedule` 至 application（472→454 行，与 HEAD diff 仅 2 hunk：docstring 来源说明 + 函数抽走改按名导入，实现体零改动）。re-point 6 文件（`config/settings` 1、`runtime_scheduler` 1、`main` 2、`test_scheduler_background` 12、`test_main_schedule_mode` 9 处 `patch()` 串）+ `scripts/ci_gate.sh:9` py_compile 路径；新增 `tests/test_schedule_times_domain.py` 8 用例（行为等价 + 三处解析到同一函数对象 + 子进程守卫 `import src.config.settings` 不拉起 application）。**至此 `src/*.py` 待迁移面清零**，仅余空 `__init__.py` 与已批准例外 `storage.py`/`webui_frontend.py`/`auth.py`。验证：守卫 `--check` 0、py_compile 8 件 OK、CI 口径 flake8 0、targeted 575 passed、全量离线 31 failed / 5537 passed / 10 errors 与基线 FAILED 集合 IDENTICAL；HEAD `8d98792d` 未变（零提交）。预存缺陷（`_refresh_daily_schedule_if_needed` 重复定义）未顺带修
- [chore] 架构迁移 R3-S15b（`src/core/pipeline.py` 整体搬包 + 取数端口化，`src/core/` 仓库层面清零）：3942 行编排层迁入 `src/application/analysis/pipeline.py`，业务实现零改动（仅 4 处：删 `from data_provider import DataFetcherManager`、加端口 import、`__init__` 追加 `stock_data` 形参、赋值改走工厂，净 +5 行）。新增 `StockDataPort` 端口（pipeline 实测 10 方法）+ `DataFetcherManagerStockDataPort` 适配器（惰性 import、`__getattr__` 透传排行榜类可选能力、每次工厂调用新建实例以保持“一条流水线一个管理器”的预热缓存语义）+ `bootstrap/analysis.py::configure_stock_data_port()`，与 `ImageRenderPort` 不同：取数是必需能力，未装配**显式抛错**而非静默降级。**属性名保留 `self.fetcher_manager`**，全仓 ~100 处测试直接赋值/断言锚点不动。re-point 28 个 py 文件 223 处（含 5 处注释内斜杠路径）+ 9 份文档 16 处；16 处 `DataFetcherManager` patch 改写为 `patch(...build_stock_data_port, return_value=MagicMock())`（语义等价）。装配三挂点：`main.py` / `src/bootstrap/api_lifecycle.py` / `tests/conftest.py`（session autouse）。新增 `tests/test_stock_data_port.py` 5 用例（未装配抛错 / 协议方法面 / 未知能力探测 None / 注入优先 / 默认走工厂）。验证：守卫 `--check` 0（application 层 `data_provider` 1→0、私有成员 0）、`compileall` 0、CI 口径 flake8 0、targeted 495 passed、全量离线 31 failed / 5529 passed / 10 errors 与基线 FAILED 集合 IDENTICAL、HEAD 未变
- [chore] 架构迁移 R3-S15a（`src/core/pipeline.py` 解耦前置，不改归属）：pipeline 3925→3942 行，把 application 层禁入项从「5 处 import + 28 处私有成员」收敛到「1 处 import + 0 私有」——`is_bse_code`/`normalize_stock_code` 改指 `src.domain.market.stock_codes`、`is_us_stock_code` 改指 `src.domain.market.us_index_symbols`、`ChipDistribution` 下沉新建 `src/domain/market/chip_distribution.py`（类体逐字节搬移；`data_provider/realtime_types.py` 461→373 行改单行 re-export，`is` 同一性 True）；函数内 `from src.infrastructure.reporting.img_render import markdown_to_image` 删除，改走 R3-S11 既有 `build_default_image_render_port()`（3 调用点，未装配 → None → 原文本回退）；19 处 `self.notifier._*` 改用 `NotificationService` 新增的 5 个公开薄转发面（`image_enabled_channels`/`image_max_chars`/`should_use_image_for_channel`/`send_channel_image`/`slack_image_target`，私有名全部保留以守住 60 处 `patch.object` 锚点）；8 处 `StockAnalysisPipeline._x` 改 `cls._x` 且 5 个 `@staticmethod` 转 `@classmethod`；1 处 `self.db._analyze_ma_status` 改用 `storage.DatabaseManager` 新增公开 `analyze_ma_status`。测试同步：`test_pipeline_notification_image_routing` 增公开面 mixin（断言零改动）、`test_pipeline_market_phase_context` 1 行 mock 名。验证：守卫 `--check` exit=0、py_compile 6 件 OK、CI 口径 flake8 0（另 F401/F821 0）、targeted 15 文件 **489 passed**、全量离线 **31 failed / 5524 passed / 10 errors**（FAILED 集与基线 IDENTICAL、ImportError 0）；HEAD `8d98792d` 未变（零提交）。行为说明：Slack 图片分支原引用 R2-B3 去继承后已不存在的 `_slack_bot_token`/`_slack_channel_id`（实际是被 `_send_channel_safely` 吞掉的 AttributeError），改由 `slack_image_target()` 从 config 取值；报告转图端口未装配时与 `NotificationService.send()` 同一降级面（生产 `main.py`/`api_lifecycle` 与测试 conftest 均已注册）。
- [chore] 架构迁移 R3-S14（`src/core` 簇末件 `trading_calendar.py` 下沉 `src/domain/market/`，前置谓词单源化）：本件不是纯平移，index 标注的 L136 `from data_provider import ...` 属 domain 明令禁入，先把两个纯谓词下沉——`is_us_stock_code`（30 行，纯 regex + `US_INDEX_MAPPING`）迁入 `src/domain/market/us_index_symbols.py`，`data_provider/us_index_mapping.py` 改三条薄 re-export（保留 `get_us_index_yf_symbol`）；`is_hk_stock_code`（32 行，原 `data_provider.akshare_fetcher._is_hk_code`）迁入 `src/domain/market/stock_codes.py`，fetcher 侧删实现、以模块级别名 `_is_hk_code` 兼容 3 处内部调用与既有测试导入面（净 -29 行）。**等价性**：从 HEAD 抽出旧实现对 30 个代码语料逐项对拍，两谓词 **0 差异**，且新旧对象身份一致（`is` 判定 True）。**迁移**：`git mv` + `git reset -q` → `src/domain/market/trading_calendar.py`（651→656 行，仅 docstring 来源说明 + L136 import 拆分，实现体零改动）；导入新模块后 `data_provider` 不再出现在 `sys.modules`（旧路径会拉起 10 个 Fetcher 的重 barrel），`get_market_for_stock` 对 us/hk/cn/jp/kr/tw 八码结果全部正确。**re-point 17 文件 28 处**（生产 10 文件 13 处：main×3、bot market、core pipeline、quote×2、alert worker、decision×2、market×2；测试 7 文件 15 处，含 `sys.modules` 键），代码面旧路径残留 0。**口径教训**：首轮全量收集报 `tests/test_trading_calendar.py` ImportError——该件用 `from src.core import trading_calendar`（包→模块绑定），点号 grep 与路径字面量 grep 均漏；补扫全仓 `from src.core import` 并改指新路径后全量转绿。**本片增量：`src/core` 2→1 件（仅余 `pipeline.py`，S15 Epic）**。验证：守卫 `--check` exit=0、py_compile 22 件 OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted **333 passed/0 fail**、全量离线 **31 failed / 5524 passed / 10 errors** 与基线 FAILED node-ID 集合 **IDENTICAL**（NEW=[]/GONE=[]）、ImportError 0；HEAD `8d98792d` 未变（零提交）。开工快照 `~/hermesx_r3s14_pre_20261030_095230.tar.gz`（659 文件、SET_EQUAL=True）。详见 `documents/framework/architecture_migration_progress.md` §0.143 与 `documents/framework/src_migration_index.md` R3-S14 段
- [chore] 架构迁移 R3-S13（`src/core` 簇次件 `market_review.py` 整体零改动下沉 `src/application/market/`）：本件 932 行，application 口径静态违规 **0**、`forbid_private_members` **0**；顶层 import 为 `src.config` + `src.application.*` + `src.domain.*` + `src.utils.*`，仅 L68/L772 两处函数内 `from src.storage import DatabaseManager`（`src.storage` 不在 application 禁入清单，属既有根级遗留）。**不拆簇决策**：取数已由 R3-S10 的 `application/market/market_analyzer.py` 承担，文件内剩余「编排/渲染/持久化」三簇共用同一 `run_market_review` 主流程、无低风险切割点，拆分需新增端口与用例边界，超出本片最小范围，故按索引目标路径直搬。**迁移**：`git mv` + `git reset -q` 单件，内容相对开工前**逐字节一致**（相对 HEAD 的差异全部来自前序切片已完成的 import 现代化）；**re-point 15 文件 44 处**（生产 6 文件 8 处：`application/analysis/analyzer_service.py` 顶层同层 import、`main.py`×2、`api/v1/endpoints/analysis.py`、`bot/commands/market.py`、`application/market/daily_market_context.py` 懒 import、`infrastructure/persistence/repositories/analysis_repository.py` 懒 import + 注释；测试 9 文件 36 处，含 `import ... as` 模块对象与 `sys.modules` 替换键），代码面旧路径残留 0、`scripts/ci_gate.sh` 与打包配置不含本件。**本片增量：`src/core` 3→2 件（余 `trading_calendar.py`、`pipeline.py`）；`src/application/market/` 13→14 件**。验证：守卫 `--check` exit=0、py_compile 16 件 OK、CI 口径 flake8（E9,F63,F7,F82）=0、独立进程冒烟（旧路径 `ModuleNotFoundError`、`analyzer_service.run_market_review` 与新模块同一对象、增量禁入集合 `[]`）、targeted **268 passed/0 fail**、全量离线 **31 failed / 5524 passed / 10 errors** 与基线 FAILED node-ID 集合 **IDENTICAL**（NEW=[]/GONE=[]）、ImportError 0；HEAD `8d98792d` 未变（零提交）。**口径备注**：导入本件会连带 `sqlalchemy`/`src.infrastructure.persistence.*`，溯源为既有链 `application/analysis/analyzer.py:59 from src.storage import persist_llm_usage`（非本片引入）。开工快照 `~/hermesx_r3s13_pre_20261030_091910.tar.gz`（659 文件、SET_EQUAL=True）。详见 `documents/framework/architecture_migration_progress.md` §0.142 与 `documents/framework/src_migration_index.md` R3-S13 段
- [chore] 架构迁移 R3-S12（`src/core` 簇首批：`market_review_lock.py` + `market_review_runtime.py` 零改动下沉 `src/application/market/`）：两件在 application 口径下静态违规 **0**、私有成员 **0**，属「可零改动平移」的低风险批。**勘察取证**：`market_review_lock` 227 行（stdlib + `src.config.Config`；锁路径由 `Path(config.database_path).parent / "market_review.lock"` 推导、无 `__file__`；`fcntl`/`ctypes` 惰性 import）；`market_review_runtime` 128 行（`src.config` + `application.generation.catalog/ports`，懒 import `analyzer`/`notification`/`search_service` 全为 application）。**迁移**：`git mv`+`git reset -q` 两件，实现体零改动（lock 相对 HEAD、runtime 相对开工快照的 diff 均只有 docstring 来源说明）；**模块级可变状态语义保持**——`_market_review_lock`（`threading.Lock`）与 `_market_review_running` 仍为单一模块实例（`importlib.import_module` 身份一致性已验证），api/bot 同源 import 不产生双实例。**re-point**：9 文件 17 处（api 2 / bot 3 / main 2 / `application/market/daily_market_context.py` 1 / 测试 9，含 `import ... as` 模块对象形态与 `sys.modules` 替换键），代码面旧路径残留 0；`scripts/ci_gate.sh` 与打包配置均不含本件。**本片增量：`src/core` 5→3 件（余 `market_review.py`、`trading_calendar.py`、`pipeline.py`）；`src/application/market/` 新增 2 件**。守卫 `--check` exit=0、py_compile 11 件 OK、导入冒烟（新增 `src.infrastructure`/`data_provider`/`api.`/`bot.` 模块为空 + 单例身份 + 锁路径 + acquire/二次拒绝/release）OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted **204 passed/0 fail**、全量离线三步法 **31 failed / 5524 passed / 10 errors** 与基线 FAILED node-ID 集合 **IDENTICAL**（NEW=[]/GONE=[]）、ImportError 0；HEAD `8d98792d` 未变（零提交）。开工快照 `~/hermesx_r3s12_pre_20261030_090312.tar.gz`（Python tarfile、657 文件、SET_EQUAL=True）。**口径纠偏**：`.claude/reviews/survey-r3-core-legacy-schemas.md` 记载的 `is_market_review_running` 实际不存在（公开面为 `market_review_lock_path`/`try_acquire_market_review_lock(config)`/`release_market_review_lock(token)` + `MarketReviewExecutionLock`）。详见 `documents/framework/architecture_migration_progress.md` §0.141 与 `documents/framework/src_migration_index.md` R3-S12 段
- [chore] 架构迁移 R3-S11（根级 `src/md2img.py` 下沉 `src/infrastructure/reporting/img_render.py` 并完成 `ImageRenderPort` 端口化）：本件 141 行，顶层 import 仅 stdlib + 同层 `markdown_render`，惰性 import `imgkit`（可选）与 `src.config.get_config`（仅读 `md2img_engine`），无路径推导；tracked。**消费面口径纠偏**：index 原备注「两个消费者都在 application」实测为 1 application（`notification.py:2658` 惰性 import，必须端口化）+ 1 core（`pipeline.py:3516`，1 import + 3 调用；`src/core/` 仅禁 drivers，直连 infra 合法）。**端口化**：`application/notification/ports.py` 新增 `ImageRenderPort`（1 方法）+ 与 send port 同型工厂 seam（`set_image_render_port_factory` / `build_default_image_render_port`，未注册返回 `None`）；`infrastructure/reporting/image_render_port.py` 新增 `Md2ImgImageRenderPort`（经 `img_render` **模块属性**转发，patch 保真）；`bootstrap/notification.py` 新增 `configure_image_render_port()` 注册类本身（零参工厂），`main.py` / `bootstrap/api_lifecycle.py` / `tests/conftest.py` 会话级 fixture 三挂点（幂等）。**用例改动**：`NotificationService.__init__` 增 `image_render_port`、发送侧改调端口；未装配 → `None` → 沿用原「转图依赖不可用」文本回退与同一失败提示日志。**移动与 re-point**：`git mv`+`git reset -q`→`img_render.py`（除 docstring 外零改动，保留 `markdown_to_image` 符号与 `get_config().md2img_engine` 读取，受 `test_config_registry.py:1932` 源码断言约束）；15 处 re-point（13 `mock.patch` 串→新模块路径、1 路径字面量、1 注释）、`ci_gate.sh` 名单无本件无需改；新增 1 条正向回归用例（`test_send_uses_injected_image_render_port`）。**本片增量：根级 `src/*.py` 6→5（实测 5 件、含 `__init__.py`）；`infrastructure/reporting/` 新增适配器并下沉实现**。守卫 `--check` exit=0、py_compile 12 件 OK、独立进程导入冒烟（application `sys.modules` 无 `src.infrastructure.reporting*`）+ 端口行为差分 OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted **217 passed/0 fail**、全量离线三步法 **31 failed / 5524 passed / 10 errors** 与基线 node-ID `diff`(RC=0)/`comm -3`=0、无 ModuleNotFound/ImportError→**0 真实回归**；HEAD `8d98792d` 未变（零提交）。开工快照 `~/hermesx_r3s11_pre_20261030_082928.tar.gz`（Python tarfile、656 文件、SET_EQUAL=True）。详见 `documents/framework/architecture_migration_progress.md` §0.140 与 `documents/framework/src_migration_index.md` R3-S11 段
- [chore] 架构迁移 R3-S10（根级 `src/market_analyzer.py` 下沉 `src/application/market/` 并完成取数端口化）：本件 1896 行，顶层唯一越层依赖为 `data_provider.base.DataFetcherManager`（L36 导入、L149 构造，仅 4 处取数：`get_main_indices(region)` / `get_market_stats(purpose=)` / `get_sector_rankings(5)` / `get_concept_rankings(5)`）；`src.config` 在 application 属非禁入层，故保持 `get_config()` 不注入。**端口化**：`application/market/ports.py` 新增 `MarketReviewDataPort`（4 方法逐项对齐 manager 契约），`infrastructure/providers/market_review_provider.py` 新增 `DataProviderMarketReviewProvider`（直连 `DataFetcherManager`、每实例一个 manager；**不复用** `DataSectorRankingProvider`，避免 `data_provider.sector` 旁路的选源/健康/缓存差异）；`bootstrap/market.py` 新增 `configure_market_review()` 向用例模块 seam 注册**工厂**（非实例），`main.py` 与 `bootstrap/api_lifecycle.py` 各装配一次（幂等）；用例 `__init__` 增 `data_provider` 参数、`self.data_manager`→`self.data_provider`、4 处取数改口，未装配时 `_NullMarketReviewDataProvider` 返回空并只警告一次（等价原「全源失败」降级）。`git mv`+`git reset -q`→`src/application/market/market_analyzer.py`；perl `\b` re-point **7 文件 48 处**（35 import + **13 patch 字符串目标**：strategy 8 / generate_text 3 / intelligence 2）、`scripts/ci_gate.sh:10` 路径同步；`test_market_strategy.py` 3 行 `data_manager`→`data_provider`、`test_market_analyzer_generate_text.py` 静态源码扫描改读 `module.__file__`（教训：**路径字面量也是消费点**，`"src/market_analyzer.py"` 字符串不会被 import 形态的 grep 命中）。守卫首轮命中 application `forbid_private_members`（`__main__` 演示块跨对象调 `_generate_template_review`）→ 删去该 dev-only 演示调用。本片增量：**根级 `src/*.py` 7→6（实测 6 件、含 `__init__.py`）、`application/market` 与 `infrastructure/providers` 各新增 1 件；index 备注的「计算分离」为 deferral，本片不宣称完成**。守卫 `--check` exit=0、py_compile 13 件 OK、导入冒烟（application 模块不再拉入 `data_provider.base`）+ 端口行为差分（Stub 注入 4 方法取值一致 / Null 兜底空概览 / bootstrap 装配后为 `DataProviderMarketReviewProvider`）OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted **346 passed/0 fail**（strategy/review/light_service/intelligence/tickflow 60 + generate_text/api_contract/alert_worker/alert_api 286）、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID `diff`(RC=0)/`comm -3`=0、无 ModuleNotFound/ImportError→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s10_pre_20261030_013459.tar.gz`（Python tarfile、648 文件、SET_EQUAL=True）。详见 `documents/framework/architecture_migration_progress.md` §0.139 与 `documents/framework/src_migration_index.md` R3-S10 段
- [chore] 架构迁移 R3-S9（根级 `src/stock_analyzer.py` 下沉 `src/domain/analysis/` 并完成 `bias_threshold` 注入）：本件顶层仅 stdlib + `pandas`/`numpy` + `src.domain.decision.scale`，唯一跨层引用是 L27 `from src.config import get_config` 与 L623 `get_config().bias_threshold`（全文件仅 1 处）；domain 禁 `src.config`，故按索引前置改为构造参数注入：新增 `DEFAULT_BIAS_THRESHOLD=5.0`（对齐 `config/settings.py:968`）、`__init__(bias_threshold=None)` 存 `self._bias_threshold`、`_generate_signal` 改读属性、`analyze_stock(..., bias_threshold=None)` 透传、删 `get_config` import。调用方保行为：`src/core/pipeline.py` 用 `getattr(self.config, "bias_threshold", DEFAULT_BIAS_THRESHOLD)`（兼容 `SimpleNamespace` 桩 config）、`analysis_tools.py` 用 `get_config().bias_threshold`；`test_stock_analyzer_bias.py` **10 处 `@patch("src.stock_analyzer.get_config")` 全改 `setUp` 构造注入 5.0**（原值均 5.0、语义等价）并移除 mock import。`git mv`+`git reset -q`→`src/domain/analysis/stock_analyzer.py`；perl `\b` re-point **6 消费文件 16 处**、残留 0；`scripts/ci_gate.sh:10` 路径同步；`domain/analysis/__init__` 为 eager barrel、**不**聚合新件以避免 `import src.domain.analysis` 即加载 pandas/numpy。本片增量：**根级 `src/*.py` 减 1（本片后实测 7 件、含 `__init__.py`）、`src/domain/analysis/` 新增 `stock_analyzer.py`**。守卫 `--check` exit=0（domain 无 `src.config` 残留）、py_compile 7 件 OK、import 冒烟（默认/注入属性）OK、注入行为差分（bias=6%：5.0→严禁追高、7.0→可小仓介入）OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted（bias/rsi/realtime_indicators/agent_pipeline）**114 passed/0 fail**、受影响 pipeline 构造/可选服务用例复跑 **24 passed**、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`(RC=0)/`comm -3`=0→**0 真实回归**（首轮曾因 `SimpleNamespace` 桩 config 缺属性 +5 failed，已以 `getattr` 默认兜底修正并全量复跑）；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s9_pre_20261029_235318.tar.gz`（Python tarfile、647 文件、SET_EQUAL=True）。详见 `documents/framework/architecture_migration_progress.md` §0.138 与 `documents/framework/src_migration_index.md` R3-S9 段
- [文档] 架构迁移文档清理（§0.131 重复块去重）：`documents/framework/architecture_migration_progress.md` 中 §0.131 交接记录因前序 SearchReplace 假失败重试被写两次（详版 + 缩略版），经全量 `grep -E "^## 0\.[0-9]+ "` 取证为**唯一重复章节**（137 标题 / 136 唯一、`uniq -d` 仅命中该标题）；逐字比对确认缩略版为详版子集（差于 `protocols.py` 顶层 import 明细、re-export 全路径、SearchReplace 假失败备注），故保留详版、删除缩略版（原 3648–3664，**−18 行**）；§0.133“文档遗留缺陷备注”标记已解决、新增 §0.137 记录。仅文档改动、无代码/配置/工作流变更（Docs only, tests not run）；复核：删除缩略块后当即 136/136、收尾新增 §0.137 标题后 137/137（`grep -c` == `sort -u | wc -l`）、`uniq -d` 空、§0.131 七段结构完整、`## 0.132` 紧接其后。详见 `documents/framework/architecture_migration_progress.md` §0.137
- [chore] 架构迁移 R3-S8（根级 `src/report_language.py` 零改动下沉 `src/domain/shared/`）：承接 R3-S7 交付末尾默认建议的下一片，选取根级余件中唯一无待决项、可零改动整体平移的 `report_language`（1338 行）。顶层 import 仅 `re`/`typing` + `src.domain.decision.scale`（domain→domain 合法）、无 `__file__` 路径推导。消费面全仓无过滤勘察：33 处引用统一为 `from src.report_language import` 单一形态（无 module/patch 串/importlib/裸形态）、分布 30 文件；含 3 个 domain 件（`decision/__init__` docstring、`decision/action`、`market/daily_context_guardrail`）→核实 `scale` 不反向 import、`decision/__init__` 已惰性化（R3-S2）、`domain/shared/__init__` 无 eager 聚合→无循环。`git mv`+`git reset -q`→`src/domain/shared/report_language.py`；perl `\b` 批量 re-point 30 文件 33 处、代码残留 0；同步 `domain/shared/__init__.py` 成员清单 + `decision/__init__.py` docstring + 活契约 `docs/multi-strategy-contract.md` 3 处文件路径（`full-guide`/`_EN` 历史叙述沿用 R1 先例保留）。本片增量：**根级 `src/*.py` 10→9（report_language 下沉）、`src/domain/shared/` 新增 `report_language.py`**。守卫 `--check` exit=0、py_compile 全 31 件 OK、import 冒烟（新路径关键符号 + 循环风险件 `decision` 惰性 barrel/action/daily_context_guardrail）OK 无循环、CI 口径 flake8（E9,F63,F7,F82）=0、targeted（report_language/fallbacks/tw_report_consumption/multi_agent/signal_attribution/decision_stability/daily_market_context×2）**305 passed/1 failed**（失败属基线噪声集）、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`/`comm` 空=IDENTICAL→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s8_pre_*`（Python tarfile、651 现存文件、SET_EQUAL=True、权威回滚点）。详见 `documents/framework/architecture_migration_progress.md` §0.136 与 `documents/framework/src_migration_index.md` R3-S8 段
- [chore] 架构迁移 R3-S7（根级 report/prompt 簇 6 件整体下沉 application）：承接索引计划的 **S5 report/prompt 簇**，选取其中**无待决项**、依赖均对 application 合法的 6 件，作为一个互相依赖的干净簇一次平移。`git mv`+`git reset -q`（6 件均 tracked）：`analysis_context_pack_prompt`(521、纯 stdlib)→`src/application/reporting/context_pack_prompt.py`、`market_phase_prompt`(217、纯 stdlib)→`src/application/reporting/market_phase_prompt.py`、`market_structure_prompt`(186、stdlib+`report_language`+`domain.market.structure`)→`src/application/reporting/market_structure_prompt.py`、`market_phase_summary`(321、stdlib+`src.core.trading_calendar`、app→core 合法)→`src/application/market/phase_summary.py`、`analysis_context_pack_overview`(304、stdlib+簇内 prompt/summary+`domain.analysis.context_pack`)→`src/application/analysis/context_pack_overview.py`、`phase_decision_guardrail`(450、stdlib+簇内 prompt/summary+`report_language`)→`src/application/analysis/phase_decision_guardrail.py`。目标 `application/analysis`/`reporting` 两包 `__init__` 均不做 eager 聚合、`application/market/__init__` barrel 不含新件→无循环风险。re-point 24 消费文件（全仓 grep 取件后 perl 批量、pipeline 同文 4 件/api×2/analyzer/base_agent/executor/alert×2 等混合消费逐行正确改写；含 **test_market_phase_summary.py:149 `patch("src.market_phase_summary.build_market_phase_context")` 字符串目标**）；代码级 6 旧路径残留 0；非 `.py` 仅 gitignored `UNKNOWN.egg-info`、无 ci_gate/workflow/docker 硬编码。本片增量：**根级 `src/*.py` 16→10（report/prompt 簇 6 件下沉）、application 三子包共新增 6 件**。守卫 `--check` exit=0（forbid_private_members 未触发）、py_compile 全 28 件 OK、六新路径 import 冒烟全关键符号 OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted（overview/prompt/phase_prompt/phase_summary/guardrail/report_directives/executor/report_renderer）**140 passed/0 fail**、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`/`comm` 空=IDENTICAL→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s7_pre_*`（Python tarfile、646 现存文件、SET_EQUAL=True、权威回滚点）。详见 `documents/framework/architecture_migration_progress.md` §0.135 与 `documents/framework/src_migration_index.md` R3-S7 段
- [chore] 架构迁移 R3-S6（`src/formatters.py` 机械拆分为 domain 切片 + infra 渲染）：承接 §3-S3 最后一件、R3 中唯一需拆分的非平凡件。`src/formatters.py`（1085 行）按函数职责逐字拆两文件：切片侧（`re`/`typing`、零 markdown2、零 `src.`）→`src/domain/shared/text_chunking.py`，渲染侧（含唯一 markdown2 用户 `markdown_to_html_document` + `format_feishu/telegram/wechat/slack`）→`src/infrastructure/reporting/markdown_render.py`。**拆分根因**：`bot/platforms/discord.py:249` 只需纯分块函数 `chunk_content_by_max_words`，若整块落 infra 则 bot→src.infrastructure 违规、若落 domain 则 markdown2 渲染语义错位，故拆两使 discord 改指 domain（bot→domain 合法）。机械拆分脚本按 1-indexed 行区间逐字重组，`ast` 符号覆盖自检 `ORIG=48==CHUNK(26)|RENDER(22)`、MISSED/EXTRA/OVERLAP 全空、两侧零交叉依赖。re-point 16 消费文件（chunk 组 8 件 + render 组 5 件 perl、**3 混合 import SearchReplace 拆两条**：feishu_sender/feishu_reply_client/test_formatters）、`rm` 删旧件、代码级 `src.formatters` 残留 0（仅两新文件 docstring 叙述来源串）；patch 字符串扫描无 `src.formatters` 目标。本片增量：**根级 `src/*.py` 17→16、domain/shared 新增 text_chunking、infra/reporting 新增 markdown_render**。守卫 `--check` exit=0、py_compile 两新文件 OK、import 冒烟 identity + 功能 OK（切片 60 块、渲染出 `<h1>`）、CI 口径 flake8（E9,F63,F7,F82）=0、targeted（formatters/report_fixtures/feishu_stream）**49 passed/0 fail**、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`/`comm` 空=IDENTICAL→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s6_pre_*`（Python tarfile、642 现存文件、SET_EQUAL=True、权威回滚点）。至此 §3-S3（feishu_doc/formatters/logging_config）完全收官。详见 `documents/framework/architecture_migration_progress.md` §0.134 与 `documents/framework/src_migration_index.md` R3-S6 段
- [chore] 架构迁移 R3-S5（根级 `src/*.py` 两件干净 infra 平移）：承接 §3-S3 中**无待决项**的两件干净 infrastructure 平移（progress 标签 R3-S5 完成的是 §3-S3 内容、非索引计划的“S5 report/prompt 簇”）；`formatters` 需拆 domain+infra 两处、属唯一非平凡件，另立后续片。**S5a** `src/logging_config.py`（197 行、纯 stdlib）`git mv`（已跟踪）→新建 `src/infrastructure/observability/logging_config.py`，re-point 18 引用点（bootstrap/logging_setup.py 2 + test_logging_config import + **test_main_schedule_mode.py 15 处 `patch("src.logging_config.setup_logging")` 字符串目标**）。**S5b** `src/feishu_doc.py`（165 行、stdlib+`lark_oapi` SDK+`src.config.get_config`，infra 层仅禁 `api.`/`bot.`、import config 合法）`git mv`→新建 `src/infrastructure/reporting/feishu_doc.py`，re-point `main.py:959` + **test_main_portfolio.py:131/355 的 `patch("src.feishu_doc.FeishuDocManager")` 字符串目标**。两新父包 `__init__` 均 docstring-only、不 eager 聚合。**关键教训**：首次消费方探测误加 `grep import|from` 过滤、且 residual 仅搜部分目录 → 首轮全量出现 +1 新 FAILED（`module 'src' has no attribute 'feishu_doc'`，patch 目标串穿过旧模块）；补 re-point patch 字符串 + 改为全仓无过滤扫描后旧路径残留 0。本片增量：**根级 `src/*.py` 19→17、`src/infrastructure/` 新增 `observability`/`reporting` 两子包**。守卫 `--check` exit=0、py_compile 8 件 OK、import 冒烟 identity（logging_config.setup_logging identity + feishu_doc.FeishuDocManager 存在）OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted（logging/schedule/portfolio）**82 passed/0 fail**、全量离线三步法（修正后复跑）**31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`/`comm` 空=IDENTICAL→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s5_pre_*`（Python tarfile + NUL 字节集合校验、636 现存文件、SET_EQUAL=True、权威回滚点）。详见 `documents/framework/architecture_migration_progress.md` §0.133 与 `documents/framework/src_migration_index.md` R3-S5 段
- [chore] 架构迁移 R3-S4（已解锁三件“落 domain”干净下沉 + 清空 `src/schemas/`）：用户对 §6 余下三件均拍板 **domain**，合并为单片三移动 + 收尾。**S4a** `src/daily_market_context_guardrail.py`（288 行、仅依赖 stdlib+`src.report_language`、解决冲突 C-1）→`src/domain/market/daily_context_guardrail.py`、re-point 3（core/pipeline + 2 测试）。**S4b** `src/schemas/run_flow.py`（126 行纯 pydantic 快照 DTO）→`src/domain/analysis/flow_snapshot.py`、re-point 3（application/runtime/run_flow + api/v1/endpoints analysis/history）。**S4c** `src/schemas/bot_message.py`（纯 dataclass/Enum）→`src/domain/notification/bot_message.py`、re-point **30 消文件**（bot/application/core/tests）**排除 `tests/test_check_architecture.py:144` 合成样例串**、同步 `docs/bot-command.md`/`_EN.md` 活文档。**S4d** `src/schemas/` 清空后整体删除。**关键实况**：`run_flow.py`/`bot_message.py` 在 HEAD 未被跟踪（`git status` 为 `??`），改用普通 `mv` 而非 `git mv`（后者对未跟踪件报 fatal “not under version control”）。本片增量：**根级 `src/*.py` 20→19、`src/schemas` 2→0（目录消失）、`src/core` 仍 5**。守卫 `--check` exit=0、py_compile 7 件 OK、三新路径 import 冒烟 identity True、CI 口径 flake8（E9,F63,F7,F82）=0、targeted **156 passed/1 failed**（失败件属基线噪声集）、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`/`comm -3` 空=IDENTICAL→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s4_pre_*`（Python tarfile + NUL 字节集合校验、635 现存文件、SET_EQUAL=True、权威回滚点）。至此 §6 C-1/G-1 均关闭、R3 的 `src/schemas` 簇完全收官。详见 `documents/framework/architecture_migration_progress.md` §0.132 与 `documents/framework/src_migration_index.md` R3-S4 段
- [chore] 架构迁移 R3-S3a/R3-S3b（`skill_opinion_outcome_evaluator` 下沉 domain + 删 `src/schemas/__init__.py`）：承接 §6 G-1 收敛。**R3-S3a**——`src/core/skill_opinion_outcome_evaluator.py`（160 行）下沉的前置 `normalize_strategy_signal`（原在 `src/application/agent/protocols.py`）经勘察仅依赖 stdlib、零 `src.` 引用，抽到新建 `src/domain/decision/strategy_signal.py`，`protocols.py` 就地 re-export（`from src.domain.decision.strategy_signal import normalize_strategy_signal`）使 11 个旧消费方零改动、`is_valid_strategy_signal` 继续复用；evaluator `git mv`+`git reset -q`→`src/domain/decision/skill_opinion_outcome.py`、其 import 改直连 domain 路径、re-point `application/decision/skill_opinion_outcome_service.py` + `tests/test_skill_opinion_outcomes.py` 模块路径、残留 0。**R3-S3b**——`src/schemas/__init__.py`（30 行 eager barrel）经全仓 grep 再确认 `from src.schemas import X` 消费方 = 0，直接 `rm` 删除，`src/schemas/` 退化为命名空间包、`from src.schemas.bot_message/run_flow import ...` 仍可导入（import 冒烟证实）。本片增量：**根级 `src/core` 6→5、`src/schemas` 3→2（余 `bot_message`/`run_flow`）**。守卫 `--check` exit=0、py_compile 5 件 OK、命名空间包 + re-export identity（`ns is np_`）冒烟 OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted（`test_skill_opinion_outcomes`+`test_multi_agent`）**226 passed/1 failed**（失败件属基线噪声集）、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`/`comm -3` 空=IDENTICAL、无 ModuleNotFound/ImportError→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s3_pre_*`（Python tarfile + NUL 字节集合校验、635 现存文件、SET_EQUAL=True、权威回滚点）。G-1 现余 run_flow（目标路径与同名服务碰撞待决）与 bot_message（消费方含未迁 core/pipeline）两件待拍板；C-1 guardrail 仍待确认落点。详见 `documents/framework/architecture_migration_progress.md` §0.131 与 `documents/framework/src_migration_index.md` R3-S3 段
- [chore] 架构迁移 R3-S2b（`src/schemas/report_schema.py` 干净平移 application/analysis）：经用户拍板先执行 §6 中唯一无争议的干净件（run_flow/guardrail 先勘察提方案、不改码）。`report_schema.py`（纯 stdlib+pydantic、零跨层 import）消费方经普查全部在 application/tests（`application/agent/final_explanation`、`application/analysis/analyzer`、`src/schemas/__init__` + 4 测试）、无 domain/infra 消费→搬 `src/application/analysis/report_schema.py` 不破坏分层（`application/analysis/__init__` 不做 eager 聚合→无循环风险）；`git mv`+`git reset -q`，perl `\b` re-point **7 文件**旧 `src.schemas.report_schema`→`src.application.analysis.report_schema`、残留 0；非 `.py` 仅历史 survey/progress 叙述与 gitignored `SOURCES.txt`。本片增量：**`src/schemas` 4→3（余 `__init__`/`bot_message`/`run_flow`）**。守卫 `--check` exit=0、py_compile 8 件 OK、新路径+`src.schemas` barrel import 冒烟 identity True、CI 口径 flake8（E9,F63,F7,F82）=0、targeted 4 件 **63 passed/0 fail**、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff`/`comm -3` 空=IDENTICAL→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。**快照方法修正**：开工快照改用 Python `tarfile` + NUL 字节集合校验（macOS bsdtar `-T` 静默漏档陷阱），`~/hermesx_r3s2b_pre_20261029_205744`（635 现存文件、SET_EQUAL=True）为当前权威回滚点。同步勘察（不改码）：run_flow 目标路径与同名服务碰撞、guardrail 证据偏向 domain，均待拍板 §6 C-1/G-1。详见 `documents/framework/architecture_migration_progress.md` §0.130 与 `documents/framework/src_migration_index.md` R3-S2b 段
- [chore] 架构迁移 R3-S2（`src/schemas` 干净子集下沉 domain、R3 Epic 续推片）：承接 R3-S1，选取 R3 中无待决项、不依赖 §6 冲突 C-1/缺口 G-1/D-07 的 6 件 schemas。经 domain 合法性勘察（依赖 `src.utils.sanitize`/根级 `src.report_language`/pydantic 均不在守卫禁入清单）确认零改动可下沉，`git mv`+`git reset -q` 分落 `src/domain/{analysis/context_pack,decision/action,decision/profile,decision/scale,market/light,market/structure}.py`；全仓 perl `\b` 词边界 re-point 42 个消费文件旧 `src.schemas.<X>`→新 domain 路径、残留 0。**循环导入修复**：搬入后 `decision/action`→`src.report_language`→`decision/scale` 与 `src/domain/decision/__init__.py` 的 eager barrel 聚合形成 `report_language` 部分初始化环（targeted collection error 暴露），经全仓 grep 确认零外部 `from src.domain.decision import <Symbol>` barrel 消费后，将该 `__init__.py` 由 eager 改为 PEP 562 惰性 `__getattr__`（符号名→子模块映射 + `importlib` 惰性解析 + `TYPE_CHECKING` 静态导入 + `__dir__`）切断该环。doc 断言测试（`test_analysis_context_pack_docs.py` 断 `analysis-context-pack.md` 历史落地字面串）因不改被断言历史串而天然绿。本片增量：`src/schemas` 10→4（余 `__init__`/`bot_message`/`report_schema`/`run_flow`，跨 application 归属待 §6 G-1 拍板）。守卫 `--check` exit=0、py_compile 6 件 OK、新路径 import 冒烟 + 循环修复独立进程复现 OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted 9 件 **283 passed/0 failed**、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff` 空=IDENTICAL、无 circular/ImportError→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s2_pre_20261029_202807`（784 条目）。详见 `documents/framework/architecture_migration_progress.md` §0.129 与 `documents/framework/src_migration_index.md` R3-S2 段
- [chore] 架构迁移 R3-S1（`src/core`/根级纯领域下沉首批、R3 Epic 起手片）：选取 R3（`src/core` 9 + 根级遗留 + `src/schemas` 10）中无待决项、不依赖 §6 冲突 C-1/缺口 G-1/D-07 的“零改动下沉 domain”批。5 件经 import 勘察均 domain 合法（`enums`/`market_profile`/`market_strategy`/`backtest_engine` 纯 stdlib+Protocol、`market_context` 仅引 `src.domain.market`）`git mv`+`git reset -q` 分落 `src/domain/{shared/enums,market/context,backtest/engine,market/profile,market/strategy}.py`（`src/core` 无 eager `__init__`→无循环导入）；全仓 perl `\b` 词边界 re-point 27 个消费文件（均为规范点号导入/`import…as` 形态、无模块名形态/patch 串/sys.modules 裸键）旧路径→新 domain 路径、残留 0；非 `.py` 层（ci_gate/workflows/docker）经 grep 确认无这 5 件的 py_compile/import-smoke 硬编码。本片增量：根级 `src/*.py` 21→19、`src/core` 9→6。守卫 `--check` exit=0、py_compile 5 件 OK、新路径 import 冒烟 OK、CI 口径 flake8（E9,F63,F7,F82）=0、targeted 14 件 **467 passed/1 failed**（失败为基线既有 `test_event_monitor_keeps_manager_failure_summary_for_direct_quote_call`）、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线 node-ID 双向 `diff` 空=IDENTICAL→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交）。开工快照 `~/hermesx_r3s1_pre_20261029_194256`（772 条目）。详见 `documents/framework/architecture_migration_progress.md` §0.128 与 `documents/framework/src_migration_index.md` R3-S1 段
- [文档] 架构迁移 R1 后续文档债收尾（`docs/` 旧 `src/agent/*` 活文档路径回写、纯文档零代码）：R1 搬包删除 `src/agent/` 后，唯一描述当前实现位置的活契约 `docs/multi-strategy-contract.md` 仍引用 20 处已不存在的 `src/agent/*` 路径（`protocols.py`/`orchestrator.py`/`disagreement.py`/`skills/*`/`agents/decision_agent.py`），本片做纯前缀替换 `src/agent/`→`src/application/agent/`（20 个目标路径经 `find`/`test -f` 逐一核实存在）。其余 `src/agent/*` 引用经逐份判定为**历史叙述或迁移规格、刻意保留不改写**：`ARCHITECTURE_TARGET.md`（迁移规格本体）、`analysis-context-pack.md`/`run-diagnostics-p2.md`/`full-guide.md`/`_EN.md`（绑定 Issue #1381/#1386/#1391 当时改动）、`agent-stream-events.md`（`## Rollback` 段指引入变更当时的文件位置）。逆替换一致性证明回写仅动路径令牌、未伤及其它内容；`multi-strategy-contract.md` 无任何测试读取断言（**Docs only, tests not run**）；未迁移面维持 96。详见 `documents/framework/architecture_migration_progress.md` §0.127
- [chore] 架构迁移 R1-A6/A7（`src/agent/` 分层归位整簇收官、目录删除）：本片完成 A6 分片（A6-1 `AgentLLMPort` 端口 seam、A6-2 Codex/LLM 适配器物理迁 `infrastructure/agent_runtime/`、A6-3a `agent_backend` 拆（ABC/DTO 留 app、`LiteLLMAgentBackend` 去 infra）、A6-3b `factory` 拆（用例/缓存留 `application/agent/factory.py`、builder 去 `bootstrap/agent.py`）、**A6-4 `events.py` 端口化搬 `application/alert/`**——唯一禁入 `data_provider.realtime.base.get_realtime_quote` 镜像 alert 既有 `DailyBarFetcherPort` 范式新建 `RealtimeQuotePort`（返 `Any`）+ events 模块级 seam（未装配降级 None）+ infra `alert_realtime_quote.py::DataProviderRealtimeQuote` + bootstrap `configure_alert_realtime_quote()`（`build_alert_service` 幂等装配、API+worker 双覆盖））；**A6 收尾**经 R1-Q1 拍板将 `litellm_route_resolution.py`（零 IO/零 SDK）搬 `application/agent/`（偏离 §4.2、无需端口）；**A7** 删除旧包 `src/agent/`（`__init__.py` 惰性 `__getattr__` shim 经全仓 grep 确认零消费方、随目录一并删除、不留转发 shim；全类型 sweep 确认无代码/打包 hidden-import/动态 importlib/测试路径断言残留）。`src/agent/` 56 件全部归位 application/infra/bootstrap/domain；守卫 `--check` passed、`py_compile` 全改件 0、CI 口径 flake8（E9,F63,F7,F82）0、litellm route/llm_adapter import 冒烟 OK、targeted `test_agent_litellm_route_resolution`+`test_agent_models_api` **37 passed**、全量离线三步法 **31 failed / 5523 passed / 10 errors** 与基线计数一致、FAILED 集为同一基线噪声集→**0 真实回归**；HEAD `8d98792d` 未变（全程零提交、待收口统一对外提交）；纯内部分层归位 + 旧包收口，无用户可见/API/配置/通知行为变化。详见 `documents/framework/architecture_migration_progress.md` §0.120~§0.126 与 `documents/framework/src_migration_index.md` R1-A6/A7 段
- [chore] 架构迁移 R2-Q9/D-03（通知簇尾巴收尾片，R2 分层归位整簇收官后的两个遗留独立小片）：**Q9 `_send_dingtalk_chunked` 归属下沉**——该“按钉钉 markdown 协议向任意 url 分批 POST”的真实逻辑原住在 `CustomWebhookSender`（同时被自定义 webhook 的钉钉机器人分支与钉钉 Stream 会话回执路共用），现抽为包内中立共享模块 `src/infrastructure/notification/senders/dingtalk_post.py::send_dingtalk_markdown_chunked(url, content, max_bytes, *, poster)`（HTTP 发送经 `poster` 回调注入以复用调用方的认证/SSL）；`CustomWebhookSender` 删除 `_send_dingtalk_chunked` 方法、两处内部调用改直调共享 helper；`composite_port.send_dingtalk_chunked` 不再伸手调 `self._custom._send_dingtalk_chunked`私有，改注入 custom 的 post 原语直调共享函数（签名同时改为与 `NotificationSendPort` 协议一致的显式参数）。**D-03 `src/notification_noise.py`（406 行）物理下沉**——经全仓 grep 确认非死码（有 5 处生产消费者），按已授权默认落法 A `git mv` 至 `src/application/notification/noise.py`（仅依赖 stdlib、零跨层 import），re-point 8 处模块路径（生产 5：`config/registry.py`、`config/settings.py`、`application/notification/notification.py`、`application/alert/notification_diagnostics.py`、`application/runtime/system_config_service.py`；测试 3：`test_notification.py` import+patch 串、`test_notification_noise.py` import）；`config → application` 反向边经核实不触发守卫（`src/config` 无专入规则、仅禁 `api./bot.`，无需改 baseline），仅需同步活文档中旧文件名引用（`documents/product/实时告警中心/alerts.md`、`docs/full-guide.md`/`_EN.md`，均保留“原 `notification_noise.py`”注记）。未迁移面 97→96（仅 D-03 动一个根级件，Q9 新件属已完成 infrastructure 区不计入）；守卫 passed、`grep src.notification_noise` 代码残留 0、`py_compile` 全改件 0、CI 口径 flake8（E9,F63,F7,F82） 0、`config→application` 无环 import 冒烟 OK、Q9 targeted `test_notification`+`_sender`+`_dingtalk`+`feishu_stream` **209 passed**、D-03 targeted 含 `test_notification_noise`/`test_alerts_docs`/`test_system_config_api` 等批除基线既有失败外无新增、`ci_gate.sh deterministic` rc=0，全量离线三步法 **31 failed / 5523 passed / 10 errors**（FAILED 与 R2-B4/B5 基线 node-ID 双向 `comm -3` = **0 差**，10 errors 全为 `apps/hrs-web/scripts/test_wt` 既有 fixture）→ **0 真实回归**；纯内部依赖倒置 + 分层归位，无用户可见/API/配置/通知行为变化
- [文档] 架构迁移 R2-B6（通知簇文档同步、R2 分层归位整簇收官）：将描述当前结构的活文档路径与叙述同步至 B5 搬层后的实况——`ARCHITECTURE_TARGET.md` §4 目标表 `src/notification*`/`src/notification_sender/` 行与 §4.1 迁移 N 线叙述（原称“逐渠道发送实现仍留在 `src/notification_sender/`、解 14-mixin 继承归 P4、不宣称完成”已过时）改为 R2-B1~B6 收官实况（组合 + `NotificationSendPort`、sender 物理入 `src/infrastructure/notification/senders/`、纯规则/常量下沉 `src/domain/notification/`、bot 经 `ReplyClient` 解耦、默认端口 bootstrap seam 装配）；`docs/notifications.md` 兼容性排除说明的 4 个具体 sender 路径（wechat/slack/telegram/feishu）改指新位。纯文档口径同步，无代码/行为变更（Docs only, tests not run）；历史审计流水（progress.md 各 §0.x、index.md 历史 bullet、`.claude/reviews/` survey）作为当时快照保留不改写
- [chore] 架构迁移 R2-B5（通知簇 sender 物理搬层：`src/notification_sender/` → `src/infrastructure/notification/senders/`，R2 通知簇收官片之一）：**B5-1 先干净 application→sender 三条边**——① 纯常量 `WECHAT_IMAGE_MAX_BYTES` 从 `wechat_sender.py` 下沉到新件 `src/domain/notification/limits.py`（零 IO、禁入任何外层），sender 与 application 各按子模块精确导入；② 新建端口方法 `NotificationSendPort.send_stream_reply(chat_id, content)`，把原 `notification.py` 的 `_send_feishu_stream_reply`+`_send_feishu_stream_chunked`（建 `FeishuReplyClient`+按段落/分隔线分块）逐字搬入组合适配器 `composite_port.py::InProcessNotificationSendPort`，application 只经端口转调、保留同名 `_send_feishu_stream_reply` 转发壳（tests 以 `patch.object` 锚定）；③ 默认端口改 **bootstrap seam**（D-02 落法 A 的搬包后细化）：`ports.py` 新增 `set_notification_send_port_factory()`/`build_default_send_port(config)`（未注册优雅降级 None），新建 `src/bootstrap/notification.py::configure_notification_send_port()` 注册适配器类工厂，`main.py` 进程级 + `src/bootstrap/api_lifecycle.py` 双挂点装配，`tests/conftest.py` 增 session 级 autouse fixture 注册（测试进程等价入口，还原搬包前默认端口语义）。**B5-2 物理搬包**：`git mv` 15 个 tracked + `mv` 2 个 untracked（`composite_port.py`/`feishu_reply_client.py`）共 17 件 → `src/infrastructure/notification/senders/`，新建父包 `src/infrastructure/notification/__init__.py`（不 eager 聚合）。**B5-3 全仓 re-point**：`src.notification_sender`/`src/notification_sender/` 两种形态在 16 个 `.py` 机械改指 `src.infrastructure.notification.senders`（含 `tests/test_notification_sender.py` 95 条 patch 串、`test_system_config_service.py` 12、`test_dingtalk_sender.py` 5、`test_notification.py:637/2110` sleep patch、`test_config_registry.py:1935` 读盘路径锚点、`main.py`/`bootstrap`/`scripts/e2e_test_feishu_app.py` 真实 import、application/domain 侧 docstring）。`_send_dingtalk_chunked` 归属重排（R2-Q9）按拍板推迟为独立小片，本搬包片随 `custom_webhook_sender` 整体下沉、不改其归属。守卫 passed（按 `src/infrastructure/` 前缀自动分层、application 不再 import infra、`forbid_private_members` 无命中）、`grep -rn "notification_sender" bot/` = **0**（B4 不变量守住）、旧路径代码 grep = 0（仅余 `src/UNKNOWN.egg-info` gitignored 构建产物与刻意保留的历史迁移叙述 docstring）、`py_compile` 全改件 0、严格 flake8（E9,F63,F7,F82）0、干净进程冒烟（工厂注册→`build_default_send_port` 返回 `InProcessNotificationSendPort` 且含 `send_stream_reply`、未注册返回 None）、边缘形态核实（无 bare import/无打包 hidden-import 声明/无 importlib 动态串）、targeted 受影响 6 文件簇 **539 passed**、`ci_gate.sh deterministic` rc=0，全量离线三步法 **32 failed / 5522 passed / 10 errors**（FAILED 与 R2-B4 基线双向 `comm -3` 仅差 1 条 `test_provider_cache` 子进程 15s 超时计时用例——对 notification/bot/sender 零耦合 grep=0、隔离空闲复跑通过而高负载偶发超 15s 超时（非稳定复现），非本片回归）→ **0 真实回归**；**未迁移面 114→97**（notification_sender 17 件完成下沉）；纯内部分层归位 + 装配接缝，无用户可见/API/配置/通知行为变化
- [chore] 架构迁移 R2-B4（通知簇 bot 回执解耦，sender 原地不动）：新建窄端口 `src/application/notification/ports.py::ReplyClient`（`runtime_checkable Protocol`，仅声明 handler 实际使用的 `reply_text` 公开名），`bot/platforms/feishu_stream.py` 加 `from __future__ import annotations`、**删除运行期 `from src.notification_sender.feishu_reply_client import FeishuReplyClient`**（仅保留 `if TYPE_CHECKING:` 下从 application `ports` 引入 `ReplyClient` 做注解）、`FeishuStreamClient.__init__` 新增可选 `reply_client_factory`、新增模块级 `set_reply_client_factory()` 注册 hook、`_create_event_handler` 内原直接构造 `FeishuReplyClient(app_id, app_secret)` 改走工厂（实例工厂优先、回退模块工厂，两者皆 None 时 fail-fast 抛清晰 `RuntimeError`）；`bot/platforms/__init__.py` **去掉 `FeishuReplyClient` 的 re-export**（try-import/`except` 兜底/`__all__` 三处，避免保留会连带将其它飞书符号降级为 None）；`main.py::start_bot_stream_clients` 飞书分支在启动 Stream 前注册 `set_reply_client_factory(FeishuReplyClient)`（入口层允许 import sender，避免 `application → infrastructure` 违层与 bootstrap 不得 import bot 的限制）；`tests/test_feishu_stream.py:2` 改指真实路径 import（**1 行，D-04 选项 A**，不再在 bot 保留运行期符号）。`grep -rn "notification_sender" bot/` = **0**（B4 硬验收）、守卫 passed（`ReplyClient.reply_text` 公开名无 `forbid_private_members` 命中）、`py_compile` 五件 0、严格 flake8（E9,F63,F7,F82）0、干净进程冒烟（无运行期 `FeishuReplyClient`、`__all__` 不含该符号、`isinstance(Fake, ReplyClient)==True`、实例/模块/双 None fail-fast 三路径）、`ci_gate.sh deterministic` passed、targeted `test_feishu_stream.py`+`test_feishu_stream_ordering.py` **6 passed**，全量离线三步法 **31 failed / 5523 passed / 10 errors**（FAILED 31 条与 R2-B3 基线双向 `comm -3` 空=IDENTICAL）→ **0 真实回归**；未迁移面 114→114（B4 不新增/删除待迁移遗留件）；纯内部依赖倒置 + 入口装配，无用户可见/API/配置/通知行为变化
- [chore] 架构迁移 R2-B3（通知簇解继承 → 组合 + thin forwarder，sender 原地不动）：`src/application/notification/notification.py` 的 `NotificationService` 去除对 `src/notification_sender/` 下 14 个 Sender 类的多重继承（`__bases__` 收敛为 `(object,)`），发送能力改由新建端口协议 `src/application/notification/ports.py::NotificationSendPort`（23 方法公开名，无 `_` 前缀）声明、组合适配器 `src/notification_sender/composite_port.py::InProcessNotificationSendPort`（组合 14 Sender、`*args/**kwargs` 透传逐字转发）实现；适配器落 `notification_sender` 而非 application，以规避守卫对 `src/application/` 的 `forbid_private_members`（适配器需转调 Sender 的 6 个 `_send_*` 私有实现）。`NotificationService.__init__` 新增可选 `send_port` 参数、默认回退内置组合（D-02 落法 A，保住全仓 97 处零参构造、不引入 fail-fast），并将原由 `EmailSender`/`FeishuSender.__init__` 写入的 `_stock_email_groups`/`_feishu_send_as_file` 改直接从 config 取；新增 23 个同名 thin forwarder（含 6 个私有 `_send_*` 变体），保持 `src/core/pipeline.py`（19 处继承成员调用）、`scripts/check_env.py:377` 与测试 60 处 `patch.object` 锚点对外方法面与继承版逐字等价。`_send_dingtalk_chunked` 真实实现仍留在 `CustomWebhookSender`（Q9 归属重排推迟到 B5，本片不改）。B3 验收锚点 `tests/test_notification.py` **87 项一行不改全绿**；守卫 passed（application 无 `forbid_private_members` 命中、未 import infra）、`py_compile` 三文件 0、严格 flake8（E9,F63,F7,F82）0、干净进程冒烟 `BASES=(object,)` + 注入端口 forwarder 转调 True、确定性检查 `ci_gate.sh deterministic` passed、targeted 8 文件 **388 passed**（隔离跑时 `test_system_config_api` 2 条 generation 用例因未装配 `GenerationRuntimePort` 顺序失败，全序下通过、非本片引入），全量离线三步法 **31 failed / 5523 passed / 10 errors**（FAILED 31 条与 R2-B2 基线双向 `comm` 空=IDENTICAL）→ **0 真实回归**；纯内部分层归位 + 组合化，无用户可见/API/配置/通知行为变化
- [chore] 架构迁移 R2-B2 次子步（通知簇 endpoint 纯规则下沉 + 垫片删除，R2-B2 整体收官）：`src/notification_sender/gotify_sender.py:19` 的 `resolve_gotify_message_endpoint` 与 `ntfy_sender.py:19` 的 `resolve_ntfy_endpoint` 抽到新件 `src/domain/notification/endpoints.py`（AST 源码片段逐字比对确认一致，仅依赖 stdlib `urllib.parse` + `typing`，零 IO / 零外层引用）；两个 sender 改为 re-export 该函数（仅保留 `notification_sender/__init__.py:15,16` 包聚合面与外部按 sender 模块路径导入的兼容面；实测 tests/ 未按名字 patch 这两个函数，收敛归 R2-B5）；`src/notification_contracts.py` / `src/notification_routing.py` 两个 re-export 垫片**删除**（全仓 py 残留 0、非 py 面 0），`tests/test_notification_routing.py:6` 同步改指真源；application 侧 3 文件对 `src.notification_sender` 的 endpoint 跨层 import 全部改指 domain（`alert/notification_diagnostics.py`、`runtime/system_config_service.py`、`notification/notification.py` 各引入 2 个符号），为 R2-B5 sender 物理搬层扫清这些禁入边。根级未迁移件 24→22、未迁移面 115→113，`src/domain/` 已完成面 32→33；`src/notification_noise.py`（406 行）属 D-03 待拍板，不在 B2 范围。守卫 passed、严格 flake8（E9,F63,F7,F82）与改动件全量 flake8 均 0、干净进程 import 证明 endpoints 零外层依赖、sender re-export 与包聚合面同一性 True + 7 项 endpoint 语义断言通过、targeted 10 文件 **660 passed / 0 fail**（含 B3 验收锚点 `tests/test_notification.py` 一行未改全绿），全量 **31 failed / 5523 passed / 10 errors**（FAILED 31 条与 R2-B2 首子步基线双向 `comm` 空=IDENTICAL，ERRORS 10 条全为 `apps/hrs-web/scripts/test_wt` 既有 fixture）→ **0 真实回归**；纯内部分层归位 + 兼容面收敛，无用户可见/API/配置/通知行为变化
- [chore] 架构迁移 R2-B2 首子步（通知簇纯规则下沉）：`src/notification_contracts.py`（62 行）与 `src/notification_routing.py`（91 行）`git mv` 下沉为 `src/domain/notification/{contracts.py,routing.py}`，实现逐字保持（两件仅依赖 stdlib typing，零 IO / 零外层引用，符合守卫 domain 层禁入 `src.config`/`src.storage`/`src.services`/`src.infrastructure` 等约束）；新建 `src/domain/notification/__init__.py` 沿用 `domain/generation` 先例**不做 eager 聚合**（避免 `config -> domain` 拉起重依赖）；旧路径改为 re-export 垫片（对外符号 7 + 6 个，`__all__` 明确），生产消费方 5 文件 8 条 import 重指真源（`config/registry.py`、`config/settings.py`×2、`application/notification/notification.py`×2、`application/alert/notification_diagnostics.py`×2、`application/runtime/system_config_service.py`），`tests/test_notification_routing.py:6` 故意保留旧路径以持续验证垫片；全仓核实无字符串式 patch/`sys.modules` 引用、非 py 面（`scripts/`/`.github/`/`docker/`/打包配置/前端）零引用、`ci_gate.sh` 不涉及旧路径；守卫 passed、严格 flake8=0、新件全量 flake8=0、干净进程 import 证明 domain 零外层依赖、垫片 13 符号同一性 True、targeted 288 passed，全量 31 failed / 5523 passed / 10 errors（passed 与 R2-B1 后同数——本片不增删用例，FAILED 31 条与基线双向 IDENTICAL）→ **0 真实回归**；纯内部分层归位 + 兼容垫片，无用户可见/API/配置/通知行为变化。（B2 余下面已由次子步完成，见下条）
- [chore] 架构迁移 R2-B1（通知簇首片·死码清理）：删除 `src/notification_capabilities.py`（278 行渠道能力描述表）与其唯一消费者 `tests/test_notification_capabilities.py`（7 个用例）；全仓核实生产零消费者（py 仅命中该测试文件，`scripts/`/`.github/`/`docker/`/打包配置零引用），根级未迁移件 25→24、未迁移面 116→115；守卫 passed、严格 flake8=0、收集 5558 无 ImportError、全量 31 failed / 5523 passed / 10 errors（passed 较 R2-A4 基线精确减 7 == 被删用例数，FAILED/ERROR 双集与基线逐行 IDENTICAL）→ 0 真实回归；纯死码删除，无用户可见/API/配置/通知行为变化
- [文档] 架构迁移 P0 补账：文件级索引入库 `documents/framework/src_migration_index.md`（未迁移 5 簇逐文件「现状 / 目标落点 / 负责切片 / 备注」，并登记 4 处勘察报告间口径冲突与覆盖缺口 C-1、G-1~G-3）；`ARCHITECTURE_TARGET.md` 新增 §4.5 汇总与指向，收敛 §4.3 结尾要求的 P0 文件级清单欠账；待拍板决策清单汇总于 `.claude/reviews/pending-decisions-2026-10-28.md`（R1 12 项 + R2 10 项 + R3 10 项，已消解 5 项、剩 7 项需维护者决定）；修正 R2-Q6 对 `src/agent` 侧 `src.infrastructure.generation` 依赖的低估（原估 3 行，实测 5 个文件 / 8 条 import，其中 3 条会在 R1-A4/A5 搬入 `application/agent/` 时触发禁入）。Docs only, tests not run；已核对文中命令、文件路径与切片名与实际仓库一致。
- [chore] 架构迁移 R2-A4（生成链路 Epic 收官）：`src/llm/` 7 个实现文件（`backend_factory`/`errors`/`generation_params`/`litellm_backend`/`local_cli_backend`/`provider_cache`/`usage`）`git mv` 入 `src/infrastructure/generation/`，删除 4 个过渡 shim（`generation_backend`/`backend_registry`/`response_content`/`hermes`）与包聚合器，`src/llm/` 目录不再存在；适配器由单文件 `adapters.py` 拆为 `adapters/` 包（4 端口各一文件、同包直接依赖、保留调用时刻解析语义）；re-point 24 个（契约改指）+ 26 个（搬包改指）文件与 50 处源码路径 patch 锚点，测试语义零改动；`docs/LLM_CONFIG_GUIDE{,_EN}.md` 能力表路径同步；py_compile / 守卫 / CI-critical flake8 均 0，定向 20 文件 998 passed，全量 31 failed / 5530 passed / 10 errors 与 A3 基线同数同清单
- [chore] 架构迁移 P3/P4 持久化收口 Epic 收官（PP-1~PP-7）：`src/repositories/` 全部仓储按业务域下沉 `src/infrastructure/persistence/repositories/`，application 改为只依赖 `src/application/*/ports.py` 的 `*RepositoryPort` + bootstrap 注册的工厂 seam。① PP-1 intelligence：端口 13 方法 + 跨层异常/常量上收 ports + 工厂 hook；② PP-2 analysis：物理搬移片（`AnalysisRepository` 唯一活消费者是 market_light 已存端口的实现，application 侧 `self.repo` 为死依赖直接删）；③ PP-3 alert：`AlertRepositoryPort` 14 方法 + 单一装配漏斗 `build_alert_service()` 纯 DI；④ PP-4 portfolio：`PortfolioRepositoryPort` 32 方法 + 3 个跨层异常（`DuplicateTradeUidError`/`DuplicateTradeDedupHashError`/`PortfolioBusyError`）上收 ports 作单一真源 + 4 service 改 seam；⑤ PP-5 decision：4 端口（6/8/3/1）+ 3 个含 ORM 字段 DTO 上收 ports + `BacktestRepository.parse_analysis_date_from_snapshot` 纯逻辑下沉 `src/domain/analysis/analysis_context_snapshot.py` + 跨域复用 `StockRepositoryPort` 并在 `application/backtest/ports.py` 新增 stock seam；⑥ PP-6 quote：`stock_service` 删死依赖 `self.repo`、`stock_daily_window_resolver` 形参改端口，`stock_repo`/`backtest_repo` 两件下沉并清空根 barrel；⑦ PP-7 收口：删除根 `src/repositories/`（git 中已无文件）、守卫把 `src.repositories` 加入 application 层禁入前缀并补回归用例、根 `src/storage.py` 保留为 `DatabaseManager` 门面（已批准例外）、ADR §3.1/§3.2、`ARCHITECTURE_TARGET.md`、AGENTS.md 与相关 docstring 回写。全过程零提交（基线 HEAD `3ee519cf`），每片 py_compile + 守卫 passed + CI-critical flake8=0 + 定向簇 pytest + 全量离线三步法比对基线，最终 **32 failed / 5529 passed / 10 errors**（passed 较 PP-6 多 1 = PP-7 新增的守卫回归用例；失败相对基线新增仅 `test_provider_cache` 的 litellm 回环 15s 超时环境型 flaky，消失 0）→ **0 真实回归**；纯内部分层归位，无 API / 前端 / 配置 / DB schema / 部署 / 报告结构变化。
- [chore] 架构迁移 SA2（P 线 search Epic 收官·Provider 下沉与端口化）：承接 SA1 搬包过渡遗留的“8 Provider 真下沉 + 端口化 + 解 isinstance”，分四片守卫绿完成。① SA2-1 契约层：`SearchResult`/`SearchResponse` DTO 下沉新建 `src/domain/search/`（供 application 与 infra 双向消费、不违层），`application/intelligence/ports.py` 追加 `SearchProviderPort` + frozen `SearchOptions`；② SA2-2 解 isinstance：两处 `isinstance(provider, TavilySearchProvider/BraveSearchProvider)` 编排耦合改为经中性 `SearchOptions` 全量下发（各 Provider 只读自身支持字段、行为等价）；③ SA2-3a 装配接缝：`SearchService.__init__` 就地构造抽为模块级 `build_search_providers()`（行为逐字不变）；④ SA2-3b 物理搬层：`BaseSearchProvider` + 8 Provider（Tavily/SerpAPI/Bocha/Anspire/MiniMax/Brave/SearXNG）+ 网络工具（`_post_with_retry`/`_get_with_retry`/`fetch_url_content`）+ `build_search_providers` 整体下沉新建 `src/infrastructure/search/providers.py`；SearchService 不再直接 import/构造具体 Provider，改经 `bootstrap.intelligence.configure_search()` 注册的 provider-builder hook 构建（main.py + api_lifecycle.py 双挂点，未注册时优雅降级为空 provider 列表、沿用 analyzer/signal_scanner 先例）；annotations `List[BaseSearchProvider]`→`List[SearchProviderPort]`；测试 6 文件 import/patch-target re-point 至 infra 命名空间 + 模块顶层 `configure_search()`。**装配契约变更**：SearchService 从就地构造→经 hook（保 `SearchService(**keys)` 签名、约 34 处测试直接构造零改动）；若启动链路未调 `configure_search`，新闻搜索降级为不可用（告警明显、不崩溃）。守卫 passed（application 无 infra 引用）、CI-critical flake8=0、providers.py pyflakes F*=0、装配冒烟优先级/兜底逐字保持、搜索簇 153 passed、**全量离线三步法 31f/5529p/10e** FAILED 集与基线逐行 IDENTICAL、ERRORS 全 test_wt 既有 fixture→**0 真实回归**；§4.3 L255 “检索用例与第三方搜索分开”search 侧已收敛（image_stock_extractor Vision 侧仍待后续）；纯内部分层归位、无用户可见/CLI/API/部署/通知/报告结构变
- [chore] 架构迁移 SA1（P 线 search Epic·搬包过渡片）：`src/search_service.py` 直搬 `src/application/intelligence/search_service.py`（git mv，8 Provider 与网络工具暂留原文件）——唯一守卫禁入 `data_provider.us_index_mapping.is_us_index_code`（核实为 `src/domain/market/us_index_symbols` 薄再导出）改指真源；`SearchService` 内 4 处 `SearchService._x` 自类名私有接收按 §0.36 收口为 `cls.`（`_is_foreign_stock`/`is_index_or_etf` 两静态方法转 classmethod，调用点类名式/self 式均兼容）；搬入 application 后新暴露 `BaseSearchProvider` 键位统计 `super()._record_success/_record_error`（`super()` 非裸 self/cls、触发 forbid_private_members，纠正 P1 勘察“随 Provider 下沉自消”误判）按方式① 提升公开 `record_*`；re-point 生产 11 + 测试 11（perl 词边界，旧 `src.search_service` 不留 shim，含 test_bot_market_command sys.modules 裸键）；**顺带修复 `scripts/ci_gate.sh:9` 陈旧 `py_compile src/search_service.py`**（搬包后旧路径不存在、set -e 会拖断 backend-gate，同 N1/A3 非 py 层盲区教训）+ 产品文档 live-news.md 路径同步；守卫 passed、严格 flake8 0、全量 flake8 HEAD 190==当前 190 未新增、import 冒烟 WIRE_OK+旧路径 ModuleNotFoundError、targeted 262 passed、全量 31f/5529p/10e FAILED 集与基线 31 条逐行 IDENTICAL（仅 +1 已知 test_provider_cache litellm 回环 15s 超时 flaky、隔离三连跑 passed/failed 定性）、ERRORS 集与 t5e6 基线 IDENTICAL→0 真实回归；**本片属搬包过渡——8 Provider 真下沉 `src/infrastructure/search/` + `SearchProviderPort` 端口化 + 解 `isinstance(provider,...)` 编排耦合归后续独立 Epic，§4.3 L255 检索用例与第三方搜索分开未完成、不宣称完成**
- [chore] 架构迁移 A3（P 线 analyzer Epic 收官片）：`src/analyzer.py` 直搬 `src/application/analysis/analyzer.py`（git mv）+ 全量 re-point（perl 词边界扫 16 生产 + 32 测试旧 `src.analyzer` 路径不留 shim）——环校验通过（analyzer 不 import 包内兄弟件、__init__ 不 eager 聚合、getLogger(__name__) 无硬编码 logger 名）；**顺带修复 N1 遗留 CI 陈旧引用**：ci_gate.sh/workflows(ci・docker-publish・ghcr-dockerhub)/scripts/test.sh 硬编码 `src/notification.py`与`src.analyzer` 导入冒烟均改新路径（否则 backend-gate 直接拖断）；docs 4 md 实现位置同步；守卫 passed，全量 31f/5529p/10e FAILED/ERRORS 双集与基线 IDENTICAL→0 真实回归；analyzer Epic 完成 LLM 簇端口化+直搬，但 domain 纯规则簇（~20 决策稳定化函数）下沉未做、§4.3 不宣称完成（待后续专项）
- [chore] 架构迁移 A2（P 线 analyzer Epic 首片）：analyzer LLM 外部调用簇端口化收口 + 装配（analyzer 本体未搬，直搬 application/analysis 归 A3）——新建 `AnalyzerLLMPort`（`src/application/analysis/analyzer_runtime_ports.py`，4 方法）+ `AnalyzerLLMAdapter`（`src/infrastructure/providers/analyzer_runtime.py` 收纳 litellm Router/completion/no-proxy/fallback 定价）+ `bootstrap/analyzer.py` api_lifecycle/main 双挂点幂等装配；analyzer 删 4 导入 + seam fail-fast + `_legacy_router_provider_alias` 提模块级 + **删死函数 `get_stock_name_multi_source`**（全仓无调用方，其惰性 data_provider.base 为 analyzer 唯一守卫禁入项，随之清零）；tests 顶层 configure + 9 破 patch 串 re-point 适配器命名空间 + Wiring 2 用例；守卫 passed，全量 31f/5529p/10e FAILED/ERRORS 双集与基线 IDENTICAL→0 真实回归
- [chore] 架构迁移 N1（P 线首 Epic）：notification 搬包过渡直搬 `src/application/notification/notification.py`（git mv，保留 14-mixin 继承，解继承端口化归 P4，不宣称 §4.3 完成）——`reports_dir` `__file__` 随搬深两层改 `resolve().parents[3]`，re-point 生产 10 + tests 11 文件 111 处 + 功能文档 5 md，不留 shim；config/config_registry 经 P0 勘察拍板判定 §4.1 责任分离已达标收口出搬层线；守卫 passed，全量 32f/5528p/10e（+1 为 test_provider_cache litellm 回环捕获沙箱网络波动，与搬包零语义关联）其余与基线 IDENTICAL→0 真实回归
- [chore] 架构迁移 T5f：system_config_service §4.3 拆分 Epic 收官（F1 机械收口 28 静态提模块级 + F2 URL 安全 7 纯函数下沉 `src/domain/shared/url_security.py` + F3 三端口端口化 `ConfigProbePort`/`NotificationDispatchPort`/`RuntimeResetPort`（`src/application/runtime/system_config_ports.py` + `src/infrastructure/providers/system_config_runtime.py` 适配器收纳 requests/litellm/src.agent/notification_sender 13 渠道）+ F4 直搬 `src/application/runtime/`）——bootstrap 双挂点装配、re-point 生产/测试/docs 12+6 文件、不留 shim，ARCHITECTURE_TARGET 高耦合清单同步除名附注记；全量 31f/5529p/10e FAILED/errors 双集与基线 IDENTICAL→0 真实回归，`src/services/` 收口仅剩 `__init__.py`
- [chore] 架构迁移 T5e-4：alphasift_service 直搬 `src/application/analysis/`（T5e §4.3 拆分 Epic 收官）——git mv 同深度平移不留 shim，re-point 6 文件（endpoints/bootstrap/两个打包脚本 hidden-import/tests 147 处），ARCHITECTURE_TARGET 高耦合清单同步删除已完成条目；全量 31f/5527p/10e FAILED/errors 集均与基线 IDENTICAL→0 真实回归，`src/services/` 余 __init__+system_config 两件
- [chore] 架构迁移 T5e-2/3：alphasift §4.3 拆分主体——HRS 桥与纯规则件下沉 `src/infrastructure/providers/hrs_alphasift_bridge.py` + `src/domain/analysis/`（alphasift_paths/hrs_analysis_summary，54 defs ast 归一比对保真），新建 `AlphaSiftRuntimePort`（application/analysis/alphasift_ports.py，9 方法：contextmanager 三件套/strict-isinstance 双语义 provider 判定/config Any 收口）+ `bootstrap/alphasift.py` 双挂点装配，alphasift_service 收口 3,605→1,849 行（seam fail-fast，端点契约逐字不变），tests 约 52 处 re-point + Wiring 用例；全量 31f/5527p/10e FAILED 集与基线 IDENTICAL→0 真实回归
- [chore] 架构迁移 T5d：intelligence_service 两段式整改（14 处私有收口 + 快讯/日历源经 NewsSourcePort 端口化、bootstrap 双挂点装配）并直搬 src/application/intelligence，re-point 11 py + 2 产品文档
- [chore] 架构迁移 T5c：stock_code_utils 四个纯代码规则函数下沉 src/domain/market（stock_codes/us_index_symbols 单一真源）并直搬 application/quote，data_provider 保持 legacy import 面，re-point 29 文件；顺带修复 base.py 两处 S2f 线漏 re-point 的既有断链
- [chore] eod_picker 全市场快照端口化 + 直搬 application/analysis（**T 线 T5b**，真实改变文件位置；T0 判 3 处禁入=快照三源取数（分时已在 S2e 下沉 quote 仅剩委托），按 B4c/S2e 先例回退链编排留用例层、三源实现经新建 `MarketSnapshotPort`（quote/ports，DataFrame 形状例外——全市场体量转 dict 性能坍塌）绑定新建 `DataProviderMarketSnapshotSource` 适配器（AkshareFetcher 单例收纳至适配器、缓存共享语义等价）；用例加模块级 seam setter（幂等）/未装配→None（与迁移前三源全失败语义一致）、`get_realtime_quote_snapshot` 保名保签名不破 `signal_scanner_service:292` 消费方；`configure_market_snapshot()` + api_lifecycle/main 双挂点；git mv src/services→src/application/analysis（basename 保留、目标 L216）；re-point 6 类文件（eod_picker.py 端点模块属性形态 + signal_scanner + 2 测试 import + documents/product/尾盘选股/eod-picker.md 锚点×3 含 ADR 合规行顺手精确化）旧路径 0 残留；交易日历 `import akshare` 属三方库非禁入留 P4；2 既有 patch data_provider 用例改假端口+calls 序断言、新增 8 端口化用例（未装配降级/run RuntimeError/setter 幂等/三源回退链×2/全空终态/adapter 透传/adapter akshare 单例）；git mv 仅暂存至 index、未 commit；端点契约逐字不变；py_compile 十件、守卫 --check passed、7 模块冒烟无环+旧路径 ModuleNotFoundError+装配链幂等、flake8 0、targeted 44 passed、全量 32f/5519p/10e（计数自洽 5512+8−1）FAILED 集与基线仅 +1 既有 flaky（隔离复跑 passed）→0 真实回归；**下一步 T5c stock_code_utils 纯函数下沉 domain 后直搬 application/quote**）
- [chore] report_renderer 零命中直搬新建 application/reporting + T5 勘察分组（**T 线 T5a**，真实改变文件位置；T5 勘察把 `src/services/` 余 6 件分组：report_renderer 探针 0 禁入/0 私有直搬（L226 拆分注记属 P4 同 T3 先例、不宣称拆分完成）、eod_picker 3 处全市场快照→端口化、stock_code_utils 4 纯函数→下沉 domain 后直搬 quote、intelligence_service 14 私有收口+ORM Protocol+news 端口两段式、alphasift/system_config 属 §4.3 L231 拆分对象需另立 Epic；本片新建 reporting 包（__init__ 不 eager 聚合）+`git mv` basename 保留+re-point 5 文件（notification.py 3 函数内 import、test_report_renderer/test_signal_attribution_e2e/test_notification 的 import 与 @patch 串、docs/multi-strategy-contract.md 锚点×2）旧路径 0 残留；**搬包新坑**：`_resolve_templates_dir` 以 `__file__` 深度推导仓库根，搬深一层致 Jinja2 模板错位、targeted 首跑 26 failed 真实回归→修正 `parents[3]`（对齐 application/quote REPO_ROOT 惯例）并确立"搬包片必须全文件审计 `__file__`/`parents[N]` 路径推导"检查项；git mv 仅暂存至 index、未 commit；render() 契约逐字不变；py_compile/守卫 --check/冒烟+旧路径 ModuleNotFoundError/flake8 0/修正后 targeted 121 passed/全量 31f/5512p/10e FAILED 集与基线逐行 IDENTICAL→0 真实回归；**下一步 T5b eod_picker 端口化**）
- [chore] social_sentiment_service 收口 11 处自类名接收者 + 直搬新建 application/intelligence（**T 线 T4**，真实改变文件位置；T0 探针命中 `SocialSentimentService._coalesce` ×11——@staticmethod 内以类名调同类 @staticmethod、守卫仅豁免裸 self/cls 故计私有访问→收口为模块级私有函数（裸调用属 Name 天然豁免），11 调用点+4 测试直调同步裸化、删类内 @staticmethod 不留委托 shim；新建 `src/application/intelligence/` 包（__init__ 不 eager 聚合，T1/S2d 惯例）+`git mv` basename 保留；re-point 3 文件（pipeline.py:66 import + 测试 import/8 @patch 串 + documents/product/行情资讯/live-news.md 锚点）全仓（含 data_provider/scripts）旧路径 0 残留；api.adanos requests 直连同 S2e 先例留 application、收敛归 P4 不宣称完成；git mv 仅暂存至 index、未 commit；对外接口逐字不变；py_compile/守卫 --check/冒烟行为断言/flake8 0/targeted 64p(1 基线既有 failed)/全量 31f/5512p/10e 与基线仅 +1 既有 flaky（隔离复跑 passed）→0 真实回归；**下一步 T5+ 整改件按 §4.3 逐件另片**）
- [chore] image_stock_extractor 零禁入直搬 application/analysis（**T 线 T3**，真实改变文件位置；目标 §4.1 L228 给 `application/analysis` 或 `infrastructure/generation` 双落点+注'业务提取流程与 Vision LLM 调用分别处理'，T0 探针判零守卫禁入（仅 src.config/src.llm/litellm/json_repair、对 application 非禁入）/零跨对象私有、且不在 §4.3 高耦合拆分清单 L231（L255 拆分属 P4 生成收敛优化非守卫阻断）→按 S2e intraday（requests 直连留 application、网络收敛留 P4）与 S1 stock_index_remote_service 先例**整体直搬 application/analysis、Vision LLM 拆分留后续 P4**、不宣称拆分完成；`git mv` src/services→src/application/analysis（basename 保留、纯 R100、**未触 EXTRACT_PROMPT 内容**故 AGENTS prompt 附贴规则未触发），包 __init__ 不 eager 聚合；re-point 3 文件（api/v1/endpoints/stocks.py + tests/test_image_stock_extractor_litellm.py import+30 @patch 串 + tests/test_analysis_api_contract.py import+2 @patch 串）全仓 py 点号残留 0；治理文档旧路径顺手修正（AGENTS.md L220 + .github/PULL_REQUEST_TEMPLATE.md L139-140 + docs/image-extract-prompt.md L3→check_ai_assets OK），src/config/settings.py 仅注释提及 basename（保留仍准确）不改、ARCHITECTURE_TARGET.md 依 D4 不改；git mv 仅暂存至 index、未 commit；对外接口/EXTRACT_PROMPT 逐字不变；py_compile 四件、守卫 --check passed、import 冒烟无环+旧路径 ModuleNotFoundError、targeted 130 passed、flake8 0、全量 32f/5511p/10e FAILED 集与基线仅 +1 既有 flaky test_provider_cache litellm（隔离复现 15.10s timeout、零交集），除此 0 真实回归；**下一步 T4 social_sentiment 先收口 11 处自类名接收者**）
- [chore] runtime 对 run_flow+run_diagnostics 零禁入直搬（**T 线 T2**，真实改变文件位置；二者 T0 判零守卫禁入/零跨对象私有，`git mv` src/services→src/application/runtime（basename 保留，包 __init__ 已声明不 eager 聚合、消费方全路径导入→无环），二者互引 run_flow L14 导入 run_diagnostics 的 3 公开名转包内 import；re-point 点号形态 **21 文件**（10 生产 endpoints.analysis/intelligence+analysis_service+read_model+daily_market_context+task_queue+market_review+pipeline+market_analyzer+search_service + services 余件 intelligence_service + run_flow 包内 import + 9 测试）+ @patch 串 test_run_flow.py:940 `_local_timezone` + docs 路径锚点 run-diagnostics-p1/p2/p3.md + src/schemas/run_flow.py docstring 消费方指向（CHANGELOG 历史条目不动）。**关键**：首轮 import 冒烟 8 模块 FAIL 暴露 `data_provider/base.py:30` 既有跨层引用 run_diagnostics（非本片新增，data_provider 不在守卫 SCAN_ROOTS 内），re-point 作用域初次仅扫 api/bot/src 漏 data_provider → 补改指 `src.application.runtime.run_diagnostics` 后全仓点号残留 0、21 模块全绿；git mv 仅暂存至 index、未 commit；对外行为零变更；py_compile 十五件、守卫 --check passed、import 冒烟 21 模块无环+旧路径 ModuleNotFoundError、targeted 9 文件 198 passed、flake8 0、全量 31f/5512p/10e FAILED 集与基线 s039_run2 逐行完全一致（无新增用例）→0 真实回归；**下一步 T3 image_stock_extractor 判 §4.3 拆分、T4 social_sentiment 收口自类名接收者**）
- [chore] analysis 域 3 件零禁入直搬 + 建包（**T 线 T1**，S 线收官后 services 清点首刀；T0 假想落点守卫探针（AST 含函数内导入+私有访问）把 `src/services/` 余 14 件分为直搬 6/收口 1/整改件：本片 3 件零禁入零跨对象私有直搬——新建 `src/application/analysis/` 包（__init__ 不 eager 聚合防 config→application 循环，S2d/S2f-1 惯例），`git mv` analysis_service/analyzer_service（全仓 0 生产导入的薄封装件，随片直搬防孤岛）/analysis_context_builder（basename 保留）；re-point 8 文件（task_queue/endpoints.analysis/pipeline + 4 测试 + docs/run-diagnostics ×2 + SKILL.md ×4 产品集成文档，check_ai_assets OK）；`src/services/__init__.py` 死名清理（删 `AnalysisService` 惰性映射与 `__all__` 死名 `TaskService`，保留可达名 `get_task_service` 改指 `src.application.runtime.task_service`）；git mv 仅暂存至 index、未 commit；对外行为零变更；py_compile 八件、守卫 --check passed、import 冒烟 9 模块无环+三行为断言全对、targeted 12 文件 494 passed、flake8 0、全量 31f/5512p/10e FAILED 集与基线 s039_run2 逐行完全一致（无新增用例）→0 真实回归；**下一步 T2 runtime 对 run_flow+run_diagnostics（24 文件爆破半径）**）
- [chore] portfolio_service 归一化改指 + 实时行情端口化 + 搬包（**S 线 S2f-3**，portfolio×3 末片，真实改变文件位置；件 1749 行 3 处守卫禁入：L14 `data_provider.base` canonical/normalize（8 使用点）→`stock_code_utils` 别名导入同体改指（B4a 同型）；L1200 `prefetch_realtime_quotes` + L1230 `get_realtime_quote(log_final_failure=False)`（读 `.price`/`.source.value`）→RealtimeQuotePort 不干净复用（无 source/模块函数 vs manager/无 prefetch）按 §2 L46 新建 `PortfolioRealtimeQuotePort`+适配器 `DataProviderPortfolioRealtimeQuote`（每调用新建 manager 逐字保 #1803 并发语义、异常上抛由用例降级保 warning 行为）+模块级 seam（H3b/S2f-2 同型）+`bootstrap.configure_portfolio_service_realtime` 双挂点；`_fetch_realtime_position_price` 保名保签名（5 处 @patch 目标不变）、float/>0 校验留应用层；`normalize_symbol` 提升公开（§2 L42，alerts 跨对象私有）；`git mv` src/services→src/application/portfolio，re-point 7 生产+~9 测试（含路径锚点与 doc-contract）旧路径 0 残留；全量首跑捕获包级循环导入（decision↔portfolio eager __init__ 环、入口顺序敏感）→按 S2d 断环惯例修（risk 对 DecisionSignalService 改 TYPE_CHECKING+两运行时点函数内惰性导入）；git mv 仅暂存至 index、未 commit；对外行为零变更，未装配优雅降级；新增 tests/test_portfolio_service_realtime_port.py 16 passed、targeted 14 文件 411 passed、py_compile 十三件、守卫 --check passed、多入口顺序冒烟 7/7 无环、flake8 0、全量 31f/5512p/10e FAILED 集与基线 s039_run2 逐行完全一致→0 真实回归；收官快照修正 quotepath 中文路径漏抓（371==371）；**S2f portfolio×3 子片与 S 线 services 余件收尾 Epic 收官**）
- [chore] portfolio_risk_service 板块归属取数端口化 + 搬包（**S 线 S2f-2**，portfolio×3 第二片，真实改变文件位置；件 558 行唯 1 守卫禁入 L458 `DataFetcherManager`（仅 `manager.get_belong_boards(symbol)` 一处调用）。无现成端口覆盖板块归属、RealtimeQuotePort 字段不含 boards→按 §2 L46 优先复用不成立时才新建，新建独立 `application/portfolio/ports.py::BelongBoardsPort`（`get_belong_boards(*, code) -> list[dict]`，best-effort）；取数仅经 `_fetch_belong_boards` 单入口、tests 直接 patch 此法（不测真实取数）→端口塞进方法内部并保名（patch 目标不受影响）；无 `self.__class__` 自共享坑；3 构造点均独立 `PortfolioRiskService()`→采模块级 seam（H3b/S2c/S2e 同型）非构造注入，保持构造签名不变。新建适配器 `infrastructure/providers/portfolio_belong_boards_provider.py::DataProviderPortfolioBelongBoards`（惰性 `from data_provider import DataFetcherManager`，SDK/数据源缺失或调用异常→空列表，选源/回退/限速仍归 data_provider，ADR-001）+ `bootstrap/portfolio.py::configure_portfolio_risk_belong_boards()` 双挂点（api_lifecycle serve 路径 + main CLI/bot 路径）。件加模块级 seam `_belong_boards_port`/`set_belong_boards_port`（幂等，仅非 None 覆盖）/`_get_belong_boards_port`，删 `self._data_manager`/`_data_manager_init_error` 与整个 `_get_data_manager`，重写 `_fetch_belong_boards` 走端口（未装配/异常/非 list→空，与迁移前 DataFetcherManager 初始化失败降级语义等价）；`git mv` src/services→src/application/portfolio（保留 basename）。re-point 三生产（api/v1/endpoints/portfolio.py:40 + src/agent/tools/data_tools.py:568 + src/application/portfolio/portfolio_alerts.py:17）+ 四测试（test_portfolio_pr2.py:30 + test_config_registry 源文件路径锚点 1649/1705 与 import 1674 + test_data_tools_portfolio_snapshot @patch 串 101/116），旧路径功能引用 grep 0 残留；git mv 仅暂存至 index、未 commit；对外行为零变更。新增 tests/test_portfolio_risk_belong_boards_port.py 10 passed（未装配降级/list 透传/异常/非 list/setter None 幂等 + 适配器 best-effort×4 + configure 装配）；py_compile 十件、守卫 --check passed（0 命中）、import 冒烟无环+端口行为实测全对、targeted 142 passed、flake8 0、全量 31f/5495p/10e，FAILED 集与基线 s039_run2 逐行完全一致（本轮 litellm flaky 通过；10 errors 为 apps/hrs-web/scripts/test_wt 既有 fixture 缺失、与 portfolio 无关；passed 5476→5495 系新增用例）→0 真实回归）
- [chore] portfolio_import_service 归一化改指 + 搬包（**S 线 S2f-1**，portfolio×3 首片，真实改变文件位置；S2f 经用户拍板按整改型分 3 子片。件 448 行唯 1 守卫禁入 L15 `data_provider.base.canonical_stock_code`（L321 解析 broker CSV 导入行证券代码，属输入边界）→归一化改指 `src.services.stock_code_utils.canonical_stock_code_for_input`（与 `canonical_stock_code` 同体的薄封装，B4a/H3a/D1/R4 同型）；`src.repositories.PortfolioRepository`/`src.services.portfolio_service` 对 application 非禁入保留。**修搬包命中 `forbid_private_members`**：L93–97 自共享类状态原经 `self.__class__._shared_*`（守卫仅豁免裸 `self`/`cls` 接收者）→4 处命中；读改 `self._shared_x`（实例查找回退类属性，逐字等价）、唯一类属性写收拢新 `@classmethod _mark_registry_initialized`（§0.36 classmethod 同型）→守卫 0）；`git mv` src/services→src/application/portfolio（保留 basename），api/v1/endpoints/portfolio.py:39 + tests/test_portfolio_pr2.py:29 两处点号式 re-point 旧路径 grep 0 残留；application/portfolio/__init__.py 不改（不 eager 聚合，经子模块全路径导入避循环）；git mv 仅暂存至 index、未 commit；对外行为零变更（导入解析结果不变、共享注册表跨实例语义不变）；py_compile 三件、守卫 --check passed、import 冒烟无环+行为实测（registry 3 项/两实例共享同一字典对象/初始化标志经 self与type 均 True）全对、targeted test_portfolio_pr2 24 passed、flake8 0、全量 32f/5484p/10e 与基线 FAILED 集仅 +1 既有 flaky test_provider_cache litellm 超时（与 S2e 同源、零关联），除此 0 真实回归）
- [chore] intraday_timeline_service 取数端口化 + 私有提升公开（**S 线 S2e**，真实改变文件位置；件 305 行唯一守卫禁入为回退路径 `data_provider.stocksdk_bridge`（直连失败后回退 stock-sdk 桥接取分时）；主路径 requests 直连经先例判定（S1 直搬的 stock_index_remote_service 本身 import requests 留 application/quote）→只端口化桥接回退、保留 requests 直连（网络收敛留 P4）。新建 `IntradayTimelineBridgePort`（application/quote/ports.py）+ `DataProviderStocksdkTimelineBridge`（infrastructure/providers/stocksdk_timeline_provider.py，惰性导入 get_stocksdk_client、best-effort 不可用/异常返回 None）；件删 data_provider import、加模块级 seam `set_timeline_bridge_port`（幂等）/`_get_bridge_port`、`_fetch_trends_via_bridge` 改调端口（未装配→空、异常→debug+空，与既有“桥接不可用→空”降级语义一致）；`src/bootstrap/quote.py` 新增 `configure_intraday_timeline_bridge()` + api_lifecycle/main 双挂点（setter 幂等，覆盖 serve+CLI/bot 全部入口）。发现 `eod_picker_service` L37/L410 跨层导入本件私有 `_fetch_intraday_trends`，按 §2 提升为公开 `fetch_intraday_trends`（全仓同步含测试 monkeypatch seam 名，旧名 0 残留）；`git mv` src/services→src/application/quote（保留 basename），stocks.py:45 re-point 旧路径 grep 0 残留；git mv 仅暂存至 index、未 commit；test 桥接回退改用假端口（去 data_provider patch）+新增未装配降级用例+适配器 best-effort 四分支用例；py_compile 十件、守卫 --check passed、import 冒烟含 src.config.settings 无环、targeted（intraday 8 + eod_picker 16 + stock_service 7）31 passed、flake8 0、全量 32f/5484p/10e 与基线 FAILED 集仅 +1 既有 flaky test_provider_cache litellm 超时（隔离复跑同 FAILED、零关联），除此 0 真实回归）
- [修复] stock_service 搬包 + 端口化并修复 `/api/v1/stocks/{code}/history` 恒空（**S 线 S2d**，用户授权的行为变更；原 `get_history_data` 引用 `KLineResult` 不存在的 `.points`，生产必抛 AttributeError 被宽 `except` 吞 → /history 一直返回空；现委托既有 `QuoteService.get_kline`（复用同一 `QuoteProviderPort`，顺带消除与 QuoteService 的 K 线取数重复），端点恢复返回真实日 K 线（period 仍限 daily）；realtime 无既有端口，新增 `RealtimeQuotePort` + `DataProviderRealtimeQuoteProvider`（逐字段保持响应契约）；`git mv` src/services→src/application/quote，`bootstrap/quote.py` 新增 `build_stock_service()`，stocks.py 端点×2 re-point，`src/services/__init__.py` 清理惰性映射；修复搬包夹带的循环导入（StockService 依赖 repositories→storage→config，不并入 application/quote/__init__ 顶层聚合）；补 tests/test_stock_service.py 7 用例；py_compile/守卫 --check/import 冒烟无环/targeted 162 passed/flake8 0/全量 32f/5482p/10e 与基线 FAILED 集仅 +1 既有 flaky test_provider_cache litellm 超时（零关联），除此 0 真实回归）
- [chore] S2c name_to_code_resolver 取数端口化 + 搬包（**S 线 S2 真实取数端口化件**，真实改变文件位置；守卫禁入的 `data_provider.code_search.base.search_codes`（仅 `_search_remote_name_to_code` 使用）改为复用既有 `QuoteProviderPort.search_codes`（**零新增适配器**），模块级 seam `set_code_search_port`/`_get_code_search_port` + 未装配/失败优雅降级空 dict（与原 code-search 失败语义一致，H3b/D4 同型）；`src/bootstrap/quote.py` 新增 `configure_name_to_code_resolver()`（复用 DataProviderQuoteProvider）+ api_lifecycle/main 双挂点（覆盖 API/CLI/bot 全部 resolve_name_to_code 入口，setter 幂等）；`git mv` src/services→src/application/quote（保留 basename）；re-point 消费方 ×6（analysis.py + bot/dispatcher.py + import_parser.py + 3 测试含 @patch 串）旧路径 grep 0 残留；git mv 仅暂存至 index、未 commit；py_compile 七件、守卫 --check passed、端口化行为冒烟（降级/装配/dict 消费）全对、targeted 59 passed + 3 基线预存（patch 不存在的 _get_akshare_name_to_code、与路径无关）、flake8 0、全量 32f/5475p/10e 与基线 FAILED 集仅 +1 既有 flaky test_provider_cache litellm 超时（零关联、§0.72/§0.75 同源），除此 0 真实回归）
- [chore] S2b stock_daily_window_resolver 搬包（**S 线 S2 轻整改件**，真实改变文件位置；守卫禁入的 ORM 注解 `src.infrastructure.persistence...StockDaily`（仅 L19/L20 使用、`from __future__ import annotations` 惰性求值）改指既有 `src/core/backtest_engine.DailyBarLike(Protocol)`（date/high/low/close 恰为消费面并集），按 D4“优先复用既有端口、不新增平行实现”**不新建重复 Protocol**；`src.repositories`（非禁入设计债）保留；`git mv` src/services→src/application/quote（保留 basename）；re-point 消费方 ×3（backtest/service.py + decision/skill_opinion_outcome_service.py + test）旧路径 grep 0 残留；git mv 仅暂存至 index、未 commit；py_compile 四件、守卫 --check passed、import 冒烟验新路径/旧路径 ModuleNotFoundError/DailyBarLike 解析且无环、targeted 195 passed、flake8 0、全量 31f/5476p/10e 与基线 FAILED 集逐行 IDENTICAL 0 回归）
- [chore] S2a import_parser 直搬（**S 线 S2 首片**，真实改变文件位置；用户拍板选 (A) 先落 application/quote、“边界/名称解析分别处理”留 P5；零守卫禁入、零跨对象私有，`git mv` src/services/import_parser.py→src/application/quote/import_parser.py（保留 basename）；re-point ×2 文件（tests/test_import_parser.py:18 + @patch 串 ×2 :61/:70 + api/v1/endpoints/stocks.py:40）旧路径 grep 0 残留；import_parser 自身→name_to_code_resolver/stock_code_utils 依赖暂不变（application→services 非守卫禁入）；git mv 仅暂存至 index、未 commit；py_compile 三件、守卫 --check passed、import 冒烟（新路径/旧路径 ModuleNotFoundError/stocks 消费链）全对、targeted 42 passed、flake8 0、全量 32f/5475p/10e 与基线 FAILED 集仅 +1 既有 flaky test_provider_cache litellm subprocess 超时（零关联、§0.72 同源），除此 0 真实回归）
- [chore] S1 quote 域 3 件零禁入直搬（**S 线 services 余件收尾 Epic 首片**，真实改变文件位置；A0 勘察（零代码）对 quote+portfolio 余件做守卫假想落点禁入画像 + 爆破半径 + 私有访问，取 3 件零守卫禁入零跨对象私有件 `git mv` src/services→src/application/quote（stock_daily_start_resolver/stock_index_remote_service/stock_list_parser，保留 basename）；re-point 12 消费文件（点号形态含 caplog logger 名串 test_stock_index_remote_service:209 + monkeypatch 串 test_backtest_service:1153、属性形态 test:18）；import_parser 按 §4.1 line 227 有落点+内部拆分分叉移出待决、stock_code_utils 系归一化改指归口保留 src/services、余整改件留 S2；旧路径点号+属性 grep 0 残留、logger 名 import 冒烟实测=新点号名；git mv 仅暂存至 index、未 commit；py_compile 十五件、守卫 --check passed、targeted 282 passed、flake8 0、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归；**并修正搬包片收官快照配方**——旧 `--diff-filter=ACM` 会漏 git mv 的 rename 新路径，改用 `diff HEAD --diff-filter=ACMRT ∪ ls-files -o` 并断言新路径 in tar members）
- [chore] D5 decision 域逐件搬包（**D 线 decision Epic（D0–D5）收官片**，真实改变文件位置；decision_signal_service/decision_signal_outcome_service/decision_signal_reassess_service/skill_opinion_outcome_service/signal_scanner_service 5 件 `git mv` 从 src/services→src/application/decision（保留 basename、不改名，与 D1 先例一致）；全仓三类 re-point——点号形态×15（含 monkeypatch 字符串 patch 目标×3 + subprocess 动态 import 串×1）、属性形态×2（scanner.py/test）、文件路径锚点（源码定位契约测试 test_decision_signal_api/test_decision_signal_docs ×2 并同步 docs/decision-signals.md L55）；旧路径三类 grep 0 残留；bootstrap 方向盲区人工核（5 件无一 import src.bootstrap）；git mv 仅暂存至 index、未 commit；py_compile 十一件、守卫真实路径 --check passed、新旧路径 import 冒烟/消费链/bootstrap seam 全对、targeted 修复锚点后 api/docs/scanner 89 passed、flake8 0、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归；至此 decision 域 7 件 + ports.py 全部落入 src/application/decision/）
- [chore] D4 signal_scanner 取数端口化 + 归一化改指（搬包前置整改片，零文件移动；归一化 data_provider.base 改指 stock_code_utils wrapper（B4a 同型，含 watchlist/ranking-map/涨停池去重 3 处）；K线/涨停池真实取数复用既有读侧端口 `quote.QuoteProviderPort.fetch_kline`（返回 dict 含 data/stock_name）/`market.LimitPoolProviderPort.fetch_board`（返回 list[dict] 含 code/name），**零新增适配器**；因 scanner 系模块函数集合，取 H3b/R5 同型模块级 seam setter/getter + 未装配优雅降级（K线缺失跳过单只、涨停池缺失返回空池，不拖垮整体）；新建 `src/bootstrap/decision.py` configure_signal_scanner（复用 infrastructure 既有 DataProviderQuoteProvider/DataProviderLimitPoolProvider），api_lifecycle/main 双挂点装配（setter 幂等）；测试 seam re-point（_fake_kline→_fake_kline_provider + monkeypatch setattr 模块端口全局）；假想落点守卫 AST scanner forbidden/private 全 NONE、守卫 passed、降级/装配/幂等冒烟全对、targeted scanner 20 + 相邻批 122 passed、flake8 0、全量 5475/32/10（较基线 s039_run2 仅 +1 flaky 超时项 test_provider_cache litellm，子进程仅 import litellm/json/threading/http.server 与本改动零交集、三连跑 passed/passed/failed 逼近 15s subprocess 超时边界），除此 flaky 项外 FAILED 集与基线逐行 IDENTICAL、0 真实回归）
- [chore] D3 decision 域 ORM 读侧 Protocol + 时间工具上提 + 归一化改指（搬包前置整改片，零文件移动；6 个 ORM 类型（AnalysisHistory/DecisionSignalRecord/Outcome/Feedback/SkillOutcome/SkillSample）实测全部仅作注解（无 isinstance/构造/模块级引用）→ 新建 application/decision/ports.py 6 只读 *Row Protocol（属性集=实测消费面并集，人工剔除 4 处局部 dict/list 误报）+ 4 件注解全替；纯 stdlib 时间工具 utc_naive_now/to_utc_naive_datetime 逐字上提新建 src/utils/time.py，persistence/base.py 改为再导出保持持久层 24 文件 import 面不变；decision_signal_service 的 data_provider 归一化改指 stock_code_utils wrapper（B4a 同型）；四件假想落点守卫 AST forbidden/private 全 NONE、守卫 passed、再导出同一性/归一化等价冒烟全对、targeted 18 文件 589 passed、flake8 0、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] D2 decision 域私有访问收口（搬包前置整改片，零文件移动；同类 §0.36 ×5 调用方 staticmethod→classmethod 改 cls.（被调方保持私有，装饰器转换前经全仓绑定引用安全审计）+ 跨类方式①提升公开 ×3（DecisionSignalService._stock_filter_codes/_normalize_optional_market/_normalize_optional_action 去下划线，全仓同步含测试直调 1 处，旧名 0 残留）；三件当前态守卫 AST 私有探测 NONE 作为 D5 搬包预验；targeted 17 文件 503 passed、flake8 0、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] D1 decision 域轻件直搬（D 线 decision Epic 首片；D0 勘察 7 件守卫 AST 假想落点探测——仅 1 件零禁入，禁入分三类 data_provider 归一化/真实取数/ORM 模型直连，用户拍板完整 Epic 分片执行 + 端口优先复用既有；D1：extractor 的 data_provider.base.normalize_stock_code 改指 stock_code_utils.normalize_stock_code_for_analysis（B4a/R4 同型）+ 新建 application/decision/ 包 + skill_opinion_sample_service/decision_signal_extractor 两件 git mv（basename 保留）；13 处 re-point（pipeline/decision_signal_service/4 测试）旧路径 0 残留、无 shim；守卫 passed、真实路径 AST forbidden/private=NONE、归一化等价冒烟 6 输入 0 差异、targeted 120 passed、flake8 0、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] R1' status 服务私有提升公开+直搬（R/M 线收官片；Config 3 classmethod `_parse_litellm_yaml/_channels_to_model_list/_legacy_keys_to_model_list` 与 GeminiAnalyzer `_get_generation_backend` outright 改名公开（B4b 先例，13 文件全词同步含测试 patch 字符串/alphasift getattr 软探测/测试 fake 类方法，旧名 0 残留）；`agent_mode_explicit` 字段保留私有存储名、新增公开读写 property（不改 __init__ 关键字/序列化契约）；两 status 服务 git mv→application/runtime/{agent_backend_status,generation_backend_status}.py（命名 B 去 _service）；7 文件 21 处 re-point（api/v1/endpoints/agent.py + system_config_service + 5 测试含 patch/monkeypatch 字符串），旧路径 0 残留、无 shim；守卫 passed、真实路径 AST forbidden/private=NONE、冒烟（property 读写/关键字构造/公开方法）正确、targeted 687 passed + alphasift 101 passed、flake8 0、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归；至此 R/M 直搬 Epic（R1–R5+R1'）计划件全部落地）
- [chore] R5 market_hotspot 端口化+直搬（R/M 线；market_hotspot_service 的 data_provider.sector 真实 provider 能力→ H3b 同型端口化：新建 SectorRankingPort（application/market/ports.py）+ DataSectorRankingProvider（infrastructure/providers/sector_ranking_provider.py，承接原 _SectorRankingGateway 逻辑与 data_provider import）+ bootstrap configure_market_hotspot() 双挂点（api_lifecycle + main）；market_hotspot 应用侧删 data_provider import、新增模块级 seam setter+未装配优雅降级，再 git mv→application/market/market_hotspot（命名 B 去 _service）；4 消费方 re-point（pipeline/market_structure/2 测试，旧路径 0 残留）；生产主路仍注入 DataFetcherManager 不变；src/services/__init__.py 无条目、market/__init__ 不改无 shim；守卫 passed、真实路径 AST forbidden/private=NONE、端口行为冒烟均正确、targeted 自然序 44 passed、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] R4 task_queue 整改+直搬（R/M 线；先整改 data_provider.base——L30 死 import canonical_stock_code（导入后未使用）删除、normalize_stock_code 改指同语义公开封装 normalize_stock_code_for_analysis（H3a/B4a 归口）——再 git mv→application/runtime/task_queue（命名 B basename 保留）；生产 5（api/v1/endpoints scanner/analysis/eod_picker/alphasift/portfolio）+ 测试 8 re-point；src/services/__init__.py 无 task_queue 惰射条目、runtime.__init__ 不改无 shim；搬入前守卫 AST 探测唯禁入=data_provider.base 一行、改后件 forbidden/private=NONE；守卫 passed、targeted 272 passed、去重键归一行为冒烟不变、全仓旧路径 0 残留、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] R3 runtime 轻件直搬（R/M 线；task_service + runtime_scheduler git mv→application/runtime（命名保留 basename）；搬入前守卫 AST 探测两件零禁入零跨对象私有访问无需整改；src/services/__init__.py 除 TaskService/get_task_service 两条惰射映射（全仓确认无属性式访问）、无 shim；生产 7（bot/commands/analyze + main/api.deps/system_config/bootstrap×2）+ 测试 6 re-point；runtime.__init__ 不改；守卫 passed、targeted 114 passed、全仓旧路径 0 残留、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] R2 market 直搬（R/M 线；market_structure_service git mv→application/market/market_structure（命名 B 去 _service 后缀，含同类内 _is_not_supported_status 3 处 §0.36 classmethod 收口）+ daily_market_context git mv→application/market/daily_market_context（basename 不改）；生产 6 + 测试 6 re-point（含 test_daily_market_context L14 from src.services import 变体）；application/market/__init__ 不改、无 shim；搬入前用守卫 AST 探测复核两件 forbidden=NONE、market_structure 探到的 3 处 private 经 §0.36 消除；守卫 passed、targeted 233 passed、全仓旧路径 0 残留、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] R1 runtime agent_model 直搬落地 + status 服务因深耦合回退（R/M 线，收敛后收官；新建 application/runtime/__init__.py 不 re-export、agent_model_service git mv→application/runtime/agent_model.py（命名 B 按职责重命名，内部符号名不变），agent_model 2 消费方 re-point；原计划同批的 agent_backend_status/generation_backend_status 搬入触发 forbid_private_members 5 处、真实整改爆破半径 ~130+（核心 Config._parse_litellm_yaml 被 ~130 测试 mock 引用），按 §1.2/§8.1 回退 src.services（与 HEAD 零差异），其 Config/analyzer 私有提升公开拆为独立 R1' 切片待确认；守卫 passed/0 违规、targeted 311 passed、全仓旧路径 0 残留、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] R0 runtime+market Epic 勘察（零代码改动）：按 §4.1 对 `src/services/` 的 application/runtime（9 件）+ application/market 剩余（3 件）做禁入画像——10 件零禁入、task_queue/market_hotspot_service 轻整改（H3a/H3b 同型）；按 §4.3 line 231 将 system_config_service/run_diagnostics/run_flow 高耦合件建议移出直搬 Epic、另立内部拆分 Epic；拟定 R1–R5 切片与①命名/②高耦合 DEFER/③端口化形态 三决策点（待拍板）
- [chore] H3c: history_loader `git mv` 入 src/application/history/loader.py（history Epic 收官片；模块逻辑逐字不变、无 shim；生产 11 处 re-point：pipeline×3/bootstrap history/analysis_tools×4/data_tools/events/alphasift + 测试 4 文件（含 patch 字符串与 docstring）；application/history/__init__ 不改、与 comparison/read_model 先例一致；全仓 grep 旧路径 0 残留；守卫 0 条、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归。至此 src/services/ 三 history 模块已全部落入 application/history）
- [chore] H3b: history_loader 日线取数端口化（history Epic 搬包最后禁入整改，决策②拆独立子片；模块级 set_history_daily_bar_fetcher + getter _get_daily_bar_fetcher 保留测试 seam，未装配优雅降级 (None,"none")；新增 HistoryDailyBarFetcherPort(ports.py) + infrastructure adapter history_daily_bar.py + bootstrap configure_history_loader，ASGI app_lifespan 与 CLI main.py 双挂点装配、setter 幂等；测试 seam 10 处 _get_fetcher_manager→_get_daily_bar_fetcher + 新增降级用例；loader application 禁入清零，H3c 可搬包；守卫 0、全量 5476/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] H3a: history_loader 代码归一化改指 stock_code_utils（H3c 拖包前置整改，B4a/H2a 同型；_history_code_candidates 内 data_provider.base→canonical/normalize_stock_code_for_analysis；严格 A/B 等价 23 输入 0 差异，行为逐字不变；DataFetcherManager 取数禁入留 H3b，行未搬；守卫通过、全量 5475/31/10 与基线 IDENTICAL 0 回归）
- [chore] H2b: history_service `git mv` 入 src/application/history/read_model.py（history Epic 搬包片，类名仍 HistoryService；3 处 HistoryService._safe_format_number 类名私有静态调用按回测 §0.36 同型收口——调用方 _append_market_snapshot_to_report @staticmethod→@classmethod、改 cls._safe_format_number 满足 forbid_private_members；生产 4 处 + 测试 7 文件 + 当前态文档 4 文件 re-point（含 services/__init__ 惰性映射除条目），无 shim；守卫 0 条、全量 5475/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] H2a: history_service 代码归一化改指 stock_code_utils（H2b 搬包前置整改，B4a 同型；history_code_filter_candidates 内 data_provider.base→canonical/normalize_stock_code_for_analysis + is_bse_code re-import 收口；严格 A/B 等价 21 输入 0 差异，行为逐字不变；守卫 0 条、全量 5475/31/10 与基线 IDENTICAL 0 回归）
- [chore] H1: history_comparison_service `git mv` 入 src/application/history/comparison.py（history Epic 首个零禁入直搬片，3 处消费方 re-point：notification.py + test_history_comparison_service + test_notification patch 字符串；无 shim，守卫 0 条、全量 5475/31/10 与基线逐行 IDENTICAL 0 回归）
- [chore] H0 history Epic 勘察：src/services/ 三 history 模块（comparison 零禁入/service 1 处 data_provider/loader 2 处含 DataFetcherManager 取数）应入 application/history/ 的禁入分析、零跨对象私有访问确认、H1-H3c 切片规划与①模块命名/②storage 是否端口化/③取数端口化是否拆子片 三决策点（零代码改动）
- [chore] B4e: alert_service+alert_worker `git mv` 入 src/application/alert/（告警链路 B 线收官片；worker service 改必传+新增 build_alert_worker 自顶向下 DI 工厂、main/runtime 改工厂；搬入后守卫命中 private:_get_realtime_quote x2，按方式①将 EventMonitor._get_realtime_quote 提升为公开 get_realtime_quote；production/测试/文档锚点全量 re-point，无 shim；守卫 0 条、全量离线三步法 0 真实回归）
- [chore] B4d: AlertService 4 个 ORM 行依赖改读侧 Protocol（ports.py 新增 Alert*Row 只读协议，alert_service 删 src.infrastructure import+8 处注解改指，消除搬包最后一项禁入，行为逐字不变 0 回归）
- [chore] B4c: AlertService 日线取数端口化（新增 DailyBarFetcherPort + infrastructure adapter + build_alert_service 工厂，alerts.py 10 处与 alert_worker 默认构造改走工厂以消 alert_service 的 data_provider 禁入，全量 bit-identical 0 回归）
- [chore] B4b: AlertService 7 私有方法公开化（~61处机械重命名，消除 alert_worker forbid_private_members 风险，全量 bit-identical 0 回归）
- [chore] B4a: alert_worker data_provider 改指 stock_code_utils（B4 搬包前置，行为等价，全量 bit-identical 0 回归）
- [chore] B3: market_light_alerts 搬入 src/application/market/（10处改指，守卫 0，全量 bit-identical 0 回归）
- [chore] B2: notification_diagnostics 搬入 src/application/alert/（5 consumer 改指，首跑发现2处漏改即时补齐）
- [chore] B1: portfolio_alerts 搬入 src/application/portfolio/（0禁入首片，PortfolioService._normalize_symbol 提升为公开）
- [chore] B0 告警链路勘察：5 文件禁入分析、B1-B4 切片规划、D5 单进程假设入档（零代码改动）
- [chore] `decision_profile_policy` 下沉 `src/domain/decision/`（§4 归属表 line 229 `domain/` 候选表**收官项 6/6**）：`src/services/decision_profile_policy.py`（253 行）是决策 profile 偏向与 guardrail 的确定性策略规则（版本常量/价格关系约束/动作替换），精确命中 §3 line 71「action/profile/scale、策略与质量规则」。此前登记的「1 处 domain 禁入依赖」实为 `src.services.decision_signal_data_quality` import，**已被 §0.41 改指顺带治愈**，本轮按当前工作树复测禁入命中 0 后执行（教训：候选体检不得引用历史命中数）。仓内剩余依赖 `src.schemas.decision_action`（`DecisionAction` 八态 Literal）非守卫禁入，其 domain/shared 归位与 §0.44 的 sanitize 同类登记、不强行归位。`git mv` 逻辑逐字不变，`domain/decision/__init__.py` 扩 re-export（8 项公开符号），生产消费方 `decision_signal_reassess_service` 与 1 测试 import 改指；私有 `_apply_*` 外部零使用，**未留转发 shim**。运行时行为逐字等价（`decision-profile-v1` 等版本常量落库载荷原值冒烟确认），无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report` 0 条；`test_decision_profile_policy` **5 passed**；改动文件 flake8 0；全量离线 `-p no:randomly` 定序**首跑即 5475/31/10** 与基线逐行 bit-identical 0 回归。
- [chore] `decision_signal_summary` 下沉 `src/domain/decision/`（§4 归属表 line 229 `domain/` 候选、§3 line 71，续作线**第五个 domain 落点**，候选表 6 项完成 5）：`src/services/decision_signal_summary.py`（113 行）承载决策信号低敏摘要字段挑选与摘录生成规则（通知/风险视图/告警链路共用）。其唯一仓内依赖 `src.utils.sanitize`（`sanitize_decision_signal_payload`/`_text`）核实为纯 stdlib 脱敏工具、不在 `src/domain/` 守卫禁入清单，方向合法，按克制原则**登记为非阻断设计债**而非本片强行归位（`sanitize` 形态是函数、不符 line 76「domain/shared 枚举与值对象」定义）。`git mv` 逻辑逐字不变，`domain/decision/__init__.py` 扩 re-export，4 生产消费方（`src/core/pipeline`、`portfolio_risk_service`、`alert_worker`、`alert_service`，均只用公开名）与 1 测试 import 改指；`SUMMARY_FIELDS`/`_public_*` 私有名外部零使用，**未留转发 shim**。运行时行为逐字等价（冒烟验证含 token URL 摘要后 `[REDACTED_URL]` 脱敏保持），无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report` 0 条；`test_decision_signal_summary`+`test_alert_worker`+`test_decision_signal_extractor` **81 passed**；改动文件 flake8 0；全量离线 `-p no:randomly` 定序**首跑即 5475/31/10** 与基线逐行 bit-identical 0 回归。
- [chore] `alert_indicators` 下沉 `src/domain/alert/`（§4 归属表 line 229 `domain/` 候选、§3 line 74「`domain/alert/` 告警条件与判定」，续作线**第四个 domain 落点**）：`src/services/alert_indicators.py`（514 行，仅依赖 stdlib + pandas、零 `src.*`）承载技术指标类告警（MA/RSI/MACD/KDJ/CCI）的参数归一化、所需 K 线量推导与阈值/交叉判定。搬包前按 §2 line 42「需要复用的辅助提升为公开契约」把测试直用的模块私有 `_calculate_rsi` 提升为公开 `calculate_rsi`（`tests/test_stock_analyzer_rsi.py` 跨实现 RSI 口径对齐与 `tests/test_alert_worker.py` 的 import/调用点同步），不加薄转发。`git mv` 到 `src/domain/alert/alert_indicators.py`（算法逐字不变），新建 `src/domain/alert/__init__.py` re-export 显式公开面（模块无 `__all__`，按顶层公开符号列 12 项），生产消费方 `src/services/alert_service.py` 与 2 测试 import 改指，产品文档 `documents/product/实时告警中心/alerts.md` 路径同步；**未留转发 shim**。过程事故如实登记：搬包命令链式兜底写法误删工作文件，因该文件 HEAD 有完整 blob、已做编辑均可断言重放，字节级恢复零丢失（git 态 `R`→`D+A`，同内容）。运行时行为除私有转公开的唯一接口面变化（仅测试消费）外逐字等价，无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report` 0 条；import 冒烟 `calculate_rsi` Wilder 末值 80.0 正确；`test_alert_worker`+`test_stock_analyzer_rsi` **59 passed**；改动文件 flake8 0；全量离线 `-p no:randomly` 三步法（首跑 32 唯一增量为已知抖动项 `test_provider_cache`，隔离 16 passed）复跑 **5475/31/10** 与基线逐行 bit-identical 0 回归。
- [chore] `scanner_indicators` 下沉 `src/domain/analysis/`（§4 归属表 line 229 `domain/` 候选、§3 line 69「分析…**可纯算的指标**」，续作线**第三个 domain 落点**）：`src/services/scanner_indicators.py`（216 行，仅依赖 stdlib + pandas、零 `src.*`）是「给定日 K 序列 → 命中哪些信号」的纯函数层（MA/MACD 金叉死叉、RSI 超买超卖、BOLL 上下轨，8 信号口径对齐 `stock_analyzer`），落点取 `domain/analysis/` 而非 `domain/alert/`——消费方 `signal_scanner_service` 按 §4 line 218 归 `application/decision/`，模块本体是通用指标计算。`git mv` 保留历史、算法逐字不变，新建 `src/domain/analysis/__init__.py` re-export 模块 `__all__` 公开面（`SIGNAL_KEYS`/`SIGNAL_LABELS`/`MIN_BARS`/`detect_signals`），消费方 `signal_scanner_service` 与测试（模块属性风格）import 改指，产品文档 `documents/product/技术信号扫描/scanner.md` 两处路径同步；历史 CHANGELOG 条目不改写。**未留转发 shim**。运行时行为逐字等价，无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report` 0 条；import 冒烟无环、V 型底部 K 线命中 `[rsi_overbought, boll_upper]`；`test_signal_scanner_service` **20 passed**；改动文件 flake8 0；全量离线 `-p no:randomly` 定序 **5475/31/10**，FAILED 集合与基线逐行 diff **完全一致**（bit-identical）0 回归。
- [chore] `decision_signal_data_quality` 下沉 `src/domain/decision/`（§4 归属表 line 229 `domain/` 候选、§3 line 71「决策…质量规则」，续作线**第二个 domain 落点**）：`src/services/decision_signal_data_quality.py`（87 行，仅依赖 `collections.abc`/`typing`、零 `src.*`/框架/ORM/IO）命中 `src/domain/` 守卫禁入清单为 0，只含决策信号数据质量档位（high/medium/low/poor/unknown）的别名归一化与严重度取最严的业务规则。`git mv` 到 `src/domain/decision/decision_signal_data_quality.py`（保留历史、逻辑逐字不变），新建 `src/domain/decision/__init__.py` re-export 公开面（仿 `domain/backtest`/`domain/market`），3 生产消费方（`src/services/decision_profile_policy`、`decision_signal_reassess_service`、`decision_signal_outcome_service`）与 1 测试的 import 改指 `src.domain.decision.decision_signal_data_quality`；全为 `src/services/`→`src.domain` 外层依赖最内层、方向合规、不成环，全部只用公开名（无外部访问模块私有 `_QUALITY_*`/`_normalize_scalar`/`_explicit_quality_levels`）。`src/services/__init__.py` 无惰性映射，**未留转发 shim**。运行时行为逐字等价，无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report`/`--check` 0 条；import 冒烟无环、`normalize(degraded)→low`/`normalize(missing)→poor`；`test_decision_signal_data_quality` **9 passed**；全量离线 `-p no:randomly` 定序 FAILED 集合与 §0.39/§0.40 的 31 项基线逐行 diff **完全一致**（纯下沉、未增删用例数）0 回归。
- [chore] `market_symbol_utils` 下沉 `src/domain/market/`（§4 归属表 line 229 `domain/` 候选、回测 Epic 后 `src/services/` 清理续作的**首个 domain 落点**）：`src/services/market_symbol_utils.py`（113 行，仅依赖 `dataclasses`/`typing`、零 `src.*`/框架/ORM/IO）命中 `src/domain/` 守卫禁入清单为 0，只含 jp/kr/tw 后缀型 Yahoo 代码的业务规则与值对象，属 `ARCHITECTURE_TARGET.md` §2「domain 表达业务概念、规则和计算」。`git mv` 到 `src/domain/market/market_symbol_utils.py`（保留历史、函数体逐字不变），新建 `src/domain/market/__init__.py` re-export 公开面（仿 `domain/backtest`），6 生产消费方（`data_provider/base`、`data_provider/yfinance_fetcher`、`src/market_context`、`src/core/trading_calendar`、`src/data/stock_index_loader`、`src/services/stock_code_utils`）与 1 测试的 import 改指 `src.domain.market.market_symbol_utils`；全为外层依赖最内层、方向合规、不成环，全部只用公开名（无外部访问模块私有 `_SUFFIX_*`/`_MARKET_TO_SPEC`）。`src/services/__init__.py` 无 `market_symbol_utils` 惰性映射，**未留转发 shim**。运行时行为逐字等价，无 API / 前端 / 配置 / DB schema / workflow 变化。（此前推荐的 `market_light_alerts`→`application/market` 候选经复核会引入 `application→src.bootstrap` 回流——守卫不拦但违背 §2 line 38 方向，故未执行，改选本 domain 候选。）验证：守卫 `--report`/`--check` 0 条；import 冒烟无环、`get_suffix_market("7203.T")→jp`；`test_market_symbol_utils` **3 passed**；全仓 flake8（E9,F63,F7,F82）0；全量离线 `-p no:randomly` 定序 **5475 passed / 31 failed / 10 errors**，与 §0.39/§0.38/§0.37 基线逐位一致（纯下沉，未增删用例数）0 回归。
- [chore] `market_light` 仓储依赖收敛为端口 + DI（§8 第 8 项设计债收束，承接 §0.38 搬包）：`src/application/market/market_light.py` 此前 `load_previous_snapshot` 仍直连 `DatabaseManager.get_instance()` + `AnalysisRepository(db)`（不触发 `src/application/` 守卫，属 `ARCHITECTURE_TARGET.md` §2「应用依赖 domain + ports」意义上的非阻断设计债）。本片按回测 §0.37 同口径在 `src/application/market/ports.py` 新增 `MarketLightSnapshotRepositoryPort`（`Protocol`，单方法 `iter_market_review_snapshot_payloads`，逐字镜像仓储读能力、不机械扩面），`load_previous_snapshot` 形参 `db_manager` 改必填端口入参 `repository`、删除 `market_light.py` 内 `src.repositories`/`src.storage` import；具体 `AnalysisRepository(DatabaseManager.get_instance())` 改由 `src/bootstrap/market.py::build_market_light_snapshot_repository()` 装配注入（对齐同域 `build_limit_pool_service`/`build_sector_service`）；唯一生产 caller `src/services/market_light_alerts.py` 与 6 测试调用点同步改接。至此 `src/application/market/market_light.py` 与兄弟 `limit_pool`/`sector` 一致、只依赖端口。运行时行为逐字等价（`DatabaseManager` 全局单例，装配点由内部移到 bootstrap），无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report`/`--check` 0 条；改动文件 flake8（E9,F63,F7,F82）0；`ci_gate.sh flake8`（全仓）0、`deterministic` 通过；market_light + alerts 5 文件组 **119 passed**（`test_alerts_docs` 8 失败为既有基线：文档内容型断言漂移，非本切片引入）；全量离线 `-p no:randomly` 定序 **5475 passed / 31 failed / 10 errors**，与 §0.38/§0.37/§0.36/§0.35c 基线逐位一致（端口化，未增删用例数）0 回归。
- [chore] `market_light_service` 搬入 `src/application/market/market_light.py`（§8 第 8 项「`src/services/` → `application/` 逐用例搬迁」续作首个候选，承接回测 Epic 收束）：按 `ARCHITECTURE_TARGET.md` §4 归属表选取最低摩擦对象 `src/services/market_light_service.py`（125 行，§0.31 已消 `sqlalchemy` 直连、无 `fastapi`/`data_provider`/`persistence.models`/私有成员违规）`git mv` 到 `src/application/market/market_light.py`。因 `src/application/` 禁入清单不含 `src.storage`/`src.repositories`，且 `_extract_region_snapshot` 为模块级函数裸名调用（不触发 `forbid_private_members`），文件内 import 与函数体逐字不变；同步改 3 个 `src/services/` 生产 import 方（`market_light_alerts.py` 取 3 符号、`alert_worker.py`/`alert_service.py` 各取 `normalize_market_alert_region`）路径为 `src.application.market.market_light`、`tests/test_market_light_service.py` 的 import 与 `patch(...market_light.MarketAnalyzer)` 目标、`src/repositories/analysis_repo.py` docstring 提及、`src/application/market/__init__.py` 域说明（`market_light` 从「后续加入」改为「已加入」）。`src/services/__init__.py` 无 `market_light` 惰性映射，**未留转发 shim**。残留：函数式模块 `load_previous_snapshot` 仍直连 `DatabaseManager`/`AnalysisRepository`（与回测 §0.37 对齐前同类的**非阻断设计债**，因函数模块无自然注入接缝，端口 + DI 收敛留待后续）。运行时行为逐字等价，无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report` 0 条；market_light + alerts 5 文件组 **111 passed**（`test_alerts_docs` 8 失败为既有基线：文档内容型断言漂移，非本切片引入）；flake8（E9,F63,F7,F82）0 违规；`ci_gate.sh architecture` 通过；全量离线 5475 passed / 31 failed / 10 errors，与 §0.37/§0.36/§0.35c 基线逐位一致（纯搬包，未增删用例数）0 回归。
- [chore] 回测仓储依赖收敛为端口 + DI（§8 第 7 项「回测服务分层」非阻断设计债收束，承接 0.36）：`src/application/backtest/service.py` 此前仍 `from src.repositories import BacktestRepository, StockRepository` + `from src.storage import DatabaseManager` 直连具体仓储/存储（不触发 `src/application/` 守卫，属 `ARCHITECTURE_TARGET.md` §2「应用依赖 domain + ports」意义上的设计债）。本片在 `src/application/backtest/ports.py` 新增 `BacktestRepositoryPort`（13 方法，签名逐一镜像 `BacktestRepository`）/`StockRepositoryPort`（`get_daily_on_date`/`get_forward_bars`）两个 `Protocol`，返回类型用领域记录、`AnalysisHistory`/`StockDaily`/联查行非首列以 `Any` 松类型（与 `history` 端口同口径，避免 application 反向依赖 `persistence.models`）；`service.__init__` 由 `(db_manager=None, daily_refill=None)` 改为接收 `(backtest_repository, stock_repository, daily_refill=None)` 端口入参，删除 `src.repositories`/`src.storage` import 与 `self.db` 属性（`self.repo`/`self.stock_repo`/`self.daily_refill` 同名保留）；具体仓储改由 `src/bootstrap/backtest.py::build_backtest_service()` 装配注入。测试 `BacktestServiceTestCase` 新增 `_service()` helper（真实仓储绑定测试库复现原行为），58 处 `BacktestService(self.db)` 批量改 `self._service()`、seam 测试改传 `MagicMock()` 端口。至此 `src/application/` 下全部用例（history/agent/market/quote/usage/watchlist/backtest）统一只依赖端口，回测用例对齐既有约定。运行时行为逐字等价，无 API / 前端 / 配置 / DB schema / workflow 变化。验证：守卫 `--report` 0 条；回测/相关 9 文件组 342 passed；flake8（E9,F63,F7,F82）0 违规；`ci_gate.sh architecture` 通过；全量离线 5475 passed / 31 failed / 10 errors，与 §0.36/§0.35c 基线逐位一致（本片未增删用例数）0 回归。
- [chore] 回测服务实际搬入 `src/application/backtest/`（回测 ORM 领域 DTO 下沉 Epic 完结 0.36，§8 第 7 项「回测服务分层」落地）：`src/services/backtest_service.py` `git mv` 到 `src/application/backtest/service.py`，**不留 `src.services.backtest_service` 转发 shim**。因 `src/application/` 层禁止 `src.infrastructure` 且 `forbid_private_members`，本片删除 `__init__` 内 `if daily_refill is None: from src.infrastructure...` 的缺省装配接缝（改由 `build_backtest_service()` 装配口注入），并将 `_normalize_code_for_display`/`_result_to_dict`/`_normalize_learning_summary` 由 `@staticmethod` 改 `@classmethod`、内部 3 处 `BacktestService._x` 改 `cls._x`（三 helper 仅本文件内引用）。6 个生产构造点（`main.py`×2 run 路径、`src/agent/memory.py`×2、`src/agent/skills/aggregator.py`×1、`src/agent/tools/backtest_tools.py`×1）统一改走 `build_backtest_service()`，3 处 import（`api/v1/endpoints/backtest.py`、`api/deps.py`、`src/bootstrap/backtest.py`）改指新路径；`src/services/__init__.py` 移除 `BacktestService` 惰性映射与 `__all__` 项。同步测试 import/patch/logger/assertLogs（`test_backtest_service.py` 含 `test_default_assembly_wires_infrastructure_adapter`→`test_bootstrap_factory_wires_infrastructure_adapter`、`ControlledDataFetcherManager` 真实 fill 显式注入适配器；`test_main_portfolio.py`/`test_skill_load_warning.py` patch 目标改工厂）、`docs/analysis-context-pack.md` 回测锚点与 `test_analysis_context_pack_docs.py`、多处 docstring 旧路径。运行时行为逐字等价，纯分层收敛，无 API / 前端 / 配置 / DB schema 变化。验证：守卫 `--report` 0 条；回测/相关 9 文件组 342 passed；flake8（E9,F63,F7,F82）0 违规；`ci_gate.sh architecture` 通过；全量离线 5475 passed / 31 failed / 10 errors，与 0.35c 基线逐位一致 0 回归。
- [chore] 回测写路径下沉并彻底移除 `backtest_service` 的 ORM 引用（回测 ORM 领域 DTO 下沉 Epic 之三 0.35c，§8 第 7 项最后搬家守卫阻断项清零）：`src/services/backtest_service.py` 5 处 `BacktestResult(...)`/`BacktestSummary(...)` 构造全部改 `BacktestResultRecord(...)`/`BacktestSummaryRecord(...)`，并**删除** `from src.infrastructure.persistence.models.analysis import BacktestResult, BacktestSummary`（grep 核实 service 源码 ORM 符号与 `src.infrastructure.persistence` 引用全部归零，文件搬入 `src/application/` 的最后一项真实守卫阻断清零）；`src/repositories/backtest_repo.py` 新增 `_to_result_orm`/`_to_summary_orm`（按 `__table__.columns.keys()` 动态取属性构造 ORM 新行，字段漂移由 0.35a 列集合一致测试先行拦截），`save_result`/`save_results_batch`/`upsert_summary` 入参改领域记录、三个 `session.add*` 点内部转 ORM，`upsert_summary` 更新分支按属性回写语义逐字不变；全仓 grep 确认写方法生产调用点全部在 service 内（契约面可控）、`tests/test_backtest_service.py` 8 处直接构造均为 `session.add` 直连库夹具（按 plan 保留 ORM，零改动）。测试文件 `test_backtest_repo_read_records.py` 更名 `test_backtest_repo_record_mapping.py`（读写映射收拢同一文件），新增 3 方法：记录写入→读回 round-trip 值一致、`upsert_summary` 新增/更新双分支不重复插行、源码级防回潮锁定（`inspect.getsource` 断言 service 无 persistence.models import/无 ORM 构造且含 Record 构造）。验证：映射测试 10 passed（7 读 + 3 写/锁定）；回测 6 文件组 121 passed（含 `run_backtest` 端到端写链）；守卫 `--report` 0 条无变化；flake8 0 违规；`ci_gate.sh architecture`+`deterministic` 通过；全量离线 5475 passed / 31 failed / 10 errors（5475−5472=3 恰为本片新增），失败集逐项一致 0 回归，新对照基线 5475/31/10。写库行为逐列等价，纯服务端内部分层收敛，无 API / 前端 / 配置 / DB schema 变化。
- [chore] 回测仓储读路径改为返回领域记录（回测 ORM 领域 DTO 下沉 Epic 之二 0.35b，§8 第 7 项最后搬家守卫阻断项清除第二阶段）：`src/repositories/backtest_repo.py` 新增会话内 ORM→领域记录映射助手 `_to_result_record`（29 字段）/`_to_summary_record`（25 字段）/`_map_context_row`（联查行首列），`list_results`/`list_results_for_recompute`/`get_results_paginated`/`get_results_with_context_batch`/`list_results_with_context`/`get_summary` 六个读方法全部改返回 `src/domain/backtest` 记录（`align_existing_result_dates` 仅返回 int、`get_candidates` 返回未被 service import 的 `AnalysisHistory`，不泄漏回测 ORM 类型，不在映射范围）；`backtest_service.py` 读消费侧 6 处类型注解改指 Record，运行时属性访问零改动（记录属性名与 ORM 列名一致，`BacktestEngine.compute_summary` 的 `BacktestResultLike` Protocol 无缝满足）。写路径（5 处 ORM 构造 + `persistence.models` import）为计划内中间态，0.35c 清除。新增 `tests/test_backtest_repo_read_records.py`（7 方法：真实 SQLite 会话断言返回记录类型/字段值逐一映射/联查非首列保持原值/缺行返回 None；0.35c 扩充写路径后更名 `test_backtest_repo_record_mapping.py`）。验证：新测试 7 passed；回测 6 文件组 118 passed；守卫 `--report` 0 条无变化；全量离线 5472 passed / 31 failed / 10 errors（5472−5465=7 恰为本片新增），失败集逐项一致 0 回归，新对照基线 5472/31/10。纯服务端内部读链路归一，无 API / 前端 / 配置 / DB schema 变化。
- [chore] 新增 `src/domain/backtest/` 领域记录层（回测 ORM 领域 DTO 下沉 Epic 之一 0.35a，§8 第 7 项最后搬家守卫阻断项清除第一阶段）：为后续把 `backtest_service` 对 `src.infrastructure.persistence.models`（`BacktestResult`/`BacktestSummary`）的直接依赖下沉为“领域记录 + 仓储双向映射”做准备（守卫不豁免 `if TYPE_CHECKING`，application 层连 TYPE_CHECKING 下 `from src.infrastructure...` 也算违规，故必须彻底不引用）。本片纯新增、零行为改动：`src/domain/{__init__.py,backtest/__init__.py,backtest/records.py}` 新增 `BacktestResultRecord`（29 字段）/`BacktestSummaryRecord`（25 字段）两个纯 `@dataclass`，字段逐一镜像 ORM 列名（保证 `src/core/backtest_engine.BacktestResultLike` 鸭子类型消费无需改名、`src/core` 零改），默认值对齐 ORM 列默认以支持 service 现有部分关键字构造。`backtest_service`/`backtest_repo` 本片尚未切换（读路径 0.35b、写路径+删 import 0.35c）。新增回归 `tests/test_backtest_domain_records.py`（6 方法）：用 `__table__.columns.keys()` 动态断言两记录字段集合与 ORM 列严格一致（防加列漏映射/凭空多字段）+ 默认值/部分构造/值相等断言。验证：`tests/test_backtest_domain_records.py` 6 passed；守卫 `--report` 0 条无变化；全量离线 5465 passed / 31 failed / 10 errors（5465−5459=6 恰为本片新增），失败集逐项一致 0 回归，新对照基线 5465/31/10。无 API / 前端 / 配置 / DB schema 变化。
- [chore] `backtest_service` 日线补数编排归位到 `DailyBarRefillPort`，消除 `data_provider` 取数与 `self.db.save_daily_data` 直用（§8 第 7 项「回测服务分层」前置收敛之二，§0.34）：`BacktestService._try_fill_daily_data` 此前内联 `from data_provider.base import DataFetcherManager` 惰性取数 + `self.db.save_daily_data(...)` 落库，同属一个“日线补数”副作用步骤。按 ARCHITECTURE_TARGET §2「数据源/写入仅经 infrastructure 适配器访问」与切片 8/10/11 既有 provider+端口模式，新增 `src/application/backtest/ports.py`（`DailyBarRefillPort.refill(*, code, start_date, end_date, days) -> None`）与 `src/infrastructure/providers/backtest_daily_refill.py`（`DataProviderDailyBarRefill`，内部保持调用期惰性导入以兼容既有 `patch("data_provider.base.DataFetcherManager")`），把取数+判空+落库两步逐字搬迁进适配器；`backtest_service.py` 的 `_try_fill_daily_data` 改为纯 `self.daily_refill.refill(...)`（窗口计算与 try/except warning 降级保留在用例层，行为逐字不变），`__init__` 新增可选 `daily_refill` 参数（未注入时函数内惰性缺省装配为迁移中间态接缝，避免改 63 个构造点）；`src/bootstrap/backtest.py::build_backtest_service()` 显式注入适配器。至此 `backtest_service.py` **既无 `data_provider` 也无 `self.db.save_daily_data`**。同时按 `check_architecture.py` 实际 RULES 纠偏§8 第 7 项口径：`src/application/` 仅禁 `data_provider`/`src.infrastructure`（及 fastapi/sqlalchemy/api/bot），**不禁 `src.repositories`/`src.storage`**，故搬家真实阻断仅剩 `src.infrastructure.persistence.models`（ORM 类型），`repositories`/`storage` 为非阻断设计债。新增 `BacktestDailyRefillSeamTests`（5 方法：端口参数捕获/空白短路/失败降级 warning/缺省装配/源码级无 data_provider 锁定）。验证：`tests/test_backtest_service.py` 68 passed（`--collect-only` 实测：改前 63 + 本片 5）；定向补数链路 12 passed（含 1390 真实 patch）；回测相关 5 文件组 223 passed；守卫 `--report` 0 条无变化；flake8 0 违规；全量离线 5459 passed / 31 failed / 10 errors（5459−5454=5 恰为本片新增），失败集逐项一致 0 回归。纯服务端内部编排搬迁，无 API / 前端 / 配置 / DB 变化，架构守卫基线不变。
- [chore] `backtest_service` 的代码归一化依赖归口 `stock_code_utils`，消除 `data_provider.base` 归一符号模块级直连（§8 第 7 项「回测服务分层」前置收敛之一，§0.33）：`BacktestService._normalize_summary_code`（组合 `data_provider.base.normalize_stock_code`/`canonical_stock_code` 与回测语境 `normalize_code`，含 `SS` 前缀双归一分支）逐字搬迁为 `src/services/stock_code_utils.py` 新增的 `normalize_stock_code_for_backtest_summary`，沿用切片 9/12「纯代码归一化只补语义化包装、不套端口+适配器」先例；`backtest_service.py` 删除 `from data_provider.base import canonical_stock_code, normalize_stock_code` 模块级导入与 `normalize_code` 别名，2 处调用（`run_backtest` / `_recompute_summaries` 的汇总去重键）改点新函数，行为逐值一致。`_try_fill_daily_data` 的 `DataFetcherManager` 函数内惰性导入与 `save_daily_data` 直用不在本片范围（§8 第 7 项剩余前置，已登记）。新增回归：`TestNormalizeStockCodeForBacktestSummary` 22 个收集项（20 个代码样本与搬迁前参考实现逐值比对 + 空值 + 源码级归口锁定断言 `backtest_service` 不得再加回模块级直连）。验证：`tests/test_stock_code_utils.py` 118 passed（改前实测 96 + 22）；回测 7 文件组 209 passed 与 §0.30 一致；守卫 `--report` 0 条无变化（本片消除的是搬家前置依赖而非守卫违规）；`ci_gate.sh` syntax + flake8 通过；全量离线 5454 passed / 31 failed / 10 errors，失败集与基线逐项一致 0 回归。纯服务端内部搬迁，无 API / 前端 / 配置 / DB 变化，架构守卫基线不变。
- [chore] `alphasift_service` 去 `fastapi` 依赖，架构守卫全仓基线首次归零（P3 前置条件 / §8 第 4 项「收紧守卫」最后 1 条，§0.32）：`src/services/alphasift_service.py` 此前直接持有 `Request`、抛 `HTTPException`（25 处引用），属服务层感知 HTTP 传输的设计级分层违规。本次新增服务层业务异常 `AlphaSiftServiceError(status_code, detail)` 替换全部 17 处 raise 与 5 处 except（`str()` 形状与 Starlette `HTTPException` 一致，后台选股任务的 `task.error` 文案不变）；`install` 的 `Request` 参数改为 `session_cookie: Optional[str]`，auth cookie 提取归位 `api/v1/endpoints/alphasift.py` 传输层；删除零调用死代码 `_ensure_alphasift_ready`。端点新增 `_call_service` 转译助手（7 个路由接入），因全局错误处理器对含 `error`+`message` 的 dict detail 直接透传，`/api/v1/alphasift/*` 的 HTTP 状态码与响应体逐字不变，前端 / 桌面端零影响。架构守卫基线 1 → **0 条**（`scripts/architecture_baseline.json` 空数组，`--report` 输出 No architecture violations found），此后所有规则新增违规直接阻断。顺手修正本机首次执行 `ci_gate.sh flake8` 暴露的 2 处历史遗留 F821（`src/storage.py` / `persistence/repositories/intelligence_repo.py` 的 `'SearchResponse'` 引号注解补 `TYPE_CHECKING` 导入，无运行时行为变化）。验证：`tests/test_alphasift_api.py` 92 passed；`ci_gate.sh` syntax/architecture/flake8/deterministic 全过；全量离线 `pytest -m "not network"` 5432 passed / 31 failed / 10 errors 与 §0.30/§0.31 基线逐项一致，0 新增失败。未做 `alphasift_service` → `src/infrastructure/alphasift/` 目录搬迁（P4，前置条件「外部包安装路径需离线测试」未满足）。
- [chore] §8 第 4 项「收紧守卫」连续归零 `src/services/` 剩余 3 条存量违规中的 2 条技术收敛项 + 1 条数据模型下沉项（承接 §0.30，架构守卫基线 4 → 1，`src/services/` 现仅剩 `alphasift_service` → `fastapi` 一条）：
  - `src/services/market_light_service.py`（`sqlalchemy`）：`load_previous_snapshot()` 此前直接 `from sqlalchemy import desc` + `session.query(AnalysisHistory).filter(...).order_by(desc(...))` + `yield_per` 扫描大盘复盘历史行；本次把这段查询下沉到 `AnalysisRepository` 新增的公开方法 `iter_market_review_snapshot_payloads(limit=None)`（生成器，逐批产出 `(id, context_snapshot)` 普通元组而非 ORM 对象，避免会话关闭后访问分离实例），服务层不再依赖 `sqlalchemy`/`AnalysisHistory` 模型本身；`MARKET_LIGHT_HISTORY_BATCH_SIZE` 常量随迁移一并挪到仓储模块，`tests/test_market_light_service.py` 同步改为从新位置导入。扫描顺序、逐行校验/降级语义、错误抛出方式均逐字保留。
  - `src/services/intelligence_service.py`（`sqlalchemy.exc`）：`create_source()` 此前直接 `except IntegrityError`（`sqlalchemy` 异常类型）识别资讯源重名；本次在 `IntelligenceRepository.create_source` 内部捕获 `IntegrityError` 并转换为新增的仓储层异常 `IntelligenceSourceNameConflictError`，服务层改为只捕获这个业务级异常，不再依赖 `sqlalchemy` 异常类型。`test_duplicate_source_name_is_validation_error` 等既有真实内存库回归测试均保持通过，说明重名转 `IntelligenceServiceError` 的对外契约未变。
  - `src/services/run_flow.py`（`api.v1.schemas.run_flow`）：服务层直接 `import api.` 是分层方向违规；核实 `RunFlowSnapshot` 所在模块是纯 Pydantic 数据模型（无任何 HTTP/路由/状态码语义），参照 §0.24 之前 `bot_message.py` 下沉先例，把 `api/v1/schemas/run_flow.py` 整体搬到新增的 `src/schemas/run_flow.py`（不留兼容 shim），并同步改掉全仓仅有的 3 处真实引用（`src/services/run_flow.py`、`api/v1/endpoints/analysis.py`、`api/v1/endpoints/history.py`）；旧文件物理删除。字段、枚举、校验语义零改动。
  未触碰 `src/services/alphasift_service.py` → `fastapi`（该服务直接持有 `Request`/抛 `HTTPException`，属于职责拆分而非机械搬迁，风险明显高于本批三条，需单独评估后再动）。全量离线回归：`pytest -m "not network"` 5432 passed / 31 failed / 10 errors，与 §0.30 基线逐项一致，0 新增失败；`./scripts/ci_gate.sh syntax` + `architecture` 均通过。
- [chore] `src/services/backtest_service.py` 的汇总重算不再自建 `sqlalchemy` 会话（P3 前置条件 / §8 第 4 项「收紧守卫」首次归零 `src/services/` 存量违规）：`_recompute_summaries()` 此前直接 `from sqlalchemy import and_, select` + `self.db.get_session()` 拼查询，并跨层调用 `BacktestRepository._build_code_conditions`（私有辅助）来按 code 过滤；本次把这两段查询收进 `BacktestRepository` 新增的公开方法 `list_results_for_recompute(code=None, eval_window_days, engine_version)`（`code=None` 表示 overall 全量范围，与原来的整体查询语义一致；按 code 过滤复用它已有的私有 `_build_code_conditions`），服务层改为直接调这个新方法，删除 `sqlalchemy` 导入与 `_recompute_summaries` 里唯一的 `self.db.get_session()` 用法。查询条件、`compute_summary` 调用参数、写回仓储的方式均逐字保留，行为不变；纯内部实现搬迁，未改任何 API / Schema / 前端 / 配置字段。架构守卫基线 5 → 4 条（`src/services/backtest_service.py -> sqlalchemy` 已消失，其余 4 条仍全部在 `src/services/`）；`tests/test_backtest_service.py`（63 项，直连真实仓储与内存库、非 mock）、`tests/test_backtest_api.py`、`tests/test_check_architecture.py` 及回测相关 7 个测试文件共 209 项全绿。此切片是 §8 第 7 项「回测服务分层」列出的前置条件之一（先消掉搬家会直接触发守卫的依赖），本次只归零这一条，未开始文件搬迁本身。
- [文档] 修正 `VISION_PROVIDER_PRIORITY` 在三处专题文档里的描述偏差（承接配置暴露批次 P5/P6 登记的待决策项，采纳“先改文档消除漂移”方向）：`docs/full-guide.md`、`docs/LLM_CONFIG_GUIDE.md`、`docs/LLM_CONFIG_GUIDE_EN.md` 此前将该键描述为“主视觉模型调用失败时按此顺序自动切换到下一个可用 provider”，但代码实测确认 `_resolve_vision_model()` 的备用推断是硬编码的 `gemini → anthropic → openai` elif 链、不引用该配置，`extract_stock_codes_from_image()` 的失败重试也只对同一个已解析模型重试（同一 provider 多把 Key 间轮换），不存在跨 provider 切换逻辑；该键真正、且唯一的行为读取点是 `Config.validate()` 划定告警检查范围（主模型自身 provider 始终单独检查，不受该列表是否包含它影响，已由既有测试钉住）。本版将三处描述改写为与代码事实一致，并明确“调整它不会带来实际调用行为变化，当前未暴露在 Web 设置页”；`src/config/settings.py` 里 `vision_provider_priority` 字段旁的注释也同步修正（原写的是“provider order for Vision fallback”，同样存在误导），`src/config/registry.py` pending 表注释同步“漂移已修正”、不入库结论不变（无行为读取方这一点独立于文档成立）。纯文档与注释修正，未触碰任何运行时分支、注册表载荷或前端代码。`docs/full-guide_EN.md` 经核对从未展开描述该键行为（仅链接至已修正的专题文档），无需同步。
- [测试] 配置暴露批次 P6 收口：新增 `tests/test_config_registry.py::TestP6LlmChannelSwitchStaysPending`（5 个用例），把 `LLM_ANSPIRE_ENABLED` 不入库的结论固定为契约——该键属于前端「LLM 渠道编辑器」的 `LLM_<渠道>_ENABLED` 草稿命名空间（从 `SettingsPage.tsx` 源码抽取两处渠道状态键正则并断言匹配，同时断言编辑器对该键的读回与写回位点仍存在），注册会造成一键两面；并由真实 `Config._load_from_env()` 四组行为回归证明它仅在 `LLM_CHANNELS` 含名为 anspire 的渠道时才影响解析结果，其余场景是不生效开关，不符合批次 P3 的“运行时确有读取方”入库标准；另锁定 3 个编辑器托管 / 行为未定键（`VISION_MODEL`、`VISION_PROVIDER_PRIORITY`、`LLM_ANSPIRE_ENABLED`）必须继续留在 `WEB_SETTINGS_PENDING_EXPOSURE` 且不得注册。本轮为测试与注释变更，未新增注册字段（registry 254 不变、pending 9 不变），运行时与设置页行为零改动；文档同步见 `docs/settings-help.md` 批次 P6 段。
- [新功能] Web 设置页「通知」分类新增 5 个报告转图片 / 企业微信消息形态字段（配置暴露批次 P5）：转图三键 `MARKDOWN_TO_IMAGE_CHANNELS`（array/textarea，默认空即关闭该特性）/ `MARKDOWN_TO_IMAGE_MAX_CHARS`（下限 1，默认 15000）/ `MD2IMG_ENGINE`（select：`wkhtmltoimage` | `markdown-to-file`）共用 `settings.notification.markdown_to_image` 帮助组，企业微信两键 `WECHAT_MSG_TYPE`（select：`markdown` | `text`）/ `WECHAT_MAX_BYTES`（下限 1，默认 4000）共用 `settings.notification.wechat_delivery`，归入已有 `notification` 分类不新建前端分类。本批沿用 P3/P4 的入库标准（运行时必有读取方）：四个属性在 `NotificationService` / `WechatSender` 实例构建时读取，而 `get_notification_service()` 每次返回新实例不缓存单例，`MD2IMG_ENGINE` 额外在每次转图调用时读，因此 5 个字段均不标 `restart_required`。本批首次把下拉枚举带入设置页：`get_field_definition` 从 `options` 自动派生 `validation.enum`，列表外值保存返回 `invalid_enum`（HTTP 400），而 `.env` / 进程环境变量路径不报错（`MD2IMG_ENGINE` 非法值回落 `wkhtmltoimage`，`WECHAT_MSG_TYPE` 原样存储并由发送侧把非 `text` 当 `markdown`），两条路径已在文案与 `docs/settings-help.md` 口径中写清。数值字段同样区分越界两条路径（设置页 `out_of_range` 拒写 vs `.env` 收敛），且 `WECHAT_MAX_BYTES` 文案写明两个易被误解读的行为：不填时默认值跟随消息类型（text 2048 / 其余 4000，与 registry 展示的字段默认 4000 不同），text 模式下发送侧还会把单条上限压到 2000 字节。`MARKDOWN_TO_IMAGE_MAX_CHARS` 写明是“跳过转图”而非截断长度，引擎缺失或转换失败均降级为文字发送。新增 `TestP5ReportImageAndWechatFormFieldsRegistered`（10 个用例，含默认值/大小写归一/渠道列表归一/引擎回落与真实 `send_to_wechat` 分片不超 2000 字节的读取路径回归，以及把 `VISION_MODEL`（写入归属已由「AI 模型接入」通道编辑器接管，注册会一键两面）与 `VISION_PROVIDER_PRIORITY`（除 `Config.validate()` 告警文案外无行为读取方且文档漂移）故意留在 pending 的断言）、`tests/test_system_config_service.py` 的保存校验回归（区间越界 `out_of_range` / 枚举列表外 `invalid_enum`）与 `docs/settings-help.md` 下拉枚举两条路径的通用口径；`docs/full-guide.md` 企业微信与 Markdown 转图片小节、`docs/full-guide_EN.md` 同步补齐（英文侧新增 Markdown To Image 小节以对齐）；`.env.example` 补 `WECHAT_MSG_TYPE` 并修正 `WECHAT_MAX_BYTES` 注释。运行时零改动（未新增 `os.getenv`、未改默认值/区间/判定逻辑），`GET /api/v1/system/config` 载荷多 5 个键（249 → 254），`WEB_SETTINGS_PENDING_EXPOSURE` 14 → 9。
- [新功能] Web 设置页「系统」分类新增 6 个组合与风险字段（配置暴露批次 P4）：风险阈值 `PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT` / `PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT` / `PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT` / `PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO` / `PORTFOLIO_RISK_LOOKBACK_DAYS`（共用 `settings.system.portfolio_risk` 帮助组）与汇率刷新开关 `PORTFOLIO_FX_UPDATE_ENABLED`（`settings.system.portfolio_fx`）。这 6 个键不只是展示默认值：会写入风险报告的 `thresholds` 并参与持仓告警触发判定（`src/services/portfolio_alerts.py` 的 breach 模式比较止损线，near 模式比较“止损线 × 接近比例”），因此文案与守卫都显式写出灵敏度影响。生效时机按真实读取路径定为“同一进程内保存即生效”：风险服务在请求处理函数内构造（`api/v1/endpoints/portfolio.py`）、`refresh_fx_rates` 按调用 `get_config()`，保存链路会重置 Config 单例，因此 6 个字段均不标 `restart_required`。数值区间只声明运行时实际存在的下限（`0.0`×4 / `1`×1）不新增 `max`，并区分越界的两条路径：设置页保存低于下限的值会被 `SystemConfigService._validate_numeric_range` 以 `out_of_range` 拒绝写入，而 `.env` / 进程环境变量里的越界值仍由 `parse_env_float/int(minimum=…)` 静默收敛（`1` 在设置页开关上不可能出现，但手写 `.env` 会被读成关闭，因此该键的保存校验比 `.env` 更严）。分类选用已有 `system`，不新建前端闭合 union `SystemConfigCategory` 的 `portfolio` 分类，避免无必要的客户端契约改动。新增 `TestP4PortfolioRiskFieldsRegistered`（8 个用例，含 `_build_stop_loss` 乘法语义的行为回归与四处变异验证）、`tests/test_system_config_service.py` 的设置页保存区间校验回归（5 个数值字段越界拒绝 / 无上限极大值通过 / FX 开关拒绝 `1`）、`docs/full-guide.md` / `docs/full-guide_EN.md`「组合与风险配置 / Portfolio risk configuration」小节与 `docs/settings-help.md` 生效语义、数值区间两条路径的通用口径条目；`.env.example` 的 6 个键已存在，只补了设置页入口、告警联动与布尔口径注释。运行时零改动（未新增 `os.getenv`、未改默认值/区间/判定逻辑），`GET /api/v1/system/config` 载荷多 6 个键（243 → 249），`WEB_SETTINGS_PENDING_EXPOSURE` 20 → 14。
- [测试] 新增设置页中文文案覆盖守卫 `TestWebUiFieldLocalizationCoverage`（4 个用例）：已注册字段必须同时存在于 `apps/hrs-web/src/utils/systemConfigI18n.ts` 的 `fieldTitleMap` / `fieldDescriptionMap`，否则中文界面会回退成英文卡片（`SettingsField.tsx` 的回退链）。盘点 243 个注册字段发现 77 个无中文条目、批次 P1/P2/P3 全部命中（此前批次只补了弹窗帮助 `settingsHelp.ts`，未补卡片文案），已为批次 P3 的 9 个键补齐中文标题+描述，剩余 68 键固定为只能收缩的 `_ZH_UI_LOCALIZATION_BACKLOG` 存量名单（新批次不得往里加名字），后续 P5/P6 注册字段时会直接阻断飘移。前端改动为文案与测试，未改设置页布局或控件。
- [新功能] Web 设置页「通知」分类新增 9 个机器人 / 飞书配置字段（配置暴露批次 P3）：机器人运行时 `BOT_ENABLED` / `BOT_COMMAND_PREFIX` / `BOT_ADMIN_USERS`、飞书事件订阅安全 `FEISHU_VERIFICATION_TOKEN` / `FEISHU_ENCRYPT_KEY`（均标敏感字段、密码控件）、飞书发送形态 `FEISHU_MAX_BYTES` / `FEISHU_SEND_AS_FILE` / `FEISHU_FOLDER_TOKEN` 与 `EMAIL_SENDER_NAME`（复用已有 `settings.notification.email` 帮助组）。本批的入库标准是“运行时存在读取方”：企业微信（`WECOM_*` 4 键）与 `TELEGRAM_WEBHOOK_SECRET` 的适配器尚未实现，`DISCORD_BOT_STATUS` 无消费代码，因此这 6 个键继续留在 `WEB_SETTINGS_PENDING_EXPOSURE`，不造出“能保存但没人读”的字段。重启边界按真实读取路径区分并在 `TestP3BotFieldsRegistered` 中锁定：`BOT_COMMAND_PREFIX` / `BOT_ADMIN_USERS` 由命令分发器单例首次构建时读取（保存链路不重置分发器）、飞书事件 Token / 密钥由 Stream 客户端建连时读取，均需重启；`BOT_ENABLED` 按请求读取、其余 4 个按通知实例读取，保存后下一次即生效。`FEISHU_MAX_BYTES` 的校验下限与 `parse_env_int(minimum=1)` 一致且不新增上限；同时记录 `BOT_ENABLED` 走 `.lower() == 'true'`（大小写不敏感，但 `1` / `yes` 等同关闭）与 `FEISHU_SEND_AS_FILE` 走 `in ('true', '1', 'yes')`（接受 `1` / `yes`）的解析口径差异。运行时零改动（未新增 `os.getenv`、未改默认值/区间/归一逻辑），`GET /api/v1/system/config` 载荷多 9 个键，其余键不变；新增 `docs/full-guide.md` / `docs/full-guide_EN.md`「机器人与事件回调配置」小节，`docs/bot-command.md` 中英同步设置页入口与生效边界，并修正其中 `bot_enabled: bool = False` 与运行时默认值（`True`）不一致的文档飘移。
- [文档] 写明“设置页保存即生效”的部署边界：`docs/full-guide.md` / `docs/full-guide_EN.md` 与 `docs/settings-help.md` 补充两类例外——容器 / 进程启动时注入的同名环境变量会在下次重启覆盖运行时文件中的保存值；GitHub Actions 每日任务（`.github/workflows/00-daily-analysis.yml`）不创建也不恢复 `.env`/`ENV_FILE`，其 `environment:` 注入的键（包括本批的 `FEISHU_FOLDER_TOKEN` / `FEISHU_SEND_AS_FILE` / `EMAIL_SENDER_NAME`）在该场景以仓库 Variables / Secrets 为唯一真源，修改设置页不会影响每日任务。仅文档澄清，未改变任何配置读取、保存或优先级逻辑；其余被同一 workflow 注入的已注册键的逐字段帮助文案本轮未一并改写，已登记为待决策项。
- [chore] `src/application/` 跨层私有访问清零，守卫补私有成员规则（P3 切片 14）：`HistoryService` 被用例层复用的 4 个下划线辅助提升为公开方法（`serialize_created_at` / `history_code_filter_candidates` / `display_stock_code` / `display_market_phase_summary`），`src/application/history/service.py`（6 处）、`src/services/alert_worker.py`、`tests/test_analysis_history.py` 同步改名；纯改名，实现体零改动（HEAD 机械套用同一重命名后，与当前文件剥离 docstring 的 AST dump 完全一致），URL / 响应字段 / 序列化口径 / `stock_bar` 取值均无变化。架构守卫新增基于 AST 属性访问的私有成员规则（仅 `src/application/` 启用，`self._x` / `cls._x` / dunder 放行，基线键使用 `private:` 命名空间与 import 键不冲突），落地时全仓 0 处违规，基线保持 5 条（均在 `src/services/`）无需重写；守卫测试 15 → 19 项（含真实工作树 `private:` 违规为 0 的锁定）。`ARCHITECTURE_TARGET.md` §2 同步“复用未下沉实现只能调公开成员”。全量离线 5391 passed / 31 failed / 10 errors，失败集与切片 13 逐项一致，0 新增失败。
- [chore] `src/` → `bot/` 反向依赖清零，守卫补 `src/` 兜底（P3 切片 13）：入站消息值对象 `BotMessage` / `ChatType` / `Platform` 从 `bot/models.py` 下沉到 `src/schemas/bot_message.py`（`bot/models.py` 109 → 17 行，只留 `BotResponse` / `WebhookResponse`；`from bot import BotMessage, ChatType` 仍可用），消除 `src/core/pipeline.py` 与 `src/services/task_service.py` 对 `bot.models` 的依赖；飞书回复客户端 `FeishuReplyClient` 整类迁移到 `src/notification_sender/feishu_reply_client.py`（与 HEAD 版 AST/源码逐字一致），`bot/platforms/feishu_stream.py` 714 → 513 行并继续导出同名符号，`src/notification.py` 的方法内 `bot.platforms` 惰性导入改走新模块。架构守卫新增 `src/` 兜底规则（禁 `api.` / `bot.`，具体规则优先），覆盖根模块与未单列子树含函数内导入；基线 7 → 5 条（剩余全部在 `src/services/`），新增 2 项守卫回归测试；`docs/bot-command.md` / `docs/bot-command_EN.md` 同步消息模型落点。全量离线 5387 passed / 31 failed / 10 errors，失败集与切片 12 逐项一致，0 新增失败。
- [chore] bot 命令接入会话用例与代码归一化薄包装，`bot/` 跨层直连清零（P3 切片 12）：`bot/commands/ask.py`（`data_provider.base` + `src.storage`）、`bot/commands/chat.py` / `bot/commands/history.py`（各 1 条函数内 `src.storage`）、`bot/dispatcher.py`（函数内 `data_provider.base`）共 5 条依赖一次归零。`/history` 三个分支改走 `AgentConversationService.list_sessions / get_messages / delete_session`，`/chat` 的 legacy 会话兼容判定改走 `session_exists`，`/ask` 的代码归一化改走 `canonical_stock_code_for_input`、写库前预热改走 `src.bootstrap.database.get_database_manager()`。用例新增 `session_exists` 与可选 `extra_session_ids`（默认仍为 `[user_id]`，`api` 侧调用不变）；命令、别名、参数解析、用户隔离规则、回复文案与异常分支均未变化，不涉及 API / Schema / Web / Desktop。已在 43 组数据下与 HEAD 版 4 个 bot 模块逐项比对（全等，0 组差异），架构守卫 `bot/` 五条基线归零（12 → 7 处 / 12 → 7 键，**`api/` 与 `bot/` 直连均为 0**），新增 15 项分层与用例契约回归测试。
- [chore] 板块端点接入市场用例与数据源适配器，`api/` 数据源直连清零（P3 切片 11）：`api/v1/endpoints/sector.py` 的四条跨层依赖（`data_provider.sector.{eastmoney,market_cards,shidaotec,stocksdk}_source`）一次归零，链路改为端点 → `src/application/market/sector.py`（`SectorService`：响应信封、字段投影、空数据降级）→ `src/infrastructure/providers/sector_provider.py`（来源优先级与快照错误翻译）→ `data_provider/sector/*`（各来源 TTL 缓存与真实请求原位不变）。与切片 10 不同，本片的选源不在数据源包内部而在端点里，`_prefer_stocksdk_then_fallback` / `_prefer_loader_chain` 两段编排随依赖一起下沉，顺序、异常吞噬范围与日志文案逐字保留。端点 357 行降至 271 行，`api/deps.py` 新增 `get_sector_service`；URL、Query 声明（`time` / `market` / `period` / `top_n` / `limit` / `sector_codes`）、16 条路由的响应字段、400/404/502 状态码与错误文案均未变化，前端无需改动。行为边界：`{"indices": [...]}`、`{"sectors": [{code,name}]}`、`{sectorType,total,boards}` 与北向/主力资金占位载荷从端点移到用例；新增 `SectorSnapshotUnavailableError`（非 `LookupError` 子类）承接历史快照缺失，避免与资金流历史的「代码不存在 → 404」混淆。已在 41 组数据下与 `HEAD` 版端点逐项比对（全等，0 组差异），并用裸 FastAPI 验证 200/400/404/502 与 Query 透传；架构守卫 `sector.py` 四条基线归零（16 → 12 处 / 16 → 12 键，**`api/` 数据源直连降为 0**），`tests/test_sector_endpoint_refactor.py` 由 12 项重写扩充至 32 项用例/适配器/HTTP 契约回归测试。
- [chore] K 线端点接入行情用例与数据源适配器（P3 切片 10）：`api/v1/endpoints/kline.py` 的三处跨层依赖（`data_provider.code_search.base` / `kline.base` / `stock_info.base`）一次归零，链路改为端点 → `src/application/quote/`（`QuoteService`：对外契约整形）→ `src/infrastructure/providers/kline_provider.py`（`KLineResult` / `StockInfoResult` / `CodeSearchResult` → 字典）→ `data_provider` 各能力 Manager（选源、回退、TTL、健康冷却原位不变）。端点 179 行降至 156 行，`api/deps.py` 新增 `get_quote_service`；URL、Query 校验（`period` 正则 / `limit` 1–10000 / `fqt` 0–2）、三类响应 Schema、404/422/502 映射与短 TTL 响应缓存（K 线 60s / 信息 30s / 搜索 300s）均未变化，前端无需改动。行为边界：成交量仍按「手」输出（`volume / 100`）并剔除行内 `prev_close`，这些整形从端点移到用例层；新增应用层 `QuoteDataError` 承接「上游行结构不合契约」，使该场景从原先未捕获的 500 变为受控的 502，而不是被 `ValueError → 422` 误判为参数错误。已在 12 组数据下与 `HEAD` 版端点逐字段比对（全等，0 组非预期差异），并用裸 FastAPI 验证 200/404/422/502 与 Query 校验；架构守卫 `kline.py` 三条基线归零（19 → 16 处 / 19 → 16 键，`api/` 降至 4 处 / 4 个键，仅剩 `sector.py`），新增 19 项用例/适配器/HTTP 契约回归测试。
- [chore] 股票端点的代码归一化归口（P3 切片 9）：`api/v1/endpoints/stocks.py` 唯一的跨层依赖 `data_provider.base` 消除，改由 `src/services/stock_code_utils.normalize_stock_code_for_stock_list` 承担 STOCK_LIST 写入标准化与自选增删匹配键；包装仍调用同一个 `normalize_stock_code`，未新建平行实现。该依赖是无 I/O 的纯函数（无选源、无缓存、无降级），因此不套用切片 8 的「端口 + 适配器」样板，避免三层空壳。URL、请求/响应 Schema、HTTP 状态码、400 错误体、`_STOCK_CODE_RE` 校验分支与 `_watchlist_match_key` 的「5 位裸码补 `HK` 前缀 + 统一大写」规则均零改动（`700` 与 `00700` 仍是两个不同匹配键，属既有行为并已用测试显式锁定）。架构守卫 `stocks.py → data_provider` 基线归零（20 → 19 处 / 20 → 19 键，`api/` 降至 7 处 / 7 个键，剩余全为 `kline.py` / `sector.py` 的数据源直连），新增 13 项回归测试（含 16 个代码样本的跨包装等价校验）。
- [chore] 涨跌停榜单端点接入应用用例与数据源适配器（P3 切片 8）：`api/v1/endpoints/limit_pool.py` 唯一的跨层依赖 `data_provider.limit_pool` 消除，链路改为端点 → `src/application/market/limit_pool.py`（`LimitPoolService`：榜单类型词汇 + 失败降级为空榜）→ `src/infrastructure/providers/limit_pool_provider.py`（`LimitPoolResult` → 明细字典）→ `data_provider/limit_pool`（选源、回退、60s TTL、健康冷却仍由该 Manager 负责，适配器不重写，避免出现第二套降级规则）。用例落点按 `ARCHITECTURE_TARGET.md` §3 的业务域取 `application/market/`（市场情绪 / 热点榜单），不按端点名新建 `application/limit_pool/`，装配同域收敛到 `src/bootstrap/market.py`。端点 75 行降至 62 行，`api/deps.py` 新增 `get_limit_pool_service`；URL、`limit` 1–200 校验、`{date, items}` 响应体与 13 字段明细契约零改动，`date` 缺省仍回显当天 `YYYYMMDD`，前端无需改动。唯一行为差异是「明细序列化异常」从 500 变为降级空榜（旧实现 `to_dict()` 写在 `try` 之外），已由测试显式锁定。已在 4 类数据 × 4 组入参下与 `HEAD` 版 `_load_board` 比对（12 组全等 / 4 组为上述预期差异 / 0 组非预期差异），并用裸 FastAPI 验证 5 个 HTTP 用例；架构守卫 `limit_pool.py` 基线归零（21 → 20 处 / 21 → 20 键，`api/` 降至 8 处 / 8 个键），新增 13 项用例、适配器与分层回归测试。
- [chore] 分析端点去持久化 + 代码归一化归口（P3 切片 7）：`api/v1/endpoints/analysis.py` 的 4 处跨层依赖全部消除——状态查询（`GET /analysis/status/{task_id}`）、任务运行流（`GET /analysis/tasks/{task_id}/flow`）与同步分析结果回填不再在函数体内构造 `DatabaseManager` 直读 `get_analysis_history` / `get_latest_fundamental_snapshot`，改为 `Depends(get_history_query_service)` 注入既有 `HistoryQueryService`（本片为其补充 `get_latest_by_query_id` 与 `get_run_flow` 的 `code` / `report_type` 过滤），`/analysis/*` 存量查询语义与 fail-open 行为不变；股票代码归一化（`canonical_stock_code` / `normalize_stock_code`）收口到 `src/services/stock_code_utils.py` 的两个语义化包装，端点不再 import `data_provider.base`。端点 1505 行增至 1521 行（+48/-32，均为依赖注入与类型标注），URL、Query、响应 Schema、404/500 错误体均未变化，前端无需改动。已在临时库造 6 条历史 + 2 条基本面快照，与 `HEAD` 版端点比对 19 组输出全等（运行流 7 / 状态查询 4 / 同步回填 8，并断言命中最新一条而非最早一条），并用裸 FastAPI 验证 9 个 HTTP 用例；架构守卫的 `analysis.py` 4 条基线归零（25 → 21 处 / 23 → 21 键，`api/` 降至 9 处 / 9 个键），新增 10 项依赖接线与端口语义回归测试。
- [chore] Agent 会话端点改为应用用例调用（P3 切片 6）：`api/v1/endpoints/agent.py` 的三个会话路由（会话列表 / 单会话消息 / 删除会话）不再在函数体内 `from src.storage import get_db` 直连管理器，改为 `Depends(get_agent_conversation_service)`；会话读取编排与 `user_id` 的「前缀隔离 + 精确包含自身」下沉到新增的 `src/application/agent/`（`AgentConversationService` + `AgentConversationPort`），仓储由 `ConversationRepository` 结构匹配，装配落在新增的 `src/bootstrap/agent.py`。端点 637 行增至 643 行（净 +6，均为依赖注入与类型标注），`/chat`、`/chat/stream`、`/research` 等其余 9 条路由与流式逻辑零改动；URL、Query、响应 Schema、状态码均未变化（不存在的 session 仍返回 200 + 空列表，重复删除仍返回 `{"deleted": 0}`），前端无需改动。已在临时库造 5 条消息（含 `telegram_1` 与 `telegram_10` 的前缀边界）与 `HEAD` 版端点比对 8 组读输出全等，删除在两个独立库各跑一次结果一致，并用裸 FastAPI 验证 9 个 HTTP 用例；架构守卫的 `agent.py → src.storage` 基线归零（28 → 25 处 / 24 → 23 键，`api/` 降至 13 处 / 11 个键），新增 10 项路由契约与用例回归测试。
- [chore] 回测端点装配归位（P3 切片 5）：`api/v1/endpoints/backtest.py` 的 4 个路由不再 `Depends(get_database_manager)` 并自行构造 `BacktestService(db_manager)`，改为 `Depends(get_backtest_service)`；装配收敛到新增的 `src/bootstrap/backtest.py`（显式绑定当前 `DatabaseManager` 单例，不缓存实例），`api/deps.py` 增加 `get_backtest_service`。端点 241 行降至 236 行，不再 import `src.storage` / `get_database_manager`；`src/services/backtest_service.py` 零改动，URL、Query 区间（`run.limit` 1–2000 / `results.limit` 1–200 / `eval_window_days` 1–120）、响应 Schema、400/404/500 错误体均未变化，前端无需改动。已在临时库造数（3 条历史 + 3 条结果 + 2 条汇总）与 `HEAD` 版端点比对 7 组输出全部全等（`results` 全量/按代码/日期过滤/分页、`performance` overall/stock、不存在代码 404），并用裸 FastAPI 验证 11 个 HTTP 用例（4×200 / 2×400 / 4×422 / 1×404）；架构守卫的 `backtest.py → src.storage` 基线归零（29 → 28 处，`api/` 降至 16 处 / 12 个键），新增 9 项路由契约回归测试。
- [chore] 分析历史端点改为应用用例调用（P3 切片 4）：`api/v1/endpoints/history.py` 的 9 个路由不再持有 `DatabaseManager` 句柄——列表/详情/诊断/运行流/新闻/Markdown 的读取编排、按股票代码分批删除（批次 10,000，无进展即报错）、个股栏归一化去重与 `fetch_limit = min(limit*3, 500)` 均迁入 `src/application/history/`（`HistoryQueryService`），读模型重建仍委托既有 `HistoryService`，股票代码归一化由 `src/infrastructure/indexing/stock_code_normalizer.py` 适配 `data_provider.base.normalize_stock_code`，装配落在 `src/bootstrap/history.py` 并由 `api.deps.get_history_query_service` 注入。端点 813 行降至 640 行，不再 import `src.storage` / `data_provider.base`；URL、Query 区间（`limit` 1–100 / 个股栏 1–500）、响应 Schema、404/400/500 错误体均未变化，前端无需改动。已在真实开发库上与 `HEAD` 版端点比对 19 组输出（`list` / `stock_bar` / `detail` / `diagnostics` / `flow` / `news` / `markdown`）全部全等；架构守卫的 `history.py → src.storage` 与 `→ data_provider.base` 两条基线归零（29 → 27 处，`api/` 降至 17 处 / 13 个键），新增 7 项用例回归测试。
- [chore] 数据库依赖归位到 bootstrap（P3 切片 3）：`get_db`（请求级 Session 依赖）与 `get_database_manager`（进程单例）从 `api/deps.py` 搬到新增的 `src/bootstrap/database.py`，`api/deps.py` 只做原样转出，不再 import `src.storage`（107 → 69 行）。函数对象身份保持不变（`is` 比对为真），因此 `Depends(...)`、`dependency_overrides[...]` 与所有调用方零改动；建库时机、Session 关闭语义、单例行为均未变化。架构守卫的 `api/deps.py → src.storage` 基线归零（32 → 31 处，`api/` 降至 19 处 / 15 个键），新增 3 项装配/关闭语义回归测试。
- [chore] LLM 用量端点改为应用用例调用（P3 切片 2）：`api/v1/endpoints/usage.py` 不再直连 `DatabaseManager`——时间窗语义（`today` / `month` / `all`，北京时间，非法值回退 `month`）与读模型组装迁入 `src/application/usage/`（`UsageService`，`now` 可注入），端口 `UsageRepositoryPort` 由既有 `LLMUsageRepository` 结构匹配实现，装配落在 `src/bootstrap/usage.py` 并由 `api.deps.get_usage_service` 注入。端点 100 行降至 43 行；URL、Query 校验（`limit` 1–200）、响应 Schema 与字段过滤均未变化，前端无需改动。已在真实开发库上对 4 个 period 值比对迁移前后 summary / dashboard 输出（8 组 JSON 全等）；架构守卫的 `usage.py → src.storage` 基线归零（33 → 32 处），新增 7 项用例回归测试。
- [chore] 自选股端点改为应用用例调用（P3 首片）：`api/v1/endpoints/watchlist.py` 不再直连 ORM 与 `DatabaseManager`——业务规则（名称/股票代码校验、分页换算、业务错误类型）迁入 `src/application/watchlist/`，SQL 迁入 `src/infrastructure/persistence/repositories/watchlist_repo.py`（查重与写入同在单个 `_run_write_transaction` 内，保留 `BEGIN IMMEDIATE` 一致性窗口），股票代码核验包装为 `src/infrastructure/indexing/stock_code_validator.py`，装配落在 `src/bootstrap/watchlist.py` 并由 `api.deps.get_watchlist_service` 注入。端点 432 行降至 256 行；URL、请求/响应 Schema、HTTP 状态码与错误体均未变化，前端无需改动。架构守卫的 `watchlist.py → src.storage` 与 `→ persistence.models.watchlist` 两条基线归零（35 → 33 处），新增 8 项用例/仓储回归测试。
- [chore] 持久化业务方法分域拆分：`DatabaseManager` 上混杂的查询/写入方法迁到 `src/infrastructure/persistence/repositories/`（`market_data_repo` / `intelligence_repo` / `analysis_history_repo` / `conversation_repo` / `llm_usage_repo` 与共享纯函数 `_common`），`src/storage.py` 由 2180 行降至 1038 行，只保留仓储装配、单例与会话入口、14 个 `_ensure_*` 委托、24 个业务方法同名委托，以及被测试按类名直接引用的 `_parse_sniper_value` 等静态辅助。SQL、事务边界与返回值不变：写入仍走 `_run_write_transaction`（`BEGIN IMMEDIATE` + 退避重试），删除分析历史仍在同一事务内级联清理决策信号 / 回测结果 / 技能样本。`src/repositories/` 的既有应用仓储本轮不动（留待 P5 收口），无表结构或数据迁移。
- [chore] 会话生命周期与启动期 schema 升级从 `src/storage.py` 分拆：新增 `src/infrastructure/persistence/session.py`（`DatabaseSession`：建引擎、SQLite `busy_timeout` / WAL PRAGMA、Session 工厂、`BEGIN IMMEDIATE` + 指数退避的写事务重试、`atexit` 释放）与 `src/infrastructure/persistence/schema_compat.py`（全部 `_ensure_*` 迁移与 `apply_startup_migrations()`）。`DatabaseManager` 的对外入口、单例幂等、建表后迁移顺序、锁重试与 PRAGMA 行为均未变化，`_ensure_*` 保留同名委托方法供测试与运维脚本调用；`src/storage.py` 由 2844 行降至 2180 行。测试中 `time` / `inspect` / `create_engine` 的 patch 目标同步重定向到真实模块，写重试测试改为 patch `DatabaseSession.create_session`。无表结构或数据迁移。（业务查询/写入方法已在 P2-B2b 继续分拆，见上一条）
- [chore] 持久化基座原子拆分：唯一 ORM `Base`、UTC 时间归一化（`utc_naive_now` / `to_utc_naive_datetime`）与 schema 版本常量从 `src/storage.py` 移到 `src/infrastructure/persistence/base.py`，32 个 ORM 模型按业务域拆到 `src/infrastructure/persistence/models/{market_data,intelligence,analysis,portfolio,agent,alert,decision,watchlist,schema}.py`，导入 `models` 包即完成注册。`src/storage.py` 由 4235 行降至 2844 行，只保留 `DatabaseManager`、会话生命周期、schema 兼容升级与 `persist_llm_usage`（后两项已在 P2-B2a 继续分拆，见上一条）。同步迁移 `src/repositories/` 与 `api/v1/endpoints/watchlist.py` 的模型导入，文档中的旧落点同步修正。表名、列名、约束、索引与 `create_all` → `_ensure_*` 顺序均未变化，无数据迁移；已用逐类 AST 比对与开发库 32/32 表对照验证零漂移。
- [chore] 配置事实源原子包化：`src/config.py` → `src/config/settings.py`（运行时值、`setup_env()`、`get_config()`）、`src/core/config_manager.py` → `src/config/env_file.py`（`.env` 原子读写）、`src/core/config_registry.py` → `src/config/registry.py`（设置页字段元数据），并新增 `src/config/__init__.py` 门面转发，业务代码的 `from src.config import Config, get_config` 不变。旧三个文件已物理移除，不留双份实现或兼容 shim。同步迁移全仓 import、测试 patch 目标（门面属性与实现模块在包化后不再是同一对象，patch 目标逐个按调用路径确认）、`ci_gate.sh` / `test.sh` 语法检查路径，以及 docs / SKILL.md 中的旧路径引用。无运行时行为、API、Schema 或设置页渲染变化。
- [新功能] Web 设置页新增 16 个资讯源配置字段：实时快讯（`WSCN_LIVE_NEWS_*` 7 个）、财经日历（`WALLSTREETCN_CALENDAR_*` 4 个）、本地资讯池（`NEWS_INTEL_*` 4 个）与 NewsNow 聚合源（`NEWSNOW_BASE_URL`）。此前这些键只能改 `.env`，而它们直接决定「行情资讯」下的快讯 / 日历 / 资讯池是否有数据。help 文案按能力分为 `live_news` / `live_calendar` / `news_intel` / `newsnow` 四组；数值字段的校验区间与 `parse_env_int` / `parse_env_float` 的 clamp 边界一致，`TestP2NewsFieldsRegistered` 通过真实 `Config._load_from_env()` 反证越界值会被收敛到同一区间。同时把缺失的四项 `WALLSTREETCN_CALENDAR_*` 补入 `.env.example`，并新增「资讯源配置」文档小节。
- [新功能] Web 设置页新增 14 个数据源配置字段：板块 / 涨跌停池路由（`SECTOR_*` / `LIMITPOOL_*` 各 3 个）与外部行情凭证（`ALPHAVANTAGE_API_KEY`、`FINNHUB_API_KEY`、`LONGBRIDGE_*` 4 个、`SOCIAL_SENTIMENT_*` 2 个）。此前这些键只能在 `.env` 中修改，Docker、桌面端和云端用户无法在设置页配置。路由字段沿用 `KLINE_*` 的 select / switch 形态并补齐中英文帮助；凭证字段使用 password 控件并标记敏感。`SECTOR_*` / `LIMITPOOL_*` 保存后运行时重载即生效；凭证字段在设置页保存后同样立即生效，但进程启动时若容器环境变量存在同名键仍以容器值为准，重启后需同步更新或移除该 override。新增 `TestP1DataSourceFieldsRegistered` 锁定字段注册形态，并校验 `SECTOR_DATA_SOURCE` / `LIMITPOOL_DATA_SOURCE` 的 options 与各 manager 真实注册的 source 一致。
- [文档] 修正 full-guide 中英「外部行情凭证」的优先级说明：原文写“容器环境变量优先于设置页保存值，需重启容器才生效”，与保存链路不符——不在 `_WEBUI_RUNTIME_ENV_FILE_PRIORITY_KEYS` 内的键在进程启动时确实以容器环境变量为准，但设置页保存后 `update()` 走 `setup_env(override=True)`，`.env` 新值会覆盖同名 `os.environ` 并立即生效，下一次重启才会被同名容器变量重新覆盖。两份 full-guide 已改为分语义表述，并给「资讯源配置」补同一条注意事项。
- [改进] 建立 Web 设置页配置可见性契约：`src/config/registry.py` 将未注册的运行时键拆分为 `WEB_SETTINGS_HIDDEN_FROM_UI`（运维/内部调优）、`WEB_SETTINGS_PENDING_EXPOSURE`（按 P1–P6 批次待注册的功能字段，P1 / P2 的 30 个已注册，其余 29 个待续）和 `WEB_SETTINGS_LEGACY_ALIASES`（4 个新旧键名兼容别名）三张声明表，并新增 `TestUnregisteredConfigKeysDeclared` 守卫：`src/config/settings.py` 的每个 `os.getenv` 键必须已注册或已声明，三张表与注册表互不相交、彼此不重叠、不得残留失效键，legacy 别名必须指向已注册的 canonical 键。此前 95 个未注册键中有 80 余个从未被任何测试覆盖（`.env.example` 守卫只校验未注释的激活键），新增 env 键可以静默变成“设置页不可见、只能改 .env”的隐形配置。本次不改变任何运行时行为与设置页渲染结果。
- [文档] 补齐 StockDB / StockSDK / K 线、股票信息、代码搜索路由共 21 个数据源配置项的 Web 设置页帮助元数据（`help_key` / `examples` / `docs`）与中英文帮助文案，并在 `docs/full-guide.md` / `docs/full-guide_EN.md` 新增「数据源路由与本地桥接」小节。这些字段自「统一数据源策略」重构引入后一直未注册 `help_key`，导致 `test_web_settings_visible_fields_have_help_metadata` 持续失败；本次按数据源族共用 `help_key` 收敛（与既有 `settings.data_source.pytdx` 一致），不改变任何运行时默认值或配置语义。
- [修复] 修复组件文档页 HrsSelect「示例四：尺寸对比（size）」四个选择器横向互相堆叠的问题。根因：`HrsSelect` 根元素内置固定宽度 `w-50`（200px），而示例四每列容器为 `max-w-40`（160px），flex 行内列间距 160+24=184px 小于 select 实际宽度，每个 select 向右溢出约 16px 压住相邻列，后渲染的兄弟节点绘制在上层即形成堆叠（其余示例容器为 `max-w-64`/`max-w-72`，均 ≥ 200px 故未暴露；`CodeTestPage` 同类尺寸对比用 `w-56` 亦无此问题）。修复：示例四列宽由 `max-w-40` 改为 `w-50`，与组件实际宽度匹配，并加注释说明该约束。已用等价 DOM 在浏览器实测四列间距 224px、零重叠，各档位触发器高度（h-7 / h-8 / h-9 / h-10）正常区分。
- [改进] 持仓页（`/trading/portfolio`）持仓表格改为与自选股页一致的贴底填充，随窗口变高而变高：原实现按「每页行数 × 估算行高 + 余量」算死高度（`10×44+64`、上限 560），既不随窗口变高，也与页头 / 提示条 / TAB 的实际占位无关。改用上一期新增的结构性方案——`Table` 的 `fillHeight`（wrapper 以 `flex-1 min-h-0` 占据剩余空间、滚动交还内部 ScrollContainer）；因本页未走 `AppPage`，在页面根（`Main` 的直接子节点）用 `flex min-h-full flex-col` + grid `flex-1 min-h-0 items-stretch` + 右栏 `flex h-full min-h-0 flex-col` 自建同构高度链，左栏账户面板原有的 `h-full` 随之生效。翻页稳定性反而增强（高度由 flex 决定、与当前页行数天然无关，末页行数少也不塌陷）。另设 `POSITION_TABLE_MIN_HEIGHT = 320` 下限兜底：页面顶部最多可同时出现账户 / 写入拦截 / 错误 / 风险降级 / 快照口径等多条 InlineAlert，全部出现时低于该高度每页 10 行只剩三四行可见，触顶改为让页面长高并由 `Main` 滚动；总览 / 集中度 / 事件三个非填充面板包 `shrink-0` 防被压缩裁剪。已用「真实 Table + 真实 AnimCard」复刻完整高度链在 720 / 900 / 1080 三档视口验证贴底零空隙，并验证 6 条提示条压测下页面长高、`Main` 可滚动。
- [修复] 修复市场总览页（`/market/index`）指数卡涨跌幅 / 涨跌点数为 `--` 且全部数字呈灰色的问题。根因：前端类型统一（`MarketIndexItem` 改名 `changePercent`→`changePct`、`preClose`→`prevClose`）时未同步 `/market-indices` 与 `/market-cards` 的 index_quote payload 适配层，后端契约仍返回 `changePercent` / `preClose`，`getChangeColorClass(undefined)` 落灰色分支、`formatPercent(undefined)` 渲染 `--`，实时行情实际已到端但无法展示。修复遵循「后端契约不动、差异由前端适配层消化」的既定策略：`apps/hrs-web/src/api/sectorData.ts` 新增 `toMarketIndexItem` 适配函数（与 `kline.ts` 的 `toStockSnapshot` 同模式），`fetchMarketIndices` / `fetchGlobalIndices` / `fetchAsiaIndices` / `fetchMarketCards` 返回前统一归一字段，其余卡片（涨跌家数 / 涨跌停 / 成交额 / 北向 / 主力 / 最强板块）字段本就与后端一致，原样透传；补充 4 条 api 层回归测试锁定适配契约。
- [修复] 修复涨跌榜页面（`/emotion/boardlist`）涨停 / 跌停榜单表格下方空出一段、未贴底适配的问题（浏览器全屏时最明显）。根因有两层：① 表格高度写死为 `height="calc(100vh - 380px)"`，380px 是对「页头 + TAB + KPI 卡 + 内边距」的魔法数估算，全屏时 `100vh` 变为屏幕高度而页头 / KPI 卡不同步变化，减数失配即留出空隙，窗口缩放与 KPI 卡换行同样失配；② 更深的链路问题——`AppPage` 仅有 `min-h-full`（高度随内容），下游一路 `height:100%` 在 auto 高度父级上全部退化为 `auto`，面板其实从未撑满，固定高度只是"猜"了一个值。改为结构性贴底：`Table` 新增 `fillHeight`（忽略 height，外层 wrapper 以 `flex-1 min-h-0` 占据剩余空间、滚动交还内部 ScrollContainer）；`AppPage` 新增可选 `fill`（默认 false，不影响其它页面）转为 flex 列以给出确定高度；涨跌榜页面根与两个榜单面板改用 `flex-1 min-h-0`。内容超高时容器仍随内容长高、由 `Main` 滚动，长页面不受影响。已用等价 DOM 副本与「真实 Table + 真实 AppPage」两种方式在 720 / 900 / 1080（全屏）三种视口高度下验证贴底零空隙，并验证流式超高内容仍可滚动。
- [chore] 已知遗留（**独立 follow-up，不随本次改动处理**）：`cd apps/hrs-web && npm run build` 当前失败（退出码 2，27 个 TypeScript 错误），`npm run lint` 另有 67 errors / 7 warnings；涉及 `KLineView.tsx` / `KLineView.test.tsx` / `ChatPage.tsx` / `ReportNews.tsx` / `ReportOverview.tsx` / `ShellHeader.tsx` / `SidebarNav-old.tsx` / `StockSearchList.tsx` / `UniverseBackground.tsx` / `DecisionSignalsPage.tsx` / `Docs_toast.tsx` / `appRouter.tsx` / `PageStateStore.tsx` / `reviewPage.tsx` / `RouteErrorBoundary.test.tsx` 等既有文件。均为**既有问题**，与涨跌停端点改名无关（改动文件在 lint / build 输出中零命中）。影响：阻断 CI `web-gate`（lint + build），需独立 PR 修复后再合入前端改动。
- [改进] 涨跌停池按 ADR-001 §10.2 B2 下沉到 `data_provider/limit_pool/`：新建能力包（`base` + `eastmoney_source` + `stocksdk_source`），固化 `LimitPoolEntry` 契约（13 字段）；`get_limit_up_pool` / `get_limit_down_pool` 从 `data_provider/base.py` 巨类移除（`akshare_fetcher.py` 按 §4.4 保留为物理后端由 `eastmoney_source` 复用），涨跌停数据收口为唯一入口——`/api/v1/limit-pool/*` 与技术信号扫描均经 `LimitPoolDataSourceManager` 取数；端点自建 60s 缓存删除、改由 Manager 统一 TTL，**修复"取数失败也把空结果缓存 60s"的缺陷**；新增 `LIMITPOOL_*` / `SECTOR_*` 配置键并同步 `.env.example` 与运行时白名单。API 响应契约与前端行为不变（`stocksdk` 源因 bridge 无涨跌停 action 暂不可用，实际仍为东财单源）。
- [改进] 涨跌停榜单后端端点按能力域重命名：文件 `api/v1/endpoints/emotion.py` → `limit_pool.py`，路由前缀 `/api/v1/emotion` → `/api/v1/limit-pool`（即 `GET /api/v1/limit-pool/limit-up-board` / `limit-down-board`），前端接口封装 `apps/hrs-web/src/api/emotionData.ts` → `limitPoolData.ts`。原因：端点命名不应绑定前端「情绪」菜单分组——菜单会重组、页面会迁移，能力域不会；该原则已写入 ADR-001 §5.3「登记与命名公约」。**不兼容变更**：旧路径 `/api/v1/emotion/*` 停止提供，前端为唯一消费方已同步改造，无兼容层。
- [新功能] 新增「情绪」一级菜单（位于「行情」之下）及其下的「涨跌榜」二级页面（路由 `/emotion/boardlist`）：页面布局参考 `/market/index`，含标题与「涨停榜单 / 跌停榜单」两个 TAB；**涨停榜单已实现表格**（代码 / 名称 / 现价 / 涨幅 / 涨停时间 / 连板 / 封单额 / 成交额 / 换手率 / 所属行业，支持按连板、封单额、成交额等排序），数据来自新增后端 `GET /api/v1/emotion/limit-up-board`（复用 DataFetcherManager.get_limit_up_pool 的 akshare 东财涨停池，加 60s TTL 缓存）。新增 zh / en / zh-Hant 三语菜单、TAB 与表头文案。
- [新功能] 涨跌榜页面完善：涨停 / 跌停榜单表格上方新增 KPI 指标卡组——涨停榜为涨停数量 / 连板高度 / 封单总额 / 炸板率 / 昨日涨停溢价（前三项由涨停池实时聚合，炸板率与昨日涨停溢价待炸板股池 / 昨日涨停池接入后以 `--` 占位补数）；跌停榜为跌停数量 / 跌停连板高度 / 封停单总额 / 跌停成交额 / 平均换手率（全部由跌停池实时聚合）。跌停榜单 TAB 完成实现：后端新增 `GET /api/v1/emotion/limit-down-board` 与 `DataFetcherManager.get_limit_down_pool`（akshare 东财跌停股池，字段与涨停池归一为同一 schema，连板数表示连续跌停次数、封板时间取最后封板时间），60s TTL 缓存与多源回退范式同涨停榜。前端榜单列定义、指标聚合与面板泛化为涨停 / 跌停共用模块（`LimitBoardPanel` / `boardColumns` / `boardMetrics`，表头仅「涨停时间 / 跌停时间」按看板语义区分），代码 / 名称列点击跳转个股 K 线页（统一 `?stockCode=` 协议）；涨跌停字段在 `types/stock.ts` 收敛为 `LimitBoardQuote` 单一真源并提供涨停 / 跌停语义别名。连板数值加粗，并按连板数以亮度递进着色（涨停越连越红、跌停越连越绿，10 板封顶，色号对齐 palette 设计令牌），KPI「连板高度」卡复用同一渐变色规则。
- [改进] 涨跌榜单接口提速：涨停 / 跌停股池取数原使用 2~5s 随机休眠的全量爬取限速，实测接口冷启动 3.6s / 5.8s；因榜单池为单次轻量 GET（与实时行情同级），改用轻量限速（0~0.3s），实测冷启动降至 0.39s / 0.25s，配合接口层 60s TTL 缓存，榜单切换可在 1 秒内完成渲染。
- [文档] 文档目录归并：后端架构 ADR `documents/架构设计/backend_architecture_adr.md` 移至 `documents/framework/`；`技术信号扫描` / `个股K线功能` / `尾盘选股` / `行情资讯` / `自选股管理` / `实时告警中心` 六个专题文档目录整体迁入 `documents/product/`；`docs/CHANGELOG.md` 迁至 `documents/CHANGELOG.md`（清理空目录 `docs/架构设计`、`docs/architecture`）；同步修正全仓 48 处旧路径引用（`src/` 注释、`apps/hrs-web/src/**` 注释、6 个测试文件的 Python 路径构造、`docs/INDEX*` 与 `FAQ*` 相对链接、GitHub blob URL 等），消除悬空链接。
- [文档] 前端路由与模块化菜单文档重构：将 `docs/authority/async-router.md` 与 `moduleMenu.md` 重写为描述已实现状态的方案文档，并重命名为 `documents/authority/frontend_async_router.md` / `frontend_module_menu.md`；`documents/架构设计/frontend_route_keepalive.md` 移至 `documents/authority/`；`documents/布局`→`layout`、`documents/组件使用示例`→`components` 目录重命名；`docs/architecture/api_spec.json` 移至 `documents/archify/`，并同步更新 `ScrollContainerContext.tsx`、2 个测试文件、`docs/INDEX*` 与 `decision-signals.md` 的旧路径引用。
- [改进] 自选股页（`WatchlistPage`）代码整理：统一参数 / 状态命名（排序字段、搜索关键词、备注编辑、分组表单等），精简冗余逻辑与过程性注释；「修改分组」弹框改用统一 `Modal` + `HrsSelect`，表格接入 `itemsLoading` 加载态；页面文案统一为「分组」（原「分类」表述），新增自选股弹框的描述标签修正为「自选股描述」。
- [修复] 修复分时缩略图（`KLineView`）在矮尺寸下被压成一条直线的问题：根因是 lightweight-charts 的 series markers（末端圆点）会参与价格轴 autoscale，且按像素高度换算——图表越矮撑出的价格范围越大（36px 缩略图被拉到约 6 倍数据宽度，全天 3% 的涨跌起伏只占 16% 高度）。改为用 `autoscaleInfoProvider` 显式锁定价格轴范围为「趋势线数据区间 + 可见昨收基准线」，渲染结果与图表高度、标记 / 均线无关；自选股列表分时缩略图占高从 16% 恢复到约 53%，尾盘选股结果卡片同步受益，并补 6 条回归测试。
- [新功能] 自选股列表新增「分时」列：复用 `KLineView` 渲染当日分时缩略图（价格趋势线 + 均价线 + 昨收基准虚线，红涨绿跌），数据源为新增的通用单票分时能力 `GET /api/v1/stocks/{code}/timeline`（东财 trends2，服务端 30s 缓存）；前端 `useWatchlistManager` 在行情之后按有界并发（3）懒加载分时并逐条合并，单只失败降级为占位「—」，不阻塞列表渲染。
- [重构] 新增 `src/services/intraday_timeline_service.py`，把单票分时取数（东财 trends2 `/get` 直连 + stock-sdk 桥接回退、全局节流、多 CDN 主机轮换、时间串标准化、KLinePoint 组装）从 `eod_picker_service` 下沉为共享能力；`eod_picker_service.fetch_intraday_timeline` 保留为兼容入口（内部委托同一实现），尾盘选股接口契约与行为不变。
- [修复] 修复 Web 通用 `Table` 组件列定义 `minWidth` 声明为必填但从未透传给 `HeroTable.Column` 的问题：现按列定义下发最小宽度，列被拖窄时不再低于该值（此前仅 `defaultWidth` 生效）。
- [改进] 路由缓存（Keep-Alive）实现改为基于第三方库 `keepalive-for-react@6` + `keepalive-for-react-router@6`（适配 React 19.2 / React Router v7）：黑名单单一配置、`maxCacheSize=8` LRU 上限、query/hash 变化重挂载、滚动位置保存/恢复等既有行为与配置入口不变；页面后台暂停改经库的 `useKeepAliveContext().active` 下发（reviewPage / StockDashboardPage / LiveNewsPage 接入）；因库官方要求开发模式下不能使用 StrictMode，`main.tsx` 移除 StrictMode 包裹（失去开发期双倍渲染自检）；删除自研的 `keepAliveCache.ts`、`PageActivityContext.tsx` 与原槽位实现。详见 `documents/authority/frontend_route_keepalive.md`（ADR-002 v4）。
- [新功能] 消息日历筛选：国家 / 地区由单选改为**多选**（`countryIds: string[]`，空数组 = 全部，含「全部国家/地区」一键清空）；hook 入参 `countryIds`（旧 `countryId` 保留兼容桥接）。
- [新功能] `HrsInput` 新增 `clearable`（默认 true）：输入内容后右侧出现 × 清除按钮，点击清空输入；以绝对定位覆盖实现，打字不丢焦点。
- [新功能] 新增「技术信号扫描（Scanner）」：路由 `/discover/scanner`，照搬参考项目 chengzuopeng/stock-dashboard 的界面与交互（左栏股票池来源 + 信号模板，右栏结果列表含命中信号与加自选、点击跳个股 K 线页）。后端 `src/services/scanner_indicators.py` 提供 8 个技术信号判定（MA/MACD 金叉死叉、RSI 超买超卖、BOLL 上下轨），`src/services/signal_scanner_service.py` 负责股票池解析（自选股 / 榜单 TopN / 涨停池）、并发 4 扫描与进度上报，`api/v1/endpoints/scanner.py` 提供 `GET /options`、`POST /tasks`、`GET /tasks/{id}`（运行中即返回增量结果）、`POST /tasks/{id}/cancel`（协作式取消并保留已命中结果），已注册进 `api/v1/router.py`；前端复用 `AnimCard/TabNav/Chip/HrsButton/EmptyState/PageHeader`，选项契约由 `/options` 下发。
- [修复] 修复日历资讯页 `/live-calendar` 及快讯抓取接口 500（`'dict' object has no attribute 'title'`）：统一数据源重构后 `WallstreetcnNewsSource.fetch` 的 `calendar`/`live` 模式误将类型对象转成原始 dict，而服务层 `_calendar_entry_to_rows`/`_live_news_entry_to_item_fields` 按属性访问（含 `scope_values` 这类 `@property`），改为返回 `CalendarEventEntry`/`LiveNewsEntry` 对象（与 `calendar_countries` 模式一致），并补充 `tests/test_live_calendar.py` 覆盖该回归链路。
- [新功能] 新增「尾盘选股法（EOD Picker）」：路由 `/eodPicker`，照搬参考项目 chengzuopeng/stock-dashboard 的界面与功能（开始屏 + 可编辑筛选 + 进度遮罩 + 结果卡片网格含分时图）。后端 `src/services/eod_picker_service.py` 实现两阶段筛选（全市场快照基础过滤 + 分时强度过滤），分时强度 = 价格站在均价线（VWAP）之上的采样点占比；`api/v1/endpoints/eod_picker.py` 提供 `GET /defaults`、`POST /tasks`（异步任务）、`GET /tasks/{id}`（轮询）、`GET /stocks/{code}/timeline`（分时懒加载），已注册进 `api/v1/router.py`。前端 `EodPickerPage` 复用 `AnimCard/HrsInput/Switch/Modal/TabNav/KLineChart` 等现成组件，筛选条件与方案/最近使用持久化于 localStorage。
- [修复] 尾盘选股：修复流通市值单位不一致（东财快照为「元」、腾讯回退为「亿元」）导致基础过滤把绝大多数股票误杀、结果数量与展示偏差的问题，统一归一化到亿元后再过滤。
- [改进] 尾盘选股：stage-1 快照数据源改为优先直连东财 clist（`push2.eastmoney.com/api/qt/clist/get`，按代码稳定排序、每页 100 并行翻满全市场、无随机休眠，字段与 `ak.stock_zh_a_spot_em` 同源），失败依次回退腾讯批量行情、东财 `ak.stock_zh_a_spot_em`；新增 `data_provider/eastmoney_quote_snapshot.py`（与 `tencent_quote_snapshot.py` 对等的独立快照模块），并补充解析/翻页/单位与回退优先级离线测试。修复东财 clist `pz` 上限 100 导致只取到第 1 页（前 100 名涨幅股）、尾盘选股 0 结果的缺陷。
- [改进] 尾盘选股：阶段 2 分时强度改为直连东财 trends2 分时接口（与参考项目 stock-sdk quotes.timeline 同源同语义，均价线为数据源真实 VWAP），替代 1 分钟 K 线多源回退（sina 源成交额为推导值、且限流会导致候选被静默丢弃）；并发上限校准为 4（东财 push2his 对高并发限流严格，实测 16 并发会触发 IP 临时封禁），单票失败自动重试。
- [修复] 尾盘选股：修复阶段 2 分时取数 0 结果缺陷——原分时走东财 trends2 的 SSE 端点（`trends2/sse`），该长连接端点已被东财持续断连（`RemoteDisconnected`，实测多次无一成功），导致每只候选都取不到分时、被静默淘汰、最终 0 结果（这正是「参照对象有结果、本项没有」的根因）。改用与 stock-sdk `getTodayTimeline` 同源的 JSON 端点 `trends2/get`，并新增多组 CDN 主机轮换（`push2his`/`33.push2his`/`63.push2his`/`7.push2his`）+ 指数退避，抵御 push2his 对单主机/高频的限流；修复后 6 只基础候选全部取到 241 个分时点并正常算出强度。
- [改进] 尾盘选股：阶段 2 分时抓取固化为「直连温和为主 + stock-sdk 桥接回退」——直连 `trends2/get` 增加**全局节流**（≈3 req/s，避免线程池并发突发触发东财 push2his 限流而导致级联 0 结果）+ 多 CDN 主机轮换 + 温和退避；直连失败回退 stock-sdk 桥接（`sdk.quotes.timeline`，A 股代码转 `sh/sz/bj` 前缀格式，走非 push2his 上游，可绕开东财限流）。新增 `data_provider/stocksdk_bridge.py:fetch_timeline` 与 `scripts/stocksdk_bridge/bridge.mjs` 的 `timeline` 动作，并补桥接回退离线测试。
- [修复] 尾盘选股：修复结果卡片分时缩略图为空的问题。根因是东财 trends2 返回的 f51 时间字段为 `YYYYMMDD HH:mm`（无连字符），前端 `KLineView.parseTimelineTime` 只识别 `YYYY-MM-DD HH:mm(:ss)`，导致所有下采样分时点被过滤、卡片走势区只展示占位符「-」。后端 `_parse_trends_payload` 新增 `_normalize_trend_date` 统一标准化为 `YYYY-MM-DD HH:mm:ss`，并同步应用于桥接回退路经，保证两种数据源都能正确渲染。
- [改进] 尾盘选股：结果卡片点击直接跳转个股 K 线页 /stock/kline（sessionStorage 传递代码与「名称（规范代码）」展示标签，K 线页自动加载并在搜索框回显），移除分时大图弹窗；筛选行增加淡灰色背景对齐参考项目视觉。
- [改进] 尾盘选股：进度模态框新增分步股票结果展示——第一步（基础条件过滤）与第二步（分时强度过滤）各自过滤出的股票以「名称（代码）」列表实时呈现（含步骤状态、数量与列表内部滚动）；后端 `run_eod_picker` 新增 `update_steps` 阶段性快照回调（全量下发、整体替换，单步条目上限 200），`GET /tasks/{id}` 响应新增 `steps` 字段（任务级 LRU 存储、终态清理），前端轮询同步渲染并补齐 zh / zh-Hant / en 三语文案。
- [改进] 信号扫描：扫描过程新增分步股票结果展示——第一步（解析股票池）与第二步（技术信号扫描）各自过滤出的股票以「名称（代码）」列表在右栏实时呈现（含步骤状态、数量与列表内部滚动）；后端 `run_signal_scan` 在阶段边界将步骤快照写入运行态 `_RunState.steps`（全量下发、整体替换，单步条目上限 200），`GET /tasks/{id}` 响应新增 `steps` 字段（`build_partial_payload` 与最终结果两路返回），前端新增 `ScannerProgressSteps` 组件并在轮询中同步渲染，补齐 zh / zh-Hant / en 三语文案。
- [修复] 修复股票基础信息（/api/v1/kline/{code}/info）在东财不可达时整页失败：新增腾讯实时行情兜底源 `TencentStockInfoSource`，默认 source 顺序追加 `tencent`，并复用 `code_to_sina_symbol` 统一剥离交易所前后缀。
- [新功能] 按 ADR-001 新增 `data_provider/{stockdb_fetcher,kline,stock_info,code_search}` 分层能力：K 线端点改为瘦端点，StockDB 以 `local` source 形式接入现有 `/api/v1/kline`、股票信息与代码搜索链路。
- [新功能] 补齐 ADR-001 约定的 `data_provider/{realtime,sector,fundamentals,news,institutional}` 功能包骨架，并将实时行情、板块排行、华尔街见闻资讯、台湾机构数据等既有通道收口到对应 source 文件。
- [改进] Web 端现有个股 K 线页新增数据源标识与数据表视图，支持在图表视图之外直接查看统一后的原始 K 线数据，便于本地 StockDB 数据核对。
- [改进] Web 设置页「数据源」分类新增统一数据源摘要卡片，集中展示 StockDB 状态、三类基础能力主源策略，并可直达本地行情页。
- [改进] 按 ADR-001 将 `data_provider/common/market.py` 的市场代码辅助函数收敛回 `common/normalize.py`，减少公共层表外文件漂移。
- [改进] 统一华尔街见闻底层抓取器命名为 `wallstreetcn_calendar_fetcher.py` / `wallstreetcn_live_news_fetcher.py`，并同步更新资讯能力层、测试与相关设计文档引用。
- [改进] 继续按 ADR-001 收敛运行时入口：移除 `kline/stock_info/code_search` 的 `service.py` 过渡层，新增 `realtime/sector/fundamentals` 正式入口，并将热点服务、个股服务、事件监控等主链路切换到能力包入口。
- [改进] 统一 `src/services/` 与 `tests/` 中 Repository 类导入到 `src/repositories` barrel，减少数据库层入口分散并补齐 ADR-001 的 D5 收口项。
- [改进] 继续按 ADR-001 收敛 `api/v1/endpoints/sector.py`：将东财市场指数/市场概览/北向资金/大盘主力/板块列表/板块资金流历史的缓存与取数主链路下沉到 `data_provider/sector/eastmoney_source.py`，端点文件仅保留参数校验与响应编排。
- [改进] 继续按 ADR-001 收敛 `api/v1/endpoints/sector.py`：将时到量化行业/个股/ETF/概念云图的直连取数、缓存与整形下沉到 `data_provider/sector/shidaotec_source.py`，补齐 `sector` 能力包的单源入口收口。
- [文档] 同步更新 `backend_architecture_adr.md` 中 `sector` 能力铺排与 B1 状态，明确 `eastmoney + shidaotec` 的分工边界，消除 ADR 与当前代码实现的文档漂移。
- [文档] 基于 StockSDK 官方文档补充 `backend_architecture_adr.md`：将 `StockSDK` 纳入数据源对接层规划，明确其作为 Node 18 桥接型物理后端的接入边界，并同步更新目录铺排、配置键、功能接口层约束、执行顺序与验证清单。
- [新功能] 新增 `data_provider/stocksdk_bridge.py` 与 `scripts/stocksdk_bridge/bridge.mjs`，以 Node bridge 方式接入 `StockSDK`，并为 `kline`、`stock_info`、`code_search` 补齐 `stocksdk_source.py` 可选数据源。
- [改进] 为 `market/index` 与 `market/sector-analysis` 补充 `data_provider/sector/stocksdk_source.py`：总览页优先使用 StockSDK 提供 A 股/港美指数、市场概览、北向资金与大盘主力；板块卡片与板块资金接口改为 StockSDK 优先、东财回退，云图仍保留时到量化专属源。
- [改进] 总览页新增统一聚合接口 `GET /api/v1/sector/market-cards?market=a|hk-us|jp-kr`：后端按 TAB key 直接返回标准化卡片列表，前端 `StockDashboardPage` 改为单接口驱动，收敛原先 7 个并发请求与页面侧拼装逻辑。
- [改进] 扩展数据源配置与设置页显示，补充 `STOCKSDK_*` 运行时配置、`stocksdk` 选源项与前端数据源标签映射。
- [文档] 为 `scripts/stocksdk_bridge/` 补充目录级说明，明确 `stock-sdk` 依赖应保留在独立 bridge 子目录，而非 `scripts/` 根目录或 `apps/hrs-web` 前端工程中。
- [文档] 更新消息日历方案文档 `documents/product/行情资讯/Live-calendar.md`：补充 `LiveCalendar` 的 `onRangeRequest + dataReadyKey` 范围握手、月视图 staged mount、自绘 List 视图职责，以及前后端按月缓存 / single-flight / 相邻月预取 / 降级保留上一帧数据等交互与性能设计说明；同步更新作者、最近更新时间与手动验证重点。
- [文档] 新增「侧边栏」组件文档 Demo 页（`/docs/component/sideBar`，仅开发调试模式可见）：同时演示应用主导航 SidebarNav（default/rail 形态与折叠态）与基于 HeroUI Pro Sidebar 的 SidebarNavV2（复用同一份菜单数据，随运行模式切换，点击走 SPA 路由跳转）。
- [改进] 消息日历筛选区域去掉外围边框；国家/地区下拉按中文名拼音首字母 A-Z 分组（组内按全拼排序，无拼音者归入 `#` 组），选项显示「国旗 + 国家名称」，下拉弹层限高（弹层与 HeroUI 内部 list-box 一并限高，滚动条落在 list-box）；关键词输入框改为占满本行剩余宽度，右对齐到操作区。
- [修复] 消息日历筛选点「重置」不生效：草稿同步按引用比较，而重置回到的 `DEFAULT_LIVE_CALENDAR_FILTER` 与初始/上次生效值可能是同一引用，比较判定无变化导致草稿不回灌；改为 `createDefaultLiveCalendarFilter()` 每次生成新对象，面板重置时先本地回灌草稿再通知 Page。
- [新功能] 消息日历新增筛选：Tab 行右侧筛选按钮（带条件数角标与展开箭头），展开区域支持重要度多选、类型三态（全部/经济数据/大事件）、国家地区下拉与标题关键词；点确认后月/周/日/列表四视图同步过滤，全部为客户端过滤不新增请求。
- [修复] 消息日历月份游标推导改用 `view.currentStart`：此前用可见范围首格（`datesSet` 的 `arg.start`），月初未周一前会把月份带偏到上月，导致当月日期（含今日/昨日）在网格中全部无事件且刷新无效。
- [改进] 消息日历支持多语言：工具栏「今天/月/周/日」文案与 FullCalendar locale（星期表头、aria 提示）随 UI 语言切换，新增 i18n 键 `common.datetime.today/month/week/day`。
- [改进] 消息日历右上角月/周/日视图切换改为三个独立纯文字标签（选中项浅灰圆角底 + 加粗），导航按钮保持连体胶囊不变。
- [改进] 消息日历月视图下点击事件标题或日期格自动切换到日视图并展示当日全部事件（数据复用当月拉取结果，不重新请求）。
- [修复] K 线全量数据回归：新浪老接口优先（datalen=10000 一次拉取上市以来全量），腾讯 K 线域名改为 ifzq 规避 WAF 拦截（web 前缀返回 501）。
- [修复] 统一等价股票代码的本地日线候选与同源窗口解析；冲突沪深交易所代码不再降级匹配裸码，回测仅接受快照或交易日历确认的起点，并在同一起点中优先完整的单一代码窗口。
- [新功能] 新增按 individual SkillAgent 自身 signal、版本化 engine 与本地已存同源日线窗口计算并持久化 `skill_opinion_outcomes` 的核心服务；本阶段不提供管理员 API、表现统计、样本充足度或权重调整。
- [新功能] Web 前端新增「总览」菜单与 `/stock-dashboard` 路由（菜单文案支持中英文切换），承载市场行情与核心指标总览（30 秒自动刷新）。
- [改进] Web 前端「首页」菜单路由由 `/` 调整为 `/home`，根路径 `/` 重定向到 `/home` 保持旧链接兼容。
- [改进] 板块分析页顶部的市场仪表盘迁移至「总览」页面，板块分析页保留云图与板块资金等分析功能。
- [新功能] 总览页新增可复用卡片组件 IndexCard（指数名称/点位/涨跌幅/涨跌点数/成交额/放量）与六种统计卡片（市场涨跌/涨跌停/全市场成交额/北向资金/大盘主力/最强板块），指数接口补充涨跌点数与成交额，概览接口新增涨停/跌停家数（按板块涨跌幅限制精确判断）。
- [新功能] 新增北向资金（`/api/v1/sector/northbound-flow`）与大盘主力（`/api/v1/sector/market-fund-flow`）接口；北向实时数据 2024-08 起停披露，数据缺失时卡片展示占位符。
- [新功能] 总览页港美/日韩 TAB 接入真实指数数据（`market-indices` 支持 `market=us|jp-kr`），海外指数无成交额时降级显示由最高/最低/昨收派生的振幅。
- [修复] 修复总览页港美/日韩 TAB 切换后页面加载失败：当东财对部分海外指数不返回数据导致实际返回数少于配置 secid 数时，IndexCardGrid 渲染循环越界访问 `undefined` 触发 RouteBoundary；改为按 `placeholderCount` 用真实数据 + `EMPTY_INDEX` 占位补齐，并对 `IndexCard` 的 `high/low/preClose` 做类型与有限值校验防止振幅派生炸错。
- [修复] 总览页港美/日韩 TAB 移除数据源无实时行情的指数：日韩移除韩国KOSDAQ（`100.KQ11`，东财 rc=102 无数据），港美移除纳指金融100（`251.IXFN`，东财无响应）与纳指互联网（`251.IXNA`，东财 rc=102 无数据）；三者经东财、Yahoo Finance、腾讯证券三源交叉验证均无数据，前端占位数量同步调整为日韩 2、港美 6。
- [修复] 总览页海外指数卡片成交额缺失时显示「成交 0.00亿」的问题：后端将东财 `f6` 为空标记或 `0` 时统一转为 `None`，前端据此降级显示由最高/最低/昨收派生的「振幅」，港美 6 个与日韩指数均生效。
- [新功能] 新增实时财经快讯中心（`/live-news`）：接入华尔街见闻 7x24 快讯，提供要闻/A股/美股/港股/外汇/商品/债券/科技 8 个频道 Tab、重要级筛选、关键词搜索与按日过滤，官方源不可用时自动降级到 NewsNow 聚合源（降级时仅保留「要闻」且无重要级）。设计与接口契约见 `documents/product/行情资讯/live-news.md`。
- [新功能] 新增快讯后端接口：`GET /api/v1/intelligence/live-news/channels`、`GET /api/v1/intelligence/live-news`、`POST /api/v1/intelligence/live-news/refresh`、`GET /api/v1/intelligence/live-news/{item_id}`，支持频道/重要级/关键词/日期区间过滤与 keyset 游标分页。
- [改进] `intelligence_items` 新增 `importance` 列与频道查询复合索引，用于承载快讯重要级；存量库通过启动时幂等补列迁移，补列失败仅告警不阻断启动。
- [修复] 快讯抓取在本地代理（Clash 等 fake-ip 模式）环境下被 SSRF 校验误拦，导致库数据陈旧、`live-news/refresh` 返回 `source url must not target private or local network addresses` 错误；对受信任内置源（华尔街见闻快讯、NewsNow 聚合源）放行 fake-ip 网段（198.18.0.0/15）并允许复用系统代理解析真实地址，用户自定义源仍保持禁用代理 + 严格判段。
- [文档] 新增消息日历（Live Calendar）设计方案 `documents/product/行情资讯/Live-calendar.md`：核实华尔街见闻 `/apiv1/finance/macrodatas` 与 `/apiv1/finance/countries` 两个可用接口（实测 2026-08-28~09-25 返回 569 条，FE 88 / FD 481），确认「宏观/财报/新股/活动」为前端过滤而非后端分流，并给出服务端打标、复用 `intelligence_items` 落表与降级策略的完整方案。
- [文档] 消息日历方案补充落表核实与重要度统一设计：`scope_type`/`scope_value`/`importance` 三列均已存在无需加列；日历与快讯一样**不注册资讯源**（注册的本质是加入 `fetch_enabled_sources` 批量抓取队列，而日历需 `year/month` 时间窗参数、通用链路无法表达，且 `calendar` 不在 `_ALLOWED_SCOPE_TYPES` 白名单内）。
- [文档] 重要度确立统一业务量纲 `0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要`，遵循「数据源只是提供方、业务定义归本项目」原则，上游量纲只在归一化入口出现一次：快讯 `score` 按 `{1→1, 2→3, 3→4}` 语义守恒映射（非简单 `+1`，避免「普通」虚增为「较重要」）、无字段填 `0`；日历上游原值直存、缺失填 `0`。输出侧 `score` 改为直接读 `importance` 列并删除 `raw_payload` 优先分支；阈值统一取 `3`。
- [文档] 快讯 `importance` 存量数据迁移方案：与阈值调整**必须同批次发布**（否则重要率从 31% 暴跌至 2%），迁移 SQL 需用 `WHEN importance IS NULL` 分支且限定 `scope_type='channel'`；因迁移前后取值集合存在交集，必须采用 `DatabaseSchemaMigration` 标记式幂等，不可依赖数据形态判断；反向迁移依赖 `raw_payload.score` 保留的原始值，改造可逆。
- [文档] 日历前端控件选型确定为 **FullCalendar v6.1.21 二次封装**（`@fullcalendar/{react,core,daygrid,interaction}`，React 19 peer 已实测确认；v7 因 daygrid/interaction 插件尚未发布正式版而暂不采用）：否决 HeroUI `Calendar`（react-aria 系为日期选择器，语义模型与"每格多事件展示"冲突）与自实现方案。封装遵循 `.conventions/frontend/COMPONENTS.md`（`components/common/LiveCalendar/`、完整透传原生 Props、`cn()` 合并、命名导出）；样式遵循「Tailwind + tailwind.config 令牌为唯一来源、不新建 CSS/SCSS、不用 `global.scss`」，主题经组件根 `--fc-*` CSS 变量层映射项目令牌（Tailwind arbitrary values，不新建文件）；类型命名按 TYPE_NAMING 用 `*Def`；i18n 前缀 `liveCalendar.*`；分类 Tab 复用现有 `TabNav`。
- [修复] 消息日历（`/live-calendar`）页日历网格完全空白（表头与月份标题显示但日期格子全部不渲染），两个叠加根因：其一，FullCalendar v6 已移除 v4 的 `height="parent"` 高度值（浏览器把 `parent` 视为非法 CSS 长度，`.fc` 与 `.fc-view-harness` 内联高度失效，`fc-view` 绝对定位铺满 0 高度 harness），封装层误用旧 API，按方案文档 `documents/product/行情资讯/Live-calendar.md` §9.4 改回 `height="100%"`；其二，外层容器 `h-full w-full [&_.fc]:h-full` 及全部 `--fc-*` 主题变量被误注释，导致 `height="100%"` 失去可参照的父级高度而塌缩，已恢复并清理调试日志。
- [改进] 消息日历（`/live-calendar`）分类 Tab 顺序调整为「全部 / 宏观 / 财报 / 新股 / 活动」并默认选中「全部」（后端 `_CALENDAR_TABS` 单一真源改 `order`，前端改为按 `order` 升序渲染）；日历工具栏日期导航由「前 / 后 + 今天」改为「前 / 今天 / 后」连体按钮组（`headerToolbar.start = 'prev,today,next'`）。
- [修复] 消息日历周视图跨月周次只拉取周一所在月份的数据，导致跨月日（如 9 月第一周中的 9/2、9/3）在网格中无事件且刷新无效：改为按 `datesSet` 可见日期范围推导覆盖的所有月份并行拉取合并（月视图上/下月填充格同理覆盖），刷新按钮同步覆盖全部可见月份。
- [修复] 消息日历首次切入日视图定位到当月 1 日而非当天：`initialDate` 由「cursor 当月 1 日」改为「今天」，首屏月视图不变，切日/周视图时落在当天所在范围。
- [chore] 消息日历 FullCalendar 封装组件重命名：目录 `components/common/LiveCalendarGrid/` → `components/common/LiveCalendar/`，文件 `LiveCalendarGrid.tsx` → `LiveCalendar.tsx`，导出组件 `LiveCalendarGrid` → `LiveCalendar`（Props 类型同步为 `LiveCalendarProps`）；纯命名调整无行为变化。同步修正按旧路径写入的引用与排除规则：`LiveCalendarPage.tsx` / `useLiveCalendar.ts` 的 import 路径、`tsconfig.app.json` 与 `eslint.config.js` 对 `demo/` 参考代码的排除路径（不改会导致 demo 泄入编译与 lint 范围）、`documents/product/行情资讯/Live-calendar.md` 全部路径与类型引用。
- [chore] 消息日历 `LiveCalendar` 组件的容器层样式独立成文件：新增 `apps/hrs-web/src/components/common/LiveCalendar/csscover.ts`（导出 `LIVE_CALENDAR_CSS_COVER`，含 167 条 `[&_.fc-*]` 覆盖类名与 `--fc-*` 主题变量），组件文件由 1062 行降至 714 行，只保留 `cn(LIVE_CALENDAR_CSS_COVER, className)` 一次引用；纯代码组织重构，经 twMerge 比对确认最终 `className` 字符串与重构前逐字相等（Vite 产物 CSS 已验证可正常扫描到）。详见 `documents/product/行情资讯/Live-calendar.md` §9.4 / §9.6。
- [文档] 新增 11 个组件文档 Demo 页（`/docs/component/*`：抽屉/按钮/下拉选择/分割线/表格/轻提示/模态框/动画卡片/快讯卡片/列表卡片/标签页），覆盖 HrsDrawer/HrsButton/HrsSelect/Separator/Table/Toast/Modal/AnimCard/NewsCard/ListCard/TabNav 的基础用法与常见变体示例。
- [文档] 新增 Input / TextArea / Chip 三个组件文档 Demo 页（`/docs/component/input`、`/docs/component/textArea`、`/docs/component/chip`），覆盖尺寸档位、受控用法、type/variant 变体、只读与禁用态及表单组合场景。
- [改进] 尾盘选股结果卡片的分时图由 eCharts 版 `KLineChart` 切换为 lightweight-charts 封装的 `KLineView`（`apps/hrs-web/src/components/kline/KLineView.tsx`）：仅渲染价格趋势线（面积填充）+ 均价线 + 昨收基准虚线，去掉左右 Y 轴 / X 轴 / 网格 / 十字光标 / 高低点标注并锁定交互，降低卡片网格场景的渲染开销；无有效分时数据时组件内渲染占位块，`KLineChart` 本体保持不变。
- [改进] 尾盘选股结果卡片视觉重构（对齐参考项目 EndOfDayPicker）：涨跌幅胶囊徽章、现价大字号 + 涨跌额 + 分时强度徽章、浅灰底缩略走势区（走势线改为红涨绿跌并新增末端圆点与「价格 / 均价」图例）、左标签右数值的 2x2 指标网格，并新增「加自选」按钮（写入排序第一个自选分组，后端 409 按已存在处理，无分组时隐藏）；排序栏同步由 TabNav 改为 HrsButton 按钮组并前置「排序」文案。
- [新功能] Web 前端支持路由缓存（Keep-Alive，ADR-002）：切换路由后页面实例保留，切回时表单/筛选/Tab/滚动位置/已加载数据/图表实例原样恢复，不重新请求、无 loading；缓存范围由单一配置文件 `apps/hrs-web/src/router/keepAliveConfig.ts` 的黑名单（pathname 匹配，支持 `/docs/*` 前缀规则）控制，默认排除登录页、对话页、组件调试页与 404，其余页面全部缓存；后台缓存页经 `usePageActive` 暂停轮询/SSE（切回即刷新），`maxCacheSize`（默认 8）LRU 硬上限约束内存；隐藏层 `display:none` 零布局零绘制，在线页不套 DOM 包裹、布局与现状一致。
- [修复] 侧边栏滑行高亮「背景滑块」错位：一级菜单展开/收起时滑块停在旧坐标（偏移量恰为被开合子菜单的高度），且折叠含激活子项的一级菜单后滑块会飘到相邻菜单行上。修复三处成因：①定位只观测菜单区容器，而子菜单开合动画（`height 0↔auto`）改变的是菜单列表自身高度、容器尺寸恒定（`nav` 定高内部滚动）故收不到事件，改为一并观测菜单列表元素；②落点只认 `[data-active]` 的激活叶子，叶子被折叠隐藏后落点悬空，改由 `apps/hrs-web/src/components/layout/SideBar/menuPath.ts` 新增的 `resolveHighlightMenuId` 统一计算落点（命中路由的菜单，容器前缀命中不抢占同名页面；被折叠祖先隐藏时上移到最近可见的祖先行，重新展开后回落到激活叶子）；③`SidebarNav` 按落点 `menuId`（`MenuNode` 新增 `data-menu-id`）精确定位，避免贴合到开合动画中尚未退场的旧行上。
- [修复] 侧边栏一级菜单首次点击不折叠：展开态来自 `menuExpanded` 数据默认值或「子项命中路由自动展开」时，`toggle` 直接对用户覆盖值（`undefined`）取反会得到 `true`，使首次点击看似无效、需点两次才折叠；改为由 `MenuNode` 回传当前有效展开态再取反（`apps/hrs-web/src/components/layout/SideBar/MenuNode.tsx` 的 `onToggle(menuId, expanded)`）。
- [修复] 侧边栏滑行高亮「背景滑块」无滑动动画（对齐参考 `SIDEBAR_NAV_THUMB.md` 的 `slideThumb` 重写）：根因是动画机制用错——先前用「JS 内联写 `transition` 再写 `transform`」靠 CSS 过渡滑行，在 `useLayoutEffect` 同步提交时极不稳定（参考 §3.5 明确规避 CSS transition 与 JS 动画两套打架），且任何写法都无法稳定触发过渡。现改为用浏览器内置 **Web Animations API（`thumb.animate`）** 复刻 `slideThumb`：`transform` 完全由 JS 动画接管、CSS 不写 `transition`；用 `getAnimations().cancel()` 实现 `overwrite:true`，并用 `getComputedStyle`+`DOMMatrixReadOnly` 取当前视觉 `Y` 作起点，跨父级路由切换后补一段 0.18s 短滑行贴合子菜单高度动画。触发收敛为参考 §3.4 的「克制原则」：**仅「用户切换路由」播滑行**，首次挂载 / 折叠 / 展开 / 菜单数据变化 / resize / 滚动一律瞬时对齐（按你的选择，折叠展开保持瞬时、不滑）；减弱动效下放短为 `0.16s` 短滑行（而非完全静止）以保证可观察到。`SidebarNav.tsx` 的 `syncThumb` 重写、`SidebarNav.module.scss` 移除过渡声明、无 `animate` 环境（jsdom 测试）自动回退为瞬时设置。
- [修复] 侧边栏滑行高亮「背景滑块」切换无动画（设多大时长都瞬间变化）：根因是滚动/ResizeObserver 副作用的依赖里含 `syncThumb`，而 `syncThumb` 身份随高亮每次变化，导致 ResizeObserver 在每次路由切换都重新 `observe`——新建的 ResizeObserver 会立刻触发一次初始回调 → `syncThumb(false)` 把刚启动的 WAAPI 滑动动画取消成瞬贴；次因是 300ms 的「补贴合」无条件取消主动画，使时长最多只生效 ~480ms。修复：RO/滚动改用「最新 `syncThumb` 引用」（`useNavThumb.ts` 的 `syncThumbRef`，经 `useLayoutEffect` 更新），依赖收敛为 `[menuItems]`/`[]`，不再随高亮重订阅；「补贴合」改为漂移检测——仅当落点真偏移（>2px，跨父级子菜单 height 动画场景）才补一段短滑行，否则让主动画播完。`apps/hrs-web/src/components/layout/SideBar/useNavThumb.ts`。
- [改进] 侧边栏滑行高亮「背景滑块」切换动画放慢：常规滑行 0.42s→0.52s（对齐参考 `SIDEBAR_NAV_THUMB.md` 的 `DUR.slide=0.52` + `power4.out` glide，快出慢收更有质感），减弱动效短滑行 0.16s→0.30s；时长抽为 `useNavThumb.ts` 顶部常量 `THUMB_SLIDE_MS` / `THUMB_SLIDE_REDUCED_MS` / `THUMB_SETTLE_MS` 便于后续调整。
- [chore] 侧边栏「滑行玻璃 / 高亮落点」子系统收敛为单一模块 `apps/hrs-web/src/components/layout/SideBar/useNavThumb.ts`：原 `menuPath.ts` 整体并入并删除——其路由匹配原语 `matchPath` 与落点解析 `resolveHighlightMenuId`（含 `findBestChain`）一并下沉，与玻璃定位同源；`matchPath` 随 `resolveHighlightMenuId` 导出，`MenuNode`/`SidebarNav` 改为从 `useNavThumb` 导入（避免为单函数单开文件，也规避在组件文件导出非组件触发 react-refresh 规则）。`useNavThumb` 由「调用方传入 `highlightMenuId`」改为「内部按 `menuItems/pathname/isExpanded` 解析并回传」，`SidebarNav` 不再自行解析、只做 DOM 接线；落点裁决由「收集全部命中链再 reduce」优化为单遍 `findBestChain`（语义不变）。测试由 `menuPath.test.ts` 更名为 `useNavThumb.test.ts`。纯重构，行为不变。
- [新功能] 新增 `UniverseBackground` 星空背景组件（`apps/hrs-web/src/components/universe/`）：将「BEYOND THE WANDERING EARTH」Three.js 体验（三层尺度梯子：地球 / 太阳系 / 银河，后期辉光，剧情/自由相机，原版 HUD）封装为可复用 React 组件，默认以银心外 halo 视角 + 星系慢转作为页面/区块背景；VOYAGE 剧情时间、ORBITS 时间倍率、星系自转速率、尺度缩放（星系→银河→太阳系→地球）均支持 props / ref 命令式控制，原版 HUD 控件（VOYAGE 滑条、ORBITS 分段、尺度标尺、DESTINATIONS、热点标记）随组件保留可直接使用；引擎与 UI 样式 vendor 自本地模板 `vibe-template/earth-migration`（MIT © 2026 玛卡巴卡，随附 LICENSE），静态资源（31M + Draco decoder）落在 `apps/hrs-web/public/universe/`；新增 `three@^0.160.1` 依赖与 tsconfig `allowJs`；无 WebGL 环境降级为 loader 故障文案不白屏。设计/使用规范见 `documents/vibe-adopt/vibe-universe.md`。
- [改进] 首页（`/home`）接入 `UniverseBackground` 星空背景：fixed + `[contain:layout_paint]` 相对主滚动容器固定（不随内容滚动、不越界盖侧栏/页头），zIndex -1 沉在内容之下；默认银心外 halo 视角 + 星系慢转，HUD（VOYAGE/ORBITS/标尺/DESTINATIONS/热点）可直接交互；暗色主题下与原 LightBloom 背景叠加（后者被不透明星空画布完全遮盖，视觉无影响）。
<!-- 新条目格式：- [类型] 描述（类型取值：新功能/改进/修复/文档/测试/chore）-->
<!-- 每条独立一行追加到本段末尾，无需分类标题，合并时冲突最小 -->

## [3.28.0] - 2026-07-26

### 发布亮点

- feat: Multi-Agent 多策略综合支持分层 deliberation、mediator/self-review、revision projection 与 multi-round，并统一最终动作和解释契约。
- feat: AI 建议页新增按决策风格分组的历史表现，specialist opinion 样本可持久化并用于后验评估。
- feat: 新增 `--portfolio futu`，可只读导入 Futu OpenD 真实账户的沪深 A 股、港股和美股 LONG 正股持仓。
- feat: Web 首页与 API 支持按单个或多个市场临时触发大盘复盘，不修改全局配置。
- feat: Tushare 支持通过 `TUSHARE_HTTP_URL` 接入自建网关或兼容镜像。
- fix: 改进港股行情路由与缓存、外股英文新闻匹配、数据源兜底顺序及桌面端发包稳定性。

### 新功能

- Multi-Agent 多策略综合新增受控 deliberation v0、可注入 mediator/self-review v1-v2、只读 revision projection v3 与 multi-round v4；增强层相对上一层 baseline 只能保持或继续 softened，不覆盖权威最终信号。
- `specialist` 模式最多选择 4 个策略专家，并通过 `AGENT_SKILL_CONCURRENCY` 控制 1–4 个 worker 并发；worker 继承主管线冻结的 target date 等上下文，单个 skill 失败不阻断其它策略或最终决策。
- Multi-Agent 报告按八态用户 action 追踪 Pipeline 最终调整，排除非法 Agent 意见；仅在 canonical action 可唯一解析时生成 explanation 与 DecisionSignal，并以同一个 `final_action` 统一最终动作契约。
- specialist 在分析历史保存成功后持久化版本化、低敏且幂等的有效 opinion 样本，为后续后验评估提供真实数据；本阶段不计算 outcome、不统计表现、不调整权重。
- AI 建议页新增决策风格历史表现，按每个分组独立的 30 个已完成样本门槛展示命中、区间涨跌、无法评估和最大不利波动，并保持旧统计接口兼容。
- 新增 `--portfolio futu`，只读导入 Futu OpenD 真实账户的沪深 A 股、港股和美股 LONG 正股持仓作为分析列表。
- Web 首页与 `POST /api/v1/analysis/market-review` 支持用严格校验的 `region` 临时选择单个或多个复盘市场；一次性覆盖不读写全局配置，并贯穿任务提交、状态、SSE、结果与历史记录。
- Tushare 数据源支持通过 `TUSHARE_HTTP_URL` 自定义接入地址；留空时继续使用官方默认地址（fixes #1985）。

### 改进

- 暂停 PR Review 的自动触发，仅保留 `workflow_dispatch` 手动入口，避免辅助评审重复运行及评论权限失败产生误导性红灯；正式 CI 检查保持不变。
- `.env.example` 与每日分析 workflow 同步映射 `TUSHARE_HTTP_URL`，保持本地和云端配置入口一致。

### 修复

- 修复外股代码映射到中文显示名时英文新闻相关性漏判，统一外股代码、英文名和别名解析，并对展开后的检索词去重（fixes #2026）。
- 特权 `pull_request_target` 流程不再检出 fork PR head；敏感步骤仅执行主分支可信脚本，PR 元数据与 diff 通过 GitHub API 读取（fixes #2051）。
- PR Review 事件载荷缺失、不可读或 JSON 非法时输出可定位且不泄露载荷的警告，并保留原有降级行为（fixes #2070）。
- 修复 Windows 上 `mimetypes` 冷启动读取注册表导致进程卡死的问题。
- 统一 `DataFetcherManager`、AkShare 与 Longbridge 对 4–5 位裸港股码的识别，避免 4 位代码被错误路由或静默失败（fixes #2091）。
- AkShare 港股实时行情增加 20 分钟全市场缓存与并发冷启动 single-flight，热缓存命中不再等待网络限速，主接口异常时仍保留新浪备用接口降级（refs #1852）。
- 将 `TencentFetcher` 默认优先级调整为 A 股日 K 数据源的最终兜底，并新增 `TENCENT_PRIORITY` 显式覆盖项（refs #2032）。
- Web 设置页和通知测试入口补齐普通钉钉群机器人配置，支持安全遮罩保存 webhook 与 secret、查看帮助并发送测试通知（refs #1957）。
- Agent Chat 普通与流式接口在请求未指定 `report_language` 时继承全局 `REPORT_LANGUAGE`，显式请求值仍优先。
- WebUI 分开展示发布版本、代码版本与构建时间，并用构建输入摘要避免复用时间戳未变化的旧静态资源（fixes #2093）。
- macOS unsigned 打包显式禁用 Electron 签名与 Hardened Runtime，在冻结后端和 electron-builder 阶段清理残缺签名，并审计原始应用与 DMG 产物；该缓解不替代 Apple Developer 签名与公证（refs #2075）。

### 文档

- 修复文档中的失效相对链接。

## [3.27.0] - 2026-07-19

### 发布亮点

- feat: 新增 Codex App Server single-agent 问股实验原型，并保持 LiteLLM、Multi Agent、普通报告和定时任务等默认链路不变。
- feat: Web AI 建议页支持保存基于历史报告快照重算的决策风格信号，补齐去重、续期、失效和可审计 guardrail 语义。
- feat: 引入多策略观点结构化输出第一阶段契约，覆盖观点标准化、基础冲突检测、聚合元数据和报告兼容边界。
- improve: 报告页明确展示输入数据状态、来源、异常影响、处理建议和诊断码，并区分页面资讯与本次分析输入。
- fix: 修复 MiniMax 推理内容污染最终 JSON、字符串 `<think>` 包装兼容及多 Agent 风险覆盖后结论未按最终信号收敛的问题。
- fix: 补齐美股实时行情 PE/PB 估值字段、多市场工具描述和 macOS Gatekeeper 安装排障说明。

### 新功能

- 新增 #1743 Phase 6 Codex App Server single-agent 问股实验原型，仅开放三个既有只读 Tool Surface 工具；默认 LiteLLM、Multi Agent、Deep Research、普通报告、定时任务与 Phase 1/2 `codex_cli` 路径保持不变。
- Web AI 建议页支持确认保存基于历史报告快照重算的决策风格信号，以 created/existing/refreshed 区分新建、原样复用和既有记录续期或维度补齐，并复用 profile-aware 去重与失效语义。
- 多策略观点结构化输出第一版新增策略观点标准化、基础冲突检测与聚合 metadata，作为 #1964 的阶段性基础契约；本版本不声明完成并发执行、完整策略调度 MVP 或前端完整多语言展示。

### 改进

- Codex 设置页仅检查配置、命令和所需协议是否允许尝试，用户保存后可直接提问；Chat 以服务端 `accepted` 事件提交问题并按实际 backend 停止。
- Web 报告页输入数据块沿用状态、来源、告警和说明字段，在说明中补充异常影响、处理建议与诊断码，并区分报告页资讯和本次分析输入。
- 更新 Anspire 数据源的项目展示信息，并将 `get_stock_info` 工具说明从 A 股限定修正为覆盖 A 股、港股和美股。

### 修复

- 修复 MiniMax 分析与渠道 JSON 测试把推理内容和最终文本拼接后导致结果无法解析、无法持久化的问题；字符串响应仅剥离开头完整的 `<think>` 包装，并保留 JSON 内容中的同名字面标签。
- 修正多 Agent 内部 runtime facts 的 timeout 归因，并让 risk application 覆盖后的 dashboard 决策字段及一句话核心结论基于 post-risk signal 完成 finalization。
- 收敛多策略综合器语义：正确处理 Signal 枚举、缺失 signal、有效 opinion_count 和 deterministic synthesis，并兼容历史与外部 dashboard 的宽松字段形状。
- Codex 问股只接受 App Server 明确完成的终态回答，并统一整体时限、累计输出、事件、工具预算和进程回收边界。
- `codex_cli` 普通分析显式固定无人值守批准策略与只读沙箱，避免新版 Codex 在非交互任务中因请求人工批准而中断。
- yfinance 美股实时行情补齐 `pe_ratio` 和 `pb_ratio`，供估值分析和下游报告使用。

### 文档

- 补充 macOS 未签名、未公证 DMG 被 Gatekeeper 拦截时的架构选择、安全排查与官方安装包临时放行步骤。

## [3.26.1] - 2026-07-12

### 发布亮点

- feat: Web 首页新增历史、自选与今日工作区，支持批量分析、今日覆盖判断和评分排行。
- feat: 新增 A 股市场结构与题材主线上下文，并贯通报告、Agent、DecisionSignal 与 Web 展示。
- feat: 飞书支持文件形式推送报告，多 Agent 支持子 Agent 独立超时钳位。
- feat: 补齐内部 HRS Tool Surface、DecisionAgent 分歧摘要和 DecisionSignal profile 契约。
- fix: 统一报告动作口径，修复按股票代码批量删除历史记录和通知理由静默截断问题。
- fix: 改进 Web、桌面端、数据源缓存及发行包资源的稳定性。

### 新功能

- 新增 A 股市场结构与题材主线上下文，并在报告、Agent、DecisionSignal 和 Web 市场位置卡中复用。
- 飞书推送新增文件上传能力：`FeishuSender.send_feishu_file(file_path)` 通过 App Bot SDK (`im.v1.file.create`) 上传文件并发送文件消息；Webhook 模式回退为发送文件内容文本；新增 `FEISHU_SEND_AS_FILE=true` 配置开关，开启后飞书以文件形式发送报告而非文字消息。
- 多 Agent 编排 Pipeline 新增子 Agent 独立超时钳位：支持 6 个环境变量为 TechnicalAgent、IntelAgent、RiskAgent、DecisionAgent、PortfolioAgent、SkillAgent 各自配置独立硬上限，互不挤占配额；默认 0 表示关闭钳位。

### 改进

- 为 multi-agent DecisionAgent 增加内部低敏分歧摘要输入管线，作为 #1904 P1 解释输出的前置 plumbing；不改变 public API、dashboard schema 或最终解释字段。
- GitHub Actions 每日分析工作流补齐 TickFlow 数据源环境变量映射，并收敛 README 数据源稳定性说明到完整指南。
- Web 首页个股栏新增历史 / 自选 / 今日切换，保留历史分析默认视图，并支持在自选页一键分析全部或仅分析今日未覆盖股票、在今日页按评分查看当天分析排行；分块提交部分失败时保留已确认计数、停止后续提交并刷新任务列表。
- GitHub Actions 每日分析工作流新增钉钉通知环境变量映射，支持在云端定时任务中直接使用钉钉机器人。
- `STOCK_LIST` 自选股解析支持中文逗号、顿号、分号、空格和换行等常见粘贴分隔符，运行时、定时热刷新、CLI `--stocks`、Web 设置保存和自选 API 统一识别，并在写回时规范为英文逗号。
- 新增 `NEWS_INTEL_AUTO_FETCH_ENABLED` 单开关，开启后个股分析、Agent 分析和大盘复盘会 fail-open 自动初始化并刷新 RSS/Atom/NewsNow 本地资讯池。
- Web AI 建议页新增主股票上下文，复用最近分析和股票索引候选，并改进表现统计零样本说明。
- DecisionSignal 将 `decision_profile` 升级为正式 nullable 字段，统一 same-profile 查询、去重、续期和失效语义，并保持 create metadata `null` 兼容与 SQLite 幂等回填诊断。
- 设置页移动端分类导航改为横向滚动列表并保证设置内容首屏可见，桌面端保留分类说明并收紧字段布局层级与间距。
- 新增 #1743 Phase 6a 内部 HRS Tool Surface 契约，统一工具 schema、stock scope fail-closed guard、结构化错误、审计摘要和脱敏诊断边界，并明确外部 AgentBackend 工具能力仍需 wire-level probe 证明。
- `src/services/analysis_service.py` 在 `report` 详情层新增 `details.raw_result` 回填，补齐与 API/历史详情的报告载荷一致性；不改变 provider、model、Base URL 或配置迁移语义。

### 修复

- 按股票代码删除历史记录时分批清理全部匹配项，并拒绝空白代码，避免超过 10000 条后残留记录或无筛选删除。
- 市场结构概念排行为空或超时时复用本轮负结果，避免批量个股分析重复请求同一概念排行数据源。
- Windows/macOS 桌面后端打包显式收集并校验 AkShare `file_fold/calendar.json`，避免发行包因缺少交易日历 package data 导致热点题材和选股日线增强降级。
- 邮件、Telegram 与报告共享的 DecisionSignal 摘要完整展示已脱敏的理由，避免固定 120 字符在句中无提示截断；Telegram 按最终 Markdown payload 长度安全分片。
- 推送报告、Jinja 报告与历史 Markdown 导出复用 Web/API 的评分-action 口径：高分但旧 `operation_advice` 仍为持有且无降级原因时，建议文案与三类统计展示为买入；有明确 guardrail reason 时继续保留持有/观望。
- WebUI 启动时显式 `--host` / `--port` 不再被 `.env` 中的 `WEBUI_HOST` / `WEBUI_PORT` 覆盖，未传 CLI 参数时统一使用解析后的运行时配置。
- Web 首页今日状态与排行使用带时区偏移的历史时间戳和完整分页数据，在查询失败、跨服务器时区边界或任务完成刷新时保持安全且准确。
- Web 首页 stock bar 刷新序列化：并发或乱序返回时仅最新请求可清除 `stockBarRefreshFailed`，避免旧响应覆盖任务完成后的刷新结果。
- Web 持仓页首屏快照改用 `include_realtime=false` 快速估值，跳过逐票实时行情预取后先展示持仓列表，避免外部实时行情源变慢时长时间空白等待。
- 修复任务状态接口重建报告动作字段时把合法情绪分 `0` 当成空值的问题，确保低分报告能按评分口径纠正为卖出建议。
- 修复 Agent 流式回复在未收到完成事件就断开时被显示为“（无内容）”的问题，改为提示流式响应中断并保留用户消息。
- 修复桌面端 `WEBUI_HOST=*` / `WEBUI_HOST=[::]` 会被原样传给端口探测和后端启动导致无法监听的问题，启动前分别规范化为 `0.0.0.0` / `::`。

### 文档

- 在 README 快速开始中补充行情数据源配置说明（`TUSHARE_TOKEN` / Longbridge），明确未配置时仍可使用 AkShare、Baostock、YFinance 等免费兜底源，并同步中英文完整指南。

## [3.25.0] - 2026-07-03

### 发布亮点

- feat: 新增 `claude_code_cli`、`opencode_cli` generation-only 本地 CLI backend，并补齐生成后端状态诊断、预览、冒烟测试 API 和 Web 状态面板。
- feat: 台股报告完整接入三大法人资料，覆盖报告渲染、LLM prompt、TWD 币别标示、收盘集合竞价识别和 fetcher 韧性加固。
- feat: 新增钉钉群机器人通知、韩语报告输出和 AI 建议决策风格重评估预览。
- feat: Agent `/chat/stream` 标准化 progress event，新增阶段开始/完成、pipeline timeout 和预算跳过语义。
- fix: 修复桌面端 WebUI host/port 绑定、macOS Homebrew CLI PATH 诊断、Discord 长报告分片、AlphaSift 超时、yfinance 分红解析、A 股回测代码归一化等稳定性问题。

### 新功能

- 钉钉群机器人通知支持 `DINGTALK_WEBHOOK_URL` 和 `DINGTALK_SECRET`，并对长文本自动切片以适配 20KB 限制。
- 报告输出语言新增韩语（`REPORT_LANGUAGE=ko`），覆盖个股报告、大盘复盘、Prompt 输出语言、决策护栏、通知模板标签与 Web 报告详情页文案。
- 新增 `claude_code_cli` 与 `opencode_cli` generation-only 本地 CLI backend，保留 LiteLLM 默认路径、Agent 工具调用边界、per-preset extractor、最小 env allowlist 与结构化错误。
- 新增生成后端状态、预览和冒烟测试 API，以及 Web 生成后端状态面板，区分轻量检查与 JSON 冒烟测试，并保持本地 CLI “仅生成、不支持问股工具调用”的边界。
- Agent `/chat/stream` progress event 新增 `stage_start`、`stage_done`、`pipeline_timeout`、`pipeline_budget_skipped`，补齐阶段进度、超时和预算跳过语义。
- 台股个股报告的 institution 区块展示 TWSE T86 / TPEx 三大法人原始买卖超净额，并将三大法人净买卖超表格注入 LLM 分析 prompt 作为台股筹码过滤器。
- 新增 AI 建议决策风格重评估预览接口与页面预览。

### 改进

- 台股三大法人 fetcher 增加并发缓存防击穿、TWSE/TPEx 分市场熔断、TPEx 日期保护和剩余 stage 预算复用，降低限流、端点故障和冷抓取超时带来的降级概率。
- AlphaSift 默认依赖 pin 更新到 `9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`，接入 wrapper 数据源 caller-side timeout、东财直连限速/抖动、策略目录元数据和防守策略。
- 选股任务状态轮询遇到可恢复超时时提示后台任务仍会自动重试，`.env.example` 补充相关超时调优项。
- 收敛个股分析评分与 DecisionSignal action 口径，统一 80/60/40/20 分段，并在风控降级时记录 raw/adjusted score、final action 与原因。
- Web 设置页左侧分类切换时仅在相关分类展示首次启动检查和 AlphaSift 辅助卡片，减少跨分类残留。

### 修复

- 修复 Windows 桌面端启动后端时固定传入 `--host 127.0.0.1` 导致 `.env` 中 `WEBUI_HOST=0.0.0.0` 不生效、局域网无法访问 WebUI 的问题；桌面端仍默认使用 `127.0.0.1`，仅在显式配置 `WEBUI_HOST` 后按配置绑定。
- 修复桌面端启动时 `.env` 中 `WEBUI_PORT` 与 Electron 自动选择端口不一致，导致窗口继续等待旧端口并连接超时的问题。
- 修复 macOS 桌面端从 Finder/Dock 启动时后端 PATH 看不到 Homebrew Codex CLI 的问题，并明确 Codex CLI 主分析与 Agent LiteLLM 工具调用分流诊断。
- 修复 Discord 长报告推送按 2000 字符上限分片逐段发送，遇到 429 限流会按 `retry_after`/`Retry-After` 有限重试，避免中途失败后只收到前半段报告。
- 修复日股、韩股和台股 `market_phase` 收盘集合竞价识别，避免临近收盘阶段仍被标记为普通 `intraday`。
- 修复 A 股个股分析遇到空 `belong_boards` 占位时不会继续补查所属板块、关联板块模块展示不稳定的问题。
- 修复大盘复盘在 LLM 标题漂移或正文缺少板块段时，Web 与推送报告偶发缺少板块主线的问题。
- 修复 Web 大盘复盘结构化数据成交额、指数点位、涨跌幅和高/低值格式化，避免浮点长尾或缺失值 `0.00` 直接展示。
- 修复 Web 首页个股栏在 stock-bar 摘要字段缺失或动作建议无法归类时隐藏情绪分与建议标识的问题。
- 修复 Web 设置页定时任务“立即执行一次”后台线程未传 `stock_codes` 导致任务崩溃的问题。
- 修复 `opencode_cli` 静态指令，避免全局 JSON-only 约束影响 `generate_text()` 与大盘复盘自由文本输出。
- 修复 yfinance 1.2.x 将 `Ticker.dividends` 返回为单列 DataFrame 时分红解析被丢弃的问题，恢复 TTM 每股分红与分红次数计算。
- 修复台股财务金额币别标示，将 TWD 金额标注为“新台币”，避免在 A 股语境下误读为人民币。
- 修复回测日线补全将 `605066.SH`、`SS605066`、`SS.605066` 等 A 股等价代码误向数据源请求 `SS605066`，导致回测数据不足的问题。

### 文档

- 新增 Agent `/chat/stream` progress event 契约文档，说明新增事件字段语义、Web 兼容边界、验证方式和回滚方式。
- 同步本地 CLI backend 隐私/部署边界，明确 local CLI 不是离线模型，Docker/CI/远端需自行安装登录，HRS 不读取 Claude/OpenCode credential 文件。
- 更新 README 三语入口和市场支持边界，说明台股 `.TW` / `.TWO`、三大法人报告区块、TWD 标注与收盘竞价识别能力边界。

### 测试

- 台股三大法人 fetcher 新增 live-smoke 脚本与 `@pytest.mark.network` 漂移检测测试，用于非阻断 network-smoke 定时任务核对 TWSE T86 / TPEx 核心字段与解析结果。

## [3.24.1] - 2026-06-28

### 修复

- 修正 Longbridge SDK 版本约束为按平台选择可安装版本，避免桌面与 Docker 发布在 `pip install -r requirements.txt` 时因不存在的 `0.2.75` 版本失败。

## [3.24.0] - 2026-06-28

### 发布亮点

- feat: 扩展台股、日股、韩股市场支持，覆盖台股 suffix-only 分析、台股三大法人资料层、JP/KR 大盘复盘和跨服务市场枚举。
- feat: 新增 GenerationBackend 抽象、`codex_cli` 本地 CLI backend、reserved Hermes 本地 HTTP 渠道和 prompt cache capability registry。
- feat: Web/API/Desktop 支持多时间定时推送与 runtime scheduler 热重建，Web 设置页补齐首次启动检查与定时任务面板。
- feat: 报告链路补齐信号归因、单股信号时间线、概念板块排行和通知/报告关联板块展示。
- fix: 修复 Docker/启动探针、静态资源 MIME、回测空结果、组合估值、通知 Markdown、AlphaSift 数据源和测试环境隔离等稳定性问题。

### 新功能

- 新增台股 suffix-only 个股分析 MVP：`.TW`/`.TWO` 代码可走 YFinance 日线与近实时行情，并补齐市场识别、交易日历和 Prompt 能力边界。
- 台股 `tw` 纳入 DecisionSignal、Portfolio、Intelligence 服务层、API 枚举和 Web 筛选，避免台股分析信号被市场归一化静默丢弃。
- 新增台股三大法人资料层 fetcher `TwInstitutionalFetcher`，支持 TWSE/TPEx 来源、日期转换、单日缓存和 fail-open 退化。
- 大盘复盘新增 `jp`/`kr` 市场，支持日经225/TOPIX、KOSPI/KOSDAQ 指数复盘，并扩展 `MARKET_REVIEW_REGION`、交易日过滤和 Web 设置枚举。
- 新增 GenerationBackend Phase 1 抽象和显式 opt-in 的 `codex_cli` 本地 CLI generation backend，提供结构化错误、fallback、stream 降级和 usage unavailable contract。
- 新增 reserved Hermes 本地 HTTP generation 渠道，提供 JSON generation、no-proxy 本地调用和 saved secret endpoint 绑定。
- 新增 Provider Cache Capability Registry，按 provider、API surface、gateway 与 verification status 建模 prompt cache 能力。
- 支持 `SCHEDULE_TIMES` 多时间定时推送，长运行 Web/API/Desktop 进程保存调度配置后可热启停或重建 runtime scheduler。
- 新增信号归因分析和 Web AI 建议页单股信号时间线，并为自动生成与历史回填的 DecisionSignal 写入默认 `decision_profile` metadata。
- 大盘复盘、Web 报告页和通知关联板块补齐概念板块排行与概念信号展示。

### 改进

- TickFlow 扩展为可选 A 股日 K、实时行情、股票列表/名称数据源，并增加 count、完整性校验和批量预取缓存保护。
- 硬化 JP/KR/TW suffix 识别、日韩股票种子索引、YFinance 报价/基本面上下文，以及 JP/KR Portfolio 与 Market Light 边界。
- Web 设置页新增首次启动配置检查卡与定时任务面板，隐藏内部 `SCHEDULE_TIMES` 键，并改善重复任务提示的关闭与自动消失体验。
- Web 历史报告详情不再内嵌 AI 建议卡片，结构化决策信号集中到 AI 建议页，并保留来源报告 ID/URL 参数精确定位。
- `GENERATION_BACKEND=codex_cli` 下普通分析与大盘复盘不再因缺少 LiteLLM API Key 被误判不可用，并改用 `--output-last-message` 文件读取最终响应。
- 本地 CLI backend 对 stdout/stderr 诊断预览和最终响应实行执行期总量上限，并补齐新增 generation backend 数字配置最大值校验。
- AlphaSift 默认依赖 pin 更新到 `0a7b9cd59e81718f851890535241bc105d4ddc64`，并默认走 HRS EastMoney 兜底 provider、暴露 source health 诊断。
- Docker Compose 默认内存建议提升到 1G；每日分析 workflow 兼容误将 `STOCK_LIST` 配到同名 Environment variables 的场景。
- Agent 路径同步 signal attribution prompt，通知报告摘要不再展开 AI 决策信号明细，完整信号保留在个股详情与单股报告。

### 修复

- API 异步批量分析共享概念板块排行缓存，避免同批多股重复拉取全市场概念排行。
- 修复通知 Markdown 表格转换在空单元格后将后续内容错配到错误表头的问题。
- 修复 Market Light 区域归一化拒绝 `jp`/`kr`、日韩历史列表市场阶段摘要误传 `analysis_phase` 和默认通知报告缺少 `dashboard.phase_decision` 的问题。
- 固定 Docker 可安装的 Longbridge SDK 版本为 0.2.75，并修复 Docker 镜像中 efinance 缓存目录属主导致 A 股数据源降级的问题。
- 持仓快照今日估值改为受限并发预取实时价，减少持仓较多时 Web 组合页面刷新超时。
- Web 首页重新分析完成后自动切换到同一股票最新报告，并修复 Windows 环境下 Web/Desktop 静态 JS 资源可能以 `text/plain` 返回导致黑屏的问题。
- 修复 `--serve --schedule` 与 Web/API runtime scheduler 状态脱节、立即执行忙碌状态误提示、重建定时任务重复监听和启动参数语义丢失。
- 修复 `main.py --serve-only` 在低配主机上因惰性 import 应用超出 uvicorn 启动自检窗口而反复重启的问题。
- 修复 Web 回测未传分析日期范围、股票代码未归一化导致成功响应但结果为空的问题，并为空候选、行情不足和非法后缀提供诊断信息。
- 修复 unsupported `GENERATION_BACKEND` 被当成空响应/模板 fallback、`codex_cli` stdout 重复计入输出上限和主分析 JSON schema fallback 语义回退的问题。
- Docker 部署中 Web 设置页保存自定义 Webhook 模板时会转义 `$content_json` 等占位符，并在运行时还原，避免 Compose 重新部署展开为空。

### 文档

- 补齐概念板块排行字段契约、通知报告行业/概念类型列展示和数据源稳定性与故障处理图示。
- 补充 JP/KR/TW suffix-only MVP、`MARKET_REVIEW_REGION` 保存/校验/回退矩阵、Market Light 边界和 PR 提交流程约束。
- 补充本地 CLI backend 隐私边界、非离线模型说明、Docker/CI 登录态限制和 `codex_cli` experimental/limited 状态。
- 补充回测请求链路说明，并同步更新 `docs/full-guide.md` 与 `docs/full-guide_EN.md` 示例。

### 测试

- 新增/更新台股、JP/KR 大盘复盘、GenerationBackend、`codex_cli`、Hermes、本地 CLI、runtime scheduler、回测和概念板块排行相关回归测试。
- 加强 `tests/test_analysis_api_contract.py`、`tests/test_analysis_history.py` 与 `tests/test_backtest_service.py` 的临时 `.env` 隔离，避免本地真实 `.env` 污染系统配置测试。

## [3.23.0] - 2026-06-20

### 发布亮点

- feat: DecisionSignal 贯通报告提取、Web 展示、反馈/后验、告警通知和组合风险，AI 建议信号进入可追踪闭环。
- feat: 新增合规 RSS/Atom 与 NewsNow 资讯源情报池，分析、Agent 和大盘复盘可 fail-open 复用本地资讯 evidence。
- feat: 新增日本/韩国 suffix-only 个股分析 MVP，支持 `.T`、`.KS`、`.KQ` 标的通过 YFinance 获取行情与技术上下文。
- feat: 新增 Token 用量监控看板、legacy LLM usage telemetry 和 message stability audit，增强 LLM 调用可观测性。
- fix: 修复运行流 live 状态、AlphaSift 缓存/字段兼容、发布说明诊断和日韩股票输入/历史展示等稳定性问题。

### 新功能

- 个股分析历史成功保存后会从最终报告 best-effort 提取 `DecisionSignal` 决策信号，复用现有信号去重、计划质量计算和脱敏契约。
- 新增 Web AI 建议页、持仓页 latest active 信号摘要、历史报告信号展示和更完整的信号详情卡片，展示评分、置信度、价格计划、催化、风险与失效条件。
- 新增 DecisionSignal 用户反馈、信号级日线后验评估、统计 API 与 Web 展示，使用 outcome/feedback sidecar 表并保留主信号表契约。
- 将 DecisionSignal 复用到告警、通知和组合风险：告警触发关联 latest active 信号或创建最小 alert 信号，通知追加低敏信号摘要，持仓风险聚合 active sell/reduce/alert 信号并保持 fail-open。
- 新增合规 RSS/Atom 资讯源配置、拉取、去重、入库、查询、retention 与基础安全校验 API，作为个股/市场资讯情报池基线。
- 资讯源新增 `newsnow` 类型、`NEWSNOW_BASE_URL` 配置和 `/api/v1/intelligence/sources/defaults` 默认源初始化接口，内置财联社热门、雪球热门股票、华尔街见闻快讯、金十数据和格隆汇事件等财经热点源。
- 个股分析、Agent 分析和大盘复盘会 fail-open 读取本地资讯/情报池，并把来源链接作为新闻上下文和 evidence 输入。
- 新增日本/韩国 suffix-only 个股分析 MVP：手输 `.T` / `.KS` / `.KQ` 代码可走 YFinance 日线与近实时行情，补充市场识别、交易日历、Prompt 语义、Web/API 类型和能力边界文档。
- 新增 Token 用量监控看板与 `/api/v1/usage/dashboard` 接口，展示 LLM 调用总量、Prompt/Completion 拆分、模型用量、调用类型分布和最近调用明细。

### 改进

- 为 `DecisionSignal` 补齐默认生命周期、同源窄 relaxed 去重、相反 active 信号自动 invalidated、terminal 状态不可 PATCH 复活和低敏 market phase hints 提取。
- 补充 Web decision-signals typed API wrapper 与契约隔离测试，并将历史报告 AI 建议查询收口到精确报告懒提取。
- HRS 数据源链路新增 Tencent 日 K 直连 fetcher、daily source health 短期熔断，并升级 AlphaSift 默认 pin/runtime bridge。
- 默认启用 `DAILY_SOURCE=auto`、Sina snapshot 优先级、候选级 quote context 与 LLM ranking timeout/max tokens 边界。
- 新增 legacy LLM usage provider/cache telemetry、message HMAC 诊断字段和普通个股分析 legacy message stability audit，不改变公开 Usage API、prompt 或 provider 参数。
- 问股页移动端策略选择改为默认收起的按钮入口，展开后仍可多选策略并在发送后自动收起，减少对对话内容的遮挡。

### 修复

- 修复运行流 live SSE 脱敏、后期 LLM/通知卡片重复、数据源聚合卡片过早成功、Web 首页窄侧栏挤压股票信息，以及个股分析自动生成大盘上下文时运行诊断互相串扰的问题。
- 修复 AlphaSift 热点题材 EastMoney 瞬断且无缓存时的空态、桌面更新热点缓存保留，以及 `leader_stocks` / `stocks` 双字段兼容问题。
- 修复 Web AI 建议页筛选/状态更新分页、价格计划单边入场价展示、持仓 latest 信号刷新、详情 JSON 安全渲染和卡片交互语义问题。
- 仅允许历史报告存在明确 `action` 或可解析动作时才触发决策信号懒回填，避免 `decision_type=hold` 等统计口径在建议不明确场景误回填。
- 修复 #1390 P6 DecisionSignal 在组合风险快照语义和默认聚合通知展示中的遗漏。
- 默认禁用 `/api/v1/intelligence/sources/defaults` 新建源，避免公开示例 NewsNow 实例被默认启用，同时统一 500 响应细节仅入日志、响应返回通用错误信息。
- Web 股票自动补全、输入校验、历史/任务展示和筛选补齐日韩 Yahoo 后缀代码、常用日韩股票索引与股票池裸码解析，避免 `000660`、`005930`、`7203.T`、`005930.KS`、`035720.KQ` 等场景崩溃、误入 A 股语义或历史分裂展示。
- 日韩个股分析在本地历史上下文缺失时会用 YFinance 日线兜底构造 K 线与技术指标上下文，避免报告误称日股/韩股核心行情和技术数据不可用。
- 发布说明生成查询 PR 作者失败时保留降级并输出包含 PR 编号和异常类型的 warning，便于排查 token、权限、网络或 GitHub API 异常。

### 文档

- README、完整指南和市场支持文档补充日股/韩股示例（`7203.T`、`005930.KS`），并明确 `.T/.KS/.KQ` 当前为 YFinance-only MVP。
- 新增 DecisionSignal 决策信号专题文档，补齐字段/API/Web/告警通知/组合风险/后验评估、脱敏、迁移与回滚说明，并收口 Web i18n 显示边界。
- 补充 AlphaSift 迁移与回退边界：明确 `ALPHASIFT_INSTALL_SPEC` 显式覆盖语义、`requirements.txt + DEFAULT_ALPHASIFT_INSTALL_SPEC` 与运行时兼容边界。
- 补充资讯源基线文档，说明 `NEWS_INTEL_*` 配置、NewsNow 自建建议、模型/provider/base URL 不变更边界，以及禁用或移除情报源变量的回退路径。

### 测试

- 新增/更新 DecisionSignal 服务、提取、反馈/后验、摘要、文档、通知、告警、持仓风险、Web 展示和 label 的回归覆盖。
- 新增/更新 RSS/Atom / NewsNow 情报源服务、API、安全校验、分析接入和配置兼容测试。
- 新增/更新日韩市场识别、股票索引、YFinance 行情兜底、Web 自动补全和输入校验测试。
- 新增/更新 LLM usage、运行流、AlphaSift、发布说明生成和移动端交互相关回归。


## [3.22.0] - 2026-06-13

### 发布亮点

- feat: 新增 DecisionSignal 独立存储与 API、运行流快照 API 和 Web 运行流视图，补齐建议动作结构化字段与历史/回测展示链路。
- feat: AlphaSift 热点题材链路升级为新版合约，支持热点榜单、题材详情、发酵路线、概念股详情、缓存与兜底数据源。
- feat: 个股分析默认注入当日大盘环境摘要，并在高风险/退潮环境下软化激进买入建议。
- fix: 修复问股历史追问标的上下文、自选股等价代码匹配、低质量新闻过滤、运行流脱敏与 AlphaSift 热点详情展示等稳定性问题。

### 新功能

- 新增独立 `DecisionSignal` 存储、Repository、Service 与 `/api/v1/decision-signals` API，支持来源/市场/股票/动作/期限/阶段去重、查询、续期、状态更新、懒过期、持仓过滤和敏感信息脱敏。
- 新增分析任务与历史报告运行流快照 API，提供 lanes、nodes、edges、events、summary 等统一契约，并从任务队列、运行诊断和 AnalysisContextPack overview 构建脱敏数据流/信息流。
- Web 端为活跃任务、历史报告和大盘复盘报告补充运行流视图入口，支持查看运行摘要、拓扑节点、事件流和基础排障详情。
- 新增 AlphaSift 热点题材链路：后端提供 `/api/v1/alphasift/hotspots` 与 `/api/v1/alphasift/hotspots/{topic}` API，Web 选股页新增热点题材区域并支持发酵路线与概念股查看。

### 改进

- 个股分析新增按当日/市场复用的大盘环境摘要，普通 Pipeline 与 Agent 分析 Prompt 可读取低敏大盘背景；新增默认开启的 `DAILY_MARKET_CONTEXT_ENABLED` 配置，用户仍可显式关闭。
- 个股分析与历史/回测展示新增可选八态 `action` / `action_label` 建议动作字段，保留 `operation_advice` 自由文本和 `decision_type=buy|hold|sell` 统计口径。
- 补充 Web decision-signals typed API wrapper 与契约隔离测试，暂不接入 UI。
- 完善运行时日志上下文，补充 logger name、触发来源、市场统计与实时行情预取链路状态，便于排查调度、API、Bot 和数据源降级路径。
- 持仓管理页新增持仓账户删除入口，复用现有账户软删除接口，误建账户会从默认列表、快照、风险、录入入口和事件列表隐藏且不物理清理历史流水。
- AlphaSift 依赖锁定更新到 `d038c52c468543726fc1fd830b53c27d3f09d6da`，并为新版 last-good snapshot、日线历史、行业/概念 provider cache、hotspot 榜单、题材发酵路线、概念股详情、上次成功热点缓存与 post-analysis 元信息补齐 HRS 运行期和 Web 适配。
- AlphaSift 热点题材读取默认优先使用上次成功缓存，手动刷新才实时拉取并覆盖缓存，实时拉取失败时尽量回退旧缓存。
- AlphaSift 热点题材区域改为默认折叠，展开并选中具体题材后再读取详情；发酵路线改为带时间标记的时间线展示，概念股可点击进入首页并直接启动分析。
- AlphaSift 热点题材数据链路复用同一次东方财富板块异动快照，并从真实涨跌幅、异动次数和高频个股推导趋势分、持续分、阶段与龙头样本。
- AlphaSift 热点题材刷新在合约层返回少量或缺少关键字段时改用 HRS 东方财富板块异动直连榜单，忽略少于 3 条的本地热点缓存，并补齐板块兜底字段。
- AlphaSift 热点题材卡片改为更紧凑的多列布局，概念股列表改为独立“分析”按钮触发个股分析；详情优先合并东方财富成分股、同花顺解析和板块异动龙头兜底并按日聚合发酵时间线。
- AlphaSift 热点题材详情新增 HRS 侧 30 分钟磁盘缓存，重复点开同一题材时复用发酵时间线与概念股详情；题材事件仅展示 AlphaSift 合约时间线、同花顺摘要、已配置新闻搜索或东财板块异动等真实来源。
- AlphaSift 热点题材消息催化改为摘要展示：配置 LLM 时优先压缩为一句题材催化摘要，未配置或调用失败时回退本地短摘要。
- AlphaSift 热点题材列表新增可选 `include_details` 详情预取，Web 默认随热点列表批量带回 Top 题材发酵路线与概念股并复用前端内存缓存；新闻催化在 LLM 不可用时改为本地事件归纳。
- 改造 `main.py --webui-only` 启动行为：若 FastAPI 监听端口已被占用，启动即 fail-fast 抛出明确错误并退出。

### 修复

- 问股从历史报告进入后的追问会持续携带当前标的，切回或重载已有会话时可从历史消息恢复基础当前标的，并由后端阻断未明确切换时的错误股票工具调用、交易所片段和指标缩写误路由。
- 自选股加入和删除按等价股票代码匹配港股及大小写美股变体，避免 `00700`、`HK00700`、`00700.HK` 或 `aapl`、`AAPL` 被误判为不同标的。
- 收紧建议动作 legacy fallback：否定/回避表达、中文金融上下文、`buy or sell`、多 guard 歧义文本以及英文复合词不再误渲染成 action badge；有结构化 `action` 时回测/历史趋势等入口按界面语言显示 action 标签。
- 股票新闻与多维情报搜索在相关度排序后新增域名无关的准入过滤，剔除下载/安装包/应用评分页及成人/招嫖服务垃圾页，并在同批已有有效标的/行业候选时移除 `score=0` 背景填充项。
- 修复历史报告运行流快照在混合时区事件时间戳下返回 500 的问题。
- 修复运行流 live SSE 事件未复用快照层递归脱敏规则的问题，避免本地路径、prompt/raw response、代理头等敏感诊断字段在 refetch 前短暂暴露。
- AlphaSift 热点题材默认加载在无缓存且旧适配层缺少 `alphasift.hotspot` 模块时返回空态，不再一打开选股页就显示 AlphaSift 未就绪；手动刷新仍会提示依赖需更新。
- 为 THS 发酵路线补充列名兜底：当 `stock_board_concept_summary_ths` 返回缺列时仅跳过该来源富化，不影响热点题材详情 API 返回。
- 桌面发布打包改用冻结可执行文件运行时探针校验 `alphasift.hrs_adapter`，避免 macOS PyInstaller 将模块内嵌进可执行文件时被文件系统/zip 扫描误判为缺失。
- AlphaSift 热点题材详情展示改为优先使用后端融合后的 `route`，避免旧 `timeline` 覆盖新闻/LLM 摘要；手动刷新热点榜单时会同步绕过同题材详情缓存。

### 文档

- README 与繁中 README 快速开始入口补充视频教程链接，并将桌面客户端入口文案调整为客户端配置教程。
- 补充 `docs/alphasift-integration.md`：明确 AlphaSift 锁定 commit 来源、Hotspot 契约边界、LLM/LiteLLM 兼容语义与关闭开关下回退路径。
- 补充 #1381 运行时范围、兼容边界、官方语义依据与常规发布回滚说明。

### 测试

- 覆盖 #1381 后端 runtime 与兼容核验：`tests/test_main_schedule_mode.py`、`tests/test_pipeline_daily_market_context.py`、`tests/test_daily_market_context.py`、`tests/test_daily_market_context_guardrail.py`、`tests/test_agent_executor.py`、`tests/test_config_env_compat.py`、`tests/test_config_registry.py` 与 `apps/hrs-web/tests/system_config_i18n.test.ts`。
- 新增/更新 AlphaSift 后端回归：`python -m pytest tests/test_alphasift_api.py -q`、`python -m pytest tests/test_docker_entrypoint.py -q`、`python -m pytest tests/test_main_schedule_mode.py -q -k "start_api_server_fails_before_thread_when_port_is_busy"`。

## [3.21.0] - 2026-06-07

### 发布亮点

- feat: 新增 Web UI 中英文界面语言切换和飞书 App Bot 通知模式，提升多人部署和企业通知场景体验。
- feat: 大盘复盘报告、历史入口和个股栏继续收口到结构化数据与统一 Markdown/GFM 渲染，Web/API 人工触发入口不再被交易日 gate 短路。
- feat: AlphaSift 选股链路改为可恢复后台任务，并完善 HRS LLM runtime bridge、默认适配层预置和兼容回归。
- fix: 修复英文界面残留中文、诊断展示、运行时环境变量展示、健康检查、桌面更新路径、工作流变量读取和多处 Web 窄布局问题。

### 新功能

- WebUI 新增独立界面语言状态与中英文切换入口，覆盖主导航、首页、登录、设置页和通用控件文案；UI 语言与 `report_language` 解耦，不改写报告语言链路。
- 飞书通知新增应用机器人（App Bot）模式，支持通过 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_CHAT_ID` 配置，无需额外创建自定义机器人。
- Web 大盘复盘报告新增专用展示视图，历史入口和首页即时结果统一使用 Markdown/GFM 渲染并隐藏个股专属模块。
- 大盘复盘新增结构化 `market_review_payload`，Web、历史详情和推送统一基于结构化数据渲染，并保留 Markdown 兼容展示。
- 新增默认关闭的 AlphaSift 选股页签，通过 `ALPHASIFT_ENABLED` 明确控制，并保留 `/install` 作为显式修复路径。

### 改进

- Web/API 大盘复盘人工触发入口不再因交易日检查或相关市场休市而短路跳过；定时任务、GitHub Actions 手动运行和 CLI 默认入口仍保持原交易日 gate。
- AlphaSift Web 选股改为后台任务提交与状态轮询，新增可恢复任务状态展示，避免外部快照、行情或 LLM 变慢时浏览器长请求超时。
- AlphaSift 选股 API 与服务层收敛到 `AlphaSiftService`，endpoint 仅做路由参数接收与错误映射。
- AlphaSift 与 HRS 的运行时 LLM 兼容桥接改为调用期注入，保留 `provider/model/base_url/custom headers/fallback` 语义链路，不做持久化迁移。
- Web 首页侧栏不再单独展示大盘复盘历史集合，最新大盘复盘作为 `MARKET` 并入个股栏，按最近分析时间参与排序，并复用个股栏的选择、删除、完整报告与历史趋势查看能力。
- 多股通知报告将市场阶段收敛为总览下方单行 `市场状态`，不再在每只股票摘要下重复展示数据质量和限制详情。
- API 错误响应构造收敛到共享 helper，保持既有错误 envelope 形状并降低 endpoint 重复代码。
- WebUI 绑定公网地址或 CORS 全开放且未启用管理员认证时新增运行时 warning；仅增加可观测性，不阻断启动、不改写配置。
- 数据库初始化新增 `schema_migrations` baseline 标记表与幂等记录，用于后续 schema 演进追踪；不迁移、不清理、不改写既有业务表数据。
- #1386 P6 复用市场阶段与 AnalysisContextPack 公开摘要联动告警、持仓手动分析、历史、回测和通知展示，不新增数据库迁移。

### 修复

- Web 英文界面补齐回测、组合风险与告警规则相关文案本地化，避免英文模式下残留中文筛选器、按钮和枚举标签。
- 综合情报搜索中的机构分析与业绩预期维度改用 180 天 provider 请求窗口，避免默认短新闻窗口漏掉财报、研报等周期性财经材料。
- Web 个股栏和历史卡片在窄布局下不再让市场阶段标签遮挡股票名称。
- 问股自由文本追问不再将 TTM、PE、YOY 等金融缩写误识别为新股票代码。
- [修复] GitHub Actions 每日分析工作流读取 SearXNG 自建实例地址时支持 Variables 优先、Secrets 回退，修复仅配置 Variables 时 URL 不生效的问题。
- Web/桌面端左侧导航选中态改用 border 实现，避免蓝色竖条指示器溢出侧栏边界；侧栏展开宽度 116px -> 136px，新增 rail 紧凑模式。
- Windows 桌面端自动更新安装目录不再预先加引号，避免带空格路径在自动安装时触发“缺少快捷方式 / 找不到 HermesX.exe”的系统弹窗。
- Agent 分析路径生成 AnalysisContextPack overview 前复用已落库日线分析上下文，避免日线已抓取成功仍显示 `daily_bars_missing`。
- 修正大盘复盘结构化 `breadth` 的可用性判断：当市场不支持或抓取失败时不下发 `breadth`，前端展示“暂无数据”，避免误导性 0 值。
- 大盘复盘语言行为遵循全局 `report_language`，并在美股中文场景下本地化市场标签与策略蓝图，避免混入英文策略段落。
- Docker Web 设置页读取配置时在活跃 `.env` 文件缺项时回退展示启动注入的同名环境变量，并补清相关挂载边界文档。
- 报告页运行诊断会区分数据源抓取成功与进入 LLM 分析输入，相关新闻区标注为报告页补充/后续检索资讯，避免与输入数据块状态互相误读。
- `/health` 根路径健康检查现在始终返回 JSON，避免静态 Web fallback 吞掉健康探针；`/api/health` 与 `/api/v1/health` 继续保持兼容。
- `ALPHASIFT_ENABLED` 关闭时不触发 `alphasift` 运行时注入；开启后优先复用已配置的 HRS/provider 配置并注入 `LITELLM_*` 与 `LLM_*` 运行时变量。
- 补齐 openai-compatible 场景下 base URL、`extra_headers` 与 `LITELLM_FALLBACK_MODELS` 的兼容路径与回退链验证。
- 桌面/镜像打包链路保持与运行时一致的 AlphaSift 适配层预置，避免 `pip install` 作为线上修复依赖。

### 文档

- 明确 Issue #777 UI 语言切换采用仓内 `UiLanguageContext` + `uiText` 实现，持久化 key 为 `HRS.uiLanguage`，并补充对应可视化验收指引。
- 明确大盘复盘展示链路、结构化 payload、语言行为、交易日 gate 差异和回滚边界。
- 补充 LLM / LiteLLM 兼容键在 Settings 展示与校验上下文中的回退边界，说明不改写、不迁移、不清理用户现有 provider/model/base URL 持久化配置。
- 补齐 #1602 运行诊断口径修复覆盖范围，说明仅统一输入与展示口径，回滚方式为常规发布回滚。
- 明确 AnalysisContextPack P6 文档、迁移与回滚边界，并同步既有 `SAVE_CONTEXT_SNAPSHOT` 到 `.env.example`、配置注册表、Web 设置帮助和完整指南。
- 补齐 #1386 P7 盘前/盘中/盘后分析的入口、迁移、回滚和用户可见说明。
- 为 AlphaSift runtime bridge 增加官方兼容依据落点，明确 provider/model/base_url/extra_headers/fallback 与回退边界。

### 测试

- Web 方向执行 `npm run lint`、`npm run build`、相关 Vitest 和 smoke 命令；未设置 `HRS_WEB_SMOKE_PASSWORD` 时 smoke 用例按设计 skip。
- Web 测试运行时声明 Node `>=20.19.0 <27` 与 npm `>=10`，并补 localStorage 测试兜底以稳定 Vitest。
- 增补 AlphaSift runtime bridge 与打包脚本静态验证，覆盖 `LLM_CHANNELS`、`LITELLM_FALLBACK_MODELS`、`alphasift.hrs_adapter`、`--collect-all alphasift`。

### chore

- 移除随 issue / PR 验收流程误入库的截图资产，并明确一次性截图证据应保留在 PR 描述、评论、附件或 artifact 中，不作为仓库文件合入。

## [3.20.0] - 2026-06-03

### 发布亮点

- feat: 新增 AlphaSift 选股入口、自动安装与稳定适配层，支持 Web 策略执行、LLM 重排展示和默认关闭的可控启用。
- feat: 完善个股历史、自选队列、市场阶段与 AnalysisContextPack 可见性，增强 Web 报告和 API 的结构化上下文能力。
- feat: MiniMax 默认模型升级到 `MiniMax-M3`，并补齐相关价格、预设和测试覆盖。
- fix: 修复健康检查、Windows 桌面更新与首次运行编码、ETF 日线 secid、LLM base_url 校验和 Agent 日线上下文误判等稳定性问题。

### 新功能

- 新增默认关闭的 AlphaSift 选股页签，通过 `ALPHASIFT_ENABLED` 开启后经由稳定适配层读取策略并执行选股。
- Web 首页左侧栏改为个股栏，按股票去重展示，大盘复盘置顶，点击个股加载最新报告，支持按代码变体（.SZ/.SH/.SS）归一化去重合并。保留全选、批量删除和删除确认入口；新增按股票代码批量删除 API `DELETE /api/v1/history/by-code/{stock_code}`。
- 报告详情右侧栏新增自选操作入口，支持查看当前股票是否在自选队列、一键加入或移除；大盘复盘报告不显示该操作。
- 问股页面输入区上方新增自选操作按钮，用户发送包含股票代码的消息后自动显示加入自选/从自选删除入口。
- Web 报告页新增同股历史趋势抽屉入口，历史列表摘要补充趋势、摘要、模型和分析时行情字段，支持按当前股票查看历史分析并加载更多。
- AnalysisContextPack P4 低敏 overview 接入历史详情、同步分析响应、completed 任务状态和 Web 报告页，展示数据块状态、来源、缺失原因与降级摘要。
- #1386 P5 为个股分析报告新增 `dashboard.phase_decision` 盘中决策护栏，并在保存历史前按市场阶段与数据质量限制高置信盘中买卖结论。
- #1386 P4a 新增 `analysis_phase=auto|premarket|intraday|postmarket` API 参数，并在异步任务 accepted、内存 status、list、SSE 与分析 pipeline 中透传请求阶段。
- #1386 P4b Web 报告页新增最终市场阶段标签，任务面板展示请求阶段，并复用 AnalysisContextPack 低敏数据质量摘要。
- MiniMax 渠道模型列表升级：新增 `MiniMax-M3` 并作为默认，按官方 OpenAI-compatible 文档支持 1M 输入上下文（项目保守注册为 `<=512K` 价格档：context_window 512K、`max_tokens` 128K，对应 $0.6/M 输入、$2.4/M 输出，>512K 输入价格档未建模），保留 `MiniMax-M2.7` 与 `MiniMax-M2.7-highspeed`，并保留 `MiniMax-M2.5` legacy 价格条目以兼容现有用户配置的成本估算。Web 设置页 MiniMax 预设模型与价格按 M3 刷新。
- 新增 AnalysisContextPack P1 内部契约与脱敏序列化测试。
- 市场阶段低敏摘要接入历史详情、同步分析响应和 completed 任务状态的 report metadata。

### 改进

- 首次运行配置校验补充缺失 AI Key、空 STOCK_LIST、Telegram/邮件成对字段和 Webhook URL 前缀诊断。
- AlphaSift 选股入口在 Web 侧边栏中移动到“问股”下方，贴近 Agent/研究辅助工作流。
- Docker 镜像构建阶段预置默认 AlphaSift 适配层，与桌面发布包一样避免运行期额外安装。
- AlphaSift 选股改为依赖 `alphasift.hrs_adapter` 的稳定接口，Web 策略列表由 AlphaSift 动态提供，不再在前端硬编码。
- AlphaSift 选股页补充 Run ID、快照数、过滤后数量、因子和风险详情，展开候选时展示真实明细，并暂时仅开放当前支持的 A 股市场。
- Web 设置页新增 AlphaSift 选股开关卡片，可直接开启或关闭选股页签。
- 开启 AlphaSift 选股时先切换 `ALPHASIFT_ENABLED` 并检查适配层可用性，缺失时自动调用受控安装接口，不再要求用户额外点击安装。
- AlphaSift 已开启但适配层缺失时，策略列表和选股接口会串行化自动安装锁定来源，并强制重装以覆盖旧版 `alphasift` 包。
- AlphaSift 选股页合并重复的快照源 fallback 提示，并保留 AlphaSift 自身的 Tushare 优先快照源逻辑。
- AlphaSift 选股页在 LLM 重排降级时展示 warning/source error/parse error，并避免把本地因子评分误显示为 LLM 判断。
- Web 设置页不再把 `ALPHASIFT_ENABLED` 作为普通数据源配置项重复展示，该值仅作为“开启选股”按钮背后的持久化状态。
- AlphaSift 关闭时隐藏 Web 左侧“选股”导航入口，避免误导未开启用户。
- 补充 AlphaSift 选股自定义策略显示逻辑，避免未匹配预设项时误显示“均衡多因子”。
- 新增 GET /api/v1/history/stocks 端点按 code 分组返回不重复个股列表；新增 GET /api/v1/stocks/watchlist、POST /api/v1/stocks/watchlist/add、POST /api/v1/stocks/watchlist/remove 端点支持自选队列增删查。STOCK_LIST 读写保持原样，不做自动归一化；add/remove 时归一化比较判断等价代码变体。
- 新增 useWatchlist hook 统一管理自选队列前端状态，复用 SystemConfigService 的 STOCK_LIST 配置项实现持久化。
- AnalysisContextPack P5 增加数据质量评分、`fetch_failed` 状态、Prompt 数据限制区块和 Web 低敏质量展示。
- #1386 P2-full 在 AnalysisContextPack Prompt 数据限制中追加市场阶段与降级数据的交叉约束，并修正中文分析 Prompt 的阶段化行情标签。
- 通知报告默认发送路径恢复既有渠道兼容转换与分片逻辑，新增 renderer 能力仅保留为未来扩展基础。
- 关联板块缺少类型数据时改为单行展示板块名称，避免生成整列 `N/A` 的板块表格。
- 优化 Web 报告详情页信息层级，将输入数据块和运行诊断下移为主体内容后的折叠辅助信息。
- 盘中分析补齐实时行情获取时间、provider 时间、stale、fallback 与 partial/estimated 标记，供 AnalysisContextPack 映射输入数据限制。

### 修复

- Agent 分析路径生成 AnalysisContextPack overview 前复用已落库日线分析上下文，避免日线已抓取成功仍显示 `daily_bars_missing`。
- 注册 /api/v1/health 路由并加入认证豁免，修复该路径返回 404 以及开启 ADMIN_AUTH_ENABLED 后健康探针收到 401 的问题。
- Windows 本地首次运行环境检查兼容非 UTF-8 控制台输出，并将 `requirements.txt` 注释改为 ASCII 以降低默认代码页下的依赖安装失败概率。
- AlphaSift HRS 适配层默认开启 LLM 重排，后端显式请求 `use_llm=True`，选股页展示 LLM 分数、判断、覆盖率和关注项。
- AlphaSift 嵌入 HRS 时复用 HRS 已解析的 LLM 模型、渠道和密钥配置，避免 Web 已配置 LLM 但选股 LLM 重排仍因缺少 provider key 降级。
- AlphaSift 选股复用 HRS LLM 路由时过滤未声明的托管 provider 备选模型，并把已声明渠道模型补入回退链，避免残留 Gemini fallback 覆盖可用的 HRS 渠道。
- AlphaSift 默认安装来源改为锁定 commit 的受信任 GitHub 地址；桌面模式自动安装不要求管理员会话，非桌面部署要求管理员认证会话，并继续限制安装来源。
- 修复 Web 开启 AlphaSift 时先安装后写配置导致默认关闭状态无法开启的问题。
- AlphaSift 状态与安装接口不再返回 `install_spec` 明文，仅返回 `install_spec_is_default` 等非敏感状态字段。
- AlphaSift 状态探测区分可选依赖缺失与非预期异常，异常场景记录 warning 并返回非敏感诊断信息。
- 调整 AlphaSift 筛选调用兼容：`screen` 以 `max_results` 为主并支持历史 `max_output` 关键词，同时允许策略透传以对齐前端手动策略参数。
- AlphaSift Web 选股请求使用独立长超时，避免开启 LLM 重排后被通用 30 秒 API 超时提前中断。
- 桌面端打包阶段预置 AlphaSift 并收集适配层，避免发布包运行时再要求管理员自动安装。
- AlphaSift 自动安装仅在 `status` 诊断为 `missing_module` 时触发（仅模块缺失场景）；适配层可导入但运行时异常不再自动 `pip install`，而是返回 `424` 并保留诊断，避免把真实运行时故障掩盖为重装。
- 收口 Web 中文界面残留英文文案与设置页 help 缺口，回测页改为中文展示，并让 Web 设置页仅展示已注册且带说明的配置项。
- Windows 桌面端自动更新静默安装时显式复用当前安装目录，避免自定义安装目录场景下卸载旧版本文件失败。
- Windows 安装器重试旧卸载器时对 `_?=` 安装目录参数加引号，修复旧版本安装在带空格路径时返回 2 导致自动更新失败。
- Windows 桌面端自动更新传给 NSIS 的 `/D=` 目录参数在包含空格时自动加引号，避免安装位置注册表被截断。
- 加固 LLM channel base_url 校验，避免解析差异导致 SSRF 绕过。
- 修正 efinance ETF 日线 Eastmoney secid 路由，避免沪市 ETF 被按深市 quote id 查询导致日线为空。

### 文档

- 明确 AlphaSift 与 LiteLLM 兼容边界：仅桥接 HRS 已声明 provider/model/base URL 为调用期注入，不对 `.env` 做 provider/model 路由迁移；回退方式为关闭 AlphaSift 并恢复原有 `LITELLM_*`/`LLM_*` 配置。
- 明确 AlphaSift 仅复用 HRS 现有 LLM/LiteLLM 配置语义，不新增 `LITELLM_MODEL`、`OPENAI_MODEL`、`OPENAI_BASE_URL`、`LLM_TIMEOUT_SEC` 等模型语义迁移；失败提示与回退路径统一沿用既有系统配置链路，仅影响 AlphaSift 选股能力本身。
- 明确 AlphaSift 自动安装来源锁定、`missing_module` 与运行时异常行为边界，以及 LLM/provider/base URL 与自定义通道回退路径，便于问题溯源与回滚到原有 LLM 配置。
- 明确同股历史趋势新增模型字段为历史快照展示元数据，不影响运行时 LLM Provider/Model/Base URL 路由与配置迁移清理；回退方式为按常规发布回滚本变更。
- 明确 #1311 的兼容性边界：渲染层仅消费分析结果 `model_used` 展示字段，未改动 `wechat/slack/feishu/telegram` sender 发送链路，不触发 provider/model/base_url 兼容迁移。
- 明确 AlphaSift 锁定 commit 的 `alphasift.hrs_adapter` 契约依据，以及当前 HRS API/Web 调用结构的兼容边界。
- 明确 Settings 页面对 LLM 配置仅做展示分组与字段归并，不改写或触发 LLM 迁移/回退路径；兼容现有 `LLM` 配置保存与回退语义。
- 新增 AnalysisContextPack P0 上下文盘点。
- 补齐告警中心 P8 文档与配置收口说明，明确 legacy JSON、高级规则、Web/API、Docker、GitHub Actions 与 Desktop 边界。

### 测试

- 同步更新 `llmProviderTemplates`、LiteLLM fallback pricing 与 MiniMax 预设相关单测，断言新默认模型。
- 补充 ETF 日线数据源路由、输入变体、fallback 与 MA 字段回归覆盖。

### chore

- 新增通知报告渠道能力画像、PreparedMessage 与结构感知 Markdown 分片基础设施，为 #1311 全渠道渲染适配打底。
- 预置企业微信、飞书、Telegram、钉钉、Slack 平台 renderer 元数据，暂不改变默认推送报告入口和可见版式。

## [3.19.0] - 2026-05-29

### 新功能

- 落地 #1391 Phase 1 运行诊断最小链路：任务/SSE 追加 trace_id，并记录日线与实时行情 ProviderRun 快照。
- 告警中心新增 P7 大盘红绿灯结构化规则，支持 `market_light_status` 与 `market_light_score_drop` 并复用现有 worker、触发历史、通知和冷却链路。
- 落地 #1391 Phase 2 运行诊断摘要：生成用户可读 RunDiagnosticSummary，提供历史报告诊断 API 与脱敏复制文本。
- 落地 #1391 Phase 3 运行诊断可见性：报告详情和任务面板默认折叠展示运行状态、trace 与可复制排障信息；后端通过 `api/v1/history/{record_id}/diagnostics` 与 `context_snapshot.diagnostics` 提供历史链路回填。
- 新增 AnalysisContextPack P1 内部契约与脱敏序列化测试。
- 新增 AnalysisContextPack P2 builder，从普通分析 pipeline 已有 artifacts 组装内部上下文包。
- 问股新增默认关闭的可见对话上下文压缩，支持 Web 开关、Agent 高级 preset、滚动摘要和最近轮次原文保护，降低长会话 token 消耗。
- 股票自动补全索引默认支持从 GitHub main 远程刷新并缓存到本地，Web/CLI 分析入口失败时自动降级到内置索引，降低摘帽和更名后旧简称污染分析的概率。
- 普通分析与 Agent 运行时 Prompt 接入 AnalysisContextPack 低敏摘要，保持 history/API/Web 输出兼容。

### 改进

- `scripts/fetch_tushare_stock_list.py` 可对 A 股中带 `XD`/`XR`/`DR`/`N`/`C` 前缀的名称进行回填修正，供自动补全刷新流程默认使用。
- Web 路由页面改为按需加载，降低首包体积并增加路由加载失败恢复提示。
- Web 完整报告 Markdown 抽屉改为按需加载。
- 新增市场阶段推断基线并明确盘前、盘中、午休、临近收盘、盘后和非交易日语义。
- 新增运行态市场阶段上下文构造与降级测试。
- 设置页配置帮助阶段性补齐 Web 设置页实际展示/可配置字段的中英双语文案，覆盖 Agent、回测、报告、通知路由、系统运行时、AI legacy、数据源和通知高级配置。
- P2-min：LLM Prompt 注入市场阶段上下文。

### 修复

- 股票自动补全索引生成缺少 `pypinyin` 时改为直接失败，避免写出缺失拼音字段的降级索引。
- 归一腾讯实时行情成交量为股口径，避免量能变化倍数被放大并误导分析报告。
- Docker 默认部署移除 `.env` 单文件挂载，避免 WebUI 保存配置时因 `os.replace` 更新挂载点触发 `Device or resource busy`。
- 收敛 #1391 Phase 0 A 股代码归属边界：补齐 `SH`/`SZ` 前缀场景的归属一致性，明确 `data_provider/baostock_fetcher.py`、`data_provider/pytdx_fetcher.py`、`data_provider/tushare_fetcher.py` 的本轮修复范围。
- 修复 `STOCK_LIST` 使用裸 A 股代码时 Baostock 等数据源 fallback 的内部格式转换，保持用户配置继续使用 6 位股票编号。
- Windows 桌面端自动更新在用户确认重启安装后改为静默执行安装器，并在停止内置后端后清理进程引用，降低安装器提示“每日股票分析无法关闭”的概率。
- macOS 桌面端将运行时配置迁移到用户数据目录，并在旧 `.app` 包内文件仍可访问时迁移 `.env`、数据库和日志，避免后续替换升级后重新配置。
- 恢复 Agent/历史兼容快照中的关联板块与板块联动字段提取，修复新版首页报告缺少“板块联动”的回归问题。
- 修正 Web 设置帮助中 legacy 告警 JSON 字段名与静默时段投递语义说明。
- 修复 Web 中文设置页在数据源、通知、系统与 Agent 区域的配置标题、说明和关键下拉选项漏翻问题。
- 修复问股会话切换和首页任务重连后可能残留 Agent/分析任务进行中状态的问题。
- 问股 single-agent 新增 provider-aware trace 分轨，跨轮保留 DeepSeek V4 thinking + tool-call 的 `reasoning_content` 与工具协议材料。
- 为 Akshare 新浪/腾讯 A 股历史兜底接口增加调用级超时，并补齐 Tushare `605xxx` 沪市代码路由回归测试，避免定时分析因数据源无响应而挂起。
- 将 `exchange-calendars` 依赖下限提升到 `4.13.0`，避免 pandas 3 环境导入交易日历时因 Timedelta 单位 `T` 失效导致分析失败。
- 交互式命令（钉钉会话、飞书会话、Telegram）触发的分析结果只回到来源会话，不再同时广播到静态通知渠道。
- 适配 Longbridge OAuth 2.0 认证与 token 缓存恢复，避免新后台无 Legacy Access Token 时长桥数据源被误判为未配置。
- Longbridge OAuth 路径在当前 SDK 不支持 `OAuthBuilder` / `Config.from_oauth` 时明确日志降级，避免 Linux/Docker 仅可安装旧 SDK 时构建失败。
- 兼容 YFinance 日线返回未命名日期索引的场景，避免标准化后缺少 `date` 列导致美股日线 fallback 中断。

### 文档

- 新增 #1391 Phase 0 运行诊断契约文档，明确 trace_id、诊断摘要、关键链路范围与脱敏/fail-open/retention 边界。
- 补齐告警中心 P8 文档与配置收口说明，明确 legacy JSON、高级规则、Web/API、Docker、GitHub Actions 与 Desktop 边界。
- 说明本次桌面修复仅覆盖 Windows NSIS 更新安装链路与后端进程生命周期清理；未改动设置项保存/模型运行时清理语义。移除此前误入的 `docker/Dockerfile` `npm registry` 变更，恢复部署构建与更新修复的职责隔离。
- 新增 AnalysisContextPack P0 上下文盘点，明确字段质量状态、现有状态映射和首版 pack 边界。
- 明确 #1391 Phase 2 的结构化检测告警为非配置迁移信号：`agent_max_steps`/`agent_orchestrator_timeout_s` 非法值会 fallback 至默认并产生日志告警，新增诊断链路仅新增 `context_snapshot`/`RunDiagnosticSummary` 读写字段，不改写 `litellm_model`、`agent_litellm_model`、`openai_base_url`、LLM channel 路由或配置迁移语义。
- 补充 #1391 Phase 3 兼容性说明：记录后端诊断持久化、历史查询与通知回写链路变更边界与回滚策略，并补齐后端门禁级验证要求。

### 测试

- 收敛 #1391 Phase 3 后端/API 与 Web 回归检查：`./scripts/ci_gate.sh`、`test_pipeline_market_phase_context.py`、`test_analysis_api_contract.py`、`test_analysis_history.py`、`npm run lint`、`npm run build`。
- 执行 `python -c "import exchange_calendars as xcals; xcals.get_calendar('XSHG'); print('ok')"` 通过验证，以覆盖导入与交易日历初始化兼容性。

## [3.18.0] - 2026-05-21

### 发布亮点

- feat: 告警中心扩展到 P2-P6，补齐后台评估、真实通知结果、业务冷却、技术指标规则，以及自选股 / 持仓 / 账户联动规则。
- feat: 个股分析支持策略选择，新增热点题材、事件驱动、成长质量和预期重估策略，并为 HK/US 报告补充基本面、财务摘要、股东回报和关联板块。
- feat: 新增 Finnhub / AlphaVantage 美股数据源适配器，扩展美股日线 failover 链，提升美股行情获取韧性。
- fix: 修复桌面端发布打包、分析状态接口、AlphaVantage 涨跌幅、持仓实时估值、告警历史去重、数据库冷启动和 fallback pricing 注册等稳定性问题。

### What's Changed

- feat: Add alert-center P2-P6, Web strategy selection, HK/US fundamental context, static-report financial sections, and Finnhub / AlphaVantage US-market fallback.
- improve: Refine LiteLLM parameter recovery, yfinance currency/dividend handling, RSI calculation, market-review presentation, stock-news relevance ranking, and report table rendering.
- fix: Harden desktop packaging/update assets, completed analysis-status responses, AlphaVantage pct_chg routing, portfolio realtime snapshots, alert trigger dedupe, DatabaseManager cold start, and fallback pricing registration.
- docs/tests: Add beginner setup and settings-help docs, document compatibility/rollback boundaries, and extend regression coverage for API, alert, packaging, and release paths.

## [3.17.1] - 2026-05-16

### 发布亮点

- fix: 桌面端 Windows / macOS 打包脚本显式关闭 electron-builder 自动发布，避免 tag 构建时因缺少 `GH_TOKEN` 在本地打包完成后失败；Release workflow 继续负责上传和发布产物。

### What's Changed

- fix: Add `--publish never` to the Windows and macOS Electron packaging scripts so tag builds only create local artifacts and GitHub Actions handles release upload/publish.

## [3.17.0] - 2026-05-16

### 发布亮点

- feat: 新增 Alert API MVP，支持告警规则 CRUD、启停、一次性测试以及触发/通知结果查询，首版覆盖 `price_cross` / `price_change_percent` / `volume_spike` 并保持 legacy 配置兼容。
- feat: 通知网关新增 ntfy 与 Gotify 一等渠道，并补齐通知降噪、静态渠道隔离、诊断、Web 测试和 GitHub Actions env 对照校验。
- feat: Windows 桌面安装版接入自动更新安装链路，支持后台下载、确认重启安装、运行时文件备份/恢复和发布产物元数据校验。
- improve: 大盘复盘新增概念排行、人气股、涨停池等底层数据源，支持指数涨跌颜色语义配置，并将复盘结果写入历史记录。
- improve: Web 设置页支持 `.env` 配置备份导入/导出和通知/Agent 区域局部错误兜底；报告新增 `REPORT_SHOW_LLM_MODEL` 开关控制模型信息展示。
- improve: Docker 启动入口自动修复挂载目录权限并在日志目录不可写时降级到控制台，减少普通部署的手动修复步骤。
- fix: 数据源缺凭据或连接失败时更温和降级，Longbridge / Pytdx 加入冷却，资金流缺失时避免输出高置信买入结论。
- fix: 分析与报告链路兼容 OpenAI-compatible `content_blocks` 响应，归一策略价格字段，并修复大盘复盘滚动和历史记录丢失问题。
- docs: 补齐通知、告警中心、桌面打包、README / 指南和 PR title 治理说明，明确多处配置兼容边界与回滚路径。
- test: 增加 Alert API、通知降噪/路由、Docker entrypoint、数据源预取、桌面更新链路和分析历史等回归覆盖。

### What's Changed

- feat: Add an Alert API MVP with rule CRUD, enable/disable, one-shot testing, trigger history, notification results, and legacy config compatibility.
- feat: Promote ntfy and Gotify to first-class notification channels with Web tests, routing, Actions integration, diagnostics, and noise control.
- feat: Add the Windows desktop auto-update install flow with runtime state backup/restore and release artifact metadata verification.
- improve: Extend market review data sources, add configurable index color semantics, and persist market review results into analysis history.
- improve: Add Web `.env` backup import/export, local settings panel error boundaries, and a report model visibility toggle.
- improve: Harden Docker startup by repairing mounted directory permissions and falling back to console logging when mounted logs are not writable.
- fix: Cool down unavailable optional fetchers, reduce noisy Longbridge/Pytdx retries, and downgrade buy advice when capital flow data is missing.
- fix: Handle OpenAI-compatible `content_blocks`, normalize strategy price fields, and recover market review scrolling/history behavior.
- docs/tests: Update notification, alert, desktop packaging, README/guide, and governance docs; add focused regression coverage for the new release paths.

## [3.16.0] - 2026-05-10

### 发布亮点

- feat: Web 首页新增“大盘复盘”触发入口、任务轮询与完成后报告直出；首次启动配置状态可提示缺口并引导到系统设置。
- feat: 新增通知路由策略，支持按 report、alert、system_error 将通知收窄到指定渠道；Web 设置页支持通知渠道一键测试。
- feat: 系统设置页新增配置项帮助入口与多语言帮助文案基础设施，首批覆盖自选股、LLM 主模型、LLM 渠道、飞书 Webhook 与 WebUI 监听地址。
- improve: 大盘复盘 API、CLI、Bot 共用 `build_market_review_runtime` 装配路径，补齐 `litellm_model` / `llm_model_list` 与 legacy key 回退说明。
- improve: 个股报告操作建议结合支撑/压力、量能、筹码与主力资金流校准，减少买入/卖出剧烈切换，并补强 Agent 决策兜底。
- improve: Docker 镜像支持非 root 用户运行，LiteLLM 依赖约束放宽到后续安全 1.x 修复版本。
- fix: 修正 LLM 渠道测试中 `Model disabled`、provider blocked 等错误分类，避免被误报为网络异常。
- fix: 港股日线跳过不支持港股的内置历史数据源；北交所 `BJ` 前缀与 `.BJ` 后缀代码校验保持一致。
- fix: Web 大盘复盘按钮可观测性、Windows fallback 锁进程探测和催化线索展示更稳健。
- docs: 新增文档中心与配置帮助维护说明，清理 README、完整指南与配置指南中的临时 PR/文档同步说明。

### What's Changed

- feat: Add a Web home market-review trigger with task polling and inline report display; setup status now points users to missing configuration.
- feat: Add notification routing by report, alert, and system_error; add one-click notification channel testing in Web settings.
- feat: Add settings field help infrastructure with multilingual help text for the first batch of core configuration fields.
- improve: Share `build_market_review_runtime` across API, CLI, and Bot market review paths; document `litellm_model` / `llm_model_list` and legacy key fallback behavior.
- improve: Calibrate stock advice with support/resistance, volume, chips, and main-force capital flow; strengthen Agent decision fallback behavior.
- improve: Run Docker images as a non-root user and relax LiteLLM constraints to allow safe future 1.x fixes.
- fix: Classify `Model disabled`, provider blocked, and related LLM channel test errors more accurately instead of reporting them as generic network failures.
- fix: Avoid unsupported built-in historical providers for Hong Kong daily data; align Beijing Stock Exchange `BJ` prefix and `.BJ` suffix validation.
- fix: Improve Web market-review observability, Windows fallback lock probing, and market catalyst snippet rendering.
- docs: Add the documentation index and settings-help maintenance guide; remove temporary PR/doc-sync notes from README and user-facing guides.

## [3.15.0] - 2026-05-05

### 发布亮点

- LLM 渠道配置体验继续升级：新增 Anspire OpenAI-compatible 网关接入，并补齐常用服务商预设、官方来源、能力标签、配置注意事项和 GitHub Actions 显式映射。
- Web LLM 配置检测更可诊断：细分错误 reason，并支持用户显式触发 JSON、tools、vision、stream 运行时 smoke。
- LLM 运行时配置清理更稳健：只清理托管 provider 的失效运行时选择，并保留 `cohere/*`、`google/*`、`xai/*` 等直连 provider 兼容语义。
- 通知与 Bot 状态可观测性增强：自定义 Webhook 支持 JSON body 模板，Bot `/status` 展示更完整的 LLM、Agent 与通知渠道状态。
- 大盘复盘、实时告警、Agent weak 兜底和持仓估值继续补强，降低默认值覆盖、缺价污染和配置排障成本。

### 新功能

- 支持 `ANSPIRE_API_KEYS` 默认接入 Anspire OpenAI-compatible 大模型网关，并在 LLM 渠道编辑器补充 Anspire Open 预设。
- 自定义 Webhook 支持 `CUSTOM_WEBHOOK_BODY_TEMPLATE` JSON body 模板，便于适配 AstrBot、NapCat 和自建推送服务。
- 大盘复盘结构化区块新增大盘红绿灯结论，基于盘面温度输出 green/yellow/red、核心原因和操作建议。
- EventMonitor 支持 `price_change_percent` 涨跌幅阈值规则，可按上涨或下跌方向触发实时告警。
- Web LLM 渠道编辑器新增常用服务商配置模板与预设，覆盖 MiniMax、火山方舟、OpenAI、Claude、Gemini、Kimi、Qwen、GLM、豆包等入口。

### 改进

- Web LLM 配置检测补充细分错误分类，并新增显式触发的 JSON/tools/vision/stream 运行时 smoke；默认测试和保存流程不变，检测结果仅作为当前配置的一次 best-effort 诊断。
- Bot `/status` 展示统一 LLM 主模型、Agent 模型、渠道模式、YAML 配置和更多通知渠道状态。
- Web LLM 渠道编辑器展示 provider 能力标签、官方来源链接和配置注意事项提示；这些标签仅用于配置参考，不代表运行时能力已验证通过。
- 抽出 Web LLM provider preset 单一模板数据源，保持现有配置保存语义不变。
- 补齐 LLM provider channel 在 GitHub Actions 中的显式映射，并同步 `.env` 示例与配置文档。

### 修复

- Agent weak 完整性兜底在模型缺少评分、趋势、操作建议或 dashboard 关键块时优先保留本地趋势分析结果，并只补齐真正缺失的仪表盘字段，避免首页评分被默认 50 覆盖。
- 统一持仓快照输出现价、市值、浮盈亏、收益率与价格元信息，避免缺价或 stale 价格污染持仓估值。
- LLM 渠道测试补充结构化诊断与设置页排障提示，便于定位 provider、模型、Base URL 和鉴权配置问题。
- 明确 runtime 清理兼容边界：仅对托管 provider（`gemini`、`vertex_ai`、`anthropic`、`openai`、`deepseek`）触发保存前失效值清理，`cohere/*`、`google/*`、`xai/*` 直连值按 legacy 兼容路径保留，不做无提示迁移或覆写。
- 将 MiniMax 预设调整为官方 OpenAI-compatible Base URL 和当前模型示例，并补充 MiniMax、火山方舟、LiteLLM 兼容来源与回退说明。
- 移除截图识别对 Gemini 3 Vision 模型的过时降级逻辑，默认推断改用当前 Gemini 模型配置。

### 文档

- 完善 LLM provider 配置文档，补充配置方式选择、Actions 变量对照、运行时检测边界、错误 reason 排障和回滚路径（#1180）。
- 补充 LLM 渠道编辑器的官方来源、依赖兼容窗口、保存时的运行时模型清理规则，以及旧配置回退路径说明。
- 为 `cohere/*`、`google/*`、`xai/*` 直连语义补充官方 provider/model 说明、`litellm>=1.80.10,<1.82.7` 兼容依据引用，并明确示例模型名仅为配置保留行为说明而非可用性背书。
- 明确 `price_change_percent` 事件告警仅为配置与运行时规则扩展，未变更模型/provider/base URL/LiteLLM 兼容语义；回退路径为关闭/移除 Event Monitor 配置。
- 同步 README、DEPLOY、full-guide、Anspire、AIHubMix 与 SerpAPI 相关说明，统一外链、配置口径和评审一致性说明。

### 测试

- 补齐 AI 配置页与 `task_queue` 的 LLM 运行时清理/同步回归证据：恢复渠道模型时保留 fallback、编辑模型列表期间不静默清空运行时选择，渠道无可用模型时清理失效 runtime 引用，并覆盖 legacy key 与 `cohere/*`、`google/*`、`xai/*` 直连 provider 保留语义。
- 覆盖 Web LLM 配置检测的细分错误分类，以及 JSON、tools、vision、stream 运行时 smoke 的显式触发路径。

## [3.14.2] - 2026-04-30

### 发布亮点

- 大盘复盘扩展到港股，并让 Bot `/market` 与 CLI/调度入口使用一致的交易日过滤语义。
- 问股与 Agent 链路增强配置缺失、决策 fallback 和多策略选择体验。
- LLM 与分析报告链路提升稳定性：非法 JSON 响应会继续尝试备用模型，LiteLLM DEBUG 日志默认降噪。
- 新增只读首次启动配置状态接口，为后续配置向导和 smoke run 奠定基础。

### 新功能

- 大盘复盘支持港股市场：`MARKET_REVIEW_REGION` 新增 `hk` 选项；`both` 扩展为 A股+港股+美股，并新增港股指数（HSI/HSTECH/HSCEI）复盘链路。
- 新增只读首次启动配置状态接口 `GET /api/v1/system/config/setup/status`，用于识别 LLM、Agent、自选股、通知和本地存储配置缺口；该接口不会重载运行时、写入 `.env` 或创建数据库文件。

### 改进

- 问股页面支持组合选择多个 Agent 策略。

### 修复

- Bot `/market` 命令复用 `get_open_markets_today()` / `compute_effective_region()` 做交易日过滤：结果作为 `override_region` 透传给 `run_market_review`；若结果为空字符串则跳过复盘并推送“今日相关市场休市”，与 CLI/调度入口行为一致。
- 问股 Agent 在未配置可用 LLM 时保留后端真实错误原因并维持 `done.success=false` 失败语义，避免前端把配置缺失误当成成功回答。
- Agent 模式未生成有效决策仪表盘时保留本地趋势分析的评分、趋势和操作建议，并将强买/强卖 fallback 归一到兼容的 `buy`/`sell` 决策类型，避免首页结果被 `50 / 观望 / 未知` 缺省值覆盖。
- 持仓快照现价缺失时不再静默回退为持仓成本；当天快照优先使用历史收盘价，仅在缺失时使用实时价 fallback，缺价持仓不再污染市值与未实现盈亏汇总，并为持仓明细返回价格来源、日期、stale 与缺价状态。
- 分析 Prompt 在注入 `trend_analysis` 前按最终 `trend_status` / `ma_alignment` 清洗互斥理由：空头结构移除看多理由、多头结构移除空头结构风险，并在事件/技术冲突与异常放量（>10 倍）时强制提示“事件先行、技术待确认”与量能降权。
- LLM 返回非 JSON 响应时同样触发备用模型切换：主模型成功返回但无法解析 JSON 时，不再立即降级为纯文本 fallback，而是依次尝试 `LITELLM_FALLBACK_MODELS` 中的备用模型；所有模型均无法返回合法 JSON 时，再降级为文本 fallback。
- LiteLLM 内部 DEBUG 日志默认压低到 WARNING，避免流式生成时 token 级日志污染 `stock_analysis_debug_*.log`；如需排查 LiteLLM 内部细节，可临时设置 `LITELLM_LOG_LEVEL=DEBUG`（Fixes #1156）。

### 文档

- 补充 LLM 配置指南与 FAQ，明确问股 Agent 对 `LITELLM_CONFIG` / `LLM_CHANNELS` / legacy `GEMINI_*` `OPENAI_*` `ANTHROPIC_*` 的兼容优先级、回退路径与“不静默迁移旧配置”的结论。

### 测试

- 新增 `tests/test_bot_market_command.py`，覆盖 `MARKET_REVIEW_REGION=both` + open markets `{"cn","us"}` / `{"cn","hk"}` 的 `override_region` 透传断言，并覆盖全市场休市跳过与关闭交易日检查路径；新增 `tests/test_yfinance_hk_indices.py` 覆盖港股指数符号映射与部分/全部失败降级路径。
- 补齐 `task_queue` 轻量导入 stub 的股票代码规范化函数，恢复 `tests/test_task_queue_config_sync.py` 收集与运行。

## [3.14.1] - 2026-04-26
- [测试] 修正大盘复盘 prompt 测试对“明日交易计划”标题的断言，并同步桌面端版本号，恢复发布 gate。

## [3.14.0] - 2026-04-26

### 发布亮点

- 📊 **大盘复盘升级为盘后工作台式结构** — A 股复盘固定输出盘面温度、指数明细、板块 Top 表、新闻催化、明日交易计划和风险提示，减少纯文字复盘的重复与空泛。
- 🖥️ **桌面端新增 GitHub Release 更新提醒** — Windows/macOS 桌面端启动后自动检测新版本，也可从设置页手动检查并跳转下载页。
- 🤖 **Pipeline Agent 数据加载大幅降噪** — K 线工具改为 DB-first 并预热 240 天历史数据，避免同一只股票重复 HTTP 请求。
- 🐳 **Docker 发布链路整理** — 发布工作流收敛为正式发布与手动补发两条路径，官方 Docker Hub 镜像名统一为 `ArcSeek-X/HermesX`。
- 🔧 **LLM 渠道与 DeepSeek V4 配置补强** — GitHub Actions 定时分析补齐多渠道变量透传，DeepSeek 官方渠道预设与示例同步到 V4。
- 🧩 **桌面端静态资源一致性校验** — 打包链路和运行时都能更早发现静态资源错配，降低 Release 包白屏排查成本。

### 新功能

- 🏠 **Web 首页历史报告区新增重新分析入口** — 支持基于原始 prompt 重做同一只股票同日期的分析。
- 🖥️ **Windows/macOS 桌面端新增 GitHub Release 更新提醒** — 启动后自动检测新版本，并支持从设置页手动检查后跳转下载页。

### 改进

- 📊 **A 股大盘复盘报告改为结构化盘后工作台版式** — 固定输出盘面温度、指数明细、板块 Top 表、新闻催化和明日交易计划。
- 🐳 **Docker 发布工作流收敛** — 更清晰地区分正式发布与手动补发链路，并统一官方 Docker Hub 镜像名为 `ArcSeek-X/HermesX`。
- 🤖 **Agent 日线工具优先复用本地缓存** — 同时持久化新获取的日线与新闻情报，减少重复数据源调用。

### 修复

- 🤖 **Pipeline Agent K 线工具 DB-first 加载** — `get_daily_history` / `analyze_trend` / `calculate_ma` / `get_volume_analysis` / `analyze_pattern` 改为优先读取本地 DB，消除同一只股票 9x5=45 次重复 HTTP 请求（Fixes #1066）。
- 🤖 **Pipeline Agent 执行前按需预热 240 天 K 线历史到 DB** — 正常情况下 K 线工具调用无需重复网络请求。
- 🕒 **冻结 `target_date` 并通过 ContextVar 透传到 Pipeline Agent K 线工具线程** — 消除跨收盘边界时间漂移。
- 🪟 **Windows 桌面端后端日志转抄编码修复** — 转抄 stdout/stderr 时优先使用 UTF-8，并兼容本地代码页回退，避免中文日志乱码。
- ⚙️ **GitHub Actions 每日分析工作流补齐 LLM 渠道变量透传** — 支持 `LLM_CHANNELS`、多 Key 与常用 `LLM_<NAME>_*`，避免本地可用的多模型配置在云端定时任务中失效（Fixes #1063, #872）。
- 📈 **历史报告详情接口修正 `change_pct` 取值** — 使用 `is None` 判断避免把 0.0（平盘）当作缺失值丢弃，移除错误的 `change_60d` 兜底，并在缺失时回退到原始实时行情字段（Fixes #1084）。
- 🔧 **DeepSeek 官方渠道预设与示例配置同步到 V4** — 保留 legacy `deepseek-chat` 默认值并增加废弃提示，同时修正模型发现后旧运行时选择导致保存失败的问题（Fixes #1108, #1109）。
- 🧩 **桌面端打包链路新增静态资源一致性检查** — `scripts/check_static_assets.py` 会在源 `static/` 与 PyInstaller 产物中校验 `index.html` 引用的资源是否真实存在，运行时也会在错配时写入明确日志，避免重现 Release 包打开后白屏（Refs #1064 / #1065 / #1050）。
- 🧩 **后端 `/assets/*` 改为显式路由托管** — 资源缺失时返回与请求扩展名匹配的 `text/javascript` / `text/css` 404，减少默认 JSON 错误响应带来的排查误导（Refs #1064）。
- 🌙 **`kimi-k2.6` 自动使用固定温度** — 主分析、大盘复盘和 Agent 调用该模型时自动使用 `temperature=1.0`，避免模型拒绝默认温度请求（Fixes #1102）。

### 文档

- 🐳 **补充官方 Docker 镜像使用说明** — 增加镜像拉取、`docker run` 用法与 `.env` / 数据目录映射说明，不再只覆盖 Compose 部署路径。
- 📨 **修正飞书自定义机器人 Webhook 示例** — `feishu_sender.py` 中的示例改为 interactive card JSON，并补充飞书自动化 Webhook 触发器配置教程。
- 📚 **优化根 README 结构** — 保留首页级功能特性、技术栈、快速开始、推送效果、Web、Agent、赞助商和新闻源入口，将细配置、交易纪律和基本面语义收口到完整指南，并将 Docker 徽章指向官方镜像页。
- 🌐 **同步英文与繁中 README 的精简入口结构** — 同时补齐完整指南中的 LLM 用量 API 与持仓管理说明。
- 🤝 **调整 AI 协作与 PR 模板中的 README 维护规则** — 明确 README 非必要不更新，细节优先进入专题文档。

### 测试

- 🧪 **稳定市场复盘相关测试的 LiteLLM stub 行为** — 避免本机安装的 LiteLLM 在测试收集顺序变化时影响市场复盘单元测试。
- 🧪 **pytest 默认跳过前端依赖目录** — 本地存在 `apps/hrs-web/node_modules` 时不再被后端测试递归扫描，避免发布前 gate 被无关目录拖慢。

## [3.13.0] - 2026-04-21

### 发布亮点

- 🌉 **长桥 OpenAPI 数据源接入** — 美股/港股行情优先使用 Longbridge，YFinance / AkShare 自动兜底；未配置时行为不变。
- 📈 **Tushare 港股全链路扩展** — 港股日线通过 `hk_daily` 获取；筹码分布对港股返回 `None`；换算单位跟随港股口径，不再套用 A 股手/千元规则。
- 🔍 **Anspire Search 语义搜索接入** — 配置 `ANSPIRE_*` 后即可使用 Anspire Search 获取实时行情及资讯，未配置时完全透明。
- 🚀 **普通分析链路支持 LLM 流式生成** — 首页任务 SSE 新增 `task_progress` 事件，进度更细化；不支持流式的 provider 自动回退到非流式调用。
- 🤖 **Web 渠道编辑器支持按需拉取可用模型列表** — `/v1/models` 统一模型发现入口，多选写回 `LLM_{CHANNEL}_MODELS`，拉取失败时保留手动输入降级。
- 🛡️ **Agent 稳定性与预算护栏全面补强** — `AGENT_MAX_STEPS` 语义统一、技能降级不中断管线、SSE 异常透传、技能加载 warning 日志补齐。
- 🛠️ **SQLite 写入链路原子化** — 批量原子 upsert + WAL + `busy_timeout` + 有限写入重试，显著降低批量分析并发锁竞争。

### 新功能

- 🌉 **集成 Longbridge OpenAPI 作为美股/港股可选数据源**（fixes #981）— 配置 `LONGBRIDGE_*` 后优先使用长桥获取日线与实时行情，YFinance / AkShare 兜底；未配置时行为与此前一致。联调使用 `tests/longbridge_live_smoke.py`（手动脚本，不参与 pytest 收集）。
- 📈 **Tushare 支持港股日线查询** — 配置 Tushare 凭证后调用 `hk_daily` 接口获取港股数据；权限不足时抛出异常，与原流程一致。
- 🔍 **集成 Anspire Search 可选语义搜索后端** — 配置 `ANSPIRE_*` 可使用 Anspire Search 获取实时行情及新闻资讯；未配置时行为与此前一致。联调使用 `tests/test_anspire_search.py`（手动脚本）。
- 🚀 **普通分析链路支持 LiteLLM 流式生成与更细任务进度** — 股票分析在 LLM 阶段优先尝试 `stream=True` 并在服务端累积 chunk，首页任务 SSE 新增 `task_progress` 事件与更细的 `message/progress` 更新；仅在最终 JSON 解析成功后持久化历史报告；不支持流式的 provider 自动回退到非流式调用。
- 🤖 **Web AI 模型配置支持按渠道获取可用模型列表** — 渠道编辑器支持调用 `/v1/models` 拉取可用模型，并以多选方式写回 `LLM_{CHANNEL}_MODELS`；拉取失败时保留手动输入作为降级路径。

### 改进

- 🔎 **SerpAPI 正文补抓范围收敛** — 自然搜索结果不再逐条同步抓取网页正文；仅对极少数高位且摘要不足的结果做延迟补抓，优先复用 SerpAPI 已返回的结构化摘要，降低搜索链路尾延迟与慢站点放大风险。
- 🤖 **LLM 接入体验简化** — 面向用户的 AI 模型接入文案统一为"主模型 / Agent 主模型 / 备选模型 / 模型渠道"，不再把 LiteLLM 当作普通用户必学概念，现有 `LITELLM_*` / `LLM_CHANNELS` 配置键保持兼容。
- 🧠 **IntelAgent 新增公司公告搜索与主力资金流工具** — 增加上交所/深交所/cninfo 公告搜索维度与 `get_capital_flow` 工具，修复 Agent 模式下公告和资金流数据经常缺失的问题。
- 📦 **后端股票名称解析优先复用 `stocks.index.json`** — 懒加载缓存前端静态索引，纯后端/缺失静态资源场景静默降级回 `STOCK_NAME_MAP` 与原有数据源回退链路。
- 📊 **TushareFetcher 港股单位适配** — `get_chip_distribution` 对港股直接返回 `None`（港股暂不支持筹码分布）；`_normalize_data` 对港股（`hk_daily`）不再做 A 股手→股、千元→元的缩放，与 Tushare 港股字段语义一致。
- ⏱️ **Agent 超步数错误增加 `AGENT_MAX_STEPS` 调整提示** — 帮助用户自助排查步数限制问题。
- ⚙️ **GitHub Actions 分析任务超时支持 `vars` 配置** — `daily_analysis.yml` 任务超时从 repository variables 读取，无需修改代码即可调整运行超时上限（fixes #1014）。

### 修复

- 📣 **大盘复盘链路接入 `REPORT_LANGUAGE`** — `REPORT_LANGUAGE=en` 时，A 股/合并复盘的 Prompt、章节标题、模板兜底文案与通知包装标题统一输出英文，避免英文正文搭配中文标题的混排问题。
- 📈 **EfinanceFetcher 指数开盘价映射兼容**（fixes #1043）— `get_main_indices()` 的开盘价映射改为兼容 `今开 → 开盘 → open`，修复部分 efinance 版本下指数开盘价被读成缺失值的问题。
- 🤖 **AGENT_MAX_STEPS 语义统一**（fixes #1026）— 在 orchestrator 多 Agent 模式下明确为"各子 Agent 步数上限而非硬覆盖"；TechnicalAgent 等高默认值 Agent 会被封顶，低默认值 Agent 保持原值；用户主动调高（>10）时统一覆盖所有子 Agent。修复了用户设置 12 但 TechnicalAgent 仍以默认 6 步运行并报 "Agent exceeded max steps" 的问题。
- 🛡️ **Specialist（Skill）Agent 失败改为优雅降级** — 技能 Agent 失败不再中断整个分析管线，与 intel/risk 保持相同的降级策略。
- 🔧 **MiniMax-M2.7 连接测试修复** — 修复 LLM 通道连接测试在 MiniMax-M2.7 下返回 "Empty response" 的问题；将 `max_tokens` 上限从 8 提升至 256 以容纳思考过程，并添加 `content_blocks` 格式解析逻辑。
- 📊 **移除 `sentiment_score` 范围约束**（fixes #942）— 移除 `HistoryItem` 与 `ReportSummary` 响应 Schema 中 `sentiment_score` 的 `ge=0/le=100` 约束，历史库中存储的超范围值不再触发 Pydantic ValidationError。
- 🖥️ **WebUI 前端资源缺失时发出明确警告** — `webui_frontend.py` 在 `static/index.html` 存在但 `static/assets/` 缺失时发出 warning，避免 CSS/JS 资源缺失导致页面异常变大却无从排查（fixes #944）。
- 🔗 **分析管线可选服务降级初始化** — `StockAnalysisPipeline` 搜索服务与社交舆情服务任一初始化异常时，记录 warning 并以禁用状态继续运行，避免外部依赖抖动阻塞主分析链路。
- 🖥️ **桌面端版本展示统一读取 `package.json`** — 统一读取 `apps/hrs-desktop/package.json`，移除 preload 中硬编码的 `0.1.0`，设置页展示真实桌面端版本；修复版本号显示错误（fixes #1048）。
- 🐋 **港股名称获取失败修复**（fixes #940）— 修复主数据源字段缺失时无法正确回退到备用字段获取港股名称的问题。
- 🔄 **SSE 任务流断开时 `CancelledError` 正确 re-raise**（fixes #967）— 修复 SSE 流中断时异常被静默吞掉导致故障无日志可查的问题。
- 🔄 **Agent SSE 清理阶段后台任务异常正确上报**（fixes #969）— 流结束时后台执行器异常现在正确记录并上报，避免错误无法感知。
- 🔇 **技能加载异常补充 `logger.warning` 日志**（fixes #970）— 在 `ask.py`、`skills/aggregator.py`、`skills/router.py` 的静默 except 块补充日志，确保技能列表为空时有日志可查。
- 🛠️ **SQLite 写入链路原子化**（fixes #878）— `stock_daily(code,date)` 使用批量原子 upsert；文件型 SQLite 连接默认启用 WAL + `busy_timeout` + 有限写入重试；"新增数"改按本次真正插入窗口计算。
- 💰 **多 Agent / 单 Agent 预算护栏语义统一** — 剩余预算低于最小阈值时主动跳过并降级；已完成阶段可构建降级报告时返回 `success=True` 并携带非空内容，否则返回 `success=False`。
- ⚙️ **GitHub Actions `daily_analysis.yml` 补齐 `REPORT_LANGUAGE` 注入**（fixes #1013）— 修复用户在 Secrets/Variables 中配置 `REPORT_LANGUAGE` 后不生效的问题。
- 📊 **任务状态 API 补齐实时价格字段**（fixes #983）— `GET /api/v1/analysis/status/{task_id}` 从数据库回填已完成任务时补齐 `current_price` / `change_pct`，修复首页报告股票名旁不显示实时价格的问题。
- 📅 **非交易日数据返回最近交易日**（fixes #1009）— 修复非交易日（周末/节假日）筹码分布与板块排行返回倒数第二个交易日数据的问题，现在正常返回最近交易日数据。
- 🔍 **A 股资讯搜索恢复中文优先** — `search_stock_news()` 在首个 provider 主要返回英文资讯时继续尝试后续引擎，并将同批结果中的中文资讯排到前面；非美股查询不再默认沿用 Brave 的 `en/US` 区域语言偏好。
- 📨 **飞书群机器人通知支持签名校验** — 飞书通知现在支持 `FEISHU_WEBHOOK_SECRET` / `FEISHU_WEBHOOK_KEYWORD`；Web 设置与文档明确区分 Webhook 推送模式和 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 应用模式，降低误配风险。
- ⚡ **LLM 适配层新增 `RateLimitError` 和 `ContextWindowExceeded` 检测** — 识别并处理速率限制与上下文窗口超出错误，提升分析链路在高负载或长文本场景下的健壮性（fixes #1002）。

### 测试

- 🧪 **TushareFetcher 港股相关单元测试** — 新增 `get_chip_distribution` 筹码分布获取与 `_normalize_data` 港股/A 股/ETF 单位处理的单元测试，覆盖港股特殊路径。

### 文档

- 📘 **DEPLOY.md 补充 UI 元素异常变大排查步骤** — 新增重建 Docker 镜像或手动执行 `npm run build` 的排查指南；`deploy-webui-cloud.md` 同步更新。
- 📨 **飞书 Webhook 配置说明补全** — 强调 `FEISHU_WEBHOOK_URL` 是群通知必填项、签名校验须两端同时启用或关闭、`FEISHU_APP_SECRET` 仅用于应用/Stream Bot 模式；`.env.example` 补充内联注释；同步英文指南。
- 🤝 **FAQ 补充 Ollama 连接失败排障条目（Q12c）** — 覆盖服务未启动、URL 配置错误、模型前缀缺失、模型未下载、远程防火墙等 5 个检查点（fixes #854）。
- 🌉 **README 补充长桥数据源使用说明** — 中/英/繁 README 明确长桥"首选 / 兜底 / 未配置不调用"边界；`docs/` 内相对路径链接修复；`LONGBRIDGE_PRINT_QUOTE_PACKAGES` 配置与代码及 `.env.example` 对齐。
- 🐋 **Docker 安装场景版本说明** — 补充最小化文档，明确 Docker 安装场景下应以 Git tag / 镜像 tag 判断版本（fixes #1091）。

## [3.12.0] - 2026-04-01

### 发布亮点

- 📊 **回测页新增"次日验证"视图** — 可按股票与日期范围查看 AI 预测 vs 次日实际涨跌，复用历史分析与 1 日回测结果，快速验证分析准确率。
- 🔧 **LLM 接入体验简化** — 用户侧文案统一收口为"主模型 / 备选模型 / 模型渠道"，不再把 LiteLLM 当作普通用户必学概念，现有配置键保持兼容。
- 🐳 **Docker / WebUI 运行时稳态补强** — 修复系统设置保存后配置不生效、启动早期日志缺失、预构建静态资源复用等问题，降低容器化部署的运维摩擦。
- 🔒 **安全与并发稳定性同步增强** — Discord 入站 Webhook 补齐 Ed25519 验签，修复并发执行时共享状态未加锁、单股推送模式通知并发复用等问题。
- 🖥️ **桌面端与定时任务细节打磨** — Windows 安装器支持自选安装目录，内置定时调度器感知运行中 SCHEDULE_TIME 变更，断点续传改按市场时区判断。

### 新功能

- 📊 **回测页新增"次日验证 / 1 日窗口"视图** — 可按股票代码与分析日期范围查看 AI 预测、次日实际涨跌及筛选区间准确率，复用历史分析与 1 日回测结果实现。
- 🏷️ **Web 设置页新增版本信息卡片** — `apps/hrs-web` 现在会在构建时注入前端包版本与构建时间，系统设置页新增只读"版本信息"区块，展示 `WebUI 版本 / 构建标识 / 构建时间`；当 `package.json` 仍为占位版本 `0.0.0` 时，会自动回退为构建标识，方便 Docker 重建后快速确认当前静态资源是否已经生效。
- 🪟 **Windows 桌面安装器支持自选安装目录** — 安装器改为支持在安装向导中自定义安装目录，安装到非默认盘符后仍沿用现有打包态目录逻辑在安装目录旁读写 `.env`、`data/stock_analysis.db` 和 `logs/desktop.log`，同时保留 `win-unpacked` 免安装分发方式。安装器仅支持当前用户安装、已禁用管理员提权（`allowElevation: false`），并通过 NSIS `.onVerifyInstDir` 阻止选择系统保护目录。

### 改进

- 🔎 **SerpAPI 正文补抓范围收敛** — 自然搜索结果不再逐条同步抓取网页正文；现在仅对极少数高位且摘要明显不足的结果，在更短超时预算内做延迟补抓，并优先复用 SerpAPI 已返回的结构化摘要，降低搜索链路尾延迟与慢站点放大风险。
- 🤖 **LLM 接入体验简化** — 面向用户的 AI 模型接入文案已统一收口为"主模型 / Agent 主模型 / 备选模型 / 模型渠道 / 高级模型路由配置"；Web 设置页、配置元数据、校验提示与中英文文档不再把 LiteLLM 当作普通用户默认必学概念，现有 `LITELLM_*` / `LLM_CHANNELS` 配置键仍保持兼容。

### 修复

- 🚀 **启动早期失败时暴露真实根因** — `python main.py` 现在通过 stderr 暴露真实根因，bootstrap 阶段不再向硬编码 `logs/` 目录写入文件日志，文件日志推迟到 `config.log_dir` 可用后创建，避免健康启动在非预期路径残留日志文件。
- 🐳 **Docker WebUI 运行时优先复用预构建静态资源** — `prepare_webui_frontend_assets()` 现在会先检查镜像内已有的 `static/index.html` 是否可直接复用；当容器运行时不包含 `apps/hrs-web` 源码目录且未安装 `npm` 时，也不会误报"未找到前端项目，无法自动构建"，从而恢复 Docker 部署后的 WebUI 打开能力。
- 🐳 **Docker WebUI 系统设置保存后配置生效** — Docker 场景下 WebUI 保存 `STOCK_LIST`、`SCHEDULE_ENABLED`、`SCHEDULE_TIME`、`SCHEDULE_RUN_IMMEDIATELY`、`RUN_IMMEDIATELY` 后，`Config` 会优先读取持久化 `.env` 中的新值，避免被容器创建时注入的旧环境变量覆盖。
- 📈 **市场复盘 LLM max_tokens 提升** — 市场复盘生成链路将 LLM `max_tokens` 从 `2048` 提升到 `8192`，降低长复盘输出因 `MAX_TOKENS` 提前截断导致内容未完成的概率。
- ⏰ **内置定时调度器感知 SCHEDULE_TIME 运行时变更** — 调度器现在会在运行中感知 WebUI 保存后的 `SCHEDULE_TIME` 变化，并在下一轮检查时重绑 daily job。
- 🪟 **Windows Release 渠道编辑器保留 MiniMax 模型前缀** — 渠道模式下填写 `minimax/<模型名>` 时，后端归一化与 Web 设置页运行时模型列表都会保留该值原样，不再误改写成 `openai/minimax/<模型名>`。
- 🤖 **Discord 入站 Webhook 补齐 Ed25519 验签** — `DiscordPlatform` 现在会基于 `X-Signature-Ed25519`、`X-Signature-Timestamp` 和原始请求体校验 Discord Interaction 签名；缺失签名头、公钥格式非法或签名不匹配时直接拒绝请求，同时对 timestamp 做 ±5 分钟时效窗口校验以防御重放攻击。
- ⚙️ **STOCK_GROUP_N / EMAIL_GROUP_N 配置关系明确化** — 明确与 `STOCK_LIST` 的关系，并在配置校验中对超出 `STOCK_LIST` 的邮件分组给出 warning。
- 🗓️ **断点续传改按市场时区和交易日历判断**（fixes #880）— 股票数据存在性检查不再直接使用服务器自然日，而是按 A 股 / 港股 / 美股各自市场时区解析"最新可复用交易日"。
- 📨 **单股推送模式不再并发复用共享通知实例** — `StockAnalysisPipeline.run()` 现在会保留个股分析并发，但把 `SINGLE_STOCK_NOTIFY=true` 下的即时通知挪到结果收集侧串行发送。
- 🔇 **实时行情降级提示收口为单次告警** — 分析主流程获取股票名称时不再提前触发一次实时行情查询，只有在全部数据源都不可用时才提示已降级为历史收盘价继续分析。
- 🔍 **A 股中文资讯搜索恢复中文优先** — `search_stock_news()` 现在会在首个 provider 主要返回英文资讯时继续尝试后续引擎，并将同批结果中的中文资讯排到前面。
- 🔒 **并发执行时共享状态补齐统一加锁** — 修复并发执行时共享状态缺少统一加锁的问题，避免多线程场景下的数据竞争。

### 测试

- 🧪 **补充设置页版本信息回归测试** — 新增 Web 设置页版本信息渲染断言，并覆盖占位版本 `0.0.0` 自动回退为构建标识的逻辑。
- 🧪 **UI 治理与关键路径回归补强** — 补充 `SidebarNav`、`ChatPage`、`BacktestPage` 等组件测试，并新增 UI governance 守卫，持续防止交互元素重新引入原生 `title` 属性或旧 `input-terminal` 样式回流。同步更新 smoke / markdown drawer 相关验证，覆盖主题升级后的关键主链路。

## [3.11.0] - 2026-03-27

### 发布亮点

- 🎨 **Web 工作台完成一轮 UI 统一与双主题升级** — 首页、问股、回测、持仓和设置页进一步收口到统一设计 token、输入表面和状态表达；新增完整浅色主题，并支持浅色 / 深色一键切换与持久化保存。
- 🤖 **Bot / Agent 能力重新补回主分支** — 恢复 `/history`、`/strategies`、`/research` 等命令，`/ask` 继续支持多股对比与组合视角；Deep Research、事件监控与 schedule 轮询链路重新接回主线能力。
- 🔒 **安全性与运行稳态同步补强** — 修复 `X-Forwarded-For` 限流绕过风险，恢复 LiteLLM 官方 PyPI 安装路径，Tushare 初始化不再依赖本地 SDK，降低 Docker、桌面打包和环境重建时的脆弱点。
- 🖥️ **日常使用细节继续打磨** — 修复首页港股自动补全提交、登录页首屏主题闪烁、历史长股票名重叠，以及 Telegram Markdown 解析失败时整条通知发送中断等问题。

### 新功能

- 🎨 **全新浅色主题与双主题切换上线** — Web 工作台新增完整浅色主题，并支持在侧边栏中一键切换浅色 / 深色模式；主题选择会持久化保存，刷新页面后仍保持当前偏好。此次升级不是局部配色微调，而是对卡片层级、边界对比、输入表面、状态提示和页面背景做了一整套 light theme 重绘。
- 🤖 **补回主分支缺失的 Agent / Bot 能力** — `#648` / `#649` 已重新补回 `main`：Bot 恢复 `/history`、`/strategies`、`/research`，`/ask` 保留多股对比与组合视角；Deep Research 与 Event Monitor 的配置重新在 Web 设置页可见并可编辑，schedule 模式也重新接入事件告警轮询。

### 改进

- 🖥️ **核心页面统一到同一套工作台视觉语言** — `Home / Chat / Backtest / Portfolio / Settings` 进一步收口到共享设计 token、`input-surface` 输入体系、空态/错误态表达和抽屉遮罩语义，减少页面之间的视觉割裂与局部私有样式漂移。
- 💬 **问股交互可达性与反馈增强** — 问股页补强了会话导出、通知发送、消息复制、历史删除与追问上下文提示；AI 回复操作不再过度依赖 hover，触屏设备和小屏场景下也能直接触达关键按钮。
- 📊 **回测与持仓页表面和状态表达继续标准化** — 回测页筛选控件、布尔状态、结果表格与汇总卡片统一到共享输入/状态原语；持仓页的导入反馈、汇率刷新提示、空态与警示信息进一步归口到共享组件，减少页面级重复实现。
- 🧭 **导航与页面壳层协同优化** — 侧边栏主题切换、问股完成角标、移动端抽屉遮罩和主内容滚动契约进一步统一，首页、问股和回测在桌面端与移动端的切页体验更稳定。

### 测试

- 🧪 **UI 治理与关键路径回归补强** — 补充 `SidebarNav`、`ChatPage`、`BacktestPage` 等组件测试，并新增 UI governance 守卫，持续防止交互元素重新引入原生 `title` 属性或旧 `input-terminal` 样式回流。同步更新 smoke / markdown drawer 相关验证，覆盖主题升级后的关键主链路。

### 修复

- 🌗 **Web 首屏默认主题预设为深色** — `apps/hrs-web/index.html` 现在会在 React 挂载前读取本地保存的主题偏好；若没有已保存值，则立即给 `<html>` 预设 `dark` 并同步 `color-scheme`，避免首页和登录页首屏先闪出浅色主题。
- 🔐 **登录页独立主题层收口** — 登录页输入框、标签、切换按钮和按钮文案现在使用独立的 `--login-*` 视觉 token，不再继承全局浅/深主题文字色；即使浏览器缓存了浅色主题，登录页仍保持稳定的深色视觉与青色密码输入表现，避免密码圆点和文案落成黑色。
- 🖥️ **首页港股代码输入修复** — Web 首页分析输入框现在可正确接受港股代码与自动完成选中的港股项，补齐 `00700.HK` / `HK00700` 等格式识别，避免提交时误报“请输入有效的股票代码或股票名称”。

- 🔒 **认证限流 X-Forwarded-For 取值修复（CWE-345）**（#841 / #842）— `get_client_ip()` 从取 `X-Forwarded-For` 最左值改为最右值，防止攻击者通过伪造首部旋转限流桶绕过暴力破解保护；仅影响 `TRUST_X_FORWARDED_FOR=true` 且单层可信反向代理的部署场景，多级代理环境需按部署文档评估配置。
- 📦 **恢复 LiteLLM 官方 PyPI 安装并锁定安全上限** — `requirements.txt` 重新使用 `pip install litellm` 的官方 PyPI 安装路径，并在保留历史最低要求 `>=1.80.10` 的同时增加 `<1.82.7` 的安全上限，避免误装已被移除的 `1.82.7` / `1.82.8` 风险版本；Windows 桌面打包脚本也同步回退到标准 `pip install -r requirements.txt` 链路，减少特殊下载分支带来的维护成本。
- 📨 **Telegram Markdown 解析失败回退纯文本**（fixes #850）— `src/notification_sender/telegram_sender.py` 现在会在 Telegram 返回 `HTTP 400` 且包含 `can't parse entities` / Markdown 解析错误时，自动去掉 `parse_mode` 后重试纯文本发送，避免 `*ST` 等正文内容直接导致整条通知失败。
- 🔢 **A 股同码实时行情保留交易所提示**（fixes #852）— `DataFetcherManager` 与 `TushareFetcher` 现在会保留 `SZ000001` / `000001.SZ` 这类显式沪深提示，旧版 Tushare 实时行情降级分支不再把深市 `000001` 误判成 `sh000001` 上证指数。
- 🎯 **多 Agent 次优买点不再盲目复制理想买点**（fixes #851）— 当多智能体结果缺少独立 `secondary_buy` 时，仪表盘现在优先展示 `N/A` 而不是把 fallback 值硬拷贝成与 `ideal_buy` 完全相同，减少误导性的双买点展示。
- 🧩 **Tushare 初始化不再强依赖本地 SDK 包** — `TushareFetcher` 现在直接使用内置 HTTP client 访问 Tushare Pro，不再在启动阶段先 `import tushare` 才能初始化；修复了 Docker、桌面打包或环境重建后因缺少 `tushare` 包而提前报 `No module named 'tushare'` 的问题，并补充对应回归测试。
- ⚙️ **`daily_analysis` 工作流补齐 `DEEPSEEK_API_KEY` 映射** — GitHub Actions 每日分析工作流现在会正确透传 `DEEPSEEK_API_KEY`，避免云端任务配置了密钥却在运行时拿不到对应环境变量。
- 🖥️ **历史列表过长股票名称截断与悬停展示**（fixes #815）— 历史列表中过长的股票名称, 现在会按字符类型自动截断（英文15/中文8/混合10字符），默认显示截断结果，悬停时展示完整名称；解决 1920x1080 分辨率下股票名称与右侧状态标签文字重叠的问题。新增 `stockName.ts` 工具函数并补充对应测试。

### 文档

- 🧾 **README 捐赠入口更新为小红书二维码** — README 及中英文说明中的赞助入口更新为小红书二维码素材，保持展示口径一致。

## [3.10.1] - 2026-03-24

### 新功能

- 🔔 **Web 端分析推送通知开关**（#808）— 首页分析按钮旁新增「推送通知」复选框，默认勾选；取消勾选时本次分析不发送 Telegram/企业微信等推送。API `POST /api/v1/analysis/analyze` 新增 `notify` 字段（`bool`，默认 `true`），不传时行为与修改前一致，Bot 和定时任务不受影响。

### 改进

- 🖥️ **问股 / 回测页面布局与壳层协同优化** — 统一 Chat / Backtest 页面容器、共享 UI 状态和跟随问答交互路径，移除部分硬编码高度限制，让导航框架内的填充与滚动行为更连贯。
- 🎨 **全局视觉与共享组件继续收敛** — Light theme 引入动态 HSL 阴影体系，统一侧边栏激活态、告警组件对比度和聊天气泡样式，并把部分零散内联样式收口为语义化 CSS 变量，提升一致性与可维护性。

### 修复

- 🖼️ **系统设置智能导入文件选择恢复** — 修复了“系统设置 > 基础设置 > 智能导入”模块中 “选择图片 / 选择文件” 两个按钮点击无响应的问题。
- 🖥️ **移动端滚动与交互层级修复** — 解决主题切换菜单在移动端被主内容遮挡的 z-index 冲突，并恢复首页长报告场景下的正常纵向滚动，不影响其他页面现有滚动行为。
- 🧾 **Markdown 纯文本复制清洗增强** — 改进纯文本导出算法，复制分析报告时会更稳定地清除表格分隔符等 Markdown 痕迹，提升分享和归档内容的纯净度。
- 🧠 **Trading philosophy injection 覆盖 legacy + Agent 全链路**（#810）— `GeminiAnalyzer`、单 Agent 模式和 skill-aware Prompt 现在共享同一套策略注入状态；只有隐式回落到内置默认 `bull_trend` 时才保留旧的趋势型提示，显式策略选择或自定义默认 skill 不再被偷偷叠加 `MA5>MA10>MA20` 多头基线。
- 🛠️ **后端 CI 依赖安装链路稳态化**（#835）— 拆分 backend gate 阶段、为依赖安装增加重试，并把 CI 用的 `litellm` 安装来源调整为更稳定的 GitHub 源，降低依赖解析抖动导致的 backend gate 偶发失败。
- 🪟 **Windows 桌面发版构建恢复 LiteLLM 安装兼容性** — `scripts/build-backend.ps1` 现在会先过滤 `requirements.txt` 中的 LiteLLM GitHub 源包，再下载对应 tag 的 zipball 到本地移除上游可选 `enterprise/` 目录后安装，绕过 Windows runner 上 Poetry 构建 wheel 时把目录误当文件打包导致的失败；同时补上 `pip install` 退出码检查，避免依赖安装失败后只在后续 `python-multipart` 校验阶段才暴露成次生报错。

### 测试

- 🧪 **问股 / 回测 / 智能导入回归覆盖补齐** — 同步更新 E2E 冒烟期望，补充 `DashboardStateBlock`、Chat 页、智能导入文件选择与相关交互回归断言，确保近期 UI 调整后的关键路径仍可稳定通过。

## [3.10.0] - 2026-03-24

### 发布亮点

- 🔎 **自动补全与索引工具扩展到三市场** — 补全索引生成链路现在同时覆盖 A 股、港股、美股，配套新增 Tushare 股票列表抓取工具与更完整的静态索引数据，让首页搜索入口从“能用”走向“更全、更稳”。
- 🖥️ **Dashboard 与报告查看体验继续收口** — 首页 Dashboard 面板、状态边界、字体层级和完整报告表格密度完成一轮统一；报告详情也补齐了 Markdown/纯文本复制与更可靠的按钮交互，减少历史报告查看与分享时的摩擦。
- 🤖 **Agent skill 与市场语义边界更清晰** — skill bundle、默认策略、回测汇总语义和兼容接口进一步收敛；同时分析 Prompt 不再默认写死 A 股上下文，美股和港股分析也能按各自市场规则生成更贴切的内容。
- ⏰ **定时与桌面配置能力更贴近真实使用场景** — 桌面端支持 `.env` 导入导出；`python main.py --schedule --stocks ...` 也不再把启动时股票快照错误带入后续计划执行，定时任务会跟随最新保存的 `STOCK_LIST`。
### 新功能

- 💾 **桌面端 `.env` 备份/恢复入口**（#754）— 桌面模式下的系统设置页新增 `导出 .env` / `导入 .env` 按钮，可直接备份当前已保存配置，或把备份文件中的键值合并恢复到当前桌面端 `.env`；导入沿用现有 `config_version` 冲突保护与运行时重载链路，不改变现有桌面端便携模式路径。
- 📊 **Tushare 股票列表获取工具** — 新增 `scripts/fetch_tushare_stock_list.py`，支持从 Tushare Pro 获取 A股、港股、美股列表信息并保存为 CSV，配有分页读取、智能限流、错误处理和进度提示；新增对应使用文档 `docs/TUSHARE_STOCK_LIST_GUIDE.md`。
- 🔎 **索引生成脚本多市场支持** — `generate_index_from_csv.py` 重构为支持 Tushare 和 AkShare 双数据源，同时覆盖 A股、港股、美股三个市场；新增按市场分类的别名映射（A股、港股常见别名，美股常用股票英文缩写）；添加 `--source` 参数切换数据源、`--test` 参数验证模式；严格过滤美股 DUMMY 记录。
- 🔎 **索引生成脚本增强** — `generate_stock_index.py` 新增 `--test`/`-t` 测试模式和 `--verbose`/`-v` 详细输出模式，添加市场分布统计，优化 JSON 输出格式。
- 📋 **首页完整报告支持双模式复制** — 历史报告详情头部新增“复制 Markdown 源码”和“复制纯文本”工具按钮；前者保留原始 Markdown 结构，后者去除常见 Markdown 格式符号，方便分享、归档和跨报告比对。复制按钮文案会跟随 `REPORT_LANGUAGE` 保持中英文一致，避免英文报告页出现中文固定文案。
- 🧩 **个股分析页补齐关联板块展示**（#669）— A 股分析写路径现在会把 `belong_boards` 一次性写入 `fundamental_context` / `fundamental_snapshot`，结构化报告详情同步新增 `belong_boards` 与 `sector_rankings` 字段，Web 个股分析页首屏可直接展示所属板块及其是否命中当日板块涨跌榜；无数据时保持 fail-open 隐藏，不影响现有分析主流程。

### 改进

- 🖥️ **Dashboard 面板统一化（PR7-2）** — 新增 `DashboardPanelHeader` 和 `DashboardStateBlock` 作为历史、报告、资讯、任务和透明度等面板的通用组件；统一了各面板标题层级、加载/空态/错误态和 CSS 变量 token。
- 🖥️ **HomePage 状态边界收口（PR7-2）** — 引入 `useHomeDashboardState` hook，集中 `stockPoolStore` 状态选取逻辑，移除 `HomePage` 中重复的本地状态派生和回调定义。
- 🧭 **Agent skill 统一到单一配置语义** — Multi-Agent runtime、API、Web chat 和配置元数据统一围绕 `skill` 概念收敛；`/api/v1/agent/skills` 成为主发现入口，`AGENT_SKILL_*` 成为主配置面，内置 skill 元数据也开始声明默认启用、排序优先级、market regime tag 等信息，减少默认策略散落在代码里的隐式耦合。
- 🔎 **自动补全索引数据更新** — 重新生成 `stocks.index.json`，涵盖 A股、港股、美股三个市场，提升自动补全覆盖率。
- 🧾 **Dashboard 字体与完整报告表格密度微调** — 收敛首页侧栏、空状态、历史操作区的字体层级，并将完整 Markdown 报告表格 `th/td` 的内边距调整到更紧凑的 4-6px 区间，让信息密度与现有 Dashboard 视觉节奏更一致。

### 修复

- ⏰ **定时模式不再锁定启动时 CLI 股票快照** — `python main.py --schedule --stocks ...` 现在不会让后续计划执行沿用启动时的旧股票列表；定时任务每次触发前都会重新读取最新保存的 `STOCK_LIST`，确保 WebUI 或 `.env` 更新后的自选股配置能参与后续推送。
- 🌍 **LLM Prompt 按股票市场动态注入上下文** — 分析链路不再把市场规则写死成 A 股；系统 Prompt 会根据股票代码识别 A 股、港股或美股，并注入对应的角色描述与交易规则提示，减少跨市场分析出现口径错位或结论失真的问题。
- 🔎 **美股自动补全复用 ticker 去重** — `generate_index_from_csv.py` 在导入 Tushare `us_basic` CSV 时会先按 `ts_code` 折叠复用的美股 ticker，优先保留更可能仍在使用的记录，避免 `stocks.index.json` 出现重复 `canonicalCode` 后让 Web 自动补全展示历史名称或提交歧义代码。
- 🧾 **Web 报告详情复制交互稳定性修复**（#749）— `ReportDetails` 中“原始分析结果 / 分析快照”的复制按钮补齐可点击层级，避免被下方 JSON 内容覆盖；两个面板的复制提示也改为各自独立，不再出现复制一个后两个按钮同时显示“已复制”的误导反馈。
- 📊 **Agent skill 回测与兼容接口语义收敛** — `get_skill_backtest_summary` 现在要求显式传入 `skill_id`，缺失时返回明确校验提示；仓库尚未持久化真实 skill 级汇总时会返回明确的 unsupported/info 响应，并保留 `normalized` 与 `*_pct` 兼容字段，避免沿用 overall 指标误导 Agent 或用户。
- 🔧 **Skill 默认选择与兼容层行为加固** — `allowed-tools` 会继续仅作为 `SKILL.md` bundle 元数据保留，不再泄露到运行时工具选择；`/api/v1/agent/strategies` 恢复旧 payload 形状；显式传入 `skills: []` 时会清空陈旧上下文；当用户明确选择策略 skill 时不再偷偷叠加默认 bull-trend，而在 `AGENT_SKILLS` 为空时则统一只回落到单一主默认 skill。

### 测试

- 🧪 **Dashboard 组件测试覆盖率扩展（PR7-2）** — 新增 `ReportNews` 和 `TaskPanel` 测试；对 `HistoryList`、`ReportDetails`、`HomePage`、`useDashboardLifecycle` 和 `stockPoolStore` 增强了断言覆盖，包括删除回退、移动端抽屉和任务生命周期等场景。
- 🧪 **多市场索引生成测试补齐** — 新增 `tests/test_generate_index_from_csv.py`，覆盖 Tushare/AkShare 双数据源解析、多市场判断、美股 DUMMY 过滤与重复 ticker 去重等核心路径。
- 🧪 **关联板块写入与 API 契约回归** — 新增 `tests/test_pipeline_related_boards.py`，并补充分析历史与分析接口契约测试，确保 `belong_boards` / `sector_rankings` 只做增量扩展且保持 fail-open。
- 🧪 **定时模式股票列表语义回归测试** — 新增 `tests/test_main_schedule_mode.py`，覆盖定时模式忽略启动时 `--stocks` 快照、单次运行仍保留 CLI 股票覆盖的边界场景。

### 文档

- 📘 **新增 Tushare 股票列表工具文档** — 新增 `docs/TUSHARE_STOCK_LIST_GUIDE.md`，说明股票列表抓取工具的使用方法、数据格式和常见问题。
- 🌍 **补齐定时模式与关联板块的双语说明** — `docs/full-guide.md` / `docs/full-guide_EN.md` 现在明确说明 scheduled mode 会在每次执行前重新读取 `STOCK_LIST`，并同步补充个股关联板块展示能力说明，减少配置预期偏差。
- 🧭 **调整 Agent 术语兼容文案** — README、双语文档、设置页与问股界面继续以“策略”作为用户入口主称呼，同时补充 `skill` 作为内部统一命名，降低迁移期理解成本。

## [3.9.0] - 2026-03-20

### 发布亮点

- 🤖 **模型链路与报告语言更灵活** — Agent 现在可以通过 `AGENT_LITELLM_MODEL` 独立选择模型链路，普通分析与 Agent 报告也可通过 `REPORT_LANGUAGE=zh|en` 输出统一语言，减少“英文内容 + 中文壳子”这类混排问题，并允许团队分别权衡主分析与 Agent 的成本、速度和能力。
- 🔎 **首页分析体验完成一轮闭环优化** — 首页新增 A 股自动补全，支持代码、中文名、拼音和别名检索；同时 Dashboard 状态收口到统一 store，历史、报告、新闻与 Markdown 抽屉的交互更稳定，“Ask AI” 追问也会优先携带当前报告上下文。
- 💬 **通知与检索能力继续外扩** — 新增 Slack 一等通知渠道；SearXNG 在未配置自建实例时可以自动发现公共实例并按受控轮询降级；Tavily 时效新闻链路修复后，严格时效过滤不再错误丢光有效结果。
- 💼 **持仓与市场复盘链路更稳** — A 股 market review 可选接入 TickFlow 强化指数与涨跌统计；持仓账本写入改为串行化以缩小并发超卖窗口；汇率刷新入口和禁用态提示也更加清晰，减少用户误判。

### 新功能

- 🔎 **Web 股票自动补全 MVP** — 首页分析输入框新增本地索引驱动的自动补全，支持股票代码、中文名、拼音和别名匹配；选中候选后会提交 canonical code，并透传 `stock_name`、`original_query`、`selection_source` 到分析请求、任务状态和 SSE 事件；索引加载失败时自动退回旧输入模式，不阻断原有提交流程。同步补充了静态索引加载器、索引生成脚本和前后端契约测试。分阶段进行开发，第一阶段仅支持 A 股。
- 💬 **Slack 一等通知渠道** — 新增 Slack 原生通知支持，同时支持 Bot Token 和 Incoming Webhook 两种接入方式；同时配置时优先使用 Bot API，确保文本与图片发送到同一频道；Bot Token 模式支持图片上传（raw body POST，不使用 multipart）；新增 `SLACK_BOT_TOKEN`、`SLACK_CHANNEL_ID`、`SLACK_WEBHOOK_URL` 配置项，GitHub Actions 工作流同步补齐对应 Secrets 传递。
- 🌍 **报告输出语言可配置**（Issue #758）— 新增 `REPORT_LANGUAGE=zh|en`，默认 `zh`；语言设置会同步注入普通分析与 Agent Prompt，并覆盖 Markdown/Jinja 模板、通知 fallback、历史/API `report_language` 元数据及 Web 报告页固定文案，避免“英文内容 + 中文壳子”的混合输出。
- 🚀 **Agent 与普通分析模型解耦**（Issue #692）— 新增 `AGENT_LITELLM_MODEL`（留空继承 `LITELLM_MODEL`，无前缀按 `openai/<model>` 归一）；Agent 执行链路与 `/api/v1/agent/models` 的 `is_primary/is_fallback` 标记改为基于 Agent 实际模型链路；系统配置与启动期校验补齐 `AGENT_LITELLM_MODEL` 的 `unknown_model/missing_runtime_source` 检查；Web 设置页新增 Agent 主模型选择并与渠道模式运行时配置同步。
- 🔎 **SearXNG 公共实例自动发现与受控轮询**（#752）— 新增 `SEARXNG_PUBLIC_INSTANCES_ENABLED`，在未配置 `SEARXNG_BASE_URLS` 时默认从 `searx.space` 拉取公共实例列表，并按受控轮询顺序选择实例；同次请求内遇到超时、连接错误、HTTP 非 200 或无效 JSON 会自动切换到下一个实例。已配置自建实例的用户保持原有优先级与语义不变；`daily_analysis` GitHub Actions 工作流也已支持显式透传该开关并在启动日志中展示当前状态。
- 📈 **TickFlow market review enhancement** (#632) — 新增可选 `TICKFLOW_API_KEY`；配置后，A 股大盘复盘的主要指数行情优先尝试 TickFlow；若当前 TickFlow 套餐支持标的池查询，市场涨跌统计也会优先尝试 TickFlow。失败或权限不足时立即回退到现有 `AkShare / Tushare / efinance` 链路；板块涨跌榜回退顺序保持不变。接入层同时适配了真实 SDK 契约：主指数查询按单次请求上限分批拉取，并将 TickFlow 返回的比例型 `change_pct` / `amplitude` 统一转换为项目内部的百分比口径。

### 改进

- **Dashboard state slice and workspace closure** — moved Home / Dashboard state into `stockPoolStore`, consolidated history selection, report loading, task syncing, polling refresh, and markdown drawer handling under a single state slice.
- **Dashboard panel standardization** — kept the current dashboard layout contract stable while unifying history, report, news, and markdown presentation with shared tokens, standardized states, and bounded in-panel scrolling for the history list.
- **Dashboard-to-chat follow-up bridge** — routed “Ask AI” follow-ups through report-context hydration instead of direct cross-page state coupling, while keeping chat sends usable when enriched history context is still loading.
- 💼 **持仓账本并发写入串行化**（#742）— 持仓源事件写入/删除现在会在 SQLite 下先获取串行化写锁，减少并发卖出把超售流水写入账本的窗口；直接持仓写接口在锁竞争时返回 `409 portfolio_busy`，CSV 导入保持逐条提交并把 busy 计入 `failed_count`。
- 💱 **持仓页汇率手动刷新入口补齐**（#748）— Web `/portfolio` 页面现在会在“汇率状态”卡片中展示“刷新汇率”按钮，直接调用现有 `POST /api/v1/portfolio/fx/refresh` 接口；刷新后会仅重载快照与风险数据，并以内联摘要反馈“已更新 / 仍 stale / 刷新失败”的结果，减少用户对 `fxStale` 长时间停留的误解。

### 修复

- 🔎 **Web 自动补全 Enter 提交语义修正** — 股票自动补全在搜索命中候选时不再默认高亮第一项；候选列表展开但用户尚未用方向键或鼠标明确选中时，按 Enter 会继续提交原始输入，避免手动输入被第一条候选静默覆盖。
- 🌍 **补齐 `REPORT_LANGUAGE` 启动解析与历史展示本地化边界** — `Config` 在启动时继续遵循“真实环境变量优先、`.env` 兜底”的既有语义，并在两者冲突时输出显式告警，减少 `REPORT_LANGUAGE` 来源不清带来的误判；同时 `/api/v1/history/{id}` 英文详情响应会同步本地化 `sentiment_label`，历史 Markdown 也会正确识别英文 `bias_status` 的风险等级 emoji，避免出现 `乐观` 或 `🚨Safe` 这类中英混排/误报展示。
- 📰 **Tavily 时效新闻检索发布时间映射修复**（#782）— Tavily 在股票新闻和严格时效的情报维度中现在会显式使用 `topic="news"`，并兼容 `published_date` / `publishedDate` 两种发布时间字段；修复了 Tavily 明明返回结果却在后续硬过滤阶段被全部记为 `drop_unknown` 丢弃的问题，同时将机构分析、业绩预期、行业分析等分析型维度恢复为宽源搜索，不再被统一压缩成新闻模式。
- 💱 **持仓页汇率刷新禁用语义修正**（#772）— 当 `PORTFOLIO_FX_UPDATE_ENABLED=false` 时，`POST /api/v1/portfolio/fx/refresh` 现在会返回显式 `refresh_enabled=false` 与 `disabled_reason`，Web `/portfolio` 页面会明确提示“汇率在线刷新已被禁用”，不再误报“当前范围无可刷新的汇率对”。
- 🤖 **Agent timeout and config hardening** — `AGENT_ORCHESTRATOR_TIMEOUT_S` now also protects the legacy single-agent ReAct loop, parallel tool batches stop waiting once the remaining budget is exhausted, and invalid numeric `.env` values fall back to safe defaults with warnings instead of crashing startup.
- 🌐 **CORS wildcard + credentials compatibility** — `CORS_ALLOW_ALL=true` no longer combines `allow_origins=["*"]` with credentialed requests, avoiding browser-side cross-origin failures in demo/development setups.
- 🧭 **Unavailable Agent settings hidden from Web UI** — Deep Research / Event Monitor controls are now treated as compatibility-only metadata in the current branch and are removed from the Settings page to avoid exposing non-functional toggles.

### 文档

- 新增 Ollama 本地模型配置说明，同步更新 `README.md` 与 `docs/README_EN.md`（Fixes #690）
- 完善 Ollama 配置说明：`docs/full-guide.md` / `docs/full-guide_EN.md` 环境变量表与 Note 补充 `OLLAMA_API_BASE`，避免英文用户误以为 Ollama 不能作为独立配置入口；合并重复的 `OLLAMA_API_BASE` 条目为单一条目
- 明确文档同步治理边界：补充 `README.md`、专题文档、双语文档与交付说明之间的默认同步规则，减少后续文档漂移

## [3.8.0] - 2026-03-17

### 发布亮点

- 🎨 **Web 界面完成一轮骨架升级** — 新的 App Shell、侧边导航、主题能力、登录与系统设置流程已经串成统一体验，桌面端加载背景也完成对齐。
- 📈 **分析上下文继续补强** — 美股新增社交舆情情报，A 股补齐财报与分红结构化上下文，Tushare 新接入筹码分布和行业板块涨跌数据。
- 🔒 **运行稳定性与配置兼容性提升** — 退出登录会立即让旧会话失效，定时启动兼容旧配置，运行中的 `MAX_WORKERS` 调整和新闻时效窗口反馈更清晰。
- 💼 **持仓纠错链路更完整** — 超售会被前置拦截，错误交易/资金流水/公司行为可以直接删除回滚，便于修复脏数据。

### 新功能

- 📱 **美股社交舆情情报** — 新增 Reddit / X / Polymarket 社交媒体情绪数据源，为美股分析提供实时社交热度、情绪评分和提及量等补充指标；完全可选，仅在配置 `SOCIAL_SENTIMENT_API_KEY` 后对美股生效。
- 📊 **A 股财报与分红结构化增强**（Issue #710）— `fundamental_context.earnings.data` 新增 `financial_report` 与 `dividend` 字段；分红统一按“仅现金分红、税前口径”计算，并补充 `ttm_cash_dividend_per_share` 与 `ttm_dividend_yield_pct`；分析/历史 API 的 `details` 追加 `financial_report`、`dividend_metrics` 可选字段，保持 fail-open 与向后兼容。
- 🔍 **接入 Tushare 筹码与行业板块接口** — 新增筹码分布、行业板块涨跌数据获取能力，并统一纳入配置化数据源优先级；默认按上海时间区分盘中/盘后交易日取数，优先使用 Tushare 同花顺接口，必要时降级到东财。
- 🧱 **Web UI 基础骨架升级** — 重建共享设计令牌与通用组件，新增 App Shell、Theme Provider、侧边导航，并同步调整 Electron 加载背景，为 Web / Desktop 的统一体验打底。
- 🔐 **登录与系统设置流程重做** — 重构 Login、Settings 与 Auth 管理流程，补上显式的认证 setup-state 处理，并让 Web 端与运行时认证配置 API 行为对齐。
- 🧪 **前端回归与冒烟覆盖补强** — 新增并扩展登录、首页、聊天、移动端 Shell、设置页、回测入口等关键路径的组件测试与 Playwright smoke coverage。

### 变更

- 🧭 **页面接入新 Shell 布局契约** — Home、Chat、Settings、Backtest 已统一接入新的页面容器、抽屉和滚动约定，降低 UI 迁移期间的页面行为不一致。
- 💾 **设置页状态同步更稳** — 优化草稿保留、直接保存同步与冲突处理，减少模块级保存后前后端配置状态不一致的问题。
- 🎭 **登录页视觉基线回归** — 登录页恢复到既有 `006` 分支的视觉基线，同时保留新的认证状态逻辑和统一表单交互模型。
- 🏛️ **AI 协作治理资产加固** — 收敛并加强 `AGENTS.md`、`CLAUDE.md`、Copilot 指令和校验脚本的一致性约束，降低治理资产长期漂移风险。

### Added

- **Web UI foundation refresh** — rebuilt shared design tokens and common primitives, introduced the app shell, theme provider, sidebar navigation, and Electron loading background alignment for the upgraded desktop/web experience
- **Settings and auth workflow overhaul** — rebuilt the Login, Settings, and Auth management flows, added explicit auth setup-state handling, and aligned the Web UI with the runtime auth configuration APIs
- **UI regression coverage and smoke checks** — expanded targeted frontend tests and added Playwright smoke coverage for login, home, chat, mobile shell, settings, and backtest entry flows

### Changed

- **Shell-driven page integration** — aligned Home, Chat, Settings, and Backtest with the new shell layout contract so routing, drawer behavior, and page-level scrolling are consistent during the UI migration
- **Settings state consistency** — refined draft preservation, direct-save synchronization, and conflict handling so module-level saves no longer leave the page out of sync with backend config state
- **Login visual baseline** — restored the login page visual treatment to the established `006` branch baseline while keeping the newer auth-state logic and unified form interaction model

### 修复

- ⏰ **定时启动立即执行兼容旧配置**（Issue #726）— `SCHEDULE_RUN_IMMEDIATELY` 未设置时会回退读取 `RUN_IMMEDIATELY`，修复升级后旧 `.env` 在定时模式下的兼容性问题；同时澄清 `.env.example` / README 中两个配置项的适用范围，并注明 Outlook / Exchange 强制 OAuth2 暂不支持。
- 🧵 **运行期 `MAX_WORKERS` 配置生效与可解释性增强**（#633）— 修复异步分析队列未按 `MAX_WORKERS` 同步的问题；新增任务队列并发 in-place 同步机制（空闲即时生效、繁忙延后），并在设置保存反馈与运行日志中明确输出 `profile/max/effective`，减少“参数未生效”误解。
- 🔐 **退出登录立即失效现有会话** — `POST /api/v1/auth/logout` 现在会轮换 session secret，避免旧 cookie 在退出后仍可继续访问受保护接口；同浏览器标签页和并发页面会被同步登出。认证开启时，该接口也不再属于匿名白名单，未登录请求会返回 `401`，避免匿名请求触发全局 session 失效。
- 🧮 **Tushare 板块/筹码调用限流与跨日缓存修复** — 新增的 `trade_cal`、行业板块排行、筹码分布链路统一接入 `_check_rate_limit()`；交易日历缓存改为按自然日刷新，避免服务跨天运行后继续沿用旧交易日判断取数日期。
- 💼 **持仓超售拦截与错误流水恢复**（#718）— `POST /api/v1/portfolio/trades` 现在会在写入前校验可卖数量，超售返回 `409 portfolio_oversell`；持仓页新增交易 / 资金流水 / 公司行为删除能力，删除后会同步失效仓位缓存与未来快照，便于从错误流水中直接恢复。
- 📧 **邮件中文发件人名编码**（#708）— 邮件通知现在会对包含中文的 `EMAIL_SENDER_NAME` 自动做 RFC 2047 编码，并在异常路径补充 SMTP 连接清理，修复 GitHub Actions / QQ SMTP 下 `'ascii' codec can't encode characters` 导致的发送失败。
- 🐛 **港股 Agent 实时行情去重与快速路由** — 统一 `HK01810` / `1810.HK` / `01810` 等港股代码归一规则；港股实时行情改为直接走单次 `akshare_hk` 路径，避免按 A 股 source priority 重复触发同一失败接口；Agent 运行期对显式 `retriable=false` 的工具失败增加短路缓存，减少同轮分析中的重复失败调用。
- 📰 **新闻时效硬过滤与策略分窗**（#697）— 新增 `NEWS_STRATEGY_PROFILE`（`ultra_short/short/medium/long`）并与 `NEWS_MAX_AGE_DAYS` 统一计算有效窗口；搜索结果在返回后执行发布时间硬过滤（时间未知剔除、超窗剔除、未来仅容忍 1 天），并在历史 fallback 链路追加相同约束，避免旧闻再次进入“最新动态/风险警报”。

### 文档

- ☁️ **新增云服务器 Web 界面部署与访问教程**（Fixes #686）— 补充从云端部署到外部访问的落地说明，降低远程自托管门槛。
- 🌍 **补齐英文文档索引与协作文档** — 新增英文文档索引、贡献指南、Bot 命令文档，并补充中英双语 issue / PR 模板，方便中英文协作与外部贡献者理解项目入口。
- 🏷️ **本地化 README 补充 Trendshift badge** — 在多语言 README 中同步补上新版能力入口标识，减少中英文说明面不一致。

## [3.7.0] - 2026-03-15

### 新功能

- 💼 **持仓管理 P0 全功能上线**（#677，对应 Issue #627）
  - **核心账本与快照闭环**：新增账户、交易、现金流水、企业行为、持仓缓存、每日快照等核心数据模型与 API 端点；支持 FIFO / AVG 双成本法回放；同日事件顺序固定为 `现金 → 企业行为 → 交易`；持仓快照写入采用原子事务。
  - **券商 CSV 导入**：支持华泰 / 中信 / 招商首批适配，含列名别名兼容；两阶段接口（解析预览 + 确认提交）；`trade_uid` 优先、key-field hash 兜底的幂等去重；前导零股票代码完整保留。
  - **组合风险报告**：集中度风险（Top Positions + A 股板块口径）、历史回撤监控（支持回填缺失快照）、止损接近预警；多币种统一换算 CNY 口径；汲取失败时回退最近成功汇率并标记 stale。
  - **Web 持仓页**（`/portfolio`）：组合总览、持仓明细、集中度饼图、风险摘要、全组合 / 单账户切换；手工录入交易 / 资金流水 / 企业行为；内嵌账户创建入口；CSV 解析 + 提交闭环与券商选择器。
  - **Agent 持仓工具**：新增 `get_portfolio_snapshot` 数据工具，默认紧凑摘要，可选持仓明细与风险数据。
  - **事件查询 API**：新增 `GET /portfolio/trades`、`GET /portfolio/cash-ledger`、`GET /portfolio/corporate-actions`，支持日期过滤与分页。
  - **可扩展 Parser Registry**：应用级共享注册，支持运行时注册新券商；新增 `GET /portfolio/imports/csv/brokers` 发现接口。

- 🎨 **前端设计系统与原子组件库**（#662）
  - 引入渐进式双主题架构（HSL 变量化设计令牌），清理历史 Legacy CSS；重构 Button / Card / Badge / Collapsible / Input / Select 等 20+ 核心组件；新增 `clsx` + `tailwind-merge` 类名合并工具；提升历史记录、LLM 配置等页面可读性。

- ⚡ **分析 API 异步契约与启动优化**（#656）
  - 规范 `POST /api/v1/analysis/analyze` 异步请求的返回契约；优化服务启动辅助逻辑；修复前端报告类型联合定义与后端响应对齐问题。

### 修复

- 🔔 **Discord 环境变量向后兼容**（#659）：运行时新增 `DISCORD_CHANNEL_ID` → `DISCORD_MAIN_CHANNEL_ID` 的 fallback 读取；历史配置用户无需修改即可恢复 Discord Bot 通知；全部相关文档与 `.env.example` 对齐。
- 🔧 **GitHub Actions Node 24 升级**（#665）：将所有 GitHub 官方 actions 升级至 Node 24 兼容版本，消除 CI 日志中的 Node.js 20 deprecation warning（影响 2026-06-02 强制升级窗口）。
- 📅 **持仓页默认日期本地化**：手工录入表单默认日期改用本地时间（`getFullYear/Month/Date`），修复 UTC-N 时区用户在当天晚间出现日期偏移的问题。
- 🔁 **CSV 导入去重逻辑加固**：dedup hash 纳入行序号作为区分因子，确保同字段合法分笔成交不被误折叠；同时在 `trade_uid` 存在时也持久化 hash，防止混合来源重复写入。

### 变更

- `POST /api/v1/portfolio/trades` 在同账户内 `trade_uid` 冲突时返回 `409`。
- 持仓风险响应新增 `sector_concentration` 字段（增量扩展），原有 `concentration` 字段保持不变。
- 分析 API `analyze` 接口异步行为契约文档化；前端报告类型联合更新。

### 测试

- 新增持仓核心服务测试（FIFO / AVG 部分卖出、同日事件顺序、重复 `trade_uid` 返回 409、快照 API 契约）。
- 新增 CSV 导入幂等性、合法分笔成交不误去重、去重边界、风险阈值边界、汇率降级行为测试。
- 新增 Agent `get_portfolio_snapshot` 工具调用测试。
- 新增分析 API 异步契约回归测试。

## [3.6.0] - 2026-03-14

### Added
- 📊 **Web UI Design System** — implemented dual-theme architecture and terminal-inspired atomic UI components
- 📊 **UI Components Refactoring** — integrated `clsx` and `tailwind-merge` for robust class composition across Web UI

- 🗑️ **History batch deletion** — Web UI now supports multi-selection and batch deletion of analysis history; added `POST /api/v1/history/batch-delete` endpoint and `ConfirmDialog` component.
- 🔐 **Auth settings API** — new `POST /api/v1/auth/settings` endpoint to enable or disable Web authentication at runtime and set the initial admin password when needed
- openclaw Skill 集成指南 — 新增 [docs/openclaw-skill-integration.md](openclaw-skill-integration.md)，说明如何通过 openclaw Skill 调用 HRS API
- ⚙️ **LLM channel protocol/test UX** — `.env` and Web settings now share the same channel shape (`LLM_CHANNELS` + `LLM_<NAME>_PROTOCOL/BASE_URL/API_KEY/MODELS/ENABLED`); settings page adds per-channel connection testing, primary/fallback/vision model selection, and protocol-aware model prefixing
- 🤖 **Agent architecture Phase 0+1** — shared protocols (`AgentContext`, `AgentOpinion`, `StageResult`), extracted `run_agent_loop()` runner, `AGENT_ARCH` switch (`single`/`multi`), config registry entries
- 🔍 **Bot NL routing** — two-layer natural-language routing: cheap regex pre-filter (stock codes + finance keywords) → lightweight LLM intent parsing; controlled by `AGENT_NL_ROUTING=true`; supports multi-stock and strategy extraction
- 💬 **`/ask` multi-stock analysis** — comma or `vs` separated codes (max 5), parallel thread execution with 150s timeout (preserves partial results), Markdown comparison summary table at top
- 📋 **`/history` command** — per-user session isolation via `{platform}_{user_id}:{scope}` format (colon delimiter prevents prefix collision); lists both `/chat` and `/ask` sessions; view detail or clear
- 📊 **`/strategies` command** — lists available strategy YAML files grouped by category (趋势/形态/反转/框架) with ✅/⬜ activation status
- 🔧 **Backtest summary tools** — `get_strategy_backtest_summary` and `get_stock_backtest_summary` registered as read-only Agent tools
- ⚙️ **Agent auto-detection** — `is_agent_available()` auto-detects from `LITELLM_MODEL`; explicit `AGENT_MODE=true/false` takes full precedence
- 🏗️ **Multi-Agent orchestrator (Phase 2)** — `AgentOrchestrator` with 4 modes (`quick`/`standard`/`full`/`strategy`); drop-in replacement for `AgentExecutor` via `AGENT_ARCH=multi`; `BaseAgent` ABC with tool subset filtering, cached data injection, and structured `AgentOpinion` output
- 🧩 **Specialised agents (Phase 2-4)** — `TechnicalAgent` (8 tools, trend/MA/MACD/volume/pattern analysis), `IntelAgent` (news & sentiment, risk flag propagation), `DecisionAgent` (synthesis into Decision Dashboard JSON), `RiskAgent` (7 risk categories, two-level severity with soft/hard override)
- 📈 **Strategy system (Phase 3)** — `StrategyAgent` (per-strategy evaluation from YAML skills), `StrategyRouter` (rule-based regime detection → strategy selection), `StrategyAggregator` (weighted consensus with backtest performance factor)
- 🔬 **Deep Research agent (Phase 5)** — `ResearchAgent` with 3-phase approach (decompose → research sub-questions → synthesise report); token budget tracking; new `/research` bot command with aliases (`/深研`, `/deepsearch`)
- 🧠 **Memory & calibration (Phase 6)** — `AgentMemory` with prediction accuracy tracking, confidence calibration (activates after minimum sample threshold), strategy auto-weighting based on historical win rate
- 📊 **Portfolio Agent (Phase 7)** — `PortfolioAgent` for multi-stock portfolio analysis (position sizing, sector concentration, correlation risk, cross-market linkage, rebalance suggestions)
- 🔔 **Event-driven alerts (Phase 7)** — `EventMonitor` with `PriceAlert`, `VolumeAlert`, `SentimentAlert` rules; async checking, callback notifications, serializable persistence
- ⚙️ **New config entries** — `AGENT_ORCHESTRATOR_MODE`, `AGENT_RISK_OVERRIDE`, `AGENT_DEEP_RESEARCH_BUDGET`, `AGENT_MEMORY_ENABLED`, `AGENT_STRATEGY_AUTOWEIGHT`, `AGENT_STRATEGY_ROUTING` — all registered in `config.py` + `config_registry.py` (WebUI-configurable)

### Changed
- 🔐 **Auth password state semantics** — stored password existence is now tracked independently from auth enablement; when auth is disabled, `/api/v1/auth/status` returns `passwordSet=false` while preserving the saved password for future re-enable
- 🔐 **Auth settings re-enable hardening** — re-enabling auth with a stored password now requires `currentPassword`, and failed session creation rolls back the auth toggle to avoid lockout
- ♻️ **AgentExecutor refactored** — `_run_loop` delegates to shared `runner.run_agent_loop()`; removed duplicated serialization/parsing/thinking-label code
- ♻️ **Unified agent switch** — Bot, API, and Pipeline all use `config.is_agent_available()` instead of divergent `config.agent_mode` checks
- 📖 **README.md** — expanded Bot commands section (ask/chat/strategies/history), added NL routing note, updated agent mode description
- 📖 **.env.example** — added `AGENT_ARCH` and `AGENT_NL_ROUTING` configuration documentation
- 🔌 **Analysis API async contract** — `POST /api/v1/analysis/analyze` now documents distinct async `202` payloads for single-stock vs batch requests, and `report_type=full` is treated consistently with the existing full-report behavior

### Fixed
- 🐛 **Analysis API blank-code guardrails** — `POST /api/v1/analysis/analyze` now drops whitespace-only entries before batch enqueue and returns `400` when no valid stock code remains
- 🐛 **Bare `/api` SPA fallback** — unknown API paths now return JSON `404` consistently for both `/api/...` and the exact `/api` path
- 🎮 **Discord channel env compatibility** — runtime now accepts legacy `DISCORD_CHANNEL_ID` as a fallback for `DISCORD_MAIN_CHANNEL_ID`, and the docs/examples now use the same variable name as the actual workflow/config implementation
- 🐛 **Session secret rotation on Windows** — use atomic replace so auth toggles invalidate existing sessions even when `.session_secret` already exists
- 🐛 **Auth toggle atomicity** — persist `ADMIN_AUTH_ENABLED` before rotating session secret; on rotation failure, roll back to the previous auth state
- 🔧 **LLM runtime selection guardrails** — YAML 模式下渠道编辑器不再覆盖 `LITELLM_MODEL` / fallback / Vision；系统配置校验补上全部渠道禁用后的运行时来源检查，并修复 `vertexai/...` 这类协议别名模型被重复加前缀的问题
- 🐛 **Multi-stock `/ask` follow-up regressions** — portfolio overlay now shares the same timeout budget as the per-stock phase and is skipped on timeout instead of blocking the bot reply; `/history` now stores the readable per-stock summary instead of raw dashboard JSON; condensed multi-stock output now renders numeric `sniper_points` values
- 🐛 **Decision dashboard enum compatibility** — multi-agent `DecisionAgent` now keeps `decision_type` within the legacy `buy|hold|sell` contract and normalizes stray `strong_*` outputs before risk override, pipeline conversion, and downstream统计/通知汇总
- 🛟 **Multi-Agent partial-result fallback** — `IntelAgent` now caches parsed intel for downstream reuse, shared JSON parsing tolerates lightly malformed model output, and the orchestrator preserves/synthesizes a minimal dashboard on timeout or mid-pipeline parse failure instead of always collapsing to `50/观望/未知`
- 🐛 **Shared LiteLLM routing restored** — bot NL intent parsing and `ResearchAgent` planning/synthesis now reuse the same LiteLLM adapter / Router / fallback / `api_base` injection path as the main Agent flow, so `LLM_CHANNELS` / `LITELLM_CONFIG` / OpenAI-compatible deployments behave consistently
- 🐛 **Bot chat session backward compatibility** — `/chat` now keeps using the legacy `{platform}_{user_id}` session id when old history already exists, and `/history` can still list / view / clear those pre-migration sessions alongside the new `{platform}_{user_id}:chat` format
- 🐛 **EventMonitor unsupported rule rejection** — config validation/runtime loading now reject or skip alert types the monitor cannot actually evaluate yet, so schedule mode no longer silently accepts permanent no-op rules
- 🐛 **P0 基本面聚合稳定性修复** (#614) — 修复 `get_stock_info` 板块语义回归（新增 `belong_boards` 并保留 `boards` 兼容别名）、引入基本面上下文精简返回以控制 token、为基本面缓存增加最大条目淘汰，并补齐 ETF 总体状态聚合与 NaN 板块字段过滤，保证 fail-open 与最小入侵。
- 🔧 **GitHub Actions 搜索引擎环境变量补充** — 工作流新增 `MINIMAX_API_KEYS`、`BRAVE_API_KEYS`、`SEARXNG_BASE_URLS` 环境变量映射，使 GitHub Actions 用户可配置 MiniMax、Brave、SearXNG 搜索服务（此前 v3.5.0 已添加 provider 实现但缺少工作流配置）
- 🤖 **Multi-Agent runtime consistency** — `AGENT_MAX_STEPS` now propagates to each orchestrated sub-agent; added cooperative `AGENT_ORCHESTRATOR_TIMEOUT_S` budget to stop overlong pipelines before they cascade further
- 🔌 **Multi-Agent feature wiring** — `AGENT_RISK_OVERRIDE` now actively downgrades final dashboards on hard risk findings; `AGENT_MEMORY_ENABLED` now injects recent analysis memory + confidence calibration into specialised agents; multi-stock `/ask` now runs `PortfolioAgent` to add portfolio-level allocation and concentration guidance
- 🔔 **EventMonitor runtime wiring** — schedule mode can now load alert rules from `AGENT_EVENT_ALERT_RULES_JSON`, poll them at `AGENT_EVENT_MONITOR_INTERVAL_MINUTES`, and send triggered alerts through the existing notification service
- 🛠️ **Follow-up stability fixes** — multi-stock `/ask` now falls back to usable text output when dashboard JSON parsing fails; EventMonitor skips semantically invalid rules instead of aborting schedule startup; background alert polling now runs independently of the main scheduled analysis loop
- 🧪 **Multi-Agent regression coverage** — added orchestrator execution tests for `run()`, `chat()`, critical-stage failure, graceful degradation, and timeout handling
- 🧹 **PortfolioAgent cleanup** — `post_process()` now reuses shared JSON parsing and removed stale unused imports
- 🚦 **Bot async dispatch** — `CommandDispatcher` now exposes `dispatch_async()`; NL intent parsing and default command execution are offloaded from the event loop, DingTalk stream awaits async handlers directly, and Feishu stream processing is moved off the SDK callback thread
- 🌐 **Async webhook handler** — new `handle_webhook_async()` function in `bot/handler.py` for use from async contexts (e.g. FastAPI); calls `dispatch_async()` directly without thread bridging
- 🧵 **Feishu stream ThreadPoolExecutor** — replaced unbounded per-message `Thread` spawning with a capped `ThreadPoolExecutor(max_workers=8)` to prevent thread explosion under message bursts
- 🔒 **EventMonitor safety** — `_check_volume()` now safely handles `get_daily_data` returning `None` (no tuple-unpacking crash); `on_trigger` callbacks support both sync and async callables via `asyncio.to_thread`/`await`
- 🧹 **ResearchAgent dedup** — `_filtered_registry()` now delegates to `BaseAgent._filtered_registry()` instead of duplicating the filtering logic
- 🧹 **Bot trailing whitespace cleanup** — removed W291/W293 whitespace issues across `bot/handler.py`, `bot/dispatcher.py`, `bot/commands/base.py`, `bot/platforms/feishu_stream.py`, `bot/platforms/dingtalk_stream.py`
- 🐛 **Dispatcher `_parse_intent_via_llm` safety** — replaced fragile `'raw' in dir()` with `'raw' in locals()` for undefined-variable guard in `JSONDecodeError` handler
- 🐛 **筹码结构 LLM 未填写时兜底补全** (#589) — DeepSeek 等模型未正确填写 `chip_structure` 时，自动用数据源已获取的筹码数据补全，保证各模型展示一致；普通分析与 Agent 模式均生效
- 🐛 **历史报告狙击点位显示原始文本** (#452) — 历史详情页现优先展示 `raw_result.dashboard.battle_plan.sniper_points` 中的原始字符串，避免 `analysis_history` 数值列把区间、说明文字或复杂点位压缩成单个数字；保留原有数值列作为回退
- 🐛 **Session prefix collision** — user ID `123` could see sessions of user `1234` via `startswith`; fixed with colon delimiter in session_id format
- 🐛 **NL pre-filter false positives** — `re.IGNORECASE` caused `[A-Z]{2,5}` to match common English words like "hello"; removed global flag, use inline `(?i:...)` only for English finance keywords
- 🐛 **Dotted ticker in strategy args** — `_get_strategy_args()` didn't recognize `BRK.B` as a stock code, leaving it in strategy text; now accepts `TICKER.CLASS` format
- ⏱️ **efinance 长调用挂起修复** (#660) — 为所有 efinance API 调用引入 `_ef_call_with_timeout()` 包装（默认 30 秒，可通过 `EFINANCE_CALL_TIMEOUT` 配置）；使用 `executor.shutdown(wait=False)` 确保超时后不再阻塞主线程，彻底消除 81 分钟挂起问题
- 🛡️ **类型安全内容完整性检查** (#660) — `check_content_integrity()` 现在将非字符串类型的 `operation_advice` / `analysis_summary` 视为缺失字段，避免下游 `get_emoji()` 因 `dict.strip()` 崩溃
- 📄 **报告保存与通知解耦** (#660) — `_save_local_report()` 不再依赖 `send_notification` 标志触发，`--no-notify` 模式下本地报告照常保存
- 🔄 **operation_advice 字典归一化** (#660) — Pipeline 和 BacktestEngine 现在将 LLM 返回的 `dict` 格式 `operation_advice` 通过 `decision_type`（不区分大小写）映射为标准字符串，防止因模型输出格式变化导致崩溃
- 🛡️ **runner.py usage None 防护** (#660) — `response.usage` 为 `None` 时不再抛出 `AttributeError`，回退为 0 token 计数
- 📋 **orchestrator 静默失败改为日志警告** (#660) — `IntelAgent` / `RiskAgent` 阶段失败现在记录 `WARNING` 而非静默跳过，便于诊断

### Notes
- ⚠️ **Multi-worker auth toggles** — runtime auth updates are process-local; multi-worker deployments must restart/roll workers to keep auth state consistent

## [3.5.0] - 2026-03-12

### Added
- 📊 **Web UI full report drawer** (Fixes #214) — history page adds "Full Report" button to display the complete Markdown analysis report in a side drawer; new `GET /api/v1/history/{record_id}/markdown` endpoint
- 📊 **LLM cost tracking** — all LLM calls (analysis, agent, market review) recorded in `llm_usage` table; new `GET /api/v1/usage/summary?period=today|month|all` endpoint returns aggregated token usage by call type and model
- 🔍 **SearXNG search provider** (Fixes #550) — quota-free self-hosted search fallback; priority: Bocha > Tavily > Brave > SerpAPI > MiniMax > SearXNG
- 🔍 **MiniMax web search provider** — `MiniMaxSearchProvider` with circuit breaker (3 failures → 300s cooldown) and dual time-filtering; configured via `MINIMAX_API_KEYS`
- 🤖 **Agent models discovery API** — `GET /api/v1/agent/models` returns available model deployments (primary/fallback/source/api_base) for Web UI model selector
- 🤖 **Agent chat export & send** (#495) — export conversation to .md file; send to configured notification channels; new `POST /api/v1/agent/chat/send`
- 🤖 **Agent background execution** (#495) — analysis continues when switching pages; badge notification on completion; auto-cancel in-progress stream on session switch
- 📝 **Report Engine P0** — Pydantic schema validation for LLM JSON; Jinja2 templates (markdown/wechat/brief) with legacy fallback; content integrity checks with retry; brief mode (`REPORT_TYPE=brief`); history signal comparison
- 📦 **Smart import** — multi-source import from image/CSV/Excel/clipboard; Vision LLM extracts code+name+confidence; name→code resolver (local map + pinyin + AkShare); confidence-tiered confirmation
- ⚙️ **GitHub Actions LiteLLM config** — workflow supports `LITELLM_CONFIG`/`LITELLM_CONFIG_YAML` for flexible AI provider configuration
- ⚙️ **Config engine refactor & system API** (#602) — unified config registry, validation and API exposure
- 📖 **LLM configuration guide** — new `docs/LLM_CONFIG_GUIDE.md` covering 3-tier config, quick start, Vision/Agent/troubleshooting

### Fixed
- 🐛 **analyze_trend always reports No historical data** (#600) — now fetches from DB/DataFetcher instead of broken `get_analysis_context`
- 🐛 **Chip structure fallback when LLM omits it** (#589) — auto-fills from data source chip data for consistent display across models
- 🐛 **History sniper points show raw text** (#452) — prioritizes original strings over compressed numeric values
- 🐛 **GitHub Actions ENABLE_CHIP_DISTRIBUTION configurable** (#617) — no longer hardcoded, supports vars/secrets override
- 🐛 **`.env` save preserves comments and blank lines** — Web settings no longer destroys `.env` formatting
- 🐛 **Agent model discovery fixes** — legacy mode includes LiteLLM-native providers; source detection aligned with runtime; fallback deployments no longer expanded per-key
- 🐛 **Stooq US stock previous close semantics** — no longer misuses open price as previous close
- 🐛 **Stock name prefetch regression** — prioritizes local `STOCK_NAME_MAP` before remote queries
- 🐛 **AkShare limit-up/down calculation** (#555) — fixed market analysis statistics
- 🐛 **AkShare Tencent source field index & ETF quote mapping** (#579)
- 🐛 **Pytdx stock name cache pagination** (#573) — prevents cache overflow
- 🐛 **PushPlus oversized report chunking** (#489) — auto-segments long content
- 🐛 **Agent chat cancel & switch** (#495) — cancel no longer misreports as failure; fast switch no longer overwrites stream state
- 🐛 **MiniMax search status in `/status` command** (#587)
- 🐛 **config_registry duplicate BOCHA_API_KEYS** — removed duplicate dict entry that silently overwrote config

### Changed
- 🔎 **Fetcher failure observability** — logs record start/success/failure with elapsed time, failover transitions; Efinance/Akshare include upstream endpoint and classified failure categories
- ♻️ **Data source resilience & cleanup** (#602) — fallback chain optimization
- ♻️ **Image extract API response extension** — new `items` field (code/name/confidence); `codes` preserved for backward compatibility
- ♻️ **Import parse error messages** — specific failure reasons for Excel/CSV; improved logging with file type and size

### Docs
- 📖 LLM config guide refactored for clarity (#583)
- 📖 `image-extract-prompt.md` with full prompt documentation
- 📖 AkShare fallback cache TTL documentation
## [3.4.10] - 2026-03-07

### Fixed
- 🐛 **EfinanceFetcher ETF OHLCV data** (#541, #527) — switch `_fetch_etf_data` from `ef.fund.get_quote_history` (NAV-only, no OHLCV, no `beg`/`end` params) to `ef.stock.get_quote_history`; ETFs now return proper open/high/low/close/volume/amount instead of zeros; remove obsolete NAV column mappings from `_normalize_data`
- 🐛 **tiktoken 0.12.0 `Unknown encoding cl100k_base`** (#537) — pin `tiktoken>=0.8.0,<0.12.0` in requirements.txt to avoid plugin-registration regression introduced in 0.12.0
- 🐛 **Web UI API error classification** (#540) — frontend no longer treats every HTTP 400 as the same "server/network" failure; now distinguishes Agent disabled / missing params / model-tool incompatibility / upstream LLM errors / local connection failures
- 🐛 **北交所代码识别失败** (#491, #533) — 8/4/92 开头的 6 位代码现正确识别为北交所；Tushare/Akshare/Yfinance 等数据源支持 .BJ 或 bj 前缀；Baostock/Pytdx 对北交所代码显式切换数据源；避免误判上海 B 股 900xxx
- 🐛 **狙击点位解析错误** (#488, #532) — 理想买入/二次买入等字段在无「元」字时误提取括号内技术指标数字；现先截去第一个括号后内容再提取

### Added
- **Markdown-to-image for dashboard report** (#455, #535) — 个股日报汇总支持 markdown 转图片推送（Telegram、WeChat、Custom、Email），与大盘复盘行为一致
- **markdown-to-file engine** (#455) — `MD2IMG_ENGINE=markdown-to-file` 可选，对 emoji 支持更好，需 `npm i -g markdown-to-file`
- **PREFETCH_REALTIME_QUOTES** (#455) — 设为 `false` 可禁用实时行情预取，避免 efinance/akshare_em 全市场拉取
- **Stock name prefetch** (#455) — 分析前预取股票名称，减少报告中「股票xxxxx」占位符
- 📊 **分析报告模型标记** (#528, #534) — 在分析报告 meta、报告末尾、推送内容中展示 `model_used`（完整 LLM 模型名）；Agent 多轮调用时记录并展示每轮实际使用的模型（支持 fallback 切换）

### Changed
- **Enhanced markdown-to-image failure warning** (#455) — 转图失败时提示具体依赖（wkhtmltopdf 或 m2f）
- **WeChat-only image routing optimization** (#455) — 仅配置企业微信图片时，不再对完整报告做冗余转图，避免误导性失败日志
- **Stock name prefetch lightweight mode** (#455) — 名称预取阶段跳过 realtime quote 查询，减少额外网络开销

## [3.4.9] - 2026-03-06

### Added
- 🧠 **Structured config validation** — `ConfigIssue` dataclass and `validate_structured()` with severity-aware logging; `CONFIG_VALIDATE_MODE=strict` aborts startup on errors
- 🖼️ **Vision model config** — `VISION_MODEL` and `VISION_PROVIDER_PRIORITY` for image stock extraction; provider fallback (Gemini → Anthropic → OpenAI → DeepSeek) when primary fails
- 🚀 **CLI init wizard** — `python -m HRS init` 3-step interactive bootstrap (model → data source → notification), 9 provider presets, incremental merge by default
- 🔧 **Multi-channel LLM support** with visual channel editor (#494)

### Changed
- ♻️ **Vision extraction** — migrated from gemini-3 hardcode to `litellm.completion()` with configurable model and provider fallback; `OPENAI_VISION_MODEL` deprecated in favor of `VISION_MODEL`
- ♻️ **Market analyzer** — uses `Analyzer.generate_text()` for LLM calls; fixes bypass and Anthropic `AttributeError` when using non-Router path
- ♻️ **Config validation refinements** — test_env output format syncs with `validate_structured` (severity-aware ✓/✗/⚠/·); Vision key warning when `VISION_MODEL` set but no provider API key; market_analyzer test covers `generate_market_review` fallback when `generate_text` returns None
- ⚙️ **Auto-tag workflow defaults to NO tag** — only tags when commit message explicitly contains `#patch`, `#minor`, or `#major`
- ♻️ **Formatter and notification refactor** (#516)

### Fixed
- 🐛 **STOCK_LIST not refreshed on scheduled runs** — `.env` or WebUI changes to `STOCK_LIST` now hot-reload before each scheduled analysis (#529)
- 🐛 **WebUI fails to load with MIME type error** — SPA fallback route now resolves correct `Content-Type` for JS/CSS files (#520)
- 🐛 **AstrBot sender docstring misplaced** — `import time` placed before docstring in `_send_astrbot`, causing it to become dead code
- 🐛 **Telegram Markdown link escaping** — `_convert_to_telegram_markdown` escaped `[]()` characters, breaking all Markdown links in reports
- 🐛 **Duplicate `discord_bot_status` field** in Config dataclass — second declaration silently shadowed the first
- 🧹 **Unused imports** — removed `shutil`/`subprocess` from `main.py`
- 🔧 **Config validation and Vision key check** (#525)

### Docs
- 📝 Clarified GitHub Actions non-trading-day manual run controls (`TRADING_DAY_CHECK_ENABLED` + `force_run`) for Issue #461 / PR #466

## [3.4.8] - 2026-03-02

### Fixed
- 🐛 **Desktop exe crashes on startup with `FileNotFoundError`** — PyInstaller build was missing litellm's JSON data files (e.g. `model_prices_and_context_window_backup.json`). Added `--collect-data litellm` to both Windows and macOS build scripts so the files are correctly bundled in the executable.

### CI
- 🔧 Cache Electron binaries on macOS CI runners to prevent intermittent EOF download failures when fetching `electron-vX.Y.Z-darwin-*.zip` from GitHub CDN
- 🔧 Fix macOS DMG `hdiutil Resource busy` error during desktop packaging

### Docs
- 📝 Clarify non-trading-day manual run controls for GitHub Actions (`TRADING_DAY_CHECK_ENABLED` + `force_run`) (#474)

## [3.4.7] - 2026-02-28

### Added
- 🧠 **CN/US Market Strategy Blueprint System** (#395) — market review prompt injects region-specific strategy blueprints with position sizing and risk trigger recommendations

### Fixed
- 🐛 **`TRADING_DAY_CHECK_ENABLED` env var and `--force-run` for GitHub Actions** (#466)
- 🐛 **Agent pipeline preserved resolved stock names** (#464) — placeholder names no longer leak into reports
- 🐛 **Code cleanup** (#462, Fixes #422)
- 🐛 **WebUI auto-build on startup** (#460)
- 🐛 **ARCH_ARGS unbound variable** (#458)
- 🐛 **Time zone inconsistency & right panel flash** (#439)

### Docs
- 📝 Clarify potential ambiguities in code (#343)
- 📝 ENABLE_EASTMONEY_PATCH guidance for Issue #453 (#456)

## [3.4.0] - 2026-02-27

### Added
- 📡 **LiteLLM Direct Integration + Multi API Key Support** (#454, Fixes #421 #428)
  - Removed native SDKs (google-generativeai, google-genai, anthropic); unified through `litellm>=1.80.10`
  - New config: `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `GEMINI_API_KEYS`, `ANTHROPIC_API_KEYS`, `OPENAI_API_KEYS`
  - Multi-key auto-builds LiteLLM Router (simple-shuffle) with 429 cooldown
  - **Breaking**: `.env` `GEMINI_MODEL` (no prefix) only for fallback; explicit config must include provider prefix

### Changed
- ♻️ **Notification Refactoring** (#435) — extracted 10 sender classes into `src/notification_sender/`

### Fixed
- 🐛 LLM NoneType crash, history API 422, sniper points extraction
- 🐛 Auto-build frontend on WebUI startup — `WEBUI_AUTO_BUILD` env var (default `true`)
- 🐛 Docker explicit project name (#448)
- 🐛 Bocha search SSL retry (#445, #446) — transient errors retry up to 3 times
- 🐛 Gemini google-genai SDK migration (Fixes #440, #444)
- 🐛 Mobile home page scrolling (Fixes #419, #433)
- 🐛 History list scroll reset (#431)
- 🐛 Settings save button false positive (fixes #417, #430)

## [3.3.22] - 2026-02-26

### Added
- 💬 **Chat History Persistence** (Fixes #400, #414) — `/chat` page survives refresh, sidebar session list
- 🎨 Project VI Assets — logo icon set, PSD, vector, banner (#425)
- 🚀 Desktop CI Auto-Release (#426) — Windows + macOS parallel builds

### Fixed
- 🐛 Agent Reasoning 400 & LiteLLM Proxy (fixes #409, #427)
- 🐛 Discord chunked sending (#413) — `DISCORD_MAX_WORDS` config
- 🐛 yfinance shared DataFrame (#412)
- 🐛 sniper_points parsing (#408)
- 🐛 Agent framework category missing (#406)
- 🐛 Date inconsistency & query id (fixes #322, #363)

## [3.3.12] - 2026-02-24

### Added
- 📈 **Intraday Realtime Technical Indicators** (Issue #234, #397) — MA calculated from realtime price, config: `ENABLE_REALTIME_TECHNICAL_INDICATORS`
- 🤖 **Agent Strategy Chat** (#367) — full ReAct pipeline, 11 YAML strategies, SSE streaming, multi-turn chat
- 📢 PushPlus Group Push — `PUSHPLUS_TOPIC` (#402)
- 📅 Trading Day Check (Issue #373, #375) — `TRADING_DAY_CHECK_ENABLED`, `--force-run`

### Fixed
- 🐛 DeepSeek reasoning mode (Issue #379, #386)
- 🐛 Agent news intel persistence (Fixes #396, #405)
- 🐛 Bare except clauses replaced with `except Exception` (#398)
- 🐛 UUID fallback for HTTP non-secure context (fixes #377, #381)
- 🐛 Docker DNS resolution (Fixes #372, #374)
- 🐛 Agent session/strategy bugs — multiple follow-up fixes for #367
- 🐛 yfinance parallel download data filtering

### Changed
- Market review strategy consistency — unified cn/us template
- Agent test assertions updated (`6 -> 11`)


## [3.2.11] - 2026-02-23

### 修复（#patch）
- 🐛 **StockTrendAnalyzer 从未执行** (Issue #357)
  - 根因：`get_analysis_context` 仅返回 2 天数据且无 `raw_data`，pipeline 中 `raw_data in context` 始终为 False
  - 修复：Step 3 直接调用 `get_data_range` 获取 90 日历天（约 60 交易日）历史数据用于趋势分析
  - 改善：趋势分析失败时用 `logger.warning(..., exc_info=True)` 记录完整 traceback

## [3.2.10] - 2026-02-22

### 新增
- ⚙️ 支持 `RUN_IMMEDIATELY` 配置项，设为 `true` 时定时任务触发后立即执行一次分析，无需等待首个定时点

### 修复
- 🐛 修复 Web UI 页面居中问题
- 🐛 修复 Settings 返回 500 错误

## [3.2.9] - 2026-02-22

### 修复
- 🐛 **ETF 分析仅关注指数走势**（Issue #274）
  - 美股/港股 ETF（如 VOO、QQQ）与 A 股 ETF 不再纳入基金公司层面风险（诉讼、声誉等）
  - 搜索维度：ETF/指数专用 risk_check、earnings、industry 查询，避免命中基金管理人新闻
  - AI 提示：指数型标的分析约束，`risk_alerts` 不得出现基金管理人公司经营风险

## [3.2.8] - 2026-02-21

### 修复
- 🐛 **BOT 与 WEB UI 股票代码大小写统一**（Issue #355）
  - BOT `/analyze` 与 WEB UI 触发分析的股票代码统一为大写（如 `aapl` → `AAPL`）
  - 新增 `canonical_stock_code()`，在 BOT、API、Config、CLI、task_queue 入口处规范化
  - 历史记录与任务去重逻辑可正确识别同一股票（大小写不再影响）

## [3.2.7] - 2026-02-20

### 新增
- 🔐 **Web 页面密码验证**（Issue #320, #349）
  - 支持 `ADMIN_AUTH_ENABLED=true` 启用 Web 登录保护
  - 首次访问在网页设置初始密码；支持「系统设置 > 修改密码」和 CLI `python -m src.auth reset_password` 重置

## [3.2.6] - 2026-02-20
### ⚠️ 破坏性变更（Breaking Changes）

- **历史记录 API 变更 (Issue #322)**
  - 路由变更：`GET /api/v1/history/{query_id}` → `GET /api/v1/history/{record_id}`
  - 参数变更：`query_id` (字符串) → `record_id` (整数)
  - 新闻接口变更：`GET /api/v1/history/{query_id}/news` → `GET /api/v1/history/{record_id}/news`
  - 原因：`query_id` 在批量分析时可能重复，无法唯一标识单条历史记录。改用数据库主键 `id` 确保唯一性
  - 影响范围：使用旧版历史详情 API 的所有客户端需同步更新

### 修复
- 修复美股（如 ADBE）技术指标矛盾：akshare 美股复权数据异常，统一美股历史数据源为 YFinance（Issue #311）
- 🐛 **历史记录查询和显示问题 (Issue #322)**
  - 修复历史记录列表查询中日期不一致问题：使用明天作为 endDate，确保包含今天全天的数据
  - 修复服务器 UI 报告选择问题：原因是多条记录共享同一 `query_id`，导致总是显示第一条。现改用 `analysis_history.id` 作为唯一标识
  - 历史详情、新闻接口及前端组件已全面适配 `record_id`
  - 新增后台轮询（每 30s）与页面可见性变更时静默刷新历史列表，确保 CLI 发起的分析完成后前端能及时同步，使用 `silent` 模式避免触发 loading 状态
- 🐛 **美股指数实时行情与日线数据** (Issue #273)
  - 修复 SPX、DJI、IXIC、NDX、VIX、RUT 等美股指数无法获取实时行情的问题
  - 新增 `us_index_mapping` 模块，将用户输入（如 SPX）映射为 Yahoo Finance 符号（如 ^GSPC）
  - 美股指数与美股股票日线数据直接路由至 YfinanceFetcher，避免遍历不支持的数据源
  - 消除重复的美股识别逻辑，统一使用 `is_us_stock_code()` 函数

### 优化
- 🎨 **首页输入栏与 Market Sentiment 布局对齐优化**
  - 股票代码输入框左缘与历史记录 glass-card 框左对齐
  - 分析按钮右缘与 Market Sentiment 外框右对齐
  - Market Sentiment 卡片向下拉伸填满格子，消除与 STRATEGY POINTS 之间的空隙
  - 窄屏时输入栏填满宽度，响应式对齐保持一致

## [3.2.5] - 2026-02-19

### 新增
- 🌍 **大盘复盘可选区域**（Issue #299）
  - 支持 `MARKET_REVIEW_REGION` 环境变量：`cn`（A股）、`us`（美股）、`both`（两者）
  - us 模式使用 SPX/纳斯达克/道指/VIX 等指数；both 模式可同时复盘 A 股与美股
  - 默认 `cn`，保持向后兼容

## [3.2.4] - 2026-02-18

### 修复
- 🐛 **统一美股数据源为 YFinance**（Issue #311）
  - akshare 美股复权数据异常，统一美股历史数据源为 YFinance
  - 修复 ADBE 等美股股票技术指标矛盾问题

## [3.2.3] - 2026-02-18

### 修复
- 🐛 **标普500实时数据缺失**（Issue #273）
  - 修复 SPX、DJI、IXIC、NDX、VIX、RUT 等美股指数无法获取实时行情的问题
  - 新增 `us_index_mapping` 模块，将用户输入（如 SPX）映射为 Yahoo Finance 符号（如 `^GSPC`）
  - 美股指数与美股股票日线数据直接路由至 YfinanceFetcher，避免遍历不支持的数据源

## [3.2.2] - 2026-02-16

### 新增
- 📊 **PE 指标支持**（Issue #296）
  - AI System Prompt 增加 PE 估值关注
- 📰 **新闻时效性筛查**（Issue #296）
  - `NEWS_MAX_AGE_DAYS`：新闻最大时效（天），默认 3，避免使用过时信息
- 📈 **强势趋势股乖离率放宽**（Issue #296）
  - `BIAS_THRESHOLD`：乖离率阈值（%），默认 5.0，可配置
  - 强势趋势股（多头排列且趋势强度 ≥70）自动放宽乖离率到 1.5 倍

## [3.2.1] - 2026-02-16

### 新增
- 🔧 **东财接口补丁可配置开关**
  - 支持 `EFINANCE_PATCH_ENABLED` 环境变量开关东财接口补丁（默认 `true`）
  - 补丁不可用时可降级关闭，避免影响主流程

## [3.2.0] - 2026-02-15

### 新增
- 🔒 **CI 门禁统一（P0）**
  - 新增 `scripts/ci_gate.sh` 作为后端门禁单一入口
  - 主 CI 改为 `backend-gate`、`docker-build`、`web-gate` 三段式
  - CI 触发改为所有 PR，避免 Required Checks 因路径过滤缺失而卡住合并
  - `web-gate` 支持前端路径变更按需触发
  - 新增 `network-smoke` 工作流承载非阻断网络场景回归
- 📦 **发布链路收敛（P0）**
  - `docker-publish` 调整为 tag 主触发，并增加发布前门禁校验
  - 手动发布增加 `release_tag` 输入与 semver/changelog 强校验
  - 发布前新增 Docker smoke（关键模块导入）
- 📝 **PR 模板升级（P0）**
  - 增加背景、范围、验证命令与结果、回滚方案、Issue 关联等必填项
- 🤖 **AI 审查覆盖增强（P0）**
  - `pr-review` 纳入 `.github/workflows/**` 范围
  - 新增 `AI_REVIEW_STRICT` 开关，可选将 AI 审查失败升级为阻断

## [3.1.13] - 2026-02-15

### 新增
- 📊 **仅分析结果摘要**（Issue #262）
  - 支持 `REPORT_SUMMARY_ONLY` 环境变量，设为 `true` 时只推送汇总，不含个股详情
  - 默认 `false`，多股时适合快速浏览

## [3.1.12] - 2026-02-15

### 新增
- 📧 **个股与大盘复盘合并推送**（Issue #190）
  - 支持 `MERGE_EMAIL_NOTIFICATION` 环境变量，设为 `true` 时将个股分析与大盘复盘合并为一次推送
  - 默认 `false`，减少邮件数量、降低被识别为垃圾邮件的风险

## [3.1.11] - 2026-02-15

### 新增
- 🤖 **Anthropic Claude API 支持**（Issue #257）
  - 支持 `ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`、`ANTHROPIC_TEMPERATURE`、`ANTHROPIC_MAX_TOKENS`
  - AI 分析优先级：Gemini > Anthropic > OpenAI
- 📷 **从图片识别股票代码**（Issue #257）
  - 上传自选股截图，通过 Vision LLM 自动提取股票代码
  - API: `POST /api/v1/stocks/extract-from-image`；支持 JPEG/PNG/WebP/GIF，最大 5MB
  - 支持 `OPENAI_VISION_MODEL` 单独配置图片识别模型
- ⚙️ **通达信数据源手动配置**（Issue #257）
  - 支持 `PYTDX_HOST`、`PYTDX_PORT` 或 `PYTDX_SERVERS` 配置自建通达信服务器

## [3.1.10] - 2026-02-15

### 新增
- ⚙️ **立即运行配置**（Issue #332）
  - 支持 `RUN_IMMEDIATELY` 环境变量，`true` 时定时任务启动后立即执行一次
- 🐛 修复 Docker 构建问题

## [3.1.9] - 2026-02-14

### 新增
- 🔌 **东财接口补丁机制**
  - 新增 `patch/eastmoney_patch.py` 修复 efinance 上游接口变更
  - 不影响其他数据源的正常运行

## [3.1.8] - 2026-02-14

### 新增
- 🔐 **Webhook 证书校验开关**（Issue #265）
  - 支持 `WEBHOOK_VERIFY_SSL` 环境变量，可关闭 HTTPS 证书校验以支持自签名证书
  - 默认保持校验，关闭存在 MITM 风险，仅建议在可信内网使用

## [3.1.7] - 2026-02-14

### 修复
- 🐛 修复包导入错误（package import error）

## [3.1.6] - 2026-02-13

### 修复
- 🐛 修复 `news_intel` 中 `query_id` 不一致问题

## [3.1.5] - 2026-02-13

### 新增
- 📷 **Markdown 转图片通知**（Issue #289）
  - 支持 `MARKDOWN_TO_IMAGE_CHANNELS` 配置，对 Telegram、企业微信、自定义 Webhook（Discord）、邮件发送图片格式报告
  - 邮件为内联附件，增强对不支持 HTML 客户端的兼容性
  - 需安装 `wkhtmltopdf` 和 `imgkit`

## [3.1.4] - 2026-02-12

### 新增
- 📧 **股票分组发往不同邮箱**（Issue #268）
  - 支持 `STOCK_GROUP_N` + `EMAIL_GROUP_N` 配置，不同股票组报告发送到对应邮箱
  - 大盘复盘发往所有配置的邮箱

## [3.1.3] - 2026-02-12

### 修复
- 🐛 修复 Docker 内运行时通过页面修改配置报错 `[Errno 16] Device or resource busy` 的问题

## [3.1.2] - 2026-02-11

### 修复
- 🐛 修复 Docker 一致性问题，解决关键批次处理与通知 Bug

## [3.1.1] - 2026-02-11

### 变更
- ♻️ `API_HOST` → `WEBUI_HOST`：Docker Compose 配置项统一

## [3.1.0] - 2026-02-11

### 新增
- 📊 **ETF 支持增强与代码规范化**
  - 统一各数据源 ETF 代码处理逻辑
  - 新增 `canonical_stock_code()` 统一代码格式，确保数据源路由正确

## [3.0.5] - 2026-02-08

### 修复
- 🐛 修复信号 emoji 与建议不一致的问题（复合建议如"卖出/观望"未正确映射）
- 🐛 修复 `*ST` 股票名在微信/Dashboard 中 markdown 转义问题
- 🐛 修复 `idx.amount` 为 None 时大盘复盘 TypeError
- 🐛 修复分析 API 返回 `report=None` 及 ReportStrategy 类型不一致问题
- 🐛 修复 Tushare 返回类型错误（dict → UnifiedRealtimeQuote）及 API 端点指向

### 新增
- 📊 大盘复盘报告注入结构化数据（涨跌统计、指数表格、板块排名）
- 🔍 搜索结果 TTL 缓存（500 条上限，FIFO 淘汰）
- 🔧 Tushare Token 存在时自动注入实时行情优先级
- 📰 新闻摘要截断长度 50→200 字

### 优化
- ⚡ 补充行情字段请求限制为最多 1 次，减少无效请求

## [3.0.4] - 2026-02-07

### 新增
- 📈 **回测引擎** (PR #269)
  - 新增基于历史分析记录的回测系统，支持收益率、胜率、最大回撤等指标评估
  - WebUI 集成回测结果展示

## [3.0.3] - 2026-02-07

### 修复
- 🐛 修复狙击点位数据解析错误问题 (PR #271)

## [3.0.2] - 2026-02-06

### 新增
- ✉️ 可配置邮件发送者名称 (PR #272)
- 🌐 外国股票支持英文关键词搜索

## [3.0.1] - 2026-02-06

### 修复
- 🐛 修复 ETF 实时行情获取、市场数据回退、企业微信消息分块问题
- 🔧 CI 流程简化

## [3.0.0] - 2026-02-06

### 移除
- 🗑️ **移除旧版 WebUI**
  - 删除基于 `http.server.ThreadingHTTPServer` 的旧版 WebUI（`web/` 包）
  - 旧版 WebUI 的功能已完全被 FastAPI（`api/`）+ React 前端替代
  - `--webui` / `--webui-only` 命令行参数标记为弃用，自动重定向到 `--serve` / `--serve-only`
  - `WEBUI_ENABLED` / `WEBUI_HOST` / `WEBUI_PORT` 环境变量保持兼容，自动转发到 FastAPI 服务
  - `webui.py` 保留为兼容入口，启动时直接调用 FastAPI 后端
  - Docker Compose 中移除 `webui` 服务定义，统一使用 `server` 服务

### 变更
- ♻️ **服务层重构**
  - 将 `web/services.py` 中的异步任务服务迁移至 `src/services/task_service.py`
  - Bot 分析命令（`bot/commands/analyze.py`）改为使用 `src.services.task_service`
  - Docker 环境变量 `WEBUI_HOST`/`WEBUI_PORT` 更名为 `API_HOST`/`API_PORT`（旧名仍兼容）

## [2.3.0] - 2026-02-01

### 新增
- 🇺🇸 **增强美股支持** (Issue #153)
  - 实现基于 Akshare 的美股历史数据获取 (`ak.stock_us_daily()`)
  - 实现基于 Yfinance 的美股实时行情获取（优先策略）
  - 增加对不支持数据源（Tushare/Baostock/Pytdx/Efinance）的美股代码过滤和快速降级

### 修复
- 🐛 修复 AMD 等美股代码被误识别为 A 股的问题 (Issue #153)

## [2.2.5] - 2026-02-01

### 新增
- 🤖 **AstrBot 消息推送** (PR #217)
  - 新增 AstrBot 通知渠道，支持推送到 QQ 和微信
  - 支持 HMAC SHA256 签名验证，确保通信安全
  - 通过 `ASTRBOT_URL` 和 `ASTRBOT_TOKEN` 配置

## [2.2.4] - 2026-02-01

### 新增
- ⚙️ **可配置数据源优先级** (PR #215)
  - 支持通过环境变量（如 `YFINANCE_PRIORITY=0`）动态调整数据源优先级
  - 无需修改代码即可优先使用特定数据源（如 Yahoo Finance）

## [2.2.3] - 2026-01-31

### 修复
- 📦 更新 requirements.txt，增加 `lxml_html_clean` 依赖以解决兼容性问题

## [2.2.2] - 2026-01-31

### 修复
- 🐛 修复代理配置区分大小写问题 (fixes #211)

## [2.2.1] - 2026-01-31

### 修复
- 🐛 **YFinance 兼容性修复** (PR #210, fixes #209)
  - 修复新版 yfinance 返回 MultiIndex 列名导致的数据解析错误

## [2.2.0] - 2026-01-31

### 新增
- 🔄 **多源回退策略增强**
  - 实现了更健壮的数据获取回退机制 (feat: multi-source fallback strategy)
  - 优化了数据源故障时的自动切换逻辑

### 修复
- 🐛 修复 analyzer 运行后无法通过改 .env 文件的 stock_list 内容调整跟踪的股票

## [2.1.14] - 2026-01-31

### 文档
- 📝 更新 README 和优化 auto-tag 规则

## [2.1.13] - 2026-01-31

### 修复
- 🐛 **Tushare 优先级与实时行情** (Fixed #185)
  - 修复 Tushare 数据源优先级设置问题
  - 修复 Tushare 实时行情获取功能

## [2.1.12] - 2026-01-30

### 修复
- 🌐 修复代理配置在某些情况下的区分大小写问题
- 🌐 修复本地环境禁用代理的逻辑

## [2.1.11] - 2026-01-30

### 优化
- 🚀 **飞书消息流优化** (PR #192)
  - 优化飞书 Stream 模式的消息类型处理
  - 修改 Stream 消息模式默认为关闭，防止配置错误运行时报错

## [2.1.10] - 2026-01-30

### 合并
- 📦 合并 PR #154 贡献

## [2.1.9] - 2026-01-30

### 新增
- 💬 **微信文本消息支持** (PR #137)
  - 新增微信推送的纯文本消息类型支持
  - 添加 `WECHAT_MSG_TYPE` 配置项

## [2.1.8] - 2026-01-30

### 修复
- 🐛 修正日志中 API 提供商显示错误 (PR #197)

## [2.1.7] - 2026-01-30

### 修复
- 🌐 禁用本地环境的代理设置，避免网络连接问题

## [2.1.6] - 2026-01-29

### 新增
- 📡 **Pytdx 数据源 (Priority 2)**
  - 新增通达信数据源，免费无需注册
  - 多服务器自动切换
  - 支持实时行情和历史数据
- 🏷️ **多源股票名称解析**
  - DataFetcherManager 新增 `get_stock_name()` 方法
  - 新增 `batch_get_stock_names()` 批量查询
  - 自动在多数据源间回退
  - Tushare 和 Baostock 新增股票名称/列表方法
- 🔍 **增强搜索回退**
  - 新增 `search_stock_price_fallback()` 用于数据源全部失败时
  - 新增搜索维度：市场分析、行业分析
  - 最大搜索次数从 3 增加到 5
  - 改进搜索结果格式（每维度 4 条结果）

### 改进
- 更新搜索查询模板以提高相关性
- 增强 `format_intel_report()` 输出结构

## [2.1.5] - 2026-01-29

### 新增
- 📡 新增 Pytdx 数据源和多源股票名称解析功能

## [2.1.4] - 2026-01-29

### 文档
- 📝 更新赞助商信息

## [2.1.3] - 2026-01-28

### 文档
- 📝 重构 README 布局
- 🌐 新增繁体中文翻译 (README_CHT.md)

### 修复
- 🐛 修复 WebUI 无法输入美股代码问题
  - 输入框逻辑改成所有字母都转换成大写
  - 支持 `.` 的输入（如 `BRK.B`）

## [2.1.2] - 2026-01-27

### 修复
- 🐛 修复个股分析推送失败和报告路径问题 (fixes #166)
- 🐛 修改 CR 错误，确保微信消息最大字节配置生效

## [2.1.1] - 2026-01-26

### 新增
- 🔧 添加 GitHub Actions auto-tag 工作流
- 📡 添加 yfinance 兜底数据源及数据缺失警告

### 修复
- 🐳 修复 docker-compose 路径和文档命令
- 🐳 Dockerfile 补充 copy src 文件夹 (fixes #145)

## [2.1.0] - 2026-01-25

### 新增
- 🇺🇸 **美股分析支持**
  - 支持美股代码直接输入（如 `AAPL`, `TSLA`）
  - 使用 YFinance 作为美股数据源
- 📈 **MACD 和 RSI 技术指标**
  - MACD：趋势确认、金叉死叉信号（零轴上金叉⭐、金叉✅、死叉❌）
  - RSI：超买超卖判断（超卖⭐、强势✅、超买⚠️）
  - 指标信号纳入综合评分系统
- 🎮 **Discord 推送支持** (PR #124, #125, #144)
  - 支持 Discord Webhook 和 Bot API 两种方式
  - 通过 `DISCORD_WEBHOOK_URL` 或 `DISCORD_BOT_TOKEN` + `DISCORD_MAIN_CHANNEL_ID` 配置
- 🤖 **机器人命令交互**
  - 钉钉机器人支持 `/分析 股票代码` 命令触发分析
  - 支持 Stream 长连接模式
- 🌡️ **AI 温度参数可配置** (PR #142)
  - 支持自定义 AI 模型温度参数
- 🐳 **Zeabur 部署支持**
  - 添加 Zeabur 镜像部署工作流
  - 支持 commit hash 和 latest 双标签

### 重构
- 🏗️ **项目结构优化**
  - 核心代码移至 `src/` 目录，根目录更清爽
  - 文档移至 `docs/` 目录
  - Docker 配置移至 `docker/` 目录
  - 修复所有 import 路径，保持向后兼容
- 🔄 **数据源架构升级**
  - 新增数据源熔断机制，单数据源连续失败自动切换
  - 实时行情缓存优化，批量预取减少 API 调用
  - 网络代理智能分流，国内接口自动直连
- 🤖 Discord 机器人重构为平台适配器架构

### 修复
- 🌐 **网络稳定性增强**
  - 自动检测代理配置，对国内行情接口强制直连
  - 修复 EfinanceFetcher 偶发的 `ProtocolError`
  - 增加对底层网络错误的捕获和重试机制
- 📧 **邮件渲染优化**
  - 修复邮件中表格不渲染问题 (#134)
  - 优化邮件排版，更紧凑美观
- 📢 **企业微信推送修复**
  - 修复大盘复盘推送不完整问题
  - 增强消息分割逻辑，支持更多标题格式
  - 增加分批发送间隔，避免限流丢失
- 👷 **CI/CD 修复**
  - 修复 GitHub Actions 中路径引用的错误

## [2.0.0] - 2026-01-24

### 新增
- 🇺🇸 **美股分析支持**
  - 支持美股代码直接输入（如 `AAPL`, `TSLA`）
  - 使用 YFinance 作为美股数据源
- 🤖 **机器人命令交互** (PR #113)
  - 钉钉机器人支持 `/分析 股票代码` 命令触发分析
  - 支持 Stream 长连接模式
  - 支持选择精简报告或完整报告
- 🎮 **Discord 推送支持** (PR #124)
  - 支持 Discord Webhook 推送
  - 添加 Discord 环境变量到工作流

### 修复
- 🐳 修复 WebUI 在 Docker 中绑定 0.0.0.0 (fixed #118)
- 🔔 修复飞书长连接通知问题
- 🐛 修复 `analysis_delay` 未定义错误
- 🔧 启动时 config.py 检测通知渠道，修复已配置自定义渠道情况下仍然提示未配置问题

### 改进
- 🔧 优化 Tushare 优先级判断逻辑，提升封装性
- 🔧 修复 Tushare 优先级提升后仍排在 Efinance 之后的问题
- ⚙️ 配置 TUSHARE_TOKEN 时自动提升 Tushare 数据源优先级
- ⚙️ 实现 4 个用户反馈 issue (#112, #128, #38, #119)

## [1.6.0] - 2026-01-19

### 新增
- 🖥️ WebUI 管理界面及 API 支持（PR #72）
  - 全新 Web 架构：分层设计（Server/Router/Handler/Service）
  - 核心 API：支持 `/analysis` (触发分析), `/tasks` (查询进度), `/health` (健康检查)
  - 交互界面：支持页面直接输入代码并触发分析，实时展示进度
  - 运行模式：新增 `--webui-only` 模式，仅启动 Web 服务
  - 解决了 [#70](https://github.com/ArcSeek-X/HermesX/issues/70) 的核心需求（提供触发分析的接口）
- ⚙️ GitHub Actions 配置灵活性增强（[#79](https://github.com/ArcSeek-X/HermesX/issues/79)）
  - 支持从 Repository Variables 读取非敏感配置（如 STOCK_LIST, GEMINI_MODEL）
  - 保持对 Secrets 的向下兼容

### 修复
- 🐛 修复企业微信/飞书报告截断问题（[#73](https://github.com/ArcSeek-X/HermesX/issues/73)）
  - 移除 notification.py 中不必要的长度硬截断逻辑
  - 依赖底层自动分片机制处理长消息
- 🐛 修复 GitHub Workflow 环境变量缺失（[#80](https://github.com/ArcSeek-X/HermesX/issues/80)）
  - 修复 `CUSTOM_WEBHOOK_BEARER_TOKEN` 未正确传递到 Runner 的问题

## [1.5.0] - 2026-01-17

### 新增
- 📲 单股推送模式（[#55](https://github.com/ArcSeek-X/HermesX/issues/55)）
  - 每分析完一只股票立即推送，不用等全部分析完
  - 命令行参数：`--single-notify`
  - 环境变量：`SINGLE_STOCK_NOTIFY=true`
- 🔐 自定义 Webhook Bearer Token 认证（[#51](https://github.com/ArcSeek-X/HermesX/issues/51)）
  - 支持需要 Token 认证的 Webhook 端点
  - 环境变量：`CUSTOM_WEBHOOK_BEARER_TOKEN`

## [1.4.0] - 2026-01-17

### 新增
- 📱 Pushover 推送支持（PR #26）
  - 支持 iOS/Android 跨平台推送
  - 通过 `PUSHOVER_USER_KEY` 和 `PUSHOVER_API_TOKEN` 配置
- 🔍 博查搜索 API 集成（PR #27）
  - 中文搜索优化，支持 AI 摘要
  - 通过 `BOCHA_API_KEYS` 配置
- 📊 Efinance 数据源支持（PR #59）
  - 新增 efinance 作为数据源选项
- 🇭🇰 港股支持（PR #17）
  - 支持 5 位代码或 HK 前缀（如 `hk00700`、`hk1810`）

### 修复
- 🔧 飞书 Markdown 渲染优化（PR #34）
  - 使用交互卡片和格式化器修复渲染问题
- ♻️ 股票列表热重载（PR #42 修复）
  - 分析前自动重载 `STOCK_LIST` 配置
- 🐛 钉钉 Webhook 20KB 限制处理
  - 长消息自动分块发送，避免被截断
- 🔄 AkShare API 重试机制增强
  - 添加失败缓存，避免重复请求失败接口

### 改进
- 📝 README 精简优化
  - 高级配置移至 `docs/full-guide.md`


## [1.3.0] - 2026-01-12

### 新增
- 🔗 自定义 Webhook 支持
  - 支持任意 POST JSON 的 Webhook 端点
  - 自动识别钉钉、Discord、Slack、Bark 等常见服务格式
  - 支持配置多个 Webhook（逗号分隔）
  - 通过 `CUSTOM_WEBHOOK_URLS` 环境变量配置

### 修复
- 📝 企业微信长消息分批发送
  - 解决自选股过多时内容超过 4096 字符限制导致推送失败的问题
  - 智能按股票分析块分割，每批添加分页标记（如 1/3, 2/3）
  - 批次间隔 1 秒，避免触发频率限制

## [1.2.0] - 2026-01-11

### 新增
- 📢 多渠道推送支持
  - 企业微信 Webhook
  - 飞书 Webhook（新增）
  - 邮件 SMTP（新增）
  - 自动识别渠道类型，配置更简单

### 改进
- 统一使用 `NOTIFICATION_URL` 配置，兼容旧的 `WECHAT_WEBHOOK_URL`
- 邮件支持 Markdown 转 HTML 渲染

## [1.1.0] - 2026-01-11

### 新增
- 🤖 OpenAI 兼容 API 支持
  - 支持 DeepSeek、通义千问、Moonshot、智谱 GLM 等
  - Gemini 和 OpenAI 格式二选一
  - 自动降级重试机制

## [1.0.0] - 2026-01-10

### 新增
- 🎯 AI 决策仪表盘分析
  - 一句话核心结论
  - 精确买入/止损/目标点位
  - 检查清单（✅⚠️❌）
  - 分持仓建议（空仓者 vs 持仓者）
- 📊 大盘复盘功能
  - 主要指数行情
  - 涨跌统计
  - 板块涨跌榜
  - AI 生成复盘报告
- 🔍 多数据源支持
  - AkShare（主数据源，免费）
  - Tushare Pro
  - Baostock
  - YFinance
- 📰 新闻搜索服务
  - Tavily API
  - SerpAPI
- 💬 企业微信机器人推送
- ⏰ 定时任务调度
- 🐳 Docker 部署支持
- 🚀 GitHub Actions 零成本部署

### 技术特性
- Gemini AI 模型（gemini-3-flash-preview）
- 429 限流自动重试 + 模型切换
- 请求间延时防封禁
- 多 API Key 负载均衡
- SQLite 本地数据存储

---

[Unreleased]: https://github.com/ArcSeek-X/HermesX/compare/v3.28.0...HEAD
[3.28.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.27.0...v3.28.0
[3.27.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.26.1...v3.27.0
[3.26.1]: https://github.com/ArcSeek-X/HermesX/compare/v3.25.0...v3.26.1
[3.25.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.24.1...v3.25.0
[3.24.1]: https://github.com/ArcSeek-X/HermesX/compare/v3.24.0...v3.24.1
[3.24.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.23.0...v3.24.0
[3.23.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.22.0...v3.23.0
[3.22.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.21.1...v3.22.0
[3.21.1]: https://github.com/ArcSeek-X/HermesX/compare/v3.21.0...v3.21.1
[3.21.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.20.0...v3.21.0
[3.20.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.19.0...v3.20.0
[3.19.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.18.0...v3.19.0
[3.18.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.17.1...v3.18.0
[3.17.1]: https://github.com/ArcSeek-X/HermesX/compare/v3.17.0...v3.17.1
[3.17.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.16.0...v3.17.0
[3.16.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.15.0...v3.16.0
[3.15.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.14.2...v3.15.0
[3.14.2]: https://github.com/ArcSeek-X/HermesX/compare/v3.14.1...v3.14.2
[3.14.1]: https://github.com/ArcSeek-X/HermesX/compare/v3.14.0...v3.14.1
[3.14.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.13.0...v3.14.0
[3.13.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.12.0...v3.13.0
[3.12.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.11.0...v3.12.0
[3.11.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.10.1...v3.11.0
[3.10.1]: https://github.com/ArcSeek-X/HermesX/compare/v3.10.0...v3.10.1
[3.10.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.9.0...v3.10.0
[3.9.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.8.0...v3.9.0
[3.8.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.7.0...v3.8.0
[3.7.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.6.0...v3.7.0
[3.6.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.5.0...v3.6.0
[3.5.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.4.10...v3.5.0
[3.4.10]: https://github.com/ArcSeek-X/HermesX/compare/v3.4.9...v3.4.10
[3.4.9]: https://github.com/ArcSeek-X/HermesX/compare/v3.4.8...v3.4.9
[3.4.8]: https://github.com/ArcSeek-X/HermesX/compare/v3.4.7...v3.4.8
[3.4.7]: https://github.com/ArcSeek-X/HermesX/compare/v3.4.0...v3.4.7
[3.4.0]: https://github.com/ArcSeek-X/HermesX/compare/v3.3.22...v3.4.0
[3.3.22]: https://github.com/ArcSeek-X/HermesX/compare/v3.3.12...v3.3.22
[3.3.12]: https://github.com/ArcSeek-X/HermesX/compare/v3.2.11...v3.3.12
[3.2.11]: https://github.com/ArcSeek-X/HermesX/compare/v3.2.10...v3.2.11
[2.3.0]: https://github.com/ArcSeek-X/HermesX/compare/v2.2.5...v2.3.0
[2.2.5]: https://github.com/ArcSeek-X/HermesX/compare/v2.2.4...v2.2.5
[2.2.4]: https://github.com/ArcSeek-X/HermesX/compare/v2.2.3...v2.2.4
[2.2.3]: https://github.com/ArcSeek-X/HermesX/compare/v2.2.2...v2.2.3
[2.2.2]: https://github.com/ArcSeek-X/HermesX/compare/v2.2.1...v2.2.2
[2.2.1]: https://github.com/ArcSeek-X/HermesX/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.14...v2.2.0
[2.1.14]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.13...v2.1.14
[2.1.13]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.12...v2.1.13
[2.1.12]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.11...v2.1.12
[2.1.11]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.10...v2.1.11
[2.1.10]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.9...v2.1.10
[2.1.9]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.8...v2.1.9
[2.1.8]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.7...v2.1.8
[2.1.7]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.6...v2.1.7
[2.1.6]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.5...v2.1.6
[2.1.5]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.4...v2.1.5
[2.1.4]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.3...v2.1.4
[2.1.3]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.2...v2.1.3
[2.1.2]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/ArcSeek-X/HermesX/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/ArcSeek-X/HermesX/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/ArcSeek-X/HermesX/compare/v1.6.0...v2.0.0
[1.6.0]: https://github.com/ArcSeek-X/HermesX/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/ArcSeek-X/HermesX/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/ArcSeek-X/HermesX/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/ArcSeek-X/HermesX/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/ArcSeek-X/HermesX/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/ArcSeek-X/HermesX/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ArcSeek-X/HermesX/releases/tag/v1.0.0
