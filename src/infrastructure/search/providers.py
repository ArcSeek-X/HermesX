"""Public provider exports and ordered factory; implementations live in adapters/."""

from __future__ import annotations
import logging
from typing import List, Optional
from src.infrastructure.search.provider_base import BaseSearchProvider, fetch_url_content
from src.infrastructure.search.adapters.tavily import TavilySearchProvider
from src.infrastructure.search.adapters.serpapi import SerpAPISearchProvider
from src.infrastructure.search.adapters.bocha import BochaSearchProvider
from src.infrastructure.search.adapters.anspire import AnspireSearchProvider
from src.infrastructure.search.adapters.minimax import MiniMaxSearchProvider
from src.infrastructure.search.adapters.brave import BraveSearchProvider
from src.infrastructure.search.adapters.searxng import SearXNGSearchProvider
import logging
logger = logging.getLogger(__name__)


def build_search_providers(
    *,
    bocha_keys: Optional[List[str]] = None,
    tavily_keys: Optional[List[str]] = None,
    anspire_keys: Optional[List[str]] = None,
    brave_keys: Optional[List[str]] = None,
    serpapi_keys: Optional[List[str]] = None,
    minimax_keys: Optional[List[str]] = None,
    searxng_base_urls: Optional[List[str]] = None,
    searxng_public_instances_enabled: bool = True,
) -> List[BaseSearchProvider]:
    """按优先级构造已配置的搜索引擎 Provider 列表。

    SA2-3a：从 ``SearchService.__init__`` 原样抽出（逐字保留 append/insert 优先级顺序
    与日志），为后续 Provider 本体下沉 infrastructure（SA2-3b）预留装配接缝——届时本
    函数迁至 ``src/infrastructure/search/``，application 经 bootstrap 注册的 hook 调用。
    """
    providers: List[BaseSearchProvider] = []
    # 初始化搜索引擎（按优先级排序）
    # 1. Bocha 优先（中文搜索优化，AI摘要）
    if bocha_keys:
        providers.append(BochaSearchProvider(bocha_keys))
        logger.info(f"已配置 Bocha 搜索，共 {len(bocha_keys)} 个 API Key")

    # 2. Tavily（免费额度更多，每月 1000 次）
    if tavily_keys:
        providers.append(TavilySearchProvider(tavily_keys))
        logger.info(f"已配置 Tavily 搜索，共 {len(tavily_keys)} 个 API Key")

    # 3. Brave Search（隐私优先，全球覆盖）
    if brave_keys:
        providers.append(BraveSearchProvider(brave_keys))
        logger.info(f"已配置 Brave 搜索，共 {len(brave_keys)} 个 API Key")

    # 4. SerpAPI 作为备选（每月 100 次）
    if serpapi_keys:
        providers.append(SerpAPISearchProvider(serpapi_keys))
        logger.info(f"已配置 SerpAPI 搜索，共 {len(serpapi_keys)} 个 API Key")

    # 5. MiniMax（Coding Plan Web Search，结构化结果）
    if minimax_keys:
        providers.append(MiniMaxSearchProvider(minimax_keys))
        logger.info(f"已配置 MiniMax 搜索，共 {len(minimax_keys)} 个 API Key")

    # 6. SearXNG（自建实例优先；未配置时可自动发现公共实例）
    searxng_provider = SearXNGSearchProvider(
        searxng_base_urls,
        use_public_instances=bool(searxng_public_instances_enabled and not searxng_base_urls),
    )
    if searxng_provider.is_available:
        providers.append(searxng_provider)
        if searxng_base_urls:
            logger.info("已配置 SearXNG 搜索，共 %s 个自建实例", len(searxng_base_urls))
        else:
            logger.info("已启用 SearXNG 公共实例自动发现模式")

    # 7. Anspire Search（实时智能搜索优化）
    if anspire_keys:
        providers.insert(0, AnspireSearchProvider(anspire_keys))
        logger.info(f"已配置 Anspire Search 搜索，共 {len(anspire_keys)} 个 API Key")

    if not providers:
        logger.warning("未配置任何搜索能力，新闻搜索功能将不可用")

    return providers
