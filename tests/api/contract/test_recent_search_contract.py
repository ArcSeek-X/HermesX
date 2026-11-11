# -*- coding: utf-8 -*-
"""个股最近搜索的用例规则与接口契约测试。

分两层验证，互不 mock 掉被测对象：

- 用例层：用记录型仓储端口验证代码归一、默认用户、市场推断、队列上限与清空语义；
- 接口层：用最小 FastAPI app + TestClient 验证 list/record/clear 三条路由的
  snake_case 传输字段与业务校验错误的 422 映射。

仓储的真实 SQLite 行为不在本文件覆盖：本文件只锁定应用层与传输层契约。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.deps import get_recent_search_service
from api.v1.endpoints import recent_search
from api.v1.schemas.recent_search import RecentSearchItem, RecentSearchRecordCreate
from src.application.recent_search import RecentSearchService, RecentSearchValidationError
from src.application.recent_search.service import MAX_RECENT_SEARCH_RECORDS


def _record_dict(stock_code: str = "600519") -> Dict[str, Any]:
    """构造一条符合 RecentSearchItem 契约的记录字典。"""
    return {
        "id": 1,
        "user_id": "default",
        "stock_code": stock_code,
        "stock_name": "贵州茅台",
        "market": "cn",
        "create_date_time": "2026-11-11T02:13:00",
        "update_date_time": "2026-11-11T03:20:00",
    }


class _RecordingRepository:
    """记录用例调用的仓储端口假实现，用于断言应用层传给持久化的参数。"""

    def __init__(self) -> None:
        self.record_calls: List[Dict[str, Any]] = []
        self.list_calls: List[Dict[str, Any]] = []
        self.clear_calls: List[Dict[str, Any]] = []

    def record_upsert(self, **kwargs: Any) -> Dict[str, Any]:
        """记录入参并返回一条记录字典。"""
        self.record_calls.append(kwargs)
        return _record_dict(kwargs["stock_code"])

    def list_recent(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """记录入参并返回空列表。"""
        self.list_calls.append(kwargs)
        return []

    def clear_all(self, **kwargs: Any) -> None:
        """记录入参，无返回值。"""
        self.clear_calls.append(kwargs)


class _FakeRecentSearchService:
    """接口测试用的用例假实现，避免连接数据库。"""

    def list_recent(self, *, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """返回一条记录；user_id 由链路透传，本假实现不依赖它。"""
        return [_record_dict()]

    def record(self, **kwargs: Any) -> Dict[str, Any]:
        """空码按真实用例语义抛校验错误，其余返回记录。"""
        if not (kwargs.get("stock_code") or "").strip():
            raise RecentSearchValidationError("股票代码不能为空")
        return _record_dict(kwargs["stock_code"])

    def clear_all(self, *, user_id: Optional[str] = None) -> None:
        """清空操作结果由端点包装，假实现无需副作用。"""
        return None


@pytest.fixture
def recent_search_client() -> TestClient:
    """只挂载最近搜索路由并覆盖依赖注入的最小应用。"""
    app = FastAPI()
    app.include_router(recent_search.router, prefix="/api/v1/recent-search")
    app.dependency_overrides[get_recent_search_service] = lambda: _FakeRecentSearchService()
    return TestClient(app)


# ---------------------------------------------------------------------------
# 应用层用例规则
# ---------------------------------------------------------------------------

def test_record_normalizes_code_and_infers_market() -> None:
    repository = _RecordingRepository()
    service = RecentSearchService(repository=repository)

    service.record(stock_code=" 600519.SH ", stock_name=" 贵州茅台 ")

    assert repository.record_calls == [{
        "user_id": "default",
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "market": "cn",
        "max_records": MAX_RECENT_SEARCH_RECORDS,
    }]


def test_record_keeps_explicit_market_and_user() -> None:
    repository = _RecordingRepository()
    service = RecentSearchService(repository=repository)

    service.record(stock_code="AAPL", market=" us ", user_id=" alice ")

    assert repository.record_calls[0]["stock_code"] == "AAPL"
    assert repository.record_calls[0]["market"] == "us"
    assert repository.record_calls[0]["user_id"] == "alice"


@pytest.mark.parametrize("raw_code", ["", "   "])
def test_record_rejects_blank_code(raw_code: str) -> None:
    service = RecentSearchService(repository=_RecordingRepository())
    with pytest.raises(RecentSearchValidationError) as exc_info:
        service.record(stock_code=raw_code)
    assert exc_info.value.error_code == "invalid_recent_search"


def test_list_and_clear_use_default_user_and_queue_limit() -> None:
    repository = _RecordingRepository()
    service = RecentSearchService(repository=repository)

    service.list_recent()
    service.clear_all(user_id="  ")

    assert repository.list_calls == [{"user_id": "default", "limit": MAX_RECENT_SEARCH_RECORDS}]
    assert repository.clear_calls == [{"user_id": "default"}]


# ---------------------------------------------------------------------------
# Schema 契约
# ---------------------------------------------------------------------------

def test_recent_search_schema_uses_snake_case_transport_names() -> None:
    request = RecentSearchRecordCreate.model_validate(
        {"stock_code": "600519", "stock_name": "贵州茅台", "market": "cn"}
    )
    assert request.stock_code == "600519"
    assert RecentSearchItem.model_validate(_record_dict()).update_date_time == "2026-11-11T03:20:00"


def test_recent_search_schema_rejects_blank_code() -> None:
    with pytest.raises(ValidationError):
        RecentSearchRecordCreate.model_validate({"stock_code": ""})


# ---------------------------------------------------------------------------
# 路由契约
# ---------------------------------------------------------------------------

def test_list_route_returns_snake_case_items(recent_search_client: TestClient) -> None:
    resp = recent_search_client.get("/api/v1/recent-search/list")
    assert resp.status_code == 200
    assert resp.json()["items"] == [_record_dict()]


def test_record_route_returns_written_item(recent_search_client: TestClient) -> None:
    resp = recent_search_client.post(
        "/api/v1/recent-search/record",
        json={"stock_code": "600519", "stock_name": "贵州茅台", "market": "cn"},
    )
    assert resp.status_code == 200
    assert resp.json()["item"]["stock_code"] == "600519"


def test_record_route_maps_validation_error_to_422(recent_search_client: TestClient) -> None:
    resp = recent_search_client.post("/api/v1/recent-search/record", json={"stock_code": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "invalid_recent_search"


def test_clear_route_returns_success(recent_search_client: TestClient) -> None:
    resp = recent_search_client.delete("/api/v1/recent-search/clear")
    assert resp.status_code == 200
    assert resp.json() == {"success": True}
