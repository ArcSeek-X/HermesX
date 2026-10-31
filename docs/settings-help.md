# 设置页配置帮助维护说明

设置页配置帮助用于把配置项的关键说明放到 WebUI 内部，减少用户在设置页和文档之间反复切换。页面上仍保留短描述，详细说明通过配置项标题旁的 help icon 打开。

本文只说明帮助系统的维护规则，不替代完整配置文档。配置语义、默认值、运行时优先级和排障细节仍以 `.env.example`、`docs/full-guide.md` 及对应专题文档为事实源。

## 数据结构

后端配置注册表在 `src/config/registry.py` 中为字段追加帮助元数据：

- `help_key`：前端多语言帮助文案的稳定 key。
- `examples`：可直接展示的配置样例。敏感字段只能使用占位符，例如 `sk-xxxx`、`your_token`。
- `docs`：相关文档链接，优先指向仓库内已有专题文档或完整指南。
- `warning_codes`：面向前端或后续校验扩展的稳定提示 code。

前端长文案维护在 `apps/hrs-web/src/locales/settingsHelp.ts`：

- 默认展示中文文案。
- 英文文案保留同样结构，便于后续扩展语言切换。
- 文案应解释用途、取值说明、影响范围、注意事项和相关文档，不应复制完整专题文档。

## WebUI 语言说明（非配置项）

本项目新增独立的 WebUI 界面语言能力（`zh` / `en`），用于静态页面文案、导航与通用控件文案。该状态与 `REPORT_LANGUAGE` 解耦，不改写报告语言语义。

- 状态键：`hrs.uiLanguage`（`localStorage`，浏览器端持久化）。
- 初始化优先级：`localStorage` 有效值优先，其次识别浏览器语言（`zh-*` / `en-*`），最后回退 `zh`。
- 该语言开关不属于 `.env` 配置字段，不在 `system/config` 的可配置字段清单中体现。
- 界面切换会同步 `document.documentElement.lang`（`zh-CN` 或 `en`）以利于可访问性与无障碍语义。

## 覆盖范围

PR1 覆盖基础设施与首批代表性配置项：

- `STOCK_LIST`
- `LITELLM_MODEL`
- `LLM_CHANNELS`
- `FEISHU_WEBHOOK_URL`
- `WEBUI_HOST`

PR2 继续覆盖高频、易填错配置项：

- AI 模型运行时：Agent 主模型、fallback 模型、高级 YAML 路由、temperature、provider API Key、OpenAI-compatible Base URL。
- LLM Channels 编辑器内部字段：渠道名、协议、Base URL、API Key、模型列表、运行时能力检测、主模型、Agent 主模型、fallback、Vision 和 temperature。
- 数据源与搜索：Tushare、股票索引远程更新开关、实时行情优先级、实时技术指标、搜索 API Key、SearXNG、筹码分布、新闻窗口。
- 通知：Webhook、Telegram、邮件、Discord/Slack 等聊天平台、报告输出、Webhook SSL 校验。
- WebUI / auth / schedule / proxy：Host、Port、登录保护、可信反向代理、定时任务、交易日检查、网络代理。

PR3 registered-field slice / 阶段性补齐：聚焦 Web 设置页中实际展示/可配置字段的 Help 补齐，包括通用配置卡片当前可见字段和 AI legacy 条件可见字段：

- Agent 配置（22 字段）：问股生成方式、Agent 模式、最大推理步数、策略列表、策略目录、自然语言路由、架构、编排器模式、超时、风险否决、Deep Research 预算/超时、记忆、策略自动权重、策略路由、问股可见对话上下文压缩、事件监控开关/间隔、告警规则 JSON。普通用户只看到新的 `AGENT_BACKEND` 选择器；旧 `AGENT_GENERATION_BACKEND` 仅保留配置兼容。
- 回测配置（5 字段）：回测开关、评估窗口、最小记录年龄、引擎版本、中性回报带。
- 报告配置（9 字段）：仅推送摘要、显示模型名、模板目录、渲染引擎、完整性校验/重试、历史信号对比、逐股推送、合并邮件。
- 通知路由配置（9 字段）：报告/告警/系统错误渠道路由、去重/冷却、静默时段/时区、最低等级、每日摘要（预留）。
- 系统运行时（7 字段）：日志级别、调试模式、最大并发、分析间隔、大盘分析开关/市场/配色。
- AI legacy 与 Anspire 配置：provider 专用多 Key、模型名、温度、Vision 模型、max tokens 与 Anspire LLM 网关字段。
- 数据源与搜索：TickFlow、SerpAPI、Brave、Bocha、MiniMax、SearXNG 公共实例、BIAS 阈值和 Pytdx 服务器字段。
- 通知高级字段：飞书高级安全/应用字段、Telegram topic、Discord/Slack 高级字段、Pushover、ntfy、Gotify、PushPlus、ServerChan3、AstrBot 和自定义 Webhook 高级模板/鉴权字段。

本轮补齐（P2 前置条件 2 的批次 P1）：板块排行 / 涨跌停池路由（`SECTOR_*` / `LIMITPOOL_*` 各 3 项）与外部行情凭证（`ALPHAVANTAGE_API_KEY`、`FINNHUB_API_KEY`、`LONGBRIDGE_*` 4 项、`SOCIAL_SENTIMENT_*` 2 项）共 14 个字段，归入「数据源」分类。路由字段的 `options` 与各 manager 实际注册的 source 绑定，由 `tests/test_config_registry.py::TestP1DataSourceFieldsRegistered` 保证一致，避免设置页出现未接入的源名。

批次 P2（资讯源）补齐：实时快讯（`WSCN_LIVE_NEWS_*` 7 项）、财经日历（`WALLSTREETCN_CALENDAR_*` 4 项）、本地资讯池（`NEWS_INTEL_*` 4 项）与 NewsNow 聚合源（`NEWSNOW_BASE_URL`）共 16 个字段，归入「数据源」分类；help_key 按能力分为 `live_news` / `live_calendar` / `news_intel` / `newsnow` 四组。数值字段的 `validation.min/max` 必须等于 `parse_env_int` / `parse_env_float` 的收敛边界（越界值运行时会被静默 clamp），由 `TestP2NewsFieldsRegistered` 以真实 `Config._load_from_env()` 反证。

数值区间的两条路径（适用于所有 `number` / `integer` 注册字段）：设置页的保存 / validate 链路走 `SystemConfigService._validate_numeric_range`，越界值返回 `out_of_range`（severity=`error`）并阻止写入，不会静默改写用户输入；`parse_env_int` / `parse_env_float` 的 `minimum` / `maximum` clamp 只作用于 `.env` 与进程环境变量读取路径。因此 registry 里声明的边界同时是“前端拒绝阈值”和“`.env` 收敛目标”，两者必须保持一致，不能只按其中一条路径描述。回归覆盖见 `tests/test_system_config_service.py::test_validate_rejects_portfolio_risk_values_below_registry_min`。

下拉（`select`）字段的枚举同理分两条路径：`get_field_definition` 会从 `options` 自动派生 `validation.enum`，设置页保存列表外的值返回 `invalid_enum`（severity=`error`）；而 `.env` / 进程环境变量路径不报错，只按字段自身的解析语义处理（`MD2IMG_ENGINE` 非法值回落默认引擎，`WECHAT_MSG_TYPE` 则原样存储、由发送侧把非 `text` 的值当 `markdown` 处理）。枚举比较按字面值，因此大写值在设置页会被拒，而 `.env` 里会先归一成小写。

批次 P3（机器人与飞书事件订阅）补齐：机器人运行时（`BOT_ENABLED` / `BOT_COMMAND_PREFIX` / `BOT_ADMIN_USERS`）、飞书事件订阅安全（`FEISHU_VERIFICATION_TOKEN` / `FEISHU_ENCRYPT_KEY`）与飞书发送形态（`FEISHU_MAX_BYTES` / `FEISHU_SEND_AS_FILE` / `FEISHU_FOLDER_TOKEN`）共 9 个字段，归入「通知」分类（`EMAIL_SENDER_NAME` 复用已有 `settings.notification.email` 组）。本批的入库标准是“运行时存在读取方”：企业微信（`WECOM_*`）与 Telegram（`TELEGRAM_WEBHOOK_SECRET`）适配器尚未实现，`DISCORD_BOT_STATUS` 无消费代码，因此这 6 个键继续留在 `WEB_SETTINGS_PENDING_EXPOSURE`，不进入设置页；`TestP3BotFieldsRegistered` 同时锁定已注册字段形态、重启边界与“无读取方不得注册”三件事。

批次 P4（组合与风险）补齐：风险阈值与窗口（`PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT` / `PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT` / `PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT` / `PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO` / `PORTFOLIO_RISK_LOOKBACK_DAYS`，共用 `settings.system.portfolio_risk` 帮助组）与汇率在线刷新开关（`PORTFOLIO_FX_UPDATE_ENABLED`，`settings.system.portfolio_fx`）共 6 个字段，归入已有的「系统」分类（不新建前端闭合 union `SystemConfigCategory` 的 `portfolio` 分类）。这批阈值会写入风险报告的 `thresholds` 并参与持仓告警触发判定，因此文案必须同时说明灵敏度影响与区间语义；由 `TestP4PortfolioRiskFieldsRegistered` 锁定注册形态、help 分组、不标 `restart_required`、区间只声明下限与运行时 `minimum` 一致，以及 `_build_stop_loss` 的乘法语义。

批次 P5（报告转图片与企业微信消息形态）补齐：转图三键（`MARKDOWN_TO_IMAGE_CHANNELS` / `MARKDOWN_TO_IMAGE_MAX_CHARS` / `MD2IMG_ENGINE`，共用 `settings.notification.markdown_to_image` 帮助组）与企业微信两键（`WECHAT_MSG_TYPE` / `WECHAT_MAX_BYTES`，`settings.notification.wechat_delivery`）共 5 个字段，归入已有的「通知」分类。本批两个下拉字段是首次把“options 派生 enum → 保存拒写”这条路径带入设置页，因此 `TestP5ReportImageAndWechatFormFieldsRegistered` 与 `test_validate_rejects_p5_select_values_outside_options` 分别锁定选项集等于运行时真正接受的值集、以及列表外值被 `invalid_enum` 拒写。`VISION_MODEL`（写入归属已由「AI 模型接入」的通道编辑器卡片接管，注册会造成一键两面）与 `VISION_PROVIDER_PRIORITY`（除 `Config.validate()` 告警文案外无行为读取方，且与文档描述已漂移）继续留在 `WEB_SETTINGS_PENDING_EXPOSURE`，需先定调才能入库。

批次 P6（LLM 渠道开关）结论：唯一待评估的 `LLM_ANSPIRE_ENABLED` **不入库**，仍留在 `WEB_SETTINGS_PENDING_EXPOSURE`。它和上面段落里的例外是同一家族：前端把任何 `LLM_` 前缀的键当作「AI 模型接入」渠道编辑器的草稿键（`SettingsPage.tsx` 的 `isLlmChannelEditorDraftKey`），本键又正好匹配 `LLM_<渠道>_ENABLED` 正则，编辑器会按渠道名读回并写回它；因此注册会造成一键两面，而且在已配置渠道时 `ai_model` 分类会把这张卡片静默过滤，“注册 = 可在设置页编辑”并不成立。另外它只在 `LLM_CHANNELS` 里确实存在名为 `anspire` 的渠道时才会改变解析结果，其余场景是一个不生效的开关，不符合批次 P3 确立的“运行时确有读取方”入库标准。回归覆盖见 `tests/test_config_registry.py::TestP6LlmChannelSwitchStaysPending`。至此配置批次 P1–P6 收口，pending 表剩下 9 个键：因编辑器托管 / 无行为读取方 + 文档漂移 / 条件性不生效而待定的 3 个键（`VISION_MODEL`、`VISION_PROVIDER_PRIORITY`、`LLM_ANSPIRE_ENABLED`），以及平台适配器尚未实现的 6 个 P3 遗留键。

Issue #1512 收口后，Web 设置页只展示后端配置注册表中的正式字段。未注册的 `.env` key 不再作为普通可编辑设置项展示，避免 raw key、`Auto-inferred field metadata.` 和无 help 按钮的配置项进入中文界面；这些 key 仍可通过 `.env` 文件或导入/导出能力保留和维护。

例外：`LLM_CHANNELS` 声明的动态渠道详情键（如 `LLM_DEEPSEEK_API_KEY`、`LLM_MY_PROXY_MODELS`）会保留在配置接口返回中，供“AI 模型接入”编辑器读取和保存；它们不作为普通配置卡片展示，也不复用 `WEB_SETTINGS_HIDDEN_FROM_UI` 的运维隐藏语义。

暂不纳入 Web 设置页展示的运维/基础设施类变量包括 `DATABASE_PATH`、`SQLITE_*`、`USE_PROXY`、`PROXY_HOST`、`PROXY_PORT`、`HTTPS_PROXY`、`NO_PROXY`、`ENV_FILE` 等。若后续需要在 Web 中编辑这些字段，应先在 `src/config/registry.py` 中正式注册并补齐 help 元数据，而不是依赖自动推断。

所有未注册的运行时键必须由 `src/config/registry.py` 中的三张声明表之一收录，`tests/test_config_registry.py` 会强制校验 `src/config/settings.py` 的每个 `os.getenv` 键都落在其中：

| 声明表 | 语义 |
| --- | --- |
| `WEB_SETTINGS_HIDDEN_FROM_UI` | 运维、基础设施与内部调优参数，明确不在 Web 暴露 |
| `WEB_SETTINGS_PENDING_EXPOSURE` | 功能类字段，按 `P1`–`P6` 批次待注册；值即批次号 |
| `WEB_SETTINGS_LEGACY_ALIASES` | 被新键取代的兼容别名，旧键 → canonical 键 |

三张表与 `_FIELD_DEFINITIONS` 互不相交：字段正式注册后必须同时从声明表移除，否则测试会报告“既注册又声明”的矛盾状态；声明表中已失效的键（`config.py` 与 `.env.example` 都不再出现）同样会导致失败。

### 覆盖边界

- `settingsHelp.ts` 中的 `settings.llm_channel.*` 系列为 LLM 渠道编辑器内部字段说明，仅用于前端渲染，不对应 `.env` 的单独配置项；这是 PR2 中刻意的“内置扩展”设计，用于提升编辑器可用性。
- 其余 help 文案均应能从 `src/config/registry.py` 中某个字段的 `help_key` 映射到后端注册元数据，便于与文档源、`warning_codes` 一起统一维护。

## 事实源优先级

新增或修改帮助文案时，优先从以下位置核对：

1. `.env.example`：配置键名、默认值、样例格式和敏感占位符。
2. `docs/full-guide.md`：主要配置说明、运行入口和部署上下文。
3. `docs/LLM_CONFIG_GUIDE.md`、`docs/llm-providers.md`：LLM 优先级、Channels、provider/model、兼容边界和排障说明。
4. 专题文档：例如 `docs/bot/feishu-bot-config.md`、`docs/deploy-webui-cloud.md`、`docs/desktop-package.md`。
5. 代码实现和测试：当文档与代码不一致时，先以可执行实现为准，并同步修正文档。

## 维护边界

- 帮助文案不能改变配置保存、校验、运行时优先级、`.env` 写回或环境变量覆盖语义。
- 不展示真实密钥、账号、token、Webhook 完整值或本机绝对路径。
- LLM 相关示例如果写入具体 provider 前缀、模型名或 Base URL，必须能追溯到当前仓库文档或官方来源；否则应使用占位符或链接到事实源。
- 对第三方模型/API 的可用性、LiteLLM 兼容窗口或 provider fallback 规则，不在设置帮助中单独承诺；需要变更时必须同步更新专题文档和 PR 兼容性说明。
- 中英双语文案应保持同一语义范围。若只更新一种语言，需要在交付说明中写明原因。
- 首屏短描述保持简洁，详细说明放在 help dialog 中，避免 hover tooltip 与常驻短描述重复。

## 重启语义

设置页保存通常只写入 `.env` 并触发可运行时重载的配置刷新。帮助文案和 `warning_codes` 必须显式区分以下情况：

- `WEBUI_HOST`、`WEBUI_PORT`：监听地址和端口只在进程启动时绑定，保存后必须重启当前进程、Docker 容器或服务管理器才会生效。
- `RUN_IMMEDIATELY`：非 schedule 模式启动期单次运行配置，保存后不会让已运行的 WebUI/API 进程立即触发分析。
- Web 设置页不直接暴露 `SCHEDULE_TIME` / `SCHEDULE_TIMES` / `SCHEDULE_RUN_IMMEDIATELY` 等内部键；用户通过“定时任务”卡片维护启用状态、多个执行时间和立即执行一次。
- `SCHEDULE_ENABLED`：WebUI/API/Desktop 长运行进程（包括 `python main.py --serve --schedule`）会在保存后按新值启动或停止 runtime scheduler；纯 CLI schedule 模式（`python main.py --schedule`）仍按启动时参数和配置运行。
- `SCHEDULE_TIME`、`SCHEDULE_TIMES`：不是重启必需项。`SCHEDULE_TIMES` 为空时使用 `SCHEDULE_TIME`；已运行的 scheduler 会按新时间重建 daily jobs。
- `SCHEDULE_RUN_IMMEDIATELY`：schedule 模式启动行为，保存后不会让当前进程立即执行一次分析；手动执行请使用 runtime scheduler 的 run-now API。
- runtime scheduler 的 run-now API 只会在没有分析任务运行时接受请求；如果已有分析在执行，会返回忙碌状态，Web 设置页会提示稍后重试。
- `BOT_COMMAND_PREFIX`、`BOT_ADMIN_USERS`：命令分发器是单例，首次构建时读取这两个值，而设置页保存链路不会重置分发器，因此保存后必须重启进程才会用新前缀/新名单。
- `FEISHU_VERIFICATION_TOKEN`、`FEISHU_ENCRYPT_KEY`：飞书 Stream 客户端建连时读取，保存后需重启才会用新值验签/解密；只改 `.env` 同样需要重启。
- `BOT_ENABLED`：Webhook 命令入口按请求从 `Config` 单例读取，保存链路会 `Config.reset_instance()`，因此下一次回调即生效；它不断开已由 `FEISHU_STREAM_ENABLED` / `DINGTALK_STREAM_ENABLED` 在启动时建立的长连接。
- `FEISHU_MAX_BYTES`、`FEISHU_SEND_AS_FILE`、`FEISHU_FOLDER_TOKEN`、`EMAIL_SENDER_NAME`：通知服务实例构建时读取，保存后下一次通知即生效，不需要重启。
- `PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT`、`PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT`、`PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT`、`PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO`、`PORTFOLIO_RISK_LOOKBACK_DAYS`：风险报告按请求构建服务时读取，保存后下一次风险报告或持仓告警评估即生效，不需要重启。这些阈值参与告警触发判定（breach 模式比较止损线，near 模式比较“止损线 × 接近比例”），不是纯展示默认值。
- `PORTFOLIO_FX_UPDATE_ENABLED`：`refresh_fx_rates` 按调用读取配置，保存后下一次手动刷新请求即生效。只接受字面 `true`（大小写不敏感），写 `1` / `yes` 等同关闭；关闭后仍使用已缓存汇率，接口返回显式的 `refresh_enabled=false`。
- `WECHAT_MSG_TYPE`、`WECHAT_MAX_BYTES`、`MARKDOWN_TO_IMAGE_CHANNELS`、`MARKDOWN_TO_IMAGE_MAX_CHARS`：通知服务实例构建时读取（`WECHAT_*` 在 `WechatSender.__init__`，转图两键在 `NotificationService.__init__`），而 `get_notification_service()` 每次返回新实例、不缓存单例，因此保存后下一次通知即生效；`MD2IMG_ENGINE` 额外在每次转图调用时从 `Config` 单例读取。

以上生效语义只描述当前服务进程，不隐含“对任何部署形态都接管”。两类例外：① 进程 / 容器启动时注入的同名环境变量会在下次重启重新覆盖运行时文件中的保存值（非 `_WEBUI_RUNTIME_ENV_FILE_PRIORITY_KEYS` 名单内的键在冷启动时也以进程环境变量为准）；② GitHub Actions 每日任务（`.github/workflows/00-daily-analysis.yml`）不读也不持久化设置页写入的配置文件，其 `environment:` 里注入的键（如 `FEISHU_FOLDER_TOKEN` / `FEISHU_SEND_AS_FILE` / `EMAIL_SENDER_NAME` / `WECHAT_MSG_TYPE`，以及大量 LLM / 数据源 / 通知凭证）在该场景下以仓库 Variables / Secrets 为唯一真源，设置页保存对其无影响。其中 `WECHAT_MSG_TYPE` 即使未配 Variables / Secrets 也会被注入字面 `markdown`（工作流里的 `|| 'markdown'` 默认），因此 Actions 上会覆盖 `.env` 里的同名设置。
