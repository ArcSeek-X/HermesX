# HermesX 全仓目标架构与服务端改造方案（实施基准 v4）

| 项目 | 约定 |
| --- | --- |
| 状态 | 服务端分层、测试整理及第二轮大文件职责拆分已实施；本文保留架构约束，部署与客户端验收缺口另列，不代表全部发布验收通过 |
| 状态更新时间 | 2026-11-04（Asia/Shanghai）；核对已实施拆分与已决约束，部署验收状态见当前总览 |
| 已落地代码依据 | `ad7274e0`（服务端职责拆分）、`6eb298aa`（测试整理）；当前 HEAD 与工作区状态以 Git 为准 |
| 当前状态总览 | [ARCHITECTURE_MIGRATION_STATUS.md](./ARCHITECTURE_MIGRATION_STATUS.md) |
| 服务端大文件拆分实施延续 | [ARCHITECTURE_TARGET_LARGE_FILE_REFACTORING.md](./ARCHITECTURE_TARGET_LARGE_FILE_REFACTORING.md)：§4.3 的服务端大文件第二轮拆分结果、验证证据与交接记录 |
| 数据源内部优化初步方案 | [ARCHITECTURE_TARGET_DATA_PROVIDER_REFACTORING.md](./ARCHITECTURE_TARGET_DATA_PROVIDER_REFACTORING.md)：保留根目录，按能力收敛管理器、具体源及公共机制；v0.3 已穷举目标路径、72 个原文件去向和 B00–B23 批次，设计阶段尚未实施 |
| 仓库根目录 | `HermesX/`；沿用现有可导入的 Python 包 `src`，不增加 `src/hermesx/` |
| 主要改造范围 | `src/`、`api/`、`bot/`、`data_provider/`、根目录 Python 入口和相应测试 |
| 联动范围 | 当导入路径或契约变化时，同步修改 Web、Desktop、脚本、Docker、CI、文档 |
| 现有资产 | 原位保留；不因本方案执行无关的目录归档、清理或忽略规则变更 |
| 历史预计改动文件数（初稿） | **约 300–450 个**（`data_provider/` 保留原路径）；若整体迁入 `src/infrastructure/providers/`，约 **400–550 个** |
| 历史预计 AI token 消耗（初稿） | 完成 P0–P5 约 **150万–350万 token**；若整体迁移数据源包、前端契约联动较多，约 **200万–450万 token**；均为跨多个实施迭代的输入+输出粗估，不是单次对话额度或费用承诺 |

以下是初稿历史估算，不表示当前待改文件数、实际 token 用量或剩余预算。估算口径：以 2026-10-23 工作树为基线，`src/`、`api/`、`bot/`、`data_provider/` 共约 352 个 Python 文件，`tests/` 约 270 个文件；约 497 个 Python 文件引用 `src` 或 `data_provider`（含服务端、测试与脚本，**不代表全部必改**）。改动文件数按全程实际触及的**去重逻辑文件**估计，包含代码、测试、Web/Desktop 必要联动、构建脚本和文档；一次移动按一个文件计，不把 Git diff 中的删除/新增算两次，不计生成物、本地数据或依赖目录。token 包含代码阅读、设计、修改、测试结果分析和返工；实际用量受每阶段范围、所用模型、上下文复用及验证轮次影响很大。P0 完成文件级职责/调用方清单后，应据此重估，不能把本区间当作进度或预算承诺。

> 设计盘点以 2026-10-23 为历史基线；§3 的目录图及旧路径属于规划或迁移基线，不应当作当前目录清单重新执行。本文现位于 `documents/framework/refactoring/ARCHITECTURE_TARGET.md`。数据源设计 ADR 见 [backend_architecture_adr.md](../backend_architecture_adr.md)，已决迁移例外及 schema 决策见 [architecture_migration_adr.md](../architecture_migration_adr.md)。

## 0. 当前实施状态与证据入口

| 范围 | 当前状态 | 证据入口 |
| --- | --- | --- |
| 服务端五层、端口及 bootstrap | 迁移主线已实施；已批准例外与保留项见 §4.5 | [架构总览](./ARCHITECTURE_MIGRATION_STATUS.md)、[实施流水](./ARCHITECTURE_MIGRATION_PROGRESS.md) |
| 测试归类、文件内部拆分及原生运行机制 | 已实施；新增回归用例与最新验证结果在测试台账追加 | [测试迁移台账](./TEST_SUITE_MIGRATION_PROGRESS.md)、[测试映射](./TEST_SUITE_SPLIT_MAPPING.md) |
| 服务端大文件第二轮拆分 | 原 13 件已评估，9 件拆分、4 件有理由保留；行数不是完成率 | [大文件拆分与交接](./ARCHITECTURE_TARGET_LARGE_FILE_REFACTORING.md) |
| 数据库与部署进程模型 | 原待确认事项均已决，见 §9.2.1；本轮不变更 schema 或进程模型 | [已决 ADR](../architecture_migration_adr.md) |
| 交付验收及前端检查 | 与代码实现完成度独立：Docker Pro 样式授权、桌面启动、干净构建、跨平台及前端检查按实际结果登记 | [当前未闭环事项](./ARCHITECTURE_MIGRATION_STATUS.md#仍需处理) |

后续执行者先核对当前状态与最新验证，再选择剩余事项；不要从 P0 重做已完成迁移，也不要把“已落地”解读为所有平台均通过验收。§6 的 P0–P5 保留为实施分解与审查框架，历史过程不覆盖当前状态。

## 1. 目标与边界

HermesX 是包含 Python 服务端、React Web、Electron Desktop、Bot、分析策略、部署流水线和文档的应用仓库。此次架构调整解决的是：入口和 HTTP 路由承载业务、`src/storage.py` 与配置文件职责过重、应用服务直接依赖具体数据源、分层关系难以检查。衡量结果看运行和依赖边界，而非“搬了多少文件”。

项目尚未上线，内部 import、配置组织、数据库结构可以统一调整；但现有本地数据库、密钥、日志和其他工作成果依然属于用户数据。任何重建数据库或清理文件都需要先确认准确目标、备份与恢复方式；“尚未上线”不等于默认允许删除数据。

本轮不要求 Web 改为 `features/`、Desktop 改为 `src/main/`，也不重排 `scripts/`、`docs/`、`documents/`。当 API 字段、启动方式、打包模块路径确实变化时，同一改动必须修正相应客户端与发布链路。

本方案采用“用例 + 端口/适配器”的依赖约束，是针对本项目多入口、多数据源和本地桌面打包的选择，不是 Python/FastAPI 的强制目录标准。尤其当前 `src` 是实际导入包名（`import src...`），**不是** Python Packaging Guide 所说的“`src/` 下再放一个独立包”的标准 src layout；保留它是为了符合现有运行与打包契约。目录数量不是验收指标：没有明确业务规则、调用方或测试需求的候选子目录不预先建空壳。

## 2. 依赖规则

```text
main.py / server.py / webui.py / api/ / bot/
                  │
                  ▼
           src.application ──────► src.domain
                  │
                  ▼
       用例侧端口（按业务域就近） ◄──── src.infrastructure

src.bootstrap ──► application + infrastructure + config
```

- `src.domain` 表达业务概念、规则和计算，不导入 FastAPI、SQLAlchemy、外部请求库及其他外层模块；**「其他外层模块」包含 `src.application`**——领域层不得反向依赖用例层（W4.1 已把通知等级/免打扰纯规则与 backend 身份常量下沉 domain，`src/config` 只依赖 domain；该方向由 `scripts/check_architecture.py` 的 `src/domain/` 禁入清单强制）。无 IO 只是必要条件，CSV 解析、HTTP DTO、模板渲染等不会仅因为“纯函数”而进入 domain。
- `src.application` 承载用例、任务编排和事务意图；依赖 domain 与面向用例定义的最小端口。**端口布局既定策略（W4.4 / ADR-002）：不建集中的 `src/application/ports/` 层，而是按业务域就近放置 `src/<layer>/<domain>/ports.py`**（实测 20+ 个），理由是端口与其服务的用例同处一包、重命名与删除影响面局部化、避免集中包变成“第二套 schema 目录”；只有确实属于领域规则本身的抽象才放在 domain。迁移过程中复用尚未下沉的读模型/服务实现时，只能调用其公开成员，跨层私有成员访问由架构守卫拦截；需要复用的辅助应提升为公开契约，而不是在用例里复制实现或加薄转发。
- `src.infrastructure` 承载 ORM、数据源适配、LLM、搜索、通知、报告输出及第三方 SDK。现有 `data_provider/common/base.py` 的 `DataSource` / `DataSourceManager` 是数据源内部的选源与降级契约，保留其已验证语义；应用端口只描述用例所需能力，不机械复制 Manager 的全部方法。
- `src.bootstrap` 集中装配端口实现和生命周期。`main.py`、`server.py`、`webui.py` 各自是入口，并共享装配逻辑；不能假设启动都经过 `main.py`。装配函数应显式区分 CLI 分析/调度与 API 服务模式；导入模块本身不应启动调度器、创建数据库或发起网络请求。
- `api/`、`bot/` 是两种外部驱动。业务 endpoint、Bot command 负责传输协议、输入校验、调用应用用例及响应映射；认证中间件、静态资源与健康检查等框架职责可保留明确的技术依赖，不强迫绕过空用例。`api/deps.py` 可以从 app 生命周期对象获取服务，但不能成为可从任意位置取具体实现的全局 Service Locator。
- 根据真实用例创建端口。对现有 `GenerationBackend(Protocol)` 等成熟契约先评估复用/迁移，避免出现同义双接口。`@runtime_checkable` 不能检查完整方法签名；需要类型检查或适配器契约测试。

## 3. 全仓目标目录

图例：`REWORK` 表示服务端结构改造目标；`KEEP` 表示保留现有位置与现有内容；`SYNC` 表示仅在服务端变更触发时同步引用或契约；`LOCAL` 表示保留在本机的运行时或开发资产。下列 `…` 表示该目录的其余现有文件全部保留，并非删除清单。新增文件是候选落点，实际以用例需要为准。这是覆盖全仓边界的**目标结构图**，不是逐文件精确清单；实施前须由工作树生成文件级迁移清单，逐项标记保留、移动、拆分或待定，不能凭此图推断未列出的文件可删除。

```text
HermesX/
├── AGENTS.md                              KEEP，协作规则唯一真源
├── CLAUDE.md -> AGENTS.md                 KEEP，软链接
├── ARCHITECTURE_TARGET.md                 初稿位置；本文现位于 documents/framework/refactoring/
├── README.md  LICENSE  SKILL.md           KEEP
├── .env.example  .gitignore  .gitattributes  .dockerignore  .python-version  KEEP
├── pyproject.toml  setup.cfg  requirements.txt  SYNC，必要时加入架构检查依赖
├── main.py  server.py  webui.py           REWORK，入口共享 src.bootstrap
├── start.sh                               SYNC，启动路径发生变化时
├── LOCAL_RUN_GUIDE.md                     KEEP
├── stock_data_view.md  数据源管理.md         KEEP
├── switch-node.js  switch-node.sh         KEEP
│
├── src/                                   REWORK，保留 src 包及 from src... 命名空间
│   ├── __init__.py
│   ├── domain/                            业务模型/规则；仅迁入满足纯业务语义的代码
│   │   ├── analysis/                      分析结果、质量规则、可纯算的指标
│   │   ├── decision/                      action/profile/scale、策略与质量规则
│   │   ├── market/                        市场结构、交易日规则、市场指标
│   │   ├── portfolio/                     持仓/风险业务计算；按实际规则建立
│   │   ├── alert/                         告警条件与判定
│   │   ├── backtest/                      脱离数据库的回测计算
│   │   └── shared/                        确有跨域复用的枚举与值对象
│   ├── application/                       按业务能力组织用例
│   │   ├── <业务域>/ports.py              已决：端口按业务域就近放置，不建集中 ports/ 目录
│   │   ├── analysis/                      个股分析、市场分析、AlphaSift、尾盘选股、pipeline
│   │   ├── backtest/                      回测用例
│   │   ├── decision/                      决策信号、评估、扫描、skill opinion
│   │   ├── portfolio/                     持仓、导入、风险、持仓告警
│   │   ├── alert/                         告警用例及 worker
│   │   ├── market/                        大盘复盘、市场灯塔、热点、板块及盘中上下文
│   │   ├── quote/                         行情/K 线/股票信息/代码解析与索引刷新
│   │   ├── history/                       历史报告与比较
│   │   ├── intelligence/                  情报与社交情绪编排
│   │   ├── agent/                         多 Agent 编排、对话、skills、业务工具
│   │   ├── reporting/                     报告内容、prompt 与语言编排
│   │   ├── runtime/                       任务、调度、运行流、系统配置用例
│   │   └── watchlist/                     自选股用例（按调用链确认）
│   ├── infrastructure/
│   │   ├── persistence/
│   │   │   ├── base.py                    唯一 ORM Base/metadata
│   │   │   ├── session.py                 engine/session 生命周期
│   │   │   ├── models/                    market_data、analysis、portfolio、decision、alert 等模型
│   │   │   ├── repositories/              仓储实现（原 src/repositories，2026-10-28 已全部迁入）
│   │   │   ├── schema_compat.py           已落地：幂等启动迁移链
│   │   │   └── ...                        ADR-008：不新增版本化迁移框架或平行 migrations/ 链
│   │   ├── providers/                     已有能力适配器；data_provider/ 原位保留，见 §9.2.1
│   │   │   ├── common/                    Base、健康检查、缓存、限速、归一化
│   │   │   ├── code_search/  fundamentals/  institutional/  kline/
│   │   │   ├── limit_pool/  news/  realtime/  sector/  stock_info/
│   │   │   └── ...                        顶层现有 fetcher/bridge 按依赖关系归位
│   │   ├── generation/                    生成实现、预设、provider cache 与 usage（原 src/llm，2026-10-28 已全部迁入）
│   │   ├── search/                        外部检索、缓存、排序实现
│   │   ├── notification/                  分发、路由、能力、降噪及各渠道 sender
│   │   ├── reporting/                     Jinja2、Markdown 转图、飞书文档适配
│   │   ├── agent_runtime/                 Codex/LiteLLM 后端、进程、传输适配
│   │   ├── brokers/                       Futu 等经纪商适配
│   │   ├── security/                      密码、会话等技术实现
│   │   ├── indexing/                      股票映射及索引加载
│   │   ├── patching/                      现有第三方补丁
│   │   └── observability/                 日志与技术诊断；有需要再细分
│   ├── bootstrap/                          各入口共用的装配及生命周期
│   └── config/                             运行值、字段元数据、.env 管理分职责
│
├── api/                                   REWORK，保留根目录 FastAPI 驱动
│   ├── app.py  deps.py  __init__.py
│   ├── middlewares/                      auth.py  error_handler.py  ...
│   └── v1/
│       ├── router.py  errors.py  __init__.py
│       ├── endpoints/                    当前 agent/alerts/alphasift/analysis/auth/backtest/
│       │                                 decision_signals/eod_picker/health/history/intelligence/
│       │                                 kline/limit_pool/portfolio/scanner/sector/stocks/
│       │                                 system_config/usage/watchlist.py
│       └── schemas/                      当前 16 个传输 DTO 文件，随契约更新
├── bot/                                   REWORK，保留根目录 IM 驱动
│   ├── dispatcher.py  handler.py  models.py  __init__.py
│   ├── platforms/                      dingtalk/feishu/discord 等现有实现
│   └── commands/                       analyze/ask/batch/chat/help/history/market/
│                                     research/status/strategies 等现有命令
│
├── apps/                                  KEEP，服务端契约变更时 SYNC
│   ├── hrs-web/
│   │   ├── package.json  package-lock.json  vite.config.ts  tsconfig*.json  ...
│   │   ├── public/                       前端公开资产与股票索引
│   │   ├── src/
│   │   │   ├── App.tsx  main.tsx  setupTests.ts
│   │   │   ├── api/  assets/  components/  constants/  contexts/  hooks/
│   │   │   ├── i18n/  locales/  pages/  router/  stores/  style/  types/  utils/
│   │   ├── e2e/  scripts/  tests/  assets/  static/
│   │   └── ...                            现有页面、组件与测试保持原位
│   └── hrs-desktop/
│       ├── main.js  preload.js  installer.nsh  package.json  package-lock.json
│       ├── renderer/loading.html
│       ├── scripts/afterPackMacos.js
│       └── tests/main.test.js  tests/preload.test.js
│
├── tests/                                 已完成：按 `TEST_SUITE_REFACTORING_PLAN.md` 的 T0–T5 分类重排（commit e630eb23），不再「随用随迁」；本图仅给顶层分组，细粒度分桶与逐件归属以该方案 §3 为唯一真源，逐件进度与证据见 `documents/framework/refactoring/TEST_SUITE_MIGRATION_PROGRESS.md`
│   ├── conftest.py  __init__.py  fixtures/
│   ├── domain/  application/  infrastructure/        # 镜像 src 分层：纯规则·值对象 / 用例与编排、端口消费 / ORM·provider·sender 等适配
│   ├── api/  bot/  bootstrap/  config/  integration/ # 各驱动与跨组件用例的 HTTP·命令契约、装配生命周期、配置、集成流程
│   └── tooling/  support/  utils/  agent/            # 脚本·workflow·docs·packaging·test_runtime·manual_smoke 工具 / 共享 stubs 与 paths 工具（方案候选的 builders·clients 尚未创建） / 纯 utils 件 / 保留的 agent 四件（`agent`、`utils` 为落地现实分组，方案 §3.1 的 `architecture/` 桶未建，其守卫按主 SUT 分入 `tooling/scripts`（check_architecture）、`api`、`bot`、`infrastructure`；分桶与命名以工作树及方案 §3 为准）
├── strategies/                            KEEP，现有 15 个 YAML 策略及 README.md
├── templates/                             KEEP，现有报告 Jinja2 模板
├── static/                                KEEP，Web 构建输出与静态资产
├── data/                                  LOCAL，现有 DB、缓存、锁、密钥、说明等原位保留
├── logs/  reports/                        LOCAL，现有运行结果原位保留
│
├── scripts/                               KEEP 路径；import、CI gate、打包引用按需 SYNC
│   ├── ci_gate.sh  test.sh  check_ai_assets.py  check_static_assets.py
│   ├── check_env.py  codex_app_server_gate_a.py  e2e_test_feishu_app.py
│   ├── build-all-macos.sh  build-all.ps1  build-backend-macos.sh  build-backend.ps1
│   ├── build-desktop-macos.sh  build-desktop.ps1  run-desktop.ps1
│   ├── fetch_tushare_stock_list.py  generate_index_from_csv.py
│   ├── generate_stock_index.py  refresh_stock_index.py
│   ├── generate_longbridge_oauth_token.py  generate_notification_actions_env_table.py
│   ├── macos-signature-audit.sh  verify-desktop-updater-artifacts.ps1
│   ├── stock_index_seeds/  stocksdk_bridge/
│   └── ...
├── docker/                                KEEP：Dockerfile  docker-compose.yml  entrypoint.sh
├── .github/                               KEEP：CODEOWNERS  FUNDING.yml  ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md  release.yml  requirements-ci.txt
│   ├── copilot-instructions.md  instructions/  scripts/
│   └── workflows/                        当前 00-daily-analysis/auto-tag/ci/create-release/
│                                       desktop-release/docker-publish/ghcr-dockerhub/
│                                       network-smoke/pr-review/stale 等工作流
├── docs/                                  KEEP：现有中英使用、部署、Bot、配置及专题文档/assets/
├── documents/                             KEEP：CHANGELOG.md、framework/、authority/、product/、
│                                       archify/、layout/、theme/ 等现有内容
├── .claude/                               KEEP：skills/、本地 reviews/
├── .agents/  .conventions/  .vscode/      KEEP，按现有规则管理
├── .idea/  .workbuddy/  .codebuddy/  .trae/  LOCAL/KEEP，现有内容保留
├── vibe-template/                         KEEP，现有第三方参考模板原位保留
└── ...                                    其他未逐项列出的现有仓库与本地文件保留
```

上树是全仓的**结构视图**，不是文件删除许可，也不是要求 Web、Desktop 和文档立即重组。`.idea/`、`.workbuddy/`、`.codebuddy/`、`.trae/`、`.DS_Store`、`__pycache__/`、`*.pyc`、`apps/*/node_modules/`、`apps/*/dist/` 等本机内容保持原样。Git 是否跟踪某项内容由现有 `.gitignore` / 仓库策略决定；“忽略”不等于删除。`data/` 中的 SQLite 数据库和本机密钥、`logs/`、`reports/` 均需要保留。唯一已确认可在实施时清理的构建残留是 `src/UNKNOWN.egg-info/`；先确认其确为生成物并记录清理结果。当前文档修改不执行任何清理。

## 4. 服务端现有模块的目标归属

以下是迁移边界，不是按名称批量 `git mv` 的命令清单；混合职责的文件需要先划分可测试的行为，再决定拆分。

| 迁移前位置 / 保留入口 | 已决落点 | 实施状态与关键校核 |
| --- | --- | --- |
| `src/config.py`、`src/core/config_manager.py`、`config_registry.py` | `src/config/` | 已完成：运行值落 `settings.py`，字段定义与注册落 `field_definitions.py` / `registry.py`，环境文件编辑落 `env_file.py`；默认值、优先级、热更新与脱敏契约保持 |
| `src/storage.py` | `src/infrastructure/persistence/` | `Base` 唯一、模型注册先于建表、session 生命周期、索引/升级顺序不变；开发库沿用 ADR-008 的保留与备份重建决策。**已完成部分迁移（2026-10-28）**：ORM/模型/会话/仓储已下沉 `persistence`，本文件保留为 `DatabaseManager` 门面（单例 + 会话/事务入口 + 同名薄委托），**暂作为已批准例外保留在 `src/storage.py`** |
| `src/repositories/` | `src/infrastructure/persistence/repositories/` | 应用端口从真实用例所需方法定义；事务所有权明确。**已完成（2026-10-28，PP-1~PP-7）**：全部仓储下沉 infra 并由 `src/application/*/ports.py` 端口 + bootstrap 装配收敛，根目录在 git 中已无文件；守卫已把 `src.repositories` 列为 application 层禁入前缀 |
| `data_provider/` | 原位保留 `data_provider/`；新能力适配层落 `src/infrastructure/providers/` | 优先隔离用例依赖；若迁移，保持 ADR-001 已验证的优先级、超时、降级、标准化和缓存行为，并同步全部入口与调用者。**当前决策（2026-10-30）：原位保留**——应用层一律经端口（`StockDataPort`/`MarketReviewDataPort`/`MarketDataPort`/`RealtimeQuotePort` 等）访问，守卫已把 `data_provider` 列为 application 层禁入前缀；未来若整体迁入 `infrastructure/providers/`，仍须守住上述行为 |
| `src/services/` | 多数进入 `src/application/<业务域>/`；纯业务规则才进入 domain | `import_parser.py` 等输入解析不因无网络就成为 domain；需检查调用图。**已完成（2026-10-29）**：具体实现已按业务域全部迁入 `src/application/`，本目录仅余 `__init__.py` 兼容面（`get_task_service` 惰性映射，全仓 0 生产调用方；删除属对外契约变更，按已批准例外保留） |
| `src/core/`、`src/analyzer.py`、`src/search_service.py` | 应用编排、领域规则、外部适配分别落位 | 不把巨型文件原样放入 `application/engine/` 后宣称分层完成。**已完成（2026-10-29~30，R3-S1~S15b）**：`src/core/` 9 件全部归位（domain 5 / application 4），仓库层面目录清零；`src/analyzer.py`→`application/analysis/analyzer.py`、`src/search_service.py`→`application/intelligence/search_service.py`（检索侧已 `SearchProviderPort` 端口化）；`src/core/pipeline.py`（3947 行）先经 S15a 解耦（domain 真源改指、`ImageRenderPort` 转图、私有访问清零），再经 S15b 取数端口化后整体搬入 `application/analysis/pipeline.py` |
| `src/schemas/` | 按用途分别放 domain/application；`api/v1/schemas/` 留在 API | Pydantic 本身不是判据；看类型服务于业务语义还是 HTTP 响应。**已完成（2026-10-29，R3-S2~S4）**：10 件按用途下沉 domain 9 / application 1，`__init__.py` 经全仓 grep 确认零 barrel 消费方后删除，目录已不存在 |
| `src/llm/`、`src/agent/` | 生成/运行时实现进入 infrastructure；Agent 用例进入 application | 已有 `GenerationBackend(Protocol)` 先评估复用，防止两套契约。**`src/llm/` 已完成（2026-10-28，R2-A1~A4）**：契约（ports/catalog）落 application、纯规则落 domain、7 个实现文件物理迁入 `src/infrastructure/generation/`，目录已删除、无 shim 残留。**`src/agent/` 已完成（2026-10-29，R1-A1~A7）**：56 件按落点全部迁入 `application/agent/`（用例/编排/skills/strategies/tools，`litellm_route_resolution` 经 R1-Q1 拍板偏离 §4.2）、`application/alert/`（`events`，实时取数经 `RealtimeQuotePort` 端口化）、`infrastructure/agent_runtime/`（Codex/LLM 适配簇）、`bootstrap/agent.py`（executor builder），目录已删除、无 shim 残留 |
| `src/notification*.py`、`src/notification_sender/` | 应用通知意图 + 基础设施路由/发送 | 单个渠道失败的隔离语义保持。**通知簇已完成（2026-10-29，R2-B1~B6 整簇收官）**：`NotificationService` 已从 14-mixin 多重继承解为组合 + `NotificationSendPort` 端口（B3），`notification.py` 落 `src/application/notification/`；逐渠道 sender（原 17 件）已物理迁入 `src/infrastructure/notification/senders/`（B5），纯规则/常量（`contracts`/`routing`/`endpoints`/`limits`）下沉 `src/domain/notification/`；`bot` 回执经 `ReplyClient` 窄端口解耦（B4），默认发送端口经 bootstrap seam（`configure_notification_send_port`）在 `main.py`/`api_lifecycle.py` 装配；目录 `src/notification_sender/` 已删除、无 shim 残留（`_send_dingtalk_chunked` 归属 R2-Q9 仍随 `custom_webhook_sender` 保留，作独立小片）。详见 `documents/framework/refactoring/ARCHITECTURE_MIGRATION_PROGRESS.md` §0.111~§0.116 与 `documents/framework/refactoring/src_migration_index.md` R2 段 |
| `src/md2img.py`、`src/feishu_doc.py`、报告模板 | 技术输出进入 infrastructure/reporting；`templates/` 原位 | 报告结构与渲染契约测试、下游通知消费同步。**已完成（2026-10-29~30）**：`src/feishu_doc.py`→`infrastructure/reporting/feishu_doc.py`（R3-S5b）、`src/md2img.py`→`infrastructure/reporting/img_render.py` 并补 `ImageRenderPort` 端口（R3-S11），`templates/` 原位 |
| `src/auth.py`、`src/data/`、`src/patches/`、`src/brokers/`、`src/utils/` | 按实际职责归位；可跨期保留旧模块 | 不为了删除旧目录造泛化 `utils` 容器。**终态（2026-10-30）**：`auth.py` 按 D-06 默认落法 A 列已批准例外（`api/` 6 处直接引用 + 中间件职责），`src/data/`(3)、`src/patches/`(2)、`src/brokers/`(1)、`src/utils/`(8) 按本条原位保留 |
| `api/`、`bot/` | 原位 | 全量盘点端点/命令对 storage、Repository、provider 的直接访问，逐用例净化 |

历史盘点曾发现 history / usage / watchlist / backtest 直连 storage，以及 kline / sector / limit_pool 直连 data_provider；这些是迁移前的风险示例，不能作为当前待办。后续新增或调整用例时仍须检查完整调用链，当前落点及完成证据见 [迁移索引](./src_migration_index.md) 与 [实施流水](./ARCHITECTURE_MIGRATION_PROGRESS.md)。

### 4.1 `src/services/` 的候选业务域

下表保留迁移前的文件级业务域盘点，文件名不代表仍位于 `src/services/`；该目录当前仅保留兼容入口。表中的候选归属须结合 §4 当前状态、§4.5 已批准例外与实际代码阅读，不再作为待搬迁清单。

| 原盘点业务域 | 历史文件名与当前边界说明 |
| --- | --- |
| `application/analysis/` | `analysis_service.py`、`analyzer_service.py`、`analysis_context_builder.py`、`alphasift_service.py`、`eod_picker_service.py`、`analyzer.py`（A3 自 `src/analyzer.py` 直搬，LLM 外部调用簇经 `AnalyzerLLMPort` 端口化） |
| `application/backtest/` | `backtest_service.py` |
| `application/decision/` | `decision_signal_service.py`、`decision_signal_extractor.py`、`decision_signal_outcome_service.py`、`decision_signal_reassess_service.py`、`signal_scanner_service.py`、`skill_opinion_outcome_service.py`、`skill_opinion_sample_service.py` |
| `application/portfolio/` | `portfolio_service.py`、`portfolio_risk_service.py`、`portfolio_import_service.py`、`portfolio_alerts.py` |
| `application/alert/` | `alert_service.py`、`alert_worker.py`、`notification_diagnostics.py` |
| `application/market/` | `market_light_service.py`、`market_light_alerts.py`、`market_hotspot_service.py`、`market_structure_service.py`、`daily_market_context.py` |
| `application/history/` | `history_service.py`、`history_loader.py`、`history_comparison_service.py` |
| `application/intelligence/` | `intelligence_service.py`、`social_sentiment_service.py`、`search_service.py`；搜索外部调用已下沉 infrastructure，第二轮又拆出具体 adapters，见 §4.3 |
| `application/quote/` | `stock_service.py`、`stock_daily_window_resolver.py`、`stock_daily_start_resolver.py`、`stock_code_utils.py`、`name_to_code_resolver.py`、`stock_index_remote_service.py`、`stock_list_parser.py`、`intraday_timeline_service.py` |
| `application/runtime/` | `task_queue.py`、`task_service.py`、`runtime_scheduler.py`、`scheduler.py`（R3-S16 自根级 `src/scheduler.py` 下沉；纯函数 `normalize_schedule_times` 已单源化到 `src/domain/shared/schedule_times.py`）、`run_flow.py`、`run_diagnostics.py`、`system_config_service.py`、`agent_backend_status_service.py`、`generation_backend_status_service.py`、`agent_model_service.py` |
| `application/reporting/` | `report_renderer.py` 已落位；通知报告内容另由 `analysis_report_renderer.py` 负责，技术输出经基础设施适配器 |
| `application/quote/` | `import_parser.py` 已落位，负责 CSV/Excel/剪贴板输入解析 |
| `application/analysis/` + `infrastructure/generation/` | `image_stock_extractor.py` 识别用例已落位；Vision 调用经 `vision_ports.py` 与 `vision_litellm.py` 分离，见 §4.3 |
| `domain/` 已落实归属 | `analysis/scanner_indicators.py`、`alert/alert_indicators.py`、`decision/decision_signal_summary.py`、`decision/decision_signal_data_quality.py`、`decision/decision_profile_policy.py`、`market/market_symbol_utils.py` |

迁移阶段的 A / SA / R2 / R3 各片过程与当时待办保留在 [实施流水](./ARCHITECTURE_MIGRATION_PROGRESS.md)。当前 `src/core/` 已归零，分析、流水线、搜索与通知协调入口已落 application；领域规则和外部调用已分别按边界提取。第二轮进一步拆分提示词、解析、结果后处理、上下文增强、报告交付与搜索适配器，具体决定见 [大文件拆分交接](./ARCHITECTURE_TARGET_LARGE_FILE_REFACTORING.md)。结果后处理仍可由 application 协调，不把“所有纯函数必须进入 domain”作为新增验收条件。

### 4.2 Agent、Provider 与辅助模块的落点

- 原 `src/agent/` 已完成迁移：用例、skills、strategies、tools 落 `src/application/agent/`，Codex/LLM/进程与传输实现落 `src/infrastructure/agent_runtime/`；`litellm_route_resolution` 按 R1-Q1 已决边界保留在 application，不能依据初稿候选再次搬迁。具体文件见迁移索引。
- `data_provider/` 已决原位保留；应用层仅经端口消费，不再等待是否物理迁包的确认。未来如需改变此决策，应单独评估优先级、超时、fallback、标准化、缓存与全部调用方，并同步 ADR。
- `src/utils/`、`src/data/`、`src/patches/` 的“技术/领域”归属不能只看原目录名。实际被多个层消费的纯函数可保留在经验证的共享模块；不要求为了清空旧目录新建无边界的 `shared/utils.py`。

### 4.3 文件内部代码拆分指引

**本方案不仅调整文件位置，还要求按职责整理文件内部的类、函数与副作用。**对同时承担两种以上职责的文件，不能仅修改 import 路径或把整个文件移入新目录后宣称完成分层。反过来，职责清晰的文件不因体积大就必须拆开；行数、文件数和目录对称性都不是拆分依据。

按下面的顺序判断一个文件是否需要拆分：

1. 列出现有对外入口、调用方和可观察契约：参数/返回值、异常、配置优先级、数据库写入、缓存、日志、调度及通知行为。先用现有测试或针对真实入口的特征测试锁定行为。
2. 给文件内各段代码标记职责：业务规则与纯计算归 `domain`；一次用例的流程、校验与协作归 `application`；数据库、网络、LLM、文件/模板、SDK 等实现归 `infrastructure`；HTTP/Bot 请求解析和响应映射留在 `api`/`bot`；实例创建及启动/关闭归 `bootstrap`。按**实际依赖和副作用**判断，不按函数名或“是否纯函数”机械分类。
3. 以一个可独立验证的业务切片为单位提取代码，先确定调用方向、共享数据契约和事务/资源所有权，再移动实现；避免复制旧逻辑、引入同义端口或保留两套长期并行的实现。必要的临时兼容层须标明调用方与移除条件。
4. 每次拆分后同时检查原入口、下游消费方、测试、导入路径、Docker/Desktop 打包和文档；验证通过后再处理下一处耦合。不得用 mock 掉实际风险层的测试代替端到端契约检查。

| 高优先级文件/文件组 | 内部拆分方向 | 必须守住的行为 |
| --- | --- | --- |
| `src/storage.py` | ORM Base/模型、engine/session、仓储、schema 升级与启动调用分开 | 模型注册、已有库升级、事务、索引和 SQLite 本地数据 |
| `src/config.py`、`src/core/config_manager.py`、`src/core/config_registry.py` | 运行时读取、字段/默认值定义、`.env` 编辑、密钥处理分开 | 默认值和优先级、热更新、脱敏、各入口取值一致 |
| `src/application/analysis/analyzer.py`、`pipeline.py`（原根级 analyzer / core pipeline） | 已完成：行情与生成调用经既有端口；筹码、提示词清洗和决策稳定性规则落 domain；第二轮拆出 `response_parser.py`、`result_policy.py`、`context_enrichment.py`、`agent_result_mapper.py` 与报告交付协作者。分析路由、并发、缓存及持久化协调留在原入口 | 分析顺序、失败降级、报告/决策输出 |
| `src/application/intelligence/search_service.py`、`src/application/analysis/image_stock_extractor.py` | 已完成：搜索经 `SearchProviderPort`，`infrastructure/search/providers.py` 现仅负责公共导出与有序工厂，具体实现位于 `provider_base.py` 与 7 个 `adapters/*.py`。图片识别经 `VisionCompletionPort` 调用 `infrastructure/generation/vision_litellm.py` 的 `LitellmVisionAdapter`；`bootstrap/analysis.py` 在 CLI、API 生命周期及测试会话装配。模型/Key 选择、Prompt、重试和结果解析仍由识别用例负责 | 超时、重试、结果归一及错误语义；不宣称真实外部 Vision 服务已验收 |
| `src/application/notification/notification.py`、`src/application/reporting/`、`src/infrastructure/notification/senders/` | 已完成：通知意图与渠道发送通过组合和 `NotificationSendPort` 分离，图片输出经 `ImageRenderPort`；第二轮已将报告内容渲染提取到 `analysis_report_renderer.py`，原通知入口保留渠道、发送端口及噪声控制 | 报告结构、渠道失败隔离、下游消费兼容 |
| `api/v1/endpoints/`、`bot/commands/` 中的混合入口 | 参数/权限/响应处理留在驱动层；业务流程提取到用例 | HTTP 状态码/Schema、Bot 命令及认证语义 |

此表只标出优先核查对象，不是预先判定每个函数的归属。P0 应形成“现有文件 → 具体职责 → 候选落点 → 调用方 → 验证证据”的文件级清单；P2–P4 在相关业务切片中完成必要拆分；P5 只收尾仍影响维护的剩余混合文件，不能把所有内部拆分推迟到最后。

### 4.4 服务端改造与 Web/Desktop 联动

**判断依据是对外契约，而不是服务端文件是否移动。**若只拆分 `src/` 内部实现，且 API 路径、请求/响应、错误、认证、任务事件、配置展示语义及静态服务方式均保持一致，Web 页面原则上不改；仍需运行对应契约测试和 Web 构建来证明一致。若这些可观察行为发生变化，必须在同一业务切片中完成服务端、Web、Desktop（如受影响）及文档联动。项目尚未上线，允许有计划地调整内部 API 契约，但不能留下前后端各自只支持半套新旧协议的中间状态。

| 服务端变化及实际触发条件 | Web 主要落点 | Desktop/其他联动与验收 |
| --- | --- | --- |
| `api/v1/endpoints/`、`api/v1/router.py` 改 URL、方法、查询参数、请求体或分页/排序语义 | `apps/hrs-web/src/api/<对应业务>.ts`；必要时 `src/utils/constants.ts`、`vite.config.ts` | 核对 Web 开发代理、部署反代与桌面端加载的同源 `/api` 路径；请求契约测试 |
| `api/v1/schemas/` 改字段、必填/可空、枚举、数值单位、时间格式或 snake_case/camelCase 映射 | `src/types/`、`src/api/utils.ts` 及对应业务 API；消费这些字段的 `src/hooks/`、`src/stores/`、`src/pages/` | 不能只让 TypeScript 编译通过；要用真实样例验证 UI 展示、过滤、排序和空态 |
| `src/services/`、应用用例或数据库改分析任务的 `200/202/409`、任务状态/轮询、运行流或 SSE 事件名/负载/重连语义 | `src/api/analysis.ts`、`src/types/analysis.ts`、`src/types/runFlow.ts`、`src/hooks/useTaskStream.ts`、`src/hooks/useRunFlowSnapshot.ts`、`src/stores/stockPoolStore.ts`；Agent 流另核对 `src/api/agent.ts` | 验证创建→进行中→完成/失败、重复提交、断线恢复及页面状态；不能只测单个事件解析函数 |
| 认证、Cookie、CORS、HTTP 状态码或错误体结构改变 | `src/api/index.ts`、`src/api/error.ts`、`src/api/auth.ts`、`src/stores/AuthStore.ts`、`src/hooks/useAuth.ts`、登录页 | 验证未登录、登录/登出、401 跳转、跨域/桌面同源请求；不以一律 Toast 代替业务错误处理 |
| 配置拆分导致配置字段、默认值、校验、脱敏、版本冲突或热更新语义改变 | `src/api/systemConfig.ts`、`src/types/systemConfig.ts`、`src/hooks/useSystemConfig.ts` 及设置页面；新增键同时检查 `.env.example` | 验证读取→编辑→校验→保存→刷新、400/409 冲突及秘密值不回显；更新专题文档 |
| 行情/K 线、持仓、决策信号、告警、报告载荷或展示语义改变 | 分别核对 `src/api/kline.ts`、`sectorData.ts`、`portfolio.ts`、`decisionSignals.ts`、`alerts.ts`、`history.ts`，以及对应 `src/types/`、hooks、store、页面和图表；路径缓存规则核对 `src/constants/cacheConfig.ts` | 验证金额/比例/日期、空数据和失败降级；报告/页面可见变化按仓库规则附可视证据 |
| 服务启动、静态资源挂载、健康检查、后端可执行文件及运行时数据路径改变 | `src/utils/constants.ts`、`vite.config.ts`、构建输出与 `/api` 请求；页面代码仅在真实行为变化时改 | `apps/hrs-desktop/main.js`、`package.json`、`tests/main.test.js`，以及后端打包脚本和 Docker；核对启动参数、`/api/health`、本地数据库/日志、Web 资源加载 |

上表中的 `src/...` Web 路径均相对于 `apps/hrs-web/`。它是**触发条件到现有代码落点的核查表**，不是要求所有列出的文件都改动。具体切片从服务端 endpoint/schema 出发，追踪到 Web API 适配层、类型、状态、页面和测试；若确认接口及语义不变，记录“不需前端代码修改”的证据即可。不要为了服务端分层顺手重构前端目录或视觉组件，也不要把后端 ORM 模型直接暴露给 Web：HTTP Schema 仍是双方契约边界。

联动验收至少包括对应后端 API/Schema 测试、`apps/hrs-web` 的相关测试与 `npm run lint`/`npm run build`；涉及登录、SSE、轮询、配置编辑或报告渲染时，补一次真实后端与 Web 的端到端操作。若影响桌面启动/静态资源，还需先构建 Web、再验证 Electron 测试与打包/启动链路。未执行的跨平台或在线验证应在交付说明中明示，不因后端单元测试通过就宣称前端兼容。

### 4.5 未迁移面文件级索引（§4.3 结尾要求的 P0 清单，2026-10-28 补齐；2026-10-30 终态：0 件待迁移）

§4.3 结尾要求 P0 形成「现有文件 → 具体职责 → 候选落点 → 调用方 → 验证证据」的文件级清单。该清单的**落点与切片归属**部分已入库 `documents/framework/refactoring/src_migration_index.md`，作为多会话并行时「一个文件只允许一个负责切片」的归属唯一真源；后续切片开工前先查该表，改动落点或补齐缺口须同步更新它。

**终态（2026-10-30，R3-S16 收官）：待迁移件 0。** 下列留存项不是待迁移面，而是已批准例外、兼容面与按 §4 目标表原位保留的模块：

| 留存项 | 实测件数 | 性质 |
| --- | --- | --- |
| 根级 `src/*.py` | 4 | `__init__.py` 空文件、`auth.py`（D-06 落法 A 例外）、`storage.py`/`webui_frontend.py`（已批准例外） |
| `src/services/__init__.py` | 1 | 兼容面：`get_task_service` 惰性映射，全仓 0 生产调用方 |
| `src/utils/`、`src/data/`、`src/patches/`、`src/brokers/` | 8 / 3 / 2 / 1 | §4 目标表列为「可跨期保留旧模块」，不为清空目录造泛化容器 |
| `data_provider/` | 原位保留 | §4 目标表「可原位保留为基础设施适配包」；应用层只经端口访问，守卫已禁止 application → `data_provider` |

**例外与移除前置条件**（2026-10-30 成文，详见 `documents/framework/architecture_migration_adr.md` ADR-002~ADR-006）：上述留存项均为**已登记的例外而非被遗忘的待迁移面**，各自的移除条件如下：`src/services/__init__.py` 兼容面（ADR-006）—— 全仓生产调用方实测 0（`bot/commands/analyze.py:81` 已直接 import `src.application.runtime.task_service`），但 `scripts/build-backend-macos.sh:94` 与 `scripts/build-backend.ps1:110` 的 PyInstaller hidden-import 仍列 `src.services`，删除需同时改两处并跑桌面端打包验证，故按既有决策（`.claude/reviews/decisions-2026-10-28-r2a.md`）**保留为兼容面**；`storage.py` 门面（ADR-004）—— 消费方全部改走仓储端口后可删除；`auth.py`（ADR-005）—— 认证/Cookie/CORS 基线已建立，继续按 ADR-005 保留；仅在多用户/OAuth、跨进程会话或部署单元拆分等前提变化时重新评估（§9.2.1-5）；`utils`/`data`/`patches`/`brokers` 四簇（ADR-003）—— 不为清空目录造泛化容器，可长期保留。

已归零簇：`src/core/`（9 → 0）、`src/schemas/`（10 → 0，目录已删）、`src/agent/`（56 → 0，目录已删）、`src/notification_sender/`（17 → 0，目录已删）、`src/repositories/`、`src/llm/`（均 → 0，目录已删）。**磁盘层面复核（2026-10-30）**：`src/repositories/` 空目录已删；构建残留 `src/UNKNOWN.egg-info/`（4 件，已被 `.gitignore:38 *.egg-info/` 忽略且 `top_level.txt` 仍列旧模块名）已清除；`src/core/` 仅余 git-ignored 的 `__pycache__/*.pyc`，实测子模块导入均报 `ModuleNotFoundError`（`src.core` 仅作为 PEP 420 空命名空间包解析，无任何属性，不产生行为风险）。

守卫复核（2026-10-30）：`scripts/architecture_baseline.json` 的 `entries` 仍为 `[]`（无任何历史豁免）；`src/core/`、`src/services/` 两条规则在目录归零、仅余兼容面后**刻意保留**为 tombstone——若未来有人在旧路径重新落业务实现，规则立即生效，不必等下一次架构评审；`src/schemas/`、`src/agent/`、`src/llm/`、`src/repositories/` 无专门规则，由 `src/` 兜底规则（禁 `api.`/`bot.`）覆盖，属预期。

**历史基线**（2026-10-28 初版剩余面 113 件，已全部完成；原口径为 R2-B1 删除死码 `src/notification_capabilities.py`、R2-B2 下沉 `notification_contracts`/`notification_routing` 并删垫片、抽 sender endpoint 到 `domain/notification/endpoints.py`）：

| 簇 | 件数 | 主要落点 | 负责切片 |
| --- | --- | --- | --- |
| 根级遗留 `src/*.py` | 22 | domain / application / infrastructure 三类 + 4 件保留原位（`auth`/`storage`/`webui_frontend` 与空 `__init__.py`）；R2-B2 已完成并删垫片的 2 件已移出 | R2-B2（已完成）；R3-S1、S2、S3、S5、S6 |
| `src/core/` | 9 | domain 5、application 4（`pipeline.py` 3922 行为最大件） | R3-S1、S4、S6 |
| `src/schemas/` | 10 | ✅ **已全部下沉并删除目录**：domain（context_pack/action/profile/scale/light/structure/bot_message/flow_snapshot）+ application（report_schema）；`__init__.py` 已删（R3-S2/S2b/S3b/S4） | R3-S2/S2b/S3b/S4（已收官） |
| `src/notification_sender/` | 16 | `infrastructure/notification/`（包级判定，「搬 or 保留原位」待拍板） | R2-B4、B5（endpoint 纯规则已由 B2 抽出） |
| `src/agent/` | 56 | `application/agent/**` 为主，Codex/LLM 适配簇进 `infrastructure/agent_runtime/` | R1-A1~A7 |

已知跨 Epic 硬约束（**已于 R1-A4/A5 解除**，保留作历史记录）：R2-A4 搬包后 `src/agent/` 5 个文件共 8 条 import 指向 `src.infrastructure.generation`，其中 3 条（`runner`/`chat_context`/`provider_trace`）所在文件的目标落点是 `application/agent/`，直接搬入会产生 3 条 `application → infrastructure` 禁入违规。

## 5. 数据库与配置决策

### 5.1 数据库

当前 ORM Base、模型、会话与仓储已落 `src/infrastructure/persistence/`；`src/storage.py` 按已批准例外保留 `DatabaseManager` 门面，启动时创建缺失表后调用 `schema_compat.py::apply_startup_migrations()`。schema 演进已由 ADR-008 定稿：维持 `create_all()` + 幂等迁移链，不引入平行版本化迁移框架。`create_all()` 不负责已有表结构升级；模型注册、迁移顺序和单一 metadata 必须保持。

事务边界按一次请求或一次后台任务中的**逻辑操作**确定；一个用例需要原子更新多个仓储时，由用例边界控制提交/回滚，仓储不各自提交。会话由入口装配并在任务结束时释放，不跨并发请求、线程或异步任务共享同一 Session。长时间的抓取/LLM 调用不持有数据库事务；具体并发与 SQLite 锁行为以实际测试确认。

现有开发库与 Desktop 本地库沿用“保留 + 备份重建”的已决路线，详见 §9.2.1 与 ADR-008；这不授权删除当前本地数据。破坏性变更前仍须确认备份与恢复步骤，现有幂等兼容升级只有在历史输入状态不再需要且决策同步后才能移除。

### 5.2 配置

当前 `src/config/` 已区分 `settings.py` 运行值、`field_definitions.py` / `registry.py` 字段元数据、`env_file.py` 环境文件编辑及相关解析模块；系统配置用例的探测、通知试发、诊断脱敏和校验又经第二轮拆分。统一加载入口与声明文件按专项评估保留，不因行数多继续强拆。后续变更仍须锁定默认值、优先级、热更新、密钥处理和脱敏契约；路径变动联动 CLI、API、Bot、Docker、Actions 与 Desktop，新增键同步 `.env.example` 及说明。

## 6. 实施顺序与交付单位

以**一条可独立验证的业务能力或边界**为 PR 单位；不采用“一文件一 PR”。项目未上线，允许在同一原子变更中全仓更新内部 import，不把包级 shim 当作通用兼容机制。`src/services/__init__.py` 不能代替 `src.services.history_service` 等子模块，`src/__init__.py` 也不能代替 `src.agent.tools.execution`。若确需跨 PR 兼容，每一个旧子模块都要明确调用者、期限和删除条件。

| 阶段 | 工作 | 可交付验收 |
| --- | --- | --- |
| P0 事实与契约 | 记录 API/Bot/应用跨层 import、所有启动入口、数据库与数据源行为、CI/构建脚本路径；盘点高耦合文件内部职责；为架构检查加入真实依赖和执行命令 | 形成依赖基线、文件级职责/调用方清单、运行矩阵、旧/新数据库测试策略；守卫在 CI 可执行 |
| P1 共享装配 | 在 `src/bootstrap/` 建立共享生命周期；逐个让 `main.py`、`server.py`、`webui.py` 使用；区分 CLI 调度与 FastAPI lifespan 所有权 | 三入口 smoke；`server:app` 与 `api.app:app` 等现有导入路径可用；仅由预期进程启动后台任务，关闭时正确释放 |
| P2 配置与持久化 | 在 `src/` 内原子转换配置包、拆分 ORM Base/模型/session；选择数据库保留或备份重建路径 | 运行配置契约、新库 schema、旧库路径、索引、事务、密钥脱敏检查 |
| P3 纵向用例 | 按行情/K 线、历史/分析、持仓、决策/告警等完整切片，使 API/Bot 调用应用用例；按消费需求新增端口；每片按第 4.4 节核对 Web/Desktop 联动 | 对应 API 契约、Bot 命令、测试与前端客户端一致；若前端不改须记录契约不变的证据；直连数持续下降 |
| P4 外部适配 | 分数据源、LLM/搜索、通知/报告、Agent 运行时收敛依赖；仅在有明确收益时迁移 `data_provider/` 物理路径；守住现有 fallback 和失败隔离 | 适配器契约、离线异常路径、单源失败、通知失败、构建 smoke 通过 |
| P5 收口 | 收尾仍混合职责且影响维护的文件；清理确无引用的旧模块；收紧 import 守卫、同步 ADR 和专题文档 | 禁止逆向依赖；每个入口、Docker 和平台打包验证；旧模块路径引用归零或列明例外 |

阶段可按依赖关系调整，具体 PR 可跨两个相邻阶段完成一个完整切片。不以“`src/` 不存在”“主入口低于某行数”作为硬验收条件。`src/` 和 `api/`、`bot/` 在最终结构中保留。

## 7. 验证与回滚

| 改动面 | 最低验证与联动 |
| --- | --- |
| Python | `./scripts/ci_gate.sh`；关键入口 smoke；新增端口与调用方实际契约测试 |
| API/Schema | 请求、响应、认证、错误码及轮询状态；Web 客户端的对应构建/测试 |
| 数据库 | 空库创建、已有开发库升级或备份重建、索引/约束、会话释放、迁移重复执行 |
| 数据源 | source 优先级、字段归一、timeout、retry、cache、fallback、网络失效 |
| 报告/通知 | 模板结构、Markdown/图像输出、渠道失败隔离；用户可见效果变化时附 PR 可视证据 |
| Desktop/发布 | 先 Web 构建，再后端打包（含 hidden imports）、Electron 构建、Docker smoke、相关 Actions |

需同步检查的已有路径：`scripts/ci_gate.sh`、`scripts/test.sh`、`scripts/check_env.py`、`scripts/build-backend-macos.sh`、`scripts/build-backend.ps1`、`scripts/codex_app_server_gate_a.py`、Docker 入口、`.github/workflows/ci.yml`、发布 workflow、`apps/hrs-desktop/`。这些文件保留当前目录和名称，仅在新模块路径影响运行时编辑。

每个 PR 明确：变更了哪条调用链、与上一状态相比的 API/DB/配置兼容影响、验证证据、未验证平台、风险和回滚步骤。代码移动 PR 可以回退提交；数据库数据变更不能仅靠 `git revert`，必须有备份和恢复步骤。执行前检查当时的工作区状态，保护其他人和其他任务的未提交改动；本文不把某一天的工作区状态当作永久事实。

<a id="8-方案通过前的确认点"></a>

## 8. 已确认约束与持续核对项

1. **数据库演进已决**：沿用 `create_all` 与幂等启动迁移链，不引入平行迁移框架（ADR-008）；开发库 / Desktop 本地库仍按保留、备份与恢复策略处理。删除历史迁移须另证历史输入不再需要。
2. **包边界已决**：`src` 继续是运行时包名，`data_provider/` 原位保留为适配边界。依赖倒置由端口和装配约束，不将物理搬包作为验收条件；若后续确需搬迁，单独覆盖全部消费者及打包路径。
3. **架构守卫已实施**：`scripts/check_architecture.py --check` 已进入 `scripts/ci_gate.sh` 和 CI 后端门禁；现有基线为空，不通过增加豁免掩盖新违规。
4. **全仓目录范围已决**：Web、Desktop、脚本、文档和本机资产按已确认范围保留。各自进一步重构需要明确的问题及验收范围。
5. **治理规则仍以 AGENTS.md 为准**：本文件是目标约束及实施索引，不是另一份开发流程真源。涉及协作治理资产调整时同步镜像并运行 `python scripts/check_ai_assets.py`。

初稿阶段的“仅文档、尚未修改代码”已不代表现状。服务端实现与专项整理已经落地；当前仍需完成的验收，以 §0 的状态入口和最新实测记录为准。

## 9. 跨模型与 Agent 的实施交接

本节供未参与前期讨论的开发者、其他模型或 Agent **独立接手**。无需先读取聊天记录；先读仓库根目录 `AGENTS.md` 和本文，再核对当前代码、测试、脚本、工作流及 Git 状态。`AGENTS.md` 约束当前开发流程，本文提供目标约束与实施证据索引；两者都不能替代实际代码和验证证据。本文中的文件数量、路径盘点和 2026-10-23 基线会过期，不能作为当前工作树事实直接执行。

### 9.1 已确认的意图与边界

- 仓库根目录为 `HermesX/`，保留现有可导入包 `src`，在其内部按 `domain / application / infrastructure / bootstrap / config` 分层；**不**改成 `src/hermesx/`。目录图是候选结构，不要求创建空目录，也不是批量移动清单。
- 本次以服务端职责、依赖和多入口装配为主；混合职责的 `.py` 文件需要拆分**内部代码**，不能仅移动文件。每个切片以第 4.3 节的行为契约、调用方向和实际验证为准。
- Web、Desktop、Bot、脚本、Docker、CI 和文档按第 4.4 节及第 7 节联动；只有对外契约或启动/打包行为改变时才改相应客户端，不借服务端改造重排前端目录。
- 项目尚未上线，内部路径和 schema 可有计划地调整；但现有本地数据库、密钥、日志、报告、原型和各类本机文件仍须保留。先确认目标和备份/恢复方案，不能把“尚未上线”解释为允许直接删库或清理资产。`src/UNKNOWN.egg-info/` 仅是可在实施时核实清理的构建残留，不是现在要执行的删除指令。
- `data_provider/` 已决原位保留为基础设施例外，新能力适配层可落 `src/infrastructure/providers/`；应用层只经端口访问。未来物理迁包属于另行评估的架构变更，不是当前未完成项。
- 不经用户明确确认，不执行 `git commit`、`git tag`、`git push`；不覆盖其他任务的改动。其他具体协作规则以当前 `AGENTS.md` 为准。

<a id="92-尚未决定接手者不得自行当成既定结论"></a>

### 9.2 架构决策与历史待确认项

> **状态回写（2026-10-30，第一批收口）**：下列 5 项中 **2/3/4 已由实施过程中的既成事实与已确认决策定稿**，转为「9.2.1 已决」。
> **状态回写（2026-10-31，W6/W7 切片）**：**1 与 5 已收口**——1 按保守路线定稿（schema 维持 `create_all` + 幂等迁移链、不引入版本化框架，现有开发库/Desktop 库采用保留 + 备份重建，见 ADR-008）；5 已建立认证/Cookie/CORS 防护清单与性能/启动基线。至此下列 5 项**全部转为「9.2.1 已决」**。

#### 9.2.1 已决（依据与证据）

| 原编号 | 结论 | 依据 |
| --- | --- | --- |
| 1 | 现有开发库与 Desktop 本地 SQLite **采用「保留 + 备份重建」**：维持 `Base.metadata.create_all()` + `apply_startup_migrations()` 幂等链（15 个 `ensure_*`/`backfill_*`），不引入 Alembic 等版本化框架；非 `_ensure_*` 白名单的列不自动补回，破坏性变更时按备份重建，`CURRENT_SCHEMA_VERSION` 仅在破坏性重建时递增 | ADR-008；W1.4 旧库升级实测（24.8 MB 副本重跑幂等：表/索引/列/行数零变化，删表可自动重建，删非白名单列 14→13 不自动补回）；`tests/infrastructure/persistence/test_schema_migration_guard.py`（无孤儿迁移/顺序/`db_session` 首参/基线常量引用） |
| 2 | `data_provider/` **不物理迁入** `src/infrastructure/providers/`，保留原路径并明确登记为基础设施例外；新能力适配层落 `src/infrastructure/providers/` | 本文 §4 目标表与 §4.5 留存项表已写明；守卫已禁止 `src/application` → `data_provider`；ADR-003 |
| 3 | 架构守卫采用仓内自研 `scripts/check_architecture.py`（静态 AST + 前缀首个匹配规则表），基线归零**已完成**：`scripts/architecture_baseline.json` 的 `entries` 为 `[]`，并由 `scripts/ci_gate.sh:11,17` 纳入 CI 阻断 | R3 收口守卫复核（本文 §4.5）；`tests/tooling/scripts/test_check_architecture.py` 合成工作区自测 |
| 4 | 本轮进程模型按**单进程假设**执行：任务队列/SSE 订阅者/调度器的进程内状态不做跨进程去重与送达保证；水平扩展属单独设计，不在迁移范围 | `documents/framework/refactoring/ARCHITECTURE_MIGRATION_PROGRESS.md` §1 已确认决策 **D5**；入口与调度所有权见同文件 §2 运行矩阵 |
| 5 | **认证/Cookie/CORS 防护清单与性能/启动基线已建立**，据此维持 `src/auth.py` 落法 A（不端口化） | `documents/framework/security_performance_baseline.md`（认证/Cookie/CORS 取证、实测耗时与验收阈值）；`tests/infrastructure/security/test_security_baseline.py`（15 条不变量）、`scripts/measure_performance_baseline.py`（可复现基线）；ADR-005 复核结论 |

1. 【已决 → 见 9.2.1】现有开发库与 Desktop 本地 SQLite 的保留、备份重建或版本化迁移路径（第 5.1、8 节）。
2. 【已决 → 见 9.2.1】`data_provider/` 是否实际迁入 `src/infrastructure/providers/`，以及相应 ADR、Docker、PyInstaller 和全仓 import 的同步范围（第 8 节）。
3. 【已决 → 见 9.2.1】架构守卫采用何种实际可执行工具，以及 P0 违规基线如何逐步归零（第 8 节）。
4. 【已决 → 见 9.2.1】目标部署进程模型：当前任务队列/SSE 订阅者和调度器有进程内状态；在确认单进程运行还是支持多 worker/多实例前，不得声称共享 bootstrap 已解决跨进程任务归属、去重与事件送达。需先给出运行约束或单独设计。
5. 【已决 → 见 9.2.1】对公网/桌面两种运行场景的认证、Cookie、CORS 与修改类请求防护，以及性能/启动时间的基线和验收阈值（已记录于 `documents/framework/security_performance_baseline.md`）。

上述五项已决，不再作为接手前待确认问题。未来若需改变决策，应列出选项、现状证据、影响面和建议，按当前授权范围推进。后续有明确决策时同步更新本文与对应 ADR，避免只留在聊天记录里。

### 9.3 每个切片的交接流程与记录格式

接手时先记录当前分支/HEAD、工作区状态、已完成阶段与最新测试结果；先从当前总览选择未完成的验收或后续演进事项；P0 的文件级职责/调用方清单是历史基线，复核适用性后再使用。对照当前代码确认本文列出的旧路径仍存在，再实施、验证和交接。不要把前一个 Agent 的“已完成”口头结论当作测试证据，也不要因为某个目录已经出现就认定分层已经完成。

每个切片结束时，在对应 PR 描述中记录以下内容，并沿用 [ARCHITECTURE_MIGRATION_PROGRESS.md](./ARCHITECTURE_MIGRATION_PROGRESS.md) 追加实施记录；测试专项同步测试台账，不另建同义进度清单：

```text
阶段/切片：P?；业务能力与本次边界
代码基线：分支、HEAD、开始时工作区状态；是否有其他任务改动
已完成：旧职责 → 新职责/路径；对外行为是否变化
契约联动：API/Bot/Web/Desktop/配置/数据库/脚本/文档中实际检查或修改的部分
决策记录：已确认的选择、依据；仍待用户确认的问题
验证证据：运行命令与结果；真实入口/旧库/打包等关键路径；未运行项及原因
风险与回滚：已知问题、数据恢复方式、临时兼容层的调用者与移除条件
下一步：下一个最小切片、前置条件；若受阻，明确阻塞点
```

交接记录只写可核对的事实，不写“全部完成”“完全兼容”等无证据结论。若某阶段改变了目录决策、估算或验收标准，应更新本文；若改变了仓库协作规则，则按 `AGENTS.md` 的治理流程同步。最终收口以第 6–7 节的运行、契约、打包和回滚验收为准，不以某个 Agent 的会话结束为准。

## 10. 参考依据

- [FastAPI：多文件应用与 APIRouter](https://fastapi.tiangolo.com/tutorial/bigger-applications/)；[Lifespan 生命周期](https://fastapi.tiangolo.com/advanced/events/)——支持拆分入口与集中管理启动/关闭，但不规定本文这套目录命名。
- [Python Packaging Guide：src layout 与 flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)——用于区分本项目现有的 `src` 包名与标准 src layout。
- [SQLAlchemy：Session 生命周期与事务边界](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)；[MetaData.create_all](https://docs.sqlalchemy.org/en/20/core/metadata.html)；[Alembic：自动生成迁移](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)——用于限定持久化拆分与 schema 演进的职责。
