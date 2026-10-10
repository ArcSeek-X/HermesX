# -*- coding: utf-8 -*-
"""
@file: normalize.py
@description: data_provider 公共标准化工具，统一股票代码、市场标签与上游 symbol 转换。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from data_provider.base import canonical_stock_code, normalize_stock_code


def _bare_stock_code(stock_code: str) -> str:
    """剥离交易所前后缀（如 000422.SZ -> 000422、sh600519 -> 600519），得到裸代码。"""
    return normalize_stock_code((stock_code or "").strip())


def code_to_sina_symbol(stock_code: str) -> str:
    """将股票代码转换为新浪 / 腾讯常用 symbol。"""
    code = _bare_stock_code(stock_code)
    if code.startswith("6"):
        return f"sh{code}"
    if code.startswith(("0", "3")):
        return f"sz{code}"
    if code.startswith(("8", "4")):
        return f"bj{code}"
    return f"sz{code}"


def code_to_secid(stock_code: str) -> str:
    """将股票代码转换为东方财富 secid。"""
    code = _bare_stock_code(stock_code)
    if code.startswith("6"):
        return f"1.{code}"
    if code.startswith(("0", "3", "4", "8")):
        return f"0.{code}"
    return f"0.{code}"


def stock_market_label(stock_code: str) -> str:
    """返回前端友好的 A 股市场标签。"""
    code = _bare_stock_code(stock_code)
    if code.startswith("6"):
        return "sh"
    if code.startswith(("0", "3")):
        return "sz"
    if code.startswith(("4", "8")):
        return "bj"
    return "sz"

__all__ = [
    "canonical_stock_code",
    "normalize_stock_code",
    "code_to_secid",
    "code_to_sina_symbol",
    "stock_market_label",
]
