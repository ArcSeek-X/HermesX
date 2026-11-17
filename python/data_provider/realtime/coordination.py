"""实时能力选源与回退的唯一实现，保留原资源/配置/诊断。"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RealtimeCoordination:
    """只接受窄回调；无第二份缓存、锁、配额或默认 Manager。"""

    use_call_fetcher_method: Callable
    use_enrich_realtime_quote: Callable
    use_get_fetcher_by_name: Callable
    use_longbridge_preferred: Callable
    use_merge_quote_fields: Callable
    use_quote_needs_supplement: Callable
    use_realtime_fetcher_token: Callable
    use_supplement_quote: Callable
    use_try_fetcher_quote: Callable
    global_List: Callable
    global_Optional: Callable
    global_is_hk_market: Callable
    global_is_jp_market: Callable
    global_is_kr_market: Callable
    global_is_tw_market: Callable
    global_logger: Callable
    global_normalize_stock_code: Callable
    global_record_provider_run: Callable
    global_record_provider_run_started: Callable
    global_summarize_exception: Callable
    global_time: Callable

    def get_realtime_quote(self, stock_code: str, *, log_final_failure: bool = True):
        """
        获取实时行情数据（自动故障切换）

        故障切换策略（按配置的优先级）：
        1. 美股：使用 YfinanceFetcher.get_realtime_quote()
        2. EfinanceFetcher.get_realtime_quote()
        3. AkshareFetcher.get_realtime_quote(source="em")  - 东财
        4. AkshareFetcher.get_realtime_quote(source="sina") - 新浪
        5. AkshareFetcher.get_realtime_quote(source="tencent") - 腾讯
        6. 返回 None（降级兜底）

        Args:
            stock_code: 股票代码
            log_final_failure: Whether to emit the final "all sources failed"
                summary log when no realtime quote is available.

        Returns:
            UnifiedRealtimeQuote 对象，所有数据源都失败则返回 None
        """
        raw_stock_code = (stock_code or "").strip()
        stock_code = self.global_normalize_stock_code()(stock_code)
        from data_provider.runtime.fetchers.akshare import _is_us_code
        from src.domain.market.us_index_symbols import is_us_index_code
        from src.config import get_config

        config = get_config()
        if not config.enable_realtime_quote:
            self.global_logger().debug(f"[实时行情] 功能已禁用，跳过 {stock_code}")
            return None
        is_us_index = is_us_index_code(stock_code)
        is_us = is_us_index or _is_us_code(stock_code)
        is_hk = not is_us and self.global_is_hk_market()(stock_code)
        is_jp = not is_us and (not is_hk) and self.global_is_jp_market()(stock_code)
        is_kr = not is_us and (not is_hk) and self.global_is_kr_market()(stock_code)
        is_tw = not is_us and (not is_hk) and self.global_is_tw_market()(stock_code)
        if is_jp or is_kr or is_tw:
            market_label = "日股" if is_jp else "韩股" if is_kr else "台股"
            quote = self.use_try_fetcher_quote(stock_code, "YfinanceFetcher")
            if quote is not None:
                self.global_logger().info(f"[实时行情] {market_label} {stock_code} 成功获取 (来源: YfinanceFetcher)")
                return self.use_enrich_realtime_quote(
                    quote, realtime_cache_ttl=getattr(config, "realtime_cache_ttl", None)
                )
            if log_final_failure:
                self.global_logger().info(f"[实时行情] {market_label} {stock_code} 无可用数据源")
            return None
        if is_us or is_hk:
            prefer_lb = self.use_longbridge_preferred() and (not is_us_index)
            if is_us:
                primary_src = "LongbridgeFetcher" if prefer_lb else "YfinanceFetcher"
                secondary_src = "YfinanceFetcher" if prefer_lb else "LongbridgeFetcher"
                market_label = "美股指数" if is_us_index else "美股"
                primary_kw: dict = {}
                secondary_kw: dict = {}
            else:
                primary_src = "LongbridgeFetcher" if prefer_lb else "AkshareFetcher"
                secondary_src = "AkshareFetcher" if prefer_lb else "LongbridgeFetcher"
                market_label = "港股"
                primary_kw = {"source": "hk"} if primary_src == "AkshareFetcher" else {}
                secondary_kw = {"source": "hk"} if secondary_src == "AkshareFetcher" else {}
            primary_token = self.use_realtime_fetcher_token(primary_src, **primary_kw)
            primary_quote = self.use_try_fetcher_quote(stock_code, primary_src, **primary_kw)
            fallback_from = primary_token if primary_quote is None else None
            if primary_quote is not None:
                self.global_logger().info(f"[实时行情] {market_label} {stock_code} 成功获取 (来源: {primary_src})")
            primary_quote = self.use_supplement_quote(stock_code, primary_quote, secondary_src, **secondary_kw)
            if is_us and (not is_us_index) and (primary_quote is not None):
                for extra_src in ["FinnhubFetcher", "AlphaVantageFetcher"]:
                    primary_quote = self.use_supplement_quote(stock_code, primary_quote, extra_src)
            if primary_quote is not None:
                return self.use_enrich_realtime_quote(
                    primary_quote,
                    fallback_from=fallback_from,
                    realtime_cache_ttl=getattr(config, "realtime_cache_ttl", None),
                )
            if log_final_failure:
                self.global_logger().info(f"[实时行情] {market_label} {stock_code} 无可用数据源")
            return None
        source_priority = [
            source.strip().lower() for source in config.realtime_source_priority.split(",") if source.strip()
        ]
        errors = []
        failed_sources: self.global_List()[str] = []
        primary_quote = None
        primary_fallback_from: self.global_Optional()[str] = None
        for source_index, source in enumerate(source_priority):
            attempt_start = self.global_time().time()
            fallback_to = source_priority[source_index + 1] if source_index + 1 < len(source_priority) else None
            fetcher = None
            try:
                quote = None
                if source == "efinance":
                    fetcher = self.use_get_fetcher_by_name("EfinanceFetcher", capability="realtime_quote")
                    if fetcher is not None and hasattr(fetcher, "get_realtime_quote"):
                        self.global_record_provider_run_started()(
                            data_type="realtime_quote", provider=fetcher.name, operation="get_realtime_quote"
                        )
                        quote = self.use_call_fetcher_method(fetcher, "get_realtime_quote", stock_code)
                elif source == "akshare_em":
                    fetcher = self.use_get_fetcher_by_name("AkshareFetcher", capability="realtime_quote")
                    if fetcher is not None and hasattr(fetcher, "get_realtime_quote"):
                        self.global_record_provider_run_started()(
                            data_type="realtime_quote", provider=fetcher.name, operation="get_realtime_quote"
                        )
                        quote = self.use_call_fetcher_method(fetcher, "get_realtime_quote", stock_code, source="em")
                elif source == "akshare_sina":
                    fetcher = self.use_get_fetcher_by_name("AkshareFetcher", capability="realtime_quote")
                    if fetcher is not None and hasattr(fetcher, "get_realtime_quote"):
                        self.global_record_provider_run_started()(
                            data_type="realtime_quote", provider=fetcher.name, operation="get_realtime_quote"
                        )
                        quote = self.use_call_fetcher_method(fetcher, "get_realtime_quote", stock_code, source="sina")
                elif source in ("tencent", "akshare_qq"):
                    fetcher = self.use_get_fetcher_by_name("AkshareFetcher", capability="realtime_quote")
                    if fetcher is not None and hasattr(fetcher, "get_realtime_quote"):
                        self.global_record_provider_run_started()(
                            data_type="realtime_quote", provider=fetcher.name, operation="get_realtime_quote"
                        )
                        quote = self.use_call_fetcher_method(
                            fetcher, "get_realtime_quote", stock_code, source="tencent"
                        )
                elif source == "tushare":
                    fetcher = self.use_get_fetcher_by_name("TushareFetcher", capability="realtime_quote")
                    if fetcher is not None and hasattr(fetcher, "get_realtime_quote"):
                        self.global_record_provider_run_started()(
                            data_type="realtime_quote", provider=fetcher.name, operation="get_realtime_quote"
                        )
                        quote = self.use_call_fetcher_method(
                            fetcher, "get_realtime_quote", raw_stock_code or stock_code
                        )
                elif source == "tickflow":
                    fetcher = self.use_get_fetcher_by_name("TickFlowFetcher", capability="realtime_quote")
                    if fetcher is not None and hasattr(fetcher, "get_realtime_quote"):
                        self.global_record_provider_run_started()(
                            data_type="realtime_quote", provider=fetcher.name, operation="get_realtime_quote"
                        )
                        quote = self.use_call_fetcher_method(
                            fetcher, "get_realtime_quote", raw_stock_code or stock_code
                        )
                provider_name = fetcher.name if fetcher is not None else source
                if quote is not None and quote.has_basic_data():
                    self.global_record_provider_run()(
                        data_type="realtime_quote",
                        provider=provider_name,
                        operation="get_realtime_quote",
                        success=True,
                        latency_ms=int((self.global_time().time() - attempt_start) * 1000),
                        fallback_to=(
                            fallback_to if primary_quote is None and self.use_quote_needs_supplement(quote) else None
                        ),
                        record_count=1,
                    )
                    if primary_quote is None:
                        primary_quote = quote
                        primary_fallback_from = failed_sources[0] if failed_sources else None
                        self.global_logger().info(f"[实时行情] {stock_code} 成功获取 (来源: {source})")
                        if not self.use_quote_needs_supplement(primary_quote):
                            return self.use_enrich_realtime_quote(
                                primary_quote,
                                fallback_from=primary_fallback_from,
                                realtime_cache_ttl=getattr(config, "realtime_cache_ttl", None),
                            )
                        self.global_logger().debug(f"[实时行情] {stock_code} 部分字段缺失，尝试从后续数据源补充")
                        supplement_attempts = 0
                    else:
                        supplement_attempts += 1
                        if supplement_attempts > 1:
                            self.global_logger().debug(f"[实时行情] {stock_code} 补充尝试已达上限，停止继续")
                            break
                        merged = self.use_merge_quote_fields(primary_quote, quote)
                        if merged:
                            self.global_logger().info(f"[实时行情] {stock_code} 从 {source} 补充了缺失字段: {merged}")
                        if not self.use_quote_needs_supplement(primary_quote):
                            break
                else:
                    self.global_record_provider_run()(
                        data_type="realtime_quote",
                        provider=provider_name,
                        operation="get_realtime_quote",
                        success=False,
                        latency_ms=int((self.global_time().time() - attempt_start) * 1000),
                        error_type="empty",
                        error_message="empty or incomplete quote",
                        fallback_to=fallback_to,
                        record_count=0,
                    )
                    if primary_quote is None:
                        failed_sources.append(source)
            except Exception as e:
                error_msg = f"[{source}] 失败: {str(e)}"
                error_type, error_reason = self.global_summarize_exception()(e)
                self.global_record_provider_run()(
                    data_type="realtime_quote",
                    provider=getattr(fetcher, "name", source),
                    operation="get_realtime_quote",
                    success=False,
                    latency_ms=int((self.global_time().time() - attempt_start) * 1000),
                    error_type=error_type,
                    error_message=error_reason,
                    fallback_to=fallback_to,
                )
                self.global_logger().info(f"[实时行情] {stock_code} {error_msg}，继续尝试下一个数据源")
                errors.append(error_msg)
                if primary_quote is None:
                    failed_sources.append(source)
                continue
        if primary_quote is not None:
            return self.use_enrich_realtime_quote(
                primary_quote,
                fallback_from=primary_fallback_from,
                realtime_cache_ttl=getattr(config, "realtime_cache_ttl", None),
            )
        if log_final_failure:
            if errors:
                self.global_logger().info(f"[实时行情] {stock_code} 所有数据源均失败: {'; '.join(errors)}")
            else:
                self.global_logger().info(f"[实时行情] {stock_code} 无可用数据源")
        return None

    def _try_fetcher_quote(self, stock_code: str, fetcher_name: str, **kw):
        """Try to get a realtime quote from a named fetcher; returns quote or None."""
        fetcher = self.use_get_fetcher_by_name(fetcher_name, capability="realtime_quote")
        if fetcher is None or not hasattr(fetcher, "get_realtime_quote"):
            self.global_record_provider_run()(
                data_type="realtime_quote",
                provider=fetcher_name,
                operation="get_realtime_quote",
                success=False,
                error_type="unavailable",
                error_message="fetcher unavailable",
            )
            return None
        attempt_start = self.global_time().time()
        try:
            self.global_record_provider_run_started()(
                data_type="realtime_quote", provider=fetcher.name, operation="get_realtime_quote"
            )
            q = self.use_call_fetcher_method(fetcher, "get_realtime_quote", stock_code, **kw)
            if q is not None and q.has_basic_data():
                self.global_record_provider_run()(
                    data_type="realtime_quote",
                    provider=fetcher.name,
                    operation="get_realtime_quote",
                    success=True,
                    latency_ms=int((self.global_time().time() - attempt_start) * 1000),
                    record_count=1,
                )
                return q
            self.global_record_provider_run()(
                data_type="realtime_quote",
                provider=fetcher.name,
                operation="get_realtime_quote",
                success=False,
                latency_ms=int((self.global_time().time() - attempt_start) * 1000),
                error_type="empty",
                error_message="empty or incomplete quote",
                record_count=0,
            )
        except Exception as e:
            error_type, error_reason = self.global_summarize_exception()(e)
            self.global_record_provider_run()(
                data_type="realtime_quote",
                provider=fetcher.name,
                operation="get_realtime_quote",
                success=False,
                latency_ms=int((self.global_time().time() - attempt_start) * 1000),
                error_type=error_type,
                error_message=error_reason,
            )
            self.global_logger().debug(f"[实时行情] {stock_code} {fetcher_name} 获取失败: {e}")
        return None
