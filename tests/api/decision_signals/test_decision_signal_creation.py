"""Tests for decision signal creation."""

from tests.api.decision_signals._decision_signal_api_support import (
    _payload,
    client_and_db,
)


def test_create_rejects_explicit_null_decision_profile_and_accepts_null_metadata(client_and_db) -> None:
    client, _db = client_and_db

    null_profile_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3010, trace_id="trace-null-profile", decision_profile=None),
    )
    assert null_profile_resp.status_code == 422, null_profile_resp.text
    assert "decision_profile" in null_profile_resp.text

    null_metadata_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3011, trace_id="trace-null-metadata", metadata=None),
    )
    assert null_metadata_resp.status_code == 200, null_metadata_resp.text
    null_metadata_item = null_metadata_resp.json()["item"]
    assert null_metadata_item["decision_profile"] == "balanced"
    assert null_metadata_item["metadata"] == {"decision_profile": "balanced"}

    omitted_metadata_payload = _payload(
        source_report_id=3012,
        trace_id="trace-omitted-metadata",
    )
    omitted_metadata_payload.pop("metadata")
    omitted_metadata_resp = client.post(
        "/api/v1/decision-signals",
        json=omitted_metadata_payload,
    )
    assert omitted_metadata_resp.status_code == 200, omitted_metadata_resp.text
    omitted_metadata_item = omitted_metadata_resp.json()["item"]
    assert omitted_metadata_item["decision_profile"] == "balanced"
    assert omitted_metadata_item["metadata"] == {"decision_profile": "balanced"}


def test_create_treats_null_lifecycle_fields_as_missing(client_and_db) -> None:
    client, _db = client_and_db

    response = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3002,
            trace_id="trace-null-lifecycle-api",
            horizon=None,
            expires_at=None,
            market_phase="intraday",
            metadata={"market_phase_summary": {"minutes_to_close": 25}},
        ),
    )

    assert response.status_code == 200, response.text
    item = response.json()["item"]
    assert item["status"] == "active"
    assert item["horizon"] == "intraday"
    assert item["expires_at"] is not None
