# -*- coding: utf-8 -*-
"""
@file: app.py
@description: FastAPI 应用工厂：创建应用实例、配置 CORS、注册鉴权与异常处理、
    挂载 v1 路由并托管前端静态文件（生产模式）。被 server.py 与 uvicorn 以
    ``api.app:app`` 直接引用，桌面端通过 HRS_STATIC_DIR 指定包内前端目录。
@author: Lensgcx (GaoCangxiong)

===================================
FastAPI 应用工厂模块
===================================

职责：
1. 创建和配置 FastAPI 应用实例
2. 配置 CORS 中间件
3. 注册路由和异常处理器
4. 托管前端静态文件（生产模式）

使用方式：
    from api.app import create_app
    app = create_app()
"""

import logging
import mimetypes

import sys

# Windows 上 mimetypes.init() 读取注册表可能极慢甚至抛错，且桌面端不需要注册表里的
# MIME 映射；这里在初始化期间临时屏蔽注册表读取，随后立即恢复原方法，避免污染全局。
if sys.platform == "win32" and not mimetypes.inited:
    _orig_read_windows_registry = getattr(mimetypes.MimeTypes, 'read_windows_registry', None)
    if _orig_read_windows_registry is not None:
        mimetypes.MimeTypes.read_windows_registry = lambda self, strict=True: None
        try: mimetypes.init()
        finally: mimetypes.MimeTypes.read_windows_registry = _orig_read_windows_registry
    else:
        mimetypes.init()
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# 模块级日志器，用于输出静态资源自检与 CORS 配置告警。
logger = logging.getLogger(__name__)

# Match src="/assets/foo.js" / href="/assets/foo.css" produced by the
# vite build. Used by the startup self-check to surface packaging
# mismatches early (see GitHub #1064 / #1065 / #1050).
# 匹配 Vite 构建产物 index.html 中的静态资源引用，供启动自检比对磁盘文件；
# 提前发现打包不一致，可避免桌面端白屏只能靠浏览器 devtools 排查。
_INDEX_ASSET_REF_PATTERN = re.compile(
    r"""(?:src|href)\s*=\s*["'](/assets/[^"']+)["']""",
    re.IGNORECASE,
)
# 前端脚本/样式后缀到 MIME 的强制映射。操作系统 MIME 表可能把 .js 识别成
# text/plain，浏览器会以严格 MIME 检查拒绝 ES module，因此需要显式登记。
_FRONTEND_ASSET_MEDIA_TYPES = {
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
}
# 资源缺失时允许原样回传的 MIME 白名单；其余类型统一降级为 text/plain，
# 避免把 404 响应当成可执行的脚本或样式被浏览器加载。
_SAFE_MISSING_ASSET_MEDIA_TYPES = frozenset(_FRONTEND_ASSET_MEDIA_TYPES.values())
# 首页 HTML 禁用缓存：前端发版后用户必须立即拿到新的 index.html，
# 否则会继续引用已被构建清理掉的旧 hash 资源而白屏。
_FRONTEND_INDEX_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _frontend_index_response(static_dir: Path) -> FileResponse:
    """构造前端首页 HTML 响应，并附带禁用缓存的响应头。

    Args:
        static_dir: 前端构建产物目录，其下必须存在 ``index.html``；调用方已校验。

    Returns:
        FileResponse: 以 ``index.html`` 为内容、带 no-cache 头的响应对象。

    Side Effects:
        无；文件读取发生在响应发送阶段。

    """
    return FileResponse(
        static_dir / "index.html",
        headers=_FRONTEND_INDEX_NO_CACHE_HEADERS,
    )


def _check_frontend_assets_consistency(static_dir: Path) -> List[str]:
    """Verify that ``index.html`` only references assets that actually exist
    under ``static_dir``. Returns the list of missing references; an empty
    list means the bundle is consistent.

    Logs an actionable error when a mismatch is detected so the root cause
    is visible in ``logs/desktop.log`` instead of surfacing as a silent
    blank page.

    校验首页引用的 /assets/* 资源是否都真实存在，返回缺失引用列表；空列表表示
    构建产物完整。发现不一致时输出可执行的修复建议日志，让问题直接暴露在
    ``logs/desktop.log``，而不是表现为无提示的白屏。

    Args:
        static_dir: 前端构建产物目录；``index.html`` 不存在时视为无需检查。

    Returns:
        List[str]: 缺失的资源引用路径（去重、保持出现顺序）；无缺失时为空列表。

    Side Effects:
        检测到缺失时写一条 ERROR 级日志；读取失败时写一条 WARNING 级日志。
        不抛异常，自检失败不阻断应用启动。
    """
    index_html = static_dir / "index.html"
    if not index_html.is_file():
        return []
    try:
        html = index_html.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Failed to read %s for asset check: %s", index_html, exc)
        return []

    # 只记录日志、不改变响应，避免自检逻辑影响正常访问。
    missing: List[str] = []
    for match in _INDEX_ASSET_REF_PATTERN.finditer(html):
        ref = match.group(1)
        candidate = static_dir / ref.lstrip("/")
        if not candidate.is_file() and ref not in missing:
            missing.append(ref)

    if missing:
        logger.error(
            "Frontend bundle is inconsistent: index.html references %d asset(s) "
            "that are not present on disk under %s. This will surface as a "
            "blank page in the desktop app (see GitHub #1064 / #1065). "
            "Missing: %s. Re-run the frontend build and make sure the packaging "
            "step copies the freshly generated dist/ directory.",
            len(missing),
            static_dir,
            ", ".join(missing),
        )
    return missing


def _resolve_asset_path(assets_dir: Path, asset_path: str) -> Optional[Path]:
    """Resolve a requested asset path while keeping it confined to assets_dir.

    Rejects absolute paths, NUL bytes, backslashes, Windows drive prefixes and
    any resolved path that escapes the root. This containment check is shared
    by the /assets/* handler and the SPA fallback.

    把 URL 中的相对路径解析为磁盘路径，并保证结果不越出根目录。依次拒绝绝对路径、
    NUL 字节、反斜杠与 Windows 盘符前缀，最后用 realpath 结果做目录包含判断；
    ``/assets/*`` 与 SPA 回退共用这一套校验。

    Args:
        assets_dir: 允许访问的根目录，会被 resolve 为绝对路径。
        asset_path: 来自路由的未解码相对路径；可为空串，但不能为 None。

    Returns:
        Optional[Path]: 安全且位于根目录内的绝对路径；任一校验不通过时返回 None。

    Side Effects:
        无；仅做路径解析与文件系统元数据检查。
    """
    decoded_path = unquote(asset_path)
    if not decoded_path or decoded_path.startswith(("/", "\\")):
        return None
    if "\x00" in decoded_path:
        return None
    if "\\" in decoded_path:
        return None
    if ":" in decoded_path.split("/", 1)[0]:
        return None

    assets_root = assets_dir.resolve()
    candidate = (assets_root / decoded_path).resolve()
    if not candidate.is_relative_to(assets_root):
        return None
    return candidate


def _register_frontend_asset_mime_types() -> None:
    """Keep Vite module assets loadable even when OS MIME maps are wrong.

    向全局 mimetypes 登记前端脚本/样式的正确类型，避免宿主系统 MIME 表异常时
    浏览器拒绝加载 ES module。在应用创建阶段调用一次即可。

    Args:
        无参数。

    Returns:
        None。

    Side Effects:
        修改进程级 ``mimetypes`` 映射表，对所有后续请求生效。
    """
    for suffix, media_type in _FRONTEND_ASSET_MEDIA_TYPES.items():
        mimetypes.add_type(media_type, suffix)


def _frontend_asset_media_type(asset_path: str) -> Optional[str]:
    """返回前端静态资源的 MIME 类型，优先使用显式映射。

    Args:
        asset_path: 资源路径或文件名，仅用其后缀判断，不要求文件存在。

    Returns:
        Optional[str]: 显式映射或系统推断出的媒体类型；无法推断时返回 None。

    Side Effects:
        无。
    """
    suffix = Path(asset_path).suffix.lower()
    if suffix in _FRONTEND_ASSET_MEDIA_TYPES:
        return _FRONTEND_ASSET_MEDIA_TYPES[suffix]
    content_type, _ = mimetypes.guess_type(asset_path)
    return content_type


def _missing_asset_media_type(asset_path: str) -> str:
    """Return a safe media type for a missing asset response.

    Only script/style types are echoed back; anything else falls back to
    text/plain so a 404 body can never be interpreted as executable content.

    为资源缺失响应挑选安全的 Content-Type：仅回传脚本/样式类型，其余降级为
    text/plain，防止 404 响应体被当成可执行内容解析。

    Args:
        asset_path: 请求的资源路径，用于推断媒体类型。

    Returns:
        str: ``text/css``、``text/javascript`` 或 ``text/plain`` 之一，不会是 None。

    Side Effects:
        无。
    """
    content_type = _frontend_asset_media_type(asset_path)
    if content_type in _SAFE_MISSING_ASSET_MEDIA_TYPES:
        return content_type
    return "text/plain"


def _warn_if_open_cors_without_auth() -> None:
    """未启用认证却开放 CORS 时发出警告，提示仅在可信网络使用。

    允许任意来源且无鉴权，等价于把 API 暴露给任意网页；桌面端与本地开发常见此配置，
    因此只告警不阻断启动。

    Args:
        无参数。

    Returns:
        None。

    Side Effects:
        满足告警条件时写一条 WARNING 级日志。
    """
    if is_auth_enabled():
        return
    logger.warning(
        "CORS_ALLOW_ALL=true is enabled while ADMIN_AUTH_ENABLED is false. "
        "The API will accept browser requests from any origin; only use this "
        "on trusted local networks or enable admin authentication."
    )

from api.v1 import api_v1_router
from api.middlewares.auth import add_auth_middleware
from api.middlewares.error_handler import add_error_handlers
from api.v1.schemas.common import HealthResponse
from src.auth import is_auth_enabled
from src.bootstrap.api_lifecycle import app_lifespan, schedule_stock_index_background_refresh
from src.data.stock_index_loader import find_existing_stock_index_path
from src.application.quote.stock_index_remote_service import get_remote_stock_index_cache_path


# 前端自动补全用的股票索引文件名，与前端请求路径 /stocks.index.json 保持一致。
_STOCK_INDEX_FILENAME = "stocks.index.json"
# 股票索引禁用强缓存：后台刷新后客户端需能及时拿到新索引。
_STOCK_INDEX_HEADERS = {
    "Cache-Control": "no-cache",
}


def create_app(static_dir: Optional[Path] = None) -> FastAPI:
    """创建并配置完整的 FastAPI 应用实例。

    依次完成 MIME 登记、静态目录定位、CORS 与鉴权中间件装配、v1 路由与异常处理器
    注册、健康检查与前端托管。前端产物存在与否决定根路由与 SPA 回退是否启用，
    因此同一工厂同时适用于 API-only 部署、Web/Docker 与 Electron 桌面端。

    Args:
        static_dir: 静态文件目录（可选）；未显式传入时优先读 ``HRS_STATIC_DIR``，
            否则回退到仓库根 ``dist-web``。目录不存在时仍可启动，仅提供 API 与文档。

    Returns:
        FastAPI: 已完成路由与中间件装配、可直接交给 ASGI 服务器运行的应用实例。

    Raises:
        不主动抛异常；静态资源自检失败仅记录日志，不影响启动。

    Side Effects:
        修改进程级 mimetypes 映射；调用时立即执行一次静态资源一致性自检，
        并在前端存在时安排股票索引的后台刷新任务。
    """
    # 静态文件目录定位（单一真相源）：
    # 桌面端由 Electron 注入 HRS_STATIC_DIR 指向包内 frontend；网页/Docker 未注入时走仓库根 dist-web。
    _register_frontend_asset_mime_types()

    if static_dir is None:
        override = os.getenv("HRS_STATIC_DIR")
        static_dir = (
            Path(override) if override else Path(__file__).resolve().parent.parent / "dist-web"
        )

    # 创建 FastAPI 实例；lifespan 负责数据库初始化与后台任务启停。
    app = FastAPI(
        title="HermesX API",
        description=(
            "A股/港股/美股自选股智能分析系统 API\n\n"
            "## 功能模块\n"
            "- 股票分析：触发 AI 智能分析\n"
            "- 历史记录：查询历史分析报告\n"
            "- 股票数据：获取行情数据\n\n"
            "## 认证方式\n"
            "支持可选管理员认证：ADMIN_AUTH_ENABLED=true 时，除登录、状态、健康检查和 "
            "OpenAPI 文档外，/api/v1/* 需要有效管理员会话 Cookie；关闭时不强制认证。"
        ),
        version="1.0.0",
        lifespan=app_lifespan,
    )

    # ============================================================
    # CORS 配置
    # ============================================================

    # 默认放行的本地开发端口；生产环境通过 CORS_ORIGINS 追加白名单来源。
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # 从环境变量添加额外的允许来源，逗号分隔并去除空白项。
    extra_origins = os.environ.get("CORS_ORIGINS", "")
    if extra_origins:
        allowed_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

    # 允许所有来源（开发/演示用）。浏览器不允许 "*" 与 credentials 同时使用，
    # 因此开放全部来源时关闭 allow_credentials，并提醒未开启鉴权的风险。
    allow_all_origins = os.environ.get("CORS_ALLOW_ALL", "").lower() == "true"
    allow_credentials = not allow_all_origins
    if allow_all_origins:
        _warn_if_open_cors_without_auth()
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_auth_middleware(app)

    # ============================================================
    # 注册路由
    # ============================================================

    # /api/v1 前缀在此统一挂载；异常处理器在路由之后注册，覆盖全部端点。
    app.include_router(api_v1_router, prefix="/api/v1")
    add_error_handlers(app)

    # ============================================================
    # 根路由和健康检查
    # ============================================================

    # 以 index.html 是否存在作为「前端已构建」的判据，决定根路由与 SPA 回退是否启用。
    has_frontend = static_dir.exists() and (static_dir / "index.html").exists()

    if has_frontend:
        # Surface bundle inconsistencies as soon as the app starts so that
        # blank-page reports (#1064 / #1065 / #1050) can be diagnosed from
        # logs/desktop.log instead of via browser devtools.
        # 启动时立即自检构建产物，白屏问题可直接从桌面端日志定位，无需浏览器 devtools。
        _check_frontend_assets_consistency(static_dir)

        @app.get("/", include_in_schema=False)
        async def root():
            """根路由：返回前端首页 index.html，并禁用浏览器缓存。

            Args:
                无参数。

            Returns:
                FileResponse: 带 no-cache 头的首页响应。

            Side Effects:
                无。
            """
            return _frontend_index_response(static_dir)
    else:
        # 前端未构建时的引导页：说明 API 仍在运行，并给出构建命令与文档入口。
        _FRONTEND_NOT_BUILT_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HRS - Frontend Not Built</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:#0a0e17;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,monospace}
  .card{max-width:580px;padding:2.5rem;border:1px solid #1e293b;border-radius:12px;background:#111827}
  h1{font-size:1.25rem;color:#38bdf8;margin-bottom:.75rem}
  p{font-size:.9rem;line-height:1.7;color:#94a3b8;margin-bottom:.5rem}
  code{background:#1e293b;padding:2px 8px;border-radius:4px;font-size:.85rem;color:#67e8f9}
  .hint{margin-top:1.25rem;padding:.75rem 1rem;border-left:3px solid #f59e0b;background:#1c1917;border-radius:0 6px 6px 0}
  .hint p{color:#fbbf24;margin:0}
  a{color:#38bdf8;text-decoration:none}
  a:hover{text-decoration:underline}
  .status{margin-top:1rem;font-size:.8rem;color:#475569}
</style></head><body><div class="card">
<h1>&#9888;&#65039; Frontend Not Built</h1>
<p>API is running, but the Web UI has not been built yet.</p>
<p>Build the frontend first:</p>
<p><code>cd apps/hrs-web &amp;&amp; npm install &amp;&amp; npm run build</code></p>
<p>Or start with auto-build:</p>
<p><code>python main.py --serve-only</code></p>
<div class="hint"><p>If you only need the API, visit <a href="/docs">/docs</a> for the interactive API documentation.</p></div>
<p class="status">API Version 1.0.0 &bull; <a href="/api/health">/api/health</a></p>
</div></body></html>"""

        @app.get("/", include_in_schema=False)
        async def root():
            """根路由：前端未构建时返回引导页面，说明 API 仍可用。

            Args:
                无参数。

            Returns:
                HTMLResponse: 内含构建指引与文档链接的静态 HTML。

            Side Effects:
                无。
            """
            return HTMLResponse(content=_FRONTEND_NOT_BUILT_HTML)

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="健康检查",
        description="用于负载均衡器或监控系统检查服务状态"
    )
    @app.get(
        "/api/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="健康检查",
        description="用于负载均衡器或监控系统检查服务状态"
    )
    async def health_check() -> HealthResponse:
        """健康检查接口，供负载均衡器与监控系统探活。

        同时注册 /health 与 /api/health，兼容历史调用方；响应始终成功，
        不检查数据库等外部依赖，避免依赖抖动导致实例被误摘除。

        Args:
            无参数。

        Returns:
            HealthResponse: status 固定为 ``ok``，timestamp 为当前本地时间的 ISO 字符串。

        Side Effects:
            无。
        """
        return HealthResponse(
            status="ok",
            timestamp=datetime.now().isoformat()
        )

    def _stock_index_candidate_paths() -> tuple[Path, ...]:
        """返回股票索引文件的候选路径，按优先级排列。

        远端缓存优先（内容更及时），本地打包索引作为冷启动兜底；本地文件不存在时
        只返回远端路径，避免把不存在的路径交给加载器。

        Args:
            无参数；捕获外层 ``static_dir``。

        Returns:
            tuple[Path, ...]: 1~2 个候选路径，顺序即查找优先级。

        Side Effects:
            无。
        """
        local_candidates = (
            static_dir / "static" / _STOCK_INDEX_FILENAME,
        )
        local_path = next((path for path in local_candidates if path.is_file()), None)
        if local_path is None:
            return (get_remote_stock_index_cache_path(),)
        return (
            get_remote_stock_index_cache_path(),
            local_path,
        )

    def _find_existing_stock_index_path() -> Optional[Path]:
        """在候选路径中找出实际存在且可用的股票索引文件。

        Args:
            无参数；调用 ``_stock_index_candidate_paths`` 获取候选集。

        Returns:
            Optional[Path]: 可用的索引文件路径；全部不可用时返回 None。

        Side Effects:
            无；远端缓存路径作为新鲜度判据传给加载器。
        """
        remote_cache_path = get_remote_stock_index_cache_path()
        return find_existing_stock_index_path(
            _stock_index_candidate_paths(),
            remote_cache_path=remote_cache_path,
        )

    @app.api_route(
        f"/{_STOCK_INDEX_FILENAME}",
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
    async def serve_stock_index():
        """Serve the freshest available stock autocomplete index.

        Triggers a coalesced background refresh on each request, then serves
        whichever index file currently exists so the first page load after a
        cold start is never blocked by the remote fetch.

        提供前端股票代码自动补全索引。每次请求都会触发一次去重的后台刷新，但响应
        立即返回当前可用的索引文件，因此冷启动首屏不会被远端抓取阻塞。

        Args:
            无参数。

        Returns:
            Response: 命中文件时为 JSON 文件响应（no-cache 头）；否则为 404 纯文本响应。

        Side Effects:
            通过 ``schedule_stock_index_background_refresh`` 安排后台索引刷新。
        """
        schedule_stock_index_background_refresh(app, "serve-stock-index")

        index_path = _find_existing_stock_index_path()
        if index_path is None:
            return Response(
                content="stock index not found",
                status_code=404,
                media_type="text/plain",
            )
        return FileResponse(
            index_path,
            media_type="application/json",
            headers=_STOCK_INDEX_HEADERS,
        )

    # ============================================================
    # 静态文件托管（前端 SPA）
    # ============================================================

    if has_frontend:
        # Serve `/assets/*` explicitly so that misses return a plain-text
        # 404 with the correct Content-Type instead of the default JSON
        # error response. JSON for a JS/CSS request is what masked the
        # blank-page root cause in #1064; here we make it obvious that the
        # static file simply does not exist on disk.
        # 单独接管 /assets/*，让缺失资源返回纯文本 404 与正确 Content-Type；
        # 默认的 JSON 错误响应曾掩盖 #1064 的白屏根因，这里让「文件不存在」一目了然。
        assets_dir = static_dir / "assets"

        # check_dir=False：构建产物缺 assets 目录时仍允许应用启动，由自检日志暴露问题。
        assets_static_files = StaticFiles(directory=str(assets_dir), check_dir=False)
        assets_root = assets_dir.resolve()

        @app.api_route(
            "/assets/{asset_path:path}",
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
        async def serve_asset(request: Request, asset_path: str):
            """响应前端静态资源请求，拒绝越界路径并为缺失资源返回纯文本 404。

            Args:
                request: 当前请求对象，其 ASGI scope 交给 StaticFiles 生成响应。
                asset_path: 路由捕获的相对路径，可能含 URL 编码或 ``..`` 段。

            Returns:
                Response: 命中文件时为静态文件响应；路径不安全或文件缺失时为 404，
                Content-Type 经 ``_missing_asset_media_type`` 收敛为安全值。

            Side Effects:
                无。
            """
            file_path = _resolve_asset_path(assets_dir, asset_path)
            if file_path is None:
                return Response(
                    content="not found",
                    status_code=404,
                    media_type="text/plain",
                )
            if file_path.is_file():
                relative_path = file_path.relative_to(assets_root).as_posix()
                return await assets_static_files.get_response(relative_path, request.scope)
            return Response(
                content="asset not found",
                status_code=404,
                media_type=_missing_asset_media_type(asset_path),
            )

        # SPA 路由回退
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(request: Request, full_path: str):
            """SPA 路由回退：非 API 路径优先返回真实静态文件，否则返回 index.html。

            前端使用 history 路由，刷新任意深层 URL 都必须拿到首页；同时要明确拦截
            未匹配的 /api/* 请求，避免 API 404 被误当成页面返回。

            Args:
                request: 当前请求对象，此处未使用，保留以满足路由签名。
                full_path: 路由捕获的剩余路径，可为空串。

            Returns:
                Response: 真实存在的静态文件、首页 HTML，或 /api/* 未匹配时的 404 JSON。

            Side Effects:
                无。
            """
            if full_path == "api" or full_path.startswith("api/"):
                return JSONResponse(
                    status_code=404,
                    content={"error": "not_found", "message": f"API endpoint /{full_path} not found"}
                )

            # Reuse the same containment check as /assets/* so that requests
            # like `/%2e%2e/%2e%2e/etc/passwd` cannot escape static_dir via
            # the SPA fallback. Starlette's :path converter does not collapse
            # `..` segments, so static_dir / full_path can resolve outside
            # the bundle root if served unchecked.
            # 复用 /assets/* 的目录包含校验，防止 `/%2e%2e/...` 之类的请求借 SPA 回退
            # 逃出 static_dir；Starlette 的 :path 转换器不会折叠 `..` 段，
            # 未校验的路径拼接会解析到产物目录之外。
            file_path = _resolve_asset_path(static_dir, full_path) if full_path else None
            if file_path is not None and file_path.is_file():
                if file_path == (static_dir / "index.html").resolve():
                    return _frontend_index_response(static_dir)
                # Issue #520: Explicitly resolve MIME type to avoid
                # browsers rejecting JS modules served as text/plain.
                # 显式推断 MIME 类型，避免浏览器因 text/plain 拒绝执行 JS module。
                content_type = _frontend_asset_media_type(str(file_path))
                return FileResponse(file_path, media_type=content_type)

            return _frontend_index_response(static_dir)

    return app


# 默认应用实例（供 uvicorn 直接使用）。导入本模块即完成一次应用装配，
# 因此进程内只应有一个 ASGI 入口；测试可通过 create_app() 创建独立实例。
app = create_app()
