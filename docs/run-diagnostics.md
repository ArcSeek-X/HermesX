# 运行诊断与数据可靠性 1.0（Phase 0–3 归档）

> 本文合并 #1391 的 Phase 0 / 1 / 2 / 3 四份阶段文档，保留各阶段当时的范围、契约、验证与回滚记录，供历史追溯使用。当前能力与接口以 [完整配置与部署指南](full-guide.md) 和代码为准。

## Phase 0 — 范围与契约（原 `run-diagnostics-p0.md`）

本文档定义 #1391 的 **Phase 0（P0）**：在不引入新页面、不改变全局分析策略与 fallback 核心语义前提下，收敛契约边界并限定本轮运行时修复范围。

### 目标

- 给后续实现提供统一术语：`trace_id`、关键链路记录、诊断摘要、脱敏排障信息。
- 明确第一阶段范围，避免把需求扩成“完整可观测平台”。
- 固化 fail-open、安全与 retention 基线，降低回归风险。

### 当前文档范围（本轮）

- 本文件为 Phase 0 合同与验收边界文档，当前 PR 为 docs + runtime fix，本轮同步补齐 `baostock_fetcher.py`、`pytdx_fetcher.py`、`tushare_fetcher.py` 的 A 股代码归属边界，并配套由 `tests/infrastructure/providers/catalog/test_a_share_fetcher_code_conversion.py` 做回归验证。
- 归属边界必须覆盖裸码与前缀码（如 `000001`、`000001.SZ`、`SH000001`、`SH.000001`、`SZ000001`、`SZ.000001`），避免把 SH/SZ 前缀语义误归类。
- 若无新增 LLM 相关 provider/model/Base URL 语义迁移需求，本轮收敛 Tushare A 股归属范围至：`600/601/603/605/688`、`000/001/002/003/300/301`，并同步回归 `605`、`001`、`003`、`301` 场景；该范围变更不视为 provider 配置/路由策略扩展。

### 非目标

- 不做 OpenTelemetry / APM / Grafana 风格监控系统。
- 不在首版展示 p95、全量 Provider 调用明细、完整运维面板。
- 不改变现有数据源优先级、分析策略、通知策略。
- 不变更 LLM provider 列表、Base URL、`llm_call` 运行时参数、`REPORT_*` 配置语义与迁移路径；本轮改动限定在 A 股代码归属解析与诊断字段边界。

#### 验收边界（本轮）

- 本轮为 `fix`（docs + runtime fix），变更仅收敛 A 股代码归属语义，不改 provider 列表、Base URL、`llm_call` 运行时语义与 `REPORT_*` 配置迁移路径。
- `data_provider/baostock_fetcher.py`、`data_provider/pytdx_fetcher.py`、`data_provider/tushare_fetcher.py` 本轮只处理：
  - 裸码与后缀码：`000001`、`000001.SH`、`000001.SZ`
  - 前缀码：`SH000001`、`SH.000001`、`SZ000001`、`SZ.000001`
- `SH000001`/`SH.000001`/`SZ000001`/`SZ.000001` 场景为 correctness blocker，需由 `tests/infrastructure/providers/catalog/test_a_share_fetcher_code_conversion.py` 覆盖回归。
- 回归最小口径为 `(cd python && python -m pytest tests/infrastructure/providers/catalog/test_a_share_fetcher_code_conversion.py)` 与 `./scripts/ci_gate.sh`，并在 PR 描述同步结果与阻塞。
- 回滚优先级为恢复本轮三文件变更到合并前提交；其余范围不应一并回退。

### 术语与契约（P0 草案）

#### 1) `trace_id`

- 含义：一次分析运行链路的统一关联 ID。
- 要求：
  - 每次分析任务仅有一个 `trace_id`。
  - 可由入口生成，或由已有任务 ID 映射（例如 Web 任务）。
  - 出现在日志/结构化诊断中用于排障关联。

#### 2) `RunDiagnosticSummary`

- 含义：给用户看的简短运行诊断摘要。
- 建议字段（首版保持最小）：
  - `trace_id`
  - `status`：`ok` / `degraded` / `failed`
  - `data_status`：关键数据路径是否降级
  - `notify_status`：通知结果摘要
  - `error_hint`：脱敏后的简要原因
- 说明：这是用户可感知能力，不等于内部全量事件日志。

#### 3) 关键链路记录（最小集合）

首版只要求记录以下关键节点结果（成功/失败/降级 + 简短原因）：

- `realtime_quote`
- `daily_data`
- `llm_call`
- `report_persist`
- `notification_dispatch`

> 说明：`news`、`fundamental`、`capital_flow` 等放到后续扩展，不作为首版阻断项。

### 安全与稳定性边界（P0 必须遵守）

#### Fail-open

- 诊断记录失败不应阻断主分析流程。
- 即使诊断写入失败，也必须继续产出分析结果（除非主流程本身失败）。

#### 脱敏

- 复制排障信息中禁止包含密钥、token、完整 webhook URL、用户账号标识。
- 错误文案输出以摘要为主，避免泄露第三方返回的敏感原文。

#### Retention

- 诊断数据保留周期应可配置或可统一清理。
- 默认策略优先保守（例如仅保留必要时间窗），避免无限增长。

#### 兼容性

- 新字段应优先追加，不破坏现有 API / Web / Desktop 读取路径。
- 旧历史记录缺少新字段时应可安全回退。

### Phase 0 交付清单

- [x] 明确目标/非目标，防止范围失控。
- [x] 定义 `trace_id` 与 `RunDiagnosticSummary` 最小契约。
- [x] 明确首版关键链路覆盖范围。
- [x] 固化 fail-open、脱敏、retention、兼容性基线。

### 后续阶段（仅说明，不在 P0 实现）

- Phase 1：`trace_id` 贯通与关键链路最小记录落地。
- Phase 2：生成并持久化 `RunDiagnosticSummary`，支持复制脱敏排障信息。
- Phase 3：Web 侧最小展示（默认折叠），并补齐文档和回滚说明。

## Phase 1 — trace_id 与 ProviderRun 落地（原 `run-diagnostics-p1.md`）

本文档记录 #1391 Phase 1 的最小运行时落地范围：统一 `trace_id`，并为首批关键数据链路记录结构化 provider 尝试。

### 本轮范围

- API / Web 异步任务创建时，`TaskInfo` 使用 `task_id` 作为默认 `trace_id`。
- 任务列表、任务状态与 SSE 事件追加 `trace_id` 字段；旧客户端可忽略该字段。
- 同步分析使用本次 `query_id` 作为默认 `trace_id`。
- pipeline 运行时建立轻量诊断上下文，贯穿日线准备与单股分析。
- `data_provider/base.py` 对以下链路记录 `ProviderRun` 风格事件：
  - `daily_data`
  - `realtime_quote`
- 诊断记录写入内存上下文，随分析 `context_snapshot.diagnostics` 保存；旧历史记录缺少该字段时保持兼容。

### `ProviderRun` 字段

首版字段保持最小：

- `trace_id`
- `data_type`
- `provider`
- `operation`
- `success`
- `latency_ms`
- `error_type`
- `error_message_sanitized`
- `fallback_to`
- `record_count`
- `created_at`

错误摘要会做基础脱敏，避免输出 token、API key、Authorization、Cookie、包含敏感参数的 webhook URL 等内容。

### 稳定性边界

- 诊断记录失败只记录 warning，不影响主分析、数据源 fallback 或历史保存。
- 本轮不新增配置项，不改变数据源优先级，不改变 fallback 策略。
- 本轮不新增 Web 展示组件；`trace_id` 和 provider runs 先进入 API/SSE/历史快照，供后续 Phase 2/3 聚合与展示复用。

### 验证建议

```bash
(cd python && python -m pytest tests/application/runtime/test_run_diagnostics_p1.py tests/integration/analysis/::AnalysisApiContractTestCase::test_get_analysis_status_normalizes_completed_queue_result_contract)
(cd python && python -m py_compile src/application/runtime/run_diagnostics.py src/application/runtime/task_queue.py src/application/analysis/analysis_service.py src/application/analysis/pipeline.py data_provider/base.py api/v1/schemas/analysis.py api/v1/endpoints/analysis.py)
```

## Phase 2 — 诊断摘要与复制排障信息（原 `run-diagnostics-p2.md`）

本文档记录 #1391 Phase 2 的后端落地范围：基于 Phase 1 的 `trace_id` 与 provider run 记录，生成用户可读的运行诊断摘要，并提供可复制的脱敏排障文本。

### 本轮范围

- 新增 `RunDiagnosticSummary` 聚合逻辑，输出总体状态：
  - `normal` / 正常
  - `degraded` / 部分降级
  - `failed` / 失败
  - `unknown` / 未知
- 摘要覆盖以下关键链路：
  - 实时行情
  - 日线数据
  - 新闻搜索
  - LLM
  - 通知
  - 历史保存
- `AnalysisService` 同步/异步任务结果追加可选 `diagnostic_summary`。
- 新增历史报告诊断 API：

```http
GET /api/v1/history/{record_id}/diagnostics
```

`record_id` 支持历史记录主键 ID 或 `query_id`，返回诊断摘要与 `copy_text`。

### 复制排障信息

`copy_text` 是面向 issue/排障的纯文本，包含：

- `trace_id`
- `query_id`
- `stock_code`
- `trigger_source`
- 总体 `data_status`
- 实时行情、日线、新闻、LLM、通知、历史保存的简短状态
- 首要原因

生成前会复用运行诊断脱敏规则，避免输出 token、API key、Authorization、Cookie、webhook URL、邮箱密码、代理凭据等敏感信息。

### 兼容性边界

- 本轮不新增配置项，不改变数据源优先级，不改变 fallback 策略。
- 本轮不改变任何 LLM/provider/Base URL/配置迁移语义，仅新增历史快照中的诊断字段与查询接口。
- API 只追加可选字段和新增只读接口；旧客户端可忽略。
- 旧报告没有 `context_snapshot.diagnostics` 时返回 `unknown`，不报错。
- 通知诊断在当前任务上下文中记录；历史报告如果保存时尚无通知证据，会在摘要中显示通知结果未知。
- 诊断摘要生成失败不得影响报告读取或分析主流程。

#### 结构化检测告警澄清

- 自动化检测命中的“模型/provider/base URL 兼容风险”来源是：`src/application/agent/factory.py` 新增了 `agent_max_steps` 与 `agent_orchestrator_timeout_s` 的 **数字安全兜底**（`_coerce_config_int`），因此扫描可能将其误识别为配置敏感路径；该命中属于测试与路由保护触发，不是运行时配置或兼容语义变更。
- 当数值配置存在非法值时，系统会记录 `warning` 到 `src.agent.factory` 日志（示例：`[AgentFactory] Invalid value for agent_max_steps...`），并回退到默认值；日志用于定位“参数未生效”类问题，与模型/provider/base URL 兼容性独立。
- 本轮确认无静默迁移/清空/改写：
  - `src/application/analysis/pipeline.py` 与 `src/application/analysis/analysis_service.py` 仅新增诊断记录，不修改 `Config` 中任何 `litellm_model`、`agent_litellm_model`、`openai_base_url` 或 channel `LLM_*` 字段。
  - `src/application/agent/factory.py` 的 `_coerce_config_int` 只在构建执行参数时计算 `max_steps` 与 `timeout_seconds`，并且不写回到 `config` 对象；`litellm_model`、`agent_litellm_model`、`openai_base_url` 原值在构造链路中完整透传。
  - 本轮不触发 `Config` 的运行时清理、持久化回写或迁移流程，因此不存在写回导致运行时配置被重写的风险。
- 回归验证：`tests/application/agent/::TestAgentConfig::test_build_agent_executor_does_not_mutate_llm_route_config` 与 `tests/application/agent/::TestAgentConfig::test_build_agent_executor_multi_arch_does_not_mutate_llm_route_config` 明确断言上述字段在 `build_agent_executor` 后保持原值。
- 回退路径：如需恢复到旧行为，移除本轮相关提交；或将 `diag_*` 字段从 `context_snapshot`/`RunDiagnosticSummary` 的反序列化链路中移除。主链路与模型/provider 配置无需额外迁移或修复。

### 验证建议

```bash
(cd python && python -m pytest tests/application/runtime/test_run_diagnostics_p2.py tests/application/runtime/test_run_diagnostics_p1.py)
(cd python && python -m py_compile src/application/runtime/run_diagnostics.py src/application/history/read_model.py api/v1/endpoints/history.py api/v1/schemas/history.py)
```

## Phase 3 — 运行流与 Web 展示（原 `run-diagnostics-p3.md`）

本文档记录 #1391 Phase 3 的交付范围：在不新增配置的前提下，补齐运行诊断可见性并将历史排障信息回填到后端上下文快照，便于自部署环境快速定位异常。

### 本轮范围

- 历史报告详情新增默认折叠的「运行诊断 / 数据可靠性」区域；#1523 后 Web 展示标题调整为「运行诊断 / 运行状态」，历史阶段标题不变。
- 任务面板对进行中任务展示默认折叠的 trace 信息，便于和后端日志、SSE、历史报告诊断串联。
- 历史报告通过只读接口拉取诊断摘要：

```http
GET /api/v1/history/{record_id}/diagnostics
```

- 同步分析响应若已经带有 `diagnostic_summary`，前端可直接展示，不额外请求历史接口。
- 诊断面板支持复制后端生成的脱敏 `copy_text`，用于 issue 或部署排障。
- 分析链路在保存历史后会补齐任务/Provider/LLM/通知诊断到 `context_snapshot.diagnostics`，历史诊断接口统一聚合为用户可读摘要。
- 首页运行流面板复用同一 RunFlowSnapshot 契约展示 active task、completed report 与大盘复盘；active task 通过任务 SSE 的可选增量事件实时追加事件流，完成或断线后再 refetch 快照保证最终一致。

### 运行流实时增量

运行流增量不新增独立 SSE endpoint，继续复用：

```http
GET /api/v1/analysis/tasks/stream
```

兼容契约：

- 事件类型仍为 `task_progress`。
- 原有 task payload 字段保持不变。
- 当本次进度更新来自运行诊断时，可选追加 `flow_event` 字段；旧客户端忽略该字段即可。
- `flow_event` 使用与 `RunFlowSnapshot.events[]` 相同的脱敏事件结构：`id`、`timestamp`、`severity`、`type`、`node_id`、`title`、`message`、`metadata`。
- active task 可追加 `provider_run_started` / `llm_run_started` 实时事件；这些事件只用于运行中的 running 卡片展示，完成后由同 `node_id` 的 `provider_run` / `llm_run` 结果事件覆盖状态，历史诊断仍以最终结果为准。
- 后端 TaskQueue 只为每个 active task 保留最近 N 条运行流事件，避免内存无限增长；完整历史仍以 `context_snapshot.diagnostics` 和历史 RunFlowSnapshot 为准。

示例：

```json
{
  "task_id": "3f87...",
  "trace_id": "3f87...",
  "stock_code": "600519",
  "status": "processing",
  "progress": 64,
  "message": "LLM 正在生成分析结果",
  "flow_event": {
    "id": "flow_0002",
    "timestamp": "2026-06-08T22:30:24",
    "severity": "success",
    "type": "llm_run",
    "node_id": "llm_analysis_1",
    "title": "LLM 成功",
    "message": "LLM deepseek-chat 成功"
  }
}
```

运行诊断记录函数会在 provider、LLM、历史保存、通知记录成功写入内存诊断后 fail-open 触发 event sink。sink 失败只记录 warning，不改变分析、保存或通知的成功/失败判定。

新闻情报搜索也纳入同一 provider 诊断语义：`SearchService.search_stock_news()` 会以 `data_type=news_search` 记录 Tavily、SearXNG、Bocha、Brave 等搜索 provider 的尝试、过滤后结果数、缓存命中和失败原因。多个搜索 provider 连续尝试时，Web 运行流主图默认聚合为一个“新闻舆情”节点，卡片展示 provider 链路与状态，节点详情展示成功/失败次数、fallback / retry 次数；需要排障时可展开该聚合节点查看单次 provider 尝试。

运行流拓扑的数据来源泳道优先按节点开始时间排序；provider / LLM 节点若只有完成时间和耗时，会以 `ended_at - duration_ms` 推导 `started_at`，并在卡片上展示开始时间。无可用时间的节点保留原展示顺序作为兜底。主图表达“入口 -> 数据来源 -> ContextPack -> LLM -> 保存/通知”的流程结构；完整排障细节保留在事件流、节点详情和聚合节点展开态中。

Web 运行流主图使用前端内部展示模型，不改变后端 `RunFlowSnapshot` 契约：

- provider attempts 按 `metadata.data_type` 聚合为数据来源节点，例如实时行情、日线数据、新闻舆情。
- `context_block_*` 节点默认折叠进 `ContextPack` 详情，避免与 provider attempts 在数据来源泳道混排。
- 点击聚合节点可在详情区查看 attempts 表格；点击“展开尝试”后，当前聚合组的子 provider 节点会回到拓扑中。
- 事件流仍展示完整事件；事件关联节点会映射到当前可见节点，折叠时指向聚合节点，展开时指向具体 attempt。
- 拓扑连线使用多连接点策略：横向主流程走左右端口，同泳道上下关系走底部到顶部，fallback / retry 继续使用文字标签与虚线样式表达。

### 运行流 API

```http
GET /api/v1/analysis/tasks/{task_id}/flow
GET /api/v1/history/{record_id}/flow
```

- 两个接口返回同一 `RunFlowSnapshot` 契约。
- active task 缺少 diagnostics 时返回 skeleton flow，不伪造 provider / LLM 事件。
- active task 若已有 recent `flow_event`，snapshot 会返回这些真实事件，并可根据事件中的节点元数据补出临时节点。
- completed history 优先从 `context_snapshot.diagnostics` 与 `analysis_context_pack_overview` 构建完整拓扑。
- 大盘复盘历史记录使用 `code=MARKET`、`report_type=market_review`，同样走 `/history/{record_id}/flow` 与 Web 运行流面板，不提供单独 UI 分叉。
- `cancel_requested` 与 `cancelled` 是合法运行流状态；用户取消不应映射为 `failed`。

### 运行流视图

运行流视图是在运行诊断摘要之上的可视化排障入口，用于串联一次分析从触发、数据获取、ContextPack 组装、LLM 生成到保存/通知的大致链路。它不替代诊断摘要的 `copy_text`，而是把同一批脱敏诊断证据组织为节点、连线、事件和摘要指标，方便从 Web 首页快速定位异常或降级环节。

后端提供两个只读快照接口：

```http
GET /api/v1/analysis/tasks/{task_id}/flow
GET /api/v1/history/{record_id}/flow
```

- `tasks/{task_id}/flow` 面向活跃任务。任务仍在内存队列中时优先返回当前任务快照；任务已完成时可按同一 `task_id/query_id` 尝试读取历史诊断。缺少诊断时返回 skeleton flow，不伪造 provider、LLM 或通知事件。
- `history/{record_id}/flow` 面向历史报告，支持历史记录主键 ID 或可解析的 `query_id`。普通个股分析与 `MARKET/market_review` 大盘复盘复用同一 `RunFlowSnapshot` 契约。
- 同一页面触发个股分析时，个股流程可按需生成或复用当日大盘上下文；这不是独立的个股分析步骤，而是 Prompt 背景生成。后台会用独立 `market_context_*` query_id 与 `scope=daily_market_context` 保存该大盘上下文，避免与个股报告共用 query_id。
- 为兼容早期已写入的混合诊断，运行流会在读取历史时按报告类型做低风险过滤：`MARKET/market_review` 记录隐藏个股行情、日线、技术、基本面与筹码 provider 节点；个股记录隐藏首次个股行情前的大盘新闻搜索，以及首次个股 LLM 前的大盘保存/通知节点。
- 通知跳过或未配置时允许 `attempts=0`，运行流展示为 skipped，不再因 Pydantic 校验失败导致 `/flow` 返回 500。
- 快照顶层包含 `summary`、`lanes`、`nodes`、`edges`、`events` 和 `generated_at`。节点状态使用 `pending/running/success/failed/degraded/fallback/timeout/cancel_requested/cancelled/skipped/unknown`，其中用户取消类状态不会被映射成 `failed`。
- 旧历史、缺失 `context_snapshot.diagnostics` 或证据不足时，后端返回 `unknown` 或 skeleton 节点；Web 端按空/未知状态展示，不影响报告详情读取。

Web 入口：

- 首页活跃任务卡片提供运行流入口，打开抽屉后按 `task_id` 拉取任务快照。
- 历史报告摘要和运行诊断区域提供运行流入口，打开抽屉后按历史记录 ID 拉取历史快照。
- 面板展示摘要、基础拓扑、事件流和节点详情；复杂拓扑聚合、实时增量事件和布局 polish 会在后续阶段继续收敛。

脱敏与兼容边界：

- 运行流只读取既有任务信息、历史结果和 `context_snapshot.diagnostics` 中的低敏诊断字段，不新增配置项、不改数据库结构、不迁移旧历史。
- `model`、`provider`、`fallback_model` 仅用于展示实际诊断到的调用信息；不参与模型选择、请求路由、Base URL 解析或配置保存。
- `metadata`、错误信息和本地路径会经过后端裁剪与脱敏，避免暴露 API key、token、cookie、webhook、prompt/raw response、代理头和本地绝对路径。
- 回滚时可移除 Web 入口和查询路径；后端新增只读快照接口不改变原有分析、历史、通知或诊断摘要接口的成功/失败语义。

### 状态文案

总体状态：

- `normal`：正常
- `degraded`：部分降级
- `failed`：失败
- `unknown`：未知

组件状态：

- `ok`：正常
- `degraded`：最近失败后已降级
- `failed`：失败
- `unknown`：未知
- `not_configured`：未配置
- `skipped`：已跳过

### 交互边界

- 诊断区域默认折叠，避免挤占报告主要内容。
- 首屏只展示总体状态、首要原因和必要 trace 信息。
- 组件状态与高级 JSON 字段放在展开区域内；高级字段再二级折叠，避免信息过载。
- 旧报告、接口失败或证据不足时显示 `unknown`，不影响报告阅读。

### 兼容性边界

- 本轮不新增 `.env` 配置项，不修改数据库结构，不引入数据迁移。
- Web 只消费 Phase 1/2 已追加的可选字段和只读诊断接口；后端补齐 `src/application/analysis/pipeline.py`、`src/application/runtime/run_diagnostics.py`、`src/storage.py` 与 `src/application/history/read_model.py` 的诊断持久化与刷新逻辑，并通过 `api/v1/endpoints/history.py` 提供可读端点。
- 后端变更范围包含任务编排、历史保存后补写、历史诊断查询与通知结果诊断记录；这些链路只追加 `context_snapshot.diagnostics` 诊断快照和摘要，不改变分析主流程、通知发送成败语义或历史报告主体字段。
- 复制文本由后端生成并脱敏；前端只负责展示和复制。
- Desktop 复用 Web 构建产物，未单独改动 Electron 主进程或打包脚本。
- 运行时配置/模型/provider/base_url 兼容语义不调整：除诊断持久化链路外，不改 provider 优先级、LiteLLM 路由、运行时清理与配置回退逻辑。
- 旧历史与旧配置兼容规则不变：历史诊断查询新增可选字段不影响既有历史查询响应解析；回退方式为移除本轮展示与相关前端查询路径，或按现有指南恢复模型和配置。
- 回滚策略：优先回退前端展示与查询入口；若需完全隔离新增链路，可回滚本轮 PR（回退后保留历史记录原有响应，新增诊断端点不再在 Web 中展示）。

#### 结构化检测澄清

本轮 review 的结构化检测命中了外部模型/API 兼容和运行时配置迁移风险；复核后结论如下：

- 模型名/provider/Base URL：本轮不新增、不替换、不重排任何模型名、provider、Base URL、channel 或 fallback 默认值，也不改变 `LITELLM_MODEL`、`AGENT_LITELLM_MODEL`、`VISION_MODEL`、`LITELLM_FALLBACK_MODELS`、`OPENAI_*`、`GEMINI_*`、`ANTHROPIC_*`、`DEEPSEEK_*` 的解析优先级。
- SDK/依赖默认值：本轮不修改 `requirements.txt`、`package.json` 依赖约束或 LiteLLM/OpenAI-compatible 调用默认参数；外部来源仍以 `docs/llm-providers.md` 和 `docs/LLM_CONFIG_GUIDE*.md` 中已记录的官方文档与当前锁定依赖说明为准。
- 保存前清理/配置迁移：本轮不触发 `.env`、Web 设置页 channel、桌面端用户数据目录、Docker 运行时配置文件或历史旧配置的迁移、清理、删除、回写策略变更。
- 本轮实际运行时改动只把既有分析 trace、provider/LLM/通知结果和脱敏错误摘要写入 `context_snapshot.diagnostics`，并通过历史只读接口和 Web 默认折叠面板展示；诊断记录失败按 fail-open 处理，不改变分析或通知的成功/失败判定。
- 因此本次属于结构化检测误报/文档澄清；无新增官方来源、旧配置迁移步骤或 provider 回退路径需要执行。若需回退，按本节回滚策略移除诊断展示/查询入口即可，模型与运行时配置恢复路径不变。

### 兼容性回归与验证（PR 合并前关键证据）

- 后端回归覆盖：
  - `tests/application/analysis/pipeline/test_pipeline_market_phase_context.py`
  - `tests/infrastructure/providers/realtime/test_realtime_types.py`
  - `tests/application/runtime/test_scheduler_background.py`
  - `tests/integration/analysis/`（子集：诊断上下文入出参/状态查询契约）
  - `tests/application/history/read_model/`（子集：历史 API 与持久化链路）
- 覆盖关系：API 合约由 `tests/integration/analysis/` 与 `tests/application/history/read_model/` 覆盖；任务编排、历史保存和 `context_snapshot.diagnostics` 由 `tests/application/analysis/pipeline/test_pipeline_market_phase_context.py` 覆盖；通知路径通过 `./scripts/ci_gate.sh` 中的既有通知回归与导入检查兜底。
- 回归命令（PR 合并前至少确认全部通过）：

```bash
./scripts/ci_gate.sh
(cd python && python -m pytest tests/infrastructure/providers/realtime/test_realtime_types.py tests/application/runtime/test_scheduler_background.py tests/application/analysis/pipeline/test_pipeline_market_phase_context.py tests/integration/analysis/ tests/application/history/read_model/)
cd apps/hrs-web && npm run lint && npm run build
```

### 验证建议

```bash
cd apps/hrs-web
npm run lint
npm run build
```

可补充执行（非阻断）：

```bash
cd apps/hrs-web
npm test -- --run src/components/report/__tests__/ReportDiagnostics.test.tsx src/components/tasks/__tests__/TaskPanel.test.tsx src/hooks/__tests__/useTaskStream.test.tsx
```

可补充确定性脚本校验：

```bash
(cd python && python -m py_compile api/v1/endpoints/analysis.py api/v1/endpoints/history.py api/v1/schemas/analysis.py api/v1/schemas/history.py src/application/analysis/pipeline.py src/application/runtime/run_diagnostics.py src/storage.py)
```

### 回滚

最小回滚方式：revert Phase 3 PR。由于本轮为可选字段与可读接口增强，回滚后后端历史快照与已落库数据保留，Web 不再展示诊断面板与 trace 诊断入口。

