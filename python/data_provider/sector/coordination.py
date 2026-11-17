"""SectorCoordination：复用原资源/缓存与既有字段、回退和预算，不复制宿主状态。"""

import pandas as pd

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple


@dataclass(frozen=True)
class SectorCoordination:
    """只接入本能力所需窄回调；资源和生命周期继续归原所有者。"""

    use_copy_ranking_rows: Callable
    use_get_fetchers_snapshot: Callable
    use_get_sector_manager: Callable
    use_get_sector_rankings_with_meta: Callable
    use_normalize_belong_boards: Callable
    current_fetchers: Callable[[], Any]
    class_concept_rankings_cache_lock: Callable[[], Any]
    class_concept_rankings_cache_ttl_seconds: Callable[[], Any]
    class_concept_rankings_empty_cache_ttl_seconds: Callable[[], Any]
    class_concept_rankings_cache: Callable[[], Any]
    call_market_tag: Callable
    call_normalize_stock_code: Callable
    call_record_provider_run: Callable
    call_record_provider_run_started: Callable
    call_summarize_exception: Callable
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def get_belong_boards(self, stock_code: str) -> List[Dict[str, Any]]:
        """
        Get stock membership boards through capability probing.

        Keep this at manager layer to avoid changing BaseFetcher abstraction.
        """
        stock_code = self.call_normalize_stock_code(stock_code)
        if self.call_market_tag(stock_code) != "cn":
            return []
        candidate_fetchers = [fetcher for fetcher in self.current_fetchers() if hasattr(fetcher, "get_belong_board")]
        for index, fetcher in enumerate(candidate_fetchers):
            fallback_to = candidate_fetchers[index + 1].name if index + 1 < len(candidate_fetchers) else None
            start = self.read_time().time()
            try:
                self.call_record_provider_run_started(
                    data_type="belong_boards",
                    provider=fetcher.name,
                    operation="get_belong_board",
                )
                raw_data = fetcher.get_belong_board(stock_code)
                boards = self.use_normalize_belong_boards(raw_data)
                if boards:
                    self.call_record_provider_run(
                        data_type="belong_boards",
                        provider=fetcher.name,
                        operation="get_belong_board",
                        success=True,
                        latency_ms=int((self.read_time().time() - start) * 1000),
                        record_count=len(boards),
                    )
                    self.read_logger().info(f"[{fetcher.name}] 获取所属板块成功: {stock_code}, count={len(boards)}")
                    return boards
                self.call_record_provider_run(
                    data_type="belong_boards",
                    provider=fetcher.name,
                    operation="get_belong_board",
                    success=False,
                    latency_ms=int((self.read_time().time() - start) * 1000),
                    error_type="empty",
                    error_message="empty belong boards",
                    fallback_to=fallback_to,
                    record_count=0,
                )
            except Exception as e:
                error_type, error_reason = self.call_summarize_exception(e)
                self.call_record_provider_run(
                    data_type="belong_boards",
                    provider=fetcher.name,
                    operation="get_belong_board",
                    success=False,
                    latency_ms=int((self.read_time().time() - start) * 1000),
                    error_type=error_type,
                    error_message=error_reason,
                    fallback_to=fallback_to,
                )
                self.read_logger().debug(f"[{fetcher.name}] 获取所属板块失败: {e}")
                continue
        return []

    def get_sector_rankings_with_meta(
        self,
        n: int = 5,
    ) -> Tuple[List[Dict], List[Dict], List[Dict[str, Any]], str]:
        """Get sector rankings with ordered fallback chain metadata."""
        source_chain: List[Dict[str, Any]] = []
        last_error = ""

        start = self.read_time().time()
        try:
            from data_provider.sector.base import SectorRankingRequest

            result = self.use_get_sector_manager().get_sector_rankings(SectorRankingRequest(limit=n))
            duration_ms = int((self.read_time().time() - start) * 1000)
            if result.top_sectors is not None and result.bottom_sectors is not None:
                source_chain.append(
                    {
                        "provider": f"data_provider.sector:{result.source or 'eastmoney'}",
                        "result": "ok",
                        "duration_ms": duration_ms,
                    }
                )
                self.read_logger().info("[data_provider.sector] 获取板块排行成功")
                return result.top_sectors, result.bottom_sectors, source_chain, ""
        except Exception as e:
            error_type, error_reason = self.call_summarize_exception(e)
            duration_ms = int((self.read_time().time() - start) * 1000)
            last_error = f"data_provider.sector ({error_type}) {error_reason}"
            source_chain.append(
                {
                    "provider": "data_provider.sector",
                    "result": "failed",
                    "duration_ms": duration_ms,
                    "error": error_reason,
                }
            )
            self.read_logger().warning("[data_provider.sector] 获取板块排行失败: %s", error_reason)

        # 直接遍历管理器已经按 priority 排好序的数据源列表
        for fetcher in self.current_fetchers():
            if not hasattr(fetcher, "get_sector_rankings"):
                continue

            start = self.read_time().time()
            try:
                data = fetcher.get_sector_rankings(n)
                duration_ms = int((self.read_time().time() - start) * 1000)
                if data and data[0] is not None and data[1] is not None:
                    source_chain.append(
                        {
                            "provider": fetcher.name,
                            "result": "ok",
                            "duration_ms": duration_ms,
                        }
                    )
                    self.read_logger().info(f"[{fetcher.name}] 获取板块排行成功")
                    return data[0], data[1], source_chain, ""

                last_error = f"{fetcher.name}返回空结果"
                source_chain.append(
                    {
                        "provider": fetcher.name,
                        "result": "empty",
                        "duration_ms": duration_ms,
                        "error": last_error,
                    }
                )
            except Exception as e:
                error_type, error_reason = self.call_summarize_exception(e)
                last_error = f"{fetcher.name} ({error_type}) {error_reason}"
                duration_ms = int((self.read_time().time() - start) * 1000)
                source_chain.append(
                    {
                        "provider": fetcher.name,
                        "result": "failed",
                        "duration_ms": duration_ms,
                        "error": error_reason,
                    }
                )
                self.read_logger().warning(f"[{fetcher.name}] 获取板块排行失败: {error_reason}")

        return [], [], source_chain, last_error

    def get_sector_rankings(self, n: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """获取板块涨跌榜（自动切换数据源）"""
        # 按需求固定回退顺序：Akshare(EM) -> Akshare(Sina) -> Tushare -> Efinance
        top, bottom, _, last_error = self.use_get_sector_rankings_with_meta(n)
        if top or bottom:
            return top, bottom
        self.read_logger().warning(f"[板块排行] 所有数据源均失败，最终错误: {last_error}")
        return [], []

    def get_concept_rankings(self, n: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """获取概念/题材涨跌榜（自动切换数据源）。"""
        try:
            normalized_n = int(n)
        except (TypeError, ValueError):
            normalized_n = 5
        if normalized_n <= 0:
            normalized_n = 5

        last_error = ""
        now = self.read_time().monotonic()

        with self.class_concept_rankings_cache_lock():
            cached = self.class_concept_rankings_cache().get(normalized_n)
            if cached and cached[0] > now:
                self.read_logger().debug("[概念排行] 命中共享缓存 n=%s", normalized_n)
                return self.use_copy_ranking_rows(cached[1]), self.use_copy_ranking_rows(cached[2])

            top: List[Dict] = []
            bottom: List[Dict] = []
            for fetcher in self.use_get_fetchers_snapshot():
                try:
                    data = fetcher.get_concept_rankings(normalized_n)
                    if data and (data[0] or data[1]):
                        top = data[0] or []
                        bottom = data[1] or []
                        self.read_logger().info(f"[{fetcher.name}] 获取概念排行成功")
                        break
                    last_error = f"{fetcher.name}返回空结果"
                except Exception as e:
                    error_type, error_reason = self.call_summarize_exception(e)
                    last_error = f"{fetcher.name} ({error_type}) {error_reason}"
                    self.read_logger().warning(f"[{fetcher.name}] 获取概念排行失败: {error_reason}")

            if not top and not bottom and last_error:
                self.read_logger().warning(f"[概念排行] 所有数据源均失败，最终错误: {last_error}")

            ttl = (
                self.class_concept_rankings_cache_ttl_seconds()
                if top or bottom
                else self.class_concept_rankings_empty_cache_ttl_seconds()
            )
            cached_top = self.use_copy_ranking_rows(top)
            cached_bottom = self.use_copy_ranking_rows(bottom)
            self.class_concept_rankings_cache()[normalized_n] = (
                self.read_time().monotonic() + ttl,
                cached_top,
                cached_bottom,
            )
            return self.use_copy_ranking_rows(cached_top), self.use_copy_ranking_rows(cached_bottom)

    def get_hot_stocks(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取市场人气股榜（自动切换数据源）。"""
        last_error = ""
        for fetcher in self.current_fetchers():
            try:
                data = fetcher.get_hot_stocks(n)
                if data:
                    self.read_logger().info(f"[{fetcher.name}] 获取人气股成功")
                    return data[:n]
                last_error = f"{fetcher.name}返回空结果"
            except Exception as e:
                error_type, error_reason = self.call_summarize_exception(e)
                last_error = f"{fetcher.name} ({error_type}) {error_reason}"
                self.read_logger().warning(f"[{fetcher.name}] 获取人气股失败: {error_reason}")
        if last_error:
            self.read_logger().warning(f"[人气股] 所有数据源均失败，最终错误: {last_error}")
        return []


def is_missing_board_value(value: Any, *, use_try_scalar_isna) -> bool:
    """Return True when a board field value should be treated as missing."""
    if value is None:
        return True
    is_missing = use_try_scalar_isna(value, "board_value")
    if is_missing is True:
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "null", "na", "n/a"}



def normalize_belong_boards(raw_data: Any, *, use_is_missing_board_value) -> List[Dict[str, Any]]:
    """Normalize belong-board results from heterogeneous providers."""
    if use_is_missing_board_value(raw_data):
        return []

    normalized: List[Dict[str, Any]] = []
    dedupe = set()

    if isinstance(raw_data, pd.DataFrame):
        if raw_data.empty:
            return []
        name_col = next(
            (
                col
                for col in raw_data.columns
                if str(col) in {"板块名称", "板块", "所属板块", "板块名", "name", "industry"}
            ),
            None,
        )
        code_col = next(
            (
                col
                for col in raw_data.columns
                if str(col) in {"板块代码", "代码", "code"}
            ),
            None,
        )
        type_col = next(
            (
                col
                for col in raw_data.columns
                if str(col) in {"板块类型", "类别", "type"}
            ),
            None,
        )
        if name_col is None:
            return []
        for _, row in raw_data.iterrows():
            board_name_raw = row.get(name_col, "")
            if use_is_missing_board_value(board_name_raw):
                continue
            board_name = str(board_name_raw).strip()
            if board_name in dedupe:
                continue
            dedupe.add(board_name)
            item = {"name": board_name}
            if code_col is not None:
                board_code_raw = row.get(code_col, "")
                if not use_is_missing_board_value(board_code_raw):
                    item["code"] = str(board_code_raw).strip()
            if type_col is not None:
                board_type_raw = row.get(type_col, "")
                if not use_is_missing_board_value(board_type_raw):
                    item["type"] = str(board_type_raw).strip()
            normalized.append(item)
        return normalized

    if isinstance(raw_data, dict):
        raw_data = [raw_data]

    if isinstance(raw_data, (list, tuple, set)):
        for item in raw_data:
            if isinstance(item, dict):
                board_name_raw = (
                    item.get("name")
                    or item.get("board_name")
                    or item.get("板块名称")
                    or item.get("板块")
                    or item.get("所属板块")
                    or item.get("板块名")
                    or item.get("industry")
                    or item.get("行业")
                )
                if use_is_missing_board_value(board_name_raw):
                    continue
                board_name = str(board_name_raw).strip()
                if board_name in dedupe:
                    continue
                dedupe.add(board_name)
                normalized_item: Dict[str, Any] = {"name": board_name}
                code_raw = (
                    item.get("code")
                    or item.get("板块代码")
                    or item.get("代码")
                )
                if not use_is_missing_board_value(code_raw):
                    normalized_item["code"] = str(code_raw).strip()
                type_raw = (
                    item.get("type")
                    or item.get("板块类型")
                    or item.get("类别")
                )
                if not use_is_missing_board_value(type_raw):
                    normalized_item["type"] = str(type_raw).strip()
                normalized.append(normalized_item)
                continue
            if use_is_missing_board_value(item):
                continue
            board_name = str(item).strip()
            if board_name in dedupe:
                continue
            dedupe.add(board_name)
            normalized.append({"name": board_name})
        return normalized

    if not use_is_missing_board_value(raw_data):
        board_name = str(raw_data).strip()
        return [{"name": board_name}]
    return []



def copy_ranking_rows(rows: List[Dict]) -> List[Dict]:
    """复制排行行数据。"""
    return [dict(row) if isinstance(row, dict) else row for row in rows or []]

