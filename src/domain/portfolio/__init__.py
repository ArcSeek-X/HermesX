# -*- coding: utf-8 -*-
"""持仓与风险领域包。

分层约定：

- 本包只放**零 IO 的纯业务规则**：占比计算、集中度排序与告警判定、回撤指标、
  止损接近度、主板块挑选。
- 快照取数、货币换算、仓储访问仍留在 ``src/application/portfolio/``
  （``PortfolioRepositoryPort`` + ``PortfolioService.convert_amount``）；调用方先把
  各持仓折算为统一计价币种，再把纯数值交给本包聚合。
- 与 ``src.domain.notification`` 同约定：本包 ``__init__`` **不做 eager 聚合**，
  消费方按子模块精确导入：``src.domain.portfolio.risk_rules``。
"""
