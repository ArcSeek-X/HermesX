"""TavilySearchProvider transport adapter."""

from __future__ import annotations
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from src.application.intelligence.ports import SearchOptions
from src.domain.search import SearchResponse, SearchResult
from src.infrastructure.search.provider_base import BaseSearchProvider

logger = logging.getLogger("src.infrastructure.search.providers")


class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily 搜索引擎

    特点：
    - 专为 AI/LLM 优化的搜索 API
    - 免费版每月 1000 次请求
    - 返回结构化的搜索结果

    文档：https://docs.tavily.com/
    """

    def __init__(self, api_keys: List[str]):
        """构造 Tavily 检索适配器并装配依赖。"""
        super().__init__(api_keys, "Tavily")

    def _do_search(
        self,
        query: str,
        api_key: str,
        max_results: int,
        days: int = 7,
        topic: Optional[str] = None,
    ) -> SearchResponse:
        """执行 Tavily 搜索"""
        try:
            from tavily import TavilyClient
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="tavily-python 未安装，请运行: pip install tavily-python",
            )

        try:
            client = TavilyClient(api_key=api_key)

            # 执行搜索（优化：使用advanced深度、限制最近几天）
            search_kwargs: Dict[str, Any] = {
                "query": query,
                "search_depth": "advanced",  # advanced 获取更多结果
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
                "days": days,  # 搜索最近天数的内容
            }
            if topic is not None:
                search_kwargs["topic"] = topic

            response = client.search(
                **search_kwargs,
            )

            # 记录原始响应到日志
            logger.info(f"[Tavily] 搜索完成，query='{query}', 返回 {len(response.get('results', []))} 条结果")
            logger.debug(f"[Tavily] 原始响应: {response}")

            # 解析结果
            results = []
            for item in response.get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        snippet=item.get("content", "")[:500],  # 截取前500字
                        url=item.get("url", ""),
                        source=self._extract_domain(item.get("url", "")),
                        published_date=item.get("published_date") or item.get("publishedDate"),
                    )
                )

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            # 检查是否是配额问题
            if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                error_msg = f"API 配额已用尽: {error_msg}"

            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)

    def search(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        """执行 Tavily 搜索，可按 SearchOptions.topic 选择是否启用新闻 topic。"""
        topic = options.topic if options is not None else None
        if topic is None:
            return super().search(query, max_results=max_results, days=days)

        api_key = self._get_next_key()
        if not api_key:
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=f"{self._name} 未配置 API Key",
            )

        start_time = time.time()
        try:
            response = self._do_search(query, api_key, max_results, days=days, topic=topic)
            response.search_time = time.time() - start_time

            if response.success:
                self.record_success(api_key)
                logger.info(
                    f"[{self._name}] 搜索 '{query}' 成功，返回 {len(response.results)} 条结果，耗时 {response.search_time:.2f}s"
                )
            else:
                self.record_error(api_key)

            return response

        except Exception as e:
            self.record_error(api_key)
            elapsed = time.time() - start_time
            logger.error(f"[{self._name}] 搜索 '{query}' 失败: {e}")
            return SearchResponse(
                query=query, results=[], provider=self._name, success=False, error_message=str(e), search_time=elapsed
            )

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 提取域名作为来源"""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain or "未知来源"
        except Exception:
            return "未知来源"
