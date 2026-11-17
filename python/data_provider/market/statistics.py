"""市场统计协调与供应商现有取数；原客户端/状态归原宿主维护。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import pandas as pd


@dataclass(frozen=True)
class MarketStatisticsLookup:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_get_tickflow_fetcher: Callable
    current_fetchers: Callable[[], Any]
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def get_market_stats(self, *, purpose: str = "unspecified") -> Dict[str, Any]:
        """获取市场涨跌统计（自动切换数据源）"""
        self.read_logger().info("[MarketStats] component=market_stats action=start purpose=%s", purpose)
        tickflow_fetcher = self.use_get_tickflow_fetcher()
        if tickflow_fetcher is not None:
            started_at = self.read_time().monotonic()
            try:
                data = tickflow_fetcher.get_market_stats()
                elapsed = self.read_time().monotonic() - started_at
                if data:
                    self.read_logger().info(
                        "[MarketStats] component=market_stats action=provider_success "
                        "purpose=%s provider=TickFlowFetcher elapsed=%.2fs",
                        purpose,
                        elapsed,
                    )
                    return data
                self.read_logger().info(
                    "[MarketStats] component=market_stats action=provider_empty "
                    "purpose=%s provider=TickFlowFetcher elapsed=%.2fs",
                    purpose,
                    elapsed,
                )
            except Exception as e:
                elapsed = self.read_time().monotonic() - started_at
                self.read_logger().warning(
                    "[MarketStats] component=market_stats action=provider_failed "
                    "purpose=%s provider=TickFlowFetcher elapsed=%.2fs error=%s",
                    purpose,
                    elapsed,
                    e,
                )

        for fetcher in self.current_fetchers():
            if fetcher.name == "TickFlowFetcher":
                continue
            started_at = self.read_time().monotonic()
            try:
                data = fetcher.get_market_stats()
                elapsed = self.read_time().monotonic() - started_at
                if data:
                    self.read_logger().info(
                        "[MarketStats] component=market_stats action=provider_success "
                        "purpose=%s provider=%s elapsed=%.2fs",
                        purpose,
                        fetcher.name,
                        elapsed,
                    )
                    return data
                self.read_logger().info(
                    "[MarketStats] component=market_stats action=provider_empty "
                    "purpose=%s provider=%s elapsed=%.2fs",
                    purpose,
                    fetcher.name,
                    elapsed,
                )
            except Exception as e:
                elapsed = self.read_time().monotonic() - started_at
                self.read_logger().warning(
                    "[MarketStats] component=market_stats action=provider_failed "
                    "purpose=%s provider=%s elapsed=%.2fs error=%s",
                    purpose,
                    fetcher.name,
                    elapsed,
                    e,
                )
                continue
        self.read_logger().warning(
            "[MarketStats] component=market_stats action=complete status=empty purpose=%s", purpose
        )
        return {}


@dataclass(frozen=True)
class AkshareStatistics:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_calc_market_stats: Callable
    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """
        获取市场涨跌统计

        数据源优先级：
        1. 东财接口 (ak.stock_zh_a_spot_em)
        2. 新浪接口 (ak.stock_zh_a_spot)
        """
        import akshare as ak

        # 优先东财接口
        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            started_at = self.read_time().monotonic()
            self.read_logger().info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=request_start"
            )
            df = ak.stock_zh_a_spot_em()
            elapsed = self.read_time().monotonic() - started_at
            self.read_logger().info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=request_complete elapsed=%.2fs",
                elapsed,
            )
            if df is not None and not df.empty:
                return self.use_calc_market_stats(df)
            self.read_logger().warning(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=parse status=empty"
            )
        except Exception as e:
            self.read_logger().warning(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=failed error=%s fallback=ak.stock_zh_a_spot",
                e,
            )

        # 东财失败后，尝试新浪接口
        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            started_at = self.read_time().monotonic()
            self.read_logger().info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=request_start"
            )
            df = ak.stock_zh_a_spot()
            elapsed = self.read_time().monotonic() - started_at
            self.read_logger().info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=request_complete elapsed=%.2fs",
                elapsed,
            )
            if df is not None and not df.empty:
                return self.use_calc_market_stats(df)
            self.read_logger().warning(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=parse status=empty"
            )
        except Exception as e:
            self.read_logger().error(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=failed error=%s",
                e,
            )

        return None


@dataclass(frozen=True)
class EfinanceStatistics:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_calc_market_stats: Callable
    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    call_ef_call_with_timeout: Callable
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]
    read_realtime_cache: Callable[[], Any]

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """
        获取市场涨跌统计 (efinance)
        """
        import efinance as ef

        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            current_time = self.read_time().time()
            if (
                self.read_realtime_cache()["data"] is not None
                and current_time - self.read_realtime_cache()["timestamp"] < self.read_realtime_cache()["ttl"]
            ):
                df = self.read_realtime_cache()["data"]
                self.read_logger().info(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=cache_hit cache_age=%.0fs",
                    current_time - self.read_realtime_cache()["timestamp"],
                )
            else:
                started_at = self.read_time().monotonic()
                self.read_logger().info(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=request_start"
                )
                df = self.call_ef_call_with_timeout(ef.stock.get_realtime_quotes)
                elapsed = self.read_time().monotonic() - started_at
                self.read_logger().info(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=request_complete elapsed=%.2fs",
                    elapsed,
                )
                self.read_realtime_cache()["data"] = df
                self.read_realtime_cache()["timestamp"] = current_time

            if df is None or df.empty:
                self.read_logger().warning(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=parse status=empty"
                )
                return None

            return self.use_calc_market_stats(df)
        except Exception as e:
            self.read_logger().error(
                "[MarketStats] component=market_stats provider=EfinanceFetcher "
                "api=ef.stock.get_realtime_quotes action=failed error=%s",
                e,
            )
            return None


@dataclass(frozen=True)
class TushareStatistics:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_calc_market_stats: Callable
    use_call_api_with_rate_limit: Callable
    use_get_china_now: Callable
    use_get_trade_dates: Callable
    use_pick_trade_date: Callable
    current_api: Callable[[], Any]
    read_logger: Callable[[], Any]

    def get_market_stats(self) -> Optional[dict]:
        """
        获取市场涨跌统计 (Tushare Pro)
        2000积分 每天访问该接口 ts.pro_api().rt_k 两次
        接口限制见：https://tushare.pro/document/1?doc_id=108
        """
        if self.current_api() is None:
            return None

        try:
            self.read_logger().info("[Tushare] ts.pro_api() 获取市场统计...")

            # 获取当前中国时间，判断是否在交易时间内
            china_now = self.use_get_china_now()
            current_clock = china_now.strftime("%H:%M")
            current_date = china_now.strftime("%Y%m%d")

            trade_dates = self.use_get_trade_dates(current_date)
            if not trade_dates:
                return None

            if current_date in trade_dates:
                if current_clock < "09:30" or current_clock > "16:30":
                    use_realtime = False
                else:
                    use_realtime = True
            else:
                use_realtime = False

            # 若实盘的时候使用 则使用其他可以实盘获取的数据源 akshare、efinance
            if use_realtime:
                try:
                    df = self.use_call_api_with_rate_limit("rt_k", ts_code="3*.SZ,6*.SH,0*.SZ,92*.BJ")
                    if df is not None and not df.empty:
                        return self.use_calc_market_stats(df)

                except Exception as e:
                    self.read_logger().error(f"[Tushare] ts.pro_api().rt_k 尝试获取实时数据失败: {e}")
                    return None
            else:

                if current_date not in trade_dates:
                    last_date = self.use_pick_trade_date(trade_dates, use_today=True)  # 拿最近的日期
                else:
                    if current_clock < "09:30":
                        last_date = self.use_pick_trade_date(trade_dates, use_today=False)  # 拿取前一天的数据
                    else:  # 即 '> 16:30'
                        last_date = self.use_pick_trade_date(trade_dates, use_today=True)  # 拿取当天的数据

                if last_date is None:
                    return None

                try:
                    df = self.use_call_api_with_rate_limit(
                        "daily",
                        ts_code="3*.SZ,6*.SH,0*.SZ,92*.BJ",
                        start_date=last_date,
                        end_date=last_date,
                    )
                    # 为防止不同接口返回的列名大小写不一致（例如 rt_k 返回小写，daily 返回大写），统一将列名转为小写
                    df.columns = [col.lower() for col in df.columns]

                    # 获取股票基础信息（包含代码和名称）
                    df_basic = self.use_call_api_with_rate_limit("stock_basic", fields="ts_code,name")
                    df = pd.merge(df, df_basic, on="ts_code", how="left")
                    # 将 daily的 amount 列的值乘以 1000 来和其他数据源保持一致
                    if "amount" in df.columns:
                        df["amount"] = df["amount"] * 1000

                    if df is not None and not df.empty:
                        return self.use_calc_market_stats(df)
                except Exception as e:
                    self.read_logger().error(f"[Tushare] ts.pro_api().daily 获取数据失败: {e}")

        except Exception as e:
            self.read_logger().error(f"[Tushare] 获取市场统计失败: {e}")

        return None


@dataclass(frozen=True)
class TickflowStatistics:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_capability_available: Callable
    use_extract_name: Callable
    use_get_client: Callable
    use_get_limit_ratio: Callable
    use_is_cn_equity_symbol: Callable
    use_is_universe_permission_error: Callable
    use_mark_capability: Callable
    use_round_limit_price: Callable
    use_safe_float: Callable
    call_normalize_stock_code: Callable
    read_logger: Callable[[], Any]
    read_math: Callable[[], Any]
    read_cn_universe_id: Callable[[], Any]

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """Calculate A-share market breadth from TickFlow universe quotes."""
        client = self.use_get_client()
        if client is None:
            return None

        if not self.use_capability_available("universe_quotes"):
            return None

        try:
            quotes = client.quotes.get(universes=[self.read_cn_universe_id()])
            self.use_mark_capability("universe_quotes", True)
        except Exception as exc:
            if self.use_is_universe_permission_error(exc):
                self.use_mark_capability("universe_quotes", False)
                self.read_logger().info(
                    "[TickFlowFetcher] universe quotes are not available; fallback to existing market stats sources"
                )
                return None
            raise
        if not quotes:
            self.read_logger().warning("[TickFlowFetcher] empty market stats quotes")
            return None

        stats = {
            "up_count": 0,
            "down_count": 0,
            "flat_count": 0,
            "limit_up_count": 0,
            "limit_down_count": 0,
            "total_amount": 0.0,
        }
        valid_rows = 0

        for quote in quotes:
            if not quote:
                continue

            symbol = str(quote.get("symbol") or "").strip().upper()
            if not self.use_is_cn_equity_symbol(symbol):
                continue

            amount = self.use_safe_float(quote.get("amount"))
            if amount is not None and amount > 0:
                stats["total_amount"] += amount / 1e8

            pure_code = self.call_normalize_stock_code(symbol)
            last_price = self.use_safe_float(quote.get("last_price"))
            prev_close = self.use_safe_float(quote.get("prev_close"))

            if last_price is None or prev_close is None or amount is None or amount <= 0:
                continue

            name = self.use_extract_name(quote)
            ratio = self.use_get_limit_ratio(pure_code, name)
            limit_up = self.use_round_limit_price(prev_close, ratio)
            limit_down = self.read_math().floor(prev_close * (1 - ratio) * 100 + 0.5) / 100.0
            limit_up_tolerance = round(abs(prev_close * (1 + ratio) - limit_up), 10)
            limit_down_tolerance = round(abs(prev_close * (1 - ratio) - limit_down), 10)

            valid_rows += 1

            if abs(last_price - limit_up) <= limit_up_tolerance:
                stats["limit_up_count"] += 1
            if abs(last_price - limit_down) <= limit_down_tolerance:
                stats["limit_down_count"] += 1

            if last_price > prev_close:
                stats["up_count"] += 1
            elif last_price < prev_close:
                stats["down_count"] += 1
            else:
                stats["flat_count"] += 1

        if valid_rows == 0:
            self.read_logger().warning("[TickFlowFetcher] no valid A-share rows for market stats")
            return None

        return stats


def calculate_market_stats(
    df: pd.DataFrame, *, normalize: Callable, is_bse: Callable, is_kc_cy: Callable, is_st: Callable
) -> Optional[Dict[str, Any]]:
    """从行情 DataFrame 计算涨跌统计。"""
    import numpy as np

    df = df.copy()

    # 1. 提取基础比对数据：最新价、昨收
    # 兼容不同接口返回的列名 sina/em efinance tushare xtdata
    code_col = next((c for c in ["代码", "股票代码", "ts_code", "stock_code"] if c in df.columns), None)
    name_col = next((c for c in ["名称", "股票名称", "name", "name"] if c in df.columns), None)
    close_col = next((c for c in ["最新价", "最新价", "close", "lastPrice"] if c in df.columns), None)
    pre_close_col = next((c for c in ["昨收", "昨日收盘", "pre_close", "lastClose"] if c in df.columns), None)
    amount_col = next((c for c in ["成交额", "成交额", "amount", "amount"] if c in df.columns), None)

    limit_up_count = 0
    limit_down_count = 0
    up_count = 0
    down_count = 0
    flat_count = 0

    for code, name, current_price, pre_close, amount in zip(
        df[code_col], df[name_col], df[close_col], df[pre_close_col], df[amount_col]
    ):

        # 停牌过滤 efinance 的停牌数据有时候会缺失价格显示为 '-'，em 显示为none
        if pd.isna(current_price) or pd.isna(pre_close) or current_price in ["-"] or pre_close in ["-"] or amount == 0:
            continue

        # em、efinance 为str 需要转换为float
        current_price = float(current_price)
        pre_close = float(pre_close)

        # 获取去除前缀的纯数字代码
        pure_code = normalize(str(code))

        # A. 确定每只股票的涨跌幅比例 (使用纯数字代码判断)
        if is_bse(pure_code):
            ratio = 0.30
        elif is_kc_cy(pure_code):  # pure_code.startswith(('688', '30')):
            ratio = 0.20
        elif is_st(name):  #'ST' in str_name:
            ratio = 0.05
        else:
            ratio = 0.10

        # B. 严格按照 A 股规则计算涨跌停价：昨收 * (1 ± 比例) -> 四舍五入保留2位小数
        limit_up_price = np.floor(pre_close * (1 + ratio) * 100 + 0.5) / 100.0
        limit_down_price = np.floor(pre_close * (1 - ratio) * 100 + 0.5) / 100.0

        limit_up_price_Tolerance = round(abs(pre_close * (1 + ratio) - limit_up_price), 10)
        limit_down_price_Tolerance = round(abs(pre_close * (1 - ratio) - limit_down_price), 10)

        # C. 精确比对
        if current_price > 0:
            is_limit_up = (current_price > 0) and (abs(current_price - limit_up_price) <= limit_up_price_Tolerance)
            is_limit_down = (current_price > 0) and (
                abs(current_price - limit_down_price) <= limit_down_price_Tolerance
            )

            if is_limit_up:
                limit_up_count += 1
            if is_limit_down:
                limit_down_count += 1

            if current_price > pre_close:
                up_count += 1
            elif current_price < pre_close:
                down_count += 1
            else:
                flat_count += 1

    # 统计数量
    stats = {
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": flat_count,
        "limit_up_count": limit_up_count,
        "limit_down_count": limit_down_count,
        "total_amount": 0.0,
    }

    # 成交额统计
    if amount_col and amount_col in df.columns:
        df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")
        stats["total_amount"] = df[amount_col].sum() / 1e8

    return stats


@dataclass(frozen=True)
class EastmoneyCardStatistics:
    """卡片辅助仍使用原 sector 模块的 Session、缓存与旧替换入口。"""

    call_get_limit_ratio: Callable
    call_fetch_market_fund_flow: Callable
    call_fetch_market_overview: Callable
    call_fetch_northbound_flow: Callable
    read_a_share_filter: Callable[[], Any]
    read_eastmoney_fflow_daykline_url: Callable[[], Any]
    read_eastmoney_index_url: Callable[[], Any]
    read_eastmoney_index_url_delay: Callable[[], Any]
    read_eastmoney_market_url: Callable[[], Any]
    read_eastmoney_northbound_url: Callable[[], Any]
    read_request_timeout: Callable[[], Any]
    read_flow_cache: Callable[[], Any]
    read_overview_cache: Callable[[], Any]
    read_session: Callable[[], Any]
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def fetch_market_overview(self) -> Optional[Dict]:
        """获取全市场涨跌家数、涨跌停与成交额概览。"""
        try:
            all_stocks = []
            for page in range(1, 60):
                resp = self.read_session().get(
                    self.read_eastmoney_market_url(),
                    params={
                        "pn": str(page),
                        "pz": "100",
                        "po": "1",
                        "np": "1",
                        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                        "fltt": "2",
                        "invt": "2",
                        "fid": "f3",
                        "fs": self.read_a_share_filter(),
                        "fields": "f2,f3,f5,f6,f10,f12,f14,f17",
                    },
                    timeout=self.read_request_timeout(),
                )
                resp.raise_for_status()
                diff = resp.json().get("data", {}).get("diff", [])
                if not diff:
                    break
                all_stocks.extend(diff)
            if not all_stocks:
                self.read_logger().warning("东方财富全市场接口返回空数据")
                return None
            rise_count = 0
            fall_count = 0
            flat_count = 0
            limit_up_count = 0
            limit_down_count = 0
            total_amount = 0.0
            weighted_volume_ratio_sum = 0.0
            total_amount_for_ratio = 0.0
            for stock in all_stocks:
                change_pct = stock.get("f3")
                if change_pct in (None, "-"):
                    continue
                try:
                    change_pct = float(change_pct)
                except (TypeError, ValueError):
                    continue
                if change_pct > 0:
                    rise_count += 1
                elif change_pct < 0:
                    fall_count += 1
                else:
                    flat_count += 1
                limit_ratio = self.call_get_limit_ratio(str(stock.get("f12", "")), str(stock.get("f14", "")))
                if change_pct >= limit_ratio - 0.1:
                    limit_up_count += 1
                elif change_pct <= -(limit_ratio - 0.1):
                    limit_down_count += 1
                amount = stock.get("f6")
                if amount in (None, "-"):
                    continue
                try:
                    amount_val = float(amount)
                except (TypeError, ValueError):
                    continue
                total_amount += amount_val
                volume_ratio = stock.get("f10")
                if volume_ratio in (None, "-"):
                    continue
                try:
                    vr = float(volume_ratio)
                except (TypeError, ValueError):
                    continue
                weighted_volume_ratio_sum += vr * amount_val
                total_amount_for_ratio += amount_val
            volume_ratio = None
            if total_amount_for_ratio > 0:
                volume_ratio = round(weighted_volume_ratio_sum / total_amount_for_ratio, 2)
            return {
                "riseCount": rise_count,
                "fallCount": fall_count,
                "flatCount": flat_count,
                "totalAmount": total_amount,
                "volumeRatio": volume_ratio,
                "limitUpCount": limit_up_count,
                "limitDownCount": limit_down_count,
            }
        except Exception as exc:
            self.read_logger().error("东方财富全市场接口异常：%s", exc, exc_info=True)
            return None

    def get_cached_market_overview(self) -> Optional[Dict]:
        """获取带缓存的市场概览。"""
        if (
            self.read_overview_cache()["data"] is None
            or (self.read_time().time() - self.read_overview_cache()["timestamp"]) > self.read_overview_cache()["ttl"]
        ):
            data = self.call_fetch_market_overview()
            if data:
                self.read_overview_cache()["data"] = data
                self.read_overview_cache()["timestamp"] = self.read_time().time()
        return self.read_overview_cache()["data"]

    def fetch_northbound_flow(self) -> Optional[Dict]:
        """获取北向资金净流入。"""
        try:
            resp = self.read_session().get(
                self.read_eastmoney_northbound_url(),
                params={"fields1": "f1,f2,f3,f4", "fields2": "f51,f52,f53,f54,f55,f56"},
                timeout=self.read_request_timeout(),
            )
            resp.raise_for_status()
            data = resp.json().get("data") or {}
            net_inflow_wan = 0.0
            found = False
            for item_key in ("hk2sh", "hk2sz"):
                raw = (data.get(item_key) or {}).get("dayNetAmtIn")
                if raw in (None, "-"):
                    continue
                try:
                    net_inflow_wan += float(raw)
                    found = True
                except (TypeError, ValueError):
                    continue
            if not found or net_inflow_wan == 0:
                self.read_logger().warning("北向资金接口返回空数据（2024-08 后可能停披露）")
                return {"netInflow": None, "name": "北向资金", "date": None}
            return {
                "netInflow": round(net_inflow_wan * 1e4, 2),
                "name": "北向资金",
                "date": (data.get("hk2sh") or {}).get("date2"),
            }
        except Exception as exc:
            self.read_logger().error("北向资金接口异常：%s", exc, exc_info=True)
            return None

    def get_cached_northbound_flow(self) -> Optional[Dict]:
        """获取带缓存的北向资金数据。"""
        if (
            self.read_flow_cache()["northbound"] is None
            or (self.read_time().time() - self.read_flow_cache()["timestamp"]) > self.read_flow_cache()["ttl"]
        ):
            data = self.call_fetch_northbound_flow()
            if data:
                self.read_flow_cache()["northbound"] = data
                self.read_flow_cache()["timestamp"] = self.read_time().time()
        return self.read_flow_cache()["northbound"]

    def fetch_market_fund_flow(self) -> Optional[Dict]:
        """获取大盘主力资金净流入。"""
        try:
            resp = self.read_session().get(
                self.read_eastmoney_fflow_daykline_url(),
                params={
                    "lmt": "1",
                    "klt": "101",
                    "secid": "1.000001",
                    "fields1": "f1,f2,f3,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
                },
                timeout=self.read_request_timeout(),
            )
            resp.raise_for_status()
            klines = resp.json().get("data", {}).get("klines") or []
            if klines:
                items = klines[-1].split(",")
                net_inflow = float(items[1]) if items[1] not in ("", "-") else None
                percent = float(items[6]) if items[6] not in ("", "-") else None
                return {
                    "mainNetInflow": round(net_inflow, 2) if net_inflow is not None else None,
                    "mainNetInflowPercent": round(percent, 2) if percent is not None else None,
                    "date": items[0] or None,
                }
            self.read_logger().warning("大盘资金流日线接口返回空数据")
        except Exception as exc:
            self.read_logger().error("大盘资金流日线接口异常：%s", exc, exc_info=True)
        for url in [self.read_eastmoney_index_url(), self.read_eastmoney_index_url_delay()]:
            try:
                resp = self.read_session().get(
                    url,
                    params={"fltt": "2", "fields": "f2,f3,f12,f14,f62", "secids": "1.000001,0.399001"},
                    timeout=self.read_request_timeout(),
                )
                resp.raise_for_status()
                diff = resp.json().get("data", {}).get("diff", [])
                if not diff:
                    continue
                net_inflow = 0.0
                for item in diff:
                    raw_flow = item.get("f62", "-")
                    if raw_flow in (None, "-"):
                        continue
                    try:
                        net_inflow += float(raw_flow)
                    except (TypeError, ValueError):
                        continue
                return {
                    "mainNetInflow": round(net_inflow, 2) if net_inflow else None,
                    "mainNetInflowPercent": None,
                    "date": None,
                }
            except Exception as exc:
                self.read_logger().error("东方财富主力资金接口(%s)异常：%s", url, exc, exc_info=True)
        return None

    def get_cached_market_fund_flow(self) -> Optional[Dict]:
        """获取带缓存的大盘主力资金数据。"""
        if (
            self.read_flow_cache()["market_fund_flow"] is None
            or (self.read_time().time() - self.read_flow_cache()["timestamp"]) > self.read_flow_cache()["ttl"]
        ):
            data = self.call_fetch_market_fund_flow()
            if data:
                self.read_flow_cache()["market_fund_flow"] = data
                self.read_flow_cache()["timestamp"] = self.read_time().time()
        return self.read_flow_cache()["market_fund_flow"]


@dataclass(frozen=True)
class StockSdkCardStatistics:
    """卡片辅助仍使用原 sector 模块的 Session、缓存与旧替换入口。"""

    call_to_float: Callable
    call_to_int: Callable
    call_fetch_market_fund_flow: Callable
    call_fetch_market_overview: Callable
    call_fetch_northbound_flow: Callable
    call_get_stocksdk_client: Callable
    read_stocksdkbridgeerror: Callable[[], Any]
    read_flow_cache: Callable[[], Any]
    read_overview_cache: Callable[[], Any]
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def fetch_market_overview(self) -> Optional[Dict]:
        """获取 StockSDK A 股市场概览。"""
        client = self.call_get_stocksdk_client()
        if not client.is_available():
            return None
        try:
            data = client.fetch_market_overview()
        except self.read_stocksdkbridgeerror() as exc:
            self.read_logger().warning("[StockSDK][sector] market overview failed: %s", exc)
            return None
        if not isinstance(data, dict):
            return None
        return {
            "riseCount": int(self.call_to_float(data.get("riseCount")) or 0),
            "fallCount": int(self.call_to_float(data.get("fallCount")) or 0),
            "flatCount": int(self.call_to_float(data.get("flatCount")) or 0),
            "totalAmount": self.call_to_float(data.get("totalAmount")) or 0.0,
            "volumeRatio": self.call_to_float(data.get("volumeRatio")),
            "limitUpCount": int(self.call_to_float(data.get("limitUpCount")) or 0),
            "limitDownCount": int(self.call_to_float(data.get("limitDownCount")) or 0),
        }

    def get_cached_market_overview(self) -> Optional[Dict]:
        """获取带缓存的 StockSDK 市场概览。"""
        if self.read_overview_cache()["data"] is None or (
            self.read_time().time() - float(self.read_overview_cache()["timestamp"])
        ) > int(self.read_overview_cache()["ttl"]):
            data = self.call_fetch_market_overview()
            if data:
                self.read_overview_cache()["data"] = data
                self.read_overview_cache()["timestamp"] = self.read_time().time()
        return self.read_overview_cache()["data"]  # type: ignore[return-value]

    def fetch_northbound_flow(self) -> Optional[Dict]:
        """获取 StockSDK 北向资金汇总。"""
        client = self.call_get_stocksdk_client()
        if not client.is_available():
            return None
        try:
            data = client.fetch_northbound_summary()
        except self.read_stocksdkbridgeerror() as exc:
            self.read_logger().warning("[StockSDK][sector] northbound failed: %s", exc)
            return None
        if not isinstance(data, dict):
            return None
        return {
            "netInflow": self.call_to_float(data.get("netInflow")),
            "name": str(data.get("name") or "北向资金"),
            "date": str(data.get("date") or "").strip() or None,
            "riseCount": self.call_to_int(data.get("riseCount")),
            "fallCount": self.call_to_int(data.get("fallCount")),
        }

    def get_cached_northbound_flow(self) -> Optional[Dict]:
        """获取带缓存的 StockSDK 北向资金数据。"""
        if self.read_flow_cache()["northbound"] is None or (
            self.read_time().time() - float(self.read_flow_cache()["timestamp"])
        ) > int(self.read_flow_cache()["ttl"]):
            data = self.call_fetch_northbound_flow()
            if data:
                self.read_flow_cache()["northbound"] = data
                self.read_flow_cache()["timestamp"] = self.read_time().time()
        return self.read_flow_cache()["northbound"]  # type: ignore[return-value]

    def fetch_market_fund_flow(self) -> Optional[Dict]:
        """获取 StockSDK 大盘主力资金。"""
        client = self.call_get_stocksdk_client()
        if not client.is_available():
            return None
        try:
            data = client.fetch_market_fund_flow()
        except self.read_stocksdkbridgeerror() as exc:
            self.read_logger().warning("[StockSDK][sector] market fund flow failed: %s", exc)
            return None
        if not isinstance(data, dict):
            return None
        return {
            "mainNetInflow": self.call_to_float(data.get("mainNetInflow")),
            "mainNetInflowPercent": self.call_to_float(data.get("mainNetInflowPercent")),
            "date": str(data.get("date") or "").strip() or None,
        }

    def get_cached_market_fund_flow(self) -> Optional[Dict]:
        """获取带缓存的 StockSDK 大盘主力资金。"""
        if self.read_flow_cache()["market_fund_flow"] is None or (
            self.read_time().time() - float(self.read_flow_cache()["timestamp"])
        ) > int(self.read_flow_cache()["ttl"]):
            data = self.call_fetch_market_fund_flow()
            if data:
                self.read_flow_cache()["market_fund_flow"] = data
                self.read_flow_cache()["timestamp"] = self.read_time().time()
        return self.read_flow_cache()["market_fund_flow"]  # type: ignore[return-value]
