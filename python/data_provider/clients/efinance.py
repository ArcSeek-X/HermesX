"""efinance 共享协议、连接和配额；无能力选源/回退或第二份资源。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple
from concurrent.futures import ThreadPoolExecutor
import re
import requests


@dataclass(frozen=True)
class EfinanceClientAccess:
    """窄资源访问契约；状态写回原所有者，兼容旧资源扩展点。"""

    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    use_random_sleep: Callable
    read_last_request_time: Callable
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

    def _prepare_history_request(self) -> None:
        """日线沿用本实例的 UA/节流，顺序和共享时钟保持不变。"""
        self.use_set_random_user_agent()
        self.use_enforce_rate_limit()


def _is_us_code(stock_code: str) -> bool:
    """
    判断代码是否为美股
    
    美股代码规则：
    - 1-5个大写字母，如 'AAPL', 'TSLA'
    - 可能包含 '.'，如 'BRK.B'
    """
    code = stock_code.strip().upper()
    return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code))


def call_with_timeout(func, *args, default_timeout, timeout=None, **kwargs):
    """Run an efinance library call in a thread with a timeout.

    efinance internally uses requests/urllib3 with no timeout, so when
    eastmoney hosts are unreachable the call can hang for many minutes.
    This helper caps the *calling thread's* wait time.  Note: Python threads
    cannot be forcibly killed, so the worker thread may continue running in
    the background until the OS-level TCP timeout fires or the process exits.
    This is acceptable — the calling thread returns promptly on timeout.
    """
    if timeout is None:
        timeout = default_timeout
    # Do NOT use 'with ThreadPoolExecutor(...)' here: the context manager calls
    # shutdown(wait=True) on __exit__, which would re-block on the hung thread.
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(func, *args, **kwargs)
        return future.result(timeout=timeout)
    finally:
        # wait=False: calling thread returns immediately; worker cleans up later
        executor.shutdown(wait=False)


def _classify_eastmoney_error(exc: Exception) -> Tuple[str, str]:
    """
    Classify Eastmoney request failures into stable log categories.
    """
    message = str(exc).strip()
    lowered = message.lower()

    remote_disconnect_keywords = (
        'remotedisconnected',
        'remote end closed connection without response',
        'connection aborted',
        'connection broken',
        'protocolerror',
    )
    timeout_keywords = (
        'timeout',
        'timed out',
        'readtimeout',
        'connecttimeout',
    )
    rate_limit_keywords = (
        'banned',
        'blocked',
        '频率',
        'rate limit',
        'too many requests',
        '429',
        '限制',
        'forbidden',
        '403',
    )

    if any(keyword in lowered for keyword in remote_disconnect_keywords):
        return "remote_disconnect", message
    if isinstance(exc, (TimeoutError, requests.exceptions.Timeout)) or any(
        keyword in lowered for keyword in timeout_keywords
    ):
        return "timeout", message
    if any(keyword in lowered for keyword in rate_limit_keywords):
        return "rate_limit_or_anti_bot", message
    if isinstance(exc, requests.exceptions.RequestException):
        return "request_error", message
    return "unknown_request_error", message
