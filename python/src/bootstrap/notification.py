# -*- coding: utf-8 -*-
"""通知相关端口的装配（发送端口 + Markdown 转图片端口）。

``NotificationService``（application 用例）只依赖 ``NotificationSendPort`` /
``ImageRenderPort`` 协议，不直接构造具体实现。Sender 与渲染实现物理位于
``src.infrastructure`` 后，application 更不能直接 import 具体适配器，因此
:class:`~src.infrastructure.notification.senders.composite_port.InProcessNotificationSendPort`
与 :class:`~src.infrastructure.reporting.image_render_port.Md2ImgImageRenderPort`
的工厂由本装配在进程入口注册；未注册时分别优雅降级为 ``None``
（仅在真实发送/转图时要求装配，与 ``configure_stock_repository`` /
SA2 ``configure_search`` 同型）。
"""

from __future__ import annotations


def configure_notification_send_port() -> None:
    """装配默认发送端口工厂（内置组合适配器）。

    注册 ``InProcessNotificationSendPort`` **类本身**（可调用工厂，签名为
    ``config -> port``）而非 eager 实例：用例侧默认经 ``build_default_send_port(config)``
    现建，避免在 import 期就拉起全部 Sender 依赖。进程启动时调用一次
    （API lifespan / CLI 入口），setter 幂等；传具体工厂可覆盖内置组合。
    """
    from src.application.notification.ports import set_notification_send_port_factory
    from src.infrastructure.notification.senders.composite_port import InProcessNotificationSendPort

    set_notification_send_port_factory(InProcessNotificationSendPort)


def configure_image_render_port() -> None:
    """装配 Markdown 转图片端口工厂（内置 md2img 适配器）。

    注册 ``Md2ImgImageRenderPort`` **类本身**（零参工厂）而非 eager 实例：用例侧
    默认经 ``build_default_image_render_port()`` 现建，避免在 import 期就拉起渲染
    依赖。进程启动时调用一次（CLI 入口 / API lifespan），setter 幂等。
    """
    from src.application.notification.ports import set_image_render_port_factory
    from src.infrastructure.reporting.image_render_port import Md2ImgImageRenderPort

    set_image_render_port_factory(Md2ImgImageRenderPort)
