"""RSS, Atom and NewsNow parsing without request, repository or runtime state."""

from __future__ import annotations
import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List, Optional
from xml.etree import ElementTree as ET
from src.domain.search.feed import FeedEntry, IntelligenceServiceError

logger = logging.getLogger("src.application.intelligence.intelligence_service")


class FeedParser:
    """Parse feed content; URL validation remains an explicit caller dependency."""

    def __init__(self, url_validator):
        """构造信息流解析器：保存 URL 校验器。"""
        self._url_validator = url_validator

    def parse_feed(self, content: bytes, *, source_name: str, limit: int) -> List[FeedEntry]:
        """解析 RSS / Atom XML，按根节点类型分发到对应解析器并截断到 limit 条。"""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise IntelligenceServiceError(f"invalid RSS/Atom feed: {exc}") from exc
        tag = self.strip_ns(root.tag).lower()
        if tag == "rss":
            nodes = root.findall("./channel/item")
            return [entry for entry in (self.parse_rss_item(node, source_name) for node in nodes[:limit]) if entry]
        if tag == "feed":
            nodes = root.findall("./{*}entry") or root.findall("./entry")
            return [entry for entry in (self.parse_atom_entry(node, source_name) for node in nodes[:limit]) if entry]
        raise IntelligenceServiceError("unsupported feed format; expected RSS or Atom")

    def parse_newsnow_payload(self, payload: Any, *, source_name: str, limit: int) -> List[FeedEntry]:
        """解析 NewsNow 响应：要求形如 {"items": [{title, url, extra{info/hover/date}, pubDate}]}。"""
        if not isinstance(payload, dict):
            raise IntelligenceServiceError("invalid NewsNow response: expected object")
        items = payload.get("items")
        if not isinstance(items, list):
            raise IntelligenceServiceError("invalid NewsNow response: missing items")
        entries = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            # 摘要优先取 extra.info，其次 extra.hover；链接优先 url，其次 mobileUrl
            extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
            published_raw = item.get("pubDate") or extra.get("date")
            entries.append(
                self.build_entry(
                    str(item.get("title") or ""),
                    str(extra.get("info") or extra.get("hover") or ""),
                    str(item.get("url") or item.get("mobileUrl") or ""),
                    source_name,
                    self.parse_datetime_or_timestamp(published_raw),
                )
            )
        return [entry for entry in entries if entry]

    def parse_rss_item(self, node: ET.Element, source_name: str) -> Optional[FeedEntry]:
        """解析单个 RSS <item>：标题、description、link、pubDate/published。"""
        return self.build_entry(
            self.text(node, "title"),
            self.text(node, "description") or self.text(node, "summary"),
            self.text(node, "link"),
            source_name,
            self.parse_datetime(self.text(node, "pubDate") or self.text(node, "published")),
        )

    def parse_atom_entry(self, node: ET.Element, source_name: str) -> Optional[FeedEntry]:
        """解析单个 Atom <entry>：链接取 rel=alternate 的 href，时间取 published/updated。"""
        url = ""
        for link in node.findall("./{*}link") or node.findall("./link"):
            if (link.attrib.get("rel") or "alternate").lower() == "alternate" and link.attrib.get("href"):
                url = link.attrib["href"].strip()
                break
        return self.build_entry(
            self.text(node, "title"),
            self.text(node, "summary") or self.text(node, "content"),
            url,
            source_name,
            self.parse_datetime(self.text(node, "published") or self.text(node, "updated")),
        )

    def build_entry(
        self, title: str, summary: str, url: str, source_name: str, published_at: Optional[datetime]
    ) -> Optional[FeedEntry]:
        """构造 FeedEntry：清洗文本、截断长度，并为条目生成稳定的去重键。

        有链接时用链接作为去重键（同时校验其合法性，非法直接丢弃该条目）；
        无链接时用 来源+标题+发布时间 的哈希生成 `no-url:intel:<hash>` 占位键，
        保证 upsert 仍能去重。
        """
        title = self.clean_text(title)[:300]
        summary = self.clean_text(summary)[:2000]
        url = url.strip()
        if not title and not url:
            return None
        if url:
            try:
                self._url_validator(url, allow_no_url=True)
            except IntelligenceServiceError:
                return None
            url_key = url
        else:
            digest = hashlib.sha256(f"{source_name}|{title}|{published_at}".encode("utf-8")).hexdigest()[:24]
            url_key = f"no-url:intel:{digest}"
        return FeedEntry(title or url_key, summary, url_key, source_name, published_at, {"source": source_name})

    @staticmethod
    def strip_ns(tag: str) -> str:
        """去掉 XML 标签的命名空间前缀，只保留本地标签名。"""
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    @classmethod
    def text(cls, node: ET.Element, name: str) -> str:
        """读取子节点文本：先按任意命名空间匹配，再退回无命名空间匹配。"""
        found = node.find(f"./{{*}}{name}")
        if found is None:
            found = node.find(f"./{name}")
        return "" if found is None or found.text is None else found.text.strip()

    @staticmethod
    def clean_text(value: str) -> str:
        """清洗文本：先剥离 HTML 标签，再折叠空白字符。"""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()

    @staticmethod
    def parse_datetime(value: str) -> Optional[datetime]:
        """解析时间字符串：优先 RFC 2822（RSS pubDate），其次 ISO 8601；统一转 UTC naive。"""
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return None
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @classmethod
    def parse_datetime_or_timestamp(cls, value: Any) -> Optional[datetime]:
        """解析时间：支持秒/毫秒时间戳与常见字符串格式（NewsNow 的 pubDate 两种都有）。"""
        if isinstance(value, (int, float)):
            timestamp = float(value)
            # 超过该阈值视为毫秒时间戳，统一换算成秒
            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000
            try:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
            except (OSError, OverflowError, ValueError):
                return None
        raw = str(value or "").strip()
        if raw.isdigit():
            return cls.parse_datetime_or_timestamp(float(raw))
        return cls.parse_datetime(raw)
