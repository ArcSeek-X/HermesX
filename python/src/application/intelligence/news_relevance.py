"""Pure news relevance, language selection and quality filtering."""

from __future__ import annotations
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import unquote, urlparse
from src.domain.market.us_index_symbols import is_us_index_code
from src.domain.search import SearchResponse, SearchResult
from src.data.stock_mapping import canonicalize_foreign_stock_code, foreign_stock_english_aliases

logger = logging.getLogger("src.application.intelligence.search_service")


NEWS_OVERSAMPLE_FACTOR = 2

NEWS_OVERSAMPLE_MAX = 10

_CHINESE_TEXT_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")

_US_STOCK_RE = re.compile(r"^[A-Za-z]{1,5}(\.[A-Za-z])?$")

_DIRECT_NEWS_CATEGORY = "direct_company_news"

_SECTOR_NEWS_CATEGORY = "sector_related_news"

_MACRO_NEWS_CATEGORY = "macro_market_news"

_NEWS_CATEGORY_PRIORITY = {
    _DIRECT_NEWS_CATEGORY: 0,
    _SECTOR_NEWS_CATEGORY: 1,
    _MACRO_NEWS_CATEGORY: 2,
}

_AMBIGUOUS_EN_COMPANY_NAMES = {"apple", "meta", "square", "target", "gap"}

_AMBIGUOUS_EN_CONFIRMING_EVENT_TERMS = (
    "earnings",
    "revenue",
    "profit",
    "guidance",
    "filing",
    "buyback",
    "dividend",
    "lawsuit",
    "merger",
    "acquisition",
)

_COMPANY_EVENT_TERMS = (
    "公告",
    "披露",
    "发布",
    "收购",
    "回购",
    "减持",
    "增持",
    "诉讼",
    "处罚",
    "业绩",
    "财报",
    "营收",
    "净利润",
    "分红",
    "董事会",
    "股东大会",
    "订单",
    "合作",
    "中标",
    "earnings",
    "revenue",
    "profit",
    "guidance",
    "filing",
    "sec",
    "shares",
    "stock",
    "buyback",
    "dividend",
    "lawsuit",
    "merger",
    "acquisition",
    "results",
    "quarterly",
    "annual",
    "announces",
    "launches",
)

_SECTOR_NEWS_TERMS = (
    "行业",
    "板块",
    "产业链",
    "龙头",
    "概念股",
    "赛道",
    "sector",
    "industry",
    "peers",
    "competitors",
    "supply chain",
    "market share",
)

_MACRO_NEWS_TERMS = (
    "大盘",
    "市场",
    "指数",
    "宏观",
    "央行",
    "利率",
    "通胀",
    "a股",
    "港股",
    "美股",
    "纳指",
    "标普",
    "market",
    "index",
    "fed",
    "inflation",
    "interest rate",
    "nasdaq",
    "s&p 500",
    "dow jones",
)

_OFFICIAL_SOURCE_HOSTS = (
    "cninfo.com.cn",
    "sse.com",
    "sse.com.cn",
    "szse.cn",
    "hkexnews.hk",
    "sec.gov",
    "nasdaq.com",
    "nyse.com",
)

_OFFICIAL_SOURCE_LABELS = (
    "cninfo",
    "hkexnews",
    "巨潮资讯",
    "巨潮资讯网",
    "上交所",
    "深交所",
    "港交所",
    "证券交易所",
    "上海证券交易所",
    "深圳证券交易所",
    "香港交易所",
    "香港联合交易所",
)

_LOW_QUALITY_DOWNLOAD_ACTION_TERMS = (
    "下载",
    "安装",
    "下载安装",
    "下载安装到手机",
    "下载链接",
    "免费下载",
    "客户端下载",
    "应用下载",
    "官方app下载",
    "安装包",
    "apk",
    "download",
    "install",
    "installer",
)

_LOW_QUALITY_DOWNLOAD_INTENT_TERMS = (
    "安装包",
    "客户端下载",
    "应用下载",
    "下载安装",
    "下载安装到手机",
    "下载链接",
    "免费下载",
    "旧版下载",
    "极速版下载",
    "官方app下载",
)

_LOW_QUALITY_APP_CONTEXT_TERMS = (
    "好评",
    "评分",
    "版本",
    "大小",
    "适用年龄",
    "开发者",
    "应用",
    "ratings",
    "reviews",
    "stars",
    "version",
    "developer",
    "package",
)

_LOW_QUALITY_APP_METADATA_TERMS = (
    "版本",
    "大小",
    "适用年龄",
    "开发者",
    "应用",
    "应用商店",
    "安卓版",
    "苹果版",
    "官方版",
    "最新版",
    "version",
    "developer",
    "package",
    "mobile app",
)

_LOW_QUALITY_APP_PAGE_DETAIL_TERMS = (
    "客户端",
    "安卓版",
    "苹果版",
    "官方版",
    "最新版",
    "应用商店",
    "下载安装到手机",
    "一键下载",
    "旧版下载",
    "极速版下载",
)

_LOW_QUALITY_FILE_SIZE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:kb|mb|gb)\b", re.IGNORECASE)

_LOW_QUALITY_RATING_RE = re.compile(
    r"(?:\d{1,3}\s*%\s*好评|好评率|用户评分|"
    r"(?:用户)?评分\s*[:：]?\s*(?:10|[0-9])(?:\.\d{1,2})?|"
    r"\b\d(?:\.\d)?\s*(?:stars?|ratings?|reviews?)\b)",
    re.IGNORECASE,
)

_LOW_QUALITY_URL_RE = re.compile(
    r"(?:^|[/_.=-])(?:download|downloads|apk|ipa|exe|dmg|installer|"
    r"software|soft|game|games|app|apps|package)(?:$|[/_.?&=-])",
    re.IGNORECASE,
)

_BUSINESS_APP_METRIC_RE = re.compile(
    r"(?:(?:下载量|安装量|装机量|应用下载|应用安装|app下载|app安装).{0,12}"
    r"(?:增长|同比|环比|上升|增加|提升|突破|达到|达|超过|超|累计|接近|保持|创新高|下降|下滑|减少|回落|放缓|持平|承压|低迷)|"
    r"(?:增长|同比|环比|上升|增加|提升|突破|达到|达|超过|超|累计|接近|保持|创新高|下降|下滑|减少|回落|放缓|持平|承压|低迷)"
    r".{0,12}(?:下载量|安装量|装机量|应用下载|应用安装|app下载|app安装)|"
    r"\b(?:downloads?|installs?)\b.{0,16}"
    r"\b(?:grew|growth|rose|increase|increased|surged|reached|reach|reaches|"
    r"hit|hits|topped|totaled|totalled|exceeded|exceeds|surpassed|surpasses|"
    r"fell|fall|declined|decline|decreased|dropped|drop|slowed|flat|weakened)\b|"
    r"\b(?:grew|growth|rose|increase|increased|surged|reached|reach|reaches|"
    r"hit|hits|topped|totaled|totalled|exceeded|exceeds|surpassed|surpasses|"
    r"fell|fall|declined|decline|decreased|dropped|drop|slowed|flat|weakened)\b"
    r".{0,16}\b(?:downloads?|installs?)\b)",
    re.IGNORECASE,
)

_ADULT_SERVICE_SPAM_STRONG_TERMS = (
    "上门特殊服务",
    "同城约",
    "约炮",
    "援交",
    "楼凤",
    "外围女",
    "外围服务",
    "包夜",
    "大保健",
    "莞式",
    "推油",
    "成人服务",
    "adult service",
    "escort service",
    "sex service",
    "call girl",
)

_ADULT_SERVICE_SPAM_AMBIGUOUS_TERMS = (
    "全套服务",
    "色情",
)

_ADULT_SERVICE_SPAM_CONTEXT_TERMS = (
    "小姐",
    "上门",
    "预约",
    "同城",
    "按摩",
    "保健",
    "足浴",
    "桑拿",
    "会所",
    "技师",
    "全套",
    "套餐",
    "vip",
)

_ADULT_SERVICE_SPAM_CONTACT_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:yue|vx|wx|qq|wechat|weixin|微信号?|微[信讯]|"
    r"电话|手机|联系电话|tel|phone)"
    r"[-_:\s：]*[a-z0-9][a-z0-9_-]{2,}(?:[^a-z0-9]|$)",
    re.IGNORECASE,
)

_ADULT_SERVICE_SPAM_CONTACT_CONTEXT_TERMS = (
    "小姐",
    "上门",
    "同城",
    "预约",
    "全套",
    "包夜",
    "大保健",
    "推油",
    "约炮",
    "援交",
    "成人",
    "色情",
)

_ADULT_SERVICE_REMEDIATION_TERMS = (
    "治理",
    "整治",
    "下架",
    "处罚",
    "监管",
    "打击",
    "清理",
    "封禁",
    "整改",
    "内容安全",
    "低俗内容",
    "平台风险",
)

_ADULT_SERVICE_SOLICITATION_TERMS = (
    "上门",
    "同城",
    "预约",
    "套餐",
    "包夜",
    "大保健",
    "推油",
    "联系",
    "咨询",
    "加微信",
    "加qq",
    "vip",
)

_A_ETF_PREFIXES = ("51", "52", "56", "58", "15", "16", "18")

_ETF_NAME_KEYWORDS = ("ETF", "FUND", "TRUST", "INDEX", "TRACKER", "UNIT")  # US/HK ETF name hints


def is_foreign_stock(stock_code: str) -> bool:
    """判断是否为港股或美股。

    Honours all canonical input forms — bare ticker (``AAPL`` / ``00700``),
    suffixed ticker (``AAPL.US`` / ``00700.HK``), and prefixed HK ticker
    (``HK00700``) — by canonicalizing to the key form used in
    STOCK_ENGLISH_NAME_MAP before applying the existing structural checks.
    This is the canonical-boundary unification that massif-01 asked for on
    PR #2047 (so alias resolution and foreign-ness detection no longer
    disagree on the same input).
    """
    code = canonicalize_foreign_stock_code(stock_code).strip()
    if not code:
        return False
    if _US_STOCK_RE.match(code):
        return True
    if code.isdigit() and len(code) == 5:
        return True
    return False


def foreign_english_query_terms(stock_code: str, stock_name: str) -> Tuple[str, ...]:
    """Return English company name(s) to embed in foreign-stock search
    queries. issue #2026: When STOCK_NAME_MAP maps a foreign ticker to a
    Chinese display name, the search layer must not pass that Chinese name
    to English news providers, otherwise the provider misses English
    headlines entirely.

    Returns the canonical alias tuple from ``STOCK_ENGLISH_NAME_MAP`` if the
    supplied ``stock_name`` is Chinese and the canonical ticker has English
    aliases. Otherwise returns an empty tuple (callers fall back to
    ``stock_name`` itself).

    Kept deliberately small and read-only: this helper never mutates the
    alias set and never invents aliases outside the single source of truth
    in ``src/data/stock_mapping.py``.
    """
    return foreign_stock_english_aliases(stock_code, stock_name)


def contains_chinese_text(value: Optional[str]) -> bool:
    """Return True when the input contains CJK characters."""
    return bool(value and _CHINESE_TEXT_RE.search(value))


def is_us_stock(stock_code: str) -> bool:
    """判断是否为美股/美股指数代码。"""
    code = (stock_code or "").strip().upper()
    return bool(_US_STOCK_RE.match(code) or is_us_index_code(code))


def should_prefer_chinese_news(stock_code: str, stock_name: str, focus_keywords: Optional[List[str]] = None) -> bool:
    """A 股或中文名称/关键词场景下优先中文资讯。

    Only returns True when there is a positive Chinese signal:
    Chinese characters in keywords/stock_name, or a 6-digit A-stock code.
    Avoids false positives for non-foreign but English contexts like
    ``stock_code="market", stock_name="US market"``.
    """
    if any((contains_chinese_text(keyword) for keyword in focus_keywords or [])):
        return True
    if contains_chinese_text(stock_name):
        return True
    code = (stock_code or "").strip()
    return code.isdigit() and len(code) == 6


def is_chinese_news_result(item: SearchResult) -> bool:
    """Heuristic check for Chinese-language news items."""
    return contains_chinese_text(" ".join(filter(None, [item.title, item.snippet, item.source])))


def prioritize_news_language(response: SearchResponse, *, prefer_chinese: bool) -> Tuple[SearchResponse, int]:
    """Reorder results by preferred language and return preferred-result count."""
    if not prefer_chinese or not response.success or (not response.results):
        return (response, 0)
    chinese_results: List[SearchResult] = []
    other_results: List[SearchResult] = []
    for item in response.results:
        if is_chinese_news_result(item):
            chinese_results.append(item)
        else:
            other_results.append(item)
    return (
        SearchResponse(
            query=response.query,
            results=chinese_results + other_results,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        ),
        len(chinese_results),
    )


def is_better_preferred_news_response(
    candidate: SearchResponse,
    *,
    candidate_preferred_count: int,
    best_response: Optional[SearchResponse],
    best_preferred_count: int,
) -> bool:
    """Prefer responses with more Chinese items, then more total items."""
    if best_response is None:
        return True
    if candidate_preferred_count != best_preferred_count:
        return candidate_preferred_count > best_preferred_count
    return len(candidate.results) > len(best_response.results)


def brave_search_locale(stock_code: str, *, prefer_chinese: bool) -> Dict[str, str]:
    """Resolve Brave locale hints without forcing US bias onto non-US symbols."""
    if prefer_chinese:
        return {"search_lang": "zh-hans", "country": "CN"}
    if is_us_stock(stock_code):
        return {"search_lang": "en", "country": "US"}
    return {}


def is_index_or_etf(stock_code: str, stock_name: str) -> bool:
    """
    Judge if symbol is index-tracking ETF or market index.
    For such symbols, analysis focuses on index movement only, not issuer company risks.
    """
    code = (stock_code or "").strip().split(".")[0]
    if not code:
        return False
    if code.isdigit() and len(code) == 6 and code.startswith(_A_ETF_PREFIXES):
        return True
    if is_us_index_code(code):
        return True
    if is_foreign_stock(code):
        name_upper = (stock_name or "").upper()
        return any((kw in name_upper for kw in _ETF_NAME_KEYWORDS))
    return False


def provider_request_size(max_results: int) -> int:
    """Apply light overfetch before time filtering to avoid sparse outputs."""
    target = max(1, int(max_results))
    return max(target, min(target * NEWS_OVERSAMPLE_FACTOR, NEWS_OVERSAMPLE_MAX))


def append_unique(values: List[str], value: Optional[str]) -> None:
    """向列表追加去重后的非空字符串。"""
    cleaned = (value or "").strip()
    if cleaned and cleaned not in values:
        values.append(cleaned)


def stock_code_identity_terms(stock_code: str) -> List[str]:
    """Return code/ticker variants that should count as strong identity hits."""
    raw = (stock_code or "").strip()
    if not raw:
        return []
    terms: List[str] = []
    upper = raw.upper()
    code_for_variants = upper
    if "." in upper:
        base, suffix = upper.rsplit(".", 1)
        if suffix == "HK" and base.isdigit() and (1 <= len(base) <= 5):
            code_for_variants = f"HK{base.zfill(5)}"
        elif suffix in {"SH", "SZ", "SS", "BJ"} and base.isdigit() and (len(base) == 6):
            code_for_variants = base
        elif suffix == "US" and re.fullmatch("[A-Z]{1,5}", base):
            code_for_variants = base
    is_us_ticker = bool(_US_STOCK_RE.match(code_for_variants))
    if not is_us_ticker:
        append_unique(terms, raw)
        append_unique(terms, upper)
        if code_for_variants != upper:
            append_unique(terms, code_for_variants)
    lower = code_for_variants.lower()
    hk_digits = ""
    if lower.startswith("hk"):
        hk_digits = re.sub("\\D", "", code_for_variants)
    elif code_for_variants.isdigit() and len(code_for_variants) == 5:
        hk_digits = code_for_variants
    if hk_digits:
        padded = hk_digits.zfill(5)
        short = str(int(hk_digits)) if hk_digits.isdigit() else hk_digits.lstrip("0")
        append_unique(terms, padded)
        append_unique(terms, f"HK{padded}")
        append_unique(terms, f"{padded}.HK")
        append_unique(terms, f"{short}.HK")
        append_unique(terms, f"HKEX:{short}")
        return terms
    if code_for_variants.isdigit() and len(code_for_variants) == 6:
        suffix = ".SH" if code_for_variants.startswith(("5", "6", "9")) else ".SZ"
        append_unique(terms, f"{code_for_variants}{suffix}")
        return terms
    if _US_STOCK_RE.match(code_for_variants):
        append_unique(terms, f"${code_for_variants}")
        append_unique(terms, f"NASDAQ:{code_for_variants}")
        append_unique(terms, f"NYSE:{code_for_variants}")
        if len(code_for_variants) > 1:
            append_unique(terms, code_for_variants)
        return terms
    return terms


def company_identity_terms(stock_name: str) -> List[str]:
    """Return conservative company-name variants for relevance matching."""
    raw = (stock_name or "").strip()
    if not raw:
        return []
    terms: List[str] = []
    append_unique(terms, raw)
    without_market_suffix = re.sub("[-－（(].*$", "", raw).strip()
    append_unique(terms, without_market_suffix)
    if contains_chinese_text(raw):
        cleaned = re.sub(
            "(股份有限公司|有限责任公司|有限公司|控股集团|控股|集团|股份|公司)$", "", without_market_suffix
        ).strip()
        if len(cleaned) >= 4:
            append_unique(terms, cleaned)
    else:
        cleaned = re.sub(
            "\\b(incorporated|inc|corporation|corp|company|co|plc|ltd|limited|holdings?)\\.?$",
            "",
            without_market_suffix,
            flags=re.IGNORECASE,
        ).strip()
        if len(cleaned) >= 3:
            append_unique(terms, cleaned)
    return terms


def contains_identity_term(text: str, term: str) -> bool:
    """判断文本是否包含指定主体识别词。"""
    if not text or not term:
        return False
    if contains_chinese_text(term):
        start = 0
        while True:
            index = text.find(term, start)
            if index < 0:
                return False
            next_char = text[index + len(term) : index + len(term) + 1]
            if next_char not in {"镇", "村", "县"}:
                return True
            start = index + len(term)
    lower_text = text.lower()
    lower_term = term.lower()
    if lower_term.startswith("$"):
        return lower_term in lower_text
    pattern = "(?<![A-Za-z0-9])" + re.escape(lower_term) + "(?![A-Za-z0-9])"
    return bool(re.search(pattern, lower_text))


def contains_stock_code_identity_term(text: str, term: str) -> bool:
    """判断文本是否包含股票代码形式的识别词。"""
    if not text or not term:
        return False
    if _US_STOCK_RE.match(term) and term.upper() == term and (not term.startswith("$")):
        ticker_pattern = f"(?:{re.escape(term)}|{re.escape(term.lower())})"
        pattern = (
            "(?<![A-Za-z0-9$:.])"
            + ticker_pattern
            + "(?=$|[^A-Za-z0-9.]|\\.(?:US|us|O|o|N|n|NYSE|nyse|NASDAQ|nasdaq|AMEX|amex)\\b)"
        )
        return bool(re.search(pattern, text))
    return contains_identity_term(text, term)


def contains_any_news_term(text: str, terms: Tuple[str, ...]) -> bool:
    """判断文本是否命中任意新闻相关词。"""
    lower = (text or "").lower()
    return any((term.lower() in lower for term in terms))


def contains_any_low_quality_news_term(text: str, terms: Tuple[str, ...]) -> bool:
    """判断文本是否命中任意低质量新闻词。"""
    lower = (text or "").lower()
    if not lower:
        return False
    for term in terms:
        normalized_term = term.lower()
        if not normalized_term:
            continue
        if normalized_term.isascii() and re.search("[a-z0-9]", normalized_term):
            pattern = "(?<![A-Za-z0-9])" + re.escape(normalized_term) + "(?![A-Za-z0-9])"
            if re.search(pattern, lower):
                return True
            continue
        if normalized_term in lower:
            return True
    return False


def candidate_hostname(value: Any) -> str:
    """从候选值中提取主机名。"""
    raw = str(value or "").strip().lower()
    if not raw or re.search("\\s", raw):
        return ""
    parse_value = raw if re.match("^[a-z][a-z0-9+.-]*://", raw) or raw.startswith("//") else f"//{raw}"
    return (urlparse(parse_value).hostname or "").rstrip(".")


def source_resembles_hostname(value: Any) -> bool:
    """判断来源值是否形似主机名。"""
    raw = str(value or "").strip().lower()
    if not raw or re.search("\\s", raw):
        return False
    if re.match("^[a-z][a-z0-9+.-]*://", raw) or raw.startswith("//"):
        return True
    return bool(re.search("\\.[a-z0-9-]{2,}(?::\\d+)?/?$", raw))


def is_trusted_official_news_source(item: SearchResult) -> bool:
    """Only trust official exemptions from trusted hosts; fallback to labels only when URL host is absent."""
    url_host = candidate_hostname(item.url)
    source_label = str(item.source or "").strip().lower()
    source_host = candidate_hostname(item.source) if source_resembles_hostname(item.source) else ""
    if url_host:
        return any(
            (
                url_host == official_host or url_host.endswith(f".{official_host}")
                for official_host in _OFFICIAL_SOURCE_HOSTS
            )
        )
    if source_host:
        return any(
            (
                source_host == official_host or source_host.endswith(f".{official_host}")
                for official_host in _OFFICIAL_SOURCE_HOSTS
            )
        )
    return source_label in _OFFICIAL_SOURCE_LABELS


def has_low_quality_news_page_signal(item: SearchResult) -> bool:
    """Detect app/download/listing pages without relying on a domain blocklist."""
    content_text = " ".join(filter(None, [item.title, item.snippet])).lower()
    parsed_url = urlparse(item.url or "")
    url_surface = unquote(" ".join(filter(None, [parsed_url.netloc, parsed_url.path, parsed_url.query]))).lower()
    has_app_context = contains_any_low_quality_news_term(content_text, _LOW_QUALITY_APP_CONTEXT_TERMS)
    has_app_metadata = contains_any_low_quality_news_term(content_text, _LOW_QUALITY_APP_METADATA_TERMS)
    has_download_action = contains_any_low_quality_news_term(content_text, _LOW_QUALITY_DOWNLOAD_ACTION_TERMS)
    has_download_intent = contains_any_low_quality_news_term(content_text, _LOW_QUALITY_DOWNLOAD_INTENT_TERMS)
    has_app_page_detail = contains_any_low_quality_news_term(content_text, _LOW_QUALITY_APP_PAGE_DETAIL_TERMS)
    has_file_size = bool(_LOW_QUALITY_FILE_SIZE_RE.search(content_text))
    has_rating = bool(_LOW_QUALITY_RATING_RE.search(content_text))
    has_url_signal = bool(_LOW_QUALITY_URL_RE.search(url_surface))
    has_business_app_metric = bool(_BUSINESS_APP_METRIC_RE.search(content_text))
    has_app_listing_detail = (
        has_file_size
        or has_rating
        or contains_any_low_quality_news_term(
            content_text,
            (
                "版本",
                "适用年龄",
                "开发者",
                "应用商店",
                "安卓版",
                "苹果版",
                "官方版",
                "最新版",
                "version",
                "developer",
                "package",
            ),
        )
    )
    has_strong_app_page_evidence = has_app_listing_detail and (
        has_url_signal or has_download_intent or (has_download_action and has_app_metadata)
    )
    has_business_app_metric_only = has_business_app_metric and (not has_strong_app_page_evidence)
    has_app_listing_context = (
        not has_business_app_metric_only
        and has_app_context
        and has_app_metadata
        and (has_download_action or has_download_intent)
        and (has_file_size or has_rating)
    )
    has_content_download_page = not has_business_app_metric_only and (
        has_download_intent
        and (has_app_page_detail or has_file_size or has_rating)
        or (has_download_action and (has_app_metadata or has_file_size))
    )
    has_url_backed_download_page = (
        not has_business_app_metric_only
        and has_url_signal
        and (
            has_file_size
            or has_download_intent
            or (has_download_action and has_app_metadata)
            or (has_app_metadata and has_rating)
        )
    )
    return has_content_download_page or has_app_listing_context or has_url_backed_download_page


def has_adult_service_spam_news_page_signal(item: SearchResult) -> bool:
    """Detect adult-service spam by content signals instead of domain names."""
    combined_text = " ".join(filter(None, [item.title, item.snippet, item.source, item.url])).lower()
    if contains_any_news_term(combined_text, _ADULT_SERVICE_SPAM_STRONG_TERMS):
        return True
    has_contact_signal = bool(_ADULT_SERVICE_SPAM_CONTACT_RE.search(combined_text))
    has_remediation_context = contains_any_news_term(combined_text, _ADULT_SERVICE_REMEDIATION_TERMS)
    if has_remediation_context and (not has_contact_signal):
        return False
    if "外围" in combined_text and contains_any_news_term(
        combined_text, ("上门", "同城", "约炮", "援交", "包夜", "大保健", "推油", "小姐", "技师")
    ):
        return True
    context_hits = sum((1 for term in _ADULT_SERVICE_SPAM_CONTEXT_TERMS if term.lower() in combined_text))
    has_service_anchor = contains_any_news_term(combined_text, ("小姐", "按摩", "足浴", "桑拿", "会所", "技师"))
    has_adult_specific_anchor = contains_any_news_term(
        combined_text, ("小姐", "约炮", "援交", "楼凤", "外围", "包夜", "大保健", "莞式", "推油", "成人", "色情")
    )
    if has_contact_signal:
        return has_adult_specific_anchor and contains_any_news_term(
            combined_text, _ADULT_SERVICE_SPAM_CONTACT_CONTEXT_TERMS
        )
    has_solicitation_signal = contains_any_news_term(combined_text, _ADULT_SERVICE_SOLICITATION_TERMS)
    has_ambiguous_adult_phrase = contains_any_news_term(combined_text, _ADULT_SERVICE_SPAM_AMBIGUOUS_TERMS)
    if has_ambiguous_adult_phrase:
        return has_service_anchor and has_solicitation_signal
    return has_adult_specific_anchor and has_service_anchor and has_solicitation_signal and (context_hits >= 3)


def score_news_relevance(item: SearchResult, *, stock_code: str, stock_name: str) -> SearchResult:
    """Attach conservative, explainable relevance metadata to one news item."""
    title = item.title or ""
    snippet = item.snippet or ""
    url = item.url or ""
    source = item.source or ""
    full_text = " ".join([title, snippet, url, source])
    score = 0
    direct_signal = 0
    reasons: List[str] = []
    has_stock_code_signal = False
    has_unambiguous_company_signal = False
    has_ambiguous_company_signal = False

    def add_reason(reason: str) -> None:
        """追加一条相关性判定理由。"""
        if reason not in reasons and len(reasons) < 5:
            reasons.append(reason)

    for term in stock_code_identity_terms(stock_code):
        if contains_stock_code_identity_term(title, term):
            score += 55
            direct_signal += 55
            has_stock_code_signal = True
            add_reason(f"标题命中股票代码 {term}")
            break
    else:
        for term in stock_code_identity_terms(stock_code):
            if contains_stock_code_identity_term(snippet, term):
                score += 34
                direct_signal += 34
                has_stock_code_signal = True
                add_reason(f"摘要命中股票代码 {term}")
                break
        else:
            for term in stock_code_identity_terms(stock_code):
                if contains_stock_code_identity_term(url, term):
                    score += 18
                    direct_signal += 18
                    has_stock_code_signal = True
                    add_reason(f"链接命中股票代码 {term}")
                    break
    for term in company_identity_terms(stock_name):
        ambiguous_en = not contains_chinese_text(term) and term.lower() in _AMBIGUOUS_EN_COMPANY_NAMES
        title_score = 26 if ambiguous_en else 45
        snippet_score = 16 if ambiguous_en else 28
        if contains_identity_term(title, term):
            score += title_score
            direct_signal += title_score
            if ambiguous_en:
                has_ambiguous_company_signal = True
            else:
                has_unambiguous_company_signal = True
            add_reason(f"标题命中公司名 {term}")
            break
        if contains_identity_term(snippet, term):
            score += snippet_score
            direct_signal += snippet_score
            if ambiguous_en:
                has_ambiguous_company_signal = True
            else:
                has_unambiguous_company_signal = True
            add_reason(f"摘要命中公司名 {term}")
            break
    english_aliases = foreign_stock_english_aliases(stock_code, stock_name)
    if english_aliases:
        seen_identity_terms: set = set()
        for alias in english_aliases:
            for term in company_identity_terms(alias):
                if term in seen_identity_terms:
                    continue
                seen_identity_terms.add(term)
                ambiguous_en = not contains_chinese_text(term) and term.lower() in _AMBIGUOUS_EN_COMPANY_NAMES
                title_score = 26 if ambiguous_en else 45
                snippet_score = 16 if ambiguous_en else 28
                if contains_identity_term(title, term):
                    score += title_score
                    direct_signal += title_score
                    if ambiguous_en:
                        has_ambiguous_company_signal = True
                    else:
                        has_unambiguous_company_signal = True
                    add_reason(f"标题命中公司英文别名 {term}")
                    break
                if contains_identity_term(snippet, term):
                    score += snippet_score
                    direct_signal += snippet_score
                    if ambiguous_en:
                        has_ambiguous_company_signal = True
                    else:
                        has_unambiguous_company_signal = True
                    add_reason(f"摘要命中公司英文别名 {term}")
                    break
    has_company_event = contains_any_news_term(full_text, _COMPANY_EVENT_TERMS)
    if has_company_event and direct_signal > 0:
        score += 12
        ambiguous_name_only = (
            has_ambiguous_company_signal and (not has_stock_code_signal) and (not has_unambiguous_company_signal)
        )
        has_confirming_event = contains_any_news_term(full_text, _AMBIGUOUS_EN_CONFIRMING_EVENT_TERMS)
        if not ambiguous_name_only or has_confirming_event:
            direct_signal += 12
        add_reason("命中公告/财报/交易等公司事件词")
    if is_trusted_official_news_source(item):
        score += 8
        add_reason("来源接近公告或交易所渠道")
    has_sector_signal = contains_any_news_term(full_text, _SECTOR_NEWS_TERMS)
    has_macro_signal = contains_any_news_term(full_text, _MACRO_NEWS_TERMS)
    if direct_signal >= 38:
        category = _DIRECT_NEWS_CATEGORY
    elif has_macro_signal and (not direct_signal):
        category = _MACRO_NEWS_CATEGORY
        score = max(0, score - 12)
        add_reason("未命中目标公司身份，归为宏观/市场新闻")
    else:
        category = _SECTOR_NEWS_CATEGORY
        if has_sector_signal:
            score += 6
            add_reason("仅命中行业或板块背景")
        else:
            add_reason("未命中股票代码或公司全称，降级为背景新闻")
    score = max(0, min(100, score))
    return SearchResult(
        title=item.title,
        snippet=item.snippet,
        url=item.url,
        source=item.source,
        published_date=item.published_date,
        relevance_score=score,
        relevance_category=category,
        relevance_reasons=reasons,
    )


def rank_news_response(
    response: SearchResponse,
    *,
    stock_code: str,
    stock_name: str,
    prefer_chinese: bool,
    max_results: int,
    log_scope: str,
) -> SearchResponse:
    """Score and sort news so direct company items are not crowded out."""
    if not response.success or not response.results:
        return response
    scored_results = [
        score_news_relevance(item, stock_code=stock_code, stock_name=stock_name) for item in response.results
    ]
    indexed_results = list(enumerate(scored_results))

    def sort_key(entry: Tuple[int, SearchResult]) -> Tuple[int, int, int, int]:
        """生成新闻结果排序用的比较键。"""
        index, result = entry
        category = result.relevance_category or _SECTOR_NEWS_CATEGORY
        category_rank = _NEWS_CATEGORY_PRIORITY.get(category, 9)
        language_rank = 0 if prefer_chinese and is_chinese_news_result(result) else 1
        if not prefer_chinese:
            language_rank = 0
        score = result.relevance_score or 0
        return (category_rank, language_rank, -score, index)

    ranked_results = [result for _, result in sorted(indexed_results, key=sort_key)]
    limited_results = ranked_results[:max_results]
    category_counts = {_DIRECT_NEWS_CATEGORY: 0, _SECTOR_NEWS_CATEGORY: 0, _MACRO_NEWS_CATEGORY: 0}
    for result in limited_results:
        if result.relevance_category in category_counts:
            category_counts[result.relevance_category] += 1
    if limited_results:
        top = limited_results[0]
        logger.info(
            "[新闻相关度] %s: direct=%s, sector=%s, macro=%s, top_score=%s, top_category=%s, reasons=%s",
            log_scope,
            category_counts[_DIRECT_NEWS_CATEGORY],
            category_counts[_SECTOR_NEWS_CATEGORY],
            category_counts[_MACRO_NEWS_CATEGORY],
            top.relevance_score,
            top.relevance_category,
            "；".join(top.relevance_reasons or []),
        )
    return SearchResponse(
        query=response.query,
        results=limited_results,
        provider=response.provider,
        success=response.success,
        error_message=response.error_message,
        search_time=response.search_time,
    )


def filter_ranked_news_for_context(response: SearchResponse, *, log_scope: str) -> SearchResponse:
    """Drop obvious non-news pages and zero-relevance fillers from ranked results."""
    if not response.success or not response.results:
        return response
    candidates: List[SearchResult] = []
    dropped_low_quality = 0
    dropped_adult_spam = 0
    dropped_zero_relevance = 0
    for item in response.results:
        is_official_source = is_trusted_official_news_source(item)
        if not is_official_source and has_low_quality_news_page_signal(item):
            dropped_low_quality += 1
            continue
        if not is_official_source and has_adult_service_spam_news_page_signal(item):
            dropped_adult_spam += 1
            continue
        candidates.append(item)
    meaningful_candidates = [
        item
        for item in candidates
        if item.relevance_category == _DIRECT_NEWS_CATEGORY or (item.relevance_score or 0) > 0
    ]
    if meaningful_candidates:
        dropped_zero_relevance = len(candidates) - len(meaningful_candidates)
        filtered_results = meaningful_candidates
    else:
        filtered_results = candidates
    if dropped_low_quality or dropped_adult_spam or dropped_zero_relevance:
        logger.info(
            "[新闻准入] %s: provider=%s, total=%s, kept=%s, drop_low_quality=%s, drop_adult_spam=%s, drop_zero_relevance=%s",
            log_scope,
            response.provider,
            len(response.results),
            len(filtered_results),
            dropped_low_quality,
            dropped_adult_spam,
            dropped_zero_relevance,
        )
    return SearchResponse(
        query=response.query,
        results=filtered_results,
        provider=response.provider,
        success=response.success,
        error_message=response.error_message,
        search_time=response.search_time,
    )


def news_relevance_stats(response: SearchResponse, *, prefer_chinese: bool) -> Dict[str, int]:
    """统计检索响应中各相关性分级数量。"""
    results = response.results if response and response.results else []
    return {
        "direct_count": sum((1 for item in results if item.relevance_category == _DIRECT_NEWS_CATEGORY)),
        "preferred_direct_count": sum(
            (
                1
                for item in results
                if prefer_chinese and item.relevance_category == _DIRECT_NEWS_CATEGORY and is_chinese_news_result(item)
            )
        ),
        "preferred_count": sum((1 for item in results if prefer_chinese and is_chinese_news_result(item))),
        "max_score": max((item.relevance_score or 0 for item in results), default=0),
        "result_count": len(results),
    }


def is_better_ranked_news_response(
    candidate: SearchResponse,
    *,
    candidate_stats: Dict[str, int],
    best_response: Optional[SearchResponse],
    best_stats: Optional[Dict[str, int]],
    prefer_chinese: bool,
) -> bool:
    """比较两个新闻检索响应的排序质量。"""
    if best_response is None or best_stats is None:
        return True
    if candidate_stats["direct_count"] != best_stats["direct_count"]:
        return candidate_stats["direct_count"] > best_stats["direct_count"]
    if prefer_chinese and candidate_stats["preferred_direct_count"] != best_stats["preferred_direct_count"]:
        return candidate_stats["preferred_direct_count"] > best_stats["preferred_direct_count"]
    if prefer_chinese and candidate_stats["preferred_count"] != best_stats["preferred_count"]:
        return candidate_stats["preferred_count"] > best_stats["preferred_count"]
    if candidate_stats["max_score"] != best_stats["max_score"]:
        return candidate_stats["max_score"] > best_stats["max_score"]
    return candidate_stats["result_count"] > best_stats["result_count"]
