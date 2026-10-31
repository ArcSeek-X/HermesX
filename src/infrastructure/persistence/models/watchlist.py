# -*- coding: utf-8 -*-
"""自选股分组与条目模型。

本模块只声明 ORM 表结构；全部模型注册在 `src.infrastructure.persistence.base.Base`
这唯一一个 metadata 上。导入本模块即完成注册，不要在别处再建 Base。
"""

from typing import Dict, Any

from sqlalchemy import (
    Column,
    String,
    SmallInteger,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Text,
)

from src.infrastructure.persistence.base import Base, utc_naive_now


class WatchlistGroup(Base):
    """自选股分类表。

    每个分类有唯一名称、分组编码、排序权重与审计时间戳，支持新增/编辑/逻辑删除。
    """

    __tablename__ = 'stock_watchlist_group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    group_code = Column(String(64), nullable=False, unique=True, index=True, comment='分组编码(服务端生成,企业内唯一)')
    description = Column(String(255), nullable=True, default='', comment='分类描述')
    delete_flag = Column(SmallInteger, nullable=False, default=0, index=True, comment='逻辑删除标志(0有效/1删除)')
    create_user_id = Column(String(64), nullable=True, comment='创建人ID')
    create_date_time = Column(DateTime, default=utc_naive_now, nullable=False, comment='创建时间')
    update_user_id = Column(String(64), nullable=True, comment='更新人ID')
    update_date_time = Column(DateTime, default=utc_naive_now, onupdate=utc_naive_now, nullable=False, comment='更新时间')

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "sort_order": self.sort_order,
            "group_code": self.group_code,
            "description": self.description or '',
            "delete_flag": self.delete_flag,
            "create_user_id": self.create_user_id,
            "create_date_time": self.create_date_time.isoformat() if self.create_date_time else None,
            "update_user_id": self.update_user_id,
            "update_date_time": self.update_date_time.isoformat() if self.update_date_time else None,
        }


class WatchlistItem(Base):
    """自选股表。

    每条记录挂在某个分类下，含股票代码、冗余名称、描述、分类内顺序与审计时间戳。
    同一分类下股票代码唯一，可移动到其它分类（改 group_id）。
    """

    __tablename__ = 'stock_watchlist_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        Integer,
        ForeignKey('stock_watchlist_group.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    stock_code = Column(String(32), nullable=False, index=True)
    stock_name = Column(String(64))
    description = Column(Text, comment='自选股描述(原note)')
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    delete_flag = Column(SmallInteger, nullable=False, default=0, index=True, comment='逻辑删除标志(0有效/1删除)')
    create_user_id = Column(String(64), nullable=True, comment='创建人ID')
    create_date_time = Column(DateTime, default=utc_naive_now, nullable=False, comment='创建时间')
    update_user_id = Column(String(64), nullable=True, comment='更新人ID')
    update_date_time = Column(DateTime, default=utc_naive_now, onupdate=utc_naive_now, nullable=False, comment='更新时间')

    __table_args__ = (
        UniqueConstraint('group_id', 'stock_code', name='uix_watchlist_item_group_code'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "description": self.description,
            "sort_order": self.sort_order,
            "delete_flag": self.delete_flag,
            "create_user_id": self.create_user_id,
            "create_date_time": self.create_date_time.isoformat() if self.create_date_time else None,
            "update_user_id": self.update_user_id,
            "update_date_time": self.update_date_time.isoformat() if self.update_date_time else None,
        }
