# -*- coding: utf-8 -*-
"""持仓/自选告警用例（应用层）。

分层说明：本包持有持仓/自选告警的目标展开、静/风险告警评估与 dry-run 结果聚合逻辑。
`portfolio_service`（S2f-3）、`portfolio_risk_service`（S2f-2）、`portfolio_import_service`（S2f-1）
均已随 S 线迁入本包，与 `portfolio_alerts` 共同构成持仓应用层用例；对外部取数
（板块归属 `BelongBoardsPort`、实时行情 `PortfolioRealtimeQuotePort`）经
`application/portfolio/ports.py` 端口收敛，由 infrastructure 适配器承载 `data_provider` 访问。
"""

from __future__ import annotations

from src.application.portfolio.portfolio_alerts import (  # noqa: F401
    DRY_RUN_TARGET_TIMEOUT_SECONDS,
    DRY_RUN_TOTAL_TIMEOUT_SECONDS,
    PORTFOLIO_ALERT_TYPES,
    SYMBOL_BATCH_TARGET_SCOPES,
    ExpandedSymbolTarget,
    PortfolioRiskAlert,
    RuntimeAlertPayload,
    StaticAlertEvaluation,
    aggregate_dry_run_results,
    ensure_active_portfolio_account,
    evaluate_portfolio_risk_alert,
    evaluate_static_alert,
    expand_symbol_targets,
    make_portfolio_risk_payload,
    make_static_payload,
    normalize_batch_target_scope_target,
    normalize_portfolio_alert_parameters,
    portfolio_effective_target,
    result_to_target_result,
)

__all__ = [
    "DRY_RUN_TARGET_TIMEOUT_SECONDS",
    "DRY_RUN_TOTAL_TIMEOUT_SECONDS",
    "PORTFOLIO_ALERT_TYPES",
    "SYMBOL_BATCH_TARGET_SCOPES",
    "ExpandedSymbolTarget",
    "PortfolioRiskAlert",
    "RuntimeAlertPayload",
    "StaticAlertEvaluation",
    "aggregate_dry_run_results",
    "ensure_active_portfolio_account",
    "evaluate_portfolio_risk_alert",
    "evaluate_static_alert",
    "expand_symbol_targets",
    "make_portfolio_risk_payload",
    "make_static_payload",
    "normalize_batch_target_scope_target",
    "normalize_portfolio_alert_parameters",
    "portfolio_effective_target",
    "result_to_target_result",
]
