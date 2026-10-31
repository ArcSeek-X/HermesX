# -*- coding: utf-8 -*-
"""stock-sdk 桥接分时适配器：把 ``data_provider.stocksdk_bridge`` 转成应用端口形状。

``data_provider/`` 原位保留为数据源能力包（ADR-001），本适配器只封装“取当日分时”这一
用例所需能力；``get_stocksdk_client`` 惰性导入（与迁移前一致），SDK / Node 缺失或调用
异常时按 best-effort 回退语义返回 ``None``，由应用层降级为空。选源 / 限速 / 主机轮换 /
重试仍由 stock-sdk 内部负责，本层不重复实现。

实现端口：:class:`~src.application.quote.ports.IntradayTimelineBridgePort`
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DataProviderStocksdkTimelineBridge:
    """:class:`IntradayTimelineBridgePort` 的 ``data_provider`` 实现。"""

    def fetch_timeline(self, *, code: str) -> Optional[Dict[str, Any]]:
        """走 stock-sdk 桥接取分时；桥接不可用或异常返回 ``None``（best-effort 回退）。"""
        try:
            from data_provider.stocksdk_bridge import get_stocksdk_client

            client = get_stocksdk_client()
            if not client.is_available():
                return None
            return client.fetch_timeline(code)
        except Exception as exc:  # noqa: BLE001 - SDK/Node 缺失等，降级为桥接不可用
            logger.debug("[Timeline] stock-sdk 桥接不可用 %s: %s", code, exc)
            return None
