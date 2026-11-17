"""MiniMaxSearchProvider transport adapter."""

from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlparse
import requests
from src.domain.search import SearchResponse, SearchResult
from src.infrastructure.search.provider_base import BaseSearchProvider, _post_with_retry

logger = logging.getLogger("src.infrastructure.search.providers")


class MiniMaxSearchProvider(BaseSearchProvider):
    """
    MiniMax Web Search (Coding Plan API)

    Features:
    - Backed by MiniMax Coding Plan subscription
    - Returns structured organic results with title/link/snippet/date
    - No native time-range parameter; time filtering is done via query
      augmentation and client-side date filtering
    - Circuit-breaker protection: 3 consecutive failures -> 300s cooldown

    API endpoint: POST https://api.minimaxi.com/v1/coding_plan/search
    """

    API_ENDPOINT = "https://api.minimaxi.com/v1/coding_plan/search"

    # Circuit-breaker settings
    _CB_FAILURE_THRESHOLD = 3
    _CB_COOLDOWN_SECONDS = 300  # 5 minutes

    def __init__(self, api_keys: List[str]):
        """构造 MiniMax 检索适配器并装配依赖。"""
        super().__init__(api_keys, "MiniMax")
        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open_until: float = 0.0

    @property
    def is_available(self) -> bool:
        """Check availability considering circuit breaker state."""
        with self._state_lock:
            if not self._api_keys:
                return False
            if self._consecutive_failures >= self._CB_FAILURE_THRESHOLD:
                if time.time() < self._circuit_open_until:
                    return False
                # Cooldown expired -> half-open, allow one probe
            return True

    def record_success(self, key: str) -> None:
        """记录一次成功调用。"""
        with self._state_lock:
            super().record_success(key)
            # Reset circuit breaker on success
            self._consecutive_failures = 0
            self._circuit_open_until = 0.0

    def record_error(self, key: str) -> None:
        """记录一次失败调用。"""
        warning_message = None
        with self._state_lock:
            super().record_error(key)
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._CB_FAILURE_THRESHOLD:
                self._circuit_open_until = time.time() + self._CB_COOLDOWN_SECONDS
                warning_message = (
                    f"[MiniMax] Circuit breaker OPEN – "
                    f"{self._consecutive_failures} consecutive failures, "
                    f"cooldown {self._CB_COOLDOWN_SECONDS}s"
                )
        if warning_message:
            logger.warning(warning_message)

    # ------------------------------------------------------------------
    # Time-range helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _time_hint(days: int, is_chinese: bool = True) -> str:
        """Build a time-hint string to append to the search query."""
        if is_chinese:
            if days <= 1:
                return "今天"
            elif days <= 3:
                return "最近三天"
            elif days <= 7:
                return "最近一周"
            else:
                return "最近一个月"
        else:
            if days <= 1:
                return "today"
            elif days <= 3:
                return "past 3 days"
            elif days <= 7:
                return "past week"
            else:
                return "past month"

    @staticmethod
    def _is_within_days(date_str: Optional[str], days: int) -> bool:
        """Check whether *date_str* falls within the last *days* days.

        Accepts common formats: ``2025-06-01``, ``2025/06/01``,
        ``Jun 1, 2025``, ISO-8601 with timezone, etc.
        Returns True when date_str is None or unparseable (keep the result).
        """
        if not date_str:
            return True
        try:
            from dateutil import parser as dateutil_parser

            dt = dateutil_parser.parse(date_str, fuzzy=True)
            from datetime import timedelta, timezone

            now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
            return (now - dt) <= timedelta(days=days + 1)  # +1 buffer
        except Exception:
            return True  # Keep result when date is unparseable

    # ------------------------------------------------------------------

    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Execute MiniMax web search."""
        try:
            # Detect language hint from query (simple heuristic)
            has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in query)
            time_hint = self._time_hint(days, is_chinese=has_cjk)
            augmented_query = f"{query} {time_hint}"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "MM-API-Source": "Minimax-MCP",
            }
            payload = {"q": augmented_query}

            response = _post_with_retry(self.API_ENDPOINT, headers=headers, json=payload, timeout=15)

            # HTTP error handling
            if response.status_code != 200:
                error_msg = self._parse_http_error(response)
                logger.warning(f"[MiniMax] Search failed: {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg,
                )

            data = response.json()

            # Check base_resp status
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                error_msg = base_resp.get("status_msg", "Unknown API error")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg,
                )

            logger.info(f"[MiniMax] Search done, query='{query}'")
            logger.debug(f"[MiniMax] Raw response keys: {list(data.keys())}")

            # Parse organic results
            results: List[SearchResult] = []
            for item in data.get("organic", []):
                date_val = item.get("date")

                # Client-side time filtering
                if not self._is_within_days(date_val, days):
                    continue

                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        snippet=(item.get("snippet", "") or "")[:500],
                        url=item.get("link", ""),
                        source=self._extract_domain(item.get("link", "")),
                        published_date=date_val,
                    )
                )

                if len(results) >= max_results:
                    break

            logger.info(f"[MiniMax] Parsed {len(results)} results (after time filter)")

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )

        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            logger.error(f"[MiniMax] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg,
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e}"
            logger.error(f"[MiniMax] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"[MiniMax] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg,
            )

    @staticmethod
    def _parse_http_error(response) -> str:
        """Parse HTTP error response from MiniMax API."""
        try:
            ct = response.headers.get("content-type", "")
            if "json" in ct:
                err = response.json()
                base_resp = err.get("base_resp", {})
                msg = base_resp.get("status_msg") or err.get("message") or str(err)
                return msg
            return response.text[:200]
        except Exception:
            return f"HTTP {response.status_code}: {response.text[:200]}"

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL as source label."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain or "未知来源"
        except Exception:
            return "未知来源"
