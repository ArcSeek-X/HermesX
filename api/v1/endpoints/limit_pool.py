# -*- coding: utf-8 -*-
"""
===================================
涨跌停榜单接口（limit_pool）
===================================

职责：
1. GET /api/v1/limit-pool/limit-up-board - 涨停榜单
   （代码 / 名称 / 现价 / 涨幅 / 涨停时间 / 连板 / 封单额 / 成交额 / 换手率 / 所属行业）

2. GET /api/v1/limit-pool/limit-down-board - 跌停榜单
   （字段与涨停榜单完全一致，仅「涨停时间」为「跌停时间」；
   连板数表示连续跌停次数，跌停池无首次封板时间，以最后封板时间充当）

取数路径（ADR-001 §5.4 调用链路）：本端点只做路由 + 编排，取数一律经 ② 层
`data_provider/limit_pool/` 的 `LimitPoolDataSourceManager`（东财股池，经 akshare 通道），
返回统一 `LimitPoolEntry` 契约并按连板数降序、首次封板时间升序排序（数据源保证）。
60s TTL 缓存由该 Manager 统一提供，端点不自建缓存。

命名说明：本端点按**能力域**（涨跌停池 = limit_pool）命名，**不绑定前端菜单分组**。
前端「情绪」菜单下的涨跌榜页面是本端点当前的消费方，菜单重组不影响本端点的命名与契约。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from data_provider.limit_pool import LIMIT_DOWN, LIMIT_UP, get_limit_pool

logger = logging.getLogger(__name__)

router = APIRouter()


def _load_board(pool_type: str, date: Optional[str], limit: int) -> List[Dict[str, Any]]:
    """取榜单并转为 API 响应 dict；数据源异常降级为空列表，不拖垮接口。

    缓存与选源 / 回退由 ② 层 Manager 负责：仅在取数成功时写入缓存，
    失败结果不会被缓存（避免一次上游抖动冻结整段 TTL）。
    """
    try:
        result = get_limit_pool(pool_type=pool_type, date=date, n=limit)
    except Exception as exc:  # 数据源异常不拖垮接口
        logger.warning("[LimitPool] 获取榜单失败: pool_type=%s error=%s", pool_type, exc)
        return []
    return [entry.to_dict() for entry in result.entries]


@router.get('/limit-up-board')
def get_limit_up_board(
    date: Optional[str] = Query(None, description='交易日 YYYYMMDD，默认当天'),
    limit: int = Query(100, ge=1, le=200, description='返回条数上限'),
):
    """涨停榜单：返回当日（或指定交易日）涨停股池明细。"""
    items = _load_board(LIMIT_UP, date, limit)
    return {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'items': items,
    }


@router.get('/limit-down-board')
def get_limit_down_board(
    date: Optional[str] = Query(None, description='交易日 YYYYMMDD，默认当天'),
    limit: int = Query(100, ge=1, le=200, description='返回条数上限'),
):
    """跌停榜单：返回当日（或指定交易日）跌停股池明细。"""
    items = _load_board(LIMIT_DOWN, date, limit)
    return {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'items': items,
    }
