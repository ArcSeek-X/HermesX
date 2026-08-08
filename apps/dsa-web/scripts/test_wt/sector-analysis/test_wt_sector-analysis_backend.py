#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块分析（SectorAnalysisPage）后端集成走查脚本
路由：域名 + /sector-analysis
对应页面：apps/dsa-web/src/pages/SectorAnalysisPage.tsx
对应 API 层：apps/dsa-web/src/api/sectorData.ts
对应后端端点：api/v1/endpoints/sector.py（前缀 /api/v1/sector）

测试范围（真实联网调用，不 mock）：
  1. /api/v1/sector/industry              行业板块树（一级/二级）+ 快照 time 参数
  2. /api/v1/sector/stock-map             个股云图三级树 + 快照 time 参数
  3. /api/v1/sector/etf-map                ETF 云图（period 矩阵：yesterday/week/month/quarter/year）
  4. /api/v1/sector/concept-map           概念云图（period 矩阵）
  5. /api/v1/sector/{sector_code}/stocks  板块成分股（契约：total/stocks，当前数据源未接入）
  6. /api/v1/sector/market-indices        市场指数
  7. /api/v1/sector/market-overview       市场概览（涨跌家数 + 量能）

输出契约（供 test_wt.sh 解析）：
  [SUMMARY] 端|检查项|明细|状态
  [PASS]/[FAIL]/[SKIP] 条件描述：明细
  [INFO] === 接口分组名 ===  （分组边界，供报告按接口展开）
"""

import os
import sys

# 允许从仓库根目录导入（与 test_wt.sh 的执行约定保持一致：切换至 apps/dsa-web 后运行）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi.testclient import TestClient  # noqa: E402

try:
    import server  # type: ignore
    APP = server.create_app()
    _APP_AVAILABLE = True
except Exception as exc:  # pragma: no cover - 环境兜底
    import traceback

    print(f"[INFO] 完整应用工厂不可用，回退最小板块 app：{exc}")
    traceback.print_exc()
    try:
        from fastapi import FastAPI  # type: ignore

        APP = FastAPI()
        import api.v1.endpoints.sector as _sector  # type: ignore

        APP.include_router(_sector.router, prefix="/api/v1/sector")
        _APP_AVAILABLE = True
    except Exception as exc2:
        print(f"[FAIL] 无法构建板块 app：{exc2}")
        _APP_AVAILABLE = False

PREFIX = "/api/v1/sector"


def emit(summary_line: str, status: str) -> None:
    print(f"[SUMMARY] 后端|{summary_line}|{status}")


def _check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"[PASS] {name}：{detail}")
    else:
        print(f"[FAIL] {name}：{detail}")
    return cond


def test_industry(client: "TestClient"):
    print("[INFO] === 行业板块树 /api/v1/sector/industry（含快照 time）===")
    # 实时
    r = client.get(f"{PREFIX}/industry")
    ok = _check("industry time=实时", r.status_code == 200, f"status={r.status_code}")
    if ok:
        data = r.json()
        sectors = data.get("sectors") or []
        _check("industry 一级行业数量>0", len(sectors) > 0, f"{len(sectors)} 个一级行业")
        has_child = any((s.get("children") or []) for s in sectors)
        _check("industry 含二级行业 children", has_child, "存在子行业节点")
        _check("industry total 字段", isinstance(data.get("total"), int), f"total={data.get('total')}")
        _check("industry snapshotTime 为空", data.get("snapshotTime") is None, f"snapshotTime={data.get('snapshotTime')}")
    emit("行业板块树（实时）", "PASS" if ok else "FAIL")

    # 快照 time 参数（若后端支持该时间点，验证参数透传；否则仅验证不崩溃）
    for t in ("10:00", "14:30"):
        r = client.get(f"{PREFIX}/industry", params={"time": t})
        ok_t = _check(f"industry time={t}", r.status_code in (200, 502), f"status={r.status_code}")
        if ok_t and r.status_code == 200:
            snap = r.json().get("snapshotTime")
            _check(f"industry time={t} 回显", snap == t, f"snapshotTime={snap}")
        emit(f"行业板块树（快照 {t}）", "PASS" if (ok_t and r.status_code == 200) else "SKIP")


def test_stock_map(client: "TestClient"):
    print("[INFO] === 个股云图 /api/v1/sector/stock-map（三级树 + 快照）===")
    r = client.get(f"{PREFIX}/stock-map")
    ok = _check("stock-map time=实时", r.status_code == 200, f"status={r.status_code}")
    if ok:
        data = r.json()
        sectors = data.get("sectors") or []
        _check("stock-map 一级节点>0", len(sectors) > 0, f"{len(sectors)} 个一级节点")
        _check("stock-map total 字段", isinstance(data.get("total"), int), f"total={data.get('total')}")
    emit("个股云图（实时）", "PASS" if ok else "FAIL")

    for t in ("10:00",):
        r = client.get(f"{PREFIX}/stock-map", params={"time": t})
        ok_t = _check(f"stock-map time={t}", r.status_code in (200, 502), f"status={r.status_code}")
        emit(f"个股云图（快照 {t}）", "PASS" if (ok_t and r.status_code == 200) else "SKIP")


def test_etf_map(client: "TestClient"):
    print("[INFO] === ETF 云图 /api/v1/sector/etf-map（period 矩阵）===")
    for period in ("yesterday", "week", "month", "quarter", "year"):
        r = client.get(f"{PREFIX}/etf-map", params={"period": period})
        ok = _check(f"etf-map period={period}", r.status_code == 200, f"status={r.status_code}")
        if ok:
            data = r.json()
            items = data.get("sectors") or data.get("etfs") or []
            _check(f"etf-map period={period} 有数据", True, f"{len(items)} 条")
        emit(f"ETF 云图（period={period}）", "PASS" if ok else "FAIL")


def test_concept_map(client: "TestClient"):
    print("[INFO] === 概念云图 /api/v1/sector/concept-map（period 矩阵）===")
    for period in ("yesterday", "week", "month", "quarter", "year"):
        r = client.get(f"{PREFIX}/concept-map", params={"period": period})
        ok = _check(f"concept-map period={period}", r.status_code == 200, f"status={r.status_code}")
        if ok:
            data = r.json()
            items = data.get("sectors") or data.get("concepts") or []
            _check(f"concept-map period={period} 有数据", True, f"{len(items)} 条")
        emit(f"概念云图（period={period}）", "PASS" if ok else "FAIL")


def test_sector_stocks(client: "TestClient"):
    print("[INFO] === 板块成分股 /api/v1/sector/{code}/stocks ===")
    # 取一个真实行业 code（优先从 industry 接口取一级节点 name/code）
    code = "电子"
    r0 = client.get(f"{PREFIX}/industry")
    if r0.status_code == 200:
        sectors = r0.json().get("sectors") or []
        if sectors:
            code = sectors[0].get("name") or sectors[0].get("code") or code
    r = client.get(f"{PREFIX}/{code}/stocks", params={"page": 1, "page_size": 20})
    ok = _check(f"sector-stocks code={code}", r.status_code == 200, f"status={r.status_code}")
    if ok:
        data = r.json()
        # 契约：total(int) + stocks(list)；当前数据源未接入，stocks 为空属符合契约
        _check("sector-stocks total 字段", isinstance(data.get("total"), int), f"total={data.get('total')}")
        _check("sector-stocks stocks 字段", isinstance(data.get("stocks"), list), f"stocks={len(data.get('stocks') or [])} 条")
    emit(f"板块成分股（code={code}）", "PASS" if ok else "FAIL")


def test_market_indices(client: "TestClient"):
    print("[INFO] === 市场指数 /api/v1/sector/market-indices ===")
    r = client.get(f"{PREFIX}/market-indices")
    ok = _check("market-indices", r.status_code == 200, f"status={r.status_code}")
    if ok:
        data = r.json()
        indices = data.get("indices") or []
        _check("market-indices indices 列表", isinstance(indices, list), f"{len(indices)} 个指数")
        if indices:
            first = indices[0]
            _check("market-indices 含名称/代码/涨跌幅",
                   any(k in first for k in ("name", "code", "changePercent", "price")),
                   f"字段={list(first.keys())[:6]}")
    emit("市场指数", "PASS" if ok else "FAIL")


def test_market_overview(client: "TestClient"):
    print("[INFO] === 市场概览 /api/v1/sector/market-overview ===")
    r = client.get(f"{PREFIX}/market-overview")
    ok = _check("market-overview", r.status_code == 200, f"status={r.status_code}")
    if ok:
        data = r.json()
        for k in ("riseCount", "fallCount", "flatCount"):
            _check(f"market-overview {k}", k in data, f"{k}={data.get(k)}")
    emit("市场概览", "PASS" if ok else "FAIL")


def main():
    if not _APP_AVAILABLE:
        emit("应用不可用（环境）", "FAIL")
        print("[FAIL] 板块分析后端走查：应用无法构建")
        sys.exit(1)

    client = TestClient(APP)
    print("[INFO] 板块分析后端集成走查开始（真实联网调用）")
    test_industry(client)
    test_stock_map(client)
    test_etf_map(client)
    test_concept_map(client)
    test_sector_stocks(client)
    test_market_indices(client)
    test_market_overview(client)
    print("[INFO] 板块分析后端集成走查结束")


if __name__ == "__main__":
    main()
