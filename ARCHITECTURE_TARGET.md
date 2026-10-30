# HermesX 全仓目标架构与服务端改造方案（草案 v3）

| 项目 | 约定 |
| --- | --- |
| 状态 | 待评审；本文是目标设计和实施顺序，不表示代码已迁移 |
| 仓库根目录 | `HermesX/`；沿用现有可导入的 Python 包 `src`，不增加 `src/hermesx/` |
| 主要改造范围 | `src/`、`api/`、`bot/`、`data_provider/`、根目录 Python 入口和相应测试 |
| 联动范围 | 当导入路径或契约变化时，同步修改 Web、Desktop、脚本、Docker、CI、文档 |
| 现有资产 | 原位保留；不因本方案执行无关的目录归档、清理或忽略规则变更 |
| 预计改动文件数 | **约 300–450 个**（`data_provider/` 保留原路径）；若整体迁入 `src/infrastructure/providers/`，约 **400–550 个** |
| 预计 AI token 消耗 | 完成 P0–P5 约 **150万–350万 token**；若整体迁移数据源包、前端契约联动较多，约 **200万–450万 token**；均为跨多个实施迭代的输入+输出粗估，不是单次对话额度或费用承诺 |

估算口径：以 2026-10-23 工作树为基线，`src/`、`api/`、`bot/`、`data_provider/` 共约 352 个 Python 文件，`tests/` 约 270 个文件；约 497 个 Python 文件引用 `src` 或 `data_provider`（含服务端、测试与脚本，**不代表全部必改**）。改动文件数按全程实际触及的**去重逻辑文件**估计，包含代码、测试、Web/Desktop 必要联动、构建脚本和文档；一次移动按一个文件计，不把 Git diff 中的删除/新增算两次，不计生成物、本地数据或依赖目录。token 包含代码阅读、设计、修改、测试结果分析和返工；实际用量受每阶段范围、所用模型、上下文复用及验证轮次影响很大。P0 完成文件级职责/调用方清单后，应据此重估，不能把本区间当作进度或预算承诺。

> 本文以 2026-10-23 的工作树为参考。具体文件归属是设计候选，迁移时以调用关系、运行入口和测试证据复核。`ARCHITECTURE_TARGET.md` 位于仓库根目录。本文与现有 `documents/framework/backend_architecture_adr.md` 的目录落点不同：该 ADR 描述已落地的数据源能力及当时的路径，本方案经评审确定后，实施 PR 应同步修订其路径说明，不能让两份文档长期冲突。

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
       src.application.ports ◄──── src.infrastructure

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
├── ARCHITECTURE_TARGET.md                 本文档
├── README.md  LICENSE  SKILL.md           KEEP
├── .env.example  .gitignore  .gitattributes  .dockerignore  .python-version  KEEP
├── pyproject.toml  setup.cfg  requirements.txt  SYNC，必要时加入架构检查依赖
├── main.py  server.py  webui.py           REWORK，入口共享 src.bootstrap
├── start.sh                               SYNC，启动路径发生变化时
├── LOCAL_RUN_GUIDE.md                     KEEP
├── stock_data_view.md  数据源管理.md         KEEP
├── switch-node.js  switch-node.sh         KEEP
├── portfolio-redesign-prototype.html     KEEP，本地现有原型
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
│   │   ├── ports/                         按消费方需要定义仓储/行情/通知/生成/搜索端口
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
│   │   │   ├── schema_compat/             现有 _ensure_* 语义，若继续支持旧开发库
│   │   │   └── migrations/                上线前确认的版本化 schema 演进机制
│   │   ├── providers/                     数据源适配的首选目标；是否迁入见第 8 节
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
├── tests/                                 REWORK，随用例/模块迁移测试，不强制一次重排
│   ├── conftest.py  fixtures/  agent/  test_*.py  ...
│   └── 按需要逐步形成 domain/ application/ infrastructure/ api/ bot/
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

| 现有位置 | 候选落点 | 关键校核 |
| --- | --- | --- |
| `src/config.py`、`src/core/config_manager.py`、`config_registry.py` | `src/config/` | 运行值、默认值、UI 字段元数据、`.env` 编辑、密钥处理保持各自契约；`src/config.py` 与 `src/config/` 的替换须同一原子变更 |
| `src/storage.py` | `src/infrastructure/persistence/` | `Base` 唯一、模型注册先于建表、session 生命周期、索引/升级顺序不变；开发库重建另作明确决策。**已完成部分迁移（2026-10-28）**：ORM/模型/会话/仓储已下沉 `persistence`，本文件保留为 `DatabaseManager` 门面（单例 + 会话/事务入口 + 同名薄委托），**暂作为已批准例外保留在 `src/storage.py`** |
| `src/repositories/` | `src/infrastructure/persistence/repositories/` | 应用端口从真实用例所需方法定义；事务所有权明确。**已完成（2026-10-28，PP-1~PP-7）**：全部仓储下沉 infra 并由 `src/application/*/ports.py` 端口 + bootstrap 装配收敛，根目录在 git 中已无文件；守卫已把 `src.repositories` 列为 application 层禁入前缀 |
| `data_provider/` | 首选 `src/infrastructure/providers/`；可原位保留为基础设施适配包 | 优先隔离用例依赖；若迁移，保持 ADR-001 已验证的优先级、超时、降级、标准化和缓存行为，并同步全部入口与调用者。**当前决策（2026-10-30）：原位保留**——应用层一律经端口（`StockDataPort`/`MarketReviewDataPort`/`MarketDataPort`/`RealtimeQuotePort` 等）访问，守卫已把 `data_provider` 列为 application 层禁入前缀；未来若整体迁入 `infrastructure/providers/`，仍须守住上述行为 |
| `src/services/` | 多数进入 `src/application/<业务域>/`；纯业务规则才进入 domain | `import_parser.py` 等输入解析不因无网络就成为 domain；需检查调用图。**已完成（2026-10-29）**：具体实现已按业务域全部迁入 `src/application/`，本目录仅余 `__init__.py` 兼容面（`get_task_service` 惰性映射，全仓 0 生产调用方；删除属对外契约变更，按已批准例外保留） |
| `src/core/`、`src/analyzer.py`、`src/search_service.py` | 应用编排、领域规则、外部适配分别落位 | 不把巨型文件原样放入 `application/engine/` 后宣称分层完成。**已完成（2026-10-29~30，R3-S1~S15b）**：`src/core/` 9 件全部归位（domain 5 / application 4），仓库层面目录清零；`src/analyzer.py`→`application/analysis/analyzer.py`、`src/search_service.py`→`application/intelligence/search_service.py`（检索侧已 `SearchProviderPort` 端口化）；`src/core/pipeline.py`（3947 行）先经 S15a 解耦（domain 真源改指、`ImageRenderPort` 转图、私有访问清零），再经 S15b 取数端口化后整体搬入 `application/analysis/pipeline.py` |
| `src/schemas/` | 按用途分别放 domain/application；`api/v1/schemas/` 留在 API | Pydantic 本身不是判据；看类型服务于业务语义还是 HTTP 响应。**已完成（2026-10-29，R3-S2~S4）**：10 件按用途下沉 domain 9 / application 1，`__init__.py` 经全仓 grep 确认零 barrel 消费方后删除，目录已不存在 |
| `src/llm/`、`src/agent/` | 生成/运行时实现进入 infrastructure；Agent 用例进入 application | 已有 `GenerationBackend(Protocol)` 先评估复用，防止两套契约。**`src/llm/` 已完成（2026-10-28，R2-A1~A4）**：契约（ports/catalog）落 application、纯规则落 domain、7 个实现文件物理迁入 `src/infrastructure/generation/`，目录已删除、无 shim 残留。**`src/agent/` 已完成（2026-10-29，R1-A1~A7）**：56 件按落点全部迁入 `application/agent/`（用例/编排/skills/strategies/tools，`litellm_route_resolution` 经 R1-Q1 拍板偏离 §4.2）、`application/alert/`（`events`，实时取数经 `RealtimeQuotePort` 端口化）、`infrastructure/agent_runtime/`（Codex/LLM 适配簇）、`bootstrap/agent.py`（executor builder），目录已删除、无 shim 残留 |
| `src/notification*.py`、`src/notification_sender/` | 应用通知意图 + 基础设施路由/发送 | 单个渠道失败的隔离语义保持。**通知簇已完成（2026-10-29，R2-B1~B6 整簇收官）**：`NotificationService` 已从 14-mixin 多重继承解为组合 + `NotificationSendPort` 端口（B3），`notification.py` 落 `src/application/notification/`；逐渠道 sender（原 17 件）已物理迁入 `src/infrastructure/notification/senders/`（B5），纯规则/常量（`contracts`/`routing`/`endpoints`/`limits`）下沉 `src/domain/notification/`；`bot` 回执经 `ReplyClient` 窄端口解耦（B4），默认发送端口经 bootstrap seam（`configure_notification_send_port`）在 `main.py`/`api_lifecycle.py` 装配；目录 `src/notification_sender/` 已删除、无 shim 残留（`_send_dingtalk_chunked` 归属 R2-Q9 仍随 `custom_webhook_sender` 保留，作独立小片）。详见 `documents/framework/architecture_migration_progress.md` §0.111~§0.116 与 `documents/framework/src_migration_index.md` R2 段 |
| `src/md2img.py`、`src/feishu_doc.py`、报告模板 | 技术输出进入 infrastructure/reporting；`templates/` 原位 | 报告结构与渲染契约测试、下游通知消费同步。**已完成（2026-10-29~30）**：`src/feishu_doc.py`→`infrastructure/reporting/feishu_doc.py`（R3-S5b）、`src/md2img.py`→`infrastructure/reporting/img_render.py` 并补 `ImageRenderPort` 端口（R3-S11），`templates/` 原位 |
| `src/auth.py`、`src/data/`、`src/patches/`、`src/brokers/`、`src/utils/` | 按实际职责归位；可跨期保留旧模块 | 不为了删除旧目录造泛化 `utils` 容器。**终态（2026-10-30）**：`auth.py` 按 D-06 默认落法 A 列已批准例外（`api/` 6 处直接引用 + 中间件职责），`src/data/`(3)、`src/patches/`(2)、`src/brokers/`(1)、`src/utils/`(8) 按本条原位保留 |
| `api/`、`bot/` | 原位 | 全量盘点端点/命令对 storage、Repository、provider 的直接访问，逐用例净化 |

特别说明：API 穿透不仅是 `agent.py`。当前 `history.py`、`usage.py`、`watchlist.py`、`backtest.py` 直接引用 `src.storage`；`kline.py`、`sector.py`、`limit_pool.py` 直接引用 `data_provider`。P0 应以全仓扫描生成完整基线，而非把若干举例当成完整清单。

### 4.1 `src/services/` 的候选业务域

下表保留旧稿对现有服务文件的盘点价值。表中的文件名沿用**当前名称**，表示首选业务归属，不强迫统一改名；每一组迁移时检查其输入、输出、IO、副作用和调用方。若一个文件承担多种职责，先在原位拆清楚再分别归位。

| 目标业务域 | 当前文件（均位于 `src/services/`） |
| --- | --- |
| `application/analysis/` | `analysis_service.py`、`analyzer_service.py`、`analysis_context_builder.py`、`alphasift_service.py`、`eod_picker_service.py`、`analyzer.py`（A3 自 `src/analyzer.py` 直搬，LLM 外部调用簇经 `AnalyzerLLMPort` 端口化） |
| `application/backtest/` | `backtest_service.py` |
| `application/decision/` | `decision_signal_service.py`、`decision_signal_extractor.py`、`decision_signal_outcome_service.py`、`decision_signal_reassess_service.py`、`signal_scanner_service.py`、`skill_opinion_outcome_service.py`、`skill_opinion_sample_service.py` |
| `application/portfolio/` | `portfolio_service.py`、`portfolio_risk_service.py`、`portfolio_import_service.py`、`portfolio_alerts.py` |
| `application/alert/` | `alert_service.py`、`alert_worker.py`、`notification_diagnostics.py` |
| `application/market/` | `market_light_service.py`、`market_light_alerts.py`、`market_hotspot_service.py`、`market_structure_service.py`、`daily_market_context.py` |
| `application/history/` | `history_service.py`、`history_loader.py`、`history_comparison_service.py` |
| `application/intelligence/` | `intelligence_service.py`、`social_sentiment_service.py`、`search_service.py`（SA1 自 `src/search_service.py` 搬包过渡直搬，8 Provider 外部调用真拆分归后续独立 Epic） |
| `application/quote/` | `stock_service.py`、`stock_daily_window_resolver.py`、`stock_daily_start_resolver.py`、`stock_code_utils.py`、`name_to_code_resolver.py`、`stock_index_remote_service.py`、`stock_list_parser.py`、`intraday_timeline_service.py` |
| `application/runtime/` | `task_queue.py`、`task_service.py`、`runtime_scheduler.py`、`scheduler.py`（R3-S16 自根级 `src/scheduler.py` 下沉；纯函数 `normalize_schedule_times` 已单源化到 `src/domain/shared/schedule_times.py`）、`run_flow.py`、`run_diagnostics.py`、`system_config_service.py`、`agent_backend_status_service.py`、`generation_backend_status_service.py`、`agent_model_service.py` |
| `application/reporting/` 或 `infrastructure/reporting/` | `report_renderer.py`；按内容生成与具体渲染依赖拆分 |
| `application/quote/` 或 API 输入适配 | `import_parser.py`；解析 CSV/Excel/剪贴板的边界与名称解析用例分别处理 |
| `application/analysis/` 或 `infrastructure/generation/` | `image_stock_extractor.py`；业务提取流程与 Vision LLM 调用分别处理 |
| `domain/` 候选 | `scanner_indicators.py`、`alert_indicators.py`、`decision_signal_summary.py`、`decision_signal_data_quality.py`、`decision_profile_policy.py`、`market_symbol_utils.py`；逐一确认业务语义和依赖方向 |

`src/core/` 中的 `pipeline.py`、`market_review*.py` 倾向于应用编排；`backtest_engine.py`、`market_strategy.py`、`market_profile.py`、`skill_opinion_outcome_evaluator.py` 与 `trading_calendar.py` 需逐一检查可否成为纯领域模块。`src/analyzer.py`、`src/search_service.py`、`src/notification.py`、`src/config.py` 和 `src/core/config_registry.py` 是高耦合拆分对象；不能只移动文件就宣布完成。（`src/services/alphasift_service.py` 已于迁移 T5e 完成 §4.3 拆分整改并迁入 `src/application/analysis/alphasift_service.py`：外部调用下沉 `src/infrastructure/providers/hrs_alphasift_bridge.py` 与 `src/domain/analysis/`，经 `AlphaSiftRuntimePort` 端口化装配。`src/services/system_config_service.py` 已于迁移 T5f 完成 §4.3 拆分整改并迁入 `src/application/runtime/system_config_service.py`：外部调用（LLM 渠道探测/通知试发/单例重置）下沉 `src/infrastructure/providers/system_config_runtime.py`、URL 安全纯规则下沉 `src/domain/shared/url_security.py`，经 `ConfigProbePort`/`NotificationDispatchPort`/`RuntimeResetPort` 端口化装配。**迁移 N 线（通知 Epic）**：`src/notification.py` 已按 §4.1 L203 落点迁入 `src/application/notification/notification.py`（N1 搬包过渡：逐渠道发送实现暂留基础设施、`reports_dir` 的 `__file__` 深度推导已随搬包修正）；后续 **R2-B1~B6 整簇收官（2026-10-29）** 已完成彻底发送端口化与物理下沉：`NotificationService` 解除 14-mixin 多重继承、改为组合 + `NotificationSendPort`（B3）；逐渠道 sender（原 17 件）物理迁入 `src/infrastructure/notification/senders/`（B5），纯规则/常量（`contracts`/`routing`/`endpoints`/`limits`）下沉 `src/domain/notification/`（B2/B5）；`bot` 回执经 `ReplyClient` 窄端口解耦（B4），默认发送端口经 bootstrap seam（`configure_notification_send_port`）在 `main.py`/`api_lifecycle.py` 装配；`src/notification_sender/` 目录已删除、无 shim，§4.3 发送端口化已收敛（唯 `_send_dingtalk_chunked` 归属 R2-Q9 仍随 `custom_webhook_sender` 保留、作独立小片）。**迁移 A 线（analyzer Epic A2/A3）**：`src/analyzer.py` 已完成 LLM 外部调用簇端口化（`import litellm`/`Router` 构造/`litellm.completion`/no-proxy 成对补全/fallback 定价注册经新建 `AnalyzerLLMPort`（`src/application/analysis/analyzer_runtime_ports.py`）下沉 `src/infrastructure/providers/analyzer_runtime.py`、`bootstrap/analyzer.py` 双挂点装配）并迁入 `src/application/analysis/analyzer.py`（`AnalysisResult` DTO 与 `GeminiAnalyzer` 编排随迁，全仓 ~94 测试 + 16 生产 re-point、旧 `src.analyzer` 路径不留 shim）；死函数 `get_stock_name_multi_source`（唯一 `data_provider.base` 禁入项）经全仓无调用方核实后删除。此片属 **LLM 簇端口化 + 搬包**——analyzer 内 ~20 个决策稳定化纯函数（可独立测试业务计算）下沉 domain 尚未完成，§4.3 L254“用例编排与业务计算分开”未彻底收敛、不宣称完成。**迁移 SA 线（search Epic，搬包过渡片 SA1）**：`src/search_service.py` 已迁入 `src/application/intelligence/search_service.py`（搬包过渡，8 Provider 与网络工具暂留原文件）；唯一守卫禁入 `data_provider.us_index_mapping.is_us_index_code`（经核实为 `src/domain/market/us_index_symbols` 的薄再导出）改指真源，`SearchService` 内 4 处 `SearchService._x` 自类名私有接收按 §0.36 收口为 `cls.`（两静态方法转 classmethod），搬入 `application/` 后新暴露的 `BaseSearchProvider` 键位统计 `super()._record_success/_record_error`（`super()` 非裸 self/cls，触发 forbid_private_members，纠正 P1 勘察“随 Provider 下沉自消”之误判）按方式① 提升为公开 `record_*`；生产 11 + 测试 11 re-point、旧 `src.search_service` 路径不留 shim；顺带修复 `scripts/ci_gate.sh` 陈旧 `py_compile src/search_service.py` 路径（同 N1/A3 非 py 层盲区教训）。此片属**搬包过渡**——8 Provider（Tavily/SerpAPI/Bocha/Anspire/MiniMax/Brave/SearXNG）+ 模块级网络工具下沉 `src/infrastructure/search/`、经 `SearchProviderPort` 端口化并解 `isinstance(provider, ...)` 编排耦合**已由后续 SA2 Epic 完成**：SA2-1 契约层（`src/domain/search/` DTO + `SearchProviderPort`/`SearchOptions`）、SA2-2 解 `isinstance`（中性 `SearchOptions` 全量下发）、SA2-3a 就地构造抽为 `build_search_providers()` 装配接缝、SA2-3b Provider 本体+网络工具物理下沉 `src/infrastructure/search/providers.py` + bootstrap `configure_search`（main/api_lifecycle 双挂点）注册 provider-builder hook、`SearchService` 不再直接 import 具体 Provider（未装配优雅降级为空列表，测试沿用 analyzer 先例模块顶层 `configure_search()`）。§4.3 L255 检索用例与第三方搜索分开（search 侧）已收敛；image_stock_extractor 的 Vision LLM 拆分仍待处理。**迁移 R3-S1（2026-10-29，`src/core`/根级纯领域下沉首批）**：`backtest_engine.py`/`market_profile.py`/`market_strategy.py`/`enums.py`/`market_context.py` 经逐一 import 勘察确认均为零改动可下沉的纯领域模块（前者三件仅 stdlib+Protocol，`enums` 跨域枚举，`market_context` 仅引 `src.domain.market`），已 `git mv` 分落 `src/domain/{backtest/engine,market/profile,market/strategy,shared/enums,market/context}.py`、全仓 27 消费方 re-point、守卫/三步法 0 回归。`src/core` 余 `pipeline.py`/`market_review*.py`（S4/S6）与 `skill_opinion_outcome_evaluator.py`/`trading_calendar.py` 等仍待后续切片。**迁移 R3-S2（2026-10-29，`src/schemas` 干净子集下沉 domain）**：`analysis_context_pack.py`/`decision_action.py`/`decision_profile.py`/`decision_scale.py`/`market_light.py`/`market_structure.py` 六件经 domain 合法性勘察（依赖 `src.utils`/`src.report_language`/pydantic 均非守卫禁入）零改动 `git mv` 分落 `src/domain/{analysis/context_pack,decision/action,decision/profile,decision/scale,market/light,market/structure}.py`、42 消费方 re-point；因搬入后 `action`→`report_language`→`scale` 与包 `__init__` eager 聚合形成循环导入，将 `src/domain/decision/__init__.py` 由 eager barrel 改为 PEP 562 惰性 `__getattr__`（经核实零外部 barrel 消费）修复；守卫/三步法 0 回归，`src/schemas` 10→4（余 `__init__`/`bot_message`/`report_schema`/`run_flow`，跨 application 归属待 §6 G-1 拍板）。**迁移 R3-S2b（2026-10-29，`report_schema` 干净平移 application/analysis）**：经用户拍板先执 §6 中唯一无争议的干净件——`report_schema.py`（纯 stdlib+pydantic、零跨层 import、消费方均 in application/tests 且无 domain/infra 消费）`git mv`→`src/application/analysis/report_schema.py`、perl re-point 7 件、守卫/三步法 0 回归、`src/schemas` 4→3。同步勘察（不改码）：`run_flow` DTO 与目标 `application/runtime/run_flow.py`（同名异职责用例服务）碰撞、建议改落 domain 或改名共存；`daily_market_context_guardrail.py`（C-1）证据偏向 domain（仅依赖 stdlib+`report_language`、无 IO/编排）——两者均待拍板 §6 C-1/G-1。**迁移 R3-S4（2026-10-29，已解锁三件“落 domain”干净下沉 + 清空 `src/schemas/`）**：用户拍板 §6 余下三件均落 **domain**，单片三移动：**S4a** `daily_market_context_guardrail.py`→`src/domain/market/daily_context_guardrail.py`（re-point 3、解决 C-1）；**S4b** `run_flow.py`（纯 pydantic 快照 DTO）→`src/domain/analysis/flow_snapshot.py`（避开与同名服务碰撞、re-point 3）；**S4c** `bot_message.py`（纯 dataclass/Enum）→`src/domain/notification/bot_message.py`（re-point 30、排除 `test_check_architecture.py` 合成样例串）；**S4d** `src/schemas/` 清空后整体删除。实况：run_flow/bot_message 在 HEAD 未被跟踪（`??`）故用普通 `mv` 而非 `git mv`；守卫/三步法 0 回归。至此 §6 C-1/G-1 均关闭、R3 的 `src/schemas` 簇完全收官（`src/schemas` 10→0）；R3 整簇仍余 `src/core`/根级其余（S3：feishu_doc/formatters/logging_config；S5：report/prompt 簇；S4：pipeline 等）待后续片。**迁移 R3-S5（2026-10-29，根级 `src/*.py` 两件干净 infra 平移、§3-S3 无待决子集）**：`logging_config.py`（197 行、纯 stdlib）与 `feishu_doc.py`（165 行、stdlib+`lark_oapi`+`src.config.get_config`、infra 层仅禁 `api.`/`bot.` 故 import config 合法）经 `git mv`（两件均 tracked）分落新建的 `src/infrastructure/observability/logging_config.py` 与 `src/infrastructure/reporting/feishu_doc.py`（两父包 `__init__` docstring-only、不 eager 聚合）；re-point 含函数体 import、`main.py:959` 与**测试内 `patch(...)` 字符串目标**（logging 15 处 + feishu 2 处）共 18+3 引用点、旧路径残留 0；守卫/三步法 0 回归，根级 `src/*.py` 19→17。`formatters`（§3-S3 唯一非平凡件、需拆 domain+infra 两处）仍待后续片。**迁移 R3-S6（2026-10-29，`src/formatters.py` 机械拆分为 domain 切片 + infra 渲染、§3-S3 收官）**：`formatters.py`（1085 行、顶层 import `re`/`typing`/`markdown2`）按函数职责逐字拆两文件——纯文本切片侧（零 markdown2、零 `src.`）→`src/domain/shared/text_chunking.py`，Markdown 渲染/平台格式转换侧（含唯一 markdown2 用户 `markdown_to_html_document`）→`src/infrastructure/reporting/markdown_render.py`。拆分根因：`bot/platforms/discord.py` 仅需纯分块函数，整块落 infra 会 `bot→src.infrastructure` 违规、落 domain 则渲染语义错位，故拆两使 discord 改指 domain（bot→domain 合法）；机械脚本 `ast` 符号自检 `ORIG=48==CHUNK(26)|RENDER(22)`、两侧零交叉依赖；re-point 16 消费文件（含 3 混合 import 拆两条）、`rm` 删旧件、代码残留 0；守卫/三步法 0 回归，根级 `src/*.py` 17→16。至此 §3-S3（feishu_doc/formatters/logging_config）完全收官；R3 整簇仍余 `src/core`/根级其余（S5：report/prompt 簇；S4：pipeline 等）待后续片。**迁移 R3-S7（2026-10-29，根级 report/prompt 簇 6 件整体下沉 application、索引计划 S5 簇）**：`analysis_context_pack_prompt`/`market_phase_prompt`/`market_structure_prompt`/`market_phase_summary`/`analysis_context_pack_overview`/`phase_decision_guardrail`（均为互相依赖、依赖对 application 合法的干净件：纯 stdlib 或 stdlib+`report_language`/`domain`/`src.core.trading_calendar`）经 `git mv`（6 件均 tracked）分落 `src/application/{reporting/context_pack_prompt,reporting/market_phase_prompt,reporting/market_structure_prompt,market/phase_summary,analysis/context_pack_overview,analysis/phase_decision_guardrail}.py`（phase_decision_guardrail 的“规则/协作分离”为可选优化、本片按目标直搬不宣称拆分）；目标 analysis/reporting 两包无 eager 聚合、market barrel 不含新件→无循环；re-point 24 消费文件（含 pipeline 同文 4 件、api×2、混合消费逐行改写、**test_market_phase_summary.py:149 patch 字符串目标**）、代码级 6 旧路径残留 0；守卫/三步法 0 回归，根级 `src/*.py` 16→10。R3 根级余 `auth`(D-06)/`market_analyzer`/`md2img`/`report_language`/`scheduler`(D-07)/`stock_analyzer`/`storage`/`webui_frontend` 与 `src/core` 大件（pipeline 3922 行最大件）仍待后续片。**迁移 R3-S8（2026-10-29，根级 `src/report_language.py` 零改动下沉 `src/domain/shared/`）**：根级余件中唯一无待决项、可零改动整体平移的一件——`report_language.py`（1338 行、顶层仅 stdlib + `src.domain.decision.scale`、domain→domain 合法、无 `__file__` 路径推导）经 `git mv`+`git reset -q`→`src/domain/shared/report_language.py`（tracked）；消费面全仓无过滤勘察得 **30 文件 33 处引用均为 `from src.report_language import` 单一形态**（无 module/patch 串/importlib/裸形态），含 3 个 domain 件→核实 `scale` 不反向 import、`decision/__init__` 已惰性化（R3-S2）、`domain/shared/__init__` 无 eager 聚合→无循环；perl `\b` 批量 re-point 30 件、代码残留 0；同步 `domain/shared/__init__.py` 成员清单 + `decision/__init__.py` docstring + 活契约 `docs/multi-strategy-contract.md` 3 处文件路径（`full-guide`/`_EN` 历史叙述沿用 R1 先例保留）；守卫/三步法 0 回归，根级 `src/*.py` 10→9。R3-S9：根级 `src/stock_analyzer.py`（857）下沉 `src/domain/analysis/stock_analyzer.py`，前置把唯一跨层 `get_config().bias_threshold`（L27/L623）改为构造参数注入（`DEFAULT_BIAS_THRESHOLD=5.0`），调用方 pipeline（`getattr` 兼容桩 config）/analysis_tools 注入 config、bias 测试 10 处 patch 改构造注入；re-point 6 文件 16 处 + `ci_gate.sh` 路径，守卫/三步法 0 回归，根级 `src/*.py` 减 1（实测 7 件、含 `__init__.py`）。R3-S10：根级 `src/market_analyzer.py`（1896）下沉 `src/application/market/market_analyzer.py`，前置把唯一越层 `data_provider.base.DataFetcherManager`（L36/L149 + 4 处取数）改为 `MarketReviewDataPort`（4 方法）构造注入 + `DataProviderMarketReviewProvider` 适配器（直连 DataFetcherManager，不复用 data_sector_ranking 旁路），`bootstrap.configure_market_review()` 注册工厂并在 main/API lifespan 装配、未装配时空概览兜底；re-point 7 文件 48 处（含 13 处 patch 字符串目标）、`ci_gate.sh` 路径、测试源码路径改读 `module.__file__`，守卫/三步法 0 回归，根级 `src/*.py` 7→6；index 备注的「计算分离」为 deferral、本片未做。R3-S11：根级 `src/md2img.py`（141）下沉 `src/infrastructure/reporting/img_render.py`，前置 `ImageRenderPort`（1 方法）+ `Md2ImgImageRenderPort` 适配器（经 `img_render` 模块属性转发，patch 保真）+ `bootstrap.configure_image_render_port()` 注册类本身（main/API lifespan/conftest 三挂点）；`NotificationService` 构造注入、未装配回退文本；`src/core/pipeline.py` 直连新路径（core 仅禁 drivers、合法；index 原「两个消费者都在 application」口径已纠偏为 1 application + 1 core）；re-point 15 处（13 patch 串 + 1 路径字面量 + 1 注释）、新增 1 条正向回归用例，守卫/三步法 0 回归，根级 `src/*.py` 6→5。R3 根级余 `auth`(D-06)/`scheduler`(D-07)/`storage`/`webui_frontend` 与 `src/core` 大件R3-S12 再把 `src/core` 的 `market_review_lock.py`（227 行）与 `market_review_runtime.py`（128 行）零改动下沉 `src/application/market/`（仅 docstring 增来源说明；模块级互斥锁单实例语义经 `importlib` 身份验证；re-point 9 文件 17 处，三步法 0 回归），R3-S13 再把 `src/core/market_review.py`（932 行）整体零改动平移 `src/application/market/`（**不拆**渲染簇：取数已由 `market_analyzer` 承担，编排/渲染/持久化经 `run_market_review` 紧耦合；re-point 15 文件 44 处，`src/core` 3→2 件），R3-S14 再把 `src/core/trading_calendar.py`（651 行）下沉 `src/domain/market/`（前置把 `is_us_stock_code` 迁入 `domain/market/us_index_symbols.py`、`is_hk_stock_code` 迁入 `domain/market/stock_codes.py`，`data_provider` 侧改薄 re-export/别名，L136 不再跨层；re-point 17 文件 28 处，`src/core` 2→1 件），当时余 `pipeline.py` 待后续片。**R3-S15a/S15b（2026-10-30）**：`src/core/pipeline.py`（3947 行）先完成解耦前置（3 处 domain 真源改指、报告转图走既有 `ImageRenderPort`、28 处私有成员访问清零），再整体搬入 `src/application/analysis/pipeline.py`，取数由 `data_provider` 直连改为 `StockDataPort`（10 方法）端口 + infra 适配器 + bootstrap 工厂（main/API lifespan/conftest 三挂点，未装配显式抛错），`src/core/` 在仓库层面清零。**R3-S16（2026-10-30）**：根级 `src/scheduler.py` 前置把纯函数 `normalize_schedule_times` 单源化到 `src/domain/shared/schedule_times.py`（消除 `config/settings.py → application` 反向边）后下沉 `src/application/runtime/scheduler.py`。至此 `src/core`/`src/schemas`/`src/agent` 均为 **0**，根级仅余 `__init__.py`（空文件）与已批准例外 `storage.py`、`webui_frontend.py`、`auth.py`（D-06 默认落法 A）。）

### 4.2 Agent、Provider 与辅助模块的落点

- `src/agent/` 的 `orchestrator.py`、`runner.py`、`executor.py`、`conversation.py`、`research.py`、`agents/`、`skills/`、`tools/`、`strategies/` 倾向于 `src/application/agent/`，但 `tools/` 内执行第三方调用的代码须拆为适配器；`agent_backend.py`、`codex_agent_backend.py`、`codex_app_server_transport.py`、`codex_tool_process.py`、`litellm_route_resolution.py`、`llm_adapter.py`、`tool_surface.py` 倾向于 `src/infrastructure/agent_runtime/`。
- `data_provider/` 现有 `common/` 和九个能力子目录（`code_search`、`fundamentals`、`institutional`、`kline`、`limit_pool`、`news`、`realtime`、`sector`、`stock_info`）已经按能力组织。若决定迁入 `src/infrastructure/providers/`，沿用这些能力边界；顶层 fetcher、snapshot、bridge 文件在保留 import 和 fallback 语义的前提下，按调用关系逐一落位。若原位保留，也必须遵守应用层只依赖端口的规则。
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
| `src/analyzer.py`（现 `src/application/analysis/analyzer.py`）、`src/core/pipeline.py` | 用例编排与可独立测试的业务计算分开；外部行情/生成调用放适配器（analyzer LLM 生成调用簇已经 `AnalyzerLLMPort` 端口化下沉适配器；生成后端工厂/运行时/usage/provider-cache 簇已由 R2-A3 经 `GenerationBackendFactoryPort`/`GenerationRuntimePort`/`GenerationUsagePort`/`ProviderCachePort` 端口化下沉 `src/infrastructure/generation/`，`src/application/` 对 `src.llm` 的导入归零；R2-A4 已完成物理归位——7 个实现文件迁入该包、4 个过渡 shim 删除、`src/llm/` 目录不存在，适配器改为同包直依赖；决策稳定化纯函数→domain 尚未拆分） | 分析顺序、失败降级、报告/决策输出 |
| `src/application/intelligence/search_service.py`（原 `src/search_service.py`）、`src/services/image_stock_extractor.py` | 检索/识别用例与第三方搜索、Vision LLM 调用分开。**search 侧 §4.3 L255 已收敛（SA2 Epic）**：`BaseSearchProvider` + 8 Provider（Tavily/SerpAPI/Bocha/Anspire/MiniMax/Brave/SearXNG）+ 模块级网络工具（`_post_with_retry`/`_get_with_retry`/`fetch_url_content`）已物理下沉 `src/infrastructure/search/providers.py`，`SearchService`（application 用例层）改经 `SearchProviderPort` 端口 + bootstrap `configure_search` 注册的 provider-builder hook 构造（不再直接 import 具体 Provider），两处 `isinstance(provider, ...)` 编排耦合经中性 `SearchOptions` 全量下发消解，`SearchResponse/SearchResult` DTO 落 `src/domain/search/`。**image_stock_extractor 的 Vision LLM 调用拆分尚未处理、不宣称完成** | 超时、重试、结果归一及错误语义 |
| `src/notification.py`（现 `src/application/notification/notification.py`）、`src/notification_sender/`、`src/services/report_renderer.py` | 通知/报告意图、模板渲染、渠道发送和技术输出分开 | 报告结构、渠道失败隔离、下游消费兼容。**终态（2026-10-30）**：通知意图与渠道发送已由 R2-B3 解 14-mixin 继承→组合 + `NotificationSendPort`，R2-B5 将 `src/notification_sender/` 物理迁至 `infrastructure/notification/senders/`（旧目录已删），R3-S11 补 `ImageRenderPort`；**仍余**：`application/notification/notification.py`（3063 行）内模板渲染与技术输出编排未分离，属 §4.3 长期项 |
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

§4.3 结尾要求 P0 形成「现有文件 → 具体职责 → 候选落点 → 调用方 → 验证证据」的文件级清单。该清单的**落点与切片归属**部分已入库 `documents/framework/src_migration_index.md`，作为多会话并行时「一个文件只允许一个负责切片」的归属唯一真源；后续切片开工前先查该表，改动落点或补齐缺口须同步更新它。

**终态（2026-10-30，R3-S16 收官）：待迁移件 0。** 下列留存项不是待迁移面，而是已批准例外、兼容面与按 §4 目标表原位保留的模块：

| 留存项 | 实测件数 | 性质 |
| --- | --- | --- |
| 根级 `src/*.py` | 4 | `__init__.py` 空文件、`auth.py`（D-06 落法 A 例外）、`storage.py`/`webui_frontend.py`（已批准例外） |
| `src/services/__init__.py` | 1 | 兼容面：`get_task_service` 惰性映射，全仓 0 生产调用方 |
| `src/utils/`、`src/data/`、`src/patches/`、`src/brokers/` | 8 / 3 / 2 / 1 | §4 目标表列为「可跨期保留旧模块」，不为清空目录造泛化容器 |
| `data_provider/` | 原位保留 | §4 目标表「可原位保留为基础设施适配包」；应用层只经端口访问，守卫已禁止 application → `data_provider` |

**例外与移除前置条件**（2026-10-30 成文，详见 `documents/framework/architecture_migration_adr.md` ADR-002~ADR-006）：上述留存项均为**已登记的例外而非被遗忘的待迁移面**，各自的移除条件如下：`src/services/__init__.py` 兼容面（ADR-006）—— 全仓生产调用方实测 0（`bot/commands/analyze.py:81` 已直接 import `src.application.runtime.task_service`），但 `scripts/build-backend-macos.sh:94` 与 `scripts/build-backend.ps1:110` 的 PyInstaller hidden-import 仍列 `src.services`，删除需同时改两处并跑桌面端打包验证，故按既有决策（`.claude/reviews/decisions-2026-10-28-r2a.md`）**保留为兼容面**；`storage.py` 门面（ADR-004）—— 消费方全部改走仓储端口后可删除；`auth.py`（ADR-005）—— 如需入四层需先定认证/CORS 基线（§9.2-5）；`utils`/`data`/`patches`/`brokers` 四簇（ADR-003）—— 不为清空目录造泛化容器，可长期保留。

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

当前 `src/storage.py` 包含 ORM 模型、`DatabaseManager`、`Base.metadata.create_all()` 和多个 `_ensure_*` 兼容升级。拆分时不得创建跳过升级逻辑的 no-op 中间版本，也不得让同一模型同时以旧、新模块身份注册。可先把数据库启动拆成 `base → models import → engine/session → schema compatibility → service bootstrap`，通过新库建表和现有开发库升级测试再切换入口。`create_all()` 只负责创建缺失表，不是已有表结构的升级方案；若引入版本化迁移，需明确它与 `_ensure_*` 的过渡期及最终唯一权威，不能让两套升级逻辑并行且无人负责。

事务边界按一次请求或一次后台任务中的**逻辑操作**确定；一个用例需要原子更新多个仓储时，由用例边界控制提交/回滚，仓储不各自提交。会话由入口装配并在任务结束时释放，不跨并发请求、线程或异步任务共享同一 Session。长时间的抓取/LLM 调用不持有数据库事务；具体并发与 SQLite 锁行为以实际测试确认。

项目尚未上线，可评估从干净 schema 重建开发数据库并为未来建立版本化迁移。但具体采用“保留/升级现有开发库”还是“备份后重建”，必须先盘点实际数据用途及 Desktop 本地库场景，形成可执行的迁移或恢复方案。正式上线前确定迁移执行时机，避免 HTTP 请求中隐式迁移。现有 `_ensure_*` 只有在其历史输入状态不再需要时才能移除。

### 5.2 配置

目标 `src/config/` 至少区分运行时读取、字段注册/校验、`.env` 编辑、密钥生命周期。先锁定当前默认值、优先级、热更新与脱敏行为，再合并事实源。配置路径改动要一并检查 `main.py`、API、Bot、Docker、Actions 和 Desktop 后端。新增键仍需更新 `.env.example` 及相应说明。

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

## 8. 方案通过前的确认点

1. 数据库演进：开发库是否有必须保留的数据、Desktop 是否仍需要升级已有本地 SQLite。确认后才能决定删除历史 `_ensure_*` 的条件。
2. 包边界：`src` 继续是运行时包名。`data_provider/` 是已按能力拆分、已有 ADR 的适配包；把它迁入 `src/infrastructure/providers/` 是首选的最终归位，但**不是实现依赖倒置的前提，也不应成为单独的“搬目录”验收项**。P4 先验证调用方是否通过用例端口隔离；仅在迁移带来明确收益且能同一变更覆盖所有导入、Docker、PyInstaller、测试和 ADR 时迁入，否则保留原包并将它明确列为基础设施例外，不为目录整齐制造破坏性改动。
3. 架构守卫：选择并安装实际使用的 import 检查工具，先采集违规基线，再把新增违规设为阻断，逐切片缩小基线；不能只在 `pyproject.toml` 写一个未执行的配置。
4. 全仓目录：Web、Desktop、脚本、文档和本机目录按本文保持原位；若未来需要各自重构，应有单独问题和验收范围。
5. 治理同步：现有 `AGENTS.md` 将 `data_provider/` 列为允许的后端边界；若最终迁移该包或调整入口约定，应在实施 PR 中同步修改 `AGENTS.md` 及镜像说明，并运行 `python scripts/check_ai_assets.py`。本草案尚不改变当前开发规则。

本文为文档修改方案，尚未修改代码、数据库或目录，也未执行清理。实施后需按实际路径更新本文件及相关专题文档。

## 9. 跨模型与 Agent 的实施交接

本节供未参与前期讨论的开发者、其他模型或 Agent **独立接手**。无需先读取聊天记录；先读仓库根目录 `AGENTS.md` 和本文，再核对当前代码、测试、脚本、工作流及 Git 状态。`AGENTS.md` 约束当前开发流程，本文描述尚未全部落地的目标；两者都不能替代实际代码证据。本文中的文件数量、路径盘点和 2026-10-23 基线会过期，不能作为当前工作树事实直接执行。

### 9.1 已确认的意图与边界

- 仓库根目录为 `HermesX/`，保留现有可导入包 `src`，在其内部按 `domain / application / infrastructure / bootstrap / config` 分层；**不**改成 `src/hermesx/`。目录图是候选结构，不要求创建空目录，也不是批量移动清单。
- 本次以服务端职责、依赖和多入口装配为主；混合职责的 `.py` 文件需要拆分**内部代码**，不能仅移动文件。每个切片以第 4.3 节的行为契约、调用方向和实际验证为准。
- Web、Desktop、Bot、脚本、Docker、CI 和文档按第 4.4 节及第 7 节联动；只有对外契约或启动/打包行为改变时才改相应客户端，不借服务端改造重排前端目录。
- 项目尚未上线，内部路径和 schema 可有计划地调整；但现有本地数据库、密钥、日志、报告、原型和各类本机文件仍须保留。先确认目标和备份/恢复方案，不能把“尚未上线”解释为允许直接删库或清理资产。`src/UNKNOWN.egg-info/` 仅是可在实施时核实清理的构建残留，不是现在要执行的删除指令。
- `data_provider/` 物理迁入 `src/infrastructure/providers/` 是可选的首选落点，不是分层成立的必要条件；先隔离应用层对具体数据源的依赖，再按收益、调用关系和打包影响决定。不得为满足树形图强行搬迁。
- 不经用户明确确认，不执行 `git commit`、`git tag`、`git push`；不覆盖其他任务的改动。其他具体协作规则以当前 `AGENTS.md` 为准。

### 9.2 尚未决定，接手者不得自行当成既定结论

> **状态回写（2026-10-30，第一批收口）**：下列 5 项中 **2/3/4 已由实施过程中的既成事实与已确认决策定稿**，转为「9.2.1 已决」；**1/5 仍为开放决策**，需用户/维护者拍板。

#### 9.2.1 已决（依据与证据）

| 原编号 | 结论 | 依据 |
| --- | --- | --- |
| 2 | `data_provider/` **不物理迁入** `src/infrastructure/providers/`，保留原路径并明确登记为基础设施例外；新能力适配层落 `src/infrastructure/providers/` | 本文 §4 目标表与 §4.5 留存项表已写明；守卫已禁止 `src/application` → `data_provider`；ADR-003 |
| 3 | 架构守卫采用仓内自研 `scripts/check_architecture.py`（静态 AST + 前缀首个匹配规则表），基线归零**已完成**：`scripts/architecture_baseline.json` 的 `entries` 为 `[]`，并由 `scripts/ci_gate.sh:11,17` 纳入 CI 阻断 | R3 收口守卫复核（本文 §4.5）；`tests/test_check_architecture.py` 合成工作区自测 |
| 4 | 本轮进程模型按**单进程假设**执行：任务队列/SSE 订阅者/调度器的进程内状态不做跨进程去重与送达保证；水平扩展属单独设计，不在迁移范围 | `documents/framework/architecture_migration_progress.md` §1 已确认决策 **D5**；入口与调度所有权见同文件 §2 运行矩阵 |

1. 现有开发库与 Desktop 本地 SQLite 的保留、备份重建或版本化迁移路径（第 5.1、8 节）。
2. 【已决 → 见 9.2.1】`data_provider/` 是否实际迁入 `src/infrastructure/providers/`，以及相应 ADR、Docker、PyInstaller 和全仓 import 的同步范围（第 8 节）。
3. 【已决 → 见 9.2.1】架构守卫采用何种实际可执行工具，以及 P0 违规基线如何逐步归零（第 8 节）。
4. 【已决 → 见 9.2.1】目标部署进程模型：当前任务队列/SSE 订阅者和调度器有进程内状态；在确认单进程运行还是支持多 worker/多实例前，不得声称共享 bootstrap 已解决跨进程任务归属、去重与事件送达。需先给出运行约束或单独设计。
5. 对公网/桌面两种运行场景的认证、Cookie、CORS 与修改类请求防护，以及性能/启动时间的基线和验收阈值，须在相关切片开始前记录；不得凭目录设计推断现状已安全或性能不变。

这些问题若影响实施结果，应列出选项、现状证据、影响面和建议，请用户/维护者确认后再落地。后续有明确决策时同步更新本文与对应 ADR，避免只留在聊天记录里。

### 9.3 每个切片的交接流程与记录格式

接手时先记录当前分支/HEAD、工作区状态、已完成阶段与最新测试结果；从 P0 的文件级职责/调用方清单选择一个可独立验证的切片。对照当前代码确认本文列出的旧路径仍存在，再实施、验证和交接。不要把前一个 Agent 的“已完成”口头结论当作测试证据，也不要因为某个目录已经出现就认定分层已经完成。

每个切片结束时，在对应 PR 描述中记录以下内容；若尚无 PR，P0 可在 `documents/framework/` 下建立**一个**统一的实施进度文档，并在后续切片持续更新，避免每个 Agent 各写一份状态摘要：

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
