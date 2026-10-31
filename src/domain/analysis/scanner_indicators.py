# -*- coding: utf-8 -*-
"""
技术信号扫描器 —— 信号检测纯函数层（分析领域）。

分层说明：本模块只含指标计算与信号判定的纯业务规则（仅依赖 stdlib/pandas，
无框架 / ORM / 存储 / IO / 数据源依赖），符合 ``src/domain/`` 守卫。

设计要点：
- 只负责「给定日 K 序列 -> 命中哪些信号」，不感知数据源、任务与并发，便于离线单测。
- 入参 bars 为按日期**升序**的 OHLC 序列，至少包含 close 字段；
  缺失 high/low 不影响本模块的八个信号（均以 close 序列计算）。
- 算法口径对齐仓库既有实现，不引入新的指标框架：
  - MACD(12/26/9) 与 src/domain/analysis/stock_analyzer.py 一致（pandas ewm，adjust=False）
  - RSI(6/12) 与 src/domain/analysis/stock_analyzer.py 一致（Wilder 平滑，alpha=1/period）
  - MA(5/10)、BOLL(20, 2σ) 为本模块新增，BOLL 用总体标准差 ddof=0
- 交叉类信号统一按「最后一根 vs 前一根」的边界穿越判定（<= / >= 取等号侧，
  即前一根持平、当根穿越也算触发），与参考项目 stock-dashboard 的口径一致。
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

import pandas as pd

# 支持的信号键（与参考项目 ScannerSignalKey 一致，避免前端映射漂移）
SIGNAL_KEYS: tuple = (
    "ma_golden",
    "ma_death",
    "macd_golden",
    "macd_death",
    "rsi_oversold",
    "rsi_overbought",
    "boll_upper",
    "boll_lower",
)

# 信号中文标签：后端日志/诊断使用；前端展示走 i18n（scanner.signal.*），此处非前端真源
SIGNAL_LABELS: Dict[str, str] = {
    "ma_golden": "MA金叉",
    "ma_death": "MA死叉",
    "macd_golden": "MACD金叉",
    "macd_death": "MACD死叉",
    "rsi_oversold": "RSI超卖",
    "rsi_overbought": "RSI超买",
    "boll_upper": "BOLL突破上轨",
    "boll_lower": "BOLL跌破下轨",
}

# 指标参数（与参考项目 / stock_analyzer 默认口径一致）
MA_FAST = 5
MA_SLOW = 10
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_SHORT = 6
RSI_MID = 12
RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0
BOLL_WINDOW = 20
BOLL_K = 2.0

# 最少需要的 K 线根数：取 MACD 慢线 + 信号线的稳定区，低于此值直接判定为数据不足
MIN_BARS = MACD_SLOW + MACD_SIGNAL


def _ema(series: "pd.Series", span: int) -> "pd.Series":
    """指数移动平均（adjust=False，与 stock_analyzer 口径一致）。"""
    return series.ewm(span=span, adjust=False).mean()


def _sma(series: "pd.Series", window: int) -> "pd.Series":
    """简单移动平均。"""
    return series.rolling(window=window).mean()


def _rsi(close: "pd.Series", period: int) -> "pd.Series":
    """Wilder 口径 RSI。

    边界：avg_loss 为 0 时无法计算 RS——此时若 avg_gain 也为 0（横盘）记 50（中性，
    避免横盘被误判为超买），有涨幅记 100（单边上涨）。
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0).fillna(0.0)
    loss = (-delta).clip(lower=0.0).fillna(0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()

    rsi = pd.Series(50.0, index=close.index)
    has_loss = avg_loss != 0
    rs = avg_gain[has_loss] / avg_loss[has_loss]
    rsi[has_loss] = 100.0 - (100.0 / (1.0 + rs))
    # 无回调但有涨幅 -> 100；无回调且无涨幅（横盘）保持 50
    rsi[(~has_loss) & (avg_gain > 0)] = 100.0
    return rsi


def _boll(close: "pd.Series") -> tuple:
    """布林带中轨/上轨/下轨（总体标准差 ddof=0）。"""
    mid = _sma(close, BOLL_WINDOW)
    std = close.rolling(window=BOLL_WINDOW).std(ddof=0)
    return mid, mid + BOLL_K * std, mid - BOLL_K * std


def _to_frame(bars: Sequence[Mapping[str, Any]]) -> "pd.DataFrame":
    """将裸 K 线字典序列规整为按日期升序、close 为数值的 DataFrame。"""
    frame = pd.DataFrame(list(bars))
    if "close" not in frame.columns:
        return pd.DataFrame(columns=["close"])

    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["close"])
    if "date" in frame.columns and len(frame) > 1:
        frame = frame.sort_values(by="date", kind="stable")
    return frame.reset_index(drop=True)


def detect_signals(
    bars: Sequence[Mapping[str, Any]],
    signals: Sequence[str],
) -> List[str]:
    """检测单只股票命中的技术信号。

    Args:
        bars: 按日期升序的日 K 序列，元素至少含 close（可选 date/high/low）。
        signals: 待检测的信号键集合（见 SIGNAL_KEYS），未知键忽略。

    Returns:
        命中的信号键列表，顺序与 signals 入参一致；数据不足或未命中时为空列表。
    """
    wanted = [key for key in signals if key in SIGNAL_KEYS]
    if not wanted or not bars:
        return []

    frame = _to_frame(bars)
    if len(frame) < MIN_BARS:
        return []

    close = frame["close"]
    matched: List[str] = []

    ma5 = _sma(close, MA_FAST)
    ma10 = _sma(close, MA_SLOW)
    dif = _ema(close, MACD_FAST) - _ema(close, MACD_SLOW)
    dea = _ema(dif, MACD_SIGNAL)
    rsi6 = _rsi(close, RSI_SHORT)
    rsi12 = _rsi(close, RSI_MID)
    _mid, upper, lower = _boll(close)

    latest_close = float(close.iloc[-1])

    if "ma_golden" in wanted and _crossed_up(ma5, ma10):
        matched.append("ma_golden")
    if "ma_death" in wanted and _crossed_down(ma5, ma10):
        matched.append("ma_death")

    if "macd_golden" in wanted and _crossed_up(dif, dea):
        matched.append("macd_golden")
    if "macd_death" in wanted and _crossed_down(dif, dea):
        matched.append("macd_death")

    if "rsi_oversold" in wanted:
        if float(rsi6.iloc[-1]) < RSI_OVERSOLD or float(rsi12.iloc[-1]) < RSI_OVERSOLD:
            matched.append("rsi_oversold")
    if "rsi_overbought" in wanted:
        if float(rsi6.iloc[-1]) > RSI_OVERBOUGHT or float(rsi12.iloc[-1]) > RSI_OVERBOUGHT:
            matched.append("rsi_overbought")

    if "boll_upper" in wanted and _is_value(upper.iloc[-1]):
        if latest_close > float(upper.iloc[-1]):
            matched.append("boll_upper")
    if "boll_lower" in wanted and _is_value(lower.iloc[-1]):
        if latest_close < float(lower.iloc[-1]):
            matched.append("boll_lower")

    # 保持与入参一致的顺序，避免结果集顺序随字典迭代漂移
    return [key for key in wanted if key in matched]


def _is_value(value: Any) -> bool:
    """判断指标末值是否为可用数值（NaN 视为不可用）。"""
    try:
        return value is not None and not pd.isna(value)
    except TypeError:
        return False


def _crossed_up(fast: "pd.Series", slow: "pd.Series") -> bool:
    """快速线上穿慢速线（前值 <= / 后值 >）。"""
    return _crossed(fast, slow, direction="up")


def _crossed_down(fast: "pd.Series", slow: "pd.Series") -> bool:
    """快速线下穿慢速线（前值 >= / 后值 <）。"""
    return _crossed(fast, slow, direction="down")


def _crossed(fast: "pd.Series", slow: "pd.Series", direction: str) -> bool:
    if len(fast) < 2 or len(slow) < 2:
        return False

    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if not all(_is_value(v) for v in (prev_fast, curr_fast, prev_slow, curr_slow)):
        return False

    prev_delta = float(prev_fast) - float(prev_slow)
    curr_delta = float(curr_fast) - float(curr_slow)

    if direction == "up":
        return prev_delta <= 0 and curr_delta > 0
    return prev_delta >= 0 and curr_delta < 0


__all__ = [
    "SIGNAL_KEYS",
    "SIGNAL_LABELS",
    "MIN_BARS",
    "detect_signals",
]
