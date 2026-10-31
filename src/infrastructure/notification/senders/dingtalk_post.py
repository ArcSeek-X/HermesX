# -*- coding: utf-8 -*-
"""钉钉 markdown 分块发送协议（R2-Q9 归属下沉，包内共享实现）。

原 ``CustomWebhookSender._send_dingtalk_chunked`` 的真实逻辑抽出为独立共享函数：
它以「钉钉 markdown 协议」向**任意 url** 分批 POST，被两类调用方共用——

1. ``CustomWebhookSender`` 自身：自定义 webhook 恰为钉钉机器人时的分批推送；
2. ``InProcessNotificationSendPort.send_dingtalk_chunked``：钉钉 Stream 会话回执
   （``NotificationService._send_via_source_context``）经端口转调。

该逻辑本身不绑定具体渠道，HTTP 发送通过 ``poster`` 回调注入（由调用方提供带
认证/SSL 配置的 post 原语），因此不再"归属"于某个 sender，消除自定义 webhook
独占钉钉命名方法、以及端口伸手调用 sender 私有的坏味道。
"""
import json
import logging
import time as _time
from typing import Any, Callable, Dict

from src.domain.shared.text_chunking import chunk_content_by_max_bytes, slice_at_max_bytes

logger = logging.getLogger(__name__)


def send_dingtalk_markdown_chunked(
    url: str,
    content: str,
    max_bytes: int = 20000,
    *,
    poster: Callable[[str, Dict[str, Any], int], bool],
) -> bool:
    """按钉钉 markdown 协议向 ``url`` 分批发送 ``content``。

    Args:
        url: 目标 webhook / 会话回执地址。
        content: Markdown 正文。
        max_bytes: 单条 body 字节上限（钉钉约 20000）。
        poster: HTTP POST 原语，签名 ``poster(url, payload, timeout) -> bool``，
            由调用方注入以复用各自的认证 / SSL / header 配置。

    Returns:
        是否全部分块发送成功。
    """
    # 为 payload 开销预留空间，避免 body 超限
    budget = max(1000, max_bytes - 1500)
    chunks = chunk_content_by_max_bytes(content, budget)
    if not chunks:
        return False

    total = len(chunks)
    ok = 0

    for idx, chunk in enumerate(chunks):
        marker = f"\n\n📄 *({idx+1}/{total})*" if total > 1 else ""
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "股票分析报告",
                "text": chunk + marker,
            },
        }

        # 如果仍超限（极端情况下），再按字节硬截断一次
        body_bytes = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        if body_bytes > max_bytes:
            hard_budget = max(200, budget - (body_bytes - max_bytes) - 200)
            payload["markdown"]["text"], _ = slice_at_max_bytes(payload["markdown"]["text"], hard_budget)

        if poster(url, payload, timeout=30):
            ok += 1
        else:
            logger.error(f"钉钉分批发送失败: 第 {idx+1}/{total} 批")

        if idx < total - 1:
            _time.sleep(1)

    return ok == total
