# -*- coding: utf-8 -*-
"""
@file: sector.py
@description: 板块与市场数据端点：行业树、市场指数与总览卡片、资金流、板块成分股及各类云图；由 api.v1.router 挂到 /api/v1/sector，取数与多源降级在 src.application.market.SectorService。
@author: Lensgcx (GaoCangxiong)

===================================
板块数据接口（申万行业分类 - 层级树形结构）
===================================

职责：
1. GET /api/v1/sector/industry - 行业板块树形数据（一级行业包含二级行业子节点）
2. GET /api/v1/sector/{sector_code}/stocks - 板块成分股列表
3. GET /api/v1/sector/market-indices - 市场指数数据（上证、深证、创业板等）
4. GET /api/v1/sector/market-overview - 市场概览（涨跌家数、成交额、涨跌停家数、量能）
5. GET /api/v1/sector/northbound-flow - 北向资金（沪深港通）净流入
6. GET /api/v1/sector/market-fund-flow - 大盘主力资金净流入

端点层只做 Query 校验、错误映射（400 / 404 / 502）与响应返回；来源优先级、降级
策略与响应信封在 ``src.application.market.SectorService``（用例），具体数据源在
``src.infrastructure.providers.sector_provider`` → ``data_provider/sector/*``。
端点不直接对接数据源包。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_sector_service
from src.application.market import SectorService, SectorSnapshotUnavailableError

# 模块级日志器，记录板块数据取数失败。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/sector。
router = APIRouter()


def _require(result: Optional[Dict[str, Any]], detail: str) -> Dict[str, Any]:
    """空数据统一映射 502。

    数据源全部失败时服务层返回空结果，此处转成明确的 502，避免前端把「没有数据」误展示成真实的空板块。

    Args:
        result: 服务层返回值；为空或 None 视为不可用。
        detail: 返回给客户端的错误说明。

    Returns:
        Dict[str, Any]: 非空的服务层结果。

    Raises:
        HTTPException: 结果为空时返回 502。
    """
    if not result:
        raise HTTPException(status_code=502, detail=detail)
    return result


@router.get("/industry")
def get_industry_sectors(
    time: str = Query("", description="快照时间，如 '10:00'，空字符串表示实时数据"),
    service: SectorService = Depends(get_sector_service),
):
    """获取行业板块树形数据（申万行业分类）。

    一级行业包含二级行业子节点；端点只做时间参数透传与异常映射。

    Args:
        time: 统计时间范围参数，由服务层解释。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        行业树形结构数据。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    try:
        result = service.get_industry_treemap(time_str=time)
    except SectorSnapshotUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _require(result, "数据获取失败")


@router.get("/market-indices")
def get_market_indices(
    market: str = Query("a", description="市场类型：a=A股，us=欧美股，jp-kr=日韩"),
    service: SectorService = Depends(get_sector_service),
):
    """获取市场指数数据。

    Args:
        market: 市场标识，决定取哪个市场的指数集合。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        指数列表及涨跌数据。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    if market not in ("a", "us", "jp-kr"):
        raise HTTPException(status_code=400, detail="market 仅支持 a、us 或 jp-kr")
    return _require(service.get_market_indices(market=market), "市场指数数据获取失败")


@router.get("/market-cards")
def get_market_cards(
    market: str = Query("a", description="市场类型：a=A股，hk-us=港美，jp-kr=日韩"),
    service: SectorService = Depends(get_sector_service),
):
    """获取市场总览 TAB 统一卡片列表。

    把多个市场指标打包成前端卡片可直接消费的结构，减少首屏请求数。

    Args:
        market: 市场标识。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        统一形状的卡片数据列表。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    if market not in ("a", "hk-us", "jp-kr"):
        raise HTTPException(status_code=400, detail="market 仅支持 a、hk-us 或 jp-kr")
    return _require(service.get_market_cards(market=market), "市场卡片数据获取失败")


@router.get("/market-overview")
def get_market_overview(service: SectorService = Depends(get_sector_service)):
    """获取市场概览数据（涨跌家数 + 量能）。

    Args:
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        涨跌家数与成交量能等概览指标。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    return _require(service.get_market_overview(), "市场概览数据获取失败")


@router.get("/northbound-flow")
def get_northbound_flow(service: SectorService = Depends(get_sector_service)):
    """获取北向资金（沪深港通）净流入数据。

    Args:
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        北向资金净流入序列或快照。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    return service.get_northbound_flow()


@router.get("/market-fund-flow")
def get_market_fund_flow(service: SectorService = Depends(get_sector_service)):
    """获取大盘主力资金净流入。

    Args:
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        主力资金净流入序列或快照。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    return service.get_market_fund_flow()


@router.get("/{sector_code}/stocks")
def get_sector_stocks(
    sector_code: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
):
    """获取板块成分股列表。

    以板块代码定位，支持分页；成分股口径由服务层统一，端点不自行筛选。

    Args:
        sector_code: 板块代码，来自路径参数。
        page: 页码，从 1 开始。
        page_size: 每页条数。

    Returns:
        当前页成分股与总数。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    logger.info("成分股接口调用：sector_code=%s, page=%s, page_size=%s", sector_code, page, page_size)
    return {"total": 0, "stocks": []}


@router.get("/stock-map")
def get_stock_cloud_map(
    time: str = Query("", description="快照时间，如 '10:00'，空字符串表示实时数据"),
    service: SectorService = Depends(get_sector_service),
):
    """获取个股云图数据（三级树：行业→子行业→个股）。

    Args:
        time: 统计时间范围参数，由服务层解释。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        三级树形云图数据。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    try:
        result = service.get_stock_cloud_map(time_str=time)
    except SectorSnapshotUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _require(result, "个股云图数据获取失败")


@router.get("/etf-map")
def get_etf_cloud_map(
    period: str = Query("yesterday", description="涨跌幅周期：yesterday/week/month/quarter/half_year/ytd/year/three_year"),
    top_n: int = Query(100, ge=10, le=500, description="选取市值前 N 的 ETF"),
    service: SectorService = Depends(get_sector_service),
):
    """获取 ETF 云图数据（扁平列表，按市值排序）。

    Args:
        period: 统计周期参数。
        top_n: 返回条目数上限。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        按市值排序的 ETF 扁平列表。

    Raises:
        HTTPException: 取数失败返回 502。
    """
    result = service.get_etf_cloud_map(period=period, top_n=top_n)
    return _require(result, "ETF 云图数据获取失败")


@router.get("/fund-flow-history")
def get_sector_fund_flow_history(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
    limit: int = Query(30, ge=5, le=100, description="返回天数"),
    top_n: int = Query(10, ge=1, le=30, description="资金流排名前 N 的板块"),
    sector_codes: Optional[str] = Query(None, description="指定板块代码，逗号分隔，如 BK0475,BK0717"),
    service: SectorService = Depends(get_sector_service),
):
    """获取板块资金流历史序列（日线）。

    支持按板块类型、序列长度、TopN 与指定板块代码集合筛选。

    Args:
        sector_type: 板块类型（行业/概念/地域）。
        limit: 历史序列长度上限。
        top_n: 参与统计的板块数量上限。
        sector_codes: 指定板块代码集合；为空时按 top_n 自动选取。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        各板块的日线资金流序列。
    """
    specified_codes = [code.strip() for code in sector_codes.split(",") if code.strip()] if sector_codes else None
    try:
        result = service.get_sector_fund_flow_history(
            sector_type=sector_type,
            limit=limit,
            top_n=top_n,
            sector_codes=specified_codes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="指定的板块代码未找到") from exc
    return _require(result, "板块资金流排行数据获取失败")


@router.get("/fund-flow-sectors")
def get_sector_fund_flow_sector_list(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
    service: SectorService = Depends(get_sector_service),
):
    """获取板块资金流可选板块列表（用于前端多选下拉框）。

    Args:
        sector_type: 板块类型。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        可选的板块代码与名称列表。
    """
    return _require(
        service.get_sector_fund_flow_sector_list(sector_type=sector_type),
        "板块列表获取失败",
    )


@router.get("/board-list")
def get_board_list(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
    service: SectorService = Depends(get_sector_service),
):
    """获取板块卡片列表数据。

    Args:
        sector_type: 板块类型。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        板块卡片数据列表。
    """
    return _require(service.get_board_list(sector_type=sector_type), "板块列表获取失败")


@router.get("/concept-map")
def get_concept_cloud_map(
    period: str = Query("yesterday", description="涨跌幅周期：yesterday/week/month/quarter/half_year/ytd/year/three_year"),
    top_n: int = Query(100, ge=10, le=500, description="选取市值前 N 的概念"),
    service: SectorService = Depends(get_sector_service),
):
    """获取概念云图数据（扁平列表，按市值排序）。

    Args:
        period: 统计周期参数。
        top_n: 返回条目数上限。
        service: 板块用例，由 Depends(get_sector_service) 装配。

    Returns:
        按市值排序的概念板块扁平列表。
    """
    result = service.get_concept_cloud_map(period=period, top_n=top_n)
    return _require(result, "概念云图数据获取失败")
