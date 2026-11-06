# -*- coding: utf-8 -*-
"""
@file: normalize.py
@description: data_provider 公共标准化工具，统一股票代码、市场标签与上游 symbol 转换。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Any, Optional

from src.domain.market.stock_codes import canonical_stock_code, normalize_stock_code


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


def try_scalar_isna(value: Any, context: str, *, logger) -> Optional[bool]:
    import numpy as np
    import pandas as pd
    """Return scalar ``pd.isna`` result, or ``None`` when callers should use fallback logic."""
    if isinstance(value, (dict, list, tuple, set, pd.DataFrame, pd.Series, pd.Index)):
        return None

    if isinstance(value, np.ndarray):
        if value.ndim != 0:
            return None
        value = value.item()

    try:
        isna_result = pd.isna(value)
    except (TypeError, ValueError) as exc:
        if hasattr(value, "__array__"):
            logger.debug(
                "[%s] pd.isna failed for array-like object; re-raise: value_type=%s error_type=%s",
                context,
                type(value).__name__,
                type(exc).__name__,
            )
            raise
        logger.debug(
            "[%s] pd.isna fallback: value_type=%s error_type=%s",
            context,
            type(value).__name__,
            type(exc).__name__,
        )
        return None

    if isinstance(isna_result, (bool, np.bool_)):
        return bool(isna_result)

    if isinstance(isna_result, np.ndarray):
        if isna_result.ndim == 0:
            return bool(isna_result.item())
        logger.debug(
            "[%s] pd.isna returned non-scalar result: value_type=%s result_type=%s",
            context,
            type(value).__name__,
            type(isna_result).__name__,
        )
        return None

    logger.debug(
        "[%s] pd.isna returned unexpected result type: value_type=%s result_type=%s",
        context,
        type(value).__name__,
        type(isna_result).__name__,
    )
    return None
