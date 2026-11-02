"""技术信号扫描器（Signal Scanner）离线单元测试：不依赖真实网络数据源。

覆盖三层：
1. scanner_indicators：八个信号的判定（含数据不足 / 未命中的负向路径）
2. signal_scanner_service：请求规整、三种股票池解析、并发扫描与进度回调、协作式取消
3. 端点层契约：/api/v1/scanner 路由前缀与任务类型标记
"""
import datetime

import pytest

from src.domain.analysis import scanner_indicators as ind
from src.application.decision import signal_scanner_service as svc


# ----------------------------- 测试数据构造 -----------------------------

def _flat_bars(n: int = 40, price: float = 100.0) -> list:
    """n 根横盘 K 线（date 升序），用于构造「无交叉」基线。"""
    start = datetime.date(2026, 1, 1)
    return [
        {
            "date": (start + datetime.timedelta(days=i)).isoformat(),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 1000,
        }
        for i in range(n)
    ]


def _with_tail(bars: list, tail_price: float) -> list:
    """在序列尾部追加一根收盘价突变（跳涨 / 跳水）的 K 线。"""
    last_date = datetime.date.fromisoformat(bars[-1]["date"])
    bars = list(bars) + [
        {
            "date": (last_date + datetime.timedelta(days=1)).isoformat(),
            "open": tail_price,
            "high": tail_price,
            "low": tail_price,
            "close": tail_price,
            "volume": 1000,
        }
    ]
    return bars


def _shock_up_bars() -> list:
    """横盘后跳涨：应触发 MA 金叉 / MACD 金叉 / RSI 超买 / BOLL 突破上轨。"""
    return _with_tail(_flat_bars(40, 100.0), 200.0)


def _shock_down_bars() -> list:
    """横盘后跳水：应触发 MA 死叉 / MACD 死叉 / RSI 超卖 / BOLL 跌破下轨。"""
    return _with_tail(_flat_bars(40, 100.0), 50.0)


# ----------------------------- 指标层 -----------------------------

def test_detect_signals_insufficient_bars():
    # 少于 MIN_BARS 根时不做判定（避免用不完整数据算出伪信号）
    assert ind.detect_signals(_flat_bars(20), list(ind.SIGNAL_KEYS)) == []
    assert ind.detect_signals([], list(ind.SIGNAL_KEYS)) == []
    assert ind.detect_signals(_flat_bars(40), []) == []


def test_detect_signals_flat_no_signal():
    # 横盘序列：无任何交叉 / 穿越 / 超买超卖（close 恰在中轨，不突破上下轨）
    assert ind.detect_signals(_flat_bars(40), list(ind.SIGNAL_KEYS)) == []


def test_detect_signals_shock_up():
    matched = ind.detect_signals(_shock_up_bars(), list(ind.SIGNAL_KEYS))
    assert matched == ["ma_golden", "macd_golden", "rsi_overbought", "boll_upper"]


def test_detect_signals_shock_down():
    matched = ind.detect_signals(_shock_down_bars(), list(ind.SIGNAL_KEYS))
    assert matched == ["ma_death", "macd_death", "rsi_oversold", "boll_lower"]


def test_detect_signals_respects_requested_subset():
    # 只请求 BOLL 上轨时，不应回传其它信号
    assert ind.detect_signals(_shock_up_bars(), ["boll_upper"]) == ["boll_upper"]
    # 请求的子集与行情方向相反时不命中
    assert ind.detect_signals(_shock_up_bars(), ["ma_death", "boll_lower"]) == []


def test_detect_signals_ignores_unknown_keys():
    assert ind.detect_signals(_shock_up_bars(), ["not_a_signal"]) == []


# ----------------------------- 请求规整 -----------------------------

def test_normalize_request_fallback():
    payload = svc.normalize_request(
        {
            "pool_source": "unknown_source",
            "ranking_field": "unknown_field",
            "signals": ["not_a_signal"],
            "top_n": 9999,
        }
    )
    assert payload["pool_source"] == svc.DEFAULT_POOL_SOURCE
    assert payload["ranking_field"] == svc.DEFAULT_RANKING_FIELD
    assert payload["signals"] == list(svc.DEFAULT_SIGNALS)
    # top_n 夹到 MAX_POOL_SIZE
    assert payload["top_n"] == svc.MAX_POOL_SIZE


def test_normalize_request_watchlist_strips_exchange():
    payload = svc.normalize_request(
        {
            "pool_source": "watchlist",
            "signals": ["ma_golden"],
            "watchlist": [{"code": "600519.SH", "name": "贵州茅台"}, {"code": "", "name": "空"}],
        }
    )
    # 交易所后缀剥离 + 空代码丢弃
    assert payload["watchlist"] == [{"code": "600519", "name": "贵州茅台"}]


# ----------------------------- 股票池解析 -----------------------------

def test_resolve_watchlist_pool_dedup():
    pool = svc.resolve_stock_pool(
        {
            "pool_source": "watchlist",
            "watchlist": [
                {"code": "600519.SH", "name": "贵州茅台"},
                {"code": "600519", "name": "贵州茅台"},
                {"code": "000001.SZ", "name": "平安银行"},
            ],
        }
    )
    assert pool == [
        {"code": "600519", "name": "贵州茅台"},
        {"code": "000001", "name": "平安银行"},
    ]


def test_resolve_ranking_pool_sorted_by_amount(monkeypatch):
    import pandas as pd

    from src.application.analysis import eod_picker_service

    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行", "成交额": 1e8, "涨跌幅": 1.0, "换手率": 2.0},
            {"代码": "600001", "名称": "第二", "成交额": 5e8, "涨跌幅": 2.0, "换手率": 1.0},
            {"代码": "600002", "名称": "第三", "成交额": 3e8, "涨跌幅": 3.0, "换手率": 5.0},
        ]
    )
    monkeypatch.setattr(eod_picker_service, "get_realtime_quote_snapshot", lambda: frame)

    pool = svc.resolve_stock_pool(
        {"pool_source": "ranking", "ranking_field": "amount", "top_n": 2}
    )
    assert [item["code"] for item in pool] == ["600001", "600002"]

    # 切换排序字段：按换手率降序
    pool = svc.resolve_stock_pool(
        {"pool_source": "ranking", "ranking_field": "turnover_rate", "top_n": 1}
    )
    assert [item["code"] for item in pool] == ["600002"]


def test_resolve_limit_up_pool(monkeypatch):
    # 涨停池取数已端口化（LimitPoolProviderPort.fetch_board 返回 list[dict]），直接装配模块端口全局
    class _FakeLimitPoolProvider:
        def fetch_board(self, *, pool_type, date, limit):
            assert pool_type == "limit_up"
            return [
                {"code": "600519", "name": "贵州茅台"},
                {"code": "600519", "name": "贵州茅台"},  # 重复代码应去重
                {"code": "", "name": "空代码"},  # 空代码应丢弃
            ]

    monkeypatch.setattr(svc, "_limit_pool_provider", _FakeLimitPoolProvider())
    pool = svc.resolve_stock_pool({"pool_source": "limit_up", "top_n": 20})
    assert pool == [{"code": "600519", "name": "贵州茅台"}]


def test_resolve_limit_up_pool_source_failure_degrades(monkeypatch):
    class _BoomProvider:
        def fetch_board(self, *, pool_type, date, limit):
            raise RuntimeError("data source down")

    monkeypatch.setattr(svc, "_limit_pool_provider", _BoomProvider())
    # 数据源异常降级为空池，由上层提示，不向上抛
    assert svc.resolve_stock_pool({"pool_source": "limit_up", "top_n": 20}) == []


# ----------------------------- 扫描执行 -----------------------------

def _fake_kline_provider(bars_by_code):
    """构造 K 线取数端口替身：按代码返回 fetch_kline 结果 dict（未知代码返回空数据）。

    取数已端口化（QuoteProviderPort），用例层以 kwargs 调用、消费 dict 的 data/stock_name。
    """

    class _Provider:
        def fetch_kline(self, *, stock_code, period, limit, fqt, before_date):
            bars = bars_by_code.get(stock_code, [])
            return {
                "data": bars,
                "stock_name": bars_by_code.get(f"{stock_code}__name", ""),
            }

    return _Provider()


def test_run_scan_matches_and_reports_progress(monkeypatch):
    monkeypatch.setattr(
        svc,
        "_kline_provider",
        _fake_kline_provider({"600519": _shock_up_bars(), "000001": _flat_bars(40, 100.0)}),
    )

    progress = []
    result = svc.run_signal_scan(
        {
            "pool_source": "watchlist",
            "signals": ["ma_golden"],
            "watchlist": [
                {"code": "600519", "name": "贵州茅台"},
                {"code": "000001", "name": "平安银行"},
            ],
        },
        task_id="unit-run-1",
        update_progress=lambda p, m: progress.append((p, m)),
    )
    svc.release_run("unit-run-1")

    assert result["pool_count"] == 2
    assert result["scanned"] == 2
    assert result["match_count"] == 1
    assert result["results"][0]["code"] == "600519"
    assert result["results"][0]["signals"] == ["ma_golden"]
    assert result["cancelled"] is False
    # 进度单调推进到 100，且阶段文案带扫描计数
    assert progress[0][0] < 100
    assert progress[-1] == (100, "扫描完成，命中 1 只")


def test_run_scan_empty_pool(monkeypatch):
    monkeypatch.setattr(svc, "_kline_provider", _fake_kline_provider({}))
    result = svc.run_signal_scan(
        {"pool_source": "watchlist", "signals": ["ma_golden"], "watchlist": []},
        task_id="unit-run-empty",
    )
    svc.release_run("unit-run-empty")
    assert result["pool_count"] == 0
    assert result["match_count"] == 0
    assert result["results"] == []


def test_run_scan_single_stock_failure_does_not_break_batch(monkeypatch):
    base = {"600519": _shock_up_bars()}

    class _P:
        def fetch_kline(self, *, stock_code, period, limit, fqt, before_date):
            if stock_code == "000001":
                raise RuntimeError("kline source down")
            return {"data": base.get(stock_code, []), "stock_name": ""}

    monkeypatch.setattr(svc, "_kline_provider", _P())
    result = svc.run_signal_scan(
        {
            "pool_source": "watchlist",
            "signals": ["ma_golden"],
            "watchlist": [
                {"code": "600519", "name": "贵州茅台"},
                {"code": "000001", "name": "平安银行"},
            ],
        },
        task_id="unit-run-partial",
    )
    svc.release_run("unit-run-partial")
    # 单只取数失败不影响整体（fail-open），成功的一只仍然命中
    assert result["match_count"] == 1
    assert result["scanned"] == 2


def test_run_scan_cancelled_raises_and_keeps_partial(monkeypatch):
    monkeypatch.setattr(
        svc,
        "_kline_provider",
        _fake_kline_provider({"600519": _shock_up_bars(), "000001": _shock_up_bars()}),
    )

    svc.register_run("unit-run-cancel")
    assert svc.request_cancel("unit-run-cancel") is True

    with pytest.raises(svc.ScanCancelled):
        svc.run_signal_scan(
            {
                "pool_source": "watchlist",
                "signals": ["ma_golden"],
                "watchlist": [{"code": "600519", "name": "贵州茅台"}],
            },
            task_id="unit-run-cancel",
        )

    # 取消后保留已命中部分结果，供前端展示「已取消但仍出结果」
    partial = svc.build_partial_payload(svc.get_run_state("unit-run-cancel"))
    assert partial["cancelled"] is True
    svc.release_run("unit-run-cancel")


def test_build_cancelled_result_without_state():
    result = svc.build_cancelled_result({"pool_source": "watchlist"}, "never-registered")
    assert result["cancelled"] is True
    assert result["results"] == []


def test_request_cancel_unknown_task():
    assert svc.request_cancel("not-exist") is False


def test_get_scanner_options_contract():
    options = svc.get_scanner_options()
    assert options["pool_sources"] == list(svc.POOL_SOURCES)
    assert options["signals"] == list(ind.SIGNAL_KEYS)
    assert options["defaults"]["signals"] == list(svc.DEFAULT_SIGNALS)


# ----------------------------- 端点层契约 -----------------------------

def test_scanner_router_paths():
    from api.v1.endpoints import scanner as scanner_endpoint

    paths = {route.path for route in scanner_endpoint.router.routes}
    assert paths == {"/options", "/tasks", "/tasks/{task_id}", "/tasks/{task_id}/cancel"}
    assert scanner_endpoint.TASK_REPORT_TYPE == "signal_scanner"
