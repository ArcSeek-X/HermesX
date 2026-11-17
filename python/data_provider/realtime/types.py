"""实时行情 DTO、源标识与值转换；不导入 Manager 或创建资源。"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from src.domain.market.chip_distribution import ChipDistribution  # noqa: F401


def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """
    安全转换为浮点数

    处理场景：
    - None / 空字符串 → default
    - pandas NaN / numpy NaN → default
    - 数值字符串 → float
    - 已是数值 → float

    Args:
        val: 待转换的值
        default: 转换失败时的默认值

    Returns:
        转换后的浮点数，或默认值
    """
    try:
        if val is None:
            return default

        # 处理字符串
        if isinstance(val, str):
            val = val.strip()
            if val == "" or val == "-" or val == "--":
                return default

        # 处理 pandas/numpy NaN
        # 使用 math.isnan 而不是 pd.isna，避免强制依赖 pandas
        import math
        try:
            if math.isnan(float(val)):
                return default
        except (ValueError, TypeError):
            pass

        return float(val)
    except (ValueError, TypeError):
        return default



def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """
    安全转换为整数

    先转换为 float，再取整，处理 "123.0" 这类情况

    Args:
        val: 待转换的值
        default: 转换失败时的默认值

    Returns:
        转换后的整数，或默认值
    """
    f_val = safe_float(val, default=None)
    if f_val is not None:
        return int(f_val)
    return default



class RealtimeSource(Enum):
    """实时行情数据源"""
    EFINANCE = "efinance"           # 东方财富（efinance库）
    AKSHARE_EM = "akshare_em"       # 东方财富（akshare库）
    AKSHARE_SINA = "akshare_sina"   # 新浪财经
    AKSHARE_QQ = "akshare_qq"       # 腾讯财经
    TUSHARE = "tushare"             # Tushare Pro
    TICKFLOW = "tickflow"           # TickFlow
    TENCENT = "tencent"             # 腾讯直连
    SINA = "sina"                   # 新浪直连
    STOOQ = "stooq"                 # Stooq 美股兜底
    LONGBRIDGE = "longbridge"       # 长桥（美股/港股兜底）
    FALLBACK = "fallback"           # 降级兜底



@dataclass
class UnifiedRealtimeQuote:
    """
    统一实时行情数据结构

    设计原则：
    - 各数据源返回的字段可能不同，缺失字段用 None 表示
    - 主流程使用 getattr(quote, field, None) 获取，保证兼容性
    - source 字段标记数据来源，便于调试
    """
    code: str
    name: str = ""
    source: RealtimeSource = RealtimeSource.FALLBACK

    # === 数据质量元数据（由 DataFetcherManager 统一补齐）===
    fetched_at: Optional[str] = None             # 本系统获取时间（ISO 8601 datetime）
    provider_timestamp: Optional[str] = None     # Provider 真实行情时间（ISO 8601 datetime）
    is_stale: Optional[bool] = None              # provider_timestamp 超过最小 TTL 阈值时为 True
    stale_seconds: Optional[int] = None          # provider_timestamp 距 fetched_at 的秒数
    fallback_from: Optional[str] = None          # 整源 fallback 的失败首选源 token
    market: Optional[str] = None                 # 市场标签（cn/hk/us/jp/kr/tw）
    currency: Optional[str] = None               # 报价币种（JPY/KRW/TWD/USD/HKD/CNY 等）
    data_quality: Optional[str] = None           # ok/partial/unavailable
    missing_fields: Optional[list[str]] = None   # provider 缺失的关键字段

    # === 核心价格数据（几乎所有源都有）===
    price: Optional[float] = None           # 最新价
    change_pct: Optional[float] = None      # 涨跌幅(%)
    change_amount: Optional[float] = None   # 涨跌额

    # === 量价指标（部分源可能缺失）===
    volume: Optional[int] = None            # 成交量（股，与历史日线口径一致）
    amount: Optional[float] = None          # 成交额（元）
    volume_ratio: Optional[float] = None    # 量比
    turnover_rate: Optional[float] = None   # 换手率(%)
    amplitude: Optional[float] = None       # 振幅(%)

    # === 价格区间 ===
    open_price: Optional[float] = None      # 开盘价
    high: Optional[float] = None            # 最高价
    low: Optional[float] = None             # 最低价
    pre_close: Optional[float] = None       # 昨收价

    # === 估值指标（仅东财等全量接口有）===
    pe_ratio: Optional[float] = None        # 市盈率(动态)
    pb_ratio: Optional[float] = None        # 市净率
    total_mv: Optional[float] = None        # 总市值(元)
    circ_mv: Optional[float] = None         # 流通市值(元)

    # === 其他指标 ===
    change_60d: Optional[float] = None      # 60日涨跌幅(%)
    high_52w: Optional[float] = None        # 52周最高
    low_52w: Optional[float] = None         # 52周最低

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（过滤 None 值）"""
        result = {
            'code': self.code,
            'name': self.name,
            'source': self.source.value,
        }
        # 只添加非 None 的字段
        optional_fields = [
            'fetched_at', 'provider_timestamp', 'is_stale', 'stale_seconds',
            'fallback_from', 'market', 'currency', 'data_quality', 'missing_fields',
            'price', 'change_pct', 'change_amount', 'volume', 'amount',
            'volume_ratio', 'turnover_rate', 'amplitude',
            'open_price', 'high', 'low', 'pre_close',
            'pe_ratio', 'pb_ratio', 'total_mv', 'circ_mv',
            'change_60d', 'high_52w', 'low_52w'
        ]
        for f in optional_fields:
            val = getattr(self, f, None)
            if val is not None:
                result[f] = val
        return result

    def has_basic_data(self) -> bool:
        """检查是否有基本的价格数据"""
        return self.price is not None and self.price > 0

    def has_volume_data(self) -> bool:
        """检查是否有量价数据"""
        return self.volume_ratio is not None or self.turnover_rate is not None

