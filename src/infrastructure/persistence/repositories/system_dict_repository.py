# -*- coding: utf-8 -*-
"""
@file: system_dict_repository.py
@description: 系统数据字典（国家）仓储：sys_dict_countries 的读写实现。
    list_active_countries 供接口层只读；upsert_countries 在单写事务内完成
    插入/更新与「上游消失国家」的软禁用，保证一致窗口。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models.system_dict import SysDictCountry

if TYPE_CHECKING:
    from src.storage import DatabaseManager


class SqlAlchemySystemDictRepository:
    """基于 SQLAlchemy 的国家字典仓储实现。"""

    def __init__(self, db_manager: "DatabaseManager") -> None:
        """构造国家字典仓储并保存数据库管理器。"""
        self._db = db_manager

    def list_active_countries(self) -> List[Dict[str, Any]]:
        """列出全部启用国家（is_active=1），按 country_id 升序，返回传输层字典。"""
        with self._db.get_session() as session:
            rows = (
                session.execute(
                    select(SysDictCountry)
                    .where(SysDictCountry.is_active.is_(True))
                    .order_by(SysDictCountry.country_id)
                )
                .scalars()
                .all()
            )
            return [self._to_dict(row) for row in rows]

    def upsert_countries(self, countries: List[Dict[str, Any]]) -> Dict[str, int]:
        """写入/更新国家字典，并软禁用上游已下线的国家。

        Args:
            countries: 上游归一化后的国家列表，每项含 country_id 等字段。

        Returns:
            {"upserted": 新增条数, "deactivated": 软禁用条数}。
        """

        def _write(session: Session) -> Dict[str, int]:
            """在单写事务内完成 upsert 与软禁用。"""
            upstream_ids: set[str] = set()
            upserted = 0
            for country in countries:
                country_code = country["country_id"]
                upstream_ids.add(country_code)
                row = session.execute(
                    select(SysDictCountry).where(SysDictCountry.country_id == country_code)
                ).scalars().first()
                if row is None:
                    row = SysDictCountry(country_id=country_code)
                    session.add(row)
                    upserted += 1
                row.country_name = country.get("country_name", "")
                row.currency = country.get("currency", "")
                row.currency_name = country.get("currency_name", "")
                row.flag_uri = country.get("flag_uri", "")
                row.source = country.get("source", "wallstreetcn")
                row.is_active = True

            deactivated = 0
            if upstream_ids:
                inactive_rows = (
                    session.execute(
                        select(SysDictCountry).where(
                            SysDictCountry.country_id.notin_(upstream_ids),
                            SysDictCountry.is_active.is_(True),
                        )
                    )
                    .scalars()
                    .all()
                )
                for row in inactive_rows:
                    row.is_active = False
                    deactivated += 1
            return {"upserted": upserted, "deactivated": deactivated}

        return self._db._run_write_transaction("system_dict.upsert_countries", _write)

    @staticmethod
    def _to_dict(row: SysDictCountry) -> Dict[str, Any]:
        """把国家字典行转为传输层字典（仅暴露接口所需字段）。"""
        return {
            "country_id": row.country_id,
            "country_name": row.country_name,
            "currency": row.currency,
            "currency_name": row.currency_name,
            "flag_uri": row.flag_uri,
        }
