"""共享 Tushare HTTP 协议；保留原认证、超时和错误语义。"""

import os
from typing import Optional
import json as _json
import pandas as pd
import requests


class _TushareHttpClient:
    """Lightweight Tushare Pro client that does not require the tushare SDK."""

    def __init__(
        self, token: str, timeout: int = 30, api_url: str = "http://api.tushare.pro"
    ) -> None:
        """构造 Tushare 取数器并装配依赖。"""
        self._token = token
        self._timeout = timeout
        self._api_url = api_url

    def query(self, api_name: str, fields: str = "", **kwargs) -> pd.DataFrame:
        """执行 Tushare 查询。"""
        req_params = {
            "api_name": api_name,
            "token": self._token,
            "params": kwargs,
            "fields": fields,
        }
        res = requests.post(self._api_url, json=req_params, timeout=self._timeout)
        if res.status_code != 200:
            raise Exception(f"Tushare API HTTP {res.status_code}")

        result = _json.loads(res.text)
        if result.get("code") != 0:
            raise Exception(
                result.get("msg") or f"Tushare API error code {result.get('code')}"
            )

        data = result.get("data") or {}
        columns = data.get("fields") or []
        items = data.get("items") or []
        return pd.DataFrame(items, columns=columns)

    def __getattr__(self, api_name: str):
        """将未定义属性访问委派给底层接口。"""
        if api_name.startswith("_"):
            raise AttributeError(api_name)

        def caller(**kwargs) -> pd.DataFrame:
            """返回底层 Tushare 调用对象。"""
            return self.query(api_name, **kwargs)

        return caller


def _resolve_tushare_http_url() -> Optional[str]:
    """读取 ``TUSHARE_HTTP_URL`` 环境变量并做基本校验。

    - 留空 / 仅空白 / 未设置 → 返回 ``None``，调用方继续走官方默认地址。
    - 设置则去掉首尾空白后返回，并校验必须是 ``http://`` 或 ``https://`` 前缀，
      避免有人误填成纯主机名（如 ``api.tushare.pro``）导致 ``requests`` 把它
      当成相对路径请求失败。
    """
    raw = os.getenv("TUSHARE_HTTP_URL")
    if not raw:
        return None
    url = raw.strip()
    if not url:
        return None
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(
            "TUSHARE_HTTP_URL 必须以 http:// 或 https:// 开头，"
            f"当前值为 {url!r}"
        )
    return url
