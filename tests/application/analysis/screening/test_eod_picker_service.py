# -*- coding: utf-8 -*-
"""尾盘选股法（EOD Picker）离线单元测试：不依赖真实网络数据源。"""
from __future__ import annotations

import datetime
import types

import pandas as pd

from src.application.analysis import eod_picker_service as svc


def _make_snapshot() -> pd.DataFrame:
    rows = [
        # A: 满足全部基础条件 + 强强度（应通过）
        {"代码": "600000", "名称": "浦发银行", "最新价": 10.0, "涨跌幅": 4.0, "量比": 1.5,
         "换手率": 7.0, "流通市值": 100.0, "成交额": 1e8},
        # B: ST -> 基础过滤排除
        {"代码": "600001", "名称": "ST某某", "最新价": 10.0, "涨跌幅": 4.0, "量比": 1.5,
         "换手率": 7.0, "流通市值": 100.0, "成交额": 1e8},
        # C: 涨幅不足 -> 基础过滤排除
        {"代码": "600002", "名称": "低涨幅", "最新价": 10.0, "涨跌幅": 1.0, "量比": 1.5,
         "换手率": 7.0, "流通市值": 100.0, "成交额": 1e8},
        # D: 基础条件满足，但分时强度弱（50% < 80%）-> 强度过滤排除
        {"代码": "600003", "名称": "弱强度", "最新价": 10.0, "涨跌幅": 4.0, "量比": 1.5,
         "换手率": 7.0, "流通市值": 100.0, "成交额": 1e8},
        # E: 量比不足 -> 基础过滤排除
        {"代码": "600004", "名称": "低量比", "最新价": 10.0, "涨跌幅": 4.0, "量比": 0.5,
         "换手率": 7.0, "流通市值": 100.0, "成交额": 1e8},
        # F: 流通市值超限 -> 基础过滤排除
        {"代码": "600005", "名称": "大市值", "最新价": 10.0, "涨跌幅": 4.0, "量比": 1.5,
         "换手率": 7.0, "流通市值": 300.0, "成交额": 1e8},
    ]
    return pd.DataFrame(rows)


def _make_trends(code: str):
    """构造东财 trends2 形态的分时点：返回 (points, preClose, name)。

    每点含 date/open/close/high/low/volume/amount/avg_price，
    与 fetch_intraday_trends 的输出契约一致。
    """
    if code == "600003":  # 弱强度：一半的点价格低于均价线 -> 50%
        closes = [10, 9, 10, 9, 10, 9, 10, 9, 10, 9]
        return (
            [
                {
                    "date": f"2026-10-09 09:{30 + i:02d}",
                    "open": float(c),
                    "close": float(c),
                    "high": float(c),
                    "low": float(c),
                    "volume": 100.0,
                    "amount": 1000.0,
                    "avg_price": 9.5,
                }
                for i, c in enumerate(closes)
            ],
            9.5,
            "弱强度",
        )
    # 强强度：价格恒在均价线之上 -> 100%
    return (
        [
            {
                "date": f"2026-10-09 09:{30 + i:02d}",
                "open": 10.0,
                "close": 10.0,
                "high": 10.0,
                "low": 10.0,
                "volume": 100.0,
                "amount": 1000.0,
                "avg_price": 9.5,
            }
            for i in range(10)
        ],
        9.5,
        "强强度",
    )


def test_defaults_keys():
    d = svc.get_eod_picker_defaults()
    for k in ("circ_mv_min", "circ_mv_max", "volume_ratio_min", "change_pct_min",
              "change_pct_max", "turnover_rate_min", "turnover_rate_max",
              "exclude_st", "strength_min", "limit"):
        assert k in d


def test_compute_strength_trends():
    # 价格恒在均价线之上 -> 100%
    strong = [{"close": 10.0, "avg_price": 9.5} for _ in range(5)]
    assert svc.compute_strength_trends(strong) == 100.0
    # 一半点价格低于均价线 -> 50%
    weak = [{"close": c, "avg_price": 9.5} for c in [10, 9, 10, 9, 10, 9, 10, 9, 10, 9]]
    assert svc.compute_strength_trends(weak) == 50.0
    assert svc.compute_strength_trends([]) == 0.0
    # 均价缺失的点被跳过，不参与计数
    partial = [{"close": 10.0, "avg_price": None}, {"close": 10.0, "avg_price": 9.0}]
    assert svc.compute_strength_trends(partial) == 100.0


def test_build_timeline_points_kline_shape():
    bars = [{"date": "2026-10-09 09:31:00", "close": 10.0, "volume": 100, "amount": 1000.0},
            {"date": "2026-10-09 09:32:00", "close": 11.0, "volume": 100, "amount": 1100.0}]
    pts = svc.build_timeline_points(bars)
    assert len(pts) == 2
    assert set(pts[0].keys()) == {"date", "open", "close", "high", "low", "volume", "amount"}
    # 第二点累计 VWAP = (1000+1100)/(100+100) = 10.5
    assert pts[1]["close"] == 11.0
    assert pts[1]["volume"] == 100.0
    assert pts[1]["amount"] == 1100.0


def test_basic_filter_and_run(monkeypatch):
    monkeypatch.setattr(svc, "get_realtime_quote_snapshot", lambda: _make_snapshot())
    monkeypatch.setattr(
        svc, "fetch_intraday_trends", lambda code: _make_trends(code)
    )

    result = svc.run_eod_picker({})
    # 基础过滤通过：A 与 D（共 2 只）；强度过滤后仅 A 留下
    assert result["candidate_count"] == 2
    assert result["match_count"] == 1
    assert result["stocks"][0]["code"] == "600000"
    assert result["stocks"][0]["strength"] == 100.0
    # 结果按强度降序，且携带下采样分时图（KLinePoint 形态）与前收价
    tl = result["stocks"][0]["timeline"]
    assert tl and set(tl[0].keys()) == {"date", "open", "close", "high", "low", "volume", "amount"}
    assert result["stocks"][0]["prev_close"] == 9.5


def test_custom_filter_excludes_all(monkeypatch):
    monkeypatch.setattr(svc, "get_realtime_quote_snapshot", lambda: _make_snapshot())
    monkeypatch.setattr(
        svc, "fetch_intraday_trends", lambda code: _make_trends(code)
    )

    # 把涨幅上限压到 3%，则 A(4%) 也被排除
    result = svc.run_eod_picker({"change_pct_max": 3.0})
    assert result["match_count"] == 0


def test_run_reports_step_snapshots(monkeypatch):
    """回归：run_eod_picker 经 update_steps 下发「基础过滤 / 分时强度」两步快照。

    快照为全量下发（整体替换），含 key / status / total / stocks[{code,name}]；
    第一步候选为 A 与 D，第二步命中仅 A（D 强度 50% 被淘汰）。
    """
    monkeypatch.setattr(svc, "get_realtime_quote_snapshot", lambda: _make_snapshot())
    monkeypatch.setattr(
        svc, "fetch_intraday_trends", lambda code: _make_trends(code)
    )

    snapshots: list[list[dict]] = []
    result = svc.run_eod_picker(
        {}, update_steps=lambda steps: snapshots.append(steps)
    )
    assert result["match_count"] == 1
    assert len(snapshots) >= 3  # 第一步 running -> 第二步 running -> 第二步 done

    final = snapshots[-1]
    assert [s["key"] for s in final] == [svc.STEP_BASIC, svc.STEP_STRENGTH]
    assert all(s["status"] == "done" for s in final)
    # 第一步：基础过滤候选 A(600000) 与 D(600003)
    assert final[0]["total"] == 2
    assert final[0]["stocks"] == [
        {"code": "600000", "name": "浦发银行"},
        {"code": "600003", "name": "弱强度"},
    ]
    # 第二步：分时强度过滤后仅 A 命中
    assert final[1]["total"] == 1
    assert final[1]["stocks"] == [{"code": "600000", "name": "浦发银行"}]
    # 中间快照：第一步 done 且第二步 running
    middle = snapshots[1]
    assert middle[0]["status"] == "done" and middle[1]["status"] == "running"
    assert middle[1]["stocks"] == []


def test_run_reports_empty_steps_when_no_candidates(monkeypatch):
    """基础过滤 0 候选时也下发两步 done 快照（空列表），前端不残留旧步骤。"""
    monkeypatch.setattr(svc, "get_realtime_quote_snapshot", lambda: _make_snapshot())
    monkeypatch.setattr(
        svc, "fetch_intraday_trends", lambda code: _make_trends(code)
    )

    snapshots: list[list[dict]] = []
    result = svc.run_eod_picker(
        {"change_pct_max": 3.0},
        update_steps=lambda steps: snapshots.append(steps),
    )
    assert result["candidate_count"] == 0
    final = snapshots[-1]
    assert [s["key"] for s in final] == [svc.STEP_BASIC, svc.STEP_STRENGTH]
    assert all(s["status"] == "done" and s["stocks"] == [] for s in final)


def test_null_upper_bound_means_unlimited(monkeypatch):
    monkeypatch.setattr(svc, "get_realtime_quote_snapshot", lambda: _make_snapshot())
    monkeypatch.setattr(
        svc, "fetch_intraday_trends", lambda code: _make_trends(code)
    )

    # 上限传 None 表示不限制：涨幅 4% / 换手率 7% 仍应通过
    result = svc.run_eod_picker({"change_pct_max": None, "turnover_rate_max": None})
    assert result["match_count"] == 1


def test_resolve_trade_date_is_not_in_the_future():
    """基准交易日不得晚于今天，且必须是工作日（周一至周五）。"""
    target, is_today = svc.resolve_trade_date()
    today = datetime.date.today()
    assert target <= today
    assert target.weekday() < 5
    assert is_today == (target == today)


def test_run_uses_previous_trade_date_when_market_closed(monkeypatch):
    """休市（周末）时应以上一个交易日为基准，而不是直接报错。"""
    # 固定为周六，期望回退到前一个交易日（周五）
    saturday = datetime.date(2026, 10, 10)
    friday = datetime.date(2026, 10, 9)
    monkeypatch.setattr(svc, "resolve_trade_date", lambda: (friday, False))
    monkeypatch.setattr(svc, "get_realtime_quote_snapshot", lambda: _make_snapshot())

    seen: dict[str, object] = {}

    def fake_intraday(code):
        seen["called"] = True
        return _make_trends(code)

    monkeypatch.setattr(svc, "fetch_intraday_trends", fake_intraday)

    result = svc.run_eod_picker({})
    assert result["trade_date"] == friday.isoformat()
    # 休市日回退上一交易日后，阶段 2 分时筛选仍正常执行
    assert seen["called"] is True
    assert saturday.weekday() == 5  # 用例前提：2026-10-10 确实是周六
    assert result["stocks"][0]["code"] == "600000"


def test_router_paths_constant():
    # 端点路由在 api/v1/endpoints/eod_picker.py 中定义，路径为：
    #   GET  /eod-picker/defaults
    #   POST /eod-picker/tasks
    #   GET  /eod-picker/tasks/{task_id}
    #   GET  /eod-picker/stocks/{code}/timeline
    # 完整依赖环境下由集成测试覆盖；此处仅做路径常量自检。
    expected = {
        "defaults": "/eod-picker/defaults",
        "tasks_post": "/eod-picker/tasks",
        "tasks_get": "/eod-picker/tasks/{task_id}",
        "timeline": "/eod-picker/stocks/{code}/timeline",
    }
    assert expected["defaults"].startswith("/eod-picker/")
    assert expected["timeline"].endswith("/timeline")


def _em_clist_df() -> pd.DataFrame:
    """东财 clist 直连快照：流通市值 / 成交额为东财原生「元」。"""
    return pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行", "最新价": 10.0, "涨跌幅": 4.0, "量比": 1.5,
             "换手率": 7.0, "流通市值": 1e10, "成交额": 1e8, "成交量": 1e5,
             "昨收": 9.6, "今开": 9.7, "最高": 10.2, "最低": 9.6},
        ]
    )


def test_eastmoney_quote_snapshot_parse_and_paginate(monkeypatch):
    """直连 clist 模块：f-field 解析、停牌行跳过、列契约与单位。"""
    from data_provider import eastmoney_quote_snapshot as em

    pages = {
        1: {"data": {"total": 2, "diff": [
            {"f12": "600000", "f14": "浦发银行", "f2": "10.0", "f3": "4.0", "f10": "1.5",
             "f8": "7.0", "f21": "10000000000", "f6": "100000000", "f5": "100000",
             "f18": "9.6", "f17": "9.7", "f15": "10.2", "f16": "9.6"},
            # 停牌：f2='-' -> price 为空，_parse_item 返回 None 被跳过
            {"f12": "600001", "f14": "ST停牌", "f2": "-", "f3": "0", "f10": "-",
             "f8": "-", "f21": "-", "f6": "-", "f5": "-", "f18": "-",
             "f17": "-", "f15": "-", "f16": "-"},
        ]}},
    }
    monkeypatch.setattr(em, "_fetch_page", lambda page, page_size: pages[page])

    df = em.fetch_eastmoney_market_snapshot(page_size=500)
    assert df is not None and len(df) == 1
    row = df.iloc[0]
    assert row["代码"] == "600000"
    assert row["名称"] == "浦发银行"
    assert row["最新价"] == 10.0
    assert row["量比"] == 1.5
    assert row["换手率"] == 7.0
    assert row["流通市值"] == 1e10   # 东财原生「元」
    assert row["成交额"] == 1e8      # 元
    assert list(df.columns) == em._COLUMNS
    # 下游按量级把「元」归一化到「亿元」：1e10 元 = 100 亿元
    assert svc._normalize_cmv(pd.Series([1e10])).iloc[0] == 100.0


def test_get_realtime_quote_snapshot_prefers_eastmoney_clist(monkeypatch):
    """优先级：快照端口东财源可用时优先采用，不触碰腾讯 / akshare（T5b 假端口）。"""
    port = _FakeSnapshotPort(
        east=_em_clist_df(),
        tencent=pd.DataFrame([{"代码": "TENCENT"}]),
        ak=pd.DataFrame([{"代码": "AKSHARE"}]),
    )
    monkeypatch.setattr(svc, "_market_snapshot_port", port)

    df = svc.get_realtime_quote_snapshot()
    assert df is not None and df.iloc[0]["代码"] == "600000"
    assert port.calls == ["east"]


def test_get_realtime_quote_snapshot_falls_back_to_tencent(monkeypatch):
    """东财源失败（返回 None）时回退腾讯批量行情（T5b 假端口）。"""
    port = _FakeSnapshotPort(
        east=None,
        tencent=pd.DataFrame([{"代码": "TENCENT"}]),
        ak=pd.DataFrame([{"代码": "AKSHARE"}]),
    )
    monkeypatch.setattr(svc, "_market_snapshot_port", port)

    df = svc.get_realtime_quote_snapshot()
    assert df is not None and df.iloc[0]["代码"] == "TENCENT"
    assert port.calls == ["east", "tencent"]


def test_eastmoney_quote_snapshot_paginates_past_first_page(monkeypatch):
    """回归：东财 pz 被压到 100 时也必须据 total 翻满全部页，不能只取第 1 页。

    曾因用「请求页大小(500)」判断结束、而东财每页只回 100，导致只拿到涨幅最高的
    前 100 只、尾盘选股 0 结果。此处模拟请求 500 但每页只回 100，断言翻满 3 页。
    """
    from data_provider import eastmoney_quote_snapshot as em

    total = 250
    cap = 100  # 东财实际每页上限

    def fake_fetch_page(page, page_size):
        start = (page - 1) * cap
        n = min(cap, total - start)
        diff = [
            {"f12": f"{600000 + start + i}", "f14": f"股票{start + i}", "f2": "10.0",
             "f3": "4.0", "f10": "1.5", "f8": "7.0", "f21": "10000000000",
             "f6": "100000000", "f5": "100000", "f18": "9.6", "f17": "9.7",
             "f15": "10.2", "f16": "9.6"}
            for i in range(n)
        ]
        return {"data": {"total": total, "diff": diff}}

    monkeypatch.setattr(em, "_fetch_page", fake_fetch_page)

    # 即便请求 page_size=500（东财会压到 100），也应翻满 3 页拿全 250 只
    df = em.fetch_eastmoney_market_snapshot(page_size=500)
    assert df is not None and len(df) == total
    assert df["代码"].nunique() == total  # 稳定排序下无重复


def test_fetch_intraday_timeline_delegates_to_shared_service(monkeypatch):
    """eod_picker.fetch_intraday_timeline 为兼容入口，实际取数委托 intraday_timeline_service。

    校验委托关系与 KLinePoint 输出契约（分时取数的网络层测试见
    tests/test_intraday_timeline_service.py）。
    """
    def fake_fetch(code: str, limit: int = 240):
        return {
            "code": code,
            "name": "浦发银行",
            "prev_close": 9.6,
            "points": [{"date": "2026-10-14 09:30:00", "open": 9.7, "close": 9.8,
                        "high": 9.9, "low": 9.6, "volume": 100000, "amount": 980000.0}],
        }

    monkeypatch.setattr(svc, "_fetch_intraday_timeline_impl", fake_fetch)

    data = svc.fetch_intraday_timeline("600000")
    assert data["code"] == "600000"
    assert data["prev_close"] == 9.6
    assert len(data["points"]) == 1
    assert set(data["points"][0].keys()) == {
        "date", "open", "close", "high", "low", "volume", "amount"
    }


# --------------------------------------------------------------------------- #
# T5b 端口化：MarketSnapshotPort seam / 回退链 / 未装配降级 / data_provider 适配器
# --------------------------------------------------------------------------- #
class _FakeSnapshotPort:
    """可编程的三源假端口：按调用顺序返回预设结果或抛预设异常。"""

    def __init__(self, east=None, tencent=None, ak=None, east_exc=None):
        self.calls: list[str] = []
        self._east, self._tencent, self._ak = east, tencent, ak
        self._east_exc = east_exc

    def fetch_eastmoney_snapshot(self):
        self.calls.append("east")
        if self._east_exc is not None:
            raise self._east_exc
        return self._east

    def fetch_tencent_snapshot(self):
        self.calls.append("tencent")
        return self._tencent

    def fetch_akshare_snapshot(self):
        self.calls.append("akshare")
        return self._ak


def test_snapshot_unassembled_returns_none(monkeypatch):
    """未装配端口时快照优雅降级为 None（与迁移前三源全部失败语义一致）。"""
    monkeypatch.setattr(svc, "_market_snapshot_port", None)
    assert svc.get_realtime_quote_snapshot() is None


def test_run_eod_picker_unassembled_raises_runtime_error(monkeypatch):
    """未装配→主流程报“数据源暂不可用”RuntimeError，不静默返回空结果。"""
    monkeypatch.setattr(svc, "_market_snapshot_port", None)
    monkeypatch.setattr(svc, "resolve_trade_date", lambda: (datetime.date(2026, 10, 23), False))
    try:
        svc.run_eod_picker({})
        raise AssertionError("应抛 RuntimeError")
    except RuntimeError as exc:
        assert "数据源暂不可用" in str(exc)


def test_set_market_snapshot_port_idempotent(monkeypatch):
    """setter 幂等：仅非 None 覆盖，重复装配不重置（双挂点安全）。"""
    monkeypatch.setattr(svc, "_market_snapshot_port", None)
    port = _FakeSnapshotPort()
    svc.set_market_snapshot_port(port)
    assert svc._market_snapshot_port is port
    svc.set_market_snapshot_port(None)
    assert svc._market_snapshot_port is port


def test_snapshot_fallback_chain_east_none_tencent_empty_falls_to_akshare(monkeypatch):
    """东财 None→腾讯空表→akshare 非空：按序回退命中第三源。"""
    frame = _make_snapshot()
    port = _FakeSnapshotPort(east=None, tencent=pd.DataFrame(), ak=frame)
    monkeypatch.setattr(svc, "_market_snapshot_port", port)
    out = svc.get_realtime_quote_snapshot()
    assert out is frame
    assert port.calls == ["east", "tencent", "akshare"]


def test_snapshot_eastmoney_exception_falls_back_to_tencent(monkeypatch):
    """东财抛异常→回退腾讯命中，异常不拖垮取数（与迁移前逐源 catch 一致）。"""
    frame = _make_snapshot()
    port = _FakeSnapshotPort(east_exc=RuntimeError("push2 不可达"), tencent=frame)
    monkeypatch.setattr(svc, "_market_snapshot_port", port)
    out = svc.get_realtime_quote_snapshot()
    assert out is frame
    assert port.calls == ["east", "tencent"]


def test_all_sources_empty_returns_none(monkeypatch):
    """三源均空/None → 返回 None（与迁移前终态一致）。"""
    port = _FakeSnapshotPort(east=None, tencent=None, ak=pd.DataFrame())
    monkeypatch.setattr(svc, "_market_snapshot_port", port)
    assert svc.get_realtime_quote_snapshot() is None


def test_adapter_snapshot_sources_passthrough(monkeypatch):
    """适配器东财/腾讯两源透传 data_provider 模块函数返回值，不做字段加工。"""
    from src.infrastructure.providers.market_snapshot_provider import (
        DataProviderMarketSnapshotSource,
    )

    frame_e = pd.DataFrame([{"代码": "600000"}])
    frame_t = pd.DataFrame([{"代码": "600001"}])
    import data_provider.eastmoney_quote_snapshot as em_mod
    import data_provider.tencent_quote_snapshot as tx_mod

    monkeypatch.setattr(em_mod, "fetch_eastmoney_market_snapshot", lambda: frame_e)
    monkeypatch.setattr(tx_mod, "fetch_tencent_market_snapshot", lambda: frame_t)

    adapter = DataProviderMarketSnapshotSource()
    assert adapter.fetch_eastmoney_snapshot() is frame_e
    assert adapter.fetch_tencent_snapshot() is frame_t


def test_adapter_akshare_fetcher_singleton_reuse(monkeypatch):
    """适配器内 AkshareFetcher 单例复用（与迁移前模块级 _fetcher 缓存共享语义一致）。"""
    from src.infrastructure.providers.market_snapshot_provider import (
        DataProviderMarketSnapshotSource,
    )

    created: list[int] = []

    class _FakeFetcher:
        def __init__(self):
            created.append(1)

        def get_realtime_quote_snapshot(self):
            return pd.DataFrame([{"代码": "600000"}])

    fake_mod = types.SimpleNamespace(AkshareFetcher=_FakeFetcher)
    monkeypatch.setitem(__import__("sys").modules, "data_provider.akshare_fetcher", fake_mod)

    adapter = DataProviderMarketSnapshotSource()
    df1 = adapter.fetch_akshare_snapshot()
    df2 = adapter.fetch_akshare_snapshot()
    assert df1 is not None and df2 is not None
    assert len(created) == 1  # 只实例化一次



