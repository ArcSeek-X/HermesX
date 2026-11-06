"""longbridge 共享协议、连接和配额；无能力选源/回退或第二份资源。"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from pathlib import Path
from src.domain.market.us_index_symbols import is_us_stock_code, is_us_index_code

logger = logging.getLogger("data_provider.longbridge_fetcher")

from dataclasses import dataclass
from typing import Callable
from typing import Any, Optional, Dict


@dataclass(frozen=True)
class LongbridgeClientAccess:
    """窄资源访问契约；状态写回原所有者，兼容旧资源扩展点。"""

    use_get_ctx: Callable
    use_invalidate_ctx: Callable
    use_is_available: Callable
    use_is_connection_error: Callable
    use_mark_connection_cooldown: Callable
    read_available: Callable
    read_config: Callable
    read_cooldown_until: Callable
    read_ctx: Callable
    read_ctx_lock: Callable
    read_static_cache: Callable
    read_static_cache_lock: Callable
    write_available: Callable
    write_config: Callable
    write_cooldown_until: Callable
    write_ctx: Callable
    read_global_Optional: Callable
    read_global_connection_cooldown_seconds: Callable
    read_global_has_legacy_credentials: Callable
    read_global_has_oauth_credentials: Callable
    read_global_is_valid_oauth_cache_file: Callable
    read_global_longbridge_config_kwargs: Callable
    read_global_longbridge_credentials: Callable
    read_global_oauth_reauth_not_supported: Callable
    read_global_oauth_sdk_unavailable_error: Callable
    read_global_oauth_token_cache_path: Callable
    read_global_restore_oauth_token_cache_from_env: Callable
    read_global_sanitize_longbridge_env: Callable
    read_global_static_info_ttl_seconds: Callable
    read_global_logger: Callable
    read_global_os: Callable
    read_global_time: Callable

    def _invalidate_ctx(self):
        """Reset cached context so the next call rebuilds the connection."""
        with self.read_ctx_lock():
            self.write_ctx(None)
            self.write_config(None)

    def _mark_connection_cooldown(self, exc: Exception) -> None:
        """标记连接冷却期。"""
        cooldown_seconds = self.read_global_connection_cooldown_seconds()()
        self.use_invalidate_ctx()
        if cooldown_seconds <= 0:
            return
        self.write_cooldown_until(self.read_global_time().time() + cooldown_seconds)
        self.read_global_logger().warning(
            "[Longbridge] 检测到连接异常，进入 %ss 冷却期以避免频繁重连: %s",
            cooldown_seconds,
            exc,
        )

    def is_available_for_request(self, capability: str = "") -> bool:
        """Report request-time availability including temporary cooldown."""
        if not self.use_is_available():
            return False
        if self.read_cooldown_until() > self.read_global_time().time():
            self.read_global_logger().debug(
                "[Longbridge] %s 冷却中，暂时跳过请求，剩余 %.1fs",
                capability or "request",
                self.read_cooldown_until() - self.read_global_time().time(),
            )
            return False
        if self.read_cooldown_until():
            self.write_cooldown_until(0.0)
        return True

    def _is_available(self) -> bool:
        """Check if Longbridge credentials are configured (OAuth or Legacy)."""
        if self.read_available() is not None:
            return self.read_available()
        try:
            from src.config import get_config

            creds = self.read_global_longbridge_credentials()(get_config())
        except Exception:
            creds = self.read_global_longbridge_credentials()()
        self.write_available(
            self.read_global_has_legacy_credentials()(creds)
            or self.read_global_has_oauth_credentials()(creds)
        )
        return self.read_available()

    def _get_ctx(self):
        """Lazy-init the QuoteContext (thread-safe)."""
        if self.read_ctx() is not None:
            return self.read_ctx()
        with self.read_ctx_lock():
            if self.read_ctx() is not None:
                return self.read_ctx()
            if not self.use_is_available():
                return None
            try:
                from longbridge.openapi import QuoteContext, Config

                self.read_global_sanitize_longbridge_env()()
                try:
                    from src.config import get_config

                    app_config = get_config()
                except Exception:
                    app_config = None
                creds = self.read_global_longbridge_credentials()(app_config)
                app_key = creds["app_key"]
                app_secret = creds["app_secret"]
                access_token = creds["access_token"]
                oauth_client_id = creds["oauth_client_id"]
                has_legacy = self.read_global_has_legacy_credentials()(creds)
                for k, v in {
                    "LONGBRIDGE_APP_KEY": app_key,
                    "LONGBRIDGE_APP_SECRET": app_secret,
                    "LONGBRIDGE_ACCESS_TOKEN": access_token,
                }.items():
                    if v and (not self.read_global_os().environ.get(k)):
                        self.read_global_os().environ[k] = v
                if oauth_client_id and (
                    not self.read_global_os().environ.get("LONGBRIDGE_OAUTH_CLIENT_ID")
                ):
                    self.read_global_os().environ[
                        "LONGBRIDGE_OAUTH_CLIENT_ID"
                    ] = oauth_client_id
                extra_kw = self.read_global_longbridge_config_kwargs()()
                lb_config = None
                oauth_error: self.read_global_Optional()[Exception] = None
                if oauth_client_id:
                    token_cache = self.read_global_oauth_token_cache_path()(
                        oauth_client_id
                    )
                    self.read_global_restore_oauth_token_cache_from_env()(
                        oauth_client_id
                    )
                    if self.read_global_is_valid_oauth_cache_file()(token_cache):
                        try:
                            from longbridge.openapi import OAuthBuilder

                            oauth = OAuthBuilder(oauth_client_id).build(
                                self.read_global_oauth_reauth_not_supported()
                            )
                            from_oauth = getattr(Config, "from_oauth", None)
                            if from_oauth is None:
                                raise AttributeError("Config.from_oauth")
                            lb_config = from_oauth(oauth)
                            self.read_global_logger().info(
                                "[Longbridge] Config.from_oauth() 创建成功"
                            )
                        except (ImportError, AttributeError):
                            oauth_error = (
                                self.read_global_oauth_sdk_unavailable_error()()
                            )
                            self.read_global_logger().warning(
                                "[Longbridge] OAuth SDK 不可用: %s", oauth_error
                            )
                        except Exception as exc:
                            oauth_error = exc
                            self.read_global_logger().warning(
                                "[Longbridge] OAuth 初始化失败: %s", exc
                            )
                    elif token_cache.exists():
                        self.read_global_logger().warning(
                            "[Longbridge] OAuth token 缓存内容异常，已拒绝交互式续期: %s。请先执行 scripts/generate_longbridge_oauth_token.py 重建缓存。",
                            token_cache,
                        )
                    else:
                        self.read_global_logger().warning(
                            "[Longbridge] OAuth client 已配置，但 token 缓存不存在: %s。请先执行 scripts/generate_longbridge_oauth_token.py 生成缓存；GitHub Actions/Docker 可提供 LONGBRIDGE_OAUTH_TOKEN_CACHE_B64。",
                            token_cache,
                        )
                if lb_config is None and has_legacy:
                    for factory_name in ("from_apikey_env", "from_env"):
                        factory = getattr(Config, factory_name, None)
                        if factory is None:
                            continue
                        try:
                            lb_config = factory()
                            self.read_global_logger().info(
                                "[Longbridge] Config.%s() 成功", factory_name
                            )
                            break
                        except Exception as e:
                            self.read_global_logger().debug(
                                "[Longbridge] Config.%s() 失败: %s", factory_name, e
                            )
                if lb_config is None and has_legacy:
                    lb_config = Config.from_apikey(
                        app_key, app_secret, access_token, **extra_kw
                    )
                    self.read_global_logger().info(
                        "[Longbridge] Config.from_apikey() 创建成功"
                    )
                elif lb_config is None:
                    reason = (
                        f"OAuth 初始化失败: {oauth_error}"
                        if oauth_error
                        else "未找到可用 OAuth token 缓存且未配置完整 Legacy 三件套"
                    )
                    self.read_global_logger().warning(
                        "[Longbridge] 未建立认证配置: %s", reason
                    )
                    self.write_available(False)
                    return None
                region = (
                    self.read_global_os().getenv("LONGBRIDGE_REGION")
                    or self.read_global_os().getenv("LONGPORT_REGION")
                    or "(auto)"
                )
                self.read_global_logger().info(
                    "[Longbridge] 配置: region=%s, http=%s, quote_ws=%s",
                    region,
                    self.read_global_os().getenv("LONGBRIDGE_HTTP_URL", "(default)"),
                    self.read_global_os().getenv(
                        "LONGBRIDGE_QUOTE_WS_URL", "(default)"
                    ),
                )
                self.write_config(lb_config)
                self.write_ctx(QuoteContext(lb_config))
                self.read_global_logger().info("[Longbridge] QuoteContext 初始化成功")
                return self.read_ctx()
            except Exception as e:
                self.read_global_logger().warning(
                    "[Longbridge] QuoteContext 初始化失败: %s", e
                )
                self.write_available(False)
                return None

    def _get_static_info(self, symbol: str) -> Optional[Any]:
        """Fetch static info (shares, EPS, BPS, name) with optional in-process TTL cache."""
        ttl = self.read_global_static_info_ttl_seconds()()
        now = self.read_global_time().time()
        if ttl > 0:
            with self.read_static_cache_lock():
                cached = self.read_static_cache().get(symbol)
                if cached and now - cached[1] < ttl:
                    return cached[0]
        ctx = self.use_get_ctx()
        if ctx is None:
            return None
        try:
            infos = ctx.static_info([symbol])
            if infos:
                info = infos[0]
                if ttl > 0:
                    with self.read_static_cache_lock():
                        self.read_static_cache()[symbol] = (info, now)
                return info
        except Exception as e:
            self.read_global_logger().debug(
                f"[Longbridge] static_info({symbol}) 失败: {e}"
            )
            if self.use_is_connection_error(e):
                self.use_mark_connection_cooldown(e)
        return None


_DEFAULT_STATIC_INFO_TTL = 86400  # 24h


_DEFAULT_CONNECTION_COOLDOWN_SECONDS = 15


def _static_info_ttl_seconds() -> int:
    """TTL for static_info cache; 0 disables caching (always fetch)."""
    raw = os.getenv("LONGBRIDGE_STATIC_INFO_TTL_SECONDS", "").strip()
    if raw == "":
        return _DEFAULT_STATIC_INFO_TTL
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_STATIC_INFO_TTL


def _connection_cooldown_seconds() -> int:
    """Cooldown after connection-close errors to avoid reconnect thrashing."""
    raw = os.getenv("LONGBRIDGE_CONNECTION_COOLDOWN_SECONDS", "").strip()
    if raw == "":
        return _DEFAULT_CONNECTION_COOLDOWN_SECONDS
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_CONNECTION_COOLDOWN_SECONDS


_REGION_URL_MAP: Dict[str, Dict[str, str]] = {
    "cn": {
        "http_url": "https://openapi.longbridge.cn",
        "quote_ws_url": "wss://openapi-quote.longbridge.cn/v2",
        "trade_ws_url": "wss://openapi-trade.longbridge.cn/v2",
    },
    "hk": {
        "http_url": "https://openapi.longbridge.com",
        "quote_ws_url": "wss://openapi-quote.longbridge.com/v2",
        "trade_ws_url": "wss://openapi-trade.longbridge.com/v2",
    },
}


def _sanitize_longbridge_env() -> None:
    """Remove empty-string LONGBRIDGE_*_URL env vars.

    GitHub Actions sets ``LONGBRIDGE_HTTP_URL: ${{ vars.X || secrets.X }}``
    which resolves to an empty string ``""`` when neither var nor secret is
    configured.  The Rust SDK's ``Config.from_apikey()`` auto-reads these
    env vars, and an empty string is *not* the same as "unset" — it causes
    the SDK to use a blank URL, which breaks the WebSocket handshake and
    results in "context dropped" / "Client is closed" within milliseconds.

    Also mirrors ``LONGBRIDGE_REGION`` → ``LONGPORT_REGION`` because the
    Rust SDK's internal ``is_cn()`` function only checks ``LONGPORT_REGION``
    (not ``LONGBRIDGE_REGION``) when deciding which default endpoints to use.
    """
    for key in (
        "LONGBRIDGE_HTTP_URL",
        "LONGBRIDGE_QUOTE_WS_URL",
        "LONGBRIDGE_TRADE_WS_URL",
        "LONGBRIDGE_ENABLE_OVERNIGHT",
        "LONGBRIDGE_PUSH_CANDLESTICK_MODE",
        "LONGBRIDGE_PRINT_QUOTE_PACKAGES",
        "LONGBRIDGE_REGION",
        "LONGBRIDGE_STATIC_INFO_TTL_SECONDS",
        "LONGBRIDGE_LOG_PATH",
    ):
        val = os.environ.get(key)
        if val is not None and val.strip() == "":
            del os.environ[key]
            logger.debug("[Longbridge] 删除空环境变量 %s", key)

    # App default: quiet (false). Matches README / docs/full-guide / .env.example; SDK alone may default verbose.
    if "LONGBRIDGE_PRINT_QUOTE_PACKAGES" not in os.environ:
        os.environ["LONGBRIDGE_PRINT_QUOTE_PACKAGES"] = "false"

    if not os.environ.get("LONGBRIDGE_LOG_PATH"):
        try:
            log_dir = (os.getenv("LOG_DIR") or "./logs").strip() or "./logs"
            p = Path(log_dir).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            os.environ["LONGBRIDGE_LOG_PATH"] = str(p / "longbridge_sdk.log")
            logger.debug("[Longbridge] 设置 LONGBRIDGE_LOG_PATH=%s",
                         os.environ["LONGBRIDGE_LOG_PATH"])
        except Exception:
            pass

    region = (os.getenv("LONGBRIDGE_REGION") or "").strip().lower()
    if region:
        if not os.environ.get("LONGPORT_REGION"):
            os.environ["LONGPORT_REGION"] = region
            logger.debug("[Longbridge] 同步 LONGPORT_REGION=%s", region)

        urls = _REGION_URL_MAP.get(region, {})
        for env_name, default_url in (
            ("LONGBRIDGE_HTTP_URL", urls.get("http_url")),
            ("LONGBRIDGE_QUOTE_WS_URL", urls.get("quote_ws_url")),
            ("LONGBRIDGE_TRADE_WS_URL", urls.get("trade_ws_url")),
        ):
            if default_url and not os.environ.get(env_name):
                os.environ[env_name] = default_url
                logger.debug("[Longbridge] 根据 REGION=%s 设置 %s=%s",
                             region, env_name, default_url)


def _longbridge_config_kwargs() -> Dict[str, Any]:
    """Optional kwargs for ``Config.from_apikey`` (Longbridge OpenAPI SDK)."""
    try:
        import inspect
        from longbridge.openapi import Config, Language, PushCandlestickMode
    except Exception:
        return {}

    try:
        params = inspect.signature(Config.from_apikey).parameters
    except Exception:
        return {}

    kw: Dict[str, Any] = {}

    if "enable_print_quote_packages" in params:
        # Unset / empty → False (quiet); SDK default would be verbose — we opt in explicitly.
        raw = os.getenv("LONGBRIDGE_PRINT_QUOTE_PACKAGES")
        if raw is None or not str(raw).strip():
            kw["enable_print_quote_packages"] = False
        else:
            raw_norm = str(raw).strip().lower()
            kw["enable_print_quote_packages"] = raw_norm not in ("0", "false", "no")

    for pname, envname in (
        ("http_url", "LONGBRIDGE_HTTP_URL"),
        ("quote_ws_url", "LONGBRIDGE_QUOTE_WS_URL"),
        ("trade_ws_url", "LONGBRIDGE_TRADE_WS_URL"),
    ):
        if pname in params:
            v = os.getenv(envname, "").strip()
            if v:
                kw[pname] = v

    if "language" in params:
        try:
            from src.domain.shared.report_language import normalize_report_language

            rl = normalize_report_language(os.getenv("REPORT_LANGUAGE"), default="zh")
            if rl == "zh":
                kw["language"] = Language.ZH_CN
            elif rl == "en":
                kw["language"] = Language.EN
        except Exception as e:
            logger.debug("Longbridge language from REPORT_LANGUAGE skipped: %s", e)

    if "enable_overnight" in params:
        o = os.getenv("LONGBRIDGE_ENABLE_OVERNIGHT", "").strip().lower()
        if o:
            kw["enable_overnight"] = o in ("1", "true", "yes")

    if "push_candlestick_mode" in params:
        cm = os.getenv("LONGBRIDGE_PUSH_CANDLESTICK_MODE", "").strip().lower()
        if cm == "realtime":
            kw["push_candlestick_mode"] = PushCandlestickMode.Realtime
        elif cm == "confirmed":
            kw["push_candlestick_mode"] = PushCandlestickMode.Confirmed
        elif cm:
            logger.warning(
                "Unknown LONGBRIDGE_PUSH_CANDLESTICK_MODE=%r; use realtime or confirmed", cm
            )

    if "log_path" in params:
        try:
            log_dir = (os.getenv("LOG_DIR") or "./logs").strip() or "./logs"
            p = Path(log_dir).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            kw["log_path"] = str(p / "longbridge_sdk.log")
        except Exception as e:
            logger.debug("Longbridge log_path from LOG_DIR skipped: %s", e)

    return kw


def _clean_optional(value: Any) -> Optional[str]:
    """清洗可选字符串值。"""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _oauth_token_cache_path(client_id: str) -> Path:
    """返回 OAuth 令牌缓存路径。"""
    return Path.home() / ".longbridge" / "openapi" / "tokens" / client_id


def _restore_oauth_token_cache_from_env(client_id: str) -> bool:
    """Restore the SDK OAuth token cache from a GitHub Actions/Docker secret.

    The Longbridge SDK expects its OAuth token cache at
    ``~/.longbridge/openapi/tokens/<client_id>``.  In headless environments the
    file can be provided as base64 through ``LONGBRIDGE_OAUTH_TOKEN_CACHE_B64``.
    If an env cache is supplied and differs from the existing file, treat the
    env value as the operator-provided recovery source for headless runs.
    """
    raw = os.getenv("LONGBRIDGE_OAUTH_TOKEN_CACHE_B64")
    if not raw:
        return False

    try:
        payload = base64.b64decode("".join(raw.split()), validate=True)
    except (binascii.Error, ValueError) as exc:
        logger.warning("[Longbridge] OAuth token cache base64 解码失败: %s", exc)
        return False

    if not payload:
        logger.warning("[Longbridge] OAuth token cache base64 为空，跳过恢复")
        return False

    token_cache = _oauth_token_cache_path(client_id)
    if token_cache.exists():
        try:
            if token_cache.read_bytes() == payload:
                logger.debug("[Longbridge] OAuth token 缓存已与 env secret 一致，跳过恢复: %s", token_cache)
                return False
        except OSError as exc:
            logger.warning("[Longbridge] 读取现有 OAuth token 缓存失败，将尝试用 env secret 覆盖: %s", exc)

    try:
        token_cache.parent.mkdir(parents=True, exist_ok=True)
        token_cache.write_bytes(payload)
        token_cache.chmod(0o600)
        logger.info("[Longbridge] 已从 LONGBRIDGE_OAUTH_TOKEN_CACHE_B64 恢复 OAuth token 缓存")
        return True
    except Exception as exc:
        logger.warning("[Longbridge] 写入 OAuth token 缓存失败: %s", exc)
        return False


def _is_valid_oauth_cache_file(token_cache: Path) -> bool:
    """Basic health check for SDK token cache content.

    We avoid attempting interactive OAuth flows when the cache is missing or
    malformed, so headless jobs fail explicitly instead of hanging for manual
    re-authorization.
    """
    if not token_cache.exists():
        return False

    try:
        raw = token_cache.read_bytes()
    except OSError as exc:
        logger.warning("[Longbridge] 读取 OAuth token 缓存失败: %s", exc)
        return False

    if not raw.strip():
        logger.warning("[Longbridge] OAuth token 缓存为空文件: %s", token_cache)
        return False

    try:
        payload = raw.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        logger.warning("[Longbridge] OAuth token 缓存不是 UTF-8 文本: %s", exc)
        return False

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        logger.warning("[Longbridge] OAuth token 缓存不是合法 JSON: %s", exc)
        return False

    if not isinstance(data, dict) or not data:
        logger.warning("[Longbridge] OAuth token 缓存内容为空或格式不符合预期: %s", token_cache)
        return False

    return True


def _oauth_reauth_not_supported(url: str) -> None:
    """构造不支持重新授权的提示。"""
    raise RuntimeError(
        f"OAuth token 缓存已失效或缺失，当前为无头运行不支持打开授权页面，请重建 LONGBRIDGE_OAUTH_TOKEN_CACHE_B64: {url}"
    )


def _oauth_sdk_unavailable_error() -> RuntimeError:
    """构造 OAuth SDK 不可用错误。"""
    return RuntimeError(
        "当前安装的 longbridge SDK 不支持 OAuth 2.0（缺少 OAuthBuilder/Config.from_oauth）。"
        "请在支持该 SDK 版本的平台安装 longbridge>=4.0.0，或继续使用 Legacy 三件套。"
    )


def _longbridge_credentials(config: Any = None) -> Dict[str, Optional[str]]:
    """Collect Longbridge auth inputs from Config/env without exposing secrets."""
    app_key = _clean_optional(getattr(config, "longbridge_app_key", None))
    app_secret = _clean_optional(getattr(config, "longbridge_app_secret", None))
    access_token = _clean_optional(getattr(config, "longbridge_access_token", None))
    oauth_client_id = _clean_optional(getattr(config, "longbridge_oauth_client_id", None))

    app_key = app_key or _clean_optional(os.getenv("LONGBRIDGE_APP_KEY"))
    app_secret = app_secret or _clean_optional(os.getenv("LONGBRIDGE_APP_SECRET"))
    access_token = access_token or _clean_optional(os.getenv("LONGBRIDGE_ACCESS_TOKEN"))
    oauth_client_id = oauth_client_id or _clean_optional(os.getenv("LONGBRIDGE_OAUTH_CLIENT_ID"))

    # Some Longbridge pages label the OAuth public client id as "App Key".
    # Use it as a compatibility alias only when no Legacy access token exists.
    if not oauth_client_id and app_key and not access_token:
        oauth_client_id = app_key

    return {
        "app_key": app_key,
        "app_secret": app_secret,
        "access_token": access_token,
        "oauth_client_id": oauth_client_id,
    }


def _has_legacy_credentials(creds: Dict[str, Optional[str]]) -> bool:
    """判断是否配置遗留凭据。"""
    return bool(creds.get("app_key") and creds.get("app_secret") and creds.get("access_token"))


def _has_oauth_credentials(creds: Dict[str, Optional[str]]) -> bool:
    """判断是否配置 OAuth 凭据。"""
    return bool(creds.get("oauth_client_id"))


def _is_us_code(stock_code: str) -> bool:
    """判断代码是否为美股。"""
    normalized = stock_code.strip().upper()
    return is_us_stock_code(normalized) or is_us_index_code(normalized)


def _is_hk_code(stock_code: str) -> bool:
    """
    判定是否为港股代码，与 ``data_provider.base._is_hk_market`` 的市场契约一致：
    支持 ``.HK`` 后缀、``HK00700`` 前缀形式，以及 4-5 位纯数字裸码（港股
    普通股为 4 位如 ``0001`` 长和、``0941`` 中国移动；最多 5 位）。

    Note: 4 位裸数字与 A 股不冲突——A 股 ETF/股票均为 6 位。
    """
    normalized = (stock_code or "").strip().upper()
    if normalized.startswith("HK"):
        digits = normalized[2:]
        return digits.isdigit() and 1 <= len(digits) <= 5
    if normalized.endswith(".HK"):
        base = normalized[:-3]
        return base.isdigit() and 1 <= len(base) <= 5
    if normalized.isdigit() and 4 <= len(normalized) <= 5:
        return True
    return False


def _to_longbridge_symbol(stock_code: str) -> Optional[str]:
    """Convert internal stock code to Longbridge symbol format.

    Examples:
        AAPL      -> AAPL.US
        HK00700   -> 0700.HK
        00700     -> 0700.HK (5-digit pure number treated as HK)
    """
    code = stock_code.strip()
    upper = code.upper()

    if upper.endswith(".US"):
        return upper
    if upper.endswith(".HK"):
        return upper

    if _is_us_code(code):
        return f"{upper}.US"

    if _is_hk_code(code):
        upper = code.upper()
        if upper.startswith("HK"):
            digits = upper[2:]
        else:
            digits = upper
        digits = digits.lstrip("0") or "0"
        return f"{digits.zfill(4)}.HK"

    return None
