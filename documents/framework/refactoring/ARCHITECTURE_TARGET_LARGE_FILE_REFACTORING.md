# HermesX 目标架构实施延续：服务端大文件第二轮拆分与交接

> `ARCHITECTURE_TARGET.md` §4.3「文件内部代码拆分指引」的服务端大文件第二轮拆分实施记录与交接补充。在现有五层架构内拆分文件内部职责，保持 API、CLI、报告、配置及数据库契约。

| 项目 | 内容 |
| --- | --- |
| 文档标识 | `ARCHITECTURE_TARGET_LARGE_FILE_REFACTORING.md` |
| 文档定位 | `ARCHITECTURE_TARGET.md` 的服务端大文件拆分专项实施延续；按职责拆分，记录落地结果、验证证据及后续交接，不替代原目标方案 |
| 作者 / 更新人 | Codex，依据维护者确认的实施范围 |
| 更新时间 | 2026-11-03（Asia/Shanghai） |
| 代码基线 | main / `6eb298aa`（实施起点）；开始时工作区干净，后续提交状态以 Git 日志为准 |
| 关联目标 | [ARCHITECTURE_TARGET.md §4.3](./ARCHITECTURE_TARGET.md#43-文件内部代码拆分指引) |
| 当前范围 | 完成 9 个混合职责文件的拆分，评估原 13 个大文件；声明和职责集中者保留 |
| 客户端边界 | Web / Electron 源文件不修改；客户端构建用于验证联动，不扩展页面能力 |

## 目录

- [处理决定](#处理决定)
- [职责落点](#职责落点)
- [依赖与兼容](#依赖与兼容)
- [验证证据](#验证证据)
- [保留事项与风险](#保留事项与风险)
- [后续交接与回滚](#后续交接与回滚)

## 处理决定

行数使用本轮前后物理行数，包含注释和空行。1800 行是盘点线索，不是验收门槛；本轮没有把一个大文件机械搬为另一个同等大小的万能组件。

| 原文件 | 基线行数 | 当前行数 | 决定与依据 |
| --- | ---: | ---: | --- |
| `src/config/field_definitions.py` | 5457 | 5457 | 保留：纯字段声明，0 个函数，不按行数切碎注册事实源。 |
| `src/config/settings.py` | 3254 | 3254 | 保留统一加载入口：_load_from_env 的 1057 行中，639 行是 287 个构造参数的显式映射；validate_structured 的跨字段语义不在本轮重写。后续如演进，先形成配置优先级与校验矩阵。 |
| `src/application/runtime/system_config_service.py` | 4328 | 1426 | 已拆：渠道探测、通知试发、初始化检查、诊断脱敏、字段校验；写入、冲突与重载留在协调入口。 |
| `src/application/analysis/analyzer.py` | 4379 | 1964 | 已拆：结果值对象、提示词、响应解析、结果后处理；保留生成路由状态与分析协调，不为降行数再次机械拆分。 |
| `src/application/analysis/pipeline.py` | 3732 | 2509 | 已拆：上下文增强、Agent 结果映射、报告交付；保留两条分析主流程、并发及缓存/锁的所有权。 |
| `src/application/notification/notification.py` | 2863 | 1434 | 已拆：报告内容渲染与通知发送职责分离，原入口继续负责渠道、发送端口与噪声控制。 |
| `src/application/intelligence/search_service.py` | 2530 | 1324 | 已拆：相关性/语言/质量策略及日期归一化；提供方选择、缓存与并发填充仍由服务协调。 |
| `src/application/agent/orchestrator.py` | 2143 | 1497 | 已拆：仪表盘汇总及其纯辅助函数；原入口负责 Agent 执行、超时和任务协调。 |
| `src/infrastructure/search/providers.py` | 2127 | 82 | 已拆：7 个具体适配器分别归位，共享基类/HTTP 重试独立；原模块保留公共类型导出与有序工厂。 |
| `src/application/intelligence/intelligence_service.py` | 2011 | 1885 | 已拆：RSS/Atom/NewsNow 解析与值对象；保留源管理、刷新和安全请求流程，未改 DNS/重定向/代理/体积限制。 |
| `src/application/market/market_analyzer.py` | 1953 | 1395 | 已拆：复盘提示词和输出模板、市场值对象；保留行情获取与复盘生成协调。 |
| `src/application/analysis/alphasift_service.py` | 1849 | 1849 | 保留：单一 AlphaSift 业务服务，主要用例 hotspots/hotspot_detail/screen 为 119/87/63 行；当前职责集中，保留同一业务服务入口。 |
| `src/infrastructure/providers/hrs_alphasift_bridge.py` | 1816 | 1816 | 保留：单一 AlphaSift 适配边界，最大函数 100 行；运行环境和候选上下文共享同一适配协议，未新增平行桥接。 |

原盘点共 13 件；本轮修改其中 9 件，另外 4 件基于职责评估保留。当前仍有 7 件达到 1800 行（包含已抽出协作者的 analyzer、pipeline、intelligence_service），不以继续切割它们来制造“全部小于阈值”的完成率。

## 职责落点

| 协调入口 | 新职责模块 | 依赖 / 状态所有权 |
| --- | --- | --- |
| SystemConfigService | `runtime/llm_channel_probe.py`、`notification_channel_test.py`、`setup_status.py`、`config_probe_diagnostics.py`、`config_value_validation.py` | 复用既有探测、通知和生成端口。组件接收必要工厂 / 配置；不接收整个 SystemConfigService。保存、冲突检查和运行时重载仍在原入口。 |
| GeminiAnalyzer | `reporting/analysis_prompt.py`、`analysis/response_parser.py`、`analysis/result_policy.py` | 提示词组装只接收运行配置与技能策略读取能力；解析只接收配置和生成后端标识解析能力。模型调用、fallback 和使用量端口不另建实现。 |
| StockAnalysisPipeline | `analysis/context_enrichment.py`、`analysis/agent_result_mapper.py`、`notification/analysis_report_delivery.py` | 数据增强接收取数 / 搜索依赖；结果映射只接收语言；报告交付接收 notifier、配置、诊断回写能力。流水线仍拥有并发锁、缓存、query 与持久化协调。 |
| NotificationService | `reporting/analysis_report_renderer.py` | 配置、显示选项和历史比较缓存显式提供；发送端口、渠道状态、噪声控制不进入渲染器。 |
| AgentOrchestrator | `agent/dashboard_finalizer.py` | 从意见构建仪表盘的纯函数，不执行 Agent，不持有调度或网络状态。 |
| SearchService | `intelligence/news_relevance.py`、`intelligence/news_freshness.py` | 质量、语言、相关性及日期策略无服务实例状态；并发缓存只保留一套。 |
| 搜索提供方 | `infrastructure/search/provider_base.py`、`adapters/{tavily,serpapi,bocha,anspire,minimax,brave,searxng}.py` | 基类、重试和正文提取共享；具体协议分别实现，原有工厂优先级不变。 |
| MarketAnalyzer | `reporting/market_review_prompt.py` | 显式市场 profile、地区、策略与语言读取能力；不获取行情或调用模型。 |
| IntelligenceService | `intelligence/feed_parser.py` | 解析接收 URL 校验回调；校验仍调用原安全流程，未 mock 或绕开安全层。 |
| 值对象 | `domain/analysis/result.py`、`domain/market/review.py`、`domain/search/feed.py` | 分析结果、市场复盘数据和 feed 条目/错误移入无 IO 的 domain；原公共入口导出同一类型对象。 |

上表 application 路径相对于 `src/application/`，domain 与 infrastructure 路径相对于 `src/`。新模块不通过反向导入原协调入口获取运行状态。

## 依赖与兼容

- 保留现有公共入口与调用签名，通过明确协作者执行职责；不是新增万能基类、mixin 或让新组件任意访问整个服务对象。
- 复用现有端口及 bootstrap，不新增平行注册表、配置开关、API 或后台任务。
- 调用期按原有时机获取端口，配置不完整时不会为了构建新组件提前触发真实外调。
- 配置写入、版本冲突、秘密占位符、重载顺序及失败处理保持原契约。
- 模型异常、流关闭、fallback、报告发送失败隔离及噪声控制释放仍使用原路径。
- URL/DNS 校验、代理禁用、响应体积限制和重定向限制未改；解析器仍显式调用 URL 校验。
- 原公共模块保留公共类型和工厂导出，只有一份类型 / 实现；保留需要的协调方法，不建立第二份行为副本。
- 新组件对外协作使用公开成员；没有通过更新架构 baseline 放行跨模块私有调用。
- 测试只更新 moved dependency 的 patch/辅助入口，不删除断言、不放宽失败预期、不增加 skip/xfail。旧日志命名空间保留，兼容现有日志过滤与秘密脱敏检查。

## 验证证据

| 检查 | 结果 |
| --- | --- |
| 收集数量 | 5725，测试数量与本轮前一致 |
| 系统配置与 API 子集 | 257 passed / 60 subtests |
| 三个核心入口联合子集 | 1636 passed / 147 subtests |
| 通知 / 流水线子集 | 242 passed / 3 subtests |
| Agent 子集 | 602 passed / 62 subtests |
| 资讯 / 搜索 / 市场子集 | 365 passed / 2 skipped / 71 subtests（该子集未排除 network） |
| 固定顺序全量离线 | 5720 passed / 1 skipped / 4 deselected / 511 subtests，330.11s |
| 随机种子 20261103 全量离线 | 同上，366.77s |
| 架构守卫 / 严重静态检查 | 通过 / 0；未修改架构 baseline |
| ci_gate syntax / deterministic | 通过，覆盖源码语法及 code / yfinance 确定性检查 |
| Web 生产构建 | 通过；使用本机已有依赖，不能替代 Docker 干净构建 |
| 内容一致性 | 3 份系统提示词常量 AST 一致；21 个结果规则函数、8 个提供方/基类及 6 个值对象的定义 AST 一致（忽略 docstring 排版）；7 种报告 × 中英韩共 21 组输出逐字一致 |
| macOS 打包后端 | 复用同固定版本的已安装依赖完成冻结；--help、关键依赖导入、日历 / 策略资源检查通过，28 个新模块均在归档内，且在冻结可执行文件中逐一实际导入通过。临时配置 / 数据库下健康接口及首页均 200；干净依赖安装因 GitHub SSL 超时未完成。 |

复现主要检查：

```bash
python scripts/check_architecture.py --check
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
./scripts/ci_gate.sh syntax
./scripts/ci_gate.sh deterministic
python -m pytest tests -m "not network" -p no:randomly
python -m pytest tests -m "not network" --randomly-seed=20261103
```

在最终协调入口清理后，相关 499 条测试和固定序全量再次通过；随机序结果来自该清理前，清理仅删除无引用的重复常量，并将诊断快照构建改为引用同一静态函数。

原报告输出比较针对给定代表样本，在隔离配置、关闭历史比较、注入惰性发送/图片对象的条件下执行，没有发送真实通知。日期固定为 2026-11-03；结构化测试继续覆盖已有报告和错误场景。没有报告格式和 UI 改动，故不新增页面截图。

## 保留事项与风险

- 架构守卫和测试通过不代表全部在线数据源、真实 LLM、通知渠道及所有桌面平台都已验收。网络测试未运行，原跳过及 27 条警告保留。
- Docker HeroUI Pro 授权缺口、桌面端口 / 就绪判定问题、UI 原生 title 守卫和全量前端 lint 都是既有独立事项，本轮没有通过改页面、移除依赖或放宽规则来关闭它们。
- 未修改 API、数据库结构、配置默认值、认证或前端交互；Web 构建验证通过，客户端无需配合改接口。
- 新模块增加了 import / 打包收集边界，已核对 PyInstaller 冻结归档及运行入口。标准脚本重新安装 AlphaSift 时 GitHub SSL 超时；本机已安装修订号与 requirements.txt 固定的 9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf 一致，后续冻结验证复用该环境，未修改正式构建脚本或放宽版本。Windows 和 Intel macOS 仍需对应平台验收。
- 保留的 4 件原文件不是“忘记处理”：字段声明、统一配置读取、单一 AlphaSift 用例和适配边界已逐项登记。需要继续演进时，以具体变更压力和独立语义设计触发，不以行数触发。

## 后续交接与回滚

先读本文件及当前架构总览，再看各协调入口和上表职责模块。修改某项能力时同时检查入口、协作者、端口、测试及打包路径，禁止只更新一处测试 patch 后声称闭环。

按业务组回滚：配置组、分析器组、流水线组、报告渲染组、Agent 汇总组、搜索组、复盘组、feed 解析组；恢复原实现时同时撤回对应新模块和测试接缝，共享值对象与全部引用方应原子回滚，保持每项行为和类型只有一个实现，不能单独恢复旧 AnalysisResult 定义而保留新定义。不覆盖维护者后续修改，不回滚用户配置、数据库或运行产物。

本轮没有对应英文内部架构文档，不新增平行译本；未改变已有中英文用户操作说明中的行为或命令。没有执行 commit / push / tag。
