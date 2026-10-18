# -*- coding: utf-8 -*-
"""
===================================
情绪面板接口（涨跌榜）
===================================

职责：
1. GET /api/v1/emotion/limit-up-board - 涨停榜单
   （代码 / 名称 / 现价 / 涨幅 / 涨停时间 / 连板 / 封单额 / 成交额 / 换手率 / 所属行业）

后续：跌停榜单 GET /api/v1/emotion/limit-down-board
（数据源：DataFetcherManager.get_limit_down_pool，akshare 东方财富跌停股池）

涨停榜单数据源：DataFetcherManager.get_limit_up_pool（akshare 东方财富涨停股池，多源回退）。
返回字段已按连板数降序、首次封板时间升序排序（数据源保证）。
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from data_provider.base import DataFetcherManager

logger = logging.getLogger(__name__)

router = APIRouter()

# 简单内存 TTL 缓存，避免频繁请求上游（与 data_provider/sector/* 的 60s 缓存范式一致）
_BOARD_CACHE: Dict[str, Dict[str, Any]] = {}
_BOARD_CACHE_TTL_SECONDS = 60.0


def _get_cached_limit_up_board(date: Optional[str], limit: int) -> List[Dict[str, Any]]:
    """获取涨停榜单并做 60s TTL 缓存；数据源异常降级为空列表，不拖垮接口。"""
    cache_key = f"{date or 'today'}:{limit}"
    now = time.time()
    cached = _BOARD_CACHE.get(cache_key)
    if cached and now - cached['ts'] < _BOARD_CACHE_TTL_SECONDS:
        return cached['data']
    try:
        data = DataFetcherManager().get_limit_up_pool(date=date, n=limit) or []
    except Exception as exc:  # 数据源异常不拖垮接口
        logger.warning("[Emotion] 获取涨停池失败: %s", exc)
        data = []
    _BOARD_CACHE[cache_key] = {'ts': now, 'data': data}
    return data


@router.get('/limit-up-board')
def get_limit_up_board(
    date: Optional[str] = Query(None, description='交易日 YYYYMMDD，默认当天'),
    limit: int = Query(100, ge=1, le=200, description='返回条数上限'),
):
    """涨停榜单：返回当日（或指定交易日）涨停股池明细。"""
    items = _get_cached_limit_up_board(date, limit)
    return {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'items': items,
    }
