"""市场指数协调与供应商现有取数；原客户端/状态归原宿主维护。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class MarketIndexLookup:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_get_tickflow_fetcher: Callable
    current_fetchers: Callable[[], Any]
    read_logger: Callable[[], Any]

    def get_main_indices(self, region: str = "cn") -> List[Dict[str, Any]]:
        """获取主要指数实时行情（自动切换数据源）"""
        if region == "cn":
            tickflow_fetcher = self.use_get_tickflow_fetcher()
            if tickflow_fetcher is not None:
                try:
                    data = tickflow_fetcher.get_main_indices(region=region)
                    if data:
                        self.read_logger().info("[TickFlowFetcher] 获取指数行情成功")
                        return data
                except Exception as e:
                    self.read_logger().warning(f"[TickFlowFetcher] 获取指数行情失败: {e}")

        for fetcher in self.current_fetchers():
            if region == "cn" and fetcher.name == "TickFlowFetcher":
                continue
            try:
                data = fetcher.get_main_indices(region=region)
                if data:
                    self.read_logger().info(f"[{fetcher.name}] 获取指数行情成功")
                    return data
            except Exception as e:
                self.read_logger().warning(f"[{fetcher.name}] 获取指数行情失败: {e}")
                continue
        return []


@dataclass(frozen=True)
class AkshareIndices:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    call_safe_float: Callable
    read_logger: Callable[[], Any]

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """
        获取主要指数实时行情 (新浪接口)，仅支持 A 股
        """
        if region != "cn":
            return None
        import akshare as ak

        # 主要指数代码映射
        indices_map = {
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "sz399006": "创业板指",
            "sh000688": "科创50",
            "sh000016": "上证50",
            "sh000300": "沪深300",
        }

        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            # 使用 akshare 获取指数行情（新浪财经接口）
            df = ak.stock_zh_index_spot_sina()

            results = []
            if df is not None and not df.empty:
                for code, name in indices_map.items():
                    # 查找对应指数
                    row = df[df["代码"] == code]
                    if row.empty:
                        # 尝试带前缀查找
                        row = df[df["代码"].str.contains(code)]

                    if not row.empty:
                        row = row.iloc[0]
                        current = self.call_safe_float(row.get("最新价", 0))
                        prev_close = self.call_safe_float(row.get("昨收", 0))
                        high = self.call_safe_float(row.get("最高", 0))
                        low = self.call_safe_float(row.get("最低", 0))

                        # 计算振幅
                        amplitude = 0.0
                        if prev_close > 0:
                            amplitude = (high - low) / prev_close * 100

                        results.append(
                            {
                                "code": code,
                                "name": name,
                                "current": current,
                                "change": self.call_safe_float(row.get("涨跌额", 0)),
                                "change_pct": self.call_safe_float(row.get("涨跌幅", 0)),
                                "open": self.call_safe_float(row.get("今开", 0)),
                                "high": high,
                                "low": low,
                                "prev_close": prev_close,
                                "volume": self.call_safe_float(row.get("成交量", 0)),
                                "amount": self.call_safe_float(row.get("成交额", 0)),
                                "amplitude": amplitude,
                            }
                        )
            return results

        except Exception as e:
            self.read_logger().error(f"[Akshare] 获取指数行情失败: {e}")
            return None


@dataclass(frozen=True)
class EfinanceIndices:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    call_ef_call_with_timeout: Callable
    call_safe_float: Callable
    read_logger: Callable[[], Any]

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """
        获取主要指数实时行情 (efinance)，仅支持 A 股
        """
        if region != "cn":
            return None
        import efinance as ef

        indices_map = {
            "000001": ("上证指数", "sh000001"),
            "399001": ("深证成指", "sz399001"),
            "399006": ("创业板指", "sz399006"),
            "000688": ("科创50", "sh000688"),
            "000016": ("上证50", "sh000016"),
            "000300": ("沪深300", "sh000300"),
        }

        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            self.read_logger().info("[API调用] ef.stock.get_realtime_quotes(['沪深系列指数']) 获取指数行情...")
            import time as _time

            api_start = _time.time()
            df = self.call_ef_call_with_timeout(ef.stock.get_realtime_quotes, ["沪深系列指数"])
            api_elapsed = _time.time() - api_start

            if df is None or df.empty:
                self.read_logger().warning(f"[API返回] 指数行情为空, 耗时 {api_elapsed:.2f}s")
                return None

            self.read_logger().info(f"[API返回] 指数行情成功: {len(df)} 条, 耗时 {api_elapsed:.2f}s")
            code_col = "股票代码" if "股票代码" in df.columns else "code"
            code_series = df[code_col].astype(str).str.zfill(6)

            results: List[Dict[str, Any]] = []
            for code, (name, full_code) in indices_map.items():
                row = df[code_series == code]
                if row.empty:
                    continue
                item = row.iloc[0]

                price_col = "最新价" if "最新价" in df.columns else "price"
                pct_col = "涨跌幅" if "涨跌幅" in df.columns else "pct_chg"
                chg_col = "涨跌额" if "涨跌额" in df.columns else "change"
                open_cols = [column for column in ("今开", "开盘", "open") if column in df.columns]
                high_col = "最高" if "最高" in df.columns else "high"
                low_col = "最低" if "最低" in df.columns else "low"
                vol_col = "成交量" if "成交量" in df.columns else "volume"
                amt_col = "成交额" if "成交额" in df.columns else "amount"
                amp_col = "振幅" if "振幅" in df.columns else "amplitude"

                current = self.call_safe_float(item.get(price_col, 0))
                change_amount = self.call_safe_float(item.get(chg_col, 0))
                open_price = 0.0
                for column in open_cols:
                    candidate = self.call_safe_float(item.get(column), default=None)
                    if candidate not in (None, 0.0):
                        open_price = candidate
                        break
                if open_price == 0.0 and open_cols:
                    open_price = self.call_safe_float(item.get(open_cols[0], 0), 0)

                results.append(
                    {
                        "code": full_code,
                        "name": name,
                        "current": current,
                        "change": change_amount,
                        "change_pct": self.call_safe_float(item.get(pct_col, 0)),
                        "open": open_price,
                        "high": self.call_safe_float(item.get(high_col, 0)),
                        "low": self.call_safe_float(item.get(low_col, 0)),
                        "prev_close": current - change_amount if current or change_amount else 0,
                        "volume": self.call_safe_float(item.get(vol_col, 0)),
                        "amount": self.call_safe_float(item.get(amt_col, 0)),
                        "amplitude": self.call_safe_float(item.get(amp_col, 0)),
                    }
                )

            if results:
                self.read_logger().info(f"[efinance] 获取到 {len(results)} 个指数行情")
            return results if results else None
        except Exception as e:
            self.read_logger().error(f"[efinance] 获取指数行情失败: {e}")
            return None


@dataclass(frozen=True)
class TushareIndices:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_check_rate_limit: Callable
    current_api: Callable[[], Any]
    read_logger: Callable[[], Any]
    read_datetime: Callable[[], Any]

    def get_main_indices(self, region: str = "cn") -> Optional[List[dict]]:
        """
        获取主要指数实时行情 (Tushare Pro)，仅支持 A 股
        """
        if region != "cn":
            return None
        if self.current_api() is None:
            return None

        from data_provider.realtime.types import safe_float

        # 指数映射：Tushare代码 -> 名称
        indices_map = {
            "000001.SH": "上证指数",
            "399001.SZ": "深证成指",
            "399006.SZ": "创业板指",
            "000688.SH": "科创50",
            "000016.SH": "上证50",
            "000300.SH": "沪深300",
        }

        try:
            self.use_check_rate_limit()

            # Tushare index_daily 获取历史数据，实时数据需用其他接口或估算
            # 由于 Tushare 免费用户可能无法获取指数实时行情，这里作为备选
            # 使用 index_daily 获取最近交易日数据

            end_date = self.read_datetime().now().strftime("%Y%m%d")
            start_date = (self.read_datetime().now() - pd.Timedelta(days=5)).strftime("%Y%m%d")

            results = []

            # 批量获取所有指数数据
            for ts_code, name in indices_map.items():
                try:
                    df = self.current_api().index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                    if df is not None and not df.empty:
                        row = df.iloc[0]  # 最新一天

                        current = safe_float(row["close"])
                        prev_close = safe_float(row["pre_close"])

                        results.append(
                            {
                                "code": ts_code.split(".")[0],  # 兼容 sh000001 格式需转换，这里保持纯数字
                                "name": name,
                                "current": current,
                                "change": safe_float(row["change"]),
                                "change_pct": safe_float(row["pct_chg"]),
                                "open": safe_float(row["open"]),
                                "high": safe_float(row["high"]),
                                "low": safe_float(row["low"]),
                                "prev_close": prev_close,
                                "volume": safe_float(row["vol"]),
                                "amount": safe_float(row["amount"]) * 1000,  # 千元转元
                                "amplitude": 0.0,  # Tushare index_daily 不直接返回振幅
                            }
                        )
                except Exception as e:
                    self.read_logger().debug(f"Tushare 获取指数 {name} 失败: {e}")
                    continue

            if results:
                return results
            else:
                self.read_logger().warning("[Tushare] 未获取到指数行情数据")

        except Exception as e:
            self.read_logger().error(f"[Tushare] 获取指数行情失败: {e}")

        return None


@dataclass(frozen=True)
class TickflowIndices:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_get_client: Callable
    use_ratio_to_percent: Callable
    use_safe_float: Callable
    read_logger: Callable[[], Any]
    read_cn_main_index_quotes: Callable[[], Any]
    read_max_symbols_per_quote_request: Callable[[], Any]

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """Fetch main A-share indices via TickFlow quotes."""
        if region != "cn":
            return None

        client = self.use_get_client()
        if client is None:
            return None

        symbols = [symbol for symbol, _, _ in self.read_cn_main_index_quotes()]
        quotes: List[Dict[str, Any]] = []
        for offset in range(0, len(symbols), self.read_max_symbols_per_quote_request()):
            batch_symbols = symbols[offset : offset + self.read_max_symbols_per_quote_request()]
            batch_quotes = client.quotes.get(symbols=batch_symbols)
            if batch_quotes:
                quotes.extend(batch_quotes)
        if not quotes:
            self.read_logger().warning("[TickFlowFetcher] empty index quotes")
            return None

        quotes_by_symbol = {str(item.get("symbol", "")).upper(): item for item in quotes if item}
        results: List[Dict[str, Any]] = []

        for symbol, code, name in self.read_cn_main_index_quotes():
            quote = quotes_by_symbol.get(symbol)
            if not quote:
                continue

            ext = quote.get("ext") or {}
            current = self.use_safe_float(quote.get("last_price")) or 0.0
            prev_close = self.use_safe_float(quote.get("prev_close")) or 0.0
            change = self.use_safe_float(ext.get("change_amount"))
            if change is None:
                change = current - prev_close if current or prev_close else 0.0
            amplitude = self.use_ratio_to_percent(ext.get("amplitude"))
            if amplitude is None and prev_close > 0:
                high = self.use_safe_float(quote.get("high")) or 0.0
                low = self.use_safe_float(quote.get("low")) or 0.0
                amplitude = (high - low) / prev_close * 100

            results.append(
                {
                    "code": code,
                    "name": name,
                    "current": current,
                    "change": change,
                    "change_pct": self.use_ratio_to_percent(ext.get("change_pct")) or 0.0,
                    "open": self.use_safe_float(quote.get("open")) or 0.0,
                    "high": self.use_safe_float(quote.get("high")) or 0.0,
                    "low": self.use_safe_float(quote.get("low")) or 0.0,
                    "prev_close": prev_close,
                    "volume": self.use_safe_float(quote.get("volume")) or 0.0,
                    "amount": self.use_safe_float(quote.get("amount")) or 0.0,
                    "amplitude": amplitude or 0.0,
                }
            )

        if len(results) != len(self.read_cn_main_index_quotes()):
            self.read_logger().warning(
                "[TickFlowFetcher] incomplete index quotes: %s/%s",
                len(results),
                len(self.read_cn_main_index_quotes()),
            )
            return None

        return results or None


@dataclass(frozen=True)
class YfinanceIndices:
    """复用原资源与回退入口，不创建另一份 SDK、缓存或重试。"""

    use_fetch_yf_ticker_data: Callable
    use_get_hk_main_indices: Callable
    use_get_jp_main_indices: Callable
    use_get_kr_main_indices: Callable
    use_get_tw_main_indices: Callable
    use_get_us_main_indices: Callable
    call_get_us_index_yf_symbol: Callable
    read_logger: Callable[[], Any]

    def fetch_yf_ticker_data(self, yf, yf_code: str, name: str, return_code: str) -> Optional[Dict[str, Any]]:
        """
        通过 yfinance 拉取单个指数/股票的行情数据。

        Args:
            yf: yfinance 模块引用
            yf_code: yfinance 使用的代码（如 '000001.SS'、'^GSPC'）
            name: 指数显示名称
            return_code: 写入结果 dict 的 code 字段（如 'sh000001'、'SPX'）

        Returns:
            行情字典，失败时返回 None
        """
        ticker = yf.Ticker(yf_code)
        # 取近两日数据以计算涨跌幅
        hist = ticker.history(period="2d")
        if hist.empty:
            return None
        today_row = hist.iloc[-1]
        prev_row = hist.iloc[-2] if len(hist) > 1 else today_row
        price = float(today_row["Close"])
        prev_close = float(prev_row["Close"])
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        high = float(today_row["High"])
        low = float(today_row["Low"])
        # 振幅 = (最高 - 最低) / 昨收 * 100
        amplitude = ((high - low) / prev_close * 100) if prev_close else 0
        return {
            "code": return_code,
            "name": name,
            "current": price,
            "change": change,
            "change_pct": change_pct,
            "open": float(today_row["Open"]),
            "high": high,
            "low": low,
            "prev_close": prev_close,
            "volume": float(today_row["Volume"]),
            "amount": 0.0,  # Yahoo Finance 不提供准确成交额
            "amplitude": amplitude,
        }

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """
        获取主要指数行情 (Yahoo Finance)，支持 A 股、美股、港股、日股、韩股与台股。
        region=us 时委托给 _get_us_main_indices。
        region=hk 时委托给 _get_hk_main_indices。
        region=jp/kr/tw 时分别委托给对应市场指数方法。
        """
        import yfinance as yf

        if region == "us":
            return self.use_get_us_main_indices(yf)
        if region == "hk":
            return self.use_get_hk_main_indices(yf)
        if region == "jp":
            return self.use_get_jp_main_indices(yf)
        if region == "kr":
            return self.use_get_kr_main_indices(yf)
        if region == "tw":
            return self.use_get_tw_main_indices(yf)

        # A 股指数：akshare 代码 -> (yfinance 代码, 显示名称)
        yf_mapping = {
            "sh000001": ("000001.SS", "上证指数"),
            "sz399001": ("399001.SZ", "深证成指"),
            "sz399006": ("399006.SZ", "创业板指"),
            "sh000688": ("000688.SS", "科创50"),
            "sh000016": ("000016.SS", "上证50"),
            "sh000300": ("000300.SS", "沪深300"),
        }

        results = []
        try:
            for ak_code, (yf_code, name) in yf_mapping.items():
                try:
                    item = self.use_fetch_yf_ticker_data(yf, yf_code, name, ak_code)
                    if item:
                        results.append(item)
                        self.read_logger().debug(f"[Yfinance] 获取指数 {name} 成功")
                except Exception as e:
                    self.read_logger().warning(f"[Yfinance] 获取指数 {name} 失败: {e}")

            if results:
                self.read_logger().info(f"[Yfinance] 成功获取 {len(results)} 个 A 股指数行情")
                return results

        except Exception as e:
            self.read_logger().error(f"[Yfinance] 获取 A 股指数行情失败: {e}")

        return None

    def get_us_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """获取美股主要指数行情（SPX、IXIC、DJI、VIX），复用 _fetch_yf_ticker_data"""
        # 大盘复盘所需核心美股指数
        us_indices = ["SPX", "IXIC", "DJI", "VIX"]
        results = []
        try:
            for code in us_indices:
                yf_symbol, name = self.call_get_us_index_yf_symbol(code)
                if not yf_symbol:
                    continue
                try:
                    item = self.use_fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        self.read_logger().debug(f"[Yfinance] 获取美股指数 {name} 成功")
                except Exception as e:
                    self.read_logger().warning(f"[Yfinance] 获取美股指数 {name} 失败: {e}")

            if results:
                self.read_logger().info(f"[Yfinance] 成功获取 {len(results)} 个美股指数行情")
                return results

        except Exception as e:
            self.read_logger().error(f"[Yfinance] 获取美股指数行情失败: {e}")

        return None

    def get_hk_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """获取港股主要指数行情（HSI、HSTECH、HSCEI），复用 _fetch_yf_ticker_data"""
        # Yahoo Finance 港股指数符号映射：
        # - HSI -> ^HSI
        # - HSTECH -> HSTECH.HK（不是 ^HSTECH）
        # - HSCEI -> ^HSCE（不是 ^HSCEI）
        # 该映射由离线单测 tests/test_yfinance_hk_indices.py 固化，避免在线依赖导致非确定性失败。
        hk_indices = {
            "HSI": ("^HSI", "恒生指数"),
            "HSTECH": ("HSTECH.HK", "恒生科技指数"),
            "HSCEI": ("^HSCE", "国企指数"),
        }
        results = []
        try:
            for code, (yf_symbol, name) in hk_indices.items():
                try:
                    item = self.use_fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        self.read_logger().debug(f"[Yfinance] 获取港股指数 {name} 成功")
                except Exception as e:
                    self.read_logger().warning(f"[Yfinance] 获取港股指数 {name} 失败: {e}")

            if results:
                self.read_logger().info(f"[Yfinance] 成功获取 {len(results)} 个港股指数行情")
                return results

        except Exception as e:
            self.read_logger().error(f"[Yfinance] 获取港股指数行情失败: {e}")

        return None

    def get_jp_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """获取日本主要指数行情（日经225、TOPIX），复用 _fetch_yf_ticker_data。"""
        jp_indices = {
            "N225": ("^N225", "日经225"),
            "TOPX": ("^TOPX", "东证指数"),
        }
        results = []
        try:
            for code, (yf_symbol, name) in jp_indices.items():
                try:
                    item = self.use_fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        self.read_logger().debug(f"[Yfinance] 获取日本指数 {name} 成功")
                except Exception as e:
                    self.read_logger().warning(f"[Yfinance] 获取日本指数 {name} 失败: {e}")
            if results:
                self.read_logger().info(f"[Yfinance] 成功获取 {len(results)} 个日本指数行情")
                return results
        except Exception as e:
            self.read_logger().error(f"[Yfinance] 获取日本指数行情失败: {e}")
        return None

    def get_kr_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """获取韩国主要指数行情（KOSPI、KOSDAQ），复用 _fetch_yf_ticker_data。"""
        kr_indices = {
            "KS11": ("^KS11", "KOSPI"),
            "KQ11": ("^KQ11", "KOSDAQ"),
        }
        results = []
        try:
            for code, (yf_symbol, name) in kr_indices.items():
                try:
                    item = self.use_fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        self.read_logger().debug(f"[Yfinance] 获取韩国指数 {name} 成功")
                except Exception as e:
                    self.read_logger().warning(f"[Yfinance] 获取韩国指数 {name} 失败: {e}")
            if results:
                self.read_logger().info(f"[Yfinance] 成功获取 {len(results)} 个韩国指数行情")
                return results
        except Exception as e:
            self.read_logger().error(f"[Yfinance] 获取韩国指数行情失败: {e}")
        return None

    def get_tw_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """获取台湾主要指数行情（加权指数 ^TWII、柜买指数 ^TWOII），复用 _fetch_yf_ticker_data。"""
        tw_indices = {
            "TWII": ("^TWII", "台湾加权指数"),
            "TWOII": ("^TWOII", "台湾柜买指数"),
        }
        results = []
        try:
            for code, (yf_symbol, name) in tw_indices.items():
                try:
                    item = self.use_fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        self.read_logger().debug(f"[Yfinance] 获取台湾指数 {name} 成功")
                except Exception as e:
                    self.read_logger().warning(f"[Yfinance] 获取台湾指数 {name} 失败: {e}")
            if results:
                self.read_logger().info(f"[Yfinance] 成功获取 {len(results)} 个台湾指数行情")
                return results
        except Exception as e:
            self.read_logger().error(f"[Yfinance] 获取台湾指数行情失败: {e}")
        return None


@dataclass(frozen=True)
class EastmoneyCardIndices:
    """卡片辅助仍使用原 sector 模块的 Session、缓存与旧替换入口。"""

    call_fetch_market_indices: Callable
    read_eastmoney_index_url: Callable[[], Any]
    read_eastmoney_index_url_delay: Callable[[], Any]
    read_market_indices: Callable[[], Any]
    read_market_indices_a50: Callable[[], Any]
    read_market_indices_jp_kr: Callable[[], Any]
    read_market_indices_us: Callable[[], Any]
    read_request_timeout: Callable[[], Any]
    read_index_cache: Callable[[], Any]
    read_session: Callable[[], Any]
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def fetch_market_indices(self, market: str = "a") -> Optional[List[Dict]]:
        """获取市场指数数据，主域名失败则回退到 delay 域名。"""
        if market == "us":
            indices_cfg = self.read_market_indices_us()
        elif market == "jp-kr":
            indices_cfg = self.read_market_indices_jp_kr()
        else:
            indices_cfg = self.read_market_indices()
        return self._fetch_by_config(indices_cfg)

    def fetch_a50_index(self) -> Optional[List[Dict]]:
        """获取富时中国 A50 指数（secid 100.XIN9）实时行情。

        该指数跟踪 SGX 富时中国 A50 期货，是 A 股休市时段（SGX 夜盘）
        的领先风向标，独立于 A 股 TAB 主指数批量接口单独取数，
        保证 StockSDK 作为主源胜出时 A50 卡片仍稳定出现。
        """
        return self._fetch_by_config(self.read_market_indices_a50())

    def _fetch_by_config(self, indices_cfg: List[Dict]) -> Optional[List[Dict]]:
        """按给定指数配置批量拉取行情，主域名失败回退 delay 域名。"""
        secids = ",".join(item["secid"] for item in indices_cfg)
        code_name_map = {item["code"]: item["name"] for item in indices_cfg}
        for url in [self.read_eastmoney_index_url(), self.read_eastmoney_index_url_delay()]:
            try:
                resp = self.read_session().get(
                    url,
                    params={
                        "fltt": "2",
                        "fields": "f2,f3,f4,f5,f6,f12,f14,f15,f16,f18",
                        "secids": secids,
                    },
                    timeout=self.read_request_timeout(),
                )
                resp.raise_for_status()
                result = resp.json()
                diff = result.get("data", {}).get("diff", [])
                if result.get("rc") != 0 or not diff:
                    self.read_logger().warning("东方财富指数接口(%s)返回异常：%s", url, result)
                    continue
                indices = []
                for item in diff:
                    amount = item.get("f6", "-")
                    amount_val = amount
                    if amount_val in ("-", "", 0, "0", "0.0", "0.00", None):
                        amount_val = None
                    else:
                        try:
                            amount_val = float(amount_val)
                            if amount_val <= 0:
                                amount_val = None
                        except (TypeError, ValueError):
                            amount_val = None
                    code = item.get("f12", "")
                    indices.append(
                        {
                            "name": code_name_map.get(code, item.get("f14", "")),
                            "code": code,
                            "price": item.get("f2") if item.get("f2") != "-" else None,
                            "changePercent": item.get("f3") if item.get("f3") != "-" else None,
                            "change": item.get("f4") if item.get("f4") != "-" else None,
                            "amount": amount_val,
                            "high": item.get("f15") if item.get("f15") != "-" else None,
                            "low": item.get("f16") if item.get("f16") != "-" else None,
                            "preClose": item.get("f18") if item.get("f18") != "-" else None,
                        }
                    )
                return indices
            except Exception as exc:
                self.read_logger().error("东方财富指数接口(%s)异常：%s", url, exc, exc_info=True)
        return None

    def get_cached_market_indices(self, market: str = "a") -> Optional[List[Dict]]:
        """获取带缓存的市场指数数据。"""
        cache = self.read_index_cache().setdefault(market, {"data": None, "timestamp": 0, "ttl": 60})
        if cache["data"] is None or (self.read_time().time() - cache["timestamp"]) > cache["ttl"]:
            data = self.call_fetch_market_indices(market)
            if data:
                cache["data"] = data
                cache["timestamp"] = self.read_time().time()
        return cache["data"]

    def get_cached_a50_index(self) -> Optional[List[Dict]]:
        """获取带缓存的富时中国 A50 指数行情（缓存键 'a50'）。"""
        cache = self.read_index_cache().setdefault("a50", {"data": None, "timestamp": 0, "ttl": 60})
        if cache["data"] is None or (self.read_time().time() - cache["timestamp"]) > cache["ttl"]:
            data = self.fetch_a50_index()
            if data:
                cache["data"] = data
                cache["timestamp"] = self.read_time().time()
        return cache["data"]


@dataclass(frozen=True)
class StockSdkCardIndices:
    """卡片辅助仍使用原 sector 模块的 Session、缓存与旧替换入口。"""

    call_to_float: Callable
    call_fetch_market_indices: Callable
    call_get_stocksdk_client: Callable
    read_stocksdkbridgeerror: Callable[[], Any]
    read_index_cache: Callable[[], Any]
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def fetch_market_indices(self, market: str = "a") -> Optional[List[Dict]]:
        """获取 StockSDK 市场指数数据。"""
        client = self.call_get_stocksdk_client()
        if not client.is_available():
            return None

        try:
            rows = client.fetch_market_indices(market)
        except self.read_stocksdkbridgeerror() as exc:
            self.read_logger().warning("[StockSDK][sector] market indices failed: market=%s error=%s", market, exc)
            return None

        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("code") or "").strip()
            name = str(row.get("name") or "").strip()
            if not code or not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "code": code,
                    "price": self.call_to_float(row.get("price")),
                    "changePercent": self.call_to_float(row.get("changePercent")),
                    "change": self.call_to_float(row.get("change")),
                    "amount": self.call_to_float(row.get("amount")),
                    "high": self.call_to_float(row.get("high")),
                    "low": self.call_to_float(row.get("low")),
                    "preClose": self.call_to_float(row.get("preClose")),
                }
            )
        return normalized or None

    def get_cached_market_indices(self, market: str = "a") -> Optional[List[Dict]]:
        """获取带缓存的 StockSDK 市场指数数据。"""
        cache = self.read_index_cache().setdefault(market, {"data": None, "timestamp": 0.0, "ttl": 60})
        if cache["data"] is None or (self.read_time().time() - float(cache["timestamp"])) > int(cache["ttl"]):
            data = self.call_fetch_market_indices(market)
            if data:
                cache["data"] = data
                cache["timestamp"] = self.read_time().time()
        return cache["data"]  # type: ignore[return-value]
