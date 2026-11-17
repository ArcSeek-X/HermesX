# -*- coding: utf-8 -*-
"""通知渠道的纯常量（R2-B5）。

这些值是"与具体渠道实现无关、零 IO"的业务规则常量（渠道消息体积上限），
不依赖任何 SDK / 网络 / 配置。历史上直接定义在各 Sender 模块内，但 application
层（``NotificationService``）也需要读取它们做发送前的体积判定——application 不能
依赖 ``src.infrastructure``（Sender 物理搬入 infra 后，见 R2-B5），因此把这类纯
常量下沉到 domain，Sender 与 application 双向按子模块精确导入。

本模块只放纯常量，禁止 import 任何外层（infra / config / SDK）。
"""

# WeChat Work image msgtype limit ~2MB (base64 payload)。
# 企业微信图片消息 base64 负载上限，原定义于 wechat_sender.py。
WECHAT_IMAGE_MAX_BYTES = 2 * 1024 * 1024
