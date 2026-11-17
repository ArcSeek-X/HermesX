# -*- coding: utf-8 -*-
"""Resolve one coherent local daily-bar window across equivalent stock codes.

在多个等价股票代码（不同后缀 / 市场形态）间选出一段连贯的本地日线窗口，
用于回测 / 评估时锚定到期望交易日；start 与 forward bars 绝不跨代码形状拼接。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Sequence, Tuple

from src.application.backtest.ports import StockRepositoryPort
from src.domain.backtest.engine import DailyBarLike


@dataclass(frozen=True)
class StockDailyWindow:
    """A start bar and its forward bars from one stored stock-code shape.

    来自同一存储代码形态的一段窗口（起始 bar + 其后的 forward bars），frozen 不可变。
    """

    code: str
    start_bar: DailyBarLike
    forward_bars: List[DailyBarLike]


def resolve_stock_daily_window(
    *,
    stock_repo: StockRepositoryPort,
    code_candidates: Sequence[str],
    expected_start_date: date,
    eval_window_days: int,
) -> Optional[StockDailyWindow]:
    """Choose one coherent window anchored to the expected trading session.

    Only candidates with a bar on the authoritative expected date are eligible.
    Complete windows outrank partial ones; remaining ties prefer more forward
    bars and then candidate order. Start and forward bars are never combined
    across code shapes.

    ``stock_repo`` only needs the two read methods declared by
    :class:`~src.application.backtest.ports.StockRepositoryPort`; callers pass
    whatever port-conforming storage they already hold.

    在候选代码里，只保留「期望交易日当天有 bar」的代码；完整窗口优先于残缺窗口，
    平局时 forward bars 越多越优先、其次按候选顺序；评分 (完整?, forward数, -rank) 取最大者。
    ``stock_repo`` 仅需 StockRepositoryPort 声明的两个读方法，调用方传入任意符合端口的存储。
    """
    best_window: Optional[StockDailyWindow] = None
    best_key: Optional[Tuple[bool, int, int]] = None
    if isinstance(eval_window_days, bool) or not isinstance(eval_window_days, int):
        raise ValueError("eval_window_days must be a positive integer")
    required_bars = eval_window_days
    if required_bars <= 0:
        raise ValueError("eval_window_days must be a positive integer")

    for rank, code in enumerate(dict.fromkeys(code_candidates)):
        if not code:
            continue
        start_bar = stock_repo.get_daily_on_date(
            code=code,
            target_date=expected_start_date,
        )
        if start_bar is None or start_bar.close is None:
            continue

        forward_bars = stock_repo.get_forward_bars(
            code=code,
            analysis_date=start_bar.date,
            eval_window_days=required_bars,
        )
        key = (
            len(forward_bars) >= required_bars,
            len(forward_bars),
            -rank,
        )
        if best_key is None or key > best_key:
            best_key = key
            best_window = StockDailyWindow(
                code=code,
                start_bar=start_bar,
                forward_bars=forward_bars,
            )

    return best_window
