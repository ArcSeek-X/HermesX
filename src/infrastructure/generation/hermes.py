# -*- coding: utf-8 -*-
"""Hermes 渠道技术适配（R2-A4）。

R2-A2 起 Hermes 的**纯规则**（模型名 / URL / 路由来源 / 错误脱敏）真源在
``src.domain.generation.hermes_rules``；本模块只保留需要 httpx/openai SDK 的
``open_hermes_no_proxy_client``。

原 ``src/llm/hermes.py`` 是「纯规则重导出 + 客户端构造」的过渡 shim，R2-A4
物理搬包后删除，纯规则引用统一改指 domain 真源。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from src.domain.generation.hermes_rules import canonicalize_hermes_base_url


@contextmanager
def open_hermes_no_proxy_client(*, api_key: str, base_url: str, timeout: float) -> Iterator[Any]:
    """Yield an OpenAI client with a no-proxy httpx transport and close it."""

    import httpx
    import openai

    canonical_base_url = canonicalize_hermes_base_url(base_url)
    http_client = httpx.Client(
        trust_env=False,
        follow_redirects=False,
        timeout=timeout,
    )
    client = openai.OpenAI(
        api_key=api_key,
        base_url=canonical_base_url,
        http_client=http_client,
    )
    try:
        yield client
    finally:
        http_client.close()
