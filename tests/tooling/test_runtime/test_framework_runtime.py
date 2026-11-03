# -*- coding: utf-8 -*-
"""Exercise the unmodified FastAPI, AnyIO and asyncio runtime contracts."""

import asyncio
import threading
from contextlib import asynccontextmanager
from contextvars import ContextVar

import anyio.to_thread
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient as FastAPITestClient


def test_native_test_client_preserves_cookies_between_requests() -> None:
    app = FastAPI()

    @app.post("/login")
    def login(response: Response) -> dict[str, bool]:
        response.set_cookie("hrs_session", "session-token")
        return {"ok": True}

    @app.get("/protected")
    def protected(request: Request) -> dict[str, str | None]:
        return {"session": request.cookies.get("hrs_session")}

    client = FastAPITestClient(app)

    assert client.post("/login").status_code == 200
    assert client.get("/protected").json() == {"session": "session-token"}


def test_native_test_client_lifespan_runs_once_per_context() -> None:
    app = FastAPI()
    lifecycle_calls = {"startup": 0, "shutdown": 0, "requests": 0}

    @app.on_event("startup")
    async def _on_startup() -> None:
        lifecycle_calls["startup"] += 1

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        lifecycle_calls["shutdown"] += 1

    @app.get("/ping")
    def ping() -> dict[str, str]:
        lifecycle_calls["requests"] += 1
        return {"ok": "pong"}

    with FastAPITestClient(app) as client:
        assert client.get("/ping").json() == {"ok": "pong"}
        assert client.get("/ping").json() == {"ok": "pong"}

    assert lifecycle_calls["startup"] == 1
    assert lifecycle_calls["shutdown"] == 1
    assert lifecycle_calls["requests"] == 2


def test_native_test_client_does_not_run_lifespan_without_context() -> None:
    app = FastAPI()
    lifecycle_calls = {"startup": 0, "shutdown": 0, "requests": 0}

    @app.on_event("startup")
    async def _on_startup() -> None:
        lifecycle_calls["startup"] += 1

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        lifecycle_calls["shutdown"] += 1

    @app.get("/ping")
    def ping() -> dict[str, str]:
        lifecycle_calls["requests"] += 1
        return {"ok": "pong"}

    client = FastAPITestClient(app)

    assert client.get("/ping").json() == {"ok": "pong"}
    assert client.get("/ping").json() == {"ok": "pong"}

    assert lifecycle_calls["startup"] == 0
    assert lifecycle_calls["shutdown"] == 0
    assert lifecycle_calls["requests"] == 2


def test_native_anyio_worker_preserves_contextvars() -> None:
    request_id = ContextVar("request_id", default="")
    request_id.set("req-123")

    async def read_from_worker() -> str:
        return await anyio.to_thread.run_sync(request_id.get)

    assert anyio.run(read_from_worker) == "req-123"


def test_native_asyncio_executor_completes_work_and_shuts_down() -> None:
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(asyncio.to_thread(lambda: 'done')) == 'done'
        loop.run_until_complete(loop.shutdown_default_executor())
    finally:
        loop.close()


def test_test_client_is_the_framework_implementation() -> None:
    assert FastAPITestClient.__module__ == 'starlette.testclient'
    assert anyio.to_thread.run_sync.__module__ == 'anyio.to_thread'
    assert asyncio.BaseEventLoop.call_soon_threadsafe.__module__ == 'asyncio.base_events'


def test_native_client_propagates_errors_and_runs_lifespan_cleanup() -> None:
    calls = []

    @asynccontextmanager
    async def lifespan(app):
        calls.append('startup')
        try:
            yield
        finally:
            calls.append('shutdown')

    app = FastAPI(lifespan=lifespan)

    @app.get('/fail')
    async def fail():
        raise RuntimeError('endpoint failed')

    with FastAPITestClient(app) as client:
        with pytest.raises(RuntimeError, match='endpoint failed'):
            client.get('/fail')
    assert calls == ['startup', 'shutdown']
    with FastAPITestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/fail').status_code == 500


def test_native_anyio_limiter_serializes_workers_and_supports_from_thread() -> None:
    async def scenario():
        limiter = anyio.CapacityLimiter(1)
        active = 0
        peak = 0
        results = []

        async def echo(value):
            await anyio.sleep(0)
            return value

        def worker(value):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                results.append(anyio.from_thread.run(echo, value))
            finally:
                active -= 1

        async def launch(value):
            await anyio.to_thread.run_sync(worker, value, limiter=limiter)

        with anyio.fail_after(5):
            async with anyio.create_task_group() as group:
                for value in range(3):
                    group.start_soon(launch, value)
        assert peak == 1
        assert sorted(results) == [0, 1, 2]

    anyio.run(scenario)


@pytest.mark.parametrize('abandon', [False, True])
def test_native_anyio_worker_cancellation_contract(abandon) -> None:
    async def scenario():
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        waiter_done = anyio.Event()
        scopes = []
        returned = []

        def worker():
            started.set()
            try:
                if not release.wait(5):
                    raise TimeoutError('test worker was not released')
                return 'result'
            finally:
                finished.set()

        async def waiter():
            with anyio.CancelScope() as scope:
                scopes.append(scope)
                returned.append(await anyio.to_thread.run_sync(worker, abandon_on_cancel=abandon))
            waiter_done.set()

        with anyio.fail_after(5):
            async with anyio.create_task_group() as group:
                group.start_soon(waiter)
                try:
                    while not started.is_set():
                        await anyio.sleep(0)
                    scopes[0].cancel()
                    if abandon:
                        await waiter_done.wait()
                        assert not finished.is_set()
                    else:
                        await anyio.sleep(0)
                        assert not waiter_done.is_set()
                finally:
                    release.set()
                await waiter_done.wait()
                while not finished.is_set():
                    await anyio.sleep(0)
        assert returned == ([] if abandon else ['result'])

    anyio.run(scenario)
