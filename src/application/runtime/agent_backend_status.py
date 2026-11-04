# -*- coding: utf-8 -*-
"""Side-effect-free compatibility status for Agent Chat backends.

对 Agent Chat 后端的无副作用兼容性状态探测。复用 Codex App Server 传输层，
在请求期评估所选后端是否可被尝试：解析候选后端、校验请求期配置不变量（agent_mode/arch/timeout），
并对 Codex 做轻量能力探测（平台、命令、协议 schema、版本），最终产出
{backend, available, version, error_code, message} 状态。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional

from src.application.agent.agent_backend import resolve_agent_backend_id
from src.application.runtime.codex_contract import (
    CodexAppServerError,
    controlled_environment,
    is_native_windows,
    resolve_command,
)
from src.config import Config, parse_env_bool, parse_env_int
from src.application.runtime.generation_backend_status import GenerationBackendStatusService


_PROBE_TERM_GRACE_SECONDS = 0.5
_PROBE_KILL_GRACE_SECONDS = 2.0


def _probe_process_group_alive(process_group_id: int) -> bool:
    """通过 killpg(pid, 0) 探测进程组是否仍存活：ProcessLookupError 表示已退出返回 False，PermissionError 表示存在返回 True，其余返回 True。"""
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_probe_process_group(process: subprocess.Popen) -> None:
    """Synchronously reclaim the CLI launcher and its native Codex child."""
    process_group_id = process.pid
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError:
        if process.poll() is None:
            process.terminate()

    term_deadline = time.monotonic() + _PROBE_TERM_GRACE_SECONDS
    if process.poll() is None:
        try:
            process.wait(timeout=max(0.0, term_deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    while _probe_process_group_alive(process_group_id) and time.monotonic() < term_deadline:
        time.sleep(0.02)

    if process.poll() is None or _probe_process_group_alive(process_group_id):
        try:
            os.killpg(process_group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            if process.poll() is None:
                process.kill()
        kill_deadline = time.monotonic() + _PROBE_KILL_GRACE_SECONDS
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.0, kill_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
        while _probe_process_group_alive(process_group_id) and time.monotonic() < kill_deadline:
            time.sleep(0.02)

    if process.poll() is None or _probe_process_group_alive(process_group_id):
        raise CodexAppServerError(
            "resource_cleanup_failed",
            "Codex compatibility-check process group could not be reclaimed",
        )


def _run_codex_probe(
    command: list[str],
    *,
    timeout: float,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """Run one bounded CLI probe without orphaning the native Codex child."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        text=capture_output,
        env=controlled_environment(),
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            _terminate_probe_process_group(process)
        finally:
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        raise
    if _probe_process_group_alive(process.pid):
        _terminate_probe_process_group(process)
    return subprocess.CompletedProcess(
        command,
        process.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _schema_contains_literal(value: Any, literal: str) -> bool:
    """递归判断 JSON schema 值中是否包含给定字面量字符串：dict 递归其 values，list 递归其 items，标量直接相等比较。"""
    if isinstance(value, dict):
        return literal in value or any(
            _schema_contains_literal(item, literal) for item in value.values()
        )
    if isinstance(value, list):
        return any(_schema_contains_literal(item, literal) for item in value)
    return value == literal


def _codex_protocol_schema_is_capable(schema_dir: Path) -> bool:
    """校验 Codex 协议 schema 是否满足能力要求：逐一对规定路径的 JSON 文件检查是否包含所需字面量（动态工具、权限档、各项请求/通知等），任一缺失或读取失败返回 False。"""
    requirements = {
        Path("v2", "ThreadStartParams.json"): {"dynamicTools", "runtimeWorkspaceRoots"},
        Path("v2", "ThreadStartResponse.json"): {
            "activePermissionProfile",
            "runtimeWorkspaceRoots",
        },
        Path("ClientRequest.json"): {
            "thread/inject_items",
            "turn/start",
            "turn/interrupt",
            "config/read",
            "mcpServerStatus/list",
        },
        Path("ServerRequest.json"): {"item/tool/call"},
        Path("ServerNotification.json"): {"item/completed", "turn/completed"},
    }
    for relative_path, literals in requirements.items():
        path = schema_dir / relative_path
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not all(_schema_contains_literal(payload, literal) for literal in literals):
            return False
    return True


def evaluate_agent_backend_config(config: Config) -> Dict[str, Any]:
    """Select the backend and evaluate only request-time configuration invariants."""
    requested = str(getattr(config, "agent_backend", "auto") or "auto").strip().lower()
    try:
        selected = resolve_agent_backend_id(config)
    except ValueError as exc:
        return {
            "backend": requested or "unknown",
            "available": False,
            "error_code": getattr(exc, "code", "capability_unsupported"),
            "message": str(exc),
        }

    if getattr(config, "agent_mode_explicit", False) and not getattr(config, "agent_mode", False):
        return {
            "backend": selected,
            "available": False,
            "error_code": "agent_mode_disabled",
            "message": "Agent mode is disabled",
        }
    if selected == "codex_app_server" and getattr(config, "agent_arch", "single") != "single":
        return {
            "backend": selected,
            "available": False,
            "error_code": "unsupported_agent_arch",
            "message": "Codex Agent currently supports single-agent Chat only",
        }
    if (
        selected == "codex_app_server"
        and int(getattr(config, "agent_orchestrator_timeout_s", 0) or 0) <= 0
    ):
        return {
            "backend": selected,
            "available": False,
            "error_code": "invalid_timeout",
            "message": "Codex Agent requires AGENT_ORCHESTRATOR_TIMEOUT_S greater than 0",
        }
    if selected == "litellm" and not config.is_agent_available():
        return {
            "backend": selected,
            "available": False,
            "error_code": "capability_unsupported",
            "message": "no_agent_primary",
        }
    return {
        "backend": selected,
        "available": True,
        "error_code": None,
        "message": None,
    }


class AgentBackendStatusService:
    """Evaluate whether the selected Chat backend can be attempted."""

    def __init__(self, *, effective_map: Optional[Dict[str, str]] = None, config: Optional[Config] = None) -> None:
        """装配状态服务：保存大写键的 effective_map（参数/环境变量快照）与可选的预置 Config。"""
        self._effective_map = {
            str(key).upper(): "" if value is None else str(value)
            for key, value in (effective_map or {}).items()
        }
        self._config = config

    def get_status(self) -> Dict[str, Any]:
        """返回所选 Chat 后端的兼容性状态：先评估请求期配置不变量，不可用直接响应；litellm 直接可用；codex_app_server 走轻量能力探测。"""
        config = self._build_config()
        evaluation = evaluate_agent_backend_config(config)
        if not evaluation["available"]:
            return self._response(
                backend=evaluation["backend"],
                available=False,
                error_code=evaluation["error_code"],
                message=evaluation["message"],
            )
        if evaluation["backend"] == "litellm":
            return self._response(backend="litellm", available=True)
        return self._codex_cheap_status()

    def _codex_cheap_status(self) -> Dict[str, Any]:
        """对 Codex App Server 做轻量能力探测：原生 Windows 不支持；解析命令、生成协议 schema 校验、读取版本，任一失败返回对应 error_code 的不可用响应。"""
        if is_native_windows():
            return self._response(
                backend="codex_app_server",
                available=False,
                error_code="platform_unsupported",
                message="Codex App Server Agent is not supported on native Windows in this phase",
            )
        try:
            command = resolve_command()
        except CodexAppServerError as exc:
            return self._response(
                backend="codex_app_server",
                available=False,
                error_code=getattr(exc, "code", "command_not_found"),
                message="Codex was not found on the HRS process PATH",
            )
        try:
            with tempfile.TemporaryDirectory(prefix="hrs-codex-protocol-") as schema_dir:
                schema_result = _run_codex_probe(
                    [
                        command[0],
                        "app-server",
                        "generate-json-schema",
                        "--experimental",
                        "--out",
                        schema_dir,
                    ],
                    timeout=5,
                )
                protocol_capable = (
                    schema_result.returncode == 0
                    and _codex_protocol_schema_is_capable(Path(schema_dir))
                )
        except CodexAppServerError as exc:
            return self._response(
                backend="codex_app_server",
                available=False,
                error_code=exc.code,
                message="Codex compatibility check could not reclaim its background process",
            )
        except (OSError, subprocess.SubprocessError):
            return self._response(
                backend="codex_app_server",
                available=False,
                error_code="capability_unsupported",
                message="Codex App Server capability check failed",
            )
        if not protocol_capable:
            return self._response(
                backend="codex_app_server",
                available=False,
                error_code="capability_unsupported",
                message="This Codex installation does not expose the required dynamic-tool protocol",
            )
        version = None
        try:
            version_result = _run_codex_probe(
                [command[0], "--version"],
                timeout=5,
                capture_output=True,
            )
            if version_result.returncode == 0:
                version = version_result.stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            pass
        return self._response(
            backend="codex_app_server",
            available=True,
            version=version,
        )

    def _response(
        self,
        *,
        backend: str,
        available: bool,
        error_code: Optional[str] = None,
        message: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构造统一的状态响应字典：含 backend/available/experimental(仅 codex 为真)/version/error_code/message。"""
        return {
            "backend": backend,
            "available": available,
            "experimental": backend == "codex_app_server",
            "version": version,
            "error_code": error_code,
            "message": message,
        }

    def _build_config(self) -> Config:
        """构造用于评估的 Config：优先复用预置 config，否则由 GenerationBackendStatusService 生成并填入 effective_map 中的 AGENT_* 环境变量（backend/arch/mode/timeout 等）。"""
        if self._config is not None:
            return self._config
        generation_service = GenerationBackendStatusService(effective_map=self._effective_map)
        config = generation_service.build_effective_config()
        config.agent_backend = (self._effective_map.get("AGENT_BACKEND") or "auto").strip().lower()
        config.agent_generation_backend = (
            self._effective_map.get("AGENT_GENERATION_BACKEND") or "auto"
        ).strip().lower()
        config.agent_litellm_model = (self._effective_map.get("AGENT_LITELLM_MODEL") or "").strip()
        config.agent_arch = (self._effective_map.get("AGENT_ARCH") or "single").strip().lower()
        config.agent_mode = parse_env_bool(self._effective_map.get("AGENT_MODE"), default=False)
        config.agent_mode_explicit = "AGENT_MODE" in self._effective_map
        config.agent_orchestrator_timeout_s = parse_env_int(
            self._effective_map.get("AGENT_ORCHESTRATOR_TIMEOUT_S"),
            600,
            field_name="AGENT_ORCHESTRATOR_TIMEOUT_S",
            minimum=0,
        )
        return config
