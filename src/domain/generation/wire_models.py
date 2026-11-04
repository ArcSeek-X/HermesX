# -*- coding: utf-8 -*-
"""Router alias -> LiteLLM wire-model resolution (domain, pure list logic).

W4.5 moved this out of ``src/infrastructure/generation/generation_params.py`` so
``src/config`` (which may only depend on the domain, see ARCHITECTURE_TARGET.md
§2) and ``src/application/agent/provider_trace.py`` can resolve router aliases
without importing the infrastructure layer.

Only alias/membership lookups live here: no provider tables, no IO, no SDK
imports. ``generation_params`` keeps a module-level re-import so its existing
import surface (and ``llm_adapter``) stays valid with a single implementation.

Router 别名 -> LiteLLM wire-model（真实模型名）的解析，纯列表逻辑、零 IO。
抽离自 infrastructure 层，使 ``src/config`` 与 agent provider_trace 在只依赖 domain 的前提下也能解析别名。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def find_model_list_entries(
    model: str,
    model_list: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Return Router model_list entries matching the configured alias.

    在 LiteLLM ``model_list`` 中找出所有 ``model_name``（或 ``litellm_params.model``）
    匹配给定别名的条目；无别名或列表为空时返回 []。
    """
    normalized_model = (model or "").strip()
    if not normalized_model or not model_list:
        return []

    entries: List[Dict[str, Any]] = []
    for entry in model_list:
        model_name = str(entry.get("model_name") or "").strip()
        if not model_name:
            params = entry.get("litellm_params", {}) or {}
            model_name = str(params.get("model") or "").strip()
        if model_name == normalized_model:
            entries.append(entry)
    return entries


def find_model_list_entry(
    model: str,
    model_list: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Return the first Router model_list entry matching the configured alias.

    返回匹配别名的第一个 ``model_list`` 条目（无则 None）。
    """
    entries = find_model_list_entries(model, model_list)
    return entries[0] if entries else None


def resolve_litellm_wire_model(
    model: str,
    model_list: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Resolve a router alias to its underlying LiteLLM wire model.

    把 Router 别名解析为底层 LiteLLM wire-model（真实模型名）；找不到映射时原样返回别名。
    """
    normalized_model = (model or "").strip()
    if not normalized_model or not model_list:
        return normalized_model

    model_entry = find_model_list_entry(normalized_model, model_list)
    if not model_entry:
        return normalized_model

    params = model_entry.get("litellm_params", {}) or {}
    wire_model = str(params.get("model") or "").strip()
    if wire_model:
        return wire_model
    return normalized_model
