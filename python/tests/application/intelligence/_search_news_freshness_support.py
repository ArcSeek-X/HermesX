# -*- coding: utf-8 -*-
"""
Unit tests for strict news freshness filtering and strategy window logic (Issue #697).
测试搜索新闻时效性相关功能测试
"""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Mock newspaper before search_service import (optional dependency)
if "newspaper" not in sys.modules:
    mock_np = MagicMock()
    mock_np.Article = MagicMock()
    mock_np.Config = MagicMock()
    sys.modules["newspaper"] = mock_np

from src.application.intelligence.search_service import SearchResponse, SearchResult, SearchService
from src.bootstrap.intelligence import configure_search

# SA2-3b：Provider 已下沉 infrastructure，测试顶层显式装配 hook（沿用 analyzer 先例）。
configure_search()
from src.application.runtime.run_diagnostics import (
    activate_run_diagnostic_context,
    current_diagnostic_snapshot,
    reset_run_diagnostic_context,
)


def _result(
    title: str,
    published_date: str | None,
    *,
    snippet: str = "snippet",
    url: str | None = None,
    source: str = "example.com",
) -> SearchResult:
    return SearchResult(
        title=title,
        snippet=snippet,
        url=url or f"https://example.com/{title}",
        source=source,
        published_date=published_date,
    )


def _response(results) -> SearchResponse:
    return SearchResponse(
        query="test",
        results=results,
        provider="Mock",
        success=True,
    )


class _SearchNewsFreshnessTestCaseFixture:
    """Tests for strategy window and strict published_date filtering."""
    def _create_service_with_mock_provider(
        self,
        *,
        news_max_age_days: int = 3,
        news_strategy_profile: str = "short",
        response: SearchResponse | None = None,
    ):
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=news_max_age_days,
            news_strategy_profile=news_strategy_profile,
        )
        mock_search = MagicMock(
            return_value=response
            or _response([_result("default", datetime.now().date().isoformat())])
        )
        service._providers[0].search = mock_search
        return service, mock_search

