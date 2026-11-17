# -*- coding: utf-8 -*-
"""分析上下文快照的纯函数解析（domain 层，无 IO / ORM 依赖）。

``context_snapshot`` 是分析历史落库时保存的增强上下文 JSON，其中
``enhanced_context.date`` 即本次分析对应的交易日。该解析原先以
``BacktestRepository.parse_analysis_date_from_snapshot`` 的静态方法形式存在，被
回测用例（``application/backtest/service.py`` 经端口）与技能观点结果评估
（``application/decision/skill_opinion_outcome_service.py`` 直接调类方法）共用。

下沉为 domain 纯函数后：仓储的静态方法改为委托本函数（保持既有调用点与端口
``BacktestRepositoryPort.parse_analysis_date_from_snapshot`` 不变），decision 用例
则直接调本函数，不再为取一个纯解析而依赖具体仓储实现。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional


def parse_analysis_date_from_snapshot(context_snapshot: Optional[str]) -> Optional[date]:
    """从 ``context_snapshot`` JSON 的 ``enhanced_context.date`` 解析分析日。

    解析失败、字段缺失或类型不符时返回 ``None``（与原静态方法行为逐字等价）。
    """
    if not context_snapshot:
        return None

    try:
        payload = json.loads(context_snapshot)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    enhanced = payload.get("enhanced_context")
    if not isinstance(enhanced, dict):
        return None

    date_str = enhanced.get("date")
    if not date_str:
        return None

    try:
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except Exception:
        return None
