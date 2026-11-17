# -*- coding: utf-8 -*-
# 本文件主要测试：测试自动补全 PR0 的 AnalyzeRequest 请求契约扩展
"""
===================================
Autocomplete PR0 - AnalyzeRequest Contract Tests
===================================

Test the ``api.v1.schemas.analysis.AnalyzeRequest`` model extension:
- accepts new autocomplete fields
- backward compatibility when new fields are omitted
- skills / legacy strategies alias
- selection_source validation
- batch stock_codes support
"""

from api.v1.schemas.analysis import AnalyzeRequest


class TestAnalyzeRequest:
    """Test AnalyzeRequest model"""

    def test_analyze_request_with_new_fields(self):
        """Test that AnalyzeRequest accepts new fields"""
        request = AnalyzeRequest(
            stock_code="600519",
            async_mode=True,
            stock_name="贵州茅台",
            original_query="茅台",
            selection_source="autocomplete",
        )
        assert request.stock_code == "600519"
        assert request.stock_name == "贵州茅台"
        assert request.original_query == "茅台"
        assert request.selection_source == "autocomplete"

    def test_analyze_request_backward_compatible(self):
        """Test backward compatibility: works fine without new fields"""
        request = AnalyzeRequest(
            stock_code="600519",
            async_mode=True,
        )
        assert request.stock_code == "600519"
        assert request.stock_name is None
        assert request.original_query is None
        assert request.selection_source is None

    def test_analyze_request_accepts_strategy_skills_alias(self):
        """Test analysis requests accept both skills and legacy strategies."""
        request = AnalyzeRequest(
            stock_code="600519",
            skills=["growth_quality"],
        )
        assert request.skills == ["growth_quality"]

        legacy_request = AnalyzeRequest(
            stock_code="600519",
            strategies=["event_driven"],
        )
        assert legacy_request.skills == ["event_driven"]

    def test_analyze_request_validation_selection_source(self):
        """Test selection_source field validation"""
        # Valid selection_source values
        for source in ["manual", "autocomplete", "import", "image"]:
            request = AnalyzeRequest(
                stock_code="600519",
                selection_source=source,
            )
            assert request.selection_source == source

    def test_analyze_request_with_multiple_stocks(self):
        """Test support for new fields in batch analysis"""
        request = AnalyzeRequest(
            stock_codes=["600519", "000001"],
            async_mode=True,
            stock_name="批量股票",
            original_query="600519,000001",
            selection_source="import",
        )
        assert request.stock_codes == ["600519", "000001"]
        assert request.stock_name == "批量股票"
        assert request.original_query == "600519,000001"
        assert request.selection_source == "import"
