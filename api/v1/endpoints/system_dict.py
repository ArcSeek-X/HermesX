# -*- coding: utf-8 -*-
"""
@file: system_dict.py
@description: 系统数据字典接口：国家字典读取与同步。
    读取端点对外独立暴露为 /api/v1/system/countries（与 intelligence / live-calendar 解耦）。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from fastapi import APIRouter

from api.v1.schemas.system_dict import (
    SysDictCountriesResponse,
    SysDictCountriesSyncResponse,
)
from src.application.system.system_dict_service import SystemDictService

router = APIRouter(tags=["SystemDict"])


@router.get(
    "/countries",
    response_model=SysDictCountriesResponse,
    summary="List system country dictionary",
)
def list_system_countries() -> SysDictCountriesResponse:
    """读取国家字典（DB-first，落库后不再回源）。"""
    return SysDictCountriesResponse(**SystemDictService().list_countries())


@router.post(
    "/countries/sync",
    response_model=SysDictCountriesSyncResponse,
    summary="Sync country dictionary from upstream",
)
def sync_system_countries() -> SysDictCountriesSyncResponse:
    """从上游对账刷新国家字典（幂等 upsert + 软禁用下线国家）。"""
    return SysDictCountriesSyncResponse(**SystemDictService().sync_countries())
