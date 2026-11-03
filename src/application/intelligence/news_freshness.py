"""Pure news date normalization, freshness filtering and result limiting."""

from __future__ import annotations
import logging
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Any, Optional
from src.domain.search import SearchResponse, SearchResult

logger = logging.getLogger("src.application.intelligence.search_service")


FUTURE_TOLERANCE_DAYS = 1


def parse_relative_news_date(text: str, now: datetime) -> Optional[date]:
    """Parse common Chinese/English relative-time strings."""
    raw = (text or "").strip()
    if not raw:
        return None
    lower = raw.lower()
    if raw in {"今天", "今日", "刚刚"} or lower in {"today", "just now", "now"}:
        return now.date()
    if raw == "昨天" or lower == "yesterday":
        return (now - timedelta(days=1)).date()
    if raw == "前天":
        return (now - timedelta(days=2)).date()
    zh = re.match("^\\s*(\\d+)\\s*(分钟|小时|天|周|个月|月|年)\\s*前\\s*$", raw)
    if zh:
        amount = int(zh.group(1))
        unit = zh.group(2)
        if unit == "分钟":
            return (now - timedelta(minutes=amount)).date()
        if unit == "小时":
            return (now - timedelta(hours=amount)).date()
        if unit == "天":
            return (now - timedelta(days=amount)).date()
        if unit == "周":
            return (now - timedelta(weeks=amount)).date()
        if unit in {"个月", "月"}:
            return (now - timedelta(days=amount * 30)).date()
        if unit == "年":
            return (now - timedelta(days=amount * 365)).date()
    en = re.match(
        "^\\s*(\\d+)\\s*(minute|minutes|min|mins|hour|hours|day|days|week|weeks|month|months|year|years)\\s*ago\\s*$",
        lower,
    )
    if en:
        amount = int(en.group(1))
        unit = en.group(2)
        if unit in {"minute", "minutes", "min", "mins"}:
            return (now - timedelta(minutes=amount)).date()
        if unit in {"hour", "hours"}:
            return (now - timedelta(hours=amount)).date()
        if unit in {"day", "days"}:
            return (now - timedelta(days=amount)).date()
        if unit in {"week", "weeks"}:
            return (now - timedelta(weeks=amount)).date()
        if unit in {"month", "months"}:
            return (now - timedelta(days=amount * 30)).date()
        if unit in {"year", "years"}:
            return (now - timedelta(days=amount * 365)).date()
    return None


def normalize_news_publish_date(value: Any) -> Optional[date]:
    """Normalize provider date value into a date object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            local_tz = datetime.now().astimezone().tzinfo or timezone.utc
            return value.astimezone(local_tz).date()
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    now = datetime.now()
    local_tz = now.astimezone().tzinfo or timezone.utc
    relative_date = parse_relative_news_date(text, now)
    if relative_date:
        return relative_date
    if text.isdigit() and len(text) in (10, 13):
        try:
            ts = int(text[:10]) if len(text) == 13 else int(text)
            return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(local_tz).date()
        except (OSError, OverflowError, ValueError):
            pass
    iso_candidate = text.replace("Z", "+00:00")
    try:
        parsed_iso = datetime.fromisoformat(iso_candidate)
        if parsed_iso.tzinfo is not None:
            return parsed_iso.astimezone(local_tz).date()
        return parsed_iso.date()
    except ValueError:
        pass
    normalized = re.sub("(\\d+)(st|nd|rd|th)", "\\1", text, flags=re.IGNORECASE)
    try:
        parsed_rfc = parsedate_to_datetime(normalized)
        if parsed_rfc:
            if parsed_rfc.tzinfo is not None:
                return parsed_rfc.astimezone(local_tz).date()
            return parsed_rfc.date()
    except (TypeError, ValueError):
        pass
    zh_match = re.search("(\\d{4})\\s*[年/\\-.]\\s*(\\d{1,2})\\s*[月/\\-.]\\s*(\\d{1,2})\\s*日?", text)
    if zh_match:
        try:
            return date(int(zh_match.group(1)), int(zh_match.group(2)), int(zh_match.group(3)))
        except ValueError:
            pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y.%m.%d",
        "%Y%m%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%a, %d %b %Y %H:%M:%S %z",
    ):
        try:
            parsed_dt = datetime.strptime(normalized, fmt)
            if parsed_dt.tzinfo is not None:
                return parsed_dt.astimezone(local_tz).date()
            return parsed_dt.date()
        except ValueError:
            continue
    return None


def filter_news_response(
    response: SearchResponse, *, search_days: int, max_results: int, log_scope: str, keep_unknown: bool = False
) -> SearchResponse:
    """Hard-filter results by published_date recency and normalize date strings."""
    if not response.success or not response.results:
        return response
    today = datetime.now().date()
    earliest = today - timedelta(days=max(0, int(search_days) - 1))
    latest = today + timedelta(days=FUTURE_TOLERANCE_DAYS)
    filtered: List[SearchResult] = []
    dropped_unknown = 0
    dropped_old = 0
    dropped_future = 0
    for item in response.results:
        published = normalize_news_publish_date(item.published_date)
        if published is None:
            if keep_unknown:
                filtered.append(
                    SearchResult(
                        title=item.title,
                        snippet=item.snippet,
                        url=item.url,
                        source=item.source,
                        published_date=item.published_date,
                        relevance_score=item.relevance_score,
                        relevance_category=item.relevance_category,
                        relevance_reasons=item.relevance_reasons,
                    )
                )
                if len(filtered) >= max_results:
                    break
                continue
            dropped_unknown += 1
            continue
        if published < earliest:
            dropped_old += 1
            continue
        if published > latest:
            dropped_future += 1
            continue
        filtered.append(
            SearchResult(
                title=item.title,
                snippet=item.snippet,
                url=item.url,
                source=item.source,
                published_date=published.isoformat(),
                relevance_score=item.relevance_score,
                relevance_category=item.relevance_category,
                relevance_reasons=item.relevance_reasons,
            )
        )
        if len(filtered) >= max_results:
            break
    if dropped_unknown or dropped_old or dropped_future:
        logger.info(
            "[新闻过滤] %s: provider=%s, total=%s, kept=%s, drop_unknown=%s, drop_old=%s, drop_future=%s, window=[%s,%s]",
            log_scope,
            response.provider,
            len(response.results),
            len(filtered),
            dropped_unknown,
            dropped_old,
            dropped_future,
            earliest.isoformat(),
            latest.isoformat(),
        )
    return SearchResponse(
        query=response.query,
        results=filtered,
        provider=response.provider,
        success=response.success,
        error_message=response.error_message,
        search_time=response.search_time,
    )


def normalize_and_limit_response(response: SearchResponse, *, max_results: int) -> SearchResponse:
    """Normalize parseable dates without enforcing freshness filtering."""
    if not response.success or not response.results:
        return response
    normalized_results: List[SearchResult] = []
    for item in response.results[:max_results]:
        normalized_date = normalize_news_publish_date(item.published_date)
        normalized_results.append(
            SearchResult(
                title=item.title,
                snippet=item.snippet,
                url=item.url,
                source=item.source,
                published_date=normalized_date.isoformat() if normalized_date is not None else item.published_date,
                relevance_score=item.relevance_score,
                relevance_category=item.relevance_category,
                relevance_reasons=item.relevance_reasons,
            )
        )
    return SearchResponse(
        query=response.query,
        results=normalized_results,
        provider=response.provider,
        success=response.success,
        error_message=response.error_message,
        search_time=response.search_time,
    )


def limit_search_response(response: SearchResponse, *, max_results: int) -> SearchResponse:
    """Trim response results without changing the rest of the metadata."""
    if not response.success or not response.results:
        return response
    limited_results = response.results[:max_results]
    if len(limited_results) == len(response.results):
        return response
    return SearchResponse(
        query=response.query,
        results=limited_results,
        provider=response.provider,
        success=response.success,
        error_message=response.error_message,
        search_time=response.search_time,
    )
