"""Market-data enrichment for the analysis context; orchestration stays in pipeline."""

from __future__ import annotations
import logging
from datetime import date
from typing import Dict, Any, Optional
import pandas as pd
from src.domain.market.chip_distribution import ChipDistribution
from src.domain.market.stock_codes import normalize_stock_code
from src.domain.analysis import pipeline_rules as _pipeline_rules
from src.domain.shared.report_language import normalize_report_language
from src.application.intelligence.search_service import SearchService
from src.domain.analysis.stock_analyzer import TrendAnalysisResult
from src.domain.market.trading_calendar import get_market_for_stock, get_market_now, is_market_open

logger = logging.getLogger("src.application.analysis.pipeline")


class AnalysisContextEnricher:
    """Enrich fetched context using explicit quote and search dependencies."""

    def __init__(self, *, config, fetcher_manager, search_service):
        """构造上下文增强器：装配配置、取数管理器与检索服务。"""
        self.config = config
        self.fetcher_manager = fetcher_manager
        self.search_service = search_service

    def enhance_context(
        self,
        context: Dict[str, Any],
        realtime_quote,
        chip_data: Optional[ChipDistribution],
        trend_result: Optional[TrendAnalysisResult],
        stock_name: str = "",
        fundamental_context: Optional[Dict[str, Any]] = None,
        market_phase_context: Optional[Dict[str, Any]] = None,
        portfolio_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        增强分析上下文

        将实时行情、筹码分布、趋势分析结果、股票名称添加到上下文中

        Args:
            context: 原始上下文
            realtime_quote: 实时行情数据（UnifiedRealtimeQuote 或 None）
            chip_data: 筹码分布数据
            trend_result: 趋势分析结果
            stock_name: 股票名称
            market_phase_context: 已构建的市场阶段上下文，用于标记盘中 partial bar

        Returns:
            增强后的上下文
        """
        enhanced = context.copy()
        enhanced["report_language"] = normalize_report_language(getattr(self.config, "report_language", "zh"))

        # 添加股票名称
        if stock_name:
            enhanced["stock_name"] = stock_name
        elif realtime_quote and getattr(realtime_quote, "name", None):
            enhanced["stock_name"] = realtime_quote.name
        if isinstance(portfolio_context, dict):
            enhanced["portfolio_context"] = dict(portfolio_context)

        # 将运行时搜索窗口透传给 analyzer，避免与全局配置重新读取产生窗口不一致
        enhanced["news_window_days"] = getattr(self.search_service, "news_window_days", 3)

        # 添加实时行情（兼容不同数据源的字段差异）
        if realtime_quote:
            # 使用 getattr 安全获取字段，缺失字段返回 None 或默认值
            volume_ratio = getattr(realtime_quote, "volume_ratio", None)
            quote_source = getattr(realtime_quote, "source", None)
            quote_source_name = getattr(quote_source, "value", quote_source)
            quote_source_name = str(quote_source_name) if quote_source_name is not None else None
            enhanced["realtime"] = {
                "name": getattr(realtime_quote, "name", ""),
                "price": getattr(realtime_quote, "price", None),
                "change_pct": getattr(realtime_quote, "change_pct", None),
                "volume_ratio": volume_ratio,
                "volume_ratio_desc": self.describe_volume_ratio(volume_ratio) if volume_ratio else "无数据",
                "turnover_rate": getattr(realtime_quote, "turnover_rate", None),
                "pe_ratio": getattr(realtime_quote, "pe_ratio", None),
                "pb_ratio": getattr(realtime_quote, "pb_ratio", None),
                "total_mv": getattr(realtime_quote, "total_mv", None),
                "circ_mv": getattr(realtime_quote, "circ_mv", None),
                "change_60d": getattr(realtime_quote, "change_60d", None),
                "source": quote_source_name,
                "fetched_at": getattr(realtime_quote, "fetched_at", None),
                "provider_timestamp": getattr(realtime_quote, "provider_timestamp", None),
                "is_stale": getattr(realtime_quote, "is_stale", None),
                "stale_seconds": getattr(realtime_quote, "stale_seconds", None),
                "fallback_from": getattr(realtime_quote, "fallback_from", None),
            }
            # 移除 None 值以减少上下文大小
            enhanced["realtime"] = {k: v for k, v in enhanced["realtime"].items() if v is not None}

        # 添加筹码分布
        if chip_data:
            current_price = getattr(realtime_quote, "price", 0) if realtime_quote else 0
            enhanced["chip"] = {
                "profit_ratio": chip_data.profit_ratio,
                "avg_cost": chip_data.avg_cost,
                "concentration_90": chip_data.concentration_90,
                "concentration_70": chip_data.concentration_70,
                "chip_status": chip_data.get_chip_status(current_price or 0),
            }

        # 添加趋势分析结果
        if trend_result:
            enhanced["trend_analysis"] = {
                "trend_status": trend_result.trend_status.value,
                "ma_alignment": trend_result.ma_alignment,
                "trend_strength": trend_result.trend_strength,
                "bias_ma5": trend_result.bias_ma5,
                "bias_ma10": trend_result.bias_ma10,
                "volume_status": trend_result.volume_status.value,
                "volume_trend": trend_result.volume_trend,
                "buy_signal": trend_result.buy_signal.value,
                "signal_score": trend_result.signal_score,
                "signal_reasons": trend_result.signal_reasons,
                "risk_factors": trend_result.risk_factors,
            }

        # Issue #234：盘中分析使用实时 OHLC 与趋势 MA 覆盖 today。
        # 防护条件：trend_result.ma5 > 0 表示 MA 计算已成功且数据量充足。
        if realtime_quote and trend_result and trend_result.ma5 > 0:
            price = getattr(realtime_quote, "price", None)
            if price is not None and price > 0:
                yesterday_close = None
                if enhanced.get("yesterday") and isinstance(enhanced["yesterday"], dict):
                    yesterday_close = enhanced["yesterday"].get("close")
                orig_today = enhanced.get("today") or {}
                market_today = (
                    get_market_now(get_market_for_stock(normalize_stock_code(enhanced.get("code", ""))))
                    .date()
                    .isoformat()
                )
                source = getattr(realtime_quote, "source", None)
                source_name = getattr(source, "value", source)
                source_name = str(source_name) if source_name is not None else "unknown"
                open_p = (
                    getattr(realtime_quote, "open_price", None)
                    or getattr(realtime_quote, "pre_close", None)
                    or yesterday_close
                    or orig_today.get("open")
                    or price
                )
                high_p = getattr(realtime_quote, "high", None) or price
                low_p = getattr(realtime_quote, "low", None) or price
                vol = getattr(realtime_quote, "volume", None)
                amt = getattr(realtime_quote, "amount", None)
                pct = getattr(realtime_quote, "change_pct", None)
                fetched_at = getattr(realtime_quote, "fetched_at", None)
                provider_timestamp = getattr(realtime_quote, "provider_timestamp", None)
                fallback_from = getattr(realtime_quote, "fallback_from", None)
                realtime_today = {
                    "close": price,
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "ma5": trend_result.ma5,
                    "ma10": trend_result.ma10,
                    "ma20": trend_result.ma20,
                    "date": market_today,
                    "data_source": f"realtime:{source_name}",
                    "realtime_source": source_name,
                    "is_estimated": True,
                }
                estimated_fields = [
                    "close",
                    "open",
                    "high",
                    "low",
                    "ma5",
                    "ma10",
                    "ma20",
                ]
                if vol is not None:
                    realtime_today["volume"] = vol
                    estimated_fields.append("volume")
                if amt is not None:
                    realtime_today["amount"] = amt
                    estimated_fields.append("amount")
                if pct is not None:
                    realtime_today["pct_chg"] = pct
                    estimated_fields.append("pct_chg")
                realtime_today["estimated_fields"] = estimated_fields
                if isinstance(market_phase_context, dict) and "is_partial_bar" in market_phase_context:
                    realtime_today["is_partial_bar"] = market_phase_context.get("is_partial_bar")
                if fetched_at is not None:
                    realtime_today["fetched_at"] = fetched_at
                if provider_timestamp is not None:
                    realtime_today["provider_timestamp"] = provider_timestamp
                if fallback_from is not None:
                    realtime_today["fallback_from"] = fallback_from
                realtime_owned_fields = {
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "amount",
                    "pct_chg",
                    "pctChg",
                    "date",
                    "data_source",
                    "dataSource",
                    "source",
                    "realtime_source",
                    "realtimeSource",
                    "is_partial_bar",
                    "isPartialBar",
                    "is_estimated",
                    "isEstimated",
                    "estimated_fields",
                    "estimatedFields",
                    "fetched_at",
                    "fetchedAt",
                    "provider_timestamp",
                    "providerTimestamp",
                    "fallback_from",
                    "fallbackFrom",
                }
                for k, v in orig_today.items():
                    if k not in realtime_today and k not in realtime_owned_fields and v is not None:
                        realtime_today[k] = v
                enhanced["today"] = realtime_today
                enhanced["ma_status"] = self.compute_ma_status(
                    price, trend_result.ma5, trend_result.ma10, trend_result.ma20
                )
                enhanced["date"] = market_today
                if yesterday_close is not None:
                    try:
                        yc = float(yesterday_close)
                        if yc > 0:
                            enhanced["price_change_ratio"] = round((price - yc) / yc * 100, 2)
                    except (TypeError, ValueError):
                        pass
                if vol is not None and enhanced.get("yesterday"):
                    yest_vol = enhanced["yesterday"].get("volume") if isinstance(enhanced["yesterday"], dict) else None
                    if yest_vol is not None:
                        try:
                            yv = float(yest_vol)
                            if yv > 0:
                                enhanced["volume_change_ratio"] = round(float(vol) / yv, 2)
                        except (TypeError, ValueError):
                            pass

        # ETF/index flag for analyzer prompt (Fixes #274)
        enhanced["is_index_etf"] = SearchService.is_index_or_etf(
            context.get("code", ""), enhanced.get("stock_name", stock_name)
        )

        # P0: append unified fundamental block; keep as additional context only
        enhanced["fundamental_context"] = (
            fundamental_context
            if isinstance(fundamental_context, dict)
            else self.fetcher_manager.build_failed_fundamental_context(
                context.get("code", ""),
                "invalid fundamental context",
            )
        )

        return enhanced

    def augment_historical_with_realtime(self, df: pd.DataFrame, realtime_quote: Any, code: str) -> pd.DataFrame:
        """
        使用当日实时行情补齐历史 OHLCV，用于盘中 MA 计算。
        Issue #234：技术指标使用实时价格，而不是沿用昨日收盘价。
        """
        if df is None or df.empty or "close" not in df.columns:
            return df
        if realtime_quote is None:
            return df
        price = getattr(realtime_quote, "price", None)
        if price is None or not (isinstance(price, (int, float)) and price > 0):
            return df

        # 非交易日可跳过实时补齐；异常情况下保持失败开放。
        enable_realtime_tech = getattr(self.config, "enable_realtime_technical_indicators", True)
        if not enable_realtime_tech:
            return df
        market = get_market_for_stock(code)
        market_today = get_market_now(market).date()
        if market and not is_market_open(market, market_today):
            return df

        last_val = df["date"].max()
        last_date = (
            last_val.date()
            if hasattr(last_val, "date")
            else (last_val if isinstance(last_val, date) else pd.Timestamp(last_val).date())
        )
        yesterday_close = float(df.iloc[-1]["close"]) if len(df) > 0 else price
        open_p = (
            getattr(realtime_quote, "open_price", None) or getattr(realtime_quote, "pre_close", None) or yesterday_close
        )
        high_p = getattr(realtime_quote, "high", None) or price
        low_p = getattr(realtime_quote, "low", None) or price
        vol = getattr(realtime_quote, "volume", None) or 0
        amt = getattr(realtime_quote, "amount", None)
        pct = getattr(realtime_quote, "change_pct", None)

        if last_date >= market_today:
            # 使用实时收盘价更新最后一行；先复制，避免修改调用方传入的 df。
            df = df.copy()
            idx = df.index[-1]
            df.loc[idx, "close"] = price
            if open_p is not None:
                df.loc[idx, "open"] = open_p
            if high_p is not None:
                df.loc[idx, "high"] = high_p
            if low_p is not None:
                df.loc[idx, "low"] = low_p
            if vol:
                df.loc[idx, "volume"] = vol
            if amt is not None:
                df.loc[idx, "amount"] = amt
            if pct is not None:
                df.loc[idx, "pct_chg"] = pct
        else:
            # 追加一行虚拟的当日实时 K 线。
            new_row = {
                "code": code,
                "date": market_today,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": price,
                "volume": vol,
                "amount": amt if amt is not None else 0,
                "pct_chg": pct if pct is not None else 0,
            }
            new_df = pd.DataFrame([new_row])
            df = pd.concat([df, new_df], ignore_index=True)
        return df

    def describe_volume_ratio(self, volume_ratio: float) -> str:
        """量比描述（量比 = 当前成交量 / 过去 5 日平均成交量）。"""
        return _pipeline_rules.describe_volume_ratio(volume_ratio)

    @staticmethod
    def compute_ma_status(close: float, ma5: float, ma10: float, ma20: float) -> str:
        """Compute MA alignment status from price and MA values."""
        return _pipeline_rules.compute_ma_status(close, ma5, ma10, ma20)
