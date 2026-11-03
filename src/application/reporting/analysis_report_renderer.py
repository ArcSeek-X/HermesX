"""Analysis report formatting; notification routing and sender state stay in notification."""

from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from src.application.market.phase_summary import format_public_market_status_line, format_public_phase_pack_excerpt
from src.domain.shared.report_language import (
    get_localized_stock_name,
    get_report_labels,
    get_signal_level,
    get_chip_unavailable_reason,
    is_chip_structure_unavailable,
    localize_chip_health,
    localize_conflict_severity,
    localize_consensus_level,
    localize_strategy_signal,
    localize_strategy_synthesis_summary,
    localize_trend_prediction,
    normalize_report_language,
    normalize_strategy_synthesis_payload,
    strategy_invalid_opinion_count,
)
from src.domain.decision.action import (
    display_action_fields_for_result,
    display_decision_type_for_result,
    display_operation_advice_for_result,
)
from src.utils.data_processing import (
    signal_attribution_has_content,
    signal_attribution_weight_items,
    normalize_model_used,
)
from src.domain.notification.rendering import (
    append_phase_decision_block as _append_phase_decision_block_impl,
    append_strategy_synthesis_block as _append_strategy_synthesis_block,
    clean_sniper_value as _clean_sniper_value_impl,
    escape_markdown_name as _escape_markdown_name,
    format_amount_cn as _format_amount_cn_impl,
    format_net_shares as _format_net_shares_impl,
    format_per_share as _format_per_share_impl,
    format_percent as _format_percent_impl,
    format_text as _format_text_impl,
    safe_float as _safe_float,
    source_display_name as _source_display_name_impl,
)
from src.domain.analysis.result import AnalysisResult

logger = logging.getLogger("src.application.notification.notification")


class AnalysisReportRenderer:
    """Render analysis reports using explicit configuration and shared history cache."""

    def __init__(self, *, config, show_llm_model, summary_only, history_compare_cache, runtime_config_provider):
        self._config = config
        self._report_show_llm_model = show_llm_model
        self._report_summary_only = summary_only
        self._history_compare_cache = history_compare_cache
        self._runtime_config_provider = runtime_config_provider

    def get_report_language(self, payload: Optional[Any] = None) -> str:
        """Resolve report language from result payload or global config."""
        if isinstance(payload, list):
            for item in payload:
                language = getattr(item, "report_language", None)
                if language:
                    return normalize_report_language(language)
        elif payload is not None:
            language = getattr(payload, "report_language", None)
            if language:
                return normalize_report_language(language)

        return normalize_report_language(getattr(self._runtime_config_provider(), "report_language", "zh"))

    def get_display_name(self, result: AnalysisResult, language: Optional[str] = None) -> str:
        report_language = normalize_report_language(language or self.get_report_language(result))
        return self.escape_md(get_localized_stock_name(result.name, result.code, report_language))

    def get_history_compare_context(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """Fetch and cache history comparison data for markdown rendering."""
        config = self._runtime_config_provider()
        history_compare_n = getattr(config, "report_history_compare_n", 0)
        if history_compare_n <= 0 or not results:
            return {"history_by_code": {}}

        report_language = self.get_report_language(results)

        cache_key = (
            history_compare_n,
            report_language,
            tuple(sorted((r.code, getattr(r, "query_id", "") or "") for r in results)),
        )
        if cache_key in self._history_compare_cache:
            return {"history_by_code": self._history_compare_cache[cache_key]}

        try:
            from src.application.history.comparison import get_signal_changes_batch

            exclude_ids = {r.code: r.query_id for r in results if getattr(r, "query_id", None)}
            codes = list(dict.fromkeys(r.code for r in results))
            history_by_code = get_signal_changes_batch(
                codes,
                limit=history_compare_n,
                exclude_query_ids=exclude_ids,
                report_language=report_language,
            )
        except Exception as e:
            logger.debug("History comparison skipped: %s", e)
            history_by_code = {}

        self._history_compare_cache[cache_key] = history_by_code
        return {"history_by_code": history_by_code}

    def collect_models_used(self, results: List[AnalysisResult]) -> List[str]:
        if not self.should_show_llm_model():
            return []
        models: List[str] = []
        for result in results:
            model = normalize_model_used(getattr(result, "model_used", None))
            if model:
                models.append(model)
        return list(dict.fromkeys(models))

    def public_phase_pack_excerpt(self, result: AnalysisResult, report_language: str) -> str:
        return format_public_phase_pack_excerpt(
            getattr(result, "market_phase_summary", None),
            getattr(result, "analysis_context_pack_overview", None),
            source=getattr(result, "analysis_visibility_source", None) or "evaluator_snapshot",
            report_language=report_language,
        )

    def public_market_status_line(self, results: List[AnalysisResult], report_language: str) -> str:
        for result in results or []:
            line = format_public_market_status_line(
                getattr(result, "market_phase_summary", None),
                report_language=report_language,
            )
            if line:
                return line
        return ""

    def append_market_status_line(
        self,
        lines: List[str],
        results: List[AnalysisResult],
        report_language: str,
    ) -> None:
        status_line = self.public_market_status_line(results, report_language)
        if status_line:
            lines.extend([status_line, ""])
        elif lines and lines[-1] != "":
            lines.append("")

    def should_show_llm_model(self) -> bool:
        return bool(getattr(self._config, "report_show_llm_model", self._report_show_llm_model))

    def generate_daily_report(self, results: List[AnalysisResult], report_date: Optional[str] = None) -> str:
        """
        生成 Markdown 格式的日报（详细版）

        Args:
            results: 分析结果列表
            report_date: 报告日期（默认今天）

        Returns:
            Markdown 格式的日报内容
        """
        if report_date is None:
            report_date = datetime.now().strftime("%Y-%m-%d")
        report_language = self.get_report_language(results)
        labels = get_report_labels(report_language)

        # 标题
        report_lines = [
            f"# 📅 {report_date} {labels['report_title']}",
            "",
            f"> {labels['analyzed_prefix']} **{len(results)}** {labels['stock_unit']} | "
            f"{labels['generated_at_label']}：{datetime.now().strftime('%H:%M:%S')}",
        ]
        self.append_market_status_line(report_lines, results, report_language)
        report_lines.extend(["---", ""])

        # 按评分排序（高分在前）
        sorted_results = sorted(results, key=lambda x: x.sentiment_score, reverse=True)

        buy_count, sell_count, hold_count = self.count_display_decisions(results, report_language)
        avg_score = sum(r.sentiment_score for r in results) / len(results) if results else 0

        report_lines.extend(
            [
                f"## 📊 {labels['summary_heading']}",
                "",
                "| 指标 | 数值 |",
                "|------|------|",
                f"| 🟢 {labels['buy_label']} | **{buy_count}** {labels['stock_unit_compact']} |",
                f"| 🟡 {labels['watch_label']} | **{hold_count}** {labels['stock_unit_compact']} |",
                f"| 🔴 {labels['sell_label']} | **{sell_count}** {labels['stock_unit_compact']} |",
                f"| 📈 {labels['avg_score_label']} | **{avg_score:.1f}** |",
                "",
                "---",
                "",
            ]
        )

        # Issue #262: summary_only 时仅输出摘要，跳过个股详情
        if self._report_summary_only:
            report_lines.extend([f"## 📊 {labels['summary_heading']}", ""])
            for r in sorted_results:
                signal_text, emoji, _ = self.get_signal_level(r)
                report_lines.append(
                    f"{emoji} **{self.get_display_name(r, report_language)}({r.code})**: "
                    f"{signal_text} | "
                    f"{labels['score_label']} {r.sentiment_score} | "
                    f"{localize_trend_prediction(r.trend_prediction, report_language)}"
                )
        else:
            report_lines.extend([f"## 📈 {labels['report_title']}", ""])
            # 逐个股票的详细分析
            for result in sorted_results:
                signal_text, emoji, _ = self.get_signal_level(result)
                confidence_stars = result.get_confidence_stars() if hasattr(result, "get_confidence_stars") else "⭐⭐"

                report_lines.extend(
                    [
                        f"### {emoji} {self.get_display_name(result, report_language)} ({result.code})",
                        "",
                        f"**{labels['action_advice_label']}：{signal_text}** | "
                        f"**{labels['score_label']}：{result.sentiment_score}** | "
                        f"**{labels['trend_label']}：{localize_trend_prediction(result.trend_prediction, report_language)}** | "
                        f"**Confidence：{confidence_stars}**",
                        "",
                    ]
                )
                self.append_market_snapshot(report_lines, result)

                # 核心看点
                if hasattr(result, "key_points") and result.key_points:
                    report_lines.extend(
                        [
                            f"**🎯 核心看点**：{result.key_points}",
                            "",
                        ]
                    )

                # 买入/卖出理由
                if hasattr(result, "buy_reason") and result.buy_reason:
                    report_lines.extend(
                        [
                            f"**💡 操作理由**：{result.buy_reason}",
                            "",
                        ]
                    )

                # 走势分析
                if hasattr(result, "trend_analysis") and result.trend_analysis:
                    report_lines.extend(
                        [
                            "#### 📉 走势分析",
                            f"{result.trend_analysis}",
                            "",
                        ]
                    )

                # 短期/中期展望
                outlook_lines = []
                if hasattr(result, "short_term_outlook") and result.short_term_outlook:
                    outlook_lines.append(f"- **短期（1-3日）**：{result.short_term_outlook}")
                if hasattr(result, "medium_term_outlook") and result.medium_term_outlook:
                    outlook_lines.append(f"- **中期（1-2周）**：{result.medium_term_outlook}")
                if outlook_lines:
                    report_lines.extend(
                        [
                            "#### 🔮 市场展望",
                            *outlook_lines,
                            "",
                        ]
                    )

                # 技术面分析
                tech_lines = []
                if result.technical_analysis:
                    tech_lines.append(f"**综合**：{result.technical_analysis}")
                if hasattr(result, "ma_analysis") and result.ma_analysis:
                    tech_lines.append(f"**均线**：{result.ma_analysis}")
                if hasattr(result, "volume_analysis") and result.volume_analysis:
                    tech_lines.append(f"**量能**：{result.volume_analysis}")
                if hasattr(result, "pattern_analysis") and result.pattern_analysis:
                    tech_lines.append(f"**形态**：{result.pattern_analysis}")
                if tech_lines:
                    report_lines.extend(
                        [
                            "#### 📊 技术面分析",
                            *tech_lines,
                            "",
                        ]
                    )

                # 基本面分析
                fund_lines = []
                if hasattr(result, "fundamental_analysis") and result.fundamental_analysis:
                    fund_lines.append(result.fundamental_analysis)
                if hasattr(result, "sector_position") and result.sector_position:
                    fund_lines.append(f"**板块地位**：{result.sector_position}")
                if hasattr(result, "company_highlights") and result.company_highlights:
                    fund_lines.append(f"**公司亮点**：{result.company_highlights}")
                if fund_lines:
                    report_lines.extend(
                        [
                            "#### 🏢 基本面分析",
                            *fund_lines,
                            "",
                        ]
                    )

                # 消息面/情绪面
                news_lines = []
                if result.news_summary:
                    news_lines.append(f"**新闻摘要**：{result.news_summary}")
                if hasattr(result, "market_sentiment") and result.market_sentiment:
                    news_lines.append(f"**市场情绪**：{result.market_sentiment}")
                if hasattr(result, "hot_topics") and result.hot_topics:
                    news_lines.append(f"**相关热点**：{result.hot_topics}")
                if news_lines:
                    report_lines.extend(
                        [
                            "#### 📰 消息面/情绪面",
                            *news_lines,
                            "",
                        ]
                    )

                # 综合分析
                if result.analysis_summary:
                    report_lines.extend(
                        [
                            "#### 📝 综合分析",
                            result.analysis_summary,
                            "",
                        ]
                    )

                # 风险提示
                if hasattr(result, "risk_warning") and result.risk_warning:
                    report_lines.extend(
                        [
                            f"⚠️ **风险提示**：{result.risk_warning}",
                            "",
                        ]
                    )

                # 数据来源说明
                if hasattr(result, "search_performed") and result.search_performed:
                    report_lines.append("*🔍 已执行联网搜索*")
                if hasattr(result, "data_sources") and result.data_sources:
                    report_lines.append(f"*📋 数据来源：{result.data_sources}*")

                # 错误信息（如果有）
                if not result.success and result.error_message:
                    report_lines.extend(
                        [
                            "",
                            f"❌ **分析异常**：{result.error_message[:100]}",
                        ]
                    )

                report_lines.extend(
                    [
                        "",
                        "---",
                        "",
                    ]
                )

        # 底部信息（去除免责声明）
        report_lines.extend(
            [
                "",
                f"*{labels['generated_at_label']}：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ]
        )

        return "\n".join(report_lines)

    @staticmethod
    def escape_md(name: str) -> str:
        """Escape markdown special characters in stock names (e.g. *ST → \\*ST)."""
        return _escape_markdown_name(name)

    @staticmethod
    def clean_sniper_value(value: Any) -> str:
        """Normalize sniper point values and remove redundant label prefixes."""
        return _clean_sniper_value_impl(value)

    def append_phase_decision_block(
        self,
        report_lines: List[str],
        dashboard: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        _append_phase_decision_block_impl(report_lines, dashboard, labels)

    def get_display_operation_advice(
        self,
        result: AnalysisResult,
        report_language: Optional[str] = None,
    ) -> str:
        return display_operation_advice_for_result(
            result,
            report_language=report_language or self.get_report_language(result),
        )

    def count_display_decisions(
        self,
        results: List[AnalysisResult],
        report_language: Optional[str] = None,
    ) -> Tuple[int, int, int]:
        language = report_language or self.get_report_language(results)
        buckets = [display_decision_type_for_result(result, report_language=language) for result in results]
        buy_count = sum(1 for bucket in buckets if bucket == "buy")
        sell_count = sum(1 for bucket in buckets if bucket == "sell")
        hold_count = len(buckets) - buy_count - sell_count
        return buy_count, sell_count, hold_count

    def get_signal_level(self, result: AnalysisResult) -> tuple:
        """Get display text and signal metadata from the resolved action."""
        report_language = self.get_report_language(result)
        display_fields = display_action_fields_for_result(
            result,
            report_language=report_language,
        )
        signal_advice = {
            "buy": "buy",
            "add": "buy",
            "hold": "hold",
            "reduce": "reduce",
            "sell": "sell",
            "watch": "watch",
            "avoid": "hold",
            "alert": "sell",
        }.get(display_fields["action"])
        _, emoji, signal_tag = get_signal_level(
            signal_advice or self.get_display_operation_advice(result, report_language),
            result.sentiment_score,
            report_language,
        )
        return (
            self.get_display_operation_advice(result, report_language),
            emoji,
            signal_tag,
        )

    def generate_dashboard_report(self, results: List[AnalysisResult], report_date: Optional[str] = None) -> str:
        """
        生成决策仪表盘格式的日报（详细版）

        格式：市场概览 + 重要信息 + 核心结论 + 数据透视 + 作战计划

        Args:
            results: 分析结果列表
            report_date: 报告日期（默认今天）

        Returns:
            Markdown 格式的决策仪表盘日报
        """
        config = self._runtime_config_provider()
        report_language = self.get_report_language(results)
        labels = get_report_labels(report_language)

        def _nlabel(en: str, zh: str, ko: str) -> str:
            if report_language == "en":
                return en
            if report_language == "ko":
                return ko
            return zh

        reason_label = _nlabel("Rationale", "操作理由", "판단 근거")
        risk_warning_label = _nlabel("Risk Warning", "风险提示", "리스크 경고")
        technical_heading = _nlabel("Technicals", "技术面", "기술적 분석")
        ma_label = _nlabel("Moving Averages", "均线", "이동평균")
        volume_analysis_label = _nlabel("Volume", "量能", "거래량")
        news_heading = _nlabel("News Flow", "消息面", "뉴스 흐름")
        if getattr(config, "report_renderer_enabled", False) and results:
            from src.application.reporting.report_renderer import render

            out = render(
                platform="markdown",
                results=results,
                report_date=report_date,
                summary_only=self._report_summary_only,
                extra_context={
                    **self.get_history_compare_context(results),
                    "report_language": report_language,
                },
            )
            if out:
                return out

        if report_date is None:
            report_date = datetime.now().strftime("%Y-%m-%d")

        # 按评分排序（高分在前）
        sorted_results = sorted(results, key=lambda x: x.sentiment_score, reverse=True)

        buy_count, sell_count, hold_count = self.count_display_decisions(results, report_language)

        report_lines = [
            f"# 🎯 {report_date} {labels['dashboard_title']}",
            "",
            f"> {labels['analyzed_prefix']} **{len(results)}** {labels['stock_unit']} | "
            f"🟢{labels['buy_label']}:{buy_count} 🟡{labels['watch_label']}:{hold_count} 🔴{labels['sell_label']}:{sell_count}",
        ]
        self.append_market_status_line(report_lines, results, report_language)

        # === 新增：分析结果摘要 (Issue #112) ===
        if results:
            report_lines.extend(
                [
                    f"## 📊 {labels['summary_heading']}",
                    "",
                ]
            )
            for r in sorted_results:
                signal_text, signal_emoji, _ = self.get_signal_level(r)
                display_name = self.get_display_name(r, report_language)
                report_lines.append(
                    f"{signal_emoji} **{display_name}({r.code})**: "
                    f"{signal_text} | "
                    f"{labels['score_label']} {r.sentiment_score} | "
                    f"{localize_trend_prediction(r.trend_prediction, report_language)}"
                )
            report_lines.extend(
                [
                    "",
                    "---",
                    "",
                ]
            )

        # 逐个股票的决策仪表盘（Issue #262: summary_only 时跳过详情）
        if not self._report_summary_only:
            for result in sorted_results:
                signal_text, signal_emoji, signal_tag = self.get_signal_level(result)
                dashboard = result.dashboard if hasattr(result, "dashboard") and result.dashboard else {}

                # 股票名称（优先使用 dashboard 或 result 中的名称，转义 *ST 等特殊字符）
                stock_name = self.get_display_name(result, report_language)

                report_lines.extend(
                    [
                        f"## {signal_emoji} {stock_name} ({result.code})",
                        "",
                    ]
                )
                # ========== 舆情与基本面概览（放在最前面）==========
                intel = dashboard.get("intelligence", {}) if dashboard else {}
                if intel:
                    report_lines.extend(
                        [
                            f"### 📰 {labels['info_heading']}",
                            "",
                        ]
                    )
                    # 舆情情绪总结
                    if intel.get("sentiment_summary"):
                        report_lines.append(f"**💭 {labels['sentiment_summary_label']}**: {intel['sentiment_summary']}")
                    # 业绩预期
                    if intel.get("earnings_outlook"):
                        report_lines.append(f"**📊 {labels['earnings_outlook_label']}**: {intel['earnings_outlook']}")
                    # 风险警报（醒目显示）
                    risk_alerts = intel.get("risk_alerts", [])
                    if risk_alerts:
                        report_lines.append("")
                        report_lines.append(f"**🚨 {labels['risk_alerts_label']}**:")
                        for alert in risk_alerts:
                            report_lines.append(f"- {alert}")
                    # 利好催化
                    catalysts = intel.get("positive_catalysts", [])
                    if catalysts:
                        report_lines.append("")
                        report_lines.append(f"**✨ {labels['positive_catalysts_label']}**:")
                        for cat in catalysts:
                            report_lines.append(f"- {cat}")
                    # 最新消息
                    if intel.get("latest_news"):
                        report_lines.append("")
                        report_lines.append(f"**📢 {labels['latest_news_label']}**: {intel['latest_news']}")
                    report_lines.append("")

                # ========== 核心结论 ==========
                core = dashboard.get("core_conclusion", {}) if dashboard else {}
                one_sentence = core.get("one_sentence", result.analysis_summary)
                time_sense = core.get("time_sensitivity", labels["default_time_sensitivity"])
                pos_advice = core.get("position_advice", {})

                report_lines.extend(
                    [
                        f"### 📌 {labels['core_conclusion_heading']}",
                        "",
                        f"**{signal_emoji} {signal_text}** | {localize_trend_prediction(result.trend_prediction, report_language)}",
                        "",
                        f"> **{labels['one_sentence_label']}**: {one_sentence}",
                        "",
                        f"⏰ **{labels['time_sensitivity_label']}**: {time_sense}",
                        "",
                    ]
                )
                # 持仓分类建议
                if pos_advice:
                    report_lines.extend(
                        [
                            f"| {labels['position_status_label']} | {labels['action_advice_label']} |",
                            "|---------|---------|",
                            f"| 🆕 **{labels['no_position_label']}** | {pos_advice.get('no_position', self.get_display_operation_advice(result, report_language))} |",
                            f"| 💼 **{labels['has_position_label']}** | {pos_advice.get('has_position', labels['continue_holding'])} |",
                            "",
                        ]
                    )

                self.append_market_snapshot(report_lines, result)

                # ========== 数据透视 ==========
                data_persp = dashboard.get("data_perspective", {}) if dashboard else {}
                if data_persp:
                    trend_data = data_persp.get("trend_status", {})
                    price_data = data_persp.get("price_position", {})
                    vol_data = data_persp.get("volume_analysis", {})
                    chip_data = data_persp.get("chip_structure", {})

                    report_lines.extend(
                        [
                            f"### 📊 {labels['data_perspective_heading']}",
                            "",
                        ]
                    )
                    # 趋势状态
                    if trend_data:
                        is_bullish = (
                            f"✅ {labels['yes_label']}"
                            if trend_data.get("is_bullish", False)
                            else f"❌ {labels['no_label']}"
                        )
                        report_lines.extend(
                            [
                                f"**{labels['ma_alignment_label']}**: {trend_data.get('ma_alignment', 'N/A')} | "
                                f"{labels['bullish_alignment_label']}: {is_bullish} | "
                                f"{labels['trend_strength_label']}: {trend_data.get('trend_score', 'N/A')}/100",
                                "",
                            ]
                        )
                    # 价格位置
                    if price_data:
                        bias_status = price_data.get("bias_status", "N/A")
                        report_lines.extend(
                            [
                                f"| {labels['price_metrics_label']} | {labels['current_price_label']} |",
                                "|---------|------|",
                                f"| {labels['current_price_label']} | {price_data.get('current_price', 'N/A')} |",
                                f"| {labels['ma5_label']} | {price_data.get('ma5', 'N/A')} |",
                                f"| {labels['ma10_label']} | {price_data.get('ma10', 'N/A')} |",
                                f"| {labels['ma20_label']} | {price_data.get('ma20', 'N/A')} |",
                                f"| {labels['bias_ma5_label']} | {price_data.get('bias_ma5', 'N/A')}% {bias_status} |",
                                f"| {labels['support_level_label']} | {price_data.get('support_level', 'N/A')} |",
                                f"| {labels['resistance_level_label']} | {price_data.get('resistance_level', 'N/A')} |",
                                "",
                            ]
                        )
                    # 量能分析
                    if vol_data:
                        report_lines.extend(
                            [
                                f"**{labels['volume_label']}**: {labels['volume_ratio_label']} {vol_data.get('volume_ratio', 'N/A')} ({vol_data.get('volume_status', '')}) | "
                                f"{labels['turnover_rate_label']} {vol_data.get('turnover_rate', 'N/A')}%",
                                f"💡 *{vol_data.get('volume_meaning', '')}*",
                                "",
                            ]
                        )
                    # 筹码结构
                    if chip_data:
                        if is_chip_structure_unavailable(chip_data):
                            report_lines.extend(
                                [
                                    f"**{labels['chip_label']}**: {get_chip_unavailable_reason(chip_data, report_language)}",
                                    "",
                                ]
                            )
                        else:
                            chip_health = localize_chip_health(chip_data.get("chip_health", "N/A"), report_language)
                            report_lines.extend(
                                [
                                    f"**{labels['chip_label']}**: {chip_data.get('profit_ratio', 'N/A')} | {chip_data.get('avg_cost', 'N/A')} | "
                                    f"{chip_data.get('concentration', 'N/A')} {chip_health}",
                                    "",
                                ]
                            )
                    else:
                        chip_unavailable_reason = get_chip_unavailable_reason(data_persp, report_language)
                        if chip_unavailable_reason:
                            report_lines.extend(
                                [
                                    f"**{labels['chip_label']}**: {chip_unavailable_reason}",
                                    "",
                                ]
                            )

                self.append_phase_decision_block(report_lines, dashboard, labels)

                # ========== 作战计划 ==========
                battle = dashboard.get("battle_plan", {}) if dashboard else {}
                if battle:
                    report_lines.extend(
                        [
                            f"### 🎯 {labels['battle_plan_heading']}",
                            "",
                        ]
                    )
                    # 狙击点位
                    sniper = battle.get("sniper_points", {})
                    if sniper:
                        report_lines.extend(
                            [
                                f"**📍 {labels['action_points_heading']}**",
                                "",
                                f"| {labels['action_points_heading']} | {labels['current_price_label']} |",
                                "|---------|------|",
                                f"| 🎯 {labels['ideal_buy_label']} | {self.clean_sniper_value(sniper.get('ideal_buy', 'N/A'))} |",
                                f"| 🔵 {labels['secondary_buy_label']} | {self.clean_sniper_value(sniper.get('secondary_buy', 'N/A'))} |",
                                f"| 🛑 {labels['stop_loss_label']} | {self.clean_sniper_value(sniper.get('stop_loss', 'N/A'))} |",
                                f"| 🎊 {labels['take_profit_label']} | {self.clean_sniper_value(sniper.get('take_profit', 'N/A'))} |",
                                "",
                            ]
                        )
                    # 仓位策略
                    position = battle.get("position_strategy", {})
                    if position:
                        report_lines.extend(
                            [
                                f"**💰 {labels['suggested_position_label']}**: {position.get('suggested_position', 'N/A')}",
                                f"- {labels['entry_plan_label']}: {position.get('entry_plan', 'N/A')}",
                                f"- {labels['risk_control_label']}: {position.get('risk_control', 'N/A')}",
                                "",
                            ]
                        )
                    # 检查清单
                    checklist = battle.get("action_checklist", []) if battle else []
                    if checklist:
                        report_lines.extend(
                            [
                                f"**✅ {labels['checklist_heading']}**",
                                "",
                            ]
                        )
                        for item in checklist:
                            report_lines.append(f"- {item}")
                        report_lines.append("")

                # ========== 信号归因分析 ==========
                signal_attr = dashboard.get("signal_attribution", {}) if dashboard else {}
                if signal_attribution_has_content(signal_attr):
                    report_lines.extend(
                        [
                            f"### 🎯 {labels['signal_attribution_heading']}",
                            "",
                        ]
                    )
                    weight_items = signal_attribution_weight_items(signal_attr)
                    if weight_items:
                        report_lines.append(f"**{labels['attribution_weights_label']}**:")
                        weight_labels = {
                            "technical_indicators": ("📈", labels["technical_indicators_label"]),
                            "news_sentiment": ("📰", labels["news_sentiment_label"]),
                            "fundamentals": ("📊", labels["fundamentals_label"]),
                            "market_conditions": ("🌐", labels["market_conditions_label"]),
                        }
                        for key, value in weight_items:
                            icon, label = weight_labels[key]
                            report_lines.append(f"- {icon} {label}: {value}%")
                        report_lines.append("")

                    # 最强信号
                    if signal_attr.get("strongest_bullish_signal"):
                        report_lines.append(
                            f"**🐂 {labels['strongest_bullish_signal_label']}**: {signal_attr['strongest_bullish_signal']}"
                        )
                    if signal_attr.get("strongest_bearish_signal"):
                        report_lines.append(
                            f"**🐻 {labels['strongest_bearish_signal_label']}**: {signal_attr['strongest_bearish_signal']}"
                        )
                    report_lines.append("")

                # ========== 多策略综合 ==========
                strategy_synthesis = normalize_strategy_synthesis_payload(
                    dashboard.get("strategy_synthesis") if dashboard else None
                )
                _append_strategy_synthesis_block(report_lines, strategy_synthesis, labels, report_language)

                # 财务摘要 / 股东回报 / 关联板块（数据缺失时自动隐藏对应小节）
                self.append_fundamental_blocks(report_lines, result)

                # 如果没有 dashboard，显示传统格式
                if not dashboard:
                    # 操作理由
                    if result.buy_reason:
                        report_lines.extend(
                            [
                                f"**💡 {reason_label}**: {result.buy_reason}",
                                "",
                            ]
                        )
                    # 风险提示
                    if result.risk_warning:
                        report_lines.extend(
                            [
                                f"**⚠️ {risk_warning_label}**: {result.risk_warning}",
                                "",
                            ]
                        )
                    # 技术面分析
                    if result.ma_analysis or result.volume_analysis:
                        report_lines.extend(
                            [
                                f"### 📊 {technical_heading}",
                                "",
                            ]
                        )
                        if result.ma_analysis:
                            report_lines.append(f"**{ma_label}**: {result.ma_analysis}")
                        if result.volume_analysis:
                            report_lines.append(f"**{volume_analysis_label}**: {result.volume_analysis}")
                        report_lines.append("")
                    # 消息面
                    if result.news_summary:
                        report_lines.extend(
                            [
                                f"### 📰 {news_heading}",
                                f"{result.news_summary}",
                                "",
                            ]
                        )

                report_lines.extend(
                    [
                        "---",
                        "",
                    ]
                )

        # 底部（去除免责声明）
        report_lines.extend(
            [
                "",
                f"*{labels['generated_at_label']}：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ]
        )
        models = self.collect_models_used(results)
        if models:
            report_lines.append(f"*{labels['analysis_model_label']}：{', '.join(models)}*")

        return "\n".join(report_lines)

    def generate_wechat_dashboard(self, results: List[AnalysisResult]) -> str:
        """
        生成企业微信决策仪表盘精简版（控制在4000字符内）

        只保留核心结论和狙击点位

        Args:
            results: 分析结果列表

        Returns:
            精简版决策仪表盘
        """
        config = self._runtime_config_provider()
        report_language = self.get_report_language(results)
        labels = get_report_labels(report_language)
        if getattr(config, "report_renderer_enabled", False) and results:
            from src.application.reporting.report_renderer import render

            out = render(
                platform="wechat",
                results=results,
                report_date=datetime.now().strftime("%Y-%m-%d"),
                summary_only=self._report_summary_only,
                extra_context={"report_language": report_language},
            )
            if out:
                return out

        report_date = datetime.now().strftime("%Y-%m-%d")

        # 按评分排序
        sorted_results = sorted(results, key=lambda x: x.sentiment_score, reverse=True)

        buy_count, sell_count, hold_count = self.count_display_decisions(results, report_language)

        lines = [
            f"## 🎯 {report_date} {labels['dashboard_title']}",
            "",
            f"> {len(results)} {labels['stock_unit']} | "
            f"🟢{labels['buy_label']}:{buy_count} 🟡{labels['watch_label']}:{hold_count} 🔴{labels['sell_label']}:{sell_count}",
        ]
        self.append_market_status_line(lines, results, report_language)

        # Issue #262: summary_only 时仅输出摘要列表
        if self._report_summary_only:
            lines.append(f"**📊 {labels['summary_heading']}**")
            lines.append("")
            for r in sorted_results:
                signal_text, signal_emoji, _ = self.get_signal_level(r)
                stock_name = self.get_display_name(r, report_language)
                lines.append(
                    f"{signal_emoji} **{stock_name}({r.code})**: "
                    f"{signal_text} | "
                    f"{labels['score_label']} {r.sentiment_score} | "
                    f"{localize_trend_prediction(r.trend_prediction, report_language)}"
                )
        else:
            for result in sorted_results:
                signal_text, signal_emoji, _ = self.get_signal_level(result)
                dashboard = result.dashboard if hasattr(result, "dashboard") and result.dashboard else {}
                core = dashboard.get("core_conclusion", {}) if dashboard else {}
                battle = dashboard.get("battle_plan", {}) if dashboard else {}
                intel = dashboard.get("intelligence", {}) if dashboard else {}

                # 股票名称
                stock_name = self.get_display_name(result, report_language)

                # 标题行：信号等级 + 股票名称
                lines.append(f"### {signal_emoji} **{signal_text}** | {stock_name}({result.code})")
                lines.append("")

                # 核心决策（一句话）
                one_sentence = core.get("one_sentence", result.analysis_summary) if core else result.analysis_summary
                if one_sentence:
                    lines.append(f"📌 **{one_sentence[:80]}**")
                    lines.append("")
                # 重要信息区（舆情+基本面）
                info_lines = []

                # 业绩预期
                if intel.get("earnings_outlook"):
                    outlook = str(intel["earnings_outlook"])[:60]
                    info_lines.append(f"📊 {labels['earnings_outlook_label']}: {outlook}")
                if intel.get("sentiment_summary"):
                    sentiment = str(intel["sentiment_summary"])[:50]
                    info_lines.append(f"💭 {labels['sentiment_summary_label']}: {sentiment}")
                if info_lines:
                    lines.extend(info_lines)
                    lines.append("")

                # 风险警报（最重要，醒目显示）
                risks = intel.get("risk_alerts", []) if intel else []
                if risks:
                    lines.append(f"🚨 **{labels['risk_alerts_label']}**:")
                    for risk in risks[:2]:  # 最多显示2条
                        risk_str = str(risk)
                        risk_text = risk_str[:50] + "..." if len(risk_str) > 50 else risk_str
                        lines.append(f"   • {risk_text}")
                    lines.append("")

                # 利好催化
                catalysts = intel.get("positive_catalysts", []) if intel else []
                if catalysts:
                    lines.append(f"✨ **{labels['positive_catalysts_label']}**:")
                    for cat in catalysts[:2]:  # 最多显示2条
                        cat_str = str(cat)
                        cat_text = cat_str[:50] + "..." if len(cat_str) > 50 else cat_str
                        lines.append(f"   • {cat_text}")
                    lines.append("")

                # 狙击点位
                sniper = battle.get("sniper_points", {}) if battle else {}
                if sniper:
                    ideal_buy = str(sniper.get("ideal_buy", ""))
                    stop_loss = str(sniper.get("stop_loss", ""))
                    take_profit = str(sniper.get("take_profit", ""))
                    points = []
                    if ideal_buy:
                        points.append(f"🎯{labels['ideal_buy_label']}:{ideal_buy[:15]}")
                    if stop_loss:
                        points.append(f"🛑{labels['stop_loss_label']}:{stop_loss[:15]}")
                    if take_profit:
                        points.append(f"🎊{labels['take_profit_label']}:{take_profit[:15]}")
                    if points:
                        lines.append(" | ".join(points))
                        lines.append("")

                # 持仓建议
                pos_advice = core.get("position_advice", {}) if core else {}
                if pos_advice:
                    no_pos = str(pos_advice.get("no_position", ""))
                    has_pos = str(pos_advice.get("has_position", ""))
                    if no_pos:
                        lines.append(f"🆕 {labels['no_position_label']}: {no_pos[:50]}")
                    if has_pos:
                        lines.append(f"💼 {labels['has_position_label']}: {has_pos[:50]}")
                    lines.append("")

                # 多策略综合
                strategy_synthesis = normalize_strategy_synthesis_payload(
                    dashboard.get("strategy_synthesis") if dashboard else None
                )
                if strategy_synthesis:
                    lines.append(
                        f"🧩 **{labels['strategy_synthesis_heading']}**: "
                        f"{localize_strategy_signal(strategy_synthesis.get('final_signal', 'N/A'), report_language)} | "
                        f"{labels['strategy_consensus_level_label']} "
                        f"{localize_consensus_level(strategy_synthesis.get('consensus_level', 'N/A'), report_language)} | "
                        f"{labels['strategy_conflict_label']} "
                        f"{localize_conflict_severity(strategy_synthesis.get('conflict_severity', 'none'), report_language)}"
                        f"({strategy_synthesis.get('conflict_count', 0)})"
                    )
                    invalid_count = strategy_invalid_opinion_count(strategy_synthesis)
                    if invalid_count:
                        lines.append(labels.get("strategy_invalid_opinions_label", "").format(count=invalid_count))
                    summary = localize_strategy_synthesis_summary(strategy_synthesis, report_language)
                    if summary:
                        lines.append(summary[:80])
                    lines.append("")

                # 检查清单简化版
                checklist = battle.get("action_checklist", []) if battle else []
                if checklist:
                    # 只显示不通过的项目
                    failed_checks = [str(c) for c in checklist if str(c).startswith("❌") or str(c).startswith("⚠️")]
                    if failed_checks:
                        lines.append(f"**{labels['failed_checks_heading']}**:")
                        for check in failed_checks[:3]:
                            lines.append(f"   {check[:40]}")
                        lines.append("")

                lines.append("---")
                lines.append("")

        # 底部
        lines.append(f"*{labels['report_time_label']}: {datetime.now().strftime('%H:%M')}*")
        models = self.collect_models_used(results)
        if models:
            lines.append(f"*{labels['analysis_model_label']}: {', '.join(models)}*")

        content = "\n".join(lines)

        return content

    def generate_wechat_summary(self, results: List[AnalysisResult]) -> str:
        """
        生成企业微信精简版日报（控制在4000字符内）

        Args:
            results: 分析结果列表

        Returns:
            精简版 Markdown 内容
        """
        report_date = datetime.now().strftime("%Y-%m-%d")
        report_language = self.get_report_language(results)
        labels = get_report_labels(report_language)

        # 按评分排序
        sorted_results = sorted(results, key=lambda x: x.sentiment_score, reverse=True)

        buy_count, sell_count, hold_count = self.count_display_decisions(results, report_language)
        avg_score = sum(r.sentiment_score for r in results) / len(results) if results else 0

        lines = [
            f"## 📅 {report_date} {labels['report_title']}",
            "",
            f"> {labels['analyzed_prefix']} **{len(results)}** {labels['stock_unit_compact']} | "
            f"🟢{labels['buy_label']}:{buy_count} 🟡{labels['watch_label']}:{hold_count} 🔴{labels['sell_label']}:{sell_count} | "
            f"{labels['avg_score_label']}:{avg_score:.0f}",
        ]
        self.append_market_status_line(lines, results, report_language)

        # 每只股票精简信息（控制长度）
        for result in sorted_results:
            signal_text, emoji, _ = self.get_signal_level(result)

            # 核心信息行
            lines.append(f"### {emoji} {self.get_display_name(result, report_language)}({result.code})")
            lines.append(
                f"**{signal_text}** | "
                f"{labels['score_label']}:{result.sentiment_score} | "
                f"{localize_trend_prediction(result.trend_prediction, report_language)}"
            )

            # 操作理由（截断）
            if hasattr(result, "buy_reason") and result.buy_reason:
                reason = result.buy_reason[:80] + "..." if len(result.buy_reason) > 80 else result.buy_reason
                lines.append(f"💡 {reason}")

            # 核心看点
            if hasattr(result, "key_points") and result.key_points:
                points = result.key_points[:60] + "..." if len(result.key_points) > 60 else result.key_points
                lines.append(f"🎯 {points}")

            # 风险提示（截断）
            if hasattr(result, "risk_warning") and result.risk_warning:
                risk = result.risk_warning[:50] + "..." if len(result.risk_warning) > 50 else result.risk_warning
                lines.append(f"⚠️ {risk}")

            lines.append("")

        # 底部（模型行在 --- 之前，Issue #528）
        models = self.collect_models_used(results)
        if models:
            lines.append(f"*{labels['analysis_model_label']}: {', '.join(models)}*")
        lines.extend(
            [
                "---",
                f"*{labels['not_investment_advice']}*",
                f"*{labels['details_report_hint']} reports/report_{report_date.replace('-', '')}.md*",
            ]
        )

        content = "\n".join(lines)

        return content

    def generate_brief_report(
        self,
        results: List[AnalysisResult],
        report_date: Optional[str] = None,
    ) -> str:
        """
        Generate brief report (3-5 sentences per stock) for mobile/push.

        Args:
            results: Analysis results list (use [result] for single stock).
            report_date: Report date (default: today).

        Returns:
            Brief markdown content.
        """
        if report_date is None:
            report_date = datetime.now().strftime("%Y-%m-%d")
        report_language = self.get_report_language(results)
        labels = get_report_labels(report_language)
        config = self._runtime_config_provider()
        if getattr(config, "report_renderer_enabled", False) and results:
            from src.application.reporting.report_renderer import render

            out = render(
                platform="brief",
                results=results,
                report_date=report_date,
                summary_only=False,
                extra_context={"report_language": report_language},
            )
            if out:
                return out
        # Fallback: brief summary from dashboard report
        if not results:
            return f"# {report_date} {labels['brief_title']}\n\n{labels['no_results']}"
        sorted_results = sorted(results, key=lambda x: x.sentiment_score, reverse=True)
        buy_count, sell_count, hold_count = self.count_display_decisions(results, report_language)
        lines = [
            f"# {report_date} {labels['brief_title']}",
            "",
            f"> {len(results)} {labels['stock_unit_compact']} | 🟢{buy_count} 🟡{hold_count} 🔴{sell_count}",
        ]
        self.append_market_status_line(lines, results, report_language)
        for r in sorted_results:
            signal_text, emoji, _ = self.get_signal_level(r)
            name = self.get_display_name(r, report_language)
            dash = r.dashboard or {}
            core = dash.get("core_conclusion", {}) or {}
            one = (core.get("one_sentence") or r.analysis_summary or "")[:60]
            lines.append(
                f"**{name}({r.code})** {emoji} "
                f"{signal_text} | "
                f"{labels['score_label']} {r.sentiment_score} | {one}"
            )
        lines.append("")
        lines.append(f"*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        models = self.collect_models_used(results)
        if models:
            lines.append(f"*{labels['analysis_model_label']}: {', '.join(models)}*")
        return "\n".join(lines)

    def generate_single_stock_report(self, result: AnalysisResult) -> str:
        """
        生成单只股票的分析报告（用于单股推送模式 #55）

        格式精简但信息完整，适合每分析完一只股票立即推送

        Args:
            result: 单只股票的分析结果

        Returns:
            Markdown 格式的单股报告
        """
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        report_language = self.get_report_language(result)
        labels = get_report_labels(report_language)
        signal_text, signal_emoji, _ = self.get_signal_level(result)
        dashboard = result.dashboard if hasattr(result, "dashboard") and result.dashboard else {}
        core = dashboard.get("core_conclusion", {}) if dashboard else {}
        battle = dashboard.get("battle_plan", {}) if dashboard else {}
        intel = dashboard.get("intelligence", {}) if dashboard else {}

        # 股票名称（转义 *ST 等特殊字符）
        stock_name = self.get_display_name(result, report_language)

        lines = [
            f"## {signal_emoji} {stock_name} ({result.code})",
            "",
            f"> {report_date} | {labels['score_label']}: **{result.sentiment_score}** | {localize_trend_prediction(result.trend_prediction, report_language)}",
            "",
        ]

        excerpt = self.public_phase_pack_excerpt(result, report_language)
        if excerpt:
            lines.extend([excerpt, ""])

        self.append_market_snapshot(lines, result)

        # 核心决策（一句话）
        one_sentence = core.get("one_sentence", result.analysis_summary) if core else result.analysis_summary
        if one_sentence:
            lines.extend(
                [
                    f"### 📌 {labels['core_conclusion_heading']}",
                    "",
                    f"**{signal_text}**: {one_sentence}",
                    "",
                ]
            )

        # 重要信息（舆情+基本面）
        info_added = False
        if intel:
            if intel.get("earnings_outlook"):
                if not info_added:
                    lines.append(f"### 📰 {labels['info_heading']}")
                    lines.append("")
                    info_added = True
                lines.append(f"📊 **{labels['earnings_outlook_label']}**: {str(intel['earnings_outlook'])[:100]}")

            if intel.get("sentiment_summary"):
                if not info_added:
                    lines.append(f"### 📰 {labels['info_heading']}")
                    lines.append("")
                    info_added = True
                lines.append(f"💭 **{labels['sentiment_summary_label']}**: {str(intel['sentiment_summary'])[:80]}")

            # 风险警报
            risks = intel.get("risk_alerts", [])
            if risks:
                if not info_added:
                    lines.append(f"### 📰 {labels['info_heading']}")
                    lines.append("")
                    info_added = True
                lines.append("")
                lines.append(f"🚨 **{labels['risk_alerts_label']}**:")
                for risk in risks[:3]:
                    lines.append(f"- {str(risk)[:60]}")

            # 利好催化
            catalysts = intel.get("positive_catalysts", [])
            if catalysts:
                lines.append("")
                lines.append(f"✨ **{labels['positive_catalysts_label']}**:")
                for cat in catalysts[:3]:
                    lines.append(f"- {str(cat)[:60]}")

        if info_added:
            lines.append("")

        # 狙击点位
        sniper = battle.get("sniper_points", {}) if battle else {}
        if sniper:
            lines.extend(
                [
                    f"### 🎯 {labels['action_points_heading']}",
                    "",
                    f"| {labels['ideal_buy_label']} | {labels['stop_loss_label']} | {labels['take_profit_label']} |",
                    "|------|------|------|",
                ]
            )
            ideal_buy = sniper.get("ideal_buy", "-")
            stop_loss = sniper.get("stop_loss", "-")
            take_profit = sniper.get("take_profit", "-")
            lines.append(f"| {ideal_buy} | {stop_loss} | {take_profit} |")
            lines.append("")

        # ========== 信号归因分析 ==========
        signal_attr = dashboard.get("signal_attribution", {}) if dashboard else {}
        if signal_attribution_has_content(signal_attr):
            lines.extend(
                [
                    f"### 🎯 {labels.get('signal_attribution_heading', '信号归因分析')}",
                    "",
                ]
            )
            # 归因权重
            weight_items = signal_attribution_weight_items(signal_attr)
            if weight_items:
                lines.append(f"**{labels.get('attribution_weights_label', '归因权重')}**:")
                weight_labels = {
                    "technical_indicators": ("📈", labels.get("technical_indicators_label", "技术指标")),
                    "news_sentiment": ("📰", labels.get("news_sentiment_label", "新闻舆情")),
                    "fundamentals": ("📊", labels.get("fundamentals_label", "基本面")),
                    "market_conditions": ("🌐", labels.get("market_conditions_label", "市场环境")),
                }
                for key, value in weight_items:
                    icon, label = weight_labels[key]
                    lines.append(f"- {icon} {label}: {value}%")
                lines.append("")

            # 最强信号
            bullish = signal_attr.get("strongest_bullish_signal")
            bearish = signal_attr.get("strongest_bearish_signal")
            if bullish:
                lines.append(f"**🐂 {labels.get('strongest_bullish_signal_label', '最强看多信号')}**: {bullish}")
            if bearish:
                lines.append(f"**🐻 {labels.get('strongest_bearish_signal_label', '最强看空信号')}**: {bearish}")
            lines.append("")

        # 持仓建议
        pos_advice = core.get("position_advice", {}) if core else {}
        if pos_advice:
            lines.extend(
                [
                    f"### 💼 {labels['position_advice_heading']}",
                    "",
                    f"- 🆕 **{labels['no_position_label']}**: {pos_advice.get('no_position', self.get_display_operation_advice(result, report_language))}",
                    f"- 💼 **{labels['has_position_label']}**: {pos_advice.get('has_position', labels['continue_holding'])}",
                    "",
                ]
            )

        # 财务摘要 / 股东回报 / 关联板块（数据缺失时自动隐藏对应小节）
        self.append_fundamental_blocks(lines, result)

        lines.append("---")
        if self.should_show_llm_model():
            model_used = normalize_model_used(getattr(result, "model_used", None))
            if model_used:
                lines.append(f"*{labels['analysis_model_label']}: {model_used}*")
        lines.append(f"*{labels['not_investment_advice']}*")

        return "\n".join(lines)

    def get_source_display_name(self, source: Any, language: Optional[str]) -> str:
        return _source_display_name_impl(source, language)

    def append_market_snapshot(self, lines: List[str], result: AnalysisResult) -> None:
        snapshot = getattr(result, "market_snapshot", None)
        if not snapshot:
            return

        report_language = self.get_report_language(result)
        labels = get_report_labels(report_language)

        lines.extend(
            [
                f"### 📈 {labels['market_snapshot_heading']}",
                "",
                f"| {labels['close_label']} | {labels['prev_close_label']} | {labels['open_label']} | {labels['high_label']} | {labels['low_label']} | {labels['change_pct_label']} | {labels['change_amount_label']} | {labels['amplitude_label']} | {labels['volume_label']} | {labels['amount_label']} |",
                "|------|------|------|------|------|-------|-------|------|--------|--------|",
                f"| {snapshot.get('close', 'N/A')} | {snapshot.get('prev_close', 'N/A')} | "
                f"{snapshot.get('open', 'N/A')} | {snapshot.get('high', 'N/A')} | "
                f"{snapshot.get('low', 'N/A')} | {snapshot.get('pct_chg', 'N/A')} | "
                f"{snapshot.get('change_amount', 'N/A')} | {snapshot.get('amplitude', 'N/A')} | "
                f"{snapshot.get('volume', 'N/A')} | {snapshot.get('amount', 'N/A')} |",
            ]
        )

        if "price" in snapshot:
            display_source = self.get_source_display_name(snapshot.get("source", "N/A"), report_language)
            lines.extend(
                [
                    "",
                    f"| {labels['current_price_label']} | {labels['volume_ratio_label']} | {labels['turnover_rate_label']} | {labels['source_label']} |",
                    "|-------|------|--------|----------|",
                    f"| {snapshot.get('price', 'N/A')} | {snapshot.get('volume_ratio', 'N/A')} | "
                    f"{snapshot.get('turnover_rate', 'N/A')} | {display_source} |",
                ]
            )

        lines.append("")

    @classmethod
    def format_amount_cn(cls, value: Any, currency: Optional[str] = None) -> str:
        """Format absolute amounts in 亿/万 + currency suffix; returns N/A on non-numeric.

        ``currency`` accepts ``USD``/``HKD``/``CNY``; unknown values fall back to 元.
        """
        return _format_amount_cn_impl(value, currency)

    @staticmethod
    def format_percent(value: Any) -> str:
        return _format_percent_impl(value)

    @classmethod
    def format_per_share(cls, value: Any, currency: Optional[str] = None) -> str:
        return _format_per_share_impl(value, currency)

    @staticmethod
    def format_text(value: Any) -> str:
        return _format_text_impl(value)

    def get_fundamental_blocks(self, result: AnalysisResult) -> Dict[str, Any]:
        """Extract financial_report / dividend / belong_boards / board rankings.

        Falls back to empty containers when fundamental_context is missing or partial,
        so callers can rely on dict shape without re-checking types.
        """
        ctx = getattr(result, "fundamental_context", None)
        if not isinstance(ctx, dict):
            return {
                "financial_report": {},
                "growth": {},
                "dividend": {},
                "belong_boards": [],
                "sector_top": [],
                "sector_bottom": [],
                "concept_top": [],
                "concept_bottom": [],
                "institution": {},
                "institution_status": None,
            }

        earnings_block = ctx.get("earnings") if isinstance(ctx.get("earnings"), dict) else {}
        earnings_data = earnings_block.get("data") if isinstance(earnings_block.get("data"), dict) else {}
        financial_report = (
            earnings_data.get("financial_report") if isinstance(earnings_data.get("financial_report"), dict) else {}
        )
        dividend = earnings_data.get("dividend") if isinstance(earnings_data.get("dividend"), dict) else {}

        growth_block = ctx.get("growth") if isinstance(ctx.get("growth"), dict) else {}
        growth_data = growth_block.get("data") if isinstance(growth_block.get("data"), dict) else {}

        boards_block = ctx.get("boards") if isinstance(ctx.get("boards"), dict) else {}
        boards_data = boards_block.get("data") if isinstance(boards_block.get("data"), dict) else {}
        sector_top = boards_data.get("top") if isinstance(boards_data.get("top"), list) else []
        sector_bottom = boards_data.get("bottom") if isinstance(boards_data.get("bottom"), list) else []
        concept_block = ctx.get("concept_boards") if isinstance(ctx.get("concept_boards"), dict) else {}
        if not concept_block and isinstance(ctx.get("concepts"), dict):
            concept_block = ctx.get("concepts")
        if not concept_block and isinstance(ctx.get("concept_rankings"), dict):
            concept_block = ctx.get("concept_rankings")
        concept_data = concept_block.get("data") if isinstance(concept_block.get("data"), dict) else concept_block
        if not isinstance(concept_data, dict):
            concept_data = {}
        concept_top = concept_data.get("top") if isinstance(concept_data.get("top"), list) else []
        concept_bottom = concept_data.get("bottom") if isinstance(concept_data.get("bottom"), list) else []

        belong_boards = ctx.get("belong_boards") if isinstance(ctx.get("belong_boards"), list) else []

        # 三大法人 (institutional flows) — tw-only; other markets keep status='not_supported'
        # and an empty data dict, so this block only renders for a Taiwan stock with data.
        institution_block = ctx.get("institution") if isinstance(ctx.get("institution"), dict) else {}
        institution_data = institution_block.get("data") if isinstance(institution_block.get("data"), dict) else {}

        return {
            "financial_report": financial_report,
            "growth": growth_data,
            "dividend": dividend,
            "belong_boards": belong_boards,
            "sector_top": sector_top,
            "sector_bottom": sector_bottom,
            "concept_top": concept_top,
            "concept_bottom": concept_bottom,
            "institution": institution_data,
            "institution_status": institution_block.get("status"),
        }

    def append_fundamental_blocks(self, lines: List[str], result: AnalysisResult) -> None:
        """Append 财务摘要 / 股东回报 / 关联板块 markdown blocks.

        Each block is only rendered when at least one cell has data; this keeps
        the email compact when the fundamental pipeline returned partial/failed
        results (e.g. HK/US markets, ETF, or AkShare outages).
        """
        blocks = self.get_fundamental_blocks(result)
        report_language = self.get_report_language(result)
        labels = get_report_labels(report_language)

        self.append_financial_summary(lines, blocks, labels)
        self.append_shareholder_return(lines, blocks, labels)
        self.append_institutional_flow(lines, blocks, labels)
        self.append_related_boards(lines, blocks, labels)

    def append_financial_summary(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        report = blocks.get("financial_report") or {}
        growth = blocks.get("growth") or {}
        currency = report.get("currency") if isinstance(report.get("currency"), str) else None
        cells = {
            "report_date": self.format_text(report.get("report_date")),
            "revenue": self.format_amount_cn(report.get("revenue"), currency),
            "net_profit": self.format_amount_cn(report.get("net_profit_parent"), currency),
            "operating_cash_flow": self.format_amount_cn(report.get("operating_cash_flow"), currency),
            "roe": self.format_percent(report.get("roe") if report.get("roe") is not None else growth.get("roe")),
            "revenue_yoy": self.format_percent(growth.get("revenue_yoy")),
            "net_profit_yoy": self.format_percent(growth.get("net_profit_yoy")),
            "gross_margin": self.format_percent(growth.get("gross_margin")),
        }
        if all(v == "N/A" for v in cells.values()):
            return

        lines.extend(
            [
                f"### 💼 {labels['financial_summary_heading']}",
                "",
                (
                    f"| {labels['report_date_label']} | {labels['revenue_label']} | "
                    f"{labels['net_profit_label']} | {labels['operating_cash_flow_label']} | "
                    f"{labels['roe_label']} | {labels['revenue_yoy_label']} | "
                    f"{labels['net_profit_yoy_label']} | {labels['gross_margin_label']} |"
                ),
                # 报告期居中，金额/比例右对齐 — 与现有市场快照风格保持一致
                "|:------:|-------:|-------:|-------:|------:|------:|------:|------:|",
                (
                    f"| {cells['report_date']} | {cells['revenue']} | {cells['net_profit']} | "
                    f"{cells['operating_cash_flow']} | {cells['roe']} | {cells['revenue_yoy']} | "
                    f"{cells['net_profit_yoy']} | {cells['gross_margin']} |"
                ),
                "",
            ]
        )

    def append_shareholder_return(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        dividend = blocks.get("dividend") or {}
        report = blocks.get("financial_report") or {}
        # Dividends are paid in the trading currency (yfinance `info.currency`)
        # which can differ from the financial-statement currency (e.g. HK ADRs
        # often report `financialCurrency=CNY` but pay dividends in HKD).
        dividend_currency = dividend.get("currency") if isinstance(dividend.get("currency"), str) else None
        if not dividend_currency:
            dividend_currency = report.get("currency") if isinstance(report.get("currency"), str) else None
        events = dividend.get("events") if isinstance(dividend.get("events"), list) else []
        latest_event = events[0] if events else {}
        if not isinstance(latest_event, dict):
            latest_event = {}

        ttm_event_count = dividend.get("ttm_event_count")
        cells = {
            "ttm_cash": self.format_per_share(dividend.get("ttm_cash_dividend_per_share"), dividend_currency),
            "ttm_count": str(ttm_event_count) if isinstance(ttm_event_count, int) else "N/A",
            "ttm_yield": self.format_percent(dividend.get("ttm_dividend_yield_pct")),
            "latest_ex": self.format_text(latest_event.get("ex_dividend_date") or latest_event.get("event_date")),
        }
        if all(v == "N/A" for v in cells.values()):
            return

        lines.extend(
            [
                f"### 💵 {labels['shareholder_return_heading']}",
                "",
                (
                    f"| {labels['ttm_cash_dividend_label']} | {labels['ttm_event_count_label']} | "
                    f"{labels['ttm_dividend_yield_label']} | {labels['latest_ex_dividend_label']} |"
                ),
                "|---------------------:|----------:|--------:|:--------:|",
                (f"| {cells['ttm_cash']} | {cells['ttm_count']} | " f"{cells['ttm_yield']} | {cells['latest_ex']} |"),
                "",
            ]
        )

    @classmethod
    def format_net_shares(cls, value: Any) -> str:
        """Format an institutional net buy/sell in 万股/亿股, signed (+ = net buy).

        Thresholds: abs >= 1e8 -> 亿股, >= 1e4 -> 万股, else 股. None/NaN/non-numeric -> N/A.
        """
        return _format_net_shares_impl(value)

    def append_institutional_flow(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        """Append the 三大法人 (institutional flows) table — tw-only.

        Renders only when the institution block reached status='ok' (a Taiwan stock
        whose TWSE T86 / TPEx fetch succeeded); every other market keeps
        status='not_supported' and is skipped, so this is strictly additive.
        """
        if blocks.get("institution_status") != "ok":
            return
        inst = blocks.get("institution") or {}
        cells = {
            "foreign": self.format_net_shares(inst.get("foreign_net")),
            "trust": self.format_net_shares(inst.get("trust_net")),
            "dealer": self.format_net_shares(inst.get("dealer_net")),
            "total": self.format_net_shares(inst.get("total_net")),
        }
        if all(v == "N/A" for v in cells.values()):
            return
        date = self.format_text(inst.get("date"))
        source = self.format_text(inst.get("source"))
        lines.extend(
            [
                f"### 📊 {labels['institutional_flow_heading']}（{date} · {source}）",
                "",
                f"> {labels['institutional_flow_note']}",
                "",
                (
                    f"| {labels['inst_foreign_label']} | {labels['inst_trust_label']} | "
                    f"{labels['inst_dealer_label']} | {labels['inst_total_label']} |"
                ),
                "|-----:|-----:|------:|------------:|",
                f"| {cells['foreign']} | {cells['trust']} | {cells['dealer']} | {cells['total']} |",
                "",
            ]
        )

    def append_related_boards(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        belong_boards = blocks.get("belong_boards") or []
        if not belong_boards:
            return

        sector_signals: Dict[str, Tuple[str, float]] = {}
        concept_signals: Dict[str, Tuple[str, float]] = {}

        def add_signals(target: Dict[str, Tuple[str, float]], rows: Any, label: str) -> None:
            for item in rows or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name or name in target:
                    continue
                change_pct = _safe_float(item.get("change_pct"))
                if change_pct is not None:
                    target[name] = (label, change_pct)

        add_signals(sector_signals, blocks.get("sector_top"), labels["leading_board_label"])
        add_signals(sector_signals, blocks.get("sector_bottom"), labels["lagging_board_label"])
        add_signals(concept_signals, blocks.get("concept_top"), labels["leading_board_label"])
        add_signals(concept_signals, blocks.get("concept_bottom"), labels["lagging_board_label"])

        def resolve_board_type(name: str, board_type: str) -> str:
            normalized_type = board_type.strip().lower()
            sector_signal = sector_signals.get(name)
            concept_signal = concept_signals.get(name)
            if concept_signal and not sector_signal:
                return "concept"
            if sector_signal and not concept_signal:
                return "sector"

            normalized_name = name.strip().lower()
            if any(marker in normalized_name for marker in ("概念", "题材", "concept", "theme")):
                return "concept"
            if any(marker in normalized_name for marker in ("行业", "industry", "sector")):
                return "sector"

            if normalized_type in {"概念", "概念板块", "题材", "concept", "theme"}:
                return "concept"
            if normalized_type in {"行业", "行业板块", "industry", "sector"}:
                return "sector"
            # A-share belong_boards may omit type for concept/theme labels.
            # Keep a deterministic display type instead of leaking N/A.
            return "concept"

        def resolve_signal(name: str, board_group: str) -> Tuple[Optional[str], Optional[float]]:
            if board_group == "sector":
                return sector_signals.get(name, (None, None))
            if board_group == "concept":
                return concept_signals.get(name, (None, None))
            sector_signal = sector_signals.get(name)
            concept_signal = concept_signals.get(name)
            if sector_signal and not concept_signal:
                return sector_signal
            if concept_signal and not sector_signal:
                return concept_signal
            return None, None

        def board_type_label(board_group: str) -> str:
            if board_group == "sector":
                return labels["industry_boards_heading"]
            return labels["concept_boards_heading"]

        # Pre-resolve rows so signal-bearing boards can show their own
        # percentage, while boards without a matching change stay plain.
        prepared: List[Tuple[str, str, Optional[str], Optional[float]]] = []
        for raw in belong_boards[:5]:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            board_type = self.format_text(raw.get("type"))
            board_group = resolve_board_type(name, board_type)
            status_text, change_pct = resolve_signal(name, board_group)
            prepared.append((name, board_type_label(board_group), status_text, change_pct))

        if not prepared:
            return

        lines.append(f"### 🧩 {labels['related_boards_heading']}")
        lines.append("")
        has_signal = any(status is not None and change_pct is not None for _, _, status, change_pct in prepared)
        if has_signal:
            for name, board_type, status_text, change_pct in prepared:
                details = []
                if status_text is not None and change_pct is not None:
                    details.append(f"{board_type} {status_text} {change_pct:+.2f}%")
                suffix = f" ({', '.join(details)})" if details else ""
                lines.append(f"- {name}{suffix}")
        else:
            lines.append(" / ".join(name for name, _, _, _ in prepared))
        lines.append("")
