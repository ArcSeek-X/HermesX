# -*- coding: utf-8 -*-
"""``api/v1/endpoints/stocks.py`` 的代码归一化归口与自选匹配键回归。

该端点曾直接 ``from data_provider.base import normalize_stock_code``，用于两处纯业务
规则：STOCK_LIST 写入前的代码标准化（``_validate_and_normalize_stock_code``）与
自选增删的等价键（``_watchlist_match_key``）。现在数据源包依赖收在
``src.application.quote.stock_code_utils.normalize_stock_code_for_stock_list``，端点不再
import ``data_provider``。本文件锁定这条契约与匹配键语义。
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from fastapi import HTTPException

from api.v1.endpoints import stocks as stocks_endpoint
from data_provider.base import normalize_stock_code
from src.application.quote.stock_code_utils import (
    normalize_stock_code_for_analysis,
    normalize_stock_code_for_stock_list,
)

# 覆盖前缀 / 后缀 / 港股 / 美股 / 日韩台 / 空串等既有归一分支。
_SAMPLES = (
    "600519",
    "SH600519",
    "sh600519",
    "SH.600519",
    "600519.SH",
    "000001.SZ",
    "920748.BJ",
    "00700",
    "hk00700",
    "1810.HK",
    "7203.T",
    "005930.KS",
    "2330.TW",
    "AAPL",
    " 600519 ",
    "",
)


def _imported_modules(path: Path) -> list:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


class StocksEndpointLayeringTestCase(unittest.TestCase):
    def test_endpoint_module_has_no_direct_provider_or_storage_import(self) -> None:
        offenders = [
            module
            for module in _imported_modules(Path(stocks_endpoint.__file__))
            if module == "data_provider"
            or module.startswith("data_provider.")
            or module == "src.storage"
            or module.startswith("src.storage.")
            or module == "src.infrastructure"
            or module.startswith("src.infrastructure.")
        ]
        self.assertEqual(offenders, [])

    def test_stock_list_wrapper_matches_data_provider_semantics(self) -> None:
        for raw in _SAMPLES:
            self.assertEqual(
                normalize_stock_code_for_stock_list(raw),
                normalize_stock_code(raw),
                raw,
            )

    def test_stock_list_wrapper_tolerates_non_string_input(self) -> None:
        self.assertEqual(
            normalize_stock_code_for_stock_list(None), normalize_stock_code("")
        )

    def test_stock_list_and_analysis_wrappers_share_semantics(self) -> None:
        """两个包装只是调用方语境不同，归一语义必须完全一致。"""
        for raw in _SAMPLES:
            self.assertEqual(
                normalize_stock_code_for_stock_list(raw),
                normalize_stock_code_for_analysis(raw),
                raw,
            )


class WatchlistStockCodeValidationTestCase(unittest.TestCase):
    def test_valid_codes_return_canonical_form(self) -> None:
        cases = {
            "600519": "600519",
            "SH600519": "600519",
            "600519.SH": "600519",
            "000001.SZ": "000001",
            "HK00700": "HK00700",
            "00700": "00700",
            "AAPL": "AAPL",
            "  600519  ": "600519",
        }
        for raw, expected in cases.items():
            self.assertEqual(
                stocks_endpoint._validate_and_normalize_stock_code(raw),
                expected,
                raw,
            )

    def test_empty_code_raises_400_with_empty_message(self) -> None:
        for raw in ("", "   "):
            with self.assertRaises(HTTPException) as ctx:
                stocks_endpoint._validate_and_normalize_stock_code(raw)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(
                ctx.exception.detail,
                {"error": "invalid_stock_code", "message": "股票代码不能为空"},
            )

    def test_bare_five_digit_code_is_accepted_as_hk(self) -> None:
        """裸 5 位数字按港股接受（与 ``_STOCK_CODE_RE`` 的 HK 分支一致）。"""
        self.assertEqual(stocks_endpoint._validate_and_normalize_stock_code("60051"), "60051")

    def test_malformed_code_raises_400_with_input_echo(self) -> None:
        # 注意：5 位数字、1-5 位字母都是合法输入（港股裸码 / 美股 ticker），不能当作非法样例。
        for raw in ("ABCDEFG", "600519.XX", "12.34", "600519,SH", "6*0519"):
            with self.assertRaises(HTTPException) as ctx:
                stocks_endpoint._validate_and_normalize_stock_code(raw)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(ctx.exception.detail["error"], "invalid_stock_code")
            self.assertIn(raw.strip(), ctx.exception.detail["message"])


class WatchlistMatchKeyTestCase(unittest.TestCase):
    def test_bare_five_digit_hk_code_gets_hk_prefix(self) -> None:
        self.assertEqual(stocks_endpoint._watchlist_match_key("00700"), "HK00700")

    def test_short_bare_code_is_not_padded(self) -> None:
        """匹配键只在「5 位裸码」时补 ``HK`` 前缀，更短的数字不做补零推断。

        这是既有行为：``700`` 与 ``00700`` 是两个不同键，不能靠前缀猜测合并。
        """
        self.assertEqual(stocks_endpoint._watchlist_match_key("700"), "700")

    def test_hk_prefix_and_suffix_forms_share_one_key(self) -> None:
        keys = {
            stocks_endpoint._watchlist_match_key(code)
            for code in ("00700", "HK00700", "hk00700", "0700.HK")
        }
        self.assertEqual(keys, {"HK00700"})

    def test_a_share_suffix_variants_share_one_key(self) -> None:
        keys = {
            stocks_endpoint._watchlist_match_key(code)
            for code in ("600519", "SH600519", "600519.SH", "sh.600519")
        }
        self.assertEqual(keys, {"600519"})

    def test_us_ticker_key_is_upper_case(self) -> None:
        self.assertEqual(stocks_endpoint._watchlist_match_key("aapl"), "AAPL")
        self.assertEqual(stocks_endpoint._watchlist_match_key(" AAPL "), "AAPL")


if __name__ == "__main__":
    unittest.main()
