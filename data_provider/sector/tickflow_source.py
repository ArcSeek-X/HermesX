"""TickflowSectorOperations：复用原资源/缓存与既有字段、回退和预算，不复制宿主状态。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TickflowSectorOperations:
    """只接入本能力所需窄回调；资源和生命周期继续归原所有者。"""

    use_capability_available: Callable
    use_extract_universe_symbols: Callable
    use_get_client: Callable
    use_is_universe_permission_error: Callable
    use_mark_capability: Callable
    use_ratio_to_percent: Callable
    use_safe_float: Callable
    current_sector_rankings_cache: Callable[[], Any]
    current_sector_rankings_cache_lock: Callable[[], Any]
    set_sector_rankings_cache: Callable[[Any], None]
    call_monotonic: Callable
    read_logger: Callable[[], Any]
    read_cn_universe_id: Callable[[], Any]
    read_sector_rankings_cache_ttl_seconds: Callable[[], Any]

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """Build SW1 industry rankings from TickFlow universes and A-share quotes."""
        try:
            limit = max(1, int(n))
        except (TypeError, ValueError):
            limit = 5

        now = self.call_monotonic()
        with self.current_sector_rankings_cache_lock():
            cached = self.current_sector_rankings_cache()
            if cached and cached[0] > now:
                return [dict(row) for row in cached[1][:limit]], [dict(row) for row in cached[2][:limit]]

        client = self.use_get_client()
        if client is None or not self.use_capability_available("universe_quotes"):
            return None

        try:
            universes = client.universes.list()
            sw1_ids = [
                str(item.get("id"))
                for item in universes or []
                if isinstance(item, dict) and str(item.get("id") or "").startswith("CN_Equity_SW1_")
            ]
            if not sw1_ids:
                return None
            details = client.universes.batch(sw1_ids)
            quotes = client.quotes.get(universes=[self.read_cn_universe_id()])
            self.use_mark_capability("universe_quotes", True)
        except Exception as exc:
            if self.use_is_universe_permission_error(exc):
                self.use_mark_capability("universe_quotes", False)
                self.read_logger().info("[TickFlowFetcher] SW1 sector rankings are unavailable for current plan")
                return None
            raise

        quote_changes: Dict[str, float] = {}
        for quote in quotes or []:
            if not isinstance(quote, dict):
                continue
            symbol = str(quote.get("symbol") or "").strip().upper()
            ext = quote.get("ext") or {}
            change_pct = self.use_ratio_to_percent(ext.get("change_pct"))
            if change_pct is None:
                last_price = self.use_safe_float(quote.get("last_price"))
                prev_close = self.use_safe_float(quote.get("prev_close"))
                if last_price is not None and prev_close and prev_close > 0:
                    change_pct = (last_price - prev_close) / prev_close * 100
            if symbol and change_pct is not None:
                quote_changes[symbol] = change_pct

        industry_symbols: Dict[str, set[str]] = {}
        universe_by_id = {
            str(item.get("id")): item for item in universes or [] if isinstance(item, dict) and item.get("id")
        }
        for universe_id, detail in (details or {}).items():
            summary = universe_by_id.get(str(universe_id), {})
            name = str(summary.get("name") or "").strip()
            if name.startswith("SW1"):
                name = name[3:].strip()
            if not name:
                continue
            industry_symbols.setdefault(name, set()).update(self.use_extract_universe_symbols(detail))

        rows: List[Dict[str, Any]] = []
        for name, symbols in industry_symbols.items():
            changes = [quote_changes[symbol] for symbol in symbols if symbol in quote_changes]
            if changes:
                rows.append(
                    {
                        "name": name,
                        "change_pct": round(sum(changes) / len(changes), 4),
                        "source": "tickflow_sw1",
                        "constituent_count": len(changes),
                    }
                )
        if not rows:
            return None

        descending = sorted(rows, key=lambda row: row["change_pct"], reverse=True)
        ascending = sorted(rows, key=lambda row: row["change_pct"])
        with self.current_sector_rankings_cache_lock():
            self.set_sector_rankings_cache((now + self.read_sector_rankings_cache_ttl_seconds(), descending, ascending))
        return [dict(row) for row in descending[:limit]], [dict(row) for row in ascending[:limit]]
