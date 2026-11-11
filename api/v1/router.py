# -*- coding: utf-8 -*-
"""
@file: router.py
@description: API v1 路由聚合：把各业务域的 APIRouter 挂到统一前缀并打上 OpenAPI 标签；
    由 api.v1 导出为 api_v1_router，最终由 api.app.create_app 挂到 /api/v1。
@author: Lensgcx (GaoCangxiong)

===================================
API v1 路由聚合
===================================

职责：
1. 聚合 v1 版本的所有 endpoint 路由
2. 统一添加 /api/v1 前缀
"""

from fastapi import APIRouter

from api.v1.endpoints import (
    agent,
    alerts,
    alphasift,
    analysis,
    auth,
    backtest,
    decision_signals,
    eod_picker,
    health,
    history,
    intelligence,
    kline,
    limit_pool,
    portfolio,
    recent_search,
    scanner,
    sector,
    stocks,
    stock_metric,
    system_config,
    usage,
    watchlist,
)

# 创建 v1 版本主路由。
# /api/v1 前缀在 api.app 挂载，避免新版 FastAPI 误判子路由 "" 为 empty path。
# router 本身不带 prefix，所有子路由的前缀集中在本文件声明，便于核对对外路径。
router = APIRouter()

# /auth：登录、登出与登录态查询，鉴权中间件对该前缀下的部分路径放行。
router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"]
)

# /agent：Agent 会话与对话能力。
router.include_router(
    agent.router,
    prefix="/agent",
    tags=["Agent"]
)

# /analysis：触发与查询 AI 智能分析任务。
router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["Analysis"]
)

# /history：分析报告历史、报告详情与新闻情报。
router.include_router(
    history.router,
    prefix="/history",
    tags=["History"]
)

# /stocks：股票行情、搜索与基础信息。
router.include_router(
    stocks.router,
    prefix="/stocks",
    tags=["Stocks"]
)

# /stock-metric：股票度量视图（查询 + 导出）。
router.include_router(
    stock_metric.router,
    prefix="/stock-metric",
    tags=["StockMetric"]
)

# /backtest：策略回测运行与结果查询。
router.include_router(
    backtest.router,
    prefix="/backtest",
    tags=["Backtest"]
)

# /system：系统配置、配置校验与 LLM 通道连通性检查。
router.include_router(
    system_config.router,
    prefix="/system",
    tags=["SystemConfig"]
)

# /usage：LLM 调用用量与成本统计。
router.include_router(
    usage.router,
    prefix="/usage",
    tags=["Usage"]
)

# /portfolio：模拟账户、交易流水、持仓快照与风险检查。
router.include_router(
    portfolio.router,
    prefix="/portfolio",
    tags=["Portfolio"]
)

# /alerts：告警规则、触发记录与通知消息。
router.include_router(
    alerts.router,
    prefix="/alerts",
    tags=["Alerts"]
)

# /decision-signals：决策信号的创建、反馈、状态与结果统计。
router.include_router(
    decision_signals.router,
    prefix="/decision-signals",
    tags=["DecisionSignals"]
)

# /alphasift：因子/选股筛选结果。
router.include_router(
    alphasift.router,
    prefix="/alphasift",
    tags=["AlphaSift"]
)

# /eod-picker：盘后选股与候选池。
router.include_router(
    eod_picker.router,
    prefix="/eod-picker",
    tags=["EodPicker"]
)

# /limit-pool：涨停/跌停榜单。
router.include_router(
    limit_pool.router,
    prefix="/limit-pool",
    tags=["LimitPool"]
)

# /intelligence：情报聚合与分析。
router.include_router(
    intelligence.router,
    prefix="/intelligence",
    tags=["Intelligence"]
)

# /scanner：市场扫描与条件选股。
router.include_router(
    scanner.router,
    prefix="/scanner",
    tags=["Scanner"]
)

# /sector：行业板块树、板块行情与资金流。
router.include_router(
    sector.router,
    prefix="/sector",
    tags=["Sector"]
)

# /kline：K 线数据查询。
router.include_router(
    kline.router,
    prefix="/kline",
    tags=["KLine"]
)

# health 不带前缀，对外暴露 /api/v1/health，供探活与鉴权白名单共用。
router.include_router(
    health.router,
    tags=["Health"]
)

# /watchlist：自选股分组与标的维护。
router.include_router(
    watchlist.router,
    prefix="/watchlist",
    tags=["Watchlist"]
)

# /recent-search：个股最近搜索的列表、记录与一键清空。
router.include_router(
    recent_search.router,
    prefix="/recent-search",
    tags=["RecentSearch"]
)
