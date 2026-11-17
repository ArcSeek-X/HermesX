# -*- coding: utf-8 -*-
"""Helpers for parsing the user-facing STOCK_LIST value.

解析用户配置的 STOCK_LIST（自选股列表）的辅助函数，处理中英文逗号、空格、分号等分隔符。
"""

from __future__ import annotations

import re
from typing import List

_STOCK_LIST_SEPARATOR_RE = re.compile(r"[\s,;\uFF0C\u3001\uFF1B]+")


def split_stock_list(value: str) -> List[str]:
    """Split STOCK_LIST values on common copy/paste separators.

    按常见复制粘贴分隔符（空白 / 英文逗号 / 中文逗号 / 分号）切分 STOCK_LIST，去空。
    """
    return [
        item.strip()
        for item in _STOCK_LIST_SEPARATOR_RE.split(value or "")
        if item.strip()
    ]


def serialize_stock_list(value: str) -> str:
    """Return STOCK_LIST in the canonical comma-separated storage form.

    将 STOCK_LIST 归一成标准逗号分隔的存储形式。
    """
    return ",".join(split_stock_list(value))
