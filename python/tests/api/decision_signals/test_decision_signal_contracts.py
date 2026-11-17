"""Tests for decision signal contracts."""

from tests.api.decision_signals._decision_signal_api_support import (
    _payload,
    _temporary_tz,
    client_and_db,
    datetime,
    timedelta,
    timezone,
)


def test_timezone_aware_future_expiry_stays_active_in_non_utc_runtime(client_and_db) -> None:
    client, _db = client_and_db

    with _temporary_tz("Asia/Shanghai"):
        created_resp = client.post(
            "/api/v1/decision-signals",
            json=_payload(
                source_report_id=3104,
                trace_id="trace-3104",
                expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            ),
        )
        assert created_resp.status_code == 200, created_resp.text
        created = created_resp.json()["item"]
        assert created["status"] == "active"
        for field_name in ("expires_at", "created_at", "updated_at"):
            assert datetime.fromisoformat(created[field_name]).tzinfo is None

        latest_resp = client.get("/api/v1/decision-signals/latest/600519")
        assert latest_resp.status_code == 200, latest_resp.text
        assert latest_resp.json()["total"] == 1
        assert latest_resp.json()["items"][0]["id"] == created["id"]


def test_query_validation_error_envelope(client_and_db) -> None:
    client, _db = client_and_db
    resp = client.get("/api/v1/decision-signals", params={"action": "panic"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_error"

    page_size_resp = client.get("/api/v1/decision-signals", params={"page_size": 0})
    assert page_size_resp.status_code == 422
    assert page_size_resp.json()["error"] == "validation_error"


def test_create_schema_and_service_validation_errors(client_and_db) -> None:
    client, _db = client_and_db

    schema_invalid_cases = [
        {"entry_low": -1},
        {"entry_high": 0},
        {"stop_loss": "nan"},
        {"target_price": "inf"},
        {"metadata": ["not-an-object"]},
    ]
    for overrides in schema_invalid_cases:
        resp = client.post("/api/v1/decision-signals", json=_payload(**overrides))
        assert resp.status_code == 422, resp.text
        assert resp.json()["error"] == "validation_error"

    range_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3301, trace_id="trace-range", entry_low=1700, entry_high=1600),
    )
    assert range_resp.status_code == 400, range_resp.text
    assert range_resp.json()["error"] == "validation_error"

    long_trace_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3302, trace_id="x" * 65),
    )
    assert long_trace_resp.status_code == 400, long_trace_resp.text
    assert long_trace_resp.json()["error"] == "validation_error"
    assert "trace_id" in long_trace_resp.json()["message"]

    sensitive_trace_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3303, trace_id="Bearer abc+/def=="),
    )
    assert sensitive_trace_resp.status_code == 400, sensitive_trace_resp.text
    assert sensitive_trace_resp.json()["error"] == "validation_error"
    assert "trace_id" in sensitive_trace_resp.json()["message"]
    assert "abc+/def==" not in str(sensitive_trace_resp.json())

    for trace_id, leaked in (
        ("Authorization: Basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
        ("cookie=session=abc123", "session=abc123"),
    ):
        sensitive_identity_resp = client.post(
            "/api/v1/decision-signals",
            json=_payload(source_report_id=3304, trace_id=trace_id),
        )
        assert sensitive_identity_resp.status_code == 400, sensitive_identity_resp.text
        assert sensitive_identity_resp.json()["error"] == "validation_error"
        assert "trace_id" in sensitive_identity_resp.json()["message"]
        assert leaked not in str(sensitive_identity_resp.json())
