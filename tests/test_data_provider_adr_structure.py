# -*- coding: utf-8 -*-
"""校验 data_provider 目录与 ADR-001 的关键结构对齐。"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_data_provider_packages_match_adr_structure() -> None:
    """ADR-001 中约定的关键能力包与三级文件应全部存在。"""
    expected_files = [
        "data_provider/common/__init__.py",
        "data_provider/common/base.py",
        "data_provider/common/normalize.py",
        "data_provider/common/cache.py",
        "data_provider/common/rate_limit.py",
        "data_provider/common/health.py",
        "data_provider/stocksdk_bridge.py",
        "data_provider/kline/__init__.py",
        "data_provider/kline/base.py",
        "data_provider/kline/local_stockdb_source.py",
        "data_provider/kline/eastmoney_source.py",
        "data_provider/kline/sina_source.py",
        "data_provider/kline/tencent_source.py",
        "data_provider/kline/stocksdk_source.py",
        "data_provider/kline/transform.py",
        "data_provider/realtime/__init__.py",
        "data_provider/realtime/base.py",
        "data_provider/realtime/akshare_source.py",
        "data_provider/realtime/tickflow_source.py",
        "data_provider/stock_info/__init__.py",
        "data_provider/stock_info/base.py",
        "data_provider/stock_info/local_stockdb_source.py",
        "data_provider/stock_info/eastmoney_source.py",
        "data_provider/stock_info/stocksdk_source.py",
        "data_provider/code_search/__init__.py",
        "data_provider/code_search/base.py",
        "data_provider/code_search/local_stockdb_source.py",
        "data_provider/code_search/eastmoney_source.py",
        "data_provider/code_search/stocksdk_source.py",
        "data_provider/sector/__init__.py",
        "data_provider/sector/base.py",
        "data_provider/sector/eastmoney_source.py",
        "data_provider/sector/market_cards_source.py",
        "data_provider/sector/shidaotec_source.py",
        "data_provider/sector/stocksdk_source.py",
        "data_provider/fundamentals/__init__.py",
        "data_provider/fundamentals/base.py",
        "data_provider/fundamentals/tushare_source.py",
        "data_provider/news/__init__.py",
        "data_provider/news/base.py",
        "data_provider/news/wallstreetcn_source.py",
        "data_provider/institutional/__init__.py",
        "data_provider/institutional/base.py",
        "data_provider/institutional/tw_source.py",
    ]

    missing = [path for path in expected_files if not (ROOT / path).exists()]
    assert not missing, f"ADR structure files missing: {missing}"

    forbidden_files = [
        "data_provider/kline/service.py",
        "data_provider/stock_info/service.py",
        "data_provider/code_search/service.py",
    ]
    unexpected = [path for path in forbidden_files if (ROOT / path).exists()]
    assert not unexpected, f"ADR structure should not keep transition files: {unexpected}"


def test_data_provider_adr_modules_are_syntax_valid() -> None:
    """新增 ADR 能力包至少要保持语法可编译。"""
    module_files = [
        "data_provider/realtime/base.py",
        "data_provider/realtime/akshare_source.py",
        "data_provider/realtime/tickflow_source.py",
        "data_provider/stocksdk_bridge.py",
        "data_provider/kline/stocksdk_source.py",
        "data_provider/stock_info/stocksdk_source.py",
        "data_provider/code_search/stocksdk_source.py",
        "data_provider/sector/base.py",
        "data_provider/sector/eastmoney_source.py",
        "data_provider/sector/market_cards_source.py",
        "data_provider/sector/shidaotec_source.py",
        "data_provider/sector/stocksdk_source.py",
        "data_provider/fundamentals/base.py",
        "data_provider/fundamentals/tushare_source.py",
        "data_provider/news/base.py",
        "data_provider/news/wallstreetcn_source.py",
        "data_provider/institutional/base.py",
        "data_provider/institutional/tw_source.py",
    ]

    for file_path in module_files:
        source = (ROOT / file_path).read_text(encoding="utf-8")
        compile(source, file_path, "exec")
