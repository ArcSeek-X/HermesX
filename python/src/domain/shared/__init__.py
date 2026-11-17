# -*- coding: utf-8 -*-
"""共享领域包：跨模块复用的纯业务规则（§3 ``domain/shared/``）。

无框架 / ORM / 存储 / IO / 数据源依赖，仅 stdlib。当前成员：

- :mod:`src.domain.shared.url_security`：URL / 主机名安全校验纯规则
  （scheme 合法性、IPv4 数值主机规范化、IDNA 归一、SSRF 元数据地址拦截、
  LLM base URL 校验与 `/models` 端点推导），供 SystemConfigService 等复用。
- :mod:`src.domain.shared.report_language`：报告 / Agent Chat 输出语言的 zh/en/ko
  三本地化纯规则（操作建议/置信度/诊断计数/label 表与 `normalize_report_language`
  等），仅依赖 stdlib 与 `src.domain.decision.scale`，多层复用。
"""
