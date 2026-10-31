# -*- coding: utf-8 -*-
"""行情原始数据模型（`stock_daily`）。

本模块只声明 ORM 表结构；全部模型注册在 `src.infrastructure.persistence.base.Base`
这唯一一个 metadata 上。导入本模块即完成注册，不要在别处再建 Base。
"""

from datetime import datetime, date
from typing import Dict, Any

from sqlalchemy import (
    Column,
    String,
    Float,
    Date,
    DateTime,
    Integer,
    Index,
    UniqueConstraint,
)

from src.infrastructure.persistence.base import Base


class StockDaily(Base):
    """
    股票日线数据模型
    
    存储每日行情数据和计算的技术指标
    支持多股票、多日期的唯一约束

    使用约定：
    - 存的是**日线全量历史**（自上市以来），不是滚动窗口，用于回测与技术分析；
    - 写入走 upsert（唯一键 code+date 冲突即更新），因此重复抓取同一区间不会产生重复行；
    - ``date`` 为交易日（Date 类型，非 DateTime），非交易日不会出现在本表；
    - 技术指标（ma5/ma10/ma20/volume_ratio）由抓取侧计算后一并落库，
      查询侧不再实时计算，避免每次读取重复运算。
    """
    __tablename__ = 'stock_daily'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 股票代码（如 600519, 000001）
    code = Column(String(10), nullable=False, index=True)
    
    # 交易日期（Date，仅交易日）
    date = Column(Date, nullable=False, index=True)
    
    # OHLC 数据
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    
    # 成交数据
    volume = Column(Float)  # 成交量（股）
    amount = Column(Float)  # 成交额（元）
    pct_chg = Column(Float)  # 涨跌幅（%）
    
    # 技术指标
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    volume_ratio = Column(Float)  # 量比
    
    # 数据来源：记录实际取到该行数据的 fetcher（如 AkshareFetcher）。
    # 多数据源 fallback 时可用于追溯是哪一源供数，排障时很有用。
    data_source = Column(String(50))
    
    # 更新时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 唯一约束：同一股票同一日期只能有一条数据（写入按此键 upsert）
    __table_args__ = (
        UniqueConstraint('code', 'date', name='uix_code_date'),
        # 覆盖「按股票查区间」与「按日期查全市场」两类查询
        Index('ix_code_date', 'code', 'date'),
    )
    
    def __repr__(self):
        return f"<StockDaily(code={self.code}, date={self.date}, close={self.close})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
            'pct_chg': self.pct_chg,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'volume_ratio': self.volume_ratio,
            'data_source': self.data_source,
        }
