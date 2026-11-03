"""Tests for decision signal reassessment."""

from tests.api.decision_signals._decision_signal_api_support import (
    DecisionSignalRecord,
    DecisionSignalService,
    _decision_signal_count,
    _payload,
    _persist_auto_balanced_signal,
    _save_reassess_history,
    _set_reassess_history_created_at,
    _valid_reassess_context,
    _valid_reassess_raw,
    client_and_db,
    datetime,
    get_repo_root,
    pytest,
    timedelta,
    utc_naive_now,
)


def test_reassess_persist_true_inherits_source_report_not_found(client_and_db) -> None:
    client, db = client_and_db
    before = _decision_signal_count(db)

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={
            "source_report_id": 999999,
            "decision_profile": "aggressive",
            "persist": True,
        },
    )

    assert response.status_code == 404, response.text
    assert response.json()["error"] == "source_report_not_found"
    assert _decision_signal_count(db) == before


@pytest.mark.parametrize(
    "payload",
    [
        {"decision_profile": "balanced", "persist": False},
        {"source_report_id": 0, "decision_profile": "balanced", "persist": False},
        {"source_report_id": 1, "decision_profile": "reckless", "persist": False},
    ],
)
def test_reassess_schema_validation_errors(client_and_db, payload) -> None:
    client, _db = client_and_db
    response = client.post("/api/v1/decision-signals/reassess", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "extra_field",
    [
        "signal_id",
        "action",
        "score",
        "confidence",
        "horizon",
        "invalidation",
        "stop_loss",
        "target_price",
        "metadata",
        "scoring_breakdown",
        "guardrail_result",
    ],
)
def test_reassess_forbids_extra_fields(client_and_db, extra_field) -> None:
    client, _db = client_and_db
    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={
            "source_report_id": 1,
            "decision_profile": "balanced",
            "persist": False,
            extra_field: "not-supported",
        },
    )
    assert response.status_code == 422


def test_reassess_error_mapping(client_and_db) -> None:
    client, db = client_and_db

    missing = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": 999999, "decision_profile": "balanced", "persist": False},
    )
    assert missing.status_code == 404
    assert missing.json()["error"] == "source_report_not_found"

    market_review_id = _save_reassess_history(
        db,
        report_type="market_review",
        raw_result=_valid_reassess_raw(),
        context_snapshot=_valid_reassess_context(),
    )
    non_stock = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": market_review_id, "decision_profile": "balanced", "persist": False},
    )
    assert non_stock.status_code == 400
    assert non_stock.json()["error"] == "unsupported_report_type"

    insufficient_id = _save_reassess_history(
        db,
        code="600519",
        operation_advice=None,
        raw_result={"analysis_summary": "仅有摘要，不能推断动作"},
        context_snapshot=_valid_reassess_context(),
    )
    insufficient = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": insufficient_id, "decision_profile": "balanced", "persist": False},
    )
    assert insufficient.status_code == 400
    assert insufficient.json()["error"] == "unsupported_report_snapshot"

    unsupported_market_id = _save_reassess_history(
        db,
        code="NOT_A_VALID_US_SYMBOL",
        raw_result=_valid_reassess_raw(),
        context_snapshot=_valid_reassess_context(),
    )
    unsupported_market = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": unsupported_market_id, "decision_profile": "balanced", "persist": False},
    )
    assert unsupported_market.status_code == 400
    assert unsupported_market.json()["error"] == "unsupported_report_snapshot"


def test_reassess_success_preview_is_read_only_and_uses_opaque_metadata(client_and_db, monkeypatch) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(),
        context_snapshot=_valid_reassess_context(),
    )
    monkeypatch.setattr(
        "src.application.decision.decision_signal_service.DecisionSignalService.create_signal_with_outcome",
        lambda *_args, **_kwargs: (
            _ for _ in ()
        ).throw(AssertionError("create_signal_with_outcome must not be called")),
    )
    monkeypatch.setattr(
        "src.application.decision.decision_signal_service.DecisionSignalService.create_history_bound_signal_with_outcome",
        lambda *_args, **_kwargs: (
            _ for _ in ()
        ).throw(AssertionError("create_history_bound_signal_with_outcome must not be called")),
    )
    monkeypatch.setattr(
        "src.application.decision.decision_signal_service.DecisionSignalService.list_signals",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("list_signals must not be called")),
    )
    monkeypatch.setattr(
        "src.application.analysis.analysis_context_builder._build_quote_block",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("reassess must not rebuild quote context")),
    )
    before = _decision_signal_count(db)

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": False},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["item"] is None
    assert payload["created"] is False
    assert payload["persist_status"] is None
    assert payload["preview"]["action"] == payload["preview"]["metadata"]["guardrail_result"]["final_action"]
    assert payload["preview"]["metadata"]["decision_profile"] == "balanced"
    assert payload["preview"]["metadata"]["profile_source"] == "user_selected"
    assert payload["preview"]["metadata"]["signal_generation_version"] == "decision-profile-reassess-v1"
    assert payload["preview"]["metadata"]["scoring_version"] == "decision-profile-scoring-v1"
    assert "scoring_breakdown" in payload["preview"]["metadata"]
    assert payload["preview"]["metadata"]["data_quality_level"] == "medium"
    assert payload["preview"]["entry_low"] == 1680
    assert payload["preview"]["stop_loss"] == 1600
    assert _decision_signal_count(db) == before


def test_reassess_preview_prefers_stability_adjusted_score(client_and_db) -> None:
    client, db = client_and_db
    raw_result = _valid_reassess_raw(
        action=None,
        sentiment_score=72,
        operation_advice="观望",
    )
    dashboard = raw_result["dashboard"]
    dashboard["decision_score_calibration"] = {
        "raw_score": 72,
        "adjusted_score": 59,
        "final_action": "watch",
        "guardrail_reason": "资金流偏弱，先观望回撤到 45-59。",
    }
    raw_result["dashboard"] = dashboard
    record_id = _save_reassess_history(
        db,
        raw_result=raw_result,
        context_snapshot=_valid_reassess_context(),
    )

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": False},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["preview"]["score"] == 59
    assert payload["preview"]["action"] == "watch"
    assert payload["preview"]["metadata"]["guardrail_result"]["final_action"] == "watch"
    assert _decision_signal_count(db) == 0


def test_reassess_service_has_no_live_market_provider_imports() -> None:
    source = (get_repo_root() / "src/application/decision/decision_signal_reassess_service.py").read_text(
        encoding="utf-8"
    )
    assert "data_provider" not in source
    assert "yfinance" not in source
    assert "akshare" not in source
    assert "build_decision_signal_payload_from_report" not in source


def test_reassess_confidence_missing_buy_is_safe_non_actionable_preview(client_and_db) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(confidence_level=None),
        context_snapshot=_valid_reassess_context(),
    )
    before = _decision_signal_count(db)

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "aggressive", "persist": False},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    guardrail = payload["preview"]["metadata"]["guardrail_result"]
    assert guardrail["raw_action"] == "buy"
    assert guardrail["final_action"] in {"watch", "alert"}
    assert guardrail["passed"] is True
    assert guardrail["adjusted"] is True
    assert "missing_confidence" in guardrail["violations"]
    assert payload["blocked_reason"] is None
    assert payload["warnings"]
    assert {warning["code"] for warning in payload["warnings"]} == {"action_adjusted_by_guardrail"}
    assert all(warning["message"] for warning in payload["warnings"])
    assert _decision_signal_count(db) == before


def test_reassess_persist_writes_authoritative_item_and_deduplicates(client_and_db) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(invalidation="跌破关键支撑且资金流转负"),
        context_snapshot=_valid_reassess_context(),
    )
    request = {
        "source_report_id": record_id,
        "decision_profile": "aggressive",
        "persist": True,
    }

    first = client.post("/api/v1/decision-signals/reassess", json=request)

    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert first_payload["preview"] is None
    assert first_payload["created"] is True
    assert first_payload["persist_status"] == "created"
    item = first_payload["item"]
    assert item["decision_profile"] == "aggressive"
    assert item["source_type"] == "analysis"
    assert item["source_report_id"] == record_id
    assert item["source_agent"] == "decision_profile_reassess"
    assert item["trigger_source"] == "web:decision_profile_reassess"
    assert item["action"] == item["metadata"]["guardrail_result"]["final_action"]
    assert item["metadata"]["profile_source"] == "user_selected"
    assert item["metadata"]["profile_policy_version"] == "decision-profile-v1"
    assert item["metadata"]["signal_generation_version"] == "decision-profile-reassess-v1"
    assert item["metadata"]["scoring_version"] == "decision-profile-scoring-v1"
    assert item["metadata"]["scoring_breakdown"]
    assert item["metadata"]["data_quality_level"] == "medium"
    assert item["metadata"]["guardrail_result"]["passed"] is True

    second = client.post("/api/v1/decision-signals/reassess", json=request)
    assert second.status_code == 200, second.text
    assert second.json()["created"] is False
    assert second.json()["persist_status"] == "existing"
    assert second.json()["item"]["id"] == item["id"]
    assert _decision_signal_count(db) == 1

    timeline = client.get(
        "/api/v1/decision-signals",
        params={"stock_code": "600519", "decision_profile": "aggressive", "page_size": 100},
    )
    assert timeline.status_code == 200, timeline.text
    assert [signal["id"] for signal in timeline.json()["items"]] == [item["id"]]


def test_reassess_persist_anchors_expired_signal_to_report_lifecycle(client_and_db) -> None:
    client, db = client_and_db
    report_created_at = utc_naive_now().replace(microsecond=0) - timedelta(days=30)
    context = _valid_reassess_context()
    context["market_phase_summary"] = {
        "phase": "intraday",
        "session_date": "2026-06-15",
        "minutes_to_close": 5,
        "ignored_private_field": "must-not-persist",
    }
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(
            horizon="intraday",
            invalidation="跌破关键支撑且资金流转负",
        ),
        context_snapshot=context,
    )
    _set_reassess_history_created_at(db, record_id, report_created_at)
    service = DecisionSignalService(db_manager=db)
    expected_created_at = service._coerce_history_created_at_to_utc_naive(report_created_at)

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "aggressive", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    item = payload["item"]
    assert payload["persist_status"] == "created"
    assert item["status"] == "expired"
    assert datetime.fromisoformat(item["created_at"]) == expected_created_at
    assert datetime.fromisoformat(item["expires_at"]) == expected_created_at + timedelta(minutes=5)
    assert item["metadata"]["market_phase_summary"] == {
        "phase": "intraday",
        "session_date": "2026-06-15",
        "minutes_to_close": 5,
    }

    listed = client.get(
        "/api/v1/decision-signals",
        params={"source_type": "analysis", "source_report_id": record_id, "page_size": 100},
    )
    assert listed.status_code == 200, listed.text
    assert [listed_item["id"] for listed_item in listed.json()["items"]] == [item["id"]]
    latest = client.get("/api/v1/decision-signals/latest/600519", params={"limit": 5})
    assert latest.status_code == 200, latest.text
    assert latest.json()["items"] == []


def test_reassess_persist_uses_saved_raw_phase_summary_when_context_summary_is_missing(
    client_and_db,
) -> None:
    client, db = client_and_db
    report_created_at = utc_naive_now().replace(microsecond=0) - timedelta(days=30)
    raw = _valid_reassess_raw(
        horizon="intraday",
        invalidation="跌破关键支撑",
        market_phase_summary={"phase": "intraday", "minutes_to_close": 7},
    )
    context = _valid_reassess_context()
    context.pop("market_phase_summary")
    record_id = _save_reassess_history(db, raw_result=raw, context_snapshot=context)
    _set_reassess_history_created_at(db, record_id, report_created_at)
    expected_created_at = DecisionSignalService(
        db_manager=db
    )._coerce_history_created_at_to_utc_naive(report_created_at)

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert response.status_code == 200, response.text
    item = response.json()["item"]
    assert item["status"] == "expired"
    assert datetime.fromisoformat(item["expires_at"]) == expected_created_at + timedelta(minutes=7)
    assert item["metadata"]["market_phase_summary"] == {
        "phase": "intraday",
        "minutes_to_close": 7,
    }


def test_reassess_persist_returns_final_invalidated_item_without_harming_newer_signal(
    client_and_db,
) -> None:
    client, db = client_and_db
    report_created_at = utc_naive_now().replace(microsecond=0) - timedelta(days=1)
    context = _valid_reassess_context()
    context["market_phase_summary"] = {"phase": "postmarket"}
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(
            horizon="3d",
            invalidation="跌破关键支撑且资金流转负",
        ),
        context_snapshot=context,
    )
    _set_reassess_history_created_at(db, record_id, report_created_at)
    newer_sell = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            action="sell",
            score=20,
            decision_profile="aggressive",
            source_report_id=record_id + 1000,
            trace_id="trace-newer-aggressive-sell",
            market_phase="postmarket",
            horizon="3d",
        ),
    ).json()["item"]

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "aggressive", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    item = payload["item"]
    assert payload["persist_status"] == "created"
    assert item["status"] == "invalidated"
    assert item["metadata"]["invalidated_by_signal_id"] == newer_sell["id"]
    assert client.get(f"/api/v1/decision-signals/{newer_sell['id']}").json()["status"] == "active"
    latest = client.get("/api/v1/decision-signals/latest/600519", params={"limit": 5})
    assert [latest_item["id"] for latest_item in latest.json()["items"]] == [newer_sell["id"]]


def test_reassess_history_refresh_uses_created_at_not_updated_at_for_invalidation(
    client_and_db,
) -> None:
    client, db = client_and_db
    report_created_at = utc_naive_now().replace(microsecond=0) - timedelta(days=1)
    raw = _valid_reassess_raw(horizon="3d", invalidation="跌破关键支撑")
    context = _valid_reassess_context()
    context["market_phase_summary"] = {"phase": "postmarket"}
    record_id = _save_reassess_history(db, raw_result=raw, context_snapshot=context)
    _set_reassess_history_created_at(db, record_id, report_created_at)
    auto_item = _persist_auto_balanced_signal(
        db,
        source_report_id=record_id,
        raw_result=raw,
        context_snapshot=context,
    )
    expected_created_at = DecisionSignalService(
        db_manager=db
    )._coerce_history_created_at_to_utc_naive(report_created_at)
    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter(DecisionSignalRecord.id == auto_item["id"]).one()
        row.created_at = expected_created_at
        row.status = "expired"
        row.expires_at = utc_naive_now() - timedelta(minutes=1)
        row.updated_at = utc_naive_now() - timedelta(minutes=1)
    newer_sell = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            action="sell",
            score=20,
            decision_profile="balanced",
            source_report_id=record_id + 2000,
            trace_id="trace-newer-balanced-sell",
            market_phase="postmarket",
            horizon="3d",
        ),
    ).json()["item"]

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["persist_status"] == "refreshed"
    assert payload["item"]["id"] == auto_item["id"]
    assert payload["item"]["status"] == "invalidated"
    assert payload["item"]["metadata"]["invalidated_by_signal_id"] == newer_sell["id"]
    assert client.get(f"/api/v1/decision-signals/{newer_sell['id']}").json()["status"] == "active"


def test_reassess_persist_requires_report_time_without_breaking_preview(client_and_db) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(invalidation="跌破关键支撑"),
        context_snapshot=_valid_reassess_context(),
    )
    _set_reassess_history_created_at(db, record_id, None)
    before = _decision_signal_count(db)

    preview = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": False},
    )
    persisted = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert preview.status_code == 200, preview.text
    assert preview.json()["preview"] is not None
    assert persisted.status_code == 400, persisted.text
    assert persisted.json()["error"] == "unsupported_report_snapshot"
    assert _decision_signal_count(db) == before


def test_reassess_balanced_persist_creates_when_auto_extraction_has_no_signal(client_and_db) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(invalidation="跌破关键支撑"),
        context_snapshot=_valid_reassess_context(),
    )

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["persist_status"] == "created"
    assert payload["created"] is True
    assert payload["item"]["decision_profile"] == "balanced"
    assert payload["item"]["source_agent"] == "decision_profile_reassess"
    assert payload["item"]["trigger_source"] == "web:decision_profile_reassess"
    assert payload["item"]["metadata"]["profile_source"] == "user_selected"
    assert payload["item"]["metadata"]["scoring_breakdown"]
    assert _decision_signal_count(db) == 1


def test_reassess_balanced_persist_reuses_actual_auto_generated_signal(client_and_db) -> None:
    client, db = client_and_db
    raw = _valid_reassess_raw(invalidation="跌破关键支撑")
    context = _valid_reassess_context()
    record_id = _save_reassess_history(db, raw_result=raw, context_snapshot=context)
    auto_item = _persist_auto_balanced_signal(
        db,
        source_report_id=record_id,
        raw_result=raw,
        context_snapshot=context,
    )

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["persist_status"] == "existing"
    assert payload["created"] is False
    assert payload["item"]["id"] == auto_item["id"]
    assert payload["item"]["source_agent"] == auto_item["source_agent"]
    assert payload["item"]["trigger_source"] == "api"
    assert payload["item"]["metadata"]["profile_source"] == "auto_default"
    assert payload["item"]["metadata"]["signal_generation_version"] == "legacy-report-extractor-v1"
    assert "scoring_breakdown" not in payload["item"]["metadata"]
    assert _decision_signal_count(db) == 1


def test_reassess_balanced_persist_refreshes_expired_auto_generated_signal(client_and_db) -> None:
    client, db = client_and_db
    raw = _valid_reassess_raw(invalidation="跌破关键支撑")
    context = _valid_reassess_context()
    record_id = _save_reassess_history(db, raw_result=raw, context_snapshot=context)
    auto_item = _persist_auto_balanced_signal(
        db,
        source_report_id=record_id,
        raw_result=raw,
        context_snapshot=context,
    )
    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter(DecisionSignalRecord.id == auto_item["id"]).one()
        row.status = "expired"
        row.expires_at = utc_naive_now() - timedelta(minutes=1)
        row.updated_at = utc_naive_now() - timedelta(minutes=1)

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["persist_status"] == "refreshed"
    assert payload["created"] is False
    assert payload["item"]["id"] == auto_item["id"]
    assert payload["item"]["status"] == "active"
    assert payload["item"]["created_at"] == auto_item["created_at"]
    assert payload["item"]["source_agent"] == auto_item["source_agent"]
    assert payload["item"]["trigger_source"] == "api"
    assert payload["item"]["metadata"]["profile_source"] == "user_selected"
    assert payload["item"]["metadata"]["signal_generation_version"] == "decision-profile-reassess-v1"
    assert payload["item"]["metadata"]["scoring_breakdown"]
    assert payload["item"]["action"] == payload["item"]["metadata"]["guardrail_result"]["final_action"]
    assert _decision_signal_count(db) == 1


def test_reassess_balanced_persist_reports_relaxed_phase_fill_without_overwriting_auto_metadata(
    client_and_db,
) -> None:
    client, db = client_and_db
    raw = _valid_reassess_raw(invalidation="跌破关键支撑")
    context = _valid_reassess_context()
    record_id = _save_reassess_history(db, raw_result=raw, context_snapshot=context)
    auto_item = _persist_auto_balanced_signal(
        db,
        source_report_id=record_id,
        raw_result=raw,
        context_snapshot=context,
    )
    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter(DecisionSignalRecord.id == auto_item["id"]).one()
        row.market_phase = None
        row.updated_at = utc_naive_now()

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["persist_status"] == "refreshed"
    assert payload["created"] is False
    assert payload["item"]["id"] == auto_item["id"]
    assert payload["item"]["market_phase"] == "intraday"
    assert payload["item"]["source_agent"] == auto_item["source_agent"]
    assert payload["item"]["trigger_source"] == "api"
    assert payload["item"]["metadata"]["profile_source"] == "auto_default"
    assert payload["item"]["metadata"]["signal_generation_version"] == "legacy-report-extractor-v1"
    assert "scoring_breakdown" not in payload["item"]["metadata"]
    assert _decision_signal_count(db) == 1


@pytest.mark.parametrize("terminal_status", ["closed", "invalidated", "archived"])
def test_reassess_balanced_persist_returns_terminal_auto_signal_without_reactivation(
    client_and_db,
    terminal_status,
) -> None:
    client, db = client_and_db
    raw = _valid_reassess_raw(invalidation="跌破关键支撑")
    context = _valid_reassess_context()
    record_id = _save_reassess_history(db, raw_result=raw, context_snapshot=context)
    auto_item = _persist_auto_balanced_signal(
        db,
        source_report_id=record_id,
        raw_result=raw,
        context_snapshot=context,
    )
    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter(DecisionSignalRecord.id == auto_item["id"]).one()
        row.status = terminal_status
        row.updated_at = utc_naive_now()

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "balanced", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["persist_status"] == "existing"
    assert payload["created"] is False
    assert payload["item"]["id"] == auto_item["id"]
    assert payload["item"]["status"] == terminal_status
    assert payload["item"]["metadata"]["profile_source"] == "auto_default"
    assert _decision_signal_count(db) == 1


def test_reassess_persist_distinguishes_profiles(client_and_db) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(invalidation="跌破关键支撑"),
        context_snapshot=_valid_reassess_context(),
    )

    aggressive = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "aggressive", "persist": True},
    )
    conservative = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "conservative", "persist": True},
    )

    assert aggressive.status_code == 200, aggressive.text
    assert conservative.status_code == 200, conservative.text
    assert aggressive.json()["item"]["id"] != conservative.json()["item"]["id"]
    assert aggressive.json()["item"]["decision_profile"] == "aggressive"
    assert conservative.json()["item"]["decision_profile"] == "conservative"
    assert _decision_signal_count(db) == 2


def test_reassess_persist_invalidates_only_same_profile_opposing_signal(client_and_db) -> None:
    client, db = client_and_db
    balanced_sell = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            action="sell",
            score=20,
            decision_profile="balanced",
            source_report_id=4101,
            trace_id="trace-balanced-sell",
        ),
    ).json()["item"]
    aggressive_sell = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            action="sell",
            score=20,
            decision_profile="aggressive",
            source_report_id=4102,
            trace_id="trace-aggressive-sell",
        ),
    ).json()["item"]
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(invalidation="跌破关键支撑"),
        context_snapshot=_valid_reassess_context(),
    )

    persisted = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "aggressive", "persist": True},
    )

    assert persisted.status_code == 200, persisted.text
    assert persisted.json()["item"]["action"] == "buy"
    assert client.get(f"/api/v1/decision-signals/{aggressive_sell['id']}").json()["status"] == "invalidated"
    assert client.get(f"/api/v1/decision-signals/{balanced_sell['id']}").json()["status"] == "active"


def test_reassess_persist_saves_safe_guardrail_downgrade_with_audit_metadata(client_and_db) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(confidence_level=None),
        context_snapshot=_valid_reassess_context(),
    )

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": "aggressive", "persist": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    guardrail = payload["item"]["metadata"]["guardrail_result"]
    assert payload["item"]["action"] == "watch"
    assert guardrail["raw_action"] == "buy"
    assert guardrail["final_action"] == "watch"
    assert guardrail["passed"] is True
    assert guardrail["adjusted"] is True
    assert guardrail["violations"]
    assert guardrail["adjustments"]
    assert payload["warnings"]
    assert all(warning["message"] for warning in payload["warnings"])
    assert _decision_signal_count(db) == 1


@pytest.mark.parametrize("decision_profile", ["balanced", "aggressive"])
def test_reassess_persist_guardrail_block_returns_structured_error_without_write(
    client_and_db,
    decision_profile,
) -> None:
    client, db = client_and_db
    record_id = _save_reassess_history(
        db,
        raw_result=_valid_reassess_raw(invalidation="跌破关键支撑"),
        context_snapshot=_valid_reassess_context(),
        stop_loss=1900,
        take_profit=1800,
    )
    before = _decision_signal_count(db)

    response = client.post(
        "/api/v1/decision-signals/reassess",
        json={"source_report_id": record_id, "decision_profile": decision_profile, "persist": True},
    )

    assert response.status_code == 400, response.text
    payload = response.json()
    assert payload["error"] == "guardrail_blocked"
    assert payload["blocked_reason"]
    assert {warning["code"] for warning in payload["warnings"]} >= {
        "action_adjusted_by_guardrail",
        "action_blocked_by_guardrail",
    }
    assert all(warning["message"] for warning in payload["warnings"])
    assert "created" not in payload
    assert _decision_signal_count(db) == before
