"""基本面聚合预算与状态协调；复用原资源所有者，不创建另一份缓存或超时槽。"""

import numpy as np
import pandas as pd

from dataclasses import dataclass
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from src.domain.market.stock_codes import normalize_stock_code

logger = logging.getLogger("data_provider.base")


@dataclass(frozen=True)
class FundamentalAggregation:
    """通过窄回调加载原适配器/缓存/重试/外部能力，不依赖公开基本面门面。"""

    use_build_fundamental_block: Callable
    use_build_market_not_supported: Callable
    use_build_offshore_fundamental_context: Callable
    current_fundamental_adapter: Callable
    current_fundamental_cache: Callable
    current_fundamental_cache_lock: Callable
    use_get_fundamental_cache_key: Callable
    use_get_tw_institutional_source: Callable
    use_has_meaningful_payload: Callable
    use_infer_block_status: Callable
    use_normalize_source_chain: Callable
    use_prune_fundamental_cache: Callable
    use_run_with_retry: Callable
    use_should_cache_fundamental_context: Callable
    current_yfinance_fundamental_adapter: Callable
    use_get_board_context: Callable
    use_get_capital_flow_context: Callable
    use_get_dragon_tiger_context: Callable
    use_get_realtime_quote: Callable
    use_get_sector_rankings_with_meta: Callable
    market_tag: Callable
    is_etf: Callable
    clock: Callable[[], Any]

    def get_fundamental_context(self, stock_code: str, budget_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Aggregate fundamental blocks with fail-open semantics.
        """
        from src.config import get_config

        config = get_config()
        if not config.enable_fundamental_pipeline:
            return self.use_build_market_not_supported(
                market=self.market_tag(stock_code),
                reason="fundamental pipeline disabled",
            )

        stock_code = normalize_stock_code(stock_code)
        market = self.market_tag(stock_code)
        is_etf = self.is_etf(stock_code)
        if market in {"us", "hk", "jp", "kr", "tw"}:
            return self.use_build_offshore_fundamental_context(
                stock_code,
                market=market,
                budget_seconds=budget_seconds,
            )

        stage_timeout = float(
            budget_seconds if budget_seconds is not None else config.fundamental_stage_timeout_seconds
        )
        stage_timeout = max(0.0, stage_timeout)
        fetch_timeout = float(config.fundamental_fetch_timeout_seconds)
        fetch_timeout = max(0.0, fetch_timeout)

        cache_ttl = int(config.fundamental_cache_ttl_seconds)
        cache_max_entries = max(0, int(getattr(config, "fundamental_cache_max_entries", 256)))
        cache_key = self.use_get_fundamental_cache_key(stock_code, stage_timeout)
        if cache_ttl > 0:
            self.use_prune_fundamental_cache(cache_ttl, cache_max_entries)
            with self.current_fundamental_cache_lock():
                cache_item = self.current_fundamental_cache().get(cache_key)
                if cache_item:
                    age = self.clock().time() - float(cache_item.get("ts", 0))
                    if age <= cache_ttl:
                        return cache_item.get("context", {})

        remaining_seconds = stage_timeout
        result_ctx: Dict[str, Any] = {
            "market": market,
            "valuation": {},
            "growth": {},
            "earnings": {},
            "institution": {},
            "capital_flow": {},
            "dragon_tiger": {},
            "boards": {},
            "coverage": {},
            "source_chain": [],
            "errors": [],
        }

        start_ts = self.clock().time()

        def _consume_budget(consumed_ms: int) -> None:
            """扣减取数耗时预算。"""
            nonlocal remaining_seconds
            remaining_seconds = max(0.0, remaining_seconds - consumed_ms / 1000.0)

        valuation_timeout = min(fetch_timeout, remaining_seconds)
        if valuation_timeout > 0:
            quote_payload, valuation_err, valuation_ms = self.use_run_with_retry(
                lambda: self.use_get_realtime_quote(stock_code),
                valuation_timeout,
                "fundamental_valuation",
            )
            _consume_budget(valuation_ms)
        else:
            quote_payload, valuation_err, valuation_ms = None, "fundamental stage timeout", 0

        valuation_payload = {
            "pe_ratio": getattr(quote_payload, "pe_ratio", None) if quote_payload else None,
            "pb_ratio": getattr(quote_payload, "pb_ratio", None) if quote_payload else None,
            "total_mv": getattr(quote_payload, "total_mv", None) if quote_payload else None,
            "circ_mv": getattr(quote_payload, "circ_mv", None) if quote_payload else None,
        }
        valuation_status = self.use_infer_block_status(
            valuation_payload,
            "partial" if quote_payload is not None else "not_supported",
        )
        if valuation_status == "partial" and valuation_err and not self.use_has_meaningful_payload(valuation_payload):
            valuation_status = "failed"
        result_ctx["valuation"] = self.use_build_fundamental_block(
            valuation_status,
            valuation_payload,
            self.use_normalize_source_chain(
                [{"provider": "realtime_quote", "result": valuation_status, "duration_ms": valuation_ms}],
                "realtime_quote",
                valuation_status,
                valuation_ms,
            ),
            [valuation_err] if valuation_err else [],
        )

        # growth / earnings / institution (one AkShare call)
        if remaining_seconds <= 0:
            bundle_status = "failed"
            bundle_payload: Dict[str, Any] = {}
            bundle_errors = ["fundamental stage timeout"]
            bundle_ms = 0
        else:
            bundle_timeout = min(fetch_timeout, remaining_seconds)
            bundle_payload, bundle_err_msg, bundle_ms = self.use_run_with_retry(
                lambda: self.current_fundamental_adapter().get_fundamental_bundle(stock_code),
                bundle_timeout,
                "fundamental_bundle",
            )
            _consume_budget(bundle_ms)
            if not isinstance(bundle_payload, dict):
                bundle_status = "failed"
                bundle_payload = {}
                bundle_errors = ["fundamental_bundle failed"]
                if bundle_err_msg:
                    bundle_errors.append(bundle_err_msg)
            else:
                bundle_status = str(bundle_payload.get("status", "not_supported"))
                bundle_errors = [bundle_err_msg] if bundle_err_msg else []

        bundle_chain = (
            self.use_normalize_source_chain(
                bundle_payload.get("source_chain", []),
                "fundamental_bundle",
                bundle_status,
                bundle_ms,
            )
            if isinstance(bundle_payload, dict)
            else self.use_normalize_source_chain(
                None,
                "fundamental_bundle",
                bundle_status,
                bundle_ms,
            )
        )
        growth_payload = bundle_payload.get("growth", {}) if isinstance(bundle_payload, dict) else {}
        earnings_payload = bundle_payload.get("earnings", {}) if isinstance(bundle_payload, dict) else {}
        institution_payload = bundle_payload.get("institution", {}) if isinstance(bundle_payload, dict) else {}
        if not isinstance(growth_payload, dict):
            growth_payload = {}
        else:
            growth_payload = dict(growth_payload)
        if not isinstance(earnings_payload, dict):
            earnings_payload = {}
        else:
            earnings_payload = dict(earnings_payload)
        if not isinstance(institution_payload, dict):
            institution_payload = {}
        else:
            institution_payload = dict(institution_payload)

        # Derive TTM dividend yield from already-fetched quote price; avoid extra quote calls.
        earnings_extra_errors: List[str] = []
        dividend_payload = earnings_payload.get("dividend")
        if isinstance(dividend_payload, dict):
            dividend_payload = dict(dividend_payload)
            ttm_cash_raw = dividend_payload.get("ttm_cash_dividend_per_share")
            ttm_cash = None
            if ttm_cash_raw is not None:
                try:
                    ttm_cash = float(ttm_cash_raw)
                except (TypeError, ValueError):
                    earnings_extra_errors.append("invalid_ttm_cash_dividend_per_share")
            if isinstance(quote_payload, dict):
                latest_price_raw = quote_payload.get("price")
            else:
                latest_price_raw = getattr(quote_payload, "price", None) if quote_payload else None
            latest_price = None
            if latest_price_raw is not None:
                try:
                    latest_price = float(latest_price_raw)
                except (TypeError, ValueError):
                    latest_price = None
            ttm_yield = None
            if ttm_cash is not None:
                if latest_price is not None and latest_price > 0:
                    ttm_yield = round(ttm_cash / latest_price * 100.0, 4)
                else:
                    earnings_extra_errors.append("invalid_price_for_ttm_dividend_yield")

            dividend_payload["ttm_dividend_yield_pct"] = ttm_yield
            if ttm_yield is not None:
                dividend_payload["yield_formula"] = "ttm_cash_dividend_per_share / latest_price * 100"
            earnings_payload["dividend"] = dividend_payload

        adapter_errors = list(bundle_payload.get("errors", [])) if isinstance(bundle_payload, dict) else []
        adapter_errors.extend(bundle_errors)
        growth_errors = list(adapter_errors)
        earnings_errors = list(adapter_errors)
        earnings_errors.extend(earnings_extra_errors)
        institution_errors = list(adapter_errors)

        growth_status = self.use_infer_block_status(growth_payload, bundle_status)
        earnings_status = self.use_infer_block_status(earnings_payload, bundle_status)
        institution_status = self.use_infer_block_status(institution_payload, bundle_status)

        result_ctx["growth"] = self.use_build_fundamental_block(
            growth_status,
            growth_payload,
            bundle_chain,
            growth_errors,
        )
        result_ctx["earnings"] = self.use_build_fundamental_block(
            earnings_status,
            earnings_payload,
            bundle_chain,
            earnings_errors,
        )
        result_ctx["institution"] = self.use_build_fundamental_block(
            institution_status,
            institution_payload,
            bundle_chain,
            institution_errors,
        )

        # capital flow
        if is_etf:
            result_ctx["capital_flow"] = self.use_build_fundamental_block(
                "not_supported",
                {},
                [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
                ["etf not fully supported"],
            )
            result_ctx["dragon_tiger"] = self.use_build_fundamental_block(
                "not_supported",
                {},
                [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
                ["etf not fully supported"],
            )
            result_ctx["boards"] = self.use_build_fundamental_block(
                "not_supported",
                {},
                [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
                ["etf not fully supported"],
            )
            result_ctx["status"] = "partial"
        else:
            capital_flow_budget = min(fetch_timeout, remaining_seconds)
            capital_flow_start = self.clock().time()
            result_ctx["capital_flow"] = self.use_get_capital_flow_context(
                stock_code,
                budget_seconds=capital_flow_budget,
            )
            _consume_budget(int((self.clock().time() - capital_flow_start) * 1000))

            dragon_tiger_budget = min(fetch_timeout, remaining_seconds)
            dragon_tiger_start = self.clock().time()
            result_ctx["dragon_tiger"] = self.use_get_dragon_tiger_context(
                stock_code,
                budget_seconds=dragon_tiger_budget,
            )
            _consume_budget(int((self.clock().time() - dragon_tiger_start) * 1000))

            result_ctx["boards"] = self.use_get_board_context(
                stock_code,
                budget_seconds=min(fetch_timeout, remaining_seconds),
            )

        block_statuses = {
            "valuation": result_ctx["valuation"].get("status", "not_supported"),
            "growth": result_ctx["growth"].get("status", "not_supported"),
            "earnings": result_ctx["earnings"].get("status", "not_supported"),
            "institution": result_ctx["institution"].get("status", "not_supported"),
            "capital_flow": result_ctx["capital_flow"].get("status", "not_supported"),
            "dragon_tiger": result_ctx["dragon_tiger"].get("status", "not_supported"),
            "boards": result_ctx["boards"].get("status", "not_supported"),
        }
        result_ctx["coverage"] = block_statuses
        for block in (
            "valuation",
            "growth",
            "earnings",
            "institution",
            "capital_flow",
            "dragon_tiger",
            "boards",
        ):
            result_ctx["errors"].extend(result_ctx[block].get("errors", []))
            result_ctx["source_chain"].extend(result_ctx[block].get("source_chain", []))

        if is_etf:
            # Keep ETF downgrade semantics for overall status even when valuation is available.
            result_ctx["status"] = (
                "not_supported" if all(value == "not_supported" for value in block_statuses.values()) else "partial"
            )
        elif all(value == "not_supported" for value in block_statuses.values()):
            result_ctx["status"] = "not_supported"
        elif "failed" in block_statuses.values() or "partial" in block_statuses.values():
            result_ctx["status"] = "partial"
        else:
            result_ctx["status"] = "ok"

        result_ctx["elapsed_ms"] = int((self.clock().time() - start_ts) * 1000)
        if cache_ttl > 0 and self.use_should_cache_fundamental_context(result_ctx):
            with self.current_fundamental_cache_lock():
                self.current_fundamental_cache()[cache_key] = {
                    "ts": self.clock().time(),
                    "context": result_ctx,
                }
            self.use_prune_fundamental_cache(cache_ttl, cache_max_entries)
        return result_ctx

    def build_offshore_fundamental_context(
        self,
        stock_code: str,
        market: str,
        budget_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """HK/US fundamental aggregation via yfinance.

        Mirrors :meth:`get_fundamental_context` but skips A-share-specific
        blocks (capital_flow, dragon_tiger, sector rankings). belong_boards is
        sourced from yfinance ``info.sector`` / ``info.industry``.

        Cache, retry and fail-open semantics intentionally match the CN path so
        upstream callers see the same shape regardless of market.
        """
        from src.config import get_config

        config = get_config()
        stage_timeout = float(
            budget_seconds if budget_seconds is not None else config.fundamental_stage_timeout_seconds
        )
        stage_timeout = max(0.0, stage_timeout)
        fetch_timeout = float(config.fundamental_fetch_timeout_seconds)
        fetch_timeout = max(0.0, fetch_timeout)

        cache_ttl = int(config.fundamental_cache_ttl_seconds)
        cache_max_entries = max(0, int(getattr(config, "fundamental_cache_max_entries", 256)))
        cache_key = self.use_get_fundamental_cache_key(stock_code, stage_timeout)
        if cache_ttl > 0:
            self.use_prune_fundamental_cache(cache_ttl, cache_max_entries)
            with self.current_fundamental_cache_lock():
                cache_item = self.current_fundamental_cache().get(cache_key)
                if cache_item:
                    age = self.clock().time() - float(cache_item.get("ts", 0))
                    if age <= cache_ttl:
                        return cache_item.get("context", {})

        result_ctx: Dict[str, Any] = {
            "market": market,
            "provider": "yfinance",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "data_quality": "unavailable",
            "missing_fields": [],
            "valuation": {},
            "growth": {},
            "earnings": {},
            "institution": {},
            "capital_flow": {},
            "dragon_tiger": {},
            "boards": {},
            "belong_boards": [],
            "coverage": {},
            "source_chain": [],
            "errors": [],
        }
        start_ts = self.clock().time()

        # Valuation: reuse realtime quote payload — yfinance returns pe/pb in the
        # same shape as AkShare, so the existing block formatter still works.
        valuation_timeout = min(fetch_timeout, stage_timeout) if stage_timeout > 0 else 0
        if valuation_timeout > 0:
            quote_payload, valuation_err, valuation_ms = self.use_run_with_retry(
                lambda: self.use_get_realtime_quote(stock_code),
                valuation_timeout,
                "fundamental_valuation",
            )
        else:
            quote_payload, valuation_err, valuation_ms = None, "fundamental stage timeout", 0
        valuation_payload = {
            "pe_ratio": getattr(quote_payload, "pe_ratio", None) if quote_payload else None,
            "pb_ratio": getattr(quote_payload, "pb_ratio", None) if quote_payload else None,
            "total_mv": getattr(quote_payload, "total_mv", None) if quote_payload else None,
            "circ_mv": getattr(quote_payload, "circ_mv", None) if quote_payload else None,
        }
        valuation_status = self.use_infer_block_status(
            valuation_payload,
            "partial" if quote_payload is not None else "not_supported",
        )
        if valuation_status == "partial" and valuation_err and not self.use_has_meaningful_payload(valuation_payload):
            valuation_status = "failed"
        result_ctx["valuation"] = self.use_build_fundamental_block(
            valuation_status,
            valuation_payload,
            self.use_normalize_source_chain(
                [{"provider": "realtime_quote", "result": valuation_status, "duration_ms": valuation_ms}],
                "realtime_quote",
                valuation_status,
                valuation_ms,
            ),
            [valuation_err] if valuation_err else [],
        )

        # Fundamental bundle via yfinance.
        bundle_timeout = min(fetch_timeout, max(stage_timeout - (self.clock().time() - start_ts), 0.0))
        if bundle_timeout <= 0:
            bundle_payload, bundle_err, bundle_ms = {}, "fundamental stage timeout", 0
        else:
            bundle_payload, bundle_err, bundle_ms = self.use_run_with_retry(
                lambda: self.current_yfinance_fundamental_adapter().get_fundamental_bundle(stock_code),
                bundle_timeout,
                "fundamental_bundle_yfinance",
            )
        if not isinstance(bundle_payload, dict):
            bundle_payload = {}

        bundle_chain = self.use_normalize_source_chain(
            bundle_payload.get("source_chain", []),
            "fundamental_bundle_yfinance",
            str(bundle_payload.get("status", "not_supported")),
            bundle_ms,
        )
        adapter_errors = list(bundle_payload.get("errors", []))
        if bundle_err:
            adapter_errors.append(bundle_err)

        growth_payload = bundle_payload.get("growth", {}) if isinstance(bundle_payload.get("growth"), dict) else {}
        earnings_payload = (
            bundle_payload.get("earnings", {}) if isinstance(bundle_payload.get("earnings"), dict) else {}
        )
        belong_boards = (
            bundle_payload.get("belong_boards") if isinstance(bundle_payload.get("belong_boards"), list) else []
        )

        growth_status = self.use_infer_block_status(growth_payload, str(bundle_payload.get("status", "not_supported")))
        earnings_status = self.use_infer_block_status(
            earnings_payload, str(bundle_payload.get("status", "not_supported"))
        )

        result_ctx["growth"] = self.use_build_fundamental_block(
            growth_status,
            growth_payload,
            bundle_chain,
            list(adapter_errors),
        )
        result_ctx["earnings"] = self.use_build_fundamental_block(
            earnings_status,
            earnings_payload,
            bundle_chain,
            list(adapter_errors),
        )

        # capital_flow / dragon_tiger / boards: no offshore data feed today -> not_supported.
        for block in ("capital_flow", "dragon_tiger", "boards"):
            result_ctx[block] = self.use_build_fundamental_block(
                "not_supported",
                {},
                [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
                ["not supported for offshore market"],
            )

        # institution: tw (台股) has a free official 三大法人 (institutional net buy/sell)
        # feed (TWSE T86 / TPEx OpenAPI); every other offshore market keeps not_supported.
        # tw-only + strictly additive + fail-open: any error or no-data -> not_supported,
        # which never interrupts the main analysis. Raw net figures only — no derived
        # signal / score / schema (per the v2 scope confirmed on issue #1777).
        tw_record = None
        if market == "tw":
            source = None
            try:
                source = self.use_get_tw_institutional_source()
            except Exception as exc:  # noqa: BLE001 - wiring failure: loud but fail-open
                logger.error("[tw-inst] source init failed (wiring bug?) code=%s: %s", stock_code, exc)
                source = None
            # fetch_timeout == 0 disables per-fetch fundamental fetches (same as valuation /
            # bundle above, which gate on fetch_timeout); honour that for institution too so
            # the FUNDAMENTAL_FETCH_TIMEOUT_SECONDS=0 config semantic is not bypassed.
            if source is not None and fetch_timeout > 0:
                # The tw institution block is a WHOLE-MARKET download (~4-5s), far slower
                # than the per-symbol quote/bundle fetches, and it is the LAST offshore
                # block. When enabled, give it the full REMAINING stage budget rather than
                # the ~3s per-fetch cap that starves it and makes the first/only stock of a
                # run coin-flip between ok and not_supported. Bounded by the stage deadline
                # via _run_with_retry, so it fails open (never blocks).
                inst_timeout = max(stage_timeout - (self.clock().time() - start_ts), 0.0)
                if inst_timeout > 0:
                    from data_provider.institutional.base import InstitutionalRequest

                    tw_result, inst_err, _inst_ms = self.use_run_with_retry(
                        lambda: source.fetch(InstitutionalRequest(stock_code=stock_code)),
                        inst_timeout,
                        "fundamental_tw_institution",
                    )
                    tw_record = tw_result.payload if tw_result is not None else None
                    if inst_err:
                        logger.warning("[tw-inst] fetch failed/timeout code=%s: %s", stock_code, inst_err)
                else:
                    tw_record = None
        # status 'ok' only when the record carries all core net figures (a genuine 0 is
        # kept — 0 is not None); None / missing core field / fetch failure -> not_supported.
        _tw_core = ("foreign_net", "trust_net", "dealer_net", "total_net")
        if tw_record is not None and all(tw_record.get(key) is not None for key in _tw_core):
            institution_status = "ok"
            result_ctx["institution"] = self.use_build_fundamental_block(
                "ok",
                {
                    "foreign_net": tw_record.get("foreign_net"),
                    "trust_net": tw_record.get("trust_net"),
                    "dealer_net": tw_record.get("dealer_net"),
                    "total_net": tw_record.get("total_net"),
                    "unit": tw_record.get("unit"),
                    "date": tw_record.get("date"),
                    "source": tw_record.get("source"),
                },
                [{"provider": tw_record.get("source", "tw-institutional"), "result": "ok", "duration_ms": 0}],
                [],
            )
        else:
            institution_status = "not_supported"
            result_ctx["institution"] = self.use_build_fundamental_block(
                "not_supported",
                {},
                [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
                ["not supported for offshore market"],
            )

        result_ctx["belong_boards"] = belong_boards

        block_statuses = {
            "valuation": result_ctx["valuation"].get("status", "not_supported"),
            "growth": growth_status,
            "earnings": earnings_status,
            "institution": institution_status,
            "capital_flow": "not_supported",
            "dragon_tiger": "not_supported",
            "boards": "not_supported",
        }
        result_ctx["coverage"] = block_statuses
        for block in ("valuation", "growth", "earnings", "institution", "capital_flow", "dragon_tiger", "boards"):
            result_ctx["errors"].extend(result_ctx[block].get("errors", []))
            result_ctx["source_chain"].extend(result_ctx[block].get("source_chain", []))

        active_statuses = {"valuation": valuation_status, "growth": growth_status, "earnings": earnings_status}
        # tw institution (when present) counts toward the OVERALL status so a report that
        # only has 三大法人 data still surfaces fundamentals (consumers key off the top-level
        # status). missing_fields stays the original three blocks, so offshore markets
        # without institution data are byte-identical (institution is not_supported there).
        status_values = list(active_statuses.values())
        if institution_status == "ok":
            status_values.append("ok")
        if all(value == "not_supported" for value in status_values):
            result_ctx["status"] = "not_supported"
            result_ctx["data_quality"] = "unavailable"
        elif "failed" in status_values or "partial" in status_values:
            result_ctx["status"] = "partial"
            result_ctx["data_quality"] = "partial"
        else:
            result_ctx["status"] = "ok"
            result_ctx["data_quality"] = "ok"
        result_ctx["missing_fields"] = [block for block, status in active_statuses.items() if status != "ok"]

        result_ctx["elapsed_ms"] = int((self.clock().time() - start_ts) * 1000)
        if cache_ttl > 0 and self.use_should_cache_fundamental_context(result_ctx):
            with self.current_fundamental_cache_lock():
                self.current_fundamental_cache()[cache_key] = {
                    "ts": self.clock().time(),
                    "context": result_ctx,
                }
            self.use_prune_fundamental_cache(cache_ttl, cache_max_entries)
        return result_ctx

    def build_failed_fundamental_context(self, stock_code: str, reason: str) -> Dict[str, Any]:
        """Build a consistent failed-context payload for caller-side fallback."""
        market = self.market_tag(stock_code)
        block_names = (
            "valuation",
            "growth",
            "earnings",
            "institution",
            "capital_flow",
            "dragon_tiger",
            "boards",
        )
        blocks = {
            block: self.use_build_fundamental_block(
                "failed",
                {},
                [{"provider": "fundamental_pipeline", "result": "failed", "duration_ms": 0}],
                [reason],
            )
            for block in block_names
        }
        return {
            "market": market,
            "status": "failed",
            "coverage": {block: "failed" for block in block_names},
            "source_chain": [{"provider": "fundamental_pipeline", "result": "failed", "duration_ms": 0}],
            "errors": [reason],
            **blocks,
        }

    def get_board_context(self, stock_code: str, budget_seconds: Optional[float] = None) -> Dict[str, Any]:
        """板块榜单块（fail-open）。"""
        from src.config import get_config

        config = get_config()
        stock_code = normalize_stock_code(stock_code)
        timeout = float(budget_seconds if budget_seconds is not None else config.fundamental_fetch_timeout_seconds)
        if self.market_tag(stock_code) != "cn" or self.is_etf(stock_code):
            return self.use_build_fundamental_block(
                "not_supported",
                {},
                [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
                ["not supported"],
            )

        if timeout <= 0:
            return self.use_build_fundamental_block(
                "failed",
                {},
                [{"provider": "fundamental_pipeline", "result": "failed", "duration_ms": 0}],
                ["fundamental stage timeout"],
            )

        def task() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], str]:
            """构造单个取数任务。"""
            return self.use_get_sector_rankings_with_meta(5)

        rankings, err, cost_ms = self.use_run_with_retry(task, timeout, "boards")
        if isinstance(rankings, tuple) and len(rankings) == 4:
            top, bottom, chain, chain_error = rankings
            if chain_error and not err:
                err = chain_error
            if not top and not bottom:
                return self.use_build_fundamental_block(
                    "failed",
                    {},
                    chain if chain else [{"provider": "sector_rankings", "result": "failed", "duration_ms": cost_ms}],
                    [err or "boards empty from all sources"],
                )
            board_status = "ok" if top and bottom else "partial"
            return self.use_build_fundamental_block(
                board_status,
                {"top": top or [], "bottom": bottom or []},
                (
                    chain
                    if chain
                    else self.use_normalize_source_chain(
                        ["sector_rankings"],
                        "boards",
                        board_status,
                        cost_ms,
                    )
                ),
                [err] if err else [],
            )

        return self.use_build_fundamental_block(
            "failed",
            {},
            [{"provider": "sector_rankings", "result": "failed", "duration_ms": cost_ms}],
            [err or "boards failed"],
        )


class FundamentalContextLoader(Protocol):
    """完整聚合 payload 的窄加载接口。"""

    def __call__(self, stock_code: str, budget_seconds: Optional[float] = None) -> Dict[str, Any]: ...


def build_fundamental_context_loader() -> FundamentalContextLoader:
    """保留一个 Source 一个原资源所有者，直接绑定唯一聚合实现而非公开门面。"""
    from data_provider.runtime.manager import DataFetcherManager

    owner = DataFetcherManager()
    return owner._fundamental_source().get_fundamental_context


def normalize_source_chain(entries: Any, provider: str, result: str, duration_ms: int) -> List[Dict[str, Any]]:
    """Normalize free-form source chain entries to structured dict list."""
    if entries is None:
        return [{"provider": provider, "result": result, "duration_ms": duration_ms}]

    normalized: List[Dict[str, Any]] = []
    if not isinstance(entries, (list, tuple)):
        entries = [entries]

    for item in entries:
        if isinstance(item, dict):
            normalized.append({
                "provider": str(item.get("provider") or provider),
                "result": str(item.get("result") or result),
                "duration_ms": int(item.get("duration_ms", duration_ms)),
            })
            continue

        if item is None:
            continue

        provider_name = str(item)
        normalized.append({
            "provider": provider_name,
            "result": result,
            "duration_ms": duration_ms,
        })

    if not normalized:
        return [{"provider": provider, "result": result, "duration_ms": duration_ms}]

    return normalized



def block_status(payload: Dict[str, Any], available: bool=True) -> str:
    """返回数据块状态。"""
    if not available:
        return "not_supported"
    if not payload:
        return "partial"
    return "ok"



def build_fundamental_block(status: str, payload: Optional[Dict[str, Any]]=None, source_chain: Optional[List[Dict[str, Any]]]=None, errors: Optional[List[str]]=None) -> Dict[str, Any]:
    """构建基本面数据块。"""
    return {
        "status": status,
        "coverage": {"status": status},
        "source_chain": source_chain or [],
        "errors": errors or [],
        "data": payload or {},
    }



def has_meaningful_payload(payload: Any, *, use_has_meaningful_payload, use_try_scalar_isna) -> bool:
    """判断载荷是否含有效内容。"""
    if payload is None:
        return False
    if isinstance(payload, str):
        normalized = payload.strip().lower()
        return normalized not in ("", "-", "nan", "none", "null", "n/a", "na")
    if isinstance(payload, dict):
        return any(use_has_meaningful_payload(v) for v in payload.values())
    if isinstance(payload, pd.DataFrame):
        if payload.empty:
            return False
        return any(
            use_has_meaningful_payload(v)
            for v in payload.to_numpy().flat
        )
    if isinstance(payload, (pd.Series, pd.Index)):
        return any(use_has_meaningful_payload(v) for v in payload.tolist())
    if isinstance(payload, np.ndarray):
        if payload.ndim == 0:
            payload = payload.item()
        else:
            return any(
                use_has_meaningful_payload(v)
                for v in payload.flat
            )
    if isinstance(payload, (list, tuple, set)):
        return any(use_has_meaningful_payload(v) for v in payload)
    if use_try_scalar_isna(payload, "fundamental_payload") is True:
        return False
    return True



def infer_block_status(payload: Any, fallback_status: str, *, use_has_meaningful_payload) -> str:
    """推断数据块状态。"""
    if use_has_meaningful_payload(payload):
        return "ok"
    if fallback_status in ("failed", "partial", "not_supported"):
        return fallback_status
    return "partial"



def should_cache_fundamental_context(context: Any, *, use_has_meaningful_payload) -> bool:
    """判断基本面上下文是否应缓存。"""
    if not isinstance(context, dict):
        return False
    status = str(context.get("status", "")).strip().lower()
    if status == "ok":
        return True
    if status == "failed":
        return False
    for block in (
        "valuation",
        "growth",
        "earnings",
        "institution",
        "capital_flow",
        "dragon_tiger",
        "boards",
    ):
        payload = context.get(block, {})
        if isinstance(payload, dict) and use_has_meaningful_payload(payload.get("data")):
            return True
    return False



def build_market_not_supported(market: str, reason: str, *, use_build_fundamental_block) -> Dict[str, Any]:
    """构造市场不支持时的降级数据。"""
    blocks = {
        "valuation": use_build_fundamental_block(
            "partial" if market == "etf" else "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        ),
        "growth": use_build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        ),
        "earnings": use_build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        ),
        "institution": use_build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        ),
        "capital_flow": use_build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        ),
        "dragon_tiger": use_build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        ),
        "boards": use_build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        ),
    }
    return {
        "market": market,
        "status": "partial" if market == "etf" else "not_supported",
        "coverage": {
            block: blocks[block]["status"] for block in blocks
        },
        "source_chain": [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
        "errors": [reason],
        **blocks,
    }

