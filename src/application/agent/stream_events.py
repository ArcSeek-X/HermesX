# -*- coding: utf-8 -*-
"""Helpers for building agent progress stream events.

The SSE endpoint forwards plain dictionaries, so these helpers intentionally
return dicts and keep existing field names stable for older clients.

构造 Agent 进度流（SSE）事件的辅助函数；返回普通 dict 以兼容老客户端字段名。
"""

from __future__ import annotations

from typing import Any, Dict


def stream_event(event_type: str, **fields: Any) -> Dict[str, Any]:
    """Build a progress event while dropping unset fields.

    Existing clients depend on top-level fields such as ``type``, ``step``,
    ``tool``, ``success`` and ``duration``.  Newer events can add fields like
    ``stage`` or ``meta`` without changing the callback/SSE contract.

    构造进度事件：固定带 ``type`` 字段，忽略值为 None 的字段；
    老客户端依赖 ``type/step/tool/success/duration``，新字段（stage/meta）增量添加不破坏契约。
    """
    event: Dict[str, Any] = {"type": event_type}
    event.update({key: value for key, value in fields.items() if value is not None})
    return event
