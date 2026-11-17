# -*- coding: utf-8 -*-
"""持仓风险纯规则（portfolio 领域）。

本模块只承载持仓/风险的**纯业务规则**——占比、集中度排序与告警判定、回撤序列
指标、止损接近度告警、主板块挑选。输入输出均为普通 ``dict`` / 标量，不含 IO、
DB、网络、配置读取与日志，因此可被 application 层在任意执行环境中复用。

货币换算与快照取数留在 application 层（``PortfolioService.convert_amount`` /
``PortfolioRepositoryPort``）：调用方需先把各持仓折算为统一计价币种，再把纯数值
交给本模块聚合。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# 板块归属无法判定时的聚合键（仅内部占位，不对用户展示）。
UNCLASSIFIED_SECTOR = "UNCLASSIFIED"


def compute_weight_pct(exposure: float, total: float) -> float:
    """占比（百分数，未四舍五入）；分母不大于 0 时按 0.0 处理。"""
    total_value = float(total or 0.0)
    exposure_value = float(exposure or 0.0)
    return (exposure_value / total_value * 100.0) if total_value > 0 else 0.0


def rank_exposure_rows(
    rows: Iterable[Dict[str, Any]],
    threshold_pct: float,
    *,
    top_n: int = 10,
) -> Tuple[List[Dict[str, Any]], float, bool]:
    """按市值降序取前 ``top_n`` 行，并给出首行权重与整体告警判定。

    返回 ``(top_rows, top_weight_pct, alert)``；无持仓时返回 ``([], 0.0, False)``。
    告警判定沿用迁移前口径——以**首行已四舍五入的** ``weight_pct`` 与阈值比较。
    """
    ordered = sorted(rows, key=lambda item: item["market_value_base"], reverse=True)
    top_weight = float(ordered[0]["weight_pct"]) if ordered else 0.0
    return ordered[:top_n], top_weight, bool(top_weight >= threshold_pct)


def compute_drawdown_metrics(
    series: Iterable[Tuple[str, float]],
    threshold_pct: float,
) -> Dict[str, Any]:
    """回撤指标：``(日期键, 净值)`` 序列 → 最大/当前回撤与告警。

    序列按日期键升序处理（与调用方传入顺序无关）；峰值从 0 起算，峰值为 0 时
    该点回撤记 0.0。返回 ``series_points`` / ``max_drawdown_pct`` /
    ``current_drawdown_pct`` / ``alert``；``fx_stale`` 由调用方合并。
    """
    ordered = sorted(series, key=lambda item: item[0])
    peak = 0.0
    max_drawdown = 0.0
    current_drawdown = 0.0
    for _, equity in ordered:
        equity_value = float(equity)
        peak = max(peak, equity_value)
        drawdown = 0.0 if peak <= 0 else (peak - equity_value) / peak * 100.0
        max_drawdown = max(max_drawdown, drawdown)
        current_drawdown = drawdown

    return {
        "series_points": len(ordered),
        "max_drawdown_pct": round(max_drawdown, 4),
        "current_drawdown_pct": round(current_drawdown, 4),
        "alert": bool(max_drawdown >= threshold_pct),
    }


def build_stop_loss_report(
    snapshot: Dict[str, Any],
    *,
    stop_loss_pct: float,
    near_ratio: float,
    top_n: int = 20,
) -> Dict[str, Any]:
    """止损接近度告警：按持仓均价与最新价计算浮亏比例。

    ``near_threshold = stop_loss_pct * near_ratio``：浮亏达到该线即进入 near 列表，
    达到 ``stop_loss_pct`` 时标记 ``is_triggered``；成本价非正的持仓直接跳过。
    """
    stop_loss_value = float(stop_loss_pct)
    near_threshold = stop_loss_value * float(near_ratio)

    warnings: List[Dict[str, Any]] = []
    for account in snapshot.get("accounts", []):
        for pos in account.get("positions", []):
            avg_cost = float(pos.get("avg_cost", 0.0) or 0.0)
            last_price = float(pos.get("last_price", 0.0) or 0.0)
            if avg_cost <= 0:
                continue
            loss_pct = max(0.0, (avg_cost - last_price) / avg_cost * 100.0)
            if loss_pct < near_threshold:
                continue
            warnings.append(
                {
                    "account_id": account.get("account_id"),
                    "symbol": pos.get("symbol"),
                    "avg_cost": round(avg_cost, 8),
                    "last_price": round(last_price, 8),
                    "loss_pct": round(loss_pct, 4),
                    "near_threshold_pct": round(near_threshold, 4),
                    "is_triggered": bool(loss_pct >= stop_loss_value),
                }
            )

    warnings.sort(key=lambda item: item["loss_pct"], reverse=True)
    return {
        "near_alert": len(warnings) > 0,
        "triggered_count": sum(1 for item in warnings if item["is_triggered"]),
        "near_count": len(warnings),
        "items": warnings[:top_n],
    }


def pick_primary_board_name(boards: Optional[Sequence[Any]]) -> Optional[str]:
    """从板块归属列表里挑主板块：优先「行业」类型，否则取首个非空名称。"""
    if not boards:
        return None

    preferred: Optional[str] = None
    fallback: Optional[str] = None
    for item in boards:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if fallback is None:
            fallback = name
        type_text = str(item.get("type") or "").strip().lower()
        if "行业" in type_text or "industry" in type_text:
            preferred = name
            break
    return preferred or fallback
