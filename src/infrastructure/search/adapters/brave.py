"""BraveSearchProvider transport adapter."""

from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
import requests
from src.application.intelligence.ports import SearchOptions
from src.domain.search import SearchResponse, SearchResult
from src.infrastructure.search.provider_base import BaseSearchProvider

logger = logging.getLogger("src.infrastructure.search.providers")


class BraveSearchProvider(BaseSearchProvider):
    """
    Brave Search 搜索引擎

    特点：
    - 隐私优先的独立搜索引擎
    - 索引超过300亿页面
    - 免费层可用
    - 支持时间范围过滤

    文档：https://brave.com/search/api/
    """

    API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_keys: List[str]):
        """构造 Brave 检索适配器并装配依赖。"""
        super().__init__(api_keys, "Brave")

    def _do_search(
        self,
        query: str,
        api_key: str,
        max_results: int,
        days: int = 7,
        search_lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> SearchResponse:
        """执行 Brave 搜索"""
        try:
            # 请求头
            headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}

            # 确定时间范围（freshness 参数）
            if days <= 1:
                freshness = "pd"  # Past day (24小时)
            elif days <= 7:
                freshness = "pw"  # Past week
            elif days <= 30:
                freshness = "pm"  # Past month
            else:
                freshness = "py"  # Past year

            # 请求参数
            params = {
                "q": query,
                "count": min(max_results, 20),  # Brave 最大支持20条
                "freshness": freshness,
                "safesearch": "moderate",
            }
            if search_lang:
                params["search_lang"] = search_lang
            if country:
                params["country"] = country

            # 执行搜索（GET 请求）
            response = requests.get(self.API_ENDPOINT, headers=headers, params=params, timeout=10)

            # 检查HTTP状态码
            if response.status_code != 200:
                error_msg = self._parse_error(response)
                logger.warning(f"[Brave] 搜索失败: {error_msg}")
                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            # 解析响应
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"响应JSON解析失败: {str(e)}"
                logger.error(f"[Brave] {error_msg}")
                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            logger.info(f"[Brave] 搜索完成，query='{query}'")
            logger.debug(f"[Brave] 原始响应: {data}")

            # 解析搜索结果
            results = []
            web_data = data.get("web", {})
            web_results = web_data.get("results", [])

            for item in web_results[:max_results]:
                # 解析发布日期（ISO 8601 格式）
                published_date = None
                age = item.get("age") or item.get("page_age")
                if age:
                    try:
                        # 转换 ISO 格式为简单日期字符串
                        dt = datetime.fromisoformat(age.replace("Z", "+00:00"))
                        published_date = dt.strftime("%Y-%m-%d")
                    except (ValueError, AttributeError):
                        published_date = age  # 解析失败时使用原始值

                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        snippet=item.get("description", "")[:500],  # 截取到500字符
                        url=item.get("url", ""),
                        source=self._extract_domain(item.get("url", "")),
                        published_date=published_date,
                    )
                )

            logger.info(f"[Brave] 成功解析 {len(results)} 条结果")

            return SearchResponse(query=query, results=results, provider=self.name, success=True)

        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)

    def _parse_error(self, response) -> str:
        """解析错误响应"""
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                # Brave API 返回的错误格式
                if "message" in error_data:
                    return error_data["message"]
                if "error" in error_data:
                    return error_data["error"]
                return str(error_data)
            return response.text[:200]
        except Exception:
            return f"HTTP {response.status_code}: {response.text[:200]}"

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

    def search(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        """执行 Brave 搜索，可按 SearchOptions.search_lang / country 传入区域与语言偏好。"""
        search_lang = options.search_lang if options is not None else None
        country = options.country if options is not None else None
        if search_lang is None and country is None:
            return super().search(query, max_results=max_results, days=days)

        return self._execute_search(
            query,
            max_results=max_results,
            days=days,
            search_lang=search_lang,
            country=country,
        )
