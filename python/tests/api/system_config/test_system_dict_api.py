"""Exercise the country dictionary route with real SQLite persistence."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.endpoints.system_dict import router
from src.bootstrap import system_dict
from src.config import Config
from src.storage import DatabaseManager


def test_country_dictionary_seeds_reads_and_syncs(tmp_path, monkeypatch):
    monkeypatch.setenv("ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "countries.db"))
    Config.reset_instance()
    DatabaseManager.reset_instance()
    app = FastAPI()
    app.include_router(router)
    countries = [{"country_id": "CN", "country_name": "China"}]
    upstream_fails = False

    def fetch_countries():
        if upstream_fails:
            raise TimeoutError("upstream unavailable")
        return countries

    monkeypatch.setattr(system_dict, "fetch_countries", fetch_countries)
    try:
        with TestClient(app) as client:
            upstream_fails = True
            assert client.get("/countries").json() == {"items": [], "degraded": True}
            upstream_fails = False
            seeded = client.get("/countries").json()
            assert not seeded["degraded"]
            assert [row["country_id"] for row in seeded["items"]] == ["CN"]
            upstream_fails = True
            assert client.get("/countries").json() == seeded
            assert client.post("/countries/sync").json() == {
                "upserted": 0, "deactivated": 0, "degraded": True,
            }
            upstream_fails = False
            countries[:] = [{"country_id": "US", "country_name": "United States"}]
            assert client.post("/countries/sync").json() == {
                "upserted": 1, "deactivated": 1, "degraded": False,
            }
            assert [row["country_id"] for row in client.get("/countries").json()["items"]] == ["US"]
    finally:
        DatabaseManager.reset_instance()
        Config.reset_instance()
