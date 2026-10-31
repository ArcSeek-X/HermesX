# -*- coding: utf-8 -*-
"""Generation / Agent backend identity vocabulary (pure).

本模块是 backend **身份标识与集合口径**的唯一真源：backend id 常量、
本地 CLI 集合、agent 能力集合、派生出的 generation-only / supported 集合。
纯常量、无依赖，因此可被 ``src/config``（字段注册与校验）直接消费。

解析与降级策略（``resolve_*`` / ``normalize_backend_id``）需要
``src.application.generation.ports`` 的 ``GenerationError``，仍留在
``src/application/generation/catalog.py``（领域层不得反向依赖应用层）。
"""

from __future__ import annotations

from typing import FrozenSet

LITELLM_BACKEND_ID = "litellm"
CODEX_CLI_BACKEND_ID = "codex_cli"
CLAUDE_CODE_CLI_BACKEND_ID = "claude_code_cli"
OPENCODE_CLI_BACKEND_ID = "opencode_cli"
AUTO_AGENT_BACKEND_ID = "auto"

LOCAL_CLI_GENERATION_BACKEND_IDS: FrozenSet[str] = frozenset({
    CODEX_CLI_BACKEND_ID,
    CLAUDE_CODE_CLI_BACKEND_ID,
    OPENCODE_CLI_BACKEND_ID,
})
AGENT_CAPABLE_BACKEND_IDS: FrozenSet[str] = frozenset({LITELLM_BACKEND_ID})
# Phase 4 local CLI backends are generation-only today. Keep this derived so a
# future agent-capable local backend does not remain classified as generation-only.
GENERATION_ONLY_BACKEND_IDS: FrozenSet[str] = LOCAL_CLI_GENERATION_BACKEND_IDS - AGENT_CAPABLE_BACKEND_IDS

SUPPORTED_GENERATION_BACKENDS: FrozenSet[str] = frozenset({
    LITELLM_BACKEND_ID,
    *LOCAL_CLI_GENERATION_BACKEND_IDS,
})
SUPPORTED_GENERATION_FALLBACK_BACKENDS: FrozenSet[str] = frozenset({LITELLM_BACKEND_ID})
SUPPORTED_AGENT_GENERATION_BACKENDS: FrozenSet[str] = frozenset({
    AUTO_AGENT_BACKEND_ID,
    *AGENT_CAPABLE_BACKEND_IDS,
    *GENERATION_ONLY_BACKEND_IDS,
})
SUPPORTED_AGENT_UI_BACKENDS: FrozenSet[str] = frozenset({
    AUTO_AGENT_BACKEND_ID,
    *AGENT_CAPABLE_BACKEND_IDS,
})
