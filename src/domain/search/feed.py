"""Normalized feed entries and validation errors, independent of fetching and storage."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


class IntelligenceServiceError(ValueError):
    """面向调用方的校验/业务错误，其文案会直接透出到 API 响应。"""


@dataclass(frozen=True)
class FeedEntry:
    """解析后的单条资讯条目，与具体数据源类型无关的中间结构。"""

    title: str  # 标题（已清洗、截断）
    summary: str  # 摘要/正文片段（已去除 HTML 标签）
    url: str  # 原文链接；无链接时退化为 no-url:intel:<hash> 形式
    source: str  # 来源的资讯源名称
    published_at: Optional[datetime]  # 发布时间（统一为 UTC naive），解析失败为 None
    raw_payload: Dict[str, Any]  # 预留的原始负载，便于排查与扩展
