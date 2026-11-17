"""Tests for decision signal identity."""

from tests.api.decision_signals._decision_signal_api_support import (
    DecisionSignalRecord,
    DecisionSignalService,
    PortfolioAccount,
    PortfolioPosition,
    _payload,
    _temporary_tz,
    client_and_db,
    datetime,
    patch,
    timedelta,
    timezone,
)


def test_create_sanitizes_public_short_fields_and_filters_by_sanitized_trigger_source(client_and_db) -> None:
    client, db = client_and_db
    raw_trigger_source = "Bearer abc+/def=="
    created_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3061,
            trace_id="trace-public-sanitized",
            stock_name="secret=plain-secret",
            source_agent="https://hooks.example.com/send",
            trigger_source=raw_trigger_source,
            action_label="token=abc",
        ),
    )
    assert created_resp.status_code == 200, created_resp.text
    item = created_resp.json()["item"]
    assert item["stock_name"] == "secret=[REDACTED]"
    assert item["source_agent"] == "[REDACTED_URL]"
    assert item["trigger_source"] == "Bearer [REDACTED]"
    assert item["action_label"] == "token=[REDACTED]"
    assert "plain-secret" not in str(item)
    assert "abc+/def==" not in str(item)
    assert "hooks.example.com" not in str(item)

    list_resp = client.get(
        "/api/v1/decision-signals",
        params={"trigger_source": raw_trigger_source},
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["items"][0]["id"] == item["id"]

    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter_by(id=item["id"]).one()
        stored_blob = " ".join(
            str(value or "")
            for value in (
                row.stock_name,
                row.source_agent,
                row.trigger_source,
                row.action_label,
            )
        )
    assert "plain-secret" not in stored_blob
    assert "abc+/def==" not in stored_blob
    assert "hooks.example.com" not in stored_blob


def test_aware_datetime_range_filters_use_utc_naive_contract(client_and_db) -> None:
    client, _db = client_and_db

    with _temporary_tz("Asia/Shanghai"):
        created_resp = client.post(
            "/api/v1/decision-signals",
            json=_payload(source_report_id=3105, trace_id="trace-3105"),
        )
        assert created_resp.status_code == 200, created_resp.text
        signal_id = created_resp.json()["item"]["id"]

        list_resp = client.get(
            "/api/v1/decision-signals",
            params={
                "created_from": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                "created_to": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
            },
        )
        assert list_resp.status_code == 200, list_resp.text
        assert list_resp.json()["total"] == 1
        assert list_resp.json()["items"][0]["id"] == signal_id


def test_holding_only_uses_cached_positions_and_stock_code_variants(client_and_db) -> None:
    client, db = client_and_db
    stock_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3201, trace_id="trace-3201", stock_code="600519.SH"),
    )
    assert stock_resp.status_code == 200, stock_resp.text
    other_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3202,
            trace_id="trace-3202",
            stock_code="AAPL",
            stock_name="Apple",
            market="us",
        ),
    )
    assert other_resp.status_code == 200, other_resp.text
    inactive_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3203,
            trace_id="trace-3203",
            stock_code="TSLA",
            stock_name="Tesla",
            market="us",
        ),
    )
    assert inactive_resp.status_code == 200, inactive_resp.text
    zero_only_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3204,
            trace_id="trace-3204",
            stock_code="MSFT",
            stock_name="Microsoft",
            market="us",
        ),
    )
    assert zero_only_resp.status_code == 200, zero_only_resp.text
    hk_same_symbol_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3205,
            trace_id="trace-3205",
            stock_code="AAPL",
            stock_name="Apple HK synthetic",
            market="hk",
        ),
    )
    assert hk_same_symbol_resp.status_code == 200, hk_same_symbol_resp.text

    with db.session_scope() as session:
        account = PortfolioAccount(
            name="Test account",
            market="cn",
            base_currency="CNY",
            is_active=True,
        )
        session.add(account)
        session.flush()
        account_id = account.id
        session.add(
            PortfolioPosition(
                account_id=account_id,
                cost_method="fifo",
                symbol="SH600519",
                market="cn",
                currency="CNY",
                quantity=100,
                avg_cost=1600,
                total_cost=160000,
            )
        )
        session.add(
            PortfolioPosition(
                account_id=account_id,
                cost_method="fifo",
                symbol="AAPL",
                market="us",
                currency="USD",
                quantity=0,
            )
        )
        session.add(
            PortfolioPosition(
                account_id=account_id,
                cost_method="fifo",
                symbol="MSFT",
                market="us",
                currency="USD",
                quantity=0,
            )
        )
        session.add(
            PortfolioPosition(
                account_id=account_id,
                cost_method="avg",
                symbol="AAPL",
                market="us",
                currency="USD",
                quantity=5,
                avg_cost=180,
                total_cost=900,
            )
        )
        inactive_account = PortfolioAccount(
            name="Inactive account",
            market="us",
            base_currency="USD",
            is_active=False,
        )
        session.add(inactive_account)
        session.flush()
        inactive_account_id = inactive_account.id
        session.add(
            PortfolioPosition(
                account_id=inactive_account_id,
                cost_method="fifo",
                symbol="TSLA",
                market="us",
                currency="USD",
                quantity=3,
                avg_cost=200,
                total_cost=600,
            )
        )

    with patch(
        "src.application.portfolio.portfolio_service.PortfolioService.get_portfolio_snapshot",
        side_effect=AssertionError("holding_only must not replay portfolio snapshots"),
    ):
        holding_resp = client.get(
            "/api/v1/decision-signals",
            params={"holding_only": "true", "account_id": account_id},
        )

    assert holding_resp.status_code == 200, holding_resp.text
    payload = holding_resp.json()
    assert payload["total"] == 2
    assert {(item["market"], item["stock_code"]) for item in payload["items"]} == {
        ("cn", "600519"),
        ("us", "AAPL"),
    }

    with patch(
        "src.application.portfolio.portfolio_service.PortfolioService.get_portfolio_snapshot",
        side_effect=AssertionError("holding_only must not replay portfolio snapshots"),
    ):
        all_active_resp = client.get(
            "/api/v1/decision-signals",
            params={"holding_only": "true"},
        )

    assert all_active_resp.status_code == 200, all_active_resp.text
    all_active_payload = all_active_resp.json()
    assert all_active_payload["total"] == 2
    assert {(item["market"], item["stock_code"]) for item in all_active_payload["items"]} == {
        ("cn", "600519"),
        ("us", "AAPL"),
    }

    with patch(
        "src.application.portfolio.portfolio_service.PortfolioService.get_portfolio_snapshot",
        side_effect=AssertionError("holding_only must not replay portfolio snapshots"),
    ):
        inactive_holding_resp = client.get(
            "/api/v1/decision-signals",
            params={"holding_only": "true", "account_id": inactive_account_id},
        )
    assert inactive_holding_resp.status_code == 200, inactive_holding_resp.text
    assert inactive_holding_resp.json()["total"] == 0
    assert inactive_holding_resp.json()["items"] == []

    variant_resp = client.get("/api/v1/decision-signals", params={"stock_code": "SH600519"})
    assert variant_resp.status_code == 200, variant_resp.text
    assert variant_resp.json()["total"] == 1

    with db.session_scope() as session:
        empty_account = PortfolioAccount(name="Empty account", market="cn", base_currency="CNY")
        session.add(empty_account)
        session.flush()
        empty_account_id = empty_account.id

    empty_resp = client.get(
        "/api/v1/decision-signals",
        params={"holding_only": "true", "account_id": empty_account_id},
    )
    assert empty_resp.status_code == 200, empty_resp.text
    assert empty_resp.json()["total"] == 0
    assert empty_resp.json()["items"] == []

    empty_bad_date_resp = client.get(
        "/api/v1/decision-signals",
        params={
            "holding_only": "true",
            "account_id": empty_account_id,
            "created_from": "bad-date",
        },
    )
    assert empty_bad_date_resp.status_code == 400
    assert empty_bad_date_resp.json()["error"] == "validation_error"


def test_dedup_distinguishes_horizon_and_market_phase(client_and_db) -> None:
    client, _db = client_and_db

    first_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3401, trace_id="trace-3401", horizon="1d", market_phase="intraday"),
    )
    assert first_resp.status_code == 200, first_resp.text
    first = first_resp.json()
    assert first["created"] is True

    duplicate_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3401, trace_id="trace-3401", horizon="1d", market_phase="intraday"),
    )
    assert duplicate_resp.status_code == 200, duplicate_resp.text
    duplicate = duplicate_resp.json()
    assert duplicate["created"] is False
    assert duplicate["item"]["id"] == first["item"]["id"]

    horizon_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3401, trace_id="trace-3401", horizon="10d", market_phase="intraday"),
    )
    assert horizon_resp.status_code == 200, horizon_resp.text
    assert horizon_resp.json()["created"] is True
    assert horizon_resp.json()["item"]["id"] != first["item"]["id"]

    phase_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3401, trace_id="trace-3401", horizon="1d", market_phase="premarket"),
    )
    assert phase_resp.status_code == 200, phase_resp.text
    assert phase_resp.json()["created"] is True
    assert phase_resp.json()["item"]["id"] != first["item"]["id"]

    list_resp = client.get(
        "/api/v1/decision-signals",
        params={
            "stock_code": "600519",
            "source_type": "analysis",
            "source_report_id": 3401,
            "trace_id": "trace-3401",
            "trigger_source": "api",
        },
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["total"] == 3

    latest_resp = client.get("/api/v1/decision-signals/latest/600519", params={"limit": 3})
    assert latest_resp.status_code == 200, latest_resp.text
    assert latest_resp.json()["total"] == 3


def test_dedup_distinguishes_source_type_for_weak_report_ids(client_and_db) -> None:
    client, _db = client_and_db

    analysis_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3451,
            trace_id="trace-3451-analysis",
            source_type="analysis",
        ),
    )
    assert analysis_resp.status_code == 200, analysis_resp.text
    analysis = analysis_resp.json()
    assert analysis["created"] is True
    assert analysis["item"]["source_type"] == "analysis"

    manual_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3451,
            trace_id="trace-3451-manual",
            source_type="manual",
        ),
    )
    assert manual_resp.status_code == 200, manual_resp.text
    manual = manual_resp.json()
    assert manual["created"] is True
    assert manual["item"]["source_type"] == "manual"
    assert manual["item"]["id"] != analysis["item"]["id"]

    duplicate_manual_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3451,
            trace_id="trace-3451-manual-new",
            source_type="manual",
        ),
    )
    assert duplicate_manual_resp.status_code == 200, duplicate_manual_resp.text
    duplicate_manual = duplicate_manual_resp.json()
    assert duplicate_manual["created"] is False
    assert duplicate_manual["item"]["id"] == manual["item"]["id"]

    list_resp = client.get(
        "/api/v1/decision-signals",
        params={"stock_code": "600519", "source_report_id": 3451},
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["total"] == 2

    analysis_list_resp = client.get(
        "/api/v1/decision-signals",
        params={"stock_code": "600519", "source_report_id": 3451, "source_type": "analysis"},
    )
    assert analysis_list_resp.status_code == 200, analysis_list_resp.text
    assert analysis_list_resp.json()["total"] == 1

    manual_list_resp = client.get(
        "/api/v1/decision-signals",
        params={"stock_code": "600519", "source_report_id": 3451, "source_type": "manual"},
    )
    assert manual_list_resp.status_code == 200, manual_list_resp.text
    assert manual_list_resp.json()["total"] == 1


def test_stock_filter_codes_cover_market_optional_hk_without_widening_other_markets() -> None:
    from src.application.decision.decision_signal_service import DecisionSignalService

    cases = [
        ("00700", None, ["00700", "HK00700"]),
        ("HK00700", None, ["HK00700"]),
        ("00700.HK", None, ["HK00700"]),
        ("00700", "hk", ["HK00700"]),
        ("600519", None, ["600519"]),
        ("600519.SH", None, ["600519"]),
        ("AAPL", None, ["AAPL"]),
    ]
    for raw_code, market, expected_codes in cases:
        assert DecisionSignalService.stock_filter_codes(raw_code, market=market) == expected_codes


def test_hk_stock_identity_variants_deduplicate_and_latest_matches(client_and_db) -> None:
    client, _db = client_and_db

    first_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3501,
            trace_id="trace-3501-a",
            stock_code="00700",
            stock_name="Tencent",
            market="hk",
        ),
    )
    assert first_resp.status_code == 200, first_resp.text
    first = first_resp.json()
    assert first["created"] is True
    assert first["item"]["stock_code"] == "HK00700"

    for raw_code, trace_id in (("HK00700", "trace-3501-b"), ("00700.HK", "trace-3501-c")):
        duplicate_resp = client.post(
            "/api/v1/decision-signals",
            json=_payload(
                source_report_id=3501,
                trace_id=trace_id,
                stock_code=raw_code,
                stock_name="Tencent",
                market="hk",
            ),
        )
        assert duplicate_resp.status_code == 200, duplicate_resp.text
        duplicate = duplicate_resp.json()
        assert duplicate["created"] is False
        assert duplicate["item"]["id"] == first["item"]["id"]

    latest_resp = client.get(
        "/api/v1/decision-signals/latest/00700",
        params={"market": "hk"},
    )
    assert latest_resp.status_code == 200, latest_resp.text
    assert latest_resp.json()["total"] == 1
    assert latest_resp.json()["items"][0]["id"] == first["item"]["id"]

    latest_cases = [
        ("00700", {}),
        ("HK00700", {}),
        ("00700.HK", {}),
        ("00700", {"market": "hk"}),
    ]
    for raw_code, params in latest_cases:
        latest_resp = client.get(f"/api/v1/decision-signals/latest/{raw_code}", params=params)
        assert latest_resp.status_code == 200, latest_resp.text
        latest_payload = latest_resp.json()
        assert latest_payload["total"] == 1
        assert latest_payload["items"][0]["id"] == first["item"]["id"]

    list_cases = [
        ("00700", {}),
        ("HK00700", {}),
        ("00700.HK", {}),
        ("00700", {"market": "hk"}),
    ]
    for raw_code, params in list_cases:
        list_resp = client.get(
            "/api/v1/decision-signals",
            params={"stock_code": raw_code, **params},
        )
        assert list_resp.status_code == 200, list_resp.text
        list_payload = list_resp.json()
        assert list_payload["total"] == 1
        assert list_payload["items"][0]["id"] == first["item"]["id"]


def test_dedup_distinguishes_market_for_same_symbol(client_and_db) -> None:
    client, _db = client_and_db

    us_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3601,
            trace_id="trace-3601-us",
            stock_code="DUPL",
            stock_name="Duplicate US",
            market="us",
        ),
    )
    assert us_resp.status_code == 200, us_resp.text
    assert us_resp.json()["created"] is True

    hk_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3601,
            trace_id="trace-3601-hk",
            stock_code="DUPL",
            stock_name="Duplicate HK",
            market="hk",
        ),
    )
    assert hk_resp.status_code == 200, hk_resp.text
    assert hk_resp.json()["created"] is True
    assert hk_resp.json()["item"]["id"] != us_resp.json()["item"]["id"]


def test_list_decision_profile_filter_distinguishes_unknown_from_omitted(client_and_db) -> None:
    client, db = client_and_db

    balanced_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3611,
            trace_id="trace-profile-api-balanced",
            decision_profile="balanced",
        ),
    )
    aggressive_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3612,
            trace_id="trace-profile-api-aggressive",
            decision_profile="aggressive",
        ),
    )
    legacy_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3613,
            trace_id="trace-profile-api-legacy",
            decision_profile="balanced",
        ),
    )
    assert balanced_resp.status_code == 200, balanced_resp.text
    assert aggressive_resp.status_code == 200, aggressive_resp.text
    assert legacy_resp.status_code == 200, legacy_resp.text
    legacy_id = legacy_resp.json()["item"]["id"]
    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter_by(id=legacy_id).one()
        row.decision_profile = None

    all_resp = client.get("/api/v1/decision-signals", params={"stock_code": "600519", "status": "active"})
    unknown_resp = client.get(
        "/api/v1/decision-signals",
        params={"stock_code": "600519", "status": "active", "decision_profile": "unknown"},
    )
    aggressive_list_resp = client.get(
        "/api/v1/decision-signals",
        params={"stock_code": "600519", "status": "active", "decision_profile": "aggressive"},
    )

    assert all_resp.status_code == 200, all_resp.text
    assert unknown_resp.status_code == 200, unknown_resp.text
    assert aggressive_list_resp.status_code == 200, aggressive_list_resp.text
    assert all_resp.json()["total"] == 3
    assert [item["id"] for item in unknown_resp.json()["items"]] == [legacy_id]
    assert aggressive_list_resp.json()["total"] == 1
    assert aggressive_list_resp.json()["items"][0]["decision_profile"] == "aggressive"
