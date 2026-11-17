# <a id="python-engineering-architecture"></a>HermesX Python 工程架构

> 📝 **方案简述**：记录现有 Python 五层结构、文件放置与命名规则，以及迁到 `python/` 后分析服务的接口、数据和验证边界。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-17

## 目录

- [一、当前结构与目标](#sec-1)
- [二、工程目录示例](#sec-2)
- [三、分层职责与依赖](#sec-3)
- [四、文件放置与命名](#sec-4)
- [五、数据源、存储与 Java 接入](#sec-5)
- [六、迁移与验证](#sec-6)

<a id="sec-1"></a>

## 一、当前结构与目标

当前 Python 工程仍从仓库根目录运行，五层结构已经落地。按[整体工程架构](engineering_architecture.md)，目标是将 Python 工程整体迁到 `python/`，保留内部目录、`src` 导入包名和现有 CLI、FastAPI、Bot 入口。下文的示例路径除非注明，均相对 **Python 工程根目录**：例如 `src/application/quote/` 当前在仓库根目录，迁移后对应仓库路径 `python/src/application/quote/`。

本方案接续原 ADR-001，并以现有代码、[五层实施基准](../framework/refactoring/ARCHITECTURE_TARGET.md#2-依赖规则)和[已决迁移例外](../framework/architecture_migration_adr.md)为依据。原四层视图、早期端点和文件清单见 Git 历史中的 ADR-001（提交 `c711b4bb`）；当前新增文件按下文归位。Python 迁目录不再进行一轮分层重构。

<a id="sec-2"></a>

## 二、工程目录示例

```text
python/                             # 目标工程根；当前这些内容在仓库根目录
├── .python-version
├── pyproject.toml / setup.cfg / requirements.txt
├── main.py                         # CLI、分析、定时运行和服务模式
├── server.py                       # FastAPI 入口
├── webui.py                        # 现有兼容入口
├── api/
│   ├── app.py / deps.py
│   ├── middlewares/
│   └── v1/
│       ├── router.py
│       ├── endpoints/kline.py     # HTTP 端点
│       └── schemas/kline.py       # HTTP 请求和响应
├── bot/
│   ├── commands/analyze.py
│   └── platforms/
├── src/
│   ├── domain/
│   │   ├── analysis/stock_analyzer.py
│   │   └── market/stock_codes.py
│   ├── application/
│   │   ├── quote/                 # service.py、ports.py
│   │   ├── analysis/              # pipeline.py、analysis_service.py 等
│   │   ├── runtime/               # 任务队列、调度、运行诊断
│   │   └── …                      # 回测、决策、Agent、情报、投组、预警、报告等
│   ├── infrastructure/
│   │   ├── persistence/
│   │   │   ├── base.py / session.py / schema_compat.py
│   │   │   ├── models/market_data.py
│   │   │   └── repositories/market_data_repo.py
│   │   ├── providers/kline_provider.py
│   │   └── …                      # 生成、通知、报告、索引、搜索、Agent 运行时
│   ├── bootstrap/                 # quote.py、analysis.py、api_lifecycle.py 等
│   ├── config/                    # 配置定义与加载
│   ├── data/                      # 随代码分发的股票索引、映射和加载器
│   ├── brokers/ / patches/ / services/ / utils/
│   └── storage.py / auth.py / webui_frontend.py
├── data_provider/
│   ├── base.py                    # 现有兼容入口
│   ├── common/                    # 通用协议、缓存、归一化、限频、健康度
│   ├── clients/                   # 供应商或 SDK 的底层客户端
│   ├── runtime/                   # 跨能力管理器、工厂和历史取数实现
│   ├── kline/                     # base.py、eastmoney_source.py、transform.py 等
│   ├── stock_info/ / code_search/ / realtime/ / sector/
│   └── …                          # 其他现有能力包
├── strategies/
├── templates/
└── tests/                          # API、应用、领域、适配器、集成和工具检查
```

【强制】`src` 是可导入包（如 `from src.application.quote import …`）。同批迁移保持其导入名，不再套一层 Python 包。现有兼容模块先随工程移动；新增代码放到所属层，旧入口在调用方全部迁离后再退役。

<a id="sec-3"></a>

## 三、分层职责与依赖

```text
HTTP / CLI / Bot → Application → Domain
                       │
                       └─ 声明用例端口 ← Infrastructure 实现
                                               └─ 行情适配调用 data_provider
Bootstrap 装配用例与适配器；Config 提供运行配置。
```

| 位置 | 职责与边界 |
| --- | --- |
| `api/`、`bot/`、入口脚本 | 接收输入、处理传输协议、调用用例、映射结果。HTTP 使用配套 schema；健康检查、认证中间件和静态资源可处理框架职责。业务端点和 Bot 命令不直接查库、取行情或调用供应商 SDK。 |
| `src/domain/` | 业务概念、指标及纯计算规则。禁止依赖 FastAPI、ORM、配置、应用层或外部 I/O。纯函数也应有领域语义才归入本层。 |
| `src/application/` | 用例、业务编排、任务和持久化意图。依赖 domain 和本域定义的窄端口；不直接导入具体适配器、`data_provider`、ORM 或 HTTP 驱动。 |
| `src/infrastructure/` | 实现仓储、行情端口、模型调用、搜索、通知、报告渲染和外部 SDK；不依赖 API 或 Bot 驱动。 |
| `src/bootstrap/` | 组装端口、服务及生命周期；共用显式的 `build_*()`、`configure_*()` 入口，不在导入时启动任务、连接外部服务或初始化数据库。 |
| `src/config/` | 配置定义、加载和校验；配置层只向 domain 依赖其他业务层，现有共享工具例外按架构基线保留；供应商行为通过用例端口处理。 |
| `data_provider/` | 行情与数据源接入边界。复用内部能力 Manager、客户端、归一化、缓存与回退机制；不得反向依赖具体用例、驱动或 bootstrap。 |

【强制】沿用 [架构检查脚本](../../scripts/check_architecture.py)及现有基线；存量例外不可作为新增反向依赖的先例。端口就近放在用例所属业务包，不设集中 `application/ports/`，也不为每个函数增加一层转发。

当前已知缺口：`src/application/system/system_dict_service.py` 仍直接依赖国家数据源、具体仓储和 `src.storage`，架构检查会报出这三项。它们不属于新增代码的可用模式；后续接入 Java 字典模块时，应按用例端口或功能迁移收口。

<a id="sec-4"></a>

## 四、文件放置与命名

| 文件位置 | 示例 | 文件应包含 |
| --- | --- | --- |
| `api/v1/endpoints/<能力>.py`、`api/v1/schemas/<能力>.py` | 两处均为 `kline.py` | 端点注册、输入与结果映射；schema 定义 HTTP 载荷，与 ORM 模型分离。公开路由在 `api/v1/router.py` 注册。 |
| `src/domain/<业务域>/` | `market/stock_codes.py`、`analysis/stock_analyzer.py` | 领域模型、值对象和纯规则。优先用业务概念命名，可按需用 `*_rules.py`。 |
| `src/application/<业务域>/` | `analysis/analysis_service.py`、`analysis/pipeline.py`、`quote/ports.py` | 用例、编排和用例需要的 `Protocol`。已有 `service.py` 可沿用；领域内有多项独立职责时使用 `<能力>_service.py` 或语义更具体的文件名。端口多时按职责拆分，如 `stock_data_port.py`。 |
| `src/infrastructure/persistence/` | `models/market_data.py`、`repositories/market_data_repo.py` | ORM 模型统一进 `models/`，查询、写入与记录转换进 `repositories/`，沿用邻近文件的 `*_repo.py` 或 `*_repository.py`。会话及兼容升级集中在 `session.py`、`schema_compat.py`。 |
| `src/infrastructure/providers/`、`data_provider/<能力>/` | `kline_provider.py`、`kline/base.py`、`kline/eastmoney_source.py` | 前者将应用端口适配到数据源能力；后者存能力契约、选源及具体实现。供应商传输或 SDK 包装放 `data_provider/clients/<供应商>/`；归一化或转换用具名文件，如 `transform.py`。 |
| `src/bootstrap/<能力>.py` | `quote.py` | 集中组装该能力的服务、端口实现和生命周期。 |
| `tests/<层或驱动>/` | `tests/api/kline/`、`tests/application/quote/` | `test_<能力或行为>.py`。跨真实组件边界的检查放 `integration/` 或相应契约目录；共享样本放 `fixtures/`，可复用辅助放 `support/`。 |

- 【强制】模块和函数用 `snake_case`，类用大驼峰，模块级常量用大写下划线。文件名表达业务用途，避免把新职责放进泛化的 `utils.py`、`common.py`。保留已有命名，不为统一后缀批量改名。
- 【强制】公共复用通过明确的公开接口；跨层不访问以下划线开头的内部成员。HTTP schema、应用入参和 ORM 模型仅在各自边界使用，不直接把数据库对象暴露为响应。
- 【推荐】按实际职责建文件和目录；优先复用邻近模块，不预建空壳。注释说明业务意图、边界和异常条件，参照[项目代码注释规范](../../.conventions/common/CODE_ANNOTATION.md)。

<a id="sec-5"></a>

## 五、数据源、存储与 Java 接入

- 【强制】K 线、基础信息、代码搜索按能力收口，复用配置驱动的选源、标准化和回退；向调用方提供稳定契约。源支持的市场、周期和字段按能力声明，可回退性按现有规则判定，不把各源差异藏成空成功。其他数据能力按自己的来源和现有策略接入。
- 【强制】StockDB 通过数据源适配器接入，由其进程管理自身数据库。第三方原始响应不因接入就新增落表；沿用已有 TTL、限速和健康冷却。项目明确持久化的日线、分析历史、投组及其他业务记录继续由 Python 仓储负责。沿用现有 schema 兼容链，不另建并行迁移机制。
- 【强制】Java 通过经服务认证的内部 HTTP 接口提交分析和查询结果，不访问 Python 数据表。Java 管登录、数据范围和任务归属，Python 管分析执行、状态和报告。迁移期间保留现有 Python API、CLI 与 Bot 行为；旧的用户业务写入路径须在对应 Java 功能接管且调用方迁离后按项退役。
- 【推荐】首期复用现有 Python 任务队列。它在进程内跟踪执行中任务和进度订阅；只有需要跨重启恢复或多实例共同处理时，再持久化任务状态并评估独立 Worker。
- 【推荐】行情链路按 `api/v1/endpoints/kline.py → src/application/quote/service.py → QuoteProviderPort → src/infrastructure/providers/kline_provider.py → data_provider/kline/` 理解，端口实例由 bootstrap 装配。不要将数据源切换规则重复写到端点或 Java 客户端。

<a id="sec-6"></a>

## 六、迁移与验证

迁移到 `python/` 时，同批更新本地启动、测试配置、架构扫描根目录和基线路径、Docker 构建上下文、GitHub Actions、股票索引、PyInstaller 入口及模板与静态资源解析。仓库级的 `scripts/`、`docker/`、`.github/` 原位保留。运行数据目录从部署配置解析，既有数据库、报告和密钥不随源码移动。

在当前布局，从仓库根目录运行 `python scripts/check_architecture.py --check` 和 `./scripts/ci_gate.sh`。实施迁移时还应验证 CLI、FastAPI、定时分析、Bot、Docker 和 Electron 安装包；涉及数据源时先覆盖超时、回退与字段契约，联网 smoke 与离线验收分别记录。未完成这些验证前，迁移后的路径只作为设计目标。
