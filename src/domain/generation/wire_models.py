# -*- coding: utf-8 -*-
"""Router alias -> LiteLLM wire-model resolution (domain, pure list logic).

W4.5 moved this out of ``src/infrastructure/generation/generation_params.py`` so
``src/config`` (which may only depend on the domain, see ARCHITECTURE_TARGET.md
§2) and ``src/application/agent/provider_trace.py`` can resolve router aliases
without importing the infrastructure layer.

Only alias/membership lookups live here: no provider tables, no IO, no SDK
imports. ``generation_params`` keeps a module-level re-import so its existing
import surface (and ``llm_adapter``) stays valid with a single implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def find_model_list_entries(
    model: str,
    model_list: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Return Router model_list entries matching the configured alias."""
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
    """Return the first Router model_list entry matching the configured alias."""
    entries = find_model_list_entries(model, model_list)
    return entries[0] if entries else None


def resolve_litellm_wire_model(
    model: str,
    model_list: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Resolve a router alias to its underlying LiteLLM wire model."""
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
