# -*- coding: utf-8 -*-
"""
@file: stocks.py
@description: 股票数据端点：实时行情、历史 K 线、当日分时、图片代码识别、文件导入与自选队列；由 api.v1.router 挂到 /api/v1/stocks，分时数据复用 kline 端点的缓存约定。
@author: Lensgcx (GaoCangxiong)

===================================
股票数据接口
===================================

职责：
1. POST /api/v1/stocks/extract-from-image 从图片提取股票代码
2. POST /api/v1/stocks/parse-import 解析 CSV/Excel/剪贴板
3. GET /api/v1/stocks/{code}/quote 实时行情接口
4. GET /api/v1/stocks/{code}/history 历史行情接口
5. GET /api/v1/stocks/{code}/timeline 分时（当日）明细接口
6. POST /api/v1/stocks/batch-quote 批量实时行情（最近搜索卡片）
7. POST /api/v1/stocks/batch-timeline 批量当日分时（下采样缩略图）
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any
import re

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, Depends

from api.deps import get_system_config_service

from api.v1.schemas.stocks import (
    BatchCodesRequest,
    BatchQuoteResponse,
    BatchTimelineItem,
    BatchTimelineResponse,
    ExtractFromImageResponse,
    ExtractItem,
    KLineData,
    StockHistoryResponse,
    StockQuote,
    StockTimelinePoint,
    StockTimelineResponse,
)
from api.v1.schemas.history import WatchlistRequest, WatchlistResponse
from api.v1.schemas.common import ErrorResponse
from src.application.analysis.image_stock_extractor import (
    ALLOWED_MIME,
    MAX_SIZE_BYTES,
    extract_stock_codes_from_image,
)
from src.application.quote.import_parser import (
    MAX_FILE_BYTES,
    parse_import_from_bytes,
    parse_import_from_text,
)
from src.application.quote.intraday_timeline_service import fetch_intraday_timeline
from src.application.quote.stock_code_utils import normalize_stock_code_for_stock_list
from src.domain.market.stock_list_parser import split_stock_list
from src.bootstrap.quote import build_stock_service
from src.application.runtime.system_config_service import SystemConfigService

# 模块级日志器，记录行情与识别失败。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/stocks。
router = APIRouter()

# 须在 /{stock_code} 路由之前定义
# 允许上传的图片 MIME 白名单字符串，用于图片识别接口的入参校验与错误提示。
ALLOWED_MIME_STR = ", ".join(ALLOWED_MIME)

# 分时缓存（TTL 30s）：分时为当日数据，短 TTL 即可显著降低自选股列表一页 10 行的
# 重复请求压力；上游 trends2 有全局节流（≈3 req/s），缓存同时降低限流风险。
_timeline_cache: Dict[str, Dict[str, Any]] = {}
# 分时数据缓存有效期（秒）；上游 trends2 有全局节流，缓存用于降低限流风险。
_TIMELINE_CACHE_TTL = 30


def _timeline_cache_valid(cache_item: Optional[Dict[str, Any]], ttl: int) -> bool:
    """分时缓存项是否仍在 TTL 内（与 kline 端点同一约定）。

    无 timestamp 的旧格式条目按立即失效处理，避免永久命中。

    Args:
        cache_item: 缓存条目字典，可为 None。
        ttl: 有效期秒数。

    Returns:
        bool: 命中且未过期返回 True。
    """
    if not cache_item:
        return False
    return (time.time() - float(cache_item.get("timestamp", 0))) < ttl


def _read_watchlist_codes(service: SystemConfigService) -> list:
    """Read STOCK_LIST codes as-is (no normalization).

    读取 STOCK_LIST 原样返回，不做代码规范化，避免写入侧悄悄改变用户已保存的代码形式。

    Args:
        service: 配置服务，提供 STOCK_LIST 读写。

    Returns:
        list: 原始股票代码列表。
    """
    config_data = service.get_config(include_schema=False)
    stock_list_str = ""
    for item in config_data.get("items", []):
        if item.get("key") == "STOCK_LIST":
            stock_list_str = str(item.get("value", ""))
            break
    return split_stock_list(stock_list_str)


def _write_watchlist_codes(service: SystemConfigService, codes: list) -> None:
    """Persist stock codes to STOCK_LIST as-is (no normalization).

    按调用方给定顺序原样持久化，去重与规范化由业务入口负责。

    Args:
        service: 配置服务。
        codes: 待写入的代码列表。

    Returns:
        None。

    Side Effects:
        修改 STOCK_LIST 配置。
    """
    config_data = service.get_config(include_schema=False)
    config_version = config_data.get("config_version", "")
    service.update(
        config_version=config_version,
        items=[{"key": "STOCK_LIST", "value": ",".join(codes)}],
        mask_token="******",
        reload_now=True,
    )


# Stock code validation patterns (aligned with frontend validateStockCode)
# 股票代码格式规则与前端 validateStockCode 保持一致，避免前后端对同一输入判定不同。
# 受支持的股票代码格式正则，与前端 validateStockCode 口径对齐。
_STOCK_CODE_RE = re.compile(
    r"^(?:\d{6}"                              # A-share 6-digit
    r"|(?:SH|SZ|BJ)\d{6}"                     # exchange-prefixed A-share
    r"|\d{6}\.(?:SH|SZ|SS|BJ)"                # exchange-suffixed A-share
    r"|\d{1,5}\.HK"                           # HK suffix format
    r"|HK\d{1,5}"                             # HK prefix format
    r"|\d{5}"                                 # bare 5-digit HK code
    r"|[A-Z]{1,5}(?:\.(?:US|[A-Z]))?"         # US ticker
    r")$",
    re.IGNORECASE,
)


def _validate_and_normalize_stock_code(code: str) -> str:
    """Validate stock code format and return canonical form.

    Raises HTTPException(400) if the code does not match supported formats.

    校验股票代码格式并转为规范形式；不符合 A 股/港股/美股等受支持格式时直接返回 400，避免非法代码进入下游数据源。

    Args:
        code: 原始代码字符串。

    Returns:
        str: 规范化后的股票代码。

    Raises:
        HTTPException: 格式不支持时返回 400。
    """
    stripped = code.strip()
    if not stripped:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_stock_code", "message": "股票代码不能为空"},
        )
    if not _STOCK_CODE_RE.match(stripped):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_stock_code",
                "message": f"'{stripped}' 不是合法的股票代码格式",
            },
        )
    return normalize_stock_code_for_stock_list(stripped)


def _watchlist_match_key(code: str) -> str:
    """Return the equivalence key used for watchlist add/remove matching.

    生成自选股增删匹配的等价键：让 600519 与 600519.SH 视为同一标的，避免重复添加。

    Args:
        code: 股票代码。

    Returns:
        str: 用于比对的等价键。
    """
    normalized = normalize_stock_code_for_stock_list(code.strip())
    if re.fullmatch(r"\d{5}", normalized):
        return f"HK{normalized}"
    return normalized.upper()


@router.post(
    "/extract-from-image",
    response_model=ExtractFromImageResponse,
    responses={
        200: {"description": "提取的股票代码"},
        400: {"description": "图片无效", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="从图片提取股票代码",
    description="上传截图/图片，通过 Vision LLM 提取股票代码。支持 JPEG、PNG、WebP、GIF，最大 5MB。",
)
def extract_from_image(
    file: Optional[UploadFile] = File(None, description="图片文件（表单字段名 file）"),
    include_raw: bool = Query(False, description="是否在结果中包含原始 LLM 响应"),
) -> ExtractFromImageResponse:
    """从上传的图片中提取股票代码（使用 Vision LLM）。

    表单字段请使用 file 上传图片。优先级：Gemini / Anthropic / OpenAI（首个可用）。

    包含原始模型输出主要用于调试，正常调用可通过 include_raw 关闭；图片类型由 ALLOWED_MIME_STR 白名单约束。

    Args:
        file: 上传的图片文件。
        include_raw: 是否在响应中附带 LLM 原始文本。

    Returns:
        ExtractFromImageResponse: 去重代码列表与带置信度的结构化条目。

    Raises:
        HTTPException: 文件类型不支持、无可用视觉模型或识别失败。
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "未提供文件，请使用表单字段 file 上传图片"},
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_type",
                "message": f"不支持的类型: {content_type}。允许: {ALLOWED_MIME_STR}",
            },
        )

    try:
        # 先读取限定大小，再检查是否还有剩余（语义清晰：超出则拒绝）
        data = file.file.read(MAX_SIZE_BYTES)
        if file.file.read(1):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "file_too_large",
                    "message": f"图片超过 {MAX_SIZE_BYTES // (1024 * 1024)}MB 限制",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"读取上传文件失败: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "read_failed", "message": "读取上传文件失败"},
        )

    try:
        items, raw_text = extract_stock_codes_from_image(data, content_type)
        extract_items = [
            ExtractItem(code=code, name=name, confidence=conf) for code, name, conf in items
        ]
        codes = [i.code for i in extract_items]
        return ExtractFromImageResponse(
            codes=codes,
            items=extract_items,
            raw_text=raw_text if include_raw else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "extract_failed", "message": str(e)})
    except Exception as e:
        logger.error(f"图片提取失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "图片提取失败"},
        )


@router.post(
    "/parse-import",
    response_model=ExtractFromImageResponse,
    responses={
        200: {"description": "解析结果"},
        400: {"description": "未提供数据或解析失败", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="解析 CSV/Excel/剪贴板",
    description="上传 CSV/Excel 文件或粘贴文本，自动解析股票代码。文件上限 2MB，文本上限 100KB。",
)
async def parse_import(request: Request) -> ExtractFromImageResponse:
    """解析 CSV/Excel 文件或剪贴板文本。

    - multipart/form-data + file: 上传文件
    - application/json + {"text": "..."}: 粘贴文本
    - 优先使用 file，若同时提供则忽略 text

    统一输出与图片识别相同的响应形状，前端可复用同一结果渲染组件。

    Args:
        request: 原始请求对象，按 Content-Type 判断输入来源。

    Returns:
        ExtractFromImageResponse: 解析出的代码列表与条目明细。

    Raises:
        HTTPException: 输入为空或格式无法解析时返回 400。
    """
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception as e:
            logger.warning("[parse_import] JSON parse failed: %s", e)
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_json", "message": f"JSON 解析失败: {e}"},
            )
        text = body.get("text") if isinstance(body, dict) else None
        if not text or not isinstance(text, str):
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "message": "未提供 text，请使用 {\"text\": \"...\"}"},
            )
        try:
            items = parse_import_from_text(text)
        except ValueError as e:
            text_bytes = len(text.encode("utf-8"))
            logger.warning(
                "[parse_import] parse_import_from_text failed: text_bytes=%d, error=%s",
                text_bytes,
                e,
            )
            raise HTTPException(status_code=400, detail={"error": "parse_failed", "message": str(e)})
    elif "multipart" in content_type:
        form = await request.form()
        file = form.get("file")
        if not file or not hasattr(file, "read"):
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "message": "未提供文件，请使用表单字段 file"},
            )
        file_size = getattr(file, "size", None)
        if isinstance(file_size, int) and file_size > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "file_too_large",
                    "message": f"文件超过 {MAX_FILE_BYTES // (1024 * 1024)}MB 限制",
                },
            )
        try:
            data = file.file.read(MAX_FILE_BYTES)
            if file.file.read(1):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "file_too_large",
                        "message": f"文件超过 {MAX_FILE_BYTES // (1024 * 1024)}MB 限制",
                    },
                )
        except HTTPException:
            raise
        except Exception as e:
            filename = getattr(file, "filename", None) or ""
            size = getattr(file, "size", None)
            logger.warning(
                "[parse_import] file read failed: filename=%r, size=%s, error=%s",
                filename,
                size,
                e,
            )
            raise HTTPException(
                status_code=400,
                detail={"error": "read_failed", "message": "读取文件失败"},
            )
        filename = getattr(file, "filename", None) or ""
        try:
            items = parse_import_from_bytes(data, filename=filename)
        except ValueError as e:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            logger.warning(
                "[parse_import] parse_import_from_bytes failed: filename=%r, ext=%r, bytes=%d, error=%s",
                filename,
                ext,
                len(data),
                e,
            )
            raise HTTPException(status_code=400, detail={"error": "parse_failed", "message": str(e)})
    else:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "message": "请使用 multipart/form-data 上传文件，或 application/json 提交 {\"text\": \"...\"}",
            },
        )

    extract_items = [
        ExtractItem(code=code, name=name, confidence=conf)
        for code, name, conf in items
    ]
    codes = list(dict.fromkeys(i.code for i in extract_items if i.code))
    return ExtractFromImageResponse(codes=codes, items=extract_items, raw_text=None)


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    responses={
        200: {"description": "当前自选队列"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取自选队列",
    description="返回当前 STOCK_LIST 配置中的所有股票代码。",
)
def get_watchlist(
    service: SystemConfigService = Depends(get_system_config_service),
) -> WatchlistResponse:
    """获取自选股列表。

    Args:
        service: 配置服务，由 Depends 注入。

    Returns:
        WatchlistResponse: 当前 STOCK_LIST 代码列表与提示文案。
    """
    try:
        codes = _read_watchlist_codes(service)
        return WatchlistResponse(stock_codes=codes, message=f"当前自选 {len(codes)} 只股票")
    except Exception as e:
        logger.error(f"获取自选队列失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"获取自选队列失败: {str(e)}"},
        )


@router.post(
    "/watchlist/add",
    response_model=WatchlistResponse,
    responses={
        200: {"description": "已加入自选"},
        400: {"description": "参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="加入自选队列",
    description="将指定股票代码加入 STOCK_LIST。",
)
def add_to_watchlist(
    request: WatchlistRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> WatchlistResponse:
    """新增自选股。

    先规范化代码并计算等价键，已存在时保持列表不变，避免重复项。

    Args:
        request: 含股票代码的请求体。
        service: 配置服务，由 Depends 注入。

    Returns:
        WatchlistResponse: 更新后的完整代码列表。

    Raises:
        HTTPException: 代码格式非法 400。

    Side Effects:
        修改 STOCK_LIST 配置。
    """
    try:
        validated = _validate_and_normalize_stock_code(request.stock_code)
        codes = _read_watchlist_codes(service)
        existing_keys = [_watchlist_match_key(c) for c in codes]
        if _watchlist_match_key(validated) not in existing_keys:
            codes.append(request.stock_code.strip())
            _write_watchlist_codes(service, codes)
        return WatchlistResponse(stock_codes=codes, message=f"已加入 {request.stock_code.strip()}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加入自选失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"加入自选失败: {str(e)}"},
        )


@router.post(
    "/watchlist/remove",
    response_model=WatchlistResponse,
    responses={
        200: {"description": "已从自选删除"},
        400: {"description": "参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="从自选队列删除",
    description="从 STOCK_LIST 中移除指定股票代码。",
)
def remove_from_watchlist(
    request: WatchlistRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> WatchlistResponse:
    """移除自选股。

    按等价键匹配删除，兼容带后缀与不带后缀的代码写法。

    Args:
        request: 含股票代码的请求体。
        service: 配置服务，由 Depends 注入。

    Returns:
        WatchlistResponse: 更新后的完整代码列表。

    Raises:
        HTTPException: 代码格式非法 400。

    Side Effects:
        修改 STOCK_LIST 配置。
    """
    try:
        validated = _validate_and_normalize_stock_code(request.stock_code)
        codes = _read_watchlist_codes(service)
        existing_keys = [_watchlist_match_key(c) for c in codes]
        requested_key = _watchlist_match_key(validated)
        if requested_key in existing_keys:
            idx = existing_keys.index(requested_key)
            codes.pop(idx)
            _write_watchlist_codes(service, codes)
        return WatchlistResponse(stock_codes=codes, message=f"已移除 {request.stock_code.strip()}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从自选删除失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"从自选删除失败: {str(e)}"},
        )


@router.get(
    "/{stock_code}/quote",
    response_model=StockQuote,
    responses={
        200: {"description": "行情数据"},
        404: {"description": "股票不存在", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取股票实时行情",
    description="获取指定股票的最新行情数据"
)
def get_stock_quote(stock_code: str) -> StockQuote:
    """获取股票实时行情

    同步端点由 FastAPI 放入线程池执行，避免阻塞数据源调用卡住事件循环。

    Args:
        stock_code: 股票代码，来自路径参数。

    Returns:
        StockQuote: 实时价格、涨跌、成交量与估值快照。

    Raises:
        HTTPException: 代码无数据或数据源失败。
    """
    try:
        service = build_stock_service()
        
        # 使用 def 而非 async def，FastAPI 自动在线程池中执行
        result = service.get_realtime_quote(stock_code)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"未找到股票 {stock_code} 的行情数据"
                }
            )
        
        return StockQuote(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时行情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"获取实时行情失败: {str(e)}"
            }
        )


@router.get(
    "/{stock_code}/history",
    response_model=StockHistoryResponse,
    responses={
        200: {"description": "历史行情数据"},
        422: {"description": "不支持的周期参数", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取股票历史行情",
    description="获取指定股票的历史 K 线数据"
)
def get_stock_history(
    stock_code: str,
    period: str = Query("daily", description="K 线周期", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365, description="获取天数")
) -> StockHistoryResponse:
    """获取股票历史行情

    获取指定股票的历史 K 线数据

    Args:
        stock_code: 股票代码
        period: K 线周期 (daily/weekly/monthly)
        days: 获取天数

    Returns:
        StockHistoryResponse: 历史行情数据

    Raises:
        HTTPException: period 不受支持或取数失败。

    Side Effects:
        无；数据由数据源层按需缓存。
    """
    try:
        service = build_stock_service()
        
        # 使用 def 而非 async def，FastAPI 自动在线程池中执行
        result = service.get_history_data(
            stock_code=stock_code,
            period=period,
            days=days
        )
        
        # 转换为响应模型
        data = [
            KLineData(
                date=item.get("date"),
                open=item.get("open"),
                high=item.get("high"),
                low=item.get("low"),
                close=item.get("close"),
                volume=item.get("volume"),
                amount=item.get("amount"),
                change_percent=item.get("change_percent")
            )
            for item in result.get("data", [])
        ]
        
        return StockHistoryResponse(
            stock_code=stock_code,
            stock_name=result.get("stock_name"),
            period=period,
            data=data
        )
    
    except ValueError as e:
        # period 参数不支持的错误（如 weekly/monthly）
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unsupported_period",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"获取历史行情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"获取历史行情失败: {str(e)}"
            }
        )


@router.get(
    "/{stock_code}/timeline",
    response_model=StockTimelineResponse,
    responses={
        200: {"description": "分时数据（上游取空时 points 为空列表）"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取股票当日分时明细",
    description=(
        "获取指定股票最近一个交易日的分时明细（1 分钟粒度，含真实均价线所需成交量/成交额），"
        "用于分时缩略图、分时图懒加载等场景。数据源为东方财富 trends2（与尾盘选股同一取数契约），"
        "休市日返回最近一个已收盘交易日的全天分时；上游取数失败时 points 为空列表，调用方按无数据渲染占位。"
    )
)
def get_stock_timeline(stock_code: str) -> StockTimelineResponse:
    """获取股票当日分时明细

    Args:
        stock_code: 股票代码（如 600519、00700、AAPL）

    Returns:
        StockTimelineResponse: 昨收价 + 分时点（KLinePoint 形态，date 为 YYYY-MM-DD HH:mm:ss）

    Raises:
        HTTPException: 代码无数据或分时源失败。

    Side Effects:
        写入进程内分时缓存，TTL 由 _TIMELINE_CACHE_TTL 控制，用于降低上游 trends2 限流风险。
    """
    return _load_timeline(stock_code)


# 卡片分时缩略图保留的点数：全天约 240 点，等距采样后足够表现走势且显著减小 payload。
TIMELINE_THUMBNAIL_POINTS = 48
# 分时批量拉取的并发上限；上游 trends2 全局节流较严，与前端自选股列表保持同一口径。
TIMELINE_BATCH_CONCURRENCY = 3


def _load_timeline(stock_code: str) -> StockTimelineResponse:
    """读取单只股票当日分时，命中进程内缓存时直接复用缓存对象。

    Args:
        stock_code: 股票代码。

    Returns:
        StockTimelineResponse: 昨收价与完整分时点。

    Raises:
        HTTPException: 上游取数失败时返回 500。

    Side Effects:
        未命中时拉取上游并写入 ``_timeline_cache``。
    """
    cached = _timeline_cache.get(stock_code)
    if _timeline_cache_valid(cached, ttl=_TIMELINE_CACHE_TTL):
        return cached["data"]  # type: ignore[return-value]

    try:
        result = fetch_intraday_timeline(stock_code)
    except Exception as exc:
        logger.error("获取分时数据失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"获取分时数据失败: {exc}"},
        ) from exc

    response = StockTimelineResponse(
        stock_code=stock_code,
        stock_name=result.get("name") or None,
        prev_close=result.get("prev_close"),
        points=[StockTimelinePoint(**point) for point in result.get("points", [])],
    )
    _timeline_cache[stock_code] = {"data": response, "timestamp": time.time()}
    return response


def _downsample_points(points: List[StockTimelinePoint]) -> List[StockTimelinePoint]:
    """等距采样分时点到缩略图点数，始终保留首尾点。"""
    if len(points) <= TIMELINE_THUMBNAIL_POINTS:
        return points
    last_index = len(points) - 1
    return [
        points[round(index * last_index / (TIMELINE_THUMBNAIL_POINTS - 1))]
        for index in range(TIMELINE_THUMBNAIL_POINTS)
    ]


def _unique_codes(codes: List[str]) -> List[str]:
    """裁剪空白并去重，保持请求中的首次出现顺序。"""
    return list(dict.fromkeys(code.strip() for code in codes if code.strip()))


@router.post(
    "/batch-quote",
    response_model=BatchQuoteResponse,
    responses={500: {"description": "服务器错误", "model": ErrorResponse}},
    summary="批量获取实时行情",
    description="一次请求并发取最多 10 只股票的规范 camelCase 实时行情，供最近搜索卡片列表渲染。",
)
def get_batch_quotes(payload: BatchCodesRequest) -> BatchQuoteResponse:
    """并发获取多只股票实时行情；单只失败跳过，不影响其它条目。"""
    codes = _unique_codes(payload.codes)
    service = build_stock_service()

    def _fetch_one(code: str) -> Optional[StockQuote]:
        """取单只行情并转成响应模型；失败或空数据返回 None。"""
        try:
            quote = service.get_realtime_quote(code)
            if not quote:
                return None
            # 数据源可能回带交易所后缀的代码；批量响应统一以请求代码标识条目，
            # 前端才能按代码把行情合并回最近搜索记录。
            quote["code"] = code
            return StockQuote(**quote)
        except Exception as exc:
            logger.warning("批量行情取数失败: code=%s, %s", code, exc)
            return None

    with ThreadPoolExecutor(max_workers=min(len(codes), 8) or 1) as executor:
        quotes = list(executor.map(_fetch_one, codes))
    return BatchQuoteResponse(items=[quote for quote in quotes if quote is not None])


@router.post(
    "/batch-timeline",
    response_model=BatchTimelineResponse,
    responses={500: {"description": "服务器错误", "model": ErrorResponse}},
    summary="批量获取当日分时（下采样）",
    description="一次请求取最多 10 只股票的分时缩略图数据，复用分时缓存并等距下采样。",
)
def get_batch_timelines(payload: BatchCodesRequest) -> BatchTimelineResponse:
    """并发获取多只股票的下采样分时；单只失败降级为空 points。"""
    codes = _unique_codes(payload.codes)

    def _fetch_one(code: str) -> BatchTimelineItem:
        """取单只分时并下采样；上游失败时保留代码、返回空点列。"""
        try:
            timeline = _load_timeline(code)
        except HTTPException as exc:
            logger.warning("批量分时取数失败: code=%s, %s", code, exc.detail)
            return BatchTimelineItem(code=code, points=[])
        return BatchTimelineItem(
            code=code,
            name=timeline.stock_name,
            prevClose=timeline.prev_close,
            points=_downsample_points(timeline.points),
        )

    with ThreadPoolExecutor(max_workers=min(len(codes), TIMELINE_BATCH_CONCURRENCY) or 1) as executor:
        return BatchTimelineResponse(items=list(executor.map(_fetch_one, codes)))
