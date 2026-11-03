# -*- coding: utf-8 -*-
"""
分析请求共享的元数据常量。

定义选股来源（selection source）枚举与对应的校验正则，供 API 层与用例层共用，
保证「手动 / 自动补全 / 导入 / 图片」四类来源在多处语义一致。
"""

from __future__ import annotations


SELECTION_SOURCES: tuple[str, ...] = ("manual", "autocomplete", "import", "image")
SELECTION_SOURCE_PATTERN = "^(" + "|".join(SELECTION_SOURCES) + ")$"
