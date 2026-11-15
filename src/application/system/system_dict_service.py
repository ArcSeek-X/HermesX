# -*- coding: utf-8 -*-
"""
@file: system_dict_service.py
@description: 系统数据字典服务：国家字典的读取与同步。
    读取走 DB-first（落库后不再每次回源）；空表时懒播种；上游失败仅库空时降级。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from data_provider.system.system_countries_source import fetch_countries as fetch_upstream_countries
from src.infrastructure.persistence.repositories.system_dict_repository import (
    SqlAlchemySystemDictRepository,
)
from src.storage import DatabaseManager

logger = logging.getLogger("application.system.system_dict_service")


class SystemDictService:
    """国家字典服务：DB-first 读取 + 回源对账。"""

    def __init__(self, repository: SqlAlchemySystemDictRepository | None = None) -> None:
        """构造国家字典服务；仓储缺省时绑定进程内 DatabaseManager 单例。"""
        self._repository = repository or SqlAlchemySystemDictRepository(DatabaseManager.get_instance())

    def list_countries(self) -> Dict[str, Any]:
        """读取国家字典（DB-first）。

        Returns:
            {"items": [...], "degraded": bool}；库非空直接返回，空表懒播种后返回，
            库空且上游失败则 degraded=True、items 为空。
        """
        active_rows = self._repository.list_active_countries()
        if active_rows:
            return {"items": active_rows, "degraded": False}

        seeded_rows = self._fetch_and_persist()
        if seeded_rows:
            return {"items": seeded_rows, "degraded": False}
        return {"items": [], "degraded": True}

    def sync_countries(self) -> Dict[str, Any]:
        """从上游对账刷新国家字典（幂等 upsert + 软禁用下线国家）。

        Returns:
            {"upserted": int, "deactivated": int, "degraded": bool}。
        """
        try:
            upstream_countries = fetch_upstream_countries()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sync country dictionary failed: %s", exc)
            return {"upserted": 0, "deactivated": 0, "degraded": True}
        result = self._repository.upsert_countries(upstream_countries)
        return {
            "upserted": result["upserted"],
            "deactivated": result["deactivated"],
            "degraded": False,
        }

    def _fetch_and_persist(self) -> List[Dict[str, Any]] | None:
        """回源拉取并落库；失败或无数据时返回 None。"""
        try:
            upstream_countries = fetch_upstream_countries()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Seed country dictionary failed: %s", exc)
            return None
        if not upstream_countries:
            return None
        self._repository.upsert_countries(upstream_countries)
        return self._repository.list_active_countries()
