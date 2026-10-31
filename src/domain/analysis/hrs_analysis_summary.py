# -*- coding: utf-8 -*-
"""HRS 候选分析摘要纯规则：从行情/基本面/资讯 dict 组装展示文本。

被 application 候选规整与 infrastructure 运行时桥共同复用，纯 dict 操作无 IO。
"""

from __future__ import annotations

from typing import Any, Dict, List


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _build_hrs_analysis_summary(
    candidate: Dict[str, Any],
    quote: Dict[str, Any],
    fundamentals: Dict[str, Any],
    news: Dict[str, Any],
) -> str:
    parts: List[str] = []
    price = _first_non_empty(quote.get("price"), candidate.get("price"))
    change_pct = _first_non_empty(quote.get("change_pct"), candidate.get("change_pct"))
    if price is not None:
        text = f"HRS行情：现价 {price}"
        if change_pct is not None:
            text += f"，涨跌幅 {change_pct}%"
        parts.append(text)

    coverage = fundamentals.get("coverage") if isinstance(fundamentals, dict) else {}
    if isinstance(coverage, dict) and coverage:
        available_blocks = [key for key, value in coverage.items() if str(value).lower() in {"available", "partial"}]
        if available_blocks:
            parts.append(f"HRS基本面覆盖：{', '.join(available_blocks[:4])}")

    news_results = news.get("results") if isinstance(news, dict) else []
    if isinstance(news_results, list) and news_results:
        titles = [str(item.get("title") or "").strip() for item in news_results if isinstance(item, dict)]
        titles = [title for title in titles if title]
        if titles:
            parts.append(f"HRS新闻：{'；'.join(titles[:2])}")

    if not parts:
        return ""
    return "；".join(parts)


def _extract_hrs_news_from_context(context: Any) -> List[Dict[str, Any]]:
    if not isinstance(context, dict):
        return []
    news = context.get("news")
    if isinstance(news, dict):
        results = news.get("results")
    elif isinstance(news, list):
        results = news
    else:
        results = None
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def _extract_hrs_analysis_summary_from_context(context: Any) -> str:
    if not isinstance(context, dict):
        return ""
    for key in ("hrs_analysis_summary", "analysis_summary", "summary"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    news = context.get("news")
    if isinstance(news, dict):
        for key in ("analysis_summary", "summary"):
            value = news.get(key)
            if isinstance(value, str) and value.strip():
                return value
    news_items = _extract_hrs_news_from_context(context)
    if not news_items:
        return ""
    quote = context.get("quote") if isinstance(context.get("quote"), dict) else {}
    fundamentals = context.get("fundamentals") if isinstance(context.get("fundamentals"), dict) else {}
    return _build_hrs_analysis_summary({}, quote, fundamentals, {"results": news_items})
