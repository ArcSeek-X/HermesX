# -*- coding: utf-8 -*-
"""AlphaSift 域装配：运行时端口绑定（litellm/EastMoney provider/HRS 取数桥）。

``alphasift_service`` 主要由 API 端点按需实例化，装配挂在 ``api_lifecycle``
（覆盖 uvicorn/main --serve/server.py 全部 API 启动链路）；CLI ``--stocks`` 主流程
不触及 AlphaSift 用例，但 ``main.py`` 与其他端口同点位进程级再装配一次，保证
脚本直调服务的路径同样可用（T5d configure_news_source 同型）。
"""

from __future__ import annotations


def configure_alphasift_runtime() -> None:
    """装配 AlphaSift 运行时端口（幂等：seam 仅非 None 覆盖，可重复调用）。"""
    from src.application.analysis.alphasift_ports import AlphaSiftRuntimePort  # noqa: F401  契约锚点
    from src.infrastructure.providers.hrs_alphasift_bridge import AlphaSiftRuntimeAdapter
    from src.application.analysis.alphasift_service import set_alphasift_runtime_port

    set_alphasift_runtime_port(AlphaSiftRuntimeAdapter())
