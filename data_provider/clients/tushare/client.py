"""tushare 共享协议、连接和配额；无能力选源/回退或第二份资源。"""

from __future__ import annotations

import os
import re
import logging
from data_provider.common.errors import DataFetchError
from src.domain.market.stock_codes import normalize_stock_code, is_bse_code

logger = logging.getLogger("data_provider.tushare_fetcher")

from dataclasses import dataclass
from typing import Callable
from typing import List, Optional
from datetime import datetime
import pandas as pd
from data_provider.clients.tushare.http import _TushareHttpClient


@dataclass(frozen=True)
class TushareClientAccess:
    """窄资源访问契约；状态写回原所有者，兼容旧资源扩展点。"""

    use_build_api_client: Callable
    use_call_api_with_rate_limit: Callable
    use_check_rate_limit: Callable
    use_get_china_now: Callable
    use_get_trade_dates: Callable
    use_pick_trade_date: Callable
    read_api: Callable
    read_call_count: Callable
    read_date_list_end: Callable
    read_minute_start: Callable
    read_date_list: Callable
    read_rate_limit_per_minute: Callable
    write_api: Callable
    write_call_count: Callable
    write_date_list_end: Callable
    write_minute_start: Callable
    write_date_list: Callable
    read_global_DataFetchError: Callable
    read_global_ZoneInfo: Callable
    read_global_TushareHttpClient: Callable
    read_global_resolve_tushare_http_url: Callable
    read_global_datetime: Callable
    read_global_get_config: Callable
    read_global_logger: Callable
    read_global_time: Callable
    read_global_timedelta: Callable

    def _init_api(self) -> None:
        """
        初始化 Tushare API

        如果 Token 未配置，此数据源将不可用。
        这里直接使用内置 HTTP client，避免运行时强依赖 tushare SDK，
        从而减少 Docker / PyInstaller / 多虚拟环境场景下因缺包导致的初始化失败。
        """
        config = self.read_global_get_config()()
        if not config.tushare_token:
            self.read_global_logger().warning("Tushare Token 未配置，此数据源不可用")
            return
        try:
            self.write_api(self.use_build_api_client(config.tushare_token))
            self.read_global_logger().info("Tushare API 初始化成功")
        except Exception as e:
            self.read_global_logger().error(f"Tushare API 初始化失败: {e}")
            self.write_api(None)

    def _build_api_client(self, token: str) -> _TushareHttpClient:
        """
        Build a lightweight Tushare Pro client over direct HTTP requests.

        The project already normalizes all Pro calls through the same request
        contract, so we do not need the official tushare SDK during runtime.

        支持通过 ``TUSHARE_HTTP_URL`` 环境变量将请求指向自建或第三方兼容
        端点，便于在网络无法直达 ``api.tushare.pro`` 时切换镜像/网关。
        留空或不设置则保持官方默认地址，行为与历史版本完全一致。
        """
        api_url = self.read_global_resolve_tushare_http_url()()
        if api_url:
            self.read_global_logger().info("Tushare 使用自定义接入地址: %s", api_url)
            client = self.read_global_TushareHttpClient()(token=token, api_url=api_url)
        else:
            client = self.read_global_TushareHttpClient()(token=token)
        self.read_global_logger().debug(
            "Tushare API client configured for direct HTTP calls"
        )
        return client

    def _check_rate_limit(self) -> None:
        """
        检查并执行速率限制

        流控策略：
        1. 检查是否进入新的一分钟
        2. 如果是，重置计数器
        3. 如果当前分钟调用次数超过限制，强制休眠
        """
        current_time = self.read_global_time().time()
        if self.read_minute_start() is None:
            self.write_minute_start(current_time)
            self.write_call_count(0)
        elif current_time - self.read_minute_start() >= 60:
            self.write_minute_start(current_time)
            self.write_call_count(0)
            self.read_global_logger().debug("速率限制计数器已重置")
        if self.read_call_count() >= self.read_rate_limit_per_minute():
            elapsed = current_time - self.read_minute_start()
            sleep_time = max(0, 60 - elapsed) + 1
            self.read_global_logger().warning(
                f"Tushare 达到速率限制 ({self.read_call_count()}/{self.read_rate_limit_per_minute()} 次/分钟)，等待 {sleep_time:.1f} 秒..."
            )
            self.read_global_time().sleep(sleep_time)
            self.write_minute_start(self.read_global_time().time())
            self.write_call_count(0)
        self.write_call_count(self.read_call_count() + 1)
        self.read_global_logger().debug(
            f"Tushare 当前分钟调用次数: {self.read_call_count()}/{self.read_rate_limit_per_minute()}"
        )

    def _call_api_with_rate_limit(self, method_name: str, **kwargs) -> pd.DataFrame:
        """统一通过速率限制包装 Tushare API 调用。"""
        if self.read_api() is None:
            raise self.read_global_DataFetchError()(
                "Tushare API 未初始化，请检查 Token 配置"
            )
        self.use_check_rate_limit()
        method = getattr(self.read_api(), method_name)
        return method(**kwargs)

    def _get_china_now(self) -> datetime:
        """返回上海时区当前时间，方便测试覆盖跨日刷新逻辑。"""
        return self.read_global_datetime().now(
            self.read_global_ZoneInfo()("Asia/Shanghai")
        )

    def _get_trade_dates(self, end_date: Optional[str] = None) -> List[str]:
        """按自然日刷新交易日历缓存，避免服务跨日后继续复用旧日历。"""
        if self.read_api() is None:
            return []
        china_now = self.use_get_china_now()
        requested_end_date = end_date or china_now.strftime("%Y%m%d")
        if (
            self.read_date_list() is not None
            and self.read_date_list_end() == requested_end_date
        ):
            return self.read_date_list()
        start_date = (china_now - self.read_global_timedelta()(days=20)).strftime(
            "%Y%m%d"
        )
        df_cal = self.use_call_api_with_rate_limit(
            "trade_cal",
            exchange="SSE",
            start_date=start_date,
            end_date=requested_end_date,
        )
        if df_cal is None or df_cal.empty or "cal_date" not in df_cal.columns:
            self.read_global_logger().warning(
                "[Tushare] trade_cal 返回为空，无法更新交易日历缓存"
            )
            self.write_date_list([])
            self.write_date_list_end(requested_end_date)
            return self.read_date_list()
        trade_dates = sorted(
            df_cal[df_cal["is_open"] == 1]["cal_date"].astype(str).tolist(),
            reverse=True,
        )
        self.write_date_list(trade_dates)
        self.write_date_list_end(requested_end_date)
        return trade_dates

    def get_trade_time(self, early_time="09:30", late_time="16:30") -> Optional[str]:
        """
        获取当前时间可以获得数据的开始时间日期

        Args:
                early_time: 默认 '09:30'
                late_time: 默认 '16:30'
                early_time-late_time 之间为使用上一个交易日数据的时间段，其他时间为使用当天数据的时间段
        Returns:
                start_date: 可以获得数据的开始日期
        """
        china_now = self.use_get_china_now()
        china_date = china_now.strftime("%Y%m%d")
        china_clock = china_now.strftime("%H:%M")
        trade_dates = self.use_get_trade_dates(china_date)
        if not trade_dates:
            return None
        if china_date in trade_dates:
            if early_time < china_clock < late_time:
                use_today = False
            else:
                use_today = True
        else:
            use_today = True
        start_date = self.use_pick_trade_date(trade_dates, use_today=use_today)
        if start_date is None:
            return None
        if not use_today:
            self.read_global_logger().info(
                f"[Tushare] 当前时间 {china_clock} 可能无法获取当天筹码分布，尝试获取前一个交易日的数据 {start_date}"
            )
        return start_date


_ETF_SH_PREFIXES = ('51', '52', '56', '58')


_ETF_SZ_PREFIXES = ('15', '16', '18')


_ETF_ALL_PREFIXES = _ETF_SH_PREFIXES + _ETF_SZ_PREFIXES


def _is_etf_code(stock_code: str) -> bool:
    """
    Check if the code is an ETF fund code.

    ETF code ranges:
    - Shanghai ETF: 51xxxx, 52xxxx, 56xxxx, 58xxxx
    - Shenzhen ETF: 15xxxx, 16xxxx, 18xxxx
    """
    code = normalize_stock_code(stock_code)
    return code.startswith(_ETF_ALL_PREFIXES) and len(code) == 6


def _is_us_code(stock_code: str) -> bool:
    """
    判断代码是否为美股
    
    美股代码规则：
    - 1-5个大写字母，如 'AAPL', 'TSLA'
    - 可能包含 '.'，如 'BRK.B'
    """
    code = stock_code.strip().upper()
    return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code))


def pick_trade_date(trade_dates: List[str], use_today: bool) -> Optional[str]:
    """根据可用交易日列表选择当天或前一交易日。"""
    if not trade_dates:
        return None
    if use_today or len(trade_dates) == 1:
        return trade_dates[0]
    return trade_dates[1]


def detect_exchange_hint(stock_code: str) -> Optional[str]:
    """Return SH/SZ/BJ when the raw user input carries an explicit exchange hint."""
    upper = (stock_code or "").strip().upper()
    if upper.startswith(("SH", "SS")) or upper.endswith((".SH", ".SS")):
        return "SH"
    if upper.startswith("SZ") or upper.endswith(".SZ"):
        return "SZ"
    if upper.startswith("BJ") or upper.endswith(".BJ"):
        return "BJ"
    return None


def get_legacy_realtime_symbol(stock_code: str, *, detect_exchange_hint) -> str:
    """Build the legacy tushare symbol while preserving explicit SH/SZ hints."""
    code = normalize_stock_code(stock_code)
    exchange_hint = detect_exchange_hint(stock_code)

    if code == '000001' and exchange_hint == 'SH':
        return 'sh000001'
    if code == '399001':
        return 'sz399001'
    if code == '399006':
        return 'sz399006'
    if code == '000300':
        return 'sh000300'
    if is_bse_code(code):
        return f"bj{code}"
    return code


def convert_stock_code(stock_code: str, *, detect_exchange_hint, is_hk, logger) -> str:
    """
    转换 A 股 / ETF / 北交所等为 Tushare ts_code（不含港股逻辑）。

    Tushare 要求的格式示例：
    - 沪市股票：600519.SH
    - 深市股票：000001.SZ
    - 沪市 ETF：510050.SH
    - 深市 ETF：159919.SZ

    Args:
        stock_code: 原始代码，如 '600519', '000001', '563230'

    Returns:
        Tushare 格式代码，如 '600519.SH', '000001.SZ'
    """
    raw_code = stock_code.strip()

    # Already has suffix.
    if '.' in raw_code:
        upper = raw_code.upper()
        code = normalize_stock_code(raw_code)
        exchange_hint = detect_exchange_hint(raw_code)
        if exchange_hint in ("SH", "SZ", "BJ") and code.isdigit():
            return f"{code}.{exchange_hint}"

        ts_code = upper
        if ts_code.endswith('.SS'):
            return f"{ts_code[:-3]}.SH"
        return ts_code

    if _is_us_code(raw_code):
        raise DataFetchError(f"TushareFetcher 不支持美股 {raw_code}，请使用 AkshareFetcher 或 YfinanceFetcher")

    if is_hk(raw_code):
        #raise DataFetchError(f"TushareFetcher 不支持港股 {raw_code}，请使用 AkshareFetcher")
        return normalize_stock_code(raw_code)

    code = normalize_stock_code(raw_code)
    exchange_hint = detect_exchange_hint(raw_code)

    if exchange_hint == "SH":
        return f"{code}.SH"
    if exchange_hint == "SZ":
        return f"{code}.SZ"
    if exchange_hint == "BJ":
        return f"{code}.BJ"

    # ETF: determine exchange by prefix
    if code.startswith(_ETF_SH_PREFIXES) and len(code) == 6:
        return f"{code}.SH"
    if code.startswith(_ETF_SZ_PREFIXES) and len(code) == 6:
        return f"{code}.SZ"

    # BSE (Beijing Stock Exchange): 8xxxxx, 4xxxxx, 920xxx
    if is_bse_code(code):
        return f"{code}.BJ"

    # Regular stocks
    # Shanghai: 600xxx, 601xxx, 603xxx, 605xxx, 688xxx (STAR Market)
    # Shenzhen: 000xxx, 001xxx, 002xxx, 003xxx, 300xxx, 301xxx (ChiNext)
    if code.startswith(('600', '601', '603', '605', '688')):
        return f"{code}.SH"
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return f"{code}.SZ"
    else:
        logger.warning(f"无法确定股票 {code} 的市场，默认使用深市")
        return f"{code}.SZ"


def convert_hk_stock_code(stock_code: str, *, is_hk, convert_stock_code) -> str:
    """
    将用户输入转为 Tushare Pro 接口所需的 ts_code（含港股 nnnnn.HK）。

    - 非港股：委托 _convert_stock_code（A 股 / ETF / 北交所等）。
    - 港股：从 HK00700、00700、00700.HK 等形式归一为 5 位数字 + .HK。
    """
    raw_code = stock_code.strip()
    if is_hk(raw_code):
        if "." in raw_code:
            ts_code = raw_code.upper()
            if ts_code.endswith(".SS"):
                return f"{ts_code[:-3]}.SH"
            if ts_code.endswith(".HK"):
                return ts_code
        digits = re.sub(r"\D", "", raw_code)
        if not digits:
            raise DataFetchError(f"无法识别港股代码 {raw_code}")
        code = digits[-5:].rjust(5, "0")
        return f"{code}.HK"
    return convert_stock_code(stock_code)
