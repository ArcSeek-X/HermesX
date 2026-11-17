# -*- coding: utf-8 -*-
"""筹码结构纯规则（analysis 领域，W5.1）。

承接原 ``src/application/analysis/analyzer.py`` 的筹码取值与判定助手：数值归一、
健康度推导与「筹码数据是否可用」判定。只依赖 ``src.domain.shared.report_language``
的本地化纯函数及本地数值计算；筹码价格/权重计算同样无 IO，不触达 provider / config / infra。
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from src.domain.shared.report_language import localize_chip_health


def safe_float(v: Any, default: float = 0.0) -> float:
    """安全转 float；失败（含 NaN）返回 ``default``。"""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        try:
            return default if math.isnan(float(v)) else float(v)
        except (ValueError, TypeError):
            return default
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


def coerce_chip_metric(v: Any) -> Optional[float]:
    """转换筹码指标，保留「缺失」与「零」的区别（缺失 → None）。"""
    if v is None:
        return None
    try:
        numeric = float(v)
    except (TypeError, ValueError):
        try:
            numeric = float(str(v).strip())
        except (TypeError, ValueError):
            return None
    return None if math.isnan(numeric) else numeric


def derive_chip_health(profit_ratio: float, concentration_90: float, language: str = "zh") -> str:
    """由获利盘比例与 90% 集中度推导筹码健康度标签。

    - 获利盘 >= 90%：警惕（获利盘极高）
    - 90% 集中度 >= 0.25：警惕（筹码分散）
    - 集中度 < 0.15 且 0.3 <= 获利盘 < 0.9：健康（集中且获利比例适中）
    - 其余：一般
    """
    if profit_ratio >= 0.9:
        return localize_chip_health("警惕", language)
    if concentration_90 >= 0.25:
        return localize_chip_health("警惕", language)
    if concentration_90 < 0.15 and 0.3 <= profit_ratio < 0.9:
        return localize_chip_health("健康", language)
    return localize_chip_health("一般", language)


def has_usable_chip_metrics(
    avg_cost: Optional[float],
    concentration_90: Optional[float],
    concentration_70: Optional[float],
) -> bool:
    """已归一化筹码指标的共同有效性规则，不负责提供方/历史字典解析。"""
    return (
        avg_cost is not None
        and avg_cost > 0
        and (
            (concentration_90 is not None and concentration_90 >= 0)
            or (concentration_70 is not None and concentration_70 >= 0)
        )
    )


def has_meaningful_chip_data(chip_data: Any) -> bool:
    """筹码数据是否具备上报所需的核心指标（均价 > 0 且至少一个集中度可解析）。

    兼容 ``ChipDistribution`` 之类的属性对象与普通 dict；dict 缺 ``concentration_90``
    时回退读 ``concentration``（历史字段名）。
    """
    if not chip_data:
        return False
    if hasattr(chip_data, "avg_cost"):
        avg_cost = coerce_chip_metric(getattr(chip_data, "avg_cost", None))
        concentration_90 = coerce_chip_metric(
            getattr(chip_data, "concentration_90", None)
        )
        concentration_70 = coerce_chip_metric(
            getattr(chip_data, "concentration_70", None)
        )
    else:
        d = chip_data if isinstance(chip_data, dict) else {}
        avg_cost = coerce_chip_metric(d.get("avg_cost"))
        concentration_90_value = d.get("concentration_90")
        if concentration_90_value is None:
            concentration_90_value = d.get("concentration")
        concentration_90 = coerce_chip_metric(concentration_90_value)
        concentration_70 = coerce_chip_metric(d.get("concentration_70"))
    return has_usable_chip_metrics(avg_cost, concentration_90, concentration_70)


def build_chip_structure(
    chip_data: Any,
    language: str = "zh",
    *,
    derive=derive_chip_health,
    to_float=safe_float,
) -> Dict[str, Any]:
    """从筹码对象 / dict 组装上报用的 ``chip_structure``。

    ``derive`` / ``to_float`` 以默认参数注入，便于调用方沿用既有 seam 替换实现；
    ``language`` 透传给健康度本地化。
    """
    if hasattr(chip_data, "profit_ratio"):
        pr = to_float(chip_data.profit_ratio)
        ac = chip_data.avg_cost
        c90 = to_float(chip_data.concentration_90)
    else:
        d = chip_data if isinstance(chip_data, dict) else {}
        pr = to_float(d.get("profit_ratio"))
        ac = d.get("avg_cost")
        c90 = to_float(d.get("concentration_90"))
    return {
        "profit_ratio": f"{pr:.1%}",
        "avg_cost": ac if (ac is not None and to_float(ac) != 0.0) else "N/A",
        "concentration": f"{c90:.2%}",
        "chip_health": derive(pr, c90, language),
    }


def compute_cyq_metrics(df: Any, current_price: float) -> dict:
    """
    基于 Tushare 的筹码分布明细表 (cyq_chips) 计算常用筹码指标
    :param df: 包含 'price' 和 'percent' 列的 DataFrame
    :param current_price: 股票当天的当前价/收盘价 (用于计算获利比例)
    :return: 包含各项筹码指标的字典
    """
    import numpy as np

    # 1. 确保按价格从小到大排序 (Tushare 返回的数据往往是纯倒序的)
    df_sorted = df.sort_values(by="price", ascending=True).reset_index(drop=True)

    # 2. 防止原始数据 percent 总和产生浮点数误差，归一化到 100%
    total_percent = df_sorted["percent"].sum()

    df_sorted["norm_percent"] = df_sorted["percent"] / total_percent * 100

    # 3. 计算筹码的累积分布
    df_sorted["cumsum"] = df_sorted["norm_percent"].cumsum()

    # --- 获利比例 ---
    # 所有价格 <= 当前价的筹码之和
    winner_rate = df_sorted[df_sorted["price"] <= current_price]["norm_percent"].sum()

    # --- 平均成本 ---
    # 价格的加权平均值
    avg_cost = np.average(df_sorted["price"], weights=df_sorted["norm_percent"])

    # --- 辅助函数：求指定累积比例处的价格 ---
    def get_percentile_price(target_pct):
        # 寻找累积求和第一次大于等于目标百分比的行索引
        """按分位数计算价格。"""
        idx = df_sorted["cumsum"].searchsorted(target_pct)
        idx = min(idx, len(df_sorted) - 1)  # 防止越界
        return df_sorted.loc[idx, "price"]

    # --- 90% 成本区与集中度 ---
    # 去头去尾各 5%
    cost_90_low = get_percentile_price(5)
    cost_90_high = get_percentile_price(95)
    if (cost_90_high + cost_90_low) != 0:
        concentration_90 = (
            (cost_90_high - cost_90_low) / (cost_90_high + cost_90_low) * 100
        )
    else:
        concentration_90 = 0.0

    # --- 70% 成本区与集中度 ---
    # 去头去尾各 15%
    cost_70_low = get_percentile_price(15)
    cost_70_high = get_percentile_price(85)
    if (cost_70_high + cost_70_low) != 0:
        concentration_70 = (
            (cost_70_high - cost_70_low) / (cost_70_high + cost_70_low) * 100
        )
    else:
        concentration_70 = 0.0

    # 返回格式化结果
    return {
        "获利比例": round(winner_rate / 100, 4),  # /100 与akshare保持一致，返回小数格式
        "平均成本": round(avg_cost, 4),
        "90成本-低": round(cost_90_low, 4),
        "90成本-高": round(cost_90_high, 4),
        "90集中度": round(concentration_90 / 100, 4),
        "70成本-低": round(cost_70_low, 4),
        "70成本-高": round(cost_70_high, 4),
        "70集中度": round(concentration_70 / 100, 4),
    }
