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

取数路径（ADR-001 §5.4 调用链路）：本端点只做路由与响应组装，取数经
``src.application.market.LimitPoolService``（用例：失败降级为空榜）→
``src.infrastructure.providers.limit_pool_provider``（适配器）→ ② 层
`data_provider/limit_pool/` 的 `LimitPoolDataSourceManager`（东财股池，经 akshare
通道）。统一 `LimitPoolEntry` 契约、按连板数降序 / 首次封板时间升序排序与
60s TTL 缓存均由该 Manager 提供，端点不自建缓存。

命名说明：本端点按**能力域**（涨跌停池 = limit_pool）命名，**不绑定前端菜单分组**。
前端「情绪」菜单下的涨跌榜页面是本端点当前的消费方，菜单重组不影响本端点的命名与契约。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps import get_limit_pool_service
from src.application.market import LIMIT_DOWN, LIMIT_UP, LimitPoolService

router = APIRouter()


@router.get('/limit-up-board')
def get_limit_up_board(
    date: Optional[str] = Query(None, description='交易日 YYYYMMDD，默认当天'),
    limit: int = Query(100, ge=1, le=200, description='返回条数上限'),
    service: LimitPoolService = Depends(get_limit_pool_service),
):
    """涨停榜单：返回当日（或指定交易日）涨停股池明细。"""
    items = service.get_board(board=LIMIT_UP, date=date, limit=limit)
    return {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'items': items,
    }


@router.get('/limit-down-board')
def get_limit_down_board(
    date: Optional[str] = Query(None, description='交易日 YYYYMMDD，默认当天'),
    limit: int = Query(100, ge=1, le=200, description='返回条数上限'),
    service: LimitPoolService = Depends(get_limit_pool_service),
):
    """跌停榜单：返回当日（或指定交易日）跌停股池明细。"""
    items = service.get_board(board=LIMIT_DOWN, date=date, limit=limit)
    return {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'items': items,
    }
