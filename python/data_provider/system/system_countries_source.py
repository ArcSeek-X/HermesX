# -*- coding: utf-8 -*-
"""
@file: system_countries_source.py
@description: 系统数据字典上游源适配：国家字典。
    复用华尔街见闻财经日历的国家字典抓取，归一化 country_id / currency 为大写，
    与全项目大写规范一致；数据字典服务（SystemDictService）依赖本模块取数。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Any, Dict, List

from data_provider.calendar.wallstreetcn_source import WallstreetcnCalendarFetcher


def fetch_countries() -> List[Dict[str, Any]]:
    """拉取并归一化国家字典。

    Returns:
        国家列表，每项含大写 country_id / currency 与中文 country_name / currency_name、flag_uri。
    """
    fetcher = WallstreetcnCalendarFetcher()
    entries = fetcher.fetch_countries()
    return [
        {
            "country_id": entry.country_id.strip().upper(),
            "country_name": entry.country_name.strip(),
            "currency": entry.currency.strip().upper(),
            "currency_name": entry.currency_name.strip(),
            "flag_uri": entry.flag_uri.strip(),
        }
        for entry in entries
    ]
