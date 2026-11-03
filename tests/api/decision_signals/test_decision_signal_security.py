"""Tests for decision signal security."""

from tests.api.decision_signals._decision_signal_api_support import (
    Config,
    DatabaseManager,
    DecisionSignalRecord,
    Path,
    TestClient,
    _payload,
    _reset_auth_globals,
    client_and_db,
    create_app,
    os,
    patch,
)


def test_decision_signal_api_requires_session_when_admin_auth_enabled(tmp_path) -> None:
    old_env_file = os.environ.get("ENV_FILE")
    old_database_path = os.environ.get("DATABASE_PATH")
    env_path = tmp_path / ".env"
    db_path = tmp_path / "decision_signal_auth.db"
    static_dir = tmp_path / "empty-static"
    static_dir.mkdir()
    env_path.write_text(
        "\n".join(
            [
                "STOCK_LIST=600519",
                "GEMINI_API_KEY=test",
                "ADMIN_AUTH_ENABLED=true",
                f"DATABASE_PATH={db_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    os.environ["ENV_FILE"] = str(env_path)
    os.environ["DATABASE_PATH"] = str(db_path)
    _reset_auth_globals()
    Config.reset_instance()
    DatabaseManager.reset_instance()

    try:
        client = TestClient(create_app(static_dir=Path(static_dir)))
        resp = client.get("/api/v1/decision-signals")
        assert resp.status_code == 401
        assert resp.json()["error"] == "unauthorized"
    finally:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        _reset_auth_globals()
        if old_env_file is None:
            os.environ.pop("ENV_FILE", None)
        else:
            os.environ["ENV_FILE"] = old_env_file
        if old_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = old_database_path


def test_internal_errors_do_not_reflect_exception_details(client_and_db) -> None:
    client, _db = client_and_db

    with patch("api.v1.endpoints.decision_signals.DecisionSignalService") as service_cls:
        service_cls.return_value.list_signals.side_effect = RuntimeError(
            "secret-token /private/tmp/internal-path"
        )
        resp = client.get("/api/v1/decision-signals")

    assert resp.status_code == 500
    payload = resp.json()
    assert payload["error"] == "internal_error"
    assert payload["message"] == "List decision signals failed"
    assert "secret-token" not in str(payload)
    assert "internal-path" not in str(payload)


def test_corrupt_persisted_json_returns_internal_error_consistently(client_and_db) -> None:
    client, db = client_and_db

    created_resp = client.post(
        "/api/v1/decision-signals",
        json=_payload(source_report_id=3251, trace_id="trace-corrupt-json"),
    )
    assert created_resp.status_code == 200, created_resp.text
    signal_id = created_resp.json()["item"]["id"]

    with db.session_scope() as session:
        row = session.query(DecisionSignalRecord).filter_by(id=signal_id).one()
        row.evidence_json = "{bad persisted json"

    cases = [
        (
            client.get("/api/v1/decision-signals", params={"stock_code": "600519"}),
            "List decision signals failed",
        ),
        (
            client.get(f"/api/v1/decision-signals/{signal_id}"),
            "Get decision signal failed",
        ),
        (
            client.get("/api/v1/decision-signals/latest/600519"),
            "Get latest decision signals failed",
        ),
    ]
    for resp, message in cases:
        assert resp.status_code == 500, resp.text
        payload = resp.json()
        assert payload["error"] == "internal_error"
        assert payload["message"] == message
        assert "bad persisted json" not in str(payload)
