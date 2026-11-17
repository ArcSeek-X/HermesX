# -*- coding: utf-8 -*-
"""SystemConfig 域装配：运行时外部调用端口绑定（探测/通知试发/单例重置）。

``system_config_service`` 主要由 API 端点经 ``api/deps``/``app.state`` 使用，装配挂在
``api_lifecycle``（覆盖 uvicorn/main --serve/server.py 全部 API 启动链路）；CLI 与其他
端口同点位进程级再装配一次，保证脚本直调服务的路径同样可用
（T5e configure_alphasift_runtime 同型）。
"""

from __future__ import annotations


def configure_system_config_runtime() -> None:
    """装配 SystemConfig 运行时端口（幂等：seam 仅非 None 覆盖，可重复调用）。"""
    from src.application.runtime.system_config_ports import (  # noqa: F401  契约锚点
        ConfigProbePort,
        NotificationDispatchPort,
        RuntimeResetPort,
    )
    from src.infrastructure.providers.system_config_runtime import (
        NotificationDispatchAdapter,
        RuntimeResetAdapter,
        SystemConfigProbeAdapter,
    )
    from src.application.runtime.system_config_service import (
        set_config_probe_port,
        set_notification_dispatch_port,
        set_runtime_reset_port,
    )

    set_config_probe_port(SystemConfigProbeAdapter())
    set_notification_dispatch_port(NotificationDispatchAdapter())
    set_runtime_reset_port(RuntimeResetAdapter())
