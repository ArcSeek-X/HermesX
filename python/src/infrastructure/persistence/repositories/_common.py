# -*- coding: utf-8 -*-
"""仓储共享的纯函数工具。

这里只放「无状态、无 IO、无业务语义」的转换函数，供多个仓储复用。放进仓储类
会因为跨域互调而把仓储重新耦合成一大坨；放进 ``storage.py`` 则会让已经收口的
门面重新长实现。

约定：本模块不 import 任何仓储、ORM 模型或 ``DatabaseManager``，保持零依赖。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd


def normalize_daily_date(value: Any) -> Any:
    """把入参归一化为 ``date``，兼容字符串 / pandas.Timestamp / datetime。

    ``stock_daily.date`` 是 Date 列，而数据源常返回字符串或 Timestamp，
    入库前统一转换，避免同一日期因类型不同被当成两条记录。
    """
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    return value


def normalize_sql_value(value: Any) -> Any:
    """把 NaN / NaT 等 pandas 缺失值转成 ``None``，避免写入非法的浮点 NaN。"""
    return None if pd.isna(value) else value


def safe_json_dumps(data: Any) -> str:
    """安全序列化为 JSON 字符串。

    反序列化方（报告渲染、诊断接口）只保证拿到字符串，不保证结构；遇到不可
    序列化对象时退化为 ``str(data)``，不允许因为一个字段让整条写入失败。
    """
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps(str(data), ensure_ascii=False)


def build_raw_result(result: Any) -> dict:
    """把分析结果对象展开为可落库的原始结果字典。

    以 ``to_dict()`` 为基础，再补 ``data_sources`` 与 ``raw_response``：前者用于
    回溯数据来源，后者是 LLM 原始响应，两者都不在 ``to_dict()`` 的稳定契约里。
    """
    data = result.to_dict() if hasattr(result, "to_dict") else {}
    data.update({
        'data_sources': getattr(result, 'data_sources', ''),
        'raw_response': getattr(result, 'raw_response', None),
    })
    return data
