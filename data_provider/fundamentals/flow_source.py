"""基本面资金流/龙虎榜块协调；复用原资源所有者，不创建另一份缓存或超时槽。"""

from dataclasses import dataclass
import logging
from typing import Any, Callable, Dict, Optional

from src.domain.market.stock_codes import normalize_stock_code

logger = logging.getLogger("data_provider.base")


@dataclass(frozen=True)
class FundamentalFlowOperations:
    """通过窄回调加载原适配器/缓存/重试/外部能力，不依赖公开基本面门面。"""

    use_build_fundamental_block: Callable
    current_fundamental_adapter: Callable
    use_normalize_source_chain: Callable
    use_run_with_retry: Callable
    market_tag: Callable
    is_etf: Callable
    clock: Callable[[], Any]

    def get_capital_flow_context(self, stock_code: str, budget_seconds: Optional[float] = None) -> Dict[str, Any]:
        """资金流向块（fail-open）。"""
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
        payload, err, cost_ms = self.use_run_with_retry(
            lambda: self.current_fundamental_adapter().get_capital_flow(stock_code),
            timeout,
            "capital_flow",
        )
        if not isinstance(payload, dict):
            return self.use_build_fundamental_block(
                "failed",
                {},
                [{"provider": "fundamental_pipeline", "result": "failed", "duration_ms": cost_ms}],
                [err or "capital_flow failed"],
            )

        stock_flow = payload.get("stock_flow") or {}
        sector_rankings = payload.get("sector_rankings") or {}
        has_stock_flow = False
        if isinstance(stock_flow, dict):
            has_stock_flow = any(v is not None for v in stock_flow.values())
        has_sector_rankings = bool(sector_rankings.get("top")) or bool(sector_rankings.get("bottom"))
        adapter_status = str(payload.get("status", "not_supported"))
        if has_stock_flow or has_sector_rankings:
            capital_flow_status = "ok"
        elif adapter_status == "not_supported":
            capital_flow_status = "not_supported"
        else:
            capital_flow_status = "partial"

        return self.use_build_fundamental_block(
            capital_flow_status,
            {
                "stock_flow": payload.get("stock_flow", {}),
                "sector_rankings": payload.get("sector_rankings", {}),
            },
            self.use_normalize_source_chain(
                payload.get("source_chain", []),
                "capital_flow",
                capital_flow_status,
                cost_ms,
            ),
            list(payload.get("errors", [])) + ([err] if err else []),
        )

    def get_dragon_tiger_context(self, stock_code: str, budget_seconds: Optional[float] = None) -> Dict[str, Any]:
        """龙虎榜块（fail-open）。"""
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
        payload, err, cost_ms = self.use_run_with_retry(
            lambda: self.current_fundamental_adapter().get_dragon_tiger_flag(stock_code),
            timeout,
            "dragon_tiger",
        )
        if not isinstance(payload, dict):
            return self.use_build_fundamental_block(
                "failed",
                {},
                [{"provider": "fundamental_pipeline", "result": "failed", "duration_ms": cost_ms}],
                [err or "dragon_tiger failed"],
            )
        return self.use_build_fundamental_block(
            (payload.get("status") if isinstance(payload.get("status"), str) else "partial"),
            {
                "is_on_list": bool(payload.get("is_on_list", False)),
                "recent_count": int(payload.get("recent_count", 0)),
                "latest_date": payload.get("latest_date"),
            },
            self.use_normalize_source_chain(
                payload.get("source_chain", []),
                "dragon_tiger",
                str(payload.get("status", "ok")),
                cost_ms,
            ),
            list(payload.get("errors", [])) + ([err] if err else []),
        )
