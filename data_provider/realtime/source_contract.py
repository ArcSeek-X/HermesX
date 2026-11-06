"""实时行情 Source 协议；独立于默认源注册和 Manager 装配。"""

from data_provider.common.base import DataSource
from data_provider.realtime.types import UnifiedRealtimeQuote


class RealtimeSource(DataSource[str, UnifiedRealtimeQuote]):
    """实时行情 source 公共抽象。"""
