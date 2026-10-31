# -*- coding: utf-8 -*-
"""分析历史查询用例。

职责边界：

- 端点不再持有数据库句柄，查询/删除/汇总一律经本用例；
- 读模型重建（详情、诊断、运行流、Markdown）仍由 ``src.application.history.read_model.HistoryService``
  承担，本用例只负责把端口注入进去并做错误语义转换；个股栏复用其代码/时间戳/
  阶段摘要辅助时，只调用 ``HistoryService`` 的公开方法（跨层私有成员访问被架构守卫拦截）。
- 个股栏去重、按代码批量删除这两段原本内联在端点里的持久化循环收进本层。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from src.application.history.errors import (
    HistoryMarkdownGenerationError,
    HistoryValidationError,
)
from src.application.history.ports import HistoryRepositoryPort, StockCodeNormalizerPort
from src.domain.shared.report_language import normalize_report_language
from src.domain.decision.action import build_action_fields
from src.application.history.read_model import HistoryService, MarkdownReportGenerationError
from src.utils.data_processing import normalize_model_used, parse_json_field

_DELETE_BY_CODE_BATCH_SIZE = 10_000


class HistoryQueryService:
    """分析历史读取与删除的用例入口。"""

    def __init__(
        self,
        repository: HistoryRepositoryPort,
        code_normalizer: StockCodeNormalizerPort,
    ) -> None:
        self._repository = repository
        self._code_normalizer = code_normalizer

    def _history(self) -> HistoryService:
        """``HistoryService`` 只持有数据源引用，按需构造即可。"""
        return HistoryService(self._repository)

    # --- 列表 / 详情 / 诊断 / 运行流 / 新闻 / Markdown -------------------------

    def list_records(
        self,
        *,
        stock_code: Optional[str] = None,
        report_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """分页查询历史列表（筛选与日期解析沿用 ``HistoryService`` 的既有语义）。"""
        return self._history().get_history_list(
            stock_code=stock_code,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit,
        )

    def get_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        """按主键 ID 或 ``query_id`` 解析并返回详情。"""
        return self._history().resolve_and_get_detail(record_id)

    def get_diagnostics(self, record_id: str) -> Optional[Dict[str, Any]]:
        """返回运行诊断摘要（记录不存在时返回 ``None``）。"""
        return self._history().resolve_and_get_diagnostics(record_id)

    def get_run_flow(
        self,
        record_id: str,
        *,
        code: Optional[str] = None,
        report_type: Optional[str] = None,
    ) -> Optional[Any]:
        """返回运行流快照（记录不存在时返回 ``None``）。

        ``code`` / ``report_type`` 用于区分同一 ``query_id`` 下的多份记录（批量分析
        会共享 query_id）；历史详情页不传，行为与迁移前一致。
        """
        return self._history().resolve_and_get_run_flow(
            record_id,
            code=code,
            report_type=report_type,
        )

    def get_news(self, record_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """返回关联新闻；记录不存在或无新闻时返回空列表。"""
        return self._history().resolve_and_get_news(record_id=record_id, limit=limit)

    def get_markdown(self, record_id: str) -> Optional[str]:
        """返回 Markdown 报告；记录不存在返回 ``None``。

        报告重建失败时抛 :class:`HistoryMarkdownGenerationError`（端点映射 500）。
        """
        try:
            return self._history().get_markdown_report(record_id)
        except MarkdownReportGenerationError as exc:
            raise HistoryMarkdownGenerationError(exc.message or "报告重建失败") from exc

    def get_latest_fundamental_snapshot(
        self,
        query_id: str,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        """详情页兜底基本面快照。"""
        return self._repository.get_latest_fundamental_snapshot(query_id=query_id, code=code)

    def get_latest_by_query_id(
        self,
        query_id: str,
        *,
        code: Optional[str] = None,
        report_type: Optional[str] = None,
    ) -> Optional[Any]:
        """按 ``query_id`` 取最新一条历史记录（可附加代码 / 报告类型过滤）。

        返回持久化记录对象，调用方按既有字段读取（``raw_result`` /
        ``context_snapshot`` / ``code`` 等）。批量分析会让同一 ``query_id`` 落多条
        记录，因此只取 ``created_at`` 最新的一条；记录不存在返回 ``None``。
        """
        return self._repository.get_latest_analysis_by_query_id(
            query_id,
            code=code,
            report_type=report_type,
        )

    # --- 删除 ---------------------------------------------------------------

    def delete_records(self, record_ids: List[int]) -> int:
        """按主键批量删除。"""
        return self._history().delete_history_records(record_ids)

    def delete_by_code(self, stock_code: str) -> int:
        """按股票代码分批删除全部历史记录（代码变体归一化匹配）。"""
        candidates = HistoryService.history_code_filter_candidates(stock_code)
        if not candidates:
            raise HistoryValidationError("stock_code 不能为空", error_code="invalid_request")

        deleted = 0
        while True:
            records, _ = self._repository.get_analysis_history_paginated(
                code=candidates,
                limit=_DELETE_BY_CODE_BATCH_SIZE,
            )
            record_ids = [record.id for record in records if record.id is not None]
            if not record_ids:
                break

            batch_deleted = self._repository.delete_analysis_history_records(record_ids)
            if batch_deleted == 0:
                raise RuntimeError("history deletion made no progress")
            deleted += batch_deleted

            if len(records) < _DELETE_BY_CODE_BATCH_SIZE:
                break

        return deleted

    # --- 个股栏 -------------------------------------------------------------

    def list_stock_bar(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """返回每只股票的最新一条分析摘要（按归一化代码去重）。"""
        history = self._history()
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None

        # 多取一些以抵消归一化去重造成的收缩（如 002460 与 002460.SZ 合并为一条）。
        fetch_limit = min(limit * 3, 500)
        records = self._repository.get_distinct_stocks_from_history(
            start_date=start,
            end_date=end,
            limit=fetch_limit,
        )

        seen: Dict[str, Any] = {}
        for record in records:
            display_code = history.display_stock_code(record.code or "")
            norm_code = self._code_normalizer.normalize(display_code)
            if norm_code not in seen or record.id > seen[norm_code].id:
                seen[norm_code] = record

        items: List[Dict[str, Any]] = []
        for record in seen.values():
            raw_result = parse_json_field(getattr(record, "raw_result", None))
            model_used = raw_result.get("model_used") if isinstance(raw_result, dict) else None
            sentiment_score = _coalesce_int(
                record.sentiment_score,
                _raw_result_value(raw_result, "sentiment_score"),
            )
            operation_advice = _coalesce_text(
                record.operation_advice,
                _raw_result_value(raw_result, "operation_advice"),
            )
            action_fields = build_action_fields(
                operation_advice=operation_advice,
                explicit_action=_raw_result_value(raw_result, "action"),
                report_type=record.report_type,
                report_language=normalize_report_language(
                    _raw_result_value(raw_result, "report_language")
                ),
                sentiment_score=sentiment_score,
                guardrail_reason=_extract_guardrail_reason(raw_result),
                align_with_score=True,
            )

            display_stock_code = history.display_stock_code(record.code)
            analysis_count = self._repository.get_analysis_history_paginated(
                code=HistoryService.history_code_filter_candidates(display_stock_code),
                limit=1,
            )[1]
            items.append(
                {
                    "id": record.id,
                    "stock_code": display_stock_code,
                    "stock_name": record.name,
                    "report_type": record.report_type,
                    "sentiment_score": sentiment_score,
                    "operation_advice": operation_advice,
                    "action": action_fields["action"],
                    "action_label": action_fields["action_label"],
                    "analysis_count": analysis_count,
                    "last_analysis_time": history.serialize_created_at(record.created_at),
                    "model_used": normalize_model_used(model_used),
                    "market_phase_summary": history.display_market_phase_summary(
                        record.code,
                        getattr(record, "context_snapshot", None),
                    ),
                }
            )

        return items[:limit]


# --- 读模型辅助（原 api/v1/endpoints/history.py 内联实现） -------------------


def _raw_result_value(raw_result: Any, key: str) -> Any:
    if not isinstance(raw_result, dict):
        return None

    value = raw_result.get(key)
    if value is not None and value != "":
        return value

    for container_key in ("summary", "dashboard"):
        container = raw_result.get(container_key)
        if isinstance(container, dict):
            nested_value = container.get(key)
            if nested_value is not None and nested_value != "":
                return nested_value

    return None


def _coalesce_text(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _coalesce_int(*values: Any) -> Optional[int]:
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def _extract_guardrail_reason(raw_result: Any) -> Optional[str]:
    if not isinstance(raw_result, dict):
        return None
    for reason in (
        raw_result.get("guardrail_reason"),
        raw_result.get("downgrade_reason"),
        raw_result.get("decision_score_guardrail_reason"),
    ):
        if reason is not None:
            text = str(reason).strip()
            if text:
                return text

    metadata = raw_result.get("metadata")
    if isinstance(metadata, dict):
        metadata_reason = metadata.get("guardrail_reason") or metadata.get("downgrade_reason")
        if metadata_reason is not None:
            text = str(metadata_reason).strip()
            if text:
                return text
    return None
