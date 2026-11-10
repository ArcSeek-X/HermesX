# -*- coding: utf-8 -*-
"""股票度量视图服务层（设计文档 §5/§6）。

职责：解析 filterList -> 解析市场并集 -> 按市场拉东财 clist 在线快照 ->
内存 (market, code) merge -> 应用筛选/排序/分页 -> 可选 join 离线因子 ->
组装响应；导出走 CSV（UTF-8 BOM + CRLF）。

在线 clist 拉取失败的市场按「降级」处理（该市场数据缺失，整体不 500）；离线因子
表未建/任务未跑时对应列返回 null（AC-6 降级）。本模块只抛 ``ValueError``，
HTTP 状态码由端点负责（避免 application 层反向依赖 api 层）。
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.application.quote.ports import StockMetricFactorsPort, StockMetricSnapshotPort
from src.config import settings
from src.utils.time import utc_naive_now

logger = logging.getLogger(__name__)

ALL_MARKETS = ("cn", "hk", "us")

# === 字段静态注册表（设计文档 §4.1 / §7.2）===
# markets: 该字段在哪些市场有数据；offline: 是否离线因子（仅 cn，hk/us 恒 null）；
# filterable / sortable：是否可筛选 / 可排序；kind：用于值类型校验。
STOCK_METRIC_FIELDS: Dict[str, Dict[str, Any]] = {
    "market": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "str"},
    "code": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "str"},
    "name": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "str"},
    "price": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "changePct": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "volume": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "relativeVolume": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "totalMarketCap": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "peRatioTTM": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "epsDiluted": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "dividendYieldPct": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "industry": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "str"},
    "roePct": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "pbRatio": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "psRatioTTM": {"markets": ALL_MARKETS, "filterable": True, "sortable": True, "kind": "num"},
    "revenueGrowthYoyPct": {"markets": ("cn",), "filterable": True, "sortable": True, "kind": "num"},
    "epsGrowthTtmYoyPct": {"markets": ("cn",), "filterable": True, "sortable": True, "kind": "num", "offline": True},
    "analystRating": {"markets": ("cn",), "filterable": True, "sortable": True, "kind": "num", "offline": True},
}

DISPLAY_COLUMNS = [
    "code", "name", "price", "changePct", "volume", "relativeVolume",
    "totalMarketCap", "peRatioTTM", "epsDiluted", "epsGrowthTtmYoyPct",
    "dividendYieldPct", "industry", "analystRating",
]
# 响应列 key → 仓储因子字典 key。两层命名不同，映射必须显式，不能靠同名猜。
OFFLINE_FIELD_MAP = {
    "epsGrowthTtmYoyPct": "eps_ttm_yoy_pct",
    "analystRating": "analyst_rating",
}
OFFLINE_FACTORS_UNAVAILABLE_NOTE = (
    "EPS 增长(TTM同比) / 分析师评级为季频离线指标，当前无可用跑批数据，按无数据展示 —（不填 0、不估算）"
)

# 以原币计价的字段：跨市场时币种不同（CNY / HKD / USD），数值不可直接比较
CURRENCY_DENOMINATED_FIELDS = {"price", "totalMarketCap", "epsDiluted"}
CROSS_MARKET_SORT_NOTE = (
    "跨市场查询时股价 / 市值 / 每股收益按原币（CNY / HKD / USD）展示，不做汇率折算；"
    "排序按市场分组，仅组内比较"
)

VALID_OPS = {"eq", "neq", "gt", "gte", "lt", "lte", "between", "in"}
MAX_FILTERS = 10
MAX_PAGE_SIZE = 100
EXPORT_LIMIT = 5000
FINANCIAL_REPORT_MAX_PAGES = 20


class StockMetricService:
    """股票度量视图业务编排（无状态；取数与仓储端口由 bootstrap 注入）。"""

    def __init__(
        self,
        snapshot_port: Optional[StockMetricSnapshotPort] = None,
        factors_port: Optional[StockMetricFactorsPort] = None,
    ) -> None:
        self._snapshot_port = snapshot_port
        self._factors_port = factors_port

    # ---- 公开接口 ----
    def query(
        self,
        *,
        filter_list: List[Any],
        sort: Any,
        page_num: int,
        page_size: int,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        self._validate(filter_list, sort)
        page_num = max(1, int(page_num or 1))
        page_size = min(max(1, int(page_size or 20)), MAX_PAGE_SIZE)
        markets = self._resolve_markets(filter_list)
        rows, degraded, warnings, quote_as_of = self._fetch_all(markets, force_refresh=force_refresh)
        rows = self._apply_filters(rows, filter_list)
        # 离线因子必须在排序前 join，否则按离线列排序时该列全为空、排序失效
        rows, offline_unavailable = self._join_offline(rows, markets)
        if offline_unavailable:
            degraded = True
            warnings.append(OFFLINE_FACTORS_UNAVAILABLE_NOTE)
        if sort.field in CURRENCY_DENOMINATED_FIELDS and len(markets) > 1:
            warnings.append(CROSS_MARKET_SORT_NOTE)
        rows = self._apply_sort(rows, sort.field, sort.order, markets)
        total = len(rows)
        offset = (page_num - 1) * page_size
        page_rows = rows[offset: offset + page_size]
        return self._build_response(
            page_rows, total, page_num, page_size, degraded, warnings, quote_as_of
        )

    def export(
        self,
        *,
        filter_list: List[Any],
        sort: Any,
        visible_columns: List[str],
        headers: Dict[str, str],
        limit: int,
    ) -> Tuple[bytes, bool]:
        self._validate(filter_list, sort)
        limit = min(max(1, int(limit or EXPORT_LIMIT)), EXPORT_LIMIT)
        markets = self._resolve_markets(filter_list)
        rows = self._fetch_all(markets)[0]
        rows = self._apply_filters(rows, filter_list)
        rows, _ = self._join_offline(rows, markets)
        rows = self._apply_sort(rows, sort.field, sort.order, markets)
        truncated = len(rows) > limit
        if truncated:
            rows = rows[:limit]
        return self._to_csv(rows, visible_columns, headers), truncated

    # ---- 校验 ----
    def _validate(self, filter_list: List[Any], sort: Any) -> None:
        if len(filter_list) > MAX_FILTERS:
            raise ValueError(f"筛选条件过多（最多 {MAX_FILTERS} 条）")
        for item in filter_list:
            field = item.field
            op = item.op
            value = item.value
            if field not in STOCK_METRIC_FIELDS:
                raise ValueError(f"不支持的筛选字段: {field}")
            if not STOCK_METRIC_FIELDS[field]["filterable"]:
                raise ValueError(f"字段不可筛选: {field}")
            if op not in VALID_OPS:
                raise ValueError(f"不支持的算子: {op}")
            self._validate_value(field, op, value)
        if sort.field not in STOCK_METRIC_FIELDS or not STOCK_METRIC_FIELDS[sort.field]["sortable"]:
            raise ValueError(f"不支持的排序字段: {sort.field}")
        if sort.order not in ("asc", "desc"):
            raise ValueError(f"不支持的排序方向: {sort.order}")

    @staticmethod
    def _validate_value(field: str, op: str, value: Any) -> None:
        meta = STOCK_METRIC_FIELDS[field]
        kind = meta["kind"]
        if op == "between":
            if not isinstance(value, (list, tuple)) or len(value) < 2:
                raise ValueError(f"{field} between 需要长度为 2 的数组")
            lo, hi = value[0], value[1]
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(f"{field} between 最小不能大于最大")
            return
        if op == "in":
            if not isinstance(value, (list, tuple)) or not value:
                raise ValueError(f"{field} in 需要非空数组")
            return
        # eq / neq / gt / gte / lt / lte
        if kind == "num" and value is not None:
            try:
                float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{field} 需要数值，收到: {value!r}")

    # ---- 市场解析 ----
    def _resolve_markets(self, filter_list: List[Any]) -> List[str]:
        market_conditions = [it for it in filter_list if it.field == "market"]
        if len(market_conditions) > 1:
            raise ValueError("仅支持单一市场并集（market 条件只能有一条）")
        if not market_conditions:
            return ["cn"]
        cond = market_conditions[0]
        raw = cond.value if cond.op == "in" else [cond.value]
        if isinstance(raw, str):
            raw = [raw]
        markets = []
        for m in raw:
            m = str(m).lower()
            if m not in ALL_MARKETS:
                raise ValueError(f"不支持的市场: {m}")
            if m not in markets:
                markets.append(m)
        return sorted(markets)

    # ---- 数据拉取 ----
    def _fetch_all(
        self, markets: List[str], force_refresh: bool = False
    ) -> Tuple[List[Dict[str, Any]], bool, List[str], str]:
        rows: List[Dict[str, Any]] = []
        degraded = False
        warnings: List[str] = []
        fetched_at_list: List[str] = []
        if self._snapshot_port is None:
            return rows, True, ["在线快照端口未装配，已按降级处理"], ""
        for market in markets:
            snapshot = self._snapshot_port(market, force_refresh=force_refresh)
            if snapshot is None:
                degraded = True
                warnings.append(f"市场 {market} 在线数据拉取失败，已按降级处理")
                continue
            snapshot_rows, fetched_at = snapshot
            rows.extend(snapshot_rows)
            if fetched_at:
                fetched_at_list.append(fetched_at)
        # 各市场按自身 TTL 缓存，取最早的抓取时刻，保守表达整批数据的最旧新鲜度；
        # 端口统一输出 +00:00 的 ISO 8601，字典序等价于时间序。
        # 全部市场无在线数据时留空，不用「当前时刻」伪造行情时间。
        quote_as_of = min(fetched_at_list) if fetched_at_list else ""
        return rows, degraded, warnings, quote_as_of

    # ---- 筛选 / 排序 ----
    @staticmethod
    def _apply_filters(rows: List[Dict[str, Any]], filter_list: List[Any]) -> List[Dict[str, Any]]:
        result = rows
        for cond in filter_list:
            if cond.field == "market":
                continue
            result = [r for r in result if _match(r.get(cond.field), cond.op, cond.value)]
        return result

    @staticmethod
    def _apply_sort(
        rows: List[Dict[str, Any]], field: str, order: str, markets: List[str]
    ) -> List[Dict[str, Any]]:
        """按字段排序：统一值类型避免混合类型比较崩溃，None 恒排末尾。

        金额类字段跨市场时币种不同（CNY / HKD / USD），一期不做汇率折算：
        按 cn/hk/us 分组，组内按原币数值排序，组间按固定市场顺序，避免把不同
        币种的绝对值混排成无意义的名次（方案 §7.2）。
        """
        kind = STOCK_METRIC_FIELDS[field]["kind"]

        def to_sort_value(value: Any) -> Any:
            if value is None:
                return None
            if kind == "num":
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
            return str(value)

        def sort_group(group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            valued: List[Tuple[Any, Dict[str, Any]]] = []
            missing: List[Dict[str, Any]] = []
            for row in group:
                value = to_sort_value(row.get(field))
                if value is None:
                    missing.append(row)
                else:
                    valued.append((value, row))
            valued.sort(key=lambda pair: pair[0], reverse=(order == "desc"))
            return [row for _, row in valued] + missing

        if field not in CURRENCY_DENOMINATED_FIELDS or len(markets) <= 1:
            return sort_group(rows)

        by_market: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            by_market.setdefault(str(row.get("market") or ""), []).append(row)
        ordered_markets = list(ALL_MARKETS) + [m for m in by_market if m not in ALL_MARKETS]
        result: List[Dict[str, Any]] = []
        for market in ordered_markets:
            if market in by_market:
                result.extend(sort_group(by_market[market]))
        return result

    # ---- 离线因子 join ----
    def _join_offline(
        self, rows: List[Dict[str, Any]], markets: List[str]
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """join cn 季频离线因子，返回 (rows, offline_unavailable)。

        离线列只填 cn 行，避免港股 / 美股与 A 股同代码时误用 A 股因子。
        """
        # 所有市场的行都带齐离线列（无来源恒为 None），保证服务层输出形状一致
        for row in rows:
            for column in OFFLINE_FIELD_MAP:
                row.setdefault(column, None)
        if "cn" not in markets:
            return rows, False
        if self._factors_port is None:
            return rows, True
        factors = self._factors_port.fetch_latest_factors("cn")
        unavailable = not factors
        for row in rows:
            if row.get("market") != "cn":
                continue
            factor = factors.get(row.get("code")) or {}
            for column, source_field in OFFLINE_FIELD_MAP.items():
                row[column] = factor.get(source_field)
        return rows, unavailable

    # ---- 响应 / CSV ----
    def _build_response(
        self,
        page_rows: List[Dict[str, Any]],
        total: int,
        page_num: int,
        page_size: int,
        degraded: bool,
        warnings: List[str],
        quote_as_of: str,
    ) -> Dict[str, Any]:
        from src.utils.pagination import paginate_response

        resp = paginate_response(page_rows, total, page_num, page_size)
        resp["asOfDate"] = self._as_of_date() or ""
        resp["quoteAsOf"] = quote_as_of
        resp["warnings"] = warnings
        resp["degraded"] = degraded
        return resp

    def _as_of_date(self) -> Optional[str]:
        """离线因子基准日：取 is_latest 行的最新报告期；无数据返回 None（响应留空，不伪造今日）。"""
        if self._factors_port is None:
            return None
        return self._factors_port.fetch_latest_as_of_date("cn")

    @staticmethod
    def _to_csv(rows: List[Dict[str, Any]], visible_columns: List[str], headers: Dict[str, str]) -> bytes:
        # 首列固定 market,code,name（设计文档 §7.4）；其余按前端可见列顺序输出（AC-7）
        requested = visible_columns or DISPLAY_COLUMNS
        tail = [
            c for c in requested
            if c in STOCK_METRIC_FIELDS and c not in ("market", "code", "name")
        ]
        cols = ["market", "code", "name"] + tail
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\r\n")
        writer.writerow([headers.get(c, c) for c in cols])
        for r in rows:
            writer.writerow([_csv_cell(r.get(c)) for c in cols])
        return buf.getvalue().encode("utf-8-sig")  # 带 BOM，Excel 中文不乱码


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        # 避免 1.0 / 长尾 0；保留原始精度
        return repr(value) if value != int(value) else str(int(value))
    return str(value)


def _match(v: Any, op: str, value: Any) -> bool:
    if op == "in":
        return isinstance(value, (list, tuple)) and v in value
    if op == "eq":
        return v == value
    if op == "neq":
        return v is not None and v != value
    if op in ("gt", "gte", "lt", "lte"):
        if v is None:
            return False
        try:
            if op == "gt":
                return v > value
            if op == "gte":
                return v >= value
            if op == "lt":
                return v < value
            return v <= value
        except TypeError:
            return False
    if op == "between":
        if not isinstance(value, (list, tuple)) or len(value) < 2 or v is None:
            return False
        lo, hi = value[0], value[1]
        try:
            if lo is not None and v < lo:
                return False
            if hi is not None and v > hi:
                return False
        except TypeError:
            return False
        return True
    return False


# === 季频离线因子跑批（设计文档 §10；调度注册时由装配层传入端口）===
def run_stock_metric_quarterly_job(factors_port: StockMetricFactorsPort) -> None:
    """季频任务入口：拉取并写入 cn 离线因子，记录跑批结果。

    ``factors_port`` 由调度装配层注入，应用层不感知数据库 / ORM。仅在
    ``STOCK_METRIC_JOB_ENABLED`` 开启时执行；任何异常均写入 calc_run 记录，
    不抛给调度器。未配置 / 源不可达时优雅降级（离线列保持 null，AC-6）。
    """
    if not settings.stock_metric_job_enabled:
        logger.info("[stock_metric] 季频任务被配置关闭，跳过")
        return
    factors_port.init_tables()
    status = "success"
    note: Optional[str] = None
    written = 0
    try:
        written = _ingest_cn_quarterly_factors(factors_port)
    except Exception as exc:  # pragma: no cover - 任务级兜底
        status = "failed"
        note = str(exc)[:255]
        logger.exception("[stock_metric] 季频任务异常: %s", exc)
    factors_port.record_calc_run(status=status, rows_written=written, note=note)


def _ingest_cn_quarterly_factors(factors_port: StockMetricFactorsPort) -> int:
    """从东财 datacenter-web 拉取 cn 最新报告期财报因子并写入。

    best-effort：任一环节失败即返回 0（不造假数据），离线列继续按 AC-6 降级。
    """
    rows = _fetch_cn_financials()
    if not rows:
        return 0
    return factors_port.upsert_periods(rows)


def _fetch_cn_financials() -> List[Dict[str, Any]]:
    """东财 datacenter-web 业绩报表（RPT_LICO_FN_CPD）最新报告期批量拉取。

    字段名以接口 ``columns=ALL`` 实测为准：``REPORTDATE`` / ``BASIC_EPS`` /
    ``WEIGHTAVG_ROE`` / ``TOTAL_OPERATE_INCOME`` / ``YSTZ``；旧骨架里的
    ``REPORT_DATE`` / ``EPSJB`` / ``ROEJQ`` 并不存在，会让接口直接返回失败。
    EPS TTM 同比需跨期累计 EPS 计算、分析师评级需另接研报源，本期均无来源，
    对应列保持 None（不估算、不造假）。
    """
    try:
        import requests

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        base_params = {
            "reportName": "RPT_LICO_FN_CPD",
            "source": "WEB",
            "client": "WEB",
        }
        # 先锁定最新报告期再分页，避免把历史各期混进 is_latest 行
        latest_resp = requests.get(
            url,
            params={
                **base_params,
                "columns": "REPORTDATE",
                "pageSize": 1,
                "sortColumns": "REPORTDATE",
                "sortTypes": -1,
            },
            timeout=20,
        )
        latest_resp.raise_for_status()
        latest_data = ((latest_resp.json() or {}).get("result") or {}).get("data") or []
        report_date_text = str(latest_data[0].get("REPORTDATE") or "")[:10] if latest_data else ""
        if not report_date_text:
            return []

        columns = (
            "SECURITY_CODE,REPORTDATE,BASIC_EPS,WEIGHTAVG_ROE,TOTAL_OPERATE_INCOME,YSTZ"
        )
        rows: List[Dict[str, Any]] = []
        now = utc_naive_now()
        for page in range(1, FINANCIAL_REPORT_MAX_PAGES + 1):
            resp = requests.get(
                url,
                params={
                    **base_params,
                    "columns": columns,
                    "filter": f"(REPORTDATE='{report_date_text}')",
                    "pageNumber": page,
                    "pageSize": 1000,
                    "sortColumns": "SECURITY_CODE",
                    "sortTypes": 1,
                },
                timeout=20,
            )
            resp.raise_for_status()
            result = (resp.json() or {}).get("result") or {}
            for item in result.get("data") or []:
                code = str(item.get("SECURITY_CODE") or "").strip()
                if not code:
                    continue
                rows.append(
                    {
                        "market": "cn",
                        "code": code,
                        "report_date": _parse_report_date(item.get("REPORTDATE")),
                        "eps_diluted": _to_float_or_none(item.get("BASIC_EPS")),
                        "eps_ttm_yoy_pct": None,  # 需跨 4 期 EPS 计算，无直接来源
                        "revenue": _to_int_or_none(item.get("TOTAL_OPERATE_INCOME")),
                        "revenue_yoy_pct": _to_float_or_none(item.get("YSTZ")),
                        "roe_pct": _to_float_or_none(item.get("WEIGHTAVG_ROE")),
                        "pb_ratio": None,
                        "ps_ratio_ttm": None,
                        "dividend_yield_pct": None,
                        "analyst_rating": None,  # 需研报评级源，本期留空
                        "is_latest": True,
                        "created_at": now,
                    }
                )
            if page >= int(result.get("pages") or 1):
                break
        return rows
    except Exception as exc:  # pragma: no cover - 源不可达降级
        logger.info("[stock_metric] 财报源暂不可用，降级: %s", exc)
        return []


def _parse_report_date(value: Any) -> date:
    from datetime import datetime as _dt

    if isinstance(value, date) and not isinstance(value, _dt):
        return value
    if isinstance(value, _dt):
        return value.date()
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return _dt.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return date.today()


def _to_float_or_none(value: Any) -> Optional[float]:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_or_none(value: Any) -> Optional[int]:
    f = _to_float_or_none(value)
    return int(f) if f is not None else None
