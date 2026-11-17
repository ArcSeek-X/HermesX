"""Agent-to-analysis mapping without persistence, model calls or pipeline state."""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from src.domain.analysis.result import AnalysisResult
from src.application.analysis.result_policy import populate_decision_action_fields
from src.domain.analysis import pipeline_rules as _pipeline_rules
from src.domain.shared.report_language import (
    get_unknown_text,
    infer_decision_type_from_advice,
    localize_confidence_level,
    localize_operation_advice,
)
from src.domain.shared.enums import ReportType
from src.domain.analysis.stock_analyzer import TrendAnalysisResult

logger = logging.getLogger("src.application.analysis.pipeline")


class AgentResultMapper:
    """Convert Agent output and trend fallbacks into the shared analysis result."""

    def __init__(self, report_language: str):
        """构造 Agent 结果映射器：保存报告语言。"""
        self.report_language = report_language

    def agent_result_to_analysis_result(
        self,
        agent_result,
        code: str,
        stock_name: str,
        report_type: ReportType,
        query_id: str,
        trend_result: Optional[TrendAnalysisResult] = None,
    ) -> AnalysisResult:
        """
        将 AgentResult 转换为 AnalysisResult。
        """
        report_language = self.report_language
        dash = None
        result = AnalysisResult(
            code=code,
            name=stock_name,
            sentiment_score=50,
            trend_prediction=get_unknown_text(report_language),
            operation_advice=localize_operation_advice("观望", report_language),
            confidence_level=localize_confidence_level("medium", report_language),
            report_language=report_language,
            success=agent_result.success,
            error_message=agent_result.error or None,
            data_sources=f"agent:{agent_result.provider}",
            model_used=agent_result.model or None,
        )

        if agent_result.success and agent_result.dashboard:
            dash = agent_result.dashboard
            ai_stock_name = str(dash.get("stock_name", "")).strip()
            if ai_stock_name and self.is_placeholder_stock_name(stock_name, code):
                result.name = ai_stock_name

            nested_dashboard = dash.get("dashboard") if isinstance(dash, dict) else None

            raw_score = self.agent_dashboard_value(
                dash,
                nested_dashboard,
                "sentiment_score",
                scalar=True,
            )
            if self.is_agent_field_missing(raw_score, scalar=True):
                fallback_score = self.trend_score_fallback(trend_result)
                if fallback_score is not None:
                    result.sentiment_score = fallback_score
                    self.mark_trend_fallback_source(result)
            else:
                result.sentiment_score = self.safe_int(raw_score, 50)

            raw_trend = self.agent_dashboard_value(
                dash,
                nested_dashboard,
                "trend_prediction",
                scalar=True,
                expect_text=True,
            )
            if self.is_agent_field_missing(raw_trend, scalar=True, expect_text=True):
                trend_label = self.trend_label_fallback(
                    trend_result,
                    report_language,
                )
                if trend_label:
                    result.trend_prediction = trend_label
                    self.mark_trend_fallback_source(result)
            else:
                result.trend_prediction = str(raw_trend)

            raw_advice = self.agent_dashboard_value(
                dash,
                nested_dashboard,
                "operation_advice",
                scalar=True,
                allow_dict=True,
                expect_text=True,
            )
            extracted_advice = ""
            if isinstance(raw_advice, dict):
                # LLM may return {"no_position": "...", "has_position": "..."}
                extracted_advice = self.extract_advice_text_from_dict(raw_advice)
                if extracted_advice:
                    result.operation_advice = localize_operation_advice(
                        extracted_advice,
                        report_language,
                    )
                else:
                    signal_label = self.trend_signal_fallback(
                        trend_result,
                        report_language,
                    )
                    if signal_label:
                        result.operation_advice = signal_label
                        self.mark_trend_fallback_source(result)
            elif not self.is_agent_field_missing(
                raw_advice,
                scalar=True,
                allow_dict=True,
                expect_text=True,
            ):
                result.operation_advice = (
                    str(raw_advice) if raw_advice else (localize_operation_advice("观望", report_language))
                )
            else:
                signal_label = self.trend_signal_fallback(trend_result, report_language)
                if signal_label:
                    result.operation_advice = signal_label
                    self.mark_trend_fallback_source(result)
            from src.application.agent.protocols import normalize_decision_signal

            raw_decision = self.agent_dashboard_value(
                dash,
                nested_dashboard,
                "decision_type",
                scalar=True,
                expect_text=True,
            )
            if self.is_agent_field_missing(raw_decision, scalar=True, expect_text=True):
                trend_decision = self.trend_decision_fallback(trend_result)
                decision_from_advice = infer_decision_type_from_advice(
                    result.operation_advice,
                    default="",
                )
                if decision_from_advice:
                    result.decision_type = decision_from_advice
                    if (
                        self.is_agent_field_missing(
                            raw_advice,
                            scalar=True,
                            allow_dict=True,
                            expect_text=True,
                        )
                        and not extracted_advice
                        and trend_decision
                    ):
                        self.mark_trend_fallback_source(result)
                else:
                    result.decision_type = trend_decision or "hold"
                    if trend_decision:
                        self.mark_trend_fallback_source(result)
            else:
                result.decision_type = normalize_decision_signal(raw_decision)
            result.confidence_level = localize_confidence_level(
                self.agent_dashboard_value(dash, nested_dashboard, "confidence_level") or result.confidence_level,
                report_language,
            )
            raw_summary = self.agent_dashboard_value(
                dash,
                nested_dashboard,
                "analysis_summary",
                scalar=True,
                expect_text=True,
            )
            if not self.is_agent_field_missing(raw_summary, scalar=True, expect_text=True):
                result.analysis_summary = str(raw_summary)
            else:
                result.analysis_summary = self.summary_fallback_from_result(result, report_language)
            top_level_phase_decision = dash.get("phase_decision") if isinstance(dash, dict) else None
            if isinstance(nested_dashboard, dict) and isinstance(top_level_phase_decision, dict):
                nested_dashboard = dict(nested_dashboard)
                nested_dashboard.setdefault("phase_decision", top_level_phase_decision)

            # The AI returns a top-level dict that contains a nested 'dashboard' sub-key
            # with core_conclusion / battle_plan / intelligence.  AnalysisResult's helper
            # methods (get_sniper_points, get_core_conclusion, etc.) expect that inner
            # structure, so we unwrap it here.
            result.dashboard = nested_dashboard or dash
            self.backfill_agent_dashboard_fields(result, trend_result, report_language)
        else:
            self.apply_trend_fallback(result, trend_result, report_language)
            if trend_result is not None:
                result.analysis_summary = result.analysis_summary or self.summary_fallback_from_result(
                    result, report_language
                )
                self.backfill_agent_dashboard_fields(result, trend_result, report_language)
            if not result.error_message:
                result.error_message = (
                    "Agent failed to generate a valid decision dashboard"
                    if report_language == "en"
                    else (
                        "에이전트가 유효한 결정 대시보드를 생성하지 못했습니다"
                        if report_language == "ko"
                        else "Agent 未能生成有效的决策仪表盘"
                    )
                )

        explicit_action = dash.get("action") if isinstance(dash, dict) else None
        if explicit_action is None and isinstance(getattr(result, "dashboard", None), dict):
            explicit_action = result.dashboard.get("action")
        return populate_decision_action_fields(result, explicit_action=explicit_action)

    @classmethod
    def agent_dashboard_value(
        cls,
        dash: Dict[str, Any],
        nested_dashboard: Any,
        key: str,
        *,
        scalar: bool = False,
        allow_dict: bool = False,
        expect_text: bool = False,
    ) -> Any:
        """Read a scalar from top-level agent payload, then nested dashboard fallback."""
        value = dash.get(key) if isinstance(dash, dict) else None
        if isinstance(nested_dashboard, dict) and cls.is_agent_field_missing(
            value,
            scalar=scalar,
            allow_dict=allow_dict,
            expect_text=expect_text,
        ):
            nested_value = nested_dashboard.get(key)
            if not cls.is_agent_field_missing(
                nested_value,
                scalar=scalar,
                allow_dict=allow_dict,
                expect_text=expect_text,
            ):
                value = nested_value
        return value

    @classmethod
    def extract_advice_text_from_dict(cls, raw_advice: dict) -> str:
        """从建议字典中提取可读建议文本。"""
        return _pipeline_rules.extract_advice_text_from_dict(raw_advice)

    @classmethod
    def is_agent_placeholder_text(cls, text: str) -> bool:
        """判断文本是否为 Agent 占位符内容。"""
        return _pipeline_rules.is_agent_placeholder_text(text)

    @classmethod
    def is_agent_field_missing(
        cls,
        value: Any,
        *,
        scalar: bool = False,
        allow_dict: bool = False,
        expect_text: bool = False,
    ) -> bool:
        """判断 Agent 结果字段是否缺失或无效。"""
        return _pipeline_rules.is_agent_field_missing(
            value,
            scalar=scalar,
            allow_dict=allow_dict,
            expect_text=expect_text,
        )

    @staticmethod
    def trend_score_fallback(trend_result: Optional[TrendAnalysisResult]) -> Optional[int]:
        """从技术面结果回退得到趋势评分。"""
        return _pipeline_rules.trend_score_fallback(trend_result)

    @classmethod
    def trend_label_fallback(
        cls,
        trend_result: Optional[TrendAnalysisResult],
        report_language: str = "zh",
    ) -> str:
        """从技术面结果回退得到趋势标签。"""
        return _pipeline_rules.trend_label_fallback(trend_result, report_language)

    @classmethod
    def trend_signal_fallback(
        cls,
        trend_result: Optional[TrendAnalysisResult],
        report_language: str = "zh",
    ) -> str:
        """从技术面结果回退得到趋势信号。"""
        return _pipeline_rules.trend_signal_fallback(trend_result, report_language)

    @staticmethod
    def trend_decision_fallback(trend_result: Optional[TrendAnalysisResult]) -> Optional[str]:
        """从技术面结果回退得到趋势决策。"""
        return _pipeline_rules.trend_decision_fallback(trend_result)

    @staticmethod
    def mark_trend_fallback_source(result: AnalysisResult) -> None:
        """标记结果中的趋势字段来自回退逻辑。"""
        if "trend:fallback" in (result.data_sources or ""):
            return
        result.data_sources = f"{result.data_sources},trend:fallback" if result.data_sources else "trend:fallback"

    @staticmethod
    def summary_fallback_from_result(result: AnalysisResult, report_language: str) -> str:
        """按报告语言从结果生成回退摘要。"""
        return _pipeline_rules.summary_fallback_from_result(result, report_language)

    def backfill_agent_dashboard_fields(
        self,
        result: AnalysisResult,
        trend_result: Optional[TrendAnalysisResult],
        report_language: str,
    ) -> None:
        """回填 Agent 仪表盘缺失字段。"""
        if not isinstance(result.dashboard, dict):
            result.dashboard = {}
        dashboard = result.dashboard

        for key in (
            "sentiment_score",
            "trend_prediction",
            "operation_advice",
            "decision_type",
            "confidence_level",
            "analysis_summary",
        ):
            current = dashboard.get(key)
            if key == "sentiment_score":
                if self.is_agent_field_missing(current, scalar=True):
                    dashboard[key] = getattr(result, key)
            elif self.is_agent_field_missing(current, scalar=True, expect_text=True):
                dashboard[key] = getattr(result, key)

        core = dashboard.get("core_conclusion")
        if not isinstance(core, dict):
            core = {}
            dashboard["core_conclusion"] = core
        if self.is_agent_field_missing(core.get("one_sentence"), scalar=True):
            core["one_sentence"] = (
                result.analysis_summary
                or self.summary_fallback_from_result(
                    result,
                    report_language,
                )
                or (
                    "Analysis pending"
                    if report_language == "en"
                    else "분석 보완 예정" if report_language == "ko" else "分析待补充"
                )
            )

        intelligence = dashboard.get("intelligence")
        if not isinstance(intelligence, dict):
            intelligence = {}
            dashboard["intelligence"] = intelligence
        risk_alerts = intelligence.get("risk_alerts")
        if (
            "risk_alerts" not in intelligence
            or self.is_agent_field_missing(risk_alerts)
            or not isinstance(risk_alerts, list)
        ):
            risk_factors = getattr(trend_result, "risk_factors", None) or []
            intelligence["risk_alerts"] = list(risk_factors)

        if result.decision_type in ("buy", "hold"):
            battle = dashboard.get("battle_plan")
            if not isinstance(battle, dict):
                battle = {}
                dashboard["battle_plan"] = battle
            sniper_points = battle.get("sniper_points")
            if not isinstance(sniper_points, dict):
                sniper_points = {}
                battle["sniper_points"] = sniper_points
            if self.is_agent_field_missing(sniper_points.get("stop_loss"), scalar=True):
                sniper_points["stop_loss"] = self.stop_loss_fallback_from_trend(
                    trend_result,
                    report_language,
                )

    @staticmethod
    def stop_loss_fallback_from_trend(
        trend_result: Optional[TrendAnalysisResult],
        report_language: str,
    ) -> Any:
        """从技术面结果回退得到止损价。"""
        return _pipeline_rules.stop_loss_fallback_from_trend(trend_result, report_language)

    @classmethod
    def apply_trend_fallback(
        cls,
        result: AnalysisResult,
        trend_result: Optional[TrendAnalysisResult],
        report_language: str,
    ) -> None:
        """对最终结果应用趋势字段回退策略。"""
        if trend_result is None:
            result.sentiment_score = 50
            result.operation_advice = localize_operation_advice("观望", report_language)
            return

        score = getattr(trend_result, "signal_score", None)
        try:
            numeric_score = int(score)
        except (TypeError, ValueError):
            numeric_score = 50
        result.sentiment_score = numeric_score if numeric_score > 0 else 50

        trend_label = cls.trend_label_fallback(trend_result, report_language)
        if trend_label:
            result.trend_prediction = trend_label

        buy_signal = getattr(trend_result, "buy_signal", None)
        signal_label = cls.trend_signal_fallback(
            trend_result,
            report_language,
        )
        if signal_label:
            result.operation_advice = signal_label
        else:
            result.operation_advice = localize_operation_advice("观望", report_language)

        from src.application.agent.protocols import normalize_decision_signal

        signal_name = getattr(buy_signal, "name", "").lower()
        signal_to_decision = {
            "strong_buy": "buy",
            "buy": "buy",
            "hold": "hold",
            "wait": "hold",
            "sell": "sell",
            "strong_sell": "sell",
        }
        result.decision_type = signal_to_decision.get(signal_name, result.decision_type or "hold")
        result.decision_type = normalize_decision_signal(result.decision_type)
        result.data_sources = f"{result.data_sources},trend:fallback" if result.data_sources else "trend:fallback"

    @staticmethod
    def is_placeholder_stock_name(name: str, code: str) -> bool:
        """Return True when the stock name is missing or placeholder-like."""
        return _pipeline_rules.is_placeholder_stock_name(name, code)

    @staticmethod
    def safe_int(value: Any, default: int = 50) -> int:
        """安全地将值转换为整数。"""
        return _pipeline_rules.safe_int(value, default)
