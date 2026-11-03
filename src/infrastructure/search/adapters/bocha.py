"""BochaSearchProvider transport adapter."""

from __future__ import annotations
import logging
from typing import List
from urllib.parse import urlparse
import requests
from src.domain.search import SearchResponse, SearchResult
from src.infrastructure.search.provider_base import BaseSearchProvider, _post_with_retry

logger = logging.getLogger("src.infrastructure.search.providers")


class BochaSearchProvider(BaseSearchProvider):
    """
    博查搜索引擎

    特点：
    - 专为AI优化的中文搜索API
    - 结果准确、摘要完整
    - 支持时间范围过滤和AI摘要
    - 兼容Bing Search API格式

    文档：https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK
    """

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Bocha")

    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """执行博查搜索"""
        try:
            import requests
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="requests 未安装，请运行: pip install requests",
            )

        try:
            # API 端点
            url = "https://api.bocha.cn/v1/web-search"

            # 请求头
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            # 确定时间范围
            freshness = "oneWeek"
            if days <= 1:
                freshness = "oneDay"
            elif days <= 7:
                freshness = "oneWeek"
            elif days <= 30:
                freshness = "oneMonth"
            else:
                freshness = "oneYear"

            # 请求参数（严格按照API文档）
            payload = {
                "query": query,
                "freshness": freshness,  # 动态时间范围
                "summary": True,  # 启用AI摘要
                "count": min(max_results, 50),  # 最大50条
            }

            # 执行搜索（带瞬时 SSL/网络错误重试）
            response = _post_with_retry(url, headers=headers, json=payload, timeout=10)

            # 检查HTTP状态码
            if response.status_code != 200:
                # 尝试解析错误信息
                try:
                    if response.headers.get("content-type", "").startswith("application/json"):
                        error_data = response.json()
                        error_message = error_data.get("message", response.text)
                    else:
                        error_message = response.text
                except Exception:
                    error_message = response.text

                # 根据错误码处理
                if response.status_code == 403:
                    error_msg = f"余额不足: {error_message}"
                elif response.status_code == 401:
                    error_msg = f"API KEY无效: {error_message}"
                elif response.status_code == 400:
                    error_msg = f"请求参数错误: {error_message}"
                elif response.status_code == 429:
                    error_msg = f"请求频率达到限制: {error_message}"
                else:
                    error_msg = f"HTTP {response.status_code}: {error_message}"

                logger.warning(f"[Bocha] 搜索失败: {error_msg}")

                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            # 解析响应
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"响应JSON解析失败: {str(e)}"
                logger.error(f"[Bocha] {error_msg}")
                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            # 检查响应code
            if data.get("code") != 200:
                error_msg = data.get("msg") or f"API返回错误码: {data.get('code')}"
                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            # 记录原始响应到日志
            logger.info(f"[Bocha] 搜索完成，query='{query}'")
            logger.debug(f"[Bocha] 原始响应: {data}")

            # 解析搜索结果
            results = []
            web_pages = data.get("data", {}).get("webPages", {})
            value_list = web_pages.get("value", [])

            for item in value_list[:max_results]:
                # 优先使用summary（AI摘要），fallback到snippet
                snippet = item.get("summary") or item.get("snippet", "")

                # 截取摘要长度
                if snippet:
                    snippet = snippet[:500]

                results.append(
                    SearchResult(
                        title=item.get("name", ""),
                        snippet=snippet,
                        url=item.get("url", ""),
                        source=item.get("siteName") or self._extract_domain(item.get("url", "")),
                        published_date=item.get("datePublished"),  # UTC+8格式，无需转换
                    )
                )

            logger.info(f"[Bocha] 成功解析 {len(results)} 条结果")

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )

        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)

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
