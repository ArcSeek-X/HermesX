"""
@file: system_config.py
@description: 系统配置端点：配置读写与导入导出、表单元数据、首次配置引导、生成后端与 Agent 后端状态、LLM 通道与通知渠道测试、运行时调度器；由 api.v1.router 挂到 /api/v1/system。
@author: Lensgcx (GaoCangxiong)

System configuration endpoints.

Covers configuration CRUD with optimistic locking, guarded .env
backup access, unsaved-draft previews, runtime backend smoke tests
and scheduler inspection.

系统配置相关端点：读取/预览 Agent 后端状态、环境变量备份访问控制等。
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.deps import get_runtime_scheduler_service, get_system_config_service
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.system_config import (
    AgentBackendStatusPreviewRequest,
    AgentBackendStatusResponse,
    DiscoverLLMChannelModelsRequest,
    DiscoverLLMChannelModelsResponse,
    ExportSystemConfigResponse,
    GenerationBackendStatusPreviewRequest,
    GenerationBackendStatusResponse,
    ImportSystemConfigRequest,
    SystemConfigConflictResponse,
    SystemConfigResponse,
    SystemConfigSchemaResponse,
    SetupStatusResponse,
    TestGenerationBackendRequest,
    TestGenerationBackendResponse,
    SystemConfigValidationErrorResponse,
    TestLLMChannelRequest,
    TestLLMChannelResponse,
    TestNotificationChannelRequest,
    TestNotificationChannelResponse,
    UpdateSystemConfigRequest,
    UpdateSystemConfigResponse,
    ValidateSystemConfigRequest,
    ValidateSystemConfigResponse,
)
from src.auth import COOKIE_NAME, is_auth_enabled, refresh_auth_state, verify_session
from src.application.runtime.system_config_service import (
    ConfigConflictError,
    ConfigImportError,
    ConfigValidationError,
    SystemConfigService,
)
from src.application.runtime.runtime_scheduler import RuntimeSchedulerService

# 模块级日志器，记录配置保存、重载与通道测试异常。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/system。
router = APIRouter()


@router.get(
    "/scheduler/status",
    summary="Get runtime scheduler status",
    description="Return status for the in-process Web/API/Desktop scheduler.",
)
def get_scheduler_status(
    scheduler: RuntimeSchedulerService = Depends(get_runtime_scheduler_service),
) -> dict:
    """Return runtime scheduler status.

    查询运行时调度器状态，只读不触发任务。

    Args:
        scheduler: 应用生命周期级调度服务，由 Depends 注入。

    Returns:
        dict: 调度器运行状态与任务概览。
    """
    return scheduler.status()


@router.post(
    "/scheduler/run-now",
    summary="Run scheduled analysis now",
    description="Trigger one scheduled analysis run in the current process.",
)
def run_scheduler_now(
    scheduler: RuntimeSchedulerService = Depends(get_runtime_scheduler_service),
) -> dict:
    """Trigger one runtime scheduled analysis run.

    立即触发一次定时分析，用于验证调度配置是否生效。

    Args:
        scheduler: 运行时调度服务，由 Depends 注入。

    Returns:
        dict: 本次触发结果。

    Side Effects:
        提交并执行一次分析任务。
    """
    result = scheduler.run_now()
    if not result.get("accepted", False):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "scheduler_busy",
                "message": "A scheduled analysis is already running",
                "reason": result.get("reason", "analysis_already_running"),
            },
        )
    return result


class EnvBackupAccessDenied(Exception):
    """环境变量备份访问被拒绝的异常，携带 HTTP 状态码与消息。

    Raised when raw `.env` backup access is not allowed for this request.

    使用场景：导出/导入 .env 前的安全门禁；非桌面端且未开启管理员认证时抛出，避免含密钥的配置文件被匿名下载。

    @author: Lensgcx (GaoCangxiong)
    """

    def __init__(self, *, status_code: int, message: str) -> None:
        """构造异常：保存 HTTP 状态码与消息。

        Args:
            status_code: 对外返回的 HTTP 状态码。
            message: 面向用户的拒绝原因。

        Returns:
            None。
        """
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _allow_env_backup_access(request: Request) -> None:
    """Gate raw .env backup/restore to explicit secure modes.

    - Desktop runtime keeps existing local behavior via HRS_DESKTOP_MODE.
    - Non-desktop runtime must have admin auth enabled and a valid session.

    桌面端沿用本机可信模式；非桌面端必须启用管理员认证且持有有效会话，否则拒绝 .env 备份的导出与恢复。

    Args:
        request: 当前请求对象，用于判断运行模式与会话凭证。

    Returns:
        None。

    Raises:
        EnvBackupAccessDenied: 不满足安全条件时抛出。
    """
    if os.getenv("HRS_DESKTOP_MODE") == "true":
        return

    refresh_auth_state()
    if not is_auth_enabled():
        raise EnvBackupAccessDenied(
            status_code=403,
            message="System config backup is disabled; enable admin authentication first",
        )

    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val and verify_session(cookie_val):
        return

    raise EnvBackupAccessDenied(
        status_code=401,
        message="System config backup requires a valid admin session",
    )


def _raise_env_backup_access_error(exc: EnvBackupAccessDenied) -> None:
    """把环境变量备份访问被拒绝的异常转换为对应状态码的 HTTPException。

    Args:
        exc: 门禁异常对象。

    Returns:
        None。

    Raises:
        HTTPException: 按 exc.status_code 抛出统一错误体。
    """
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "error": "env_backup_access_denied",
            "message": exc.message,
        },
    )


@router.get(
    "/config",
    response_model=SystemConfigResponse,
    responses={
        200: {"description": "Configuration loaded"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get system configuration",
    description=(
        "Read current configuration and return display values. Server-masked "
        "sensitive fields may return the mask token; clients should use "
        "raw_value_exists and is_masked to interpret values."
    ),
)
def get_system_config(
    include_schema: bool = Query(True, description="Whether to include schema metadata"),
    service: SystemConfigService = Depends(get_system_config_service),
) -> SystemConfigResponse:
    """Load and return current system configuration.

    读取当前配置值；敏感项以掩码返回，include_schema 控制是否附带表单元数据。

    Args:
        include_schema: 是否附带字段元数据，默认 False。
        service: 应用生命周期级系统配置服务，由 Depends 注入。

    Returns:
        SystemConfigResponse: 配置键值对、版本号与掩码占位符。
    """
    try:
        payload = service.get_config(include_schema=include_schema)
        return SystemConfigResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to load system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to load system configuration",
            },
        )


@router.get(
    "/config/setup/status",
    response_model=SetupStatusResponse,
    responses={
        200: {"description": "Setup status loaded"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get first-run setup status",
    description="Read a side-effect-free setup readiness summary from saved and runtime configuration.",
)
def get_setup_status(
    service: SystemConfigService = Depends(get_system_config_service),
) -> SetupStatusResponse:
    """Return first-run setup status without writing config or reloading runtime state.

    只读检查首次配置就绪度，不写配置也不重载运行时。

    Args:
        service: 系统配置服务，由 Depends 注入。

    Returns:
        SetupStatusResponse: 逐项检查结果与缺失必填键。
    """
    try:
        payload = service.get_setup_status()
        return SetupStatusResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to load setup status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to load setup status",
            },
        )


@router.get(
    "/config/generation-backends/status",
    response_model=GenerationBackendStatusResponse,
    responses={
        200: {"description": "Generation backend status loaded"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get generation backend status",
    description=(
        "Read a side-effect-free generation backend cheap-check status from "
        "saved and runtime configuration. This endpoint does not run a model request."
    ),
)
def get_generation_backend_status(
    service: SystemConfigService = Depends(get_system_config_service),
) -> GenerationBackendStatusResponse:
    """Return saved/runtime generation backend status without writing config.

    仅读取已保存配置对应的后端状态，不发起真实模型调用。

    Args:
        service: 系统配置服务，由 Depends 注入。

    Returns:
        GenerationBackendStatusResponse: 主/备后端与全部后端状态。
    """
    try:
        payload = service.get_generation_backend_status()
        return GenerationBackendStatusResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to load generation backend status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to load generation backend status",
            },
        )


@router.post(
    "/config/generation-backends/status/preview",
    response_model=GenerationBackendStatusResponse,
    responses={
        200: {"description": "Generation backend status preview loaded"},
        400: {"description": "Validation failed", "model": SystemConfigValidationErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Preview generation backend status",
    description="Run a side-effect-free cheap check against unsaved settings draft values.",
)
def preview_generation_backend_status(
    request: GenerationBackendStatusPreviewRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> GenerationBackendStatusResponse:
    """Return generation backend status for unsaved draft values.

    按未保存的草稿配置临时装配后端状态，不改写磁盘配置。

    Args:
        request: 草稿键值对请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        GenerationBackendStatusResponse: 草稿配置下的后端状态。
    """
    try:
        payload = service.preview_generation_backend_status(
            items=[item.model_dump() for item in request.items],
            mask_token=request.mask_token,
        )
        return GenerationBackendStatusResponse.model_validate(payload)
    except ConfigValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "message": "System configuration validation failed",
                "issues": exc.issues,
            },
        )
    except Exception as exc:
        logger.error("Failed to preview generation backend status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to preview generation backend status",
            },
        )


@router.post(
    "/config/generation-backends/smoke-test",
    response_model=TestGenerationBackendResponse,
    responses={
        200: {"description": "Generation backend smoke test completed"},
        400: {"description": "Validation failed", "model": SystemConfigValidationErrorResponse},
        422: {"description": "Invalid smoke test request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Smoke test generation backend",
    description="Run an explicit fixed-prompt generation backend smoke test without persisting config.",
)
def test_generation_backend(
    request: TestGenerationBackendRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> TestGenerationBackendResponse:
    """Run a fixed generation backend smoke test.

    发起一次真实调用冒烟测试；超时与模式由请求体控制。

    Args:
        request: 冒烟测试请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        TestGenerationBackendResponse: 测试结果与更新后的后端状态。

    Side Effects:
        触发外部模型调用，可能更新内存中的最近错误状态。
    """
    try:
        payload = service.test_generation_backend(
            backend_id=request.backend_id,
            mode=request.mode,
            items=[item.model_dump() for item in request.items],
            mask_token=request.mask_token,
            timeout_seconds=request.timeout_seconds,
        )
        return TestGenerationBackendResponse.model_validate(payload)
    except ConfigValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "message": "System configuration validation failed",
                "issues": exc.issues,
            },
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Failed to smoke test generation backend: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to smoke test generation backend",
            },
        )


@router.get(
    "/config/agent-backends/status",
    response_model=AgentBackendStatusResponse,
    summary="Get Agent Chat backend status",
    description="Read selected Agent Chat backend configuration and command capability without a model request.",
)
def get_agent_backend_status(
    service: SystemConfigService = Depends(get_system_config_service),
) -> AgentBackendStatusResponse:
    """返回当前 Agent 后端的运行状态。

    Args:
        service: 系统配置服务，由 Depends 注入。

    Returns:
        AgentBackendStatusResponse: 后端可用性、实验标记与版本。
    """
    try:
        return AgentBackendStatusResponse.model_validate(service.get_agent_backend_status())
    except Exception as exc:
        logger.error("Failed to load Agent backend status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to load Agent backend status"},
        )


@router.post(
    "/config/agent-backends/status/preview",
    response_model=AgentBackendStatusResponse,
    summary="Preview Agent Chat backend status",
    description="Run a side-effect-free cheap check against unsaved Agent settings.",
)
def preview_agent_backend_status(
    request: AgentBackendStatusPreviewRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> AgentBackendStatusResponse:
    """按请求预览 Agent 后端状态变更后的结果。

    Args:
        request: 草稿键值对请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        AgentBackendStatusResponse: 草稿配置下的兼容性状态。

    Side Effects:
        无；不写配置、不重载运行时。
    """
    try:
        return AgentBackendStatusResponse.model_validate(
            service.preview_agent_backend_status(
                items=[item.model_dump() for item in request.items],
                mask_token=request.mask_token,
            )
        )
    except Exception as exc:
        logger.error("Failed to preview Agent backend status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to preview Agent backend status"},
        )


@router.put(
    "/config",
    response_model=UpdateSystemConfigResponse,
    responses={
        200: {"description": "Configuration updated"},
        400: {"description": "Validation failed", "model": SystemConfigValidationErrorResponse},
        409: {"description": "Version conflict", "model": SystemConfigConflictResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Update system configuration",
    description="Update key-value pairs in .env. Mask token preserves existing secret values.",
)
def update_system_config(
    request: UpdateSystemConfigRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> UpdateSystemConfigResponse:
    """Validate and persist system configuration updates.

    以 config_version 做乐观锁；校验失败返回逐项问题，掩码值不写回，保存后按需重载运行时配置。

    Args:
        request: 更新请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        UpdateSystemConfigResponse: 生效项数、跳过掩码数与重载状态。

    Raises:
        HTTPException: 校验失败 400、版本冲突 409。

    Side Effects:
        写入 .env 并可能重载运行时配置。
    """
    try:
        payload = service.update(
            config_version=request.config_version,
            items=[item.model_dump() for item in request.items],
            mask_token=request.mask_token,
            reload_now=request.reload_now,
        )
        return UpdateSystemConfigResponse.model_validate(payload)
    except ConfigValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "message": "System configuration validation failed",
                "issues": exc.issues,
            },
        )
    except ConfigConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "config_version_conflict",
                "message": "Configuration has changed, please reload and retry",
                "current_config_version": exc.current_version,
            },
        )
    except Exception as exc:
        logger.error("Failed to update system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to update system configuration",
            },
        )


@router.get(
    "/config/export",
    response_model=ExportSystemConfigResponse,
    responses={
        200: {"description": "Env exported"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Env backup disabled", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Export env backup",
    description="Return the raw saved .env content for configuration backup.",
)
def export_system_config(
    request: Request,
    service: SystemConfigService = Depends(get_system_config_service),
) -> ExportSystemConfigResponse:
    """Export the active `.env` file for config backup.

    先经 _allow_env_backup_access 做安全门禁，再返回可保存的 .env 文本。

    Args:
        request: 原始请求对象，用于访问校验。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        ExportSystemConfigResponse: .env 全文与当前版本号。

    Raises:
        HTTPException: 不满足安全条件时拒绝导出。
    """
    try:
        _allow_env_backup_access(request)
    except EnvBackupAccessDenied as exc:
        logger.warning("System config export blocked: %s", exc)
        _raise_env_backup_access_error(exc)

    try:
        payload = service.export_env()
        return ExportSystemConfigResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to export system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to export system configuration",
            },
        )


@router.post(
    "/config/import",
    response_model=UpdateSystemConfigResponse,
    responses={
        200: {"description": "Env imported"},
        400: {
            "description": "Import failed",
            "content": {
                "application/json": {
                    "schema": {
                        "anyOf": [
                            {"$ref": "#/components/schemas/ErrorResponse"},
                            {"$ref": "#/components/schemas/SystemConfigValidationErrorResponse"},
                        ]
                    }
                }
            },
        },
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Env backup disabled", "model": ErrorResponse},
        409: {"description": "Version conflict", "model": SystemConfigConflictResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Import env backup",
    description="Merge raw .env text into the saved configuration with config version conflict protection.",
)
def import_system_config(
    request: ImportSystemConfigRequest,
    request_obj: Request,
    service: SystemConfigService = Depends(get_system_config_service),
) -> UpdateSystemConfigResponse:
    """Import a `.env` backup into the active config.

    同样以 config_version 做并发保护，导入后按需重载运行时配置。

    Args:
        request: 导入请求体，含 .env 全文。
        request_obj: 原始请求对象，用于访问校验。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        UpdateSystemConfigResponse: 生效项数与重载状态。

    Raises:
        HTTPException: 校验失败 400、版本冲突 409、无权限时拒绝导入。

    Side Effects:
        覆盖 .env 并可能重载运行时配置。
    """
    try:
        _allow_env_backup_access(request_obj)
    except EnvBackupAccessDenied as exc:
        logger.warning("System config import blocked: %s", exc)
        _raise_env_backup_access_error(exc)

    try:
        payload = service.import_env(
            config_version=request.config_version,
            content=request.content,
            reload_now=request.reload_now,
        )
        return UpdateSystemConfigResponse.model_validate(payload)
    except ConfigImportError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_import_file",
                "message": exc.message,
            },
        )
    except ConfigValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "message": "System configuration validation failed",
                "issues": exc.issues,
            },
        )
    except ConfigConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "config_version_conflict",
                "message": "Configuration has changed, please reload and retry",
                "current_config_version": exc.current_version,
            },
        )
    except Exception as exc:
        logger.error("Failed to import system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to import system configuration",
            },
        )


@router.post(
    "/config/validate",
    response_model=ValidateSystemConfigResponse,
    responses={
        200: {"description": "Validation completed"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Validate system configuration",
    description="Validate submitted configuration values without writing to .env.",
)
def validate_system_config(
    request: ValidateSystemConfigRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> ValidateSystemConfigResponse:
    """Run pre-save validation only.

    只做校验不写配置，供保存前逐字段高亮问题。

    Args:
        request: 校验请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        ValidateSystemConfigResponse: 是否通过及全部问题列表。
    """
    try:
        payload = service.validate(items=[item.model_dump() for item in request.items])
        return ValidateSystemConfigResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to validate system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to validate system configuration",
            },
        )


@router.post(
    "/config/llm/test-channel",
    response_model=TestLLMChannelResponse,
    responses={
        200: {"description": "Channel test completed"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Test one LLM channel",
    description="Run a minimal LLM request against one unsaved or saved channel definition.",
)
def test_llm_channel(
    request: TestLLMChannelRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> TestLLMChannelResponse:
    """Validate and test one channel definition without writing `.env`.

    使用草稿配置测试 LLM 通道连通性与能力，不写配置文件。

    Args:
        request: 通道测试请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        TestLLMChannelResponse: 总体结果、实际协议/模型与能力探测明细。

    Side Effects:
        发起外部模型调用。
    """
    try:
        payload = service.test_llm_channel(
            name=request.name,
            protocol=request.protocol,
            base_url=request.base_url,
            api_key=request.api_key,
            models=request.models,
            enabled=request.enabled,
            timeout_seconds=request.timeout_seconds,
            capability_checks=request.capability_checks,
            use_saved_secret=request.use_saved_secret,
        )
        return TestLLMChannelResponse.model_validate(payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Failed to test LLM channel: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to test LLM channel",
            },
        )


@router.post(
    "/config/notification/test-channel",
    response_model=TestNotificationChannelResponse,
    responses={
        200: {"description": "Notification channel test completed"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Test one notification channel",
    description="Send a short test notification using unsaved or saved notification configuration.",
)
def test_notification_channel(
    request: TestNotificationChannelRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> TestNotificationChannelResponse:
    """Validate and test one notification channel without writing `.env`.

    使用草稿配置发送测试消息，不写配置文件。

    Args:
        request: 通知渠道测试请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        TestNotificationChannelResponse: 逐渠道投递尝试结果。

    Side Effects:
        触发外部通知发送。
    """
    try:
        payload = service.test_notification_channel(
            channel=request.channel,
            items=[item.model_dump() for item in request.items],
            mask_token=request.mask_token,
            title=request.title,
            content=request.content,
            timeout_seconds=request.timeout_seconds,
        )
        return TestNotificationChannelResponse.model_validate(payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Failed to test notification channel: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to test notification channel",
            },
        )


@router.post(
    "/config/llm/discover-models",
    response_model=DiscoverLLMChannelModelsResponse,
    responses={
        200: {"description": "Model discovery completed"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Discover models for one LLM channel",
    description="Call one unsaved or saved channel's `/models` endpoint and return discovered model IDs.",
)
def discover_llm_channel_models(
    request: DiscoverLLMChannelModelsRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> DiscoverLLMChannelModelsResponse:
    """Discover models for one channel definition without writing `.env`.

    从草稿通道拉取可用模型列表，不写配置文件。

    Args:
        request: 模型发现请求体。
        service: 系统配置服务，由 Depends 注入。

    Returns:
        DiscoverLLMChannelModelsResponse: 模型列表与实际生效协议。

    Side Effects:
        调用上游模型列表接口。
    """
    try:
        payload = service.discover_llm_channel_models(
            name=request.name,
            protocol=request.protocol,
            base_url=request.base_url,
            api_key=request.api_key,
            models=request.models,
            timeout_seconds=request.timeout_seconds,
            use_saved_secret=request.use_saved_secret,
        )
        return DiscoverLLMChannelModelsResponse.model_validate(payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Failed to discover LLM channel models: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to discover LLM channel models",
            },
        )


@router.get(
    "/config/schema",
    response_model=SystemConfigSchemaResponse,
    responses={
        200: {"description": "Schema loaded"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get system configuration schema",
    description="Return categorized field metadata used for dynamic settings form rendering.",
)
def get_system_config_schema(
    service: SystemConfigService = Depends(get_system_config_service),
) -> SystemConfigSchemaResponse:
    """Return schema metadata for system configuration fields.

    Args:
        service: 系统配置服务，由 Depends 注入。

    Returns:
        SystemConfigSchemaResponse: 字段与分类元数据，供前端动态渲染设置表单。
    """
    try:
        payload = service.get_schema()
        return SystemConfigSchemaResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to load system configuration schema: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to load system configuration schema",
            },
        )
