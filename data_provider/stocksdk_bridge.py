# -*- coding: utf-8 -*-
"""
===================================
StockSDK 共享桥接客户端
===================================

职责：
1. 作为 Python 侧访问 StockSDK 的唯一桥接入口。
2. 统一 Node 进程调用、JSON 协议、错误映射与运行时参数。
3. 为 `stocksdk_source.py` 提供 K 线 / 行情 / 搜索的共享调用能力。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from threading import RLock
from typing import Any, Dict, List, Optional

from data_provider.base import normalize_stock_code

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE_ENTRY = REPO_ROOT / "scripts" / "stocksdk_bridge" / "bridge.mjs"


class StockSdkBridgeError(RuntimeError):
    """StockSDK bridge 调用失败。"""

    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class StockSdkSettings:
    """StockSDK bridge 运行配置。"""

    enabled: bool
    node_bin: str
    bridge_entry: str
    timeout_ms: int
    rate_limit_rps: int
    kline_fallback: bool


@dataclass(frozen=True)
class StockSdkSymbol:
    """StockSDK 调用所需的标准化 symbol。"""

    original_code: str
    normalized_code: str
    market: str
    symbol: str


def settings_from_config(config: Any) -> StockSdkSettings:
    """从全局 Config 生成 StockSDK 设置。"""
    return StockSdkSettings(
        enabled=bool(getattr(config, "stocksdk_enabled", False)),
        node_bin=str(getattr(config, "stocksdk_node_bin", "node") or "node").strip() or "node",
        bridge_entry=str(getattr(config, "stocksdk_bridge_entry", str(DEFAULT_BRIDGE_ENTRY))).strip()
        or str(DEFAULT_BRIDGE_ENTRY),
        timeout_ms=max(int(getattr(config, "stocksdk_timeout_ms", 8000)), 1000),
        rate_limit_rps=max(int(getattr(config, "stocksdk_rate_limit_rps", 3)), 1),
        kline_fallback=bool(getattr(config, "stocksdk_kline_fallback", True)),
    )


def resolve_stocksdk_symbol(stock_code: str) -> StockSdkSymbol:
    """将项目内股票代码归一为 StockSDK 友好的 symbol。"""
    original = (stock_code or "").strip()
    normalized = normalize_stock_code(original)
    upper = normalized.upper()

    if re.fullmatch(r"HK\d{1,5}", upper):
        return StockSdkSymbol(
            original_code=original,
            normalized_code=upper,
            market="hk",
            symbol=upper[2:].zfill(5),
        )
    if re.fullmatch(r"\d{1,5}\.HK", upper):
        return StockSdkSymbol(
            original_code=original,
            normalized_code=upper,
            market="hk",
            symbol=upper[:-3].zfill(5),
        )
    if upper.isdigit() and 4 <= len(upper) <= 5:
        return StockSdkSymbol(
            original_code=original,
            normalized_code=upper,
            market="hk",
            symbol=upper.zfill(5),
        )
    if re.fullmatch(r"(105|106|107)\.[A-Z][A-Z0-9.-]*", upper):
        return StockSdkSymbol(
            original_code=original,
            normalized_code=upper,
            market="us",
            symbol=upper,
        )
    if re.fullmatch(r"[A-Z][A-Z0-9.-]*", upper):
        return StockSdkSymbol(
            original_code=original,
            normalized_code=upper,
            market="us",
            symbol=upper,
        )
    return StockSdkSymbol(
        original_code=original,
        normalized_code=normalized,
        market="cn",
        symbol=normalized,
    )


class StockSdkBridgeClient:
    """StockSDK Python bridge 客户端。"""

    def __init__(self, settings: StockSdkSettings) -> None:
        self.settings = settings

    def is_available(self) -> bool:
        """返回 bridge 当前是否可尝试。"""
        if not self.settings.enabled:
            return False
        if not self._resolve_bridge_entry_path().exists():
            return False
        return self._resolve_node_binary() is not None

    def ping(self) -> bool:
        """探测 bridge 是否可用。"""
        try:
            self.invoke("ping", {})
        except StockSdkBridgeError:
            return False
        return True

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """执行 StockSDK 搜索。"""
        data = self.invoke("search", {"query": query, "limit": max(int(limit), 1)})
        return data if isinstance(data, list) else []

    def fetch_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """按股票代码获取单只行情。"""
        symbol = resolve_stocksdk_symbol(stock_code)
        data = self.invoke(
            "quote",
            {
                "stockCode": symbol.normalized_code,
                "market": symbol.market,
                "symbol": symbol.symbol,
            },
        )
        return data if isinstance(data, dict) else None

    def fetch_kline(
        self,
        stock_code: str,
        *,
        period: str,
        adjust: str,
        limit: int,
        before_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按股票代码获取历史 K 线。"""
        symbol = resolve_stocksdk_symbol(stock_code)
        data = self.invoke(
            "kline",
            {
                "stockCode": symbol.normalized_code,
                "market": symbol.market,
                "symbol": symbol.symbol,
                "period": period,
                "adjust": adjust,
                "limit": max(int(limit), 1),
                "beforeDate": before_date,
                "klineFallback": self.settings.kline_fallback,
            },
        )
        return data if isinstance(data, list) else []

    def fetch_market_indices(self, market: str = "a") -> List[Dict[str, Any]]:
        """获取市场指数列表。"""
        data = self.invoke("market_indices", {"market": market})
        return data if isinstance(data, list) else []

    def fetch_market_overview(self) -> Optional[Dict[str, Any]]:
        """获取 A 股市场概览。"""
        data = self.invoke("market_overview", {})
        return data if isinstance(data, dict) else None

    def fetch_northbound_summary(self) -> Optional[Dict[str, Any]]:
        """获取北向资金汇总。"""
        data = self.invoke("northbound_summary", {})
        return data if isinstance(data, dict) else None

    def fetch_market_fund_flow(self) -> Optional[Dict[str, Any]]:
        """获取大盘主力资金。"""
        data = self.invoke("market_fund_flow", {})
        return data if isinstance(data, dict) else None

    def fetch_board_list(self, sector_type: str = "industry") -> List[Dict[str, Any]]:
        """获取行业或概念板块列表。"""
        data = self.invoke("board_list", {"sectorType": sector_type})
        return data if isinstance(data, list) else []

    def fetch_sector_fund_flow_rank(self, sector_type: str = "industry", limit: int = 10) -> List[Dict[str, Any]]:
        """获取板块资金流排行。"""
        data = self.invoke(
            "sector_fund_flow_rank",
            {"sectorType": sector_type, "limit": max(int(limit), 1)},
        )
        return data if isinstance(data, list) else []

    def fetch_sector_fund_flow_history_batch(
        self,
        sector_codes: List[str],
        *,
        limit: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """批量获取多个板块的资金流历史。"""
        data = self.invoke(
            "sector_fund_flow_history_batch",
            {
                "codes": [str(code).strip() for code in sector_codes if str(code).strip()],
                "limit": max(int(limit), 1),
            },
            timeout_ms=max(self.settings.timeout_ms * 2, 8000),
        )
        if not isinstance(data, dict):
            return {}
        return {str(code): rows for code, rows in data.items() if isinstance(rows, list)}

    def invoke(self, action: str, payload: Dict[str, Any], timeout_ms: Optional[int] = None) -> Any:
        """调用 Node bridge 脚本。"""
        if not self.settings.enabled:
            raise StockSdkBridgeError("stocksdk_disabled", "StockSDK 数据源未启用", 503)

        node_bin = self._resolve_node_binary()
        if not node_bin:
            raise StockSdkBridgeError("stocksdk_node_missing", "未找到可执行的 Node.js 18+ 运行时", 503)

        bridge_entry = self._resolve_bridge_entry_path()
        if not bridge_entry.exists():
            raise StockSdkBridgeError("stocksdk_bridge_missing", f"StockSDK bridge 脚本不存在：{bridge_entry}", 503)

        request_payload = {
            "action": action,
            "payload": payload,
            "sdkOptions": self._build_sdk_options(),
        }

        try:
            completed = subprocess.run(
                [node_bin, str(bridge_entry)],
                input=json.dumps(request_payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                timeout=max(int(timeout_ms or self.settings.timeout_ms), 1000) / 1000.0,
                env=self._build_subprocess_env(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise StockSdkBridgeError("stocksdk_timeout", "StockSDK bridge 调用超时", 504) from exc
        except OSError as exc:
            raise StockSdkBridgeError("stocksdk_spawn_failed", f"启动 StockSDK bridge 失败：{exc}", 503) from exc

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if not stdout:
            raise StockSdkBridgeError("stocksdk_empty_response", "StockSDK bridge 未返回结果", 502)

        try:
            payload_obj = json.loads(stdout)
        except ValueError as exc:
            raise StockSdkBridgeError("stocksdk_bad_json", "StockSDK bridge 返回的不是合法 JSON", 502) from exc

        if completed.returncode != 0 and payload_obj.get("ok", True):
            detail = stderr or stdout or f"exit={completed.returncode}"
            raise StockSdkBridgeError("stocksdk_bridge_failed", f"StockSDK bridge 执行失败：{detail}", 502)
        if not payload_obj.get("ok", False):
            error = payload_obj.get("error") or {}
            code = str(error.get("code") or "stocksdk_error")
            message = str(error.get("message") or "StockSDK 请求失败")
            raise StockSdkBridgeError(code, message, 502)
        return payload_obj.get("data")

    def _resolve_node_binary(self) -> Optional[str]:
        node_bin = self.settings.node_bin
        if not node_bin:
            return None
        if Path(node_bin).exists():
            return node_bin
        return shutil.which(node_bin)

    def _resolve_bridge_entry_path(self) -> Path:
        entry = Path(self.settings.bridge_entry)
        if entry.is_absolute():
            return entry
        return REPO_ROOT / entry

    def _build_sdk_options(self) -> Dict[str, Any]:
        return {
            "timeout": self.settings.timeout_ms,
            "rateLimit": {
                "requestsPerSecond": self.settings.rate_limit_rps,
                "maxBurst": self.settings.rate_limit_rps,
            },
            "providerPolicies": {
                "eastmoney": {
                    "timeout": self.settings.timeout_ms,
                    "rateLimit": {
                        "requestsPerSecond": self.settings.rate_limit_rps,
                        "maxBurst": self.settings.rate_limit_rps,
                    },
                }
            },
        }

    def _build_subprocess_env(self) -> Dict[str, str]:
        env = dict()
        for key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "SYSTEMROOT"):
            raw_value = os.environ.get(key)
            if raw_value:
                env[key] = raw_value
        env["NODE_NO_WARNINGS"] = "1"
        return env


_CLIENT: Optional[StockSdkBridgeClient] = None
_CLIENT_LOCK = RLock()


def get_stocksdk_client() -> StockSdkBridgeClient:
    """返回进程内共享的 StockSDK 客户端。"""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None:
            from src.config import get_config

            _CLIENT = StockSdkBridgeClient(settings_from_config(get_config()))
            logger.info("[StockSDK] bridge initialized with entry=%s", _CLIENT.settings.bridge_entry)
    return _CLIENT


__all__ = [
    "StockSdkBridgeClient",
    "StockSdkBridgeError",
    "StockSdkSettings",
    "StockSdkSymbol",
    "get_stocksdk_client",
    "resolve_stocksdk_symbol",
    "settings_from_config",
]
