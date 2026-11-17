# -*- coding: utf-8 -*-
"""
@file: system_dict.py
@description: 系统数据字典接口响应模型：国家字典读取与同步。
@author: Lensgcx (GaoCangxiong)
"""

from typing import List

from pydantic import BaseModel


class SysDictCountryItem(BaseModel):
    """国家字典单项：字段与前端 CountryMarketOptionDef 对齐。"""

    country_id: str
    country_name: str
    currency: str = ""
    currency_name: str = ""
    flag_uri: str = ""


class SysDictCountriesResponse(BaseModel):
    """国家字典读取响应。"""

    items: List[SysDictCountryItem] = []
    degraded: bool = False


class SysDictCountriesSyncResponse(BaseModel):
    """国家字典同步响应。"""

    upserted: int = 0
    deactivated: int = 0
    degraded: bool = False
