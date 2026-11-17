# -*- coding: utf-8 -*-
"""
@file: analysis.py
@description: 分析与异步任务契约：分析请求、大盘复盘触发、任务状态/列表、批量提交与重复任务错误体；由 api.v1.endpoints.analysis 使用，任务状态经 SSE 推送给前端。
@author: Lensgcx (GaoCangxiong)

===================================
分析相关模型
===================================

职责：
1. 定义分析请求和响应模型
2. 定义任务状态模型
3. 定义异步任务队列相关模型
"""

from typing import Optional, List, Any, Literal
from enum import Enum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from src.utils.analysis_metadata import SELECTION_SOURCE_PATTERN
from src.utils.market_review_region import normalize_market_review_region_strict


class TaskStatusEnum(str, Enum):
    """异步任务状态枚举。

    使用场景：任务状态查询与 SSE 事件；CANCEL_REQUESTED 表示已请求取消但工作线程尚未退出，与 CANCELLED 区分，避免前端提前清理任务。

    @author: Lensgcx (GaoCangxiong)
    """
    # 任务已入队、尚未开始执行。
    PENDING = "pending"
    # 任务正在执行中。
    PROCESSING = "processing"
    # 任务正常完成，结果可读。
    COMPLETED = "completed"
    # 任务执行失败，错误信息可读。
    FAILED = "failed"
    # 已收到取消请求，工作线程尚未确认退出。
    CANCEL_REQUESTED = "cancel_requested"
    # 任务已确认取消，不会再产生结果。
    CANCELLED = "cancelled"


# 分析阶段取值：auto 交由服务层按当前交易时段推断，其余三项为显式覆盖。
AnalysisPhase = Literal["auto", "premarket", "intraday", "postmarket"]


class AnalyzeRequest(BaseModel):
    """Analysis request parameters.

    使用场景：POST /api/v1/analysis 触发分析。stock_code 与 stock_codes 二选一；report_language / skills 同时接受驼峰别名，兼容旧前端。未传的语言与区域参数回退到运行时全局配置。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 单只股票代码；与 stock_codes 二选一，两者都为空时由服务端按默认池处理。
    stock_code: Optional[str] = Field(
        None, 
        description="单只股票代码", 
        json_schema_extra={"example": "600519"},
    )
    # 多只股票代码列表，触发批量分析；与 stock_code 二选一。
    stock_codes: Optional[List[str]] = Field(
        None, 
        description="多只股票代码（与 stock_code 二选一）",
        json_schema_extra={"example": ["600519", "000858"]},
    )
    # 报告类型 simple / detailed / full / brief，默认 detailed；由正则限制取值。
    report_type: str = Field(
        "detailed",
        description="报告类型：simple(精简) / detailed(完整) / full(完整) / brief(简洁)",
        pattern="^(simple|detailed|full|brief)$",
    )
    # 是否忽略缓存强制重新取数，默认 False；会增加数据源调用量。
    force_refresh: bool = Field(
        False,
        description="是否强制刷新（忽略缓存）"
    )
    # 是否异步执行，默认 False；开启后返回任务 ID 而非报告正文。
    async_mode: bool = Field(
        False,
        description="是否使用异步模式"
    )
    # 分析阶段覆盖，默认 auto；显式指定可跳过服务层的时段推断。
    analysis_phase: AnalysisPhase = Field(
        "auto",
        description="分析阶段覆盖：auto(自动推断) / premarket(盘前) / intraday(盘中) / postmarket(盘后)",
    )
    # 用户从自动补全中选中的名称，用于报告展示与选股审计；可为空。
    stock_name: Optional[str] = Field(
        None,
        description="用户选中的股票名称（自动补全时提供）",
        json_schema_extra={"example": "贵州茅台"},
    )
    # 用户原始输入（中文名、拼音缩写或代码），用于核对代码解析是否正确。
    original_query: Optional[str] = Field(
        None,
        description="用户原始输入（如茅台、gzmt、600519）",
        json_schema_extra={"example": "茅台"},
    )
    # 选股来源标识，受 SELECTION_SOURCE_PATTERN 约束；用于统计入口质量。
    selection_source: Optional[str] = Field(
        None,
        description="股票选择来源：manual(手动输入) | autocomplete(自动补全) | import(导入) | image(图片识别)",
        pattern=SELECTION_SOURCE_PATTERN,
        json_schema_extra={"example": "autocomplete"},
    )
    # 是否在完成后发送推送通知，默认 True；异步任务同样生效。
    notify: bool = Field(
        True,
        description="是否发送推送通知（Telegram/企业微信等）"
    )
    # 报告输出语言 zh / en / ko；None 表示回退到全局 REPORT_LANGUAGE，兼容驼峰别名 reportLanguage。
    report_language: Optional[Literal["zh", "en", "ko"]] = Field(
        None,
        validation_alias=AliasChoices("report_language", "reportLanguage"),
        description="本次分析报告输出语言；未传时使用全局 REPORT_LANGUAGE",
    )
    # 本次分析使用的策略 skill ID 列表；兼容旧字段 strategies，None 表示使用默认策略集。
    skills: Optional[List[str]] = Field(
        None,
        validation_alias=AliasChoices("skills", "strategies"),
        description="本次分析使用的策略 skill ID 列表；兼容 legacy strategies 字段",
        json_schema_extra={"example": ["bull_trend", "growth_quality"]},
    )

    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "report_type": "detailed",
            "force_refresh": False,
            "async_mode": False,
            "analysis_phase": "auto",
            "stock_name": "贵州茅台",
            "original_query": "茅台",
            "selection_source": "autocomplete",
            "notify": True,
            "report_language": "zh",
            "skills": ["bull_trend"]
        }
    })


class MarketReviewRequest(BaseModel):
    """Market review trigger parameters.

    使用场景：手动触发大盘复盘后台任务；region 经严格校验后规范化，非法输入整体拒绝，避免部分市场被分析造成结论不完整。

    @author: Lensgcx (GaoCangxiong)
    """

    # 复盘完成后是否发送推送通知，默认 True。
    send_notification: bool = Field(
        True,
        description="是否在大盘复盘完成后发送推送通知",
    )
    # 复盘报告语言；None 表示回退到全局 REPORT_LANGUAGE，兼容驼峰别名。
    report_language: Optional[Literal["zh", "en", "ko"]] = Field(
        None,
        validation_alias=AliasChoices("report_language", "reportLanguage"),
        description="本次大盘复盘报告输出语言；未传时使用全局 REPORT_LANGUAGE",
    )
    # 复盘市场范围 token（cn/hk/us/jp/kr/both），长度 1~64；both 只能单独使用，其余可逗号组合；非法输入整体拒绝，None 回退到全局 MARKET_REVIEW_REGION。
    region: Optional[str] = Field(
        None,
        min_length=1,
        max_length=64,
        description=(
            "本次大盘复盘市场覆盖。合法 token 为 cn、hk、us、jp、kr、both；"
            "both 只能单独使用，其余 token 可用逗号组合。输入会忽略大小写和 token 两侧空格、"
            "去重并按 cn,hk,us,jp,kr 排序；空值、空 token、未知 token、both 混用或超过 "
            "64 个字符会整体返回 4xx，不会部分执行。未传时使用运行时全局 MARKET_REVIEW_REGION。"
        ),
        json_schema_extra={
            "example": "cn,us",
            "examples": ["cn", "jp,kr", "both"],
        },
    )

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: Optional[str]) -> Optional[str]:
        """Strictly validate request input and return its canonical ordering.

        把大盘复盘市场范围严格校验并规范化：忽略大小写与 token 两侧空格、去重后按固定顺序输出。未知 token、空 token、both 混用等整体拒绝，避免任务只对部分市场执行。

        Args:
            value: 原始区域字符串，可为 None；长度上限由字段约束保证。

        Returns:
            Optional[str]: 规范化后的逗号分隔 token 串；入参为 None 时返回 None。

        Raises:
            ValueError: 含未知 token、空 token、both 与其他 token 混用等非法输入，由 Pydantic 转成 4xx 响应。

        Side Effects:
            无。
        """
        if value is None:
            return None
        return normalize_market_review_region_strict(value)


class MarketReviewAccepted(BaseModel):
    """Market review background task accepted response.

    使用场景：复盘任务提交后立即返回，前端据 task_id 轮询状态；region 回传规范化结果，便于用户确认实际覆盖范围。

    @author: Lensgcx (GaoCangxiong)
    """

    # 提交状态，固定 accepted；仅表示任务已接收，不代表执行成功。
    status: str = Field("accepted", description="提交状态")
    # 面向用户的提交提示。
    message: str = Field(..., description="提示信息")
    # 回传本次任务是否会在完成后发送通知，供前端确认。
    send_notification: bool = Field(..., description="是否发送通知")
    # 任务实际执行的规范化市场范围，可能与用户输入的大小写/顺序不同。
    region: str = Field(
        ...,
        description="本次任务实际执行的 canonical 市场范围",
        examples=["us", "jp,kr"],
    )
    # 贯穿本次任务的诊断 trace ID，供日志与排障串联；缺失时为 None。
    trace_id: Optional[str] = Field(
        None,
        description="本次后台任务的诊断 trace ID",
    )
    # 后台任务 ID；仅当任务确实提交成功时返回，限流或冲突时可为 None。
    task_id: Optional[str] = Field(
        None,
        description="任务 ID（仅当任务实际提交时返回）",
    )


class AnalysisResultResponse(BaseModel):
    """同步分析的完整结果响应。

    使用场景：async_mode=False 时直接返回报告；report 保持 Any 以兼容不同报告类型的结构演进。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 分析记录唯一标识，可用于回查历史报告。
    query_id: str = Field(..., description="分析记录唯一标识")
    # 贯穿本次任务的诊断 trace ID，供日志与排障串联；缺失时为 None。
    trace_id: Optional[str] = Field(None, description="诊断 trace ID")
    # 被分析的股票代码。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；代码映射失败或历史记录未保存时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 分析报告正文，结构随 report_type 变化，故保持 Any；无报告时为 None。
    report: Optional[Any] = Field(None, description="分析报告")
    # 本次运行的诊断摘要（降级、数据源等）；正常无降级时可为 None。
    diagnostic_summary: Optional[Any] = Field(None, description="运行诊断摘要")
    # 分析完成时间（ISO 8601），用于报告展示。
    created_at: str = Field(..., description="创建时间")
    
    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "query_id": "abc123def456",
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "report": {
                "summary": {
                    "sentiment_score": 75,
                    "operation_advice": "持有"
                }
            },
            "created_at": "2024-01-01T12:00:00"
        }
    })


class TaskAccepted(BaseModel):
    """异步任务接受响应。

    使用场景：任务入队后返回，前端用 task_id 轮询 / SSE 订阅；status 仅允许 pending / processing，完成态由状态接口给出。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 异步任务唯一标识，用于轮询任务状态与 SSE 订阅。
    task_id: str = Field(..., description="任务 ID，用于查询状态")
    # 贯穿本次任务的诊断 trace ID，供日志与排障串联；缺失时为 None。
    trace_id: Optional[str] = Field(None, description="诊断 trace ID")
    # 入队后的状态，仅允许 pending / processing，由正则约束。
    status: str = Field(
        ..., 
        description="任务状态",
        pattern="^(pending|processing)$"
    )
    # 入队提示信息；可为空。
    message: Optional[str] = Field(None, description="提示信息")
    # 本次请求的分析阶段，默认 auto，用于状态页回显。
    analysis_phase: AnalysisPhase = Field("auto", description="请求的分析阶段")
    
    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "task_abc123",
            "status": "pending",
            "message": "Analysis task accepted",
            "analysis_phase": "auto"
        }
    })


class BatchTaskAcceptedItem(BaseModel):
    """批量异步任务中单个成功提交项。

    使用场景：与 TaskAccepted 类似但额外带 stock_code，让前端按标的逐项更新提交结果。

    @author: Lensgcx (GaoCangxiong)
    """

    # 异步任务唯一标识，用于轮询任务状态与 SSE 订阅。
    task_id: str = Field(..., description="任务 ID，用于查询状态")
    # 贯穿本次任务的诊断 trace ID，供日志与排障串联；缺失时为 None。
    trace_id: Optional[str] = Field(None, description="诊断 trace ID")
    # 该成功提交项对应的股票代码，供前端逐项更新。
    stock_code: str = Field(..., description="股票代码")
    # 该标的任务的入队状态，仅允许 pending / processing。
    status: str = Field(
        ...,
        description="任务状态",
        pattern="^(pending|processing)$"
    )
    # 该标的的入队提示信息。
    message: Optional[str] = Field(None, description="提示信息")
    # 分析阶段：auto 自动推断 / premarket 盘前 / intraday 盘中 / postmarket 盘后。
    analysis_phase: AnalysisPhase = Field("auto", description="请求的分析阶段")

    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "task_abc123",
            "stock_code": "600519",
            "status": "pending",
            "message": "分析任务已加入队列: 600519",
            "analysis_phase": "auto"
        }
    })


class BatchDuplicateTaskItem(BaseModel):
    """批量异步任务中因重复而跳过的项。

    使用场景：同一股票已有进行中任务时返回，existing_task_id 让前端可跳转到已有任务而非报错。

    @author: Lensgcx (GaoCangxiong)
    """

    # 因已有进行中任务而被跳过的股票代码。
    stock_code: str = Field(..., description="股票代码")
    # 已存在的任务 ID，前端可据此跳转查看结果。
    existing_task_id: str = Field(..., description="已存在的任务 ID")
    # 重复原因说明，通常包含已有任务 ID。
    message: str = Field(..., description="错误信息")

    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "existing_task_id": "task_existing_123",
            "message": "股票 600519 正在分析中 (task_id: task_existing_123)"
        }
    })


class BatchTaskAcceptedResponse(BaseModel):
    """批量异步任务接受响应。

    使用场景：一次提交多只股票；成功与重复分别列出，单只重复不应导致整批失败。

    @author: Lensgcx (GaoCangxiong)
    """

    # 成功入队的任务列表；全部重复时为空列表。
    accepted: List[BatchTaskAcceptedItem] = Field(default_factory=list, description="成功提交的任务列表")
    # 因重复被跳过的标的列表；无重复时为空列表。
    duplicates: List[BatchDuplicateTaskItem] = Field(default_factory=list, description="重复而跳过的任务列表")
    # 整批提交的汇总说明，含成功数与跳过数。
    message: str = Field(..., description="汇总信息")

    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "accepted": [
                {
                    "task_id": "task_abc123",
                    "stock_code": "600519",
                    "status": "pending",
                    "message": "分析任务已加入队列: 600519",
                    "analysis_phase": "auto"
                }
            ],
            "duplicates": [
                {
                    "stock_code": "000858",
                    "existing_task_id": "task_existing_456",
                    "message": "股票 000858 正在分析中 (task_id: task_existing_456)"
                }
            ],
            "message": "已提交 1 个任务，1 个重复跳过"
        }
    })


class TaskStatus(BaseModel):
    """Task status model.

    使用场景：任务状态轮询与 SSE 事件；同时容纳个股分析结果与大盘复盘结果，互不相关的字段以 None 区分，历史 DB 缺列时 analysis_phase 也可能为空。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 异步任务唯一标识，用于轮询任务状态与 SSE 订阅。
    task_id: str = Field(..., description="任务 ID")
    # 贯穿本次任务的诊断 trace ID，供日志与排障串联；缺失时为 None。
    trace_id: Optional[str] = Field(None, description="诊断 trace ID")
    # 任务当前状态，取值受 TaskStatusEnum 约束。
    status: TaskStatusEnum = Field(
        ..., 
        description="任务状态",
    )
    # 执行进度百分比 0~100；尚未开始或无法估算时为 None。
    progress: Optional[int] = Field(
        None, 
        description="进度百分比 (0-100)",
        ge=0,
        le=100
    )
    # 个股分析结果；仅 completed 且为个股任务时存在。
    result: Optional[AnalysisResultResponse] = Field(
        None, 
        description="分析结果（仅在 completed 时存在）"
    )
    # 大盘复盘报告纯文本；仅复盘任务返回。
    market_review_report: Optional[str] = Field(
        None,
        description="大盘复盘任务返回的报告文本（仅大盘复盘任务）",
    )
    # 结构化大盘复盘载荷，供 Web 端按区块渲染；旧任务只有纯文本报告时为 None。
    market_review_payload: Optional[Any] = Field(
        None,
        description="Structured market-review payload for API/Web consumers.",
    )
    # 大盘复盘实际执行的规范化市场范围；非复盘任务或历史记录为 None。
    region: Optional[str] = Field(
        None,
        description="大盘复盘任务实际执行的 canonical 市场范围",
    )
    # 失败原因；仅 failed 状态有值。
    error: Optional[str] = Field(
        None, 
        description="错误信息（仅在 failed 时存在）"
    )
    # 股票名称；代码映射失败或历史记录未保存时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 用户原始输入文本，保留用于选股来源审计与问题复现。
    original_query: Optional[str] = Field(None, description="用户原始输入")
    # 选股来源：manual / autocomplete / import / image，受 SELECTION_SOURCE_PATTERN 约束。
    selection_source: Optional[str] = Field(
        None,
        description="选择来源",
        pattern=SELECTION_SOURCE_PATTERN,
    )
    # 请求的分析阶段；从旧 DB 记录回退读取时可能为 None。
    analysis_phase: Optional[AnalysisPhase] = Field(
        None,
        description="请求的分析阶段；无持久化字段的历史 DB fallback 可能为空",
    )
    # 本次分析使用的策略 skill ID 列表；未指定时为 None。
    skills: Optional[List[str]] = Field(None, description="本次任务使用的策略 skill ID 列表")
    
    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "task_abc123",
            "status": "completed",
            "progress": 100,
            "result": None,
            "market_review_report": None,
            "error": None,
            "stock_name": "贵州茅台",
            "original_query": "茅台",
            "selection_source": "autocomplete",
            "analysis_phase": "auto",
            "skills": ["bull_trend"]
        }
    })


class TaskInfo(BaseModel):
    """Task details model.

    Used for task list and SSE event delivery.

    使用场景：任务列表与 SSE 事件推送；相比 TaskStatus 增加时间戳与提交参数，便于前端还原任务上下文而无需回查数据库。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 异步任务唯一标识，用于轮询任务状态与 SSE 订阅。
    task_id: str = Field(..., description="任务 ID")
    # 贯穿本次任务的诊断 trace ID，供日志与排障串联；缺失时为 None。
    trace_id: Optional[str] = Field(None, description="诊断 trace ID")
    # 任务对应的股票代码；复盘任务可能使用占位值。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；代码映射失败或历史记录未保存时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 任务当前状态，取值受 TaskStatusEnum 约束。
    status: TaskStatusEnum = Field(..., description="任务状态")
    # 执行进度百分比 0~100，默认 0；与 TaskStatus 不同，此处始终有值。
    progress: int = Field(0, description="进度百分比 (0-100)", ge=0, le=100)
    # 当前阶段的状态消息，用于任务列表直接展示。
    message: Optional[str] = Field(None, description="状态消息")
    # 生成报告的类型，默认 detailed，用于列表标注。
    report_type: str = Field("detailed", description="报告类型")
    # 记录创建时间字符串，用于排序与展示。
    created_at: str = Field(..., description="创建时间")
    # 开始执行时间；仍在排队时为 None。
    started_at: Optional[str] = Field(None, description="开始执行时间")
    # 结束时间（完成、失败或取消）；进行中为 None。
    completed_at: Optional[str] = Field(None, description="完成时间")
    # 失败原因；仅任务状态为 failed 时有值。
    error: Optional[str] = Field(None, description="错误信息（仅在 failed 时存在）")
    # 用户原始输入文本，保留用于选股来源审计与问题复现。
    original_query: Optional[str] = Field(None, description="用户原始输入")
    # 选股来源：manual / autocomplete / import / image，受 SELECTION_SOURCE_PATTERN 约束。
    selection_source: Optional[str] = Field(
        None,
        description="选择来源",
        pattern=SELECTION_SOURCE_PATTERN,
    )
    # 提交时的分析阶段，默认 auto。
    analysis_phase: AnalysisPhase = Field("auto", description="请求的分析阶段")
    # 本次分析使用的策略 skill ID 列表；未指定时为 None。
    skills: Optional[List[str]] = Field(None, description="本次任务使用的策略 skill ID 列表")
    # 复盘任务实际执行的规范化市场范围；个股任务为 None。
    region: Optional[str] = Field(
        None,
        description="大盘复盘任务实际执行的 canonical 市场范围",
    )
    
    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "abc123def456",
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "status": "processing",
            "progress": 50,
            "message": "正在分析中...",
            "report_type": "detailed",
            "created_at": "2026-02-05T10:30:00",
            "started_at": "2026-02-05T10:30:01",
            "completed_at": None,
            "error": None,
            "original_query": "茅台",
            "selection_source": "autocomplete",
            "analysis_phase": "auto",
            "skills": ["bull_trend"]
        }
    })


class TaskListResponse(BaseModel):
    """任务列表响应模型。

    使用场景：任务中心首页；pending / processing 计数让前端直接展示队列概览，无需遍历 tasks 自行统计。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 任务总数，包含已完成与失败的任务。
    total: int = Field(..., description="任务总数")
    # 等待执行的任务数，用于队列概览。
    pending: int = Field(..., description="等待中的任务数")
    # 执行中的任务数，用于队列概览。
    processing: int = Field(..., description="处理中的任务数")
    # 任务明细列表，供前端渲染任务中心。
    tasks: List[TaskInfo] = Field(..., description="任务列表")
    
    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 3,
            "pending": 1,
            "processing": 2,
            "tasks": []
        }
    })


class DuplicateTaskErrorResponse(BaseModel):
    """重复任务错误响应模型。

    使用场景：单只股票分析遇进行中任务时返回 409 类错误，携带 existing_task_id 供前端跳转到已有任务。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 错误码，固定 duplicate_task，便于前端识别并跳转已有任务。
    error: str = Field("duplicate_task", description="错误类型")
    # 重复提交的说明文案。
    message: str = Field(..., description="错误信息")
    # 触发重复冲突的股票代码。
    stock_code: str = Field(..., description="股票代码")
    # 已存在任务的 ID，供前端跳转。
    existing_task_id: str = Field(..., description="已存在的任务 ID")
    
    # 仅用于 OpenAPI 展示请求/响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "duplicate_task",
            "message": "股票 600519 正在分析中",
            "stock_code": "600519",
            "existing_task_id": "abc123def456"
        }
    })
