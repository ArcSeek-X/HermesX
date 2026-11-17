"""AnspireSearchProvider transport adapter."""

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urlparse
import requests
from src.domain.search import SearchResponse, SearchResult
from src.infrastructure.search.provider_base import BaseSearchProvider, _get_with_retry

logger = logging.getLogger("src.infrastructure.search.providers")


class AnspireSearchProvider(BaseSearchProvider):
    """
    Anspire Search 搜索引擎

    特点：
    - 面向AI生态的下一代实时智能搜索引擎
    - 结果精准、响应快速
    - 适用于股票新闻和市场情报搜索

    文档: https://open.anspire.cn/document/docs/searchApi/
    """

    def __init__(self, api_keys: List[str]):
        """构造 Anspire 检索适配器并装配依赖。"""
        super().__init__(api_keys, "Anspire")

    def _do_search(
        self, query: str, api_key: str, max_results: int, days: int = 7, region_mode: int = 0
    ) -> SearchResponse:
        """执行 Anspire 搜索"""
        try:
            import requests
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="requests 未安装，请运行：pip install requests",
            )

        try:
            # API 端点
            url = "https://plugin.anspire.cn/api/ntsearch/search"

            # 请求头
            headers = {"Authorization": f"Bearer {api_key}"}

            # 请求参数
            payload = {
                "query": query,
                "top_k": min(max_results, 50),
                "FromTime": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"),
                "ToTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "region_mode": region_mode,
            }

            # 执行搜索
            response = _get_with_retry(url, headers=headers, params=payload, timeout=10)

            # 检查 HTTP 状态码
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
                    error_msg = f"余额不足或权限不足：{error_message}"
                elif response.status_code == 401:
                    error_msg = f"API KEY 无效：{error_message}"
                elif response.status_code == 400:
                    error_msg = f"请求参数错误：{error_message}"
                else:
                    error_msg = f"HTTP {response.status_code}: {error_message}"

                logger.warning(f"[Anspire] 搜索失败：{error_msg}")

                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            # 解析响应
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"响应 JSON 解析失败：{str(e)}"
                logger.error(f"[Anspire] {error_msg}")
                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            if "code" in data and data.get("code") != 200:
                error_msg = data.get("msg") or f"API 返回错误码：{data.get('code')}"
                logger.warning(f"[Anspire] 搜索失败：{error_msg}")
                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            if "results" not in data:
                error_msg = "响应中缺少 results 字段"
                logger.error(f"[Anspire] {error_msg}，原始响应：{data}")
                return SearchResponse(
                    query=query, results=[], provider=self.name, success=False, error_message=error_msg
                )

            # 记录原始响应到日志
            logger.info(f"[Anspire] 搜索完成，query='{query}'")
            logger.debug(f"[Anspire] 原始响应：{data}")

            results = []
            value_list = data.get("results", [])

            for item in value_list[:max_results]:
                snippet = item.get("content")
                if snippet and isinstance(snippet, str) and len(snippet) > 500:
                    snippet = snippet[:500] + "..."

                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        snippet=snippet,
                        url=item.get("url", ""),
                        source=self._extract_domain(item.get("url", "")),
                        published_date=item.get("date", ""),
                    )
                )

            logger.info(f"[Anspire] 成功解析 {len(results)} 条结果")

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )

        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            logger.error(f"[Anspire] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败：{str(e)}"
            logger.error(f"[Anspire] {error_msg}")
            return SearchResponse(query=query, results=[], provider=self.name, success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"未知错误：{str(e)}"
            logger.error(f"[Anspire] {error_msg}")
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
