# -*- coding: utf-8 -*-
"""
@file: agent.py
@description: Agent 对话端点：技能与模型列表、后端状态、同步/流式对话、深度研究、会话增删改查与通知转发；由 api.v1.router 挂到 /api/v1/agent，SSE 流式执行与取消由本模块的活动流注册表协调。
@author: Lensgcx (GaoCangxiong)

Agent API endpoints.

Exposes regular and streaming chat, deep research, session management
and runtime backend/model discovery.
"""

import asyncio
import json
import logging
import threading
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from api.deps import get_agent_conversation_service
from api.v1.schemas.system_config import AgentBackendStatusResponse
from src.application.agent import AgentConversationService
from src.config import get_config
from src.application.runtime.agent_model import list_agent_model_deployments

# Tool name -> Chinese display name mapping
# 工具标识到中文展示名的映射，供 SSE 进度事件直接渲染，避免前端硬编码一套翻译。
# 工具标识到中文展示名的静态映射；新增工具时需同步登记，否则 SSE 事件回退显示原始标识。
TOOL_DISPLAY_NAMES: Dict[str, str] = {
    "get_realtime_quote":         "获取实时行情",
    "get_daily_history":          "获取历史K线",
    "get_chip_distribution":      "分析筹码分布",
    "get_analysis_context":       "获取分析上下文",
    "get_stock_info":             "获取股票基本面",
    "search_stock_news":          "搜索股票新闻",
    "search_comprehensive_intel": "搜索综合情报",
    "analyze_trend":              "分析技术趋势",
    "calculate_ma":               "计算均线系统",
    "get_volume_analysis":        "分析量能变化",
    "analyze_pattern":            "识别K线形态",
    "get_market_indices":         "获取市场指数",
    "get_sector_rankings":        "分析行业板块",
    "get_skill_backtest_summary": "获取技能回测概览",
    "get_strategy_backtest_summary": "获取策略回测概览",
    "get_stock_backtest_summary": "获取个股回测数据",
}

# 模块级日志器，记录 Agent 执行与 SSE 流异常。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/agent。
router = APIRouter()

# 活跃 Codex SSE 流注册表：request_id -> 取消事件；注册与注销均在
# _ACTIVE_CODEX_STREAMS_LOCK 保护下进行，取消端点据此通知对应流。
_ACTIVE_CODEX_STREAMS: Dict[str, threading.Event] = {}
# 保护活动流注册表的互斥锁；注册、查询与注销都需持有。
_ACTIVE_CODEX_STREAMS_LOCK = threading.Lock()

class ChatRequest(BaseModel):
    """Agent 对话请求体。使用场景：同步与流式对话共用；兼容旧字段 strategies。@author: Lensgcx (GaoCangxiong)
    """
    # populate_by_name=True：允许用字段名或别名构造，兼容 strategies 旧命名。
    model_config = ConfigDict(populate_by_name=True)

    # 本轮用户输入，必填。
    message: str
    # 续接的会话 ID；为空表示新建会话。
    session_id: Optional[str] = None
    # 客户端请求 ID，用于流式取消关联，长度 1~64。
    request_id: Optional[str] = Field(default=None, min_length=1, max_length=64)
    # 本次使用的技能 ID 列表，兼容旧参数名 strategies。
    skills: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("skills", "strategies"),
    )
    # 上一次分析上下文，用于复用已取数据；行尾英文注释说明其用途。
    context: Optional[Dict[str, Any]] = None  # Previous analysis context for data reuse

    @property
    def effective_skills(self) -> Optional[List[str]]:
        """Return skill ids from the unified request shape.

        统一从 skills 读取技能 ID；strategies 只是兼容别名，不再保留第二套字段。

        Args:
            self: ChatRequest 实例。

        Returns:
            Optional[List[str]]: 技能 ID 列表；未指定为 None。
        """
        return self.skills


def _build_agent_chat_context(request: ChatRequest, config, skills: Optional[List[str]]) -> Dict[str, Any]:
    """Build the shared context contract for regular and streaming Agent Chat.

    构造普通对话与流式对话共用的上下文契约，避免两条执行路径产生不同的上下文语义。

    Args:
        request: 对话请求体。
        config: 运行时配置。
        skills: 本次生效的技能 ID 列表。

    Returns:
        Dict[str, Any]: 传给后端执行器的上下文字典。
    """
    context = dict(request.context or {})
    if skills is not None:
        context["skills"] = skills
    report_language = context.get("report_language")
    if report_language is None or (isinstance(report_language, str) and not report_language.strip()):
        context["report_language"] = config.report_language
    return context


class ChatResponse(BaseModel):
    """Agent 对话响应体。使用场景：非流式对话返回正文与会话 ID。@author: Lensgcx (GaoCangxiong)
    """
    # 对话是否成功。
    success: bool
    # Agent 回复正文；失败时为空或错误说明。
    content: str
    # 本次会话 ID，供后续续接。
    session_id: str
    # 失败原因；成功时为 None。
    error: Optional[str] = None


class SkillInfo(BaseModel):
    """单个策略技能的描述。使用场景：技能下拉列表项。@author: Lensgcx (GaoCangxiong)
    """
    # 技能稳定标识，作为请求入参。
    id: str
    # 技能展示名称。
    name: str
    # 技能用途说明。
    description: str

class SkillsResponse(BaseModel):
    """可用技能列表响应。使用场景：对话页初始化技能选择器。@author: Lensgcx (GaoCangxiong)
    """
    # 可用技能列表。
    skills: List[SkillInfo]
    # 默认选中的技能 ID；无默认时为 None。
    default_skill_id: str = ""


class StrategiesResponse(BaseModel):
    """旧版策略列表响应。使用场景：兼容仍使用 strategies 命名的旧前端。@author: Lensgcx (GaoCangxiong)
    """
    # 旧字段命名的技能列表，元素形状与 SkillInfo 一致。
    strategies: List[SkillInfo]
    # 旧字段命名的默认技能 ID。
    default_strategy_id: str = ""


class AgentModelDeployment(BaseModel):
    """Agent 模型部署信息。使用场景：模型下拉展示可用部署及其主/备角色。@author: Lensgcx (GaoCangxiong)
    """
    # 部署稳定标识，供模型选择回传。
    deployment_id: str
    # 模型标识。
    model: str
    # 底层供应商标识。
    provider: str
    # 配置来源（如系统配置、环境变量）。
    source: str
    # API 基础地址；使用供应商默认地址时为空。
    api_base: Optional[str] = None
    # 部署名称，用于展示。
    deployment_name: Optional[str] = None
    # 是否为主部署。
    is_primary: bool = False
    # 是否为回退部署。
    is_fallback: bool = False


class AgentModelsResponse(BaseModel):
    """Agent 可用模型列表响应体。使用场景：模型选择弹窗。@author: Lensgcx (GaoCangxiong)
    """
    # 已配置模型部署列表。
    models: List[AgentModelDeployment]


@router.get("/models", response_model=AgentModelsResponse)
async def get_agent_models():
    """Get configured Agent model deployments for frontend selection.

    Args:
        无参数。

    Returns:
        AgentModelsResponse: 已配置模型部署及主/备标记。
    """
    config = get_config()
    from src.application.agent.agent_backend import AgentBackendConfigError, resolve_agent_backend_id

    try:
        selected_backend = resolve_agent_backend_id(config)
    except AgentBackendConfigError:
        return AgentModelsResponse(models=[])
    if selected_backend == "codex_app_server":
        return AgentModelsResponse(models=[])
    return AgentModelsResponse(
        models=[AgentModelDeployment(**item) for item in list_agent_model_deployments(config)]
    )


@router.get("/status", response_model=AgentBackendStatusResponse)
async def get_agent_status():
    """Return the current effective Chat backend status for the Chat page.

    Args:
        无参数。

    Returns:
        AgentBackendStatusResponse: 当前后端可用性与实验状态。
    """
    payload = await asyncio.to_thread(_get_agent_chat_status, get_config())
    return _agent_status_response(payload)


def _agent_status_response(payload: Dict[str, Any]) -> AgentBackendStatusResponse:
    """构造 Agent 服务状态响应。

    Args:
        payload: 后端探测结果字典，字段可能缺失。

    Returns:
        AgentBackendStatusResponse: 补齐默认值后的状态模型。
    """
    return AgentBackendStatusResponse(
        backend=payload["backend"],
        available=payload["available"],
        experimental=payload["experimental"],
        version=payload.get("version"),
        error_code=payload.get("error_code"),
        message=payload.get("message"),
    )


def _build_skills_response(config) -> SkillsResponse:
    """构造技能列表响应。

    Args:
        config: 运行时配置，决定默认技能 ID。

    Returns:
        SkillsResponse: 可用技能与默认选中项。
    """
    from src.application.agent.factory import get_skill_manager
    from src.application.agent.skills.defaults import get_primary_default_skill_id

    skill_manager = get_skill_manager(config)
    available_skills = sorted(
        [
            skill
            for skill in skill_manager.list_skills()
            if getattr(skill, "user_invocable", True)
        ],
        key=lambda skill: (
            int(getattr(skill, "default_priority", 100)),
            skill.display_name,
            skill.name,
        ),
    )
    skills = [
        SkillInfo(id=skill.name, name=skill.display_name, description=skill.description)
        for skill in available_skills
    ]
    return SkillsResponse(
        skills=skills,
        default_skill_id=get_primary_default_skill_id(available_skills),
    )


@router.get("/skills", response_model=SkillsResponse)
async def get_skills():
    """Get available agent strategy skills.

    Args:
        无参数。

    Returns:
        SkillsResponse: 技能列表。
    """
    return _build_skills_response(get_config())


@router.get("/strategies", response_model=StrategiesResponse, include_in_schema=False)
async def get_strategies():
    """Compatibility alias for legacy clients.

    为旧前端保留 /strategies 路径，返回结构与 /skills 一致。

    Args:
        无参数。

    Returns:
        StrategiesResponse: 旧字段命名的技能列表。
    """
    payload = _build_skills_response(get_config())
    return StrategiesResponse(
        strategies=payload.skills,
        default_strategy_id=payload.default_skill_id,
    )

@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """Chat with the AI Agent without progress events.

    Codex Agent callers must use ``/chat/stream``, which provides progress
    events and request cancellation. The default LiteLLM Agent keeps this
    endpoint's existing behavior.

    同步对话：一次请求返回完整正文，不产生 SSE 进度事件；Codex 后端调用方应改用流式端点以获得进度与取消能力。

    Args:
        request: 对话请求体。

    Returns:
        ChatResponse: 对话正文、会话 ID 与错误状态。

    Raises:
        HTTPException: 后端不可用或执行失败。

    Side Effects:
        持久化会话与消息记录。
    """
    config = get_config()
    backend_id = _select_agent_chat_backend(config)
    if backend_id == "codex_app_server":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "capability_unsupported",
                "message": "Codex Agent requires the Chat interface with progress and stop support",
            },
        )
    
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        skills = request.effective_skills
        executor = _build_executor(config, skills or None)

        ctx = _build_agent_chat_context(request, config, skills)

        # Offload the blocking call to a thread to avoid blocking the event loop.
        # Agent 执行是阻塞调用，放进线程池以免卡住 ASGI 事件循环导致其他请求饥饿。
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: executor.chat(message=request.message, session_id=session_id,
                                  context=ctx),
        )

        return ChatResponse(
            success=result.success,
            content=result.content,
            session_id=session_id,
            error=result.error,
        )
            
    except Exception as e:
        logger.error(f"Agent chat API failed: {e}")
        logger.exception("Agent chat error details:")
        raise HTTPException(status_code=500, detail=str(e))


class SessionItem(BaseModel):
    """会话列表项。使用场景：历史会话侧栏，带消息数与最近活跃时间。@author: Lensgcx (GaoCangxiong)
    """
    # 会话 ID，供消息查询与删除。
    session_id: str
    # 会话标题，通常由首轮消息生成。
    title: str
    # 会话中的消息条数。
    message_count: int
    # 会话创建时间字符串。
    created_at: Optional[str] = None
    # 最近活跃时间字符串，用于列表排序。
    last_active: Optional[str] = None

class SessionsResponse(BaseModel):
    """会话列表响应体。使用场景：一次性返回当前用户的会话摘要。@author: Lensgcx (GaoCangxiong)
    """
    # 会话摘要列表。
    sessions: List[SessionItem]

class SessionMessagesResponse(BaseModel):
    """单个会话的完整消息列表。使用场景：切换会话时重建对话上下文。@author: Lensgcx (GaoCangxiong)
    """
    # 所属会话 ID。
    session_id: str
    # 消息列表，按时间升序。
    messages: List[Dict[str, Any]]


@router.get("/chat/sessions", response_model=SessionsResponse)
async def list_chat_sessions(
    limit: int = 50,
    user_id: Optional[str] = None,
    service: AgentConversationService = Depends(get_agent_conversation_service),
):
    """获取聊天会话列表

    Args:
        limit: Maximum number of sessions to return.
        user_id: Optional platform-prefixed user identifier for session
            isolation.  When provided, only sessions whose session_id
            starts with this prefix are returned.  The value must
            include the platform prefix, e.g. ``telegram_12345``,
            ``feishu_ou_abc``.
        service: 会话用例，由 Depends 装配。

    按会话隔离前缀过滤时，user_id 必须带平台前缀；不带前缀的值会被拒绝，避免跨会话串数据。

    Returns:
        SessionsResponse: 会话摘要列表。
    """
    sessions = service.list_sessions(limit=limit, user_id=user_id)
    return SessionsResponse(sessions=sessions)


@router.get("/chat/sessions/{session_id}", response_model=SessionMessagesResponse)
async def get_chat_session_messages(
    session_id: str,
    limit: int = 100,
    service: AgentConversationService = Depends(get_agent_conversation_service),
):
    """获取单个会话的完整消息。

    Args:
        session_id: 会话 ID，来自路径参数。
        limit: 返回消息条数上限。
        service: 会话用例，由 Depends 装配。

    Returns:
        SessionMessagesResponse: 按时间升序的消息列表。

    Raises:
        HTTPException: 会话不存在 404。
    """
    messages = service.get_messages(session_id, limit=limit)
    return SessionMessagesResponse(session_id=session_id, messages=messages)


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    service: AgentConversationService = Depends(get_agent_conversation_service),
):
    """删除指定会话。

    Args:
        session_id: 会话 ID，来自路径参数。
        service: 会话用例，由 Depends 装配。

    Returns:
        删除结果。

    Side Effects:
        删除会话及其消息记录。
    """
    count = service.delete_session(session_id)
    return {"deleted": count}


class SendChatRequest(BaseModel):
    """Request body for sending chat content to notification channels.

    使用场景：把对话内容转发到已配置的通知渠道。@author: Lensgcx (GaoCangxiong)
    """

    # 要转发的对话内容。
    content: str = Field(..., min_length=1, max_length=50000)
    # 通知标题；为空时使用默认标题。
    title: Optional[str] = None


@router.post("/chat/send")
async def send_chat_to_notification(request: SendChatRequest):
    """Send chat session content to configured notification channels.
    Uses run_in_executor to avoid blocking the event loop.

    把对话内容转发到通知渠道；阻塞式发送放进线程池，单渠道失败不影响其他渠道。

    Args:
        request: 转发请求体，含内容与可选标题。

    Returns:
        逐渠道投递结果。

    Raises:
        HTTPException: 未配置可用渠道时返回 400。

    Side Effects:
        触发外部通知发送。
    """
    from src.application.notification.notification import NotificationService

    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(
        None,
        lambda: NotificationService().send(request.content),
    )
    if not success:
        return {
            "success": False,
            "error": "no_channels",
            "message": "未配置通知渠道，请先在设置中配置",
        }
    return {"success": True}


def _build_executor(config, skills: Optional[List[str]] = None):
    """Build and return the backend-neutral Chat executor (sync helper).

    构造与后端实现无关的执行器，供同步与流式路径共用。

    Args:
        config: 运行时配置。
        skills: 本次生效的技能 ID 列表。

    Returns:
        Agent 执行器实例。
    """
    from src.bootstrap.agent import build_agent_chat_executor

    return build_agent_chat_executor(config, skills=skills)


def _get_agent_chat_status(config) -> Dict[str, Any]:
    """返回 Agent 对话服务当前状态。

    Args:
        config: 运行时配置。

    Returns:
        Dict[str, Any]: 后端可用性、实验标记与版本等字段。
    """
    from src.application.runtime.agent_backend_status import AgentBackendStatusService

    return AgentBackendStatusService(config=config).get_status()


def _select_agent_chat_backend(config) -> str:
    """Select the runtime backend without repeating the compatibility probe.

    复用已有状态结果选择后端，避免每次对话都重复做一次兼容性探测。

    Args:
        config: 运行时配置。

    Returns:
        str: 后端标识。
    """
    from src.application.runtime.agent_backend_status import evaluate_agent_backend_config

    evaluation = evaluate_agent_backend_config(config)
    if not evaluation["available"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": evaluation["error_code"],
                "message": evaluation["message"],
            },
        )
    return evaluation["backend"]


async def _run_research_in_background(
    agent,
    question: str,
    context: Optional[Dict[str, Any]],
    *,
    timeout: int,
):
    """Run deep research off the event loop with an internal overall timeout.

    把阻塞式研究放到线程执行，并在内部设置整体超时，避免长任务拖住 ASGI 事件循环。

    Args:
        agent: 研究 Agent 实例。
        question: 研究问题。
        context: 附加上下文。
        timeout: 整体超时秒数。

    Returns:
        研究结果字典或超时/异常结果。

    Side Effects:
        在线程池中启动执行。
    """
    return await asyncio.to_thread(
        agent.research,
        question,
        context,
        timeout_seconds=timeout,
    )


# ============================================================
# Deep research endpoint / 深度研究端点
# ============================================================

class ResearchRequest(BaseModel):
    """深度研究请求体。使用场景：发起长耗时研究任务，可附股票代码限定范围。@author: Lensgcx (GaoCangxiong)
    """
    # 研究问题，必填。
    question: str
    # 限定研究范围的股票代码；为空表示不限标的。
    stock_code: Optional[str] = None

class ResearchResponse(BaseModel):
    """深度研究响应体。使用场景：返回研究正文、来源与 token 用量；失败时 success=False 且 error 有值。@author: Lensgcx (GaoCangxiong)
    """
    # 研究是否成功完成。
    success: bool
    # 研究正文；失败时为空。
    content: str
    # 引用的来源列表。
    sources: List[str] = Field(default_factory=list)
    # 本次研究的 token 用量统计。
    token_usage: int = 0
    # 失败原因；成功时为 None。
    error: Optional[str] = None


@router.post("/research", response_model=ResearchResponse)
async def agent_research(request: ResearchRequest):
    """Run a deep-research query via the ResearchAgent.

    Similar to the ``/research`` bot command but exposed as a REST endpoint.

    与机器人 /research 命令能力一致，改为 REST 端点供 Web 调用。

    Args:
        request: 研究请求体。

    Returns:
        ResearchResponse: 研究正文、来源、token 用量与错误状态。

    Side Effects:
        触发外部模型调用与检索。
    """
    config = get_config()
    if not config.is_agent_available():
        raise HTTPException(status_code=400, detail="Agent mode is not enabled")

    question = request.question
    context: Optional[Dict[str, Any]] = None
    if request.stock_code:
        question = f"[Stock: {request.stock_code}] {question}"
        context = {"stock_code": request.stock_code}

    try:
        from src.application.agent.research import ResearchAgent
        from src.application.agent.factory import get_tool_registry
        from src.bootstrap.agent import build_agent_llm_adapter

        registry = get_tool_registry()
        llm_adapter = build_agent_llm_adapter(config)
        budget = getattr(config, "agent_deep_research_budget", 30000)

        agent = ResearchAgent(
            tool_registry=registry,
            llm_adapter=llm_adapter,
            token_budget=budget,
        )

        research_timeout = getattr(config, "agent_deep_research_timeout", 180)

        result = await _run_research_in_background(
            agent,
            question,
            context,
            timeout=research_timeout,
        )
        if getattr(result, "timed_out", False):
            logger.warning("Agent research API timed out after %ss", research_timeout)
            return ResearchResponse(
                success=False,
                content="",
                sources=[],
                token_usage=0,
                error=f"Deep research timed out after {research_timeout}s",
            )

        return ResearchResponse(
            success=result.success,
            content=result.report,
            sources=[f"Sub-question {i+1}: {q}" for i, q in enumerate(result.sub_questions)],
            token_usage=result.total_tokens,
            error=result.error if not result.success else None,
        )
    except Exception as e:
        logger.error("Agent research API failed: %s", e)
        logger.exception("Agent research error details:")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def agent_chat_stream(request: ChatRequest):
    """Chat with the AI Agent, streaming progress via SSE.
    Each SSE event is a JSON object with a 'type' field:
      - thinking: AI is deciding next action
      - stage_start: an agent or orchestrator stage has begun
      - stage_done: an agent or orchestrator stage finished
      - tool_start: a tool call has begun
      - tool_done: a tool call finished
      - generating: final answer being generated
      - pipeline_timeout: analysis stopped because the stage/pipeline budget expired
      - pipeline_budget_skipped: analysis stopped before an unstarted stage
        because the remaining budget was too low for useful work
      - done: analysis complete, contains 'content' and 'success'
      - error: error occurred, contains 'message'

    以 SSE 推送上述事件；活动流注册在 _ACTIVE_CODEX_STREAMS，取消端点据此通知正在执行的后端。pipeline_* 事件表示分析预算耗尽后的提前终止，不是执行异常。

    Args:
        request: 对话请求体。

    Returns:
        StreamingResponse: text/event-stream 响应。

    Side Effects:
        注册并在结束时注销活动流；持久化会话与消息。
    """
    config = get_config()
    backend_id = _select_agent_chat_backend(config)

    session_id = request.session_id or str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    cancel_event = threading.Event()
    request_id = request.request_id or str(uuid.uuid4())
    if backend_id == "codex_app_server":
        with _ACTIVE_CODEX_STREAMS_LOCK:
            if request_id in _ACTIVE_CODEX_STREAMS:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "request_conflict",
                        "message": "This Agent request is already running",
                    },
                )
            _ACTIVE_CODEX_STREAMS[request_id] = cancel_event

    skills = request.effective_skills
    stream_ctx = _build_agent_chat_context(request, config, skills)

    def progress_callback(event: dict):
        """构造 SSE 进度回调。

        Args:
            event: 后端产生的进度事件字典。

        Returns:
            None。

        Side Effects:
            把事件放入队列供 event_generator 读取。
        """
        if backend_id == "codex_app_server" and cancel_event.is_set():
            return
        # Enrich tool events with display names
        # 用 TOOL_DISPLAY_NAMES 给工具事件补中文名，SSE 事件本身只携带稳定工具标识。
        if event.get("type") in ("tool_start", "tool_done"):
            tool = event.get("tool", "")
            event["display_name"] = TOOL_DISPLAY_NAMES.get(tool, tool)
        asyncio.run_coroutine_threadsafe(queue.put(event), loop)

    def run_sync(executor, turn):
        """在线程池中同步执行 Agent 运行。

        Args:
            executor: Agent 执行器。
            turn: 本轮对话输入。

        Returns:
            后端执行结果。

        Side Effects:
            通过队列向 SSE 生成器发送进度事件。
        """
        try:
            execute_kwargs = {
                "progress_callback": progress_callback,
            }
            if backend_id == "codex_app_server":
                execute_kwargs["cancel_event"] = cancel_event
            result = executor.execute_turn(
                turn,
                **execute_kwargs,
            )
            event = {
                "type": "done",
                "success": result.success,
                "content": result.content,
                "error": result.error,
                "total_steps": result.total_steps,
                "session_id": session_id,
            }
            event.update({
                "backend": getattr(result, "backend", "") or backend_id,
                "error_code": getattr(result, "error_code", None),
                "request_id": request_id,
            })
            asyncio.run_coroutine_threadsafe(queue.put(event), loop)
        except Exception as exc:
            logger.error("Agent stream error: %s", exc)
            event = {
                "type": "error",
                "message": "Agent Chat failed" if backend_id == "codex_app_server" else str(exc),
                "error_code": getattr(exc, "code", "unknown_backend_error"),
                "backend": backend_id,
                "request_id": request_id,
            }
            asyncio.run_coroutine_threadsafe(queue.put(event), loop)

    async def event_generator():
        """生成 SSE 事件流。

        Args:
            无显式参数；捕获外层请求与执行上下文。

        Returns:
            Iterator[str]: 逐条 SSE 格式化事件文本。

        Side Effects:
            结束时清理活动流注册与后端进程。
        """
        fut = None
        try:
            try:
                executor = await asyncio.to_thread(_build_executor, config, skills or None)
                turn = await asyncio.to_thread(
                    executor.prepare_turn,
                    message=request.message,
                    session_id=session_id,
                    context=stream_ctx,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Agent request preparation failed: %s", exc, exc_info=True)
                event = {
                    "type": "error",
                    "message": "Agent request was not accepted",
                    "error_code": "request_not_accepted",
                    "backend": backend_id,
                    "request_id": request_id,
                }
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                return

            accepted_event = {
                "type": "accepted",
                "backend": backend_id,
                "request_id": request_id,
                "session_id": session_id,
            }
            yield "data: " + json.dumps(accepted_event, ensure_ascii=False) + "\n\n"

            # Backend execution starts only after the accepted event has been
            # yielded, so Web state and server persistence share one commit point.
            # accepted 事件推送后才启动后端执行，保证前端状态与服务端持久化发生在同一提交点。
            fut = loop.run_in_executor(None, run_sync, executor, turn)
            while True:
                try:
                    if backend_id == "codex_app_server":
                        # Codex owns one authoritative backend deadline.  A
                        # second API timeout would race it and could emit a
                        # terminal event before process cleanup finishes.
                        # 全局截止时间由 Codex 后端独自控制；API 侧再加超时会与之竞争，可能在进程清理完成前就发出终态事件。
                        event = await queue.get()
                    else:
                        event = await asyncio.wait_for(queue.get(), timeout=300.0)
                except asyncio.TimeoutError:
                    event = {"type": "error", "message": "分析超时"}
                    yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                    break
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                if event.get("type") in ("done", "error"):
                    break
        finally:
            if backend_id == "codex_app_server" and (fut is None or not fut.done()):
                cancel_event.set()
            try:
                if backend_id == "codex_app_server" and fut is not None:
                    while not fut.done():
                        try:
                            await asyncio.shield(fut)
                        except asyncio.CancelledError:
                            # Client disconnect cancellation must not abandon the
                            # owned Codex/tool worker before it actually exits.
                            # 客户端断开时不能遗弃仍在运行的 Codex/工具工作线程，必须等其真正退出。
                            cancel_event.set()
                    if not fut.cancelled():
                        fut.result()
                elif fut is not None:
                    await asyncio.wait_for(fut, timeout=5.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                # Cleanup taking longer than 5s is treated as an expected timeout; no warning.
                # 清理超过 5 秒视为可预期的超时，不输出告警，避免日志噪声。
                logger.debug("agent executor cleanup timed out after 5s for session %s", session_id)
            except Exception as exc:
                logger.warning("agent executor cleanup error (ignored): %s", exc, exc_info=True)
            finally:
                if backend_id == "codex_app_server":
                    with _ACTIVE_CODEX_STREAMS_LOCK:
                        if _ACTIVE_CODEX_STREAMS.get(request_id) is cancel_event:
                            _ACTIVE_CODEX_STREAMS.pop(request_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/stream/{request_id}/cancel")
async def cancel_agent_chat_stream(request_id: str):
    """Signal cancellation while the original Codex SSE remains open.

    保持原 SSE 连接不中断，只置位取消事件，由流式生成器在检查点收尾。

    Args:
        request_id: 待取消的请求 ID。

    Returns:
        取消受理结果。

    Side Effects:
        置位对应 threading.Event。
    """
    with _ACTIVE_CODEX_STREAMS_LOCK:
        cancel_event = _ACTIVE_CODEX_STREAMS.get(request_id)
    if cancel_event is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "request_not_active",
                "message": "This Agent request is no longer running",
            },
        )
    cancel_event.set()
    return {"accepted": True, "request_id": request_id}
