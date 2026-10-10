# -*- coding: utf-8 -*-
"""
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
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from data_provider.sector.eastmoney_source import (
    fetch_sector_fund_flow_rank as fetch_sector_fund_flow_rank_from_eastmoney,
    get_cached_board_list as get_cached_board_list_from_eastmoney,
    get_cached_market_fund_flow as get_cached_market_fund_flow_from_eastmoney,
    get_cached_market_indices as get_cached_market_indices_from_eastmoney,
    get_cached_market_overview as get_cached_market_overview_from_eastmoney,
    get_cached_northbound_flow as get_cached_northbound_flow_from_eastmoney,
    get_sector_fund_flow_history_data as get_sector_fund_flow_history_data_from_eastmoney,
)
from data_provider.sector.market_cards_source import get_market_cards as get_market_cards_from_source
from data_provider.sector.shidaotec_source import (
    SnapshotDataUnavailableError,
    get_board_card_list as get_board_card_list_from_shidaotec,
    get_concept_treemap,
    get_etf_treemap,
    get_industry_treemap,
    get_stock_treemap,
)
from data_provider.sector.stocksdk_source import (
    fetch_sector_fund_flow_rank as fetch_sector_fund_flow_rank_from_stocksdk,
    get_cached_board_list as get_cached_board_list_from_stocksdk,
    get_cached_market_fund_flow as get_cached_market_fund_flow_from_stocksdk,
    get_cached_market_indices as get_cached_market_indices_from_stocksdk,
    get_cached_market_overview as get_cached_market_overview_from_stocksdk,
    get_cached_northbound_flow as get_cached_northbound_flow_from_stocksdk,
    get_sector_fund_flow_history_data as get_sector_fund_flow_history_data_from_stocksdk,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _prefer_stocksdk_then_fallback(stocksdk_loader, fallback_loader):
    """优先尝试 StockSDK，失败后回退到既有数据源。"""
    try:
        data = stocksdk_loader()
    except Exception as exc:  # noqa: BLE001 - endpoint 只负责聚合回退
        logger.warning("StockSDK sector provider failed, fallback to legacy source: %s", exc)
        data = None
    if data:
        return data
    return fallback_loader()


def _prefer_loader_chain(*loaders):
    """按顺序尝试多个 provider，返回第一份可用数据。"""
    for loader in loaders:
        try:
            data = loader()
        except Exception as exc:  # noqa: BLE001 - endpoint 只负责聚合回退
            logger.warning("Sector provider failed in fallback chain: %s", exc)
            data = None
        if data:
            return data
    return None


@router.get("/industry")
def get_industry_sectors(
    time: str = Query("", description="快照时间，如 '10:00'，空字符串表示实时数据"),
):
    """
    获取行业板块树形数据（申万行业分类）

    返回层级结构：
    - 一级行业（电子、银行、医药生物等）作为父节点
    - 二级行业（半导体、国有大型银行等）作为子节点
    - 父节点颜色 = 子节点加权平均涨跌幅

    参数：
    - time: 快照时间（如 '10:00'），为空则返回实时数据
    """
    try:
        result = get_industry_treemap(time)
    except SnapshotDataUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=502, detail="数据获取失败")
    return result


@router.get("/market-indices")
def get_market_indices(market: str = Query("a", description="市场类型：a=A股，us=欧美股，jp-kr=日韩")):
    """
    获取市场指数数据

    返回主要市场指数的实时行情：
    - market=a：上证指数、深证成指、创业板指、科创50、上证50、沪深300、中证500 等
    - market=us：道琼斯、标普500、纳斯达克、纳斯达克100、纳指金龙中国、纳指金融100、纳指互联网、费城半导体
    - market=jp-kr：日经指数、韩国综指(KOSPI)、韩国KOSDAQ
    """
    if market not in ("a", "us", "jp-kr"):
        raise HTTPException(status_code=400, detail="market 仅支持 a、us 或 jp-kr")
    data = _prefer_stocksdk_then_fallback(
        lambda: get_cached_market_indices_from_stocksdk(market),
        lambda: get_cached_market_indices_from_eastmoney(market),
    )
    if not data:
        raise HTTPException(status_code=502, detail="市场指数数据获取失败")
    return {"indices": data}


@router.get("/market-cards")
def get_market_cards(
    market: str = Query("a", description="市场类型：a=A股，hk-us=港美，jp-kr=日韩"),
):
    """
    获取市场总览 TAB 统一卡片列表。

    返回：
    - market: 与前端 MARKET_TABS.key 保持一致的市场标识
    - cards: 已按卡片渲染契约组装好的列表
    """
    if market not in ("a", "hk-us", "jp-kr"):
        raise HTTPException(status_code=400, detail="market 仅支持 a、hk-us 或 jp-kr")

    result = get_market_cards_from_source(market)
    if not result:
        raise HTTPException(status_code=502, detail="市场卡片数据获取失败")
    return result


@router.get("/market-overview")
def get_market_overview():
    """
    获取市场概览数据（涨跌家数 + 量能）

    数据来源：东方财富 push2delay API（全量 A 股实时行情）
    返回：
    - riseCount: 上涨家数
    - fallCount: 下跌家数
    - flatCount: 平盘家数
    - totalAmount: 当日成交额（元）
    """
    data = _prefer_stocksdk_then_fallback(
        get_cached_market_overview_from_stocksdk,
        get_cached_market_overview_from_eastmoney,
    )
    if not data:
        raise HTTPException(status_code=502, detail="市场概览数据获取失败")
    return data


@router.get("/northbound-flow")
def get_northbound_flow():
    """
    获取北向资金（沪深港通）净流入数据

    数据来源：东方财富 kamt 接口
    注意：自 2024-08 起北向资金实时数据停止盘中披露，接口可能返回空数据，
    此时返回 netInflow=None（200），由前端展示占位符，不抛错。
    """
    data = _prefer_stocksdk_then_fallback(
        get_cached_northbound_flow_from_stocksdk,
        get_cached_northbound_flow_from_eastmoney,
    )
    if not data:
        return {"netInflow": None, "name": "北向资金"}
    return data


@router.get("/market-fund-flow")
def get_market_fund_flow():
    """
    获取大盘主力资金净流入

    数据来源：东方财富 ulist 实时接口（上证指数 + 深证成指主力净流入汇总）
    返回：mainNetInflow（元）、mainNetInflowPercent（%）、date（实时接口为 None）
    """
    data = _prefer_stocksdk_then_fallback(
        get_cached_market_fund_flow_from_stocksdk,
        get_cached_market_fund_flow_from_eastmoney,
    )
    if not data:
        return {"mainNetInflow": None, "mainNetInflowPercent": None, "date": None}
    return data


@router.get("/{sector_code}/stocks")
def get_sector_stocks(
    sector_code: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
):
    """
    获取板块成分股列表

    注意：时到量化 API 不提供成分股数据，此接口暂返回空列表。
    如需成分股功能，需要接入其他数据源（如东方财富、新浪等）。
    """
    logger.info("成分股接口调用：sector_code=%s, page=%s, page_size=%s", sector_code, page, page_size)
    return {"total": 0, "stocks": []}


@router.get("/stock-map")
def get_stock_cloud_map(
    time: str = Query("", description="快照时间，如 '10:00'，空字符串表示实时数据"),
):
    """
    获取个股云图数据（三级树：行业→子行业→个股）

    参数：
    - time: 快照时间（如 '10:00'），为空则返回实时数据
    """
    try:
        result = get_stock_treemap(time)
    except SnapshotDataUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=502, detail="个股云图数据获取失败")
    return result


@router.get("/etf-map")
def get_etf_cloud_map(
    period: str = Query("yesterday", description="涨跌幅周期：yesterday/week/month/quarter/half_year/ytd/year/three_year"),
    top_n: int = Query(100, ge=10, le=500, description="选取市值前 N 的 ETF"),
):
    """
    获取 ETF 云图数据（扁平列表，按市值排序）

    参数：
    - period: 涨跌幅周期（yesterday=昨日涨跌幅, week=近一周, month=近一月,
              quarter=近三月, half_year=近半年, ytd=今年以来, year=近一年, three_year=近三年）
    - top_n: 选取市值前 N 的 ETF（默认 100）
    """
    result = get_etf_treemap(period=period, top_n=top_n)
    if not result:
        raise HTTPException(status_code=502, detail="ETF 云图数据获取失败")
    return result


@router.get("/fund-flow-history")
def get_sector_fund_flow_history(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
    limit: int = Query(30, ge=5, le=100, description="返回天数"),
    top_n: int = Query(10, ge=1, le=30, description="资金流排名前 N 的板块"),
    sector_codes: Optional[str] = Query(None, description="指定板块代码，逗号分隔，如 BK0475,BK0717"),
):
    """
    获取板块资金流历史序列（日线）

    数据来源：东方财富 push2delay（排行）+ push2his（日线资金流）
    返回：
    - dates: 日期数组
    - sectors: 各板块资金流序列（主力净流入，单位亿，保留2位小数）
    """
    specified_codes = [code.strip() for code in sector_codes.split(",") if code.strip()] if sector_codes else None
    try:
        result = _prefer_stocksdk_then_fallback(
            lambda: get_sector_fund_flow_history_data_from_stocksdk(
                sector_type=sector_type,
                limit=limit,
                top_n=top_n,
                sector_codes=specified_codes,
            ),
            lambda: get_sector_fund_flow_history_data_from_eastmoney(
                sector_type=sector_type,
                limit=limit,
                top_n=top_n,
                sector_codes=specified_codes,
            ),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="指定的板块代码未找到") from exc
    if not result:
        raise HTTPException(status_code=502, detail="板块资金流排行数据获取失败")
    return result


@router.get("/fund-flow-sectors")
def get_sector_fund_flow_sector_list(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
):
    """
    获取板块资金流可选板块列表（用于前端多选下拉框）

    返回所有行业/概念板块的代码和名称，按当日主力净流入降序排列。
    """
    all_sectors = _prefer_stocksdk_then_fallback(
        lambda: fetch_sector_fund_flow_rank_from_stocksdk(sector_type, 200),
        lambda: fetch_sector_fund_flow_rank_from_eastmoney(sector_type, 200),
    )
    if not all_sectors:
        raise HTTPException(status_code=502, detail="板块列表获取失败")
    return {
        "sectors": [{"code": sector["code"], "name": sector["name"]} for sector in all_sectors],
    }


@router.get("/board-list")
def get_board_list(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
):
    """
    获取板块卡片列表数据

    返回行业或概念板块的完整信息，包括：
    - 排名、代码、名称
    - 涨跌幅、总市值（亿）、换手率（%)
    - 上涨家数、下跌家数

    注意：领涨股票信息需要额外调用成分股接口，本接口暂不包含。
    """
    boards = _prefer_loader_chain(
        lambda: get_cached_board_list_from_stocksdk(sector_type),
        lambda: get_cached_board_list_from_eastmoney(sector_type),
        lambda: get_board_card_list_from_shidaotec(sector_type),
    )
    if not boards:
        raise HTTPException(status_code=502, detail="板块列表获取失败")
    return {
        "sectorType": sector_type,
        "total": len(boards),
        "boards": boards,
    }


@router.get("/concept-map")
def get_concept_cloud_map(
    period: str = Query("yesterday", description="涨跌幅周期：yesterday/week/month/quarter/half_year/ytd/year/three_year"),
    top_n: int = Query(100, ge=10, le=500, description="选取市值前 N 的概念"),
):
    """
    获取概念云图数据（扁平列表，按市值排序）

    参数：
    - period: 涨跌幅周期（yesterday=昨日涨跌幅, week=近一周, month=近一月,
              quarter=近三月, half_year=近半年, ytd=今年以来, year=近一年, three_year=近三年）
    - top_n: 选取市值前 N 的概念（默认 100）
    """
    result = get_concept_treemap(period=period, top_n=top_n)
    if not result:
        raise HTTPException(status_code=502, detail="概念云图数据获取失败")
    return result
