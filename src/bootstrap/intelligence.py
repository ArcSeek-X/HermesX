# -*- coding: utf-8 -*-
"""资讯域装配：Wallstreetcn 快讯/日历源端口绑定。

``IntelligenceService`` 仅由 API 端点按需实例化，装配挂在
``api_lifecycle``（覆盖 uvicorn/main --serve/server.py 全部 API 启动链路）；
CLI/bot 入口不触及资讯服务，无需额外挂点。
"""

from __future__ import annotations


def configure_news_source() -> None:
    """装配资讯源端口（幂等：seam 仅非 None 覆盖，可重复调用）。"""
    from src.application.intelligence.intelligence_service import set_news_source_port
    from src.infrastructure.providers.wallstreetcn_news_port import WallstreetcnNewsPort

    set_news_source_port(WallstreetcnNewsPort())


def configure_intelligence_repository() -> None:
    """装配资讯仓储端口工厂（幂等：可重复调用只会重新指向同一工厂）。

    将 infrastructure 的 ``IntelligenceRepository`` 类作为零参工厂注册到
    application ``IntelligenceService`` 的仓储 seam，使用例层无需直接 import
    具体仓储即可进行资讯读写（PP-1 持久化收口）。注：此处传类而非实例，因为
    ``IntelligenceRepository`` 构造时捕获当前 ``DatabaseManager`` 单例，而运行/测试期
    会 ``reset_instance()`` 重建管理器；工厂使每个服务实例都绑定到构造当下的管理器（
    与 backtest/history 的 ``build_*`` 工厂同一考量）。未装配时服务构造即 fail-fast。
    """
    from src.application.intelligence.intelligence_service import (
        set_intelligence_repository_factory,
    )
    from src.infrastructure.persistence.repositories.intelligence_repository import (
        IntelligenceRepository,
    )

    set_intelligence_repository_factory(IntelligenceRepository)


def configure_search() -> None:
    """装配搜索 Provider 构造 hook（幂等：重复调用只会重新指向同一工厂）。

    将 infrastructure 的 :func:`src.infrastructure.search.build_search_providers`
    注册到 application ``SearchService`` 的 provider-builder hook，使用例层无需直接
    import 具体 Provider 即可按 key 构造搜索器列表（SA2-3b 分层归位）。未装配时
    SearchService 优雅降级为空 provider 列表。
    """
    from src.application.intelligence.search_service import set_search_provider_builder
    from src.infrastructure.search import build_search_providers

    set_search_provider_builder(build_search_providers)
