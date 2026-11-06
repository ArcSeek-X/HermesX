"""tickflow 共享协议、连接和配额；无能力选源/回退或第二份资源。"""

from __future__ import annotations

import logging
import math
import os
from data_provider.realtime.types import safe_int
from src.domain.market.stock_codes import is_bse_code, normalize_stock_code

logger = logging.getLogger("data_provider.tickflow_fetcher")

from dataclasses import dataclass
from typing import Callable
from typing import Any, Dict, Optional, Tuple, List
import pandas as pd


@dataclass(frozen=True)
class TickflowClientAccess:
    """窄资源访问契约；状态写回原所有者，兼容旧资源扩展点。"""

    use_build_client: Callable
    use_coerce_frame: Callable
    read_capability_checked_at: Callable
    read_capability_lock: Callable
    read_capability_supported: Callable
    read_client: Callable
    read_client_lock: Callable
    read_daily_cache: Callable
    read_daily_cache_lock: Callable
    read_quote_cache: Callable
    read_quote_cache_lock: Callable
    read_api_key: Callable
    read_kline_adjust: Callable
    read_timeout: Callable
    write_client: Callable
    read_global_CAPABILITY_NEGATIVE_CACHE_TTL_SECONDS: Callable
    read_global_logger: Callable
    read_global_monotonic: Callable

    def close(self) -> None:
        """Close the underlying TickFlow client if it was created."""
        with self.read_client_lock():
            client = self.read_client()
            self.write_client(None)
        with self.read_capability_lock():
            for key in self.read_capability_supported():
                self.read_capability_supported()[key] = None
            self.read_capability_checked_at().clear()
        if client is not None:
            try:
                client.close()
            except Exception as exc:
                self.read_global_logger().debug(
                    "[TickFlowFetcher] close client failed: %s", exc
                )

    def _build_client(self):
        """惰性构建 TickFlow 客户端实例。"""
        from tickflow import TickFlow

        return TickFlow(api_key=self.read_api_key(), timeout=self.read_timeout())

    def _get_client(self):
        """返回已构建客户端；无 api_key 时返回 None（fail-open）。"""
        if not self.read_api_key():
            return None
        if self.read_client() is not None:
            return self.read_client()
        with self.read_client_lock():
            if self.read_client() is None:
                self.write_client(self.use_build_client())
            return self.read_client()

    def _daily_cache_key(
        self, symbol: str, start_date: str, end_date: str
    ) -> Tuple[str, str, str, str]:
        """构造日线缓存键（符号/区间/复权）。"""
        return (symbol.upper(), start_date, end_date, self.read_kline_adjust())

    def _get_daily_cache(
        self, cache_key: Tuple[str, str, str, str]
    ) -> Optional[pd.DataFrame]:
        """从进程内日线缓存读取命中项。"""
        with self.read_daily_cache_lock():
            cached = self.read_daily_cache().get(cache_key)
            if cached is not None:
                return cached.copy()
        return None

    def _set_daily_cache(
        self, cache_key: Tuple[str, str, str, str], df: pd.DataFrame
    ) -> None:
        """写入日线缓存（受锁保护）。"""
        with self.read_daily_cache_lock():
            self.read_daily_cache()[cache_key] = self.use_coerce_frame(df)

    def _capability_available(self, capability: str) -> bool:
        """检查某能力是否当前可用（带冷却时间）。"""
        now = self.read_global_monotonic()()
        with self.read_capability_lock():
            supported = self.read_capability_supported().get(capability)
            if supported is not False:
                return True
            checked_at = self.read_capability_checked_at().get(capability, 0.0)
            if (
                now - checked_at
                >= self.read_global_CAPABILITY_NEGATIVE_CACHE_TTL_SECONDS()
            ):
                self.read_capability_supported()[capability] = None
                self.read_capability_checked_at().pop(capability, None)
                return True
            return False

    def _mark_capability(self, capability: str, supported: bool) -> None:
        """记录某能力当前是否可用（受锁保护）。"""
        with self.read_capability_lock():
            self.read_capability_supported()[capability] = supported
            self.read_capability_checked_at()[
                capability
            ] = self.read_global_monotonic()()

    def _store_quotes(self, quotes: Any) -> int:
        """将实时报价批量写入缓存，返回写入条数。"""
        if not quotes:
            return 0
        if isinstance(quotes, dict):
            quotes_iter = [quotes]
        else:
            quotes_iter = list(quotes)
        stored = 0
        now = self.read_global_monotonic()()
        with self.read_quote_cache_lock():
            for quote in quotes_iter:
                if not isinstance(quote, dict):
                    continue
                symbol = str(quote.get("symbol") or "").upper()
                if not symbol:
                    continue
                self.read_quote_cache()[symbol] = (now, quote)
                stored += 1
        return stored

    def _get_cached_quote(
        self, symbol: str, ttl_seconds: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """读取带 TTL 的实时报价缓存。"""
        ttl = 600 if ttl_seconds is None else max(0, int(ttl_seconds))
        now = self.read_global_monotonic()()
        with self.read_quote_cache_lock():
            cached = self.read_quote_cache().get(symbol.upper())
            if not cached:
                return None
            cached_at, quote = cached
            if ttl and now - cached_at > ttl:
                self.read_quote_cache().pop(symbol.upper(), None)
                return None
            return dict(quote)


_SUPPORTED_KLINE_ADJUSTS = {
    "none",
    "forward",
    "backward",
    "forward_additive",
    "backward_additive",
}


def _parse_env_int(name: str, default: int, minimum: int = 1) -> int:
    """从环境变量读取整数，解析失败或空值回退默认（含最小值约束）。"""
    raw_value = os.getenv(name)
    if raw_value is None or not str(raw_value).strip():
        return default
    try:
        parsed = int(str(raw_value).strip())
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r; falling back to %s", name, raw_value, default)
        return default
    return max(minimum, parsed)


def safe_float(value: Any) -> Optional[float]:
    """将值安全转为 float；空/占位符返回 None。"""
    if value in (None, "", "-"):
        return None
    try:
        numeric = float(value)
        if math.isnan(numeric):
            return None
        return numeric
    except (TypeError, ValueError):
        return None



def parse_bool(value: Optional[str], default: bool) -> bool:
    """解析布尔值；None 或非真值返回默认值。"""
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized not in {"0", "false", "no", "off"}



def normalize_priority(value: Optional[int]) -> int:
    """归一化数据源优先级，缺省回退环境变量 TICKFLOW_PRIORITY。"""
    if value is None:
        return _parse_env_int("TICKFLOW_PRIORITY", 2, minimum=0)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        logger.warning("Invalid TickFlow priority=%r; falling back to 2", value)
        return 2



def normalize_adjust(value: Optional[str]) -> str:
    """归一化复权方式（qfq/hfq/none）。"""
    normalized = (value or "none").strip().lower()
    if normalized in _SUPPORTED_KLINE_ADJUSTS:
        return normalized
    logger.warning(
        "Invalid TICKFLOW_KLINE_ADJUST=%r; falling back to none",
        value,
    )
    return "none"



def ratio_to_percent(value: Any, *, use_safe_float) -> Optional[float]:
    """将比率转为百分比浮点值。"""
    ratio = use_safe_float(value)
    if ratio is None:
        return None
    return ratio * 100.0



def ratio_series_to_percent(series: pd.Series) -> pd.Series:
    """将比率序列逐元素转为百分比。"""
    return pd.to_numeric(series, errors="coerce") * 100.0



def cn_lots_to_shares(lots: Any, default: Optional[int]=None) -> Any:
    """将 A 股手数序列换算为股数（×100）。"""
    if isinstance(lots, pd.Series):
        return pd.to_numeric(lots, errors="coerce") * 100
    volume = safe_int(lots, default)
    if volume is None:
        return default
    return volume * 100



def extract_name(quote: Dict[str, Any]) -> str:
    """从行情报价中提取证券名称。"""
    ext = quote.get("ext") or {}
    name = ext.get("name") or quote.get("name") or ""
    return str(name).strip()



def is_permission_error(exc: Exception) -> bool:
    """判断异常是否为权限类错误（按状态码/code 匹配）。"""
    status_code = getattr(exc, "status_code", None)
    code = str(getattr(exc, "code", "") or "").upper()
    message = f"{getattr(exc, 'message', '')} {exc}".strip().lower()

    if status_code == 403:
        return True
    if code in {"PERMISSION_DENIED", "FORBIDDEN", "UNAUTHORIZED"}:
        return True
    return any(
        keyword in message
        for keyword in (
            "permission",
            "forbidden",
            "unauthorized",
            "not entitled",
            "no access",
            "\u6743\u9650",
            "\u65e0\u6743",
            "\u5957\u9910",
        )
    )



def is_universe_permission_error(exc: Exception, *, use_is_permission_error) -> bool:
    """判断异常是否为标的池权限错误。"""
    message = f"{getattr(exc, 'message', '')} {exc}".strip().lower()
    return use_is_permission_error(exc) or "universe" in message or "\u6807\u7684\u6c60" in message



def is_cn_equity_symbol(symbol: str) -> bool:
    """判断符号是否为 A 股普通股票代码。"""
    normalized = normalize_stock_code(symbol)
    upper_symbol = (symbol or "").strip().upper()
    return (
        normalized.isdigit()
        and len(normalized) == 6
        and upper_symbol.endswith((".SH", ".SZ", ".BJ"))
    )



def coerce_frame(value: Any) -> pd.DataFrame:
    """将任意值强制为 DataFrame，失败时返回空框。"""
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        try:
            return pd.DataFrame(value)
        except ValueError as exc:
            if "all scalar values" in str(exc).lower():
                return pd.DataFrame([value])
            raise
    return pd.DataFrame(value)



def exchange_from_code(stock_code: str) -> Optional[str]:
    """从股票代码后缀推断交易所标识。"""
    upper = (stock_code or "").strip().upper()
    if upper.endswith(".SS"):
        return "SH"
    if upper.endswith((".SH", ".SZ", ".BJ")):
        return upper.rsplit(".", 1)[1]
    if upper.startswith(("SH.", "SS.")):
        return "SH"
    if upper.startswith("SZ."):
        return "SZ"
    if upper.startswith("BJ."):
        return "BJ"
    if upper.startswith("SH"):
        return "SH"
    if upper.startswith("SZ"):
        return "SZ"
    if upper.startswith("BJ"):
        return "BJ"
    return None



def to_tickflow_symbol(stock_code: str, *, use_exchange_from_code) -> Optional[str]:
    """将标准代码转换为 TickFlow 符号格式。"""
    code = normalize_stock_code(stock_code)
    if not (code.isdigit() and len(code) == 6):
        return None

    exchange = use_exchange_from_code(stock_code)
    if not exchange:
        if is_bse_code(code):
            exchange = "BJ"
        elif code.startswith(("6", "5")):
            exchange = "SH"
        elif code.startswith(("0", "1", "2", "3")):
            exchange = "SZ"
        else:
            return None
    return f"{code}.{exchange}"



def get_realtime_cache_ttl() -> int:
    """读取实时报价的缓存 TTL 配置。"""
    try:
        from src.config import get_config

        return int(get_config().realtime_cache_ttl)
    except Exception:
        return 600






def extract_instrument_name(instrument: Any) -> Optional[str]:
    """从 instrument 结构提取证券名称。"""
    if isinstance(instrument, list):
        if not instrument:
            return None
        instrument = instrument[0]
    if not isinstance(instrument, dict):
        return None
    name = (
        instrument.get("name")
        or instrument.get("short_name")
        or instrument.get("display_name")
        or (instrument.get("ext") or {}).get("name")
    )
    return str(name).strip() if name else None



def extract_universe_entries(universe: Any) -> List[Dict[str, str]]:
    """从标的池响应中提取条目列表。"""
    if universe is None:
        return []
    if isinstance(universe, dict):
        raw_symbols = universe.get("symbols") or universe.get("data") or universe.get("items") or []
    else:
        raw_symbols = universe
    entries: List[Dict[str, str]] = []
    for item in raw_symbols:
        name = ""
        if isinstance(item, str):
            symbol = item
        elif isinstance(item, dict):
            symbol = item.get("symbol") or item.get("code") or ""
            ext = item.get("ext") or {}
            name = (
                item.get("name")
                or item.get("short_name")
                or item.get("display_name")
                or ext.get("name")
                or ""
            )
        else:
            symbol = ""
        symbol = str(symbol).strip().upper()
        if symbol:
            entries.append({"symbol": symbol, "name": str(name).strip() if name else ""})
    return entries



def extract_universe_symbols(universe: Any) -> List[str]:
    """从标的池条目提取符号列表。"""
    return [entry["symbol"] for entry in extract_universe_entries(universe)]

