# -*- coding: utf-8 -*-
"""
@file: system_dict.py
@description: 系统数据字典 ORM 模型：国家/市场字典表 sys_dict_countries。
    国家信息低频静态，落库后作为全项目唯一真源，供 /api/v1/system/countries 等读取。
@author: Lensgcx (GaoCangxiong)
"""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, UniqueConstraint

from src.infrastructure.persistence.base import Base, utc_naive_now


class SysDictCountry(Base):
    """国家/市场字典：country_id 为规范大写业务键，全项目统一从此表读取。"""

    __tablename__ = "sys_dict_countries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 规范大写国家代码（ISO 3166-1 alpha-2），如 US/CN/HK；全项目唯一真源
    country_id = Column(String(8), nullable=False)
    # 国家/地区中文名，如 美国/中国/香港
    country_name = Column(String(64), nullable=False)
    # 规范大写货币代码（ISO 4217），如 USD/CNY/HKD
    currency = Column(String(8), nullable=False, default="")
    # 货币中文名，如 美元/人民币/港币
    currency_name = Column(String(32), nullable=False, default="")
    # 国旗图片远程 URL（沿用上游，未本地化）
    flag_uri = Column(String(512), nullable=False, default="")
    # 数据来源上游标识，当前仅 wallstreetcn
    source = Column(String(32), nullable=False, default="wallstreetcn")
    # 软禁用：上游下线国家置 0，不硬删，避免破坏历史事件引用
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_naive_now)
    updated_at = Column(DateTime, default=utc_naive_now, onupdate=utc_naive_now)

    __table_args__ = (
        UniqueConstraint("country_id", name="uix_sys_dict_country_id"),
        Index("ix_sys_dict_country_active", "is_active"),
    )
