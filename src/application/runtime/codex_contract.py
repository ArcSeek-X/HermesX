# -*- coding: utf-8 -*-
"""Codex App Server 用例侧共享契约。

本模块承载 ``CodexAppServerTransport``（基础设施）与 ``agent_backend_status``
（应用层健康探测）共同依赖的「命令 / 环境 / 错误」契约，作为单一真源：

- ``CodexAppServerError``：结构化的 App Server 传输失败异常。基础设施抛出、
  应用层捕获，必须是同一个类对象，因此真源不能留在 ``src.infrastructure``
  （应用层禁入基础设施）。
- ``is_native_windows`` / ``controlled_environment`` / ``resolve_command``：
  探测与拉起 Codex 子进程前的纯函数式准备（OS 判定、环境变量白名单过滤、
  argv 组装），应用层探针与基础设施传输层复用同一份实现。

``src.infrastructure.agent_runtime.codex_app_server_transport`` 从此处导入这些
符号（基础设施→应用层合法），并保持自身命名空间再导出，兼容既有
``from ...codex_app_server_transport import CodexAppServerError`` 等引用。
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional

# Codex App Server 拉起时使用的最小权限配置覆盖（只读工作区、禁用网络/apps/plugins）。
_BASE_CONFIG_OVERRIDES = (
    'default_permissions="hrs_gate_a"',
    'permissions.hrs_gate_a.description="HRS Agent read-only workspace"',
    'permissions.hrs_gate_a.filesystem={":minimal"="read",":workspace_roots"={"."="read"}}',
    "permissions.hrs_gate_a.network.enabled=false",
    "features.apps=false",
    "features.plugins=false",
)

# Codex 进程可继承的环境变量白名单，避免把无关密钥 / 会话状态透传给子进程。
_ALLOWED_ENV_NAMES = {
    "CODEX_HOME",
    "HOME",
    "LANG",
    "LC_ALL",
    "LOGNAME",
    "PATH",
    "SHELL",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "TMPDIR",
    "USER",
}


class CodexAppServerError(RuntimeError):
    """Structured App Server transport failure."""

    def __init__(self, code: str, message: str, *, turn_started: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.turn_started = turn_started


def is_native_windows() -> bool:
    """Return whether the current process is running on native Windows."""
    return os.name == "nt"


def controlled_environment(source: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Return the allowlisted environment inherited by Codex."""
    environment = os.environ if source is None else source
    return {name: environment[name] for name in _ALLOWED_ENV_NAMES if environment.get(name)}


def resolve_command(executable: str = "codex") -> List[str]:
    """Resolve the fixed App Server argv and least-privilege overrides."""
    if is_native_windows():
        raise CodexAppServerError(
            "capability_unsupported",
            "Codex App Server Agent is not supported on native Windows in this phase",
        )
    resolved = shutil.which(executable)
    if resolved is None:
        raise CodexAppServerError("command_not_found", "Codex executable was not found")
    command = [resolved, "app-server", "--stdio"]
    for override in _BASE_CONFIG_OVERRIDES:
        command.extend(["-c", override])
    return command
