"""Market review value objects shared by orchestration and prompt assembly."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class MarketIndex:
    """大盘指数数据"""

    code: str  # 指数代码
    name: str  # 指数名称
    current: float = 0.0  # 当前点位
    change: float = 0.0  # 涨跌点数
    change_pct: float = 0.0  # 涨跌幅(%)
    open: float = 0.0  # 开盘点位
    high: float = 0.0  # 最高点位
    low: float = 0.0  # 最低点位
    prev_close: float = 0.0  # 昨收点位
    volume: float = 0.0  # 成交量（手）
    amount: float = 0.0  # 成交额（元）
    amplitude: float = 0.0  # 振幅(%)

    def to_dict(self) -> Dict[str, Any]:
        """将复盘对象转换为字典。"""
        return {
            "code": self.code,
            "name": self.name,
            "current": self.current,
            "change": self.change,
            "change_pct": self.change_pct,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "amount": self.amount,
            "amplitude": self.amplitude,
        }


@dataclass
class MarketOverview:
    """市场概览数据"""

    date: str  # 日期
    indices: List[MarketIndex] = field(default_factory=list)  # 主要指数
    up_count: int = 0  # 上涨家数
    down_count: int = 0  # 下跌家数
    flat_count: int = 0  # 平盘家数
    limit_up_count: int = 0  # 涨停家数
    limit_down_count: int = 0  # 跌停家数
    total_amount: float = 0.0  # 两市成交额（亿元）
    # north_flow: float = 0.0           # 北向资金净流入（亿元）- 已废弃，接口不可用

    # 板块涨幅榜
    top_sectors: List[Dict] = field(default_factory=list)  # 涨幅前5板块
    bottom_sectors: List[Dict] = field(default_factory=list)  # 跌幅前5板块
    top_concepts: List[Dict] = field(default_factory=list)  # 涨幅前5概念
    bottom_concepts: List[Dict] = field(default_factory=list)  # 跌幅前5概念


@dataclass
class MarketLightReviewResult:
    """Internal market-review parts built from one overview fetch."""

    overview: MarketOverview
    report: str
    market_light_snapshot: Optional[Dict[str, Any]]
    structured_payload: Dict[str, Any] = field(default_factory=dict)
