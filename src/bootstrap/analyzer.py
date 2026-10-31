# -*- coding: utf-8 -*-
"""Analyzer 域装配：LLM 运行时外部调用端口绑定（Router 构造/直调补全/无代理补全/零价注册）。

``src/application/analysis/analyzer.py`` 的 GeminiAnalyzer 由 pipeline / market_review / agent / API 端点
在函数体内构造，CLI 与 API 两条启动链路都会触达——装配挂在 ``api_lifecycle``
（覆盖 uvicorn/main --serve/server.py 全部 API 启动链路）与 ``main.py`` CLI 同点位
（T5e/T5f configure_*_runtime 双挂点同型）。seam 幂等（仅非 None 覆盖），可重复调用。
"""

from __future__ import annotations


def configure_analyzer_runtime() -> None:
    """装配 Analyzer LLM 运行时端口（幂等：seam 仅非 None 覆盖）。"""
    from src.application.analysis.analyzer_runtime_ports import AnalyzerLLMPort  # noqa: F401  契约锚点
    from src.infrastructure.providers.analyzer_runtime import AnalyzerLLMAdapter
    from src.application.analysis.analyzer import set_analyzer_llm_port

    set_analyzer_llm_port(AnalyzerLLMAdapter())
