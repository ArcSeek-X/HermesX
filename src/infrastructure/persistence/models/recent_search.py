# -*- coding: utf-8 -*-
"""个股最近搜索记录模型。

本模块只声明 ORM 表结构；全部模型注册在 `src.infrastructure.persistence.base.Base`
这唯一一个 metadata 上。导入本模块即完成注册，不要在别处再建 Base。
"""

from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from src.infrastructure.persistence.base import Base, utc_naive_now


class StockRecentSearch(Base):
    """个股最近搜索记录表。

    按 ``(user_id, stock_code)`` 唯一：重复搜索只刷新名称与更新时间并顶到队首；
    单用户本地应用统一使用 ``user_id='default'``，预留多用户扩展。
    """

    __tablename__ = 'stock_recent_search'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, default='default', index=True)
    stock_code = Column(String(32), nullable=False, index=True)
    stock_name = Column(String(64), nullable=True)
    market = Column(String(16), nullable=True)
    create_date_time = Column(DateTime, nullable=False, default=utc_naive_now)
    update_date_time = Column(
        DateTime,
        nullable=False,
        default=utc_naive_now,
        onupdate=utc_naive_now,
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'stock_code', name='uix_recent_search_user_code'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """把最近搜索记录转换为传输层字典（时间列统一 ISO 字符串）。"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "market": self.market,
            "create_date_time": self.create_date_time.isoformat() if self.create_date_time else None,
            "update_date_time": self.update_date_time.isoformat() if self.update_date_time else None,
        }
