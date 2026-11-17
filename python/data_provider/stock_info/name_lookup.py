"""名称回退、轻量预取、批量协调及各源精确名称查询；不承担代码搜索或索引持久化。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class StockNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_cache_stock_name: Callable
    use_call_fetcher_method: Callable
    use_ensure_concurrency_guards: Callable
    use_get_cached_stock_name: Callable
    use_get_fetchers_snapshot: Callable
    use_is_fetcher_available: Callable
    use_batch_get_stock_names: Callable
    use_get_realtime_quote: Callable
    use_get_stock_name: Callable
    read_stock_name_cache: Callable[[], Any]
    read_stock_name_cache_lock: Callable[[], Any]
    call_get_index_stock_name: Callable
    call_is_meaningful_stock_name: Callable
    call_normalize_stock_code: Callable
    current_stock_name_map: Callable[[], Any]
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str, allow_realtime: bool = True) -> Optional[str]:
        """
        获取股票中文名称（自动切换数据源）

        尝试从多个数据源获取股票名称：
        1. 先从内存缓存中获取（如果有）
        2. 再尝试本地维护映射与 stocks.index.json 索引
        3. 然后按需查询实时行情
        4. 依次尝试各个数据源的 get_stock_name 方法

        Args:
            stock_code: 股票代码
            allow_realtime: Whether to query realtime quote first. Set False when
                caller only wants lightweight prefetch without triggering heavy
                realtime source calls.

        Returns:
            股票中文名称，所有数据源都失败则返回 None
        """
        raw_stock_code = (stock_code or "").strip()
        # Normalize code (strip SH/SZ prefix etc.)
        stock_code = self.call_normalize_stock_code(stock_code)
        static_name = self.current_stock_name_map().get(stock_code)

        # 1. 先检查缓存
        cached_name = self.use_get_cached_stock_name(stock_code)
        if cached_name is not None:
            return cached_name

        if self.call_is_meaningful_stock_name(static_name, stock_code):
            return self.use_cache_stock_name(stock_code, static_name) or static_name

        index_name = self.call_get_index_stock_name(stock_code)
        if self.call_is_meaningful_stock_name(index_name, stock_code):
            return self.use_cache_stock_name(stock_code, index_name) or index_name

        # 2. 尝试从实时行情中获取（最快，可按需禁用）
        if allow_realtime:
            quote = self.use_get_realtime_quote(raw_stock_code or stock_code, log_final_failure=False)
            if (
                quote
                and hasattr(quote, "name")
                and self.call_is_meaningful_stock_name(getattr(quote, "name", ""), stock_code)
            ):
                name = quote.name
                self.use_cache_stock_name(stock_code, name)
                self.log().info(f"[股票名称] 从实时行情获取: {stock_code} -> {name}")
                return name

        # 3. 依次尝试各个数据源
        from data_provider.runtime.fetchers.akshare import _is_us_code

        is_us = _is_us_code(stock_code)
        _US_CAPABLE_FETCHERS = {"YfinanceFetcher", "LongbridgeFetcher", "FinnhubFetcher", "AlphaVantageFetcher"}
        for fetcher in self.use_get_fetchers_snapshot():
            if not hasattr(fetcher, "get_stock_name"):
                continue
            if is_us and fetcher.name not in _US_CAPABLE_FETCHERS:
                continue
            if not self.use_is_fetcher_available(fetcher, capability="stock_name"):
                continue
            try:
                name = self.use_call_fetcher_method(fetcher, "get_stock_name", stock_code)
                if self.call_is_meaningful_stock_name(name, stock_code):
                    self.use_cache_stock_name(stock_code, name)
                    self.log().info(f"[股票名称] 从 {fetcher.name} 获取: {stock_code} -> {name}")
                    return name
            except Exception as e:
                self.log().debug(f"[股票名称] {fetcher.name} 获取失败: {e}")
                continue

        # 4. 所有数据源都失败
        self.log().warning(f"[股票名称] 所有数据源都无法获取 {stock_code} 的名称")
        return ""

    def prefetch_stock_names(self, stock_codes: List[str], use_bulk: bool = False) -> None:
        """
        Pre-fetch stock names into cache before parallel analysis (Issue #455).

        When use_bulk=False, only calls get_stock_name per code (no get_stock_list),
        avoiding full-market fetch. Sequential execution to avoid rate limits.

        Args:
            stock_codes: Stock codes to prefetch.
            use_bulk: If True, may use get_stock_list (full fetch). Default False.
        """
        if not stock_codes:
            return
        stock_codes = [self.call_normalize_stock_code(c) for c in stock_codes]
        if use_bulk:
            self.use_batch_get_stock_names(stock_codes)
            return
        for code in stock_codes:
            # Skip realtime lookup to avoid triggering expensive full-market quote
            # requests during the prefetch phase.
            self.use_get_stock_name(code, allow_realtime=False)

    def batch_get_stock_names(self, stock_codes: List[str]) -> Dict[str, str]:
        """
        批量获取股票中文名称

        先尝试从支持批量查询的数据源获取股票列表，
        然后再逐个查询缺失的股票名称。

        Args:
            stock_codes: 股票代码列表

        Returns:
            {股票代码: 股票名称} 字典
        """
        result = {}
        missing_codes = set(stock_codes)

        # 1. 先检查缓存
        self.use_ensure_concurrency_guards()
        with self.read_stock_name_cache_lock():
            for code in stock_codes:
                cached_name = self.read_stock_name_cache().get(code)
                if cached_name is not None:
                    result[code] = cached_name
                    missing_codes.discard(code)

        if not missing_codes:
            return result

        # 2. 尝试批量获取股票列表
        for fetcher in self.use_get_fetchers_snapshot():
            if not hasattr(fetcher, "get_stock_list") or not missing_codes:
                continue
            if not self.use_is_fetcher_available(fetcher, capability="stock_list"):
                continue
            try:
                stock_list = self.use_call_fetcher_method(fetcher, "get_stock_list")
                if stock_list is not None and not stock_list.empty:
                    cache_updates: Dict[str, str] = {}
                    for _, row in stock_list.iterrows():
                        code = row.get("code")
                        name = row.get("name")
                        if code and name:
                            cache_updates[code] = name
                            if code in missing_codes:
                                result[code] = name
                                missing_codes.discard(code)

                    if cache_updates:
                        with self.read_stock_name_cache_lock():
                            self.read_stock_name_cache().update(cache_updates)

                    if not missing_codes:
                        break

                    self.log().info(f"[股票名称] 从 {fetcher.name} 批量获取完成，剩余 {len(missing_codes)} 个待查")
            except Exception as e:
                self.log().debug(f"[股票名称] {fetcher.name} 批量获取失败: {e}")
                continue

        # 3. 逐个获取剩余的
        for code in list(missing_codes):
            name = self.use_get_stock_name(code)
            if name:
                result[code] = name
                missing_codes.discard(code)

        self.log().info(f"[股票名称] 批量获取完成，成功 {len(result)}/{len(stock_codes)}")
        return result


@dataclass(frozen=True)
class TushareNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_check_rate_limit: Callable
    use_convert_hk_stock_code_for_tushare: Callable
    use_convert_stock_code: Callable
    read_api: Callable[[], Any]
    read_stock_name_cache: Callable[[], Any]
    write_stock_name_cache: Callable[[Any], None]
    has_stock_name_cache: Callable[[], bool]
    call_is_etf_code: Callable
    call_is_hk_market: Callable
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        获取股票名称

        使用 Tushare 的 stock_basic 接口获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            股票名称，失败返回 None
        """
        if self.read_api() is None:
            self.log().warning("Tushare API 未初始化，无法获取股票名称")
            return None

        # 检查缓存
        if self.has_stock_name_cache() and stock_code in self.read_stock_name_cache():
            return self.read_stock_name_cache()[stock_code]

        # 初始化缓存
        if not self.has_stock_name_cache():
            self.write_stock_name_cache({})

        try:
            # 速率限制检查
            self.use_check_rate_limit()

            # 根据市场/类型选择基础信息接口
            if self.call_is_hk_market(stock_code):
                ts_code = self.use_convert_hk_stock_code_for_tushare(stock_code)
                # 港股：使用 hk_basic
                df = self.read_api().hk_basic(ts_code=ts_code, fields="ts_code,name")
            elif self.call_is_etf_code(stock_code):
                ts_code = self.use_convert_stock_code(stock_code)
                # ETF：使用 fund_basic
                df = self.read_api().fund_basic(ts_code=ts_code, fields="ts_code,name")
            else:
                ts_code = self.use_convert_stock_code(stock_code)
                # A 股股票：使用 stock_basic
                df = self.read_api().stock_basic(ts_code=ts_code, fields="ts_code,name")

            if df is not None and not df.empty:
                name = df.iloc[0]["name"]
                self.read_stock_name_cache()[stock_code] = name
                self.log().debug(f"Tushare 获取股票名称成功: {stock_code} -> {name}")
                return name

        except Exception as e:
            self.log().warning(f"Tushare 获取股票名称失败 {stock_code}: {e}")

        return None


@dataclass(frozen=True)
class PytdxNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_build_stock_list_cache: Callable
    use_get_market_code: Callable
    use_pytdx_session: Callable
    read_stock_list_cache: Callable[[], Any]
    read_stock_name_cache: Callable[[], Any]
    call_is_hk_market: Callable
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        获取股票名称

        Args:
            stock_code: 股票代码

        Returns:
            股票名称，失败返回 None
        """
        # 港股不支持（pytdx 不含港股数据）
        if self.call_is_hk_market(stock_code):
            return None

        # 先检查缓存
        if stock_code in self.read_stock_name_cache():
            return self.read_stock_name_cache()[stock_code]

        try:
            market, code = self.use_get_market_code(stock_code)

            with self.use_pytdx_session() as api:
                # 获取股票列表（缓存）
                if self.read_stock_list_cache() is None:
                    self.use_build_stock_list_cache(api)

                # 查找股票名称
                name = self.read_stock_list_cache().get(code)
                if name:
                    self.read_stock_name_cache()[stock_code] = name
                    return name

                # 尝试使用 get_finance_info
                finance_info = api.get_finance_info(market, code)
                if finance_info and "name" in finance_info:
                    name = finance_info["name"]
                    self.read_stock_name_cache()[stock_code] = name
                    return name

        except Exception as e:
            self.log().debug(f"Pytdx 获取股票名称失败 {stock_code}: {e}")

        return None


@dataclass(frozen=True)
class BaostockNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_baostock_session: Callable
    use_convert_stock_code: Callable
    read_stock_name_cache: Callable[[], Any]
    write_stock_name_cache: Callable[[Any], None]
    has_stock_name_cache: Callable[[], bool]
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        获取股票名称

        使用 Baostock 的 query_stock_basic 接口获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            股票名称，失败返回 None
        """
        # 检查缓存
        if self.has_stock_name_cache() and stock_code in self.read_stock_name_cache():
            return self.read_stock_name_cache()[stock_code]

        # 初始化缓存
        if not self.has_stock_name_cache():
            self.write_stock_name_cache({})

        try:
            bs_code = self.use_convert_stock_code(stock_code)

            with self.use_baostock_session() as bs:
                # 查询股票基本信息
                rs = bs.query_stock_basic(code=bs_code)

                if rs.error_code == "0":
                    data_list = []
                    while rs.next():
                        data_list.append(rs.get_row_data())

                    if data_list:
                        # Baostock 返回的字段：code, code_name, ipoDate, outDate, type, status
                        fields = rs.fields
                        name_idx = fields.index("code_name") if "code_name" in fields else None
                        if name_idx is not None and len(data_list[0]) > name_idx:
                            name = data_list[0][name_idx]
                            self.read_stock_name_cache()[stock_code] = name
                            self.log().debug(f"Baostock 获取股票名称成功: {stock_code} -> {name}")
                            return name

        except Exception as e:
            self.log().warning(f"Baostock 获取股票名称失败 {stock_code}: {e}")

        return None


@dataclass(frozen=True)
class TickflowNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_extract_instrument_name: Callable
    use_extract_name: Callable
    use_get_cached_quote: Callable
    use_get_client: Callable
    use_store_quotes: Callable
    use_to_tickflow_symbol: Callable
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """查询股票名称（优先缓存）。"""
        symbol = self.use_to_tickflow_symbol(stock_code)
        quote = self.use_get_cached_quote(symbol) if symbol else None
        name = self.use_extract_name(quote or {}) if quote else ""
        if name:
            return name

        client = self.use_get_client()
        if client is None or not symbol:
            return None

        try:
            quotes = client.quotes.get(symbols=[symbol])
            self.use_store_quotes(quotes)
            cached = self.use_get_cached_quote(symbol)
            name = self.use_extract_name(cached or {})
            if name:
                return name
        except Exception:
            self.log().debug("[TickFlowFetcher] quote name lookup failed for %s", symbol, exc_info=True)

        try:
            instrument = client.instruments.get(symbol)
            return self.use_extract_instrument_name(instrument)
        except Exception:
            self.log().debug("[TickFlowFetcher] instrument lookup failed for %s", symbol, exc_info=True)
        return None


@dataclass(frozen=True)
class LongbridgeNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_get_static_info: Callable
    call_to_longbridge_symbol: Callable
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """Return stock name from Longbridge static_info (name_cn or name_en)."""
        symbol = self.call_to_longbridge_symbol(stock_code)
        if symbol is None:
            return None
        info = self.use_get_static_info(symbol)
        if info is None:
            return None
        name = getattr(info, "name_cn", "") or getattr(info, "name_en", "") or ""
        return name.strip() or None


@dataclass(frozen=True)
class FinnhubNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_is_us_stock: Callable
    read_api_key: Callable[[], Any]
    current_requests: Callable[[], Any]
    current_finnhub_base_url: Callable[[], Any]
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """查询美股公司名称（profile 接口）；无 key 或非美股返回 None。"""
        if not self.read_api_key() or not self.use_is_us_stock(stock_code):
            return None

        symbol = stock_code.strip().upper()
        try:
            resp = self.current_requests().get(
                f"{self.current_finnhub_base_url()}/search",
                params={"q": symbol, "token": self.read_api_key()},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.log().debug(f"[Finnhub] Symbol search failed for {symbol}: {e}")
            return None

        for item in data.get("result", []):
            if item.get("symbol") == symbol and item.get("description"):
                return item["description"]
        return None


@dataclass(frozen=True)
class AlphaVantageNameLookup:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_is_us_stock: Callable
    read_api_key: Callable[[], Any]
    current_requests: Callable[[], Any]
    current_av_base_url: Callable[[], Any]
    log: Callable[[], Any]

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """获取股票名称。"""
        if not self.read_api_key() or not self.use_is_us_stock(stock_code):
            return None

        symbol = stock_code.strip().upper()
        try:
            resp = self.current_requests().get(
                self.current_av_base_url(),
                params={
                    "function": "SYMBOL_SEARCH",
                    "keywords": symbol,
                    "apikey": self.read_api_key(),
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.log().debug(f"[AlphaVantage] Symbol search failed for {symbol}: {e}")
            return None

        for match in data.get("bestMatches", []):
            if match.get("1. symbol") == symbol and match.get("2. name"):
                return match["2. name"]
        return None
