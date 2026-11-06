"""日历/快讯迁移保留安全请求回调、关闭、异常及原始字段契约。"""

import json
from types import SimpleNamespace

import pytest

from data_provider.calendar import wallstreetcn_source as calendar
from data_provider.news import wallstreetcn_live as live
from data_provider.news.base import NewsRequest
from data_provider.news.wallstreetcn_source import WallstreetcnNewsSource


class Response:
    status_code = 200

    def __init__(self, payload):
        self.content = json.dumps(payload).encode()
        self.closed = False

    def close(self):
        self.closed = True


def test_calendar_uses_injected_safe_request_without_redirects_and_keeps_utc(
    monkeypatch,
):
    response = Response(
        {
            "code": 20000,
            "data": {
                "items": [
                    {
                        "id": 7,
                        "public_date": 0,
                        "title": "<b>全天</b>",
                        "country_id": "US",
                    },
                    {
                        "id": 8,
                        "public_date": 1800000000,
                        "title": "事件",
                        "importance": 4,
                    },
                ]
            },
        }
    )
    calls = []

    def safe_get(url, **kwargs):
        calls.append((url, kwargs))
        return response

    # The transport is supplied by the application security boundary, not rebuilt here.
    monkeypatch.setattr(
        "data_provider.news.wallstreetcn_source.get_config",
        lambda: SimpleNamespace(
            wallstreetcn_calendar_base_url="https://calendar.example",
            wallstreetcn_calendar_timeout=8,
            wallstreetcn_calendar_enabled=True,
        ),
    )
    source = WallstreetcnNewsSource(request_get=safe_get)
    result = source.fetch(NewsRequest(mode="calendar", start_ts=0, end_ts=1800000000))
    assert source.calendar_fetcher._request_get is safe_get
    assert source.live_fetcher._request_get is safe_get
    assert calls[0][0].endswith("/apiv1/finance/macrodatas?start=0&end=1800000000")
    assert calls[0][1]["allow_redirects"] is False
    assert [entry.public_date for entry in result.items] == [0, 1800000000]
    assert result.items[0].title == "全天"
    assert result.items[1].raw["importance"] == 4
    assert response.closed


@pytest.mark.parametrize(
    "module,fetcher,method,args",
    [
        (calendar, "WallstreetcnCalendarFetcher", "fetch_countries", ()),
        (live, "WallstreetcnLiveNewsFetcher", "fetch_channel", ("global-channel",)),
    ],
)
def test_response_limit_closes_response_through_canonical_path(module, fetcher, method, args, monkeypatch):
    if module is calendar:
        monkeypatch.setattr(module, "_MAX_RESPONSE_BYTES", 1)
    response = Response({"code": 20000, "data": {"items": []}})
    if module is live:
        response.content = b"x" * (4 * 1024 * 1024 + 1)
    client = getattr(module, fetcher)(request_get=lambda *a, **kw: response)
    error = calendar.CalendarFetchError if module is calendar else live.LiveNewsFetchError
    with pytest.raises(error, match="too large"):
        getattr(client, method)(*args)
    assert response.closed


def test_calendar_invalid_range_does_not_issue_request():
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid range must be rejected before I/O")

    client = calendar.WallstreetcnCalendarFetcher(request_get=forbidden)
    with pytest.raises(calendar.CalendarFetchError, match="invalid calendar time range"):
        client.fetch_range(2, 1)


def test_index_test_import_does_not_shadow_stdlib_in_fresh_process():
    import subprocess
    import sys
    from tests.support.paths import get_repo_root

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "import sys",
                    "from pathlib import Path",
                    "root = Path.cwd()",
                    "import tests.infrastructure.providers.kline.test_us_index_mapping",
                    "assert str(root / 'data_provider') not in sys.path",
                    "import calendar",
                    "import pandas",
                    "import data_provider.calendar.wallstreetcn_source",
                    "assert len(calendar.day_abbr) == 7",
                ]
            ),
        ],
        cwd=get_repo_root(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
