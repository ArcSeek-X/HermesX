# -*- coding: utf-8 -*-
"""Shared wiring and lifecycle for every HermesX entry point.

Modules in this package assemble implementations for the application ports and
own process-level lifecycle concerns. They must not import ``api`` or ``bot``:
entry points inject their own drivers (ASGI app, Bot clients) into the
bootstrap functions. Importing a bootstrap module never starts a scheduler,
opens the database or performs network requests.

本包负责所有 HermesX 入口（CLI / API / WebUI / Desktop）的装配与进程级生命周期。
仅做端口实现装配，禁止反向 import ``api``/``bot``；驱动（ASGI app、Bot 客户端）由入口自行注入。
导入本包不会启动调度器、不会开库、不发网络请求。
"""
