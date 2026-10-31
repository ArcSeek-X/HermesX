"""通知发送端口契约（R2-B3）。

``NotificationService`` 历史上通过多重继承 ``src/infrastructure/notification/senders/`` 下的 14 个
Sender 类来获得"向具体渠道发送"的能力，使 application 层直接耦合了 sender 实现。
本模块把这部分能力收敛为一个显式端口：``NotificationService`` 只依赖
``NotificationSendPort`` 协议，具体发送由组合适配器
``InProcessNotificationSendPort``（``src/infrastructure/notification/senders/composite_port.py``）实现。

设计约束（见 architecture_migration_progress §0.114）：
- 方法面即 §5.3 实测的 23 个真实调用点，不新增、不遗漏；名称使用公开名（无 ``_`` 前缀），
  以便 ``forbid_private_members`` 守卫对 ports.py 零命中。
- 保持结构化（Protocol / 鸭子类型），不引入 ABC 继承链，避免再次形成"is-a Sender"耦合。
- application → domain 合法；本文件不 import ``src.infrastructure.notification.senders``（实现下沉到适配器）。
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class NotificationSendPort(Protocol):
    """NotificationService 所需的全部发送能力（按真实调用点去重）。

    实现方负责持有各渠道 Sender 并逐方法转发；调用方（``NotificationService``）
    只在同名 thin forwarder 中转调本端口，从而保持对外方法面与继承版完全一致。
    """

    # —— 静态渠道派发（14 个渠道，调用点 notification.py:_send_to_static_channel）——
    def send_wechat(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool: ...

    def send_dingtalk(self, content: str, title: str = "", timeout_seconds: int = 10) -> bool: ...

    def send_feishu(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool: ...

    def send_telegram(self, content: str, *args: Any, **kwargs: Any) -> bool: ...

    def send_email(self, content: str, *args: Any, **kwargs: Any) -> bool: ...

    def send_pushover(self, content: str, *args: Any, **kwargs: Any) -> bool: ...

    def send_ntfy(self, content: str, *args: Any, **kwargs: Any) -> bool: ...

    def send_gotify(self, content: str, *args: Any, **kwargs: Any) -> bool: ...

    def send_pushplus(self, content: str, *args: Any, **kwargs: Any) -> bool: ...

    def send_serverchan3(self, content: str, *args: Any, **kwargs: Any) -> bool: ...

    def send_custom(self, content: str) -> bool: ...

    def send_discord(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool: ...

    def send_slack(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool: ...

    def send_astrbot(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool: ...

    # —— 图片 / 文件变体（Issue #289，调用点 _send_to_static_channel 的 use_image 分支）——
    def send_wechat_image(self, image_bytes: bytes) -> bool: ...

    def send_telegram_photo(self, image_bytes: bytes) -> bool: ...

    def send_email_with_inline_image(
        self, image_bytes: bytes, receivers: Optional[List[str]] = None
    ) -> bool: ...

    def send_custom_webhook_image(
        self, image_bytes: bytes, fallback_content: str = ""
    ) -> bool: ...

    def send_slack_image(self, image_bytes: bytes, fallback_content: str = "") -> bool: ...

    def send_feishu_file(self, file_path: str) -> bool: ...

    def send_dingtalk_chunked(self, url: str, content: str, max_bytes: int = 20000) -> bool: ...

    # —— 邮件收件人解析（调用点 _send_to_static_channel 的 EMAIL 分支）——
    def all_email_receivers(self) -> List[str]: ...

    def receivers_for_stocks(self, stock_codes: List[str]) -> List[str]: ...

    # —— 飞书 Stream 会话回执（R2-B5：具体客户端构造/分块/发送下沉组合适配器）——
    def send_stream_reply(self, chat_id: str, content: str) -> bool: ...


@runtime_checkable
class ReplyClient(Protocol):
    """飞书 Stream 会话回执的窄端口（R2-B4）。

    ``bot/platforms/feishu_stream.py`` 历史上直接 ``import`` 具体实现
    ``src.infrastructure.notification.senders.feishu_reply_client.FeishuReplyClient`` 并在事件处理器里
    ``FeishuReplyClient(app_id, app_secret)`` 现建，使驱动层在运行期耦合 sender 实现；
    sender 物理搬入 ``src/infrastructure/`` 后（R2-B5）会命中 bot 禁入面而判红。本端口把
    "向来源会话回执"这一能力抽象出来：``FeishuStreamHandler`` 只按协议调用（仅用到
    ``reply_text``），具体客户端由入口（``main.py`` 启动 Stream 前）经工厂注入，bot 不再
    持有 sender 符号。

    仅声明 handler 实际使用的公开方法，保持结构化（鸭子类型），不引入继承链；
    方法名均为公开名（无 ``_`` 前缀），以便 ``forbid_private_members`` 守卫零命中。
    """

    def reply_text(
        self,
        message_id: str,
        text: str,
        at_user: bool = False,
        user_id: Optional[str] = None,
    ) -> bool: ...


# —— 默认发送端口的 bootstrap seam（R2-B5）——
#
# application 不得 import src.infrastructure；Sender 物理搬入 infra 后，
# NotificationService 的默认内置组合适配器不能再由 application 直接构造，改经
# 下面这对 hook：具体工厂（infra 的 InProcessNotificationSendPort）由入口（main.py /
# api_lifecycle）通过 src/bootstrap.configure_notification_send_port() 注册；未注册时
# build_default_send_port 优雅降级为 None（与 SA2 configure_search “未注册降级为空”同型）。
_send_port_factory: Optional[Callable[[Any], "NotificationSendPort"]] = None


def set_notification_send_port_factory(
    factory: Optional[Callable[[Any], "NotificationSendPort"]]
) -> None:
    """注册默认发送端口工厂（入口装配用，幂等；传 None 可重置）。"""
    global _send_port_factory
    _send_port_factory = factory


def build_default_send_port(config: Any) -> Optional[NotificationSendPort]:
    """用已注册的工厂构造默认发送端口；未注册时返回 None（发送时才要求装配）。"""
    if _send_port_factory is None:
        return None
    return _send_port_factory(config)


# —— 图片渲染端口的 bootstrap seam（R3-S11）——
#
# Markdown 转图片（Issue #289/#455）在 application 侧只服务通知渠道，具体渲染
# （wkhtmltoimage / markdown-to-file）属基础设施能力。``md2img`` 物理搬入
# ``src.infrastructure.reporting.img_render`` 后，application 不能再 import 它，
# 改经下面这对 hook：工厂由入口（main.py / api_lifespan）通过
# ``src/bootstrap.configure_image_render_port()`` 注册；未注册时返回 None，
# 发送侧自动回退为文本（与“渲染依赖不可用”同一降级路径，不 fail-fast）。


@runtime_checkable
class ImageRenderPort(Protocol):
    """Markdown 渲染为图片的能力（失败或缺依赖时返回 None，由调用方回退文本）。"""

    def markdown_to_image(
        self, markdown_text: str, max_chars: int = 15000
    ) -> Optional[bytes]: ...


_image_render_port_factory: Optional[Callable[[], "ImageRenderPort"]] = None


def set_image_render_port_factory(
    factory: Optional[Callable[[], "ImageRenderPort"]],
) -> None:
    """注册默认图片渲染端口工厂（入口装配用，幂等；传 None 可重置）。"""
    global _image_render_port_factory
    _image_render_port_factory = factory


def build_default_image_render_port() -> Optional[ImageRenderPort]:
    """用已注册的工厂构造默认图片渲染端口；未注册时返回 None（回退文本发送）。"""
    if _image_render_port_factory is None:
        return None
    return _image_render_port_factory()
