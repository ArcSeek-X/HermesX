"""akshare 共享协议、连接和配额；无能力选源/回退或第二份资源。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Any, Tuple
import multiprocessing
import pandas as pd
from src.domain.market.stock_codes import is_bse_code


@dataclass(frozen=True)
class AkshareClientAccess:
    """窄资源访问契约；状态写回原所有者，兼容旧资源扩展点。"""

    use_random_sleep: Callable
    read_last_request_time: Callable
    read_realtime_sleep_max: Callable
    read_realtime_sleep_min: Callable
    read_sleep_max: Callable
    read_sleep_min: Callable
    write_last_request_time: Callable
    read_global_USER_AGENTS: Callable
    read_global_logger: Callable
    read_global_random: Callable
    read_global_time: Callable

    def _set_random_user_agent(self) -> None:
        """
        设置随机 User-Agent

        通过修改 requests Session 的 headers 实现
        这是关键的反爬策略之一
        """
        try:
            import akshare as ak  # noqa: F401 - 保留原可选依赖探测/副作用

            random_ua = self.read_global_random().choice(self.read_global_USER_AGENTS())
            self.read_global_logger().debug(f"设置 User-Agent: {random_ua[:50]}...")
        except Exception as e:
            self.read_global_logger().debug(f"设置 User-Agent 失败: {e}")

    def _enforce_rate_limit(self) -> None:
        """
        强制执行速率限制

        策略：
        1. 检查距离上次请求的时间间隔
        2. 如果间隔不足，补充休眠时间
        3. 然后再执行随机 jitter 休眠
        """
        if self.read_last_request_time() is not None:
            elapsed = self.read_global_time().time() - self.read_last_request_time()
            min_interval = self.read_sleep_min()
            if elapsed < min_interval:
                additional_sleep = min_interval - elapsed
                self.read_global_logger().debug(f"补充休眠 {additional_sleep:.2f} 秒")
                self.read_global_time().sleep(additional_sleep)
        self.use_random_sleep(self.read_sleep_min(), self.read_sleep_max())
        self.write_last_request_time(self.read_global_time().time())

    def _enforce_realtime_rate_limit(self) -> None:
        """
        实时行情（单股直连腾讯/新浪）专用轻量限速。

        与 `_enforce_rate_limit` 的区别：实时行情是单股轻量 HTTP 请求，
        不需要默认 2~5s 的随机休眠（那会直接拖垮单股 quote 接口到秒级）。
        这里用独立的短休眠参数（默认 0~0.3s）在防封与低延迟间取平衡。
        """
        if self.read_last_request_time() is not None:
            elapsed = self.read_global_time().time() - self.read_last_request_time()
            min_interval = self.read_realtime_sleep_min()
            if elapsed < min_interval:
                self.read_global_time().sleep(min_interval - elapsed)
        self.use_random_sleep(
            self.read_realtime_sleep_min(), self.read_realtime_sleep_max()
        )
        self.write_last_request_time(self.read_global_time().time())


_AKSHARE_HISTORY_CALL_TIMEOUT = 30.0


_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE = 1.0


_AKSHARE_TIMEOUT_PROCESS_START_METHOD = "spawn"


def _is_etf_code(stock_code: str) -> bool:
    """
    判断代码是否为 ETF 基金

    ETF 代码规则：
    - 上交所 ETF: 51xxxx, 52xxxx, 56xxxx, 58xxxx
    - 深交所 ETF: 15xxxx, 16xxxx, 18xxxx

    Args:
        stock_code: 股票/基金代码

    Returns:
        True 表示是 ETF 代码，False 表示是普通股票代码
    """
    etf_prefixes = ('51', '52', '56', '58', '15', '16', '18')
    code = stock_code.strip().split('.')[0]
    return code.startswith(etf_prefixes) and len(code) == 6


def _to_sina_tx_symbol(stock_code: str) -> str:
    """Convert 6-digit A-share code to sh/sz/bj prefixed symbol for Sina/Tencent APIs."""
    base = (stock_code.strip().split(".")[0] if "." in stock_code else stock_code).strip()
    if is_bse_code(base):
        return f"bj{base}"
    # Shanghai: 60xxxx, 5xxxx (ETF), 90xxxx (B-shares)
    if base.startswith(("6", "5", "90")):
        return f"sh{base}"
    return f"sz{base}"


def _akshare_call_with_timeout(
    func,
    *args,
    timeout: Optional[float] = None,
    call_name: str = "akshare",
    **kwargs,
):
    """Run an akshare call with a bounded wait time."""
    wait_seconds = _AKSHARE_HISTORY_CALL_TIMEOUT if timeout is None else float(timeout)

    multiprocessing.freeze_support()
    ctx = multiprocessing.get_context(_AKSHARE_TIMEOUT_PROCESS_START_METHOD)
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_akshare_timeout_worker,
        args=(child_conn, func, args, kwargs),
        name=f"akshare-{call_name}",
        daemon=True,
    )

    process.start()
    child_conn.close()

    try:
        if not parent_conn.poll(wait_seconds):
            _terminate_akshare_process(process)
            raise TimeoutError(f"{call_name} 调用超过 {wait_seconds:g}s，已放弃等待")

        try:
            ok, value = parent_conn.recv()
        except EOFError as exc:
            raise RuntimeError(f"{call_name} 调用进程未返回结果") from exc
    finally:
        parent_conn.close()
        process.join(_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE)
        _terminate_akshare_process(process)

    if ok:
        return value
    raise value


def _akshare_timeout_worker(conn, func, args, kwargs) -> None:
    """在超时监控线程中执行 AkShare 调用。"""
    try:
        conn.send((True, func(*args, **kwargs)))
    except BaseException as exc:
        try:
            conn.send((False, exc))
        except BaseException:
            try:
                conn.send((False, RuntimeError(f"{type(exc).__name__}: {exc}")))
            except BaseException:
                pass
    finally:
        conn.close()


def _terminate_akshare_process(process) -> None:
    """终止超时的 AkShare 子进程。"""
    if process.is_alive():
        process.terminate()
        process.join(_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE)
    if process.is_alive():
        process.kill()
        process.join(_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE)


def safe_float(value: Any) -> Optional[float]:
    """将值安全转换为 float。"""
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int:
    """将值安全转换为 int。"""
    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def find_first_column(df: pd.DataFrame, candidates: Tuple[str, ...]) -> Optional[str]:
    """按候选名查找首个存在的列。"""
    columns = [str(col) for col in df.columns]
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def find_column_containing(df: pd.DataFrame, keywords: Tuple[str, ...]) -> Optional[str]:
    """查找名称包含关键字的列。"""
    for col in df.columns:
        col_text = str(col)
        if all(keyword in col_text for keyword in keywords):
            return col
    return None
