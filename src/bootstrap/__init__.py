# -*- coding: utf-8 -*-
"""Shared wiring and lifecycle for every HermesX entry point.

Modules in this package assemble implementations for the application ports and
own process-level lifecycle concerns. They must not import ``api`` or ``bot``:
entry points inject their own drivers (ASGI app, Bot clients) into the
bootstrap functions. Importing a bootstrap module never starts a scheduler,
opens the database or performs network requests.
"""
