# HermesX 测试体系分类、拆分与整理方案

> **服务端五层架构迁移后的测试组织与维护指引**
>
> 本方案围绕 HermesX 已调整的代码边界，说明如何归类测试、拆分混合职责文件、收敛公共依赖并保留现有行为覆盖，供后续开发者、模型与 Agent 分批实施和交接使用。

| 项目 | 约定 |
| --- | --- |
| 作者 | Codex（依据项目维护者提出的目标与讨论整理） |
| 文档版本 | v1.1 |
| 创建日期 | 2026-10-31 |
| 最后更新时间 | 2026-10-31（Asia/Shanghai） |
| 状态 | 后续测试重构的设计与实施指引；本文不表示测试已经迁移 |
| 关联架构方案 | [ARCHITECTURE_TARGET.md](./ARCHITECTURE_TARGET.md)；本方案是其测试体系整理专项补充 |
| 基线日期 | 2026-10-31；实施前重新统计与验证 |
| 主要范围 | `tests/` 的目录归类、文件内部拆分、公共测试依赖及运行分类 |
| 必要联动 | 测试配置、脚本、CI、文档中真实引用测试路径的部分 |
| 目标 | 便于按职责定位、按业务回归、单独运行和跨 Agent 接手，同时保持原有行为覆盖 |
| 实施权限 | 本文只交付方案；实际代码整理按用户后续指令执行，Git 操作遵守 `AGENTS.md` |

## 目录

- [与架构调整方案的关系](#architecture-relationship)
- [1. 背景与事实基线](#baseline)
- [2. 本方案采用的设计决定](#decisions)
- [3. 目标目录与归类规则](#layout)
- [4. 文件内部拆分与命名](#splitting)
- [5. 公共依赖、fixture 与导入治理](#dependencies)
  - [5.1 fixture 的可见范围](#fixture-scope)
  - [5.2 全局兼容补丁](#compatibility)
  - [5.3 support、样本与导入](#support)
- [6. marker 与运行方式](#execution)
- [7. 实施顺序与可交付单位](#stages)
- [8. 验收、回滚与交接](#acceptance)
  - [8.1 验收口径](#acceptance-criteria)
  - [8.2 统一迁移记录](#handoff)
- [9. 边界与接手提醒](#boundaries)
- [10. 参考依据](#references)

<a id="architecture-relationship"></a>

## 与架构调整方案的关系

[ARCHITECTURE_TARGET.md](./ARCHITECTURE_TARGET.md) 规定服务端的目标边界、依赖方向、职责拆分和验收原则。本方案承接这些设计，专门处理迁移后测试体系的组织问题；生产代码的架构决策继续以关联方案、已确认 ADR 和当前实现为依据。

| 架构方案中的要求 | 本方案如何承接 |
| --- | --- |
| §2 分层依赖与 §3 目标目录 | 按被测边界与业务域归类测试，覆盖 domain、application、infrastructure、bootstrap、config 及 API/Bot 驱动 |
| §4.3 文件内部代码拆分 | 将同一文件内混合的规则、用例、接口与集成测试拆成职责清晰的测试单元，并保留原行为对应关系 |
| §4.4 Web/Desktop 联动 | 核对接口、状态、认证和打包契约；客户端原生测试继续在各自应用目录维护 |
| §6–7 分阶段实施、验证与回滚 | 用 T0–T5 独立编号组织测试专项，逐批核对用例发现、行为覆盖、共享状态与门禁结果 |
| §9 跨模型与 Agent 交接 | 建立统一的测试迁移清单与切片交接记录，后续执行者无需依赖聊天记录还原决定 |

服务端迁移状态由 [ARCHITECTURE_MIGRATION_STATUS.md](./ARCHITECTURE_MIGRATION_STATUS.md) 汇总，历史执行过程见 [ARCHITECTURE_MIGRATION_PROGRESS.md](./ARCHITECTURE_MIGRATION_PROGRESS.md)。测试专项实施后使用本方案第 8.2 节约定的独立进度记录；不能把此前服务端迁移完成率直接当作本轮测试整理的进度。涉及生产行为或架构边界变化时，须回到架构方案与仓库流程评估其范围。

<a id="baseline"></a>

## 1. 背景与事实基线

服务端五层迁移已经形成新的源码边界，但测试仍以历史平铺结构为主。本方案承接 `ARCHITECTURE_TARGET.md` 的职责划分和交接原则；以当前 `AGENTS.md`、可执行配置及代码为准，不复用已经过期的旧模块路径。

本轮通过文件统计、AST 扫描和代表性内容阅读得到以下情况，未重新运行完整测试套件：

| 项目 | 当前观察 |
| --- | ---: |
| `tests/` 文件数（按 `rg --files` 可见文件口径） | 306 |
| 直接位于 `tests/` 根目录的文件 | 299 |
| `test_*.py` 文件 | 298 |
| Python 文件总行数 | 136330 |
| 不少于 1000 行的 Python 文件 | 28 |
| 不少于 2000 行的 Python 文件 | 14 |

`setup.cfg` 当前设置 `testpaths = tests`、`python_files = test_*.py`，已声明 `unit / integration / network / benchmark`。本轮 AST 扫描发现直接使用 `pytest.mark.network` 与 `pytest.mark.benchmark` 的位置，但未发现直接使用 `pytest.mark.unit`、`pytest.mark.integration` 的位置；这不代替运行时 marker 盘点。

代表性问题：

- `test_multi_agent.py` 同时包含解析、领域规则、编排、记忆、事件监控和 API 测试，一个文件无法表达清晰归属。
- `test_system_config_service.py` 中一个 TestCase 包含 220 个测试方法，配置展示、秘密值、模型发现和运行时行为等集中在同一类。
- `tests/conftest.py` 全局替换 asyncio、AnyIO 和 FastAPI/Starlette TestClient 的部分行为，并通过会话级自动 fixture 注册端口工厂；纯领域测试也处于这套公共环境中。
- 多个测试直接修改 `sys.modules`、`sys.path` 或在模块导入时装配生产端口；共享辅助 `tests.litellm_stub` 又被多个业务域消费。
- 若干文件通过 `Path(__file__).parents[1]` 或 `parent.parent` 推导仓库根目录，另有样本路径相对于测试文件；搬迁后必须逐项修正。

测试数量和代码行数仅用于发现维护热点，不作为删除用例、强制拆分或压缩覆盖的理由。此前重构台账记录的 5713 passed 是历史结果，不能直接作为本轮开工时的最新结果。

<a id="decisions"></a>

## 2. 本方案采用的设计决定

1. **目录按被测边界，再按业务域组织。**与 `src/domain`、`src/application`、`src/infrastructure` 等职责对应，但不机械复制所有源码子目录。
2. **运行属性用 marker 表达。**不再同时建立 `unit/<层>/<域>` 与 `integration/<层>/<域>` 两套镜像目录；`tests/integration/` 只放真实跨边界流程。
3. **测试文件按行为契约拆分。**大文件先盘点职责和共享准备过程，再提取；不按行数平均切分，不强制“一源码文件对应一测试文件”。
4. **先保持行为覆盖，再调整共享依赖。**目录迁移、内部拆分、fixture/stub 治理分批验证，便于定位回归。
5. **公共测试代码留在测试体系。**可复用辅助放 `tests/support/`，静态样本放 `tests/fixtures/`；局部 fixture 就近管理，不因整理测试向生产代码加入测试专用兼容实现。
6. **保持现有运行方式作为首轮基线。**保留 `testpaths = tests` 和当前导入模式，初期保留唯一文件名；导入模式、并行运行、超时阈值和 CI 触发策略另作有证据的调整。
7. **保持现有 unittest/pytest 风格。**不顺便全量改写 TestCase、不按文件数/行数 KPI 删改测试；删除或合并用例须说明保护行为及替代证据。

目录归属与实际运行属性分开判断。例如仓储测试即使使用临时 SQLite，仍归 `infrastructure/persistence/`；是否标记 integration 由其是否验证实际组件协作决定。文件名称含 `e2e` 不代表已验证完整入口链路。

<a id="layout"></a>

## 3. 目标目录与归类规则

下树是可按需建立的结构，不要求创建空目录。顶层仅保留必要入口、公共配置和说明。

```text
tests/
├── conftest.py
├── domain/
│   ├── analysis/  decision/  market/  portfolio/
│   └── notification/  generation/  shared/
├── application/
│   ├── analysis/  agent/  backtest/  decision/
│   ├── portfolio/  alert/  market/  quote/
│   └── history/  intelligence/  notification/  reporting/  runtime/  usage/  watchlist/
├── infrastructure/
│   ├── persistence/  providers/  generation/  notification/
│   └── search/  reporting/  indexing/  agent_runtime/  security/
├── api/
│   ├── analysis/  agent/  portfolio/  auth/
│   └── ...                         # 其他已有 API 能力
├── bot/
├── bootstrap/
├── config/
├── integration/                    # 多组件实际协作的完整流程
│   ├── analysis/  agent/  reporting/
│   └── ...
├── architecture/                   # 分层、依赖与装配边界约束
├── tooling/                        # 脚本、工作流、文档一致性、打包配置
├── support/                        # 共享 stub、构造器、必要测试兼容工具
└── fixtures/                       # 报告、行情、响应等静态样本
```

| 被验证的职责 | 目录 | 当前文件举例及判断要求 |
| --- | --- | --- |
| 纯领域计算、值对象与规则 | `domain/<业务域>/` | `test_portfolio_risk_rules.py`、`test_decision_action.py`、`test_pipeline_domain_rules.py`；确认主体确为纯规则后归入 |
| 业务用例、编排、端口消费 | `application/<业务域>/` | `test_portfolio_service.py`、`test_history_query_service.py`；用例使用替身端口仍归本层 |
| ORM、仓储、升级、SDK 与第三方适配 | `infrastructure/<能力>/` | `test_storage_schema_upgrade.py`、`test_backtest_repo_record_mapping.py`、各 fetcher/sender 测试 |
| HTTP 路径、校验、状态码、响应与认证 | `api/<能力>/` | `test_portfolio_api.py`、`test_auth_api.py`、`test_kline_schema.py`；纯 DTO 或规则测试按实际职责另分 |
| IM 命令、分发和平台协议 | `bot/` | `test_ask_command.py`、`test_feishu_stream.py`、`test_discord_platform.py` |
| 装配与生命周期的实际行为 | `bootstrap/` | `test_bootstrap_entrypoints.py`、`test_bootstrap_api_lifecycle.py` |
| 配置读取、字段定义、解析与文件编辑 | `config/` | `test_config_manager.py`、`test_config_registry.py`、`test_config_env_compat.py`；系统设置用例仍归 application/runtime |
| 实际跨边界业务流程 | `integration/<业务域>/` | `test_analysis_integration.py` 等须核查真实入口、参与组件和 mock 边界后判定 |
| AST/源码边界与装配规则守卫 | `architecture/` | `test_check_architecture.py`、各 `*_wiring.py` 中纯静态约束部分 |
| 开发与交付工具、文档和工作流契约 | `tooling/` | `test_build_release_notes.py`、`test_docker_entrypoint.py`、`test_packaging_build_scripts.py`、各文档契约测试 |

补充约束：

- `data_provider/` 是原位保留的基础设施适配包，其测试可归 `infrastructure/providers/`，不要求迁移生产包。
- `src/auth.py` 等已批准留存模块按实际职责归类测试；例如密码/会话实现放 `infrastructure/security/`，HTTP 认证放 `api/auth/`。不借分类改变生产代码例外决策。
- `tests/agent/` 的四个现有文件需逐项判断：纯风险/分歧规则与用例协作可以有不同落点。
- `tw_institutional_live_smoke.py`、`longbridge_live_smoke.py` 等非默认收集脚本单独登记调用方式；不能因移动或改名而意外进入离线门禁。
- Web 的 Vitest/Playwright 测试继续位于 `apps/hrs-web/`，Desktop 测试继续位于 `apps/hrs-desktop/`。根级 Python 测试只承接相关 Python/打包契约，不集中搬走客户端原生测试。

<a id="splitting"></a>

## 4. 文件内部拆分与命名

以下是优先候选，具体目标文件名由行为盘点确定。混合文件可以分别进入多个被测边界，不强求整文件单一落点。

| 文件及基线行数 | 拆分方向 | 重点约束 |
| --- | --- | --- |
| `test_system_config_service.py`（4609） | 读取/展示、校验、保存/冲突、导入导出、模型发现/探测、秘密值处理、运行时接线 | 当前 222 个测试方法；保留临时 `.env`、Config 重置与失败/脱敏反例 |
| `test_multi_agent.py`（4043） | 解析、领域 DTO/规则、策略路由/聚合、编排器、事件监控、记忆、API 与集成流程 | 不同类分别归属；不能全部因名称含 agent 而移入 application |
| `test_analysis_api_contract.py`（3904） | 请求响应、异步状态、重复提交、任务队列协作、图片识别 | 区分 HTTP 契约和队列行为；保持 200/202/409 等既有语义 |
| `test_market_analyzer_generate_text.py`（3585） | 生成/回退、提示词、运行时接线、用量持久化 | 保留真实调用链覆盖，不能只保留模板字符串断言 |
| `test_agent_pipeline.py`（3455） | 配置、工厂构造、结果转换、路由、技能注册/激活、pipeline 接线 | 核对模块级 stub、策略目录相对路径和注册状态 |
| `test_backtest_service.py`（3254） | 回测用例、结果汇总、日线补数端口、异常/边界 | 保留数据库读写与端口协作的实际风险路径 |
| `test_alphasift_api.py`（3082）及其他大文件 | 按 endpoint、业务状态与共同准备过程进一步盘点 | 不预先按大小判定全部都要拆 |

拆分规则：

1. 先列出测试类、方法、参数集、setUp/tearDown、fixture、patch 位置及被保护行为，再确定新文件。
2. 相同输入形态、执行路径、断言逻辑的差异数据可参数化，并设置可读的场景 ID；错误码、异常路径或不同协作行为不强行合成一个大参数表。
3. 同一职责的辅助优先局部保留；确实多个文件共享时再提取最小构造器或 fixture，避免统一“万能测试基类”。
4. unittest 公共基类只承载准备/释放和辅助方法，不能遗留 `test_*` 方法让多个子类重复继承收集。导入其他测试类也可能改变收集结果，必须实测。
5. `test_portfolio_pr2.py`、`test_run_diagnostics_p1.py`、`test_run_diagnostics_p2.py`、`test_autocomplete_pr0.py` 等按保护的业务行为重新命名；历史编号留在迁移记录，不作为长期分类。
6. 对疑似重复用例，比较入口、前置状态、断言与故障检出能力；确认完全重复并有替代后才合并。不可因同样 mock 或同样调用某方法就判重复。

<a id="dependencies"></a>

## 5. 公共依赖、fixture 与导入治理

<a id="fixture-scope"></a>

### 5.1 fixture 的可见范围

根级 `conftest.py` 最终只承担确实全仓通用的配置。业务域的临时数据库、HTTP client、默认装配和状态清理逐步下放到可见范围合适的子目录 `conftest.py` 或显式 fixture；pytest fixture 按目录发现，不要求测试文件直接 import 它们。

现有大量 unittest.TestCase 不接收 pytest fixture 函数参数。对它们先保留可核对的 setUp/tearDown 或提取无测试方法的辅助，再选择适合的局部 autouse/显式装配方法；不为了统一 fixture 顺手改写整套测试风格。

`Config` 单例、环境变量、端口工厂、事件订阅者、线程池和缓存等全局状态，需记录初始化与恢复责任。临时文件和数据库放隔离目录，不能依赖开发者本机 `.env`、真实密钥或 `data/` 中的业务数据库。

<a id="compatibility"></a>

### 5.2 全局兼容补丁

当前 conftest 中的 asyncio 唤醒/关闭、AnyIO 线程执行与 TestClient 替换是独立治理对象，不能只搬到 support 后继续无条件全局生效，也不能随目录迁移直接删除。先复现原问题，盘点哪些测试依赖补丁，验证异常、取消、生命周期和并发行为，再决定适用范围。

关键 API/异步链路应保留使用真实框架运行机制的验证路径；测试替身或兼容 client 不能单独证明生产机制正确。是否需要保留某个环境兼容模式，由该切片的证据决定，不预先新增配置开关。

<a id="support"></a>

### 5.3 support、样本与导入

- `tests.litellm_stub` 等跨业务辅助是首批登记对象。先保留稳定入口，验证实际导入方式后再迁入 `support/`，同步所有引用；避免复制出多个实现不同的 stub。
- 审查各文件模块级 `sys.modules` 写入和装配：能够局部注入/恢复的逐步收敛，确认是否影响模块收集顺序。支持模块被导入时不应自行注册无关生产服务。
- 仓库根路径与样本路径通过少量统一辅助或 fixture 获取；测试对真实源码路径的架构断言仍可保留，但不能依赖测试目录深度。
- 暂不统一切换 `--import-mode=importlib`，也不批量新增 `__init__.py`；这两项会改变包名、模块身份和 helper 导入。初期保持文件 basename 唯一，后续需要改变时单独验证。
- 保留当前 `fixtures/notification_reports/` 等已有样本，迁移测试时修正引用。静态响应应脱敏，测试生成的报告、缓存和日志放临时目录。

<a id="execution"></a>

## 6. marker 与运行方式

沿用已注册 marker，不为每个目录新增同义标签。可先按模块或测试类标注，在文件内仍有不同属性时再细化。

| marker | 选择依据 |
| --- | --- |
| `unit` | 聚焦规则或单个组件，依赖受控，结果可确定；不因大量 mock 自动认定覆盖充分 |
| `integration` | 实际组件协作，例如 API→用例→临时数据库；可以同时具有 network 或 benchmark 属性 |
| `network` | 实际访问外部网络/三方服务；mock requests 的离线适配测试不属于该类 |
| `benchmark` | 有明确计时预算、运行条件和失败含义的性能验证 |

标记前审查真实 IO；不能把现有失败用例改标为 network、skip 或 xfail 来让离线门禁变绿。`unit` 与 `integration` 的收敛可逐步推进，未标注用例仍要留在全量离线门禁中。

实施后的典型运行方式（目录建立后才适用）：

```bash
python -m pytest tests/domain -q
python -m pytest tests/application/portfolio tests/api/portfolio -q
python -m pytest tests -m "not network" -q
python -m pytest tests -m network -q
```

`scripts/ci_gate.sh` 当前执行 `python -m pytest -m "not network"`，仍通过 `testpaths = tests` 递归发现；网络 smoke 使用 `-m network`。需同步所有硬编码旧路径的脚本、工作流与文档。禁止通过收窄默认收集目录排除难迁移测试。

<a id="stages"></a>

## 7. 实施顺序与可交付单位

本次使用 T0–T5 编号，避免与已完成的服务端 P0–P5 阶段混淆。每个切片按一个业务域或一组公共依赖交付，并遵守 `AGENTS.md` 的验证与 Git 规则。

| 阶段 | 工作 | 完成条件 |
| --- | --- | --- |
| T0 事实与清单 | 重新收集用例、marker、耗时及失败基线；逐文件确定归属和移动/拆分/保留状态 | 全部 298 个现有 test 文件及非默认收集辅助均有去向；实际数若变化，以当时工作树为准 |
| T1 低耦合试点 | 迁移纯领域规则和独立工具测试；保持文件名、测试逻辑与运行配置 | 单文件、目录与全量收集正常，修正根路径/样本引用，建立后续模板 |
| T2 按域归类 | 迁移配置、基础设施、应用、API、Bot、bootstrap 和架构测试 | 每批记录原→新路径、调用命令及发现的混合职责；职责不明者先保留并列明原因 |
| T3 内部拆分 | 按第 4 节拆代表性大文件，逐项映射保护行为 | 无意外遗漏或重复继承收集；参数化/合并造成数量变化有解释 |
| T4 公共依赖治理 | 缩小 fixture/装配范围，收敛 stub、模块级副作用与兼容补丁 | 单跑与全量一致；随机顺序验证通过；关键真实机制验证可复跑 |
| T5 收口 | 核对全仓测试引用、门禁和样本；补操作说明与进度记录 | 全量离线结果不退化；网络未跑项明示；目录归属与实际运行说明一致 |

T2/T3 可按业务域穿插，T4 中确属搬迁前置条件的部分可提前，但应在记录中单独说明。优先选择低耦合试点，不建议第一批就同时改全局 conftest 和最大的几个 API 文件。

<a id="acceptance"></a>

## 8. 验收、回滚与交接

<a id="acceptance-criteria"></a>

### 8.1 验收口径

- **纯移动阶段**：收集用例应能通过路径映射一一对应；记录新增/删除/skip/xfail 差异，不能只比较 passed 总数。
- **拆分阶段**：追踪测试类/方法、参数场景与保护行为；显式检查重复收集、基类继承和导入测试类带来的新增项。参数化可能改变用例数，须说明实际覆盖如何对应。
- **运行验证**：先跑受影响单文件/目录，再跑全量离线；涉及共享状态时增加随机顺序验证。已有 pytest-randomly 环境下记录 seed，以便复现。
- **测试发现**：使用 `python -m pytest tests --collect-only -q` 盘点；收集动作仍会执行模块导入，确认不会触发真实外部操作或写入业务数据。不要把 test 函数静态数量当作参数化后的实际用例数。
- **性能**：记录收集耗时与最慢用例（如 `--durations=20`），比较同一环境下的数据；不为满足任意秒数随意放宽断言。是否引入并行运行在全局状态隔离之后另作验证。
- **风险路径**：数据库升级、认证/秘密值、任务/SSE/取消、数据源 fallback、通知失败隔离和装配缺失行为须保留验证；不以 mock 掉这些风险层的局部通过替代。

<a id="handoff"></a>

### 8.2 统一迁移记录

T0 在本目录建立一份 `TEST_SUITE_MIGRATION_PROGRESS.md`（实施时创建），集中维护文件归属与切片状态，不让多个 Agent 各写一份冲突清单。每个原文件至少记录：

| 原路径 | 验证职责 | 目标路径/拆分结果 | fixture/stub/路径依赖 | 状态 | 验证证据 |
| --- | --- | --- | --- | --- | --- |
| T0 逐项填写 | 基于实际测试内容 | 可多个目标 | 含脚本/CI 引用 | 待定/完成/阻塞 | 命令、结果与切片编号 |

每片另记录分支/HEAD、开工时其他改动、决策、旧→新用例对应、失败与跳过差异、未验证项、下一片和回滚方式。历史统计不覆盖当前状态；清单数值更新必须注明基线。

回滚按切片恢复该片文件路径和测试配置，并保留其他任务工作成果；公共 fixture/stub 改动与消费者同步回退。不得复制覆盖整个工作区或删除业务数据。提交、推送、tag 及 PR 操作依用户授权和 `AGENTS.md` 执行。

<a id="boundaries"></a>

## 9. 边界与接手提醒

本文确定分类、拆分和实施原则；每个文件最终落点、重复用例是否可合并、兼容补丁能否移除，须由 T0 与对应切片给出代码和运行证据。尚未逐一语义审查全部 298 个文件，不能据此声称现有测试重复、无价值或已经完成分类。

本轮交付只有本方案文档，未移动/拆分测试、未改配置、未删除样本或执行代码测试。当前无对应英文版设计文档，本次不新增平行翻译；后续若修改已有中英操作文档，按仓库规则同步评估。

<a id="references"></a>

## 10. 参考依据

- [pytest 导入机制](https://docs.pytest.org/en/stable/explanation/pythonpath.html)：默认导入方式、文件同名限制及 importlib 模式的辅助模块导入差异。
- [pytest fixture](https://docs.pytest.org/en/stable/how-to/fixtures.html)：fixture 的发现、作用域、复用与参数化。
- [pytest marker](https://docs.pytest.org/en/latest/how-to/mark.html)：按运行属性标记与选择测试。
- 仓内依据：`AGENTS.md`、`setup.cfg`、`tests/conftest.py`、`scripts/ci_gate.sh`、`.github/workflows/network-smoke.yml` 及本目录的服务端迁移文档。
