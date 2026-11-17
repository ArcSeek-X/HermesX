# -*- coding: utf-8 -*-
"""通知基础设施包（R2-B5）。

历史上逐渠道 Sender 与内置组合适配器位于顶层 ``src/notification_sender/``；随 R2
通知簇迁移，整体物理下沉到 ``src/infrastructure/notification/senders/``，与
``NotificationSendPort``（application 用例契约端口）解耦：

- ``senders/``：14 个渠道 Sender + ``FeishuReplyClient`` + ``composite_port``
  （内置组合适配器 ``InProcessNotificationSendPort``），均为具体 IO 实现。
- application 只依赖端口协议，不 import 本子树；具体适配器经
  ``src/bootstrap/notification.py`` 的 seam 在进程入口注册（详见 R2-B5）。

本包不 re-export 具体 Sender（避免 application/入口按包名误引造成隐式耦合），
消费方按 ``src.infrastructure.notification.senders.<module>`` 精确导入。
"""
