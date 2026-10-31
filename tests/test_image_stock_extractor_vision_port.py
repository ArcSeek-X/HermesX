# -*- coding: utf-8 -*-
"""Vision 调用端口（W5.5）的契约回归。

覆盖三件事：

1. 端口未装配时**显式报错**（不静默降级为空识别结果），并指向 bootstrap 装配入口；
2. 识别用例把「模型 / Key / Prompt / 超时 / OpenAI 兼容通道参数」组装好后交给端口，
   适配器只负责发请求——两者可分别测试；
3. 应用层源码不再直接调 litellm（防回退）。

装配由 ``src.bootstrap.analysis.configure_vision_completion_port()`` 完成，
测试会话在 ``tests/conftest.py`` 已装配默认适配器，本文件内自行换/复位。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.application.analysis import image_stock_extractor
from src.application.analysis.vision_ports import (
    get_vision_completion_port,
    set_vision_completion_port,
)
from src.infrastructure.generation import vision_litellm
from src.infrastructure.generation.vision_litellm import LitellmVisionAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_GEMINI_KEY = "sk-gemini-testkey-1234"
_OPENAI_KEY = "sk-openai-testkey-1234"


class _RecordingPort:
    """记录调用参数的假端口。"""

    def __init__(self, text: str = '[]') -> None:
        self.text = text
        self.calls: list[Dict[str, object]] = []

    def complete(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return self.text


def _cfg(**kwargs):
    defaults = dict(
        stock_list=["600519"],
        tushare_token=None,
        llm_model_list=[],
        llm_channels=[],
        litellm_config_path=None,
        litellm_model="",
        litellm_fallback_models=[],
        vision_model="",
        vision_provider_priority="gemini,anthropic,openai",
        gemini_api_keys=[_GEMINI_KEY],
        gemini_model="gemini-3.1-pro-preview",
        anthropic_api_keys=[],
        anthropic_model="claude-sonnet-4-6",
        openai_api_keys=[_OPENAI_KEY],
        openai_model="gpt-5.5",
        openai_base_url=None,
        openai_vision_model=None,
        deepseek_api_keys=[],
        config_validate_mode="warn",
    )
    defaults.update(kwargs)
    from src.config import Config

    return Config(**defaults)


@pytest.fixture()
def restore_default_port():
    """用例内可任意改端口，退出时复位为 conftest 装配的默认适配器。"""

    yield
    set_vision_completion_port(LitellmVisionAdapter())


def test_unassembled_port_raises_explicitly(restore_default_port) -> None:
    set_vision_completion_port(None)

    with pytest.raises(RuntimeError) as excinfo:
        get_vision_completion_port()

    assert "configure_vision_completion_port" in str(excinfo.value)
    assert "main.py" in str(excinfo.value)


def test_call_litellm_vision_delegates_to_port(restore_default_port) -> None:
    port = _RecordingPort('["600519"]')
    set_vision_completion_port(port)

    with patch.object(image_stock_extractor, "get_config", return_value=_cfg()):
        result = image_stock_extractor._call_litellm_vision("b64data", "image/jpeg")

    assert result == '["600519"]'
    assert len(port.calls) == 1
    call = port.calls[0]
    assert call["model"] == "gemini/gemini-3.1-pro-preview"
    assert call["api_key"] == _GEMINI_KEY
    assert call["mime_type"] == "image/jpeg"
    assert call["image_b64"] == "b64data"
    assert call["prompt"] == image_stock_extractor.EXTRACT_PROMPT
    assert call["timeout"] == image_stock_extractor.VISION_API_TIMEOUT
    assert call["max_tokens"] == 1024
    # gemini 通道不注入 OpenAI 兼容参数
    assert call["api_base"] is None
    assert call["extra_headers"] is None


def test_call_litellm_vision_passes_openai_compat_base(restore_default_port) -> None:
    port = _RecordingPort()
    set_vision_completion_port(port)
    cfg = _cfg(
        gemini_api_keys=[],
        openai_vision_model="openai/gpt-5.5",
        openai_base_url="https://aihubmix.com/v1",
    )

    with patch.object(image_stock_extractor, "get_config", return_value=cfg):
        image_stock_extractor._call_litellm_vision("b64data", "image/png")

    call = port.calls[0]
    assert call["api_base"] == "https://aihubmix.com/v1"
    assert call["extra_headers"] == {"APP-Code": "GPIJ3886"}


def test_application_module_does_not_call_litellm_directly() -> None:
    source = (PROJECT_ROOT / "src/application/analysis/image_stock_extractor.py").read_text(
        encoding="utf-8"
    )

    assert "import litellm" not in source
    assert "litellm.completion" not in source


def test_adapter_builds_openai_vision_payload() -> None:
    adapter = LitellmVisionAdapter()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = '["600519"]'

    with patch.object(vision_litellm, "litellm") as fake_litellm:
        fake_litellm.completion = MagicMock(return_value=response)
        text = adapter.complete(
            model="openai/gpt-5.5",
            api_key=_OPENAI_KEY,
            mime_type="image/jpeg",
            image_b64="QUJD",
            prompt="extract",
            timeout=60,
            max_tokens=512,
            api_base="https://example.invalid/v1",
            extra_headers={"X-Test": "1"},
        )

    assert text == '["600519"]'
    kwargs = fake_litellm.completion.call_args[1]
    assert kwargs["model"] == "openai/gpt-5.5"
    assert kwargs["max_tokens"] == 512
    assert kwargs["timeout"] == 60
    assert kwargs["api_key"] == _OPENAI_KEY
    assert kwargs["api_base"] == "https://example.invalid/v1"
    assert kwargs["extra_headers"] == {"X-Test": "1"}
    content = kwargs["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "extract"}
    assert content[1]["image_url"]["url"] == "data:image/jpeg;base64,QUJD"


def test_adapter_raises_on_empty_response() -> None:
    adapter = LitellmVisionAdapter()
    empty = MagicMock()
    empty.choices = []

    with patch.object(vision_litellm, "litellm") as fake_litellm:
        fake_litellm.completion = MagicMock(return_value=empty)
        with pytest.raises(ValueError, match="returned empty response"):
            adapter.complete(
                model="gemini/x",
                api_key=None,
                mime_type="image/jpeg",
                image_b64="QUJD",
                prompt="p",
                timeout=1,
            )


def test_port_protocol_is_runtime_checkable() -> None:
    from src.application.analysis.vision_ports import VisionCompletionPort

    assert isinstance(LitellmVisionAdapter(), VisionCompletionPort)


def test_optional_api_base_defaults_none() -> None:
    """适配器未收到 api_base / extra_headers 时不应向 litellm 注入这两个键。"""
    adapter = LitellmVisionAdapter()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "ok"

    with patch.object(vision_litellm, "litellm") as fake_litellm:
        fake_litellm.completion = MagicMock(return_value=response)
        adapter.complete(
            model="gemini/x",
            api_key=None,
            mime_type="image/jpeg",
            image_b64="QUJD",
            prompt="p",
            timeout=1,
        )

    kwargs = fake_litellm.completion.call_args[1]
    assert "api_base" not in kwargs
    assert "extra_headers" not in kwargs
