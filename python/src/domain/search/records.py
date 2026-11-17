# -*- coding: utf-8 -*-
"""搜索领域的记录类型（领域 DTO）。

``SearchResult`` / ``SearchResponse`` 是检索用例与各个搜索引擎适配器共享的返回
契约：纯 stdlib ``dataclass``，无框架 / ORM / 网络 / IO 依赖。归属与边界
（ARCHITECTURE_TARGET §2）：

- 应用层（``src/application/intelligence/search_service``）编排、返回这些记录；
- 基础设施层的 Provider 适配器（SA2 后续片下沉）构造这些记录作为搜索结果；
- 仓储层（``src/storage`` / ``infrastructure/.../intelligence_repo``）以
  ``SearchResponse`` 作持久化类型注解。

集中收纳在 domain，使 application 与 infrastructure 无需为共享 DTO 互相 import
（``src/application`` 禁依赖 ``src/infrastructure``），两者都只依赖本领域包。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SearchResult:
    """搜索结果数据类"""
    title: str
    snippet: str  # 摘要
    url: str
    source: str  # 来源网站
    published_date: Optional[str] = None
    relevance_score: Optional[int] = None
    relevance_category: Optional[str] = None
    relevance_reasons: Optional[List[str]] = None

    def to_text(self) -> str:
        """转换为文本格式"""
        date_str = f" ({self.published_date})" if self.published_date else ""
        relevance_parts: List[str] = []
        if self.relevance_category:
            relevance_parts.append(self.relevance_category)
        if self.relevance_score is not None:
            relevance_parts.append(f"score={self.relevance_score}")
        if self.relevance_reasons:
            relevance_parts.append(f"依据: {'；'.join(self.relevance_reasons[:3])}")
        relevance_str = f"\n关联度: {'; '.join(relevance_parts)}" if relevance_parts else ""
        return f"【{self.source}】{self.title}{date_str}\n{self.snippet}{relevance_str}"


@dataclass
class SearchResponse:
    """搜索响应"""
    query: str
    results: List[SearchResult]
    provider: str  # 使用的搜索引擎
    success: bool = True
    error_message: Optional[str] = None
    search_time: float = 0.0  # 搜索耗时（秒）

    def to_context(self, max_results: int = 5) -> str:
        """将搜索结果转换为可用于 AI 分析的上下文"""
        if not self.success or not self.results:
            return f"搜索 '{self.query}' 未找到相关结果。"

        lines = [f"【{self.query} 搜索结果】（来源：{self.provider}）"]
        for i, result in enumerate(self.results[:max_results], 1):
            lines.append(f"\n{i}. {result.to_text()}")

        return "\n".join(lines)
