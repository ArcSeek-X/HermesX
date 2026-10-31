# -*- coding: utf-8 -*-
"""W7.2：启动时间与关键接口性能基线测量（离线、可复现）。

`ARCHITECTURE_TARGET.md` §9.2-5 要求「性能/启动时间的基线数值与验收阈值须在相关
切片开始前记录」。本脚本产出可复现的数字，供
`documents/framework/security_performance_baseline.md` 登记基线：

1. `import api.app` 冷进程耗时（子进程，含解释器启动，排除本地模块缓存复用）；
2. 完整 lifespan 启动耗时（临时库建表 + 幂等迁移 + 适配器装配，抑制调度器）；
3. `create_app()` 工厂耗时（进程内，重复取最小/中位）；
4. API 表面规模（OpenAPI paths 数）与 OpenAPI 首次生成耗时；
5. 关键接口的 p50 / p95 延迟（ASGI transport，**不触发 lifespan**，因此不会
   跑启动迁移、不写数据库，也不发起网络请求）。

用法：
    python scripts/measure_performance_baseline.py           # 人类可读
    python scripts/measure_performance_baseline.py --json     # 机器可读
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # 直接以脚本方式运行时，仓库根不在 sys.path[0]
    sys.path.insert(0, str(ROOT))
ENDPOINTS = ("/api/health", "/api/v1/health", "/api/v1/auth/status")
IMPORT_REPEATS = 3
FACTORY_REPEATS = 3
LATENCY_REQUESTS = 40
WARMUP_REQUESTS = 5


def _ms(seconds: float) -> float:
    return round(seconds * 1000, 2)


def measure_import_ms() -> dict:
    """冷子进程 `import api.app` 的墙钟耗时（含解释器启动）。"""
    samples = []
    for _ in range(IMPORT_REPEATS):
        start = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "-c", "import api.app"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        elapsed = time.perf_counter() - start
        if proc.returncode != 0:
            raise RuntimeError(f"import api.app 失败：{proc.stderr.strip()}")
        samples.append(_ms(elapsed))
    return {"samples": samples, "min": min(samples), "median": round(statistics.median(samples), 2)}


_LIFESPAN_SNIPPET = """
import asyncio, json, os, shutil, sqlite3, tempfile, time
from pathlib import Path

tmp_dir = Path(tempfile.mkdtemp(prefix="hrs_baseline_"))
db_path = tmp_dir / "baseline.db"
os.environ["DATABASE_PATH"] = str(db_path)

from api.app import create_app

async def main():
    app = create_app()
    start = time.perf_counter()
    async with app.router.lifespan_context(app):
        elapsed = round((time.perf_counter() - start) * 1000, 2)
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
    print(json.dumps({"startup_ms": elapsed, "table_count": tables}))
    shutil.rmtree(tmp_dir, ignore_errors=True)

asyncio.run(main())
"""


def measure_lifespan_ms() -> dict:
    """完整 lifespan 启动耗时（建库 + 幂等迁移 + 适配器装配）。

    隔离子进程：``DATABASE_PATH`` 指向临时目录、``HRS_RUNTIME_SCHEDULER_SUPPRESS_START=true``
    抑制调度器启动，因此不触碰开发库、不注册定时任务、不发起网络请求。
    """
    env = dict(os.environ)
    env["HRS_RUNTIME_SCHEDULER_SUPPRESS_START"] = "true"
    proc = subprocess.run(
        [sys.executable, "-c", _LIFESPAN_SNIPPET],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"lifespan 启动失败：{proc.stderr.strip()[-800:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def measure_factory_ms() -> dict:
    """`create_app()` 进程内耗时（首次调用含路由装配）与 API 表面规模。"""
    from api.v1 import api_v1_router
    from api.app import create_app

    samples = []
    for _ in range(FACTORY_REPEATS):
        start = time.perf_counter()
        app = create_app()
        samples.append(_ms(time.perf_counter() - start))

    # 当前 FastAPI 版本的 include_router 是惰性的，``app.routes`` 只反映顶层条目，
    # 真实 API 面以 OpenAPI paths 计；首次生成也代表 /docs 首访成本。
    start = time.perf_counter()
    schema = app.openapi()
    return {
        "samples": samples,
        "min": min(samples),
        "median": round(statistics.median(samples), 2),
        "api_v1_route_entries": len(api_v1_router.routes),
        "openapi_path_count": len(schema["paths"]),
        "openapi_first_call_ms": _ms(time.perf_counter() - start),
    }


async def _measure_latencies(app) -> dict:
    import httpx

    transport = httpx.ASGITransport(app=app)
    results: dict[str, dict] = {}
    async with httpx.AsyncClient(transport=transport, base_url="http://baseline.local") as client:
        for path in ENDPOINTS:
            for _ in range(WARMUP_REQUESTS):
                await client.get(path)

            samples, status = [], None
            for _ in range(LATENCY_REQUESTS):
                start = time.perf_counter()
                response = await client.get(path)
                samples.append((time.perf_counter() - start) * 1000)
                status = response.status_code
            samples.sort()
            results[path] = {
                "status": status,
                "p50": round(samples[int(len(samples) * 0.50) - 1], 2),
                "p95": round(samples[int(len(samples) * 0.95) - 1], 2),
                "max": round(samples[-1], 2),
            }
    return results


def collect() -> dict:
    payload = {
        "import_api_app": measure_import_ms(),
        "lifespan_startup": measure_lifespan_ms(),
        "create_app": measure_factory_ms(),
        "python": sys.version.split()[0],
    }
    from api.app import create_app

    app = create_app()
    payload["endpoint_latency"] = asyncio.run(_measure_latencies(app))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure startup and key endpoint baselines.")
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    args = parser.parse_args()

    payload = collect()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"python {payload['python']}")
    imp = payload["import_api_app"]
    fac = payload["create_app"]
    life = payload["lifespan_startup"]
    print(f"import api.app   min={imp['min']}ms median={imp['median']}ms  samples={imp['samples']}")
    print(f"lifespan startup {life['startup_ms']}ms (temp DB tables={life['table_count']})")
    print(
        f"create_app()     min={fac['min']}ms median={fac['median']}ms  "
        f"samples={fac['samples']}"
    )
    print(
        f"api surface      openapi_paths={fac['openapi_path_count']} "
        f"api_v1_entries={fac['api_v1_route_entries']} "
        f"openapi_first_call={fac['openapi_first_call_ms']}ms"
    )
    print("endpoint latency (ASGI, lifespan 未触发):")
    for path, stat in payload["endpoint_latency"].items():
        print(
            f"  {path:<22} status={stat['status']} "
            f"p50={stat['p50']}ms p95={stat['p95']}ms max={stat['max']}ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
