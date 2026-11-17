# -*- coding: utf-8 -*-
"""生成域纯规则。

分层约定：

- 本包只放**与厂商无关、零 IO 的纯规则**：模型输出清洗、Hermes 路由/命名/脱敏规则、
  诊断文本脱敏。
- 需要 httpx/openai SDK、subprocess、文件 IO 的实现留在
  ``src/infrastructure/generation/``（R2-A4 搬包后落位）。
- 本包 ``__init__`` **不做 eager 聚合**，避免 ``config -> domain`` 拉起重依赖
  （见 ``documents/framework/refactoring/ARCHITECTURE_MIGRATION_PROGRESS.md`` 历史坑 #3）。
"""
