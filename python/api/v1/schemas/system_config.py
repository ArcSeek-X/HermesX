# -*- coding: utf-8 -*-
"""
@file: system_config.py
@description: 系统配置接口契约：动态表单字段元数据、配置读写与导入导出、首次配置引导、生成后端与 Agent 后端状态、LLM 通道与通知渠道连通性测试；由 api.v1.endpoints.system_config 返回。
@author: Lensgcx (GaoCangxiong)

System configuration API schemas.

Defines the metadata contract used to render the settings form, the
read/update/import/export payloads with optimistic locking, and the
connectivity smoke-test results for LLM and notification channels.

配置读写以 config_version 做乐观锁；敏感值以 mask_token 往返，未修改的掩码值在提交时会被跳过，避免把占位符写回 .env。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# LLM 能力探测项取值：json 结构化输出 / tools 工具调用 / vision 视觉输入 / stream 流式输出。
LLMCapabilityCheck = Literal["json", "tools", "vision", "stream"]
# 生成后端冒烟模式：text 纯文本调用 / json 结构化输出调用，默认 json。
GenerationBackendSmokeMode = Literal["text", "json"]
# 后端健康状态：not_tested 未测试 / passed 通过 / failed 失败 / skipped 跳过。
GenerationBackendHealthStatus = Literal["not_tested", "passed", "failed", "skipped"]
# 可测试的通知渠道取值闭包，逐项含义见 Literal 行尾注释。
NotificationTestChannel = Literal[
    "wechat",       # 企业微信
    "feishu",       # 飞书
    "dingtalk",     # 钉钉
    "telegram",     # Telegram Bot
    "email",        # 邮件 SMTP
    "pushover",     # Pushover
    "ntfy",         # ntfy.sh
    "gotify",       # Gotify
    "pushplus",     # PushPlus
    "serverchan3",  # Server酱³
    "custom",       # 自定义 Webhook
    "discord",      # Discord Webhook
    "slack",        # Slack Webhook
    "astrbot",      # AstrBot 机器人接入
]


class SystemConfigOption(BaseModel):
    """Select option metadata for frontend rendering.

    使用场景：下拉/单选控件的候选项；label 与 value 分离，便于本地化文案而不影响写入配置的取值。

    @author: Lensgcx (GaoCangxiong)
    """

    # 下拉项的展示文案。
    label: str
    # 下拉项实际写入配置的值。
    value: str


class SystemConfigDocLink(BaseModel):
    """Documentation link metadata for field help panels.

    使用场景：设置项帮助面板中的关联文档入口；href 由服务端提供，避免前端硬编码文档路径。

    @author: Lensgcx (GaoCangxiong)
    """

    # 帮助面板中展示的文档标题。
    label: str
    # 文档链接地址，由服务端下发避免前端硬编码。
    href: str


class SystemConfigFieldSchema(BaseModel):
    """Metadata schema for a single config field.

    使用场景：驱动设置页动态表单的渲染与校验；is_sensitive 决定值是否掩码，options / validation / docs 均由后端下发，保证表单与服务端校验规则同源。

    @author: Lensgcx (GaoCangxiong)
    """

    # Configuration key name：配置键名，必填。
    key: str = Field(..., description="Configuration key name")
    # Display title：表单_label 文案；缺省时前端回退显示 key。
    title: Optional[str] = Field(None, description="Display title")
    # Field description：字段用途说明，展示在帮助面板。
    description: Optional[str] = Field(None, description="Field description")
    # 配置分类：base / data_source / ai_model / notification / system / agent / backtest / uncategorized。
    category: Literal["base", "data_source", "ai_model", "notification", "system", "agent", "backtest", "uncategorized"]
    # 值类型：string / integer / number / boolean / array / json / time，决定解析与校验方式。
    data_type: Literal["string", "integer", "number", "boolean", "array", "json", "time"]
    # 表单控件：text / password / number / select / textarea / switch / time。
    ui_control: Literal["text", "password", "number", "select", "textarea", "switch", "time"]
    # 是否为敏感项；为 True 时读取值被掩码，提交掩码值会被跳过。
    is_sensitive: bool
    # 是否为必填项；决定首次配置引导是否将其计入缺失。
    is_required: bool
    # 是否允许在 Web 设置页编辑；只读项仅展示。
    is_editable: bool
    # 默认值字符串；None 表示无默认值或由运行时继承。
    default_value: Optional[str] = None
    # 候选项列表，元素可为纯字符串或带 label/value 的对象，默认空列表。
    options: List[str | SystemConfigOption] = Field(default_factory=list)
    # 校验规则字典（范围、正则等），与服务端校验同源，默认空字典。
    validation: Dict[str, Any] = Field(default_factory=dict)
    # 字段在分类内的展示顺序，升序排列。
    display_order: int
    # Stable localization key for detailed help content：稳定本地化键，避免帮助文案随 key 变化失效。
    help_key: Optional[str] = Field(None, description="Stable localization key for detailed help content")
    # Safe example values for help panels：可公开展示的安全示例值，默认空列表。
    examples: List[str] = Field(default_factory=list, description="Safe example values for help panels")
    # Related documentation links：关联文档链接列表，默认空列表。
    docs: List[SystemConfigDocLink] = Field(default_factory=list, description="Related documentation links")
    # Stable warning identifiers for help panels：稳定告警码，前端据此展示提示，默认空列表。
    warning_codes: List[str] = Field(default_factory=list, description="Stable warning identifiers for help panels")


class SystemConfigCategorySchema(BaseModel):
    """Category grouping metadata.

    使用场景：设置页按分类折叠字段；display_order 控制分类顺序，fields 为该类下的字段元数据列表。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分类稳定标识，用于前端分组与锚点。
    category: str
    # 分类展示标题。
    title: str
    # 分类用途说明；可为空。
    description: Optional[str] = None
    # 分类展示顺序，升序排列。
    display_order: int
    # 该分类下的字段元数据列表，必填。
    fields: List[SystemConfigFieldSchema]


class SystemConfigSchemaResponse(BaseModel):
    """Metadata response for dynamic frontend rendering.

    使用场景：设置页初始化拉取整份表单描述；schema_version 供前端判断是否需要刷新缓存的表单元数据。

    @author: Lensgcx (GaoCangxiong)
    """

    # 表单元数据版本，变更时前端应刷新缓存。
    schema_version: str
    # 按展示顺序排列的分类列表，必填。
    categories: List[SystemConfigCategorySchema]


class SystemConfigItem(BaseModel):
    """Config value entry with optional schema metadata.

    使用场景：读取当前配置值；敏感值以 mask_token 替换，raw_value_exists 区分「未配置」与「已配置但被掩码」。

    @author: Lensgcx (GaoCangxiong)
    """

    # populate_by_name=True：允许同时用 schema_ 与别名 schema 构造，兼容关键字 schema 与 Pydantic 基类属性冲突。
    model_config = ConfigDict(populate_by_name=True)

    # 配置项键名，与 .env 中的变量名一致，是校验问题的定位依据。
    key: str
    # 当前配置值；敏感项已被掩码替换为 mask_token。
    value: str
    # 原始值是否已配置；用于区分「未配置」与「已配置但被掩码」。
    raw_value_exists: bool
    # 当前 value 是否为掩码占位符；提交时该值会被跳过。
    is_masked: bool
    # 该键对应的字段元数据；对外序列化为 schema，未知键时为 None。
    schema_: Optional[SystemConfigFieldSchema] = Field(default=None, alias="schema")


class SystemConfigResponse(BaseModel):
    """Read response for current configuration values.

    使用场景：设置页读取全部配置；config_version 是后续更新的乐观锁凭据。

    @author: Lensgcx (GaoCangxiong)
    """

    # 配置版本号，用作乐观锁凭据；与服务端当前版本不一致时提交被拒绝。
    config_version: str
    # 本次响应用于替换敏感值的掩码字符串，提交时原样回传即视为未修改。
    mask_token: str
    # 当前配置键值对列表，必填。
    items: List[SystemConfigItem]
    # 配置最后更新时间；未知时为 None。
    updated_at: Optional[str] = None


class SetupStatusCheck(BaseModel):
    """One first-run setup readiness check.

    使用场景：首次运行引导逐项展示配置状态；status 区分已配置/继承默认/可选/待处理，next_step 给出下一步入口。

    @author: Lensgcx (GaoCangxiong)
    """

    # 该检查项对应的配置键或检查标识。
    key: str
    # 检查项展示标题。
    title: str
    # 检查项分类 base / ai_model / agent / notification / system。
    category: Literal["base", "ai_model", "agent", "notification", "system"]
    # 是否为必要项；为 True 且未配置时计入 required_missing_keys。
    required: bool
    # 检查状态：configured 已配置 / inherited 继承默认 / optional 可选 / needs_action 待处理。
    status: Literal["configured", "inherited", "optional", "needs_action"]
    # 该检查项的状态说明。
    message: str
    # 建议的下一步入口或操作提示；无需引导时为 None。
    next_step: Optional[str] = None


class SetupStatusResponse(BaseModel):
    """Read-only first-run setup status.

    使用场景：引导页判断是否可进入冒烟测试；required_missing_keys 明确指出还缺哪些必填项。

    @author: Lensgcx (GaoCangxiong)
    """

    # 必填配置是否全部就绪。
    is_complete: bool
    # 是否可以进入冒烟测试；可能受非必填但关键的能力约束。
    ready_for_smoke: bool
    # 仍缺失的必填配置键列表，默认空列表。
    required_missing_keys: List[str] = Field(default_factory=list)
    # 建议优先处理的检查项标识；全部就绪时为 None。
    next_step_key: Optional[str] = None
    # 逐项检查结果列表，默认空列表。
    checks: List[SetupStatusCheck] = Field(default_factory=list)


class GenerationBackendStatus(BaseModel):
    """Cheap status for one generation backend.

    ``health_status`` and ``last_error_*`` describe the current status request
    or the explicit smoke-test request only; they are not persisted history.

    使用场景：设置页展示各生成后端的可用性与能力；状态查询刻意轻量，不发起真实模型调用，冒烟测试才更新 health_status 与最近错误。

    @author: Lensgcx (GaoCangxiong)
    """

    # 生成后端稳定标识，作为路由与测试入参。
    backend_id: str
    # 后端类型 litellm / local_cli。
    backend_type: Literal["litellm", "local_cli"]
    # 底层供应商标识，用于展示与分组。
    provider_id: str
    # 当前配置下该后端是否可用。
    available: bool
    # 健康状态，默认 not_tested；仅反映本次状态查询或显式冒烟测试，不是持久历史。
    health_status: GenerationBackendHealthStatus = "not_tested"
    # 是否支持结构化 JSON 输出。
    supports_json: bool
    # 是否支持工具调用。
    supports_tools: bool
    # 是否支持流式输出。
    supports_stream: bool
    # 是否支持视觉输入。
    supports_vision: bool
    # 是否为当前主后端。
    is_primary: bool
    # 该后端的降级目标 ID；无降级配置时为 None。
    fallback_target: Optional[str] = None
    # 该后端允许的最大并发调用数。
    max_concurrency: int
    # 是否能提供用量统计；影响看板是否展示该后端的 token 数。
    usage_available: bool
    # 最近一次状态查询或冒烟测试的错误码；不是持久历史。
    last_error_code: Optional[str] = None
    # 最近一次错误的可读说明；不是持久历史。
    last_error_message: Optional[str] = None


class GenerationBackendStatusResponse(BaseModel):
    """Generation backend status payload.

    使用场景：设置页一次返回主后端、回退后端与全部后端列表，便于展示当前路由与降级目标。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当前主生成后端 ID。
    primary_backend_id: str
    # 当前回退后端 ID；未配置为 None。
    fallback_backend_id: Optional[str] = None
    # 主后端的完整状态，必填。
    primary: GenerationBackendStatus
    # 回退后端状态；未配置时为 None。
    fallback: Optional[GenerationBackendStatus] = None
    # 全部已配置后端的状态列表，默认空列表。
    backends: List[GenerationBackendStatus] = Field(default_factory=list)


class AgentBackendStatusResponse(BaseModel):
    """Compatibility status for the selected Agent Chat backend.

    使用场景：Agent 设置区提示后端是否可用、是否为实验特性及版本信息。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当前选中的 Agent Chat 后端标识。
    backend: str
    # 该后端在当前环境下是否可用。
    available: bool
    # 是否为实验特性；前端据此给出稳定性提示。
    experimental: bool
    # 后端版本字符串；无法探测时为 None。
    version: Optional[str] = None
    # 兼容性检查失败的错误码；正常时为 None。
    error_code: Optional[str] = None
    # 兼容性检查的说明文案；正常时可为 None。
    message: Optional[str] = None


class ExportSystemConfigResponse(BaseModel):
    """Export payload for raw `.env` backups.

    使用场景：导出配置备份；content 为可直接保存的 .env 文本，敏感值已按导出策略处理。

    @author: Lensgcx (GaoCangxiong)
    """

    # 可直接保存为 .env 的完整配置文本，必填。
    content: str
    # 导出时的配置版本号，导入时用于并发校验。
    config_version: str
    # 配置最后更新时间；未知时为 None。
    updated_at: Optional[str] = None


class SystemConfigUpdateItem(BaseModel):
    """Single key-value update item.

    使用场景：更新、校验、预览与导入预览共用的最小键值对；值统一为字符串，类型转换由服务端按字段元数据执行。

    @author: Lensgcx (GaoCangxiong)
    """

    # 配置项键名，与 .env 中的变量名一致，是校验问题的定位依据。
    key: str
    # 配置值字符串；类型转换由服务端按字段元数据执行。
    value: str


class GenerationBackendStatusPreviewRequest(BaseModel):
    """Unsaved-draft preview request for generation backend status.

    使用场景：表单未保存时预览后端状态；服务端按草稿值临时装配，不改写磁盘配置。

    @author: Lensgcx (GaoCangxiong)
    """

    # 未保存的表单草稿键值对，默认空列表。
    items: List[SystemConfigUpdateItem] = Field(default_factory=list)
    # 敏感值的掩码占位符，默认 ******；提交时原样回传的掩码会被服务端跳过，不写回配置。
    mask_token: str = "******"


class AgentBackendStatusPreviewRequest(BaseModel):
    """Unsaved-draft preview request for Agent Chat backend status.

    使用场景：切换 Agent 后端但尚未保存时预览兼容性。

    @author: Lensgcx (GaoCangxiong)
    """

    # 未保存的 Agent 相关草稿键值对，默认空列表。
    items: List[SystemConfigUpdateItem] = Field(default_factory=list)
    # 敏感值的掩码占位符，默认 ******；提交时原样回传的掩码会被服务端跳过，不写回配置。
    mask_token: str = "******"


class TestGenerationBackendRequest(BaseModel):
    """Explicit generation backend smoke-test request.

    使用场景：用户主动发起真实调用冒烟测试；timeout_seconds 上限 3600 秒，避免长请求无限占用。

    @author: Lensgcx (GaoCangxiong)
    """

    # 指定要测试的后端；为空时使用当前主后端。
    backend_id: Optional[str] = None
    # 冒烟模式 text / json，默认 json。
    mode: GenerationBackendSmokeMode = "json"
    # 未保存的草稿配置，便于测试尚未落库的改动，默认空列表。
    items: List[SystemConfigUpdateItem] = Field(default_factory=list)
    # 敏感值的掩码占位符，默认 ******；提交时原样回传的掩码会被服务端跳过，不写回配置。
    mask_token: str = "******"
    # 测试超时秒数，范围 1~3600；为空时使用服务端默认值。
    timeout_seconds: Optional[float] = Field(default=None, ge=1.0, le=3600.0)


class TestGenerationBackendResponse(BaseModel):
    """Generation backend smoke-test result.

    使用场景：冒烟测试端点返回是否成功、所用模式与更新后的后端状态。

    @author: Lensgcx (GaoCangxiong)
    """

    # 操作或测试是否成功。
    success: bool
    # 本次实际采用的冒烟模式。
    mode: GenerationBackendSmokeMode
    # 面向用户的结果或错误说明。
    message: str
    # 测试后的后端状态，含 health_status 与最近错误。
    status: GenerationBackendStatus


class UpdateSystemConfigRequest(BaseModel):
    """Update request payload.

    使用场景：保存设置表单；config_version 做乐观锁，items 至少一项，掩码值由服务端跳过以免写回占位符。

    @author: Lensgcx (GaoCangxiong)
    """

    # 配置版本号，用作乐观锁凭据；与服务端当前版本不一致时提交被拒绝。
    config_version: str
    # 敏感值的掩码占位符，默认 ******；提交时原样回传的掩码会被服务端跳过，不写回配置。
    mask_token: str = "******"
    # 保存后是否立即重载运行时配置，默认 True。
    reload_now: bool = True
    # 待更新的键值对，至少 1 项；值为 mask_token 的项会被跳过。
    items: List[SystemConfigUpdateItem] = Field(..., min_length=1)


class UpdateSystemConfigResponse(BaseModel):
    """Update operation result payload.

    使用场景：保存后回传实际生效数量；skipped_masked_count 说明有多少项因仍是掩码而未改动。

    @author: Lensgcx (GaoCangxiong)
    """

    # 操作或测试是否成功。
    success: bool
    # 配置版本号，用作乐观锁凭据；与服务端当前版本不一致时提交被拒绝。
    config_version: str
    # 实际写入的配置项数。
    applied_count: int
    # 因仍是掩码占位符而跳过的项数，防止把占位符写回配置。
    skipped_masked_count: int
    # 本次是否触发了运行时重载。
    reload_triggered: bool
    # 实际发生变更的配置键列表。
    updated_keys: List[str]
    # 非阻断性告警列表，默认空列表。
    warnings: List[str] = Field(default_factory=list)


class ValidateSystemConfigRequest(BaseModel):
    """Validation request payload.

    使用场景：保存前校验草稿；不写配置，只返回逐项问题。

    @author: Lensgcx (GaoCangxiong)
    """

    # 待校验的键值对，至少 1 项；校验不写配置。
    items: List[SystemConfigUpdateItem] = Field(..., min_length=1)


class ImportSystemConfigRequest(BaseModel):
    """Import request payload for raw `.env` backups.

    使用场景：从备份文本恢复配置；同样以 config_version 做并发保护。

    @author: Lensgcx (GaoCangxiong)
    """

    # 配置版本号，用作乐观锁凭据；与服务端当前版本不一致时提交被拒绝。
    config_version: str
    # 导入的原始 .env 文本，必填。
    content: str
    # 导入后是否立即重载运行时配置，默认 True。
    reload_now: bool = True


class ConfigValidationIssue(BaseModel):
    """Validation issue details.

    使用场景：定位某个配置键的校验失败原因；severity 为 warning 时不阻断保存，error 才阻断。

    @author: Lensgcx (GaoCangxiong)
    """

    # 配置项键名，与 .env 中的变量名一致，是校验问题的定位依据。
    key: str
    # 稳定问题码，前端据此给出针对性提示。
    code: str
    # 面向用户的结果或错误说明。
    message: str
    # 问题级别 error 阻断保存 / warning 仅提示。
    severity: Literal["error", "warning"]
    # 期望的取值或格式说明；不适用时为 None。
    expected: Optional[str] = None
    # 实际收到的值；敏感值需脱敏，不适用时为 None。
    actual: Optional[str] = None


class ValidateSystemConfigResponse(BaseModel):
    """Validation result payload.

    使用场景：校验端点返回总体是否通过及全部问题列表。

    @author: Lensgcx (GaoCangxiong)
    """

    # 是否存在阻断级问题；warning 不影响该值为 True。
    valid: bool
    # 全部校验问题列表，包含 warning。
    issues: List[ConfigValidationIssue]


class TestLLMChannelRequest(BaseModel):
    """Request payload for testing one LLM channel.

    使用场景：新增通道时验证连通性与能力；api_key 为空时可配合 use_saved_secret 复用已保存密钥，避免前端回传敏感值。

    @author: Lensgcx (GaoCangxiong)
    """

    # 通道或配置对象的展示名称，默认 channel，用于报告中标识来源。
    name: str = "channel"
    # 通道协议标识，默认 openai；resolved_protocol 回传实际生效值。
    protocol: str = "openai"
    # 通道 API 基础地址，默认空字符串；为空时按协议使用默认地址。
    base_url: str = ""
    # 通道密钥，默认空字符串；为空且 use_saved_secret=True 时复用已保存密钥。
    api_key: str = ""
    # 模型名称列表，默认空列表。
    models: List[str] = Field(default_factory=list)
    # 该通道是否启用，默认 True。
    enabled: bool = True
    # 单个通道测试超时秒数，默认 20.0。
    timeout_seconds: float = 20.0
    # 需要额外探测的能力列表，默认空列表。
    capability_checks: List[LLMCapabilityCheck] = Field(default_factory=list)
    # 是否复用已保存密钥，默认 False；避免前端回传敏感值。
    use_saved_secret: bool = False


class LLMCapabilityCheckResult(BaseModel):
    """Runtime capability smoke result for one requested check.

    使用场景：逐项说明 JSON / tools / vision / stream 能力探测结果，stage 指出失败发生在哪一步，retryable 决定是否值得重试。

    @author: Lensgcx (GaoCangxiong)
    """

    # 单项能力探测结果 passed / failed / skipped。
    status: Literal["passed", "failed", "skipped"]
    # 该项探测的可读结果说明。
    message: str
    # 机器可识别的错误码；成功时为 None。
    error_code: Optional[str] = None
    # 探测所处阶段，便于定位失败环节。
    stage: str
    # 失败是否可重试，默认 False。
    retryable: bool = False
    # 本次调用耗时毫秒数；超时未返回时为 None。
    latency_ms: Optional[int] = None
    # 结构化诊断信息字典，默认空字典。
    details: Dict[str, Any] = Field(default_factory=dict)


class TestLLMChannelResponse(BaseModel):
    """Response payload for one LLM channel connectivity test.

    使用场景：通道测试端点返回总体结果与实际生效的协议/模型，capability_results 按能力名索引明细。

    @author: Lensgcx (GaoCangxiong)
    """

    # 操作或测试是否成功。
    success: bool
    # 面向用户的结果或错误说明。
    message: str
    # 错误描述或错误码，具体含义由所属响应约定。
    error: Optional[str] = None
    # 机器可识别的错误码；成功时为 None。
    error_code: Optional[str] = None
    # 失败或探测所处的阶段标识，便于定位链路位置。
    stage: Optional[str] = None
    # 失败是否可重试，默认 False。
    retryable: Optional[bool] = None
    # 结构化诊断信息字典，默认空字典。
    details: Dict[str, Any] = Field(default_factory=dict)
    # 服务端最终判定并实际使用的协议；与请求值可能因自动识别而不同。
    resolved_protocol: Optional[str] = None
    # 实际用于测试的模型名；自动选择时与请求列表不同。
    resolved_model: Optional[str] = None
    # 本次调用耗时毫秒数；超时未返回时为 None。
    latency_ms: Optional[int] = None
    # 按能力名索引的探测结果，默认空字典。
    capability_results: Dict[str, LLMCapabilityCheckResult] = Field(default_factory=dict)


class NotificationTestAttempt(BaseModel):
    """One notification delivery attempt result.

    使用场景：一次测试可能向多个渠道尝试，逐渠道记录结果与 HTTP 状态，便于定位是配置错误还是渠道侧拒绝。

    @author: Lensgcx (GaoCangxiong)
    """

    # 本次尝试对应的通知渠道。
    channel: NotificationTestChannel
    # 操作或测试是否成功。
    success: bool
    # 面向用户的结果或错误说明。
    message: str
    # 投递目标（如 Webhook 地址或收件人）；未知时为 None。
    target: Optional[str] = None
    # 机器可识别的错误码；成功时为 None。
    error_code: Optional[str] = None
    # 失败阶段，默认 notification_send。
    stage: str = "notification_send"
    # 失败是否可重试，默认 False。
    retryable: bool = False
    # 本次调用耗时毫秒数；超时未返回时为 None。
    latency_ms: Optional[int] = None
    # 渠道返回的 HTTP 状态码；网络层失败时为 None。
    http_status: Optional[int] = None


class TestNotificationChannelRequest(BaseModel):
    """Request payload for testing one notification channel.

    使用场景：设置页用草稿配置发送测试消息；items 为未保存的键值草稿，title/content 提供默认测试文案。

    @author: Lensgcx (GaoCangxiong)
    """

    # 待测试的通知渠道，必填。
    channel: NotificationTestChannel
    # 未保存的草稿配置，用于测试尚未落库的改动，默认空列表。
    items: List[SystemConfigUpdateItem] = Field(default_factory=list)
    # 敏感值的掩码占位符，默认 ******；提交时原样回传的掩码会被服务端跳过，不写回配置。
    mask_token: str = "******"
    # 测试消息标题，默认「HRS 通知测试」，长度 1~80。
    title: str = Field(default="HRS 通知测试", min_length=1, max_length=80)
    # 测试消息正文，默认中文提示文案，长度 1~1000。
    content: str = Field(default="这是一条来自 HRS Web 设置页的通知测试消息。", min_length=1, max_length=1000)
    # 测试超时秒数，范围 1~120，默认 20.0。
    timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)


class TestNotificationChannelResponse(BaseModel):
    """Response payload for one notification channel connectivity test.

    使用场景：返回总体结果与逐渠道尝试明细；单渠道失败不影响其他渠道的尝试。

    @author: Lensgcx (GaoCangxiong)
    """

    # 操作或测试是否成功。
    success: bool
    # 面向用户的结果或错误说明。
    message: str
    # 机器可识别的错误码；成功时为 None。
    error_code: Optional[str] = None
    # 失败或探测所处的阶段标识，便于定位链路位置。
    stage: Optional[str] = None
    # 失败是否可重试，默认 False。
    retryable: bool = False
    # 本次调用耗时毫秒数；超时未返回时为 None。
    latency_ms: Optional[int] = None
    # 逐渠道投递尝试结果列表，默认空列表。
    attempts: List[NotificationTestAttempt] = Field(default_factory=list)


class DiscoverLLMChannelModelsRequest(BaseModel):
    """Request payload for discovering models from one LLM channel.

    使用场景：填写通道后拉取可用模型列表；与 TestLLMChannelRequest 类似但不做能力探测。

    @author: Lensgcx (GaoCangxiong)
    """

    # 通道或配置对象的展示名称，默认 channel，用于报告中标识来源。
    name: str = "channel"
    # 通道协议标识，默认 openai；resolved_protocol 回传实际生效值。
    protocol: str = "openai"
    # 通道 API 基础地址，默认空字符串；为空时按协议使用默认地址。
    base_url: str = ""
    # 通道密钥，默认空字符串；为空且 use_saved_secret=True 时复用已保存密钥。
    api_key: str = ""
    # 模型名称列表，默认空列表。
    models: List[str] = Field(default_factory=list)
    # 模型发现请求超时秒数，默认 20.0。
    timeout_seconds: float = 20.0
    # 是否复用已保存密钥，默认 False；避免前端回传敏感值。
    use_saved_secret: bool = False


class DiscoverLLMChannelModelsResponse(BaseModel):
    """Response payload for one LLM channel model discovery request.

    使用场景：把上游返回的模型列表回填到表单；resolved_protocol 说明实际按哪种协议解析。

    @author: Lensgcx (GaoCangxiong)
    """

    # 操作或测试是否成功。
    success: bool
    # 面向用户的结果或错误说明。
    message: str
    # 错误描述或错误码，具体含义由所属响应约定。
    error: Optional[str] = None
    # 机器可识别的错误码；成功时为 None。
    error_code: Optional[str] = None
    # 失败或探测所处的阶段标识，便于定位链路位置。
    stage: Optional[str] = None
    # 失败是否可重试，默认 False。
    retryable: Optional[bool] = None
    # 结构化诊断信息字典，默认空字典。
    details: Dict[str, Any] = Field(default_factory=dict)
    # 服务端最终判定并实际使用的协议；与请求值可能因自动识别而不同。
    resolved_protocol: Optional[str] = None
    # 从通道发现的可用模型列表，默认空列表。
    models: List[str] = Field(default_factory=list)
    # 本次调用耗时毫秒数；超时未返回时为 None。
    latency_ms: Optional[int] = None


class SystemConfigValidationErrorResponse(BaseModel):
    """Error payload for failed update validation.

    使用场景：更新请求校验失败时返回逐项问题，前端可直接高亮对应字段。

    @author: Lensgcx (GaoCangxiong)
    """

    # 错误描述或错误码，具体含义由所属响应约定。
    error: str
    # 面向用户的结果或错误说明。
    message: str
    # 导致更新被拒绝的逐项校验问题。
    issues: List[ConfigValidationIssue]


class SystemConfigConflictResponse(BaseModel):
    """Error payload for optimistic lock conflict.

    使用场景：配置已被他人修改时拒绝当前提交，current_config_version 供前端提示刷新后重试。

    @author: Lensgcx (GaoCangxiong)
    """

    # 错误描述或错误码，具体含义由所属响应约定。
    error: str
    # 面向用户的结果或错误说明。
    message: str
    # 服务端当前的配置版本号，前端应据此刷新后重试提交。
    current_config_version: str
