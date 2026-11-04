#!/usr/bin/env python3
"""Generate the Longbridge SDK OAuth token cache for headless runtimes.

为无头运行时生成 Longbridge SDK 的 OAuth token 缓存。先在交互机器上运行一次以完成授权，
再将缓存文件 base64 存入 GitHub Actions 密钥，供调度/Docker 运行使用。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def _default_client_id() -> str:
    """返回默认 client_id：依次取环境变量 LONGBRIDGE_OAUTH_CLIENT_ID、LONGBRIDGE_APP_KEY，去空白。"""
    return (
        os.getenv("LONGBRIDGE_OAUTH_CLIENT_ID")
        or os.getenv("LONGBRIDGE_APP_KEY")
        or ""
    ).strip()


def _token_cache_path(client_id: str) -> Path:
    """返回 OAuth token 缓存路径：~/.longbridge/openapi/tokens/<client_id>。"""
    return Path.home() / ".longbridge" / "openapi" / "tokens" / client_id


def main() -> int:
    """CLI 入口：解析 --client-id/--verify-symbol，执行 Longbridge OAuth 授权、可选校验标的，并提示缓存路径与 CI 用法。"""
    parser = argparse.ArgumentParser(
        description=(
            "Run Longbridge OAuth authorization and persist the SDK token cache. "
            "Use this once on an interactive machine before schedule/Docker/GitHub Actions runs."
        )
    )
    parser.add_argument(
        "--client-id",
        default=_default_client_id(),
        help="OAuth client_id. Defaults to LONGBRIDGE_OAUTH_CLIENT_ID, then LONGBRIDGE_APP_KEY.",
    )
    parser.add_argument(
        "--verify-symbol",
        default="",
        help="Optional Longbridge symbol such as AAPL.US or 700.HK to verify QuoteContext after auth.",
    )
    args = parser.parse_args()

    client_id = (args.client_id or "").strip()
    if not client_id:
        parser.error("missing --client-id or LONGBRIDGE_OAUTH_CLIENT_ID")

    try:
        from longbridge.openapi import Config, OAuthBuilder, QuoteContext
    except Exception as exc:
        raise SystemExit(
            "longbridge SDK is not installed. Run `pip install -r requirements.txt` first."
        ) from exc

    def show_url(url: str) -> None:
        """OAuth 回调：将授权 URL 打印给用户以便手动在浏览器中授权。"""
        print(f"Open this URL to authorize Longbridge OAuth:\n{url}\n")

    oauth = OAuthBuilder(client_id).build(show_url)
    config = Config.from_oauth(oauth)

    if args.verify_symbol:
        ctx = QuoteContext(config)
        quote = ctx.quote([args.verify_symbol])[0]
        print(f"Verified {args.verify_symbol}: {getattr(quote, 'last_done', None)}")

    token_cache = _token_cache_path(client_id)
    print(f"OAuth token cache: {token_cache}")
    print(
        "For GitHub Actions, store the base64 of this file as "
        "`LONGBRIDGE_OAUTH_TOKEN_CACHE_B64`."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
