# -*- coding: utf-8 -*-
"""Markdown 转图片端口的进程内适配器（R3-S11）。

``NotificationService``（application 用例）不再 import 具体渲染实现；本适配器把
``ImageRenderPort`` 原样转发给 ``src.infrastructure.reporting.img_render``
（原 ``src/md2img.py`` 下沉而来）。

设计约束：
- 契约与降级语义逐字保持：``markdown_to_image(markdown_text, max_chars)``，
  失败/缺依赖返回 ``None``，调用方据此回退为文本发送。
- 经模块对象属性调用（而非 ``from ... import markdown_to_image``），使既有测试的
  ``patch("src.infrastructure.reporting.img_render.markdown_to_image")`` 仍然生效。
"""

from __future__ import annotations

from typing import Optional

from src.infrastructure.reporting import img_render


class Md2ImgImageRenderPort:
    """把 ``ImageRenderPort`` 转发给 ``img_render.markdown_to_image``。"""

    def markdown_to_image(
        self, markdown_text: str, max_chars: int = 15000
    ) -> Optional[bytes]:
        return img_render.markdown_to_image(markdown_text, max_chars=max_chars)
