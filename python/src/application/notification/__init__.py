# -*- coding: utf-8 -*-
"""通知用例编排（多渠道通知意图、路由、内容组装与失败隔离）。

按 ``ARCHITECTURE_TARGET.md`` §4.1 的归属口径，通知的"发送意图与编排"落在
``application/notification/``，具体逐渠道 SDK 发送实现留在 ``src/infrastructure/notification/senders/``
（基础设施层，``NotificationService`` 经多重继承复用其能力）。``src/notification.py``
及其编排门面自 ``src/`` 下沉至本包。消费方直接子模块 import（不在此重复导出，
避免 eager 聚合引入循环依赖，与 ``application/runtime``、``application/intelligence``
先例一致）。
"""
