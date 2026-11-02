# -*- coding: utf-8 -*-
"""
===================================
Search Algorithm Performance Tests
===================================

Benchmarks the name-to-code resolution engine under load.
测试搜索性能相关功能测试
"""

import time
import pytest

from src.application.quote import name_to_code_resolver
from src.application.quote.name_to_code_resolver import resolve_name_to_code


class _FakeCodeSearchPort:
    """最小 ``QuoteProviderPort`` 实现，用于替换 code-search 在线 fallback。

    历史版本直接 patch 已下线的 ``_get_akshare_name_to_code``；解析引擎现改走
    ``QuoteProviderPort.search_codes`` 端口，这里用最薄桩还原「远端候选固定」语义。
    """

    def __init__(self, name_to_code: dict[str, str] | None = None) -> None:
        self._name_to_code = name_to_code or {}
        self.calls: list[tuple[str, int]] = []

    def search_codes(self, *, keyword: str, limit: int) -> list[dict]:
        self.calls.append((keyword, limit))
        return [
            {"code": code, "name": name}
            for name, code in self._name_to_code.items()
        ]


class TestSearchPerformance:
    """Benchmark tests for stock search resolution."""

    @pytest.mark.benchmark
    def test_resolve_name_to_code_fast_path_throughput(self):
        """Benchmark the common fast paths without typo/fuzzy fallbacks dominating runtime."""
        inputs = [
            "600519", "00700", "AAPL", "TSLA",
            "贵州茅台", "腾讯控股", "阿里巴巴",
            "aaaaaaa", "1234567",
        ]

        # Warm caches/import paths before timing.
        for s in inputs:
            resolve_name_to_code(s)

        start_time = time.time()
        iterations = 30
        for _ in range(iterations):
            for s in inputs:
                resolve_name_to_code(s)

        duration = time.time() - start_time
        avg_ms = (duration / (iterations * len(inputs))) * 1000

        print(f"\nAverage fast-path resolution time: {avg_ms:.2f}ms")
        assert avg_ms < 20, f"Fast-path resolution too slow: {avg_ms:.2f}ms"

    @pytest.mark.benchmark
    def test_resolve_name_to_code_typo_fallback_budget(self, monkeypatch):
        """Benchmark typo/fuzzy fallback separately with a smaller iteration budget."""
        # 远端候选为空，确保计时只覆盖本地映射 + 单字误写兜底。
        monkeypatch.setattr(
            name_to_code_resolver, "_code_search_port", _FakeCodeSearchPort()
        )
        typo_inputs = [
            "贵州茅苔",
            "平安银形",
        ]

        for s in typo_inputs:
            resolve_name_to_code(s)

        start_time = time.time()
        iterations = 10
        for _ in range(iterations):
            for s in typo_inputs:
                resolve_name_to_code(s)

        duration = time.time() - start_time
        avg_ms = (duration / (iterations * len(typo_inputs))) * 1000

        print(f"\nAverage typo/fallback resolution time: {avg_ms:.2f}ms")
        assert avg_ms < 100, f"Typo fallback too slow: {avg_ms:.2f}ms"

    @pytest.mark.benchmark
    def test_fuzzy_match_performance_large_set(self, monkeypatch):
        """Test difflib fuzzy matching performance with a 5000+ stock set."""
        # Simulate 5000 remote candidates returned by the code-search port.
        fake_market = {f"股票_{i}": f"{i:06d}" for i in range(5000)}
        monkeypatch.setattr(
            name_to_code_resolver, "_code_search_port", _FakeCodeSearchPort(fake_market)
        )

        query = "股票_4999"  # Worst case or near worst case for fuzzy matching

        start_time = time.time()
        iterations = 20
        for _ in range(iterations):
            resolve_name_to_code(query)

        duration = time.time() - start_time
        avg_ms = (duration / iterations) * 1000

        print(f"\nFuzzy match (5000 stocks) avg time: {avg_ms:.2f}ms")
        # Fuzzy matching 5000 strings is CPU intensive.
        # Aiming for < 100ms per request on a standard CI environment.
        assert avg_ms < 200, f"Fuzzy matching too slow: {avg_ms:.2f}ms"
