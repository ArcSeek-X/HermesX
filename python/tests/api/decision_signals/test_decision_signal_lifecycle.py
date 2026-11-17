"""Tests for decision signal lifecycle."""

from tests.api.decision_signals._decision_signal_api_support import (
    DecisionSignalRecord,
    _payload,
    client_and_db,
    pytest,
    timedelta,
    utc_naive_now,
)


def test_create_duplicate_list_detail_latest_and_status_update(client_and_db) -> None:
    client, _db = client_and_db

    created_resp = client.post("/api/v1/decision-signals", json=_payload())
    assert created_resp.status_code == 200, created_resp.text
    created = created_resp.json()
    assert created["created"] is True
    signal_id = created["item"]["id"]
    assert created["item"]["stock_code"] == "600519"
    assert created["item"]["plan_quality"] == "partial"
    assert created["item"]["decision_profile"] == "balanced"
    assert created["item"]["metadata"]["decision_profile"] == "balanced"
    assert created["item"]["expires_at"] is not None

    duplicate_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(reason="重复报告里不同文案不应覆盖旧信号"),
    )
    assert duplicate_resp.status_code == 200, duplicate_resp.text
    duplicate = duplicate_resp.json()
    assert duplicate["created"] is False
    assert duplicate["item"]["id"] == signal_id
    assert duplicate["item"]["reason"] == "突破平台"

    list_resp = client.get(
        "/api/v1/decision-signals",
        params={
            "market": "cn",
            "stock_code": "600519.SH",
            "action": "buy",
            "market_phase": "intraday",
            "source_type": "analysis",
            "trigger_source": "api",
            "status": "active",
        },
    )
    assert list_resp.status_code == 200, list_resp.text
    listed = list_resp.json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == signal_id

    detail_resp = client.get(f"/api/v1/decision-signals/{signal_id}")
    assert detail_resp.status_code == 200, detail_resp.text
    assert detail_resp.json()["id"] == signal_id

    latest_resp = client.get("/api/v1/decision-signals/latest/600519", params={"limit": 1})
    assert latest_resp.status_code == 200, latest_resp.text
    assert latest_resp.json()["items"][0]["id"] == signal_id

    patch_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={
            "status": "closed",
            "metadata": {"closed_by": "api-test", "decision_profile": "aggressive"},
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["status"] == "closed"
    assert patch_resp.json()["metadata"]["closed_by"] == "api-test"
    assert patch_resp.json()["metadata"]["decision_profile"] == "balanced"
    assert "task_id" not in patch_resp.json()["metadata"]

    clear_metadata_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={"status": "archived", "metadata": None},
    )
    assert clear_metadata_resp.status_code == 200, clear_metadata_resp.text
    assert clear_metadata_resp.json()["status"] == "archived"
    assert clear_metadata_resp.json()["metadata"] is None

    terminal_reactivate_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={"status": "active"},
    )
    assert terminal_reactivate_resp.status_code == 400, terminal_reactivate_resp.text
    assert terminal_reactivate_resp.json()["error"] == "validation_error"

    invalid_status_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={"status": "bad_status"},
    )
    assert invalid_status_resp.status_code == 422
    assert invalid_status_resp.json()["error"] == "validation_error"

    missing_resp = client.get("/api/v1/decision-signals/999999")
    assert missing_resp.status_code == 404


def test_status_update_sanitizes_metadata_before_response_and_persistence(client_and_db) -> None:
    client, db = client_and_db

    created_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3051, trace_id="trace-3051"),
    )
    assert created_resp.status_code == 200, created_resp.text
    signal_id = created_resp.json()["item"]["id"]

    patch_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={
            "status": "closed",
            "metadata": {
                "source_url": "https://news.example.com/article?id=1",
                "ordinary_services_url": "https://example.com/services/research?id=1",
                "ordinary_robot_url": "https://example.com/robot/send/report?id=1",
                "webhook": "https://hooks.slack.com/services/T000/B000/abcdef",
                "feishu": "https://open.feishu.cn/open-apis/bot/v2/hook/abcdef",
                "userinfo": "https://user:pass@example.com/path",
                "fragment": "https://news.example.com/cb#access_token=abc",
                "note": "Bearer abc+/def==",
            },
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text
    response_blob = str(patch_resp.json()["metadata"])
    assert "https://news.example.com/article?id=1" in response_blob
    assert "https://example.com/services/research?id=1" in response_blob
    assert "https://example.com/robot/send/report?id=1" in response_blob
    assert "[REDACTED_URL]" in response_blob
    assert "hooks.slack.com" not in response_blob
    assert "open.feishu.cn" not in response_blob
    assert "user:pass" not in response_blob
    assert "access_token=abc" not in response_blob
    assert "abc+/def==" not in response_blob
    assert "+/def==" not in response_blob

    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter_by(id=signal_id).one()
        stored_blob = str(row.metadata_json)
    assert "https://news.example.com/article?id=1" in stored_blob
    assert "https://example.com/services/research?id=1" in stored_blob
    assert "https://example.com/robot/send/report?id=1" in stored_blob
    assert "[REDACTED_URL]" in stored_blob
    assert "hooks.slack.com" not in stored_blob
    assert "open.feishu.cn" not in stored_blob
    assert "user:pass" not in stored_blob
    assert "access_token=abc" not in stored_blob
    assert "abc+/def==" not in stored_blob
    assert "+/def==" not in stored_blob


def test_detail_endpoint_lazily_expires_active_signal(client_and_db) -> None:
    client, _db = client_and_db
    created_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3101,
            trace_id="trace-3101",
            expires_at=(utc_naive_now() - timedelta(minutes=5)).isoformat(),
        ),
    )
    assert created_resp.status_code == 200, created_resp.text
    signal_id = created_resp.json()["item"]["id"]
    assert created_resp.json()["item"]["status"] == "expired"

    detail_resp = client.get(f"/api/v1/decision-signals/{signal_id}")
    assert detail_resp.status_code == 200, detail_resp.text
    assert detail_resp.json()["status"] == "expired"

    reactivate_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={"status": "active"},
    )
    assert reactivate_resp.status_code == 400, reactivate_resp.text
    assert reactivate_resp.json()["error"] == "validation_error"

    close_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={"status": "closed"},
    )
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["status"] == "closed"

    latest_resp = client.get("/api/v1/decision-signals/latest/600519")
    assert latest_resp.status_code == 200, latest_resp.text
    assert latest_resp.json()["total"] == 0


def test_patch_status_rejects_expired_signal_without_expires_at_extension(client_and_db) -> None:
    client, _db = client_and_db
    created_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=31011,
            trace_id="trace-31011",
            status="expired",
            expires_at=None,
        ),
    )
    assert created_resp.status_code == 200, created_resp.text
    item = created_resp.json()["item"]
    assert item["status"] == "expired"

    reactivate_resp = client.patch(
        f"/api/v1/decision-signals/{item['id']}/status",
        json={"status": "active"},
    )
    assert reactivate_resp.status_code == 400, reactivate_resp.text
    assert reactivate_resp.json()["error"] == "validation_error"


def test_create_accepts_timezone_aware_expires_at_values(client_and_db) -> None:
    client, _db = client_and_db

    expired_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3102,
            trace_id="trace-3102",
            expires_at="2020-01-01T00:00:00Z",
        ),
    )
    assert expired_resp.status_code == 200, expired_resp.text
    expired_item = expired_resp.json()["item"]
    assert expired_item["status"] == "expired"
    assert expired_item["expires_at"] == "2020-01-01T00:00:00"

    active_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3103,
            trace_id="trace-3103",
            expires_at="2099-01-01T00:00:00+08:00",
        ),
    )
    assert active_resp.status_code == 200, active_resp.text
    active_item = active_resp.json()["item"]
    assert active_item["status"] == "active"
    assert active_item["expires_at"] == "2098-12-31T16:00:00"


def test_create_refreshes_expired_same_source_when_future_expiry_is_supplied(client_and_db) -> None:
    client, db = client_and_db
    expired_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3111,
            trace_id="trace-refresh-original",
            expires_at="2020-01-01T00:00:00Z",
            reason="old reason",
            target_price=1800,
        ),
    )
    assert expired_resp.status_code == 200, expired_resp.text
    expired = expired_resp.json()
    signal_id = expired["item"]["id"]
    assert expired["created"] is True
    assert expired["item"]["status"] == "expired"

    refresh_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3111,
            trace_id="trace-refresh-new",
            expires_at=(utc_naive_now() + timedelta(days=2)).isoformat(),
            reason="fresh reason",
            target_price=1900,
        ),
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    refreshed = refresh_resp.json()
    assert refreshed["created"] is False
    assert refreshed["item"]["id"] == signal_id
    assert refreshed["item"]["status"] == "active"
    assert refreshed["item"]["reason"] == "fresh reason"
    assert refreshed["item"]["target_price"] == 1900
    assert refreshed["item"]["trace_id"] == "trace-refresh-original"
    assert refreshed["item"]["created_at"] == expired["item"]["created_at"]

    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter_by(id=signal_id).one()
        assert row.status == "active"
        assert row.reason == "fresh reason"
        assert row.trace_id == "trace-refresh-original"


def test_create_invalidates_opposing_active_signal_and_latest_filters_it(client_and_db) -> None:
    client, _db = client_and_db
    buy_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=31101,
            trace_id="trace-api-opposing-buy",
            action="buy",
        ),
    )
    assert buy_resp.status_code == 200, buy_resp.text
    buy = buy_resp.json()["item"]

    sell_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=31102,
            trace_id="trace-api-opposing-sell",
            action="sell",
        ),
    )
    assert sell_resp.status_code == 200, sell_resp.text
    sell = sell_resp.json()["item"]

    old_resp = client.get(f"/api/v1/decision-signals/{buy['id']}")
    assert old_resp.status_code == 200, old_resp.text
    old = old_resp.json()
    assert old["status"] == "invalidated"
    assert old["metadata"]["invalidated_by_signal_id"] == sell["id"]

    latest_resp = client.get("/api/v1/decision-signals/latest/600519", params={"limit": 5})
    assert latest_resp.status_code == 200, latest_resp.text
    latest = latest_resp.json()
    assert latest["total"] == 1
    assert latest["items"][0]["id"] == sell["id"]


def test_create_does_not_refresh_expired_same_source_without_future_active_expiry(client_and_db) -> None:
    client, _db = client_and_db
    expired_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3112,
            trace_id="trace-refresh-past-original",
            expires_at="2020-01-01T00:00:00Z",
            reason="old reason",
        ),
    )
    assert expired_resp.status_code == 200, expired_resp.text
    expired = expired_resp.json()

    second_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3112,
            trace_id="trace-refresh-past-new",
            expires_at="2020-01-02T00:00:00Z",
            reason="fresh reason",
        ),
    )
    assert second_resp.status_code == 200, second_resp.text
    second = second_resp.json()
    assert second["created"] is False
    assert second["item"]["id"] == expired["item"]["id"]
    assert second["item"]["status"] == "expired"
    assert second["item"]["reason"] == "old reason"


@pytest.mark.parametrize("terminal_status", ["closed", "invalidated", "archived"])
def test_create_does_not_reactivate_terminal_same_source_status(client_and_db, terminal_status) -> None:
    client, _db = client_and_db
    created_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3113,
            trace_id="trace-terminal-original",
            reason="old reason",
        ),
    )
    assert created_resp.status_code == 200, created_resp.text
    signal_id = created_resp.json()["item"]["id"]

    status_resp = client.patch(
        f"/api/v1/decision-signals/{signal_id}/status",
        json={"status": terminal_status},
    )
    assert status_resp.status_code == 200, status_resp.text

    second_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(
            source_report_id=3113,
            trace_id="trace-terminal-new",
            expires_at=(utc_naive_now() + timedelta(days=2)).isoformat(),
            reason="fresh reason",
        ),
    )
    assert second_resp.status_code == 200, second_resp.text
    second = second_resp.json()
    assert second["created"] is False
    assert second["item"]["id"] == signal_id
    assert second["item"]["status"] == terminal_status
    assert second["item"]["reason"] == "old reason"
